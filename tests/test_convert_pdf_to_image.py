#!/usr/bin/env python
# -*- coding: utf-8 -*-

import types
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestConvertPdfToImageLoopBack(unittest.TestCase):
    """Branch 26->25: -f option loop-back (multiple optlist iterations)"""

    @patch("utils.convert_pdf_to_image.convert_from_path")
    @patch("utils.convert_pdf_to_image.FileManager")
    @patch("utils.convert_pdf_to_image.Env")
    @patch("utils.convert_pdf_to_image.header_str", "HEADER")
    @patch("sys.stdin", new=StringIO(""))
    @patch("sys.argv", ["prog", "-f", "/tmp/myfeed", "/tmp/test.pdf"])
    def test_f_option_sets_feed_dir(self, mock_env, mock_fm, mock_convert):
        """Covers branch 26->25 (loop back after -f processing)"""
        mock_env.get.side_effect = lambda k: {"WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/images", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, "")

        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        mock_fm.get_cache_file_path.return_value = Path("/tmp/images/myfeed/cache")
        mock_fm.get_cache_url.return_value = "http://img/myfeed/cache"

        with patch.object(Path, "is_file", return_value=True), patch.object(Path, "mkdir"), patch.object(Path, "unlink"), patch("builtins.print"):
            from utils.convert_pdf_to_image import main

            result = main()

        self.assertEqual(result, 0)


class TestConvertPdfToImageUrlDownload(unittest.TestCase):
    """Branch 33->42: URL download path"""

    @patch("utils.convert_pdf_to_image.convert_from_path")
    @patch("utils.convert_pdf_to_image.FileManager")
    @patch("utils.convert_pdf_to_image.Crawler")
    @patch("utils.convert_pdf_to_image.Env")
    @patch("utils.convert_pdf_to_image.header_str", "HEADER")
    @patch("sys.stdin", new=StringIO(""))
    @patch("sys.argv", ["prog", "http://example.com/test.pdf"])
    def test_http_url_download(self, mock_env, mock_crawler_cls, mock_fm, mock_convert):
        """Covers branch 33->42 (HTTP URL download path)"""
        mock_env.get.side_effect = lambda k: {"WEB_SERVICE_PDF_DIR_PREFIX": "/tmp/pdfs", "WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/images", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, "")

        mock_crawler = MagicMock()
        mock_crawler_cls.return_value = mock_crawler
        mock_crawler.run.return_value = ("ok", None, None)

        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        mock_fm.get_cache_file_path.return_value = Path("/tmp/images/feed/cache")
        mock_fm.get_cache_url.return_value = "http://img/feed/cache"

        with patch.object(Path, "is_file", return_value=False), patch.object(Path, "mkdir"), patch.object(Path, "unlink"), patch("builtins.print"):
            from utils.convert_pdf_to_image import main

            result = main()

        self.assertEqual(result, 0)
        mock_crawler.run.assert_called_once()

    @patch("utils.convert_pdf_to_image.convert_from_path")
    @patch("utils.convert_pdf_to_image.FileManager")
    @patch("utils.convert_pdf_to_image.Crawler")
    @patch("utils.convert_pdf_to_image.Env")
    @patch("utils.convert_pdf_to_image.header_str", "HEADER")
    @patch("sys.stdin", new=StringIO(""))
    @patch("sys.argv", ["prog", "http://example.com/test.pdf"])
    def test_http_download_failure_logs_error(self, mock_env, mock_crawler_cls, mock_fm, mock_convert):
        """Covers branch 39->40: download fails -> LOGGER.error"""
        mock_env.get.side_effect = lambda k: {"WEB_SERVICE_PDF_DIR_PREFIX": "/tmp/pdfs", "WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/images", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, "")

        mock_crawler = MagicMock()
        mock_crawler_cls.return_value = mock_crawler
        mock_crawler.run.return_value = ("", "download failed", None)

        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        mock_fm.get_cache_file_path.return_value = Path("/tmp/images/feed/cache")
        mock_fm.get_cache_url.return_value = "http://img/feed/cache"

        with patch.object(Path, "is_file", return_value=False), patch.object(Path, "mkdir"), patch.object(Path, "unlink"), patch("builtins.print"):
            from utils.convert_pdf_to_image import main

            result = main()

        self.assertEqual(result, 0)

    @patch("utils.convert_pdf_to_image.Env")
    @patch("utils.convert_pdf_to_image.header_str", "HEADER")
    @patch("sys.stdin", new=StringIO(""))
    @patch("sys.argv", ["prog", "not_a_file_nor_url"])
    def test_invalid_input_returns_minus1(self, mock_env):
        """Covers branch 33->42: neither file nor URL -> return -1 (line 42)"""
        with patch.object(Path, "is_file", return_value=False):
            from utils.convert_pdf_to_image import main

            result = main()

        self.assertEqual(result, -1)


class TestConvertPdfToImageMainBlock(unittest.TestCase):
    """__main__ block coverage (lines 68-69)"""

    def test_main_block(self):
        import utils.convert_pdf_to_image as mod

        src = Path(mod.__file__).read_text(encoding="utf-8")
        code = compile(src, mod.__file__, "exec")  # noqa: S102
        fake_mod = types.ModuleType("__main__")
        fake_mod.__name__ = "__main__"
        fake_mod.__file__ = mod.__file__

        with patch("sys.argv", ["prog"]), patch("sys.stdin", new=StringIO("")):
            with self.assertRaises(SystemExit) as cm:
                eval(code, fake_mod.__dict__)  # noqa: S307
            self.assertEqual(cm.exception.code, -1)


if __name__ == "__main__":
    unittest.main()
