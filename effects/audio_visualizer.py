"""
effects/audio_visualizer.py — Dynamic Audio Waveform & Spectrum Visualizer.

Adapted and evolved for Section 2.1 (Item 8) & Section 28.8:
Replaces missing MoviePy waveform scripts with native FFmpeg hardware-accelerated
`showwaves` and `showfreqs` filter generators.
Overlays a dynamic, glowing, transparent audio spectrum directly underneath
karaoke subtitles for podcast, debate, philosophy, and documentary shorts.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import imageio_ffmpeg
from services.path_security import validate_asset_path


logger = logging.getLogger("audio_visualizer")


def get_ffmpeg_binary() -> str:
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


RECOMMENDED_NICHES = frozenset({
    "podcast",
    "podcast_debate",
    "debate",
    "stoic_quotes",
    "philosophy",
    "motivation",
    "knowledge",
    "facts",
    "confession",
    "reddit_story",
    "history_talk",
    "audiobook",
})


def is_visualizer_recommended_for_niche(niche: str) -> bool:
    """Returns True if the given content niche is ideal for dynamic audio waveform overlay."""
    if not niche:
        return False
    norm = str(niche).strip().lower().replace("-", "_")
    return norm in RECOMMENDED_NICHES or any(n in norm for n in ("podcast", "quote", "debate", "talk"))


def build_waveform_filter(
    audio_tag: str = "1:a",
    video_tag: str = "0:v",
    out_tag: str = "out_wave",
    width: int = 1080,
    height: int = 160,
    x_pos: Optional[str] = None,
    y_pos: int = 1380,
    mode: str = "line",
    color: str = "0x00D7FF@0.85",
    scale: str = "sqrt",
    opacity: float = 0.85,
) -> Tuple[str, str]:
    """
    Constructs an FFmpeg filter_complex fragment for rendering a real-time reactive
    waveform spectrum overlay without Python GIL or PIL CPU loops.

    Returns:
        (filter_string, out_tag)
    """
    w = max(100, int(width))
    h = max(40, int(height))
    x_expr = x_pos if x_pos is not None else "(W-w)/2"
    y_expr = str(y_pos)

    # Format color if hex string like #00D7FF or 0x00D7FF
    clean_color = color.replace("#", "0x")
    if "@" not in clean_color:
        clean_color = f"{clean_color}@{opacity:.2f}"

    if mode in ("frequency_bars", "showfreqs", "spectrum"):
        # Frequency spectrum analyzer (bars)
        wave_gen = (
            f"[{audio_tag}]showfreqs=s={w}x{h}:mode=bar:ascale=log:fscale=log:"
            f"colors={clean_color},format=yuva420p[wave_stream]"
        )
    else:
        # Oscilloscope waveform line (line, p2p, cline)
        wave_mode = mode if mode in ("line", "p2p", "cline") else "line"
        wave_gen = (
            f"[{audio_tag}]showwaves=s={w}x{h}:mode={wave_mode}:colors={clean_color}:"
            f"scale={scale},format=yuva420p[wave_stream]"
        )

    overlay_expr = (
        f"[{video_tag}][wave_stream]overlay=x={x_expr}:y={y_expr}:shortest=1[{out_tag}]"
    )

    full_filter = f"{wave_gen};{overlay_expr}"
    return full_filter, out_tag


def render_standalone_waveform(
    audio_path: str,
    output_path: str,
    duration: Optional[float] = None,
    width: int = 1080,
    height: int = 180,
    mode: str = "line",
    color: str = "0x00D7FF@0.90",
    fps: int = 30,
) -> str:
    """
    Renders a standalone transparent alpha video file (MOV/ProRes or WebM/VP9)
    representing the audio waveform spectrum.
    """
    valid_audio = validate_asset_path(audio_path)
    if not os.path.isfile(valid_audio):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    ffmpeg_exe = get_ffmpeg_binary()

    clean_color = color.replace("#", "0x")
    if "@" not in clean_color:
        clean_color = f"{clean_color}@0.90"

    if mode in ("frequency_bars", "showfreqs", "spectrum"):
        filter_str = (
            f"showfreqs=s={width}x{height}:mode=bar:ascale=log:fscale=log:"
            f"colors={clean_color},format=yuva420p,fps={fps}"
        )
    else:
        wave_mode = mode if mode in ("line", "p2p", "cline") else "line"
        filter_str = (
            f"showwaves=s={width}x{height}:mode={wave_mode}:colors={clean_color}:"
            f"scale=sqrt,format=yuva420p,fps={fps}"
        )

    cmd = [
        ffmpeg_exe, "-y", "-loglevel", "error",
        "-i", valid_audio,
        "-filter_complex", filter_str,
    ]

    if duration and float(duration) > 0:
        cmd.extend(["-t", f"{float(duration):.3f}"])

    # Output encoding
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".webm":
        cmd.extend(["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p"])
    elif ext == ".mov":
        cmd.extend(["-c:v", "png", "-pix_fmt", "rgba"])
    else:
        # Fallback to standard MP4 with black background
        cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p"])

    cmd.append(output_path)

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        err = (res.stderr or "").strip()
        raise RuntimeError(f"FFmpeg audio waveform rendering failed: {err}")

    return output_path
