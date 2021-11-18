#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import unittest
from crawler import Crawler, HeadlessBrowser, RequestsClient


class CrawlerTest(unittest.TestCase):
    def setUp(self):
        for cookie_file in [HeadlessBrowser.COOKIE_FILE, RequestsClient.COOKIE_FILE]:
            if os.path.isfile(cookie_file):
                os.remove(cookie_file)

    def test_runHttp(self):
        url = "http://info.cern.ch/"
        crawler = Crawler()
        actual, _, _ = crawler.run(url)
        m = re.search(r'<title>http://info.cern.ch</title>', actual)
        self.assertTrue(m)
        del crawler

    def test_runHttps(self):
        url = "https://theuselessweb.site/unicodesnowmanforyou/"
        crawler = Crawler()
        actual, _, _ = crawler.run(url)
        m = re.search(r'&#9731;', actual)
        self.assertTrue(m)
        del crawler

    def test_imagesInCanvas(self):
        url = "https://terzeron.com/images_in_canvas_test.html"
        crawler = Crawler(render_js=True, copy_images_from_canvas=True)
        actual, _, _ = crawler.run(url)
        m = re.search(r'<div class="images_from_canvas"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAABkCAYAAADDhn8LAAAAAX.*KBUgI3O8Nj9LDhwKlP8DuACSYNiipSoAAAAASUVORK5CYII="></div>', actual)
        self.assertTrue(m)
        del crawler

    def tearDown(self):
        for cookie_file in [HeadlessBrowser.COOKIE_FILE, RequestsClient.COOKIE_FILE]:
            if os.path.isfile(cookie_file):
                os.remove(cookie_file)


if __name__ == "__main__":
    unittest.main()