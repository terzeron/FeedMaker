#!/usr/bin/env python3

import sys
import os
import re
import time
import pprint
import feedmakerutil
from feedmakerutil import die, err, warn
from feedmakerutil import Config
from logger import Logger


logger = Logger("collect_new_list.py")


def extract_urls(url, options):
    logger.debug("# extract_urls(%s)" % (url))
    
    option_str = feedmakerutil.determine_crawler_options(options)
    whole_cmd = ""
    
    cmd = "crawler.sh %s '%s'" % (option_str, url)
    if whole_cmd:
        whole_cmd += " | " + cmd
    else:
        whole_cmd += cmd
    logger.debug("# %s" % (whole_cmd))
    (result, error) = feedmakerutil.exec_cmd(cmd)
    if error:
        time.sleep(5)
        (result, error) = feedmakerutil.exec_cmd(cmd)
        if error:
            logger.debug(whole_cmd + "\n" + str(result) + "\n")
            die("can't get result from crawler script")
                
    cmd = "extract_element.py collection"
    if whole_cmd:
        whole_cmd += " | " + cmd
    else:
        whole_cmd += cmd
    logger.debug("# %s" % (whole_cmd))
    (result, error) = feedmakerutil.exec_cmd(cmd, result)
    if error: 
        logger.debug(whole_cmd + "\n" + str(result) + "\n")
        logger.err(error)
        die("can't get result from extract script")

    cmd = options["item_capture_script"]
    if whole_cmd:
        whole_cmd += " | " + cmd
    else:
        whole_cmd += cmd
    logger.debug("# %s" % (whole_cmd))
    (result, error) = feedmakerutil.exec_cmd(cmd, result)
    if error:
        logger.debug(whole_cmd + "\n" + str(result) + "\n")
        die("can't get result from capture script")

    # check the result
    result_list = []
    for line in result.rstrip().split("\n"):
        line = line.rstrip()
        if re.search(r'^\#', line) or re.search(r'^\s*$', line):
            continue
        items = line.split("\t")
        link = items[0]
        title = " ".join(items[1:])
        if link == None or link == "" or title == None or title == "":
            die("can't get the link and title from '%s'," % (link))
        result_list.append((link, title))
    return result_list


def compose_url_list(conf, options):
    logger.debug("# compose_url_list()")
    result_list = []

    for list_url in options["list_url_list"]:
        url_list = extract_urls(list_url, options)
        result_list.extend(url_list)

    result_list = feedmakerutil.remove_duplicates(result_list)
    return result_list


def main():
    total_list = []

    conf = Config.read_config()
    options = Config.get_collection_configs(conf)
    logger.debug("# options=%s" % pprint.pformat(options))

    # collect items from specified url list
    logger.debug("# collecting items from specified url list...")
    total_list = compose_url_list(conf, options)
    for (link, title) in total_list:
        logger.info("%s\t%s" % (link, title))

    return 0


if __name__ == "__main__":
    sys.exit(main())
