"""PiAPI Kling (and related) text-to-video adapter."""
from __future__ import annotations

import time
from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, download_url, env_key, log_skip_once

# PiAPI task create endpoint (Kling T2V) — path may evolve; override via PIAPI_VIDEO_ENDPOINT
_CREATE = "https://api.piapi.ai/api/v1/task"
_MODEL = "kling"


class PiAPIVideoProvider(AIVideoProvider):
    name = "piapi"
    priority = 40

    def is_available(self) -> bool:
        return bool(env_key("PIAPI_KEY", "PIAPI_API_KEY"))

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        key = env_key("PIAPI_KEY", "PIAPI_API_KEY")
        if not key:
            log_skip_once(self.name, "PIAPI_KEY missing")
            return None
        headers = {
            "x-api-key": key,
            "Content-Type": "application/json",
        }
        ar = "9:16" if "9" in str(aspect) else "16:9"
        dur = 5 if duration < 7.5 else 10
        payload = {
            "model": env_key("PIAPI_VIDEO_MODEL") or "kling",
            "task_type": "video_generation",
            "input": {
                "prompt": prompt,
                "negative_prompt": "watermark, text, logo, blurry, low quality",
                "duration": dur,
                "aspect_ratio": ar,
                "mode": "std",
                "version": "2.1",
            },
        }
        create_url = env_key("PIAPI_VIDEO_ENDPOINT") or _CREATE
        try:
            r = requests.post(create_url, headers=headers, json=payload, timeout=60)
            if r.status_code in (401, 403):
                log_skip_once(self.name, f"auth HTTP {r.status_code}")
                return None
            if r.status_code not in (200, 201, 202):
                # Alternate payload shape used by some PiAPI Kling routes
                alt = {
                    "model": "kling",
                    "input": {"prompt": prompt, "duration": dur, "aspect_ratio": ar},
                }
                r = requests.post(create_url, headers=headers, json=alt, timeout=60)
                if r.status_code not in (200, 201, 202):
                    print(f"    [AI-VIDEO:piapi] HTTP {r.status_code}: {r.text[:200]}")
                    return None
            data = r.json()
            task_id = (
                data.get("data", {}).get("task_id")
                or data.get("task_id")
                or data.get("data", {}).get("id")
                or data.get("id")
            )
            video_url = _find_url(data)
            if not video_url and task_id:
                video_url = _poll_task(task_id, headers)
            if not video_url:
                return None
            if not download_url(video_url, output_path):
                return None
            return AIVideoResult(
                path=output_path,
                provider=self.name,
                model=payload.get("model", _MODEL),
                prompt=prompt,
                seed=seed,
                duration=float(dur),
                aspect=ar,
                license=ai_generated_license(self.name, str(payload.get("model"))),
            )
        except Exception as exc:
            print(f"    [AI-VIDEO:piapi] {exc}")
            return None


def _find_url(data: dict) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    for key in ("video_url", "url", "video"):
        v = data.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v
        if isinstance(v, dict) and str(v.get("url", "")).startswith("http"):
            return v["url"]
    out = data.get("output") or data.get("data") or {}
    if isinstance(out, dict):
        return _find_url(out)
    if isinstance(out, list):
        for item in out:
            u = _find_url(item) if isinstance(item, dict) else None
            if u:
                return u
    return None


def _poll_task(task_id: str, headers: dict, timeout: float = 240.0) -> Optional[str]:
    url = f"https://api.piapi.ai/api/v1/task/{task_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                st = str(
                    data.get("data", {}).get("status")
                    or data.get("status")
                    or ""
                ).lower()
                if st in ("completed", "success", "succeeded", "done"):
                    return _find_url(data)
                if st in ("failed", "error", "cancelled"):
                    return None
        except Exception:
            pass
        time.sleep(4)
    return None
