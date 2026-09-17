"""
Research, script generation, trending scanner, Reddit and RSS news router.
"""
import re
from fastapi import APIRouter, HTTPException
import requests
import config
from trending_scanner import scan_youtube_shorts_trends
from niche_templates import get_niche_production_profile
from api_models import ContentGapResearchRequest, ScriptGenerateRequest
from research_service import build_content_gap_suggestions
from scene_generator import generate_scenes, generate_reddit_rewrite_script
from reddit_client import fetch_public_posts
from rss_scanner import DEFAULT_RSS_FEEDS, get_breaking_news_topics

router = APIRouter(tags=["Research"])


@router.get("/api/trending/scan")
def api_scan_trending(topic: str = "Uzay", time_filter: str = "week", sort_by: str = "views", category: str = "all"):
    try:
        trends = scan_youtube_shorts_trends(topic, time_filter=time_filter, sort_by=sort_by, category=category)
        return {"status": "ok", "topic": topic, "trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/research/content-gaps")
def analyze_content_gaps(req: ContentGapResearchRequest):
    if len(req.raw_topics) > 12_000:
        raise HTTPException(status_code=400, detail="En fazla 12.000 karakterlik araştırma metni girin.")
    profile = get_niche_production_profile(req.niche or "1_news_flash")
    return {
        "status": "ok",
        "source": "YouTube Studio Research / Content gaps (manuel içe aktarma)",
        "profile": profile,
        "suggestions": build_content_gap_suggestions(req.raw_topics, req.niche or "1_news_flash"),
    }


@router.post("/api/script/generate")
def api_generate_script(req: ScriptGenerateRequest):
    try:
        old_lang = config.LANGUAGE
        if req.language:
            config.LANGUAGE = req.language
        if req.reddit_post and req.niche == "2_reddit_confessions":
            source_text = f"{req.reddit_post.get('title', '')}\n{req.reddit_post.get('body', '')}"
            plan = generate_reddit_rewrite_script(source_text, lang=req.language or "tr")
            plan["reddit_post"] = req.reddit_post
        else:
            plan = generate_scenes(req.keyword, niche_type=req.niche)
        plan["niche_profile"] = get_niche_production_profile(req.niche or "1_news_flash")
        config.LANGUAGE = old_lang
        return {"status": "ok", "plan": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/research/reddit")
def get_reddit_posts(subreddit: str = "AITA", limit: int = 10):
    """Fetches Reddit research posts with automatic discovery fallback (zero API key requirement)."""
    safe_subreddit = re.sub(r"[^A-Za-z0-9_]", "", subreddit) or "AITA"
    try:
        posts = fetch_public_posts(safe_subreddit, limit)
        has_keys = bool(getattr(config, "REDDIT_CLIENT_ID", "") and getattr(config, "REDDIT_CLIENT_SECRET", ""))
        mode = "oauth" if has_keys else "auto_discovery"
        return {
            "status": "ok",
            "posts": posts,
            "mode": mode,
            "message": "Resmi OAuth üzerinden çekildi." if has_keys else "Otomatik akıllı keşif havuzundan çekildi (API anahtarı gerekmez)."
        }
    except Exception as exc:
        return {"status": "error", "detail": f"Reddit araştırması alınamadı: {exc}", "posts": []}



@router.get("/api/rss/sources")
def get_rss_sources():
    """Returns default RSS sources (Items 1, 57)."""
    return {"sources": DEFAULT_RSS_FEEDS}


@router.get("/api/rss/fetch")
def fetch_rss_news(source: str = "aa_guncel", limit: int = 5):
    """Fetches breaking news from RSS feed (Item 57)."""
    items = get_breaking_news_topics(source, max_items=limit)
    return {"status": "ok", "source": source, "items": items}
