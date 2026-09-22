"""
Channel onboarding, anti-detect warmup, and Studio UI automation router.
"""
from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel, Field
import database
from channel_onboarding_bot import channel_bot
from server_core import broadcast_event

router = APIRouter(tags=["Channel"])


class ChannelAnalyzeRequest(BaseModel):
    channel_url: str
    proxy_url: Optional[str] = None
    niche: Optional[str] = "Stoic / Motivasyon"
    is_brand_new: Optional[bool] = True
    recovery_email: Optional[str] = None
    phone_number: Optional[str] = None
    phone_type: Optional[str] = "physical"


class ChannelWarmupRequest(BaseModel):
    identifier: str


class ChannelStudioUploadRequest(BaseModel):
    identifier: str
    video_path: str
    title: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = Field(default_factory=list)
    scheduled_hour: Optional[int] = 18


@router.post("/api/channel/analyze")
def analyze_channel_endpoint(req: ChannelAnalyzeRequest):
    """Analyzes new channel URL, binds isolated profile, verifies proxy, email, phone and generates 15-rule roadmap."""
    res = channel_bot.analyze_channel(
        channel_url=req.channel_url,
        proxy_url=req.proxy_url,
        niche=req.niche or "Stoic / Motivasyon",
        is_brand_new=req.is_brand_new if req.is_brand_new is not None else True,
        recovery_email=req.recovery_email,
        phone_number=req.phone_number,
        phone_type=req.phone_type or "physical"
    )
    return res


@router.get("/api/channel/list")
def list_managed_channels_endpoint():
    """Lists all registered channels with health scores and isolation status."""
    channels = database.list_managed_channels()
    return {"status": "ok", "channels": channels}


@router.post("/api/channel/warmup")
async def run_channel_warmup_endpoint(req: ChannelWarmupRequest):
    """Executes automated organic warm-up session with live logging."""
    def log_handler(msg: str):
        broadcast_event("log", f"[AntiDetect] {msg}")

    broadcast_event("log", f"🛡️ Kanal için Anti-Detect Çerez Isındırma başlatıldı: {req.identifier}")
    result = await channel_bot.execute_warmup_session(
        channel_id_or_url=req.identifier,
        log_callback=log_handler
    )
    return result


@router.post("/api/channel/studio_upload")
def run_studio_upload_endpoint(req: ChannelStudioUploadRequest):
    """Executes Studio UI safe upload with jitter, ctime manipulation, and typing delays."""
    def log_handler(msg: str):
        broadcast_event("log", f"[StudioUI] {msg}")

    result = channel_bot.execute_studio_upload(
        channel_id_or_url=req.identifier,
        video_path=req.video_path,
        title=req.title,
        description=req.description or "",
        tags=req.tags or [],
        scheduled_hour=req.scheduled_hour if req.scheduled_hour is not None else 18,
        log_callback=log_handler
    )
    return result
