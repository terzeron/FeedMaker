#!/usr/bin/env python


import os
import sys
import re
import time
import json
from datetime import datetime
import random
import logging
import logging.config
import concurrent.futures
import getopt
from typing import Dict, Tuple, List, Any, Set
from feed_maker_util import Config, exec_cmd, send_error_msg, kill_process_group
from feed_maker import FeedMaker


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


def execute_job(feed_dir: str, list_archiving_period: int) -> bool:
    LOGGER.debug("execute_job(feed_dir='%s', list_archiving_period=%d)", feed_dir, list_archiving_period)
    print(feed_dir)
    os.chdir(feed_dir)
    if os.path.isdir(feed_dir) and os.path.isfile(os.path.join(feed_dir, "conf.xml")):
        do_exist_old_list_file = False
        if os.path.isdir("newlist"):
            for list_file in os.listdir("newlist"):
                if os.path.isfile(list_file):
                    if os.stat(os.path.join("newlist", list_file)).st_mtime + list_archiving_period * 24 * 60 * 60 < time.time():
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


def print_usage() -> None:
    print("Usage:\t%s [-h] [-r] [-c] [ <feed path> ]")
    print("\t\t[-a]")
    print("\t\t-a: make all feeds")
    print("\t\t-h: print usage")
    print("\t\t-r: remove all files and execute clearly")
    print("\t\t-c: collection forcibly")


def determine_options() -> Tuple[Dict[str, Any], List[str]]:
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


def get_img_set_in_img_dir(img_dir: str) -> Set[str]:
    LOGGER.debug("get_img_set_in_img_dir(img_dir='%s')", img_dir)
    img_set_in_img_dir = set([])
    if os.path.isdir(img_dir):
        for file in os.listdir(img_dir):
            if os.path.isfile(os.path.join(img_dir, file)):
                img_set_in_img_dir.add(file)
    return img_set_in_img_dir


def remove_log_files(file_list: List[str]) -> None:
    LOGGER.debug("remove_log_files(file_list=%r)", file_list)
    for file in file_list:
        if os.path.isfile(file):
            os.remove(file)


def remove_image_files_with_zero_size(img_dir: str) -> None:
    LOGGER.debug("remove_image_files_with_zero_size(img_dir='%s')", img_dir)
    for path, _, files in os.walk(img_dir):
        for file in files:
            file_path = os.path.join(path, file)
            if os.path.isfile(file_path):
                if os.stat(file_path).st_size == 0:
                    os.remove(file_path)


def remove_all_files(rss_file_name: str) -> None:
    LOGGER.debug("remove_all_files(rss_file_name='%s')", rss_file_name)
    for file in os.listdir("html"):
        file_path = os.path.join("html", file)
        if os.path.isfile(file_path):
            os.remove(file_path)
    for file in os.listdir("newlist"):
        file_path = os.path.join("newlist", file)
        if os.path.isfile(file_path):
            os.remove(file_path)
    for file in ["start_idx.txt", rss_file_name, rss_file_name + ".old", "error.log", "collector.error.log", "run.log"]:
        if os.path.isfile(file):
            os.remove(file)


def remove_old_html_files(archiving_period: int) -> None:
    LOGGER.debug("remove_old_html_files(archiving_period=%d)", archiving_period)
    if os.path.exists("html"):
        LOGGER.info("deleting older html files than %d days", archiving_period)
        # deleting older html files than archiving_period
        for file in os.listdir("html"):
            file_path = os.path.join("html", file)
            if os.path.isfile(file_path) and os.path.exists(file_path) and os.stat(file_path).st_ctime + archiving_period * 24 * 60 * 60 < time.time():
                os.remove(file_path)
                LOGGER.info(file_path)


def remove_html_files_without_cached_image_files(img_dir: str) -> None:
    LOGGER.debug("remove_html_files_without_cached_image_files(img_dir='%s')", img_dir)
    img_set_in_img_dir = get_img_set_in_img_dir(img_dir)

    if os.path.isdir("html"):
        img_html_map = {}
        for file in os.listdir("html"):
            file_path = os.path.join("html", file)
            if os.path.isfile(file_path):
                with open(file_path) as f:
                    try:
                        for line in f:
                            m = re.search(r'<img src=[\"\']https?://terzeron\.com/xml/img/[^/]+/(?P<img>\S+)[\"\']', line)
                            if m:
                                # 실제로 다운로드되어 있는지 확인
                                img_file = m.group("img")
                                img_html_map[img_file] = file
                    except UnicodeDecodeError as e:
                        LOGGER.error("Unicode decode error in '%s'", file_path)
                        raise e

        for img_file in set(img_html_map.keys()) - img_set_in_img_dir:
            html_file = img_html_map[img_file]
            html_file_path = os.path.join("html", html_file)
            if os.path.isfile(html_file_path):
                LOGGER.info("deleting html file '%s' for missing image file '%s'", html_file, img_file)
                os.remove(html_file_path)


def remove_temporary_files() -> None:
    LOGGER.debug("remove_temporary_files()")
    for file in ["nohup.out", "temp.html", "x.html"]:
        if os.path.isfile(file):
            os.remove(file)


def remove_unused_img_files(rss_file_name: str, img_dir: str) -> None:
    LOGGER.debug("remove_unused_img_files(rss_file_name='%s', img_dir='%s')", rss_file_name, img_dir)
    if not os.path.isfile(rss_file_name):
        return

    img_set_in_img_dir = get_img_set_in_img_dir(img_dir)
    img_set_in_xml_file = set([])

    # rss 파일 내부의 이미지 파일을 모아서
    with open(rss_file_name) as f:
        for line in f:
            m = re.search(r'img src=[\"\']https?://terzeron\.com/xml/img/[^/]+/(?P<img>[^\"\']+)[\"\']', line)
            if m:
                img_file = m.group("img")
                img_set_in_xml_file.add(img_file)

    # 이미지 디렉토리에만 존재하는 이미지 파일을 모두 삭제
    for img_file in sorted(img_set_in_img_dir - img_set_in_xml_file):
        LOGGER.info("deleting unused image file '%s' from '%s'", img_file, img_dir)
        img_file_path = os.path.join(img_dir, img_file)
        os.remove(img_file_path)


def make_single_feed(feed_name: str, img_dir: str, archiving_period: int, options: Dict[str, Any]) -> bool:
    LOGGER.info(feed_name)
    LOGGER.debug("make_single_feed(feed_name='%s', img_dir='%s', archiving_period=%d, options=%r)", feed_name, img_dir, archiving_period, options)
    rss_file_name = feed_name + ".xml"

    config = Config()
    collection_conf = config.get_collection_configs()

    do_remove_all_files = options["do_remove_all_files"]
    force_collection_opt = options["force_collection_opt"]
    collect_only_opt = options["collect_only_opt"]

    if do_remove_all_files:
        # -r 옵션 사용하면 html 디렉토리의 파일들, newlist 디렉토리의 파일들, 각종 로그 파일, feed xml 파일들을 삭제
        remove_all_files(rss_file_name)

    # 다운로드되어 있어야 하는 이미지가 없는 html 파일 삭제
    remove_html_files_without_cached_image_files(img_dir)

    # make_feed.py 실행하여 feed 파일 생성
    LOGGER.info("making feed file '%s'", rss_file_name)
    feed_maker = FeedMaker(force_collection_opt, collect_only_opt, rss_file_name)
    result = feed_maker.make()

    # 불필요한 파일 삭제
    remove_temporary_files()

    return result


def make_all_feeds(feed_maker_cwd: str, log_dir: str, img_dir: str) -> bool:
    LOGGER.debug("make_all_feeds(feed_maker_cwd='%s', log_dir='%s', img_dir='%s')", feed_maker_cwd, log_dir, img_dir)
    runlog = "run.log"
    list_archiving_period = 3

    LOGGER.info("deleting log files")
    remove_log_files([runlog])
    LOGGER.info("deleting image files with zero size")
    remove_image_files_with_zero_size(img_dir)

    LOGGER.info("executing feed generation")
    feed_dir_path_list: List[str] = []
    for path, dirs, _ in os.walk(feed_maker_cwd):
        if "/_" not in path:
            for d in dirs:
                dir_path = os.path.join(path, d)
                if not d.startswith("_") and os.path.isdir(dir_path) and os.path.isfile(os.path.join(dir_path, "conf.xml")):
                    feed_dir_path_list.append(dir_path)

    random.shuffle(feed_dir_path_list)
    failed_feed_list: List[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_to_feed = {executor.submit(execute_job, feed_dir_path, list_archiving_period): feed_dir_path for feed_dir_path in feed_dir_path_list}
        for future in concurrent.futures.as_completed(future_to_feed):
            feed = future_to_feed[future]
            try:
                result = future.result()
                if not result:
                    LOGGER.warning("can't execute a job for feed '%s', %s", feed, result)
                    failed_feed_list.append(os.path.basename(feed))
            except Exception as e:
                LOGGER.warning("can't execute a job for feed '%s', %s", feed, e)
                failed_feed_list.append(os.path.basename(feed))

    # read global config
    access_token: str = ""
    receiver_id: str = ""
    with open(os.path.join(os.environ["FEED_MAKER_HOME_DIR"], "bin", "global_config.json"), "r") as f:
        global_config: Dict[str, Any] = json.load(f)
        access_token = global_config["access_token"]
        receiver_id = global_config["receiver_id"]

    if len(failed_feed_list) > 0:
        send_error_msg(", ".join(failed_feed_list), access_token, receiver_id)

    cmd = "find_problems.sh > %s/find_problems.log 2>&1" % log_dir
    _, error = exec_cmd(cmd)
    if error:
        send_error_msg(error, access_token, receiver_id)
    return not error


def main() -> int:
    archiving_period = 30

    start_ts = time.time()
    print(datetime.now().astimezone().isoformat(timespec="seconds"))

    options, args = determine_options()
    if args:
        if len(args) > 1:
            print_usage()
            return -1
        os.chdir(args[0])

    if options["do_make_all_feeds"]:
        feed_maker_cwd = os.getenv("FEED_MAKER_WORK_DIR")
        if not feed_maker_cwd:
            LOGGER.error("can't get environment variable 'FEED_MAKER_WORK_DIR'")
            return -1
        log_dir = os.path.join(feed_maker_cwd, "logs")
        www_feeds_dir = os.getenv("FEED_MAKER_WWW_FEEDS_DIR")
        if not www_feeds_dir:
            LOGGER.error("can't get environment variable 'FEED_MAKER_WWW_FEEDS_DIR'")
            return -1
        img_dir = os.path.join(www_feeds_dir, "img")
        result = make_all_feeds(feed_maker_cwd, log_dir, img_dir)
        kill_process_group("chromedriver")
    else:
        feed_name = os.path.basename(os.getcwd())
        www_feeds_dir = os.getenv("FEED_MAKER_WWW_FEEDS_DIR")
        if not www_feeds_dir:
            LOGGER.error("can't get environment variable 'FEED_MAKER_WWW_FEEDS_DIR'")
            return -1
        img_dir = os.path.join(www_feeds_dir, "img", feed_name)
        result = make_single_feed(feed_name, img_dir, archiving_period, options)

    end_ts = time.time()
    print(datetime.now().astimezone().isoformat(timespec="seconds"))
    LOGGER.info("elapse=%f", (end_ts - start_ts))

    return 0 if result else -1


if __name__ == "__main__":
    sys.exit(main())
