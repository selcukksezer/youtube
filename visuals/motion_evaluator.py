"""
visuals/motion_evaluator.py — Video Motion Amplitude & Smoothness Evaluator.
Adapted and evolved from reference_repos/helios (eval/1_get_motion_amplitude.py,
eval/2_get_motion_smoothness.py).

Provides:
- Farneback dense optical flow / frame-difference motion amplitude measurement.
- Detection of static "dead-frame" AI/stock videos and chaotic jittery hallucinations.
- Self-healing cinematic Ken Burns injection when static scenes are detected.
"""

from __future__ import annotations

import logging
import math
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import imageio_ffmpeg
from services.path_security import validate_asset_path


logger = logging.getLogger("motion_evaluator")


def get_ffmpeg_binary() -> str:
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


class VideoMotionEvaluator:
    """
    Evaluates motion amplitude and smoothness of video clips to prevent static image clips
    or chaotic AI hallucinations from damaging viewer retention.
    """

    DEFAULT_MIN_MOTION = 0.08  # Below this, video looks like a static still photo
    DEFAULT_MAX_MOTION = 22.0  # Above this, video suffers from chaotic flickering/jitter

    @classmethod
    def extract_probe_frames(
        cls,
        video_path: str,
        num_frames: int = 12,
        width: int = 320,
        height: int = 180,
    ) -> List[Any]:
        """
        Extracts uniformly sampled low-resolution RGB frames for fast motion evaluation.
        Uses OpenCV if installed, or falls back to FFmpeg raw image pipe.
        """
        valid_path = validate_asset_path(video_path)
        if not os.path.isfile(valid_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        frames: List[Any] = []
        try:
            import cv2
            cap = cv2.VideoCapture(valid_path)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if total > 0 and cap.isOpened():
                step = max(1, total // max(1, num_frames))
                for i in range(0, min(total, num_frames * step), step):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                    ret, frame = cap.read()
                    if not ret:
                        break
                    resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                    frames.append(gray)
                cap.release()
                if len(frames) >= 2:
                    return frames
        except Exception:
            pass

        # Robust FFmpeg image extraction fallback (zero external C-library dependency)
        ffmpeg = get_ffmpeg_binary()
        with tempfile.TemporaryDirectory() as tmpdir:
            pattern = os.path.join(tmpdir, "probe_%03d.bmp")
            cmd = [
                ffmpeg, "-y", "-loglevel", "error",
                "-i", valid_path,
                "-vf", f"fps=3,scale={width}:{height}",
                "-frames:v", str(num_frames),
                pattern,
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            try:
                from PIL import Image
                for fname in sorted(os.listdir(tmpdir)):
                    if fname.endswith(".bmp"):
                        im = Image.open(os.path.join(tmpdir, fname)).convert("L")
                        frames.append(list(im.getdata()))
            except Exception:
                pass

        return frames

    @classmethod
    def compute_motion_score(cls, frames: List[Any]) -> Dict[str, Any]:
        """
        Computes motion amplitude using Farneback optical flow (when OpenCV available)
        or normalized frame difference variance (helios eval pattern).
        """
        if len(frames) < 2:
            return {
                "motion_amplitude": 0.0,
                "motion_smoothness": 1.0,
                "is_static": True,
                "is_chaotic": False,
                "verdict": "insufficient_frames",
            }

        # Check if frames are OpenCV numpy arrays
        try:
            import cv2
            import numpy as np
            if isinstance(frames[0], np.ndarray):
                flow_magnitudes = []
                accelerations = []
                prev_mag = 0.0

                for i in range(1, len(frames)):
                    flow = cv2.calcOpticalFlowFarneback(
                        frames[i - 1],
                        frames[i],
                        flow=None,
                        pyr_scale=0.5,
                        levels=2,
                        winsize=13,
                        iterations=2,
                        poly_n=5,
                        poly_sigma=1.1,
                        flags=0,
                    )
                    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                    mean_mag = float(np.mean(mag))
                    flow_magnitudes.append(mean_mag)

                    if i > 1:
                        accel = abs(mean_mag - prev_mag)
                        accelerations.append(accel)
                    prev_mag = mean_mag

                avg_motion = float(np.mean(flow_magnitudes)) if flow_magnitudes else 0.0
                smoothness = 1.0 / (1.0 + (float(np.mean(accelerations)) if accelerations else 0.0))

                is_static = avg_motion < cls.DEFAULT_MIN_MOTION
                is_chaotic = avg_motion > cls.DEFAULT_MAX_MOTION

                verdict = "excellent"
                if is_static:
                    verdict = "static_dead_air"
                elif is_chaotic:
                    verdict = "chaotic_jitter"

                return {
                    "motion_amplitude": round(avg_motion, 3),
                    "motion_smoothness": round(smoothness, 3),
                    "is_static": is_static,
                    "is_chaotic": is_chaotic,
                    "verdict": verdict,
                }
        except Exception:
            pass

        # Fallback: Normalized pixel absolute difference
        diffs = []
        for i in range(1, len(frames)):
            f1 = frames[i - 1]
            f2 = frames[i]
            length = min(len(f1), len(f2))
            diff_sum = sum(abs(f1[j] - f2[j]) for j in range(0, length, 8))
            diffs.append(diff_sum / (length / 8.0))

        avg_diff = sum(diffs) / len(diffs) if diffs else 0.0
        normalized_motion = avg_diff / 10.0

        is_static = normalized_motion < cls.DEFAULT_MIN_MOTION
        is_chaotic = normalized_motion > cls.DEFAULT_MAX_MOTION

        return {
            "motion_amplitude": round(normalized_motion, 3),
            "motion_smoothness": 0.85,
            "is_static": is_static,
            "is_chaotic": is_chaotic,
            "verdict": "static_dead_air" if is_static else ("chaotic_jitter" if is_chaotic else "good"),
        }

    @classmethod
    def evaluate_video(cls, video_path: str) -> Dict[str, Any]:
        """Full motion analysis of video clip."""
        frames = cls.extract_probe_frames(video_path)
        return cls.compute_motion_score(frames)

    @classmethod
    def heal_static_video_with_ken_burns(
        cls,
        source_path: str,
        output_path: str,
        duration: float = 5.0,
        zoom_rate: float = 0.0015,
    ) -> str:
        """
        Self-healing mechanism (ShortsVideoCreators pattern):
        If an AI clip is evaluated as static, injects a smooth native FFmpeg zoompan
        camera movement so the scene stays dynamic without having to regenerate.
        """
        valid_src = validate_asset_path(source_path)
        ffmpeg = get_ffmpeg_binary()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        frames_total = int(duration * 30)
        vf = (
            f"zoompan=z='min(zoom+{zoom_rate:.5f},1.15)':d={frames_total}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        )
        cmd = [
            ffmpeg, "-y", "-loglevel", "error",
            "-i", valid_src,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-t", f"{duration:.2f}",
            output_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
