#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import unittest
import logging.config
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, PropertyMock

from bin.feed_manager import FeedManager
from bin.models import FeedInfo
from bin.feed_maker_util import Config


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class FeedManagerTestBase(unittest.TestCase):
    """Base class with common DB mock setup."""

    def setUp(self) -> None:
        self.mock_session = MagicMock()
        self.mock_query = MagicMock()
        self.mock_session.query.return_value = self.mock_query
        self.mock_query.filter_by.return_value = self.mock_query
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.where.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query

        self.patcher_session = patch("bin.feed_manager.DB.session_ctx")
        self.mock_session_ctx = self.patcher_session.start()
        self.mock_session_ctx.return_value.__enter__ = MagicMock(return_value=self.mock_session)
        self.mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

    def tearDown(self) -> None:
        self.patcher_session.stop()

    def _make_feed_row(self, **kwargs) -> MagicMock:
        row = MagicMock(spec=FeedInfo)
        defaults = {
            "feed_name": "test_feed",
            "feed_title": "Test Feed",
            "group_name": "test_group",
            "is_active": True,
            "config": "",
            "config_modify_date": None,
            "url_list_count": 0,
            "is_completed": False,
            "current_index": 0,
            "total_item_count": 0,
            "unit_size_per_day": 0.0,
            "progress_ratio": 0.0,
            "due_date": None,
            "collect_date": None,
            "feedmaker": False,
            "rss_update_date": None,
            "public_html": False,
            "public_feed_file_path": "",
            "file_size": 0,
            "num_items": 0,
            "upload_date": None,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(row, k, v)
        return row


class TestGetFeedNameListUrlCountMap(FeedManagerTestBase):
    def test_returns_map_with_rows(self) -> None:
        row1 = self._make_feed_row(feed_name="feed_a", feed_title="Feed A", group_name="grp", url_list_count=5)
        row2 = self._make_feed_row(feed_name="feed_b", feed_title="Feed B", group_name="grp2", url_list_count=3)
        self.mock_query.all.return_value = [row1, row2]

        result = FeedManager.get_feed_name_list_url_count_map()

        self.assertEqual(len(result), 2)
        self.assertIn("feed_a", result)
        self.assertEqual(result["feed_a"]["count"], 5)
        self.assertEqual(result["feed_a"]["feed_title"], "Feed A")
        self.assertEqual(result["feed_a"]["group_name"], "grp")
        self.assertIn("feed_b", result)
        self.assertEqual(result["feed_b"]["count"], 3)

    def test_returns_empty_when_no_rows(self) -> None:
        self.mock_query.all.return_value = []
        result = FeedManager.get_feed_name_list_url_count_map()
        self.assertEqual(result, {})


class TestGetElementNameCountMap(FeedManagerTestBase):
    def test_returns_map_with_rows(self) -> None:
        row1 = MagicMock()
        row1.element_name = "c.list_url_list"
        row1.count = 10
        row2 = MagicMock()
        row2.element_name = "r.title"
        row2.count = 5
        self.mock_query.all.return_value = [row1, row2]

        result = FeedManager.get_element_name_count_map()

        self.assertEqual(len(result), 2)
        self.assertIn("c.list_url_list", result)
        self.assertEqual(result["c.list_url_list"]["count"], 10)
        self.assertIn("r.title", result)

    def test_returns_empty_when_no_rows(self) -> None:
        self.mock_query.all.return_value = []
        result = FeedManager.get_element_name_count_map()
        self.assertEqual(result, {})


class TestRemoveConfigInfo(FeedManagerTestBase):
    def test_remove_without_file_removal(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.name = "my_feed"
        feed_dir_path.__truediv__ = MagicMock()

        FeedManager.remove_config_info(feed_dir_path, do_remove_file=False)

        self.mock_query.update.assert_called_once()
        update_args = self.mock_query.update.call_args[0][0]
        self.assertEqual(update_args[FeedInfo.is_active], False)
        self.assertEqual(update_args[FeedInfo.config], "")
        self.assertIsNone(update_args[FeedInfo.config_modify_date])
        # unlink should not be called
        feed_dir_path.__truediv__.return_value.unlink.assert_not_called()

    def test_remove_with_file_removal(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.name = "my_feed"
        conf_file = MagicMock()
        feed_dir_path.__truediv__ = MagicMock(return_value=conf_file)

        FeedManager.remove_config_info(feed_dir_path, do_remove_file=True)

        conf_file.unlink.assert_called_once_with(missing_ok=True)
        self.mock_query.update.assert_called_once()


class TestAddConfigInfo(FeedManagerTestBase):
    def test_not_a_dir_returns_early(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = False

        FeedManager._add_config_info(self.mock_session, feed_dir_path)

        self.mock_session.query.assert_not_called()
        self.mock_session.add.assert_not_called()

    def test_skips_git_dir(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = ".git"
        feed_dir_path.parent.name = "group"

        FeedManager._add_config_info(self.mock_session, feed_dir_path)

        self.mock_session.flush.assert_not_called()

    def test_skips_mypy_cache_group(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "some_feed"
        feed_dir_path.parent.name = ".mypy_cache"

        FeedManager._add_config_info(self.mock_session, feed_dir_path)

        self.mock_session.flush.assert_not_called()

    def test_skips_test_dir(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "test"
        feed_dir_path.parent.name = "group"

        FeedManager._add_config_info(self.mock_session, feed_dir_path)

        self.mock_session.flush.assert_not_called()

    def test_disabled_feed_with_underscore_prefix(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "_disabled_feed"
        feed_dir_path.parent.name = "group"

        self.mock_query.first.return_value = None

        FeedManager._add_config_info(self.mock_session, feed_dir_path)

        self.mock_session.add.assert_called_once()
        added = self.mock_session.add.call_args[0][0]
        self.assertEqual(added.feed_name, "disabled_feed")
        self.assertFalse(added.is_active)
        self.mock_session.flush.assert_called_once()

    def test_disabled_group_with_underscore_prefix(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "feed"
        feed_dir_path.parent.name = "_disabled_group"

        self.mock_query.first.return_value = None

        FeedManager._add_config_info(self.mock_session, feed_dir_path)

        self.mock_session.add.assert_called_once()
        added = self.mock_session.add.call_args[0][0]
        self.assertEqual(added.group_name, "disabled_group")
        self.assertFalse(added.is_active)

    def test_active_feed_reads_config_and_updates_existing(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "my_feed"
        feed_dir_path.parent.name = "my_group"

        conf_file = MagicMock()
        conf_file.is_file.return_value = True

        config_data = {"configuration": {"rss": {"title": "My Title::suffix", "link": "http://example.com"}, "collection": {"list_url_list": ["url1", "url2"], "is_completed": True, "unit_size_per_day": 5}, "extraction": {"element_id": "content"}}}
        conf_file.open.return_value.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=json.dumps(config_data))))
        conf_file.open.return_value.__exit__ = MagicMock(return_value=None)

        # patch json.load to return config_data
        def truediv_side_effect(other):
            if other == Config.DEFAULT_CONF_FILE:
                return conf_file
            return MagicMock()

        feed_dir_path.__truediv__ = MagicMock(side_effect=truediv_side_effect)

        stat_result = MagicMock()
        stat_result.st_mtime = 1700000000.0
        feed_dir_path.stat.return_value = stat_result

        existing_feed = self._make_feed_row(feed_name="my_feed", group_name="my_group")
        self.mock_query.first.return_value = existing_feed

        with patch("json.load", return_value=config_data):
            FeedManager._add_config_info(self.mock_session, feed_dir_path)

        # Should update existing, not add new
        self.mock_session.add.assert_not_called()
        self.assertEqual(existing_feed.feed_title, "My Title")
        self.assertTrue(existing_feed.is_active)
        self.assertEqual(existing_feed.url_list_count, 2)
        self.assertTrue(existing_feed.is_completed)
        self.assertEqual(existing_feed.unit_size_per_day, 5)
        self.mock_session.flush.assert_called_once()

    def test_active_feed_adds_new_when_not_existing(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "new_feed"
        feed_dir_path.parent.name = "group"

        conf_file = MagicMock()
        conf_file.is_file.return_value = True

        config_data = {"configuration": {"rss": {"title": "New Feed"}, "collection": {"list_url_list": ["u1"]}, "extraction": {}}}

        def truediv_side_effect(other):
            if other == Config.DEFAULT_CONF_FILE:
                return conf_file
            return MagicMock()

        feed_dir_path.__truediv__ = MagicMock(side_effect=truediv_side_effect)

        stat_result = MagicMock()
        stat_result.st_mtime = 1700000000.0
        feed_dir_path.stat.return_value = stat_result

        self.mock_query.first.return_value = None

        with patch("json.load", return_value=config_data):
            FeedManager._add_config_info(self.mock_session, feed_dir_path)

        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()

    def test_active_feed_no_conf_file(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "feed_no_conf"
        feed_dir_path.parent.name = "group"

        conf_file = MagicMock()
        conf_file.is_file.return_value = False

        def truediv_side_effect(other):
            if other == Config.DEFAULT_CONF_FILE:
                return conf_file
            return MagicMock()

        feed_dir_path.__truediv__ = MagicMock(side_effect=truediv_side_effect)

        self.mock_query.first.return_value = None

        FeedManager._add_config_info(self.mock_session, feed_dir_path)

        # Should still add a record with empty config
        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()

    def test_element_name_count_map_accumulates(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "feed"
        feed_dir_path.parent.name = "group"

        conf_file = MagicMock()
        conf_file.is_file.return_value = True

        config_data = {"configuration": {"rss": {"title": "T", "link": "http://x.com"}, "collection": {"list_url_list": ["u"]}, "extraction": {"element_id": "c"}}}

        def truediv_side_effect(other):
            if other == Config.DEFAULT_CONF_FILE:
                return conf_file
            return MagicMock()

        feed_dir_path.__truediv__ = MagicMock(side_effect=truediv_side_effect)
        stat_result = MagicMock()
        stat_result.st_mtime = 1700000000.0
        feed_dir_path.stat.return_value = stat_result

        self.mock_query.first.return_value = None

        element_map: dict[str, int] = {}
        with patch("json.load", return_value=config_data):
            FeedManager._add_config_info(self.mock_session, feed_dir_path, element_map)

        # collection has 'list_url_list' -> 'c.list_url_list'
        # rss has 'title', 'link' -> 'r.title', 'r.link'
        # extraction has 'element_id' -> 'e.element_id'
        self.assertIn("c.list_url_list", element_map)
        self.assertIn("r.title", element_map)
        self.assertIn("r.link", element_map)
        self.assertIn("e.element_id", element_map)


class TestAddConfigInfoWrapper(FeedManagerTestBase):
    def test_add_config_info_calls_internal(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.name = "feed"

        with patch.object(FeedManager, "_add_config_info") as mock_add, patch.object(FeedManager, "_add_element_info") as mock_elem:
            FeedManager.add_config_info(feed_dir_path)
            mock_add.assert_called_once()
            mock_elem.assert_called_once()


class TestAddElementInfo(FeedManagerTestBase):
    def test_accumulates_to_total(self) -> None:
        element_map = {"c.url": 3, "r.title": 1}
        total_map: dict[str, int] = {"c.url": 5}

        FeedManager._add_element_info(element_map, total_map)

        self.assertEqual(total_map["c.url"], 8)
        self.assertEqual(total_map["r.title"], 1)

    def test_no_total_map_does_nothing(self) -> None:
        element_map = {"c.url": 3}
        # Should not raise
        FeedManager._add_element_info(element_map, None)

    def test_empty_element_map(self) -> None:
        total_map: dict[str, int] = {"c.url": 5}
        FeedManager._add_element_info({}, total_map)
        self.assertEqual(total_map, {"c.url": 5})


class TestLoadAllConfigFiles(FeedManagerTestBase):
    @patch.object(FeedManager, "_add_config_info")
    @patch.object(FeedManager, "_add_element_info")
    def test_iterates_directories(self, mock_elem: MagicMock, mock_add: MagicMock) -> None:
        group_dir = MagicMock()
        group_dir.is_dir.return_value = True
        feed_dir1 = MagicMock()
        feed_dir1.is_dir.return_value = True
        feed_dir2 = MagicMock()
        feed_dir2.is_dir.return_value = False
        group_dir.iterdir.return_value = [feed_dir1, feed_dir2]

        with patch.object(FeedManager, "work_dir_path", new_callable=PropertyMock) as mock_work:
            mock_path = MagicMock()
            mock_path.iterdir.return_value = [group_dir]
            mock_work.return_value = mock_path
            fm = FeedManager()
            fm.work_dir_path = mock_path

            fm.load_all_config_files(max_num_feeds=10)

        # Only feed_dir1 (is_dir=True) should trigger _add_config_info
        mock_add.assert_called_once()

    @patch.object(FeedManager, "_add_config_info")
    @patch.object(FeedManager, "_add_element_info")
    def test_skips_non_dir_groups(self, mock_elem: MagicMock, mock_add: MagicMock) -> None:
        non_dir = MagicMock()
        non_dir.is_dir.return_value = False

        with patch.object(FeedManager, "work_dir_path", new_callable=PropertyMock):
            fm = FeedManager()
            fm.work_dir_path = MagicMock()
            fm.work_dir_path.iterdir.return_value = [non_dir]

            fm.load_all_config_files(max_num_feeds=10)

        mock_add.assert_not_called()


class TestRemoveRssInfo(FeedManagerTestBase):
    def test_remove_without_file(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.name = "my_feed"

        FeedManager.remove_rss_info(feed_dir_path, do_remove_file=False)

        self.mock_query.update.assert_called_once()
        update_args = self.mock_query.update.call_args[0][0]
        self.assertEqual(update_args[FeedInfo.feedmaker], False)
        self.assertIsNone(update_args[FeedInfo.rss_update_date])

    def test_remove_with_file(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.name = "my_feed"
        rss_file = MagicMock()
        feed_dir_path.__truediv__ = MagicMock(return_value=rss_file)

        FeedManager.remove_rss_info(feed_dir_path, do_remove_file=True)

        rss_file.unlink.assert_called_once_with(missing_ok=True)


class TestAddRssInfo(FeedManagerTestBase):
    def test_not_a_dir_returns_early(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = False

        FeedManager._add_rss_info(self.mock_session, feed_dir_path)

        self.mock_session.query.assert_not_called()

    def test_skips_git_dir(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = ".git"
        feed_dir_path.parent.name = "group"

        FeedManager._add_rss_info(self.mock_session, feed_dir_path)

        self.mock_session.query.assert_not_called()

    def test_disabled_feed_strips_prefix(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "_disabled"
        feed_dir_path.parent.name = "group"

        self.mock_query.all.return_value = []

        FeedManager._add_rss_info(self.mock_session, feed_dir_path)

        self.mock_session.add.assert_called_once()
        added = self.mock_session.add.call_args[0][0]
        self.assertEqual(added.feed_name, "disabled")
        self.assertFalse(added.is_active)

    def test_disabled_group_strips_prefix(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "feed"
        feed_dir_path.parent.name = "_grp"

        self.mock_query.all.return_value = []

        FeedManager._add_rss_info(self.mock_session, feed_dir_path)

        added = self.mock_session.add.call_args[0][0]
        self.assertEqual(added.group_name, "grp")
        self.assertFalse(added.is_active)

    def test_active_feed_with_rss_file_updates_existing(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "my_feed"
        feed_dir_path.parent.name = "group"

        rss_file = MagicMock()
        rss_file.is_file.return_value = True
        stat_result = MagicMock()
        stat_result.st_mtime = 1700000000.0
        rss_file.stat.return_value = stat_result

        feed_dir_path.__truediv__ = MagicMock(return_value=rss_file)

        existing = self._make_feed_row(feed_name="my_feed", group_name="group")
        self.mock_query.all.return_value = [existing]

        FeedManager._add_rss_info(self.mock_session, feed_dir_path)

        self.assertTrue(existing.feedmaker)
        self.assertIsNotNone(existing.rss_update_date)
        self.assertTrue(existing.is_active)
        self.mock_session.add.assert_not_called()

    def test_active_feed_without_rss_file(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "my_feed"
        feed_dir_path.parent.name = "group"

        rss_file = MagicMock()
        rss_file.is_file.return_value = False
        feed_dir_path.__truediv__ = MagicMock(return_value=rss_file)

        self.mock_query.all.return_value = []

        FeedManager._add_rss_info(self.mock_session, feed_dir_path)

        self.mock_session.add.assert_called_once()
        added = self.mock_session.add.call_args[0][0]
        self.assertFalse(added.feedmaker)
        self.assertIsNone(added.rss_update_date)

    def test_active_feed_adds_new(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "new_feed"
        feed_dir_path.parent.name = "group"

        rss_file = MagicMock()
        rss_file.is_file.return_value = True
        stat_result = MagicMock()
        stat_result.st_mtime = 1700000000.0
        rss_file.stat.return_value = stat_result
        feed_dir_path.__truediv__ = MagicMock(return_value=rss_file)

        self.mock_query.all.return_value = []

        FeedManager._add_rss_info(self.mock_session, feed_dir_path)

        self.mock_session.add.assert_called_once()


class TestLoadAllRssFiles(FeedManagerTestBase):
    @patch.object(FeedManager, "_add_rss_info")
    def test_iterates_feed_dirs(self, mock_add: MagicMock) -> None:
        group_dir = MagicMock()
        group_dir.is_dir.return_value = True
        feed_dir = MagicMock()
        feed_dir.is_dir.return_value = True
        file_in_group = MagicMock()
        file_in_group.is_dir.return_value = False
        group_dir.iterdir.return_value = [feed_dir, file_in_group]

        fm = FeedManager()
        fm.work_dir_path = MagicMock()
        fm.work_dir_path.iterdir.return_value = [group_dir]

        fm.load_all_rss_files(max_num_feeds=10)

        mock_add.assert_called_once()

    @patch.object(FeedManager, "_add_rss_info")
    def test_skips_non_dir_groups(self, mock_add: MagicMock) -> None:
        non_dir = MagicMock()
        non_dir.is_dir.return_value = False

        fm = FeedManager()
        fm.work_dir_path = MagicMock()
        fm.work_dir_path.iterdir.return_value = [non_dir]

        fm.load_all_rss_files(max_num_feeds=10)

        mock_add.assert_not_called()


class TestGetFeedNamePublicFeedInfoMap(FeedManagerTestBase):
    def test_returns_map_with_rows(self) -> None:
        row = self._make_feed_row(feed_name="pub_feed", feed_title="Public", group_name="g", file_size=1024, num_items=5, upload_date=datetime(2024, 1, 1, tzinfo=timezone.utc))
        self.mock_query.all.return_value = [row]

        result = FeedManager.get_feed_name_public_feed_info_map()

        self.assertEqual(len(result), 1)
        self.assertIn("pub_feed", result)
        self.assertEqual(result["pub_feed"]["file_size"], 1024)
        self.assertEqual(result["pub_feed"]["num_items"], 5)

    def test_returns_empty_when_no_rows(self) -> None:
        self.mock_query.all.return_value = []
        result = FeedManager.get_feed_name_public_feed_info_map()
        self.assertEqual(result, {})


class TestRemovePublicFeed(FeedManagerTestBase):
    def test_remove_without_file(self) -> None:
        path = MagicMock(spec=Path)
        path.stem = "my_feed"

        FeedManager.remove_public_feed(path, do_remove_file=False)

        self.mock_query.update.assert_called_once()
        path.unlink.assert_not_called()

    def test_remove_with_file(self) -> None:
        path = MagicMock(spec=Path)
        path.stem = "my_feed"

        FeedManager.remove_public_feed(path, do_remove_file=True)

        path.unlink.assert_called_once_with(missing_ok=True)
        self.mock_query.update.assert_called_once()

    def test_remove_public_feed_by_feed_name(self) -> None:
        fm = FeedManager()
        fm.public_feed_dir_path = MagicMock()
        expected_path = MagicMock()
        fm.public_feed_dir_path.__truediv__ = MagicMock(return_value=expected_path)
        expected_path.stem = "my_feed"

        with patch.object(FeedManager, "remove_public_feed") as mock_remove:
            fm.remove_public_feed_by_feed_name("my_feed", do_remove_file=True)
            mock_remove.assert_called_once()


class TestAddPublicFeed(FeedManagerTestBase):
    def test_not_a_file_returns_zero(self) -> None:
        path = MagicMock(spec=Path)
        path.is_file.return_value = False

        result = FeedManager._add_public_feed(self.mock_session, path)

        self.assertEqual(result, 0)
        self.mock_session.query.assert_not_called()

    def test_reads_file_and_updates_existing(self) -> None:
        path = MagicMock(spec=Path)
        path.is_file.return_value = True
        path.stem = "my_feed"
        stat_result = MagicMock()
        stat_result.st_size = 2048
        stat_result.st_mtime = 1700000000.0
        path.stat.return_value = stat_result

        file_content = "<rss><item>first</item><item>second</item></rss>"
        path.open.return_value.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=file_content)))
        path.open.return_value.__exit__ = MagicMock(return_value=None)

        existing = self._make_feed_row(feed_name="my_feed")
        self.mock_query.all.return_value = [existing]

        result = FeedManager._add_public_feed(self.mock_session, path)

        self.assertEqual(result, 2)
        self.assertTrue(existing.public_html)
        self.assertEqual(existing.file_size, 2048)
        self.assertEqual(existing.num_items, 2)

    def test_adds_new_when_not_existing(self) -> None:
        path = MagicMock(spec=Path)
        path.is_file.return_value = True
        path.stem = "new_feed"
        stat_result = MagicMock()
        stat_result.st_size = 512
        stat_result.st_mtime = 1700000000.0
        path.stat.return_value = stat_result

        file_content = "<rss><item>one</item></rss>"
        path.open.return_value.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=file_content)))
        path.open.return_value.__exit__ = MagicMock(return_value=None)

        self.mock_query.all.return_value = []

        result = FeedManager._add_public_feed(self.mock_session, path)

        self.assertEqual(result, 1)
        self.mock_session.add.assert_called_once()


class TestLoadAllPublicFeedFiles(FeedManagerTestBase):
    @patch.object(FeedManager, "_add_public_feed", return_value=3)
    def test_iterates_glob(self, mock_add: MagicMock) -> None:
        file1 = MagicMock()
        file2 = MagicMock()

        fm = FeedManager()
        fm.public_feed_dir_path = MagicMock()
        fm.public_feed_dir_path.glob.return_value = [file1, file2]

        fm.load_all_public_feed_files(max_num_public_feeds=10)

        self.assertEqual(mock_add.call_count, 2)


class TestGetFeedNameProgressInfoMap(FeedManagerTestBase):
    def test_returns_map_with_rows(self) -> None:
        row = self._make_feed_row(feed_name="prog_feed", feed_title="Progress", group_name="g", is_completed=True, current_index=10, total_item_count=100, unit_size_per_day=5.0, progress_ratio=14.0, due_date=datetime(2025, 1, 1, tzinfo=timezone.utc))
        self.mock_query.all.return_value = [row]

        result = FeedManager.get_feed_name_progress_info_map()

        self.assertEqual(len(result), 1)
        self.assertIn("prog_feed", result)
        self.assertEqual(result["prog_feed"]["current_index"], 10)
        self.assertEqual(result["prog_feed"]["total_item_count"], 100)
        self.assertEqual(result["prog_feed"]["unit_size_per_day"], 5.0)

    def test_handles_none_values(self) -> None:
        row = self._make_feed_row(feed_name="f", feed_title="T", group_name="g", unit_size_per_day=None, progress_ratio=None, current_index=0, total_item_count=0, due_date=None)
        self.mock_query.all.return_value = [row]

        result = FeedManager.get_feed_name_progress_info_map()

        self.assertEqual(result["f"]["unit_size_per_day"], 0.0)
        self.assertEqual(result["f"]["progress_ratio"], 0.0)

    def test_returns_empty_when_no_rows(self) -> None:
        self.mock_query.all.return_value = []
        result = FeedManager.get_feed_name_progress_info_map()
        self.assertEqual(result, {})


class TestRemoveProgressInfo(FeedManagerTestBase):
    def test_remove_without_file(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.name = "my_feed"

        FeedManager.remove_progress_info(feed_dir_path, do_remove_file=False)

        self.mock_query.update.assert_called_once()
        update_args = self.mock_query.update.call_args[0][0]
        self.assertFalse(update_args[FeedInfo.is_completed])
        self.assertEqual(update_args[FeedInfo.current_index], 0)

    def test_remove_with_file(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.name = "my_feed"
        start_idx_file = MagicMock()
        feed_dir_path.__truediv__ = MagicMock(return_value=start_idx_file)

        FeedManager.remove_progress_info(feed_dir_path, do_remove_file=True)

        start_idx_file.unlink.assert_called_once_with(missing_ok=True)


class TestAddProgressInfo(FeedManagerTestBase):
    def test_not_a_dir_returns_zero(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = False

        result = FeedManager._add_progress_info(self.mock_session, feed_dir_path)

        self.assertEqual(result, 0)

    def test_skips_git_dir(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = ".git"
        feed_dir_path.parent.name = "group"

        conf_file = MagicMock()
        conf_file.is_file.return_value = False
        feed_dir_path.__truediv__ = MagicMock(return_value=conf_file)

        result = FeedManager._add_progress_info(self.mock_session, feed_dir_path)

        self.assertEqual(result, 0)

    def test_disabled_feed_strips_prefix(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "_disabled"
        feed_dir_path.parent.name = "group"

        conf_file = MagicMock()
        conf_file.is_file.return_value = False
        feed_dir_path.__truediv__ = MagicMock(return_value=conf_file)

        self.mock_query.first.return_value = None
        self.mock_query.all.return_value = []

        result = FeedManager._add_progress_info(self.mock_session, feed_dir_path)

        self.assertEqual(result, 1)
        self.mock_session.add.assert_called_once()
        added = self.mock_session.add.call_args[0][0]
        self.assertEqual(added.feed_name, "disabled")
        self.assertFalse(added.is_active)

    def test_disabled_group_strips_prefix(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "feed"
        feed_dir_path.parent.name = "_grp"

        conf_file = MagicMock()
        conf_file.is_file.return_value = False
        feed_dir_path.__truediv__ = MagicMock(return_value=conf_file)

        self.mock_query.first.return_value = None
        self.mock_query.all.return_value = []

        result = FeedManager._add_progress_info(self.mock_session, feed_dir_path)

        self.assertEqual(result, 1)
        added = self.mock_session.add.call_args[0][0]
        self.assertEqual(added.group_name, "grp")

    def test_active_completed_feed_with_progress(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "my_feed"
        feed_dir_path.parent.name = "group"

        # Config file with is_completed
        conf_data = {"configuration": {"collection": {"is_completed": True}}}

        conf_file = MagicMock()
        conf_file.is_file.return_value = True
        conf_file.open.return_value.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=json.dumps(conf_data))))
        conf_file.open.return_value.__exit__ = MagicMock(return_value=None)

        # start_idx.txt
        start_idx_file = MagicMock()
        start_idx_file.is_file.return_value = True
        start_idx_file.open.return_value.__enter__ = MagicMock(return_value=MagicMock(readline=MagicMock(return_value="100\t2024-01-01")))
        start_idx_file.open.return_value.__exit__ = MagicMock(return_value=None)

        # newlist dir with files
        newlist_dir = MagicMock()
        newlist_dir.is_dir.return_value = True
        list_file = MagicMock()
        list_file.suffix = ".txt"
        stat_result = MagicMock()
        stat_result.st_mtime = 1700000000.0
        list_file.stat.return_value = stat_result
        list_file.open.return_value.__enter__ = MagicMock(return_value=iter(["url1\ttitle1\n", "url2\ttitle2\n", "url3\ttitle3\n"]))
        list_file.open.return_value.__exit__ = MagicMock(return_value=None)
        newlist_dir.iterdir.return_value = [list_file]

        def truediv_side_effect(other):
            if other == Config.DEFAULT_CONF_FILE:
                return conf_file
            if other == "start_idx.txt":
                return start_idx_file
            if other == "newlist":
                return newlist_dir
            return MagicMock()

        feed_dir_path.__truediv__ = MagicMock(side_effect=truediv_side_effect)

        # DB row with is_completed and unit_size_per_day
        db_row = self._make_feed_row(feed_name="my_feed", is_completed=True, unit_size_per_day=2.0)
        self.mock_query.first.return_value = db_row
        self.mock_query.all.return_value = []

        with patch("json.load", return_value=conf_data):
            result = FeedManager._add_progress_info(self.mock_session, feed_dir_path)

        self.assertEqual(result, 1)
        self.mock_session.add.assert_called_once()

    def test_active_feed_no_completed_row(self) -> None:
        """Active feed where DB has no is_completed row."""
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "my_feed"
        feed_dir_path.parent.name = "group"

        conf_file = MagicMock()
        conf_file.is_file.return_value = False
        feed_dir_path.__truediv__ = MagicMock(return_value=conf_file)

        self.mock_query.first.return_value = None
        self.mock_query.all.return_value = []

        result = FeedManager._add_progress_info(self.mock_session, feed_dir_path)

        self.assertEqual(result, 1)
        self.mock_session.add.assert_called_once()

    def test_updates_existing_feed(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "my_feed"
        feed_dir_path.parent.name = "group"

        conf_file = MagicMock()
        conf_file.is_file.return_value = False
        feed_dir_path.__truediv__ = MagicMock(return_value=conf_file)

        self.mock_query.first.return_value = None
        existing = self._make_feed_row(feed_name="my_feed", group_name="group")
        self.mock_query.all.return_value = [existing]

        result = FeedManager._add_progress_info(self.mock_session, feed_dir_path)

        self.assertEqual(result, 1)
        self.mock_session.add.assert_not_called()
        self.assertFalse(existing.is_completed)

    def test_reads_config_is_completed(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.is_dir.return_value = True
        feed_dir_path.name = "feed"
        feed_dir_path.parent.name = "group"

        conf_data = {"configuration": {"collection": {"is_completed": True}}}
        conf_file = MagicMock()
        conf_file.is_file.return_value = True
        conf_file.open.return_value.__enter__ = MagicMock(return_value=MagicMock())
        conf_file.open.return_value.__exit__ = MagicMock(return_value=None)

        start_idx = MagicMock()
        start_idx.is_file.return_value = False

        newlist_dir = MagicMock()
        newlist_dir.is_dir.return_value = False

        def truediv_side_effect(other):
            if other == Config.DEFAULT_CONF_FILE:
                return conf_file
            if other == "start_idx.txt":
                return start_idx
            if other == "newlist":
                return newlist_dir
            return MagicMock()

        feed_dir_path.__truediv__ = MagicMock(side_effect=truediv_side_effect)

        db_row = self._make_feed_row(feed_name="feed", is_completed=True, unit_size_per_day=1.0)
        self.mock_query.first.return_value = db_row
        self.mock_query.all.return_value = []

        with patch("json.load", return_value=conf_data):
            result = FeedManager._add_progress_info(self.mock_session, feed_dir_path)

        self.assertEqual(result, 1)


class TestLoadAllProgressInfoFromFiles(FeedManagerTestBase):
    @patch.object(FeedManager, "_add_progress_info", return_value=1)
    def test_iterates_directories(self, mock_add: MagicMock) -> None:
        group_dir = MagicMock()
        group_dir.is_dir.return_value = True
        feed_dir = MagicMock()
        feed_dir.is_dir.return_value = True
        non_dir = MagicMock()
        non_dir.is_dir.return_value = False
        group_dir.iterdir.return_value = [feed_dir, non_dir]

        fm = FeedManager()
        fm.work_dir_path = MagicMock()
        fm.work_dir_path.iterdir.return_value = [group_dir]

        fm.load_all_progress_info_from_files(max_num_feeds=10)

        mock_add.assert_called_once()

    @patch.object(FeedManager, "_add_progress_info", return_value=1)
    def test_skips_non_dir_groups(self, mock_add: MagicMock) -> None:
        non_dir = MagicMock()
        non_dir.is_dir.return_value = False

        fm = FeedManager()
        fm.work_dir_path = MagicMock()
        fm.work_dir_path.iterdir.return_value = [non_dir]

        fm.load_all_progress_info_from_files(max_num_feeds=10)

        mock_add.assert_not_called()


class TestSearch(FeedManagerTestBase):
    def test_empty_list(self) -> None:
        self.assertEqual(FeedManager.search([]), [])

    def test_all_whitespace(self) -> None:
        self.assertEqual(FeedManager.search(["", " ", "  "]), [])

    def test_mixed_empty_and_valid(self) -> None:
        row = self._make_feed_row(feed_name="abc", feed_title="ABC", group_name="g", is_active=True)
        self.mock_query.all.return_value = [row]

        result = FeedManager.search(["abc", "", " "])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["feed_name"], "abc")

    def test_returns_formatted_results(self) -> None:
        row = self._make_feed_row(feed_name="one_piece", feed_title="One Piece", group_name="manga", is_active=True)
        self.mock_query.all.return_value = [row]

        result = FeedManager.search(["piece"])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["feed_name"], "one_piece")
        self.assertEqual(result[0]["feed_title"], "One Piece")
        self.assertEqual(result[0]["group_name"], "manga")
        self.assertTrue(result[0]["is_active"])

    def test_uses_feed_name_as_title_when_title_empty(self) -> None:
        row = self._make_feed_row(feed_name="no_title", feed_title="", group_name="g", is_active=True)
        self.mock_query.all.return_value = [row]

        result = FeedManager.search(["no_title"])

        self.assertEqual(result[0]["feed_title"], "no_title")

    def test_uses_feed_name_as_title_when_title_none(self) -> None:
        row = self._make_feed_row(feed_name="no_title", feed_title=None, group_name="g", is_active=True)
        self.mock_query.all.return_value = [row]

        result = FeedManager.search(["no_title"])

        self.assertEqual(result[0]["feed_title"], "no_title")

    def test_multiple_keywords(self) -> None:
        row = self._make_feed_row(feed_name="feed_abc", feed_title="ABC", group_name="g", is_active=True)
        self.mock_query.all.return_value = [row]

        result = FeedManager.search(["abc", "feed"])

        self.assertEqual(len(result), 1)


class TestGetGroups(FeedManagerTestBase):
    def test_returns_groups_sorted(self) -> None:
        # Mock distinct query for group names
        row_b = MagicMock()
        row_b.group_name = "beta"
        row_a = MagicMock()
        row_a.group_name = "alpha"

        call_count = [0]

        def query_side_effect(*args, **kwargs):
            return self.mock_query

        self.mock_session.query.side_effect = query_side_effect

        # distinct().all() returns group name rows
        self.mock_query.distinct.return_value = self.mock_query
        self.mock_query.all.return_value = [row_b, row_a]

        # count calls
        self.mock_query.count.side_effect = [3, 2, 1, 1]

        result = FeedManager.get_groups()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "alpha")
        self.assertEqual(result[1]["name"], "beta")

    def test_returns_empty_when_no_groups(self) -> None:
        self.mock_query.distinct.return_value = self.mock_query
        self.mock_query.all.return_value = []

        result = FeedManager.get_groups()

        self.assertEqual(result, [])

    def test_is_active_true_when_active_count_positive(self) -> None:
        row = MagicMock()
        row.group_name = "g"
        self.mock_query.distinct.return_value = self.mock_query
        self.mock_query.all.return_value = [row]
        # first count = total, second = active
        self.mock_query.count.side_effect = [5, 3]

        result = FeedManager.get_groups()

        self.assertTrue(result[0]["is_active"])

    def test_is_active_false_when_no_active_feeds(self) -> None:
        row = MagicMock()
        row.group_name = "g"
        self.mock_query.distinct.return_value = self.mock_query
        self.mock_query.all.return_value = [row]
        self.mock_query.count.side_effect = [5, 0]

        result = FeedManager.get_groups()

        self.assertFalse(result[0]["is_active"])


class TestGetFeedsByGroup(FeedManagerTestBase):
    def test_returns_feeds(self) -> None:
        row = self._make_feed_row(feed_name="feed1", feed_title="Feed 1", group_name="grp", is_active=True)
        self.mock_query.all.return_value = [row]

        result = FeedManager.get_feeds_by_group("grp")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "feed1")
        self.assertEqual(result[0]["title"], "Feed 1")
        self.assertEqual(result[0]["group_name"], "grp")
        self.assertTrue(result[0]["is_active"])

    def test_uses_feed_name_as_title_when_empty(self) -> None:
        row = self._make_feed_row(feed_name="feed_x", feed_title="", group_name="g", is_active=True)
        self.mock_query.all.return_value = [row]

        result = FeedManager.get_feeds_by_group("g")

        self.assertEqual(result[0]["title"], "feed_x")

    def test_uses_feed_name_as_title_when_none(self) -> None:
        row = self._make_feed_row(feed_name="feed_x", feed_title=None, group_name="g", is_active=True)
        self.mock_query.all.return_value = [row]

        result = FeedManager.get_feeds_by_group("g")

        self.assertEqual(result[0]["title"], "feed_x")

    def test_returns_empty(self) -> None:
        self.mock_query.all.return_value = []
        result = FeedManager.get_feeds_by_group("no_group")
        self.assertEqual(result, [])


class TestGetFeedInfo(FeedManagerTestBase):
    def test_feed_not_found(self) -> None:
        self.mock_query.first.return_value = None

        result = FeedManager.get_feed_info("grp", "nonexistent")

        self.assertEqual(result, {})

    def test_feed_with_config(self) -> None:
        config_data = {"rss": {"title": "T"}, "collection": {}}
        feed = self._make_feed_row(
            feed_name="feed1",
            feed_title="Feed 1",
            group_name="grp",
            config=json.dumps(config_data),
            config_modify_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            collect_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
            total_item_count=50,
            public_feed_file_path="/path/to/feed.xml",
            file_size=1024,
            num_items=10,
            upload_date=datetime(2024, 3, 1, tzinfo=timezone.utc),
            current_index=20,
            unit_size_per_day=5.0,
            progress_ratio=48.0,
            due_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        self.mock_query.first.return_value = feed

        result = FeedManager.get_feed_info("grp", "feed1")

        self.assertEqual(result["feed_name"], "feed1")
        self.assertEqual(result["config"], config_data)
        self.assertIn("collection_info", result)
        self.assertIn("public_feed_info", result)
        self.assertIn("progress_info", result)
        self.assertEqual(result["progress_info"]["current_index"], 20)

    def test_feed_with_empty_config(self) -> None:
        feed = self._make_feed_row(feed_name="feed1", feed_title="F", group_name="g", config="")
        self.mock_query.first.return_value = feed

        result = FeedManager.get_feed_info("g", "feed1")

        self.assertEqual(result["config"], {})


class TestToggleFeed(FeedManagerTestBase):
    def test_toggle_active_to_inactive(self) -> None:
        row = self._make_feed_row(feed_name="my_feed")
        self.mock_query.first.return_value = row

        result = FeedManager.toggle_feed("my_feed")

        self.assertTrue(result)
        self.mock_query.update.assert_called_once()
        update_args = self.mock_query.update.call_args[0][0]
        self.assertEqual(update_args[FeedInfo.feed_name], "_my_feed")
        self.assertFalse(update_args[FeedInfo.is_active])

    def test_toggle_inactive_to_active(self) -> None:
        row = self._make_feed_row(feed_name="_my_feed")
        self.mock_query.first.return_value = row

        result = FeedManager.toggle_feed("_my_feed")

        self.assertTrue(result)
        update_args = self.mock_query.update.call_args[0][0]
        self.assertEqual(update_args[FeedInfo.feed_name], "my_feed")
        self.assertTrue(update_args[FeedInfo.is_active])

    def test_toggle_nonexistent_feed(self) -> None:
        self.mock_query.first.return_value = None

        result = FeedManager.toggle_feed("nonexistent")

        self.assertTrue(result)
        self.mock_query.update.assert_not_called()


class TestToggleGroup(FeedManagerTestBase):
    def test_toggle_active_to_inactive(self) -> None:
        row = self._make_feed_row(group_name="my_group")
        self.mock_query.first.return_value = row

        result = FeedManager.toggle_group("my_group")

        self.assertTrue(result)
        update_args = self.mock_query.update.call_args[0][0]
        self.assertEqual(update_args[FeedInfo.group_name], "_my_group")
        self.assertFalse(update_args[FeedInfo.is_active])

    def test_toggle_inactive_to_active(self) -> None:
        row = self._make_feed_row(group_name="_my_group")
        self.mock_query.first.return_value = row

        result = FeedManager.toggle_group("_my_group")

        self.assertTrue(result)
        update_args = self.mock_query.update.call_args[0][0]
        self.assertEqual(update_args[FeedInfo.group_name], "my_group")
        self.assertTrue(update_args[FeedInfo.is_active])

    def test_toggle_nonexistent_group(self) -> None:
        self.mock_query.first.return_value = None

        result = FeedManager.toggle_group("nonexistent")

        self.assertTrue(result)
        self.mock_query.update.assert_not_called()


class TestLoadAll(FeedManagerTestBase):
    def test_calls_all_load_methods(self) -> None:
        fm = FeedManager()
        with patch.object(fm, "load_all_config_files") as m1, patch.object(fm, "load_all_rss_files") as m2, patch.object(fm, "load_all_public_feed_files") as m3, patch.object(fm, "load_all_progress_info_from_files") as m4:
            fm.load_all(max_num_feeds=5, max_num_public_feeds=10)

            m1.assert_called_once_with(5)
            m2.assert_called_once_with(5)
            m3.assert_called_once_with(10)
            m4.assert_called_once_with(5)

    def test_calls_with_defaults(self) -> None:
        fm = FeedManager()
        with patch.object(fm, "load_all_config_files") as m1, patch.object(fm, "load_all_rss_files") as m2, patch.object(fm, "load_all_public_feed_files") as m3, patch.object(fm, "load_all_progress_info_from_files") as m4:
            fm.load_all()

            m1.assert_called_once_with(None)
            m2.assert_called_once_with(None)
            m3.assert_called_once_with(None)
            m4.assert_called_once_with(None)


class TestAddRssInfoWrapper(FeedManagerTestBase):
    def test_add_rss_info_calls_internal(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.name = "feed"

        with patch.object(FeedManager, "_add_rss_info") as mock_add:
            FeedManager.add_rss_info(feed_dir_path)
            mock_add.assert_called_once()


class TestAddPublicFeedWrapper(FeedManagerTestBase):
    def test_add_public_feed_calls_internal(self) -> None:
        path = MagicMock(spec=Path)
        path.stem = "feed"

        with patch.object(FeedManager, "_add_public_feed", return_value=5) as mock_add:
            FeedManager.add_public_feed(path)
            mock_add.assert_called_once()

    def test_add_public_feed_by_feed_name(self) -> None:
        fm = FeedManager()
        fm.public_feed_dir_path = MagicMock()
        expected_path = MagicMock()
        expected_path.stem = "feed"
        fm.public_feed_dir_path.__truediv__ = MagicMock(return_value=expected_path)

        with patch.object(FeedManager, "add_public_feed") as mock_add:
            fm.add_public_feed_by_feed_name("feed")
            mock_add.assert_called_once()


class TestAddProgressInfoWrapper(FeedManagerTestBase):
    def test_add_progress_info_calls_internal(self) -> None:
        feed_dir_path = MagicMock(spec=Path)
        feed_dir_path.name = "feed"

        with patch.object(FeedManager, "_add_progress_info", return_value=1) as mock_add:
            FeedManager.add_progress_info(feed_dir_path)
            mock_add.assert_called_once()


if __name__ == "__main__":
    unittest.main()
