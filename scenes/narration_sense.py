"""
Strip narration that does not say the topic.

Catches three failures that reach the timeline:
- a celebrity the topic never named, spliced into the title
- the same title slice written twice in one scene
- a classroom template that repeats the headline instead of a fact
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

_BOILERPLATE_RE = re.compile(
    r"yıllarca sınıfta tekrar|ilk kontrol:|iddia şu:|şablona kaymaz|kısa stub yok|"
    r"nişin kuralları|niche pack|six-word stub|the claim is this:",
    re.IGNORECASE,
)

_FAKE_QUOTE_RE = re.compile(
    r"\bhakkında söylediği söz şok edici:\s*|\bonce said about\b[^:]{0,80}:\s*",
    re.IGNORECASE,
)


def _tokens(text: str, min_len: int = 3) -> List[str]:
    return [
        w.casefold()
        for w in re.findall(r"[^\W\d_]{3,}", text or "", flags=re.UNICODE)
        if len(w) >= min_len
    ]


def _strip_foreign_names(text: str, topic: str) -> str:
    topic_l = (topic or "").casefold()
    try:
        from viral_retention_engine import ViralRetentionEngine
        names = list(ViralRetentionEngine.TRIGGER_NAMES)
    except Exception:
        names = []
    cleaned = text or ""
    for name in names:
        if name.casefold() in topic_l:
            continue
        cleaned = re.sub(
            rf"\b{re.escape(name)}['’](?:ın|in|un|ün|nın|nin|nun|nün)\b",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
    cleaned = _FAKE_QUOTE_RE.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _collapse_repeated_span(text: str, span: int = 4) -> str:
    words = (text or "").split()
    changed = True
    while changed and len(words) >= span * 2:
        changed = False
        seen: Dict[str, int] = {}
        for i in range(0, len(words) - span + 1):
            key = " ".join(w.casefold().strip(".,!?;:") for w in words[i:i + span])
            if key in seen:
                del words[i:i + span]
                changed = True
                break
            seen[key] = i
    out = re.sub(r"\s+", " ", " ".join(words)).strip()
    out = re.sub(r"\s+([.!?])", r"\1", out)
    if out and out[-1] not in ".!?":
        out += "."
    return out


def _extra_content_words(narr: str, title: str) -> int:
    title_set = set(_tokens(title, min_len=3))
    return sum(1 for w in _tokens(narr, min_len=3) if w not in title_set)


def _off_topic(narration: str, topic: str) -> bool:
    distinctive = [t for t in _tokens(topic, min_len=5)]
    if len(distinctive) < 1:
        return False
    blob = (narration or "").casefold()
    return not any(tok in blob for tok in distinctive)


def repair_nonsensical_narration(plan: Dict[str, Any], topic: str = "") -> Dict[str, Any]:
    """Return the plan with mashed titles and template lines replaced."""
    if not isinstance(plan, dict):
        return plan
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return plan

    topic = (topic or plan.get("keyword") or plan.get("title") or "").strip()
    from scenes.fallback import _topic_bound_narrations, _viewer_subject

    subject = _viewer_subject(topic)
    is_tr = str(plan.get("language") or "tr").lower()[:2] != "en"
    beats = _topic_bound_narrations(subject, is_tr)

    joined_after_strip = []
    for sc in scenes:
        if not isinstance(sc, dict):
            continue
        narr = _strip_foreign_names(str(sc.get("narration") or ""), topic)
        narr = _collapse_repeated_span(narr)
        sc["narration"] = narr
        joined_after_strip.append(narr)
    full = " ".join(joined_after_strip)
    replace_all = _off_topic(full, topic) and any(
        _BOILERPLATE_RE.search(n) or _extra_content_words(n, plan.get("title") or topic) < 4
        for n in joined_after_strip
    )

    for i, sc in enumerate(scenes):
        if not isinstance(sc, dict):
            continue
        narr = str(sc.get("narration") or "")
        echo = _extra_content_words(narr, topic) < 4 and len(_tokens(narr)) >= 6
        if replace_all or _BOILERPLATE_RE.search(narr) or echo:
            sc["narration"] = beats[i % len(beats)]

    plan_title = str(plan.get("title") or "")
    topic_tokens = set(_tokens(topic, min_len=4))
    title_tokens = set(_tokens(plan_title, min_len=4))
    if topic_tokens and len(topic_tokens & title_tokens) < 2 and plan_title.casefold() != topic.casefold():
        plan["title"] = topic

    plan["full_narration"] = " ".join(
        str(s.get("narration") or "").strip()
        for s in scenes
        if isinstance(s, dict) and str(s.get("narration") or "").strip()
    )
    return plan
