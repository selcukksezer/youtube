"""
System features router: Niches, Batch processing, Quota, Anti-Detect, Retention, Proofs, Roadmap.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import requests
import config
from niche_templates import list_all_niches, get_niche_production_profile
from batch_processor import batch_manager
from quota_manager import quota_tracker
from server_core import (
    is_rendering_active,
    process_batch_queue
)
from server_core import state

router = APIRouter(tags=["System"])


class BatchSubmitRequest(BaseModel):
    text: str
    niche: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"


@router.get("/api/niches")
def get_niches():
    """Returns all 35 pre-configured niche templates (Items 1-35)."""
    return {"niches": list_all_niches()}


@router.get("/api/niches/{niche_id}/profile")
def get_niche_profile(niche_id: str):
    """Returns the concrete render settings selected by a niche."""
    return {"status": "ok", "profile": get_niche_production_profile(niche_id)}


@router.get("/api/niches/{niche_id}/trends")
def get_niche_trends(niche_id: str, region: str = "TR"):
    """Fetches the past 24-hour YouTube video signals through YouTube Data API v3."""
    profile = get_niche_production_profile(niche_id)
    if not config.YOUTUBE_DATA_API_KEY:
        return {
            "status": "unavailable",
            "reason": "YOUTUBE_DATA_API_KEY tanımlı değil; resmi son 24 saat verisi alınamadı.",
            "profile": profile,
            "trends": []
        }

    published_after = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat().replace("+00:00", "Z")
    params = {
        "part": "snippet", "type": "video", "q": profile["name"], "order": "viewCount",
        "publishedAfter": published_after, "regionCode": region.upper(), "maxResults": 10,
        "key": config.YOUTUBE_DATA_API_KEY
    }
    try:
        search = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=12)
        search.raise_for_status()
        items = search.json().get("items", [])
        ids = [item.get("id", {}).get("videoId") for item in items if item.get("id", {}).get("videoId")]
        stats_by_id = {}
        if ids:
            stats = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "statistics", "id": ",".join(ids), "key": config.YOUTUBE_DATA_API_KEY},
                timeout=12
            )
            stats.raise_for_status()
            stats_by_id = {item["id"]: item.get("statistics", {}) for item in stats.json().get("items", [])}
        trends = [
            {
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"].get("channelTitle", ""),
                "published_at": item["snippet"].get("publishedAt", ""),
                "view_count": int(stats_by_id.get(item["id"]["videoId"], {}).get("viewCount", 0)),
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            }
            for item in items if item.get("id", {}).get("videoId")
        ]
        return {"status": "ok", "profile": profile, "trends": trends}
    except requests.RequestException as exc:
        return {"status": "error", "reason": str(exc), "profile": profile, "trends": []}


@router.post("/api/batch/submit")
def submit_batch_jobs(req: BatchSubmitRequest, background_tasks: BackgroundTasks):
    """Parses newline-separated topics or CSV rows and enqueues batch jobs (Items 70, 78)."""
    jobs = batch_manager.parse_text_lines(req.text, default_niche=req.niche, language=req.language)
    batch_manager.add_jobs(jobs)
    if jobs and not batch_manager.is_running and not state.is_rendering_active:
        background_tasks.add_task(process_batch_queue)
    return {"status": "ok", "enqueued": len(jobs)}


@router.get("/api/batch/status")
def get_batch_queue_status():
    """Returns current batch processing status and queue list."""
    return batch_manager.get_queue_status()


@router.get("/api/quota/stats")
def get_quota_statistics():
    """Returns API call count, errors, and zero cost health metrics (Items 62, 69)."""
    return quota_tracker.get_stats()


@router.post("/api/quota/reset")
def reset_quota_statistics():
    """Resets all API quota tracking counters and errors."""
    quota_tracker.reset_all()
    return {"status": "ok", "message": "Yapay zeka kota sayaçları sıfırlandı.", "stats": quota_tracker.get_stats()}



@router.get("/api/anti_detect/profile")
def get_anti_detect_profile(channel_id: str = "default_channel", lang: str = "en"):
    """Generates isolated browser profile configuration to prevent bot detection (Items 1-70)."""
    from anti_detect_engine import anti_detect_engine
    profile = anti_detect_engine.generate_profile(channel_id=channel_id, lang=lang)
    return {"status": "ok", "profile": profile.__dict__}


@router.get("/api/anti_detect/jitter")
def get_upload_jitter(hour: int = 18, minute: int = 0):
    """Calculates upload schedule jitter to prevent robotic timing footprint (Items 8, 47)."""
    from anti_detect_engine import anti_detect_engine
    jitter = anti_detect_engine.calculate_upload_jitter(target_hour=hour, target_minute=minute)
    return {"status": "ok", "jitter": jitter}


@router.get("/api/anti_detect/warmup")
def get_warmup_plan(niche: str = "stoic"):
    """Generates organic account warm-up session plan before video upload (Items 7, 17, 18)."""
    from anti_detect_engine import anti_detect_engine
    plan = anti_detect_engine.generate_warmup_session_plan(niche_keyword=niche)
    return {"status": "ok", "warmup_plan": plan}


@router.get("/api/hybrid_niches")
def get_hybrid_niches():
    """Returns all 7 high-RPM hybrid synergy niches (Items 276-345)."""
    from hybrid_niches import list_all_hybrid_niches
    return {"status": "ok", "hybrid_niches": list_all_hybrid_niches()}


@router.get("/api/retention/formulas")
def get_retention_formulas():
    """Returns 12 seamless loop formulas and pattern interrupt triggers (Items 201-275)."""
    from viral_retention_engine import viral_retention_engine
    return {
        "status": "ok", 
        "formulas": viral_retention_engine.LOOP_FORMULAS,
        "interrupts": viral_retention_engine.PATTERN_INTERRUPTS
    }


@router.get("/api/proof/appeal_script")
def get_appeal_script(channel_name: str = "Shorts AI Studio", title: str = "3 Stoic Rules"):
    """Generates professional 5-minute YouTube Appeal Video Script for Reused Content reviews (Items 472-475)."""
    from proof_archiver import proof_archiver
    script = proof_archiver.generate_appeal_video_script(channel_name=channel_name, video_title=title)
    return {"status": "ok", "script": script}


@router.get("/api/roadmap/audit")
def get_roadmap_500_audit():
    """Returns compliance audit verifying all 500 roadmap items (100% coverage)."""
    from roadmap_500_evaluator import roadmap_500_evaluator
    return roadmap_500_evaluator.audit_all_items()


@router.get("/api/roadmap/items")
def get_roadmap_500_items(section: Optional[int] = None, search: Optional[str] = None):
    """Returns all 500 roadmap items, with optional section filter and search query."""
    from roadmap_500_evaluator import roadmap_500_evaluator
    items = list(roadmap_500_evaluator.items.values())
    if section:
        items = [it for it in items if it.get("section_id") == section]
    if search:
        s = search.lower()
        items = [it for it in items if s in it["title"].lower() or s in it["description"].lower()]
    return {"status": "ok", "total": len(items), "items": items}


@router.get("/api/health")
def get_system_health():
    """Returns real-time system health, VideoToolbox encoder, disk space, and API status (Item 464)."""
    from system_resilience import get_system_health_status
    return get_system_health_status()

