"""
services/process_cleaner.py — Subprocess Rollback, Temp File Cleanup & Error Categorization.

Adapted and evolved from reference_repos2/autoclip (backend/core/error_middleware.py & celery_app.py).
Provides:
1. SubprocessRollbackManager: Context manager registering active subprocesses and tempfiles,
   terminating zombie processes (FFmpeg, yt-dlp) and deleting orphan files upon unhandled error or cancel.
2. Structured Error Categorization matching autoclip schema (CONFIGURATION, NETWORK, API, FILE_IO, PROCESSING, VALIDATION, SYSTEM).
"""

from __future__ import annotations

import enum
import logging
import os
import signal
import subprocess
import time
import uuid
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("ProcessCleaner")


class ErrorCategory(str, enum.Enum):
    CONFIGURATION = "CONFIGURATION"
    NETWORK = "NETWORK"
    API = "API"
    FILE_IO = "FILE_IO"
    PROCESSING = "PROCESSING"
    VALIDATION = "VALIDATION"
    SYSTEM = "SYSTEM"


def categorize_exception(exc: Exception, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Classifies an arbitrary exception into a standardized error response payload."""
    exc_type = type(exc).__name__
    exc_msg = str(exc)
    req_id = request_id or str(uuid.uuid4())

    category = ErrorCategory.SYSTEM
    error_code = "INTERNAL_ERROR"

    if isinstance(exc, (FileNotFoundError, PermissionError, IsADirectoryError)):
        category = ErrorCategory.FILE_IO
        error_code = "FILE_ACCESS_ERROR"
    elif isinstance(exc, (ValueError, TypeError, KeyError)):
        category = ErrorCategory.VALIDATION
        error_code = "INVALID_PAYLOAD"
    elif isinstance(exc, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
        category = ErrorCategory.PROCESSING
        error_code = "SUBPROCESS_EXECUTION_FAILURE"
    elif "connect" in exc_msg.lower() or "timeout" in exc_msg.lower() or "socket" in exc_msg.lower():
        category = ErrorCategory.NETWORK
        error_code = "NETWORK_UNAVAILABLE"
    elif "api" in exc_msg.lower() or "key" in exc_msg.lower() or "auth" in exc_msg.lower():
        category = ErrorCategory.API
        error_code = "EXTERNAL_API_ERROR"

    return {
        "error": {
            "code": error_code,
            "category": category.value,
            "type": exc_type,
            "message": exc_msg,
            "request_id": req_id,
            "timestamp": round(time.time(), 3),
        }
    }


class SubprocessRollbackManager:
    """Tracks active subprocesses and temporary files for guaranteed cleanup on failure/cancel."""

    def __init__(self):
        self._active_processes: Set[subprocess.Popen] = set()
        self._temp_files: Set[str] = set()

    def register_process(self, proc: subprocess.Popen) -> None:
        if proc and isinstance(proc, subprocess.Popen):
            self._active_processes.add(proc)

    def unregister_process(self, proc: subprocess.Popen) -> None:
        self._active_processes.discard(proc)

    def register_temp_file(self, file_path: str) -> None:
        if file_path and isinstance(file_path, str):
            self._temp_files.add(file_path)

    def unregister_temp_file(self, file_path: str) -> None:
        self._temp_files.discard(file_path)

    def terminate_all(self, graceful_timeout: float = 1.0) -> int:
        """Terminates all registered running processes cleanly, then forces SIGKILL if necessary."""
        killed_count = 0
        for proc in list(self._active_processes):
            try:
                if proc.poll() is None:
                    proc.terminate()
                    killed_count += 1
            except Exception as e:
                logger.debug(f"Error terminating process {proc.pid}: {e}")

        # Wait briefly for graceful termination
        time.sleep(min(graceful_timeout, 0.5))

        # Force kill any lingering zombie processes
        for proc in list(self._active_processes):
            try:
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass
            finally:
                self._active_processes.discard(proc)

        return killed_count

    def cleanup_temp_files(self) -> int:
        """Removes all registered temporary artifacts without crashing."""
        deleted_count = 0
        for fpath in list(self._temp_files):
            try:
                if os.path.exists(fpath):
                    if os.path.isdir(fpath):
                        import shutil
                        shutil.rmtree(fpath, ignore_errors=True)
                    else:
                        os.remove(fpath)
                    deleted_count += 1
            except Exception as e:
                logger.debug(f"Failed to delete temp file {fpath}: {e}")
            finally:
                self._temp_files.discard(fpath)

        return deleted_count

    def rollback(self) -> Dict[str, int]:
        """Convenience method executing full emergency teardown."""
        procs_killed = self.terminate_all()
        files_deleted = self.cleanup_temp_files()
        return {"processes_killed": procs_killed, "files_deleted": files_deleted}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.warning(f"Rollback triggered due to exception: {exc_val}")
            self.rollback()


GLOBAL_ROLLBACK_MANAGER = SubprocessRollbackManager()
