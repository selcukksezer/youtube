"""
DirectorPlan pre-flight validation (Items 88, 129, 201-204, 274, 494).
"""
from __future__ import annotations

from typing import Any, Dict, List

from .quality_gate import check_narration_integrity
from .schema import DirectorPlan


def validate_director_plan(plan: DirectorPlan) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    qt = plan.quality_thresholds

    n = len(plan.scenes)
    if n < qt.min_scenes:
        errors.append(f"Madde 88: en az {qt.min_scenes} görsel kesim gerekli, şu an {n}")

    total = plan.total_duration()
    if total < qt.min_duration or total > qt.max_duration:
        errors.append(
            f"Madde 494: süre {total:.1f}s hedef dışı ({qt.min_duration}-{qt.max_duration}s)"
        )

    if plan.scenes:
        if plan.scenes[0].beat_type != "hook" and plan.scenes[0].t1 > 3.5:
            warnings.append("Madde 201-203: ilk sahne hook beat olarak işaretlenmeli")
        hook_end = plan.scenes[0].t1 if plan.scenes else 0
        if hook_end > 4.0:
            warnings.append("Madde 201: hook penceresi 0-3s ideal; ilk sahne uzun")

    climax_scenes = [s for s in plan.scenes if s.beat_type == "climax"]
    if not climax_scenes and total >= 30:
        warnings.append("Madde 225/274: climax beat atanmamış")

    if not (plan.full_narration or "").strip():
        errors.append("full_narration boş")

    word_count = len((plan.full_narration or "").split())
    # Rough intelligibility: ~2.8 words/sec at natural rate for 42s ≈ 118 words
    target_words = int(qt.target_duration * 2.6)
    if word_count > int(target_words * qt.max_audio_speed * 1.05):
        warnings.append(
            f"Narration {word_count} kelime; ~{target_words} hedef — TTS hız tavanı aşılabilir"
        )

    for ni in check_narration_integrity(plan):
        if ni.startswith("fragment"):
            errors.append(f"Kopuk cümle: {ni}")
        elif ni.startswith("low_words"):
            errors.append(f"Sahne kelime sayısı düşük: {ni}")
        else:
            errors.append(ni)

    alignment_flags = 0
    for s in plan.scenes:
        if s.visual_intent and s.visual_intent.must_exclude:
            alignment_flags += 1
        if not (s.search_queries or s.visual_intent.search_queries):
            warnings.append(f"Sahne {s.index}: search_queries boş")

    ok = len(errors) == 0
    result = {
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "scene_count": n,
        "total_duration": total,
        "word_count": word_count,
        "visual_intent_coverage": alignment_flags,
        "roadmap_items_checked": [88, 129, 201, 274, 494],
    }
    plan.validation = result
    return result
