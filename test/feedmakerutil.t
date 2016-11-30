#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import sys
import unittest
from bs4 import BeautifulSoup, Comment
import pprint
import xml.dom.minidom
import feedmakerutil


class XPathTest(unittest.TestCase):
    def test_getFirstTokenFromPath(self):
        # id, name, idx, remainder of path, isAnywhere
        token = feedmakerutil.getFirstTokenFromPath("")
        self.assertEqual(token, (None, None, None, None, False))
        token = feedmakerutil.getFirstTokenFromPath("/html/body")
        self.assertEqual(token, (None, "body", None, "", False))
        token = feedmakerutil.getFirstTokenFromPath("/html/body/div")
        self.assertEqual(token, (None, "div", None, "", False))
        token = feedmakerutil.getFirstTokenFromPath('//*[@id="Text_Contents"]')
        self.assertEqual(token, ("Text_Contents", None, None, "", True))
        token = feedmakerutil.getFirstTokenFromPath('//*[@id="Text_Contents"]/form/select')
        self.assertEqual(token, ("Text_Contents", None, None, "form/select", True))
        token = feedmakerutil.getFirstTokenFromPath('/form/select')
        self.assertEqual(token, (None, "form", None, "select", False))
        token = feedmakerutil.getFirstTokenFromPath('//select')
        self.assertEqual(token, (None, "select", None, "", True))
        token = feedmakerutil.getFirstTokenFromPath("/html/body/div[3]")
        self.assertEqual(token, (None, "div", "3", "", False))
        token = feedmakerutil.getFirstTokenFromPath("/html/body/div[3]/img[2]")
        self.assertEqual(token, (None, "div", "3", "img[2]", False))
        token = feedmakerutil.getFirstTokenFromPath("//img[2]")
        self.assertEqual(token, (None, "img", "2", "", True))

    def test_getNodeWithPath(self):
        soup = BeautifulSoup('<html><body><div>hello</div><div id="ct"><span>text</span></div></body></html>', 'html.parser')

        targetNode = feedmakerutil.getNodeWithPath(soup.body, '//span')
        self.assertEqual(targetNode[0].name, "span")
        self.assertEqual(targetNode[0].contents[0], "text")

        targetNode = feedmakerutil.getNodeWithPath(soup.body, '//*[@id="ct"]')
        self.assertEqual(targetNode[0].name, "div")
        self.assertEqual(targetNode[0].contents[0].contents[0], "text")

        targetNode = feedmakerutil.getNodeWithPath(soup.body, '/html/body/div')
        self.assertEqual(targetNode[0].name, "div")
        self.assertEqual(targetNode[0].contents[0], "hello")

        targetNode = feedmakerutil.getNodeWithPath(soup.body, '/div[2]')
        self.assertEqual(targetNode[0].name, "div")
        self.assertEqual(targetNode[0].contents[0].contents[0], "text")

        targetNode = feedmakerutil.getNodeWithPath(soup.body, '//*[@id="ct"]/span')
        self.assertEqual(targetNode[0].name, "span")
        self.assertEqual(targetNode[0].contents[0], "text")

        targetNode = feedmakerutil.getNodeWithPath(soup.body, '/div[2]/span')
        self.assertEqual(targetNode[0].name, "span")
        self.assertEqual(targetNode[0].contents[0], "text")


class IOTest(unittest.TestCase):
    def test_readConfig(self):
        config = feedmakerutil.readConfig()
        self.assertTrue(config != None)
        self.assertTrue(isinstance(config, xml.dom.minidom.Document))
        
    def test_getConfigNode(self):
        config = feedmakerutil.readConfig()
        collection = feedmakerutil.getConfigNode(config, "collection")
        self.assertTrue(collection)
        listUrlList = feedmakerutil.getConfigNode(collection, "list_url_list")
        self.assertTrue(listUrlList)
        listUrl = feedmakerutil.getConfigNode(listUrlList, "list_url")
        self.assertTrue(listUrl)

    def test_getValueFromConfig(self):
        config = feedmakerutil.readConfig()
        collection = feedmakerutil.getConfigNode(config, "collection")
        listUrlList = feedmakerutil.getConfigNode(collection, "list_url_list")
        listUrl = feedmakerutil.getConfigNode(listUrlList, "list_url")
        v = feedmakerutil.getValueFromConfig(listUrl)
        self.assertEqual(v, "http://m.navercast.naver.com/homeMain.nhn?page=")
        extraction = feedmakerutil.getConfigNode(config, "extraction")
        elementList = feedmakerutil.getConfigNode(extraction, "element_list")
        elementId = feedmakerutil.getConfigNode(elementList, "element_id")
        v = feedmakerutil.getValueFromConfig(elementId)
        self.assertEqual(v, "ct")


class UtilTest(unittest.TestCase):
    def test_getUrlPrefix(self):
        prefix = feedmakerutil.getUrlPrefix("http://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(prefix, "http://www.naver.com/movie/hello/");

    def test_getUrlDomain(self):
        domain = feedmakerutil.getUrlDomain("http://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(domain, "http://www.naver.com/")

    def test_concatenateUrl(self):
        url = feedmakerutil.concatenateUrl("http://www.naver.com/movie", "hello")
        self.assertEqual(url, "http://www.naver.com/hello")
        url = feedmakerutil.concatenateUrl("http://www.naver.com/movie/", "hello")
        self.assertEqual(url, "http://www.naver.com/movie/hello")

    def test_getShortMd5Name(self):
        self.assertEqual(feedmakerutil.getShortMd5Name("http://terzeron.net"), "e0ad299")


if __name__ == "__main__":
    unittest.main()
