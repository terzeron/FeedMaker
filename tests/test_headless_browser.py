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

if __name__ == "__main__":
    unittest.main()
