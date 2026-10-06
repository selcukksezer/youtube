"""
services/material_cache.py — Striped-Lock Persistent Stock Material Cache.

Adapted and evolved from reference_repos2/MoneyPrinterTurbo
(app/services/material_cache.py).
Solves disk cache lock contention under high-concurrency tasks via 256 striped
mutexes, guarantees crash-safe atomic writes via NamedTemporaryFile + os.replace,
and strips sensitive authorization credentials/query tokens from public URLs.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit


MATERIAL_SEARCH_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
_CACHE_FORMAT_VERSION = 2
_CACHE_LOCKS = tuple(threading.Lock() for _ in range(256))
_CACHE_FILE_PATTERN = re.compile(r"^[0-9a-f]{64}\.json$")
_CACHE_TEMP_FILE_PATTERN = re.compile(r"^\.[0-9a-f]{64}-[a-z0-9_]+\.tmp$")


def safe_public_url(value: Any) -> Optional[str]:
    """
    Strips query parameters and credentials from public URLs (MoneyPrinterTurbo pattern).
    Prevents temporary auth tokens or signed S3 keys from persisting into long-term cache.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = urlsplit(value.strip())
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            return None
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    except Exception:
        return None


class MaterialCache:
    """
    Thread-safe, multi-worker resilient cache for stock video/image search results.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "material_search"
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_lock(self, cache_key: str) -> threading.Lock:
        slot = int(hashlib.md5(cache_key.encode("utf-8")).hexdigest()[:4], 16) % len(_CACHE_LOCKS)
        return _CACHE_LOCKS[slot]

    def _cache_key(self, query: str, provider: str, aspect: str = "portrait") -> str:
        raw = f"{provider.strip().lower()}:{aspect.strip().lower()}:{query.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(
        self, query: str, provider: str, aspect: str = "portrait", ttl: int = MATERIAL_SEARCH_CACHE_TTL_SECONDS
    ) -> Optional[List[Dict[str, Any]]]:
        """Retrieves cached search items if present and not expired."""
        key = self._cache_key(query, provider, aspect)
        path = os.path.join(self.cache_dir, f"{key}.json")

        with self._get_lock(key):
            if not os.path.isfile(path):
                return None
            try:
                stat = os.stat(path)
                if (time.time() - stat.st_mtime) > ttl:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    return None

                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)

                if payload.get("version") == _CACHE_FORMAT_VERSION:
                    return payload.get("items")
            except Exception:
                return None
        return None

    def set(
        self, query: str, provider: str, items: List[Dict[str, Any]], aspect: str = "portrait"
    ) -> None:
        """
        Atomically saves search results into cache using temporary file + os.replace.
        Strips auth credentials from source URLs before persisting.
        """
        key = self._cache_key(query, provider, aspect)
        target_path = os.path.join(self.cache_dir, f"{key}.json")

        sanitized_items = []
        for item in items:
            it = dict(item)
            if "source_url" in it:
                it["source_url"] = safe_public_url(it["source_url"])
            sanitized_items.append(it)

        payload = {
            "version": _CACHE_FORMAT_VERSION,
            "created_at": time.time(),
            "query": query,
            "provider": provider,
            "aspect": aspect,
            "items": sanitized_items,
        }

        content = json.dumps(payload, ensure_ascii=False, indent=2)

        with self._get_lock(key):
            try:
                # Write to tempfile in the same directory, then rename atomically
                temp = tempfile.NamedTemporaryFile(
                    dir=self.cache_dir, delete=False, suffix=".tmp", prefix=f".{key}-"
                )
                temp.write(content.encode("utf-8"))
                temp.flush()
                temp.close()

                os.replace(temp.name, target_path)
            except Exception:
                if 'temp' in locals() and os.path.exists(temp.name):
                    try:
                        os.remove(temp.name)
                    except OSError:
                        pass

    def cleanup_expired(self, max_age_seconds: int = MATERIAL_SEARCH_CACHE_TTL_SECONDS) -> int:
        """Removes expired cache files and orphaned temporary write files."""
        now = time.time()
        cleaned_count = 0

        try:
            for fname in os.listdir(self.cache_dir):
                fpath = os.path.join(self.cache_dir, fname)
                if not os.path.isfile(fpath):
                    continue

                is_cache = _CACHE_FILE_PATTERN.match(fname)
                is_temp = _CACHE_TEMP_FILE_PATTERN.match(fname)

                if is_cache:
                    if (now - os.path.getmtime(fpath)) > max_age_seconds:
                        try:
                            os.remove(fpath)
                            cleaned_count += 1
                        except OSError:
                            pass
                elif is_temp:
                    # Clean temp files older than 15 minutes (abandoned writes)
                    if (now - os.path.getmtime(fpath)) > 900:
                        try:
                            os.remove(fpath)
                            cleaned_count += 1
                        except OSError:
                            pass
        except Exception:
            pass

        return cleaned_count


# Global singleton
GLOBAL_MATERIAL_CACHE = MaterialCache()
