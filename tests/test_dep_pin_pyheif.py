#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `pyheif`.

Purpose
-------
Pin the pyheif surface utils/image_downloader.py relies on for decoding
HEIC/HEIF images before handing them to PIL. Production calls
`pyheif.read(path)` and reads `.mode`, `.size`, `.data` off the result
to build `PIL.Image.frombytes(mode, size, data)`.

pyheif is a C extension (libheif binding), so an upgrade can change the
entry point or the decoded-object attribute names. No HEIF fixture ships
with the repo, so this test pins the `read` entry point and that it
genuinely attempts to decode (raising on non-HEIF input) rather than
silently degrading. The `.mode/.size/.data` attribute contract is
documented above and covered behaviorally by test_image_downloader.py.

Reference call sites (production code):
    utils/image_downloader.py:11    import pyheif
    utils/image_downloader.py:114   heif_file = pyheif.read(str(cache_file_path))
    utils/image_downloader.py:115   Image.frombytes(heif_file.mode, heif_file.size, heif_file.data)
"""

import unittest

import pyheif


class PyheifSurfaceTest(unittest.TestCase):
    def test_read_is_callable(self) -> None:
        # utils/image_downloader.py:114 -- pyheif.read(...)
        self.assertTrue(callable(pyheif.read))

    def test_read_rejects_non_heif_input(self) -> None:
        # A real decode attempt: bogus bytes must raise, not return a
        # degraded object that would later crash Image.frombytes.
        with self.assertRaises(Exception):
            pyheif.read(b"this-is-not-a-heif-image")


if __name__ == "__main__":
    unittest.main()
