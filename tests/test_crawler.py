#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import logging
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import requests

from bin.crawler import Crawler, Method, print_usage, RequestsClient
from bin.headless_browser import HeadlessBrowser
import tempfile
from requests.cookies import RequestsCookieJar
import sys as _sys
from bin.crawler import main
from pathlib import Path as _Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Common mock responses
MOCK_HTML_RESPONSE = ("<!DOCTYPE html><html><body>Test</body></html>", "", {}, 200)
MOCK_BASIC_HTML = ("<!DOCTYPE html><html><head><title>Basic Test</title></head><body><h1>Basic Test Page</h1></body></html>", "", {}, 200)
MOCK_UNICODE_HTML = ("<!DOCTYPE html><html><body>안녕하세요</body></html>", "", {}, 200)
MOCK_HEADLESS_HTML = "<!DOCTYPE html><html><body>Test</body></html>"


class TestCrawler(unittest.TestCase):
    """Test Crawler with mock responses"""

    @classmethod
    def setUpClass(cls) -> None:
        # patcher 등록
        cls.patcher_remove = patch("os.remove")
        cls.patcher_isfile = patch("os.path.isfile", return_value=True)
        cls.mock_remove = cls.patcher_remove.start()
        cls.mock_isfile = cls.patcher_isfile.start()
        # Clean up cookie files once at the beginning (실제 파일 접근 없음)
        for cookie_file in (HeadlessBrowser.COOKIE_FILE, RequestsClient.COOKIE_FILE):
            try:
                if os.path.isfile(cookie_file):
                    os.remove(cookie_file)
            except (OSError, ImportError):
                pass

    @classmethod
    def tearDownClass(cls) -> None:
        cls.patcher_remove.stop()
        cls.patcher_isfile.stop()

    def setUp(self) -> None:
        # 각 테스트마다 requests, time.sleep 등 patch
        self.patcher_sleep = patch("time.sleep")
        self.patcher_requests = patch("requests.get")
        self.mock_sleep = self.patcher_sleep.start()
        self.mock_requests = self.patcher_requests.start()

    def tearDown(self) -> None:
        self.patcher_sleep.stop()
        self.patcher_requests.stop()

    def test_print_usage(self) -> None:
        with patch("sys.stdout", new=io.StringIO()) as stdout:
            print_usage()
            output = stdout.getvalue()
            self.assertIn("Usage:", output)
            self.assertIn("--render-js", output)

    def test_get_option_str(self) -> None:
        options = {"render_js": True, "copy_images_from_canvas": False, "simulate_scrolling": True, "user_agent": "Firefox", "referer": "https://abc.com", "encoding": "cp949", "headers": {"Content-Type": "application/json", "Transfer-Encoding": "chunked"}, "timeout": 20}
        actual = Crawler.get_option_str(options)
        expected = " --render-js=true --copy-images-from-canvas=false --simulate-scrolling=true --user-agent='Firefox' --referer='https://abc.com' --encoding='cp949' --header='Content-Type: application/json; Transfer-Encoding: chunked' --timeout=20"
        self.assertEqual(expected, actual)

    @patch("bin.crawler.RequestsClient.make_request")
    def test_crawler_basic(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_BASIC_HTML

        crawler = Crawler()
        self.assertTrue(crawler)
        url = "http://test.com/basic.html"
        actual, _, _ = crawler.run(url)

        self.assertIsNotNone(actual)
        if actual:
            m = re.search(r"<!DOCTYPE html>", actual, re.IGNORECASE)
            self.assertTrue(m)

    @patch("bin.crawler.RequestsClient.make_request")
    def test_crawler_options_passed_to_client(self, mock_make_request: MagicMock) -> None:
        """옵션(timeout, encoding, headers 등)이 Crawler에 올바르게 설정되는지 검증"""
        mock_make_request.return_value = MOCK_HTML_RESPONSE

        headers = {"User-Agent": "TestBot", "Referer": "http://test.com"}
        crawler = Crawler(num_retries=3, timeout=30, encoding="cp949", verify_ssl=False, headers=headers)
        self.assertEqual(crawler.num_retries, 3)
        self.assertEqual(crawler.requests_client.timeout, 30)
        self.assertEqual(crawler.requests_client.encoding, "cp949")
        self.assertFalse(crawler.requests_client.verify_ssl)
        self.assertEqual(crawler.requests_client.headers["User-Agent"], "TestBot")

        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIn("Test", actual)
        mock_make_request.assert_called_once_with(url, download_file=None, data=None, allow_redirects=True)

    @patch("bin.headless_browser.HeadlessBrowser.make_request")
    def test_crawler_with_render_js(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HEADLESS_HTML

        crawler = Crawler(render_js=True)
        url = "http://test.com/test.html"
        actual, _, _ = crawler.run(url)
        self.assertIn("Test", actual)
        mock_make_request.assert_called_once()

    @patch("bin.crawler.RequestsClient.make_request")
    def test_crawler_method_head_and_get(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HTML_RESPONSE

        crawler = Crawler(method=Method.HEAD)
        self.assertEqual(crawler.requests_client.method, Method.HEAD)
        crawler.run("http://test.com/test.html")

        crawler = Crawler(method=Method.GET)
        self.assertEqual(crawler.requests_client.method, Method.GET)
        crawler.run("http://test.com/test.html")

    @patch("bin.crawler.RequestsClient.make_request")
    @patch("time.sleep")  # Mock time.sleep to avoid 5-second delay
    def test_crawler_network_retry(self, mock_sleep: MagicMock, mock_make_request: MagicMock) -> None:
        mock_make_request.side_effect = [("", "Network error", {}, 500), ("<!DOCTYPE html><html><body>Success</body></html>", "", {}, 200)]

        crawler = Crawler(num_retries=2)
        actual, _, _ = crawler.run("http://test.com/test.html")
        self.assertIn("Success", actual)
        self.assertEqual(mock_make_request.call_count, 2)

    @patch("bin.headless_browser.HeadlessBrowser.make_request")
    def test_crawler_with_headless_browser_options(self, mock_make_request: MagicMock) -> None:
        mock_make_request.return_value = MOCK_HEADLESS_HTML

        crawler = Crawler(render_js=True, simulate_scrolling=True, copy_images_from_canvas=True)
        self.assertTrue(crawler.headless_browser.simulate_scrolling)
        self.assertTrue(crawler.headless_browser.copy_images_from_canvas)
        actual, _, _ = crawler.run("http://test.com/test.html")
        self.assertIn("Test", actual)


class TestRequestsClientBlockedURL(unittest.TestCase):
    """make_request with blocked URL / referer scenarios"""

    @patch("bin.crawler.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.client = RequestsClient(dir_path=Path(tempfile.mkdtemp()))

    @patch("bin.crawler.URLSafety.check_url", return_value=(False, "private IP"))
    def test_blocked_url(self, mock_check):
        result, error, headers, status = self.client.make_request("http://192.168.1.1/page")
        self.assertEqual(result, "")
        self.assertIn("blocked url", error)
        self.assertIsNone(status)

    @patch("bin.crawler.URLSafety.check_url")
    def test_blocked_referer_url(self, mock_check):
        # first call (url) passes, second call (referer) fails
        mock_check.side_effect = [(True, ""), (False, "private IP")]
        self.client.headers["Referer"] = "http://192.168.1.1/ref"
        result, error, headers, status = self.client.make_request("http://example.com/page")
        self.assertEqual(result, "")
        self.assertIn("blocked url", error)
        self.assertIsNone(status)


class TestRequestsClientRefererErrors(unittest.TestCase):
    """make_request referer ConnectionError / ReadTimeout"""

    @patch("bin.crawler.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.client = RequestsClient(dir_path=Path(tempfile.mkdtemp()))
        self.client.headers["Referer"] = "http://example.com/ref"

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.get", side_effect=requests.exceptions.ConnectionError("conn err"))
    def test_referer_connection_error(self, mock_get, mock_check):
        result, error, headers, status = self.client.make_request("http://example.com/page")
        self.assertEqual(result, "")
        self.assertIn("can't connect", error)
        self.assertIsNone(status)

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.get", side_effect=requests.exceptions.ReadTimeout("timeout"))
    def test_referer_read_timeout(self, mock_get, mock_check):
        result, error, headers, status = self.client.make_request("http://example.com/page")
        self.assertEqual(result, "")
        self.assertIn("timeout", error)
        self.assertIsNone(status)


class TestRequestsClientMethods(unittest.TestCase):
    """make_request POST / HEAD methods"""

    @patch("bin.crawler.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.tmp = tempfile.mkdtemp()
        self.client = RequestsClient(dir_path=Path(self.tmp))

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.post")
    def test_post_method(self, mock_post, mock_check):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = RequestsCookieJar()
        mock_resp.encoding = "utf-8"
        mock_resp.text = "<html><head></head><body>ok</body></html>"
        mock_resp.request = MagicMock(url="http://example.com/api")
        mock_post.return_value = mock_resp

        self.client.method = Method.POST
        result, error, headers, status = self.client.make_request("http://example.com/api", data={"key": "val"})
        self.assertIn("og:url", result)
        self.assertEqual(status, 200)
        mock_post.assert_called_once()

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.head")
    def test_head_method(self, mock_head, mock_check):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_head.return_value = mock_resp

        self.client.method = Method.HEAD
        result, error, headers, status = self.client.make_request("http://example.com/page")
        self.assertEqual(result, "200")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/html")


class TestRequestsClientNon200AndNone(unittest.TestCase):
    """make_request non-200 status, None response, download_file"""

    @patch("bin.crawler.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.client = RequestsClient(dir_path=Path(tempfile.mkdtemp()))

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.get")
    def test_non_200_status(self, mock_get, mock_check):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.cookies = RequestsCookieJar()
        mock_resp.headers = {"X-Err": "forbidden"}
        mock_get.return_value = mock_resp

        result, error, headers, status = self.client.make_request("http://example.com/secret")
        self.assertEqual(result, "")
        self.assertIn("403", error)
        self.assertEqual(status, 403)

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.get", side_effect=requests.exceptions.ConnectionError("fail"))
    def test_response_connection_error(self, mock_get, mock_check):
        result, error, headers, status = self.client.make_request("http://example.com/page")
        self.assertEqual(result, "")
        self.assertIn("can't connect", error)
        self.assertIsNone(status)

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.get")
    def test_download_file(self, mock_get, mock_check):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = RequestsCookieJar()
        mock_resp.raw = MagicMock()
        mock_resp.__iter__ = MagicMock(return_value=iter([b"data"]))
        mock_get.return_value = mock_resp

        dl_path = Path(tempfile.mkdtemp()) / "downloaded.bin"
        result, error, headers, status = self.client.make_request("http://example.com/file.bin", download_file=dl_path)
        self.assertEqual(result, "200")
        self.assertEqual(status, 200)
        self.assertTrue(dl_path.exists())
        dl_path.unlink(missing_ok=True)


class TestRequestsClientCookiesAndOgUrl(unittest.TestCase):
    """Cookies from referer, og:url injection"""

    @patch("bin.crawler.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.tmp = tempfile.mkdtemp()
        self.client = RequestsClient(dir_path=Path(self.tmp))

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.get")
    def test_cookies_from_referer(self, mock_get, mock_check):
        # referer response with cookies
        referer_resp = MagicMock()
        referer_resp.cookies = RequestsCookieJar()
        referer_resp.cookies.set("sid", "abc123")

        # main response
        main_resp = MagicMock()
        main_resp.status_code = 200
        main_resp.cookies = RequestsCookieJar()
        main_resp.encoding = "utf-8"
        main_resp.text = '<html><head><meta property="og:url" content="http://example.com/page"/></head><body>ok</body></html>'
        main_resp.request = MagicMock(url="http://example.com/page")

        mock_get.side_effect = [referer_resp, main_resp]
        self.client.headers["Referer"] = "http://example.com/ref"

        result, error, headers, status = self.client.make_request("http://example.com/page")
        self.assertEqual(status, 200)
        # og:url already present, no injection
        self.assertEqual(result.count("og:url"), 1)

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.get")
    def test_og_url_injection(self, mock_get, mock_check):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = RequestsCookieJar()
        mock_resp.encoding = "utf-8"
        mock_resp.text = "<html><head><title>Test</title></head><body>ok</body></html>"
        mock_resp.request = MagicMock(url="http://example.com/page")
        mock_get.return_value = mock_resp

        result, error, headers, status = self.client.make_request("http://example.com/page")
        self.assertIn("og:url", result)
        self.assertIn("http://example.com/page", result)


class TestRequestsClientCookieDir(unittest.TestCase):
    """_get_cookie_dir with non-writable directory"""

    @patch("bin.crawler.Env.get", return_value="false")
    def test_non_writable_dir_fallback(self, mock_env):
        client = RequestsClient(dir_path=Path("/nonexistent/readonly/dir"))
        with patch("os.access", return_value=False):
            cookie_dir = client._get_cookie_dir()
            self.assertIn("fm_cookies", str(cookie_dir))


class TestRequestsClientCookieFiles(unittest.TestCase):
    """write_cookies_to_file and read_cookies_from_file"""

    @patch("bin.crawler.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.tmp = Path(tempfile.mkdtemp())
        self.client = RequestsClient(dir_path=self.tmp)

    def test_write_and_read_cookies(self):
        jar = RequestsCookieJar()
        jar.set("token", "xyz")
        jar.set("session", "abc")

        self.client.write_cookies_to_file(jar)

        cookie_file = self.tmp / RequestsClient.COOKIE_FILE
        self.assertTrue(cookie_file.is_file())

        self.client.cookies = {}
        self.client.read_cookies_from_file()
        self.assertEqual(self.client.cookies["token"], "xyz")
        self.assertEqual(self.client.cookies["session"], "abc")

    def test_read_cookies_no_file(self):
        self.client.cookies = {}
        self.client.read_cookies_from_file()
        self.assertEqual(self.client.cookies, {})

    def tearDown(self):
        cookie_file = self.tmp / RequestsClient.COOKIE_FILE
        cookie_file.unlink(missing_ok=True)


class TestCrawlerRunRenderJS(unittest.TestCase):
    """run with render_js=True (mock HeadlessBrowser)"""

    @patch("bin.crawler.HeadlessBrowser")
    def test_render_js_success(self, mock_hb_cls):
        mock_hb = MagicMock()
        mock_hb.make_request.return_value = "<html>rendered</html>"
        mock_hb_cls.return_value = mock_hb

        crawler = Crawler(render_js=True)
        result, error, headers = crawler.run("http://example.com/page")
        self.assertEqual(result, "<html>rendered</html>")
        self.assertEqual(error, "")

    @patch("bin.crawler.HeadlessBrowser")
    def test_render_js_empty_response(self, mock_hb_cls):
        mock_hb = MagicMock()
        mock_hb.make_request.return_value = ""
        mock_hb_cls.return_value = mock_hb

        crawler = Crawler(render_js=True, num_retries=2)
        result, error, headers = crawler.run("http://example.com/page")
        self.assertEqual(result, "")
        self.assertEqual(mock_hb.make_request.call_count, 2)


class TestCrawlerRunRetryStatusCodes(unittest.TestCase):
    """run with retry and various status codes"""

    @patch("bin.crawler.RequestsClient")
    def test_no_retry_on_401(self, mock_rc_cls):
        mock_rc = MagicMock()
        mock_rc.make_request.return_value = ("", "unauthorized", {}, 401)
        mock_rc_cls.return_value = mock_rc

        crawler = Crawler(num_retries=3)
        crawler.requests_client = mock_rc
        result, error, headers = crawler.run("http://example.com/page")
        self.assertEqual(result, "")
        self.assertEqual(mock_rc.make_request.call_count, 1)

    @patch("bin.crawler.RequestsClient")
    def test_no_retry_on_403(self, mock_rc_cls):
        mock_rc = MagicMock()
        mock_rc.make_request.return_value = ("", "forbidden", {}, 403)
        mock_rc_cls.return_value = mock_rc

        crawler = Crawler(num_retries=3)
        crawler.requests_client = mock_rc
        result, error, headers = crawler.run("http://example.com/page")
        self.assertEqual(mock_rc.make_request.call_count, 1)

    @patch("bin.crawler.RequestsClient")
    def test_no_retry_on_404(self, mock_rc_cls):
        mock_rc = MagicMock()
        mock_rc.make_request.return_value = ("", "not found", {}, 404)
        mock_rc_cls.return_value = mock_rc

        crawler = Crawler(num_retries=3)
        crawler.requests_client = mock_rc
        result, error, headers = crawler.run("http://example.com/page")
        self.assertEqual(mock_rc.make_request.call_count, 1)

    @patch("bin.crawler.RequestsClient")
    def test_no_retry_on_405(self, mock_rc_cls):
        mock_rc = MagicMock()
        mock_rc.make_request.return_value = ("", "method not allowed", {}, 405)
        mock_rc_cls.return_value = mock_rc

        crawler = Crawler(num_retries=3)
        crawler.requests_client = mock_rc
        result, error, headers = crawler.run("http://example.com/page")
        self.assertEqual(mock_rc.make_request.call_count, 1)

    @patch("bin.crawler.RequestsClient")
    def test_no_retry_on_410(self, mock_rc_cls):
        mock_rc = MagicMock()
        mock_rc.make_request.return_value = ("", "gone", {}, 410)
        mock_rc_cls.return_value = mock_rc

        crawler = Crawler(num_retries=3)
        crawler.requests_client = mock_rc
        result, error, headers = crawler.run("http://example.com/page")
        self.assertEqual(mock_rc.make_request.call_count, 1)

    @patch("time.sleep")
    @patch("bin.crawler.RequestsClient")
    def test_retry_on_500(self, mock_rc_cls, mock_sleep):
        mock_rc = MagicMock()
        mock_rc.make_request.return_value = ("", "server error", {}, 500)
        mock_rc_cls.return_value = mock_rc

        crawler = Crawler(num_retries=3)
        crawler.requests_client = mock_rc
        result, error, headers = crawler.run("http://example.com/page")
        self.assertEqual(result, "")
        self.assertEqual(mock_rc.make_request.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 3)

    @patch("bin.crawler.RequestsClient")
    def test_read_timeout_exception(self, mock_rc_cls):
        mock_rc = MagicMock()
        mock_rc.make_request.side_effect = requests.exceptions.ReadTimeout("timeout")
        mock_rc_cls.return_value = mock_rc

        crawler = Crawler(num_retries=1)
        crawler.requests_client = mock_rc
        with self.assertRaises(Crawler.ReadTimeoutException):
            crawler.run("http://example.com/page")


class TestCrawlerGetOptionStr(unittest.TestCase):
    """get_option_str with various option combinations"""

    def test_empty_options(self):
        result = Crawler.get_option_str({})
        self.assertEqual(result, "")

    def test_verify_ssl_false(self):
        result = Crawler.get_option_str({"verify_ssl": False})
        self.assertIn("--verify-ssl=false", result)

    def test_blob_to_dataurl(self):
        result = Crawler.get_option_str({"blob_to_dataurl": True})
        self.assertIn("--blob-to-dataurl=true", result)

    def test_disable_headless(self):
        result = Crawler.get_option_str({"disable_headless": True})
        self.assertIn("--disable-headless=true", result)

    def test_headers_with_none_value(self):
        result = Crawler.get_option_str({"headers": {"X-Key": "None"}})
        # "None" value should be skipped
        self.assertNotIn("X-Key: None", result)

    def test_timeout_none(self):
        result = Crawler.get_option_str({"timeout": None})
        self.assertIn("--timeout=60", result)

    def test_user_agent_empty(self):
        result = Crawler.get_option_str({"user_agent": ""})
        self.assertNotIn("--user-agent", result)

    def test_referer_empty(self):
        result = Crawler.get_option_str({"referer": ""})
        self.assertNotIn("--referer", result)

    def test_encoding_empty(self):
        result = Crawler.get_option_str({"encoding": ""})
        self.assertNotIn("--encoding", result)


# ────────────────────────────────────────────────────────
# From test_crawler_main.py
# ────────────────────────────────────────────────────────
class TestCrawlerMain(unittest.TestCase):
    """bin/crawler.py main() 함수 테스트"""

    @patch("bin.crawler.Crawler")
    def test_main_with_url_arg(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("response body", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        mock_crawler_cls.assert_called_once()
        mock_instance.run.assert_called_once_with("https://example.com", download_file=None)

    @patch("bin.crawler.Crawler")
    def test_main_with_f_option(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "-f", "/tmp/feeddir", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args

        self.assertEqual(call_kwargs.kwargs.get("dir_path") or call_kwargs[1].get("dir_path"), _Path("/tmp/feeddir"))

    @patch("bin.crawler.Crawler")
    def test_main_with_spider(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--spider", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertEqual(call_kwargs.kwargs.get("method") or call_kwargs[1].get("method"), Method.HEAD)

    @patch("bin.crawler.Crawler")
    def test_main_with_render_js(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--render-js=true", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertTrue(call_kwargs.kwargs.get("render_js") or call_kwargs[1].get("render_js"))

    @patch("bin.crawler.Crawler")
    def test_main_with_verify_ssl_false(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--verify-ssl=false", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertFalse(call_kwargs.kwargs.get("verify_ssl", True) if "verify_ssl" in call_kwargs.kwargs else call_kwargs[1].get("verify_ssl", True))

    @patch("bin.crawler.Crawler")
    def test_main_with_header(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--header=X-Custom: myvalue", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        self.assertEqual(headers["X-Custom"], "myvalue")

    @patch("bin.crawler.Crawler")
    def test_main_with_timeout_and_retry(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--timeout=30", "--retry=3", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertEqual(call_kwargs.kwargs.get("timeout") or call_kwargs[1].get("timeout"), 30)
        self.assertEqual(call_kwargs.kwargs.get("num_retries") or call_kwargs[1].get("num_retries"), 3)

    @patch("bin.crawler.Crawler")
    def test_main_with_encoding(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--encoding=cp949", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertEqual(call_kwargs.kwargs.get("encoding") or call_kwargs[1].get("encoding"), "cp949")

    @patch("bin.crawler.Crawler")
    def test_main_with_download(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--download=output.html", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        mock_instance.run.assert_called_once_with("https://example.com", download_file=Path("output.html"))

    @patch("bin.crawler.Crawler")
    def test_main_with_user_agent_and_referer(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--user-agent=TestBot", "--referer=http://ref.com", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        self.assertEqual(headers["User-Agent"], "TestBot")
        self.assertEqual(headers["Referer"], "http://ref.com")

    def test_main_no_args(self) -> None:
        with patch.object(_sys, "argv", ["crawler.py"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, -1)

    def test_main_h_option(self) -> None:
        with patch.object(_sys, "argv", ["crawler.py", "-h"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)

    @patch("bin.crawler.Crawler")
    def test_main_with_copy_images_from_canvas(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--copy-images-from-canvas=true", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertTrue(call_kwargs.kwargs.get("copy_images_from_canvas") or call_kwargs[1].get("copy_images_from_canvas"))

    @patch("bin.crawler.Crawler")
    def test_main_with_simulate_scrolling(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--simulate-scrolling=true", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertTrue(call_kwargs.kwargs.get("simulate_scrolling") or call_kwargs[1].get("simulate_scrolling"))

    @patch("bin.crawler.Crawler")
    def test_main_with_disable_headless(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--disable-headless=true", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertTrue(call_kwargs.kwargs.get("disable_headless") or call_kwargs[1].get("disable_headless"))

    @patch("bin.crawler.Crawler")
    def test_main_with_blob_to_dataurl(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(_sys, "argv", ["crawler.py", "--blob-to-dataurl=true", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertTrue(call_kwargs.kwargs.get("blob_to_dataurl") or call_kwargs[1].get("blob_to_dataurl"))

    @patch("bin.crawler.Crawler")
    def test_main_error_response(self, mock_crawler_cls: MagicMock) -> None:
        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("", "connection error", {})

        with patch.object(_sys, "argv", ["crawler.py", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)

    def test_main_invalid_option(self) -> None:
        with patch.object(_sys, "argv", ["crawler.py", "--invalid-option", "https://example.com"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, -1)


class TestRequestsClientReadTimeoutOnMainRequest(unittest.TestCase):
    """make_request ReadTimeout on main request (not referer) → covers L135-138"""

    @patch("bin.crawler.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.client = RequestsClient(dir_path=Path(tempfile.mkdtemp()))

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.get", side_effect=requests.exceptions.ReadTimeout("read timed out"))
    def test_read_timeout_on_main_request(self, mock_get, mock_check):
        result, error, headers, status = self.client.make_request("http://example.com/slow")
        self.assertEqual(result, "")
        self.assertIn("timeout", error)
        self.assertIsNone(status)


class TestRequestsClientResponseNone(unittest.TestCase):
    """response is None after try block → covers L142"""

    @patch("bin.crawler.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.client = RequestsClient(dir_path=Path(tempfile.mkdtemp()))
        # method を無効な値にして response = None のまま通過
        self.client.method = MagicMock()  # not GET/POST/HEAD

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    def test_response_none(self, mock_check):
        result, error, headers, status = self.client.make_request("http://example.com/page")
        self.assertEqual(result, "")
        self.assertIn("can't get response", error)
        self.assertIsNone(status)


class TestRequestsClientCookieWithExpiry(unittest.TestCase):
    """read_cookies_from_file with expiry field → covers L83-84"""

    @patch("bin.crawler.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.tmp = Path(tempfile.mkdtemp())
        self.client = RequestsClient(dir_path=self.tmp)

    def test_cookie_expiry_removed(self):
        import json

        cookie_file = self.tmp / RequestsClient.COOKIE_FILE
        cookies = [{"name": "token", "value": "abc", "expiry": 9999999999}]
        with cookie_file.open("w", encoding="utf-8") as f:
            json.dump(cookies, f)

        self.client.read_cookies_from_file()
        self.assertEqual(self.client.cookies["token"], "abc")

    def tearDown(self):
        cookie_file = self.tmp / RequestsClient.COOKIE_FILE
        cookie_file.unlink(missing_ok=True)


class TestRequestsClientNoEncoding(unittest.TestCase):
    """encoding not set → utf-8 fallback → covers L159-161"""

    @patch("bin.crawler.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.client = RequestsClient(dir_path=Path(tempfile.mkdtemp()), encoding="")

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.get")
    def test_no_encoding_defaults_utf8(self, mock_get, mock_check):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = RequestsCookieJar()
        mock_resp.text = "<html><head></head><body>ok</body></html>"
        mock_resp.request = MagicMock(url="http://example.com/page")
        mock_get.return_value = mock_resp

        result, error, headers, status = self.client.make_request("http://example.com/page")
        self.assertEqual(status, 200)
        self.assertEqual(mock_resp.encoding, "utf-8")

    @patch("bin.crawler.URLSafety.check_url", return_value=(True, ""))
    @patch("requests.get")
    def test_falsy_encoding_hits_else_branch(self, mock_get, mock_check):
        """encoding이 falsy일 때 else 분기(L161) 커버"""
        self.client.encoding = ""  # 직접 falsy로 설정

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = RequestsCookieJar()
        mock_resp.text = "<html><head></head><body>ok</body></html>"
        mock_resp.request = MagicMock(url="http://example.com/page")
        mock_get.return_value = mock_resp

        result, error, headers, status = self.client.make_request("http://example.com/page")
        self.assertEqual(status, 200)
        self.assertEqual(mock_resp.encoding, "utf-8")


# ────────────────────────────────────────────────────────
# Login feature tests
# ────────────────────────────────────────────────────────
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


from bin.crawler import LoginManager


def _find_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


LOGIN_FORM_HTML = """<!DOCTYPE html><html><body>
<form action="/do_login" method="post">
<input type="hidden" name="csrf_token" value="abc123"/>
<input type="hidden" name="redirect" value="/home"/>
<input type="text" name="username"/>
<input type="password" name="passwd"/>
<button type="submit">Login</button>
</form>
</body></html>"""

LOGIN_FORM_NO_HIDDEN_HTML = """<!DOCTYPE html><html><body>
<form method="post">
<input type="text" name="user"/>
<input type="password" name="pass"/>
<input type="submit" value="Login"/>
</form>
</body></html>"""

LOGIN_FORM_RELATIVE_ACTION_HTML = """<!DOCTYPE html><html><body>
<form action="../auth/submit" method="post">
<input type="password" name="pw"/>
</form>
</body></html>"""

NO_FORM_HTML = """<!DOCTYPE html><html><body><p>No form here</p></body></html>"""


class _LoginTestHandler(BaseHTTPRequestHandler):
    """로그인 테스트용 HTTP 핸들러."""

    def log_message(self, format, *args):
        pass  # suppress log output

    def do_GET(self):
        if self.path == "/login":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(LOGIN_FORM_HTML.encode())
        elif self.path == "/protected":
            cookie_header = self.headers.get("Cookie", "")
            if "session_id=" in cookie_header:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><head></head><body>Protected Content</body></html>")
            else:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/do_login":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            # 간단한 검증: username=testuser&passwd=testpass 포함 여부
            if "username=testuser" in body and "passwd=testpass" in body:
                self.send_response(200)
                self.send_header("Set-Cookie", "session_id=valid_session_123; Path=/")
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body>Login OK</body></html>")
            else:
                self.send_response(401)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body>Unauthorized</body></html>")
        else:
            self.send_response(404)
            self.end_headers()


class TestLoginManagerLoadConfig(unittest.TestCase):
    """LoginManager.load_login_config() - 실제 파일 I/O 테스트"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_load_valid_config(self):
        config_data = {"login_url": "http://example.com/login", "id": "user1", "password": "pass1", "id_field": "username", "password_field": "passwd"}
        (self.tmp / ".login.json").write_text(json.dumps(config_data), encoding="utf-8")
        result = LoginManager.load_login_config(self.tmp)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "user1")
        self.assertEqual(result["login_url"], "http://example.com/login")

    def test_load_no_file(self):
        result = LoginManager.load_login_config(self.tmp)
        self.assertIsNone(result)

    def test_load_missing_required_field(self):
        config_data = {"login_url": "http://example.com/login", "id": "user1"}
        (self.tmp / ".login.json").write_text(json.dumps(config_data), encoding="utf-8")
        result = LoginManager.load_login_config(self.tmp)
        self.assertIsNone(result)

    def test_load_invalid_json(self):
        (self.tmp / ".login.json").write_text("not valid json {{{", encoding="utf-8")
        result = LoginManager.load_login_config(self.tmp)
        self.assertIsNone(result)

    def test_load_empty_required_field(self):
        config_data = {"login_url": "", "id": "user1", "password": "pass1"}
        (self.tmp / ".login.json").write_text(json.dumps(config_data), encoding="utf-8")
        result = LoginManager.load_login_config(self.tmp)
        self.assertIsNone(result)

    def test_load_without_optional_fields(self):
        config_data = {"login_url": "http://example.com/login", "id": "user1", "password": "pass1"}
        (self.tmp / ".login.json").write_text(json.dumps(config_data), encoding="utf-8")
        result = LoginManager.load_login_config(self.tmp)
        self.assertIsNotNone(result)
        self.assertNotIn("id_field", result)

    def tearDown(self):
        login_file = self.tmp / ".login.json"
        login_file.unlink(missing_ok=True)


class TestLoginManagerParseForm(unittest.TestCase):
    """LoginManager.parse_login_form() - 순수 함수 테스트, mock 없음"""

    def test_parse_form_with_hidden_fields(self):
        post_url, hidden, id_field, pw_field = LoginManager.parse_login_form(LOGIN_FORM_HTML, "http://example.com/login")
        self.assertEqual(post_url, "http://example.com/do_login")
        self.assertEqual(hidden["csrf_token"], "abc123")
        self.assertEqual(hidden["redirect"], "/home")
        self.assertEqual(id_field, "username")
        self.assertEqual(pw_field, "passwd")

    def test_parse_form_no_hidden_fields(self):
        post_url, hidden, id_field, pw_field = LoginManager.parse_login_form(LOGIN_FORM_NO_HIDDEN_HTML, "http://example.com/login")
        self.assertEqual(post_url, "http://example.com/login")
        self.assertEqual(hidden, {})
        self.assertEqual(id_field, "user")
        self.assertEqual(pw_field, "pass")

    def test_parse_form_relative_action(self):
        post_url, hidden, id_field, pw_field = LoginManager.parse_login_form(LOGIN_FORM_RELATIVE_ACTION_HTML, "http://example.com/app/login")
        self.assertEqual(post_url, "http://example.com/auth/submit")
        self.assertEqual(pw_field, "pw")

    def test_parse_no_form(self):
        post_url, hidden, id_field, pw_field = LoginManager.parse_login_form(NO_FORM_HTML, "http://example.com/login")
        self.assertEqual(post_url, "http://example.com/login")
        self.assertEqual(hidden, {})
        self.assertEqual(id_field, "")
        self.assertEqual(pw_field, "")

    def test_parse_multiple_forms_selects_password_form(self):
        html = """<html><body>
        <form action="/search"><input type="text" name="q"/></form>
        <form action="/login"><input type="text" name="user"/><input type="password" name="pw"/></form>
        </body></html>"""
        post_url, hidden, id_field, pw_field = LoginManager.parse_login_form(html, "http://example.com/page")
        self.assertEqual(post_url, "http://example.com/login")
        self.assertEqual(id_field, "user")
        self.assertEqual(pw_field, "pw")


class TestLoginManagerCheckSuccess(unittest.TestCase):
    """LoginManager.check_login_success() - 최소 mock (Response 객체)"""

    def _make_response(self, status_code, cookies=None):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status_code
        resp.cookies = RequestsCookieJar()
        if cookies:
            for k, v in cookies.items():
                resp.cookies.set(k, v)
        return resp

    def test_success_with_cookies(self):
        resp = self._make_response(200, {"session": "abc"})
        self.assertTrue(LoginManager.check_login_success(resp))

    def test_success_200_no_cookies(self):
        resp = self._make_response(200)
        self.assertTrue(LoginManager.check_login_success(resp))

    def test_success_302_no_cookies(self):
        resp = self._make_response(302)
        self.assertTrue(LoginManager.check_login_success(resp))

    def test_failure_401(self):
        resp = self._make_response(401)
        self.assertFalse(LoginManager.check_login_success(resp))

    def test_failure_403(self):
        resp = self._make_response(403)
        self.assertFalse(LoginManager.check_login_success(resp))


class TestRequestsClientLogin(unittest.TestCase):
    """RequestsClient.login() - 실제 HTTP 서버 기반 통합 테스트"""

    @classmethod
    def setUpClass(cls):
        cls.port = _find_free_port()
        cls.server = HTTPServer(("127.0.0.1", cls.port), _LoginTestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    @patch("bin.crawler.Env.get", return_value="true")
    def test_login_success(self, mock_env):
        client = RequestsClient(dir_path=self.tmp)
        config = {"login_url": f"http://127.0.0.1:{self.port}/login", "id": "testuser", "password": "testpass", "id_field": "username", "password_field": "passwd"}
        result = client.login(config)
        self.assertTrue(result)
        # 쿠키 파일이 생성되었는지 확인
        cookie_file = self.tmp / RequestsClient.COOKIE_FILE
        self.assertTrue(cookie_file.is_file())
        with cookie_file.open("r") as f:
            cookies = json.load(f)
        cookie_names = [c["name"] for c in cookies]
        self.assertIn("session_id", cookie_names)

    @patch("bin.crawler.Env.get", return_value="true")
    def test_login_failure_wrong_credentials(self, mock_env):
        client = RequestsClient(dir_path=self.tmp)
        config = {"login_url": f"http://127.0.0.1:{self.port}/login", "id": "wronguser", "password": "wrongpass", "id_field": "username", "password_field": "passwd"}
        result = client.login(config)
        self.assertFalse(result)

    @patch("bin.crawler.Env.get", return_value="true")
    def test_login_connection_error(self, mock_env):
        client = RequestsClient(dir_path=self.tmp)
        config = {"login_url": "http://127.0.0.1:1/login", "id": "user", "password": "pass", "id_field": "u", "password_field": "p"}
        result = client.login(config)
        self.assertFalse(result)

    def tearDown(self):
        cookie_file = self.tmp / RequestsClient.COOKIE_FILE
        cookie_file.unlink(missing_ok=True)


class TestCrawlerTryLogin(unittest.TestCase):
    """Crawler._try_login() 통합 테스트 - 실제 HTTP 서버"""

    @classmethod
    def setUpClass(cls):
        cls.port = _find_free_port()
        cls.server = HTTPServer(("127.0.0.1", cls.port), _LoginTestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    @patch("bin.crawler.Env.get", return_value="true")
    def test_try_login_with_config(self, mock_env):
        config_data = {"login_url": f"http://127.0.0.1:{self.port}/login", "id": "testuser", "password": "testpass", "id_field": "username", "password_field": "passwd"}
        (self.tmp / ".login.json").write_text(json.dumps(config_data), encoding="utf-8")

        crawler = Crawler(dir_path=self.tmp)
        crawler._try_login()

        # 쿠키가 저장되었는지 확인
        cookie_file = self.tmp / RequestsClient.COOKIE_FILE
        self.assertTrue(cookie_file.is_file())

    @patch("bin.crawler.Env.get", return_value="true")
    def test_try_login_no_config(self, mock_env):
        crawler = Crawler(dir_path=self.tmp)
        # .login.json 없으면 아무것도 안 함 (에러 없이)
        crawler._try_login()

    @patch("bin.crawler.Env.get", return_value="true")
    def test_try_login_skips_if_cookie_exists(self, mock_env):
        config_data = {"login_url": f"http://127.0.0.1:{self.port}/login", "id": "testuser", "password": "testpass", "id_field": "username", "password_field": "passwd"}
        (self.tmp / ".login.json").write_text(json.dumps(config_data), encoding="utf-8")
        # 쿠키 파일 미리 생성
        (self.tmp / RequestsClient.COOKIE_FILE).write_text("[]", encoding="utf-8")

        crawler = Crawler(dir_path=self.tmp)
        # login()이 호출되지 않아야 함
        with patch.object(crawler.requests_client, "login") as mock_login:
            crawler._try_login()
            mock_login.assert_not_called()

    @patch("bin.crawler.Env.get", return_value="true")
    def test_full_login_then_crawl(self, mock_env):
        """로그인 후 보호된 페이지 크롤링 E2E"""
        config_data = {"login_url": f"http://127.0.0.1:{self.port}/login", "id": "testuser", "password": "testpass", "id_field": "username", "password_field": "passwd"}
        (self.tmp / ".login.json").write_text(json.dumps(config_data), encoding="utf-8")

        crawler = Crawler(dir_path=self.tmp)
        response, error, _ = crawler.run(f"http://127.0.0.1:{self.port}/protected")
        self.assertIn("Protected Content", response)

    def tearDown(self):
        for f in self.tmp.iterdir():
            f.unlink(missing_ok=True)


class TestHeadlessBrowserLogin(unittest.TestCase):
    """HeadlessBrowser.login() - selenium mock (불가피)"""

    @patch("bin.headless_browser.Env.get", return_value="false")
    def setUp(self, mock_env):
        self.tmp = Path(tempfile.mkdtemp())
        self.browser = HeadlessBrowser(dir_path=self.tmp)

    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.webdriver.Chrome")
    def test_login_success(self, mock_chrome_cls, mock_which):
        mock_driver = MagicMock()
        mock_chrome_cls.return_value = mock_driver
        mock_driver.current_url = "http://example.com/home"

        mock_id_elem = MagicMock()
        mock_pw_elem = MagicMock()

        def find_element_side_effect(by, name):
            if name == "username":
                return mock_id_elem
            elif name == "passwd":
                return mock_pw_elem
            raise Exception(f"Unexpected: {name}")

        mock_driver.find_element.side_effect = find_element_side_effect

        with patch("bin.headless_browser.WebDriverWait") as mock_wait_cls:
            mock_wait = MagicMock()
            mock_wait_cls.return_value = mock_wait
            mock_wait.until.side_effect = [mock_id_elem, True]

            mock_submit = MagicMock()
            mock_driver.find_element.side_effect = None
            mock_driver.find_element.return_value = mock_submit

            mock_driver.get_cookies.return_value = [{"name": "session", "value": "abc"}]

            config = {"login_url": "http://example.com/login", "id": "testuser", "password": "testpass", "id_field": "username", "password_field": "passwd"}
            result = self.browser.login(config)
            self.assertTrue(result)

    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.webdriver.Chrome")
    def test_login_no_cookies_after_submit(self, mock_chrome_cls, mock_which):
        mock_driver = MagicMock()
        mock_chrome_cls.return_value = mock_driver
        mock_driver.current_url = "http://example.com/login"

        mock_elem = MagicMock()

        with patch("bin.headless_browser.WebDriverWait") as mock_wait_cls:
            mock_wait = MagicMock()
            mock_wait_cls.return_value = mock_wait
            from selenium.common.exceptions import TimeoutException as _SelTE

            mock_wait.until.side_effect = [mock_elem, _SelTE()]

            mock_driver.find_element.return_value = mock_elem
            mock_driver.get_cookies.return_value = []

            config = {"login_url": "http://example.com/login", "id": "user", "password": "pass", "id_field": "username", "password_field": "passwd"}
            result = self.browser.login(config)
            self.assertFalse(result)

    def test_login_no_chromedriver(self):
        with patch("bin.headless_browser.which", return_value=None):
            config = {"login_url": "http://example.com/login", "id": "user", "password": "pass", "id_field": "username", "password_field": "passwd"}
            result = self.browser.login(config)
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
