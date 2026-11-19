#!/usr/bin/env python


import math
import os
import re
import subprocess
import sys
from contextlib import suppress
from datetime import datetime, timedelta, timezone
import logging.config
import getopt
from collections import deque
from pathlib import Path
from typing import Any, Optional
from filelock import FileLock, Timeout
from bin.feed_maker_util import Config, PathUtil, FileManager, NotFoundConfigItemError, Env, Process
from bin.headless_browser import HeadlessBrowser
from bin.notification import Notification
from bin.feed_maker import FeedMaker, STOP_FLAG_FILE_NAME
from bin.problem_manager import ProblemManager

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

# run.py -a에서 완결 피드의 미처리 항목이 이 개수 이상이면 별도 세션으로 넘긴다.
LONG_TERM_TASK_THRESHOLD = 50


def spread_feeds_by_group(feed_dir_path_list: list[Path]) -> list[Path]:
    """같은 피드그룹의 피드가 실행 순서에서 최대한 멀리 떨어지도록 정렬한다.

    피드 수를 가중치로 쓰는 smooth weighted round-robin으로 그룹을 고른다. 큰 그룹도 전체 구간에 고르게 퍼진다.
    직전 그룹은 피한다. 다만 남은 피드로 연속 실행 상한을 지킬 수 없으면 피하지 않는다.
    상한은 피할 수 없는 최소값 ceil(최대 그룹 피드 수 / (나머지 피드 수 + 1))이다.
    같은 입력에는 항상 같은 순서를 돌려준다. 그룹 안에서는 피드 이름순이다.
    """
    queues: dict[str, deque[Path]] = {}
    for feed_dir_path in sorted(feed_dir_path_list, key=lambda p: (p.parent.name, p.name)):
        queues.setdefault(feed_dir_path.parent.name, deque()).append(feed_dir_path)
    if not queues:
        return []

    group_names = sorted(queues, key=lambda g: (-len(queues[g]), g))
    weights = {g: len(queues[g]) for g in group_names}
    total = len(feed_dir_path_list)
    max_run = math.ceil(weights[group_names[0]] / (total - weights[group_names[0]] + 1))
    current = dict.fromkeys(group_names, 0)

    def is_feasible(pick: str, run_after: int) -> bool:
        remaining_total = sum(len(q) for q in queues.values()) - 1
        for group_name, queue in queues.items():
            left = len(queue) - (1 if group_name == pick else 0)
            if left == 0:
                continue
            pending = left + (run_after if group_name == pick else 0)
            if math.ceil(pending / (remaining_total - left + 1)) > max_run:
                return False
        return True

    result: list[Path] = []
    last = ""
    run = 0
    for _ in range(total):
        candidates = [g for g in group_names if queues[g]]
        for group_name in candidates:
            current[group_name] += weights[group_name]
        candidates.sort(key=lambda g: -current[g])
        can_avoid_last = any(g != last and is_feasible(g, 1) for g in candidates)
        choice = candidates[0]
        for group_name in candidates:
            if group_name == last and can_avoid_last:
                continue
            run_after = run + 1 if group_name == last else 1
            if run_after <= max_run and is_feasible(group_name, run_after):
                choice = group_name
                break
        run = run + 1 if choice == last else 1
        last = choice
        current[choice] -= total
        result.append(queues[choice].popleft())
    return result


class FeedMakerRunner:
    def __init__(self, html_archiving_period: int, list_archiving_period: int) -> None:
        LOGGER.debug(f"# FeedMakerRunner(html_archiving_period={html_archiving_period}, list_archiving_period={list_archiving_period})")
        self.html_archiving_period = html_archiving_period
        self.list_archiving_period = list_archiving_period
        # 마지막 make_single_feed() 실패 원인. backend가 사용자 메시지에 덧붙인다.
        self.failure_reason = ""
        # 마지막 make_single_feed()에서 장시간 작업으로 판정했는지
        self.is_long_term_task = False
        # 마지막 make_single_feed()가 다른 세션이 쥔 피드 잠금 때문에 실행하지 못했는지
        self.is_running_elsewhere = False
        self.work_dir_path = Path(Env.get("FM_WORK_DIR"))
        if not self.work_dir_path.is_dir():
            LOGGER.error("Error: Can't find work directory '%s'", PathUtil.short_path(self.work_dir_path))
        self.img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX"))
        if not self.img_dir_path.is_dir():
            LOGGER.error("Error: Can't find image directory '%s'", PathUtil.short_path(self.img_dir_path))

    def __del__(self) -> None:
        self.html_archiving_period = 0
        self.list_archiving_period = 0
        self.work_dir_path = Path()
        self.img_dir_path = Path()

    def make_single_feed(self, feed_dir_path: Path, options: dict[str, Any]) -> bool:
        LOGGER.debug("# make_single_feed(feed_dir_path='%s', options=%r)", PathUtil.short_path(feed_dir_path), options)

        start_time = datetime.now(timezone.utc)
        self.failure_reason = ""
        self.is_long_term_task = False
        self.is_running_elsewhere = False

        lock_file_path = feed_dir_path / ".feed_maker_runner.lock"
        if lock_file_path.is_file():
            st = lock_file_path.stat()
            if datetime.fromtimestamp(st.st_mtime, timezone.utc) < datetime.now(timezone.utc) - timedelta(days=1):
                LOGGER.debug("remove old lock file '%s'", PathUtil.short_path(lock_file_path))
                lock_file_path.unlink(missing_ok=True)

        try:
            logging.getLogger("filelock").setLevel(logging.ERROR)
            with FileLock(str(lock_file_path), timeout=5):
                # 잠금 파일 mtime은 획득할 때 갱신되지 않을 수 있다.
                # 위의 1일 경과 잠금 삭제가 실행 중인 장시간 작업의 잠금을 지우지 않도록 획득 시각으로 맞춘다.
                with suppress(OSError):
                    lock_file_path.touch()
                # 이전 실행에서 남은 중단 요청이 이번 실행을 막지 않도록 지운다.
                (feed_dir_path / STOP_FLAG_FILE_NAME).unlink(missing_ok=True)
                feed_name = feed_dir_path.name
                LOGGER.info("* %s", PathUtil.short_path(feed_dir_path))
                rss_file_path = feed_dir_path / f"{feed_name}.xml"
                feed_img_dir_path = self.img_dir_path / feed_name

                do_remove_all_files = options.get("do_remove_all_files", False)
                force_collection_opt = options.get("force_collection_opt", False)
                collect_only_opt = options.get("collect_only_opt", False)
                extract_only_opt = options.get("extract_only_opt", False)
                window_size = options.get("window_size", FeedMaker.DEFAULT_WINDOW_SIZE)

                if do_remove_all_files:
                    # -r 옵션 사용하면 html 디렉토리의 파일들, newlist 디렉토리의 파일들, 각종 로그 파일, feed xml 파일들을 삭제
                    FileManager.remove_all_files(feed_dir_path)
                # 0 byte 이미지 파일 삭제
                FileManager.remove_image_files_with_zero_size(feed_img_dir_path)
                # 다운로드되어 있어야 하는 이미지가 없는 html 파일 삭제
                FileManager.remove_html_files_without_cached_image_files(feed_dir_path, feed_img_dir_path)

                # make_feed.py 실행하여 feed 파일 생성
                LOGGER.info("* making feed file '%s'", PathUtil.short_path(rss_file_path))
                feed_maker = FeedMaker(feed_dir_path=feed_dir_path, do_collect_by_force=force_collection_opt, do_collect_only=collect_only_opt, rss_file_path=rss_file_path, window_size=window_size, do_extract_only=extract_only_opt, long_term_task_threshold=options.get("long_term_task_threshold", 0))
                try:
                    result = feed_maker.make()
                    self.failure_reason = feed_maker.failure_reason
                    self.is_long_term_task = feed_maker.is_long_term_task is True
                finally:
                    (feed_dir_path / STOP_FLAG_FILE_NAME).unlink(missing_ok=True)
                    # 피드 단위로 Chromium 세션을 재활용 — 같은 피드그룹 안에서 자원이 누적되어
                    # N번째 피드부터 page.evaluate/page.goto가 무한 대기에 빠지는 현상을 차단.
                    # user_data_dir은 보존되어 로그인 상태/쿠키는 유지됨.
                    HeadlessBrowser.recycle_session()

                # 불필요한 파일 삭제
                FileManager.remove_temporary_files(feed_dir_path)
        except Timeout:
            LOGGER.warning("can't run multiple feed makers concurrently")
            self.is_running_elsewhere = True
            return False

        end_time = datetime.now(timezone.utc)
        LOGGER.info("# Running time analysis")
        LOGGER.info(f"* Start time: {start_time.isoformat(timespec='seconds')}")
        LOGGER.info(f"* End time: {end_time.isoformat(timespec='seconds')}")
        LOGGER.info(f"* Elapsed time: {(end_time - start_time).total_seconds()}")

        return result

    def make_all_feeds(self, options: dict[str, Any]) -> bool:
        LOGGER.debug("# make_all_feeds()")
        num_feeds = options.get("num_feeds", 0)

        start_time = datetime.now(timezone.utc)

        LOGGER.info("# Generating feeds")
        feed_dir_path_list: list[Path] = []
        for group_dir_path in self.work_dir_path.iterdir():
            if not group_dir_path.name.startswith("_") and group_dir_path.is_dir():
                for feed_dir_path in group_dir_path.iterdir():
                    conf_file_path = feed_dir_path / Config.DEFAULT_CONF_FILE
                    if not feed_dir_path.name.startswith("_") and feed_dir_path.is_dir() and conf_file_path.is_file():
                        feed_dir_path_list.append(feed_dir_path)

        feed_dir_path_list = spread_feeds_by_group(feed_dir_path_list)
        if num_feeds > 0:
            feed_dir_path_list = feed_dir_path_list[:num_feeds]

        failed_feed_list: list[str] = []
        for feed_dir_path in feed_dir_path_list:
            print(feed_dir_path)
            feed_name = feed_dir_path.name
            config = Config(feed_dir_path=feed_dir_path)
            try:
                collection_conf = config.get_collection_configs()
            except NotFoundConfigItemError as e:
                LOGGER.error(e)
                failed_feed_list.append(feed_dir_path.parent.name + "/" + feed_name)
                continue

            try:
                if collection_conf.get("is_completed", False):
                    result = self.make_single_feed(feed_dir_path, options={"force_collection_opt": "-c", "long_term_task_threshold": LONG_TERM_TASK_THRESHOLD})
                    if self.is_running_elsewhere:
                        LOGGER.info("skipping '%s', running in another session", PathUtil.short_path(feed_dir_path))
                        continue
                    if self.is_long_term_task:
                        if not self._spawn_long_term_task(feed_dir_path):
                            failed_feed_list.append(feed_dir_path.parent.name + "/" + feed_name)
                        continue
                    if not result:
                        LOGGER.warning(f"Warning: can't make a feed '{feed_name} with all completed articles, {result}")
                        failed_feed_list.append(feed_dir_path.parent.name + "/" + feed_name)
                        continue

                result = self.make_single_feed(feed_dir_path, options={})
                if self.is_running_elsewhere:
                    LOGGER.info("skipping '%s', running in another session", PathUtil.short_path(feed_dir_path))
                    continue
                if not result:
                    LOGGER.warning(f"Warning: can't make a feed '{feed_name}' with recent articles, {result}")
                    failed_feed_list.append(feed_dir_path.parent.name + "/" + feed_name)
            except NotFoundConfigItemError as e:
                # 피드 하나의 설정 누락이 전체 실행(run.py -a)을 중단시키지 않도록 격리
                LOGGER.error(e)
                failed_feed_list.append(feed_dir_path.parent.name + "/" + feed_name)
            except Exception:  # pylint: disable=broad-exception-caught
                # crawler는 in-process로 돌아 처리하지 않은 예외가 여기까지 올라온다.
                # 피드 하나의 예외가 나머지 피드 실행을 막지 않게 격리하고,
                # stderr(run_all.log, 매 회차 덮어씀) 대신 run.log에 traceback을 남긴다.
                LOGGER.exception("Error: unexpected exception in making a feed '%s'", feed_name)
                failed_feed_list.append(feed_dir_path.parent.name + "/" + feed_name)

        end_time = datetime.now(timezone.utc)
        LOGGER.info("# Running time analysis")
        LOGGER.info(f"* Start time: {start_time.isoformat(timespec='seconds')}")
        LOGGER.info(f"* End time: {end_time.isoformat(timespec='seconds')}")
        LOGGER.info(f"* Elapsed time: {(end_time - start_time).total_seconds()}")

        if failed_feed_list:
            notification = Notification()
            notification.send_msg(", ".join(failed_feed_list), "Errors of FeedMaker")
        return True

    @staticmethod
    def _spawn_long_term_task(feed_dir_path: Path) -> bool:
        """장시간 작업을 단일 피드 실행(run.py <feed_dir>)으로 넘긴다.

        새 세션으로 띄워 run_all_feeds의 timeout이 process group을 종료해도 살아남게 한다.
        자식이 피드 잠금을 쥐는 동안 이후 회차의 run.py -a는 이 피드를 건너뛴다.
        """
        log_file_path = feed_dir_path / "run_long_term.log"
        try:
            with log_file_path.open("w", encoding="utf-8") as log_file:
                subprocess.Popen(  # pylint: disable=consider-using-with
                    [sys.executable, str(Path(__file__).resolve()), str(feed_dir_path)], cwd=feed_dir_path, stdin=subprocess.DEVNULL, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True
                )
        except OSError as e:
            LOGGER.error("Error: can't spawn long-term task for '%s': %r", PathUtil.short_path(feed_dir_path), e)
            return False
        LOGGER.info("spawned long-term task for '%s' in a new session", PathUtil.short_path(feed_dir_path))
        return True

    @staticmethod
    def request_stop(group_name: str, feed_name: str) -> tuple[bool, str]:
        """실행 중인 피드 작업에 중단을 요청한다.

        중단 플래그 파일을 만들어 FeedMaker가 다음 아이템 전에 멈추게 하고,
        지금 도는 하위 프로세스(download_image.py 등)는 바로 종료한다.
        """
        if FeedMakerRunner.check_running(group_name, feed_name) is not True:
            return False, "실행 중인 작업이 없습니다"
        feed_dir_path = Path(Env.get("FM_WORK_DIR")) / group_name / feed_name
        (feed_dir_path / STOP_FLAG_FILE_NAME).touch()
        # 해당 피드 디렉터리 경로를 인자로 받은 하위 프로세스만 종료한다.
        num_killed = Process.kill_process_group(re.escape(str(feed_dir_path)) + r"(\s|/|$)")
        LOGGER.info("stop requested for '%s/%s', terminated %d process(es)", group_name, feed_name, num_killed)
        return True, ""

    @staticmethod
    def check_running(group_name: str, feed_name: str) -> Optional[bool]:
        work_dir_path = Path(Env.get("FM_WORK_DIR"))
        feed_dir_path = work_dir_path / group_name / feed_name
        # FileLock은 상위 디렉터리를 만들므로, 삭제/비활성화된 피드 디렉터리가 lock 파일만 담은 채 되살아나지 않게 막는다
        if not feed_dir_path.is_dir():
            return None
        lock_file_path = feed_dir_path / ".feed_maker_runner.lock"
        try:
            logging.getLogger("filelock").setLevel(logging.ERROR)
            with FileLock(str(lock_file_path), timeout=1):
                # unlocked
                return False
        except Timeout:
            # locked
            return True
        except FileNotFoundError:
            return None


def print_usage() -> None:
    print("Usage:\t%s [-h] [-r] [-c] [ <feed path> ]")
    print("\t\t[-a]")
    print("\t\t-a: make all feeds")
    print("\t\t-h: print usage")
    print("\t\t-r: remove all files and execute clearly")
    print("\t\t-c: collection forcibly")
    print("\t\t-e: skip collection and run extraction and rss generation only")


def determine_options() -> tuple[dict[str, Any], list[str]]:
    LOGGER.debug("# determine_options()")
    do_make_all_feeds = False
    do_remove_all_files = False
    force_collection_opt = ""
    collect_only_opt = ""
    extract_only_opt = ""
    num_feeds = 0
    window_size = FeedMaker.DEFAULT_WINDOW_SIZE

    optlist, args = getopt.getopt(sys.argv[1:], "ahrceln:w:")
    for o, a in optlist:
        match o:
            case "-a":
                do_make_all_feeds = True
            case "-h":
                print_usage()
                sys.exit(0)
            case "-r":
                do_remove_all_files = True
            case "-c":
                force_collection_opt = "-c"
            case "-e":
                extract_only_opt = "-e"
            case "-l":
                collect_only_opt = "-l"
            case "-n":
                num_feeds = int(a)
            case "-w":
                window_size = int(a)

    options = {"do_make_all_feeds": do_make_all_feeds, "do_remove_all_files": do_remove_all_files, "force_collection_opt": force_collection_opt, "collect_only_opt": collect_only_opt, "extract_only_opt": extract_only_opt, "num_feeds": num_feeds, "window_size": window_size}
    return options, args


def main() -> int:
    LOGGER.debug("# main()")
    feed_dir_path: Path = Path.cwd()

    options, args = determine_options()
    if args:
        if len(args) > 1:
            print_usage()
            return -1
        # '.' 같은 상대 경로는 Path.name이 ''가 되어 DB에 빈 feed_name/group_name이 기록된다.
        # PathUtil.short_path와 같이 symlink는 풀지 않고 abspath로만 정규화한다.
        feed_dir_path = Path(os.path.abspath(args[0]))
    LOGGER.debug(options)
    LOGGER.debug(PathUtil.short_path(feed_dir_path))

    runner = FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)
    problem_manager = ProblemManager()

    if options.get("do_make_all_feeds", False):
        result = runner.make_all_feeds(options)
        HeadlessBrowser.cleanup_all_sessions()
        problem_manager.load_all()
    else:
        # 실행 결과 반영(update_feed_info)은 끝에서만 하므로, 설정 정보를 먼저 DB에 올려
        # 실행 중에도 problems/management 탭에서 피드를 찾을 수 있게 한다.
        # DB 갱신 실패가 피드 생성을 막으면 안 되므로 예외는 경고로만 남긴다.
        try:
            problem_manager.feed_manager.add_config_info(feed_dir_path)
        except Exception as e:  # pylint: disable=broad-exception-caught
            LOGGER.warning("Failed to sync config info of '%s' before run: %r", PathUtil.short_path(feed_dir_path), e)

        config = Config(feed_dir_path=feed_dir_path)
        collection_conf = config.get_collection_configs()

        # -e(extract_only)가 지정되면 is_completed 피드라도 강제 collection 단계를
        # 건너뛰고 곧바로 window 추출만 진행한다.
        if collection_conf.get("is_completed", False) and not options.get("collect_only_opt", "") and not options.get("extract_only_opt", ""):
            temp_options = {"force_collection_opt": "-c"}
            LOGGER.info("run with force_collection_opt '-c'")
            result = runner.make_single_feed(feed_dir_path, temp_options)
            if not result:
                return -1
        result = runner.make_single_feed(feed_dir_path, options)
        problem_manager.update_feed_info(feed_dir_path)

    LOGGER.info("# Checking problems and making report")

    return 0 if result else -1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
