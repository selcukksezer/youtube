"""Optional local ComfyUI / self-host Wan endpoint."""
from __future__ import annotations

from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, download_url, env_key, log_skip_once


class LocalVideoProvider(AIVideoProvider):
    name = "local"
    priority = 5  # prefer when available = truly unlimited

    def is_available(self) -> bool:
        return bool(env_key("LOCAL_AI_VIDEO_URL"))

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        base = env_key("LOCAL_AI_VIDEO_URL").rstrip("/")
        if not base:
            log_skip_once(self.name, "LOCAL_AI_VIDEO_URL missing")
            return None
        payload = {
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect,
            "seed": seed,
        }
        try:
            r = requests.post(f"{base}/generate", json=payload, timeout=600)
            if r.status_code != 200:
                print(f"    [AI-VIDEO:local] HTTP {r.status_code}")
                return None
            data = r.json() if "json" in (r.headers.get("content-type") or "") else {}
            url = data.get("url") or data.get("video_url")
            path = data.get("path")
            if path and path != output_path:
                import shutil, os
                if os.path.isfile(path):
                    shutil.copy2(path, output_path)
                    path = output_path
            elif url:
                if not download_url(url, output_path):
                    return None
                path = output_path
            else:
                # raw mp4 body
                if r.content[:4] in (b"\x00\x00\x00\x18", b"\x00\x00\x00\x1c", b"ftyp") or len(r.content) > 10_000:
                    from ..http_util import write_bytes
                    if write_bytes(r.content, output_path):
                        path = output_path
            if not path:
                return None
            return AIVideoResult(
                path=path,
                provider=self.name,
                model="local-wan",
                prompt=prompt,
                seed=seed,
                duration=duration,
                aspect=aspect,
                license=ai_generated_license(self.name, "local-wan"),
            )
        except Exception as exc:
            print(f"    [AI-VIDEO:local] {exc}")
            return None
