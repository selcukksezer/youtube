import json
import importlib
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import server
from services import subtitle_translation

research_router = importlib.import_module("routers.research_router")


def _response(payload):
    content = json.dumps(payload, ensure_ascii=False)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_translate_srt_preserves_indices_timestamps_and_multiline_cues(monkeypatch):
    calls = []

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            calls.append(kwargs)
            return _response([
                {"index": "1", "text": "Translated first\nline"},
                {"index": "2", "text": "Translated second"},
            ])

    def fake_openai(**kwargs):
        assert kwargs["api_key"] == "test-key"
        return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    monkeypatch.setattr(subtitle_translation, "OpenAI", fake_openai)
    source = (
        "1\n00:00:00,000 --> 00:00:01,200\nFirst\nline\n\n"
        "2\n00:00:01,200 --> 00:00:02,500\nSecond\n"
    )

    result = subtitle_translation.translate_srt(
        source,
        target_language="English",
        source_language="Turkish",
        api_key="test-key",
        base_url="https://llm.example/v1",
        model="test-model",
    )

    assert result == (
        "1\n00:00:00,000 --> 00:00:01,200\nTranslated first\nline\n\n"
        "2\n00:00:01,200 --> 00:00:02,500\nTranslated second\n"
    )
    assert len(calls) == 1
    assert calls[0]["model"] == "test-model"
    assert "Turkish" in calls[0]["messages"][1]["content"]


def test_translate_srt_batches_large_transcripts_and_validates_each_batch(monkeypatch):
    calls = []

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            calls.append(kwargs)
            start = len(calls[:-1]) * 20 + 1
            payload = [
                {"index": str(index), "text": f"Translated {index}"}
                for index in range(start, min(start + 20, 24))
            ]
            return _response(payload)

    def fake_openai(**kwargs):
        assert kwargs["api_key"] == "test-key"
        return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    monkeypatch.setattr(subtitle_translation, "OpenAI", fake_openai)
    source = "\n\n".join(
        f"{index}\n00:00:{index:02},000 --> 00:00:{index:02},500\nCue {index}"
        for index in range(1, 24)
    )

    result = subtitle_translation.translate_srt(
        source,
        target_language="English",
        api_key="test-key",
        base_url="",
        model="test-model",
    )

    assert len(calls) == 2
    assert "23\n00:00:23,000 --> 00:00:23,500\nTranslated 23" in result


@pytest.mark.parametrize(
    "srt_text",
    [
        "",
        "not an SRT cue",
        "1\n00:00:00,000 --> broken\nText",
    ],
)
def test_translate_srt_rejects_invalid_srt(srt_text):
    with pytest.raises(subtitle_translation.SubtitleTranslationError):
        subtitle_translation.translate_srt(
            srt_text,
            target_language="English",
            api_key="test-key",
            base_url="",
            model="test-model",
        )


def test_translate_srt_rejects_missing_or_duplicate_translation_indices(monkeypatch):
    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            assert kwargs["model"] == "test-model"
            return _response([{"index": "1", "text": "Only one"}])

    def fake_openai(**kwargs):
        assert kwargs["api_key"] == "test-key"
        return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    monkeypatch.setattr(subtitle_translation, "OpenAI", fake_openai)
    with pytest.raises(subtitle_translation.SubtitleTranslationError, match="atladı"):
        subtitle_translation.translate_srt(
            "1\n00:00:00,000 --> 00:00:01,000\nFirst\n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nSecond",
            target_language="English",
            api_key="test-key",
            base_url="",
            model="test-model",
        )


def test_translate_srt_rejects_duplicate_srt_indices():
    with pytest.raises(subtitle_translation.SubtitleTranslationError, match="benzersiz"):
        subtitle_translation.translate_srt(
            "1\n00:00:00,000 --> 00:00:01,000\nFirst\n\n"
            "1\n00:00:01,000 --> 00:00:02,000\nSecond",
            target_language="English",
            api_key="test-key",
            base_url="",
            model="test-model",
        )


def test_subtitle_translation_route_returns_preserved_srt(monkeypatch):
    monkeypatch.setattr(
        research_router.config, "AI_API_KEY", "test-key"
    )
    monkeypatch.setattr(
        research_router.config, "AI_BASE_URL", "https://llm.example/v1"
    )
    monkeypatch.setattr(research_router.config, "AI_MODEL", "test-model")

    def fake_translate(srt_text, **kwargs):
        assert srt_text.startswith("1\n")
        assert kwargs["target_language"] == "English"
        return "1\n00:00:00,000 --> 00:00:01,000\nTranslated\n"

    monkeypatch.setattr(
        "services.subtitle_translation.translate_srt",
        fake_translate,
    )

    response = TestClient(server.app).post(
        "/api/subtitles/translate",
        json={
            "srt_text": "1\n00:00:00,000 --> 00:00:01,000\nHello",
            "target_language": "English",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["target_language"] == "English"
    assert "00:00:00,000 --> 00:00:01,000" in payload["srt_text"]


def test_subtitle_translation_route_maps_invalid_srt_to_422():
    response = TestClient(server.app).post(
        "/api/subtitles/translate",
        json={"srt_text": "invalid", "target_language": "English"},
    )
    assert response.status_code == 422
