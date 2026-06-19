#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from utils.merge_and_split import resolve_local_image_path, parse_stdin_images, resolve_output_format, vstack_images, _build_background_mask, _scan_band_centers, decide_cut, save_segment, merge_and_split_stream, print_statistics, main, INFIX, INDEX_WIDTH, segment_postfix, DEFAULT_BANDWIDTH, FORMAT_INFO

# blackorwhite 전략에서 검정/흰색은 모두 배경이므로, content는 중간 회색을 사용해야
# 밴드(흰색/검정 균일 영역)가 분할점으로서 의미를 가진다.
_CONTENT = (128, 128, 128)
_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)

_BW = DEFAULT_BANDWIDTH
_BIG_LIMIT = 65500


def _solid(width: int, height: int, color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (width, height), color)


def _content_with_bands(width: int, total_height: int, bands: list[tuple[int, int, tuple[int, int, int]]]) -> Image.Image:
    """회색 content 위에 (위치, 두께, 색) 밴드를 얹은 합성 이미지."""
    im = Image.new("RGB", (width, total_height), _CONTENT)
    for band_at, thickness, color in bands:
        im.paste(Image.new("RGB", (width, thickness), color), (0, band_at))
    return im


def _cut(im: Image.Image, *, target: int = 1080, window: int = 200, bandwidth: int = _BW, diff_threshold: float = 0.05, accept: int = 1, strategy: str = "blackorwhite", size_limit: int = _BIG_LIMIT) -> int | None:
    return decide_cut(im, target=target, window=window, bandwidth=bandwidth, diff_threshold=diff_threshold, accept=accept, strategy=strategy, size_limit=size_limit)


class TestResolveLocalImagePath(unittest.TestCase):
    def test_resolves_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            f = dir_path / "abcdef1.webp"
            f.write_bytes(b"x")
            self.assertEqual(resolve_local_image_path("https://img.example.com/feed/abcdef1.webp", dir_path), f)

    def test_strips_query_string(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            f = dir_path / "abcdef1.webp"
            f.write_bytes(b"x")
            self.assertEqual(resolve_local_image_path("https://img.example.com/feed/abcdef1.webp?v=2", dir_path), f)

    def test_missing_file_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(resolve_local_image_path("https://img.example.com/feed/missing.webp", Path(d)))

    def test_empty_basename_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(resolve_local_image_path("https://img.example.com/feed/", Path(d)))
            self.assertIsNone(resolve_local_image_path("/", Path(d)))
            self.assertIsNone(resolve_local_image_path("", Path(d)))


class TestParseStdinImages(unittest.TestCase):
    def _make_dir_with(self, names: list[str]) -> Path:
        d = Path(tempfile.mkdtemp())
        for n in names:
            (d / n).write_bytes(b"x")
        return d

    def test_collects_resolvable_images_in_order(self) -> None:
        d = self._make_dir_with(["a.webp", "b.webp"])
        html = "<img src='http://x/feed/a.webp'/>\n<img src='http://x/feed/b.webp'/>\n"
        with patch("utils.merge_and_split.IO.read_stdin_as_line_list", return_value=html.splitlines()):
            files, normal, width = parse_stdin_images(d)
        self.assertEqual([f.name for f in files], ["a.webp", "b.webp"])
        self.assertEqual(width, "")

    def test_unresolved_image_passes_through_as_normal(self) -> None:
        d = self._make_dir_with(["a.webp"])
        html = "<img src='http://x/feed/a.webp'/>\n<img src='http://x/feed/missing.webp'/>\n"
        with patch("utils.merge_and_split.IO.read_stdin_as_line_list", return_value=html.splitlines()):
            files, normal, _ = parse_stdin_images(d)
        self.assertEqual([f.name for f in files], ["a.webp"])
        self.assertTrue(any("missing.webp" in line for line in normal))

    def test_captures_first_width_attr(self) -> None:
        d = self._make_dir_with(["a.webp", "b.webp"])
        html = "<img src='http://x/feed/a.webp' width='80%'/>\n<img src='http://x/feed/b.webp' width='50%'/>\n"
        with patch("utils.merge_and_split.IO.read_stdin_as_line_list", return_value=html.splitlines()):
            _, _, width = parse_stdin_images(d)
        self.assertEqual(width, "width='80%'")

    def test_multiple_imgs_and_text_in_one_line(self) -> None:
        d = self._make_dir_with(["a.webp", "b.webp"])
        html = "before<img src='http://x/feed/a.webp'/>mid<img src='http://x/feed/b.webp'/>after"
        with patch("utils.merge_and_split.IO.read_stdin_as_line_list", return_value=[html]):
            files, normal, _ = parse_stdin_images(d)
        self.assertEqual(len(files), 2)
        self.assertIn("before", normal)
        self.assertIn("mid", normal)
        self.assertIn("after", normal)

    def test_skips_br_and_blank_lines(self) -> None:
        d = self._make_dir_with([])
        html = "<br>\n\n<p>keep</p>\n"
        with patch("utils.merge_and_split.IO.read_stdin_as_line_list", return_value=html.splitlines()):
            files, normal, _ = parse_stdin_images(d)
        self.assertEqual(files, [])
        self.assertEqual(normal, ["<p>keep</p>"])


class TestResolveOutputFormat(unittest.TestCase):
    def test_override_aliases(self) -> None:
        self.assertEqual(resolve_output_format([], "jpg"), "JPEG")
        self.assertEqual(resolve_output_format([], ".jpeg"), "JPEG")
        self.assertEqual(resolve_output_format([], "PNG"), "PNG")
        self.assertEqual(resolve_output_format([], "webp"), "WEBP")

    def test_override_invalid_raises(self) -> None:
        with self.assertRaises(ValueError):
            resolve_output_format([], "gif")

    def test_preserve_source_extension(self) -> None:
        # 내용이 아니라 확장자 기준. (실제로 webp 내용이어도 .jpg면 JPEG)
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            jpg = dir_path / "a.jpg"
            _solid(10, 10, _CONTENT).save(jpg, format="WEBP")  # webp 내용, .jpg 확장자
            self.assertEqual(resolve_output_format([jpg], None), "JPEG")
            png = dir_path / "b.png"
            png.write_bytes(b"x")
            self.assertEqual(resolve_output_format([png], None), "PNG")

    def test_unknown_ext_skipped_then_known(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            unknown = dir_path / "a.bin"
            unknown.write_bytes(b"x")
            webp = dir_path / "b.webp"
            webp.write_bytes(b"x")
            self.assertEqual(resolve_output_format([unknown, webp], None), "WEBP")

    def test_all_unknown_ext_falls_back_to_webp(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.bin"
            bad.write_bytes(b"x")
            self.assertEqual(resolve_output_format([bad], None), "WEBP")


class TestVstackImages(unittest.TestCase):
    def test_different_widths_pad_white(self) -> None:
        a = _solid(100, 30, (255, 0, 0))
        b = _solid(160, 50, (0, 255, 0))
        merged = vstack_images(a, b)
        self.assertEqual(merged.size, (160, 80))
        self.assertEqual(merged.getpixel((150, 10)), _WHITE)
        self.assertEqual(merged.getpixel((0, 30)), (0, 255, 0))

    def test_same_width(self) -> None:
        merged = vstack_images(_solid(100, 30, (1, 2, 3)), _solid(100, 20, (4, 5, 6)))
        self.assertEqual(merged.size, (100, 50))

    def test_bottom_narrower(self) -> None:
        merged = vstack_images(_solid(200, 10, (1, 1, 1)), _solid(50, 10, (2, 2, 2)))
        self.assertEqual(merged.size, (200, 20))
        self.assertEqual(merged.getpixel((100, 15)), _WHITE)

    def test_none_top_returns_bottom(self) -> None:
        b = _solid(40, 20, (0, 0, 255))
        self.assertIs(vstack_images(None, b), b)


class TestScanBandCenters(unittest.TestCase):
    def test_finds_white_band(self) -> None:
        im = _content_with_bands(800, 2000, [(1100, 40, _WHITE)])
        centers = _scan_band_centers(im, 1000, 1300, _BW, 0.05, 1)
        self.assertTrue(centers)
        self.assertTrue(all(1100 <= c <= 1140 for c in centers))

    def test_no_band_returns_empty(self) -> None:
        im = _solid(800, 2000, _CONTENT)
        self.assertEqual(_scan_band_centers(im, 1000, 1300, _BW, 0.05, 1), [])

    def test_range_smaller_than_bandwidth(self) -> None:
        im = _content_with_bands(800, 2000, [(1100, 40, _WHITE)])
        self.assertEqual(_scan_band_centers(im, 1100, 1110, _BW, 0.05, 1), [])


class TestDecideCut(unittest.TestCase):
    def test_band_in_window_nearest_to_target(self) -> None:
        im = _content_with_bands(800, 2000, [(1100, 40, _WHITE)])
        cut = _cut(im)
        assert cut is not None
        self.assertGreaterEqual(cut, 1100)
        self.assertLessEqual(cut, 1140)

    def test_black_band_detected(self) -> None:
        im = _content_with_bands(800, 2000, [(1100, 40, _BLACK)])
        cut = _cut(im)
        assert cut is not None
        self.assertGreaterEqual(cut, 1100)
        self.assertLessEqual(cut, 1140)

    def test_band_centered_on_target(self) -> None:
        im = _content_with_bands(800, 2000, [(1070, 20, _WHITE)])
        self.assertEqual(_cut(im), 1080)

    def test_nearest_among_multiple_in_window(self) -> None:
        im = _content_with_bands(800, 2000, [(950, 30, _WHITE), (1150, 30, _WHITE)])
        cut = _cut(im)
        assert cut is not None
        self.assertGreaterEqual(cut, 1150)
        self.assertLessEqual(cut, 1180)

    def test_no_band_in_window_extends_to_next_band(self) -> None:
        # 윈도우[880,1280]엔 밴드 없음, 1500에 밴드 -> 확장하여 거기서 절단
        im = _content_with_bands(800, 3000, [(1500, 40, _WHITE)])
        cut = _cut(im)
        assert cut is not None
        self.assertGreaterEqual(cut, 1500)
        self.assertLessEqual(cut, 1540)

    def test_no_band_under_limit_returns_none(self) -> None:
        im = _solid(800, 2000, _CONTENT)
        self.assertIsNone(_cut(im, size_limit=_BIG_LIMIT))

    def test_no_band_at_limit_forces_cut(self) -> None:
        im = _solid(800, 2000, _CONTENT)
        self.assertEqual(_cut(im, size_limit=1500), 1500)

    def test_band_beyond_size_limit_forces_cut_at_limit(self) -> None:
        # 자연 밴드가 size_limit(1500) 너머(1700)에만 있다. 거기서 자르면 세그먼트가
        # 출력 포맷 한계를 넘으므로, 한계 안엔 밴드가 없는 것으로 보고 1500에서 강제 절단.
        im = _content_with_bands(800, 2000, [(1700, 40, _WHITE)])
        self.assertEqual(_cut(im, size_limit=1500), 1500)


class TestSaveSegment(unittest.TestCase):
    def test_saves_with_format_and_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            for fmt, expect_suffix in [("JPEG", ".jpg"), ("PNG", ".png"), ("WEBP", ".webp")]:
                seg = save_segment(_solid(100, 100, (10, 20, 30)), dir_path, "https://example.com/page?id=1", 1, 75, fmt)
                self.assertTrue(seg.is_file())
                self.assertIn(f"_{segment_postfix(1)}", seg.name)
                self.assertIn(f"_{INFIX}001", seg.name)
                self.assertTrue(seg.name.endswith(expect_suffix))
                with Image.open(seg) as im:
                    self.assertEqual(im.format, fmt)
                seg.unlink()


class TestSegmentPostfix(unittest.TestCase):
    def test_zero_padded_to_fixed_width(self) -> None:
        self.assertEqual(segment_postfix(1), f"{INFIX}001")
        self.assertEqual(segment_postfix(77), f"{INFIX}077")
        self.assertEqual(segment_postfix(100), f"{INFIX}100")

    def test_numeric_part_has_fixed_digit_count(self) -> None:
        for idx in (1, 9, 77, 999):
            self.assertEqual(len(segment_postfix(idx)[len(INFIX) :]), INDEX_WIDTH)


class TestMergeAndSplitStream(unittest.TestCase):
    def _run(self, dir_path: Path, img_files: list[Path], *, target: int = 1080, window: int = 200, bandwidth: int = _BW, diff_threshold: float = 0.05, accept: int = 1, quality: int = 75, width_attr: str = "", output_format: str | None = None, print_stats: bool = False) -> tuple[int, str, list[Path]]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            count = merge_and_split_stream(
                img_file_list=img_files,
                page_url="https://example.com/page",
                feed_img_dir_path=dir_path,
                img_url_prefix="https://img.example.com/feed",
                width_attr=width_attr,
                target=target,
                window=window,
                bandwidth=bandwidth,
                diff_threshold=diff_threshold,
                accept=accept,
                quality=quality,
                output_format=output_format,
                print_stats=print_stats,
            )
        segs = sorted(dir_path.glob(f"*_{INFIX}*"), key=lambda p: int(p.stem.split(INFIX)[-1]))
        return count, buf.getvalue(), segs

    def _save_sources(self, dir_path: Path, images: list[Image.Image], fmt: str = "WEBP", ext: str = ".webp") -> list[Path]:
        paths = []
        for i, im in enumerate(images):
            p = dir_path / f"src{i}{ext}"
            im.save(p, format=fmt)
            paths.append(p)
        return paths

    @staticmethod
    def _wh(path: Path) -> tuple[int, int]:
        with Image.open(path) as im:
            return im.size

    def test_cuts_land_on_bands_and_preserve_height(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            # 각 이미지에 하단 흰 밴드(자연 분할점). 총 높이 보존 + 밴드에서 절단 확인.
            images = [_content_with_bands(800, 1500, [(1450, 50, _WHITE)]) for _ in range(4)]
            total = sum(im.height for im in images)
            files = self._save_sources(dir_path, images)
            count, out, segs = self._run(dir_path, files)
            self.assertGreaterEqual(count, 2)
            self.assertEqual(len(segs), count)
            self.assertEqual(out.count("<img "), count)
            self.assertEqual(sum(self._wh(s)[1] for s in segs), total)

    def test_no_force_cut_extends_past_target(self) -> None:
        # 밴드가 1450에만 있으니 1080이 아니라 ~1450 부근에서 잘려야 함(강제 1080 없음)
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            images = [_content_with_bands(800, 1500, [(1450, 50, _WHITE)]) for _ in range(3)]
            files = self._save_sources(dir_path, images)
            _, _, segs = self._run(dir_path, files)
            heights = [self._wh(s)[1] for s in segs]
            # 1080 고정 조각이 아니라 밴드(~1500) 기준 조각
            self.assertTrue(all(h > 1200 for h in heights[:-1]), heights)

    def test_single_short_image_one_segment(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            files = self._save_sources(dir_path, [_solid(800, 500, _CONTENT)])
            count, _, segs = self._run(dir_path, files)
            self.assertEqual(count, 1)
            self.assertEqual(self._wh(segs[0])[1], 500)

    def test_format_preserved_from_source(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            files = self._save_sources(dir_path, [_content_with_bands(800, 1500, [(1450, 50, _WHITE)])], fmt="JPEG", ext=".jpg")
            _, _, segs = self._run(dir_path, files)
            self.assertTrue(segs)
            for s in segs:
                self.assertTrue(s.name.endswith(".jpg"))
                with Image.open(s) as im:
                    self.assertEqual(im.format, "JPEG")

    def test_format_override(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            files = self._save_sources(dir_path, [_content_with_bands(800, 1500, [(1450, 50, _WHITE)])], fmt="JPEG", ext=".jpg")
            _, _, segs = self._run(dir_path, files, output_format="png")
            self.assertTrue(all(s.name.endswith(".png") for s in segs))

    def test_webp_size_guard(self) -> None:
        # 출력 WEBP 강제 + 밴드 없는 큰 PNG 소스 -> 세그먼트는 WEBP 한계 이하
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            src = dir_path / "tall.png"
            _solid(800, 20000, _CONTENT).save(src, format="PNG")
            _, _, segs = self._run(dir_path, [src], output_format="webp")
            self.assertGreaterEqual(len(segs), 2)
            for s in segs:
                self.assertLessEqual(self._wh(s)[1], FORMAT_INFO["WEBP"][1])
            self.assertEqual(sum(self._wh(s)[1] for s in segs), 20000)

    def test_band_beyond_webp_limit_does_not_overflow(self) -> None:
        # 네이버 웹툰 회귀: 자연 밴드가 WEBP 한계(16383) 너머(17000)에만 있어도
        # 세그먼트가 한계를 넘지 않아야 한다(인코딩 실패 방지).
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            src = dir_path / "tall.png"
            _content_with_bands(800, 20000, [(17000, 50, _WHITE)]).save(src, format="PNG")
            _, _, segs = self._run(dir_path, [src], output_format="webp")
            self.assertGreaterEqual(len(segs), 2)
            for s in segs:
                self.assertLessEqual(self._wh(s)[1], FORMAT_INFO["WEBP"][1])
            self.assertEqual(sum(self._wh(s)[1] for s in segs), 20000)

    def test_width_attr_propagated(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            files = self._save_sources(dir_path, [_solid(800, 500, _CONTENT)])
            _, out, _ = self._run(dir_path, files, width_attr="width='100%'")
            self.assertIn("width='100%'", out)

    def test_unreadable_image_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            good = dir_path / "good.webp"
            _solid(800, 500, _CONTENT).save(good, format="WEBP")
            bad = dir_path / "bad.webp"
            bad.write_bytes(b"not an image")
            count, _, segs = self._run(dir_path, [bad, good])
            self.assertEqual(count, 1)
            self.assertEqual(self._wh(segs[0])[1], 500)

    def test_statistics_emitted(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            files = self._save_sources(dir_path, [_solid(800, 500, _CONTENT)])
            _, out, _ = self._run(dir_path, files, print_stats=True)
            self.assertIn("merge_and_split statistics", out)
            self.assertIn("original:", out)
            self.assertIn("segments:", out)


class TestPrintStatistics(unittest.TestCase):
    def test_skips_unreadable_original(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            good = dir_path / "good.webp"
            _solid(800, 300, _CONTENT).save(good, format="WEBP")
            bad = dir_path / "bad.webp"
            bad.write_bytes(b"not an image")
            buf = io.StringIO()
            with redirect_stdout(buf):
                print_statistics([good, bad], [(800, 300)])
            self.assertIn("original: 2 files, total height 300px, max width 800px", buf.getvalue())


class TestColorStrategy(unittest.TestCase):
    def test_blackorwhite_builds_mask(self) -> None:
        roi = Image.new("RGB", (4, 1), _WHITE)
        roi.putpixel((0, 0), _CONTENT)
        mask = _build_background_mask(roi, "blackorwhite", 1)
        self.assertEqual(list(mask.tobytes()), [1, 0, 0, 0])

    def test_unsupported_strategy_raises(self) -> None:
        roi = Image.new("RGB", (4, 1), _WHITE)
        with self.assertRaises(ValueError):
            _build_background_mask(roi, "dominant", 1)

    def test_main_rejects_unsupported_color(self) -> None:
        with tempfile.TemporaryDirectory() as work_s:
            feed_dir = Path(work_s) / "myfeed"
            feed_dir.mkdir()

            def fake_env_get(key: str) -> str:
                return {"WEB_SERVICE_IMAGE_DIR_PREFIX": work_s, "WEB_SERVICE_IMAGE_URL_PREFIX": "https://img.test/xml"}[key]

            argv = ["merge_and_split.py", "-f", str(feed_dir), "-c", "fuzzy", "https://example.com/demo"]
            with patch("utils.merge_and_split.Env.get", side_effect=fake_env_get), patch("utils.merge_and_split.IO.read_stdin_as_line_list", return_value=[]), patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                rc = main()
            self.assertEqual(rc, -1)


class TestMainIntegration(unittest.TestCase):
    def _setup(self, work_s: str, img_root: Path, images: list[tuple[str, Image.Image, str]]) -> str:
        feed_img_dir = img_root / "myfeed"
        feed_img_dir.mkdir()
        tags = []
        for name, im, fmt in images:
            im.save(feed_img_dir / name, format=fmt)
            tags.append(f"<img src='https://img.test/xml/myfeed/{name}'/>")
        return "<p>intro</p>\n" + "\n".join(tags) + "\n"

    def _env(self, img_root: Path):
        def fake_env_get(key: str) -> str:
            return {"WEB_SERVICE_IMAGE_DIR_PREFIX": str(img_root), "WEB_SERVICE_IMAGE_URL_PREFIX": "https://img.test/xml"}[key]

        return fake_env_get

    def test_main_preserves_source_format(self) -> None:
        with tempfile.TemporaryDirectory() as img_root_s, tempfile.TemporaryDirectory() as work_s:
            img_root = Path(img_root_s)
            feed_dir = Path(work_s) / "myfeed"
            feed_dir.mkdir()
            imgs = [(f"o{i}.jpg", _content_with_bands(800, 1500, [(1450, 50, _WHITE)]), "JPEG") for i in range(3)]
            html = self._setup(work_s, img_root, imgs)
            argv = ["merge_and_split.py", "-f", str(feed_dir), "https://example.com/demo"]
            out = io.StringIO()
            with patch("utils.merge_and_split.Env.get", side_effect=self._env(img_root)), patch("utils.merge_and_split.IO.read_stdin_as_line_list", return_value=html.splitlines()), patch.object(sys, "argv", argv), redirect_stdout(out):
                rc = main()
            self.assertEqual(rc, 0)
            self.assertIn("<p>intro</p>", out.getvalue())
            segs = list((img_root / "myfeed").glob(f"*_{INFIX}*.jpg"))
            self.assertGreaterEqual(len(segs), 1)
            total = sum(Image.open(s).height for s in segs)
            self.assertEqual(total, 4500)

    def test_main_all_options_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as img_root_s, tempfile.TemporaryDirectory() as work_s:
            img_root = Path(img_root_s)
            feed_dir = Path(work_s) / "myfeed"
            feed_dir.mkdir()
            html = self._setup(work_s, img_root, [("a.webp", _content_with_bands(800, 1500, [(1450, 50, _WHITE)]), "WEBP")])
            argv = ["merge_and_split.py", "-f", str(feed_dir), "-H", "800", "-w", "150", "-b", "10", "-t", "0.1", "-a", "5", "-c", "blackorwhite", "-F", "png", "-q", "80", "https://example.com/demo"]
            out = io.StringIO()
            with patch("utils.merge_and_split.Env.get", side_effect=self._env(img_root)), patch("utils.merge_and_split.IO.read_stdin_as_line_list", return_value=html.splitlines()), patch.object(sys, "argv", argv), redirect_stdout(out):
                rc = main()
            self.assertEqual(rc, 0)
            self.assertGreaterEqual(len(list((img_root / "myfeed").glob(f"*_{INFIX}*.png"))), 1)

    def test_main_no_images_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as img_root_s, tempfile.TemporaryDirectory() as work_s:
            img_root = Path(img_root_s)
            feed_dir = Path(work_s) / "myfeed"
            feed_dir.mkdir()
            argv = ["merge_and_split.py", "-f", str(feed_dir), "https://example.com/demo"]
            out = io.StringIO()
            with patch("utils.merge_and_split.Env.get", side_effect=self._env(img_root)), patch("utils.merge_and_split.IO.read_stdin_as_line_list", return_value=["<p>only text</p>"]), patch.object(sys, "argv", argv), redirect_stdout(out):
                rc = main()
            self.assertEqual(rc, 0)
            self.assertIn("<p>only text</p>", out.getvalue())

    def test_main_rejects_unsupported_format(self) -> None:
        with tempfile.TemporaryDirectory() as work_s:
            feed_dir = Path(work_s) / "myfeed"
            feed_dir.mkdir()
            argv = ["merge_and_split.py", "-f", str(feed_dir), "-F", "gif", "https://example.com/demo"]
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                rc = main()
            self.assertEqual(rc, -1)

    def test_main_help_exits(self) -> None:
        argv = ["merge_and_split.py", "-h"]
        with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                main()

    def test_main_no_args_shows_usage_and_exits(self) -> None:
        argv = ["merge_and_split.py"]
        with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                main()

    def test_main_feed_dir_not_directory_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            not_a_dir = Path(d) / "nope"
            argv = ["merge_and_split.py", "-f", str(not_a_dir), "https://example.com/demo"]
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                rc = main()
            self.assertEqual(rc, -1)


if __name__ == "__main__":
    unittest.main()
