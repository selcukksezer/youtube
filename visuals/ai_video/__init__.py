"""AI text-to-video providers + visual mixer (AI / stock / procedural peers)."""
from __future__ import annotations

from .base import AIVideoResult, AIVideoProvider
from .chain import generate_ai_clip, available_providers, ai_video_enabled
from .mixer import VisualSource, assign_visual_source, mix_weights, peer_failover_order
from .prompt import build_cinematic_prompt

__all__ = [
    "AIVideoResult",
    "AIVideoProvider",
    "generate_ai_clip",
    "available_providers",
    "ai_video_enabled",
    "VisualSource",
    "assign_visual_source",
    "mix_weights",
    "peer_failover_order",
    "build_cinematic_prompt",
]
