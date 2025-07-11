#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import logging.config
from pathlib import Path
from bs4 import BeautifulSoup
from bs4.element import Tag, PageElement, NavigableString
from typing import Any

from bin.feed_maker_util import HTMLExtractor

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class HTMLExtractorTest(unittest.TestCase):
    def test_get_first_token_from_path(self) -> None:
        # id, name, idx, remainder of path, isAnywhere
        actual = HTMLExtractor.get_first_token_from_path("")
        self.assertEqual((None, None, None, None, False), actual)

        actual = HTMLExtractor.get_first_token_from_path("/html/body")
        self.assertEqual((None, "body", None, "", False), actual)

        actual = HTMLExtractor.get_first_token_from_path("/html/body/div")
        self.assertEqual((None, "div", None, "", False), actual)

        actual = HTMLExtractor.get_first_token_from_path('//*[@id="Text_Contents"]')
        self.assertEqual(("Text_Contents", None, None, "", True), actual)

        actual = HTMLExtractor.get_first_token_from_path('//*[@id="Text_Contents"]/form/select')
        self.assertEqual(("Text_Contents", None, None, "form/select", True), actual)

        actual = HTMLExtractor.get_first_token_from_path('/form/select')
        self.assertEqual((None, "form", None, "select", False), actual)

        actual = HTMLExtractor.get_first_token_from_path('//select')
        self.assertEqual((None, "select", None, "", True), actual)

        actual = HTMLExtractor.get_first_token_from_path("/html/body/div[3]")
        self.assertEqual((None, "div", 3, "", False), actual)

        actual = HTMLExtractor.get_first_token_from_path("/html/body/div[3]/img[2]")
        self.assertEqual((None, "div", 3, "img[2]", False), actual)

        actual = HTMLExtractor.get_first_token_from_path("//img[2]")
        self.assertEqual((None, "img", 2, "", True), actual)

    def test_get_node_with_path(self) -> None:
        soup = BeautifulSoup('<html><body><div>hello</div><div id="ct"><span>text</span></div></body></html>', 'html.parser')
        assert soup.body is not None
        body = soup.body

        target_node = HTMLExtractor.get_node_with_path(body, '//span')
        if target_node:
            actual = target_node[0].name
            expected = "span"
            self.assertEqual(expected, actual)

            content: Any = target_node[0].contents[0]
            actual = str(content.string)
            expected = "text"
            self.assertEqual(expected, actual)
        else:
            self.fail()

        target_node = HTMLExtractor.get_node_with_path(body, '//*[@id="ct"]')
        if target_node:
            actual = target_node[0].name
            expected = "div"
            self.assertEqual(expected, actual)

            parent: Any = target_node[0].contents[0]  
            content2: Any = parent.contents[0]  
            actual = str(content2.string)
            expected = "text"
            self.assertEqual(expected, actual)
        else:
            self.fail()

        target_node = HTMLExtractor.get_node_with_path(body, '/html/body/div')
        if target_node:
            actual = target_node[0].name
            expected = "div"
            self.assertEqual(expected, actual)

            content3: Any = target_node[0].contents[0]  
            actual = str(content3.string)
            expected = "hello"
            self.assertEqual(expected, actual)
        else:
            self.fail()

        target_node = HTMLExtractor.get_node_with_path(body, '/div[2]')
        if target_node:
            actual = target_node[0].name
            expected = "div"
            self.assertEqual(expected, actual)

            parent2: Any = target_node[0].contents[0]  
            content4: Any = parent2.contents[0]  
            actual = str(content4.string)
            expected = "text"
            self.assertEqual(expected, actual)
        else:
            self.fail()

        target_node = HTMLExtractor.get_node_with_path(body, '//*[@id="ct"]/span')
        if target_node:
            actual = target_node[0].name
            expected = "span"
            self.assertEqual(expected, actual)
            content5: Any = target_node[0].contents[0]  
            actual = str(content5.string)
            expected = "text"
            self.assertEqual(expected, actual)
        else:
            self.fail()

        target_node = HTMLExtractor.get_node_with_path(body, '/div[2]/span')
        if target_node:
            actual = target_node[0].name
            expected = "span"
            self.assertEqual(expected, actual)

            content6: Any = target_node[0].contents[0]  
            actual = str(content6.string)
            expected = "text"
            self.assertEqual(expected, actual)
        else:
            self.fail()


if __name__ == "__main__":
    unittest.main()  
