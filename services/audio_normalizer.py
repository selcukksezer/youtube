"""
services/audio_normalizer.py — Two-Pass EBU R128 (-14 LUFS) Audio Normalizer & Ducking Engine.

Adapted and evolved from reference_repos2/NarratoAI (app/services/audio_normalizer.py & audio_merger.py).
Solves single-pass loudnorm pumping artifacts by:
1. Pass 1: Analyzing input audio integrated loudness, true peak, LRA, and threshold via FFmpeg JSON stderr output.
2. Pass 2: Applying linear true normalization tailored specifically for YouTube Shorts / TikTok (-14.0 LUFS, -1.5 dBTP).
3. Ducking BGM filter generation for clean multi-track vocal hierarchy.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Any, Dict, Optional

import imageio_ffmpeg

logger = logging.getLogger("AudioNormalizer")

# Default broadcast & streaming targets
SHORTS_TARGET_LUFS = -14.0
SHORTS_MAX_PEAK = -1.5
SHORTS_LRA = 7.0


class AudioNormalizer:
    """Two-pass EBU R128 loudness analysis and normalization."""

    def __init__(
        self,
        target_lufs: float = SHORTS_TARGET_LUFS,
        max_peak: float = SHORTS_MAX_PEAK,
        target_lra: float = SHORTS_LRA,
    ):
        self.target_lufs = target_lufs
        self.max_peak = max_peak
        self.target_lra = target_lra
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def parse_loudnorm_json_from_stderr(self, stderr_text: str) -> Optional[Dict[str, float]]:
        """Extracts and parses loudnorm JSON statistics block from FFmpeg stderr output."""
        if not stderr_text:
            return None

        # Look for the last JSON object block in stderr
        match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr_text, re.DOTALL)
        if not match:
            # Fallback line-by-line parser
            lines = stderr_text.splitlines()
            buf = []
            capturing = False
            for line in lines:
                if line.strip() == "{":
                    capturing = True
                    buf = [line]
                elif capturing:
                    buf.append(line)
                    if line.strip() == "}":
                        break
            if not buf:
                return None
            json_str = "\n".join(buf)
        else:
            json_str = match.group(0)

        try:
            data = json.loads(json_str)
            return {
                "input_i": float(data.get("input_i", 0.0)),
                "input_tp": float(data.get("input_tp", 0.0)),
                "input_lra": float(data.get("input_lra", 0.0)),
                "input_thresh": float(data.get("input_thresh", 0.0)),
                "target_offset": float(data.get("target_offset", 0.0)),
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse loudnorm JSON: {e}")
            return None

    def analyze_audio_lufs(self, audio_path: str) -> Optional[Dict[str, float]]:
        """
        Runs First Pass FFmpeg analysis without generating output media (-f null -).
        Returns measured input_i, input_tp, input_lra, input_thresh, target_offset.
        """
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return None

        cmd = [
            self.ffmpeg_exe,
            "-hide_banner",
            "-nostats",
            "-i", audio_path,
            "-af", f"loudnorm=I={self.target_lufs}:TP={self.max_peak}:LRA={self.target_lra}:print_format=json",
            "-f", "null",
            "-",
        ]

        try:
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False)
            return self.parse_loudnorm_json_from_stderr(proc.stderr)
        except Exception as e:
            logger.error(f"First-pass loudnorm analysis failed: {e}")
            return None

    def build_two_pass_loudnorm_filter(self, measured: Dict[str, float]) -> str:
        """
        Constructs Second Pass FFmpeg filter using the exact measured parameters.
        Prevents dynamic gain pumping and delivers precise -14.0 LUFS.
        """
        return (
            f"loudnorm=I={self.target_lufs}:TP={self.max_peak}:LRA={self.target_lra}:"
            f"measured_I={measured['input_i']:.2f}:"
            f"measured_TP={measured['input_tp']:.2f}:"
            f"measured_LRA={measured['input_lra']:.2f}:"
            f"measured_thresh={measured['input_thresh']:.2f}:"
            f"offset={measured.get('target_offset', 0.0):.2f}:"
            f"linear=true"
        )

    def normalize_audio_file(self, input_path: str, output_path: str) -> bool:
        """
        Performs full two-pass EBU R128 audio normalization.
        """
        stats = self.analyze_audio_lufs(input_path)
        if not stats:
            # Fallback to single-pass if first-pass analysis produced no stats
            logger.warning("First pass failed, falling back to single-pass loudnorm")
            filter_str = f"loudnorm=I={self.target_lufs}:TP={self.max_peak}:LRA={self.target_lra}"
        else:
            filter_str = self.build_two_pass_loudnorm_filter(stats)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-hide_banner",
            "-i", input_path,
            "-af", filter_str,
            "-ar", "44100",
            "-ac", "2",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path,
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception as e:
            logger.error(f"Audio normalization render failed: {e}")
            return False

    @staticmethod
    def build_ducking_filter(
        voice_label: str = "[0:a]",
        bgm_label: str = "[1:a]",
        output_label: str = "[aout]",
        duck_volume: float = 0.20,
    ) -> str:
        """
        Builds FFmpeg filter complex expression to mix voiceover with background music,
        attenuating BGM to specified relative volume while voice is playing.
        """
        return (
            f"{bgm_label}volume={duck_volume:.2f}[bgm_ducked];"
            f"{voice_label}[bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2{output_label}"
        )


GLOBAL_AUDIO_NORMALIZER = AudioNormalizer()
