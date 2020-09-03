#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import io
import codecs
import subprocess
import hashlib
import logging
import logging.config
from datetime import datetime
from typing import List, Any, Dict, Tuple, Optional, Set
import psutil
import xmltodict
from ordered_set import OrderedSet


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()
# noinspection PyPep8
header_str = '''<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no"/>
<style>img { max-width: 100%; margin-top: 0px; margin-bottom: 0px; } table { border-width: thin; border-style: dashed; }</style>

'''


def make_path(path: str) -> None:
    try:
        os.makedirs(path)
    except FileExistsError:
        # ignore
        pass


def exec_cmd(cmd: str, input_data=None) -> Tuple[str, Optional[str]]:
    try:
        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if input_data:
            result, error = p.communicate(input_data.encode("utf-8"))
        else:
            result, error = p.communicate()
        if p.returncode != 0:
            raise subprocess.CalledProcessError(returncode=p.returncode, cmd=cmd, output=result, stderr=error)
        if error:
            # handle warnings
            if b"InsecureRequestWarning" not in error and b"_RegisterApplication(), FAILED TO establish the default connection to the WindowServer" not in error:
                return "", error.decode("utf-8")
    except subprocess.CalledProcessError:
        return "", "Error with non-zero exit status in command '{}'".format(cmd)
    except subprocess.SubprocessError:
        return "", "Error in execution of command '{}'".format(cmd)
    return result.decode(encoding="utf-8"), ""


def send_error_msg(msg: Optional[str], access_token: str, receiver_id: str) -> bool:
    if not msg:
        return False
    LOGGER.debug("send_error_msg('%s')", msg)
    cmd = " ".join(('''
        curl -s -X POST
             -H 'Content-Type:application/json'
             -H 'Authorization: Bearer %s'
             -d '{ "to": "%s", "messages": [ { "type": "text", "text": "%s" } ] }' 
             https://api.line.me/v2/bot/message/push
        ''' % (access_token, receiver_id, msg[:1999])).split("\n"))
    result, error = exec_cmd(cmd)
    if error:
        LOGGER.warning("can't send error message '%s', %s", msg, error)
        return False
    LOGGER.info(result)
    return True


def determine_crawler_options(options: Dict[str, Any]) -> str:
    LOGGER.debug("# determine_crawler_options()")

    option_str: str = ""
    if "render_js" in options:
        option_str += " --render-js=%s" % ("true" if options["render_js"] else "false")
    if "verify_ssl" in options:
        option_str += " --verify-ssl=%s" % ("true" if options["verify_ssl"] else "false")
    if "copy_images_from_canvas" in options:
        option_str += " --copy-images-from-canvas=%s" % ("true" if options["copy_images_from_canvas"] else "false")
    if "user_agent" in options and options["user_agent"]:
        option_str += " --user-agent='%s'" % options["user_agent"]
    if "referer" in options and options["referer"]:
        option_str += " --referer='%s'" % options["referer"]
    if "encoding" in options and options["encoding"]:
        option_str += " --encoding='%s'" % options["encoding"]
    if "header_list" in options:
        for header in options["header_list"]:
            option_str += " --header '%s'" % header

    #LOGGER.debug("title=%s, review_point=%d, review_point_threshold=%f", title, review_point, review_point_threshold)
    #if review_point and review_point_threshold and review_point > review_point_threshold:
        # 일반적으로 평점이 사용되지 않는 경우나
        # 평점이 기준치를 초과하는 경우에만 추출
        #warn("ignore an article due to the low score")
        #return 0

    return option_str


def remove_duplicates(a_list: List[Any]) -> List[Any]:
    seen: Set[Any] = OrderedSet()
    result: List[Any] = []
    for item in a_list:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def remove_file(file_path: str) -> None:
    if os.path.isfile(file_path):
        os.remove(file_path)


def find_process_group(parent_proc_name: str) -> List[int]:
    # find a parent process id by parent process name
    parent_children_map: Dict[int, List[int]] = {}
    ppid_list = []
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=["pid", "ppid", "name"])
        except psutil.NoSuchProcess:
            pass
        else:
            ppid = pinfo["ppid"]
            if ppid in parent_children_map:
                pid_list = parent_children_map[ppid]
                pid_list.append(pinfo["pid"])
            else:
                pid_list = [pinfo["pid"]]
            parent_children_map[ppid] = pid_list
            if pinfo["name"] == parent_proc_name:
                ppid_list.append(pinfo["pid"])

    # find a child process id by parent process name and child process name
    result_pid_list = []
    for ppid in ppid_list:
        result_pid_list.append(ppid)
        if ppid in parent_children_map:
            result_pid_list.extend(parent_children_map[ppid])

    return result_pid_list


def kill_process_group(proc_name: str) -> None:
    LOGGER.debug("kill_process_group(proc_name='%s')", proc_name)
    pid_list = find_process_group(proc_name)
    for pid in pid_list:
        p = psutil.Process(pid)
        p.terminate()


def get_current_time() -> datetime:
    return datetime.now().astimezone()


def get_time_str(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def get_current_time_str() -> str:
    return get_time_str(get_current_time())


def get_rss_date_str() -> str:
    dt = get_current_time()
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def get_short_date_str(dt=get_current_time()) -> str:
    return dt.strftime("%Y%m%d")


class HTMLExtractor:
    @staticmethod
    def get_first_token_from_path(path_str: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str], bool]:
        # print "get_first_token_from_path(path_str='%s')" % path_str
        if not path_str:
            return None, None, None, None, False
        is_anywhere: bool = False
        if path_str[0:2] == "//":
            is_anywhere = True
        tokens: List[str] = path_str.split("/")
        i: int = 0
        valid_token: str = ""
        for token in tokens:
            valid_token = token
            # print "tokens[%d]='%s'" % (i, token)
            i += 1
            if token not in ("", "html", "body"):
                # 첫번째 유효한 토큰만 꺼내옴
                break

        # 해당 토큰에 대해 정규식 매칭 시도
        pattern = re.compile(r'''
            (
              (?P<name>\w+)
              (?:\[
                (?P<idx>\d+)
              \])?
            |
              \*\[@id=\"(?P<id>\w+)\"\]
            )
        ''', re.VERBOSE)
        m = pattern.match(valid_token)
        if m:
            name = m.group("name")
            idx = int(m.group("idx")) if m.group("idx") else None
            id_str = m.group("id")
        else:
            return None, None, None, None, False

        # id, name, idx, path의 나머지 부분, is_anywhere을 반환
        return id_str, name, idx, "/".join(tokens[i:]), is_anywhere

    @staticmethod
    def get_node_with_path(node, path_str: Optional[str]) -> Optional[List[Any]]:
        if not node:
            return None
        # print "\n# get_node_with_path(node='%s', path_str='%s')" % (node.name, path_str)
        node_list = []

        (node_id, name, idx, next_path_str, is_anywhere) = HTMLExtractor.get_first_token_from_path(path_str)
        # print "node_id='%s', name='%s', idx=%d, next_path_str='%s', is_anywhere=%s" % (node_id, name, idx, next_path_str, is_anywhere)

        if node_id:
            # print "searching with id"
            # 특정 id로 노드를 찾아서 현재 노드에 대입
            nodes = node.find_all(attrs={"id": node_id})
            # print "nodes=", nodes
            if not nodes or nodes == []:
                # print("error, no id matched")
                return None
            if len(nodes) > 1:
                # print("error, two or more id matched")
                return None
            # print "found! node=%s" % nodes[0].name
            node_list.append(nodes[0])
            result_node_list = HTMLExtractor.get_node_with_path(nodes[0], next_path_str)
            if result_node_list:
                node_list = result_node_list
        else:
            # print "searching with name and index"
            if not name:
                return None

            # print "#children=%d" % len(node.contents)
            i = 1
            for child in node.contents:
                if hasattr(child, 'name'):
                    # print "i=%d child='%s', idx=%s" % (i, child.name, idx)
                    # 이름이 일치하거나 //로 시작한 경우
                    if child.name == name:
                        # print "name matched! i=%d child='%s', idx=%d" % (i, child.name, idx)
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
                                # print "\n*** extend! #result_node_list=", len(result_node_list)
                                if result_node_list:
                                    node_list.extend(result_node_list)
                        if idx and i == idx:
                            break
                        # 이름이 일치했을 때만 i를 증가시킴
                        i = i + 1
                    if is_anywhere:
                        # print "can be anywhere"
                        result_node_list = HTMLExtractor.get_node_with_path(child, name)
                        if result_node_list:
                            node_list.extend(result_node_list)
                        # print "node_list=", node_list
        return node_list


class IO:
    @staticmethod
    def read_stdin() -> str:
        line_list = IO.read_stdin_as_line_list()
        return "".join(line_list)

    @staticmethod
    def read_stdin_as_line_list() -> List[str]:
        input_stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="ignore")
        line_list = []
        for line in input_stream:
            line_list.append(line)
        return line_list

    @staticmethod
    def read_file(file=None) -> str:
        if not file or file == "":
            return IO.read_stdin()

        line_list = IO.read_file_as_line_list(file)
        return "".join(line_list)

    @staticmethod
    def read_file_as_line_list(file) -> List[str]:
        with codecs.open(file, 'rb', encoding="utf-8", errors="ignore") as f:
            line_list = f.readlines()
            f.close()
        return line_list


class Config:
    config: Dict[str, Dict[str, Any]] = {}

    def __init__(self) -> None:
        if "FEED_MAKER_CONF_FILE" in os.environ and os.environ["FEED_MAKER_CONF_FILE"]:
            config_file = os.environ["FEED_MAKER_CONF_FILE"]
        else:
            config_file = "conf.xml"
        with open(config_file, "r") as f:
            parsed_data = xmltodict.parse(f.read())
            if not parsed_data or "configuration" not in parsed_data:
                LOGGER.error("can't get configuration from config file")
                sys.exit(-1)
            else:
                self.config = parsed_data["configuration"]

    @staticmethod
    def _get_bool_config_value(config_node: Dict[str, Any], key: str, default: bool = False) -> bool:
        ret = default
        if key in config_node:
            if config_node[key] == "true":
                ret = True
            elif config_node[key] == "false":
                ret = False
        return ret

    @staticmethod
    def _get_str_config_value(config_node: Dict[str, Any], key: str, default: str = None) -> Optional[str]:
        if key in config_node:
            return config_node[key]
        return default

    @staticmethod
    def _get_int_config_value(config_node: Dict[str, Any], key: str, default: int = None) -> Optional[int]:
        if key in config_node:
            return int(config_node[key])
        return default

    @staticmethod
    def _get_float_config_value(config_node: Dict[str, Any], key: str, default: float = None) -> Optional[float]:
        if key in config_node:
            return float(config_node[key])
        return default

    @staticmethod
    def _traverse_config_node(config_node: Dict[str, Any], key: str) -> List[str]:
        result: List[str] = []
        if key in config_node:
            if isinstance(config_node[key], list):
                result.extend(config_node[key])
            else:
                result.append(config_node[key])
            return result

        for _, v in config_node.items():
            if isinstance(v, Dict):
                data = Config._traverse_config_node(v, key)
                result.extend(data)
        return result

    @staticmethod
    def _get_config_value_list(config_node: Dict[str, Any], key: str, default: List[Any] = None) -> Optional[List[Any]]:
        result = Config._traverse_config_node(config_node, key)
        if result:
            return result
        return default

    def get_collection_configs(self) -> Dict[str, Any]:
        LOGGER.debug("# get_collection_configs()")
        conf: Dict[str, Any] = {}
        if "collection" in self.config:
            collection_conf = self.config["collection"]

            render_js = Config._get_bool_config_value(collection_conf, "render_js")
            verify_ssl = Config._get_bool_config_value(collection_conf, "verify_ssl", True)
            ignore_old_list = Config._get_bool_config_value(collection_conf, "ignore_old_list")
            is_completed = Config._get_bool_config_value(collection_conf, "is_completed")

            item_capture_script = Config._get_str_config_value(collection_conf, "item_capture_script", "./capture_item_link_title.py")
            sort_field_pattern = Config._get_str_config_value(collection_conf, "sort_field_pattern")
            user_agent = Config._get_str_config_value(collection_conf, "user_agent")
            encoding = Config._get_str_config_value(collection_conf, "encoding", "utf-8")
            referer = Config._get_str_config_value(collection_conf, "referer")

            unit_size_per_day = Config._get_float_config_value(collection_conf, "unit_size_per_day")

            list_url_list = Config._get_config_value_list(collection_conf, "list_url", [])
            post_process_script_list = Config._get_config_value_list(collection_conf, "post_process_script", [])

            conf = {
                "render_js": render_js,
                "verify_ssl": verify_ssl,
                "ignore_old_list": ignore_old_list,
                "is_completed": is_completed,

                "item_capture_script": item_capture_script,
                "sort_field_pattern": sort_field_pattern,
                "user_agent": user_agent,
                "encoding": encoding,
                "referer": referer,

                "unit_size_per_day": unit_size_per_day,

                "list_url_list": list_url_list,
                "post_process_script_list": post_process_script_list,
            }
        return conf

    def get_extraction_configs(self) -> Dict[str, Any]:
        LOGGER.debug("# get_extraciton_configs()")
        conf: Dict[str, Any] = {}
        if "extraction" in self.config:
            extraction_conf = self.config["extraction"]

            render_js = Config._get_bool_config_value(extraction_conf, "render_js")
            verify_ssl = Config._get_bool_config_value(extraction_conf, "verify_ssl", True)
            bypass_element_extraction = Config._get_bool_config_value(extraction_conf, "bypass_element_extraction")
            force_sleep_between_articles = Config._get_bool_config_value(extraction_conf, "force_sleep_between_articles")
            copy_images_from_canvas = Config._get_bool_config_value(extraction_conf, "copy_images_from_canvas")

            user_agent = Config._get_str_config_value(extraction_conf, "user_agent")
            encoding = Config._get_str_config_value(extraction_conf, "encoding", "utf8")
            referer = Config._get_str_config_value(extraction_conf, "referer")

            review_point_threshold = Config._get_int_config_value(extraction_conf, "review_point_threshold")

            element_id_list = Config._get_config_value_list(extraction_conf, "element_id", [])
            element_class_list = Config._get_config_value_list(extraction_conf, "element_class", [])
            element_path_list = Config._get_config_value_list(extraction_conf, "element_path", [])
            post_process_script_list = Config._get_config_value_list(extraction_conf, "post_process_script", [])
            header_list = Config._get_config_value_list(extraction_conf, "header", [])

            conf = {
                "render_js": render_js,
                "verify_ssl": verify_ssl,
                "bypass_element_extraction": bypass_element_extraction,
                "force_sleep_between_articles": force_sleep_between_articles,
                "copy_images_from_canvas": copy_images_from_canvas,

                "user_agent": user_agent,
                "encoding": encoding,
                "referer": referer,

                "review_point_threshold": review_point_threshold,

                "element_id_list": element_id_list,
                "element_class_list": element_class_list,
                "element_path_list": element_path_list,
                "post_process_script_list": post_process_script_list,
                "header_list": header_list,
            }
        return conf

    def get_notification_configs(self) -> Dict[str, Any]:
        LOGGER.debug("# get_notification_configs()")
        conf: Dict[str, Any] = {}
        if "notification" in self.config:
            notification_conf = self.config["notification"]
            if "email" in notification_conf:
                email = notification_conf["email"]
                if email:
                    recipient = Config._get_str_config_value(email, "recipient")
                    subject = Config._get_str_config_value(email, "subject")
                    conf = {
                        "email_recipient": recipient,
                        "email_subject": subject,
                    }
        return conf

    def get_rss_configs(self) -> Dict[str, Any]:
        LOGGER.debug("# get_rss_configs()")
        conf: Dict[str, Any] = {}
        if "rss" in self.config:
            rss_conf = self.config["rss"]
            if rss_conf:
                rss_title = Config._get_str_config_value(rss_conf, "title")
                rss_description = Config._get_str_config_value(rss_conf, "description")
                rss_generator = Config._get_str_config_value(rss_conf, "generator")
                rss_copyright = Config._get_str_config_value(rss_conf, "copyright")
                rss_link = Config._get_str_config_value(rss_conf, "link")
                rss_language = Config._get_str_config_value(rss_conf, "language")
                rss_no_item_desc = Config._get_str_config_value(rss_conf, "no_item_desc")
                rss_url_prefix_for_guid = Config._get_str_config_value(rss_conf, "url_prefix_for_guid")
                conf = {
                    "rss_title": rss_title,
                    "rss_description": rss_description,
                    "rss_generator": rss_generator,
                    "rss_copyright": rss_copyright,
                    "rss_link": rss_link,
                    "rss_language": rss_language,
                    "rss_no_item_desc": rss_no_item_desc,
                    "rss_url_prefix_for_guid": rss_url_prefix_for_guid
                }
        return conf


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
            first_slash_index = url[host_index:].find('/', host_index)
            if first_slash_index >= 0:
                return url[host_index:(host_index + first_slash_index)]
        return ""

    # http://naver.com/api/items?page_no=3 => /api/items?page_no=3
    @staticmethod
    def get_url_path(url: str) -> str:
        scheme_separator = "://"
        host_index = url.find(scheme_separator) + len(scheme_separator)
        if host_index >= 0:
            first_slash_index = url[host_index:].find('/', host_index)
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
        if url2 == "#":
            return full_url
        if len(url2) > 0 and url2[0] == '/':
            url1 = URL.get_url_scheme(full_url) + "://" + URL.get_url_domain(full_url)
        elif len(url2) > 0 and url2[0:2] == "./":
            url1 = URL.get_url_prefix(full_url)
            url2 = url2[2:]
        else:
            url1 = URL.get_url_except_query(full_url)

        if len(url1) > 0 and len(url2) > 0:
            if url1[-1] == '/' and url2[0] == '/':
                return url1 + url2[1:]
            if url1[-1] != '/' and url2[0] != '/':
                return url1 + '/' + url2
        return url1 + url2

    @staticmethod
    def get_short_md5_name(content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()[:7]


class Cache:
    @staticmethod
    def get_cache_info_common(prefix: str, img_url: str, img_ext: str, postfix=None, index=None) -> str:
        LOGGER.debug("# get_cache_info_common(%s, %s, %s, %s, %d)", prefix, img_url, img_ext, postfix if postfix else "None", index if index else -1)
        postfix_str = ""
        if postfix and postfix != "":
            postfix_str = "_" + str(postfix)

        index_str = ""
        if index and index != "":
            index_str = "." + str(index)

        if re.search(r'https?://', img_url) and img_ext:
            result_str = prefix + "/" + URL.get_short_md5_name(img_url) + postfix_str + index_str + "." + img_ext
        else:
            result_str = prefix + "/" + URL.get_short_md5_name(img_url)
        return result_str

    @staticmethod
    def get_cache_url(url_prefix: str, img_url: str, img_ext: str, postfix=None, index=None) -> str:
        LOGGER.debug("# get_cache_url(%s, %s, %s, %s, %d)", url_prefix, img_url, img_ext, postfix if postfix else "None", index if index else -1)
        return Cache.get_cache_info_common(url_prefix, img_url, img_ext, postfix, index)

    @staticmethod
    def get_cache_file_name(path_prefix: str, img_url: str, img_ext: str, postfix=None, index=None) -> str:
        LOGGER.debug("# get_cache_file_name(%s, %s, %s, %s, %d)", path_prefix, img_url, img_ext, postfix if postfix else "None", index if index else -1)
        return Cache.get_cache_info_common(path_prefix, img_url, img_ext, postfix, index)
