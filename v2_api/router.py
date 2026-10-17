import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse

import config
import database
from api_models import PlanValidateRequest, VideoRenderRequest
from server_core import process_video_task
from server_core import state
from .schemas import ProjectCreate, ProjectUpdate, RenderRequest, ScriptRequest

router = APIRouter(prefix="/api/v2", tags=["V2 Production"])


def _project(row: dict) -> dict:
    if not row:
        return row
    result = dict(row)
    for field in ("plan_json", "settings_json"):
        raw = result.pop(field, None)
        try:
            result[field.removesuffix("_json")] = json.loads(raw) if raw else None
        except (TypeError, ValueError):
            result[field.removesuffix("_json")] = None
    settings_dict = result.get("settings") if isinstance(result.get("settings"), dict) else {}
    result.setdefault("topic", settings_dict.get("topic") or result.get("title") or "")
    return result


def _require_project(project_id: str) -> dict:
    project = database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return project


@router.post("/projects")
def create_project(req: ProjectCreate):
    project_id = f"prj_{uuid.uuid4().hex[:12]}"
    created = database.create_project(
        project_id, req.title.strip(), req.niche, req.language
    )
    extra_updates: dict[str, Any] = {}
    if isinstance(req.plan, dict):
        extra_updates["plan_json"] = json.dumps(req.plan, ensure_ascii=False)
        extra_updates["status"] = "script_ready"
    settings_payload = dict(req.settings or {})
    if req.visual_mode:
        settings_payload.setdefault("visual_mode", req.visual_mode)
    if req.topic:
        settings_payload.setdefault("topic", req.topic.strip())
    if settings_payload:
        extra_updates["settings_json"] = json.dumps(settings_payload, ensure_ascii=False)
    if extra_updates:
        database.update_project(project_id, **extra_updates)
        created = database.get_project(project_id) or created
    proj_out = _project(created)
    if req.topic:
        proj_out["topic"] = req.topic.strip()
    return {"status": "ok", "project": proj_out, **proj_out}


@router.get("/projects")
def get_projects(limit: int = 50):
    return {"status": "ok", "projects": [_project(p) for p in database.list_projects(max(1, min(limit, 100)))]}


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    return {"status": "ok", "project": _project(_require_project(project_id))}


@router.patch("/projects/{project_id}")
def update_project(project_id: str, req: ProjectUpdate):
    current = _require_project(project_id)
    settings = req.settings
    if settings is None and current.get("settings_json"):
        try:
            settings = json.loads(current["settings_json"])
        except ValueError:
            settings = None
    # title/niche/language are intentionally kept in one small migration-safe update.
    with database.get_connection() as conn:
        values = {
            "title": req.title.strip() if req.title else current["title"],
            "niche": req.niche or current["niche"],
            "language": req.language or current["language"],
            "settings_json": json.dumps(settings, ensure_ascii=False) if settings is not None else current.get("settings_json"),
            "plan_json": json.dumps(req.plan, ensure_ascii=False) if req.plan is not None else current.get("plan_json"),
            "id": project_id,
        }
        conn.execute("""UPDATE projects SET title=:title, niche=:niche, language=:language,
                       settings_json=:settings_json, plan_json=:plan_json,
                       updated_at=CURRENT_TIMESTAMP WHERE id=:id""", values)
        conn.commit()
    return {"status": "ok", "project": _project(_require_project(project_id))}


@router.post("/projects/{project_id}/script")
def generate_project_script(project_id: str, req: ScriptRequest):
    project = _require_project(project_id)
    topic = (req.topic or project["title"]).strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Konu boş olamaz")
    from routers.research_router import api_generate_script
    from api_models import ScriptGenerateRequest
    generated = api_generate_script(ScriptGenerateRequest(
        keyword=topic,
        niche=project["niche"],
        language=project["language"],
    ))
    database.update_project(project_id, status="script_ready", plan_json=json.dumps(generated["plan"], ensure_ascii=False))
    return {"status": "ok", "project": _project(_require_project(project_id)), **generated}


@router.post("/projects/{project_id}/validate")
def validate_project(project_id: str):
    project = _require_project(project_id)
    if not project.get("plan_json"):
        raise HTTPException(status_code=409, detail="Önce senaryo üretin")
    plan = json.loads(project["plan_json"])
    from routers.video_router import _plan_gate_result
    result = _plan_gate_result(plan, title=project["title"], niche=project["niche"],
                               language=project["language"], recompile=True, auto_repair=True)
    if result.get("plan"):
        database.update_project(project_id, status="ready_to_render" if result["ok"] else "script_ready",
                                plan_json=json.dumps(result["plan"], ensure_ascii=False))
    return {"status": "ok", "project": _project(_require_project(project_id)), **result}


def _run_job(job_id: str, project_id: str, req: VideoRenderRequest):
    state.active_render_job_id = job_id
    worker_started = False
    gate_released = False
    try:
        job = database.get_render_job(job_id)
        if not job:
            raise RuntimeError(f"Render işi bulunamadı: {job_id}")
        if job["status"] == "cancelling" or state.current_render_state.get("cancel_requested"):
            database.update_render_job(job_id, status="cancelled", step="İptal edildi")
            database.update_project(project_id, status="ready_to_render")
            with state.render_lock:
                state.is_rendering_active = False
            gate_released = True
            return

        database.update_render_job(job_id, status="rendering", step="Başlatılıyor")
        worker_started = True
        process_video_task(req, reset_cancel_request=False)
        job = database.get_render_job(job_id)
        if job and job["status"] in ("completed", "failed", "cancelled"):
            if job["status"] == "cancelled":
                database.update_project(project_id, status="ready_to_render")
            elif job["status"] == "completed":
                database.update_project(project_id, status="completed")
            elif job["status"] == "failed":
                database.update_project(project_id, status="failed")
            return
        if state.current_render_state.get("error"):
            database.update_render_job(job_id, status="failed", error_message=state.current_render_state["error"])
            database.update_project(project_id, status="failed")
        elif job:
            database.update_render_job(job_id, status="completed", percent=100, step="Tamamlandı",
                                       output_url=state.current_render_state.get("video_url") or "")
            database.update_project(project_id, status="completed")
    except Exception as exc:
        database.update_render_job(job_id, status="failed", step="Başarısız", error_message=str(exc))
        database.update_project(project_id, status="failed")
    finally:
        if state.active_render_job_id == job_id:
            state.active_render_job_id = None
        if not worker_started and not gate_released:
            with state.render_lock:
                state.is_rendering_active = False


@router.post("/projects/{project_id}/render")
def render_project(project_id: str, req: RenderRequest, background_tasks: BackgroundTasks):
    project = _require_project(project_id)
    if not project.get("plan_json"):
        raise HTTPException(status_code=409, detail="Önce senaryo üretin")
    with state.render_lock:
        if state.is_rendering_active:
            raise HTTPException(status_code=429, detail="Başka bir render çalışıyor")
        state.current_render_state["cancel_requested"] = False
        state.is_rendering_active = True
    try:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        database.create_render_job(job_id, project_id)
        try:
            settings = json.loads(project.get("settings_json") or "{}")
        except (TypeError, ValueError):
            settings = {}
        settings.update(req.settings or {})
        extra_fields = {
            k: v
            for k, v in settings.items()
            if k in VideoRenderRequest.model_fields
            and k not in {
                "keyword", "plan", "niche", "language", "resolution", "voice_gender",
                "tts_voice", "bgm_track", "bgm_volume", "subtitle_preset", "visual_mode",
                "gameplay_category", "channel_id", "split_screen", "enable_ken_burns",
                "enable_hook_card", "resume", "whisper_align", "task_id",
            }
        }
        render_req = VideoRenderRequest(
            keyword=project["title"], plan=json.loads(project["plan_json"]), niche=project["niche"],
            language=project["language"], resolution=settings.get("resolution", "1080p"),
            voice_gender=settings.get("voice_gender", "male"), tts_voice=settings.get("tts_voice"),
            bgm_track=settings.get("bgm_track", ""), bgm_volume=settings.get("bgm_volume", 0.12),
            subtitle_preset=settings.get("subtitle_preset"),
            visual_mode=settings.get("visual_mode", "auto"),
            gameplay_category=settings.get("gameplay_category", "auto"),
            channel_id=settings.get("channel_id"),
            split_screen=bool(settings.get("split_screen", False)),
            enable_ken_burns=bool(settings.get("enable_ken_burns", False)),
            enable_hook_card=bool(settings.get("enable_hook_card", True)),
            resume=bool(settings.get("resume", False)),
            whisper_align=settings.get("whisper_align"),
            task_id=job_id,
            **extra_fields,
        )
        database.update_project(project_id, status="rendering", settings_json=json.dumps(settings, ensure_ascii=False))
        background_tasks.add_task(_run_job, job_id, project_id, render_req)
        return {"status": "started", "job": database.get_render_job(job_id)}
    except Exception:
        # Never leave the process-wide render gate locked on setup failure.
        state.is_rendering_active = False
        raise


@router.get("/render-jobs/{job_id}")
def get_job(job_id: str):
    job = database.get_render_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Render işi bulunamadı")
    return {"status": "ok", "job": job}


@router.post("/render-jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job = database.get_render_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Render işi bulunamadı")
    if job["status"] in ("completed", "failed", "cancelled"):
        return {"status": "ok", "job": job}
    if state.active_render_job_id in (None, job_id):
        state.current_render_state["cancel_requested"] = True
    database.update_render_job(job_id, status="cancelling", step="İptal bekleniyor")
    return {"status": "ok", "job": database.get_render_job(job_id)}


@router.get("/render-jobs/{job_id}/events")
async def job_events(job_id: str, request: Request, after: int = 0):
    """Stream persisted render events and state snapshots from a resume cursor."""
    if not database.get_render_job(job_id):
        raise HTTPException(status_code=404, detail="Render işi bulunamadı")
    if after < 0:
        raise HTTPException(status_code=400, detail="after negatif olamaz")
    last_event_header = request.headers.get("last-event-id")
    if last_event_header is not None:
        try:
            after = max(after, int(last_event_header))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Last-Event-ID geçersiz") from exc

    last = None
    async def stream():
        nonlocal last, after
        idle_ticks = 0
        while not await request.is_disconnected():
            events = database.list_render_job_events(job_id, after_id=after)
            for event in events:
                after = event["id"]
                event_payload = {
                    "job_id": job_id,
                    "event_type": event["event_type"],
                    "payload": event["payload"],
                    "timestamp": event["created_at"],
                }
                yield (
                    f"id: {after}\nevent: render.event\n"
                    f"data: {json.dumps(event_payload, ensure_ascii=False)}\n\n"
                )

            job = database.get_render_job(job_id)
            payload = json.dumps({"event": "render.state", "job": job}, ensure_ascii=False)
            if payload != last:
                last = payload
                idle_ticks = 0
                yield f"data: {payload}\n\n"
            else:
                idle_ticks += 1
                if idle_ticks >= 15:  # Send keepalive every ~10s to prevent proxy timeout
                    idle_ticks = 0
                    yield ": keepalive\n\n"
            if job and job["status"] in ("completed", "failed", "cancelled"):
                if not database.list_render_job_events(job_id, after_id=after, limit=1):
                    break
            await asyncio.sleep(0.7)
    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
