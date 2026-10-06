"""
Tests for Chapter 10.1: Server-Sent Events (SSE) Canlı Log ve İlerleme Akışı
Covers:
- Section 10.1 canonical message formatting:
  event: progress
  data: {"percent": 59, "step": "[Compliance] visual_credits hazir"}
  event: log
  data: [22:04:11] [Director] Plan derlendi: 10 sahne, 58.4s
- Thread-safe state snapshot and refresh replay (get_current_render_snapshot)
- Slow-consumer protection (queue overflow & drop-oldest backpressure)
- FastAPI /api/events endpoint headers (text/event-stream, no-cache, X-Accel-Buffering: no)
- SSE handshake retry period
"""
import asyncio
import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from server_core.state import (
    format_sse_message,
    get_current_render_snapshot,
    broadcast_event,
    current_render_state,
    event_queues,
    render_lock,
)
from routers.video_router import sse_events


def test_format_sse_message_canonical_progress():
    payload = {"percent": 59, "step": "[Compliance] visual_credits hazir"}
    formatted = format_sse_message("progress", payload, timestamp=1700000000.0)

    assert formatted.startswith("event: progress\n")
    assert "\ndata: " in formatted
    assert formatted.endswith("\n\n")

    # Verify data line parses back to json
    data_line = [line for line in formatted.splitlines() if line.startswith("data: ")][0]
    data_json = json.loads(data_line[len("data: "):])
    assert data_json["percent"] == 59
    assert data_json["step"] == "[Compliance] visual_credits hazir"
    assert data_json["timestamp"] == 1700000000.0


def test_format_sse_message_canonical_log():
    log_text = "[22:04:11] [Director] Plan derlendi: 10 sahne, 58.4s"
    formatted = format_sse_message("log", log_text)

    assert formatted.startswith("event: log\n")
    assert f"data: {log_text}\n\n" in formatted


def test_format_sse_message_complete_and_error():
    complete_payload = {"url": "/output/test_short.mp4", "percent": 100}
    formatted_complete = format_sse_message("complete", complete_payload)
    assert formatted_complete.startswith("event: complete\n")
    assert "/output/test_short.mp4" in formatted_complete

    error_text = "FFmpeg out of memory error"
    formatted_error = format_sse_message("error", error_text)
    assert formatted_error.startswith("event: error\n")
    assert error_text in formatted_error


def test_get_current_render_snapshot_structure():
    with render_lock:
        current_render_state["is_rendering"] = True
        current_render_state["percent"] = 42
        current_render_state["step"] = "Altyazılar derleniyor..."
        current_render_state["stage"] = "SUBTITLES"
        current_render_state["logs"] = ["[10:00:00] Initialized", "[10:00:01] Processing"]

    snapshot = get_current_render_snapshot()
    assert snapshot["is_rendering"] is True
    assert snapshot["percent"] == 42
    assert snapshot["step"] == "Altyazılar derleniyor..."
    assert snapshot["stage"] == "SUBTITLES"
    assert len(snapshot["logs"]) == 2

    # Clean up
    with render_lock:
        current_render_state["is_rendering"] = False
        current_render_state["percent"] = 0
        current_render_state["logs"] = []


def test_broadcast_event_slow_consumer_queue_overflow():
    test_q = asyncio.Queue(maxsize=3)
    event_queues.append(test_q)

    try:
        # Fill queue to max capacity
        broadcast_event("log", "Line 1")
        broadcast_event("log", "Line 2")
        broadcast_event("log", "Line 3")
        assert test_q.full()

        # Overflow: line 4 should cause drop-oldest without exception
        broadcast_event("log", "Line 4")
        assert test_q.qsize() == 3

        # Read back queue: Line 1 was dropped, Line 2, 3, 4 remain
        item1 = test_q.get_nowait()
        item2 = test_q.get_nowait()
        item3 = test_q.get_nowait()
        assert item1["data"] == "Line 2"
        assert item2["data"] == "Line 3"
        assert item3["data"] == "Line 4"
    finally:
        if test_q in event_queues:
            event_queues.remove(test_q)


def test_sse_events_endpoint_response_headers():
    async def _run():
        mock_request = MagicMock()
        mock_request.is_disconnected = AsyncMock(return_value=True)

        resp = await sse_events(mock_request)
        assert resp.media_type == "text/event-stream"
        assert resp.headers["Cache-Control"] == "no-cache"
        assert resp.headers["Connection"] == "keep-alive"
        assert resp.headers["X-Accel-Buffering"] == "no"

    asyncio.run(_run())
