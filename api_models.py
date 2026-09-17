"""Pydantic request schemas shared by FastAPI route modules."""
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ConfigUpdateModel(BaseModel):
    language: Optional[str] = None
    tts_gender: Optional[str] = None
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


class ScriptGenerateRequest(BaseModel):
    keyword: str
    niche: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"
    reddit_post: Optional[Dict[str, Any]] = None


class ContentGapResearchRequest(BaseModel):
    raw_topics: str
    niche: Optional[str] = "1_news_flash"


class VideoRenderRequest(BaseModel):
    keyword: str
    plan: Optional[Dict[str, Any]] = None
    niche: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"
    voice_gender: Optional[str] = "male"
    bgm_track: Optional[str] = ""
    bgm_volume: Optional[float] = 0.12
    subtitle_highlight_color: Optional[str] = "#FFD700"
    subtitle_color: Optional[str] = "white"
    subtitle_font_size: Optional[int] = 54
    subtitle_y_position: Optional[float] = 0.8
    subtitle_preset: Optional[str] = None
    split_screen: Optional[bool] = False
    anti_duplicate: Optional[bool] = False
    watermark_path: Optional[str] = None
    enable_ken_burns: Optional[bool] = False
    reddit_post: Optional[Dict[str, Any]] = None


class KeyTestRequest(BaseModel):
    provider: str
    api_key: str