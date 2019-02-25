#!/usr/bin/env python3

import sys
import os
import re
import time
import datetime
import getopt
import subprocess
import pprint
import logging
import logging.config
from feed_maker_util import Config, URL, exec_cmd, make_path, determine_crawler_options, header_str
from collections import OrderedDict
from new_list_collector import NewListCollector
from typing import List, Dict, Any, Tuple, Union, Set, Callable
import PyRSS2Gen


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
logger = logging.getLogger()
SECONDS_PER_DAY = 60 * 60 * 24


class FeedMaker:
    def __init__(self, do_collect_by_force: bool, do_collect_only: bool, rss_file_name: str) -> None:
        # ToDo: 글로벌 설정 파일로 분리
        self.MAX_CONTENT_LENGTH = 64 * 1024
        self.MAX_NUM_DAYS = 7
        self.WINDOW_SIZE = 10
        self.image_tag_fmt_str = "\n<img src='https://terzeron.com/img/1x1.jpg?feed=%s&item=%s'/>\n"

        self.collection_conf: Dict[str, Any] = {}
        self.extraction_conf: Dict[str, Any] = {}
        self.rss_conf: Dict[str, Any] = {}
        self.do_collect_by_force = do_collect_by_force
        self.do_collect_only = do_collect_only
        self.rss_file_name = rss_file_name

        self.list_dir = "newlist"
        self.html_dir = "html"
        self.start_idx_file_name = "start_idx.txt"
        make_path(self.list_dir)
        make_path(self.html_dir)
        
        self.recent_feed_list: List[Tuple[str, str]] = []
        self.old_feed_list: List[Tuple[str, str]] = []
        self.new_feed_list: List[Tuple[str, str]] = []

        
    def get_pub_date_str(self, file_name: str) -> str:
        if os.path.isfile(file_name):
            ts = os.stat(file_name).st_mtime
        else:
            ts = datetime.datetime.now().timestamp()
        dt = datetime.datetime.fromtimestamp(float(ts))
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    

    def get_rss_date_str(self, ts=datetime.datetime.now().timestamp()) -> str:
        dt = datetime.datetime.fromtimestamp(float(ts))
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    

    def get_date_str(self, ts=datetime.datetime.now().timestamp()) -> str:
        dt = datetime.datetime.fromtimestamp(float(ts))
        return dt.strftime("%Y%m%d")
    

    def get_list_file_name(self, date_str: str) -> str:
        return "%s/%s.txt" % (self.list_dir, date_str)
    

    def get_html_file_name(self, link: str) -> str:
        return "%s/%s.html" % (self.html_dir, URL.get_short_md5_name(link))
    
    
    def cmp_int_or_str(self, a: Dict[str, str], b: Dict[str, str]) -> int:
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
    

    def cmp_to_key(self, mycmp) -> Callable[[Dict[str, object]], Any]:
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
    
        
    def get_recent_feed_list(self) -> None:
        logger.debug("# get_recent_feed_list()")
    
        date_str = self.get_date_str()
        new_list_file_name = self.get_list_file_name(date_str)
    
        collector = NewListCollector(self.collection_conf, new_list_file_name)
        self.recent_feed_list = collector.collect()
    
    
    def read_old_feed_list_from_file(self) -> None:
        logger.debug("# read_old_feed_list_from_file()")

        feed_list: List[Tuple[str, str]] = []
        ts = datetime.datetime.now().timestamp()
        if not self.collection_conf["is_completed"]:
            # 아직 진행 중인 피드에 대해서는 현재 날짜에 가장 가까운
            # 과거 리스트 파일 1개를 찾아서 그 안에 기록된 리스트를 꺼냄
    
            # 과거까지 리스트가 존재하는지 확인
            for i in range(self.MAX_NUM_DAYS):
                date_str = self.get_date_str(ts - i * SECONDS_PER_DAY)
                list_file = self.get_list_file_name(date_str)
                # 오늘에 가장 가까운 리스트가 존재하면 탈출
                if os.path.isfile(list_file):
                    logger.info(list_file)
                    # read the old list
                    with open(list_file, 'r', encoding='utf-8') as in_file:
                        for line in in_file:
                            line = line.rstrip()
                            link, title = line.split("\t")
                            feed_list.append((link, title))
                        if len(feed_list) > 0:
                            break
        else:
            # 이미 완료된 피드에 대해서는 기존 리스트를 모두 취합함
            for entry in os.scandir(self.list_dir):
                if entry.name.startswith(".") and entry.is_file():
                    continue
    
                file_path = self.list_dir + "/" + entry.name
                with open(file_path, 'r', encoding='utf-8') as in_file:
                    for line in in_file:
                        line = line.rstrip()
                        link, title = line.split("\t")
                        feed_list.append((link, title))
        self.old_feed_list = list(set(feed_list))
        
    
    def generate_rss_feed(self) -> bool:
        logger.debug("# generate_rss_feed()")

        last_build_date_str = self.get_rss_date_str()
        date_str = self.get_date_str()
        temp_rss_file_name = self.rss_file_name + "." + date_str
    
        rss_items: List[PyRSS2Gen.RSSItem] = []
        for link, title in self.new_feed_list:
            html_file_name = self.get_html_file_name(link)
            pub_date_str = self.get_rss_date_str()
    
            content = ""
            with open(html_file_name, 'r', encoding='utf-8') as in_file:
                logger.info("adding '%s' to the result" % html_file_name)
                for line in in_file:
                    content += line
                    # restrict big contents
                    if len(content) >= self.MAX_CONTENT_LENGTH:
                        content = "<strong>본문이 너무 길어서 전문을 싣지 않았습니다. 다음의 원문 URL을 참고해주세요.</strong><br/>" + content
                        break
                rss_items.append(
                    PyRSS2Gen.RSSItem(
                        title=title,
                        link=link,
                        guid=link,
                        pubDate=pub_date_str,
                        description=content
                    )
                )
    
        rss = PyRSS2Gen.RSS2(
            title=self.rss_conf["rss_title"],
            link=self.rss_conf["rss_link"],
            description=self.rss_conf["rss_description"],
            lastBuildDate=last_build_date_str,
            items=rss_items
        )
        rss.write_xml(open(temp_rss_file_name, 'w'), encoding='utf-8')
    
        # 이번에 만들어진 rss 파일이 이전 파일과 내용이 다른지 확인
        is_different = False
        if os.path.isfile(self.rss_file_name):
            cmd = 'diff "%s" "%s" | grep -v -Ee \"(^(<|>) <(pub_date|last_build_date))|(^---\$)|(^[0-9,]+[a-z][0-9,]+\$)\" | wc -c' % (temp_rss_file_name, self.rss_file_name)
            logger.debug(cmd)
            result, error = exec_cmd(cmd)
            logger.debug(result)
            m = re.search(r'^\s*(?P<num_of_different_lines>\d+)\s*$', result)
            if m and m.group("num_of_different_lines") != "0":
                is_different = True
        else:
            is_different = True
    
        error = None
        if is_different:
            # 이전 파일을 old 파일로 이름 바꾸기
            if os.path.isfile(self.rss_file_name):
                cmd = 'mv -f "%s" "%s.old"' % (self.rss_file_name, self.rss_file_name)
                logger.debug(cmd)
                result, error = exec_cmd(cmd)
                if error:
                    return False
            # 이번에 만들어진 파일을 정식 파일 이름으로 바꾸기
            if os.path.isfile(temp_rss_file_name):
                cmd = 'mv -f "%s" "%s"' % (temp_rss_file_name, self.rss_file_name)
                logger.debug(cmd)
                result, error = exec_cmd(cmd)
        else:
            # 이번에 만들어진 파일을 지우기
            cmd = 'rm -f "%s"' % temp_rss_file_name
            logger.debug(cmd)
            result, error = exec_cmd(cmd)
    
        if error:
            return False
        return True
    
    
    def make_html_file(self, link: str, title: str) -> None:
        html_file_name = self.get_html_file_name(link)
        if os.path.isfile(html_file_name):
            size = os.stat(html_file_name).st_size
        else:
            size = 0
    
        if os.path.isfile(html_file_name) and size > len(header_str) + len(self.image_tag_fmt_str) + 1:
            # 이미 성공적으로 만들어져 있으니까 피드 리스트에 추가
            logger.info("Success: %s: %s --> %s: %d" % (title, link, html_file_name, size))
        else:
            # 파일이 존재하지 않거나 크기가 작으니 다시 생성 시도
            cmd = self.determine_cmd(link, html_file_name)
            logger.debug(cmd)
            result, error = exec_cmd(cmd)
            if error:
                time.sleep(5)
                result, error = exec_cmd(cmd)
                if error:
                    logger.error("can't extract HTML elements")
                    sys.exit(-1)
    
            if os.path.isfile(html_file_name):
                size = os.stat(html_file_name).st_size
            else:
                size = 0
    
            md5_name = URL.get_short_md5_name(link)
            if size > len(header_str) + 1:
                # append image_tag_str to html_file_name
                image_tag_str = self.image_tag_fmt_str % (self.rss_file_name, md5_name)
                with open(html_file_name, "a") as outfile:
                    outfile.write(image_tag_str)
    
                # 피드 리스트에 추가
                logger.info("Success: %s: %s --> %s: %d" % (title, link, html_file_name, size))
            else:
                # 피드 리스트에서 제외
                logger.warning("%s: %s --> %s: %d (<= %d byte of header)" % (title, link, html_file_name, size, len(header_str) + len(self.image_tag_fmt_str) + 1))
                return
    
            if self.extraction_conf["force_sleep_between_articles"]:
                time.sleep(1)
    
    
    def determine_cmd(self, link: str, html_file_name: str) -> str:
        post_process_cmd = ""
        for script in self.extraction_conf["post_process_script_list"]:
            post_process_cmd += ' | %s "%s"' % (script, link)
    
        if self.extraction_conf["bypass_element_extraction"]:
            extraction_cmd = ""
        else:
            extraction_cmd = ' | extract.py "%s"' % link
    
        option_str = determine_crawler_options(self.extraction_conf)
        cmd = 'crawler.py %s "%s" %s %s > "%s"' % (option_str, link, extraction_cmd, post_process_cmd, html_file_name) 
    
        return cmd
                
    
    def diff_feeds_and_make_htmls(self) -> None:
        logger.debug("# diff_feeds_and_make_htmls()")

        recent_set = set(self.recent_feed_list)
        old_set = set(self.old_feed_list)
        self.new_feed_list = list(recent_set - old_set)
        
        # collect items to be generated as RSS feed
        logger.info("Appending %d new items to the feed list" % (len(self.new_feed_list)))
        for link, title in reversed(self.new_feed_list):
            self.make_html_file(link, title)

        logger.info("Appending %d old items to the feed list" % (len(self.old_feed_list)))
        for link, title in reversed(self.old_feed_list):
            self.make_html_file(link, title)
    
        
    def get_idx_data(self) -> Tuple[int, int, int]:
        logger.debug("# get_idx_data()")
    
        if os.path.isfile(self.start_idx_file_name):
            with open(self.start_idx_file_name, 'r', encoding='utf-8') as in_file:
                line = in_file.readline()
                m = re.search(r'(?P<start_idx>\d+)\t(?P<mtime>\d+)', line)
                if m:
                    start_idx = int(m.group("start_idx"))
                    end_idx = start_idx + self.WINDOW_SIZE
                    mtime = int(m.group("mtime"))
                    
                    logger.info("start index: %d, end index:%d, last modified time: %d, %s" % (start_idx, end_idx, mtime, self.get_rss_date_str(mtime)))
                    return start_idx, end_idx, mtime

        # 처음 생성 시, 또는 파일에 정보가 없을 때
        start_idx = 0
        end_idx = self.WINDOW_SIZE
        mtime = int(datetime.datetime.now().timestamp())
        self.write_idx_data(start_idx, mtime, True)
        return start_idx, end_idx, mtime
    
    
    def write_idx_data(self, start_idx: int, mtime: int, do_write_initially: bool = False) -> None:
        logger.debug("# write_idx_data(start_idx=%d, mtime=%d)" % (start_idx, mtime))
    
        ts = datetime.datetime.now().timestamp()
        increment_size = int(((int(ts) - mtime) * self.collection_conf["unit_size_per_day"]) / 86400)
        logger.debug("start_idx=%d, current time=%d, mtime=%d, self.WINDOW_SIZE=%d, increment_size=%d" % (start_idx, int(ts), mtime, self.WINDOW_SIZE, increment_size))
        if do_write_initially or increment_size > 0:
            next_start_idx = start_idx + increment_size
            with open(self.start_idx_file_name, 'w', encoding='utf-8') as out_file:
                logger.info("next start index: %d, current time: %d, %s" % (next_start_idx, ts, self.get_rss_date_str(ts)))
                out_file.write("%d\t%d\n" % (int(next_start_idx), int(ts)))


    def fetch_old_feed_list_window(self) -> None:
        # 오름차순 정렬
        feed_id_sort_field_list: List[Dict[str, object]] = []
        feed_item_existence_set: Set[str] = set([])
        
        matched_count = 0
        sort_field_pattern = self.collection_conf["sort_field_pattern"]
        for i, item in enumerate(self.old_feed_list):
            link, title = item
            m = re.search(sort_field_pattern, link + "\t" + title)
            if m:
                sort_field = "%09s" % m.group(1)
                try:
                    if m.group(2):
                        sort_field += "%09s" % m.group(2)
                except IndexError as e:
                    # ignore
                    pass
                matched_count += 1
            else:
                sort_field = "999999999"
    
            if link not in feed_item_existence_set:
                # 번호 to 기준필드 정보를 저장해둠 
                feed_id_sort_field = {"id": i, "sf": sort_field}
                feed_item_existence_set.add(link)
                feed_id_sort_field_list.append(feed_id_sort_field)
                
        # 전체 리스트 중 절반 이상의 정렬필드를 검출하지 못하면 경고
        if matched_count > len(self.old_feed_list) / 2:
            sorted_feed_list = sorted(feed_id_sort_field_list, key=self.cmp_to_key(self.cmp_int_or_str))
        else:
            logger.warning("can't match the pattern /%s/" % (self.collection_conf["sort_field_pattern"]))
            sorted_feed_list = feed_id_sort_field_list
        
        start_idx, end_idx, mtime = self.get_idx_data()
        for i, feed in enumerate(sorted_feed_list):
            id = feed["id"]
            if start_idx <= i < end_idx:
                link, title = self.old_feed_list[id]
                logger.info("%s\t%s" % (link, title))
                self.new_feed_list.append(self.old_feed_list[id])

        self.write_idx_data(start_idx, mtime)
    
                
    def make(self) -> bool:
        logger.info("=========================================================")
        logger.info(" " + os.getcwd() + " ")
        logger.info("=========================================================")
                   
        config = Config()
        if not config:
            logger.error("can't find conf.xml file nor get config element")
            sys.exit(-1)
        self.collection_conf = config.get_collection_configs()
        logger.info("self.collection_conf=%s" % pprint.pformat(self.collection_conf))
    
        # -c 또는 -l 옵션이 지정된 경우, 설정의 is_completed 값 무시
        if self.do_collect_by_force or self.do_collect_only:
            self.collection_conf["is_completed"] = False
    
        if not self.do_collect_only:
            # 과거 피드항목 리스트를 가져옴
            self.read_old_feed_list_from_file()
            if not self.old_feed_list or len(self.old_feed_list) == 0:
                logger.warning("Can't read old feed list from files")
    
        # 완결여부 설정값 판단 
        if self.collection_conf["is_completed"]:
            # 완결된 피드는 적재된 리스트에서 일부 피드항목을 꺼내옴
            self.fetch_old_feed_list_window()
        else:
            # 피딩 중인 피드는 최신 피드항목을 받아옴
            self.get_recent_feed_list()
            if not self.recent_feed_list or len(self.recent_feed_list) == 0:
                logger.error("Can't get recent feed list from urls")
                return False
            if self.do_collect_only:
                return True
            
            # 과거 피드항목 리스트와 최근 피드항목 리스트를 비교함
            if self.collection_conf["ignore_old_list"]:
                self.old_feed_list = []
                self.new_feed_list = self.recent_feed_list
    
            self.extraction_conf = config.get_extraction_configs()
            logger.info("self.extraction_conf=%s" % pprint.pformat(self.extraction_conf))

            self.diff_feeds_and_make_htmls()
            if not self.new_feed_list or len(self.new_feed_list) == 0:
                logger.info("No new feeds, no update of rss file")
    
        if not self.do_collect_by_force:
            # generate RSS feed
            self.rss_conf = config.get_rss_configs()
            logger.info("self.rss_conf=%s" % pprint.pformat(self.rss_conf))
            if not self.generate_rss_feed():
                return False
        
            # upload RSS feed file
            cmd = 'upload.py %s' % self.rss_file_name
            logger.debug(cmd)
            result, error = exec_cmd(cmd)
            logger.debug(result)
            if error:
                return False
        
            m = re.search(r'Upload success', result)
            if m:
                logger.info("Uploaded file '%s'" % self.rss_file_name)
                if not self.do_collect_by_force:
                    # email notification
                    notification_conf = config.get_notification_configs()
                    if notification_conf:
                        cmd = "| mail -s '%s' '%s'" % (notification_conf["email_subject"], notification_conf["email_recipient"])
                        with subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE) as p:
                            for link, title in self.recent_feed_list:
                                p.communicate("%s\t%s\n" % (link, title))
                        logger.info("Sent a notification in mail")
            else:
                logger.info("No need to upload same file '%s'" % self.rss_file_name)
        return True
    
    
