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

from utils.update_manga_site import update_domain, check_site, print_usage, main
from bin.feed_maker_util import NotFoundConfigFileError, InvalidConfigFileError, NotFoundConfigItemError


class TestUpdateMangaSite(unittest.TestCase):
    def setUp(self):  # type: ignore
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

    def tearDown(self):  # type: ignore
        """Clean up after each test method."""
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

        # Mock git commands
        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "")

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

        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "")

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

        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "")

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

        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "")
            
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

        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "")
            
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

        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "")
            
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

        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "git error")
            
            result = update_domain(test_run=False, new_number=456)
            
            self.assertTrue(result)

    def test_update_domain_multiple_feeds(self):
        """Test update_domain with multiple feed directories."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create test feed config for test_feed directory
        test_feed_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/test_feed/list"
                    ]
                }
            }
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(test_feed_config, f)

        # Create multiple feed directories
        feed_dirs = ["feed1", "feed2", "feed3"]
        for feed_dir in feed_dirs:
            feed_path = Path(feed_dir)
            feed_path.mkdir()
            conf_file = feed_path / "conf.json"
            individual_feed_config: Dict[str, Any] = {
                "configuration": {
                    "collection": {
                        "list_url_list": [
                            f"https://example.com123/{feed_dir}/list"
                        ]
                    }
                }
            }
            with open(conf_file, 'w', encoding='utf-8') as f:
                json.dump(individual_feed_config, f)

        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "")
            
            result = update_domain(test_run=False, new_number=456)
            
            self.assertTrue(result)

            # Check that all feeds were updated
            for feed_dir in feed_dirs:
                conf_file = Path(feed_dir) / "conf.json"
                with open(conf_file, 'r', encoding='utf-8') as f:
                    updated_config = json.load(f)
                    expected_url = f"https://example.com456/{feed_dir}/list"
                    self.assertEqual(updated_config["configuration"]["collection"]["list_url_list"][0], expected_url)

    def test_update_domain_skip_dot_directories(self):
        """Test update_domain skips directories starting with dot."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create test feed config for test_feed directory
        test_feed_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/test_feed/list"
                    ]
                }
            }
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(test_feed_config, f)

        # Create a dot directory
        dot_dir = Path(".git")
        dot_dir.mkdir()
        conf_file = dot_dir / "conf.json"
        with open(conf_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)

        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "")
            
            result = update_domain(test_run=False, new_number=456)
            
            self.assertTrue(result)

    def test_update_domain_skip_files(self):
        """Test update_domain skips files (only processes directories)."""
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        # Create test feed config for test_feed directory
        test_feed_config: Dict[str, Any] = {
            "configuration": {
                "collection": {
                    "list_url_list": [
                        "https://example.com123/test_feed/list"
                    ]
                }
            }
        }
        with open(self.conf_file_path, 'w', encoding='utf-8') as f:
            json.dump(test_feed_config, f)

        # Create a file (not directory)
        test_file = Path("test_file.txt")
        test_file.touch()

        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "")
            
            result = update_domain(test_run=False, new_number=456)
            
            self.assertTrue(result)

    def test_check_site_success(self):
        """Test check_site function success."""
        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("Site check successful", "")
            
            with patch('sys.stdout', new=StringIO()) as fake_out:
                result = check_site()
                
                self.assertTrue(result)
                output = fake_out.getvalue()
                self.assertIn("Site check successful", output)

    def test_check_site_error(self):
        """Test check_site function with error."""
        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "Site check failed")
            
            with patch('sys.stdout', new=StringIO()) as fake_out:
                result = check_site()
                
                self.assertTrue(result)
                output = fake_out.getvalue()
                self.assertIn("Site check failed", output)

    def test_main_success(self):
        """Test main function with valid arguments."""
        with patch('utils.update_manga_site.update_domain') as mock_update:
            mock_update.return_value = True
            
            with patch('utils.update_manga_site.check_site') as mock_check:
                mock_check.return_value = True
                
                with patch('sys.argv', ['update_manga_site.py', '456']):
                    result = main()
                    
                    self.assertEqual(result, 0)
                    mock_update.assert_called_once_with(False, 456)
                    mock_check.assert_called_once()

    def test_main_test_mode(self):
        """Test main function with test mode flag."""
        with patch('utils.update_manga_site.update_domain') as mock_update:
            mock_update.return_value = True
            
            with patch('sys.argv', ['update_manga_site.py', '-t', '456']):
                result = main()
                
                self.assertEqual(result, 0)
                mock_update.assert_called_once_with(True, 456)

    def test_main_no_arguments(self):
        """Test main function with no arguments."""
        with patch('sys.argv', ['update_manga_site.py']):
            with patch('sys.stdout', new=StringIO()) as fake_out:
                result = main()
                
                self.assertEqual(result, -1)
                output = fake_out.getvalue()
                self.assertIn("Usage:", output)

    def test_main_invalid_number(self):
        """Test main function with invalid number."""
        with patch('sys.argv', ['update_manga_site.py', 'invalid']):
            with self.assertRaises(ValueError):
                main()

    def test_main_update_domain_failure(self):
        """Test main function when update_domain fails."""
        with patch('utils.update_manga_site.update_domain') as mock_update:
            mock_update.return_value = False
            
            with patch('sys.argv', ['update_manga_site.py', '456']):
                result = main()
                
                self.assertEqual(result, 0)
                mock_update.assert_called_once_with(False, 456)

    def test_update_domain_url_pattern_matching(self):
        """Test update_domain with various URL patterns."""
        test_cases = [
            ("https://example.com123/test", "https://example.com456/test"),
            ("http://example.com123/test", "http://example.com456/test"),
            ("https://sub.example.com123/test", "https://sub.example.com456/test"),
            ("https://example.com123", "https://example.com456"),
            ("https://example.com123/", "https://example.com456/"),
        ]
        
        for original_url, expected_url in test_cases:
            with self.subTest(original_url=original_url):
                site_config: Dict[str, Any] = {
                    "url": original_url,
                    "referer": "https://example.com123/referer"
                }
                with open(self.site_config_path, 'w', encoding='utf-8') as f:
                    json.dump(site_config, f)

                # Create test feed config for each test case
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

                with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
                    mock_exec.return_value = ("", "")
                    
                    result = update_domain(test_run=False, new_number=456)
                    
                    self.assertTrue(result)
                    
                    with open(self.site_config_path, 'r', encoding='utf-8') as f:
                        updated_config = json.load(f)
                        self.assertEqual(updated_config["url"], expected_url)

    def test_update_domain_list_url_pattern_matching(self):
        """Test update_domain with various list URL patterns."""
        test_cases = [
            ("https://example.com123/list", "https://example.com456/list"),
            ("https://example.com123/list.html", "https://example.com456/list.html"),
            ("https://example.com123/list/", "https://example.com456/list/"),
            ("https://example.com123/list.php", "https://example.com456/list.php"),
        ]
        
        site_config: Dict[str, Any] = {
            "url": "https://example.com123/test",
            "referer": "https://example.com123/referer"
        }
        with open(self.site_config_path, 'w', encoding='utf-8') as f:
            json.dump(site_config, f)

        for original_list_url, expected_list_url in test_cases:
            with self.subTest(original_list_url=original_list_url):
                feed_config: Dict[str, Any] = {
                    "configuration": {
                        "collection": {
                            "list_url_list": [original_list_url]
                        }
                    }
                }
                with open(self.conf_file_path, 'w', encoding='utf-8') as f:
                    json.dump(feed_config, f)

                with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
                    mock_exec.return_value = ("", "")
                    
                    result = update_domain(test_run=False, new_number=456)
                    
                    self.assertTrue(result)
                    
                    with open(self.conf_file_path, 'r', encoding='utf-8') as f:
                        updated_config = json.load(f)
                        self.assertEqual(updated_config["configuration"]["collection"]["list_url_list"][0], expected_list_url)

    def test_update_domain_cleanup_files(self):
        """Test update_domain cleans up old files."""
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

        # Create files that should be cleaned up
        xml_file = self.feed_dir / f"{self.feed_dir.name}.xml"
        xml_file.touch()
        old_xml_file = xml_file.with_suffix(xml_file.suffix + ".old")
        old_xml_file.touch()

        with patch('utils.update_manga_site.Process.exec_cmd') as mock_exec:
            mock_exec.return_value = ("", "")
            
            result = update_domain(test_run=False, new_number=456)
            
            self.assertTrue(result)
            
            # Check that files were cleaned up
            self.assertFalse(xml_file.exists())
            self.assertFalse(old_xml_file.exists())
            self.assertFalse(self.newlist_dir.exists())


if __name__ == "__main__":
    unittest.main()  # type: ignore