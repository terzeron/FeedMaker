#!/usr/bin/env python
# -*- coding: utf-8 -*-

from BeautifulSoup import BeautifulSoup, Comment
import re
import sys
#import pprint
#import codecs;

def extract_files(files):
	for f in files:
		if extract_content(f) < 0:
			return -1

def read_file(file):
	fp = open(file)
	html = ""
	for line in fp:
		html += line
	fp.close()
	return html

def extract_content(file):
	html = read_file(file)
	soup = BeautifulSoup(html, fromEncoding="utf-8")
	text = soup.find(attrs={"id": "navercast_div"})
	if text == None:
		#sys.stderr.write("can't identify the DOM hierarchy of '%s'\n" % file)
		sys.exit(-1);
	print text

def traverse_element(element):
	prev_href = None
	for a in element.findAll('a'): 
		img = a.find('img')
		if prev_href != a['href']:
			print "%s\t%s" % (a['href'].encode("utf-8"), img['alt'].encode("utf-8")),
		else:
			print "- %s" % img['alt'].encode("utf-8")

		prev_href = a['href']
 
if __name__ == "__main__":
	extract_files(sys.argv[1:])
