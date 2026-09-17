"""
Video pipeline, gallery, events SSE, and render status router.
"""
import os
import time
import asyncio
import subprocess
from typing import Optional
import imageio_ffmpeg
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
import config
import database
from api_models import VideoRenderRequest
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
