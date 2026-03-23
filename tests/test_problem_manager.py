#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import unittest
import shutil
import tempfile
from datetime import datetime, timezone
import logging.config
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

from bin.feed_maker_util import Config
from bin.problem_manager import ProblemManager


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestProblemManager(unittest.TestCase):
    temp_dir: Optional[Path] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = Path(tempfile.mkdtemp())
        ProblemManager.is_tables_created = False

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.temp_dir and cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)

    def setUp(self) -> None:
        assert self.temp_dir is not None

        self.test_feed_dir_path = self.temp_dir / "my_test_group" / "my_test_feed2"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

        self.mock_session = MagicMock()
        self.mock_query = MagicMock()
        self.mock_session.query.return_value = self.mock_query

        ProblemManager.is_tables_created = False

        with patch("bin.db.DB.create_all_tables"), patch("bin.db.DB.session_ctx") as mock_session_ctx:
            mock_session_ctx.return_value.__enter__.return_value = self.mock_session
            mock_session_ctx.return_value.__exit__.return_value = None
            self.pm = ProblemManager()

    def tearDown(self) -> None:
        if self.test_feed_dir_path.parent.exists():
            shutil.rmtree(self.test_feed_dir_path.parent)
        del self.pm

    def test_get_feed_name_status_info_map(self) -> None:
        with patch.object(ProblemManager, "get_feed_name_status_info_map") as mock_get_map:
            mock_get_map.return_value = {
                "test_feed": {
                    "feed_name": "test_feed",
                    "feed_title": "Test Feed",
                    "group_name": "test_group",
                    "http_request": True,
                    "public_html": True,
                    "feedmaker": True,
                    "access_date": datetime.now(timezone.utc),
                    "view_date": datetime.now(timezone.utc),
                    "upload_date": datetime.now(timezone.utc),
                    "update_date": datetime.now(timezone.utc),
                    "file_path": "/path/to/feed.xml",
                }
            }

            result = ProblemManager.get_feed_name_status_info_map()

        self.assertIn("test_feed", result)
        status_info = result["test_feed"]
        self.assertIn("feed_name", status_info)
        self.assertIn("feed_title", status_info)
        self.assertIn("group_name", status_info)
        self.assertIn("http_request", status_info)
        self.assertIn("public_html", status_info)
        self.assertIn("feedmaker", status_info)
        self.assertIn("access_date", status_info)
        self.assertIn("view_date", status_info)
        self.assertIn("upload_date", status_info)
        self.assertIn("update_date", status_info)
        self.assertIn("file_path", status_info)

    def test_update_feed_info_basic(self) -> None:
        conf_data = {"configuration": {"rss": {"title": "Test Feed Title"}, "collection": {"list_url_list": ["http://example.com"], "is_completed": False, "unit_size_per_day": 1.0}}}
        test_config_file_path = self.test_feed_dir_path / Config.DEFAULT_CONF_FILE
        with test_config_file_path.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        with (
            patch("bin.feed_manager.FeedManager.remove_config_info") as mock_remove_config,
            patch("bin.feed_manager.FeedManager.remove_rss_info") as mock_remove_rss,
            patch("bin.feed_manager.FeedManager.remove_progress_info") as mock_remove_progress,
            patch("bin.access_log_manager.AccessLogManager.remove_httpd_access_info") as mock_remove_access,
            patch("bin.html_file_manager.HtmlFileManager.remove_html_file_in_path_from_info") as mock_remove_html,
            patch("bin.feed_manager.FeedManager.add_config_info") as mock_add_config,
            patch("bin.feed_manager.FeedManager.add_rss_info") as mock_add_rss,
            patch("bin.feed_manager.FeedManager.add_progress_info") as mock_add_progress,
            patch("bin.html_file_manager.HtmlFileManager.add_html_file") as mock_add_html,
            patch.object(self.pm.feed_manager, "remove_public_feed_by_feed_name") as mock_remove_public,
            patch.object(self.pm.feed_manager, "add_public_feed_by_feed_name") as mock_add_public,
        ):
            self.pm.update_feed_info(self.test_feed_dir_path)

            mock_remove_config.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_remove_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_access.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_html.assert_called_once_with("feed_dir_path", self.test_feed_dir_path)
            mock_add_config.assert_called_once_with(self.test_feed_dir_path)
            mock_add_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_add_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_add_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_add_html.assert_called_once_with(self.test_feed_dir_path)

    def test_update_feed_info_with_new_path(self) -> None:
        assert self.temp_dir is not None
        new_feed_dir_path: Path = self.temp_dir / "my_test_group" / "new_test_feed"
        new_feed_dir_path.mkdir(parents=True, exist_ok=True)

        conf_data = {"configuration": {"rss": {"title": "New Test Feed Title"}, "collection": {"list_url_list": ["http://newexample.com"], "is_completed": True, "unit_size_per_day": 2.0}}}
        test_config_file_path = new_feed_dir_path / Config.DEFAULT_CONF_FILE
        with test_config_file_path.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        with (
            patch("bin.feed_manager.FeedManager.remove_config_info") as mock_remove_config,
            patch("bin.feed_manager.FeedManager.remove_rss_info") as mock_remove_rss,
            patch("bin.feed_manager.FeedManager.remove_progress_info") as mock_remove_progress,
            patch("bin.access_log_manager.AccessLogManager.remove_httpd_access_info") as mock_remove_access,
            patch("bin.html_file_manager.HtmlFileManager.remove_html_file_in_path_from_info") as mock_remove_html,
            patch("bin.feed_manager.FeedManager.add_config_info") as mock_add_config,
            patch("bin.feed_manager.FeedManager.add_rss_info") as mock_add_rss,
            patch("bin.feed_manager.FeedManager.add_progress_info") as mock_add_progress,
            patch("bin.html_file_manager.HtmlFileManager.add_html_file") as mock_add_html,
            patch.object(self.pm.feed_manager, "remove_public_feed_by_feed_name") as mock_remove_public,
            patch.object(self.pm.feed_manager, "add_public_feed_by_feed_name") as mock_add_public,
        ):
            self.pm.update_feed_info(self.test_feed_dir_path, new_feed_dir_path)

            mock_remove_config.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_access.assert_called_once_with(self.test_feed_dir_path)
            mock_add_config.assert_called_once_with(new_feed_dir_path)
            mock_add_html.assert_called_once_with(new_feed_dir_path)

        if new_feed_dir_path.parent.exists():
            shutil.rmtree(new_feed_dir_path.parent)

    def test_update_feed_info_nonexistent_directories(self) -> None:
        assert self.temp_dir is not None
        nonexistent_path: Path = self.temp_dir / "nonexistent_group" / "nonexistent_feed"

        with (
            patch("bin.feed_manager.FeedManager.remove_config_info"),
            patch("bin.feed_manager.FeedManager.remove_rss_info"),
            patch("bin.feed_manager.FeedManager.remove_progress_info"),
            patch("bin.access_log_manager.AccessLogManager.remove_httpd_access_info"),
            patch("bin.html_file_manager.HtmlFileManager.remove_html_file_in_path_from_info"),
            patch("bin.feed_manager.FeedManager.add_config_info"),
            patch("bin.feed_manager.FeedManager.add_rss_info"),
            patch("bin.feed_manager.FeedManager.add_progress_info"),
            patch("bin.html_file_manager.HtmlFileManager.add_html_file"),
            patch.object(self.pm.feed_manager, "remove_public_feed_by_feed_name"),
            patch.object(self.pm.feed_manager, "add_public_feed_by_feed_name"),
            patch("bin.problem_manager.LOGGER.warning") as mock_warning,
        ):
            self.pm.update_feed_info(nonexistent_path)
            mock_warning.assert_called_once()

    def test_load_all(self) -> None:
        with patch("bin.db.DB.session_ctx") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__enter__.return_value = mock_session
            mock_session_ctx.return_value.__exit__.return_value = None

            try:
                self.pm.load_all(max_num_feeds=20, max_num_public_feeds=40)
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"load_all failed with exception: {e}")

    def test_is_tables_created_skips_create_all_tables(self) -> None:
        ProblemManager.is_tables_created = True

        with patch("bin.db.DB.create_all_tables") as mock_create_tables, patch("bin.db.DB.session_ctx") as mock_session_ctx:
            mock_session_ctx.return_value.__enter__.return_value = self.mock_session
            mock_session_ctx.return_value.__exit__.return_value = None
            pm2 = ProblemManager()
            mock_create_tables.assert_not_called()
            self.assertTrue(ProblemManager.is_tables_created)
            del pm2

    def test_main_block(self) -> None:
        import runpy
        import sys

        with patch("bin.db.DB.create_all_tables"), patch("bin.db.DB.session_ctx") as mock_session_ctx, patch("bin.feed_manager.FeedManager.load_all") as mock_fm_load, patch("bin.html_file_manager.HtmlFileManager.load_all_html_files") as mock_hf_load:
            mock_session_ctx.return_value.__enter__.return_value = self.mock_session
            mock_session_ctx.return_value.__exit__.return_value = None

            saved = sys.modules.pop("bin.problem_manager", None)
            try:
                runpy.run_module("bin.problem_manager", run_name="__main__", alter_sys=False)
            finally:
                if saved is not None:
                    sys.modules["bin.problem_manager"] = saved

            mock_fm_load.assert_called_once()
            mock_hf_load.assert_called_once()


if __name__ == "__main__":
    unittest.main()
