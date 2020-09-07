#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from bs4 import BeautifulSoup
import feed_maker_util
from feed_maker_util import Config, URL, HTMLExtractor


class HTMLExtractorTest(unittest.TestCase):
    def test_get_first_token_from_path(self):
        # id, name, idx, remainder of path, isAnywhere
        token = HTMLExtractor.get_first_token_from_path("")
        self.assertEqual(token, (None, None, None, None, False))
        token = HTMLExtractor.get_first_token_from_path("/html/body")
        self.assertEqual(token, (None, "body", None, "", False))
        token = HTMLExtractor.get_first_token_from_path("/html/body/div")
        self.assertEqual(token, (None, "div", None, "", False))
        token = HTMLExtractor.get_first_token_from_path('//*[@id="Text_Contents"]')
        self.assertEqual(token, ("Text_Contents", None, None, "", True))
        token = HTMLExtractor.get_first_token_from_path('//*[@id="Text_Contents"]/form/select')
        self.assertEqual(token, ("Text_Contents", None, None, "form/select", True))
        token = HTMLExtractor.get_first_token_from_path('/form/select')
        self.assertEqual(token, (None, "form", None, "select", False))
        token = HTMLExtractor.get_first_token_from_path('//select')
        self.assertEqual(token, (None, "select", None, "", True))
        token = HTMLExtractor.get_first_token_from_path("/html/body/div[3]")
        self.assertEqual(token, (None, "div", 3, "", False))
        token = HTMLExtractor.get_first_token_from_path("/html/body/div[3]/img[2]")
        self.assertEqual(token, (None, "div", 3, "img[2]", False))
        token = HTMLExtractor.get_first_token_from_path("//img[2]")
        self.assertEqual(token, (None, "img", 2, "", True))

    def test_get_node_with_path(self):
        soup = BeautifulSoup('<html><body><div>hello</div><div id="ct"><span>text</span></div></body></html>', 'html.parser')

        target_node = HTMLExtractor.get_node_with_path(soup.body, '//span')
        self.assertEqual(target_node[0].name, "span")
        self.assertEqual(target_node[0].contents[0], "text")

        target_node = HTMLExtractor.get_node_with_path(soup.body, '//*[@id="ct"]')
        self.assertEqual(target_node[0].name, "div")
        self.assertEqual(target_node[0].contents[0].contents[0], "text")

        target_node = HTMLExtractor.get_node_with_path(soup.body, '/html/body/div')
        self.assertEqual(target_node[0].name, "div")
        self.assertEqual(target_node[0].contents[0], "hello")

        target_node = HTMLExtractor.get_node_with_path(soup.body, '/div[2]')
        self.assertEqual(target_node[0].name, "div")
        self.assertEqual(target_node[0].contents[0].contents[0], "text")

        target_node = HTMLExtractor.get_node_with_path(soup.body, '//*[@id="ct"]/span')
        self.assertEqual(target_node[0].name, "span")
        self.assertEqual(target_node[0].contents[0], "text")

        target_node = HTMLExtractor.get_node_with_path(soup.body, '/div[2]/span')
        self.assertEqual(target_node[0].name, "span")
        self.assertEqual(target_node[0].contents[0], "text")


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = Config()

    def tearDown(self):
        self.config = None
        
    def test_init(self):
        self.assertNotEqual(self.config, None)
        self.assertTrue(isinstance(self.config, feed_maker_util.Config))
        
    def test_get_collection_configs(self):
        configs = self.config.get_collection_configs()
        self.assertTrue(isinstance(configs, dict))
        self.assertEqual(configs["item_capture_script"], "./capture_item_link_title.py")
        self.assertFalse(configs["ignore_old_list"])
        self.assertEqual(configs["sort_field_pattern"], None)
        self.assertEqual(configs["unit_size_per_day"], None)
        self.assertEqual(configs["list_url_list"], ["http://m.navercast.naver.com/homeMain.nhn?page=1", "http://m.navercast.naver.com/homeMain.nhn?page=2"])
        self.assertEqual(configs["post_process_script_list"], [])
    
    def test_get_extraction_configs(self):
        configs = self.config.get_extraction_configs()
        self.assertTrue(isinstance(configs, dict))
        self.assertFalse(configs["render_js"])
        self.assertEqual(configs["review_point_threshold"], None)
        self.assertNotEqual(configs["user_agent"], None)
        self.assertEqual(configs["element_id_list"], ["ct", "content"])
        self.assertEqual(configs["element_class_list"], ["se_doc_viewer", "content_view"])
        self.assertEqual(configs["element_path_list"], [])
        self.assertEqual(configs["post_process_script_list"], ["post_process_script_for_navercast.py"])
        self.assertEqual(configs["header_list"], [])

    def test_get_notification_configs(self):
        configs = self.config.get_notification_configs()
        self.assertTrue(isinstance(configs, dict))
        self.assertEqual(configs["email_recipient"], "terzeron@gmail.com")
        self.assertEqual(configs["email_subject"], "Success in navercast")

    def test_get_rss_configs(self):
        configs = self.config.get_rss_configs()
        self.assertTrue(isinstance(configs, dict))
        self.assertEqual(configs["rss_title"], "네이버캐스트 모바일")


class UtilTest(unittest.TestCase):
    def test_get_url_scheme(self):
        scheme = URL.get_url_scheme("http://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(scheme, "http")
        scheme = URL.get_url_scheme("https://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(scheme, "https")

    def test_get_url_domain(self):
        domain = URL.get_url_domain("http://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(domain, "www.naver.com")
        domain = URL.get_url_domain("https://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(domain, "www.naver.com")

    def test_get_url_path(self):
        path = URL.get_url_path("http://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(path, "/movie/hello/test.nhn?query=test")
        path = URL.get_url_path("https://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(path, "/movie/hello/test.nhn?query=test")

    def test_get_url_prefix(self):
        prefix = URL.get_url_prefix("http://www.naver.com/movie")
        self.assertEqual(prefix, "http://www.naver.com/")
        prefix = URL.get_url_prefix("https://www.naver.com/movie")
        self.assertEqual(prefix, "https://www.naver.com/")
        prefix = URL.get_url_prefix("http://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(prefix, "http://www.naver.com/movie/hello/")
        prefix = URL.get_url_prefix("https://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(prefix, "https://www.naver.com/movie/hello/")

    def test_get_url_except_query(self):
        result = URL.get_url_except_query("http://www.naver.com/movie")
        self.assertEqual(result, "http://www.naver.com/movie")
        result = URL.get_url_except_query("https://www.naver.com/movie")
        self.assertEqual(result, "https://www.naver.com/movie")
        result = URL.get_url_except_query("http://www.naver.com/movie?page_no=3")
        self.assertEqual(result, "http://www.naver.com/movie")
        result = URL.get_url_except_query("https://www.naver.com/movie?page_no=3")
        self.assertEqual(result, "https://www.naver.com/movie")
        result = URL.get_url_except_query("http://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(result, "http://www.naver.com/movie/hello/test.nhn")
        result = URL.get_url_except_query("https://www.naver.com/movie/hello/test.nhn?query=test")
        self.assertEqual(result, "https://www.naver.com/movie/hello/test.nhn")

    def test_concatenate_url(self):
        url = URL.concatenate_url("http://www.naver.com/movie", "/sports")
        self.assertEqual(url, "http://www.naver.com/sports")
        url = URL.concatenate_url("http://www.naver.com/movie/", "/sports")
        self.assertEqual(url, "http://www.naver.com/sports")
        url = URL.concatenate_url("https://www.naver.com/movie", "/sports")
        self.assertEqual(url, "https://www.naver.com/sports")
        url = URL.concatenate_url("https://www.naver.com/movie/", "/sports")
        self.assertEqual(url, "https://www.naver.com/sports")

        url = URL.concatenate_url("http://www.naver.com/movie", "sports")
        self.assertEqual(url, "http://www.naver.com/movie/sports")
        url = URL.concatenate_url("http://www.naver.com/movie/", "sports")
        self.assertEqual(url, "http://www.naver.com/movie/sports")
        url = URL.concatenate_url("https://www.naver.com/movie", "sports")
        self.assertEqual(url, "https://www.naver.com/movie/sports")
        url = URL.concatenate_url("https://www.naver.com/movie/", "sports")
        self.assertEqual(url, "https://www.naver.com/movie/sports")

        url = URL.concatenate_url("http://www.naver.com/movie", "#")
        self.assertEqual(url, "http://www.naver.com/movie")
        url = URL.concatenate_url("http://www.naver.com/movie/", "#")
        self.assertEqual(url, "http://www.naver.com/movie/")
        url = URL.concatenate_url("http://www.naver.com/view.nhn?page_no=3", "#")
        self.assertEqual(url, "http://www.naver.com/view.nhn?page_no=3")
        url = URL.concatenate_url("http://www.naver.com/movie/view.nhn?page_no=3", "#")
        self.assertEqual(url, "http://www.naver.com/movie/view.nhn?page_no=3")
        url = URL.concatenate_url("http://www.naver.com/movie/view.nhn?page_no=3", "./list.nhn?page_no=4")
        self.assertEqual(url, "http://www.naver.com/movie/list.nhn?page_no=4")

    def test_get_short_md5_name(self):
        self.assertEqual(URL.get_short_md5_name("https://terzeron.com"), "b8025d0")

    def test_encode(self):
        self.assertEqual(URL.encode('http://5rs-wc22.com/식극의-소마/post/134225?a=테스트b'), 'http://5rs-wc22.com/%EC%8B%9D%EA%B7%B9%EC%9D%98-%EC%86%8C%EB%A7%88/post/134225?a=%ED%85%8C%EC%8A%A4%ED%8A%B8b')


class ExecCmdTest(unittest.TestCase):
    def test_exec_cmd(self):
        valid_cmd = "ls feed_maker_util.t"
        (result, error) = feed_maker_util.exec_cmd(valid_cmd)
        self.assertTrue(result)
        self.assertEqual(error, "")
        self.assertTrue("feed_maker_util.t" in result)
        
        invalid_cmd = "ls non_existent_file"
        (result, error) = feed_maker_util.exec_cmd(invalid_cmd)
        self.assertFalse(result)
        self.assertTrue("Error with non-zero exit status in command" in error)

        invalid_cmd = "lslslsls non_existent_file"
        (result, error) = feed_maker_util.exec_cmd(invalid_cmd)
        self.assertFalse(result)
        self.assertTrue("Error with non-zero exit status in command" in error)

        bidirectional_cmd = "cat"
        input_str = "hello world"
        (result, error) = feed_maker_util.exec_cmd(bidirectional_cmd, input_str)
        self.assertTrue(result)
        self.assertEqual(error, "")
        self.assertTrue("hello world" in result)


if __name__ == "__main__":
    unittest.main()
