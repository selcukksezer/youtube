"""
services/llm_cache.py — Deterministic LLM Response Disk Cache.

Adapted and evolved from reference_repos2/MoneyPrinterV2 (src/cache.py).
Caches expensive OpenAI, Gemini, and Ollama completion responses using
sha256 prompt signatures, atomic temporary file replacement, and striped locks.
Saves API quota and accelerates iterative testing.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from typing import Any, Dict, Optional


_CACHE_LOCKS = tuple(threading.Lock() for _ in range(256))
DEFAULT_LLM_CACHE_TTL = 7 * 24 * 3600  # 7 days


class LLMResponseCache:
    """Thread-safe persistent cache for LLM completion responses."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "llm_responses"
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def _hash_key(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        param_str = json.dumps(extra_params or {}, sort_keys=True)
        raw = f"{model.strip()}:{system_prompt.strip()}:{user_prompt.strip()}:{param_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_lock(self, key: str) -> threading.Lock:
        slot = int(key[:4], 16) % len(_CACHE_LOCKS)
        return _CACHE_LOCKS[slot]

    def get(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        extra_params: Optional[Dict[str, Any]] = None,
        ttl: int = DEFAULT_LLM_CACHE_TTL,
    ) -> Optional[str]:
        """Returns cached text completion if present and fresh."""
        key = self._hash_key(model, system_prompt, user_prompt, extra_params)
        path = os.path.join(self.cache_dir, f"{key}.json")

        with self._get_lock(key):
            if not os.path.isfile(path):
                self.misses += 1
                return None
            try:
                stat = os.stat(path)
                if (time.time() - stat.st_mtime) > ttl:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    self.misses += 1
                    return None

                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.hits += 1
                return data.get("response")
            except Exception:
                self.misses += 1
                return None

    def set(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_text: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Atomically saves LLM completion response into disk cache."""
        if not response_text:
            return

        key = self._hash_key(model, system_prompt, user_prompt, extra_params)
        target_path = os.path.join(self.cache_dir, f"{key}.json")

        payload = {
            "model": model,
            "created_at": time.time(),
            "response": response_text,
            "extra_params": extra_params or {},
        }

        content = json.dumps(payload, ensure_ascii=False, indent=2)

        with self._get_lock(key):
            try:
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


# Global singleton
GLOBAL_LLM_CACHE = LLMResponseCache()
