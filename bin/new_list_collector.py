#!/usr/bin/env python3


import os
import pprint
import re
import sys
import time
import getopt
import logging
import logging.config
from typing import Dict, List, Tuple, Any
from feed_maker_util import Config, exec_cmd, determine_crawler_options, remove_duplicates


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
logger = logging.getLogger()


class NewListCollector:
    def __init__(self, collection_conf: Dict[str, Any], new_list_file_name: str) -> None:
        self.collection_conf = collection_conf
        self.new_list_file_name = new_list_file_name

        
    def extract_urls(self, url) -> List[Tuple[str, str]]:
        logger.debug("# extract_urls(%s)" % url)
        
        option_str = determine_crawler_options(self.collection_conf)
        whole_cmd = ""
        
        cmd = "crawler.py %s '%s'" % (option_str, url)
        if whole_cmd:
            whole_cmd += " | " + cmd
        else:
            whole_cmd += cmd
        logger.debug("%s" % whole_cmd)
        (result, error) = exec_cmd(cmd)
        if error:
            time.sleep(5)
            (result, error) = exec_cmd(cmd)
            if error:
                logger.debug(whole_cmd + "\n" + str(result) + "\n")
                logger.error("# can't get result from crawler script")
                sys.exit(-1)
                    
        cmd = "extract_element.py collection"
        if whole_cmd:
            whole_cmd += " | " + cmd
        else:
            whole_cmd += cmd
        logger.debug("%s" % whole_cmd)
        (result, error) = exec_cmd(cmd, result)
        if error: 
            logger.debug(whole_cmd + "\n" + str(result) + "\n")
            logger.error("can't get result from extract script, %s" % (error))
            sys.exit(-1)
    
        cmd = self.collection_conf["item_capture_script"]
        if whole_cmd:
            whole_cmd += " | " + cmd
        else:
            whole_cmd += cmd
        logger.debug("%s" % whole_cmd)
        (result, error) = exec_cmd(cmd, result)
        if error:
            logger.debug(whole_cmd + "\n" + str(result) + "\n")
            logger.error("can't get result from capture script, %s" % (error))
            sys.exit(-1)
    
        # check the result
        result_list = []
        for line in result.rstrip().split("\n"):
            line = line.rstrip()
            if re.search(r'^#', line) or re.search(r'^\s*$', line):
                continue
            items = line.split("\t")
            link = items[0]
            title = " ".join(items[1:])
            if not link or not title:
                logger.error("can't get the link and title from '%s', %s" % (link, error))
                sys.exit(-1)
            result_list.append((link, title))
        return result_list
    
    
    def compose_url_list(self) -> List[Tuple[str, str]]:
        logger.debug("# compose_url_list()")
        result_list: List[Tuple[str, str]] = []
    
        for list_url in self.collection_conf["list_url_list"]:
            url_list = self.extract_urls(list_url)
            result_list.extend(url_list)
    
        result_list = remove_duplicates(result_list)
        return result_list

    
    def save_new_list_to_file(self, new_list: List[Tuple[str, str]]) -> None:
        try:
            with open(self.new_list_file_name, 'w', encoding='utf-8') as out_file:
                for link, title in new_list:
                    out_file.write("%s\t%s\n" % (link, title))
                    logger.info("%s\t%s" % (link, title))
        except IOError as e:
            logger.error(str(e))
            sys.exit(-1)


    def collect(self) -> List[Tuple[str, str]]:
        logger.debug("# collect()")
        config = Config()
    
        # collect items from specified url list
        logger.debug("collecting items from specified url list...")
        new_list = self.compose_url_list()
        if new_list and len(new_list) > 0:
            self.save_new_list_to_file(new_list)
            return new_list
        return None

