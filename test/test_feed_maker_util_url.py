#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import logging.config
from pathlib import Path
from bin.feed_maker_util import URL

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class URLTest(unittest.TestCase):
    def test_get_url_scheme(self):
        actual = URL.get_url_scheme("http://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "http"
        self.assertEqual(expected, actual)

        actual = URL.get_url_scheme("https://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "https"
        self.assertEqual(expected, actual)

    def test_get_url_domain(self):
        actual = URL.get_url_domain("http://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "www.naver.com"
        self.assertEqual(expected, actual)

        actual = URL.get_url_domain("https://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "www.naver.com"
        self.assertEqual(expected, actual)

        actual = URL.get_url_domain("https://tkor.ws/던전-리셋")
        expected = "tkor.ws"
        self.assertEqual(expected, actual)

        actual = URL.get_url_domain("https://naver.com")
        expected = "naver.com"
        self.assertEqual(expected, actual)

    def test_get_url_path(self):
        actual = URL.get_url_path("http://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "/movie/hello/test.nhn?query=test"
        self.assertEqual(expected, actual)

        actual = URL.get_url_path("https://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "/movie/hello/test.nhn?query=test"
        self.assertEqual(expected, actual)

        actual = URL.get_url_path("https://tkor.ws/던전-리셋")
        expected = "/던전-리셋"
        self.assertEqual(expected, actual)

    def test_get_url_prefix(self):
        actual = URL.get_url_prefix("http://www.naver.com/movie")
        expected = "http://www.naver.com/"
        self.assertEqual(expected, actual)

        actual = URL.get_url_prefix("https://www.naver.com/movie")
        expected = "https://www.naver.com/"
        self.assertEqual(expected, actual)

        actual = URL.get_url_prefix("http://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "http://www.naver.com/movie/hello/"
        self.assertEqual(expected, actual)

        actual = URL.get_url_prefix("https://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "https://www.naver.com/movie/hello/"
        self.assertEqual(expected, actual)

        actual = URL.get_url_prefix("https://tkor.ws/던전-리셋")
        expected = "https://tkor.ws/"
        self.assertEqual(expected, actual)

    def test_get_url_except_query(self):
        actual = URL.get_url_except_query("http://www.naver.com/movie")
        expected = "http://www.naver.com/movie"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("https://www.naver.com/movie")
        expected = "https://www.naver.com/movie"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("http://www.naver.com/movie?page_no=3")
        expected = "http://www.naver.com/movie"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("https://www.naver.com/movie?page_no=3")
        expected = "https://www.naver.com/movie"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("http://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "http://www.naver.com/movie/hello/test.nhn"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("https://www.naver.com/movie/hello/test.nhn?query=test")
        expected = "https://www.naver.com/movie/hello/test.nhn"
        self.assertEqual(expected, actual)

        actual = URL.get_url_except_query("https://tkor.ws/던전-리셋")
        expected = "https://tkor.ws/던전-리셋"
        self.assertEqual(expected, actual)

    def test_concatenate_url(self):
        actual = URL.concatenate_url("http://www.naver.com/movie", "/sports")
        expected = "http://www.naver.com/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("http://www.naver.com/movie/", "/sports")
        expected = "http://www.naver.com/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("https://www.naver.com/movie", "/sports")
        expected = "https://www.naver.com/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("https://www.naver.com/movie/", "/sports")
        expected = "https://www.naver.com/sports"
        self.assertEqual(expected, actual)

        actual = URL.concatenate_url("http://www.naver.com/movie", "sports")
        expected = "http://www.naver.com/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("http://www.naver.com/movie/", "sports")
        expected = "http://www.naver.com/movie/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("https://www.naver.com/movie", "sports")
        expected = "https://www.naver.com/sports"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("https://www.naver.com/movie/", "sports")
        expected = "https://www.naver.com/movie/sports"
        self.assertEqual(expected, actual)

        actual = URL.concatenate_url("http://www.naver.com/movie", "#")
        expected = "http://www.naver.com/movie"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("http://www.naver.com/movie/", "#")
        expected = "http://www.naver.com/movie/"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("http://www.naver.com/view.nhn?page_no=3", "#")
        expected = "http://www.naver.com/view.nhn?page_no=3"
        self.assertEqual(expected, actual)
        actual = URL.concatenate_url("http://www.naver.com/movie/view.nhn?page_no=3", "#")
        expected = "http://www.naver.com/movie/view.nhn?page_no=3"
        self.assertEqual(expected, actual)

        actual = URL.concatenate_url("http://www.naver.com/movie/view.nhn?page_no=3", "./list.nhn?page_no=4")
        expected = "http://www.naver.com/movie/list.nhn?page_no=4"
        self.assertEqual(expected, actual)

    def test_get_short_md5_name(self):
        self.assertEqual(URL.get_short_md5_name("https://terzeron.com"), "b8025d0")

    def test_encode(self):
        self.assertEqual(URL.encode('http://5rs-wc22.com/식극의-소마/post/134225?a=테스트b'), 'http://5rs-wc22.com/%EC%8B%9D%EA%B7%B9%EC%9D%98-%EC%86%8C%EB%A7%88/post/134225?a=%ED%85%8C%EC%8A%A4%ED%8A%B8b')


if __name__ == "__main__":
    unittest.main()
