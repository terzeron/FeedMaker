#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""점진적 병합 + 밴드 분할.

이미지를 세로로 이어붙이며, 목표 높이(기본 1080) 부근부터 검정/흰색 균일 가로
밴드를 찾아 그 자연스러운 밴드 위치에서 분할한다. 목표 높이는 강제 절단점이
아니라 분할을 시작할 기준일 뿐이며, 창 안에 밴드가 없으면 다음 밴드가 나타날
때까지 계속 이어붙인다(그림 중간을 강제로 자르지 않음). 출력 포맷의 차원
한계(WEBP/JPEG/PNG)에 도달할 때만 강제로 절단한다.

폭 고정 HTML/PDF 뷰어에서 전체 스트림을 스크롤하는 환경을 가정한다.

stdin -> stdout. 다운로드는 하지 않고 이미 캐시된 로컬 이미지 파일을 병합/분할한다.
"""

import getopt
import logging.config
import re
import sys
from pathlib import Path

from PIL import Image

from bin.feed_maker_util import Env, FileManager, IO, PathUtil

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

# 매우 긴 병합 이미지를 다루므로 DecompressionBomb 가드를 해제
Image.MAX_IMAGE_PIXELS = None

# 기본값
DEFAULT_TARGET_HEIGHT = 1080
DEFAULT_WINDOW = 200
DEFAULT_BANDWIDTH = 20
DEFAULT_DIFF_THRESHOLD = 0.05
DEFAULT_ACCEPTABLE_DIFF = 1
DEFAULT_QUALITY = 75
DEFAULT_COLOR_STRATEGY = "blackorwhite"

# 배경색(분할 밴드) 전략. 지금은 blackorwhite만 지원하며, 추후
# white/black/#hex/fuzzy/dominant 등은 _build_background_mask의 dispatch에 추가한다.
SUPPORTED_COLOR_STRATEGIES = ("blackorwhite",)

# 세그먼트 파일명에 붙이는 infix (기존 캐시 파일과 네임스페이스 분리)
INFIX = "ms"

# 세그먼트 인덱스 자릿수 (0-padding 고정폭, 파일명 사전순 정렬 보장)
INDEX_WIDTH = 3


def segment_postfix(index: int) -> str:
    """세그먼트 파일명/URL에 공통으로 쓰는 postfix. 파일과 URL이 어긋나지 않도록 단일 소스로 관리."""
    return f"{INFIX}{index:0{INDEX_WIDTH}d}"


# WEBP 차원 한계
WEBP_SIZE_LIMIT = 16383

# 출력 포맷별 (파일 확장자, 차원 하드 상한). 상한은 강제 절단 시 사용된다.
FORMAT_INFO: dict[str, tuple[str, int]] = {"JPEG": (".jpg", 65500), "PNG": (".png", 100000), "WEBP": (".webp", WEBP_SIZE_LIMIT)}

_IMG_PATTERN = re.compile(r"<img[^>]*src=[\"'](?P<src>[^\"']+)[\"'][^>]*?/?>")
_WIDTH_PATTERN = re.compile(r"width=['\"][^'\"]*['\"]")


def resolve_local_image_path(src: str, feed_img_dir_path: Path) -> Path | None:
    """img src(캐시 URL)를 로컬 캐시 파일 경로로 해석. 존재하지 않으면 None."""
    basename = src.split("?")[0].rstrip("/").split("/")[-1]
    if not basename:
        return None
    candidate = feed_img_dir_path / basename
    return candidate if candidate.is_file() else None


def parse_stdin_images(feed_img_dir_path: Path) -> tuple[list[Path], list[str], str]:
    """stdin HTML을 읽어 로컬 이미지 파일 목록, 일반 HTML 줄, 대표 width 속성을 반환."""
    img_file_list: list[Path] = []
    normal_html_lines: list[str] = []
    width_attr = ""

    for line in IO.read_stdin_as_line_list():
        line = line.rstrip()
        if not _IMG_PATTERN.search(line):
            if not re.search(r"^</?br>$", line) and line.strip():
                normal_html_lines.append(line)
            continue

        pos = 0
        for m in _IMG_PATTERN.finditer(line):
            pre_text = line[pos : m.start()].strip()
            if pre_text:
                normal_html_lines.append(pre_text)
            pos = m.end()

            tag = m.group(0)
            local_path = resolve_local_image_path(m.group("src"), feed_img_dir_path)
            if local_path:
                img_file_list.append(local_path)
                if not width_attr:
                    width_match = _WIDTH_PATTERN.search(tag)
                    if width_match:
                        width_attr = width_match.group(0)
            else:
                # 캐시되지 않은(다운로드 안 된) 이미지는 원본 태그 그대로 통과
                normal_html_lines.append(tag)

        tail_text = line[pos:].strip()
        if tail_text:
            normal_html_lines.append(tail_text)

    return img_file_list, normal_html_lines, width_attr


_EXT_TO_FORMAT = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}


def resolve_output_format(img_file_list: list[Path], override: str | None) -> str:
    """출력 포맷(Pillow 포맷명)을 결정.

    override가 없으면 첫 원본 파일의 **확장자**로 포맷을 유지한다(사용자가 보는
    확장자 기준). 알 수 없는 확장자뿐이면 WEBP로 폴백.
    """
    if override:
        key = "." + override.strip().lower().lstrip(".")
        if key not in _EXT_TO_FORMAT:
            raise ValueError(f"unsupported output format: {override}")
        return _EXT_TO_FORMAT[key]
    for f in img_file_list:
        fmt = _EXT_TO_FORMAT.get(f.suffix.lower())
        if fmt:
            return fmt
    return "WEBP"


def vstack_images(top: Image.Image | None, bottom: Image.Image) -> Image.Image:
    """두 이미지를 세로로 이어붙임. 폭이 다르면 max 폭의 흰 배경에 좌측 정렬."""
    if top is None:
        return bottom
    new_width = max(top.width, bottom.width)
    new_height = top.height + bottom.height
    merged = Image.new("RGB", (new_width, new_height), "white")
    merged.paste(top, (0, 0))
    merged.paste(bottom, (0, top.height))
    return merged


def _build_background_mask(roi: Image.Image, strategy: str, accept: int) -> Image.Image:
    """RGB ROI에서 배경=0, content=1 인 'L' 모드 마스크를 생성.

    배경색 전략별 매핑 지점이다. 지금은 blackorwhite만 지원하며, 추후
    white/black/#hex/fuzzy/dominant 등을 이 dispatch에 분기로 추가하면 된다.
    """
    if strategy == "blackorwhite":
        black_max = accept
        white_min = 255 - accept
        gray = roi.convert("L")
        # 검정 근처(<= accept) 또는 흰색 근처(>= 255-accept) 픽셀을 배경(0)으로 매핑
        return gray.point(lambda p: 0 if (p <= black_max or p >= white_min) else 1)
    raise ValueError(f"unsupported color strategy: {strategy}")


def _background_row_flags(im: Image.Image, y_lo: int, y_hi: int, accept: int, diff_threshold: float, strategy: str = DEFAULT_COLOR_STRATEGY) -> list[bool]:
    """[y_lo, y_hi) 각 행이 배경 행(분할 가능)인지 여부를 반환.

    배경이 아닌(content) 픽셀 수가 width * diff_threshold 이하이면 배경 행으로 간주.
    """
    width = im.width
    roi = im.crop((0, y_lo, width, y_hi))
    mask = _build_background_mask(roi, strategy, accept)
    data = mask.tobytes()
    max_content = width * diff_threshold

    flags: list[bool] = []
    for r in range(y_hi - y_lo):
        content_count = sum(data[r * width : (r + 1) * width])
        flags.append(content_count <= max_content)
    return flags


def _scan_band_centers(im: Image.Image, lo: int, hi: int, bandwidth: int, diff_threshold: float, accept: int, strategy: str = DEFAULT_COLOR_STRATEGY) -> list[int]:
    """[lo, hi) 범위에서 bandwidth행 이상 연속된 배경 밴드의 중심 y 목록을 반환."""
    if hi - lo < bandwidth:
        return []
    flags = _background_row_flags(im, lo, hi, accept, diff_threshold, strategy)
    centers: list[int] = []
    run = 0
    for idx, is_bg in enumerate(flags):
        if is_bg:
            run += 1
            if run >= bandwidth:
                band_start = idx - bandwidth + 1
                centers.append(lo + band_start + bandwidth // 2)
        else:
            run = 0
    return centers


def decide_cut(im: Image.Image, *, target: int, window: int, bandwidth: int, diff_threshold: float, accept: int, strategy: str, size_limit: int) -> int | None:
    """분할 지점 y를 결정. 더 누적이 필요하면 None을 반환한다.

    1) target 주변 ±window 안에 밴드가 있으면 target에 가장 가까운 밴드에서 절단.
    2) 없으면 window 이후 첫 밴드(아래쪽)까지 확장해 그 밴드에서 절단.
    3) 그래도 밴드가 없고 size_limit에 도달했으면 size_limit에서 강제 절단.
    4) 밴드도 없고 size_limit도 안 됐으면 None(이미지를 더 이어붙여야 함).
    """
    height = im.height
    lo = max(bandwidth, target - window)
    hi = min(height, target + window)
    centers = _scan_band_centers(im, lo, hi, bandwidth, diff_threshold, accept, strategy)
    if centers:
        return min(centers, key=lambda c: abs(c - target))

    lo2 = min(max(bandwidth, target + window), height)
    # size_limit 안에서만 밴드를 찾는다. 한계를 넘는 밴드에서 절단하면 세그먼트가
    # 출력 포맷의 차원 한계를 초과해 인코딩에 실패한다(아래 강제 절단으로 위임).
    hi2 = min(height, size_limit)
    centers2 = _scan_band_centers(im, lo2, hi2, bandwidth, diff_threshold, accept, strategy)
    if centers2:
        return min(centers2)

    if height >= size_limit:
        return size_limit
    return None


def save_segment(im: Image.Image, feed_img_dir_path: Path, page_url: str, index: int, quality: int, out_format: str) -> Path:
    """세그먼트를 지정 포맷으로 저장하고 경로를 반환."""
    suffix, _ = FORMAT_INFO[out_format]
    seg_path = FileManager.get_cache_file_path(feed_img_dir_path, page_url, postfix=segment_postfix(index), suffix=suffix)
    save_kwargs = {"quality": quality} if out_format in ("JPEG", "WEBP") else {}
    im.save(seg_path, format=out_format, **save_kwargs)
    LOGGER.debug("saved segment %s (%dx%d, %s)", PathUtil.short_path(seg_path), im.width, im.height, out_format)
    return seg_path


def print_statistics(original_files: list[Path], segments: list[tuple[int, int]]) -> None:
    """원본 대비 처리 결과(파일 수/총 높이/최대 폭/면적)를 HTML 주석으로 출력."""
    orig_height = orig_area = orig_width = 0
    for f in original_files:
        try:
            with Image.open(f) as im:
                w, h = im.size
        except (OSError, IOError, ValueError, TypeError, RuntimeError):
            continue
        orig_height += h
        orig_area += w * h
        orig_width = max(orig_width, w)

    seg_height = sum(h for _, h in segments)
    seg_area = sum(w * h for w, h in segments)
    seg_width = max((w for w, _ in segments), default=0)

    print("<!-- merge_and_split statistics -->")
    print(f"<!-- original: {len(original_files)} files, total height {orig_height}px, max width {orig_width}px, area {orig_area:,}px^2 -->")
    print(f"<!-- segments: {len(segments)} files, total height {seg_height}px, max width {seg_width}px, area {seg_area:,}px^2 -->")


def merge_and_split_stream(
    *, img_file_list: list[Path], page_url: str, feed_img_dir_path: Path, img_url_prefix: str, width_attr: str, target: int, window: int, bandwidth: int, diff_threshold: float, accept: int, quality: int, color_strategy: str = DEFAULT_COLOR_STRATEGY, output_format: str | None = None, print_stats: bool = False
) -> int:
    """이미지를 점진적으로 병합하며 자연스러운 밴드 위치에서 분할하여 세그먼트를 출력."""
    out_format = resolve_output_format(img_file_list, output_format)
    suffix, size_limit = FORMAT_INFO[out_format]
    index = 1
    segments: list[tuple[int, int]] = []

    def emit(segment: Image.Image, idx: int) -> int:
        save_segment(segment, feed_img_dir_path, page_url, idx, quality, out_format)
        segments.append((segment.width, segment.height))
        seg_url = FileManager.get_cache_url(img_url_prefix, page_url, postfix=segment_postfix(idx), suffix=suffix)
        if width_attr:
            print(f"<img src='{seg_url}' {width_attr}/>")
        else:
            print(f"<img src='{seg_url}'/>")
        return idx + 1

    buffer: Image.Image | None = None
    for img_file in img_file_list:
        try:
            with Image.open(img_file) as im:
                img = im.convert("RGB").copy()
        except (OSError, IOError, ValueError, TypeError, RuntimeError) as e:
            LOGGER.error("can't open image '%s': %r", PathUtil.short_path(img_file), e)
            continue

        buffer = vstack_images(buffer, img)
        while buffer is not None:
            cut_y = decide_cut(buffer, target=target, window=window, bandwidth=bandwidth, diff_threshold=diff_threshold, accept=accept, strategy=color_strategy, size_limit=size_limit)
            if cut_y is None or cut_y >= buffer.height:
                break
            index = emit(buffer.crop((0, 0, buffer.width, cut_y)), index)
            buffer = buffer.crop((0, cut_y, buffer.width, buffer.height))

    # 남은 꼬리 flush. 위 루프가 buffer를 항상 size_limit 이하로 비워두므로 통째로 출력.
    if buffer is not None and buffer.height > 0:
        index = emit(buffer, index)

    if print_stats:
        print_statistics(img_file_list, segments)

    return index - 1


def print_usage(program_name: str) -> None:
    print(f"Usage: {program_name} [-f <feed_dir>] [-H <target_height>] [-w <window>] [-b <bandwidth>] [-t <diff_threshold>] [-a <acceptable_diff>] [-c <color_strategy>] [-F <format>] [-q <quality>] <page_url>")
    print("\t\t-f <feed_dir>: feed directory (default: cwd)")
    print(f"\t\t-H <target_height>: split target/min height (default: {DEFAULT_TARGET_HEIGHT})")
    print(f"\t\t-w <window>: band search window (+-px) (default: {DEFAULT_WINDOW})")
    print(f"\t\t-b <bandwidth>: band thickness (default: {DEFAULT_BANDWIDTH})")
    print(f"\t\t-t <diff_threshold>: content pixel ratio threshold (default: {DEFAULT_DIFF_THRESHOLD})")
    print(f"\t\t-a <acceptable_diff>: acceptable diff of color value (default: {DEFAULT_ACCEPTABLE_DIFF})")
    print(f"\t\t-c <color_strategy>: band color strategy {SUPPORTED_COLOR_STRATEGIES} (default: {DEFAULT_COLOR_STRATEGY})")
    print("\t\t-F <format>: output format jpg/png/webp (default: keep source format)")
    print(f"\t\t-q <quality>: JPEG/WEBP quality (default: {DEFAULT_QUALITY})")
    sys.exit(0)


def main() -> int:
    LOGGER.debug("# main()")
    feed_dir_path = Path.cwd()
    target = DEFAULT_TARGET_HEIGHT
    window = DEFAULT_WINDOW
    bandwidth = DEFAULT_BANDWIDTH
    diff_threshold = DEFAULT_DIFF_THRESHOLD
    accept = DEFAULT_ACCEPTABLE_DIFF
    quality = DEFAULT_QUALITY
    color_strategy = DEFAULT_COLOR_STRATEGY
    output_format: str | None = None

    optlist, args = getopt.getopt(sys.argv[1:], "f:H:w:b:t:a:c:F:q:h")
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)
        elif o == "-H":
            target = int(a)
        elif o == "-w":
            window = int(a)
        elif o == "-b":
            bandwidth = int(a)
        elif o == "-t":
            diff_threshold = float(a)
        elif o == "-a":
            accept = int(a)
        elif o == "-c":
            color_strategy = a
        elif o == "-F":
            output_format = a
        elif o == "-q":
            quality = int(a)
        elif o == "-h":
            print_usage(sys.argv[0])

    if color_strategy not in SUPPORTED_COLOR_STRATEGIES:
        LOGGER.error("unsupported color strategy '%s' (supported: %s)", color_strategy, SUPPORTED_COLOR_STRATEGIES)
        return -1

    if output_format is not None:
        try:
            resolve_output_format([], output_format)
        except ValueError:
            LOGGER.error("unsupported output format '%s' (supported: jpg/png/webp)", output_format)
            return -1

    if len(args) < 1:
        print_usage(sys.argv[0])

    if not feed_dir_path or not feed_dir_path.is_dir():
        LOGGER.error("can't find such a directory '%s'", PathUtil.short_path(feed_dir_path))
        return -1

    page_url = args[0]
    feed_name = feed_dir_path.name
    feed_img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / feed_name
    feed_img_dir_path.mkdir(exist_ok=True)
    img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/" + feed_name

    img_file_list, normal_html_lines, width_attr = parse_stdin_images(feed_img_dir_path)
    for line in normal_html_lines:
        print(line)

    if not img_file_list:
        return 0

    merge_and_split_stream(
        img_file_list=img_file_list,
        page_url=page_url,
        feed_img_dir_path=feed_img_dir_path,
        img_url_prefix=img_url_prefix,
        width_attr=width_attr,
        target=target,
        window=window,
        bandwidth=bandwidth,
        diff_threshold=diff_threshold,
        accept=accept,
        quality=quality,
        color_strategy=color_strategy,
        output_format=output_format,
        print_stats=True,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
