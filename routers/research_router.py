"""
Research, script generation, trending scanner, Reddit and RSS news router.
"""
import re
from fastapi import APIRouter, HTTPException
import requests
import config
from trending_scanner import scan_youtube_shorts_trends
from niche_templates import get_niche_production_profile, get_niche_ab_variants
from api_models import ContentGapResearchRequest, ScriptGenerateRequest, TopicSuggestRequest
from services.topic_suggester import suggest_topics
from research_service import (
    build_content_gap_suggestions,
    aggregate_format_fingerprint,
    build_content_gap_fingerprint,
    extract_format_fingerprint_from_title,
)
from director import resolve_niche_from_topic, compile_director_plan, pre_render_score
from director.visual_intent import resolve_topic_intelligence
from scene_generator import generate_scenes, generate_reddit_rewrite_script
from scenes.narration_validate import apply_auto_repair_if_needed
from viral_seo_agent import append_research_source_reference
from reddit_client import fetch_public_posts
from rss_scanner import DEFAULT_RSS_FEEDS, get_breaking_news_topics

router = APIRouter(tags=["Research"])


@router.post("/api/topics/suggest")
def api_suggest_topics(req: TopicSuggestRequest):
    """Advanced niche-aware topic suggestions (YouTube + AI + trend + Reddit signals)."""
    try:
        result = suggest_topics(
            niche_id=req.niche_id or "1_news_flash",
            language=req.language or config.LANGUAGE,
            count=req.count or 5,
            topic_hint=req.topic_hint or "",
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "Niş bulunamadı."))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/trending/scan")
def api_scan_trending(topic: str = "Uzay", time_filter: str = "week", sort_by: str = "views", category: str = "all"):
    try:
        trends = scan_youtube_shorts_trends(topic, time_filter=time_filter, sort_by=sort_by, category=category)
        fps = [t.get("format_fingerprint") for t in trends if t.get("format_fingerprint")]
        return {
            "status": "ok",
            "topic": topic,
            "trends": trends,
            "format_fingerprint": aggregate_format_fingerprint(fps),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/research/content-gaps")
def analyze_content_gaps(req: ContentGapResearchRequest):
    if len(req.raw_topics) > 12_000:
        raise HTTPException(status_code=400, detail="En fazla 12.000 karakterlik araştırma metni girin.")
    profile = get_niche_production_profile(req.niche or "1_news_flash")
    suggestions = build_content_gap_suggestions(req.raw_topics, req.niche or "1_news_flash")
    return {
        "status": "ok",
        "source": "YouTube Studio Research / Content gaps (manuel içe aktarma)",
        "profile": profile,
        "suggestions": suggestions,
        "format_fingerprint": build_content_gap_fingerprint(suggestions, req.niche or "1_news_flash"),
    }


@router.post("/api/script/generate")
def api_generate_script(req: ScriptGenerateRequest):
    try:
        old_lang = config.LANGUAGE
        if req.language:
            config.LANGUAGE = req.language
        topic_intel = resolve_topic_intelligence(req.keyword or "", req.niche or "1_news_flash")
        locked_niche = topic_intel["resolved_niche"]
        if req.reddit_post and locked_niche == "2_reddit_confessions":
            source_text = f"{req.reddit_post.get('title', '')}\n{req.reddit_post.get('body', '')}"
            plan = generate_reddit_rewrite_script(source_text, lang=req.language or "tr")
            plan["reddit_post"] = req.reddit_post
        else:
            fp = req.format_fingerprint
            if not fp:
                fp = extract_format_fingerprint_from_title(req.keyword or "")
            plan = generate_scenes(
                req.keyword,
                niche_type=locked_niche,
                language=req.language or config.LANGUAGE,
                format_fingerprint=fp,
            )
        plan["niche_id"] = locked_niche
        if req.format_fingerprint:
            plan["format_fingerprint"] = req.format_fingerprint
        plan["niche_profile"] = get_niche_production_profile(locked_niche)
        plan["topic_intelligence"] = topic_intel

        # P3-34: A/B hook variants in generate response
        hook_variants = get_niche_ab_variants(locked_niche)
        plan["hook_variants"] = hook_variants.get("variants", [])

        # Auto-fetch stock video candidates for each scene (Item 89 & 130)
        try:
            from routers.media_router import auto_fetch_videos_for_scenes
            if "scenes" in plan and plan["scenes"]:
                plan["scenes"] = auto_fetch_videos_for_scenes(plan["scenes"])
        except Exception as err:
            print(f"  [AutoStock] Note: {err}")

        config.LANGUAGE = old_lang

        validation = None
        plagiarism = None
        fair_use_notice = append_research_source_reference("", keyword=req.keyword or "").strip()
        try:
            from director.quality_gate import check_narration_integrity
            from scenes.enrichment import enrich_plan_scenes

            # P2-03: auto-repair first — quality gate helps, never blocks normal scripts
            plan_in = dict(plan)
            if plan_in.get("scenes"):
                plan_in = enrich_plan_scenes(plan_in, lang=req.language or config.LANGUAGE, niche_id=locked_niche)
            fixes: list = []
            repaired = False
            if plan_in.get("scenes"):
                plan_in, fixes, repaired = apply_auto_repair_if_needed(plan_in)
                if fixes:
                    plan = plan_in

            director = compile_director_plan(
                plan_in,
                title=req.keyword,
                niche_id=locked_niche,
                language=req.language or config.LANGUAGE,
                reddit_post=req.reddit_post,
            )
            plan = director.to_legacy_plan()
            integrity = check_narration_integrity(director)
            pre = pre_render_score(director)
            narr_block = list(integrity) + [
                i for i in pre.get("issues", [])
                if i.startswith("fragment") or i.startswith("low_words")
                or i.startswith("empty_narration") or i.startswith("no_terminal")
            ]
            validation = {
                "ok": not narr_block,
                "narration_ok": not narr_block,
                "repaired": repaired,
                "fixes": fixes,
                "narration_integrity": integrity,
                "pre_render_score": pre,
                "issues": narr_block,
            }
        except Exception as val_err:
            print(f"  [ScriptGenerate] Validation note: {val_err}")

        try:
            from plagiarism_checker import check_script_originality
            is_original, similarity, matched_title = check_script_originality(
                plan.get("full_narration", ""),
                keyword=req.keyword,
                title=plan.get("title", req.keyword),
                auto_add_if_approved=False,
            )
            plagiarism = {
                "approved": is_original,
                "similarity_pct": round(similarity * 100, 1),
                "matched_title": matched_title,
                "threshold_pct": 45,
            }
        except Exception as plag_err:
            print(f"  [ScriptGenerate] Plagiarism note: {plag_err}")

        ch_paths = config.channel_paths(getattr(req, "channel_id", None))

        return {
            "status": "ok",
            "plan": plan,
            "validation": validation,
            "hook_variants": hook_variants,
            "plagiarism": plagiarism,
            "fair_use_notice": fair_use_notice,
            "channel_paths": ch_paths,
            "topic_intelligence": topic_intel,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/research/reddit")
def get_reddit_posts(subreddit: str = "AITA", limit: int = 10, lang: str = None):
    """Fetches Reddit research posts with automatic discovery fallback (zero API key requirement)."""
    safe_subreddit = re.sub(r"[^A-Za-z0-9_]", "", subreddit) or "AITA"
    try:
        target_lang = lang or getattr(config, "LANGUAGE", "tr")
        posts = fetch_public_posts(safe_subreddit, limit, lang=target_lang)
        has_keys = bool(getattr(config, "REDDIT_CLIENT_ID", "") and getattr(config, "REDDIT_CLIENT_SECRET", ""))
        is_ai = bool(posts and posts[0].get("source") == "ai_discovery")
        mode = "oauth" if has_keys else ("ai_discovery" if is_ai else "viral_archive")
        msg = (
            "Resmi OAuth üzerinden çekildi." if mode == "oauth"
            else ("Yapay zeka ile anlık taze viral hikayeler keşfedildi." if mode == "ai_discovery"
                  else "Genişletilmiş viral arşiv rotasyonundan çekildi.")
        )
        return {
            "status": "ok",
            "posts": posts,
            "mode": mode,
            "message": msg
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
