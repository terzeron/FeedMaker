#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest
from feedmakerutil import get_md5_name
import subprocess


def read_entire_file(fileName):
	with open(fileName) as f:
		result = f.read()
		f.close()
		return result

	
class CollectionTest(unittest.TestCase):

	def test_daum_webtoon(self):
		os.environ['FEED_MAKER_CONF_FILE'] = "daum.webtoon.2.conf.xml"
		url = "http://cartoon.media.daum.net/data/mobile/webtoon/list_episode_by_nickname?nickname=mujang"
		fileNamePrefix = "daum.webtoon.2.list"
		htmlFileName = fileNamePrefix + ".html"
		extractedFileName = fileNamePrefix + ".extracted"
		listFileName = fileNamePrefix + ".txt"

		expected = read_entire_file(extractedFileName)
		cmd = "cat %s | extract_element.py collection" % (htmlFileName)
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)

		expected = read_entire_file(listFileName)
		cmd = "cat %s | %s/daum/capture_item_daumwebtoon_mobile.pl" % (extractedFileName, os.environ['FEED_MAKER_HOME'])
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)


	def test_kakao_webtoon(self):
		os.environ['FEED_MAKER_CONF_FILE'] = "kakao.webtoon.2.conf.xml"
		url = "http://page.kakao.com/viewer?productId=47196263"
		fileNamePrefix = "kakao.webtoon.2.list"
		htmlFileName = fileNamePrefix + ".html"
		extractedFileName = fileNamePrefix + ".extracted"
		listFileName = fileNamePrefix + ".txt"

		expected = read_entire_file(extractedFileName)
		cmd = "cat %s | extract_element.py collection" % (htmlFileName)
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)

		expected = read_entire_file(listFileName)
		cmd = "cat %s | %s/kakao/capture_item_kakaowebtoon.pl" % (extractedFileName, os.environ['FEED_MAKER_HOME'])
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)


	def test_naver_webtoon(self):
		os.environ['FEED_MAKER_CONF_FILE'] = "naver.webtoon.2.conf.xml"
		url = "http://page.naver.com/viewer?productId=47196263"
		fileNamePrefix = "naver.webtoon.2.list"
		htmlFileName = fileNamePrefix + ".html"
		extractedFileName = fileNamePrefix + ".extracted"
		listFileName = fileNamePrefix + ".txt"

		expected = read_entire_file(extractedFileName)
		cmd = "cat %s | extract_element.py collection" % (htmlFileName)
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)

		expected = read_entire_file(listFileName)
		cmd = "cat %s | %s/naver/capture_item_naverwebtoon.pl" % (extractedFileName, os.environ['FEED_MAKER_HOME'])
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)

		
if __name__ == "__main__":
	unittest.main()
