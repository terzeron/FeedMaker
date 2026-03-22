#!/usr/bin/env python
# -*- coding: utf-8 -*-


import io
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from dotenv import dotenv_values

from bin.feed_maker_util import Env
import utils.download_merge_split
from utils.download_merge_split import crop_image_file, ThresholdOptions, ImageTypeOptions, ProcessOptions
from unittest.mock import PropertyMock
from utils.download_merge_split import (
    get_image_dimensions,
    crop_image_files,
    split_image_file,
    progressive_merge_and_split,
    create_merged_chunks,
    _fix_cross_batch_boundaries,
    _convert_jpeg_to_webp,
    _save_merged_chunk,
    _output_all_final_split_files,
    print_image_files,
    print_cached_image_file,
    print_statistics,
    download_image_and_read_metadata,
    JPEG_SIZE_LIMIT,
)


class TestDownloadMergeSplit(unittest.TestCase):
    def setUp(self) -> None:
        # patcher 등록 (모든 외부 의존성 mock)
        self.patcher_argv = patch("sys.argv")
        self.patcher_environ = patch.dict("os.environ", {}, clear=False)
        self.patcher_stdin = patch("sys.stdin")
        self.patcher_stdout = patch("sys.stdout")
        self.patcher_makedirs = patch("os.makedirs")
        self.patcher_copyfile = patch("shutil.copyfile")
        self.patcher_remove = patch("os.remove")
        self.patcher_exists = patch("os.path.exists", return_value=True)
        self.patcher_getsize = patch("os.path.getsize", return_value=1024)
        self.patcher_requests_get = patch("requests.get")
        self.patcher_image_open = patch("PIL.Image.open")
        self.patcher_crawler_run = patch("bin.crawler.Crawler.run", return_value=(True, None, None))
        self.patcher_convert_image_format = patch("utils.image_downloader.ImageDownloader.convert_image_format", return_value=Path("dummy_path"))
        self.patcher_download_image = patch("utils.image_downloader.ImageDownloader.download_image", return_value=(Path("dummy_path"), "dummy_url"))
        self.patcher_is_file = patch.object(Path, "is_file", return_value=True)
        self.patcher_is_dir = patch.object(Path, "is_dir", return_value=True)
        self.patcher_suffix = patch.object(Path, "suffix", ".jpeg")
        self.patcher_exec_cmd = patch("bin.feed_maker_util.Process.exec_cmd", return_value=("mock_result", None))
        mock_config_instance = MagicMock()
        mock_config_instance.get_extraction_configs.return_value = {"user_agent": "", "encoding": "utf-8", "render_js": False, "num_retries": 1, "verify_ssl": True, "headers": {}, "timeout": 60}
        self.patcher_config = patch("utils.download_merge_split.Config", return_value=mock_config_instance)

        self.mock_argv = self.patcher_argv.start()
        self.mock_environ = self.patcher_environ.start()
        self.mock_stdin = self.patcher_stdin.start()
        self.mock_stdout = self.patcher_stdout.start()
        self.mock_makedirs = self.patcher_makedirs.start()
        self.mock_copyfile = self.patcher_copyfile.start()
        self.mock_remove = self.patcher_remove.start()
        self.mock_exists = self.patcher_exists.start()
        self.mock_getsize = self.patcher_getsize.start()
        self.mock_requests_get = self.patcher_requests_get.start()
        self.mock_image_open = self.patcher_image_open.start()
        self.mock_crawler_run = self.patcher_crawler_run.start()
        self.mock_convert_image_format = self.patcher_convert_image_format.start()
        self.mock_download_image = self.patcher_download_image.start()
        self.mock_is_file = self.patcher_is_file.start()
        self.mock_is_dir = self.patcher_is_dir.start()
        self.mock_suffix = self.patcher_suffix.start()
        self.mock_exec_cmd = self.patcher_exec_cmd.start()
        self.mock_config = self.patcher_config.start()

        page_url = "https://comic.naver.com/webtoon/detail.nhn?titleId=602910&no=197"
        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        self.fake_argv = ["download_merge_split.py", "-f", work_dir, "-m", "-b", "100", "-n", "4", "-c", "fuzzy", page_url]

        # .env의 PATH 환경변수 강제 적용
        env = dotenv_values(Path(__file__).parent.parent / ".env")
        self.fake_env = {"PATH": f"{Env.get('PATH')}:{env.get('PATH', '')}"}

    def tearDown(self) -> None:
        self.patcher_argv.stop()
        self.patcher_environ.stop()
        self.patcher_stdin.stop()
        self.patcher_stdout.stop()
        self.patcher_makedirs.stop()
        self.patcher_copyfile.stop()
        self.patcher_remove.stop()
        self.patcher_exists.stop()
        self.patcher_getsize.stop()
        self.patcher_requests_get.stop()
        self.patcher_image_open.stop()
        self.patcher_crawler_run.stop()
        self.patcher_convert_image_format.stop()
        self.patcher_download_image.stop()
        self.patcher_is_file.stop()
        self.patcher_is_dir.stop()
        self.patcher_suffix.stop()
        self.patcher_exec_cmd.stop()
        self.patcher_config.stop()

    def test_download_merge_split(self) -> None:
        self.maxDiff = None
        test_input = (
            "<div>\n"
            "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_1.jpg'/>\n"
            "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_2.jpg' width='100%'/>\n"
            "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_3.jpg' width='100%' />\n"
            "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_4.jpg'/>\n"
        )
        url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        expected_output = (
            "<div>\n"
            "<img src='%s/one_second/0163a33_1.1.jpeg'/>\n"
            "<img src='%s/one_second/0163a33_1.2.jpeg'/>\n"
            "<img src='%s/one_second/0163a33_1.3.jpeg'/>\n"
            "<img src='%s/one_second/0163a33_1.4.jpeg'/>\n"
            "<img src='%s/one_second/0163a33_2.1.jpeg' width='100%%'/>\n"
            "<img src='%s/one_second/0163a33_2.2.jpeg' width='100%%'/>\n"
            "<img src='%s/one_second/0163a33_2.3.jpeg' width='100%%'/>\n"
            "<img src='%s/one_second/0163a33_2.4.jpeg' width='100%%'/>\n"
            "<img src='%s/one_second/0163a33_3.1.jpeg' width='100%%'/>\n"
            "<img src='%s/one_second/0163a33_3.2.jpeg' width='100%%'/>\n"
            "<img src='%s/one_second/0163a33_3.3.jpeg' width='100%%'/>\n"
            "<img src='%s/one_second/0163a33_3.4.jpeg' width='100%%'/>\n"
            "<img src='%s/one_second/0163a33_4.1.jpeg'/>\n"
            "<img src='%s/one_second/0163a33_4.2.jpeg'/>\n"
            "<img src='%s/one_second/0163a33_4.3.jpeg'/>\n"
            "<img src='%s/one_second/0163a33_4.4.jpeg'/>\n"
        ) % ((url_prefix,) * 16)

        statistics_comment = (
            "<!-- Image Processing Statistics -->\n"
            "<!-- Original Images: 4 files -->\n"
            "<!-- Original Total Area: 0px², Total Height: 0px -->\n"
            "<!-- Original Max Width: 0px, Avg Width: 0px -->\n"
            "<!-- Processed Images: 0 files -->\n"
            "<!-- Processed Total Area: 0px², Total Height: 0px -->\n"
            "<!-- Processed Max Width: 0px, Avg Width: 0px -->\n"
            "<!-- Note: Height/Area increase is expected due to cross-batch boundary merging for seamless transitions -->\n"
        )
        expected_output += statistics_comment

        with (
            patch("sys.argv", self.fake_argv),
            patch.dict("os.environ", self.fake_env, clear=False),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
            patch("os.makedirs"),
            patch("shutil.copyfile"),
            patch("os.remove"),
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
            patch("utils.image_downloader.ImageDownloader.convert_image_format", return_value=Path("dummy_path")),
            patch("utils.image_downloader.ImageDownloader.download_image") as mock_download_image,
            patch("utils.download_merge_split.get_image_dimensions", return_value=(0, 0)),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "glob", return_value=[]),
            patch.object(Path, "suffix", ".jpeg"),
            patch("bin.feed_maker_util.Process.exec_cmd", return_value=("mock_result", None)),
            patch("utils.download_merge_split.progressive_merge_and_split") as mock_progressive_merge_split,
        ):
            # Mock download_image to return valid paths
            mock_download_image.return_value = (Path("dummy_path"), "dummy_url")

            # Mock progressive_merge_and_split to produce expected output
            def mock_split_function(*args, **kwargs):
                # Generate the expected split image URLs
                img_url_prefix = kwargs.get("img_url_prefix", "https://terzeron.com/xml/img/one_second")
                for chunk in range(1, 5):  # 4 chunks
                    for split in range(1, 5):  # 4 splits each
                        if chunk in [2, 3]:  # chunks 2 and 3 have width attribute
                            print(f"<img src='{img_url_prefix}/0163a33_{chunk}.{split}.jpeg' width='100%'/>")
                        else:
                            print(f"<img src='{img_url_prefix}/0163a33_{chunk}.{split}.jpeg'/>")

            mock_progressive_merge_split.side_effect = mock_split_function

            utils.download_merge_split.main()
            actual_output = mock_stdout.getvalue()
            self.assertEqual(actual_output.strip(), expected_output.strip())

    def test_statistics_validation(self) -> None:
        """Test that statistics are properly included in output"""
        self.maxDiff = None
        test_input = "<div>\n<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_1.jpg'/>\n<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_2.jpg'/>\n"

        # Enable stats for this test
        test_env = self.fake_env.copy()

        with (
            patch("sys.argv", self.fake_argv),
            patch.dict("os.environ", test_env, clear=False),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
            patch("os.makedirs"),
            patch("shutil.copyfile"),
            patch("os.remove"),
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
            patch("utils.image_downloader.ImageDownloader.convert_image_format", return_value=Path("dummy_path")),
            patch("utils.image_downloader.ImageDownloader.download_image") as mock_download_image,
            patch("utils.download_merge_split.get_image_dimensions", return_value=(0, 0)),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "glob", return_value=[]),
            patch.object(Path, "suffix", ".jpeg"),
            patch("bin.feed_maker_util.Process.exec_cmd", return_value=("mock_result", None)),
            patch("utils.download_merge_split.progressive_merge_and_split") as mock_progressive_merge_split,
        ):
            # Mock download_image to return valid paths
            mock_download_image.return_value = (Path("dummy_path"), "dummy_url")

            # Mock progressive_merge_and_split to produce expected output
            def mock_split_function(*args, **kwargs):
                # Generate some test split image URLs
                print("<img src='https://test.com/img/test_1.1.jpeg'/>")
                print("<img src='https://test.com/img/test_1.2.jpeg'/>")
                print("<img src='https://test.com/img/test_2.1.jpeg'/>")
                print("<img src='https://test.com/img/test_2.2.jpeg'/>")

            mock_progressive_merge_split.side_effect = mock_split_function

            utils.download_merge_split.main()
            actual_output = mock_stdout.getvalue()

            # Check for statistics in output - basic validation
            self.assertIn("<!-- Image Processing Statistics -->", actual_output)
            self.assertIn("<!-- Original Images:", actual_output)
            self.assertIn("<!-- Processed Images:", actual_output)
            self.assertIn("<!-- Original Total Area:", actual_output)
            self.assertIn("<!-- Processed Total Area:", actual_output)
            # Area Change is only shown when original area > 0
            # self.assertIn("<!-- Area Change:", actual_output)
            self.assertIn("cross-batch boundary merging", actual_output)

            # Verify statistics structure is correct
            lines = actual_output.split("\n")
            statistics_started = False
            for line in lines:
                if "<!-- Image Processing Statistics -->" in line:
                    statistics_started = True
                if statistics_started and "<!-- Original Images:" in line:
                    # Check that the original images count is a number
                    import re

                    match = re.search(r"<!-- Original Images: (\d+) files -->", line)
                    self.assertIsNotNone(match, "Original images count should be a number")
                    original_count = int(match.group(1))
                    self.assertGreaterEqual(original_count, 0, "Original images count should be >= 0")

                if statistics_started and "<!-- Processed Images:" in line:
                    # Check that the processed images count is a number
                    match = re.search(r"<!-- Processed Images: (\d+) files -->", line)
                    self.assertIsNotNone(match, "Processed images count should be a number")
                    processed_count = int(match.group(1))
                    self.assertGreaterEqual(processed_count, 0, "Processed images count should be >= 0")

    def test_statistics_function_directly(self) -> None:
        """Test the statistics function directly with mock data"""
        from pathlib import Path
        import io
        from unittest.mock import patch

        # Create mock image files
        mock_original_images = [Path("/mock/img1.jpeg"), Path("/mock/img2.jpeg")]

        mock_page_url = "https://test.com/page"
        mock_feed_img_dir = Path("/mock/feed_img_dir")

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, patch("utils.download_merge_split.get_image_dimensions") as mock_get_dimensions, patch("pathlib.Path.glob") as mock_glob, patch("pathlib.Path.exists", return_value=True):
            # Mock image dimensions
            mock_get_dimensions.side_effect = [
                (800, 1200),  # Original image 1: 800x1200
                (800, 1000),  # Original image 2: 800x1000
                (800, 600),  # Split image 1: 800x600
                (800, 700),  # Split image 2: 800x700
            ]

            # Mock glob to return split image files
            mock_split_files = [Path("/mock/hash_1.1.jpeg"), Path("/mock/hash_1.2.jpeg")]
            mock_glob.return_value = mock_split_files

            # Call the statistics function directly
            utils.download_merge_split.print_statistics(mock_original_images, mock_page_url, mock_feed_img_dir)

            output = mock_stdout.getvalue()

            # Verify basic statistics structure
            self.assertIn("<!-- Image Processing Statistics -->", output)
            self.assertIn("<!-- Original Images: 2 files -->", output)
            self.assertIn("<!-- Processed Images: 2 files -->", output)
            self.assertIn("<!-- Original Total Area: 1,760,000px²", output)  # (800*1200) + (800*1000)
            self.assertIn("<!-- Processed Total Area: 1,040,000px²", output)  # (800*600) + (800*700)
            self.assertIn("<!-- Area Change: -40.9%", output)  # Expected reduction
            self.assertIn("cross-batch boundary merging", output)

    def test_download_image_and_read_metadata(self):
        """Test parsing HTML and downloading images."""
        from bin.crawler import Crawler

        test_html = "<p>Some text</p>\n<img src='http://test.com/img1.jpg'/>\n<img src='/img2.png' width='50%'/>\n<img src='data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='/>\n<span>More text</span>"
        page_url = "http://test.com/page.html"
        feed_dir_path = Path("/fake/dir")
        feed_img_dir_path = Path("/fake/img_dir")
        crawler = Crawler(dir_path=feed_dir_path)

        # Mock what download_image returns
        self.mock_download_image.side_effect = [(Path("/fake/img_dir/img1.jpg"), "http://test.com/img1.jpg"), (Path("/fake/img_dir/img2.png"), "http://test.com/img2.png"), (Path("/fake/img_dir/data_img.gif"), "data:image/gif;base64,...")]

        with patch("sys.stdin", new=io.StringIO(test_html)):
            img_files, img_urls, normal_html, img_widths = utils.download_merge_split.download_image_and_read_metadata(feed_dir_path, crawler, feed_img_dir_path, page_url)

        # Assertions
        self.assertEqual(len(img_files), 3)
        self.assertEqual(img_files[0], Path("/fake/img_dir/img1.jpg"))
        self.assertEqual(img_files[1], Path("/fake/img_dir/img2.png"))

        self.assertEqual(len(img_urls), 3)
        self.assertEqual(img_urls[0], "http://test.com/img1.jpg")
        # Check if relative URL was correctly concatenated
        self.assertEqual(img_urls[1], "http://test.com/img2.png")
        self.assertTrue(img_urls[2].startswith("data:image"))

        self.assertEqual(len(normal_html), 2)
        self.assertEqual(normal_html[0], "<p>Some text</p>")
        self.assertEqual(normal_html[1], "<span>More text</span>")

        self.assertEqual(len(img_widths), 3)
        self.assertEqual(img_widths[0], "")
        self.assertEqual(img_widths[1], "width='50%'")
        self.assertEqual(img_widths[2], "")

    def test_progressive_merge_and_split_logic(self):
        """Test the orchestration logic of progressive_merge_and_split."""
        # Common setup
        feed_dir_path = Path("/fake/dir")
        img_file_list = [Path("/fake/img1.jpg"), Path("/fake/img2.jpg")]
        page_url = "http://test.com/page"
        feed_img_dir_path = Path("/fake/img_dir")
        img_url_prefix = "http://test.com/prefix"

        threshold_options = ThresholdOptions(bandwidth=0, diff_threshold=0, size_threshold=0, acceptable_diff_of_color_value=0, num_units=0)
        image_type_options = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
        process_options = ProcessOptions(do_innercrop=False, do_only_merge=True)

        # Mock the functions called by the orchestrator
        with (
            patch("utils.download_merge_split.create_merged_chunks") as mock_create_chunks,
            patch("utils.download_merge_split.crop_image_file") as mock_crop,
            patch("utils.download_merge_split.split_image_file") as mock_split,
            patch("utils.download_merge_split._fix_cross_batch_boundaries") as mock_fix,
            patch("utils.download_merge_split._output_all_final_split_files") as mock_output_files,
            patch("builtins.print") as mock_print,
        ):
            # Let create_merged_chunks return some dummy data
            mock_chunk_path1 = Path("/fake/chunk1.jpeg")
            mock_chunk_path2 = Path("/fake/chunk2.jpeg")
            mock_create_chunks.return_value = [(mock_chunk_path1, "width='100%'"), (mock_chunk_path2, "")]

            # --- Scenario 2.1: Test do_only_merge=True ---
            mock_create_chunks.reset_mock()
            mock_split.reset_mock()
            mock_print.reset_mock()

            utils.download_merge_split.progressive_merge_and_split(feed_dir_path=feed_dir_path, img_file_list=img_file_list, page_url=page_url, feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix, threshold_options=threshold_options, image_type_options=image_type_options, process_options=process_options)
            mock_split.assert_not_called()
            self.assertIn("width='100%'", mock_print.call_args_list[0].args[0])
            self.assertNotIn("width=", mock_print.call_args_list[1].args[0])

            # --- Scenario 3.1: Test do_innercrop=True ---
            mock_create_chunks.reset_mock()
            mock_crop.reset_mock()
            mock_split.return_value = True  # Ensure split is "successful"
            # process_options에서 do_innercrop=True로 설정
            innercrop_options = ProcessOptions(do_innercrop=True, do_only_merge=True)
            utils.download_merge_split.progressive_merge_and_split(
                feed_dir_path=feed_dir_path, img_file_list=img_file_list, page_url=page_url, feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix, threshold_options=threshold_options, image_type_options=image_type_options, process_options=innercrop_options
            )
            self.assertEqual(mock_crop.call_count, 2)
            mock_crop.assert_any_call(feed_dir_path, mock_chunk_path1)
            mock_crop.assert_any_call(feed_dir_path, mock_chunk_path2)

            # --- Scenario 2.2: Standard split operation ---
            mock_fix.reset_mock()
            mock_output_files.reset_mock()
            mock_split.reset_mock()

            process_options = ProcessOptions(do_innercrop=False, do_only_merge=False)
            utils.download_merge_split.progressive_merge_and_split(feed_dir_path=feed_dir_path, img_file_list=img_file_list, page_url=page_url, feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix, threshold_options=threshold_options, image_type_options=image_type_options, process_options=process_options)
            self.assertEqual(mock_split.call_count, 2)
            mock_fix.assert_called_once()
            mock_output_files.assert_called_once()

    def test_download_failure_handling(self):
        """Scenario 4: Test that the script handles image download failures gracefully."""
        from bin.crawler import Crawler

        test_html = "<img src='http://test.com/img1.jpg'/>\n<img src='http://test.com/failed.jpg'/>\n<img src='http://test.com/img3.jpg'/>"
        page_url = "http://test.com/page.html"
        feed_dir_path = Path("/fake/dir")
        feed_img_dir_path = Path("/fake/img_dir")
        crawler = Crawler(dir_path=feed_dir_path)

        # Mock download_image to simulate a failure for the second image
        self.mock_download_image.side_effect = [
            (Path("/fake/img_dir/img1.jpg"), "http://test.com/img1.jpg"),
            (None, "http://test.com/failed.jpg"),  # The failure
            (Path("/fake/img_dir/img3.jpg"), "http://test.com/img3.jpg"),
        ]

        with patch("sys.stdin", new=io.StringIO(test_html)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            img_files, _, _, _ = utils.download_merge_split.download_image_and_read_metadata(feed_dir_path, crawler, feed_img_dir_path, page_url)

            output = mock_stdout.getvalue()

            # Assert that only successful downloads are in the list
            self.assertEqual(len(img_files), 2)
            self.assertIn(Path("/fake/img_dir/img1.jpg"), img_files)
            self.assertNotIn(None, img_files)
            self.assertIn(Path("/fake/img_dir/img3.jpg"), img_files)

            # Assert that an error message was printed for the failed download
            self.assertIn("<img src='http://test.com/failed.jpg' alt='original image'/>", output)

    def test_main_no_merge_with_flip_option(self):
        """Scenario 3.2: Test main function with -l (flip) and no-merge options."""
        page_url = "https://comic.naver.com/webtoon/detail.nhn?titleId=602910&no=197"
        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        # argv without -m but with -l
        fake_argv_flip = ["download_merge_split.py", "-f", work_dir, "-l", page_url]
        test_input = "<img src='http://test.com/img1.jpg'/>"

        with (
            patch("sys.argv", fake_argv_flip),
            patch.dict("os.environ", self.fake_env, clear=False),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO),
            patch("utils.download_merge_split.split_image_file", return_value=True),
            patch("utils.download_merge_split.get_image_dimensions", return_value=(100, 100)),
            patch("utils.download_merge_split.print_image_files") as mock_print_files,
        ):
            utils.download_merge_split.main()

            # Assert that print_image_files was called with the flip option enabled
            mock_print_files.assert_called_once()
            # Check the keyword arguments of the call
            _, called_kwargs = mock_print_files.call_args
            self.assertTrue(called_kwargs.get("do_flip_right_to_left"))


class TestGetImageDimensions(unittest.TestCase):
    """get_image_dimensions: success and all exception paths"""

    def test_success(self):
        mock_img = MagicMock()
        mock_img.size = (800, 600)
        mock_img.__enter__ = MagicMock(return_value=mock_img)
        mock_img.__exit__ = MagicMock(return_value=False)

        with patch("utils.download_merge_split.Image.open", return_value=mock_img):
            w, h = get_image_dimensions(Path("/fake/img.jpg"))
        self.assertEqual((w, h), (800, 600))

    def test_os_error(self):
        with patch("utils.download_merge_split.Image.open", side_effect=OSError("bad")):
            self.assertEqual(get_image_dimensions(Path("/fake/img.jpg")), (0, 0))

    def test_io_error(self):
        with patch("utils.download_merge_split.Image.open", side_effect=IOError("bad")):
            self.assertEqual(get_image_dimensions(Path("/fake/img.jpg")), (0, 0))

    def test_type_error(self):
        with patch("utils.download_merge_split.Image.open", side_effect=TypeError("bad")):
            self.assertEqual(get_image_dimensions(Path("/fake/img.jpg")), (0, 0))

    def test_value_error(self):
        with patch("utils.download_merge_split.Image.open", side_effect=ValueError("bad")):
            self.assertEqual(get_image_dimensions(Path("/fake/img.jpg")), (0, 0))

    def test_runtime_error(self):
        with patch("utils.download_merge_split.Image.open", side_effect=RuntimeError("bad")):
            self.assertEqual(get_image_dimensions(Path("/fake/img.jpg")), (0, 0))


class TestCropImageFileExtended(unittest.TestCase):
    """crop_image_file: success and command failure"""

    def test_success_replaces_file(self):
        with tempfile.TemporaryDirectory() as td:
            feed_dir = Path(td)
            img = feed_dir / "test.png"
            img.write_text("original")
            temp = img.with_suffix(".png.temp")

            def fake_exec(cmd, dir_path):
                temp.write_text("cropped")
                return "", ""

            with patch("utils.download_merge_split.Process.exec_cmd", side_effect=fake_exec):
                crop_image_file(feed_dir, img)

            self.assertEqual(img.read_text(), "cropped")
            self.assertFalse(temp.exists())

    def test_command_failure(self):
        with tempfile.TemporaryDirectory() as td:
            feed_dir = Path(td)
            img = feed_dir / "test.png"
            img.write_text("original")

            with patch("utils.download_merge_split.Process.exec_cmd", return_value=("", "error")):
                crop_image_file(feed_dir, img)

            self.assertEqual(img.read_text(), "original")


class TestCropImageFiles(unittest.TestCase):
    """crop_image_files: iterates over num_units and calls crop_image_file"""

    def test_crops_multiple_files(self):
        feed_dir = Path("/fake/feed")
        feed_img_dir = Path("/fake/img")
        img_url = "http://test.com/img.jpg"
        num_units = 3

        with patch("utils.download_merge_split.FileManager.get_cache_file_path") as mock_get_path, patch("utils.download_merge_split.crop_image_file") as mock_crop, patch.object(Path, "is_file", return_value=True):
            mock_get_path.side_effect = [Path(f"/fake/img/img_{i}.jpg") for i in range(1, 4)]
            crop_image_files(feed_dir, num_units, feed_img_dir, img_url)

        self.assertEqual(mock_crop.call_count, 3)

    def test_skips_missing_files(self):
        feed_dir = Path("/fake/feed")
        feed_img_dir = Path("/fake/img")
        img_url = "http://test.com/img.jpg"

        with patch("utils.download_merge_split.FileManager.get_cache_file_path", return_value=Path("/fake/missing.jpg")), patch("utils.download_merge_split.crop_image_file") as mock_crop, patch.object(Path, "is_file", return_value=False):
            crop_image_files(feed_dir, 2, feed_img_dir, img_url)

        mock_crop.assert_not_called()


class TestSplitImageFile(unittest.TestCase):
    """split_image_file: success and command failure"""

    def _make_options(self):
        threshold = ThresholdOptions(bandwidth=10, diff_threshold=0.05, size_threshold=0, acceptable_diff_of_color_value=1, num_units=25)
        image_type = ImageTypeOptions(bgcolor_option="-c fuzzy", orientation_option="", wider_scan_option="")
        return threshold, image_type

    def test_success(self):
        t, it = self._make_options()
        with patch("utils.download_merge_split.Process.exec_cmd", return_value=("ok", None)):
            result = split_image_file(feed_dir_path=Path("/fake"), img_file_path=Path("/fake/img.jpg"), threshold_options=t, image_type_options=it)
        self.assertTrue(result)

    def test_failure(self):
        t, it = self._make_options()
        with patch("utils.download_merge_split.Process.exec_cmd", return_value=("", "split error")):
            result = split_image_file(feed_dir_path=Path("/fake"), img_file_path=Path("/fake/img.jpg"), threshold_options=t, image_type_options=it)
        self.assertFalse(result)


class TestConvertJpegToWebp(unittest.TestCase):
    """_convert_jpeg_to_webp: success, non-jpeg, failure"""

    def test_success_rgb(self):
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "test.jpeg"
            PILImage.new("RGB", (10, 10), "red").save(src, format="JPEG")
            result = _convert_jpeg_to_webp(src, quality=75)
            self.assertIsNotNone(result)
            self.assertEqual(result.suffix, ".webp")
            self.assertTrue(result.exists())
            self.assertFalse(src.exists())

    def test_success_rgba_converts_to_rgb(self):
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "test.jpeg"
            PILImage.new("RGB", (10, 10), "red").save(src, format="JPEG")

            # Mock Image.open to return RGBA image
            mock_img = MagicMock()
            mock_img.mode = "RGBA"
            mock_img.convert.return_value = mock_img
            mock_img.__enter__ = MagicMock(return_value=mock_img)
            mock_img.__exit__ = MagicMock(return_value=False)

            with patch("utils.download_merge_split.Image.open", return_value=mock_img):
                result = _convert_jpeg_to_webp(src, quality=75)

            mock_img.convert.assert_called_once_with("RGB")
            self.assertIsNotNone(result)

    def test_non_jpeg_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "test.png"
            src.write_text("fake")
            result = _convert_jpeg_to_webp(src)
            self.assertIsNone(result)

    def test_nonexistent_file_returns_none(self):
        result = _convert_jpeg_to_webp(Path("/nonexistent/file.jpeg"))
        self.assertIsNone(result)

    def test_exception_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "test.jpeg"
            src.write_text("not a real jpeg")
            result = _convert_jpeg_to_webp(src)
            self.assertIsNone(result)


class TestCreateMergedChunks(unittest.TestCase):
    """create_merged_chunks: normal merging, JPEG size limit, error handling"""

    def _make_mock_img(self, width=100, height=200, mode="RGB"):
        mock_img = MagicMock()
        mock_img.size = (width, height)
        mock_img.mode = mode
        mock_img.copy.return_value = MagicMock()
        mock_img.__enter__ = MagicMock(return_value=mock_img)
        mock_img.__exit__ = MagicMock(return_value=False)
        return mock_img

    def test_single_image(self):
        mock_img = self._make_mock_img(100, 200)
        with patch("utils.download_merge_split.Image.open", return_value=mock_img), patch("utils.download_merge_split._save_merged_chunk", return_value=Path("/fake/chunk_1.jpeg")) as mock_save:
            result = create_merged_chunks([Path("/fake/img1.jpg")], Path("/fake/img_dir"), "http://test.com/page")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], Path("/fake/chunk_1.jpeg"))

    def test_multiple_images_within_limit(self):
        mock_img = self._make_mock_img(100, 200)
        with patch("utils.download_merge_split.Image.open", return_value=mock_img), patch("utils.download_merge_split.Image.new") as mock_new, patch("utils.download_merge_split._save_merged_chunk", return_value=Path("/fake/chunk.jpeg")):
            mock_merged = MagicMock()
            mock_new.return_value = mock_merged
            result = create_merged_chunks([Path("/fake/img1.jpg"), Path("/fake/img2.jpg")], Path("/fake/img_dir"), "http://test.com/page")
        self.assertEqual(len(result), 1)

    def test_jpeg_size_limit_splits_chunks(self):
        """When combined height exceeds JPEG_SIZE_LIMIT, a new chunk is created"""
        img1 = self._make_mock_img(100, JPEG_SIZE_LIMIT - 100)
        img2 = self._make_mock_img(100, 200)

        with patch("utils.download_merge_split.Image.open", side_effect=[img1, img2]), patch("utils.download_merge_split._save_merged_chunk", return_value=Path("/fake/chunk.jpeg")) as mock_save:
            result = create_merged_chunks([Path("/fake/img1.jpg"), Path("/fake/img2.jpg")], Path("/fake/img_dir"), "http://test.com/page")
        self.assertEqual(len(result), 2)
        self.assertEqual(mock_save.call_count, 2)

    def test_image_open_error_skips(self):
        """OSError in Image.open skips that image"""
        good_img = self._make_mock_img(100, 200)
        with patch("utils.download_merge_split.Image.open", side_effect=[OSError("bad"), good_img]), patch("utils.download_merge_split._save_merged_chunk", return_value=Path("/fake/chunk.jpeg")):
            result = create_merged_chunks([Path("/fake/bad.jpg"), Path("/fake/good.jpg")], Path("/fake/img_dir"), "http://test.com/page")
        self.assertEqual(len(result), 1)

    def test_invalid_dimensions_skipped(self):
        """Image with zero dimensions is skipped"""
        mock_img = self._make_mock_img(0, 0)
        with patch("utils.download_merge_split.Image.open", return_value=mock_img), patch("utils.download_merge_split._save_merged_chunk", return_value=Path("/fake/chunk.jpeg")):
            result = create_merged_chunks([Path("/fake/img.jpg")], Path("/fake/img_dir"), "http://test.com/page")
        self.assertEqual(len(result), 0)

    def test_empty_file_list(self):
        result = create_merged_chunks([], Path("/fake"), "http://test.com")
        self.assertEqual(result, [])

    def test_width_attr_propagation(self):
        """Width attributes from img_width_list propagate to chunks"""
        mock_img = self._make_mock_img(100, 200)
        with patch("utils.download_merge_split.Image.open", return_value=mock_img), patch("utils.download_merge_split._save_merged_chunk", return_value=Path("/fake/chunk.jpeg")):
            result = create_merged_chunks([Path("/fake/img1.jpg")], Path("/fake/img_dir"), "http://test.com/page", img_width_list=["width='100%'"])
        self.assertEqual(result[0][1], "width='100%'")

    def test_non_rgb_mode_converts(self):
        """Non-RGB images are converted"""
        mock_img = self._make_mock_img(100, 200, mode="RGBA")
        mock_img.convert.return_value = mock_img
        with patch("utils.download_merge_split.Image.open", return_value=mock_img), patch("utils.download_merge_split._save_merged_chunk", return_value=Path("/fake/chunk.jpeg")):
            create_merged_chunks([Path("/fake/img.png")], Path("/fake"), "http://test.com")
        mock_img.convert.assert_called_with("RGB")

    def test_unexpected_exception_skips(self):
        """Unexpected exceptions (e.g. DecompressionBombError) are caught and skipped"""
        good_img = self._make_mock_img(100, 200)
        with patch("utils.download_merge_split.Image.open", side_effect=[Exception("DecompressionBomb"), good_img]), patch("utils.download_merge_split._save_merged_chunk", return_value=Path("/fake/chunk.jpeg")):
            result = create_merged_chunks([Path("/fake/bomb.jpg"), Path("/fake/good.jpg")], Path("/fake"), "http://test.com")
        self.assertEqual(len(result), 1)


class TestFixCrossBatchBoundaries(unittest.TestCase):
    """_fix_cross_batch_boundaries: merging, skip on exceed, exception handling"""

    def test_merges_cross_batch_boundary(self):
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            hash_prefix = "abc1234"
            page_url = "http://test.com/page"

            f1 = feed_img_dir / f"{hash_prefix}_1.2.jpeg"
            f2 = feed_img_dir / f"{hash_prefix}_2.1.jpeg"
            PILImage.new("RGB", (100, 50), "red").save(f1, format="JPEG")
            PILImage.new("RGB", (100, 60), "blue").save(f2, format="JPEG")

            with patch("utils.download_merge_split.URL.get_short_md5_name", return_value=hash_prefix):
                _fix_cross_batch_boundaries(feed_img_dir, page_url)

            self.assertFalse(f1.exists())
            self.assertTrue(f2.exists())
            with PILImage.open(f2) as merged:
                self.assertEqual(merged.size[1], 110)

    def test_skip_when_exceeds_limit(self):
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            hash_prefix = "abc1234"

            f1 = feed_img_dir / f"{hash_prefix}_1.2.jpeg"
            f2 = feed_img_dir / f"{hash_prefix}_2.1.jpeg"
            PILImage.new("RGB", (100, JPEG_SIZE_LIMIT - 10), "red").save(f1, format="JPEG")
            PILImage.new("RGB", (100, 20), "blue").save(f2, format="JPEG")

            with patch("utils.download_merge_split.URL.get_short_md5_name", return_value=hash_prefix):
                _fix_cross_batch_boundaries(feed_img_dir, "http://test.com")

            self.assertTrue(f1.exists())
            self.assertTrue(f2.exists())

    def test_no_batch_files(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("utils.download_merge_split.URL.get_short_md5_name", return_value="nope"):
                _fix_cross_batch_boundaries(Path(td), "http://test.com")

    def test_single_batch_no_merge(self):
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            hash_prefix = "abc1234"
            f1 = feed_img_dir / f"{hash_prefix}_1.1.jpeg"
            f2 = feed_img_dir / f"{hash_prefix}_1.2.jpeg"
            PILImage.new("RGB", (100, 50), "red").save(f1, format="JPEG")
            PILImage.new("RGB", (100, 50), "blue").save(f2, format="JPEG")

            with patch("utils.download_merge_split.URL.get_short_md5_name", return_value=hash_prefix):
                _fix_cross_batch_boundaries(feed_img_dir, "http://test.com")

            self.assertTrue(f1.exists())
            self.assertTrue(f2.exists())

    def test_exception_in_image_open_caught(self):
        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            hash_prefix = "abc1234"
            f1 = feed_img_dir / f"{hash_prefix}_1.1.jpeg"
            f2 = feed_img_dir / f"{hash_prefix}_2.1.jpeg"
            f1.write_text("not an image")
            f2.write_text("not an image")

            with patch("utils.download_merge_split.URL.get_short_md5_name", return_value=hash_prefix):
                _fix_cross_batch_boundaries(feed_img_dir, "http://test.com")

            self.assertTrue(f1.exists())
            self.assertTrue(f2.exists())


class TestProgressiveMergeAndSplit(unittest.TestCase):
    """progressive_merge_and_split: orchestration logic"""

    def _make_options(self, do_innercrop=False, do_only_merge=False):
        t = ThresholdOptions(bandwidth=10, diff_threshold=0.05, size_threshold=0, acceptable_diff_of_color_value=1, num_units=25)
        it = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
        p = ProcessOptions(do_innercrop=do_innercrop, do_only_merge=do_only_merge)
        return t, it, p

    def test_empty_list_returns_immediately(self):
        t, it, p = self._make_options()
        with patch("utils.download_merge_split._run_normal_merge_split_process") as mock_run:
            progressive_merge_and_split(feed_dir_path=Path("/f"), img_file_list=[], page_url="http://t.com", feed_img_dir_path=Path("/i"), img_url_prefix="http://p", threshold_options=t, image_type_options=it, process_options=p)
        mock_run.assert_not_called()

    def test_do_only_merge_skips_fix_and_output(self):
        t, it, p = self._make_options(do_only_merge=True)
        with patch("utils.download_merge_split._run_normal_merge_split_process") as mock_run, patch("utils.download_merge_split._fix_cross_batch_boundaries") as mock_fix, patch("utils.download_merge_split._output_all_final_split_files") as mock_out:
            progressive_merge_and_split(feed_dir_path=Path("/f"), img_file_list=[Path("/img.jpg")], page_url="http://t.com", feed_img_dir_path=Path("/i"), img_url_prefix="http://p", threshold_options=t, image_type_options=it, process_options=p)
        mock_run.assert_called_once()
        mock_fix.assert_not_called()
        mock_out.assert_not_called()

    def test_split_mode_calls_fix_and_output(self):
        t, it, p = self._make_options(do_only_merge=False)
        with patch("utils.download_merge_split._run_normal_merge_split_process"), patch("utils.download_merge_split._fix_cross_batch_boundaries") as mock_fix, patch("utils.download_merge_split._output_all_final_split_files") as mock_out:
            progressive_merge_and_split(feed_dir_path=Path("/f"), img_file_list=[Path("/img.jpg")], page_url="http://t.com", feed_img_dir_path=Path("/i"), img_url_prefix="http://p", threshold_options=t, image_type_options=it, process_options=p)
        mock_fix.assert_called_once()
        mock_out.assert_called_once()


class TestPrintImageFiles(unittest.TestCase):
    """print_image_files: normal and flipped order"""

    def test_normal_order(self):
        with patch("utils.download_merge_split.FileManager.get_cache_file_path") as mock_path, patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/url") as mock_url, patch.object(Path, "is_file", return_value=True), patch("builtins.print") as mock_print:
            mock_path.return_value = Path("/fake/split.jpg")
            print_image_files(num_units=2, feed_img_dir_path=Path("/fake"), img_url_prefix="http://prefix", img_url="http://img.jpg", img_file_path=None, postfix="1", do_flip_right_to_left=False)
        self.assertEqual(mock_print.call_count, 2)

    def test_flipped_order(self):
        with patch("utils.download_merge_split.FileManager.get_cache_file_path") as mock_path, patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/url"), patch.object(Path, "is_file", return_value=True), patch("builtins.print") as mock_print:
            mock_path.return_value = Path("/fake/split.jpg")
            print_image_files(num_units=3, feed_img_dir_path=Path("/fake"), img_url_prefix="http://prefix", img_url="http://img.jpg", img_file_path=None, postfix="1", do_flip_right_to_left=True)
        self.assertEqual(mock_print.call_count, 3)

    def test_with_img_file_path(self):
        """When img_file_path is provided, uses with_stem for split paths"""
        with patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/url"), patch.object(Path, "is_file", return_value=True), patch("builtins.print") as mock_print:
            img_file = Path("/fake/image.jpeg")
            print_image_files(num_units=2, feed_img_dir_path=Path("/fake"), img_url_prefix="http://prefix", img_url="http://img.jpg", img_file_path=img_file, postfix=None, do_flip_right_to_left=False)
        self.assertEqual(mock_print.call_count, 2)

    def test_missing_split_file_skipped(self):
        with patch("utils.download_merge_split.FileManager.get_cache_file_path", return_value=Path("/fake/split.jpg")), patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/url"), patch.object(Path, "is_file", return_value=False), patch("builtins.print") as mock_print:
            print_image_files(num_units=2, feed_img_dir_path=Path("/fake"), img_url_prefix="http://prefix", img_url="http://img.jpg", img_file_path=None, postfix="1", do_flip_right_to_left=False)
        mock_print.assert_not_called()

    def test_data_image_url_truncated_in_log(self):
        """Data URIs should not cause issues (truncated in logging)"""
        with patch("utils.download_merge_split.FileManager.get_cache_file_path", return_value=Path("/fake/split.jpg")), patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/url"), patch.object(Path, "is_file", return_value=True), patch("builtins.print"):
            print_image_files(num_units=1, feed_img_dir_path=Path("/fake"), img_url_prefix="http://prefix", img_url="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA==", img_file_path=None, postfix="1", do_flip_right_to_left=False)


class TestPrintCachedImageFile(unittest.TestCase):
    """print_cached_image_file: file exists and file missing"""

    def test_file_exists_prints_img_tag(self):
        with (
            patch("utils.download_merge_split.FileManager.get_cache_file_path", return_value=Path("/fake/cache.jpeg")),
            patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/cache.jpeg"),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "suffix", new_callable=PropertyMock, return_value=".jpeg"),
            patch("builtins.print") as mock_print,
        ):
            print_cached_image_file(Path("/fake/img_dir"), "http://prefix", "http://img.jpg", unit_num=1)
        mock_print.assert_called_once()
        self.assertIn("<img src=", mock_print.call_args[0][0])

    def test_file_missing_no_output(self):
        with patch("utils.download_merge_split.FileManager.get_cache_file_path", return_value=Path("/fake/missing.jpeg")), patch.object(Path, "is_file", return_value=False), patch("builtins.print") as mock_print:
            print_cached_image_file(Path("/fake/img_dir"), "http://prefix", "http://img.jpg", unit_num=1)
        mock_print.assert_not_called()


class TestPrintStatistics(unittest.TestCase):
    """print_statistics: various scenarios"""

    def test_basic_statistics_output(self):
        with patch("utils.download_merge_split.get_image_dimensions", return_value=(100, 200)), patch.object(Path, "exists", return_value=True), patch.object(Path, "glob", return_value=[]), patch("utils.download_merge_split.URL.get_short_md5_name", return_value="abc"), patch("builtins.print") as mock_print:
            print_statistics([Path("/fake/img1.jpg")], "http://test.com", Path("/fake/img_dir"))

        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Image Processing Statistics", output)
        self.assertIn("Original Images: 1 files", output)

    def test_no_original_images(self):
        with patch.object(Path, "glob", return_value=[]), patch("utils.download_merge_split.URL.get_short_md5_name", return_value="abc"), patch("builtins.print") as mock_print:
            print_statistics([], "http://test.com", Path("/fake"))

        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Original Images: 0 files", output)
        self.assertNotIn("Area Change", output)

    def test_area_change_printed_when_original_area_positive(self):
        with patch("utils.download_merge_split.get_image_dimensions", return_value=(100, 100)), patch.object(Path, "exists", return_value=True), patch.object(Path, "glob", return_value=[]), patch("utils.download_merge_split.URL.get_short_md5_name", return_value="abc"), patch("builtins.print") as mock_print:
            print_statistics([Path("/fake/img1.jpg")], "http://test.com", Path("/fake"))

        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Area Change", output)

    def test_with_processed_files(self):
        """When processed split files exist, their stats are computed"""
        mock_split = Path("/fake/img_dir/abc_1.1.jpeg")
        with patch("utils.download_merge_split.get_image_dimensions", return_value=(200, 300)), patch.object(Path, "exists", return_value=True), patch.object(Path, "glob", return_value=[mock_split]), patch("utils.download_merge_split.URL.get_short_md5_name", return_value="abc"), patch("builtins.print") as mock_print:
            print_statistics([Path("/fake/orig.jpg")], "http://test.com", Path("/fake/img_dir"))

        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Processed Images: 1 files", output)


class TestDownloadImageAndReadMetadata(unittest.TestCase):
    """download_image_and_read_metadata: various paths"""

    def _setup_common(self):
        self.feed_dir = Path("/fake/feed/test_feed")
        self.feed_img_dir = Path("/fake/img_dir")
        self.page_url = "http://test.com/page"
        self.crawler = MagicMock()

    def test_svg_data_uri_printed_as_svg(self):
        self._setup_common()
        svg_url = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjwvc3ZnPg=="
        html = f"<img src='{svg_url}'/>"

        with patch("utils.download_merge_split.IO.read_stdin_as_line_list", return_value=[html]), patch("utils.download_merge_split.Env.get", return_value="http://img"), patch("utils.download_merge_split.ImageDownloader.download_image", return_value=(None, svg_url)), patch("builtins.print") as mock_print:
            files, urls, html_lines, widths = download_image_and_read_metadata(self.feed_dir, self.crawler, self.feed_img_dir, self.page_url)

        self.assertEqual(len(files), 0)
        printed = [str(c) for c in mock_print.call_args_list]
        svg_printed = any("alt='svg image'" in s for s in printed)
        self.assertTrue(svg_printed)

    def test_download_failure_non_svg(self):
        self._setup_common()
        html = "<img src='http://test.com/broken.jpg'/>"

        with (
            patch("utils.download_merge_split.IO.read_stdin_as_line_list", return_value=[html]),
            patch("utils.download_merge_split.Env.get", return_value="http://img"),
            patch("utils.download_merge_split.ImageDownloader.download_image", return_value=(None, "http://test.com/broken.jpg")),
            patch("builtins.print") as mock_print,
        ):
            files, urls, html_lines, widths = download_image_and_read_metadata(self.feed_dir, self.crawler, self.feed_img_dir, self.page_url)

        self.assertEqual(len(files), 0)
        printed = [str(c) for c in mock_print.call_args_list]
        original_printed = any("alt='original image'" in s for s in printed)
        self.assertTrue(original_printed)

    def test_successful_download(self):
        self._setup_common()
        html = "<img src='http://test.com/img.jpg'/>"
        cache_path = Path("/fake/img_dir/cached.jpeg")

        with (
            patch("utils.download_merge_split.IO.read_stdin_as_line_list", return_value=[html]),
            patch("utils.download_merge_split.Env.get", return_value="http://img"),
            patch("utils.download_merge_split.ImageDownloader.download_image", return_value=(cache_path, "http://test.com/img.jpg")),
            patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/test_feed/cached"),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "suffix", new_callable=PropertyMock, return_value=".jpeg"),
            patch("builtins.print"),
        ):
            files, urls, html_lines, widths = download_image_and_read_metadata(self.feed_dir, self.crawler, self.feed_img_dir, self.page_url)

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], cache_path)
        self.assertEqual(urls[0], "http://test.com/img.jpg")

    def test_relative_url_concatenated(self):
        self._setup_common()
        html = "<img src='/relative/img.jpg'/>"
        cache_path = Path("/fake/img_dir/cached.jpeg")

        with (
            patch("utils.download_merge_split.IO.read_stdin_as_line_list", return_value=[html]),
            patch("utils.download_merge_split.Env.get", return_value="http://img"),
            patch("utils.download_merge_split.ImageDownloader.download_image", return_value=(cache_path, "http://test.com/relative/img.jpg")),
            patch("utils.download_merge_split.URL.concatenate_url", return_value="http://test.com/relative/img.jpg") as mock_concat,
            patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/test_feed/cached"),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "suffix", new_callable=PropertyMock, return_value=".jpeg"),
            patch("builtins.print"),
        ):
            files, urls, html_lines, widths = download_image_and_read_metadata(self.feed_dir, self.crawler, self.feed_img_dir, self.page_url)

        mock_concat.assert_called_once()

    def test_pre_and_post_text_printed(self):
        self._setup_common()
        html = "<div>pre text<img src='http://test.com/img.jpg'/>post text</div>"
        cache_path = Path("/fake/img_dir/cached.jpeg")

        with (
            patch("utils.download_merge_split.IO.read_stdin_as_line_list", return_value=[html]),
            patch("utils.download_merge_split.Env.get", return_value="http://img"),
            patch("utils.download_merge_split.ImageDownloader.download_image", return_value=(cache_path, "url")),
            patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://url"),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "suffix", new_callable=PropertyMock, return_value=".jpeg"),
            patch("builtins.print") as mock_print,
        ):
            download_image_and_read_metadata(self.feed_dir, self.crawler, self.feed_img_dir, self.page_url)

        printed_args = [c[0][0] for c in mock_print.call_args_list]
        self.assertTrue(any("pre text" in s for s in printed_args))
        self.assertTrue(any("post text" in s for s in printed_args))

    def test_br_tags_filtered_from_normal_html(self):
        self._setup_common()
        lines = ["<br>", "</br>", "<p>keep this</p>"]

        with patch("utils.download_merge_split.IO.read_stdin_as_line_list", return_value=lines), patch("utils.download_merge_split.Env.get", return_value="http://img"), patch("builtins.print"):
            _, _, html_lines, _ = download_image_and_read_metadata(self.feed_dir, self.crawler, self.feed_img_dir, self.page_url)

        self.assertIn("<p>keep this</p>", html_lines)

    def test_width_attribute_captured(self):
        self._setup_common()
        html = "<img src='http://test.com/img.jpg' width='80%'/>"
        cache_path = Path("/fake/img_dir/cached.jpeg")

        with (
            patch("utils.download_merge_split.IO.read_stdin_as_line_list", return_value=[html]),
            patch("utils.download_merge_split.Env.get", return_value="http://img"),
            patch("utils.download_merge_split.ImageDownloader.download_image", return_value=(cache_path, "url")),
            patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://url"),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "suffix", new_callable=PropertyMock, return_value=".jpeg"),
            patch("builtins.print"),
        ):
            _, _, _, widths = download_image_and_read_metadata(self.feed_dir, self.crawler, self.feed_img_dir, self.page_url)

        self.assertEqual(len(widths), 1)
        self.assertIn("width='80%'", widths[0])


class TestSaveMergedChunk(unittest.TestCase):
    """_save_merged_chunk: saves image with correct path"""

    def test_saves_and_returns_path(self):
        mock_img = MagicMock()
        expected_path = Path("/fake/img_dir/hash_1.jpeg")

        with patch("utils.download_merge_split.FileManager.get_cache_file_path", return_value=expected_path):
            result = _save_merged_chunk(mock_img, Path("/fake/img_dir"), "http://test.com", 1)

        mock_img.save.assert_called_once_with(expected_path, format="JPEG", quality=75)
        self.assertEqual(result, expected_path)


class TestOutputAllFinalSplitFiles(unittest.TestCase):
    """_output_all_final_split_files: conversion and output"""

    def test_webp_conversion_success(self):
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            hash_prefix = "abc1234"

            f1 = feed_img_dir / f"{hash_prefix}_1.1.jpeg"
            PILImage.new("RGB", (10, 10), "red").save(f1, format="JPEG")

            with patch("utils.download_merge_split.URL.get_short_md5_name", return_value=hash_prefix), patch("utils.download_merge_split.FileManager.get_cache_url", return_value=f"http://img/{hash_prefix}_1.1"), patch("builtins.print") as mock_print:
                _output_all_final_split_files(feed_img_dir, "http://test.com", "http://img")

            printed = mock_print.call_args_list[0][0][0]
            self.assertIn(".webp", printed)

    def test_webp_conversion_failure_falls_back_to_jpeg(self):
        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            hash_prefix = "abc1234"

            f1 = feed_img_dir / f"{hash_prefix}_1.1.jpeg"
            f1.write_text("not a real jpeg")

            with patch("utils.download_merge_split.URL.get_short_md5_name", return_value=hash_prefix), patch("utils.download_merge_split.FileManager.get_cache_url", return_value=f"http://img/{hash_prefix}_1.1"), patch("builtins.print") as mock_print:
                _output_all_final_split_files(feed_img_dir, "http://test.com", "http://img")

            printed = mock_print.call_args_list[0][0][0]
            self.assertIn(".jpeg", printed)

    def test_sorted_output_order(self):
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            hash_prefix = "abc1234"

            for batch, split in [(2, 1), (1, 2), (1, 1)]:
                f = feed_img_dir / f"{hash_prefix}_{batch}.{split}.jpeg"
                PILImage.new("RGB", (10, 10), "red").save(f, format="JPEG")

            printed_order = []
            with patch("utils.download_merge_split.URL.get_short_md5_name", return_value=hash_prefix), patch("utils.download_merge_split.FileManager.get_cache_url", side_effect=lambda *a, **kw: f"http://img/{hash_prefix}_{kw.get('postfix', '')}"), patch("builtins.print", side_effect=lambda s: printed_order.append(s)):
                _output_all_final_split_files(feed_img_dir, "http://test.com", "http://img")

            self.assertEqual(len(printed_order), 3)
            self.assertIn("1.1", printed_order[0])
            self.assertIn("1.2", printed_order[1])
            self.assertIn("2.1", printed_order[2])


class TestRunNormalMergeSplitProcess(unittest.TestCase):
    """_run_normal_merge_split_process: chunk processing with do_only_merge and split"""

    def test_do_only_merge_prints_img_tags(self):
        from utils.download_merge_split import _run_normal_merge_split_process

        chunk_path = MagicMock()
        chunk_path.exists.return_value = True

        t = ThresholdOptions(bandwidth=10, diff_threshold=0.05, size_threshold=0, acceptable_diff_of_color_value=1, num_units=25)
        it = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
        p = ProcessOptions(do_innercrop=False, do_only_merge=True)

        with patch("utils.download_merge_split.create_merged_chunks", return_value=[(chunk_path, "width='100%'")]), patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/chunk_1"), patch("builtins.print") as mock_print:
            _run_normal_merge_split_process([Path("/fake/img.jpg")], "http://test.com", Path("/fake"), Path("/fake/img"), "http://img", t, it, p)

        mock_print.assert_called_once()
        self.assertIn("width='100%'", mock_print.call_args[0][0])

    def test_do_only_merge_no_width_attr(self):
        from utils.download_merge_split import _run_normal_merge_split_process

        chunk_path = MagicMock()
        chunk_path.exists.return_value = True

        t = ThresholdOptions(bandwidth=10, diff_threshold=0.05, size_threshold=0, acceptable_diff_of_color_value=1, num_units=25)
        it = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
        p = ProcessOptions(do_innercrop=False, do_only_merge=True)

        with patch("utils.download_merge_split.create_merged_chunks", return_value=[(chunk_path, "")]), patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/chunk_1"), patch("builtins.print") as mock_print:
            _run_normal_merge_split_process([Path("/fake/img.jpg")], "http://test.com", Path("/fake"), Path("/fake/img"), "http://img", t, it, p)

        printed = mock_print.call_args[0][0]
        self.assertNotIn("width=", printed)
        self.assertIn(".jpeg'/>", printed)

    def test_split_mode_calls_split(self):
        from utils.download_merge_split import _run_normal_merge_split_process

        chunk_path = MagicMock()
        chunk_path.exists.return_value = True

        t = ThresholdOptions(bandwidth=10, diff_threshold=0.05, size_threshold=0, acceptable_diff_of_color_value=1, num_units=25)
        it = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
        p = ProcessOptions(do_innercrop=False, do_only_merge=False)

        with patch("utils.download_merge_split.create_merged_chunks", return_value=[(chunk_path, "")]), patch("utils.download_merge_split.split_image_file", return_value=True) as mock_split:
            _run_normal_merge_split_process([Path("/fake/img.jpg")], "http://test.com", Path("/fake"), Path("/fake/img"), "http://img", t, it, p)

        mock_split.assert_called_once()

    def test_innercrop_called_when_enabled(self):
        from utils.download_merge_split import _run_normal_merge_split_process

        chunk_path = MagicMock()
        chunk_path.exists.return_value = True

        t = ThresholdOptions(bandwidth=10, diff_threshold=0.05, size_threshold=0, acceptable_diff_of_color_value=1, num_units=25)
        it = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
        p = ProcessOptions(do_innercrop=True, do_only_merge=True)

        with patch("utils.download_merge_split.create_merged_chunks", return_value=[(chunk_path, "")]), patch("utils.download_merge_split.crop_image_file") as mock_crop, patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/chunk"), patch("builtins.print"):
            _run_normal_merge_split_process([Path("/fake/img.jpg")], "http://test.com", Path("/fake"), Path("/fake/img"), "http://img", t, it, p)

        mock_crop.assert_called_once()

    def test_chunk_cleanup_after_processing(self):
        from utils.download_merge_split import _run_normal_merge_split_process

        chunk_path = MagicMock()
        chunk_path.exists.return_value = True

        t = ThresholdOptions(bandwidth=10, diff_threshold=0.05, size_threshold=0, acceptable_diff_of_color_value=1, num_units=25)
        it = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
        p = ProcessOptions(do_innercrop=False, do_only_merge=True)

        with patch("utils.download_merge_split.create_merged_chunks", return_value=[(chunk_path, "")]), patch("utils.download_merge_split.FileManager.get_cache_url", return_value="http://img/chunk"), patch("builtins.print"):
            _run_normal_merge_split_process([Path("/fake/img.jpg")], "http://test.com", Path("/fake"), Path("/fake/img"), "http://img", t, it, p)

        chunk_path.unlink.assert_called_once()


# ────────────────────────────────────────────────────────
# From test_remaining_gaps.py: download_merge_split main() 테스트
# ────────────────────────────────────────────────────────
class TestDownloadMergeSplitPrintUsage(unittest.TestCase):
    """print_usage: lines 561-575"""

    def test_print_usage(self):
        import io
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
        import io
        from utils.download_merge_split import main
        from bin.feed_maker_util import Env

        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": ""}
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
        import io
        from utils.download_merge_split import main
        from bin.feed_maker_util import Env

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
        import io
        from bin.feed_maker_util import Env

        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": ""}
        mock_dl_meta.return_value = ([], [], [], [])

        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        argv = ["download_merge_split.py", "-f", work_dir, "-v", "-w", "-t", "0.1", "-s", "10", "-a", "5", "-q", "90", "-n", "30", "-b", "15", "https://example.com/page"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO):
            from utils.download_merge_split import main

            ret = main()
            self.assertEqual(ret, 0)

    def test_main_no_args_calls_print_usage(self):
        import io
        from bin.feed_maker_util import Env

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


if __name__ == "__main__":
    unittest.main()


class TestDownloadMergeSplitWebPOutputs(unittest.TestCase):
    def test_convert_jpeg_to_webp_basic(self) -> None:
        from utils.download_merge_split import _convert_jpeg_to_webp
        from PIL import Image
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_dir = Path(td)
            src = tmp_dir / "sample.jpeg"
            # create a small valid JPEG
            img = Image.new("RGB", (10, 10), "white")
            img.save(src, format="JPEG")

            out_path = _convert_jpeg_to_webp(src, quality=75)
            self.assertIsNotNone(out_path)
            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.suffix.lower(), ".webp")
            self.assertFalse(src.exists())

    def test_output_all_final_split_files_converts_and_prints_webp(self) -> None:
        from utils.download_merge_split import _output_all_final_split_files
        from bin.feed_maker_util import URL
        from PIL import Image
        import io
        import tempfile

        page_url = "http://example.com/page"
        img_url_prefix = "https://img.example.com/test"
        prefix = URL.get_short_md5_name(page_url)

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            # Prepare two JPEG split files that should be converted and printed as WEBP
            f1 = feed_img_dir / f"{prefix}_1.1.jpeg"
            f2 = feed_img_dir / f"{prefix}_1.2.jpeg"

            img1 = Image.new("RGB", (8, 8), "white")
            img2 = Image.new("RGB", (8, 8), "white")
            img1.save(f1, format="JPEG")
            img2.save(f2, format="JPEG")

            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                _output_all_final_split_files(feed_img_dir, page_url, img_url_prefix)
                output = mock_stdout.getvalue()

            # Expect WEBP outputs only
            self.assertIn(f"<img src='{img_url_prefix}/{prefix}_1.1.webp'/>", output)
            self.assertIn(f"<img src='{img_url_prefix}/{prefix}_1.2.webp'/>", output)

            # Original JPEGs should be removed; WEBP files should exist
            self.assertFalse(f1.exists())
            self.assertFalse(f2.exists())
            self.assertTrue(feed_img_dir.joinpath(f"{prefix}_1.1.webp").exists())
            self.assertTrue(feed_img_dir.joinpath(f"{prefix}_1.2.webp").exists())

    def test_print_statistics_prefers_webp_over_jpeg(self) -> None:
        from utils.download_merge_split import print_statistics
        from bin.feed_maker_util import URL
        from PIL import Image
        import io
        import tempfile

        page_url = "http://example.com/page2"
        prefix = URL.get_short_md5_name(page_url)

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            # Same stem: both JPEG and WEBP exist
            jpeg_path = feed_img_dir / f"{prefix}_1.1.jpeg"
            webp_path = feed_img_dir / f"{prefix}_1.1.webp"

            img = Image.new("RGB", (12, 12), "white")
            img.save(jpeg_path, format="JPEG")
            img.save(webp_path, format="WEBP")

            # Also add another only-WEBP file
            webp_only = feed_img_dir / f"{prefix}_1.2.webp"
            img.save(webp_only, format="WEBP")

            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                # original_images can be empty for this check
                print_statistics([], page_url, feed_img_dir)
                output = mock_stdout.getvalue()

            # Processed Images should count stems uniquely, preferring WEBP over JPEG
            # Here we expect two processed images: 1.1 (webp chosen over jpeg) and 1.2 (webp)
            self.assertIn("<!-- Processed Images: 2 files -->", output)


class TestCropImageFile(unittest.TestCase):
    def test_crop_success_replaces_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            feed_dir = Path(tmpdir)
            img_file = feed_dir / "test.jpg"
            img_file.write_text("original")
            temp_file = img_file.with_suffix(".jpg.temp")

            def fake_exec_cmd(cmd, dir_path):
                # innercrop가 temp 파일을 생성하는 것을 시뮬레이션
                temp_file.write_text("cropped")
                return "", ""

            with patch("utils.download_merge_split.Process.exec_cmd", side_effect=fake_exec_cmd):
                crop_image_file(feed_dir, img_file)

            self.assertEqual(img_file.read_text(), "cropped")
            self.assertFalse(temp_file.exists())

    def test_crop_error_keeps_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            feed_dir = Path(tmpdir)
            img_file = feed_dir / "test.jpg"
            img_file.write_text("original")

            with patch("utils.download_merge_split.Process.exec_cmd", return_value=("", "innercrop failed")):
                crop_image_file(feed_dir, img_file)

            self.assertEqual(img_file.read_text(), "original")

    def test_crop_no_temp_file_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            feed_dir = Path(tmpdir)
            img_file = feed_dir / "test.jpg"
            img_file.write_text("original")

            # innercrop 성공했지만 temp 파일을 생성하지 않은 경우
            with patch("utils.download_merge_split.Process.exec_cmd", return_value=("", "")):
                crop_image_file(feed_dir, img_file)

            self.assertEqual(img_file.read_text(), "original")


class TestBranchCoverage(unittest.TestCase):
    """Additional tests for uncovered branches"""

    def test_convert_jpeg_to_webp_unlink_exception(self) -> None:
        """Line 239-240: exception when unlinking original JPEG after conversion"""
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "sample.jpeg"
            img = PILImage.new("RGB", (10, 10), "red")
            img.save(src, format="JPEG")

            with patch.object(Path, "unlink", side_effect=OSError("permission denied")):
                result = _convert_jpeg_to_webp(src, quality=75)
                # Should still return the webp path despite unlink failure
                self.assertIsNotNone(result)
                self.assertEqual(result.suffix, ".webp")

    def test_fix_cross_batch_boundaries_skip_non_batch_files(self) -> None:
        """Line 262->258: filename parts != 2 should be skipped"""
        from PIL import Image as PILImage
        from bin.feed_maker_util import URL

        page_url = "http://example.com/page"
        prefix = URL.get_short_md5_name(page_url)

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            # Create a file with no dot separator (parts length == 1)
            bad_file = feed_img_dir / f"{prefix}_1.jpeg"
            img = PILImage.new("RGB", (10, 10), "white")
            img.save(bad_file, format="JPEG")

            # Should not crash
            _fix_cross_batch_boundaries(feed_img_dir, page_url)

    def test_fix_cross_batch_boundaries_non_rgb_images(self) -> None:
        """Lines 301, 306: images with non-RGB mode in _fix_cross_batch_boundaries"""
        from PIL import Image as PILImage
        from bin.feed_maker_util import URL

        page_url = "http://example.com/page2"
        prefix = URL.get_short_md5_name(page_url)

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            # Create RGBA images (non-RGB) for two adjacent batches
            f1 = feed_img_dir / f"{prefix}_1.1.jpeg"
            f2 = feed_img_dir / f"{prefix}_2.1.jpeg"
            img1 = PILImage.new("RGBA", (10, 20), (255, 0, 0, 128))
            img2 = PILImage.new("RGBA", (10, 15), (0, 255, 0, 128))
            img1.convert("RGB").save(f1, format="JPEG")
            img2.convert("RGB").save(f2, format="JPEG")

            # Patch Image.open to return RGBA mode images
            original_open = PILImage.open

            def mock_open(path, *args, **kwargs):
                img = original_open(path, *args, **kwargs)
                rgba = img.convert("RGBA")

                class FakeImg:
                    def __init__(self, inner):
                        self._inner = inner

                    def __enter__(self):
                        return self._inner

                    def __exit__(self, *a):
                        self._inner.close()

                return FakeImg(rgba)

            with patch("utils.download_merge_split.Image.open", side_effect=mock_open):
                _fix_cross_batch_boundaries(feed_img_dir, page_url)

    def test_fix_cross_batch_boundaries_exceeds_jpeg_limit(self) -> None:
        """Line 294-296: merged height > JPEG_SIZE_LIMIT should skip"""
        from PIL import Image as PILImage
        from bin.feed_maker_util import URL

        page_url = "http://example.com/tall"
        prefix = URL.get_short_md5_name(page_url)

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            f1 = feed_img_dir / f"{prefix}_1.1.jpeg"
            f2 = feed_img_dir / f"{prefix}_2.1.jpeg"

            # Create very tall images that sum > 32767
            img1 = PILImage.new("RGB", (10, 20000), "white")
            img2 = PILImage.new("RGB", (10, 20000), "white")
            img1.save(f1, format="JPEG")
            img2.save(f2, format="JPEG")

            _fix_cross_batch_boundaries(feed_img_dir, page_url)
            # Both files should still exist (merge was skipped)
            self.assertTrue(f1.exists())
            self.assertTrue(f2.exists())

    def test_output_all_final_split_files_skip_non_batch_files(self) -> None:
        """Line 340->336: filename parts != 2 should be skipped in _output_all_final_split_files"""
        from PIL import Image as PILImage
        from bin.feed_maker_util import URL
        import io

        page_url = "http://example.com/output"
        prefix = URL.get_short_md5_name(page_url)

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            # File with single part (no dot in batch.split)
            bad_file = feed_img_dir / f"{prefix}_1.jpeg"
            img = PILImage.new("RGB", (10, 10), "white")
            img.save(bad_file, format="JPEG")

            with patch("sys.stdout", new_callable=io.StringIO) as out:
                _output_all_final_split_files(feed_img_dir, page_url, "https://img.example.com")
                # Should produce no output since the file doesn't match batch.split pattern
                self.assertEqual(out.getvalue(), "")

    def test_create_merged_chunks_invalid_image_size(self) -> None:
        """Lines 382-384: image with invalid size attribute"""
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            img_file = Path(td) / "test.jpeg"
            img = PILImage.new("RGB", (10, 10), "white")
            img.save(img_file, format="JPEG")

            # Mock Image.open to return an image with invalid size
            mock_img = MagicMock()
            mock_img.__enter__ = MagicMock(return_value=mock_img)
            mock_img.__exit__ = MagicMock(return_value=False)
            mock_img.mode = "RGB"
            mock_img.copy.return_value = mock_img
            mock_img.size = None

            with patch("utils.download_merge_split.Image.open", return_value=mock_img):
                result = create_merged_chunks([img_file], feed_img_dir, "http://example.com/page")
                self.assertEqual(result, [])

    def test_create_merged_chunks_width_attr_mid_chunk(self) -> None:
        """Line 431-432: width_attr assigned when current_chunk_width_attr is empty"""
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            f1 = Path(td) / "img1.jpeg"
            f2 = Path(td) / "img2.jpeg"
            img1 = PILImage.new("RGB", (100, 100), "white")
            img2 = PILImage.new("RGB", (100, 100), "white")
            img1.save(f1, format="JPEG")
            img2.save(f2, format="JPEG")

            result = create_merged_chunks([f1, f2], feed_img_dir, "http://example.com/page", img_width_list=["", "width='100%'"])
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0][1], "width='100%'")

    def test_create_merged_chunks_nonexistent_image(self) -> None:
        """Lines 433-435: non-existent image path raises OSError"""
        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            nonexistent = Path(td) / "nonexistent.jpeg"

            result = create_merged_chunks([nonexistent], feed_img_dir, "http://example.com/page")
            self.assertEqual(result, [])

    def test_run_normal_merge_split_split_fails(self) -> None:
        """Line 215->220: split_image_file returns False"""
        from PIL import Image as PILImage
        from utils.download_merge_split import _run_normal_merge_split_process
        import io

        with tempfile.TemporaryDirectory() as td:
            feed_dir = Path(td)
            feed_img_dir = Path(td) / "img"
            feed_img_dir.mkdir()

            img_file = Path(td) / "test.jpeg"
            img = PILImage.new("RGB", (100, 100), "white")
            img.save(img_file, format="JPEG")

            threshold_opts = ThresholdOptions(bandwidth=10, diff_threshold=0.05, size_threshold=0, acceptable_diff_of_color_value=1, num_units=4)
            image_type_opts = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
            process_opts = ProcessOptions(do_innercrop=False, do_only_merge=False)

            with patch("utils.download_merge_split.split_image_file", return_value=False), patch("sys.stdout", new_callable=io.StringIO):
                _run_normal_merge_split_process([img_file], "http://example.com/page", feed_dir, feed_img_dir, "https://img.example.com", threshold_opts, image_type_opts, process_opts)

    def test_progressive_merge_and_split_do_only_merge(self) -> None:
        """Lines 205-212: do_only_merge=True flag"""
        from PIL import Image as PILImage
        import io

        with tempfile.TemporaryDirectory() as td:
            feed_dir = Path(td)
            feed_img_dir = Path(td) / "img"
            feed_img_dir.mkdir()

            img_file = Path(td) / "test.jpeg"
            img = PILImage.new("RGB", (100, 100), "white")
            img.save(img_file, format="JPEG")

            threshold_opts = ThresholdOptions(bandwidth=10, diff_threshold=0.05, size_threshold=0, acceptable_diff_of_color_value=1, num_units=4)
            image_type_opts = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
            process_opts = ProcessOptions(do_innercrop=False, do_only_merge=True)

            with patch("sys.stdout", new_callable=io.StringIO) as out:
                progressive_merge_and_split(feed_dir_path=feed_dir, img_file_list=[img_file], page_url="http://example.com/page", feed_img_dir_path=feed_img_dir, img_url_prefix="https://img.example.com", threshold_options=threshold_opts, image_type_options=image_type_opts, process_options=process_opts)
                output = out.getvalue()
                self.assertIn(".jpeg'/>", output)

    def test_progressive_merge_and_split_do_only_merge_with_width(self) -> None:
        """Lines 209-210: do_only_merge=True with width attribute"""
        from PIL import Image as PILImage
        import io

        with tempfile.TemporaryDirectory() as td:
            feed_dir = Path(td)
            feed_img_dir = Path(td) / "img"
            feed_img_dir.mkdir()

            img_file = Path(td) / "test.jpeg"
            img = PILImage.new("RGB", (100, 100), "white")
            img.save(img_file, format="JPEG")

            threshold_opts = ThresholdOptions(bandwidth=10, diff_threshold=0.05, size_threshold=0, acceptable_diff_of_color_value=1, num_units=4)
            image_type_opts = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
            process_opts = ProcessOptions(do_innercrop=False, do_only_merge=True)

            with patch("sys.stdout", new_callable=io.StringIO) as out:
                progressive_merge_and_split(
                    feed_dir_path=feed_dir, img_file_list=[img_file], page_url="http://example.com/page", feed_img_dir_path=feed_img_dir, img_url_prefix="https://img.example.com", threshold_options=threshold_opts, image_type_options=image_type_opts, process_options=process_opts, img_width_list=["width='100%'"]
                )
                output = out.getvalue()
                self.assertIn("width='100%'", output)

    @patch("utils.download_merge_split.Config")
    @patch("utils.download_merge_split.download_image_and_read_metadata")
    @patch("utils.download_merge_split.split_image_file", return_value=False)
    @patch("utils.download_merge_split.print_cached_image_file")
    @patch("utils.download_merge_split.print_statistics")
    @patch("utils.download_merge_split.Crawler")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    def test_main_split_only_failure_path(self, _is_dir, _mkdir, _crawler, mock_stats, mock_cached, mock_split, mock_dl_meta, mock_config):
        """Line 678: split_image_file returns False -> print_cached_image_file"""
        import io
        from utils.download_merge_split import main
        from bin.feed_maker_util import Env

        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": ""}
        img_path = Path("/tmp/fake.jpg")
        mock_dl_meta.return_value = ([img_path], ["https://example.com/img.jpg"], [], [""])

        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        argv = ["download_merge_split.py", "-f", work_dir, "https://example.com/page"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO):
            ret = main()
            self.assertEqual(ret, 0)
            mock_cached.assert_called_once()

    @patch("utils.download_merge_split.Config")
    @patch("utils.download_merge_split.download_image_and_read_metadata")
    @patch("utils.download_merge_split.split_image_file", return_value=True)
    @patch("utils.download_merge_split.crop_image_files")
    @patch("utils.download_merge_split.print_image_files")
    @patch("utils.download_merge_split.print_statistics")
    @patch("utils.download_merge_split.Crawler")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    def test_main_split_with_innercrop(self, _is_dir, _mkdir, _crawler, mock_stats, mock_print, mock_crop, mock_split, mock_dl_meta, mock_config):
        """Lines 674-675: split success with do_innercrop"""
        import io
        from utils.download_merge_split import main
        from bin.feed_maker_util import Env

        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": ""}
        img_path = Path("/tmp/fake.jpg")
        mock_dl_meta.return_value = ([img_path], ["https://example.com/img.jpg"], [], [""])

        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        argv = ["download_merge_split.py", "-f", work_dir, "-i", "https://example.com/page"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO):
            ret = main()
            self.assertEqual(ret, 0)
            mock_crop.assert_called_once()

    def test_main_h_option(self):
        """Lines 625-626: -h option calls print_usage and exits"""
        argv = ["download_merge_split.py", "-h"]
        with patch("sys.argv", argv), self.assertRaises(SystemExit):
            from utils.download_merge_split import main

            main()

    @patch("utils.download_merge_split.Config")
    @patch("utils.download_merge_split.download_image_and_read_metadata")
    @patch("utils.download_merge_split.progressive_merge_and_split")
    @patch("utils.download_merge_split.print_statistics")
    @patch("utils.download_merge_split.Crawler")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    def test_main_only_merge_option(self, _is_dir, _mkdir, _crawler, mock_stats, mock_pms, mock_dl_meta, mock_config):
        """Lines 627-628: --only-merge option"""
        import io
        from utils.download_merge_split import main
        from bin.feed_maker_util import Env

        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": ""}
        img_path = Path("/tmp/fake.jpg")
        mock_dl_meta.return_value = ([img_path], ["https://example.com/img.jpg"], [], [""])

        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        argv = ["download_merge_split.py", "-f", work_dir, "-m", "--only-merge=true", "https://example.com/page"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO):
            ret = main()
            self.assertEqual(ret, 0)
            call_kwargs = mock_pms.call_args
            self.assertTrue(call_kwargs.kwargs["process_options"].do_only_merge)

    @patch("utils.download_merge_split.Config")
    @patch("utils.download_merge_split.download_image_and_read_metadata")
    @patch("utils.download_merge_split.progressive_merge_and_split")
    @patch("utils.download_merge_split.print_statistics")
    @patch("utils.download_merge_split.Crawler")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    def test_main_i_option(self, _is_dir, _mkdir, _crawler, mock_stats, mock_pms, mock_dl_meta, mock_config):
        """Line 606: -i option sets do_innercrop"""
        import io
        from utils.download_merge_split import main
        from bin.feed_maker_util import Env

        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": ""}
        img_path = Path("/tmp/fake.jpg")
        mock_dl_meta.return_value = ([img_path], ["https://example.com/img.jpg"], [], [""])

        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        argv = ["download_merge_split.py", "-f", work_dir, "-m", "-i", "https://example.com/page"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO):
            ret = main()
            self.assertEqual(ret, 0)
            call_kwargs = mock_pms.call_args
            self.assertTrue(call_kwargs.kwargs["process_options"].do_innercrop)

    def test_print_statistics_nonexistent_processed_file(self) -> None:
        """Line 533->532: file in chosen_files that doesn't exist"""
        from PIL import Image as PILImage
        from bin.feed_maker_util import URL
        import io

        page_url = "http://example.com/stats_nonexist"
        prefix = URL.get_short_md5_name(page_url)

        with tempfile.TemporaryDirectory() as td:
            feed_img_dir = Path(td)
            orig = Path(td) / "orig.jpeg"
            img = PILImage.new("RGB", (100, 50), "white")
            img.save(orig, format="JPEG")

            # Create one real split file and reference one non-existent
            split_file = feed_img_dir / f"{prefix}_1.1.jpeg"
            img.save(split_file, format="JPEG")
            nonexistent = feed_img_dir / f"{prefix}_99.99.jpeg"

            original_glob = Path.glob

            def mock_glob(self_path, pattern):
                if str(self_path) == td:
                    if "*.webp" in pattern:
                        return []
                    if "*.jpeg" in pattern:
                        return [split_file, nonexistent]
                return original_glob(self_path, pattern)

            with patch.object(Path, "glob", mock_glob), patch("sys.stdout", new_callable=io.StringIO) as out:
                print_statistics([orig], page_url, feed_img_dir)
                output = out.getvalue()
                self.assertIn("Image Processing Statistics", output)
                self.assertIn("Processed Images: 1 files", output)

    def test_main_only_merge_false_option(self):
        """Line 627->598: --only-merge=false triggers the branch but sets False"""
        import io
        from utils.download_merge_split import main
        from bin.feed_maker_util import Env

        with (
            patch("utils.download_merge_split.Config") as mc,
            patch("utils.download_merge_split.download_image_and_read_metadata") as mdl,
            patch("utils.download_merge_split.progressive_merge_and_split") as mpms,
            patch("utils.download_merge_split.print_statistics"),
            patch("utils.download_merge_split.Crawler"),
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.is_dir", return_value=True),
        ):
            mc.return_value.get_extraction_configs.return_value = {"user_agent": ""}
            img_path = Path("/tmp/fake.jpg")
            mdl.return_value = ([img_path], ["https://example.com/img.jpg"], [], [""])

            work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
            argv = ["download_merge_split.py", "-f", work_dir, "-m", "--only-merge=false", "https://example.com/page"]
            with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO):
                ret = main()
                self.assertEqual(ret, 0)
                call_kwargs = mpms.call_args
                self.assertFalse(call_kwargs.kwargs["process_options"].do_only_merge)
