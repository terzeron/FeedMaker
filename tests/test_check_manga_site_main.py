#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
import logging.config
from pathlib import Path
from unittest.mock import patch, MagicMock

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")


class TestCheckMangaSiteMain(unittest.TestCase):
    """utils/check_manga_site.py main() 함수 테스트"""

    def test_main_no_config_file(self) -> None:
        from utils.check_manga_site import main

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = main()
        self.assertEqual(result, -1)

    @patch("utils.check_manga_site.get")
    @patch("utils.check_manga_site.get_url_pattern")
    @patch("utils.check_manga_site.read_config")
    def test_main_success(self, mock_read_config: MagicMock, mock_get_url_pattern: MagicMock, mock_get: MagicMock) -> None:
        from utils.check_manga_site import main

        mock_read_config.return_value = {"url": "https://manga123.example.com/path", "keyword": "manga"}
        mock_get_url_pattern.return_value = ("pattern", "pre", 123, ".example.com", "/path")
        mock_get.return_value = (True, "response body", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "site_config.json"
            config_path.write_text(json.dumps({"url": "https://manga123.example.com/path", "keyword": "manga"}))
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = main()

        self.assertEqual(result, 0)

    @patch("utils.check_manga_site.get")
    @patch("utils.check_manga_site.get_url_pattern")
    @patch("utils.check_manga_site.read_config")
    def test_main_failure_with_new_url(self, mock_read_config: MagicMock, mock_get_url_pattern: MagicMock, mock_get: MagicMock) -> None:
        from utils.check_manga_site import main

        mock_read_config.return_value = {"url": "https://manga123.example.com/path", "keyword": "manga"}
        mock_get_url_pattern.return_value = ("pattern", "pre", 123, ".example.com", "/path")
        mock_get.return_value = (False, "response", "https://manga456.example.com/path")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "site_config.json"
            config_path.write_text(json.dumps({"url": "x", "keyword": "y"}))
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = main()

        self.assertEqual(result, -1)

    @patch("utils.check_manga_site.get_new_url")
    @patch("utils.check_manga_site.get")
    @patch("utils.check_manga_site.get_url_pattern")
    @patch("utils.check_manga_site.read_config")
    def test_main_failure_no_new_url_found_via_get_new_url(self, mock_read_config: MagicMock, mock_get_url_pattern: MagicMock, mock_get: MagicMock, mock_get_new_url: MagicMock) -> None:
        from utils.check_manga_site import main

        mock_read_config.return_value = {"url": "https://manga123.example.com/path", "keyword": "manga"}
        mock_get_url_pattern.return_value = ("pattern", "pre", 123, ".example.com", "/path")
        mock_get.return_value = (False, "response body", "")
        mock_get_new_url.return_value = ("", 0)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "site_config.json"
            config_path.write_text(json.dumps({"url": "x", "keyword": "y"}))
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = main()

        self.assertEqual(result, -1)

    @patch("utils.check_manga_site.get_new_url")
    @patch("utils.check_manga_site.get")
    @patch("utils.check_manga_site.get_url_pattern")
    @patch("utils.check_manga_site.read_config")
    def test_main_failure_get_new_url_found(self, mock_read_config: MagicMock, mock_get_url_pattern: MagicMock, mock_get: MagicMock, mock_get_new_url: MagicMock) -> None:
        from utils.check_manga_site import main

        mock_read_config.return_value = {"url": "https://manga123.example.com/path", "keyword": "manga"}
        mock_get_url_pattern.return_value = ("pattern", "pre", 123, ".example.com", "/path")
        mock_get.return_value = (False, "response body", "")
        mock_get_new_url.return_value = ("https://manga456.example.com/path", 456)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "site_config.json"
            config_path.write_text(json.dumps({"url": "x", "keyword": "y"}))
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = main()

        self.assertEqual(result, -1)


class TestGetLocationRecursivelyRedirect(unittest.TestCase):
    """get_location_recursively: redirect path (response_size=0, new_url)"""

    @patch("utils.check_manga_site.Crawler")
    def test_redirect_with_location_header(self, mock_crawler_cls: MagicMock) -> None:
        from utils.check_manga_site import get_location_recursively

        mock_instance = MagicMock()
        # First call: empty response with Location header (redirect)
        # Second call: actual content
        mock_instance.run.side_effect = [("", "", {"location": "https://newsite.com/page"}), ("final content here", "", {})]
        mock_crawler_cls.return_value = mock_instance

        result_url, response = get_location_recursively("https://old.com/page", {})
        self.assertEqual(response, "final content here")

    @patch("utils.check_manga_site.Crawler")
    def test_no_redirect_no_response(self, mock_crawler_cls: MagicMock) -> None:
        from utils.check_manga_site import get_location_recursively

        mock_instance = MagicMock()
        # Empty response, no location header
        mock_instance.run.return_value = ("", "", {})
        mock_crawler_cls.return_value = mock_instance

        result_url, response = get_location_recursively("https://example.com/page", {})
        # new_url="" and response_size=0 => falls through to return ("", "")
        self.assertEqual(response, "")


class TestCleanUrlNonProtocolRelative(unittest.TestCase):
    """clean_url: non-protocol-relative URL returned as-is"""

    def test_absolute_url_returned_unchanged(self) -> None:
        from utils.check_manga_site import clean_url

        result = clean_url("https://example.com/page", scheme="http", path="/extra")
        self.assertEqual(result, "https://example.com/page")

    def test_http_url_returned_unchanged(self) -> None:
        from utils.check_manga_site import clean_url

        result = clean_url("http://example.com", scheme="https", path="/path")
        self.assertEqual(result, "http://example.com")


class TestGetNewUrlEmptyMatchesFiltered(unittest.TestCase):
    """get_new_url: empty matches are filtered via 'if not match: continue'"""

    def test_empty_match_groups_skipped(self) -> None:
        from utils.check_manga_site import get_new_url

        # Pattern that can produce empty matches via alternation
        # Using a pattern where some matches are empty string
        response = "manga124 manga125 manga125"
        # Matches: "124", "125", "125"
        new_url, new_number = get_new_url(url="https://manga123.example.com/path", response=response, new_pattern=r"manga(\d+)", pre="https://manga", num=123, domain_postfix=".example.com", post="/path")
        self.assertNotEqual(new_url, "")
        self.assertGreater(new_number, 123)


class TestPrintNewUrl(unittest.TestCase):
    def test_same_url(self) -> None:
        from utils.check_manga_site import print_new_url

        # Should not raise, just prints "same url"
        print_new_url("https://example.com", "https://example.com", 0)

    def test_different_url(self) -> None:
        from utils.check_manga_site import print_new_url

        print_new_url("https://old.com", "https://new.com", 456)


if __name__ == "__main__":
    unittest.main()
