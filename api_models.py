"""Pydantic request schemas shared by FastAPI route modules."""
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, ValidationInfo, field_validator, model_validator


def _normalize_voice_gender(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in {"male", "female", "auto"}:
        raise ValueError("voice_gender must be 'male', 'female', or 'auto'")
    return normalized


def _normalize_tts_voice(value: Optional[str], language: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or normalized.casefold() == "auto":
        return None
    from tts_voices import is_voice_available_from_catalog

    if not is_voice_available_from_catalog(normalized, language):
        raise ValueError("tts_voice must identify a voice available for the selected language")
    return normalized


def _normalize_subtitle_color(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    from subtitle_generator import NAMED_COLORS

    if normalized.casefold() in NAMED_COLORS:
        return normalized.casefold()
    if len(normalized) == 7 and normalized.startswith("#"):
        try:
            int(normalized[1:], 16)
        except ValueError:
            pass
        else:
            return normalized.upper()
    raise ValueError("subtitle colors must be #RRGGBB or a supported named color")


def _normalize_visualizer_color(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None

    color_part, separator, opacity_part = normalized.partition("@")
    if color_part.startswith("#"):
        hex_part = color_part[1:]
        prefix = "0x"
    elif color_part[:2].lower() == "0x":
        hex_part = color_part[2:]
        prefix = "0x"
    else:
        raise ValueError("audio_visualizer_color must be #RRGGBB or 0xRRGGBB")
    if len(hex_part) != 6:
        raise ValueError("audio_visualizer_color must contain exactly six hex digits")
    try:
        int(hex_part, 16)
    except ValueError as exc:
        raise ValueError("audio_visualizer_color must contain only hex digits") from exc

    if separator:
        try:
            opacity = float(opacity_part)
        except ValueError as exc:
            raise ValueError("audio_visualizer_color opacity must be between 0 and 1") from exc
        if not 0 <= opacity <= 1:
            raise ValueError("audio_visualizer_color opacity must be between 0 and 1")
        return f"{prefix}{hex_part.upper()}@{opacity:g}"
    return f"{prefix}{hex_part.upper()}"


def _normalize_bgm_track(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        return ""

    from services.bgm_security import validate_bgm_filename

    studio_prefix = "youtube_studio/"
    if normalized.casefold().startswith(studio_prefix):
        filename = normalized[len(studio_prefix):]
        if "/" in filename:
            raise ValueError("default_bgm_track must be a filename, not a nested path")
        return f"{studio_prefix}{validate_bgm_filename(filename)}"
    return validate_bgm_filename(normalized)


def _normalize_niche_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None

    from hybrid_niches import HYBRID_NICHES
    from niche_templates import NICHES, exact_style16
    from services.niche_topic_vault import NICHE_ALIASES

    if (
        normalized not in NICHES
        and normalized not in NICHE_ALIASES
        and normalized not in HYBRID_NICHES
        and not exact_style16(normalized)
    ):
        raise ValueError("niche must identify a supported niche")
    return normalized


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


class GoogleAIGenerateImageRequest(BaseModel):
    prompt: str
    model: Optional[str] = None


class GoogleAIGenerateVideoRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    duration_seconds: Optional[int] = 6


class RoyaltyFreeBgmRequest(BaseModel):
    query: Optional[str] = "ambient cinematic"
    prefer: Optional[str] = "auto"


class TtsPreviewRequest(BaseModel):
    text: Optional[str] = "Merhaba, bu kısa ses önizlemesidir."
    voice_gender: Optional[str] = "male"
    language: Optional[str] = "tr"
    tts_voice: Optional[str] = None

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


class ScriptGenerateRequest(BaseModel):
    keyword: str
    niche: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"
    reddit_post: Optional[Dict[str, Any]] = None
    channel_id: Optional[str] = None
    format_fingerprint: Optional[Dict[str, Any]] = None
    force_regenerate: Optional[bool] = False
    variation_attempt: Optional[int] = 0
    previous_narration: Optional[str] = None
    continuity_context: Optional[str] = Field(default=None, max_length=4000)
    enable_outro: Optional[bool] = True

    @field_validator("niche")
    @classmethod
    def normalize_supported_niche(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_niche_id(value)


class ScriptTranslateRequest(BaseModel):
    plan: Dict[str, Any]
    target_lang: str = Field(pattern="^(tr|en)$")


class ScriptManuscriptRequest(BaseModel):
    text: str = Field(min_length=30, max_length=12000)
    title: Optional[str] = Field(default=None, max_length=240)
    niche: Optional[str] = "1_news_flash"
    language: str = Field(default="tr", pattern="^(tr|en)$")

    @field_validator("niche")
    @classmethod
    def normalize_supported_niche(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_niche_id(value)


class SeriesPlanRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=240)
    niche: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"
    episode_count: int = Field(default=3, ge=2, le=5)

    @field_validator("niche")
    @classmethod
    def normalize_supported_niche(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_niche_id(value)


class PlanValidateRequest(BaseModel):
    plan: Dict[str, Any]
    title: Optional[str] = None
    niche: Optional[str] = None
    language: Optional[str] = "tr"
    recompile: Optional[bool] = True
    auto_repair: Optional[bool] = True

    @field_validator("niche")
    @classmethod
    def normalize_supported_niche(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_niche_id(value)


class PlanRepairRequest(BaseModel):
    plan: Dict[str, Any]
    title: Optional[str] = None
    niche: Optional[str] = None
    language: Optional[str] = "tr"
    recompile: Optional[bool] = True

    @field_validator("niche")
    @classmethod
    def normalize_supported_niche(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_niche_id(value)


class ContentGapResearchRequest(BaseModel):
    raw_topics: str
    niche: Optional[str] = "1_news_flash"

    @field_validator("niche")
    @classmethod
    def normalize_supported_niche(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_niche_id(value)


class TopicSuggestRequest(BaseModel):
    niche_id: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"
    count: Optional[int] = Field(default=5, ge=1, le=10)
    topic_hint: Optional[str] = None

    @field_validator("niche_id")
    @classmethod
    def normalize_supported_niche(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_niche_id(value)


class ShareDecisionRequest(BaseModel):
    decision: str = Field(..., description="'keep' = YouTube'da paylaş (proof sakla), 'discard' = sil")
    project_slug: Optional[str] = None


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


class KeyTestRequest(BaseModel):
    provider: str
    api_key: str


class GeneratedSceneSchema(BaseModel):
    """P2-22: strict schema for AI-generated scene objects."""

    model_config = {"extra": "ignore"}

    narration: str = Field(..., min_length=1)
    duration: Optional[float] = Field(default=None, gt=0)
    scene_description: Optional[str] = None
    search_query: Optional[str] = None
    search_queries: Optional[List[str]] = None
    mood: Optional[str] = None
    beat_type: Optional[str] = None

    @field_validator("narration")
    @classmethod
    def narration_not_blank(cls, value: str) -> str:
        if not str(value).strip():
            raise ValueError("narration must not be blank")
        try:
            from scenes.narration_validate import scene_narration_usable, HARD_MIN_WORDS_PER_SCENE
        except ImportError:
            return value
        if not scene_narration_usable(value, min_words=HARD_MIN_WORDS_PER_SCENE):
            raise ValueError("narration too short or placeholder-only")
        return value

    @field_validator("scene_description")
    @classmethod
    def scene_description_not_placeholder(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        try:
            from scenes.narration_validate import scene_description_usable
        except ImportError:
            return value
        if str(value).strip() and not scene_description_usable(value):
            raise ValueError("scene_description is placeholder or too short")
        return value

    @model_validator(mode="after")
    def has_visual_reference(self) -> "GeneratedSceneSchema":
        has_desc = bool(str(self.scene_description or "").strip())
        has_sq = bool(str(self.search_query or "").strip())
        has_sqs = bool(self.search_queries and any(str(q).strip() for q in self.search_queries))
        if not (has_desc or has_sq or has_sqs):
            raise ValueError("scene needs scene_description, search_query, or search_queries")
        if has_desc:
            try:
                from scenes.narration_validate import scene_description_usable
                if not scene_description_usable(self.scene_description or ""):
                    raise ValueError("scene_description is placeholder or too short")
            except ImportError:
                pass
        return self


class GeneratedPlanSchema(BaseModel):
    """P2-22: strict schema for AI scene-plan JSON root."""

    model_config = {"extra": "allow"}

    scenes: List[GeneratedSceneSchema] = Field(..., min_length=1)


def validate_generated_plan(data: Dict[str, Any]) -> GeneratedPlanSchema:
    """Raise ValidationError when AI scene JSON is malformed."""
    return GeneratedPlanSchema.model_validate(data)


def validate_generated_plan_errors(data: Any) -> List[str]:
    """Return human-readable validation errors; empty list means OK."""
    if not isinstance(data, dict):
        return ["plan root must be a JSON object"]
    try:
        validate_generated_plan(data)
        return []
    except ValidationError as exc:
        return [
            f"{'.'.join(str(p) for p in err.get('loc', ()))}: {err.get('msg', 'invalid')}"
            for err in exc.errors()
        ]