#!/usr/bin/env python
#-*- coding: utf-8 -*-


import os
import os.path
import sys
import subprocess
import re
from feedmakerutil import *


def main(rssFile):
	dir = os.environ["FEED_MAKER_WWW_FEEDS"]
	dataFileList = []
	doUpload = False
	maxTryCount = 3
	oldRssFile = rssFile + ".old"

	if os.path.isfile(oldRssFile):
		# 과거 파일이 존재하면 비교해보고 다른 경우에만 업로드
		cmd = "diff '%s' '%s' | egrep -v \"(^(<|>) <(pubDate|lastBuildDate))|(^---\$)|(^[0-9,]+[a-z][0-9,]+\$)\" | wc -c" % (rssFile, oldRssFile)
		#print cmd
		result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
		if result != False:
			#print result
			p = re.compile(r"^\s*(\d+)\s*$")
			match = p.match(result)
			if match and match.group(1) != "0":
				doUpload = True
	elif os.path.isfile(rssFile):
		# 과거 파일이 존재하지 않고 신규 파일만 존재하면 업로드
		doUpload = True
	else:
		err("Error: Upload failed! the same old RSS file")
		return False
		
	if doUpload == True:
		cmd = "cp %s %s" % (rssFile, dir)
		#print cmd
		for i in range(0, maxTryCount):
			result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
			if result != False:
				#print result
				print "Upload success!\n"
				return True
	else:
		warn("Upload failed! No change from the previous RSS file")
		return False


if __name__ == "__main__":
    main(sys.argv[1])
