"""Local, descriptive edit-cadence analysis for reference videos."""

from __future__ import annotations

import math
import re
import statistics
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import imageio_ffmpeg


_CUT_THRESHOLD = 0.25
_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_VIDEO_STREAM_RE = re.compile(r"^\s*Stream #.*?: Video:", re.MULTILINE)
_AUDIO_STREAM_RE = re.compile(r"^\s*Stream #.*?: Audio:", re.MULTILINE)
_RESOLUTION_RE = re.compile(r"\b(\d{2,5})x(\d{2,5})\b")
_FPS_RE = re.compile(r"(?:,|\s)(\d+(?:\.\d+)?)\s+fps\b")
_CUT_RE = re.compile(r"pts_time:([-+]?\d+(?:\.\d+)?)")
_LUFS_RE = re.compile(r"\bI:\s*(-?\d+(?:\.\d+)?)\s*LUFS\b")


class VideoTeardownError(RuntimeError):
    """Raised when FFmpeg cannot produce a complete reference-video report."""


def _run_ffmpeg(input_path: str, output_args: List[str], timeout: float) -> str:
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-hide_banner",
        "-nostdin",
        "-i",
        input_path,
        *output_args,
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise VideoTeardownError(
            f"Video analizi {timeout:.0f} saniyede tamamlanmadı."
        ) from exc
    except OSError as exc:
        raise VideoTeardownError(f"FFmpeg çalıştırılamadı: {exc}") from exc

    stderr = result.stderr.decode("utf-8", errors="replace")
    if result.returncode != 0:
        detail = stderr[-500:].strip() or f"exit code {result.returncode}"
        raise VideoTeardownError(f"FFmpeg video analiz hatası: {detail}")
    return stderr


def _probe_media(input_path: str) -> Tuple[float, int, int, Optional[float], bool]:
    stderr = _run_ffmpeg(
        input_path,
        ["-frames:v", "1", "-an", "-f", "null", "-"],
        timeout=30.0,
    )
    duration_match = _DURATION_RE.search(stderr)
    video_line_match = _VIDEO_STREAM_RE.search(stderr)
    if not duration_match or not video_line_match:
        raise VideoTeardownError("FFmpeg geçerli video süresi veya video akışı bulamadı.")

    hours, minutes, seconds = duration_match.groups()
    duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    video_line_end = stderr.find("\n", video_line_match.start())
    video_line = stderr[video_line_match.start():video_line_end if video_line_end >= 0 else None]
    resolution_match = _RESOLUTION_RE.search(video_line)
    if not math.isfinite(duration) or duration <= 0 or not resolution_match:
        raise VideoTeardownError("Video süresi veya çözünürlüğü geçersiz.")

    fps_match = _FPS_RE.search(video_line)
    fps = float(fps_match.group(1)) if fps_match else None
    return (
        duration,
        int(resolution_match.group(1)),
        int(resolution_match.group(2)),
        fps,
        bool(_AUDIO_STREAM_RE.search(stderr)),
    )


def _cut_statistics(cut_times: List[float], duration: float) -> Dict[str, Any]:
    boundaries = [0.0, *cut_times, duration]
    intervals = [
        round(end - start, 3)
        for start, end in zip(boundaries, boundaries[1:])
        if end > start
    ]
    return {
        "cut_count": len(cut_times),
        "cuts_per_minute": round(len(cut_times) / duration * 60.0, 2),
        "shot_interval_count": len(intervals),
        "median_shot_interval_sec": round(statistics.median(intervals), 3) if intervals else None,
        "shot_interval_stddev_sec": round(statistics.pstdev(intervals), 3) if len(intervals) > 1 else 0.0,
        "shortest_shot_sec": min(intervals) if intervals else None,
    }


def analyze_reference_video(input_path: str) -> Dict[str, Any]:
    """Measure scene-cut cadence and integrated loudness without uploading media."""
    duration, width, height, fps, has_audio = _probe_media(input_path)
    filter_args = ["-vf", f"select='gt(scene,{_CUT_THRESHOLD})',showinfo", "-an"]
    if has_audio:
        filter_args = [
            "-vf",
            f"select='gt(scene,{_CUT_THRESHOLD})',showinfo",
            "-af",
            "ebur128=framelog=quiet",
        ]
    stderr = _run_ffmpeg(input_path, [*filter_args, "-f", "null", "-"], timeout=300.0)
    cut_times = sorted({
        round(float(match.group(1)), 3)
        for match in _CUT_RE.finditer(stderr)
        if 0.2 < float(match.group(1)) < duration
    })
    lufs_matches = list(_LUFS_RE.finditer(stderr)) if has_audio else []
    integrated_lufs = float(lufs_matches[-1].group(1)) if lufs_matches else None
    notes = [
        "Ölçümler tanımlayıcıdır; performans veya platform başarısı garantisi değildir.",
        "Otomatik altyazı/OCR analizi bu rapora dahil değildir.",
    ]
    if has_audio and integrated_lufs is None:
        raise VideoTeardownError("Ses akışı bulundu ancak entegre LUFS ölçümü alınamadı.")
    if not has_audio:
        notes.append("Ses akışı bulunmadı; LUFS ölçümü atlandı.")

    report: Dict[str, Any] = {
        "duration_sec": round(duration, 3),
        "resolution": {"width": width, "height": height},
        "fps": fps,
        "cut_threshold": _CUT_THRESHOLD,
        "cut_timestamps_sec": cut_times,
        **_cut_statistics(cut_times, duration),
        "integrated_lufs": integrated_lufs,
        "notes": notes,
    }
    return report
