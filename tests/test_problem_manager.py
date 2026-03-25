#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import unittest
import shutil
import tempfile
from datetime import datetime, timezone
import logging.config
from pathlib import Path
from typing import Any, Optional
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
        with patch("bin.db.DB.session_ctx") as mock_session_ctx, patch.object(self.pm.feed_manager, "load_all") as mock_fm_load, patch.object(self.pm.html_file_manager, "load_all_html_files") as mock_hf_load:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__enter__.return_value = mock_session
            mock_session_ctx.return_value.__exit__.return_value = None

            result = self.pm.load_all(max_num_feeds=20, max_num_public_feeds=40)

            self.assertEqual(result, 0)
            mock_fm_load.assert_called_once_with(max_num_feeds=20, max_num_public_feeds=40)
            mock_hf_load.assert_called_once_with(20)

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


class TestGetFeedNameStatusInfoMapDuplicateFiltering(unittest.TestCase):
    """같은 feed_name에 feedmaker=True/False 레코드가 공존할 때 필터링 검증"""

    def _make_feed_row(self, feed_name: str, group_name: str, feedmaker: bool, **kwargs: Any) -> MagicMock:
        row = MagicMock()
        row.feed_name = feed_name
        row.group_name = group_name
        row.feedmaker = feedmaker
        row.feed_title = kwargs.get("feed_title", "")
        row.http_request = kwargs.get("http_request", True)
        row.public_html = kwargs.get("public_html", True)
        row.is_active = kwargs.get("is_active", True)
        row.access_date = kwargs.get("access_date", datetime.now(timezone.utc))
        row.view_date = kwargs.get("view_date", None)
        row.rss_update_date = kwargs.get("rss_update_date", None)
        row.public_feed_file_path = kwargs.get("public_feed_file_path", "")
        row.upload_date = kwargs.get("upload_date", None)
        row.config = kwargs.get("config", "")
        return row

    def _setup_session(self, mock_session_ctx: MagicMock, rows: list, feedmaker_true_names: list[str]) -> None:
        """메인 쿼리(rows)와 feedmaker_true_names 쿼리를 모두 mock"""
        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        # s.query(FeedInfo).where(...).order_by(...).all() → rows
        main_query = MagicMock()
        main_query.where.return_value.order_by.return_value.all.return_value = rows

        # s.query(FeedInfo.feed_name).filter(...).all() → feedmaker_true_names
        name_row = type("Row", (), {})
        feedmaker_query = MagicMock()
        name_rows = []
        for name in feedmaker_true_names:
            r = name_row()
            r.feed_name = name
            name_rows.append(r)
        feedmaker_query.filter.return_value.all.return_value = name_rows

        # query() 호출 시 인자에 따라 분기
        from bin.models import FeedInfo

        def query_side_effect(*args):
            if len(args) == 1 and args[0] is FeedInfo.feed_name:
                return feedmaker_query
            return main_query

        mock_session.query.side_effect = query_side_effect

    @patch("bin.db.DB.session_ctx")
    def test_duplicate_feed_name_excludes_feedmaker_false(self, mock_session_ctx: MagicMock) -> None:
        """feedmaker=True 레코드가 있으면 같은 이름의 feedmaker=False 레코드를 제외"""
        rows = [self._make_feed_row("dup_feed", "group_a", feedmaker=False), self._make_feed_row("dup_feed", "group_b", feedmaker=True)]
        self._setup_session(mock_session_ctx, rows, ["dup_feed"])

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertIn("dup_feed", result)
        self.assertEqual(result["dup_feed"]["group_name"], "group_b")
        self.assertTrue(result["dup_feed"]["feedmaker"])

    @patch("bin.db.DB.session_ctx")
    def test_duplicate_excludes_even_when_true_filtered_by_query(self, mock_session_ctx: MagicMock) -> None:
        """feedmaker=True 레코드가 SQL 조건으로 rows에서 빠져도, 전체 테이블 조회로 감지하여 제외"""
        # rows에는 feedmaker=False만 있음 (feedmaker=True는 3번 조건으로 쿼리에서 제외된 상황)
        rows = [self._make_feed_row("dup_feed", "group_a", feedmaker=False)]
        # 하지만 전체 테이블에는 feedmaker=True가 존재
        self._setup_session(mock_session_ctx, rows, ["dup_feed"])

        result = ProblemManager.get_feed_name_status_info_map()

        # feedmaker=False인 group_a가 제외되어 결과에 없어야 함
        self.assertNotIn("dup_feed", result)

    @patch("bin.db.DB.session_ctx")
    def test_unique_feedmaker_false_is_kept(self, mock_session_ctx: MagicMock) -> None:
        """feedmaker=True 레코드가 없으면 feedmaker=False 레코드를 유지"""
        rows = [self._make_feed_row("solo_feed", "group_a", feedmaker=False)]
        self._setup_session(mock_session_ctx, rows, [])

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertIn("solo_feed", result)
        self.assertFalse(result["solo_feed"]["feedmaker"])

    @patch("bin.db.DB.session_ctx")
    def test_multiple_duplicates_only_feedmaker_true_kept(self, mock_session_ctx: MagicMock) -> None:
        """여러 그룹에 같은 feed_name이 있을 때 feedmaker=True만 유지"""
        rows = [self._make_feed_row("multi_feed", "group_a", feedmaker=False), self._make_feed_row("multi_feed", "group_b", feedmaker=False), self._make_feed_row("multi_feed", "group_c", feedmaker=True)]
        self._setup_session(mock_session_ctx, rows, ["multi_feed"])

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertIn("multi_feed", result)
        self.assertEqual(result["multi_feed"]["group_name"], "group_c")
        self.assertTrue(result["multi_feed"]["feedmaker"])

    @patch("bin.db.DB.session_ctx")
    def test_mixed_feeds_with_and_without_duplicates(self, mock_session_ctx: MagicMock) -> None:
        """중복 피드와 단독 피드가 혼재할 때 각각 올바르게 처리"""
        rows = [self._make_feed_row("dup_feed", "group_a", feedmaker=False), self._make_feed_row("normal_feed", "group_x", feedmaker=False), self._make_feed_row("dup_feed", "group_b", feedmaker=True), self._make_feed_row("another_feed", "group_y", feedmaker=True)]
        self._setup_session(mock_session_ctx, rows, ["dup_feed", "another_feed"])

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertIn("dup_feed", result)
        self.assertEqual(result["dup_feed"]["group_name"], "group_b")
        self.assertIn("normal_feed", result)
        self.assertFalse(result["normal_feed"]["feedmaker"])
        self.assertIn("another_feed", result)
        self.assertTrue(result["another_feed"]["feedmaker"])


if __name__ == "__main__":
    unittest.main()
