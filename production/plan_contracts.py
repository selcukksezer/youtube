"""Pydantic contracts from plan.md section 14. Fail-fast on new publish payloads."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AspectRatio(str, Enum):
    PORTRAIT_9_16 = "9:16"
    SQUARE_1_1 = "1:1"
    LANDSCAPE_16_9 = "16:9"


class VisualAssetType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    AI_VIDEO = "ai_video"
    AI_IMAGE = "ai_image"
    PROCEDURAL = "procedural"
    WHITEBOARD = "whiteboard"


class LicenseType(str, Enum):
    PEXELS = "pexels"
    PIXABAY = "pixabay"
    UNSPLASH = "unsplash"
    CC0 = "cc0"
    COMMERCIAL_FREE = "commercial_free"
    AI_GENERATED = "ai_generated"
    PUBLIC_DOMAIN = "public_domain"
    UNKNOWN = "unknown"


class VisualAssetSpec(BaseModel):
    asset_id: str
    asset_type: VisualAssetType
    local_path: str
    source_url: Optional[str] = None
    provider: str
    license: LicenseType = LicenseType.COMMERCIAL_FREE
    width: int = Field(default=1080, ge=2)
    height: int = Field(default=1920, ge=2)
    duration_sec: float = Field(default=0.0, ge=0.0)
    fps: float = Field(default=30.0, ge=1.0)
    is_safe_for_commercial: bool = True
    author_attribution: Optional[str] = None


class SceneIntent(BaseModel):
    scene_index: int = Field(ge=0)
    start_sec: float = Field(ge=0.0)
    duration_sec: float = Field(gt=0.0)
    narration_text: str = Field(min_length=1)
    visual_search_terms: List[str] = Field(default_factory=list)
    motion_type: str = "zoom_in"
    transition_in: str = "fade"
    transition_duration: float = Field(default=0.25, ge=0.0, le=1.0)
    selected_visual: Optional[VisualAssetSpec] = None


class AudioBusSpec(BaseModel):
    tts_voice: str = "tr-TR-AhmetNeural"
    tts_rate: float = Field(default=1.05, ge=0.5, le=2.0)
    tts_pitch: str = "+0Hz"
    bgm_track_path: Optional[str] = None
    bgm_volume_db: float = Field(default=-18.0, le=0.0)
    sidechain_ducking_db: float = Field(default=-14.0, le=0.0)
    sfx_manifest: List[Dict[str, Any]] = Field(default_factory=list)
    master_lufs_target: float = Field(default=-14.0, ge=-24.0, le=-6.0)


class PublishDirectorPlan(BaseModel):
    job_id: str = Field(min_length=1)
    niche_id: str = Field(min_length=1)
    topic: str = Field(min_length=3)
    aspect_ratio: AspectRatio = AspectRatio.PORTRAIT_9_16
    target_duration_sec: float = Field(default=45.0, ge=10.0, le=60.0)
    retention_hook_type: str = "cognitive_dissonance"
    loop_bridge_text: str = ""
    scenes: List[SceneIntent] = Field(min_length=1)
    audio_bus: AudioBusSpec = Field(default_factory=AudioBusSpec)
    subtitle_style: str = "capcut_yellow"
    anti_detect_enabled: bool = True
    hardware_accel: str = "auto"
    output_video_path: Optional[str] = None


class WordTimestamp(BaseModel):
    word: str
    start_sec: float
    end_sec: float
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class SubtitlePage(BaseModel):
    page_index: int
    start_sec: float
    end_sec: float
    text: str
    words: List[WordTimestamp]
    style_name: str = "capcut_yellow"
    layout_zone: str = "bottom_safe_zone"


class QualityGateVerdict(BaseModel):
    job_id: str
    passed: bool
    retention_score: float = Field(ge=0.0, le=100.0)
    audio_lufs_actual: float
    duplicate_asset_count: int = Field(ge=0)
    unsafe_license_count: int = Field(ge=0)
    unrendered_text_count: int = Field(ge=0)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
