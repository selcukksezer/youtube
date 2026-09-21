"""Replicate text-to-video adapter (Wan-class models)."""
from __future__ import annotations

import time
from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, download_url, env_key, log_skip_once

# Public model versions that support T2V; override via REPLICATE_VIDEO_MODEL
_DEFAULT_MODEL = "wan-video/wan-2.1-t2v-480p"


class ReplicateVideoProvider(AIVideoProvider):
    name = "replicate"
    priority = 20

    def is_available(self) -> bool:
        return bool(env_key("REPLICATE_API_TOKEN", "REPLICATE_API_KEY"))

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        token = env_key("REPLICATE_API_TOKEN", "REPLICATE_API_KEY")
        if not token:
            log_skip_once(self.name, "REPLICATE_API_TOKEN missing")
            return None
        model = env_key("REPLICATE_VIDEO_MODEL") or _DEFAULT_MODEL
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }
        ar = "9:16" if "9" in str(aspect) else "16:9"
        payload = {
            "input": {
                "prompt": prompt,
                "aspect_ratio": ar,
                **({"seed": int(seed)} if seed is not None else {}),
            }
        }
        # Prefer model name endpoint when no version hash
        if ":" in model or len(model) > 60:
            url = "https://api.replicate.com/v1/predictions"
            payload["version"] = model.split(":")[-1] if ":" in model else model
        else:
            url = f"https://api.replicate.com/v1/models/{model}/predictions"

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code in (401, 403):
                log_skip_once(self.name, f"auth HTTP {r.status_code}")
                return None
            if r.status_code not in (200, 201, 202):
                print(f"    [AI-VIDEO:replicate] HTTP {r.status_code}: {r.text[:200]}")
                return None
            data = r.json()
            out = _output_url(data)
            if not out:
                get_url = data.get("urls", {}).get("get") or f"https://api.replicate.com/v1/predictions/{data.get('id')}"
                out = _poll(get_url, {"Authorization": f"Bearer {token}"})
            if not out:
                return None
            if not download_url(out, output_path):
                return None
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
            print(f"    [AI-VIDEO:replicate] {exc}")
            return None


def _output_url(data: dict) -> Optional[str]:
    out = data.get("output")
    if isinstance(out, str) and out.startswith("http"):
        return out
    if isinstance(out, list) and out:
        last = out[-1]
        if isinstance(last, str) and last.startswith("http"):
            return last
    return None


def _poll(url: str, headers: dict, timeout: float = 240.0) -> Optional[str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code != 200:
                time.sleep(3)
                continue
            data = r.json()
            st = str(data.get("status") or "")
            if st == "succeeded":
                return _output_url(data)
            if st in ("failed", "canceled"):
                return None
        except Exception:
            pass
        time.sleep(3)
    return None
