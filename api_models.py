"""Pydantic request schemas shared by FastAPI route modules."""
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, ValidationInfo, field_validator, model_validator

from api_models_ext import (
    ContentGapResearchRequest,
    GeneratedPlanSchema,
    GeneratedSceneSchema,
    GoogleAIGenerateImageRequest,
    GoogleAIGenerateVideoRequest,
    KeyTestRequest,
    PlanRepairRequest,
    PlanValidateRequest,
    RoyaltyFreeBgmRequest,
    ScriptGenerateRequest,
    ScriptManuscriptRequest,
    ScriptTranslateRequest,
    SeriesPlanRequest,
    ShareDecisionRequest,
    TopicSuggestRequest,
    TtsPreviewRequest,
    _normalize_bgm_track,
    _normalize_niche_id,
    _normalize_subtitle_color,
    _normalize_tts_voice,
    _normalize_visualizer_color,
    _normalize_voice_gender,
    validate_generated_plan,
    validate_generated_plan_errors,
)


class ConfigUpdateModel(BaseModel):
    language: Optional[str] = None
    tts_gender: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_rate: Optional[str] = None
    tts_pitch: Optional[str] = None
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None
    deepseek_key: Optional[str] = None
    grok_key: Optional[str] = None
    pexels_key: Optional[str] = None
    pixabay_key: Optional[str] = None
    youtube_data_key: Optional[str] = None
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    subtitle_color: Optional[str] = None
    subtitle_highlight_color: Optional[str] = None
    subtitle_font_size: Optional[int] = Field(default=None, ge=40, le=72)
    subtitle_y_position: Optional[float] = Field(default=None, ge=0.5, le=0.9)
    enable_bgm: Optional[bool] = None
    bgm_volume: Optional[float] = Field(default=None, ge=0.0, le=0.3)
    default_bgm_track: Optional[str] = None
    # Google AI Pro model slots
    gemini_model: Optional[str] = None
    gemini_image_model: Optional[str] = None
    gemini_video_model: Optional[str] = None
    gemini_tts_model: Optional[str] = None
    use_gemini_image_gen: Optional[bool] = None
    use_gemini_video_gen: Optional[bool] = None
    use_gemini_tts: Optional[bool] = None
    use_gemini_grounding: Optional[bool] = None
    use_gemini_embeddings: Optional[bool] = None
    prefer_gemini_scene_images: Optional[bool] = None
    auto_fetch_royalty_free_bgm: Optional[bool] = None
    elevenlabs_key: Optional[str] = None
    sonilo_key: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    azure_speech_key: Optional[str] = None
    azure_speech_region: Optional[str] = None
    postbridge_api_key: Optional[str] = None

    @field_validator("language")
    @classmethod
    def normalize_supported_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized not in {"tr", "en"}:
            raise ValueError("language must be 'tr' or 'en'")
        return normalized

    @field_validator("tts_gender")
    @classmethod
    def normalize_tts_gender(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_voice_gender(value)

    @field_validator("tts_voice")
    @classmethod
    def validate_tts_voice(
        cls,
        value: Optional[str],
        info: ValidationInfo,
    ) -> Optional[str]:
        language = info.data.get("language")
        if language is None:
            import config
            language = config.LANGUAGE
        return _normalize_tts_voice(value, language)

    @field_validator("tts_rate")
    @classmethod
    def normalize_tts_rate(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"[+-]\d+%", normalized):
            raise ValueError("tts_rate must use a signed percentage such as '+18%'")
        rate = int(normalized[:-1])
        if not -50 <= rate <= 100:
            raise ValueError("tts_rate must be between -50% and +100%")
        return normalized

    @field_validator("tts_pitch")
    @classmethod
    def normalize_tts_pitch(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"[+-]\d+Hz", normalized):
            raise ValueError("tts_pitch must use a signed Hz value such as '+0Hz'")
        return normalized

    @field_validator("subtitle_color", "subtitle_highlight_color")
    @classmethod
    def normalize_subtitle_colors(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_subtitle_color(value)

    @field_validator("default_bgm_track")
    @classmethod
    def normalize_default_bgm_track(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_bgm_track(value)


class VideoRenderRequest(BaseModel):
    keyword: str
    plan: Optional[Dict[str, Any]] = None
    niche: Optional[str] = None
    language: Optional[str] = "tr"
    voice_gender: Optional[str] = "male"
    tts_voice: Optional[str] = None
    bgm_track: Optional[str] = ""
    bgm_volume: Optional[float] = Field(default=0.12, ge=0.0, le=0.3)
    subtitle_highlight_color: Optional[str] = None
    subtitle_color: Optional[str] = None
    subtitle_font_size: Optional[int] = Field(default=54, ge=40, le=72)
    subtitle_y_position: Optional[float] = Field(default=0.8, ge=0.5, le=0.9)
    subtitle_preset: Optional[str] = None
    split_screen: Optional[bool] = False
    gameplay_category: Optional[str] = "auto"
    anti_duplicate: Optional[bool] = True
    watermark_path: Optional[str] = None
    enable_ken_burns: Optional[bool] = False
    enable_zoompan: Optional[bool] = False
    reddit_post: Optional[Dict[str, Any]] = None
    resolution: Optional[str] = "1080p"
    visual_mode: Optional[str] = "auto"
    auto_publish: Optional[bool] = False
    channel_id: Optional[str] = None
    allow_similar_script: Optional[bool] = False
    force_render: Optional[bool] = False
    resume: Optional[bool] = False
    whisper_align: Optional[bool] = None
    enable_intro_whoosh: Optional[bool] = False
    enable_bgm: Optional[bool] = None
    enable_outro: Optional[bool] = True
    enable_sonilo_sfx: bool = False

    @field_validator("keyword")
    @classmethod
    def normalize_keyword(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("keyword must not be empty")
        return normalized

    @field_validator("niche")
    @classmethod
    def normalize_supported_niche(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_niche_id(value)

    @model_validator(mode="after")
    def inherit_niche_from_plan(self) -> "VideoRenderRequest":
        if self.niche is None and self.plan:
            self.niche = _normalize_niche_id(self.plan.get("niche_id"))
        return self

    @field_validator("voice_gender")
    @classmethod
    def normalize_voice_gender(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_voice_gender(value)

    @field_validator("tts_voice")
    @classmethod
    def validate_tts_voice(
        cls,
        value: Optional[str],
        info: ValidationInfo,
    ) -> Optional[str]:
        return _normalize_tts_voice(value, info.data.get("language"))

    @field_validator("language")
    @classmethod
    def normalize_supported_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in {"tr", "en"}:
            raise ValueError("language must be 'tr' or 'en'")
        return normalized

    @field_validator("resolution")
    @classmethod
    def normalize_supported_resolution(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in {"1080p", "720p", "540p"}:
            raise ValueError("resolution must be '1080p', '720p', or '540p'")
        return normalized

    @field_validator("visual_mode")
    @classmethod
    def normalize_supported_visual_mode(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized not in {"auto", "flux", "whiteboard", "mixed"}:
            raise ValueError(
                "visual_mode must be 'auto', 'flux', 'whiteboard', or 'mixed'"
            )
        return normalized

    @field_validator("gameplay_category")
    @classmethod
    def normalize_gameplay_category(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        from gameplay_pool import GAMEPLAY_CATEGORIES

        if normalized not in GAMEPLAY_CATEGORIES:
            raise ValueError("gameplay_category must be a supported gameplay category")
        return normalized

    @field_validator("subtitle_color", "subtitle_highlight_color")
    @classmethod
    def normalize_subtitle_colors(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_subtitle_color(value)

    @field_validator("subtitle_preset")
    @classmethod
    def normalize_subtitle_preset(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        from subtitle_generator import SUBTITLE_PRESETS

        if normalized not in SUBTITLE_PRESETS:
            raise ValueError("subtitle_preset must be a supported subtitle style")
        return normalized

    @field_validator("audio_visualizer_mode")
    @classmethod
    def normalize_audio_visualizer_mode(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized not in {
            "line", "p2p", "cline", "frequency_bars", "showfreqs", "spectrum",
        }:
            raise ValueError("audio_visualizer_mode must be a supported waveform mode")
        return normalized

    @field_validator("bgm_track")
    @classmethod
    def validate_render_bgm_track(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_bgm_track(value)

    @field_validator("watermark_path")
    @classmethod
    def validate_watermark_path(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if ".." in normalized.replace("\\", "/").split("/"):
            raise ValueError("watermark_path must not contain '..'")
        return normalized

    @field_validator("audio_visualizer_color")
    @classmethod
    def normalize_audio_visualizer_color(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_visualizer_color(value)

    enable_outro_swell: Optional[bool] = True
    duck_attack_ms: Optional[float] = Field(default=80, ge=20, le=200)
    duck_release_ms: Optional[float] = Field(default=200, ge=50, le=600)
    intro_blast: Optional[float] = Field(default=0.85, ge=0.5, le=1.0)
    outro_swell_sec: Optional[float] = Field(default=5, ge=2, le=10)
    enable_hook_card: Optional[bool] = True
    hook_text: Optional[str] = None
    enable_broll_insert: Optional[bool] = False
    enable_face_center: Optional[bool] = False
    enable_emphasis_card: Optional[bool] = False
    enable_audio_visualizer: Optional[bool] = False
    audio_visualizer_mode: Optional[str] = "line"
    audio_visualizer_color: Optional[str] = "0x00D7FF"
    enable_news_ticker: Optional[bool] = False
    news_ticker_text: Optional[str] = None
    enable_reddit_card: Optional[bool] = False
    task_id: Optional[str] = None


__all__ = [
    "ConfigUpdateModel",
    "ContentGapResearchRequest",
    "GeneratedPlanSchema",
    "GeneratedSceneSchema",
    "GoogleAIGenerateImageRequest",
    "GoogleAIGenerateVideoRequest",
    "KeyTestRequest",
    "PlanRepairRequest",
    "PlanValidateRequest",
    "RoyaltyFreeBgmRequest",
    "ScriptGenerateRequest",
    "ScriptManuscriptRequest",
    "ScriptTranslateRequest",
    "SeriesPlanRequest",
    "ShareDecisionRequest",
    "TopicSuggestRequest",
    "TtsPreviewRequest",
    "VideoRenderRequest",
    "validate_generated_plan",
    "validate_generated_plan_errors",
]