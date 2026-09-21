"""Stitch short AI clips into a longer Short segment via ffmpeg concat."""
from __future__ import annotations

import math
import os
import subprocess
import tempfile
from typing import List, Optional, Sequence

import imageio_ffmpeg


def clip_count_for_duration(target_sec: float, clip_max: float = 5.0) -> int:
    t = max(float(target_sec or 5.0), 1.0)
    m = max(float(clip_max or 5.0), 2.0)
    return max(1, int(math.ceil(t / m)))


def ffmpeg_concat(paths: Sequence[str], output_path: str) -> Optional[str]:
    """
    Concat demuxer path list → single mp4 (re-encode for mismatched codecs).
    Returns output_path on success.
    """
    files = [p for p in paths if p and os.path.isfile(p) and os.path.getsize(p) > 1000]
    if not files:
        return None
    if len(files) == 1:
        if files[0] != output_path:
            import shutil
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            shutil.copy2(files[0], output_path)
        return output_path if os.path.isfile(output_path) else None

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        list_path = fh.name
        for p in files:
            # concat demuxer needs escaped single quotes in path
            safe = os.path.abspath(p).replace("'", "'\\''")
            fh.write(f"file '{safe}'\n")
    try:
        cmd = [
            ffmpeg, "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",
            output_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=180)
        if proc.returncode != 0 or not os.path.isfile(output_path):
            # Fallback: filter_complex concat
            return _filter_complex_concat(files, output_path, ffmpeg)
        if os.path.getsize(output_path) < 5000:
            return None
        print(f"    [AI-VIDEO:stitch] n={len(files)} → {os.path.basename(output_path)}")
        return output_path
    except Exception as exc:
        print(f"    [AI-VIDEO:stitch] fail: {exc}")
        return None
    finally:
        try:
            os.unlink(list_path)
        except OSError:
            pass


def _filter_complex_concat(files: List[str], output_path: str, ffmpeg: str) -> Optional[str]:
    try:
        inputs: List[str] = []
        for p in files:
            inputs.extend(["-i", p])
        n = len(files)
        filters = "".join(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                          f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
                          for i in range(n))
        concat_in = "".join(f"[v{i}]" for i in range(n))
        filters += f"{concat_in}concat=n={n}:v=1:a=0[outv]"
        cmd = [
            ffmpeg, "-y", *inputs,
            "-filter_complex", filters,
            "-map", "[outv]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=240)
        if proc.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 5000:
            print(f"    [AI-VIDEO:stitch] filter_complex n={n}")
            return output_path
    except Exception as exc:
        print(f"    [AI-VIDEO:stitch] filter fail: {exc}")
    return None
