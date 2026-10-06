"""
Face-Centered 9:16 Vertical Reframing Engine (Plan Item P1).
Adapted from anil_matcha_shorts_generator (clipper.py:_reframe_vertical) & ai-content-studio.

Detects faces using OpenCV Haar Cascades, computes smoothed horizontal center,
and generates optimal FFmpeg crop coordinates so the subject remains centered
in 9:16 vertical shorts without expensive re-encoding loops.
"""
from __future__ import annotations

import os
import sys
import math
from bisect import bisect_right
from typing import List, Optional, Tuple


def _get_short_path(path: str) -> str:
    """Resolve Windows 8.3 short path to avoid non-ASCII path encoding issues in OpenCV C++ core."""
    if sys.platform == "win32" and os.path.exists(path):
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(500)
            if ctypes.windll.kernel32.GetShortPathNameW(path, buf, 500) > 0:
                return buf.value
        except Exception:
            pass
    return path


def _load_cascade():
    """Safely loads cv2 Haar cascade classifier."""
    try:
        import cv2
        data_dir = getattr(cv2.data, "haarcascades", "")
        if not data_dir:
            return None
        xml_path = os.path.join(data_dir, "haarcascade_frontalface_default.xml")
        if not os.path.exists(xml_path):
            return None
        safe_path = _get_short_path(xml_path)
        cascade = cv2.CascadeClassifier(safe_path)
        if cascade.empty():
            return None
        return cascade
    except Exception:
        return None


def detect_face_track(
    media_path: str, samples_per_sec: float = 2.0,
    duration: Optional[float] = None, start_time: float = 0.0,
    max_samples: int = 120,
) -> List[Tuple[float, float]]:
    """Sample the requested interval; return relative time and normalized center.

    Bound detection attempts, including frames without faces. Seek between
    samples instead of decoding every frame. Missing detections hold the last
    position; interpolate measured positions in the final renderer.
    """
    if not media_path or not os.path.isfile(media_path):
        return []
    try:
        import cv2
    except (ImportError, OSError):
        return []
    cascade = _load_cascade()
    if cascade is None:
        return []

    def measure(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces) == 0:
            return None
        x, _, w, _ = max(faces, key=lambda f: f[2] * f[3])
        return max(0.0, min(1.0, float(x + w / 2.0) / frame.shape[1]))

    cap = None
    try:
        if os.path.splitext(media_path)[1].lower() in (".jpg", ".jpeg", ".png", ".webp"):
            import numpy as np
            frame = cv2.imdecode(np.fromfile(media_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            center = measure(frame) if frame is not None else None
            return [(0.0, center)] if center is not None else []
        cap = cv2.VideoCapture(_get_short_path(media_path))
        if not cap.isOpened():
            return []
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        if not math.isfinite(fps) or fps <= 0:
            fps = 30.0
        count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        start = max(0.0, float(start_time))
        available = max(0.0, count / fps - start)
        limit = min(float(duration), available) if duration is not None and available else float(duration or available or 10.0)
        if not math.isfinite(limit) or limit <= 0:
            return []
        attempts = max(1, min(120, int(max_samples)))
        step = max(1.0 / max(0.5, float(samples_per_sec)), limit / max(1, attempts - 1))
        track = []
        previous = None
        for index in range(attempts):
            stamp = index * step
            if stamp >= limit:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, round((start + stamp) * fps))
            ok, frame = cap.read()
            if not ok:
                break
            center = measure(frame)
            if center is not None:
                # Same per-frame 0.15 response as anil, converted to sample time.
                alpha = 1.0 - 0.85 ** (step * fps)
                previous = center if previous is None else previous + alpha * (center - previous)
            if previous is not None:
                track.append((round(stamp, 4), float(previous)))
        return track
    except Exception:
        return []
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def face_center_at(track: List[Tuple[float, float]], time: float) -> float:
    """Interpolate the same measured trajectory in MoviePy or tests."""
    if not track:
        return 0.5
    index = bisect_right([p[0] for p in track], time)
    if index == 0:
        return track[0][1]
    if index == len(track):
        return track[-1][1]
    t0, x0 = track[index - 1]
    t1, x1 = track[index]
    return x0 + (x1 - x0) * (time - t0) / (t1 - t0)


def face_crop_expression(track: List[Tuple[float, float]]) -> Optional[str]:
    """Post-scale FFmpeg x(t); normalized coordinates avoid scale mismatch."""
    if not track:
        return None
    terms = [f"{track[0][1]:.7f}"]
    for (t0, x0), (t1, x1) in zip(track, track[1:]):
        if t1 > t0 and abs(x1 - x0) > 0.000001:
            terms.append(f"({x1-x0:.7f})*clip((t-{t0:.4f})/{t1-t0:.4f},0,1)")
    return "2*floor(max(0,min(iw-ow,iw*(" + "+".join(terms) + ")-ow/2))/2)"


def detect_face_center_x(media_path: str, samples_per_sec: float = 2.0) -> Optional[float]:
    """Stable static crop for callers that do not use a time expression."""
    track = detect_face_track(media_path, samples_per_sec, duration=10.0, max_samples=20)
    if not track:
        return None
    sorted_centers = sorted(center for _, center in track)
    mid_start = len(sorted_centers) // 4
    mid_end = max(mid_start + 1, len(sorted_centers) - mid_start)
    avg_center = sum(sorted_centers[mid_start:mid_end]) / float(mid_end - mid_start)
    return float(max(0.0, min(1.0, avg_center)))


def compute_face_crop_x(
    media_path: str,
    src_w: int,
    src_h: int,
    out_w: int = 1080,
    out_h: int = 1920,
) -> Optional[int]:
    """
    Computes horizontal crop X offset (in pixels) for 9:16 target framing.
    Returns None if media is already vertical or no face detected.
    """
    if src_w <= 0 or src_h <= 0 or out_w <= 0 or out_h <= 0:
        return None

    # Only landscape or square source requires horizontal re-centering
    target_aspect = out_w / float(out_h)
    src_aspect = src_w / float(src_h)
    if src_aspect <= target_aspect:
        return None

    center_norm = detect_face_center_x(media_path)
    if center_norm is None:
        return None

    # Width of the crop window inside src
    crop_w = int(src_h * target_aspect)
    crop_w = max(2, crop_w - (crop_w % 2))

    # Calculate desired left pixel
    pixel_center = int(center_norm * src_w)
    left_x = pixel_center - crop_w // 2

    # Clamp to boundaries
    clamped_x = max(0, min(src_w - crop_w, left_x))
    # Modulo-2 even alignment
    return clamped_x - (clamped_x % 2)
