#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import re
import subprocess
import hashlib
import json
import base64
import logging.config
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from urllib.parse import urlparse, urlunparse, quote, urljoin, urlsplit
from typing import Any, Optional, Union, TypeVar, Sequence
from collections.abc import Hashable
import psutil
from bs4 import Tag


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()
# noinspection PyPep8
header_str = '''<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no"/>
<style>img { max-width: 100%; margin-top: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; } table { border-width: thin; border-style: dashed; }</style>

'''

T = TypeVar('T', bound=Union[Hashable, dict[str, Any], list[Any]])
K = TypeVar('K', bound=Hashable)
V = TypeVar('V')


class Data:
    @staticmethod
    def _to_hashable(item: Union[dict[str, Any], list[Any], Any]) -> Union[Hashable, tuple[tuple[str, Hashable], ...], tuple[Hashable, ...]]:
        if isinstance(item, dict):
            return tuple((str(k), Data._to_hashable(v)) for k, v in sorted(item.items()))
        if isinstance(item, list):
            return tuple(Data._to_hashable(x) for x in item)
        if not isinstance(item, Hashable):
            raise TypeError(f"Item must be hashable, got {type(item)}")
        return item

    @staticmethod
    def remove_duplicates(a_list: Sequence[T]) -> list[T]:
        seen: dict[Hashable, bool] = {}
        unique_result: list[T] = []
        for item in a_list:
            hashable_item = Data._to_hashable(item)
            if hashable_item in seen and seen[hashable_item]:
                continue
            seen[hashable_item] = True
            unique_result.append(item)
        return unique_result

    @staticmethod
    def _get_sorted_lines_from_rss_file(file: Path) -> list[str]:
        line_list: list[str] = []
        with file.open("r", encoding="utf-8") as infile:
            lines = infile.readlines()
            for line in lines:
                line = re.sub(r"(<!\[CDATA\[|]]>)", "", line)
                line = re.sub(r"<(pubDate|lastBuildDate)>[^<>]+</(pubDate|lastBuildDate)>", "", line)
                line = re.sub(r"</?\??\w+([^<>]*)>", "\n", line)
                for a_line in line.split("\n"):
                    if re.search(r"^\s*$", a_line):
                        continue
                    line_list.append(a_line)
        return sorted(line_list)

    @staticmethod
    def compare_two_rss_files(file1: Path, file2: Path) -> bool:
        # 두 파일에서 element 태그를 모두 삭제하고 나머지 텍스트 내용을 비교
        line_list1 = Data._get_sorted_lines_from_rss_file(file1)
        line_list2 = Data._get_sorted_lines_from_rss_file(file2)
        return line_list1 == line_list2


class Process:
    @staticmethod
    def _replace_script_path(script: str, dir_path: Path) -> Optional[str]:
        if not dir_path or not dir_path.is_dir():
            return None

        program = script.split(" ")[0]
        program_full_path_str: Optional[str]

        if program.startswith("/"):
            # absolute path
            program_full_path_str = program
        elif program.startswith("./") or program.startswith("../"):
            # relative path
            program_full_path = (dir_path / program).resolve()
            if not program_full_path.exists():
                return None
            program_full_path_str = str(program_full_path)
        else:
            # non-absolute path
            program_full_path_str = which(program)
            if not program_full_path_str:
                return None

        # For absolute and relative paths, check if file exists, is file or symlink, and is executable
        if program.startswith("/") or program.startswith("./") or program.startswith("../"):
            p = Path(program_full_path_str)
            resolved = p.resolve()
            if not (resolved.exists() and resolved.is_file() and os.access(str(resolved), os.X_OK)):
                return None
        # For non-absolute paths, which() already checked existence
        elif not which(program_full_path_str):
            return None

        result = program_full_path_str
        if len(script.split(" ")) > 1:
            result += " " + " ".join(script.split(" ")[1:])
        return result

    @staticmethod
    def exec_cmd(cmd: str, dir_path: Path = Path.cwd(), input_data: Optional[str] = None) -> tuple[str, str]:
        LOGGER.debug("# Process.exec_cmd(cmd=%s, dir_path=%s, input_data=%d bytes)", cmd, PathUtil.short_path(dir_path), len(input_data) if input_data else 0)
        new_cmd = Process._replace_script_path(cmd, dir_path)
        if not new_cmd:
            return "", f"Error in getting path of executable '{cmd}'"
        LOGGER.debug(new_cmd)
        try:
            with subprocess.Popen(new_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8") as p:
                result, error = p.communicate(input=input_data)
                if error and "InsecureRequestWarning" not in error and "_RegisterApplication(), FAILED TO establish the default connection to the WindowServer" not in error:
                    if "error" in error.lower():
                        return "", error
                    else:
                        LOGGER.warning(error)

        except subprocess.CalledProcessError as e:
            return "", f"Error with non-zero exit status, {e}"
        except subprocess.SubprocessError as e:
            return "", f"Error in execution of command, {e}"
        return result or "", ""

    @staticmethod
    def _find_process_list(proc_expr: str) -> list[int]:
        matched_pid_list: list[int] = []
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=["pid", "cmdline"])
            except psutil.NoSuchProcess:
                continue

            pid = pinfo.get("pid")
            if not pid:
                continue

            cmdline_list = pinfo.get("cmdline") or []
            merged_cmdline = " ".join(cmdline_list)

            if re.search(proc_expr, merged_cmdline):
                matched_pid_list.append(pid)
        return matched_pid_list

    @staticmethod
    def kill_process_group(proc_expr: str) -> int:
        pid_list = Process._find_process_list(proc_expr)
        count = 0
        for pid in pid_list:
            try:
                psutil.Process(pid).terminate()
                count += 1
            except psutil.NoSuchProcess:
                pass
        return count


class Datetime:
    @staticmethod
    def get_current_time() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _get_time_str(dt: datetime) -> str:
        return dt.isoformat(timespec="seconds")

    @staticmethod
    def get_current_time_str() -> str:
        return Datetime._get_time_str(Datetime.get_current_time())

    @staticmethod
    def get_rss_date_str() -> str:
        dt = Datetime.get_current_time()
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")

    @staticmethod
    def get_short_date_str(dt: Optional[datetime] = None) -> str:
        if not dt:
            dt = Datetime.get_current_time()
        return dt.strftime("%Y%m%d")

    @staticmethod
    def convert_datetime_to_str(d: Optional[Union[str, datetime]]) -> Optional[str]:
        if not d:
            return None
        if isinstance(d, str):
            return d
        return d.strftime("%Y-%m-%d %H:%M:%S")


class HTMLExtractor:
    @staticmethod
    def get_first_token_from_path(path_str: Optional[str]) -> tuple[
        Optional[str], Optional[str], Optional[int], Optional[str], bool]:
        if not path_str:
            return None, None, None, None, False
        is_anywhere: bool = False
        if path_str[0:2] == "//":
            is_anywhere = True
        tokens: list[str] = path_str.split("/")
        i: int = 0
        valid_token: str = ""
        for token in tokens:
            valid_token = token
            i += 1
            if token not in ("", "html", "body"):
                # 첫번째 유효한 토큰만 꺼내옴
                break

        # 해당 토큰에 대해 정규식 매칭 시도
        pattern = re.compile(r'''
            (
              (?P<name>\w+)
              (?:\[
                (?P<index>\d+)
              ])?
            |
              \*\[@id=\"(?P<id>\w+)\"]
            )
        ''', re.VERBOSE)
        m = pattern.match(valid_token)
        if m:
            name = m.group("name")
            index = int(m.group("index")) if m.group("index") else None
            id_str = m.group("id")
        else:
            return None, None, None, None, False

        # id, name, idx, path의 나머지 부분, is_anywhere을 반환
        return id_str, name, index, "/".join(tokens[i:]), is_anywhere

    @staticmethod
    def get_node_with_path(node: Tag, path_str: Optional[str]) -> Optional[list[Tag]]:
        if not node:
            return None
        node_list: list[Tag] = []

        (node_id, name, idx, next_path_str, is_anywhere) = HTMLExtractor.get_first_token_from_path(path_str)

        if node_id:
            # print "searching with id"
            # 특정 id로 노드를 찾아서 현재 노드에 대입
            nodes = node.find_all(attrs={"id": node_id})
            if not nodes or nodes == []:
                # print("error, no id matched")
                return None
            if len(nodes) > 1:
                # print("error, two or more id matched")
                return None
            node_list.append(nodes[0])
            result_node_list = HTMLExtractor.get_node_with_path(nodes[0], next_path_str)
            if result_node_list:
                node_list = result_node_list
        else:
            if not name:
                return None

            i = 1
            for child in node.contents:
                if isinstance(child, Tag):
                    # print "i=%d child='%s', idx=%s" % (i, child.name, idx)
                    # 이름이 일치하거나 //로 시작한 경우
                    if child.name == name:
                        if not idx or i == idx:
                            # 인덱스가 지정되지 않았거나, 지정되었고 인덱스가 일치할 때
                            if next_path_str == "":
                                # 단말 노드이면 현재 일치한 노드를 반환
                                # print "*** append! child='%s'" % child.name
                                node_list.append(child)
                            else:
                                # 중간 노드이면 recursion
                                # print "*** recursion ***"
                                result_node_list = HTMLExtractor.get_node_with_path(child, next_path_str)
                                if result_node_list:
                                    node_list.extend(result_node_list)
                        if idx and i == idx:
                            break
                        # 이름이 일치했을 때만 i를 증가시킴
                        i = i + 1
                    if is_anywhere:
                        result_node_list = HTMLExtractor.get_node_with_path(child, name)
                        if result_node_list:
                            node_list.extend(result_node_list)
        return node_list


class IO:
    @staticmethod
    def read_stdin() -> str:
        line_list = IO.read_stdin_as_line_list()
        return "".join(line_list)

    @staticmethod
    def read_stdin_as_line_list() -> list[str]:
        line_list: list[str] = []
        for line in sys.stdin:
            line_list.append(line)
        return line_list


class NotFoundEnvError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class Env:
    @staticmethod
    def get(var: str, default_value: str = "") -> str:
        value = os.getenv(var, default_value)
        if value is None:
            raise NotFoundEnvError(f"can't get environment variable '{var}'")
        return value


class NotFoundConfigFileError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidConfigFileError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class NotFoundConfigItemError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class Config:
    conf: dict[str, dict[str, Any]] = {}

    def __init__(self, feed_dir_path: Path = Path.cwd()) -> None:
        LOGGER.debug("# Config(feed_dir_path=%s)", PathUtil.short_path(feed_dir_path))
        conf_file = os.getenv("FM_CONF_FILE", "")
        if conf_file:
            config_file_path = Path(conf_file)
        else:
            config_file_path = feed_dir_path / "conf.json"
        if config_file_path.is_file():
            with config_file_path.open('r', encoding="utf-8") as infile:
                data = json.load(infile)
                if "configuration" in data:
                    self.conf = data.get("configuration", {})
                    return
                    
                raise InvalidConfigFileError(f"can't get configuration from '{config_file_path} with invalid format")
        else:
            raise NotFoundConfigFileError(f"can't find configuration file '{config_file_path}'")

    @staticmethod
    def _get_bool_config_value(config_node: dict[str, Any], key: str, default: bool = False) -> bool:
        value: bool = default
        if key in config_node:
            value = config_node[key]
        return value

    @staticmethod
    def _get_str_config_value(config_node: dict[str, Any], key: str, default: Optional[str] = None) -> Optional[str]:
        value: Optional[str] = default
        if key in config_node:
            value = config_node[key]
        return value

    @staticmethod
    def _get_int_config_value(config_node: dict[str, Any], key: str, default: Optional[int] = None) -> Optional[int]:
        value: Optional[int] = default
        if key in config_node:
            try:
                value = int(config_node[key])
            except TypeError:
                value = None
        return value

    @staticmethod
    def _get_float_config_value(config_node: dict[str, Any], key: str, default: Optional[float] = None) -> Optional[float]:
        value: Optional[float] = default
        if key in config_node:
            try:
                value = float(config_node[key])
            except TypeError:
                value = None
        return value

    @staticmethod
    def _get_list_config_value(config_node: dict[str, Any], key: str, default: Optional[list[Any]] = None) -> Optional[list[Any]]:
        value: Optional[list[Any]] = default if default else []
        if key in config_node:
            try:
                value = config_node[key]
            except TypeError:
                value = None
        return value

    @staticmethod
    def _get_dict_config_value(config_node: dict[str, Any], key: str, default: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        value: Optional[dict[str, Any]] = default if default else {}
        if key in config_node:
            try:
                value = config_node[key]
            except TypeError:
                value = None
        return value

    def get_collection_configs(self) -> dict[str, Any]:
        LOGGER.debug("# get_collection_configs()")
        if "collection" in self.conf:
            collection_conf = self.conf.get("collection", {})
            if collection_conf:
                conf = {
                    "render_js": Config._get_bool_config_value(collection_conf, "render_js", False),
                    "verify_ssl": Config._get_bool_config_value(collection_conf, "verify_ssl", True),
                    "ignore_old_list": Config._get_bool_config_value(collection_conf, "ignore_old_list", False),
                    "is_completed": Config._get_bool_config_value(collection_conf, "is_completed", False),
                    "copy_images_from_canvas": Config._get_bool_config_value(collection_conf, "copy_images_from_canvas", False),
                    "simulate_scrolling": Config._get_bool_config_value(collection_conf, "simulate_scrolling", False),
                    "disable_headless": Config._get_bool_config_value(collection_conf, "disable_headless", False),
                    "blob_to_dataurl": Config._get_bool_config_value(collection_conf, "blob_to_dataurl", False),

                    "item_capture_script": Config._get_str_config_value(collection_conf, "item_capture_script", "./capture_item_link_title.py"),
                    "sort_field_pattern": Config._get_str_config_value(collection_conf, "sort_field_pattern"),
                    "user_agent": Config._get_str_config_value(collection_conf, "user_agent"),
                    "encoding": Config._get_str_config_value(collection_conf, "encoding", "utf-8"),
                    "referer": Config._get_str_config_value(collection_conf, "referer"),

                    "timeout": Config._get_int_config_value(collection_conf, "timeout", 60),
                    "unit_size_per_day": Config._get_float_config_value(collection_conf, "unit_size_per_day", 1),
                    "num_retries": Config._get_int_config_value(collection_conf, "num_retries", 1),
                    "window_size": Config._get_int_config_value(collection_conf, "window_size", 5),

                    "list_url_list": Config._get_list_config_value(collection_conf, "list_url_list", []),
                    "post_process_script_list": Config._get_list_config_value(collection_conf, "post_process_script_list", []),
                    "headers": Config._get_dict_config_value(collection_conf, "headers", {})
                }
                return conf

        raise NotFoundConfigItemError("can't get configuration item 'collection'")

    def get_extraction_configs(self) -> dict[str, Any]:
        LOGGER.debug("# get_extraction_configs()")
        if "extraction" in self.conf:
            extraction_conf = self.conf.get("extraction", {})
            if extraction_conf:
                conf = {
                    "render_js": Config._get_bool_config_value(extraction_conf, "render_js", False),
                    "verify_ssl": Config._get_bool_config_value(extraction_conf, "verify_ssl", True),
                    "bypass_element_extraction": Config._get_bool_config_value(extraction_conf, "bypass_element_extraction"),
                    "force_sleep_between_articles": Config._get_bool_config_value(extraction_conf, "force_sleep_between_articles"),
                    "copy_images_from_canvas": Config._get_bool_config_value(extraction_conf, "copy_images_from_canvas"),
                    "simulate_scrolling": Config._get_bool_config_value(extraction_conf, "simulate_scrolling"),
                    "disable_headless": Config._get_bool_config_value(extraction_conf, "disable_headless", False),
                    "blob_to_dataurl": Config._get_bool_config_value(extraction_conf, "blob_to_dataurl", False),

                    "user_agent": Config._get_str_config_value(extraction_conf, "user_agent"),
                    "encoding": Config._get_str_config_value(extraction_conf, "encoding", "utf-8"),
                    "referer": Config._get_str_config_value(extraction_conf, "referer"),

                    "threshold_to_remove_html_with_incomplete_image": Config._get_int_config_value(extraction_conf, "threshold_to_remove_html_with_incomplete_image", 0),
                    "timeout": Config._get_int_config_value(extraction_conf, "timeout", 60),
                    "num_retries": Config._get_int_config_value(extraction_conf, "num_retries", 1),

                    "element_id_list": Config._get_list_config_value(extraction_conf, "element_id_list", []),
                    "element_class_list": Config._get_list_config_value(extraction_conf, "element_class_list", []),
                    "element_path_list": Config._get_list_config_value(extraction_conf, "element_path_list", []),
                    "post_process_script_list": Config._get_list_config_value(extraction_conf, "post_process_script_list", []),
                    "headers": Config._get_dict_config_value(extraction_conf, "headers", {}),
                }
                return conf
            
        raise NotFoundConfigItemError("can't get configuration item 'extraction'")

    def get_rss_configs(self) -> dict[str, Any]:
        LOGGER.debug("# get_rss_configs()")
        if "rss" in self.conf:
            rss_conf = self.conf.get("rss", {})
            if rss_conf:
                conf = {
                    "ignore_broken_link": Config._get_str_config_value(rss_conf, "ignore_broken_link", ""),
                    "rss_title": Config._get_str_config_value(rss_conf, "title"),
                    "rss_generator": Config._get_str_config_value(rss_conf, "generator"),
                    "rss_copyright": Config._get_str_config_value(rss_conf, "copyright"),
                    "rss_link": Config._get_str_config_value(rss_conf, "link"),
                    "rss_language": Config._get_str_config_value(rss_conf, "language"),
                    "rss_url_prefix_for_guid": Config._get_str_config_value(rss_conf, "url_prefix_for_guid")
                }
                return conf

        raise NotFoundConfigItemError("can't get configuration item 'rss'")


class URL:
    # http://naver.com/api/items?page_no=3 => http
    @staticmethod
    def get_url_scheme(url: str) -> str:
        scheme_separator = "://"
        separator_index = url.find(scheme_separator)
        if separator_index >= 0:
            return url[:separator_index]
        return ""

    # http://naver.com/api/items?page_no=3 => naver.com
    @staticmethod
    def get_url_domain(url: str) -> str:
        scheme_separator = "://"
        host_index = url.find(scheme_separator) + len(scheme_separator)
        if host_index >= 0:
            first_slash_index = url[host_index:].find("/")
            if first_slash_index >= 0:
                return url[host_index:(host_index + first_slash_index)]
            return url[host_index:]
        return ""

    # http://naver.com/api/items?page_no=3 => /api/items?page_no=3
    @staticmethod
    def get_url_path(url: str) -> str:
        scheme_separator = "://"
        host_index = url.find(scheme_separator) + len(scheme_separator)
        if host_index >= 0:
            first_slash_index = url[host_index:].find('/')
            if first_slash_index >= 0:
                return url[(host_index + first_slash_index):]
        return ""

    # http://naver.com/api/items?page_no=3 => http://naver.com/api/
    @staticmethod
    def get_url_prefix(url: str) -> str:
        scheme_separator = "://"
        host_index = url.find(scheme_separator) + len(scheme_separator)
        if host_index >= 0:
            last_slash_index = url.rfind('/', host_index)
            if last_slash_index >= 0:
                return url[:(last_slash_index + 1)]
        return ""

    # http://naver.com/api/items?page_no=3 => http://naver.com/api/items
    @staticmethod
    def get_url_except_query(url: str) -> str:
        query_index = url.find('?')
        if query_index >= 0:
            return url[:query_index]
        return url

    # http://naver.com/api + /data => http://naver.com/data
    # http://naver.com/api + data => http://naver.com/api/data
    # http://naver.com/api/view.nhn?page_no=3 + # => http://naver.com/api/view.nhn?page_no=3
    @staticmethod
    def concatenate_url(full_url: str, url2: str) -> str:
        result = urljoin(full_url, url2)
        if url2.endswith("?"):
            result += "?"
        return result

    @staticmethod
    def get_short_md5_name(content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()[:7]

    @staticmethod
    def encode(url: str) -> Any:
        parsed = urlparse(url)
        quoted_path = quote(parsed.path)
        quoted_query = quote(parsed.query, safe='=')
        parsed = parsed._replace(path=quoted_path, query=quoted_query)
        return urlunparse(parsed)

    @staticmethod
    def encode_suffix(url: str) -> str:
        parsed_url = urlsplit(url)
        prefix = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        url_suffix = url[len(prefix):]
        encoded_suffix = base64.b64encode(url_suffix.encode("utf-8")).decode("utf-8")
        return prefix + encoded_suffix


class FileManager:
    DATA_IMAGE_PREFIX = "data:image"
    IMAGE_NOT_FOUND_IMAGE = "image-not-found.png"
    IMAGE_NOT_FOUND_IMAGE_URL = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/" + IMAGE_NOT_FOUND_IMAGE
    IMAGE_DIR_PATH = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX"))

    @staticmethod
    def _get_cache_info_common_postfix(img_url_for_hashing: str, postfix: Optional[Union[str, int]] = None, index: Optional[int] = None) -> str:
        LOGGER.debug("# get_cache_info_common(img_url_for_hashing='%s'', postfix='%s', index=%r)", img_url_for_hashing[:30], postfix, index)

        # postfix: _pfxstr (valid string)
        postfix_str = ""
        if postfix and postfix != "":
            postfix_str = "_" + str(postfix)

        # index: .1, .2, .3, ... (0 is ignored)
        index_str = ""
        if index:
            index_str = "." + str(index)

        if img_url_for_hashing.startswith(("http", "data:image")):
            return URL.get_short_md5_name(img_url_for_hashing) + postfix_str + index_str
        return URL.get_short_md5_name(img_url_for_hashing)

    @staticmethod
    def get_cache_url(url_prefix: str, img_url_for_hashing: str, postfix: Optional[Union[str, int]] = None, index: Optional[int] = None, suffix: Optional[str] = None) -> str:
        LOGGER.debug("# get_cache_url(url_prefix='%s', img_url_for_hashing='%s', postfix=%r, index=%r, suffix=%r)", url_prefix, img_url_for_hashing[:30], postfix, index, suffix)
        url = url_prefix + "/" + FileManager._get_cache_info_common_postfix(img_url_for_hashing=img_url_for_hashing, postfix=postfix, index=index)
        if suffix:
            url += suffix
        return url

    @staticmethod
    def get_cache_file_path(path_prefix: Path, img_url_for_hashing: str, postfix: Optional[Union[str, int]] = None, index: Optional[int] = None, suffix: Optional[str] = None) -> Path:
        LOGGER.debug("# get_cache_file_path(path_prefix=%r, img_url_for_hashing='%s', postfix='%s', index=%r, suffix=%r)", PathUtil.short_path(path_prefix), img_url_for_hashing[:30], postfix, index, suffix)
        file_path = path_prefix / FileManager._get_cache_info_common_postfix(img_url_for_hashing=img_url_for_hashing, postfix=postfix, index=index)
        if suffix:
            return file_path.with_suffix(file_path.suffix + suffix)
        return file_path

    @staticmethod
    def get_incomplete_image_list(html_file_path: Path) -> list[str]:
        LOGGER.debug("# get_incomplete_image_list(html_file_path='%s')", PathUtil.short_path(html_file_path))
        result: list[str] = []
        feed_name = html_file_path.parent.parent.name
        with html_file_path.open("r", encoding="utf-8") as f:
            try:
                for line in f:
                    if FileManager.IMAGE_NOT_FOUND_IMAGE in line:
                        result.append(FileManager.IMAGE_NOT_FOUND_IMAGE)
                    escaped_image_url_prefix = re.sub(r'https', 'https?', Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"))
                    escaped_image_url_prefix = re.sub(r'\.', '\\.', escaped_image_url_prefix)
                    m = re.search(r'<img src=[\"\']%s/[^/]+/(?P<img>\S+)[\"\']' % escaped_image_url_prefix, line)
                    if m:
                        # 실제로 다운로드되어 있는지 확인
                        img_file_name = m.group("img")
                        img_file_path = FileManager.IMAGE_DIR_PATH / feed_name / img_file_name
                        if not img_file_path.is_file() or img_file_path.stat().st_size == 0:
                            result.append(img_file_name)
            except UnicodeDecodeError as e:
                LOGGER.error("Error: Unicode decode error in '%s'", PathUtil.short_path(html_file_path))
                raise e
        return result

    @staticmethod
    def remove_html_file_without_cached_image_files(html_file_path: Path) -> None:
        LOGGER.debug("# remove_html_file_without_cached_image_files(html_file_path='%s')", PathUtil.short_path(html_file_path))
        incomplete_img_list = FileManager.get_incomplete_image_list(html_file_path)
        if len(incomplete_img_list) > 0:
            LOGGER.info("* '%s' deleted (due to %r)", PathUtil.short_path(html_file_path), incomplete_img_list)
            html_file_path.unlink(missing_ok=True)

    @staticmethod
    def remove_html_files_without_cached_image_files(feed_dir_path: Path, feed_img_dir_path: Path) -> None:
        LOGGER.debug("# remove_html_files_without_cached_image_files(feed_dir_path='%s', feed_img_dir_path='%s')", PathUtil.short_path(feed_dir_path), PathUtil.short_path(feed_img_dir_path))
        LOGGER.info("# deleting html files without cached image files")
        conf = Config(feed_dir_path).get_extraction_configs()
        html_dir_path = feed_dir_path / "html"
        if html_dir_path.is_dir():
            for html_file_path in html_dir_path.iterdir():
                if html_file_path.is_file():
                    threshold_to_remove_html_with_incomplete_image = conf.get("threshold_to_remove_html_with_incomplete_image", 0)
                    if threshold_to_remove_html_with_incomplete_image >= 0:
                        incomplete_image_list = FileManager.get_incomplete_image_list(html_file_path)
                        if threshold_to_remove_html_with_incomplete_image < len(incomplete_image_list):
                            FileManager.remove_html_file_without_cached_image_files(html_file_path)

    @staticmethod
    def remove_image_files_with_zero_size(feed_img_dir_path: Path) -> None:
        LOGGER.debug("# remove_image_files_with_zero_size()")
        LOGGER.info("# deleting image files with zero size")
        if feed_img_dir_path.is_dir():
            for img_file_path in feed_img_dir_path.iterdir():
                if img_file_path.is_file() and img_file_path.stat().st_size == 0:
                    LOGGER.info("* %s", PathUtil.short_path(img_file_path))
                    img_file_path.unlink(missing_ok=True)

    @staticmethod
    def remove_temporary_files(feed_dir_path: Path) -> None:
        LOGGER.debug("# remove_temporary_files(feed_dir_path='%s')", PathUtil.short_path(feed_dir_path))
        LOGGER.info("# deleting temporary files")
        for file in ("nohup.out", "temp.html", "x.html"):
            file_path = feed_dir_path / file
            if file_path.is_file():
                LOGGER.info("* %s", PathUtil.short_path(file_path))
                file_path.unlink(missing_ok=True)

    @staticmethod
    def remove_all_files(feed_dir_path: Path) -> None:
        LOGGER.debug("# remove_all_files(feed_dir_path='%s')", PathUtil.short_path(feed_dir_path))
        LOGGER.info("# deleting all files (html files, list files, rss file, various temporary files)")
        for html_file_path in (feed_dir_path / "html").iterdir():
            LOGGER.info("* %s", PathUtil.short_path(html_file_path))
            html_file_path.unlink(missing_ok=True)
        for list_file_path in (feed_dir_path / "newlist").iterdir():
            LOGGER.info("* %s", PathUtil.short_path(list_file_path))
            list_file_path.unlink(missing_ok=True)

        rss_file_path = feed_dir_path / (feed_dir_path.name + ".xml")
        old_rss_file_path = rss_file_path.with_suffix(rss_file_path.suffix + ".old")
        start_index_file_path = feed_dir_path / "start_idx.txt"
        for file_path in (rss_file_path, old_rss_file_path, start_index_file_path):
            LOGGER.info("* %s", PathUtil.short_path(file_path))
            file_path.unlink(missing_ok=True)

        FileManager.remove_temporary_files(feed_dir_path)


class PathUtil:
    work_dir_path = Path(Env.get("FM_WORK_DIR")).resolve()
    public_feed_dir_path = Path(Env.get("WEB_SERVICE_FEED_DIR_PREFIX")).resolve()

    _work_dir_path_str = str(work_dir_path)
    _public_feed_dir_path_str = str(public_feed_dir_path)

    @staticmethod
    def short_path(path: Optional[Path]) -> str:
        if not path:
            return ""

        path_str = str(path)

        # os.path.abspath를 사용하여 심볼릭 링크를 해석하지 않고 절대 경로를 얻습니다.
        # 이렇게 하면 테스트 환경에서 의도한 경로 구조를 유지할 수 있습니다.
        abs_path_str = os.path.abspath(path_str)

        if abs_path_str.startswith(PathUtil._work_dir_path_str):
            return os.path.relpath(abs_path_str, PathUtil._work_dir_path_str)

        if abs_path_str.startswith(PathUtil._public_feed_dir_path_str):
            return os.path.relpath(abs_path_str, PathUtil._public_feed_dir_path_str)

        return path_str
# Modified
# Another modification
