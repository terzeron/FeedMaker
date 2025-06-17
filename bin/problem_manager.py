#!/usr/bin/env python


import logging.config
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional
from bin.feed_maker_util import PathUtil
from bin.feed_manager import FeedManager
from bin.access_log_manager import AccessLogManager
from bin.html_file_manager import HtmlFileManager
from bin.db import DB, not_, and_, or_, func
from bin.models import LockForConcurrentLoading, FeedInfo

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class ProblemManager:
    num_days = 60

    def __init__(self, loki_url: Optional[str] = None) -> None:
        self.feed_manager = FeedManager()
        self.access_log_manager = AccessLogManager(loki_url=loki_url)
        self.html_file_manager = HtmlFileManager()

    def __del__(self) -> None:
        del self.feed_manager
        del self.access_log_manager
        del self.html_file_manager

    @classmethod
    def get_feed_name_status_info_map(cls) -> dict[str, dict[str, Any]]:
        LOGGER.debug("# get_feed_name_status_info_map()")
        feed_name_status_info_map: dict[str, dict[str, Any]] = {}

        # exclude feeds unrequested and unregistered and unmade
        # --> NOT ( http_request = 0 AND public_html = 0 AND feedmaker = 0 )
        # exclude feeds REQUESTED and unregistered and unmade but ACCESSED long ago
        # --> NOT ( http_request = 1 AND public_html = 0 AND feedmaker = 0 AND access_date IS NOT NULL AND DATEDIFF(access_date, current_date) > %s )
        # exclude feeds REQUESTED and REGISTERED and MADE AND ACCESSED OR VIEWED RECENTLY
        # --> NOT ( http_request = 1 AND public_html = 1 AND feedmaker = 1 AND ( access_date IS NOT NULL AND DATEDIFF(current_date, access_date) < %s OR view_date IS NOT NULL AND DATEDIFF(current_date, view_date) < %s ) )
        #for row in self.db.query("SELECT * FROM feed_info WHERE NOT ( http_request = 0 AND public_html = 0 AND feedmaker = 0 ) AND NOT ( http_request = 1 AND public_html = 0 AND feedmaker = 0 AND access_date IS NOT NULL AND DATEDIFF(access_date, current_date) > %s ) AND NOT ( http_request = 1 AND public_html = 1 AND feedmaker = 1 AND config IS NOT NULL AND ( access_date IS NOT NULL AND DATEDIFF(current_date, access_date) < %s OR view_date IS NOT NULL AND DATEDIFF(current_date, view_date) < %s ) ) ORDER BY feedmaker, public_html, http_request, collect_date, rss_update_date, upload_date, access_date, view_date", self.num_days, self.num_days, self.num_days):
        with DB.session_ctx() as s:
            rows = s.query(FeedInfo).where(
                # 1) http_request=0 AND public_html=0 AND feedmaker=0 인 행 제외
                not_(and_(
                    not_(FeedInfo.http_request),
                    not_(FeedInfo.public_html),
                    not_(FeedInfo.feedmaker),
                )),
                # 2) http_request=1, public_html=0, feedmaker=0, access_date IS NOT NULL,
                #    DATEDIFF(access_date, current_date) > num_days 인 행 제외
                not_(and_(
                    FeedInfo.http_request,
                    not_(FeedInfo.public_html),
                    not_(FeedInfo.feedmaker),
                    FeedInfo.access_date.isnot(None),
                    func.datediff(FeedInfo.access_date, func.current_timestamp) > cls.num_days,
                )),
                # 3) http_request=1, public_html=1, feedmaker=1, config IS NOT NULL,
                #    AND (access_date IS NOT NULL AND DATEDIFF(current_date,access_date)<num_days
                #         OR view_date IS NOT NULL AND DATEDIFF(current_date,view_date)<num_days)
                not_(and_(
                    FeedInfo.http_request,
                    FeedInfo.public_html,
                    FeedInfo.feedmaker,
                    FeedInfo.config.isnot(None),
                    or_(
                        and_(
                            FeedInfo.access_date.isnot(None),
                            func.datediff(func.current_timestamp, FeedInfo.access_date) < cls.num_days,
                        ),
                        and_(
                            FeedInfo.view_date.isnot(None),
                            func.datediff(func.current_timestamp, FeedInfo.view_date) < cls.num_days,
                        ),
                    ),
                )),
            ).order_by(
                FeedInfo.feedmaker,
                FeedInfo.public_html,
                FeedInfo.http_request,
                FeedInfo.collect_date,
                FeedInfo.rss_update_date,
                FeedInfo.upload_date,
                FeedInfo.access_date,
                FeedInfo.view_date,
            ).all()
            for row in rows:
                feed_name = row.feed_name
                feed_name_status_info_map[feed_name] = {
                    "feed_name": feed_name,
                    "feed_title": row.feed_title,
                    "group_name": row.group_name,
                    "http_request": row.http_request,
                    "access_date": row.access_date,
                    "view_date": row.view_date,
                    "feedmaker": row.feedmaker,
                    "update_date": row.rss_update_date,
                    "public_html": row.public_html,
                    "file_path": row.public_feed_file_path,
                    "upload_date": row.upload_date
                }

        return feed_name_status_info_map

    def update_feed_info(self, feed_dir_path: Path, new_feed_dir_path: Optional[Path] = None) -> None:
        LOGGER.debug("# update_feed_info(feed_dir_path=%s, new_feed_dir_path=%s)", PathUtil.short_path(feed_dir_path), PathUtil.short_path(new_feed_dir_path))
        if not new_feed_dir_path:
            new_feed_dir_path = feed_dir_path

        if not feed_dir_path.is_dir() and not new_feed_dir_path.is_dir():
            LOGGER.warning("can't find feed directory '%s' or '%s'", PathUtil.short_path(feed_dir_path), PathUtil.short_path(new_feed_dir_path))
        FeedManager.remove_config_info(feed_dir_path)
        FeedManager.remove_rss_info(feed_dir_path)
        self.feed_manager.remove_public_feed_by_feed_name(feed_dir_path.name)
        FeedManager.remove_progress_info(feed_dir_path)
        AccessLogManager.remove_httpd_access_info(feed_dir_path)
        self.html_file_manager.remove_html_file_in_path_from_info("feed_dir_path", feed_dir_path)

        FeedManager.add_config_info(new_feed_dir_path)
        FeedManager.add_rss_info(new_feed_dir_path)
        self.feed_manager.add_public_feed_by_feed_name(new_feed_dir_path.name)
        FeedManager.add_progress_info(new_feed_dir_path)
        self.access_log_manager.add_httpd_access_info()
        self.html_file_manager.add_html_file(new_feed_dir_path)

    @staticmethod
    def lock_problem_database() -> bool:
        with DB.session_ctx(isolation_level="SERIALIZABLE") as s:
            rows = s.query(LockForConcurrentLoading).all()
            if not rows:
                s.add(LockForConcurrentLoading(lock_time=datetime.now(timezone.utc)))
                return True
            row = rows[0]
            lock_time = row.lock_time
            if (datetime.now(timezone.utc) - lock_time).total_seconds() < 60:
                return False
            s.query(LockForConcurrentLoading).delete()
            s.add(LockForConcurrentLoading(lock_time=datetime.now(timezone.utc)))
            return True

    @staticmethod
    def unlock_problem_database() -> None:
        with DB.session_ctx(isolation_level="SERIALIZABLE") as s:
            rows = s.query(LockForConcurrentLoading).all()
            if not rows or len(rows) == 0:
                return
            s.query(LockForConcurrentLoading).delete()

    def load_all(self, max_num_feeds: Optional[int] = None, max_num_public_feeds: Optional[int] = None, max_num_days: int = 30) -> int:
        LOGGER.debug("# load_all(max_num_feeds=%r, max_num_public_feds=%r, max_num_days=%d)", max_num_feeds, max_num_public_feeds, max_num_days)
        if ProblemManager.lock_problem_database():
            LOGGER.info("* start loading information")
            self.feed_manager.load_all_config_files(max_num_feeds)
            self.feed_manager.load_all_rss_files(max_num_feeds)
            self.feed_manager.load_all_public_feed_files(max_num_public_feeds)
            self.feed_manager.load_all_progress_info_from_files(max_num_feeds)
            self.access_log_manager.load_all_httpd_access_info(max_num_days)
            self.html_file_manager.load_all_html_files(max_num_feeds)
            ProblemManager.unlock_problem_database()
            LOGGER.info("* finish loading information")
        else:
            LOGGER.info("* abort loading information")
        return 0


if __name__ == "__main__":
    pm = ProblemManager()
    pm.load_all()
