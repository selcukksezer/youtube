"""Opt-in, video-and-audio-aware highlight suggestions via TwelveLabs Pegasus."""

from __future__ import annotations

import math
import os
import re
from typing import Any, Dict, List
from urllib.parse import urlparse


_SEGMENT_RE = re.compile(
    r"^\s*(?:\d+\.\s*)?\[(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\]\s*(.+?)\s*$",
    re.MULTILINE,
)
_PROMPT = """You are a video clipping assistant. Analyze the actual video visuals and audio.
Select up to {num_clips} engaging, self-contained highlight segments.
Each segment must be 8 to 75 seconds long, remain within the video, and capture a
complete moment. Consider the full video timeline, not only its opening. When
several strong moments exist, prefer distinct, non-overlapping moments across
the timeline instead of repeated moments from one section. Base each description
only on visible or audible evidence; do not invent context. Return segments in
chronological order. Reply only with one segment per line in this format:
1. [start_seconds-end_seconds] brief description
Use decimal seconds from the beginning of the video."""


class MultimodalConfigurationError(RuntimeError):
    """Raised when the optional video-understanding provider is not configured."""


def multimodal_analysis_requested(payload: Dict[str, Any]) -> bool:
    mode = str(payload.get("analysis_mode") or "transcript").strip().lower()
    if mode not in {"transcript", "multimodal"}:
        raise ValueError("analysis_mode must be 'transcript' or 'multimodal'.")
    if mode != "multimodal":
        return False

    consent = payload.get("external_analysis_consent")
    if consent is not True and str(consent or "").strip().lower() not in {
        "1", "true", "yes", "on",
    }:
        raise ValueError(
            "Multimodal analiz için videonun TwelveLabs'a gönderilmesine açık onay gerekli."
        )
    return True


def parse_pegasus_highlights(
    response_text: str,
    *,
    video_duration: float,
    num_clips: int,
) -> List[Dict[str, Any]]:
    """Parse and validate Pegasus timestamped segment suggestions."""
    if not isinstance(response_text, str):
        return []

    try:
        duration = float(video_duration)
    except (TypeError, ValueError):
        return []
    if not math.isfinite(duration) or duration <= 0:
        return []
    limit = max(1, min(5, int(num_clips or 1)))
    highlights: List[Dict[str, Any]] = []
    for match in _SEGMENT_RE.finditer(response_text):
        start = float(match.group(1))
        end = float(match.group(2))
        title = match.group(3).strip()
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or not title
            or start < 0
            or end > duration
        ):
            continue
        clip_duration = end - start
        if clip_duration < 8.0 or clip_duration > 75.0:
            continue
        highlights.append({
            "title": title,
            "start_time": round(start, 3),
            "end_time": round(end, 3),
            "score": 0,
            "source": "twelvelabs_pegasus",
        })
    highlights.sort(key=lambda item: (item["start_time"], item["end_time"]))
    return highlights[:limit]


def analyze_video_highlights(
    video_url: str,
    *,
    video_duration: float,
    num_clips: int,
) -> List[Dict[str, Any]]:
    """Ask Pegasus to identify highlights from a user-approved public URL."""
    parsed_url = urlparse(str(video_url or "").strip())
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("Multimodal analiz için geçerli bir HTTP(S) video URL gerekli.")

    api_key = os.getenv("TWELVELABS_API_KEY", "").strip()
    if not api_key:
        raise MultimodalConfigurationError(
            "Multimodal analiz yapılandırılmamış. TWELVELABS_API_KEY ayarlayın."
        )

    try:
        from twelvelabs import TwelveLabs
        from twelvelabs.types.video_context import VideoContext_Url
    except ImportError as exc:
        raise MultimodalConfigurationError(
            "TwelveLabs SDK eksik. requirements.txt bağımlılıklarını yükleyin."
        ) from exc

    client = TwelveLabs(api_key=api_key)
    response = client.analyze(
        model_name="pegasus1.5",
        video=VideoContext_Url(url=video_url),
        prompt=_PROMPT.format(num_clips=max(1, min(5, int(num_clips or 1)))),
        max_tokens=2048,
    )
    suggestions = parse_pegasus_highlights(
        response.data,
        video_duration=video_duration,
        num_clips=num_clips,
    )
    if not suggestions:
        raise RuntimeError("TwelveLabs geçerli zaman aralıklı klip önerisi döndürmedi.")
    return suggestions
