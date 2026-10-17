"""
Video pipeline, SSE events, plan validation/repair, and render status core router.
Gallery, timeline asset prep, and creative tool routes live in modular sub-routers
(`video_gallery_routes`, `video_timeline_routes`, `video_tools_routes`) and are
included + re-exported here for full backward compatibility.
"""
import asyncio
import logging
import subprocess
from typing import Optional

import imageio_ffmpeg
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

import config
from api_models import PlanRepairRequest, PlanValidateRequest, VideoRenderRequest
from production.quality import validate_scene_durations, validate_script_quality
from scenes.narration_validate import sanitize_plan_scene_descriptions
from server_core import (
    broadcast_event,
    current_render_state,
    event_queues,
    is_rendering_active,
    process_video_task,
    render_lock,
    state,
)

from .video_gallery_routes import (
    _VERIFIED_VIDEO_PROBES,
    _gallery_thumbnail_cache_key,
    _quality_gate_summary_for_filename,
    api_get_video_thumbnail,
    api_get_videos,
    delete_video,
    get_database_videos,
    get_gallery,
    router as gallery_router,
    video_share_decision,
)
from .video_timeline_routes import (
    _sanitize_project_slug,
    api_prepare_timeline_assets,
    api_replace_scene_media,
    get_latest_project_plan,
    get_project_plan,
    normalize_scene_paths_for_web,
    router as timeline_router,
)
from .video_tools_routes import (
    api_audit_script_virality,
    api_clipper_analyze,
    api_clipper_render,
    api_grounding_audit,
    api_helios_enhance_scenes,
    api_helios_prompt,
    api_punch_in_curve,
    api_refine_video_title_idea,
    api_speaker_layout,
    router as tools_router,
)

router = APIRouter(tags=["Video"])
logger = logging.getLogger(__name__)


@router.post("/api/video/render")
def api_render_video(req: VideoRenderRequest, background_tasks: BackgroundTasks):
    if req.enable_sonilo_sfx and not str(getattr(config, "SONILO_API_KEY", "") or "").strip():
        raise HTTPException(
            status_code=400,
            detail="AI Görüntü SFX için Ayarlar bölümünde Sonilo API Key tanımlayın.",
        )
    quality_repair = None
    if req.plan is not None:
        script_quality = validate_script_quality(req.plan)
        from production.script_repair import repair_script_quality_plan

        repair_result = repair_script_quality_plan(
            req.plan,
            script_quality,
            title=req.keyword,
            niche_id=req.niche or req.plan.get("niche_id") or "1_news_flash",
            language=req.language or "tr",
        )
        quality_repair = repair_result["quality_repair"]
        if quality_repair["status"] in ("repaired", "partially_repaired"):
            req.plan = repair_result["plan"]
            req.keyword = req.plan.get("title") or req.keyword
            script_quality = repair_result["script_quality"]
            req.plan.setdefault("meta", {})
            req.plan["meta"]["script_quality"] = script_quality
            req.plan["meta"]["script_quality_repair"] = quality_repair
        if script_quality.get("hard_fail"):
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Senaryo üretim kalite kapısından geçemedi.",
                    "script_quality": script_quality,
                    "script_quality_repair": quality_repair,
                },
            )

    with state.render_lock:
        if state.is_rendering_active:
            raise HTTPException(
                status_code=429,
                detail="Şu anda arka planda aktif bir video render işlemi çalışıyor. Lütfen mevcut işlemin bitmesini bekleyin.",
            )
        state.is_rendering_active = True

    try:
        background_tasks.add_task(process_video_task, req)
    except Exception:
        with state.render_lock:
            state.is_rendering_active = False
        raise
    return {
        "status": "started",
        "message": "Video rendering pipeline launched.",
        "script_quality_repair": quality_repair,
    }


@router.get("/api/events")
async def sse_events(request: Request):
    q = asyncio.Queue(maxsize=300)
    state.event_queues.append(q)

    async def event_generator():
        try:
            yield "retry: 3000\n\n"

            snapshot = state.get_current_render_snapshot()
            if snapshot.get("is_rendering"):
                yield state.format_sse_message(
                    "progress",
                    {
                        "percent": snapshot.get("percent", 0),
                        "step": snapshot.get("step", "Render ediliyor..."),
                        "stage": snapshot.get("stage", "RENDERING"),
                    },
                )
                for log_line in snapshot.get("logs", [])[-25:]:
                    yield state.format_sse_message("log", log_line)
            elif snapshot.get("video_url"):
                yield state.format_sse_message(
                    "complete",
                    {
                        "url": snapshot.get("video_url"),
                        "percent": 100,
                        "step": "Tamamlandı!",
                    },
                )

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event_item = await asyncio.wait_for(q.get(), timeout=1.0)
                    if isinstance(event_item, dict):
                        e_type = event_item.get("type", "message")
                        e_data = event_item.get("data")
                        e_time = event_item.get("timestamp")
                        yield state.format_sse_message(e_type, e_data, e_time)
                    elif isinstance(event_item, str):
                        if event_item.startswith("event:") or event_item.startswith(":"):
                            yield event_item
                        else:
                            yield f"data: {event_item}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            if q in state.event_queues:
                state.event_queues.remove(q)

    from server_core.render_resilience import safe_sse_event_generator

    def _cleanup_queue() -> None:
        if q in state.event_queues:
            state.event_queues.remove(q)

    return StreamingResponse(
        safe_sse_event_generator(event_generator(), on_cleanup=_cleanup_queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _plan_gate_result(
    raw: dict,
    *,
    title: str,
    niche: str,
    language: str,
    recompile: bool,
    auto_repair: bool,
):
    """Validate plan; optionally auto-repair before integrity gate."""
    from director import compile_director_plan, pre_render_score
    from director.quality_gate import check_narration_integrity
    from scenes.narration_coherence import detect_repeated_topic_discontinuities
    from scenes.narration_validate import apply_auto_repair_if_needed, plan_narration_ok

    plan_in = dict(raw or {})
    fixes: list = []
    repaired = False
    raw_scenes = plan_in.get("scenes")
    scene_shape_invalid = raw_scenes is not None and (
        not isinstance(raw_scenes, list)
        or any(not isinstance(scene, dict) for scene in raw_scenes)
    )
    scene_rows = (
        [scene for scene in raw_scenes if isinstance(scene, dict)]
        if isinstance(raw_scenes, list)
        else []
    )
    _duration, duration_issues = validate_scene_durations(scene_rows)
    intent_issues = [
        f"scene_{index}_visual_intent_invalid"
        for index, scene in enumerate(scene_rows)
        if scene.get("visual_intent") is not None
        and not isinstance(scene.get("visual_intent"), dict)
    ]
    narration_issues = [
        f"scene_{index}_narration_invalid"
        for index, scene in enumerate(scene_rows)
        if not isinstance(scene.get("narration"), str)
    ]
    description_issues = [
        f"scene_{index}_visual_description_invalid"
        for index, scene in enumerate(scene_rows)
        if not isinstance(scene.get("scene_description"), str)
    ]
    text_issues = narration_issues + description_issues
    if scene_shape_invalid or duration_issues or intent_issues or text_issues:
        script_quality = validate_script_quality(plan_in)
        quality_repair = {
            "status": "not_needed",
            "findings_before": [],
            "findings_after": [],
        }
        if auto_repair:
            from production.script_repair import repair_script_quality_plan

            repair_result = repair_script_quality_plan(
                plan_in,
                script_quality,
                title=title,
                niche_id=niche,
                language=language,
            )
            quality_repair = repair_result["quality_repair"]
            if quality_repair["status"] in ("repaired", "partially_repaired"):
                result = _plan_gate_result(
                    repair_result["plan"],
                    title=repair_result["plan"].get("title") or title,
                    niche=niche,
                    language=language,
                    recompile=True,
                    auto_repair=False,
                )
                result["quality_repair"] = quality_repair
                result["repaired"] = True
                result["plan"].setdefault("meta", {})
                result["plan"]["meta"]["script_quality_repair"] = quality_repair
                return result
        narration_ok = not narration_issues and plan_narration_ok(
            {
                "scenes": [
                    {
                        **scene,
                        "narration": str(scene.get("narration") or ""),
                    }
                    for scene in scene_rows
                ]
            }
        )
        plan_in.setdefault("meta", {})
        plan_in["meta"]["script_quality"] = script_quality
        plan_in["meta"]["render_allowed"] = narration_ok and not script_quality.get("hard_fail")
        plan_in["meta"]["script_quality_repair"] = quality_repair
        return {
            "ok": narration_ok,
            "narration_ok": narration_ok,
            "repaired": False,
            "fixes": [],
            "narration_integrity": [],
            "scene_continuity_advisories": [],
            "script_quality": script_quality,
            "quality_repair": quality_repair,
            "pre_render_score": {
                "ok": False,
                "score": 0,
                "issues": (["scenes_invalid"] if scene_shape_invalid else [])
                + duration_issues
                + intent_issues
                + text_issues,
                "phase": "pre",
            },
            "plan": plan_in,
            "plan_narration_ok": narration_ok,
        }

    if auto_repair and plan_in.get("scenes"):
        plan_in, fixes, repaired = apply_auto_repair_if_needed(plan_in)

    if plan_in.get("scenes"):
        try:
            from scenes.enrichment import enrich_plan_scenes

            plan_in = enrich_plan_scenes(plan_in, lang=language, niche_id=niche)
        except Exception:
            logger.warning(
                "Scene enrichment failed during plan validation; continuing without enrichment",
                exc_info=True,
            )

    if recompile:
        director = compile_director_plan(
            plan_in,
            title=title,
            niche_id=niche,
            language=language,
        )
        plan_out = director.to_legacy_plan()
    else:
        from director.schema import DirectorPlan, ScenePlan

        scenes = [
            ScenePlan.from_dict(s, index=i) for i, s in enumerate(plan_in.get("scenes") or [])
        ]
        director = DirectorPlan(
            title=title,
            niche_id=niche,
            language=language,
            full_narration=str(plan_in.get("full_narration", "")),
            scenes=scenes,
        )
        plan_out = plan_in

    plan_out = sanitize_plan_scene_descriptions(plan_out or {})
    scene_continuity_advisories = detect_repeated_topic_discontinuities(
        plan_out.get("scenes") or []
    )
    script_quality = validate_script_quality(plan_out)
    quality_repair = {
        "status": "not_needed",
        "findings_before": [],
        "findings_after": [],
    }
    if auto_repair:
        from production.script_repair import repair_script_quality_plan

        repair_result = repair_script_quality_plan(
            plan_out,
            script_quality,
            title=title,
            niche_id=niche,
            language=language,
        )
        quality_repair = repair_result["quality_repair"]
        if quality_repair["status"] in ("repaired", "partially_repaired"):
            plan_out = repair_result["plan"]
            director = repair_result["director"]
            script_quality = repair_result["script_quality"]
            scene_continuity_advisories = detect_repeated_topic_discontinuities(
                plan_out.get("scenes") or []
            )

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
    from server_core.quality_gate_policy import evaluate_unified_quality_gates

    unified_gate = evaluate_unified_quality_gates(
        script_contract_issues=list(script_quality.get("issues") or []),
        duration_seconds=float(script_quality.get("duration") or 48.0),
        narration_empty=bool("empty_narration" in narr_block),
    )
    plan_out.setdefault("meta", {})
    plan_out["meta"]["script_quality"] = script_quality
    plan_out["meta"]["render_allowed"] = bool(
        not narr_block and not script_quality.get("hard_fail")
    )
    plan_out["meta"]["script_quality_repair"] = quality_repair
    plan_out["meta"]["unified_quality_gate"] = unified_gate
    return {
        "ok": not narr_block,
        "narration_ok": not narr_block,
        "repaired": repaired,
        "fixes": fixes,
        "narration_integrity": integrity,
        "scene_continuity_advisories": scene_continuity_advisories,
        "script_quality": script_quality,
        "quality_repair": quality_repair,
        "unified_quality_gate": unified_gate,
        "pre_render_score": pre,
        "plan": plan_out,
        "plan_narration_ok": plan_narration_ok(plan_out),
    }


@router.post("/api/plan/validate")
def validate_plan(
    req: PlanValidateRequest,
    auto_repair: Optional[bool] = Query(None, description="Query override for auto-repair"),
):
    """Pre-render narration integrity + semantic score for studio timeline."""
    raw = dict(req.plan or {})
    title = req.title or raw.get("title") or "Video"
    repair_flag = req.auto_repair is not False if auto_repair is None else bool(auto_repair)
    try:
        result = _plan_gate_result(
            raw,
            title=title,
            niche=req.niche or raw.get("niche_id") or "1_news_flash",
            language=req.language or "tr",
            recompile=bool(req.recompile),
            auto_repair=repair_flag,
        )
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/plan/repair")
def repair_plan(req: PlanRepairRequest):
    """Auto-repair broken scene narrations; returns fixed plan + issue log."""
    from scenes.narration_validate import auto_repair_plan, plan_narration_ok

    raw = dict(req.plan or {})
    title = req.title or raw.get("title") or "Video"
    try:
        repaired_plan, fixes = auto_repair_plan(raw)
        gate = _plan_gate_result(
            repaired_plan,
            title=title,
            niche=req.niche or raw.get("niche_id") or "1_news_flash",
            language=req.language or "tr",
            recompile=bool(req.recompile),
            auto_repair=False,
        )
        return {
            "status": "ok",
            "repaired": bool(fixes),
            "fixes": fixes,
            "ok": gate["ok"],
            "plan": gate["plan"],
            "narration_ok": gate["narration_ok"],
            "narration_integrity": gate["narration_integrity"],
            "scene_continuity_advisories": gate["scene_continuity_advisories"],
            "script_quality": gate["script_quality"],
            "quality_repair": gate.get("quality_repair"),
            "pre_render_score": gate["pre_render_score"],
            "plan_narration_ok": plan_narration_ok(gate["plan"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/status")
def get_render_status():
    state.current_render_state["is_rendering"] = state.is_rendering_active
    return state.current_render_state


@router.post("/api/video/cancel")
def cancel_render():
    if state.is_rendering_active:
        if state.current_render_state.get("cancel_requested"):
            return {"status": "ok", "message": "İptal isteği zaten işleniyor.", "active": True}
        state.current_render_state["cancel_requested"] = True
        state.current_render_state["cancel_notified"] = True
        state.broadcast_event(
            "log", "[Sistem] Kullanıcı tarafından render iptal isteği gönderildi."
        )
        return {"status": "ok", "message": "Render iptal isteği alındı.", "active": True}

    state.current_render_state["cancel_requested"] = False
    state.current_render_state["is_rendering"] = False
    state.is_rendering_active = False
    return {"status": "ok", "message": "Aktif render bulunmuyor.", "active": False}


router.include_router(gallery_router)
router.include_router(timeline_router)
router.include_router(tools_router)
routes = router.routes

