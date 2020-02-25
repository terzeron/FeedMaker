#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import unittest
from unittest.mock import patch
from io import StringIO
from feed_maker_util import exec_cmd, remove_file
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
            m = re.search(r'--sleep-time=', result)
            self.assertTrue(m)

    def test_basicInstantiation(self):
        crawler = Crawler()
        self.assertTrue(crawler)
        result = crawler.run("https://m.naver.com")
        m = re.search(r'<!DOCTYPE html>', result)
        self.assertTrue(m)
        m = re.search(r'<meta property="og:url" content="http://m.naver.com/">', result)
        self.assertTrue(m)
        
        crawler = Crawler(method=Method.HEAD)
        self.assertTrue(crawler)
        result = crawler.run("https://m.naver.com")
        self.assertEqual(200, result)

    def test_instantiateWithOptions(self):
        # default parameter
        crawler = Crawler()
        self.assertEqual(Method.GET, crawler.method)
        self.assertEqual({}, crawler.headers)
        self.assertEqual(10, crawler.timeout)
        self.assertEqual(1, crawler.num_retries)
        self.assertEqual(None, crawler.sleep_time)
        self.assertEqual(False, crawler.render_js)
        self.assertEqual(None, crawler.download_file)
        self.assertEqual(None, crawler.encoding)
        self.assertEqual(True, crawler.verify_ssl)

        crawler = Crawler(method=Method.GET)
        self.assertEqual(Method.GET, crawler.method)
        crawler = Crawler(method=Method.HEAD)
        self.assertEqual(Method.HEAD, crawler.method)
        crawler = Crawler(method=Method.POST)
        self.assertEqual(Method.POST, crawler.method)

        crawler = Crawler(headers={})
        self.assertEqual({}, crawler.headers)
        crawler = Crawler(headers={"Referer": "https://m.naver.com"})
        self.assertEqual({"Referer": "https://m.naver.com"}, crawler.headers)

        crawler = Crawler(timeout=5)
        self.assertEqual(5, crawler.timeout)

        crawler = Crawler(num_retries=3)
        self.assertEqual(3, crawler.num_retries)

        crawler = Crawler(sleep_time=6)
        self.assertEqual(6, crawler.sleep_time)

        crawler = Crawler(render_js=True)
        self.assertEqual(True, crawler.render_js)
        crawler = Crawler(render_js=False)
        self.assertEqual(False, crawler.render_js)

        crawler = Crawler(download_file="test.html")
        self.assertEqual("test.html", crawler.download_file)

        crawler = Crawler(encoding="cp949")
        self.assertEqual("cp949", crawler.encoding)

        crawler = Crawler(verify_ssl=False)
        self.assertEqual(False, crawler.verify_ssl)
        crawler = Crawler(verify_ssl=True)
        self.assertEqual(True, crawler.verify_ssl)

    def test_runHttp(self):
        url = "http://info.cern.ch/"
        crawler = Crawler()
        result = crawler.run(url)
        m = re.search(r'<title>http://info.cern.ch</title>', result)
        self.assertTrue(m)

    def test_runHttps(self):
        url = "https://theuselessweb.site/unicodesnowmanforyou/"
        crawler = Crawler()
        result = crawler.run(url)
        m = re.search(r'&#9731;', result)
        self.assertTrue(m)

    def test_runHeadlessBrowser(self):
        url = "https://kr.vuejs.org/v2/guide/index.html"
        crawler = Crawler(render_js=False)
        result = crawler.run(url)
        m = re.search(r'<div id="app-6" class="demo"><p>안녕하세요 Vue!</p> <input></div>', result)
        self.assertFalse(m)
        crawler = Crawler(render_js=True)
        result = crawler.run(url) 
        m = re.search(r'<div id="app-6" class="demo"><p>안녕하세요 Vue!</p> <input></div>', result)
        self.assertTrue(m)

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
