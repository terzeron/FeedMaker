#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import requests
from requests.cookies import RequestsCookieJar

from bin.crawler import Crawler, Method, RequestsClient


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


if __name__ == "__main__":
    unittest.main()
