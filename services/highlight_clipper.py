"""
Long-video Shorts clipper. Separate from the narration render.

anil dedupe_highlights drops a candidate when overlap exceeds half of that
candidate only, and _sanitize_highlights clamps to the file duration.
openshorts dedupe_overlapping uses the shorter span, so a long window cannot
hide a short duplicate. openshorts snap_clip_to_words lands on word edges.
FunClip video_clip then adds start_ost/end_ost in milliseconds; those offsets
are applied here and pulled back out of a word if they land inside one.
autoclip edit_video_by_subtitle_deletion drops named subtitle ranges and
concatenates what remains. The vertical frame is one FFmpeg cover crop.
anil _reframe_vertical re-encodes every frame in OpenCV. That path is not used.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional, Sequence, Tuple

OUT_W = 1080
OUT_H = 1920


def clamp_span(start: float, end: float, duration: float) -> Optional[Tuple[float, float]]:
    start = float(start)
    end = float(end)
    if duration and duration > 0:
        start = min(max(0.0, start), float(duration))
        end = min(max(0.0, end), float(duration))
    else:
        start = max(0.0, start)
        end = max(0.0, end)
    if end <= start:
        return None
    return start, end


def _score(item: Dict[str, Any]) -> float:
    for key in ("score", "predicted_score"):
        if item.get(key) is None:
            continue
        try:
            return float(item.get(key))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _span(item: Dict[str, Any]) -> Tuple[float, float]:
    if item.get("start_time") is not None or item.get("end_time") is not None:
        return float(item.get("start_time") or 0.0), float(item.get("end_time") or 0.0)
    return float(item.get("start") or 0.0), float(item.get("end") or 0.0)


def normalize_words(words: Optional[Sequence[Dict[str, Any]]]) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for word in words or []:
        if not isinstance(word, dict):
            continue
        start = word.get("s", word.get("start"))
        end = word.get("e", word.get("end"))
        if start is None or end is None:
            continue
        try:
            s = float(start)
            e = float(end)
        except (TypeError, ValueError):
            continue
        if e <= s:
            continue
        rows.append({"s": s, "e": e})
    rows.sort(key=lambda row: row["s"])
    return rows


def dedupe_overlapping(clips: Sequence[Dict[str, Any]], ratio: float = 0.5) -> List[Dict[str, Any]]:
    """Drop a clip when the overlap is at least `ratio` of the shorter span."""
    indexed = list(enumerate(clips or []))
    kept: List[Tuple[int, Dict[str, Any]]] = []
    for idx, clip in sorted(indexed, key=lambda pair: (-_score(pair[1]), pair[0])):
        if not isinstance(clip, dict):
            continue
        start, end = _span(clip)
        if end <= start:
            continue
        clash = False
        for _, other in kept:
            other_start, other_end = _span(other)
            overlap = min(end, other_end) - max(start, other_start)
            shorter = max(1e-6, min(end - start, other_end - other_start))
            if overlap > 0 and overlap / shorter >= ratio:
                clash = True
                break
        if not clash:
            kept.append((idx, clip))
    return [clip for _, clip in sorted(kept, key=lambda pair: pair[0])]


def _escape_interiors(
    start: float,
    end: float,
    words: Sequence[Dict[str, float]],
    duration: float,
) -> Tuple[float, float]:
    for word in words:
        if word["s"] < start < word["e"]:
            start = word["s"]
        if word["s"] < end < word["e"]:
            end = word["e"]
    if duration and duration > 0:
        start = max(0.0, min(start, duration))
        end = min(end, duration)
    return start, end


def inside_word(time_s: float, words: Sequence[Dict[str, Any]]) -> bool:
    for word in normalize_words(words):
        if word["s"] < float(time_s) < word["e"]:
            return True
    return False


def snap_span(
    start: float,
    end: float,
    words: Optional[Sequence[Dict[str, Any]]],
    video_duration: float,
    start_ost_ms: float = 0.0,
    end_ost_ms: float = 0.0,
    min_duration: float = 8.0,
    max_duration: float = 75.0,
    search_window: float = 1.5,
    max_lead: float = 0.35,
    max_tail: float = 0.45,
) -> Tuple[float, float]:
    """
    Snap to the nearest word edge, then apply FunClip millisecond offsets.
    An offset that falls inside a word is pulled back to the word edge.
    """
    rows = normalize_words(words)
    duration = float(video_duration or 0.0)
    start = float(start)
    end = float(end)
    if not rows:
        shifted = clamp_span(start + start_ost_ms / 1000.0, end + end_ost_ms / 1000.0, duration)
        return shifted if shifted else (round(start, 3), round(end, 3))

    starts = [row["s"] for row in rows]
    ends = [row["e"] for row in rows]
    new_start = start
    start_hits = [s for s in starts if abs(s - new_start) <= search_window]
    if start_hits:
        word_start = min(start_hits, key=lambda s: abs(s - new_start))
        prev_ends = [e for e in ends if e <= word_start]
        if prev_ends:
            gap = max(0.0, word_start - max(prev_ends))
            lead = min(max_lead, gap / 2.0)
        else:
            lead = max_lead
        new_start = max(0.0, word_start - lead)

    new_end = end
    end_hits = [e for e in ends if abs(e - new_end) <= search_window]
    if end_hits:
        word_end = min(end_hits, key=lambda e: abs(e - new_end))
        next_starts = [s for s in starts if s >= word_end]
        if next_starts:
            gap = max(0.0, min(next_starts) - word_end)
            tail = min(max_tail, gap / 2.0)
        else:
            tail = max_tail
        limit = duration if duration > 0 else word_end + tail
        new_end = min(limit, word_end + tail)

    new_start += float(start_ost_ms) / 1000.0
    new_end += float(end_ost_ms) / 1000.0
    new_start, new_end = _escape_interiors(new_start, new_end, rows, duration)

    if new_end - new_start < min_duration:
        target = new_start + min_duration
        later = sorted(e for e in ends if e >= target - 0.05)
        if later:
            new_end = later[0]
            new_start, new_end = _escape_interiors(new_start, new_end, rows, duration)
    if new_end - new_start > max_duration:
        target = new_start + max_duration
        earlier = [e for e in ends if new_start < e <= target]
        new_end = max(earlier) if earlier else min(new_end, new_start + max_duration)
        new_start, new_end = _escape_interiors(new_start, new_end, rows, duration)

    if new_end <= new_start:
        new_start, new_end = _escape_interiors(start, end, rows, duration)
    return round(new_start, 3), round(new_end, 3)


def select_highlights(
    raw: Sequence[Dict[str, Any]],
    duration: float,
    words: Optional[Sequence[Dict[str, Any]]] = None,
    num_clips: int = 3,
    start_ost_ms: float = 0.0,
    end_ost_ms: float = 0.0,
    ratio: float = 0.5,
) -> List[Dict[str, Any]]:
    limit = max(1, min(5, int(num_clips or 1)))
    cleaned: List[Dict[str, Any]] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        start, end = _span(item)
        clamped = clamp_span(start, end, duration)
        if not clamped:
            continue
        snapped = snap_span(
            clamped[0],
            clamped[1],
            words,
            duration,
            start_ost_ms=start_ost_ms,
            end_ost_ms=end_ost_ms,
        )
        if snapped[1] <= snapped[0]:
            continue
        row = dict(item)
        row["start_time"] = snapped[0]
        row["end_time"] = snapped[1]
        row["start"] = snapped[0]
        row["end"] = snapped[1]
        cleaned.append(row)
    kept = dedupe_overlapping(cleaned, ratio=ratio)
    kept.sort(key=lambda clip: (-_score(clip), _span(clip)[0]))
    return kept[:limit]


def kept_timeline(
    segments: Sequence[Dict[str, Any]],
    deleted_ids: Sequence[Any],
) -> List[Tuple[float, float]]:
    """Drop deleted subtitle ranges. Touching survivors merge. Gaps stay."""
    deleted = {str(item) for item in (deleted_ids or [])}
    rows: List[Tuple[float, float]] = []
    for index, segment in enumerate(segments or []):
        if not isinstance(segment, dict):
            continue
        sid = str(segment.get("id", index))
        try:
            start = float(segment.get("start", segment.get("startTime", 0.0)) or 0.0)
            end = float(segment.get("end", segment.get("endTime", 0.0)) or 0.0)
        except (TypeError, ValueError):
            continue
        if end <= start or sid in deleted:
            continue
        rows.append((start, end))
    rows.sort()
    merged: List[Tuple[float, float]] = []
    for start, end in rows:
        if merged and start <= merged[-1][1] + 0.05:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def vertical_vf(
    src_w: int,
    src_h: int,
    crop_x: Optional[int] = None,
    out_w: int = OUT_W,
    out_h: int = OUT_H,
) -> str:
    src_w = max(2, int(src_w or 2))
    src_h = max(2, int(src_h or 2))
    scale = max(out_w / float(src_w), out_h / float(src_h))
    scaled_w = int(src_w * scale)
    scaled_h = int(src_h * scale)
    scaled_w -= scaled_w % 2
    scaled_h -= scaled_h % 2
    scaled_w = max(out_w, scaled_w)
    scaled_h = max(out_h, scaled_h)
    max_x = max(0, scaled_w - out_w)
    if crop_x is None:
        x = max_x // 2
    else:
        x = max(0, min(max_x, int(crop_x)))
    y = max(0, (scaled_h - out_h) // 2)
    return f"scale={scaled_w}:{scaled_h}:flags=lanczos,crop={out_w}:{out_h}:{x}:{y},setsar=1"


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _probe_wh(path: str) -> Tuple[int, int]:
    try:
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return 0, 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        cap.release()
        return width, height
    except Exception:
        return 0, 0


def _has_audio(path: str, ffmpeg: str) -> bool:
    proc = subprocess.run([ffmpeg, "-hide_banner", "-i", path], capture_output=True, text=True)
    return "Audio:" in (proc.stderr or "")


def cut_ranges_vertical(
    source: str,
    ranges: Sequence[Tuple[float, float]],
    out_path: str,
    crop_x: Optional[int] = None,
) -> str:
    """One FFmpeg graph. Trim, concat, then 9:16 cover crop."""
    if not source or not os.path.isfile(source):
        raise FileNotFoundError(source)
    usable = [(float(a), float(b)) for a, b in ranges if float(b) > float(a)]
    if not usable:
        raise ValueError("Kesilecek aralık yok.")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    ffmpeg = _ffmpeg_exe()
    width, height = _probe_wh(source)
    if width < 2 or height < 2:
        width, height = 1920, 1080
    if crop_x is None:
        try:
            from render.ffmpeg_graph import face_cover_crop_x
            crop_x = face_cover_crop_x(source, OUT_W, OUT_H)
        except Exception:
            crop_x = None
    vf = vertical_vf(width, height, crop_x=crop_x)
    audio = _has_audio(source, ffmpeg)
    parts: List[str] = []
    links: List[str] = []
    for index, (start, end) in enumerate(usable):
        parts.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{index}]")
        links.append(f"[v{index}]")
        if audio:
            parts.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{index}]")
            links.append(f"[a{index}]")
    if audio:
        parts.append(f"{''.join(links)}concat=n={len(usable)}:v=1:a=1[vc][ac]")
        parts.append(f"[vc]{vf}[vout]")
        maps = ["-map", "[vout]", "-map", "[ac]", "-c:a", "aac"]
    else:
        parts.append(f"{''.join(links)}concat=n={len(usable)}:v=1:a=0[vc]")
        parts.append(f"[vc]{vf}[vout]")
        maps = ["-map", "[vout]"]
    cmd = [
        ffmpeg, "-y", "-i", source,
        "-filter_complex", ";".join(parts),
        *maps,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.isfile(out_path):
        tail = (proc.stderr or "")[-400:]
        raise RuntimeError(tail or "ffmpeg kesim başarısız")
    return out_path
