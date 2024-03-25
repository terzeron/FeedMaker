#!/usr/bin/env python


import os
import json
import math
import logging.config
from pathlib import Path
from datetime import datetime, timedelta
from itertools import islice
from typing import Dict, Any, Optional, List
from bin.feed_maker_util import PathUtil, Datetime, Data
from bin.db_manager import DBManager, Cursor, IntegrityError

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class FeedManager:
    work_dir = Path(os.environ["FM_WORK_DIR"])
    public_feed_dir = Path(os.environ["WEB_SERVICE_FEEDS_DIR"])

    def __init__(self, db_manager: Optional[DBManager] = None) -> None:
        if db_manager:
            self.db = db_manager
        else:
            self.db = DBManager(os.environ["FM_DB_HOST"], int(os.environ["FM_DB_PORT"]), os.environ["MYSQL_DATABASE"], os.environ["MYSQL_USER"], os.environ["MYSQL_PASSWORD"])

    def __del__(self) -> None:
        del self.db

    def get_feed_name_list_url_count_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_feed_name_list_url_count_map()")
        feed_name_list_url_count_map = {}

        for row in self.db.query("SELECT * FROM feed_info WHERE url_list_count > 1"):
            feed_name = row["feed_name"]
            feed_name_list_url_count_map[feed_name] = {
                "feed_name": feed_name,
                "feed_title": row["feed_title"],
                "group_name": row["group_name"],
                "count": row["url_list_count"]
            }

        return feed_name_list_url_count_map

    def get_element_name_count_map(self) -> Dict[str, Any]:
        LOGGER.debug("# get_element_name_count_map()")
        element_name_count_map = {}

        for row in self.db.query("SELECT * FROM element_name_count"):
            element_name = row["element_name"]
            element_name_count_map[element_name] = {
                "element_name": element_name,
                "count": row["count"]
            }

        return element_name_count_map

    def remove_config_info(self, feed_dir_path: Path) -> None:
        LOGGER.debug("# remove_config_info(feed_dir_path='%s')", PathUtil.short_path(feed_dir_path))
        feed_name = feed_dir_path.stem
        with self.db.get_connection_and_cursor() as (connection, cursor):
            self.db.execute(cursor, "UPDATE feed_info SET config = NULL, config_modify_date = NULL WHERE feed_name = %s", feed_name)
            self.db.commit(connection)
        LOGGER.info("* The removing of config info of feed '%s' is done.", feed_name)

    def _add_config_info(self, cursor: Cursor, feed_dir_path: Path, element_name_count_map: Optional[Dict[str, int]] = None) -> None:
        if not feed_dir_path.is_dir():
            LOGGER.error("can't find a feed directory '%s'", PathUtil.short_path(feed_dir_path))
            return
        element_name_count_map = element_name_count_map if element_name_count_map is not None else {}
        feed_name = feed_dir_path.name
        group_name = feed_dir_path.parent.name

        config_str = None
        config_modify_date_str = None
        title = None
        url_list_count = None
        is_completed = None
        unit_size_per_day = None

        if group_name in (".mypy_cache", ".git", "test"):
            return
        if group_name.startswith("_") or feed_name.startswith("_"):
            # disabled feed
            if group_name.startswith("_"):
                group_name = group_name[1:]
            if feed_name.startswith("_"):
                feed_name = feed_name[1:]
        else:
            # active feed
            conf_json_file_path = feed_dir_path / "conf.json"
            if feed_dir_path.is_dir() and conf_json_file_path.is_file():
                s = feed_dir_path.stat()
                config_modify_date = datetime.utcfromtimestamp(s.st_mtime)
                config_modify_date_str = Datetime.convert_datetime_to_str(config_modify_date)

                with conf_json_file_path.open("r", encoding="utf-8") as infile:
                    json_data = json.load(infile)
                if json_data and "configuration" in json_data:
                    config_str = json.dumps(json_data["configuration"])
                    rss_data = json_data["configuration"].get("rss", {})
                    title = rss_data.get("title", "")
                    if "::" in title:
                        title = title.split("::")[0]
                    collection_data = json_data["configuration"].get("collection", {})
                    url_list_count = len(collection_data.get("list_url_list", []))
                    is_completed = collection_data.get("is_completed", False)
                    unit_size_per_day = collection_data.get("unit_size_per_day", 0)

                for sub_config_element in ["collection", "extraction", "rss"]:
                    for element in json_data["configuration"][sub_config_element]:
                        key = sub_config_element[0] + "." + element
                        element_name_count_map[key] = element_name_count_map.get(key, 0) + 1

        try:
            self.db.execute(cursor, "INSERT INTO feed_info (feed_name, feed_title, group_name, config, config_modify_date, url_list_count, is_completed, unit_size_per_day) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", feed_name, title, group_name, config_str, config_modify_date_str, url_list_count, is_completed, unit_size_per_day)
        except IntegrityError:
            self.db.execute(cursor, "UPDATE feed_info SET feed_title = %s, group_name = %s, config = %s, config_modify_date = %s, url_list_count = %s, is_completed = %s, unit_size_per_day = %s WHERE feed_name = %s", title, group_name, config_str, config_modify_date_str, url_list_count, is_completed, unit_size_per_day, feed_name)

    def add_config_info(self, feed_dir_path: Path) -> None:
        feed_name = feed_dir_path.stem
        with self.db.get_connection_and_cursor() as (connection, cursor):
            element_name_count_map: Dict[str, int] = {}
            self._add_config_info(cursor, feed_dir_path, element_name_count_map)
            self._add_element_info(cursor, element_name_count_map)
            self.db.commit(connection)
            LOGGER.info("* The adding of config info of feed '%s' is done.", feed_name)

    def _add_element_info(self, cursor, element_name_count_map: Dict[str, int]) -> None:
        for element_name, count in element_name_count_map.items():
            try:
                self.db.execute(cursor, "INSERT INTO element_name_count (element_name, count) VALUES (%s, %s)", element_name, count)
            except IntegrityError:
                self.db.execute(cursor, "UPDATE element_name_count SET count = %s WHERE element_name = %s", count, element_name)

    def load_all_config_files(self, max_num_feeds: Optional[int] = None) -> None:
        LOGGER.debug("# load_all_config_files(max_num_feeds=%r)", max_num_feeds)
        start_ts = datetime.now()
        with self.db.get_connection_and_cursor() as (connection, cursor):
            num_items = 0
            element_name_count_map: Dict[str, int] = {}
            for group_dir_path in islice(self.work_dir.iterdir(), max_num_feeds):
                if not group_dir_path.is_dir():
                    continue

                for feed_dir_path in group_dir_path.iterdir():
                    if not feed_dir_path.is_dir():
                        continue
                    self._add_config_info(cursor, feed_dir_path, element_name_count_map)
                    self._add_element_info(cursor, element_name_count_map)
                    num_items += 1
            self.db.commit(connection)
        end_ts = datetime.now()
        LOGGER.info("* The loading of all config files is done. %d items / %s sec", num_items, (end_ts - start_ts))

    def remove_rss_info(self, feed_dir_path: Path) -> None:
        LOGGER.debug("# remove_rss_info(feed_dir_path='%s')", PathUtil.short_path(feed_dir_path))
        feed_name = feed_dir_path.stem
        with self.db.get_connection_and_cursor() as (connection, cursor):
            self.db.execute(cursor, "UPDATE feed_info SET feedmaker = NULL, rss_update_date = NULL WHERE feed_name = %s", feed_name)
            self.db.commit(connection)
        LOGGER.info("* The removing of rss info of feed '%s' is done.", feed_name)

    def _add_rss_info(self, cursor: Cursor, feed_dir_path: Path) -> None:
        if not feed_dir_path.is_dir():
            LOGGER.error("can't find a feed directory '%s'", PathUtil.short_path(feed_dir_path))
            return
        feed_name = feed_dir_path.name
        group_name = feed_dir_path.parent.name

        feedmaker: Optional[bool] = None
        rss_update_date_str = None

        if group_name in (".mypy_cache", ".git", "test"):
            return
        if group_name.startswith("_") or feed_name.startswith("_"):
            # disabled feed
            if feed_name.startswith("_"):
                feed_name = feed_name[1:]
        else:
            # active feed
            rss_file_path = feed_dir_path / f"{feed_name}.xml"
            if rss_file_path.is_file():
                feedmaker = True
                s = rss_file_path.stat()
                rss_update_date = datetime.utcfromtimestamp(s.st_mtime)
                rss_update_date_str = Datetime.convert_datetime_to_str(rss_update_date)

        try:
            self.db.execute(cursor, "INSERT INTO feed_info (feed_name, feedmaker, rss_update_date) VALUES (%s, %s, %s)", feed_name, feedmaker, rss_update_date_str)
        except IntegrityError:
            self.db.execute(cursor, "UPDATE feed_info SET feedmaker = %s, rss_update_date = %s WHERE feed_name = %s", feedmaker, rss_update_date_str, feed_name)

    def add_rss_info(self, feed_dir_path: Path) -> None:
        feed_name = feed_dir_path.stem
        with self.db.get_connection_and_cursor() as (connection, cursor):
            self._add_rss_info(cursor, feed_dir_path)
            self.db.commit(connection)
        LOGGER.info("* The adding of rss info of feed '%s' is done.", feed_name)

    def load_all_rss_files(self, max_num_feeds: Optional[int] = None) -> None:
        LOGGER.debug("# load_all_rss_files(max_num_feeds=%r)", max_num_feeds)
        start_ts = datetime.now()
        with self.db.get_connection_and_cursor() as (connection, cursor):
            num_items = 0
            for group_dir_path in islice(self.work_dir.iterdir(), max_num_feeds):
                if not group_dir_path.is_dir():
                    continue

                for feed_dir_path in group_dir_path.iterdir():
                    if not feed_dir_path.is_dir():
                        continue
                    self._add_rss_info(cursor, feed_dir_path)
                    num_items += 1
            self.db.commit(connection)
        end_ts = datetime.now()
        LOGGER.info("* The loading of all rss files is done. %d items / %s sec", num_items, (end_ts - start_ts))

    def get_feed_name_public_feed_info_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_feed_name_public_feed_info_map()")
        feed_name_public_feed_info_map = {}

        for row in self.db.query("SELECT * FROM feed_info WHERE public_html = %s", True):
            feed_name = row["feed_name"]
            feed_name_public_feed_info_map[feed_name] = {
                "feed_name": feed_name,
                "feed_title": row["feed_title"],
                "group_name": row["group_name"],
                "file_size": row["file_size"],
                "num_items": row["num_items"],
                "upload_date": row["upload_date"]
            }

        return feed_name_public_feed_info_map

    def remove_public_feed(self, public_feed_file_path: Path) -> None:
        feed_name = public_feed_file_path.stem
        with self.db.get_connection_and_cursor() as (connection, cursor):
            self.db.execute(cursor, "UPDATE feed_info SET public_html = NULL, public_feed_file_path = NULL, file_size = NULL, num_items = NULL, upload_date = NULL WHERE feed_name = %s", feed_name)
            self.db.commit(connection)
        LOGGER.info("* The removing of public feed info of feed '%s' is done.", feed_name)

    def remove_public_feed_by_feed_name(self, feed_name: str) -> None:
        public_feed_file_path = self.public_feed_dir / f"{feed_name}.xml"
        self.remove_public_feed(public_feed_file_path)

    def _add_public_feed(self, cursor: Cursor, public_feed_file_path: Path) -> int:
        if not public_feed_file_path.is_file():
            LOGGER.error("can't find a public feed file '%s'", PathUtil.short_path(public_feed_file_path))
            return 0
        feed_name = public_feed_file_path.stem
        group_name = public_feed_file_path.parent.name

        public_html = None
        path_str = None
        size = None
        num_item_elements = None
        upload_date_str = None

        if group_name in (".mypy_cache", ".git", "test"):
            return 0
        if group_name.startswith("_") or feed_name.startswith("_"):
            # disabled feed
            if feed_name.startswith("_"):
                feed_name = feed_name[1:]
        else:
            # active feed
            with public_feed_file_path.open("r", encoding="utf-8") as infile:
                file_content = infile.read()
            public_html = True
            path_str = PathUtil.short_path(public_feed_file_path)
            num_item_elements = file_content.count("<item>")
            s = public_feed_file_path.stat()
            size = s.st_size
            upload_date = datetime.utcfromtimestamp(s.st_mtime)
            upload_date_str = Datetime.convert_datetime_to_str(upload_date)

        try:
            self.db.execute(cursor, "INSERT INTO feed_info (feed_name, public_html, public_feed_file_path, file_size, num_items, upload_date) VALUES (%s, %s, %s, %s, %s, %s)", feed_name, public_html, path_str, size, num_item_elements, upload_date_str)
        except IntegrityError:
            self.db.execute(cursor, "UPDATE feed_info SET public_html = %s, public_feed_file_path = %s, file_size = %s, num_items = %s, upload_date = %s WHERE feed_name = %s", public_html, path_str, size, num_item_elements, upload_date_str, feed_name)

        return 1

    def add_public_feed(self, public_feed_file_path: Path) -> None:
        feed_name = public_feed_file_path.stem
        with self.db.get_connection_and_cursor() as (connection, cursor):
            self._add_public_feed(cursor, public_feed_file_path)
            self.db.commit(connection)
        LOGGER.info("* The adding of public feed info of file '%s' is done.", feed_name)

    def add_public_feed_by_feed_name(self, feed_name: str) -> None:
        public_feed_file_path = self.public_feed_dir / f"{feed_name}.xml"
        self.add_public_feed(public_feed_file_path)

    def load_all_public_feed_files(self, max_num_public_feeds: Optional[int] = None) -> None:
        LOGGER.debug("# load_all_public_feed_files(max_num_public_feeds=%r)", max_num_public_feeds)
        start_ts = datetime.now()
        with self.db.get_connection_and_cursor() as (connection, cursor):
            num_items = 0
            for feed_file_path in islice(self.public_feed_dir.iterdir(), max_num_public_feeds):
                if feed_file_path.suffix == ".xml":
                    num_items += self._add_public_feed(cursor, feed_file_path)

            self.db.commit(connection)
        end_ts = datetime.now()
        LOGGER.info("* The loading of all public feed files is done. %d items / %s sec", num_items, (end_ts - start_ts))

    def get_feed_name_progress_info_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_feed_name_progress_info_map()")
        feed_name_progress_info_map = {}

        for row in self.db.query("SELECT * FROM feed_info WHERE is_completed = %s", True):
            feed_name = row["feed_name"]
            feed_name_progress_info_map[feed_name] = {
                "feed_name": feed_name,
                "feed_title": row["feed_title"],
                "group_name": row["group_name"],
                "current_index": row["current_index"],
                "total_item_count": row["total_item_count"],
                "unit_size_per_day": row["unit_size_per_day"],
                "progress_ratio": row["progress_ratio"],
                "due_date": row["due_date"]
            }

        return feed_name_progress_info_map

    def remove_progress_info(self, feed_dir_path: Path) -> None:
        feed_name = feed_dir_path.name
        with self.db.get_connection_and_cursor() as (connection, cursor):
            self.db.execute(cursor, "UPDATE feed_info SET is_completed = NULL, current_index = NULL, total_item_count = NULL, unit_size_per_day = NULL, progress_ratio = NULL AND due_date = NULL WHERE feed_name = %s", feed_name)
            self.db.commit(connection)
        LOGGER.info("* The removing of progress info of feed '%s' is done.", feed_name)

    def _add_progress_info(self, cursor: Cursor, feed_dir_path: Path) -> int:
        feed_name = feed_dir_path.name
        if not feed_dir_path.is_dir():
            LOGGER.error("can't find a feed directory '%s'", PathUtil.short_path(feed_dir_path))
            return 0
        group_name = feed_dir_path.parent.name

        is_completed: Optional[bool] = None
        unit_size_per_day = 1 # prevent "divided by zero"
        current_index: Optional[int] = None
        total_item_count: Optional[int] = None
        progress_ratio: Optional[float] = None
        due_date_str: Optional[str] = None
        collect_date_str: Optional[str] = None

        if group_name in (".mypy_cache", ".git", "test"):
            return 0
        if group_name.startswith("_") or feed_name.startswith("_"):
            # disabled feed
            if feed_name.startswith("_"):
                feed_name = feed_name[1:]
        else:
            # active feed
            rows = self.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND is_completed = %s", feed_name, True)
            if rows and len(rows) > 0:
                row = rows[0]
                unit_size_per_day = row["unit_size_per_day"]

                is_completed = True
                # read current_index from start_idx.txt
                current_index = 0
                file_path = feed_dir_path / "start_idx.txt"
                if file_path.is_file():
                    with file_path.open('r', encoding="utf-8") as infile:
                        line = infile.readline()
                    current_index = int(line.split('\t')[0])

                # determine total_item_count & collect_date
                url_list: List[str] = []
                list_dir_path = feed_dir_path / "newlist"
                collect_date = None
                if list_dir_path.is_dir():
                    for list_file_path in list_dir_path.iterdir():
                        if list_file_path.suffix == ".txt":
                            s = list_file_path.stat()
                            temp_dt = datetime.utcfromtimestamp(s.st_mtime)
                            if not collect_date or collect_date < temp_dt:
                                collect_date = temp_dt
                            with list_file_path.open('r', encoding="utf-8") as infile:
                                for line in infile:
                                    url = line.split('\t')[0]
                                    url_list.append(url)
                total_item_count = len(list(set(url_list)))
                collect_date_str = Datetime.convert_datetime_to_str(collect_date)

                # progress information
                progress_ratio = int((current_index + 4) * 100 / (total_item_count + 1))
                remainder = total_item_count - (current_index + 4)
                num_days = int(math.ceil(remainder / unit_size_per_day))
                due_date = datetime.now() + timedelta(days=num_days)
                due_date_str = Datetime.convert_datetime_to_str(due_date)

        try:
            self.db.execute(cursor, "INSERT INTO feed_info (feed_name, is_completed, current_index, total_item_count, progress_ratio, due_date, collect_date) VALUES (%s, %s, %s, %s, %s, %s, %s)", feed_name, is_completed, current_index, total_item_count, progress_ratio, due_date_str, collect_date_str)
        except IntegrityError:
            self.db.execute(cursor, "UPDATE feed_info SET is_completed = %s, current_index = %s, total_item_count = %s, progress_ratio = %s, due_date = %s, collect_date = %s WHERE feed_name = %s", is_completed, current_index, total_item_count, progress_ratio, due_date_str, collect_date_str, feed_name)
        return 1

    def add_progress_info(self, feed_dir_path: Path) -> None:
        feed_name = feed_dir_path.name
        with self.db.get_connection_and_cursor() as (connection, cursor):
            self._add_progress_info(cursor, feed_dir_path)
            self.db.commit(connection)
        LOGGER.info("* The adding of progress info of feed '%s' is done.", feed_name)

    def load_all_progress_info_from_files(self, max_num_feeds: Optional[int] = None) -> None:
        LOGGER.debug("# load_all_progress_info_from_files(max_num_feeds=%r)", max_num_feeds)
        start_ts = datetime.now()
        with self.db.get_connection_and_cursor() as (connection, cursor):
            num_items = 0
            for group_dir_path in islice(self.work_dir.iterdir(), max_num_feeds):
                if not group_dir_path.is_dir():
                    continue

                for feed_dir_path in group_dir_path.iterdir():
                    if not feed_dir_path.is_dir():
                        continue
                    num_items += self._add_progress_info(cursor, feed_dir_path)
            self.db.commit(connection)
        end_ts = datetime.now()
        LOGGER.info("* The loading of all progress info is done. %d items / %s sec", num_items, (end_ts - start_ts))

    def search(self, keyword_list: List[str]) -> List[Dict[str, Any]]:
        LOGGER.debug("# search(keyword_list={keyword_list})")
        search_result = []
        row_list = []
        if keyword_list:
            conditions = " AND ".join([f"feed_name LIKE '%{keyword}%'" for keyword in keyword_list])
            for row in self.db.query(f"SELECT * FROM feed_info WHERE {conditions}"):
                row_list.append(row)
            conditions = " AND ".join([f"feed_title LIKE '%{keyword}%'" for keyword in keyword_list])
            for row in self.db.query(f"SELECT * FROM feed_info WHERE {conditions}"):
                row_list.append(row)

        for row in Data.remove_duplicates(row_list):
            search_result.append({
                "feed_name": row["feed_name"],
                "feed_title": row["feed_title"],
                "group_name": row["group_name"]
            })
        return search_result

    def get_groups(self) -> List[Dict[str, Any]]:
        LOGGER.debug("# get_groups()")
        group_list = []
        for row in self.db.query("SELECT DISTINCT group_name, COUNT(*) AS count FROM feed_info WHERE group_name IS NOT NULL GROUP BY group_name ORDER BY group_name"):
            group_list.append({
                "name": row["group_name"],
                "num_feeds": row["count"]
            })
        return group_list

    def get_feeds_by_group(self, group_name: str) -> List[Dict[str, Any]]:
        LOGGER.debug("# get_feeds_by_group(group_name='%s')", group_name)
        feed_list = []
        for row in self.db.query("SELECT * FROM feed_info WHERE group_name = %s AND config IS NOT NULL", group_name):
            feed_list.append({
                "name": row["feed_name"],
                "title": row["feed_title"]
            })
        return feed_list

    def get_feed_info(self, group_name: str, feed_name: str) -> Dict[str, Any]:
        LOGGER.debug("# get_feed_info(group_name='%s', feed_name='%s')", group_name, feed_name)
        rows = self.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND group_name = %s AND config IS NOT NULL", feed_name, group_name)
        if rows and len(rows) > 0:
            row = rows[0]
            return {
                "feed_name": row["feed_name"],
                "feed_title": row["feed_title"],
                "group_name": row["group_name"],
                "config": json.loads(row["config"]),
                "config_modify_date": row["config_modify_date"],
                "collection_info": {
                    "collect_date": row["collect_date"],
                    "total_item_count": row["total_item_count"]
                },
                "public_feed_info": {
                    "public_feed_file_path": row["public_feed_file_path"],
                    "file_size": row["file_size"],
                    "num_items": row["num_items"],
                    "upload_date": row["upload_date"]
                },
                "progress_info": {
                    "current_index": row["current_index"],
                    "total_item_count": row["total_item_count"],
                    "unit_size_per_day": row["unit_size_per_day"],
                    "progress_ratio": row["progress_ratio"],
                    "due_date": row["due_date"]
                },
            }
        return {}

    def toggle_feed(self, feed_name: str) -> bool:
        LOGGER.debug("# toggle_feed(feed_name='%s')", feed_name)
        with self.db.get_connection_and_cursor() as (connection, cursor):
            rows = self.db.query("SELECT * FROM feed_info WHERE feed_name = %s", feed_name)
            if rows and len(rows) > 0:
                row = rows[0]
                is_active = row["is_active"]
                is_active = not is_active
                self.db.execute(cursor, "UPDATE feed_info SET is_active = %s WHERE feed_name = %s", is_active, feed_name)
                self.db.commit(connection)
                return True
        return False

    def toggle_group(self, group_name: str) -> bool:
        LOGGER.debug("# toggle_group(group_name='%s')", group_name)
        with self.db.get_connection_and_cursor() as (connection, cursor):
            rows = self.db.query("SELECT * FROM feed_info WHERE group_name = %s", group_name)
            if rows and len(rows) > 0:
                for row in rows:
                    is_active = row["is_active"]
                    is_active = not is_active
                    self.db.execute(cursor, "UPDATE feed_info SET is_active = %s WHERE group_name = %s", is_active, group_name)
                self.db.commit(connection)
                return True
        return False
