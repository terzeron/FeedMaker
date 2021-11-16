#!/usr/bin/env python
# -*- coding: utf-8 -*-


import re
import json
import unittest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from headless_browser import HeadlessBrowser


class TestHeadlessBrowser(unittest.TestCase):
    def setUp(self):
        self.browser = HeadlessBrowser()
        self.cookie_file_path = self.browser.dir_path / HeadlessBrowser.COOKIE_FILE

    def tearDown(self) -> None:
        del self.browser
        del self.cookie_file_path

    def test_make_request(self):
        url = "https://chromedriver.chromium.org/downloads/version-selection"
        actual = self.browser.make_request(url)
        matched = re.search(r'Version Selection', actual)
        self.assertTrue(matched)


if __name__ == "__main__":
    unittest.main()
