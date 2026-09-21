"""Fal.ai Wan / Hunyuan text-to-video adapter."""
from __future__ import annotations

import time
from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, download_url, env_key, log_skip_once

# Prefer lighter Wan first (cheaper free credits), then Hunyuan
_MODELS = (
    "fal-ai/wan-t2v",
    "fal-ai/hunyuan-video",
)


class FalVideoProvider(AIVideoProvider):
    name = "fal"
    priority = 10

    def is_available(self) -> bool:
        return bool(env_key("FAL_API_KEY", "FAL_KEY"))

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        key = env_key("FAL_API_KEY", "FAL_KEY")
        if not key:
            log_skip_once(self.name, "FAL_API_KEY missing")
            return None
        headers = {
            "Authorization": f"Key {key}",
            "Content-Type": "application/json",
        }
        ar = "9:16" if aspect in ("9:16", "9/16", "portrait") else "16:9"
        # ~5s at 16fps ≈ 81 frames (Wan minimum)
        payload = {
            "prompt": prompt,
            "aspect_ratio": ar,
            "resolution": "720p",
            "num_frames": 81,
            "frames_per_second": 16,
            "turbo_mode": True,
        }
        if seed is not None:
            payload["seed"] = int(seed)

        for model in _MODELS:
            try:
                # Queue API
                submit = requests.post(
                    f"https://queue.fal.run/{model}",
                    headers=headers,
                    json=payload if model.endswith("wan-t2v") else {
                        "prompt": prompt,
                        "aspect_ratio": ar,
                        "resolution": "720p",
                        **({"seed": int(seed)} if seed is not None else {}),
                    },
                    timeout=60,
                )
                if submit.status_code in (401, 403):
                    log_skip_once(self.name, f"auth fail HTTP {submit.status_code}")
                    return None
                if submit.status_code == 402:
                    log_skip_once(self.name, "credits exhausted")
                    return None
                if submit.status_code not in (200, 201, 202):
                    print(f"    [AI-VIDEO:fal] submit {model} HTTP {submit.status_code}")
                    continue
                body = submit.json()
                req_id = body.get("request_id") or body.get("requestId")
                status_url = body.get("status_url") or (
                    f"https://queue.fal.run/{model}/requests/{req_id}/status" if req_id else None
                )
                result_url = body.get("response_url") or (
                    f"https://queue.fal.run/{model}/requests/{req_id}" if req_id else None
                )
                # Immediate result?
                video_url = _extract_video_url(body)
                if not video_url and status_url and result_url:
                    video_url = _poll_fal(status_url, result_url, headers)
                if not video_url:
                    continue
                if not download_url(video_url, output_path):
                    continue
                return AIVideoResult(
                    path=output_path,
                    provider=self.name,
                    model=model,
                    prompt=prompt,
                    seed=seed,
                    duration=duration,
                    aspect=ar,
                    license=ai_generated_license(self.name, model),
                )
            except Exception as exc:
                print(f"    [AI-VIDEO:fal] {model}: {exc}")
                continue
        return None


def _extract_video_url(data: dict) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    v = data.get("video")
    if isinstance(v, dict) and v.get("url"):
        return v["url"]
    if isinstance(v, str) and v.startswith("http"):
        return v
    for key in ("video_url", "url", "output"):
        val = data.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
        if isinstance(val, dict) and val.get("url"):
            return val["url"]
    # nested response
    resp = data.get("response") or data.get("data") or {}
    if isinstance(resp, dict):
        return _extract_video_url(resp)
    return None


def _poll_fal(status_url: str, result_url: str, headers: dict, timeout: float = 200.0) -> Optional[str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            st = requests.get(status_url, headers=headers, timeout=30)
            if st.status_code == 200:
                sj = st.json()
                status = str(sj.get("status") or "").upper()
                if status in ("COMPLETED", "OK"):
                    res = requests.get(result_url, headers=headers, timeout=60)
                    if res.status_code == 200:
                        return _extract_video_url(res.json())
                if status in ("FAILED", "ERROR", "CANCELLED"):
                    return None
        except Exception:
            pass
        time.sleep(3.0)
    return None
