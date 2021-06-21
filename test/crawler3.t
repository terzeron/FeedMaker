#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import unittest
from crawler import Crawler, COOKIE_FILE_FOR_REQUESTS_CLIENT, COOKIE_FILE_FOR_HEADLESS_BROWSER


class CrawlerTest(unittest.TestCase):
    def setUp(self):
        for cookie_file in [COOKIE_FILE_FOR_REQUESTS_CLIENT, COOKIE_FILE_FOR_HEADLESS_BROWSER]:
            if os.path.isfile(cookie_file):
                os.remove(cookie_file)

    def test_runHeadlessBrowser(self):
        url = "https://kr.vuejs.org/v2/guide/index.html"
        crawler = Crawler(render_js=False)
        result, _ = crawler.run(url)
        m = re.search(r'<div id="app-6" class="demo"><p>안녕하세요 Vue!</p> <input></div>', result)
        self.assertFalse(m)
        del crawler

        crawler = Crawler(render_js=True)
        result, _ = crawler.run(url)
        m = re.search(r'<div id="app-6" class="demo"><p>안녕하세요 Vue!</p> <input></div>', result)
        self.assertTrue(m)
        del crawler

    def tearDown(self):
        for cookie_file in [COOKIE_FILE_FOR_REQUESTS_CLIENT, COOKIE_FILE_FOR_HEADLESS_BROWSER]:
            if os.path.isfile(cookie_file):
                os.remove(cookie_file)


if __name__ == "__main__":
    unittest.main()
