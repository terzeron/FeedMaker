#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import os
import sys
import unittest
import subprocess
import feedmakerutil


class UploadScriptTest(unittest.TestCase):
    rss_file_name = "sportsdonga.webtoon.1.result.xml"
    old_rss_file_name = rss_file_name + ".old"
    different_rss_file_name = "sportsdonga.webtoon.2.result.xml"
    www_dir = os.environ["HOME"] + "/public_html/xml"
    uploaded_file_path = www_dir + "/" + rss_file_name

        
    def setUp(self):
        feedmakerutil.remove_file(self.uploaded_file_path)
            
            
    def test_0_upload_first(self):
        cmd = "upload.py %s" % self.rss_file_name
        (result, error) = feedmakerutil.exec_cmd(cmd)
        
        self.assertTrue(result)
        self.assertTrue("success" in result)
        self.assertTrue(os.path.isfile(self.uploaded_file_path))
        

    def test_1_upload_unchanged(self):
        cmd = "cp %s %s" % (self.rss_file_name, self.old_rss_file_name)
        (result, error) = feedmakerutil.exec_cmd(cmd)
        
        cmd = "upload.py %s" % self.rss_file_name
        (result, error) = feedmakerutil.exec_cmd(cmd)
        
        self.assertTrue(result)
        self.assertTrue("Upload failed! No change from the previous RSS file" in result)
        self.assertFalse(os.path.isfile(self.uploaded_file_path))

        
    def test_2_upload_changed(self):
        cmd = "cp %s %s" % (self.different_rss_file_name, self.old_rss_file_name)
        (result, error) = feedmakerutil.exec_cmd(cmd)
        
        cmd = "upload.py %s" % self.rss_file_name
        (result, error) = feedmakerutil.exec_cmd(cmd)
        
        self.assertTrue(result and result != "")
        self.assertTrue("success" in result)
        self.assertTrue(os.path.isfile(self.uploaded_file_path))
        
        
    def tearDown(self):
        feedmakerutil.remove_file(self.uploaded_file_path)
        feedmakerutil.remove_file(self.old_rss_file_name)

        
if __name__ == "__main__":
    unittest.main()
