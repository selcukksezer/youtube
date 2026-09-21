"""Viewer-centric quality score (0–100) for API/UI — research §E + CREATIVE_DIRECTION §4."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}", (text or "").lower())


def _hook_strength(scenes: Sequence[Dict[str, Any]]) -> float:
    if not scenes:
        return 0.0
    first = scenes[0]
    narr = (first.get("narration") or "").strip()
    beat = (first.get("beat_type") or first.get("beat") or "").lower()
    score = 0.3
    if beat == "hook" or first.get("index", 0) in (0, 1):
        score += 0.2
    if re.search(r"[?？]|!\s*$", narr) or re.search(
        r"\b(neden|asla|kimse|şok|sakın|why|never|secret)\b", narr, re.I
    ):
        score += 0.3
    if 6 <= len(narr.split()) <= 28:
        score += 0.2
    return min(1.0, score)


def _visual_alignment(scenes: Sequence[Dict[str, Any]]) -> float:
    if not scenes:
        return 0.0
    scores = []
    for s in scenes:
        narr_t = set(_tokens(s.get("narration") or ""))
        q_t = set()
        for q in s.get("search_queries") or []:
            q_t |= set(_tokens(str(q)))
        vi = s.get("visual_intent") or {}
        if isinstance(vi, dict):
            for q in vi.get("search_queries") or []:
                q_t |= set(_tokens(str(q)))
            q_t |= set(_tokens(str(vi.get("subject") or "")))
        if not narr_t or not q_t:
            scores.append(0.35)
            continue
        overlap = len(narr_t & q_t) / max(1, len(narr_t | q_t))
        scores.append(min(1.0, 0.25 + overlap * 2))
    return sum(scores) / len(scores)


def _pacing(scenes: Sequence[Dict[str, Any]], total_dur: float) -> float:
    if not scenes or total_dur <= 0:
        return 0.4
    wps = []
    for s in scenes:
        words = len((s.get("narration") or "").split())
        d = float(s.get("duration") or s.get("target_duration") or 0) or (total_dur / len(scenes))
        if d > 0:
            wps.append(words / d)
    if not wps:
        return 0.4
    avg = sum(wps) / len(wps)
    # TR sweet spot ~2.5–3.2 wps
    if 2.2 <= avg <= 3.5:
        band = 1.0
    elif 1.6 <= avg < 2.2 or 3.5 < avg <= 4.2:
        band = 0.65
    else:
        band = 0.35
    if len(wps) >= 2:
        mean = avg
        var = sum((x - mean) ** 2 for x in wps) / len(wps)
        variance_ok = 1.0 if var < 1.2 else 0.7 if var < 2.5 else 0.4
    else:
        variance_ok = 0.7
    return 0.6 * band + 0.4 * variance_ok


def _loop_closure(scenes: Sequence[Dict[str, Any]]) -> float:
    if len(scenes) < 2:
        return 0.3
    a = set(_tokens(scenes[0].get("narration") or ""))
    b = set(_tokens(scenes[-1].get("narration") or ""))
    if not a or not b:
        return 0.25
    return min(1.0, len(a & b) / max(3, min(len(a), len(b))) * 1.5)


def _caption_fit(scenes: Sequence[Dict[str, Any]]) -> float:
    ok = 0
    for s in scenes:
        n = len((s.get("narration") or "").split())
        if n <= 14:
            ok += 1
        elif n <= 22:
            ok += 0.5
    return ok / max(1, len(scenes))


def compute_viewer_score(
    plan: Dict[str, Any],
    *,
    license_safe: bool = True,
    compliance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Weighted 0–100:
      hook 25 · visual 25 · pacing 15 · loop 15 · caption 10 · license 10
    """
    scenes = plan.get("scenes") or []
    total = float(plan.get("total_duration") or 0)
    if total <= 0 and scenes:
        total = sum(float(s.get("duration") or 4) for s in scenes)

    h = _hook_strength(scenes)
    v = _visual_alignment(scenes)
    p = _pacing(scenes, total)
    loop = _loop_closure(scenes)
    cap = _caption_fit(scenes)
    lic = 1.0 if license_safe else 0.0

    if compliance and compliance.get("hard_fail"):
        lic = min(lic, 0.2)

    total_score = (
        25 * h + 25 * v + 15 * p + 15 * loop + 10 * cap + 10 * lic
    )
    return {
        "score": round(total_score, 1),
        "components": {
            "hook_strength": round(h * 100, 1),
            "visual_alignment": round(v * 100, 1),
            "pacing": round(p * 100, 1),
            "loop_closure": round(loop * 100, 1),
            "caption_fit": round(cap * 100, 1),
            "license_safety": round(lic * 100, 1),
        },
        "pass": total_score >= 55 and not (compliance or {}).get("hard_fail"),
    }
