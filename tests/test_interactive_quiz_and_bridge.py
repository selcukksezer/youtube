"""
Test for Item 97 Interactive Quiz Engine and Kids Song Project Bridge Integration.
"""
import pytest
from fastapi.testclient import TestClient
from server import app
import niche_templates
from effects import apply_interactive_quiz_overlay
import kids_song_bridge

client = TestClient(app)


def test_interactive_quiz_niche_registered():
    assert "37_interactive_quiz" in niche_templates.NICHES
    niche = niche_templates.NICHES["37_interactive_quiz"]
    assert niche["id"] == "37_interactive_quiz"
    assert niche["has_split_screen"] is True
    assert niche["viral_score"] >= 90
    assert "quiz" in niche["trending_keywords"]
    assert niche_templates.NICHE_FAMILY_MAP["37_interactive_quiz"] == "quiz"


def test_interactive_quiz_production_profile():
    profile = niche_templates.get_niche_production_profile("37_interactive_quiz")
    assert profile["id"] == "37_interactive_quiz"
    assert profile["production_rules"]["split_screen"] is True
    assert profile["production_rules"]["clickbait_overlays"] is True


def test_interactive_quiz_overlay_callable():
    assert callable(apply_interactive_quiz_overlay)


def test_kids_song_project_creation():
    res = kids_song_bridge.create_kids_song_project(
        name="Test Bebek Sarkisi",
        topic="Minik Kediler",
        age_group="3-5",
        mood="neşeli",
        lyrics="Miyav miyav kedi geldi",
    )
    assert isinstance(res, dict)
    assert "ok" in res
    if res.get("ok"):
        assert "project_id" in res
        assert "slug" in res
        assert "/cocuk-sarki/" in res.get("url", "")


def test_api_kids_song_projects_endpoint():
    payload = {
        "title": "Renkli Balonlar Sarkisi",
        "topic": "Balonlar ve Renkler",
        "lyrics": "Kırmızı mavi sarı balon uçtu havaya"
    }
    res = client.post("/api/kids-song/projects", json=payload)
    assert res.status_code in (200, 503)
    data = res.json()
    if res.status_code == 200:
        assert data.get("ok") is True
        assert "project" in data
        assert data["project"]["name"] == "Renkli Balonlar Sarkisi"
