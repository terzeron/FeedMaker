#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `resvg_py`.

Purpose
-------
Pin the resvg_py surface utils/image_downloader.py relies on for
rasterizing SVG images to PNG before optimizing to WebP. Production
calls `resvg_py.svg_to_bytes(svg_string=...)` and writes the result
straight to a `.png` file, so the return value must be PNG-encoded
bytes. resvg_py is a Rust extension; an upgrade could rename the
function or change the return type.

This test exercises the REAL renderer against a tiny SVG.

Reference call sites (production code):
    utils/image_downloader.py:10    import resvg_py
    utils/image_downloader.py:103   png_bytes = resvg_py.svg_to_bytes(svg_string=svg_content)
    utils/image_downloader.py:104   new_cache_file_path.with_suffix(".png").write_bytes(png_bytes)
"""

import unittest

import resvg_py

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_TINY_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="red"/></svg>'


class ResvgPySurfaceTest(unittest.TestCase):
    def test_svg_to_bytes_is_callable(self) -> None:
        self.assertTrue(callable(resvg_py.svg_to_bytes))

    def test_svg_to_bytes_accepts_svg_string_kwarg_and_returns_png(self) -> None:
        # utils/image_downloader.py:103 -- svg_to_bytes(svg_string=...)
        out = bytes(resvg_py.svg_to_bytes(svg_string=_TINY_SVG))
        self.assertTrue(out, "renderer returned empty output")
        # Production writes this directly as a .png; it must be PNG-encoded.
        self.assertTrue(out.startswith(_PNG_MAGIC), "output is not PNG-encoded")


if __name__ == "__main__":
    unittest.main()
