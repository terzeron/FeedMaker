#!/usr/bin/env python


import sys
import os
import re
import time
import logging
import logging.config
from base64 import b64decode
from typing import List, Dict, Any
from feed_maker_util import Config, IO, Cache, exec_cmd, make_path, URL
from crawler import Crawler


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()
IMAGE_NOT_FOUND_IMAGE_URL = "https://terzeron.com/image-not-found.png"


def download_image(crawler: Crawler, path_prefix: str, img_url: str) -> str:
    LOGGER.debug("# download_image(crawler=%r, path_prefix=%s, img_url=%r)", crawler, path_prefix, img_url if not img_url.startswith("data:image") else img_url[:30])
    cache_file = Cache.get_cache_file_name(path_prefix, img_url)
    for ext in ["", ".png", ".jpeg", ".jpg"]:
        if os.path.isfile(cache_file + ext) and os.stat(cache_file + ext).st_size > 0:
            return cache_file + ext

    m = re.search(r'^data:image/(?P<img_ext>png|jpeg|jpg);base64,(?P<img_data>.+)', img_url)
    if m:
        img_data = m.group("img_data")
        img_ext = "." + m.group("img_ext")
        LOGGER.debug("image data '%s' as base64 to cache file '%s%s'", img_data[:30], cache_file, img_ext)
        if os.path.isfile(cache_file + img_ext) and os.stat(cache_file + img_ext).st_size > 0:
            return cache_file + img_ext
        with open(cache_file + img_ext, "wb") as outfile:
            decoded_data = b64decode(img_data)
            outfile.write(decoded_data)
        return cache_file + img_ext

    if img_url.startswith("http"):
        LOGGER.debug("image url '%s' to cache file '%s'", img_url, cache_file)
        result = crawler.run(img_url, download_file=cache_file)
        if not result:
            time.sleep(5)
            result = crawler.run(url=img_url, download_file=cache_file)
            if not result:
                return ""
    else:
        return ""
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file
    return ""


def main() -> int:
    cmd = "basename " + os.getcwd()
    result, error = exec_cmd(cmd)
    if error:
        LOGGER.warning("can't execute command '%s', %s", cmd, error)
        return -1

    feed_name = result.rstrip()
    img_url_prefix = "https://terzeron.com/xml/img/" + feed_name
    path_prefix = os.environ["FEED_MAKER_WWW_FEEDS_DIR"] + "/img/" + feed_name
    page_url = sys.argv[1]

    make_path(path_prefix)

    config = Config()
    if not config:
        LOGGER.error("can't read configuration")
        return -1
    extraction_conf = config.get_extraction_configs()

    headers: Dict[str, Any] = {}
    if "user_agent" in extraction_conf:
        headers["User-Agent"] = extraction_conf["user_agent"]
    headers["Referer"] = URL.encode(page_url)
    crawler = Crawler(headers=headers, num_retries=2)

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
        /?>
        (?P<post_text>.*)
        ''', line, re.VERBOSE)
        if m:
            pre_text = m.group("pre_text")
            img_url = m.group("img_url")
            post_text = m.group("post_text")

            m = re.search(r'^\s*$', pre_text)
            if not m:
                print(pre_text)

            # download
            cache_file = download_image(crawler, path_prefix, img_url)
            if cache_file:
                _, ext = os.path.splitext(cache_file)
                cache_url = Cache.get_cache_url(img_url_prefix, img_url, "")
                LOGGER.debug("%s -> %s / %s%s", img_url if not img_url.startswith("data:image") else img_url[:30], cache_file, cache_url, ext)
                print("<img src='%s%s'/>" % (cache_url, ext))
            else:
                LOGGER.debug("no cache file '%s'", cache_file)
                print("<img src='%s' alt='not exist or size 0'/>" % IMAGE_NOT_FOUND_IMAGE_URL)

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
