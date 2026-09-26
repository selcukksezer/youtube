"""
Smart Vertical Video Cropper with OpenCV Face-Tracking.
Adapted and improved from Anil-matcha/AI-Youtube-Shorts-Generator (clipper.py).
Tracks human faces in horizontal video and smoothly glides a vertical 9:16 window.
"""
import os
import subprocess
from typing import Optional, Tuple
import cv2
import imageio_ffmpeg


def _parse_aspect_ratio(aspect_ratio: str = "9:16") -> float:
    try:
        w, h = aspect_ratio.split(":")
        return float(w) / float(h)
    except Exception:
        return 9.0 / 16.0


def _get_ffmpeg_exe() -> str:
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def reframe_to_vertical(
    in_path: str,
    out_path: str,
    aspect_ratio: str = "9:16",
    smoothing: float = 0.15,
    sample_every_n_frames: int = 2,
) -> str:
    """
    Reframes an input video to vertical 9:16 using OpenCV face detection + motion smoothing.
    If no face is detected, it falls back to a clean center crop.
    Keeps original audio intact.
    """
    if not os.path.exists(in_path):
        raise FileNotFoundError(f"Input video not found: {in_path}")

    target_ratio = _parse_aspect_ratio(aspect_ratio)
    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {in_path}")

    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    if src_w <= 0 or src_h <= 0:
        cap.release()
        raise RuntimeError(f"Invalid video dimensions: {src_w}x{src_h}")

    # Compute crop dimensions
    if target_ratio < (src_w / src_h):
        crop_h = src_h
        crop_w = int(crop_h * target_ratio)
    else:
        crop_w = src_w
        crop_h = int(crop_w / target_ratio)

    # Ensure even dimensions for video codecs
    crop_w = max(2, crop_w - (crop_w % 2))
    crop_h = max(2, crop_h - (crop_h % 2))

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    silent_tmp = out_path + ".silent.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(silent_tmp, fourcc, fps, (crop_w, crop_h))

    last_center: Optional[Tuple[int, int]] = None
    frame_idx = 0
    cached_box = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Face detection optimization: run every N frames
            if frame_idx % sample_every_n_frames == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(
                    gray, scaleFactor=1.15, minNeighbors=4, minSize=(40, 40)
                )
                if len(faces) > 0:
                    # Choose largest face (main speaker)
                    cached_box = max(faces, key=lambda f: f[2] * f[3])
                else:
                    cached_box = None

            if cached_box is not None:
                x, y, w, h = cached_box
                cx = x + w // 2
                cy = y + h // 2
                if last_center is None:
                    last_center = (cx, cy)
                else:
                    lx, ly = last_center
                    # Exponential smoothing to avoid jerky camera moves
                    last_center = (
                        int(lx + (cx - lx) * smoothing),
                        int(ly + (cy - ly) * smoothing),
                    )

            if last_center is None:
                last_center = (src_w // 2, src_h // 2)

            cx, cy = last_center
            x0 = max(0, min(src_w - crop_w, cx - crop_w // 2))
            y0 = max(0, min(src_h - crop_h, cy - crop_h // 2))

            cropped = frame[y0 : y0 + crop_h, x0 : x0 + crop_w]
            writer.write(cropped)
            frame_idx += 1
    finally:
        cap.release()
        writer.release()

    # Mux audio back using FFmpeg
    ffmpeg_exe = _get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-loglevel",
        "error",
        "-i",
        silent_tmp,
        "-i",
        in_path,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "22",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-shortest",
        out_path,
    ]

    subprocess.run(cmd, check=True)
    if os.path.exists(silent_tmp):
        try:
            os.remove(silent_tmp)
        except OSError:
            pass

    return out_path


def crop_subclip_smart(
    source_path: str,
    start_time: float,
    end_time: float,
    out_path: str,
    aspect_ratio: str = "9:16",
) -> str:
    """
    Cuts a segment [start_time, end_time] and reframes with smart face-tracking.
    """
    ffmpeg_exe = _get_ffmpeg_exe()
    cut_tmp = out_path + ".cut.mp4"

    cmd_cut = [
        ffmpeg_exe,
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{start_time:.3f}",
        "-to",
        f"{end_time:.3f}",
        "-i",
        source_path,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "aac",
        cut_tmp,
    ]
    subprocess.run(cmd_cut, check=True)

    try:
        return reframe_to_vertical(cut_tmp, out_path, aspect_ratio=aspect_ratio)
    finally:
        if os.path.exists(cut_tmp):
            try:
                os.remove(cut_tmp)
            except OSError:
                pass
