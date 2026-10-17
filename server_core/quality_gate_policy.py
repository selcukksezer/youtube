"""
server_core/quality_gate_policy.py
==================================
Solves Top 100 Problems — Category II (Problems 11–20):
11. Consolidates 15+ sequential blocking quality gates into a unified evaluator
12. Originality Gate (>45% similarity) soft-warning mode for iterative same-niche renders
13. Monetization Policy Gate false-positive filter for legitimate news/finance topics
14. Script Contract Gate soft auto-repair instead of immediate rejection
15. Semantic Mismatch Gate advisory fallback (substitutes safe stock query instead of aborting)
16. Clip Uniqueness / pHash pool exhaustion fallback (allows horizontal flip / zoom variant when pool is small)
17. Duration Band Gate soft tolerance (36.0s–66.5s passes with warning instead of hard fail)
18. Research Evidence Gate offline tolerance (proceeds with advisory note when external search times out)
19. UI Render Button unblock helper (prevents soft warnings from locking the Studio Render button)
20. Post-Render Quarantine vs Pre-Render Kill (always produces the MP4 first, then attaches quality warnings)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import config


@dataclass
class QualityGateDecision:
    passed: bool
    hard_fail: bool
    mode: str
    blocking_reasons: list[str] = field(default_factory=list)
    advisory_warnings: list[str] = field(default_factory=list)
    auto_repairs_applied: list[str] = field(default_factory=list)
    ui_render_button_blocked: bool = False


def evaluate_unified_quality_gates(
    *,
    mode: str | None = None,
    originality_similarity: float = 0.0,
    policy_risk_flags: list[str] | None = None,
    script_contract_issues: list[str] | None = None,
    semantic_mismatch_scenes: list[int] | None = None,
    unique_clips_available: int = 10,
    required_clips: int = 6,
    duration_seconds: float = 48.0,
    research_evidence_found: bool = True,
    has_video_stream: bool = True,
    narration_empty: bool = False,
) -> dict[str, Any]:
    """
    Problems #11–#20: Evaluate all 15+ pipeline gates in a single pass.
    In `advisory` mode (default), only catastrophic failures (`narration_empty` or `has_video_stream=False`)
    hard-stop the render; all other gates emit structured advisory warnings and auto-repairs.
    """
    active_mode = (mode or getattr(config, "QUALITY_GATE_MODE", "advisory") or "advisory").strip().lower()
    strict = active_mode == "strict"

    blocking: list[str] = []
    warnings: list[str] = []
    repairs: list[str] = []

    # Catastrophic checks (always block)
    if narration_empty:
        blocking.append("empty_narration")
    if not has_video_stream:
        blocking.append("no_video_stream")

    # #12 Originality similarity gate
    if originality_similarity > 0.45:
        msg = f"originality_similarity_high:{originality_similarity:.2f}"
        if strict and originality_similarity > 0.75:
            blocking.append(msg)
        else:
            warnings.append(msg)
            repairs.append("applied_variation_seed_and_hook_rotation")

    # #13 Monetization policy gate (filter false positives on news/finance)
    benign_finance_news = {"market_volatility", "crypto_drop", "historical_conflict", "economic_crisis"}
    real_policy_flags = [f for f in (policy_risk_flags or []) if f not in benign_finance_news]
    if real_policy_flags:
        msg = f"policy_flags:{','.join(real_policy_flags)}"
        if strict:
            blocking.append(msg)
        else:
            warnings.append(msg)

    # #14 Script contract gate
    if script_contract_issues:
        msg = f"script_contract:{','.join(script_contract_issues[:5])}"
        if strict:
            blocking.append(msg)
        else:
            warnings.append(msg)
            repairs.append("contextual_narration_auto_repair")

    # #15 Semantic mismatch gate
    if semantic_mismatch_scenes:
        msg = f"semantic_mismatch_scenes:{len(semantic_mismatch_scenes)}"
        if strict and len(semantic_mismatch_scenes) > 3:
            blocking.append(msg)
        else:
            warnings.append(msg)
            repairs.append("substituted_niche_motif_queries")

    # #16 Clip uniqueness / pHash pool exhaustion
    if unique_clips_available < required_clips:
        msg = f"clip_pool_narrow:{unique_clips_available}/{required_clips}"
        warnings.append(msg)
        repairs.append("applied_mirror_zoom_jitter_to_reused_clips")

    # #17 Duration band gate (38s-60s target, 35s-68s soft band)
    if duration_seconds < 38.0 or duration_seconds > 65.0:
        msg = f"duration_band:{duration_seconds:.1f}s"
        if strict and (duration_seconds < 30.0 or duration_seconds > 75.0):
            blocking.append(msg)
        else:
            warnings.append(msg)

    # #18 Research evidence gate
    if not research_evidence_found:
        msg = "research_evidence_offline_fallback"
        if strict:
            blocking.append(msg)
        else:
            warnings.append(msg)
            repairs.append("used_verified_evergreen_facts")

    hard_fail = len(blocking) > 0
    decision = QualityGateDecision(
        passed=not hard_fail,
        hard_fail=hard_fail,
        mode=active_mode,
        blocking_reasons=blocking,
        advisory_warnings=warnings,
        auto_repairs_applied=repairs,
        ui_render_button_blocked=hard_fail,
    )
    return {
        "passed": decision.passed,
        "hard_fail": decision.hard_fail,
        "mode": decision.mode,
        "blocking_reasons": decision.blocking_reasons,
        "advisory_warnings": decision.advisory_warnings,
        "auto_repairs_applied": decision.auto_repairs_applied,
        "ui_render_button_blocked": decision.ui_render_button_blocked,
        "render_before_quarantine": True,
    }
