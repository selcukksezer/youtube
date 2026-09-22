from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=240)
    niche: str = "1_news_flash"
    language: str = "tr"


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
