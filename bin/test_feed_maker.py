#!/usr/bin/env python


import os
import shutil
import logging.config
from pathlib import Path
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch, call
from typing import Any
from feed_maker import FeedMaker
from feed_maker_util import Config, Datetime

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


def assert_in_mock_logger(param: Any, mock_logger, do_substr_match: bool = False) -> bool:
    for arg in mock_logger.call_args_list:
        if do_substr_match:
            if str(param) in str(arg.args[0]):
                return True
        else:
            if call(param) == arg:
                return True
    return False


class TestFeedMaker(unittest.TestCase):
    def setUp(self) -> None:
        group_name = "naver"
        feed_name = "oneplusone"
        self.feed_dir_path = Path(os.environ["FEED_MAKER_WORK_DIR"]) / group_name / feed_name
        self.feed_dir_path.mkdir(exist_ok=True)
        self.rss_file_path = self.feed_dir_path / (feed_name + ".xml")
        self.rss_file_path.touch()
        self.old_rss_file_path = self.feed_dir_path / (feed_name + ".xml.old")
        self.old_rss_file_path.touch()
        self.sample_conf_file_path = Path.cwd() / "test" / "conf.naverwebtoon.json"
        self.conf_file_path = self.feed_dir_path / "conf.json"
        shutil.copy(self.sample_conf_file_path, self.conf_file_path)

        self.maker = FeedMaker(self.feed_dir_path, do_collect_by_force=False, do_collect_only=False,
                               rss_file_path=self.rss_file_path)
        self.config = Config(feed_dir_path=self.feed_dir_path)
        if not self.config:
            self.fail()
        self.maker.collection_conf = self.config.get_collection_configs()
        self.maker.extraction_conf = self.config.get_extraction_configs()
        self.maker.rss_conf = self.config.get_rss_configs()

        self.item1_url = "https://comic.naver.com/webtoon/detail?titleId=725586&no=137"
        self.item2_url = "https://comic.naver.com/webtoon/detail?titleId=725586&no=136"

        self.list_dir_path = self.feed_dir_path / "newlist"
        self.list_dir_path.mkdir(exist_ok=True)
        date1_str = Datetime.get_short_date_str()
        self.list_file1_path = self.list_dir_path / (date1_str + ".txt")
        date2_str = Datetime.get_short_date_str(datetime.now() - timedelta(days=1))
        self.list_file2_path = self.list_dir_path / (date2_str + ".txt")
        with open(self.list_file2_path, "w", encoding="utf-8") as outfile:
            outfile.write("https://comic.naver.com/webtoon/detail?titleId=725586&no=136\t136화\n")

        self.html_dir_path = self.feed_dir_path / "html"
        self.html_dir_path.mkdir(exist_ok=True)
        md5_name = "3e1c485"
        self.html_file1_path = self.html_dir_path / (md5_name + ".html")
        with open(self.html_file1_path, "w", encoding="utf-8") as outfile:
            outfile.write(
                f"<div>with image tag string</div>\n<img src='https://terzeron.com/img/1x1.jpg?feed=oneplusone.xml&item={md5_name}'/>\n")
        md5_name = "8da6dfb"
        self.html_file2_path = self.html_dir_path / (md5_name + ".html")
        with open(self.html_file2_path, "w", encoding="utf-8") as outfile:
            outfile.write("<div>without image tag string</div>\n")

        self.feed_img_dir_path = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"]) / "img" / feed_name
        self.feed_img_dir_path.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        self.html_file2_path.unlink(missing_ok=True)
        self.html_file1_path.unlink(missing_ok=True)
        shutil.rmtree(self.html_dir_path)

        self.list_file2_path.unlink(missing_ok=True)
        self.list_file1_path.unlink(missing_ok=True)
        shutil.rmtree(self.list_dir_path)

        del self.maker

        self.conf_file_path.unlink(missing_ok=True)
        self.old_rss_file_path.unlink(missing_ok=True)
        self.rss_file_path.unlink(missing_ok=True)
        shutil.rmtree(self.feed_dir_path)

    def test_get_image_tag_str(self):
        actual = FeedMaker._get_image_tag_str(self.rss_file_path.name, self.item1_url)
        expected = "<img src='https://terzeron.com/img/1x1.jpg?feed=oneplusone.xml&item=3e1c485'/>"
        self.assertEqual(expected, actual)

    def test_get_size_of_template_with_image_tag(self):
        actual = FeedMaker.get_size_of_template_with_image_tag(self.rss_file_path.name)
        expected = 407
        self.assertEqual(expected, actual)

    def test_is_image_tag_in_html_file(self):
        image_tag_str = FeedMaker._get_image_tag_str(self.rss_file_path.name, self.item1_url)
        actual = FeedMaker._is_image_tag_in_html_file(self.html_file1_path, image_tag_str)
        expected = True
        self.assertEqual(expected, actual)

    def test_append_image_tag_to_html_file(self):
        img_tag_str = FeedMaker._get_image_tag_str(self.rss_file_path.name, self.item2_url)

        # no image tag in the html file
        is_found = False
        if self.html_file2_path.is_file():
            with open(self.html_file2_path, "r", encoding="utf-8") as infile:
                for line in infile:
                    if img_tag_str in line:
                        is_found = True
        self.assertFalse(is_found)

        FeedMaker._append_image_tag_to_html_file(self.html_file2_path, img_tag_str)

        # image tag is appended to the html file
        is_found = False
        with open(self.html_file2_path, "r", encoding="utf-8") as infile:
            for line in infile:
                if img_tag_str in line:
                    is_found = True
        self.assertTrue(is_found)

    def test_get_size_of_template(self):
        actual = FeedMaker._get_size_of_template()
        expected = 328
        self.assertEqual(expected, actual)

    def test_get_html_file_path(self):
        actual = FeedMaker._get_html_file_path(self.html_dir_path, self.item1_url)
        expected = self.html_file1_path
        self.assertEqual(expected, actual)

    def test_get_list_file_path(self):
        date_str = Datetime.get_short_date_str()
        actual = FeedMaker._get_list_file_path(self.list_dir_path, date_str)
        expected = self.list_file1_path
        self.assertEqual(expected, actual)

    def test_cmp_int_or_str(self):
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

    def test_cmp_to_key(self):
        data_list = [{"id": 1, "sf": "399"}, {"id": 2, "sf": "400"}, {"id": 3, "sf": "398"}]
        actual = sorted(data_list, key=FeedMaker._cmp_to_key(FeedMaker._cmp_int_or_str))
        expected = [{"id": 3, "sf": "398"}, {"id": 1, "sf": "399"}, {"id": 2, "sf": "400"}]
        self.assertEqual(expected, actual)

    def test_make_html_file(self):
        with patch.object(LOGGER, "info") as mock_info:
            actual = self.maker._make_html_file(self.item1_url, "137화")
            self.assertTrue(actual)

            self.assertTrue(assert_in_mock_logger(
                "New: https://comic.naver.com/webtoon/detail?titleId=725586&no=137\t137화\tnaver/oneplusone/html/3e1c485.html",
                mock_info, True))

    def test_get_idx_data(self):
        dt1 = Datetime.get_current_time()
        actual = self.maker._get_idx_data()
        expected = (0, 5)
        dt2 = Datetime.get_current_time()
        self.assertEqual(expected, actual[0:2])
        self.assertTrue(dt1 < actual[2] < dt2)

    def test_write_idx_data(self):
        dt = Datetime.get_current_time()
        ts = Datetime._get_time_str(dt)
        self.maker._write_idx_data(0, dt, True)
        with open(self.maker.start_idx_file_path, "r", encoding="utf-8") as infile:
            actual = infile.read()
            expected = f"0\t{ts}\n"
            self.assertEqual(expected, actual)

        dt = Datetime.get_current_time()
        ts = Datetime._get_time_str(dt)
        self.maker._write_idx_data(0, dt)
        with open(self.maker.start_idx_file_path, "r", encoding="utf-8") as infile:
            actual = infile.read()
            expected = f"0\t{ts}\n"
            self.assertEqual(expected, actual)

    def test_1_read_old_feed_list_from_file(self):
        with patch.object(LOGGER, "info") as mock_info:
            actual = self.maker._read_old_feed_list_from_file()
            self.assertIsNotNone(actual)
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            self.assertEqual(expected, actual)

            self.assertTrue(
                assert_in_mock_logger(self.list_file2_path.relative_to(self.maker.work_dir_path), mock_info))

    def test_2_fetch_old_feed_list_window(self):
        with patch.object(LOGGER, "info") as mock_info:
            old_feed_list = self.maker._read_old_feed_list_from_file()
            actual = self.maker._fetch_old_feed_list_window(old_feed_list)
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            self.assertEqual(expected, actual)

            self.assertTrue(
                assert_in_mock_logger(self.list_file2_path.relative_to(self.maker.work_dir_path), mock_info))
            self.assertTrue(assert_in_mock_logger("start index", mock_info, True))

    def test_3_get_recent_feed_list(self):
        actual = self.maker._get_recent_feed_list()
        self.assertIsNotNone(actual)
        # Do NOT inspect the content of recent feeds
        self.assertEqual(1, len(actual))
        self.assertEqual(2, len(actual[0]))

    def test_4_diff_feeds_and_make_htmls(self):
        with patch.object(LOGGER, "info") as mock_info:
            old_feed_list = self.maker._read_old_feed_list_from_file()
            recent_feed_list = self.maker._get_recent_feed_list()

            actual = self.maker._diff_feeds_and_make_htmls(recent_feed_list=recent_feed_list,
                                                           old_feed_list=old_feed_list)
            # Do NOT inspect the content of recent feeds
            self.assertEqual(2, len(actual))
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            self.assertEqual(expected, actual[1:])

            self.assertTrue(assert_in_mock_logger("Appending 1 new items to the feed list", mock_info))
            self.assertTrue(assert_in_mock_logger("Appending 1 old items to the feed list", mock_info))

    def test_5_generate_rss_feed(self):
        with patch.object(LOGGER, "info") as mock_info:
            old_feed_list = self.maker._read_old_feed_list_from_file()
            recent_feed_list = self.maker._get_recent_feed_list()
            merged_feed_list = self.maker._diff_feeds_and_make_htmls(recent_feed_list=recent_feed_list,
                                                                     old_feed_list=old_feed_list)

            actual = self.maker._generate_rss_feed(merged_feed_list)
            self.assertTrue(actual)

            self.assertTrue(self.rss_file_path.is_file())
            self.assertTrue(self.old_rss_file_path.is_file())

            self.assertTrue(assert_in_mock_logger("Generating rss feed file...", mock_info))

            with open(self.rss_file_path, "r", encoding="utf-8") as infile:
                from xml.dom.minidom import parse, parseString
                document = parse(infile)
                count = 0
                for rss in document.childNodes:
                    for channel in rss.childNodes:
                        for element in channel.childNodes:
                            if element.localName == "item":
                                count += 1
                self.assertEqual(2, count)

    def test_6_make(self):
        with patch.object(LOGGER, "info") as mock_info:
            actual = self.maker.make()
            self.assertTrue(actual)

            self.assertTrue(assert_in_mock_logger("upload success!", mock_info))


if __name__ == "__main__":
    unittest.main()
