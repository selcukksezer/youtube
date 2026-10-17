from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=240)
    topic: Optional[str] = Field(default=None, max_length=240)
    niche: str = "1_news_flash"
    language: str = "tr"
    visual_mode: Optional[str] = None
    plan: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def sync_title_and_topic(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            raw_title = str(data.get("title") or "").strip()
            raw_topic = str(data.get("topic") or "").strip()
            if not raw_title and raw_topic:
                data["title"] = raw_topic
            elif raw_title and not raw_topic:
                data["topic"] = raw_title
        return data


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=240)
    niche: Optional[str] = None
    language: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None


class ScriptRequest(BaseModel):
    topic: Optional[str] = None


class RenderRequest(BaseModel):
    settings: Dict[str, Any] = Field(default_factory=dict)
