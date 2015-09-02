#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
from bs4 import BeautifulSoup, Comment


def getFirstTokenFromPath(pathStr):
    #print "getFirstTokenFromPath(pathStr='%s')" % (pathStr)
    isAnywhere = False
    if pathStr[0:2] == "//":
        isAnywhere = True
    tokens = pathStr.split("/")
    i = 0
    for token in tokens:
        #print "tokens[%d]='%s'" % (i, token)
        i = i + 1
        if token in ("", "html", "body"):
            continue
        else:
            # 첫번째 유효한 토큰만 꺼내옴
            break

    # 해당 토큰에 대해 정규식 매칭 시도
    pattern = re.compile(r"((?P<name>\w+)(?:\[(?P<idx>\d+)\])?|\*\[@id=\"(?P<id>\w+)\"\])")
    m = pattern.match(token)
    if m != None:
        id = m.group("id")
        name = m.group("name")
        idx = m.group("idx")
    else:
        return (None, None, None, None, False)

    # id, name, idx, path의 나머지 부분, isAnywhere을 반환
    return (id, name, idx, "/".join(tokens[i:]), isAnywhere)


def getNodeWithPath(node, pathStr):
    if node == None:
        return None
    #print "\n# getNodeWithPath(node='%s', pathStr='%s')" % (node.name, pathStr)
    nodeList = []

    (nodeId, name, idx, nextPathStr, isAnywhere) = getFirstTokenFromPath(pathStr)
    #print "nodeId='%s', name='%s', idx=%s, nextPathStr='%s', isAnywhere=%s" % (nodeId, name, idx, nextPathStr, isAnywhere)

    if nodeId != None:
        #print "searching with id"
        # 특정 id로 노드를 찾아서 현재 노드에 대입
        nodes = node.find_all(attrs={"id":nodeId})
        #print "nodes=", nodes
        if nodes == None or nodes == []:
            print("error, no id matched")
            sys.exit(-1)
        if len(nodes) > 1:
            print("error, two or more id matched")
            sys.exit(-1)
        #print "found! node=%s" % (nodes[0].name)
        nodeList.append(nodes[0])
        resultNodeList = getNodeWithPath(nodes[0], nextPathStr)
        if resultNodeList != None:
            nodeList = resultNodeList
    else:
        #print "searching with name and index"
        nodeId = ""
        if name == None:
            return None
        if idx != None:
            idx = int(idx)

        #print "#children=%d" % (len(node.contents))
        i = 1
        for child in node.contents:
            if hasattr(child, 'name'):
                #print "i=%d child='%s', idx=%s" % (i, child.name, idx)
                # 이름이 일치하거나 //로 시작한 경우
                if child.name == name:
                    #print "name matched! i=%d child='%s', idx=%s" % (i, child.name, idx)
                    if idx == None or i == idx:
                        # 인덱스가 지정되지 않았거나, 지정되었고 인덱스가 일치할 때
                        if nextPathStr == "":
                            # 단말 노드이면 현재 일치한 노드를 반환
                            #print "*** append! child='%s'" % (child.name)
                            nodeList.append(child)
                        else:
                            # 중간 노드이면 recursion
                            #print "*** recursion ***"
                            resultNodeList = getNodeWithPath(child, nextPathStr)
                            #print "\n*** extend! #resultNodeList=", len(resultNodeList)
                            if resultNodeList != None:
                                nodeList.extend(resultNodeList)
                    if idx != None and i == idx:
                        break
                    # 이름이 일치했을 때만 i를 증가시킴
                    i = i + 1
                if isAnywhere == True:
                    #print "can be anywhere"
                    resultNodeList = getNodeWithPath(child, name)
                    if resultNodeList != None:
                        nodeList.extend(resultNodeList)
                    #print "nodeList=", nodeList
    return nodeList


def readStdin():
    import io
    inputStream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="ignore")
    lineList = []
    for line in inputStream:
        lineList.append(line)
        
    return "".join(lineList)


def readFile(file):
    if file != "":
        fp = open(file, "r")
    else:
        fp = sys.stdin
    lineList = []
    lineList = fp.readlines()
    fp.close()
    return "".join(lineList)


def readConfig():
    import xml.dom.minidom
    if 'FEED_MAKER_CONF_FILE' in os.environ:
        configFile = os.environ['FEED_MAKER_CONF_FILE']
    else:
        configFile = "conf.xml"
    return xml.dom.minidom.parse(configFile)


def getAllConfigNodes(node, key):
    return node.getElementsByTagName(key);


def getConfigNode(node, key):
    nodes = getAllConfigNodes(node, key)
    if not nodes:
        return None
    return nodes[0]


def getValueFromConfig(node):
    if node and node.childNodes:
        return node.childNodes[0].nodeValue
    return None


def getConfigValue(node, key):
    return getValueFromConfig(getConfigNode(node, key))


def getAllConfigValues(node, key):
    result = []
    for item in getAllConfigNodes(node, key):
        itemValue = getValueFromConfig(item)
        if itemValue != None:
            result.append(itemValue)
    return result


def getUrlPrefix(url):
    protocol = "http://"
    protocolLen = len(protocol)
    if url[:protocolLen] == protocol:
        # http:// 뒷쪽부터 /의 마지막 위치를 찾아냄
        index = url.rfind('/', protocolLen)
        return url[:index + 1]
    return ""


def getUrlDomain(url):
    protocol = "http://"
    protocolLen = len(protocol)
    if url[:protocolLen] == protocol:
        index = url.find('/', protocolLen)
        return url[:index + 1]
    return ""


def concatenateUrl(fullUrl, url2):
    if len(url2) > 0 and url2[0] == '/':
        url1 = getUrlDomain(fullUrl)
    else:
        url1 = getUrlPrefix(fullUrl)
    if len(url1) > 0 and len(url2) > 0:
        if url1[-1] == '/' and url2[0] == '/':
            return url1 + url2[1:]
    return url1 + url2


def getMd5Name(str):
    import hashlib
    return hashlib.md5(str.encode()).hexdigest()


def err(msg):
    sys.stderr.write("Error: %s\n" % msg)


def die(msg):
    sys.stderr.write("Error: %s\n", msg)
    sys.exit(-1)
    

def warn(msg):
    sys.stderr.write("Warning: %s\n" % msg)


def execCmd(cmd):
    import subprocess
    try:
        result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
    except subprocess.SubprocessError:
        return False
    return result.decode(encoding="utf-8")


def removeFile(filePath):
    if os.path.isfile(filePath):
        os.remove(filePath)


