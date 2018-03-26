#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import re
import sys
import signal
from feedmakerutil import Config, IO, HTMLExtractor, die
from logger import Logger


logger = Logger("extract_element.py")
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def extract_content(config_item: str) -> None:
    logger.debug("# extract_content()")
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
        logger.debug("# element_id: %s" % id_str)
        logger.debug("# element_class: %s" % class_str)
        logger.debug("# element_path: %s" % path_str)
        logger.debug("# encoding: %s" % enc)
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
    
    ret = -1
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
                    ret = 0
        if class_str != None and class_str != "":
            divs = soup.find_all(class_=class_str)
            if divs:
                for div in divs:
                    print(div)
                    ret = 0
        if path_str != None and path_str != "":
            divs = HTMLExtractor.get_node_with_path(soup, path_str)
            if divs:
                for div in divs:
                    print(div)
                    ret = 0
        if ret == 0:
            break
    return ret


def print_usage(program_name: str) -> None:
    print(("Usage:\t%s\t<config item>\n" % program_name))
    print("")


def main() -> int:
    if len(sys.argv) < 2:
        print_usage(sys.argv[0])
        sys.exit(-1)
    return extract_content(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())