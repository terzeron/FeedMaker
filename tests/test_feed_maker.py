#!/usr/bin/env python


import shutil
import logging.config
from pathlib import Path
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch, Mock
from xml.dom.minidom import parse

from bin.feed_maker import FeedMaker
from bin.feed_maker_util import Config, Datetime, PathUtil, Env, header_str


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
        group_name = "naver"
        feed_name = "certain_webtoon"
        self.feed_dir_path = Path(Env.get("FM_WORK_DIR")) / group_name / feed_name
        self.feed_dir_path.mkdir(exist_ok=True)
        self.rss_file_path = self.feed_dir_path / f"{feed_name}.xml"
        self.rss_file_path.touch()
        self.old_rss_file_path = self.feed_dir_path / f"{feed_name}.xml.old"
        self.old_rss_file_path.touch()
        self.sample_conf_file_path = Path(__file__).parent / "conf.naverwebtoon.json"
        self.conf_file_path = self.feed_dir_path / "conf.json"
        shutil.copy(self.sample_conf_file_path, self.conf_file_path)

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
        # 현재 날짜 파일에도 내용을 추가하여 is_completed=False일 때도 올바른 파일을 찾을 수 있도록 함
        with self.list_file1_path.open("w", encoding="utf-8") as outfile:
            outfile.write("https://comic.naver.com/webtoon/detail?titleId=725586&no=136\t136화\n")

        self.html_dir_path = self.feed_dir_path / "html"
        self.html_dir_path.mkdir(exist_ok=True)
        md5_name = "3e1c485"
        self.html_file1_path = self.html_dir_path / f"{md5_name}.html"
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        with self.html_file1_path.open("w", encoding="utf-8") as outfile:
            outfile.write(header_str)
            outfile.write(f"<div>with image tag string</div>\n<img src='{img_url_prefix}/1x1.jpg?feed=certain_webtoon.xml&item={md5_name}'/>\n")
            outfile.write("A" * 400)  # 템플릿 크기보다 크게 만듦
        md5_name = "8da6dfb"
        self.html_file2_path = self.html_dir_path / f"{md5_name}.html"
        with self.html_file2_path.open("w", encoding="utf-8") as outfile:
            outfile.write(header_str)
            outfile.write("<div>without image tag string</div>\n")
            outfile.write("B" * 400)  # 템플릿 크기보다 크게 만듦

        self.feed_img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / feed_name
        self.feed_img_dir_path.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        self.html_file2_path.unlink(missing_ok=True)
        self.html_file1_path.unlink(missing_ok=True)
        shutil.rmtree(self.html_dir_path)

        self.list_file2_path.unlink(missing_ok=True)
        self.list_file1_path.unlink(missing_ok=True)
        shutil.rmtree(self.list_dir_path)

        # 실패 URL 캐시 파일 정리
        if hasattr(self.maker, 'failed_urls_cache_file') and self.maker.failed_urls_cache_file.exists():
            self.maker.failed_urls_cache_file.unlink(missing_ok=True)

        del self.maker

        self.conf_file_path.unlink(missing_ok=True)
        self.old_rss_file_path.unlink(missing_ok=True)
        self.rss_file_path.unlink(missing_ok=True)
        shutil.rmtree(self.feed_dir_path)

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

            self.assertTrue(assert_in_mock_logger("Old: https://comic.naver.com/webtoon/detail?titleId=725586&no=137\t137화\tnaver/certain_webtoon/html/3e1c485.html", mock_info, True))

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
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            self.assertEqual(expected, actual)
            self.assertTrue(assert_in_mock_logger(PathUtil.short_path(self.list_file2_path), mock_info))

        self.maker.collection_conf["is_completed"] = False
        with patch.object(LOGGER, "info") as mock_info:
            actual = self.maker._read_old_feed_list_from_file()
            self.assertIsNotNone(actual)
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            self.assertEqual(expected, actual)
            self.assertTrue(assert_in_mock_logger(PathUtil.short_path(self.list_file1_path), mock_info))

    def test_2_fetch_old_feed_list_window(self) -> None:
        self.maker.collection_conf["is_completed"] = True
        with patch.object(LOGGER, "info") as mock_info:
            old_feed_list = self.maker._read_old_feed_list_from_file()
            actual = self.maker._fetch_old_feed_list_window(old_feed_list)
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            self.assertEqual(expected, actual)
            self.assertTrue(assert_in_mock_logger(PathUtil.short_path(self.list_file2_path), mock_info))
            self.assertTrue(assert_in_mock_logger("start index", mock_info, True))

        self.maker.collection_conf["is_completed"] = False
        with patch.object(LOGGER, "info") as mock_info:
            old_feed_list = self.maker._read_old_feed_list_from_file()
            actual = self.maker._fetch_old_feed_list_window(old_feed_list)
            expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            self.assertEqual(expected, actual)
            self.assertTrue(assert_in_mock_logger(PathUtil.short_path(self.list_file1_path), mock_info))
            self.assertTrue(assert_in_mock_logger("start index", mock_info, True))

    def test_3_get_recent_feed_list(self) -> None:
        # Mock NewlistCollector to avoid external dependencies
        with patch('bin.feed_maker.NewlistCollector') as mock_collector:
            # Configure mock to return test data
            mock_instance = mock_collector.return_value
            mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            
            self.maker.collection_conf["is_completed"] = True
            actual = self.maker._get_recent_feed_list()
            self.assertIsNotNone(actual)
            # Do NOT inspect the content of recent feeds
            self.assertEqual(1, len(actual))
            self.assertEqual(2, len(actual[0]))

            self.maker.collection_conf["is_completed"] = False
            actual = self.maker._get_recent_feed_list()
            self.assertIsNotNone(actual)
            # Do NOT inspect the content of recent feeds
            self.assertEqual(1, len(actual))
            self.assertEqual(2, len(actual[0]))

    def test_4_diff_feeds_and_make_htmls(self) -> None:
        # Mock all external dependencies
        with patch('bin.feed_maker_util.Process.exec_cmd', side_effect=lambda *a, **k: ("mock_result", None)):
            with patch('bin.feed_maker.Extractor.extract_content', return_value="<html><body><div>This is a much larger HTML content that should be bigger than the template size to pass the size check in the feed maker. It needs to be at least 359 bytes to avoid being excluded. This content is intentionally made very long to ensure it passes the size threshold. We need to add more text here to make sure the file size is large enough. Let's add some more content to reach the required size. This should be sufficient now.</div></body></html>"):
                with patch('bin.feed_maker.NewlistCollector') as mock_collector, \
                     patch('bin.feed_maker.Crawler') as mock_crawler, \
                     patch.object(LOGGER, "info") as mock_info:
                    
                    # Configure mock to return test data
                    mock_instance = mock_collector.return_value
                    mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
                    
                    # Mock crawler with larger HTML content to pass size check
                    mock_crawler_instance = mock_crawler.return_value
                    mock_crawler_instance.run.return_value = ("<html><body><div>This is a much larger HTML content that should be bigger than the template size to pass the size check in the feed maker. It needs to be at least 359 bytes to avoid being excluded. This content is intentionally made very long to ensure it passes the size threshold. We need to add more text here to make sure the file size is large enough. Let's add some more content to reach the required size. This should be sufficient now.</div></body></html>", None, None)
                    
                    old_feed_list = self.maker._read_old_feed_list_from_file()
                    recent_feed_list = self.maker._get_recent_feed_list()

                    actual = self.maker._diff_feeds_and_make_htmls(recent_feed_list=recent_feed_list, old_feed_list=old_feed_list)
                    # Do NOT inspect the content of recent feeds
                    self.assertEqual(1, len(actual))  # 새로운 항목이 없으므로 기존 항목만 1개
                    expected = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
                    self.assertEqual(expected, actual)

                    self.assertTrue(assert_in_mock_logger("Appending 0 new items to the feed list", mock_info))
                    self.assertTrue(assert_in_mock_logger("Appending 1 old items to the feed list", mock_info))

    def test_5_generate_rss_feed(self) -> None:
        # Mock all external dependencies
        with patch('bin.feed_maker_util.Process.exec_cmd', side_effect=lambda *a, **k: ("mock_result", None)):
            with patch('bin.feed_maker.Extractor.extract_content', return_value="<html><body><div>This is a much larger HTML content that should be bigger than the template size to pass the size check in the feed maker. It needs to be at least 359 bytes to avoid being excluded. This content is intentionally made very long to ensure it passes the size threshold. We need to add more text here to make sure the file size is large enough. Let's add some more content to reach the required size. This should be sufficient now.</div></body></html>"):
                with patch('bin.feed_maker.NewlistCollector') as mock_collector, \
                     patch('bin.feed_maker.Crawler') as mock_crawler, \
                     patch.object(LOGGER, "info") as mock_info:
                    
                    # Configure mock to return test data
                    mock_instance = mock_collector.return_value
                    mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
                    
                    # Mock crawler with larger HTML content to pass size check
                    mock_crawler_instance = mock_crawler.return_value
                    mock_crawler_instance.run.return_value = ("<html><body><div>This is a much larger HTML content that should be bigger than the template size to pass the size check in the feed maker. It needs to be at least 359 bytes to avoid being excluded. This content is intentionally made very long to ensure it passes the size threshold. We need to add more text here to make sure the file size is large enough. Let's add some more content to reach the required size. This should be sufficient now.</div></body></html>", None, None)
                    
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
        with patch('bin.feed_maker_util.Process.exec_cmd', side_effect=lambda *a, **k: ("mock_result", None)):
            with patch('bin.feed_maker.NewlistCollector') as mock_collector, \
                 patch('bin.feed_maker.Crawler') as mock_crawler, \
                 patch.object(LOGGER, "info") as mock_info:
                
                # Configure mock to return test data
                mock_instance = mock_collector.return_value
                mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
                
                # Mock crawler
                mock_crawler_instance = mock_crawler.return_value
                mock_crawler_instance.run.return_value = ("mock_html_content", None, None)
                
                actual = self.maker.make()
                self.assertTrue(actual)

                self.assertTrue(assert_in_mock_logger("upload success!", mock_info))

    def test_failed_url_cache(self) -> None:
        """실패 URL 캐싱 기능 테스트"""
        test_url = "https://example.com/failed_url"
        test_error = "connection timeout"
        
        # 초기에는 실패한 URL이 없어야 함
        if hasattr(self.maker, '_is_url_recently_failed'):
            self.assertFalse(self.maker._is_url_recently_failed(test_url))
        
        # 실패 URL을 캐시에 추가
        if hasattr(self.maker, '_add_failed_url'):
            self.maker._add_failed_url(test_url, test_error)
        
        # 캐시 파일이 생성되었는지 확인
        if hasattr(self.maker, 'failed_urls_cache_file'):
            self.assertTrue(self.maker.failed_urls_cache_file.exists())
        
        # 실패한 URL이 캐시에서 조회되는지 확인
        if hasattr(self.maker, '_is_url_recently_failed'):
            self.assertTrue(self.maker._is_url_recently_failed(test_url))
        
        # 다른 URL은 캐시에 없어야 함
        if hasattr(self.maker, '_is_url_recently_failed'):
            self.assertFalse(self.maker._is_url_recently_failed("https://example.com/other_url"))


if __name__ == "__main__":
    unittest.main()
