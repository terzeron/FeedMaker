#!/usr/bin/env python
# -*- coding: utf-8 -*-


import re
import sys
import logging.config
from pathlib import Path
from typing import Any
from shutil import which
from bin.feed_maker_util import Process, Data, PathUtil
from bin.crawler import Crawler, Method

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class NewlistCollector:
    def __init__(self, feed_dir_path: Path, collection_conf: dict[str, Any], new_list_file_path: Path) -> None:
        LOGGER.debug("# NewlistCollector(feed_dir_path=%s, collection_conf=%r, new_list_file_path=%s", PathUtil.short_path(feed_dir_path), collection_conf, PathUtil.short_path(new_list_file_path))
        self.feed_dir_path: Path = feed_dir_path
        self.collection_conf: dict[str, Any] = collection_conf
        self.new_list_file_path: Path = new_list_file_path

    def __del__(self) -> None:
        del self.collection_conf

    @staticmethod
    def split_result_into_items(result: str) -> list[tuple[str, str]]:
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
                LOGGER.error("Error: Can't split a line into link and title, line='%s'", line)
                return []
            result_list.append((link, title))
        return result_list

    def _compose_url_list(self) -> list[tuple[str, str]]:
        LOGGER.debug("# compose_url_list()")

        result_list: list[tuple[str, str]] = []
        conf = self.collection_conf
        headers: dict[str, str] = conf.get("headers", {})
        if "referer" in conf:
            headers["Referer"] = conf.get("referer", "")
        crawler = Crawler(dir_path=self.feed_dir_path, render_js=conf.get("render_js", False), method=Method.GET, headers=headers, timeout=conf.get("timeout", 60), num_retries=conf.get("num_retries", 1), encoding=conf.get("encoding", "utf-8"), verify_ssl=conf.get("verify_ssl", True), copy_images_from_canvas=conf.get("copy_images_from_canvas", False), simulate_scrolling=conf.get("simulate_scrolling", False), disable_headless=conf.get("disable_headless", False), blob_to_dataurl=conf.get("blob_to_dataurl", False))
        option_str = Crawler.get_option_str(self.collection_conf)
        for url in conf.get("list_url_list", []):
            crawler_cmd = f"crawler.py -f '{self.feed_dir_path}' {option_str} '{url}'"
            LOGGER.debug("cmd=%s", crawler_cmd)
            try:
                result, error, _ = crawler.run(url)
                if not result:
                    LOGGER.error("Warning: can't get result from web page '%s', %s", url, error)
                    continue
            except UnicodeDecodeError as e:
                LOGGER.error(e)
                continue

            capture_cmd = f"{self.collection_conf['item_capture_script']} -f '{self.feed_dir_path}'"
            LOGGER.debug("cmd=%s", capture_cmd)
            result, error = Process.exec_cmd(capture_cmd, dir_path=self.feed_dir_path, input_data=result)
            if not result or error:
                LOGGER.warning("Warning: can't get result from item capture script, cmd='%s', %r", capture_cmd, error)
                continue

            for post_process_script in self.collection_conf.get("post_process_script_list", []):
                program = post_process_script.split(" ")[0]
                program_fullpath = which(program)
                if program_fullpath and (program_fullpath.startswith("/usr") or program_fullpath.startswith("/bin") or program_fullpath.startswith("/sbin") or program_fullpath.startswith("/opt/homebrew/bin")):
                    post_process_cmd = f"{post_process_script}"
                else:
                    post_process_cmd = f"{post_process_script} -f '{self.feed_dir_path}' '{url}'"
                LOGGER.debug("cmd=%s", post_process_cmd)
                result, error = Process.exec_cmd(post_process_cmd, dir_path=self.feed_dir_path, input_data=result)
                if not result or error:
                    LOGGER.warning("Warning: can't get result from post process scripts, cmd='%s', %r", post_process_cmd, error)

            url_list = self.split_result_into_items(result)
            result_list.extend(url_list)

        if not result_list:
            LOGGER.error("Error: Can't get new list from '%r'", conf.get("list_url_list", []))
            return []
        result_list = Data.remove_duplicates(result_list)
        return result_list

    def _save_new_list_to_file(self, new_list: list[tuple[str, str]]) -> None:
        try:
            with open(self.new_list_file_path, 'w', encoding='utf-8') as out_file:
                for link, title in new_list:
                    out_file.write(f"{link}\t{title}\n")
        except IOError as e:
            LOGGER.error("Error: %s", e)
            sys.exit(-1)

    def collect(self) -> list[tuple[str, str]]:
        LOGGER.debug("# collect()")

        # collect items from specified url list
        LOGGER.debug("collecting items from specified url list...")
        new_list = self._compose_url_list()
        if new_list:
            self._save_new_list_to_file(new_list)
            return new_list
        return []
