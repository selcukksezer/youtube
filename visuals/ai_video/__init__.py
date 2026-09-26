"""AI text-to-video providers + visual mixer (AI / stock / procedural peers)."""
from __future__ import annotations

from .base import AIVideoResult, AIVideoProvider
from .chain import generate_ai_clip, available_providers, ai_video_enabled
from .helios_prompt_builder import HeliosPromptBuilder, build_helios_prompt, HELIOS_NEGATIVE_PROMPT
from .kids_safety import check_kids_prompt_safety, is_kids_niche
from .mixer import VisualSource, assign_visual_source, mix_weights, peer_failover_order
from .prompt import build_cinematic_prompt, resolve_style_preset
from .providers.helios import HeliosVideoProvider
from .stitch import clip_count_for_duration, ffmpeg_concat

__all__ = [
    "AIVideoResult",
    "AIVideoProvider",
    "HeliosVideoProvider",
    "HeliosPromptBuilder",
    "build_helios_prompt",
    "HELIOS_NEGATIVE_PROMPT",
    "generate_ai_clip",
    "available_providers",
    "ai_video_enabled",
    "VisualSource",
    "assign_visual_source",
    "mix_weights",
    "peer_failover_order",
    "build_cinematic_prompt",
    "resolve_style_preset",
    "check_kids_prompt_safety",
    "is_kids_niche",
    "clip_count_for_duration",
    "ffmpeg_concat",
]
