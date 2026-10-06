"""
services/sse_log_stream.py — Thread-Safe Ring Buffer SSE Log Streamer.

Adapted and evolved from reference_repos2/MoneyPrinter (Backend/logstream.py).
Provides:
1. Thread-safe bounded ring buffer (default 500 entries) with non-blocking oldest-eviction.
2. Automatic terminal ANSI escape code stripping.
3. Standardized SSE formatting (data: {...}\\n\\n) with keepalive heartbeats (: keepalive\\n\\n).
4. Lifecycle control events (progress, log, complete, error, cancelled).
"""

from __future__ import annotations

import json
import queue
import re
import time
from typing import Any, Dict, Generator, Optional


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def strip_ansi_codes(text: str) -> str:
    """Removes terminal escape codes so clean text reaches browser clients."""
    if not text or not isinstance(text, str):
        return ""
    return _ANSI_ESCAPE_RE.sub("", text)


class SSELogStream:
    """Thread-safe log queue that doubles as an SSE generator for real-time WebUI updates."""

    def __init__(self, maxsize: int = 500):
        self.maxsize = maxsize
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)

    def clear(self) -> None:
        """Drains all pending items from the queue."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def push(self, message: str, level: str = "info", extra: Optional[Dict[str, Any]] = None) -> None:
        """Adds a log entry. Safely evicts the oldest entry if the queue is full."""
        clean_msg = strip_ansi_codes(str(message)).strip()
        if not clean_msg:
            return

        entry = {
            "type": "log",
            "message": clean_msg,
            "level": str(level).lower(),
            "timestamp": round(time.time(), 3),
        }
        if extra:
            entry.update(extra)

        self._safe_put(entry)

    def push_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Pushes lifecycle control events (e.g. progress, complete, error, cancelled)."""
        entry = {
            "type": str(event_type).lower(),
            "timestamp": round(time.time(), 3),
            **(data or {}),
        }
        self._safe_put(entry)

    def _safe_put(self, entry: Dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(entry)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(entry)
            except queue.Full:
                pass

    def stream(self, timeout: float = 25.0) -> Generator[str, None, None]:
        """
        Yields standard SSE formatted lines.
        Sends keepalive comments periodically to prevent browser socket timeout.
        Terminates cleanly on final events (complete, error, cancelled).
        """
        while True:
            try:
                entry = self._queue.get(timeout=timeout)
                yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"
                if entry.get("type") in ("complete", "error", "cancelled"):
                    return
            except queue.Empty:
                # Keep connection alive through proxies/firewalls
                yield ": keepalive\n\n"

    def size(self) -> int:
        return self._queue.qsize()


# Global default log stream instance
GLOBAL_LOG_STREAM = SSELogStream()
