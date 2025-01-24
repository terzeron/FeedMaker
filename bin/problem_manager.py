#!/usr/bin/env python


import os
import logging.config
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from bin.feed_maker_util import PathUtil
from bin.feed_manager import FeedManager
from bin.access_log_manager import AccessLogManager
from bin.html_file_manager import HtmlFileManager
from bin.db_manager import DBManager

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class ProblemManager:
    num_days = 60

    def __init__(self, db_manager: Optional[DBManager] = None) -> None:
        if db_manager:
            self.db = db_manager
        else:
            self.db = DBManager(os.environ["FM_DB_HOST"], int(os.environ["FM_DB_PORT"]), os.environ["MYSQL_DATABASE"], os.environ["MYSQL_USER"], os.environ["MYSQL_PASSWORD"])

        self.feed_manager = FeedManager()
        self.access_log_manager = AccessLogManager(self.db)
        self.html_file_manager = HtmlFileManager(self.db)

    def __del__(self) -> None:
        del self.feed_manager
        del self.access_log_manager
        del self.html_file_manager
        del self.db

    def get_feed_name_status_info_map(self) -> Dict[str, Dict[str, Any]]:
        LOGGER.debug("# get_feed_name_status_info_map()")
        feed_name_status_info_map = {}

        # exclude feeds unrequested and unregistered and unmade
        # --> NOT ( http_request = 0 AND public_html = 0 AND feedmaker = 0 )
        # exclude feeds REQUESTED and unregistered and unmade but ACCESSED long ago
        # --> NOT ( http_request = 1 AND public_html = 0 AND feedmaker = 0 AND access_date IS NOT NULL AND DATEDIFF(access_date, current_date) > %s )
        # exclude feeds REQUESTED and REGISTERED and MADE AND ACCESSED OR VIEWED RECENTLY
        # --> NOT ( http_request = 1 AND public_html = 1 AND feedmaker = 1 AND ( access_date IS NOT NULL AND DATEDIFF(current_date, access_date) < %s OR view_date IS NOT NULL AND DATEDIFF(current_date, view_date) < %s ) )
        for row in self.db.query("SELECT * FROM feed_info WHERE NOT ( http_request = 0 AND public_html = 0 AND feedmaker = 0 ) AND NOT ( http_request = 1 AND public_html = 0 AND feedmaker = 0 AND access_date IS NOT NULL AND DATEDIFF(access_date, current_date) > %s ) AND NOT ( http_request = 1 AND public_html = 1 AND feedmaker = 1 AND config IS NOT NULL AND ( access_date IS NOT NULL AND DATEDIFF(current_date, access_date) < %s OR view_date IS NOT NULL AND DATEDIFF(current_date, view_date) < %s ) ) ORDER BY feedmaker, public_html, http_request, collect_date, rss_update_date, upload_date, access_date, view_date", self.num_days, self.num_days, self.num_days):
            feed_name = row["feed_name"]
            feed_name_status_info_map[feed_name] = {
                "feed_name": feed_name,
                "feed_title": row["feed_title"],
                "group_name": row["group_name"],
                "http_request": row["http_request"],
                "access_date": row["access_date"],
                "view_date": row["view_date"],
                "feedmaker": row["feedmaker"],
                "update_date": row["rss_update_date"],
                "public_html": row["public_html"],
                "file_path": row["public_feed_file_path"],
                "upload_date": row["upload_date"]
            }

        return feed_name_status_info_map

    def update_feed_info(self, feed_dir_path: Path, new_feed_dir_path: Optional[Path] = None) -> None:
        LOGGER.debug("# update_feed_info(feed_dir_path=%s, new_feed_dir_path=%s)", PathUtil.short_path(feed_dir_path), PathUtil.short_path(new_feed_dir_path))
        if not new_feed_dir_path:
            new_feed_dir_path = feed_dir_path

        if not feed_dir_path.is_dir() and not new_feed_dir_path.is_dir():
            LOGGER.warning("can't find feed directory '%s' or '%s'", PathUtil.short_path(feed_dir_path), PathUtil.short_path(new_feed_dir_path))
        self.feed_manager.remove_config_info(feed_dir_path)
        self.feed_manager.remove_rss_info(feed_dir_path)
        self.feed_manager.remove_public_feed_by_feed_name(feed_dir_path.name)
        self.feed_manager.remove_progress_info(feed_dir_path)
        self.access_log_manager.remove_httpd_access_info(feed_dir_path)
        self.html_file_manager.remove_html_file_in_path_from_info("feed_dir_path", feed_dir_path)

        self.feed_manager.add_config_info(new_feed_dir_path)
        self.feed_manager.add_rss_info(new_feed_dir_path)
        self.feed_manager.add_public_feed_by_feed_name(new_feed_dir_path.name)
        self.feed_manager.add_progress_info(new_feed_dir_path)
        self.access_log_manager.add_httpd_access_info()
        self.html_file_manager.add_html_file(new_feed_dir_path)

    def lock_problem_database(self) -> bool:
        with self.db.get_connection_and_cursor(with_serializable_transaction=True) as (connection, cursor):
            rows = self.db.query("SELECT * FROM lock_for_concurrent_loading FOR UPDATE")
            if rows and len(rows) > 0:
                if rows[0]["lock_time"] and datetime.now() - rows[0]["lock_time"] < timedelta(seconds=60):
                    self.db.rollback(connection)
                    return False
                self.db.execute(cursor, "DELETE FROM lock_for_concurrent_loading")
            self.db.execute(cursor, "INSERT INTO lock_for_concurrent_loading VALUES (CURRENT_TIMESTAMP)")
            self.db.commit(connection)
        return True

    def unlock_problem_database(self) -> None:
        with self.db.get_connection_and_cursor(with_serializable_transaction=True) as (connection, cursor):
            rows = self.db.query("SELECT * FROM lock_for_concurrent_loading FOR UPDATE")
            if not rows or len(rows) == 0:
                self.db.rollback(connection)
                return
            self.db.execute(cursor, "DELETE FROM lock_for_concurrent_loading")
            self.db.commit(connection)

    def load_all(self, max_num_feeds: Optional[int] = None, max_num_public_feeds: Optional[int] = None, max_num_days: int = 30) -> int:
        LOGGER.debug("# load_all(max_num_feeds=%r, max_num_public_feds=%r, max_num_days=%d)", max_num_feeds, max_num_public_feeds, max_num_days)
        if self.lock_problem_database():
            LOGGER.info("* start loading information")
            self.feed_manager.load_all_config_files(max_num_feeds)
            self.feed_manager.load_all_rss_files(max_num_feeds)
            self.feed_manager.load_all_public_feed_files(max_num_public_feeds)
            self.feed_manager.load_all_progress_info_from_files(max_num_feeds)
            self.access_log_manager.load_all_httpd_access_info(max_num_days)
            self.html_file_manager.load_all_html_files(max_num_feeds)
            self.unlock_problem_database()
            LOGGER.info("* finish loading information")
        else:
            LOGGER.info("* abort loading information")
        return 0


if __name__ == "__main__":
    pm = ProblemManager()
    pm.load_all()
