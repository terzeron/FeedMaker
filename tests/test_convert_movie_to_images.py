#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import types
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestConvertMovieToImagesCalledProcessError(unittest.TestCase):
    """Branch coverage for subprocess.CalledProcessError (lines 26, 33-34, 36)"""

    @patch("utils.convert_movie_to_images.Env")
    @patch("utils.convert_movie_to_images.URL")
    @patch("utils.convert_movie_to_images.IO")
    @patch("utils.convert_movie_to_images.which")
    @patch("builtins.print")
    def test_rtmpdump_called_process_error(self, mock_print, mock_which, mock_io, mock_url, mock_env):
        """rtmpdump raises CalledProcessError -> line 33-34"""
        mock_env.get.side_effect = lambda k: "/tmp/img" if "IMAGE_DIR" in k else "http://img"
        mock_url.get_short_md5_name.return_value = "abc123"
        mock_io.read_stdin_as_line_list.return_value = ["<video src='http://x?videoPath=rtmp://example.com/stream&y'>"]

        def which_side(name):
            if name == "rtmpdump":
                return "/usr/bin/rtmpdump"
            if name == "extract_images_from_video.sh":
                return "/usr/bin/extract_images_from_video.sh"
            return None

        mock_which.side_effect = which_side

        error = subprocess.CalledProcessError(1, "rtmpdump", stderr=b"rtmp error")

        with patch.object(Path, "is_file", return_value=False), patch("builtins.open", MagicMock()), patch("subprocess.run", side_effect=[error, None]), patch.object(Path, "iterdir", return_value=[]):
            from utils.convert_movie_to_images import main

            result = main()

        self.assertEqual(result, 0)
        calls = [str(c) for c in mock_print.call_args_list]
        self.assertTrue(any("rtmp error" in c for c in calls))

    @patch("utils.convert_movie_to_images.Env")
    @patch("utils.convert_movie_to_images.URL")
    @patch("utils.convert_movie_to_images.IO")
    @patch("utils.convert_movie_to_images.which")
    @patch("builtins.print")
    def test_extract_called_process_error(self, mock_print, mock_which, mock_io, mock_url, mock_env):
        """extract_images_from_video.sh raises CalledProcessError -> line 41-42"""
        mock_env.get.side_effect = lambda k: "/tmp/img" if "IMAGE_DIR" in k else "http://img"
        mock_url.get_short_md5_name.return_value = "abc123"
        mock_io.read_stdin_as_line_list.return_value = ["<video src='http://x?videoPath=rtmp://example.com/stream&y'>"]

        def which_side(name):
            if name == "rtmpdump":
                return None
            if name == "extract_images_from_video.sh":
                return "/usr/bin/extract_images_from_video.sh"
            return None

        mock_which.side_effect = which_side

        extract_error = subprocess.CalledProcessError(1, "extract")

        with patch.object(Path, "is_file", return_value=False), patch("subprocess.run", side_effect=extract_error), patch.object(Path, "iterdir", return_value=[]):
            from utils.convert_movie_to_images import main

            result = main()

        self.assertEqual(result, 0)


class TestConvertMovieToImagesVideoExists(unittest.TestCase):
    """Branch 26->36: video file exists, skip rtmpdump, go to extract"""

    @patch("utils.convert_movie_to_images.Env")
    @patch("utils.convert_movie_to_images.URL")
    @patch("utils.convert_movie_to_images.IO")
    @patch("utils.convert_movie_to_images.which")
    @patch("builtins.print")
    def test_video_file_exists_skips_rtmpdump(self, mock_print, mock_which, mock_io, mock_url, mock_env):
        """Video file already exists -> skip rtmpdump, go to extract (branch 26->36)"""
        mock_env.get.side_effect = lambda k: "/tmp/img" if "IMAGE_DIR" in k else "http://img"
        mock_url.get_short_md5_name.return_value = "abc123"
        mock_io.read_stdin_as_line_list.return_value = ["<video src='http://x?videoPath=rtmp://example.com/stream&y'>"]
        mock_which.return_value = "/usr/bin/extract_images_from_video.sh"

        call_count = 0

        def is_file_side(self_path):
            nonlocal call_count
            call_count += 1
            # 1st call: image_file_path.is_file() -> False (need to process)
            if call_count == 1:
                return False
            # 2nd call: video_file_path.is_file() -> True (video exists)
            return True

        with patch.object(Path, "is_file", is_file_side), patch("subprocess.run"), patch.object(Path, "iterdir", return_value=[]):
            from utils.convert_movie_to_images import main

            result = main()

        self.assertEqual(result, 0)


class TestConvertMovieToImagesMainBlock(unittest.TestCase):
    """__main__ block coverage (lines 51-52)"""

    def test_main_block(self):
        import utils.convert_movie_to_images as mod

        src = Path(mod.__file__).read_text(encoding="utf-8")
        code = compile(src, mod.__file__, "exec")  # noqa: S102
        fake_mod = types.ModuleType("__main__")
        fake_mod.__name__ = "__main__"
        fake_mod.__file__ = mod.__file__

        with patch("sys.argv", ["prog", "http://test"]), patch("sys.stdin", new=StringIO("")):
            with self.assertRaises(SystemExit) as cm:
                eval(code, fake_mod.__dict__)  # noqa: S307
            self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
