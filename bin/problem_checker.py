#!/usr/bin/env python


import os
import json
import math
import re
from pathlib import Path
from datetime import datetime, timedelta
import logging
import logging.config
from typing import List, Dict, Any, Union, Optional
from feed_maker import FeedMaker

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class ProblemChecker:
    work_dir = Path(os.environ["FEED_MAKER_WORK_DIR"])
    public_feed_dir = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"])
    httpd_access_log_dir = Path(os.environ["HOME"]) / "apps/logs"
    htaccess_file = public_feed_dir / ".." / ".htaccess"

    def __init__(self) -> None:
        # alias -> name
        self.feed_alias_name_map: Dict[str, str] = {}
        # name -> alias
        self.feed_name_aliases_map: Dict[str, Dict[str, Any]] = {}
        # name -> title
        self.feed_name_title_map: Dict[str, Any] = {}
        # name -> group
        self.feed_name_group_map: Dict[str, str] = {}
        # name -> config
        self.feed_name_config_map: Dict[str, Any] = {}
        # name -> update date of rss file
        self.feed_name_rss_info_map: Dict[str, Any] = {}
        # name -> progress(index,count,progress_ratio,unit_size,num_days)
        self.feed_name_progress_info_list: List[Dict[str, Any]] = []
        # name -> public_feed_info(size, mtime)
        self.public_feed_info_list: List[Dict[str, Any]] = []
        # alias -> access_info(access_status,access_date,view_status,view_date,is_in_xml_dir)
        self.feed_alias_access_info_map: Dict[str, Dict[str, Any]] = {}
        # alias -> status_info(htaccess,http_request,public_html,feedmaker)
        self.feed_alias_status_info_map: Dict[str, Dict[str, Any]] = {}
        self.feed_alias_status_info_list: List[Dict[str, Any]] = []
        # html -> size
        self.html_file_size_list: List[Dict[str, Any]] = []
        # html -> image_tag count
        self.html_file_with_many_image_tag_list: List[Dict[str, Any]] = []
        self.html_file_without_image_tag_list: List[Dict[str, Any]] = []
        # html -> image-not-found count
        self.html_file_image_not_found_list: List[Dict[str, Any]] = []
        # name -> list_url count
        self.feed_name_list_url_count_list: List[Dict[str, Any]] = []
        # element name -> count
        self.element_name_count_list: List[Dict[str, Any]] = []

    def __del__(self) -> None:
        del self.feed_alias_name_map
        del self.feed_name_aliases_map
        del self.feed_name_title_map
        del self.feed_name_group_map
        del self.feed_name_config_map
        del self.feed_name_rss_info_map
        del self.feed_name_progress_info_list
        del self.public_feed_info_list
        del self.feed_alias_access_info_map
        del self.feed_alias_status_info_map
        del self.feed_alias_status_info_list
        del self.html_file_size_list
        del self.html_file_with_many_image_tag_list
        del self.html_file_without_image_tag_list
        del self.html_file_image_not_found_list
        del self.feed_name_list_url_count_list
        del self.element_name_count_list

    def load_htaccess_file(self, do_merge=False) -> None:
        self.feed_alias_name_map.clear()
        self.feed_name_aliases_map.clear()
        with open(self.htaccess_file, 'r') as infile:
            for line in infile:
                m = re.search(r'^RewriteRule\s+\^(?P<feed_alias>[^\t]+)\\\.xml\$\s+xml/(?P<feed_name>[^\t]+)\\\.xml\s*$', line)
                if m:
                    feed_alias = re.sub(r'\\\.', '.', m.group("feed_alias"))
                    feed_name = re.sub(r'\\\.', '.', m.group("feed_name"))
                    self.feed_alias_name_map[feed_alias] = feed_name
                    aliases = self.feed_name_aliases_map.get(feed_name, {})
                    aliases[feed_alias] = True
                    self.feed_name_aliases_map[feed_name] = aliases

        print("The loading of htaccess file is done. %d items" % len(self.feed_alias_name_map))
        if do_merge:
            self.merge_all_feeds_status()

    def load_all_config_rss_files(self, do_merge=False) -> None:
        LOGGER.debug("# load_all_config_rss_files()")
        self.feed_name_rss_info_map.clear()
        feed_name_list_url_count_map: Dict[str, int] = {}
        element_name_count_map: Dict[str, int] = {}
        for group_path in self.work_dir.iterdir():
            group_name = group_path.name
            if not group_path.is_dir() or group_name in ["test", "logs", ".git"]:
                continue
            for feed_path in group_path.iterdir():
                if not feed_path.is_dir():
                    continue
                feed_name = feed_path.name
                try:
                    self.feed_name_group_map[feed_name] = group_name
                    with open(feed_path / "conf.json", 'r') as infile:
                        json_data = json.load(infile)
                        if json_data and "configuration" in json_data:
                            self.feed_name_config_map[feed_name] = json_data["configuration"]
                            if "rss" in json_data["configuration"] and "title" in json_data["configuration"]["rss"]:
                                title = json_data["configuration"]["rss"]["title"]
                                if "::" in title:
                                    title = title.split("::")[0]
                            else:
                                title = ""
                            self.feed_name_title_map[feed_name] = title

                            if "collection" in json_data["configuration"] and "list_url_list" in json_data["configuration"]["collection"] and not group_name.startswith("_") and not feed_name.startswith("_"):
                                feed_name_list_url_count_map[feed_name] = len(json_data["configuration"]["collection"]["list_url_list"])
                            if "collection" in json_data["configuration"]:
                                for element in json_data["configuration"]["collection"]:
                                    element_name_count_map[element] = element_name_count_map.get(element, 0) + 1
                            if "extraction" in json_data["configuration"]:
                                for element in json_data["configuration"]["extraction"]:
                                    element_name_count_map[element] = element_name_count_map.get(element, 0) + 1
                            if "rss" in json_data["configuration"]:
                                for element in json_data["configuration"]["rss"]:
                                    element_name_count_map[element] = element_name_count_map.get(element, 0) + 1
                    rss_file_path = feed_path / (feed_name + ".xml")
                    if rss_file_path.is_file():
                        s = rss_file_path.stat()
                        update_date = datetime.fromtimestamp(s.st_mtime)
                        self.feed_name_rss_info_map[feed_name] = {"update_date": update_date}
                except IOError:
                    pass

        self.feed_name_list_url_count_list.clear()
        self.element_name_count_list.clear()
        for feed_name, count in feed_name_list_url_count_map.items():
            if count != 1:
                self.feed_name_list_url_count_list.append({"feed_name": feed_name, "group_name": self.feed_name_group_map.get(feed_name, ""), "feed_title": self.feed_name_title_map.get(feed_name, ""), "count": count})
        for element_name, count in element_name_count_map.items():
            self.element_name_count_list.append({"element_name": element_name, "count": count})

        print("The loading of all config files and rss files is done. %d items" % len(self.feed_name_rss_info_map))
        if do_merge:
            self.merge_all_feeds_status()

    def load_all_public_feed_files(self, do_merge=False) -> None:
        self.public_feed_info_list.clear()
        for path in self.public_feed_dir.iterdir():
            if path.suffix == ".xml":
                feed_name = path.stem
                if not feed_name.startswith("_"):
                    try:
                        s = path.stat()
                        upload_date = datetime.fromtimestamp(s.st_mtime)
                        self.public_feed_info_list.append({"feed_name": feed_name, "feed_title": self.feed_name_title_map.get(feed_name, ""), "file_path": str(path.relative_to(self.public_feed_dir)), "upload_date": self.convert_datetime_to_str(upload_date), "size": s.st_size})
                    except Exception as e:
                        LOGGER.error("can't get stat from public_feed '%s', %s", path, str(e))

        print("The loading of public feed file is done. %d items" % len(self.public_feed_info_list))
        if do_merge:
            self.merge_all_feeds_status()

    @staticmethod
    def get_html_file_name(path: Path) -> str:
        return path.parent.parent.name + "/html/" + path.name

    def load_all_html_files(self, do_merge=False) -> None:
        LOGGER.debug("# load_all_html_files()")
        html_file_image_tag_count_map: Dict[Path, int] = {}
        html_file_image_not_found_count_map: Dict[Path, int] = {}
        self.html_file_size_list.clear()
        html_file_count = 0

        for path in self.work_dir.glob("*/*/html/*"):
            if path.parent.name.startswith("_") or path.parent.parent.name.startswith("_"):
                continue
            if path.suffix == ".html":
                s = path.stat()
                html_file_count += 1
                if 124 < s.st_size < 434:
                    self.html_file_size_list.append({"file_name": self.get_html_file_name(path), "file_path": str(path.relative_to(self.work_dir)), "size": s.st_size, "update_date": self.convert_datetime_to_str(datetime.fromtimestamp(s.st_mtime))})

                # html file with normal size should have image tag
                # would find html files with zero count of image tag
                if s.st_size > FeedMaker.get_size_of_template_with_image_tag(path.name):
                    html_file_image_tag_count_map[path] = 0
                with open(path, 'r') as infile:
                    for line in infile:
                        # image tag counting
                        if re.search(r'1x1.jpg', line):
                            html_file_image_tag_count_map[path] = html_file_image_tag_count_map.get(path, 0) + 1
                        # image-not-found.png counting
                        if re.search(r'image-not-found\.png', line):
                            html_file_image_not_found_count_map[path] = html_file_image_not_found_count_map.get(path, 0) + 1

        self.html_file_with_many_image_tag_list.clear()
        self.html_file_without_image_tag_list.clear()
        self.html_file_image_not_found_list.clear()
        for path, count in html_file_image_tag_count_map.items():
            if count > 1:
                self.html_file_with_many_image_tag_list.append({"file_name": self.get_html_file_name(path), "file_path": str(path.relative_to(self.work_dir)), "count": count})
            if count < 1:
                self.html_file_without_image_tag_list.append({"file_name": self.get_html_file_name(path), "file_path": str(path.relative_to(self.work_dir)), "count": count})
        for path, count in html_file_image_not_found_count_map.items():
            self.html_file_image_not_found_list.append({"file_name": self.get_html_file_name(path), "file_path": str(path.relative_to(self.work_dir)), "count": count})

        print("The loading of all html files is done. %d items" % html_file_count)
        if do_merge:
            self.merge_all_feeds_status()

    def load_all_progress_info_from_files(self, do_merge=False) -> None:
        LOGGER.debug("# load_all_progress_info_from_files()")
        self.feed_name_progress_info_list.clear()
        for feed_name, config in self.feed_name_config_map.items():
            if feed_name.startswith("_") or self.feed_name_group_map[feed_name].startswith("_"):
                continue
            if "collection" in config and "is_completed" in config["collection"]:
                if config["collection"]["is_completed"]:
                    index = 0
                    file_path = self.work_dir / self.feed_name_group_map[feed_name] / feed_name / "start_idx.txt"
                    if file_path.is_file():
                        with open(file_path, 'r') as infile:
                            line = infile.readline()
                            index = int(line.split('\t')[0])

                    url_list: List[str] = []
                    dir_name = self.work_dir / self.feed_name_group_map[feed_name] / feed_name / "newlist"
                    if dir_name.is_dir():
                        for file in dir_name.iterdir():
                            if file.suffix == ".txt":
                                with open(dir_name / file, 'r') as infile:
                                    for line in infile:
                                        url = line.split('\t')[0]
                                        url_list.append(url)
                    count = len(list(set(url_list)))

                    unit_size = config["collection"].get("unit_size_per_day", 1)
                    progress_ratio = (index + 4) * 100 / (count + 1)
                    remainder = count - (index + 4)
                    num_days = int(math.ceil(remainder / unit_size))

                    self.feed_name_progress_info_list.append({"feed_name": feed_name, "feed_title": self.feed_name_title_map[feed_name], "group_name": self.feed_name_group_map[feed_name], "index": index, "count": count, "ratio": int(progress_ratio), "unit_size": unit_size, "due_date": self.convert_datetime_to_str(datetime.now() + timedelta(days=num_days))})

        print("The loading of all progress info is done. %d items" % len(self.feed_name_progress_info_list))
        if do_merge:
            self.merge_all_feeds_status()

    def load_all_httpd_access_files(self, do_merge=False) -> None:
        LOGGER.debug("# load_all_httpd_access_files()")
        self.feed_alias_access_info_map.clear()
        # read access.log for 1 month
        today = datetime.today()
        for i in range(30, -1, -1):
            date_str = (today - timedelta(days=i)).strftime("%y%m%d")
            file_path = self.httpd_access_log_dir / ("access.log." + date_str)
            if not file_path.is_file():
                continue
            with open(file_path, 'r') as infile:
                for line in infile:
                    # view
                    m = re.search(r'\[(?P<date>\d+/\w+/\d+):\d+:\d+:\d+ \+\d+] "GET /img/1x1\.jpg\?feed=(?P<feed_name>[\w._\-]+)\.xml\S* HTTP\S+" (?P<status_code>\d+) (?:\d+|-) "[^"]*" "[^"]*"', line)
                    if m:
                        feed_name = m.group("feed_name")
                        for feed_alias in self.feed_name_aliases_map.get(feed_name, {}):
                            status_code = int(m.group("status_code"))
                            if status_code != 200:
                                continue
                            date = datetime.strptime(m.group("date"), "%d/%b/%Y")
                            # determine the latest view date & status
                            if not (feed_alias in self.feed_alias_access_info_map and "view_date" in self.feed_alias_access_info_map[feed_alias]):
                                access_info = self.feed_alias_access_info_map.get(feed_alias, {})
                                access_info["feed_alias"] = feed_alias
                                access_info["feed_name"] = feed_name
                                access_info["view_date"] = date
                                access_info["view_status"] = status_code
                                access_info["is_in_xml_dir"] = False
                                self.feed_alias_access_info_map[feed_alias] = access_info
                    # access
                    m = re.search(r'\[(?P<date>\d+/\w+/\d+):\d+:\d+:\d+ \+\d+] "GET /(?P<feed>(xml/)?(?P<feed_alias>[\w._\-]+))\.xml\S* HTTP\S+" (?P<status_code>\d+) (?:\d+|-) "[^"]*" "[^"]*"', line)
                    if m:
                        feed = m.group("feed")
                        feed_alias = m.group("feed_alias")
                        feed_name = self.feed_alias_name_map.get(feed_alias, feed_alias)
                        status_code = int(m.group("status_code"))
                        if status_code != 200:
                            continue
                        date = datetime.strptime(m.group("date"), "%d/%b/%Y")
                        # determine the latest access date & status
                        if not (feed_alias in self.feed_alias_access_info_map and "accesss_date" in self.feed_alias_access_info_map[feed_alias]):
                            access_info = self.feed_alias_access_info_map.get(feed_alias, {})
                            access_info["feed_alias"] = feed_alias
                            access_info["feed_name"] = feed_name
                            access_info["access_date"] = date
                            access_info["access_status"] = status_code
                            access_info["is_in_xml_dir"] = feed.startswith("xml/")
                            self.feed_alias_access_info_map[feed_alias] = access_info

        print("The loading of http access log is done. %d items" % len(self.feed_alias_access_info_map))
        if do_merge:
            self.merge_all_feeds_status()

    @staticmethod
    def convert_datetime_to_str(date: Optional[Union[str, datetime]]) -> str:
        if not date:
            return ""
        if isinstance(date, str):
            return date
        if isinstance(date, datetime):
            return date.astimezone().strftime("%y-%m-%d")
        return ""

    def get_status_info_with_default(self, alias: str) -> Dict[str, Any]:
        if alias in self.feed_alias_status_info_map:
            return self.feed_alias_status_info_map[alias]
        return {"http_request": False, "htaccess": False, "public_html": False, "feedmaker": False, "access_date": None, "view_date": None, "upload_date": None, "update_date": None}

    def merge_all_feeds_status(self) -> None:
        self.feed_alias_status_info_map.clear()
        self.feed_alias_status_info_list.clear()

        # feed_alias_name_map(alias -> name), check 'htaccess'
        for feed_alias, feed_name in self.feed_alias_name_map.items():
            status_info = self.get_status_info_with_default(feed_alias)
            status_info["feed_alias"] = feed_alias
            status_info["feed_name"] = feed_name
            status_info["htaccess"] = True
            self.feed_alias_status_info_map[feed_alias] = status_info

        # feed_alias_access_info_map(alias -> access_info), check 'http_request'
        for feed_alias, access_info in self.feed_alias_access_info_map.items():
            status_info = self.get_status_info_with_default(feed_alias)
            status_info["access_date"] = access_info.get("access_date", None)
            status_info["view_date"] = access_info.get("view_date", None)
            status_info["http_request"] = True
            status_info["feed_alias"] = feed_alias
            feed_name = self.feed_alias_name_map.get(feed_alias, "")
            status_info["feed_name"] = status_info.get("feed_name", feed_name)
            self.feed_alias_status_info_map[feed_alias] = status_info

        # public_feed_info_list(public_feed_info(name)), check 'public_html'
        for public_feed_info in self.public_feed_info_list:
            feed_name = public_feed_info["feed_name"]
            file_path = public_feed_info["file_path"]
            upload_date = public_feed_info["upload_date"]
            if feed_name not in self.feed_name_aliases_map:
                status_info = self.get_status_info_with_default(feed_name)
                status_info["public_html"] = True
                status_info["upload_date"] = upload_date
                status_info["feed_alias"] = ""
                status_info["file_path"] = file_path
                status_info["feed_name"] = feed_name
                self.feed_alias_status_info_map[feed_name] = status_info
                continue

            for feed_alias in self.feed_name_aliases_map.get(feed_name, {}):
                status_info = self.get_status_info_with_default(feed_alias)
                status_info["public_html"] = True
                status_info["upload_date"] = upload_date
                status_info["feed_alias"] = feed_alias
                status_info["file_path"] = file_path
                status_info["feed_name"] = feed_name
                self.feed_alias_status_info_map[feed_alias] = status_info

        # rss_info_map(name -> rss_info), check 'feedmaker'
        for feed_name in self.feed_name_rss_info_map:
            if feed_name not in self.feed_name_aliases_map:
                status_info = self.get_status_info_with_default(feed_name)
                status_info["feedmaker"] = True
                status_info["update_date"] = self.feed_name_rss_info_map[feed_name]["update_date"]
                status_info["feed_alias"] = ""
                status_info["feed_name"] = feed_name
                self.feed_alias_status_info_map[feed_name] = status_info
                continue

            for feed_alias in self.feed_name_aliases_map.get(feed_name, {}):
                status_info = self.get_status_info_with_default(feed_alias)
                status_info["feedmaker"] = True
                status_info["update_date"] = self.feed_name_rss_info_map[feed_name]["update_date"]
                status_info["feed_alias"] = feed_alias
                status_info["feed_name"] = feed_name
                self.feed_alias_status_info_map[feed_alias] = status_info

        # merge
        for _, status_info in self.feed_alias_status_info_map.items():
            feed_name = status_info.get("feed_name", "")

            # exclude very normal cases
            if not status_info["http_request"] and not status_info["htaccess"] and not status_info["public_html"] and not status_info["feedmaker"]:
                # unrequested and deleted
                continue
            if status_info["http_request"] and not status_info["htaccess"] and not status_info["public_html"] and not status_info["feedmaker"]:
                if status_info["access_date"] and status_info["access_date"] < datetime.today() - timedelta(days=14):
                    # requested a few weeks ago but deleted
                    continue
            if status_info["http_request"] and status_info["htaccess"] and status_info["public_html"] and status_info["feedmaker"]:
                # requested and serviced
                if status_info["access_date"] and datetime.today() - timedelta(days=14) < status_info["access_date"] or status_info["view_date"] and datetime.today() - timedelta(days=14) < status_info["view_date"]:
                    # accessed or viewed recently
                    continue

            status_info["feed_title"] = status_info.get("feed_title", self.feed_name_title_map.get(feed_name, ""))
            status_info["group_name"] = status_info.get("group_name", self.feed_name_group_map.get(feed_name, ""))
            # datetime to string
            status_info["access_date"] = self.convert_datetime_to_str(status_info["access_date"])
            status_info["view_date"] = self.convert_datetime_to_str(status_info["view_date"])
            status_info["upload_date"] = self.convert_datetime_to_str(status_info["upload_date"])
            status_info["update_date"] = self.convert_datetime_to_str(status_info["update_date"])

            self.feed_alias_status_info_list.append(status_info)

        LOGGER.info("The merging of all information is done.")

    def load(self) -> None:
        self.load_htaccess_file()
        self.load_all_config_rss_files()
        self.load_all_public_feed_files()
        self.load_all_progress_info_from_files()
        self.load_all_httpd_access_files()
        self.load_all_html_files()
        self.merge_all_feeds_status()
