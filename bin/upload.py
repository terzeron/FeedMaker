#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import re
import logging
import logging.config
from feed_maker_util import exec_cmd


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
logger = logging.getLogger()


def main(rss_file: str) -> int:
    d = os.environ["FEED_MAKER_WWW_FEEDS_DIR"]
    do_upload = False
    old_rss_file = rss_file + ".old"

    if os.path.isfile(old_rss_file):
        # 과거 파일이 존재하면 비교해보고 다른 경우에만 업로드
        cmd: str = "perl -pe 's/(\<\/?\w+\>)/\\n$1/g' %s > %s.temp && perl -pe 's/(\<\/?\w+\>)/\\n$1/g' %s > %s.temp && diff '%s.temp' '%s.temp' | egrep -v \"(^(<|>) <(pubDate|lastBuildDate))|(^---$)|(^[0-9,]+[a-z][0-9,]+$)\" | wc -c; rm -f %s.temp %s.temp" % (rss_file, rss_file, old_rss_file, old_rss_file, rss_file, old_rss_file, rss_file, old_rss_file)
        logger.debug(cmd)
        result, error = exec_cmd(cmd)
        if not error:
            logger.debug(result)
            match = re.search(r"^\s*(\d+)\s*$", result)
            if match and match.group(1) != "0":
                do_upload = True
    elif os.path.isfile(rss_file):
        # 과거 파일이 존재하지 않고 신규 파일만 존재하면 업로드
        do_upload = True
    else:
        logger.error("Upload failed! the same old RSS file")
        return -1
        
    if do_upload:
        cmd = "cp %s %s" % (rss_file, d)
        logger.debug(cmd)
        result, error = exec_cmd(cmd)
        if not error:
            logger.info("Upload success!")
            return 0
    logger.warning("Upload failed! No change from the previous RSS file")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
