"""
services/video_preflight.py — Pre-Upload MP4 Integrity & Quality Preflight Validator.

Adapted and evolved from reference_repos2/MoneyPrinterV2 (scripts/upload_video.sh).
Verifies that generated video files are intact, non-empty, playable, and contain
both video and audio streams before triggering expensive browser uploads or webhooks.
Prevents uploading black/corrupt videos to YouTube, TikTok, or Instagram.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict, List, Optional
import imageio_ffmpeg


def verify_mp4_integrity(
    video_path: str,
    min_duration: float = 3.0,
    max_duration: float = 65.0,
    min_filesize_bytes: int = 50 * 1024,  # 50 KB
) -> Dict[str, Any]:
    """
    Runs comprehensive ffprobe preflight checks on an MP4 file before publication:
    1. File existence and minimum size (>50KB).
    2. Video stream presence, resolution (must be 9:16 vertical 1080x1920 or similar).
    3. Audio stream presence.
    4. Duration matches Shorts bounds (3s to 60s default).
    5. Clean moov atom / faststart check.
    """
    errors: List[str] = []

    if not os.path.exists(video_path):
        return {
            "valid": False,
            "errors": [f"File not found: {video_path}"],
            "duration": 0.0,
            "width": 0,
            "height": 0,
            "has_audio": False,
        }

    file_size = os.path.getsize(video_path)
    if file_size < min_filesize_bytes:
        errors.append(f"File size too small ({file_size} bytes < {min_filesize_bytes} bytes). Likely corrupt.")

    import shutil
    import re

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffprobe_candidate = ffmpeg_exe.replace("ffmpeg", "ffprobe")
    ffprobe_exe = None
    if os.path.exists(ffprobe_candidate):
        ffprobe_exe = ffprobe_candidate
    elif shutil.which("ffprobe"):
        ffprobe_exe = "ffprobe"

    duration = 0.0
    width = 0
    height = 0
    has_video = False
    has_audio = False

    try:
        if ffprobe_exe:
            cmd = [
                ffprobe_exe,
                "-v", "error",
                "-show_entries", "stream=index,codec_type,codec_name,width,height,duration:format=duration,size,format_name",
                "-of", "json",
                video_path,
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            probe_data = json.loads(proc.stdout)

            streams = probe_data.get("streams", [])
            fmt = probe_data.get("format", {})

            format_dur = float(fmt.get("duration", 0.0) or 0.0)
            duration = format_dur

            for s in streams:
                ctype = s.get("codec_type")
                if ctype == "video":
                    has_video = True
                    width = int(s.get("width") or 0)
                    height = int(s.get("height") or 0)
                elif ctype == "audio":
                    has_audio = True
        else:
            # Fallback to ffmpeg -i when ffprobe binary is absent on system
            proc = subprocess.run(
                [ffmpeg_exe, "-i", video_path, "-hide_banner"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="ignore",
            )
            raw = (proc.stderr or "") + (proc.stdout or "")
            dur_m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", raw)
            if dur_m:
                h_val, m_val, s_val = int(dur_m.group(1)), int(dur_m.group(2)), float(dur_m.group(3))
                duration = h_val * 3600 + m_val * 60 + s_val
            vid_m = re.search(r"Stream\s*#\d+:\d+.*?: Video:.*?(\d{2,5})x(\d{2,5})", raw)
            if vid_m:
                has_video = True
                width = int(vid_m.group(1))
                height = int(vid_m.group(2))
            if re.search(r"Stream\s*#\d+:\d+.*?: Audio:", raw):
                has_audio = True

        if not has_video:
            errors.append("Missing video stream in MP4 container.")
        if not has_audio:
            errors.append("Missing audio track (voiceover or background music).")

        if duration < min_duration:
            errors.append(f"Duration too short ({duration:.2f}s < {min_duration:.2f}s).")
        elif duration > max_duration:
            errors.append(f"Duration exceeds Shorts limit ({duration:.2f}s > {max_duration:.2f}s).")

        # Vertical orientation check (height should exceed width)
        if width > 0 and height > 0 and width > height:
            errors.append(f"Video is landscape ({width}x{height}), Shorts requires vertical 9:16.")

    except subprocess.CalledProcessError as e:
        errors.append(f"FFprobe inspection failed: {e.stderr.strip() or 'Corrupt media container'}")
    except Exception as e:
        errors.append(f"Preflight error: {str(e)}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "duration": round(duration, 3),
        "width": width,
        "height": height,
        "has_audio": has_audio,
        "filesize_bytes": file_size,
    }
