"""Striped disk locks and atomic replace. MoneyPrinterTurbo material_cache pattern."""
from __future__ import annotations

import hashlib
import os
import threading

_CACHE_LOCKS = tuple(threading.Lock() for _ in range(256))


def lock_for_key(key: str) -> threading.Lock:
    digest = hashlib.sha256(str(key).encode("utf-8", "replace")).digest()
    return _CACHE_LOCKS[digest[0]]


def atomic_replace(tmp_path: str, final_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(final_path)) or ".", exist_ok=True)
    os.replace(tmp_path, final_path)
