"""
Unit and Integration tests for Chapter 28.3 (anil_matcha_shorts_generator adaptations):
- scenes.scene_composer (clip_video_segment, RMSAudioEnergyAnalyzer, WhisperTranscriber, dedupe_highlights)
- Verification of keyframe dual-seek, wave/audioop RMS amplitude scoring, and highlight deduping.
"""

import math
import os
import struct
import subprocess
import tempfile
import wave
import pytest

from scenes.scene_composer import (
    clip_video_segment,
    RMSAudioEnergyAnalyzer,
    WhisperTranscriber,
    dedupe_highlights,
    get_ffmpeg_binary,
)


def _generate_synthetic_wav(path: str, duration_sec: float = 6.0, sample_rate: int = 16000):
    """Generates a WAV with silence first, then a loud peak between 2.0s and 4.0s."""
    total_frames = int(duration_sec * sample_rate)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)

        frames = bytearray()
        for i in range(total_frames):
            t = i / sample_rate
            if 2.0 <= t <= 4.0:
                # Loud 440 Hz tone
                val = int(24000 * math.sin(2 * math.pi * 440 * t))
            else:
                # Quiet whisper / background
                val = int(500 * math.sin(2 * math.pi * 100 * t))
            frames.extend(struct.pack("<h", max(-32768, min(32767, val))))
        wf.writeframes(frames)


def _generate_synthetic_mp4(path: str, duration_sec: float = 8.0):
    """Creates a lightweight test mp4 using ffmpeg lavfi."""
    ffmpeg = get_ffmpeg_binary()
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={duration_sec}:size=640x360:rate=30",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration_sec}",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def test_rms_waveform_analysis():
    """Verify RMS energy calculation and peak window identification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = os.path.join(tmpdir, "test_audio.wav")
        _generate_synthetic_wav(wav_path, duration_sec=6.0)

        # 1. Compute RMS Profile
        profile = RMSAudioEnergyAnalyzer.compute_rms_profile(wav_path, window_ms=250)
        assert len(profile) > 0
        assert all("start" in p and "rms" in p and "normalized" in p for p in profile)

        # Find peak windows
        peaks = RMSAudioEnergyAnalyzer.find_highest_energy_window(profile, window_duration=2.0, top_k=1)
        assert len(peaks) == 1
        peak = peaks[0]
        # Peak should be around 2.0s - 4.0s
        assert 1.5 <= peak["start"] <= 2.5
        assert peak["energy_score"] > 0.6


def test_whisper_transcriber_scoring():
    """Verify tri-factor composite virality and confidence scoring."""
    # High virality: contains high-impact power words and high RMS
    score_high = WhisperTranscriber.score_segment(
        text="Bu inanılmaz gizli sır tam bir para tuzağı!",
        rms_energy=0.85,
        word_confidences=[0.98, 0.99, 0.95, 0.97],
    )

    # Low virality: mundane sentence with low RMS
    score_low = WhisperTranscriber.score_segment(
        text="Bugün hava biraz bulutlu ve sakin görünüyor.",
        rms_energy=0.20,
        word_confidences=[0.80, 0.85],
    )

    assert score_high > score_low
    assert score_high >= 70.0
    assert score_low <= 60.0


def test_dedupe_highlights_overlap_suppression():
    """Verify overlapping highlight candidate suppression."""
    candidates = [
        {"title": "C1", "start": 0.0, "end": 10.0, "score": 92.0},
        {"title": "C2", "start": 2.0, "end": 9.0, "score": 75.0},   # Overlaps 100% with C1 (drop)
        {"title": "C3", "start": 15.0, "end": 25.0, "score": 88.0},  # Independent (keep)
        {"title": "C4", "start": 23.0, "end": 30.0, "score": 60.0},  # Overlaps 28% with C3 (keep if ratio < 0.5)
    ]

    kept = dedupe_highlights(candidates, max_overlap_ratio=0.5)
    kept_titles = [k["title"] for k in kept]

    assert "C1" in kept_titles
    assert "C3" in kept_titles
    assert "C2" not in kept_titles  # Dropped due to >50% overlap with C1


def test_clip_video_segment_dual_seek():
    """Verify dual-seek keyframe-accurate clipping with FFmpeg."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_mp4 = os.path.join(tmpdir, "source.mp4")
        out_mp4 = os.path.join(tmpdir, "cut.mp4")

        _generate_synthetic_mp4(src_mp4, duration_sec=8.0)
        assert os.path.isfile(src_mp4)

        # Clip segment from 4.0s to 7.0s (triggers dual-seek since start > 3.0)
        res = clip_video_segment(
            source_path=src_mp4,
            start_time=4.0,
            end_time=7.0,
            output_path=out_mp4,
            accurate_seek=True,
            reframe_vertical=True,
            target_width=540,
            target_height=960,
        )

        assert res == out_mp4
        assert os.path.isfile(out_mp4)
        assert os.path.getsize(out_mp4) > 1000
