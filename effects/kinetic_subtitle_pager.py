"""
Kinetic Subtitle Pager.
Adapted from gyoridavid/short-video-maker (createCaptionPages & word-level highlight).

Converts raw Whisper word timestamps into punchy, 1-line dynamic subtitle pages
with active word pill highlights, optimal mobile reading bounds, and ASS karaoke export.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class KineticWord:
    word: str
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        return max(10, self.end_ms - self.start_ms)

    @property
    def duration_cs(self) -> int:
        """Centiseconds for ASS \\k karaoke tags."""
        return max(1, round(self.duration_ms / 10.0))


@dataclass
class KineticPage:
    page_index: int
    start_ms: int
    end_ms: int
    words: List[KineticWord] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.word for w in self.words)

    @property
    def start_time_ass(self) -> str:
        return self._ms_to_ass_time(self.start_ms)

    @property
    def end_time_ass(self) -> str:
        return self._ms_to_ass_time(self.end_ms)

    @staticmethod
    def _ms_to_ass_time(ms: int) -> str:
        total_sec = ms / 1000.0
        hrs = int(total_sec // 3600)
        rem = total_sec % 3600
        mins = int(rem // 60)
        secs = rem % 60
        return f"{hrs:d}:{mins:02d}:{secs:05.2f}"

    def to_ass_dialogue(
        self,
        style_name: str = "Default",
        highlight_bgr: str = "&H00D7FF&",  # Yellow in ASS BGR format
        normal_bgr: str = "&HFFFFFF&",     # White in ASS BGR format
        bounce: bool = False,
    ) -> str:
        """Generates ASS karaoke dialogue line with sequential word highlighting and optional bounce pop."""
        karaoke_parts = []
        for w in self.words:
            tag = f"{{\\k{w.duration_cs}\\t(0,70,\\fscx115\\fscy115)\\t(70,140,\\fscx100\\fscy100)}}" if bounce else f"{{\\k{w.duration_cs}}}"
            karaoke_parts.append(f"{tag}{w.word}")
        karaoke_text = " ".join(karaoke_parts)
        return f"Dialogue: 0,{self.start_time_ass},{self.end_time_ass},{style_name},,0,0,0,,{karaoke_text}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_index": self.page_index,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "text": self.text,
            "words": [
                {
                    "word": w.word,
                    "start_ms": w.start_ms,
                    "end_ms": w.end_ms,
                    "duration_ms": w.duration_ms,
                }
                for w in self.words
            ],
        }


class KineticSubtitlePager:
    """Partitions word-level timestamps into rapid 1-line mobile subtitle cards."""

    def __init__(
        self,
        line_max_length: int = 22,
        max_distance_ms: int = 1000,
        highlight_color: str = "#FFD700",
        background_pill_color: str = "#0055FF",
    ):
        self.line_max_length = line_max_length
        self.max_distance_ms = max_distance_ms
        self.highlight_color = highlight_color
        self.background_pill_color = background_pill_color

    def create_pages(self, raw_words: List[Dict[str, Any]]) -> List[KineticPage]:
        """
        Groups words into single-line pages based on max characters and silence gaps.
        raw_words schema: [{"word": str, "start": float (seconds), "end": float (seconds)}]
        or: [{"word": str, "start_ms": int, "end_ms": int}]
        """
        if not raw_words:
            return []

        # Normalize words to ms
        normalized_words: List[KineticWord] = []
        for rw in raw_words:
            w_text = str(rw.get("word") or rw.get("text") or "").strip()
            if not w_text:
                continue

            if "start_ms" in rw:
                s_ms = int(rw["start_ms"])
                e_ms = int(rw.get("end_ms", s_ms + 300))
            else:
                s_ms = int(round(float(rw.get("start", 0.0)) * 1000))
                e_ms = int(round(float(rw.get("end", (s_ms / 1000.0) + 0.3)) * 1000))

            normalized_words.append(KineticWord(word=w_text, start_ms=s_ms, end_ms=max(s_ms + 10, e_ms)))

        if not normalized_words:
            return []

        pages: List[KineticPage] = []
        curr_page = KineticPage(
            page_index=0,
            start_ms=normalized_words[0].start_ms,
            end_ms=normalized_words[0].end_ms,
            words=[],
        )

        for w in normalized_words:
            # Check for pause gap to start a new page
            is_gap = curr_page.words and (w.start_ms - curr_page.end_ms > self.max_distance_ms)

            # Check if current line exceeds line_max_length
            current_len = sum(len(kw.word) for kw in curr_page.words) + len(curr_page.words)
            is_full = curr_page.words and (current_len + len(w.word) > self.line_max_length)

            if is_gap or is_full:
                pages.append(curr_page)
                curr_page = KineticPage(
                    page_index=len(pages),
                    start_ms=w.start_ms,
                    end_ms=w.end_ms,
                    words=[w],
                )
            else:
                curr_page.words.append(w)
                curr_page.end_ms = max(curr_page.end_ms, w.end_ms)

        if curr_page.words:
            pages.append(curr_page)

        return pages

    def generate_ass_dialogues(self, pages: List[KineticPage]) -> List[str]:
        """Exports ASS dialogue event lines."""
        return [p.to_ass_dialogue() for p in pages]


kinetic_subtitle_pager = KineticSubtitlePager()
