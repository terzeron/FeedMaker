#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Coverage gap tests for multiple modules.
Target: close remaining uncovered lines across utils and backend.
"""

import io
import sys
import asyncio
import types
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from bin.feed_maker_util import Env


# ---------------------------------------------------------------------------
# 1. utils/download_image.py
# ---------------------------------------------------------------------------
class TestGetBaseDomain(unittest.TestCase):
    """_get_base_domain: lines 23, 25, 26"""

    def test_two_parts_returns_as_is(self):
        from utils.download_image import _get_base_domain

        self.assertEqual(_get_base_domain("example.com"), "example.com")

    def test_co_kr_suffix_returns_last_three(self):
        from utils.download_image import _get_base_domain

        self.assertEqual(_get_base_domain("www.example.co.kr"), "example.co.kr")

    def test_three_plus_parts_returns_last_two(self):
        from utils.download_image import _get_base_domain

        self.assertEqual(_get_base_domain("sub.example.com"), "example.com")

    def test_single_part(self):
        from utils.download_image import _get_base_domain

        self.assertEqual(_get_base_domain("localhost"), "localhost")


class TestIsSameOrigin(unittest.TestCase):
    """_is_same_origin: lines 32, 34, 37"""

    def test_img_no_scheme_returns_true(self):
        from utils.download_image import _is_same_origin

        self.assertTrue(_is_same_origin("https://example.com/page", "/images/a.jpg"))

    def test_img_data_scheme_returns_true(self):
        from utils.download_image import _is_same_origin

        self.assertTrue(_is_same_origin("https://example.com", "data:image/png;base64,abc"))

    def test_page_no_hostname_returns_true(self):
        from utils.download_image import _is_same_origin

        self.assertTrue(_is_same_origin("/local/path", "https://cdn.example.com/a.png"))


class TestReplaceImgTagError(unittest.TestCase):
    """replace_img_tag: lines 61-63 (OSError path)"""

    @patch("utils.download_image.ImageDownloader.download_image", side_effect=OSError("disk full"))
    def test_download_os_error_returns_error_tag(self, _mock_dl):
        from utils.download_image import replace_img_tag

        mock_match = MagicMock()
        mock_match.group.side_effect = lambda key: {"img_url": "https://example.com/img.jpg", 0: "<img src='https://example.com/img.jpg'/>"}[key]
        crawler = MagicMock()
        result = replace_img_tag(mock_match, crawler=crawler, feed_img_dir_path=Path("/tmp"), quality=75)
        self.assertIn("error occurred", result)


class TestDownloadImageMain(unittest.TestCase):
    """main(): lines 74-75 (-q), 78-79 (bad dir), 98-99 (no img), 110, 115-117 (tail)"""

    def setUp(self):
        self.work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"

    @patch("utils.download_image.Config")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_quality_option(self, mock_dl, _is_dir, _mkdir, mock_config):
        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        mock_dl.return_value = (True, f"{img_url_prefix}/one_second/abc.webp")

        argv = ["download_image.py", "-f", self.work_dir, "-q", "50", "https://example.com/page"]
        stdin_data = "<img src='https://example.com/img.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            import utils.download_image

            ret = utils.download_image.main()
            self.assertEqual(ret, 0)
            self.assertIn("img", out.getvalue())

    @patch("pathlib.Path.is_dir", return_value=False)
    def test_directory_not_found(self, _is_dir):
        argv = ["download_image.py", "-f", "/nonexistent/dir", "https://example.com"]
        with patch("sys.argv", argv):
            import utils.download_image

            ret = utils.download_image.main()
            self.assertEqual(ret, -1)

    @patch("utils.download_image.Config")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    def test_line_without_img_tag(self, _is_dir, _mkdir, mock_config):
        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        argv = ["download_image.py", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<p>Hello world</p>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            import utils.download_image

            ret = utils.download_image.main()
            self.assertEqual(ret, 0)
            self.assertIn("Hello world", out.getvalue())

    @patch("utils.download_image.Config")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_tail_text_after_last_element(self, mock_dl, _is_dir, _mkdir, mock_config):
        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        mock_dl.return_value = (True, f"{img_url_prefix}/one_second/abc.webp")

        argv = ["download_image.py", "-f", self.work_dir, "https://example.com/page"]
        # After img replacement, there will be tail text after last element
        stdin_data = "<img src='https://example.com/img.jpg'/>some tail text"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            import utils.download_image

            ret = utils.download_image.main()
            self.assertEqual(ret, 0)
            output = out.getvalue()
            self.assertIn("tail text", output)


# ---------------------------------------------------------------------------
# 2. utils/convert_movie_to_images.py
# ---------------------------------------------------------------------------
class TestConvertMovieToImages(unittest.TestCase):
    """Lines 33-34, 41-42, 45-46"""

    @patch("utils.convert_movie_to_images.IO.read_stdin_as_line_list")
    @patch("utils.convert_movie_to_images.Env.get")
    @patch("pathlib.Path.is_file")
    @patch("utils.convert_movie_to_images.which")
    def test_rtmpdump_called_process_error(self, mock_which, mock_is_file, mock_env_get, mock_stdin):
        mock_stdin.return_value = ["<video src='http://x?videoPath=rtmp://stream.example.com/live&extra=1'>"]
        mock_env_get.side_effect = lambda key: {"WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/test_imgs", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img.example.com"}[key]
        # image file doesn't exist, video file doesn't exist
        mock_is_file.return_value = False
        # Only rtmpdump is found; extract script is not found
        mock_which.side_effect = lambda name: "/usr/bin/rtmpdump" if name == "rtmpdump" else None

        with (
            patch("sys.argv", ["convert_movie_to_images.py", "http://example.com/movie"]),
            patch("builtins.open", MagicMock()),
            patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "rtmpdump", stderr=b"connection failed")),
            patch("pathlib.Path.iterdir", return_value=iter([])),
            patch("sys.stdout", new_callable=io.StringIO) as out,
        ):
            from utils.convert_movie_to_images import main

            ret = main()
            self.assertEqual(ret, 0)
            self.assertIn("connection failed", out.getvalue())

    @patch("utils.convert_movie_to_images.IO.read_stdin_as_line_list")
    @patch("utils.convert_movie_to_images.Env.get")
    @patch("utils.convert_movie_to_images.which")
    def test_extract_images_called_process_error(self, mock_which, mock_env_get, mock_stdin):
        mock_stdin.return_value = ["<video src='http://x?videoPath=rtmp://stream.example.com/live&extra=1'>"]
        mock_env_get.side_effect = lambda key: {"WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/test_imgs", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img.example.com"}[key]

        def which_side_effect(name):
            if name == "rtmpdump":
                return None
            if name == "extract_images_from_video.sh":
                return "/usr/bin/extract_images_from_video.sh"
            return None

        mock_which.side_effect = which_side_effect

        # image file doesn't exist, but video file exists
        def is_file_side_effect(self_path=None):
            return False

        with (
            patch("sys.argv", ["convert_movie_to_images.py", "http://example.com/movie"]),
            patch("pathlib.Path.is_file", return_value=False),
            patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "extract", stderr=b"")),
            patch("pathlib.Path.iterdir", return_value=iter([])),
            patch("sys.stdout", new_callable=io.StringIO) as out,
        ):
            from utils.convert_movie_to_images import main

            ret = main()
            self.assertEqual(ret, 0)

    @patch("utils.convert_movie_to_images.IO.read_stdin_as_line_list")
    @patch("utils.convert_movie_to_images.Env.get")
    @patch("utils.convert_movie_to_images.which")
    def test_iterdir_matching_image_files(self, mock_which, mock_env_get, mock_stdin):
        mock_stdin.return_value = ["<video src='http://x?videoPath=rtmp://stream.example.com/live&extra=1'>"]
        mock_env_get.side_effect = lambda key: {"WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/test_imgs", "WEB_SERVICE_IMAGE_URL_PREFIX": "http://img.example.com"}[key]
        mock_which.return_value = None

        # Simulate image file already exists
        mock_entry1 = MagicMock()
        mock_entry1.name = "abc1234_0001.jpg"
        mock_entry2 = MagicMock()
        mock_entry2.name = "other_file.txt"

        # Use URL to compute correct id_str
        from bin.feed_maker_util import URL

        id_str = URL.get_short_md5_name("http://example.com/movie")

        mock_entry1.name = f"{id_str}_0001.jpg"

        with patch("sys.argv", ["convert_movie_to_images.py", "http://example.com/movie"]), patch("pathlib.Path.is_file", return_value=True), patch("pathlib.Path.iterdir", return_value=iter([mock_entry1, mock_entry2])), patch("sys.stdout", new_callable=io.StringIO) as out:
            from utils.convert_movie_to_images import main

            ret = main()
            self.assertEqual(ret, 0)
            self.assertIn(f"{id_str}_0001.jpg", out.getvalue())


# ---------------------------------------------------------------------------
# 3. utils/translation.py
# ---------------------------------------------------------------------------
class TestTranslationMain(unittest.TestCase):
    """main(): lines 486-489, 494-497, 499-506, 510"""

    @patch("utils.translation.translate_html")
    def test_main_with_c_option_and_valid_html(self, mock_translate_html):
        mock_translate_html.return_value = ("<p>번역됨</p>", 0)
        argv = ["translation.py", "-c"]
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO("<p>Hello</p>")), patch("sys.stdout", new_callable=io.StringIO) as out:
            from utils.translation import main

            main()
            self.assertIn("번역됨", out.getvalue())
            # verify provider was passed as CLAUDE
            from utils.translation import TranslationProvider

            mock_translate_html.assert_called_once()
            call_kwargs = mock_translate_html.call_args
            self.assertEqual(call_kwargs.kwargs.get("provider") or call_kwargs[1].get("provider"), TranslationProvider.CLAUDE)

    @patch("utils.translation.translate_html")
    def test_main_with_empty_stdin(self, mock_translate_html):
        argv = ["translation.py"]
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO("")):
            from utils.translation import main

            main()
            mock_translate_html.assert_not_called()

    def test_main_with_getopt_error(self):
        argv = ["translation.py", "-x"]  # invalid option
        with patch("sys.argv", argv), self.assertRaises(SystemExit) as ctx:
            from utils.translation import main

            main()
        self.assertEqual(ctx.exception.code, 1)

    @patch("utils.translation.translate_html")
    def test_main_with_t_option(self, mock_translate_html):
        import utils.translation

        mock_translate_html.return_value = ("<p>OK</p>", 0)
        argv = ["translation.py", "-t", "2.5"]
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO("<p>test</p>")), patch("sys.stdout", new_callable=io.StringIO):
            utils.translation.main()
            self.assertEqual(utils.translation._SLEEP_SECONDS, 2.5)
        # restore
        utils.translation._SLEEP_SECONDS = 1

    @patch("utils.translation.translate_html")
    def test_main_with_untranslated(self, mock_translate_html):
        mock_translate_html.return_value = ("<p>partial</p>", 3)
        argv = ["translation.py"]
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO("<p>Hello</p>")), patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as ctx:
                from utils.translation import main

                main()
            self.assertEqual(ctx.exception.code, -1)


# ---------------------------------------------------------------------------
# 4. utils/download_merge_split.py
# ---------------------------------------------------------------------------
class TestDownloadMergeSplitPrintUsage(unittest.TestCase):
    """print_usage: lines 561-575"""

    def test_print_usage(self):
        from utils.download_merge_split import print_usage

        with patch("sys.stdout", new_callable=io.StringIO) as out, self.assertRaises(SystemExit):
            print_usage("test_program")
        output = out.getvalue()
        self.assertIn("Usage:", output)
        self.assertIn("-m: merge", output)

    @patch("utils.download_merge_split.Config")
    @patch("utils.download_merge_split.download_image_and_read_metadata")
    @patch("utils.download_merge_split.Crawler")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    def test_main_no_merge(self, _is_dir, _mkdir, _crawler, mock_dl_meta, mock_config):
        """main() without -m: lines 606+ (split-only path)"""
        from utils.download_merge_split import main

        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": ""}
        # Return empty image list -> early return
        mock_dl_meta.return_value = ([], [], [], [])

        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        argv = ["download_merge_split.py", "-f", work_dir, "https://example.com/page"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO):
            ret = main()
            self.assertEqual(ret, 0)

    @patch("utils.download_merge_split.Config")
    @patch("utils.download_merge_split.download_image_and_read_metadata")
    @patch("utils.download_merge_split.split_image_file", return_value=True)
    @patch("utils.download_merge_split.print_image_files")
    @patch("utils.download_merge_split.print_statistics")
    @patch("utils.download_merge_split.Crawler")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    def test_main_split_only_with_images(self, _is_dir, _mkdir, _crawler, mock_stats, mock_print, mock_split, mock_dl_meta, mock_config):
        """main() split-only path with actual images: lines 669-678"""
        from utils.download_merge_split import main

        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": ""}
        img_path = Path("/tmp/fake_img.jpg")
        mock_dl_meta.return_value = ([img_path], ["https://example.com/img.jpg"], ["<p>hello</p>"], [""])

        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        argv = ["download_merge_split.py", "-f", work_dir, "https://example.com/page"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = main()
            self.assertEqual(ret, 0)
            mock_split.assert_called_once()
            mock_print.assert_called_once()


class TestDownloadMergeSplitMainOptions(unittest.TestCase):
    """main() option parsing: lines 610, 612, 616, 618, 620, 623-628"""

    @patch("utils.download_merge_split.Config")
    @patch("utils.download_merge_split.download_image_and_read_metadata")
    @patch("utils.download_merge_split.Crawler")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    def test_main_various_options(self, _is_dir, _mkdir, _crawler, mock_dl_meta, mock_config):
        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": ""}
        mock_dl_meta.return_value = ([], [], [], [])

        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        argv = [
            "download_merge_split.py",
            "-f",
            work_dir,
            "-v",  # orientation_option (line 610)
            "-w",  # wider_scan_option (line 612)
            "-t",
            "0.1",  # diff_threshold (line 616)
            "-s",
            "10",  # size_threshold (line 618)
            "-a",
            "5",  # acceptable_diff (line 620)
            "-q",
            "90",  # quality (line 623-624)
            "-n",
            "30",  # num_units (line 622)
            "-b",
            "15",  # bandwidth (line 614)
            "https://example.com/page",
        ]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO):
            from utils.download_merge_split import main

            ret = main()
            self.assertEqual(ret, 0)

    def test_main_no_args_calls_print_usage(self):
        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        argv = ["download_merge_split.py", "-f", work_dir]
        with patch("sys.argv", argv), patch("pathlib.Path.is_dir", return_value=True), patch("sys.stdout", new_callable=io.StringIO), self.assertRaises(SystemExit):
            from utils.download_merge_split import main

            main()

    @patch("pathlib.Path.is_dir", return_value=False)
    def test_main_bad_dir(self, _is_dir):
        """lines 634-635: feed_dir_path not a directory"""
        argv = ["download_merge_split.py", "-f", "/nonexistent", "https://example.com"]
        with patch("sys.argv", argv):
            from utils.download_merge_split import main

            ret = main()
            self.assertEqual(ret, -1)


# ---------------------------------------------------------------------------
# 5. backend/main.py
# ---------------------------------------------------------------------------
class TestBackendLogin(unittest.TestCase):
    """Login endpoint: lines 121-132"""

    def test_login_success(self):
        import backend.main as bmain

        with patch.object(bmain, "verify_facebook_token", return_value=True), patch.object(bmain, "Env") as mock_env, patch.object(bmain, "create_session", return_value="session123"), patch.object(bmain, "set_session_cookie"):
            mock_env.get.return_value = "user@example.com"
            request = bmain.LoginRequest(email="user@example.com", name="User", access_token="tok")
            response = asyncio.run(bmain.login(request))
            self.assertEqual(response.status_code, 200)

    def test_login_create_session_exception(self):
        import backend.main as bmain

        with patch.object(bmain, "verify_facebook_token", return_value=True), patch.object(bmain, "Env") as mock_env, patch.object(bmain, "create_session", side_effect=RuntimeError("db error")):
            mock_env.get.return_value = "user@example.com"
            request = bmain.LoginRequest(email="user@example.com", name="User", access_token="tok")
            from fastapi import HTTPException

            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(bmain.login(request))
            self.assertEqual(ctx.exception.status_code, 500)


class TestBackendMiddleware(unittest.TestCase):
    """OPTIONS request: lines 62-63"""

    def test_options_request_passes_through(self):
        import backend.main as bmain

        mock_request = MagicMock()
        mock_request.method = "OPTIONS"

        mock_response = MagicMock()

        async def mock_call_next(req):
            return mock_response

        response = asyncio.run(bmain.auth_middleware(mock_request, mock_call_next))
        self.assertEqual(response, mock_response)


class TestBackendExcepthook(unittest.TestCase):
    """handle_exception: line 85"""

    def test_handle_exception(self):
        import backend.main as bmain

        try:
            raise ValueError("test error")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            # Should not raise
            bmain.handle_exception(exc_type, exc_value, exc_tb)


class TestBackendFailureEndpoints(unittest.TestCase):
    """Lines 305-307, 322-323, 337-338, 351-352, 385-386, 399-400"""

    def _make_failing_manager(self):
        mgr = MagicMock()
        mgr.extract_titles_from_public_feed.return_value = ("FILE_NOT_FOUND", "file not found")
        mgr.get_site_config.return_value = (None, "config error")
        mgr.save_site_config.return_value = (None, "save error")
        mgr.toggle_group.return_value = (None, "toggle error")
        mgr.toggle_feed.return_value = (None, "toggle feed error")
        mgr.run.return_value = (None, "run error")
        return mgr

    def test_extract_titles_failure(self):
        import backend.main as bmain

        mgr = self._make_failing_manager()
        r = asyncio.run(bmain.extract_titles_from_public_feed("f", feed_maker_manager=mgr))
        self.assertEqual(r["status"], "failure")
        self.assertEqual(r["error_code"], "FILE_NOT_FOUND")

    def test_get_site_config_failure(self):
        import backend.main as bmain

        mgr = self._make_failing_manager()
        r = asyncio.run(bmain.get_site_config("g", feed_maker_manager=mgr))
        self.assertEqual(r["status"], "failure")

    def test_save_site_config_failure(self):
        import backend.main as bmain

        bmain.require_admin = lambda _: None
        mgr = self._make_failing_manager()

        async def _json():
            return {}

        req = types.SimpleNamespace(json=_json)
        r = asyncio.run(bmain.save_site_config("g", request=req, feed_maker_manager=mgr))
        self.assertEqual(r["status"], "failure")

    def test_toggle_group_failure(self):
        import backend.main as bmain

        mgr = self._make_failing_manager()
        r = asyncio.run(bmain.toggle_group("g", feed_maker_manager=mgr))
        self.assertEqual(r["status"], "failure")

    def test_toggle_feed_failure(self):
        import backend.main as bmain

        mgr = self._make_failing_manager()
        r = asyncio.run(bmain.toggle_feed("g", "f", feed_maker_manager=mgr))
        self.assertEqual(r["status"], "failure")

    def test_run_feed_failure(self):
        import backend.main as bmain

        bmain.require_admin = lambda _: None
        mgr = self._make_failing_manager()
        req = MagicMock()
        r = bmain.run_feed("g", "f", request=req, feed_maker_manager=mgr)
        self.assertEqual(r["status"], "failure")


# ---------------------------------------------------------------------------
# 6. bin/uploader.py
# ---------------------------------------------------------------------------
class TestUploaderMain(unittest.TestCase):
    """main(): lines 47, 51"""

    @patch("bin.uploader.Uploader.upload", return_value=0)
    def test_main_calls_upload(self, mock_upload):
        from bin.uploader import main

        with patch("sys.argv", ["uploader.py", "feed.xml"]):
            ret = main()
            self.assertEqual(ret, 0)
            mock_upload.assert_called_once()
            call_arg = mock_upload.call_args[0][0]
            self.assertTrue(str(call_arg).endswith("feed.xml"))


# ---------------------------------------------------------------------------
# 7. utils/search_manga_site.py
# ---------------------------------------------------------------------------
class TestSearchMangaSiteMain(unittest.TestCase):
    """main(): lines 634-649, 653"""

    @patch("utils.search_manga_site.SearchManager")
    def test_main_keyword_no_site(self, mock_sm_cls):
        mock_sm = MagicMock()
        mock_sm.search_sites.return_value = "<div>result</div>"
        mock_sm_cls.return_value = mock_sm

        argv = ["search_manga_site.py", "keyword_test"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO) as out:
            from utils.search_manga_site import main

            ret = main()
            self.assertEqual(ret, 0)
            mock_sm.search_sites.assert_called_once_with("", "keyword_test", False)
            self.assertIn("result", out.getvalue())

    @patch("utils.search_manga_site.SearchManager")
    def test_main_with_site_name(self, mock_sm_cls):
        mock_sm = MagicMock()
        mock_sm.search_sites.return_value = "<div>site result</div>"
        mock_sm_cls.return_value = mock_sm

        argv = ["search_manga_site.py", "-s", "funbe", "keyword_test"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO) as out:
            from utils.search_manga_site import main

            ret = main()
            self.assertEqual(ret, 0)
            mock_sm.search_sites.assert_called_once_with("funbe", "keyword_test", False)

    @patch("utils.search_manga_site.SearchManager")
    def test_main_with_torrent_option(self, mock_sm_cls):
        mock_sm = MagicMock()
        mock_sm.search_sites.return_value = ""
        mock_sm_cls.return_value = mock_sm

        argv = ["search_manga_site.py", "-t", "keyword_test"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO):
            from utils.search_manga_site import main

            ret = main()
            self.assertEqual(ret, 0)
            mock_sm.search_sites.assert_called_once_with("", "keyword_test", True)


# ---------------------------------------------------------------------------
# 8. bin/run.py
# ---------------------------------------------------------------------------
class TestRunPrintUsage(unittest.TestCase):
    """print_usage: lines 162-167"""

    def test_print_usage(self):
        from bin.run import print_usage

        with patch("sys.stdout", new_callable=io.StringIO) as out:
            print_usage()
        output = out.getvalue()
        self.assertIn("Usage:", output)
        self.assertIn("-a: make all feeds", output)


class TestRunMainDetermineOptions(unittest.TestCase):
    """determine_options and main entry path"""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    def test_main_single_feed(self, mock_config, mock_runner_cls, mock_pm_cls):
        mock_config.return_value.get_collection_configs.return_value = {"is_completed": False}
        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = True
        mock_runner_cls.return_value = mock_runner
        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        argv = ["run.py"]
        with patch("sys.argv", argv), patch("pathlib.Path.is_dir", return_value=True):
            from bin.run import main

            ret = main()
            self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
