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


def assert_in_mock_logger(param: Any, mock_logger, do_submatch: bool = False) -> bool:
    for arg in mock_logger.call_args_list:
        if do_submatch:
            if param in arg.args[0]:
                return True
        else:
            if call(param) == arg:
                return True
    return False


class DataTest(unittest.TestCase):
    def test_remove_duplicates(self):
        input_data = ["3", "a", "b", "1", "d", "d", "b", "c", "3", "2", "1"]
        expected = ["3", "a", "b", "1", "d", "c", "2"]
        actual = Data.remove_duplicates(input_data)
        self.assertEqual(expected, actual)

    def test_get_sorted_lines_from_rss_file(self):
        file_path = Path(__file__).parent / "sportsdonga.webtoon.1.result.xml"
        expected = sorted([
            '<rss version="2.0"',
            ' xmlns:blogChannel="http://backend.userland.com/blogChannelModule"',
            '>',
            '스포츠동아웹툰목록',
            'https://terzeron.com/oneplusone.xml',
            '스포츠동아웹툰목록 - 모바일 버전 RSS Feed',
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

    def test_compare_two_rss_files(self):
        file_path = Path(__file__).parent / "sportsdonga.webtoon.1.result.xml"
        file_different_path = Path(__file__).parent / "sportsdonga.webtoon.2.result.xml"
        file_with_only_different_date = Path(__file__).parent / "sportsdonga.webtoon.3.result.xml"
        actual = Data.compare_two_rss_files(file_path, file_different_path)
        self.assertFalse(actual)
        actual = Data.compare_two_rss_files(file_path, file_with_only_different_date)
        self.assertTrue(actual)


class ProcessTest(unittest.TestCase):
    def test_replace_script_path(self):
        cmd = "shuf"
        # OS마다 shuf가 설치된 경로가 다를 수 있음
        real_program_path = which("shuf")
        expected = real_program_path
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "/usr/bin/tail -5"
        # 어떤 디렉토리에서 실행하든 /usr/bin/tail이 실행되어야 함
        expected = "/usr/bin/tail -5"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "non_existent_program arg1"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "uploader.py test.xml"
        real_program_path = which("uploader.py")
        expected = f"{real_program_path} test.xml"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "../capture_item_naverwebtoon.py -n 500"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "./capture_item_naverwebtoon.py -n 500"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "./capture_item_link_title.py"
        actual = Process._replace_script_path(cmd, Path.cwd())
        expected = str(Path.cwd() / "capture_item_link_title.py")
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

    def test_exec_cmd(self):
        valid_cmd = "ls test_feed_maker_util.py"
        actual, error = Process.exec_cmd(valid_cmd)
        self.assertTrue(actual)
        self.assertEqual(error, "")
        self.assertTrue("test_feed_maker_util.py" in actual)

        invalid_cmd = "ls non_existent_file"
        actual, error = Process.exec_cmd(invalid_cmd)
        self.assertFalse(actual)
        self.assertTrue("No such file or directory" in error)

        invalid_cmd = "lslslsls non_existent_file"
        actual, error = Process.exec_cmd(invalid_cmd)
        self.assertFalse(actual)
        self.assertTrue("Error in getting path of executable" in error)

        bidirectional_cmd = "cat"
        input_str = "hello world"
        actual, error = Process.exec_cmd(bidirectional_cmd, input_data=input_str)
        self.assertTrue(actual)
        self.assertEqual(error, "")
        self.assertTrue("hello world" in actual)

    def test_find_process_group_and_kill_process_group(self):
        with subprocess.Popen(["sleep", "20"]):
            actual = len(Process._find_process_group(r"sleep 20"))
            expected = 1
            self.assertGreaterEqual(expected, actual)

            actual = Process.kill_process_group(r"sleep 20")
            expected = 1
            self.assertGreaterEqual(expected, actual)


class DatetimeTest(unittest.TestCase):
    def test_get_current_time(self):
        # All three datetime functions may be completed in 1 seconds
        expected1 = str(datetime.now().astimezone())
        actual = str(Datetime.get_current_time())
        expected2 = str(datetime.now().astimezone())

        # YYYY-MM-DD HH:MI:SS
        e1 = expected1[:19]
        e2 = expected2[:19]
        a = actual[:19]
        self.assertIn(a, [e1, e2])

        # timezone
        expected = expected1[-6:]
        actual = actual[-6:]
        self.assertEqual(expected, actual)

    def test_get_time_str(self):
        expected = "2021-10-22T14:59:17"
        dt = datetime(2021, 10, 22, 14, 59, 17)
        actual = Datetime._get_time_str(dt)
        self.assertEqual(expected, actual)

    def test_get_current_time_str(self):
        actual = Datetime.get_current_time_str()
        m = re.search(r"^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\+\d\d:\d\d$", actual)
        self.assertTrue(m)

    def test_get_rss_date_str(self):
        actual = Datetime.get_rss_date_str()
        m = re.search(r"^(Sun|Mon|Tue|Wed|Thu|Fri|Sat), \d+ (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d\d\d\d \d\d:\d\d:\d\d \+\d\d\d\d$", actual)
        self.assertTrue(m)

    def test_get_short_date_str(self):
        expected = datetime.now().strftime("%Y%m%d")
        actual = Datetime.get_short_date_str()
        self.assertEqual(expected, actual)

        expected = "20211022"
        dt = datetime(2021, 10, 22, 14, 59, 17)
        actual = Datetime.get_short_date_str(dt)
        self.assertEqual(expected, actual)


class HTMLExtractorTest(unittest.TestCase):
    def test_get_first_token_from_path(self):
        # id, name, idx, remainder of path, isAnywhere
        actual = HTMLExtractor.get_first_token_from_path("")
        self.assertEqual((None, None, None, None, False), actual)

        actual = HTMLExtractor.get_first_token_from_path("/html/body")
        self.assertEqual((None, "body", None, "", False), actual)

        actual = HTMLExtractor.get_first_token_from_path("/html/body/div")
        self.assertEqual((None, "div", None, "", False), actual)

        actual = HTMLExtractor.get_first_token_from_path('//*[@id="Text_Contents"]')
        self.assertEqual(("Text_Contents", None, None, "", True), actual)

        actual = HTMLExtractor.get_first_token_from_path('//*[@id="Text_Contents"]/form/select')
        self.assertEqual(("Text_Contents", None, None, "form/select", True), actual)

        actual = HTMLExtractor.get_first_token_from_path('/form/select')
        self.assertEqual((None, "form", None, "select", False), actual)

        actual = HTMLExtractor.get_first_token_from_path('//select')
        self.assertEqual((None, "select", None, "", True), actual)

        actual = HTMLExtractor.get_first_token_from_path("/html/body/div[3]")
        self.assertEqual((None, "div", 3, "", False), actual)

        actual = HTMLExtractor.get_first_token_from_path("/html/body/div[3]/img[2]")
        self.assertEqual((None, "div", 3, "img[2]", False), actual)

        actual = HTMLExtractor.get_first_token_from_path("//img[2]")
        self.assertEqual((None, "img", 2, "", True), actual)

    def test_get_node_with_path(self):
        soup = BeautifulSoup('<html><body><div>hello</div><div id="ct"><span>text</span></div></body></html>', 'html.parser')

        target_node = HTMLExtractor.get_node_with_path(soup.body, '//span')
        if target_node:
            actual = target_node[0].name
            expected = "span"
            self.assertEqual(expected, actual)

            actual = target_node[0].contents[0]
            expected = "text"
            self.assertEqual(expected, actual)
        else:
            self.fail()

        target_node = HTMLExtractor.get_node_with_path(soup.body, '//*[@id="ct"]')
        if target_node:
            actual = target_node[0].name
            expected = "div"
            self.assertEqual(expected, actual)

            actual = target_node[0].contents[0].contents[0]
            expected = "text"
            self.assertEqual(expected, actual)
        else:
            self.fail()

        target_node = HTMLExtractor.get_node_with_path(soup.body, '/html/body/div')
        if target_node:
            actual = target_node[0].name
            expected = "div"
            self.assertEqual(expected, actual)

            actual = target_node[0].contents[0]
            expected = "hello"
            self.assertEqual(expected, actual)
        else:
            self.fail()

        target_node = HTMLExtractor.get_node_with_path(soup.body, '/div[2]')
        if target_node:
            actual = target_node[0].name
            expected = "div"
            self.assertEqual(expected, actual)

            actual = target_node[0].contents[0].contents[0]
            expected = "text"
            self.assertEqual(expected, actual)
        else:
            self.fail()

        target_node = HTMLExtractor.get_node_with_path(soup.body, '//*[@id="ct"]/span')
        if target_node:
            actual = target_node[0].name
            expected = "span"
            self.assertEqual(expected, actual)
            actual = target_node[0].contents[0]
            expected = "text"
            self.assertEqual(expected, actual)
        else:
            self.fail()

        target_node = HTMLExtractor.get_node_with_path(soup.body, '/div[2]/span')
        if target_node:
            actual = target_node[0].name
            expected = "span"
            self.assertEqual(expected, actual)

            actual = target_node[0].contents[0]
            expected = "text"
            self.assertEqual(expected, actual)
        else:
            self.fail()


class IOTest(unittest.TestCase):
    def test_read_stdin(self):
        expected = "test data from stdin\nsecond line from stdin\n"
        with patch("sys.stdin", StringIO("test data from stdin\nsecond line from stdin\n")):
            actual = IO.read_stdin()
            self.assertEqual(expected, actual)

    def test_read_stdin_as_line_list(self):
        expected = ["test data from stdin\n", "second line from stdin\n"]
        with patch("sys.stdin", StringIO("test data from stdin\nsecond line from stdin\n")):
            actual = IO.read_stdin_as_line_list()
            self.assertEqual(expected, actual)


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = Config(feed_dir_path=Path.cwd())
        if not self.config:
            LOGGER.error("can't get configuration")

    def tearDown(self):
        del self.config

    def test_init(self):
        actual = self.config is not None
        self.assertTrue(actual)
        actual = isinstance(self.config, Config)
        self.assertTrue(actual)

    def test_get_bool_config_value(self):
        collection_conf = self.config.conf["collection"]
        extraction_conf = self.config.conf["extraction"]

        # existent, without default
        actual = self.config._get_bool_config_value(collection_conf, "verify_ssl")
        expected = True
        self.assertEqual(expected, actual)

        # existent, with default
        actual = self.config._get_bool_config_value(collection_conf, "verify_ssl", False)
        expected = True
        self.assertEqual(expected, actual)

        # not existent, without default
        actual = self.config._get_bool_config_value(extraction_conf, "verify_ssl")
        expected = False
        self.assertEqual(expected, actual)

        # not existent, with default
        actual = self.config._get_bool_config_value(extraction_conf, "verify_ssl", False)
        expected = False
        self.assertEqual(expected, actual)

    def test_get_str_config_value(self):
        collection_conf = self.config.conf["collection"]
        extraction_conf = self.config.conf["extraction"]

        # existent, without default
        actual = self.config._get_str_config_value(collection_conf, "encoding")
        self.assertEqual("utf-8", actual)

        # existent, with default
        actual = self.config._get_str_config_value(collection_conf, "encoding", "cp949")
        self.assertEqual("utf-8", actual)

        # not existent, with default
        actual = self.config._get_str_config_value(extraction_conf, "encoding", "cp949")
        self.assertEqual("cp949", actual)

        # not existent, without default
        actual = self.config._get_str_config_value(extraction_conf, "encoding")
        self.assertIsNone(actual)

    def test_get_int_config_value(self):
        collection_conf = self.config.conf["collection"]
        extraction_conf = self.config.conf["extraction"]

        # existent, without default
        actual = self.config._get_int_config_value(extraction_conf, "timeout")
        self.assertEqual(30, actual)

        # existent, with default
        actual = self.config._get_int_config_value(extraction_conf, "timeout", 20)
        self.assertEqual(30, actual)

        # not existent, without default
        actual = self.config._get_int_config_value(collection_conf, "timeout")
        self.assertIsNone(actual)

        # not existent, with default
        actual = self.config._get_int_config_value(collection_conf, "timeout", 10)
        self.assertEqual(10, actual)

    def test_get_float_config_value(self):
        collection_conf = self.config.conf["collection"]
        extraction_conf = self.config.conf["extraction"]

        # existent, without default
        actual = self.config._get_float_config_value(collection_conf, "unit_size_per_day")
        expected = 1.5
        self.assertEqual(expected, actual)

        # existent, with default
        actual = self.config._get_float_config_value(collection_conf, "unit_size_per_day", 3.3)
        self.assertEqual(1.5, actual)

        # not existent, without default
        actual = self.config._get_float_config_value(extraction_conf, "unit_size_per_day")
        self.assertIsNone(actual)

        # not existent, with default
        actual = self.config._get_float_config_value(extraction_conf, "unit_size_per_day", 5.8)
        self.assertEqual(5.8, actual)

    def test_get_config_value_list(self):
        collection_conf = self.config.conf["collection"]
        actual = self.config._get_list_config_value(collection_conf, "list_url_list", [])
        expected = ["https://terms.naver.com/list.naver?cid=58737&categoryId=58737&page=1",
                    "https://terms.naver.com/list.naver?cid=58737&categoryId=58737&page=2"]
        self.assertEqual(expected, actual)

        actual2 = self.config._get_dict_config_value(collection_conf, "headers", {})
        self.assertEqual({}, actual2)

        actual2 = self.config._get_dict_config_value(collection_conf, "headers")
        self.assertEqual({}, actual2)

    def test_get_collection_configs(self):
        configs = self.config.get_collection_configs()
        actual = isinstance(configs, dict)
        self.assertTrue(actual)

        actual = configs["item_capture_script"]
        self.assertEqual("./capture_item_link_title.py", actual)

        actual = configs["ignore_old_list"]
        self.assertFalse(actual)

        actual = configs["sort_field_pattern"]
        self.assertIsNone(actual)

        actual = configs["unit_size_per_day"]
        self.assertEqual(1.5, actual)

        actual = configs["list_url_list"]
        expected = ["https://terms.naver.com/list.naver?cid=58737&categoryId=58737&page=1",
                    "https://terms.naver.com/list.naver?cid=58737&categoryId=58737&page=2"]
        self.assertEqual(expected, actual)

        actual = configs["post_process_script_list"]
        expected = ['shuf']
        self.assertEqual(expected, actual)

    def test_get_extraction_configs(self):
        configs = self.config.get_extraction_configs()
        actual = isinstance(configs, dict)
        self.assertTrue(actual)

        actual = configs["render_js"]
        self.assertFalse(actual)

        actual = configs["user_agent"]
        self.assertTrue(actual)

        actual = configs["element_id_list"]
        expected = ["ct", "content"]
        self.assertEqual(expected, actual)

        actual = configs["element_class_list"]
        expected = ["se_doc_viewer", "content_view"]
        self.assertEqual(expected, actual)

        actual = configs["element_path_list"]
        expected = []
        self.assertEqual(expected, actual)

        actual = configs["post_process_script_list"]
        expected = ["post_process_script_for_navercast.py"]
        self.assertEqual(expected, actual)

        actual2 = configs["headers"]
        self.assertEqual({}, actual2)

    def test_get_rss_configs(self):
        configs = self.config.get_rss_configs()
        actual = isinstance(configs, dict)
        self.assertTrue(actual)

        actual = configs["rss_title"]
        expected = "네이버캐스트 모바일"
        self.assertEqual(expected, actual)


class URLTest(unittest.TestCase):
    def test_get_url_scheme(self):
        actual = URL.get_url_scheme("http://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "http"
        self.assertEqual(expected, actual)

        actual = URL.get_url_scheme("https://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "https"
        self.assertEqual(expected, actual)

    def test_get_url_domain(self):
        actual = URL.get_url_domain("http://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "www.naver.com"
        self.assertEqual(expected, actual)

        actual = URL.get_url_domain("https://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "www.naver.com"
        self.assertEqual(expected, actual)

        actual = URL.get_url_domain("https://tkor.ws/던전-리셋")
        expected = "tkor.ws"
        self.assertEqual(expected, actual)

        actual = URL.get_url_domain("https://naver.com")
        expected = "naver.com"
        self.assertEqual(expected, actual)

    def test_get_url_path(self):
        actual = URL.get_url_path("http://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "/movie/hello/test.nhn?query=test"
        self.assertEqual(expected, actual)

        actual = URL.get_url_path("https://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "/movie/hello/test.nhn?query=test"
        self.assertEqual(expected, actual)

        actual = URL.get_url_path("https://tkor.ws/던전-리셋")
        expected = "/던전-리셋"
        self.assertEqual(expected, actual)

    def test_get_url_prefix(self):
        actual = URL.get_url_prefix("http://www.naver.com/movie")
        expected = "http://www.naver.com/"
        self.assertEqual(expected, actual)

        actual = URL.get_url_prefix("https://www.naver.com/movie")
        expected = "https://www.naver.com/"
        self.assertEqual(expected, actual)

        actual = URL.get_url_prefix("http://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "http://www.naver.com/movie/hello/"
        self.assertEqual(expected, actual)

        actual = URL.get_url_prefix("https://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "https://www.naver.com/movie/hello/"
        self.assertEqual(expected, actual)

        actual = URL.get_url_prefix("https://tkor.ws/던전-리셋")
        expected = "https://tkor.ws/"
        self.assertEqual(expected, actual)

    def test_get_url_except_query(self):
        actual = URL.get_url_except_query("http://www.naver.com/movie")
        expected = "http://www.naver.com/movie"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("https://www.naver.com/movie")
        expected = "https://www.naver.com/movie"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("http://www.naver.com/movie?page_no=3")
        expected = "http://www.naver.com/movie"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("https://www.naver.com/movie?page_no=3")
        expected = "https://www.naver.com/movie"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("http://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "http://www.naver.com/movie/hello/test.nhn"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("https://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "https://www.naver.com/movie/hello/test.nhn"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("https://tkor.ws/던전-리셋")
        expected = "https://tkor.ws/던전-리셋"
        self.assertEqual(expected, actual)

    def test_concatenate_url(self):
        actual = URL.concatenate_url("http://www.naver.com/movie", "/sports")
        expected = "http://www.naver.com/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("http://www.naver.com/movie/", "/sports")
        expected = "http://www.naver.com/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("https://www.naver.com/movie", "/sports")
        expected = "https://www.naver.com/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("https://www.naver.com/movie/", "/sports")
        expected = "https://www.naver.com/sports"
        self.assertEqual(expected, actual)

        actual = URL.concatenate_url("http://www.naver.com/movie", "sports")
        expected = "http://www.naver.com/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("http://www.naver.com/movie/", "sports")
        expected = "http://www.naver.com/movie/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("https://www.naver.com/movie", "sports")
        expected = "https://www.naver.com/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("https://www.naver.com/movie/", "sports")
        expected = "https://www.naver.com/movie/sports"
        self.assertEqual(expected, actual)

        actual = URL.concatenate_url("http://www.naver.com/movie", "#")
        expected = "http://www.naver.com/movie"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("http://www.naver.com/movie/", "#")
        expected = "http://www.naver.com/movie/"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("http://www.naver.com/view.nhn?page_no=3", "#")
        expected = "http://www.naver.com/view.nhn?page_no=3"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("http://www.naver.com/movie/view.nhn?page_no=3", "#")
        expected = "http://www.naver.com/movie/view.nhn?page_no=3"
        self.assertEqual(expected, actual)

        actual = URL.concatenate_url("http://www.naver.com/movie/view.nhn?page_no=3", "./list.nhn?page_no=4")
        expected = "http://www.naver.com/movie/list.nhn?page_no=4"
        self.assertEqual(expected, actual)

    def test_get_short_md5_name(self):
        self.assertEqual(URL.get_short_md5_name("https://terzeron.com"), "b8025d0")

    def test_encode(self):
        self.assertEqual(URL.encode('http://5rs-wc22.com/식극의-소마/post/134225?a=테스트b'), 'http://5rs-wc22.com/%EC%8B%9D%EA%B7%B9%EC%9D%98-%EC%86%8C%EB%A7%88/post/134225?a=%ED%85%8C%EC%8A%A4%ED%8A%B8b')


class FileManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        group_name = "naver"
        feed_name = "oneplusone"
        self.feed_dir_path = Path(os.environ["FM_WORK_DIR"]) / group_name / feed_name
        self.feed_dir_path.mkdir(exist_ok=True)
        self.sample_conf_file_path = Path(__file__).parent / "conf.naverwebtoon.json"
        self.conf_file_path = self.feed_dir_path / "conf.json"
        shutil.copy(self.sample_conf_file_path, self.conf_file_path)

        self.rss_file_path = self.feed_dir_path / f"{feed_name}.xml"
        self.rss_file_path.touch()
        self.old_rss_file_path = self.rss_file_path.with_suffix(self.rss_file_path.suffix + ".old")
        self.old_rss_file_path.touch()
        self.start_idx_file_path = self.feed_dir_path / "start_idx.txt"
        self.start_idx_file_path.touch()
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
            self.assertTrue(assert_in_mock_logger("* '1234567.html' deleted (due to ['567890a.png'])", mock_info))

        self.assertFalse(self.html_file2_path.is_file())

    def test_remove_html_files_without_cached_image_files(self):
        self.assertTrue(self.html_file2_path.is_file())
        with patch.object(LOGGER, "info") as mock_info:
            FileManager.remove_html_files_without_cached_image_files(self.feed_dir_path, self.feed_img_dir_path)
            self.assertTrue(assert_in_mock_logger("# deleting html files without cached image files", mock_info))
            self.assertTrue(assert_in_mock_logger("* '1234567.html' deleted (due to ['567890a.png'])", mock_info))

        self.assertFalse(self.html_file2_path.is_file())

    def test_remove_temporary_files(self):
        self.assertTrue(self.garbage_file_path.is_file())
        with patch.object(LOGGER, "info") as _:
            FileManager.remove_temporary_files(self.feed_dir_path)

        self.assertFalse(self.garbage_file_path.is_file())

    def test_remove_all_files(self):
        self.assertTrue(self.rss_file_path.is_file())
        self.assertTrue(self.start_idx_file_path.is_file())
        self.assertTrue(self.garbage_file_path.is_file())
        self.assertTrue(self.list_file_path.is_file())
        self.assertTrue(self.html_file1_path.is_file())

        with patch.object(LOGGER, "info") as mock_info:
            FileManager.remove_all_files(self.feed_dir_path)

            self.assertTrue(assert_in_mock_logger("# deleting all files (html files, list files, rss file, various temporary files)", mock_info))
            self.assertTrue(assert_in_mock_logger("# deleting temporary files", mock_info))

        self.assertFalse(self.rss_file_path.is_file())
        self.assertFalse(self.start_idx_file_path.is_file())
        self.assertFalse(self.garbage_file_path.is_file())
        self.assertFalse(self.list_file_path.is_file())
        self.assertFalse(self.html_file1_path.is_file())


def count_substr(member: str, container: List[str]) -> int:
    count = 0
    for element in container:
        if member in element:
            count += 1
    return count


class TestPathUtil(unittest.TestCase):
    def test_convert_path_to_str(self):
        work_dir = Path(os.environ["FM_WORK_DIR"])
        public_feed_dir = Path(os.environ["WEB_SERVICE_FEEDS_DIR"])
        httpd_access_log_dir = Path(os.environ["FM_LOG_DIR"])
        htaccess_file = Path(os.environ["WEB_SERVICE_FEEDS_DIR"]) / ".htaccess"
        self.assertEqual(PathUtil.convert_path_to_str(work_dir), ".")
        self.assertEqual(PathUtil.convert_path_to_str(public_feed_dir), ".")
        self.assertEqual(PathUtil.convert_path_to_str(httpd_access_log_dir), "logs")
        self.assertEqual(PathUtil.convert_path_to_str(htaccess_file), ".htaccess")


if __name__ == "__main__":
    unittest.main()
