import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

from selenium.common.exceptions import TimeoutException, WebDriverException


class TestHeadlessBrowserInit(unittest.TestCase):
    """Test __init__ with default and custom options"""

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_init_defaults(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        b = HeadlessBrowser()
        self.assertEqual(b.dir_path, Path.cwd())
        self.assertIn("User-Agent", b.headers)
        self.assertFalse(b.copy_images_from_canvas)
        self.assertFalse(b.simulate_scrolling)
        self.assertFalse(b.disable_headless)
        self.assertFalse(b.blob_to_dataurl)
        self.assertEqual(b.timeout, 60)

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_init_custom(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        headers = {"User-Agent": "CustomBot", "Referer": "http://example.com"}
        b = HeadlessBrowser(dir_path=Path("/tmp"), headers=headers, copy_images_from_canvas=True, simulate_scrolling=True, disable_headless=True, blob_to_dataurl=True, timeout=30)
        self.assertEqual(b.dir_path, Path("/tmp"))
        self.assertEqual(b.headers["User-Agent"], "CustomBot")
        self.assertTrue(b.copy_images_from_canvas)
        self.assertTrue(b.simulate_scrolling)
        self.assertTrue(b.disable_headless)
        self.assertTrue(b.blob_to_dataurl)
        self.assertEqual(b.timeout, 30)


class TestGetCookieDir(unittest.TestCase):
    """Test _get_cookie_dir: writable and non-writable directory"""

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_writable_dir(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        with tempfile.TemporaryDirectory() as tmpdir:
            b = HeadlessBrowser(dir_path=Path(tmpdir))
            result = b._get_cookie_dir()
            self.assertEqual(result, Path(tmpdir))

    @patch("bin.headless_browser.Env.get", return_value="false")
    @patch("os.access", return_value=False)
    def test_non_writable_dir(self, mock_access, mock_env):
        from bin.headless_browser import HeadlessBrowser

        b = HeadlessBrowser(dir_path=Path("/nonexistent/readonly"))
        result = b._get_cookie_dir()
        self.assertIn("fm_cookies", str(result))
        self.assertTrue(result.exists())


class TestOptionsHash(unittest.TestCase):
    """Test _get_options_hash returns consistent hash"""

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_consistent_hash(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        opts = MagicMock()
        opts.arguments = ["--headless", "--no-sandbox"]
        h1 = HeadlessBrowser._get_options_hash(opts)
        h2 = HeadlessBrowser._get_options_hash(opts)
        self.assertEqual(h1, h2)
        self.assertIsInstance(h1, str)
        self.assertTrue(len(h1) > 0)


class TestCachedDriver(unittest.TestCase):
    """Test _get_cached_driver, _set_cached_driver, _cleanup_cached_driver"""

    def setUp(self):
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser.cleanup_all_drivers()

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_no_cache(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        opts = MagicMock()
        opts.arguments = ["--headless"]
        result = HeadlessBrowser._get_cached_driver(opts)
        self.assertIsNone(result)

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_matching_hash(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        opts = MagicMock()
        opts.arguments = ["--headless"]
        driver = MagicMock()
        driver.current_url = "about:blank"
        HeadlessBrowser._set_cached_driver(driver, opts)
        result = HeadlessBrowser._get_cached_driver(opts)
        self.assertIs(result, driver)

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_mismatched_hash(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        opts1 = MagicMock()
        opts1.arguments = ["--headless"]
        opts2 = MagicMock()
        opts2.arguments = ["--no-headless"]
        driver = MagicMock()
        driver.current_url = "about:blank"
        HeadlessBrowser._set_cached_driver(driver, opts1)
        result = HeadlessBrowser._get_cached_driver(opts2)
        self.assertIsNone(result)

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_dead_driver(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        opts = MagicMock()
        opts.arguments = ["--headless"]
        driver = MagicMock()
        type(driver).current_url = PropertyMock(side_effect=WebDriverException("dead"))
        HeadlessBrowser._set_cached_driver(driver, opts)
        result = HeadlessBrowser._get_cached_driver(opts)
        self.assertIsNone(result)

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_set_cached_driver(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        opts = MagicMock()
        opts.arguments = ["--headless"]
        driver = MagicMock()
        HeadlessBrowser._set_cached_driver(driver, opts)
        self.assertIs(HeadlessBrowser._thread_local._driver_cache, driver)

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_cleanup_with_cache(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        opts = MagicMock()
        opts.arguments = ["--headless"]
        driver = MagicMock()
        HeadlessBrowser._set_cached_driver(driver, opts)
        HeadlessBrowser._cleanup_cached_driver()
        driver.quit.assert_called_once()
        self.assertIsNone(HeadlessBrowser._thread_local._driver_cache)

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_cleanup_without_cache(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        # Should not raise
        HeadlessBrowser._cleanup_cached_driver()

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_cleanup_all_drivers(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        opts = MagicMock()
        opts.arguments = ["--headless"]
        driver = MagicMock()
        HeadlessBrowser._set_cached_driver(driver, opts)
        HeadlessBrowser.cleanup_all_drivers()
        driver.quit.assert_called_once()


class TestCookies(unittest.TestCase):
    """Test _write_cookies_to_file and _read_cookies_from_file"""

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_write_and_read_cookies(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        with tempfile.TemporaryDirectory() as tmpdir:
            b = HeadlessBrowser(dir_path=Path(tmpdir))
            driver = MagicMock()
            driver.get_cookies.return_value = [{"name": "test", "value": "val", "domain": ".example.com"}]
            b._write_cookies_to_file(driver)

            cookie_file = Path(tmpdir) / HeadlessBrowser.COOKIE_FILE
            self.assertTrue(cookie_file.exists())

            driver2 = MagicMock()
            b._read_cookies_from_file(driver2)
            driver2.add_cookie.assert_called_once()
            call_arg = driver2.add_cookie.call_args[0][0]
            self.assertEqual(call_arg["name"], "test")

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_read_cookies_no_file(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        with tempfile.TemporaryDirectory() as tmpdir:
            b = HeadlessBrowser(dir_path=Path(tmpdir))
            driver = MagicMock()
            # Should not raise when no cookie file exists
            b._read_cookies_from_file(driver)
            driver.add_cookie.assert_not_called()

    @patch("bin.headless_browser.Env.get", return_value="false")
    def test_read_cookies_with_expiry_removed(self, mock_env):
        from bin.headless_browser import HeadlessBrowser

        with tempfile.TemporaryDirectory() as tmpdir:
            b = HeadlessBrowser(dir_path=Path(tmpdir))
            cookie_file = Path(tmpdir) / HeadlessBrowser.COOKIE_FILE
            cookies = [{"name": "c1", "value": "v1", "domain": ".ex.com", "expiry": 999}]
            with cookie_file.open("w") as f:
                json.dump(cookies, f)

            driver = MagicMock()
            b._read_cookies_from_file(driver)
            call_arg = driver.add_cookie.call_args[0][0]
            self.assertNotIn("expiry", call_arg)


class TestMakeRequest(unittest.TestCase):
    """Test make_request with various scenarios"""

    def setUp(self):
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser.cleanup_all_drivers()

    @patch("bin.headless_browser.Env.get", return_value="false")
    @patch("bin.headless_browser.URLSafety.check_url", return_value=(False, "blocked"))
    def test_url_safety_blocked(self, mock_check, mock_env):
        from bin.headless_browser import HeadlessBrowser

        b = HeadlessBrowser()
        result = b.make_request("http://evil.example.com")
        self.assertEqual(result, "")

    @patch("bin.headless_browser.Env.get", return_value="false")
    @patch("bin.headless_browser.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.webdriver.Chrome")
    @patch("bin.headless_browser.WebDriverWait")
    def test_successful_request(self, mock_wait, mock_chrome_cls, mock_which, mock_check, mock_env):
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.page_source = "<html>OK</html>"
        mock_driver.current_url = "about:blank"
        mock_driver.get_cookies.return_value = []
        mock_chrome_cls.return_value = mock_driver
        mock_wait_inst = MagicMock()
        mock_wait.return_value = mock_wait_inst

        b = HeadlessBrowser()
        result = b.make_request("http://example.com")
        self.assertEqual(result, "<html>OK</html>")
        mock_driver.get.assert_called_with("http://example.com")

    @patch("bin.headless_browser.Env.get", return_value="false")
    @patch("bin.headless_browser.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.webdriver.Chrome")
    @patch("bin.headless_browser.WebDriverWait")
    def test_timeout_exception(self, mock_wait, mock_chrome_cls, mock_which, mock_check, mock_env):
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.get.side_effect = TimeoutException("timeout")
        mock_driver.current_url = "about:blank"
        mock_chrome_cls.return_value = mock_driver
        mock_wait_inst = MagicMock()
        mock_wait.return_value = mock_wait_inst

        b = HeadlessBrowser()
        result = b.make_request("http://example.com")
        self.assertEqual(result, "")

    @patch("bin.headless_browser.Env.get", return_value="false")
    @patch("bin.headless_browser.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.webdriver.Chrome")
    @patch("bin.headless_browser.WebDriverWait")
    def test_webdriver_exception(self, mock_wait, mock_chrome_cls, mock_which, mock_check, mock_env):
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.get.side_effect = WebDriverException("network error")
        mock_driver.current_url = "about:blank"
        mock_chrome_cls.return_value = mock_driver
        mock_wait_inst = MagicMock()
        mock_wait.return_value = mock_wait_inst

        b = HeadlessBrowser()
        result = b.make_request("http://example.com")
        self.assertEqual(result, "")

    @patch("bin.headless_browser.Env.get", return_value="false")
    @patch("bin.headless_browser.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.webdriver.Chrome")
    @patch("bin.headless_browser.WebDriverWait")
    def test_request_with_referer(self, mock_wait, mock_chrome_cls, mock_which, mock_check, mock_env):
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.page_source = "<html>Ref</html>"
        mock_driver.current_url = "about:blank"
        mock_driver.get_cookies.return_value = []
        mock_chrome_cls.return_value = mock_driver
        mock_wait_inst = MagicMock()
        mock_wait.return_value = mock_wait_inst

        b = HeadlessBrowser(headers={"Referer": "http://referer.com"})
        result = b.make_request("http://example.com")
        self.assertEqual(result, "<html>Ref</html>")
        # Should have called get twice: once for referer, once for the URL
        calls = mock_driver.get.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][0], "http://referer.com")
        self.assertEqual(calls[1][0][0], "http://example.com")

    @patch("bin.headless_browser.Env.get", return_value="false")
    @patch("bin.headless_browser.URLSafety.check_url")
    def test_referer_blocked(self, mock_check, mock_env):
        from bin.headless_browser import HeadlessBrowser

        # First call (URL check) passes, second call (referer check) fails
        mock_check.side_effect = [(True, ""), (False, "referer blocked")]

        with patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver"), patch("bin.headless_browser.webdriver.Chrome") as mock_chrome_cls, patch("bin.headless_browser.WebDriverWait"):
            mock_driver = MagicMock()
            mock_driver.current_url = "about:blank"
            mock_chrome_cls.return_value = mock_driver

            b = HeadlessBrowser(headers={"Referer": "http://evil.com"})
            result = b.make_request("http://example.com")
            self.assertEqual(result, "")

    @patch("bin.headless_browser.Env.get", return_value="false")
    @patch("bin.headless_browser.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.webdriver.Chrome")
    @patch("bin.headless_browser.WebDriverWait")
    def test_copy_images_from_canvas(self, mock_wait, mock_chrome_cls, mock_which, mock_check, mock_env):
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.page_source = "<html>canvas</html>"
        mock_driver.current_url = "about:blank"
        mock_driver.get_cookies.return_value = []
        mock_chrome_cls.return_value = mock_driver
        mock_wait_inst = MagicMock()
        mock_wait.return_value = mock_wait_inst

        b = HeadlessBrowser(copy_images_from_canvas=True)
        result = b.make_request("http://example.com")
        self.assertEqual(result, "<html>canvas</html>")
        # Should have executed the canvas conversion script
        script_calls = [str(c) for c in mock_driver.execute_script.call_args_list]
        self.assertTrue(any("images_from_canvas" in s for s in script_calls))

    @patch("bin.headless_browser.Env.get", return_value="false")
    @patch("bin.headless_browser.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.webdriver.Chrome")
    @patch("bin.headless_browser.WebDriverWait")
    def test_simulate_scrolling(self, mock_wait, mock_chrome_cls, mock_which, mock_check, mock_env):
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.page_source = "<html>scroll</html>"
        mock_driver.current_url = "about:blank"
        mock_driver.get_cookies.return_value = []
        mock_chrome_cls.return_value = mock_driver
        mock_wait_inst = MagicMock()
        mock_wait.return_value = mock_wait_inst

        b = HeadlessBrowser(simulate_scrolling=True)
        result = b.make_request("http://example.com")
        self.assertEqual(result, "<html>scroll</html>")
        mock_driver.execute_async_script.assert_called_once()

    @patch("bin.headless_browser.Env.get", return_value="false")
    @patch("bin.headless_browser.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.webdriver.Chrome")
    @patch("bin.headless_browser.WebDriverWait")
    def test_blob_to_dataurl(self, mock_wait, mock_chrome_cls, mock_which, mock_check, mock_env):
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.page_source = "<html>blob</html>"
        mock_driver.current_url = "about:blank"
        mock_driver.get_cookies.return_value = []
        mock_chrome_cls.return_value = mock_driver
        mock_wait_inst = MagicMock()
        mock_wait.return_value = mock_wait_inst

        b = HeadlessBrowser(blob_to_dataurl=True)
        result = b.make_request("http://example.com")
        self.assertEqual(result, "<html>blob</html>")
        script_calls = [str(c) for c in mock_driver.execute_script.call_args_list]
        self.assertTrue(any("blob" in s.lower() for s in script_calls))


if __name__ == "__main__":
    unittest.main()
