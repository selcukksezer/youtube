"""
System features router: Niches, Batch processing, Quota, Anti-Detect, Retention, Proofs, Roadmap.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import requests
import config
from niche_templates import (
    list_all_niches, get_niche_production_profile,
    get_niche_ab_variants, get_niche_leaderboard, NICHES
)
from batch_processor import batch_manager
from quota_manager import quota_tracker
from server_core import (
    is_rendering_active,
    process_batch_queue
)
from server_core import state
from hybrid_niches import HYBRID_NICHES
from research_service import extract_format_fingerprint_from_title, aggregate_format_fingerprint
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
def get_niche_ab_variants_endpoint(niche_id: str):
    """Returns 3 A/B test hook variants (Curiosity / Shock / Debate) for a niche."""
    return {"status": "ok", "data": get_niche_ab_variants(niche_id)}


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
    # Determine winner per dimension
    comp_order = {"low": 3, "medium": 2, "high": 1}
    winner = {
        "viral_score": req.niche_a if a["viral_score"] >= b["viral_score"] else req.niche_b,
        "avg_retention_pct": req.niche_a if a["avg_retention_pct"] >= b["avg_retention_pct"] else req.niche_b,
        "competition": req.niche_a if comp_order.get(a["competition_level"], 2) >= comp_order.get(b["competition_level"], 2) else req.niche_b,
        "tier1": req.niche_a if a["tier1_compatible"] else req.niche_b,
    }
    overall_score_a = a["viral_score"] + a["avg_retention_pct"] + comp_order.get(a["competition_level"], 2) * 5
    overall_score_b = b["viral_score"] + b["avg_retention_pct"] + comp_order.get(b["competition_level"], 2) * 5
    overall_winner = req.niche_a if overall_score_a >= overall_score_b else req.niche_b
    return {
        "status": "ok",
        "niche_a": a,
        "niche_b": b,
        "winner_per_dimension": winner,
        "overall_winner": overall_winner,
        "overall_scores": {req.niche_a: overall_score_a, req.niche_b: overall_score_b}
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
    blended_viral = int((a.get("viral_score", 80) + b.get("viral_score", 80)) / 2 * 1.08)  # 8% synergy bonus
    blended_viral = min(blended_viral, 99)
    blended_retention = int((a.get("avg_retention_pct", 75) + b.get("avg_retention_pct", 75)) / 2)
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
                f"Bu ikilem var mı yok mu? {name_a} mi yoksa {name_b} mi kazanır?"
            ]
        }
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

    # 1. Resmi YouTube Data API v3 (Anahtar tanımlıysa) — niche keywords first
    if config.YOUTUBE_DATA_API_KEY:
        published_after = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat().replace("+00:00", "Z")
        for query in niche_search_queries(niche_id):
            params = {
                "part": "snippet", "type": "video", "q": query, "order": "viewCount",
                "publishedAfter": published_after, "regionCode": region.upper(),
                "maxResults": MAX_TREND_CARDS, "key": config.YOUTUBE_DATA_API_KEY,
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
                        timeout=12,
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
                        "view_count_text": f"{int(stats_by_id.get(item['id']['videoId'], {}).get('viewCount', 0)):,} görüntülenme",
                        "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                        "source_type": SOURCE_YOUTUBE_API,
                    }
                    for item in items if item.get("id", {}).get("videoId")
                ]
                trends = filter_trends_for_family(trends, niche_id)
                if trends:
                    return build_trends_response(trends, SOURCE_YOUTUBE_API, profile, _enrich_trends_with_fingerprint)
            except Exception as exc:
                print(f"  [YouTubeDataAPI] Resmi API uyarısı ({exc}), sonraki anahtar kelime deneniyor...")

    # 2. Açık Web YouTube 24-Saat Arama Fallback'i (API Key Gerektirmez!)
    public_trends = fetch_niche_youtube_trends(niche_id, region=region)
    if public_trends:
        return build_trends_response(public_trends, SOURCE_YOUTUBE_SEARCH, profile, _enrich_trends_with_fingerprint)

    # 3. Nişe uygun AI/template önerileri — sahte kanal/görüntülenme yok
    curated = generate_synthetic_trend_signals(niche_id)
    return build_trends_response(curated, SOURCE_AI, profile, _enrich_trends_with_fingerprint)


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
def get_quota_statistics(refresh: bool = False):
    """Returns API call count, errors, real-time live quotas and health metrics."""
    return quota_tracker.get_stats(force_live=refresh)


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
        "interrupts": viral_retention_engine.PATTERN_INTERRUPTS
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


@router.get("/api/analytics/algorithmic-threshold")
def get_algorithmic_threshold_advisory(view_count: int = 0, swipe_rate_pct: Optional[float] = None):
    """Item 379: Algoritmik eşik analizi — YouTube Analytics API yok, advisory stub."""
    from proof_archiver import ProofArchiver
    from database import get_video_stats
    advisory = ProofArchiver.analyze_algorithmic_view_threshold(view_count, swipe_rate_pct)
    advisory["local_render_stats"] = get_video_stats()
    return {"status": "ok", "advisory": advisory}


@router.get("/api/analytics/feed-distribution")
def get_feed_distribution_advisory(swipe_rate_pct: float = 35.0, test_audience: int = 500):
    """Item 387: Feed dağıtım ivmesi — 500 kişi test kitlesi advisory stub."""
    from proof_archiver import ProofArchiver
    return {
        "status": "ok",
        "advisory": ProofArchiver.analyze_feed_distribution_phase(swipe_rate_pct, test_audience),
    }


@router.get("/api/analytics/traffic-sources")
def get_traffic_sources_advisory(
    shorts_feed_pct: float = 85.0,
    browse_features_pct: float = 8.0,
    external_pct: float = 5.0,
):
    """Items 406-409: Trafik kaynakları + haftalık analitik advisory stub."""
    from proof_archiver import ProofArchiver
    from database import get_video_stats
    advisory = ProofArchiver.analyze_traffic_sources(
        shorts_feed_pct, browse_features_pct, external_pct
    )
    advisory["local_render_stats"] = get_video_stats()
    return {"status": "ok", "advisory": advisory}


@router.get("/api/analytics/channel-momentum")
def get_channel_momentum_advisory(total_videos: int = 0, avg_views: int = 0):
    """Item 410: Sabır ve ivme eşiği — 30 video kalibrasyon advisory."""
    from proof_archiver import ProofArchiver
    from database import get_video_stats
    stats = get_video_stats()
    if total_videos <= 0:
        total_videos = int(stats.get("total_completed") or 0)
    advisory = ProofArchiver.get_channel_momentum_threshold(total_videos, avg_views)
    advisory["local_render_stats"] = stats
    return {"status": "ok", "advisory": advisory}


@router.get("/api/analytics/algorithm-reset")
def get_algorithm_reset_advisory(days_paused: int = 0):
    """Item 394/469: Algoritma resetleme dönemi — 4 gün duraklama rehberi."""
    from proof_archiver import ProofArchiver
    return {
        "status": "ok",
        "advisory": ProofArchiver.get_distribution_pause_guidance(days_paused),
    }


@router.get("/api/growth/operator-pack")
def get_growth_operator_pack(
    topic: str = "Stoacılık",
    title: str = "",
    user_comment: str = "",
    related_video_url: str = "",
    lang: str = "tr",
):
    """B5 growth deferred close-out: 311-322 + 384 operator pack (no auto-upload)."""
    from growth_tactics import export_growth_operator_pack

    pack = export_growth_operator_pack(
        topic=topic,
        title=title or topic,
        user_comment=user_comment,
        related_video_url=related_video_url,
        lang=lang,
    )
    return {"status": "ok", "operator_pack": pack}


@router.get("/api/channel-health/repeated-content-recovery")
def get_repeated_content_recovery(channel_name: str = "YourChannel", lang: str = "tr"):
    """Item 476: Reused content rejection — 30-day operator recovery plan."""
    from proof_archiver import ProofArchiver

    return {
        "status": "ok",
        "recovery": ProofArchiver.get_repeated_content_rejection_recovery_plan(
            channel_name=channel_name,
            lang=lang,
        ),
    }


@router.get("/api/seo/operator-pack")
def get_seo_operator_pack(
    keyword: str = "Stoacılık",
    title: str = "",
    target_country: str = "TR",
    lang: str = "tr",
):
    """B6 Batch 4: SEO operator pack — metadata + Studio paste fields (no auto-upload)."""
    from viral_seo_agent import export_seo_operator_pack
    from database import get_video_stats

    stats = get_video_stats()
    total = int(stats.get("total_completed") or 0)
    pack = export_seo_operator_pack(
        keyword=keyword,
        title=title or keyword,
        target_country=target_country,
        lang=lang,
        total_renders=total,
    )
    return {"status": "ok", "operator_pack": pack}


@router.get("/api/channel-health/checklist")
def get_channel_health_checklist(
    channel_age_days: int = 14,
    planned_daily_uploads: int = 1,
    hours_since_upload: float = 72.0,
    view_count: int = 0,
    strike_count: int = 0,
    niche: str = "Stoacılık",
    topic: str = "Zihin Disiplini",
    lang: str = "tr",
):
    """B8 Batch 4: Actionable kanal sağlığı checklist (466-500 in-scope advisory)."""
    from proof_archiver import ProofArchiver
    from database import get_video_stats

    stats = get_video_stats()
    total = int(stats.get("total_completed") or 0)
    data = ProofArchiver.build_actionable_channel_health_checklist(
        channel_age_days=channel_age_days,
        planned_daily_uploads=planned_daily_uploads,
        hours_since_upload=hours_since_upload,
        view_count=view_count,
        total_videos=total,
        strike_count=strike_count,
        niche=niche,
        topic=topic,
        lang=lang,
    )
    return {"status": "ok", **data}


@router.get("/api/channel-health/zero-views")
def get_zero_views_diagnostic(
    hours_since_upload: float = 72.0,
    view_count: int = 0,
    total_videos: int = 0,
):
    """Item 466: 0 izlenme teşhisi."""
    from proof_archiver import ProofArchiver
    from database import get_video_stats
    stats = get_video_stats()
    if total_videos <= 0:
        total_videos = int(stats.get("total_completed") or 0)
    return {
        "status": "ok",
        "diagnostic": ProofArchiver.diagnose_zero_views(
            hours_since_upload, view_count, total_videos
        ),
    }


@router.get("/api/channel-health/warmup")
def get_warmup_protocol_check(channel_age_days: int = 7, planned_daily_uploads: int = 1):
    """Item 467: 14 günlük kanal ısınma protokolü."""
    from proof_archiver import ProofArchiver
    return {"status": "ok", "warmup": ProofArchiver.check_warmup_protocol(channel_age_days, planned_daily_uploads)}


@router.get("/api/channel-health/engagement-recovery")
def get_engagement_recovery(hours_since_upload: float = 72.0, view_count: int = 0, total_videos: int = 0):
    """Item 468: Etkileşim kurtarma — metadata revizyon rehberi."""
    from proof_archiver import ProofArchiver
    return {
        "status": "ok",
        "advisory": ProofArchiver.get_engagement_recovery_guidance(
            hours_since_upload, view_count, total_videos
        ),
    }


@router.get("/api/channel-health/shadowban-recovery")
def get_shadowban_recovery_plan(days: int = 7):
    """Item 486: Gölge engelden çıkış egzersizi."""
    from proof_archiver import ProofArchiver
    return {"status": "ok", "plan": ProofArchiver.generate_shadowban_recovery_plan(days)}


@router.get("/api/channel-health/copyright-strikes")
def get_copyright_strike_advisory(strike_count: int = 0):
    """Item 484: Telif ihtarı yönetimi."""
    from proof_archiver import ProofArchiver
    return {"status": "ok", "advisory": ProofArchiver.get_copyright_strike_advisory(strike_count)}


@router.get("/api/channel-health/comment-blocklist")
def get_comment_moderation_blocklist(lang: str = "tr"):
    """Item 495: Studio engellenen kelimeler listesi."""
    from proof_archiver import ProofArchiver
    return {"status": "ok", "blocklist": ProofArchiver.get_comment_moderation_blocklist(lang)}


@router.get("/api/monetization/funnel")
def get_monetization_funnel(niche: str = "Stoacılık", topic: str = "Zihin Disiplini", lang: str = "tr"):
    """Items 477-478: Affiliate / dijital ürün funnel şablonu."""
    from proof_archiver import ProofArchiver
    return {"status": "ok", "funnel": ProofArchiver.generate_monetization_funnel(niche, topic, lang)}


@router.get("/api/monetization/tier1-rpm")
def get_tier1_rpm_advisory(target_country: str = "US"):
    """Item 481: Tier-1 ülke RPM çarpanı."""
    from proof_archiver import ProofArchiver
    return {"status": "ok", "advisory": ProofArchiver.get_tier1_rpm_multiplier(target_country)}


@router.get("/api/hardware/specs")
def get_hardware_specifications():
    """Detects CPU, RAM, NVIDIA GPU, and NVENC capabilities, offering tailor-made profiles."""
    from hardware_detector import get_system_hardware_specs
    specs = get_system_hardware_specs()
    specs["current_config"] = {
        "use_gpu": getattr(config, "USE_GPU_ACCELERATION", True),
        "gpu_codec": getattr(config, "GPU_CODEC", "h264_nvenc"),
        "render_threads": getattr(config, "RENDER_THREADS", 8),
        "fps_diversify": getattr(config, "FPS_DIVERSIFY", True),
        "resolution": getattr(config, "RENDER_RESOLUTION_MODE", "1080p"),
        "safe_mode": getattr(config, "RENDER_SAFE_MODE", True)
    }
    specs["resolution_options"] = [
        {"id": "1080p", "label": "1080x1920 (Full HD — YouTube Shorts Final)", "width": 1080, "height": 1920},
        {"id": "720p", "label": "720x1280 (Hızlı HD — 2.2x Daha Hızlı)", "width": 720, "height": 1280},
        {"id": "540p", "label": "540x960 (Ultra Hızlı Test — 4x Kat Daha Hızlı!)", "width": 540, "height": 960}
    ]
    return {"status": "ok", "specs": specs}


@router.post("/api/hardware/apply_profile")
def apply_hardware_profile(data: dict):
    """Applies automatic or manual hardware settings (GPU NVENC, CPU threads, FPS mode, Resolution, Safe Mode)."""
    profile = data.get("profile", "manual")
    threads = int(data.get("threads", getattr(config, "RENDER_THREADS", 8)))
    use_gpu = bool(data.get("use_gpu", True))
    gpu_codec = str(data.get("gpu_codec", "h264_nvenc"))
    fps_div = bool(data.get("fps_diversify", True))
    fixed_fps = float(data.get("fixed_fps", 30.0))
    resolution = str(data.get("resolution", getattr(config, "RENDER_RESOLUTION_MODE", "1080p")))
    if "safe_mode" in data:
        config.RENDER_SAFE_MODE = bool(data["safe_mode"])

    config.USE_GPU_ACCELERATION = use_gpu
    config.GPU_CODEC = gpu_codec
    config.RENDER_THREADS = threads
    config.FPS_DIVERSIFY = fps_div
    if not fps_div and fixed_fps > 0:
        config.FPS = fixed_fps
    if resolution in ("1080p", "720p", "540p"):
        config.RENDER_RESOLUTION_MODE = resolution

    # Persist directly into .env so choices remain after restarts
    try:
        from settings_service import _save_to_env_file
        _save_to_env_file()
    except Exception:
        pass

    res_dims = config.RESOLUTIONS.get(config.RENDER_RESOLUTION_MODE, (1080, 1920))
    mode_text = "Hızlı Güvenli Mod" if config.RENDER_SAFE_MODE else "Tam Kural (Tüm Efektler Aktif)"

    return {
        "status": "ok",
        "message": f"Donanım ve Render ayarları başarıyla kaydedildi! (GPU: {'h264_nvenc' if use_gpu else 'CPU libx264'}, Mod: {mode_text}, Çözünürlük: {config.RENDER_RESOLUTION_MODE} [{res_dims[0]}x{res_dims[1]}])",
        "current_config": {
            "use_gpu": config.USE_GPU_ACCELERATION,
            "gpu_codec": config.GPU_CODEC,
            "render_threads": config.RENDER_THREADS,
            "fps_diversify": config.FPS_DIVERSIFY,
            "fps": getattr(config, "FPS", 30.0),
            "resolution": config.RENDER_RESOLUTION_MODE,
            "safe_mode": config.RENDER_SAFE_MODE
        }
    }


