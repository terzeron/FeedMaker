#!/usr/bin/env python

import os
import re
import logging.config
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import requests
from bin.feed_maker_util import Datetime
from bin.db_manager import DBManager, Cursor, IntegrityError

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class AccessLogManager:
    work_dir = Path(os.environ["FM_WORK_DIR"])

    def __init__(self, db_manager: Optional[DBManager] = None) -> None:
        if db_manager:
            self.db = db_manager
        else:
            self.db = DBManager(os.environ["FM_DB_HOST"], int(os.environ["FM_DB_PORT"]), os.environ["MYSQL_DATABASE"], os.environ["MYSQL_USER"], os.environ["MYSQL_PASSWORD"])

        self.loki_url = os.environ["FM_LOKI_URL"] + "/query_range"

    def loki_search(self, params) -> Tuple[List[str], Dict[str, Any]]:
        logs: List[str] = []
        stats: Dict[str, Any] = {}
        response = requests.get(self.loki_url, params=params, timeout=60, verify=False)
        if response:
            json_data = response.json()
            if "status" in json_data and json_data["status"] == "success":
                if "data" in json_data and "result" in json_data["data"]:
                    if "stats" in json_data["data"]:
                        stats = json_data["data"]["stats"]

                    for result in json_data["data"]["result"]:
                        if "values" in result:
                            for _, log_item in result["values"]:
                                logs.append(log_item)
        return logs, stats

    def search(self, date_str: str) -> Tuple[List[Tuple[datetime, str]], List[Tuple[datetime, str]]]:
        duration_in_minutes = 60 * 24 * 1 # 1 days
        step_in_minutes = 60 * 6 # by 6 hours

        # 특정일 0시 0분 0초
        the_day = datetime.strptime(date_str, "%Y-%m-%d")

        accessed_feed_list: List[Tuple[datetime, str]] = []
        viewed_feed_list: List[Tuple[datetime, str]] = []
        for i in range(0, duration_in_minutes, step_in_minutes):
            start = (the_day + timedelta(minutes=i)).astimezone().isoformat()
            end = (the_day + timedelta(minutes=i + step_in_minutes)).astimezone().isoformat()
            params = {"query": '{namespace="feedmaker"}', "start": start, "end": end, "limit": 5000, "direction": "forward"}

            result, _ = self.loki_search(params)
            for log in result:
                m = re.search(r'\[(?P<time>[^\]]+)\] "GET (?P<uri>[^ ]+) HTTP[^"]+\" (?P<status>\d+)', log)
                if m:
                    if m.group("status") == "200" or m.group("status") == "304":
                        time = m.group("time")
                        dt = datetime.strptime(time, "%d/%b/%Y:%H:%M:%S %z")

                        uri = m.group("uri")
                        m = re.search(r'/xml/img/(?P<feed>[^/]+)/(?P<item>.+)', uri)
                        if m:
                            feed = m.group("feed")
                            #item = m.group("item")
                        m = re.search(r'/xml/(?P<feed>.+).xml', uri)
                        if m:
                            feed = m.group("feed")
                            accessed_feed_list.append((dt, feed))
                        m = re.search(r'/img/1x1\.jpg\?feed=(?P<feed>[^&]+)\.xml&item=(?P<item>.+)', uri)
                        if m:
                            feed = m.group("feed")
                            #item = m.group("item")
                            viewed_feed_list.append((dt, feed))

        return accessed_feed_list, viewed_feed_list

    def remove_httpd_access_info(self, feed_dir_path: Path) -> None:
        feed_name = feed_dir_path.name
        with self.db.get_connection_and_cursor() as (connection, cursor):
            self.db.execute(cursor, "UPDATE feed_info SET http_request = NULL, access_date = NULL WHERE feed_name = %s", feed_name)
            self.db.commit(connection)
        LOGGER.info("* The removing of access info of feed '%s' is done.", feed_name)

    def _add_httpd_access_info(self, cursor: Cursor, date_str: str = "") -> int:
        num_items = 0
        accessed_feed_list, viewed_feed_list = self.search(date_str)
        for access_date, feed_name in accessed_feed_list:
            access_date_str = Datetime.convert_datetime_to_str(access_date)
            try:
                self.db.execute(cursor, "INSERT INTO feed_info (feed_name, http_request, access_date) VALUES (%s, %s, %s)", feed_name, True, access_date_str)
            except IntegrityError:
                self.db.execute(cursor, "UPDATE feed_info SET http_request = %s, access_date = %s WHERE feed_name = %s", True, access_date_str, feed_name)
            num_items += 1

        for view_date, feed_name in viewed_feed_list:
            view_date_str = Datetime.convert_datetime_to_str(view_date)
            try:
                self.db.execute(cursor, "INSERT INTO feed_info (feed_name, http_request, view_date) VALUES (%s, %s, %s)", feed_name, True, view_date_str)
            except IntegrityError:
                self.db.execute(cursor, "UPDATE feed_info SET http_request = %s, view_date = %s WHERE feed_name = %s", True, view_date_str, feed_name)
            num_items += 1

        return num_items

    def add_httpd_access_info(self) -> None:
        LOGGER.debug("# add_httpd_access_info()")
        with self.db.get_connection_and_cursor() as (connection, cursor):
            rows = self.db.query("SELECT DATEDIFF(CURRENT_DATE, MAX(access_date)) AS days FROM feed_info")
            if rows and len(rows) > 0 and rows[0]["days"] is not None:
                days = rows[0]["days"] + 1
            else:
                days = 30

            for i in range(days, -1, -1):
                date_str = (datetime.today() - timedelta(days=i)).strftime("%Y-%m-%d")
                self._add_httpd_access_info(cursor, date_str)
            self.db.commit(connection)
        LOGGER.info("* The adding of access info is done.")

    def load_all_httpd_access_info(self, max_num_days: int = 30) -> None:
        LOGGER.debug("# load_all_httpd_access_info(max_num_days=%d)", max_num_days)
        start_ts = datetime.now()
        with self.db.get_connection_and_cursor() as (connection, cursor):
            # read access.log for 1 month
            today = datetime.today()
            num_items = 0
            for i in range(max_num_days, -1, -1):
                date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                num_items += self._add_httpd_access_info(cursor, date_str=date_str)

            self.db.commit(connection)
        end_ts = datetime.now()
        LOGGER.info("* The loading of all httpd access logs is done. %d items / %s sec", num_items, (end_ts - start_ts))
