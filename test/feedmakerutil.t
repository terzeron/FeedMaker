#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import sys
import unittest
from bs4 import BeautifulSoup, Comment
import pprint
import xml.dom.minidom
import feedmakerutil


class X_pathTest(unittest.TestCase):
    def test_get_first_token_from_path(self):
        # id, name, idx, remainder of path, isAnywhere
        token = feedmakerutil.get_first_token_from_path("")
        self.assertEqual(token, (None, None, None, None, False))
        token = feedmakerutil.get_first_token_from_path("/html/body")
        self.assertEqual(token, (None, "body", None, "", False))
        token = feedmakerutil.get_first_token_from_path("/html/body/div")
        self.assertEqual(token, (None, "div", None, "", False))
        token = feedmakerutil.get_first_token_from_path('//*[@id="Text_Contents"]')
        self.assertEqual(token, ("Text_Contents", None, None, "", True))
        token = feedmakerutil.get_first_token_from_path('//*[@id="Text_Contents"]/form/select')
        self.assertEqual(token, ("Text_Contents", None, None, "form/select", True))
        token = feedmakerutil.get_first_token_from_path('/form/select')
        self.assertEqual(token, (None, "form", None, "select", False))
        token = feedmakerutil.get_first_token_from_path('//select')
        self.assertEqual(token, (None, "select", None, "", True))
        token = feedmakerutil.get_first_token_from_path("/html/body/div[3]")
        self.assertEqual(token, (None, "div", "3", "", False))
        token = feedmakerutil.get_first_token_from_path("/html/body/div[3]/img[2]")
        self.assertEqual(token, (None, "div", "3", "img[2]", False))
        token = feedmakerutil.get_first_token_from_path("//img[2]")
        self.assertEqual(token, (None, "img", "2", "", True))

    def test_get_node_with_path(self):
        soup = BeautifulSoup('<html><body><div>hello</div><div id="ct"><span>text</span></div></body></html>', 'html.parser')

        target_node = feedmakerutil.get_node_with_path(soup.body, '//span')
        self.assertEqual(target_node[0].name, "span")
        self.assertEqual(target_node[0].contents[0], "text")

        target_node = feedmakerutil.get_node_with_path(soup.body, '//*[@id="ct"]')
        self.assertEqual(target_node[0].name, "div")
        self.assertEqual(target_node[0].contents[0].contents[0], "text")

        target_node = feedmakerutil.get_node_with_path(soup.body, '/html/body/div')
        self.assertEqual(target_node[0].name, "div")
        self.assertEqual(target_node[0].contents[0], "hello")

        target_node = feedmakerutil.get_node_with_path(soup.body, '/div[2]')
        self.assertEqual(target_node[0].name, "div")
        self.assertEqual(target_node[0].contents[0].contents[0], "text")

        target_node = feedmakerutil.get_node_with_path(soup.body, '//*[@id="ct"]/span')
        self.assertEqual(target_node[0].name, "span")
        self.assertEqual(target_node[0].contents[0], "text")

        target_node = feedmakerutil.get_node_with_path(soup.body, '/div[2]/span')
        self.assertEqual(target_node[0].name, "span")
        self.assertEqual(target_node[0].contents[0], "text")


class IOTest(unittest.TestCase):
    def test_read_config(self):
        config = feedmakerutil.read_config()
        self.assertTrue(config != None)
        self.assertTrue(isinstance(config, xml.dom.minidom.Document))
        
    def test_get_config_node(self):
        config = feedmakerutil.read_config()
        collection = feedmakerutil.get_config_node(config, "collection")
        self.assertTrue(collection)
        list_url_list = feedmakerutil.get_config_node(collection, "list_url_list")
        self.assertTrue(list_url_list)
        list_url = feedmakerutil.get_config_node(list_url_list, "list_url")
        self.assertTrue(list_url)

    def test_get_value_from_config(self):
        config = feedmakerutil.read_config()
        collection = feedmakerutil.get_config_node(config, "collection")
        list_url_list = feedmakerutil.get_config_node(collection, "list_url_list")
        list_url = feedmakerutil.get_config_node(list_url_list, "list_url")
        v = feedmakerutil.get_value_from_config(list_url)
        self.assertEqual(v, "http://m.navercast.naver.com/homeMain.nhn?page=")
        extraction = feedmakerutil.get_config_node(config, "extraction")
        element_list = feedmakerutil.get_config_node(extraction, "element_list")
        elementId = feedmakerutil.get_config_node(element_list, "element_id")
        v = feedmakerutil.get_value_from_config(elementId)
        self.assertEqual(v, "ct")


class UtilTest(unittest.TestCase):
    def test_get_url_prefix(self):
        prefix = feedmakerutil.get_url_prefix("http://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(prefix, "http://www.naver.com/movie/hello/");

    def test_get_url_domain(self):
        domain = feedmakerutil.get_url_domain("http://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(domain, "http://www.naver.com/")

    def test_concatenate_url(self):
        url = feedmakerutil.concatenate_url("http://www.naver.com/movie", "hello")
        self.assertEqual(url, "http://www.naver.com/hello")
        url = feedmakerutil.concatenate_url("http://www.naver.com/movie/", "hello")
        self.assertEqual(url, "http://www.naver.com/movie/hello")

    def test_get_short_md5_name(self):
        self.assertEqual(feedmakerutil.get_short_md5_name("http://terzeron.net"), "e0ad299")


class ExecCmdTest(unittest.TestCase):
    def test_exec_cmd(self):
        valid_cmd = "ls feedmakerutil.t"
        (result, error) = feedmakerutil.exec_cmd(valid_cmd)
        self.assertTrue(result)
        self.assertEqual(error, "")
        self.assertTrue("feedmakerutil.t" in result)
        
        invalid_cmd = "ls non_existent_file"
        (result, error) = feedmakerutil.exec_cmd(invalid_cmd)
        self.assertFalse(result)
        self.assertTrue("ls: non_existent_file: No such file or directory" in error)

        invalid_cmd = "lslslsls non_existent_file"
        (result, error) = feedmakerutil.exec_cmd(invalid_cmd)
        self.assertFalse(result)
        self.assertTrue("/bin/sh: lslslsls: command not found" in error)


if __name__ == "__main__":
    unittest.main()
