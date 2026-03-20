#!/usr/bin/env python

import sys
import re
import getopt
import logging.config
import functools
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse
from utils.image_downloader import ImageDownloader
from bin.feed_maker_util import Config, IO, PathUtil, Env
from bin.crawler import Crawler


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def _get_base_domain(hostname: str) -> str:
    parts = hostname.split(".")
    if len(parts) <= 2:
        return hostname
    if parts[-2] in ("co", "or", "ne", "ac", "go"):
        return ".".join(parts[-3:]) if len(parts) >= 3 else hostname
    return ".".join(parts[-2:])


def _is_same_origin(page_url: str, img_url: str) -> bool:
    parsed_img = urlparse(img_url)
    if not parsed_img.scheme or not parsed_img.hostname:
        return True
    if parsed_img.scheme == "data":
        return True
    parsed_page = urlparse(page_url)
    if not parsed_page.hostname:
        return True
    return _get_base_domain(parsed_page.hostname) == _get_base_domain(parsed_img.hostname)


def replace_img_tag(match: re.Match[str], *, crawler: Crawler, feed_img_dir_path: Path, quality: int, page_url: str = "", exclude_ad_images: bool = False) -> str:
    img_url = match.group("img_url")
    original_tag = match.group(0)

    if exclude_ad_images and page_url and not _is_same_origin(page_url, img_url):
        LOGGER.warning("광고 이미지 제외: %s (page: %s)", img_url, page_url)
        return ""

    try:
        _, new_img_url = ImageDownloader.download_image(crawler, feed_img_dir_path, img_url, quality=quality)
        if new_img_url:
            # width 속성만 보존하고 나머지는 제거
            width_match = re.search(r"width=['\"][^'\"]*['\"]", original_tag)
            if width_match:
                width_attr = width_match.group(0)
                return f"<img src='{new_img_url}' {width_attr}/>"
            else:
                return f"<img src='{new_img_url}'/>"
        else:
            return "<img src='not_found.png' alt='not exist or size 0'/>"
    except (OSError, IOError, TypeError, ValueError, RuntimeError) as e:
        LOGGER.error(f"이미지 다운로드 중 오류 발생: {e}")
        return "<img src='not_found.png' alt='error occurred'/>"


def main() -> int:
    feed_dir_path = Path.cwd()
    quality = 75  # default quality

    optlist, args = getopt.getopt(sys.argv[1:], "f:q:")
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)
        elif o == "-q":
            quality = int(a)

    if not feed_dir_path.is_dir():
        LOGGER.error("can't find such a directory '%s'", PathUtil.short_path(feed_dir_path))
        return -1

    page_url = args[0]
    feed_name = feed_dir_path.name
    feed_img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / feed_name
    feed_img_dir_path.mkdir(exist_ok=True)

    config = Config(feed_dir_path)
    extraction_conf = config.get_extraction_configs()
    exclude_ad_images = extraction_conf.get("exclude_ad_images", False)
    headers = {"User-Agent": extraction_conf.get("user_agent", ""), "Referer": page_url}
    crawler = Crawler(dir_path=feed_dir_path, headers=headers, num_retries=2)

    replacer = functools.partial(replace_img_tag, crawler=crawler, feed_img_dir_path=feed_img_dir_path, quality=quality, page_url=page_url, exclude_ad_images=exclude_ad_images)

    def split_and_print(line: str, replacer: Callable[..., str]) -> None:
        # 이미지 태그가 있으면 치환 후 태그/요소 단위로 분리 출력
        img_pattern = r'<img[^>]*src=["\'](?P<img_url>[^"\']+)["\'][^>]*?/?>'
        if not re.search(img_pattern, line):
            print(line, end="")
            return
        # <noscript> 내 중복 이미지 제거
        line = re.sub(r"<noscript>\s*<img[^>]*/?>\s*</noscript>", "", line)
        new_line = re.sub(img_pattern, replacer, line)
        # <tag>...</tag> 또는 <self-closing/> 패턴
        element_pattern = r"<([^/\s>]+)[^>]*>.*?</\1>|<[^>]+/?>"
        current = 0
        for m in re.finditer(element_pattern, new_line):
            if m.start() > current:
                text = new_line[current : m.start()].strip()
                if text:
                    print(text)
            print(m.group(0))
            current = m.end()
        # 남은 텍스트
        if current < len(new_line):
            tail = new_line[current:].strip()
            if tail:
                print(tail)

    for line in IO.read_stdin_as_line_list():
        split_and_print(line, replacer)

    return 0


if __name__ == "__main__":
    sys.exit(main())
