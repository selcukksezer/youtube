import os
import pytest
from services.stock_simplifier_fallback import simplify_query_to_noun, build_resilient_query_ladder
from effects.xfade_transitions import AVAILABLE_TRANSITIONS, concat_with_xfade_transitions
from services.dual_visual_manager import compose_dual_visual_scene


def test_simplify_query_to_noun():
    query = "ancient roman marble bust statue"
    candidates = simplify_query_to_noun(query)
    assert len(candidates) >= 2
    assert "bust statue" in candidates or "statue" in candidates
    assert "statue" in candidates


def test_build_resilient_query_ladder():
    initial = ["fourteen wolves running in snow", "dark forest night"]
    ladder = build_resilient_query_ladder(initial)
    assert len(ladder) > len(initial)
    # Check that initial queries come first
    assert ladder[0] == "fourteen wolves running in snow"
    assert ladder[1] == "dark forest night"
    # Check that fallback nouns exist
    assert any("snow" in q for q in ladder)
    assert any("forest" in q or "night" in q for q in ladder)


def test_available_transitions():
    assert "fade" in AVAILABLE_TRANSITIONS
    assert "wipeleft" in AVAILABLE_TRANSITIONS
    assert "smoothleft" in AVAILABLE_TRANSITIONS
    assert len(AVAILABLE_TRANSITIONS) >= 6


def test_dual_visual_manager_file_not_found():
    with pytest.raises(FileNotFoundError):
        compose_dual_visual_scene(
            clip_a_path="non_existent_clip_a.mp4",
            clip_b_path=None,
            audio_path="non_existent_audio.wav",
            output_path="out.mp4",
            total_duration=5.0,
        )
