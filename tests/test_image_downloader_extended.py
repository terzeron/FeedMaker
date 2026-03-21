#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from base64 import b64encode

from PIL import Image, UnidentifiedImageError

from utils.image_downloader import ImageDownloader


class TestDownloadImageBlocked(unittest.TestCase):
    def test_blocked_domain_egloos(self) -> None:
        crawler = MagicMock()
        result = ImageDownloader.download_image(crawler, Path("/tmp/feed"), "http://www.egloos.com/img.jpg")
        self.assertEqual(result, (None, None))
        crawler.run.assert_not_called()

    def test_blocked_domain_hanafos(self) -> None:
        crawler = MagicMock()
        result = ImageDownloader.download_image(crawler, Path("/tmp/feed"), "http://hanafos.com/photo.png")
        self.assertEqual(result, (None, None))


class TestDownloadImageCacheHit(unittest.TestCase):
    @patch("utils.image_downloader.FileManager")
    @patch("utils.image_downloader.Env")
    def test_cache_hit_returns_cached(self, mock_env: MagicMock, mock_fm: MagicMock) -> None:
        crawler = MagicMock()
        mock_env.get.return_value = "http://img.example.com"

        mock_cache_path = MagicMock(spec=Path)
        mock_cache_path.is_file.return_value = True
        mock_cache_path.stat.return_value = MagicMock(st_size=1024)
        mock_cache_path.suffix = ".webp"
        mock_cache_path.name = "abc123.webp"
        mock_fm.get_cache_file_path.return_value = mock_cache_path
        mock_fm.get_cache_url.return_value = "http://img.example.com/feed/abc123.webp"

        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "feed"

        path, url = ImageDownloader.download_image(crawler, feed_dir, "http://example.com/photo.jpg")
        self.assertEqual(path, mock_cache_path)
        self.assertEqual(url, "http://img.example.com/feed/abc123.webp")
        crawler.run.assert_not_called()


class TestDownloadImageBase64(unittest.TestCase):
    @patch("utils.image_downloader.ImageDownloader.convert_image_format")
    @patch("utils.image_downloader.FileManager")
    @patch("utils.image_downloader.Env")
    def test_base64_png_converts_to_webp(self, mock_env: MagicMock, mock_fm: MagicMock, mock_convert: MagicMock) -> None:
        mock_env.get.return_value = "http://img.example.com"
        crawler = MagicMock()

        mock_cache_path = MagicMock(spec=Path)
        mock_cache_path.is_file.return_value = False
        mock_cache_path.stat.return_value = MagicMock(st_size=0)

        mock_converted = MagicMock(spec=Path)
        mock_converted.is_file.return_value = True
        mock_converted.suffix = ".webp"
        mock_cache_path.with_suffix.return_value = mock_converted

        mock_fm.get_cache_file_path.return_value = mock_cache_path
        mock_fm.get_cache_url.return_value = "http://img.example.com/feed/abc.webp"
        mock_convert.return_value = mock_converted

        png_data = b64encode(b"\x89PNG\r\n\x1a\nfake").decode()
        data_uri = f"data:image/png;base64,{png_data}"

        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "feed"

        m = mock_open()
        with patch("builtins.open", m):
            path, url = ImageDownloader.download_image(crawler, feed_dir, data_uri)

        mock_convert.assert_called_once_with(mock_converted, quality=75)
        self.assertEqual(path, mock_converted)

    @patch("utils.image_downloader.FileManager")
    @patch("utils.image_downloader.Env")
    def test_base64_webp_skips_conversion(self, mock_env: MagicMock, mock_fm: MagicMock) -> None:
        mock_env.get.return_value = "http://img.example.com"
        crawler = MagicMock()

        mock_cache_path = MagicMock(spec=Path)
        mock_cache_path.is_file.return_value = False
        mock_cache_path.stat.return_value = MagicMock(st_size=0)

        mock_webp_path = MagicMock(spec=Path)
        mock_webp_path.suffix = ".webp"
        mock_cache_path.with_suffix.return_value = mock_webp_path

        mock_fm.get_cache_file_path.return_value = mock_cache_path
        mock_fm.get_cache_url.return_value = "http://img.example.com/feed/abc.webp"

        webp_data = b64encode(b"RIFFxxxxWEBPfake").decode()
        data_uri = f"data:image/webp;base64,{webp_data}"

        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "feed"

        m = mock_open()
        with patch("builtins.open", m):
            path, url = ImageDownloader.download_image(crawler, feed_dir, data_uri)

        self.assertEqual(path, mock_webp_path)
        self.assertIsNotNone(url)


class TestDownloadImageHTTP(unittest.TestCase):
    @patch("utils.image_downloader.ImageDownloader.convert_image_format")
    @patch("utils.image_downloader.FileManager")
    @patch("utils.image_downloader.Env")
    def test_http_success_first_try(self, mock_env: MagicMock, mock_fm: MagicMock, mock_convert: MagicMock) -> None:
        mock_env.get.return_value = "http://img.example.com"
        crawler = MagicMock()
        crawler.run.return_value = (True, None, None)

        mock_cache_path = MagicMock(spec=Path)
        mock_cache_path.is_file.return_value = False
        mock_cache_path.stat.return_value = MagicMock(st_size=0)

        mock_converted = MagicMock(spec=Path)
        mock_converted.is_file.return_value = True
        mock_converted.suffix = ".webp"
        mock_convert.return_value = mock_converted

        mock_fm.get_cache_file_path.return_value = mock_cache_path
        mock_fm.get_cache_url.return_value = "http://img.example.com/feed/abc.webp"

        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "feed"

        path, url = ImageDownloader.download_image(crawler, feed_dir, "http://example.com/img.jpg")
        self.assertEqual(path, mock_converted)
        self.assertEqual(crawler.run.call_count, 1)

    @patch("utils.image_downloader.time")
    @patch("utils.image_downloader.ImageDownloader.convert_image_format")
    @patch("utils.image_downloader.FileManager")
    @patch("utils.image_downloader.Env")
    def test_http_retry_success(self, mock_env: MagicMock, mock_fm: MagicMock, mock_convert: MagicMock, mock_time: MagicMock) -> None:
        mock_env.get.return_value = "http://img.example.com"
        crawler = MagicMock()
        crawler.run.side_effect = [(False, None, None), (True, None, None)]

        mock_cache_path = MagicMock(spec=Path)
        mock_cache_path.is_file.return_value = False
        mock_cache_path.stat.return_value = MagicMock(st_size=0)

        mock_converted = MagicMock(spec=Path)
        mock_converted.is_file.return_value = True
        mock_converted.suffix = ".webp"
        mock_convert.return_value = mock_converted

        mock_fm.get_cache_file_path.return_value = mock_cache_path
        mock_fm.get_cache_url.return_value = "http://img.example.com/feed/abc.webp"

        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "feed"

        path, url = ImageDownloader.download_image(crawler, feed_dir, "http://example.com/img.jpg")
        self.assertEqual(path, mock_converted)
        self.assertEqual(crawler.run.call_count, 2)
        mock_time.sleep.assert_called_once_with(5)

    @patch("utils.image_downloader.time")
    @patch("utils.image_downloader.FileManager")
    @patch("utils.image_downloader.Env")
    def test_http_fail_after_retry(self, mock_env: MagicMock, mock_fm: MagicMock, mock_time: MagicMock) -> None:
        mock_env.get.return_value = "http://img.example.com"
        crawler = MagicMock()
        crawler.run.return_value = (False, None, None)

        mock_cache_path = MagicMock(spec=Path)
        mock_cache_path.is_file.return_value = False
        mock_cache_path.stat.return_value = MagicMock(st_size=0)

        mock_fm.get_cache_file_path.return_value = mock_cache_path

        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "feed"

        path, url = ImageDownloader.download_image(crawler, feed_dir, "http://example.com/img.jpg")
        self.assertEqual((path, url), (None, None))
        self.assertEqual(crawler.run.call_count, 2)


class TestOptimizeForWebtoon(unittest.TestCase):
    def test_no_resize_needed(self) -> None:
        img = MagicMock(spec=Image.Image)
        img.width = 800
        img.height = 1200

        with patch("utils.image_downloader.ImageOps") as mock_ops:
            mock_ops.exif_transpose.return_value = img
            result = ImageDownloader.optimize_for_webtoon(img, max_width=1600)

        self.assertEqual(result, img)
        img.resize.assert_not_called()

    def test_resize_needed(self) -> None:
        img = MagicMock(spec=Image.Image)
        img.width = 3200
        img.height = 4800

        resized_img = MagicMock(spec=Image.Image)
        img.resize.return_value = resized_img

        with patch("utils.image_downloader.ImageOps") as mock_ops:
            mock_ops.exif_transpose.return_value = img
            result = ImageDownloader.optimize_for_webtoon(img, max_width=1600)

        img.resize.assert_called_once_with((1600, 2400), Image.Resampling.LANCZOS)
        self.assertEqual(result, resized_img)

    def test_exif_transpose_applied(self) -> None:
        original_img = MagicMock(spec=Image.Image)
        transposed_img = MagicMock(spec=Image.Image)
        transposed_img.width = 500
        transposed_img.height = 700

        with patch("utils.image_downloader.ImageOps") as mock_ops:
            mock_ops.exif_transpose.return_value = transposed_img
            result = ImageDownloader.optimize_for_webtoon(original_img)

        mock_ops.exif_transpose.assert_called_once_with(original_img)
        self.assertEqual(result, transposed_img)


class TestConvertImageFormatSVG(unittest.TestCase):
    @patch("utils.image_downloader.resvg_py")
    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_svg_converts_to_webp(self, mock_optimize: MagicMock, mock_resvg: MagicMock) -> None:
        cache_path = MagicMock(spec=Path)
        svg_header = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        mock_file = MagicMock()
        mock_file.read.return_value = svg_header
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        cache_path.open.return_value = mock_file

        webp_path = MagicMock(spec=Path)
        png_path = MagicMock(spec=Path)
        cache_path.with_suffix.return_value = webp_path
        webp_path.with_suffix.return_value = png_path
        cache_path.read_text.return_value = "<svg></svg>"

        mock_resvg.svg_to_bytes.return_value = b"fakepng"

        mock_img = MagicMock(spec=Image.Image)
        mock_optimized = MagicMock(spec=Image.Image)
        mock_optimize.return_value = mock_optimized
        mock_rgb = MagicMock()
        mock_optimized.convert.return_value = mock_rgb

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.return_value.__enter__ = MagicMock(return_value=mock_img)
            mock_open_img.return_value.__exit__ = MagicMock(return_value=False)

            result = ImageDownloader.convert_image_format(cache_path, quality=80)

        self.assertEqual(result, webp_path)
        mock_resvg.svg_to_bytes.assert_called_once()
        cache_path.unlink.assert_called_once_with(missing_ok=True)
        png_path.unlink.assert_called_once_with(missing_ok=True)


class TestConvertImageFormatHEIF(unittest.TestCase):
    @patch("utils.image_downloader.pyheif")
    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_heif_converts_to_webp(self, mock_optimize: MagicMock, mock_pyheif: MagicMock) -> None:
        cache_path = MagicMock(spec=Path)
        # Header containing ftypheic
        header = b"\x00\x00\x00\x1cftypheic" + b"\x00" * 1000
        mock_file = MagicMock()
        mock_file.read.return_value = header
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        cache_path.open.return_value = mock_file

        webp_path = MagicMock(spec=Path)
        cache_path.with_suffix.return_value = webp_path

        heif_file = MagicMock()
        heif_file.mode = "RGB"
        heif_file.size = (1000, 1500)
        heif_file.data = b"pixeldata"
        mock_pyheif.read.return_value = heif_file

        mock_img = MagicMock(spec=Image.Image)
        mock_optimized = MagicMock(spec=Image.Image)
        mock_rgb = MagicMock()
        mock_optimized.convert.return_value = mock_rgb
        mock_optimize.return_value = mock_optimized

        with patch("utils.image_downloader.Image.frombytes", return_value=mock_img):
            result = ImageDownloader.convert_image_format(cache_path, quality=75)

        self.assertEqual(result, webp_path)
        mock_rgb.save.assert_called_once_with(webp_path, "WEBP", quality=75)


class TestConvertImageFormatWEBP(unittest.TestCase):
    def _make_cache_path_with_header(self, header: bytes) -> MagicMock:
        cache_path = MagicMock(spec=Path)
        mock_file = MagicMock()
        mock_file.read.return_value = header
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        cache_path.open.return_value = mock_file
        return cache_path

    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_webp_no_resize_same_suffix(self, mock_optimize: MagicMock) -> None:
        cache_path = self._make_cache_path_with_header(b"RIFF\x00\x00\x00\x00WEBP")
        cache_path.suffix = ".webp"

        mock_img = MagicMock(spec=Image.Image)
        mock_img.format = "WEBP"
        mock_img.size = (800, 1200)
        mock_optimize.return_value = mock_img  # same size = no resize

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.return_value.__enter__ = MagicMock(return_value=mock_img)
            mock_open_img.return_value.__exit__ = MagicMock(return_value=False)
            result = ImageDownloader.convert_image_format(cache_path, quality=75)

        self.assertEqual(result, cache_path)

    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_webp_no_resize_different_suffix_rename(self, mock_optimize: MagicMock) -> None:
        cache_path = self._make_cache_path_with_header(b"RIFF\x00\x00\x00\x00WEBP")
        cache_path.suffix = ".jpg"

        target_path = MagicMock(spec=Path)
        target_path.exists.return_value = False
        cache_path.with_suffix.return_value = target_path

        mock_img = MagicMock(spec=Image.Image)
        mock_img.format = "WEBP"
        mock_img.size = (800, 1200)
        mock_optimize.return_value = mock_img  # same size

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.return_value.__enter__ = MagicMock(return_value=mock_img)
            mock_open_img.return_value.__exit__ = MagicMock(return_value=False)
            result = ImageDownloader.convert_image_format(cache_path, quality=75)

        cache_path.rename.assert_called_once_with(target_path)
        self.assertEqual(result, target_path)

    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_webp_resize_needed(self, mock_optimize: MagicMock) -> None:
        cache_path = self._make_cache_path_with_header(b"RIFF\x00\x00\x00\x00WEBP")
        cache_path.suffix = ".webp"

        target_path = MagicMock(spec=Path)
        cache_path.with_suffix.return_value = target_path

        mock_img = MagicMock(spec=Image.Image)
        mock_img.format = "WEBP"
        mock_img.size = (3200, 4800)

        mock_optimized = MagicMock(spec=Image.Image)
        mock_optimized.size = (1600, 2400)  # different size = resized
        mock_rgb = MagicMock()
        mock_optimized.convert.return_value = mock_rgb
        mock_optimize.return_value = mock_optimized

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.return_value.__enter__ = MagicMock(return_value=mock_img)
            mock_open_img.return_value.__exit__ = MagicMock(return_value=False)
            result = ImageDownloader.convert_image_format(cache_path, quality=75)

        mock_rgb.save.assert_called_once_with(target_path, "WEBP", quality=75)
        self.assertEqual(result, target_path)

    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_webp_oserror_in_save(self, mock_optimize: MagicMock) -> None:
        cache_path = self._make_cache_path_with_header(b"RIFF\x00\x00\x00\x00WEBP")
        cache_path.suffix = ".webp"

        target_path = MagicMock(spec=Path)
        cache_path.with_suffix.return_value = target_path

        mock_img = MagicMock(spec=Image.Image)
        mock_img.format = "WEBP"
        mock_img.size = (3200, 4800)

        mock_optimized = MagicMock(spec=Image.Image)
        mock_optimized.size = (1600, 2400)
        mock_rgb = MagicMock()
        mock_rgb.save.side_effect = OSError("disk full")
        mock_optimized.convert.return_value = mock_rgb
        mock_optimize.return_value = mock_optimized

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.return_value.__enter__ = MagicMock(return_value=mock_img)
            mock_open_img.return_value.__exit__ = MagicMock(return_value=False)
            result = ImageDownloader.convert_image_format(cache_path, quality=75)

        self.assertIsNone(result)


class TestConvertImageFormatNonWEBP(unittest.TestCase):
    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_non_webp_converts_to_webp(self, mock_optimize: MagicMock) -> None:
        cache_path = MagicMock(spec=Path)
        cache_path.suffix = ".jpg"
        # JPEG header
        header = b"\xff\xd8\xff\xe0" + b"\x00" * 1020
        mock_file = MagicMock()
        mock_file.read.return_value = header
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        cache_path.open.return_value = mock_file

        webp_path = MagicMock(spec=Path)
        cache_path.with_suffix.return_value = webp_path

        mock_img = MagicMock(spec=Image.Image)
        mock_img.format = "JPEG"
        mock_img.size = (800, 1200)

        mock_optimized = MagicMock(spec=Image.Image)
        mock_rgb = MagicMock()
        mock_optimized.convert.return_value = mock_rgb
        mock_optimize.return_value = mock_optimized

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.return_value.__enter__ = MagicMock(return_value=mock_img)
            mock_open_img.return_value.__exit__ = MagicMock(return_value=False)
            result = ImageDownloader.convert_image_format(cache_path, quality=80)

        mock_rgb.save.assert_called_once_with(webp_path, "WEBP", quality=80)
        self.assertEqual(result, webp_path)

    def test_unidentified_image_error(self) -> None:
        cache_path = MagicMock(spec=Path)
        # Not SVG, not HEIF
        header = b"garbage data" + b"\x00" * 1012
        mock_file = MagicMock()
        mock_file.read.return_value = header
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        cache_path.open.return_value = mock_file

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.side_effect = UnidentifiedImageError("bad image")
            result = ImageDownloader.convert_image_format(cache_path, quality=75)

        self.assertIsNone(result)

    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_non_webp_oserror_in_save(self, mock_optimize: MagicMock) -> None:
        cache_path = MagicMock(spec=Path)
        cache_path.suffix = ".png"
        header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 1016
        mock_file = MagicMock()
        mock_file.read.return_value = header
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        cache_path.open.return_value = mock_file

        webp_path = MagicMock(spec=Path)
        cache_path.with_suffix.return_value = webp_path

        mock_img = MagicMock(spec=Image.Image)
        mock_img.format = "PNG"

        mock_optimized = MagicMock(spec=Image.Image)
        mock_rgb = MagicMock()
        mock_rgb.save.side_effect = IOError("write failed")
        mock_optimized.convert.return_value = mock_rgb
        mock_optimize.return_value = mock_optimized

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.return_value.__enter__ = MagicMock(return_value=mock_img)
            mock_open_img.return_value.__exit__ = MagicMock(return_value=False)
            result = ImageDownloader.convert_image_format(cache_path, quality=75)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
