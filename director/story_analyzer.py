"""
director/story_analyzer.py — Dramatic Tension Arc & Narrative Velocity Analyzer.

Adapted and evolved from reference_repos2/dramaclaw (src/novelvideo/story_analysis.py).
Analyzes script pacing, emotional intensity, and tension progression across scenes
to optimize shot durations and audio impact points.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


_HIGH_TENSION_KEYWORDS = {
    "shock", "secret", "danger", "deadly", "crisis", "warning", "never", "suddenly",
    "tehlike", "şok", "gizli", "korkunç", "asla", "dikkat", "patlama", "ölümcül",
    "kriz", "ihanet", "bomba", "cinayet", "gizem", "panik", "acil",
}

_TRANSITION_KEYWORDS = {
    "however", "meanwhile", "then", "later", "because", "therefore",
    "oysa", "ancak", "fakat", "derken", "ardından", "çünkü", "bu yüzden",
}


@dataclass
class SceneTensionMetrics:
    scene_index: int
    text: str
    word_count: int
    tension_score: float  # 0.0 (calm exposition) to 1.0 (climax peak)
    recommended_shot_duration: float  # seconds
    beat_category: str  # "hook", "exposition", "escalation", "climax", "resolution"


class StoryArcAnalyzer:
    """Evaluates the dramatic tension curve and pacing across script scenes."""

    @staticmethod
    def calculate_scene_tension(scene_index: int, total_scenes: int, text: str) -> float:
        """
        Calculates normalized tension score [0.0, 1.0] based on:
        - Structural position (hook at start, climax near 80%, resolution at end)
        - Lexical tension keywords
        - Punctuation cues (exclamations, questions)
        """
        if not text:
            return 0.2

        text_lower = text.lower()
        words = re.findall(r"\w+", text_lower)
        word_count = len(words)
        if word_count == 0:
            return 0.2

        # 1. Lexical cues
        tension_word_count = sum(1 for w in words if w in _HIGH_TENSION_KEYWORDS)
        lexical_factor = min(0.4, (tension_word_count / max(1, word_count)) * 2.0)

        # 2. Punctuation intensity
        exclamation_count = text.count("!")
        question_count = text.count("?")
        punct_factor = min(0.3, (exclamation_count * 0.15) + (question_count * 0.10))

        # 3. Positional structural baseline (Hook -> Build -> Climax -> Resolution)
        pos_ratio = scene_index / max(1, total_scenes - 1)
        if scene_index == 0:
            pos_factor = 0.45  # Hook
        elif pos_ratio >= 0.70 and pos_ratio <= 0.90:
            pos_factor = 0.50  # Climax zone
        elif pos_ratio > 0.90:
            pos_factor = 0.25  # Resolution
        else:
            pos_factor = 0.20 + (pos_ratio * 0.25)  # Rising action

        raw_score = pos_factor + lexical_factor + punct_factor
        return round(max(0.1, min(1.0, raw_score)), 2)

    @classmethod
    def analyze_story_arc(cls, scenes_text: List[str]) -> List[SceneTensionMetrics]:
        """Analyzes a sequence of scene texts and returns tension metrics."""
        total = len(scenes_text)
        results: List[SceneTensionMetrics] = []

        for idx, text in enumerate(scenes_text):
            score = cls.calculate_scene_tension(idx, total, text)
            words = len(re.findall(r"\w+", text))

            # Determine beat category
            if idx == 0:
                category = "hook"
            elif score >= 0.75:
                category = "climax"
            elif score >= 0.50:
                category = "escalation"
            elif idx == total - 1:
                category = "resolution"
            else:
                category = "exposition"

            # Recommend dynamic shot duration (higher tension = faster pacing)
            if category in ("hook", "climax"):
                rec_duration = max(2.5, min(4.0, 1.5 + (words * 0.25)))
            else:
                rec_duration = max(3.5, min(6.0, 2.0 + (words * 0.35)))

            results.append(SceneTensionMetrics(
                scene_index=idx,
                text=text,
                word_count=words,
                tension_score=score,
                recommended_shot_duration=round(rec_duration, 2),
                beat_category=category,
            ))

        return results


GLOBAL_STORY_ANALYZER = StoryArcAnalyzer()
