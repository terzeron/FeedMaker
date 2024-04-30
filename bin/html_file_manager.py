#!/usr/bin/env python


import os
import re
import logging.config
from pathlib import Path
from datetime import datetime
from itertools import islice
from typing import Dict, Any, Optional
from bin.feed_maker_util import PathUtil, Datetime
from bin.db_manager import DBManager, Cursor, IntegrityError

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class HtmlFileManager:
    work_dir = Path(os.environ["FM_WORK_DIR"])

    def __init__(self, db_manager: Optional[DBManager] = None) -> None:
        if db_manager:
            self.db = db_manager
        else:
            self.db = DBManager(os.environ["FM_DB_HOST"], int(os.environ["FM_DB_PORT"]), os.environ["MYSQL_DATABASE"], os.environ["MYSQL_USER"], os.environ["MYSQL_PASSWORD"])

    @staticmethod
    def get_html_file_name(path: Path) -> str:
        return path.parent.parent.name + "/html/" + path.name

    def get_html_file_size_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_html_file_size_map()")
        html_file_size_map = {}

        for row in self.db.query("SELECT * FROM html_file_info WHERE size > 124 AND size < 434"):
            file_name = row["file_name"]
            file_path = row["file_path"]
            feed_dir_path = row["feed_dir_path"]
            size = int(row["size"])
            update_date = row["update_date"]
            html_file_size_map[file_name] = {"file_name": file_name, "file_path": file_path, "feed_dir_path": feed_dir_path, "size": size, "update_date": update_date}

        return html_file_size_map

    def get_html_file_with_many_image_tag_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_html_file_with_many_image_tag_map()")
        html_file_with_many_image_tag_map = {}

        for row in self.db.query("SELECT * FROM html_file_info WHERE count_with_many_image_tag > 0"):
            file_name = row["file_name"]
            file_path = row["file_path"]
            feed_dir_path = row["feed_dir_path"]
            count = int(row["count_with_many_image_tag"])
            update_date = row["update_date"]
            html_file_with_many_image_tag_map[file_name] = {
                "file_name": file_name,
                "file_path": file_path,
                "feed_dir_path": feed_dir_path,
                "count": count,
                "update_date": update_date
            }

        return html_file_with_many_image_tag_map

    def get_html_file_without_image_tag_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_html_file_without_image_tag_map()")
        html_file_without_image_tag_map = {}

        for row in self.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 1"):
            file_name = row["file_name"]
            file_path = row["file_path"]
            feed_dir_path = row["feed_dir_path"]
            count = int(row["count_without_image_tag"])
            update_date = row["update_date"]
            html_file_without_image_tag_map[file_name] = {
                "file_name": file_name,
                "file_path": file_path,
                "feed_dir_path": feed_dir_path,
                "count": count,
                "update_date": update_date
            }

        return html_file_without_image_tag_map

    def get_html_file_image_not_found_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_html_file_image_not_found_map()")
        html_file_image_not_found_map = {}

        for row in self.db.query("SELECT * FROM html_file_info WHERE count_with_image_not_found > 0"):
            file_name = row["file_name"]
            file_path = row["file_path"]
            feed_dir_path = row["feed_dir_path"]
            count = int(row["count_with_image_not_found"])
            update_date = row["update_date"]
            html_file_image_not_found_map[file_name] = {
                "file_name": file_name,
                "file_path": file_path,
                "feed_dir_path": feed_dir_path,
                "count": count,
                "update_date": update_date
            }

        return html_file_image_not_found_map

    def remove_html_file_in_path_from_info(self, dir_type_name: str, path: Path, do_remove_file: bool = False) -> None:
        LOGGER.debug("# remove_html_file_in_path_from_info(dir_type_name='%s'', path='%s')", dir_type_name, PathUtil.short_path(path))
        if dir_type_name not in ("file_path", "feed_dir_path"):
            LOGGER.error("can't identify directory/file type '%s'", dir_type_name)
            return

        with self.db.get_connection_and_cursor() as (connection, cursor):
            if dir_type_name == "feed_dir_path":
                feed_dir_path_str = PathUtil.short_path(path)
                rows = self.db.query("SELECT * FROM html_file_info WHERE feed_dir_path = %s", feed_dir_path_str)
                for row in rows:
                    file_path = row["file_path"]
                    if do_remove_file:
                        (self.work_dir / file_path).unlink(missing_ok=True)
                self.db.execute(cursor, "DELETE FROM html_file_info WHERE feed_dir_path = %s", feed_dir_path_str)
            if dir_type_name == "file_path":
                file_path_str = PathUtil.short_path(path)
                self.db.execute(cursor, "DELETE FROM html_file_info WHERE file_path = %s", file_path_str)
                if do_remove_file:
                    path.unlink(missing_ok=True)
            self.db.commit(connection)

        LOGGER.info("* The removing of some html files in '%s' is done", PathUtil.short_path(path))

    def _add_html_file(self, cursor: Cursor, feed_dir_path: Path, html_file_image_tag_count_map: Optional[Dict[Path, int]] = None, html_file_image_not_found_count_map: Optional[Dict[Path, int]] = None) -> int:
        LOGGER.debug("# _add_html_info(feed_dir_path=%s)", PathUtil.short_path(feed_dir_path))
        html_file_count = 0
        html_file_image_tag_count_map = html_file_image_tag_count_map if html_file_image_tag_count_map is not None else {}
        html_file_image_not_found_count_map = html_file_image_not_found_count_map if html_file_image_not_found_count_map is not None else {}

        for path in feed_dir_path.glob("html/*"):
            feed_name = path.parent.name
            group_name = path.parent.parent.name
            if feed_name.startswith("_") or group_name.startswith("_"):
                continue

            if path.suffix == ".html":
                s = path.stat()
                html_file_count += 1

                file_path_str = PathUtil.short_path(path)
                file_name = self.get_html_file_name(path)
                feed_dir_path_str = PathUtil.short_path(feed_dir_path)
                update_date = datetime.utcfromtimestamp(s.st_mtime)
                update_date_str = Datetime.convert_datetime_to_str(update_date)
                size = s.st_size

                if size < 434:
                    try:
                        self.db.execute(cursor, "INSERT INTO html_file_info (file_path, file_name, feed_dir_path, size, update_date) VALUES (%s, %s, %s, %s, %s)", file_path_str, file_name, feed_dir_path_str, size, update_date_str)
                    except IntegrityError:
                        self.db.execute(cursor, "UPDATE html_file_info SET file_name = %s, feed_dir_path = %s, size = %s, update_date = %s WHERE file_path = %s", file_name, feed_dir_path_str, size, update_date_str, file_path_str)

                # html file with normal size should have image tag
                # would find html files with zero count of image tag
                html_file_image_tag_count_map[path] = 0
                with path.open('r', encoding="utf-8") as infile:
                    for line in infile:
                        # image tag counting
                        if re.search(r'1x1\.jpg', line):
                            html_file_image_tag_count_map[path] = html_file_image_tag_count_map.get(path, 0) + 1
                        # image-not-found.png counting
                        if re.search(r'image-not-found\.png', line):
                            html_file_image_not_found_count_map[path] = html_file_image_not_found_count_map.get(path, 0) + 1

        for path, count in html_file_image_tag_count_map.items():
            file_path_str = PathUtil.short_path(path)
            file_name = self.get_html_file_name(path)
            feed_dir_path_str = PathUtil.short_path(path.parent.parent)
            if count > 1:
                try:
                    self.db.execute(cursor, "INSERT INTO html_file_info (file_path, file_name, feed_dir_path, count_with_many_image_tag) VALUES (%s, %s, %s, %s)", file_path_str, file_name, feed_dir_path_str, 1)
                except IntegrityError:
                    self.db.execute(cursor, "UPDATE html_file_info SET file_name = %s, feed_dir_path = %s, count_with_many_image_tag = %s WHERE file_path = %s", file_name, feed_dir_path_str, 1, file_path_str)
            if count < 1:
                try:
                    self.db.execute(cursor, "INSERT INTO html_file_info (file_path, file_name, feed_dir_path, count_without_image_tag) VALUES (%s, %s, %s, %s)", file_path_str, file_name, feed_dir_path_str, 1)
                except IntegrityError:
                    self.db.execute(cursor, "UPDATE html_file_info SET file_name = %s, feed_dir_path = %s, count_without_image_tag = %s WHERE file_path = %s", file_name, feed_dir_path_str, 1, file_path_str)

        for path, count in html_file_image_not_found_count_map.items():
            file_path_str = PathUtil.short_path(path)
            file_name = self.get_html_file_name(path)
            feed_dir_path_str = PathUtil.short_path(path.parent.parent)
            try:
                self.db.execute(cursor, "INSERT INTO html_file_info (file_path, file_name, feed_dir_path, count_with_image_not_found) VALUES (%s, %s, %s, %s)", file_path_str, file_name, feed_dir_path_str, 1)
            except IntegrityError:
                self.db.execute(cursor, "UPDATE html_file_info SET file_name = %s, feed_dir_path = %s, count_with_image_not_found = %s WHERE file_path = %s", file_name, feed_dir_path_str, 1, file_path_str)

        return html_file_count

    def add_html_file(self, feed_dir_path: Path) -> None:
        if not feed_dir_path.is_dir():
            LOGGER.error("can't find a feed directory '%s'", PathUtil.short_path(feed_dir_path))
            return
        with self.db.get_connection_and_cursor() as (connection, cursor):
            html_file_count = self._add_html_file(cursor, feed_dir_path)
            self.db.commit(connection)
        LOGGER.info("* The adding of some html files in '%s' is done. %d items", PathUtil.short_path(feed_dir_path), html_file_count)

    def load_all_html_files(self, max_num_feeds: Optional[int] = None) -> None:
        LOGGER.debug("# load_all_html_files(max_num_feeds=%r)", max_num_feeds)
        start_ts = datetime.now()
        html_file_image_tag_count_map: Dict[Path, int] = {}
        html_file_image_not_found_count_map: Dict[Path, int] = {}
        with self.db.get_connection_and_cursor() as (connection, cursor):
            html_file_count = 0

            for group_path in islice(self.work_dir.iterdir(), max_num_feeds):
                if not group_path.is_dir():
                    continue

                for feed_dir_path in group_path.iterdir():
                    if not feed_dir_path.is_dir():
                        continue
                    html_file_count += self._add_html_file(cursor, feed_dir_path, html_file_image_tag_count_map, html_file_image_not_found_count_map)

            self.db.commit(connection)
        end_ts = datetime.now()
        LOGGER.info("* The loading of all html files is done. %d items / %s sec", html_file_count, (end_ts - start_ts))
