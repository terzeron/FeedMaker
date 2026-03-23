#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
from unittest.mock import patch, call, MagicMock
import logging.config
from pathlib import Path
import os

from bin.feed_maker_util import Config
from bin.new_list_collector import NewlistCollector
from unittest.mock import patch, MagicMock

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
        expected1 = [("https://url1", "world", []), ("https://url2", "coffee", [])]
        self.assertEqual(expected1, actual)

        input_str2 = "https://url1\tworld\tmusic\t3\nhttps://url2\tcoffee\tbook\t4"
        actual = NewlistCollector.split_result_into_items(input_str2)
        expected1 = [("https://url1", "world", ["music", "3"]), ("https://url2", "coffee", ["book", "4"])]
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
            self.assertEqual(3, len(item))

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
        self.assertEqual(len(actual[0]), 3)

    @staticmethod
    def count_tsv_file(tsv_file_path: Path) -> tuple[int, int]:
        num_items = 0
        with tsv_file_path.open("r", encoding="utf-8") as infile:
            data = infile.read()
            line_list = data.split("\n")
            num_lines = len(line_list)
            for line in line_list:
                if "\t" in line:
                    link, title, _ = line.split("\t")
                    if link and title:
                        num_items += 1
        return num_lines, num_items

    def test_save_new_list_to_file(self) -> None:
        new_list: list[tuple[str, str, list[str]]] = [
            ("http://cartoon.media.daum.net/webtoon/view/dontgiveheart", "그 책에 마음을 주지 마세요", []),
            ("http://cartoon.media.daum.net/webtoon/view/mujigaebridge", "무지개다리 파수꾼", [])
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
        self.assertEqual(len(actual[0]), 3)
        if self.collector.new_list_file_path.is_file():
            num_lines, num_items = NewlistCollectorTest.count_tsv_file(self.collector.new_list_file_path)
            self.assertGreaterEqual(num_lines, 10)
            self.assertGreaterEqual(num_items, 10)
        else:
            self.fail()


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
