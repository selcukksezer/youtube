"""Luma Dream Machine / Ray paid API adapter."""
from __future__ import annotations

import time
from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, download_url, env_key, log_skip_once

_BASE = "https://api.lumalabs.ai/dream-machine/v1"


class LumaVideoProvider(AIVideoProvider):
    name = "luma"
    priority = 18

    def is_available(self) -> bool:
        return bool(env_key("LUMA_API_KEY", "LUMAAI_API_KEY", "LUMA_KEY"))

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        key = env_key("LUMA_API_KEY", "LUMAAI_API_KEY", "LUMA_KEY")
        if not key:
            log_skip_once(self.name, "LUMA_API_KEY missing")
            return None
        headers = {
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        # Ray API: duration string "5s" / "9s" class
        dur_s = "9s" if duration >= 7 else "5s"
        model = env_key("LUMA_VIDEO_MODEL") or "ray-2"
        ar = "9:16" if "9" in str(aspect) else "16:9"
        payload = {
            "prompt": prompt,
            "model": model,
            "resolution": "720p",
            "duration": dur_s,
            "aspect_ratio": ar,
        }
        try:
            r = requests.post(f"{_BASE}/generations", headers=headers, json=payload, timeout=60)
            if r.status_code in (401, 403):
                log_skip_once(self.name, f"auth HTTP {r.status_code}")
                return None
            if r.status_code not in (200, 201, 202):
                print(f"    [AI-VIDEO:luma] HTTP {r.status_code}: {r.text[:180]}")
                return None
            data = r.json() or {}
            gen_id = data.get("id")
            video_url = _extract_url(data)
            if not video_url and gen_id:
                video_url = _poll(gen_id, headers)
            if not video_url or not download_url(video_url, output_path):
                return None
            return AIVideoResult(
                path=output_path,
                provider=self.name,
                model=model,
                prompt=prompt,
                seed=seed,
                duration=float(duration or 5),
                aspect=ar,
                license=ai_generated_license(self.name, model),
            )
        except Exception as exc:
            print(f"    [AI-VIDEO:luma] {exc}")
            return None


def _extract_url(data: dict) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    assets = data.get("assets") or {}
    if isinstance(assets, dict) and assets.get("video"):
        return assets["video"]
    for key in ("video", "video_url", "url"):
        v = data.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v
        if isinstance(v, dict) and v.get("url"):
            return v["url"]
    return None


def _poll(gen_id: str, headers: dict, timeout: float = 300.0) -> Optional[str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{_BASE}/generations/{gen_id}", headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json() or {}
                st = str(data.get("state") or data.get("status") or "").lower()
                if st in ("completed", "succeeded", "success"):
                    return _extract_url(data)
                if st in ("failed", "error", "canceled", "cancelled"):
                    return None
        except Exception:
            pass
        time.sleep(4.0)
    return None
