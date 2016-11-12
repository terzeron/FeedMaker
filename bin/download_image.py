#!/usr/bin/env python3

import sys
import os
import re
from feedmakerutil import debug_print
import feedmakerutil


def getCacheFileName(pathPrefix, imgUrl, imgExt, postfix=None, index=None):
    postfixStr = ""; 
    if postfix:
        postfixStr = "_" + postfix
    
    indexStr = ""
    if index:
        indexStr = "." + index
                         
    if re.search(r'^https?://', imgUrl) and imgExt:
        return pathPrefix + "/" + feedmakerutil.getMd5Name(imgUrl) + postfixStr + indexStr + "." + imgExt
     
    return pathPrefix + "/" + imgUrl


def downloadImage(pathPrefix, imgUrl, imgExt, pageUrl):
    cacheFile = getCacheFileName(pathPrefix, imgUrl, imgExt)
    if os.path.isfile(cacheFile) and os.stat(cacheFile).st_size > 0:
        return True
    cmd = 'wget.sh --download "%s" --referer "%s" "%s"' % (cacheFile, pageUrl, imgUrl)
    debug_print("<!-- %s -->" % (cmd))
    result = feedmakerutil.execCmd(cmd)
    debug_print("<!-- %s -->" % (result))
    if os.path.isfile(cacheFile) and os.stat(cacheFile).st_size > 0:
        return cacheFile
    return False


def main():
    cmd = "basename " + os.getcwd()
    feedName = feedmakerutil.execCmd(cmd).rstrip()
    imgUrlPrefix = "http://terzeron.net/xml/img/" + feedName
    pathPrefix = os.environ["FEED_MAKER_WWW_FEEDS"] + "/img/" + feedName

    imgPrefix = ""
    img_index = -1
    imgExt = "jpg"
    num_units = 25

    url = sys.argv[1]
    cmd = ""
    result = ""

    feedmakerutil.makePath(pathPrefix)

    lineList = feedmakerutil.readStdinAsLineList()
    for line in lineList:
        line = line.rstrip()
        m = re.search(r'''
        (?P<preText>.*)
        <img 
        \s*
        src=
        (["\'])
        (?P<imgUrl>[^"\']+)
        (["\'])
        (\s*width=["\']\d+%?["\'])?
        /?>
        (?P<postText>.*)
        ''', line, re.VERBOSE)
        if m:
            preText = m.group("preText")
            imgUrl = m.group("imgUrl")
            postText = m.group("postText")
            
            m = re.search(r'^\s*$', preText)
            if not m:
                print(preText)

            # download
            cacheFile = downloadImage(pathPrefix, imgUrl, imgExt, url)
            if cacheFile:
                cacheUrl = feedmakerutil.getCacheUrl(imgUrlPrefix, imgUrl, imgExt)
                debug_print("<!-- %s -> %s / %s -->" % (imgUrl, cacheFile, cacheUrl))
                print("<img src='%s'/>" % (cacheUrl))
            else:
                print("<img src='%s' alt='not exist or size 0'/>" % (imgUrl))

            m = re.search(r'^\s*$', postText)
            if not m:
                print(postText)
        else:
            print(line)

            
if __name__ == "__main__":
    main()
