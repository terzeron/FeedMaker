#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

from utils.download_merge_split import (
    get_image_dimensions,
    crop_image_file,
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
    ThresholdOptions,
    ImageTypeOptions,
    ProcessOptions,
    JPEG_SIZE_LIMIT,
)


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


class TestCropImageFile(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
