#!/usr/bin/env python3


import sys
import os
import re
import time
import feedmakerutil
from feedmakerutil import IO, Cache
from logger import Logger
from typing import List, Optional


logger = Logger("download_image.py")


def download_image(path_prefix: str, img_url: str, img_ext: str, page_url: str) -> Optional[str]:
    cache_file: str = Cache.get_cache_file_name(path_prefix, img_url, img_ext)
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file
    cmd: str = 'crawler.sh --download "%s" --referer "%s" "%s"' % (cache_file, page_url, img_url)
    logger.debug("<!-- %s -->" % cmd)
    (result, error) = feedmakerutil.exec_cmd(cmd)
    logger.debug("<!-- %s -->" % result)
    if error:
        time.sleep(5)
        (result, error) = feedmakerutil.exec_cmd(cmd)
        if error:
            return None
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file
    return None


def main() -> int:
    cmd: str = "basename " + os.getcwd()
    (result, error) = feedmakerutil.exec_cmd(cmd)
    if error:
        return -1

    feed_name: str = result.rstrip()
    img_url_prefix: str = "http://terzeron.net/xml/img/" + feed_name
    path_prefix: str = os.environ["FEED_MAKER_WWW_FEEDS"] + "/img/" + feed_name
    img_ext: str = "jpg"
    page_url: str = sys.argv[1]

    feedmakerutil.make_path(path_prefix)

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
            pre_text: str = m.group("pre_text")
            img_url: str = m.group("img_url")
            post_text: str = m.group("post_text")
           
            m = re.search(r'^\s*$', pre_text)
            if not m:
                print(pre_text)

            # download
            cache_file: str = download_image(path_prefix, img_url, img_ext, page_url)
            if cache_file:
                cache_url: str = Cache.get_cache_url(img_url_prefix, img_url, img_ext)
                logger.debug("<!-- %s -> %s / %s -->" % (img_url, cache_file, cache_url))
                print("<img src='%s'/>" % cache_url)
            else:
                print("<img src='%s' alt='not exist or size 0'/>" % img_url)

            m = re.search(r'^\s*$', post_text)
            if not m:
                print(post_text)
        else:
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
