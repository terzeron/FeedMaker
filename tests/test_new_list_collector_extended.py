#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch, MagicMock
import logging.config
from pathlib import Path

from bin.new_list_collector import NewlistCollector

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestSplitResultIntoItemsExtended(unittest.TestCase):
    """split_result_into_items: empty link/title (40-41), ValueError (42-44)"""

    def test_empty_link_returns_empty(self) -> None:
        # tab-separated but link is empty -> line 39-41
        result = NewlistCollector.split_result_into_items("\ttitle1")
        self.assertEqual(result, [])

    def test_empty_title_returns_empty(self) -> None:
        result = NewlistCollector.split_result_into_items("http://link\t")
        self.assertEqual(result, [])

    def test_no_tab_raises_value_error_path(self) -> None:
        # single field without tab -> ValueError on unpack -> line 42-44
        result = NewlistCollector.split_result_into_items("no-tab-here")
        self.assertEqual(result, [])


class TestComposeUrlListExtended(unittest.TestCase):
    """_compose_url_list edge cases: lines 64-68, 74-75, 80-83, 86-87, 93-94"""

    def setUp(self) -> None:
        self.feed_dir = Path("/tmp/test_feed")
        self.collection_conf = {"list_url_list": ["http://example.com/list"], "item_capture_script": "./capture.py"}
        self.collector = NewlistCollector(self.feed_dir, self.collection_conf, self.feed_dir / "new_list.txt")

    def tearDown(self) -> None:
        del self.collector

    @patch("bin.new_list_collector.Crawler")
    def test_crawler_run_fails_continues(self, mock_crawler_cls) -> None:
        """crawler.run returns empty result -> line 64-65, then empty result_list -> 93-94"""
        instance = MagicMock()
        mock_crawler_cls.return_value = instance
        instance.run.return_value = ("", "some error", None)

        result = self.collector._compose_url_list()
        self.assertEqual(result, [])

    @patch("bin.new_list_collector.Crawler")
    def test_crawler_run_unicode_decode_error(self, mock_crawler_cls) -> None:
        """crawler.run raises UnicodeDecodeError -> line 66-68"""
        instance = MagicMock()
        mock_crawler_cls.return_value = instance
        instance.run.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "mock")

        result = self.collector._compose_url_list()
        self.assertEqual(result, [])

    @patch("bin.new_list_collector.Process")
    @patch("bin.new_list_collector.Crawler")
    def test_capture_script_fails_continues(self, mock_crawler_cls, mock_process) -> None:
        """capture script returns empty -> line 74-75"""
        instance = MagicMock()
        mock_crawler_cls.return_value = instance
        instance.run.return_value = ("<html>ok</html>", None, None)
        mock_process.exec_cmd.return_value = ("", "capture error")

        result = self.collector._compose_url_list()
        self.assertEqual(result, [])

    @patch("bin.new_list_collector.which")
    @patch("bin.new_list_collector.Process")
    @patch("bin.new_list_collector.Crawler")
    def test_post_process_system_path(self, mock_crawler_cls, mock_process, mock_which) -> None:
        """post_process_script with system path -> line 80-81"""
        self.collection_conf["post_process_script_list"] = ["shuf"]
        instance = MagicMock()
        mock_crawler_cls.return_value = instance
        instance.run.return_value = ("<html>ok</html>", None, None)

        # First call: capture script, second call: post_process (shuf)
        mock_process.exec_cmd.side_effect = [
            ("http://link1\ttitle1\n", None),  # capture
            ("http://link1\ttitle1\n", None),  # shuf (system path)
        ]
        mock_which.return_value = "/usr/bin/shuf"

        result = self.collector._compose_url_list()
        self.assertEqual(len(result), 1)
        # Verify the post_process command doesn't include -f flag for system path
        calls = mock_process.exec_cmd.call_args_list
        self.assertNotIn("-f", calls[1][0][0])

    @patch("bin.new_list_collector.which")
    @patch("bin.new_list_collector.Process")
    @patch("bin.new_list_collector.Crawler")
    def test_post_process_custom_path(self, mock_crawler_cls, mock_process, mock_which) -> None:
        """post_process_script with custom path -> line 82-83"""
        self.collection_conf["post_process_script_list"] = ["my_script.py"]
        instance = MagicMock()
        mock_crawler_cls.return_value = instance
        instance.run.return_value = ("<html>ok</html>", None, None)

        mock_process.exec_cmd.side_effect = [
            ("http://link1\ttitle1\n", None),  # capture
            ("http://link1\ttitle1\n", None),  # custom script
        ]
        mock_which.return_value = "/home/user/my_script.py"

        result = self.collector._compose_url_list()
        self.assertEqual(len(result), 1)
        # Custom path -> command includes -f flag
        calls = mock_process.exec_cmd.call_args_list
        self.assertIn("-f", calls[1][0][0])

    @patch("bin.new_list_collector.which")
    @patch("bin.new_list_collector.Process")
    @patch("bin.new_list_collector.Crawler")
    def test_post_process_script_fails(self, mock_crawler_cls, mock_process, mock_which) -> None:
        """post_process_script fails -> line 86-87, then empty split -> 93-94"""
        self.collection_conf["post_process_script_list"] = ["failing_script.py"]
        instance = MagicMock()
        mock_crawler_cls.return_value = instance
        instance.run.return_value = ("<html>ok</html>", None, None)

        mock_process.exec_cmd.side_effect = [
            ("http://link1\ttitle1\n", None),  # capture
            ("", "post process error"),  # post_process fails
        ]
        mock_which.return_value = None

        result = self.collector._compose_url_list()
        self.assertEqual(result, [])

    @patch("bin.new_list_collector.Process")
    @patch("bin.new_list_collector.Crawler")
    def test_empty_result_list(self, mock_crawler_cls, mock_process) -> None:
        """All URLs yield nothing -> empty result_list -> line 93-94"""
        self.collection_conf["list_url_list"] = []
        result = self.collector._compose_url_list()
        self.assertEqual(result, [])


class TestSaveNewListToFileExtended(unittest.TestCase):
    """_save_new_list_to_file: IOError -> line 104-106"""

    def test_ioerror_calls_sys_exit(self) -> None:
        feed_dir = Path("/tmp/test_feed")
        collector = NewlistCollector(feed_dir, {}, Path("/nonexistent/dir/file.txt"))
        with self.assertRaises(SystemExit):
            collector._save_new_list_to_file([("http://link", "title", [])])
        del collector


class TestCollectExtended(unittest.TestCase):
    """collect: returns empty when _compose_url_list returns [] -> line 117"""

    def test_collect_returns_empty(self) -> None:
        feed_dir = Path("/tmp/test_feed")
        collector = NewlistCollector(feed_dir, {"list_url_list": [], "item_capture_script": "./capture.py"}, feed_dir / "new_list.txt")
        with patch.object(collector, "_compose_url_list", return_value=[]):
            result = collector.collect()
            self.assertEqual(result, [])
        del collector


if __name__ == "__main__":
    unittest.main()
