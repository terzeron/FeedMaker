#!/usr/bin/env python


import os
import sys
import re
import time
import random
import concurrent.futures
import getopt
from logger import Logger
from typing import Dict, Tuple, List, Any, Set
import feedmakerutil
from feedmakerutil import Config


logger = Logger("run.py")


def send_error_msg(msg: str) -> bool:
    cmd = " ".join(('''
    curl -s -X POST
         -H 'Content-Type:application/json'
         -H 'Authorization: Bearer gdrao6YPr50SCzwqb7By40yqwOotDdo9a/+nGYmFkL3xMUA1P3OPJO7aKlNTnN12tz0BzJ5C/TX+gTZiIUFeXIa8X1reFHNXPcJ/hlZysxTkBOkSzbEI/TUbBVDjves+lDqDwVicBisE3/MelN5QrAdB04t89/1O/w1cDnyilFU='
    -d '{
        "to": "U52aa71b262aa645ba5f3e4786949ef23",
        "messages":[
            {
                "type": "text",
                "text": "%s"
            }
        ]
    }' https://api.line.me/v2/bot/message/push
    ''' % msg[:1999]).split("\n"))
    print(cmd)
    result, error = feedmakerutil.exec_cmd(cmd)
    if error:
        logger.err(error)
        return False
    logger.info(result)
    return True


def execute_job(feed_dir: str, runlog: str, errorlog: str, list_archiving_period: int) -> bool:
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
            result, error = feedmakerutil.exec_cmd(cmd)
            if error:
                return False
        
        cmd = "run.py"
        result, error = feedmakerutil.exec_cmd(cmd)
        if error:
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

    optlist, args = getopt.getopt(sys.argv[1:], "ahrc")
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

    options = {
        "do_make_all_feeds": do_make_all_feeds,
        "do_remove_all_files": do_remove_all_files,
        "force_collection_opt": force_collection_opt,
    }
    return options, args


def get_img_set_in_img_dir(img_dir: str) -> Set[str]:
    img_set_in_img_dir = set([])
    if os.path.isdir(img_dir):
        for file in os.listdir(img_dir):
            if os.path.isfile(os.path.join(img_dir, file)):
                img_set_in_img_dir.add(file)
    return img_set_in_img_dir


def remove_log_files(file_list: List[str]) -> None:
    for file in file_list:
        if os.path.isfile(file):
            os.remove(file)


def remove_image_files_old_and_with_zero_size(img_dir: str, max_archiving_period: int) -> None:
    for path, dirs, files in os.walk(img_dir):
        for file in files:
            file_path = os.path.join(path, file)
            if os.path.isfile(file_path):
                if os.stat(file_path).st_size == 0 or os.stat(file_path).st_mtime + max_archiving_period * 24 * 60 * 60 < time.time():
                    os.remove(file_path)

            
def remove_all_files(feed_xml_file: str) -> None:
    for file in os.listdir("html"):
        file_path = os.path.join("html", file)
        if os.path.isfile(file_path):
            os.remove(file_path)
    for file in os.listdir("newlist"):
        file_path = os.path.join("newlist", file)
        if os.path.isfile(file_path):
            os.remove(file_path)
    for file in ["start_idx.txt", feed_xml_file, feed_xml_file + ".old", "error.log", "collector.error.log", "run.log"]:
        if os.path.isfile(file):
            os.remove(file)


def remove_old_html_files(archiving_period: int) -> None:
    if os.path.exists("html"):
        logger.info("deleting older html files than 30 days")
        # deleting older html files than archiving_period
        for file in os.listdir("html"):
            file_path = os.path.join("html", file)
            if os.path.isfile(file_path) and os.path.exists(file_path) and os.stat(file_path).st_ctime + archiving_period * 24 * 60 * 60 < time.time():
                os.remove(file_path)
                logger.info(file_path)


def remove_html_files_without_cached_image_files(img_dir: str) -> None:
    img_set_in_img_dir = get_img_set_in_img_dir(img_dir)

    if os.path.isdir("html"):
        img_html_map = {}
        for file in os.listdir("html"):
            file_path = os.path.join("html", file)
            if os.path.isfile(file_path):
                with open(file_path) as f:
                    for line in f:
                        m = re.search(r'<img src=[\"\']https?://terzeron\.net/xml/img/[^/]+/(?P<img>.+\.jpg)[\"\']', line)
                        if m:
                            # 실제로 다운로드되어 있는지 확인
                            img_file = m.group("img")
                            img_html_map[img_file] = file

        for img_file in set(img_html_map.keys()) - img_set_in_img_dir:
            html_file = img_html_map[img_file]
            html_file_path = os.path.join("html", html_file)
            if os.path.isfile(html_file_path):
                logger.info("deleting html file '%s' for missing image file '%s'" % (html_file, img_file))
                os.remove(html_file_path)


def remove_temporary_files() -> None:
    for file in ["cookie.txt", "nohup.out"]:
        if os.path.isfile(file):
            os.remove(file)


def remove_unused_img_files(feed_xml_file: str, img_dir: str) -> None:
    if not os.path.isfile(feed_xml_file):
        return
    
    img_set_in_img_dir = get_img_set_in_img_dir(img_dir)
    img_set_in_xml_file = set([])

    with open(feed_xml_file) as f:
        for line in f:
            m = re.search(r'img src=[\"\']https?://terzeron\.net/xml/img/[^/]+/(?P<img>[^\'\"]+\.jpg)[\"\']', line)
            if m:
                img_file = m.group("img")
                img_set_in_xml_file.add(img_file)

    for img_file in img_set_in_img_dir - img_set_in_xml_file:
        logger.info("deleting unused image file '%s'" % img_file)
        img_file_path = os.path.join(img_dir, img_file)
        os.remove(img_file_path)


def make_single_feed(feed_name: str, img_dir: str, archiving_period: int, do_remove_all_files: bool, force_collection_opt: str) -> bool:
    logger.info(feed_name)
    feed_xml_file = feed_name + ".xml"

    config = Config()
    collection_conf = config.get_collection_configs()

    if do_remove_all_files:
        # -r 옵션 사용하면 html 디렉토리의 파일들, newlist 디렉토리의 파일들, 각종 로그 파일, feed xml 파일들을 삭제
        remove_all_files(feed_xml_file)
    else:
        # archiving_period일 이상 오래된 html 파일을 삭제
        remove_old_html_files(archiving_period)

    # 다운로드되어 있어야 하는 이미지가 없는 html 파일 삭제
    remove_html_files_without_cached_image_files(img_dir)

    # make_feed.py 실행하여 feed 파일 생성
    logger.info("making feed file '%s'" % feed_xml_file)
    cmd = "make_feed.py %s %s" % (force_collection_opt, feed_xml_file)
    logger.info(cmd)
    result, error = feedmakerutil.exec_cmd(cmd)

    # 불필요한 파일 삭제
    remove_temporary_files()

    # 진행 중 피드인 경우, 파일에 포함되지 않은 이미지 삭제
    if not collection_conf["is_completed"]:
        remove_unused_img_files(feed_xml_file, img_dir)

    if error:
        logger.err(error)
        return False
    print(result)
    return True


def make_all_feeds(feed_maker_cwd: str, log_dir: str, img_dir: str) -> bool:
    runlog = "run.log"
    errorlog = "error.log"
    collectorerrorlog = "collector.error.log"
    max_archiving_period = 60
    list_archiving_period = 3

    logger.info("deleting log files")
    remove_log_files([runlog, errorlog, collectorerrorlog])
    logger.info("deleting old image files and image files with zero size")
    remove_image_files_old_and_with_zero_size(img_dir, max_archiving_period)

    logger.info("executing feed generation")
    feed_dir_path_list: List[str] = []
    for path, dirs, files in os.walk(feed_maker_cwd):
        if "/_" not in path:
            for d in dirs:
                dir_path = os.path.join(path, d)
                if not d.startswith("_") and os.path.isdir(dir_path) and os.path.isfile(os.path.join(dir_path, "conf.xml")):
                    feed_dir_path_list.append(dir_path)

    random.shuffle(feed_dir_path_list)
    failed_feed_list: List[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_feed = {executor.submit(execute_job, feed_dir_path, runlog, errorlog, list_archiving_period): feed_dir_path for feed_dir_path in feed_dir_path_list}
        for future in concurrent.futures.as_completed(future_to_feed):
            feed = future_to_feed[future]
            try:
                result = future.result()
                if not result:
                    print(feed, result)
                    failed_feed_list.append(os.path.basename(feed))
            except Exception as e:
                print(feed, e)
                failed_feed_list.append(os.path.basename(feed))

    if len(failed_feed_list) > 0:
        send_error_msg(", ".join(failed_feed_list))

    cmd = "find_problems.sh > %s/find_problems.log 2>&1" % log_dir
    res, error = feedmakerutil.exec_cmd(cmd)
    if error:
        send_error_msg(error)
    return not error


def main() -> int:
    archiving_period = 30

    start_ts = time.time()
    print(time.ctime(start_ts))

    options, args = determine_options()
    if args:
        if len(args) > 1:
            print_usage()
            return -1
        os.chdir(args[0])

    if options["do_make_all_feeds"]:
        feed_maker_cwd = os.getenv("FEED_MAKER_WORK_DIR")
        log_dir = os.path.join(feed_maker_cwd, "logs")
        img_dir = os.path.join(os.getenv("FEED_MAKER_WWW_FEEDS_DIR"), "img")
        result = make_all_feeds(feed_maker_cwd, log_dir, img_dir)
    else:
        feed_name = os.path.basename(os.getcwd())
        img_dir = os.path.join(os.getenv("FEED_MAKER_WWW_FEEDS_DIR"), "img", feed_name)
        result = make_single_feed(feed_name, img_dir, archiving_period, options["do_remove_all_files"], options["force_collection_opt"])
        
    end_ts = time.time()
    print(time.ctime(end_ts))
    logger.info("elapse=%f" % (end_ts - start_ts))

    return 0 if result else -1


if __name__ == "__main__":
    sys.exit(main())
