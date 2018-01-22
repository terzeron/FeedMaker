#!/Usr/bin/env python3

import sys
import os
import re
import feedmakerutil
from feedmakerutil import die, err, warn


def determine_crawler_options(options):
    option_str = ""

    if "true" == options["render_js"]:
        option_str += " --render-js"
    if options["user_agent"]:
        option_str += " --ua '%s'" % (options["user_agent"])
    if options["referer"]:
        option_str += " --referer '%s'" % (options["referer"])
        
    return option_str


def extractUrls(url, options):
    #print("# extractUrls(%s, %s, %s, %s) % (url, options["item_capture_script", options["user_agent"], options["referer"]))

    option_str = determine_crawler_options(options)
    cmd = "crawler.sh %s '%s' | extract_element.py collection | %s" % (option_str, url, options["item_capture_script"])
    print("# %s" % (cmd))
    result = feedmakerutil.exec_cmd(cmd)
    if not result:
        die("can't execute '%s'" % (cmd))

    # check the result
    resultList = []
    for line in result.rstrip().split("\n"):
        line = line.rstrip()
        if re.search(r'^\#', line) or re.search(r'^\s*$', line):
            continue
        items = line.split("\t")
        link = items[0]
        title = " ".join(items[1:])
        if link == None or link == "" or title == None or title == "":
            die("can't get the link and title from '%s'," % (link))
        resultList.append((link, title))
    return resultList


def composeUrlList(listUrlList, options):
    #print("# composeUrlList(%s, %s, %s, %s)" % (listUrlList, options["render_js"], options["item_capture_script"], options["referer"]))
    resultList = []
    
    listUrls = feedmakerutil.get_all_config_values(listUrlList, "list_url")
    for listUrl in listUrls:
        urlList = extractUrls(listUrl, options)
        resultList.extend(urlList)
    return resultList


def main():
    totalList = []
    options = {}

    # configuration
    config = feedmakerutil.read_config()
    if config == None:
        die("can't find conf.xml nor get config element")
    collectionConf = feedmakerutil.get_config_node(config, "collection")

    listUrlList = feedmakerutil.get_config_node(collectionConf, "list_url_list")
    if listUrlList:
        print("# list_url_list: ", listUrlList)

    doRenderJs = feedmakerutil.get_config_value(collectionConf, "render_js")
    print("# render_js: ", doRenderJs)

    itemCaptureScript = feedmakerutil.get_config_value(collectionConf, "item_capture_script")
    if not itemCaptureScript or itemCaptureScript == "":
        itemCaptureScript = "./capture_item_link_title.pl"
        if not os.path.isfile(itemCaptureScript):
            itemCaptureScript = "./capture_item_link_title.py"
    print("# item_capture_script: %s" % (itemCaptureScript))
    itemCaptureScriptProgram = itemCaptureScript.split(" ")[0]
    if not itemCaptureScriptProgram or not os.path.isfile(itemCaptureScriptProgram) or not os.access(itemCaptureScriptProgram, os.X_OK):
        die("can't execute '%s'" % (itemCaptureScriptProgram))

    userAgent = feedmakerutil.get_config_value(collectionConf, "user_agent")

    referer = feedmakerutil.get_config_value(collectionConf, "referer")

    options = {
        "render_js": doRenderJs,
        "item_capture_script": itemCaptureScript,
        "user_agent": userAgent,
        "referer": referer
    }

    # collect items from specified url list
    print("# collecting items from specified url list...")
    totalList = composeUrlList(listUrlList, options)
    for (link, title) in totalList:
        print("%s\t%s" % (link, title))

    return 0


if __name__ == "__main__":
    sys.exit(main())
