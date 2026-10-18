"""
Server state, concurrency locks, and SSE event streaming.
"""
import json
import time
import asyncio
import threading
import logging
from typing import List, Any, Optional

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

# Per-task render state isolation registry
render_tasks_by_id: dict[str, dict] = {}


def register_task_state(task_id: str, data: dict) -> dict:
    """Register or update isolated state for a specific render task_id."""
    if not task_id:
        return {}
    with render_lock:
        existing = render_tasks_by_id.get(task_id, {})
        updated = {
            "task_id": task_id,
            "is_rendering": True,
            "cancel_requested": False,
            **existing,
            **(data or {}),
        }
        render_tasks_by_id[task_id] = updated
        return dict(updated)


def is_task_cancelled(task_id: Optional[str]) -> bool:
    """Check whether a specific task_id (or global render state) has cancellation requested."""
    if current_render_state.get("cancel_requested", False):
        return True
    if not task_id:
        return False
    with render_lock:
        task_state = render_tasks_by_id.get(task_id)
        return bool(task_state and task_state.get("cancel_requested", False))


def clear_task_state(task_id: Optional[str]) -> None:
    """Remove isolated state for a completed/cancelled task_id."""
    if not task_id:
        return
    with render_lock:
        render_tasks_by_id.pop(task_id, None)


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
        logger.exception(
            "Render event payload sanitization failed; %s event was not broadcast",
            event_type,
        )
        raise
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
            database.append_render_job_event(job_id, event_type, data)
            if event_type == "progress" and isinstance(data, dict):
                job = database.get_render_job(job_id)
                job_status = (
                    job["status"]
                    if job and job["status"] in ("cancelling", "completed", "failed", "cancelled")
                    else "rendering"
                )
                database.update_render_job(
                    job_id, status=job_status, percent=int(data.get("percent", 0)),
                    step=str(data.get("step", "Render ediliyor")),
                )
            elif event_type == "complete":
                url = data.get("url") if isinstance(data, dict) else None
                database.update_render_job(job_id, status="completed", percent=100,
                                           step="Tamamlandı", output_url=url or "")
            elif event_type == "error":
                cancelled = bool(current_render_state.get("cancel_requested"))
                database.update_render_job(
                    job_id,
                    status="cancelled" if cancelled else "failed",
                    step="İptal edildi" if cancelled else "Başarısız",
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
            next_stream = getattr(original_stdout, "terminal", None) or getattr(
                original_stdout, "original_stdout", None
            )
            if next_stream is None or next_stream is original_stdout:
                break
            original_stdout = next_stream
        self.terminal = original_stdout
        self.original_stdout = original_stdout

    def write(self, buf):
        self.terminal.write(buf)
        msg = buf.strip()
        if msg:
            broadcast_event("log", msg)

    def flush(self):
        self.terminal.flush()

    def __getattr__(self, name):
        # encoding / isatty / fileno etc. — libraries poke at sys.stdout
        return getattr(self.terminal, name)
