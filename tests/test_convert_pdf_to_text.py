#!/usr/bin/env python
# -*- coding: utf-8 -*-

import types
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestConvertPdfToTextInvalidInput(unittest.TestCase):
    """Branch 37->38: invalid input (neither file nor URL) -> return -1"""

    @patch("sys.stdin", new=StringIO(""))
    @patch("sys.argv", ["prog", "not_a_file_nor_url"])
    def test_invalid_input_returns_minus1(self):
        """Covers else branch: not a file and not http -> LOGGER.error + return -1"""
        with patch.object(Path, "is_file", return_value=False):
            from utils.convert_pdf_to_text import main

            result = main()

        self.assertEqual(result, -1)


class TestConvertPdfToTextDownloadFailure(unittest.TestCase):
    """Branch 35->36: HTTP URL download failure -> LOGGER.error(error)"""

    @patch("utils.convert_pdf_to_text.pdftotext")
    @patch("utils.convert_pdf_to_text.Crawler")
    @patch("utils.convert_pdf_to_text.Env")
    @patch("sys.stdin", new=StringIO(""))
    @patch("sys.argv", ["prog", "http://example.com/test.pdf"])
    def test_http_download_failure_logs_error(self, mock_env, mock_crawler_cls, mock_pdftotext):
        """Covers branch 35->36: download fails -> LOGGER.error"""
        mock_env.get.side_effect = lambda k: "/tmp/pdfs" if "PDF_DIR" in k else ""

        mock_crawler = MagicMock()
        mock_crawler_cls.return_value = mock_crawler
        mock_crawler.run.return_value = ("", "download failed", None)

        mock_pdf = MagicMock()
        mock_pdf.__iter__ = MagicMock(return_value=iter(["page1 text"]))
        mock_pdftotext.PDF.return_value = mock_pdf

        with patch("builtins.open", MagicMock()), patch("builtins.print"), patch.object(Path, "unlink"):
            from utils.convert_pdf_to_text import main

            result = main()

        self.assertEqual(result, 0)


class TestConvertPdfToTextMainBlock(unittest.TestCase):
    """__main__ block coverage (lines 59-60)"""

    def test_main_block(self):
        import utils.convert_pdf_to_text as mod

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
