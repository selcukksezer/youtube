"""DeepInfra Wan text-to-video adapter."""
from __future__ import annotations

from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import (
    ai_generated_license,
    decode_data_uri,
    download_url,
    env_key,
    log_skip_once,
)

_DEFAULT_MODEL = "Wan-AI/Wan2.2-T2V-A14B"


class DeepInfraVideoProvider(AIVideoProvider):
    name = "deepinfra"
    priority = 30

    def is_available(self) -> bool:
        return bool(env_key("DEEPINFRA_TOKEN", "DEEPINFRA_API_KEY"))

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        token = env_key("DEEPINFRA_TOKEN", "DEEPINFRA_API_KEY")
        if not token:
            log_skip_once(self.name, "DEEPINFRA_TOKEN missing")
            return None
        model = env_key("DEEPINFRA_VIDEO_MODEL") or _DEFAULT_MODEL
        url = f"https://api.deepinfra.com/v1/inference/{model}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {"prompt": prompt}
        if seed is not None:
            payload["seed"] = int(seed)
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=300)
            if r.status_code in (401, 403):
                log_skip_once(self.name, f"auth HTTP {r.status_code}")
                return None
            if r.status_code != 200:
                print(f"    [AI-VIDEO:deepinfra] HTTP {r.status_code}: {r.text[:200]}")
                return None
            data = r.json()
            video = data.get("video_url") or data.get("video") or ""
            ok = False
            if isinstance(video, str) and video.startswith("data:"):
                ok = decode_data_uri(video, output_path)
            elif isinstance(video, str) and video.startswith("http"):
                ok = download_url(video, output_path)
            if not ok:
                return None
            return AIVideoResult(
                path=output_path,
                provider=self.name,
                model=model,
                prompt=prompt,
                seed=seed,
                duration=duration,
                aspect=aspect,
                license=ai_generated_license(self.name, model),
                raw={"request_id": data.get("request_id")},
            )
        except Exception as exc:
            print(f"    [AI-VIDEO:deepinfra] {exc}")
            return None
