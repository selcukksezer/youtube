"""Runway Gen-4.5 text-to-video (paid API — commercial OK)."""
from __future__ import annotations

import time
from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, download_url, env_key, log_skip_once

_BASE = "https://api.dev.runwayml.com/v1"
_VERSION = "2024-11-06"


class RunwayVideoProvider(AIVideoProvider):
    name = "runway"
    priority = 15

    def is_available(self) -> bool:
        return bool(env_key("RUNWAYML_API_SECRET", "RUNWAY_API_KEY", "RUNWAY_API_SECRET"))

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        key = env_key("RUNWAYML_API_SECRET", "RUNWAY_API_KEY", "RUNWAY_API_SECRET")
        if not key:
            log_skip_once(self.name, "RUNWAYML_API_SECRET missing")
            return None
        headers = {
            "Authorization": f"Bearer {key}",
            "X-Runway-Version": _VERSION,
            "Content-Type": "application/json",
        }
        ratio = "720:1280" if "9" in str(aspect) else "1280:720"
        dur = int(max(2, min(10, round(duration or 5))))
        model = env_key("RUNWAY_VIDEO_MODEL") or "gen4.5"
        payload = {
            "model": model,
            "promptText": (prompt or "")[:1000],
            "ratio": ratio,
            "duration": dur,
        }
        if seed is not None:
            payload["seed"] = int(seed) % (2**31)
        try:
            r = requests.post(f"{_BASE}/text_to_video", headers=headers, json=payload, timeout=60)
            if r.status_code in (401, 403):
                log_skip_once(self.name, f"auth HTTP {r.status_code}")
                return None
            if r.status_code not in (200, 201, 202):
                print(f"    [AI-VIDEO:runway] HTTP {r.status_code}: {r.text[:180]}")
                return None
            task_id = (r.json() or {}).get("id")
            if not task_id:
                return None
            video_url = _poll_task(task_id, headers)
            if not video_url or not download_url(video_url, output_path):
                return None
            return AIVideoResult(
                path=output_path,
                provider=self.name,
                model=model,
                prompt=prompt,
                seed=seed,
                duration=float(dur),
                aspect=aspect,
                license=ai_generated_license(self.name, model),
            )
        except Exception as exc:
            print(f"    [AI-VIDEO:runway] {exc}")
            return None


def _poll_task(task_id: str, headers: dict, timeout: float = 300.0) -> Optional[str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            st = requests.get(f"{_BASE}/tasks/{task_id}", headers=headers, timeout=30)
            if st.status_code != 200:
                time.sleep(4.0)
                continue
            data = st.json() or {}
            status = str(data.get("status") or "").upper().replace(" ", "_")
            if status in ("SUCCEEDED", "SUCCESS", "COMPLETED"):
                out = data.get("output")
                if isinstance(out, list) and out:
                    return out[0] if isinstance(out[0], str) else (out[0] or {}).get("url")
                if isinstance(out, str):
                    return out
                return None
            if status in ("FAILED", "ERROR", "CANCELLED", "CANCELED"):
                return None
        except Exception:
            pass
        time.sleep(4.0)
    return None
