#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging.config
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestGetVerifySsl(unittest.TestCase):
    """_get_verify_ssl: lines 34-37, 41-42"""

    @patch("bin.access_log_manager.Env.get")
    def test_ca_bundle_file_exists(self, mock_env_get: MagicMock) -> None:
        from bin.access_log_manager import AccessLogManager

        with tempfile.NamedTemporaryFile(suffix=".pem") as f:

            def env_side_effect(key, default=""):
                if key == "FM_LOKI_CA_BUNDLE":
                    return f.name
                return default

            mock_env_get.side_effect = env_side_effect
            result = AccessLogManager._get_verify_ssl()
            self.assertEqual(result, f.name)

    @patch("bin.access_log_manager.Env.get")
    def test_ca_bundle_file_not_found(self, mock_env_get: MagicMock) -> None:
        from bin.access_log_manager import AccessLogManager

        def env_side_effect(key, default=""):
            if key == "FM_LOKI_CA_BUNDLE":
                return "/nonexistent/path/ca.pem"
            if key == "FM_LOKI_VERIFY_SSL":
                return "true"
            return default

        mock_env_get.side_effect = env_side_effect
        result = AccessLogManager._get_verify_ssl()
        # Falls through to check FM_LOKI_VERIFY_SSL, defaults to True
        self.assertTrue(result)

    @patch("bin.access_log_manager.Env.get")
    def test_verify_ssl_disabled(self, mock_env_get: MagicMock) -> None:
        from bin.access_log_manager import AccessLogManager

        def env_side_effect(key, default=""):
            if key == "FM_LOKI_CA_BUNDLE":
                return ""
            if key == "FM_LOKI_VERIFY_SSL":
                return "false"
            return default

        mock_env_get.side_effect = env_side_effect
        result = AccessLogManager._get_verify_ssl()
        self.assertFalse(result)


class TestLokiSearch(unittest.TestCase):
    """loki_search: lines 51-65"""

    @patch("bin.access_log_manager.Env.get")
    @patch("bin.access_log_manager.requests.get")
    def test_loki_search_success(self, mock_requests_get: MagicMock, mock_env_get: MagicMock) -> None:
        from bin.access_log_manager import AccessLogManager

        mock_env_get.return_value = "http://localhost:3100/loki/api/v1"

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.__bool__ = lambda self: True
        mock_response.json.return_value = {"status": "success", "data": {"result": [{"values": [[1700000000000000000, "log line 1"], [1700000001000000000, "log line 2"]]}], "stats": {"ingester": {"totalLinesSent": 2}}}}
        mock_requests_get.return_value = mock_response

        alm = AccessLogManager(loki_url="http://localhost:3100/loki/api/v1")
        logs, stats, last_ts = alm.loki_search({"query": "test"})

        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0], "log line 1")
        self.assertEqual(last_ts, 1700000001000000000)
        self.assertIn("ingester", stats)

    @patch("bin.access_log_manager.Env.get")
    @patch("bin.access_log_manager.requests.get")
    def test_loki_search_empty_data(self, mock_requests_get: MagicMock, mock_env_get: MagicMock) -> None:
        from bin.access_log_manager import AccessLogManager

        mock_env_get.return_value = "http://localhost:3100/loki/api/v1"

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.__bool__ = lambda self: True
        mock_response.json.return_value = {"status": "success", "data": {}}
        mock_requests_get.return_value = mock_response

        alm = AccessLogManager(loki_url="http://localhost:3100/loki/api/v1")
        logs, stats, last_ts = alm.loki_search({"query": "test"})

        self.assertEqual(len(logs), 0)
        self.assertIsNone(last_ts)


class TestSearchTimeRangePaginationStall(unittest.TestCase):
    """_search_time_range: lines 93-95, 115-116 (pagination stall)"""

    @patch("bin.access_log_manager.Env.get")
    @patch("bin.access_log_manager.AccessLogManager.loki_search")
    def test_pagination_stall(self, mock_loki_search: MagicMock, mock_env_get: MagicMock) -> None:
        from bin.access_log_manager import AccessLogManager

        mock_env_get.return_value = "http://localhost:3100/loki/api/v1"

        local_tz = datetime.now().astimezone().tzinfo
        start_dt = datetime(2024, 1, 1, tzinfo=local_tz)
        end_dt = datetime(2024, 1, 1, 6, tzinfo=local_tz)
        start_ns = int(start_dt.timestamp()) * 1_000_000_000

        # Return exactly LOKI_QUERY_LIMIT logs but with last_ts that doesn't advance
        page_logs = [f'[01/Jan/2024:12:00:00 +0000] "GET /xml/feed{i}.xml HTTP/1.1" 200' for i in range(5000)]
        # last_ts <= current_start_ns => stall detected, break
        mock_loki_search.return_value = (page_logs, {}, start_ns - 1)

        alm = AccessLogManager(loki_url="http://localhost:3100/loki/api/v1")
        accessed: list = []
        viewed: list = []

        alm._search_time_range(start_dt, end_dt, accessed, viewed)

        # Should only be called once because pagination stalled
        self.assertEqual(mock_loki_search.call_count, 1)

    @patch("bin.access_log_manager.Env.get")
    @patch("bin.access_log_manager.AccessLogManager.loki_search")
    def test_start_past_end(self, mock_loki_search: MagicMock, mock_env_get: MagicMock) -> None:
        from bin.access_log_manager import AccessLogManager

        mock_env_get.return_value = "http://localhost:3100/loki/api/v1"

        local_tz = datetime.now().astimezone().tzinfo
        start_dt = datetime(2024, 1, 2, tzinfo=local_tz)
        end_dt = datetime(2024, 1, 1, tzinfo=local_tz)

        alm = AccessLogManager(loki_url="http://localhost:3100/loki/api/v1")
        accessed: list = []
        viewed: list = []

        alm._search_time_range(start_dt, end_dt, accessed, viewed)

        # start >= end, so no search should happen
        mock_loki_search.assert_not_called()


class TestRemoveHttpdAccessInfo(unittest.TestCase):
    """remove_httpd_access_info: lines 132-138"""

    @patch("bin.access_log_manager.DB.session_ctx")
    def test_remove_access_info(self, mock_session_ctx: MagicMock) -> None:
        from bin.access_log_manager import AccessLogManager

        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        feed_dir_path = Path("/some/group/my_feed")
        AccessLogManager.remove_httpd_access_info(feed_dir_path)

        mock_session.query.assert_called_once()
        mock_session.query.return_value.filter_by.assert_called_once_with(feed_name="my_feed")


class TestAddHttpdAccessInfoNoExistingFeeds(unittest.TestCase):
    """add_httpd_access_info: lines 163, 173-176, 182-185 (new feed insert path)"""

    @patch("bin.access_log_manager.Env.get")
    @patch("bin.access_log_manager.AccessLogManager._add_httpd_access_info")
    @patch("bin.access_log_manager.DB.session_ctx")
    def test_add_new_feeds(self, mock_session_ctx: MagicMock, mock_add_info: MagicMock, mock_env_get: MagicMock) -> None:
        from bin.access_log_manager import AccessLogManager

        mock_env_get.return_value = "http://localhost:3100/loki/api/v1"

        now = datetime.now()
        mock_add_info.return_value = ({"new_feed": now}, {"new_viewed_feed": now})

        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        # Mock query for datediff => days=None => days=1
        mock_row = MagicMock()
        mock_row.days = None
        mock_session.query.return_value.first.return_value = mock_row
        # Mock filter_by().all() => empty list => s.add() path
        mock_session.query.return_value.filter_by.return_value.all.return_value = []

        alm = AccessLogManager(loki_url="http://localhost:3100/loki/api/v1")
        alm.add_httpd_access_info()

        # s.add should have been called for new feeds
        self.assertTrue(mock_session.add.called)


class TestLoadAllHttpdAccessInfoNewFeeds(unittest.TestCase):
    """load_all_httpd_access_info: lines 206-209, 216-219 (new feed insert path)"""

    @patch("bin.access_log_manager.Env.get")
    @patch("bin.access_log_manager.AccessLogManager._add_httpd_access_info")
    @patch("bin.access_log_manager.DB.session_ctx")
    def test_load_inserts_new_feeds(self, mock_session_ctx: MagicMock, mock_add_info: MagicMock, mock_env_get: MagicMock) -> None:
        from bin.access_log_manager import AccessLogManager

        mock_env_get.return_value = "http://localhost:3100/loki/api/v1"

        now = datetime.now()
        mock_add_info.return_value = ({"new_access_feed": now}, {"new_view_feed": now})

        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)
        # filter_by().all() => empty list => insert path
        mock_session.query.return_value.filter_by.return_value.all.return_value = []

        alm = AccessLogManager(loki_url="http://localhost:3100/loki/api/v1")
        alm.load_all_httpd_access_info(max_num_days=1)

        self.assertTrue(mock_session.add.called)


if __name__ == "__main__":
    unittest.main()
