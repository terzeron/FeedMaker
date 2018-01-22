#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import subprocess
from bs4 import BeautifulSoup, Comment


isDebugMode = False


def debug_print(a):
    if isDebugMode:
        print(a)


def make_path(path):
    try:
        os.makedirs(path)
    except _fileExistsError:
        # ignore
        None


def exec_cmd(cmd):
    try:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (result, error) = p.communicate()
        if error:
            if not error.startswith(b"_RegisterApplication(), FAILED TO establish the default connection to the WindowServer"):
                return False
    except subprocess.CalledProcessError:
        return False
    except subprocess.SubprocessError:
        return False
    return result.decode(encoding="utf-8")


def get_first_token_from_path(path_str):
    #print "get_first_token_from_path(path_str='%s')" % (path_str)
    isAnywhere = False
    if path_str[0:2] == "//":
        isAnywhere = True
    tokens = path_str.split("/")
    i = 0
    for token in tokens:
        #print "tokens[%d]='%s'" % (i, token)
        i = i + 1
        if token in ("", "html", "body"):
            continue
        else:
            # 첫번째 유효한 토큰만 꺼내옴
            break

    # 해당 토큰에 대해 정규식 매칭 시도
    pattern = re.compile(r"((?P<name>\w+)(?:\[(?P<idx>\d+)\])?|\*\[@id=\"(?P<id>\w+)\"\])")
    m = pattern.match(token)
    if m != None:
        id = m.group("id")
        name = m.group("name")
        idx = m.group("idx")
    else:
        return (None, None, None, None, False)

    # id, name, idx, path의 나머지 부분, isAnywhere을 반환
    return (id, name, idx, "/".join(tokens[i:]), isAnywhere)


def get_node_with_path(node, path_str):
    if node == None:
        return None
    #print "\n# get_node_with_path(node='%s', path_str='%s')" % (node.name, path_str)
    node_list = []

    (nodeId, name, idx, next_path_str, isAnywhere) = get_first_token_from_path(path_str)
    #print "nodeId='%s', name='%s', idx=%s, next_path_str='%s', isAnywhere=%s" % (nodeId, name, idx, next_path_str, isAnywhere)

    if nodeId != None:
        #print "searching with id"
        # 특정 id로 노드를 찾아서 현재 노드에 대입
        nodes = node.find_all(attrs={"id":nodeId})
        #print "nodes=", nodes
        if nodes == None or nodes == []:
            print("error, no id matched")
            sys.exit(-1)
        if len(nodes) > 1:
            print("error, two or more id matched")
            sys.exit(-1)
        #print "found! node=%s" % (nodes[0].name)
        node_list.append(nodes[0])
        result_node_list = get_node_with_path(nodes[0], next_path_str)
        if result_node_list != None:
            node_list = result_node_list
    else:
        #print "searching with name and index"
        nodeId = ""
        if name == None:
            return None
        if idx != None:
            idx = int(idx)

        #print "#children=%d" % (len(node.contents))
        i = 1
        for child in node.contents:
            if hasattr(child, 'name'):
                #print "i=%d child='%s', idx=%s" % (i, child.name, idx)
                # 이름이 일치하거나 //로 시작한 경우
                if child.name == name:
                    #print "name matched! i=%d child='%s', idx=%s" % (i, child.name, idx)
                    if idx == None or i == idx:
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
                            if result_node_list != None:
                                node_list.extend(result_node_list)
                    if idx != None and i == idx:
                        break
                    # 이름이 일치했을 때만 i를 증가시킴
                    i = i + 1
                if isAnywhere == True:
                    #print "can be anywhere"
                    result_node_list = get_node_with_path(child, name)
                    if result_node_list != None:
                        node_list.extend(result_node_list)
                    #print "node_list=", node_list
    return node_list


def read_stdin():
    line_list = read_stdin_as_line_list()
    return "".join(line_list)


def read_stdin_as_line_list():
    import io
    input_stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="ignore")
    line_list = []
    for line in input_stream:
        line_list.append(line)
    return line_list


def read_file(file = None):
    if file == None or file == "":
        return read_stdin()
           
    line_list = read_fileAsLine_list(file)
    return "".join(line_list)


def read_fileAsLine_list(file):
    import codecs

    with codecs.open(file, 'rb', encoding="utf-8", errors="ignore") as f:
        line_list = f.readlines()
        f.close()
        return line_list


def read_config():
    import xml.dom.minidom
    if 'FEED_MAKER_CONF_FILE' in os.environ:
        config_file = os.environ['FEED_MAKER_CONF_FILE']
    else:
        config_file = "conf.xml"
    return xml.dom.minidom.parse(config_file)


def get_all_config_nodes(node, key):
    return node.getElementsByTagName(key);


def get_config_node(node, key):
    nodes = get_all_config_nodes(node, key)
    if not nodes:
        return None
    return nodes[0]


def get_value_from_config(node):
    if node and node.childNodes:
        return node.childNodes[0].nodeValue
    return None


def get_config_value(node, key):
    return get_value_from_config(get_config_node(node, key))


def get_all_config_values(node, key):
    result = []
    for item in get_all_config_nodes(node, key):
        item_value = get_value_from_config(item)
        if item_value != None:
            result.append(item_value)
    return result


def get_url_prefix(url):
    protocol = "http://"
    protocolLen = len(protocol)
    if url[:protocolLen] == protocol:
        # http:// 뒷쪽부터 /의 마지막 위치를 찾아냄
        index = url.rfind('/', protocolLen)
        return url[:index + 1]
    return ""


def get_url_domain(url):
    protocol = "http://"
    protocolLen = len(protocol)
    if url[:protocolLen] == protocol:
        index = url.find('/', protocolLen)
        return url[:index + 1]
    return ""


def concatenate_url(full_url, url2):
    if len(url2) > 0 and url2[0] == '/':
        url1 = get_url_domain(full_url)
    else:
        url1 = get_url_prefix(full_url)
    if len(url1) > 0 and len(url2) > 0:
        if url1[-1] == '/' and url2[0] == '/':
            return url1 + url2[1:]
    return url1 + url2


def get_short_md5_name(str):
    import hashlib
    return hashlib.md5(str.encode()).hexdigest()[:7]


def err(msg):
    sys.stderr.write("Error: %s\n" % msg)


def die(msg):
    sys.stderr.write("Error: %s\n" % msg)
    sys.exit(-1)
    

def warn(msg):
    sys.stderr.write("Warning: %s\n" % msg)


def remove_file(file_path):
    if os.path.isfile(file_path):
        os.remove(file_path)



def get_cache_info_common(prefix, img_url, img_ext, postfix=None, index=None):
    postfix_str = ""
    if postfix and postfix != "":
        postfix_str = "_" + str(postfix)

    index_str = ""
    if index and index != "":
        index_str = "." + str(index)

    result_str = ""
    if re.search(r'https?://', img_url) and img_ext:
        result_str = prefix + "/" + get_short_md5_name(img_url) + postfix_str + index_str + "." + img_ext
    else:
        result_str = prefix + "/" + img_url
    debug_print("result_str=" + result_str)
    return result_str


def get_cache_url(url_prefix, img_url, img_ext, postfix=None, index=None):
    debug_print("# get_cache_url(%s, %s, %s, %s, %d)" % (url_prefix, img_url, img_ext, postfix, index if index else 0))
    return get_cache_info_common(url_prefix, img_url, img_ext,  postfix)


def get_cache_file_name(path_prefix, img_url, img_ext, postfix=None, index=None):
    debug_print("# get_cache_file_name(%s, %s, %s, %s, %d)" % (path_prefix, img_url, img_ext, postfix, index if index else 0))
    return get_cache_info_common(path_prefix, img_url, img_ext, postfix)
