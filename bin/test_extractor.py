#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
import unittest
import logging.config
from pathlib import Path
from bs4 import BeautifulSoup
from extractor import Extractor
from feed_maker_util import Config, header_str

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()

dummy_url = "https://test.com"


class ExtractTest(unittest.TestCase):
    def setUp(self):
        self.config = Config(feed_dir_path=Path.cwd() / "test")
        if not self.config:
            LOGGER.error("can't get configuration")
            sys.exit(-1)
        self.html_content = '''
        <html>
        <body>
        <div id="content">message1</div>
        <div class="content_view">message2</div>
        <div class="content_view">message3</div>
        <div>message4</div>
        <div class="list">
        <span class="link">
        <a href="https://abc.com/test_image1.png">link</a>
        </span>        
        </div>        
        </body>
        </html>'''
        parser = "html.parser"
        self.soup = BeautifulSoup(self.html_content, parser)

    def tearDown(self):
        del self.soup

    @staticmethod
    def wrap_header(string: str) -> str:
        return header_str + "\n" + string + "\n"

    def test_extract_content(self):
        extraction_conf = self.config.get_extraction_configs()
        extractor = Extractor()
        actual = extractor.extract_content(extraction_conf, dummy_url, input_data=self.html_content)
        expected = ExtractTest.wrap_header('''<div>\nmessage2</div>\n<div>\nmessage3</div>\n<div>\nmessage1</div>''')
        self.assertEqual(actual, expected)

    def test_traverse_element(self):
        extractor = Extractor()
        element = self.soup.find_all(attrs={"id": "content"})[0]
        url = "https://abc.com/items"
        encoding = "utf-8"
        actual = extractor._traverse_element(element, url, encoding)
        expected = '''<div>\nmessage1</div>\n'''
        self.assertEqual(expected, actual)

    def test_check_element_class(self):
        extractor = Extractor()
        element = self.soup.find_all(attrs={"class": "list"})[0].contents[1]
        element_name = "span"
        class_name = "link"
        actual = extractor._check_element_class(element, element_name, class_name)
        self.assertTrue(actual)


if __name__ == "__main__":
    unittest.main()
