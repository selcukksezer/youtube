"""
services/gameplay_background_manager.py — Non-Repetitive Gameplay/ASMR Background Chooser & Asset Manager.

Adapted and evolved from reference_repos2/RedditVideoMakerBot (video_creation/background.py).
Solves:
1. Infinite loop / crash when background video is shorter than required clip length.
2. Cross-render segment repetition by maintaining an interval history database.
3. Seamless looping fallback for short clips.
4. Seamless integration with gameplay_pool.py categories, disk cache, and procedural fallback.
"""

from __future__ import annotations

import os
import random
import subprocess
from typing import Callable, Dict, List, Optional, Tuple

import imageio_ffmpeg

GAMEPLAY_CATEGORIES: Dict[str, str] = {
    "auto": "Otomatik (Nişe Göre)",
    "minecraft_parkour": "Minecraft Parkur",
    "subway_surfers_style": "Subway Surfers",
    "gta_car_ramp": "GTA V Dublör / Araba Rampası",
    "asmr_kinetic_sand": "Kinetik Kum / ASMR",
    "soap_cutting": "Sabun Kesme / Tatmin Edici",
    "mobile_game": "Genel Mobil Oyun",
}

NICHE_DEFAULT_GAMEPLAY: Dict[str, str] = {
    "11_reddit_stories": "subway_surfers_style",
    "2_reddit_confessions": "subway_surfers_style",
    "3_split_gameplay": "subway_surfers_style",
    "4_would_you_rather": "minecraft_parkour",
    "2_philosophy_stoic": "asmr_kinetic_sand",
    "6_psychology_tricks": "minecraft_parkour",
    "8_survival_myth": "gta_car_ramp",
    "9_five_facts": "soap_cutting",
    "10_fitness_biohack": "minecraft_parkour",
    "13_crypto_finance": "gta_car_ramp",
    "14_mysterious_cases": "asmr_kinetic_sand",
}


class GameplayBackgroundManager:
    """Manages long background video assets (Minecraft parkour, Subway Surfers, ASMR soap cutting)."""

    def __init__(self):
        self.used_history: List[Tuple[float, float]] = []

    def resolve_category(self, category: Optional[str] = None, niche: Optional[str] = None) -> str:
        cat = (category or "").strip().lower()
        if cat and cat in GAMEPLAY_CATEGORIES and cat != "auto":
            return cat
        if niche and niche in NICHE_DEFAULT_GAMEPLAY:
            return NICHE_DEFAULT_GAMEPLAY[niche]
        return "mobile_game"

    def get_safe_background_interval(
        self,
        video_length: float,
        target_clip_length: float,
        buffer_margin: float = 5.0,
    ) -> Tuple[float, float, bool]:
        """
        Calculates safe start and end timestamps.
        Returns (start_sec, end_sec, needs_loop).
        """
        video_len = float(video_length)
        clip_len = float(target_clip_length)

        if video_len <= 0 or clip_len <= 0:
            return 0.0, max(clip_len, 1.0), True

        # Case 1: Video is shorter than required clip -> Looping required
        if video_len <= clip_len:
            return 0.0, video_len, True

        # Case 2: Video is longer -> Select randomized non-repetitive window
        max_start = video_len - clip_len
        if max_start <= buffer_margin:
            return 0.0, clip_len, False

        # Attempt to find an interval not overlapping recent renders
        chosen_start = 0.0
        found = False

        for _ in range(15):
            candidate = round(random.uniform(0.0, max_start), 2)
            cand_end = candidate + clip_len

            # Check overlap with recent intervals (>60% overlap rejected)
            is_overlapping = False
            for u_start, u_end in self.used_history[-10:]:
                overlap_start = max(candidate, u_start)
                overlap_end = min(cand_end, u_end)
                overlap = max(0.0, overlap_end - overlap_start)
                if overlap / clip_len > 0.60:
                    is_overlapping = True
                    break

            if not is_overlapping:
                chosen_start = candidate
                found = True
                break

        if not found:
            chosen_start = round(random.uniform(0.0, max_start), 2)

        interval = (chosen_start, round(chosen_start + clip_len, 2))
        self.used_history.append(interval)
        if len(self.used_history) > 50:
            self.used_history.pop(0)

        return interval[0], interval[1], False

    def get_gameplay_clip(
        self,
        project_dir: str,
        category: str = "auto",
        niche: Optional[str] = None,
        target_duration: float = 30.0,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Optional[str]:
        """
        Fetches or creates a gameplay video asset for split-screen rendering.
        1. Checks local cache (assets/gameplay_pool/<category>).
        2. Queries stock providers via gameplay_pool.py.
        3. If all else fails, generates a procedural satisfying loop to ensure render safety.
        """
        resolved = self.resolve_category(category, niche)
        os.makedirs(project_dir, exist_ok=True)

        try:
            import gameplay_pool
            clip = gameplay_pool.fetch_gameplay_clip(
                project_dir=project_dir,
                category=resolved,
                niche=niche,
                target_duration=target_duration,
                cancel_check=cancel_check,
            )
            if clip and os.path.exists(clip) and os.path.getsize(clip) > 5000:
                return clip
        except Exception as exc:
            print(f"  [GameplayBackgroundManager] Pool search notice: {exc}")

        # Check existing project directory or assets directory for any existing gameplay files
        for search_dir in [
            os.path.join("assets", "gameplay_pool", resolved),
            os.path.join("assets", "gameplay_pool"),
            project_dir,
        ]:
            if os.path.isdir(search_dir):
                for f in os.listdir(search_dir):
                    if f.lower().endswith((".mp4", ".mov", ".webm")):
                        candidate = os.path.join(search_dir, f)
                        if os.path.getsize(candidate) > 10000:
                            return candidate

        # Robust procedural fallback: generate a 1080x960 satisfying ambient motion loop
        return self.generate_procedural_gameplay_clip(project_dir, target_duration)

    def generate_procedural_gameplay_clip(self, project_dir: str, duration: float = 15.0) -> str:
        """
        Generates a 1080x960 smooth procedural satisfying ambient video clip
        as a fallback when external gameplay clips cannot be downloaded.
        """
        out_path = os.path.join(project_dir, "gameplay_procedural_fallback.mp4")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            return out_path

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        dur = max(5.0, min(60.0, float(duration)))
        # Generates a sleek, dark neon moving wave procedural canvas (satisfying/asmr aesthetic)
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"mandelbrot=size=1080x960:rate=30:maxiter=120,hue=H=2*PI*t/12:s=0.65",
            "-t", f"{dur:.2f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            out_path
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=25)
            if res.returncode == 0 and os.path.exists(out_path):
                return out_path
        except Exception:
            pass

        # Ultra-light fallback if mandelbrot filter unavailable
        cmd_simple = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"testsrc=size=1080x960:rate=30,boxblur=20:5",
            "-t", f"{dur:.2f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            out_path
        ]
        try:
            subprocess.run(cmd_simple, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            if os.path.exists(out_path):
                return out_path
        except Exception:
            pass

        return out_path

    def build_extract_background_filter(
        self,
        start_time: float,
        duration: float,
        needs_loop: bool = False,
        target_width: int = 1080,
        target_height: int = 1920,
    ) -> str:
        """
        Constructs single-pass FFmpeg trim, scale, and crop filter graph.
        """
        if needs_loop:
            return (
                f"loop=loop=-1:size=32767:start=0,"
                f"trim=duration={duration:.2f},"
                f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
                f"crop={target_width}:{target_height},"
                f"setpts=PTS-STARTPTS"
            )

        return (
            f"trim=start={start_time:.2f}:duration={duration:.2f},"
            f"setpts=PTS-STARTPTS,"
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height}"
        )


GLOBAL_BACKGROUND_MANAGER = GameplayBackgroundManager()
