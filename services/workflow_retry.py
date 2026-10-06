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
from typing import Any, Callable, Dict, Optional, Tuple


class RenderAttemptError(Exception):
    """Raised when all render retry attempts fail."""
    pass


class WorkflowRenderRetry:
    """Manages resilient render execution with isolated attempt artifacts."""

    @staticmethod
    def get_attempt_path(target_path: str, attempt: int) -> str:
        """Returns isolated output path for attempt (e.g. video.attempt-002.mp4)."""
        if attempt <= 1:
            return target_path
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
    ) -> Dict[str, Any]:
        """
        Executes render_fn(output_file, use_hardware_gpu).
        If attempt fails:
        1. Backs off exponentially.
        2. Unlinks broken attempt file.
        3. On final retry, switches to software CPU fallback.
        4. On success, moves attempt file cleanly to target output_path.
        """
        last_error: Optional[str] = None
        attempt_history = []
        backoff = initial_backoff

        for attempt in range(1, max_attempts + 1):
            use_gpu = (attempt < max_attempts)  # Fall back to software CPU on final attempt
            attempt_file = cls.get_attempt_path(output_path, attempt)

            # Ensure clean start
            if os.path.exists(attempt_file):
                try:
                    os.unlink(attempt_file)
                except OSError:
                    pass

            t0 = time.time()
            try:
                success = render_fn(attempt_file, use_gpu)
                elapsed = round(time.time() - t0, 3)

                if success and os.path.exists(attempt_file) and os.path.getsize(attempt_file) > 0:
                    # Rename to final output_path if not already identical
                    if attempt_file != output_path:
                        if os.path.exists(output_path):
                            os.unlink(output_path)
                        os.rename(attempt_file, output_path)

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
            except Exception as e:
                last_error = str(e)
                elapsed = round(time.time() - t0, 3)

            attempt_history.append({"attempt": attempt, "use_gpu": use_gpu, "elapsed_sec": elapsed, "success": False, "error": last_error})

            # Cleanup broken attempt file
            if os.path.exists(attempt_file):
                try:
                    os.unlink(attempt_file)
                except OSError:
                    pass

            if attempt < max_attempts:
                time.sleep(backoff)
                backoff *= backoff_multiplier

        raise RenderAttemptError(f"Render failed after {max_attempts} attempts. Last error: {last_error}")


GLOBAL_RENDER_RETRY = WorkflowRenderRetry()
