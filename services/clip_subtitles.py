"""Build subtitle sidecars for clipped source-video ranges."""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence


def _finite_seconds(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    return seconds if math.isfinite(seconds) else None


def _segment_bounds(segment: Mapping[str, Any]) -> tuple[float, float] | None:
    start = _finite_seconds(segment.get("start", segment.get("s")))
    end = _finite_seconds(segment.get("end", segment.get("e")))
    if end is None and start is not None:
        duration = _finite_seconds(segment.get("duration"))
        if duration is not None:
            end = start + duration
    if start is None or end is None or end <= start:
        return None
    return start, end


def _format_srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return (
        f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},"
        f"{milliseconds:03d}"
    )


def _normalized_segments(
    segments: Iterable[Mapping[str, Any]],
) -> list[tuple[float, float, str]]:
    normalized = []
    for segment in segments:
        if not isinstance(segment, Mapping):
            continue
        bounds = _segment_bounds(segment)
        text = " ".join(
            str(segment.get("text") or segment.get("word") or segment.get("w") or "").split()
        )
        if bounds is not None and text:
            normalized.append((bounds[0], bounds[1], text))
    return normalized


def _format_srt_cues(cues: list[tuple[float, float, str]]) -> str:
    blocks = [
        f"{index}\n{_format_srt_time(start)} --> {_format_srt_time(end)}\n{text}"
        for index, (start, end, text) in enumerate(cues, start=1)
    ]
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def build_full_srt(segments: Iterable[Mapping[str, Any]]) -> str:
    """Return source-timeline SRT cues without rebasing or range selection."""
    cues = [
        (start, end, text)
        for start, end, text in _normalized_segments(segments)
        if round(end * 1000) > round(start * 1000)
    ]
    cues.sort(key=lambda cue: (cue[0], cue[1]))
    return _format_srt_cues(cues)


def build_clip_srt(
    segments: Iterable[Mapping[str, Any]],
    ranges: Iterable[Sequence[Any]],
) -> str:
    """Return SRT cues rebased to the concatenated output timeline."""
    normalized_segments = _normalized_segments(segments)
    cues: list[tuple[float, float, str]] = []
    timeline_offset = 0.0

    for clip_range in ranges:
        try:
            source_start = _finite_seconds(clip_range[0])
            source_end = _finite_seconds(clip_range[1])
        except (IndexError, TypeError):
            continue
        if source_start is None or source_end is None or source_end <= source_start:
            continue
        source_start = max(0.0, source_start)
        if source_end <= source_start:
            continue

        for segment_start, segment_end, text in normalized_segments:
            if not text:
                continue
            overlap_start = max(source_start, segment_start)
            overlap_end = min(source_end, segment_end)
            if overlap_end <= overlap_start:
                continue
            cue_start = timeline_offset + overlap_start - source_start
            cue_end = timeline_offset + overlap_end - source_start
            if round(cue_end * 1000) <= round(cue_start * 1000):
                continue
            cues.append((cue_start, cue_end, text))

        timeline_offset += source_end - source_start

    cues.sort(key=lambda cue: (cue[0], cue[1]))
    return _format_srt_cues(cues)
