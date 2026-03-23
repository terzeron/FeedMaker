#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging.config
import socket

from bs4 import BeautifulSoup, Tag

from bin.feed_maker_util import Data, Env, NotFoundEnvError, Config, NotFoundConfigFileError, InvalidConfigFileError, NotFoundConfigItemError, PathUtil, FileManager, URL, HTMLExtractor, IO, Process, URLSafety, header_str

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestHeaderStr(unittest.TestCase):
    """header_str module-level constant"""

    def test_header_str_contains_meta(self) -> None:
        self.assertIn("Content-Type", header_str)
        self.assertIn("text/html", header_str)
        self.assertIn("viewport", header_str)
        self.assertIn("<style>", header_str)


class TestDataEdgeCases(unittest.TestCase):
    """Data._to_hashable edge cases: set/frozenset (line 48) and unhashable (line 50)"""

    def test_to_hashable_set(self) -> None:
        result = Data._to_hashable({1, 2, 3})
        self.assertIsInstance(result, frozenset)

    def test_to_hashable_frozenset(self) -> None:
        result = Data._to_hashable(frozenset([1, 2]))
        self.assertIsInstance(result, frozenset)

    def test_to_hashable_unhashable_type(self) -> None:
        class Unhashable:
            __hash__ = None  # type: ignore

        with self.assertRaises(TypeError):
            Data._to_hashable(Unhashable())


class TestEnv(unittest.TestCase):
    """Env.get() with missing env var and default"""

    def test_get_existing_env_var(self) -> None:
        with patch.dict(os.environ, {"TEST_VAR_XYZ": "hello"}):
            self.assertEqual("hello", Env.get("TEST_VAR_XYZ"))

    def test_get_missing_env_var_returns_default(self) -> None:
        # When default_value is "" (default), os.getenv returns "" not None
        result = Env.get("NONEXISTENT_VAR_ABC_12345")
        self.assertEqual("", result)

    def test_get_with_explicit_default(self) -> None:
        result = Env.get("NONEXISTENT_VAR_ABC_12345", "fallback")
        self.assertEqual("fallback", result)


class TestProcessResolveExecutable(unittest.TestCase):
    """Process._resolve_executable edge cases: lines 94, 101, 105-108, 117"""

    def test_empty_program(self) -> None:
        result = Process._resolve_executable("", Path.cwd())
        self.assertIsNone(result)

    def test_absolute_path_nonexistent(self) -> None:
        result = Process._resolve_executable("/nonexistent/path/to/bin", Path.cwd())
        self.assertIsNone(result)

    def test_relative_path_nonexistent(self) -> None:
        result = Process._resolve_executable("./nonexistent_script.sh", Path.cwd())
        self.assertIsNone(result)

    def test_relative_path_parent_nonexistent(self) -> None:
        result = Process._resolve_executable("../nonexistent_script.sh", Path.cwd())
        self.assertIsNone(result)

    def test_path_lookup_not_executable(self) -> None:
        # which returns a path but it's not executable
        with patch("bin.feed_maker_util.which", return_value="/some/path"):
            with patch("bin.feed_maker_util.Path.resolve", return_value=Path("/some/path")):
                with patch("bin.feed_maker_util.Path.exists", return_value=True):
                    with patch("bin.feed_maker_util.Path.is_file", return_value=True):
                        with patch("os.access", return_value=False):
                            result = Process._resolve_executable("somecmd", Path.cwd())
                            self.assertIsNone(result)


class TestProcessExecCmd(unittest.TestCase):
    """Process.exec_cmd edge cases: lines 162-170"""

    def test_exec_cmd_stderr_with_error_keyword(self) -> None:
        """stderr containing 'error' should be returned as error"""
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("output", "some error occurred")
            mock_proc.returncode = 0
            mock_proc.__enter__ = lambda s: mock_proc
            mock_proc.__exit__ = MagicMock(return_value=False)
            mock_popen.return_value = mock_proc

            # Need a valid argv
            with patch.object(Process, "_build_argv", return_value=(["echo", "hi"], "")):
                result, error = Process.exec_cmd("echo hi")
                self.assertEqual("", result)
                self.assertIn("error", error.lower())

    def test_exec_cmd_stderr_warning_no_error(self) -> None:
        """stderr without 'error' keyword should just log warning"""
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("output", "some warning message")
            mock_proc.returncode = 0
            mock_proc.__enter__ = lambda s: mock_proc
            mock_proc.__exit__ = MagicMock(return_value=False)
            mock_popen.return_value = mock_proc

            with patch.object(Process, "_build_argv", return_value=(["echo", "hi"], "")):
                result, error = Process.exec_cmd("echo hi")
                self.assertEqual("output", result)
                self.assertEqual("", error)

    def test_exec_cmd_called_process_error(self) -> None:
        """CalledProcessError should be caught (line 167-168)"""
        import subprocess

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = subprocess.CalledProcessError(1, "cmd")
            # Need __enter__ setup but side_effect overrides it
            with patch.object(Process, "_build_argv", return_value=(["echo", "hi"], "")):
                result, error = Process.exec_cmd("echo hi")
                self.assertEqual("", result)
                self.assertIn("non-zero exit status", error)

    def test_exec_cmd_subprocess_error(self) -> None:
        """SubprocessError should be caught (line 169-170)"""
        import subprocess

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = subprocess.SubprocessError("broken")
            with patch.object(Process, "_build_argv", return_value=(["echo", "hi"], "")):
                result, error = Process.exec_cmd("echo hi")
                self.assertEqual("", result)
                self.assertIn("Error in execution of command", error)


class TestProcessFindAndKill(unittest.TestCase):
    """Process._find_process_list and kill_process_group edge cases: lines 179-180, 184, 201-202"""

    def test_find_process_list_no_such_process(self) -> None:
        """NoSuchProcess during iteration should be handled (line 179-180)"""
        import psutil

        mock_proc = MagicMock()
        mock_proc.as_dict.side_effect = psutil.NoSuchProcess(999)
        with patch("psutil.process_iter", return_value=[mock_proc]):
            result = Process._find_process_list("some_pattern")
            self.assertEqual([], result)

    def test_find_process_list_no_pid(self) -> None:
        """Process with no pid should be skipped (line 184)"""
        mock_proc = MagicMock()
        mock_proc.as_dict.return_value = {"pid": None, "cmdline": ["test"]}
        with patch("psutil.process_iter", return_value=[mock_proc]):
            result = Process._find_process_list("test")
            self.assertEqual([], result)

    def test_kill_process_group_no_such_process(self) -> None:
        """NoSuchProcess during kill should be handled (line 201-202)"""
        import psutil

        with patch.object(Process, "_find_process_list", return_value=[12345]):
            with patch("psutil.Process") as mock_ps:
                mock_ps.return_value.terminate.side_effect = psutil.NoSuchProcess(12345)
                count = Process.kill_process_group("pattern")
                self.assertEqual(0, count)


class TestProcessReplaceScriptPath(unittest.TestCase):
    """Process._replace_script_path edge case: line 143"""

    def test_invalid_dir_path(self) -> None:
        result = Process._replace_script_path("echo", Path("/nonexistent_dir_xyz"))
        self.assertIsNone(result)


class TestConfigErrorPaths(unittest.TestCase):
    """Config error paths: lines 453, 469, 479-481, 503-504, 513-514, 523-524, 533-534, 569, 604, 622"""

    def test_config_file_not_found(self) -> None:
        with self.assertRaises(NotFoundConfigFileError):
            Config(feed_dir_path=Path("/nonexistent_dir_xyz_abc"))

    def test_config_invalid_format(self) -> None:
        tmp_dir = Path(__file__).parent / "_tmp_config_test"
        tmp_dir.mkdir(exist_ok=True)
        conf_path = tmp_dir / Config.DEFAULT_CONF_FILE
        try:
            with conf_path.open("w", encoding="utf-8") as f:
                json.dump({"not_configuration": {}}, f)
            with self.assertRaises(InvalidConfigFileError):
                Config(feed_dir_path=tmp_dir)
        finally:
            conf_path.unlink(missing_ok=True)
            tmp_dir.rmdir()

    def test_get_collection_configs_missing(self) -> None:
        tmp_dir = Path(__file__).parent / "_tmp_config_test2"
        tmp_dir.mkdir(exist_ok=True)
        conf_path = tmp_dir / Config.DEFAULT_CONF_FILE
        try:
            with conf_path.open("w", encoding="utf-8") as f:
                json.dump({"configuration": {"rss": {"title": "test"}}}, f)
            config = Config(feed_dir_path=tmp_dir)
            with self.assertRaises(NotFoundConfigItemError):
                config.get_collection_configs()
        finally:
            conf_path.unlink(missing_ok=True)
            tmp_dir.rmdir()

    def test_get_extraction_configs_missing(self) -> None:
        tmp_dir = Path(__file__).parent / "_tmp_config_test3"
        tmp_dir.mkdir(exist_ok=True)
        conf_path = tmp_dir / Config.DEFAULT_CONF_FILE
        try:
            with conf_path.open("w", encoding="utf-8") as f:
                json.dump({"configuration": {"rss": {"title": "test"}}}, f)
            config = Config(feed_dir_path=tmp_dir)
            with self.assertRaises(NotFoundConfigItemError):
                config.get_extraction_configs()
        finally:
            conf_path.unlink(missing_ok=True)
            tmp_dir.rmdir()

    def test_get_rss_configs_missing(self) -> None:
        tmp_dir = Path(__file__).parent / "_tmp_config_test4"
        tmp_dir.mkdir(exist_ok=True)
        conf_path = tmp_dir / Config.DEFAULT_CONF_FILE
        try:
            with conf_path.open("w", encoding="utf-8") as f:
                json.dump({"configuration": {"collection": {"list_url_list": []}}}, f)
            config = Config(feed_dir_path=tmp_dir)
            with self.assertRaises(NotFoundConfigItemError):
                config.get_rss_configs()
        finally:
            conf_path.unlink(missing_ok=True)
            tmp_dir.rmdir()

    def test_get_int_config_value_type_error(self) -> None:
        """TypeError in _get_int_config_value returns None (line 503-504)"""
        result = Config._get_int_config_value({"key": None}, "key")
        self.assertIsNone(result)

    def test_get_float_config_value_type_error(self) -> None:
        """TypeError in _get_float_config_value returns None (line 513-514)"""
        result = Config._get_float_config_value({"key": None}, "key")
        self.assertIsNone(result)

    def test_get_list_config_value_type_error(self) -> None:
        """TypeError in _get_list_config_value (line 523-524)"""

        # To trigger TypeError, config_node[key] must raise TypeError
        # This is hard to trigger naturally. Use a mock dict.
        class TypeErrorDict(dict):  # type: ignore
            def __getitem__(self, key: str) -> None:
                raise TypeError("test")

        result = Config._get_list_config_value(TypeErrorDict({"key": True}), "key")
        self.assertIsNone(result)

    def test_get_dict_config_value_type_error(self) -> None:
        """TypeError in _get_dict_config_value (line 533-534)"""

        class TypeErrorDict(dict):  # type: ignore
            def __getitem__(self, key: str) -> None:
                raise TypeError("test")

        result = Config._get_dict_config_value(TypeErrorDict({"key": True}), "key")
        self.assertIsNone(result)


class TestPathUtilShortPath(unittest.TestCase):
    """PathUtil.short_path edge cases: lines 858"""

    def test_short_path_none(self) -> None:
        result = PathUtil.short_path(None)
        self.assertEqual("", result)

    def test_short_path_public_feed_dir(self) -> None:
        """Path under public_feed_dir_path should be shortened (line 858)"""
        public_dir = PathUtil.public_feed_dir_path
        test_path = public_dir / "some_feed" / "file.xml"
        result = PathUtil.short_path(test_path)
        self.assertIn("some_feed", result)
        self.assertNotIn(str(public_dir), result)

    def test_short_path_unrelated_path(self) -> None:
        """Path not under work_dir or public_feed_dir returns as-is"""
        test_path = Path("/tmp/unrelated/path.txt")
        result = PathUtil.short_path(test_path)
        self.assertEqual(str(test_path), result)


class TestFileManagerRemoveAllFiles(unittest.TestCase):
    """FileManager.remove_all_files: complete flow"""

    def setUp(self) -> None:
        self.test_dir = Path(__file__).parent / "_tmp_fm_test"
        self.test_dir.mkdir(exist_ok=True)
        (self.test_dir / "html").mkdir(exist_ok=True)
        (self.test_dir / "newlist").mkdir(exist_ok=True)

    def tearDown(self) -> None:
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_remove_all_files(self) -> None:
        # Create test files
        html_file = self.test_dir / "html" / "test.html"
        html_file.write_text("test")
        list_file = self.test_dir / "newlist" / "list.txt"
        list_file.write_text("test")
        rss_file = self.test_dir / (self.test_dir.name + ".xml")
        rss_file.write_text("test")
        old_rss = rss_file.with_suffix(rss_file.suffix + ".old")
        old_rss.write_text("test")
        start_idx = self.test_dir / "start_idx.txt"
        start_idx.write_text("0")
        nohup = self.test_dir / "nohup.out"
        nohup.write_text("test")

        FileManager.remove_all_files(self.test_dir)

        self.assertFalse(html_file.exists())
        self.assertFalse(list_file.exists())
        self.assertFalse(rss_file.exists())
        self.assertFalse(old_rss.exists())
        self.assertFalse(start_idx.exists())
        self.assertFalse(nohup.exists())


class TestFileManagerRemoveImageFilesWithZeroSize(unittest.TestCase):
    """FileManager.remove_image_files_with_zero_size: lines 797-803"""

    def test_remove_zero_size_images(self) -> None:
        test_dir = Path(__file__).parent / "_tmp_img_test"
        test_dir.mkdir(exist_ok=True)
        try:
            zero_file = test_dir / "zero.png"
            zero_file.write_text("")
            nonzero_file = test_dir / "nonzero.png"
            nonzero_file.write_text("data")

            FileManager.remove_image_files_with_zero_size(test_dir)

            self.assertFalse(zero_file.exists())
            self.assertTrue(nonzero_file.exists())
        finally:
            import shutil

            if test_dir.exists():
                shutil.rmtree(test_dir)

    def test_remove_image_files_nonexistent_dir(self) -> None:
        """Non-existent dir should not raise"""
        FileManager.remove_image_files_with_zero_size(Path("/nonexistent_xyz"))


class TestFileManagerRemoveTemporaryFiles(unittest.TestCase):
    """FileManager.remove_temporary_files"""

    def test_remove_temp_files(self) -> None:
        test_dir = Path(__file__).parent / "_tmp_temp_test"
        test_dir.mkdir(exist_ok=True)
        try:
            for name in ("nohup.out", "temp.html", "x.html"):
                (test_dir / name).write_text("test")

            FileManager.remove_temporary_files(test_dir)

            for name in ("nohup.out", "temp.html", "x.html"):
                self.assertFalse((test_dir / name).exists())
        finally:
            import shutil

            if test_dir.exists():
                shutil.rmtree(test_dir)


class TestFileManagerCacheMethods(unittest.TestCase):
    """FileManager.get_cache_file_path and get_cache_url: lines 730, 733-738"""

    def test_get_cache_url_with_suffix(self) -> None:
        url = FileManager.get_cache_url("http://example.com/img", "http://original.com/image.png", suffix=".jpg")
        self.assertTrue(url.endswith(".jpg"))
        self.assertTrue(url.startswith("http://example.com/img/"))

    def test_get_cache_url_without_suffix(self) -> None:
        url = FileManager.get_cache_url("http://example.com/img", "http://original.com/image.png")
        self.assertFalse(url.endswith(".jpg"))

    def test_get_cache_file_path_with_suffix(self) -> None:
        path = FileManager.get_cache_file_path(Path("/tmp"), "http://original.com/image.png", suffix=".webp")
        self.assertTrue(str(path).endswith(".webp"))

    def test_get_cache_file_path_without_suffix(self) -> None:
        path = FileManager.get_cache_file_path(Path("/tmp"), "http://original.com/image.png")
        self.assertFalse(str(path).endswith(".webp"))

    def test_get_cache_info_non_http_url(self) -> None:
        """Non-http URL just returns md5 without postfix (line 730)"""
        result = FileManager._get_cache_info_common_postfix("some_local_file.png", postfix="pfx", index=2)
        # Should still be just md5 hash, no postfix/index
        self.assertEqual(7, len(result))

    def test_get_cache_info_with_postfix_and_index(self) -> None:
        result = FileManager._get_cache_info_common_postfix("http://example.com/img.png", postfix="thumb", index=3)
        self.assertIn("_thumb", result)
        self.assertIn(".3", result)


class TestURLMethods(unittest.TestCase):
    """URL edge cases: lines 633, 645, 667, 701-705"""

    def test_get_url_scheme_no_scheme(self) -> None:
        result = URL.get_url_scheme("no-scheme-here")
        self.assertEqual("", result)

    def test_get_url_domain_no_slash(self) -> None:
        """Domain without trailing slash (line 644)"""
        result = URL.get_url_domain("http://example.com")
        self.assertEqual("example.com", result)

    def test_get_url_domain_no_scheme(self) -> None:
        """No scheme separator (line 645)"""
        result = URL.get_url_domain("just-a-string")
        # host_index = -1 + 3 = 2, so it finds domain from index 2
        # This is an edge case in the implementation
        self.assertIsInstance(result, str)

    def test_get_url_path_no_path(self) -> None:
        """URL without path after domain (line 652->656)"""
        result = URL.get_url_path("http://example.com")
        self.assertEqual("", result)

    def test_get_url_prefix_no_slash_after_host(self) -> None:
        """No slash after host (line 667)"""
        result = URL.get_url_prefix("http://example.com")
        self.assertEqual("", result)

    def test_encode_suffix(self) -> None:
        """URL.encode_suffix (lines 701-705)"""
        url = "http://example.com/path/to/resource"
        result = URL.encode_suffix(url)
        self.assertTrue(result.startswith("http://example.com/"))
        # The suffix part should be base64 encoded
        import base64

        encoded_part = result[len("http://example.com/") :]
        decoded = base64.b64decode(encoded_part).decode("utf-8")
        self.assertEqual("path/to/resource", decoded)


class TestHTMLExtractorGetNodeWithPath(unittest.TestCase):
    """HTMLExtractor.get_node_with_path: lines 275, 283, 294, 297, 322->324"""

    def _make_soup(self, html: str) -> Tag:
        soup = BeautifulSoup(html, "html.parser")
        return soup

    def test_get_node_with_path_none_node(self) -> None:
        """None node returns None (line 283)"""
        result = HTMLExtractor.get_node_with_path(None, "div")  # type: ignore
        self.assertIsNone(result)

    def test_get_node_with_path_by_id_not_found(self) -> None:
        """ID not found returns None (line 294)"""
        soup = self._make_soup("<div><p>hello</p></div>")
        result = HTMLExtractor.get_node_with_path(soup, '*[@id="nonexistent"]')
        self.assertIsNone(result)

    def test_get_node_with_path_by_id_multiple(self) -> None:
        """Multiple ID matches returns None (line 297)"""
        soup = self._make_soup('<div id="dup">a</div><div id="dup">b</div>')
        result = HTMLExtractor.get_node_with_path(soup, '*[@id="dup"]')
        self.assertIsNone(result)

    def test_get_first_token_no_match(self) -> None:
        """Invalid token returns None (line 275)"""
        result = HTMLExtractor.get_first_token_from_path("///???")
        self.assertEqual((None, None, None, None, False), result)

    def test_get_node_with_path_recursive(self) -> None:
        """Recursive path traversal (line 322->324)"""
        html = "<div><section><p>text</p></section></div>"
        soup = self._make_soup(html)
        result = HTMLExtractor.get_node_with_path(soup, "div/section/p")
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)  # type: ignore


class TestIOReadStdinAsLineList(unittest.TestCase):
    """IO.read_stdin_as_line_list: line 359"""

    def test_read_stdin_as_line_list(self) -> None:
        mock_stdin = io.StringIO("line1\nline2\nline3\n")
        with patch.object(sys, "stdin", mock_stdin):
            result = IO.read_stdin_as_line_list()
            self.assertEqual(["line1\n", "line2\n", "line3\n"], result)

    def test_read_stdin_as_line_list_empty(self) -> None:
        mock_stdin = io.StringIO("")
        with patch.object(sys, "stdin", mock_stdin):
            result = IO.read_stdin_as_line_list()
            self.assertEqual([], result)


class TestURLSafetyCheckUrl(unittest.TestCase):
    """URLSafety.check_url: lines 399-400, 407, 414, 438-439, 441"""

    def test_invalid_url_scheme(self) -> None:
        ok, msg = URLSafety.check_url("ftp://example.com", allow_private=False)
        self.assertFalse(ok)
        self.assertIn("Blocked URL scheme", msg)

    def test_no_scheme(self) -> None:
        ok, msg = URLSafety.check_url("://example.com", allow_private=False)
        self.assertFalse(ok)
        self.assertIn("Blocked URL scheme", msg)

    def test_missing_host(self) -> None:
        ok, msg = URLSafety.check_url("http://", allow_private=False)
        self.assertFalse(ok)
        self.assertIn("Missing host", msg)

    def test_localhost_blocked(self) -> None:
        ok, msg = URLSafety.check_url("http://localhost/path", allow_private=False)
        self.assertFalse(ok)
        self.assertIn("localhost", msg)

    def test_private_ip_blocked(self) -> None:
        ok, msg = URLSafety.check_url("http://192.168.1.1/path", allow_private=False)
        self.assertFalse(ok)
        self.assertIn("Blocked IP", msg)

    def test_private_ip_allowed(self) -> None:
        ok, msg = URLSafety.check_url("http://192.168.1.1/path", allow_private=True)
        self.assertTrue(ok)
        self.assertEqual("", msg)

    def test_allowed_host_exact(self) -> None:
        ok, msg = URLSafety.check_url("http://trusted.com/path", allow_private=False, allowed_hosts_raw="trusted.com")
        self.assertTrue(ok)
        self.assertEqual("", msg)

    def test_allowed_host_suffix(self) -> None:
        ok, msg = URLSafety.check_url("http://sub.trusted.com/path", allow_private=False, allowed_hosts_raw=".trusted.com")
        self.assertTrue(ok)

    def test_global_ip_allowed(self) -> None:
        ok, msg = URLSafety.check_url("http://8.8.8.8/path", allow_private=False)
        self.assertTrue(ok)

    def test_dns_resolution_failure(self) -> None:
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("DNS failed")):
            ok, msg = URLSafety.check_url("http://nonexistent-host-xyz.invalid/path", allow_private=False)
            self.assertFalse(ok)
            self.assertIn("DNS resolution failed", msg)

    def test_invalid_resolved_ip(self) -> None:
        """Invalid IP from DNS resolution (line 438-439)"""
        with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("not_an_ip", 80))]):
            ok, msg = URLSafety.check_url("http://example-test.com/path", allow_private=False)
            self.assertFalse(ok)
            self.assertIn("Invalid resolved IP", msg)

    def test_resolved_private_ip_blocked(self) -> None:
        """Resolved IP is private (line 441)"""
        with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 80))]):
            ok, msg = URLSafety.check_url("http://example-test.com/path", allow_private=False)
            self.assertFalse(ok)
            self.assertIn("Blocked IP", msg)

    def test_url_parse_exception(self) -> None:
        """urlparse raises exception (line 399-400)"""
        with patch("bin.feed_maker_util.urlparse", side_effect=ValueError("bad url")):
            ok, msg = URLSafety.check_url("http://example.com", allow_private=False)
            self.assertFalse(ok)
            self.assertIn("Invalid URL", msg)

    def test_parse_allowed_hosts_empty(self) -> None:
        exact, suffixes = URLSafety._parse_allowed_hosts("")
        self.assertEqual(set(), exact)
        self.assertEqual(set(), suffixes)

    def test_parse_allowed_hosts_with_empty_tokens(self) -> None:
        """Empty tokens in comma-separated list (line 375)"""
        exact, suffixes = URLSafety._parse_allowed_hosts("host1,,host2,")
        self.assertEqual({"host1", "host2"}, exact)


class TestFileManagerRemoveHtmlFilesWithoutCachedImageFiles(unittest.TestCase):
    """FileManager.remove_html_files_without_cached_image_files: lines 786->exit, 788->787, 790->787"""

    def test_nonexistent_html_dir(self) -> None:
        """html dir doesn't exist - should not raise"""
        tmp_dir = Path(__file__).parent / "_tmp_html_test"
        tmp_dir.mkdir(exist_ok=True)
        conf_path = tmp_dir / Config.DEFAULT_CONF_FILE
        try:
            with conf_path.open("w", encoding="utf-8") as f:
                json.dump({"configuration": {"extraction": {"element_id_list": [], "element_class_list": [], "element_path_list": [], "post_process_script_list": [], "headers": {}, "threshold_to_remove_html_with_incomplete_image": 0}}}, f)
            # No html directory exists, should return without error
            FileManager.remove_html_files_without_cached_image_files(tmp_dir, tmp_dir / "img")
        finally:
            conf_path.unlink(missing_ok=True)
            tmp_dir.rmdir()


class TestCustomExceptions(unittest.TestCase):
    """Custom exception constructors: lines 453, 469 etc."""

    def test_not_found_config_file_error(self) -> None:
        e = NotFoundConfigFileError("test message")
        self.assertEqual("test message", str(e))

    def test_invalid_config_file_error(self) -> None:
        e = InvalidConfigFileError("test message")
        self.assertEqual("test message", str(e))

    def test_not_found_config_item_error(self) -> None:
        e = NotFoundConfigItemError("test message")
        self.assertEqual("test message", str(e))

    def test_not_found_env_error(self) -> None:
        e = NotFoundEnvError("test message")
        self.assertEqual("test message", str(e))


# --- Merged from test_url_safety.py ---


class URLSafetyTest(unittest.TestCase):
    def test_block_non_http_schemes(self) -> None:
        ok, _ = URLSafety.check_url("file:///etc/passwd", allow_private=False)
        self.assertFalse(ok)

    def test_block_localhost_ip(self) -> None:
        ok, _ = URLSafety.check_url("http://127.0.0.1/", allow_private=False)
        self.assertFalse(ok)

    def test_block_link_local_metadata(self) -> None:
        ok, _ = URLSafety.check_url("http://169.254.169.254/latest/meta-data/", allow_private=False)
        self.assertFalse(ok)

    def test_block_ipv6_loopback(self) -> None:
        ok, _ = URLSafety.check_url("http://[::1]/", allow_private=False)
        self.assertFalse(ok)

    def test_allow_public_ip(self) -> None:
        ok, _ = URLSafety.check_url("http://93.184.216.34/", allow_private=False)
        self.assertTrue(ok)

    def test_allow_private_when_flagged(self) -> None:
        ok, _ = URLSafety.check_url("http://127.0.0.1/", allow_private=True)
        self.assertTrue(ok)

    def test_allowlist_bypass(self) -> None:
        ok, _ = URLSafety.check_url("http://localhost/", allow_private=False, allowed_hosts_raw="localhost")
        self.assertTrue(ok)

    def test_allowlist_suffix(self) -> None:
        ok, _ = URLSafety.check_url("https://sub.example.com/path", allow_private=False, allowed_hosts_raw=".example.com")
        self.assertTrue(ok)

    def test_block_when_dns_resolution_fails(self) -> None:
        ok, _ = URLSafety.check_url("http://nonexistent.invalid/", allow_private=False)
        self.assertFalse(ok)


class TestResolveExecutable(unittest.TestCase):
    """Process._resolve_executable: relative path not found → covers L108"""

    def test_relative_path_not_found(self) -> None:
        result = Process._resolve_executable("./nonexistent_script.py", Path("/tmp"))
        self.assertIsNone(result)

    def test_relative_path_parent_not_found(self) -> None:
        result = Process._resolve_executable("../nonexistent_script.py", Path("/tmp"))
        self.assertIsNone(result)


class TestDatetimeConvertToStr(unittest.TestCase):
    """Datetime.convert_datetime_to_str with string input → covers L233-235"""

    def test_string_input_returned_as_is(self) -> None:
        from bin.feed_maker_util import Datetime

        result = Datetime.convert_datetime_to_str("2024-01-01 00:00:00")
        self.assertEqual(result, "2024-01-01 00:00:00")

    def test_none_input(self) -> None:
        from bin.feed_maker_util import Datetime

        result = Datetime.convert_datetime_to_str(None)
        self.assertIsNone(result)


class TestConfigWithEnvVar(unittest.TestCase):
    """Config __init__ with FM_CONF_FILE env var → covers L468-469"""

    def test_fm_conf_file_env(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"configuration": {"collection": {}}}, f)
            f.flush()
            with patch.dict(os.environ, {"FM_CONF_FILE": f.name}):
                config = Config()
                self.assertIn("collection", config.conf)
        os.unlink(f.name)


class TestURLGetDomainNoPath(unittest.TestCase):
    """URL.get_url_domain with no path → covers L644"""

    def test_domain_without_path(self) -> None:
        result = URL.get_url_domain("https://example.com")
        self.assertEqual(result, "example.com")


class TestURLConcatenateWithQuestionMark(unittest.TestCase):
    """URL.concatenate_url with url2 ending in '?' → covers L684"""

    def test_concatenate_with_question_mark(self) -> None:
        result = URL.concatenate_url("http://example.com/page", "?")
        self.assertIn("?", result)


class TestFileManagerGetIncompleteImageListEdgeCases(unittest.TestCase):
    """FileManager.get_incomplete_image_list: IMAGE_NOT_FOUND and UnicodeDecodeError → covers L757,767-769"""

    def test_image_not_found_in_html(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            feed_dir = Path(tmpdir) / "testfeed"
            feed_dir.mkdir()
            html_dir = feed_dir / "html"
            html_dir.mkdir()
            html_file = html_dir / "test.html"
            html_file.write_text(f'<img src="http://img/testfeed/{FileManager.IMAGE_NOT_FOUND_IMAGE}"/>\n')
            result = FileManager.get_incomplete_image_list(html_file)
            self.assertIn(FileManager.IMAGE_NOT_FOUND_IMAGE, result)

    def test_unicode_decode_error(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            feed_dir = Path(tmpdir) / "testfeed"
            feed_dir.mkdir()
            html_dir = feed_dir / "html"
            html_dir.mkdir()
            html_file = html_dir / "test.html"
            html_file.write_bytes(b"\xff\xfe invalid utf-8 \x80\x81")
            with self.assertRaises(UnicodeDecodeError):
                FileManager.get_incomplete_image_list(html_file)


if __name__ == "__main__":
    unittest.main()
