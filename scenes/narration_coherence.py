"""
Cross-scene narration coherence — detect and repair split verbs / continuation fragments.
Runs after generate and before compile timeline condense.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Tuple

from .narration_validate import MIN_WORDS_PER_SCENE, normalize_narration_for_validation

# Scene N ends with incomplete verb stem (e.g. "ilan.", "de.", "ki.")
_INCOMPLETE_VERB_END_RE = re.compile(
    r"\b(?:ilan|et|de|ki|gör|gor|söyl|soyl|yap|ol|ver|gel|git|dur|kal|"
    r"başla|basla|bit|aç|ac|kapat|düş|dus|dön|don|çık|cik|al|"
    r"tanı|tani|kabul|redd|savun|suçla|sucla)\.\s*$",
    re.IGNORECASE,
)

# Scene N+1 starts with capitalized verb continuation fragment
_VERB_CONTINUATION_START_RE = re.compile(
    r"^(?:Etti|Ediyor|Ederek|Edile|Edildi|Eden|Edil|"
    r"Oluyor|Oldu|Olan|Olarak|"
    r"Görüyor|Gördü|Görül|"
    r"Yaptı|Yapıyor|Yapıl|"
    r"Verdi|Veriyor|"
    r"Dedi|Diyor|"
    r"Başladı|Basladi|Bitti|"
    r"Geldi|Gidiyor|Gitti)\b",
    re.IGNORECASE,
)

_DANGLING_SINGLE_WORD_END = frozenset({
    "ilan", "et", "de", "ki", "ve", "ama", "için", "icin", "ile", "ise",
    "olarak", "gibi", "bir", "bu", "o", "beni", "seni", "onu",
})


def _last_word(text: str) -> str:
    words = (text or "").strip().split()
    if not words:
        return ""
    return words[-1].lower().rstrip(".,!?;:")


def _first_word(text: str) -> str:
    words = (text or "").strip().split()
    if not words:
        return ""
    return words[0].rstrip(".,!?;:")


def detect_split_verb_pair(prev_narr: str, next_narr: str) -> bool:
    """True when prev ends with incomplete verb and next starts with continuation."""
    prev = normalize_narration_for_validation(prev_narr)
    nxt = normalize_narration_for_validation(next_narr)
    if not prev or not nxt:
        return False

    if _INCOMPLETE_VERB_END_RE.search(prev):
        if _VERB_CONTINUATION_START_RE.match(nxt):
            return True

    tail = _last_word(prev)
    if tail in _DANGLING_SINGLE_WORD_END and _VERB_CONTINUATION_START_RE.match(nxt):
        return True

    # "ilan." + "Etti ve ..." — explicit user bug pattern
    if tail == "ilan" and _first_word(nxt).lower().startswith("ett"):
        return True

    return False


def _merge_scene_pair(scenes: List[Dict[str, Any]], idx: int) -> List[str]:
    """Merge scenes[idx] and scenes[idx+1]; return fix descriptions."""
    a = scenes[idx]
    b = scenes[idx + 1]
    left = (a.get("narration") or "").strip().rstrip(".!?")
    right = (b.get("narration") or "").strip()
    if _VERB_CONTINUATION_START_RE.match(right):
        right = right[0].lower() + right[1:]
    merged = f"{left} {right.lstrip()}".strip()
    merged = re.sub(r"\s+", " ", merged)
    if merged and merged[-1] not in ".!?":
        merged += "."

    a["narration"] = merged
    dur_a = float(a.get("duration") or 3.0)
    dur_b = float(b.get("duration") or 3.0)
    a["duration"] = round(dur_a + dur_b, 1)

    # Keep distinct visual angles from both merged scenes.
    q_a = list(a.get("search_queries") or [])
    q_b = list(b.get("search_queries") or [])
    merged_queries = []
    for query in q_a + q_b:
        text = str(query or "").strip()
        if text and text.casefold() not in {item.casefold() for item in merged_queries}:
            merged_queries.append(text)
    if merged_queries:
        a["search_queries"] = merged_queries[:3]

    scenes.pop(idx + 1)
    return [f"merged_split_verb_{idx}_{idx + 1}"]


def repair_split_verbs_across_scenes(
    scenes: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Scan adjacent scenes for split-verb / continuation fragments and merge them.
    """
    scenes = copy.deepcopy(scenes)
    fixes: List[str] = []
    i = 0
    while i < len(scenes) - 1:
        prev = (scenes[i].get("narration") or "").strip()
        nxt = (scenes[i + 1].get("narration") or "").strip()
        if prev and nxt and detect_split_verb_pair(prev, nxt):
            fixes.extend(_merge_scene_pair(scenes, i))
            continue
        i += 1
    return scenes, fixes


def repair_cross_scene_coherence(
    plan: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """Repair split verbs in a full plan dict; rebuild full_narration."""
    plan = copy.deepcopy(plan or {})
    scenes, fixes = repair_split_verbs_across_scenes(plan.get("scenes") or [])
    plan["scenes"] = scenes
    plan["full_narration"] = " ".join(
        (s.get("narration") or "").strip() for s in scenes if (s.get("narration") or "").strip()
    )
    return plan, fixes
