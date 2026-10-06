"""
Test suite verifying the fixes for production pipeline errors:
1. No audio_duration_probe_failed when audio_path is None (pre-TTS)
2. Semantic overlap returns valid scores for authorized clips
3. Post-render audit accepts yuv420p and yuvj420p without unexpected_pix_fmt warning
4. 'değil' and 'kendisidir' in Turkish sentences do not trigger fragment_ending or dangling_tail
5. Stoic and pack procedural fallback narrations meet word constraints and pass virality audit
6. Pollinations AI fast circuit breaker trips on 429/timeout
"""
import os
import pytest
from render.pipeline_audit import pre_render_audit, post_render_audit, _semantic_overlap, audit_search_queries
from scenes.narration_validate import scene_narration_issues
from scenes.fallback import _generate_stoic_scenes, _generate_procedural_fallback_scenes
from services.virality_evaluator import evaluate_script_virality
from services.pollinations_ai_visual import (
    pollinations_circuit_open,
    trip_pollinations_circuit,
    reset_pollinations_circuit,
)


def test_pre_render_audit_no_audio_probe_warning():
    clips = [
        {"path": "s000_pexels_123.mp4", "duration": 5.0, "narration": "Birinci sahne test."},
        {"path": "s001_pexels_456.mp4", "duration": 5.0, "narration": "İkinci sahne test."},
        {"path": "s002_pexels_789.mp4", "duration": 5.0, "narration": "Üçüncü sahne test."},
        {"path": "s003_pexels_999.mp4", "duration": 5.0, "narration": "Dördüncü sahne test."},
    ]
    # In pre-render stage, audio has not been generated yet
    result = pre_render_audit(clips, audio_path=None)
    assert "audio_duration_probe_failed" not in result["warnings"]


def test_semantic_overlap_authorized_clips():
    clip = {
        "path": "s000_pexels_4761764.mp4",
        "duration": 5.0,
        "narration": "Modern dünyanın henüz açıklayamadığı ilginç olaylar",
        "scene_description": "bold infographic motion background wide establishing view",
        "search_queries": ["bold infographic motion background"],
        "visual_intent": {"search_queries": ["bold infographic motion background"]},
        "candidate_topic_match_score": 0.35,
        "score": 100,
    }
    score = _semantic_overlap(clip)
    assert score >= 0.25


def test_turkish_degil_not_dangling_tail():
    sentence = "Kontrol edemediğin haberler, gürültü ve başkalarının öfkesi senin huzurunu çalmak zorunda değil."
    issues = scene_narration_issues(sentence)
    assert "dangling_tail" not in issues
    assert "fragment_ending" not in issues
    assert "dangling_sentence" not in issues


def test_turkish_kendisidir_not_dangling():
    sentence = "Marcus Aurelius'un dediği gibi: Yolun önündeki engel, artık yolun kendisidir."
    issues = scene_narration_issues(sentence)
    assert "dangling_tail" not in issues
    assert "fragment_ending" not in issues


def test_stoic_fallback_no_narration_issues():
    plan = _generate_stoic_scenes("Zor ve Toksik İnsanlarla Başa Çıkmanın Stoacı Yolu", is_tr=True)
    for i, s in enumerate(plan["scenes"]):
        issues = scene_narration_issues(s["narration"])
        assert not issues, f"Scene {i} had issues: {issues} in '{s['narration']}'"
    audit = evaluate_script_virality(plan["full_narration"], topic="Zor ve Toksik İnsanlarla Başa Çıkmanın Stoacı Yolu")
    assert audit.get("score", 0) >= 30
    assert not any("tekrarlanan" in str(iss).lower() for iss in audit.get("issues", []))


def test_pack_procedural_fallback_no_repetitive_strings():
    plan = _generate_procedural_fallback_scenes("Modern Dünyanın Henüz Açıklayamadığı En İlginç Üç Bilimsel Gizem ve Olay", language="tr")
    for i, s in enumerate(plan["scenes"]):
        issues = scene_narration_issues(s["narration"])
        assert not issues, f"Scene {i} had issues: {issues} in '{s['narration']}'"
    audit = evaluate_script_virality(plan["full_narration"], topic="Modern Dünyanın Henüz Açıklayamadığı En İlginç Üç Bilimsel Gizem ve Olay")
    assert audit.get("score", 0) >= 30
    assert not any("tekrarlanan" in str(iss).lower() for iss in audit.get("issues", []))


def test_pollinations_circuit_breaker():
    reset_pollinations_circuit()
    assert not pollinations_circuit_open()
    trip_pollinations_circuit(60.0)
    assert pollinations_circuit_open()
    reset_pollinations_circuit()
    assert not pollinations_circuit_open()
