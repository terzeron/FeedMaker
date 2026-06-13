#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `PIL` (Pillow).

Purpose
-------
Pin the Pillow surface used by FeedMaker's image pipeline. A Pillow upgrade
that drops `Image.Resampling.LANCZOS`, changes the `Image.new(mode, size,
color)` signature, or relocates `ImageOps.exif_transpose` will fail at CI
time before the image-conversion path runs in production.

Reference call sites (production code):
    utils/image_downloader.py:12   from PIL import Image, ImageOps, UnidentifiedImageError
    utils/image_downloader.py:82   ImageOps.exif_transpose(img)
    utils/image_downloader.py:88-91 img.width / img.height / img.resize(..., Image.Resampling.LANCZOS)
    utils/image_downloader.py:106  Image.open(path) as img:
    utils/image_downloader.py:108  optimized_img.convert("RGB").save(path, "WEBP", quality=...)
    utils/image_downloader.py:115  Image.frombytes(mode, size, data)
    utils/image_downloader.py:129  img.size == other.size
    utils/image_downloader.py:161  except UnidentifiedImageError
    utils/merge_and_split.py:232 w, h = im.size
    utils/merge_and_split.py:271 im.convert("RGB") (mode normalization)
    utils/merge_and_split.py:134 Image.new("RGB", (w, h), "white")
    utils/merge_and_split.py:135 merged.paste(top, (0, 0))
    utils/merge_and_split.py:221 im.save(seg_path, format=out_format, **save_kwargs)
"""

import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


# -----------------------------------------------------------------------------
# 1. Import-time symbol surface
# -----------------------------------------------------------------------------


class PILImportSurfaceTest(unittest.TestCase):
    """Pin the symbols image_downloader.py imports from PIL."""

    def test_image_module_exposes_image_class(self) -> None:
        # merge_and_split.py:267 -- buffer: Image.Image | None
        # image_downloader.py:81/450  -- type hints reference Image.Image
        self.assertTrue(isinstance(Image.Image, type))

    def test_image_ops_module_is_importable(self) -> None:
        self.assertTrue(callable(ImageOps.exif_transpose))

    def test_unidentified_image_error_is_exception_subclass(self) -> None:
        # image_downloader.py:161 -- except UnidentifiedImageError
        self.assertTrue(isinstance(UnidentifiedImageError, type))
        self.assertTrue(issubclass(UnidentifiedImageError, Exception))


# -----------------------------------------------------------------------------
# 2. Image.new(mode, size, color) constructor shape
# -----------------------------------------------------------------------------


class ImageNewCallShapeTest(unittest.TestCase):
    """Pin Image.new("RGB", (w, h), "white") used in merge_and_split.py:134."""

    def test_image_new_with_three_positional_args(self) -> None:
        img = Image.new("RGB", (16, 8), "white")
        self.assertEqual(img.mode, "RGB")
        self.assertEqual(img.size, (16, 8))


# -----------------------------------------------------------------------------
# 3. Instance attribute / shape contracts
# -----------------------------------------------------------------------------


class ImageInstanceShapeTest(unittest.TestCase):
    """Pin attribute shapes production reads from an Image instance."""

    def _img(self) -> Image.Image:
        return Image.new("RGB", (20, 10), "white")

    def test_size_is_width_height_tuple(self) -> None:
        # merge_and_split.py:232 -- w, h = im.size
        img = self._img()
        w, h = img.size
        self.assertEqual((w, h), (20, 10))

    def test_width_and_height_attributes(self) -> None:
        # image_downloader.py:88-90 -- img.width, img.height
        img = self._img()
        self.assertEqual(img.width, 20)
        self.assertEqual(img.height, 10)

    def test_mode_attribute_is_string(self) -> None:
        # merge_and_split.py:271 -- im.convert("RGB") normalizes mode
        img = self._img()
        self.assertEqual(img.mode, "RGB")


# -----------------------------------------------------------------------------
# 4. resize(..., Image.Resampling.LANCZOS) -- the resampling enum is canonical
# -----------------------------------------------------------------------------


class ImageResizeAndResamplingTest(unittest.TestCase):
    """Pin Image.Resampling.LANCZOS existence and resize call shape."""

    def test_resampling_lanczos_is_an_enum_value(self) -> None:
        # image_downloader.py:91 -- Image.Resampling.LANCZOS
        self.assertTrue(hasattr(Image, "Resampling"))
        self.assertTrue(hasattr(Image.Resampling, "LANCZOS"))

    def test_resize_with_size_tuple_and_resampling_filter(self) -> None:
        img = Image.new("RGB", (100, 50), "white")
        resized = img.resize((50, 25), Image.Resampling.LANCZOS)
        self.assertEqual(resized.size, (50, 25))


# -----------------------------------------------------------------------------
# 5. convert(mode) returns a NEW image in that mode
# -----------------------------------------------------------------------------


class ImageConvertCallShapeTest(unittest.TestCase):
    """Pin img.convert("RGB") used in image_downloader.py and merge_and_split.py."""

    def test_convert_to_rgb_returns_new_image_with_that_mode(self) -> None:
        img = Image.new("RGBA", (4, 4), (255, 0, 0, 128))
        rgb = img.convert("RGB")
        self.assertEqual(rgb.mode, "RGB")
        # original is not mutated
        self.assertEqual(img.mode, "RGBA")


# -----------------------------------------------------------------------------
# 6. save(path, format=, quality=) and save(path, "WEBP", quality=)
# -----------------------------------------------------------------------------


class ImageSaveCallShapeTest(unittest.TestCase):
    """Pin save call shapes used in production."""

    def test_save_with_format_kwarg_and_quality(self) -> None:
        # merge_and_split.py:221 -- im.save(path, format=out_format, **save_kwargs)
        img = Image.new("RGB", (8, 8), "white")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.webp"
            img.save(p, format="WEBP", quality=75)
            self.assertTrue(p.is_file())

    def test_save_with_positional_format_and_quality(self) -> None:
        # image_downloader.py:108 -- img.save(path, "WEBP", quality=quality)
        img = Image.new("RGB", (8, 8), "white")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.webp"
            img.save(p, "WEBP", quality=75)
            self.assertTrue(p.is_file())

    def test_save_jpeg_with_quality(self) -> None:
        # merge_and_split.py:221 -- im.save(path, format="JPEG", **save_kwargs)
        img = Image.new("RGB", (8, 8), "white")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.jpg"
            img.save(p, format="JPEG", quality=75)
            self.assertTrue(p.is_file())


# -----------------------------------------------------------------------------
# 7. Image.open(path) as a context manager
# -----------------------------------------------------------------------------


class ImageOpenContextManagerTest(unittest.TestCase):
    """Pin `with Image.open(p) as img:` usage."""

    def _write_sample(self, tmp: Path) -> Path:
        Image.new("RGB", (4, 4), "white").save(tmp / "x.png")
        return tmp / "x.png"

    def test_image_open_supports_with_statement(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            src = self._write_sample(tmp)
            with Image.open(src) as img:
                self.assertEqual(img.size, (4, 4))


# -----------------------------------------------------------------------------
# 8. Image.frombytes(mode, size, data)
# -----------------------------------------------------------------------------


class ImageFromBytesCallShapeTest(unittest.TestCase):
    """Pin Image.frombytes used in image_downloader.py:115 for HEIF decoding."""

    def test_frombytes_with_mode_size_and_raw_bytes(self) -> None:
        mode = "RGB"
        size = (2, 2)
        data = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255])
        img = Image.frombytes(mode, size, data)
        self.assertEqual(img.mode, "RGB")
        self.assertEqual(img.size, (2, 2))


# -----------------------------------------------------------------------------
# 9. paste(other, (x, y))
# -----------------------------------------------------------------------------


class ImagePasteCallShapeTest(unittest.TestCase):
    """Pin merged.paste(other, (x, y)) used in merge_and_split.py:135."""

    def test_paste_other_image_at_offset_changes_pixel(self) -> None:
        bg = Image.new("RGB", (4, 4), "white")
        fg = Image.new("RGB", (2, 2), "black")
        bg.paste(fg, (0, 0))
        # top-left now black, bottom-right still white
        self.assertEqual(bg.getpixel((0, 0)), (0, 0, 0))
        self.assertEqual(bg.getpixel((3, 3)), (255, 255, 255))


# -----------------------------------------------------------------------------
# 10. ImageOps.exif_transpose returns an Image
# -----------------------------------------------------------------------------


class ImageOpsExifTransposeTest(unittest.TestCase):
    """Pin ImageOps.exif_transpose(img) used in image_downloader.py:82."""

    def test_exif_transpose_returns_an_image_instance(self) -> None:
        img = Image.new("RGB", (4, 4), "white")
        out = ImageOps.exif_transpose(img)
        self.assertIsInstance(out, Image.Image)


# -----------------------------------------------------------------------------
# 11. UnidentifiedImageError is raised by Image.open on garbage bytes
# -----------------------------------------------------------------------------


class UnidentifiedImageErrorTest(unittest.TestCase):
    """Pin: Image.open() on non-image bytes raises UnidentifiedImageError."""

    def test_open_on_garbage_raises_unidentified_image_error(self) -> None:
        # image_downloader.py:161 catches this exact exception.
        buf = io.BytesIO(b"this is not an image")
        with self.assertRaises(UnidentifiedImageError):
            Image.open(buf).load()


if __name__ == "__main__":
    unittest.main()
