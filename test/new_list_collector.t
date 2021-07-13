#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
import unittest
import logging
import logging.config
from feed_maker_util import Config
from new_list_collector import NewListCollector


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
logging.disable(logging.CRITICAL)


class NewListCollectorTest(unittest.TestCase):
    def setUp(self):
        config = Config()
        self.collection_conf = config.get_collection_configs()
        self.collector = NewListCollector(self.collection_conf, "temp_list.txt")

    def tearDown(self):
        pass

    def test_compose_a_url(self):
        url_list = ["http://a.com"]
        cmd = self.collector.compose_cmd(url_list)
        self.assertEqual("crawler.py  --render-js=false --verify-ssl=true --encoding='utf-8' --timeout=60 --retry=2 'http://a.com' | ./capture_item_link_title.py | shuf", cmd)

    def test_compose_two_urls(self):
        url_list = ["http://a.com", "http://b.com"]
        cmd = self.collector.compose_cmd(url_list)
        self.assertEqual("( crawler.py  --render-js=false --verify-ssl=true --encoding='utf-8' --timeout=60 --retry=2 'http://a.com' | ./capture_item_link_title.py; crawler.py  --render-js=false --verify-ssl=true --encoding='utf-8' --timeout=60 --retry=2 'http://b.com' | ./capture_item_link_title.py ) | shuf", cmd)

    def test_split_normal_result(self):
        test_input = '''
http://cartoon.media.daum.net/webtoon/view/dontgiveheart	그 책에 마음을 주지 마세요
http://cartoon.media.daum.net/webtoon/view/haksajaeseng	학사재생
http://cartoon.media.daum.net/webtoon/view/exchangerate	환율이 바뀌었나요?
http://cartoon.media.daum.net/webtoon/view/mujigaebridge	무지개다리 파수꾼
'''
        result_list = self.collector.split_result_into_items(test_input)
        self.assertEqual(4, len(result_list))
        for item in result_list:
            self.assertEqual(2, len(item))

    def test_split_abnormal_result(self):
        test_input = '''
http://cartoon.media.daum.net/webtoon/view/dontgiveheart	그 책에 마음을 주지 마세요
http://cartoon.media.daum.net/webtoon/view/haksajaeseng	
http://cartoon.media.daum.net/webtoon/view/exchangerate
http://cartoon.media.daum.net/webtoon/view/mujigaebridge	무지개다리 파수꾼
'''
        result_list = self.collector.split_result_into_items(test_input)
        self.assertEqual(0, len(result_list))



if __name__ == "__main__":
    unittest.main()
