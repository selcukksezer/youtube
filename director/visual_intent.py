"""
Bölüm 7 — Visual Director Layer.

Every scene gets a structured `VisualIntent` before stock search or AI fallback
runs. Prevents generic nature/space footage on specific historical/mythological
topics and enforces a continuity motif across scenes.

Motif dictionaries, topic-niche locks, aliases, hybrid signals, and scoring live in:
- `director/motif_data.py`
- `director/visual_intent_scoring.py`
"""
from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

from director.motif_data import (
    DEFAULT_MOOD_CYCLE,
    FAMILY_MOTIFS,
    NICHE_MOTIFS,
    TOPIC_HYBRID_SIGNALS,
    TOPIC_NICHE_ALIASES,
    TOPIC_NICHE_LOCK,
    _DEFAULT_MOTIF,
)
from .schema import ScenePlan, VisualIntent
from .visual_intent_scoring import (
    SHOT_INTENTS,
    _EMBED_CACHE,
    _MAX_EMBED_CACHE_ENTRIES,
    _embed_text,
    _embedding_similarity_boost,
    _tokenize,
    assign_camera_direction,
    classify_scene_intent,
    semantic_relevance_score,
    text_contains_excluded,
)


def _match_aliases(text: str) -> Optional[str]:
    low = (text or "").lower()
    for phrase, niche_id in TOPIC_NICHE_ALIASES:
        if phrase in low:
            return niche_id
    return None


def _fuzzy_match_niche(title: str, min_hits: float = 1.5) -> Optional[str]:
    """Score topic against NICHES trending_keywords + names."""
    try:
        from niche_templates import NICHES
    except ImportError:
        return None
    text = (title or "").lower()
    tokens = _tokenize(title)
    best_id: Optional[str] = None
    best_score = 0.0
    for nid, niche in NICHES.items():
        score = 0.0
        for kw in niche.get("trending_keywords", []):
            kl = kw.lower()
            if kl in text:
                score += 2.0
            elif any(kl in t or t in kl for t in tokens if len(t) >= 3):
                score += 1.0
        for label in (niche.get("name", ""), niche.get("name_en", "")):
            for part in label.lower().split():
                if len(part) >= 5 and part in text:
                    score += 0.75
        if score > best_score:
            best_score = score
            best_id = nid
    if best_score >= min_hits:
        return best_id
    names = {nid: (n.get("name", "") or nid) for nid, n in NICHES.items()}
    matches = difflib.get_close_matches(text[:60], list(names.values()), n=1, cutoff=0.55)
    if matches:
        for nid, name in names.items():
            if name == matches[0]:
                return nid
    return None


def _detect_hybrid_niche(title: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (hybrid_id, fallback_standard_niche) when dual-domain keywords hit."""
    low = (title or "").lower()
    for group_a, group_b, hybrid_id, fallback in TOPIC_HYBRID_SIGNALS:
        hit_a = any(k in low for k in group_a)
        hit_b = any(k in low for k in group_b)
        if hit_a and hit_b:
            return hybrid_id, fallback
    return None, None


def resolve_topic_intelligence(title: str, niche_id: str) -> Dict[str, Any]:
    """P1-02: full topic→niche resolution with method + optional hybrid hint."""
    text = title or ""
    requested = niche_id or "1_news_flash"
    for pattern, locked in TOPIC_NICHE_LOCK:
        if pattern.search(text):
            hybrid, _ = _detect_hybrid_niche(text)
            return {
                "resolved_niche": locked,
                "requested_niche": requested,
                "match_method": "regex_lock",
                "hybrid_niche": hybrid,
                "locked": locked != requested,
            }
    if requested == "10_religious_quotes" and re.search(
        r"\bhz\b|hazret|peygamber|ayet|hadis|dua\b|allah|islam|sabır|tevekkül", text, re.I
    ):
        return {
            "resolved_niche": requested,
            "requested_niche": requested,
            "match_method": "requested_religious",
            "hybrid_niche": None,
            "locked": False,
        }
    alias = _match_aliases(text)
    if alias:
        hybrid, _ = _detect_hybrid_niche(text)
        return {
            "resolved_niche": alias,
            "requested_niche": requested,
            "match_method": "alias",
            "hybrid_niche": hybrid,
            "locked": alias != requested,
        }
    hybrid, hybrid_fallback = _detect_hybrid_niche(text)
    if hybrid and hybrid_fallback:
        return {
            "resolved_niche": hybrid_fallback,
            "requested_niche": requested,
            "match_method": "hybrid",
            "hybrid_niche": hybrid,
            "locked": hybrid_fallback != requested,
        }
    fuzzy = _fuzzy_match_niche(text)
    if fuzzy:
        return {
            "resolved_niche": fuzzy,
            "requested_niche": requested,
            "match_method": "fuzzy",
            "hybrid_niche": None,
            "locked": fuzzy != requested,
        }
    return {
        "resolved_niche": requested,
        "requested_niche": requested,
        "match_method": "passthrough",
        "hybrid_niche": None,
        "locked": False,
    }


def resolve_niche_from_topic(title: str, niche_id: str) -> str:
    return resolve_topic_intelligence(title, niche_id)["resolved_niche"]


def get_motif_bank(niche_id: str) -> Dict[str, Any]:
    if niche_id in NICHE_MOTIFS:
        return NICHE_MOTIFS[niche_id]
    try:
        from niche_templates import get_niche_family
        family = get_niche_family(niche_id)
    except Exception:
        family = "general"
    return FAMILY_MOTIFS.get(family, _DEFAULT_MOTIF)


SHOT_TAGS = ("establishing", "closeup", "action", "transition")
_SHOT_CAMERA = {
    "establishing": "slow wide push",
    "closeup": "gentle push",
    "action": "quick pan",
    "transition": "pull back",
}
_SHOT_FRAME = {
    "establishing": "wide shot",
    "closeup": "close up",
    "action": "motion",
    "transition": "wide shot",
}
_SHOT_FIGHTS = {
    "establishing": ("close up", "closeup", "macro"),
    "closeup": ("wide shot", "aerial"),
    "action": (),
    "transition": ("close up", "closeup", "macro"),
}
_CLOSE_SHOT_RE = re.compile(
    r"\b(göz|yüz|el|parmak|detay|yakın|close|eye|face|hand|detail|macro)\b",
    re.IGNORECASE,
)
_ACTION_SHOT_RE = re.compile(
    r"\b(koş|düş|çarp|patla|kaç|vur|fırla|run|crash|hit|explode|chase|sprint)\b",
    re.IGNORECASE,
)


def assign_shot_type(narration: str, index: int, total: int, beat_type: str = "") -> str:
    """One framing tag per scene. Last scene pulls back. Verbs beat the default wide."""
    text = narration or ""
    if total > 1 and index == total - 1:
        return "transition"
    if _ACTION_SHOT_RE.search(text) or str(beat_type or "") == "climax":
        return "action"
    if _CLOSE_SHOT_RE.search(text):
        return "closeup"
    if index == 0 or str(beat_type or "") == "hook":
        return "establishing"
    return "closeup" if index % 2 else "establishing"


def _intent_for_subject(
    scene: ScenePlan,
    bank: Dict[str, Any],
    subject: str,
    scene_index: int,
    locked: bool = False,
    shot_type: str = "",
) -> VisualIntent:
    tag = shot_type if shot_type in SHOT_TAGS else assign_shot_type(
        scene.narration or "", scene_index, 0, getattr(scene, "beat_type", "") or ""
    )
    frame = _SHOT_FRAME[tag]
    fights = _SHOT_FIGHTS[tag]
    existing_q = scene.search_queries or []
    exclude = [e.lower() for e in bank.get("must_exclude", [])]
    clean_existing = []
    for q in existing_q:
        ql = q.lower()
        if any(ex in ql for ex in exclude):
            continue
        if any(bad in ql for bad in fights):
            continue
        clean_existing.append(q)

    palette = bank.get("mood_palette") or []
    scene_mood = palette[scene_index % len(palette)] if palette else str(bank.get("mood", "cinematic"))

    queries = [subject, f"{subject} {frame}"]
    if not locked:
        era_q = f"{bank.get('era', '')} {subject}".strip()
        if era_q and era_q not in queries:
            queries.append(era_q)
    for q in clean_existing[:2]:
        if q not in queries:
            queries.append(q)

    return VisualIntent(
        subject=subject,
        action=_SHOT_CAMERA[tag],
        shot_type=tag,
        setting=str(bank.get("era", "")),
        era=str(bank.get("era", "")),
        mood=scene_mood,
        must_include=list(bank.get("must_include") or []),
        must_exclude=list(bank.get("must_exclude") or []),
        continuity_motif=str(bank.get("motif", "default")),
        search_queries=queries,
    )


def build_visual_intent_for_scene(
    scene: ScenePlan,
    niche_id: str,
    title: str = "",
    scene_index: int = 0,
    shot_type: str = "",
) -> VisualIntent:
    bank = get_motif_bank(niche_id)
    from visuals.subject_lock import match_shot

    shot = match_shot(scene.narration or "")
    if shot is None:
        shot = match_shot(scene.scene_description or "")
    if shot is None and title:
        shot = match_shot(title)
    if shot is not None:
        return _intent_for_subject(
            scene, bank, shot.primary, scene_index, locked=True, shot_type=shot_type
        )

    subjects: List[str] = list(bank.get("subjects") or _DEFAULT_MOTIF["subjects"])
    subject = subjects[scene_index % len(subjects)]

    narr_tokens = _tokenize(scene.narration)
    for cand in subjects:
        if _tokenize(cand) & narr_tokens:
            subject = cand
            break

    return _intent_for_subject(
        scene, bank, subject, scene_index, locked=False, shot_type=shot_type
    )


def _fork_distinct_from_previous(
    intent: VisualIntent,
    scene: ScenePlan,
    bank: Dict[str, Any],
    scene_index: int,
    prev: VisualIntent,
    shot_type: str = "",
) -> VisualIntent:
    """Vary adjacent same-subject shots without changing their semantic root."""
    if intent.subject != prev.subject:
        return intent
    from visuals.subject_lock import next_variant
    alt_shot = next_variant(intent.subject, scene_index)
    if alt_shot and alt_shot != prev.subject:
        return _intent_for_subject(
            scene, bank, alt_shot, scene_index, locked=True, shot_type=shot_type or intent.shot_type
        )
    subjects: List[str] = list(bank.get("subjects") or _DEFAULT_MOTIF["subjects"])
    for offset in range(1, len(subjects)):
        alt = subjects[(scene_index + offset) % len(subjects)]
        if alt != prev.subject:
            return _intent_for_subject(
                scene, bank, alt, scene_index, shot_type=shot_type or intent.shot_type
            )
    return intent


def apply_visual_intents(scenes: List[ScenePlan], niche_id: str, title: str = "") -> List[ScenePlan]:
    from scenes.narration_validate import scene_description_usable

    locked = resolve_niche_from_topic(title, niche_id)
    bank = get_motif_bank(locked)
    prev_cam: Optional[str] = None
    total = len(scenes)

    for i, scene in enumerate(scenes):
        sc_intent = classify_scene_intent(
            narration=scene.narration,
            beat_type=scene.beat_type,
            index=i,
            total_scenes=total,
            title=title,
            scene_description=scene.scene_description,
        )
        cam_dir = assign_camera_direction(sc_intent, index=i, prev_direction=prev_cam)
        scene.scene_intent = sc_intent
        scene.camera_direction = cam_dir
        prev_cam = cam_dir

        intent = build_visual_intent_for_scene(
            scene, locked, title=title, scene_index=i, shot_type=sc_intent
        )
        if i > 0 and scenes[i - 1].visual_intent:
            intent = _fork_distinct_from_previous(
                intent, scene, bank, i, scenes[i - 1].visual_intent, shot_type=sc_intent
            )
        scene.visual_intent = intent

        cam_to_action_map = {
            "zoom_in": "slow push in",
            "zoom_out": "slow pull out",
            "pan_left": "pan left",
            "pan_right": "pan right",
            "tilt_up": "tilt up",
            "tilt_down": "tilt down",
            "static": "static shot",
        }
        intent.action = cam_to_action_map.get(cam_dir, intent.action)
        intent.shot_type = sc_intent

        exclude = list(intent.must_exclude or [])
        fights = _SHOT_FIGHTS.get(sc_intent, ())
        from visuals.subject_lock import family_of_phrase, query_matches_clip
        locked_family = family_of_phrase(intent.subject)
        if scene.search_queries and (scene.narration or "").strip():
            merged = [
                q for q in scene.search_queries
                if not text_contains_excluded(q, exclude)
                and not any(bad in q.lower() for bad in fights)
            ]
            for q in intent.search_queries:
                if q not in merged and not text_contains_excluded(q, exclude):
                    merged.append(q)
            if locked_family is not None:
                on_subject = [
                    q for q in merged
                    if query_matches_clip(intent.subject, q) or query_matches_clip(q, intent.subject)
                ]
                if on_subject:
                    merged = on_subject
            scene.search_queries = (merged[:4] or list(intent.search_queries))
        else:
            scene.search_queries = intent.search_queries
        if not scene_description_usable(scene.scene_description or ""):
            from scenes.narration_validate import synthesize_scene_description
            scene.scene_description = synthesize_scene_description(scene)
        palette = bank.get("mood_palette") or DEFAULT_MOOD_CYCLE
        scene.mood = palette[i % len(palette)]
    return scenes
