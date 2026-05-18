#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `pdf2image`.

Purpose
-------
Pin convert_from_path(pdf_path) used by utils/convert_pdf_to_image.py.
A pdf2image upgrade that changes the return shape, renames the entry
point, or stops accepting pathlib.Path would silently break the
PDF→image pipeline.

Reference call sites (production code):
    utils/convert_pdf_to_image.py:9   from pdf2image import convert_from_path
    utils/convert_pdf_to_image.py:53  images = convert_from_path(pdf_file_path)
    utils/convert_pdf_to_image.py:55  for num, image in enumerate(images):
    utils/convert_pdf_to_image.py:60  image.save(image_file, image_type)  -- PIL Image
"""

import tempfile
import unittest
from pathlib import Path

from PIL import Image
from pdf2image import convert_from_path


def _build_one_page_pdf(target_dir: Path) -> Path:
    # PIL can render a Pillow Image straight to PDF, so we don't need an
    # extra dependency to fabricate a sample PDF for the test.
    src = Image.new("RGB", (200, 100), "white")
    pdf_path = target_dir / "sample.pdf"
    src.save(pdf_path, format="PDF")
    return pdf_path


class Pdf2ImageImportSurfaceTest(unittest.TestCase):
    def test_convert_from_path_is_callable(self) -> None:
        self.assertTrue(callable(convert_from_path))


class ConvertFromPathCallShapeTest(unittest.TestCase):
    """Pin convert_from_path(pdf_file_path) -- pathlib.Path argument."""

    def test_convert_from_path_returns_list_of_pil_images(self) -> None:
        # utils/convert_pdf_to_image.py iterates the return value AND calls
        # `.save(image_file, image_type)` on each element -- so each element
        # must be (or quack as) a PIL Image.
        with tempfile.TemporaryDirectory() as t:
            pdf = _build_one_page_pdf(Path(t))
            images = convert_from_path(pdf)

            self.assertIsInstance(images, list)
            self.assertEqual(len(images), 1)
            self.assertIsInstance(images[0], Image.Image)

    def test_returned_image_supports_save_with_format_positional(self) -> None:
        # Production passes `image_type` as the second positional arg.
        with tempfile.TemporaryDirectory() as t:
            pdf = _build_one_page_pdf(Path(t))
            images = convert_from_path(pdf)
            out = Path(t) / "page.jpg"
            images[0].save(out, "JPEG")
            self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
