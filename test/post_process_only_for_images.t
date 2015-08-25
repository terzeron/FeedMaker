#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
import sys
import unittest
import subprocess


class PostProcessOnlyForImagesScriptTest(unittest.TestCase):
	originalFile = "nate.webtoon.1.html.extracted"
	processedFile = "nate.webtoon.1.html.processed"


	def readEntireFile(self, fileName):
		with open(fileName, 'r') as f:
			result = f.read()
			f.close()
			return result
		
	
	def setUp(self):
		None
			
			
	def test_process(self):
		cmd = "cat %s | %s" % (self.originalFile, os.environ['FEED_MAKER_HOME'] + '/bin/post_process_only_for_images.py')
		result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
		expected = self.readEntireFile(self.processedFile)
		self.assertEqual(expected, result)
		
		
	def tearDown(self):
		None

		
if __name__ == "__main__":
	unittest.main()
