#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import unittest
import logging.config
from pathlib import Path
from unittest.mock import patch, MagicMock

from bin.feed_maker_util import NotFoundConfigItemError

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestReadConfig(unittest.TestCase):
    def test_valid_config(self) -> None:
        from utils.check_manga_site import read_config

        config_data = {"url": "https://example.com", "keyword": "manga"}
        tmp_path = Path("/tmp/test_site_config_valid.json")
        tmp_path.write_text(json.dumps(config_data), encoding="utf-8")
        try:
            result = read_config(tmp_path)
            self.assertEqual(result["url"], "https://example.com")
            self.assertEqual(result["keyword"], "manga")
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_missing_url(self) -> None:
        from utils.check_manga_site import read_config

        config_data = {"keyword": "manga"}
        tmp_path = Path("/tmp/test_site_config_no_url.json")
        tmp_path.write_text(json.dumps(config_data), encoding="utf-8")
        try:
            with self.assertRaises(NotFoundConfigItemError):
                read_config(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_missing_keyword(self) -> None:
        from utils.check_manga_site import read_config

        config_data = {"url": "https://example.com"}
        tmp_path = Path("/tmp/test_site_config_no_kw.json")
        tmp_path.write_text(json.dumps(config_data), encoding="utf-8")
        try:
            with self.assertRaises(NotFoundConfigItemError):
                read_config(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_empty_file(self) -> None:
        from utils.check_manga_site import read_config

        tmp_path = Path("/tmp/test_site_config_empty.json")
        tmp_path.write_text("", encoding="utf-8")
        try:
            with self.assertRaises(json.JSONDecodeError):
                read_config(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)


class TestCleanUrl(unittest.TestCase):
    def test_protocol_relative_url(self) -> None:
        from utils.check_manga_site import clean_url

        result = clean_url("//example.com/page", scheme="https", path="/extra")
        self.assertEqual(result, "https://example.com/page/extra")

    def test_normal_url_unchanged(self) -> None:
        from utils.check_manga_site import clean_url

        result = clean_url("https://example.com/page")
        self.assertEqual(result, "https://example.com/page")


class TestGetUrlPattern(unittest.TestCase):
    def test_matching_url(self) -> None:
        from utils.check_manga_site import get_url_pattern

        url = "https://manga123.example.com/path/to/page"
        new_pattern, pre, num, domain_postfix, post = get_url_pattern(url)
        self.assertNotEqual(new_pattern, "")
        self.assertEqual(num, 123)
        self.assertIn(r"(\d+)", new_pattern)

    def test_non_matching_url(self) -> None:
        from utils.check_manga_site import get_url_pattern

        url = "https://example.com/"
        new_pattern, pre, num, domain_postfix, post = get_url_pattern(url)
        self.assertEqual(new_pattern, "")
        self.assertEqual(num, 0)


class TestGetNewUrl(unittest.TestCase):
    def test_matching_patterns_found(self) -> None:
        from utils.check_manga_site import get_new_url

        url = "https://manga123.example.com/path"
        response = 'href="https://manga124.example.com/path" href="https://manga125.example.com/path" href="https://manga125.example.com/path"'
        new_pattern = r"https://manga(\d+)\.example\.com(?:/path)?"
        new_url, new_number = get_new_url(url=url, response=response, new_pattern=new_pattern, pre="https://manga", num=123, domain_postfix=".example.com", post="/path")
        self.assertNotEqual(new_url, "")
        self.assertGreater(new_number, 123)

    def test_no_matches(self) -> None:
        from utils.check_manga_site import get_new_url

        new_url, new_number = get_new_url(url="https://manga123.example.com/path", response="no matching urls here", new_pattern=r"https://manga(\d+)\.example\.com(?:/path)?", pre="https://manga", num=123, domain_postfix=".example.com", post="/path")
        self.assertEqual(new_url, "")
        self.assertEqual(new_number, 0)

    def test_empty_matches(self) -> None:
        from utils.check_manga_site import get_new_url

        # All matches are <= num, so url_count_map stays empty
        response = "https://manga100.example.com/path https://manga50.example.com/path"
        new_url, new_number = get_new_url(url="https://manga123.example.com/path", response=response, new_pattern=r"https://manga(\d+)\.example\.com(?:/path)?", pre="https://manga", num=123, domain_postfix=".example.com", post="/path")
        self.assertEqual(new_url, "")
        self.assertEqual(new_number, 0)


class TestGet(unittest.TestCase):
    @patch("utils.check_manga_site.get_location_recursively")
    def test_success_keyword_found(self, mock_get_loc: MagicMock) -> None:
        from utils.check_manga_site import get

        url = "https://example.com/page"
        response_body = "some content with manga keyword and example.com domain"
        mock_get_loc.return_value = (url, response_body)
        config = {"keyword": "manga"}
        success, response, new_url = get(url, config)
        self.assertTrue(success)
        self.assertEqual(response, response_body)

    @patch("utils.check_manga_site.get_location_recursively")
    def test_no_response(self, mock_get_loc: MagicMock) -> None:
        from utils.check_manga_site import get

        url = "https://example.com/page"
        mock_get_loc.return_value = ("", "")
        config = {"keyword": "manga"}
        success, response, new_url = get(url, config)
        self.assertFalse(success)
        self.assertEqual(response, "")

    @patch("utils.check_manga_site.get_location_recursively")
    def test_keyword_not_found(self, mock_get_loc: MagicMock) -> None:
        from utils.check_manga_site import get

        url = "https://example.com/page"
        mock_get_loc.return_value = (url, "some content without the expected word and example.com")
        config = {"keyword": "manga"}
        success, response, new_url = get(url, config)
        self.assertFalse(success)
        self.assertNotEqual(response, "")
        self.assertEqual(new_url, "")

    @patch("utils.check_manga_site.get_location_recursively")
    def test_domain_not_found(self, mock_get_loc: MagicMock) -> None:
        from utils.check_manga_site import get

        url = "https://example.com/page"
        new_redirected_url = "https://newsite.com/page"
        mock_get_loc.return_value = (new_redirected_url, "content with manga keyword but different domain")
        config = {"keyword": "manga"}
        success, response, new_url = get(url, config)
        self.assertFalse(success)
        self.assertEqual(new_url, new_redirected_url)


class TestGetLocationRecursively(unittest.TestCase):
    @patch("utils.check_manga_site.Crawler")
    def test_direct_response(self, mock_crawler_cls: MagicMock) -> None:
        from utils.check_manga_site import get_location_recursively

        mock_instance = MagicMock()
        mock_instance.run.return_value = ("page content", "", {})
        mock_crawler_cls.return_value = mock_instance
        url = "https://example.com/page"
        config = {}
        result_url, response = get_location_recursively(url, config)
        self.assertEqual(result_url, url)
        self.assertEqual(response, "page content")

    @patch("utils.check_manga_site.Crawler")
    def test_redirect(self, mock_crawler_cls: MagicMock) -> None:
        from utils.check_manga_site import get_location_recursively

        mock_instance = MagicMock()
        # First call: redirect with empty body
        # Second call: actual content
        mock_instance.run.side_effect = [("", "", {"Location": "https://newsite.com/page"}), ("final content", "", {})]
        mock_crawler_cls.return_value = mock_instance
        url = "https://example.com/page"
        config = {}
        result_url, response = get_location_recursively(url, config)
        self.assertEqual(response, "final content")

    @patch("utils.check_manga_site.Crawler")
    def test_timeout(self, mock_crawler_cls: MagicMock) -> None:
        from utils.check_manga_site import get_location_recursively
        from bin.crawler import Crawler

        # Preserve the real exception class so the except clause can catch it
        mock_crawler_cls.ReadTimeoutException = Crawler.ReadTimeoutException
        mock_instance = MagicMock()
        mock_instance.run.side_effect = Crawler.ReadTimeoutException()
        mock_crawler_cls.return_value = mock_instance
        url = "https://example.com/page"
        config = {}
        result_url, response = get_location_recursively(url, config)
        self.assertEqual(result_url, "")
        self.assertEqual(response, "")


if __name__ == "__main__":
    unittest.main()
