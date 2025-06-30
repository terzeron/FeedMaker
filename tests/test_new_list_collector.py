#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
from unittest.mock import patch, call, MagicMock
import logging.config
from pathlib import Path
import os

from bin.feed_maker_util import Config
from bin.new_list_collector import NewlistCollector

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class NewlistCollectorTest(unittest.TestCase):
    def setUp(self) -> None:
        # 테스트용 작업 디렉토리를 tests 디렉토리로 설정
        work_dir_path = Path(__file__).parent
        config = Config(feed_dir_path=work_dir_path)
        self.collection_conf = config.get_collection_configs()
        self.collector = NewlistCollector(work_dir_path, self.collection_conf, work_dir_path / "temp_list.txt")

    def tearDown(self) -> None:
        self.collector.new_list_file_path.unlink(missing_ok=True)
        del self.collector
        del self.collection_conf

    def test_split_result_into_items(self) -> None:
        # without newline
        input_str1 = "https://url1\tworld\nhttps://url2\tcoffee"
        actual = NewlistCollector.split_result_into_items(input_str1)
        expected1 = [("https://url1", "world"), ("https://url2", "coffee")]
        self.assertEqual(expected1, actual)

        # normal input
        test_input = '''
https://cartoon.media.daum.net/webtoon/view/dontgiveheart\t그 책에 마음을 주지 마세요
https://cartoon.media.daum.net/webtoon/view/haksajaeseng\t학사재생
https://cartoon.media.daum.net/webtoon/view/exchangerate\t환율이 바뀌었나요?
https://cartoon.media.daum.net/webtoon/view/mujigaebridge\t무지개다리 파수꾼
'''
        actual = self.collector.split_result_into_items(test_input)
        self.assertEqual(4, len(actual))
        for item in actual:
            self.assertEqual(2, len(item))

        # abnormal input
        test_input = '''
https://cartoon.media.daum.net/webtoon/view/dontgiveheart\t그 책에 마음을 주지 마세요
https://cartoon.media.daum.net/webtoon/view/haksajaeseng\t
https://cartoon.media.daum.net/webtoon/view/exchangerate
https://cartoon.media.daum.net/webtoon/view/mujigaebridge\t무지개다리 파수꾼
'''
        with patch.object(LOGGER, "error") as mock_error:
            actual = self.collector.split_result_into_items(test_input)
            self.assertEqual(0, len(actual))

            args_list = mock_error.call_args_list
            expected = call(
                "Error: Can't split a line into link and title, line='%s'", 'https://cartoon.media.daum.net/webtoon/view/haksajaeseng')
            self.assertIn(expected, args_list)

    @patch('bin.new_list_collector.Crawler')
    @patch('bin.new_list_collector.Process')
    def test_compose_url_list(self, mock_process, mock_crawler) -> None:
        # Mock crawler response
        mock_crawler_instance = MagicMock()
        mock_crawler.return_value = mock_crawler_instance
        mock_crawler_instance.run.return_value = (
            '<strong class="title"><a href="/entry.naver?docId=123">테스트 제목 1</a></strong>',
            None,
            None
        )

        # Mock process response
        mock_process.exec_cmd.return_value = (
            'https://terms.naver.com/entry.naver?docId=123\t테스트 제목 1\n'
            'https://terms.naver.com/entry.naver?docId=456\t테스트 제목 2\n'
            'https://terms.naver.com/entry.naver?docId=789\t테스트 제목 3\n'
            'https://terms.naver.com/entry.naver?docId=012\t테스트 제목 4\n'
            'https://terms.naver.com/entry.naver?docId=345\t테스트 제목 5\n',
            None
        )

        actual = self.collector._compose_url_list()
        self.assertGreaterEqual(len(actual), 5)
        self.assertEqual(len(actual[0]), 2)

    @staticmethod
    def count_tsv_file(tsv_file_path: Path) -> tuple[int, int]:
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

    def test_save_new_list_to_file(self) -> None:
        new_list: list[tuple[str, str]] = [
            ("http://cartoon.media.daum.net/webtoon/view/dontgiveheart", "그 책에 마음을 주지 마세요"),
            ("http://cartoon.media.daum.net/webtoon/view/mujigaebridge", "무지개다리 파수꾼")
        ]
        self.collector._save_new_list_to_file(new_list)
        if self.collector.new_list_file_path.is_file():
            num_lines, num_items = NewlistCollectorTest.count_tsv_file(self.collector.new_list_file_path)
            self.assertEqual(3, num_lines)
            self.assertEqual(2, num_items)
        else:
            self.fail()

    @patch('bin.new_list_collector.Crawler')
    @patch('bin.new_list_collector.Process')
    def test_collect(self, mock_process, mock_crawler) -> None:
        # Mock crawler response
        mock_crawler_instance = MagicMock()
        mock_crawler.return_value = mock_crawler_instance
        mock_crawler_instance.run.return_value = (
            '<strong class="title"><a href="/entry.naver?docId=123">테스트 제목 1</a></strong>',
            None,
            None
        )

        # Mock process response
        mock_process.exec_cmd.return_value = (
            'https://terms.naver.com/entry.naver?docId=123\t테스트 제목 1\n'
            'https://terms.naver.com/entry.naver?docId=456\t테스트 제목 2\n'
            'https://terms.naver.com/entry.naver?docId=789\t테스트 제목 3\n'
            'https://terms.naver.com/entry.naver?docId=012\t테스트 제목 4\n'
            'https://terms.naver.com/entry.naver?docId=345\t테스트 제목 5\n'
            'https://terms.naver.com/entry.naver?docId=678\t테스트 제목 6\n'
            'https://terms.naver.com/entry.naver?docId=901\t테스트 제목 7\n'
            'https://terms.naver.com/entry.naver?docId=234\t테스트 제목 8\n'
            'https://terms.naver.com/entry.naver?docId=567\t테스트 제목 9\n'
            'https://terms.naver.com/entry.naver?docId=890\t테스트 제목 10\n',
            None
        )

        actual = self.collector.collect()
        self.assertGreaterEqual(len(actual), 5)
        self.assertEqual(len(actual[0]), 2)
        if self.collector.new_list_file_path.is_file():
            num_lines, num_items = NewlistCollectorTest.count_tsv_file(self.collector.new_list_file_path)
            self.assertGreaterEqual(num_lines, 10)
            self.assertGreaterEqual(num_items, 10)
        else:
            self.fail()


if __name__ == "__main__":
    unittest.main()
