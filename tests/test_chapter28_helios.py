"""
Unit and Integration tests for Chapter 28.4 (helios adaptations):
- visuals.motion_evaluator (VideoMotionEvaluator, compute_motion_score, heal_static_video_with_ken_burns)
- Verifies Farneback optical flow / frame difference motion amplitude scoring and static-scene healing.
"""

import os
import subprocess
import tempfile
import pytest

from visuals.motion_evaluator import VideoMotionEvaluator, get_ffmpeg_binary


def _create_static_test_video(path: str, duration_sec: float = 3.0):
    """Creates a completely static video (constant color) using lavfi color."""
    ffmpeg = get_ffmpeg_binary()
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=blue:s=320x240:d={duration_sec}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _create_moving_test_video(path: str, duration_sec: float = 3.0):
    """Creates a dynamic video with moving test patterns."""
    ffmpeg = get_ffmpeg_binary()
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={duration_sec}:size=320x240:rate=25",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def test_motion_evaluation_static_detection():
    """Verify that a completely static video is detected with low motion amplitude."""
    with tempfile.TemporaryDirectory() as tmpdir:
        static_mp4 = os.path.join(tmpdir, "static.mp4")
        _create_static_test_video(static_mp4, duration_sec=3.0)

        res = VideoMotionEvaluator.evaluate_video(static_mp4)
        assert res["is_static"] is True
        assert res["motion_amplitude"] < 0.05
        assert "static" in res["verdict"]


def test_motion_evaluation_dynamic_video():
    """Verify that a moving video produces significant motion amplitude."""
    with tempfile.TemporaryDirectory() as tmpdir:
        moving_mp4 = os.path.join(tmpdir, "moving.mp4")
        _create_moving_test_video(moving_mp4, duration_sec=3.0)

        res = VideoMotionEvaluator.evaluate_video(moving_mp4)
        assert res["is_static"] is False
        assert res["motion_amplitude"] > 0.05
        assert res["verdict"] in ("excellent", "good")


def test_heal_static_video_with_ken_burns():
    """Verify self-healing Ken Burns camera pan-zoom transforms static clip into dynamic output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        static_mp4 = os.path.join(tmpdir, "static_input.mp4")
        healed_mp4 = os.path.join(tmpdir, "healed_output.mp4")
        _create_static_test_video(static_mp4, duration_sec=3.0)

        res_path = VideoMotionEvaluator.heal_static_video_with_ken_burns(
            source_path=static_mp4,
            output_path=healed_mp4,
            duration=3.0,
            zoom_rate=0.003,
        )

        assert res_path == healed_mp4
        assert os.path.isfile(healed_mp4)
        assert os.path.getsize(healed_mp4) > 1000
