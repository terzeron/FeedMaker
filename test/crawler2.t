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

    def test_runHttp(self):
        url = "http://info.cern.ch/"
        crawler = Crawler()
        result, _ = crawler.run(url)
        m = re.search(r'<title>http://info.cern.ch</title>', result)
        self.assertTrue(m)
        del crawler

    def test_runHttps(self):
        url = "https://theuselessweb.site/unicodesnowmanforyou/"
        crawler = Crawler()
        result, _ = crawler.run(url)
        m = re.search(r'&#9731;', result)
        self.assertTrue(m)
        del crawler

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

    def test_imagesInCanvas(self):
        url = "https://terzeron.com/images_in_canvas_test.html"
        crawler = Crawler(render_js=True, copy_images_from_canvas=True)
        result, _ = crawler.run(url)
        m = re.search(r'<div class="images_from_canvas"><img src="data:image/png;base64,iVBORw0KGgoAAAAN.*1WQAAAABJRU5ErkJggg=="></div>', result)
        self.assertTrue(m)
        del crawler

    def tearDown(self):
        if os.path.isfile(COOKIE_FILE):
            os.remove(COOKIE_FILE)


if __name__ == "__main__":
    unittest.main()
