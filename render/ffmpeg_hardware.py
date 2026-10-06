"""
render/ffmpeg_hardware.py — Hardware Acceleration Profiler & Encoder Selector.

Adapted and evolved from reference_repos2/NarratoAI (app/config/ffmpeg_config.py).
Detects GPU capabilities (NVIDIA NVENC, Apple VideoToolbox, Intel QuickSync, VAAPI)
and selects the optimal encoder profile with automatic software fallback to libx264.
"""

from __future__ import annotations

import os
import platform
import subprocess
from typing import Dict, List, Optional
import imageio_ffmpeg


class FFmpegHardwareDetector:
    """Detects available FFmpeg hardware acceleration encoders."""

    def __init__(self):
        self._cached_profile: Optional[str] = None
        self._ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def get_supported_encoders(self) -> List[str]:
        """Runs ffmpeg -encoders and extracts available video encoders."""
        try:
            res = subprocess.run(
                [self._ffmpeg_exe, "-hide_banner", "-encoders"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=True,
            )
            encoders = []
            for line in res.stdout.splitlines():
                if "V....." in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        encoders.append(parts[1])
            return encoders
        except Exception:
            return ["libx264"]

    def detect_best_encoder_profile(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Determines the fastest stable video encoder profile for current hardware:
        1. h264_nvenc (NVIDIA GPUs on Windows/Linux)
        2. h264_videotoolbox (Apple Silicon / Intel macOS)
        3. h264_qsv (Intel QuickSync)
        4. libx264 (Universal CPU fallback)
        """
        if self._cached_profile and not force_refresh:
            return self._cached_profile

        encoders = self.get_supported_encoders()
        sys_name = platform.system()

        # Priority 1: NVIDIA NVENC
        if "h264_nvenc" in encoders:
            profile = {
                "name": "nvidia_nvenc",
                "encoder": "h264_nvenc",
                "hwaccel": "cuda",
                "extra_args": ["-preset", "p4", "-rc", "vbr", "-cq", "25", "-spatial-aq", "1"],
                "is_hardware": True,
            }
        # Priority 2: Apple VideoToolbox
        elif sys_name == "Darwin" and "h264_videotoolbox" in encoders:
            profile = {
                "name": "apple_videotoolbox",
                "encoder": "h264_videotoolbox",
                "hwaccel": "videotoolbox",
                "extra_args": ["-q:v", "65"],
                "is_hardware": True,
            }
        # Priority 3: Intel QuickSync
        elif "h264_qsv" in encoders:
            profile = {
                "name": "intel_qsv",
                "encoder": "h264_qsv",
                "hwaccel": "qsv",
                "extra_args": ["-preset", "fast", "-global_quality", "25"],
                "is_hardware": True,
            }
        # Priority 4: Universal software CPU libx264
        else:
            profile = {
                "name": "universal_cpu",
                "encoder": "libx264",
                "hwaccel": None,
                "extra_args": ["-preset", "fast", "-crf", "22"],
                "is_hardware": False,
            }

        self._cached_profile = profile
        return profile


GLOBAL_HW_DETECTOR = FFmpegHardwareDetector()
