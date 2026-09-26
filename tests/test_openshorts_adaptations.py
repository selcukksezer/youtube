"""
Tests for mutonby/openshorts adaptations:
1. PunchInDirector (asymmetric zoom, smoothstep easing, FFmpeg filter generation)
2. HookVisualGrounding (semantic alignment, slop detection, regrounded visual intent)
3. ActiveSpeakerDetector (dialogue turn analysis, split-stack vs single portrait routing)
"""
import pytest
from effects.punch_in_director import PunchInDirector, punch_in_director
from services.hook_visual_grounding import HookVisualGrounding, hook_visual_grounding
from services.active_speaker_detector import ActiveSpeakerDetector, LayoutDecision, active_speaker_detector


def test_punch_in_director_zoom_curve():
    """Verify asymmetric curve (rise, hold, fall) and peak zoom."""
    zooms = punch_in_director.calculate_zoom_curve(
        total_duration_sec=6.0,
        fps=30,
        emphasis_times=[1.0],  # Punch at 1.0s
        max_zoom=1.12,
    )
    assert len(zooms) == 180  # 6s * 30fps
    # Initial frame at t=0 should be 1.0
    assert zooms[0] == 1.0
    # At t=1.0s (frame 30), zoom should start rising
    assert zooms[30] == 1.0
    # At hold period (t=1.5s, frame 45), zoom should reach peak 1.12
    assert pytest.approx(zooms[45], rel=1e-2) == 1.12
    # At t=5.0s (after fall), zoom should return to 1.0
    assert zooms[150] == 1.0


def test_punch_in_director_ffmpeg_filter():
    """Verify generated FFmpeg filter string syntax."""
    f_str = punch_in_director.generate_ffmpeg_zoom_filter(
        width=1080,
        height=1920,
        total_duration_sec=4.0,
        punch_time_sec=0.5,
        max_zoom=1.12,
        fps=30,
    )
    assert "scale=1080:1920" in f_str
    assert "crop=w=" in f_str
    assert "1.120" in f_str


def test_hook_visual_grounding_matching():
    """Verify high coherence when narration and visual scene align."""
    narration = "Jüpiter'in devasa kırmızı lekesi yüzyıllardır dönüyor"
    v_desc = "Jüpiter gezegeni kırmızı leke fırtınası uzay boşluğu"
    score, n_ents, v_ents = hook_visual_grounding.calculate_coherence(narration, v_desc)
    assert score >= 0.35  # Grounded!
    assert "jüpiter" in n_ents


def test_hook_visual_grounding_disjointed_repair():
    """Verify low coherence slop detection and automatic regrounding."""
    narration = "Büyük İskender ordusuyla Pers imparatorluğuna doğru yürüdü"
    slop_desc = "Ofiste kahve içen modern iş insanı dizüstü bilgisayar"  # Disjointed!
    
    audit = hook_visual_grounding.reground_scene(
        narration=narration,
        scene_description=slop_desc,
    )
    assert not audit.is_grounded  # Successfully flagged as disjointed!
    assert audit.coherence_score < 0.35
    # Must have rewritten the visual intent to match Alexander / soldiers / army
    assert any(w in audit.regrounded_visual_intent.lower() for w in ["iskender", "ordusuyla", "pers"])


def test_active_speaker_detector_single_speaker():
    """Verify single dominant speaker suppresses split stack."""
    turns = [
        {"speaker": "A", "start": 0.0, "end": 18.0},
        {"speaker": "B", "start": 18.1, "end": 19.5},  # Short interjection <20%
    ]
    res = active_speaker_detector.evaluate_turns(turns, total_duration_sec=20.0)
    assert res.layout_decision == LayoutDecision.SINGLE_PORTRAIT
    assert not res.is_multispeaker


def test_active_speaker_detector_conversational_split():
    """Verify balanced dialogue routes to split-screen stack."""
    turns = [
        {"speaker": "Host", "start": 0.0, "end": 3.0},
        {"speaker": "Guest", "start": 3.1, "end": 6.0},
        {"speaker": "Host", "start": 6.1, "end": 8.5},
        {"speaker": "Guest", "start": 8.6, "end": 12.0},
    ]
    res = active_speaker_detector.evaluate_turns(turns, total_duration_sec=12.0)
    assert res.layout_decision == LayoutDecision.SPLIT_STACK
    assert res.is_multispeaker
