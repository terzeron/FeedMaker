#!/usr/bin/env python3


import sys
import os
import re
import time
import logging
import logging.config
from feed_maker_util import IO, Cache, exec_cmd, make_path
from typing import List, Optional
from base64 import b64decode


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
logger = logging.getLogger()


def download_image(path_prefix: str, img_url_or_data: str, page_url: str) -> Optional[str]:
    logger.debug("# download_image(%s, %s, %s)" % (path_prefix, img_url_or_data[:30], page_url))
    cache_file = Cache.get_cache_file_name(path_prefix, img_url_or_data, "")
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file

    m = re.search(r'^data:image/(?:png|jpeg|jpg);base64,(?P<img_data>.+)', img_url_or_data)
    if m:
        img_data = m.group("img_data")
        logger.debug("image data '%s' as base64 to cache file '%s'" % (img_data[:30], cache_file))
        if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
            return cache_file
        with open(cache_file, "wb") as outfile:
            decoded_data = b64decode(img_data)
            outfile.write(decoded_data)
        return cache_file

    if img_url_or_data.startswith("http"):
        img_url = img_url_or_data
        logger.debug("image url '%s' to cache file '%s'" % (img_url, cache_file))
        cmd = 'crawler.py --retry 2 --download "%s" --referer "%s" "%s"' % (cache_file, page_url, img_url)
        logger.debug("%s" % cmd)
        (result, error) = exec_cmd(cmd)
        logger.debug("result: %s" % result)
        if error:
            time.sleep(5)
            (result, error) = exec_cmd(cmd)
            if error:
                return None
    else:
        return None
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file
    return None


def main() -> int:
    cmd = "basename " + os.getcwd()
    (result, error) = exec_cmd(cmd)
    if error:
        return -1

    feed_name = result.rstrip()
    img_url_prefix = "https://terzeron.com/xml/img/" + feed_name
    path_prefix = os.environ["FEED_MAKER_WWW_FEEDS_DIR"] + "/img/" + feed_name
    page_url = sys.argv[1]

    make_path(path_prefix)

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
            cache_file = download_image(path_prefix, img_url_or_data, page_url)
            if cache_file:
                cache_url = Cache.get_cache_url(img_url_prefix, img_url_or_data, "")
                logger.debug("%s -> %s / %s" % (img_url_or_data[:100], cache_file, cache_url))
                print("<img src='%s'/>" % cache_url)
            else:
                logger.debug("no cache file '%s'" % (cache_file))
                print("<img src='%s' alt='not exist or size 0'/>" % img_url_or_data)

            m = re.search(r'^\s*$', post_text)
            if not m:
                print(post_text)
        else:
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
