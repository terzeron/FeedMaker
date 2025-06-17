#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
from pathlib import Path
import json
import logging.config
from shutil import rmtree
from typing import Any, Optional
from bin.run import FeedMakerRunner
from bin.feed_maker_util import Process, PathUtil, Env
from bin.feed_manager import FeedManager
from bin.access_log_manager import AccessLogManager
from bin.html_file_manager import HtmlFileManager
from bin.problem_manager import ProblemManager
from utils.search_manga_site import SearchManager

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger(__name__)


class FeedMakerManager:
    work_dir_path = Path(Env.get("FM_WORK_DIR"))
    img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX"))
    pdf_dir_path = Path(Env.get("WEB_SERVICE_PDF_DIR_PREFIX"))
    CONF_FILE = "conf.json"
    SITE_CONF_FILE = "site_config.json"

    def __init__(self) -> None:
        self.feed_manager = FeedManager()
        self.access_log_manager = AccessLogManager()
        self.html_file_manager = HtmlFileManager()
        self.problem_manager = ProblemManager()

    def __del__(self) -> None:
        del self.feed_manager
        del self.access_log_manager
        del self.html_file_manager
        del self.problem_manager

    async def aclose(self) -> None:
        return None

    def _git_add(self, feed_dir_path: Path) -> tuple[str, Optional[str]]:
        feed_name = feed_dir_path.name
        conf_file_relative = PathUtil.short_path(feed_dir_path)
        os.chdir(self.work_dir_path)
        cmd = f"git add {conf_file_relative} && git commit -m 'add {feed_name}'"
        return Process.exec_cmd(cmd, dir_path=self.work_dir_path)

    def _git_rm(self, feed_dir_path: Path) -> tuple[str, Optional[str]]:
        feed_name = feed_dir_path.name
        conf_file_relative = PathUtil.short_path(feed_dir_path)
        os.chdir(self.work_dir_path)
        cmd = f"git rm -r {conf_file_relative} && git commit -m 'remove {feed_name}'"
        return Process.exec_cmd(cmd, dir_path=self.work_dir_path)

    def _git_mv(self, feed_dir_path: Path, new_feed_dir_path: Path) -> tuple[str, Optional[str]]:
        feed_dir_name = feed_dir_path.name
        new_feed_dir_name = new_feed_dir_path.name
        feed_dir_path_relative = PathUtil.short_path(feed_dir_path)
        new_feed_dir_path_relative = PathUtil.short_path(new_feed_dir_path)
        os.chdir(self.work_dir_path)
        cmd = f"git mv {feed_dir_path_relative} {new_feed_dir_path_relative} && git commit -m 'rename {feed_dir_name} to {new_feed_dir_name}' || mv {feed_dir_path_relative} {new_feed_dir_path_relative}"
        return Process.exec_cmd(cmd, dir_path=self.work_dir_path)

    def _read_config_file(self, feed_dir_path: Path) -> dict[str, Any]:
        conf_file_path = feed_dir_path / self.CONF_FILE
        if conf_file_path.is_file():
            with conf_file_path.open('r', encoding='utf-8') as infile:
                line_list: list[str] = []
                for line in infile:
                    line_list.append(line)
                json_data = json.loads(''.join(line_list))
                if "configuration" not in json_data:
                    LOGGER.error("can't find normal configuration '%s'", PathUtil.short_path(feed_dir_path))
                    return {}
                configuration: dict[str, Any] = json_data["configuration"]
                return configuration
        return {}

    @staticmethod
    def _get_title_from_configuration(configuration: dict[str, Any], feed_name: str) -> str:
        if configuration and "rss" in configuration and "title" in configuration["rss"]:
            title = configuration["rss"]["title"].split("::")[0]
        else:
            title = feed_name
        return title

    async def get_exec_result(self) -> tuple[str, str]:
        LOGGER.debug("# get_exec_result()")
        exec_result_file_path = self.work_dir_path / "logs" / "run_all_feeds_summary.log"
        if exec_result_file_path.is_file():
            with exec_result_file_path.open('r', encoding='utf-8') as infile:
                return infile.read(), ""
        else:
            return "", f"can't find such file '{PathUtil.short_path(exec_result_file_path)}'"

    @staticmethod
    async def get_problems_status_info() -> tuple[dict[str, dict[str, Any]], str]:
        LOGGER.debug("# get_problems_status_info()")
        feed_name_status_info = ProblemManager.get_feed_name_status_info_map()
        return feed_name_status_info, ""

    @staticmethod
    async def get_problems_progress_info() -> tuple[dict[str, dict[str, Any]], str]:
        LOGGER.debug("# get_problems_progress_info()")
        return FeedManager.get_feed_name_progress_info_map(), ""

    @staticmethod
    async def get_problems_public_feed_info() -> tuple[dict[str, dict[str, Any]], str]:
        LOGGER.debug("# get_problems_public_feed_info()")
        return FeedManager.get_feed_name_public_feed_info_map(), ""

    async def get_problems_html_info(self) -> tuple[dict[str, Any], str]:
        LOGGER.debug("# get_problems_html_info()")
        return {
            "html_file_size_map": self.html_file_manager.get_html_file_size_map(),
            "html_file_with_many_image_tag_map": self.html_file_manager.get_html_file_with_many_image_tag_map(),
            "html_file_without_image_tag_map": self.html_file_manager.get_html_file_without_image_tag_map(),
            "html_file_image_not_found_map": self.html_file_manager.get_html_file_image_not_found_map()
        }, ""

    @staticmethod
    async def get_problems_element_info() -> tuple[dict[str, Any], str]:
        LOGGER.debug("# get_problems_element_info()")
        return FeedManager.get_element_name_count_map(), ""

    @staticmethod
    async def get_problems_list_url_info() -> tuple[dict[str, Any], str]:
        LOGGER.debug("# get_problems_list_url_info()")
        return FeedManager.get_feed_name_list_url_count_map(), ""

    @staticmethod
    def _determine_keyword_in_config_item(keyword: str, config: dict[str, Any], *args: str) -> bool:
        config_item: dict[str, Any] = config
        for arg in args:
            if arg in config_item:
                config_item = config_item[arg]
        return keyword in config_item

    @staticmethod
    async def search(keywords: str) -> tuple[list[dict[str, Any]], str]:
        LOGGER.debug("# search(keywords='%s')", keywords)
        keyword_list = keywords.split(' ')
        result = FeedManager.search(keyword_list)
        if result:
            return result, ""
        return [], f"can't search feed or group matching '{keywords}'"

    @staticmethod
    async def search_site(keyword: str) -> tuple[list[tuple[str, str]], str]:
        LOGGER.debug("# search_site(keyword='%s')", keyword)
        search_manager = SearchManager()
        result = search_manager.search("", keyword)
        if result:
            return result, ""
        return [], f"can't search site matching '{keyword}'"

    @staticmethod
    def _compare_names(x: dict[str, Any], y: dict[str, Any]) -> int:
        if x['name'][0] == "_" and y['name'][0] != "_":
            return 1
        if x['name'][0] != "_" and y['name'][0] == "_":
            return -1
        if x['name'] < y['name']:
            return -1
        if x['name'] > y['name']:
            return 1
        return 0

    @staticmethod
    async def get_groups() -> tuple[list[dict[str, Any]], str]:
        LOGGER.debug("# get_groups()")
        result = FeedManager.get_groups()
        if result:
            return result, ""
        return [], "no group list"

    @staticmethod
    def _compare_title(x: dict[str, Any], y: dict[str, Any]) -> int:
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

    async def get_site_config(self, group_name: str) -> tuple[dict[str, str], str]:
        LOGGER.debug("# get_site_config(group_name='%s')", group_name)
        path = self.work_dir_path / group_name / self.SITE_CONF_FILE
        if path.is_file():
            with path.open('r', encoding='utf-8') as infile:
                json_data = json.load(infile)
                return json_data, ""
        return {}, f"no feed list in group '{group_name}'"

    async def save_site_config(self, group_name: str, post_data: dict[str, Any]) -> tuple[bool, str]:
        LOGGER.debug("# save_site_config(group_name='%s', post_data=%r)", group_name, post_data)
        path = self.work_dir_path / group_name / self.SITE_CONF_FILE
        try:
            with path.open('w', encoding='utf-8') as outfile:
                outfile.write(json.dumps(post_data, indent=2, ensure_ascii=False))
        except IOError as e:
            return False, str(e)
        return True, ""

    @staticmethod
    async def get_feeds_by_group(group_name: str) -> tuple[list[dict[str, str]], str]:
        LOGGER.debug("# get_feeds_by_group(group_name='%s')", group_name)
        result = FeedManager.get_feeds_by_group(group_name)
        if result:
            result.sort(key=lambda obj: obj["title"])
            return result, ""
        return [], f"no feed list in group '{group_name}'"

    @staticmethod
    async def get_feed_info_by_name(group_name: str, feed_name: str) -> tuple[dict[str, Any], str]:
        LOGGER.debug("# get_feed_info_by_name(group_name='%s', feed_name='%s')", group_name, feed_name)
        feed_info = FeedManager.get_feed_info(group_name, feed_name)
        if feed_info:
            return feed_info, ""
        return {}, f"can't get feed info of '{group_name}/{feed_name}'"

    async def save_config_file(self, group_name: str, feed_name: str, post_data: dict[str, Any]) -> tuple[bool, str]:
        LOGGER.debug("# save_config_file(group_name='%s', feed_name='%s', post_data=%r)", group_name, feed_name, post_data)
        if "configuration" not in post_data:
            return False, "invalid configuration format (no 'configuration')"

        configuration = post_data["configuration"]
        if not ("collection" in configuration and "extraction" in configuration and "rss" in configuration):
            return False, "invalid configuration format (no 'collection' or 'extraction' or 'rss')"

        config_file_path = self.work_dir_path / group_name / feed_name / self.CONF_FILE
        config_file_path.parent.mkdir(exist_ok=True)
        with config_file_path.open('w', encoding='utf-8') as outfile:
            outfile.write(json.dumps(post_data, indent=2, ensure_ascii=False))

        self._git_add(config_file_path)

        # re-scan feeds by group
        FeedManager.add_config_info(config_file_path.parent)
        FeedManager.add_rss_info(config_file_path.parent)
        return True, ""

    def run(self, group_name: str, feed_name: str) -> tuple[bool, str]:
        LOGGER.debug("# run(group_name='%s', feed_name='%s')", group_name, feed_name)
        feed_dir_path = self.work_dir_path / group_name / feed_name
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
            else:
                return False, "invalid format of configuration file"

        self.problem_manager.update_feed_info(feed_dir_path)
        return True, ""

    def _remove_public_img_pdf_feed_files(self, feed_name: str) -> None:
        LOGGER.debug("# _remove_public_img_pdf_feed_files(feed_name='%s')", feed_name)
        feed_img_dir_path = self.img_dir_path / feed_name
        feed_pdf_dir_path = self.pdf_dir_path / feed_name

        # remove files
        if feed_img_dir_path.is_dir():
            LOGGER.debug("deleting %s", PathUtil.short_path(feed_img_dir_path))
            rmtree(feed_img_dir_path)
        if feed_pdf_dir_path.is_dir():
            LOGGER.debug("deleting %s", PathUtil.short_path(feed_pdf_dir_path))
            rmtree(feed_pdf_dir_path)

    async def remove_list(self, group_name: str, feed_name: str) -> None:
        LOGGER.debug("# remove_list(group_name='%s', feed_name='%s')", group_name, feed_name)
        feed_dir_path = self.work_dir_path / group_name / feed_name
        list_dir_path = feed_dir_path / "newlist"
        if list_dir_path.is_dir():
            rmtree(list_dir_path)

    async def remove_html(self, group_name: str, feed_name: str) -> None:
        LOGGER.debug("# remove_html(group_name='%s', feed_name='%s')", group_name, feed_name)
        feed_dir_path = self.work_dir_path / group_name / feed_name
        html_dir_path = feed_dir_path / "html"
        if html_dir_path.is_dir():
            rmtree(html_dir_path)
        self.html_file_manager.remove_html_file_in_path_from_info("feed_dir_path", feed_dir_path, do_remove_file=True)

    async def remove_html_file(self, group_name: str, feed_name: str, html_file_name: str) -> None:
        LOGGER.debug("# remove_html_file(group_name='%s', feed_name='%s')", group_name, feed_name)
        html_file_path = self.work_dir_path / group_name / feed_name / "html" / html_file_name
        html_file_path.unlink(missing_ok=True)
        self.html_file_manager.remove_html_file_in_path_from_info("file_path", html_file_path, do_remove_file=True)

    async def remove_public_feed(self, feed_name: str) -> None:
        LOGGER.debug("# remove_public_feed(feed_name='%s')", feed_name)
        self.feed_manager.remove_public_feed_by_feed_name(feed_name, do_remove_file=True)

    async def remove_feed(self, group_name: str, feed_name: str) -> tuple[bool, str]:
        LOGGER.debug(f"# remove_feed({group_name}, {feed_name})")
        feed_dir_path = self.work_dir_path / group_name / feed_name
        conf_file_path = feed_dir_path / self.CONF_FILE
        if not feed_dir_path or not conf_file_path:
            return False, f"can't remove feed '{PathUtil.short_path(feed_dir_path)}'"

        # remove files
        self._remove_public_img_pdf_feed_files(feed_name)

        # git rm & commit
        self._git_rm(feed_dir_path)

        # remove remainder files and directories
        if feed_dir_path.is_dir():
            rmtree(feed_dir_path)

        # re-scan feed
        FeedManager.remove_config_info(feed_dir_path, do_remove_file=True)
        FeedManager.remove_rss_info(feed_dir_path, do_remove_file=True)
        self.feed_manager.remove_public_feed_by_feed_name(feed_name, do_remove_file=True)
        FeedManager.remove_progress_info(feed_dir_path, do_remove_file=True)
        AccessLogManager.remove_httpd_access_info(feed_dir_path)
        self.html_file_manager.remove_html_file_in_path_from_info("feed_dir_path", feed_dir_path, do_remove_file=True)
        return True, ""

    async def remove_group(self, group_name: str) -> tuple[bool, str]:
        LOGGER.debug(f"# remove_group({group_name})")
        group_dir_path = self.work_dir_path / group_name
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
        for feed_dir_path in group_dir_path.iterdir():
            FeedManager.remove_config_info(feed_dir_path, do_remove_file=True)
            FeedManager.remove_rss_info(feed_dir_path, do_remove_file=True)
            self.feed_manager.remove_public_feed_by_feed_name(feed_dir_path.name, do_remove_file=True)
            FeedManager.remove_progress_info(feed_dir_path, do_remove_file=True)
            AccessLogManager.remove_httpd_access_info(feed_dir_path)
            self.html_file_manager.remove_html_file_in_path_from_info("feed_dir_path", feed_dir_path, do_remove_file=True)
        return True, ""

    @staticmethod
    async def toggle_feed(feed_name: str) -> tuple[str, str]:
        LOGGER.debug("# toggle_feed(feed_name='%s')", feed_name)

        if FeedManager.toggle_feed(feed_name):
            return feed_name, ""
        return "", f"can't toggle feed '{feed_name}'"

    @staticmethod
    async def toggle_group(group_name: str) -> tuple[str, str]:
        LOGGER.debug(f"# toggle_group({group_name})")

        if FeedManager.toggle_group(group_name):
            return group_name, ""
        return "", f"can't toggle group '{group_name}'"

    @staticmethod
    async def check_running(group_name: str, feed_name: str) -> Optional[bool]:
        # LOGGER.debug(f"# check_running({group_name}, {feed_name})")
        return FeedMakerRunner.check_running(group_name, feed_name)
