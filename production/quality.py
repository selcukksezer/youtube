"""Hard quality gates for research-backed Shorts packages."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from production.quality_rules import (
    ADVISORY_SCENE_WORDS,
    MAX_ADVISORY_SCENE_WORDS,
    MAX_DURATION,
    MAX_HARD_SCENES,
    MAX_SCENE_CAPTION_EMPHASIS,
    MAX_SCENE_CLAIM_IDS,
    MAX_SCENE_DURATION,
    MAX_SCENE_MUST_EXCLUDE,
    MAX_SCENE_SEARCH_QUERIES,
    MAX_SCENES,
    MAX_TITLE_LENGTH,
    MAX_WORDS,
    MIN_DURATION,
    MIN_HARD_SCENES,
    MIN_SCENE_WORDS,
    MIN_SCENES,
    MIN_TITLE_LENGTH,
    MIN_WORDS,
    OPTIMAL_MAX_WORDS,
    OPTIMAL_MIN_WORDS,
    TARGET_MAX_DURATION,
    TARGET_MIN_DURATION,
    _AGE_CLAIM_RE,
    _AUDIENCE_PROMPT_RE,
    _CANONICAL_UNITS,
    _CURIOSITY_HOOK_RE,
    _DAY_FIRST_DATE_RE,
    _DOT_DAY_FIRST_DATE_RE,
    _FILLER_RE,
    _ISO_DATE_RE,
    _MONTH_FIRST_DATE_RE,
    _MONTH_NAME_PATTERN,
    _MONTH_NAME_TO_NUMBER,
    _MOOD_LABEL_RE,
    _NUMBER_VALUE_PATTERN,
    _NUMBER_WITH_UNIT_RE,
    _NUMBER_WORD_ATOM,
    _NUMBER_WORD_VALUES,
    _PLACEHOLDER_MARKERS,
    _PREMATURE_CLOSING_RE,
    _SLASH_ISO_DATE_RE,
    _STORY_STOPWORDS,
    _TOKEN_RE,
    _YEAR_CLAIM_RE,
    _canonical_numeric_claim,
    _extract_date_claims,
    _norm,
    _parse_number_value,
    _scene_fingerprint,
    _scene_queries,
    _source_evidence_text,
    _story_quality_checks,
    _words,
    validate_scene_durations,
)


def validate_script_quality(plan: Dict[str, Any], *, channel_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a deterministic report; never silently upgrades a weak script."""
    plan = plan or {}
    raw_scenes = plan.get("scenes")
    scenes = (
        [scene for scene in raw_scenes if isinstance(scene, dict)]
        if isinstance(raw_scenes, list)
        else []
    )
    scenes_invalid = raw_scenes is not None and (
        not isinstance(raw_scenes, list) or len(scenes) != len(raw_scenes)
    )
    scene_narration = " ".join(
        value for s in scenes
        if isinstance((value := s.get("narration")), str)
    )
    full_narration = str(plan.get("full_narration") or "")
    scene_words = _words(scene_narration)
    full_words = _words(full_narration)
    words = scene_words if scenes else full_words
    issues: List[str] = []
    warnings: List[str] = []

    title = plan.get("title")
    if not isinstance(title, str):
        issues.append("title_invalid")
    else:
        title_length = len(title.strip())
        if not MIN_TITLE_LENGTH <= title_length <= MAX_TITLE_LENGTH:
            issues.append(f"title_length_out_of_bounds:{title_length}")

    if scenes_invalid:
        issues.append("scenes_invalid")

    duration, duration_issues = validate_scene_durations(scenes)
    issues.extend(duration_issues)

    if scenes and full_narration and full_words != scene_words:
        issues.append("full_narration_mismatch")

    if duration < MIN_DURATION or duration > MAX_DURATION:
        issues.append(f"duration_out_of_band:{duration:.2f}")
    elif not (TARGET_MIN_DURATION <= duration <= TARGET_MAX_DURATION + 0.25):
        warnings.append(f"duration_near_band_edge:{duration:.2f}")

    if len(scenes) < MIN_HARD_SCENES:
        issues.append(f"scene_count_out_of_band:{len(scenes)}")
    elif len(scenes) > MAX_HARD_SCENES:
        issues.append(f"scene_count_exceeds_limit:{len(scenes)}")
    elif not (MIN_SCENES <= len(scenes) <= MAX_SCENES):
        warnings.append(f"scene_count_near_edge:{len(scenes)}")

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
        raw_narration = scene.get("narration")
        narration = raw_narration.strip() if isinstance(raw_narration, str) else ""
        if not isinstance(raw_narration, str):
            issues.append(f"scene_{index}_narration_invalid")
        elif any(marker in narration.casefold() for marker in _PLACEHOLDER_MARKERS):
            issues.append(f"scene_{index}_narration_placeholder")
        raw_description = scene.get("scene_description")
        description = raw_description.strip() if isinstance(raw_description, str) else ""
        queries = _scene_queries(scene)
        raw_queries = scene.get("search_queries")
        w_count = len(_words(narration))
        visual_intent = scene.get("visual_intent")
        if w_count < MIN_SCENE_WORDS:
            issues.append(f"scene_{index}_words_below_{MIN_SCENE_WORDS}")
        elif w_count < ADVISORY_SCENE_WORDS:
            warnings.append(f"scene_{index}_words_below_{ADVISORY_SCENE_WORDS}")
        elif w_count > MAX_ADVISORY_SCENE_WORDS:
            warnings.append(f"scene_{index}_words_above_{MAX_ADVISORY_SCENE_WORDS}")
        if (
            not description
            or len(description) < 12
            or any(marker in description.casefold() for marker in _PLACEHOLDER_MARKERS)
        ):
            issues.append(f"scene_{index}_visual_description_invalid")
        if raw_queries is not None and (
            not isinstance(raw_queries, list)
            or any(not isinstance(query, str) for query in raw_queries)
        ):
            issues.append(f"scene_{index}_queries_invalid")
        if len(queries) < 2:
            issues.append(f"scene_{index}_queries_insufficient")
        if isinstance(raw_queries, list) and len(raw_queries) > MAX_SCENE_SEARCH_QUERIES:
            issues.append(f"scene_{index}_queries_above_{MAX_SCENE_SEARCH_QUERIES}")
        for field, maximum in (
            ("claim_ids", MAX_SCENE_CLAIM_IDS),
            ("must_exclude", MAX_SCENE_MUST_EXCLUDE),
            ("caption_emphasis", MAX_SCENE_CAPTION_EMPHASIS),
        ):
            if field not in scene:
                continue
            values = scene[field]
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                issues.append(f"scene_{index}_{field}_invalid")
            elif len(values) > maximum:
                issues.append(f"scene_{index}_{field}_above_{maximum}")
        if visual_intent is not None and not isinstance(visual_intent, dict):
            issues.append(f"scene_{index}_visual_intent_invalid")
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
    issues.extend(story_quality["issues"])
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
            "target_min_duration": TARGET_MIN_DURATION,
            "target_max_duration": TARGET_MAX_DURATION,
            "max_scene_duration": MAX_SCENE_DURATION,
            "min_scenes": MIN_SCENES,
            "max_scenes": MAX_SCENES,
            "hard_min_scenes": MIN_HARD_SCENES,
            "hard_max_scenes": MAX_HARD_SCENES,
            "max_scene_claim_ids": MAX_SCENE_CLAIM_IDS,
            "max_scene_must_exclude": MAX_SCENE_MUST_EXCLUDE,
            "max_scene_caption_emphasis": MAX_SCENE_CAPTION_EMPHASIS,
            "min_title_length": MIN_TITLE_LENGTH,
            "max_title_length": MAX_TITLE_LENGTH,
            "min_words": MIN_WORDS,
            "max_words": MAX_WORDS,
            "min_scene_words": MIN_SCENE_WORDS,
            "max_advisory_scene_words": MAX_ADVISORY_SCENE_WORDS,
            "max_scene_search_queries": MAX_SCENE_SEARCH_QUERIES,
        },
        "channel_profile": channel_profile or {},
    }


def build_policy_snapshot(*, ai_disclosure_required: bool = False, sources: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Record policy inputs without pretending that a URL fetch is legal proof."""
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
