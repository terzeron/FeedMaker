#!/usr/bin/env python


import sys
from datetime import datetime, timedelta, timezone
import random
import logging.config
import getopt
from pathlib import Path
from typing import Any, Optional
from filelock import FileLock, Timeout
from bin.feed_maker_util import Config, Process, PathUtil, FileManager, NotFoundConfigItemError, Env
from bin.notification import Notification
from bin.feed_maker import FeedMaker
from bin.problem_manager import ProblemManager

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class FeedMakerRunner:
    def __init__(self, html_archiving_period: int, list_archiving_period: int):
        LOGGER.debug(f"# FeedMakerRunner(html_archiving_period={html_archiving_period}, list_archiving_period={list_archiving_period})")
        self.html_archiving_period = html_archiving_period
        self.list_archiving_period = list_archiving_period
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

        lock_file_path = feed_dir_path / ".feed_maker_runner.lock"
        if lock_file_path.is_file():
            st = lock_file_path.stat()
            if datetime.fromtimestamp(st.st_mtime, timezone.utc) < datetime.now(timezone.utc) - timedelta(days=1):
                LOGGER.debug("remove old lock file '%s'", PathUtil.short_path(lock_file_path))
                lock_file_path.unlink(missing_ok=True)

        try:
            logging.getLogger("filelock").setLevel(logging.ERROR)
            with FileLock(str(lock_file_path), timeout=5):
                feed_name = feed_dir_path.name
                LOGGER.info("* %s", PathUtil.short_path(feed_dir_path))
                rss_file_path = feed_dir_path / f"{feed_name}.xml"
                feed_img_dir_path = self.img_dir_path / feed_name

                do_remove_all_files = options.get("do_remove_all_files", False)
                force_collection_opt = options.get("force_collection_opt", False)
                collect_only_opt = options.get("collect_only_opt", False)
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
                feed_maker = FeedMaker(feed_dir_path=feed_dir_path, do_collect_by_force=force_collection_opt, do_collect_only=collect_only_opt, rss_file_path=rss_file_path, window_size=window_size)
                result = feed_maker.make()

                # 불필요한 파일 삭제
                FileManager.remove_temporary_files(feed_dir_path)
        except Timeout:
            LOGGER.error("can't run multiple feed makers concurrently")
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
                    conf_file_path = feed_dir_path / "conf.json"
                    if not feed_dir_path.name.startswith("_") and feed_dir_path.is_dir() and conf_file_path.is_file():
                        feed_dir_path_list.append(feed_dir_path)

        random.shuffle(feed_dir_path_list)
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

            if collection_conf.get("is_completed", False):
                result = self.make_single_feed(feed_dir_path, options={"force_collection_opt": "-c"})
                if not result:
                    LOGGER.warning(f"Warning: can't make a feed '{feed_name} with all completed articles, {result}")
                    failed_feed_list.append(feed_dir_path.parent.name + "/" + feed_name)
                    continue

            result = self.make_single_feed(feed_dir_path, options={})
            if not result:
                LOGGER.warning(f"Warning: can't make a feed '{feed_name}' with recent articles, {result}")
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
    def check_running(group_name: str, feed_name: str) -> Optional[bool]:
        work_dir_path = Path(Env.get("FM_WORK_DIR"))
        lock_file_path = work_dir_path / group_name / feed_name / ".feed_maker_runner.lock"
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


def determine_options() -> tuple[dict[str, Any], list[str]]:
    LOGGER.debug("# determine_options()")
    do_make_all_feeds = False
    do_remove_all_files = False
    force_collection_opt = ""
    collect_only_opt = ""
    num_feeds = 0
    window_size = FeedMaker.DEFAULT_WINDOW_SIZE

    optlist, args = getopt.getopt(sys.argv[1:], "ahrcln:w:")
    for o, a in optlist:
        if o == "-a":
            do_make_all_feeds = True
        elif o == "-h":
            print_usage()
            sys.exit(0)
        elif o == "-r":
            do_remove_all_files = True
        elif o == "-c":
            force_collection_opt = "-c"
        elif o == "-l":
            collect_only_opt = "-l"
        elif o == "-n":
            num_feeds = int(a)
        elif o == "-w":
            window_size = int(a)

    options = {
        "do_make_all_feeds": do_make_all_feeds,
        "do_remove_all_files": do_remove_all_files,
        "force_collection_opt": force_collection_opt,
        "collect_only_opt": collect_only_opt,
        "num_feeds": num_feeds,
        "window_size": window_size
    }
    return options, args


def main() -> int:
    LOGGER.debug("# main()")
    feed_dir_path: Path = Path.cwd()

    options, args = determine_options()
    if args:
        if len(args) > 1:
            print_usage()
            return -1
        feed_dir_path = Path(sys.argv[0])
    LOGGER.debug(options)
    LOGGER.debug(PathUtil.short_path(feed_dir_path))

    runner = FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)
    problem_manager = ProblemManager()

    if options.get("do_make_all_feeds", False):
        result = runner.make_all_feeds(options)
        Process.kill_process_group(r"chromedriver")
        problem_manager.load_all()
    else:
        config = Config(feed_dir_path=feed_dir_path)
        collection_conf = config.get_collection_configs()

        if collection_conf.get("is_completed", False) and not options.get("collect_only_opt", ""):
            temp_options = {"force_collection_opt": "-c"}
            LOGGER.info("run with force_collection_opt '-c'")
            result = runner.make_single_feed(feed_dir_path, temp_options)
            if not result:
                return -1
        result = runner.make_single_feed(feed_dir_path, options)
        problem_manager.update_feed_info(feed_dir_path)

    LOGGER.info("# Checking problems and making report")

    return 0 if result else -1


if __name__ == "__main__":
    sys.exit(main())
