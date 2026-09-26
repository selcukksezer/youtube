"""
Tests for gyoridavid/short-video-maker adaptations:
1. AudioMoodDirector (sentiment analysis, 12 mood tags, ducking params)
2. KineticSubtitlePager (1-line caption paging, word highlight, ASS karaoke)
3. ScenePacingGuard (visual asset deduplication, tail loop padding, duration limits)
"""
import pytest
from services.audio_mood_director import AudioMoodDirector, MusicMood, audio_mood_director
from effects.kinetic_subtitle_pager import KineticSubtitlePager, kinetic_subtitle_pager
from services.scene_pacing_guard import ScenePacingGuard, scene_pacing_guard


def test_audio_mood_director_sentiment_detection():
    """Verify keyword and niche sentiment mapping."""
    # Test dark sentiment
    mood_dark = audio_mood_director.detect_mood("Bu karanlık ve korkunç gecede katil ortaya çıktı")
    assert mood_dark == MusicMood.DARK

    # Test excited sentiment
    mood_excited = audio_mood_director.detect_mood("Bitcoin rekor kırdı inanılmaz bir yükseliş ve zafer")
    assert mood_excited == MusicMood.EXCITED

    # Test niche fallback
    mood_stoic = audio_mood_director.detect_mood("Her şey akıp gider", niche_id="stoic")
    assert mood_stoic == MusicMood.CONTEMPLATIVE


def test_audio_mood_director_ducking_and_track():
    """Verify volume ducking calculations and track resolution."""
    res = audio_mood_director.direct_audio_for_script(
        script_text="Marcus Aurelius zihnin gücünü anlattı",
        niche_id="philosophy",
    )
    assert res["mood"] == "contemplative"
    assert "track" in res and res["track"]["path"]
    mix = res["mix"]
    assert mix["bgm_volume_db"] < -12.0  # Proper ducking below voice
    assert 0.0 < mix["bgm_volume_linear"] < 0.5


def test_kinetic_subtitle_pager():
    """Verify single-line word timestamp grouping and ASS karaoke dialogue generation."""
    words = [
        {"word": "Bu", "start": 0.0, "end": 0.2},
        {"word": "video", "start": 0.25, "end": 0.6},
        {"word": "hayatını", "start": 0.65, "end": 1.1},
        {"word": "tamamen", "start": 1.15, "end": 1.6},
        {"word": "değiştirecek.", "start": 1.65, "end": 2.3},
        # Gap of 1.5s
        {"word": "Hazır", "start": 3.8, "end": 4.1},
        {"word": "mısın?", "start": 4.15, "end": 4.5},
    ]

    pager = KineticSubtitlePager(line_max_length=20, max_distance_ms=1000)
    pages = pager.create_pages(words)

    # Should have split into at least 2 pages (due to length or gap)
    assert len(pages) >= 2

    # Check first page structure
    p0 = pages[0]
    assert p0.page_index == 0
    assert len(p0.text) <= 25
    assert len(p0.words) > 0

    # Check ASS dialogue karaoke format
    ass_line = p0.to_ass_dialogue(style_name="Punchy")
    assert "Dialogue: 0," in ass_line
    assert r"{\k" in ass_line
    assert "Punchy" in ass_line


def test_scene_pacing_guard_deduplication_and_padding():
    """Verify visual asset deduplication, tail padding, and duration bounds."""
    guard = ScenePacingGuard(min_scene_sec=1.5, max_scene_sec=6.0, default_padding_back_ms=800)
    scenes = [
        {"duration": 1.0, "visual_id": "vid_A", "text": "Kısa sahne"},       # Violation: <1.5s
        {"duration": 4.0, "visual_id": "vid_B", "text": "Normal sahne"},
        {"duration": 7.5, "visual_id": "vid_A", "text": "Tekrar & Uzun"},    # Violations: duplicate vid_A & >6.0s
    ]

    result = guard.audit_and_repair(scenes)

    assert not result.is_valid  # Had violations
    assert any("duplicate" in v for v in result.violations)
    assert any("below minimum" in v for v in result.violations)
    assert any("exceeds maximum" in v for v in result.violations)

    # Check repaired scenes
    repaired = result.repaired_scenes
    assert len(repaired) == 3
    # Scene 0 clamped to min 1.5s
    assert repaired[0]["duration"] >= 1.5
    # Scene 2 duplicate cleared
    assert repaired[2]["visual_id"] is None
    assert repaired[2].get("force_new_visual") is True
    assert repaired[2].get("split_required") is True
    # Last scene has tail padding
    assert repaired[2]["padding_back_sec"] == 0.8
