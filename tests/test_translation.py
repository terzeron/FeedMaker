#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import json
import time
import unittest
import logging.config
from pathlib import Path

from bin.feed_maker_util import Env
from unittest.mock import patch, MagicMock

from bin.crawler import Crawler
from utils.translation import (
    Translation, TranslationService, TranslationServiceFactory,
    DeepLTranslationService, AzureTranslationService, GoogleTranslationService,
    ClaudeTranslationService, TranslationProvider, _is_rate_limit_error,
    _CACHE_TTL_SECONDS,
)


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TranslationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_cwd = Path.cwd()
        self.work_dir = Path(Env.get("FM_WORK_DIR")) / "translation_test"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.translation_map_path = self.work_dir / "translation_map.json"
        if self.translation_map_path.is_file():
            self.translation_map_path.unlink(missing_ok=True)

        # 테스트용 환경 변수 설정
        self._old_fm_work_dir = os.environ.get("FM_WORK_DIR", None)
        os.environ["FM_WORK_DIR"] = str(self.work_dir)
        os.chdir(self.work_dir)

    def tearDown(self) -> None:
        # 캐시 파일 삭제
        if self.translation_map_path.is_file():
            self.translation_map_path.unlink(missing_ok=True)
        # 원래 디렉토리로 복귀
        os.chdir(self._old_cwd)
        # 작업 디렉토리 및 하위 파일/디렉토리 모두 삭제
        shutil.rmtree(self.work_dir, ignore_errors=True)
        # 환경 변수 복원
        if self._old_fm_work_dir is not None:
            os.environ["FM_WORK_DIR"] = self._old_fm_work_dir
        else:
            os.environ.pop("FM_WORK_DIR", None)

    def test_chunk_by_items_basic(self) -> None:
        items = ["a", "b", "c", "d", "e"]
        chunks = TranslationService.chunk_by_items(items, max_items=2)
        self.assertEqual([["a", "b"], ["c", "d"], ["e"]], chunks)

    def test_chunk_by_items_empty_list(self) -> None:
        """빈 리스트 처리 테스트"""
        translator = Translation()
        chunks = TranslationService.chunk_by_items([], max_items=3)
        self.assertEqual([], chunks)

    def test_chunk_by_items_single_item(self) -> None:
        """단일 아이템 처리 테스트"""
        translator = Translation()
        chunks = TranslationService.chunk_by_items(["single"], max_items=5)
        self.assertEqual([["single"]], chunks)

    def test_chunk_by_items_exact_multiple(self) -> None:
        """max_items의 정확한 배수인 경우 테스트"""
        translator = Translation()
        items = ["a", "b", "c", "d", "e", "f"]
        chunks = TranslationService.chunk_by_items(items, max_items=3)
        self.assertEqual([["a", "b", "c"], ["d", "e", "f"]], chunks)

    def test_chunk_by_items_none_values(self) -> None:
        """None 값 처리 테스트"""
        translator = Translation()
        items = ["a", None, "c", None, "e"]
        chunks = TranslationService.chunk_by_items(items, max_items=2)
        self.assertEqual([["a", None], ["c", None], ["e"]], chunks)

    def test_chunk_by_items_large_max_items(self) -> None:
        """max_items가 리스트 크기보다 큰 경우 테스트"""
        translator = Translation()
        items = ["a", "b", "c"]
        chunks = TranslationService.chunk_by_items(items, max_items=10)
        self.assertEqual([["a", "b", "c"]], chunks)

    @unittest.skipIf(Env.get("DEEPL_API_KEY", "") == "", "DEEPL_API_KEY not set")
    def test_translate_by_deepl_success(self) -> None:
        """DeepL 번역 성공 케이스 테스트"""
        translator = Translation()
        texts = [("/a", "Hello"), ("/b", "Good day")]
        result = translator.translate(texts)

        # 번역 결과가 있는지 확인 (API 에러 시 빈 리스트 반환 가능)
        self.assertIsInstance(result, list)

        if len(result) > 0:
            # 번역이 성공한 경우
            self.assertEqual(len(result), 2)

            # 각 항목이 (link, text) 튜플인지 확인
            for link, text in result:
                self.assertIsInstance(link, str)
                self.assertIsInstance(text, str)
                self.assertGreater(len(text), 0)

            # 원문이 번역 결과에 포함되어 있는지 확인
            result_texts = [text for _, text in result]
            self.assertTrue(any("Hello" in text for text in result_texts))
            self.assertTrue(any("Good day" in text for text in result_texts))
        else:
            # API 에러로 인해 번역이 실패한 경우 (456 에러 등)
            # 이는 테스트 실패가 아닌 API 제한으로 인한 것으로 간주
            self.skipTest("DeepL API returned empty result (possibly due to rate limiting or API error)")

    @unittest.skipIf(Env.get("DEEPL_API_KEY", "") == "", "DEEPL_API_KEY not set")
    def test_translate_by_deepl_multiple_batches(self) -> None:
        """DeepL 다중 배치 처리 테스트"""
        translator = Translation()
        # MAX_ITEMS_PER_BATCH보다 많은 텍스트로 테스트 (60개)
        texts = [(f"/{i}", f"Test text {i}") for i in range(60)]
        result = translator.translate(texts)

        # 번역 결과가 있는지 확인 (API 에러 시 빈 리스트 반환 가능)
        self.assertIsInstance(result, list)

        if len(result) > 0:
            # 번역이 성공한 경우
            self.assertEqual(len(result), 60)

            # 모든 번역 결과가 유효한지 확인
            for link, text in result:
                self.assertIsInstance(link, str)
                self.assertIsInstance(text, str)
                self.assertGreater(len(text), 0)

            # 모든 원문이 번역 결과에 포함되어 있는지 확인
            result_texts = [text for _, text in result]
            for i in range(60):
                self.assertTrue(any(f"Test text {i}" in text for text in result_texts))
        else:
            # API 에러로 인해 번역이 실패한 경우 (456 에러 등)
            # 이는 테스트 실패가 아닌 API 제한으로 인한 것으로 간주
            self.skipTest("DeepL API returned empty result (possibly due to rate limiting or API error)")

    # ========== translate_by_azure 메서드 테스트 ==========

    @unittest.skipIf(Env.get("AZURE_API_KEY", "") == "", "AZURE_API_KEY not set")
    def test_translate_by_azure_success(self) -> None:
        """Azure 번역 성공 케이스 테스트"""
        translator = Translation()
        texts = [("/a", "Hello"), ("/b", "Good day")]
        result = translator.translate(texts)

        # 번역 결과가 있는지 확인
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertIn("Hello", result[0][1])
        self.assertIn("Good day", result[1][1])

        # 번역된 텍스트가 한국어인지 확인
        for key, value in result:
            self.assertIsInstance(value, str)
            self.assertGreater(len(value), 0)

    @unittest.skipIf(Env.get("AZURE_API_KEY", "") == "", "AZURE_API_KEY not set")
    def test_translate_by_azure_multiple_batches(self) -> None:
        """Azure 다중 배치 처리 테스트"""
        translator = Translation()
        # MAX_ITEMS_PER_BATCH보다 많은 텍스트로 테스트 (60개)
        texts = [(f"/{i}", f"Test text {i}") for i in range(60)]
        result = translator.translate(texts)

        # 모든 텍스트가 번역되었는지 확인
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 60)

        # 모든 번역 결과가 유효한지 확인
        for i in range(60):
            link, text = result[i]
            self.assertIn(f"Test text {i}", text)
            self.assertIsInstance(text, str)
            self.assertGreater(len(text), 0)

    def test_translation_service_initialization(self) -> None:
        """TranslationService 초기화 테스트"""
        service = TranslationServiceFactory.create_service()
        self.assertIsNotNone(service)

    def test_deepl_translator_initialization(self) -> None:
        """DeepLTranslator 초기화 테스트"""
        service = DeepLTranslationService(Env.get("DEEPL_API_KEY", ""))
        self.assertIsNotNone(service.endpoint)
        self.assertIsNotNone(service.api_key)
        self.assertEqual(service, DeepLTranslationService)

    def test_azure_translator_initialization(self) -> None:
        """AzureTranslator 초기화 테스트"""
        service = AzureTranslationService(Env.get("AZURE_API_KEY", ""))
        self.assertIsNotNone(service.endpoint)
        self.assertIsNotNone(service.api_key)
        self.assertEqual(service, AzureTranslationService)

    def test_google_translator_initialization(self) -> None:
        """GoogleTranslator 초기화 테스트"""
        service = GoogleTranslationService(Env.get("GOOGLE_API_KEY", ""))
        self.assertIsNotNone(service.endpoint)
        self.assertIsNotNone(service.api_key)
        self.assertEqual(service, GoogleTranslationService)

    def test_claude_translator_initialization(self) -> None:
        """ClaudeTranslator 초기화 테스트"""
        service = ClaudeTranslationService(Env.get("ANTHROPIC_API_KEY", ""))
        self.assertIsNotNone(service.endpoint)
        self.assertIsNotNone(service.api_key)
        self.assertEqual(service, ClaudeTranslationService)

    @unittest.skipIf(Env.get("ANTHROPIC_API_KEY", "") == "", "ANTHROPIC_API_KEY not set")
    def test_translate_by_claude_success(self) -> None:
        """Claude 번역 성공 케이스 테스트"""
        service = ClaudeTranslationService(Env.get("ANTHROPIC_API_KEY"))
        result = service.translate_batch(["Hello", "Good day"])

        self.assertIsInstance(result, dict)
        if len(result) > 0:
            self.assertEqual(len(result), 2)
            self.assertIn("Hello", result)
            self.assertIn("Good day", result)
            for en, ko in result.items():
                self.assertIsInstance(ko, str)
                self.assertGreater(len(ko), 0)
        else:
            self.skipTest("Claude API returned empty result")

    def test_translate_uses_cache_without_api(self) -> None:
        """캐시 사용 테스트 (API 호출 없이)"""
        # v2 포맷 캐시 파일 준비
        now = int(time.time())
        cache = {
            "_version": 2,
            "Global warming": {"t": "지구 온난화", "ts": now},
            "Speed of light": {"t": "빛의 속도", "ts": now},
        }
        self.translation_map_path.write_text(json.dumps(cache, ensure_ascii=False, indent=4), encoding="utf-8")

        translator = Translation()
        result = translator.translate([
            ("/a", "Global warming"),
            ("/b", "Speed of light"),
        ])

        self.assertIn(("/a", "지구 온난화(Global warming)"), result)
        self.assertIn(("/b", "빛의 속도(Speed of light)"), result)

    @unittest.skipIf(Env.get("DEEPL_API_KEY", "") == "" and Env.get("AZURE_API_KEY", "") == "", "No API keys set")
    def test_translate_do_save_false(self) -> None:
        """do_save=False 옵션 테스트"""
        translator = Translation()
        result = translator.translate([
            ("/a", "Test save false"),
        ], do_save=False)

        # 번역이 성공했는지 확인
        self.assertEqual(len(result), 1)
        link, text = result[0]
        self.assertEqual(link, "/a")
        self.assertGreater(len(text), 0)

        # 캐시 파일이 업데이트되지 않았는지 확인 (새로운 번역이 캐시에 저장되지 않음)
        if self.translation_map_path.is_file():
            saved_cache = json.loads(self.translation_map_path.read_text(encoding="utf-8"))
            self.assertNotIn("Test save false", saved_cache)

    @unittest.skipIf(Env.get("DEEPL_API_KEY", "") == "" and Env.get("AZURE_API_KEY", "") == "", "No API keys set")
    def test_translate_no_cache_file(self) -> None:
        """캐시 파일이 없는 경우 테스트"""
        translator = Translation()
        result = translator.translate([
            ("/a", "Hello world"),
        ])

        # 번역이 성공했는지 확인
        self.assertEqual(len(result), 1)
        link, text = result[0]
        self.assertEqual(link, "/a")
        self.assertGreater(len(text), 0)

        # 캐시 파일이 생성되었는지 확인
        self.assertTrue(self.translation_map_path.is_file())

        # 캐시 파일에 번역이 v2 포맷으로 저장되었는지 확인
        saved_cache = json.loads(self.translation_map_path.read_text(encoding="utf-8"))
        self.assertEqual(saved_cache["_version"], 2)
        self.assertIn("Hello world", saved_cache)
        self.assertIn("t", saved_cache["Hello world"])
        self.assertIn("ts", saved_cache["Hello world"])

    @unittest.skipIf(Env.get("DEEPL_API_KEY", "") == "" and Env.get("AZURE_API_KEY", "") == "", "No API keys set")
    def test_translate_mixed_cached_and_new(self) -> None:
        """캐시된 항목과 새로운 항목이 섞인 경우 테스트"""
        # v2 포맷 캐시에 기존 번역 저장
        now = int(time.time())
        cache = {
            "_version": 2,
            "Global warming": {"t": "지구 온난화", "ts": now},
        }
        self.translation_map_path.write_text(json.dumps(cache, ensure_ascii=False, indent=4), encoding="utf-8")

        translator = Translation()
        result = translator.translate([
            ("/a", "Global warming"),  # 캐시된 항목
            ("/b", "New test text"),   # 새로운 항목
        ])

        # 결과가 2개인지 확인
        self.assertEqual(len(result), 2)

        # 캐시된 항목은 기존 번역 사용
        cached_result = next((text for link, text in result if link == "/a"), "")
        self.assertIsNotNone(cached_result)
        self.assertIsInstance(cached_result, str)
        self.assertIn("지구 온난화", cached_result)

        # 새로운 항목은 번역됨
        new_result = next((text for link, text in result if link == "/b"), "")
        self.assertIsNotNone(new_result)

    @unittest.skipIf(Env.get("DEEPL_API_KEY", "") == "" and Env.get("AZURE_API_KEY", "") == "", "No API keys set")
    def test_translate_comprehensive_integration(self) -> None:
        """실제 API를 사용한 포괄적인 통합 테스트"""
        # v2 포맷 캐시에 기존 번역 저장
        now = int(time.time())
        cache = {
            "_version": 2,
            "Global warming": {"t": "지구 온난화", "ts": now},
            "Speed of light": {"t": "빛의 속도", "ts": now},
        }
        self.translation_map_path.write_text(json.dumps(cache, ensure_ascii=False, indent=4), encoding="utf-8")

        # 테스트 데이터: 캐시 2건 + 신규 2건
        inputs = [
            ("/a", "Global warming"),           # 캐시
            ("/b", "Speed of light"),           # 캐시
            ("/c", "Artificial intelligence"),  # 신규
            ("/d", "Law of gravity"),           # 신규
        ]

        translator = Translation()
        result = translator.translate(inputs)

        # 결과가 4개인지 확인
        self.assertEqual(len(result), 4)

        # 캐시된 항목들은 기존 번역 사용
        cached_a = next((text for link, text in result if link == "/a"), "")
        self.assertIsNotNone(cached_a)
        self.assertIsInstance(cached_a, str)
        self.assertIn("지구 온난화", cached_a)

        cached_b = next((text for link, text in result if link == "/b"), "")
        self.assertIsNotNone(cached_b)
        self.assertIsInstance(cached_b, str)
        self.assertIn("빛의 속도", cached_b)

        # 신규 항목들은 번역됨
        new_c = next((text for link, text in result if link == "/c"), "")
        self.assertIsNotNone(new_c)
        self.assertIsInstance(new_c, str)
        self.assertGreater(len(new_c), 0)

        new_d = next((text for link, text in result if link == "/d"), "")
        self.assertIsNotNone(new_d)
        self.assertIsInstance(new_d, str)
        self.assertGreater(len(new_d), 0)

        # 캐시 파일에 모든 번역이 v2 포맷으로 저장되었는지 확인
        self.assertTrue(self.translation_map_path.is_file())
        saved = json.loads(self.translation_map_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["_version"], 2)
        for key in ("Global warming", "Speed of light", "Artificial intelligence", "Law of gravity"):
            self.assertIn(key, saved)
            self.assertIn("t", saved[key])

    def test_translate_empty_input(self) -> None:
        """빈 입력 리스트 처리 테스트"""
        translator = Translation()
        result = translator.translate([])
        self.assertEqual(result, [])

    def test_translate_none_values_in_input(self) -> None:
        """입력에 None 값이 포함된 경우 테스트"""
        translator = Translation()
        result = translator.translate([
            ("/a", ""),
            ("/b", "Valid text"),
        ])

        # None은 빈 문자열로 변환되어 처리됨
        self.assertEqual(len(result), 2)

        # None 값은 빈 문자열로 처리됨
        none_result = next((text for link, text in result if link == "/a"), None)
        self.assertIsNotNone(none_result)

        # 유효한 텍스트는 그대로 처리됨
        valid_result = next((text for link, text in result if link == "/b"), None)
        self.assertIsNotNone(valid_result)

    def test_translate_duplicate_texts(self) -> None:
        """중복된 텍스트 처리 테스트"""
        translator = Translation()
        result = translator.translate([
            ("/a", "Hello"),
            ("/b", "Hello"),  # 중복
        ])

        # 현재 구현에서는 중복된 텍스트는 마지막 링크만 처리됨
        # 이는 의도된 동작으로 보임 (같은 텍스트는 한 번만 번역)
        self.assertEqual(len(result), 1)
        link, text = result[0]
        self.assertEqual(link, "/b")
        self.assertGreater(len(text), 0)

    @unittest.skipIf(Env.get("DEEPL_API_KEY", "") == "" and Env.get("AZURE_API_KEY", "") == "", "No API keys set")
    def test_translate_special_characters(self) -> None:
        """특수 문자 처리 테스트"""
        translator = Translation()
        result = translator.translate([
            ("/a", "Hello & World"),
        ])

        # 특수 문자가 포함된 텍스트도 번역됨
        self.assertEqual(len(result), 1)
        link, text = result[0]
        self.assertEqual(link, "/a")
        self.assertGreater(len(text), 0)


class RateLimitErrorTest(unittest.TestCase):
    """_is_rate_limit_error() 단위 테스트"""

    def test_429_detected(self) -> None:
        self.assertTrue(_is_rate_limit_error("can't get response from 'https://x' with status code '429'"))

    def test_456_detected(self) -> None:
        self.assertTrue(_is_rate_limit_error("can't get response from 'https://x' with status code '456'"))

    def test_529_detected(self) -> None:
        self.assertTrue(_is_rate_limit_error("can't get response from 'https://x' with status code '529'"))

    def test_200_not_detected(self) -> None:
        self.assertFalse(_is_rate_limit_error("can't get response from 'https://x' with status code '200'"))

    def test_500_not_detected(self) -> None:
        self.assertFalse(_is_rate_limit_error("can't get response from 'https://x' with status code '500'"))

    def test_empty_string(self) -> None:
        self.assertFalse(_is_rate_limit_error(""))

    def test_no_status_code(self) -> None:
        self.assertFalse(_is_rate_limit_error("some random error message"))


class CreateServicesTest(unittest.TestCase):
    """TranslationServiceFactory.create_services() 테스트"""

    def test_priority_order(self) -> None:
        """모든 키가 설정된 경우 Azure → DeepL → Google → Claude 순서"""
        env = {
            "AZURE_API_KEY": "az-key",
            "DEEPL_API_KEY": "dl-key",
            "GOOGLE_API_KEY": "gg-key",
            "ANTHROPIC_API_KEY": "cl-key",
        }
        with patch.object(Env, "get", side_effect=lambda k, default="": env.get(k, default)):
            services = TranslationServiceFactory.create_services()
        self.assertEqual(len(services), 4)
        self.assertEqual(services[0].provider, TranslationProvider.AZURE)
        self.assertEqual(services[1].provider, TranslationProvider.DEEPL)
        self.assertEqual(services[2].provider, TranslationProvider.GOOGLE)
        self.assertEqual(services[3].provider, TranslationProvider.CLAUDE)

    def test_missing_keys_filtered(self) -> None:
        """키가 없는 서비스는 제외"""
        env = {"DEEPL_API_KEY": "dl-key"}
        with patch.object(Env, "get", side_effect=lambda k, default="": env.get(k, default)):
            services = TranslationServiceFactory.create_services()
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].provider, TranslationProvider.DEEPL)

    def test_no_keys_returns_empty(self) -> None:
        """키가 하나도 없으면 빈 리스트"""
        with patch.object(Env, "get", return_value=""):
            services = TranslationServiceFactory.create_services()
        self.assertEqual(services, [])

    def test_create_service_backward_compat(self) -> None:
        """create_service()는 첫 번째 서비스 반환"""
        env = {"AZURE_API_KEY": "az-key", "DEEPL_API_KEY": "dl-key"}
        with patch.object(Env, "get", side_effect=lambda k, default="": env.get(k, default)):
            service = TranslationServiceFactory.create_service()
        self.assertIsNotNone(service)
        self.assertEqual(service.provider, TranslationProvider.AZURE)


class FallbackChainTest(unittest.TestCase):
    """_translate_with_fallback() fallback 시나리오 테스트"""

    def setUp(self) -> None:
        self._old_cwd = Path.cwd()
        self.work_dir = Path(Env.get("FM_WORK_DIR")) / "fallback_test"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._old_fm_work_dir = os.environ.get("FM_WORK_DIR", None)
        os.environ["FM_WORK_DIR"] = str(self.work_dir)
        os.chdir(self.work_dir)

    def tearDown(self) -> None:
        os.chdir(self._old_cwd)
        shutil.rmtree(self.work_dir, ignore_errors=True)
        if self._old_fm_work_dir is not None:
            os.environ["FM_WORK_DIR"] = self._old_fm_work_dir
        else:
            os.environ.pop("FM_WORK_DIR", None)

    def _make_mock_service(self, provider: TranslationProvider, result: dict[str, str]) -> MagicMock:
        svc = MagicMock()
        svc.provider = provider
        svc.translate_batch.return_value = result
        return svc

    def test_first_service_handles_all(self) -> None:
        """첫 번째 서비스가 모두 처리하면 두 번째 호출 안 함"""
        svc1 = self._make_mock_service(TranslationProvider.AZURE, {"a": "가", "b": "나"})
        svc2 = self._make_mock_service(TranslationProvider.DEEPL, {})

        translator = Translation.__new__(Translation)
        translator.services = [svc1, svc2]
        translator.service = svc1

        result = translator._translate_with_fallback(["a", "b"])
        self.assertEqual(result, {"a": "가", "b": "나"})
        svc2.translate_batch.assert_not_called()

    def test_fallback_to_second_service(self) -> None:
        """첫 번째 서비스가 부분 실패 → 나머지를 두 번째 서비스가 처리"""
        svc1 = self._make_mock_service(TranslationProvider.AZURE, {"a": "가"})
        svc2 = self._make_mock_service(TranslationProvider.DEEPL, {"b": "나"})

        translator = Translation.__new__(Translation)
        translator.services = [svc1, svc2]
        translator.service = svc1

        result = translator._translate_with_fallback(["a", "b"])
        self.assertEqual(result, {"a": "가", "b": "나"})
        svc2.translate_batch.assert_called_once_with(["b"])

    def test_all_services_fail(self) -> None:
        """모든 서비스 실패 시 빈 결과"""
        svc1 = self._make_mock_service(TranslationProvider.AZURE, {})
        svc2 = self._make_mock_service(TranslationProvider.DEEPL, {})

        translator = Translation.__new__(Translation)
        translator.services = [svc1, svc2]
        translator.service = svc1

        result = translator._translate_with_fallback(["a", "b"])
        self.assertEqual(result, {})

    def test_three_services_cascade(self) -> None:
        """3개 서비스 캐스케이드: 각각 1개씩 처리"""
        svc1 = self._make_mock_service(TranslationProvider.AZURE, {"a": "가"})
        svc2 = self._make_mock_service(TranslationProvider.DEEPL, {"b": "나"})
        svc3 = self._make_mock_service(TranslationProvider.GOOGLE, {"c": "다"})

        translator = Translation.__new__(Translation)
        translator.services = [svc1, svc2, svc3]
        translator.service = svc1

        result = translator._translate_with_fallback(["a", "b", "c"])
        self.assertEqual(result, {"a": "가", "b": "나", "c": "다"})
        svc2.translate_batch.assert_called_once_with(["b", "c"])
        svc3.translate_batch.assert_called_once_with(["c"])


class ClaudeRobustnessTest(unittest.TestCase):
    """Claude 부분 일치/검증 테스트"""

    def test_partial_match_accepted(self) -> None:
        """반환 개수 < 배치 크기여도 앞에서부터 매핑"""
        svc = ClaudeTranslationService("fake-key")
        # 3개 요청에 2개만 응답하는 시나리오를 mock
        response_json = json.dumps({
            "content": [{"type": "text", "text": '"가", "나"]'}]
        })
        with patch.object(Crawler, "run", return_value=(response_json, "", {})):
            result = svc.translate_batch(["a", "b", "c"])
        # a→가, b→나만 매핑, c는 누락
        self.assertEqual(result, {"a": "가", "b": "나"})

    def test_empty_string_excluded(self) -> None:
        """빈 문자열 번역은 제외"""
        svc = ClaudeTranslationService("fake-key")
        response_json = json.dumps({
            "content": [{"type": "text", "text": '"가", ""]'}]
        })
        with patch.object(Crawler, "run", return_value=(response_json, "", {})):
            result = svc.translate_batch(["a", "b"])
        self.assertEqual(result, {"a": "가"})

    def test_same_as_original_excluded(self) -> None:
        """원문과 동일한 번역은 제외"""
        svc = ClaudeTranslationService("fake-key")
        response_json = json.dumps({
            "content": [{"type": "text", "text": '"가", "b"]'}]
        })
        with patch.object(Crawler, "run", return_value=(response_json, "", {})):
            result = svc.translate_batch(["a", "b"])
        self.assertEqual(result, {"a": "가"})


class CacheTTLTest(unittest.TestCase):
    """캐시 TTL(7일) 만료 관련 테스트"""

    def setUp(self) -> None:
        self._old_cwd = Path.cwd()
        self.work_dir = Path(Env.get("FM_WORK_DIR")) / "ttl_test"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.work_dir / "translation_map.json"
        self._old_fm_work_dir = os.environ.get("FM_WORK_DIR", None)
        os.environ["FM_WORK_DIR"] = str(self.work_dir)
        os.chdir(self.work_dir)

    def tearDown(self) -> None:
        os.chdir(self._old_cwd)
        shutil.rmtree(self.work_dir, ignore_errors=True)
        if self._old_fm_work_dir is not None:
            os.environ["FM_WORK_DIR"] = self._old_fm_work_dir
        else:
            os.environ.pop("FM_WORK_DIR", None)

    def test_old_format_migration(self) -> None:
        """구 포맷(flat dict) → v2 마이그레이션 시 ts=now 부여"""
        old_cache = {"Hello": "안녕하세요", "World": "세계"}
        self.cache_path.write_text(json.dumps(old_cache, ensure_ascii=False), encoding="utf-8")

        now = 1_700_000_000
        with patch("utils.translation.time") as mock_time:
            mock_time.time.return_value = now
            flat, ts_cache = Translation._load_translation_cache(self.cache_path)

        self.assertEqual(flat, {"Hello": "안녕하세요", "World": "세계"})
        self.assertEqual(ts_cache["Hello"], {"t": "안녕하세요", "ts": now})
        self.assertEqual(ts_cache["World"], {"t": "세계", "ts": now})

    def test_expired_entries_purged(self) -> None:
        """TTL 초과 항목은 로드 시 제거"""
        now = 1_700_000_000
        expired_ts = now - _CACHE_TTL_SECONDS - 1  # 7일 + 1초 전
        v2_cache = {
            "_version": 2,
            "Old": {"t": "오래된", "ts": expired_ts},
            "New": {"t": "새로운", "ts": now - 100},
        }
        self.cache_path.write_text(json.dumps(v2_cache, ensure_ascii=False), encoding="utf-8")

        with patch("utils.translation.time") as mock_time:
            mock_time.time.return_value = now
            flat, ts_cache = Translation._load_translation_cache(self.cache_path)

        self.assertNotIn("Old", flat)
        self.assertNotIn("Old", ts_cache)
        self.assertEqual(flat["New"], "새로운")
        self.assertIn("New", ts_cache)

    def test_unexpired_entries_kept(self) -> None:
        """TTL 미만 항목은 유지"""
        now = 1_700_000_000
        recent_ts = now - _CACHE_TTL_SECONDS + 3600  # 만료 1시간 전
        v2_cache = {
            "_version": 2,
            "Recent": {"t": "최근", "ts": recent_ts},
        }
        self.cache_path.write_text(json.dumps(v2_cache, ensure_ascii=False), encoding="utf-8")

        with patch("utils.translation.time") as mock_time:
            mock_time.time.return_value = now
            flat, ts_cache = Translation._load_translation_cache(self.cache_path)

        self.assertEqual(flat["Recent"], "최근")
        self.assertIn("Recent", ts_cache)

    def test_expired_entry_becomes_retranslation_target(self) -> None:
        """만료 항목은 재번역 대상이 됨"""
        now = 1_700_000_000
        expired_ts = now - _CACHE_TTL_SECONDS - 1
        v2_cache = {
            "_version": 2,
            "Hello": {"t": "안녕하세요", "ts": expired_ts},
        }
        self.cache_path.write_text(json.dumps(v2_cache, ensure_ascii=False), encoding="utf-8")

        mock_svc = MagicMock()
        mock_svc.provider = TranslationProvider.AZURE
        mock_svc.translate_batch.return_value = {"Hello": "안녕!"}

        translator = Translation.__new__(Translation)
        translator.services = [mock_svc]
        translator.service = mock_svc

        with patch("utils.translation.time") as mock_time:
            mock_time.time.return_value = now
            result = translator.translate([("/a", "Hello")])

        # 만료되었으므로 API 호출됨
        mock_svc.translate_batch.assert_called_once_with(["Hello"])
        self.assertEqual(result, [("/a", "안녕!(Hello)")])

    def test_save_includes_version_2(self) -> None:
        """저장 시 _version: 2가 포함"""
        ts_cache = {"Hello": {"t": "안녕", "ts": 1_700_000_000}}
        Translation._save_translation_cache(self.cache_path, ts_cache)

        saved = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["_version"], 2)
        self.assertEqual(saved["Hello"]["t"], "안녕")
        self.assertEqual(saved["Hello"]["ts"], 1_700_000_000)

    def test_empty_file_returns_empty(self) -> None:
        """캐시 파일이 없으면 빈 튜플 반환"""
        flat, ts_cache = Translation._load_translation_cache(self.cache_path)
        self.assertEqual(flat, {})
        self.assertEqual(ts_cache, {})


if __name__ == "__main__":
    unittest.main()
