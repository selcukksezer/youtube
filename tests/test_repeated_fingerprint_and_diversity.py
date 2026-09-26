"""Regression tests for unique visual scene fingerprints and topic suggester diversity."""
import pytest
from scenes.fallback import _subject_visuals, _generate_procedural_fallback_scenes
from scenes.enrichment import ensure_unique_scene_visual_fingerprints, enrich_plan_scenes
from production.quality import validate_script_quality
from services.topic_suggester import suggest_topics


def test_subject_visuals_has_unique_fingerprints():
    pack = {"id": "12_amazon_affiliate", "name": "Amazon Affiliate", "subjects": ["gadget box", "smart device"]}
    visuals = _subject_visuals(pack, "Amazon Akıllı Ürünler")
    assert len(visuals) >= 10
    descs = [v[0] for v in visuals]
    assert len(set(descs)) == len(descs), "Scene descriptions must all be unique"


def test_ensure_unique_scene_visual_fingerprints_deduplicates():
    duplicate_scenes = [
        {"scene_description": "smart watch on desk", "search_queries": ["smart watch", "desk tech"], "duration": 5.0},
        {"scene_description": "smart watch on desk", "search_queries": ["smart watch", "desk tech"], "duration": 5.0},
        {"scene_description": "smart watch on desk", "search_queries": ["smart watch", "desk tech"], "duration": 5.0},
    ]
    diversified = ensure_unique_scene_visual_fingerprints(duplicate_scenes)
    descs = [s["scene_description"] for s in diversified]
    assert len(set(descs)) == 3, "Duplicate scene descriptions must be diversified"


def test_quality_gate_never_hard_fails_on_repeated_fingerprint():
    plan = {
        "title": "Amazon Test Video",
        "scenes": [
            {
                "narration": f"Bu sahne urunun {i+1}. en onemli ve dikkat cekici ozelligini detaylica anlatiyor.",
                "scene_description": "smart gadget on wooden desk",
                "search_queries": ["smart gadget", "gadget unboxing"],
                "duration": 5.2,
            }
            for i in range(10)
        ],
    }
    plan["full_narration"] = " ".join(s["narration"] for s in plan["scenes"])
    report = validate_script_quality(plan)
    issues = report.get("issues", [])
    assert not any("repeated_scene_fingerprint" in issue for issue in issues), (
        f"repeated_scene_fingerprint must not be a hard issue: {issues}"
    )


def test_topic_suggester_diversity():
    res1 = suggest_topics("12_amazon_affiliate", count=5)
    res2 = suggest_topics("12_amazon_affiliate", count=5)
    assert res1["status"] == "ok"
    assert res2["status"] == "ok"
    assert len(res1["suggestions"]) >= 3
    assert len(res2["suggestions"]) >= 3
