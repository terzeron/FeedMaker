#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
import sys
import unittest
import subprocess


class UploadScriptTest(unittest.TestCase):
	rssFileName = "sportsdonga.webtoon.1.result.xml"
	oldRssFileName = rssFileName + ".old"
	differentRssFileName = "sportsdonga.webtoon.2.result.xml"
	wwwDir = os.environ["HOME"] + "/public_html/xml"
	uploadedFilePath = wwwDir + "/" + rssFileName

	def removeUploadedFile(self):
		if os.path.isfile(self.uploadedFilePath):
			os.remove(self.uploadedFilePath)

		
	def setUp(self):
		self.removeUploadedFile()
			
			
	def test_uploadFirst(self):
		cmd = "upload.py %s" % self.rssFileName
		result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]

		self.assertTrue(result != None and result != "")
		self.assertTrue(result.find("success") > 0)
		self.assertTrue(os.path.isfile(self.uploadedFilePath))
		

	def test_uploadUnchanged(self):
		cmd = "cp %s %s" % (self.rssFileName, self.oldRssFileName)
		result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]

		cmd = "upload.py %s" % self.rssFileName
		result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]

		self.assertTrue(result != None and result != "")
		self.assertTrue(result.find("failed") > 0 and result.find("No change") > 0)
		self.assertFalse(os.path.isfile(self.uploadedFilePath))

		
	def test_uploadChanged(self):
		cmd = "cp %s %s" % (self.differentRssFileName, self.oldRssFileName)
		result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]

		cmd = "upload.py %s" % self.rssFileName
		result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]

		self.assertTrue(result != None and result != "")
		self.assertTrue(result.find("success") > 0)
		self.assertTrue(os.path.isfile(self.uploadedFilePath))
		
		
	def tearDown(self):
		self.removeUploadedFile()
		if os.path.isfile(self.oldRssFileName):
			os.remove(self.oldRssFileName)

		
if __name__ == "__main__":
	unittest.main()
