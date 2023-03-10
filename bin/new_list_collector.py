#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import re
import sys
import logging.config
from pathlib import Path
from typing import Dict, List, Tuple, Any
from distutils.spawn import find_executable
from feed_maker_util import Process, Data
from crawler import Crawler, Method

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class NewListCollector:
    def __init__(self, feed_dir_path: Path, collection_conf: Dict[str, Any], new_list_file_path: Path) -> None:
        LOGGER.debug(
            f"# NewListCollector(feed_dir_path={feed_dir_path}, collection_conf={collection_conf}, new_list_file_path={new_list_file_path}")
        self.feed_dir_path: Path = feed_dir_path
        self.collection_conf: Dict[str, Any] = collection_conf
        self.new_list_file_path: Path = new_list_file_path

    def __del__(self):
        del self.collection_conf

    @staticmethod
    def split_result_into_items(result) -> List[Tuple[str, str]]:
        LOGGER.debug("# extract_urls()")

        result_list = []
        for line in result.rstrip().split("\n"):
            line = line.rstrip()
            if re.search(r'^#', line) or re.search(r'^\s*$', line):
                continue
            items = line.split("\t")
            link = items[0]
            title = " ".join(items[1:])
            if not link or not title:
                LOGGER.error(f"Error: Can't split a line into link and title, line='{line}'")
                return []
            result_list.append((link, title))
        return result_list

    def _compose_url_list(self) -> List[Tuple[str, str]]:
        LOGGER.debug("# compose_url_list()")

        result_list: List[Tuple[str, str]] = []
        conf = self.collection_conf
        crawler = Crawler(dir_path=self.feed_dir_path, render_js=conf["render_js"], method=Method.GET, headers=conf["header_list"], timeout=conf["timeout"], num_retries=conf["num_retries"], encoding=conf["encoding"], verify_ssl=conf["verify_ssl"], copy_images_from_canvas=conf["copy_images_from_canvas"], simulate_scrolling=conf["simulate_scrolling"], disable_headless=conf["disable_headless"], blob_to_dataurl=conf["blob_to_dataurl"])
        option_str = Crawler.get_option_str(self.collection_conf)
        for url in conf["list_url_list"]:
            crawler_cmd = f"crawler.py -f '{self.feed_dir_path}' {option_str} '{url}'"
            LOGGER.debug(f"cmd={crawler_cmd}")
            try:
                result, error, _ = crawler.run(url)
                if not result:
                    LOGGER.error(error)
                    continue
            except UnicodeDecodeError as e:
                LOGGER.error(e)
                continue

            capture_cmd = f"{self.collection_conf['item_capture_script']} -f '{self.feed_dir_path}'"
            LOGGER.debug(f"cmd={capture_cmd}")
            result, error_msg = Process.exec_cmd(capture_cmd, dir_path=self.feed_dir_path, input_data=result)
            if not result or error_msg:
                LOGGER.warning("Warning: can't get result from item capture script")
                LOGGER.debug(error_msg)
                continue

            for post_process_script in self.collection_conf["post_process_script_list"]:
                program = post_process_script.split(" ")[0]
                program_fullpath = find_executable(program)
                if program_fullpath and (program_fullpath.startswith("/usr") or program_fullpath.startswith("/bin") or program_fullpath.startswith("/sbin") or program_fullpath.startswith("/opt/homebrew/bin")):
                    post_process_cmd = f"{post_process_script}"
                else:
                    post_process_cmd = f"{post_process_script} -f '{self.feed_dir_path}' '{url}'"
                LOGGER.debug(f"cmd={post_process_cmd}")
                result, error_msg = Process.exec_cmd(post_process_cmd, dir_path=self.feed_dir_path, input_data=result)
                if not result or error:
                    LOGGER.warning("Warning: can't get result from post process scripts")
                    LOGGER.debug(error_msg)

            url_list = self.split_result_into_items(result)
            result_list.extend(url_list)

        if not result_list:
            LOGGER.error(f"Error: Can't get new list from {conf['list_url_list']}")
            return []
        result_list = Data.remove_duplicates(result_list)
        return result_list

    def _save_new_list_to_file(self, new_list: List[Tuple[str, str]]) -> None:
        try:
            with open(self.new_list_file_path, 'w', encoding='utf-8') as out_file:
                for link, title in new_list:
                    out_file.write(f"{link}\t{title}\n")
        except IOError as e:
            LOGGER.error("Error: %s", e)
            sys.exit(-1)

    def collect(self) -> List[Tuple[str, str]]:
        LOGGER.debug("# collect()")

        # collect items from specified url list
        LOGGER.debug("collecting items from specified url list...")
        new_list = self._compose_url_list()
        if new_list:
            self._save_new_list_to_file(new_list)
            return new_list
        return []
