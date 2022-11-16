#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import unittest
from crawler import Crawler, HeadlessBrowser, RequestsClient


class CrawlerTest(unittest.TestCase):
    def setUp(self):
        for cookie_file in (HeadlessBrowser.COOKIE_FILE, RequestsClient.COOKIE_FILE):
            if os.path.isfile(cookie_file):
                os.remove(cookie_file)

    def test_runHeadlessBrowser(self):
        url = "https://facebook.com"
        crawler = Crawler(render_js=False)
        actual, _, _ = crawler.run(url)
        m = re.search(r'이메일', actual)
        self.assertFalse(m)
        del crawler

        crawler = Crawler(render_js=True)
        actual, _, _ = crawler.run(url)
        m = re.search(r'이메일', actual)
        self.assertTrue(m)
        del crawler

    def tearDown(self):
        for cookie_file in (HeadlessBrowser.COOKIE_FILE, RequestsClient.COOKIE_FILE):
            if os.path.isfile(cookie_file):
                os.remove(cookie_file)


if __name__ == "__main__":
    unittest.main()
