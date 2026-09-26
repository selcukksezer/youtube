"""
Multi-Zone Subtitle Director.
Adapted and enhanced from lcy362/agnes-video-generator (core/screenwriter/style.py).
Breaks monotonic bottom-only subtitles by dynamically distributing lines across 3 vertical zones:
- TOP (\\an8): Opening hook, warning callouts, pattern interrupts.
- CENTER (\\an5): Dramatic climax, 1-word punchlines, revelatory questions.
- BOTTOM (\\an2): Standard narration and supporting context.
Generates styled ASS override tags to optimize viewer attention on mobile screens.
"""
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Dict, List, Optional


class SubtitleZone(str, Enum):
    TOP = "top"        # \an8: Top Center
    CENTER = "center"  # \an5: Middle Center
    BOTTOM = "bottom"  # \an2: Bottom Center


@dataclass
class StyledSubtitleLine:
    index: int
    text: str
    start_sec: float
    end_sec: float
    zone: SubtitleZone
    ass_alignment_tag: str
    font_size: int
    color_bgr_hex: str
    margin_v: int


class MultiZoneSubtitleDirector:
    """
    Plans multi-zone subtitle placement and generates ASS override codes.
    """

    def __init__(
        self,
        base_font_size: int = 50,
        hook_font_size: int = 62,
        center_font_size: int = 68,
        safe_margin_top: int = 140,
        safe_margin_bottom: int = 120,
    ):
        self.base_font_size = base_font_size
        self.hook_font_size = hook_font_size
        self.center_font_size = center_font_size
        self.safe_margin_top = safe_margin_top
        self.safe_margin_bottom = safe_margin_bottom

    def classify_line_zone(
        self,
        text: str,
        start_sec: float,
        end_sec: float,
        index: int,
        total_lines: int,
    ) -> SubtitleZone:
        """
        Determines the optimal vertical zone for a subtitle line.
        """
        clean_text = text.lower().strip()

        # Rule 1: First 2.0 seconds or hook line 0 -> TOP zone
        if start_sec < 2.0 or index == 0:
            return SubtitleZone.TOP

        # Rule 2: Short punchy climax or question -> CENTER zone
        words = clean_text.split()
        is_short_punch = len(words) <= 4 and any(punct in text for punct in ["!", "?", "..."])
        is_curiosity_peak = any(w in clean_text for w in ["peki", "neden", "asıl soru", "şok", "inanılmaz", "asla"])

        if (is_short_punch or is_curiosity_peak) and 0.25 <= (index / max(1, total_lines)) <= 0.85:
            return SubtitleZone.CENTER

        # Default narration -> BOTTOM zone
        return SubtitleZone.BOTTOM

    def plan_subtitle_styling(
        self,
        subtitles: List[Dict[str, Any]],
    ) -> List[StyledSubtitleLine]:
        """
        Processes raw subtitle entries and plans multi-zone layouts.
        """
        total = len(subtitles)
        styled_lines: List[StyledSubtitleLine] = []
        last_zone = SubtitleZone.BOTTOM

        for idx, sub in enumerate(subtitles):
            text = str(sub.get("text") or sub.get("content") or "").strip()
            start = float(sub.get("start", idx * 3.0))
            end = float(sub.get("end", start + 2.5))

            zone = self.classify_line_zone(text, start, end, idx, total)

            # Avoid keeping CENTER zone for 2 consecutive lines
            if zone == SubtitleZone.CENTER and last_zone == SubtitleZone.CENTER:
                zone = SubtitleZone.BOTTOM

            if zone == SubtitleZone.TOP:
                align = "\\an8"
                fs = self.hook_font_size
                color = "&H0000FFFF&"  # Vibrant Yellow (BGR)
                mv = self.safe_margin_top
            elif zone == SubtitleZone.CENTER:
                align = "\\an5"
                fs = self.center_font_size
                color = "&H00FFFF00&"  # Neon Cyan
                mv = 0
            else:
                align = "\\an2"
                fs = self.base_font_size
                color = "&H00FFFFFF&"  # Clean White
                mv = self.safe_margin_bottom

            styled_lines.append(
                StyledSubtitleLine(
                    index=idx + 1,
                    text=text,
                    start_sec=start,
                    end_sec=end,
                    zone=zone,
                    ass_alignment_tag=align,
                    font_size=fs,
                    color_bgr_hex=color,
                    margin_v=mv,
                )
            )
            last_zone = zone

        return styled_lines

    def format_ass_override_tag(self, line: StyledSubtitleLine) -> str:
        """
        Generates ASS inline override code like '{\\an8\\fs62\\c&H0000FFFF&}'.
        """
        return f"{{{line.ass_alignment_tag}\\fs{line.font_size}\\c{line.color_bgr_hex}}}"

    def to_ass_dialogue_line(self, line: StyledSubtitleLine) -> str:
        """
        Formats a complete ASS event dialogue line.
        """
        def _sec_to_ass(s: float) -> str:
            hrs = int(s // 3600)
            mins = int((s % 3600) // 60)
            secs = s % 60
            return f"{hrs:01d}:{mins:02d}:{secs:05.2f}"

        t_start = _sec_to_ass(line.start_sec)
        t_end = _sec_to_ass(line.end_sec)
        override = self.format_ass_override_tag(line)

        return f"Dialogue: 0,{t_start},{t_end},Default,,0,0,{line.margin_v},,{override}{line.text}"


multi_zone_subtitle_director = MultiZoneSubtitleDirector()
