"""Shared HTTP helpers for AI video adapters (no heavy SDKs required)."""
from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, Optional, Tuple

import requests

USER_AGENT = "youtubeoto-ai-video/1.0"
_SKIP_LOGGED: set = set()


def log_skip_once(provider: str, reason: str) -> None:
    key = f"{provider}:{reason}"
    if key in _SKIP_LOGGED:
        return
    _SKIP_LOGGED.add(key)
    print(f"    [AI-VIDEO:{provider}] skip — {reason}")


def env_key(*names: str) -> str:
    for n in names:
        v = (os.getenv(n) or "").strip()
        if v:
            return v
    # also check config module if loaded
    try:
        import config
        for n in names:
            v = str(getattr(config, n, "") or "").strip()
            if v:
                return v
    except Exception:
        pass
    return ""


def download_url(url: str, path: str, timeout: int = 90, headers: Optional[dict] = None) -> bool:
    try:
        hdrs = {"User-Agent": USER_AGENT}
        if headers:
            hdrs.update(headers)
        with requests.get(url, stream=True, timeout=timeout, headers=hdrs) as r:
            r.raise_for_status()
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "wb") as fh:
                for chunk in r.iter_content(256 * 1024):
                    if chunk:
                        fh.write(chunk)
        return os.path.isfile(path) and os.path.getsize(path) > 10_000
    except Exception as exc:
        print(f"    [AI-VIDEO:dl] {exc}")
        return False


def write_bytes(data: bytes, path: str) -> bool:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return os.path.isfile(path) and os.path.getsize(path) > 10_000
    except OSError as exc:
        print(f"    [AI-VIDEO:write] {exc}")
        return False


def decode_data_uri(uri: str, path: str) -> bool:
    if not uri or "," not in uri:
        return False
    _, _, payload = uri.partition(",")
    try:
        return write_bytes(base64.b64decode(payload), path)
    except Exception as exc:
        print(f"    [AI-VIDEO:b64] {exc}")
        return False


def poll_json(
    status_url: str,
    *,
    headers: dict,
    done_key: str = "status",
    done_values: Tuple[str, ...] = ("COMPLETED", "succeeded", "SUCCESS", "completed"),
    fail_values: Tuple[str, ...] = ("FAILED", "failed", "ERROR", "canceled"),
    timeout: float = 180.0,
    interval: float = 3.0,
) -> Optional[Dict[str, Any]]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(status_url, headers=headers, timeout=30)
            if r.status_code != 200:
                time.sleep(interval)
                continue
            data = r.json()
            st = str(data.get(done_key) or data.get("state") or "").upper()
            if any(v.upper() == st for v in done_values) or data.get("output") or data.get("video"):
                if any(v.upper() == st for v in fail_values):
                    return None
                return data
            if any(v.upper() == st for v in fail_values):
                return None
        except Exception:
            pass
        time.sleep(interval)
    return None


def ai_generated_license(provider: str, model: str = "", commercial_ok: bool = True) -> dict:
    return {
        "license": "ai_generated",
        "source": provider,
        "safe": bool(commercial_ok),
        "needs_attribution": True,
        "author": provider,
        "title": f"AI video ({model or provider})",
        "raw": f"{provider}:{model}",
        "license_url": "",
        "source_url": "",
    }
