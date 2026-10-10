"""Hard quality gates for research-backed Shorts packages."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional


MIN_DURATION = 45.0
MAX_DURATION = 60.0
MIN_SCENES = 6
MAX_SCENES = 12
OPTIMAL_MIN_WORDS = 120
OPTIMAL_MAX_WORDS = 170
MIN_WORDS = 85
MAX_WORDS = 195
MIN_SCENE_WORDS = 7
ADVISORY_SCENE_WORDS = 12


_FILLER_RE = re.compile(
    r"\b(bunu aklında tut|bunu aklinda tut|takipte kalın|takipte kalin|"
    r"yorumlarda paylaşın|yorumlarda paylasin|like atın|abone olun)\b",
    re.I,
)
_TOKEN_RE = re.compile(r"[\wçğıöşüÇĞİÖŞÜ'-]+")
_STORY_STOPWORDS = {
    "ama", "artık", "ben", "bir", "bu", "da", "de", "diye", "en", "ile",
    "için", "ve", "the", "and", "but", "for", "with", "that", "this",
}
_NUMBER_WITH_UNIT_RE = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(%|yıl|years?|gün|days?|saat|hours?|dakika|"
    r"minutes?|milyon|million|km|metre|meters?)\b",
    re.I,
)
_AUDIENCE_PROMPT_RE = re.compile(
    r"\?|yorum(?:larda|lara)?|siz olsaydınız|ne düşünüyorsunuz|what would you do|comment",
    re.I,
)


def _words(value: Any) -> List[str]:
    return re.findall(r"[\wçğıöşüÇĞİÖŞÜ'-]+", str(value or ""))


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _scene_fingerprint(scene: Dict[str, Any]) -> str:
    return _norm(" ".join([
        str(scene.get("scene_description") or ""),
        " ".join(str(q) for q in (scene.get("search_queries") or [])[:2]),
    ]))


def _source_evidence_text(plan: Dict[str, Any]) -> str:
    parts: List[str] = []
    reddit_post = plan.get("reddit_post")
    if isinstance(reddit_post, dict):
        parts.extend(str(reddit_post.get(key) or "") for key in ("title", "body", "selftext"))

    snippets = plan.get("fact_snippets") or []
    if isinstance(snippets, list):
        for snippet in snippets:
            if isinstance(snippet, str):
                parts.append(snippet)
            elif isinstance(snippet, dict):
                parts.extend(
                    str(snippet.get(key) or "")
                    for key in ("title", "text", "snippet", "description", "content")
                )
    return " ".join(parts)


def _story_quality_checks(plan: Dict[str, Any], scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
    warnings: List[str] = []
    title_tokens = {
        token.casefold()
        for token in _TOKEN_RE.findall(str(plan.get("title") or ""))
        if len(token) > 2 and token.casefold() not in _STORY_STOPWORDS
    }
    opening_sentence = re.split(
        r"(?<=[.!?])\s+",
        str(scenes[0].get("narration") or ""),
        maxsplit=1,
    )[0] if scenes else ""
    hook_tokens = {
        token.casefold()
        for token in _TOKEN_RE.findall(opening_sentence)
        if token.casefold() not in _STORY_STOPWORDS
    } if scenes else set()
    title_overlap = len(title_tokens & hook_tokens) / len(title_tokens) if title_tokens else 0.0
    if len(title_tokens) >= 5 and title_overlap >= 0.8:
        warnings.append(f"opening_repeats_title:{title_overlap:.2f}")

    repeated_pairs = []
    scene_tokens = [
        {
            token.casefold()
            for token in _TOKEN_RE.findall(str(scene.get("narration") or ""))
            if token.casefold() not in _STORY_STOPWORDS
        }
        for scene in scenes
    ]
    for left in range(len(scene_tokens)):
        for right in range(left + 1, len(scene_tokens)):
            a, b = scene_tokens[left], scene_tokens[right]
            if len(a) < 7 or len(b) < 7:
                continue
            similarity = len(a & b) / len(a | b) if (a | b) else 0.0
            if similarity >= 0.8:
                repeated_pairs.append([left, right])
    if repeated_pairs:
        warnings.append(
            "repeated_narration_scenes:"
            + ",".join(f"{left + 1}-{right + 1}" for left, right in repeated_pairs[:10])
        )

    source_text = _source_evidence_text(plan).casefold()
    source_claims = {
        (match.group(2).casefold(), match.group(1).replace(",", "."))
        for match in _NUMBER_WITH_UNIT_RE.finditer(source_text)
    }
    unsupported_claims = []
    conflicting_claims = []
    if source_text:
        source_values_by_unit: Dict[str, set[str]] = {}
        for unit, value in source_claims:
            source_values_by_unit.setdefault(unit, set()).add(value)
        for index, scene in enumerate(scenes):
            narration = str(scene.get("narration") or "")
            for match in _NUMBER_WITH_UNIT_RE.finditer(narration):
                unit = match.group(2).casefold()
                value = match.group(1).replace(",", ".")
                claim = f"{index + 1}:{value}{unit}"
                if (unit, value) not in source_claims:
                    unsupported_claims.append(claim)
                    if source_values_by_unit.get(unit):
                        conflicting_claims.append(claim)
        if unsupported_claims:
            warnings.append("numeric_claims_not_in_source:" + ",".join(unsupported_claims[:10]))
        if conflicting_claims:
            warnings.append("numeric_source_conflicts:" + ",".join(conflicting_claims[:10]))

    final_narration = str(scenes[-1].get("narration") or "").strip() if scenes else ""
    has_viewer_prompt = bool(_AUDIENCE_PROMPT_RE.search(final_narration))
    ending_style = "viewer_prompt" if has_viewer_prompt else "statement" if final_narration else "missing"
    if ending_style == "missing":
        warnings.append("ending_scene_missing")
    elif ending_style == "statement" and len(_words(final_narration)) < ADVISORY_SCENE_WORDS:
        warnings.append("ending_is_brief_statement")

    return {
        "warnings": warnings,
        "opening_title_overlap": round(title_overlap, 3),
        "repeated_narration_pairs": repeated_pairs[:10],
        "numeric_source_check": "numeric claims only" if source_text else "source text unavailable",
        "ending_style": ending_style,
    }


def validate_script_quality(plan: Dict[str, Any], *, channel_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a deterministic report; never silently upgrades a weak script."""
    plan = plan or {}
    scenes = [s for s in (plan.get("scenes") or []) if isinstance(s, dict)]
    full = str(plan.get("full_narration") or " ".join(str(s.get("narration") or "") for s in scenes))
    words = _words(full)
    duration = sum(float(s.get("duration") or 0) for s in scenes)
    issues: List[str] = []
    warnings: List[str] = []

    # Duration: allow 38s-65s without hard fail (45-60.25 is target)
    if duration < 38.0 or duration > 65.0:
        issues.append(f"duration_out_of_band:{duration:.2f}")
    elif not (MIN_DURATION <= duration <= MAX_DURATION + 0.25):
        warnings.append(f"duration_near_band_edge:{duration:.2f}")

    if not (MIN_SCENES <= len(scenes) <= MAX_SCENES):
        if len(scenes) < 4:
            issues.append(f"scene_count_out_of_band:{len(scenes)}")
        else:
            warnings.append(f"scene_count_near_edge:{len(scenes)}")

    # Word count: 85-195 is hard band; 120-170 is optimal target
    if not (MIN_WORDS <= len(words) <= MAX_WORDS):
        issues.append(f"word_count_out_of_band:{len(words)}")
    elif len(words) < OPTIMAL_MIN_WORDS:
        warnings.append(f"word_count_below_optimal:{len(words)}_target_{OPTIMAL_MIN_WORDS}")
    elif len(words) > OPTIMAL_MAX_WORDS:
        warnings.append(f"word_count_above_optimal:{len(words)}_target_{OPTIMAL_MAX_WORDS}")

    if not scenes:
        issues.append("scenes_missing")

    fingerprints = [_scene_fingerprint(s) for s in scenes]
    repeated = [key for key, count in Counter(fingerprints).items() if key and count > 1]
    if repeated:
        warnings.append(f"repeated_scene_fingerprint:{len(repeated)}")

    for index, scene in enumerate(scenes):
        narration = str(scene.get("narration") or "").strip()
        description = str(scene.get("scene_description") or "").strip()
        queries = [str(q).strip() for q in (scene.get("search_queries") or []) if str(q).strip()]
        w_count = len(_words(narration))
        if w_count < MIN_SCENE_WORDS:
            issues.append(f"scene_{index}_words_below_{MIN_SCENE_WORDS}")
        elif w_count < ADVISORY_SCENE_WORDS:
            warnings.append(f"scene_{index}_words_below_{ADVISORY_SCENE_WORDS}")
        if not description or len(description) < 12 or "scene_description" in description.casefold():
            issues.append(f"scene_{index}_visual_description_invalid")
        if len(queries) < 2:
            issues.append(f"scene_{index}_queries_insufficient")
        if _FILLER_RE.search(narration):
            warnings.append(f"scene_{index}_mechanical_filler")
        if narration and narration[-1] not in ".!?":
            warnings.append(f"scene_{index}_missing_terminal")

    if len(words) < OPTIMAL_MIN_WORDS:
        warnings.append("regenerate_with_deeper_argument")
    if len(words) > OPTIMAL_MAX_WORDS:
        warnings.append("condense_by_removing_redundancy_not_generic_padding")
    if duration < 50:
        warnings.append("shorter_than_viewmade_style_default")

    story_quality = _story_quality_checks(plan, scenes)
    warnings.extend(story_quality["warnings"])

    hard = bool(issues)
    return {
        "ok": not hard,
        "action": "DROP" if hard else "RENDER_ALLOWED",
        "hard_fail": hard,
        "issues": issues,
        "warnings": warnings,
        "story_quality": story_quality,
        "duration": round(duration, 3),
        "scene_count": len(scenes),
        "word_count": len(words),
        "limits": {
            "min_duration": MIN_DURATION,
            "max_duration": MAX_DURATION,
            "min_scenes": MIN_SCENES,
            "max_scenes": MAX_SCENES,
            "min_words": MIN_WORDS,
            "max_words": MAX_WORDS,
            "min_scene_words": MIN_SCENE_WORDS,
        },
        "channel_profile": channel_profile or {},
    }


def build_policy_snapshot(*, ai_disclosure_required: bool = False, sources: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Record policy inputs without pretending that a URL fetch is legal proof."""
    from datetime import datetime, timezone

    urls = list(sources or [
        "https://support.google.com/youtube/answer/1311392",
        "https://support.google.com/youtube/answer/12504220",
        "https://support.google.com/youtube/answer/14328491",
        "https://support.google.com/youtube/answer/6162278",
        "https://support.google.com/youtube/answer/2801973",
        "https://support.google.com/youtube/answer/2797370",
    ])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_urls": urls,
        "source_confidence": "official_urls_snapshot_recheck_before_publish",
        "ai_disclosure_required": bool(ai_disclosure_required),
        "manual_recheck_required": True,
        "rules": {
            "no_mass_produced_repetitive_templates": True,
            "no_reuploads_or_fake_engagement": True,
            "license_manifest_required": True,
            "factual_claims_need_independent_evidence": True,
        },
    }
