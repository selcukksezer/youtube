"""Hard quality gates for research-backed Shorts packages."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional


MIN_DURATION = 45.0
MAX_DURATION = 60.0
MIN_SCENES = 6
MAX_SCENES = 12
MIN_WORDS = 120
MAX_WORDS = 170
MIN_SCENE_WORDS = 12

_FILLER_RE = re.compile(
    r"\b(bunu aklında tut|bunu aklinda tut|takipte kalın|takipte kalin|"
    r"yorumlarda paylaşın|yorumlarda paylasin|like atın|abone olun)\b",
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


def validate_script_quality(plan: Dict[str, Any], *, channel_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a deterministic report; never silently upgrades a weak script."""
    plan = plan or {}
    scenes = [s for s in (plan.get("scenes") or []) if isinstance(s, dict)]
    full = str(plan.get("full_narration") or " ".join(str(s.get("narration") or "") for s in scenes))
    words = _words(full)
    duration = sum(float(s.get("duration") or 0) for s in scenes)
    issues: List[str] = []
    warnings: List[str] = []

    if not (MIN_DURATION <= duration <= MAX_DURATION + 0.25):
        issues.append(f"duration_out_of_band:{duration:.2f}")
    if not (MIN_SCENES <= len(scenes) <= MAX_SCENES):
        issues.append(f"scene_count_out_of_band:{len(scenes)}")
    if not (MIN_WORDS <= len(words) <= MAX_WORDS):
        issues.append(f"word_count_out_of_band:{len(words)}")
    if not scenes:
        issues.append("scenes_missing")
    elif str(scenes[0].get("beat_type") or "").casefold() != "hook":
        issues.append("hook_beat_missing")

    fingerprints = [_scene_fingerprint(s) for s in scenes]
    repeated = [key for key, count in Counter(fingerprints).items() if key and count > 1]
    if repeated:
        issues.append(f"repeated_scene_fingerprint:{len(repeated)}")

    for index, scene in enumerate(scenes):
        narration = str(scene.get("narration") or "").strip()
        description = str(scene.get("scene_description") or "").strip()
        queries = [str(q).strip() for q in (scene.get("search_queries") or []) if str(q).strip()]
        if len(_words(narration)) < MIN_SCENE_WORDS:
            issues.append(f"scene_{index}_words_below_{MIN_SCENE_WORDS}")
        if not description or len(description) < 12 or "scene_description" in description.casefold():
            issues.append(f"scene_{index}_visual_description_invalid")
        if len(queries) < 2:
            issues.append(f"scene_{index}_queries_insufficient")
        if _FILLER_RE.search(narration):
            issues.append(f"scene_{index}_mechanical_filler")
        if narration and narration[-1] not in ".!?":
            issues.append(f"scene_{index}_missing_terminal")

    if len(words) < MIN_WORDS:
        warnings.append("regenerate_with_deeper_argument")
    if len(words) > MAX_WORDS:
        warnings.append("condense_by_removing_redundancy_not_generic_padding")
    if duration < 50:
        warnings.append("shorter_than_viewmade_style_default")

    hard = bool(issues)
    return {
        "ok": not hard,
        "action": "DROP" if hard else "RENDER_ALLOWED",
        "hard_fail": hard,
        "issues": issues,
        "warnings": warnings,
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

