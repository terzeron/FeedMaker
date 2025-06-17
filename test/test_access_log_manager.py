#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import shutil
import logging.config
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from test.test_common import TestCommon
from bin.access_log_manager import AccessLogManager
from bin.db import DB
from bin.models import FeedInfo

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestAccessLogManager(unittest.TestCase):
    loki_container = None
    mysql_container = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.loki_container = TestCommon.prepare_loki_container()
        cls.mysql_container = TestCommon.prepare_mysql_container()
        DB.init(TestCommon.get_db_config(cls.mysql_container))

    @classmethod
    def tearDownClass(cls) -> None:
        TestCommon.dispose_mysql_container(cls.mysql_container)
        TestCommon.dispose_loki_container(cls.loki_container)

    def setUp(self) -> None:
        self.loki_url = TestCommon.get_loki_url(self.__class__.loki_container)
        self.db_config = TestCommon.get_db_config(self.__class__.mysql_container)
        DB.create_all_tables(self.db_config)

        self.alm = AccessLogManager(loki_url=self.loki_url)

        self.test_feed_dir_path = AccessLogManager.work_dir_path / "my_test_group" / "my_test_feed3"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_feed_dir_path.parent)

        del self.alm

        DB.drop_all_tables(self.db_config)
        del self.db_config
        del self.loki_url

    def test_loki_search(self) -> None:
        # from yesterday to today
        start_dt = datetime.now(timezone.utc) - timedelta(days=1)
        start_ns = int(
            start_dt.replace(tzinfo=timezone.utc).timestamp()) * 1_000_000_000 + start_dt.microsecond * 1000
        end_dt = datetime.now(timezone.utc)
        end_ns = int(
            end_dt.replace(tzinfo=timezone.utc).timestamp()) * 1_000_000_000 + end_dt.microsecond * 1000
        params = {
            "query": '{namespace="feedmaker"}',
            "start": start_ns,
            "end": end_ns,
            "limit": 5000,
            "direction": "forward"
        }
        logs, stats = self.alm.loki_search(params)
        self.assertIsNotNone(logs)
        self.assertGreater(len(logs), 0)
        self.assertIsNotNone(stats)
        self.assertGreater(len(stats), 0)

    def test_search(self) -> None:
        today = date.today()
        accessed_feed_list, viewed_feed_list = self.alm.search_by_date(today)
        self.assertGreater(len(accessed_feed_list), 0)
        self.assertGreaterEqual(len(viewed_feed_list), 0)

    def test_add_httpd_access_info(self) -> None:
        # get date from recent log file
        today = date.today()
        recent_date: datetime = datetime.now(timezone.utc) - timedelta(days=60)
        for i in range(7):
            specific_date = today - timedelta(days=i)
            accessed_feed_list, viewed_feed_list = self.alm.search_by_date(specific_date)
            if accessed_feed_list or viewed_feed_list:
                recent_date = sorted(accessed_feed_list + viewed_feed_list)[-1][0]
                break

        self.alm.add_httpd_access_info()

        with DB.session_ctx() as s:
            rows = s.query(FeedInfo).all()
            assert rows is not None
            self.assertGreaterEqual(len(rows), 1)
            for row in rows:
                assert row is not None
                self.assertIsNotNone(row.feed_name)
                self.assertTrue(row.http_request)
                self.assertEqual(row.access_date.date() if row.access_date else None, recent_date.date() if recent_date else None)

    def test_load_all_httpd_access_info(self) -> None:
        self.alm.load_all_httpd_access_info(max_num_days=14)

        with DB.session_ctx() as s:
            rows = s.query(FeedInfo).all()
            assert rows is not None
            self.assertGreaterEqual(len(rows), 1)
            for row in rows:
                assert row is not None
                self.assertIsNotNone(row.feed_name)
                self.assertIsNotNone(row.access_date)


if __name__ == "__main__":
    unittest.main()
