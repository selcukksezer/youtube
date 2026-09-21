"""Disk cache keyed by prompt hash so retries do not burn quota."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from typing import Optional

_CACHE_DIRNAME = "ai_video_cache"


def cache_root(base_dir: Optional[str] = None) -> str:
    if base_dir:
        root = os.path.join(base_dir, _CACHE_DIRNAME)
    else:
        try:
            import config
            root = os.path.join(getattr(config, "BASE_DIR", "."), "data", _CACHE_DIRNAME)
        except Exception:
            root = os.path.join("data", _CACHE_DIRNAME)
    os.makedirs(root, exist_ok=True)
    return root


def prompt_hash(prompt: str, aspect: str = "9:16", duration: float = 5.0, provider: str = "") -> str:
    raw = f"{provider}|{aspect}|{round(float(duration), 1)}|{prompt.strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def cache_lookup(key: str, dest_path: str, base_dir: Optional[str] = None) -> Optional[str]:
    root = cache_root(base_dir)
    src = os.path.join(root, f"{key}.mp4")
    meta = os.path.join(root, f"{key}.json")
    if not (os.path.isfile(src) and os.path.getsize(src) > 10_000):
        return None
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    shutil.copy2(src, dest_path)
    return dest_path if os.path.isfile(dest_path) else None


def cache_store(key: str, video_path: str, meta: Optional[dict] = None, base_dir: Optional[str] = None) -> None:
    if not (os.path.isfile(video_path) and os.path.getsize(video_path) > 10_000):
        return
    root = cache_root(base_dir)
    dst = os.path.join(root, f"{key}.mp4")
    try:
        shutil.copy2(video_path, dst)
        if meta is not None:
            with open(os.path.join(root, f"{key}.json"), "w", encoding="utf-8") as fh:
                json.dump(meta, fh, ensure_ascii=False, indent=2)
    except OSError:
        pass
