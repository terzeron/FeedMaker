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

	
class ExtractionTest(unittest.TestCase):

	def test_daum_webtoon(self):
		os.environ['FEED_MAKER_CONF_FILE'] = "daum.webtoon.1.conf.xml"
		url = "http://cartoon.media.daum.net/m/webtoon/viewer/30086"
		htmlFileName = "daum.webtoon.1.html"
		extractedFileName = htmlFileName + ".extracted"
		processedFileName = htmlFileName + ".processed"
		downloadedFileName = htmlFileName + ".downloaded"

		# extract.py test
		expected = read_entire_file(extractedFileName)
		cmd = "cat %s | extract.py '%s'" % (htmlFileName, url)
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)

        # post process test
		expected = read_entire_file(processedFileName)
		cmd = "cat %s | %s/daum/post_process_daumwebtoon.pl '%s'" % (extractedFileName, os.environ['FEED_MAKER_HOME'], url)
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)

		
	def test_kakao_webtoon(self):
		os.environ['FEED_MAKER_CONF_FILE'] = "kakao.webtoon.1.conf.xml"
		url = "http://page.kakao.com/viewer?productId=47731651"
		htmlFileName = "kakao.webtoon.1.html"
		extractedFileName = htmlFileName + ".extracted"
		processedFileName = htmlFileName + ".processed"
		downloadedFileName = htmlFileName + ".downloaded"

		# extract.py test
		expected = read_entire_file(extractedFileName)
		cmd = "cat %s | extract.py '%s'" % (htmlFileName, url)
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)

        # post process test
		expected = read_entire_file(processedFileName)
		cmd = "cat %s | post_process_only_for_images.pl '%s'" % (extractedFileName, url)
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)
		

	def test_naver_webtoon(self):
		os.environ['FEED_MAKER_CONF_FILE'] = "naver.webtoon.1.conf.xml"
		url = "http://comic.naver.com/webtoon/detail.nhn?titleId=548870&no=118"
		htmlFileName = "naver.webtoon.1.html"
		extractedFileName = htmlFileName + ".extracted"
		processedFileName = htmlFileName + ".processed"
		downloadedFileName = htmlFileName + ".downloaded"

		# extract.py test
		expected = read_entire_file(extractedFileName)
		cmd = "cat %s | extract.py '%s'" % (htmlFileName, url)
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)

		# post process test
		expected = read_entire_file(processedFileName)
		cmd = "cat %s | %s/naver/post_process_naverwebtoon_mobile.pl '%s'" % (extractedFileName, os.environ['FEED_MAKER_HOME'], url)
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)

		# download test
		expected = read_entire_file(downloadedFileName)
		cmd = "cat %s | download_image.pl '%s'" % (processedFileName, url)
		result = subprocess.check_output(cmd, shell=True)
		self.assertEqual(expected, result)

		
if __name__ == "__main__":
	unittest.main()
