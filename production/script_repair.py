"""Bounded AI repair for production quality findings."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from production.quality import validate_script_quality

logger = logging.getLogger(__name__)

_REPAIRABLE_WARNING_PREFIXES = (
    "duration_near_band_edge:",
    "opening_repeats_title:",
    "word_count_below_optimal:",
    "word_count_above_optimal:",
    "scene_count_near_edge:",
)
_REPAIRABLE_WARNING_CODES = {
    "shorter_than_viewmade_style_default",
    "regenerate_with_deeper_argument",
}


def repairable_quality_findings(report: Dict[str, Any]) -> List[str]:
    findings = [
        issue for issue in report.get("issues", [])
        if isinstance(issue, str)
    ]
    warnings = [
        warning for warning in report.get("warnings", [])
        if isinstance(warning, str)
        and (
            warning in _REPAIRABLE_WARNING_CODES
            or warning.startswith(_REPAIRABLE_WARNING_PREFIXES)
            or (
                warning.startswith("scene_")
                and ("_words_below_" in warning or "_words_above_" in warning)
            )
        )
    ]
    return findings + warnings


def repair_script_quality_plan(
    plan: Dict[str, Any],
    report: Dict[str, Any],
    *,
    title: str,
    niche_id: str,
    language: str,
    channel_profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    findings = repairable_quality_findings(report)
    state = {
        "status": "not_needed",
        "findings_before": findings,
        "findings_after": findings,
        "warnings_before": [
            warning for warning in report.get("warnings", [])
            if warning in findings
        ],
        "warnings_after": [
            warning for warning in report.get("warnings", [])
            if warning in findings
        ],
    }
    if not findings:
        return {"plan": plan, "script_quality": report, "quality_repair": state}

    from scenes.generator import repair_script_quality

    generation = repair_script_quality(plan, findings, language=language)
    state["status"] = generation.get("status", "failed")
    if generation.get("error"):
        state["error"] = generation["error"]
    if generation.get("status") != "candidate":
        return {"plan": plan, "script_quality": report, "quality_repair": state}

    try:
        from director import compile_director_plan
        from scenes.narration_validate import sanitize_plan_scene_descriptions

        candidate = generation["plan"]
        director = compile_director_plan(
            candidate,
            title=candidate.get("title") or title,
            niche_id=niche_id,
            language=language,
        )
        repaired_plan = director.to_legacy_plan()
        for key, value in plan.items():
            if key not in {
                "title", "full_narration", "scenes", "meta",
                "niche_id", "director_plan",
            }:
                repaired_plan.setdefault(key, value)
        repaired_plan["meta"] = {
            **(plan.get("meta") if isinstance(plan.get("meta"), dict) else {}),
            **(repaired_plan.get("meta") if isinstance(repaired_plan.get("meta"), dict) else {}),
        }
        repaired_plan = sanitize_plan_scene_descriptions(repaired_plan)
        repaired_report = validate_script_quality(
            repaired_plan,
            channel_profile=channel_profile,
        )
    except Exception:
        logger.exception("AI script-quality repair candidate failed compilation")
        state["status"] = "failed"
        state["error"] = "Repaired script could not be compiled."
        return {"plan": plan, "script_quality": report, "quality_repair": state}

    remaining = repairable_quality_findings(repaired_report)
    state["findings_after"] = remaining
    state["warnings_after"] = [
        warning for warning in repaired_report.get("warnings", [])
        if warning in remaining
    ]
    no_new_hard_issues = set(repaired_report.get("issues", [])).issubset(
        set(report.get("issues", []))
    )
    if len(remaining) >= len(findings) or not no_new_hard_issues:
        state["status"] = "findings_remain"
        return {"plan": plan, "script_quality": report, "quality_repair": state}

    state["status"] = "repaired" if not remaining else "partially_repaired"
    director.meta["script_quality"] = repaired_report
    director.meta["render_allowed"] = bool(repaired_report.get("ok"))
    director.meta["script_quality_repair"] = state
    repaired_plan["meta"] = {
        **(repaired_plan.get("meta") if isinstance(repaired_plan.get("meta"), dict) else {}),
        "script_quality": repaired_report,
        "render_allowed": bool(repaired_report.get("ok")),
        "script_quality_repair": state,
    }
    return {
        "plan": repaired_plan,
        "director": director,
        "script_quality": repaired_report,
        "quality_repair": state,
    }
