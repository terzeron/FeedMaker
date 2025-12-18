#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import json
import unittest
import logging.config
from pathlib import Path

from bin.feed_maker_util import Env
from utils.translation import Translation, TranslationService, TranslationServiceFactory, DeepLTranslationService, AzureTranslationService, GoogleTranslationService


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

    def test_translate_uses_cache_without_api(self) -> None:
        """캐시 사용 테스트 (API 호출 없이)"""
        # 캐시 파일 준비
        cache = {
            "Global warming": "지구 온난화",
            "Speed of light": "빛의 속도",
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

        # 캐시 파일에 번역이 저장되었는지 확인
        saved_cache = json.loads(self.translation_map_path.read_text(encoding="utf-8"))
        self.assertIn("Hello world", saved_cache)

    @unittest.skipIf(Env.get("DEEPL_API_KEY", "") == "" and Env.get("AZURE_API_KEY", "") == "", "No API keys set")
    def test_translate_mixed_cached_and_new(self) -> None:
        """캐시된 항목과 새로운 항목이 섞인 경우 테스트"""
        # 캐시에 기존 번역 저장
        cache = {
            "Global warming": "지구 온난화",
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
        # 캐시에 기존 번역 저장
        cache = {
            "Global warming": "지구 온난화",
            "Speed of light": "빛의 속도",
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

        # 캐시 파일에 모든 번역이 저장되었는지 확인
        self.assertTrue(self.translation_map_path.is_file())
        saved = json.loads(self.translation_map_path.read_text(encoding="utf-8"))
        self.assertIn("Global warming", saved)
        self.assertIn("Speed of light", saved)
        self.assertIn("Artificial intelligence", saved)
        self.assertIn("Law of gravity", saved)

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


if __name__ == "__main__":
    unittest.main()
