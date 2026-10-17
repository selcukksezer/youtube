"""
FastAPI routers package.
"""
from . import (
    channel_router,
    clipper_router,
    config_router,
    google_ai_router,
    jobs_v1_router,
    kids_song_router,
    media_router,
    research_router,
    system_router,
    video_router,
)

__all__ = [
    "config_router",
    "video_router",
    "media_router",
    "research_router",
    "channel_router",
    "system_router",
    "google_ai_router",
    "kids_song_router",
    "clipper_router",
    "jobs_v1_router",
]
