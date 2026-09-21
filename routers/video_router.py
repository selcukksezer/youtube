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
            videos.append(video)
            if len(videos) >= limit:
                break
        return {"status": "ok", "videos": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/video/render")
def api_render_video(req: VideoRenderRequest, background_tasks: BackgroundTasks):
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
    q = asyncio.Queue()
    state.event_queues.append(q)
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=1.0)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield f": keep-alive\n\n"
        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            if q in state.event_queues:
                state.event_queues.remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
    from scenes.narration_validate import apply_auto_repair_if_needed, plan_narration_ok

    plan_in = dict(raw or {})
    fixes: list = []
    repaired = False

    if auto_repair and plan_in.get("scenes"):
        plan_in, fixes, repaired = apply_auto_repair_if_needed(plan_in)

    if plan_in.get("scenes"):
        try:
            from scenes.enrichment import enrich_plan_scenes
            plan_in = enrich_plan_scenes(plan_in, lang=language)
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
