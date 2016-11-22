#!/Usr/bin/env python3

import sys
import os
import re
import feedmakerutil
from feedmakerutil import die, err, warn


def extractUrls(doRenderJs, url, itemCaptureScript, userAgent, referer):
    #print("# extractUrls(%s, %s, %s, %s) % (url, itemCaptureScript, userAgent, referer))

    option = ""
    if doRenderJs == "true":
        option += " --render-js"
    if userAgent != "":
        option += " --ua '%s'" % (userAgent)
    if referer != "":
        option += " --referer '%s'" % (referer)
    cmd = "wget.sh %s '%s' | extract_element.py collection | %s" % (option, url, itemCaptureScript)
    print("# %s" % (cmd))
    result = feedmakerutil.execCmd(cmd)
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


def composeUrlList(doRenderJs, listUrlList, itemCaptureScript, userAgent, referer):
    #print("# composeUrlList(%s, %s, %s, %s)" % (doRenderJs, listUrlList, itemCaptureScript, referer))
    resultList = []
    
    listUrls = feedmakerutil.getAllConfigValues(listUrlList, "list_url")
    for listUrl in listUrls:
        urlList = extractUrls(doRenderJs, listUrl, itemCaptureScript, userAgent, referer)
        resultList.extend(urlList)
    return resultList


def main():
    totalList = []

    # configuration
    config = feedmakerutil.readConfig()
    if config == None:
        die("can't find conf.xml nor get config element")
    collectionConf = feedmakerutil.getConfigNode(config, "collection")
    doRenderJs = feedmakerutil.getConfigNode(collectionConf, "render_js")
    print("# render_js: ", doRenderJs)

    listUrlList = feedmakerutil.getConfigNode(collectionConf, "list_url_list")
    if listUrlList:
        print("# list_url_list: ", listUrlList)

    itemCaptureScript = feedmakerutil.getConfigValue(collectionConf, "item_capture_script")
    if not itemCaptureScript or itemCaptureScript == "":
        itemCaptureScript = "./capture_item_link_title.pl"
        if not os.path.isfile(itemCaptureScript):
            itemCaptureScript = "./capture_item_link_title.py"
    print("# item_capture_script: %s" % (itemCaptureScript))
    itemCaptureScriptProgram = itemCaptureScript.split(" ")[0]
    if not itemCaptureScriptProgram or not os.path.isfile(itemCaptureScriptProgram) or not os.access(itemCaptureScriptProgram, os.X_OK):
        die("can't execute '%s'" % (itemCaptureScriptProgram))

    userAgent = feedmakerutil.getConfigValue(collectionConf, "user_agent")
    referer = feedmakerutil.getConfigValue(collectionConf, "referer")

    # collect items from specified url list
    print("# collecting items from specified url list...")
    totalList = composeUrlList(doRenderJs, listUrlList, itemCaptureScript, userAgent, referer)
    for (link, title) in totalList:
        print("%s\t%s" % (link, title))

    return 0


if __name__ == "__main__":
    sys.exit(main())
