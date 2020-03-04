#!/usr/bin/env python


import os
import re
import sys
import time
import logging
import logging.config
from typing import Dict, List, Tuple, Any, Optional
from feed_maker_util import exec_cmd, determine_crawler_options, remove_duplicates


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class NewListCollector:
    def __init__(self, collection_conf: Dict[str, Any], new_list_file_name: str) -> None:
        self.collection_conf = collection_conf
        self.new_list_file_name = new_list_file_name


    def compose_and_execute_cmd(self, url: str) -> Tuple[Optional[str], Any]:
        option_str = determine_crawler_options(self.collection_conf)
        option_str += " --retry=2"
        crawl_cmd = "crawler.py %s '%s'" % (option_str, url)
        capture_cmd = self.collection_conf["item_capture_script"]
        post_process_cmd = ""
        for script in self.collection_conf["post_process_script_list"]:
            if post_process_cmd:
                post_process_cmd += ' | %s' % script
            else:
                post_process_cmd = script
        cmd_list = [crawl_cmd, capture_cmd, post_process_cmd]

        full_cmd = ""
        for cmd in cmd_list:
            if full_cmd and cmd:
                full_cmd += " | " + cmd
            else:
                full_cmd += cmd

        LOGGER.debug("%s", full_cmd)
        result, error = exec_cmd(full_cmd)
        if not result:
            LOGGER.warning("can't execute command '%s', %s", full_cmd, error)
            LOGGER.debug("wait for seconds and retry")
            time.sleep(10)
            result, error = exec_cmd(full_cmd)
            if not result:
                LOGGER.warning("can't execute command '%s', %s", full_cmd, error)
                LOGGER.error("# can't get result from the command '%s'", full_cmd)
        return (result, error)


    def extract_urls(self, url) -> List[Tuple[str, str]]:
        LOGGER.debug("# extract_urls(%s)", url)

        result, error = self.compose_and_execute_cmd(url)
        if not result:
            return []

        result_list = []
        for line in result.rstrip().split("\n"):
            line = line.rstrip()
            if re.search(r'^#', line) or re.search(r'^\s*$', line):
                continue
            items = line.split("\t")
            link = items[0]
            title = " ".join(items[1:])
            if not link or not title:
                LOGGER.error("can't get the link and title from '%s', %s", link, error)
                return []
            result_list.append((link, title))
        return result_list


    def compose_url_list(self) -> List[Tuple[str, str]]:
        LOGGER.debug("# compose_url_list()")
        result_list: List[Tuple[str, str]] = []

        for list_url in self.collection_conf["list_url_list"]:
            url_list = self.extract_urls(list_url)
            if not url_list:
                return []
            result_list.extend(url_list)

        result_list = remove_duplicates(result_list)
        return result_list


    def save_new_list_to_file(self, new_list: List[Tuple[str, str]]) -> None:
        try:
            with open(self.new_list_file_name, 'w', encoding='utf-8') as out_file:
                for link, title in new_list:
                    out_file.write("%s\t%s\n" % (link, title))
                    LOGGER.info("%s\t%s", link, title)
        except IOError as e:
            LOGGER.error(str(e))
            sys.exit(-1)


    def collect(self) -> List[Tuple[str, str]]:
        LOGGER.debug("# collect()")

        # collect items from specified url list
        LOGGER.debug("collecting items from specified url list...")
        new_list = self.compose_url_list()
        if new_list and len(new_list) > 0:
            self.save_new_list_to_file(new_list)
            return new_list
        return []
