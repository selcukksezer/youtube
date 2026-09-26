"""
Tests for Helios (PKU-YuanGroup/Helios) Adaptations:
1. HeliosPromptBuilder 4-tier cinematographic shot generation
2. Helios negative prompt against AI slop
3. Helios inference parameter sizing (fps=24, 9:16 vertical, frame counts)
4. HeliosVideoProvider registry and metadata
5. HeliosVisualEnhancer scene sequence pacing and camera variation
"""
import pytest
from visuals.ai_video.helios_prompt_builder import (
    HELIOS_NEGATIVE_PROMPT,
    HeliosPromptBuilder,
    build_helios_prompt,
)
from visuals.ai_video.providers import ALL_PROVIDER_CLASSES, HeliosVideoProvider
from visuals.ai_video import AIVideoResult
from services.helios_visual_enhancer import helios_visual_enhancer


def test_helios_prompt_builder_four_tiers():
    """Verify Helios 4-tier shot structure: Camera, Action, Atmosphere, Optic."""
    prompt = build_helios_prompt(
        narration="Bitcoin balinaları aniden büyük transferler yapmaya başladı",
        scene_description="Kripto cüzdanı açılıyor",
        niche_id="crypto",
        aspect="9:16",
        index=0,
    )
    assert len(prompt) > 50
    # Must contain vertical 9:16 framing
    assert "9:16" in prompt or "vertical" in prompt
    # Must contain optic finish
    assert "35mm film" in prompt or "bokeh" in prompt
    # Must contain camera movement
    assert any(w in prompt for w in ["push-in", "tracking", "close-up", "sweep", "tilt"])


def test_helios_negative_prompt():
    """Verify Helios negative prompt kills AI slop and artifacts."""
    assert "Bright tones" in HELIOS_NEGATIVE_PROMPT
    assert "extra fingers" in HELIOS_NEGATIVE_PROMPT
    assert "walking backwards" in HELIOS_NEGATIVE_PROMPT
    assert "subtitles" in HELIOS_NEGATIVE_PROMPT


def test_helios_shot_params():
    """Verify vertical resolution, 24 fps, and odd frame counts."""
    params = HeliosPromptBuilder.create_helios_params(
        narration="Antik Roma gladyatör arenasında gergin bekleyiş",
        scene_description="Gladyatör kılıcını çekti",
        niche_id="history",
        duration=4.125,
        aspect="9:16",
        distilled=True,
    )
    p_dict = params.to_dict()
    assert p_dict["width"] == 384
    assert p_dict["height"] == 640
    assert p_dict["fps"] == 24
    assert p_dict["num_frames"] % 2 == 1  # Odd frames for Helios chunks
    assert p_dict["guidance_scale"] == 1.0
    assert p_dict["pyramid_num_inference_steps_list"] == [2, 2, 2]


def test_helios_provider_in_registry():
    """Verify HeliosVideoProvider is properly registered with high priority."""
    prov_classes = [cls.__name__ for cls in ALL_PROVIDER_CLASSES]
    assert "HeliosVideoProvider" in prov_classes
    prov = HeliosVideoProvider()
    assert prov.name == "helios"
    assert prov.priority == 8


def test_helios_visual_enhancer_scene_sequence():
    """Verify camera movement sequencing across scenes."""
    scenes = [
        {"narration": "Sahne 1 kanca", "scene_description": "giriş"},
        {"narration": "Sahne 2 kanıt", "scene_description": "detay"},
        {"narration": "Sahne 3 şok", "scene_description": "dönüm noktası"},
    ]
    enhanced = helios_visual_enhancer.enhance_scenes_sequence(scenes, niche_id="philosophy")
    assert len(enhanced) == 3
    # Verify different camera movements are assigned sequentially
    motions = [s["helios_camera_motion"] for s in enhanced]
    assert len(set(motions)) == 3  # All 3 scenes have distinct camera motions
    for s in enhanced:
        assert "helios_prompt" in s
        assert "helios_negative_prompt" in s
        assert "helios_inference_config" in s
