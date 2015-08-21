#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
from bs4 import BeautifulSoup, Comment
import pprint
import xml.dom.minidom
from feedmakerutil import get_first_token_from_path, read_config, get_url_prefix, get_url_domain, concatenate_url, get_config_node, get_value_from_config, get_node_with_path


class XPathTest(unittest.TestCase):
	def test_get_first_token_from_path(self):
		# id, name, idx, remainder of path, is_anywhere
		token = get_first_token_from_path("")
		self.assertEqual(token, (None, None, None, None, False))
		token = get_first_token_from_path("/html/body")
		self.assertEqual(token, (None, "body", None, "", False))
		token = get_first_token_from_path("/html/body/div")
		self.assertEqual(token, (None, "div", None, "", False))
		token = get_first_token_from_path('//*[@id="Text_Contents"]')
		self.assertEqual(token, ("Text_Contents", None, None, "", True))
		token = get_first_token_from_path('//*[@id="Text_Contents"]/form/select')
		self.assertEqual(token, ("Text_Contents", None, None, "form/select", True))
		token = get_first_token_from_path('/form/select')
		self.assertEqual(token, (None, "form", None, "select", False))
		token = get_first_token_from_path('//select')
		self.assertEqual(token, (None, "select", None, "", True))
		token = get_first_token_from_path("/html/body/div[3]")
		self.assertEqual(token, (None, "div", "3", "", False))
		token = get_first_token_from_path("/html/body/div[3]/img[2]")
		self.assertEqual(token, (None, "div", "3", "img[2]", False))
		token = get_first_token_from_path("//img[2]")
		self.assertEqual(token, (None, "img", "2", "", True))

	def test_get_node_with_path(self):
		soup = BeautifulSoup('<html><body><div>hello</div><div id="ct"><span>text</span></div></body></html>', 'html5lib', from_encoding="utf-8")

		target_node = get_node_with_path(soup.body, '//span')
		self.assertEqual(target_node[0].name, "span")
		self.assertEqual(target_node[0].contents[0], "text")

		target_node = get_node_with_path(soup.body, '//*[@id="ct"]')
		self.assertEqual(target_node[0].name, "div")
		self.assertEqual(target_node[0].contents[0].contents[0], "text")

		target_node = get_node_with_path(soup.body, '/html/body/div')
		self.assertEqual(target_node[0].name, "div")
		self.assertEqual(target_node[0].contents[0], "hello")

		target_node = get_node_with_path(soup.body, '/div[2]')
		self.assertEqual(target_node[0].name, "div")
		self.assertEqual(target_node[0].contents[0].contents[0], "text")

		target_node = get_node_with_path(soup.body, '//*[@id="ct"]/span')
		self.assertEqual(target_node[0].name, "span")
		self.assertEqual(target_node[0].contents[0], "text")

		target_node = get_node_with_path(soup.body, '/div[2]/span')
		self.assertEqual(target_node[0].name, "span")
		self.assertEqual(target_node[0].contents[0], "text")


class IOTest(unittest.TestCase):
	def test_read_config(self):
		config = read_config()
		self.assertTrue(config != None)
		self.assertTrue(isinstance(config, xml.dom.minidom.Document))
		
	def test_get_config_node(self):
		config = read_config()
		collection = get_config_node(config, "collection")
		self.assertTrue(collection)
		list_url_list = get_config_node(collection, "list_url_list")
		self.assertTrue(list_url_list)
		list_url = get_config_node(list_url_list, "list_url")
		self.assertTrue(list_url)

	def test_get_value_from_config(self):
		config = read_config()
		collection = get_config_node(config, "collection")
		list_url_list = get_config_node(collection, "list_url_list")
		list_url = get_config_node(list_url_list, "list_url")
		v = get_value_from_config(list_url)
		self.assertEquals(v, "http://m.navercast.naver.com/homeMain.nhn?page=")
		extraction = get_config_node(config, "extraction")
		element_list = get_config_node(extraction, "element_list")
		element_id = get_config_node(element_list, "element_id")
		v = get_value_from_config(element_id)
		self.assertEquals(v, "ct")


class UtilTest(unittest.TestCase):
	def test_get_url_prefix(self):
		prefix = get_url_prefix("http://www.naver.com/movie/hello/test.nhn?query=test")
		self.assertEquals(prefix, "http://www.naver.com/movie/hello/");

	def test_get_url_domain(self):
		domain = get_url_domain("http://www.naver.com/movie/hello/test.nhn?query=test")
		self.assertEquals(domain, "http://www.naver.com/")

	def test_concatenate_url(self):
		url = concatenate_url("http://www.naver.com/movie", "hello")
		self.assertEquals(url, "http://www.naver.com/hello")
		url = concatenate_url("http://www.naver.com/movie/", "hello")
		self.assertEquals(url, "http://www.naver.com/movie/hello")


if __name__ == "__main__":
	unittest.main()
