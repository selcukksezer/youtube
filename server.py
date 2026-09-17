"""
YouTube Shorts Ultimate — FastAPI Backend Server
Modular architecture with separated routers and async execution services.
"""
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import config
import database

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
    system_router
)

app = FastAPI(title="YouTube Shorts Ultimate Web Dashboard")


@app.on_event("startup")
def on_startup():
    database.cleanup_stale_tasks()


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


@app.get("/")
def read_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>Web Dashboard is loading...</h2>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
