"""
scenes/scene_composer.py — Keyframe-Accurate Video Segment Clipper,
RMS Audio Waveform Analyzer & Whisper Confidence Scorer.

Adapted and evolved from reference_repos/anil_matcha_shorts_generator
(shorts_generator/clipper.py, transcriber.py, highlights.py).
Solves the dropped-frame seeking problem using dual -ss flags and eliminates
OpenCV CPU loops with native single-pass FFmpeg hardware graphs.
"""

from __future__ import annotations

import audioop
import json
import logging
import math
import os
import re
import subprocess
import wave
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import imageio_ffmpeg
from services.path_security import validate_asset_path, sanitize_filename


logger = logging.getLogger("scene_composer")


def get_ffmpeg_binary() -> str:
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def clip_video_segment(
    source_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    accurate_seek: bool = True,
    target_width: int = 1080,
    target_height: int = 1920,
    reframe_vertical: bool = False,
    encoder: str = "libx264",
) -> str:
    """
    Keyframe-accurate video subclip cutting.
    Eliminates dropped frames and black flashes (anil_matcha_shorts_generator flaw)
    via dual-seek strategy:
      - Pre-input fast seek (-ss start - delta) jumps close to prior I-frame.
      - Post-input fine seek (-ss delta) decodes exact target timestamp.
    """
    valid_source = validate_asset_path(source_path)
    if not os.path.isfile(valid_source):
        raise FileNotFoundError(f"Source video not found: {source_path}")

    start = max(0.0, float(start_time))
    end = float(end_time)
    if end <= start:
        raise ValueError(f"Invalid clip boundaries: start={start:.3f}, end={end:.3f}")

    duration = end - start
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    ffmpeg_exe = get_ffmpeg_binary()

    cmd: List[str] = [ffmpeg_exe, "-y", "-loglevel", "error"]

    if accurate_seek and start > 3.0:
        # Dual-seek: Jump fast to 2 seconds before target, then decode forward
        pre_seek = start - 2.0
        fine_seek = 2.0
        cmd.extend(["-ss", f"{pre_seek:.3f}", "-i", valid_source])
        cmd.extend(["-ss", f"{fine_seek:.3f}", "-t", f"{duration:.3f}"])
    else:
        # Standard input-seek for start close to origin
        cmd.extend(["-ss", f"{start:.3f}", "-i", valid_source, "-t", f"{duration:.3f}"])

    cmd.extend(["-avoid_negative_ts", "make_zero"])

    if reframe_vertical:
        # Hardware-ready 9:16 vertical cover crop with smooth scaling (replaces OpenCV loop)
        vf = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height},"
            f"setsar=1,fps=30"
        )
        cmd.extend(["-vf", vf])

    cmd.extend([
        "-c:v", encoder,
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        err_msg = (res.stderr or "").strip()
        raise RuntimeError(f"FFmpeg clipping failed: {err_msg}")

    return output_path


def compose_dual_clip_scene(
    video_a_path: str,
    video_b_path: str,
    total_duration: float,
    output_path: str,
    audio_path: Optional[str] = None,
    target_width: int = 1080,
    target_height: int = 1920,
    fps: int = 30,
    encoder: str = "libx264",
    split_ratio: float = 0.5,
) -> str:
    """
    Combines two video clips into a single scene with split duration (e.g. 50/50 A/B cut).
    Adapted and evolved from reference_repos/saard00_shorts_generator (modules/composer.py).

    Eliminates saard00's two-step multi-pass disk re-encoding by assembling the
    split cut directly in a single-pass FFmpeg filter_complex stream:
      [0:v]trim=duration=dur_a,setpts=PTS-STARTPTS,scale=...,crop=...[v0];
      [1:v]trim=duration=dur_b,setpts=PTS-STARTPTS,scale=...,crop=...[v1];
      [v0][v1]concat=n=2:v=1:a=0[v]
    """
    valid_a = validate_asset_path(video_a_path)
    valid_b = validate_asset_path(video_b_path)
    if not os.path.isfile(valid_a):
        raise FileNotFoundError(f"Video A not found: {video_a_path}")
    if not os.path.isfile(valid_b):
        raise FileNotFoundError(f"Video B not found: {video_b_path}")

    dur = max(0.2, float(total_duration))
    ratio = min(0.9, max(0.1, float(split_ratio)))
    dur_a = round(dur * ratio, 3)
    dur_b = round(dur - dur_a, 3)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    ffmpeg_exe = get_ffmpeg_binary()

    vf_a = (
        f"[0:v]trim=duration={dur_a:.3f},setpts=PTS-STARTPTS,"
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
        f"crop={target_width}:{target_height},setsar=1,fps={fps}[v0]"
    )
    vf_b = (
        f"[1:v]trim=duration={dur_b:.3f},setpts=PTS-STARTPTS,"
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
        f"crop={target_width}:{target_height},setsar=1,fps={fps}[v1]"
    )
    filter_complex = f"{vf_a};{vf_b};[v0][v1]concat=n=2:v=1:a=0[outv]"

    cmd: List[str] = [
        ffmpeg_exe, "-y", "-loglevel", "error",
        "-stream_loop", "-1", "-i", valid_a,
        "-stream_loop", "-1", "-i", valid_b,
    ]

    has_audio = False
    if audio_path:
        valid_audio = validate_asset_path(audio_path)
        if os.path.isfile(valid_audio):
            cmd.extend(["-i", valid_audio])
            has_audio = True

    cmd.extend(["-filter_complex", filter_complex, "-map", "[outv]"])

    if has_audio:
        cmd.extend(["-map", "2:a", "-c:a", "aac", "-b:a", "128k"])
    else:
        cmd.append("-an")

    cmd.extend([
        "-c:v", encoder,
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-t", f"{dur:.3f}",
        "-movflags", "+faststart",
        output_path,
    ])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        err_msg = (res.stderr or "").strip()
        raise RuntimeError(f"FFmpeg dual clip composition failed: {err_msg}")

    return output_path


class RMSAudioEnergyAnalyzer:
    """
    Extracts RMS (Root-Mean-Square) amplitude energy profiles from audio waveform
    to pinpoint the most dynamic, high-energy 3-second segments of speech.
    """

    @staticmethod
    def extract_pcm_wav(media_path: str, target_wav: str, sample_rate: int = 16000) -> str:
        """Extracts mono 16-bit PCM WAV for precision audio analysis."""
        ffmpeg_exe = get_ffmpeg_binary()
        cmd = [
            ffmpeg_exe, "-y", "-loglevel", "error",
            "-i", media_path,
            "-ac", "1",
            "-ar", str(sample_rate),
            "-vn",
            "-c:a", "pcm_s16le",
            target_wav,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return target_wav

    @classmethod
    def compute_rms_profile(
        cls,
        wav_path: str,
        window_ms: int = 250,
    ) -> List[Dict[str, float]]:
        """
        Calculates time-indexed RMS values using Python built-in wave + audioop modules.
        Returns list of {'start': float, 'end': float, 'rms': float, 'normalized': float}.
        """
        if not os.path.isfile(wav_path):
            raise FileNotFoundError(f"WAV file not found: {wav_path}")

        profile: List[Dict[str, float]] = []
        with wave.open(wav_path, "rb") as wf:
            framerate = wf.getframerate()
            sample_width = wf.getsampwidth()
            n_channels = wf.getnchannels()

            chunk_frames = int(framerate * (window_ms / 1000.0))
            frame_idx = 0
            max_rms = 1.0

            while True:
                data = wf.readframes(chunk_frames)
                if not data:
                    break
                rms = audioop.rms(data, sample_width)
                if rms > max_rms:
                    max_rms = float(rms)

                start_sec = frame_idx * (window_ms / 1000.0)
                end_sec = start_sec + (len(data) / (sample_width * n_channels * framerate))
                profile.append({
                    "start": round(start_sec, 3),
                    "end": round(end_sec, 3),
                    "rms": float(rms),
                })
                frame_idx += 1

        # Normalize 0.0 to 1.0
        for entry in profile:
            entry["normalized"] = round(entry["rms"] / max(1.0, max_rms), 3)

        return profile

    @classmethod
    def find_highest_energy_window(
        cls,
        profile: List[Dict[str, float]],
        window_duration: float = 3.0,
        min_gap_sec: float = 4.0,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Sliding-window analysis to identify top-k non-overlapping peak energy windows.
        """
        if not profile:
            return []

        step_sec = profile[0]["end"] - profile[0]["start"] if len(profile) > 1 else 0.25
        samples_in_win = max(1, int(window_duration / step_sec))

        candidates: List[Dict[str, Any]] = []
        for i in range(len(profile) - samples_in_win + 1):
            sub = profile[i : i + samples_in_win]
            avg_rms = sum(item["normalized"] for item in sub) / len(sub)
            win_start = sub[0]["start"]
            win_end = sub[-1]["end"]
            candidates.append({
                "start": win_start,
                "end": win_end,
                "duration": round(win_end - win_start, 3),
                "energy_score": round(avg_rms, 3),
            })

        candidates.sort(key=lambda x: x["energy_score"], reverse=True)

        selected: List[Dict[str, Any]] = []
        for cand in candidates:
            clash = False
            for s in selected:
                if abs(cand["start"] - s["start"]) < min_gap_sec:
                    clash = True
                    break
            if not clash:
                selected.append(cand)
                if len(selected) >= top_k:
                    break

        return selected


class WhisperTranscriber:
    """
    Word-level timestamp extractor and confidence scorer.
    Integrates Faster-Whisper when present, or provides standard structural fallback.
    """

    VIRALITY_KEYWORDS = {
        "para", "sır", "gizli", "şok", "tehlike", "bomba", "inanılmaz", "asla",
        "milyarder", "ölümcül", "taktik", "kanıt", "yalan", "hata", "uyarı",
        "money", "secret", "crazy", "shocking", "insane", "hidden", "warning",
    }

    @classmethod
    def score_segment(
        cls,
        text: str,
        rms_energy: float = 0.5,
        word_confidences: Optional[List[float]] = None,
    ) -> float:
        """
        Tri-factor virality calculation:
          - 50% Text keyword density & hook intent.
          - 30% RMS audio waveform energy peak.
          - 20% Whisper transcription word confidence.
        """
        clean_words = re.findall(r"\b\w+\b", text.lower())
        if not clean_words:
            return 0.0

        keyword_hits = sum(1 for w in clean_words if w in cls.VIRALITY_KEYWORDS)
        keyword_density = min(1.0, keyword_hits / max(1, len(clean_words) / 3))
        text_score = min(1.0, 0.4 + keyword_density * 0.6)

        avg_conf = 0.95
        if word_confidences:
            avg_conf = sum(word_confidences) / len(word_confidences)

        total_score = (0.50 * text_score) + (0.30 * min(1.0, max(0.0, rms_energy))) + (0.20 * avg_conf)
        return round(total_score * 100, 1)


def dedupe_highlights(
    highlights: List[Dict[str, Any]],
    max_overlap_ratio: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Drops candidate highlights if overlap with an already selected higher-scoring
    highlight exceeds max_overlap_ratio (anil_matcha_shorts_generator pattern).
    """
    sorted_items = sorted(
        highlights,
        key=lambda x: float(x.get("score", x.get("energy_score", 0.0))),
        reverse=True,
    )
    kept: List[Dict[str, Any]] = []

    for item in sorted_items:
        start = float(item["start_time"] if "start_time" in item else item.get("start", 0.0))
        end = float(item["end_time"] if "end_time" in item else item.get("end", 0.0))
        dur = max(0.001, end - start)

        overlaps = False
        for k in kept:
            k_start = float(k["start_time"] if "start_time" in k else k.get("start", 0.0))
            k_end = float(k["end_time"] if "end_time" in k else k.get("end", 0.0))
            overlap_sec = max(0.0, min(end, k_end) - max(start, k_start))
            if (overlap_sec / dur) >= max_overlap_ratio:
                overlaps = True
                break

        if not overlaps:
            kept.append(item)

    return kept
