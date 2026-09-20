"""
DirectorPlan Compiler — merges AI scene plan, niche profile, retention arc, visual intents.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from niche_templates import get_niche_production_profile

from .schema import (
    DirectorPlan,
    QualityThresholds,
    ScenePlan,
    merge_effect_manifest,
)
from .timeline import solve_timeline
from .validate import validate_director_plan
from .visual_intent import apply_visual_intents, resolve_niche_from_topic
from .audio_bus import build_audio_events


def _apply_beat_hints_advisory(plan: DirectorPlan) -> None:
    """P2-21: log advisory beat grid; attach beat_hint_ms — never changes durations."""
    if not plan.scenes:
        return
    try:
        from bgm_manager import (
            compute_scene_beat_hints,
            get_bgm_path,
            list_bgm_tracks,
            match_bgm_track_to_niche,
        )

        track = match_bgm_track_to_niche(plan.niche_id, list_bgm_tracks())
        bgm_path = get_bgm_path(track) if track else None
        hints = compute_scene_beat_hints(plan.scenes, bgm_path=bgm_path)
        for sc, hint in zip(plan.scenes, hints):
            sc.beat_hint_ms = hint.get("beat_hint_ms")
        if hints:
            bpm = hints[0].get("bpm", 120.0)
            deltas = [abs(h.get("delta_ms", 0)) for h in hints]
            avg_delta = sum(deltas) / max(1, len(deltas))
            cuts = ", ".join(f"{h.get('suggested_cut_ms', 0):.0f}ms" for h in hints[:4])
            suffix = "…" if len(hints) > 4 else ""
            print(
                f"  [Director] Beat hints (advisory, {bpm:.0f} BPM, avg Δ{avg_delta:.0f}ms): "
                f"[{cuts}{suffix}]"
            )
    except Exception as exc:
        print(f"  [Director] Beat hints skipped: {exc}")


def _cleanse_scene_narrations(raw_plan: Dict[str, Any]) -> None:
    """Item 134 / P1-09: strip AI clichés from scene narrations before compile."""
    try:
        from voice.script_humanizer import cleanse_ai_cliches
    except ImportError:
        return
    for s in raw_plan.get("scenes") or []:
        if isinstance(s, dict) and s.get("narration"):
            s["narration"] = cleanse_ai_cliches(str(s["narration"]))
    if raw_plan.get("full_narration"):
        raw_plan["full_narration"] = cleanse_ai_cliches(str(raw_plan["full_narration"]))


def _scenes_from_legacy(raw_plan: Dict[str, Any]) -> list:
    scenes = []
    for i, s in enumerate(raw_plan.get("scenes") or []):
        if isinstance(s, ScenePlan):
            scenes.append(s)
            continue
        queries = s.get("search_queries")
        if not queries and s.get("search_query"):
            queries = [s["search_query"]]
        scenes.append(ScenePlan.from_dict({**s, "search_queries": queries or []}, index=i))
    return scenes


def compile_director_plan(
    raw_plan: Optional[Dict[str, Any]] = None,
    *,
    title: str = "",
    niche_id: str = "1_news_flash",
    language: str = "tr",
    reddit_post: Optional[Dict[str, Any]] = None,
) -> DirectorPlan:
    """
    Normalize legacy AI plan → DirectorPlan, lock niche from topic,
    solve timeline, attach visual intents + audio event bus, validate.
    """
    raw_plan = dict(raw_plan or {})
    title = title or raw_plan.get("title") or "Video"
    requested_niche = niche_id or raw_plan.get("niche_id") or "1_news_flash"
    locked_niche = resolve_niche_from_topic(title, requested_niche)
    if locked_niche != requested_niche:
        print(f"  [Director] Nis kilitlendi: '{requested_niche}' -> '{locked_niche}' (konu uyumu)")

    _cleanse_scene_narrations(raw_plan)

    from scenes.narration_validate import apply_auto_repair_if_needed
    from scenes.narration_coherence import repair_cross_scene_coherence

    raw_plan, coherence_fixes = repair_cross_scene_coherence(raw_plan)
    if coherence_fixes:
        print(f"  [Director] Split-fiil birleştirildi: {coherence_fixes}")

    raw_plan, narr_fixes, _ = apply_auto_repair_if_needed(raw_plan)
    if narr_fixes:
        print(f"  [Director] Anlatım otomatik düzeltildi: {len(narr_fixes)} fix")

    niche_profile = get_niche_production_profile(locked_niche)
    scenes = _scenes_from_legacy(raw_plan)

    plan = DirectorPlan(
        title=title,
        niche_id=locked_niche,
        language=language,
        full_narration=str(raw_plan.get("full_narration", "")),
        scenes=scenes,
        niche_profile=niche_profile,
        effect_manifest=merge_effect_manifest(niche_profile),
        quality_thresholds=QualityThresholds(),
        visual_theme=str(raw_plan.get("visual_theme", "")),
        hook_text=str(raw_plan.get("hook_text", "")),
        loop_text=str(raw_plan.get("loop_text", "")),
        reddit_post=reddit_post or raw_plan.get("reddit_post"),
        meta={
            "requested_niche": requested_niche,
            "locked_niche": locked_niche,
            "source": "compile_director_plan",
        },
    )

    if not plan.scenes and plan.full_narration:
        # Minimal single-scene fallback split by sentences
        parts = [p.strip() for p in plan.full_narration.replace("!", ".").replace("?", ".").split(".") if p.strip()]
        if not parts:
            parts = [plan.full_narration]
        plan.scenes = [
            ScenePlan(index=i, narration=p, duration=3.0, scene_description=p[:80])
            for i, p in enumerate(parts[:16])
        ]

    plan = solve_timeline(plan)

    # Post-timeline split-verb repair (cadence pad may have left fragments)
    legacy_mid = plan.to_legacy_plan()
    legacy_mid, mid_coherence = repair_cross_scene_coherence(legacy_mid)
    if mid_coherence:
        print(f"  [Director] Post-timeline split-fiil düzeltildi: {mid_coherence}")
        plan.scenes = [
            ScenePlan.from_dict(s, index=i)
            for i, s in enumerate(legacy_mid.get("scenes") or [])
        ]
        plan = solve_timeline(plan)

    # Post-condense repair — only when timeline left fragments (P0-02)
    from scenes.narration_validate import auto_repair_plan, scene_narration_issues
    needs_post_repair = any(scene_narration_issues(s.narration or "") for s in plan.scenes)
    post_fixes = []
    if needs_post_repair:
        legacy_after = plan.to_legacy_plan()
        repaired_after, post_fixes = auto_repair_plan(legacy_after)
    if post_fixes:
        print(f"  [Director] Post-condense anlatım düzeltildi: {len(post_fixes)} fix")
        for i, sc in enumerate(plan.scenes):
            if i < len(repaired_after.get("scenes") or []):
                sc.narration = repaired_after["scenes"][i].get("narration", sc.narration)
        if len(repaired_after.get("scenes") or []) != len(plan.scenes):
            from .schema import ScenePlan
            plan.scenes = [
                ScenePlan.from_dict(s, index=i)
                for i, s in enumerate(repaired_after.get("scenes") or [])
            ]
            plan = solve_timeline(plan)

    apply_visual_intents(plan.scenes, plan.niche_id, title=plan.title)
    build_audio_events(plan)
    _apply_beat_hints_advisory(plan)
    # Always rebuild from condensed scenes (never keep stale long raw narration)
    plan.rebuild_full_narration()
    validate_director_plan(plan)

    # Hook / loop hints from first/last narration
    if plan.scenes:
        plan.hook_text = plan.hook_text or (plan.scenes[0].narration or "")[:120]
        plan.loop_text = plan.loop_text or (plan.scenes[-1].narration or "")[:120]

    print(
        f"  [Director] Plan derlendi: {len(plan.scenes)} sahne, "
        f"{plan.total_duration():.1f}s, niş={plan.niche_id}, "
        f"SFX={len(plan.audio_events)}, valid={plan.validation.get('ok')}"
    )
    return plan
