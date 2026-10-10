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
            raise RuntimeError(report.get("error", "verification failed"))
        return {"path": path, "verification": report}

    def verify(self, path: str) -> Dict[str, Any]:
        if not path or not os.path.isfile(path) or os.path.getsize(path) < 100_000:
            return {"ok": False, "error": "render output is missing or too small"}
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        try:
            # NB: `ffmpeg -i` with no output file always exits non-zero; the
            # stream info is still printed to stderr, so judge by that.
            result = subprocess.run([ffmpeg, "-i", path, "-hide_banner"], capture_output=True, text=True, timeout=30)
            text = result.stderr or ""
            has_video = "Video:" in text
            has_audio = "Audio:" in text
            if has_video and has_audio:
                return {"ok": True, "has_video": True, "has_audio": True, "bytes": os.path.getsize(path)}
            return {"ok": False, "error": "render output is missing video/audio stream",
                    "has_video": has_video, "has_audio": has_audio, "bytes": os.path.getsize(path)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
