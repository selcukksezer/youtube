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
    DirectorScene,
    merge_effect_manifest,
)
from .timeline import solve_timeline
from .validate import validate_director_plan
from .visual_intent import apply_visual_intents, resolve_topic_intelligence
from .audio_bus import build_audio_events
from visuals.mixed_visual import is_mixed_mode, mixed_scene_mode


def _apply_beat_hints_advisory(plan: DirectorPlan) -> None:
    """Bölüm 7.3: Snap scene cuts onto 80-120 BPM track beats with speech word-count shield."""
    if not plan.scenes:
        return
    try:
        from bgm_manager import (
            get_bgm_path,
            list_bgm_tracks,
            match_bgm_track_to_niche,
            snap_timeline_to_beat_grid,
            normalize_bpm_to_shorts_band,
            parse_bgm_bpm,
        )

        track = match_bgm_track_to_niche(plan.niche_id, list_bgm_tracks())
        bgm_path = get_bgm_path(track) if track else None
        
        # 80-120 BPM hipnotik kurgu aralığına kilitlenmiş timeline beat-snapping
        plan.scenes = snap_timeline_to_beat_grid(
            plan.scenes,
            bgm_path=bgm_path or "",
            enforce_band=True,
            min_scene_dur=1.8,
            max_scene_dur=7.0,
        )
        
        bpm = normalize_bpm_to_shorts_band(parse_bgm_bpm(bgm_path or ""))
        plan.meta["beat_bpm"] = bpm
        cap = float((plan.quality_thresholds.max_duration if plan.quality_thresholds else 60.0) or 60.0)
        snapped = plan.total_duration()
        if snapped > cap + 0.05 and plan.scenes:
            scale = cap / snapped
            t = 0.0
            for scene in plan.scenes:
                scene.duration = round(max(0.8, scene.duration * scale), 3)
                scene.t0 = round(t, 3)
                t = round(t + scene.duration, 3)
                scene.t1 = t
            drift = cap - plan.scenes[-1].t1
            plan.scenes[-1].duration = round(plan.scenes[-1].duration + drift, 3)
            plan.scenes[-1].t1 = round(plan.scenes[-1].t0 + plan.scenes[-1].duration, 3)
        
        if plan.time_map is not None:
            plan.time_map["target_duration"] = plan.total_duration()
            plan.time_map["beat_bpm"] = bpm
            plan.time_map["cuts"] = [
                {"index": s.index, "t0": s.t0, "t1": s.t1, "beat": s.beat_type}
                for s in plan.scenes
            ]
        print(
            f"  [Director] Beat snap ({bpm:.0f} BPM, 80-120 band): "
            + ", ".join(f"{s.t1:.2f}s" for s in plan.scenes[:4])
        )
    except Exception as exc:
        print(f"  [Director] Beat hints skipped: {exc}")


def _apply_fact_verification(plan: DirectorPlan) -> None:
    """Bölüm 7.4: Senaryodaki sayısal ve tarihsel iddiaları web kaynaklarıyla çapraz doğrular ve teyitsizleri arındırır."""
    if not plan.scenes:
        return
    try:
        from services.web_fact_researcher import verify_and_sanitize_scenes
        hook = str(((plan.meta or {}).get("retention_metadata") or {}).get("opening_hook") or "")
        cached = (plan.meta or {}).get("fact_snippets", None)
        plan.scenes, fact_report = verify_and_sanitize_scenes(
            plan.scenes,
            topic=plan.title or "",
            web_snippets=cached,
            protect_text=hook,
        )
        plan.rebuild_full_narration()
        plan.meta["fact_verification"] = fact_report
        if fact_report.get("sanitized_count", 0) > 0:
            print(
                f"  [FactResearcher] Anti-hallucination: {fact_report['sanitized_count']} teyitsiz iddia güvenli forma dönüştürüldü."
            )
    except Exception as exc:
        print(f"  [FactResearcher] Fact verification notice: {exc}")


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
    plan_vm = raw_plan.get("visual_mode")
    scenes = []
    for i, s in enumerate(raw_plan.get("scenes") or []):
        if isinstance(s, ScenePlan):
            if is_mixed_mode(plan_vm) and (not s.visual_mode or is_mixed_mode(s.visual_mode)):
                s.visual_mode = mixed_scene_mode(i)
            elif plan_vm and not s.visual_mode:
                s.visual_mode = plan_vm
            scenes.append(s)
            continue
        queries = s.get("search_queries")
        if not queries and s.get("search_query"):
            queries = [s["search_query"]]
        s_data = {**s, "search_queries": queries or []}
        if is_mixed_mode(plan_vm) and (
            not s_data.get("visual_mode") or is_mixed_mode(s_data.get("visual_mode"))
        ):
            s_data["visual_mode"] = mixed_scene_mode(i)
        elif plan_vm and not s_data.get("visual_mode"):
            s_data["visual_mode"] = plan_vm
        scenes.append(ScenePlan.from_dict(s_data, index=i))
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
    if requested_niche and requested_niche != "1_news_flash":
        locked_niche = requested_niche
        topic_intel = resolve_topic_intelligence(title, requested_niche)
    else:
        topic_intel = resolve_topic_intelligence(title, requested_niche)
        locked_niche = topic_intel["resolved_niche"]

    try:
        from scenes.fallback import _generate_procedural_fallback_scenes
        from scenes.narration_validate import plan_needs_procedural_inject

        if plan_needs_procedural_inject(raw_plan.get("scenes") or []):
            print("  [Director] Anlatım boş veya placeholder — prosedürel fallback enjekte ediliyor")
            fb = _generate_procedural_fallback_scenes(
                title,
                niche_type=locked_niche,
                language=language,
            )
            raw_plan.update(fb)
    except Exception as exc:
        print(f"  [Director] Fallback enjekte edilemedi: {exc}")

    if locked_niche != requested_niche:
        print(f"  [Director] Nis kilitlendi: '{requested_niche}' -> '{locked_niche}' (konu uyumu)")
    hybrid_id = topic_intel.get("hybrid_niche") or raw_plan.get("hybrid_niche")
    hybrid_meta: Dict[str, Any] = {}
    if hybrid_id:
        try:
            from hybrid_niches import get_hybrid_niche, get_hybrid_render_overlay_spec
            hybrid_def = get_hybrid_niche(hybrid_id)
            hybrid_meta = {
                "hybrid_niche": hybrid_id,
                "hybrid_split_screen": raw_plan.get("hybrid_split_screen", hybrid_def.get("split_screen_default", False)),
                "hybrid_bg_style": hybrid_def.get("bg_style", ""),
                "hybrid_render_overlay": raw_plan.get("hybrid_render_overlay") or get_hybrid_render_overlay_spec(hybrid_id),
            }
            print(f"  [Director] Hibrit niş: {hybrid_id} ({topic_intel.get('match_method')})")
        except ImportError:
            hybrid_meta = {"hybrid_niche": hybrid_id}
    if raw_plan.get("retention_metadata"):
        hybrid_meta["retention_metadata"] = raw_plan["retention_metadata"]
    if "fact_snippets" in raw_plan:
        hybrid_meta["fact_snippets"] = raw_plan.get("fact_snippets") or []
    if raw_plan.get("hybrid_split_screen") and hybrid_id:
        hybrid_meta["hybrid_split_screen"] = True

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
    try:
        from scenes.hadith_overlay import attach_hadith_screen_text
        raw_plan["niche_id"] = locked_niche
        raw_plan["title"] = title
        attach_hadith_screen_text(raw_plan)
    except Exception as exc:
        print(f"  [Director] Hadis Arapça satırı eklenemedi: {exc}")
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
        visual_mode=raw_plan.get("visual_mode"),
        meta={
            "requested_niche": requested_niche,
            "locked_niche": locked_niche,
            "source": "compile_director_plan",
            "topic_intelligence": {
                "match_method": topic_intel.get("match_method"),
                "hybrid_niche": hybrid_id,
            },
            **hybrid_meta,
        },
    )
    if hybrid_id and not plan.loop_text:
        try:
            from hybrid_niches import get_hybrid_niche
            loop = get_hybrid_niche(hybrid_id).get("loop_bridge")
            if loop:
                plan.loop_text = loop
        except ImportError:
            pass

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
    _apply_fact_verification(plan)
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
