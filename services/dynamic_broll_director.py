"""
Dynamic B-Roll Timeline Director.
Adapted and enhanced from naqashafzal/AI-Content-Studio (pipeline_shorts.py).
Extracts, schedules, and overlays visual B-Roll cutaways onto talking-head / highlight clips
to prevent visual monotony and maximize viewer retention on YouTube Shorts & TikTok.
"""
from dataclasses import dataclass, field
import logging
import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class BRollCue:
    start_offset: float
    end_offset: float
    subject: str
    visual_query: str
    video_path: Optional[str] = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end_offset - self.start_offset)


class DynamicBRollDirector:
    """
    Plans and integrates retention-optimizing B-Roll cutaway overlays into vertical shorts.
    """

    def __init__(
        self,
        min_hook_protection_sec: float = 1.8,
        min_cue_duration_sec: float = 2.0,
        max_cue_duration_sec: float = 5.5,
        default_target_width: int = 1080,
        default_target_height: int = 1920,
    ):
        self.min_hook_protection_sec = min_hook_protection_sec
        self.min_cue_duration_sec = min_cue_duration_sec
        self.max_cue_duration_sec = max_cue_duration_sec
        self.target_width = default_target_width
        self.target_height = default_target_height

    def sanitize_cues(
        self,
        cues_raw: List[Dict[str, Any]],
        clip_duration: float,
    ) -> List[BRollCue]:
        """
        Validates, clamps, and cleans raw B-Roll suggestions from LLM.
        Guarantees:
        1. Does not overlap with the opening hook (first 1.8 seconds).
        2. Leaves breathing room at the end (at least 1.0s before clip ends).
        3. Cues are between 2.0s and 5.5s duration.
        4. Cues do not overlap with each other.
        """
        sanitized: List[BRollCue] = []
        last_end = self.min_hook_protection_sec

        for item in cues_raw:
            subject = str(item.get("subject", "")).strip().lower()
            if not subject or subject in ("none", "null", "talking", "speaker"):
                continue

            try:
                start = float(item.get("start_offset", 0.0))
                end = float(item.get("end_offset", start + 3.0))
            except (ValueError, TypeError):
                continue

            # Protect opening hook
            start = max(start, last_end + 0.5)
            # Duration clamping
            dur = max(self.min_cue_duration_sec, min(end - start, self.max_cue_duration_sec))
            end = start + dur

            # Protect clip tail
            if end > (clip_duration - 1.0):
                end = clip_duration - 1.0
                start = end - min(dur, self.min_cue_duration_sec)

            if start >= end or start < self.min_hook_protection_sec:
                continue

            query = str(item.get("visual_query") or subject).strip()
            # Clean up query for stock search
            clean_query = re.sub(r'[^a-zA-Z0-9\s]', '', query).strip()
            if not clean_query:
                clean_query = "cinematic atmospheric footage"

            cue = BRollCue(
                start_offset=round(start, 2),
                end_offset=round(end, 2),
                subject=subject,
                visual_query=clean_query,
                video_path=item.get("video_path"),
            )
            sanitized.append(cue)
            last_end = cue.end_offset

        return sanitized

    def plan_retention_broll(
        self,
        clip_duration: float,
        narration: str = "",
        explicit_cues: Optional[List[Dict[str, Any]]] = None,
    ) -> List[BRollCue]:
        """
        If explicit cues are provided, sanitizes them.
        Otherwise, if clip is long (>12s), generates algorithmic retention cutaways
        at high drop-off points (e.g. 25% and 65% timestamps).
        """
        if explicit_cues:
            sanitized = self.sanitize_cues(explicit_cues, clip_duration)
            if sanitized:
                return sanitized

        # Algorithmic fallback if no explicit cues but clip is long enough
        if clip_duration < 10.0:
            return []

        cues: List[BRollCue] = []
        words = [w for w in re.split(r'\W+', narration) if len(w) > 4]

        # First retention cutaway around 2.5s - 5.5s
        q1 = words[0] if words else "dramatic reveal"
        cues.append(
            BRollCue(
                start_offset=2.5,
                end_offset=min(5.5, clip_duration - 2.0),
                subject="opening_emphasis",
                visual_query=q1,
            )
        )

        # Second cutaway around midway if clip > 22s
        if clip_duration > 22.0:
            mid = round(clip_duration * 0.55, 1)
            q2 = words[min(len(words) - 1, 4)] if len(words) > 4 else "technology data"
            cues.append(
                BRollCue(
                    start_offset=mid,
                    end_offset=min(mid + 3.0, clip_duration - 1.5),
                    subject="midpoint_retention",
                    visual_query=q2,
                )
            )

        return cues

    def generate_ffmpeg_overlay_graph(
        self,
        broll_cues: List[BRollCue],
        width: int = 1080,
        height: int = 1920,
    ) -> Tuple[str, str]:
        """
        Constructs the FFmpeg -filter_complex string for overlaying multiple B-Roll clips.
        Each B-Roll input (indexed 1..N) is scaled/cropped to vertical 9:16 and overlaid
        with enable='between(t, start, end)'.
        
        Returns:
            (filter_complex_string, final_video_map_tag)
        """
        if not broll_cues:
            return "", "0:v"

        filter_steps: List[str] = []
        current_base = "0:v"

        for idx, cue in enumerate(broll_cues):
            in_idx = idx + 1
            # Scale broll to fill 9:16 vertical without distortion
            scale_tag = f"broll_scaled_{idx}"
            scale_filter = (
                f"[{in_idx}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}[{scale_tag}]"
            )
            filter_steps.append(scale_filter)

            out_tag = f"v_overlay_{idx}"
            overlay_filter = (
                f"[{current_base}][{scale_tag}]overlay=0:0:"
                f"enable='between(t,{cue.start_offset},{cue.end_offset})'[{out_tag}]"
            )
            filter_steps.append(overlay_filter)
            current_base = out_tag

        return ";".join(filter_steps), current_base


dynamic_broll_director = DynamicBRollDirector()
