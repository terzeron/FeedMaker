#!/usr/bin/env python3

import sys
import os
import re
import time
import datetime
import getopt
import subprocess
import pprint
import feedmakerutil
from feedmakerutil import warn, die
from feedmakerutil import Config
from feedmakerutil import URL
from typing import List, Dict, Any, Tuple, Union
from logger import Logger
import PyRSS2Gen


logger = Logger("make_feed.py")
SECONDS_PER_DAY = 60 * 60 * 24
MAX_CONTENT_LENGTH = 64 * 1024
MAX_NUM_DAYS = 7


def get_pub_date_str(file_name: str) -> str:
    if os.path.isfile(file_name):
        ts = os.stat(file_name).st_mtime
    else:
        ts = datetime.datetime.now().timestamp()
    dt = datetime.datetime.fromtimestamp(float(ts))
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def get_rss_date_str(ts=datetime.datetime.now().timestamp()) -> str:
    dt = datetime.datetime.fromtimestamp(float(ts))
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def get_date_str(ts=datetime.datetime.now().timestamp()) -> str:
    dt = datetime.datetime.fromtimestamp(float(ts))
    return dt.strftime("%Y%m%d")


def get_list_file_name(list_dir: str, date_str: str) -> str:
    return "%s/%s.txt" % (list_dir, date_str)


def get_new_file_name(url: str) -> str:
    return "html/" + URL.get_short_md5_name(url) + ".html"


def get_recent_list(list_dir: str, post_process_script_list: List[str]) -> List[str]:
    logger.debug("# get_recent_list(%s)" % list_dir)

    date_str = get_date_str()
    new_list_file_name = get_list_file_name(list_dir, date_str)
    cmd = "collect_new_list.py"
    for post_process_script in post_process_script_list:
        if cmd:
            cmd += " |"
        cmd += ' %s "%s"' % (post_process_script, new_list_file_name)

    logger.debug(cmd)
    result, error = feedmakerutil.exec_cmd(cmd)
    if error:
        die("can't collect new list from the page")

    with open(new_list_file_name, 'w', encoding='utf-8') as out_file:
        out_file.write(result)
        
    with open(new_list_file_name, 'r', encoding='utf-8') as in_file:
        uniq_list: List[str] = []
        for line in in_file:
            line = line.rstrip()
            if not line.startswith("# "):
                uniq_list.append(line)

    return uniq_list


def read_old_list_from_file(list_dir: str, is_completed: bool) -> List[str]:
    logger.debug("# read_old_list_from_file(list_dir=%s, is_completed=%r)" % (list_dir, is_completed))

    result_list: List[str] = []
    ts = datetime.datetime.now().timestamp()
    if not is_completed:
        # 아직 진행 중인 피드에 대해서는 현재 날짜에 가장 가까운
        # 과거 리스트 파일 1개를 찾아서 그 안에 기록된 리스트를 꺼냄

        # 과거까지 리스트가 존재하는지 확인
        for i in range(MAX_NUM_DAYS):
            date_str = get_date_str(ts - i * SECONDS_PER_DAY)
            list_file = get_list_file_name(list_dir, date_str)
            logger.info(list_file)
            # 오늘에 가장 가까운 리스트가 존재하면 탈출
            if os.path.isfile(list_file):
                # read the old list
                with open(list_file, 'r', encoding='utf-8') as in_file:
                    for line in in_file:
                        line = line.rstrip()
                        if not line.startswith("# "):
                            result_list.append(line)
    else:
        # 이미 완료된 피드에 대해서는 기존 리스트를 모두 취합함
        for entry in os.scandir(list_dir):
            if entry.name.startswith(".") and entry.is_file():
                continue

            file_path = list_dir + "/" + entry.name
            with open(file_path, 'r', encoding='utf-8') as in_file:
                for line in in_file:
                    line = line.rstrip()
                    if not line.startswith("# "):
                        result_list.append(line)
    return list(set(result_list))


def generate_rss_feed(rss_conf, feed_list: List[str], rss_file_name: str) -> bool:
    logger.debug("# generate_rss_feed(%s)" % rss_file_name)

    logger.info("rss_conf=%s" % pprint.pformat(rss_conf))

    last_build_date_str = get_rss_date_str()
    date_str = get_date_str()
    temp_rss_file_name = rss_file_name + "." + date_str

    rss_items: List[PyRSS2Gen.RSSItem] = []
    for feed_item in feed_list:
        article_url, article_title = feed_item.split('\t')
        new_file_name = get_new_file_name(article_url)
        pub_date_str = get_rss_date_str()

        content = ""
        with open(new_file_name, 'r', encoding='utf-8') as in_file:
            logger.info("adding '%s' to the result" % new_file_name)
            for line in in_file:
                content += line
                # restrict big contents
                if len(content) >= MAX_CONTENT_LENGTH:
                    content = "<strong>본문이 너무 길어서 전문을 싣지 않았습니다. 다음의 원문 URL을 참고해주세요.</strong><br/>" + content
                    break
            rss_items.append(
                PyRSS2Gen.RSSItem(
                    title=article_title,
                    link=article_url,
                    guid=article_url,
                    pubDate=pub_date_str,
                    description=content
                )
            )

    rss = PyRSS2Gen.RSS2(
        title=rss_conf["rss_title"],
        link=rss_conf["rss_link"],
        description=rss_conf["rss_description"],
        lastBuildDate=last_build_date_str,
        items=rss_items
    )
    rss.write_xml(open(temp_rss_file_name, 'w'), encoding='utf-8')

    # 이번에 만들어진 rss 파일이 이전 파일과 내용이 다른지 확인
    is_different = False
    if os.path.isfile(rss_file_name):
        cmd = 'diff "%s" "%s" | grep -v -Ee \"(^(<|>) <(pub_date|last_build_date))|(^---\$)|(^[0-9,]+[a-z][0-9,]+\$)\" | wc -c' % (temp_rss_file_name, rss_file_name)
        logger.debug(cmd)
        result, error = feedmakerutil.exec_cmd(cmd)
        logger.debug(result)
        m = re.search(r'^\s*(?P<num_of_different_lines>\d+)\s*$', result)
        if m and m.group("num_of_different_lines") != "0":
            is_different = True
    else:
        is_different = True

    error = False
    if is_different:
        # 이전 파일을 old 파일로 이름 바꾸기
        if os.path.isfile(rss_file_name):
            cmd = 'mv -f "%s" "%s.old"' % (rss_file_name, rss_file_name)
            logger.debug(cmd)
            result, error = feedmakerutil.exec_cmd(cmd)
            if error:
                return False
        # 이번에 만들어진 파일을 정식 파일 이름으로 바꾸기
        if os.path.isfile(temp_rss_file_name):
            cmd = 'mv -f "%s" "%s"' % (temp_rss_file_name, rss_file_name)
            logger.debug(cmd)
            result, error = feedmakerutil.exec_cmd(cmd)
    else:
        # 이번에 만들어진 파일을 지우기
        cmd = 'rm -f "%s"' % temp_rss_file_name
        logger.debug(cmd)
        result, error = feedmakerutil.exec_cmd(cmd)

    if error:
        return False
    return True


def append_item_to_result(feed_list: List[str], item: str, rss_file_name: str, extraction_conf: Dict[str, Any]) -> None:
    url = ""
    title = ""
    fields = item.split('\t')
    if len(fields) == 2:
        url, title = fields
    elif len(fields) == 3:
        url, title, review_point = fields
    new_file_name = get_new_file_name(url)
    if os.path.isfile(new_file_name):
        size = os.stat(new_file_name).st_size
    else:
        size = 0

    if os.path.isfile(new_file_name) and size > len(feedmakerutil.header_str) + 1:
        # 이미 성공적으로 만들어져 있으니까 피드 리스트에 추가
        logger.info("Success: %s: %s --> %s: %d" % (title, url, new_file_name, size))
        feed_list.append(item)
    else:
        # 파일이 존재하지 않거나 크기가 작으니 다시 생성 시도
        cmd = determine_cmd(extraction_conf, url, new_file_name)
        logger.debug(cmd)
        result, error = feedmakerutil.exec_cmd(cmd)
        if error:
            time.sleep(5)
            result, error = feedmakerutil.exec_cmd(cmd)
            if error:
                die("can't extract HTML elements")

        if os.path.isfile(new_file_name):
            size = os.stat(new_file_name).st_size
        else:
            size = 0
        md5_name = URL.get_short_md5_name(url)
        if size > len(feedmakerutil.header_str) + 1:
            cmd = 'echo "<img src=\'http://terzeron.net/img/1x1.jpg?feed=%s&item=%s\'/>" >> "%s"' % (rss_file_name, md5_name, new_file_name)
            logger.debug(cmd)
            result, error = feedmakerutil.exec_cmd(cmd)
            if error:
                die("can't append page view logging tag")

            # 피드 리스트에 추가
            logger.info("Success: %s: %s --> %s: %d" % (title, url, new_file_name, size))
            feed_list.append(item)
        else:
            # 피드 리스트에서 제외
            warn("%s: %s --> %s: %d (< %d byte of header)" % (title, url, new_file_name, size, len(feedmakerutil.header_str)))
            return

        if extraction_conf["force_sleep_between_articles"]:
            time.sleep(1)


def determine_cmd(extraction_conf: Dict[str, Any], url: str, new_file_name: str) -> str:
    post_process_cmd = ""
    for script in extraction_conf["post_process_script_list"]:
        post_process_cmd += ' | %s "%s"' % (script, url)

    if extraction_conf["bypass_element_extraction"]:
        extraction_cmd = ""
    else:
        extraction_cmd = ' | extract.py "%s"' % url

    option_str = feedmakerutil.determine_crawler_options(extraction_conf)
    cmd = 'crawler.py %s "%s" %s %s > "%s"' % (option_str, url, extraction_cmd, post_process_cmd, new_file_name) 

    return cmd
            

def diff_old_and_recent(extraction_conf, recent_list: List[str], old_list: List[str], feed_list: List[str], rss_file_name: str) -> bool:
    logger.debug("# diff_old_and_recent(len(recent_list)=%d, len(old_list)=%d), len(feed_list)=%d, rss_file_name=%s" % (len(recent_list), len(old_list), len(feed_list), rss_file_name))

    old_map: Dict[str, str] = {}
    for old in old_list:
        if re.search(r'^#', old):
            continue
        url, title = old.split('\t')
        old_map[url] = title
    logger.debug(str(len(old_list)))

    # differentiate
    result_list: List[str] = []
    for recent in recent_list:
        if re.search(r'^#', recent):
            continue
        
        url, title = recent.split('\t')
        if url not in old_map:
            result_list.append(recent)
            logger.debug("not exists %s" % recent)
        else:
            logger.debug("exists %s" % recent)

    # collect items to be generated as RSS feed
    logger.info("Appending %d new items to the feed list" % (len(result_list)))
    for new_item in reversed(result_list):
        if re.search(r'^#', new_item):
            continue
        append_item_to_result(feed_list, new_item, rss_file_name, extraction_conf)
    
    logger.info("Appending %d old items to the feed list" % (len(old_list)))
    for old_item in reversed(old_list):
        if re.search(r'^#', old_item):
            continue
        append_item_to_result(feed_list, old_item, rss_file_name, extraction_conf)

    if len(feed_list) == 0:
        logger.info("새로 추가된 feed가 없으므로 결과 파일을 변경하지 않음")
        return False
    return True

    
def get_start_idx(file_name: str) -> Tuple[int, int]:
    logger.debug("# get_start_idx(%s)" % file_name)

    if os.path.isfile(file_name):
        with open(file_name, 'r', encoding='utf-8') as in_file:
            line = in_file.readline()
            m = re.search(r'(?P<start_idx>\d+)\t(?P<mtime>\d+)', line)
            if m:
                start_idx = int(m.group("start_idx"))
                mtime = int(m.group("mtime"))
                
                logger.info("start index: %d" % start_idx)
                logger.info("last modified time: %d, %s" % (mtime, get_rss_date_str(mtime)))
                return start_idx, mtime

    # 처음 생성 시
    write_next_start_idx(file_name, 0)
    ts = datetime.datetime.now().timestamp()
    return 0, int(ts)


def write_next_start_idx(file_name: str, next_start_idx: int) -> None:
    logger.debug("# write_next_start_idx(%s, %d)" % (file_name, next_start_idx))

    ts = datetime.datetime.now().timestamp()
    with open(file_name, 'w', encoding='utf-8') as out_file:
        logger.info("next start index: %d" % next_start_idx)
        logger.info("current time: %d, %s" % (ts, get_rss_date_str(ts)))
        out_file.write("%d\t%d\n" % (int(next_start_idx), int(ts)))


def print_usage() -> None:
    print("usage:\t%s\t<config file> <rss file>" % (sys.argv[0]))
    print()


def cmp_int_or_str(a: Dict[str, str], b: Dict[str, str]) -> int:
    m1 = re.search(r'^\d+$', a["sf"])
    m2 = re.search(r'^\d+$', b["sf"])
    if m1 and m2:
        return int(a["sf"]) - int(b["sf"])
    else:
        if a["sf"] < b["sf"]:
            return -1
        elif a["sf"] > b["sf"]:
            return 1
        else:
            return 0


def cmp_to_key(mycmp):
    # noinspection PyUnusedLocal,PyUnusedLocal
    class K:
        def __init__(self, obj, *args):
            self.obj = obj
            
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K

    
def main():
    logger.info("=========================================================")
    logger.info(" " + os.getcwd() + " ")
    logger.info("=========================================================")

    do_collect_by_force = False
               
    optlist, args = getopt.getopt(sys.argv[1:], "c")
    for o, a in optlist:
        if o == '-c':
            do_collect_by_force = True
               
    if len(args) == 0:
        print_usage()
        sys.exit(-1)
               
    rss_file_name = args[0]

    config = Config()
    if not config:
        die("can't find conf.xml file nor get config element")
    collection_conf = config.get_collection_configs()
    logger.info("collection_conf=%s" % pprint.pformat(collection_conf))

    # -c 옵션이 지정된 경우, 설정의 is_completed 값 무시
    if do_collect_by_force:
        collection_conf["is_completed"] = False

    list_dir = "newlist"
    feedmakerutil.make_path(list_dir)
    feedmakerutil.make_path("html")

    # 과거 피드항목 리스트를 가져옴
    feed_list: List[str] = []
    old_list = read_old_list_from_file(list_dir, collection_conf["is_completed"])
    if not old_list:
        warn("can't get old list!")

    # 완결여부 설정값 판단 
    recent_list: List[str] = []
    if collection_conf["is_completed"]:
        # 완결된 피드는 적재된 리스트에서 일부 피드항목을 꺼내옴

        # 오름차순 정렬
        feed_id_sort_field_list: List[Dict[str, Union[int, str]]] = []
        feed_item_existence_set = set([])

        matched_count = 0
        for i, old_item in enumerate(old_list):
            m = re.search(collection_conf["sort_field_pattern"], old_item)
            if m:
                sort_field = "%09s" % (m.group(1))
                try:
                    sort_field += "%09s" % (m.group(2))
                except IndexError:
                    pass
                matched_count += 1
            else:
                sort_field = "0"

            if old_item not in feed_item_existence_set:
                feed_id_sort_field = {"id": i, "sf": sort_field}
                feed_item_existence_set.add(old_item)
                feed_id_sort_field_list.append(feed_id_sort_field)

        # 전체 리스트 중 절반 이상의 정렬필드를 검출하지 못하면 경고
        if matched_count > len(old_list) / 2:
            sorted_feed_list = sorted(feed_id_sort_field_list, key=cmp_to_key(cmp_int_or_str))
        else:
            warn("can't match the pattern /%s/" % (collection_conf["sort_field_pattern"]))
            sorted_feed_list = feed_id_sort_field_list
            
        idx_file = "start_idx.txt"
        window_size = 10  # feedly initial max window size
        start_idx, mtime = get_start_idx(idx_file)
        end_idx = start_idx + window_size
        for i, feed in enumerate(sorted_feed_list):
            if start_idx <= i < end_idx:
                feed_list.append(old_list[feed["id"]])
                try:
                    url, title = old_list[feed["id"]].split("\t")
                except ValueError:
                    print("feed['id']=%r, old_list[feed['id']]=%r" % (feed["id"], old_list[feed["id"]]))
                    die("can't read old list")
                guid = URL.get_short_md5_name(url)
                logger.info("%s\t%s\t%s" % (url, title, guid))

        ts = datetime.datetime.now().timestamp()
        increment_size = int(((int(ts) - mtime) * collection_conf["unit_size_per_day"]) / 86400)
        logger.info("# start_idx=%d, end_idx=%d, current time=%d, mtime=%d, window_size=%d, increment_size=%d" % (start_idx, end_idx, int(ts), mtime, window_size, increment_size))
        if increment_size > 0:
            write_next_start_idx(idx_file, start_idx + increment_size)
    else:
        # 피딩 중인 피드는 최신 피드항목을 받아옴
        recent_list = get_recent_list(list_dir, collection_conf["post_process_script_list"])
        if not recent_list:
            die("can't get recent list!")
        
        # 과거 피드항목 리스트와 최근 피드항목 리스트를 비교함
        if collection_conf["ignore_old_list"]:
            old_list: List[str] = []
            feed_list = recent_list

        extraction_conf = config.get_extraction_configs()
        if not diff_old_and_recent(extraction_conf, recent_list, old_list, feed_list, rss_file_name):
            return -1

    if not do_collect_by_force:
        # generate RSS feed
        rss_conf = config.get_rss_configs()
        if not generate_rss_feed(rss_conf, feed_list, rss_file_name):
            return -1
    
    # upload RSS feed file
    cmd = 'upload.py %s' % rss_file_name
    logger.debug(cmd)
    result, error = feedmakerutil.exec_cmd(cmd)
    logger.debug(result)
    if error:
        return -1

    m = re.search(r'Upload success', result)
    if m:
        logger.info("Uploaded file '%s'" % rss_file_name)
        if not do_collect_by_force:
            # email notification
            notification_conf = config.get_notification_configs()
            if notification_conf:
                cmd = "| mail -s '%s' '%s'" % (notification_conf["email_subject"], notification_conf["email_recipient"])
                with subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE) as p:
                    for feed in recent_list:
                        p.communicate(feed + "\n")
                logger.info("sent a notification in mail")
    else:
        logger.info("No need to upload same file '%s'" % rss_file_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
