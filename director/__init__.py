"""
DirectorPlan package — production orchestration spine for the 500-item roadmap.
"""
from .schema import DirectorPlan, ScenePlan, VisualIntent, AudioEvent, QualityThresholds, DEFAULT_EFFECT_MANIFEST
from .compiler import compile_director_plan
from .validate import validate_director_plan
from .timeline import solve_timeline, fit_tts_to_timeline
from .visual_intent import (
    apply_visual_intents,
    resolve_niche_from_topic,
    resolve_topic_intelligence,
    semantic_relevance_score,
)
from .audio_bus import (
    build_audio_events,
    collect_tape_stop_times,
    master_audio_one_pass,
    apply_audio_events_to_wav,
)
from .quality_gate import pre_render_score, post_render_score, scenes_needing_regen

__all__ = [
    "DirectorPlan",
    "ScenePlan",
    "VisualIntent",
    "AudioEvent",
    "QualityThresholds",
    "DEFAULT_EFFECT_MANIFEST",
    "compile_director_plan",
    "validate_director_plan",
    "solve_timeline",
    "fit_tts_to_timeline",
    "apply_visual_intents",
    "resolve_niche_from_topic",
    "resolve_topic_intelligence",
    "semantic_relevance_score",
    "build_audio_events",
    "collect_tape_stop_times",
    "master_audio_one_pass",
    "apply_audio_events_to_wav",
    "pre_render_score",
    "post_render_score",
    "scenes_needing_regen",
]
