"""MiniMax Hailuo paid text-to-video (free app tier is non-commercial — key only)."""
from __future__ import annotations

import time
from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, download_url, env_key, log_skip_once

# Official API hosts have shifted; override with MINIMAX_VIDEO_ENDPOINT if needed.
_CREATE = "https://api.minimaxi.chat/v1/video_generation"
_QUERY = "https://api.minimaxi.chat/v1/query/video_generation"
_FILE = "https://api.minimaxi.chat/v1/files/retrieve"


class MiniMaxVideoProvider(AIVideoProvider):
    name = "minimax"
    priority = 22

    def is_available(self) -> bool:
        return bool(env_key("MINIMAX_API_KEY", "MINIMAX_GROUP_API_KEY", "HAILUO_API_KEY"))

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        key = env_key("MINIMAX_API_KEY", "MINIMAX_GROUP_API_KEY", "HAILUO_API_KEY")
        if not key:
            log_skip_once(self.name, "MINIMAX_API_KEY missing")
            return None
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        group = env_key("MINIMAX_GROUP_ID", "MINIMAX_GROUPID")
        if group:
            headers["GroupId"] = group
        model = env_key("MINIMAX_VIDEO_MODEL") or "T2V-01"
        create_url = env_key("MINIMAX_VIDEO_ENDPOINT") or _CREATE
        payload = {
            "model": model,
            "prompt": prompt,
        }
        # Some tenants accept duration / aspect_ratio
        if duration:
            payload["duration"] = int(max(5, min(10, round(duration))))
        try:
            r = requests.post(create_url, headers=headers, json=payload, timeout=60)
            if r.status_code in (401, 403):
                log_skip_once(self.name, f"auth HTTP {r.status_code}")
                return None
            if r.status_code not in (200, 201, 202):
                print(f"    [AI-VIDEO:minimax] HTTP {r.status_code}: {r.text[:180]}")
                return None
            data = r.json() or {}
            task_id = (
                data.get("task_id")
                or data.get("data", {}).get("task_id")
                or (data.get("base_resp") and data.get("task_id"))
            )
            if not task_id and data.get("file_id"):
                # rare sync
                pass
            video_url = _find_url(data)
            if not video_url and task_id:
                video_url = _poll(task_id, headers)
            if not video_url or not download_url(video_url, output_path):
                return None
            return AIVideoResult(
                path=output_path,
                provider=self.name,
                model=model,
                prompt=prompt,
                seed=seed,
                duration=float(duration or 5),
                aspect=aspect,
                license=ai_generated_license(self.name, model),
            )
        except Exception as exc:
            print(f"    [AI-VIDEO:minimax] {exc}")
            return None


def _find_url(data: dict) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    for key in ("download_url", "video_url", "file_url", "url"):
        v = data.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v
    file_id = data.get("file_id")
    if file_id and isinstance(data.get("download_url"), str):
        return data["download_url"]
    nested = data.get("data") or data.get("file") or {}
    if isinstance(nested, dict):
        return _find_url(nested)
    return None


def _poll(task_id: str, headers: dict, timeout: float = 300.0) -> Optional[str]:
    query = env_key("MINIMAX_VIDEO_QUERY") or _QUERY
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(query, headers=headers, params={"task_id": task_id}, timeout=30)
            if r.status_code == 200:
                data = r.json() or {}
                st = str(data.get("status") or data.get("task_status") or "").upper()
                if st in ("SUCCESS", "SUCCESSFUL", "DONE", "COMPLETED", "FINISHED"):
                    url = _find_url(data)
                    if url:
                        return url
                    # file retrieve path
                    file_id = data.get("file_id")
                    if file_id:
                        fr = requests.get(
                            env_key("MINIMAX_FILE_ENDPOINT") or _FILE,
                            headers=headers,
                            params={"file_id": file_id},
                            timeout=30,
                        )
                        if fr.status_code == 200:
                            return _find_url(fr.json() or {})
                if st in ("FAILED", "FAIL", "ERROR"):
                    return None
        except Exception:
            pass
        time.sleep(4.0)
    return None
