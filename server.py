"""
YouTube Shorts Ultimate — FastAPI Backend Server
Modular architecture with separated routers and async execution services.
"""
import os
import re
import sys
import asyncio
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import config
import database

logger = logging.getLogger(__name__)

# Re-exports for backwards compatibility
from server_core import (
    render_lock,
    is_rendering_active,
    event_queues,
    current_render_state,
    broadcast_event,
    SSELogStreamer,
    process_video_task,
    process_batch_queue
)

from routers import (
    config_router,
    video_router,
    media_router,
    research_router,
    channel_router,
    system_router,
    google_ai_router,
    kids_song_router,
)
from v2_api.router import router as v2_router

app = FastAPI(title="YouTube Shorts Ultimate Web Dashboard")


def _windows_asyncio_exception_handler(loop, context):
    exc = context.get("exception")
    if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
        return
    loop.default_exception_handler(context)


@app.on_event("startup")
async def on_startup():
    database.cleanup_stale_tasks()
    if sys.platform == "win32":
        try:
            asyncio.get_running_loop().set_exception_handler(_windows_asyncio_exception_handler)
        except Exception as exc:
            logger.warning("Windows asyncio exception handler kurulamadı: %s", exc)


@app.on_event("shutdown")
def on_shutdown():
    from kids_song_bridge import stop_managed
    stop_managed()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular routers
app.include_router(config_router)
app.include_router(video_router)
app.include_router(media_router)
app.include_router(research_router)
app.include_router(channel_router)
app.include_router(system_router)
app.include_router(google_ai_router)
app.include_router(kids_song_router)
app.include_router(v2_router)

# Serve BGM audio files for in-browser audio playback
if not os.path.exists(config.BGM_DIR):
    os.makedirs(config.BGM_DIR, exist_ok=True)
app.mount("/bgm_audio", StaticFiles(directory=config.BGM_DIR), name="bgm_audio")

# Serve output static directory
app.mount("/output", StaticFiles(directory=config.OUTPUT_DIR), name="output")

# Serve proofs dossier directory
PROOFS_DIR = os.path.join(config.BASE_DIR, "proofs")
os.makedirs(PROOFS_DIR, exist_ok=True)
app.mount("/proofs", StaticFiles(directory=PROOFS_DIR), name="proofs")

# Serve UI static files
STATIC_DIR = os.path.join(config.BASE_DIR, "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    icon_path = os.path.join(STATIC_DIR, "favicon.ico")
    if os.path.exists(icon_path):
        return FileResponse(icon_path)
    return Response(status_code=204)


def _static_mtime_version(filename: str) -> str:
    path = os.path.join(STATIC_DIR, filename)
    try:
        return str(int(os.path.getmtime(path)))
    except OSError:
        return "0"


def _render_index_html() -> str:
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as handle:
        html = handle.read()
    for asset in ("app.js", "style.css", "hardware_panel.js", "settings-quota.css"):
        version = _static_mtime_version(asset)
        html = re.sub(
            rf"(/static/{re.escape(asset)}\?v=)[^\"']+",
            rf"\g<1>{version}",
            html,
        )
    return html


@app.get("/")
def read_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return HTMLResponse(
            _render_index_html(),
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
    return HTMLResponse("<h2>Web Dashboard is loading...</h2>")


@app.get("/studio-v2", include_in_schema=False)
def read_studio_v2():
    path = os.path.join(STATIC_DIR, "studio-v2.html")
    with open(path, "r", encoding="utf-8") as handle:
        return HTMLResponse(handle.read(), headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
