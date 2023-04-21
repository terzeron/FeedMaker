#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
from pathlib import Path
import json
import logging
import logging.config
from datetime import datetime
from shutil import rmtree
from typing import List, Dict, Any, Tuple, Optional
from functools import cmp_to_key
from run import FeedMakerRunner
from feed_maker_util import Htaccess, Process, Data, PathUtil
from problem_manager import ProblemManager
from search_manga_site import SearchManager

logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
LOGGER = logging.getLogger(__name__)


class FeedManager:
    work_dir = Path(os.environ["FEED_MAKER_WORK_DIR"])
    public_feed_dir = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"])
    CONF_FILE = "conf.json"
    SITE_CONF_FILE = "site_config.json"

    def __init__(self) -> None:
        # group_name -> feed_title_list(name, title)
        self.group_name_feed_title_list_map: Dict[str, List[Dict[str, str]]] = {}
        # feed_name -> configuration
        self.feed_name_config_map: Dict[str, Any] = {}
        self.problem_manager = ProblemManager()
        self.problem_manager.load_all()

    def _git_add(self, feed_dir_path: Path) -> Tuple[str, Optional[str]]:
        feed_name = feed_dir_path.name
        conf_file_relative = PathUtil.convert_path_to_str(feed_dir_path)
        os.chdir(self.work_dir)
        cmd = f"git add {conf_file_relative} && git commit -m 'add {feed_name}'"
        return Process.exec_cmd(cmd, dir_path=self.work_dir)

    def _git_rm(self, feed_dir_path: Path) -> Tuple[str, Optional[str]]:
        feed_name = feed_dir_path.name
        conf_file_relative = PathUtil.convert_path_to_str(feed_dir_path)
        os.chdir(self.work_dir)
        cmd = f"git rm -r {conf_file_relative} && git commit -m 'remove {feed_name}'"
        return Process.exec_cmd(cmd, dir_path=self.work_dir)

    def _git_mv(self, feed_dir_path: Path, new_feed_dir_path: Path) -> Tuple[str, Optional[str]]:
        feed_dir_name = feed_dir_path.name
        new_feed_dir_name = new_feed_dir_path.name
        feed_dir_path_relative = PathUtil.convert_path_to_str(feed_dir_path)
        new_feed_dir_path_relative = PathUtil.convert_path_to_str(new_feed_dir_path)
        os.chdir(self.work_dir)
        cmd = f"git mv {feed_dir_path_relative} {new_feed_dir_path_relative} && git commit -m 'rename {feed_dir_name} to {new_feed_dir_name}' || mv {feed_dir_path_relative} {new_feed_dir_path_relative}"
        return Process.exec_cmd(cmd, dir_path=self.work_dir)

    def _read_config_file(self, feed_dir_path: Path) -> Dict[str, Any]:
        conf_file_path = feed_dir_path / self.CONF_FILE
        if conf_file_path.is_file():
            with conf_file_path.open('r', encoding='utf-8') as infile:
                line_list: List[str] = []
                for line in infile:
                    line_list.append(line)
                json_data = json.loads(''.join(line_list))
                if "configuration" not in json_data:
                    LOGGER.error(f"can't find normal configuration '{PathUtil.convert_path_to_str(feed_dir_path)}'")
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

    def scan_all_feeds(self) -> None:
        LOGGER.debug("# scan_all_feeds()")
        self.feed_name_config_map.clear()
        self.group_name_feed_title_list_map.clear()
        for group_dir_path in self.work_dir.iterdir():
            if group_dir_path.is_dir():
                group_name = group_dir_path.name
                if group_name in ("test", "logs") or group_name.startswith("."):
                    continue
                self._scan_feeds_by_group(group_name)

    async def get_exec_result(self) -> Tuple[str, str]:
        LOGGER.debug("# get_exec_result()")
        exec_result_file_path = self.work_dir / "logs" / "all.log"
        if exec_result_file_path.is_file():
            with exec_result_file_path.open('r', encoding='utf-8') as infile:
                return infile.read(), ""
        else:
            return "", f"can't find such file '{PathUtil.convert_path_to_str(exec_result_file_path)}'"

    async def get_problems_status_info(self) -> Tuple[Dict[str, Dict[str, Any]], str]:
        LOGGER.debug("# get_problems_status_info()")
        feed_alias_status_info = self.problem_manager.get_feed_alias_status_info_map()
        return feed_alias_status_info, ""

    async def get_problems_progress_info(self) -> Tuple[Dict[str, Dict[str, Any]], str]:
        LOGGER.debug("# get_problems_progress_info()")
        return self.problem_manager.get_feed_name_progress_info_map(), ""

    async def get_problems_public_feed_info(self) -> Tuple[Dict[str, Dict[str, Any]], str]:
        LOGGER.debug("# get_problems_public_feed_info()")
        return self.problem_manager.get_feed_name_public_feed_info_map(), ""

    async def get_problems_html_info(self) -> Tuple[Dict[str, Any], str]:
        LOGGER.debug("# get_problems_html_info()")
        return {"html_file_size_map": self.problem_manager.get_html_file_size_map(), "html_file_with_many_image_tag_map": self.problem_manager.get_html_file_with_many_image_tag_map(), "html_file_without_image_tag_map": self.problem_manager.get_html_file_without_image_tag_map(), "html_file_image_not_found_map": self.problem_manager.get_html_file_image_not_found_map()}, ""

    async def get_problems_element_info(self) -> Tuple[Dict[str, Any], str]:
        LOGGER.debug("# get_problems_element_info()")
        return {"feed_name_list_url_count_map": self.problem_manager.get_feed_name_list_url_count_map(), "element_name_count_map": self.problem_manager.get_element_name_count_map()}, ""

    @staticmethod
    def _determine_keyword_in_config_item(keyword: str, config: Dict[str, Any], *args):
        config_item: Dict[str, Any] = config
        for arg in args:
            if arg in config_item:
                config_item = config_item[arg]
        return keyword in config_item

    async def search(self, keywords: str) -> Tuple[List[Dict[str, Any]], str]:
        LOGGER.debug(f"# search(keywords={keywords})")
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
                group_name = self.problem_manager.feed_name_group_map.get(feed_name, "")
                title = self.problem_manager.feed_name_title_map.get(feed_name, "")
                result_list.append({'group_name': group_name, 'feed_name': feed_name, 'feed_title': title})

        return result_list, ""

    @staticmethod
    def search_site(keyword: str) -> Tuple[List[Tuple[str, str]], str]:
        LOGGER.debug(f"# search_site(keyword={keyword})")
        search_manager = SearchManager()
        return search_manager.search("", keyword), ""

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

    async def get_groups(self) -> Tuple[List[Dict[str, Any]], str]:
        LOGGER.debug("# get_groups()")
        group_list: List[Dict[str, Any]] = []
        if self.group_name_feed_title_list_map:
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

    async def get_site_config(self, group_name: str) -> Tuple[Dict[str, str], str]:
        LOGGER.debug(f"# get_site_config({group_name})")
        path = self.work_dir / group_name / self.SITE_CONF_FILE
        if path.is_file():
            with path.open('r', encoding='utf-8') as infile:
                json_data = json.load(infile)
                return json_data, ""
        return {}, f"no feed list in group '{group_name}'"

    async def save_site_config(self, group_name: str, post_data: Dict[str, Any]) -> Tuple[bool, str]:
        LOGGER.debug(f"# save_site_config({group_name}, {post_data})")
        path = self.work_dir / group_name / self.SITE_CONF_FILE
        try:
            with path.open('w', encoding='utf-8') as outfile:
                outfile.write(json.dumps(post_data, indent=2, ensure_ascii=False))
        except IOError as e:
            return False, str(e)
        return True, ""

    async def get_feeds_by_group(self, group_name: str) -> Tuple[List[Dict[str, str]], str]:
        LOGGER.debug(f"# get_feeds_by_group({group_name})")
        if group_name in self.group_name_feed_title_list_map:
            feed_title_list = self.group_name_feed_title_list_map[group_name]
            return sorted(feed_title_list, key=cmp_to_key(FeedManager._compare_title)), ""
        return [], f"no feed list in group '{group_name}'"

    async def get_feed_info_by_name(self, group_name: str, feed_name: str) -> Tuple[Dict[str, Any], str]:
        LOGGER.debug(f"# get_feed_info_by_name({feed_name})")
        feed_dir_path = self.work_dir / group_name / feed_name
        list_dir_path = feed_dir_path / "newlist"
        last_collect_date = datetime.now()
        result_list = []
        collection_info = {}
        if list_dir_path.is_dir():
            for list_file_path in list_dir_path.iterdir():
                st = list_file_path.stat()
                if not last_collect_date:
                    last_collect_date = datetime.fromtimestamp(st.st_mtime)
                else:
                    if last_collect_date < datetime.fromtimestamp(st.st_mtime):
                        last_collect_date = datetime.fromtimestamp(st.st_mtime)
                with list_file_path.open('r', encoding='utf-8') as infile:
                    for line in infile:
                        link, _ = line.split("\t")
                        result_list.append(link)
            result_list = Data.remove_duplicates(result_list)
            collection_info = {"collect_date": ProblemManager.convert_datetime_to_str(last_collect_date), "count": len(result_list)}
        feed_info = {
            "config": self.feed_name_config_map.get(feed_name, {}),
            "collection_info": collection_info,
            "public_feed_info": self.problem_manager.get_feed_name_public_feed_info_map().get(feed_name, {}),
            "progress_info": self.problem_manager.get_feed_name_progress_info_map().get(feed_name, {}),
        }
        return feed_info, ""

    async def save_config_file(self, group_name: str, feed_name: str, post_data: Dict[str, Any]) -> Tuple[bool, str]:
        LOGGER.debug(f"# save_config_file({group_name}, {feed_name}, {post_data})")
        if "configuration" not in post_data:
            return False, "invalid configuration format (no 'configuration')"

        configuration = post_data["configuration"]
        if not ("collection" in configuration and "extraction" in configuration and "rss" in configuration):
            return False, "invalid configuration format (no 'collection' or 'extraction' or 'rss')"

        config_file_path = self.work_dir / group_name / feed_name / self.CONF_FILE
        config_file_path.parent.mkdir(exist_ok=True)
        with config_file_path.open('w', encoding='utf-8') as outfile:
            outfile.write(json.dumps(post_data, indent=2, ensure_ascii=False))

        self._git_add(config_file_path)

        # re-scan feeds by group
        self.scan_all_feeds()
        self.problem_manager.add_config_rss_file_to_info(config_file_path.parent)
        return True, ""

    def run(self, group_name: str, feed_name: str, alias: str) -> Tuple[bool, str]:
        LOGGER.debug(f"# run({group_name}, {feed_name}, {alias})")
        feed_dir_path = self.work_dir / group_name / feed_name
        conf_file_path = feed_dir_path / self.CONF_FILE
        with conf_file_path.open('rb') as infile:
            json_data = json.load(infile)
            if "configuration" in json_data:
                runner = FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)
                if json_data["configuration"]["collection"].get("is_completed", False):
                    result = runner.make_single_feed(
                        feed_dir_path, options={"force_collection_opt": "-c"})
                    if not result:
                        return False, "error in making a feed with all completed articles"

                result = runner.make_single_feed(feed_dir_path, options={})
                if not result:
                    return False, "error in making a feed with recent articles"

                _, error = Htaccess.get_alias(group_name, feed_name)
                if error:
                    _, error = Htaccess.set_alias(group_name, feed_name, alias)
                    if error:
                        return False, "error in setting alias to .htaccess"
            else:
                return False, "invalid format of configuration file"

        self.problem_manager.reload_htaccess_file()
        self.problem_manager.update_feed_info(feed_dir_path)
        return True, ""

    def _remove_public_img_pdf_feed_files(self, feed_name: str) -> None:
        LOGGER.debug(f"# _remove_public_img_pdf_feed_files({feed_name})")
        img_dir_path = self.public_feed_dir / "img" / feed_name
        pdf_dir_path = self.public_feed_dir / "pdf" / feed_name
        feed_file_path = self.public_feed_dir / f"{feed_name}.xml"

        # remove files
        if img_dir_path.is_dir():
            LOGGER.debug(f"deleting {img_dir_path}")
            rmtree(img_dir_path)
        if pdf_dir_path.is_dir():
            LOGGER.debug(f"deleting {pdf_dir_path}")
            rmtree(pdf_dir_path)
        LOGGER.debug(f"deleting {feed_file_path}")
        feed_file_path.unlink(missing_ok=True)

    async def remove_list(self, group_name: str, feed_name: str) -> None:
        LOGGER.debug(f"# remove_list({group_name}, {feed_name})")
        feed_dir_path = self.work_dir / group_name / feed_name
        list_dir_path = feed_dir_path / "newlist"
        if list_dir_path.is_dir():
            rmtree(list_dir_path)

    async def remove_html(self, group_name: str, feed_name: str) -> None:
        LOGGER.debug(f"# remove_html({group_name}, {feed_name})")
        feed_dir_path = self.work_dir / group_name / feed_name
        html_dir_path = feed_dir_path / "html"
        if html_dir_path.is_dir():
            rmtree(html_dir_path)
        self.problem_manager.remove_html_file_in_path_from_info("feed_dir_path", feed_dir_path)

    async def remove_html_file(self, group_name: str, feed_name: str, html_file_name: str) -> None:
        LOGGER.debug(f"# remove_html_file({group_name}, {feed_name})")
        html_file_path = self.work_dir / group_name / feed_name / "html" / html_file_name
        html_file_path.unlink(missing_ok=True)
        self.problem_manager.remove_html_file_in_path_from_info("file_path", html_file_path)

    async def remove_public_feed(self, feed_name: str) -> None:
        LOGGER.debug(f"# remove_public_feed({feed_name})")
        feed_file_path = self.public_feed_dir / f"{feed_name}.xml"
        feed_file_path.unlink(missing_ok=True)
        self.problem_manager.remove_public_feed_file_from_info(feed_file_path)

    async def remove_feed(self, group_name: str, feed_name: str) -> Tuple[bool, str]:
        LOGGER.debug(f"# remove_feed({group_name}, {feed_name})")
        feed_dir_path = self.work_dir / group_name / feed_name
        conf_file_path = feed_dir_path / self.CONF_FILE
        if not feed_dir_path or not conf_file_path:
            return False, f"can't remove feed '{PathUtil.convert_path_to_str(feed_dir_path)}'"

        # remove files
        self._remove_public_img_pdf_feed_files(feed_name)

        # git rm & commit
        self._git_rm(feed_dir_path)

        # remove remainder files and directories
        if feed_dir_path.is_dir():
            rmtree(feed_dir_path)

        # remove alias
        result, _ = Htaccess.remove_alias(group_name, feed_name)
        if not result:
            return False, "error in removing alias from .htaccess"

        # re-scan feeds by group
        self.scan_all_feeds()
        self.problem_manager.update_feed_info(feed_dir_path)
        return True, ""

    async def remove_group(self, group_name: str) -> Tuple[bool, str]:
        LOGGER.debug(f"# remove_group({group_name})")
        group_dir_path = self.work_dir / group_name
        if not group_dir_path:
            return False, f"can't remove group '{group_name}'"

        # remove files
        for feed_dir_path in group_dir_path.iterdir():
            feed_name = feed_dir_path.name
            self._remove_public_img_pdf_feed_files(feed_name)

        # git rm & commit
        self._git_rm(group_dir_path)

        # remove remainder files and directories
        if group_dir_path.is_dir():
            rmtree(group_dir_path)

        # re-scan feeds by group
        self.scan_all_feeds()
        self.problem_manager.reload_htaccess_file()
        for feed_dir_path in group_dir_path.iterdir():
            self.problem_manager.remove_config_rss_file_from_info(feed_dir_path)
            feed_file_path = self.public_feed_dir / f"{feed_dir_path.name}.xml"
            self.problem_manager.remove_public_feed_file_from_info(feed_file_path)
            self.problem_manager.remove_progress_from_info(feed_dir_path)
            self.problem_manager.remove_html_file_in_path_from_info("feed_dir_path", feed_dir_path)
        self.problem_manager.load_all_httpd_access_files()
        return True, ""

    async def toggle_feed(self, group_name: str, feed_name: str) -> Tuple[str, str]:
        LOGGER.debug(f"# toggle_feed({group_name}, {feed_name})")
        if feed_name.startswith("_"):
            new_feed_name = feed_name[1:]
        else:
            new_feed_name = "_" + feed_name

        # rename feed directory
        feed_dir_path = self.work_dir / group_name / feed_name
        new_feed_dir_path = self.work_dir / group_name / new_feed_name
        if not feed_dir_path.is_dir():
            return "", f"can't find such a directory '{PathUtil.convert_path_to_str(feed_dir_path)}'"
        # git mv & commit
        self._git_mv(feed_dir_path, new_feed_dir_path)

        # re-scan feeds by group
        self._scan_feeds_by_group(group_name)

        self.problem_manager.reload_htaccess_file()
        self.problem_manager.update_feed_info(feed_dir_path)
        return new_feed_name, ""

    async def toggle_group(self, group_name: str) -> Tuple[str, str]:
        LOGGER.debug(f"# toggle_group({group_name})")
        if group_name.startswith("_"):
            new_group_name = group_name[1:]
        else:
            new_group_name = "_" + group_name

        # rename feed directory
        group_dir_path = self.work_dir / group_name
        new_group_dir_path = self.work_dir / new_group_name
        if not group_dir_path.is_dir():
            return "", f"can't find such a directory '{PathUtil.convert_path_to_str(group_dir_path)}'"
        # git mv & commit
        self._git_mv(group_dir_path, new_group_dir_path)

        # re-scan feeds by group
        self.scan_all_feeds()
        self.problem_manager.reload_htaccess_file()
        if group_name.startswith("_"):
            # enable
            for feed_dir_path in new_group_dir_path.iterdir():
                self.problem_manager.add_config_rss_file_to_info(feed_dir_path)
                feed_file_path = self.public_feed_dir / f"{feed_dir_path.name}.xml"
                self.problem_manager.add_public_feed_file_to_info(feed_file_path)
                self.problem_manager.add_progress_to_info(feed_dir_path)
                self.problem_manager.add_html_files_in_path_to_info(feed_dir_path)
        else:
            # disable
            for feed_dir_path in group_dir_path.iterdir():
                self.problem_manager.remove_config_rss_file_from_info(feed_dir_path)
                feed_file_path = self.public_feed_dir / f"{feed_dir_path.name}.xml"
                self.problem_manager.remove_public_feed_file_from_info(feed_file_path)
                self.problem_manager.remove_progress_from_info(feed_dir_path)
                self.problem_manager.remove_html_file_in_path_from_info("feed_dir_path", feed_dir_path)
        self.problem_manager.load_all_httpd_access_files()
        return new_group_name, ""

    @staticmethod
    async def get_alias(group_name: str, feed_name: str):
        LOGGER.debug(f"# get_alias({group_name}, {feed_name})")
        result, error = Htaccess.get_alias(group_name, feed_name)
        if not result:
            return "", error
        return result, ""

    async def remove_alias(self, group_name: str, feed_name: str):
        LOGGER.debug(f"# remove_alias({group_name}, {feed_name})")
        result, error = Htaccess.remove_alias(group_name, feed_name)
        if not result:
            return False, error
        self.problem_manager.reload_htaccess_file()
        return True, ""

    async def rename_alias(self, group_name: str, feed_name: str, new_alias: str):
        LOGGER.debug(f"# rename_alias({group_name}, {feed_name}, {new_alias})")
        result, error = Htaccess.set_alias(group_name, feed_name, new_alias)
        if not result:
            return False, error
        self.problem_manager.reload_htaccess_file()
        return True, ""

    @staticmethod
    async def check_running(group_name: str, feed_name: str) -> bool:
        # LOGGER.debug(f"# check_running({group_name}, {feed_name})")
        return FeedMakerRunner.check_running(group_name, feed_name)
