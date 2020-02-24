#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
import re
import signal
import logging
from urllib.parse import urlencode
from feed_maker_util import exec_cmd
from typing import Optional, Dict


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
logger = logging.getLogger()


def get_default_config(type_name) -> Dict[str, str]:
    if type_name == "book":
        url_prefix = "http://book.naver.com/search/search.nhn?sm=sta_hty.book&sug=&where=nexearch&"
        url_param = "query"
        encoding = "utf-8"
        review_point_pattern = r'<div class="review_point( b_star)?">\s*<span style="width:(\d+\.\d+)%;">별점'
    elif type_name == "movie":
        url_prefix = "http://movie.naver.com/movie/search/result.nhn?section=all&ie=utf8&"
        url_param = "query"
        encoding = "cp949"
        review_point_pattern = r'<dd class="point( b_star)?">\s*<span class="star">\s*<em class="view_star" style="width:(\d+\.\d+)%"></em>\s*</span>\s*<em class="num">\d+\.\d+</em>\s*<em class="cuser_cnt">[^<]*</em>\s*</dd>\s*</dd>\s*<dd class="etc">(?:(?:<a href=\x27/movie/sdb/browsing/bmovie\.nhn\?genre=\d+\x27>[^<]*</a>,\s*)*<a href=\x27/movie/sdb/browsing/bmovie\.nhn\?genre=\d+\x27>[^<]*</a>\s*<span class="vr">\|</span>\s*)?<em>(?:<a href=\'/movie/sdb/browsing/bmovie\.nhn\?nation=[^\']+\'>[^<]*</a>,\s*)*<a href=\'/movie/sdb/browsing/bmovie\.nhn\?nation=[^\']+\'>[^<]*</a></em>\s*<span class="vr">\|</span>\d+[^<]*\s*<span class="vr">\|</span>\s*<a href="/movie/sdb/browsing/bmovie\.nhn\?year=\d\d\d\d">(\d\d\d\d)</a></dd>'
    elif type_name == "game":
        url_prefix = "http://store.steampowered.com/search/?"
        url_param = "term"
        encoding = "utf-8"
        review_point_pattern = r'<div class="col search_metascore">(\d+)</div>'
        # review_point_pattern = r'\s*<div class="col search_released">\d+ \w+ \d\d\d\d</div>'
    else:
        return {}
    return {"url_prefix": url_prefix, "url_param": url_param, "encoding": encoding, "review_point_pattern": review_point_pattern}


def get_page(url) -> Optional[str]:
    cmd = "crawler.py \"%s\"" % url
    result, error = exec_cmd(cmd)
    return result


def get_first_search_result(config, type_name, keyword, year) -> str:
    url_prefix = config["url_prefix"]
    url_param = config["url_param"]
    review_point_pattern = config["review_point_pattern"]

    url = "%s%s" % (url_prefix, urlencode({url_param: keyword}))
    html = get_page(url)
    if not html:
        logger.error("can't get page html from url '%s'" % url)
        return ""
    m = re.search(review_point_pattern, html, re.MULTILINE)
    # print "review_point_pattern=", review_point_pattern
    # print "m=", m
    if m:
        # print "m='%s', '%s' '%s'" % (m.group(0), m.group(1), m.group(2))
        if type_name == "movie":
            if m.group(1) == " b_star":
                return "0.1"
            elif m.group(3) != year:
                return "0.2"
            else:
                return m.group(2)
        elif type_name == "book":
            if m.group(1) == " b_star":
                return "0.1"
            else:
                return m.group(2)
        elif type_name == "game":
            return m.group(1)

    return "0.0"


def print_usage() -> None:
    print("usage: %s\t <book|movie|game> <keyword> [ <year> ]\n\n" % sys.argv[0])


def main() -> int:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    if len(sys.argv) < 3:
        print_usage()
        return -1
    type_name = sys.argv[1]
    keyword = sys.argv[2]
    if type_name != "book" and type_name != "movie" and type_name != "game":
        print_usage()
        return -1
    year = ""
    if len(sys.argv) > 3:
        year = sys.argv[3]
    config = get_default_config(type_name)
    point = get_first_search_result(config, type_name, keyword, year)
    if point:
        print(point)
    return 0


if __name__ == "__main__":
    sys.exit(main())
