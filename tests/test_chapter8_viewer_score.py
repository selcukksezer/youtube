"""
Tests for Chapter 8.5: Virality Audit ve İzleyici Puanlama Motoru
Covers:
- 100-point virality audit components:
  1. Hook strength (30 points)
  2. Rhythm & pacing (25 points)
  3. Emotional contrast & curiosity (25 points)
  4. Seamless loop bridge (20 points)
- Pass threshold >= 70.0 points
- Automatic virality repair engine (auto_repair_script_virality) for scores < 70
- Backward-compatible compute_viewer_score integration
"""
import pytest
from compliance.viewer_score import (
    calculate_hook_score,
    calculate_rhythm_pacing_score,
    calculate_emotional_contrast_score,
    calculate_loop_bridge_score,
    audit_script_virality,
    auto_repair_script_virality,
    compute_viewer_score,
    VIRALITY_PASS_THRESHOLD,
)


def test_hook_score_high_for_question_and_triggers():
    scenes = [
        {
            "beat_type": "hook",
            "narration": "Neden kimse Roma'nın bu gizli sırrından bahsetmiyor?",
        }
    ]
    score = calculate_hook_score(scenes)
    assert 22.0 <= score <= 30.0


def test_hook_score_low_for_passive_statement():
    scenes = [
        {
            "beat_type": "intro",
            "narration": "Ve bugün antik Roma hakkında bazı genel bilgiler konuşacağız arkadaşlar.",
        }
    ]
    score = calculate_hook_score(scenes)
    assert score < 20.0


def test_rhythm_pacing_score_in_sweet_spot():
    scenes = [
        {"narration": "Roma imparatorluğu zirvedeyken kimse sonun geldiğine inanmıyordu.", "duration": 3.0},
        {"narration": "Fakat içeriden başlayan çürüme dış düşmanlardan çok daha tehlikeliydi.", "duration": 3.2},
    ]
    score = calculate_rhythm_pacing_score(scenes, total_dur=6.2)
    assert 18.0 <= score <= 25.0


def test_emotional_contrast_score_detects_contrast_words():
    scenes = [
        {"narration": "Herkes zafer kutluyordu ama sarayda gizli bir panik vardı."},
        {"narration": "Oysa gerçek çok farklıydı çünkü asıl tehlike kapıdaydı."},
    ]
    score = calculate_emotional_contrast_score(scenes)
    assert 18.0 <= score <= 25.0


def test_loop_bridge_score_rewards_semantic_closure():
    scenes = [
        {"narration": "Neden Sezar en yakın dostunun ihanetini son ana kadar fark etmedi?"},
        {"narration": "Güven bazen en ölümcül silaha dönüşebilir."},
        {"narration": "İşte tam da bu yüzden Sezar o gün tarihin akışını değiştirdi..."},
    ]
    score = calculate_loop_bridge_score(scenes)
    assert 16.0 <= score <= 20.0


def test_audit_script_virality_full_100_points_passing():
    plan = {
        "scenes": [
            {
                "beat_type": "hook",
                "narration": "Neden kimse bu şok edici gerçeği konuşmuyor?",
                "duration": 3.0,
            },
            {
                "beat_type": "build",
                "narration": "Herkes imparatorluğun yıkılmaz olduğunu sanıyordu ama sarayda gizli bir plan vardı.",
                "duration": 3.5,
            },
            {
                "beat_type": "climax",
                "narration": "Oysa gerçek çok daha sarsıcıydı ve kimse buna hazırlıklı değildi.",
                "duration": 3.0,
            },
            {
                "beat_type": "loop_bridge",
                "narration": "İşte tam da bu yüzden kimse bu şok edici gerçeği unutamadı...",
                "duration": 3.0,
            },
        ],
        "total_duration": 12.5,
    }

    report = audit_script_virality(plan)
    assert report["passed"] is True
    assert report["status"] == "PASSED"
    assert report["score"] >= VIRALITY_PASS_THRESHOLD
    assert "hook_strength" in report["components"]
    assert "rhythm_pacing" in report["components"]
    assert "emotional_contrast" in report["components"]
    assert "loop_bridge" in report["components"]


def test_audit_script_virality_failing_triggers_repairable():
    weak_plan = {
        "scenes": [
            {"narration": "Bugün ağaçlar hakkında konuşalım.", "duration": 5.0},
            {"narration": "Ağaçlar yeşildir ve yaprak dökerler.", "duration": 5.0},
            {"narration": "Sonra da kış gelir.", "duration": 5.0},
        ],
        "total_duration": 15.0,
    }

    report = audit_script_virality(weak_plan)
    assert report["passed"] is False
    assert report["score"] < VIRALITY_PASS_THRESHOLD
    assert len(report["diagnostics"]) > 0

    # Automatic virality repair
    repaired_plan, repaired_report = auto_repair_script_virality(weak_plan)
    assert repaired_report["score"] > report["score"]
    assert repaired_report["score"] >= VIRALITY_PASS_THRESHOLD
    assert repaired_report["passed"] is True


def test_compute_viewer_score_backward_compatibility():
    plan = {
        "scenes": [
            {"narration": "Neden kimse bunu söylemiyor?", "beat_type": "hook"},
            {"narration": "Çünkü gerçek çok basit aslında ama kimse bakmıyor."},
            {"narration": "İşte tam da bu yüzden sen artık biliyorsun..."},
        ],
        "total_duration": 10.0,
    }
    res = compute_viewer_score(plan)
    assert "score" in res
    assert "components" in res
    assert "pass" in res
    assert res["score"] >= 70.0
    assert res["pass"] is True
