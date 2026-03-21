#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
from unittest.mock import patch, MagicMock

from bin.crawler import Method


class TestCrawlerMain(unittest.TestCase):
    """bin/crawler.py main() 함수 테스트"""

    @patch("bin.crawler.Crawler")
    def test_main_with_url_arg(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("response body", "", {})

        with patch.object(sys, "argv", ["crawler.py", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        mock_crawler_cls.assert_called_once()
        mock_instance.run.assert_called_once_with("https://example.com", download_file=None)

    @patch("bin.crawler.Crawler")
    def test_main_with_f_option(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "-f", "/tmp/feeddir", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        from pathlib import Path

        self.assertEqual(call_kwargs.kwargs.get("dir_path") or call_kwargs[1].get("dir_path"), Path("/tmp/feeddir"))

    @patch("bin.crawler.Crawler")
    def test_main_with_spider(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--spider", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertEqual(call_kwargs.kwargs.get("method") or call_kwargs[1].get("method"), Method.HEAD)

    @patch("bin.crawler.Crawler")
    def test_main_with_render_js(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--render-js=true", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertTrue(call_kwargs.kwargs.get("render_js") or call_kwargs[1].get("render_js"))

    @patch("bin.crawler.Crawler")
    def test_main_with_verify_ssl_false(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--verify-ssl=false", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertFalse(call_kwargs.kwargs.get("verify_ssl", True) if "verify_ssl" in call_kwargs.kwargs else call_kwargs[1].get("verify_ssl", True))

    @patch("bin.crawler.Crawler")
    def test_main_with_header(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--header=X-Custom: myvalue", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        self.assertEqual(headers["X-Custom"], "myvalue")

    @patch("bin.crawler.Crawler")
    def test_main_with_timeout_and_retry(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--timeout=30", "--retry=3", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertEqual(call_kwargs.kwargs.get("timeout") or call_kwargs[1].get("timeout"), 30)
        self.assertEqual(call_kwargs.kwargs.get("num_retries") or call_kwargs[1].get("num_retries"), 3)

    @patch("bin.crawler.Crawler")
    def test_main_with_encoding(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--encoding=cp949", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertEqual(call_kwargs.kwargs.get("encoding") or call_kwargs[1].get("encoding"), "cp949")

    @patch("bin.crawler.Crawler")
    def test_main_with_download(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main
        from pathlib import Path

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--download=output.html", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        mock_instance.run.assert_called_once_with("https://example.com", download_file=Path("output.html"))

    @patch("bin.crawler.Crawler")
    def test_main_with_user_agent_and_referer(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--user-agent=TestBot", "--referer=http://ref.com", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        self.assertEqual(headers["User-Agent"], "TestBot")
        self.assertEqual(headers["Referer"], "http://ref.com")

    def test_main_no_args(self) -> None:
        from bin.crawler import main

        with patch.object(sys, "argv", ["crawler.py"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, -1)

    def test_main_h_option(self) -> None:
        from bin.crawler import main

        with patch.object(sys, "argv", ["crawler.py", "-h"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)

    @patch("bin.crawler.Crawler")
    def test_main_with_copy_images_from_canvas(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--copy-images-from-canvas=true", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertTrue(call_kwargs.kwargs.get("copy_images_from_canvas") or call_kwargs[1].get("copy_images_from_canvas"))

    @patch("bin.crawler.Crawler")
    def test_main_with_simulate_scrolling(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--simulate-scrolling=true", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertTrue(call_kwargs.kwargs.get("simulate_scrolling") or call_kwargs[1].get("simulate_scrolling"))

    @patch("bin.crawler.Crawler")
    def test_main_with_disable_headless(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--disable-headless=true", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertTrue(call_kwargs.kwargs.get("disable_headless") or call_kwargs[1].get("disable_headless"))

    @patch("bin.crawler.Crawler")
    def test_main_with_blob_to_dataurl(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("ok", "", {})

        with patch.object(sys, "argv", ["crawler.py", "--blob-to-dataurl=true", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)
        call_kwargs = mock_crawler_cls.call_args
        self.assertTrue(call_kwargs.kwargs.get("blob_to_dataurl") or call_kwargs[1].get("blob_to_dataurl"))

    @patch("bin.crawler.Crawler")
    def test_main_error_response(self, mock_crawler_cls: MagicMock) -> None:
        from bin.crawler import main

        mock_instance = mock_crawler_cls.return_value
        mock_instance.run.return_value = ("", "connection error", {})

        with patch.object(sys, "argv", ["crawler.py", "https://example.com"]):
            result = main()

        self.assertEqual(result, 0)

    def test_main_invalid_option(self) -> None:
        from bin.crawler import main

        with patch.object(sys, "argv", ["crawler.py", "--invalid-option", "https://example.com"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, -1)


if __name__ == "__main__":
    unittest.main()
