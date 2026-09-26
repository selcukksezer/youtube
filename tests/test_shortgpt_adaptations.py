import os
import pytest
from services.timed_visual_matcher import clean_query, generate_timed_visual_queries
from services.audio_tempo_guard import get_audio_duration, apply_shorts_tempo_guard
from services.facts_story_engine import FactsStoryEngine


def test_clean_query_removes_buzzwords():
    raw_query = "roman marble statue cinematic 4k atmospheric epic"
    cleaned = clean_query(raw_query)
    assert "cinematic" not in cleaned.lower()
    assert "4k" not in cleaned.lower()
    assert "atmospheric" not in cleaned.lower()
    assert "roman" in cleaned.lower()
    assert len(cleaned.split()) <= 3


def test_timed_visual_matcher_local_fallback():
    scenes = [
        {
            "scene_number": 1,
            "narration": "Okyanusun derinliklerinde daha önce hiç görülmemiş bir balina türü keşfedildi.",
            "scene_description": "Whale swimming in deep blue ocean water",
            "search_queries": ["okyanus derinlikleri 4k", "cinematic whale"],
        },
        {
            "scene_number": 2,
            "narration": "Bilim insanları bu devasa canlının iletişim seslerini kaydetmeyi başardı.",
            "scene_description": "Scientists in research laboratory analyzing sound waves",
            "search_queries": ["laboratuvar kayit", "epic sound waves"],
        },
    ]

    matched = generate_timed_visual_queries(scenes, niche_id="13_mystery", force_local=True)
    assert len(matched) == 2
    for sc in matched:
        assert len(sc["search_queries"]) >= 1
        for q in sc["search_queries"]:
            assert "4k" not in q.lower()
            assert "cinematic" not in q.lower()


def test_audio_tempo_guard_on_existing_wav(tmp_path):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_wav = os.path.join(root_dir, "test_tr.wav")

    if os.path.exists(test_wav):
        dur = get_audio_duration(test_wav)
        assert dur > 0.0

        out_wav = str(tmp_path / "tempo_guarded.wav")
        # Test applying tempo guard
        res = apply_shorts_tempo_guard(test_wav, out_wav, max_duration=100.0)
        assert os.path.exists(res)
        assert os.path.getsize(res) > 1000


def test_facts_story_engine_fallback_quality():
    script = FactsStoryEngine._procedural_fallback("Büyük Piramitler", is_tr=True)
    assert script["title"] == "Büyük Piramitler"
    assert len(script["scenes"]) == 4
    # Check that it doesn't contain forbidden slop
    full_text = script["full_narration"].lower()
    assert "tek bir ayrıntı yeter" not in full_text
    assert "gözlerime inanamadım" not in full_text
    assert "kleopatra" not in full_text
    assert len(script["scenes"][0]["search_queries"]) >= 2
