"""Persistent, source-aware cache for local transcript results."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import tempfile
import threading
from typing import Any, Callable, Dict, List, Optional


DEFAULT_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "shorts_video_creators", "transcript_cache"
)
_CACHE_FORMAT_VERSION = 1
_CACHE_LOCKS = tuple(threading.Lock() for _ in range(256))
logger = logging.getLogger(__name__)


class LocalTranscriptCache:
    """Caches non-empty local ASR transcripts by source and transcription inputs."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR

    @staticmethod
    def _source_identity(source_path: str) -> str:
        canonical_path = os.path.normcase(os.path.realpath(os.path.abspath(source_path)))
        return hashlib.sha256(canonical_path.encode("utf-8")).hexdigest()

    @staticmethod
    def _fingerprint(
        source_path: str,
        language: str,
        hotwords: str,
        model: Dict[str, str],
    ) -> Dict[str, Any]:
        stat = os.stat(source_path)
        return {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "language": language.strip().lower(),
            "hotwords_sha256": hashlib.sha256(hotwords.encode("utf-8")).hexdigest(),
            "model": model,
        }

    @staticmethod
    def _get_lock(key: str) -> threading.Lock:
        return _CACHE_LOCKS[int(key[:8], 16) % len(_CACHE_LOCKS)]

    @staticmethod
    def _validated_segments(value: Any) -> Optional[List[Dict[str, Any]]]:
        if not isinstance(value, list) or not value:
            return None

        validated: List[Dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str):
                return None
            try:
                start = float(item["start"])
                end = float(item["end"])
            except (KeyError, TypeError, ValueError):
                return None
            if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
                return None
            text = item["text"].strip()
            if not text:
                return None
            validated.append({"start": start, "end": end, "text": text})
        return validated

    def _read(self, path: str, fingerprint: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("Failed to read transcript cache %s: %s", os.path.basename(path), exc)
            return None

        if (
            not isinstance(payload, dict)
            or payload.get("version") != _CACHE_FORMAT_VERSION
            or payload.get("fingerprint") != fingerprint
        ):
            return None

        segments = self._validated_segments(payload.get("segments"))
        if segments is None:
            logger.warning("Ignoring empty or invalid transcript cache %s", os.path.basename(path))
        return segments

    def _write(
        self,
        path: str,
        key: str,
        fingerprint: Dict[str, Any],
        segments: List[Dict[str, Any]],
    ) -> None:
        temp_path: Optional[str] = None
        payload = {
            "version": _CACHE_FORMAT_VERSION,
            "fingerprint": fingerprint,
            "segments": segments,
        }
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.cache_dir,
                delete=False,
                suffix=".tmp",
                prefix=f".{key}-",
            ) as handle:
                temp_path = handle.name
                json.dump(payload, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("Failed to write transcript cache %s: %s", os.path.basename(path), exc)
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError as cleanup_exc:
                    logger.warning("Failed to remove temporary transcript cache: %s", cleanup_exc)

    def get_or_create(
        self,
        source_path: str,
        *,
        language: str,
        hotwords: str,
        model: Dict[str, str],
        producer: Callable[[], List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """Return a matching transcript or compute and atomically cache a non-empty result."""
        key = self._source_identity(source_path)
        fingerprint = self._fingerprint(source_path, language, hotwords, model)
        path = os.path.join(self.cache_dir, f"{key}.json")
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as exc:
            logger.warning("Transcript cache is unavailable; transcribing without cache: %s", exc)
            return producer()

        with self._get_lock(key):
            cached = self._read(path, fingerprint)
            if cached is not None:
                return cached

            segments = producer()
            validated = self._validated_segments(segments)
            if validated is not None:
                self._write(path, key, fingerprint, validated)
            return segments
