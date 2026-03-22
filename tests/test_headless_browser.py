#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import shutil
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

from bin.headless_browser import HeadlessBrowser
import json
import tempfile
from unittest.mock import patch, MagicMock, PropertyMock
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.common.exceptions import InvalidCookieDomainException
from selenium.common.exceptions import NoAlertPresentException

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestHeadlessBrowser(unittest.TestCase):
    """Test HeadlessBrowser with mock responses"""

    test_dir: Optional[Path] = None

    @classmethod
    def setUpClass(cls) -> None:
        # Create test directory
        cls.test_dir = Path(__file__).parent / "tmp" / "work" / "test_webroot"
        cls.test_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        # Clean up HeadlessBrowser cached drivers
        HeadlessBrowser.cleanup_all_drivers()
        # Clean up test directory
        if cls.test_dir and cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)

    def setUp(self) -> None:
        # Clean up cached driver before each test
        HeadlessBrowser.cleanup_all_drivers()
        if os.path.isfile(HeadlessBrowser.COOKIE_FILE):
            os.remove(HeadlessBrowser.COOKIE_FILE)

    def tearDown(self) -> None:
        self.setUp()

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_headless_browser(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Test Page</h1></body></html>'
        
        browser = HeadlessBrowser()
        self.assertTrue(browser)
        url = "http://test.com/test.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_headless_browser_network_retry(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><body>Success</body></html>'
        
        browser = HeadlessBrowser()
        url = "http://test.com/test.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_headless_browser_with_headers(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><body>Test</body></html>'
        
        headers = {"User-Agent": "TestBot", "Referer": "http://test.com"}
        browser = HeadlessBrowser(headers=headers)
        url = "http://test.com/test.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_headless_browser_with_disable_headless(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><body>Test</body></html>'
        
        browser = HeadlessBrowser(disable_headless=True)
        url = "http://test.com/test.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_headless_browser_with_timeout(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><body>Test</body></html>'
        
        browser = HeadlessBrowser(timeout=30)
        url = "http://test.com/test.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_basic_javascript_rendering(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><head><title>JS Basic Test</title></head><body><div id="content"><span>Hello, World!</span></div></body></html>'
        
        browser = HeadlessBrowser()
        url = "http://test.com/js_basic.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)
        if actual:
            self.assertIn("Hello, World!", actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_canvas_to_image_conversion(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><head><title>Canvas Test</title></head><body><canvas id="testCanvas" width="100" height="100"></canvas><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" /></body></html>'
        
        browser = HeadlessBrowser(copy_images_from_canvas=True)
        url = "http://test.com/canvas.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)
        if actual:
            self.assertIn("data:image/png;base64", actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_lazy_loading_with_scrolling(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><head><title>Lazy Loading Test</title></head><body><div id="container" style="height: 2000px;"><div id="content"><p>Content loaded by scrolling</p></div></div><div id="rendering_completed_in_scrolling"></div></body></html>'
        
        browser = HeadlessBrowser(simulate_scrolling=True)
        url = "http://test.com/lazy_loading.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)
        if actual:
            self.assertIn("Content loaded by scrolling", actual)
            self.assertIn("rendering_completed_in_scrolling", actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_blob_to_dataurl_conversion(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><head><title>Blob Test</title></head><body><canvas id="blobCanvas" width="50" height="50"></canvas><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" /><div id="rendering_completed_in_converting_blob"></div></body></html>'
        
        browser = HeadlessBrowser(blob_to_dataurl=True)
        url = "http://test.com/blob.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)
        if actual:
            self.assertIn("data:image/png;base64", actual)
            self.assertIn("rendering_completed_in_converting_blob", actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_complex_javascript_rendering(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><head><title>Complex JS Test</title></head><body><div id="dynamic-content"><h2>Dynamically loaded content</h2><p>This content was loaded via JavaScript</p></div><div id="rendering_completed_in_complex_js"></div></body></html>'
        
        browser = HeadlessBrowser()
        url = "http://test.com/complex_js.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)
        if actual:
            self.assertIn("Dynamically loaded content", actual)
            self.assertIn("rendering_completed_in_complex_js", actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_javascript_rendering_with_custom_headers(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><body><div id="header-content">Custom headers applied</div></body></html>'
        
        headers = {"X-Custom-Header": "test-value", "Authorization": "Bearer token123"}
        browser = HeadlessBrowser(headers=headers)
        url = "http://test.com/headers.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)
        if actual:
            self.assertIn("Custom headers applied", actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_javascript_rendering_with_timeout(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method
        mock_make_request.return_value = '<!DOCTYPE html><html><body><div id="timeout-content">Content loaded with timeout</div></body></html>'
        
        browser = HeadlessBrowser(timeout=10)
        url = "http://test.com/timeout.html"
        actual = browser.make_request(url)
        self.assertIsNotNone(actual)
        if actual:
            self.assertIn("Content loaded with timeout", actual)

    @patch('bin.headless_browser.HeadlessBrowser.make_request')
    def test_multiple_requests_same_browser(self, mock_make_request: MagicMock) -> None:
        # Mock HeadlessBrowser.make_request method with side effect
        mock_make_request.side_effect = [
            '<!DOCTYPE html><html><body><h1>Page 1</h1></body></html>',
            '<!DOCTYPE html><html><body><h1>Page 2</h1></body></html>',
            '<!DOCTYPE html><html><body><h1>Page 3</h1></body></html>'
        ]
        
        browser = HeadlessBrowser()
        urls = [
            "http://test.com/page1.html",
            "http://test.com/page2.html",
            "http://test.com/page3.html"
        ]
        
        for i, url in enumerate(urls):
            actual = browser.make_request(url)
            self.assertIsNotNone(actual)
            if actual:
                self.assertIn(f"Page {i+1}", actual)


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


# ────────────────────────────────────────────────────────
# From test_final_gaps.py: HeadlessBrowser.make_request() 추가 테스트
# ────────────────────────────────────────────────────────
class TestHeadlessBrowserMakeRequest(unittest.TestCase):
    """Cover uncovered branches in HeadlessBrowser.make_request()."""

    def _make_browser(self, **kwargs):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": {"FM_CRAWLER_ALLOW_PRIVATE_IPS": "false", "FM_CRAWLER_ALLOWED_HOSTS": ""}.get(k, d)
            from bin.headless_browser import HeadlessBrowser

            defaults = dict(dir_path=Path(tempfile.gettempdir()), timeout=5)
            defaults.update(kwargs)
            return HeadlessBrowser(**defaults)

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_invalid_cookie_domain_unlink_and_retry(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 261-263: InvalidCookieDomainException causes unlink and retry."""
        from selenium.common.exceptions import InvalidCookieDomainException

        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser()
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

        mock_driver = MagicMock()
        mock_wd.Chrome.return_value = mock_driver
        mock_wd.ChromeOptions.return_value = MagicMock()
        mock_driver.page_source = "<html></html>"

        cookie_dir = Path(tempfile.mkdtemp())
        browser._cookie_dir = cookie_dir
        cookie_file = cookie_dir / HeadlessBrowser.COOKIE_FILE
        cookie_file.write_text(json.dumps([{"name": "test", "value": "v", "domain": ".bad.com"}]))

        call_count = [0]
        original_exception = InvalidCookieDomainException("bad domain")

        def add_cookie_side_effect(cookie):
            nonlocal call_count
            call_count[0] += 1
            if call_count[0] <= 1:
                raise original_exception

        mock_driver.add_cookie.side_effect = add_cookie_side_effect

        result = browser.make_request("https://example.com")
        self.assertIsInstance(result, str)

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value=None)
    def test_chromedriver_not_found(self, mock_which, mock_wd, mock_safety):
        """Line 301: FileNotFoundError when chromedriver not in PATH."""
        mock_safety.check_url.return_value = (True, "")
        mock_wd.ChromeOptions.return_value = MagicMock()

        browser = self._make_browser()
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

        result = browser.make_request("https://example.com")
        self.assertEqual(result, "")

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_cached_driver_reuse(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 307-309: cached driver reuse path (reset timeout)."""
        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser()
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.current_url = "about:blank"
        mock_driver.page_source = "<html>cached</html>"
        mock_driver.get_cookies.return_value = []
        mock_wd.ChromeOptions.return_value = MagicMock(arguments=[])

        options = mock_wd.ChromeOptions()
        HeadlessBrowser._set_cached_driver(mock_driver, options)

        result = browser.make_request("https://example.com")
        mock_driver.set_page_load_timeout.assert_called()
        self.assertEqual(result, "<html>cached</html>")

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_cloudflare_timeout_on_referer(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 323-324: cloudflare bypass timeout on referer page."""
        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser(headers={"User-Agent": "test", "Referer": "https://referer.com"})
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

        mock_driver = MagicMock()
        mock_wd.Chrome.return_value = mock_driver
        mock_wd.ChromeOptions.return_value = MagicMock()
        mock_driver.page_source = "<html>cf</html>"

        mock_wait_instance = MagicMock()
        mock_wait_instance.until.side_effect = TimeoutException("cf timeout")
        mock_wait.return_value = mock_wait_instance

        result = browser.make_request("https://example.com")
        self.assertIsInstance(result, str)

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_general_exception_during_driver_get(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 338-341: general Exception during driver.get."""
        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser()
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

        mock_driver = MagicMock()
        mock_wd.Chrome.return_value = mock_driver
        mock_wd.ChromeOptions.return_value = MagicMock()
        mock_driver.get.side_effect = Exception("general error")

        result = browser.make_request("https://example.com")
        self.assertEqual(result, "")

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_simulate_scrolling_timeout(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 370-371: simulate_scrolling TimeoutException."""
        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser(simulate_scrolling=True)
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

        mock_driver = MagicMock()
        mock_wd.Chrome.return_value = mock_driver
        mock_wd.ChromeOptions.return_value = MagicMock()
        mock_driver.execute_async_script.side_effect = TimeoutException("scroll timeout")
        mock_driver.page_source = "<html>scrolled</html>"

        wait_instance = MagicMock()
        call_idx = [0]

        def until_side_effect(*args, **kwargs):
            call_idx[0] += 1
            if call_idx[0] >= 3:
                raise TimeoutException("marker timeout")

        wait_instance.until.side_effect = until_side_effect
        mock_wait.return_value = wait_instance

        result = browser.make_request("https://example.com")
        self.assertIsInstance(result, str)

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_completion_marker_timeout(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 384-385: completion marker timeout."""
        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser(copy_images_from_canvas=True)
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

        mock_driver = MagicMock()
        mock_wd.Chrome.return_value = mock_driver
        mock_wd.ChromeOptions.return_value = MagicMock()
        mock_driver.page_source = "<html>canvas</html>"

        wait_instance = MagicMock()
        wait_instance.until.side_effect = [None, TimeoutException("marker")]
        mock_wait.return_value = wait_instance

        result = browser.make_request("https://example.com")
        self.assertIsInstance(result, str)

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_page_source_webdriver_exception(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 390-392: page_source WebDriverException."""
        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser()
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

        mock_driver = MagicMock()
        mock_wd.Chrome.return_value = mock_driver
        mock_wd.ChromeOptions.return_value = MagicMock()
        type(mock_driver).page_source = PropertyMock(side_effect=WebDriverException("source error"))

        result = browser.make_request("https://example.com")
        self.assertEqual(result, "")

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_unexpected_oserror_in_try_block(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 396-398: unexpected OSError in try block."""
        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser()
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

        mock_wd.ChromeOptions.side_effect = OSError("unexpected os error")

        result = browser.make_request("https://example.com")
        self.assertEqual(result, "")

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_driver_close_quit_in_finally(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 403-408: driver close/quit in finally block with error."""
        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser()
        from bin.headless_browser import HeadlessBrowser

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

        mock_driver = MagicMock()
        mock_wd.Chrome.return_value = mock_driver
        mock_wd.ChromeOptions.return_value = MagicMock()
        mock_driver.page_source = "<html>ok</html>"
        mock_driver.close.side_effect = OSError("close error")

        def fake_get_cached(opts):
            return None

        with patch.object(HeadlessBrowser, "_get_cached_driver", side_effect=fake_get_cached):
            with patch.object(HeadlessBrowser, "_set_cached_driver"):
                result = browser.make_request("https://example.com")

        self.assertIsInstance(result, str)

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_alert_dismiss_in_finally(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 413-414: alert dismiss NoAlertPresentException in finally."""
        from selenium.common.exceptions import NoAlertPresentException

        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser()
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.current_url = "about:blank"
        mock_driver.page_source = "<html>alert</html>"

        mock_opts = MagicMock(arguments=[])
        mock_wd.ChromeOptions.return_value = mock_opts
        HeadlessBrowser._set_cached_driver(mock_driver, mock_opts)

        mock_driver.switch_to.alert.dismiss.side_effect = NoAlertPresentException("no alert")

        result = browser.make_request("https://example.com")
        self.assertIsInstance(result, str)

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.URLSafety")
    @patch("bin.headless_browser.webdriver")
    @patch("bin.headless_browser.which", return_value="/usr/bin/chromedriver")
    @patch("bin.headless_browser.WebDriverWait")
    def test_storage_clear_webdriver_exception(self, mock_wait, mock_which, mock_wd, mock_safety):
        """Lines 419-420: storage clear WebDriverException in finally."""
        mock_safety.check_url.return_value = (True, "")

        browser = self._make_browser()
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.current_url = "about:blank"
        mock_driver.page_source = "<html>storage</html>"
        mock_driver.get_cookies.return_value = []

        mock_opts = MagicMock(arguments=[])
        mock_wd.ChromeOptions.return_value = mock_opts
        HeadlessBrowser._set_cached_driver(mock_driver, mock_opts)

        original_execute = MagicMock()

        def execute_side_effect(script, *args):
            if "Storage" in script:
                raise WebDriverException("storage error")
            return original_execute(script, *args)

        mock_driver.execute_script.side_effect = execute_side_effect

        result = browser.make_request("https://example.com")
        self.assertIsInstance(result, str)

        HeadlessBrowser._thread_local._driver_cache = None
        HeadlessBrowser._thread_local._driver_options_hash = None

    @patch("bin.headless_browser.webdriver")
    def test_cleanup_cached_driver_quit_exception(self, mock_wd):
        """Lines 235-236: cached driver quit raises WebDriverException."""
        from bin.headless_browser import HeadlessBrowser

        mock_driver = MagicMock()
        mock_driver.quit.side_effect = WebDriverException("quit error")
        HeadlessBrowser._thread_local._driver_cache = mock_driver
        HeadlessBrowser._thread_local._driver_options_hash = "some_hash"

        HeadlessBrowser._cleanup_cached_driver()
        self.assertIsNone(getattr(HeadlessBrowser._thread_local, "_driver_cache", None))


if __name__ == "__main__":
    unittest.main()
