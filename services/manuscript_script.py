"""Convert an existing narration manuscript into a scene-based Shorts plan."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?。！？])\s+|\n+")
_WORDS_PER_SECOND = {"tr": 2.45, "en": 2.7}
_MIN_SCENE_SECONDS = 3.5
_MAX_SCENE_SECONDS = 8.0
MAX_MANUSCRIPT_SCENES = 24


class ManuscriptSegmentationError(ValueError):
    """Raised when a manuscript cannot safely become a bounded scene plan."""


def _estimate_duration(text: str, language: str) -> float:
    words = len(text.split())
    return words / _WORDS_PER_SECOND[language]


def split_manuscript_text(text: str, language: str = "tr") -> List[str]:
    """Split text at sentence boundaries, keeping narration wording unchanged."""
    normalized_language = (language or "tr").strip().lower()
    if normalized_language not in _WORDS_PER_SECOND:
        raise ManuscriptSegmentationError("Manuscript language must be 'tr' or 'en'.")

    source = (text or "").strip()
    if not source:
        raise ManuscriptSegmentationError("Manuscript text is required.")

    sentences = [
        " ".join(sentence.split())
        for sentence in _SENTENCE_BOUNDARY.split(source)
        if sentence.strip()
    ]
    if not sentences:
        raise ManuscriptSegmentationError("Manuscript text contains no readable sentences.")

    segments: List[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if current and _estimate_duration(candidate, normalized_language) > _MAX_SCENE_SECONDS:
            segments.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        segments.append(current)

    if len(segments) > 1 and _estimate_duration(segments[-1], normalized_language) < _MIN_SCENE_SECONDS:
        combined = f"{segments[-2]} {segments[-1]}"
        if _estimate_duration(combined, normalized_language) <= _MAX_SCENE_SECONDS:
            segments[-2:] = [combined]

    if len(segments) > MAX_MANUSCRIPT_SCENES:
        raise ManuscriptSegmentationError(
            f"Manuscript creates {len(segments)} scenes; shorten it to {MAX_MANUSCRIPT_SCENES} scenes or fewer."
        )
    return segments


def build_manuscript_plan(
    text: str,
    title: Optional[str] = None,
    language: str = "tr",
    niche_id: str = "1_news_flash",
) -> Dict[str, Any]:
    """Create a legacy-compatible scene plan without rewriting the source script."""
    segments = split_manuscript_text(text, language=language)
    clean_title = (title or "").strip()
    if not clean_title:
        clean_title = re.split(r"(?<=[.!?。！？])\s+", segments[0], maxsplit=1)[0][:120].strip()

    scenes = [
        {
            "scene_number": index,
            "narration": segment,
            "duration": round(max(1.0, _estimate_duration(segment, language)), 2),
            "scene_description": segment,
            "search_queries": [],
        }
        for index, segment in enumerate(segments, start=1)
    ]
    return {
        "title": clean_title,
        "topic": clean_title,
        "keyword": clean_title,
        "full_narration": " ".join(segments),
        "language": language,
        "niche_id": niche_id,
        "scenes": scenes,
        "manuscript_import": {
            "scene_count": len(scenes),
            "estimated_duration": round(sum(scene["duration"] for scene in scenes), 2),
            "max_scene_seconds": _MAX_SCENE_SECONDS,
        },
    }
