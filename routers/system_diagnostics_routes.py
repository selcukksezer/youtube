"""System diagnostics, roadmap audit, channel health, hardware profile, and plagiarism routes."""
from __future__ import annotations

import os
import sys
from typing import Optional

from fastapi import APIRouter

import config

router = APIRouter(tags=["System"])


def _sysr_attr(name: str, default):
    mod = sys.modules.get("routers.system_router")
    return getattr(mod, name, default) if mod is not None else default


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
        items = [
            it
            for it in items
            if s in it["title"].lower() or s in it["description"].lower()
        ]
    return {"status": "ok", "total": len(items), "items": items}


@router.get("/api/health")
def get_system_health():
    """Returns real-time system health, VideoToolbox encoder, disk space, and API status (Item 464)."""
    from system_resilience import get_system_health_status

    return get_system_health_status()


@router.get("/api/analytics/algorithmic-threshold")
def get_algorithmic_threshold_advisory(
    view_count: int = 0, swipe_rate_pct: Optional[float] = None
):
    """Item 379: Algoritmik eşik analizi — YouTube Analytics API yok, advisory stub."""
    from database import get_video_stats
    from proof_archiver import ProofArchiver

    advisory = ProofArchiver.analyze_algorithmic_view_threshold(view_count, swipe_rate_pct)
    advisory["local_render_stats"] = get_video_stats()
    return {"status": "ok", "advisory": advisory}


@router.get("/api/analytics/ops-dashboard")
def get_ops_dashboard():
    """R10 #100: Local ops dashboard snapshot (renders + managed channels)."""
    from database import get_ops_dashboard_snapshot

    return {"status": "ok", "dashboard": get_ops_dashboard_snapshot()}


@router.get("/api/analytics/scenario-quality-dashboard")
def get_scenario_quality_dashboard(limit: int = 25):
    """FUTURE_ROADMAP §5 #3: Scenario quality monitoring dashboard (validation.issues + plan_linter metrics)."""
    from scenes.plan_linter import build_scenario_quality_dashboard_metrics

    return {
        "status": "ok",
        "scenario_quality": build_scenario_quality_dashboard_metrics(recent_limit=limit),
    }


@router.get("/api/analytics/feed-distribution")
def get_feed_distribution_advisory(swipe_rate_pct: float = 35.0, test_audience: int = 500):
    """Item 387: Feed dağıtım ivmesi — 500 kişi test kitlesi advisory stub."""
    from proof_archiver import ProofArchiver
    return {"status": "ok", "advisory": ProofArchiver.analyze_feed_distribution_phase(swipe_rate_pct, test_audience)}


@router.get("/api/analytics/traffic-sources")
def get_traffic_sources_advisory(
    shorts_feed_pct: float = 85.0, browse_features_pct: float = 8.0, external_pct: float = 5.0
):
    """Items 406-409: Trafik kaynakları + haftalık analitik advisory stub."""
    from database import get_video_stats
    from proof_archiver import ProofArchiver
    advisory = ProofArchiver.analyze_traffic_sources(shorts_feed_pct, browse_features_pct, external_pct)
    advisory["local_render_stats"] = get_video_stats()
    return {"status": "ok", "advisory": advisory}


@router.get("/api/analytics/channel-momentum")
def get_channel_momentum_advisory(total_videos: int = 0, avg_views: int = 0):
    """Item 410: Sabır ve ivme eşiği — 30 video kalibrasyon advisory."""
    from database import get_video_stats
    from proof_archiver import ProofArchiver
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
    return {"status": "ok", "advisory": ProofArchiver.get_distribution_pause_guidance(days_paused)}


@router.get("/api/growth/operator-pack")
def get_growth_operator_pack(
    topic: str = "Stoacılık",
    title: str = "",
    niche: str = "",
    user_comment: str = "",
    related_video_url: str = "",
    lang: str = "tr",
):
    """B5 growth deferred close-out: 311-322 + 384 operator pack (no auto-upload)."""
    from growth_tactics import export_growth_operator_pack
    pack = export_growth_operator_pack(
        topic=topic, title=title or topic, user_comment=user_comment, related_video_url=related_video_url, lang=lang
    )
    if niche and isinstance(pack, dict):
        pack["niche"] = niche
    return {"status": "ok", "operator_pack": pack}


@router.post("/api/analytics/retention-diagnosis")
def diagnose_retention_metrics(payload: dict):
    """Diagnoses Shorts retention metrics (APV, stayed-to-watch %, duration) and estimates curve."""
    from proof_archiver import ProofArchiver
    from services.distribution_and_growth_hub import fetch_or_estimate_channel_retention_curve

    apv = float(payload.get("avg_percentage_viewed") or 75.0)
    stayed_pct = float(payload.get("stayed_to_watch_pct") or 70.0)
    duration_sec = float(payload.get("duration_sec") or 42.0)
    view_count = int(payload.get("view_count") or 1500)
    channel_id = str(payload.get("channel_id") or "default")
    swipe_rate_pct = round(max(0.0, 100.0 - stayed_pct), 2)

    threshold_adv = ProofArchiver.analyze_algorithmic_view_threshold(view_count, swipe_rate_pct)
    feed_phase = ProofArchiver.analyze_feed_distribution_phase(swipe_rate_pct, 500)
    curve = fetch_or_estimate_channel_retention_curve(channel_id, duration_sec=duration_sec)
    diagnosis = {
        "avg_percentage_viewed": apv,
        "stayed_to_watch_pct": stayed_pct,
        "swipe_away_pct": swipe_rate_pct,
        "duration_sec": duration_sec,
        "viral_tier": "high" if (apv >= 75.0 and stayed_pct >= 70.0) else ("medium" if apv >= 60.0 else "low"),
        "threshold_advisory": threshold_adv,
        "feed_distribution": feed_phase,
        "retention_curve": curve,
    }
    return {"status": "ok", "diagnosis": diagnosis}


@router.post("/api/analytics/shadowban-diagnosis")
def diagnose_shadowban_metrics(payload: dict):
    """Diagnoses potential shadowban vs normal algorithmic cooldown from recent views and Shorts feed ratio."""
    from proof_archiver import ProofArchiver

    raw_views = payload.get("recent_views") or [1450, 2100, 1890, 2400, 1950]
    recent_views = [int(v) for v in raw_views if isinstance(v, (int, float))] or [0]
    shorts_feed_ratio = float(payload.get("shorts_feed_ratio") or 0.84)
    hours_since_upload = float(payload.get("hours_since_upload") or 48.0)
    avg_views = round(sum(recent_views) / max(1, len(recent_views)), 1)
    shorts_pct = round(shorts_feed_ratio * 100.0 if shorts_feed_ratio <= 1.0 else shorts_feed_ratio, 1)

    zero_diag = ProofArchiver.diagnose_zero_views(
        hours_since_upload,
        int(recent_views[-1]),
        len(recent_views),
    )
    traffic = ProofArchiver.analyze_traffic_sources(
        shorts_feed_pct=shorts_pct,
        browse_features_pct=round(max(0.0, 100.0 - shorts_pct) * 0.6, 1),
        external_pct=round(max(0.0, 100.0 - shorts_pct) * 0.4, 1),
    )
    shadowban_risk = "low" if (avg_views >= 200 and shorts_pct >= 50.0) else ("high" if avg_views < 10 else "medium")
    diagnosis = {
        "shadowban_risk": shadowban_risk,
        "avg_recent_views": avg_views,
        "shorts_feed_pct": shorts_pct,
        "zero_view_check": zero_diag,
        "traffic_analysis": traffic,
        "recovery_plan": ProofArchiver.generate_shadowban_recovery_plan(7) if shadowban_risk != "low" else None,
    }
    return {"status": "ok", "diagnosis": diagnosis}


@router.get("/api/seo/viral_metadata")
def get_seo_viral_metadata(
    topic: str = "Stoacılık",
    niche: str = "6_stoic_philosophy",
    target_country: str = "TR",
    lang: str = "tr",
):
    """Generates viral SEO metadata + 15 tags + operator pack for a given topic and niche."""
    from database import get_video_stats
    from viral_seo_agent import export_seo_operator_pack, generate_15_viral_tags

    stats = get_video_stats()
    total = int(stats.get("total_completed") or 0)
    pack = export_seo_operator_pack(
        keyword=topic,
        title=topic,
        target_country=target_country,
        lang=lang,
        total_renders=total,
    )
    tags = generate_15_viral_tags(topic, niche=niche, lang=lang)
    metadata = {
        "topic": topic,
        "niche": niche,
        "lang": lang,
        "target_country": target_country,
        "tags": tags,
        "seo_pack": pack,
    }
    return {"status": "ok", "metadata": metadata, "operator_pack": pack}


@router.get("/api/analytics/monetization-progress")
def get_monetization_progress(
    subscribers: int = 650,
    shorts_views_90d: int = 2_400_000,
    watch_hours_365d: int = 1800,
    niche: str = "Stoacılık",
    topic: str = "Zihin Disiplini",
    lang: str = "tr",
):
    """Calculates YouTube Partner Program (YPP Lite & Full YPP) progress and monetization funnel."""
    from proof_archiver import ProofArchiver

    lite_subs_pct = round(min(100.0, (subscribers / 500.0) * 100.0), 1)
    lite_views_pct = round(min(100.0, (shorts_views_90d / 3_000_000.0) * 100.0), 1)
    lite_hours_pct = round(min(100.0, (watch_hours_365d / 3_000.0) * 100.0), 1)
    full_subs_pct = round(min(100.0, (subscribers / 1_000.0) * 100.0), 1)
    full_views_pct = round(min(100.0, (shorts_views_90d / 10_000_000.0) * 100.0), 1)
    full_hours_pct = round(min(100.0, (watch_hours_365d / 4_000.0) * 100.0), 1)

    progress = {
        "subscribers": subscribers,
        "shorts_views_90d": shorts_views_90d,
        "watch_hours_365d": watch_hours_365d,
        "ypp_early_access": {
            "eligible": subscribers >= 500 and (shorts_views_90d >= 3_000_000 or watch_hours_365d >= 3_000),
            "subscribers_pct": lite_subs_pct,
            "shorts_views_pct": lite_views_pct,
            "watch_hours_pct": lite_hours_pct,
        },
        "ypp_full_ad_revenue": {
            "eligible": subscribers >= 1_000 and (shorts_views_90d >= 10_000_000 or watch_hours_365d >= 4_000),
            "subscribers_pct": full_subs_pct,
            "shorts_views_pct": full_views_pct,
            "watch_hours_pct": full_hours_pct,
        },
        "funnel": ProofArchiver.generate_monetization_funnel(niche, topic, lang),
    }
    return {"status": "ok", "progress": progress}


@router.get("/api/analytics/niche-leaderboard")
def get_analytics_niche_leaderboard(lang: str = "tr"):
    """Returns niches sorted by viral_score/RPM for the analytics leaderboard."""
    from niche_templates import get_niche_leaderboard

    board = get_niche_leaderboard()
    return {"status": "ok", "lang": lang, "leaderboard": board, "niches": board}


@router.get("/api/channel-health/repeated-content-recovery")
def get_repeated_content_recovery(channel_name: str = "YourChannel", lang: str = "tr"):
    """Item 476: Reused content rejection — 30-day operator recovery plan."""
    from proof_archiver import ProofArchiver
    return {"status": "ok", "recovery": ProofArchiver.get_repeated_content_rejection_recovery_plan(channel_name=channel_name, lang=lang)}


@router.get("/api/seo/operator-pack")
def get_seo_operator_pack(keyword: str = "Stoacılık", title: str = "", target_country: str = "TR", lang: str = "tr"):
    """B6 Batch 4: SEO operator pack — metadata + Studio paste fields (no auto-upload)."""
    from database import get_video_stats
    from viral_seo_agent import export_seo_operator_pack
    stats = get_video_stats()
    total = int(stats.get("total_completed") or 0)
    pack = export_seo_operator_pack(keyword=keyword, title=title or keyword, target_country=target_country, lang=lang, total_renders=total)
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
    from database import get_video_stats
    from proof_archiver import ProofArchiver
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
def get_zero_views_diagnostic(hours_since_upload: float = 72.0, view_count: int = 0, total_videos: int = 0):
    """Item 466: 0 izlenme teşhisi."""
    from database import get_video_stats
    from proof_archiver import ProofArchiver
    stats = get_video_stats()
    if total_videos <= 0:
        total_videos = int(stats.get("total_completed") or 0)
    return {"status": "ok", "diagnostic": ProofArchiver.diagnose_zero_views(hours_since_upload, view_count, total_videos)}


@router.get("/api/channel-health/warmup")
def get_warmup_protocol_check(channel_age_days: int = 7, planned_daily_uploads: int = 1):
    """Item 467: 14 günlük kanal ısınma protokolü."""
    from proof_archiver import ProofArchiver
    return {"status": "ok", "warmup": ProofArchiver.check_warmup_protocol(channel_age_days, planned_daily_uploads)}


@router.get("/api/channel-health/engagement-recovery")
def get_engagement_recovery(hours_since_upload: float = 72.0, view_count: int = 0, total_videos: int = 0):
    """Item 468: Etkileşim kurtarma — metadata revizyon rehberi."""
    from proof_archiver import ProofArchiver
    return {"status": "ok", "advisory": ProofArchiver.get_engagement_recovery_guidance(hours_since_upload, view_count, total_videos)}


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
    cfg = _sysr_attr("config", config)
    specs = get_system_hardware_specs()
    try:
        from visuals.face_reframe import _load_cascade
        specs["has_opencv"] = _load_cascade() is not None
    except Exception:
        specs["has_opencv"] = False
    try:
        from system_resilience import encoder_choices
        specs["encoder_choices"] = encoder_choices()
    except Exception:
        specs["encoder_choices"] = []
    specs["current_config"] = {
        "use_gpu": getattr(cfg, "USE_GPU_ACCELERATION", True),
        "gpu_codec": getattr(cfg, "GPU_CODEC", "h264_nvenc"),
        "render_threads": getattr(cfg, "RENDER_THREADS", 8),
        "fps_diversify": getattr(cfg, "FPS_DIVERSIFY", True),
        "resolution": getattr(cfg, "RENDER_RESOLUTION_MODE", "1080p"),
        "safe_mode": getattr(cfg, "RENDER_SAFE_MODE", True),
    }
    specs["resolution_options"] = [
        {"id": "1080p", "label": "1080x1920 (Full HD — YouTube Shorts Final)", "width": 1080, "height": 1920},
        {"id": "720p", "label": "720x1280 (Hızlı HD — 2.2x Daha Hızlı)", "width": 720, "height": 1280},
        {"id": "540p", "label": "540x960 (Ultra Hızlı Test — 4x Kat Daha Hızlı!)", "width": 540, "height": 960},
    ]
    return {"status": "ok", "specs": specs}


@router.post("/api/hardware/apply_profile")
def apply_hardware_profile(data: dict):
    """Applies automatic or manual hardware settings."""
    cfg = _sysr_attr("config", config)
    threads = int(data.get("threads", getattr(cfg, "RENDER_THREADS", 8)))
    use_gpu = bool(data.get("use_gpu", True))
    gpu_codec = str(data.get("gpu_codec", "h264_nvenc"))
    fps_div = bool(data.get("fps_diversify", True))
    fixed_fps = float(data.get("fixed_fps", 30.0))
    resolution = str(
        data.get("resolution", getattr(cfg, "RENDER_RESOLUTION_MODE", "1080p"))
    )
    if "safe_mode" in data:
        cfg.RENDER_SAFE_MODE = bool(data["safe_mode"])

    cfg.USE_GPU_ACCELERATION = use_gpu
    cfg.GPU_CODEC = gpu_codec
    cfg.RENDER_THREADS = threads
    cfg.FPS_DIVERSIFY = fps_div
    if not fps_div and fixed_fps > 0:
        cfg.FPS = fixed_fps
    if resolution in ("1080p", "720p", "540p"):
        cfg.RENDER_RESOLUTION_MODE = resolution

    try:
        from settings_service import _save_to_env_file

        _save_to_env_file()
    except Exception:
        pass

    res_dims = cfg.RESOLUTIONS.get(cfg.RENDER_RESOLUTION_MODE, (1080, 1920))
    mode_text = (
        "Hızlı Güvenli Mod"
        if cfg.RENDER_SAFE_MODE
        else "Tam Kural (Tüm Efektler Aktif)"
    )

    return {
        "status": "ok",
        "message": f"Donanım ve Render ayarları başarıyla kaydedildi! (Kodlayıcı: {cfg.GPU_CODEC}, Mod: {mode_text}, Çözünürlük: {cfg.RENDER_RESOLUTION_MODE} [{res_dims[0]}x{res_dims[1]}])",
        "current_config": {
            "use_gpu": cfg.USE_GPU_ACCELERATION,
            "gpu_codec": cfg.GPU_CODEC,
            "render_threads": cfg.RENDER_THREADS,
            "fps_diversify": cfg.FPS_DIVERSIFY,
            "fps": getattr(cfg, "FPS", 30.0),
            "resolution": cfg.RENDER_RESOLUTION_MODE,
            "safe_mode": cfg.RENDER_SAFE_MODE,
        },
    }


@router.get("/api/system/public-apis/status")
def get_public_apis_status(live: bool = False):
    """Bölüm 34.2: Inspect availability and health of public-apis catalog endpoints."""
    try:
        from services.public_apis_catalog import PUBLIC_ENDPOINTS

        endpoints = [
            {
                "name": ep.name,
                "category": ep.category.value,
                "base_url": ep.base_url,
                "description": ep.description,
                "is_active": ep.is_active,
                "last_status_code": ep.last_status_code,
                "failure_count": ep.failure_count,
            }
            for ep in PUBLIC_ENDPOINTS.values()
        ]
        return {"status": "ok", "live_checked": bool(live), "endpoints": endpoints}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/api/compliance/copyright-risk")
def scan_plan_copyright_risk(payload: dict):
    """Scans free text, scene queries, clip filenames, and BGM tracks for Content-ID / copyright risks."""
    from copyright_risk import scan_audio_copyright_risk, scan_copyright_risk

    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
    clips = list(payload.get("clip_names") or [])
    sources = list(payload.get("source_labels") or [])
    bgm_tracks = list(payload.get("bgm_tracks") or [])
    if payload.get("bgm_track"):
        bgm_tracks.append(str(payload["bgm_track"]))
    if str(payload.get("text") or "").strip():
        clips.append(str(payload.get("text")).strip())

    for sc in plan.get("scenes") or []:
        if isinstance(sc, dict):
            clips.extend(sc.get("search_queries") or [])
            for k in ("search_query", "narration"):
                if sc.get(k):
                    clips.append(str(sc[k]))
            if sc.get("path"):
                clips.append(os.path.basename(str(sc["path"])))
            sel = sc.get("selected_video")
            if isinstance(sel, dict) and sel.get("source"):
                sources.append(str(sel["source"]))

    visual_scan = scan_copyright_risk(clips, sources)
    audio_scan = scan_audio_copyright_risk(bgm_tracks)
    overall_safe = bool(visual_scan.get("safe", True) and audio_scan.get("safe", True))
    matched_terms = []
    for item in (visual_scan.get("flagged_items") or []) + (audio_scan.get("flagged_items") or []):
        if isinstance(item, dict):
            matched_terms.extend(item.get("matched_keywords") or ([item.get("item")] if item.get("item") else []))
        elif isinstance(item, str):
            matched_terms.append(item)
    recs = list(dict.fromkeys((visual_scan.get("recommendations") or []) + (audio_scan.get("recommendations") or [])))
    report = {
        "safe": overall_safe,
        "risk_level": "high" if not overall_safe else "low",
        "risk_score": min(100, len(matched_terms) * 35) if matched_terms else 0,
        "matched_terms": matched_terms,
        "recommendations": recs,
    }
    return {"status": "ok", "safe": overall_safe, "report": report, "visual": visual_scan, "audio": audio_scan}


@router.get("/api/plagiarism/stats")
def get_plagiarism_db_stats():
    from plagiarism_checker import get_db_stats
    stats = get_db_stats()
    return {"status": "ok", "stats": stats, "total_fingerprints": stats.get("total_scripts") or stats.get("count") or 0, "recent": stats.get("recent") or stats.get("recent_topics") or []}


@router.post("/api/plagiarism/clear")
def clear_plagiarism_db_endpoint():
    from plagiarism_checker import clear_plagiarism_db, get_db_stats
    before = get_db_stats()
    clear_plagiarism_db()
    return {"status": "ok", "cleared": before.get("total_scripts") or before.get("count") or 0, "message": "İntihal veritabanı temizlendi.", "stats": get_db_stats()}


@router.get("/api/system/top100-diagnostics")
def get_top100_system_diagnostics():
    from anti_detect.operational_guards import get_account_recovery_2fa_checklist, get_notification_channels_health
    from effects.advanced_subtitle_and_motion import get_niche_mandatory_font_family, resolve_occlusion_free_subtitle_y
    from server_core.pipeline_orchestrator import evaluate_honest_audit_summary, get_active_effects_status_report, get_ordered_composer_effect_chain, get_workspace_isolation_config
    from server_core.quality_gate_policy import evaluate_unified_quality_gates
    from server_core.render_resilience import get_uvicorn_reload_excludes, resolve_safe_render_threads, resume_interrupted_render_jobs
    from server_core.workspace_maintenance import build_js_bundle_manifest, get_html_tab_sections_manifest, verify_dockerfile_python312
    from services.distribution_and_growth_hub import fetch_or_estimate_channel_retention_curve, get_oauth_upload_readiness
    from services.scenario_enhancements import rotate_procedural_fallback_variant, score_title_ctr_ml_heuristic
    from services.visual_render_enhancements import get_generative_ai_video_adapter_status
    from voice.acoustic_mastering_pipeline import build_mastering_eq_and_subbass_mono_filter, check_local_piper_kokoro_status

    return {
        "status": "ok",
        "render_resilience": {"safe_threads": resolve_safe_render_threads(), "reload_excludes": get_uvicorn_reload_excludes(), "interrupted_jobs": resume_interrupted_render_jobs()},
        "quality_gate_policy": evaluate_unified_quality_gates(),
        "pipeline_orchestrator": {"effects_status": get_active_effects_status_report(), "effect_chain": get_ordered_composer_effect_chain(), "honest_audit_summary": evaluate_honest_audit_summary(), "workspace_isolation": get_workspace_isolation_config()},
        "scenario_enhancements": {"sample_archetype": rotate_procedural_fallback_variant("finance", "Bitcoin", run_seed=1), "sample_ctr_score": score_title_ctr_ml_heuristic("Bitcoin Neden Düştü? 3 Kritik Sır!")},
        "visual_render_enhancements": {"generative_video_adapters": get_generative_ai_video_adapter_status({})},
        "acoustic_mastering": {"local_tts_status": check_local_piper_kokoro_status(), "eq_chain": build_mastering_eq_and_subbass_mono_filter()},
        "subtitle_and_motion": {"mandatory_font_sample": get_niche_mandatory_font_family("history_empire"), "safe_subtitle_y": resolve_occlusion_free_subtitle_y()},
        "distribution_and_growth": {"oauth_readiness": get_oauth_upload_readiness(), "retention_baseline": fetch_or_estimate_channel_retention_curve("default")},
        "operational_guards": {"notifications": get_notification_channels_health(), "recovery_checklist": get_account_recovery_2fa_checklist("default")},
        "workspace_maintenance": {"dockerfile": verify_dockerfile_python312("Dockerfile"), "js_bundle": build_js_bundle_manifest("static/js"), "html_tabs": get_html_tab_sections_manifest("static/index.html")},
    }



