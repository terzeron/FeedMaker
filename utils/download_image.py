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
from bin.feed_maker_util import Config, IO, Cache, URL
from bin.crawler import Crawler

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()
IMAGE_NOT_FOUND_IMAGE_URL = "https://terzeron.com/image-not-found.png"


def download_image(crawler: Crawler, feed_img_dir_path: Path, img_url: str) -> Optional[Path]:
    LOGGER.debug(f"# download_image(crawler={crawler}, feed_img_dir_path={feed_img_dir_path}, img_url={img_url[:30]})")
    cache_file = Cache.get_cache_file_path(feed_img_dir_path, img_url)
    for ext in ["", ".png", ".jpeg", ".jpg"]:
        cache_file_path = cache_file.with_suffix(ext)
        if cache_file_path.is_file() and cache_file_path.stat().st_size > 0:
            return cache_file_path

    m = re.search(r'^data:image/(?P<img_ext>png|jpeg|jpg);base64,(?P<img_data>.+)', img_url)
    if m:
        img_data = m.group("img_data")
        img_ext = "." + m.group("img_ext")
        LOGGER.debug(f"image data '{img_data[:30]}' as base64 to cache file '{cache_file}{img_ext}'")
        img_file_path = cache_file.with_suffix(img_ext)
        if img_file_path.is_file() and img_file_path.stat().st_size > 0:
            return img_file_path
        with open(img_file_path, "wb") as outfile:
            decoded_data = b64decode(img_data)
            outfile.write(decoded_data)
        return img_file_path

    if img_url.startswith("http"):
        LOGGER.debug(f"image url '{img_url}' to cache file '{cache_file}'")
        result, _, _ = crawler.run(img_url, download_file=cache_file)
        if not result:
            time.sleep(5)
            result, _, _ = crawler.run(url=img_url, download_file=cache_file)
            if not result:
                return None
    else:
        return None
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file
    return None


def main() -> int:
    LOGGER.debug("# main()")
    feed_dir_path = Path.cwd()

    optlist, args = getopt.getopt(sys.argv[1:], "f:")
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)

    if not feed_dir_path or not feed_dir_path.is_dir():
        LOGGER.error(f"can't find such a directory '{feed_dir_path}'")
        return -1

    page_url: str = args[0]
    feed_name = feed_dir_path.name
    img_url_prefix = "https://terzeron.com/xml/img/" + feed_name
    feed_img_dir_path: Path = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"]) / "img" / feed_name
    feed_img_dir_path.mkdir(exist_ok=True)
    LOGGER.debug(f"feed_dir_path={feed_dir_path}")
    LOGGER.debug(f"feed_name={feed_name}")
    LOGGER.debug(f"item_url_prefix={img_url_prefix}")
    LOGGER.debug(f"feed_img_dir_path={feed_img_dir_path}")

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
        \s*
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
            if cache_file_path:
                _, ext = os.path.splitext(cache_file_path)
                cache_url = Cache.get_cache_url(img_url_prefix, img_url, "")
                url_img_short = img_url if not img_url.startswith("data:image") else img_url[:30]
                LOGGER.debug(f"{url_img_short} -> {cache_file_path} / {cache_url}{ext}")
                print(f"<img src='{cache_url}{ext}'/>")
            else:
                LOGGER.debug(f"no cache file for '{img_url}'")
                print(f"<img src='{IMAGE_NOT_FOUND_IMAGE_URL}' alt='not exist or size 0'/>")

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
