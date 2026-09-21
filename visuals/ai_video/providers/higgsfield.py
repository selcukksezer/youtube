"""Higgsfield Cloud text-to-video adapter (async REST).

Docs: https://docs.higgsfield.ai
Auth: Authorization: Key {KEY_ID}:{KEY_SECRET}
Base: https://api.higgsfield.ai

Credentials (any one form):
  HIGGSFIELD_CREDENTIALS=key_id:key_secret
  HIGGSFIELD_API_KEY_ID + HIGGSFIELD_API_KEY_SECRET
  HF_API_KEY_ID + HF_API_KEY_SECRET   (official doc names)

Do NOT reuse HF_TOKEN — that is HuggingFace.
"""
from __future__ import annotations

import os
import time
from typing import Optional, Tuple

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import USER_AGENT, ai_generated_license, download_url, env_key, log_skip_once

_BASE_DEFAULT = "https://api.higgsfield.ai"

# First = preferred. Override with HIGGSFIELD_T2V_MODEL=owner/model/path
_DEFAULT_MODELS = (
    "bytedance/seedance-2.5/text-to-video",
    "bytedance/seedance-v1/text-to-video",
    "minimax/hailuo-02/text-to-video",
    "kwaivgi/kling-v2.1-master/text-to-video",
)


def resolve_higgsfield_credentials() -> Tuple[str, str]:
    """Return (key_id, key_secret) or ("", "")."""
    combined = env_key(
        "HIGGSFIELD_CREDENTIALS",
        "HIGGSFIELD_API_CREDENTIALS",
        "HF_CREDENTIALS",
    )
    if combined and ":" in combined:
        kid, _, secret = combined.partition(":")
        kid, secret = kid.strip(), secret.strip()
        if kid and secret:
            return kid, secret

    kid = env_key(
        "HIGGSFIELD_API_KEY_ID",
        "HIGGSFIELD_KEY_ID",
        "HF_API_KEY_ID",
    )
    secret = env_key(
        "HIGGSFIELD_API_KEY_SECRET",
        "HIGGSFIELD_KEY_SECRET",
        "HF_API_KEY_SECRET",
    )
    if kid and secret:
        return kid, secret
    return "", ""


def _auth_header(key_id: str, key_secret: str) -> dict:
    return {
        "Authorization": f"Key {key_id}:{key_secret}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }


def _base_url() -> str:
    return (os.getenv("HIGGSFIELD_BASE_URL") or _BASE_DEFAULT).rstrip("/")


def _model_list() -> tuple:
    primary = (os.getenv("HIGGSFIELD_T2V_MODEL") or "").strip().strip("/")
    if primary:
        rest = [m for m in _DEFAULT_MODELS if m != primary]
        return (primary, *rest)
    return _DEFAULT_MODELS


def _clamp_duration(seconds: float) -> int:
    # Seedance family: 4–30s; other models typically accept similar ints
    return max(4, min(30, int(round(float(seconds) or 5.0))))


def _aspect_ratio(aspect: str) -> str:
    a = (aspect or "9:16").replace("/", ":").strip().lower()
    allowed = {"16:9", "4:3", "1:1", "3:4", "9:16", "21:9"}
    if a in ("portrait", "vertical", "9x16"):
        return "9:16"
    if a in ("landscape", "horizontal", "16x9"):
        return "16:9"
    return a if a in allowed else "9:16"


def _extract_video_url(data: dict) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    video = data.get("video")
    if isinstance(video, dict) and video.get("url"):
        return str(video["url"])
    if isinstance(video, str) and video.startswith("http"):
        return video
    for key in ("video_url", "url", "output"):
        val = data.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
        if isinstance(val, dict) and val.get("url"):
            return str(val["url"])
    # Some models wrap under result / data / output
    for nest in ("result", "data", "output", "response"):
        inner = data.get(nest)
        if isinstance(inner, dict):
            found = _extract_video_url(inner)
            if found:
                return found
    return None


def _poll_status(
    status_url: str,
    headers: dict,
    *,
    timeout: float = 300.0,
    interval: float = 3.0,
) -> Optional[dict]:
    deadline = time.time() + timeout
    terminal_fail = {"failed", "nsfw", "canceled", "cancelled", "error"}
    while time.time() < deadline:
        try:
            r = requests.get(status_url, headers=headers, timeout=45)
            if r.status_code == 401:
                log_skip_once("higgsfield", "auth fail HTTP 401")
                return None
            if r.status_code == 404:
                return None
            if r.status_code != 200:
                time.sleep(interval)
                continue
            body = r.json()
            status = str(body.get("status") or "").lower()
            if status == "completed":
                return body
            if status in terminal_fail:
                err = body.get("error") or status
                print(f"    [AI-VIDEO:higgsfield] terminal={status} err={err}")
                return None
        except Exception as exc:
            print(f"    [AI-VIDEO:higgsfield] poll: {exc}")
        time.sleep(interval)
    print("    [AI-VIDEO:higgsfield] poll timeout")
    return None


class HiggsfieldVideoProvider(AIVideoProvider):
    """Pay-as-you-go Higgsfield Cloud — Seedance / Kling / Hailuo via one key."""

    name = "higgsfield"
    # Prefer when credentials present (high-quality catalog)
    priority = 8

    def is_available(self) -> bool:
        kid, secret = resolve_higgsfield_credentials()
        return bool(kid and secret)

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        kid, secret = resolve_higgsfield_credentials()
        if not kid or not secret:
            log_skip_once(self.name, "HIGGSFIELD credentials missing (KEY_ID:SECRET)")
            return None

        headers = _auth_header(kid, secret)
        base = _base_url()
        ar = _aspect_ratio(aspect)
        dur = _clamp_duration(duration)
        resolution = (os.getenv("HIGGSFIELD_RESOLUTION") or "720p").strip()
        # Our pipeline supplies TTS — disable model audio by default
        generate_audio = (os.getenv("HIGGSFIELD_GENERATE_AUDIO") or "false").strip().lower() in (
            "1", "true", "yes", "on",
        )

        payload_base = {
            "prompt": (prompt or "").strip()[:2000] or "cinematic vertical shot",
            "duration": dur,
            "resolution": resolution if resolution in ("480p", "720p", "1080p") else "720p",
            "aspect_ratio": ar,
            "output_format": "mp4",
            "generate_audio": generate_audio,
        }
        if seed is not None:
            payload_base["seed"] = int(seed)

        for model in _model_list():
            endpoint = f"{base}/{model}"
            try:
                submit = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload_base,
                    timeout=60,
                )
                if submit.status_code in (401, 403):
                    log_skip_once(self.name, f"auth fail HTTP {submit.status_code}")
                    return None
                if submit.status_code == 402:
                    log_skip_once(self.name, "balance empty (HTTP 402)")
                    return None
                if submit.status_code == 404:
                    print(f"    [AI-VIDEO:higgsfield] model not found: {model}")
                    continue
                if submit.status_code == 422:
                    # Retry with minimal body (some models reject extra fields)
                    minimal = {"prompt": payload_base["prompt"], "aspect_ratio": ar}
                    submit = requests.post(endpoint, headers=headers, json=minimal, timeout=60)
                if submit.status_code not in (200, 201, 202):
                    detail = ""
                    try:
                        detail = str(submit.json().get("detail") or submit.text[:200])
                    except Exception:
                        detail = submit.text[:200]
                    print(f"    [AI-VIDEO:higgsfield] submit {model} HTTP {submit.status_code}: {detail}")
                    continue

                body = submit.json()
                video_url = _extract_video_url(body)
                status_url = body.get("status_url")
                if not video_url and status_url:
                    done = _poll_status(str(status_url), headers)
                    if done:
                        video_url = _extract_video_url(done)
                if not video_url and body.get("request_id"):
                    # Construct status URL if API omitted status_url
                    fallback_status = f"{base}/requests/{body['request_id']}/status"
                    done = _poll_status(fallback_status, headers)
                    if done:
                        video_url = _extract_video_url(done)
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
                    duration=float(dur),
                    aspect=ar,
                    license=ai_generated_license(self.name, model, commercial_ok=True),
                    raw={"request_id": body.get("request_id"), "model": model},
                )
            except Exception as exc:
                print(f"    [AI-VIDEO:higgsfield] {model}: {exc}")
                continue
        return None
