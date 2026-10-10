"""
Native FFmpeg filter_complex render graph (Item 418).
Concat demuxer + scale/crop/fps + ASS + color/grain/vignette + audio → single encode.
MoviePy remains available as capability fallback via video_composer.compose_video.
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import imageio_ffmpeg

import config


def _escape_ass_path(path: str) -> str:
    # FFmpeg subtitles filter on Windows needs escaped drive and slashes
    p = os.path.abspath(path).replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        p = p[0] + "\\:" + p[2:]
    return p.replace("'", r"\'")


def _probe_has_audio(path: str) -> bool:
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        r = subprocess.run(
            [exe, "-i", path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=20,
        )
        return "Audio:" in (r.stderr or "")
    except Exception:
        return False


def _probe_audio_duration(ffmpeg: str, audio_path: str) -> float:
    """Return audio duration in seconds, or -1.0 when probing fails."""
    try:
        proc = subprocess.run(
            [ffmpeg, "-i", audio_path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, timeout=15,
        )
        text = (proc.stderr or b"").decode("utf-8", errors="replace")
        m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", text)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return -1.0


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
    if not path or not os.path.exists(path):
        return 0.0
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        probe = subprocess.run(
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
    if not path or not os.path.exists(path):
        return False
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        r = subprocess.run(
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
    if not path or not os.path.exists(path):
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
        # `build_scene_filter_chain` and `vertical_vf` scale first, then crop.
        # The detector returns source pixels, so translate the offset into the
        # post-scale coordinate system before writing the FFmpeg crop expression.
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


def _plan_cutaways(
    clips: List[Dict[str, Any]],
    total_dur: float,
    word_timings: Optional[List[Dict[str, Any]]],
) -> List[Tuple[str, float, float]]:
    """
    ai-content-studio overlays with enable=between, one new encode per cue.
    This keeps the window and drops the extra encode. Cue length is 2.0-3.2s.
    Non-overlapping overlays, maximum 3.
    """
    candidates: List[Tuple[str, float, float]] = []
    hook_guard = 1.8
    tail_guard = 1.0
    for clip in clips:
        for item in clip.get("broll_inserts") or []:
            path = item.get("path")
            if not path or not os.path.exists(path):
                continue
            raw_start = max(0.0, float(item.get("start") or 0.0))
            raw_end = float(item.get("end") or (raw_start + 2.5))
            dur = max(2.0, min(3.2, raw_end - raw_start))
            start = max(hook_guard, raw_start)
            end = min(total_dur - tail_guard, start + dur)
            if end - start < 2.0 and total_dur >= hook_guard + 2.0 + tail_guard:
                end = total_dur - tail_guard
                start = max(hook_guard, end - dur)
            if end - start >= 2.0:
                candidates.append((path, start, end))

    if not candidates and not getattr(config, "RENDER_SAFE_MODE", False) and len(clips) >= 3 and total_dur >= 10.0:
        narration = " ".join(str(w.get("text") or "") for w in (word_timings or []))
        try:
            from services.dynamic_broll_director import dynamic_broll_director
            cues = dynamic_broll_director.plan_retention_broll(total_dur, narration)[:3]
        except Exception:
            cues = []
        starts: List[float] = []
        cursor = 0.0
        for clip in clips:
            starts.append(cursor)
            cursor += float(clip.get("duration") or 3.0)
        for cue in cues:
            raw_start = float(cue.start_offset)
            dur = max(2.0, min(3.2, float(cue.end_offset) - raw_start))
            start = max(hook_guard, raw_start)
            end = min(total_dur - tail_guard, start + dur)
            if end - start < 2.0:
                continue
            donor = None
            for idx, clip in enumerate(clips):
                scene_end = starts[idx] + float(clip.get("duration") or 3.0)
                if end <= starts[idx] or start >= scene_end:
                    donor = clip.get("path")
                    break
            if donor and os.path.exists(donor):
                candidates.append((donor, start, end))

    # Sort and enforce non-overlapping constraint, max 3
    candidates.sort(key=lambda x: x[1])
    selected: List[Tuple[str, float, float]] = []
    last_end = hook_guard
    for path, start, end in candidates:
        if start < last_end:
            # Overlap detected: try shifting if room allows
            if last_end + 0.2 + 2.0 <= total_dur - tail_guard:
                original_dur = end - start
                start = last_end + 0.2
                end = min(total_dur - tail_guard, start + original_dur)
                if end - start < 2.0:
                    continue
            else:
                continue
        if end - start >= 2.0 and len(selected) < 3:
            selected.append((path, round(start, 2), round(end, 2)))
            last_end = end
    return selected



def resolve_camera_intent(
    scene_intent: Optional[str] = None,
    camera_direction: Optional[str] = None,
    scene_index: int = 0,
    total_scenes: int = 1,
    narration: Optional[str] = None,
) -> str:
    """
    Bölüm 33.3 P4 (youtube-shorts-pipeline verticals/broll.py 3-kamera niyet modeli):
    Sahne niyetine göre 3 temel kamera hareketinden birini belirler:
    - Soru / Hook / Curiosity / Establishing -> 'zoom_in' (z='1+0.12*ease')
    - Geçiş / Transition / Action / Body / Conflict -> 'pan_right' (z='1.12', x over time)
    - Kapanış / Conclusion / Outro / CTA / Climax / Resolution -> 'zoom_out' (z='1+0.12*ease_back')

    Açık kamera yönü ('pan_left', 'tilt_down', vb.) belirtilmişse öncelikli olarak korunur.
    """
    cam = (camera_direction or "").lower().strip()
    if cam in (
        "zoom_in", "zoom_out", "pan_right", "pan_left",
        "tilt_down", "tilt_up", "static", "push_in", "pull_out"
    ):
        return cam

    intent = (scene_intent or "").lower().strip()

    # 1. Soru / Merak / Kanca niyetleri -> zoom_in
    if intent in (
        "question", "soru", "hook", "curiosity", "establishing",
        "closeup", "soru_zoom_in", "shock", "quiz"
    ):
        return "zoom_in"

    # 2. Geçiş / Gövde / Aksiyon niyetleri -> pan_right
    if intent in (
        "transition", "gecis", "geçiş", "action", "body",
        "conflict", "bridge", "gecis_pan"
    ):
        return "pan_right"

    # 3. Kapanış / Çözüm / Outro niyetleri -> zoom_out
    if intent in (
        "conclusion", "kapanis", "kapanış", "outro", "cta",
        "climax", "resolution", "kapanis_zoom_out", "final"
    ):
        return "zoom_out"

    # 4. Anlatı metninde soru işareti veya soru kancası analizi
    narr = (narration or "").lower().strip()
    if "?" in narr or any(narr.startswith(w) for w in (
        "neden", "nasıl", "kim", "hiç", "biliyor musun", "fark ettin mi",
        "why", "how", "did you know", "what if"
    )):
        return "zoom_in"

    # 5. Sahne pozisyonu ve ardışık döngü (3-kamera rotasyonu)
    if total_scenes > 2 and scene_index == total_scenes - 1:
        return "zoom_out"

    cycle = ["zoom_in", "pan_right", "zoom_out"]
    return cycle[int(scene_index) % 3]


def cheap_pan_filter(
    width: int,
    height: int,
    duration: float,
    scene_index: int = 0,
    camera_direction: Optional[str] = None,
    scene_intent: Optional[str] = None,
    total_scenes: Optional[int] = None,
    narration: Optional[str] = None,
) -> str:
    """
    Smooth cosine ease-in-out push via overscale + moving crop (Madde 418 / Master Plan Paket 4 / Bölüm 7.6).
    Replaces linear zoompan with smooth cinematic acceleration and deceleration curves.
    Supports camera_direction: 'pan_right', 'pan_left', 'tilt_down', 'tilt_up', 'zoom_in', 'zoom_out', 'static'
    veya Bölüm 33.3 P4 sahne niyeti (Soru zoom_in, Geçiş pan_right, Kapanış zoom_out).
    """
    dur = max(float(duration), 0.1)
    sw = max(width + 2, (int(width * 1.08) // 2) * 2)
    sh = max(height + 2, (int(height * 1.08) // 2) * 2)

    prog = f"0.5*(1-cos(PI*min(t\\,{dur:.3f})/{dur:.3f}))"
    prog_rev = f"0.5*(1+cos(PI*min(t\\,{dur:.3f})/{dur:.3f}))"

    cam = resolve_camera_intent(
        scene_intent=scene_intent,
        camera_direction=camera_direction,
        scene_index=scene_index,
        total_scenes=total_scenes or 1,
        narration=narration or "",
    )
    if cam == "pan_right":
        xexpr = f"(in_w-out_w)*{prog}"
        yexpr = "(in_h-out_h)/2"
    elif cam == "pan_left":
        xexpr = f"(in_w-out_w)*{prog_rev}"
        yexpr = "(in_h-out_h)/2"
    elif cam == "tilt_down":
        xexpr = "(in_w-out_w)/2"
        yexpr = f"(in_h-out_h)*{prog}"
    elif cam == "tilt_up":
        xexpr = "(in_w-out_w)/2"
        yexpr = f"(in_h-out_h)*{prog_rev}"
    elif cam == "static":
        xexpr = "(in_w-out_w)/2"
        yexpr = "(in_h-out_h)/2"
    elif cam in ("zoom_in", "push_in"):
        xexpr = f"(in_w-out_w)*0.5*{prog}"
        yexpr = f"(in_h-out_h)*0.5*{prog}"
    elif cam in ("zoom_out", "pull_out"):
        xexpr = f"(in_w-out_w)*0.5*{prog_rev}"
        yexpr = f"(in_h-out_h)*0.5*{prog_rev}"
    else:
        direction = int(scene_index) % 4
        if direction == 0:
            xexpr = f"(in_w-out_w)*{prog}"
            yexpr = "(in_h-out_h)/2"
        elif direction == 1:
            xexpr = f"(in_w-out_w)*{prog_rev}"
            yexpr = "(in_h-out_h)/2"
        elif direction == 2:
            xexpr = "(in_w-out_w)/2"
            yexpr = f"(in_h-out_h)*{prog}"
        else:
            xexpr = "(in_w-out_w)/2"
            yexpr = f"(in_h-out_h)*{prog_rev}"

    return f"scale={sw}:{sh},crop={width}:{height}:x='{xexpr}':y='{yexpr}'"


def zoompan_filter(
    width: int,
    height: int,
    duration: float,
    scene_index: int = 0,
    camera_direction: Optional[str] = None,
    output_fps: Optional[float] = None,
    scene_intent: Optional[str] = None,
    total_scenes: Optional[int] = None,
    narration: Optional[str] = None,
) -> str:
    """
    Opt-in Ken Burns (Bölüm 33.3 P4 / youtube-shorts-pipeline:animate_frame).
    Sahne niyetine göre 3 kamera:
      - Soru -> zoom_in (z='1+0.12*ease', iw/2-iw/zoom/2)
      - Geçiş -> pan_right (z='1.12', x pans across)
      - Kapanış -> zoom_out (z='1+0.12*ease_back', iw/2-iw/zoom/2)
    Kosinüs rampası jerk'i önler.
    """
    fps = float(output_fps) if output_fps else float(getattr(config, "FPS", 30) or 30)
    frames = max(1, int(max(float(duration), 0.1) * fps))
    ease = f"0.5*(1-cos(PI*on/{frames}))"
    ease_back = f"0.5*(1+cos(PI*on/{frames}))"

    cam = resolve_camera_intent(
        scene_intent=scene_intent,
        camera_direction=camera_direction,
        scene_index=scene_index,
        total_scenes=total_scenes or 1,
        narration=narration or "",
    )
    if cam in ("zoom_in", "push_in"):
        z_expr = f"1+0.12*{ease}"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif cam in ("zoom_out", "pull_out"):
        z_expr = f"1+0.12*{ease_back}"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif cam in ("pan_right", "pan"):
        z_expr = "1.12"
        x_expr = f"(iw-iw/zoom)*{ease}"
        y_expr = "(ih-ih/zoom)/2"
    elif cam == "pan_left":
        z_expr = "1.12"
        x_expr = f"(iw-iw/zoom)*{ease_back}"
        y_expr = "(ih-ih/zoom)/2"
    elif cam == "tilt_down":
        z_expr = "1.12"
        x_expr = "(iw-iw/zoom)/2"
        y_expr = f"(ih-ih/zoom)*{ease}"
    elif cam == "tilt_up":
        z_expr = "1.12"
        x_expr = "(iw-iw/zoom)/2"
        y_expr = f"(ih-ih/zoom)*{ease_back}"
    elif cam == "static":
        z_expr = "1.0"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        kind = int(scene_index) % 3
        if kind == 1:
            z_expr = "1.12"
            x_expr = f"(iw-iw/zoom)*{ease}"
            y_expr = "(ih-ih/zoom)/2"
        elif kind == 2:
            z_expr = f"1+0.12*{ease_back}"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        else:
            z_expr = f"1+0.12*{ease}"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"

    return (
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={frames}:s={width}x{height}:fps={fps:.2f}"
    )


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
    if not path or not os.path.exists(path):
        return {}
    probe = ""
    try:
        import imageio_ffmpeg
        folder = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        for name in ("ffprobe.exe", "ffprobe"):
            cand = os.path.join(folder, name)
            if os.path.isfile(cand):
                probe = cand
                break
    except Exception:
        probe = ""
    if not probe:
        probe = shutil.which("ffprobe") or ""
    if not probe:
        return {}
    try:
        proc = subprocess.run(
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


def build_scene_filter_chain(
    input_index: int,
    duration: float,
    width: int,
    height: int,
    scene_index: int,
    enable_ken_burns: bool = True,
    enable_zoompan: bool = False,
    split_screen: bool = False,
    gameplay_index: Optional[int] = None,
    gameplay_label: Optional[str] = None,
    fit_and_fill: bool = False,
    gameplay_start: float = 0.0,
    crop_x: Optional[int] = None,
    tail_crop_x=None,
    tail_fit_and_fill: Optional[bool] = None,
    pad_seconds: float = 0.0,
    tail_input_index: Optional[int] = None,
    head_seconds: Optional[float] = None,
    color_filter: str = "",
    tail_color_filter: str = "",
    gameplay_color_filter: str = "",
    camera_direction: Optional[str] = None,
    output_fps: Optional[float] = None,
    scene_intent: Optional[str] = None,
    total_scenes: Optional[int] = None,
    narration: Optional[str] = None,
) -> str:
    """
    Per-input video chain: trim, fps, scale/crop cover, optional crop-pan.
    Split: top 58% scene, bottom 42% looped gameplay (soap / satisfying).
    Fit & Fill: Blurred background + centered aspect-ratio preserved foreground (Paket 2).
    """
    width = align_even_dimension(width)
    height = align_even_dimension(height)
    split = bool(split_screen and (gameplay_label or gameplay_index is not None))
    out_h = align_even_dimension(int(height * 0.58)) if split else height
    fps = float(output_fps) if output_fps else float(getattr(config, "FPS", 30) or 30)
    fps_token = f"{fps:.2f}".rstrip("0").rstrip(".")

    def _lead(label: str, extra: str) -> str:
        extra = (extra or "").strip().strip(",")
        if not extra:
            return label
        return f"{label}{extra},"
    pad = ""
    if pad_seconds and float(pad_seconds) > 0.12:
        pad = f"tpad=stop_mode=clone:stop_duration={float(pad_seconds):.3f},"
    cover_crop = f"crop={width}:{out_h}"
    if crop_x is not None and not fit_and_fill:
        offset = f"'{crop_x}'" if isinstance(crop_x, str) else str(max(0, int(crop_x)))
        cover_crop += f":x={offset}"

    if tail_input_index is not None and head_seconds is not None and not split:
        head_len = max(0.2, min(float(head_seconds), float(duration) - 0.2))
        tail_len = max(0.2, float(duration) - head_len)

        def _piece(src_index: int, seg_dur: float, seg_pad: float, suffix: str) -> str:
            pad_f = ""
            if seg_pad and float(seg_pad) > 0.12:
                pad_f = f"tpad=stop_mode=clone:stop_duration={float(seg_pad):.3f},"
            tag = f"seg{scene_index}{suffix}"
            src = _lead(f"[{src_index}:v]", color_filter if suffix == "a" else tail_color_filter)
            piece_fit = fit_and_fill if suffix == "a" or tail_fit_and_fill is None else tail_fit_and_fill
            piece_crop = cover_crop if suffix == "a" else f"crop={width}:{out_h}"
            if suffix == "b" and tail_crop_x is not None:
                offset = f"'{tail_crop_x}'" if isinstance(tail_crop_x, str) else str(max(0, int(tail_crop_x)))
                piece_crop += f":x={offset}"
            if piece_fit:
                return (
                    f"{src}trim=duration={seg_dur:.3f},{pad_f}setpts=PTS-STARTPTS,"
                    f"fps={fps_token},split[fg_raw_{scene_index}{suffix}][bg_raw_{scene_index}{suffix}];"
                    f"[bg_raw_{scene_index}{suffix}]scale={width}:{out_h}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{out_h},boxblur=25:5[bg_blur_{scene_index}{suffix}];"
                    f"[fg_raw_{scene_index}{suffix}]scale={width}:{out_h}:force_original_aspect_ratio=decrease"
                    f"[fg_fit_{scene_index}{suffix}];"
                    f"[bg_blur_{scene_index}{suffix}][fg_fit_{scene_index}{suffix}]overlay=(W-w)/2:(H-h)/2,"
                    f"setsar=1[{tag}]"
                )
            return (
                f"{src}trim=duration={seg_dur:.3f},{pad_f}setpts=PTS-STARTPTS,"
                f"fps={fps_token},scale={width}:{out_h}:force_original_aspect_ratio=increase,"
                f"{piece_crop},setsar=1[{tag}]"
            )

        head = _piece(input_index, head_len, 0.0, "a")
        tail = _piece(int(tail_input_index), tail_len, float(pad_seconds or 0.0), "b")
        motion = ""
        if enable_zoompan:
            motion = "," + zoompan_filter(
                width, out_h, duration, scene_index,
                camera_direction=camera_direction,
                output_fps=fps,
                scene_intent=scene_intent,
                total_scenes=total_scenes,
                narration=narration,
            )
        elif enable_ken_burns:
            motion = "," + cheap_pan_filter(
                width, out_h, duration, scene_index,
                camera_direction=camera_direction,
                scene_intent=scene_intent,
                total_scenes=total_scenes,
                narration=narration,
            )
        bright = ""
        try:
            from effects.filters import get_scene_brightness_alternation_filter
            bright = "," + get_scene_brightness_alternation_filter(scene_index)
        except Exception:
            pass
        joined = (
            f"{head};{tail};"
            f"[seg{scene_index}a][seg{scene_index}b]concat=n=2:v=1:a=0"
            f"[cat{scene_index}]"
        )
        return joined + f";[cat{scene_index}]null{bright}{motion},setsar=1[v{scene_index}]"

    if fit_and_fill:
        base = (
            f"{_lead(f'[{input_index}:v]', color_filter)}"
            f"trim=duration={duration:.3f},{pad}setpts=PTS-STARTPTS,"
            f"fps={fps_token},"
            f"split[fg_raw_{scene_index}][bg_raw_{scene_index}];"
            f"[bg_raw_{scene_index}]scale={width}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={width}:{out_h},boxblur=25:5[bg_blur_{scene_index}];"
            f"[fg_raw_{scene_index}]scale={width}:{out_h}:force_original_aspect_ratio=decrease[fg_fit_{scene_index}];"
            f"[bg_blur_{scene_index}][fg_fit_{scene_index}]overlay=(W-w)/2:(H-h)/2,"
            f"setsar=1"
        )
    else:
        # Cover crop to 9:16 (or the top panel when split)
        base = (
            f"{_lead(f'[{input_index}:v]', color_filter)}"
            f"trim=duration={duration:.3f},{pad}setpts=PTS-STARTPTS,"
            f"fps={fps_token},"
            f"scale={width}:{out_h}:force_original_aspect_ratio=increase,"
            f"{cover_crop},"
            f"setsar=1"
        )
    try:
        from effects.filters import get_scene_brightness_alternation_filter
        base += f",{get_scene_brightness_alternation_filter(scene_index)}"
    except Exception:
        pass
    if enable_zoompan:
        base += "," + zoompan_filter(
            width, out_h, duration, scene_index,
            camera_direction=camera_direction,
            output_fps=fps,
            scene_intent=scene_intent,
            total_scenes=total_scenes,
            narration=narration,
        )
    elif enable_ken_burns:
        base += "," + cheap_pan_filter(
            width, out_h, duration, scene_index,
            camera_direction=camera_direction,
            scene_intent=scene_intent,
            total_scenes=total_scenes,
            narration=narration,
        )
    if not split:
        base += f",setsar=1[v{scene_index}]"
        return base
    bot_h = align_even_dimension(int(height - out_h))
    base += f"[top{scene_index}]"
    gp_src = gameplay_label or f"[{gameplay_index}:v]"
    start = max(0.0, float(gameplay_start or 0.0))
    gameplay = (
        f"{_lead(gp_src, gameplay_color_filter)}trim=start={start:.3f}:duration={duration:.3f},setpts=PTS-STARTPTS,"
        f"fps={fps_token},"
        f"scale={width}:{bot_h}:force_original_aspect_ratio=increase,"
        f"crop={width}:{bot_h},"
        f"drawbox=y=0:h=3:color=0xFFD700@0.95:t=fill,"
        f"setsar=1[bot{scene_index}]"
    )
    stack = f"[top{scene_index}][bot{scene_index}]vstack=inputs=2,setsar=1[v{scene_index}]"
    return base + ";" + gameplay + ";" + stack


def get_look_filters(width: int, height: int, anti_duplicate: bool = True) -> str:
    """Color jitter with independent RGB gamma channels, unsharp, temporal noise, vignette (Items 72, 84, 86, 92, Chapter 8.2)."""
    from compliance.anti_repetition import get_rgb_color_jitter_filter, get_temporal_noise_filter
    parts = [
        get_rgb_color_jitter_filter(jitter_range=0.015),
        "unsharp=5:5:0.8:5:5:0.0",
    ]
    if anti_duplicate:
        parts.append(get_temporal_noise_filter(strength=3, flag="t"))
    # Soft vignette
    parts.append("vignette=PI/5")
    return ",".join(parts)


def render_with_ffmpeg_graph(
    clips: List[Dict[str, Any]],
    audio_path: str,
    output_path: str,
    *,
    word_timings: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    subtitle_opts: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable] = None,
    cancel_check: Optional[Callable] = None,
    anti_duplicate: bool = True,
    enable_ken_burns: bool = True,
    enable_zoompan: bool = False,
    enable_broll: bool = False,
    enable_face_center: bool = False,
    ass_path: Optional[str] = None,
    emphasis_ass_path: Optional[str] = None,
    enable_emphasis_card: bool = False,
    gameplay_path: Optional[str] = None,
    hybrid_render_overlay: Optional[Dict[str, Any]] = None,
    enable_audio_visualizer: bool = False,
    audio_visualizer_mode: str = "line",
    audio_visualizer_color: str = "0x00D7FF",
    enable_news_ticker: bool = False,
    news_ticker_text: Optional[str] = None,
    niche_id: str = "",
    enable_reddit_card: bool = False,
    reddit_card_path: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Item 418: Single filter_complex concat + look + optional ASS + audio mux + NVENC/libx264.
    Returns output_path on success, empty string on failure (caller may fallback to MoviePy).
    """
    valid = [c for c in clips if c.get("path") and os.path.exists(c["path"])]
    if not valid or not audio_path or not os.path.exists(audio_path):
        return ""
    # P0-03: never repeat one stock clip when fetch partially failed
    if len(valid) < len(clips):
        print(
            f"  [FFmpegGraph] ABORT: {len(valid)}/{len(clips)} clips valid "
            f"-- partial fetch would repeat one visual",
            flush=True,
        )
        return ""

    W, H = getattr(config, "get_target_resolution", lambda: (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))()
    W = align_even_dimension(int(W))
    H = align_even_dimension(int(H))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_dir = tempfile.mkdtemp(prefix="ffgraph_")
    concat_list = os.path.join(tmp_dir, "concat.txt")

    # Generate ASS if needed
    if not ass_path and word_timings:
        try:
            from subtitle_generator import create_karaoke_subtitles
            ass_path = os.path.join(tmp_dir, "subs.ass")
            sub_opts = dict(subtitle_opts or {})
            if "audio_path" not in sub_opts and audio_path:
                sub_opts["audio_path"] = audio_path
            create_karaoke_subtitles(
                word_timings, ass_path, style_opts=sub_opts,
            )
        except Exception as e:
            print(f"  [FFmpegGraph] ASS notice: {e}")
            ass_path = None

    if progress_callback:
        progress_callback(76, "[FFmpegGraph] Filter complex derleniyor (Madde 418)...")

    if getattr(config, "FPS_DIVERSIFY", True):
        from compliance.anti_repetition import get_diversified_fps
        output_fps = get_diversified_fps()
    else:
        output_fps = float(getattr(config, "FPS", 30) or 30)

    # Build inputs
    from system_resilience import get_ffmpeg_loglevel
    cmd: List[str] = [ffmpeg, "-y", "-hide_banner", "-loglevel", get_ffmpeg_loglevel()]
    filter_parts: List[str] = []
    gp_ok = bool(gameplay_path and os.path.exists(gameplay_path))
    gp_dur = _probe_duration(gameplay_path) if gp_ok else 0.0
    n = len(valid)
    cursor = 0
    for i, clip in enumerate(valid):
        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
        dur = float(clip.get("duration", 3.0))
        media_dur = _probe_duration(clip.get("path"))
        pad_seconds = 0.0
        tail_index = None
        head_seconds = None
        tail_path = "" if gp_ok else (clip.get("tail_path") or "")
        use_tail = (
            bool(tail_path)
            and os.path.exists(tail_path)
            and media_dur > 0.2
            and dur - media_dur > 0.12
        )
        if use_tail:
            cmd.extend(["-i", clip["path"]])
            head_index = cursor
            cursor += 1
            cmd.extend(["-i", tail_path])
            tail_index = cursor
            cursor += 1
            head_seconds = min(media_dur, max(0.2, dur - 0.2))
            tail_need = max(0.2, dur - head_seconds)
            tail_media = _probe_duration(tail_path)
            if tail_media > 0.2 and tail_need - tail_media > 0.12:
                pad_seconds = tail_need - tail_media
        elif media_dur > 0.2 and dur - media_dur > 0.12:
            # Seamless loop instead of frozen frame cloning
            cmd.extend(["-stream_loop", "-1", "-i", clip["path"]])
            head_index = cursor
            cursor += 1
            pad_seconds = 0.0
        else:
            cmd.extend(["-i", clip["path"]])
            head_index = cursor
            cursor += 1
        panel_h = align_even_dimension(int(H * 0.58)) if gp_ok else H
        crop_x = clip.get("crop_x")
        is_landscape = _probe_is_landscape(clip.get("path"))

        if enable_face_center and is_landscape:
            if crop_x is None:
                crop_x = face_cover_crop_x(clip.get("path"), W, panel_h, duration=dur)
            if crop_x is not None:
                # Face detected: reframe vertically around subject instead of fit-fill
                use_fit_fill = False
            elif clip.get("fit_and_fill") is not None:
                use_fit_fill = bool(clip.get("fit_and_fill"))
            else:
                use_fit_fill = True
        else:
            use_fit_fill = clip.get("fit_and_fill")
            if use_fit_fill is None:
                use_fit_fill = is_landscape
            else:
                use_fit_fill = bool(use_fit_fill)
        tail_crop_x = None
        tail_fit_fill = None
        if use_tail:
            tail_fit_fill = _probe_is_landscape(tail_path)
            if enable_face_center and tail_fit_fill:
                tail_crop_x = face_cover_crop_x(tail_path, W, panel_h, duration=tail_need)
                if tail_crop_x is not None:
                    tail_fit_fill = False
        tracking = enable_face_center and (crop_x is not None or tail_crop_x is not None)
        gp_label = None
        if gp_ok:
            gp_label = f"[{cursor}:v]" if n == 1 else f"[gp{i}]"
        filter_parts.append(
            build_scene_filter_chain(
                head_index, dur, W, H, i,
                enable_ken_burns=enable_ken_burns and not tracking,
                enable_zoompan=enable_zoompan and not tracking,
                split_screen=gp_ok,
                gameplay_index=cursor if gp_ok and n == 1 else None,
                gameplay_label=gp_label,
                fit_and_fill=use_fit_fill,
                gameplay_start=gameplay_start_seconds(gp_dur, dur, i) if gp_ok else 0.0,
                crop_x=crop_x,
                tail_crop_x=tail_crop_x,
                tail_fit_and_fill=tail_fit_fill,
                pad_seconds=pad_seconds,
                tail_input_index=tail_index,
                head_seconds=head_seconds,
                color_filter=color_convert_filter(probe_stream_color(clip.get("path") or "")),
                tail_color_filter=color_convert_filter(probe_stream_color(tail_path)) if use_tail else "",
                gameplay_color_filter=color_convert_filter(probe_stream_color(gameplay_path or "")) if gp_ok else "",
                camera_direction=(
                    clip.get("camera_direction")
                    or ((clip.get("visual_intent") or {}).get("camera_direction") if isinstance(clip.get("visual_intent"), dict) else "")
                    or ""
                ),
                output_fps=output_fps,
                scene_intent=(
                    clip.get("scene_intent")
                    or clip.get("intent")
                    or clip.get("beat_type")
                    or ((clip.get("visual_intent") or {}).get("shot_type") if isinstance(clip.get("visual_intent"), dict) else "")
                    or ""
                ),
                total_scenes=n,
                narration=clip.get("narration") or "",
            )
        )

    gp_index = cursor
    if gp_ok:
        cmd.extend(["-stream_loop", "-1", "-i", gameplay_path])
        cursor += 1
        print(f"  [FFmpegGraph] Split-screen alt panel: {os.path.basename(gameplay_path)}", flush=True)
        if n > 1:
            arms = "".join(f"[gp{i}]" for i in range(n))
            filter_parts.insert(0, f"[{gp_index}:v]split={n}{arms}")
    concat_in = "".join(f"[v{i}]" for i in range(n))
    filter_parts.append(f"{concat_in}concat=n={n}:v=1:a=0[vcat]")

    look = get_look_filters(W, H, anti_duplicate=anti_duplicate)
    total_dur = max(0.1, sum(float(c.get("duration", 3.0)) for c in valid))
    prog = (
        f"drawbox=x=0:y=ih-6:w='iw*min(1\\,t/{total_dur:.3f})':"
        f"h=6:color=0x00E5FF@0.9:t=fill"
    )
    mid = f"[vcat]{look},{prog}[vlook]"
    filter_parts.append(mid)
    picture = "vlook"
    next_input = cursor
    if enable_broll and not getattr(config, "RENDER_SAFE_MODE", False):
        cutaways = _plan_cutaways(valid, total_dur, word_timings)[:3]
        for bi, (bpath, bstart, bend) in enumerate(cutaways):
            cmd.extend(["-i", bpath])
            dest = f"vcut{bi}"
            filter_parts.append(
                f"[{next_input}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H}[broll{bi}];"
                f"[{picture}][broll{bi}]overlay=0:0:"
                f"enable='between(t,{bstart:.2f},{bend:.2f})'[{dest}]"
            )
            picture = dest
            next_input += 1

    hook_path = ""
    hook_opts = subtitle_opts or {}
    hook_text = hook_opts.get("hook_card_text", title) or ""
    if hook_text and not hook_opts.get("disable_hook_card"):
        try:
            from effects.hook_card import create_hook_image
            hook_path = create_hook_image(hook_text, W, os.path.join(tmp_dir, "hook.png")) or ""
        except Exception as hook_err:
            print(f"  [FFmpegGraph] hook card notice: {hook_err}")
            hook_path = ""
    if hook_path and os.path.exists(hook_path):
        cmd.extend(["-loop", "1", "-t", "2.5", "-i", hook_path])
        hook_input = next_input
        next_input += 1

    # Dynamic audio visualizer overlay (short-video-maker / Chapter 28.8)
    should_visualize = bool(enable_audio_visualizer)
    if not should_visualize and niche_id:
        try:
            from effects.audio_visualizer import is_visualizer_recommended_for_niche
            should_visualize = is_visualizer_recommended_for_niche(niche_id)
        except Exception:
            should_visualize = False

    audio_idx = None
    if should_visualize and os.path.exists(audio_path):
        audio_idx = next_input
        cmd.extend(["-i", audio_path])
        next_input += 1
        try:
            from effects.audio_visualizer import build_waveform_filter
            wave_flt, wave_tag = build_waveform_filter(
                audio_tag=f"{audio_idx}:a",
                video_tag=picture,
                out_tag="vwave",
                width=W,
                height=140,
                y_pos=int(H * 0.72),
                mode=audio_visualizer_mode or "line",
                color=audio_visualizer_color or "0x00D7FF",
                opacity=0.80,
            )
            filter_parts.append(wave_flt)
            picture = wave_tag
        except Exception as wave_err:
            print(f"  [FFmpegGraph] audio visualizer notice: {wave_err}", flush=True)

    if ass_path and os.path.exists(ass_path):
        esc = _escape_ass_path(ass_path)
        filter_parts.append(
            f"[{picture}]subtitles='{esc}'[vsub]"
        )
        picture = "vsub"

    # Plan Item P6: Secondary emphasis layer for numbers & power keywords
    if enable_emphasis_card and emphasis_ass_path and os.path.exists(emphasis_ass_path):
        esc_emp = _escape_ass_path(emphasis_ass_path)
        filter_parts.append(
            f"[{picture}]subtitles='{esc_emp}'[vemp]"
        )
        picture = "vemp"

    if hook_path and os.path.exists(hook_path):
        from effects.hook_card import hook_overlay_filter
        filter_parts.append(f"[{hook_input}:v]format=rgba[hook]")
        filter_parts.append(hook_overlay_filter(picture, "hook", "vhook", H))
        picture = "vhook"

    # Master Plan Chapter 1.1 & 1.2: Native FFmpeg single-pass hybrid UI overlay
    hybrid_spec = hybrid_render_overlay
    hybrid_info = None
    if hybrid_spec and isinstance(hybrid_spec, dict):
        try:
            from effects.hybrid_overlay import create_hybrid_ui_overlay_png
            hybrid_info = create_hybrid_ui_overlay_png(
                hybrid_spec,
                width=W,
                height=H,
                total_duration=total_dur,
                out_path=os.path.join(tmp_dir, "hybrid_ui.png"),
            )
        except Exception as hy_err:
            print(f"  [FFmpegGraph] hybrid UI overlay notice: {hy_err}", flush=True)
            hybrid_info = None

    if hybrid_info and os.path.exists(hybrid_info["png_path"]):
        h_dur = hybrid_info["duration"]
        cmd.extend(["-loop", "1", "-t", f"{h_dur:.2f}", "-i", hybrid_info["png_path"]])
        hybrid_input = next_input
        next_input += 1
        filter_parts.append(f"[{hybrid_input}:v]format=rgba[hy_rgba]")
        x_expr = hybrid_info["x_expr"]
        y_expr = hybrid_info["y_expr"]
        enable_expr = hybrid_info["enable_expr"]
        filter_parts.append(
            f"[{picture}][hy_rgba]overlay=x={x_expr}:y={y_expr}:"
            f"enable='{enable_expr}':eof_action=pass:repeatlast=0[vhybrid]"
        )
    # Chapter 28.10 / youtube-shorts-pipeline: Broadcast-grade breaking news lower-third ticker
    should_ticker = bool(enable_news_ticker)
    if not should_ticker and niche_id:
        try:
            from effects.ticker import is_ticker_enabled_for_niche
            should_ticker = is_ticker_enabled_for_niche(niche_id)
        except Exception:
            should_ticker = False

    ticker_png = None
    if should_ticker:
        try:
            from effects.ticker import generate_news_ticker_image
            t_text = news_ticker_text or title or "SON DAKİKA GELİŞMESİ"
            ticker_png = os.path.join(tmp_dir, "news_ticker.png")
            generate_news_ticker_image(
                headline=t_text,
                output_path=ticker_png,
                width=W,
                height=130,
            )
            if os.path.exists(ticker_png):
                cmd.extend(["-loop", "1", "-t", f"{total_dur:.3f}", "-i", ticker_png])
                ticker_input = next_input
                next_input += 1
                filter_parts.append(f"[{ticker_input}:v]format=rgba[ticker_rgba]")
                filter_parts.append(
                    f"[{picture}][ticker_rgba]overlay=x=0:y={int(H * 0.14)}:"
                    f"enable='between(t,0.5,{total_dur:.3f})':eof_action=pass:repeatlast=0[vticker]"
                )
                picture = "vticker"
        except Exception as ticker_err:
            print(f"  [FFmpegGraph] news ticker notice: {ticker_err}", flush=True)

    # Reddit Question Card overlay (RedditVideoMakerBot / Chapter 28.16)
    _director = kwargs.get("director")
    _reddit_active = bool(
        enable_reddit_card
        or kwargs.get("enable_reddit_card", False)
        or (_director and getattr(_director, "niche_id", "") in ("reddit", "reddit_story", "11_reddit_stories"))
        or (niche_id in ("reddit", "reddit_story", "11_reddit_stories"))
    )
    rcard_png = reddit_card_path or kwargs.get("reddit_card_path")
    if _reddit_active or (rcard_png and os.path.exists(rcard_png)):
        try:
            if not rcard_png or not os.path.exists(rcard_png):
                from reddit_card_renderer import generate_transparent_reddit_card_png
                rcard_png = os.path.join(tempfile.gettempdir(), f"rcard_{int(time.time()*1000)}.png")
                card_title = title or "Reddit Soru"
                generate_transparent_reddit_card_png(
                    title=card_title,
                    subreddit="AskReddit",
                    output_path=rcard_png,
                    card_width=int(W * 0.88),
                )
            if rcard_png and os.path.exists(rcard_png):
                card_duration = sum(float(c.get("duration", 3.0)) for c in valid) + 0.5
                cmd.extend(["-loop", "1", "-t", f"{card_duration:.3f}", "-i", rcard_png])
                rcard_input = next_input
                next_input += 1
                filter_parts.append(
                    f"[{rcard_input}:v]format=rgba,"
                    f"fade=t=in:st=0:d=0.35:alpha=1[rcard_faded]"
                )
                filter_parts.append(
                    f"[{picture}][rcard_faded]overlay=x=(W-w)/2:y={int(H * 0.28)}:"
                    f"enable='between(t,0,{card_duration:.3f})':eof_action=pass:repeatlast=0[vrcard]"
                )
                picture = "vrcard"
                print("  [FFmpegGraph] Reddit question card overlay active", flush=True)
        except Exception as rcard_err:
            print(f"  [FFmpegGraph] Reddit card overlay notice: {rcard_err}", flush=True)

    filter_parts.append(f"[{picture}]format=yuv420p,{_BT709_TAG}[vout]")
    vlabel = "[vout]"

    # Audio is the last input. Cutaway, subtitles, then hook card sit before it.
    if audio_idx is None:
        audio_idx = next_input
        cmd.extend(["-i", audio_path])
        next_input += 1

    filter_complex = ";".join(filter_parts)

    # Chapter 3.4 & Section 16.1: Hierarchical hardware encoder negotiation
    from system_resilience import get_encoder_fallback_chain
    use_gpu = getattr(config, "USE_GPU_ACCELERATION", True)
    gpu_codec = getattr(config, "GPU_CODEC", "")
    threads = int(getattr(config, "FFMPEG_THREADS", getattr(config, "RENDER_THREADS", 4)) or 4)
    encoder_candidates = get_encoder_fallback_chain(use_gpu, gpu_codec)

    fps = output_fps

    # K2: Probe audio duration — use explicit -t instead of -shortest.
    _clip_total = sum(float(c.get("duration", 3.0)) for c in valid)
    _audio_dur = _probe_audio_duration(ffmpeg, audio_path)
    if _audio_dur > 0:
        _t_limit = min(_audio_dur, _clip_total) + 0.5  # 0.5s buffer for rounding
        print(
            f"  [FFmpegGraph] K2-AV: audio={_audio_dur:.2f}s clips={_clip_total:.2f}s "
            f"→ encode limit={_t_limit:.2f}s",
            flush=True,
        )
    else:
        _t_limit = _clip_total + 0.5
        print(
            f"  [FFmpegGraph] K2-AV: audio probe failed → limit=clips+0.5={_t_limit:.2f}s",
            flush=True,
        )
    av_clamp = ["-t", f"{_t_limit:.3f}"]

    if enable_zoompan:
        print("  [FFmpegGraph] zoompan AÇIK — bu geçiş render süresini uzatır", flush=True)

    # Attempt encoding with encoder fallback chain (NVENC -> QSV -> AMF -> MF -> libx264)
    try:
        for candidate_idx, (vcodec, mode) in enumerate(encoder_candidates):
            if cancel_check and cancel_check():
                raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass

            run_cmd = list(cmd)
            run_cmd.extend([
                "-filter_complex", filter_complex,
                "-map", vlabel,
                "-map", f"{audio_idx}:a",
                *vcodec,
                "-r", f"{fps:.2f}",
                "-colorspace", "bt709",
                "-color_primaries", "bt709",
                "-color_trc", "bt709",
                "-color_range", "tv",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                *av_clamp,
                "-movflags", "+faststart",
                "-map_metadata", "-1",
                "-metadata", f"title={title or 'Shorts'}",
                "-metadata", "encoder=Final Cut Pro",
                "-threads", str(threads),
                output_path,
            ])

            print(f"  [FFmpegGraph] Export: {W}x{H} @ {fps:.2f} | {mode} | {n} scenes | Madde 418", flush=True)
            if progress_callback:
                progress_callback(80, f"[FFmpegGraph] Kodlama başlıyor ({mode})...")

            try:
                proc = subprocess.Popen(
                    run_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
                )
                stderr_queue: queue.Queue[str] = queue.Queue()

                def _stderr_reader(p=proc, q=stderr_queue):
                    try:
                        if p.stderr:
                            for line in iter(p.stderr.readline, ""):
                                q.put(line)
                            p.stderr.close()
                    except Exception:
                        pass

                reader_thread = threading.Thread(target=_stderr_reader, daemon=True)
                reader_thread.start()

                stderr_data = []
                last_heartbeat = time.time()
                inactivity_limit = 120.0  # 120s inactivity limit (Item 3.5)

                while True:
                    if cancel_check and cancel_check():
                        proc.terminate()
                        try:
                            proc.wait(timeout=2.0)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

                    try:
                        line = stderr_queue.get(timeout=1.0)
                        stderr_data.append(line)
                        last_heartbeat = time.time()
                        if "time=" in line and progress_callback:
                            progress_callback(88, f"[FFmpegGraph] Kodlama devam ediyor ({mode})...")
                    except queue.Empty:
                        pass

                    if proc.poll() is not None:
                        while not stderr_queue.empty():
                            try:
                                stderr_data.append(stderr_queue.get_nowait())
                            except queue.Empty:
                                break
                        break

                    # Item 3.5: Heartbeat zombie process detection & termination
                    if time.time() - last_heartbeat > inactivity_limit:
                        print(f"  [FFmpegGraph] {mode} {inactivity_limit}s sessiz kaldı (zombi koruması), sonlandırılıyor...", flush=True)
                        proc.terminate()
                        try:
                            proc.wait(timeout=3.0)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                        break

                if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) >= 100000:
                    if progress_callback:
                        progress_callback(95, "[FFmpegGraph] Tamamlandı")
                    print(f"  [FFmpegGraph] OK → {output_path} ({os.path.getsize(output_path)//1024} KB) [{mode}]", flush=True)

                    # Post-render packaging: truthful metadata cleanup only.
                    try:
                        from anti_detect.post_render import apply_post_render_humanization
                        post = apply_post_render_humanization(output_path, title=title or "")
                        if post.get("metadata_applied"):
                            print("  [FFmpegGraph] [PostRender] metadata cleaned and title recorded.")
                    except Exception as pr_err:
                        print(f"  [FFmpegGraph] PostRender note: {pr_err}")

                    return output_path
                else:
                    err = "".join(stderr_data)[-800:]
                    print(f"  [FFmpegGraph] {mode} başarısız oldu (kod: {proc.returncode}): {err[:200]}", flush=True)
                    if candidate_idx < len(encoder_candidates) - 1:
                        next_mode = encoder_candidates[candidate_idx + 1][1]
                        print(f"  [FFmpegGraph] Sıradaki kodlayıcıya geçiliyor: {next_mode}", flush=True)
                        continue
            except InterruptedError:
                raise
            except Exception as candidate_err:
                print(f"  [FFmpegGraph] {mode} denemesinde istisna: {candidate_err}", flush=True)
                if candidate_idx < len(encoder_candidates) - 1:
                    continue

        return ""
    except InterruptedError:
        raise
    except Exception as e:
        print(f"  [FFmpegGraph] Exception: {e}")
        return ""
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def _needs_moviepy_composer(kwargs: Dict[str, Any]) -> bool:
    """
    FFmpeg graph covers concat + look + ASS + NVENC + hybrid UI in one pass.
    MoviePy only when explicit legacy fallback is requested or when an unknown,
    non-native overlay format is encountered.
    """
    if kwargs.get("force_moviepy"):
        return True
    if kwargs.get("enable_native_hybrid") is True:
        return False
    overlay = kwargs.get("hybrid_render_overlay") or {}
    if isinstance(overlay, dict) and (overlay.get("ui_type") or overlay.get("overlay")):
        if getattr(config, "ENABLE_NATIVE_HYBRID_OVERLAY", False):
            return False
        return True
    return False


def compose_via_director(
    clips: List[Dict[str, Any]],
    audio_path: str,
    word_timings: List[Dict[str, Any]],
    output_path: str,
    **kwargs,
) -> str:
    """
    Prefer FFmpeg graph; fall back to MoviePy compose_video for capability gaps.
    """
    prefer_ffmpeg = kwargs.pop("prefer_ffmpeg", True)
    enable_native_hybrid = kwargs.pop(
        "enable_native_hybrid", getattr(config, "ENABLE_NATIVE_HYBRID_OVERLAY", False)
    )
    if not enable_native_hybrid and _needs_moviepy_composer(kwargs):
        print(
            "  [Director] MoviePy compose_video — full Section-2/B5 overlay pipeline "
            "(FFmpeg graph is look+subs only)",
            flush=True,
        )
        from video_composer import compose_video
        kwargs.setdefault("audio_premastered", kwargs.get("audio_premastered", True))
        return compose_video(clips, audio_path, word_timings, output_path, **kwargs)

    # Fast path: basic concat + look when overlays disabled explicitly
    if prefer_ffmpeg and getattr(config, "ENABLE_FFMPEG_GRAPH", True):
        result = render_with_ffmpeg_graph(
            clips, audio_path, output_path,
            word_timings=word_timings,
            title=kwargs.get("title", ""),
            subtitle_opts=kwargs.get("subtitle_opts"),
            progress_callback=kwargs.get("progress_callback"),
            cancel_check=kwargs.get("cancel_check"),
            anti_duplicate=kwargs.get("anti_duplicate", True),
            enable_ken_burns=kwargs.get("enable_ken_burns", True),
            enable_zoompan=bool(kwargs.get("enable_zoompan", False)),
            enable_broll=bool(kwargs.get("enable_broll", False) or kwargs.get("enable_broll_insert", False)),
            enable_face_center=bool(kwargs.get("enable_face_center", False)),
            emphasis_ass_path=kwargs.get("emphasis_ass_path"),
            enable_emphasis_card=bool(kwargs.get("enable_emphasis_card", False)),
            gameplay_path=kwargs.get("gameplay_path") if kwargs.get("split_screen") or kwargs.get("gameplay_path") else None,
            hybrid_render_overlay=kwargs.get("hybrid_render_overlay"),
            enable_audio_visualizer=bool(kwargs.get("enable_audio_visualizer", False)),
            audio_visualizer_mode=kwargs.get("audio_visualizer_mode", "line"),
            audio_visualizer_color=kwargs.get("audio_visualizer_color", "0x00D7FF"),
            enable_news_ticker=bool(kwargs.get("enable_news_ticker", False)),
            news_ticker_text=kwargs.get("news_ticker_text"),
            niche_id=kwargs.get("niche_id", ""),
            enable_reddit_card=bool(kwargs.get("enable_reddit_card", False)),
            reddit_card_path=kwargs.get("reddit_card_path"),
            director=kwargs.get("director"),
        )
        if result:
            return result
        print("  [Director] FFmpeg graph fallback → MoviePy compose_video")

    from video_composer import compose_video
    kwargs["audio_premastered"] = kwargs.pop("audio_premastered", True)
    return compose_video(clips, audio_path, word_timings, output_path, **kwargs)
