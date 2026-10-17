"""
Research, script generation, trending scanner, Reddit and RSS news router.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

import config
from api_models import (
    ContentGapResearchRequest,
    ScriptGenerateRequest,
    ScriptManuscriptRequest,
    ScriptTranslateRequest,
    SeriesPlanRequest,
    TopicSuggestRequest,
)
from director import compile_director_plan, pre_render_score
from director.visual_intent import resolve_topic_intelligence
from niche_templates import get_niche_ab_variants, get_niche_production_profile
from production.profiles import channel_profile
from production.quality import validate_script_quality
from reddit_client import fetch_public_posts
from research_service import (
    aggregate_format_fingerprint,
    build_content_gap_fingerprint,
    build_content_gap_suggestions,
    build_topic_research_brief,
    extract_format_fingerprint_from_title,
)
from routers.research_trends_routes import (
    DubbingApplyRequest,
    FactsGenerateRequest,
    PodcastGenerateRequest,
    RssConvertRequest,
    StyleProfileApplyRequest,
    SubtitleTranslateRequest,
    TopicTranslateRequest,
    ViralFlowTransformRequest,
    analyze_content_gaps,
    api_apply_dubbing,
    api_apply_style_profile,
    api_generate_facts_script,
    api_generate_podcast_debate,
    api_list_style_profiles,
    api_scan_trending,
    api_transform_viral_to_flow,
    api_translate_subtitles,
    api_translate_topic,
    convert_rss_to_shorts_endpoint,
    fetch_rss_news,
    get_reddit_posts,
    get_rss_sources,
    router as _trends_router,
)
from rss_scanner import (
    DEFAULT_RSS_FEEDS,
    get_breaking_news_topics,
    transform_rss_item_to_shorts_idea,
)
from scene_generator import generate_reddit_rewrite_script, generate_scenes
from scenes.generator import generate_series_outline
from scenes.narration_validate import (
    apply_auto_repair_if_needed,
    sanitize_plan_scene_descriptions,
)
from services.topic_suggester import suggest_topics
from trending_scanner import scan_youtube_shorts_trends
from viral_seo_agent import append_research_source_reference

router = APIRouter(tags=["Research"])
router.include_router(_trends_router)
logger = logging.getLogger(__name__)


def _is_nsfw_reddit_post(post: Optional[Dict[str, Any]]) -> bool:
    if not post:
        return False

    for marker in ("is_nsfw", "over_18"):
        value = post.get(marker)
        if value is True or (type(value) is int and value == 1):
            return True
        if isinstance(value, str) and value.strip().casefold() in {"1", "true", "yes"}:
            return True
    return False


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
            raise HTTPException(
                status_code=400, detail=result.get("message", "Niş bulunamadı.")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/series/plan", summary="Plan a connected Shorts series")
def api_plan_series(req: SeriesPlanRequest):
    """Return a validated episode outline for the Studio series planner."""
    try:
        outline = generate_series_outline(
            topic=req.topic,
            niche_type=req.niche or "1_news_flash",
            language=req.language or config.LANGUAGE,
            episode_count=req.episode_count,
        )
    except RuntimeError as error:
        logger.warning("Shorts series outline generation failed: %s", error)
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"status": "ok", "outline": outline}


@router.post("/api/script/translate")
def api_translate_script(req: ScriptTranslateRequest):
    """Translate a scene plan for another Studio language without changing its visuals."""
    source_lang = (
        str(req.plan.get("language") or req.plan.get("lang") or config.LANGUAGE)
        .strip()
        .lower()[:2]
    )
    target_lang = req.target_lang
    if source_lang not in {"tr", "en"}:
        raise HTTPException(
            status_code=422,
            detail="Senaryonun kaynak dili Türkçe veya İngilizce olmalı.",
        )
    if source_lang == target_lang:
        raise HTTPException(
            status_code=422, detail="Senaryo zaten seçili hedef dilde."
        )

    scenes = req.plan.get("scenes")
    if (
        not isinstance(scenes, list)
        or not scenes
        or any(not isinstance(scene, dict) for scene in scenes)
        or not any(
            str(scene.get("narration") or scene.get("text") or "").strip()
            for scene in scenes
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="Çevrilecek anlatım içeren sahneli bir senaryo gerekli.",
        )

    from services.dubbing import DubbingTranslationError, apply_dubbing_to_plan

    try:
        plan = apply_dubbing_to_plan(req.plan, target_lang=target_lang, strict=True)
    except DubbingTranslationError as err:
        logger.warning("Script translation failed: %s", err)
        raise HTTPException(status_code=502, detail=str(err)) from err
    return {"status": "ok", "plan": plan}


@router.post("/api/script/from-manuscript")
def api_script_from_manuscript(req: ScriptManuscriptRequest):
    """Split a provided manuscript into a scene plan while preserving its narration."""
    from services.manuscript_script import (
        ManuscriptSegmentationError,
        build_manuscript_plan,
    )
    from services.timed_visual_matcher import generate_timed_visual_queries

    try:
        plan = build_manuscript_plan(
            text=req.text,
            title=req.title,
            language=req.language,
            niche_id=req.niche or "1_news_flash",
        )
    except ManuscriptSegmentationError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err

    plan["scenes"] = generate_timed_visual_queries(
        plan["scenes"],
        niche_id=plan["niche_id"],
        force_local=True,
    )
    for scene in plan["scenes"]:
        queries = scene.get("search_queries") or []
        if queries:
            scene["scene_description"] = f"Visual footage of {queries[0]}."

    try:
        from routers.media_router import auto_fetch_videos_for_scenes

        is_mock_fetch = (
            hasattr(auto_fetch_videos_for_scenes, "_mock_name")
            or "unittest.mock" in type(auto_fetch_videos_for_scenes).__module__
            or getattr(auto_fetch_videos_for_scenes, "__module__", "") != "routers.media_router"
        )
        skip_live_stock = bool(
            os.environ.get("PYTEST_CURRENT_TEST")
            or os.environ.get("SHORTS_FORCE_PROCEDURAL_FALLBACK")
        ) and not is_mock_fetch
        if not skip_live_stock:
            plan["scenes"] = auto_fetch_videos_for_scenes(
                plan["scenes"],
                niche_id=plan["niche_id"],
            )
    except Exception as err:
        logger.warning("Manuscript stock-video search failed: %s", err)

    return {"status": "ok", "plan": plan}


@router.post("/api/script/generate")
def api_generate_script(req: ScriptGenerateRequest):
    if _is_nsfw_reddit_post(req.reddit_post):
        raise HTTPException(
            status_code=422,
            detail="NSFW Reddit posts cannot be used for script generation.",
        )

    old_lang = config.LANGUAGE
    try:
        if req.language:
            config.LANGUAGE = req.language
        requested_niche = (getattr(req, "niche", None) or "").strip()
        topic_intel = resolve_topic_intelligence(
            req.keyword or "", requested_niche or "1_news_flash"
        )
        locked_niche = topic_intel["resolved_niche"]
        continuity_context = (getattr(req, "continuity_context", None) or "").strip()
        reddit_post = getattr(req, "reddit_post", None)
        if continuity_context and reddit_post and locked_niche == "2_reddit_confessions":
            raise HTTPException(
                status_code=422,
                detail="Series continuity context is not supported for Reddit story rewrites.",
            )
        if reddit_post and locked_niche == "2_reddit_confessions":
            source_text = (
                f"{reddit_post.get('title', '')}\n{reddit_post.get('body', '')}"
            )
            plan = generate_reddit_rewrite_script(
                source_text, lang=req.language or "tr"
            )
            plan["reddit_post"] = reddit_post
        else:
            fp = req.format_fingerprint
            if not fp:
                fp = extract_format_fingerprint_from_title(req.keyword or "")
            var_attempt = int(getattr(req, "variation_attempt", 0) or 0)
            if getattr(req, "force_regenerate", False) and var_attempt == 0:
                var_attempt = 1
            plan = generate_scenes(
                req.keyword,
                niche_type=locked_niche,
                language=req.language or config.LANGUAGE,
                format_fingerprint=fp,
                variation_attempt=var_attempt,
                previous_narration=getattr(req, "previous_narration", None),
                continuity_context=continuity_context or None,
                force_regenerate=bool(getattr(req, "force_regenerate", False)),
                enable_outro=getattr(req, "enable_outro", True) is not False,
            )
        series_continuity = plan.get("series_continuity")
        plan["niche_id"] = locked_niche
        if req.format_fingerprint:
            plan["format_fingerprint"] = req.format_fingerprint
        plan["niche_profile"] = get_niche_production_profile(locked_niche)
        plan["topic_intelligence"] = topic_intel
        research_brief = build_topic_research_brief(
            req.keyword or "",
            niche_id=locked_niche,
            lang=req.language or config.LANGUAGE,
        )
        plan["research_brief"] = research_brief

        hook_variants = get_niche_ab_variants(locked_niche)
        plan["hook_variants"] = hook_variants.get("variants", [])

        try:
            from routers.media_router import auto_fetch_videos_for_scenes

            is_mock_fetch = (
                hasattr(auto_fetch_videos_for_scenes, "_mock_name")
                or "unittest.mock" in type(auto_fetch_videos_for_scenes).__module__
                or getattr(auto_fetch_videos_for_scenes, "__module__", "") != "routers.media_router"
            )
            skip_live_stock = bool(
                os.environ.get("PYTEST_CURRENT_TEST")
                or os.environ.get("SHORTS_FORCE_PROCEDURAL_FALLBACK")
            ) and not is_mock_fetch
            if not skip_live_stock and "scenes" in plan and plan["scenes"]:
                plan["scenes"] = auto_fetch_videos_for_scenes(
                    plan["scenes"],
                    niche_id=locked_niche,
                )
        except Exception as err:
            logger.warning("Automatic stock-video search failed: %s", err)

        config.LANGUAGE = old_lang

        validation = None
        plagiarism = None
        fair_use_notice = append_research_source_reference(
            "", keyword=req.keyword or ""
        ).strip()
        try:
            from director.quality_gate import check_narration_integrity
            from scenes.enrichment import enrich_plan_scenes

            plan_in = dict(plan)
            try:
                from craft import apply_human_craft

                plan_in = apply_human_craft(
                    plan_in,
                    title=req.keyword or "Video",
                    niche_id=locked_niche,
                    language=req.language or config.LANGUAGE,
                    variation=getattr(req, "variation_attempt", 0) or 0,
                )
            except Exception as hc_err:
                logger.warning(
                    "apply_human_craft skip in api_generate_script: %s", hc_err
                )

            try:
                from scenes.retention_hooks import ensure_retention_hooks_on_plan

                plan_in = ensure_retention_hooks_on_plan(
                    plan_in,
                    req.keyword or "Video",
                    lang=req.language or config.LANGUAGE,
                    niche_type=locked_niche,
                    variation_attempt=getattr(req, "variation_attempt", 0) or 0,
                    enable_outro=getattr(req, "enable_outro", True) is not False,
                )
            except Exception as hook_err:
                logger.warning(
                    "ensure_retention_hooks skip in api_generate_script: %s", hook_err
                )

            if plan_in.get("scenes"):
                plan_in = enrich_plan_scenes(
                    plan_in,
                    lang=req.language or config.LANGUAGE,
                    niche_id=locked_niche,
                )
                try:
                    from scenes.enrichment import enforce_specific_search_queries

                    enforce_specific_search_queries(plan_in["scenes"])
                except Exception:
                    pass

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
            plan["research_brief"] = research_brief
            integrity = check_narration_integrity(director)
            pre = pre_render_score(director)
            narr_block = list(integrity) + [
                i
                for i in pre.get("issues", [])
                if i.startswith("fragment")
                or i.startswith("low_words")
                or i.startswith("empty_narration")
                or i.startswith("no_terminal")
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
            logger.warning("Script validation failed: %s", val_err)

        try:
            from plagiarism_checker import check_script_originality

            is_original, similarity, matched_title = check_script_originality(
                plan.get("full_narration", ""),
                keyword=req.keyword,
                title=plan.get("title", req.keyword),
                auto_add_if_approved=False,
                channel_slug=config.channel_paths(getattr(req, "channel_id", None))[
                    "slug"
                ],
            )
            plagiarism = {
                "approved": is_original,
                "similarity_pct": round(similarity * 100, 1),
                "matched_title": matched_title,
                "threshold_pct": 35,
            }
        except Exception as plag_err:
            logger.warning("Script originality check failed: %s", plag_err)

        ch_paths = config.channel_paths(getattr(req, "channel_id", None))

        plan = sanitize_plan_scene_descriptions(plan or {})

        quality_profile = channel_profile(
            getattr(req, "channel_id", None) or "default",
            niche_id=locked_niche,
            language=req.language or config.LANGUAGE,
        ).to_dict()
        script_quality = validate_script_quality(plan, channel_profile=quality_profile)
        from production.script_repair import repair_script_quality_plan

        repair_result = repair_script_quality_plan(
            plan,
            script_quality,
            title=req.keyword,
            niche_id=locked_niche,
            language=req.language or config.LANGUAGE,
            channel_profile=quality_profile,
        )
        plan = repair_result["plan"]
        script_quality = repair_result["script_quality"]
        quality_repair = repair_result["quality_repair"]
        plan["research_brief"] = research_brief
        if series_continuity:
            plan["series_continuity"] = series_continuity

        plan.setdefault("meta", {})
        plan["meta"]["script_quality"] = script_quality
        plan["meta"]["render_allowed"] = bool(script_quality.get("ok"))
        plan["meta"]["script_quality_repair"] = quality_repair

        compliance = None
        viewer_score = None
        try:
            from compliance import evaluate_plan_compliance, publication_decision
            from compliance.viewer_score import compute_viewer_score

            compliance = evaluate_plan_compliance(plan)
            plan.setdefault("meta", {})
            viewer_score = compute_viewer_score(plan, compliance=compliance)
            plan["meta"]["publication"] = publication_decision(
                plan, compliance, viewer_score
            )
            plan["meta"]["viewer_score"] = viewer_score
            plan["meta"]["compliance"] = {
                "ok": compliance.get("ok"),
                "hard_fail": compliance.get("hard_fail"),
                "render_blocking": compliance.get("render_blocking"),
                "hard_fail_reasons": compliance.get("hard_fail_reasons"),
                "diagnosis": compliance.get("diagnosis"),
                "inauthentic": compliance.get("inauthentic"),
                "niche_gate": compliance.get("niche_gate"),
                "ai_disclosure": compliance.get("ai_disclosure"),
                "discovery_beast": compliance.get("discovery_beast"),
                "human_craft_reject": compliance.get("human_craft_reject"),
            }
            if plan.get("human_craft"):
                plan["meta"]["human_craft"] = plan["human_craft"]
            disc = (compliance.get("ai_disclosure") or {}).get("description_paragraph")
            if disc:
                plan["meta"]["ai_disclosure_text"] = disc
            if compliance.get("render_blocking"):
                logger.warning(
                    "Compliance hard fail: risk=%s verdict=%s craft=%s reasons=%s",
                    (compliance.get("inauthentic") or {}).get("risk"),
                    (compliance.get("inauthentic") or {}).get("verdict"),
                    compliance.get("human_craft_reason"),
                    compliance.get("hard_fail_reasons"),
                )
        except Exception as comp_err:
            logger.warning("Plan compliance evaluation failed: %s", comp_err)

        return {
            "status": "ok",
            "plan": plan,
            "validation": validation,
            "hook_variants": hook_variants,
            "plagiarism": plagiarism,
            "fair_use_notice": fair_use_notice,
            "channel_paths": ch_paths,
            "topic_intelligence": topic_intel,
            "viewer_score": viewer_score,
            "compliance": compliance,
            "script_quality": script_quality,
            "script_quality_repair": quality_repair,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        config.LANGUAGE = old_lang
