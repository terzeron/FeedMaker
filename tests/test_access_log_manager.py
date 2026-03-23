#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bin.access_log_manager import AccessLogManager
from bin.models import FeedInfo


class TestRecordFeedAccess(unittest.TestCase):
    @patch("bin.access_log_manager.DB.session_ctx")
    def test_update_existing_feed(self, mock_session_ctx: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_feed = MagicMock()
        mock_feed.http_request = False
        mock_feed.access_date = None
        mock_session.query.return_value.filter_by.return_value.all.return_value = [mock_feed]

        AccessLogManager.record_feed_access("test_feed")

        self.assertTrue(mock_feed.http_request)
        self.assertIsNotNone(mock_feed.access_date)

    @patch("bin.access_log_manager.DB.session_ctx")
    def test_insert_new_feed(self, mock_session_ctx: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.query.return_value.filter_by.return_value.all.return_value = []

        AccessLogManager.record_feed_access("new_feed")

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        self.assertIsInstance(added, FeedInfo)
        self.assertEqual(added.feed_name, "new_feed")
        self.assertTrue(added.http_request)


class TestRecordItemView(unittest.TestCase):
    @patch("bin.access_log_manager.DB.session_ctx")
    def test_update_existing_feed(self, mock_session_ctx: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_feed = MagicMock()
        mock_feed.http_request = False
        mock_feed.view_date = None
        mock_session.query.return_value.filter_by.return_value.all.return_value = [mock_feed]

        AccessLogManager.record_item_view("test_feed")

        self.assertTrue(mock_feed.http_request)
        self.assertIsNotNone(mock_feed.view_date)

    @patch("bin.access_log_manager.DB.session_ctx")
    def test_insert_new_feed(self, mock_session_ctx: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.query.return_value.filter_by.return_value.all.return_value = []

        AccessLogManager.record_item_view("new_feed")

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        self.assertIsInstance(added, FeedInfo)
        self.assertEqual(added.feed_name, "new_feed")
        self.assertTrue(added.http_request)


class TestRemoveHttpdAccessInfo(unittest.TestCase):
    @patch("bin.access_log_manager.DB.session_ctx")
    def test_remove_access_info(self, mock_session_ctx: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        feed_dir_path = Path("/some/group/my_feed")
        AccessLogManager.remove_httpd_access_info(feed_dir_path)

        mock_session.query.assert_called_once()
        mock_session.query.return_value.filter_by.assert_called_once_with(feed_name="my_feed")


if __name__ == "__main__":
    unittest.main()
