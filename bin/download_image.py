#!/usr/bin/env python3

import sys
import os
import re
from feedmakerutil import debug_print
import feedmakerutil


def get_cache_file_name(path_prefix, img_url, img_ext, postfix=None, index=None):
    postfix_str = ""; 
    if postfix:
        postfix_str = "_" + postfix
    
    index_str = ""
    if index:
        index_str = "." + index
                         
    if re.search(r'^https?://', img_url) and img_ext:
        return path_prefix + "/" + feedmakerutil.get_short_md5_name(img_url) + postfix_str + index_str + "." + img_ext
     
    return path_prefix + "/" + img_url


def download_image(path_prefix, img_url, img_ext, page_url):
    cache_file = get_cache_file_name(path_prefix, img_url, img_ext)
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return True
    cmd = 'crawler.sh --download "%s" --referer "%s" "%s"' % (cache_file, page_url, img_url)
    debug_print("<!-- %s -->" % (cmd))
    result = feedmakerutil.exec_cmd(cmd)
    debug_print("<!-- %s -->" % (result))
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file
    return False


def main():
    cmd = "basename " + os.getcwd()
    feedName = feedmakerutil.exec_cmd(cmd).rstrip()
    img_url_prefix = "http://terzeron.net/xml/img/" + feedName
    path_prefix = os.environ["FEED_MAKER_WWW_FEEDS"] + "/img/" + feedName

    img_prefix = ""
    img_index = -1
    img_ext = "jpg"
    num_units = 25

    _url = sys.argv[1]
    cmd = ""
    result = ""

    feedmakerutil.make_path(path_prefix)

    lineList = feedmakerutil.read_stdin_as_line_list()
    for line in lineList:
        line = line.rstrip()
        m = re.search(r'''
        (?P<preText>.*)
        <img 
        \s*
        src=
        (["\'])
        (?P<img_url>[^"\']+)
        (["\'])
        (\s*width=["\']\d+%?["\'])?
        /?>
        (?P<postText>.*)
        ''', line, re.VERBOSE)
        if m:
            preText = m.group("preText")
            img_url = m.group("img_url")
            postText = m.group("postText")
            
            m = re.search(r'^\s*$', preText)
            if not m:
                print(preText)

            # download
            cache_file = download_image(path_prefix, img_url, img_ext, _url)
            if cache_file:
                cache_url = feedmakerutil.get_cache_url(img_url_prefix, img_url, img_ext)
                debug_print("<!-- %s -> %s / %s -->" % (img_url, cache_file, cache_url))
                print("<img src='%s'/>" % (cache_url))
            else:
                print("<img src='%s' alt='not exist or size 0'/>" % (img_url))

            m = re.search(r'^\s*$', postText)
            if not m:
                print(postText)
        else:
            print(line)

            
if __name__ == "__main__":
    main()
