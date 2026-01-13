#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Loki Integration Tests using testcontainers

This module tests the Loki log querying functionality with a real Loki container.
These tests verify that AccessLogManager can correctly query logs from Loki.

Note: These tests require Docker to be running.
"""

import logging.config
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from bin.access_log_manager import AccessLogManager
from tests.common_test_util import start_loki_container

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestLokiIntegration(unittest.TestCase):
    """Integration tests for Loki using real container"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        self.loki_container = None
        self.loki_url = None
        self.alm = None

    def tearDown(self) -> None:
        """Clean up test fixtures"""
        if self.alm:
            del self.alm

    def test_loki_container_startup(self) -> None:
        """Test that Loki container starts successfully"""
        with start_loki_container() as loki:
            loki_url = loki.get_url()
            LOGGER.info(f"Loki URL: {loki_url}")

            # Wait for Loki to be ready (Loki takes longer to start than MySQL)
            max_retries = 60
            loki_ready = False
            for i in range(max_retries):
                try:
                    response = requests.get(f"{loki_url}/ready", timeout=2)
                    if response.status_code == 200:
                        LOGGER.info("Loki is ready")
                        loki_ready = True
                        break
                except requests.exceptions.RequestException:
                    pass
                if i < max_retries - 1:
                    time.sleep(2)

            self.assertTrue(loki_ready, "Loki failed to become ready in time")

            # Verify Loki status
            response = requests.get(f"{loki_url}/ready", timeout=5)
            self.assertEqual(response.status_code, 200)

    def test_loki_push_and_query(self) -> None:
        """Test pushing logs to Loki and querying them back"""
        with start_loki_container() as loki:
            loki_url = loki.get_url()

            # Wait for Loki to be ready
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{loki_url}/ready", timeout=2)
                    if response.status_code == 200:
                        break
                except requests.exceptions.RequestException:
                    if i < max_retries - 1:
                        time.sleep(1)
                    else:
                        raise

            # Push test logs
            now_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
            test_logs = {
                "streams": [
                    {
                        "stream": {"namespace": "feedmaker", "job": "test"},
                        "values": [
                            [
                                str(now_ns),
                                '[01/Jan/2024:12:00:00 +0000] "GET /xml/test_feed.xml HTTP/1.1" 200',
                            ],
                            [
                                str(now_ns + 1_000_000),
                                '[01/Jan/2024:12:00:01 +0000] "GET /img/1x1.jpg?feed=test_feed.xml&item=123 HTTP/1.1" 200',
                            ],
                        ],
                    }
                ]
            }

            response = requests.post(
                f"{loki_url}/loki/api/v1/push",
                json=test_logs,
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            self.assertEqual(response.status_code, 204)

            # Wait for logs to be indexed
            time.sleep(2)

            # Query logs back
            start_ns = now_ns - 60_000_000_000  # 1 minute before
            end_ns = now_ns + 60_000_000_000  # 1 minute after

            params = {
                "query": '{namespace="feedmaker"}',
                "start": start_ns,
                "end": end_ns,
                "limit": 100,
            }

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range", params=params, timeout=10
            )
            self.assertEqual(response.status_code, 200)

            json_data = response.json()
            self.assertEqual(json_data.get("status"), "success")

            data = json_data.get("data", {})
            result = data.get("result", [])

            # Verify we got some results
            self.assertGreater(len(result), 0)

            # Verify log content
            found_logs = []
            for result_item in result:
                values = result_item.get("values", [])
                for _, log_line in values:
                    found_logs.append(log_line)

            self.assertGreater(len(found_logs), 0)
            LOGGER.info(f"Found {len(found_logs)} log entries")

    def test_access_log_manager_loki_search(self) -> None:
        """Test AccessLogManager.loki_search() with real Loki container"""
        with start_loki_container() as loki:
            loki_url = loki.get_url()

            # Wait for Loki to be ready
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{loki_url}/ready", timeout=2)
                    if response.status_code == 200:
                        break
                except requests.exceptions.RequestException:
                    if i < max_retries - 1:
                        time.sleep(1)
                    else:
                        raise

            # Create AccessLogManager with test Loki URL
            alm = AccessLogManager(loki_url=f"{loki_url}/loki/api/v1")

            # Push test logs
            now_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
            test_logs = {
                "streams": [
                    {
                        "stream": {"namespace": "feedmaker", "job": "nginx"},
                        "values": [
                            [
                                str(now_ns),
                                '[22/Dec/2025:12:00:00 +0000] "GET /xml/comic/naver/test_feed.xml HTTP/1.1" 200',
                            ],
                            [
                                str(now_ns + 1_000_000),
                                '[22/Dec/2025:12:00:01 +0000] "GET /xml/comic/naver/test_feed2.xml HTTP/1.1" 304',
                            ],
                            [
                                str(now_ns + 2_000_000),
                                '[22/Dec/2025:12:00:02 +0000] "GET /img/1x1.jpg?feed=test_feed.xml&item=item123 HTTP/1.1" 200',
                            ],
                        ],
                    }
                ]
            }

            response = requests.post(
                f"{loki_url}/loki/api/v1/push",
                json=test_logs,
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            self.assertEqual(response.status_code, 204)

            # Wait for logs to be indexed
            time.sleep(2)

            # Query using AccessLogManager
            start_ns = now_ns - 60_000_000_000
            end_ns = now_ns + 60_000_000_000

            params = {
                "query": '{namespace="feedmaker"}',
                "start": start_ns,
                "end": end_ns,
                "limit": 5000,
                "direction": "forward",
            }

            logs, stats = alm.loki_search(params)

            # Verify results
            self.assertIsNotNone(logs)
            self.assertGreater(len(logs), 0)
            self.assertIsNotNone(stats)

            LOGGER.info(f"AccessLogManager found {len(logs)} logs")

            # Verify log format
            for log in logs:
                self.assertIn("GET /", log)
                self.assertIn("HTTP/1.1", log)

            del alm

    def test_access_log_manager_search_by_date(self) -> None:
        """Test AccessLogManager.search_by_date() - the core business logic"""
        with start_loki_container() as loki:
            loki_url = loki.get_url()

            # Wait for Loki to be ready
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{loki_url}/ready", timeout=2)
                    if response.status_code == 200:
                        break
                except requests.exceptions.RequestException:
                    if i < max_retries - 1:
                        time.sleep(1)
                    else:
                        raise

            # Create AccessLogManager with test Loki URL
            alm = AccessLogManager(loki_url=f"{loki_url}/loki/api/v1")

            # Use local timezone (same as search_by_date uses)
            local_tz = datetime.now().astimezone().tzinfo
            today = datetime.now(local_tz).date()

            # Create test logs with proper nginx log format
            # Using current local time so search_by_date will find them
            now = datetime.now(local_tz)
            now_ns = int(now.timestamp() * 1_000_000_000)

            # Format: [dd/mmm/yyyy:hh:mm:ss +timezone]
            # Get timezone offset
            tz_offset = now.strftime("%z")
            tz_offset_formatted = f"{tz_offset[:3]}:{tz_offset[3:]}" if len(tz_offset) == 5 else tz_offset
            time_str = now.strftime(f"%d/%b/%Y:%H:%M:%S {tz_offset}")

            test_logs = {
                "streams": [
                    {
                        "stream": {"namespace": "feedmaker", "job": "nginx"},
                        "values": [
                            # Feed access logs (RSS XML requests)
                            [
                                str(now_ns),
                                f'[{time_str}] "GET /xml/comic/naver/test_feed1.xml HTTP/1.1" 200',
                            ],
                            [
                                str(now_ns + 1_000_000_000),  # +1 second
                                f'[{time_str}] "GET /xml/comic/daum/test_feed2.xml HTTP/1.1" 304',
                            ],
                            [
                                str(now_ns + 2_000_000_000),  # +2 seconds
                                f'[{time_str}] "GET /xml/news/test_feed3.xml HTTP/1.1" 200',
                            ],
                            # Item view logs (tracking pixel requests)
                            [
                                str(now_ns + 3_000_000_000),  # +3 seconds
                                f'[{time_str}] "GET /img/1x1.jpg?feed=comic/naver/test_feed1.xml&item=item001 HTTP/1.1" 200',
                            ],
                            [
                                str(now_ns + 4_000_000_000),  # +4 seconds
                                f'[{time_str}] "GET /img/1x1.jpg?feed=comic/daum/test_feed2.xml&item=item002 HTTP/1.1" 200',
                            ],
                            # Non-matching logs (should be ignored)
                            [
                                str(now_ns + 5_000_000_000),  # +5 seconds
                                f'[{time_str}] "GET /static/style.css HTTP/1.1" 200',
                            ],
                            [
                                str(now_ns + 6_000_000_000),  # +6 seconds
                                f'[{time_str}] "GET /xml/test.xml HTTP/1.1" 404',  # 404 should be ignored
                            ],
                        ],
                    }
                ]
            }

            response = requests.post(
                f"{loki_url}/loki/api/v1/push",
                json=test_logs,
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            self.assertEqual(response.status_code, 204)

            # Wait for logs to be indexed
            time.sleep(3)

            # Test search_by_date - this is the main business logic
            accessed_feed_list, viewed_feed_list = alm.search_by_date(today)

            # Verify accessed feeds (RSS XML requests)
            LOGGER.info(f"Found {len(accessed_feed_list)} accessed feeds")
            LOGGER.info(f"Accessed feeds: {accessed_feed_list}")

            self.assertGreater(len(accessed_feed_list), 0, "Should find at least one accessed feed")

            # Extract feed names from accessed_feed_list
            accessed_feed_names = [feed_name for _, feed_name in accessed_feed_list]

            # Verify expected feeds are in the results
            self.assertIn("comic/naver/test_feed1", accessed_feed_names)
            self.assertIn("comic/daum/test_feed2", accessed_feed_names)
            self.assertIn("news/test_feed3", accessed_feed_names)

            # Verify viewed feeds (tracking pixel requests)
            LOGGER.info(f"Found {len(viewed_feed_list)} viewed feeds")
            LOGGER.info(f"Viewed feeds: {viewed_feed_list}")

            self.assertGreater(len(viewed_feed_list), 0, "Should find at least one viewed feed")

            # Extract feed names from viewed_feed_list
            viewed_feed_names = [feed_name for _, feed_name in viewed_feed_list]

            # Verify expected feeds are in the results
            self.assertIn("comic/naver/test_feed1", viewed_feed_names)
            self.assertIn("comic/daum/test_feed2", viewed_feed_names)

            # Verify timestamps are datetime objects
            for dt, _ in accessed_feed_list:
                self.assertIsInstance(dt, datetime)
                self.assertIsNotNone(dt.tzinfo, "Datetime should have timezone info")

            for dt, _ in viewed_feed_list:
                self.assertIsInstance(dt, datetime)
                self.assertIsNotNone(dt.tzinfo, "Datetime should have timezone info")

            del alm


if __name__ == "__main__":
    unittest.main()
