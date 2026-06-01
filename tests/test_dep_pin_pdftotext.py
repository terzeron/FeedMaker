#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `pdftotext`.

Purpose
-------
Pin the pdftotext surface utils/convert_pdf_to_text.py relies on.
`pdftotext` is a C extension binding to poppler, so an upgrade (or a
poppler ABI change) can break the call shape or the page-iteration
contract. Production opens a PDF as a binary file object, constructs
`pdftotext.PDF(f)`, then iterates pages as plain strings.

This test exercises the REAL library against a minimal in-memory PDF so
that an API change is caught rather than mocked over (the functional
test in test_convert_pdf_to_text.py mocks pdftotext on purpose).

Reference call sites (production code):
    utils/convert_pdf_to_text.py:10   import pdftotext
    utils/convert_pdf_to_text.py:44   pdf = pdftotext.PDF(f)
    utils/convert_pdf_to_text.py:45   for page in pdf: ... page.replace(...)
"""

import io
import unittest

import pdftotext

# Minimal single-page PDF containing the text "Hello PDF".
_MINIMAL_PDF = (
    b"%PDF-1.1\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 44>>stream\nBT /F1 18 Tf 20 100 Td (Hello PDF) Tj ET\nendstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"trailer<</Root 1 0 R>>\n"
)


class PdftotextSurfaceTest(unittest.TestCase):
    def test_pdf_class_is_callable(self) -> None:
        self.assertTrue(callable(pdftotext.PDF))

    def test_pdf_is_iterable_of_string_pages(self) -> None:
        # utils/convert_pdf_to_text.py:44-45 -- pdftotext.PDF(f); for page in pdf
        pdf = pdftotext.PDF(io.BytesIO(_MINIMAL_PDF))
        pages = list(pdf)
        self.assertEqual(len(pages), 1)
        self.assertIsInstance(pages[0], str)
        # page strings support .replace(...) as production uses them.
        self.assertIn("Hello PDF", pages[0])


if __name__ == "__main__":
    unittest.main()
