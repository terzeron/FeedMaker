#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import unittest
from unittest.mock import patch
from io import StringIO
#from feed_maker_util import kill_process_group
from crawler import Method, Crawler, print_usage, COOKIE_FILE, DEFAULT_USER_AGENT


class CrawlerTest(unittest.TestCase):
    def setUp(self):
        if os.path.isfile(COOKIE_FILE):
            os.remove(COOKIE_FILE)

    def test_printUsage(self):
        with patch('sys.stdout', new=StringIO()) as stdout:
            print_usage()
            result = stdout.getvalue()
            m = re.search(r'--spider', result)
            self.assertTrue(m)
            m = re.search(r'--render-js=', result)
            self.assertTrue(m)
            m = re.search(r'--verify-ssl=', result)
            self.assertTrue(m)
            m = re.search(r'--download=', result)
            self.assertTrue(m)
            m = re.search(r'--header=', result)
            self.assertTrue(m)
            m = re.search(r'--encoding=', result)
            self.assertTrue(m)
            m = re.search(r'--user-agent=', result)
            self.assertTrue(m)
            m = re.search(r'--referer=', result)
            self.assertTrue(m)
            m = re.search(r'--retry=', result)
            self.assertTrue(m)

    def test_basicInstantiation(self):
        crawler = Crawler()
        self.assertTrue(crawler)
        result, _ = crawler.run("https://m.naver.com")
        m = re.search(r'<!DOCTYPE html>', result, re.IGNORECASE)
        self.assertTrue(m)
        m = re.search(r'<meta property="og:url" content="http://m.naver.com/">', result)
        self.assertTrue(m)
        del crawler

        crawler = Crawler(method=Method.HEAD)
        self.assertTrue(crawler)
        result, _ = crawler.run("https://m.naver.com")
        self.assertEqual("200", result)
        del crawler

    def test_instantiateWithOptions(self):
        # default parameter
        crawler = Crawler()
        client = crawler.requests_client
        self.assertEqual(1, crawler.num_retries)
        self.assertEqual(False, crawler.render_js)
        self.assertEqual(Method.GET, client.method)
        self.assertEqual(10, client.timeout)
        #self.assertEqual({}, client.headers)
        self.assertEqual(None, client.encoding)
        self.assertEqual(True, client.verify_ssl)
        del client
        del crawler

        crawler = Crawler(num_retries=3)
        self.assertEqual(3, crawler.num_retries)
        del crawler

        crawler = Crawler(render_js=True)
        self.assertEqual(True, crawler.render_js)
        del crawler
        crawler = Crawler(render_js=False)
        self.assertEqual(False, crawler.render_js)
        del crawler

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

        crawler = Crawler(timeout=5)
        client = crawler.requests_client
        self.assertEqual(5, client.timeout)
        del client
        del crawler

        crawler = Crawler(encoding="cp949")
        client = crawler.requests_client
        self.assertEqual("cp949", client.encoding)
        del client
        del crawler

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
        if os.path.isfile(COOKIE_FILE):
            os.remove(COOKIE_FILE)


if __name__ == "__main__":
    unittest.main()
