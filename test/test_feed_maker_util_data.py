#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import logging.config
from pathlib import Path
from bin.feed_maker_util import Data

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class DataTest(unittest.TestCase):
    def test_remove_duplicates(self) -> None:
        input_data = ["3", "a", "b", "1", "d", "d", "b", "c", "3", "2", "1"]
        expected = ["3", "a", "b", "1", "d", "c", "2"]
        actual = Data.remove_duplicates(input_data)
        self.assertEqual(expected, actual)

    def test_remove_duplicates_with_list_of_list(self) -> None:
        input_data = [[1, 2, 3], [4, 5, 6], [1, 2, 3]]
        expected = [[1, 2, 3], [4, 5, 6]]
        actual = Data.remove_duplicates(input_data)  # type: ignore
        self.assertEqual(expected, actual)

    def test_remove_duplicates_with_list_of_dict(self) -> None:
        input_data = [{"a":[1,2,3]}, {"a":[3,4,5]}, {"a":[4,5,6]}, {"a":[1,2,3]}]
        expected = [{"a":[1,2,3]}, {"a":[3,4,5]}, {"a":[4,5,6]}]
        actual = Data.remove_duplicates(input_data)  # type: ignore
        self.assertEqual(expected, actual)

    def test_get_sorted_lines_from_rss_file(self) -> None:
        file_path = Path(__file__).parent / "sportsdonga.webtoon.1.result.xml"
        expected = sorted([
            '<rss version="2.0"',
            ' xmlns:blogChannel="http://backend.userland.com/blogChannelModule"',
            '>',
            '스포츠동아웹툰목록',
            'https://terzeron.com/sports_donga_webtoon.xml',
            'Copyright sports.donga.com. All Rights Reserved',
            "Terzeron's Feed Generator",

            '클로저 이상용',
            'http://sports.donga.com/cartoon?cid=0100000204',
            'http://sports.donga.com/cartoon?cid=0100000204',

            '돌직구',
            'http://sports.donga.com/cartoon?cid=0100000202',
            'http://sports.donga.com/cartoon?cid=0100000202',
        ])
        actual = Data._get_sorted_lines_from_rss_file(file_path)
        self.assertEqual(expected, actual)

    def test_compare_two_rss_files(self) -> None:
        file_path = Path(__file__).parent / "sportsdonga.webtoon.1.result.xml"
        file_different_path = Path(__file__).parent / "sportsdonga.webtoon.2.result.xml"
        file_with_only_different_date = Path(__file__).parent / "sportsdonga.webtoon.3.result.xml"
        actual = Data.compare_two_rss_files(file_path, file_different_path)
        self.assertFalse(actual)
        actual = Data.compare_two_rss_files(file_path, file_with_only_different_date)
        self.assertTrue(actual)


if __name__ == "__main__":
    unittest.main()
