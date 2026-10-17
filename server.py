"""
YouTube Shorts Ultimate — FastAPI Backend Server
Modular architecture with separated routers and async execution services.
"""
import os
import re
import sys
import asyncio
import logging
import warnings
from contextlib import asynccontextmanager

warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")

from server_core.workspace_maintenance import configure_urllib3_libressl_warning_filter

configure_urllib3_libressl_warning_filter()

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, Response
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

from routers.config_router import router as config_router
from routers.video_router import router as video_router
from routers.media_router import router as media_router
from routers.research_router import router as research_router
from routers.channel_router import router as channel_router
from routers.system_router import router as system_router
from routers.google_ai_router import router as google_ai_router
from routers.kids_song_router import router as kids_song_router
from routers.clipper_router import router as clipper_router
from routers.jobs_v1_router import router as jobs_v1_router
from routers.auth_git_router import (
    router as auth_git_router,
    get_authenticated_user,
    is_auth_bypassed,
    require_studio_auth,
    studio_auth_middleware,
    start_auto_git_updater,
    stop_auto_git_updater,
)
from v2_api.router import router as v2_router
from server_core.render_resilience import resume_interrupted_render_jobs


def _windows_asyncio_exception_handler(loop, context):
    exc = context.get("exception")
    if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
        return
    loop.default_exception_handler(context)


async def on_startup():
    database.cleanup_stale_tasks()
    try:
        resume_interrupted_render_jobs(database)
    except Exception as exc:
        logger.debug("Interrupted render jobs check skipped: %s", exc)
    try:
        asyncio.get_running_loop().set_exception_handler(_windows_asyncio_exception_handler)
    except Exception as exc:
        logger.warning("Asyncio exception handler kurulamadı: %s", exc)
    start_auto_git_updater()


def on_shutdown():
    stop_auto_git_updater()
    from server_core import state
    state.current_render_state["cancel_requested"] = True
    from kids_song_bridge import stop_managed
    stop_managed()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()
    try:
        yield
    finally:
        on_shutdown()


app = FastAPI(title="YouTube Shorts Ultimate Web Dashboard", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular routers
_AUTH_DEPS = [Depends(require_studio_auth)]
app.middleware("http")(studio_auth_middleware)
app.include_router(auth_git_router)
app.include_router(config_router, dependencies=_AUTH_DEPS)
app.include_router(video_router, dependencies=_AUTH_DEPS)
app.include_router(media_router, dependencies=_AUTH_DEPS)
app.include_router(research_router, dependencies=_AUTH_DEPS)
app.include_router(channel_router, dependencies=_AUTH_DEPS)
app.include_router(system_router, dependencies=_AUTH_DEPS)
app.include_router(google_ai_router, dependencies=_AUTH_DEPS)
app.include_router(kids_song_router, dependencies=_AUTH_DEPS)
app.include_router(clipper_router, dependencies=_AUTH_DEPS)
app.include_router(v2_router, dependencies=_AUTH_DEPS)
app.include_router(jobs_v1_router, dependencies=_AUTH_DEPS)

# Serve BGM audio files for in-browser audio playback
if not os.path.exists(config.BGM_DIR):
    os.makedirs(config.BGM_DIR, exist_ok=True)
app.mount("/bgm_audio", StaticFiles(directory=config.BGM_DIR), name="bgm_audio")

# Serve output static directory
app.mount("/output", StaticFiles(directory=config.OUTPUT_DIR), name="output")

# Serve assets directory for in-browser scene video and media preview
if not os.path.exists(config.ASSETS_DIR):
    os.makedirs(config.ASSETS_DIR, exist_ok=True)
app.mount("/assets", StaticFiles(directory=config.ASSETS_DIR), name="assets")


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
    apple_icon = os.path.join(STATIC_DIR, "icons", "apple-touch-icon.png")
    if os.path.exists(apple_icon):
        return FileResponse(apple_icon, media_type="image/png")
    return Response(status_code=204)


@app.get("/manifest.json", include_in_schema=False)
def pwa_manifest():
    manifest_path = os.path.join(STATIC_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/manifest+json")
    return Response(status_code=404)


@app.get("/sw.js", include_in_schema=False)
def pwa_service_worker():
    sw_path = os.path.join(STATIC_DIR, "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(
            sw_path,
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
        )
    return Response(status_code=404)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": "ShortsVideoCreators", "render_threads": config.RENDER_THREADS}


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
    assets = (
        "app.js", "style.css", "studio.css", "hardware_panel.js", "settings-quota.css",
        "js/state-defaults.js", "js/state-sync.js", "js/state.js",
        "js/navigation.js", "js/clipper.js", "js/niches.js",
        "js/studio-plan-editor.js", "js/studio-ai-tools.js", "js/studio.js",
        "js/timeline-preview.js", "js/timeline.js",
        "js/bgm-library.js", "js/audio-media.js",
        "js/public-apis.js", "js/render-sse-handler.js", "js/render-monitor.js",
        "js/channels-manager.js", "js/gallery-channels.js",
        "js/quota-analytics.js", "js/settings-quota.js", "js/viral_features.js", "js/git-auth-ui.js",
    )
    for asset in assets:
        version = _static_mtime_version(asset)
        html = re.sub(
            rf"(/static/{re.escape(asset)}\?v=)[^\"']+",
            rf"\g<1>{version}",
            html,
        )
        html = re.sub(
            rf"\"/static/{re.escape(asset)}\"",
            rf'"/static/{asset}?v={version}"',
            html,
        )
    return html


@app.get("/")
def read_root(request: Request = None):
    if request is not None and not is_auth_bypassed(request) and not get_authenticated_user(request):
        return RedirectResponse(url="/login", status_code=302)
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return HTMLResponse(
            _render_index_html(),
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
    return HTMLResponse("<h2>Web Dashboard is loading...</h2>")


if __name__ == "__main__":
    import socket
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s_sock:
            s_sock.connect(("8.8.8.8", 80))
            lan_ip = s_sock.getsockname()[0]
        print(f"📱 iPhone / iOS PWA Baglantisi: http://{lan_ip}:{port}")
    except Exception:
        pass
    uvicorn.run("server:app", host=host, port=port, reload=False)
