#!/usr/bin/env python


import re
import logging.config
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, date, timedelta, timezone
import requests

from bin.feed_maker_util import Env
from bin.models import FeedInfo
from bin.db import DB, func

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class AccessLogManager:
    work_dir_path = Path(Env.get("FM_WORK_DIR"))

    def __init__(self, *, loki_url: Optional[str] = None) -> None:
        self.loki_url = (loki_url if loki_url else Env.get("FM_LOKI_URL")) + "/query_range"

    def __del__(self) -> None:
        del self.loki_url

    def loki_search(self, params: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        logs: list[str] = []
        stats: dict[str, Any] = {}
        response = requests.get(self.loki_url, params=params, timeout=60, verify=False)
        response.raise_for_status()
        if response:
            json_data = response.json()
            status = json_data.get("status", "")
            if status == "success":
                data = json_data.get("data", {})
                if data:
                    result = data.get("result", [])
                    for result_item in result:
                        values = result_item.get("values", [])
                        for _, log_item in values:
                            logs.append(log_item)
                    stats = data.get("stats", {})

        return logs, stats

    def search_by_date(self, the_day: date) -> tuple[list[tuple[datetime, str]], list[tuple[datetime, str]]]:
        duration_in_minutes = 60 * 24  # 1 day
        step_in_minutes = 60 * 6  # by 6 hours

        accessed_feed_list: list[tuple[datetime, str]] = []
        viewed_feed_list: list[tuple[datetime, str]] = []
        local_tz = datetime.now().astimezone().tzinfo
        for i in range(0, duration_in_minutes, step_in_minutes):
            start_dt = (datetime(the_day.year, the_day.month, the_day.day, tzinfo=local_tz) + timedelta(minutes=i))
            start_ns = int(
                start_dt.replace(tzinfo=local_tz).timestamp()) * 1_000_000_000 + start_dt.microsecond * 1000
            end_dt = (datetime(the_day.year, the_day.month, the_day.day, tzinfo=local_tz) + timedelta(
                minutes=i + step_in_minutes))
            end_ns = int(end_dt.replace(tzinfo=local_tz).timestamp()) * 1_000_000_000 + end_dt.microsecond * 1000
            # print(f"{start_dt=} ~ {end_dt=}")
            params = {
                "query": '{namespace="feedmaker"}',
                "start": start_ns,
                "end": end_ns,
                "limit": 5000,
                "direction": "forward"
            }

            result, _ = self.loki_search(params)
            # print(result)
            for log in result:
                m = re.search(r'\[(?P<time>[^]]+)] "GET (?P<uri>[^ ]+) HTTP[^"]+\" (?P<status>\d+)', log)
                if m and m.group("status") in ("200", "304"):
                    dt = datetime.strptime(m.group("time"), "%d/%b/%Y:%H:%M:%S %z")
                    uri = m.group("uri")
                    m1 = re.search(r'/xml/(?P<feed>.+).xml', uri)
                    if m1:
                        accessed_feed_list.append((dt, m1.group("feed")))
                    m2 = re.search(r'/img/1x1\.jpg\?feed=(?P<feed>[^&]+)\.xml&item=(?P<item>.+)', uri)
                    if m2:
                        viewed_feed_list.append((dt, m2.group("feed")))

        return accessed_feed_list, viewed_feed_list

    @classmethod
    def remove_httpd_access_info(cls, feed_dir_path: Path) -> None:
        feed_name = feed_dir_path.name
        with DB.session_ctx() as s:
            s.query(FeedInfo).filter_by(feed_name=feed_name).update({
                FeedInfo.http_request: None, 
                FeedInfo.access_date: None
            })
        LOGGER.info("* The removing of access info of feed '%s' is done.", feed_name)

    def _add_httpd_access_info(self, specific_date: date) -> tuple[dict[str, datetime], dict[str, datetime]]:
        accessed_feed_list, viewed_feed_list = self.search_by_date(specific_date)

        latest_access: dict[str, datetime] = {}
        for access_date, feed_name in accessed_feed_list:
            if not (prev := latest_access.get(feed_name)) or access_date > prev:
                latest_access[feed_name] = access_date

        latest_view: dict[str, datetime] = {}
        for view_date, feed_name in viewed_feed_list:
            if not (prev := latest_access.get(feed_name)) or view_date > prev:
                latest_access[feed_name] = view_date

        return latest_access, latest_view

    def add_httpd_access_info(self) -> None:
        LOGGER.debug("# add_httpd_access_info()")
        # get the number of days since the last access date
        with DB.session_ctx() as s:
            row = s.query(func.datediff(func.current_date, func.max(FeedInfo.access_date)).label("days")).first()
            if row and row.days:
                days = row.days + 1
            else:
                days = 1  # 30

            for i in range(days, -1, -1):
                specific_date = datetime.today() - timedelta(days=i)
                latest_access, latest_view = self._add_httpd_access_info(specific_date)

                for feed_name, access_date in latest_access.items():
                    existing_feeds = s.query(FeedInfo).filter_by(feed_name=feed_name).all()
                    if existing_feeds:
                        for feed in existing_feeds:
                            feed.http_request = True
                            feed.access_date = access_date
                    else:
                        s.add(FeedInfo(feed_name=feed_name, http_request=True, access_date=access_date))

                for feed_name, view_date in latest_view.items():
                    existing_feeds = s.query(FeedInfo).filter_by(feed_name=feed_name).all()
                    if existing_feeds:
                        for feed in existing_feeds:
                            feed.http_request = True
                            feed.view_date = view_date
                    else:
                        s.add(FeedInfo(feed_name=feed_name, http_request=True, view_date=view_date))

        LOGGER.info("* The adding of access info is done.")

    def load_all_httpd_access_info(self, max_num_days: int = 30) -> None:
        LOGGER.debug("# load_all_httpd_access_info(max_num_days=%d)", max_num_days)
        start_ts = datetime.now(timezone.utc)
        latest_access: dict[str, datetime] = {}
        latest_view: dict[str, datetime] = {}

        for i in range(max_num_days, -1, -1):
            specific_date = datetime.today() - timedelta(days=i)
            latest_access, latest_view = self._add_httpd_access_info(specific_date)
            with DB.session_ctx() as s:
                for feed_name, access_date in latest_access.items():
                    existing_feeds = s.query(FeedInfo).filter_by(feed_name=feed_name).all()
                    if existing_feeds:
                        for feed in existing_feeds:
                            feed.http_request = True
                            feed.access_date = access_date
                    else:
                        s.add(FeedInfo(feed_name=feed_name, http_request=True, access_date=access_date))

            with DB.session_ctx() as s:
                for feed_name, view_date in latest_view.items():
                    existing_feeds = s.query(FeedInfo).filter_by(feed_name=feed_name).all()
                    if existing_feeds:
                        for feed in existing_feeds:
                            feed.http_request = True
                            feed.view_date = view_date
                    else:
                        s.add(FeedInfo(feed_name=feed_name, http_request=True, view_date=view_date))

        end_ts = datetime.now(timezone.utc)
        total_num_items = len(latest_access) + len(latest_view)
        LOGGER.info("* The loading of all httpd access logs is done. %d items / %s sec", total_num_items, (end_ts - start_ts))
