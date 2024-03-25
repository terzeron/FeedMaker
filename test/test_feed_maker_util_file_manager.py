#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import re
import shutil
import unittest
from unittest.mock import patch, call
from io import StringIO
import logging.config
from typing import List, Any
from datetime import datetime
from pathlib import Path
from shutil import which
import subprocess
from bs4 import BeautifulSoup
from bin.feed_maker_util import Config, URL, HTMLExtractor, Datetime, Process, IO, Data, FileManager, PathUtil

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

def assert_in_mock_logger(message: str, mock_logger, do_submatch: bool = False) -> bool:
    for mock_call in mock_logger.call_args_list:
        formatted_message = mock_call.args[0] % mock_call.args[1:]
        if do_submatch:
            if message in formatted_message:
                return True
        else:
            if formatted_message == message:
                return True
    return False


class FileManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        group_name = "naver"
        feed_name = "certain_webtoon"
        self.feed_dir_path = Path(os.environ["FM_WORK_DIR"]) / group_name / feed_name
        self.feed_dir_path.mkdir(exist_ok=True)
        self.sample_conf_file_path = Path(__file__).parent / "conf.naverwebtoon.json"
        self.conf_file_path = self.feed_dir_path / "conf.json"
        shutil.copy(self.sample_conf_file_path, self.conf_file_path)

        self.rss_file_path = self.feed_dir_path / f"{feed_name}.xml"
        self.rss_file_path.touch()
        self.old_rss_file_path = self.rss_file_path.with_suffix(self.rss_file_path.suffix + ".old")
        self.old_rss_file_path.touch()
        self.start_index_file_path = self.feed_dir_path / "start_idx.txt"
        self.start_index_file_path.touch()
        self.garbage_file_path = self.feed_dir_path / "nohup.out"
        self.garbage_file_path.touch()

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

        self.feed_img_dir_path: Path = Path(os.environ["WEB_SERVICE_FEEDS_DIR"]) / "img" / feed_name
        self.feed_img_dir_path.mkdir(exist_ok=True)
        self.empty_img_file_path = self.feed_img_dir_path / "empty.png"
        self.empty_img_file_path.touch()

    def tearDown(self) -> None:
        self.garbage_file_path.unlink(missing_ok=True)

        self.html_file1_path.unlink(missing_ok=True)
        self.html_file2_path.unlink(missing_ok=True)
        shutil.rmtree(self.html_dir_path)

        self.empty_img_file_path.unlink(missing_ok=True)

    def test__get_cache_info_common_postfix(self):
        img_url = "https://image-comic.pstatic.net/webtoon/759457/50/20211007123156_e8e0d3210b1b5222a92a0d12de7068b3_IMAG01_1.jpg"
        actual = FileManager._get_cache_info_common_postfix(img_url)
        expected = "e7e0b83"
        self.assertEqual(expected, actual)

        actual = FileManager._get_cache_info_common_postfix(img_url, postfix="part")
        expected = "e7e0b83_part"
        self.assertEqual(expected, actual)

        actual = FileManager._get_cache_info_common_postfix(img_url, postfix="part", index=0)
        expected = "e7e0b83_part"
        self.assertEqual(expected, actual)

        actual = FileManager._get_cache_info_common_postfix(img_url, postfix="part", index=1)
        expected = "e7e0b83_part.1"
        self.assertEqual(expected, actual)

    def test_get_cache_url(self):
        url_prefix = "https://terzeron.com/xml/img/test"
        img_url = "https://image-comic.pstatic.net/webtoon/759457/50/20211007123156_e8e0d3210b1b5222a92a0d12de7068b3_IMAG01_1.jpg"
        actual = FileManager.get_cache_url(url_prefix, img_url)
        expected = "https://terzeron.com/xml/img/test/e7e0b83"
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_url(url_prefix, img_url, postfix="part")
        expected = "https://terzeron.com/xml/img/test/e7e0b83_part"
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_url(url_prefix, img_url, postfix="part", index=0)
        expected = "https://terzeron.com/xml/img/test/e7e0b83_part"
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_url(url_prefix, img_url, postfix="part", index=1)
        expected = "https://terzeron.com/xml/img/test/e7e0b83_part.1"
        self.assertEqual(expected, actual)

    def test_get_cache_file_path(self):
        img_url = "https://image-comic.pstatic.net/webtoon/759457/50/20211007123156_e8e0d3210b1b5222a92a0d12de7068b3_IMAG01_1.jpg"
        actual = FileManager.get_cache_file_path(self.feed_img_dir_path, img_url)
        expected = self.feed_img_dir_path / "e7e0b83"
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_file_path(self.feed_img_dir_path, img_url, postfix="part")
        expected = self.feed_img_dir_path / "e7e0b83_part"
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_file_path(self.feed_img_dir_path, img_url, postfix="part", index=0)
        expected = self.feed_img_dir_path / "e7e0b83_part"
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_file_path(self.feed_img_dir_path, img_url, postfix="part", index=1)
        expected = self.feed_img_dir_path / "e7e0b83_part.1"
        self.assertEqual(expected, actual)

    def test_get_incomplete_image(self):
        expected = ["567890a.png"]
        actual = FileManager.get_incomplete_image_list(self.html_file2_path)
        self.assertEqual(expected, actual)

    def test_remove_html_file_without_cached_image_files(self):
        self.assertTrue(self.html_file2_path.is_file())
        with patch.object(LOGGER, "info") as mock_info:
            FileManager.remove_html_file_without_cached_image_files(self.html_file2_path)
            self.assertTrue(assert_in_mock_logger("* 'naver/certain_webtoon/html/1234567.html' deleted (due to ['567890a.png'])", mock_info, do_submatch=True))

        self.assertFalse(self.html_file2_path.is_file())

    def test_remove_html_files_without_cached_image_files(self):
        self.assertTrue(self.html_file2_path.is_file())
        with patch.object(LOGGER, "info") as mock_info:
            FileManager.remove_html_files_without_cached_image_files(self.feed_dir_path, self.feed_img_dir_path)
            self.assertTrue(assert_in_mock_logger("# deleting html files without cached image files", mock_info))
            self.assertTrue(assert_in_mock_logger("* 'naver/certain_webtoon/html/1234567.html' deleted (due to ['567890a.png'])", mock_info, do_submatch=True))

        self.assertFalse(self.html_file2_path.is_file())

    def test_remove_temporary_files(self):
        self.assertTrue(self.garbage_file_path.is_file())
        with patch.object(LOGGER, "info") as _:
            FileManager.remove_temporary_files(self.feed_dir_path)

        self.assertFalse(self.garbage_file_path.is_file())

    def test_remove_all_files(self):
        self.assertTrue(self.rss_file_path.is_file())
        self.assertTrue(self.start_index_file_path.is_file())
        self.assertTrue(self.garbage_file_path.is_file())
        self.assertTrue(self.list_file_path.is_file())
        self.assertTrue(self.html_file1_path.is_file())

        with patch.object(LOGGER, "info") as mock_info:
            FileManager.remove_all_files(self.feed_dir_path)

            self.assertTrue(assert_in_mock_logger("# deleting all files (html files, list files, rss file, various temporary files)", mock_info))
            self.assertTrue(assert_in_mock_logger("# deleting temporary files", mock_info))

        self.assertFalse(self.rss_file_path.is_file())
        self.assertFalse(self.start_index_file_path.is_file())
        self.assertFalse(self.garbage_file_path.is_file())
        self.assertFalse(self.list_file_path.is_file())
        self.assertFalse(self.html_file1_path.is_file())


if __name__ == "__main__":
    unittest.main()
