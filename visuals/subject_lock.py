"""Concrete shot lock.

A sentence about a skyscraper must search for a skyscraper.
Niche mood banks (ocean, marble, fog) are not a substitute when the
sentence names something a camera can film.

ViewMade's researched-short path works the same way: read the scene,
then fetch real footage of that subject and reframe it. License checks
stay in the providers. This module only decides the search subject.
"""
from __future__ import annotations

import re
from typing import List, Optional, Sequence

from .subject_lock_data import FAMILIES, ShotFamily


_FOLD = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
    "â": "a", "î": "i", "û": "u",
})


def fold(text: str) -> str:
    return (text or "").casefold().translate(_FOLD)


def _has_phrase(folded: str, needle: str) -> bool:
    n = fold(needle).strip()
    if len(n) < 3:
        return False
    if " " in n:
        return n in folded
    # Long stems keep Turkish suffixes: gökdelen / gökdelenlerin / gökdeleni.
    # Short stems stay whole words so "kale" does not hit "kalem", and "okul" does not hit "okulda söylemezler".
    if len(n) >= 6:
        return re.search(rf"(?<![a-z0-9]){re.escape(n)}", folded) is not None
    return re.search(rf"(?<![a-z0-9]){re.escape(n)}(?![a-z0-9])", folded) is not None


_BY_LENGTH: List[tuple] = []
for _fam in FAMILIES:
    for _needle in _fam.needles:
        _BY_LENGTH.append((len(fold(_needle)), _needle, _fam))
_BY_LENGTH.sort(key=lambda row: row[0], reverse=True)


def match_shot(*parts: str) -> Optional[ShotFamily]:
    """Longest concrete noun in the text. Title is a fallback, not a override."""
    blob = fold(" ".join(p for p in parts if p))
    if len(blob) < 3:
        return None
    for _, needle, fam in _BY_LENGTH:
        if _has_phrase(blob, needle):
            return fam
    return None


def family_of_phrase(phrase: str) -> Optional[ShotFamily]:
    folded = fold(phrase)
    if not folded:
        return None
    for fam in FAMILIES:
        names = [fold(fam.primary), fold(fam.root)] + [fold(v) for v in fam.variants]
        if folded in names:
            return fam
        if fold(fam.root) in folded:
            return fam
    return None


def next_variant(primary: str, index: int) -> Optional[str]:
    """Another camera angle of the same subject. None when the phrase is not locked."""
    fam = family_of_phrase(primary)
    if fam is None:
        return None
    cycle = [fam.primary, *list(fam.variants)]
    alts = [item for item in cycle if fold(item) != fold(primary)]
    if not alts:
        return None
    return alts[abs(int(index)) % len(alts)]


_FILLER_QUERIES = {
    "nature", "cinematic", "cinematic atmosphere", "n/a", "tbd", "none",
}
_GENERIC_FALLBACK_WORDS = {"nature", "sunrise", "landscape", "scenery", "broll", "footage"}


def queries_for_scene(
    narration: str = "",
    scene_description: str = "",
    subject: str = "",
    existing: Optional[Sequence[str]] = None,
    limit: int = 4,
) -> List[str]:
    """Keep queries that name the sentence's subject. Drop nature and atmosphere filler."""
    shot = match_shot(narration, scene_description, subject)
    raw = [str(q).strip() for q in (existing or []) if str(q).strip()]
    if shot is not None:
        kept = [
            q for q in raw
            if query_matches_clip(shot.primary, q) or query_matches_clip(q, shot.primary)
        ]
        merged: List[str] = []
        seen = set()
        for q in list(shot_queries(shot, limit=limit)) + kept:
            key = fold(q)
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(q)
            if len(merged) >= limit:
                break
        return merged
    return [
        q for q in raw
        if fold(q) not in _FILLER_QUERIES
        and not (_GENERIC_FALLBACK_WORDS & set(fold(q).split()))
    ][:limit]


def lock_scene_queries(scene: dict) -> None:
    """Rewrite one generated scene so search queries film the sentence."""
    intent = scene.get("visual_intent") if isinstance(scene.get("visual_intent"), dict) else {}
    existing = scene.get("search_queries") or []
    if isinstance(existing, str):
        existing = [existing]
    queries = queries_for_scene(
        narration=str(scene.get("narration") or ""),
        scene_description=str(scene.get("scene_description") or ""),
        subject=str(intent.get("subject") or ""),
        existing=existing,
    )
    scene["search_queries"] = queries
    shot = match_shot(
        str(scene.get("narration") or ""),
        str(scene.get("scene_description") or ""),
        str(intent.get("subject") or ""),
    )
    if shot is None:
        return
    updated = dict(intent)
    updated["subject"] = shot.primary
    updated["search_queries"] = queries
    updated["visual_priority"] = updated.get("visual_priority") or "subject"
    scene["visual_intent"] = updated


def shot_queries(family: ShotFamily, limit: int = 4) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in (family.primary, *family.variants):
        key = fold(raw)
        if key in seen:
            continue
        seen.add(key)
        out.append(raw)
        if len(out) >= limit:
            break
    return out


# Tokens that appear in almost every stock title. They must not
# count as proof that a skyscraper query matched a beach clip.
WEAK_TOKENS = {
    "light", "dark", "night", "day", "closeup", "close", "detail", "aerial",
    "soft", "natural", "city", "view", "people", "person", "street", "water",
    "sky", "road", "room", "hand", "hands", "background", "video", "clip",
    "footage", "stock", "slow", "motion", "shot", "scene", "beautiful",
    "cinematic", "atmospheric", "wide", "over", "with", "from", "into",
}


def strong_tokens(query: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z]{4,}", fold(query))
    return [t for t in tokens if t not in WEAK_TOKENS]


def query_matches_clip(query: str, clip_text: str) -> bool:
    """True when the clip text actually names the shot, not a weak neighbor word."""
    strong = strong_tokens(query)
    if not strong:
        return True
    blob = fold(clip_text)
    return any(token in blob for token in strong)


__all__ = [
    "FAMILIES",
    "ShotFamily",
    "WEAK_TOKENS",
    "family_of_phrase",
    "fold",
    "lock_scene_queries",
    "match_shot",
    "next_variant",
    "queries_for_scene",
    "query_matches_clip",
    "shot_queries",
    "strong_tokens",
]
