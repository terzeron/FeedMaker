#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import unittest
from unittest.mock import patch
from io import StringIO
from crawler import Method, Crawler, HeadlessBrowser, RequestsClient, print_usage, DEFAULT_USER_AGENT


class CrawlerTest(unittest.TestCase):
    def setUp(self):
        for cookie_file in [HeadlessBrowser.COOKIE_FILE, RequestsClient.COOKIE_FILE]:
            if os.path.isfile(cookie_file):
                os.remove(cookie_file)

    def test_print_usage(self):
        with patch('sys.stdout', new=StringIO()) as stdout:
            print_usage()
            actual = stdout.getvalue()
            m = re.search(r'--spider', actual)
            self.assertTrue(m)
            m = re.search(r'--render-js=', actual)
            self.assertTrue(m)
            m = re.search(r'--verify-ssl=', actual)
            self.assertTrue(m)
            m = re.search(r'--download=', actual)
            self.assertTrue(m)
            m = re.search(r'--header=', actual)
            self.assertTrue(m)
            m = re.search(r'--encoding=', actual)
            self.assertTrue(m)
            m = re.search(r'--user-agent=', actual)
            self.assertTrue(m)
            m = re.search(r'--referer=', actual)
            self.assertTrue(m)
            m = re.search(r'--retry=', actual)
            self.assertTrue(m)

    def test_get_option_str(self):
        options = {
            "render_js": True,
            "referer": "https://abc.com",
            "simulate_scrolling": True,
            "timeout": 20,
            "user_agent": "Firefox",
            "encoding": "cp949",
            "header_list": ["Content-Type: application/json", "Transfer-Encoding: chunked"],
            "copy_images_from_canvas": False
        }
        actual = Crawler.get_option_str(options)
        expected = " --render-js=true --copy-images-from-canvas=false --simulate-scrolling=true --user-agent='Firefox' --referer='https://abc.com' --encoding='cp949' --header='Content-Type: application/json' --header='Transfer-Encoding: chunked' --timeout=20"
        self.assertEqual(expected, actual)

    def test_crawler(self):
        crawler = Crawler()
        self.assertTrue(crawler)
        actual, _, _ = crawler.run("https://m.naver.com")
        m = re.search(r'<!DOCTYPE html>', actual, re.IGNORECASE)
        self.assertTrue(m)
        m = re.search(r'<meta property="og:url" content="http://m.naver.com/">', actual)
        self.assertTrue(m)
        del crawler

        crawler = Crawler(method=Method.HEAD)
        self.assertTrue(crawler)
        actual, _, _ = crawler.run("https://m.naver.com")
        self.assertEqual("200", actual)
        del crawler

    def test_crawler_without_options(self):
        # default parameter
        crawler = Crawler()
        client = crawler.requests_client
        self.assertEqual(1, crawler.num_retries)
        self.assertEqual(False, crawler.render_js)
        self.assertEqual(Method.GET, client.method)
        self.assertEqual({"User-Agent": DEFAULT_USER_AGENT}, client.headers)
        self.assertEqual(60, client.timeout)
        self.assertEqual("utf-8", client.encoding)
        self.assertEqual(True, client.verify_ssl)
        del client
        del crawler

    def test_crawler_with_num_retries(self):
        crawler = Crawler(num_retries=3)
        self.assertEqual(3, crawler.num_retries)
        del crawler

    def test_crawler_with_render_js(self):
        crawler = Crawler(render_js=True)
        self.assertEqual(True, crawler.render_js)
        del crawler

        crawler = Crawler(render_js=False)
        self.assertEqual(False, crawler.render_js)
        del crawler

    def test_crawler_with_method(self):
        crawler = Crawler(method=Method.GET)
        client = crawler.requests_client
        self.assertEqual(Method.GET, client.method)
        del client
        del crawler

        crawler = Crawler(method=Method.HEAD)
        client = crawler.requests_client
        self.assertEqual(Method.HEAD, client.method)
        del client
        del crawler

        crawler = Crawler(method=Method.POST)
        client = crawler.requests_client
        self.assertEqual(Method.POST, client.method)
        del client
        del crawler

    def test_crawler_with_headers(self):
        crawler = Crawler(headers={})
        client = crawler.requests_client
        self.assertEqual({'User-Agent': DEFAULT_USER_AGENT}, client.headers)
        del client
        del crawler

        crawler = Crawler(headers={"Referer": "https://m.naver.com"})
        client = crawler.requests_client
        self.assertEqual({"Referer": "https://m.naver.com", 'User-Agent': DEFAULT_USER_AGENT}, client.headers)
        del client
        del crawler

    def test_crawler_with_timeout(self):
        crawler = Crawler(timeout=5)
        client = crawler.requests_client
        self.assertEqual(5, client.timeout)
        del client
        del crawler

    def test_crawler_with_encoding(self):
        crawler = Crawler(encoding="cp949")
        client = crawler.requests_client
        self.assertEqual("cp949", client.encoding)
        del client
        del crawler

        crawler = Crawler(encoding="utf-8")
        client = crawler.requests_client
        self.assertEqual("utf-8", client.encoding)
        del client
        del crawler

    def test_crawler_with_verify_ssl(self):
        crawler = Crawler(verify_ssl=False)
        client = crawler.requests_client
        self.assertEqual(False, client.verify_ssl)
        del client
        del crawler

        crawler = Crawler(verify_ssl=True)
        client = crawler.requests_client
        self.assertEqual(True, client.verify_ssl)
        del client
        del crawler

    def tearDown(self):
        for cookie_file in [HeadlessBrowser.COOKIE_FILE, RequestsClient.COOKIE_FILE]:
            if os.path.isfile(cookie_file):
                os.remove(cookie_file)


if __name__ == "__main__":
    unittest.main()
