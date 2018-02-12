#!/usr/bin/env python3
#-*- coding: utf-8 -*-


import os
import os.path
import sys
import subprocess
import re
import feedmakerutil
from feedmakerutil import die, err, warn


def main(rss_file):
    dir = os.environ["FEED_MAKER_WWW_FEEDS"]
    data_file_list = []
    do_upload = False
    old_rss_file = rss_file + ".old"

    if os.path.isfile(old_rss_file):
        # 과거 파일이 존재하면 비교해보고 다른 경우에만 업로드
        cmd = "diff '%s' '%s' | egrep -v \"(^(<|>) <(pubDate|lastBuildDate))|(^---\$)|(^[0-9,]+[a-z][0-9,]+\$)\" | wc -c" % (rss_file, old_rss_file)
        #print(cmd)
        (result, error) = feedmakerutil.exec_cmd(cmd)
        if not error:
            #print(result)
            match = re.search(r"^\s*(\d+)\s*$", result)
            if match and match.group(1) != "0":
                do_upload = True
    elif os.path.isfile(rss_file):
        # 과거 파일이 존재하지 않고 신규 파일만 존재하면 업로드
        do_upload = True
    else:
        err("Upload failed! the same old RSS file")
        return False
        
    if do_upload == True:
        cmd = "cp %s %s" % (rss_file, dir)
        #print(cmd)
        (result, error) = feedmakerutil.exec_cmd(cmd)
        if not error:
            print("Upload success!\n")
            return True
            
    warn("Upload failed! No change from the previous RSS file")
    return False


if __name__ == "__main__":
    main(sys.argv[1])
