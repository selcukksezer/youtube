import pytest
from fastapi.testclient import TestClient

import server
from services import dubbing


@pytest.fixture
def client():
    return TestClient(server.app)


def test_apply_dubbing_to_plan_preserves_scene_data_and_rebuilds_narration(monkeypatch):
    monkeypatch.setattr(
        dubbing,
        "translate_text",
        lambda text, source_lang="tr", target_lang="en", strict=False: f"Translated {text}",
    )
    plan = {
        "language": "tr",
        "title": "Kaynak başlık",
        "full_narration": "Eski anlatım",
        "scenes": [
            {
                "narration": "İlk sahne",
                "duration": 3.2,
                "scene_description": "A lighthouse at night",
                "search_queries": ["lighthouse"],
            }
        ],
    }

    translated = dubbing.apply_dubbing_to_plan(plan, target_lang="en", strict=True)

    assert translated["language"] == "en"
    assert translated["title"] == "Translated Kaynak başlık"
    assert translated["full_narration"] == "Translated İlk sahne"
    assert translated["scenes"][0]["narration"] == "Translated İlk sahne"
    assert translated["scenes"][0]["narration_source"] == "İlk sahne"
    assert translated["scenes"][0]["narration_source_lang"] == "tr"
    assert translated["scenes"][0]["duration"] == 3.2
    assert translated["scenes"][0]["scene_description"] == "A lighthouse at night"
    assert plan["scenes"][0]["narration"] == "İlk sahne"


def test_strict_translation_fails_instead_of_using_glossary_fallback(monkeypatch):
    import config

    monkeypatch.setattr(config, "GEMINI_API_KEY", "")

    with pytest.raises(dubbing.DubbingTranslationError, match="API anahtarı"):
        dubbing.translate_text("gizli gerçek burada", strict=True)


def test_script_translation_route_uses_strict_translation_and_returns_plan(client, monkeypatch):
    expected_plan = {"language": "en", "scenes": [{"narration": "A translated line"}]}
    calls = []

    def fake_apply(plan, target_lang, strict):
        calls.append((plan, target_lang, strict))
        return expected_plan

    monkeypatch.setattr(dubbing, "apply_dubbing_to_plan", fake_apply)
    source_plan = {
        "language": "tr",
        "title": "Başlık",
        "scenes": [{"narration": "Türkçe anlatım", "duration": 4}],
    }

    response = client.post(
        "/api/script/translate",
        json={"plan": source_plan, "target_lang": "en"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "plan": expected_plan}
    assert calls == [(source_plan, "en", True)]


@pytest.mark.parametrize(
    ("plan", "target_lang", "message"),
    [
        ({"language": "tr", "scenes": [{"narration": "Türkçe"}]}, "tr", "zaten"),
        ({"language": "tr", "scenes": []}, "en", "sahneli"),
        ({"language": "fr", "scenes": [{"narration": "Bonjour"}]}, "en", "kaynak dili"),
    ],
)
def test_script_translation_route_rejects_invalid_translation_requests(
    client, plan, target_lang, message
):
    response = client.post(
        "/api/script/translate",
        json={"plan": plan, "target_lang": target_lang},
    )

    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_script_translation_route_surfaces_provider_failure(client, monkeypatch):
    def fail_translation(*args, **kwargs):
        raise dubbing.DubbingTranslationError("Gemini API anahtarı yapılandırılmamış.")

    monkeypatch.setattr(dubbing, "apply_dubbing_to_plan", fail_translation)
    response = client.post(
        "/api/script/translate",
        json={
            "plan": {"language": "tr", "scenes": [{"narration": "Türkçe anlatım"}]},
            "target_lang": "en",
        },
    )

    assert response.status_code == 502
    assert "API anahtarı" in response.json()["detail"]
