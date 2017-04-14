#!/usr/bin/env python3
#-*- coding: utf-8 -*-


import os
import sys
import re
import pathlib
import sqlite3
import feedmakerutil


dbName = "problems.db"
statusTable = "xml_status"
aliasMapTable = "feed_alias_name"
feedAccessFile = os.environ["FEED_MAKER_CWD"] + "/logs/feed_access.txt"
htaccessFile = os.environ["FEED_MAKER_WWW_FEEDS"] + "/../.htaccess"
publicHtmlPath = os.environ["FEED_MAKER_WWW_FEEDS"]
feedMakerPath = os.environ["FEED_MAKER_CWD"]



def createXmlStatusTable(c):
    queryStr = "DROP TABLE IF EXISTS %s" % (statusTable)
    c.execute(queryStr)
    queryStr = "CREATE TABLE %s (feed_alias VARCHAR(256) PRIMARY KEY, http_request INT NOT NULL DEFAULT 0, htaccess INT NOT NULL DEFAULT 0, public_html INT NOT NULL DEFAULT 0, feedmaker INT NOT NULL DEFAULT 0, last_request_date date)" % (statusTable)
    c.execute(queryStr)

    queryStr = "DROP TABLE IF EXISTS %s" % (aliasMapTable)
    c.execute(queryStr)
    queryStr = "CREATE TABLE %s (feed_alias VARCHAR(256) PRIMARY KEY, feed_name VARCHAR(256) NOT NULL DEFAULT '')" % (aliasMapTable)
    c.execute(queryStr)
    queryStr = "CREATE INDEX feed_name_idx on %s (feed_name)" % (aliasMapTable)
    c.execute(queryStr)
    
    
def updateHtaccessStatus(c):
    lineList = feedmakerutil.readFileAsLineList(htaccessFile)
    for line in lineList:
        m = re.search(r'^RewriteRule\s+\^(?P<feed_alias>[^\t]+)\\\.xml\$\s+xml/(?P<feed_name>[^\t]+)\\\.xml\s*$', line)
        if m:
            feedAlias = re.sub(r'\\\.', '.', m.group("feed_alias"))
            feedName = re.sub(r'\\\.', '.', m.group("feed_name"))
            #print("htaccess: ", feedAlias, feedName)
            
            queryStr = "INSERT OR IGNORE INTO %s (feed_alias, feed_name) VALUES ('%s', '%s')" % (aliasMapTable, feedAlias, feedName)
            c.execute(queryStr)
            queryStr = "UPDATE %s SET feed_name = '%s' WHERE feed_alias = '%s'" % (aliasMapTable, feedName, feedAlias)
            c.execute(queryStr)

            queryStr = "INSERT OR IGNORE INTO %s (feed_alias, htaccess) VALUES ('%s', %d)" % (statusTable, feedAlias, 1)
            c.execute(queryStr)
            queryStr = "UPDATE %s SET htaccess = %d WHERE feed_alias = '%s'" % (statusTable, 1, feedAlias)
            c.execute(queryStr)


def updateFeedAccessStatus(c):
    lineList = feedmakerutil.readFileAsLineList(feedAccessFile)
    for line in lineList:
        m = re.search(r'(?P<date>\d+)\t(?P<feed_name>[^\t]+)\t(?P<http_status>\d+)', line)
        if m:
            date = m.group("date")
            feedName = m.group("feed_name")
            #httpStatus = m.group("http_status")
            #print("http_request: ", feedName)
            
            for row in c.execute("SELECT feed_alias FROM feed_alias_name WHERE feed_name = '%s'" % (feedName)):
                feedAlias = row[0]
                queryStr = "INSERT OR IGNORE INTO %s (feed_alias, http_request, last_request_date) VALUES ('%s', %d, '%s')" % (statusTable, feedAlias, 1, date)
                c.execute(queryStr)
                queryStr = "UPDATE %s SET http_request = %d, last_request_date = '%s' WHERE feed_alias = '%s'" % (statusTable, 1, date, feedAlias)
                c.execute(queryStr)

            
def updatePublicHtmlStatus(c):
    p = pathlib.Path(publicHtmlPath)
    feedList = list(p.glob('*.xml'))
    for feed in feedList:
        if re.search(r'(^_|^conf.xml$)', feed.name):
            continue
        feedName = re.sub(r'\.xml', '', feed.name)
        #print("public_html: ", feedName)

        for row in c.execute("SELECT feed_alias FROM feed_alias_name WHERE feed_name = '%s'" % (feedName)):
            feedAlias = row[0]
            queryStr = "INSERT OR IGNORE INTO %s (feed_alias, public_html) VALUES ('%s', %d)" % (statusTable, feedAlias, 1)
            c.execute(queryStr)
            queryStr = "UPDATE %s SET public_html = %d WHERE feed_alias = '%s'" % (statusTable, 1, feedAlias)
            c.execute(queryStr)


def updateFeedMakerStatus(c):
    p = pathlib.Path(feedMakerPath)
    feedList = list(p.glob('*/*/*.xml'))
    for feed in feedList:
        if re.search(r'(^_|^conf.xml$)', feed.name):
            continue
        m = re.match(r'(?P<feed_name>\S+)\.xml', feed.name)
        if m:
            feedName = m.group("feed_name")
            #print("feed_maker: ", feedName)

            for row in c.execute("SELECT feed_alias FROM feed_alias_name WHERE feed_name = '%s'" % (feedName)):
                feedAlias = row[0]
                queryStr = "INSERT OR IGNORE INTO %s (feed_alias, feedmaker) VALUES ('%s', %d)" % (statusTable, feedAlias, 1)
                c.execute(queryStr)
                queryStr = "UPDATE %s SET feedmaker = %d WHERE feed_alias = '%s'" % (statusTable, 1, feedAlias)
                c.execute(queryStr)


def printMismatchFeeds(c):
    queryStr = "SELECT s.feed_alias, feed_name, http_request, htaccess, public_html, feedmaker, last_request_date FROM xml_status s JOIN feed_alias_name a ON s.feed_alias = a.feed_alias WHERE http_request != 1 OR htaccess != 1 OR public_html != 1 OR feedmaker != 1 ORDER BY http_request, htaccess, public_html, feedmaker"
    print("<table>")

    print("<tr>")
    print("<th>외부</th>")
    print("<th>내부</th>")
    print("<th>http request</th>")
    print("<th>htaccess</th>")
    print("<th>public_html</th>")
    print("<th>feedmaker</th>")
    print("<th>last request date</th>")
    print("<th>관리</th>")
    print("</tr>")
    
    print("<tr>")
    for row in c.execute(queryStr):
        feedAlias = row[0]
        feedName = row[1]
        httpRequest = row[2]
        htaccess = row[3]
        publicHtml = row[4]
        feedmaker = row[5]
        lastRequestDate = row[6]

        if feedAlias == feedName:
            feedAlias = ""
        if not lastRequestDate:
            lastRequestDate = ""
        
        print("<tr>")
        print("<td class='external'><a href='https://terzeron.net/%s.xml' target='_blank'>%s</a></td>" % (feedAlias, feedAlias))
        print("<td class='internal'><a href='https://terzeron.net/xml/%s.xml' target='_blank'>%s</a></td>" % (feedName, feedName))
        print("<td class='http_request'>%s</td>" % (httpRequest == 1 and "O" or "X"))
        print("<td class='htaccess'>%s</td>" % (htaccess == 1 and "O" or "X"))
        print("<td class='public_html'>%s</td>" % (publicHtml == 1 and "O" or "X"))
        print("<td class='feedmaker'>%s</td>" % (feedmaker == 1 and "O" or "X"))
        print("<td class='last_request_date'>%s</td>" % lastRequestDate)
        print("<td class='management'><a href='add_feed.php?feed_name=%s'>%s</a></td>" % (feedName, feedName))
        print("</tr>")
    print("</table>")
    print("</div>")
    print("</div>")

            
def main():
    conn = sqlite3.connect(dbName)
    c = conn.cursor()

    createXmlStatusTable(c)

    updateHtaccessStatus(c)
    updateFeedAccessStatus(c)
    updatePublicHtmlStatus(c)
    updateFeedMakerStatus(c)
    conn.commit()
    
    printMismatchFeeds(c)

    conn.close()

    
if __name__ == "__main__":
    main()
