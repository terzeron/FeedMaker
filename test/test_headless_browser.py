#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
from pathlib import Path
import unittest
from bin.headless_browser import HeadlessBrowser


class TestHeadlessBrowser(unittest.TestCase):
    def setUp(self) -> None:
        if os.path.isfile(HeadlessBrowser.COOKIE_FILE):
            os.remove(HeadlessBrowser.COOKIE_FILE)

    def tearDown(self) -> None:
        self.setUp()

    def test_headless_browser(self) -> None:
        browser = HeadlessBrowser()
        self.assertEqual(Path.cwd(), browser.dir_path)
        self.assertEqual({"User-Agent": HeadlessBrowser.DEFAULT_USER_AGENT}, browser.headers)
        self.assertFalse(browser.copy_images_from_canvas)
        self.assertFalse(browser.simulate_scrolling)
        self.assertFalse(browser.disable_headless)
        self.assertFalse(browser.blob_to_dataurl)
        self.assertEqual(60, browser.timeout)
        del browser

    def test_make_request(self) -> None:
        browser = HeadlessBrowser()
        url = "https://terzeron.com/crawler/js_rendering.html"
        actual = browser.make_request(url)
        self.assertIn('<div><span>Hello, World!</span></div>', actual)
        del browser

    def test_headless_browser_with_copy_images_from_canvas(self) -> None:
        browser = HeadlessBrowser(copy_images_from_canvas=True)
        url = "https://terzeron.com/crawler/images_in_canvas_test.html"
        actual = browser.make_request(url)
        self.assertIn('<div class="images_from_canvas"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUh', actual)
        del browser

    def test_headless_browser_with_simulate_scrolling(self) -> None:
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

    def test_headless_browser_with_blob_to_dataurl(self) -> None:
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

    def test_headless_browser_with_headers(self) -> None:
        browser = HeadlessBrowser(headers={"User-Agent": "Mozilla"})
        self.assertEqual("Mozilla", browser.headers["User-Agent"])
        del browser

    def test_headless_browser_with_disable_headless(self) -> None:
        browser = HeadlessBrowser(disable_headless=True)
        self.assertTrue(browser.disable_headless)
        del browser

    def test_headless_browser_with_timeout(self) -> None:
        browser = HeadlessBrowser(timeout=10)
        self.assertEqual(10, browser.timeout)
        del browser


if __name__ == "__main__":
    unittest.main()
