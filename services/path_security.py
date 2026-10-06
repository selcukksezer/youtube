"""
services/path_security.py — Path security and traversal defense helpers.
Ported and evolved from reference_repos/agnes-video-generator/core/path_security.py
(Plan Section 28.1 & Section 17.1).

Defends against CodeQL py/path-injection, directory traversal (../),
Windows drive breakout, null-byte poisoning, and argument injection in subprocesses.
"""
from __future__ import annotations

import os
import re
import tempfile
from typing import Iterable, List, Optional

import config

__all__ = [
    "UnsafePathError",
    "safe_join",
    "safe_workspace_path",
    "validate_asset_path",
    "validate_task_id",
    "sanitize_filename",
]

_TASK_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.\-]")


class UnsafePathError(ValueError):
    """Raised when a path escapes its allowed root or contains dangerous characters."""
    pass


def safe_join(root: str, *parts: str) -> str:
    """
    Join ``parts`` onto ``root`` and guarantee the resulting path stays strictly inside ``root``.

    Uses realpath normalization to resolve symlinks and `..` segments, then verifies
    containment under root directory.

    Raises:
        UnsafePathError: if any part contains null bytes, or target escapes root.
    """
    if not root:
        raise UnsafePathError("Root directory must not be empty.")

    for p in parts:
        if "\x00" in str(p):
            raise UnsafePathError("Null byte detected in path component.")

    root_real = os.path.realpath(os.path.abspath(root))
    joined = os.path.join(root_real, *parts)
    target_real = os.path.realpath(os.path.abspath(joined))

    prefix = root_real if root_real.endswith(os.sep) else root_real + os.sep
    if target_real != root_real and not target_real.startswith(prefix):
        raise UnsafePathError(f"Path escapes root directory: {joined!r} (target: {target_real!r})")

    return target_real


def safe_workspace_path(path: str, *, allowed_root: Optional[str] = None) -> str:
    """
    Normalize a path and contain it within ``allowed_root`` (defaults to config.BASE_DIR).

    If ``path`` is relative, it is joined onto ``allowed_root``.
    If ``path`` is absolute, it is verified to be within ``allowed_root``.
    """
    root = os.path.realpath(os.path.abspath(allowed_root or config.BASE_DIR))
    if os.path.isabs(path):
        target = os.path.realpath(os.path.abspath(path))
        prefix = root if root.endswith(os.sep) else root + os.sep
        if target != root and not target.startswith(prefix):
            raise UnsafePathError(f"Absolute path outside allowed root: {path!r}")
        return target
    return safe_join(root, path)


def validate_asset_path(path: str, allowed_roots: Optional[Iterable[str]] = None) -> str:
    """
    Verifies that a given asset file path is contained within at least one approved project root.

    Approved defaults:
    - config.BASE_DIR
    - config.OUTPUT_DIR
    - config.BGM_DIR
    - config.AUDIO_DIR
    - config.ASSETS_DIR
    - System temp directory

    Returns normalized realpath if valid, raises UnsafePathError otherwise.
    """
    if not path or not isinstance(path, str):
        raise UnsafePathError("Asset path must be a non-empty string.")

    if "\x00" in path:
        raise UnsafePathError("Null byte detected in asset path.")

    target_real = os.path.realpath(os.path.abspath(path))

    if allowed_roots is None:
        roots = [
            getattr(config, "BASE_DIR", os.getcwd()),
            getattr(config, "OUTPUT_DIR", os.path.join(os.getcwd(), "output")),
            getattr(config, "BGM_DIR", os.path.join(os.getcwd(), "bgm")),
            getattr(config, "AUDIO_DIR", os.path.join(os.getcwd(), "audio")),
            getattr(config, "ASSETS_DIR", os.path.join(os.getcwd(), "assets")),
            tempfile.gettempdir(),
        ]
    else:
        roots = list(allowed_roots)

    for r in roots:
        if not r:
            continue
        r_real = os.path.realpath(os.path.abspath(r))
        prefix = r_real if r_real.endswith(os.sep) else r_real + os.sep
        if target_real == r_real or target_real.startswith(prefix):
            return target_real

    raise UnsafePathError(f"Asset path escapes all allowed roots: {path!r}")


def validate_task_id(task_id: str) -> str:
    """
    Validates a task or job ID against a strict alphanumeric whitelist (1-64 chars).
    Prevents path traversal, URL parameter injection, and CLI argument injection.
    """
    if not task_id or not isinstance(task_id, str):
        raise UnsafePathError("Task ID must be a non-empty string.")

    cleaned = task_id.strip()
    if not _TASK_ID_RE.fullmatch(cleaned):
        raise UnsafePathError(f"Invalid task ID format: {task_id!r} (must match {_TASK_ID_RE.pattern})")

    # Reject leading dashes to prevent CLI option injection (-i, --option)
    if cleaned.startswith("-"):
        raise UnsafePathError(f"Task ID cannot start with dash: {task_id!r}")

    return cleaned


def sanitize_filename(name: str, max_length: int = 120, fallback: str = "asset") -> str:
    """
    Sanitizes an untrusted filename for safe filesystem storage.
    Replaces unsafe characters, strips path delimiters, and prevents dot/dash prefixes.
    """
    base = os.path.basename(name or "").strip()
    if not base:
        return fallback

    safe = _SAFE_FILENAME_RE.sub("_", base)
    # Strip leading dots or dashes
    safe = safe.lstrip(".-")
    if not safe:
        safe = fallback

    if len(safe) > max_length:
        root, ext = os.path.splitext(safe)
        ext = ext[:16]
        root = root[: max_length - len(ext)]
        safe = root + ext

    return safe or fallback
