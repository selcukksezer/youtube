import importlib

import pytest
from fastapi.testclient import TestClient

import server
from services import manuscript_script
from services import timed_visual_matcher

media_router = importlib.import_module("routers.media_router")


@pytest.fixture
def client():
    return TestClient(server.app)


def test_split_manuscript_preserves_all_text_and_uses_reading_duration():
    text = (
        "İlk bölümde izleyiciye önemli bir soru soruyoruz. "
        "Ardından olayın arka planını kısa ve anlaşılır biçimde açıklıyoruz. "
        "Son sahnede beklenmedik sonucu anlatıp izleyiciyi düşünmeye davet ediyoruz."
    )

    segments = manuscript_script.split_manuscript_text(text)

    assert len(segments) == 2
    assert " ".join(segments) == text
    assert all(segment.endswith((".", "!", "?")) for segment in segments)
    assert all(
        len(segment.split()) / 2.45 <= 8.0
        for segment in segments
    )


def test_split_manuscript_keeps_long_sentence_intact():
    long_sentence = " ".join(["kelime"] * 25) + "."

    assert manuscript_script.split_manuscript_text(long_sentence) == [long_sentence]


def test_split_manuscript_rejects_more_than_24_scene_segments():
    text = " ".join(
        (
            f"Bu sahne numara {index} için detaylı anlatım metnidir ve izleyiciye olayın "
            "arka planını anlaması için gereken bütün önemli ayrıntıları açıkça anlatır."
        )
        for index in range(25)
    )

    with pytest.raises(manuscript_script.ManuscriptSegmentationError, match="24 scenes"):
        manuscript_script.split_manuscript_text(text)


def test_build_manuscript_plan_preserves_source_narration():
    source = "İlk cümle metni anlatır. İkinci cümle sonucu açıklar."

    plan = manuscript_script.build_manuscript_plan(
        source,
        language="tr",
        niche_id="13_mystery",
    )

    assert plan["title"] == "İlk cümle metni anlatır."
    assert plan["full_narration"] == source
    assert plan["language"] == "tr"
    assert plan["niche_id"] == "13_mystery"
    assert plan["scenes"][0]["narration"] in source
    assert plan["scenes"][0]["duration"] > 0


def test_manuscript_route_builds_local_visuals_and_stock_candidates(
    client, monkeypatch
):
    matcher_calls = []
    stock_calls = []

    def fake_match(scenes, niche_id, force_local):
        matcher_calls.append((niche_id, force_local))
        for scene in scenes:
            scene["search_queries"] = ["ancient stone bridge"]
        return scenes

    def fake_stock(scenes, niche_id):
        stock_calls.append(niche_id)
        scenes[0]["selected_video"] = {"url": "https://stock.example/video.mp4"}
        return scenes

    monkeypatch.setattr(
        timed_visual_matcher,
        "generate_timed_visual_queries",
        fake_match,
    )
    monkeypatch.setattr(media_router, "auto_fetch_videos_for_scenes", fake_stock)
    source = (
        "Eski bir taş köprü, vadinin iki yakasını birbirine bağlıyordu. "
        "Her gün yüzlerce kişi bu köprüden geçiyor ve hayatına devam ediyordu."
    )

    response = client.post(
        "/api/script/from-manuscript",
        json={
            "text": source,
            "title": "Köprünün hikâyesi",
            "language": "tr",
            "niche": "1_news_flash",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()["plan"]
    assert payload["full_narration"] == source
    assert payload["title"] == "Köprünün hikâyesi"
    assert payload["scenes"][0]["scene_description"] == "Visual footage of ancient stone bridge."
    assert payload["scenes"][0]["selected_video"]["url"].endswith(".mp4")
    assert matcher_calls == [("1_news_flash", True)]
    assert stock_calls == ["1_news_flash"]


def test_manuscript_route_rejects_invalid_scene_count(client):
    text = " ".join(
        (
            f"Bu sahne numara {index} için detaylı anlatım metnidir ve izleyiciye olayın "
            "arka planını anlaması için gereken bütün önemli ayrıntıları açıkça anlatır."
        )
        for index in range(25)
    )

    response = client.post(
        "/api/script/from-manuscript",
        json={"text": text, "language": "tr"},
    )

    assert response.status_code == 422
    assert "24 scenes" in response.json()["detail"]
