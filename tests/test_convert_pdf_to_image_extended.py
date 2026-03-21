#!/usr/bin/env python

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from io import StringIO


class TestConvertPdfToImageMain(unittest.TestCase):
    """main: -f option (26-27), HTTP URL download (33-42), download failure (39-40), line 69"""

    @patch("utils.convert_pdf_to_image.convert_from_path")
    @patch("utils.convert_pdf_to_image.FileManager")
    @patch("utils.convert_pdf_to_image.Env")
    @patch("utils.convert_pdf_to_image.header_str", "HEADER")
    @patch("sys.stdin", new=StringIO(""))
    @patch("sys.argv", ["convert_pdf_to_image.py", "-f", "/tmp/myfeed", "/tmp/test.pdf"])
    def test_f_option_sets_feed_dir_path(self, mock_env, mock_fm, mock_convert) -> None:
        """main with -f option -> line 26-27"""
        mock_env.get.side_effect = lambda k: {"WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/images", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, "")

        with patch.object(Path, "is_file", return_value=True), patch.object(Path, "mkdir"), patch.object(Path, "unlink"), patch("builtins.print"):
            mock_image = MagicMock()
            mock_convert.return_value = [mock_image]
            mock_fm.get_cache_file_path.return_value = Path("/tmp/images/myfeed/cache")
            mock_fm.get_cache_url.return_value = "http://img/myfeed/cache"

            from utils.convert_pdf_to_image import main

            result = main()
            self.assertEqual(result, 0)

    @patch("utils.convert_pdf_to_image.convert_from_path")
    @patch("utils.convert_pdf_to_image.FileManager")
    @patch("utils.convert_pdf_to_image.Crawler")
    @patch("utils.convert_pdf_to_image.Env")
    @patch("utils.convert_pdf_to_image.header_str", "HEADER")
    @patch("sys.stdin", new=StringIO(""))
    @patch("sys.argv", ["convert_pdf_to_image.py", "http://example.com/test.pdf"])
    def test_http_url_download(self, mock_env, mock_crawler_cls, mock_fm, mock_convert) -> None:
        """main with HTTP URL -> line 33-42"""
        mock_env.get.side_effect = lambda k: {"WEB_SERVICE_PDF_DIR_PREFIX": "/tmp/pdfs", "WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/images", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, "")

        mock_crawler = MagicMock()
        mock_crawler_cls.return_value = mock_crawler
        mock_crawler.run.return_value = ("ok", None, None)

        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        mock_fm.get_cache_file_path.return_value = Path("/tmp/images/myfeed/cache")
        mock_fm.get_cache_url.return_value = "http://img/myfeed/cache"

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
    @patch("sys.argv", ["convert_pdf_to_image.py", "http://example.com/test.pdf"])
    def test_http_url_download_failure(self, mock_env, mock_crawler_cls, mock_fm, mock_convert) -> None:
        """main with URL download failure -> line 39-40"""
        mock_env.get.side_effect = lambda k: {"WEB_SERVICE_PDF_DIR_PREFIX": "/tmp/pdfs", "WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/images", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, "")

        mock_crawler = MagicMock()
        mock_crawler_cls.return_value = mock_crawler
        mock_crawler.run.return_value = ("", "download failed", None)

        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        mock_fm.get_cache_file_path.return_value = Path("/tmp/images/myfeed/cache")
        mock_fm.get_cache_url.return_value = "http://img/myfeed/cache"

        with patch.object(Path, "is_file", return_value=False), patch.object(Path, "mkdir"), patch.object(Path, "unlink"), patch("builtins.print"):
            from utils.convert_pdf_to_image import main

            result = main()
            self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
