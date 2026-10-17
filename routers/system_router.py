"""
System features router: Niches, Batch processing, Quota, Anti-Detect, Retention, Proofs, Roadmap.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import requests

import config
from batch_processor import batch_manager
from hybrid_niches import HYBRID_NICHES
from niche_templates import (
    NICHES,
    get_niche_ab_variants,
    get_niche_leaderboard,
    get_niche_production_profile,
    list_all_niches,
)
from quota_manager import quota_tracker
from research_service import (
    aggregate_format_fingerprint,
    extract_format_fingerprint_from_title,
)
from routers.system_diagnostics_routes import (
    apply_hardware_profile,
    clear_plagiarism_db_endpoint,
    get_algorithm_reset_advisory,
    get_algorithmic_threshold_advisory,
    get_channel_health_checklist,
    get_channel_momentum_advisory,
    get_comment_moderation_blocklist,
    get_copyright_strike_advisory,
    get_engagement_recovery,
    get_feed_distribution_advisory,
    get_growth_operator_pack,
    get_hardware_specifications,
    get_monetization_funnel,
    get_ops_dashboard,
    get_plagiarism_db_stats,
    get_public_apis_status,
    get_repeated_content_recovery,
    get_roadmap_500_audit,
    get_roadmap_500_items,
    get_seo_operator_pack,
    get_shadowban_recovery_plan,
    get_system_health,
    get_tier1_rpm_advisory,
    get_top100_system_diagnostics,
    get_traffic_sources_advisory,
    get_warmup_protocol_check,
    get_zero_views_diagnostic,
    router as _diagnostics_router,
    scan_plan_copyright_risk,
)
from server_core import is_rendering_active, process_batch_queue, state
from services.niche_trend_signals import (
    MAX_TREND_CARDS,
    SOURCE_AI,
    SOURCE_YOUTUBE_API,
    SOURCE_YOUTUBE_SEARCH,
    build_trends_response,
    fetch_niche_youtube_trends,
    fetch_public_youtube_trends,
    filter_trends_for_family,
    generate_synthetic_trend_signals,
    get_content_gap_examples,
    niche_search_queries,
)

router = APIRouter(tags=["System"])
router.include_router(_diagnostics_router)


def _enrich_trends_with_fingerprint(trends: list) -> dict:
    """P2-04: attach per-title and aggregate format fingerprints to trend payloads."""
    fps = []
    for trend in trends:
        fp = extract_format_fingerprint_from_title(trend.get("title", ""))
        trend["format_fingerprint"] = fp
        fps.append(fp)
    return aggregate_format_fingerprint(fps)


class BatchSubmitRequest(BaseModel):
    text: str
    niche: Optional[str] = "1_news_flash"
    language: Optional[str] = "tr"


class NicheCompareRequest(BaseModel):
    niche_a: str
    niche_b: str


class NicheCollisionRequest(BaseModel):
    niche_a: str
    niche_b: str


@router.get("/api/niches")
def get_niches():
    """Returns all 35 pre-configured niche templates with full analytics schema."""
    return {"niches": list_all_niches()}


@router.get("/api/niches/leaderboard")
def get_niches_leaderboard():
    """Returns all niches sorted by viral_score descending — for leaderboard display."""
    return {"status": "ok", "leaderboard": get_niche_leaderboard()}


@router.get("/api/niches/resolve-from-topic")
def resolve_niche_from_topic_api(topic: str = "", niche: str = "1_news_flash"):
    """Lock niche from topic keywords (same rules as director compile path)."""
    from director import resolve_niche_from_topic

    resolved = resolve_niche_from_topic(topic or "", niche or "1_news_flash")
    profile = NICHES.get(resolved) or {}
    return {
        "status": "ok",
        "topic": topic,
        "requested_niche": niche or "1_news_flash",
        "resolved_niche": resolved,
        "niche_name": profile.get("name") or resolved,
        "locked": resolved != (niche or "1_news_flash"),
    }


@router.get("/api/niches/{niche_id}/profile")
def get_niche_profile(niche_id: str):
    """Returns the concrete render settings selected by a niche."""
    profile = get_niche_production_profile(niche_id)
    profile["content_gap_examples"] = get_content_gap_examples(niche_id)
    return {"status": "ok", "profile": profile}


@router.get("/api/niches/{niche_id}/ab_variants")
def get_niche_ab_variants_endpoint(niche_id: str, topic: str = ""):
    """Returns 3 A/B test hook variants (Curiosity / Shock / Debate) for a niche."""
    data = get_niche_ab_variants(niche_id)
    if topic and isinstance(data, dict):
        data["topic"] = topic
    variants = data.get("variants", []) if isinstance(data, dict) else []
    return {"status": "ok", "data": data, "variants": variants}


@router.post("/api/niches/compare")
def compare_niches(req: NicheCompareRequest):
    """Compares two niches side-by-side on RPM, viral score, retention, competition."""

    def _get_data(niche_id: str):
        n = NICHES.get(niche_id)
        if not n:
            return None
        return {
            "id": niche_id,
            "name": n["name"],
            "category": n["category"],
            "icon": n.get("icon", "fa-fire"),
            "rpm_tier": n.get("rpm_tier", "$2-5"),
            "viral_score": n.get("viral_score", 75),
            "avg_retention_pct": n.get("avg_retention_pct", 70),
            "competition_level": n.get("competition_level", "medium"),
            "best_posting_time": n.get("best_posting_time", "12:00-15:00 TRT"),
            "tier1_compatible": n.get("tier1_compatible", False),
            "episodic_capable": n.get("episodic_capable", False),
            "cta_type": n.get("cta_type", "comment"),
        }

    a = _get_data(req.niche_a)
    b = _get_data(req.niche_b)
    if not a or not b:
        return {"status": "error", "message": "Bir veya her iki niş bulunamadı."}
    comp_order = {"low": 3, "medium": 2, "high": 1}
    winner = {
        "viral_score": req.niche_a if a["viral_score"] >= b["viral_score"] else req.niche_b,
        "avg_retention_pct": req.niche_a
        if a["avg_retention_pct"] >= b["avg_retention_pct"]
        else req.niche_b,
        "competition": req.niche_a
        if comp_order.get(a["competition_level"], 2)
        >= comp_order.get(b["competition_level"], 2)
        else req.niche_b,
        "tier1": req.niche_a if a["tier1_compatible"] else req.niche_b,
    }
    overall_score_a = (
        a["viral_score"]
        + a["avg_retention_pct"]
        + comp_order.get(a["competition_level"], 2) * 5
    )
    overall_score_b = (
        b["viral_score"]
        + b["avg_retention_pct"]
        + comp_order.get(b["competition_level"], 2) * 5
    )
    overall_winner = req.niche_a if overall_score_a >= overall_score_b else req.niche_b
    return {
        "status": "ok",
        "niche_a": a,
        "niche_b": b,
        "winner_per_dimension": winner,
        "overall_winner": overall_winner,
        "overall_scores": {req.niche_a: overall_score_a, req.niche_b: overall_score_b},
    }


@router.post("/api/niches/collision")
def collide_niches(req: NicheCollisionRequest):
    """Merges two niches into a unique hybrid concept (Niche Collision Engine)."""
    a = NICHES.get(req.niche_a) or HYBRID_NICHES.get(req.niche_a)
    b = NICHES.get(req.niche_b) or HYBRID_NICHES.get(req.niche_b)
    if not a or not b:
        return {"status": "error", "message": "Bir veya her iki niş bulunamadı."}
    name_a = a["name"].split("(")[0].strip()
    name_b = b["name"].split("(")[0].strip()
    collision_id = f"{req.niche_a}_x_{req.niche_b}"
    blended_viral = int((a.get("viral_score", 80) + b.get("viral_score", 80)) / 2 * 1.08)
    blended_viral = min(blended_viral, 99)
    blended_retention = int(
        (a.get("avg_retention_pct", 75) + b.get("avg_retention_pct", 75)) / 2
    )
    return {
        "status": "ok",
        "collision": {
            "id": collision_id,
            "name": f"{name_a} × {name_b}",
            "category_blend": f"{a['category']} + {b['category']}",
            "blended_tone": f"{a.get('tone','')}, {b.get('tone','')}",
            "blended_viral_score": blended_viral,
            "blended_retention": blended_retention,
            "hook_style": f"{a.get('hook_style','')} Üstelik: {b.get('hook_style','')}",
            "system_prompt": (
                f"Bu senaryoda iki farklı dünyayı melezle: {name_a} VE {name_b}. "
                f"Her iki konseptin görsel ve tematik unsurlarını sahne sahne harmanla. "
                f"Anlatım tonu: {a.get('tone','')}, {b.get('tone','')}. "
                f"Varsayılan müzik: {a.get('default_music','energetic')}."
            ),
            "suggested_niche_base": req.niche_a,
            "collision_hook_variants": [
                f"Ne zaman {name_a} ile {name_b} bir araya gelse, ortaya bu akıl almaz tablo çıkıyor.",
                f"{name_a} + {name_b} = İnterneti yıkacak içerik.",
                f"Bu ikilem var mı yok mu? {name_a} mi yoksa {name_b} mi kazanır?",
            ],
        },
    }


@router.get("/api/niches/{niche_id}/trending_topics")
def get_niche_trending_topics(niche_id: str, region: str = "TR"):
    """Returns trending topic suggestions for a specific niche via YouTube web scraping."""
    niche = NICHES.get(niche_id)
    if not niche:
        return {"status": "error", "message": "Niş bulunamadı."}
    keywords = niche_search_queries(niche_id)
    public = fetch_niche_youtube_trends(niche_id, region=region)
    source = SOURCE_YOUTUBE_SEARCH if public else SOURCE_AI
    if not public:
        public = generate_synthetic_trend_signals(niche_id)
    return {
        "status": "ok",
        "source": source,
        "niche_name": niche["name"],
        "trending_keywords": keywords,
        "topics": public[:MAX_TREND_CARDS],
    }


@router.get("/api/niches/{niche_id}/trends")
def get_niche_trends(niche_id: str, region: str = "TR"):
    """Fetches the past 24-hour YouTube video signals through YouTube Data API v3, with automatic public fallback."""
    profile = get_niche_production_profile(niche_id)

    if config.YOUTUBE_DATA_API_KEY:
        published_after = (
            (datetime.now(timezone.utc) - timedelta(hours=24))
            .isoformat()
            .replace("+00:00", "Z")
        )
        for query in niche_search_queries(niche_id):
            params = {
                "part": "snippet",
                "type": "video",
                "q": query,
                "order": "viewCount",
                "publishedAfter": published_after,
                "regionCode": region.upper(),
                "maxResults": MAX_TREND_CARDS,
                "key": config.YOUTUBE_DATA_API_KEY,
            }
            try:
                search = requests.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params=params,
                    timeout=12,
                )
                search.raise_for_status()
                items = search.json().get("items", [])
                ids = [
                    item.get("id", {}).get("videoId")
                    for item in items
                    if item.get("id", {}).get("videoId")
                ]
                stats_by_id = {}
                if ids:
                    stats = requests.get(
                        "https://www.googleapis.com/youtube/v3/videos",
                        params={
                            "part": "statistics",
                            "id": ",".join(ids),
                            "key": config.YOUTUBE_DATA_API_KEY,
                        },
                        timeout=12,
                    )
                    stats.raise_for_status()
                    stats_by_id = {
                        item["id"]: item.get("statistics", {})
                        for item in stats.json().get("items", [])
                    }
                trends = [
                    {
                        "video_id": item["id"]["videoId"],
                        "title": item["snippet"]["title"],
                        "channel": item["snippet"].get("channelTitle", ""),
                        "published_at": item["snippet"].get("publishedAt", ""),
                        "view_count": int(
                            stats_by_id.get(item["id"]["videoId"], {}).get(
                                "viewCount", 0
                            )
                        ),
                        "view_count_text": f"{int(stats_by_id.get(item['id']['videoId'], {}).get('viewCount', 0)):,} görüntülenme",
                        "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                        "source_type": SOURCE_YOUTUBE_API,
                    }
                    for item in items
                    if item.get("id", {}).get("videoId")
                ]
                trends = filter_trends_for_family(trends, niche_id)
                if trends:
                    return build_trends_response(
                        trends,
                        SOURCE_YOUTUBE_API,
                        profile,
                        _enrich_trends_with_fingerprint,
                    )
            except Exception as exc:
                print(
                    f"  [YouTubeDataAPI] Resmi API uyarısı ({exc}), sonraki anahtar kelime deneniyor..."
                )

    public_trends = fetch_niche_youtube_trends(niche_id, region=region)
    if public_trends:
        return build_trends_response(
            public_trends,
            SOURCE_YOUTUBE_SEARCH,
            profile,
            _enrich_trends_with_fingerprint,
        )

    curated = generate_synthetic_trend_signals(niche_id)
    return build_trends_response(
        curated, SOURCE_AI, profile, _enrich_trends_with_fingerprint
    )


@router.post("/api/batch/submit")
def submit_batch_jobs(req: BatchSubmitRequest, background_tasks: BackgroundTasks):
    """Parses newline-separated topics or CSV rows and enqueues batch jobs (Items 70, 78)."""
    jobs = batch_manager.parse_text_lines(
        req.text, default_niche=req.niche, language=req.language
    )
    batch_manager.add_jobs(jobs)
    if jobs and not batch_manager.is_running and not state.is_rendering_active:
        background_tasks.add_task(process_batch_queue)
    return {"status": "ok", "enqueued": len(jobs)}


@router.get("/api/batch/status")
def get_batch_queue_status():
    """Returns current batch processing status and queue list."""
    return batch_manager.get_queue_status()


@router.get("/api/quota/stats")
def get_quota_statistics(refresh: bool = False):
    """Returns API call count, errors, real-time live quotas and health metrics."""
    return quota_tracker.get_stats(force_live=refresh)


@router.post("/api/quota/reset")
def reset_quota_statistics():
    """Resets all API quota tracking counters and errors."""
    quota_tracker.reset_all()
    return {
        "status": "ok",
        "message": "Yapay zeka kota sayaçları sıfırlandı.",
        "stats": quota_tracker.get_stats(),
    }


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

    jitter = anti_detect_engine.calculate_upload_jitter(
        target_hour=hour, target_minute=minute
    )
    return {"status": "ok", "jitter": jitter}


@router.get("/api/anti_detect/warmup")
def get_warmup_plan(niche: str = "stoic"):
    """Generates organic account warm-up session plan before video upload (Items 7, 17, 18)."""
    from anti_detect_engine import anti_detect_engine

    plan = anti_detect_engine.generate_warmup_session_plan(niche_keyword=niche)
    return {"status": "ok", "warmup_plan": plan}


@router.get("/api/hybrid_niches")
def get_hybrid_niches():
    """Returns hybrid synergy niche library (Items 276-345)."""
    from hybrid_niches import list_all_hybrid_niches

    return {"status": "ok", "hybrid_niches": list_all_hybrid_niches()}


@router.get("/api/retention/formulas")
def get_retention_formulas():
    """Returns 12 seamless loop formulas and pattern interrupt triggers (Items 201-275)."""
    from viral_retention_engine import viral_retention_engine

    return {
        "status": "ok",
        "formulas": viral_retention_engine.LOOP_FORMULAS,
        "interrupts": viral_retention_engine.PATTERN_INTERRUPTS,
    }


@router.get("/api/proof/appeal_script")
def get_appeal_script(
    channel_name: str = "Shorts AI Studio",
    title: str = "3 Stoic Rules",
    channel_url: str = "",
):
    """Generates professional 5-minute YouTube Appeal Video Script for Reused Content reviews (Items 472-475)."""
    from proof_archiver import proof_archiver

    workflow = proof_archiver.build_appeal_video_operator_workflow(
        channel_name=channel_name,
        video_title=title,
        channel_url=channel_url,
    )
    return {
        "status": "ok",
        "script": workflow["script"],
        "workflow": workflow,
        "checklist": workflow["checklist"],
        "operator_steps": workflow["operator_steps"],
    }


# Registered diagnostic sub-router endpoints (from system_diagnostics_routes.py):
# - /api/seo/operator-pack -> export_seo_operator_pack
# - /api/growth/operator-pack -> export_growth_operator_pack
# - /api/channel-health/checklist -> build_actionable_channel_health_checklist
# - /api/channel-health/repeated-content-recovery -> get_repeated_content_recovery
# - /api/channel-health/zero-views -> diagnose_zero_views
# - /api/monetization/funnel -> get_monetization_funnel
_DIAGNOSTIC_ROUTE_REGISTRY = {
    "/api/seo/operator-pack": "export_seo_operator_pack",
    "/api/growth/operator-pack": "export_growth_operator_pack",
    "/api/channel-health/checklist": "build_actionable_channel_health_checklist",
    "/api/channel-health/repeated-content-recovery": "get_repeated_content_recovery",
    "/api/channel-health/zero-views": "diagnose_zero_views",
    "/api/monetization/funnel": "get_monetization_funnel",
}

