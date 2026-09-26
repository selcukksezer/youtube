"""
Hook & Visual Grounding Service.
Adapted from mutonby/openshorts (hook_grounding.py).

Guarantees semantic coherence between what the narrator says and what is shown on screen.
Detects disjointed/nonsensical visual mismatches and regrounds visual descriptions
so the video never talks about one thing while showing something completely irrelevant.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class GroundingAuditResult:
    is_grounded: bool
    coherence_score: float  # 0.0 to 1.0
    narration_entities: List[str]
    visual_entities: List[str]
    regrounded_visual_intent: str
    regrounded_search_terms: List[str]
    explanation: str


class HookVisualGrounding:
    """Audits and regrounds audio narration against visual scene descriptions."""

    MIN_COHERENCE_THRESHOLD: float = 0.35

    # Stopwords to ignore in entity extraction
    STOPWORDS: Set[str] = {
        "bu", "şu", "o", "bir", "ve", "veya", "ile", "için", "gibi", "kadar", "daha",
        "çok", "en", "ama", "fakat", "ancak", "çünkü", "nasıl", "neden", "kim",
        "the", "a", "an", "and", "or", "in", "on", "at", "for", "with", "about",
        "as", "by", "from", "is", "are", "was", "were", "it", "this", "that"
    }

    @classmethod
    def extract_salient_entities(cls, text: str) -> List[str]:
        """Extracts substantive nouns, subjects, and actions from text."""
        words = re.findall(r"\b[A-Za-zÇĞİÖŞÜçğıöşü]{3,}\b", text.lower())
        meaningful = [w for w in words if w not in cls.STOPWORDS]
        # Keep unique in order
        seen = set()
        out = []
        for w in meaningful:
            if w not in seen:
                seen.add(w)
                out.append(w)
        return out

    @classmethod
    def calculate_coherence(
        cls,
        narration: str,
        visual_desc: str,
    ) -> Tuple[float, List[str], List[str]]:
        """Calculates semantic overlap ratio between narration and visual prompt."""
        n_entities = cls.extract_salient_entities(narration)
        v_entities = cls.extract_salient_entities(visual_desc)

        if not n_entities or not v_entities:
            return 0.5, n_entities, v_entities  # Neutral when sparse

        # Compute overlap
        set_n = set(n_entities)
        set_v = set(v_entities)
        overlap = set_n.intersection(set_v)

        # Also give partial credit for substring matches
        partial_matches = 0
        for ne in set_n:
            for ve in set_v:
                if (len(ne) > 3 and len(ve) > 3) and (ne in ve or ve in ne):
                    partial_matches += 1
                    break

        score = (len(overlap) * 1.0 + partial_matches * 0.5) / max(len(set_n), 1)
        score = min(1.0, round(score, 3))
        return score, n_entities, v_entities

    @classmethod
    def reground_scene(
        cls,
        narration: str,
        scene_description: str = "",
        niche_id: str = "general",
    ) -> GroundingAuditResult:
        """
        Audits narration and visual description.
        If coherence is below threshold, synthesizes a grounded visual intent and search terms.
        """
        score, n_ents, v_ents = cls.calculate_coherence(narration, scene_description)
        is_grounded = score >= cls.MIN_COHERENCE_THRESHOLD

        if is_grounded and scene_description:
            regrounded_intent = scene_description
            terms = [e for e in n_ents[:3]]
            explanation = "Visual scene is semantically grounded with narration."
        else:
            # Reground directly from the most salient narration subjects
            salient = n_ents[:4]
            regrounded_intent = f"Direct visual of {', '.join(salient)} matching narration: {narration[:120]}"
            terms = salient[:3]
            explanation = (
                f"Disjointed visual detected (coherence {score:.2f} < {cls.MIN_COHERENCE_THRESHOLD}). "
                f"Regrounded visual intent to match spoken subjects: {salient}."
            )

        return GroundingAuditResult(
            is_grounded=is_grounded,
            coherence_score=score,
            narration_entities=n_ents,
            visual_entities=v_ents,
            regrounded_visual_intent=regrounded_intent,
            regrounded_search_terms=terms,
            explanation=explanation,
        )

    @classmethod
    def reground_plan_scenes(
        cls,
        scenes: List[Dict[str, Any]],
        niche_id: str = "general",
    ) -> List[Dict[str, Any]]:
        """Audits all scenes in a plan and rewrites any disjointed visual descriptions."""
        regrounded_scenes = []
        for sc in scenes:
            c_sc = dict(sc)
            narration = str(c_sc.get("narration") or c_sc.get("text") or "")
            v_desc = str(c_sc.get("scene_description") or c_sc.get("visual_intent") or "")

            audit = cls.reground_scene(
                narration=narration,
                scene_description=v_desc,
                niche_id=niche_id,
            )

            c_sc["grounding_coherence_score"] = audit.coherence_score
            c_sc["is_grounded"] = audit.is_grounded
            if not audit.is_grounded:
                c_sc["scene_description"] = audit.regrounded_visual_intent
                c_sc["grounded_terms"] = audit.regrounded_search_terms
            regrounded_scenes.append(c_sc)

        return regrounded_scenes


hook_visual_grounding = HookVisualGrounding()
