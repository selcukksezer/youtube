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
    "stage": "IDLE",
    "keyword": "",
    "logs": [],
    "cancel_requested": False,
    "cancel_notified": False,
    "video_url": None,
    "error": None
}


def format_sse_message(event_type: str, data: Any, timestamp: float = None) -> str:
    """
    Formats a message according to Section 10.1 canonical SSE specification:
    event: <event_type>
    data: <payload>
    """
    if timestamp is None:
        timestamp = time.time()

    if isinstance(data, dict):
        payload_obj = dict(data)
        if "timestamp" not in payload_obj:
            payload_obj["timestamp"] = timestamp
        payload_str = json.dumps(payload_obj, ensure_ascii=False)
    elif isinstance(data, (list, int, float, bool)):
        payload_str = json.dumps(data, ensure_ascii=False)
    else:
        payload_str = str(data)

    return f"event: {event_type}\ndata: {payload_str}\n\n"


def get_current_render_snapshot() -> dict:
    """Returns a thread-safe copy of the current render state across page refreshes."""
    with render_lock:
        return {
            "is_rendering": bool(current_render_state.get("is_rendering", False)),
            "percent": int(current_render_state.get("percent", 0)),
            "step": str(current_render_state.get("step", "Hazır")),
            "stage": str(current_render_state.get("stage", "IDLE")),
            "keyword": str(current_render_state.get("keyword", "")),
            "logs": list(current_render_state.get("logs", [])),
            "cancel_requested": bool(current_render_state.get("cancel_requested", False)),
            "video_url": current_render_state.get("video_url"),
            "error": current_render_state.get("error")
        }


def broadcast_event(event_type: str, data: Any):
    global current_render_state
    try:
        from services.log_sanitizer import sanitize_payload
        data = sanitize_payload(data)
    except Exception:
        pass
    if event_type == "progress":
        if isinstance(data, dict):
            current_render_state["percent"] = data.get("percent", current_render_state["percent"])
            current_render_state["step"] = data.get("step", current_render_state["step"])
            if "stage" in data:
                current_render_state["stage"] = data["stage"]
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

    # Section 10.1 payload object (supports both dict event items and JSON string consumers)
    payload_dict = {"type": event_type, "data": data, "timestamp": time.time()}
    for q in list(event_queues):
        try:
            if q.full():
                try:
                    q.get_nowait()
                except Exception:
                    pass
            q.put_nowait(payload_dict)
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
