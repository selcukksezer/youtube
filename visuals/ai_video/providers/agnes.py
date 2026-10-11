"""Agnes Video 2.5 text-to-video adapter."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, download_url, env_key, log_skip_once

_DEFAULT_BASE_URL = "https://apihub.agnes-ai.com/v1"
_ASPECT_RATIOS = ("21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
_POLL_TIMEOUT_SECONDS = 240.0
_POLL_INTERVAL_SECONDS = 3.0


def _aspect_ratio(aspect: str) -> str:
    normalized = str(aspect or "").strip().lower().replace("/", ":")
    aliases = {
        "portrait": "9:16",
        "landscape": "16:9",
        "square": "1:1",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in _ASPECT_RATIOS:
        return normalized
    try:
        width, height = (float(value) for value in normalized.split(":", 1))
        if width <= 0 or height <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return "9:16"

    ratio = width / height
    return min(
        _ASPECT_RATIOS,
        key=lambda value: abs(ratio - _ratio_value(value)),
    )


def _ratio_value(aspect: str) -> float:
    width, height = aspect.split(":")
    return int(width) / int(height)


def _base_urls() -> tuple[str, str]:
    configured = (env_key("AGNES_BASE_URL", "AGNES_API_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")
    if configured.endswith("/v1"):
        return configured, configured[:-3]
    return f"{configured}/v1", configured


def _api_keys() -> list[str]:
    keys = []
    for index in range(1, 100):
        name = "AGNES_API_KEY" if index == 1 else f"AGNES_API_KEY_{index}"
        key = env_key(name)
        if not key:
            break
        if key not in keys:
            keys.append(key)
    return keys


def _auth_headers(key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _video_url(data: Dict[str, Any]) -> Optional[str]:
    for key in ("url", "video_url", "output"):
        value = data.get(key)
        if isinstance(value, str) and value.startswith(("https://", "http://")):
            return value
        if isinstance(value, dict):
            nested_url = value.get("url") or value.get("video_url")
            if isinstance(nested_url, str) and nested_url.startswith(("https://", "http://")):
                return nested_url
    for key in ("data", "result", "video"):
        nested = data.get(key)
        if isinstance(nested, dict):
            found = _video_url(nested)
            if found:
                return found
    return None


def _poll_video(
    status_url: str,
    keys: list[str],
    start_key_index: int = 0,
) -> Optional[Dict[str, Any]]:
    deadline = time.monotonic() + _POLL_TIMEOUT_SECONDS
    last_status = ""
    key_index = start_key_index
    while time.monotonic() < deadline:
        try:
            response = None
            for offset in range(len(keys)):
                candidate_index = (key_index + offset) % len(keys)
                response = requests.get(
                    status_url,
                    headers=_auth_headers(keys[candidate_index]),
                    timeout=30,
                )
                if response.status_code != 429:
                    key_index = candidate_index
                    break
            if response is None:
                print("    [AI-VIDEO:agnes] no API key available for polling")
                return None
            if response.status_code == 429:
                key_index = (key_index + 1) % len(keys)
                time.sleep(_POLL_INTERVAL_SECONDS)
                continue
            if response.status_code in (401, 403):
                log_skip_once("agnes", f"poll auth HTTP {response.status_code}")
                return None
            if response.status_code in (400, 404):
                print(f"    [AI-VIDEO:agnes] poll HTTP {response.status_code}: {response.text[:180]}")
                return None
            if response.status_code == 200:
                data = response.json()
                if not isinstance(data, dict):
                    print("    [AI-VIDEO:agnes] poll response was not a JSON object")
                    return None
                status = str(data.get("status") or "").strip().lower()
                if status and status != last_status:
                    print(f"    [AI-VIDEO:agnes] status={status}")
                    last_status = status
                if status in ("completed", "complete", "succeeded", "success"):
                    return data
                if status in ("failed", "error", "cancelled", "canceled"):
                    print(f"    [AI-VIDEO:agnes] generation failed: {data.get('error', status)}")
                    return None
        except (requests.RequestException, ValueError) as exc:
            print(f"    [AI-VIDEO:agnes] poll error: {exc}")
        time.sleep(_POLL_INTERVAL_SECONDS)
    print("    [AI-VIDEO:agnes] polling timed out")
    return None


class AgnesVideoProvider(AIVideoProvider):
    name = "agnes"
    priority = 35

    def is_available(self) -> bool:
        return bool(_api_keys())

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        keys = _api_keys()
        if not keys:
            log_skip_once(self.name, "AGNES_API_KEY missing")
            return None

        base_v1, api_root = _base_urls()
        model = env_key("AGNES_VIDEO_MODEL") or "agnes-video-2.5-flash"
        seconds = str(max(4, min(12, int(round(duration or 5.0)))))
        video_aspect = _aspect_ratio(aspect)
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "mode": "text",
            "seconds": seconds,
            "size": "720P",
            "aspect_ratio": video_aspect,
        }
        if seed is not None:
            payload["seed"] = int(seed)

        try:
            response = None
            active_key_index = 0
            for key_index, key in enumerate(keys):
                response = requests.post(
                    f"{base_v1}/videos",
                    headers=_auth_headers(key),
                    json=payload,
                    timeout=(15, 60),
                )
                active_key_index = key_index
                if response.status_code != 429:
                    break
            if response is None:
                return None
            if response.status_code == 429:
                log_skip_once(self.name, "all configured API keys rate limited")
                return None
            if response.status_code in (401, 403):
                log_skip_once(self.name, f"submit auth HTTP {response.status_code}")
                return None
            if response.status_code == 402:
                log_skip_once(self.name, "account credits unavailable")
                return None
            if response.status_code not in (200, 201, 202):
                print(f"    [AI-VIDEO:agnes] submit HTTP {response.status_code}: {response.text[:180]}")
                return None

            task = response.json()
            if not isinstance(task, dict):
                print("    [AI-VIDEO:agnes] submit response was not a JSON object")
                return None
            task_id = task.get("video_id") or task.get("task_id") or task.get("id")
            if not isinstance(task_id, str) or not task_id:
                print("    [AI-VIDEO:agnes] submit response did not include a task id")
                return None

            poll_query = urlencode({"video_id": task_id, "model_name": model})
            status = _poll_video(
                f"{api_root}/agnesapi?{poll_query}",
                keys,
                start_key_index=active_key_index,
            )
            video_url = _video_url(status) if status else None
            if not video_url:
                return None
            if not download_url(video_url, output_path):
                return None

            return AIVideoResult(
                path=output_path,
                provider=self.name,
                model=model,
                prompt=prompt,
                seed=seed,
                duration=float(seconds),
                aspect=video_aspect,
                license=ai_generated_license(self.name, model),
            )
        except (requests.RequestException, ValueError, TypeError) as exc:
            print(f"    [AI-VIDEO:agnes] {exc}")
            return None
