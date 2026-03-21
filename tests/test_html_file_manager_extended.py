#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tempfile
import unittest
import shutil
import logging.config
from pathlib import Path
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from datetime import datetime, timezone

from bin.html_file_manager import HtmlFileManager
from bin.db import DB

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestHtmlFileManagerExtended(unittest.TestCase):
    """Extended tests for HtmlFileManager to improve coverage."""

    def setUp(self) -> None:
        self.mock_db_config = {"host": "localhost", "port": 3306, "user": "test", "password": "test", "database": "test"}
        self.mock_session = MagicMock()
        self.mock_query = MagicMock()
        self.mock_session.query.return_value = self.mock_query

        self.patcher_init = patch("bin.db.DB.init", return_value=None)
        self.patcher_create = patch("bin.db.DB.create_all_tables", return_value=None)
        self.patcher_drop = patch("bin.db.DB.drop_all_tables", return_value=None)
        self.patcher_session = patch("bin.db.DB.session_ctx")
        self.mock_session_ctx = self.patcher_session.start()
        self.mock_session_ctx.return_value.__enter__ = MagicMock(return_value=self.mock_session)
        self.mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)
        self.patcher_init.start()
        self.patcher_create.start()
        self.patcher_drop.start()
        DB.init(self.mock_db_config)
        DB.create_all_tables(self.mock_db_config)

        self.hfm = HtmlFileManager()
        self.test_feed_dir_path = self.hfm.work_dir_path / "ext_test_group" / "ext_test_feed"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_feed_dir_path.parent, ignore_errors=True)
        del self.hfm
        DB.drop_all_tables(self.mock_db_config)
        self.patcher_init.stop()
        self.patcher_create.stop()
        self.patcher_drop.stop()
        self.patcher_session.stop()

    # ── get_html_file_name ──

    def test_get_html_file_name_basic(self) -> None:
        path = self.test_feed_dir_path / "html" / "abc123.html"
        result = HtmlFileManager.get_html_file_name(path)
        self.assertEqual("ext_test_feed/html/abc123.html", result)

    def test_get_html_file_name_different_path(self) -> None:
        path = Path("/some/group/feedX/html/deadbeef.html")
        result = HtmlFileManager.get_html_file_name(path)
        self.assertEqual("feedX/html/deadbeef.html", result)

    # ── _get_feed_title_from_path ──

    @patch("bin.html_file_manager.FeedManager.get_feed_info")
    def test_get_feed_title_from_path_success(self, mock_get_feed_info: MagicMock) -> None:
        mock_get_feed_info.return_value = {"feed_title": "My Feed Title"}
        result = HtmlFileManager._get_feed_title_from_path("groupA/feedB")
        self.assertEqual("My Feed Title", result)
        mock_get_feed_info.assert_called_once_with("groupA", "feedB")

    @patch("bin.html_file_manager.FeedManager.get_feed_info")
    def test_get_feed_title_from_path_no_title_key(self, mock_get_feed_info: MagicMock) -> None:
        mock_get_feed_info.return_value = {"other_key": "value"}
        result = HtmlFileManager._get_feed_title_from_path("groupA/feedB")
        self.assertEqual("feedB", result)

    @patch("bin.html_file_manager.FeedManager.get_feed_info")
    def test_get_feed_title_from_path_none_info(self, mock_get_feed_info: MagicMock) -> None:
        mock_get_feed_info.return_value = None
        result = HtmlFileManager._get_feed_title_from_path("groupA/feedB")
        self.assertEqual("feedB", result)

    def test_get_feed_title_from_path_short_path(self) -> None:
        result = HtmlFileManager._get_feed_title_from_path("only_one_part")
        self.assertEqual("", result)

    @patch("bin.html_file_manager.FeedManager.get_feed_info")
    def test_get_feed_title_from_path_exception(self, mock_get_feed_info: MagicMock) -> None:
        mock_get_feed_info.side_effect = RuntimeError("DB error")
        result = HtmlFileManager._get_feed_title_from_path("groupA/feedB")
        self.assertEqual("", result)

    # ── get_html_file_size_map with DB rows ──

    @patch("bin.html_file_manager.HtmlFileManager._get_feed_title_from_path", return_value="Title")
    def test_get_html_file_size_map_with_rows(self, mock_title: MagicMock) -> None:
        mock_row = SimpleNamespace(file_name="feed/html/abc.html", file_path="group/feed/html/abc.html", feed_dir_path="group/feed", size=100, update_date=datetime(2024, 1, 1, tzinfo=timezone.utc))
        self.mock_query.where.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = [mock_row]

        result = HtmlFileManager.get_html_file_size_map("test_feed")
        self.assertIn("feed/html/abc.html", result)
        entry = result["feed/html/abc.html"]
        self.assertEqual(100, entry["size"])
        self.assertEqual("group/feed", entry["feed_dir_path"])
        self.assertEqual("Title", entry["feed_title"])

    # ── get_html_file_with_many_image_tag_map with DB rows ──

    @patch("bin.html_file_manager.HtmlFileManager._get_feed_title_from_path", return_value="FT")
    def test_get_html_file_with_many_image_tag_map_with_rows(self, mock_title: MagicMock) -> None:
        mock_row = SimpleNamespace(file_name="f/html/x.html", file_path="g/f/html/x.html", feed_dir_path="g/f", count_with_many_image_tag=3, update_date=datetime(2024, 2, 1, tzinfo=timezone.utc))
        self.mock_query.where.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = [mock_row]

        result = HtmlFileManager.get_html_file_with_many_image_tag_map()
        self.assertIn("f/html/x.html", result)
        self.assertEqual(3, result["f/html/x.html"]["count"])
        self.assertEqual("FT", result["f/html/x.html"]["feed_title"])

    # ── get_html_file_without_image_tag_map with DB rows ──

    @patch("bin.html_file_manager.HtmlFileManager._get_feed_title_from_path", return_value="NoImg")
    def test_get_html_file_without_image_tag_map_with_rows(self, mock_title: MagicMock) -> None:
        mock_row = SimpleNamespace(file_name="f/html/y.html", file_path="g/f/html/y.html", feed_dir_path="g/f", count_without_image_tag=2, update_date=datetime(2024, 3, 1, tzinfo=timezone.utc))
        self.mock_query.where.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = [mock_row]

        result = HtmlFileManager.get_html_file_without_image_tag_map()
        self.assertIn("f/html/y.html", result)
        self.assertEqual(2, result["f/html/y.html"]["count"])
        self.assertEqual("NoImg", result["f/html/y.html"]["feed_title"])

    # ── get_html_file_image_not_found_map with DB rows ──

    @patch("bin.html_file_manager.HtmlFileManager._get_feed_title_from_path", return_value="NF")
    def test_get_html_file_image_not_found_map_with_rows(self, mock_title: MagicMock) -> None:
        mock_row = SimpleNamespace(file_name="f/html/z.html", file_path="g/f/html/z.html", feed_dir_path="g/f", count_with_image_not_found=5, update_date=datetime(2024, 4, 1, tzinfo=timezone.utc))
        self.mock_query.where.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = [mock_row]

        result = HtmlFileManager.get_html_file_image_not_found_map()
        self.assertIn("f/html/z.html", result)
        self.assertEqual(5, result["f/html/z.html"]["count"])
        self.assertEqual("NF", result["f/html/z.html"]["feed_title"])

    # ── remove_html_file_in_path_from_info ──

    def test_remove_html_file_invalid_dir_type(self) -> None:
        """Invalid dir_type_name should log error and return early."""
        self.hfm.remove_html_file_in_path_from_info("invalid_type", Path("/tmp/test"))
        # Should not interact with DB
        self.mock_session.query.assert_not_called()

    def test_remove_html_file_by_feed_dir_path(self) -> None:
        mock_row = SimpleNamespace(file_path="g/f/html/a.html")
        self.mock_query.where.return_value = self.mock_query
        self.mock_query.filter_by.return_value = self.mock_query
        self.mock_query.all.return_value = [mock_row]

        self.hfm.remove_html_file_in_path_from_info("feed_dir_path", self.test_feed_dir_path)
        self.mock_query.filter_by.assert_called()
        self.mock_query.delete.assert_called()

    def test_remove_html_file_by_feed_dir_path_with_do_remove(self) -> None:
        """With do_remove_file=True, should call unlink on physical files."""
        mock_row = SimpleNamespace(file_path="g/f/html/a.html")
        self.mock_query.where.return_value = self.mock_query
        self.mock_query.filter_by.return_value = self.mock_query
        self.mock_query.all.return_value = [mock_row]

        with patch.object(Path, "unlink") as mock_unlink:
            self.hfm.remove_html_file_in_path_from_info("feed_dir_path", self.test_feed_dir_path, do_remove_file=True)
            mock_unlink.assert_called()

    def test_remove_html_file_by_file_path(self) -> None:
        file_path = self.test_feed_dir_path / "html" / "test.html"
        self.mock_query.filter_by.return_value = self.mock_query

        self.hfm.remove_html_file_in_path_from_info("file_path", file_path)
        self.mock_query.filter_by.assert_called()
        self.mock_query.delete.assert_called()

    def test_remove_html_file_by_file_path_with_do_remove(self) -> None:
        file_path = self.test_feed_dir_path / "html" / "test.html"
        self.mock_query.filter_by.return_value = self.mock_query

        with patch.object(Path, "unlink") as mock_unlink:
            self.hfm.remove_html_file_in_path_from_info("file_path", file_path, do_remove_file=True)
            mock_unlink.assert_called_with(missing_ok=True)

    # ── add_html_file ──

    def test_add_html_file_non_existent_dir(self) -> None:
        """Non-existent directory should log error and return."""
        non_existent = Path("/tmp/nonexistent_feed_dir_12345")
        self.hfm.add_html_file(non_existent)
        # Should not interact with DB session
        self.mock_session.merge.assert_not_called()

    def test_add_html_file_with_html_files(self) -> None:
        html_dir = self.test_feed_dir_path / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / "abc123.html").write_text("<p>hello</p>")

        self.hfm.add_html_file(self.test_feed_dir_path)
        self.mock_session.merge.assert_called_once()
        self.mock_session.flush.assert_called_once()

    def test_add_html_file_skips_underscore_dirs(self) -> None:
        """Files under directories starting with _ should be skipped."""
        # Create html dir named _hidden under a _group
        hidden_feed = self.hfm.work_dir_path / "_hidden_group" / "_hidden_feed"
        html_dir = hidden_feed / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / "test.html").write_text("<p>skip me</p>")

        try:
            self.hfm.add_html_file(hidden_feed)
            # The file should be skipped due to underscore prefix
            self.mock_session.merge.assert_not_called()
        finally:
            shutil.rmtree(hidden_feed.parent, ignore_errors=True)

    def test_add_html_file_skips_non_html(self) -> None:
        """Non-html files in html/ directory should be skipped."""
        html_dir = self.test_feed_dir_path / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / "readme.txt").write_text("not html")

        self.hfm.add_html_file(self.test_feed_dir_path)
        self.mock_session.merge.assert_not_called()

    # ── load_all_html_files ──

    def test_load_all_html_files_new_file(self) -> None:
        """New file on filesystem but not in DB should be inserted."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            grp_path = tmp_path / "load_grp"
            feed_path = grp_path / "load_feed"
            html_dir = feed_path / "html"
            html_dir.mkdir(parents=True, exist_ok=True)
            (html_dir / "new1.html").write_text("<p>new</p>")

            # DB has no files
            self.mock_query.all.return_value = []
            self.mock_query.filter.return_value = self.mock_query

            self.hfm.work_dir_path = tmp_path
            self.hfm.load_all_html_files(max_num_feeds=20)

            self.mock_session.bulk_insert_mappings.assert_called_once()
            args = self.mock_session.bulk_insert_mappings.call_args
            mappings = args[0][1]
            self.assertEqual(1, len(mappings))
            self.assertIn("new1.html", mappings[0]["file_name"])

    def test_load_all_html_files_deleted_file(self) -> None:
        """File in DB but not on filesystem should be deleted."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            grp_path = tmp_path / "empty_grp"
            grp_path.mkdir(parents=True, exist_ok=True)

            # DB has a file that doesn't exist on filesystem
            db_row = SimpleNamespace(file_path="del_grp/del_feed/html/gone.html", update_date=datetime(2024, 1, 1, tzinfo=timezone.utc))
            self.mock_query.all.return_value = [db_row]
            self.mock_query.filter.return_value = self.mock_query

            self.hfm.work_dir_path = tmp_path
            self.hfm.load_all_html_files(max_num_feeds=20)

            self.mock_query.delete.assert_called_with(synchronize_session=False)

    def test_load_all_html_files_skips_non_dir(self) -> None:
        """Non-directory entries at group level should be skipped."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create a file (not dir) at work_dir level
            (tmp_path / "not_a_dir.txt").write_text("not a directory")

            self.mock_query.all.return_value = []
            self.mock_query.filter.return_value = self.mock_query

            self.hfm.work_dir_path = tmp_path
            self.hfm.load_all_html_files(max_num_feeds=20)
            # Should complete without error

    def test_load_all_html_files_file_not_found(self) -> None:
        """FileNotFoundError during stat should be handled gracefully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            grp_path = tmp_path / "fnf_grp"
            feed_path = grp_path / "fnf_feed"
            html_dir = feed_path / "html"
            html_dir.mkdir(parents=True, exist_ok=True)
            test_file = html_dir / "vanish.html"
            test_file.write_text("<p>gone</p>")

            self.mock_query.all.return_value = []
            self.mock_query.filter.return_value = self.mock_query

            original_stat = Path.stat

            def patched_stat(path_self, *args, **kwargs):
                if path_self.name == "vanish.html":
                    raise FileNotFoundError("gone")
                return original_stat(path_self, *args, **kwargs)

            self.hfm.work_dir_path = tmp_path
            with patch.object(Path, "stat", new=patched_stat):
                self.hfm.load_all_html_files(max_num_feeds=20)

            # Should not insert the vanished file
            self.mock_session.bulk_insert_mappings.assert_not_called()

    # ── _prepare_html_file_info ──

    def test_prepare_html_file_info_many_image_tags(self) -> None:
        """File with >1 image tags (1x1.jpg) should set count_with_many_image_tag=1."""
        html_dir = self.test_feed_dir_path / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        test_file = html_dir / "many_img.html"
        test_file.write_text("<img src='1x1.jpg'/>\n<img src='1x1.jpg'/>\n")

        mtime = datetime(2024, 5, 1, tzinfo=timezone.utc)
        result = self.hfm._prepare_html_file_info(test_file, mtime)
        self.assertEqual(1, result["count_with_many_image_tag"])
        self.assertEqual(0, result["count_without_image_tag"])

    def test_prepare_html_file_info_no_image_tag(self) -> None:
        """File with no 1x1.jpg tags should set count_without_image_tag=1."""
        html_dir = self.test_feed_dir_path / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        test_file = html_dir / "no_img.html"
        test_file.write_text("<p>no images</p>\n")

        mtime = datetime(2024, 5, 1, tzinfo=timezone.utc)
        result = self.hfm._prepare_html_file_info(test_file, mtime)
        self.assertEqual(0, result["count_with_many_image_tag"])
        self.assertEqual(1, result["count_without_image_tag"])

    def test_prepare_html_file_info_image_not_found(self) -> None:
        """File with image-not-found.png should set count_with_image_not_found."""
        html_dir = self.test_feed_dir_path / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        test_file = html_dir / "notfound.html"
        test_file.write_text("<img src='image-not-found.png'/>\n<img src='image-not-found.png'/>\n<img src='1x1.jpg'/>\n")

        mtime = datetime(2024, 5, 1, tzinfo=timezone.utc)
        result = self.hfm._prepare_html_file_info(test_file, mtime)
        self.assertEqual(2, result["count_with_image_not_found"])

    def test_prepare_html_file_info_unicode_error(self) -> None:
        """UnicodeDecodeError should be caught; image_tag_count stays 0 so count_without_image_tag=1."""
        html_dir = self.test_feed_dir_path / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        test_file = html_dir / "binary.html"
        test_file.write_bytes(b"\x80\x81\x82\x83")

        mtime = datetime(2024, 5, 1, tzinfo=timezone.utc)
        result = self.hfm._prepare_html_file_info(test_file, mtime)
        self.assertEqual(0, result["count_with_many_image_tag"])
        # image_tag_count remains 0 after UnicodeDecodeError, so count_without_image_tag=1
        self.assertEqual(1, result["count_without_image_tag"])
        self.assertEqual(0, result["count_with_image_not_found"])


if __name__ == "__main__":
    unittest.main()
