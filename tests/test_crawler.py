#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import logging
import os
import re
import shutil
import sys
import time
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

import requests

from bin.crawler import Crawler, Method, print_usage, DEFAULT_USER_AGENT, RequestsClient
from bin.headless_browser import HeadlessBrowser

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Common mock responses
MOCK_HTML_RESPONSE = ('<!DOCTYPE html><html><body>Test</body></html>', '', {}, 200)
MOCK_BASIC_HTML = ('<!DOCTYPE html><html><head><title>Basic Test</title></head><body><h1>Basic Test Page</h1></body></html>', '', {}, 200)
MOCK_UNICODE_HTML = ('<!DOCTYPE html><html><body>안녕하세요</body></html>', '', {}, 200)
MOCK_HEADLESS_HTML = '<!DOCTYPE html><html><body>Test</body></html>'


class TestCrawler(unittest.TestCase):
    """Test Crawler with mock responses"""

    @classmethod
    def setUpClass(cls) -> None:
        # patcher 등록
        cls.patcher_remove = patch('os.remove')
        cls.patcher_isfile = patch('os.path.isfile', return_value=True)
        cls.mock_remove = cls.patcher_remove.start()
        cls.mock_isfile = cls.patcher_isfile.start()
        # Clean up cookie files once at the beginning (실제 파일 접근 없음)
        for cookie_file in (HeadlessBrowser.COOKIE_FILE, RequestsClient.COOKIE_FILE):
            try:
                if os.path.isfile(cookie_file):
                    os.remove(cookie_file)
            except (OSError, ImportError):
                pass

    @classmethod
    def tearDownClass(cls) -> None:
        cls.patcher_remove.stop()
        cls.patcher_isfile.stop()

    def setUp(self) -> None:
        # 각 테스트마다 requests, time.sleep 등 patch
        self.patcher_sleep = patch('time.sleep')
        self.patcher_requests = patch('requests.get')
        self.mock_sleep = self.patcher_sleep.start()
        self.mock_requests = self.patcher_requests.start()

    def tearDown(self) -> None:
        self.patcher_sleep.stop()
        self.patcher_requests.stop()

    def test_print_usage(self) -> None:
        with patch('sys.stdout', new=io.StringIO()) as stdout:
            print_usage()
            output = stdout.getvalue()
            self.assertIn("Usage:", output)
            self.assertIn("--render-js", output)

    def test_get_option_str(self) -> None:
        options = {
            "render_js": True,
            "copy_images_from_canvas": False,
            "simulate_scrolling": True,
            "user_agent": "Firefox",
            "referer": "https://abc.com",
            "encoding": "cp949",
            "headers": {"Content-Type": "application/json", "Transfer-Encoding": "chunked"},
            "timeout": 20
        }
        actual = Crawler.get_option_str(options)
        expected = " --render-js=true --copy-images-from-canvas=false --simulate-scrolling=true --user-agent='Firefox' --referer='https://abc.com' --encoding='cp949' --header='Content-Type: application/json; Transfer-Encoding: chunked' --timeout=20"
        self.assertEqual(expected, actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_crawler_basic(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_BASIC_HTML
        
        crawler = Crawler()
        self.assertTrue(crawler)
        url = "http://test.com/basic.html"
        actual, _, _ = crawler.run(url)
        
        self.assertIsNotNone(actual)
        if actual:
            m = re.search(r'<!DOCTYPE html>', actual, re.IGNORECASE)
            self.assertTrue(m)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_crawler_without_options(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        crawler = Crawler()
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_crawler_with_num_retries(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        crawler = Crawler(num_retries=3)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_crawler_with_render_js(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HEADLESS_HTML
        
        crawler = Crawler(render_js=True)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_crawler_with_method(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        # Test HEAD method
        crawler = Crawler(method=Method.HEAD)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)
        
        # Test GET method
        crawler = Crawler(method=Method.GET)
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_crawler_with_headers(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        headers = {"User-Agent": "TestBot", "Referer": "http://test.com"}
        crawler = Crawler(headers=headers)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_crawler_with_timeout(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        crawler = Crawler(timeout=30)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_crawler_with_encoding(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        crawler = Crawler(encoding="cp949")
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_crawler_with_verify_ssl(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        crawler = Crawler(verify_ssl=False)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_run_https_with_unicode(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_UNICODE_HTML
        
        crawler = Crawler()
        url = "https://test.com/unicode.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    @patch('time.sleep')  # Mock time.sleep to avoid 5-second delay
    def test_crawler_network_retry(self, mock_sleep: MagicMock, mock_make_request: MagicMock) -> None:
        # Mock with side effect for retry logic
        mock_make_request.side_effect = [
            ('', 'Network error', {}, 500),  # First call fails
            ('<!DOCTYPE html><html><body>Success</body></html>', '', {}, 200)  # Second call succeeds
        ]
        
        crawler = Crawler(num_retries=2)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_crawler_with_custom_headers(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        custom_headers = {"X-Custom-Header": "test-value"}
        crawler = Crawler(headers=custom_headers)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_crawler_with_headless_browser_options(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HEADLESS_HTML
        
        crawler = Crawler(
            render_js=True,
            simulate_scrolling=True,
            copy_images_from_canvas=True
        )
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_crawler_multiple_requests(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        crawler = Crawler()
        urls = [
            "http://test.com/page1.html",
            "http://test.com/page2.html",
            "http://test.com/page3.html"
        ]
        
        for url in urls:
            actual, _, _ = crawler.run(url)
            self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_user_agent_header(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = ('<!DOCTYPE html><html><body><div id="user-agent">TestBot</div></body></html>', '', {}, 200)
        
        headers = {"User-Agent": "TestBot"}
        crawler = Crawler(headers=headers)
        url = "http://test.com/echo_headers.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_referer_header(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = ('<!DOCTYPE html><html><body><div id="referer">http://test.com/referer</div></body></html>', '', {}, 200)
        
        headers = {"Referer": "http://test.com/referer"}
        crawler = Crawler(headers=headers)
        url = "http://test.com/echo_headers.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_encoding_utf8(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = ('<!DOCTYPE html><html><body><div id="utf8">안녕하세요</div></body></html>', '', {}, 200)
        
        crawler = Crawler(encoding="utf-8")
        url = "http://test.com/utf8.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_encoding_cp949(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = ('<!DOCTYPE html><html><body><div id="cp949">안녕하세요</div></body></html>', '', {}, 200)
        
        crawler = Crawler(encoding="cp949")
        url = "http://test.com/cp949.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_method_head(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        crawler = Crawler(method=Method.HEAD)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)

    @patch('bin.crawler.RequestsClient.make_request')
    def test_method_get(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE
        
        crawler = Crawler(method=Method.GET)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIsNotNone(actual)


if __name__ == "__main__":
    unittest.main()
