"""
Unit and Integration tests for Chapter 28.5 (invideo-ai-nexus adaptations):
- director.visual_intent (SHOT_INTENTS, classify_scene_intent, assign_camera_direction)
- Verifies intelligent camera mapping: Question=zoom_in, Transition=pan_left, Conclusion=zoom_out.
"""

import pytest
from director.schema import ScenePlan, SCENE_INTENTS, CAMERA_DIRECTIONS
from director.visual_intent import (
    SHOT_INTENTS,
    classify_scene_intent,
    assign_camera_direction,
    apply_visual_intents,
)


def test_invideo_nexus_shot_intents_mapping():
    """Verify invideo-ai-nexus core camera motion mapping rules."""
    assert "question" in SHOT_INTENTS
    assert "transition" in SHOT_INTENTS
    assert "conclusion" in SHOT_INTENTS

    # Soru = Zoom-in
    assert SHOT_INTENTS["question"]["camera_direction"] == "zoom_in"
    # Geçiş = Pan-left
    assert SHOT_INTENTS["transition"]["camera_direction"] == "pan_left"
    # Sonuç = Zoom-out
    assert SHOT_INTENTS["conclusion"]["camera_direction"] == "zoom_out"


def test_classify_and_assign_camera_motion():
    """Verify semantic scene classification and camera assignment."""
    # 1. Question hook
    intent_q = classify_scene_intent(
        narration="Peki bu piramitlerin sırrı neden yüzyıllardır çözülemedi?",
        index=0,
        total_scenes=4,
    )
    assert intent_q == "question"
    cam_q = assign_camera_direction(intent_q, index=0)
    assert cam_q == "zoom_in"

    # 2. Transition
    intent_t = classify_scene_intent(
        narration="Ancak yıllar sonra araştırmacılar derinlerde gizli bir oda buldular.",
        index=1,
        total_scenes=4,
    )
    assert intent_t == "transition"
    cam_t = assign_camera_direction(intent_t, index=1)
    assert cam_t == "pan_left"

    # 3. Conclusion (Outro)
    intent_c = classify_scene_intent(
        narration="İşte bu yüzden tarih boyunca hiçbir sır sonsuza kadar saklı kalmaz.",
        index=3,
        total_scenes=4,
        beat_type="resolution",
    )
    assert intent_c == "conclusion"
    cam_c = assign_camera_direction(intent_c, index=3)
    assert cam_c == "zoom_out"


def test_apply_visual_intents_end_to_end():
    """Verify full ScenePlan pipeline assigns semantic camera directions."""
    scenes = [
        ScenePlan(index=0, narration="Neden kimse bu gerçeği konuşmuyor?", duration=5.0),
        ScenePlan(index=1, narration="Fakat laboratuvar sonuçları her şeyi değiştirdi.", duration=5.0),
        ScenePlan(index=2, narration="Sonuç olarak insanlık yeni bir çağa adım attı.", duration=5.0),
    ]

    enriched = apply_visual_intents(scenes, niche_id="9_five_facts", title="Büyük Keşif")
    assert len(enriched) == 3

    # Scene 0 (Question) -> zoom_in
    assert enriched[0].camera_direction == "zoom_in"
    # Scene 1 (Transition) -> pan_left
    assert enriched[1].camera_direction == "pan_left"
    # Scene 2 (Conclusion) -> zoom_out
    assert enriched[2].camera_direction == "zoom_out"
