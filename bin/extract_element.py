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


def main() -> int:
    logger.debug("# extract_content()")
    # configuration
    config = Config()
    if not config:
        die("can't read configuration")

    collection_conf = config.get_collection_configs()
    if not collection_conf:
        die("can't get collection configuration")

    id_list = collection_conf["element_id_list"]
    class_list = collection_conf["element_class_list"]
    path_list = collection_conf["element_path_list"]
    encoding = collection_conf["encoding"]
    logger.debug("# element_id: %r" % id_list)
    logger.debug("# element_class: %r" % class_list)
    logger.debug("# element_path: %r" % path_list)
    logger.debug("# encoding: %r" % encoding)

    # read html contents
    html = IO.read_stdin()

    # sanitize
    html = re.sub(r'alt="(.*)<br>(.*)"', r'alt="\1 \2"', html)
    html = re.sub(r'<br>', r'<br/>', html)
    html = re.sub(r'[\x01\x08]', '', html, re.LOCALE)
    html = re.sub(r'<\?xml[^>]+>', r'', html)

    if not id_list and not class_list and not path_list:
        print(html)
        return 0

    ret = -1
    for parser in ["html.parser", "html5lib", "lxml"]:
        soup = BeautifulSoup(html, parser)
        if not soup:
            die("can't parse HTML")

        for id_str in id_list:
            divs = soup.find_all(attrs={"id": id_str})
            if divs:
                for div in divs:
                    print(div)
                    ret = 0

        for class_str in class_list:
            divs = soup.find_all(class_=class_str)
            if divs:
                for div in divs:
                    print(div)
                    ret = 0

        for path_str in path_list:
            divs = HTMLExtractor.get_node_with_path(soup, path_str)
            if divs:
                for div in divs:
                    print(div)
                    ret = 0
    return ret


if __name__ == "__main__":
    sys.exit(main())
