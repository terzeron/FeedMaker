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


# ────────────────────────────────────────────────────────
# From test_final_gaps.py: image_downloader 추가 테스트
# ────────────────────────────────────────────────────────
class TestImageDownloaderBase64Fails(unittest.TestCase):
    """Line 54: base64 data URI conversion returns None."""

    @patch("utils.image_downloader.Env")
    def test_base64_convert_fails_returns_none(self, mock_env):
        import tempfile
        import base64

        mock_env.get.return_value = "/img"

        crawler = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            feed_img_dir = Path(tmpdir) / "feed"
            feed_img_dir.mkdir()

            tiny_png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100).decode()
            data_uri = f"data:image/png;base64,{tiny_png}"

            with patch.object(ImageDownloader, "convert_image_format", return_value=None):
                result_path, result_url = ImageDownloader.download_image(crawler, feed_img_dir, data_uri)
            self.assertIsNone(result_path)
            self.assertIsNone(result_url)


class TestImageDownloaderNonHttpUrl(unittest.TestCase):
    """Line 74: non-http img_url (not base64, not http) returns None, None."""

    @patch("utils.image_downloader.Env")
    def test_non_http_non_base64_url(self, mock_env):
        import tempfile

        mock_env.get.return_value = "/img"

        crawler = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            feed_img_dir = Path(tmpdir) / "feed"
            feed_img_dir.mkdir()
            result_path, result_url = ImageDownloader.download_image(crawler, feed_img_dir, "ftp://example.com/img.png")
        self.assertIsNone(result_path)
        self.assertIsNone(result_url)


class TestImageDownloaderWebpFallbackSave(unittest.TestCase):
    """Lines 134-136: WEBP with target_path already exists - fallback to save."""

    def test_webp_target_exists_fallback(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test.jpg"
            target_file = Path(tmpdir) / "test.webp"

            img = Image.new("RGB", (10, 10), "red")
            img.save(cache_file, "WEBP")
            target_file.write_bytes(b"existing")

            result = ImageDownloader.convert_image_format(cache_file, quality=75)
            self.assertIsNotNone(result)
            self.assertEqual(result.suffix, ".webp")


# ────────────────────────────────────────────────────────
# Branch coverage improvements
# ────────────────────────────────────────────────────────
class TestHTTPConvertFailFallthrough(unittest.TestCase):
    """Branch 67->74: HTTP download OK but convert_image_format returns None."""

    @patch("utils.image_downloader.ImageDownloader.convert_image_format")
    @patch("utils.image_downloader.FileManager")
    @patch("utils.image_downloader.Env")
    def test_http_convert_returns_none(self, mock_env: MagicMock, mock_fm: MagicMock, mock_convert: MagicMock) -> None:
        mock_env.get.return_value = "http://img.example.com"
        crawler = MagicMock()
        crawler.run.return_value = (True, None, None)

        mock_cache_path = MagicMock(spec=Path)
        mock_cache_path.is_file.return_value = False
        mock_cache_path.stat.return_value = MagicMock(st_size=0)
        mock_fm.get_cache_file_path.return_value = mock_cache_path

        mock_convert.return_value = None  # conversion fails

        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "feed"

        path, url = ImageDownloader.download_image(crawler, feed_dir, "http://example.com/img.jpg")
        self.assertEqual((path, url), (None, None))


class TestExifTransposeReturnsNone(unittest.TestCase):
    """Branch 80->85: exif_transpose returns None, skip assignment."""

    def test_exif_transpose_returns_none(self) -> None:
        img = MagicMock(spec=Image.Image)
        img.width = 800
        img.height = 1200

        with patch("utils.image_downloader.ImageOps") as mock_ops:
            mock_ops.exif_transpose.return_value = None
            result = ImageDownloader.optimize_for_webtoon(img, max_width=1600)

        # Original img should be returned unchanged
        self.assertEqual(result, img)
        img.resize.assert_not_called()


class TestConvertImageFormatSVGDataUri(unittest.TestCase):
    """Branch 80->85 via SVG: tests SVG content detection and resvg conversion."""

    @patch("utils.image_downloader.resvg_py")
    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_svg_cleanup_intermediate_png(self, mock_optimize: MagicMock, mock_resvg: MagicMock) -> None:
        """Branch 140->142: Verify PNG intermediate file is cleaned up during SVG conversion."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test.svg"
            cache_file.write_text("<svg xmlns='http://www.w3.org/2000/svg'><rect/></svg>")

            # Create a small valid PNG for resvg output
            img = Image.new("RGB", (10, 10), "blue")
            import io

            buf = io.BytesIO()
            img.save(buf, "PNG")
            mock_resvg.svg_to_bytes.return_value = buf.getvalue()

            mock_optimized = MagicMock(spec=Image.Image)
            mock_rgb = MagicMock()
            mock_optimized.convert.return_value = mock_rgb
            mock_optimize.return_value = mock_optimized

            result = ImageDownloader.convert_image_format(cache_file, quality=75)

            self.assertIsNotNone(result)
            self.assertEqual(result.suffix, ".webp")
            # Original SVG file should be removed
            self.assertFalse(cache_file.exists())
            # Intermediate PNG should be removed
            self.assertFalse(Path(tmpdir, "test.png").exists())


class TestWebpNoResizeSamePath(unittest.TestCase):
    """Branch 135->137: WebP target exists, cache_file_path == target_path (suffix already .webp)."""

    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_webp_no_resize_diff_suffix_target_exists(self, mock_optimize: MagicMock) -> None:
        """When target_path already exists and suffix differs, fallback save with cache==target skip unlink."""
        cache_path = MagicMock(spec=Path)
        cache_path.suffix = ".jpg"

        target_path = MagicMock(spec=Path)
        target_path.exists.return_value = True
        cache_path.with_suffix.return_value = target_path

        mock_img = MagicMock(spec=Image.Image)
        mock_img.format = "WEBP"
        mock_img.size = (800, 1200)

        mock_optimized = MagicMock(spec=Image.Image)
        mock_optimized.size = (800, 1200)  # same size = no resize
        mock_rgb = MagicMock()
        mock_optimized.convert.return_value = mock_rgb
        mock_optimize.return_value = mock_optimized

        # Header is not SVG, not HEIF
        header = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 1012
        mock_file = MagicMock()
        mock_file.read.return_value = header
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        cache_path.open.return_value = mock_file

        # Make cache_path == target_path for the `if` check
        cache_path.__eq__ = lambda self, other: other is target_path
        cache_path.__ne__ = lambda self, other: other is not target_path

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.return_value.__enter__ = MagicMock(return_value=mock_img)
            mock_open_img.return_value.__exit__ = MagicMock(return_value=False)
            result = ImageDownloader.convert_image_format(cache_path, quality=75)

        # Should fallback to save since target exists, then skip unlink since paths are equal
        mock_rgb.save.assert_called_once_with(target_path, "WEBP", quality=75)
        cache_path.unlink.assert_not_called()
        self.assertEqual(result, target_path)


class TestWebpResizeSamePath(unittest.TestCase):
    """Branch 140->142: WebP resize needed but cache_file_path == target_path."""

    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_webp_resize_same_path(self, mock_optimize: MagicMock) -> None:
        cache_path = MagicMock(spec=Path)
        cache_path.suffix = ".webp"

        target_path = cache_path  # same object
        cache_path.with_suffix.return_value = target_path

        mock_img = MagicMock(spec=Image.Image)
        mock_img.format = "WEBP"
        mock_img.size = (3200, 4800)

        mock_optimized = MagicMock(spec=Image.Image)
        mock_optimized.size = (1600, 2400)
        mock_rgb = MagicMock()
        mock_optimized.convert.return_value = mock_rgb
        mock_optimize.return_value = mock_optimized

        header = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 1012
        mock_file = MagicMock()
        mock_file.read.return_value = header
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        cache_path.open.return_value = mock_file

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.return_value.__enter__ = MagicMock(return_value=mock_img)
            mock_open_img.return_value.__exit__ = MagicMock(return_value=False)
            result = ImageDownloader.convert_image_format(cache_path, quality=75)

        mock_rgb.save.assert_called_once_with(target_path, "WEBP", quality=75)
        cache_path.unlink.assert_not_called()
        self.assertEqual(result, target_path)


class TestNonWebpSamePath(unittest.TestCase):
    """Branch 152->154: Non-WEBP conversion where cache_file_path == new_cache_file_path."""

    @patch("utils.image_downloader.ImageDownloader.optimize_for_webtoon")
    def test_non_webp_same_path_skip_unlink(self, mock_optimize: MagicMock) -> None:
        cache_path = MagicMock(spec=Path)
        cache_path.suffix = ".webp"  # suffix is already .webp but format is not WEBP

        # with_suffix(".webp") returns itself
        cache_path.with_suffix.return_value = cache_path

        mock_img = MagicMock(spec=Image.Image)
        mock_img.format = "PNG"  # Non-WEBP format
        mock_img.size = (800, 1200)

        mock_optimized = MagicMock(spec=Image.Image)
        mock_rgb = MagicMock()
        mock_optimized.convert.return_value = mock_rgb
        mock_optimize.return_value = mock_optimized

        header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 1016
        mock_file = MagicMock()
        mock_file.read.return_value = header
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        cache_path.open.return_value = mock_file

        with patch("utils.image_downloader.Image.open") as mock_open_img:
            mock_open_img.return_value.__enter__ = MagicMock(return_value=mock_img)
            mock_open_img.return_value.__exit__ = MagicMock(return_value=False)
            result = ImageDownloader.convert_image_format(cache_path, quality=80)

        mock_rgb.save.assert_called_once_with(cache_path, "WEBP", quality=80)
        cache_path.unlink.assert_not_called()
        self.assertEqual(result, cache_path)


# --- Merged from test_image_optimization.py ---

import tempfile


def create_test_image(width: int, height: int, format: str = "PNG") -> Path:
    """테스트용 이미지 생성"""
    temp_dir = Path(tempfile.mkdtemp())
    img_path = temp_dir / f"test_image_{width}x{height}.{format.lower()}"

    # 간단한 테스트 이미지 생성
    img = Image.new("RGB", (width, height), color="red")
    img.save(img_path, format)

    return img_path


def test_image_optimization():
    """이미지 최적화 테스트"""
    print("=== 이미지 최적화 테스트 시작 ===\n")

    test_cases = [{"width": 1200, "height": 800, "format": "PNG"}, {"width": 600, "height": 900, "format": "PNG"}, {"width": 1920, "height": 1080, "format": "JPEG"}, {"width": 400, "height": 600, "format": "PNG"}]

    for i, case in enumerate(test_cases, 1):
        print(f"테스트 케이스 {i}: {case['width']}x{case['height']} {case['format']}")

        # 원본 이미지 생성
        original_path = create_test_image(case["width"], case["height"], case["format"])
        original_size = original_path.stat().st_size

        print(f"  원본 파일: {original_path.name}")
        print(f"  원본 크기: {original_size:,} bytes")

        # 최적화 적용
        optimized_path = ImageDownloader.convert_image_format(original_path)

        if optimized_path and optimized_path.exists():
            optimized_size = optimized_path.stat().st_size
            reduction = (1 - optimized_size / original_size) * 100

            with Image.open(optimized_path) as img:
                print(f"  최적화 파일: {optimized_path.name}")
                print(f"  최적화 크기: {optimized_size:,} bytes")
                print(f"  용량 감소: {reduction:.1f}%")
                print(f"  최종 해상도: {img.width}x{img.height}")
                print(f"  최종 포맷: {img.format}")
        else:
            print("  최적화 실패!")

        print()

        # 임시 파일 정리
        original_path.unlink(missing_ok=True)
        if optimized_path:
            optimized_path.unlink(missing_ok=True)
        original_path.parent.rmdir()


def test_webtoon_optimization():
    """웹툰 최적화 기능 테스트"""
    print("=== 웹툰 최적화 기능 테스트 ===\n")

    # 큰 이미지로 테스트
    large_img = Image.new("RGB", (1500, 2000), color="blue")
    small_img = Image.new("RGB", (600, 800), color="green")

    print("큰 이미지 테스트 (1500x2000):")
    optimized_large = ImageDownloader.optimize_for_webtoon(large_img, max_width=800)
    print(f"  최적화 후: {optimized_large.width}x{optimized_large.height}")

    print("\n작은 이미지 테스트 (600x800):")
    optimized_small = ImageDownloader.optimize_for_webtoon(small_img, max_width=800)
    print(f"  최적화 후: {optimized_small.width}x{optimized_small.height}")

    print()


if __name__ == "__main__":
    unittest.main()
