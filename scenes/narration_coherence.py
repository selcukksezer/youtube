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

_TOPIC_STOP_WORDS = frozenset({
    "acaba", "ama", "ancak", "artık", "aslında", "bana", "bazen", "bazı",
    "belki", "ben", "beni", "benim", "bile", "bir", "biraz", "biz", "bize",
    "bizim", "bu", "buna", "bundan", "bunun", "böyle", "çok", "çünkü", "daha",
    "de", "defa", "diye", "en", "gibi", "hem", "her", "hiç", "için", "ile",
    "ise", "ki", "kadar", "karşı", "kendi", "kez", "kim", "mı", "mi", "mu",
    "mü", "nasıl", "ne", "neden", "nerede", "nereye", "niçin", "o", "ona",
    "ondan", "onlar", "onlara", "onların", "onu", "onun", "orada", "oysa",
    "sanki", "sen", "seni", "senin", "siz", "size", "sizin", "şey", "şu",
    "şuna", "şunlar", "şunu", "tabii", "tam", "ve", "veya", "ya", "yani",
    "yine",
})

_SCENE_BRIDGE_RE = re.compile(
    r"\b(?:ama|ancak|fakat|oysa|halbuki|buna rağmen|bununla birlikte|"
    r"bu yüzden|bu nedenle|dolayısıyla|böylece|ardından|sonrasında|sonra|"
    r"bu sırada|öte yandan|aynı zamanda|çünkü|zira|üstelik|buna karşılık|"
    r"dedi|diyor|söyledi|söylüyor|anlattı|aktardı|belirtti|iddia etti|"
    r"göre|diye|sordu|cevapladı|yanıtladı|gibi(?:dir|ydi|ymiş|ymis)?|sanki|tıpkı|adeta|"
    r"benzer|benzedi|metafor)\b",
    re.IGNORECASE,
)


def _topic_words(text: str) -> set[str]:
    normalized = normalize_narration_for_validation(text).casefold().replace("\u0307", "")
    return {
        word for word in re.findall(r"[a-zçğıöşü]+", normalized)
        if len(word) >= 3 and word not in _TOPIC_STOP_WORDS
    }


def _is_unbridged_topic_jump(previous: str, following: str) -> bool:
    if _SCENE_BRIDGE_RE.search(f"{previous} {following}"):
        return False
    previous_words = _topic_words(previous)
    following_words = _topic_words(following)
    return len(previous_words) >= 4 and len(following_words) >= 4 and not previous_words.intersection(following_words)


def detect_repeated_topic_discontinuities(scenes: List[Dict[str, Any]]) -> List[str]:
    """Return advisory messages for runs of two or more unbridged topic jumps."""
    narrations = [(scene or {}).get("narration") or "" for scene in (scenes or [])]
    jumps = [
        bool(narrations[i].strip() and narrations[i + 1].strip()
             and _is_unbridged_topic_jump(narrations[i], narrations[i + 1]))
        for i in range(len(narrations) - 1)
    ]

    advisories: List[str] = []
    start = 0
    while start < len(jumps):
        if not jumps[start]:
            start += 1
            continue
        end = start
        while end + 1 < len(jumps) and jumps[end + 1]:
            end += 1
        if end - start + 1 >= 2:
            advisories.append(
                f"Sahneler {start + 1}-{end + 2} arasında art arda konu geçişleri var; anlatım akışını gözden geçirin."
            )
        start = end + 1
    return advisories


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
