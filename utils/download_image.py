#!/usr/bin/env python


import sys
import os
import re
import time
import getopt
import logging.config
from pathlib import Path
from base64 import b64decode
from typing import List, Dict, Any, Optional
import cairosvg
import pyheif
from PIL import Image, UnidentifiedImageError
from bin.feed_maker_util import Config, IO, FileManager, URL, PathUtil
from bin.crawler import Crawler

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def download_image(crawler: Crawler, feed_img_dir_path: Path, img_url: str) -> Optional[Path]:
    LOGGER.debug("# download_image(crawler=%r, feed_img_dir_path='%s', img_url='%s')", crawler, PathUtil.short_path(feed_img_dir_path), img_url[:30])
    # cache file
    cache_file_path = FileManager.get_cache_file_path(feed_img_dir_path, img_url)
    if cache_file_path.is_file() and cache_file_path.stat().st_size > 0:
        return cache_file_path

    # image data uri
    m = re.search(r'^data:image/(?P<img_ext>png|jpeg|jpg);base64,(?P<img_data>.+)', img_url)
    if m:
        img_data = m.group("img_data")
        suffix = "." + m.group("img_ext")
        LOGGER.debug(f"image data '{img_data[:30]}' as base64 to cache file '{cache_file_path}{suffix}'")
        img_file_path = cache_file_path.with_suffix(suffix)
        if img_file_path.is_file() and img_file_path.stat().st_size > 0:
            return img_file_path
        with open(img_file_path, "wb") as outfile:
            decoded_data = b64decode(img_data)
            outfile.write(decoded_data)
        return img_file_path

    # http uri
    if img_url.startswith("http"):
        result, _, _ = crawler.run(img_url, download_file=cache_file_path)
        if not result:
            time.sleep(5)
            result, _, _ = crawler.run(url=img_url, download_file=cache_file_path)
            if not result:
                return None

        with cache_file_path.open("rb") as infile:
            header = infile.read(1024)

        if header.startswith(b"<svg"):
            LOGGER.debug(f"convert svg file '{cache_file_path}' to PNG")
            new_cache_file_path = cache_file_path.with_suffix(".png")
            cairosvg.svg2png(url=str(cache_file_path), write_to=str(new_cache_file_path))
            cache_file_path.unlink(missing_ok=True)
            cache_file_path = new_cache_file_path
        elif b"ftypheic" in header or b"ftypheix" in header or b"ftyphevc" in header or b"ftyphevx" in header:
            LOGGER.debug(f"convert heic file '{cache_file_path}' to PNG")
            heif_file = pyheif.read(str(cache_file_path))
            img = Image.frombytes(mode=heif_file.mode, size=heif_file.size, data=heif_file.data)
            new_cache_file_path = cache_file_path.with_suffix(".png")
            img.save(new_cache_file_path, "PNG")
        else:
            # normal image file
            LOGGER.debug(f"{cache_file_path=}")
            try:
                with Image.open(cache_file_path) as img:
                    if img.format in ("JPEG", "PNG", "WEBP", "GIF"):
                        LOGGER.debug(f"append image extension '{img.format.lower()}'")
                        new_cache_file_path = cache_file_path.with_suffix("." + img.format.lower())
                        cache_file_path.rename(new_cache_file_path)
                    else:
                        LOGGER.debug(f"convert '{cache_file_path}' to PNG")
                        new_cache_file_path = cache_file_path.with_suffix(".png")
                        img.convert("RGB").save(new_cache_file_path, "PNG")
                        cache_file_path.unlink(missing_ok=True)

                    cache_file_path = new_cache_file_path
            except UnidentifiedImageError:
                LOGGER.warning(f"can't identify image '{cache_file_path}'")
                return None
    else:
        return None
    if cache_file_path.is_file() and cache_file_path.stat().st_size > 0:
        return cache_file_path
    return None


def main() -> int:
    LOGGER.debug("# main()")
    feed_dir_path = Path.cwd()

    optlist, args = getopt.getopt(sys.argv[1:], "f:")
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)

    if not feed_dir_path or not feed_dir_path.is_dir():
        LOGGER.error("can't find such a directory '%s'", PathUtil.short_path(feed_dir_path))
        return -1

    page_url: str = args[0]
    feed_name = feed_dir_path.name
    img_url_prefix = "https://terzeron.com/xml/img/" + feed_name
    feed_img_dir_path: Path = Path(os.environ["WEB_SERVICE_FEEDS_DIR"]) / "img" / feed_name
    feed_img_dir_path.mkdir(exist_ok=True)
    LOGGER.debug("feed_dir_path='%s'", PathUtil.short_path(feed_dir_path))
    LOGGER.debug("feed_name='%s'", feed_name)
    LOGGER.debug("item_url_prefix='%s'", img_url_prefix)
    LOGGER.debug("feed_img_dir_path='%s'", PathUtil.short_path(feed_img_dir_path))

    config = Config(feed_dir_path=feed_dir_path)
    if not config:
        LOGGER.error("can't get configuration")
        return -1
    extraction_conf = config.get_extraction_configs()
    if not extraction_conf:
        LOGGER.error("can't get extraction configuration")
        return -1

    timeout = extraction_conf.get("timeout", None)
    headers: Dict[str, Any] = {"User-Agent": extraction_conf.get("user_agent", None), "Referer": URL.encode(page_url)}
    crawler = Crawler(dir_path=feed_dir_path, headers=headers, num_retries=2, timeout=timeout)

    line_list: List[str] = IO.read_stdin_as_line_list()
    for line in line_list:
        line = line.rstrip()
        m = re.search(r'''
        (?P<pre_text>.*)
        <img
        [^>]*
        src=
        (["\'])
        (?P<img_url>[^"\']+)
        (["\'])
        (\s*width=["\']\d+%?["\'])?
        [^>]*
        /?>
        (?P<post_text>.*)
        ''', line, re.VERBOSE)
        if m:
            pre_text = m.group("pre_text")
            img_url = m.group("img_url")
            if not img_url.startswith("http"):
                img_url = URL.concatenate_url(page_url, img_url)
            post_text = m.group("post_text")

            m = re.search(r'^\s*$', pre_text)
            if not m:
                print(pre_text)

            # download
            cache_file_path = download_image(crawler, feed_img_dir_path, img_url)
            if cache_file_path and cache_file_path.is_file():
                suffix = cache_file_path.suffix
                cache_url = FileManager.get_cache_url(img_url_prefix, img_url, "")
                url_img_short = img_url if not img_url.startswith("data:image") else img_url[:30]
                LOGGER.debug("%s -> %s / %s%s", url_img_short, PathUtil.short_path(cache_file_path), cache_url, suffix)
                print(f"<img src='{cache_url}{suffix}'/>")
            else:
                LOGGER.debug(f"no cache file for '{img_url}'")
                print(f"<img src='{FileManager.IMAGE_NOT_FOUND_IMAGE_URL}' alt='not exist or size 0'/>")

            m = re.search(r'^\s*$', post_text)
            if not m:
                print(post_text)
        else:
            m = re.search(r'^</?br>$', line)
            if not m:
                print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
