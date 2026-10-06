"""
Video pipeline, gallery, events SSE, and render status router.
"""
import json
import os
import time
import asyncio
import subprocess
from typing import Any, Dict, Optional
import imageio_ffmpeg
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
import config
import database
from api_models import VideoRenderRequest, PlanValidateRequest, PlanRepairRequest, ShareDecisionRequest
from server_core import (
    render_lock,
    is_rendering_active,
    event_queues,
    current_render_state,
    broadcast_event,
    process_video_task
)
from server_core import state
from scenes.narration_validate import sanitize_plan_scene_descriptions
from production.quality import validate_script_quality

router = APIRouter(tags=["Video"])


def _quality_gate_summary_for_filename(filename: str) -> Optional[Dict[str, Any]]:
    """P2-26: load post-render quality_gate.json summary for gallery cards."""
    base = os.path.splitext(os.path.basename(filename or ""))[0]
    if not base:
        return None
    qpath = os.path.join(config.ASSETS_DIR, base, "quality_gate.json")
    if not os.path.isfile(qpath):
        return None
    try:
        with open(qpath, "r", encoding="utf-8") as qf:
            qg = json.load(qf)
    except Exception:
        return None
    post = qg.get("post") or {}
    pre = qg.get("pre") or {}
    return {
        "ok": post.get("ok", True),
        "score": post.get("score"),
        "issues": post.get("issues") or [],
        "duration": post.get("video_duration"),
        "pre_ok": pre.get("ok"),
        "pre_score": pre.get("score"),
    }


@router.get("/api/videos")
def api_get_videos(limit: int = 50):
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        candidates = database.get_recent_videos(limit=limit * 3)
        videos = []
        for video in candidates:
            if video.get("status") != "completed" or not video.get("filename"):
                continue
            video_path = os.path.join(config.OUTPUT_DIR, os.path.basename(video["filename"]))
            if not os.path.isfile(video_path) or os.path.getsize(video_path) < 100_000:
                continue
            probe = subprocess.run(
                [ffmpeg_exe, "-v", "error", "-i", video_path, "-f", "null", "-"],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20
            )
            if probe.returncode != 0:
                continue
            video["size_mb"] = round(os.path.getsize(video_path) / (1024 * 1024), 2)
            qg = _quality_gate_summary_for_filename(video["filename"])
            if qg:
                video["quality_gate"] = qg
            try:
                from services.gallery_cache import gallery_cache
                task_key = os.path.splitext(os.path.basename(video["filename"]))[0]
                thumb_path = gallery_cache.ensure_thumb(task_key, video_path)
                if thumb_path:
                    video["thumbnail_url"] = gallery_cache.get_thumb_url(task_key)
            except Exception:
                pass
            videos.append(video)
            if len(videos) >= limit:
                break
        return {"status": "ok", "videos": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/videos/{task_id}/thumbnail")
def api_get_video_thumbnail(task_id: str):
    """Returns cached 480p preview thumbnail for completed video (Plan Section 28.1)."""
    from services.gallery_cache import gallery_cache
    from services.path_security import validate_task_id, UnsafePathError
    from fastapi.responses import FileResponse
    try:
        safe_id = validate_task_id(task_id)
    except UnsafePathError:
        raise HTTPException(status_code=400, detail="Geçersiz görev kimliği.")

    thumb_path = gallery_cache.get_thumb_path(safe_id)
    if not thumb_path or not os.path.isfile(thumb_path):
        cand_video = os.path.join(config.OUTPUT_DIR, safe_id)
        if not os.path.isfile(cand_video):
            cand_video = os.path.join(config.OUTPUT_DIR, f"{safe_id}.mp4")
        if os.path.isfile(cand_video):
            thumb_path = gallery_cache.ensure_thumb(safe_id, cand_video)

    if not thumb_path or not os.path.isfile(thumb_path):
        raise HTTPException(status_code=404, detail="Önizleme resmi bulunamadı.")
    return FileResponse(thumb_path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.post("/api/video/render")
def api_render_video(req: VideoRenderRequest, background_tasks: BackgroundTasks):
    if req.plan is not None:
        script_quality = validate_script_quality(req.plan)
        if script_quality.get("hard_fail"):
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Senaryo üretim kalite kapısından geçemedi.",
                    "script_quality": script_quality,
                },
            )

    with state.render_lock:
        if state.is_rendering_active:
            raise HTTPException(
                status_code=429, 
                detail="Şu anda arka planda aktif bir video render işlemi çalışıyor. Lütfen mevcut işlemin bitmesini bekleyin."
            )
        state.is_rendering_active = True

    background_tasks.add_task(process_video_task, req)
    return {"status": "started", "message": "Video rendering pipeline launched."}


@router.get("/api/events")
async def sse_events(request: Request):
    q = asyncio.Queue(maxsize=300)
    state.event_queues.append(q)
    
    async def event_generator():
        try:
            # Section 10.1 Handshake: Reconnect retry period
            yield "retry: 3000\n\n"

            # Section 10.1 Replay: Page refresh state recovery
            snapshot = state.get_current_render_snapshot()
            if snapshot.get("is_rendering"):
                yield state.format_sse_message(
                    "progress",
                    {
                        "percent": snapshot.get("percent", 0),
                        "step": snapshot.get("step", "Render ediliyor..."),
                        "stage": snapshot.get("stage", "RENDERING")
                    }
                )
                for log_line in snapshot.get("logs", [])[-25:]:
                    yield state.format_sse_message("log", log_line)
            elif snapshot.get("video_url"):
                yield state.format_sse_message(
                    "complete",
                    {
                        "url": snapshot.get("video_url"),
                        "percent": 100,
                        "step": "Tamamlandı!"
                    }
                )

            # Main SSE event stream loop
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

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/api/project/clear_stock_cache")
async def clear_stock_cache(request: Request):
    """
    Clears cached stock video files from project asset directory when switching to MiniMax-H3.
    """
    import re
    try:
        data = await request.json()
        topic = data.get("topic") or data.get("project_slug") or ""
        if not topic:
            return {"status": "ok", "deleted_count": 0}

        safe_slug = re.sub(r'[\/:*?"<>| ]', '_', topic)[:60].strip('_')
        proj_dir = os.path.join(config.BASE_DIR, "assets", safe_slug)
        deleted_count = 0
        if os.path.exists(proj_dir):
            for fname in os.listdir(proj_dir):
                fl = fname.lower()
                if (fl.endswith(".mp4") or fl.endswith(".webm")) and any(k in fl for k in ("pexels", "pixabay", "stock", "source")):
                    fp = os.path.join(proj_dir, fname)
                    try:
                        os.remove(fp)
                        deleted_count += 1
                    except Exception:
                        pass
        return {"status": "ok", "deleted_count": deleted_count}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/api/gallery")
def get_gallery():
    if not os.path.exists(config.OUTPUT_DIR):
        return {"videos": []}
    
    # Filter out temporary working files
    files = [f for f in os.listdir(config.OUTPUT_DIR) if f.lower().endswith(".mp4") and not f.lower().endswith("_tmp.mp4")]
    videos = []
    for f in sorted(files, key=lambda x: os.path.getmtime(os.path.join(config.OUTPUT_DIR, x)), reverse=True):
        fp = os.path.join(config.OUTPUT_DIR, f)
        mtime = os.path.getmtime(fp)
        size_mb = round(os.path.getsize(fp) / (1024*1024), 2)
        videos.append({
            "filename": f,
            "title": f.rsplit(".", 1)[0].replace("_", " "),
            "url": f"/output/{f}",
            "size_mb": size_mb,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        })
    return {"videos": videos}


@router.post("/api/videos/{video_id}/share-decision")
def video_share_decision(video_id: int, req: ShareDecisionRequest):
    """
    Post-render manual upload flow (Item 133 / 471).
    keep  → proof + SEO + assets preserved for YouTube dispute/manual upload
    discard → delete video, proof bundle, project assets, audio temps
    """
    from proof_archiver import proof_archiver

    video = database.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video kaydı bulunamadı.")

    decision = (req.decision or "").strip().lower()
    if decision not in ("keep", "discard"):
        raise HTTPException(status_code=400, detail="decision 'keep' veya 'discard' olmalı.")

    filename = video.get("filename") or ""
    channel_slug = video.get("channel_slug") or "default"
    project_slug = req.project_slug or (os.path.splitext(filename)[0] if filename else None)

    if decision == "keep":
        if filename:
            proof_archiver.mark_share_kept(filename)
        database.update_share_decision(video_id, "keep")
        return {
            "status": "ok",
            "decision": "keep",
            "message": "Proof ve SEO paketi saklandı. YouTube'a manuel yükleyebilirsiniz.",
            "youtube_upload_url": "https://www.youtube.com/upload",
        }

    if not filename:
        database.update_share_decision(video_id, "discarded")
        database.delete_video_by_id(video_id)
        return {"status": "ok", "decision": "discard", "message": "Kayıt silindi (dosya yoktu).", "deleted": []}

    result = proof_archiver.discard_video_bundle(
        filename,
        channel_slug=channel_slug,
        project_slug=project_slug,
    )
    database.update_share_decision(video_id, "discarded")
    database.delete_video_by_id(video_id)

    return {
        "status": "ok",
        "decision": "discard",
        "message": "Video ve ilişkili dosyalar silindi.",
        "deleted_count": len(result.get("deleted") or []),
        "errors": result.get("errors") or [],
    }


@router.delete("/api/gallery/{filename}")
def delete_video(filename: str):
    safe_filename = os.path.basename(filename)
    fp = os.path.realpath(os.path.join(config.OUTPUT_DIR, safe_filename))
    out_dir_real = os.path.realpath(config.OUTPUT_DIR)

    # Path traversal check
    if not fp.startswith(out_dir_real) or not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")

    try:
        os.remove(fp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya silinemedi: {str(e)}")

    # Delete related ASS and SRT subtitle files if present
    base_no_ext = fp.rsplit(".", 1)[0]
    for sub_ext in [".ass", ".srt"]:
        sub_path = base_no_ext + sub_ext
        if os.path.exists(sub_path):
            try:
                os.remove(sub_path)
            except Exception:
                pass

    # Synchronize and remove from SQLite database
    database.delete_video_by_filename(safe_filename)

    return {"status": "ok", "message": "Video ve ilişkili dosyalar başarıyla silindi."}


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

    if auto_repair and plan_in.get("scenes"):
        plan_in, fixes, repaired = apply_auto_repair_if_needed(plan_in)

    if plan_in.get("scenes"):
        try:
            from scenes.enrichment import enrich_plan_scenes
            plan_in = enrich_plan_scenes(plan_in, lang=language, niche_id=niche)
        except Exception:
            pass

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
        scenes = [ScenePlan.from_dict(s, index=i) for i, s in enumerate(plan_in.get("scenes") or [])]
        director = DirectorPlan(
            title=title,
            niche_id=niche,
            language=language,
            full_narration=str(plan_in.get("full_narration", "")),
            scenes=scenes,
        )
        plan_out = plan_in

    plan_out = sanitize_plan_scene_descriptions(plan_out or {})
    scene_continuity_advisories = detect_repeated_topic_discontinuities(plan_out.get("scenes") or [])

    integrity = check_narration_integrity(director)
    pre = pre_render_score(director)
    narr_block = list(integrity) + [
        i for i in pre.get("issues", [])
        if i.startswith("fragment") or i.startswith("low_words")
        or i.startswith("empty_narration") or i.startswith("no_terminal")
    ]
    return {
        "ok": not narr_block,
        "narration_ok": not narr_block,
        "repaired": repaired,
        "fixes": fixes,
        "narration_integrity": integrity,
        "scene_continuity_advisories": scene_continuity_advisories,
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
            "pre_render_score": gate["pre_render_score"],
            "plan_narration_ok": plan_narration_ok(gate["plan"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{slug}/plan")
def get_project_plan(slug: str):
    """Load saved plan.json / director_plan.json for gallery reopen → timeline."""
    import json
    import re as _re

    safe = os.path.basename(slug or "").strip()
    safe = _re.sub(r"[^\w\-]", "", safe.replace(" ", "_"))[:120]
    if not safe:
        raise HTTPException(status_code=400, detail="Gecersiz proje adi")

    proj = os.path.join(config.ASSETS_DIR, safe)
    if not os.path.isdir(proj):
        # Try fuzzy: match folder that starts with slug
        try:
            for name in os.listdir(config.ASSETS_DIR):
                if name.startswith(safe[:40]) or safe.startswith(name[:40]):
                    cand = os.path.join(config.ASSETS_DIR, name)
                    if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "plan.json")):
                        proj = cand
                        safe = name
                        break
        except OSError:
            pass
    plan_path = os.path.join(proj, "plan.json")
    if not os.path.isfile(plan_path):
        raise HTTPException(status_code=404, detail="Bu video icin kayitli senaryo bulunamadi")

    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            plan = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan okunamadi: {e}")

    director = None
    dpath = os.path.join(proj, "director_plan.json")
    if os.path.isfile(dpath):
        try:
            with open(dpath, "r", encoding="utf-8") as f:
                director = json.load(f)
        except Exception:
            director = None

    qg = None
    qpath = os.path.join(proj, "quality_gate.json")
    if os.path.isfile(qpath):
        try:
            with open(qpath, "r", encoding="utf-8") as f:
                qg = json.load(f)
        except Exception:
            qg = None

    from director import compile_director_plan, pre_render_score
    from director.quality_gate import check_narration_integrity

    title = plan.get("title") or safe.replace("_", " ")
    niche_id = (director or {}).get("niche_id") or plan.get("niche_id") or "1_news_flash"
    try:
        compiled = compile_director_plan(plan, title=title, niche_id=niche_id)
        integrity = check_narration_integrity(compiled)
        pre = pre_render_score(compiled)
        if integrity or not pre.get("ok"):
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Kayitli senaryo kopuk cumle iceriyor — yeni senaryo uretin.",
                    "narration_integrity": integrity,
                    "pre_render_score": pre,
                },
            )
        plan = compiled.to_legacy_plan()
        director = compiled.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan dogrulanamadi: {e}")

    plan = sanitize_plan_scene_descriptions(plan or {})

    return {
        "status": "ok",
        "slug": safe,
        "plan": plan,
        "director": director,
        "quality_gate": qg,
    }


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
        state.broadcast_event("log", "[Sistem] Kullanıcı tarafından render iptal isteği gönderildi.")
        try:
            from visuals.ai_video.providers.minimax_h3 import comfy_base_url
            import requests
            requests.post(f"{comfy_base_url()}/interrupt", timeout=1.5)
        except Exception:
            pass
        return {"status": "ok", "message": "Render iptal isteği alındı.", "active": True}

    state.current_render_state["cancel_requested"] = False
    state.current_render_state["is_rendering"] = False
    state.is_rendering_active = False
    return {"status": "ok", "message": "Aktif render bulunmuyor.", "active": False}


@router.get("/api/database/videos")
def get_database_videos():
    videos = database.get_recent_videos(100)
    stats = database.get_video_stats()
    return {"status": "ok", "videos": videos, "stats": stats}


@router.post("/api/script/virality_audit")
def api_audit_script_virality(payload: Dict[str, Any]):
    """8-signal virality and slop audit adapted from Anil-matcha highlights engine."""
    from services.virality_evaluator import evaluate_script_virality
    narration = str(payload.get("narration") or payload.get("full_narration") or "").strip()
    topic = str(payload.get("topic") or payload.get("title") or "").strip()
    result = evaluate_script_virality(narration, topic=topic)
    return {"status": "ok", "audit": result}


@router.post("/api/clipper/analyze")
def api_clipper_analyze(payload: Dict[str, Any]):
    """Analyzes a YouTube URL, fetches transcript, and detects viral 9:16 highlights."""
    url = str(payload.get("url") or "").strip()
    num_clips = int(payload.get("num_clips") or 3)
    if not url:
        raise HTTPException(status_code=400, detail="YouTube URL gerekli.")

    try:
        from services.youtube_clipper import youtube_clipper
        info = youtube_clipper.extract_youtube_info(url)
        # Fetch subtitles or transcribe
        subs = youtube_clipper.fetch_subtitles_or_transcribe(url, "")
        transcript_text = " ".join(s["text"] for s in subs) if subs else info.get("description", "")
        duration = float(info.get("duration") or 300)
        raw_highlights = youtube_clipper.detect_highlights_with_llm(
            transcript_text=transcript_text,
            num_clips=max(1, min(5, num_clips)),
            video_duration=duration,
        )
        from services.highlight_clipper import select_highlights
        words = [
            {"w": row.get("text") or "", "s": row.get("start"), "e": row.get("end")}
            for row in (subs or [])
        ]
        highlights = select_highlights(
            raw_highlights,
            duration=duration,
            words=words,
            num_clips=num_clips,
        )
        return {
            "status": "ok",
            "video_info": info,
            "highlights_count": len(highlights),
            "highlights": highlights,
            "words": words,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clipper analizi başarısız: {e}")


@router.post("/api/clipper/render")
def api_clipper_render(payload: Dict[str, Any]):
    """Downloads YouTube video segment and applies OpenCV face-tracking 9:16 crop."""
    url = str(payload.get("url") or "").strip()
    highlight = payload.get("highlight") or {}
    clip_index = int(payload.get("clip_index") or 1)

    if not url or not highlight:
        raise HTTPException(status_code=400, detail="URL ve highlight objesi gerekli.")

    try:
        from services.youtube_clipper import youtube_clipper
        source_path = youtube_clipper.download_video(url)
        out_clip_path = youtube_clipper.render_highlight_clip(
            source_video_path=source_path,
            highlight=highlight,
            clip_index=clip_index,
        )
        return {
            "status": "ok",
            "message": "Viral Short başarıyla üretildi.",
            "output_path": out_clip_path,
            "filename": os.path.basename(out_clip_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clipper render başarısız: {e}")


@router.post("/api/helios/prompt")
def api_helios_prompt(payload: Dict[str, Any]):
    """Generates Helios 4-tier cinematographic prompt and inference configuration."""
    narration = str(payload.get("narration") or "").strip()
    scene_description = str(payload.get("scene_description") or "").strip()
    niche_id = str(payload.get("niche_id") or "general").strip()
    aspect = str(payload.get("aspect") or "9:16").strip()
    index = int(payload.get("index") or 0)
    duration = float(payload.get("duration") or 4.0)

    from visuals.ai_video.helios_prompt_builder import HeliosPromptBuilder, HELIOS_NEGATIVE_PROMPT

    params = HeliosPromptBuilder.create_helios_params(
        narration=narration,
        scene_description=scene_description,
        niche_id=niche_id,
        duration=duration,
        aspect=aspect,
        index=index,
    )
    return {
        "status": "ok",
        "prompt": params.prompt,
        "negative_prompt": HELIOS_NEGATIVE_PROMPT,
        "inference_params": params.to_dict(),
    }


@router.post("/api/helios/enhance_scenes")
def api_helios_enhance_scenes(payload: Dict[str, Any]):
    """Applies Helios 4-tier shot grammar and sequence pacing across all script scenes."""
    scenes = payload.get("scenes") or []
    niche_id = str(payload.get("niche_id") or "general").strip()
    aspect = str(payload.get("aspect") or "9:16").strip()

    if not isinstance(scenes, list) or not scenes:
        raise HTTPException(status_code=400, detail="scenes listesi boş olamaz.")

    from services.helios_visual_enhancer import helios_visual_enhancer
    enhanced = helios_visual_enhancer.enhance_scenes_sequence(
        scenes=scenes,
        niche_id=niche_id,
        aspect=aspect,
    )
    return {
        "status": "ok",
        "count": len(enhanced),
        "scenes": enhanced,
    }


@router.post("/api/punch_in/curve")
def api_punch_in_curve(payload: Dict[str, Any]):
    """Calculates asymmetric smoothstep punch-in zoom curve and FFmpeg filter."""
    duration = float(payload.get("duration") or 5.0)
    fps = int(payload.get("fps") or 30)
    emphasis_times = payload.get("emphasis_times")
    max_zoom = float(payload.get("max_zoom") or 1.12)
    width = int(payload.get("width") or 1080)
    height = int(payload.get("height") or 1920)

    from effects.punch_in_director import punch_in_director
    zooms = punch_in_director.calculate_zoom_curve(
        total_duration_sec=duration,
        fps=fps,
        emphasis_times=emphasis_times,
        max_zoom=max_zoom,
    )
    ffmpeg_filter = punch_in_director.generate_ffmpeg_zoom_filter(
        width=width,
        height=height,
        total_duration_sec=duration,
        punch_time_sec=emphasis_times[0] if emphasis_times else 0.5,
        max_zoom=max_zoom,
        fps=fps,
    )
    return {
        "status": "ok",
        "frame_count": len(zooms),
        "peak_zoom": max(zooms) if zooms else 1.0,
        "sample_zooms": [round(z, 3) for z in zooms[:15]],
        "ffmpeg_filter": ffmpeg_filter,
    }


@router.post("/api/grounding/audit")
def api_grounding_audit(payload: Dict[str, Any]):
    """Audits and regrounds narration vs visual scene descriptions to prevent absurd slop."""
    scenes = payload.get("scenes") or []
    niche_id = str(payload.get("niche_id") or "general").strip()

    if not isinstance(scenes, list) or not scenes:
        raise HTTPException(status_code=400, detail="scenes listesi boş olamaz.")

    from services.hook_visual_grounding import hook_visual_grounding
    regrounded = hook_visual_grounding.reground_plan_scenes(
        scenes=scenes,
        niche_id=niche_id,
    )
    mismatches = sum(1 for s in regrounded if not s.get("is_grounded"))

    return {
        "status": "ok",
        "total_scenes": len(regrounded),
        "regrounded_count": mismatches,
        "scenes": regrounded,
    }


@router.post("/api/speaker/layout")
def api_speaker_layout(payload: Dict[str, Any]):
    """Evaluates multi-speaker dialogue turns and selects optimal vertical layout."""
    turns = payload.get("turns") or []
    total_duration = float(payload.get("total_duration") or 30.0)

    from services.active_speaker_detector import active_speaker_detector
    res = active_speaker_detector.evaluate_turns(
        turns=turns,
        total_duration_sec=total_duration,
    )
    return {
        "status": "ok",
        "layout_decision": res.layout_decision.value,
        "is_multispeaker": res.is_multispeaker,
        "speaker_distribution": res.speaker_distribution,
        "explanation": res.explanation,
    }


