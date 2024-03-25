#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import shutil
import logging.config
import unittest
from unittest.mock import patch, call
from pathlib import Path
from typing import Any
from bin.run import FeedMakerRunner

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


class TestFeedMakerRunner(unittest.TestCase):
    def setUp(self) -> None:
        group_name = "naver"
        feed_name = "certain_webtoon"

        self.runner = FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)

        self.feed_dir_path = Path(os.environ["FM_WORK_DIR"]) / group_name / feed_name
        self.feed_dir_path.mkdir(exist_ok=True)

        self.list_dir_path = self.feed_dir_path / "newlist"
        self.list_dir_path.mkdir(exist_ok=True)

        # prepare conf.json from conf.naverwebtoon.json
        self.sample_conf_file_path = Path(__file__).parent / "conf.naverwebtoon.json"
        self.conf_file_path = self.feed_dir_path / "conf.json"
        shutil.copy(self.sample_conf_file_path, self.conf_file_path)

    def tearDown(self) -> None:
        self.conf_file_path.unlink(missing_ok=True)
        shutil.rmtree(self.list_dir_path)
        shutil.rmtree(self.feed_dir_path)
        del self.runner

    def test_make_single_feed(self):
        # with -c
        options = {"force_collection_opt": "-c"}
        with patch.object(LOGGER, "warning") as mock_warning:
            with patch.object(LOGGER, "info") as mock_info:
                actual = self.runner.make_single_feed(self.feed_dir_path, options)
                self.assertTrue(actual)

                self.assertTrue(assert_in_mock_logger("Warning: can't read old feed list from files", mock_warning))
                self.assertTrue(assert_in_mock_logger("* naver/certain_webtoon", mock_info))
                self.assertTrue(assert_in_mock_logger("Appending 1 new items to the feed list", mock_info))

        # without -c
        options = {}
        with patch.object(LOGGER, "info") as mock_info:
            actual = self.runner.make_single_feed(self.feed_dir_path, options)
            self.assertTrue(actual)

            self.assertTrue(assert_in_mock_logger("* naver/certain_webtoon", mock_info))
            self.assertTrue(assert_in_mock_logger("Appending 1 old items to the feed list", mock_info))
            self.assertTrue(assert_in_mock_logger("Generating rss feed file...", mock_info))
            # self.assertTrue(assert_in_mock_logger("upload success!", mock_info))

    def test_make_all_feeds(self):
        with patch.object(LOGGER, "info") as mock_info:
            options = {"num_feeds": 1}
            actual = self.runner.make_all_feeds(options)
            self.assertTrue(actual)

            self.assertTrue(assert_in_mock_logger("# Generating feeds", mock_info))
            self.assertTrue(assert_in_mock_logger("# deleting html files without cached image files", mock_info))
            self.assertTrue(assert_in_mock_logger("# deleting image files with zero size", mock_info))


if __name__ == "__main__":
    unittest.main()
