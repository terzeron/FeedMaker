#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import logging.config
from pathlib import Path
from bin.feed_maker_util import Config

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = Config(feed_dir_path=Path.cwd())
        if not self.config:
            LOGGER.error("can't get configuration")

    def tearDown(self):
        del self.config

    def test_init(self):
        actual = self.config is not None
        self.assertTrue(actual)
        actual = isinstance(self.config, Config)
        self.assertTrue(actual)

    def test_get_bool_config_value(self):
        collection_conf = self.config.conf["collection"]
        extraction_conf = self.config.conf["extraction"]

        # existent, without default
        actual = self.config._get_bool_config_value(collection_conf, "verify_ssl")
        expected = True
        self.assertEqual(expected, actual)

        # existent, with default
        actual = self.config._get_bool_config_value(collection_conf, "verify_ssl", False)
        expected = True
        self.assertEqual(expected, actual)

        # not existent, without default
        actual = self.config._get_bool_config_value(extraction_conf, "verify_ssl")
        expected = False
        self.assertEqual(expected, actual)

        # not existent, with default
        actual = self.config._get_bool_config_value(extraction_conf, "verify_ssl", False)
        expected = False
        self.assertEqual(expected, actual)

    def test_get_str_config_value(self):
        collection_conf = self.config.conf["collection"]
        extraction_conf = self.config.conf["extraction"]

        # existent, without default
        actual = self.config._get_str_config_value(collection_conf, "encoding")
        self.assertEqual("utf-8", actual)

        # existent, with default
        actual = self.config._get_str_config_value(collection_conf, "encoding", "cp949")
        self.assertEqual("utf-8", actual)

        # not existent, with default
        actual = self.config._get_str_config_value(extraction_conf, "encoding", "cp949")
        self.assertEqual("cp949", actual)

        # not existent, without default
        actual = self.config._get_str_config_value(extraction_conf, "encoding")
        self.assertIsNone(actual)

    def test_get_int_config_value(self):
        collection_conf = self.config.conf["collection"]
        extraction_conf = self.config.conf["extraction"]

        # existent, without default
        actual = self.config._get_int_config_value(extraction_conf, "timeout")
        self.assertEqual(30, actual)

        # existent, with default
        actual = self.config._get_int_config_value(extraction_conf, "timeout", 20)
        self.assertEqual(30, actual)

        # not existent, without default
        actual = self.config._get_int_config_value(collection_conf, "timeout")
        self.assertIsNone(actual)

        # not existent, with default
        actual = self.config._get_int_config_value(collection_conf, "timeout", 10)
        self.assertEqual(10, actual)

    def test_get_float_config_value(self):
        collection_conf = self.config.conf["collection"]
        extraction_conf = self.config.conf["extraction"]

        # existent, without default
        actual = self.config._get_float_config_value(collection_conf, "unit_size_per_day")
        expected = 1.5
        self.assertEqual(expected, actual)

        # existent, with default
        actual = self.config._get_float_config_value(collection_conf, "unit_size_per_day", 3.3)
        self.assertEqual(1.5, actual)

        # not existent, without default
        actual = self.config._get_float_config_value(extraction_conf, "unit_size_per_day")
        self.assertIsNone(actual)

        # not existent, with default
        actual = self.config._get_float_config_value(extraction_conf, "unit_size_per_day", 5.8)
        self.assertEqual(5.8, actual)

    def test_get_config_value_list(self):
        collection_conf = self.config.conf["collection"]
        actual = self.config._get_list_config_value(collection_conf, "list_url_list", [])
        expected = ["https://terms.naver.com/list.naver?cid=58737&categoryId=58737&page=1",
                    "https://terms.naver.com/list.naver?cid=58737&categoryId=58737&page=2"]
        self.assertEqual(expected, actual)

        actual2 = self.config._get_dict_config_value(collection_conf, "headers", {})
        self.assertEqual({}, actual2)

        actual2 = self.config._get_dict_config_value(collection_conf, "headers")
        self.assertEqual({}, actual2)

    def test_get_collection_configs(self):
        configs = self.config.get_collection_configs()
        actual = isinstance(configs, dict)
        self.assertTrue(actual)

        actual = configs["item_capture_script"]
        self.assertEqual("./capture_item_link_title.py", actual)

        actual = configs["ignore_old_list"]
        self.assertFalse(actual)

        actual = configs["sort_field_pattern"]
        self.assertIsNone(actual)

        actual = configs["unit_size_per_day"]
        self.assertEqual(1.5, actual)

        actual = configs["list_url_list"]
        expected = ["https://terms.naver.com/list.naver?cid=58737&categoryId=58737&page=1",
                    "https://terms.naver.com/list.naver?cid=58737&categoryId=58737&page=2"]
        self.assertEqual(expected, actual)

        actual = configs["post_process_script_list"]
        expected = ['shuf']
        self.assertEqual(expected, actual)

    def test_get_extraction_configs(self):
        configs = self.config.get_extraction_configs()
        actual = isinstance(configs, dict)
        self.assertTrue(actual)

        actual = configs["render_js"]
        self.assertFalse(actual)

        actual = configs["user_agent"]
        self.assertTrue(actual)

        actual = configs["element_id_list"]
        expected = ["ct", "content"]
        self.assertEqual(expected, actual)

        actual = configs["element_class_list"]
        expected = ["se_doc_viewer", "content_view"]
        self.assertEqual(expected, actual)

        actual = configs["element_path_list"]
        expected = []
        self.assertEqual(expected, actual)

        actual = configs["post_process_script_list"]
        expected = ["post_process_script_for_navercast.py"]
        self.assertEqual(expected, actual)

        actual2 = configs["headers"]
        self.assertEqual({}, actual2)

    def test_get_rss_configs(self):
        configs = self.config.get_rss_configs()
        actual = isinstance(configs, dict)
        self.assertTrue(actual)

        actual = configs["rss_title"]
        expected = "네이버캐스트 모바일"
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
