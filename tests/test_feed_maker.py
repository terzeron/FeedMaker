#!/usr/bin/env python


import os
import shutil
import logging.config
from pathlib import Path
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch, Mock
from xml.dom.minidom import parse

from bin.feed_maker import FeedMaker
from bin.feed_maker_util import Config, Datetime, PathUtil, Env, header_str
import tempfile
from unittest.mock import MagicMock  # noqa: F401
from bin.feed_maker_util import URL, NotFoundConfigItemError
import json


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def assert_in_mock_logger(message: str, mock_logger: Mock, do_submatch: bool = False) -> bool:
    for mock_call in mock_logger.call_args_list:
        formatted_message = mock_call.args[0] % mock_call.args[1:]
        if do_submatch:
            if message in formatted_message:
                return True
        else:
            if formatted_message == message:
                return True
    return False


class TestFeedMaker(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = Path(tempfile.mkdtemp())
        group_name = "naver"
        feed_name = "certain_webtoon"
        work_dir = self.tmp_root / "work"
        img_dir = self.tmp_root / "img"
        self.public_feed_dir_path = self.tmp_root / "xml"
        for d in [work_dir / group_name / feed_name, img_dir, self.public_feed_dir_path]:
            d.mkdir(parents=True, exist_ok=True)
        self.public_rss_file_path = self.public_feed_dir_path / f"{feed_name}.xml"
        self.public_old_rss_file_path = self.public_feed_dir_path / f"{feed_name}.xml.old"
        self.feed_dir_path = work_dir / group_name / feed_name
        self.rss_file_path = self.feed_dir_path / f"{feed_name}.xml"
        self.rss_file_path.touch()
        self.old_rss_file_path = self.feed_dir_path / f"{feed_name}.xml.old"
        self.old_rss_file_path.touch()
        self.sample_conf_file_path = Path(__file__).parent / "conf.naverwebtoon.json"
        self.conf_file_path = self.feed_dir_path / Config.DEFAULT_CONF_FILE
        shutil.copy(self.sample_conf_file_path, self.conf_file_path)

        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        self._env_patcher = patch.dict(os.environ, {"FM_WORK_DIR": str(work_dir), "WEB_SERVICE_FEED_DIR_PREFIX": str(self.public_feed_dir_path), "WEB_SERVICE_IMAGE_DIR_PREFIX": str(img_dir)})
        self._env_patcher.start()

        self.maker = FeedMaker(feed_dir_path=self.feed_dir_path, do_collect_by_force=False, do_collect_only=False, rss_file_path=self.rss_file_path)
        self.config = Config(feed_dir_path=self.feed_dir_path)
        if not self.config:
            self.fail()
        self.maker.collection_conf = self.config.get_collection_configs()
        self.maker.extraction_conf = self.config.get_extraction_configs()
        self.maker.rss_conf = self.config.get_rss_configs()

        # 테스트를 위해 post_process_script_list를 비워서 download_image.py가 실행되지 않도록 함
        self.maker.extraction_conf["post_process_script_list"] = []

        self.item1_url = "https://comic.naver.com/webtoon/detail?titleId=725586&no=137"
        self.item2_url = "https://comic.naver.com/webtoon/detail?titleId=725586&no=136"

        self.list_dir_path = self.feed_dir_path / "newlist"
        self.list_dir_path.mkdir(exist_ok=True)
        date1_str = Datetime.get_short_date_str()
        self.list_file1_path = self.list_dir_path / f"{date1_str}.txt"
        date2_str = Datetime.get_short_date_str(datetime.now(timezone.utc) - timedelta(days=1))
        self.list_file2_path = self.list_dir_path / f"{date2_str}.txt"
        with self.list_file2_path.open("w", encoding="utf-8") as outfile:
            outfile.write("https://comic.naver.com/webtoon/detail?titleId=725586&no=136\t136화\n")
        with self.list_file1_path.open("w", encoding="utf-8") as outfile:
            outfile.write("https://comic.naver.com/webtoon/detail?titleId=725586&no=136\t136화\n")

        self.html_dir_path = self.feed_dir_path / "html"
        self.html_dir_path.mkdir(exist_ok=True)
        md5_name = "3e1c485"
        self.html_file1_path = self.html_dir_path / f"{md5_name}.html"
        with self.html_file1_path.open("w", encoding="utf-8") as outfile:
            outfile.write(header_str)
            outfile.write(f"<div>with image tag string</div>\n<img src='{img_url_prefix}/1x1.jpg?feed=certain_webtoon.xml&item={md5_name}'/>\n")
            outfile.write("A" * 400)
        md5_name = "8da6dfb"
        self.html_file2_path = self.html_dir_path / f"{md5_name}.html"
        with self.html_file2_path.open("w", encoding="utf-8") as outfile:
            outfile.write(header_str)
            outfile.write("<div>without image tag string</div>\n")
            outfile.write("B" * 400)

        self.feed_img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / feed_name
        self.feed_img_dir_path.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        self._env_patcher.stop()
        del self.maker
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_get_image_tag_str(self) -> None:
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        actual = FeedMaker.get_image_tag_str(img_url_prefix, self.rss_file_path.name, self.item1_url)
        expected = f"<img src='{img_url_prefix}/1x1.jpg?feed=certain_webtoon.xml&item=3e1c485'/>"
        self.assertEqual(expected, actual)

    def test_get_size_of_template_with_image_tag(self) -> None:
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        expected = len(header_str) + len("\n") + len(FeedMaker.get_image_tag_str(img_url_prefix, self.rss_file_path.name)) + len("\n")

        actual1 = FeedMaker.get_size_of_template_with_image_tag(img_url_prefix, self.rss_file_path.name)
        self.assertEqual(expected, actual1)

        actual2 = len(header_str + "\n" + FeedMaker.get_image_tag_str(img_url_prefix, self.rss_file_path.name) + "\n")
        self.assertEqual(expected, actual2)

    def test_is_image_tag_in_html_file(self) -> None:
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        image_tag_str = FeedMaker.get_image_tag_str(img_url_prefix, self.rss_file_path.name, self.item1_url)
        actual = FeedMaker._is_image_tag_in_html_file(self.html_file1_path, image_tag_str)
        self.assertTrue(actual)

    def test_append_image_tag_to_html_file(self) -> None:
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        img_tag_str = FeedMaker.get_image_tag_str(img_url_prefix, self.rss_file_path.name, self.item2_url)

        # no image tag in the html file
        is_found = False
        if self.html_file2_path.is_file():
            with self.html_file2_path.open("r", encoding="utf-8") as infile:
                for line in infile:
                    if img_tag_str in line:
                        is_found = True
        self.assertFalse(is_found)

        FeedMaker._append_image_tag_to_html_file(self.html_file2_path, img_tag_str)

        # image tag is appended to the html file
        is_found = False
        with self.html_file2_path.open("r", encoding="utf-8") as infile:
            for line in infile:
                if img_tag_str in line:
                    is_found = True
        self.assertTrue(is_found)

    def test_get_size_of_template(self) -> None:
        actual = FeedMaker._get_size_of_template()
        expected = 359
        self.assertEqual(expected, actual)

    def test_get_html_file_path(self) -> None:
        actual = FeedMaker._get_html_file_path(self.html_dir_path, self.item1_url)
        expected = self.html_file1_path
        self.assertEqual(expected, actual)

    def test_get_list_file_path(self) -> None:
        date_str = Datetime.get_short_date_str()
        actual = FeedMaker._get_list_file_path(self.list_dir_path, date_str)
        expected = self.list_file1_path
        self.assertEqual(expected, actual)

    def test_cmp_int_or_str(self) -> None:
        a = {"sf": "1"}
        b = {"sf": "2"}
        actual = FeedMaker._cmp_int_or_str(a, b)
        expected = -1
        self.assertEqual(expected, actual)

        a = {"sf": "10"}
        b = {"sf": "1"}
        actual = FeedMaker._cmp_int_or_str(a, b)
        expected = 9
        self.assertEqual(expected, actual)

        a = {"sf": "hello"}
        b = {"sf": "hell"}
        actual = FeedMaker._cmp_int_or_str(a, b)
        expected = 1
        self.assertEqual(expected, actual)

        a = {"sf": "hello"}
        b = {"sf": "world"}
        actual = FeedMaker._cmp_int_or_str(a, b)
        expected = -1
        self.assertEqual(expected, actual)

    def test_cmp_to_key(self) -> None:
        data_list = [{"id": 1, "sf": "399"}, {"id": 2, "sf": "400"}, {"id": 3, "sf": "398"}]
        actual = sorted(data_list, key=FeedMaker._cmp_to_key(FeedMaker._cmp_int_or_str))
        expected = [{"id": 3, "sf": "398"}, {"id": 1, "sf": "399"}, {"id": 2, "sf": "400"}]
        self.assertEqual(expected, actual)

    def test_make_html_file(self) -> None:
        with patch.object(LOGGER, "info") as mock_info:
            actual = self.maker._make_html_file(self.item1_url, "137화")
            self.assertTrue(actual)

            self.assertTrue(assert_in_mock_logger("Old: https://comic.naver.com/webtoon/detail?titleId=725586&no=137\t137화\t", mock_info, True))

    def test_get_index_data(self) -> None:
        dt1 = Datetime.get_current_time()
        actual = self.maker._get_index_data()
        expected = (1, 6)
        dt2 = Datetime.get_current_time()
        self.assertEqual(expected, actual[0:2])
        datetime_str = actual[2]
        self.assertIsNotNone(datetime_str)
        if datetime_str:
            self.assertTrue(dt1 < datetime_str < dt2)

    def test_write_index_data(self) -> None:
        dt = Datetime.get_current_time()
        ts = Datetime._get_time_str(dt)
        self.maker._write_index_data(0, dt, True)
        with self.maker.start_index_file_path.open("r", encoding="utf-8") as infile:
            actual = infile.read()
            expected = f"0\t{ts}\n"
            self.assertEqual(expected, actual)

        dt = Datetime.get_current_time()
        ts = Datetime._get_time_str(dt)
        self.maker._write_index_data(0, dt)
        with self.maker.start_index_file_path.open("r", encoding="utf-8") as infile:
            actual = infile.read()
            expected = f"0\t{ts}\n"
            self.assertEqual(expected, actual)

    def test_1_read_old_feed_list_from_file(self) -> None:
        self.maker.collection_conf["is_completed"] = True
        with patch.object(LOGGER, "info") as mock_info:
            actual = self.maker._read_old_feed_list_from_file()
            self.assertIsNotNone(actual)
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화", [])]
            self.assertEqual(expected, actual)
            self.assertTrue(assert_in_mock_logger(PathUtil.short_path(self.list_file2_path), mock_info))

        self.maker.collection_conf["is_completed"] = False
        with patch.object(LOGGER, "info") as mock_info:
            actual = self.maker._read_old_feed_list_from_file()
            self.assertIsNotNone(actual)
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화", [])]
            self.assertEqual(expected, actual)
            self.assertTrue(assert_in_mock_logger(PathUtil.short_path(self.list_file1_path), mock_info))

    def test_2_fetch_old_feed_list_window(self) -> None:
        self.maker.collection_conf["is_completed"] = True
        with patch.object(LOGGER, "info") as mock_info:
            old_feed_list = self.maker._read_old_feed_list_from_file()
            actual = self.maker._fetch_old_feed_list_window(old_feed_list)
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화", [])]
            self.assertEqual(expected, actual)
            self.assertTrue(assert_in_mock_logger(PathUtil.short_path(self.list_file2_path), mock_info))
            self.assertTrue(assert_in_mock_logger("start index", mock_info, True))

        self.maker.collection_conf["is_completed"] = False
        with patch.object(LOGGER, "info") as mock_info:
            old_feed_list = self.maker._read_old_feed_list_from_file()
            actual = self.maker._fetch_old_feed_list_window(old_feed_list)
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화", [])]
            self.assertEqual(expected, actual)
            self.assertTrue(assert_in_mock_logger(PathUtil.short_path(self.list_file1_path), mock_info))
            self.assertTrue(assert_in_mock_logger("start index", mock_info, True))

    def test_3_get_recent_feed_list(self) -> None:
        # Mock NewlistCollector to avoid external dependencies
        with patch("bin.feed_maker.NewlistCollector") as mock_collector:
            # Configure mock to return test data
            mock_instance = mock_collector.return_value
            mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화", [])]

            self.maker.collection_conf["is_completed"] = True
            actual = self.maker._get_recent_feed_list()
            self.assertIsNotNone(actual)
            # Do NOT inspect the content of recent feeds
            self.assertEqual(1, len(actual))
            self.assertEqual(3, len(actual[0]))

            self.maker.collection_conf["is_completed"] = False
            actual = self.maker._get_recent_feed_list()
            self.assertIsNotNone(actual)
            # Do NOT inspect the content of recent feeds
            self.assertEqual(1, len(actual))
            self.assertEqual(3, len(actual[0]))

    def test_4_diff_feeds_and_make_htmls(self) -> None:
        # Mock all external dependencies
        with patch("bin.feed_maker_util.Process.exec_cmd", side_effect=lambda *a, **k: ("mock_result", None)):
            with patch(
                "bin.feed_maker.Extractor.extract_content",
                return_value="<html><body><div>This is a much larger HTML content that should be bigger than the template size to pass the size check in the feed maker. It needs to be at least 359 bytes to avoid being excluded. This content is intentionally made very long to ensure it passes the size threshold. We need to add more text here to make sure the file size is large enough. Let's add some more content to reach the required size. This should be sufficient now.</div></body></html>",
            ):
                with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch("bin.feed_maker.Crawler") as mock_crawler, patch.object(LOGGER, "info") as mock_info:
                    # Configure mock to return test data
                    mock_instance = mock_collector.return_value
                    mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화", [])]

                    # Mock crawler with larger HTML content to pass size check
                    mock_crawler_instance = mock_crawler.return_value
                    mock_crawler_instance.run.return_value = (
                        "<html><body><div>This is a much larger HTML content that should be bigger than the template size to pass the size check in the feed maker. It needs to be at least 359 bytes to avoid being excluded. This content is intentionally made very long to ensure it passes the size threshold. We need to add more text here to make sure the file size is large enough. Let's add some more content to reach the required size. This should be sufficient now.</div></body></html>",
                        None,
                        None,
                    )

                    old_feed_list = self.maker._read_old_feed_list_from_file()
                    recent_feed_list = self.maker._get_recent_feed_list()

                    actual = self.maker._diff_feeds_and_make_htmls(recent_feed_list=recent_feed_list, old_feed_list=old_feed_list)
                    # Do NOT inspect the content of recent feeds
                    self.assertEqual(1, len(actual))  # 새로운 항목이 없으므로 기존 항목만 1개
                    expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화", [])]
                    self.assertEqual(expected, actual)

                    self.assertTrue(assert_in_mock_logger("Appending 0 new items to the feed list", mock_info))
                    self.assertTrue(assert_in_mock_logger("Appending 1 old items to the feed list", mock_info))

    def test_5_generate_rss_feed(self) -> None:
        # Mock all external dependencies
        with patch("bin.feed_maker_util.Process.exec_cmd", side_effect=lambda *a, **k: ("mock_result", None)):
            with patch(
                "bin.feed_maker.Extractor.extract_content",
                return_value="<html><body><div>This is a much larger HTML content that should be bigger than the template size to pass the size check in the feed maker. It needs to be at least 359 bytes to avoid being excluded. This content is intentionally made very long to ensure it passes the size threshold. We need to add more text here to make sure the file size is large enough. Let's add some more content to reach the required size. This should be sufficient now.</div></body></html>",
            ):
                with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch("bin.feed_maker.Crawler") as mock_crawler, patch.object(LOGGER, "info") as mock_info:
                    # Configure mock to return test data
                    mock_instance = mock_collector.return_value
                    mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화", [])]

                    # Mock crawler with larger HTML content to pass size check
                    mock_crawler_instance = mock_crawler.return_value
                    mock_crawler_instance.run.return_value = (
                        "<html><body><div>This is a much larger HTML content that should be bigger than the template size to pass the size check in the feed maker. It needs to be at least 359 bytes to avoid being excluded. This content is intentionally made very long to ensure it passes the size threshold. We need to add more text here to make sure the file size is large enough. Let's add some more content to reach the required size. This should be sufficient now.</div></body></html>",
                        None,
                        None,
                    )

                    old_feed_list = self.maker._read_old_feed_list_from_file()
                    recent_feed_list = self.maker._get_recent_feed_list()
                    merged_feed_list = self.maker._diff_feeds_and_make_htmls(recent_feed_list=recent_feed_list, old_feed_list=old_feed_list)

                    actual = self.maker._generate_rss_feed(merged_feed_list)
                    self.assertTrue(actual)

                    self.assertTrue(self.rss_file_path.is_file())
                    self.assertTrue(self.old_rss_file_path.is_file())

                    self.assertTrue(assert_in_mock_logger("Generating rss feed file...", mock_info))

                    with self.rss_file_path.open("r", encoding="utf-8") as infile:
                        document = parse(infile)
                        count = 0
                        for rss in document.childNodes:
                            for channel in rss.childNodes:
                                for element in channel.childNodes:
                                    if element.localName == "item":
                                        count += 1
                        self.assertEqual(1, count)  # 새로운 항목이 없으므로 기존 항목만 1개

    def test_6_make(self) -> None:
        # Mock all external dependencies
        with patch("bin.feed_maker_util.Process.exec_cmd", side_effect=lambda *a, **k: ("mock_result", None)):
            with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch("bin.feed_maker.Crawler") as mock_crawler, patch.object(LOGGER, "info") as mock_info:
                # Configure mock to return test data
                mock_instance = mock_collector.return_value
                mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화", [])]

                # Mock crawler
                mock_crawler_instance = mock_crawler.return_value
                mock_crawler_instance.run.return_value = ("mock_html_content", None, None)

                actual = self.maker.make()
                self.assertTrue(actual)

                self.assertTrue(assert_in_mock_logger("upload success!", mock_info))

    def test_failed_url_cache(self) -> None:
        failed_url = "http://example.com/failed"

        # 시나리오 1: ignore_broken_link = "1 hour"
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"
        self.maker._add_failed_url(failed_url, "test failure")

        self.assertTrue(self.maker.failed_urls_cache_file.exists())
        self.assertTrue(self.maker._is_url_recently_failed(failed_url))

        # 만료되지 않았으므로 정리되지 않아야 함
        self.maker._cleanup_expired_failed_urls()
        self.assertTrue(self.maker._is_url_recently_failed(failed_url))

        # 시나리오 2: ignore_broken_link = "" (기본값)
        self.maker.failed_urls_cache_file.unlink()
        self.maker.rss_conf["ignore_broken_link"] = ""
        self.maker._add_failed_url("http://another.com/failed", "another failure")
        self.assertFalse(self.maker.failed_urls_cache_file.exists())

        # 시나리오 3: 만료 테스트
        self.maker.rss_conf["ignore_broken_link"] = "1 second"
        expired_url = "http://example.com/expired"

        # 시간을 과거로 조작하여 캐시 생성
        past_time = Datetime.get_current_time() - timedelta(seconds=5)
        with patch("bin.feed_maker_util.Datetime.get_current_time", return_value=past_time):
            self.maker._add_failed_url(expired_url, "expired failure")

        self.assertTrue(self.maker.failed_urls_cache_file.exists())

        # 현재 시간에는 만료되었어야 함
        self.assertFalse(self.maker._is_url_recently_failed(expired_url))

        # 정리 작업 후에는 파일에서 삭제되어야 함
        self.maker._cleanup_expired_failed_urls()
        with self.maker.failed_urls_cache_file.open("r", encoding="utf-8") as f:
            content = f.read()
            self.assertNotIn(expired_url, content)

    def test_failed_url_cache_formats(self) -> None:
        """다양한 시간 포맷에 대한 실패 URL 캐싱 기능 테스트"""
        test_cases = ["always", "1 month", "1 months", "2 month", "2 months", "3 week", "4 weeks", "5 day", "6 days", "7 hour", "8 hours"]

        for i, case in enumerate(test_cases):
            with self.subTest(case=case):
                # Clean up cache file before each subtest
                if self.maker.failed_urls_cache_file.exists():
                    self.maker.failed_urls_cache_file.unlink()

                url = f"http://example.com/testcase-{i}"
                self.maker.rss_conf["ignore_broken_link"] = case
                self.maker._add_failed_url(url, f"Testing {case}")

                self.assertTrue(self.maker.failed_urls_cache_file.exists(), f"Cache file should exist for case: {case}")

                # Check that the URL is now considered failed
                self.assertTrue(self.maker._is_url_recently_failed(url), f"URL should be recently failed for case: {case}")

                # Check that the expiry date is valid
                with self.maker.failed_urls_cache_file.open("r", encoding="utf-8") as f:
                    content = f.read()
                    self.assertIn(url, content)

                    lines = content.strip().split("\n")
                    found_line = ""
                    for line in lines:
                        if url in line:
                            found_line = line
                            break

                    self.assertTrue(found_line, f"URL not found in cache for case: {case}")

                    _, expiry_str = found_line.strip().split("\t")
                    expiry_dt = self.maker.isoparser.isoparse(expiry_str)

                    if case == "always":
                        self.assertIn("9999-", expiry_str)
                    else:
                        now = Datetime.get_current_time()
                        self.assertGreater(expiry_dt, now, f"Expiry date should be in the future for case: {case}")


class TestCmpIntOrStr(unittest.TestCase):
    def test_both_numeric(self) -> None:
        a = {"sf": "10"}
        b = {"sf": "3"}
        self.assertGreater(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_both_numeric_equal(self) -> None:
        a = {"sf": "5"}
        b = {"sf": "5"}
        self.assertEqual(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_both_numeric_less(self) -> None:
        a = {"sf": "2"}
        b = {"sf": "10"}
        self.assertLess(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_both_string_less(self) -> None:
        a = {"sf": "apple"}
        b = {"sf": "banana"}
        self.assertLess(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_both_string_greater(self) -> None:
        a = {"sf": "banana"}
        b = {"sf": "apple"}
        self.assertGreater(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_both_string_equal(self) -> None:
        a = {"sf": "same"}
        b = {"sf": "same"}
        self.assertEqual(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_mixed_numeric_and_string(self) -> None:
        # One numeric, one string -> string comparison
        a = {"sf": "10"}
        b = {"sf": "abc"}
        result = FeedMaker._cmp_int_or_str(a, b)
        self.assertIsInstance(result, int)


class TestCmpToKey(unittest.TestCase):
    def test_sorting_with_cmp_to_key(self) -> None:
        items = [{"sf": "10"}, {"sf": "2"}, {"sf": "5"}]
        key_func = FeedMaker._cmp_to_key(FeedMaker._cmp_int_or_str)
        sorted_items = sorted(items, key=key_func)
        self.assertEqual([d["sf"] for d in sorted_items], ["2", "5", "10"])

    def test_comparator_lt_gt_eq(self) -> None:
        key_func = FeedMaker._cmp_to_key(FeedMaker._cmp_int_or_str)
        k1 = key_func({"sf": "1"})
        k2 = key_func({"sf": "2"})
        k3 = key_func({"sf": "2"})

        self.assertTrue(k1 < k2)
        self.assertTrue(k2 > k1)
        self.assertTrue(k2 == k3)
        self.assertTrue(k1 <= k2)
        self.assertTrue(k2 >= k1)
        self.assertTrue(k1 != k2)

    def test_eq_with_non_k_type(self) -> None:
        key_func = FeedMaker._cmp_to_key(FeedMaker._cmp_int_or_str)
        k1 = key_func({"sf": "1"})
        self.assertEqual(k1.__eq__("not_a_K"), NotImplemented)
        self.assertEqual(k1.__ne__("not_a_K"), NotImplemented)


class TestGetImageTagStr(unittest.TestCase):
    def test_generates_image_tag(self) -> None:
        result = FeedMaker.get_image_tag_str("https://example.com", "feed.xml", "http://item.com/page/1")
        self.assertIn("https://example.com", result)
        self.assertIn("feed.xml", result)
        self.assertIn("1x1.jpg", result)
        self.assertTrue(result.startswith("<img"))

    def test_default_item_url(self) -> None:
        result = FeedMaker.get_image_tag_str("https://example.com", "feed.xml")
        md5 = URL.get_short_md5_name(URL.get_url_path("any_url"))
        self.assertIn(md5, result)


class TestGetSizeOfTemplateWithImageTag(unittest.TestCase):
    def test_returns_positive_int(self) -> None:
        size = FeedMaker.get_size_of_template_with_image_tag("https://example.com", "feed.xml")
        self.assertGreater(size, 0)
        # Should be header + newline + image_tag + newline
        image_tag = FeedMaker.get_image_tag_str("https://example.com", "feed.xml")
        expected = len(header_str) + len("\n") + len(image_tag) + len("\n")
        self.assertEqual(size, expected)


class TestIsImageTagInHtmlFile(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(tempfile.mkdtemp())
        self.html_file = self.work_dir / "test.html"

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def test_tag_found(self) -> None:
        self.html_file.write_text("<html><img src='test'/></html>", encoding="utf-8")
        self.assertTrue(FeedMaker._is_image_tag_in_html_file(self.html_file, "<img src='test'/>"))

    def test_tag_not_found(self) -> None:
        self.html_file.write_text("<html><p>no image</p></html>", encoding="utf-8")
        self.assertFalse(FeedMaker._is_image_tag_in_html_file(self.html_file, "<img src='test'/>"))


class TestAppendImageTagToHtmlFile(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(tempfile.mkdtemp())
        self.html_file = self.work_dir / "test.html"

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def test_appends_tag(self) -> None:
        self.html_file.write_text("<html></html>", encoding="utf-8")
        FeedMaker._append_image_tag_to_html_file(self.html_file, "<img src='tag'/>")
        content = self.html_file.read_text(encoding="utf-8")
        self.assertIn("<img src='tag'/>", content)
        self.assertTrue(content.endswith("\n"))


class TestGetHtmlFilePath(unittest.TestCase):
    def test_constructs_path(self) -> None:
        html_dir = Path("/tmp/html")
        result = FeedMaker._get_html_file_path(html_dir, "http://example.com/page/1")
        self.assertEqual(result.parent, html_dir)
        self.assertTrue(result.name.endswith(".html"))
        # Should use md5 of url path
        expected_md5 = URL.get_short_md5_name(URL.get_url_path("http://example.com/page/1"))
        self.assertEqual(result.name, f"{expected_md5}.html")


class TestGetListFilePath(unittest.TestCase):
    def test_constructs_path(self) -> None:
        list_dir = Path("/tmp/newlist")
        result = FeedMaker._get_list_file_path(list_dir, "20240101")
        self.assertEqual(result, list_dir / "20240101.txt")


class TestGetSizeOfTemplate(unittest.TestCase):
    def test_returns_header_plus_newline(self) -> None:
        size = FeedMaker._get_size_of_template()
        self.assertEqual(size, len(header_str) + 1)


class TestReadOldFeedListFromFile(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(tempfile.mkdtemp())
        img_dir = self.work_dir / "img"
        img_dir.mkdir(exist_ok=True)
        self.feed_dir = self.work_dir / "test_feed"
        self.feed_dir.mkdir(parents=True, exist_ok=True)
        self.list_dir = self.feed_dir / "newlist"
        self.list_dir.mkdir(exist_ok=True)
        self.html_dir = self.feed_dir / "html"
        self.html_dir.mkdir(exist_ok=True)

        self._env_patcher = patch.dict(os.environ, {"FM_WORK_DIR": str(self.work_dir), "WEB_SERVICE_IMAGE_DIR_PREFIX": str(img_dir)})
        self._env_patcher.start()

        self.sample_conf_file = Path(__file__).parent / "conf.naverwebtoon.json"
        self.conf_file = self.feed_dir / Config.DEFAULT_CONF_FILE
        if self.sample_conf_file.is_file():
            shutil.copy(self.sample_conf_file, self.conf_file)

        self.rss_file = self.feed_dir / "test.xml"
        self.rss_file.touch()

    def tearDown(self) -> None:
        self._env_patcher.stop()
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def _make_maker(self) -> FeedMaker:
        return FeedMaker(feed_dir_path=self.feed_dir, do_collect_by_force=False, do_collect_only=False, rss_file_path=self.rss_file)

    def test_no_collection_conf_returns_empty(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {}
        result = maker._read_old_feed_list_from_file()
        self.assertEqual(result, [])

    def test_not_completed_reads_recent_list_file(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": False}

        dt = Datetime.get_current_time()
        date_str = Datetime.get_short_date_str(dt)
        list_file = FeedMaker._get_list_file_path(self.list_dir, date_str)
        list_file.write_text("http://example.com/1\tTitle1\n", encoding="utf-8")

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "http://example.com/1")
        self.assertEqual(result[0][1], "Title1")

    def test_not_completed_searches_past_days(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": False}

        # No file for today, but file exists for 2 days ago
        dt = Datetime.get_current_time()
        past_date_str = Datetime.get_short_date_str(dt - timedelta(days=2))
        list_file = FeedMaker._get_list_file_path(self.list_dir, past_date_str)
        list_file.write_text("http://example.com/old\tOldTitle\n", encoding="utf-8")

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "http://example.com/old")

    def test_not_completed_no_list_files(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": False}

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(result, [])

    def test_completed_reads_all_list_files(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": True}

        # Create multiple list files
        (self.list_dir / "20240101.txt").write_text("http://a.com/1\tA\n", encoding="utf-8")
        (self.list_dir / "20240102.txt").write_text("http://b.com/2\tB\n", encoding="utf-8")

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(len(result), 2)
        links = [r[0] for r in result]
        self.assertIn("http://a.com/1", links)
        self.assertIn("http://b.com/2", links)

    def test_completed_skips_hidden_files(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": True}

        (self.list_dir / ".hidden").write_text("should be skipped\n", encoding="utf-8")
        (self.list_dir / "20240101.txt").write_text("http://a.com/1\tA\n", encoding="utf-8")

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(len(result), 1)

    def test_metadata_parsing(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": False}

        dt = Datetime.get_current_time()
        date_str = Datetime.get_short_date_str(dt)
        list_file = FeedMaker._get_list_file_path(self.list_dir, date_str)
        list_file.write_text("http://example.com/1\tTitle1\tmeta1\tmeta2\n", encoding="utf-8")

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2], ["meta1", "meta2"])


# ────────────────────────────────────────────────────────
# From test_final_gaps.py: feed_maker 추가 테스트
# ────────────────────────────────────────────────────────
class TestFeedMakerIsUrlRecentlyFailed(unittest.TestCase):
    """Lines 206-207: _is_url_recently_failed returns True."""

    @patch("bin.feed_maker.Env")
    def test_recently_failed_url_skips(self, mock_env):
        from datetime import timedelta

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_env.get.side_effect = lambda k, d="": {"FM_WORK_DIR": tmpdir, "WEB_SERVICE_IMAGE_DIR_PREFIX": tmpdir, "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, d)

            feed_dir = Path(tmpdir) / "testfeed"
            feed_dir.mkdir()
            (feed_dir / "newlist").mkdir()
            (feed_dir / "html").mkdir()

            rss_file = feed_dir / "testfeed.xml"

            cache_file = feed_dir / ".failed_urls_cache"
            future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            cache_file.write_text(f"https://failed.com/page\t{future}\n")

            fm = FeedMaker(feed_dir_path=feed_dir, do_collect_by_force=False, do_collect_only=False, rss_file_path=rss_file)
            fm.extraction_conf = {"render_js": False}
            fm.rss_conf = {}

            result = fm._make_html_file("https://failed.com/page", "title")
            self.assertFalse(result)


class TestFeedMakerHtmlFileNotFound(unittest.TestCase):
    """Lines 469-470: html_file_path not a file in _generate_rss_feed (skips)."""

    @patch("bin.feed_maker.Env")
    @patch("bin.feed_maker.Uploader")
    def test_html_file_missing_skipped(self, mock_uploader, mock_env):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_env.get.side_effect = lambda k, d="": {"FM_WORK_DIR": tmpdir, "WEB_SERVICE_IMAGE_DIR_PREFIX": tmpdir, "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, d)

            feed_dir = Path(tmpdir) / "testfeed"
            feed_dir.mkdir()
            (feed_dir / "newlist").mkdir()
            (feed_dir / "html").mkdir()

            rss_file = feed_dir / "testfeed.xml"

            fm = FeedMaker(feed_dir_path=feed_dir, do_collect_by_force=False, do_collect_only=False, rss_file_path=rss_file)
            fm.rss_conf = {"rss_title": "Test", "rss_link": "http://test.com"}

            feed_list = [("https://example.com/missing", "Missing Title", [])]
            result = fm._generate_rss_feed(feed_list)
            self.assertTrue(result)


class TestFeedMakerContentTruncation(unittest.TestCase):
    """Lines 477-478: content >= MAX_CONTENT_LENGTH truncation."""

    @patch("bin.feed_maker.Env")
    @patch("bin.feed_maker.Data")
    def test_content_truncated(self, mock_data, mock_env):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_env.get.side_effect = lambda k, d="": {"FM_WORK_DIR": tmpdir, "WEB_SERVICE_IMAGE_DIR_PREFIX": tmpdir, "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, d)

            feed_dir = Path(tmpdir) / "testfeed"
            feed_dir.mkdir()
            (feed_dir / "newlist").mkdir()
            html_dir = feed_dir / "html"
            html_dir.mkdir()

            rss_file = feed_dir / "testfeed.xml"

            fm = FeedMaker(feed_dir_path=feed_dir, do_collect_by_force=False, do_collect_only=False, rss_file_path=rss_file)
            fm.rss_conf = {"rss_title": "Test", "rss_link": "http://test.com"}

            link = "https://example.com/big"
            md5 = URL.get_short_md5_name(URL.get_url_path(link))
            html_file = html_dir / f"{md5}.html"
            html_file.write_text("x" * (FeedMaker.MAX_CONTENT_LENGTH + 1000))

            mock_data.compare_two_rss_files.return_value = False

            feed_list = [(link, "Big Content", [])]
            result = fm._generate_rss_feed(feed_list)
            self.assertTrue(result)


class TestFeedMakerRssFileNotExistIsDifferent(unittest.TestCase):
    """Line 503: rss_file_path doesn't exist, is_different=True."""

    @patch("bin.feed_maker.Env")
    def test_rss_not_exist_is_different(self, mock_env):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_env.get.side_effect = lambda k, d="": {"FM_WORK_DIR": tmpdir, "WEB_SERVICE_IMAGE_DIR_PREFIX": tmpdir, "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, d)

            feed_dir = Path(tmpdir) / "testfeed"
            feed_dir.mkdir()
            (feed_dir / "newlist").mkdir()
            html_dir = feed_dir / "html"
            html_dir.mkdir()

            rss_file = feed_dir / "testfeed.xml"

            fm = FeedMaker(feed_dir_path=feed_dir, do_collect_by_force=False, do_collect_only=False, rss_file_path=rss_file)
            fm.rss_conf = {"rss_title": "Test", "rss_link": "http://test.com"}

            result = fm._generate_rss_feed([])
            self.assertTrue(result)
            self.assertTrue(rss_file.is_file())


class TestFeedMakerGenerateRssFeedReturnsFalse(unittest.TestCase):
    """Lines 627-628: _generate_rss_feed returns False in make()."""

    @patch("bin.feed_maker.Env")
    @patch("bin.feed_maker.Config")
    def test_generate_rss_feed_failure(self, mock_config_cls, mock_env):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_env.get.side_effect = lambda k, d="": {"FM_WORK_DIR": tmpdir, "WEB_SERVICE_IMAGE_DIR_PREFIX": tmpdir, "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, d)

            feed_dir = Path(tmpdir) / "testfeed"
            feed_dir.mkdir()
            (feed_dir / "newlist").mkdir()
            (feed_dir / "html").mkdir()

            rss_file = feed_dir / "testfeed.xml"

            fm = FeedMaker(feed_dir_path=feed_dir, do_collect_by_force=False, do_collect_only=False, rss_file_path=rss_file)

            mock_config = MagicMock()
            mock_config.get_collection_configs.return_value = {"is_completed": True}
            mock_config.get_extraction_configs.return_value = {}
            mock_config.get_rss_configs.return_value = {}
            mock_config_cls.return_value = mock_config

            with patch.object(fm, "_read_old_feed_list_from_file", return_value=[("http://a.com", "title", [])]):
                with patch.object(fm, "_fetch_old_feed_list_window", return_value=[("http://a.com", "title", [])]):
                    result = fm.make()
            self.assertFalse(result)


# ---------------------------------------------------------------------------
# From test_feed_maker_make.py
# ---------------------------------------------------------------------------
class FeedMakerMakeTestBase(unittest.TestCase):
    """Base class that creates a FeedMaker instance with real dirs and mocked config."""

    def setUp(self) -> None:
        self.tmp_root = Path(tempfile.mkdtemp())
        work_dir = self.tmp_root / "work"
        img_dir = self.tmp_root / "img"
        self.group_name = "naver"
        self.feed_name = "test_make_feed"
        self.feed_dir_path = work_dir / self.group_name / self.feed_name
        self.feed_dir_path.mkdir(parents=True, exist_ok=True)
        img_dir.mkdir(exist_ok=True)
        self.rss_file_path = self.feed_dir_path / f"{self.feed_name}.xml"
        self.rss_file_path.touch()

        self._env_patcher = patch.dict(os.environ, {"FM_WORK_DIR": str(work_dir), "WEB_SERVICE_IMAGE_DIR_PREFIX": str(img_dir)})
        self._env_patcher.start()

        sample_conf = Path(__file__).parent / "conf.naverwebtoon.json"
        conf_file = self.feed_dir_path / Config.DEFAULT_CONF_FILE
        shutil.copy(sample_conf, conf_file)

        self.maker = FeedMaker(feed_dir_path=self.feed_dir_path, do_collect_by_force=False, do_collect_only=False, rss_file_path=self.rss_file_path)
        config = Config(feed_dir_path=self.feed_dir_path)
        self.maker.collection_conf = config.get_collection_configs()
        self.maker.extraction_conf = config.get_extraction_configs()
        self.maker.rss_conf = config.get_rss_configs()
        # avoid running download_image.py
        self.maker.extraction_conf["post_process_script_list"] = []

        self.html_dir = self.feed_dir_path / "html"
        self.list_dir = self.feed_dir_path / "newlist"
        self.img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

    def tearDown(self) -> None:
        self._env_patcher.stop()
        del self.maker
        shutil.rmtree(self.tmp_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# _make_html_file tests
# ---------------------------------------------------------------------------
class TestMakeHtmlFileExistingWithImageTag(FeedMakerMakeTestBase):
    """Existing HTML file that has image tag -> returns True (old feed)."""

    def test_existing_file_with_image_tag(self) -> None:
        item_url = "http://example.com/page/1"
        html_path = FeedMaker._get_html_file_path(self.html_dir, item_url)
        image_tag = FeedMaker.get_image_tag_str(self.img_url_prefix, self.rss_file_path.name, item_url)
        # write file larger than template+image_tag size
        html_path.write_text(header_str + "\n" + image_tag + "\n" + "A" * 500, encoding="utf-8")

        result = self.maker._make_html_file(item_url, "Title1")
        self.assertTrue(result)


class TestMakeHtmlFileExistingWithoutImageTag(FeedMakerMakeTestBase):
    """Existing HTML file without image tag -> removes file, returns False."""

    def test_existing_file_without_image_tag(self) -> None:
        item_url = "http://example.com/page/2"
        html_path = FeedMaker._get_html_file_path(self.html_dir, item_url)
        # write file larger than template+image_tag but NO image tag
        html_path.write_text(header_str + "\n" + "B" * 500, encoding="utf-8")

        result = self.maker._make_html_file(item_url, "Title2")
        self.assertFalse(result)
        self.assertFalse(html_path.is_file())


class TestMakeHtmlFileCrawlerFails(FeedMakerMakeTestBase):
    """Crawler returns error -> returns False."""

    def test_crawler_fails(self) -> None:
        item_url = "http://example.com/page/fail_crawl"
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls:
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = (None, "connection error", None)

            result = self.maker._make_html_file(item_url, "Fail")
            self.assertFalse(result)


class TestMakeHtmlFileExtractorFails(FeedMakerMakeTestBase):
    """Extractor returns empty content -> returns False."""

    def test_extractor_fails(self) -> None:
        item_url = "http://example.com/page/fail_extract"
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls, patch("bin.feed_maker.Extractor.extract_content", return_value=None):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "Fail")
            self.assertFalse(result)


class TestMakeHtmlFileBypassExtraction(FeedMakerMakeTestBase):
    """bypass_element_extraction=True skips extractor."""

    def test_bypass_extraction(self) -> None:
        item_url = "http://example.com/page/bypass"
        self.maker.extraction_conf["bypass_element_extraction"] = True
        big_content = header_str + "\n" + "C" * 500

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls:
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = (big_content, None, None)

            result = self.maker._make_html_file(item_url, "Bypass")
            self.assertTrue(result)

        self.maker.extraction_conf.pop("bypass_element_extraction", None)


class TestMakeHtmlFilePostProcessScript(FeedMakerMakeTestBase):
    """post_process_script_list is executed."""

    def test_post_process_script(self) -> None:
        item_url = "http://example.com/page/postproc"
        big_content = header_str + "\n" + "D" * 500
        self.maker.extraction_conf["post_process_script_list"] = ["my_script.py"]

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls, patch("bin.feed_maker.Extractor.extract_content", return_value=big_content), patch("bin.feed_maker_util.Process.exec_cmd", return_value=(big_content, None)), patch("shutil.which", return_value=None):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "PostProc")
            self.assertTrue(result)

        self.maker.extraction_conf["post_process_script_list"] = []


class TestMakeHtmlFilePostProcessFails(FeedMakerMakeTestBase):
    """post_process_script fails -> returns False."""

    def test_post_process_fails(self) -> None:
        item_url = "http://example.com/page/postfail"
        self.maker.extraction_conf["post_process_script_list"] = ["fail_script.py"]
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls, patch("bin.feed_maker.Extractor.extract_content", return_value="<html>ok</html>"), patch("bin.feed_maker_util.Process.exec_cmd", return_value=(None, "script error")), patch("shutil.which", return_value=None):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "PostFail")
            self.assertFalse(result)

        self.maker.extraction_conf["post_process_script_list"] = []


class TestMakeHtmlFileSizeTooSmall(FeedMakerMakeTestBase):
    """Created file smaller than template -> excluded, returns False."""

    def test_size_too_small(self) -> None:
        item_url = "http://example.com/page/small"
        tiny_content = "tiny"  # much smaller than template

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls, patch("bin.feed_maker.Extractor.extract_content", return_value=tiny_content):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "Small")
            self.assertFalse(result)


class TestMakeHtmlFileExceptionDuringCreation(FeedMakerMakeTestBase):
    """Exception during HTML creation -> returns False."""

    def test_exception_during_creation(self) -> None:
        item_url = "http://example.com/page/exc"
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls:
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.side_effect = RuntimeError("boom")

            result = self.maker._make_html_file(item_url, "Exc")
            self.assertFalse(result)


class TestMakeHtmlFileThresholdCheck(FeedMakerMakeTestBase):
    """threshold_to_remove_html_with_incomplete_image triggers removal."""

    def test_threshold_removes_html(self) -> None:
        item_url = "http://example.com/page/threshold"
        big_content = header_str + "\n" + "E" * 500
        self.maker.extraction_conf["threshold_to_remove_html_with_incomplete_image"] = 1

        with (
            patch("bin.feed_maker.Crawler") as mock_crawler_cls,
            patch("bin.feed_maker.Extractor.extract_content", return_value=big_content),
            patch("bin.feed_maker.FileManager.get_incomplete_image_list", return_value=["img1", "img2"]),
            patch("bin.feed_maker.FileManager.remove_image_files_with_zero_size"),
            patch("bin.feed_maker.FileManager.remove_html_file_without_cached_image_files"),
        ):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "Threshold")
            self.assertFalse(result)

        self.maker.extraction_conf.pop("threshold_to_remove_html_with_incomplete_image", None)


class TestMakeHtmlFileNoExtractionConf(FeedMakerMakeTestBase):
    """No extraction_conf -> returns False early."""

    def test_no_extraction_conf(self) -> None:
        self.maker.extraction_conf = {}
        result = self.maker._make_html_file("http://example.com/x", "X")
        self.assertFalse(result)


class TestMakeHtmlFilePostProcessSystemProgram(FeedMakerMakeTestBase):
    """Post-process script found in system path (/usr/bin) uses simple command."""

    def test_system_program_path(self) -> None:
        item_url = "http://example.com/page/sysprog"
        big_content = header_str + "\n" + "F" * 500
        self.maker.extraction_conf["post_process_script_list"] = ["sed s/a/b/"]

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls, patch("bin.feed_maker.Extractor.extract_content", return_value=big_content), patch("bin.feed_maker_util.Process.exec_cmd", return_value=(big_content, None)) as mock_exec, patch("shutil.which", return_value="/usr/bin/sed"):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "SysProg")
            self.assertTrue(result)
            # system program: command without -f option
            cmd_arg = mock_exec.call_args[0][0]
            self.assertNotIn("-f", cmd_arg)

        self.maker.extraction_conf["post_process_script_list"] = []


# ---------------------------------------------------------------------------
# _get_index_data tests
# ---------------------------------------------------------------------------
class TestGetIndexDataFileExists(FeedMakerMakeTestBase):
    """start_idx.txt exists with valid data."""

    def test_file_exists_with_data(self) -> None:
        mtime_str = "2025-01-15T10:00:00+00:00"
        self.maker.start_index_file_path.write_text(f"10\t{mtime_str}\n", encoding="utf-8")
        start, end, mtime = self.maker._get_index_data()
        self.assertEqual(start, 10)
        self.assertEqual(end, 10 + self.maker.window_size)
        self.assertIsNotNone(mtime)


class TestGetIndexDataFileNotExist(FeedMakerMakeTestBase):
    """start_idx.txt does not exist -> creates it."""

    def test_file_not_exist(self) -> None:
        self.maker.start_index_file_path.unlink(missing_ok=True)
        start, end, mtime = self.maker._get_index_data()
        self.assertEqual(start, 1)
        self.assertEqual(end, 1 + self.maker.window_size)
        self.assertIsNotNone(mtime)
        self.assertTrue(self.maker.start_index_file_path.is_file())


class TestGetIndexDataFileExistsNoMatch(FeedMakerMakeTestBase):
    """start_idx.txt exists but has no matching data -> fallback to default."""

    def test_file_exists_no_match(self) -> None:
        self.maker.start_index_file_path.write_text("invalid_content\n", encoding="utf-8")
        start, end, mtime = self.maker._get_index_data()
        self.assertEqual(start, 1)
        self.assertEqual(end, 1 + self.maker.window_size)


# ---------------------------------------------------------------------------
# _write_index_data tests
# ---------------------------------------------------------------------------
class TestWriteIndexDataWithIncrement(FeedMakerMakeTestBase):
    """increment_size > 0 triggers write."""

    def test_increment_write(self) -> None:
        past = Datetime.get_current_time() - timedelta(days=2)
        self.maker.collection_conf["unit_size_per_day"] = 2
        next_idx, ts_str = self.maker._write_index_data(5, past)
        self.assertGreater(next_idx, 5)
        self.assertIsNotNone(ts_str)
        self.assertTrue(self.maker.start_index_file_path.is_file())


class TestWriteIndexDataInitialWrite(FeedMakerMakeTestBase):
    """do_write_initially=True triggers write even with 0 increment."""

    def test_initial_write(self) -> None:
        now = Datetime.get_current_time()
        next_idx, ts_str = self.maker._write_index_data(1, now, do_write_initially=True)
        self.assertEqual(next_idx, 1)
        self.assertIsNotNone(ts_str)


class TestWriteIndexDataNoWrite(FeedMakerMakeTestBase):
    """No increment and not initial -> no write."""

    def test_no_write(self) -> None:
        now = Datetime.get_current_time()
        self.maker.collection_conf["unit_size_per_day"] = 0
        next_idx, ts_str = self.maker._write_index_data(1, now, do_write_initially=False)
        self.assertEqual(next_idx, 1)
        self.assertIsNone(ts_str)


# ---------------------------------------------------------------------------
# _fetch_old_feed_list_window tests
# ---------------------------------------------------------------------------
class TestFetchOldFeedListWindow(FeedMakerMakeTestBase):
    """Normal window slicing."""

    def test_normal_window(self) -> None:
        old_list = [("http://example.com/1", "Title1", []), ("http://example.com/2", "Title2", []), ("http://example.com/3", "Title3", [])]
        # sort_field_pattern from config: "no=(\d+)\t" won't match these URLs
        # so matched_count will be 0, and sorted_feed_list = feed_id_sort_field_list (unsorted)
        self.maker.collection_conf["sort_field_pattern"] = r"example.com/(\d+)"
        self.maker.window_size = 2
        # ensure start_idx file
        self.maker.start_index_file_path.unlink(missing_ok=True)

        result = self.maker._fetch_old_feed_list_window(old_list)
        self.assertIsNotNone(result)
        self.assertLessEqual(len(result), 2)


class TestFetchOldFeedListWindowNoMtime(FeedMakerMakeTestBase):
    """_get_index_data returns None mtime -> returns None."""

    def test_no_mtime(self) -> None:
        old_list = [("http://example.com/1", "T", [])]
        self.maker.collection_conf["sort_field_pattern"] = r"example.com/(\d+)"

        with patch.object(self.maker, "_get_index_data", return_value=(0, 0, None)):
            result = self.maker._fetch_old_feed_list_window(old_list)
            self.assertIsNone(result)


class TestFetchOldFeedListWindowNoSortFieldPattern(FeedMakerMakeTestBase):
    """Missing sort_field_pattern raises NotFoundConfigItemError."""

    def test_no_sort_field_pattern(self) -> None:
        self.maker.collection_conf["sort_field_pattern"] = ""
        with self.assertRaises(NotFoundConfigItemError):
            self.maker._fetch_old_feed_list_window([("http://a.com/1", "T", [])])


# ---------------------------------------------------------------------------
# _get_recent_feed_list tests
# ---------------------------------------------------------------------------
class TestGetRecentFeedList(FeedMakerMakeTestBase):
    """Delegates to NewlistCollector."""

    def test_delegates_to_collector(self) -> None:
        with patch("bin.feed_maker.NewlistCollector") as mock_cls:
            mock_cls.return_value.collect.return_value = [("http://x.com/1", "X", [])]
            result = self.maker._get_recent_feed_list()
            self.assertEqual(len(result), 1)
            mock_cls.assert_called_once()


# ---------------------------------------------------------------------------
# _get_new_feeds tests
# ---------------------------------------------------------------------------
class TestGetNewFeeds(FeedMakerMakeTestBase):
    """Filters items not in old list."""

    def test_filters_new(self) -> None:
        recent = [("http://a.com/1", "A", []), ("http://b.com/2", "B", [])]
        old = [("http://a.com/1", "A", [])]
        result = self.maker._get_new_feeds(recent, old)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "http://b.com/2")

    def test_no_new_feeds(self) -> None:
        recent = [("http://a.com/1", "A", [])]
        old = [("http://a.com/1", "A", [])]
        result = self.maker._get_new_feeds(recent, old)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# _diff_feeds_and_make_htmls tests
# ---------------------------------------------------------------------------
class TestDiffFeedsAndMakeHtmls(FeedMakerMakeTestBase):
    """Merges new + old and calls _make_html_file."""

    def test_new_and_old_merge(self) -> None:
        recent = [("http://a.com/1", "A", []), ("http://b.com/2", "B", [])]
        old = [("http://a.com/1", "A", [])]

        with patch.object(self.maker, "_make_html_file", return_value=True):
            result = self.maker._diff_feeds_and_make_htmls(recent, old)
            self.assertGreaterEqual(len(result), 1)
            self.assertLessEqual(len(result), self.maker.window_size)


class TestDiffFeedsHtmlFailure(FeedMakerMakeTestBase):
    """_make_html_file returns False -> item not in merged list."""

    def test_html_failure_excluded(self) -> None:
        recent = [("http://a.com/1", "A", [])]
        old: list = []

        with patch.object(self.maker, "_make_html_file", return_value=False):
            result = self.maker._diff_feeds_and_make_htmls(recent, old)
            self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# _generate_rss_feed tests
# ---------------------------------------------------------------------------
class TestGenerateRssFeed(FeedMakerMakeTestBase):
    """RSS generation, file comparison, rename."""

    def test_generates_rss(self) -> None:
        item_url = "http://example.com/rss/1"
        html_path = FeedMaker._get_html_file_path(self.html_dir, item_url)
        html_path.write_text(header_str + "\ncontent here\n", encoding="utf-8")

        merged = [(item_url, "RSSTitle", [])]
        result = self.maker._generate_rss_feed(merged)
        self.assertTrue(result)
        self.assertTrue(self.rss_file_path.is_file())

    def test_no_rss_conf(self) -> None:
        self.maker.rss_conf = {}
        result = self.maker._generate_rss_feed([])
        self.assertFalse(result)

    def test_same_content_no_rename(self) -> None:
        """When new RSS is same as existing, temp file is deleted."""
        item_url = "http://example.com/rss/same"
        html_path = FeedMaker._get_html_file_path(self.html_dir, item_url)
        html_path.write_text(header_str + "\ncontent\n", encoding="utf-8")

        merged = [(item_url, "Same", [])]
        # Generate first time
        self.maker._generate_rss_feed(merged)
        # Generate again (same content)
        with patch("bin.feed_maker.Data.compare_two_rss_files", return_value=True):
            result = self.maker._generate_rss_feed(merged)
            self.assertTrue(result)


class TestGenerateRssFeedMissingTitle(FeedMakerMakeTestBase):
    """Missing rss_title raises NotFoundConfigItemError."""

    def test_missing_title(self) -> None:
        self.maker.rss_conf["rss_title"] = ""
        with self.assertRaises(NotFoundConfigItemError):
            self.maker._generate_rss_feed([])


class TestGenerateRssFeedMissingLink(FeedMakerMakeTestBase):
    """Missing rss_link raises NotFoundConfigItemError."""

    def test_missing_link(self) -> None:
        self.maker.rss_conf["rss_link"] = ""
        with self.assertRaises(NotFoundConfigItemError):
            self.maker._generate_rss_feed([])


# ---------------------------------------------------------------------------
# make() tests
# ---------------------------------------------------------------------------
class TestMakeIsCompletedPath(FeedMakerMakeTestBase):
    """make() with is_completed=True uses _fetch_old_feed_list_window."""

    def test_is_completed(self) -> None:
        # Write list files for completed feed
        dt = Datetime.get_current_time()
        date_str = Datetime.get_short_date_str(dt)
        list_file = self.list_dir / f"{date_str}.txt"
        list_file.write_text("http://example.com/c/1\tC1\n", encoding="utf-8")

        # Set is_completed in config file
        conf_file = self.feed_dir_path / Config.DEFAULT_CONF_FILE

        with conf_file.open("r", encoding="utf-8") as f:
            conf_data = json.load(f)
        conf_data["configuration"]["collection"]["is_completed"] = True
        with conf_file.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        with patch.object(FeedMaker, "_fetch_old_feed_list_window", return_value=[("http://example.com/c/1", "C1", [])]) as mock_fetch, patch.object(FeedMaker, "_generate_rss_feed", return_value=True), patch("bin.feed_maker.Uploader.upload"):
            result = self.maker.make()
            self.assertTrue(result)
            mock_fetch.assert_called_once()


class TestMakeNormalPath(FeedMakerMakeTestBase):
    """make() normal (not completed) path."""

    def test_normal_path(self) -> None:
        with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch.object(FeedMaker, "_diff_feeds_and_make_htmls", return_value=[("http://x.com/1", "X", [])]), patch.object(FeedMaker, "_generate_rss_feed", return_value=True), patch("bin.feed_maker.Uploader.upload"):
            mock_collector.return_value.collect.return_value = [("http://x.com/1", "X", [])]

            result = self.maker.make()
            self.assertTrue(result)


class TestMakeCollectOnly(FeedMakerMakeTestBase):
    """make() with do_collect_only skips RSS generation."""

    def test_collect_only(self) -> None:
        self.maker.do_collect_only = True

        with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch.object(FeedMaker, "_generate_rss_feed") as mock_gen:
            mock_collector.return_value.collect.return_value = [("http://x.com/1", "X", [])]

            result = self.maker.make()
            self.assertTrue(result)
            mock_gen.assert_not_called()


class TestMakeIgnoreOldList(FeedMakerMakeTestBase):
    """make() with ignore_old_list clears old list before diff."""

    def test_ignore_old_list(self) -> None:
        # Write list file so old_feed_list is non-empty initially
        dt = Datetime.get_current_time()
        date_str = Datetime.get_short_date_str(dt)
        list_file = self.list_dir / f"{date_str}.txt"
        list_file.write_text("http://example.com/old/1\tOld1\n", encoding="utf-8")

        # Set ignore_old_list in the config
        conf_file = self.feed_dir_path / Config.DEFAULT_CONF_FILE

        with conf_file.open("r", encoding="utf-8") as f:
            conf_data = json.load(f)
        conf_data["configuration"]["collection"]["ignore_old_list"] = True
        with conf_file.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch.object(FeedMaker, "_diff_feeds_and_make_htmls", return_value=[("http://x.com/1", "X", [])]) as mock_diff, patch.object(FeedMaker, "_generate_rss_feed", return_value=True), patch("bin.feed_maker.Uploader.upload"):
            mock_collector.return_value.collect.return_value = [("http://x.com/1", "X", [])]

            result = self.maker.make()
            self.assertTrue(result)
            # old_feed_list should have been cleared
            call_args = mock_diff.call_args
            old_list_arg = call_args[1].get("old_feed_list", call_args[0][1])
            self.assertEqual(old_list_arg, [])


class TestMakeRecentFeedListEmpty(FeedMakerMakeTestBase):
    """make() returns False when recent feed list is empty."""

    def test_empty_recent(self) -> None:
        with patch("bin.feed_maker.NewlistCollector") as mock_collector:
            mock_collector.return_value.collect.return_value = []

            result = self.maker.make()
            self.assertFalse(result)


class TestMakeGenerateRssFails(FeedMakerMakeTestBase):
    """make() returns False when _generate_rss_feed fails."""

    def test_rss_generation_fails(self) -> None:
        with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch.object(FeedMaker, "_diff_feeds_and_make_htmls", return_value=[("http://x.com/1", "X", [])]), patch.object(FeedMaker, "_generate_rss_feed", return_value=False):
            mock_collector.return_value.collect.return_value = [("http://x.com/1", "X", [])]

            result = self.maker.make()
            self.assertFalse(result)


class TestMakeForceCollect(FeedMakerMakeTestBase):
    """make() with do_collect_by_force sets is_completed=False."""

    def test_force_collect(self) -> None:
        self.maker.do_collect_by_force = True

        with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch.object(FeedMaker, "_diff_feeds_and_make_htmls", return_value=[("http://x.com/1", "X", [])]), patch.object(FeedMaker, "_generate_rss_feed", return_value=True), patch("bin.feed_maker.Uploader.upload"):
            mock_collector.return_value.collect.return_value = [("http://x.com/1", "X", [])]

            result = self.maker.make()
            self.assertTrue(result)


class TestMakeCompletedWindowEmpty(FeedMakerMakeTestBase):
    """make() with is_completed returns False when window is empty."""

    def test_completed_empty_window(self) -> None:
        conf_file = self.feed_dir_path / Config.DEFAULT_CONF_FILE

        with conf_file.open("r", encoding="utf-8") as f:
            conf_data = json.load(f)
        conf_data["configuration"]["collection"]["is_completed"] = True
        with conf_file.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        with patch.object(FeedMaker, "_fetch_old_feed_list_window", return_value=[]):
            result = self.maker.make()
            self.assertFalse(result)


class TestFailedUrlCacheEdgeCases(FeedMakerMakeTestBase):
    """Edge cases in failed URL cache: empty lines, invalid timestamps → covers L592,599-600,621,627-628"""

    def test_is_url_recently_failed_with_empty_lines_and_bad_timestamp(self) -> None:
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"
        cache = self.maker.failed_urls_cache_file
        cache.write_text("\n\nhttp://bad.com/page\tINVALID_TIMESTAMP\nhttp://good.com/page\t9999-12-31T23:59:59+00:00\n\n")

        self.assertFalse(self.maker._is_url_recently_failed("http://bad.com/page"))
        self.assertTrue(self.maker._is_url_recently_failed("http://good.com/page"))

    def test_cleanup_with_empty_lines_and_bad_timestamp(self) -> None:
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"
        cache = self.maker.failed_urls_cache_file
        cache.write_text("\n\nhttp://bad.com/page\tINVALID\nhttp://good.com/page\t9999-12-31T23:59:59+00:00\n\n")

        self.maker._cleanup_expired_failed_urls()
        content = cache.read_text()
        self.assertNotIn("INVALID", content)
        self.assertIn("http://good.com/page", content)


class TestGetExpirationFromConfigEdgeCases(FeedMakerMakeTestBase):
    """_get_expiration_from_config: invalid pattern → covers L654,672"""

    def test_invalid_pattern_returns_none(self) -> None:
        self.maker.rss_conf["ignore_broken_link"] = "not a valid pattern"
        result = self.maker._get_expiration_from_config()
        self.assertIsNone(result)

    def test_empty_string_returns_none(self) -> None:
        self.maker.rss_conf["ignore_broken_link"] = ""
        result = self.maker._get_expiration_from_config()
        self.assertIsNone(result)


class TestFetchOldFeedListWindowSortFieldEdgeCases(FeedMakerMakeTestBase):
    """sort_field pattern no-match and partial match → covers L376,379,391-392,407"""

    def test_sort_field_no_match_uses_default(self) -> None:
        """When pattern doesn't match any item, uses 999999999 as sort_field."""
        old_list = [("http://example.com/abc", "Title1", []), ("http://example.com/def", "Title2", [])]
        # pattern이 아무것도 매치하지 않도록 설정
        self.maker.collection_conf["sort_field_pattern"] = r"NOMATCH_(\d+)"
        self.maker.window_size = 10
        self.maker.start_index_file_path.unlink(missing_ok=True)

        result = self.maker._fetch_old_feed_list_window(old_list)
        self.assertIsNotNone(result)

    def test_sort_field_with_two_groups(self) -> None:
        """Pattern with two capture groups → covers L375-376."""
        old_list = [("http://example.com/10/a", "Title", []), ("http://example.com/5/b", "Title2", [])]
        # 두 개의 캡처 그룹이 있는 패턴
        self.maker.collection_conf["sort_field_pattern"] = r"example.com/(\d+)/([a-z])"
        self.maker.window_size = 10
        self.maker.start_index_file_path.unlink(missing_ok=True)

        result = self.maker._fetch_old_feed_list_window(old_list)
        self.assertIsNotNone(result)


class TestGenerateRssFeedWithGuidPrefix(FeedMakerMakeTestBase):
    """rss_url_prefix_for_guid set → covers L482"""

    def test_guid_prefix(self) -> None:
        from bin.feed_maker_util import URL, header_str

        link = "https://example.com/page/1"
        md5 = URL.get_short_md5_name(URL.get_url_path(link))
        html_file = self.html_dir / f"{md5}.html"
        html_file.write_text(header_str + "<div>content</div>" + "A" * 200)

        self.maker.rss_conf["rss_url_prefix_for_guid"] = "https://myguid.com"
        self.maker.rss_conf["rss_title"] = "Test"
        self.maker.rss_conf["rss_link"] = "http://test.com"

        from unittest.mock import patch as _patch

        with _patch("bin.feed_maker.Data.compare_two_rss_files", return_value=False):
            with _patch("bin.feed_maker.Uploader") as mock_up:
                mock_up.return_value.upload.return_value = True
                result = self.maker._generate_rss_feed([(link, "Title", [])])
                self.assertTrue(result)


class TestGetIndexDataWriteFailure(FeedMakerMakeTestBase):
    """_get_index_data: _write_index_data returns empty → covers L339"""

    def test_write_index_data_returns_empty(self) -> None:
        self.maker.start_index_file_path.unlink(missing_ok=True)
        with patch.object(self.maker, "_write_index_data", return_value=(0, None)):
            start, end, mtime = self.maker._get_index_data()
            self.assertEqual(start, 0)
            self.assertEqual(end, 0)
            self.assertIsNone(mtime)


if __name__ == "__main__":
    unittest.main()
