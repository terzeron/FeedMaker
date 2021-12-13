#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
from pathlib import Path
import unittest
from headless_browser import HeadlessBrowser


class TestHeadlessBrowser(unittest.TestCase):
    def setUp(self):
        if os.path.isfile(HeadlessBrowser.COOKIE_FILE):
            os.remove(HeadlessBrowser.COOKIE_FILE)

    def tearDown(self):
        if os.path.isfile(HeadlessBrowser.COOKIE_FILE):
            os.remove(HeadlessBrowser.COOKIE_FILE)

    def test_headless_browser(self):
        browser = HeadlessBrowser()
        self.assertEqual(Path.cwd(), browser.dir_path)
        self.assertEqual({"User-Agent": HeadlessBrowser.DEFAULT_USER_AGENT}, browser.headers)
        self.assertEqual(False, browser.copy_images_from_canvas)
        self.assertEqual(False, browser.simulate_scrolling)
        self.assertEqual(False, browser.disable_headless)
        self.assertEqual(False, browser.blob_to_dataurl)
        self.assertEqual(60, browser.timeout)
        del browser

    def test_make_request(self):
        browser = HeadlessBrowser()
        url = "https://chromedriver.chromium.org/downloads/version-selection"
        actual = browser.make_request(url)
        self.assertIn('Version Selection', actual)
        del browser

    def test_headless_browser_with_copy_images_from_canvas(self):
        browser = HeadlessBrowser(copy_images_from_canvas=True)
        url = "https://terzeron.com/crawler/images_in_canvas_test.html"
        actual = browser.make_request(url)
        self.assertIn('<div class="images_from_canvas"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUh', actual)
        del browser

    def test_headless_browser_with_simulate_scrolling(self):
        browser = HeadlessBrowser(simulate_scrolling=False)
        url = "https://terzeron.com/crawler/lazy_loading_scrolling_test.html"
        actual = browser.make_request(url)
        self.assertNotIn('<p>image rendered</p>', actual)
        del browser

        browser = HeadlessBrowser(simulate_scrolling=True)
        url = "https://terzeron.com/crawler/lazy_loading_scrolling_test.html"
        actual = browser.make_request(url)
        self.assertIn('<p>image rendered</p>', actual)
        del browser

    def test_headless_browser_with_blob_to_dataurl(self):
        browser = HeadlessBrowser(blob_to_dataurl=False)
        url = "https://terzeron.com/crawler/blob_image_test.html"
        actual = browser.make_request(url)
        self.assertIn('<img src="blob:https://terzeron.com/', actual)
        del browser

        browser = HeadlessBrowser(blob_to_dataurl=True)
        url = "https://terzeron.com/crawler/blob_image_test.html"
        actual = browser.make_request(url)
        self.assertIn('<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA', actual)
        del browser

    def test_headless_browser_with_headers(self):
        browser = HeadlessBrowser(headers={"User-Agent": "Mozilla"})
        self.assertEqual("Mozilla", browser.headers["User-Agent"])
        del browser

    def test_headless_browser_with_disable_headless(self):
        browser = HeadlessBrowser(disable_headless=True)
        self.assertEqual(True, browser.disable_headless)
        del browser

    def test_headless_browser_with_timeout(self):
        browser = HeadlessBrowser(timeout=10)
        self.assertEqual(10, browser.timeout)
        del browser


if __name__ == "__main__":
    unittest.main()
