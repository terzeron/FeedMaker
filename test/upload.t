#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import os
import sys
import unittest
import subprocess
import feedmakerutil


class UploadScriptTest(unittest.TestCase):
	rssFileName = "sportsdonga.webtoon.1.result.xml"
	oldRssFileName = rssFileName + ".old"
	differentRssFileName = "sportsdonga.webtoon.2.result.xml"
	wwwDir = os.environ["HOME"] + "/public_html/xml"
	uploadedFilePath = wwwDir + "/" + rssFileName

		
	def setUp(self):
		feedmakerutil.removeFile(self.uploadedFilePath)
			
			
	def test_uploadFirst(self):
		cmd = "upload.py %s" % self.rssFileName
		result = feedmakerutil.execCmd(cmd)

		self.assertTrue(result and result != "")
		self.assertTrue("success" in result)
		self.assertTrue(os.path.isfile(self.uploadedFilePath))
		

	def test_uploadUnchanged(self):
		cmd = "cp %s %s" % (self.rssFileName, self.oldRssFileName)
		result = feedmakerutil.execCmd(cmd)
		#print(cmd)

		cmd = "upload.py %s 2>&1" % self.rssFileName
		result = feedmakerutil.execCmd(cmd)
		#print(cmd)
		#print(result)

		self.assertTrue(result)
		self.assertTrue("failed" in result)
		self.assertTrue("No change" in result)
		self.assertFalse(os.path.isfile(self.uploadedFilePath))

		
	def test_uploadChanged(self):
		cmd = "cp %s %s" % (self.differentRssFileName, self.oldRssFileName)
		result = feedmakerutil.execCmd(cmd)
		
		cmd = "upload.py %s" % self.rssFileName
		result = feedmakerutil.execCmd(cmd)
		
		self.assertTrue(result and result != "")
		self.assertTrue("success" in result)
		self.assertTrue(os.path.isfile(self.uploadedFilePath))
		
		
	def tearDown(self):
		feedmakerutil.removeFile(self.uploadedFilePath)
		feedmakerutil.removeFile(self.oldRssFileName)

		
if __name__ == "__main__":
	unittest.main()
