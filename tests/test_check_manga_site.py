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


# ────────────────────────────────────────────────────────
# From test_check_manga_site_main.py
# ────────────────────────────────────────────────────────
class TestCheckMangaSiteMain(unittest.TestCase):
    """utils/check_manga_site.py main() 함수 테스트"""

    def test_main_no_config_file(self) -> None:
        import tempfile as _tempfile
        from utils.check_manga_site import main

        with _tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = main()
        self.assertEqual(result, -1)

    @patch("utils.check_manga_site.get")
    @patch("utils.check_manga_site.get_url_pattern")
    @patch("utils.check_manga_site.read_config")
    def test_main_success(self, mock_read_config: MagicMock, mock_get_url_pattern: MagicMock, mock_get: MagicMock) -> None:
        import tempfile as _tempfile
        from utils.check_manga_site import main

        mock_read_config.return_value = {"url": "https://manga123.example.com/path", "keyword": "manga"}
        mock_get_url_pattern.return_value = ("pattern", "pre", 123, ".example.com", "/path")
        mock_get.return_value = (True, "response body", "")

        with _tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "site_config.json"
            config_path.write_text(json.dumps({"url": "https://manga123.example.com/path", "keyword": "manga"}))
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = main()

        self.assertEqual(result, 0)

    @patch("utils.check_manga_site.get")
    @patch("utils.check_manga_site.get_url_pattern")
    @patch("utils.check_manga_site.read_config")
    def test_main_failure_with_new_url(self, mock_read_config: MagicMock, mock_get_url_pattern: MagicMock, mock_get: MagicMock) -> None:
        import tempfile as _tempfile
        from utils.check_manga_site import main

        mock_read_config.return_value = {"url": "https://manga123.example.com/path", "keyword": "manga"}
        mock_get_url_pattern.return_value = ("pattern", "pre", 123, ".example.com", "/path")
        mock_get.return_value = (False, "response", "https://manga456.example.com/path")

        with _tempfile.TemporaryDirectory() as tmpdir:
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
        import tempfile as _tempfile
        from utils.check_manga_site import main

        mock_read_config.return_value = {"url": "https://manga123.example.com/path", "keyword": "manga"}
        mock_get_url_pattern.return_value = ("pattern", "pre", 123, ".example.com", "/path")
        mock_get.return_value = (False, "response body", "")
        mock_get_new_url.return_value = ("", 0)

        with _tempfile.TemporaryDirectory() as tmpdir:
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
        import tempfile as _tempfile
        from utils.check_manga_site import main

        mock_read_config.return_value = {"url": "https://manga123.example.com/path", "keyword": "manga"}
        mock_get_url_pattern.return_value = ("pattern", "pre", 123, ".example.com", "/path")
        mock_get.return_value = (False, "response body", "")
        mock_get_new_url.return_value = ("https://manga456.example.com/path", 456)

        with _tempfile.TemporaryDirectory() as tmpdir:
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


class TestReadConfigEmptyObject(unittest.TestCase):
    """read_config: empty/null JSON object triggers NotFoundConfigFileError (branch 22->31)"""

    def test_empty_json_object(self) -> None:
        from utils.check_manga_site import read_config
        from bin.feed_maker_util import NotFoundConfigFileError

        tmp_path = Path("/tmp/test_site_config_empty_obj.json")
        # json.load of "null" returns None, which is falsy -> falls through to raise
        tmp_path.write_text("null", encoding="utf-8")
        try:
            with self.assertRaises(NotFoundConfigFileError):
                read_config(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_empty_json_dict(self) -> None:
        from utils.check_manga_site import read_config
        from bin.feed_maker_util import NotFoundConfigFileError

        tmp_path = Path("/tmp/test_site_config_empty_dict.json")
        # Empty dict {} is falsy -> falls through to raise
        tmp_path.write_text("{}", encoding="utf-8")
        try:
            with self.assertRaises(NotFoundConfigFileError):
                read_config(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)


class TestGetLocationRecursivelyLowercaseLocationWithBody(unittest.TestCase):
    """get_location_recursively: lowercase 'location' header with non-empty response (branches 56->58, 58->61)"""

    @patch("utils.check_manga_site.Crawler")
    def test_lowercase_location_header_with_response_body(self, mock_crawler_cls: MagicMock) -> None:
        from utils.check_manga_site import get_location_recursively

        mock_instance = MagicMock()
        # Response has both body and lowercase location header
        # new_url is set AND response_size > 0 -> neither branch for redirect/direct applies
        # Falls through to return (new_url, response) at line 70
        mock_instance.run.return_value = ("page content", "", {"location": "https://other.com"})
        mock_crawler_cls.return_value = mock_instance

        result_url, response = get_location_recursively("https://example.com/page", {})
        self.assertEqual(result_url, "https://other.com")
        self.assertEqual(response, "page content")

    @patch("utils.check_manga_site.Crawler")
    def test_no_location_header_with_response(self, mock_crawler_cls: MagicMock) -> None:
        """response_headers present but no Location/location key -> new_url stays empty, response_size > 0"""
        from utils.check_manga_site import get_location_recursively

        mock_instance = MagicMock()
        mock_instance.run.return_value = ("page content", "", {"Content-Type": "text/html"})
        mock_crawler_cls.return_value = mock_instance

        result_url, response = get_location_recursively("https://example.com/page", {})
        self.assertEqual(result_url, "https://example.com/page")
        self.assertEqual(response, "page content")


class TestGetNewUrlEmptyMatchString(unittest.TestCase):
    """get_new_url: regex produces empty match strings that are skipped (branch 107->108)"""

    def test_empty_match_string_skipped(self) -> None:
        from utils.check_manga_site import get_new_url

        # Use unittest.mock to inject empty strings into findall results
        with patch("utils.check_manga_site.re") as mock_re:
            # findall returns a mix of empty strings and valid digits
            mock_re.findall.return_value = ["", "200", "", "200"]
            # re.search is used later on the constructed URL
            mock_re.search.return_value = MagicMock(group=lambda x: "200")

            new_url, new_number = get_new_url(url="https://manga123.example.com/path", response="dummy", new_pattern=r"(\d+)", pre="https://manga", num=123, domain_postfix=".example.com", post="/path")
        self.assertNotEqual(new_url, "")
        self.assertEqual(new_number, 200)


class TestGetNewUrlNoPatternMatchOnResult(unittest.TestCase):
    """get_new_url: url_count_map has entries but re.search on new_url returns None (branch 126->128)"""

    def test_pattern_no_match_on_constructed_url(self) -> None:
        from utils.check_manga_site import get_new_url

        # Use a pattern where findall returns digits, but the constructed new_url
        # (pre + match + domain_postfix + post) doesn't match new_pattern
        # new_pattern finds digits, constructs url, but re.search(new_pattern, new_url) fails
        response = "200 200 200"
        # The pattern extracts digits from response
        find_pattern = r"(\d+)"
        # But constructed url = "X" + "200" + "Y" + "Z" = "X200YZ"
        # re.search(r"(\d+)", "X200YZ") would match, so we need a more specific pattern
        # Actually, re.search with the same pattern will always match if it found it before
        # We need a pattern that matches in response but not in the constructed URL
        # Use a lookahead/lookbehind pattern
        find_pattern = r"(?<=\s)(\d+)(?=\s)"
        # response " 200 " matches, constructs "pre200domainpost", re.search won't match
        # because there are no spaces around the digits
        response = " 200 200 200 "
        new_url, new_number = get_new_url(url="dummy", response=response, new_pattern=find_pattern, pre="pre", num=123, domain_postfix="domain", post="post")
        # url_count_map will have "pre200domainpost" but re.search won't match it
        # so new_number stays at the initial value (num=123)
        self.assertEqual(new_url, "pre200domainpost")
        self.assertEqual(new_number, 123)


class TestMainBlock(unittest.TestCase):
    """Cover if __name__ == '__main__' block (branch 195->196)"""

    def test_main_block(self) -> None:
        import runpy

        # run_module re-executes the module as __main__; main() returns -1
        # because there's no site_config.json in cwd
        with self.assertRaises(SystemExit) as cm:
            runpy.run_module("utils.check_manga_site", run_name="__main__", alter_sys=True)
        self.assertEqual(cm.exception.code, -1)


class TestGetLocationRecursivelyOgUrl(unittest.TestCase):
    """get_location_recursively: og:url 메타 태그에서 JS 리다이렉트 감지 (lines 69-72)"""

    @patch("utils.check_manga_site.Crawler")
    def test_og_url_domain_change(self, mock_crawler_cls: MagicMock) -> None:
        """og:url 도메인이 원본과 다를 때 final_url 반환"""
        from utils.check_manga_site import get_location_recursively

        original_url = "https://manga123.example.com/page"
        og_url = "https://manga456.newdomain.com/page"
        html = f'<html><head><meta property="og:url" content="{og_url}"/></head><body>content</body></html>'

        mock_instance = MagicMock()
        mock_instance.run.return_value = (html, "", {})
        mock_crawler_cls.return_value = mock_instance

        result_url, response = get_location_recursively(original_url, {})
        self.assertEqual(result_url, og_url)
        self.assertEqual(response, html)

    @patch("utils.check_manga_site.Crawler")
    def test_og_url_alternate_attribute_order(self, mock_crawler_cls: MagicMock) -> None:
        """content 속성이 property보다 앞에 오는 og:url 포맷 감지"""
        from utils.check_manga_site import get_location_recursively

        original_url = "https://manga123.example.com/page"
        og_url = "https://manga789.otherdomain.com/page"
        html = f'<html><head><meta content="{og_url}" property="og:url"/></head><body>text</body></html>'

        mock_instance = MagicMock()
        mock_instance.run.return_value = (html, "", {})
        mock_crawler_cls.return_value = mock_instance

        result_url, response = get_location_recursively(original_url, {})
        self.assertEqual(result_url, og_url)

    @patch("utils.check_manga_site.Crawler")
    def test_og_url_same_domain_not_returned(self, mock_crawler_cls: MagicMock) -> None:
        """og:url 도메인이 원본과 같을 때 원본 URL 반환"""
        from utils.check_manga_site import get_location_recursively

        url = "https://manga123.example.com/page"
        html = f'<html><head><meta property="og:url" content="{url}"/></head><body>content</body></html>'

        mock_instance = MagicMock()
        mock_instance.run.return_value = (html, "", {})
        mock_crawler_cls.return_value = mock_instance

        result_url, response = get_location_recursively(url, {})
        self.assertEqual(result_url, url)


class TestGetDomainHintFromCookies(unittest.TestCase):
    """get_domain_hint_from_cookies (lines 173-192)"""

    def test_no_cookie_file(self) -> None:
        from utils.check_manga_site import get_domain_hint_from_cookies
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = get_domain_hint_from_cookies("https://manga123.example.com/page")
        self.assertEqual(result, "")

    def test_invalid_json(self) -> None:
        from utils.check_manga_site import get_domain_hint_from_cookies
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cookie_file = Path(tmpdir) / "cookies.headlessbrowser.json"
            cookie_file.write_text("not valid json", encoding="utf-8")
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = get_domain_hint_from_cookies("https://manga123.example.com/page")
        self.assertEqual(result, "")

    def test_no_numeric_domain(self) -> None:
        """도메인에 숫자가 없으면 빈 문자열 반환"""
        from utils.check_manga_site import get_domain_hint_from_cookies
        import tempfile

        cookies = [{"domain": "manga456.example.com"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            cookie_file = Path(tmpdir) / "cookies.headlessbrowser.json"
            cookie_file.write_text(json.dumps(cookies), encoding="utf-8")
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = get_domain_hint_from_cookies("https://nonnumeric.example.com/page")
        self.assertEqual(result, "")

    def test_higher_number_domain_found(self) -> None:
        """쿠키에 더 높은 번호의 도메인이 있으면 반환"""
        from utils.check_manga_site import get_domain_hint_from_cookies
        import tempfile

        cookies = [{"domain": "manga100.example.com"}, {"domain": "manga789.example.com"}, {"domain": "manga456.example.com"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            cookie_file = Path(tmpdir) / "cookies.headlessbrowser.json"
            cookie_file.write_text(json.dumps(cookies), encoding="utf-8")
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = get_domain_hint_from_cookies("https://manga123.example.com/page")
        self.assertEqual(result, "manga789.example.com")

    def test_no_higher_domain(self) -> None:
        """모든 쿠키 도메인이 현재 번호 이하이면 빈 문자열 반환"""
        from utils.check_manga_site import get_domain_hint_from_cookies
        import tempfile

        cookies = [{"domain": "manga50.example.com"}, {"domain": "manga100.example.com"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            cookie_file = Path(tmpdir) / "cookies.headlessbrowser.json"
            cookie_file.write_text(json.dumps(cookies), encoding="utf-8")
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = get_domain_hint_from_cookies("https://manga123.example.com/page")
        self.assertEqual(result, "")

    def test_cookie_without_domain_key(self) -> None:
        """domain 키가 없는 쿠키 항목은 무시"""
        from utils.check_manga_site import get_domain_hint_from_cookies
        import tempfile

        cookies = [{"name": "session", "value": "abc"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            cookie_file = Path(tmpdir) / "cookies.headlessbrowser.json"
            cookie_file.write_text(json.dumps(cookies), encoding="utf-8")
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = get_domain_hint_from_cookies("https://manga123.example.com/page")
        self.assertEqual(result, "")


class TestMainDomainHintFromCookies(unittest.TestCase):
    """main(): get_domain_hint_from_cookies가 domain을 반환할 때 (lines 225-227)"""

    @patch("utils.check_manga_site.get_domain_hint_from_cookies")
    @patch("utils.check_manga_site.get_new_url")
    @patch("utils.check_manga_site.get")
    @patch("utils.check_manga_site.get_url_pattern")
    @patch("utils.check_manga_site.read_config")
    def test_main_uses_cookie_domain_hint(self, mock_read_config: MagicMock, mock_get_url_pattern: MagicMock, mock_get: MagicMock, mock_get_new_url: MagicMock, mock_get_domain_hint: MagicMock) -> None:
        import tempfile
        from utils.check_manga_site import main

        url = "https://manga123.example.com/path"
        mock_read_config.return_value = {"url": url, "keyword": "manga"}
        mock_get_url_pattern.side_effect = [("pattern", "pre", 123, ".example.com", "/path"), ("pattern2", "pre", 789, ".example.com", "/path")]
        mock_get.return_value = (False, "response body", "")
        mock_get_new_url.return_value = ("", 0)
        mock_get_domain_hint.return_value = "manga789.example.com"

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "site_config.json"
            config_path.write_text(json.dumps({"url": url, "keyword": "manga"}), encoding="utf-8")
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = main()

        self.assertEqual(result, -1)
        mock_get_domain_hint.assert_called_once_with(url)

    @patch("utils.check_manga_site.get_domain_hint_from_cookies")
    @patch("utils.check_manga_site.get_new_url")
    @patch("utils.check_manga_site.get")
    @patch("utils.check_manga_site.get_url_pattern")
    @patch("utils.check_manga_site.read_config")
    def test_main_no_cookie_domain_hint(self, mock_read_config: MagicMock, mock_get_url_pattern: MagicMock, mock_get: MagicMock, mock_get_new_url: MagicMock, mock_get_domain_hint: MagicMock) -> None:
        """get_domain_hint_from_cookies가 빈 문자열 반환 → 'can't get new url' 출력 (line 229)"""
        import tempfile
        from utils.check_manga_site import main

        url = "https://manga123.example.com/path"
        mock_read_config.return_value = {"url": url, "keyword": "manga"}
        mock_get_url_pattern.return_value = ("pattern", "pre", 123, ".example.com", "/path")
        mock_get.return_value = (False, "response body", "")
        mock_get_new_url.return_value = ("", 0)
        mock_get_domain_hint.return_value = ""

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "site_config.json"
            config_path.write_text(json.dumps({"url": url, "keyword": "manga"}), encoding="utf-8")
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                result = main()

        self.assertEqual(result, -1)


if __name__ == "__main__":
    unittest.main()
