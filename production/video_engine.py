"""Safe FFmpeg render facade with verification and transparent metadata."""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional

import imageio_ffmpeg

from render.ffmpeg_graph import render_with_ffmpeg_graph


class VideoEngine:
    def __init__(self, width: int = 1080, height: int = 1920) -> None:
        self.width = width
        self.height = height

    def render(self, clips: List[Dict[str, Any]], audio_path: str, output_path: str, *, title: str = "", word_timings: Optional[list] = None, subtitle_opts: Optional[dict] = None) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        path = render_with_ffmpeg_graph(
            clips,
            audio_path,
            output_path,
            title=title,
            word_timings=word_timings,
            subtitle_opts=subtitle_opts,
            anti_duplicate=False,
            enable_ken_burns=True,
        )
        report = self.verify(path or output_path)
        if not report["ok"]:
            raise RuntimeError(report["error"])
        return {"path": path, "verification": report}

    def verify(self, path: str) -> Dict[str, Any]:
        if not path or not os.path.isfile(path) or os.path.getsize(path) < 100_000:
            return {"ok": False, "error": "render output is missing or too small"}
        ffprobe = imageio_ffmpeg.get_ffmpeg_exe()
        try:
            result = subprocess.run([ffprobe, "-i", path, "-hide_banner"], capture_output=True, text=True, timeout=30)
            text = result.stderr or ""
            has_video = "Video:" in text
            has_audio = "Audio:" in text
            return {"ok": result.returncode == 0 and has_video and has_audio, "has_video": has_video, "has_audio": has_audio, "bytes": os.path.getsize(path)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
