"""Opt-in Sonilo video-to-SFX generation for completed renders."""

import logging
import os
import subprocess
import time
import uuid
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

import imageio_ffmpeg
import requests

import config
from render.pipeline_audit import _ffprobe_duration, _ffprobe_streams

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.sonilo.com"
VIDEO_TO_SFX_PATH = "/v1/video-to-sfx"
TASKS_PATH = "/v1/tasks"
MAX_VIDEO_DURATION_SECONDS = 180.0
CONNECT_TIMEOUT_SECONDS = 15
REQUEST_TIMEOUT_SECONDS = 600
POLL_TIMEOUT_SECONDS = 30
POLL_INTERVAL_SECONDS = 5.0
MIX_VOLUME = 0.6


class SoniloSfxError(RuntimeError):
    """A recoverable Sonilo SFX failure that leaves the original render intact."""


def _api_error_message(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        body = {}
    detail: Any = (
        body.get("detail") or body.get("error") or body.get("message")
        if isinstance(body, dict)
        else None
    )
    if isinstance(detail, dict):
        detail = detail.get("message") or detail.get("code")
    if not isinstance(detail, str):
        detail = ""
    detail = detail.strip()[:240]
    suffix = f": {detail}" if detail else ""
    return f"Sonilo API HTTP {response.status_code}{suffix}"


def _submit_task(video_path: str, api_key: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with open(video_path, "rb") as video_file:
            response = requests.post(
                f"{API_BASE_URL}{VIDEO_TO_SFX_PATH}",
                headers=headers,
                files={
                    "video": (os.path.basename(video_path), video_file, "video/mp4"),
                },
                timeout=(CONNECT_TIMEOUT_SECONDS, REQUEST_TIMEOUT_SECONDS),
            )
    except (OSError, requests.exceptions.RequestException) as exc:
        raise SoniloSfxError(f"Sonilo SFX task submission failed: {exc}") from exc

    if response.status_code >= 400:
        raise SoniloSfxError(_api_error_message(response))
    try:
        body = response.json()
    except ValueError as exc:
        raise SoniloSfxError("Sonilo SFX submission returned invalid JSON.") from exc
    task_id = body.get("task_id") if isinstance(body, dict) else None
    if not isinstance(task_id, str) or not task_id.strip():
        raise SoniloSfxError("Sonilo SFX submission did not return a task ID.")
    return task_id.strip()


def _task_error_message(body: Dict[str, Any], task_id: str) -> str:
    detail: Any = body.get("error")
    if isinstance(detail, dict):
        detail = detail.get("message") or detail.get("code")
    if not isinstance(detail, str) or not detail.strip():
        detail = "generation failed"
    refund_note = " (charge refunded)" if body.get("refunded") is True else ""
    return f"Sonilo SFX task {task_id} failed: {detail.strip()[:240]}{refund_note}"


def _poll_task(task_id: str, api_key: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.monotonic() + REQUEST_TIMEOUT_SECONDS
    last_error: Optional[BaseException] = None

    while True:
        try:
            response = requests.get(
                f"{API_BASE_URL}{TASKS_PATH}/{task_id}",
                headers=headers,
                timeout=(CONNECT_TIMEOUT_SECONDS, POLL_TIMEOUT_SECONDS),
            )
        except requests.exceptions.RequestException as exc:
            last_error = exc
        else:
            if response.status_code >= 500:
                last_error = SoniloSfxError(
                    f"Sonilo task polling returned HTTP {response.status_code}."
                )
            elif response.status_code >= 400:
                raise SoniloSfxError(_api_error_message(response))
            else:
                try:
                    body = response.json()
                except ValueError as exc:
                    raise SoniloSfxError(
                        "Sonilo SFX task polling returned invalid JSON."
                    ) from exc
                if not isinstance(body, dict):
                    raise SoniloSfxError(
                        "Sonilo SFX task polling returned an invalid response."
                    )
                status = body.get("status")
                if status == "succeeded":
                    return body
                if status == "failed":
                    raise SoniloSfxError(_task_error_message(body, task_id))

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SoniloSfxError(
                f"Timed out waiting for Sonilo SFX task {task_id}."
            ) from last_error
        time.sleep(min(POLL_INTERVAL_SECONDS, remaining))


def _result_audio_url(body: Dict[str, Any], task_id: str) -> str:
    audio = body.get("audio")
    url = audio.get("url") if isinstance(audio, dict) else None
    if not isinstance(url, str) or not url.strip():
        raise SoniloSfxError(
            f"Sonilo SFX task {task_id} succeeded without an audio URL."
        )
    try:
        parsed = urlsplit(url.strip())
    except ValueError as exc:
        raise SoniloSfxError("Sonilo returned an invalid SFX URL.") from exc
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise SoniloSfxError("Sonilo returned an unsafe SFX URL.")
    return url.strip()


def _download_audio(url: str) -> bytes:
    try:
        response = requests.get(url, timeout=(CONNECT_TIMEOUT_SECONDS, 60))
    except requests.exceptions.RequestException as exc:
        raise SoniloSfxError(f"Sonilo SFX download failed: {exc}") from exc
    if response.status_code >= 400:
        raise SoniloSfxError(
            f"Sonilo SFX download returned HTTP {response.status_code}."
        )
    if not response.content:
        raise SoniloSfxError("Sonilo returned an empty SFX audio file.")
    return response.content


def _request_sfx_audio(video_path: str, api_key: str) -> bytes:
    task_id = _submit_task(video_path, api_key)
    task = _poll_task(task_id, api_key)
    return _download_audio(_result_audio_url(task, task_id))


def _mix_sfx(video_path: str, audio_path: str, output_path: str) -> None:
    streams = _ffprobe_streams(video_path)
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    if not has_audio:
        raise SoniloSfxError(
            "Could not confirm the render's existing audio track; render preserved."
        )
    filter_complex = (
        f"[1:a:0]volume={MIX_VOLUME}[sfx];"
        "[0:a:0][sfx]amix=inputs=2:duration=first:"
        "dropout_transition=0:normalize=0[aout]"
    )

    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v:0",
        "-map",
        "[aout]",
        "-map_metadata",
        "0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
    ]
    command.extend(["-movflags", "+faststart", output_path])

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SoniloSfxError(f"FFmpeg could not mix Sonilo SFX: {exc}") from exc
    if result.returncode != 0:
        stderr = (result.stderr or b"").decode("utf-8", errors="replace")[-400:]
        raise SoniloSfxError(
            f"FFmpeg could not mix Sonilo SFX (exit {result.returncode}): {stderr}"
        )
    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise SoniloSfxError("FFmpeg did not produce a mixed video.")


def add_ai_sfx_to_video(video_path: str) -> None:
    """Generate SFX and atomically replace the render only after successful mixing."""
    api_key = str(getattr(config, "SONILO_API_KEY", "") or "").strip()
    if not api_key:
        raise SoniloSfxError("Sonilo API key is not configured.")
    if not video_path or not os.path.isfile(video_path):
        raise SoniloSfxError("Rendered video does not exist.")

    duration = _ffprobe_duration(video_path)
    if duration <= 0:
        raise SoniloSfxError("Could not verify video duration; Sonilo upload skipped.")
    if duration > MAX_VIDEO_DURATION_SECONDS:
        raise SoniloSfxError(
            f"Video duration {duration:.1f}s exceeds Sonilo's "
            f"{MAX_VIDEO_DURATION_SECONDS:.0f}s SFX limit."
        )

    token = uuid.uuid4().hex
    directory = os.path.dirname(os.path.abspath(video_path))
    audio_path = os.path.join(directory, f".sonilo_sfx_{token}.m4a")
    mixed_path = os.path.join(directory, f".sonilo_sfx_{token}.mp4")
    try:
        audio = _request_sfx_audio(video_path, api_key)
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio)
        _mix_sfx(video_path, audio_path, mixed_path)
        os.replace(mixed_path, video_path)
    except SoniloSfxError:
        raise
    except OSError as exc:
        raise SoniloSfxError(f"Could not save the Sonilo SFX render: {exc}") from exc
    finally:
        for temporary_path in (audio_path, mixed_path):
            try:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
            except OSError as exc:
                logger.warning(
                    "Could not remove temporary Sonilo file %s: %s",
                    temporary_path,
                    exc,
                )
