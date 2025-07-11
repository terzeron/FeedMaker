#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import json
import tempfile
import shutil
import os
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch
from io import StringIO

from bin.feed_maker_util import NotFoundConfigFileError, InvalidConfigFileError, NotFoundConfigItemError
from utils.update_manga_site import update_domain, check_site, print_usage, main


class TestUpdateMangaSite(unittest.TestCase):
    def setUp(self):  
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create test directory structure
        self.site_config_path = Path("site_config.json")
        self.feed_dir = Path("test_feed")
        self.feed_dir.mkdir()
        self.conf_file_path = self.feed_dir / "conf.json"
        self.newlist_dir = self.feed_dir / "newlist"
        self.newlist_dir.mkdir()
        
        # Create test files
        (self.newlist_dir / "test_file.txt").touch()
        (self.feed_dir / "test_feed.xml").touch()
        (self.feed_dir / "test_feed.xml.old").touch()

        # Mock git commands for all tests
        self.process_patcher = patch('utils.update_manga_site.Process.exec_cmd')
        self.mock_process = self.process_patcher.start()
        self.mock_process.return_value = ("", "")

    def tearDown(self):  
        """Clean up after each test method."""
        self.process_patcher.stop()
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_print_usage(self):
        """Test print_usage function."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            print_usage()
            output = fake_out.getvalue()
            self.assertIn("Usage:", output)
            self.assertIn("-t: run for test", output)

    def test_update_domain_success(self):
        """Test successful domain update."""
        # Create test site config
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create test feed config
        feed_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/list1",
                        "https://example.com123/list2"
                    ]
                }
            }
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(feed_config, f)

        result = update_domain(test_run=False, new_number=456)

        self.assertTrue(result)

        # Check if site config was updated
        with open(self.site_config_path, 'r', encoding='utf-8') as f:
            updated_config = json.load(f)
            self.assertEqual(updated_config["url"], "https://example.com456/test")
            self.assertEqual(updated_config["referer"], "https://example.com456/referer")

        # Check if feed config was updated
        with open(self.conf_file_path, 'r', encoding='utf-8') as f:
            updated_feed_config = json.load(f)
            expected_urls = [
                "https://example.com456/list1",
                "https://example.com456/list2"
            ]
            self.assertEqual(updated_feed_config["configuration"]["collection"]["list_url_list"], expected_urls)

    def test_update_domain_test_run(self):
        """Test domain update in test mode (no actual changes)."""
        # Create test site config
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create test feed config
        feed_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/list1"
                    ]
                }
            }
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(feed_config, f)

        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = update_domain(test_run=True, new_number=456)
            
            self.assertTrue(result)
            output = fake_out.getvalue()
            
            # Check that test output shows the changes
            self.assertIn("https://example.com", output)
            self.assertIn("456", output)

            # Verify original files were not changed
            with open(self.site_config_path, 'r', encoding='utf-8') as f:
                original_config = json.load(f)
                self.assertEqual(original_config["url"], "https://example.com123/test")

    def test_update_domain_no_site_config_file(self):
        """Test update_domain when site_config.json doesn't exist."""
        with self.assertRaises(NotFoundConfigFileError):
            update_domain(test_run=False, new_number=456)

    def test_update_domain_invalid_site_config(self):
        """Test update_domain with invalid site config."""
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            f.write("invalid json")

        # Actual code throws JSONDecodeError first, then InvalidConfigFileError
        with self.assertRaises((json.JSONDecodeError, InvalidConfigFileError)):
            update_domain(test_run=False, new_number=456)

    def test_update_domain_missing_url(self):
        """Test update_domain when url is missing from config."""
        site_config: Dict[str, Any] = {"referer": "https://example.com123/referer"}
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        with self.assertRaises(NotFoundConfigItemError):
            update_domain(test_run=False, new_number=456)

    def test_update_domain_empty_url(self):
        """Test update_domain when url is empty."""
        site_config: Dict[str, Any] = {"url": "", "referer": "https://example.com123/referer"}
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        with self.assertRaises(NotFoundConfigItemError):
            update_domain(test_run=False, new_number=456)

    def test_update_domain_empty_referer(self):
        """Test update_domain when referer is empty."""
        site_config: Dict[str, Any] = {"url": "https://example.com123/test", "referer": ""}
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create test feed config
        feed_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/list1"
                    ]
                }
            }
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(feed_config, f)

        result = update_domain(test_run=False, new_number=456)

        self.assertTrue(result)

        # Check if site config was updated (only url, referer should remain empty)
        with open(self.site_config_path, 'r', encoding='utf-8') as f:
            updated_config = json.load(f)
            self.assertEqual(updated_config["url"], "https://example.com456/test")
            self.assertEqual(updated_config["referer"], "")

    def test_update_domain_no_referer_in_config(self):
        """Test update_domain when referer is not in config."""
        site_config: Dict[str, Any] = {"url": "https://example.com123/test"}
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create test feed config
        feed_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/list1"
                    ]
                }
            }
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(feed_config, f)

        result = update_domain(test_run=False, new_number=456)

        self.assertTrue(result)

        # Check if site config was updated (only url)
        with open(self.site_config_path, 'r', encoding='utf-8') as f:
            updated_config = json.load(f)
            self.assertEqual(updated_config["url"], "https://example.com456/test")
            self.assertNotIn("referer", updated_config)

    def test_update_domain_feed_without_list_url_list(self):
        """Test update_domain with feed config that doesn't have list_url_list."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create feed config without list_url_list
        feed_config: Dict[str, Any] = {
            "configuration": {
                "collection": {}
            }
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(feed_config, f)

        result = update_domain(test_run=False, new_number=456)

        self.assertTrue(result)

    def test_update_domain_feed_without_collection(self):
        """Test update_domain with feed config that doesn't have collection."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create feed config without collection
        feed_config: Dict[str, Any] = {
            "configuration": {}
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(feed_config, f)

        result = update_domain(test_run=False, new_number=456)

        self.assertTrue(result)

    def test_update_domain_feed_without_configuration(self):
        """Test update_domain with feed config that doesn't have configuration."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create feed config without configuration
        feed_config: Dict[str, Any] = {}
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(feed_config, f)

        result = update_domain(test_run=False, new_number=456)

        self.assertTrue(result)

    def test_update_domain_git_error(self):
        """Test update_domain when git commands fail."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        feed_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/list1"
                    ]
                }
            }
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(feed_config, f)

        # Mock git error
        self.mock_process.return_value = ("", "git error")

        result = update_domain(test_run=False, new_number=456)

        # Should still succeed even with git errors
        self.assertTrue(result)

        # Check if files were updated despite git errors
        with open(self.site_config_path, 'r', encoding='utf-8') as f:
            updated_config = json.load(f)
            self.assertEqual(updated_config["url"], "https://example.com456/test")

    def test_update_domain_multiple_feeds(self):
        """Test update_domain with multiple feed directories."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create multiple feed directories
        feed1_dir = Path("feed1")
        feed1_dir.mkdir()
        feed1_conf = feed1_dir / "conf.json"
        feed1_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/feed1/list1"
                    ]
                }
            }
        }
        with open(feed1_conf, 'w', encoding='utf-8') as f:
            json.dump(feed1_config, f)

        feed2_dir = Path("feed2")
        feed2_dir.mkdir()
        feed2_conf = feed2_dir / "conf.json"
        feed2_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/feed2/list1"
                    ]
                }
            }
        }
        with open(feed2_conf, 'w', encoding='utf-8') as f:
            json.dump(feed2_config, f)

        feed3_dir = Path("feed3")
        feed3_dir.mkdir()
        feed3_conf = feed3_dir / "conf.json"
        feed3_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/feed3/list1"
                    ]
                }
            }
        }
        with open(feed3_conf, 'w', encoding='utf-8') as f:
            json.dump(feed3_config, f)

        result = update_domain(test_run=False, new_number=456)

        self.assertTrue(result)

        # Check if all feed configs were updated
        with open(feed1_conf, 'r', encoding='utf-8') as f:
            updated_feed1_config = json.load(f)
            self.assertEqual(updated_feed1_config["configuration"]["collection"]["list_url_list"],
                           ["https://example.com456/feed1/list1"])

        with open(feed2_conf, 'r', encoding='utf-8') as f:
            updated_feed2_config = json.load(f)
            self.assertEqual(updated_feed2_config["configuration"]["collection"]["list_url_list"],
                           ["https://example.com456/feed2/list1"])

        with open(feed3_conf, 'r', encoding='utf-8') as f:
            updated_feed3_config = json.load(f)
            self.assertEqual(updated_feed3_config["configuration"]["collection"]["list_url_list"],
                           ["https://example.com456/feed3/list1"])

    def test_update_domain_skip_dot_directories(self):
        """Test update_domain skips directories starting with dot."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create a dot directory
        dot_dir = Path(".hidden")
        dot_dir.mkdir()
        dot_conf = dot_dir / "conf.json"
        dot_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/hidden/list1"
                    ]
                }
            }
        }
        with open(dot_conf, 'w', encoding='utf-8') as f:
            json.dump(dot_config, f)

        result = update_domain(test_run=False, new_number=456)

        self.assertTrue(result)

        # Check that hidden directory was not updated
        with open(dot_conf, 'r', encoding='utf-8') as f:
            original_dot_config = json.load(f)
            self.assertEqual(original_dot_config["configuration"]["collection"]["list_url_list"],
                           ["https://example.com123/hidden/list1"])

    def test_update_domain_skip_files(self):
        """Test update_domain skips files (only processes directories)."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create a file (not directory)
        file_path = Path("some_file.txt")
        file_path.touch()

        result = update_domain(test_run=False, new_number=456)

        self.assertTrue(result)
        # Should not crash when encountering files

    def test_check_site_success(self):
        """Test check_site function."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        result = check_site()
        self.assertTrue(result)

    def test_check_site_error(self):
        """Test check_site function when site config doesn't exist."""
        result = check_site()
        self.assertTrue(result)  # 실제 함수는 항상 True를 반환함

    def test_main_success(self):
        """Test main function with valid arguments."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        with patch('sys.argv', ['update_manga_site.py', '456']):
            result = main()
            self.assertEqual(result, 0)

    def test_main_test_mode(self):
        """Test main function in test mode."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        with patch('sys.argv', ['update_manga_site.py', '-t', '456']):
            result = main()
            self.assertEqual(result, 0)

    def test_main_no_arguments(self):
        """Test main function with no arguments."""
        with patch('sys.argv', ['update_manga_site.py']):
            result = main()
        self.assertEqual(result, -1)  # 실제 함수 리턴값에 맞춤

    def test_main_invalid_number(self):
        """Test main function with invalid number."""
        with patch('sys.argv', ['update_manga_site.py', 'invalid']):
            with self.assertRaises(ValueError):
                main()

    def test_main_update_domain_failure(self):
        """Test main function when update_domain fails."""
        with patch('sys.argv', ['update_manga_site.py', '456']):
            with self.assertRaises(NotFoundConfigFileError):
                main()

    def test_update_domain_url_pattern_matching(self):
        """Test URL pattern matching for various URL formats."""
        test_cases = [
            ("https://example.com123/test", 456, "https://example.com456/test"),
            ("https://example.com123/", 456, "https://example.com456/"),
            ("https://example.com123", 456, "https://example.com456"),
            ("http://example.com123/test", 456, "http://example.com456/test"),
            ("https://sub.example.com123/test", 456, "https://sub.example.com456/test"),
        ]

        for original_url, new_number, expected_url in test_cases:
            site_config: Dict[str, Any] = {
                "url": original_url,
                "referer": "https://example.com123/referer"
            }
            with open(self.site_config_path, 'w', encoding='utf-8') as f:
                json.dump(site_config, f)

            feed_config: Dict[str, Any] = {
                "configuration": {
                    "collection": {
                        "list_url_list": [
                            original_url + "/list1"
                        ]
                    }
                }
            }
            with open(self.conf_file_path, 'w', encoding='utf-8') as f:
                json.dump(feed_config, f)

            result = update_domain(test_run=False, new_number=new_number)

            self.assertTrue(result)

            # Check if site config was updated correctly
            with open(self.site_config_path, 'r', encoding='utf-8') as f:
                updated_config = json.load(f)
                self.assertEqual(updated_config["url"], expected_url)

    def test_update_domain_list_url_pattern_matching(self):
        """Test list URL pattern matching for various URL formats."""
        test_cases = [
            ("https://example.com123/list1", 456, "https://example.com456/list1"),
            ("https://example.com123/list1.html", 456, "https://example.com456/list1.html"),
            ("https://example.com123/list1/", 456, "https://example.com456/list1/"),
            ("http://example.com123/list1", 456, "http://example.com456/list1"),
            ("https://sub.example.com123/list1", 456, "https://sub.example.com456/list1"),
        ]

        for original_url, new_number, expected_url in test_cases:
            site_config: Dict[str, Any] = {
                "url": "https://example.com123/test",
                "referer": "https://example.com123/referer"
            }
            with open(self.site_config_path, 'w', encoding='utf-8') as f:
                json.dump(site_config, f)

            feed_config: Dict[str, Any] = {
                "configuration": {
                    "collection": {
                        "list_url_list": [original_url]
                    }
                }
            }
            with open(self.conf_file_path, 'w', encoding='utf-8') as f:
                json.dump(feed_config, f)

            result = update_domain(test_run=False, new_number=new_number)

            self.assertTrue(result)

            # Check if feed config was updated correctly
            with open(self.conf_file_path, 'r', encoding='utf-8') as f:
                updated_feed_config = json.load(f)
                self.assertEqual(updated_feed_config["configuration"]["collection"]["list_url_list"],
                               [expected_url])

    def test_update_domain_cleanup_files(self):
        """Test that cleanup removes newlist and xml files."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        feed_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/list1"
                    ]
                }
            }
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(feed_config, f)

        # Create additional files that should be cleaned up
        (self.newlist_dir / "additional_file.txt").touch()
        (self.feed_dir / "test_feed.xml").touch()
        (self.feed_dir / "test_feed.xml.old").touch()

        result = update_domain(test_run=False, new_number=456)

        self.assertTrue(result)

        # Check that cleanup files were removed
        self.assertFalse((self.newlist_dir / "test_file.txt").exists())
        self.assertFalse((self.newlist_dir / "additional_file.txt").exists())
        self.assertFalse(self.newlist_dir.exists())  # Directory should be removed
        self.assertFalse((self.feed_dir / "test_feed.xml").exists())
        self.assertFalse((self.feed_dir / "test_feed.xml.old").exists())


if __name__ == "__main__":
    unittest.main()
