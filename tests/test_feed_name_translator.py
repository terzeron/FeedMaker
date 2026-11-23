#!/usr/bin/env python
# -*- coding: utf-8 -*-

import types
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.feed_name_translator import FeedNameTranslator, MODEL, contains_hangul, extract_source_text, normalize_feed_name


def _text_response(text: str, stop_reason: str = "end_turn") -> types.SimpleNamespace:
    return types.SimpleNamespace(stop_reason=stop_reason, content=[types.SimpleNamespace(type="text", text=text)], _request_id="req_test")


class TestHelpers:
    def test_extract_source_text_uses_left_of_separator(self) -> None:
        assert extract_source_text(" 나 혼자만 레벨업 :: 네이버웹툰 ") == "나 혼자만 레벨업"

    def test_extract_source_text_without_separator(self) -> None:
        assert extract_source_text("나 혼자만 레벨업") == "나 혼자만 레벨업"

    def test_contains_hangul(self) -> None:
        assert contains_hangul("abc 한글")
        assert not contains_hangul("abc 123")

    def test_normalize_lowercases_joins_and_drops_articles(self) -> None:
        assert normalize_feed_name("The Boy Who Became a King!") == "boy_who_became_king"

    def test_normalize_keeps_numbers_and_collapses_separators(self) -> None:
        assert normalize_feed_name("  Level-Up  2  ") == "level_up_2"

    def test_normalize_drops_apostrophes_inside_words(self) -> None:
        assert normalize_feed_name("Omniscient Reader's Viewpoint") == "omniscient_readers_viewpoint"
        assert normalize_feed_name("Reader’s") == "readers"

    def test_normalize_keeps_articles_when_nothing_else_remains(self) -> None:
        assert normalize_feed_name("The") == "the"


class TestFeedNameTranslator:
    def test_requires_api_key(self) -> None:
        with pytest.raises(ValueError):
            FeedNameTranslator(api_key="")

    def test_translate_sends_left_text_and_normalizes(self) -> None:
        translator = FeedNameTranslator(api_key="test")
        translator.client = MagicMock()
        translator.client.messages.create.return_value = _text_response('{"english": "Only I Level Up"}')

        assert translator.translate("나 혼자만 레벨업::네이버웹툰") == "only_i_level_up"
        kwargs = translator.client.messages.create.call_args.kwargs
        assert kwargs["model"] == MODEL
        assert kwargs["messages"] == [{"role": "user", "content": "나 혼자만 레벨업"}]
        assert kwargs["output_config"]["format"]["type"] == "json_schema"

    def test_translate_returns_empty_on_unexpected_output(self) -> None:
        translator = FeedNameTranslator(api_key="test")
        translator.client = MagicMock()
        translator.client.messages.create.return_value = _text_response("not json")

        assert translator.translate("제목") == ""

    def test_translate_skips_api_without_hangul(self) -> None:
        translator = FeedNameTranslator(api_key="test")
        translator.client = MagicMock()

        assert translator.translate("One Piece::site") == ""
        translator.client.messages.create.assert_not_called()

    def test_translate_returns_empty_on_refusal(self) -> None:
        translator = FeedNameTranslator(api_key="test")
        translator.client = MagicMock()
        translator.client.messages.create.return_value = _text_response("", stop_reason="refusal")

        assert translator.translate("제목") == ""


class TestFeedNameSuggestionEndpoint:
    @pytest.fixture
    def client(self):
        from backend.main import app

        user = MagicMock()
        user.user_email = "test@example.com"
        with patch("backend.main.get_current_user", return_value=user), patch("backend.main.require_admin", return_value=user):
            yield TestClient(app, headers={"Origin": "https://fm.terzeron.com"})

    def test_success(self, client: TestClient) -> None:
        with patch("backend.main.FeedNameTranslator") as translator_cls:
            translator_cls.return_value.translate.return_value = "only_i_level_up"
            res = client.post("/feed_name_suggestion", json={"title": "나 혼자만 레벨업::네이버웹툰"})

        assert res.status_code == 200
        assert res.json() == {"status": "success", "feed_name": "only_i_level_up"}
        translator_cls.return_value.translate.assert_called_once_with("나 혼자만 레벨업::네이버웹툰")

    def test_failure_when_key_missing(self, client: TestClient) -> None:
        with patch("backend.main.FeedNameTranslator", side_effect=ValueError("ANTHROPIC_API_KEY is not set")):
            res = client.post("/feed_name_suggestion", json={"title": "제목"})

        assert res.status_code == 200
        assert res.json()["status"] == "failure"
        assert "ANTHROPIC_API_KEY" in res.json()["message"]

    def test_rejects_too_long_title(self, client: TestClient) -> None:
        res = client.post("/feed_name_suggestion", json={"title": "가" * 501})
        assert res.status_code == 422
