#!/usr/bin/env python


import sys
import os
import re
import time
import urllib.parse
import logging
import logging.config
from base64 import b64decode
from typing import List, Optional, Dict, Any
from feed_maker_util import Config, IO, Cache, exec_cmd, make_path
from crawler import Crawler


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()
IMAGE_NOT_FOUND_IMAGE_URL = "https://terzeron.com/image-not-found.png"


def download_image(crawler: Crawler, path_prefix: str, img_url_or_data: str, page_url: str) -> Optional[str]:
    LOGGER.debug("# download_image(crawler=%r, path_prefix=%s, image_url_or_data=%s, page_url=%s)", crawler, path_prefix, img_url_or_data, page_url)
    cache_file = Cache.get_cache_file_name(path_prefix, img_url_or_data, "")
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file

    m = re.search(r'^data:image/(?:png|jpeg|jpg);base64,(?P<img_data>.+)', img_url_or_data)
    if m:
        img_data = m.group("img_data")
        LOGGER.debug("image data '%s' as base64 to cache file '%s'", img_data, cache_file)
        if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
            return cache_file
        with open(cache_file, "wb") as outfile:
            decoded_data = b64decode(img_data)
            outfile.write(decoded_data)
        return cache_file

    if img_url_or_data.startswith("http"):
        img_url = img_url_or_data

        # handle non ascii url
        url = urllib.parse.urlsplit(page_url)
        urls = list(url)
        urls[2] = urllib.parse.quote(urls[2])
        page_url = urllib.parse.urlunsplit(urls)

        LOGGER.debug("image url '%s' to cache file '%s'", img_url, cache_file)
        result = crawler.run(img_url, download_file=cache_file)
        if not result:
            time.sleep(5)
            result = crawler.run(img_url)
            if not result:
                return None
    else:
        return None
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file
    return None


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
    headers["Referer"] = page_url
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
        (?P<img_url_or_data>[^"\']+)
        (["\'])
        (\s*width=["\']\d+%?["\'])?
        /?>
        (?P<post_text>.*)
        ''', line, re.VERBOSE)
        if m:
            pre_text = m.group("pre_text")
            img_url_or_data = m.group("img_url_or_data")
            post_text = m.group("post_text")

            m = re.search(r'^\s*$', pre_text)
            if not m:
                print(pre_text)

            # download
            cache_file = download_image(crawler, path_prefix, img_url_or_data, page_url)
            if cache_file:
                cache_url = Cache.get_cache_url(img_url_prefix, img_url_or_data, "")
                LOGGER.debug("%s -> %s / %s", img_url_or_data, cache_file, cache_url)
                print("<img src='%s'/>" % cache_url)
            else:
                LOGGER.debug("no cache file '%s'", cache_file)
                print("<img src='%s' alt='not exist or size 0'/>" % IMAGE_NOT_FOUND_IMAGE_URL)

            m = re.search(r'^\s*$', post_text)
            if not m:
                print(post_text)
        else:
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
