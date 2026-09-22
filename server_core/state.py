"""
Server state, concurrency locks, and SSE event streaming.
"""
import json
import time
import asyncio
import threading
import logging
from typing import List, Any

logger = logging.getLogger(__name__)

# Concurrency lock to prevent multiple heavy ffmpeg/moviepy renders simultaneously
render_lock = threading.Lock()
is_rendering_active = False
active_render_job_id = None

# Global queue for SSE event streaming
event_queues: List[asyncio.Queue] = []

# Persistent Render State across page refreshes
current_render_state = {
    "is_rendering": False,
    "percent": 0,
    "step": "Hazır",
    "keyword": "",
    "logs": [],
    "cancel_requested": False,
    "cancel_notified": False,
    "video_url": None,
    "error": None
}


def broadcast_event(event_type: str, data: Any):
    global current_render_state
    if event_type == "progress":
        if isinstance(data, dict):
            current_render_state["percent"] = data.get("percent", current_render_state["percent"])
            current_render_state["step"] = data.get("step", current_render_state["step"])
    elif event_type == "log":
        current_render_state["logs"].append(str(data))
        if len(current_render_state["logs"]) > 150:
            current_render_state["logs"] = current_render_state["logs"][-150:]
    elif event_type == "complete":
        current_render_state["is_rendering"] = False
        current_render_state["percent"] = 100
        current_render_state["step"] = "Tamamlandı!"
        if isinstance(data, dict):
            current_render_state["video_url"] = data.get("url")
    elif event_type == "error":
        current_render_state["is_rendering"] = False
        current_render_state["error"] = str(data)

    # The legacy worker emits global events. Mirror them to the durable V2 job
    # selected by the V2 router so refreshes no longer lose render progress.
    job_id = active_render_job_id
    if job_id:
        try:
            import database
            if event_type == "progress" and isinstance(data, dict):
                database.update_render_job(
                    job_id, status="rendering", percent=int(data.get("percent", 0)),
                    step=str(data.get("step", "Render ediliyor")),
                )
            elif event_type == "complete":
                url = data.get("url") if isinstance(data, dict) else None
                database.update_render_job(job_id, status="completed", percent=100,
                                           step="Tamamlandı", output_url=url or "")
            elif event_type == "error":
                database.update_render_job(job_id, status="failed", step="Başarısız",
                                           error_message=str(data))
        except Exception as exc:
            logger.warning("Render job state güncellenemedi (%s): %s", job_id, exc)

    payload = json.dumps({"type": event_type, "data": data, "timestamp": time.time()})
    for q in list(event_queues):
        try:
            q.put_nowait(payload)
        except Exception as exc:
            logger.debug("SSE kuyruğuna olay yazılamadı: %s", exc)


class SSELogStreamer:
    """Redirects print statements to SSE queue."""
    def __init__(self, original_stdout):
        # Never nest: if a render starts while sys.stdout is already wrapped
        # (batch thread + direct render, or a previous run that failed to
        # restore), unwrap to the real stream. A nested wrapper broadcast each
        # line twice to the SSE log panel.
        while isinstance(original_stdout, SSELogStreamer):
            original_stdout = original_stdout.original_stdout
        self.original_stdout = original_stdout

    def write(self, buf):
        self.original_stdout.write(buf)
        msg = buf.strip()
        if msg:
            broadcast_event("log", msg)

    def flush(self):
        self.original_stdout.flush()

    def __getattr__(self, name):
        # encoding / isatty / fileno etc. — libraries poke at sys.stdout
        return getattr(self.original_stdout, name)
