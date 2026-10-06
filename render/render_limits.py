"""
render/render_limits.py — Hardware Resource & Render Concurrency Safeguards.

Adapted and evolved from reference_repos/short-video-maker
(remotion.config.ts, src/config.ts - concurrency and video cache limits).
Enforces system hardware boundaries (fps=30, 1080x1920 vertical canvas,
NVENC hardware encoder session caps, and RAM cache quotas) to prevent
OOM crashes, CPU thrashing, and encoder saturation.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RenderLimits:
    """System-wide video rendering constraints."""
    DEFAULT_FPS: int = 30
    VERTICAL_WIDTH: int = 1080
    VERTICAL_HEIGHT: int = 1920
    MAX_CONCURRENT_RENDERS: int = int(os.getenv("SHORTS_MAX_CONCURRENCY", "2"))
    MAX_VIDEO_CACHE_MB: int = int(os.getenv("SHORTS_VIDEO_CACHE_MB", "2048"))


class RenderConcurrencyGate:
    """
    Thread-safe and async-safe execution gate to prevent simultaneous
    heavy FFmpeg/NVENC encoding runs from exceeding GPU/CPU limits.
    """

    def __init__(self, max_concurrency: Optional[int] = None):
        self.max_concurrency = max(1, max_concurrency or RenderLimits.MAX_CONCURRENT_RENDERS)
        self._thread_semaphore = threading.BoundedSemaphore(self.max_concurrency)
        self._lock = threading.Lock()
        self._active_renders: int = 0
        self._queued_renders: int = 0
        self._peak_concurrent: int = 0
        self._total_served: int = 0

    @property
    def active_count(self) -> int:
        with self._lock:
            return self._active_renders

    @property
    def queued_count(self) -> int:
        with self._lock:
            return self._queued_renders

    def get_metrics(self) -> Dict[str, Any]:
        """Returns snapshot of current render concurrency and throughput."""
        with self._lock:
            return {
                "max_concurrency": self.max_concurrency,
                "active_renders": self._active_renders,
                "queued_renders": self._queued_renders,
                "peak_concurrent": self._peak_concurrent,
                "total_served": self._total_served,
                "available_slots": max(0, self.max_concurrency - self._active_renders),
            }

    @contextmanager
    def acquire_slot_sync(self, task_id: str = "anonymous", timeout: float = 60.0):
        """Synchronous context manager with timeout protection."""
        with self._lock:
            self._queued_renders += 1

        acquired = self._thread_semaphore.acquire(timeout=timeout)
        with self._lock:
            self._queued_renders -= 1

        if not acquired:
            raise TimeoutError(
                f"Render concurrency limit reached ({self.max_concurrency}). "
                f"Task {task_id} timed out after {timeout}s waiting for a render slot."
            )

        with self._lock:
            self._active_renders += 1
            if self._active_renders > self._peak_concurrent:
                self._peak_concurrent = self._active_renders
            self._total_served += 1

        try:
            yield
        finally:
            with self._lock:
                self._active_renders -= 1
            self._thread_semaphore.release()

    @asynccontextmanager
    async def acquire_slot(self, task_id: str = "anonymous", timeout: float = 60.0):
        """Asynchronous context manager using non-blocking executor wait."""
        loop = asyncio.get_running_loop()
        start_time = time.monotonic()

        with self._lock:
            self._queued_renders += 1

        acquired = False
        try:
            while not acquired:
                # Try acquiring without blocking
                acquired = self._thread_semaphore.acquire(blocking=False)
                if acquired:
                    break
                if (time.monotonic() - start_time) >= timeout:
                    raise TimeoutError(
                        f"Async render concurrency limit reached ({self.max_concurrency}). "
                        f"Task {task_id} timed out after {timeout}s."
                    )
                await asyncio.sleep(0.1)
        finally:
            with self._lock:
                self._queued_renders -= 1

        with self._lock:
            self._active_renders += 1
            if self._active_renders > self._peak_concurrent:
                self._peak_concurrent = self._active_renders
            self._total_served += 1

        try:
            yield
        finally:
            with self._lock:
                self._active_renders -= 1
            self._thread_semaphore.release()


# Global default concurrency gate
GLOBAL_RENDER_GATE = RenderConcurrencyGate()
