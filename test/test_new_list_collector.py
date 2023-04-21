#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
import unittest
from unittest.mock import patch, call
import logging.config
from pathlib import Path
from typing import List, Tuple
from feed_maker_util import Config
from new_list_collector import NewListCollector

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class NewListCollectorTest(unittest.TestCase):
    def setUp(self):
        work_dir_path = Path.cwd()
        config = Config(feed_dir_path=work_dir_path)
        if not config:
            LOGGER.error("can't get configuration")
            sys.exit(-1)
        self.collection_conf = config.get_collection_configs()
        if not self.collection_conf:
            LOGGER.error("can't get collection configuration")
            sys.exit(-1)

        self.collector = NewListCollector(work_dir_path, self.collection_conf, work_dir_path / "temp_list.txt")

    def tearDown(self):
        self.collector.new_list_file_path.unlink(missing_ok=True)
        del self.collector
        del self.collection_conf

    def test_split_result_into_items(self):
        # without newline
        input_str1 = "https://url1\tworld\nhttps://url2\tcoffee"
        actual = NewListCollector.split_result_into_items(input_str1)
        expected1 = [("https://url1", "world"), ("https://url2", "coffee")]
        self.assertEqual(expected1, actual)

        # normal input
        test_input = '''
http://cartoon.media.daum.net/webtoon/view/dontgiveheart\t그 책에 마음을 주지 마세요
http://cartoon.media.daum.net/webtoon/view/haksajaeseng\t학사재생
http://cartoon.media.daum.net/webtoon/view/exchangerate\t환율이 바뀌었나요?
http://cartoon.media.daum.net/webtoon/view/mujigaebridge\t무지개다리 파수꾼
'''
        actual = self.collector.split_result_into_items(test_input)
        self.assertEqual(4, len(actual))
        for item in actual:
            self.assertEqual(2, len(item))

        # abnormal input
        test_input = '''
http://cartoon.media.daum.net/webtoon/view/dontgiveheart\t그 책에 마음을 주지 마세요
http://cartoon.media.daum.net/webtoon/view/haksajaeseng\t
http://cartoon.media.daum.net/webtoon/view/exchangerate
http://cartoon.media.daum.net/webtoon/view/mujigaebridge\t무지개다리 파수꾼
'''
        with patch.object(LOGGER, "error") as mock_error:
            actual = self.collector.split_result_into_items(test_input)
            self.assertEqual(0, len(actual))

            args_list = mock_error.call_args_list
            expected = call(
                "Error: Can't split a line into link and title, line='http://cartoon.media.daum.net/webtoon/view/haksajaeseng'")
            self.assertIn(expected, args_list)

    def test_compose_url_list(self):
        actual = self.collector._compose_url_list()
        self.assertGreaterEqual(len(actual), 5)
        self.assertEqual(len(actual[0]), 2)

    @staticmethod
    def count_tsv_file(tsv_file_path: Path):
        num_items = 0
        with tsv_file_path.open("r", encoding="utf-8") as infile:
            data = infile.read()
            line_list = data.split("\n")
            num_lines = len(line_list)
            for line in line_list:
                if "\t" in line:
                    link, title = line.split("\t")
                    if link and title:
                        num_items += 1
        return num_lines, num_items

    def test_save_new_list_to_file(self):
        new_list: List[Tuple[str, str]] = [
            ("http://cartoon.media.daum.net/webtoon/view/dontgiveheart", "그 책에 마음을 주지 마세요"),
            ("http://cartoon.media.daum.net/webtoon/view/mujigaebridge", "무지개다리 파수꾼")
        ]
        self.collector._save_new_list_to_file(new_list)
        if self.collector.new_list_file_path.is_file():
            num_lines, num_items = NewListCollectorTest.count_tsv_file(self.collector.new_list_file_path)
            self.assertEqual(3, num_lines)
            self.assertEqual(2, num_items)
        else:
            self.fail()

    def test_collect(self):
        actual = self.collector.collect()
        self.assertGreaterEqual(len(actual), 5)
        self.assertEqual(len(actual[0]), 2)
        if self.collector.new_list_file_path.is_file():
            num_lines, num_items = NewListCollectorTest.count_tsv_file(self.collector.new_list_file_path)
            self.assertGreaterEqual(num_lines, 10)
            self.assertGreaterEqual(num_items, 10)
        else:
            self.fail()


if __name__ == "__main__":
    unittest.main()
