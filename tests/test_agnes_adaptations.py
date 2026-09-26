"""
Tests for lcy362/agnes-video-generator adaptations:
1. ArtifactDependencyGraph (fine-grained cache invalidation, minimal rebuild paths)
2. CharacterIdentityAnchor (character visual continuity, police-sketch conditioning, reference prompt)
3. MultiZoneSubtitleDirector (3-zone ASS subtitle positioning: \\an8 top, \\an5 center, \\an2 bottom)
"""
import pytest
from services.artifact_dependency_graph import (
    ArtifactDependencyGraph,
    ImpactPlan,
    PipelineStep,
    artifact_dependency_graph,
)
from services.character_identity_anchor import (
    CharacterAnchor,
    CharacterIdentityAnchor,
    character_identity_anchor,
)
from services.multi_zone_subtitle_director import (
    MultiZoneSubtitleDirector,
    SubtitleZone,
    multi_zone_subtitle_director,
)


# --- 1. ArtifactDependencyGraph Tests ---
def test_dependency_graph_visual_edit_preserves_audio():
    """Verify modifying a scene visual preserves all TTS audio and subtitles."""
    impact = artifact_dependency_graph.compute_impact(["scene:3:visual"], total_scenes=5)

    assert "scene_visual:3" in impact.invalidated_artifacts
    assert "final_video" in impact.invalidated_artifacts
    assert "tts_audio:3" not in impact.invalidated_artifacts
    assert "subtitles" not in impact.invalidated_artifacts

    assert impact.can_reuse_audio
    assert impact.can_reuse_subtitles
    assert not impact.can_reuse_visuals

    # Steps to re-run should not include TTS
    assert PipelineStep.TTS_SYNTHESIS not in impact.steps_to_rerun
    assert PipelineStep.VISUAL_FETCH_OR_GEN in impact.steps_to_rerun
    assert PipelineStep.FINAL_COMPOSITE in impact.steps_to_rerun


def test_dependency_graph_narration_edit_preserves_visuals():
    """Verify modifying a scene narration preserves video clips while rebuilding audio."""
    impact = artifact_dependency_graph.compute_impact(["scene:2:narration"], total_scenes=5)

    assert "tts_audio:2" in impact.invalidated_artifacts
    assert "subtitles" in impact.invalidated_artifacts
    assert "scene_visual:2" not in impact.invalidated_artifacts

    assert impact.can_reuse_visuals
    assert not impact.can_reuse_audio
    assert not impact.can_reuse_subtitles

    assert PipelineStep.TTS_SYNTHESIS in impact.steps_to_rerun
    assert PipelineStep.VISUAL_FETCH_OR_GEN not in impact.steps_to_rerun


def test_dependency_graph_bgm_edit_minimal_rebuild():
    """Verify modifying BGM only re-mixes audio and muxes final video (0 video re-encoding)."""
    impact = artifact_dependency_graph.compute_impact(["audio:bgm"], total_scenes=5)

    assert impact.can_reuse_audio
    assert impact.can_reuse_visuals
    assert impact.can_reuse_subtitles

    assert impact.steps_to_rerun == [
        PipelineStep.AUDIO_MIX,
        PipelineStep.FINAL_COMPOSITE,
    ]


def test_dependency_graph_story_edit_invalidates_all():
    """Verify changing core story invalidates the entire pipeline."""
    impact = artifact_dependency_graph.compute_impact(["story"], total_scenes=4)
    assert not impact.can_reuse_audio
    assert not impact.can_reuse_visuals
    assert not impact.can_reuse_subtitles
    assert PipelineStep.SCRIPT_GEN in impact.steps_to_rerun


# --- 2. CharacterIdentityAnchor Tests ---
def test_character_identity_anchor_creation():
    """Verify anchor extraction deriving character archetype and police sketch."""
    anchor = character_identity_anchor.extract_or_create_anchor("Marcus Aurelius'un Stoa Felsefesi")
    assert anchor.name == "Marcus Aurelius"
    assert "crimson" in anchor.outfit.lower() or "roman" in anchor.outfit.lower()
    assert "marble" in anchor.color_palette.lower() or "bronze" in anchor.color_palette.lower()

    sketch = anchor.to_police_sketch()
    assert "Marcus Aurelius" not in sketch  # Sketch should be purely physical
    assert "color scheme:" in sketch


def test_character_identity_anchor_prompt_building():
    """Verify building reference keyframe prompt with diffused lighting and zero occlusion."""
    anchor = CharacterAnchor(
        name="Alex",
        gender="male",
        age_group="30s",
        hair="short dark hair",
        facial_features="blue eyes",
        outfit="black leather jacket",
        color_palette="black, navy",
    )
    ref_prompt = character_identity_anchor.build_reference_image_prompt(anchor)
    assert "Character reference sheet of Alex" in ref_prompt
    assert "No occlusion" in ref_prompt
    assert "neutral standing pose" in ref_prompt


def test_character_identity_anchor_scene_injection():
    """Verify injecting anchor into scene visual prompt."""
    anchor = CharacterAnchor(
        name="Alex",
        gender="male",
        age_group="30s",
        hair="short dark hair",
        facial_features="blue eyes",
        outfit="black leather jacket",
        color_palette="black, navy",
    )
    base_prompt = "Standing on a rain-slicked neon street at midnight"
    injected = character_identity_anchor.inject_anchor_into_scene_prompt(base_prompt, anchor)
    assert "featuring Alex" in injected
    assert "black leather jacket" in injected


# --- 3. MultiZoneSubtitleDirector Tests ---
def test_multi_zone_subtitle_classification():
    """Verify dynamic 3-zone subtitle placement and ASS alignment tags."""
    subs = [
        {"text": "Bu sırrı asla unutmayın!", "start": 0.0, "end": 2.2},   # Hook -> TOP (\an8)
        {"text": "Yüzyıllardır saklanan kadim bir kural var.", "start": 2.5, "end": 6.0},  # Context -> BOTTOM (\an2)
        {"text": "Peki en kritik gerçek ne?", "start": 6.2, "end": 8.5},   # Climax question -> CENTER (\an5)
        {"text": "Zihnini korumayı seçtiğinde her şey değişir.", "start": 8.8, "end": 12.0},  # Narration -> BOTTOM (\an2)
    ]

    styled = multi_zone_subtitle_director.plan_subtitle_styling(subs)
    assert len(styled) == 4

    # Line 1: Hook at the top
    assert styled[0].zone == SubtitleZone.TOP
    assert styled[0].ass_alignment_tag == "\\an8"
    assert styled[0].font_size == multi_zone_subtitle_director.hook_font_size
    assert "&H0000FFFF&" in styled[0].color_bgr_hex  # Yellow

    # Line 2: Standard narration at bottom
    assert styled[1].zone == SubtitleZone.BOTTOM
    assert styled[1].ass_alignment_tag == "\\an2"

    # Line 3: Climax question in the center
    assert styled[2].zone == SubtitleZone.CENTER
    assert styled[2].ass_alignment_tag == "\\an5"
    assert styled[2].font_size == multi_zone_subtitle_director.center_font_size

    # Line 4: Standard narration at bottom
    assert styled[3].zone == SubtitleZone.BOTTOM
    assert styled[3].ass_alignment_tag == "\\an2"


def test_multi_zone_subtitle_ass_dialogue_formatting():
    """Verify generation of valid ASS Dialogue event line with override tags."""
    subs = [{"text": "Durdur ve dinle!", "start": 0.5, "end": 2.0}]
    styled = multi_zone_subtitle_director.plan_subtitle_styling(subs)
    ass_line = multi_zone_subtitle_director.to_ass_dialogue_line(styled[0])

    assert ass_line.startswith("Dialogue: 0,0:00:00.50,0:00:02.00,Default,,0,0,")
    assert "{\\an8\\fs62\\c&H0000FFFF&}Durdur ve dinle!" in ass_line
