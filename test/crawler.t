#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import unittest
from unittest.mock import patch
from io import StringIO
from feed_maker_util import kill_process_group
from crawler import Method, Crawler, print_usage


class CrawlerTest(unittest.TestCase):
    def setUp(self):
        pass

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
        result = crawler.run("https://m.naver.com")
        m = re.search(r'<!DOCTYPE html>', result)
        self.assertTrue(m)
        m = re.search(r'<meta property="og:url" content="http://m.naver.com/">', result)
        self.assertTrue(m)
        del crawler

        crawler = Crawler(method=Method.HEAD)
        self.assertTrue(crawler)
        result = crawler.run("https://m.naver.com")
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
        self.assertEqual({}, client.headers)
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
        self.assertEqual({}, client.headers)
        del client
        del crawler
        crawler = Crawler(headers={"Referer": "https://m.naver.com"})
        client = crawler.requests_client
        self.assertEqual({"Referer": "https://m.naver.com"}, client.headers)
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

    def test_runHttp(self):
        url = "http://info.cern.ch/"
        crawler = Crawler()
        result = crawler.run(url)
        m = re.search(r'<title>http://info.cern.ch</title>', result)
        self.assertTrue(m)
        del crawler

    def test_runHttps(self):
        url = "https://theuselessweb.site/unicodesnowmanforyou/"
        crawler = Crawler()
        result = crawler.run(url)
        m = re.search(r'&#9731;', result)
        self.assertTrue(m)
        del crawler

    def test_runHeadlessBrowser(self):
        url = "https://kr.vuejs.org/v2/guide/index.html"
        crawler = Crawler(render_js=False)
        result = crawler.run(url)
        m = re.search(r'<div id="app-6" class="demo"><p>안녕하세요 Vue!</p> <input></div>', result)
        self.assertFalse(m)
        del crawler
        
        crawler = Crawler(render_js=True)
        result = crawler.run(url)
        m = re.search(r'<div id="app-6" class="demo"><p>안녕하세요 Vue!</p> <input></div>', result)
        self.assertTrue(m)
        del crawler

    def tearDown(self):
        kill_process_group("chromedriver")
        kill_process_group("chrome")


if __name__ == "__main__":
    unittest.main()
