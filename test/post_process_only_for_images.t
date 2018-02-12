#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import os
import sys
import unittest
import subprocess
import feedmakerutil


class PostProcessOnlyForImagesScriptTest(unittest.TestCase):
    original_file = "nate.webtoon.1.html.extracted"
    processed_file = "nate.webtoon.1.html.processed"


    def test_process(self):
        cmd = "cat %s | %s" % (self.original_file, os.environ['FEED_MAKER_HOME'] + '/bin/post_process_only_for_images.py')
        #print(cmd)
        (result, error) = feedmakerutil.exec_cmd(cmd)
        expected = feedmakerutil.read_file(self.processed_file)
        self.assertEqual(expected, result)
        
        
if __name__ == "__main__":
    unittest.main()
