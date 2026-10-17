"""
FFmpeg probing, path escaping, encoder fallback, and process cleanup helpers.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

import imageio_ffmpeg

import config


def _fg():
    return sys.modules.get("render.ffmpeg_graph")


def _fg_os():
    fg = _fg()
    return getattr(fg, "os", os) if fg is not None else os


def _fg_subprocess():
    fg = _fg()
    return getattr(fg, "subprocess", subprocess) if fg is not None else subprocess


def _fg_config():
    fg = _fg()
    return getattr(fg, "config", config) if fg is not None else config


def _escape_ass_path(path: str) -> str:
    # FFmpeg subtitles filter on Windows needs escaped drive and slashes
    p = _fg_os().path.abspath(path).replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        p = p[0] + "\\:" + p[2:]
    return p.replace("'", r"\'")


def _escape_filter_path(path: str) -> str:
    """Alias for FFmpeg filter path escaping."""
    return _escape_ass_path(path)


def _escape_drawtext(text: str) -> str:
    """Escape text for FFmpeg drawtext filter parameter values."""
    s = str(text or "")
    s = s.replace("\\", "\\\\")
    s = s.replace(":", "\\:")
    s = s.replace("'", r"\'")
    s = s.replace("%", "\\%")
    return s


def _with_ffgraph_temp_dir(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        tmp_dir = tempfile.mkdtemp(prefix="ffgraph_")
        try:
            kwargs["_ffgraph_temp_dir"] = tmp_dir
            return func(*args, **kwargs)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    return wrapped


def _cleanup_ffmpeg_process(proc, reader_thread=None):
    if proc is None:
        return
    subp = _fg_subprocess()
    try:
        still_running = proc.poll() is None
    except OSError as exc:
        print(f"  [FFmpegGraph] FFmpeg süreç temizliği uyarısı: {exc}", flush=True)
        still_running = True
    if still_running:
        try:
            proc.terminate()
        except OSError as exc:
            print(f"  [FFmpegGraph] FFmpeg terminate uyarısı: {exc}", flush=True)
    try:
        proc.wait(timeout=2.0)
    except subp.TimeoutExpired:
        try:
            proc.kill()
        except OSError as exc:
            print(f"  [FFmpegGraph] FFmpeg kill uyarısı: {exc}", flush=True)
        try:
            proc.wait(timeout=5.0)
        except subp.TimeoutExpired as exc:
            print(f"  [FFmpegGraph] FFmpeg süreç sonlandırılamadı: {exc}", flush=True)
        except OSError as exc:
            print(f"  [FFmpegGraph] FFmpeg wait uyarısı: {exc}", flush=True)
    except OSError as exc:
        print(f"  [FFmpegGraph] FFmpeg wait uyarısı: {exc}", flush=True)

    if reader_thread is not None:
        reader_thread.join(timeout=2.0)
    for stream in (getattr(proc, "stdout", None), getattr(proc, "stderr", None)):
        if stream is not None:
            try:
                stream.close()
            except OSError as exc:
                print(f"  [FFmpegGraph] FFmpeg pipe kapatılamadı: {exc}", flush=True)
    if reader_thread is not None and reader_thread.is_alive():
        reader_thread.join(timeout=1.0)


def _probe_has_audio(path: str) -> bool:
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        r = _fg_subprocess().run(
            [exe, "-i", path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=20,
        )
        return "Audio:" in (r.stderr or "")
    except Exception:
        return False


def _probe_audio_duration(ffmpeg: str, audio_path: str) -> float:
    """Return audio duration in seconds, or -1.0 when probing fails."""
    try:
        proc = _fg_subprocess().run(
            [ffmpeg, "-i", audio_path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, timeout=15,
        )
        raw = proc.stderr or b""
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
        m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", text)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return -1.0


def _probe_video_fps(path: str) -> float:
    """Probe nominal video stream FPS, returning 30.0 on fallback."""
    if not path or not _fg_os().path.exists(path):
        return 30.0
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        r = _fg_subprocess().run(
            [exe, "-i", path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=10,
        )
        m = re.search(r",\s*(\d+(?:\.\d+)?)\s*fps\b", r.stderr or "")
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return 30.0


def _probe_dimensions(path: str) -> Tuple[int, int]:
    """Return (width, height) of video/image or (0, 0) when unknown."""
    if not path or not _fg_os().path.exists(path):
        return (0, 0)
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        r = _fg_subprocess().run(
            [exe, "-i", path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=10,
        )
        m = re.search(r"Video:.*,\s*(\d{2,5})x(\d{2,5})", r.stderr or "")
        if m:
            return (int(m.group(1)), int(m.group(2)))
    except Exception:
        pass
    return (0, 0)


def _validate_clip_paths(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter clips with existing file paths."""
    os_mod = _fg_os()
    return [c for c in (clips or []) if c.get("path") and os_mod.path.exists(c["path"])]


def _resolve_clip_transition(clip: Dict[str, Any], index: int = 0) -> str:
    """Resolve clip transition style (default hard/cut or explicit wipe/crossfade)."""
    if not isinstance(clip, dict):
        return "cut"
    if clip.get("wipe_transition"):
        return str(clip.get("wipe_direction") or "wipeleft")
    return str(clip.get("transition") or ("cut" if index == 0 else "fade"))


def _build_encoder_candidates(use_gpu: bool, gpu_codec: str = "") -> list:
    from system_resilience import get_encoder_fallback_chain
    return get_encoder_fallback_chain(use_gpu, gpu_codec)


def align_even_dimension(value: int) -> int:
    """H.264 macroblocks require even width and height."""
    size = int(value)
    if size < 2:
        return 2
    return size - (size % 2)


def gameplay_start_seconds(clip_duration: float, need: float, scene_index: int = 0) -> float:
    """RedditVideoMakerBot / Chapter 28.16: Non-repetitive safe gameplay interval with history tracking."""
    try:
        from services.gameplay_background_manager import GLOBAL_BACKGROUND_MANAGER
        start, end, needs_loop = GLOBAL_BACKGROUND_MANAGER.get_safe_background_interval(
            video_length=clip_duration,
            target_clip_length=need,
        )
        return float(start)
    except Exception:
        room = float(clip_duration) - float(need) - 0.2
        if room < 0.5:
            return 0.0
        frac = ((int(scene_index) * 37) % 100) / 100.0
        return round(room * frac, 3)


VIDEO_DURATION_SAFETY_MARGIN: float = 0.1


def get_required_video_duration(
    audio_duration: float,
    safety_margin: float = VIDEO_DURATION_SAFETY_MARGIN,
) -> float:
    """
    MoneyPrinterTurbo pattern (P9):
    FFmpeg concat/transcode can round down frame counts by several dozen milliseconds.
    Adding a small safety margin (0.1s) avoids black frames, stutter, or muted endings.
    """
    return max(0.0, float(audio_duration) + float(safety_margin))


def _probe_duration(path: str) -> float:
    if not path or not _fg_os().path.exists(path):
        return 0.0
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        probe = _fg_subprocess().run(
            [exe, "-i", path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=10,
        )
        match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", probe.stderr or "")
        if not match:
            return 0.0
        return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))
    except Exception:
        return 0.0


def _probe_is_landscape(path: str) -> bool:
    """Master Plan Paket 2: True if video/image is horizontal/landscape (w > h)."""
    if not path or not _fg_os().path.exists(path):
        return False
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        r = _fg_subprocess().run(
            [exe, "-i", path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=10,
        )
        m = re.search(r"Video:.*,\s*(\d{2,5})x(\d{2,5})", r.stderr or "")
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            return w > h
    except Exception:
        pass
    return False


def face_cover_crop_x(path: str, out_w: int, out_h: int, duration: Optional[float] = None):
    """
    anil local/clipper.py:_reframe_vertical tracks the largest Haar face.
    Uses visuals.face_reframe with safe path resolution and stable sampling.
    Near-center faces stay on default center crop. Fit-and-fill does not call this.
    """
    if not path or not _fg_os().path.exists(path):
        return None
    try:
        if duration is not None:
            from visuals.face_reframe import detect_face_track, face_crop_expression
            return face_crop_expression(detect_face_track(path, duration=duration))
        from visuals.face_reframe import compute_face_crop_x
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            cap.release()
            return None
        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        cap.release()
        if src_w < 16 or src_h < 16:
            return None
        source_x = compute_face_crop_x(path, src_w, src_h, out_w, out_h)
        if source_x is None:
            return None
        scale = max(float(out_w) / float(src_w), float(out_h) / float(src_h))
        scaled_w = max(int(out_w), int(src_w * scale))
        scaled_h = max(int(out_h), int(src_h * scale))
        scaled_w -= scaled_w % 2
        scaled_h -= scaled_h % 2
        scaled_x = int(round(float(source_x) * scale))
        scaled_x = max(0, min(scaled_w - int(out_w), scaled_x))
        return scaled_x - (scaled_x % 2)
    except Exception:
        return None


_BT601_SPACE = {
    "bt470bg": "bt601-6-625",
    "smpte170m": "bt601-6-525",
    "bt601": "bt601-6-625",
    "smpte240m": "smpte240m",
}
_BT2020_SPACE = {"bt2020nc", "bt2020", "bt2020ncl"}
_HDR_TRANSFER = {"arib-std-b67", "smpte2084"}
_FULL_RANGE = {"pc", "jpeg", "full"}
_BT709_TAG = "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv"


def color_convert_filter(meta: Optional[Dict[str, Any]]) -> str:
    """
    A metadata flag alone leaves bt601 or full-range pixels labeled as bt709.
    HDR uses explicit zscale pin/tin/min. The hable chain fails here with
    "no path between colorspaces". Untagged HD stays unconverted.
    Two-pass video encode is not added.
    """
    meta = meta or {}
    space = str(meta.get("color_space") or "").lower()
    transfer = str(meta.get("color_transfer") or meta.get("color_trc") or "").lower()
    crange = str(meta.get("color_range") or "").lower()
    if transfer in _HDR_TRANSFER:
        matrix = "bt709" if space == "bt709" else "bt2020nc"
        return (
            f"zscale=pin=bt2020:tin={transfer}:min={matrix}:"
            "t=bt709:m=bt709:p=bt709:r=tv,format=yuv420p"
        )
    iall = _BT601_SPACE.get(space)
    if space in _BT2020_SPACE:
        iall = "bt2020"
    full = crange in _FULL_RANGE
    if not iall and not full:
        return ""
    filt = "colorspace=all=bt709:range=tv:fast=1"
    if iall:
        filt += f":iall={iall}"
    if full:
        filt += ":irange=pc"
    return filt


def probe_stream_color(path: str) -> Dict[str, str]:
    os_mod = _fg_os()
    if not path or not os_mod.path.exists(path):
        return {}
    probe = ""
    try:
        folder = os_mod.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        for name in ("ffprobe.exe", "ffprobe"):
            cand = os_mod.path.join(folder, name)
            if os_mod.path.isfile(cand):
                probe = cand
                break
    except Exception:
        probe = ""
    if not probe:
        probe = shutil.which("ffprobe") or ""
    if not probe:
        return {}
    try:
        proc = _fg_subprocess().run(
            [
                probe, "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=color_space,color_transfer,color_primaries,color_range",
                "-of", "json", path,
            ],
            capture_output=True, text=True, timeout=8,
        )
        if proc.returncode != 0:
            return {}
        stream = (json.loads(proc.stdout or "{}").get("streams") or [{}])[0]
    except Exception:
        return {}
    return {
        "color_space": str(stream.get("color_space") or ""),
        "color_transfer": str(stream.get("color_transfer") or ""),
        "color_primaries": str(stream.get("color_primaries") or ""),
        "color_range": str(stream.get("color_range") or ""),
    }
