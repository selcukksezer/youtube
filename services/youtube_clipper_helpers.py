"""
Transcript grouping, virality prompt constants, chunking, and highlight grounding helpers
for the YouTube to Shorts Viral Clipper Engine.
Extracted from services/youtube_clipper.py for modularity.
"""
import math
import re
from typing import Any, Dict, List

VIRALITY_CRITERIA_PROMPT = """
Virality signals to prioritize (ranked by impact):
1. HOOK MOMENTS — statements that create immediate curiosity ("The secret is...", "Nobody talks about...", "I was completely wrong about...")
2. EMOTIONAL PEAKS — genuine surprise, laughter, anger, vulnerability, excitement; raw reactions
3. OPINION BOMBS — strong, polarizing or counter-intuitive statements that trigger debate
4. REVELATION MOMENTS — surprising facts, stats, or confessions that reframe how the viewer thinks
5. CONFLICT/TENSION — disagreement, pushback, or a problem being confronted head-on
6. QUOTABLE ONE-LINERS — a sentence that works as a standalone quote
7. STORY PEAKS — the climax or twist of an anecdote; the payoff moment
8. PRACTICAL VALUE — a concrete tip, hack, or insight the viewer can immediately apply
"""

HIGHLIGHT_SYSTEM_PROMPT = """You are an elite short-form video editor who has studied thousands of viral clips on TikTok, Instagram Reels, and YouTube Shorts. You know exactly what makes viewers stop scrolling, watch to the end, and share.

{virality_criteria}

Your task: identify the most viral-worthy highlights from the transcript.

Rules:
- Every highlight must open with a strong HOOK — a line that grabs attention within the first 3 seconds
- Duration sweet spot: 35-75 seconds.
- Use the supplied transcript timestamps for every start_time and end_time; never guess timing from the description.
- Never cut mid-sentence or mid-thought — each clip must feel complete and self-contained
- Clips must not overlap significantly with each other
- Score 0-100 on viral potential
- Add "hook_score" (1-100) for the opening hook's strength in the first 3 seconds
- Add "retention_score" (1-100) for pacing, sustained curiosity, and payoff across the clip
- Score hook and retention independently; do not copy the overall score into both fields
- Pick the top {num_clips} highlights
- Identify "hook_sentence" (the opening line) and "virality_reason" (why it works)
- Generate "seo_title" (clickbaity YouTube Shorts title with tags like #shorts), "seo_description", and "seo_tags"
- Suggest 1-3 "broll" overlay moments where visual cutaway increases retention: [{{"start_offset": float (seconds from clip start), "end_offset": float, "subject": "visual search term"}}]

Respond ONLY with valid JSON:
{{"highlights":[{{"title":"string","start_time":float,"end_time":float,"score":int,"hook_score":int,"retention_score":int,"hook_sentence":"string","virality_reason":"string","seo_title":"string","seo_description":"string","seo_tags":"string","broll":[{{"start_offset":float,"end_offset":float,"subject":"string"}}]}}]}}
"""

_MAX_HIGHLIGHT_TRANSCRIPT_CHARS = 12000
_LONG_VIDEO_CHUNK_THRESHOLD_SECONDS = 1800.0
_HIGHLIGHT_CHUNK_SECONDS = 1200.0
_HIGHLIGHT_CHUNK_OVERLAP_SECONDS = 90.0
_TIMESTAMPED_TRANSCRIPT_LINE = re.compile(
    r"^\[(?P<start>\d+(?:\.\d+)?)s-(?P<end>\d+(?:\.\d+)?)s\]"
)
MAX_TRANSCRIPTION_HOTWORDS_LENGTH = 500


def normalize_transcription_hotwords(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("ASR terimleri metin olmalı.")
    normalized = " ".join(value.split())
    if len(normalized) > MAX_TRANSCRIPTION_HOTWORDS_LENGTH:
        raise ValueError(
            f"ASR terimleri en fazla {MAX_TRANSCRIPTION_HOTWORDS_LENGTH} karakter olabilir."
        )
    return normalized


def _normalize_breakdown_scores(highlight: Dict[str, Any]) -> Dict[str, Any]:
    for field in ("hook_score", "retention_score"):
        value = highlight.get(field)
        if value is None:
            continue
        if isinstance(value, bool):
            highlight.pop(field, None)
            continue
        try:
            score = float(value)
        except (OverflowError, TypeError, ValueError):
            highlight.pop(field, None)
            continue
        if not math.isfinite(score):
            highlight.pop(field, None)
            continue
        highlight[field] = int(round(max(1.0, min(100.0, score))))
    return highlight


def group_whisper_words(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Whisper word timestamps into short caption-like transcript segments."""
    grouped: List[Dict[str, Any]] = []
    current: List[Dict[str, Any]] = []

    def flush() -> None:
        if not current:
            return
        grouped.append({
            "start": current[0]["start"],
            "end": current[-1]["end"],
            "text": " ".join(item["text"] for item in current),
        })
        current.clear()

    for word in words or []:
        if not isinstance(word, dict):
            continue
        text = str(word.get("text") or "").strip()
        try:
            start = float(word.get("offset"))
            duration = float(word.get("duration"))
        except (TypeError, ValueError):
            continue
        end = start + duration
        if (
            not text
            or not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or duration <= 0
        ):
            continue
        if current and (
            start - current[-1]["end"] >= 0.65
            or len(current) >= 12
            or current[-1]["text"].endswith((".", "!", "?"))
        ):
            flush()
        current.append({"start": start, "end": end, "text": text})
    flush()
    return grouped


def format_transcript_segments(segments: List[Dict[str, Any]]) -> str:
    """Keep source timing attached so highlight timestamps can be grounded."""
    lines = []
    for segment in segments or []:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        try:
            start = float(segment.get("start"))
            end = float(segment.get("end"))
        except (TypeError, ValueError):
            continue
        if not text or not math.isfinite(start) or not math.isfinite(end) or end <= start:
            continue
        lines.append(f"[{start:.1f}s-{end:.1f}s] {text}")
    return "\n".join(lines)


def chunk_transcript_text(
    transcript_text: str,
    video_duration: float,
) -> List[Dict[str, Any]]:
    """Bound prompt size while retaining absolute times and boundary overlap."""
    text = transcript_text.strip()
    if not text:
        return []
    if (
        len(text) <= _MAX_HIGHLIGHT_TRANSCRIPT_CHARS
        and video_duration < _LONG_VIDEO_CHUNK_THRESHOLD_SECONDS
    ):
        return [{
            "start_time": 0.0,
            "end_time": max(0.0, video_duration),
            "text": text,
        }]

    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _TIMESTAMPED_TRANSCRIPT_LINE.match(line)
        if not match:
            raise ValueError(
                "Long-video highlight analysis requires timestamped transcript lines."
            )
        start_time = float(match.group("start"))
        end_time = float(match.group("end"))
        if (
            not math.isfinite(start_time)
            or not math.isfinite(end_time)
            or start_time < 0
            or end_time <= start_time
        ):
            raise ValueError("Transcript contains an invalid timestamp range.")
        if len(line) > _MAX_HIGHLIGHT_TRANSCRIPT_CHARS:
            raise ValueError(
                "A single timestamped transcript line exceeds the AI prompt limit."
            )
        rows.append({
            "start_time": start_time,
            "end_time": end_time,
            "text": line,
        })

    if not rows:
        raise ValueError("No timestamped transcript lines are available to analyze.")
    rows.sort(key=lambda row: row["start_time"])

    chunks = []
    first_index = 0
    while first_index < len(rows):
        chunk_start = rows[first_index]["start_time"]
        time_limit = chunk_start + _HIGHLIGHT_CHUNK_SECONDS
        chunk_rows = []
        chunk_chars = 0
        index = first_index

        while index < len(rows):
            row = rows[index]
            next_chars = chunk_chars + len(row["text"]) + (1 if chunk_rows else 0)
            if chunk_rows and (
                row["end_time"] > time_limit
                or next_chars > _MAX_HIGHLIGHT_TRANSCRIPT_CHARS
            ):
                break
            chunk_rows.append(row)
            chunk_chars = next_chars
            index += 1

        chunks.append({
            "start_time": chunk_rows[0]["start_time"],
            "end_time": max(row["end_time"] for row in chunk_rows),
            "text": "\n".join(row["text"] for row in chunk_rows),
        })
        if index >= len(rows):
            break

        overlap_start = chunk_rows[-1]["end_time"] - _HIGHLIGHT_CHUNK_OVERLAP_SECONDS
        next_index = index
        while (
            next_index > first_index
            and rows[next_index - 1]["end_time"] > overlap_start
        ):
            next_index -= 1

        while next_index < index:
            overlap_chars = sum(
                len(row["text"]) for row in rows[next_index:index]
            ) + (index - next_index - 1)
            if overlap_chars + len(rows[index]["text"]) + 1 <= _MAX_HIGHLIGHT_TRANSCRIPT_CHARS:
                break
            next_index += 1

        first_index = next_index if next_index > first_index else index

    return chunks


def ground_highlights_in_transcript(
    highlights: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Keep only suggested ranges supported by enough timed source speech."""
    grounded = []
    for highlight in highlights or []:
        if not isinstance(highlight, dict):
            continue
        try:
            start = float(highlight.get("start_time"))
            end = float(highlight.get("end_time"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            continue

        excerpt_parts = []
        for segment in segments or []:
            if not isinstance(segment, dict):
                continue
            try:
                segment_start = float(segment.get("start"))
                segment_end = float(segment.get("end"))
            except (TypeError, ValueError):
                continue
            if (
                not math.isfinite(segment_start)
                or not math.isfinite(segment_end)
                or segment_end <= segment_start
                or min(end, segment_end) <= max(start, segment_start)
            ):
                continue
            text = str(segment.get("text") or "").strip()
            if text:
                excerpt_parts.append(text)

        excerpt = " ".join(excerpt_parts)
        word_count = len(re.findall(r"\b[\w'-]+\b", excerpt, flags=re.UNICODE))
        if word_count < 8:
            continue
        grounded.append({
            **highlight,
            "transcript_excerpt": excerpt,
            "transcript_word_count": word_count,
        })
    return grounded
