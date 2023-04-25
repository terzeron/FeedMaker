#!/usr/bin/env python


import os
import json
import math
import re
import logging.config
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import suppress
from typing import List, Dict, Any, Union, Optional
from feed_maker import FeedMaker
from feed_maker_util import Config, PathUtil
from db_manager import DBManager, Cursor, IntegrityError

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class ProblemManager:
    work_dir = Path(os.environ["FEED_MAKER_WORK_DIR"])
    public_feed_dir = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"])
    httpd_access_log_dir = Path(os.environ["HOME"]) / "apps/logs"
    htaccess_file = public_feed_dir / ".." / ".htaccess"
    num_days = 14

    def __init__(self, db_manager: Optional[DBManager] = None) -> None:
        global_config = Config.get_global_config()
        if not global_config:
            LOGGER.error("can't find the global configuration")
            return

        if db_manager:
            self.db = db_manager
        else:
            self.db = DBManager(global_config["db_host"], global_config["db_port"], global_config["db_name"], global_config["db_user"], global_config["db_password"])

        self.feed_alias_name_map: Dict[str, str] = {}
        self.feed_name_aliases_map: Dict[str, Dict[str, bool]] = {}
        self.feed_name_title_map: Dict[str, str] = {}
        self.feed_name_group_map: Dict[str, str] = {}
        self.feed_name_config_map: Dict[str, Dict[str, Any]] = {}

    def __del__(self) -> None:
        del self.feed_alias_name_map
        del self.feed_name_title_map
        del self.feed_name_group_map
        del self.feed_name_aliases_map
        del self.db

    @staticmethod
    def convert_datetime_to_str(d: Union[str, datetime]) -> str:
        if not d:
            return ""
        if isinstance(d, str):
            return d
        if isinstance(d, datetime):
            return d.astimezone().strftime("%y-%m-%d")
        return ""

    @staticmethod
    def get_html_file_name(path: Path) -> str:
        return path.parent.parent.name + "/html/" + path.name

    def remove_htaccess_info(self, feed_name: str) -> None:
        connection, cursor = self.db.get_connection_and_cursor()
        self.db.execute(cursor, "DELETE FROM feed_alias_name WHERE feed_name = %s", feed_name)
        self.db.execute(cursor, "DELETE FROM feed_alias_status_info WHERE feed_name = %s", feed_name)
        self.db.commit(connection, cursor)
        if feed_name in self.feed_name_aliases_map:
            for feed_alias in self.feed_name_aliases_map[feed_name]:
                if feed_alias in self.feed_alias_name_map:
                    del self.feed_alias_name_map[feed_alias]
            del self.feed_name_aliases_map[feed_name]

    def _add_htaccess_info(self, cursor: Cursor, the_feed_name: str) -> None:
        with open(self.htaccess_file, 'r', encoding="utf-8") as infile:
            for line in infile:
                m = re.search(r'^RewriteRule\s+\^(?P<feed_alias>[^\t]+)\\\.xml\$\s+xml/(?P<feed_name>[^\t]+)\\\.xml\s*$', line)
                if m:
                    feed_alias = re.sub(r'\\\.', '.', m.group("feed_alias"))
                    feed_name = re.sub(r'\\\.', '.', m.group("feed_name"))
                    if feed_name == the_feed_name:
                        try:
                            self.db.execute(cursor, "INSERT INTO feed_alias_name VALUES (%s, %s)", feed_alias, feed_name)
                        except IntegrityError:
                            self.db.execute(cursor, "UPDATE feed_alias_name SET feed_name = %s WHERE feed_alias = %s", feed_name, feed_alias)
                        try:
                            self.db.execute(cursor, "INSERT INTO feed_alias_status_info (feed_alias, feed_name, htaccess) VALUES (%s, %s, %s)", feed_alias, feed_name, True)
                        except IntegrityError:
                            self.db.execute(cursor, "UPDATE feed_alias_status_info SET feed_name = %s, htaccess = %s WHERE feed_alias = %s", feed_name, True, feed_alias)
                        self.feed_alias_name_map[feed_alias] = feed_name
                        aliases = self.feed_name_aliases_map.get(feed_name, {})
                        aliases[feed_alias] = True
                        self.feed_name_aliases_map[feed_name] = aliases

    def add_htaccess_info(self, feed_name: str) -> None:
        connection, cursor = self.db.get_connection_and_cursor()
        self._add_htaccess_info(cursor, feed_name)
        self.db.commit(connection, cursor)
        LOGGER.info(f"* The adding of htaccess file for '{feed_name}' is done.")

    def load_htaccess_file(self) -> None:
        LOGGER.debug("# reload_htaccess_file()")
        connection, cursor = self.db.get_connection_and_cursor()

        self.db.execute(cursor, "TRUNCATE feed_alias_name")
        self.db.execute(cursor, "TRUNCATE feed_alias_status_info")

        num_items = 0
        with open(self.htaccess_file, 'r', encoding="utf-8") as infile:
            for line in infile:
                m = re.search(r'^RewriteRule\s+\^(?P<feed_alias>[^\t]+)\\\.xml\$\s+xml/(?P<feed_name>[^\t]+)\\\.xml\s*$', line)
                if m:
                    feed_alias = re.sub(r'\\\.', '.', m.group("feed_alias"))
                    feed_name = re.sub(r'\\\.', '.', m.group("feed_name"))
                    try:
                        self.db.execute(cursor, "INSERT INTO feed_alias_name VALUES (%s, %s)", feed_alias, feed_name)
                    except IntegrityError:
                        self.db.execute(cursor, "UPDATE feed_alias_name SET feed_name = %s WHERE feed_alias = %s", feed_name, feed_alias)
                    try:
                        self.db.execute(cursor, "INSERT INTO feed_alias_status_info (feed_alias, feed_name, htaccess) VALUES (%s, %s, %s)", feed_alias, feed_name, True)
                    except IntegrityError:
                        self.db.execute(cursor, "UPDATE feed_alias_status_info SET feed_name = %s, htaccess = %s WHERE feed_alias = %s", feed_name, True, feed_alias)
                    self.feed_alias_name_map[feed_alias] = feed_name
                    aliases = self.feed_name_aliases_map.get(feed_name, {})
                    aliases[feed_alias] = True
                    self.feed_name_aliases_map[feed_name] = aliases
                    num_items += 1

        self.db.commit(connection, cursor)
        LOGGER.info(f"* The loading of htaccess file is done. {num_items} items")

    def get_feed_name_list_url_count_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_feed_name_list_url_count_map()")
        feed_name_list_url_count_map = {}

        for row in self.db.query("SELECT * FROM feed_name_list_url_count"):
            feed_name = row["feed_name"]
            feed_title = row["feed_title"]
            group_name = row["group_name"]
            count = row["count"]
            feed_name_list_url_count_map[feed_name] = {"feed_name": feed_name, "feed_title": feed_title, "group_name": group_name, "count": count}

        return feed_name_list_url_count_map

    def get_element_name_count_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_element_name_count_map()")
        element_name_count_map = {}

        for row in self.db.query("SELECT * FROM element_name_count"):
            element_name = row["element_name"]
            count = row["count"]
            element_name_count_map[element_name] = {"element_name": element_name, "count": count}

        return element_name_count_map

    def remove_config_rss_info(self, feed_dir_path: Path) -> None:
        LOGGER.debug("# remove_config_rss_file_from_info(feed_dir_path={feed_dir_path})")
        feed_name = feed_dir_path.name
        connection, cursor = self.db.get_connection_and_cursor()
        self.db.execute(cursor, "DELETE FROM feed_name_config WHERE feed_name = %s", feed_name)
        self.db.execute(cursor, "DELETE FROM feed_name_title_group WHERE feed_name = %s", feed_name)
        self.db.execute(cursor, "DELETE FROM feed_name_list_url_count WHERE feed_name = %s", feed_name)
        self.db.execute(cursor, "DELETE FROM feed_name_rss_info WHERE feed_name = %s", feed_name)
        self.db.commit(connection, cursor)
        LOGGER.info(f"* The removing of config & rss file '{feed_name}' is done.")

    def _add_config_rss_info(self, cursor: Cursor, feed_dir_path: Path, element_name_count_map: Optional[Dict[str, int]] = None) -> int:
        element_name_count_map = element_name_count_map if element_name_count_map is not None else {}
        if not feed_dir_path.is_dir():
            return 0
        feed_name = feed_dir_path.name
        group_name = feed_dir_path.parent.name
        feed_title = self.feed_name_title_map.get(feed_name, "")

        num_items = 0
        with suppress(IOError):
            self.feed_name_group_map[feed_name] = group_name
            with open(feed_dir_path / "conf.json", 'r', encoding="utf-8") as infile:
                json_data = json.load(infile)
                if json_data and "configuration" in json_data:
                    try:
                        self.db.execute(cursor, "INSERT INTO feed_name_config (feed_name, config) VALUES (%s, %s)", feed_name, json.dumps(json_data["configuration"]))
                    except IntegrityError:
                        self.db.execute(cursor, "UPDATE feed_name_config SET config = %s WHERE feed_name = %s", json.dumps(json_data["configuration"]), feed_name)
                    self.feed_name_config_map[feed_name] = json_data["configuration"]

                if "rss" in json_data["configuration"] and "title" in json_data["configuration"]["rss"]:
                    title = json_data["configuration"]["rss"]["title"]
                    if "::" in title:
                        title = title.split("::")[0]
                else:
                    title = ""
                try:
                    self.db.execute(cursor, "INSERT INTO feed_name_title_group (feed_name, feed_title, group_name) VALUES (%s, %s, %s)", feed_name, title, group_name)
                except IntegrityError:
                    self.db.execute(cursor, "UPDATE feed_name_title_group SET feed_title = %s, group_name = %s WHERE feed_name = %s", title, group_name, feed_name)
                self.feed_name_title_map[feed_name] = title

                if "collection" in json_data["configuration"] and "list_url_list" in \
                        json_data["configuration"]["collection"] and not group_name.startswith("_") and not feed_name.startswith("_"):
                    count = len(json_data["configuration"]["collection"]["list_url_list"])
                    if count != 1:
                        try:
                            self.db.execute(cursor, "INSERT INTO feed_name_list_url_count (feed_name, feed_title, group_name, count) VALUES (%s, %s, %s, %s)", feed_name, title, group_name, count)
                        except IntegrityError:
                            self.db.execute(cursor, "UPDATE feed_name_list_url_count SET feed_title = %s, group_name = %s, count = %s WHERE feed_name = %s", title, group_name, count, feed_name)

                if "collection" in json_data["configuration"]:
                    for sub_config_element in ["collection", "extraction", "rss"]:
                        for element in json_data["configuration"][sub_config_element]:
                            key = sub_config_element[0] + "." + element
                            element_name_count_map[key] = element_name_count_map.get(key, 0) + 1

            rss_file_path = feed_dir_path / f"{feed_name}.xml"
            if rss_file_path.is_file():
                s = rss_file_path.stat()
                update_date = datetime.fromtimestamp(s.st_mtime)
                try:
                    self.db.execute(cursor, "INSERT INTO feed_name_rss_info (feed_name, update_date) VALUES (%s, %s)", feed_name, self.convert_datetime_to_str(update_date))
                except IntegrityError:
                    self.db.execute(cursor, "UPDATE feed_name_rss_info SET update_date = %s WHERE feed_name = %s", self.convert_datetime_to_str(update_date), feed_name)
                num_items += 1

                for feed_alias, _ in self.feed_name_aliases_map.get(feed_name, {}).items():
                    try:
                        self.db.execute(cursor, "INSERT INTO feed_alias_status_info (feed_alias, feed_name, feed_title, group_name, feedmaker, update_date) VALUES (%s, %s, %s, %s, %s, %s)", feed_alias, feed_name, feed_title, group_name, True, update_date)
                    except IntegrityError:
                        self.db.execute(cursor, "UPDATE feed_alias_status_info SET feed_name = %s, feed_title = %s, group_name = %s, feedmaker = %s, update_date = %s WHERE feed_alias = %s", feed_name, feed_title, group_name, True, update_date, feed_alias)

        return num_items

    def add_config_rss_info(self, feed_dir_path: Path) -> int:
        if not feed_dir_path.is_dir():
            LOGGER.warning("can't find feed directory '%s'", feed_dir_path)
            return 0
        connection, cursor = self.db.get_connection_and_cursor()
        num_items = self._add_config_rss_info(cursor, feed_dir_path)
        self.db.commit(connection, cursor)
        LOGGER.info(f"* The adding of config & rss file '{feed_dir_path}' is done.")
        return num_items

    def load_all_config_rss_files(self) -> None:
        LOGGER.debug("# load_all_config_rss_files()")
        connection, cursor = self.db.get_connection_and_cursor()

        self.db.execute(cursor, "TRUNCATE feed_name_config")
        self.db.execute(cursor, "TRUNCATE feed_name_title_group")
        self.db.execute(cursor, "TRUNCATE element_name_count")
        self.db.execute(cursor, "TRUNCATE feed_name_list_url_count")
        self.db.execute(cursor, "TRUNCATE feed_name_rss_info")

        if not self.feed_name_aliases_map:
            LOGGER.error("can't find name to aliases mapping data in loading config and rss files")
            return

        element_name_count_map: Dict[str, int] = {}
        num_items = 0
        for group_dir_path in self.work_dir.iterdir():
            group_name = group_dir_path.name
            if not group_dir_path.is_dir() or group_name in ("test", "logs", ".git"):
                continue
            for feed_dir_path in group_dir_path.iterdir():
                if not feed_dir_path.is_dir():
                    continue
                num_items += self._add_config_rss_info(cursor, feed_dir_path, element_name_count_map)

        for element_name, count in element_name_count_map.items():
            try:
                self.db.execute(cursor, "INSERT INTO element_name_count (element_name, count) VALUES (%s, %s)", element_name, count)
            except IntegrityError:
                self.db.execute(cursor, "UPDATE element_name_count SET count = %s WHERE element_name = %s", count, element_name)

        self.db.commit(connection, cursor)
        LOGGER.info(f"* The loading of all config files and rss files is done. {num_items} items")

    def get_feed_name_public_feed_info_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_feed_name_public_feed_info_map()")
        feed_name_public_feed_info_map = {}

        for row in self.db.query("SELECT * FROM feed_name_public_feed_info"):
            feed_name = row["feed_name"]
            feed_title = row["feed_title"]
            group_name = row["group_name"]
            file_path = row["file_path"]
            upload_date = row["upload_date"]
            file_size = row["file_size"]
            num_items = row["num_items"]
            feed_name_public_feed_info_map[feed_name] = {"feed_name": feed_name, "feed_title": feed_title, "group_name": group_name, "file_path": file_path, "upload_date": upload_date, "size": file_size, "num_items": num_items}

        return feed_name_public_feed_info_map

    def remove_public_feed_info(self, feed_file_path: Path):
        connection, cursor = self.db.get_connection_and_cursor()
        feed_name = feed_file_path.parent.name
        self.db.execute(cursor, "DELETE FROM feed_name_public_feed_info WHERE feed_name = %s", feed_name)
        self.db.commit(connection, cursor)
        LOGGER.info(f"* The removing of public feed file '{feed_name}' is done.")

    def _add_public_feed_info(self, cursor: Cursor, feed_file_path: Path) -> int:
        feed_name = feed_file_path.stem
        if feed_name.startswith("_"):
            return 0

        with feed_file_path.open("r", encoding="utf-8") as infile:
            file_content = infile.read()
            num_item_elements = file_content.count("<item>")
        feed_title = self.feed_name_title_map.get(feed_name, "")
        group_name = self.feed_name_group_map.get(feed_name, "")
        s = feed_file_path.stat()
        upload_date = datetime.fromtimestamp(s.st_mtime)
        path_str = PathUtil.convert_path_to_str(feed_file_path)

        try:
            self.db.execute(cursor, "INSERT INTO feed_name_public_feed_info (feed_name, feed_title, group_name, file_path, upload_date, file_size, num_items) VALUES (%s, %s, %s, %s, %s, %s, %s)", feed_name, feed_title, group_name, path_str, self.convert_datetime_to_str(upload_date), s.st_size, num_item_elements)
        except IntegrityError:
            self.db.execute(cursor, "UPDATE feed_name_public_feed_info SET feed_title = %s, group_name = %s, file_path = %s, upload_date = %s, file_size = %s, num_items = %s WHERE feed_name = %s", feed_title, group_name, path_str, self.convert_datetime_to_str(upload_date), s.st_size, num_item_elements, feed_name)

        for feed_alias, _ in self.feed_name_aliases_map.get(feed_name, {}).items():
            try:
                self.db.execute(cursor, "INSERT INTO feed_alias_status_info (feed_alias, feed_name, feed_title, group_name, public_html, upload_date, file_path) VALUES (%s, %s, %s, %s, %s, %s, %s)", feed_alias, feed_name, feed_title, group_name, True, upload_date, path_str)
            except IntegrityError:
                self.db.execute(cursor, "UPDATE feed_alias_status_info SET feed_name = %s, feed_title = %s, group_name = %s, public_html = %s, upload_date = %s, file_path = %s WHERE feed_alias = %s", feed_name, feed_title, group_name, True, upload_date, path_str, feed_alias)

        return 1

    def add_public_feed_info(self, feed_file_path: Path):
        connection, cursor = self.db.get_connection_and_cursor()
        self._add_public_feed_info(cursor, feed_file_path)
        self.db.commit(connection, cursor)
        LOGGER.info(f"* The adding of public feed file '{PathUtil.convert_path_to_str(feed_file_path)}' is done.")

    def load_all_public_feed_files(self) -> None:
        LOGGER.debug("# load_all_public_feed_files()")
        connection, cursor = self.db.get_connection_and_cursor()

        self.db.execute(cursor, "TRUNCATE feed_name_public_feed_info")

        if not self.feed_name_title_map:
            LOGGER.error("can't find name to title mapping data in loading public feed files")
            return
        if not self.feed_name_group_map:
            LOGGER.error("can't find name to group mapping data in loading public feed files")
            return
        if not self.feed_name_aliases_map:
            LOGGER.error("can't find name to aliases mapping data in loading public feed files")
            return

        num_items = 0
        for feed_file_path in self.public_feed_dir.iterdir():
            if feed_file_path.suffix == ".xml":
                num_items += self._add_public_feed_info(cursor, feed_file_path)

        self.db.commit(connection, cursor)
        LOGGER.info(f"* The loading of public feed file is done. {num_items} items")

    def get_html_file_size_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_html_file_size_map()")
        html_file_size_map = {}

        for row in self.db.query("SELECT * FROM html_file_size"):
            file_name = row["file_name"]
            file_path = row["file_path"]
            feed_dir_path = row["feed_dir_path"]
            group_dir_path = row["group_dir_path"]
            size = int(row["size"])
            update_date = row["update_date"]
            html_file_size_map[file_name] = {"file_name": file_name, "file_path": file_path, "feed_dir_path": feed_dir_path, "group_dir_path": group_dir_path, "size": size, "update_date": update_date}

        return html_file_size_map

    def get_html_file_with_many_image_tag_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_html_file_with_many_image_tag_map()")
        html_file_with_many_image_tag_map = {}

        for row in self.db.query("SELECT * FROM html_file_with_many_image_tag"):
            file_name = row["file_name"]
            file_path = row["file_path"]
            feed_dir_path = row["feed_dir_path"]
            group_dir_path = row["group_dir_path"]
            count = int(row["count"])
            html_file_with_many_image_tag_map[file_name] = {"file_name": file_name, "file_path": file_path, "feed_dir_path": feed_dir_path, "group_dir_path": group_dir_path, "count": count}

        return html_file_with_many_image_tag_map

    def get_html_file_without_image_tag_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_html_file_without_image_tag_map()")
        html_file_without_image_tag_map = {}

        for row in self.db.query("SELECT * FROM html_file_with_many_image_tag"):
            file_name = row["file_name"]
            file_path = row["file_path"]
            feed_dir_path = row["feed_dir_path"]
            group_dir_path = row["group_dir_path"]
            count = int(row["count"])
            html_file_without_image_tag_map[file_name] = {"file_name": file_name, "file_path": file_path, "feed_dir_path": feed_dir_path, "group_dir_path": group_dir_path, "count": count}

        return html_file_without_image_tag_map

    def get_html_file_image_not_found_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_html_file_image_not_found_map()")
        html_file_image_not_found_map = {}

        for row in self.db.query("SELECT * FROM html_file_image_not_found"):
            file_name = row["file_name"]
            file_path = row["file_path"]
            feed_dir_path = row["feed_dir_path"]
            group_dir_path = row["group_dir_path"]
            count = int(row["count"])
            html_file_image_not_found_map[file_name] = {"file_name": file_name, "file_path": file_path, "feed_dir_path": feed_dir_path, "group_dir_path": group_dir_path, "count": count}

        return html_file_image_not_found_map

    def remove_html_file_in_path_from_info(self, dir_type_name: str, path: Path) -> None:
        LOGGER.debug(f"# remove_html_file_in_path_from_info(dir_type_name={dir_type_name}, dir_path={path})")
        if dir_type_name not in ("file_path", "feed_dir_path", "group_dir_path"):
            return

        connection, cursor = self.db.get_connection_and_cursor()
        if dir_type_name == "feed_dir_path":
            feed_dir_path_str = PathUtil.convert_path_to_str(path)
            self.db.execute(cursor, "DELETE FROM html_file_size WHERE feed_dir_path = %s", feed_dir_path_str)
            self.db.execute(cursor, "DELETE FROM html_file_with_many_image_tag WHERE feed_dir_path = %s", feed_dir_path_str)
            self.db.execute(cursor, "DELETE FROM html_file_without_image_tag WHERE feed_dir_path = %s", feed_dir_path_str)
            self.db.execute(cursor, "DELETE FROM html_file_image_not_found WHERE feed_dir_path = %s", feed_dir_path_str)
        if dir_type_name == "file_path":
            file_path_str = PathUtil.convert_path_to_str(path)
            self.db.execute(cursor, "DELETE FROM html_file_size WHERE file_path = %s", file_path_str)
            self.db.execute(cursor, "DELETE FROM html_file_with_many_image_tag WHERE file_path = %s", file_path_str)
            self.db.execute(cursor, "DELETE FROM html_file_without_image_tag WHERE file_path = %s", file_path_str)
            self.db.execute(cursor, "DELETE FROM html_file_image_not_found WHERE file_path = %s", file_path_str)
        self.db.commit(connection, cursor)
        LOGGER.info(f"* The removing of some html files in '{PathUtil.convert_path_to_str(path)}' is done.")

    def _add_html_info(self, cursor: Cursor, feed_dir_path: Path, web_service_url: str, html_file_image_tag_count_map: Optional[Dict[Path, int]] = None, html_file_image_not_found_count_map: Optional[Dict[Path, int]] = None) -> int:
        LOGGER.debug(f"# add_html_files_in_path_to_info(feed_dir_path={feed_dir_path})")
        html_file_count = 0
        html_file_image_tag_count_map = html_file_image_tag_count_map if html_file_image_tag_count_map is not None else {}
        html_file_image_not_found_count_map = html_file_image_not_found_count_map if html_file_image_not_found_count_map is not None else {}

        for path in feed_dir_path.glob("html/*"):
            if path.parent.name.startswith("_") or path.parent.parent.name.startswith("_"):
                continue
            if path.suffix == ".html":
                s = path.stat()
                html_file_count += 1
                if 124 < s.st_size < 434:
                    file_path_str = PathUtil.convert_path_to_str(path)
                    file_name = self.get_html_file_name(path)
                    feed_dir_path_str = PathUtil.convert_path_to_str(feed_dir_path)
                    group_dir_path_str = PathUtil.convert_path_to_str(feed_dir_path.parent)
                    update_date_str = self.convert_datetime_to_str(datetime.fromtimestamp(s.st_mtime))
                    try:
                        self.db.execute(cursor, "INSERT INTO html_file_size (file_path, file_name, feed_dir_path, group_dir_path, size, update_date) VALUES (%s, %s, %s, %s, %s, %s)", file_path_str, file_name, feed_dir_path_str, group_dir_path_str, s.st_size, update_date_str)
                    except IntegrityError:
                        self.db.execute(cursor, "UPDATE html_file_size SET file_name = %s, feed_dir_path = %s, group_dir_path =%s, size = %s, update_date = %s WHERE file_path = %s", file_name, feed_dir_path_str, group_dir_path_str, s.st_size, update_date_str, file_path_str)

                # html file with normal size should have image tag
                # would find html files with zero count of image tag
                if s.st_size > FeedMaker.get_size_of_template_with_image_tag(web_service_url, path.name):
                    html_file_image_tag_count_map[path] = 0
                with path.open('r', encoding="utf-8") as infile:
                    for line in infile:
                        # image tag counting
                        if re.search(r'1x1.jpg', line):
                            html_file_image_tag_count_map[path] = html_file_image_tag_count_map.get(path, 0) + 1
                        # image-not-found.png counting
                        if re.search(r'image-not-found\.png', line):
                            html_file_image_not_found_count_map[path] = html_file_image_not_found_count_map.get(path, 0) + 1

        for path, count in html_file_image_tag_count_map.items():
            file_path_str = PathUtil.convert_path_to_str(path)
            file_name = self.get_html_file_name(path)
            feed_dir_path_str = PathUtil.convert_path_to_str(path.parent.parent)
            group_dir_path_str = PathUtil.convert_path_to_str(path.parent.parent.parent)
            if count > 1:
                try:
                    self.db.execute(cursor, "INSERT INTO html_file_with_many_image_tag (file_path, file_name, feed_dir_path, group_dir_path, count) VALUES (%s, %s, %s, %s, %s)", file_path_str, file_name, feed_dir_path_str, group_dir_path_str, count)
                except IntegrityError:
                    self.db.execute(cursor, "UPDATE html_file_with_many_image_tag SET file_name = %s, feed_dir_path = %s, group_dir_path = %s, count = %s WHERE file_path = %s", file_name, feed_dir_path_str, group_dir_path_str, count, file_path_str)
            if count < 1:
                try:
                    self.db.execute(cursor, "INSERT INTO html_file_without_image_tag (file_path, file_name, feed_dir_path, group_dir_path, count) VALUES (%s, %s, %s, %s, %s)", file_path_str, file_name, feed_dir_path_str, group_dir_path_str, count)
                except IntegrityError:
                    self.db.execute(cursor, "UPDATE html_file_without_image_tag SET file_name = %s, feed_dir_path = %s, group_dir_path = %s, count = %s WHERE file_path = %s", file_name, feed_dir_path_str, group_dir_path_str, count, file_path_str)

        for path, count in html_file_image_not_found_count_map.items():
            file_path_str = PathUtil.convert_path_to_str(path)
            file_name = self.get_html_file_name(path)
            feed_dir_path_str = PathUtil.convert_path_to_str(path.parent.parent)
            group_dir_path_str = PathUtil.convert_path_to_str(path.parent.parent.parent)
            try:
                self.db.execute(cursor, "INSERT INTO html_file_image_not_found (file_path, file_name, feed_dir_path, group_dir_path, count) VALUES (%s, %s, %s, %s, %s)", file_path_str, file_name, feed_dir_path_str, group_dir_path_str, count)
            except IntegrityError:
                self.db.execute(cursor, "UPDATE html_file_image_not_found SET file_name = %s, feed_dir_path = %s, group_dir_path = %s, count = %s WHERE file_path = %s", file_name, feed_dir_path_str, group_dir_path_str, count, file_path_str)

        return html_file_count

    def add_html_info(self, feed_dir_path: Path):
        connection, cursor = self.db.get_connection_and_cursor()
        global_conf = Config.get_global_config()
        web_service_url = global_conf["web_service_url"]
        html_file_count = self._add_html_info(cursor, feed_dir_path, web_service_url)
        self.db.commit(connection, cursor)
        LOGGER.info(f"* The adding of some html files in '{PathUtil.convert_path_to_str(feed_dir_path)}' is done. {html_file_count} items")

    def load_all_html_files(self) -> None:
        LOGGER.debug("# load_all_html_files()")
        html_file_image_tag_count_map: Dict[Path, int] = {}
        html_file_image_not_found_count_map: Dict[Path, int] = {}
        connection, cursor = self.db.get_connection_and_cursor()

        self.db.execute(cursor, "TRUNCATE html_file_size")
        self.db.execute(cursor, "TRUNCATE html_file_with_many_image_tag")
        self.db.execute(cursor, "TRUNCATE html_file_without_image_tag")
        self.db.execute(cursor, "TRUNCATE html_file_image_not_found")

        html_file_count = 0
        global_conf = Config.get_global_config()
        web_service_url = global_conf["web_service_url"]

        for group_path in self.work_dir.iterdir():
            group_name = group_path.name
            if not group_path.is_dir() or group_name in ("test", "logs", ".git"):
                continue
            for feed_dir_path in group_path.iterdir():
                html_file_count += self._add_html_info(cursor, feed_dir_path, web_service_url, html_file_image_tag_count_map, html_file_image_not_found_count_map)

        self.db.commit(connection, cursor)
        LOGGER.info(f"* The loading of all html files is done. {html_file_count} items")

    def get_feed_name_progress_info_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_feed_name_progress_info_map()")
        feed_name_progress_info_map = {}

        for row in self.db.query("SELECT * FROM feed_name_progress_info"):
            feed_name = row["feed_name"]
            feed_title = row["feed_title"]
            group_name = row["group_name"]
            idx = row["idx"]
            count = row["count"]
            unit_size = row["unit_size"]
            progress_ratio = row["progress_ratio"]
            due_date = row["due_date"]
            feed_name_progress_info_map[feed_name] = {"feed_name": feed_name, "feed_title": feed_title, "group_name": group_name, "index": idx, "count": count, "unit_size": unit_size, "ratio": progress_ratio, "due_date": due_date}

        return feed_name_progress_info_map

    def remove_progress_info(self, feed_dir_path: Path):
        connection, cursor = self.db.get_connection_and_cursor()
        feed_name = feed_dir_path.name
        self.db.execute(cursor, "DELETE FROM feed_name_progress_info WHERE feed_name = %s", feed_name)
        self.db.commit(connection, cursor)
        LOGGER.info(f"* The removing of progress of '{feed_name}' is done.")

    def _add_progress_info(self, cursor: Cursor, feed_dir_path: Path) -> int:
        feed_name = feed_dir_path.name
        if not feed_dir_path.is_dir() or feed_name.startswith((".", "_")) or feed_name not in self.feed_name_config_map:
            return 0

        config = self.feed_name_config_map[feed_name]
        if "collection" not in config or "is_completed" not in config["collection"] or not config["collection"]["is_completed"]:
            return 0

        index = 0
        file_path = feed_dir_path / "start_idx.txt"
        if file_path.is_file():
            with file_path.open('r', encoding="utf-8") as infile:
                line = infile.readline()
                index = int(line.split('\t')[0])

        url_list: List[str] = []
        dir_name = feed_dir_path / "newlist"
        if dir_name.is_dir():
            for file in dir_name.iterdir():
                if file.suffix == ".txt":
                    with open(dir_name / file, 'r', encoding="utf-8") as infile:
                        for line in infile:
                            url = line.split('\t')[0]
                            url_list.append(url)
        count = len(list(set(url_list)))

        feed_title = self.feed_name_title_map[feed_name]
        group_name = self.feed_name_group_map[feed_name]
        progress_ratio = int((index + 4) * 100 / (count + 1))
        unit_size = config["collection"].get("unit_size_per_day", 1)
        remainder = count - (index + 4)
        num_days = int(math.ceil(remainder / unit_size))
        due_date = datetime.now() + timedelta(days=num_days)

        try:
            self.db.execute(cursor, "INSERT INTO feed_name_progress_info (feed_name, feed_title, group_name, idx, count, unit_size, progress_ratio, due_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", feed_name, feed_title, group_name, index, count, unit_size, progress_ratio, self.convert_datetime_to_str(due_date))
        except IntegrityError:
            self.db.execute(cursor, "UPDATE feed_name_progress_info SET feed_title = %s, group_name = %s, idx = %s, count = %s, unit_size = %s, progress_ratio = %s, due_date = %s WHERE feed_name = %s", feed_title, group_name, index, count, unit_size, progress_ratio, self.convert_datetime_to_str(due_date), feed_name)
        return 1

    def add_progress_info(self, feed_dir_path: Path):
        feed_name = feed_dir_path.name
        if not feed_dir_path.is_dir() or feed_name.startswith((".", "_")) or feed_name not in self.feed_name_config_map:
            LOGGER.warning("can't find feed directory '%s'", feed_dir_path)
            return

        connection, cursor = self.db.get_connection_and_cursor()
        self._add_progress_info(cursor, feed_dir_path)
        self.db.commit(connection, cursor)
        LOGGER.info(f"* The adding of progress info of '{PathUtil.convert_path_to_str(feed_dir_path)}' is done.")

    def load_all_progress_info_from_files(self) -> None:
        LOGGER.debug("# load_all_progress_info_from_files()")
        connection, cursor = self.db.get_connection_and_cursor()

        self.db.execute(cursor, "TRUNCATE feed_name_progress_info")

        if not self.feed_name_config_map:
            LOGGER.error("can't find name to config mapping data in loading all progress info from files")
            return
        if not self.feed_name_title_map:
            LOGGER.error("can't find name to title mapping data in loading all progress info from files")
            return
        if not self.feed_name_group_map:
            LOGGER.error("can't find name to group mapping data in loading all progress info from files")
            return

        num_items = 0

        for group_dir_path in self.work_dir.iterdir():
            group_name = group_dir_path.name
            if not group_dir_path.is_dir() or group_name in ("test", "logs") or group_name.startswith((".", "_")):
                continue

            for feed_dir_path in group_dir_path.iterdir():
                num_items += self._add_progress_info(cursor, feed_dir_path)
        self.db.commit(connection, cursor)
        LOGGER.info(f"* The loading of all progress info is done. {num_items} items")

    def _add_http_access_info(self, cursor: Cursor, access_file_path: Path) -> int:
        num_items = 0
        with access_file_path.open('r', encoding="utf-8") as infile:
            for line in infile:
                # view
                m = re.search(r'\[(?P<date>\d+/\w+/\d+):\d+:\d+:\d+ \+\d+] "GET /img/1x1\.jpg\?feed=(?P<feed_name>[\w.\-]+)\.xml\S* HTTP\S+" (?P<status_code>\d+) (?:\d+|-) "[^"]*" "[^"]*"', line)
                if m:
                    feed_name = m.group("feed_name")
                    feed_title = self.feed_name_title_map.get(feed_name, "")
                    group_name = self.feed_name_group_map.get(feed_name, "")
                    for feed_alias, _ in self.feed_name_aliases_map.get(feed_name, {}).items():
                        status_code = int(m.group("status_code"))
                        if status_code != 200:
                            continue
                        view_date = datetime.strptime(m.group("date"), "%d/%b/%Y")
                        # determine the latest view date & status
                        try:
                            self.db.execute(cursor, "INSERT INTO feed_alias_access_info (feed_alias, feed_name, view_date, view_status, is_in_xml_dir) VALUES (%s, %s, %s, %s, %s)", feed_alias, feed_name, self.convert_datetime_to_str(view_date), status_code, False)
                        except IntegrityError:
                            self.db.execute(cursor, "UPDATE feed_alias_access_info SET feed_name = %s, view_date = %s, view_status = %s, is_in_xml_dir = %s WHERE feed_alias = %s", feed_name, self.convert_datetime_to_str(view_date), status_code, False, feed_alias)
                        num_items += 1
                        try:
                            self.db.execute(cursor, "INSERT INTO feed_alias_status_info (feed_alias, feed_name, feed_title, group_name, http_request, view_date) VALUES (%s, %s, %s, %s, %s, %s)", feed_alias, feed_name, feed_title, group_name, True, view_date)
                        except IntegrityError:
                            self.db.execute(cursor, "UPDATE feed_alias_status_info SET feed_name = %s, feed_title = %s, group_name = %s, http_request = %s, view_date = %s WHERE feed_alias = %s", feed_name, feed_title, group_name, True, view_date, feed_alias)

                # access
                m = re.search(
                    r'\[(?P<date>\d+/\w+/\d+):\d+:\d+:\d+ \+\d+] "GET /(?P<feed>(xml/)?(?P<feed_alias>[\w.\-]+))\.xml\S* HTTP\S+" (?P<status_code>\d+)',
                    line)
                if m:
                    feed = m.group("feed")
                    feed_alias = m.group("feed_alias")
                    feed_name = self.feed_alias_name_map.get(feed_alias, "")
                    feed_title = self.feed_name_title_map.get(feed_name, "")
                    group_name = self.feed_name_group_map.get(feed_name, "")
                    status_code = int(m.group("status_code"))
                    if status_code != 200:
                        continue
                    access_date = datetime.strptime(m.group("date"), "%d/%b/%Y")
                    is_in_xml_dir = feed.startswith("xml/")
                    # determine the latest access date & status
                    try:
                        self.db.execute(cursor, "INSERT INTO feed_alias_access_info (feed_alias, feed_name, access_date, access_status, is_in_xml_dir) VALUES (%s, %s, %s, %s, %s)", feed_alias, feed_name, self.convert_datetime_to_str(access_date), status_code, is_in_xml_dir)
                    except IntegrityError:
                        self.db.execute(cursor, "UPDATE feed_alias_access_info SET feed_name = %s, access_date = %s, access_status = %s, is_in_xml_dir = %s WHERE feed_alias = %s", feed_name, self.convert_datetime_to_str(access_date), status_code, is_in_xml_dir, feed_alias)
                    num_items += 1
                    try:
                        self.db.execute(cursor, "INSERT INTO feed_alias_status_info (feed_alias, feed_name, feed_title, group_name, http_request, access_date) VALUES (%s, %s, %s, %s, %s, %s)", feed_alias, feed_name, feed_title, group_name, True, access_date)
                    except IntegrityError:
                        self.db.execute(cursor, "UPDATE feed_alias_status_info SET feed_name = %s, feed_title = %s, group_name = %s, http_request = %s, access_date = %s WHERE feed_alias = %s", feed_name, feed_title, group_name, True, access_date, feed_alias)

        return num_items

    def add_httpd_access_info(self, feed_dir_path: Path):
        LOGGER.debug(f"# add_httpd_access_files_to_info_after_last_log({feed_dir_path})")
        feed_name = feed_dir_path.name
        connection, cursor = self.db.get_connection_and_cursor()
        for feed_alias, _ in self.feed_name_aliases_map.get(feed_name, {}).items():
            rows = self.db.query("SELECT access_date FROM feed_alias_access_info WHERE feed_alias = %s", feed_alias)
            last_log_date = rows[0]["access_date"]
            today = datetime.today()
            for i in range(30, -1, -1):
                specific_date = today - timedelta(days=i)
                if specific_date < last_log_date:
                    continue
                date_str = specific_date.strftime("%y%m%d")
                access_file_path = self.httpd_access_log_dir / f"access.log.{date_str}"
                if not access_file_path.is_file():
                    # LOGGER.warning("can't find access file '%s'", access_file_path)
                    continue

                self._add_http_access_info(cursor, access_file_path)
                LOGGER.info(f"* The adding of access info of '{PathUtil.convert_path_to_str(access_file_path)}' is done.")
        self.db.commit(connection, cursor)

    def load_all_httpd_access_files(self) -> None:
        LOGGER.debug("# load_all_httpd_access_files()")
        connection, cursor = self.db.get_connection_and_cursor()

        self.db.execute(cursor, "TRUNCATE feed_alias_access_info")

        if not self.feed_alias_name_map:
            LOGGER.error("can't find alias to name mapping data in loading all httpd access files")
            return
        if not self.feed_name_title_map:
            LOGGER.error("can't find name to title mapping data in loading all httpd access files")
            return
        if not self.feed_name_group_map:
            LOGGER.error("can't find name to group mapping data in loading all httpd access files")
            return
        if not self.feed_name_aliases_map:
            LOGGER.error("can't find name to alias mapping data in loading all httpd access files")
            return

        # read access.log for 1 month
        today = datetime.today()
        num_items = 0
        for i in range(30, -1, -1):
            date_str = (today - timedelta(days=i)).strftime("%y%m%d")
            access_file_path = self.httpd_access_log_dir / f"access.log.{date_str}"
            if not access_file_path.is_file():
                # LOGGER.warning("can't find access file '%s'", access_file_path)
                continue
            num_items += self._add_http_access_info(cursor, access_file_path)

        self.db.commit(connection, cursor)
        LOGGER.info(f"* The loading of http access log is done. {num_items} items")

    def get_feed_alias_status_info_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_feed_alias_status_info_map()")
        feed_alias_status_info_map = {}

        for row in self.db.query("SELECT * FROM feed_alias_status_info WHERE NOT ( http_request IS NULL AND htaccess IS NULL AND public_html IS NULL AND feedmaker IS NULL ) AND NOT ( http_request IS NOT NULL AND htaccess IS NULL AND public_html IS NULL AND feedmaker IS NULL AND access_date IS NOT NULL AND DATEDIFF(access_date, current_date) > %s ) AND NOT ( http_request IS NOT NULL AND htaccess IS NOT NULL AND public_html IS NOT NULL AND feedmaker IS NOT NULL AND ( access_date IS NOT NULL AND DATEDIFF(current_date, access_date) < %s OR view_date IS NOT NULL AND DATEDIFF(current_date, view_date) < %s ) )", ProblemManager.num_days, ProblemManager.num_days, ProblemManager.num_days):
            feed_alias = row["feed_alias"]
            feed_name = row["feed_name"]
            feed_title = row["feed_title"]
            group_name = row["group_name"]
            htaccess = row["htaccess"]
            http_request = row["http_request"]
            public_html = row["public_html"]
            feedmaker = row["feedmaker"]
            access_date = row["access_date"]
            view_date = row["view_date"]
            upload_date = row["upload_date"]
            update_date = row["update_date"]
            file_path = row["file_path"]
            feed_alias_status_info_map[feed_alias] = {"feed_alias": feed_alias, "feed_name": feed_name, "feed_title": feed_title, "group_name": group_name, "htaccess": htaccess, "http_request": http_request, "public_html": public_html, "feedmaker": feedmaker, "access_date": access_date, "view_date": view_date, "upload_date": upload_date, "update_date": update_date, "file_path": file_path}

        return feed_alias_status_info_map

    def update_feed_info(self, feed_dir_path: Path) -> None:
        LOGGER.debug(f"# update_feed_info(feed_dir_path={feed_dir_path})")
        self.remove_htaccess_info(feed_dir_path.name)
        self.add_htaccess_info(feed_dir_path.name)
        self.remove_config_rss_info(feed_dir_path)
        self.add_config_rss_info(feed_dir_path)
        self.remove_public_feed_info(feed_dir_path)
        feed_file_path = self.public_feed_dir / f"{feed_dir_path.name}.xml"
        self.add_public_feed_info(feed_file_path)
        self.remove_progress_info(feed_dir_path)
        self.add_progress_info(feed_dir_path)
        self.add_httpd_access_info(feed_dir_path)
        self.add_html_info(feed_dir_path)

    def lock_problem_database(self) -> bool:
        connection, cursor = self.db.get_connection_and_cursor(with_serializable_transaction=True)
        rows = self.db.query("SELECT * FROM lock_for_concurrent_loading FOR UPDATE")
        if rows and len(rows) > 0:
            if rows[0]["lock_time"] and datetime.now() - rows[0]["lock_time"] < timedelta(seconds=60):
                self.db.rollback(connection, cursor)
                return False
            else:
                self.db.execute(cursor, "DELETE FROM lock_for_concurrent_loading")
        self.db.execute(cursor, "INSERT INTO lock_for_concurrent_loading VALUES (CURRENT_TIMESTAMP)")
        self.db.commit(connection, cursor)
        return True

    def unlock_problem_database(self) -> None:
        connection, cursor = self.db.get_connection_and_cursor(with_serializable_transaction=True)
        rows = self.db.query("SELECT * FROM lock_for_concurrent_loading FOR UPDATE")
        if not rows or len(rows) == 0:
            self.db.rollback(connection, cursor)
            return
        self.db.execute(cursor, "DELETE FROM lock_for_concurrent_loading")
        self.db.commit(connection, cursor)

    def load_all(self) -> int:
        LOGGER.debug("# load_all()")
        if self.lock_problem_database():
            LOGGER.info("* start loading information")
            self.load_htaccess_file()
            self.load_all_config_rss_files()
            self.load_all_public_feed_files()
            self.load_all_progress_info_from_files()
            self.load_all_httpd_access_files()
            self.load_all_html_files()
            self.unlock_problem_database()
            LOGGER.info("* finish loading information")
        else:
            LOGGER.info("* abort loading information")
        return 0


if __name__ == "__main__":
    pm = ProblemManager()
    pm.load_all()
