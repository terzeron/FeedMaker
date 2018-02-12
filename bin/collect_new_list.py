#!/usr/bin/env python3

import sys
import os
import re
import feedmakerutil
from feedmakerutil import die, err, warn


error_log_file_name = "collector.error.log"


def determine_crawler_options(options):
    option_str = ""

    if "true" == options["render_js"]:
        option_str += " --render-js"
    if options["user_agent"]:
        option_str += " --ua '%s'" % (options["user_agent"])
    if options["referer"]:
        option_str += " --referer '%s'" % (options["referer"])
        
    return option_str


def extract_urls(url, options):
    #print("# extract_urls(%s, %s, %s, %s) % (url, options["item_capture_script", options["user_agent"], options["referer"]))

    option_str = determine_crawler_options(options)
    cmd = "crawler.sh %s '%s' | extract_element.py collection | %s" % (option_str, url, options["item_capture_script"])
    print("# %s" % (cmd))
    (result, error) = feedmakerutil.exec_cmd(cmd)
    with open(error_log_file_name, 'w', encoding='utf-8') as error_file:
        if error:
            error_file.write(cmd + "\n" + str(result) + "\n")
            sys.stderr.write(cmd + "\n" + str(result) + "\n")
            cmd = "crawler.sh %s '%s' | extract_element.py collection" % (option_str, url)
            (result, error) = feedmakerutil.exec_cmd(cmd)
            if error: 
                error_file.write(cmd + "\n" + str(result) + "\n")
                sys.stderr.write(cmd + "\n" + str(result) + "\n")
                cmd = "crawler.sh %s '%s'" % (option_str, url)
                (result, error) = feedmakerutil.exec_cmd(cmd)
                if error:
                    error_file.write(cmd + "\n" + str(result) + "\n")
                    sys.stderr.write(cmd + "\n" + str(result) + "\n")
                    error_file.write("can't get result from crawler script\n")
                    die("can't get result from crawler script")
                error_file.write("can't get result from extract script\n")
                die("can't get result from extract script")
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


def compose_url_list(list_url_list, options):
    #print("# compose_url_list(%s, %s, %s, %s)" % (list_url_list, options["render_js"], options["item_capture_script"], options["referer"]))
    result_list = []
    
    list_urls = feedmakerutil.get_all_config_values(list_url_list, "list_url")
    for list_url in list_urls:
        url_list = extract_urls(list_url, options)
        result_list.extend(url_list)
    return result_list


def main():
    total_list = []
    options = {}

    # configuration
    config = feedmakerutil.read_config()
    if config == None:
        die("can't find conf.xml nor get config element")
    collection_conf = feedmakerutil.get_config_node(config, "collection")

    list_url_list = feedmakerutil.get_config_node(collection_conf, "list_url_list")
    if list_url_list:
        print("# list_url_list: ", list_url_list)

    do_render_js = feedmakerutil.get_config_value(collection_conf, "render_js")
    print("# render_js: ", do_render_js)

    item_capture_script = feedmakerutil.get_config_value(collection_conf, "item_capture_script")
    if not item_capture_script or item_capture_script == "":
        item_capture_script = "./capture_item_link_title.py"
    print("# item_capture_script: %s" % (item_capture_script))
    item_capture_script_program = item_capture_script.split(" ")[0]
    if not item_capture_script_program or not os.path.isfile(item_capture_script_program) or not os.access(item_capture_script_program, os.X_OK):
        with open(error_log_file_name, 'w', encoding='utf-8') as error_file:
            error_file.write("can't execute '%s'\n" % (item_capture_script_program))
        die("can't execute '%s'" % (item_capture_script_program))

    user_agent = feedmakerutil.get_config_value(collection_conf, "user_agent")

    referer = feedmakerutil.get_config_value(collection_conf, "referer")

    options = {
        "render_js": do_render_js,
        "item_capture_script": item_capture_script,
        "user_agent": user_agent,
        "referer": referer
    }

    # collect items from specified url list
    print("# collecting items from specified url list...")
    total_list = compose_url_list(list_url_list, options)
    for (link, title) in total_list:
        print("%s\t%s" % (link, title))

    return 0


if __name__ == "__main__":
    sys.exit(main())
