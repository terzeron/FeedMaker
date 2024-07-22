#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import unittest
import shutil
import logging.config
from datetime import datetime, timedelta
from pathlib import Path
from bin.feed_manager import FeedManager
from bin.access_log_manager import AccessLogManager
from bin.db_manager import DBManager


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestAccessLogManager(unittest.TestCase):
    def setUp(self) -> None:
        self.db = DBManager(os.environ["FM_DB_HOST"], int(os.environ["FM_DB_PORT"]), os.environ["MYSQL_DATABASE"], os.environ["MYSQL_USER"], os.environ["MYSQL_PASSWORD"])
        self.alm = AccessLogManager(self.db)
        self.fm = FeedManager(self.db)

        self.test_feed_dir_path = self.alm.work_dir / "my_test_group" / "my_test_feed3"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

        with self.alm.db.get_connection_and_cursor() as (connection, cursor):
            self.alm.db.execute(cursor, "DELETE FROM feed_info WHERE feed_name LIKE 'my_test_feed%'")
            self.alm.db.commit(connection)

    def tearDown(self) -> None:
        with self.alm.db.get_connection_and_cursor() as (connection, cursor):
            self.alm.db.execute(cursor, "DELETE FROM feed_info WHERE feed_name LIKE 'my_test_feed%'")
            self.alm.db.commit(connection)

        del self.alm
        shutil.rmtree(self.test_feed_dir_path.parent)

    def test_loki_search(self):
        access_log_manager = AccessLogManager()
        start = (datetime.now() + timedelta(days=-1)).strftime("%Y-%m-%dT00:00:00+09:00")
        end = datetime.now().strftime("%Y-%m-%dT23:59:59+09:00")
        params = {"query": '{namespace="feedmaker"}', "start": start, "end": end, "limit": 5000, "direction": "forward"}
        logs, stats = access_log_manager.loki_search(params)
        self.assertTrue(logs)
        self.assertTrue(stats)

    def test_search(self):
        access_log_manager = AccessLogManager()
        date_str = datetime.now().strftime("%Y-%m-%d")
        accessed_feed_list, viewed_feed_list = access_log_manager.search(date_str)
        self.assertGreater(len(accessed_feed_list), 0)
        self.assertGreaterEqual(len(viewed_feed_list), 0)

    def test_add_httpd_access_info(self):
        self.alm.load_all_httpd_access_info(max_num_days=14)
        feed_name = "navercast"

        # get date from recent log file
        today = datetime.today()
        recent_log_file_date_str = ""
        for i in range(7):
            specific_date = today - timedelta(days=i)
            date_str = specific_date.strftime("%Y-%m-%d")
            accessed_feed_list, viewed_feed_list = self.alm.search(date_str)
            if accessed_feed_list or viewed_feed_list:
                recent_log_file_date_str = sorted(accessed_feed_list + viewed_feed_list)[-1][0].strftime("%Y-%m-%d")
                break

        self.alm.add_httpd_access_info()
        rows = self.db.query("SELECT * FROM feed_info WHERE feed_name = %s", feed_name)
        self.assertIsNotNone(rows)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["access_date"].strftime("%Y-%m-%d"), recent_log_file_date_str)

    def test_load_all_httpd_access_info(self):
        self.alm.load_all_httpd_access_info(max_num_days=14)

        row = self.db.query("SELECT * FROM feed_info WHERE http_request = TRUE")
        self.assertGreater(len(row[0]), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["feed_name"])
            self.assertIsNotNone(row[0]["access_date"])


if __name__ == "__main__":
    unittest.main()
