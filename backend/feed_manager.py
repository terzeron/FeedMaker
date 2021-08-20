#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import os
from pathlib import Path
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from functools import cmp_to_key
from run import FeedMakerRunner
from feed_maker_util import Htaccess, exec_cmd


class FeedManager:
    # group_name -> feed_title_list(name, title)
    group_name_feed_title_list_map: Dict[str, List[Dict[str, str]]] = {}
    # feed_name -> configuration
    feed_name_config_map: Dict[str, Any] = {}
    work_dir = Path(os.environ["FEED_MAKER_WORK_DIR"])
    www_feeds_dir = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"])
    CONF_FILE = "conf.json"

    def git_add(self, conf_file_path: Path) -> Tuple[str, Optional[str]]:
        os.chdir(self.work_dir)
        feed_name = conf_file_path.parent.name
        conf_file_relative = conf_file_path.relative_to(self.work_dir)
        cmd = "git add %s && git commit -m 'add feed %s'" % (conf_file_relative, feed_name)
        return exec_cmd(cmd)

    def git_rm(self, conf_file_path: Path) -> Tuple[str, Optional[str]]:
        os.chdir(self.work_dir)
        feed_name = conf_file_path.parent.name
        conf_file_relative = conf_file_path.relative_to(self.work_dir)
        cmd = "git rm %s && git commit -m 'remove feed %s'" % (conf_file_relative, feed_name)
        return exec_cmd(cmd)

    def git_mv(self, conf_file_path: Path, new_conf_file_path: Path) -> Tuple[str, Optional[str]]:
        os.chdir(self.work_dir)
        feed_name = conf_file_path.parent.name
        new_feed_name = new_conf_file_path.parent.name
        conf_file_relative = conf_file_path.relative_to(self.work_dir)
        new_conf_file_relative = new_conf_file_path.relative_to(self.work_dir)
        cmd = "git mv %s %s && git commit -m 'rename feed %s to %s'" % (
            conf_file_relative, new_conf_file_relative, feed_name, new_feed_name)
        return exec_cmd(cmd)

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def read_config_file(self, path: Path) -> Dict[str, Any]:
        self.logger.debug("# read_config_file(path=%r)", path)
        with open(path, 'r') as infile:
            json_data = json.load(infile)
            if "configuration" not in json_data:
                self.logger.error("can't find normal configuration '%s'", path)
                return {}
            return json_data["configuration"]

    def load_all_feeds(self) -> None:
        self.feed_name_config_map = {}
        self.group_name_feed_title_list_map = {}
        for path in self.work_dir.glob("*/*/" + self.CONF_FILE):
            feed_name = path.parent.name
            group_name = path.parent.parent.name

            configuration = self.read_config_file(path)
            title = configuration["rss"]["title"].split("::")[0]

            feed_title_list = self.group_name_feed_title_list_map.get(group_name, [])
            feed_title_list.append({"name": feed_name, "title": title})
            self.group_name_feed_title_list_map[group_name] = feed_title_list

            self.feed_name_config_map[feed_name] = configuration

    def get_exec_result(self) -> Tuple[str, str]:
        exec_result_file_path = self.work_dir / "logs" / "all.log"
        if exec_result_file_path.is_file():
            with open(exec_result_file_path, 'r') as infile:
                return infile.read(), ""
        else:
            return "", "can't find such file '%s'" % exec_result_file_path.relative_to(self.work_dir)

    def get_problems(self) -> Tuple[str, str]:
        problems_file_path = self.work_dir / "logs" / "find_problems.log"
        if problems_file_path.is_file():
            with open(problems_file_path, 'r') as infile:
                return infile.read(), ""
        else:
            return "", "can't find such file '%s'" % problems_file_path.relative_to(self.work_dir)

    @staticmethod
    def compare_names(x, y):
        if x[0] == "_" and y[0] != "_":
            return 1
        elif x[0] != "_" and y[0] == "_":
            return -1
        elif x < y:
            return -1
        elif x > y:
            return 1
        return 0

    def get_groups(self) -> Tuple[List[str], str]:
        group_list: List[str] = []
        if self.group_name_feed_title_list_map != {}:
            for group_name in self.group_name_feed_title_list_map:
                group_list.append(group_name)
            return sorted(group_list, key=cmp_to_key(FeedManager.compare_names)), ""
        return [], "no group list"

    @staticmethod
    def compare_title(x, y):
        if x["title"] < y["title"]:
            return -1
        elif x["title"] > y["title"]:
            return 1
        return 0

    def get_feeds_by_group(self, group_name: str) -> Tuple[List[Dict[str, str]], str]:
        if group_name in self.group_name_feed_title_list_map:
            feed_title_list = self.group_name_feed_title_list_map[group_name]
            return sorted(feed_title_list, key=cmp_to_key(FeedManager.compare_title)), ""
        return [], "no feed list in group '%s'" % group_name

    def get_feed_info_by_name(self, feed_name: str) -> Tuple[Dict[str, Any], str]:
        feed_info = self.feed_name_config_map.get(feed_name, {})
        if feed_info != {}:
            return feed_info, ""
        return {}, "empty configuration in feed '%s'" % feed_name

    def save_config_file(self, group_name: str, feed_name: str, post_data: Dict[str, Any]) -> Tuple[bool, str]:
        if "configuration" not in post_data:
            return False, "invalid conifiguration format (no 'configuration')"

        configuration = post_data["configuration"]
        if not ("collection" in configuration and "extraction" in configuration and "rss" in configuration):
            return False, "invalid conifiguration format (no 'collection' or 'extraction' or 'rss')"

        config_file_path = self.work_dir / group_name / feed_name / self.CONF_FILE
        config_file_path.parent.mkdir(exist_ok=True)
        with open(config_file_path, 'w') as outfile:
            json.dump(post_data, outfile, indent=2, ensure_ascii=False)

        title = configuration["rss"]["title"].split("::")[0]
        feed_title_list = self.group_name_feed_title_list_map[group_name]
        feed_title_list.append({"name": feed_name, "title": title})
        self.group_name_feed_title_list_map[group_name] = feed_title_list
        self.feed_name_config_map[feed_name] = post_data

        print(self.git_add(config_file_path))

        return True, ""

    def run(self, group_name: str, feed_name: str) -> Tuple[bool, str]:
        feed_dir_path = self.work_dir / group_name / feed_name
        os.chdir(feed_dir_path)
        conf_file_path = feed_dir_path / self.CONF_FILE
        with open(conf_file_path, 'r') as infile:
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
        return True, ""

    @staticmethod
    def remove_dir_and_files(path: Path) -> Tuple[bool, str]:
        if path.is_dir():
            print(path)
            try:
                for list_file in path.iterdir():
                    list_file.unlink()
                path.rmdir()
                return True, ""
            except Exception as e:
                return False, str(e)
        return False, "can't remove directory '%s'" % path

    def remove_list(self, group_name: str, feed_name: str) -> Tuple[bool, str]:
        feed_dir_path = self.work_dir / group_name / feed_name
        list_dir_path = feed_dir_path / "newlist"
        return self.remove_dir_and_files(list_dir_path)

    def remove_html(self, group_name: str, feed_name: str) -> Tuple[bool, str]:
        feed_dir_path = self.work_dir / group_name / feed_name
        html_dir_path = feed_dir_path / "html"
        return self.remove_dir_and_files(html_dir_path)

    def rescan_feeds_by_group(self, group_name: str, feed_name: str):
        self.group_name_feed_title_list_map[group_name] = {}
        self.feed_name_config_map[feed_name] = {}
        group_dir_path = self.work_dir / group_name
        feed_title_list: List[Dict[str, str]] = []
        for conf_file_path in group_dir_path.glob("*/" + self.CONF_FILE):
            feed_name = conf_file_path.parent.name
            configuration = self.read_config_file(conf_file_path)
            title = configuration["rss"]["title"].split("::")[0]
            feed_title_list.append({"name": feed_name, "title": title})
            self.group_name_feed_title_list_map[group_name] = feed_title_list
            self.feed_name_config_map[feed_name] = configuration

    def remove_feed(self, group_name: str, feed_name: str) -> Tuple[bool, str]:
        feed_dir_path = self.work_dir / group_name / feed_name
        conf_file_path = feed_dir_path / self.CONF_FILE
        if not feed_dir_path or not conf_file_path:
            return False, "can't remove feed '%s'" % feed_dir_path.relative_to(self.work_dir)

        rss_file_path = self.www_feeds_dir / "xml" / (feed_name + ".xml")
        img_dir_path = self.www_feeds_dir / "img" / feed_name
        pdf_dir_path = self.www_feeds_dir / "pdf" / feed_name

        # git rm & commit
        print(self.git_rm(conf_file_path))

        # remove files
        self.remove_dir_and_files(feed_dir_path)
        self.remove_dir_and_files(img_dir_path)
        self.remove_dir_and_files(pdf_dir_path)
        if rss_file_path.is_file():
            print(rss_file_path)
            rss_file_path.unlink()

        # re-scan feeds by group
        self.load_all_feeds()
        return True, ""

    def enable(self, group_name: str, feed_name: str, do_enable: bool) -> Tuple[bool, str]:
        if do_enable:
            if feed_name.startswith("_"):
                new_feed_name = feed_name[1:]
            else:
                return True, ""
        else:
            if not feed_name.startswith("_"):
                new_feed_name = "_" + feed_name
            else:
                return True, ""

        # rename feed directory
        feed_dir_path = self.work_dir / group_name / feed_name
        conf_file_path = feed_dir_path / self.CONF_FILE
        new_feed_dir_path = self.work_dir / group_name / new_feed_name
        new_conf_file_path = new_feed_dir_path / self.CONF_FILE
        if not feed_dir_path.is_dir():
            return False, "can't find such a directory '%s'" % feed_dir_path.relative_to(self.work_dir)
        feed_dir_path.rename(new_feed_dir_path)

        # git mv & commit
        print(self.git_mv(conf_file_path, new_conf_file_path))

        # re-scan feeds by group
        self.rescan_feeds_by_group(group_name, feed_name)

        print("self.group_name_feed_title_list_map[%s]=%r" % (group_name, self.group_name_feed_title_list_map[group_name]))
        print("self.feed_name_config_map[%s]=%r" % (new_feed_name, self.feed_name_config_map[new_feed_name]))
        return True, ""

    def rename_alias(self, group_name: str, feed_name: str, new_alias: str):
        result = Htaccess.set_alias(group_name, feed_name, new_alias)
        if not result:
            return False, "error in renaming alias in .htaccess"
        return True, ""
