#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import subprocess
from logger import Logger
from typing import List, Any, Dict, Tuple, Optional, Set


logger: Logger = Logger("feedmakerutil.py")
header_str: str = '''<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no"/>
<style>img { max-width: 100%; margin-top: 0px; margin-bottom: 0px; }</style>

'''


def make_path(path: str) -> None:
    try:
        os.makedirs(path)
    except FileExistsError:
        # ignore
        None


def exec_cmd(cmd: str, input=None) -> Tuple[Optional[str], str]:
    try:
        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if input:
            (result, error) = p.communicate(input.encode("utf-8"))
        else:
            (result, error) = p.communicate()
        if error:
            if not error.startswith(b"_RegisterApplication(), FAILED TO establish the default connection to the WindowServer"):
                return (None, error.decode("utf-8"))
    except subprocess.CalledProcessError:
        return (None, "Error with non-zero exit status in execution of subprocess")
    except subprocess.SubprocessError:
        return (None, "Error in execution of subprocess")
    return (result.decode(encoding="utf-8"), "")



def get_first_token_from_path(path_str: str) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str], bool]:
    #print "get_first_token_from_path(path_str='%s')" % (path_str)
    is_anywhere: bool = False
    if path_str[0:2] == "//":
        is_anywhere = True
    tokens: List[str] = path_str.split("/")
    i: int = 0
    for token in tokens:
        #print "tokens[%d]='%s'" % (i, token)
        i += 1
        if token in ("", "html", "body"):
            continue
        else:
            # 첫번째 유효한 토큰만 꺼내옴
            break

    # 해당 토큰에 대해 정규식 매칭 시도
    pattern = re.compile(r"""
    (
      (?P<name>\w+)
      (?:\[
        (?P<idx>\d+)
      \])?
    |
      \*\[@id=\"(?P<id>\w+)\"\]
    )
    """, re.VERBOSE)
    m = pattern.match(token)
    if m:
        name = m.group("name")
        idx = int(m.group("idx")) if m.group("idx") else None
        id = m.group("id")
    else:
        return (None, None, None, None, False)

    # id, name, idx, path의 나머지 부분, is_anywhere을 반환
    return (id, name, idx, "/".join(tokens[i:]), is_anywhere)


def get_node_with_path(node, path_str: str) -> List[Any]:
    if not node:
        return None
    #print "\n# get_node_with_path(node='%s', path_str='%s')" % (node.name, path_str)
    node_list = []

    (node_id, name, idx, next_path_str, is_anywhere) = get_first_token_from_path(path_str)
    #print "node_id='%s', name='%s', idx=%d, next_path_str='%s', is_anywhere=%s" % (node_id, name, idx, next_path_str, is_anywhere)

    if node_id:
        #print "searching with id"
        # 특정 id로 노드를 찾아서 현재 노드에 대입
        nodes = node.find_all(attrs={"id": node_id})
        #print "nodes=", nodes
        if not nodes or nodes == []:
            #print("error, no id matched")
            return None
        if len(nodes) > 1:
            #print("error, two or more id matched")
            return None
        #print "found! node=%s" % (nodes[0].name)
        node_list.append(nodes[0])
        result_node_list = get_node_with_path(nodes[0], next_path_str)
        if result_node_list:
            node_list = result_node_list
    else:
        #print "searching with name and index"
        node_id = ""
        if not name:
            return None

        #print "#children=%d" % (len(node.contents))
        i = 1
        for child in node.contents:
            if hasattr(child, 'name'):
                #print "i=%d child='%s', idx=%s" % (i, child.name, idx)
                # 이름이 일치하거나 //로 시작한 경우
                if child.name == name:
                    #print "name matched! i=%d child='%s', idx=%d" % (i, child.name, idx)
                    if not idx or i == idx:
                        # 인덱스가 지정되지 않았거나, 지정되었고 인덱스가 일치할 때
                        if next_path_str == "":
                            # 단말 노드이면 현재 일치한 노드를 반환
                            #print "*** append! child='%s'" % (child.name)
                            node_list.append(child)
                        else:
                            # 중간 노드이면 recursion
                            #print "*** recursion ***"
                            result_node_list = get_node_with_path(child, next_path_str)
                            #print "\n*** extend! #result_node_list=", len(result_node_list)
                            if result_node_list:
                                node_list.extend(result_node_list)
                    if idx and i == idx:
                        break
                    # 이름이 일치했을 때만 i를 증가시킴
                    i = i + 1
                if is_anywhere:
                    #print "can be anywhere"
                    result_node_list = get_node_with_path(child, name)
                    if result_node_list:
                        node_list.extend(result_node_list)
                    #print "node_list=", node_list
    return node_list


class IO:
    @staticmethod
    def read_stdin() -> str:
        line_list = IO.read_stdin_as_line_list()
        return "".join(line_list)


    @staticmethod
    def read_stdin_as_line_list() -> List[str]:
        import io
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
        import codecs

        with codecs.open(file, 'rb', encoding="utf-8", errors="ignore") as f:
            line_list = f.readlines()
            f.close()
        return line_list


class Config:
    @staticmethod
    def read_config() -> Any:
        from xml.dom import minidom
        if "FEED_MAKER_CONF_FILE" in os.environ and os.environ["FEED_MAKER_CONF_FILE"]:
            config_file = os.environ["FEED_MAKER_CONF_FILE"]
        else:
            config_file = "conf.xml"
        return minidom.parse(config_file)


    @staticmethod
    def get_all_config_nodes(node, key: str) -> Any:
        return node.getElementsByTagName(key)


    @staticmethod
    def get_config_node(node, key: str) -> Any:
        nodes = Config.get_all_config_nodes(node, key)
        if not nodes:
            return None
        return nodes[0]


    @staticmethod
    def get_value_from_config(node) -> str:
        if node and node.childNodes:
            return node.childNodes[0].nodeValue
        return None


    @staticmethod
    def get_config_value(node, key: str) -> str:
        return Config.get_value_from_config(Config.get_config_node(node, key))


    @staticmethod
    def get_all_config_values(node, key: str) -> List[str]:
        result = []
        for item in Config.get_all_config_nodes(node, key):
            item_value = Config.get_value_from_config(item)
            if item_value:
                result.append(item_value)
        return result


    @staticmethod
    def get_config_values_as_list(list_item_name: str, single_item_name: str, parent_conf_node) -> List[str]:
        list: List[str] = []
        conf_node = Config.get_config_node(parent_conf_node, list_item_name)
        if conf_node:
            # 리스트 노드로부터 개별 항목을 리스트로 추출
            # <post_process_script_list>
            #     <post_process_script>...</post_process_script>
            #     <post_process_script>...</post_process_script>
            # </post_process_script_list>
            list = Config.get_all_config_values(conf_node, single_item_name)
        else:
            # 리스트 노드로 정의되어 있지 않으면 개별 항목을 리스트 형태로 변환
            # <post_process_script>...</post_process_script>
            item = Config.get_config_value(parent_conf_node, single_item_name)
            if item:
                list.append(item)
        return list


    @staticmethod
    def get_collection_configs(config: Any) -> Dict[str, Any]:
        logger.debug("# get_collection_configs()")
        conf = Config.get_config_node(config, "collection")
        if not conf:
            die("can't get collection element")

        item_capture_script = Config.get_config_value(conf, "item_capture_script")
        if not item_capture_script:
            item_capture_script = "./capture_item_link_title.py"
        # 파일 존재 여부, 실행 권한 체크
        item_capture_script_program = item_capture_script.split(" ")[0]
        if not item_capture_script_program or not os.path.isfile(item_capture_script_program) or not os.access(item_capture_script_program, os.X_OK):
            die("can't execute '%s'\n" % (item_capture_script_program))

        ignore_old_list: bool = bool("true" == Config.get_config_value(conf, "ignore_old_list"))
        is_completed: bool = bool("true" == Config.get_config_value(conf, "is_completed"))
        sort_field_pattern: str = Config.get_config_value(conf, "sort_field_pattern")
        unit_size_per_day: float = float(Config.get_config_value(conf, "unit_size_per_day")) if Config.get_config_value(conf, "unit_size_per_day") else None
        user_agent = Config.get_config_value(conf, "user_agent")
        encoding = Config.get_config_value(conf, "encoding")

        list_url_list = Config.get_config_values_as_list("list_url_list", "list_url", conf)
        post_process_script_list = Config.get_config_values_as_list("post_process_script_list", "post_process_script", conf)

        options = {
            "item_capture_script": item_capture_script,
            "list_url_list": list_url_list,
            "ignore_old_list": ignore_old_list,
            "is_completed": is_completed,
            "sort_field_pattern": sort_field_pattern,
            "unit_size_per_day": unit_size_per_day,
            "user_agent": user_agent,
            "encoding": encoding,
            "post_process_script_list": post_process_script_list,
        }

        return options


    def get_extraction_configs(config: Any) -> Dict[str, Any]:
        logger.debug("# get_extraciton_configs()")
        conf = Config.get_config_node(config, "extraction")
        if not conf:
            die("can't get extraction element")

        render_js: bool = bool("true" == Config.get_config_value(conf, "render_js"))
        uncompress_gzip: bool = bool("true" == Config.get_config_value(conf, "uncompress_gzip"))
        bypass_element_extraction: bool = bool("true" == Config.get_config_value(conf, "bypass_element_extraction"))
        force_sleep_between_articles = bool("true" == Config.get_config_value(conf, "force_sleep_between_articles"))

        review_point_threshold = Config.get_config_value(conf, "review_point_threshold")
        user_agent = Config.get_config_value(conf, "user_agent")
        encoding = Config.get_config_value(conf, "encoding")
        referer = Config.get_config_value(conf, "referer")

        header_list = Config.get_config_values_as_list("header_list", "header", conf)
        post_process_script_list = Config.get_config_values_as_list("post_process_script_list", "post_process_script", conf)

        options = {
            "render_js": render_js,
            "uncompress_gzip": uncompress_gzip,
            "force_sleep_between_articles": force_sleep_between_articles,
            "bypass_element_extraction": bypass_element_extraction,
            "review_point_threshold": review_point_threshold,
            "user_agent": user_agent,
            "encoding": encoding,
            "referer": referer,
            "header_list": header_list,
            "post_process_script_list": post_process_script_list,
        }

        return options


    def get_notification_configs(config: Any) -> Dict[str, Any]:
        logger.debug("# get_notification_configs()")
        options = None
        conf = Config.get_config_node(config, "notification")
        if conf:
            email = Config.get_config_node(conf, "email")
            if email:
                recipient = Config.get_config_value(email, "recipient")
                subject = Config.get_config_value(email, "subject")

                options = {
                    "email_recipient": recipient,
                    "email_subject": subject,
                }
        return options


    def get_rss_configs(config: Any) -> Dict[str, Any]:
        logger.debug("# get_rss_configs()")
        conf = Config.get_config_node(config, "rss")
        if not conf:
            die("can't get rss element")

        rss_title = Config.get_config_value(conf, "title")
        rss_description = Config.get_config_value(conf, "description")
        rss_generator = Config.get_config_value(conf, "generator")
        rss_copyright = Config.get_config_value(conf, "copyright")
        rss_link = Config.get_config_value(conf, "link")
        rss_language = Config.get_config_value(conf, "language")
        rss_no_item_desc = Config.get_config_value(conf, "no_item_desc")

        options = {
            "rss_title": rss_title,
            "rss_description": rss_description,
            "rss_generator": rss_generator,
            "rss_copyright": rss_copyright,
            "rss_link": rss_link,
            "rss_language": rss_language,
            "rss_no_item_desc": rss_no_item_desc
        }
        return options


class URL:
    @staticmethod
    def get_url_prefix(url: str) -> str:
        protocol = "http://"
        protocol_len = len(protocol)
        if url[:protocol_len] == protocol:
            # http:// 뒷쪽부터 /의 마지막 위치를 찾아냄
            index = url.rfind('/', protocol_len)
            return url[:index + 1]
        return ""


    @staticmethod
    def get_url_domain(url: str) -> str:
        protocol = "http://"
        protocol_len = len(protocol)
        if url[:protocol_len] == protocol:
            index = url.find('/', protocol_len)
            return url[:index + 1]
        return ""


    @staticmethod
    def concatenate_url(full_url: str, url2: str) -> str:
        if len(url2) > 0 and url2[0] == '/':
            url1 = URL.get_url_domain(full_url)
        else:
            url1 = URL.get_url_prefix(full_url)
        if len(url1) > 0 and len(url2) > 0:
            if url1[-1] == '/' and url2[0] == '/':
                return url1 + url2[1:]
        return url1 + url2


    @staticmethod
    def get_short_md5_name(str: str) -> str:
        import hashlib
        return hashlib.md5(str.encode()).hexdigest()[:7]


def err(msg: str) -> None:
    logger.err(msg)


def die(msg: str) -> None:
    logger.err(msg)
    sys.exit(-1)


def warn(msg: str) -> None:
    logger.warn(msg)


def remove_file(file_path: str) -> None:
    if os.path.isfile(file_path):
        os.remove(file_path)


class Cache:
    @staticmethod
    def get_cache_info_common(prefix: str, img_url: str, img_ext: str, postfix=None, index=None) -> str:
        logger.debug("# get_cache_info_common(%s, %s, %s, %s, %d)" % (prefix, img_url, img_ext, postfix if postfix else "None", index if index else -1))
        postfix_str = ""
        if postfix and postfix != "":
            postfix_str = "_" + str(postfix)

        index_str = ""
        if index and index != "":
            index_str = "." + str(index)

        result_str = ""
        if re.search(r'https?://', img_url) and img_ext:
            result_str = prefix + "/" + URL.get_short_md5_name(img_url) + postfix_str + index_str + "." + img_ext
            logger.debug("result_str=" + result_str)
        else:
            result_str = prefix + "/" + img_url
            logger.debug("result_str=" + result_str)
        return result_str


    @staticmethod
    def get_cache_url(url_prefix: str, img_url: str, img_ext: str, postfix=None, index=None) -> str:
        logger.debug("# get_cache_url(%s, %s, %s, %s, %d)" % (url_prefix, img_url, img_ext, postfix if postfix else "None", index if index else -1))
        return Cache.get_cache_info_common(url_prefix, img_url, img_ext, postfix, index)


    @staticmethod
    def get_cache_file_name(path_prefix: str, img_url: str, img_ext: str, postfix=None, index=None):
        logger.debug("# get_cache_file_name(%s, %s, %s, %s, %d)" % (path_prefix, img_url, img_ext, postfix if postfix else "None", index if index else -1))
        return Cache.get_cache_info_common(path_prefix, img_url, img_ext, postfix, index)


def determine_crawler_options(options: Dict[str, Any]) -> str:
    logger.debug("# determine_crawler_options()")

    option_str = ""
    if "render_js" in options and options["render_js"]:
        option_str += " --render-js"
    if "uncompress_gzip" in options and options["uncompress_gzip"]:
        option_str += " --uncompress-gzip"
    if "user_agent" in options and options["user_agent"]:
        option_str += " --ua '%s'" % (options["user_agent"])
    if "referer" in options and options["referer"]:
        option_str += " --referer '%s'" % (options["referer"])
    if "encoding" in options and options["encoding"]:
        option_str += " --encoding '%s'" % (options["encoding"])
    if "header_list" in options and options["header_list"]:
        for header in options["header_list"]:
            option_str += " --header '%s'" % (header)

    '''
    logger.debug("title=%s, review_point=%d, review_point_threshold=%f" % (title, review_point, review_point_threshold))
    if review_point and review_point_threshold and review_point > review_point_threshold:
        # 일반적으로 평점이 사용되지 않는 경우나
        # 평점이 기준치를 초과하는 경우에만 추출
        warn("ignore an article due to the low score")
        return 0
    '''

    return option_str


def remove_duplicates(list: List[Any]) -> List[Any]:
    seen: Set[Any] = set()
    result: List[Any] = []
    for item in list:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
