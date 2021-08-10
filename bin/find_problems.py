#!/usr/bin/env python


import sys
import os
import json
import math
import re
from pathlib import Path
from datetime import datetime, timedelta
import logging
import logging.config
from typing import List, Tuple, Dict, Any
from feed_maker import FeedMaker


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class ProblemChecker:
    work_dir = Path(os.environ["FEED_MAKER_WORK_DIR"])
    result_dir = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"])
    httpd_access_log_dir = Path(os.environ["HOME"]) / "apps/logs"
    htaccess_file = result_dir / ".." / ".htaccess"


    def __init__(self) -> None:
        # alias -> name
        self.feed_alias_name_map: Dict[str, str] = {}
        # name -> alias
        self.feed_name_alias_map: Dict[str, str] = {}
        # name -> group
        self.feed_name_group_map: Dict[str, str] = {}
        # name -> config
        self.feed_name_config_map: Dict[str, Any] = {}
        # name -> progress(index,count,progress_ratio,unit_size,num_days)
        self.feed_name_progress_info_map: Dict[str, Tuple[int, int, float, int, int]] = {}
        # name -> result_info(size, mtime)
        self.feed_name_result_info_map: Dict[str, Dict[str, Any]] = {}
        # alias -> access_info(access_status,access_time,view_status,view_time,is_in_xml_dir)
        self.feed_alias_access_info_map: Dict[str, Dict[str, Any]] = {}
        # alias -> status_info(htaccess,http_request,public_html,feedmaker)
        self.feed_alias_status_info_map: Dict[str, Dict[str, Any]] = {}
        # html -> size
        self.html_file_size_map: Dict[str, int] = {}
        # html -> image_tag count
        self.html_file_image_tag_count_map: Dict[str, int] = {}
        # html -> image-not-found count
        self.html_file_image_not_found_count_map: Dict[str, int] = {}


    def __del__(self) -> None:
        del self.feed_alias_name_map
        del self.feed_name_alias_map
        del self.feed_name_group_map

        del self.feed_name_config_map
        del self.feed_name_progress_info_map
        del self.feed_name_result_info_map
        del self.feed_alias_access_info_map
        del self.html_file_size_map
        del self.html_file_image_tag_count_map
        del self.html_file_image_not_found_count_map


    def check_number_of_list_url_elements(self) -> None:
        print("## the number of \"list_url\" elements")
        feed_count_map: Dict[str, Tuple[bool, int]] = {}
        for feed_name, config in self.feed_name_config_map.items():
            if "collection" in config:
                if "list_url_list" in config["collection"]:
                    count = len(config["collection"]["list_url_list"])
                    if count > 1:
                        status = config["collection"].get("is_completed", False)
                        feed_count_map[feed_name] = status, count

        # sorted print
        for feed_name, value in sorted(feed_count_map.items(), key=lambda item: item[1], reverse=True):
            status, count = value
            print("* %s (%s): %d items" % (feed_name, "completed" if status else "ing", count))
        print()


    @staticmethod
    def count_by_key(config: Dict[str, Any], k: str, count_map: Dict[str, int]) -> None:
        if k in config and config[k]:
            count_map[k] = count_map.get(k, 0) + 1


    @staticmethod
    def print_element_count(count_map: Dict[str, int]) -> None:
        for element, count in sorted(count_map.items(), key=lambda item: item[1], reverse=True):
            print("* %s: %d" % (element, count))

    def check_number_of_occurrence_of_each_element(self) -> None:
        print("## the number of occurences of elements")
        collection_req_count_map: Dict[str, int] = {}
        collection_opt_count_map: Dict[str, int] = {}
        extraction_req_count_map: Dict[str, int] = {}
        extraction_opt_count_map: Dict[str, int] = {}
        rss_req_count_map: Dict[str, int] = {}
        rss_opt_count_map: Dict[str, int] = {}
        for _, config in self.feed_name_config_map.items():
            for k, v in config["collection"].items():
                if k in ["list_url_list", "item_capture_script"] and v:
                    ProblemChecker.count_by_key(config["collection"], k, collection_req_count_map)
                else:
                    ProblemChecker.count_by_key(config["collection"], k, collection_opt_count_map)
            for k, v in config["extraction"].items():
                if k in ["element_id_list", "element_class_list", "element_path_list"] and v:
                    ProblemChecker.count_by_key(config["extraction"], k, extraction_req_count_map)
                else:
                    ProblemChecker.count_by_key(config["extraction"], k, extraction_opt_count_map)
            for k, v in config["rss"].items():
                if k in ["rss_title", "rss_description", "rss_generator", "rss_copyright", "rss_link", "rss_language"] and v:
                    ProblemChecker.count_by_key(config["rss"], k, rss_req_count_map)
                else:
                    ProblemChecker.count_by_key(config["rss"], k, rss_opt_count_map)

        print("### collection")
        ProblemChecker.print_element_count(collection_req_count_map)
        ProblemChecker.print_element_count(collection_opt_count_map)
        print()
        print("### extraction")
        ProblemChecker.print_element_count(extraction_req_count_map)
        ProblemChecker.print_element_count(extraction_opt_count_map)
        print()
        print("### rss")
        ProblemChecker.print_element_count(rss_req_count_map)
        ProblemChecker.print_element_count(rss_opt_count_map)
        print()


    def check_validity_of_configuration_files(self) -> None:
        print("# Validity of Configuration Files\n")
        self.check_number_of_list_url_elements()
        self.check_number_of_occurrence_of_each_element()
        print()


    def check_size_time_of_result_files(self) -> None:
        print("# Size & Time of Result Files\n")
        for feed_name, result_info in sorted(self.feed_name_result_info_map.items(), key=lambda item: item[1]["size"]):
            size = result_info["size"]
            if size < 600:
                print("* %s: %s bytes" % (feed_name, size))
        print()


    def check_too_small_html_files(self) -> None:
        print("## small html files")
        for file, size in self.html_file_size_map.items():
            if 0 < size < 100:
                print("* %s: %s bytes" % (file, size))
        print()


    def check_html_files_without_image_tag(self) -> None:
        print("## html files without image tag")
        for file, count in self.html_file_image_tag_count_map.items():
            if count < 1:
                print("* %s: %d" % (file, count))
        print()


    def check_html_files_with_many_image_tag(self) -> None:
        print("## html files with too many image tags")
        for file, count in self.html_file_image_tag_count_map.items():
            if count > 1:
                print("* %s: %d" % (file, count))
        print()


    def check_html_files_with_image_not_found(self) -> None:
        print("## html files with 'image-not-found.png'")
        for file, count in self.html_file_image_not_found_count_map.items():
            print("* %s: %d" % (file, count))
        print()


    def check_html_content(self) -> None:
        print("# HTML Content\n")
        self.check_too_small_html_files()
        self.check_html_files_without_image_tag()
        self.check_html_files_with_many_image_tag()
        self.check_html_files_with_image_not_found()
        print()


    def check_incremental_feeding(self) -> None:
        print("# Incremental Feeding Progressive\n")
        for feed_name, progress_info in sorted(self.feed_name_progress_info_map.items(), key=lambda item: item[1][4], reverse=True):
            index, count, progress_ratio, unit_size, num_days = progress_info
            print("* %s: %d/%d=%.0f%%, %d articles/day, %s" % (feed_name, index + 4, count, int(progress_ratio), unit_size, (datetime.now() + timedelta(days=num_days)).strftime("%Y-%m-%d")))
        print()


    def check_garbage_feeds(self) -> None:
        print("# Garbage Feeds\n")
        for feed_alias, access_info in self.feed_alias_access_info_map.items():
            access_status = access_info.get("access_status", None)
            access_time = access_info.get("access_time", None)
            view_status = access_info.get("view_status", None)
            view_time = access_info.get("view_time", None)
            is_in_xml_dir = access_info.get("is_in_xml_dir", False)
            if is_in_xml_dir and access_status not in [200, 301]:
                # direct access to public_html/xml/feed.xml
                print("* xml/%s: A %s %s" % (feed_alias, str(access_status) if access_status else "", access_time.strftime("%Y-%m-%d") if access_time else ""))
            elif view_status not in [200, None]:
                # view error
                print("* %s: V %s %s" % (feed_alias, str(view_status) if view_status else "", view_time.strftime("%Y-%m-%d") if view_time else ""))
            elif access_status not in [200, 301] and access_time and access_time + timedelta(days=7) > datetime.now() and view_time and access_time > view_time:
                # access error (for the last 14 days)
                print("* %s: A %s %s" % (feed_alias, str(access_status) if access_status else "", access_time.strftime("%Y-%m-%d") if access_time else ""))
        print()


    def check_old_result_files(self) -> None:
        #
        #
        # feed status로 통합해서 출력할 것
        #
        #
        print("## old result files")
        file_mtime_map: Dict[str, datetime] = {}
        for file, result_info in self.feed_name_result_info_map.items():
            mtime = result_info["mtime"]
            if datetime.now() - timedelta(days=10) > datetime.fromtimestamp(mtime):
                file_mtime_map[file] = mtime

        # sorted print
        for file, mtime in sorted(file_mtime_map.items(), key=lambda item: item[1]):
            print("* %s: %s" % (file, datetime.fromtimestamp(mtime).astimezone().strftime("%Y-%m-%d")))
        print()


    def check_feed_status(self) -> None:
        print("# Feed Status\n")
        requested_but_deleted_feed_list: List[Tuple[str, str]] = []
        paused_or_unregistered_feed_list: List[Tuple[str, str]] = []
        for alias, status_info in self.feed_alias_status_info_map.items():
            if status_info["http_request"] == 1 and status_info["htaccess"] == 0 and status_info["public_html"] == 0 and status_info["feedmaker"] == 0:
                requested_but_deleted_feed_list.append((alias, status_info["feed_name"]))
                continue
            elif status_info["http_request"] == 0 and status_info["htaccess"] == 1 and status_info["public_html"] == 1 and status_info["feedmaker"] == 1:
                paused_or_unregistered_feed_list.append((alias, status_info["feed_name"]))
                continue

        print("## requested but deleted feed list\n")
        for alias, name in requested_but_deleted_feed_list:
            if not alias:
                print("* %s" % name)
            elif not name:
                print("* %s" % alias)
            elif alias == name:
                print("* %s" % alias)
            else:
                print("* %s(%s)" % (alias, name))
        print()

        print("## unrequested(paused or unregistered) feed list\n")
        for alias, name in paused_or_unregistered_feed_list:
            if not alias:
                print("* %s" % name)
            elif not name:
                print("* %s" % alias)
            elif alias == name:
                print("* %s" % alias)
            else:
                print("* %s(%s)" % (alias, name))
        print()


    def load_all_config_files(self) -> None:
        LOGGER.debug("# load_all_config_files()")
        for path in ProblemChecker.work_dir.glob("*/*/conf.json"):
            if path.parent.name.startswith("_") or path.parent.parent.name.startswith("_"):
                continue
            
            try:
                feed_name = path.parent.name
                self.feed_name_group_map[feed_name] = path.parent.parent.name
                self.feed_alias_name_map[feed_name] = feed_name
                self.feed_name_alias_map[feed_name] = feed_name
                with open(path, 'r') as infile:
                    json_data = json.load(infile)
                    self.feed_name_config_map[feed_name] = json_data["configuration"]
            except Exception as e:
                LOGGER.error("can't load configuraion of feed '%s', %s", path, str(e))


    def load_all_html_files(self) -> None:
        LOGGER.debug("# load_all_html_files()")
        for path in ProblemChecker.work_dir.glob("*/*/html/*"):
            if path.parent.name.startswith("_") or path.parent.parent.name.startswith("_"):
                continue
            if path.suffix == ".html":
                relative_path = path.parent.parent.name + "/html/" + path.name
                s = path.stat()
                self.html_file_size_map[relative_path] = s.st_size

                # html file with normal size should have image tag
                # would find html files with zero count of image tag
                if s.st_size > FeedMaker.get_size_of_template_with_image_tag(path.name):
                    self.html_file_image_tag_count_map[relative_path] = 0
                with open(path, 'r') as infile:
                    for line in infile:
                        # image tag counting
                        if re.search(r'1x1.jpg', line):
                            self.html_file_image_tag_count_map[relative_path] = self.html_file_image_tag_count_map.get(relative_path, 0) + 1
                        # image-not-found.png counting
                        if re.search(r'image-not-found\.png', line):
                            self.html_file_image_not_found_count_map[relative_path] = self.html_file_image_not_found_count_map.get(relative_path, 0) + 1


    def load_all_result_files(self) -> None:
        for file in ProblemChecker.result_dir.iterdir():
            if file.suffix == ".xml":
                try:
                    file_path = ProblemChecker.result_dir / file
                    feed_name = file.stem
                    s = file_path.stat()
                    self.feed_name_result_info_map[feed_name] = {"mtime": s.st_mtime, "size": s.st_size}
                except Exception as e:
                    LOGGER.error("can't get stat from result '%s', %s", file_path, str(e))


    def load_all_progress_info_from_files(self) -> None:
        LOGGER.debug("# load_all_progress_info_from_files()")
        for feed_name, config in self.feed_name_config_map.items():
            if "collection" in config and "is_completed" in config["collection"]:
                if config["collection"]["is_completed"]:
                    index = 0
                    file_path = ProblemChecker.work_dir / self.feed_name_group_map[feed_name] / feed_name / "start_idx.txt"
                    with open(file_path, 'r') as infile:
                        line = infile.readline()
                        index = int(line.split('\t')[0])

                    url_list: List[str] = []
                    dir_name = ProblemChecker.work_dir / self.feed_name_group_map[feed_name] / feed_name / "newlist"
                    for file in dir_name.iterdir():
                        if file.suffix == ".txt":
                            with open(dir_name / file, 'r') as infile:
                                for line in infile:
                                    url = line.split('\t')[0]
                                    url_list.append(url)
                    count = len(list(set(url_list)))

                    unit_size = config["collection"]["unit_size_per_day"] 
                    progress_ratio = (index + 4) * 100 / count
                    remainder = count - (index + 4)
                    num_days = int(math.ceil(remainder / unit_size))

                    self.feed_name_progress_info_map[feed_name] = index, count, progress_ratio, unit_size, num_days


    def load_all_httpd_access_files(self) -> None:
        LOGGER.debug("# load_all_httpd_access_files()")
        # read access.log for 1 month
        today = datetime.today()
        for i in range(30, -1, -1):
            date_str = (today - timedelta(days=i)).strftime("%y%m%d")
            file_path = ProblemChecker.httpd_access_log_dir / ("access.log." + date_str)
            with open(file_path, 'r') as infile:
                for line in infile:
                    # view
                    m = re.search(r'\[(?P<date>\d+/\w+/\d+):\d+:\d+:\d+ \+\d+\] "GET /img/1x1\.jpg\?feed=(?P<feed_name>[\w\.\_\-]+)\.xml\S* HTTP\S+" (?P<status_code>\d+) (?:\d+|-) "[^"]*" "[^"]*"', line)
                    if m:
                        feed_name = m.group("feed_name")
                        feed_alias = self.feed_name_alias_map.get(feed_name, feed_name)
                        status_code = int(m.group("status_code"))
                        date = datetime.strptime(m.group("date"), "%d/%b/%Y")
                        # determine the latest view date & status
                        if not (feed_alias in self.feed_alias_access_info_map and "view_time" in self.feed_alias_access_info_map[feed_alias]):
                            access_info = self.feed_alias_access_info_map.get(feed_alias, {})
                            access_info["view_time"] = date
                            access_info["view_status"] = status_code
                            access_info["is_in_xml_dir"] = False
                            self.feed_alias_access_info_map[feed_alias] = access_info
                    # access
                    m = re.search(r'\[(?P<date>\d+/\w+/\d+):\d+:\d+:\d+ \+\d+\] "GET /(?P<feed>(xml/)?(?P<feed_alias>[\w\.\_\-]+))\.xml\S* HTTP\S+" (?P<status_code>\d+) (?:\d+|-) "[^"]*" "[^"]*"', line)
                    if m:
                        feed = m.group("feed")
                        if feed in ["sitemap", "sitemanager", "filezilla", "clientaccesspolicy"]:
                            continue
                        feed_alias = m.group("feed_alias")
                        status_code = int(m.group("status_code"))
                        date = datetime.strptime(m.group("date"), "%d/%b/%Y")
                        # determine the latest access date & status
                        if not (feed_alias in self.feed_alias_access_info_map and "accesss_date" in self.feed_alias_access_info_map[feed_alias]):
                            access_info = self.feed_alias_access_info_map.get(feed_alias, {})
                            access_info["access_time"] = date
                            access_info["access_status"] = status_code
                            access_info["is_in_xml_dir"] = feed.startswith("xml/")
                            self.feed_alias_access_info_map[feed_alias] = access_info


    def load_htaccess_file(self) -> None:
        with open(ProblemChecker.htaccess_file, 'r') as infile:
            for line in infile:
                m = re.search(r'^RewriteRule\s+\^(?P<feed_alias>[^\t]+)\\\.xml\$\s+xml/(?P<feed_name>[^\t]+)\\\.xml\s*$', line)
                if m:
                    feed_alias = re.sub(r'\\\.', '.', m.group("feed_alias"))
                    feed_name = re.sub(r'\\\.', '.', m.group("feed_name"))
                    self.feed_alias_name_map[feed_alias] = feed_name
                    self.feed_name_alias_map[feed_name] = feed_alias



    def merge_all_feeds_status(self) -> None:
        # alias -> name, htaccess
        for alias, name in self.feed_alias_name_map.items():
            status_info = self.feed_alias_status_info_map.get(alias, {})
            status_info["feed_name"] = name
            status_info["htaccess"] = True
            # default values for unspecified attributes
            status_info["http_request"] = status_info.get("http_request", False)
            status_info["public_html"] = status_info.get("public_html", False)
            status_info["feedmaker"] = status_info.get("feedmaker", False)
            status_info["last_access_time"] = status_info.get("last_access_time", "")
            status_info["last_view_time"] = status_info.get("last_view_time", "")
            self.feed_alias_status_info_map[alias] = status_info

        # alias -> http_request
        for alias, access_info in self.feed_alias_access_info_map.items():
            status_info = self.feed_alias_status_info_map.get(alias, {})
            status_info["last_access_time"] = access_info.get("access_time", "")
            status_info["last_view_time"] = access_info.get("view_time", "")
            status_info["http_request"] = True
            # default values for unspecified attributes
            status_info["feed_name"] = self.feed_alias_name_map.get(alias, "")
            status_info["htaccess"] = status_info.get("htaccess", False)
            status_info["public_html"] = status_info.get("public_html", False)
            status_info["feedmaker"] = status_info.get("feedmaker", False)
            status_info["last_access_time"] = status_info.get("last_access_time", "")
            status_info["last_view_time"] = status_info.get("last_view_time", "")
            self.feed_alias_status_info_map[alias] = status_info

        # alias -> public_html
        for name in self.feed_name_result_info_map:
            if name in self.feed_name_alias_map:
                alias = self.feed_name_alias_map[name]
                status_info = self.feed_alias_status_info_map.get(alias, {})
                status_info["public_html"] = True
                # default values for unspecified attributes
                status_info["feed_name"] = self.feed_alias_name_map.get(alias, "")
                status_info["htaccess"] = status_info.get("htaccess", False)
                status_info["http_request"] = status_info.get("http_request", False)
                status_info["feedmaker"] = status_info.get("feedmaker", False)
                status_info["last_access_time"] = status_info.get("last_access_time", "")
                status_info["last_view_time"] = status_info.get("last_view_time", "")
                self.feed_alias_status_info_map[alias] = status_info

        # feedmaker
        for name in self.feed_name_config_map:
            if name in self.feed_name_alias_map:
                alias = self.feed_name_alias_map[name]
                status_info = self.feed_alias_status_info_map.get(alias, {})
                status_info["feedmaker"] = True
                # default values for unspecified attributes
                status_info["feed_name"] = self.feed_alias_name_map.get(alias, "")
                status_info["htaccess"] = status_info.get("htaccess", False)
                status_info["http_request"] = status_info.get("http_request", False)
                status_info["public_html"] = status_info.get("public_html", False)
                status_info["last_access_time"] = status_info.get("last_access_time", "")
                status_info["last_view_time"] = status_info.get("last_view_time", "")
                self.feed_alias_status_info_map[alias] = status_info


def main() -> int:
    LOGGER.debug("# main()")
    checker = ProblemChecker()
    checker.load_htaccess_file()
    checker.load_all_config_files()
    checker.load_all_progress_info_from_files()
    checker.load_all_result_files()
    checker.load_all_html_files()
    checker.load_all_httpd_access_files()
    checker.merge_all_feeds_status()

    checker.check_validity_of_configuration_files()
    checker.check_size_time_of_result_files()
    checker.check_html_content()
    checker.check_incremental_feeding()
    checker.check_garbage_feeds()
    checker.check_feed_status()

    return 0


if __name__ == "__main__":
    sys.exit(main())
