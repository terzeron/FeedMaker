#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup, Comment
import re
import subprocess
import os
import sys
import urllib.request, urllib.error, urllib.parse
import socket
import copy
import signal
import feedmakerutil
from feedmakerutil import Config
from feedmakerutil import IO


signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def extract_content(config_item):
    #print "# extract_content()"
    # configuration
    class_str = ""
    id_str = ""
    path_str = ""
    config = Config.read_config()
    if config == None:
        return -1
    if config_item in ("collection", "extraction"):
        conf_node = Config.get_config_node(config, config_item)
        if conf_node == None:
            die("can't find '%s' element from configuration" % config_item)
        id_str = Config.get_config_value(conf_node, "element_id")
        class_str = Config.get_config_value(conf_node, "element_class")
        path_str = Config.get_config_value(conf_node, "element_path")
        enc = Config.get_config_value(conf_node, "encoding")
        #print("# element_id:", id_str)
        #print("# element_class:", class_str)
        #print("# element_path:", path_str)
        #print("# encoding:", enc)
    else:
        return -1
    
    # read html contents
    html = IO.read_stdin()

    # sanitize
    html = re.sub(r'alt="(.*)<br>(.*)"', r'alt="\1 \2"', html);
    html = re.sub(r'<br>', r'<br/>', html)
    html = re.sub(r'[\x01\x08]', '', html, re.LOCALE)
    html = re.sub(r'<\?xml[^>]+>', r'', html)

    if (class_str == None or class_str == "") and (id_str == None or id_str == "") and (path_str == None or path_str == ""):
        print(html)
        return
    
    ret = 0
    for parser in [ "html.parser", "html5lib", "lxml" ]:
        soup = BeautifulSoup(html, parser)
        if soup == None:
            print("can't parse html")
            print(html)
            sys.exit(-1)    
    
        if id_str != None and id_str != "":
            divs = soup.find_all(attrs={"id":id_str})
            if divs:
                for div in divs:
                    print(div)
                    ret = 1
        if class_str != None and class_str != "":
            divs = soup.find_all(class_=class_str)
            if divs:
                for div in divs:
                    print(div)
                    ret = 1
        if path_str != None and path_str != "":
            divs = get_node_with_path(soup, path_str)
            if divs:
                for div in divs:
                    print(div)
                    ret = 1
        if ret > 0:
            break


def print_usage(program_name):
    print(("Usage:\t%s\t<config item>\n" % program_name))
    print("")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage(sys.argv[0])
        sys.exit(-1)
    extract_content(sys.argv[1])
