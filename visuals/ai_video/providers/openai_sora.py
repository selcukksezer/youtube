"""OpenAI Sora Videos API (v1/videos) — paid; scheduled shutdown 2026-09-24."""
from __future__ import annotations

import time
from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, env_key, log_skip_once, write_bytes

_BASE = "https://api.openai.com/v1"


class OpenAISoraProvider(AIVideoProvider):
    name = "openai_sora"
    priority = 25

    def is_available(self) -> bool:
        if not env_key("OPENAI_API_KEY"):
            return False
        # Allow explicit disable (EOL / cost)
        flag = (env_key("USE_OPENAI_SORA") or "true").lower()
        return flag not in ("0", "false", "no", "off")

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        key = env_key("OPENAI_API_KEY")
        if not key:
            log_skip_once(self.name, "OPENAI_API_KEY missing")
            return None
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        # Allowed seconds: 4 / 8 / 12
        if duration >= 10:
            seconds = "12"
        elif duration >= 6:
            seconds = "8"
        else:
            seconds = "4"
        size = "720x1280" if "9" in str(aspect) else "1280x720"
        model = env_key("OPENAI_SORA_MODEL") or "sora-2"
        payload = {
            "model": model,
            "prompt": prompt,
            "seconds": seconds,
            "size": size,
        }
        try:
            r = requests.post(f"{_BASE}/videos", headers=headers, json=payload, timeout=60)
            if r.status_code in (401, 403):
                log_skip_once(self.name, f"auth HTTP {r.status_code}")
                return None
            if r.status_code == 404:
                log_skip_once(self.name, "videos API unavailable/deprecated")
                return None
            if r.status_code not in (200, 201, 202):
                print(f"    [AI-VIDEO:openai_sora] HTTP {r.status_code}: {r.text[:180]}")
                return None
            data = r.json() or {}
            vid = data.get("id")
            if not vid:
                return None
            if not _wait_complete(vid, headers):
                return None
            content = requests.get(
                f"{_BASE}/videos/{vid}/content",
                headers={"Authorization": f"Bearer {key}"},
                timeout=120,
            )
            if content.status_code != 200 or len(content.content) < 10_000:
                print(f"    [AI-VIDEO:openai_sora] content HTTP {content.status_code}")
                return None
            if not write_bytes(content.content, output_path):
                return None
            return AIVideoResult(
                path=output_path,
                provider=self.name,
                model=model,
                prompt=prompt,
                seed=seed,
                duration=float(seconds),
                aspect=aspect,
                license=ai_generated_license(self.name, model),
            )
        except Exception as exc:
            print(f"    [AI-VIDEO:openai_sora] {exc}")
            return None


def _wait_complete(video_id: str, headers: dict, timeout: float = 360.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{_BASE}/videos/{video_id}", headers=headers, timeout=30)
            if r.status_code != 200:
                time.sleep(3.0)
                continue
            st = str((r.json() or {}).get("status") or "").lower()
            if st == "completed":
                return True
            if st == "failed":
                return False
        except Exception:
            pass
        time.sleep(3.0)
    return False
