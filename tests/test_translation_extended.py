#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import shutil
import unittest
import logging.config
from pathlib import Path
from unittest.mock import patch, MagicMock

from bin.feed_maker_util import Env
from utils.translation import Translation, TranslationServiceFactory, DeepLTranslationService, AzureTranslationService, GoogleTranslationService, ClaudeTranslationService, TranslationProvider, translate_html, _CACHE_TTL_SECONDS

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestDeepLTranslationService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = DeepLTranslationService(api_key="fake-deepl-key")

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_success(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        response = json.dumps({"translations": [{"text": "안녕"}, {"text": "세계"}]})
        mock_client.run.return_value = (response, "", 200)

        result = self.svc.translate_batch(["hello", "world"])
        self.assertEqual(result, {"hello": "안녕", "world": "세계"})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_rate_limit_breaks(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        mock_client.run.return_value = ("", "status code '429'", 429)

        result = self.svc.translate_batch(["hello"])
        self.assertEqual(result, {})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_non_rate_limit_error_continues(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        # First call: non-unrecoverable error (500), second call: success
        response = json.dumps({"translations": [{"text": "세계"}]})
        mock_client.run.side_effect = [("", "status code '500'", 500), (response, "", 200)]

        result = self.svc.translate_batch(["hello", "world"])
        # With batch size 20, both go in one batch, so first call fails and continues
        # but since both texts are in one batch, only one call is made per batch
        # Actually chunk_by_items with max 20 puts both in one batch
        # So only one call, which fails, then continues to next batch (none)
        self.assertEqual(result, {})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_request_exception(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        mock_client.run.side_effect = Exception("connection error")

        result = self.svc.translate_batch(["hello"])
        self.assertEqual(result, {})


class TestAzureTranslationService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = AzureTranslationService(api_key="fake-azure-key")

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_success(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        response = json.dumps([{"translations": [{"text": "안녕"}]}, {"translations": [{"text": "세계"}]}])
        mock_client.run.return_value = (response, "", 200)

        result = self.svc.translate_batch(["hello", "world"])
        self.assertEqual(result, {"hello": "안녕", "world": "세계"})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_unrecoverable_error_breaks(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        mock_client.run.return_value = ("", "status code '403'", 403)

        result = self.svc.translate_batch(["hello"])
        self.assertEqual(result, {})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_request_exception(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        mock_client.run.side_effect = Exception("timeout")

        result = self.svc.translate_batch(["hello"])
        self.assertEqual(result, {})


class TestGoogleTranslationService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = GoogleTranslationService(api_key="fake-google-key")

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_success(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        response = json.dumps({"data": {"translations": [{"translatedText": "안녕"}, {"translatedText": "세계"}]}})
        mock_client.run.return_value = (response, "", 200)

        result = self.svc.translate_batch(["hello", "world"])
        self.assertEqual(result, {"hello": "안녕", "world": "세계"})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_error_empty_response(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        mock_client.run.return_value = ("", "status code '401'", 401)

        result = self.svc.translate_batch(["hello"])
        self.assertEqual(result, {})


class TestClaudeTranslationService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = ClaudeTranslationService(api_key="fake-claude-key")

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_success(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        response = json.dumps({"content": [{"type": "text", "text": '"안녕", "세계"]'}], "stop_reason": "end_turn"})
        mock_client.run.return_value = (response, "", 200)

        result = self.svc.translate_batch(["hello", "world"])
        self.assertEqual(result, {"hello": "안녕", "world": "세계"})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_type_error_response(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        response = json.dumps({"type": "error", "error": {"type": "overloaded_error", "message": "overloaded"}})
        mock_client.run.return_value = (response, "", 200)

        result = self.svc.translate_batch(["hello"])
        self.assertEqual(result, {})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_max_tokens_truncation_with_recovery(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        # Truncated JSON: missing closing bracket, but has a recoverable last comma
        response = json.dumps({"content": [{"type": "text", "text": '"안녕", "세계", "잘린텍'}], "stop_reason": "max_tokens"})
        mock_client.run.return_value = (response, "", 200)

        result = self.svc.translate_batch(["hello", "world", "truncated"])
        # Recovery should parse ["안녕", "세계"] (up to last complete item)
        self.assertEqual(result, {"hello": "안녕", "world": "세계"})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_empty_response(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        mock_client.run.return_value = ("", "status code '529'", 529)

        result = self.svc.translate_batch(["hello"])
        self.assertEqual(result, {})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_unexpected_format(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        # Returns a dict instead of list after prefill reconstruction
        response = json.dumps({"content": [{"type": "text", "text": '{"key": "value"}]'}], "stop_reason": "end_turn"})
        mock_client.run.return_value = (response, "", 200)

        result = self.svc.translate_batch(["hello"])
        # "[" + '{"key": "value"}]' => '[{"key": "value"}]' which is a list of dict, not list of str
        # isinstance check on items will filter out non-str items
        self.assertEqual(result, {})

    @patch("utils.translation.time.sleep")
    @patch("utils.translation.Crawler")
    def test_translate_batch_general_exception(self, mock_crawler_cls: MagicMock, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_crawler_cls.return_value = mock_client
        mock_client.run.side_effect = RuntimeError("unexpected")

        result = self.svc.translate_batch(["hello"])
        self.assertEqual(result, {})


class TestTranslationServiceFactory(unittest.TestCase):
    @patch("utils.translation.Env.get")
    def test_create_services_with_all_keys(self, mock_env_get: MagicMock) -> None:
        mock_env_get.side_effect = lambda k: {"AZURE_API_KEY": "azure-key", "DEEPL_API_KEY": "deepl-key", "GOOGLE_API_KEY": "google-key", "ANTHROPIC_API_KEY": "claude-key"}.get(k, "")

        services = TranslationServiceFactory.create_services()
        self.assertEqual(len(services), 4)
        self.assertIsInstance(services[0], AzureTranslationService)
        self.assertIsInstance(services[1], DeepLTranslationService)
        self.assertIsInstance(services[2], GoogleTranslationService)
        self.assertIsInstance(services[3], ClaudeTranslationService)

    @patch("utils.translation.Env.get")
    def test_create_services_with_no_keys(self, mock_env_get: MagicMock) -> None:
        mock_env_get.return_value = ""

        services = TranslationServiceFactory.create_services()
        self.assertEqual(len(services), 0)

    @patch("utils.translation.Env.get")
    def test_create_services_partial_keys(self, mock_env_get: MagicMock) -> None:
        mock_env_get.side_effect = lambda k: "deepl-key" if k == "DEEPL_API_KEY" else ""

        services = TranslationServiceFactory.create_services()
        self.assertEqual(len(services), 1)
        self.assertIsInstance(services[0], DeepLTranslationService)


class TestTranslationCacheLoadSave(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(Env.get("FM_WORK_DIR")) / "translation_ext_test"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.work_dir / "translation_map.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def test_load_nonexistent_file(self) -> None:
        flat, ts = Translation._load_translation_cache(self.cache_path)
        self.assertEqual(flat, {})
        self.assertEqual(ts, {})

    def test_load_v1_format_migration(self) -> None:
        v1_data = {"hello": "안녕", "world": "세계"}
        with self.cache_path.open("w", encoding="utf-8") as f:
            json.dump(v1_data, f)

        flat, ts = Translation._load_translation_cache(self.cache_path)
        self.assertEqual(flat, {"hello": "안녕", "world": "세계"})
        # ts should have timestamps
        self.assertIn("hello", ts)
        self.assertIn("ts", ts["hello"])
        self.assertEqual(ts["hello"]["t"], "안녕")

    def test_load_v2_format(self) -> None:
        now = int(time.time())
        v2_data = {"_version": 2, "hello": {"t": "안녕", "ts": now}, "world": {"t": "세계", "ts": now}}
        with self.cache_path.open("w", encoding="utf-8") as f:
            json.dump(v2_data, f)

        flat, ts = Translation._load_translation_cache(self.cache_path)
        self.assertEqual(flat, {"hello": "안녕", "world": "세계"})
        self.assertEqual(len(ts), 2)

    def test_load_v2_expired_entries_purged(self) -> None:
        old_ts = int(time.time()) - _CACHE_TTL_SECONDS - 100
        now = int(time.time())
        v2_data = {"_version": 2, "old_entry": {"t": "오래된", "ts": old_ts}, "new_entry": {"t": "새로운", "ts": now}}
        with self.cache_path.open("w", encoding="utf-8") as f:
            json.dump(v2_data, f)

        flat, ts = Translation._load_translation_cache(self.cache_path)
        self.assertNotIn("old_entry", flat)
        self.assertIn("new_entry", flat)

    def test_save_translation_cache(self) -> None:
        now = int(time.time())
        ts_cache = {"hello": {"t": "안녕", "ts": now}}
        Translation._save_translation_cache(self.cache_path, ts_cache)

        with self.cache_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["_version"], 2)
        self.assertEqual(data["hello"]["t"], "안녕")


class TestTranslateWithFallback(unittest.TestCase):
    @patch("utils.translation.TranslationServiceFactory.create_services")
    def test_single_service_success(self, mock_create: MagicMock) -> None:
        mock_svc = MagicMock()
        mock_svc.provider = TranslationProvider.DEEPL
        mock_svc.translate_batch.return_value = {"hello": "안녕"}
        mock_create.return_value = [mock_svc]

        translator = Translation.__new__(Translation)
        translator.services = [mock_svc]
        translator.service = mock_svc

        result = translator._translate_with_fallback(["hello"])
        self.assertEqual(result, {"hello": "안녕"})

    @patch("utils.translation.TranslationServiceFactory.create_services")
    def test_fallback_to_second_service(self, mock_create: MagicMock) -> None:
        mock_svc1 = MagicMock()
        mock_svc1.provider = TranslationProvider.DEEPL
        mock_svc1.translate_batch.return_value = {}  # fails

        mock_svc2 = MagicMock()
        mock_svc2.provider = TranslationProvider.GOOGLE
        mock_svc2.translate_batch.return_value = {"hello": "안녕"}

        mock_create.return_value = [mock_svc1, mock_svc2]

        translator = Translation.__new__(Translation)
        translator.services = [mock_svc1, mock_svc2]
        translator.service = mock_svc1

        result = translator._translate_with_fallback(["hello"])
        self.assertEqual(result, {"hello": "안녕"})
        mock_svc2.translate_batch.assert_called_once_with(["hello"])

    @patch("utils.translation.TranslationServiceFactory.create_services")
    def test_all_services_fail(self, mock_create: MagicMock) -> None:
        mock_svc1 = MagicMock()
        mock_svc1.provider = TranslationProvider.DEEPL
        mock_svc1.translate_batch.return_value = {}

        mock_svc2 = MagicMock()
        mock_svc2.provider = TranslationProvider.GOOGLE
        mock_svc2.translate_batch.return_value = {}

        mock_create.return_value = [mock_svc1, mock_svc2]

        translator = Translation.__new__(Translation)
        translator.services = [mock_svc1, mock_svc2]
        translator.service = mock_svc1

        result = translator._translate_with_fallback(["hello"])
        self.assertEqual(result, {})


class TestTranslateHtml(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(Env.get("FM_WORK_DIR")) / "translate_html_test"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.work_dir / "translation_map.json"
        self._old_env = os.environ.get("FM_WORK_DIR", None)
        os.environ["FM_WORK_DIR"] = str(self.work_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)
        if self._old_env is not None:
            os.environ["FM_WORK_DIR"] = self._old_env

    @patch("utils.translation.TranslationServiceFactory.create_services")
    def test_normal_html(self, mock_create: MagicMock) -> None:
        mock_svc = MagicMock()
        mock_svc.provider = TranslationProvider.DEEPL
        mock_svc.translate_batch.return_value = {"Hello": "안녕"}
        mock_create.return_value = [mock_svc]

        html = "<p>Hello</p>"
        result, untranslated = translate_html(html)
        self.assertIn("안녕", result)
        self.assertEqual(untranslated, 0)

    @patch("utils.translation.TranslationServiceFactory.create_services")
    def test_empty_text_nodes(self, mock_create: MagicMock) -> None:
        mock_create.return_value = []
        html = "<p>   </p><div>\n</div>"
        result, untranslated = translate_html(html)
        self.assertEqual(untranslated, 0)

    @patch("utils.translation.TranslationServiceFactory.create_services")
    def test_skip_tags(self, mock_create: MagicMock) -> None:
        mock_svc = MagicMock()
        mock_svc.provider = TranslationProvider.DEEPL
        mock_svc.translate_batch.return_value = {"Visible": "보이는"}
        mock_create.return_value = [mock_svc]

        html = "<p>Visible</p><script>var x = 1;</script><style>body{}</style><code>code</code>"
        result, untranslated = translate_html(html)
        # script/style/code content should not be translated
        mock_svc.translate_batch.assert_called_once()
        call_args = mock_svc.translate_batch.call_args[0][0]
        self.assertIn("Visible", call_args)
        self.assertNotIn("var x = 1;", call_args)
        self.assertNotIn("body{}", call_args)
        self.assertNotIn("code", call_args)


if __name__ == "__main__":
    unittest.main()
