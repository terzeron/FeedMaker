#!/usr/bin/env python3


import os
import sys
import re
import getopt
import feedmakerutil


isDebugMode = False

def debug_print(a):
    if isDebugMode:
        print(a)


def getCacheUrl(urlPrefix, url, imgExt, postfix=None, index=None):
    debug_print("# getCacheUrl(%s, %s, %s, %s, %d)" % (urlPrefix, url, imgExt, postfix, index if index else 0))
    resultStr = ""
    postfixStr = ""
    if postfix and postfix != "":
        postfixStr = "_" + str(postfix)
    indexStr = ""
    if index and index != "":
        indexStr = "." + str(index)
    m = re.search(r'http://', url)
    if m and imgExt:
        resultStr = urlPrefix + "/" + feedmakerutil.getMd5Name(url) + postfixStr + indexStr + "." + imgExt
    else:
        resultStr = urlPrefix + "/" + imgUrl
    return resultStr


def getCacheFileName(pathPrefix, url, imgExt, postfix=None, index=None):
    debug_print("# getCacheFileName(%s, %s, %s, %s, %d)" % (pathPrefix, url, imgExt, postfix, index if index else 0))
    resultStr = ""
    postfixStr = "" 
    if postfix and postfix != "":
        postfixStr = "_" + str(postfix)
    indexStr = ""
    if index and index != "":
        indexStr = "." + str(index)
    m = re.search(r'http://', url)
    if m and imgExt:
        resultStr = pathPrefix + "/" + feedmakerutil.getMd5Name(url) + postfixStr + indexStr + "." + imgExt
    else:
        resultStr = pathPrefix + "/" + imgUrl
    debug_print("resultStr=" + resultStr)
    return resultStr


def downloadImage(pathPrefix, imgUrl, imgExt, pageUrl):
    debug_print("# downloadImage(%s, %s, %s, %s)" % (pathPrefix, imgUrl, imgExt, pageUrl))
    cacheFile = getCacheFileName(pathPrefix, imgUrl, imgExt)
    cmd = '[ -f "%s" -a -s "%s" ] || wget.sh --download "%s" --referer "%s" "%s"' % (cacheFile, cacheFile, cacheFile, pageUrl, imgUrl)
    debug_print(cmd)
    result = feedmakerutil.execCmd(cmd)
    debug_print(result)
    if result == False:
        return False
    return cacheFile


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i+n]


def getTotalHeight(imgSizeList):
    debug_print("# getTotalHeight()")
    #
    # calculate the total height
    #
    totalHeight = 0
    for dimension in imgSizeList:
        (width, height) = dimension.split("\t")
        totalHeight = totalHeight + int(height)
    debug_print("<!-- totalHeight=%d -->" % (totalHeight))
    return totalHeight


def downloadImageAndReadMetadata(pathPrefix, imgExt, pageUrl):
    debug_print("# downloadImageAndReadMetadata(%s, %s, %s)" % (pathPrefix, imgExt, pageUrl))
    #
    # read input and collect image files into the list
    # (file name, url and dimension)
    #
    imgFileList = []
    imgUrlList = []
    imgSizeList = []
    lineList = feedmakerutil.readStdinAsLineList()
    for line in lineList:
        m1 = re.search(r"<img src=(?:[\"'])(?P<imgUrl>[^\"']+)(?:[\"'])( width='\d+%?')?/?>", line)
        if m1:
            imgUrl = m1.group("imgUrl")
            debug_print(imgUrl)
            # download
            cacheFile = downloadImage(pathPrefix, imgUrl, imgExt, pageUrl)
            if not cacheFile:
                sys.stderr.write("Error: can't download the image from '%s'\n" % (imgUrl))
                continue
            imgFileList.append(cacheFile)
            imgUrlList.append(imgUrl)
            debug_print("<!-- %s -> %s -->" % (imgUrl, cacheFile))
            cmd = "../../../CartoonSplit/size.py " + cacheFile
            debug_print(cmd)
            result = feedmakerutil.execCmd(cmd)
            if result == False:
                sys.stderr.write("Error: can't get the size of image file '%s', cmd='%s'\n" % (cacheFile, cmd))
                sys.exit(-1)

            m2 = re.search(r"^(?P<width>\d+)\s+(?P<height>\d+)", result)
            if m2:
                width = m2.group("width")
                height = m2.group("height")
                imgSizeList.append("%s\t%s" % (width, height))
                debug_print("<!-- cacheFile=cacheFile, imgUrl=imgUrl, width=width, height=height -->")
        else:
            debug_print(line)
    return (imgFileList, imgUrlList, imgSizeList)


def splitImageList(imgFileList):
    debug_print("# splitImageList()")
    #
    # split array into 4 sub-array
    #
    imgFilePartitionList = []
    partitionSize = int((len(imgFileList) + 3) / 4) 
    debug_print("<!-- length=%d, partitionSize=%d -->" % (len(imgFileList), partitionSize))
    for i in range(int(len(imgFileList) / partitionSize)):
        imgFilePartitionList.append(imgFileList[i * partitionSize : (i+1) * partitionSize])
    debug_print(imgFilePartitionList)
    return imgFilePartitionList


def mergeImageFiles(imgFileList, pathPrefix, imgUrl, imgExt, num):
    debug_print("# mergeImageFiles()")
    #
    # merge mode
    #
    mergedImgFile = getCacheFileName(pathPrefix, imgUrl, imgExt, num)
    cmd  = "../../../CartoonSplit/merge.py " + mergedImgFile + " "
    for cacheFile in imgFileList:
        cmd = cmd + cacheFile + " "
    debug_print(cmd)
    result = feedmakerutil.execCmd(cmd)
    debug_print(result)
    if result == False:
        sys.stderr.write("Error: can't merge the image files, cmd='%s'\n" % (cmd))
        sys.exit(-1)
    return mergedImgFile


def cropImageFile(imgFile):
    debug_print("# cropImagefile()")
    #
    # crop mode (optional)
    #
    cmd = "innercrop -f 4 -m crop \"%s\" \"%s.temp\" && mv -f \"%s.temp\" \"%s\"" % (imgFile, imgFile, imgFile, imgFile)
    debug_print(cmd)
    result = feedmakerutil.execCmd(cmd)
    if result == False:
        sys.stderr.write("Error: can't crop the image file '%s', cmd='%s'\n" % (imgFile, cmd))
        sys.exit(-1)


def removeImageFiles(imgFileList):
    debug_print("# removeImageFiles()")
    #
    # remove the original image
    # 
    cmd = "rm -f "
    for cacheFile in imgFileList:
        cmd = cmd + "'" + cacheFile + "' "
    debug_print(cmd)
    result = feedmakerutil.execCmd(cmd)
    debug_print(result)
    if result == False:
        return False
    return True
        

def splitImageFile(imgFile, numUnits, bgcolorOption, orientationOption):
    debug_print("# splitImageFile(%s, %d, %s, %s)" % (imgFile, numUnits, bgcolorOption, orientationOption))
    #
    # split the image
    #
    cmd = "../../../CartoonSplit/split.py -b 10 -t 0.03 -n %d -i %s %s %s" % (numUnits, orientationOption, bgcolorOption, imgFile)
    debug_print(cmd)
    result = feedmakerutil.execCmd(cmd)
    debug_print(result)
    if result == False:
        sys.stderr.write("Error: can't split the image file, cmd='%s'\n" % (cmd))
        sys.exit(-1)


def printImageFiles(numUnits, pathPrefix, imgUrlPrefix, imgUrl, imgExt, num, doFlipRightToLeft):
    debug_print("# printImageFiles(%d, %s, %s, %s, %s, %d, %s)" % (numUnits, pathPrefix, imgUrlPrefix, imgUrl, imgExt, num if num else 0, doFlipRightToLeft))
    # print the split images
    if not doFlipRightToLeft:
        customRange = range(numUnits)
    else:
        customRange = reversed(range(numUnits))
        for i in customRange:
            splitImgFile = getCacheFileName(pathPrefix, imgUrl, imgExt, num, i + 1)
            debug_print("splitImgFile=" + splitImgFile)
            if os.path.exists(splitImgFile):
                splitImgUrl = getCacheUrl(imgUrlPrefix, imgUrl, imgExt, num, i + 1)
                print("<img src='%s''/>" % (splitImgUrl))


def main():
    global isDebugMode
    
    cmd = "basename " + os.getcwd()
    debug_print(cmd);
    feedName = feedmakerutil.execCmd(cmd).rstrip()
    debug_print("<!-- feedName=%s -->" % (feedName))
    pathPrefix = os.environ["FEED_MAKER_WWW_FEEDS"] + "/img/" + feedName;
    debug_print("<!--- pathPrefix=%s -->" % (pathPrefix))
    feedmakerutil.makePath(pathPrefix)

    imgUrlPrefix = "http://terzeron.net/xml/img/" + feedName
    imgPrefix = ""
    imgIndex = -1
    imgExt = "jpg"
    numUnits = 25
    cmd = ""
    result = ""

    # options
    bgcolorOption = ""
    doMerge = False
    doInnercrop = False
    orientationOption = ""
    doFlipRightToLeft = False
    optlist, args = getopt.getopt(sys.argv[1:], "c:milvd")
    for o, a in optlist:
        if o == "-c":
            bgcolorOption = "-c " + a
        elif o == "-m":
            doMerge = True
        elif o == "-i":
            doInnercrop = True
        elif o == "-l":
            doFlipRightToLeft = True
        elif o == "-v":
            orientationOption = "-v"
            numUnits = 3
        elif o == "-d":
            isDebugMode = True
            
    pageUrl = args[0]
    (imgFileList, imgUrlList, imgSizeList) = downloadImageAndReadMetadata(pathPrefix, imgExt, pageUrl)
    debug_print(imgFileList)
    if len(imgFileList) == 0:
        sys.exit(0)

    if doMerge:
        # merge-split mode
        totalHeight = getTotalHeight(imgSizeList)
        imgFilePartitionList = splitImageList(imgFileList)
    
        num = 1
        for imgFileList in imgFilePartitionList:
            if len(imgFileList) == 0:
                continue

            mergedImgFile = mergeImageFiles(imgFileList, pathPrefix, pageUrl, imgExt, num)

            if doInnercrop:
                cropImageFile(mergedImgFile)
                
            removeImageFiles(imgFileList)
            splitImageFile(mergedImgFile, numUnits, bgcolorOption, orientationOption)
            removeImageFiles([mergedImgFile])
            printImageFiles(numUnits, pathPrefix, imgUrlPrefix, pageUrl, imgExt, num, doFlipRightToLeft)
            num = num + 1
    else:
        # only split mode
        for i in range(len(imgFileList)):
            imgFile = imgFileList[i]
            imgUrl = imgUrlList[i]
            debug_print("imgFile=" + imgFile)
            debug_print("imgUrl=" + imgUrl)
            splitImageFile(imgFile, numUnits, bgcolorOption, orientationOption)
            printImageFiles(numUnits, pathPrefix, imgUrlPrefix, imgUrl, imgExt, None, doFlipRightToLeft)
                

                                 
if __name__ == "__main__":
    main()
