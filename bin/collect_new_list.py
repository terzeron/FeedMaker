#!/usr/bin/env python3

import sys
import os
import re
import time
import feedmakerutil
from feedmakerutil import die, err, warn
from feedmakerutil import Config

error_log_file_name = "collector.error.log"


def extract_urls(url, options):
    #print("# extract_urls(%s, %s, %s, %s) % (url, options["item_capture_script", options["user_agent"], options["referer"]))
    print("# options=", options)
    
    option_str = feedmakerutil.determine_crawler_options(options)
    whole_cmd = ""
    
    with open(error_log_file_name, 'w', encoding='utf-8') as error_file:
        cmd = "crawler.sh %s '%s'" % (option_str, url)
        if whole_cmd:
            whole_cmd += " | " + cmd
        else:
            whole_cmd += cmd
        print("# %s" % (whole_cmd))
        (result, error) = feedmakerutil.exec_cmd(cmd)
        if error:
            time.sleep(5)
            (result, error) = feedmakerutil.exec_cmd(cmd)
            if error:
                error_file.write(whole_cmd + "\n" + str(result) + "\n")
                sys.stderr.write(whole_cmd + "\n" + str(result) + "\n")
                error_file.write("can't get result from crawler script\n")
                die("can't get result from crawler script")
                
        cmd = "extract_element.py collection"
        if whole_cmd:
            whole_cmd += " | " + cmd
        else:
            whole_cmd += cmd
        print("# %s" % (whole_cmd))
        (result, error) = feedmakerutil.exec_cmd(cmd, result)
        if error: 
            error_file.write(whole_cmd + "\n" + str(result) + "\n")
            sys.stderr.write(whole_cmd + "\n" + str(result) + "\n")
            error_file.write("can't get result from extract script\n")
            die("can't get result from extract script")

        cmd = options["item_capture_script"]
        if whole_cmd:
            whole_cmd += " | " + cmd
        else:
            whole_cmd += cmd
        print("# %s" % (whole_cmd))
        (result, error) = feedmakerutil.exec_cmd(cmd, result)
        if error:
            error_file.write(whole_cmd + "\n" + str(result) + "\n")
            sys.stderr.write(whole_cmd + "\n" + str(result) + "\n")
            error_file.write("can't get result from capture script\n")
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
    #print("# compose_url_list(%s, %s, %s, %s)" % (list_url_list, options["render_js"], options["item_capture_script"], options["referer"]))
    result_list = []

    for list_url in options["list_url_list"]:
        url_list = extract_urls(list_url, options)
        result_list.extend(url_list)
    return result_list


def main():
    total_list = []

    conf = Config.read_config()
    options = Config.get_collection_configs(conf)

    # collect items from specified url list
    print("# collecting items from specified url list...")
    total_list = compose_url_list(conf, options)
    for (link, title) in total_list:
        print("%s\t%s" % (link, title))

    return 0


if __name__ == "__main__":
    sys.exit(main())
