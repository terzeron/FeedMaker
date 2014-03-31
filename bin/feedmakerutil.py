#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
from bs4 import BeautifulSoup, Comment


def get_first_token_from_path(path_str):
	#print "get_first_token_from_path(path_str='%s')" % (path_str)
	is_anywhere = False
	if path_str[0:2] == "//":
		is_anywhere = True
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

	# id, name, idx, path의 나머지 부분, is_anywhere을 반환
	return (id, name, idx, "/".join(tokens[i:]), is_anywhere)


def get_node_with_path(node, path_str):
	if node == None:
		return None
	#print "\n# get_node_with_path(node='%s', path_str='%s')" % (node.name, path_str)
	node_list = []

	(node_id, name, idx, next_path_str, is_anywhere) = get_first_token_from_path(path_str)
	#print "node_id='%s', name='%s', idx=%s, next_path_str='%s', is_anywhere=%s" % (node_id, name, idx, next_path_str, is_anywhere)

	if node_id != None:
		#print "searching with id"
		# 특정 id로 노드를 찾아서 현재 노드에 대입
		nodes = node.find_all(attrs={"id":node_id})
		#print "nodes=", nodes
		if nodes == None or nodes == []:
			print "error, no id matched"
			sys.exit(-1)
		if len(nodes) > 1:
			print "error, two or more id matched"
			sys.exit(-1)
		#print "found! node=%s" % (nodes[0].name)
		node_list.append(nodes[0])
		result_node_list = get_node_with_path(nodes[0], next_path_str)
		if result_node_list != None:
			node_list = result_node_list
	else:
		#print "searching with name and index"
		node_id = ""
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
				if is_anywhere == True:
					#print "can be anywhere"
					result_node_list = get_node_with_path(child, name)
					if result_node_list != None:
						node_list.extend(result_node_list)
					#print "node_list=", node_list
	return node_list


def read_stdin():
	html = ""
	for line in sys.stdin:
		html += line
	return html


def read_file(file):
    if file != "":
        fp = open(file, "r")
    else:
        fp = sys.stdin
    html = ""
    for line in fp:
        html += line
    fp.close()
    return html


def read_config(config_file):
	import xml.dom.minidom
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
	protocol_len = len(protocol)
	if url[:protocol_len] == protocol:
		# http:// 뒷쪽부터 /의 마지막 위치를 찾아냄
		index = url.rfind('/', protocol_len)
		return url[:index + 1]
	return ""

def get_url_domain(url):
	protocol = "http://"
	protocol_len = len(protocol)
	if url[:protocol_len] == protocol:
		index = url.find('/', protocol_len)
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


