#!/usr/bin/env python
# -*- coding: utf-8 -*-


import io
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from dotenv import dotenv_values

from bin.feed_maker_util import Env
import utils.download_merge_split
from utils.download_merge_split import ThresholdOptions, ImageTypeOptions, ProcessOptions


class TestDownloadMergeSplit(unittest.TestCase):
    def setUp(self) -> None:
        # patcher 등록 (모든 외부 의존성 mock)
        self.patcher_argv = patch('sys.argv')
        self.patcher_environ = patch.dict('os.environ', {}, clear=False)
        self.patcher_stdin = patch('sys.stdin')
        self.patcher_stdout = patch('sys.stdout')
        self.patcher_makedirs = patch('os.makedirs')
        self.patcher_copyfile = patch('shutil.copyfile')
        self.patcher_remove = patch('os.remove')
        self.patcher_exists = patch('os.path.exists', return_value=True)
        self.patcher_getsize = patch('os.path.getsize', return_value=1024)
        self.patcher_requests_get = patch('requests.get')
        self.patcher_image_open = patch('PIL.Image.open')
        self.patcher_crawler_run = patch('bin.crawler.Crawler.run', return_value=(True, None, None))
        self.patcher_convert_image_format = patch('utils.image_downloader.ImageDownloader.convert_image_format', return_value=Path('dummy_path'))
        self.patcher_download_image = patch('utils.image_downloader.ImageDownloader.download_image', return_value=(Path('dummy_path'), 'dummy_url'))
        self.patcher_is_file = patch.object(Path, 'is_file', return_value=True)
        self.patcher_suffix = patch.object(Path, 'suffix', '.jpeg')
        self.patcher_exec_cmd = patch('bin.feed_maker_util.Process.exec_cmd', return_value=("mock_result", None))

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
        self.mock_suffix = self.patcher_suffix.start()
        self.mock_exec_cmd = self.patcher_exec_cmd.start()

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
        self.patcher_suffix.stop()
        self.patcher_exec_cmd.stop()

    def test_download_merge_split(self) -> None:
        self.maxDiff = None
        test_input = ("<div>\n"
                      "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_1.jpg'/>\n"
                      "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_2.jpg' width='100%'/>\n"
                      "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_3.jpg' width='100%' />\n"
                      "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_4.jpg'/>\n")
        url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        expected_output = ("<div>\n"
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
                          "<img src='%s/one_second/0163a33_4.4.jpeg'/>\n") % ((url_prefix,) * 16)

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

        with patch('sys.argv', self.fake_argv), \
             patch.dict('os.environ', self.fake_env, clear=False), \
             patch('sys.stdin', new=io.StringIO(test_input)), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('os.makedirs'), \
             patch('shutil.copyfile'), \
             patch('os.remove'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024), \
             patch('utils.image_downloader.ImageDownloader.convert_image_format', return_value=Path('dummy_path')), \
             patch('utils.image_downloader.ImageDownloader.download_image') as mock_download_image, \
             patch('utils.download_merge_split.get_image_dimensions', return_value=(0, 0)), \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(Path, 'glob', return_value=[]), \
             patch.object(Path, 'suffix', '.jpeg'), \
             patch('bin.feed_maker_util.Process.exec_cmd', return_value=("mock_result", None)), \
             patch('utils.download_merge_split.progressive_merge_and_split') as mock_progressive_merge_split:

            # Mock download_image to return valid paths
            mock_download_image.return_value = (Path('dummy_path'), 'dummy_url')

            # Mock progressive_merge_and_split to produce expected output
            def mock_split_function(*args, **kwargs):
                # Generate the expected split image URLs
                img_url_prefix = kwargs.get('img_url_prefix', 'https://terzeron.com/xml/img/one_second')
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
        test_input = ("<div>\n"
                      "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_1.jpg'/>\n"
                      "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_2.jpg'/>\n")

        # Enable stats for this test
        test_env = self.fake_env.copy()

        with patch('sys.argv', self.fake_argv), \
             patch.dict('os.environ', test_env, clear=False), \
             patch('sys.stdin', new=io.StringIO(test_input)), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('os.makedirs'), \
             patch('shutil.copyfile'), \
             patch('os.remove'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024), \
             patch('utils.image_downloader.ImageDownloader.convert_image_format', return_value=Path('dummy_path')), \
             patch('utils.image_downloader.ImageDownloader.download_image') as mock_download_image, \
             patch('utils.download_merge_split.get_image_dimensions', return_value=(0, 0)), \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(Path, 'glob', return_value=[]), \
             patch.object(Path, 'suffix', '.jpeg'), \
             patch('bin.feed_maker_util.Process.exec_cmd', return_value=("mock_result", None)), \
             patch('utils.download_merge_split.progressive_merge_and_split') as mock_progressive_merge_split:

            # Mock download_image to return valid paths
            mock_download_image.return_value = (Path('dummy_path'), 'dummy_url')

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
            lines = actual_output.split('\n')
            statistics_started = False
            for line in lines:
                if "<!-- Image Processing Statistics -->" in line:
                    statistics_started = True
                if statistics_started and "<!-- Original Images:" in line:
                    # Check that the original images count is a number
                    import re
                    match = re.search(r'<!-- Original Images: (\d+) files -->', line)
                    self.assertIsNotNone(match, "Original images count should be a number")
                    original_count = int(match.group(1))
                    self.assertGreaterEqual(original_count, 0, "Original images count should be >= 0")

                if statistics_started and "<!-- Processed Images:" in line:
                    # Check that the processed images count is a number
                    match = re.search(r'<!-- Processed Images: (\d+) files -->', line)
                    self.assertIsNotNone(match, "Processed images count should be a number")
                    processed_count = int(match.group(1))
                    self.assertGreaterEqual(processed_count, 0, "Processed images count should be >= 0")

    def test_statistics_function_directly(self) -> None:
        """Test the statistics function directly with mock data"""
        from pathlib import Path
        import io
        from unittest.mock import patch

        # Create mock image files
        mock_original_images = [
            Path('/mock/img1.jpeg'),
            Path('/mock/img2.jpeg'),
        ]

        mock_page_url = 'https://test.com/page'
        mock_feed_img_dir = Path('/mock/feed_img_dir')

        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('utils.download_merge_split.get_image_dimensions') as mock_get_dimensions, \
             patch('pathlib.Path.glob') as mock_glob, \
             patch('pathlib.Path.exists', return_value=True):

            # Mock image dimensions
            mock_get_dimensions.side_effect = [
                (800, 1200),  # Original image 1: 800x1200
                (800, 1000),  # Original image 2: 800x1000
                (800, 600),   # Split image 1: 800x600
                (800, 700),   # Split image 2: 800x700
            ]

            # Mock glob to return split image files
            mock_split_files = [
                Path('/mock/hash_1.1.jpeg'),
                Path('/mock/hash_1.2.jpeg'),
            ]
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

        test_html = (
            "<p>Some text</p>\n"
            "<img src='http://test.com/img1.jpg'/>\n"
            "<img src='/img2.png' width='50%'/>\n"
            "<img src='data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='/>\n"
            "<span>More text</span>"
        )
        page_url = "http://test.com/page.html"
        feed_dir_path = Path("/fake/dir")
        feed_img_dir_path = Path("/fake/img_dir")
        crawler = Crawler(dir_path=feed_dir_path)

        # Mock what download_image returns
        self.mock_download_image.side_effect = [
            (Path("/fake/img_dir/img1.jpg"), "http://test.com/img1.jpg"),
            (Path("/fake/img_dir/img2.png"), "http://test.com/img2.png"),
            (Path("/fake/img_dir/data_img.gif"), "data:image/gif;base64,..."),
        ]

        with patch('sys.stdin', new=io.StringIO(test_html)):
            img_files, img_urls, normal_html, img_widths = utils.download_merge_split.download_image_and_read_metadata(
                feed_dir_path, crawler, feed_img_dir_path, page_url
            )

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
        feed_dir_path = Path('/fake/dir')
        img_file_list = [Path('/fake/img1.jpg'), Path('/fake/img2.jpg')]
        page_url = 'http://test.com/page'
        feed_img_dir_path = Path('/fake/img_dir')
        img_url_prefix = 'http://test.com/prefix'

        threshold_options = ThresholdOptions(bandwidth=0, diff_threshold=0, size_threshold=0, acceptable_diff_of_color_value=0, num_units=0)
        image_type_options = ImageTypeOptions(bgcolor_option="", orientation_option="", wider_scan_option="")
        process_options = ProcessOptions(do_innercrop=False, do_only_merge=True)

        # Mock the functions called by the orchestrator
        with patch('utils.download_merge_split.create_merged_chunks') as mock_create_chunks, \
             patch('utils.download_merge_split.crop_image_file') as mock_crop, \
             patch('utils.download_merge_split.split_image_file') as mock_split, \
             patch('utils.download_merge_split._fix_cross_batch_boundaries') as mock_fix, \
             patch('utils.download_merge_split._output_all_final_split_files') as mock_output_files, \
             patch('builtins.print') as mock_print:

            # Let create_merged_chunks return some dummy data
            mock_chunk_path1 = Path('/fake/chunk1.jpeg')
            mock_chunk_path2 = Path('/fake/chunk2.jpeg')
            mock_create_chunks.return_value = [
                (mock_chunk_path1, "width='100%'"),
                (mock_chunk_path2, "")
            ]

            # --- Scenario 2.1: Test do_only_merge=True ---
            mock_create_chunks.reset_mock()
            mock_split.reset_mock()
            mock_print.reset_mock()

            utils.download_merge_split.progressive_merge_and_split(
                feed_dir_path=feed_dir_path, img_file_list=img_file_list, page_url=page_url,
                feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix,
                threshold_options=threshold_options, image_type_options=image_type_options, process_options=process_options)
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
                feed_dir_path=feed_dir_path, img_file_list=img_file_list, page_url=page_url,
                feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix,
                threshold_options=threshold_options, image_type_options=image_type_options, process_options=innercrop_options)
            self.assertEqual(mock_crop.call_count, 2)
            mock_crop.assert_any_call(feed_dir_path, mock_chunk_path1)
            mock_crop.assert_any_call(feed_dir_path, mock_chunk_path2)

            # --- Scenario 2.2: Standard split operation ---
            mock_fix.reset_mock()
            mock_output_files.reset_mock()
            mock_split.reset_mock()

            process_options = ProcessOptions(do_innercrop=False, do_only_merge=False)
            utils.download_merge_split.progressive_merge_and_split(
                feed_dir_path=feed_dir_path, img_file_list=img_file_list, page_url=page_url,
                feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix,
                threshold_options=threshold_options, image_type_options=image_type_options, process_options=process_options)
            self.assertEqual(mock_split.call_count, 2)
            mock_fix.assert_called_once()
            mock_output_files.assert_called_once()

    def test_download_failure_handling(self):
        """Scenario 4: Test that the script handles image download failures gracefully."""
        from bin.crawler import Crawler

        test_html = (
            "<img src='http://test.com/img1.jpg'/>\n"
            "<img src='http://test.com/failed.jpg'/>\n"
            "<img src='http://test.com/img3.jpg'/>"
        )
        page_url = "http://test.com/page.html"
        feed_dir_path = Path("/fake/dir")
        feed_img_dir_path = Path("/fake/img_dir")
        crawler = Crawler(dir_path=feed_dir_path)

        # Mock download_image to simulate a failure for the second image
        self.mock_download_image.side_effect = [
            (Path("/fake/img_dir/img1.jpg"), "http://test.com/img1.jpg"),
            (None, "http://test.com/failed.jpg"), # The failure
            (Path("/fake/img_dir/img3.jpg"), "http://test.com/img3.jpg"),
        ]

        with patch('sys.stdin', new=io.StringIO(test_html)), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            img_files, _, _, _ = utils.download_merge_split.download_image_and_read_metadata(
                feed_dir_path, crawler, feed_img_dir_path, page_url
            )

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

        with patch('sys.argv', fake_argv_flip), \
             patch.dict('os.environ', self.fake_env, clear=False), \
             patch('sys.stdin', new=io.StringIO(test_input)), \
             patch('sys.stdout', new_callable=io.StringIO), \
             patch('utils.download_merge_split.split_image_file', return_value=True), \
             patch('utils.download_merge_split.get_image_dimensions', return_value=(100, 100)), \
             patch('utils.download_merge_split.print_image_files') as mock_print_files:

            utils.download_merge_split.main()

            # Assert that print_image_files was called with the flip option enabled
            mock_print_files.assert_called_once()
            # Check the keyword arguments of the call
            _, called_kwargs = mock_print_files.call_args
            self.assertTrue(called_kwargs.get('do_flip_right_to_left'))

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

            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
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

            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                # original_images can be empty for this check
                print_statistics([], page_url, feed_img_dir)
                output = mock_stdout.getvalue()

            # Processed Images should count stems uniquely, preferring WEBP over JPEG
            # Here we expect two processed images: 1.1 (webp chosen over jpeg) and 1.2 (webp)
            self.assertIn("<!-- Processed Images: 2 files -->", output)
