#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import shutil
import logging.config
import unittest
from unittest.mock import patch, call
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from run import FeedMakerRunner

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


def assert_in_mock_logger(param: Any, mock_logger, do_submatch: bool = False) -> bool:
    for arg in mock_logger.call_args_list:
        if do_submatch:
            if param in arg.args[0]:
                return True
        else:
            if call(param) == arg:
                return True
    return False


class TestFeedMakerRunner(unittest.TestCase):
    def setUp(self) -> None:
        group_name = "naver"
        feed_name = "oneplusone"

        self.runner = FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)

        self.feed_dir_path = Path(os.environ["FEED_MAKER_WORK_DIR"]) / group_name / feed_name
        self.feed_dir_path.mkdir(exist_ok=True)
        self.garbage_file_path = self.feed_dir_path / "nohup.out"
        self.garbage_file_path.touch()
        self.rss_file_path = self.feed_dir_path / (feed_name + ".xml")
        self.rss_file_path.touch()
        self.old_rss_file_path = self.rss_file_path.with_suffix(self.rss_file_path.suffix + ".old")
        self.old_rss_file_path.touch()
        self.start_idx_file_path = self.feed_dir_path / "start_idx.txt"
        self.start_idx_file_path.touch()

        self.list_dir_path = self.feed_dir_path / "newlist"
        self.list_dir_path.mkdir(exist_ok=True)
        self.list_file_path = self.list_dir_path / "20211108.txt"
        self.list_file_path.touch()

        self.html_dir_path = self.feed_dir_path / "html"
        self.html_dir_path.mkdir(exist_ok=True)
        self.html_file1_path = self.html_dir_path / "0abcdef.html"
        self.html_file1_path.touch()
        self.html_file2_path = self.html_dir_path / "1234567.html"
        with open(self.html_file2_path, "w", encoding="utf-8") as outfile:
            outfile.write(f"<img src='https://terzeron.com/xml/img/{feed_name}/567890a.png'/>\n")

        self.feed_img_dir_path = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"]) / "img" / feed_name
        self.feed_img_dir_path.mkdir(exist_ok=True)
        # add a file for this feed
        self.empty_img_file_path = self.feed_img_dir_path / "empty.png"
        self.empty_img_file_path.touch()

        self.sample_conf_file_path = Path.cwd() / "test" / "conf.naverwebtoon.json"
        self.conf_file_path = self.feed_dir_path / "conf.json"
        shutil.copy(self.sample_conf_file_path, self.conf_file_path)

    def tearDown(self) -> None:
        self.conf_file_path.unlink(missing_ok=True)

        self.empty_img_file_path.unlink(missing_ok=True)

        self.list_file_path.unlink(missing_ok=True)
        shutil.rmtree(self.list_dir_path)
        self.html_file1_path.unlink(missing_ok=True)
        self.html_file2_path.unlink(missing_ok=True)
        shutil.rmtree(self.html_dir_path)

        self.start_idx_file_path.unlink(missing_ok=True)
        self.old_rss_file_path.unlink(missing_ok=True)
        self.rss_file_path.unlink(missing_ok=True)
        self.garbage_file_path.unlink(missing_ok=True)
        shutil.rmtree(self.feed_dir_path)

        del self.runner

    def test_1_get_img_set_in_img_dir(self):
        actual = self.runner._get_img_set_in_img_dir(self.feed_img_dir_path)
        expected = self.empty_img_file_path.relative_to(self.feed_img_dir_path).name
        self.assertIn(expected, actual)

    def test_2_remove_image_files_with_zero_size(self):
        with patch.object(LOGGER, "info") as mock_info:
            self.runner._remove_image_files_with_zero_size(self.feed_img_dir_path)
            actual = self.runner._get_img_set_in_img_dir(self.feed_img_dir_path)
            expected = self.empty_img_file_path.relative_to(self.feed_img_dir_path).name
            self.assertNotIn(expected, actual)

            self.assertTrue(assert_in_mock_logger("# deleting image files with zero size", mock_info))

    def test_3_remove_old_html_files(self):
        with patch.object(LOGGER, "info") as mock_info:
            self.runner._remove_old_html_files(self.feed_dir_path)
            do_exist = False
            for html_file_path in self.html_dir_path.iterdir():
                if html_file_path.is_file():
                    ctime = datetime.fromtimestamp(html_file_path.stat().st_ctime)
                    if ctime + timedelta(days=self.runner.html_archiving_period) < datetime.now():
                        do_exist = True
                        break
            self.assertFalse(do_exist)

            self.assertTrue(assert_in_mock_logger("# deleting old html files", mock_info))

    def test_4_remove_html_files_without_cached_image_files(self):
        self.assertTrue(self.html_file2_path.is_file())

        with patch.object(LOGGER, "info") as mock_info:
            self.runner._remove_html_files_without_cached_image_files(self.feed_dir_path, self.feed_img_dir_path)
            self.assertFalse(self.html_file2_path.is_file())

            self.assertTrue(assert_in_mock_logger("# deleting html files without cached image files", mock_info))
            self.assertTrue(assert_in_mock_logger("* '1234567.html' (due to '567890a.png')", mock_info))

    def test_5_remove_temporary_files(self):
        self.assertTrue(self.garbage_file_path.is_file())

        with patch.object(LOGGER, "info") as _:
            self.runner._remove_temporary_files(self.feed_dir_path)

        self.assertFalse(self.garbage_file_path.is_file())

    def test_6_remove_all_files(self):
        self.assertTrue(self.garbage_file_path.is_file())
        self.assertTrue(self.rss_file_path.is_file())
        self.assertTrue(self.list_file_path.is_file())
        self.assertTrue(self.html_file1_path.is_file())
        self.assertTrue(self.start_idx_file_path.is_file())

        with patch.object(LOGGER, "info") as mock_info:
            self.runner._remove_all_files(self.feed_dir_path, self.rss_file_path)

            self.assertTrue(assert_in_mock_logger(
                "# deleting all files (html files, list files, rss file, various temporary files)", mock_info))
            self.assertTrue(assert_in_mock_logger("# deleting temporary files", mock_info))

        self.assertFalse(self.garbage_file_path.is_file())
        self.assertFalse(self.rss_file_path.is_file())
        self.assertFalse(self.list_file_path.is_file())
        self.assertFalse(self.html_file1_path.is_file())
        self.assertFalse(self.start_idx_file_path.is_file())

    def test_make_single_feed(self):
        # with -c
        options = {"force_collection_opt": "-c"}
        with patch.object(LOGGER, "warning") as mock_warning:
            with patch.object(LOGGER, "info") as mock_info:
                actual = self.runner.make_single_feed(self.feed_dir_path, options)
                self.assertTrue(actual)

                self.assertTrue(assert_in_mock_logger("Warning: can't read old feed list from files", mock_warning))
                self.assertTrue(assert_in_mock_logger("* naver/oneplusone", mock_info))
                self.assertTrue(assert_in_mock_logger("Appending 1 new items to the feed list", mock_info))

        # without -c
        options = {}
        with patch.object(LOGGER, "info") as mock_info:
            actual = self.runner.make_single_feed(self.feed_dir_path, options)
            self.assertTrue(actual)

            self.assertTrue(assert_in_mock_logger("* naver/oneplusone", mock_info))
            self.assertTrue(assert_in_mock_logger("Appending 1 old items to the feed list", mock_info))
            self.assertTrue(assert_in_mock_logger("Generating rss feed file...", mock_info))
            self.assertTrue(assert_in_mock_logger("upload success!", mock_info))


def test_make_all_feeds(self):
    with patch.object(LOGGER, "warning") as mock_warning:
        with patch.object(LOGGER, "info") as mock_info:
            actual = self.runner.make_all_feeds(num_feeds=1)
            self.assertTrue(actual)

            self.assertTrue(assert_in_mock_logger("Warning: can't read old feed list from files", mock_warning))
            self.assertTrue(assert_in_mock_logger("# Running time analysis", mock_info))


if __name__ == "__main__":
    unittest.main()
