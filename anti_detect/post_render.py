"""Compatibility hook for render paths.

Post-render anti-detect manipulation is disabled.  Keeping this function as a
no-op avoids breaking older callers while preserving the encoded file and its
timestamps exactly as produced by the renderer.
"""
from __future__ import annotations

import os
from typing import Any, Dict


def apply_post_render_humanization(video_path: str, title: str = "") -> Dict[str, Any]:
    """Return an audit record without modifying the file."""
    result: Dict[str, Any] = {
        "path": video_path,
        "size_delta_kb": 0,
        "aged_minutes": 0,
        "metadata_applied": False,
        "hash_scrambled": False,
    }
    if not video_path or not os.path.exists(video_path):
        return result

    return result
