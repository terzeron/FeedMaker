#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import sys
import re
import pathlib
import sqlite3
import json
from feedmakerutil import IO
from typing import List, Dict


db_name = "problems.db"
status_table = "feed_status"
alias_map_table = "feed_alias_name"
feed_access_file = os.environ["FEED_MAKER_WORK_DIR"] + "/logs/feed_access.txt"
htaccess_file = os.environ["FEED_MAKER_WWW_FEEDS_DIR"] + "/../.htaccess"
public_html_path = os.environ["FEED_MAKER_WWW_FEEDS_DIR"]
feedmaker_path = os.environ["FEED_MAKER_WORK_DIR"]


def create_feed_status_table(c) -> None:
    query_str = "DROP TABLE IF EXISTS %s" % status_table
    c.execute(query_str)
    query_str = "CREATE TABLE %s (feed_alias VARCHAR(256) PRIMARY KEY, http_request INT NOT NULL DEFAULT 0, htaccess INT NOT NULL DEFAULT 0, public_html INT NOT NULL DEFAULT 0, feedmaker INT NOT NULL DEFAULT 0, last_request_date date)" % status_table
    c.execute(query_str)

    query_str = "DROP TABLE IF EXISTS %s" % alias_map_table
    c.execute(query_str)
    query_str = "CREATE TABLE %s (feed_alias VARCHAR(256) PRIMARY KEY, feed_name VARCHAR(256) NOT NULL DEFAULT '')" % alias_map_table
    c.execute(query_str)
    query_str = "CREATE INDEX feed_name_idx on %s (feed_name)" % alias_map_table
    c.execute(query_str)


def update_htaccess_status(c) -> None:
    line_list = IO.read_file_as_line_list(htaccess_file)
    for line in line_list:
        m = re.search(r'^RewriteRule\s+\^(?P<feed_alias>[^\t]+)\\\.xml\$\s+xml/(?P<feed_name>[^\t]+)\\\.xml\s*$', line)
        if m:
            feed_alias = re.sub(r'\\\.', '.', m.group("feed_alias"))
            feed_name = re.sub(r'\\\.', '.', m.group("feed_name"))
            # print("htaccess: ", feed_alias, feed_name)

            query_str = "INSERT OR IGNORE INTO %s (feed_alias, feed_name) VALUES ('%s', '%s')" % (
                alias_map_table, feed_alias, feed_name)
            c.execute(query_str)
            query_str = "UPDATE %s SET feed_name = '%s' WHERE feed_alias = '%s'" % (
                alias_map_table, feed_name, feed_alias)
            c.execute(query_str)

            query_str = "INSERT OR IGNORE INTO %s (feed_alias, htaccess) VALUES ('%s', %d)" % (
                status_table, feed_alias, 1)
            c.execute(query_str)
            query_str = "UPDATE %s SET htaccess = %d WHERE feed_alias = '%s'" % (status_table, 1, feed_alias)
            c.execute(query_str)


def update_feed_access_status(c) -> None:
    line_list = IO.read_file_as_line_list(feed_access_file)
    for line in line_list:
        m = re.search(r'(?P<date>\d+)\t(?P<feed_name>[^\t]+)\t(?P<http_status>\d+)', line)
        if m:
            date = m.group("date")
            feed_name = m.group("feed_name")
            # http_status = m.group("http_status")
            # print("http_request: ", feed_name)

            for row in c.execute("SELECT feed_alias FROM feed_alias_name WHERE feed_name = '%s'" % feed_name):
                feed_alias = row[0]
                query_str = "INSERT OR IGNORE INTO %s (feed_alias, http_request, last_request_date) VALUES ('%s', %d, '%s')" % (
                    status_table, feed_alias, 1, date)
                c.execute(query_str)
                query_str = "UPDATE %s SET http_request = %d, last_request_date = '%s' WHERE feed_alias = '%s'" % (
                    status_table, 1, date, feed_alias)
                c.execute(query_str)


def update_public_html_status(c) -> None:
    p = pathlib.Path(public_html_path)
    feed_list = list(p.glob('*.xml'))
    for feed in feed_list:
        if re.search(r'(^_|^conf.xml$)', feed.name):
            continue
        feed_name = re.sub(r'\.xml', '', feed.name)
        # print("public_html: ", feed_name)

        for row in c.execute("SELECT feed_alias FROM feed_alias_name WHERE feed_name = '%s'" % feed_name):
            feed_alias = row[0]
            query_str = "INSERT OR IGNORE INTO %s (feed_alias, public_html) VALUES ('%s', %d)" % (
                status_table, feed_alias, 1)
            c.execute(query_str)
            query_str = "UPDATE %s SET public_html = %d WHERE feed_alias = '%s'" % (status_table, 1, feed_alias)
            c.execute(query_str)


def update_feedmaker_status(c) -> None:
    p = pathlib.Path(feedmaker_path)
    feed_list = list(p.glob('*/*/*.xml'))
    for feed in feed_list:
        if re.search(r'(^_|^conf.xml$)', feed.name):
            continue
        m = re.match(r'(?P<feed_name>\S+)\.xml', feed.name)
        if m:
            feed_name = m.group("feed_name")
            # print("feed_maker: ", feed_name)

            for row in c.execute("SELECT feed_alias FROM feed_alias_name WHERE feed_name = '%s'" % feed_name):
                feed_alias = row[0]
                query_str = "INSERT OR IGNORE INTO %s (feed_alias, feedmaker) VALUES ('%s', %d)" % (
                    status_table, feed_alias, 1)
                c.execute(query_str)
                query_str = "UPDATE %s SET feedmaker = %d WHERE feed_alias = '%s'" % (status_table, 1, feed_alias)
                c.execute(query_str)


def print_mismatch_feeds(c) -> None:
    query_str = "SELECT s.feed_alias, feed_name, http_request, htaccess, public_html, feedmaker, last_request_date FROM feed_status s JOIN feed_alias_name a ON s.feed_alias = a.feed_alias WHERE http_request != 1 OR htaccess != 1 OR public_html != 1 OR feedmaker != 1 ORDER BY http_request, htaccess, public_html, feedmaker"
    result_list: List[Dict[Str, Str]] = []
    for row in c.execute(query_str):
        feed_alias = row[0]
        feed_name = row[1]
        http_request = row[2]
        htaccess = row[3]
        public_html = row[4]
        feedmaker = row[5]
        last_request_date = row[6]

        if not last_request_date:
            last_request_date = ""

        result = {
            "feed_alias": row[0],
            "feed_name": row[1],
            "http_request": row[2],
            "htaccess": row[3],
            "public_html": row[4],
            "feedmaker": row[5],
            "last_request_date": row[6]
        }
        result_list.append(result)

        '''
        print("<td class='external'><a href='https://terzeron.net/%s.xml' target='_blank'>" % feed_alias)
        if feed_alias != feed_name:
            print("<strong><i>%s</i></strong>" % feed_alias)
        else:
            print(feed_alias)
        print("<td class='internal'><a href='https://terzeron.net/xml/%s.xml' target='_blank'>%s</a></td>" % (feed_name, feed_name))
        print("<td class='http_request'>%s</td>" % (http_request == 1 and "O" or "X"))
        print("<td class='htaccess'>%s</td>" % (htaccess == 1 and "O" or "X"))
        print("<td class='public_html'>%s</td>" % (public_html == 1 and "O" or "X"))
        print("<td class='feedmaker'>%s</td>" % (feedmaker == 1 and "O" or "X"))
        print("<td class='last_request_date'>%s</td>" % last_request_date)
        print("<td class='management'><a href='exec.php?command=view&feed_name=%s'>%s</a></td>" % (feed_name, feed_name))
        '''
    print(json.dumps(result_list))
    
        
def main() -> int:
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    create_feed_status_table(c)

    update_htaccess_status(c)
    update_feed_access_status(c)
    update_public_html_status(c)
    update_feedmaker_status(c)
    conn.commit()

    print_mismatch_feeds(c)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
