#!/usr/bin/env python


import logging.config
from pathlib import Path
from datetime import datetime, timezone

from bin.feed_maker_util import Env
from bin.models import FeedInfo
from bin.db import DB

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class AccessLogManager:
    work_dir_path = Path(Env.get("FM_WORK_DIR"))

    @staticmethod
    def record_feed_access(feed_name: str) -> None:
        now = datetime.now(timezone.utc)
        try:
            with DB.session_ctx() as s:
                existing_feeds = s.query(FeedInfo).filter_by(feed_name=feed_name).all()
                if existing_feeds:
                    for feed in existing_feeds:
                        feed.http_request = True
                        feed.access_date = now
                else:
                    s.add(FeedInfo(feed_name=feed_name, http_request=True, access_date=now))
            LOGGER.debug("Recorded feed access: %s", feed_name)
        except Exception:
            LOGGER.error("Failed to record feed access for '%s'", feed_name, exc_info=True)

    @staticmethod
    def record_item_view(feed_name: str) -> None:
        now = datetime.now(timezone.utc)
        try:
            with DB.session_ctx() as s:
                existing_feeds = s.query(FeedInfo).filter_by(feed_name=feed_name).all()
                if existing_feeds:
                    for feed in existing_feeds:
                        feed.http_request = True
                        feed.view_date = now
                else:
                    s.add(FeedInfo(feed_name=feed_name, http_request=True, view_date=now))
            LOGGER.debug("Recorded item view: %s", feed_name)
        except Exception:
            LOGGER.error("Failed to record item view for '%s'", feed_name, exc_info=True)

    @classmethod
    def remove_httpd_access_info(cls, feed_dir_path: Path) -> None:
        feed_name = feed_dir_path.name
        with DB.session_ctx() as s:
            s.query(FeedInfo).filter_by(feed_name=feed_name).update({FeedInfo.http_request: False, FeedInfo.access_date: None})
        LOGGER.info("* The removing of access info of feed '%s' is done.", feed_name)
