#!/usr/bin/env python3

import sys
import os
import re
import time
import datetime
import getopt
import subprocess
from feedmakerutil import warn, die
import feedmakerutil
import PyRSS2Gen


SECONDS_PER_DAY = 60 * 60 * 24
MIN_CONTENT_LENGTH = 64
MAX_CONTENT_LENGTH = 64 * 1024
MAX_NUM_DAYS = 7


def getPubDateStr(fileName):
    if os.path.isfile(fileName):
        ts = os.stat(fileName).st_mtime
    else:
        ts = datetime.datetime.now().timestamp()
    dt = datetime.datetime.fromtimestamp(float(ts))
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def getRssDateStr(ts=datetime.datetime.now().timestamp()):
    dt = datetime.datetime.fromtimestamp(float(ts))
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def getDateStr(ts=datetime.datetime.now().timestamp()):
    dt = datetime.datetime.fromtimestamp(float(ts))
    return dt.strftime("%Y%m%d")


def getListFileName(listDir, dateStr):
    return "%s/%s.txt" % (listDir, dateStr)


def getNewFileName(url):
    return "html/" + feedmakerutil.getShortMd5Name(url) + ".html"


def getCollectionConfigs(config):
    collectionConf = feedmakerutil.getConfigNode(config, "collection")
    if collectionConf == None:
        die("can't get collection element")
    doIgnoreOldList = feedmakerutil.getConfigValue(collectionConf, "do_ignore_old_list")
    doIgnoreOldList = bool("true" == doIgnoreOldList)
    isCompleted = feedmakerutil.getConfigValue(collectionConf, "is_completed")
    isCompleted = bool("true" == isCompleted)
    sortFieldPattern = feedmakerutil.getConfigValue(collectionConf, "sort_field_pattern")
    unitSizePerDay = feedmakerutil.getConfigValue(collectionConf, "unit_size_per_day")
    unitSizePerDay = float(unitSizePerDay) if unitSizePerDay else None
    postProcessScript = feedmakerutil.getConfigValue(collectionConf, "post_process_script")
    return (doIgnoreOldList, isCompleted, sortFieldPattern, unitSizePerDay, postProcessScript)


def getExtractionConfigs(config):
    extractionConf = feedmakerutil.getConfigNode(config, "extraction")
    if extractionConf == None:
        die("can't get extraction element")
    postProcessScript = feedmakerutil.getConfigValue(extractionConf, "post_process_script")
    postProcess2Script = feedmakerutil.getConfigValue(extractionConf, "post_process2_script")
    doRenderJs = feedmakerutil.getConfigValue(extractionConf, "render_js")
    doForceSleepBetweenArticles = feedmakerutil.getConfigValue(extractionConf, "force_sleep_between_articles")
    doBypassElementExtraction = feedmakerutil.getConfigValue(extractionConf, "bypass_element_extraction")
    reviewPointThreshold = feedmakerutil.getConfigValue(extractionConf, "review_point_threshold")
    return (postProcessScript, postProcess2Script, doRenderJs, doForceSleepBetweenArticles, doBypassElementExtraction, reviewPointThreshold)


def getNotificationConfigs(config):
    notiConf = feedmakerutil.getConfigNode(config, "notification")
    email = feedmakerutil.getConfigNode(notiConf, "email")
    recipient = feedmakerutil.getConfigValue(email, "recipient")
    subject = feedmakerutil.getConfigValue(email, "subject")
    return (email, recipient, subject)

    
def getRecentList(listDir, postProcessScript):
    print("# getRecentList(%s)" % (listDir))

    dateStr = getDateStr()
    newListFileName = getListFileName(listDir, dateStr)
    if postProcessScript:
        postProcessCmd = '%s "%s"' % (postProcessScript, newListFileName)
    else:
        postProcessCmd = 'remove_duplicate_line.py > "%s"' % (newListFileName)

    cmd = "collect_new_list.py | " + postProcessCmd
    print(cmd)
    result = feedmakerutil.execCmd(cmd)
    if result == False:
        die("can't collect new list from the page")

    with open(newListFileName, 'r', encoding='utf-8') as inFile:
        uniqList = []
        for line in inFile:
            line = line.rstrip()
            uniqList.append(line)

    return uniqList


def readOldListFromFile(listDir, isCompleted):
    print("# readOldListFromFile(listDir=%s, isCompleted=%r)" % (listDir, isCompleted))

    resultList = []
    ts = datetime.datetime.now().timestamp()
    if isCompleted == False:
        # 아직 진행 중인 피드에 대해서는 현재 날짜에 가장 가까운
        # 과거 리스트 파일 1개를 찾아서 그 안에 기록된 리스트를 꺼냄

        listFile = ""
        i = 0
        # 과거까지 리스트가 존재하는지 확인
        for i in range(MAX_NUM_DAYS):
            dateStr = getDateStr(ts - i * SECONDS_PER_DAY)
            listFile = getListFileName(listDir, dateStr)
            print(listFile)
            # 오늘에 가장 가까운 리스트가 존재하면 탈출
            if os.path.isfile(listFile):
                # read the old list
                with open(listFile, 'r', encoding='utf-8') as inFile:
                    for line in inFile:
                        line = line.rstrip()
                        resultList.append(line)
    else:
        # 이미 완료된 피드에 대해서는 기존 리스트를 모두 취합함
        for entry in os.scandir(listDir):
            if entry.name.startswith(".") and entry.is_file():
                continue

            filePath = listDir + "/" + entry.name
            with open(filePath, 'r', encoding='utf-8') as inFile:
                for line in inFile:
                    line = line.rstrip()
                    resultList.append(line)
    return list(set(resultList))


def getRssConfigValues(rssConfig):
    rssTitle = feedmakerutil.getConfigValue(rssConfig, "title")
    rssDescription = feedmakerutil.getConfigValue(rssConfig, "description")
    rssGenerator = feedmakerutil.getConfigValue(rssConfig, "generator")
    rssCopyright = feedmakerutil.getConfigValue(rssConfig, "copyright")
    rssLink = feedmakerutil.getConfigValue(rssConfig, "link")
    rssLanguage = feedmakerutil.getConfigValue(rssConfig, "language")
    rssNoItemDesc = feedmakerutil.getConfigValue(rssConfig, "no_item_desc")
    return (rssTitle, rssDescription, rssGenerator, rssCopyright, rssLink, rssLanguage, rssNoItemDesc)
    

def generateRssFeed(config, feedList, rssFileName):
    print("# generateRssFeed(%s)" % (rssFileName))

    rssConfig = feedmakerutil.getConfigNode(config, "rss")
    if rssConfig == None:
        die("can't get rss element")
    
    (rssTitle, rssDescription, rssGenerator, rssCopyright, rssLink, rssLanguage, rssNoItemDesc) = getRssConfigValues(rssConfig)

    lastBuildDateStr = getRssDateStr()
    dateStr = getDateStr()
    tempRssFileName = rssFileName + "." + dateStr

    rssItems = []
    for feedItem in feedList:
        (articleUrl, articleTitle) = feedItem.split('\t')
        newFileName = getNewFileName(articleUrl)
        guid = feedmakerutil.getShortMd5Name(articleUrl)
        pubDateStr = getRssDateStr()
        
        content = ""
        with open(newFileName, 'r', encoding='utf-8') as inFile:
            print("adding '%s' to the result" % (newFileName))
            for line in inFile:
                content += line
                # restrict big contents
                if len(content) >= MAX_CONTENT_LENGTH:
                    content = "<strong>본문이 너무 길어서 전문을 싣지 않았습니다. 다음의 원문 URL을 참고해주세요.</strong><br/>" + content
                    break
            rssItems.append(
                PyRSS2Gen.RSSItem(
                    title=articleTitle,
                    link=articleUrl,
                    guid=articleUrl,
                    pubDate=pubDateStr,
                    description=content
                )
            )

    rss = PyRSS2Gen.RSS2(
        title=rssTitle,
        link=rssLink,
        description=rssDescription,
        lastBuildDate=lastBuildDateStr,
        items=rssItems
    )
    rss.write_xml(open(tempRssFileName, 'w'), encoding='utf-8')

    # 이번에 만들어진 rss 파일이 이전 파일과 내용이 다른지 확인
    isDifferent = False
    if os.path.isfile(rssFileName):
        cmd = 'diff "%s" "%s" | grep -v -Ee \"(^(<|>) <(pubDate|lastBuildDate))|(^---\$)|(^[0-9,]+[a-z][0-9,]+\$)\" | wc -c' % (tempRssFileName, rssFileName)
        print(cmd)
        result = feedmakerutil.execCmd(cmd)
        print(result)
        m = re.search(r'^\s*(?P<numOfDifferentLines>\d+)\s*$', result)
        if m and m.group("numOfDifferentLines") != "0":
            isDifferent = True
    else:
        isDifferent = True

    if isDifferent == True:
        # 이전 파일을 old 파일로 이름 바꾸기
        if os.path.isfile(rssFileName):
            cmd = 'mv -f "%s" "%s.old"' % (rssFileName, rssFileName)
            print(cmd)
            result = feedmakerutil.execCmd(cmd)
            if result == False:
                return False
        # 이번에 만들어진 파일을 정식 파일 이름으로 바꾸기
        if os.path.isfile(tempRssFileName):
            cmd = 'mv -f "%s" "%s"' % (tempRssFileName, rssFileName)
            print(cmd)
            result = feedmakerutil.execCmd(cmd)
    else:
        # 이번에 만들어진 파일을 지우기
        cmd = 'rm -f "%s"' % (tempRssFileName)
        print(cmd)
        result = feedmakerutil.execCmd(cmd)

    if result == False:
        return False
    return True


def appendItemToResult(config, feedList, item, rssFileName):
    fields = item.split('\t')
    reviewPoint = None
    if len(fields) == 2:
        (url, title) = fields
    elif len(fields) == 3:
        (url, title, reviewPoint) = fields
    newFileName = getNewFileName(url)
    size = 0
    if os.path.isfile(newFileName) and os.stat(newFileName).st_size >= MIN_CONTENT_LENGTH:
        # 이미 성공적으로 만들어져 있으니까 피드 리스트에 추가
        print("Success: %s: %s --> %s: %d" % (title, url, newFileName, os.stat(newFileName).st_size))
        feedList.append(item)
    else:
        # 파일이 존재하지 않거나 크기가 작으니 다시 생성 시도
        (postProcessScript, postProcess2Script, doRenderJs, doForceSleepBetweenArticles, doBypassElementExtraction, reviewPointThreshold) = getExtractionConfigs(config)
        
        cmd = ""
        postProcessCmd = ""

        if postProcessScript:
            postProcessCmd = '| %s "%s"' % (postProcessScript, url)
            if postProcess2Script:
                postProcessCmd += ' | %s "%s"' % (postProcess2Script, url)
        
        option = ""
        if "true" == doRenderJs:
            option = "--render-js"
        
        #print("title=%s, reviewPoint=%d, reviewPointThreshold=%f" % (title, reviewPoint, reviewPointThreshold))
        if reviewPoint and reviewPointThreshold and reviewPoint > reviewPointThreshold:
            # 일반적으로 평점이 사용되지 않는 경우나
            # 평점이 기준치를 초과하는 경우에만 추출
            warn("ignore an article due to the low score")
            return 0

        extractionCmd = '| extract.py "%s"' % (url)
        if "true" == doBypassElementExtraction:
            extractionCmd = ""

        cmd = 'wget.sh %s "%s" %s %s > "%s"' % (option, url, extractionCmd, postProcessCmd, newFileName) 
        print(cmd)
        result = feedmakerutil.execCmd(cmd)
        if result == False:
            die("can't extract HTML elements")
        
        md5Name = feedmakerutil.getShortMd5Name(url)
        size = os.stat(newFileName).st_size
        if size > 0:
            cmd = 'echo "<img src=\'http://terzeron.net/img/1x1.jpg?feed=%s&item=%s\'/>" >> "%s"' % (rssFileName, md5Name, newFileName)
            print(cmd)
            result = feedmakerutil.execCmd(cmd)
            if result == False:
                die("can't append page view logging tag")
        
        size = os.stat(newFileName).st_size
        if size < MIN_CONTENT_LENGTH:
            # 피드 리스트에서 제외
            warn("%s: %s --> %s: %d (< %d byte)" % (title, url, newFileName, size, MIN_CONTENT_LENGTH))
            return 0
        else:
            # 피드 리스트에 추가
            print("Success: %s: %s --> %s: %d" % (title, url, newFileName, size))
            feedList.append(item)

        if "true" == doForceSleepBetweenArticles:
            time.sleep(1)


def diffOldAndRecent(config, recentList, oldList, feedList, rssFileName):
    print("# diffOldAndRecent(len(recentList)=%d, len(oldList)=%d), len(feedList)=%d, rssFileName=%s" % (len(recentList), len(oldList), len(feedList), rssFileName))
    oldMap = {}
    for old in oldList:
        if re.search(r'^\#', old):
            continue
        (url, title) = old.split('\t')
        oldMap[url] = title
    #print(len(oldList))

    # differentiate
    resultList = []
    for recent in recentList:
        if re.search(r'^\#', recent):
            continue
        
        (url, title) = recent.split('\t')
        if url not in oldMap:
            resultList.append(recent)
            print("not exists %s" % (recent))
        else:
            print("exists %s" % (recent))

    # collect items to be generated as RSS feed
    print("Appending %d new items to the feed list" % (len(resultList)))
    for newItem in reversed(resultList):
        if re.search(r'^\#', newItem):
            continue
        appendItemToResult(config, feedList, newItem, rssFileName)
    
    print("Appending %d old items to the feed list" % (len(oldList)))
    for oldItem in reversed(oldList):
        if re.search(r'^\#', oldItem):
            continue
        appendItemToResult(config, feedList, oldItem, rssFileName)

    if len(feedList) == 0:
        print("Notice: 새로 추가된 feed가 없으므로 결과 파일을 변경하지 않음")
        return False
    return True

    
def getStartIdx(fileName):
    print("# getStartIdx(%s)" % (fileName))

    if os.path.isfile(fileName):
        with open(fileName, 'r', encoding='utf-8') as inFile:
            line = inFile.readline()
            startIdx = 0
            mtime = 0
            m = re.search(r'(?P<startIdx>\d+)\t(?P<mtime>\d+)', line)
            if m:
                startIdx = int(m.group("startIdx"))
                mtime = int(m.group("mtime"))
                
                print("start index: %d" % (startIdx))
                print("last modified time: %d, %s" % (mtime, getRssDateStr(mtime)))
                return (startIdx, mtime)

    # 처음 생성 시
    writeNextStartIdx(fileName, 0)
    ts = datetime.datetime.now().timestamp()
    return (0, int(ts))


def writeNextStartIdx(fileName, nextStartIdx):
    print("# writeNextStartIdx(%s, %d)" % (fileName, nextStartIdx))

    ts = datetime.datetime.now().timestamp()
    with open(fileName, 'w', encoding='utf-8') as outFile:
        print("next start index: %d" % (nextStartIdx))
        print("current time: %d, %s" % (ts, getRssDateStr(ts)))
        outFile.write("%d\t%d\n" % (int(nextStartIdx), int(ts)))


def printUsage():
    print("usage:\t%s\t<config file> <rss file>" % (sys.argv[0]))
    print()


def cmpIntOrStr(a, b):
    m1 = re.search(r'^\d+$', a["sf"])
    m2 = re.search(r'^\d+$', b["sf"])
    if m1 and m2:
        return (int(a["sf"]) - int(b["sf"]))
    else:
        if a["sf"] < b["sf"]:
            return -1
        elif a["sf"] > b["sf"]:
            return 1
        else:
            return 0


def cmpToKey(mycmp):
    class K:
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K

    
def main():
    print("=========================================================")
    print(" " + os.getcwd() + " ")
    print("=========================================================")

    doCollectByForce = False
               
    optlist, args = getopt.getopt(sys.argv[1:], "c")
    for o, a in optlist:
        if o == '-c':
            doCollectByForce = True
               
    if len(args) == 0:
        printUsage()
        sys.exit(-1)
               
    rssFileName = args[0]

    config = feedmakerutil.readConfig()
    if config == None:
        die("can't find conf.xml file nor get config element")
    (doIgnoreOldList, isCompleted, sortFieldPattern, unitSizePerDay, postProcessScript) = getCollectionConfigs(config)
    print("doIgnoreOldList=%r, isCompleted=%r, sortFieldPatter=%s, unitSizePerDay=%f, postProcessScript=%s" % (doIgnoreOldList, isCompleted, sortFieldPattern, unitSizePerDay if unitSizePerDay else -1, postProcessScript))
    
    # -c 옵션이 지정된 경우, 설정의 isCompleted 값 무시
    if doCollectByForce == True:
        isCompleted = False

    listDir = "newlist"
    feedmakerutil.makePath(listDir)
    feedmakerutil.makePath("html")

    # 과거 피드항목 리스트를 가져옴
    feedList = []
    oldList = readOldListFromFile(listDir, isCompleted)
    if not oldList:
        warn("can't get old list!")

    # 완결여부 설정값 판단 
    recentList = []
    if isCompleted == True:
        # 완결된 피드는 적재된 리스트에서 일부 피드항목을 꺼내옴

        # 오름차순 정렬
        feedIdSortFieldList = []
        feedItemExistenceSet = set([])

        for i, oldItem in enumerate(oldList):
            sortField = ""
            m = re.search(sortFieldPattern, oldItem)
            if m:
                sortField = m.group(1)
            else:
                warn("can't match the pattern /%s/" % (sortFieldPattern))
            
            if oldItem not in feedItemExistenceSet:
                feedIdSortField = {}
                feedIdSortField["id"] = i
                feedIdSortField["sf"] = sortField
                feedItemExistenceSet.add(oldItem)
                feedIdSortFieldList.append(feedIdSortField)

        sortedFeedList = sorted(feedIdSortFieldList, key=cmpToKey(cmpIntOrStr))
        idxFile = "start_idx.txt"
        windowSize = 10 # feedly initial max window size
        (startIdx, mtime) = getStartIdx(idxFile)
        endIdx = startIdx + windowSize
        for i, feed in enumerate(sortedFeedList):
            if i >= startIdx and i < endIdx:
                feedList.append(oldList[feed["id"]])
                (url, title) = oldList[feed["id"]].split("\t")
                guid = feedmakerutil.getShortMd5Name(url)
                print("%s\t%s\t%s" % (url, title, guid))

        ts = datetime.datetime.now().timestamp()
        incrementSize = int(((int(ts) - mtime) * unitSizePerDay) / 86400)
        print("# startIdx=%d, endIdx=%d, current time=%d, mtime=%d, windowSize=%d, incrementSize=%d" % (startIdx, endIdx, int(ts), mtime, windowSize, incrementSize))
        if incrementSize > 0:
            writeNextStartIdx(idxFile, startIdx + incrementSize)
    else:
        # 피딩 중인 피드는 최신 피드항목을 받아옴
        recentList = getRecentList(listDir, postProcessScript)
        if not recentList:
            die("can't get recent list!")
        
        # 과거 피드항목 리스트와 최근 피드항목 리스트를 비교함
        if doIgnoreOldList:
            oldList = []
            feedList = recentList
        
        if diffOldAndRecent(config, recentList, oldList, feedList, rssFileName) == False:
            return -1

    if doCollectByForce == False:
        # generate RSS feed
        if generateRssFeed(config, feedList, rssFileName) == False:
            return -1
    
    # upload RSS feed file
    cmd = 'upload.py %s' % (rssFileName)
    print(cmd)
    result = feedmakerutil.execCmd(cmd)
    print(result)
    if result == False:
        return -1

    m = re.search(r'Upload: success', result)
    if m and doCollectByForce == False:
        # email notification
        (email, recipient, subject) = getNotificationConfigs(config)
        if email and recipient and subject:
            cmd = "| mail -s '%s' '%s'" % (subject, recipient)
            with subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE) as p:
                for feed in recentList:
                    p.write(feed + "\n")
            print("sent a notification in mail")
    return 0


if __name__ == "__main__":
    sys.exit(main())
