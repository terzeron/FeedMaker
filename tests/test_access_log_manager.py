#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Modified for testmon testing

import logging
import logging.config
import shutil
import time
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        # Mock containers instead of real ones
        print("🚀 Setting up mock containers...")
        start_time = time.time()
        
        # Mock DB configuration
        cls.mock_db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        }
        
        elapsed = time.time() - start_time
        print(f"✅ Mock setup completed in {elapsed:.2f}s")

    @classmethod
    def tearDownClass(cls) -> None:
        # No cleanup needed for mock containers
        pass

    def setUp(self) -> None:
        # Mock Loki URL
        self.loki_url = "http://localhost:3100"
        
        # Mock DB configuration
        self.mock_db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        }
        
        # Mock DB session
        self.mock_session = MagicMock()
        self.mock_query = MagicMock()
        self.mock_session.query.return_value = self.mock_query
        
        # Mock DB initialization
        with patch('bin.db.DB.init') as mock_init, \
             patch('bin.db.DB.create_all_tables') as mock_create_tables, \
             patch('bin.db.DB.session_ctx') as mock_session_ctx:
            
            mock_init.return_value = None
            mock_create_tables.return_value = None
            mock_session_ctx.return_value.__enter__.return_value = self.mock_session
            mock_session_ctx.return_value.__exit__.return_value = None
            
            # Initialize DB with mock config
            DB.init(self.mock_db_config)
            DB.create_all_tables(self.mock_db_config)

        # Mock AccessLogManager with mock Loki URL
        with patch('bin.access_log_manager.AccessLogManager.loki_search') as mock_loki_search:
            # Mock Loki search response
            mock_loki_search.return_value = (
                [{"timestamp": "1640995200000000000", "line": "test log entry"}],
                {"status": "success", "stats": {"ingester": {"totalLinesSent": "10"}}},
                1640995200000000000
            )

            self.alm = AccessLogManager(loki_url=self.loki_url)

        self.test_feed_dir_path = AccessLogManager.work_dir_path / "my_test_group" / "my_test_feed3"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_feed_dir_path.parent)

        del self.alm

        # Mock DB cleanup
        with patch('bin.db.DB.drop_all_tables') as mock_drop_tables:
            mock_drop_tables.return_value = None
            DB.drop_all_tables(self.mock_db_config)
        
        del self.mock_db_config
        del self.loki_url

    @patch('bin.access_log_manager.AccessLogManager.loki_search')
    def test_loki_search(self, mock_loki_search) -> None:
        # Mock Loki search response
        mock_loki_search.return_value = (
            [{"timestamp": "1640995200000000000", "line": "test log entry"}],
            {"status": "success", "stats": {"ingester": {"totalLinesSent": "10"}}},
            1640995200000000000
        )

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
        logs, stats, last_ts = self.alm.loki_search(params)
        self.assertIsNotNone(logs)
        self.assertGreater(len(logs), 0)
        self.assertIsNotNone(stats)
        self.assertGreater(len(stats), 0)
        self.assertIsNotNone(last_ts)

    @patch('bin.access_log_manager.AccessLogManager.search_by_date')
    def test_search(self, mock_search_by_date) -> None:
        # Mock search_by_date response
        mock_search_by_date.return_value = (
            [("test_feed", datetime.now())],  # accessed_feed_list
            [("test_feed2", datetime.now())]  # viewed_feed_list
        )
        
        today = date.today()
        accessed_feed_list, viewed_feed_list = self.alm.search_by_date(today)
        self.assertGreater(len(accessed_feed_list), 0)
        self.assertGreaterEqual(len(viewed_feed_list), 0)

    @patch('bin.access_log_manager.AccessLogManager.search_by_date')
    def test_add_httpd_access_info(self, mock_search_by_date) -> None:
        # Mock search_by_date response
        mock_search_by_date.return_value = (
            [("test_feed", datetime.now())],  # accessed_feed_list
            [("test_feed2", datetime.now())]  # viewed_feed_list
        )
        
        # Mock FeedInfo query results
        mock_feed_info = MagicMock()
        mock_feed_info.feed_name = "test_feed"
        mock_feed_info.http_request = True
        mock_feed_info.access_date = datetime.now()
        
        self.mock_query.all.return_value = [mock_feed_info]
        
        # Mock DB session for add_httpd_access_info
        with patch('bin.db.DB.session_ctx') as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__enter__.return_value = mock_session
            mock_session_ctx.return_value.__exit__.return_value = None
            
            # Mock the query results
            mock_session.query.return_value.all.return_value = [mock_feed_info]
            
            self.alm.add_httpd_access_info()

            rows = mock_session.query.return_value.all()
            assert rows is not None
            self.assertGreaterEqual(len(rows), 1)
            for row in rows:
                assert row is not None
                self.assertIsNotNone(row.feed_name)
                self.assertTrue(row.http_request)

    @patch('bin.access_log_manager.AccessLogManager.search_by_date')
    def test_load_all_httpd_access_info(self, mock_search_by_date) -> None:
        # Mock search_by_date response
        mock_search_by_date.return_value = (
            [("test_feed", datetime.now())],  # accessed_feed_list
            [("test_feed2", datetime.now())]  # viewed_feed_list
        )
        
        # Mock FeedInfo query results
        mock_feed_info = MagicMock()
        mock_feed_info.feed_name = "test_feed"
        mock_feed_info.access_date = datetime.now()
        
        self.mock_query.all.return_value = [mock_feed_info]
        
        # Mock DB session for load_all_httpd_access_info
        with patch('bin.db.DB.session_ctx') as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__enter__.return_value = mock_session
            mock_session_ctx.return_value.__exit__.return_value = None
            
            # Mock the query results
            mock_session.query.return_value.all.return_value = [mock_feed_info]
            
            self.alm.load_all_httpd_access_info(max_num_days=14)

            rows = mock_session.query.return_value.all()
            assert rows is not None
            self.assertGreaterEqual(len(rows), 1)
            for row in rows:
                assert row is not None
                self.assertIsNotNone(row.feed_name)
                self.assertIsNotNone(row.access_date)


    @patch('bin.access_log_manager.AccessLogManager.loki_search')
    def test_search_time_range_pagination(self, mock_loki_search) -> None:
        """limit 도달 시 페이지네이션으로 모든 로그를 가져오는지 확인"""
        local_tz = datetime.now().astimezone().tzinfo
        start_dt = datetime(2024, 1, 1, tzinfo=local_tz)
        end_dt = datetime(2024, 1, 1, 6, tzinfo=local_tz)
        # start_dt 이후의 타임스탬프 사용
        base_ts = int(start_dt.timestamp()) * 1_000_000_000 + 1_000_000_000

        # 첫 번째 호출: limit(5000)개 반환 → 페이지네이션 트리거
        page1_logs = [
            f'[01/Jan/2024:12:00:00 +0000] "GET /xml/feed{i}.xml HTTP/1.1" 200'
            for i in range(5000)
        ]
        # 두 번째 호출: limit 미만 반환 → 종료
        page2_logs = [
            '[01/Jan/2024:12:01:00 +0000] "GET /xml/extra_feed.xml HTTP/1.1" 200'
        ]
        mock_loki_search.side_effect = [
            (page1_logs, {}, base_ts + 5000_000_000_000),
            (page2_logs, {}, base_ts + 6000_000_000_000),
        ]

        accessed: list[tuple[datetime, str]] = []
        viewed: list[tuple[datetime, str]] = []

        self.alm._search_time_range(start_dt, end_dt, accessed, viewed)

        # 두 번 호출되었는지 확인 (페이지네이션)
        self.assertEqual(mock_loki_search.call_count, 2)
        # 두 번째 호출의 start가 첫 번째 last_ts + 1인지 확인
        second_call_params = mock_loki_search.call_args_list[1][0][0]
        self.assertEqual(second_call_params["start"], base_ts + 5000_000_000_000 + 1)
        # 모든 로그가 파싱되었는지 확인 (5000 + 1 = 5001)
        self.assertEqual(len(accessed), 5001)

    @patch('bin.access_log_manager.AccessLogManager.loki_search')
    def test_search_time_range_no_pagination_needed(self, mock_loki_search) -> None:
        """limit 미만일 때 한 번만 호출하는지 확인"""
        logs = [
            '[01/Jan/2024:12:00:00 +0000] "GET /xml/feed1.xml HTTP/1.1" 200'
        ]
        mock_loki_search.return_value = (logs, {}, 1700000000_000_000_000)

        accessed: list[tuple[datetime, str]] = []
        viewed: list[tuple[datetime, str]] = []
        local_tz = datetime.now().astimezone().tzinfo
        start_dt = datetime(2024, 1, 1, tzinfo=local_tz)
        end_dt = datetime(2024, 1, 1, 6, tzinfo=local_tz)

        self.alm._search_time_range(start_dt, end_dt, accessed, viewed)

        self.assertEqual(mock_loki_search.call_count, 1)
        self.assertEqual(len(accessed), 1)


if __name__ == "__main__":
    unittest.main()
