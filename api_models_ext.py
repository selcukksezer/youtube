"""Extended Pydantic request schemas and normalization helpers for FastAPI routes."""
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
    if not normalized or normalized.casefold() in {"auto", "__auto__", "default", "random"}:
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


class GoogleAIGenerateImageRequest(BaseModel):
    prompt: str
    model: Optional[str] = None


class GoogleAIGenerateVideoRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    duration_seconds: Optional[int] = 6


class RoyaltyFreeBgmRequest(BaseModel):
    query: Optional[str] = "ambient cinematic"
    mood: Optional[str] = None
    prefer: Optional[str] = "auto"

    @model_validator(mode="before")
    @classmethod
    def map_mood_to_query(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("mood") and not data.get("query"):
            data = dict(data)
            data["query"] = data.get("mood")
        return data


class TtsPreviewRequest(BaseModel):
    text: Optional[str] = "Merhaba, bu kısa ses önizlemesidir."
    voice_gender: Optional[str] = "male"
    language: Optional[str] = "tr"
    tts_voice: Optional[str] = None
    voice: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def map_voice_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if data.get("voice") and not data.get("tts_voice"):
                data["tts_voice"] = data.get("voice")
            raw_voice = str(data.get("tts_voice") or "").strip().lower()
            if not data.get("language") and raw_voice.startswith(("en-", "tr-")):
                data["language"] = raw_voice[:2]
        return data

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
    count: Optional[int] = Field(default=5, ge=1, le=30)
    topic_hint: Optional[str] = None
    refresh: Optional[bool] = False
    exclude_titles: Optional[List[str]] = None

    @field_validator("niche_id")
    @classmethod
    def normalize_supported_niche(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_niche_id(value)


class ShareDecisionRequest(BaseModel):
    decision: str = Field(..., description="'keep' = YouTube'da paylaş (proof sakla), 'discard' = sil")
    project_slug: Optional[str] = None


class KeyTestRequest(BaseModel):
    provider: str
    api_key: str = ""
    key: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_key_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if not data.get("api_key") and data.get("key") is not None:
                data["api_key"] = str(data.get("key") or "")
        return data


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
