#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import os
import sys
import unittest
import subprocess
import feedmakerutil


class PostProcessOnlyForImagesScriptTest(unittest.TestCase):
	originalFile = "nate.webtoon.1.html.extracted"
	processedFile = "nate.webtoon.1.html.processed"


	def test_process(self):
		cmd = "cat %s | %s" % (self.originalFile, os.environ['FEED_MAKER_HOME'] + '/bin/post_process_only_for_images.py')
		#print(cmd)
		result = feedmakerutil.execCmd(cmd)
		expected = feedmakerutil.readFile(self.processedFile)
		self.assertEqual(expected, result)
		
		
if __name__ == "__main__":
	unittest.main()
