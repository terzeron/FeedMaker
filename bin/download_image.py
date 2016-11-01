#!/usr/bin/env python3

import sys
import os
import re
import feedmakerutil

def getCacheUrl(urlPrefix, imgUrl, imgExt, postfix=None, index=None):
    postfixStr = ""
    if postfix:
        postfixStr = "_" + postfix
    
    indexStr = ""
    if index:
        indexStr = "." + index
    
    if re.search(r'^https?://', imgUrl) and imgExt:
        return urlPrefix + "/" + feedmakerutil.getMd5Name(imgUrl) + postfixStr + indexStr + "." + imgExt

    return urlPrefix + "/" + imgUrl


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
    cmd = '[ -f "%s" -a -s "%s" ] || wget.sh --download "%s" --referer "%s" "%s"' % (cacheFile, cacheFile, cacheFile, pageUrl, imgUrl)
    #print("<!-- cmd -->")
    result = feedmakerutil.execCmd(cmd)
    #print("<!-- result -->")
    return result


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
            if downloadImage(pathPrefix, imgUrl, imgExt, url) == False:
                continue
            
            cacheFile = getCacheFileName(pathPrefix, imgUrl, imgExt)
            cacheUrl = getCacheUrl(imgUrlPrefix, imgUrl, imgExt)
            #print("<!-- imgUrl -> cacheFile / cacheUrl -->")
            print("<img src='%s'/>" % (cacheUrl))

            m = re.search(r'^\s*$', postText)
            if not m:
                print(postText)
        else:
            print(line)

            
if __name__ == "__main__":
    main()
