#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import signal
import subprocess
import re
from urllib.parse import urlencode
from bs4 import BeautifulSoup, Comment


def get_default_config(type):
    if type == "book":
        url_prefix = "http://book.naver.com/search/search.nhn?sm=sta_hty.book&sug=&where=nexearch&"
        url_param = "query"
        encoding = "utf-8"
        review_point_pattern = r'<div class="review_point( b_star)?">\s*<span style="width:(\d+\.\d+)%;">별점'
    elif type == "movie":
        url_prefix = "http://movie.naver.com/movie/search/result.nhn?section=all&ie=utf8&"
        url_param = "query"
        encoding = "cp949"
        review_point_pattern = r'<dd class="point( b_star)?">\s*<span class="star">\s*<em class="view_star" style="width:(\d+\.\d+)%"></em>\s*</span>\s*<em class="num">\d+\.\d+</em>\s*<em class="cuser_cnt">[^<]*</em>\s*</dd>\s*</dd>\s*<dd class="etc">(?:(?:<a href=\x27/movie/sdb/browsing/bmovie\.nhn\?genre=\d+\x27>[^<]*</a>,\s*)*<a href=\x27/movie/sdb/browsing/bmovie\.nhn\?genre=\d+\x27>[^<]*</a>\s*<span class="vr">\|</span>\s*)?<em>(?:<a href=\'/movie/sdb/browsing/bmovie\.nhn\?nation=[^\']+\'>[^<]*</a>,\s*)*<a href=\'/movie/sdb/browsing/bmovie\.nhn\?nation=[^\']+\'>[^<]*</a></em>\s*<span class="vr">\|</span>\d+[^<]*\s*<span class="vr">\|</span>\s*<a href="/movie/sdb/browsing/bmovie\.nhn\?year=\d\d\d\d">(\d\d\d\d)</a></dd>'
    elif type == "game":
        url_prefix = "http://store.steampowered.com/search/?"
        url_param = "term"
        encoding = "utf-8"
        review_point_pattern = r'<div class="col search_metascore">(\d+)</div>'
        #review_point_pattern = r'\s*<div class="col search_released">\d+ \w+ \d\d\d\d</div>'
    else:
        return {}
    return {"url_prefix": url_prefix, "url_param": url_param, "encoding": encoding, "review_point_pattern": review_point_pattern}


def get_page(url, encoding):
    cmd = "crawler.sh \"%s\"" % (url)
    result = feedmakerutil.execCmd(cmd)
    return result


def get_first_search_result(config, type, keyword, year):
    url_prefix = config["url_prefix"]
    url_param = config["url_param"]
    encoding = config["encoding"]
    review_point_pattern = config["review_point_pattern"]

    url = "%s%s" % (url_prefix, urlencode({url_param: keyword}));
    html = get_page(url, encoding)
    m = re.search(review_point_pattern, html, re.MULTILINE)
    #print "review_point_pattern=", review_point_pattern
    #print "m=", m
    if m:
        #print "m='%s', '%s' '%s'" % (m.group(0), m.group(1), m.group(2))
        if type == "movie":
            if m.group(1) == " b_star":
                return "0.1"
            elif m.group(3) != year:
                return "0.2"
            else:
                return m.group(2)
        elif type == "book":
            if m.group(1) == " b_star":
                return "0.1"
            else:
                return m.group(2)
        elif type == "game":
            return m.group(1)   

    return "0.0"


def print_usage(program):
    print("usage: %s\t <book|movie|game> <keyword> [ <year> ]\n\n" % (program));

    
if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    if len(sys.argv) < 3:
        print_usage(sys.argv[0])
        sys.exit(-1)
    type = sys.argv[1]
    keyword = sys.argv[2]
    if type != "book" and type != "movie" and type != "game":
        print_usage(sys.argv[0])
        sys.exit(-1)
    year = ""
    if len(sys.argv) > 3:
        year = sys.argv[3]
    config = get_default_config(type)
    point = get_first_search_result(config, type, keyword, year)
    if point:
        print(point)

    
