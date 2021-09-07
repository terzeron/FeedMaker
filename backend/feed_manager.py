#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
from pathlib import Path
import json
import logging
from shutil import rmtree
from typing import List, Dict, Any, Tuple, Optional
from functools import cmp_to_key
from run import FeedMakerRunner
from feed_maker_util import Htaccess, exec_cmd
from problem_checker import ProblemChecker


class FeedManager:
    work_dir = Path(os.environ["FEED_MAKER_WORK_DIR"])
    www_feeds_dir = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"])
    CONF_FILE = "conf.json"
    SITE_CONF_FILE = "site_config.json"

    def __init__(self, logger: logging.Logger) -> None:
        print("FeedManager.__init__()")
        self.logger = logger
        # group_name -> feed_title_list(name, title)
        self.group_name_feed_title_list_map: Dict[str, List[Dict[str, str]]] = {}
        # feed_name -> configuration
        self.feed_name_config_map: Dict[str, Any] = {}
        self.checker = ProblemChecker()
        self.checker.load()

    def __del__(self) -> None:
        del self.group_name_feed_title_list_map
        del self.feed_name_config_map
        del self.checker

    def _git_add(self, feed_dir_path: Path) -> Tuple[str, Optional[str]]:
        os.chdir(self.work_dir)
        feed_name = feed_dir_path.name
        conf_file_relative = feed_dir_path.relative_to(self.work_dir)
        cmd = "git add %s && git commit -m 'add %s'" % (conf_file_relative, feed_name)
        return exec_cmd(cmd)

    def _git_rm(self, feed_dir_path: Path) -> Tuple[str, Optional[str]]:
        os.chdir(self.work_dir)
        feed_name = feed_dir_path.name
        conf_file_relative = feed_dir_path.relative_to(self.work_dir)
        cmd = "git rm -r %s && git commit -m 'remove %s'" % (conf_file_relative, feed_name)
        return exec_cmd(cmd)

    def _git_mv(self, feed_dir_path: Path, new_feed_dir_path: Path) -> Tuple[str, Optional[str]]:
        os.chdir(self.work_dir)
        feed_dir_name = feed_dir_path.name
        new_feed_dir_name = new_feed_dir_path.name
        feed_dir_path_relative = feed_dir_path.relative_to(self.work_dir)
        new_feed_dir_path_relative = new_feed_dir_path.relative_to(self.work_dir)
        cmd = "git mv %s %s && git commit -m 'rename %s to %s' || mv %s %s" % (feed_dir_path_relative, new_feed_dir_path_relative, feed_dir_name, new_feed_dir_name, feed_dir_path_relative, new_feed_dir_path_relative)
        return exec_cmd(cmd)

    def _read_config_file(self, feed_dir_path: Path) -> Dict[str, Any]:
        self.logger.debug("# _read_config_file(feed_dir_path=%r)", feed_dir_path)
        conf_file_path = feed_dir_path / self.CONF_FILE
        if conf_file_path.is_file():
            with open(conf_file_path, 'r', encoding='utf-8') as infile:
                line_list: List[str] = []
                for line in infile:
                    line_list.append(line)
                json_data = json.loads(''.join(line_list))
                if "configuration" not in json_data:
                    self.logger.error("can't find normal configuration '%s'", feed_dir_path.relative_to(self.work_dir))
                    return {}
                return json_data["configuration"]
        return {}

    @staticmethod
    def _get_title_from_configuration(configuration: Dict[str, Any], feed_name: str) -> str:
        if configuration and "rss" in configuration and "title" in configuration["rss"]:
            title = configuration["rss"]["title"].split("::")[0]
        else:
            title = feed_name
        return title

    def _scan_feeds_by_group(self, group_name: str) -> None:
        group_dir_path = self.work_dir / group_name
        feed_title_list: List[Dict[str, str]] = []
        for path in group_dir_path.iterdir():
            if path.is_dir():
                feed_name = path.name
                if feed_name.startswith("."):
                    continue
                configuration = self._read_config_file(path)
                self.feed_name_config_map[feed_name] = configuration
                title = self._get_title_from_configuration(configuration, feed_name)
                feed_title_list.append({"name": feed_name, "title": title})
            elif path.name == self.SITE_CONF_FILE:
                feed_title_list.append({"name": path.name, "title": path.name})
        self.group_name_feed_title_list_map[group_name] = feed_title_list

    def load_all_feeds(self) -> None:
        self.feed_name_config_map.clear()
        self.group_name_feed_title_list_map.clear()
        for group_dir_path in self.work_dir.iterdir():
            if group_dir_path.is_dir():
                group_name = group_dir_path.name
                if group_name in ["test", "logs"] or group_name.startswith("."):
                    continue
                self._scan_feeds_by_group(group_name)

    def get_exec_result(self) -> Tuple[str, str]:
        exec_result_file_path = self.work_dir / "logs" / "all.log"
        if exec_result_file_path.is_file():
            with open(exec_result_file_path, 'r', encoding='utf-8') as infile:
                return infile.read(), ""
        else:
            return "", "can't find such file '%s'" % exec_result_file_path.relative_to(self.work_dir)

    def get_problems_status_info(self) -> Tuple[Dict[str, Any], str]:
        return self.checker.feed_alias_status_info_list, ""

    def get_problems_progress_info(self) -> Tuple[List[Dict[str, Any]], str]:
        return self.checker.feed_name_progress_info_list, ""

    def get_problems_public_feed_info(self) -> Tuple[List[Dict[str, Any]], str]:
        return self.checker.public_feed_info_list, ""

    def get_problems_html_info(self) -> Tuple[Dict[str, Any], str]:
        return {
                   "html_file_size_list": self.checker.html_file_size_list,
                   "html_file_with_many_image_tag_list": self.checker.html_file_with_many_image_tag_list,
                   "html_file_without_image_tag_list": self.checker.html_file_without_image_tag_list,
                   "html_file_image_not_found_list": self.checker.html_file_image_not_found_list
               }, ""

    def get_problems_element_info(self) -> Tuple[Dict[str, Any], str]:
        return {
                   "feed_name_list_url_count_list": self.checker.feed_name_list_url_count_list,
                   "element_name_count_list": self.checker.element_name_count_list
               }, ""

    @staticmethod
    def _determine_keyword_in_config_item(keyword, config, *args):
        config_item = config
        for arg in args:
            if arg in config_item:
                config_item = config_item[arg]
        return keyword in config_item

    def search(self, keywords: str) -> Tuple[List[Dict[str, Any]], str]:
        result_list: List[Dict[str, Any]] = []
        keyword_list = keywords.split(' ')
        for feed_name, config in self.feed_name_config_map.items():
            match_count_in_name = 0
            match_count_in_title = 0
            match_count_in_description = 0
            for keyword in keyword_list:
                if keyword in feed_name:
                    match_count_in_name += 1
                if self._determine_keyword_in_config_item(keyword, config, "rss", "title"):
                    match_count_in_title += 1
                if self._determine_keyword_in_config_item(keyword, config, "rss", "description"):
                    match_count_in_description += 1

            if match_count_in_name == len(keyword_list) or match_count_in_title == len(keyword_list) or match_count_in_description == len(keyword_list):
                group_name = self.checker.feed_name_group_map.get(feed_name, "")
                title = self.checker.feed_name_title_map.get(feed_name, "")
                result_list.append({'group_name': group_name, 'feed_name': feed_name, 'feed_title': title})

        return result_list, ""

    @staticmethod
    def _compare_names(x, y):
        if x['name'][0] == "_" and y['name'][0] != "_":
            return 1
        if x['name'][0] != "_" and y['name'][0] == "_":
            return -1
        if x['name'] < y['name']:
            return -1
        if x['name'] > y['name']:
            return 1
        return 0

    def get_groups(self) -> Tuple[List[Dict[str, Any]], str]:
        group_list: List[Dict[str, Any]] = []
        if self.group_name_feed_title_list_map != {}:
            for group_name, feed_title_list in self.group_name_feed_title_list_map.items():
                group_list.append({"name": group_name, "num_feeds": len(feed_title_list)})
            return sorted(group_list, key=cmp_to_key(FeedManager._compare_names)), ""
        return [], "no group list"

    @staticmethod
    def _compare_title(x, y):
        if x["name"][0] == "_" and y["name"][0] != "_":
            return 1
        if x["name"][0] != "_" and y["name"][0] == "_":
            return -1
        if x["title"][0] == "_" and y["title"][0] != "_":
            return 1
        if x["title"][0] != "_" and y["title"][0] == "_":
            return -1
        if x["title"] < y["title"]:
            return -1
        if x["title"] > y["title"]:
            return 1
        return 0

    def get_site_config(self, group_name: str) -> Tuple[Dict[str, str], str]:
        path = self.work_dir / group_name / self.SITE_CONF_FILE
        if path.is_file():
            with open(path, 'r', encoding='utf-8') as infile:
                json_data = json.load(infile)
                return json_data, ""
        return {}, "no feed list in group '%s'" % group_name

    def save_site_config(self, group_name: str, post_data: Dict[str, Any]) -> Tuple[bool, str]:
        path = self.work_dir / group_name / self.SITE_CONF_FILE
        try:
            with open(path, 'w', encoding='utf-8') as outfile:
                outfile.write(json.dumps(post_data, indent=2, ensure_ascii=False))
        except IOError as e:
            return False, str(e)
        return True, ""

    def get_feeds_by_group(self, group_name: str) -> Tuple[List[Dict[str, str]], str]:
        if group_name in self.group_name_feed_title_list_map:
            feed_title_list = self.group_name_feed_title_list_map[group_name]
            return sorted(feed_title_list, key=cmp_to_key(FeedManager._compare_title)), ""
        return [], "no feed list in group '%s'" % group_name

    def get_feed_info_by_name(self, feed_name: str) -> Tuple[Dict[str, Any], str]:
        return self.feed_name_config_map.get(feed_name, {}), ""

    def save_config_file(self, group_name: str, feed_name: str, post_data: Dict[str, Any]) -> Tuple[bool, str]:
        if "configuration" not in post_data:
            return False, "invalid configuration format (no 'configuration')"

        configuration = post_data["configuration"]
        if not ("collection" in configuration and "extraction" in configuration and "rss" in configuration):
            return False, "invalid configuration format (no 'collection' or 'extraction' or 'rss')"

        config_file_path = self.work_dir / group_name / feed_name / self.CONF_FILE
        config_file_path.parent.mkdir(exist_ok=True)
        with open(config_file_path, 'w', encoding='utf-8') as outfile:
            outfile.write(json.dumps(post_data, indent=2, ensure_ascii=False))

        title = configuration["rss"]["title"].split("::")[0]
        feed_title_list = self.group_name_feed_title_list_map[group_name]
        feed_title_list.append({"name": feed_name, "title": title})
        self.group_name_feed_title_list_map[group_name] = feed_title_list
        self.feed_name_config_map[feed_name] = configuration

        self._git_add(config_file_path)

        # re-scan feeds by group
        self.load_all_feeds()
        self.checker.load()
        return True, ""

    def run(self, group_name: str, feed_name: str) -> Tuple[bool, str]:
        feed_dir_path = self.work_dir / group_name / feed_name
        os.chdir(feed_dir_path)
        conf_file_path = feed_dir_path / self.CONF_FILE
        with open(conf_file_path, 'rb') as infile:
            json_data = json.load(infile)
            if "configuration" in json_data:
                runner = FeedMakerRunner(
                    html_archiving_period=30, list_archiving_period=7)
                if json_data["configuration"]["collection"].get("is_completed", False):
                    result = runner.make_single_feed(
                        feed_dir_path, options={"force_collection_opt": "-c"})
                    if not result:
                        return False, "error in making a feed with all completed articles"

                result = runner.make_single_feed(feed_dir_path, options={})
                if not result:
                    return False, "error in making a feed with recent articles"

                result = Htaccess.set_alias(group_name, feed_name)
                if not result:
                    return False, "error in setting alias to .htaccess"
            else:
                return False, "invalid format of configuration file"
        self.checker.load()
        return True, ""

    def _remove_public_img_pdf_feed_files(self, feed_name: str) -> None:
        img_dir_path = self.www_feeds_dir / "img" / feed_name
        pdf_dir_path = self.www_feeds_dir / "pdf" / feed_name
        feed_file_path = self.www_feeds_dir / "xml" / (feed_name + ".xml")

        # remove files
        try:
            rmtree(img_dir_path)
            rmtree(pdf_dir_path)
            if feed_file_path.is_file():
                feed_file_path.unlink()
            self.checker.load_all_public_feed_files(do_merge=True)
        except FileNotFoundError:
            pass

    def remove_list(self, group_name: str, feed_name: str) -> None:
        feed_dir_path = self.work_dir / group_name / feed_name
        list_dir_path = feed_dir_path / "newlist"
        try:
            rmtree(list_dir_path)
        except FileNotFoundError:
            pass

    def remove_html(self, group_name: str, feed_name: str) -> None:
        feed_dir_path = self.work_dir / group_name / feed_name
        html_dir_path = feed_dir_path / "html"
        try:
            rmtree(html_dir_path)
            self.checker.load_all_html_files(do_merge=True)
        except FileNotFoundError:
            pass

    def remove_html_file(self, group_name: str, feed_name: str, html_file_name: str) -> None:
        html_dir_path = self.work_dir / group_name / feed_name / "html" / html_file_name
        try:
            html_dir_path.unlink()
            self.checker.load_all_html_files(do_merge=True)
        except FileNotFoundError:
            pass

    def remove_public_feed(self, feed_name: str) -> None:
        feed_path = self.www_feeds_dir / (feed_name + ".xml")
        try:
            feed_path.unlink()
            self.checker.load_all_public_feed_files(do_merge=True)
        except FileNotFoundError:
            pass

    def remove_feed(self, group_name: str, feed_name: str) -> Tuple[bool, str]:
        feed_dir_path = self.work_dir / group_name / feed_name
        conf_file_path = feed_dir_path / self.CONF_FILE
        if not feed_dir_path or not conf_file_path:
            return False, "can't remove feed '%s'" % feed_dir_path.relative_to(self.work_dir)

        # remove files
        self._remove_public_img_pdf_feed_files(feed_name)

        # git rm & commit
        self._git_rm(feed_dir_path)

        # remove remainder files and directories
        try:
            rmtree(feed_dir_path)
        except FileNotFoundError:
            pass

        # re-scan feeds by group
        self.load_all_feeds()
        self.checker.load()
        return True, ""

    def remove_group(self, group_name: str) -> Tuple[bool, str]:
        group_dir_path = self.work_dir / group_name
        if not group_dir_path:
            return False, "can't remove group '%s'" % group_name

        # remove files
        for feed_dir_path in group_dir_path.iterdir():
            feed_name = feed_dir_path.name
            self._remove_public_img_pdf_feed_files(feed_name)

        # git rm & commit
        self._git_rm(group_dir_path)

        # remove remainder files and directories
        try:
            rmtree(group_dir_path)
        except FileNotFoundError:
            pass

        # re-scan feeds by group
        self.load_all_feeds()
        self.checker.load()
        return True, ""

    def toggle_feed(self, group_name: str, feed_name: str) -> Tuple[str, str]:
        if feed_name.startswith("_"):
            new_feed_name = feed_name[1:]
        else:
            new_feed_name = "_" + feed_name

        # rename feed directory
        feed_dir_path = self.work_dir / group_name / feed_name
        new_feed_dir_path = self.work_dir / group_name / new_feed_name
        if not feed_dir_path.is_dir():
            return "", "can't find such a directory '%s'" % feed_dir_path.relative_to(self.work_dir)
        # git mv & commit
        self._git_mv(feed_dir_path, new_feed_dir_path)

        # re-scan feeds by group
        self.group_name_feed_title_list_map[group_name].clear()
        self.feed_name_config_map[feed_name].clear()
        self._scan_feeds_by_group(group_name)

        self.checker.load()
        return new_feed_name, ""

    def toggle_group(self, group_name: str) -> Tuple[str, str]:
        if group_name.startswith("_"):
            new_group_name = group_name[1:]
        else:
            new_group_name = "_" + group_name

        # rename feed directory
        group_dir_path = self.work_dir / group_name
        new_group_dir_path = self.work_dir / new_group_name
        if not group_dir_path.is_dir():
            return "", "can't find such a directory '%s'" % group_dir_path.relative_to(self.work_dir)
        # git mv & commit
        self._git_mv(group_dir_path, new_group_dir_path)

        # re-scan feeds by group
        self.load_all_feeds()
        self.checker.load()
        return new_group_name, ""

    @staticmethod
    def get_alias(group_name: str, feed_name: str):
        result, error = Htaccess.get_alias(group_name, feed_name)
        if not result:
            return "", error
        return result, ""

    def remove_alias(self, group_name: str, feed_name: str):
        result, error = Htaccess.remove_alias(group_name, feed_name)
        if not result:
            return False, error
        self.checker.load_htaccess_file(do_merge=True)
        return True, ""

    def rename_alias(self, group_name: str, feed_name: str, new_alias: str):
        result, error = Htaccess.set_alias(group_name, feed_name, new_alias)
        if not result:
            return False, error
        self.checker.load_htaccess_file(do_merge=True)
        return True, ""
