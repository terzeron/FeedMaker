#!/usr/bin/env python


import re
import logging.config
from pathlib import Path
from datetime import datetime, timezone
from itertools import islice
from typing import Any, Optional

from bin.models import HtmlFileInfo
from bin.feed_maker import FeedMaker
from bin.feed_maker_util import PathUtil, Env
from bin.db import DB, Session
from bin.feed_manager import FeedManager


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class HtmlFileManager:
    work_dir_path = Path(Env.get("FM_WORK_DIR"))

    @staticmethod
    def get_html_file_name(path: Path) -> str:
        return path.parent.parent.name + "/html/" + path.name

    @staticmethod
    def _get_feed_title_from_path(feed_dir_path: str) -> str:
        """Extract feed title from feed directory path"""
        try:
            # feed_dir_path format: "group_name/feed_name"
            parts = feed_dir_path.split("/")
            if len(parts) >= 2:
                group_name = parts[0]
                feed_name = parts[1]
                # Get feed info from FeedManager
                feed_info = FeedManager.get_feed_info(group_name, feed_name)
                LOGGER.debug("Feed info for %s/%s: %s", group_name, feed_name, feed_info)
                if feed_info and "feed_title" in feed_info:
                    return feed_info["feed_title"]
                return feed_name
            return ""
        except (OSError, IOError, KeyError, TypeError, ValueError, AttributeError, RuntimeError) as e:
            LOGGER.warning("Failed to get feed title for %s: %s", feed_dir_path, e)
            return ""

    @staticmethod
    def get_html_file_size_map(feed_name: str = "") -> dict[str, dict[str, Any]]:
        LOGGER.debug("# get_html_file_size_map()")
        html_file_size_map = {}

        with DB.session_ctx() as s:
            rows = s.query(HtmlFileInfo).where(HtmlFileInfo.size < FeedMaker.get_size_of_template_with_image_tag(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), feed_name)).order_by(HtmlFileInfo.update_date).all()
            for row in rows:
                file_name = row.file_name
                file_path = row.file_path
                feed_dir_path = row.feed_dir_path
                size = row.size
                update_date = row.update_date
                feed_title = HtmlFileManager._get_feed_title_from_path(feed_dir_path)
                html_file_size_map[file_name] = {
                    "file_name": file_name, 
                    "file_path": file_path, 
                    "feed_dir_path": feed_dir_path, 
                    "size": size, 
                    "update_date": update_date,
                    "feed_title": feed_title
                }

        return html_file_size_map

    @staticmethod
    def get_html_file_with_many_image_tag_map() -> dict[str, dict[str, Any]]:
        LOGGER.debug("# get_html_file_with_many_image_tag_map()")
        html_file_with_many_image_tag_map = {}

        with DB.session_ctx() as s:
            rows = s.query(HtmlFileInfo).where(HtmlFileInfo.count_with_many_image_tag > 1).order_by(HtmlFileInfo.update_date).all()
            for row in rows:
                file_name = row.file_name
                file_path = row.file_path
                feed_dir_path = row.feed_dir_path
                count = row.count_with_many_image_tag
                update_date = row.update_date
                feed_title = HtmlFileManager._get_feed_title_from_path(feed_dir_path)
                html_file_with_many_image_tag_map[file_name] = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "feed_dir_path": feed_dir_path,
                    "count": count,
                    "update_date": update_date,
                    "feed_title": feed_title
                }

        return html_file_with_many_image_tag_map

    @staticmethod
    def get_html_file_without_image_tag_map() -> dict[str, dict[str, Any]]:
        LOGGER.debug("# get_html_file_without_image_tag_map()")
        html_file_without_image_tag_map = {}

        with DB.session_ctx() as s:
            rows = s.query(HtmlFileInfo).where(HtmlFileInfo.count_without_image_tag > 0).order_by(HtmlFileInfo.update_date).all()
            for row in rows:
                file_name = row.file_name
                file_path = row.file_path
                feed_dir_path = row.feed_dir_path
                count = row.count_without_image_tag
                update_date = row.update_date
                feed_title = HtmlFileManager._get_feed_title_from_path(feed_dir_path)
                html_file_without_image_tag_map[file_name] = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "feed_dir_path": feed_dir_path,
                    "count": count,
                    "update_date": update_date,
                    "feed_title": feed_title
                }

        return html_file_without_image_tag_map

    @staticmethod
    def get_html_file_image_not_found_map() -> dict[str, dict[str, Any]]:
        LOGGER.debug("# get_html_file_image_not_found_map()")
        html_file_image_not_found_map = {}

        with DB.session_ctx() as s:
            rows = s.query(HtmlFileInfo).where(HtmlFileInfo.count_with_image_not_found > 0).order_by(HtmlFileInfo.update_date).all()
            for row in rows:
                file_name = row.file_name
                file_path = row.file_path
                feed_dir_path = row.feed_dir_path
                count = row.count_with_image_not_found
                update_date = row.update_date
                feed_title = HtmlFileManager._get_feed_title_from_path(feed_dir_path)
                html_file_image_not_found_map[file_name] = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "feed_dir_path": feed_dir_path,
                    "count": count,
                    "update_date": update_date,
                    "feed_title": feed_title
                }

        return html_file_image_not_found_map

    def remove_html_file_in_path_from_info(self, dir_type_name: str, path: Path, do_remove_file: bool = False) -> None:
        LOGGER.debug("# remove_html_file_in_path_from_info(dir_type_name='%s'', path='%s')", dir_type_name, PathUtil.short_path(path))
        if dir_type_name not in ("file_path", "feed_dir_path"):
            LOGGER.error("can't identify directory/file type '%s'", dir_type_name)
            return

        with DB.session_ctx() as s:
            if dir_type_name == "feed_dir_path":
                feed_dir_path_str = PathUtil.short_path(path)
                rows = s.query(HtmlFileInfo).where(HtmlFileInfo.feed_dir_path == feed_dir_path_str).all()
                for row in rows:
                    file_path = row.file_path
                    if do_remove_file:
                        (self.work_dir_path / file_path).unlink(missing_ok=True)
                s.query(HtmlFileInfo).filter_by(feed_dir_path=feed_dir_path_str).delete()

            if dir_type_name == "file_path":
                file_path_str = PathUtil.short_path(path)
                s.query(HtmlFileInfo).filter_by(file_path=file_path_str).delete()
                if do_remove_file:
                    path.unlink(missing_ok=True)

        LOGGER.info("* The removing of some html files in '%s' is done", PathUtil.short_path(path))

    def _add_html_file(self, s: Session, feed_dir_path: Path) -> int:
        LOGGER.debug("# _add_html_info(feed_dir_path=%s)", PathUtil.short_path(feed_dir_path))
        html_file_count = 0
        update_date = datetime.now(timezone.utc)

        for path in feed_dir_path.glob("html/*"):
            feed_name = path.parent.name
            group_name = path.parent.parent.name
            if feed_name.startswith("_") or group_name.startswith("_"):
                continue

            if path.suffix == ".html":
                st = path.stat()
                html_file_count += 1

                file_path_str = PathUtil.short_path(path)
                file_name = self.get_html_file_name(path)
                feed_dir_path_str = PathUtil.short_path(feed_dir_path)
                update_date = datetime.fromtimestamp(st.st_mtime, timezone.utc)
                size = st.st_size

                #if size < FeedMaker.get_size_of_template_with_image_tag(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), feed_name):
                #print(f"{file_path_str=}, {size=}")
                s.merge(HtmlFileInfo(file_path=file_path_str, file_name=file_name, feed_dir_path=feed_dir_path_str, size=size, update_date=update_date))
                s.flush()

        return html_file_count

    def add_html_file(self, feed_dir_path: Path) -> None:
        if not feed_dir_path.is_dir():
            LOGGER.error("can't find a feed directory '%s'", PathUtil.short_path(feed_dir_path))
            return
        with DB.session_ctx() as s:
            html_file_count = self._add_html_file(s, feed_dir_path)
        LOGGER.info("* The adding of some html files in '%s' is done. %d items", PathUtil.short_path(feed_dir_path), html_file_count)

    def load_all_html_files(self, max_num_feeds: Optional[int] = None) -> None:
        LOGGER.debug("# load_all_html_files(max_num_feeds=%r)", max_num_feeds)
        start_ts = datetime.now(timezone.utc)

        with DB.session_ctx() as s:
            db_files = {row.file_path: row.update_date for row in s.query(HtmlFileInfo.file_path, HtmlFileInfo.update_date).all()}
            
            new_files = []
            updated_files = []
            
            file_system_paths = set()

            for group_path in islice(self.work_dir_path.iterdir(), max_num_feeds):
                if not group_path.is_dir():
                    continue

                for feed_dir_path in group_path.iterdir():
                    if not feed_dir_path.is_dir():
                        continue
                    
                    for path in feed_dir_path.glob("html/*.html"):
                        file_path_str = PathUtil.short_path(path)
                        file_system_paths.add(file_path_str)
                        
                        try:
                            mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                        except FileNotFoundError:
                            continue

                        if file_path_str not in db_files:
                            # New file
                            new_files.append(self._prepare_html_file_info(path, mtime))
                        elif mtime != db_files[file_path_str]:
                            # Updated file
                            updated_files.append(self._prepare_html_file_info(path, mtime))
            
            deleted_files = set(db_files.keys()) - file_system_paths

            if new_files:
                s.bulk_insert_mappings(new_files)
            if updated_files:
                s.bulk_update_mappings(updated_files)
            if deleted_files:
                s.query(HtmlFileInfo).filter(HtmlFileInfo.file_path.in_(deleted_files)).delete(synchronize_session=False)

        end_ts = datetime.now(timezone.utc)
        total_processed = len(new_files) + len(updated_files) + len(deleted_files)
        LOGGER.info("* The loading of all html files is done. %d items processed / %s sec", total_processed, (end_ts - start_ts).total_seconds())

    def _prepare_html_file_info(self, path: Path, mtime: datetime) -> dict[str, Any]:
        file_path_str = PathUtil.short_path(path)
        file_name = self.get_html_file_name(path)
        feed_dir_path_str = PathUtil.short_path(path.parent.parent)
        size = path.stat().st_size

        count_with_many_image_tag = 0
        count_without_image_tag = 0
        count_with_image_not_found = 0
        image_tag_count = 0

        try:
            with path.open('r', encoding="utf-8") as infile:
                for line in infile:
                    if re.search(r'1x1\.jpg', line):
                        image_tag_count += 1
                    if re.search(r'image-not-found\.png', line):
                        count_with_image_not_found += 1
        except (FileNotFoundError, UnicodeDecodeError) as e:
            LOGGER.warning("Could not process file %s: %s", file_path_str, e)
        
        if image_tag_count > 1:
            count_with_many_image_tag = 1
        elif image_tag_count < 1:
            count_without_image_tag = 1
        
        return {
            "file_path": file_path_str,
            "file_name": file_name,
            "feed_dir_path": feed_dir_path_str,
            "size": size,
            "update_date": mtime,
            "count_with_many_image_tag": count_with_many_image_tag,
            "count_without_image_tag": count_without_image_tag,
            "count_with_image_not_found": count_with_image_not_found,
        }
