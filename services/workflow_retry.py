"""
services/workflow_retry.py — Bounded Exponential Backoff Render Retry & Attempt Management.

Adapted and evolved from reference_repos2/video-autopilot-kit (src/workflow_render_retry.py).
Handles transient FFmpeg/GPU encoding failures (e.g. NVENC memory spikes, device contention)
with bounded retries, attempt isolation, and automatic software CPU fallback.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class RenderAttemptError(Exception):
    """Raised when all render retry attempts fail."""
    pass


class WorkflowRenderRetry:
    """Manages resilient render execution with isolated attempt artifacts."""

    @staticmethod
    def get_attempt_path(target_path: str, attempt: int) -> str:
        """Returns an isolated output path for each attempt."""
        if attempt < 1:
            raise ValueError("attempt must be at least 1")
        p = Path(target_path)
        return str(p.with_name(f"{p.stem}.attempt-{attempt:03d}{p.suffix}"))

    @classmethod
    def execute_render_with_retry(
        cls,
        render_fn: Callable[[str, bool], bool],
        output_path: str,
        max_attempts: int = 3,
        initial_backoff: float = 0.5,
        backoff_multiplier: float = 2.0,
        initial_use_gpu: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes render_fn(output_file, use_hardware_gpu).
        If attempt fails:
        1. Backs off exponentially.
        2. Unlinks broken attempt file.
        3. On final retry, switches to software CPU fallback.
        4. On success, moves attempt file cleanly to target output_path.
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if initial_backoff < 0:
            raise ValueError("initial_backoff must not be negative")

        last_error: Optional[str] = None
        attempt_history = []
        backoff = initial_backoff

        for attempt in range(1, max_attempts + 1):
            use_gpu = initial_use_gpu and attempt < max_attempts
            attempt_file = cls.get_attempt_path(output_path, attempt)

            try:
                os.unlink(attempt_file)
            except FileNotFoundError:
                pass

            t0 = time.time()
            cancelled: Optional[InterruptedError] = None
            try:
                success = render_fn(attempt_file, use_gpu)
                elapsed = round(time.time() - t0, 3)

                if success and os.path.exists(attempt_file) and os.path.getsize(attempt_file) > 0:
                    os.replace(attempt_file, output_path)

                    attempt_history.append({"attempt": attempt, "use_gpu": use_gpu, "elapsed_sec": elapsed, "success": True})
                    return {
                        "success": True,
                        "attempts_used": attempt,
                        "output_path": output_path,
                        "used_gpu": use_gpu,
                        "history": attempt_history,
                    }
                else:
                    last_error = f"Attempt {attempt} produced empty or missing file."
            except InterruptedError as exc:
                last_error = str(exc)
                elapsed = round(time.time() - t0, 3)
                cancelled = exc
            except Exception as exc:
                last_error = str(exc)
                elapsed = round(time.time() - t0, 3)

            attempt_history.append({"attempt": attempt, "use_gpu": use_gpu, "elapsed_sec": elapsed, "success": False, "error": last_error})

            try:
                os.unlink(attempt_file)
            except FileNotFoundError:
                pass

            if cancelled is not None:
                raise cancelled

            if attempt < max_attempts:
                time.sleep(backoff)
                backoff *= backoff_multiplier

        raise RenderAttemptError(f"Render failed after {max_attempts} attempts. Last error: {last_error}")


GLOBAL_RENDER_RETRY = WorkflowRenderRetry()
