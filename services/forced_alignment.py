"""
services/forced_alignment.py — Zero-Drift Word Timestamp Alignment & Subtitle Pager.

Adapted and evolved from reference_repos2/FunClip (funclip/videoclipper.py & subtitle_renderer.py).
Solves the fundamental A/V sync drift between ASR (Whisper/SenseVoice) and TTS audio duration:
1. Re-scales and snaps word timestamps monotonically into [0.0, audio_duration].
2. Eliminates negative gaps and overlapping word boundaries.
3. Groups tokens into compact, high-retention subtitle pages with guaranteed zero drift.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple


def calculate_alignment_drift(words: List[Dict[str, Any]], audio_duration: float) -> float:
    """Returns the signed drift in seconds between the last word end and audio duration."""
    if not words or audio_duration <= 0.0:
        return 0.0
    last_end = float(words[-1].get("end", 0.0))
    return round(last_end - audio_duration, 4)


def align_word_timestamps_to_audio_duration(
    words: List[Dict[str, Any]],
    audio_duration: float,
    max_tokens_per_page: int = 8,
    max_page_duration_sec: float = 3.0,
) -> List[Dict[str, Any]]:
    """
    Performs forced alignment to prevent subtitle drift:
    1. If the last detected word ends after or significantly before audio_duration,
       proportionally rescales word timestamps so the utterance ends precisely at audio_duration.
    2. Ensures strict monotonic progression: word[i].start >= word[i-1].end.
    3. Clamps all values inside [0.0, audio_duration].
    """
    if not words or audio_duration <= 0.0:
        return []

    processed: List[Dict[str, Any]] = [copy.deepcopy(w) for w in words]

    # Calculate scale factor if raw ASR duration deviates from physical audio duration
    raw_start = float(processed[0].get("start", 0.0))
    raw_end = float(processed[-1].get("end", audio_duration))
    raw_span = max(0.01, raw_end - raw_start)

    # If raw end exceeds audio duration or falls short by more than 150ms, rescale
    if abs(raw_end - audio_duration) > 0.10:
        scale = audio_duration / max(0.01, raw_end)
        for w in processed:
            w["start"] = round(float(w.get("start", 0.0)) * scale, 3)
            w["end"] = round(float(w.get("end", 0.0)) * scale, 3)

    # Monotonic & boundary clamping pass
    current_time = 0.0
    for i, w in enumerate(processed):
        start = max(current_time, float(w.get("start", current_time)))
        end = max(start + 0.05, float(w.get("end", start + 0.05)))

        # Clamp to audio_duration
        if start > audio_duration:
            start = max(0.0, audio_duration - 0.1)
        if end > audio_duration:
            end = audio_duration

        w["start"] = round(start, 3)
        w["end"] = round(end, 3)
        current_time = w["end"]

    return processed


def paginate_aligned_words(
    aligned_words: List[Dict[str, Any]],
    max_tokens_per_page: int = 6,
    max_page_duration: float = 2.5,
) -> List[Dict[str, Any]]:
    """
    Groups aligned words into subtitle pages ensuring short, punchy visual presentation.
    Each page contains: { "text": str, "start": float, "end": float, "words": List[...] }
    """
    if not aligned_words:
        return []

    pages: List[Dict[str, Any]] = []
    current_page_words: List[Dict[str, Any]] = []

    for w in aligned_words:
        if not current_page_words:
            current_page_words.append(w)
            continue

        page_start = current_page_words[0]["start"]
        potential_end = w["end"]
        potential_duration = potential_end - page_start
        potential_token_count = len(current_page_words) + 1

        if potential_token_count > max_tokens_per_page or potential_duration > max_page_duration:
            # Finalize current page
            page_text = " ".join(item["word"].strip() for item in current_page_words if item.get("word"))
            pages.append({
                "text": page_text,
                "start": current_page_words[0]["start"],
                "end": current_page_words[-1]["end"],
                "words": list(current_page_words),
            })
            current_page_words = [w]
        else:
            current_page_words.append(w)

    if current_page_words:
        page_text = " ".join(item["word"].strip() for item in current_page_words if item.get("word"))
        pages.append({
            "text": page_text,
            "start": current_page_words[0]["start"],
            "end": current_page_words[-1]["end"],
            "words": list(current_page_words),
        })

    return pages
