"""Pydantic request schemas shared by FastAPI route modules."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


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
    subtitle_font_size: Optional[int] = None
    subtitle_y_position: Optional[float] = None
    enable_bgm: Optional[bool] = None
    bgm_volume: Optional[float] = None
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
    tts_voice: Optional[str] = None
    language: Optional[str] = "tr"


class ScriptGenerateRequest(BaseModel):
    keyword: str
    niche: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"
    reddit_post: Optional[Dict[str, Any]] = None
    channel_id: Optional[str] = None
    format_fingerprint: Optional[Dict[str, Any]] = None


class PlanValidateRequest(BaseModel):
    plan: Dict[str, Any]
    title: Optional[str] = None
    niche: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"
    recompile: Optional[bool] = True
    auto_repair: Optional[bool] = True


class PlanRepairRequest(BaseModel):
    plan: Dict[str, Any]
    title: Optional[str] = None
    niche: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"
    recompile: Optional[bool] = True


class ContentGapResearchRequest(BaseModel):
    raw_topics: str
    niche: Optional[str] = "1_news_flash"


class TopicSuggestRequest(BaseModel):
    niche_id: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"
    count: Optional[int] = Field(default=5, ge=1, le=10)
    topic_hint: Optional[str] = None


class ShareDecisionRequest(BaseModel):
    decision: str = Field(..., description="'keep' = YouTube'da paylaş (proof sakla), 'discard' = sil")
    project_slug: Optional[str] = None


class VideoRenderRequest(BaseModel):
    keyword: str
    plan: Optional[Dict[str, Any]] = None
    niche: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"
    voice_gender: Optional[str] = "male"
    tts_voice: Optional[str] = None
    bgm_track: Optional[str] = ""
    bgm_volume: Optional[float] = 0.12
    subtitle_highlight_color: Optional[str] = "#FFD700"
    subtitle_color: Optional[str] = "white"
    subtitle_font_size: Optional[int] = 54
    subtitle_y_position: Optional[float] = 0.8
    subtitle_preset: Optional[str] = None
    split_screen: Optional[bool] = False
    gameplay_category: Optional[str] = "auto"
    anti_duplicate: Optional[bool] = False
    watermark_path: Optional[str] = None
    enable_ken_burns: Optional[bool] = False
    reddit_post: Optional[Dict[str, Any]] = None
    resolution: Optional[str] = "1080p"
    auto_publish: Optional[bool] = False
    channel_id: Optional[str] = None


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
            from scenes.narration_validate import scene_narration_usable
        except ImportError:
            return value
        if not scene_narration_usable(value):
            raise ValueError("narration too short or placeholder-only")
        return value

    @model_validator(mode="after")
    def has_visual_reference(self) -> "GeneratedSceneSchema":
        has_desc = bool(str(self.scene_description or "").strip())
        has_sq = bool(str(self.search_query or "").strip())
        has_sqs = bool(self.search_queries and any(str(q).strip() for q in self.search_queries))
        if not (has_desc or has_sq or has_sqs):
            raise ValueError("scene needs scene_description, search_query, or search_queries")
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