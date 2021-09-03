#!/usr/bin/env python


import os
import sys
import re
from datetime import datetime, timedelta
import random
import logging
import logging.config
import concurrent.futures
import getopt
from pathlib import Path
from typing import Dict, Tuple, List, Any, Set
from feed_maker_util import Config, exec_cmd, send_error_msg
from feed_maker import FeedMaker
from problem_checker import ProblemChecker


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class FeedMakerRunner:
    def __init__(self, html_archiving_period: int, list_archiving_period: int):
        LOGGER.debug("# __init__(html_archiving_period=%d, list_archiving_period=%d", html_archiving_period, list_archiving_period)
        self.html_archiving_period = html_archiving_period
        self.list_archiving_period = list_archiving_period
        self.work_dir_path = Path(os.environ["FEED_MAKER_WORK_DIR"])
        if not self.work_dir_path.is_dir():
            LOGGER.error("can't find work directory '%s'", self.work_dir_path)
        self.img_dir_path = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"]) / "img"
        if not self.img_dir_path.is_dir():
            LOGGER.error("can't find image directory '%s'", self.img_dir_path)


    def execute_job(self, feed_dir_path: Path) -> bool:
        LOGGER.debug("# execute_job(feed_dir_path='%s')", feed_dir_path)
        LOGGER.info("* %s", feed_dir_path)
        os.chdir(feed_dir_path)
        conf_file_path = feed_dir_path / "conf.json"
        if conf_file_path.is_file():
            do_exist_old_list_file = False
            list_dir = feed_dir_path / "newlist"
            if list_dir.is_dir():
                for list_file in list_dir.iterdir():
                    if list_file.is_file():
                        list_file_path = feed_dir_path / "newlist" / list_file
                        mtime = datetime.fromtimestamp(list_file_path.stat().st_mtime)
                        if mtime + timedelta(days=self.list_archiving_period) < datetime.now():
                            do_exist_old_list_file = True
                        break

            config = Config()
            collection_conf = config.get_collection_configs()
            if collection_conf["is_completed"] and not do_exist_old_list_file:
                cmd = "run.py -c"
                _, error = exec_cmd(cmd)
                if error:
                    LOGGER.warning("can't execute command '%s', %s", cmd, error)
                    return False

            cmd = "run.py"
            _, error = exec_cmd(cmd)
            if error:
                LOGGER.warning("can't execute command '%s', %s", cmd, error)
                return False
        return True


    @staticmethod
    def get_img_set_in_img_dir(feed_img_dir_path: Path) -> Set[str]:
        LOGGER.debug("# get_img_set_in_img_dir()")
        img_set_in_img_dir = set([])
        if feed_img_dir_path.is_dir():
            for img_file_path in feed_img_dir_path.iterdir():
                img_set_in_img_dir.add(img_file_path.name)
        return img_set_in_img_dir


    @staticmethod
    def remove_image_files_with_zero_size(feed_img_dir_path: Path) -> None:
        LOGGER.debug("# remove_image_files_with_zero_size()")
        LOGGER.info("# deleting image files with zero size")
        if feed_img_dir_path.is_dir():
            for img_file_path in feed_img_dir_path.iterdir():
                if img_file_path.is_file():
                    if img_file_path.stat().st_size == 0:
                        LOGGER.info("* %s", img_file_path)
                        img_file_path.unlink()


    @staticmethod
    def remove_all_files(feed_dir_path: Path, rss_file_path: Path) -> None:
        LOGGER.debug("# remove_all_files(feed_dir_path='%s', rss_file_path='%s')", feed_dir_path, rss_file_path)
        LOGGER.info("# deleting all files (html files, list files, rss file, various temporary files")
        for html_file_path in (feed_dir_path / "html").iterdir():
            if html_file_path.is_file():
                LOGGER.info("* %s", html_file_path)
                html_file_path.unlink()
        for list_file_path in (feed_dir_path / "newlist").iterdir():
            if list_file_path.is_file():
                LOGGER.info("* %s", list_file_path)
                list_file_path.unlink()
        for file_path in [feed_dir_path / "start_idx.txt", rss_file_path, Path(str(rss_file_path) + ".old"), feed_dir_path / "run.log"]:
            if file_path.is_file():
                LOGGER.info("* %s", file_path)
                file_path.unlink()


    def remove_old_html_files(self, feed_dir_path: Path) -> None:
        LOGGER.debug("# remove_old_html_files(feed_dir_path='%s')", feed_dir_path)
        LOGGER.info("# deleting old html files")
        html_dir_path = feed_dir_path / "html"
        if html_dir_path.is_dir():
            # deleting older html files than archiving_period
            for html_file_path in html_dir_path.iterdir():
                ctime = datetime.fromtimestamp(html_file_path.stat().st_ctime)
                if html_file_path.is_file() and ctime + timedelta(days=self.html_archiving_period) < datetime.now():
                    LOGGER.info("* %s", html_file_path)
                    html_file_path.unlink()


    def remove_html_files_without_cached_image_files(self, feed_dir_path: Path, feed_img_dir_path: Path) -> None:
        LOGGER.debug("# remove_html_files_without_cached_image_files(feed_dir_path='%s', feed_img_dir_path='%s')", feed_dir_path, feed_img_dir_path)
        LOGGER.info("# deleting html files without cached image files")
        img_set_in_img_dir: Set[str] = self.get_img_set_in_img_dir(feed_img_dir_path)

        html_dir_path = feed_dir_path / "html"
        if html_dir_path.is_dir():
            img_html_map = {}
            for html_file_path in html_dir_path.iterdir():
                if html_file_path.is_file():
                    with open(html_file_path) as f:
                        try:
                            for line in f:
                                m = re.search(r'<img src=[\"\']https?://terzeron\.com/xml/img/[^/]+/(?P<img>\S+)[\"\']', line)
                                if m:
                                    # 실제로 다운로드되어 있는지 확인
                                    img_file = m.group("img")
                                    img_html_map[img_file] = html_file_path.name
                        except UnicodeDecodeError as e:
                            LOGGER.error("Unicode decode error in '%s'", html_file_path.name)
                            raise e

            for img_file in set(img_html_map.keys()) - img_set_in_img_dir:
                html_file = img_html_map[img_file]
                html_file_path = html_dir_path / html_file
                if html_file_path.is_file():
                    LOGGER.info("* '%s' (due to '%s')", html_file, img_file)
                    html_file_path.unlink()


    @staticmethod
    def remove_temporary_files(feed_dir_path: Path) -> None:
        LOGGER.debug("# remove_temporary_files(feed_dir_path='%s')", feed_dir_path)
        LOGGER.info("# deleting temporary files")
        for file in ["nohup.out", "temp.html", "x.html"]:
            file_path = feed_dir_path / file
            if file_path.is_file():
                LOGGER.info("* %s", file_path)
                file_path.unlink()


    def make_single_feed(self, feed_dir_path: Path, options: Dict[str, Any]) -> bool:
        LOGGER.debug("# make_single_feed(feed_dir_path='%s', options=%r)", feed_dir_path, options)

        start_time = datetime.now()
        os.chdir(feed_dir_path)
        feed_name = feed_dir_path.name
        LOGGER.info("* %s", (feed_dir_path.parent.name + "/" + feed_name))
        rss_file_path = feed_dir_path / (feed_name + ".xml")
        feed_img_dir_path = self.img_dir_path / feed_name

        do_remove_all_files = options.get("do_remove_all_files", False)
        force_collection_opt = options.get("force_collection_opt", "")
        collect_only_opt = options.get("collect_only_opt", "")

        if do_remove_all_files:
            # -r 옵션 사용하면 html 디렉토리의 파일들, newlist 디렉토리의 파일들, 각종 로그 파일, feed xml 파일들을 삭제
            self.remove_all_files(feed_dir_path, rss_file_path)
        # 다운로드되어 있어야 하는 이미지가 없는 html 파일 삭제
        self.remove_html_files_without_cached_image_files(feed_dir_path, feed_img_dir_path)
        # 0 byte 이미지 파일 삭제
        self.remove_image_files_with_zero_size(feed_img_dir_path)

        # make_feed.py 실행하여 feed 파일 생성
        LOGGER.info("* making feed file '%s'", rss_file_path)
        feed_maker = FeedMaker(force_collection_opt, collect_only_opt, rss_file_path.name)
        result = feed_maker.make()

        # 불필요한 파일 삭제
        self.remove_temporary_files(feed_dir_path)

        end_time = datetime.now()
        LOGGER.info("# Running time analysis")
        LOGGER.info("* Start time: %s", start_time.astimezone().isoformat(timespec="seconds"))
        LOGGER.info("* End time: %s", end_time.astimezone().isoformat(timespec="seconds"))
        LOGGER.info("* Elapsed time: %.2f", (end_time - start_time).total_seconds())

        return result


    def make_all_feeds(self) -> bool:
        LOGGER.debug("# make_all_feeds()")

        start_time = datetime.now()

        LOGGER.info("# deleting log file")
        runlog_path = self.work_dir_path / "run.log"
        runlog_path.unlink()

        LOGGER.info("# generating feeds")
        feed_dir_path_list: List[Path] = []
        for group_dir_path in self.work_dir_path.iterdir():
            if not group_dir_path.name.startswith("_") and group_dir_path.is_dir():
                for feed_dir_path in group_dir_path.iterdir():
                    conf_file_path = feed_dir_path / "conf.json"
                    if not feed_dir_path.name.startswith("_") and feed_dir_path.is_dir() and conf_file_path.is_file():
                        feed_dir_path_list.append(feed_dir_path)

        random.shuffle(feed_dir_path_list)
        failed_feed_list: List[str] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_to_feed = {executor.submit(self.execute_job, feed_dir_path): feed_dir_path for feed_dir_path in feed_dir_path_list}
            for future in concurrent.futures.as_completed(future_to_feed):
                feed_dir_path = future_to_feed[future]
                feed_name = feed_dir_path.name
                try:
                    result = future.result()
                    if not result:
                        LOGGER.warning("can't execute a job for feed '%s', %s", feed_name, result)
                        failed_feed_list.append(feed_dir_path.parent.name + "/" + feed_name)
                except Exception as e:
                    LOGGER.warning("can't execute a job for feed '%s', %s", feed_name, e)
                    failed_feed_list.append(feed_dir_path.parent.name + "/" + feed_name)

        end_time = datetime.now()
        LOGGER.info("# Running time analysis")
        LOGGER.info("* Start time: %s", start_time.astimezone().isoformat(timespec="seconds"))
        LOGGER.info("* End time: %s", end_time.astimezone().isoformat(timespec="seconds"))
        LOGGER.info("* Elapsed time: %.2f", (end_time - start_time).total_seconds())

        if len(failed_feed_list) > 0:
            send_error_msg(", ".join(failed_feed_list), subject="Errors of FeedMaker")

        LOGGER.info("# checking problems and making report")
        checker = ProblemChecker()
        checker.load()
        return True


def print_usage() -> None:
    print("Usage:\t%s [-h] [-r] [-c] [ <feed path> ]")
    print("\t\t[-a]")
    print("\t\t-a: make all feeds")
    print("\t\t-h: print usage")
    print("\t\t-r: remove all files and execute clearly")
    print("\t\t-c: collection forcibly")


def determine_options() -> Tuple[Dict[str, Any], List[str]]:
    LOGGER.debug("# determine_options()")
    do_make_all_feeds = False
    do_remove_all_files = False
    force_collection_opt = ""
    collect_only_opt = ""

    optlist, args = getopt.getopt(sys.argv[1:], "ahrcl")
    for o, _ in optlist:
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

    options = {
        "do_make_all_feeds": do_make_all_feeds,
        "do_remove_all_files": do_remove_all_files,
        "force_collection_opt": force_collection_opt,
        "collect_only_opt": collect_only_opt,
    }
    return options, args


def main() -> int:
    LOGGER.debug("# main()")

    options, args = determine_options()
    if args:
        if len(args) > 1:
            print_usage()
            return -1
        feed_dir_path = sys.argv[0]
    else:
        feed_dir_path = Path.cwd()
    runner = FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)
    if options["do_make_all_feeds"]:
        result = runner.make_all_feeds()
    else:
        result = runner.make_single_feed(feed_dir_path, options)

    return 0 if result else -1


if __name__ == "__main__":
    sys.exit(main())
