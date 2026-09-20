"""
P2-02: Shared post-render humanization — metadata, file aging, MP4 uniqueness.
Used by FFmpeg graph path, MoviePy compose path, and render_worker.
"""
from __future__ import annotations

import os
import random
import time
from typing import Any, Dict


def apply_post_render_humanization(video_path: str, title: str = "") -> Dict[str, Any]:
    """
    Wire existing anti-detect modules after encode:
    - Rule 30: MP4 free-atom size variation
    - Rule 29: ctime/mtime backdating
    - Items 127+128: metadata strip + fake NLE signature
    - Item 429: hash scramble
    """
    result: Dict[str, Any] = {
        "path": video_path,
        "size_delta_kb": 0,
        "aged_minutes": 0,
        "metadata_applied": False,
        "hash_scrambled": False,
    }
    if not video_path or not os.path.exists(video_path):
        return result

    try:
        from anti_detect_engine import anti_detect_engine

        size_res = anti_detect_engine.apply_video_size_variation(video_path)
        if size_res.get("success"):
            result["size_delta_kb"] = size_res.get("delta_kb", 0)
    except Exception as exc:
        print(f"  [PostRender] Size variation note: {exc}")

    try:
        past_secs = random.randint(900, 2700)
        aged_time = time.time() - past_secs
        os.utime(video_path, (aged_time, aged_time))
        result["aged_minutes"] = past_secs // 60
    except Exception as exc:
        print(f"  [PostRender] utime note: {exc}")

    try:
        from effects_engine import apply_full_metadata_pipeline, scramble_mp4_hash

        clean_title = title or os.path.splitext(os.path.basename(video_path))[0]
        meta_path = video_path.rsplit(".", 1)[0] + "_metadata.mp4"
        piped = apply_full_metadata_pipeline(video_path, meta_path, title=clean_title, nle_name="auto")
        if piped == meta_path and os.path.exists(meta_path):
            os.replace(meta_path, video_path)
            result["metadata_applied"] = True

        scramble_mp4_hash(video_path)
        result["hash_scrambled"] = True
    except Exception as exc:
        print(f"  [PostRender] Metadata pipeline note: {exc}")

    return result
