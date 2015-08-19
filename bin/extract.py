#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup, Comment
import re
import subprocess
import os
import sys
import urllib
import copy
import signal
import cgi
from feedmakerutil import read_config, get_config_node, get_config_value, get_all_config_values, concatenate_url, get_url_prefix, read_file, get_node_with_path


# recursion으로 구현된 traverse_element()의 여러 레벨에서 조회하는 변수
footnote_num = 0
	
def print_header():
	print "<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'/>"
	print '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=2.0, minimum-scal#e=0.5, user-scalable=yes" />'
	print "<style>img { max-width: 100%; margin-top: 0px; margin-bottom: 0px; }</style>"


def print_trailer():
	print "<p/>"


def extract_content(args):
	item_url = args[0]
	file = ""
	if len(args) > 1:
		file = args[1]

	# configuration
	config = read_config()
	if config == None:
		return -1
	rss = get_config_node(config, "rss")
	if rss == None:
		print >> sys.stderr, "can't find 'rss' element from configuration"
	description = get_config_value(rss, "description")
	if description == None:
		print >> sys.stderr, "can't find 'rss' element from configuration"
	feed_url = get_config_value(rss, "feed_url")
	if feed_url == None:
		print >> sys.stderr, "can't find 'rss' element from configuration"
	extraction = get_config_node(config, "extraction")

	# read html contents
	html = read_file(file)

	if extraction != None:
		element_list = get_config_node(extraction, "element_list")
		if element_list == None:
			print >> sys.stderr, "can't find 'element_list' element from configuration"
		class_list = get_all_config_values(element_list, "element_class")
		id_list = get_all_config_values(element_list, "element_id")
		path_list = get_all_config_values(element_list, "element_path")
		encoding = get_config_value(element_list, "encoding")
		if encoding == None or encoding == "":
			encoding = "utf8"
		#print "# element_id:", id_list
		#print "# element_class:", class_list
		#print "# element_path:", path_list
		#print "# encoding:", encoding
	else:
		print html
		return True

	# sanitize
	html = re.sub(r'alt="(.*)<br>(.*)"', r'alt="\1 \2"', html);
	html = re.sub(r'<br>', r'<br/>', html);
	html = re.sub(r'<\?xml[^>]+>', r'', html)
	html = re.sub(r'/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/', r'', html)

	# header
	#print_header()

	# main article sections
	ret = 0
	for parser in [ "html5lib", "lxml" ]:
		soup = BeautifulSoup(html, parser, from_encoding='utf-8')
		for a_class in class_list:
			divs = soup.find_all(attrs={"class": a_class})
			if divs:
				for div in divs:
					ret = traverse_element(div, item_url, encoding)
		for an_id in id_list:
			divs = soup.find_all(attrs={"id": an_id})
			if divs:
				for div in divs:
					ret = traverse_element(div, item_url, encoding)
		for an_path in path_list:
			divs = get_node_with_path(soup.body, an_path)
			if divs:
				for div in divs:
					ret = traverse_element(div, item_url, encoding)
		if ret > 0:
			break
				
	if (class_list == None or class_list == []) and (id_list == None or id_list == []) and (path_list == None or path_list == []):
		ret = traverse_element(soup.body, item_url, encoding)

	# trailer
	#print_trailer()

	return True


def check_element_class(element, element_name, class_name):
	if element.name == element_name and element.has_attr("class") and class_name in element["class"]:
		return True
	return False


def traverse_element(element, url, encoding):
	global footnote_num
	ret = -1
	
	#print "# traverse_element()"
	if isinstance(element, Comment):
		return ret
	elif not hasattr(element, 'name') or element.name == None: 
		# text or self-close element (<br/>)
		sys.stdout.write("%s" % cgi.escape(str(element)))
		ret = 1
		return ret
	else: 
		# element
		#print "#%s#" % element.name

		# 원칙
		# 모든 element는 그 안에 다른 element나 text를 포함한다.
		# 그러므로 open tag를 써주고 그 다음에 recursive call로 처리하고
		# close tag를 써주면 된다.
		#
		# 예외 처리
		# 이미지는 src attribute를 써줘야 함, 뒤에 <br/>을 덧붙여야 함
		# naver.net을 포함하고 /17.jpg로 끝나는 이미지 경로는 제거해야 함
		# 테이블 관련 태그는 모두 무시?
		# 자바스크립트?
		# flash?

		open_close_tag = False
		if element.name == "p":
			print "<p>\n";
			for e in element.contents:
				ret = traverse_element(e, url, encoding)
			# 하위 노드를 처리하고 return하지 않으면, 텍스트를 직접 
			# 감싸고 있는 <p>의 경우, 중복된 내용이 노출될 수 있음
			print "</p>\n";
			ret = 1
			return ret
		elif element.name == "img":
			if element.has_attr("data-lazy-src"):
				data_lazy_src = element["data-lazy-src"]
				if data_lazy_src[:7] != "http://":
					data_lazy_src = concatenate_url(url, data_lazy_src)
				src = data_lazy_src
			elif element.has_attr("lazysrc"):
				lazy_src = element["lazysrc"]
				if lazy_src[:7] != "http://":
					lazy_src = concatenate_url(url, lazy_src)
				src = lazy_src
			elif element.has_attr("data-src"):
				data_src = element["data-src"]
				if data_src[:7] != "http://":
					data_src = concatenate_url(url, data_src)
				src = data_src
			elif element.has_attr("data-original"):
				data_src = element["data-original"]
				if data_src[:7] != "http://":
					data_src = concatenate_url(url, data_src)
				src = data_src
			elif element.has_attr("src"):
				src = element["src"]
				if src[:7] != "http://":
					src = concatenate_url(url, src)
				if "ncc.phinf.naver.net" in src and ("/17.jpg" in src or "/8_17px.jpg" in src or "/7px.jpg" in src or "/20px.jpg" in src):
					# 외부에서 접근 불가능한 이미지 제거
					return ret
			sys.stdout.write("<img src='%s'" % src)
			if element.has_attr("width"):
				sys.stdout.write(" width='%s'" % element["width"])
			sys.stdout.write("/>\n")
			ret = 1
		elif element.name == "a":
			if element.has_attr("onclick"):
				# 주석레이어 제거
				m = re.search(r"(open|close)FootnoteLayer\('(\d+)'", element["onclick"])
				if m:
					open_or_close = m.group(1)
					if open_or_close == "open":
						footnote_num = m.group(2)
					return ret
			if element.has_attr("href"):
				# complementing href value
				href = element["href"]
				if href != "" and href[:7] != "http://":
					href = concatenate_url(url, href)
				# A tag는 href와 target attribute를 출력해줘야 함
				sys.stdout.write("<a href='%s'" % href)
				if element.has_attr("target"):
					sys.stdout.write(" target='%s'>\n" % element["target"])
				else:
					sys.stdout.write(">")
				ret = 1
				open_close_tag = True
		elif element.name in ("iframe", "embed"):
			if element.has_attr("src"):
				src = element["src"]
				if "video_player.nhn" in src or ".swf" in src or "getCommonPlayer.nhn" in src:
					# flash 파일은 [IFRAME with Flash]라고 표시
					print "[Flash Player]<br/>"
					print "<%s src='%s'></%s><br/>" % (element.name, src, element.name)
					print "<a href='%s'>%s</a><br/>" % (src, src)
				else:
					sys.stdout.write("%s\n" % str(element))
				ret = 1
		elif element.name in ("param", "object"):
			if element.has_attr("name") and element["name"] == "Src" and element.has_attr("value") and ".swf" in element["value"]:
				src = element["value"]
				print "[Flash Player]<br/>"
				print "<video src='%s'></video><br/>" % (src)
				print "<a href='%s'>%s</a><br/>" % (src, src)
			ret = 1
		elif element.name == "map":
			# image map
			# extract only link information from area element
			for child in element.contents:
				if hasattr(child, "name") and child.name == "area":
					link_href = "#"
					link_title = "empty link title"
					if child.has_attr("href"):
						link_href = child["href"]
					if child.has_attr("alt"):
						link_title = child["alt"]
					print "<br/><br/><strong><a href='%s'>%s</a></strong><br/><br/>\n" % (link_href, link_title)
					ret = 1
				elif element.name in ("o:p", "st1:time"):
					# skip unknown element 
					return ret
		elif element.name in ("script"):
			# skip this element
			return ret
		elif element.name in ("v:shapetype", "qksdmssnfl", "qksdmssnfl<span"):
			# skip malformed element
			return ret
		else:
			if check_element_class(element, "div", "paginate_v1"):
				# <div class="paginate">...
				# ajax로 받아오는 페이지들을 미리 요청
				result = re.search(r"change_page\('([^' ]+)/literature_module/(\d+)/literature_(\d+)_(\d+)\.html'", str(element));
				if result:
					url_prefix = result.group(1)
					leaf_id = result.group(2)
					article_num = result.group(3)
					page_num = result.group(4)
					cmd = "collect_ajax_pages.pl " + leaf_id + " " + article_num + " " + page_num + " " + encoding
					output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
					print output
					ret = 1
				return ret
			elif check_element_class(element, "div", "view_option option_top"):
				# "오늘의 문학"에서 폰트크기와 책갈피 이미지 영역 제거
				return ret
			elif check_element_class(element, "span", "page_prev") or check_element_class(element, "span", "page_next"):
				# <span class="page_prev">... or <span class="page_next">...
				# 이전/다음 페이지 화살표 링크 영역 제거
				return ret
			elif check_element_class(element, "dl", "designlist"):
				# <dl class="designlist">...
				# skip this element and sub-elements
				return ret
			elif check_element_class(element, "div", "na_ly_cmt"):
				# <a onclick="openFootnoteLayer('번호'...)의 번호와 비교
				if hasattr(element, "id"):
					if element["id"] != "footnoteLayer" + str(footnote_num):
						return ret
					#else:
						#print str(element)
			elif element.name in ("style", "table", "tbody", "tr", "td", "th", "font", "st1:personname", "script"):
				# skip this element 
				None
			else:				
				sys.stdout.write("<%s>\n" % element.name)
				open_close_tag = True
				ret = 1

		if hasattr(element, 'contents'):
			for e in element.contents:
				if e == "\n":
					continue
				else:
					ret = traverse_element(e, url, encoding)
		elif isinstance(element, Comment):
			return ret
		else:
			sys.stdout.write(element)
			ret = 1
			return ret

		if open_close_tag == True:
			sys.stdout.write("</%s>\n" % element.name)
			ret = 1

	return ret


def print_usage(program_name):
	print "Usage:\t%s\t<file or url> <html file>\n" % program_name
	print ""


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print_usage(sys.argv[0])
		sys.exit(-1)
	signal.signal(signal.SIGPIPE, signal.SIG_DFL)
	extract_content(sys.argv[1:])
