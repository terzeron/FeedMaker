#!/usr/bin/env python3

import pprint
import re
import sys
import time
import getopt
from collections import OrderedDict
from typing import Dict

import feedmakerutil
from feedmakerutil import Config
from feedmakerutil import die
from logger import Logger


logger = Logger("collect_new_list.py")
do_debug = False


def log(*args):
    if do_debug:
        logger.info(*args)
    else:
        logger.debug(*args)


def extract_urls(url, options):
    log("# extract_urls(%s)" % url)
    
    option_str = feedmakerutil.determine_crawler_options(options)
    whole_cmd = ""
    
    cmd = "crawler.py %s '%s'" % (option_str, url)
    if whole_cmd:
        whole_cmd += " | " + cmd
    else:
        whole_cmd += cmd
    log("# %s" % whole_cmd)
    (result, error) = feedmakerutil.exec_cmd(cmd)
    if error:
        time.sleep(5)
        (result, error) = feedmakerutil.exec_cmd(cmd)
        if error:
            log(whole_cmd + "\n" + str(result) + "\n")
            die("can't get result from crawler script")
                
    cmd = "extract_element.py collection"
    if whole_cmd:
        whole_cmd += " | " + cmd
    else:
        whole_cmd += cmd
    log("# %s" % whole_cmd)
    (result, error) = feedmakerutil.exec_cmd(cmd, result)
    if error: 
        log(whole_cmd + "\n" + str(result) + "\n")
        logger.err(error)
        die("can't get result from extract script")

    cmd = options["item_capture_script"]
    if whole_cmd:
        whole_cmd += " | " + cmd
    else:
        whole_cmd += cmd
    log("# %s" % whole_cmd)
    (result, error) = feedmakerutil.exec_cmd(cmd, result)
    if error:
        log(whole_cmd + "\n" + str(result) + "\n")
        die("can't get result from capture script")

    # check the result
    result_list = []
    for line in result.rstrip().split("\n"):
        line = line.rstrip()
        if re.search(r'^#', line) or re.search(r'^\s*$', line):
            continue
        items = line.split("\t")
        link = items[0]
        title = " ".join(items[1:])
        if not link or not title:
            die("can't get the link and title from '%s'," % link)
        result_list.append((link, title))
    return result_list


def compose_url_list(collection_conf: Dict[str, OrderedDict]):
    log("# compose_url_list()")
    result_list = []

    for list_url in collection_conf["list_url_list"]:
        url_list = extract_urls(list_url, collection_conf)
        result_list.extend(url_list)

    result_list = feedmakerutil.remove_duplicates(result_list)
    return result_list


def main():
    global do_debug
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "d")
    except getopt.GetoptError as err:
        logger.error(err)
        sys.exit(-1)
    
    for o, a in opts:
        if o == "-d":
            do_debug = True
        
    config = Config()
    collection_conf = config.get_collection_configs()
    log("# collection_conf=%s" % pprint.pformat(collection_conf))

    # collect items from specified url list
    log("# collecting items from specified url list...")
    total_list = compose_url_list(collection_conf)
    for (link, title) in total_list:
        logger.info("%s\t%s" % (link, title))

    return 0


if __name__ == "__main__":
    sys.exit(main())
