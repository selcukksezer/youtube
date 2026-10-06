"""
services/gallery_cache.py — Production Gallery Thumbnail Cache & Eviction Engine.
Ported and evolved from reference_repos/agnes-video-generator/core/gallery_cache.py
and reference_repos2/MoneyPrinterTurbo/app/services/material_cache.py
(Plan Section 28.1 & Section 10.4).

Provides:
- Isolated thumbnail storage in ``output/gallery_cache/`` without polluting video directories.
- Fast lazy thumbnail generation via FFmpeg (480p preview frame).
- Strict task_id alphanumeric whitelist and safe_join containment (anti-traversal).
- 256 striped locks to eliminate race conditions and parallel extraction collisions.
- LRU memory/disk eviction policy and automated stale cache cleanup.
"""
from __future__ import annotations

import collections
import hashlib
import logging
import os
import subprocess
import tempfile
import threading
import time
from typing import Dict, Optional, Tuple

import imageio_ffmpeg

import config
from services.path_security import (
    UnsafePathError,
    safe_join,
    validate_asset_path,
    validate_task_id,
)

logger = logging.getLogger(__name__)

_CACHE_LOCKS: Tuple[threading.Lock, ...] = tuple(threading.Lock() for _ in range(256))
_CLEANUP_LOCK = threading.Lock()


def _striped_lock(key: str) -> threading.Lock:
    idx = int(hashlib.md5(str(key).encode("utf-8", "replace")).hexdigest()[:2], 16)
    return _CACHE_LOCKS[idx % len(_CACHE_LOCKS)]


class GalleryCache:
    """
    Manages lazy extraction, caching, and LRU eviction of video preview thumbnails.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        max_items: int = 300,
        max_age_seconds: int = 7 * 86400,
    ):
        self.cache_dir = cache_dir or os.path.join(
            getattr(config, "OUTPUT_DIR", os.path.join(os.getcwd(), "output")),
            "gallery_cache",
        )
        self.max_items = max_items
        self.max_age_seconds = max_age_seconds
        self._lru_access: collections.OrderedDict[str, float] = collections.OrderedDict()
        self._lru_lock = threading.Lock()
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_thumb_path(self, task_id: str) -> Optional[str]:
        """
        Derives the secure absolute thumbnail path for a validated task_id.
        Returns None if task_id fails whitelist validation.
        """
        try:
            valid_id = validate_task_id(task_id)
            return safe_join(self.cache_dir, f"{valid_id}.jpg")
        except UnsafePathError as err:
            logger.warning("[GalleryCache] Rejected invalid task_id %r: %s", task_id, err)
            return None

    def has_thumb(self, task_id: str) -> bool:
        """Checks if a valid, non-empty thumbnail already exists on disk."""
        path = self.get_thumb_path(task_id)
        return bool(path and os.path.isfile(path) and os.path.getsize(path) > 1000)

    def get_thumb_url(self, task_id: str) -> Optional[str]:
        """Returns the public web URL path for the thumbnail if it exists."""
        if not self.has_thumb(task_id):
            return None
        valid_id = validate_task_id(task_id)
        return f"/output/gallery_cache/{valid_id}.jpg"

    def ensure_thumb(
        self,
        task_id: str,
        video_path: str,
        timestamp_sec: float = 1.0,
        timeout_sec: int = 30,
    ) -> Optional[str]:
        """
        Guarantees thumbnail availability: returns existing cache or lazily extracts single frame.
        Guards against path traversal, concurrent duplicate extraction, and corrupted videos.
        """
        thumb_path = self.get_thumb_path(task_id)
        if not thumb_path:
            return None

        # Quick hit
        if os.path.isfile(thumb_path) and os.path.getsize(thumb_path) > 1000:
            with self._lru_lock:
                self._lru_access[task_id] = time.time()
                self._lru_access.move_to_end(task_id)
            return thumb_path

        if not video_path:
            return None

        try:
            safe_source = validate_asset_path(video_path)
        except UnsafePathError as err:
            logger.warning("[GalleryCache] Unsafe video source path %r: %s", video_path, err)
            return None

        if not os.path.isfile(safe_source) or os.path.getsize(safe_source) < 1000:
            return None

        # Striped lock around the extraction to prevent parallel ffmpeg collisions for the same task
        with _striped_lock(task_id):
            # Double check after lock
            if os.path.isfile(thumb_path) and os.path.getsize(thumb_path) > 1000:
                with self._lru_lock:
                    self._lru_access[task_id] = time.time()
                    self._lru_access.move_to_end(task_id)
                return thumb_path

            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            os.makedirs(self.cache_dir, exist_ok=True)
            tmp_thumb = thumb_path + f".tmp_{os.getpid()}_{time.time_ns()}.jpg"

            try:
                cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{max(0.1, float(timestamp_sec)):.2f}",
                    "-i",
                    safe_source,
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=480:-2",
                    "-q:v",
                    "4",
                    tmp_thumb,
                ]
                res = subprocess.run(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=timeout_sec,
                )
                if res.returncode != 0 or not os.path.isfile(tmp_thumb) or os.path.getsize(tmp_thumb) < 500:
                    # Fallback to frame 0 if video is shorter than timestamp_sec
                    cmd[4] = "0.0"
                    res = subprocess.run(
                        cmd,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        check=False,
                        timeout=timeout_sec,
                    )

                if os.path.isfile(tmp_thumb) and os.path.getsize(tmp_thumb) > 500:
                    os.replace(tmp_thumb, thumb_path)
                    with self._lru_lock:
                        self._lru_access[task_id] = time.time()
                        self._lru_access.move_to_end(task_id)
                        if len(self._lru_access) > self.max_items:
                            self._evict_oldest()
                    return thumb_path
                else:
                    logger.warning("[GalleryCache] Failed to extract thumbnail for %s", task_id)
                    return None
            except Exception as exc:
                logger.warning("[GalleryCache] Error generating thumbnail for %s: %s", task_id, exc)
                return None
            finally:
                if os.path.isfile(tmp_thumb):
                    try:
                        os.remove(tmp_thumb)
                    except OSError:
                        pass

    def _evict_oldest(self) -> None:
        """Internal helper to evict least recently used entries."""
        while len(self._lru_access) > self.max_items:
            oldest_id, _ = self._lru_access.popitem(last=False)
            t_path = self.get_thumb_path(oldest_id)
            if t_path and os.path.isfile(t_path):
                try:
                    os.remove(t_path)
                except OSError:
                    pass

    def cleanup_expired(self) -> int:
        """
        Removes thumbnails older than max_age_seconds and orphaned temporary files.
        Returns count of removed files.
        """
        with _CLEANUP_LOCK:
            removed = 0
            now = time.time()
            if not os.path.isdir(self.cache_dir):
                return 0

            for entry in os.scandir(self.cache_dir):
                if entry.name.endswith(".tmp") or ".tmp_" in entry.name:
                    # Remove dangling temp files older than 5 minutes
                    if now - entry.stat().st_mtime > 300:
                        try:
                            os.remove(entry.path)
                            removed += 1
                        except OSError:
                            pass
                    continue

                if entry.name.endswith(".jpg"):
                    mtime = entry.stat().st_mtime
                    if now - mtime > self.max_age_seconds:
                        try:
                            os.remove(entry.path)
                            removed += 1
                        except OSError:
                            pass

            return removed


# Global singleton instance
gallery_cache = GalleryCache()
