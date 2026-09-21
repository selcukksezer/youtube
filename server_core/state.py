"""
Server state, concurrency locks, and SSE event streaming.
"""
import json
import time
import asyncio
import threading
from typing import List, Any

# Concurrency lock to prevent multiple heavy ffmpeg/moviepy renders simultaneously
render_lock = threading.Lock()
is_rendering_active = False

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

    payload = json.dumps({"type": event_type, "data": data, "timestamp": time.time()})
    for q in list(event_queues):
        try:
            q.put_nowait(payload)
        except Exception:
            pass


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
