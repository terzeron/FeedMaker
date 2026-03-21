#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for small utility scripts with 0% coverage:
- utils/remove_non_breaking_space.py
- utils/post_process_only_for_images.py
- utils/convert_pdf_to_image.py
- utils/convert_pdf_to_text.py
- utils/convert_movie_to_images.py
- utils/aggregate_titles.py
"""

import io
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path


class TestRemoveNonBreakingSpace(unittest.TestCase):
    """utils/remove_non_breaking_space.py"""

    def _run_script(self, input_lines: list[str]) -> str:
        stdin_data = "".join(input_lines)
        with patch("sys.stdin", io.StringIO(stdin_data)):
            import importlib
            import utils.remove_non_breaking_space as mod

            # Capture stdout
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                importlib.reload(mod)
            return captured.getvalue()

    def test_replaces_nbsp(self) -> None:
        result = self._run_script(["hello\u00a0world\n"])
        self.assertIn("hello world", result)
        self.assertNotIn("\u00a0", result)

    def test_no_nbsp(self) -> None:
        result = self._run_script(["normal text\n"])
        self.assertIn("normal text", result)

    def test_multiple_nbsp(self) -> None:
        result = self._run_script(["a\u00a0b\u00a0c\n"])
        self.assertIn("a b c", result)

    def test_empty_input(self) -> None:
        result = self._run_script([])
        self.assertEqual(result, "")


class TestPostProcessOnlyForImages(unittest.TestCase):
    """utils/post_process_only_for_images.py"""

    def _run_main(self, argv: list[str], stdin_lines: list[str]) -> tuple[str, int]:
        stdin_data = "".join(stdin_lines)
        with patch("sys.argv", argv), patch("sys.stdin", io.StringIO(stdin_data)):
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                from utils.post_process_only_for_images import main

                ret = main()
            return captured.getvalue(), ret

    def test_basic_img_extraction(self) -> None:
        lines = ["<div><img src='http://example.com/1.jpg'></div>\n", "<div><img src='http://example.com/2.jpg'></div>\n"]
        output, ret = self._run_main(["prog"], lines)
        self.assertEqual(ret, 0)
        self.assertIn("img src=", output)

    def test_remove_not_found_images(self) -> None:
        lines = ["<img src='http://example.com/image-not-found.png'>\n", "<img src='http://example.com/good.jpg'>\n"]
        output, ret = self._run_main(["prog", "-r"], lines)
        self.assertNotIn("image-not-found.png", output)
        self.assertIn("good.jpg", output)

    def test_leave_only_unique_images(self) -> None:
        lines = ["<img src='http://example.com/1.jpg'>\n", "<img src='http://example.com/1.jpg'>\n", "<img src='http://example.com/2.jpg'>\n"]
        output, ret = self._run_main(["prog", "-u"], lines)
        self.assertEqual(output.count("1.jpg"), 1)
        self.assertIn("2.jpg", output)

    def test_meta_and_style_preserved(self) -> None:
        lines = ["<meta charset='utf-8'>\n", "<style>body{}</style>\n", "<img src='test.jpg'>\n"]
        output, ret = self._run_main(["prog"], lines)
        self.assertIn("<meta", output)
        self.assertIn("<style", output)

    def test_no_img_tags(self) -> None:
        lines = ["<p>hello</p>\n"]
        output, ret = self._run_main(["prog"], lines)
        self.assertNotIn("img", output)

    def test_both_options(self) -> None:
        lines = ["<img src='http://example.com/1.jpg'>\n", "<img src='http://example.com/1.jpg'>\n", "<img src='http://example.com/image-not-found.png'>\n"]
        output, ret = self._run_main(["prog", "-u", "-r"], lines)
        self.assertEqual(output.count("1.jpg"), 1)
        self.assertNotIn("image-not-found.png", output)


class TestConvertPdfToImage(unittest.TestCase):
    """utils/convert_pdf_to_image.py"""

    @patch("utils.convert_pdf_to_image.convert_from_path")
    @patch("utils.convert_pdf_to_image.FileManager")
    @patch("utils.convert_pdf_to_image.Env.get")
    @patch("utils.convert_pdf_to_image.Crawler")
    def test_local_file(self, mock_crawler_cls, mock_env_get, mock_fm, mock_convert) -> None:
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            pdf_path = f.name
        try:

            def env_side_effect(key, default=""):
                return {
                    "WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/img",
                    "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img",
                    "WEB_SERVICE_PDF_DIR_PREFIX": "/tmp/pdf",
                    "FM_WORK_DIR": "/tmp/work",
                    "WEB_SERVICE_FEED_DIR_PREFIX": "/tmp/feed",
                    "FM_LOG_DIR": "/tmp/logs",
                    "FM_CRAWLER_ALLOW_PRIVATE_IPS": "false",
                    "FM_CRAWLER_ALLOWED_HOSTS": "",
                }.get(key, default)

            mock_env_get.side_effect = env_side_effect

            mock_img = MagicMock()
            mock_convert.return_value = [mock_img]
            mock_fm.get_cache_file_path.return_value = Path("/tmp/img/test/cache")
            mock_fm.get_cache_url.return_value = "http://img/test/cache"

            with patch("sys.argv", ["prog", pdf_path]), patch("sys.stdin", io.StringIO("")), patch("pathlib.Path.mkdir"), patch("pathlib.Path.unlink"), patch("builtins.print") as mock_print:
                from utils.convert_pdf_to_image import main

                ret = main()
            self.assertEqual(ret, 0)
            mock_convert.assert_called_once()
        finally:
            os.unlink(pdf_path)

    @patch("utils.convert_pdf_to_image.Env.get")
    def test_no_args(self, mock_env_get) -> None:
        mock_env_get.return_value = "/tmp"
        with patch("sys.argv", ["prog"]), patch("sys.stdin", io.StringIO("")):
            from utils.convert_pdf_to_image import main

            ret = main()
        self.assertEqual(ret, -1)


class TestConvertPdfToText(unittest.TestCase):
    """utils/convert_pdf_to_text.py"""

    @patch("utils.convert_pdf_to_text.pdftotext.PDF")
    @patch("utils.convert_pdf_to_text.Env.get")
    def test_local_file(self, mock_env_get, mock_pdf_cls) -> None:
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            pdf_path = f.name
        try:
            mock_env_get.return_value = "/tmp"
            mock_pdf_cls.return_value = ["Page 1 text\nMore text"]

            with patch("sys.argv", ["prog", pdf_path]), patch("sys.stdin", io.StringIO("")), patch("pathlib.Path.unlink"), patch("builtins.print") as mock_print:
                from utils.convert_pdf_to_text import main

                ret = main()
            self.assertEqual(ret, 0)
        finally:
            os.unlink(pdf_path)

    @patch("utils.convert_pdf_to_text.Env.get")
    def test_no_args(self, mock_env_get) -> None:
        mock_env_get.return_value = "/tmp"
        with patch("sys.argv", ["prog"]), patch("sys.stdin", io.StringIO("")):
            from utils.convert_pdf_to_text import main

            ret = main()
        self.assertEqual(ret, -1)

    @patch("utils.convert_pdf_to_text.Env.get")
    def test_invalid_arg(self, mock_env_get) -> None:
        mock_env_get.return_value = "/tmp"
        with patch("sys.argv", ["prog", "not_a_file_not_http"]), patch("sys.stdin", io.StringIO("")):
            from utils.convert_pdf_to_text import main

            ret = main()
        self.assertEqual(ret, -1)

    @patch("utils.convert_pdf_to_text.pdftotext.PDF")
    @patch("utils.convert_pdf_to_text.Crawler")
    @patch("utils.convert_pdf_to_text.Env.get")
    def test_http_url(self, mock_env_get, mock_crawler_cls, mock_pdf_cls) -> None:
        mock_env_get.return_value = "/tmp"
        mock_crawler = MagicMock()
        mock_crawler.run.return_value = ("200", "", None)
        mock_crawler_cls.return_value = mock_crawler
        mock_pdf_cls.return_value = ["Page text"]

        with patch("sys.argv", ["prog", "http://example.com/doc.pdf"]), patch("sys.stdin", io.StringIO("")), patch("builtins.open", mock_open(read_data=b"pdf")), patch("pathlib.Path.unlink"), patch("builtins.print"):
            from utils.convert_pdf_to_text import main

            ret = main()
        self.assertEqual(ret, 0)


class TestConvertMovieToImages(unittest.TestCase):
    """utils/convert_movie_to_images.py"""

    @patch("utils.convert_movie_to_images.Env.get")
    @patch("utils.convert_movie_to_images.URL.get_short_md5_name", return_value="abc123")
    @patch("utils.convert_movie_to_images.IO.read_stdin_as_line_list")
    @patch("utils.convert_movie_to_images.which")
    @patch("utils.convert_movie_to_images.subprocess.run")
    def test_main_with_video(self, mock_run, mock_which, mock_stdin, mock_md5, mock_env_get) -> None:
        mock_env_get.side_effect = lambda k, d="": {"WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/img", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, d)
        mock_stdin.return_value = ["<video src='test?videoPath=rtmp://example.com/video&other'>"]
        mock_which.side_effect = lambda x: f"/usr/bin/{x}"

        # Mock Path operations and file open to prevent creating abc123.avi
        with patch("sys.argv", ["prog", "http://example.com/page"]), patch("pathlib.Path.is_file", return_value=False), patch("pathlib.Path.iterdir", return_value=[]), patch("builtins.open", mock_open()), patch("builtins.print"):
            from utils.convert_movie_to_images import main

            ret = main()
        self.assertEqual(ret, 0)

    @patch("utils.convert_movie_to_images.Env.get")
    @patch("utils.convert_movie_to_images.URL.get_short_md5_name", return_value="abc123")
    @patch("utils.convert_movie_to_images.IO.read_stdin_as_line_list")
    def test_main_no_video(self, mock_stdin, mock_md5, mock_env_get) -> None:
        mock_env_get.side_effect = lambda k, d="": {"WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/img", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img"}.get(k, d)
        mock_stdin.return_value = ["<p>no video here</p>"]

        with patch("sys.argv", ["prog", "http://example.com/page"]), patch("builtins.print"):
            from utils.convert_movie_to_images import main

            ret = main()
        self.assertEqual(ret, 0)


class TestAggregateTitles(unittest.TestCase):
    """utils/aggregate_titles.py"""

    def test_extract_clustered_lines_empty(self) -> None:
        from utils.aggregate_titles import _extract_clustered_lines

        result = _extract_clustered_lines(Path("/nonexistent/file"))
        self.assertEqual(result, [])

    def test_extract_clustered_lines_valid(self) -> None:
        import tempfile
        import os
        from utils.aggregate_titles import _extract_clustered_lines

        content = "cluster1\t3\t1\ttitle1\t2\ttitle2\t3\ttitle3\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write(content)
            tmp_path = f.name
        try:
            result = _extract_clustered_lines(Path(tmp_path))
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0], ("1", "title1"))
        finally:
            os.unlink(tmp_path)

    def test_extract_clustered_lines_below_threshold(self) -> None:
        import tempfile
        import os
        from utils.aggregate_titles import _extract_clustered_lines

        content = "cluster1\t2\t1\ttitle1\t2\ttitle2\n"  # count=2 < 3
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write(content)
            tmp_path = f.name
        try:
            result = _extract_clustered_lines(Path(tmp_path))
            self.assertEqual(result, [])
        finally:
            os.unlink(tmp_path)

    def test_extract_clustered_lines_short_fields(self) -> None:
        import tempfile
        import os
        from utils.aggregate_titles import _extract_clustered_lines

        content = "cluster1\t5\n"  # only 2 fields, < 3
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write(content)
            tmp_path = f.name
        try:
            result = _extract_clustered_lines(Path(tmp_path))
            self.assertEqual(result, [])
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
