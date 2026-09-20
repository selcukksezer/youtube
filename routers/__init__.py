"""
FastAPI routers package.
"""
from .config_router import router as config_router
from .video_router import router as video_router
from .media_router import router as media_router
from .research_router import router as research_router
from .channel_router import router as channel_router
from .system_router import router as system_router
from .google_ai_router import router as google_ai_router

__all__ = [
    "config_router",
    "video_router",
    "media_router",
    "research_router",
    "channel_router",
    "system_router",
    "google_ai_router",
]
