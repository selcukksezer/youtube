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
    return result


def _require_project(project_id: str) -> dict:
    project = database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return project


@router.post("/projects")
def create_project(req: ProjectCreate):
    project_id = f"prj_{uuid.uuid4().hex[:12]}"
    return {"status": "ok", "project": _project(database.create_project(
        project_id, req.title.strip(), req.niche, req.language
    ))}


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
    generated = api_generate_script(type("ScriptReq", (), {
        "keyword": topic, "niche": project["niche"], "language": project["language"],
        "reddit_post": None, "channel_id": None, "format_fingerprint": None,
    })())
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
    database.update_render_job(job_id, status="rendering", step="Başlatılıyor")
    try:
        process_video_task(req)
        if state.current_render_state.get("error"):
            database.update_render_job(job_id, status="failed", error_message=state.current_render_state["error"])
        elif database.get_render_job(job_id) and database.get_render_job(job_id).get("status") not in ("completed", "failed"):
            database.update_render_job(job_id, status="completed", percent=100, step="Tamamlandı",
                                       output_url=state.current_render_state.get("video_url") or "")
    except Exception as exc:
        database.update_render_job(job_id, status="failed", step="Başarısız", error_message=str(exc))
    finally:
        state.active_render_job_id = None


@router.post("/projects/{project_id}/render")
def render_project(project_id: str, req: RenderRequest, background_tasks: BackgroundTasks):
    project = _require_project(project_id)
    if not project.get("plan_json"):
        raise HTTPException(status_code=409, detail="Önce senaryo üretin")
    with state.render_lock:
        if state.is_rendering_active:
            raise HTTPException(status_code=429, detail="Başka bir render çalışıyor")
        state.is_rendering_active = True
    try:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        database.create_render_job(job_id, project_id)
        try:
            settings = json.loads(project.get("settings_json") or "{}")
        except (TypeError, ValueError):
            settings = {}
        settings.update(req.settings or {})
        render_req = VideoRenderRequest(
            keyword=project["title"], plan=json.loads(project["plan_json"]), niche=project["niche"],
            language=project["language"], resolution=settings.get("resolution", "1080p"),
            voice_gender=settings.get("voice_gender", "male"), tts_voice=settings.get("tts_voice"),
            bgm_track=settings.get("bgm_track", ""), bgm_volume=settings.get("bgm_volume", 0.12),
            split_screen=bool(settings.get("split_screen", False)),
            enable_ken_burns=bool(settings.get("enable_ken_burns", False)),
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
    state.current_render_state["cancel_requested"] = True
    database.update_render_job(job_id, status="cancelling", step="İptal bekleniyor")
    return {"status": "ok", "job": database.get_render_job(job_id)}


@router.get("/render-jobs/{job_id}/events")
async def job_events(job_id: str, request: Request):
    if not database.get_render_job(job_id):
        raise HTTPException(status_code=404, detail="Render işi bulunamadı")
    last = None
    async def stream():
        nonlocal last
        while not await request.is_disconnected():
            job = database.get_render_job(job_id)
            payload = json.dumps({"event": "render.state", "job": job}, ensure_ascii=False)
            if payload != last:
                last = payload
                yield f"data: {payload}\n\n"
            if job and job["status"] in ("completed", "failed", "cancelled"):
                break
            await asyncio.sleep(0.7)
    return StreamingResponse(stream(), media_type="text/event-stream")
