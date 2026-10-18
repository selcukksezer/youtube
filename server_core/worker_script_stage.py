"""
Render Worker Stage 1–4: Script Generation, Human Craft, DirectorPlan Compilation,
Originality Gate (Item 120), Pre-Render Quality Gate, and Monetization Compliance Gate.
Extracted from server_core/render_worker.py for modularity.
"""
import json
import os
from typing import Any, Callable, Dict, Optional, Tuple

import config
import database
from niche_templates import get_niche_production_profile
from plagiarism_checker import check_script_originality
from scene_generator import generate_scenes
from . import state
from .pipeline_state_machine import PipelineStage


def run_script_and_director_stage(
    *,
    req: Any,
    plan: Optional[Dict[str, Any]],
    keyword: str,
    locked_niche: str,
    target_lang: str,
    vm: Any,
    proj: str,
    ch_paths: Dict[str, str],
    db_id: Optional[int],
    sm: Any,
    check_cancelled: Callable[[], None],
    log_fn: Callable[..., None],
    stamp_visual_mode_fn: Callable[[Any, Any], None],
    ensure_ui_plan_fn: Callable[[Any, str, str, str], Any],
    quality_report_allows_render_fn: Callable[..., bool],
) -> Tuple[bool, Optional[Dict[str, Any]], Any, str, int, Dict[str, Any]]:
    """
    Executes Stages 2, 3, and 4 of the render pipeline.
    Returns (ok_to_continue, plan, director, keyword, final_variation_attempt, pre_result).
    """
    from director import (
        apply_visual_intents,
        build_audio_events,
        compile_director_plan,
        pre_render_score,
        scenes_needing_regen,
    )

    MAX_ORIGINALITY_RETRIES = 3
    use_director = getattr(config, "ENABLE_DIRECTOR_PLAN", True)
    director = None
    is_original = False
    similarity = 0.0
    matched_title = None
    final_variation_attempt = 0
    lang_label = "İngilizce" if target_lang == "en" else "Türkçe"
    pre_result: Dict[str, Any] = {}

    narration_repaired = False

    for orig_attempt in range(MAX_ORIGINALITY_RETRIES):
        final_variation_attempt = orig_attempt
        narration_repaired = False
        check_cancelled()
        if orig_attempt > 0 or not plan:
            if orig_attempt == 0:
                sm.transition_to(
                    PipelineStage.STAGE_2_HOOK_NARRATIVE,
                    f"Kanca ve Anlatı Üretimi: '{keyword}' (Niş: {locked_niche})",
                    pct=8.0,
                )
                log_fn(
                    f"[Director] AI senaryosu oluşturuluyor ({lang_label} - {config.AI_PROVIDER}, "
                    f"niş={locked_niche}): '{keyword}'",
                    12,
                )
            else:
                log_fn(
                    f"[Item 120] Benzerlik yüksek (%{similarity * 100:.1f}) — "
                    f"senaryo yeniden üretiliyor ({orig_attempt + 1}/{MAX_ORIGINALITY_RETRIES})...",
                    14 + orig_attempt,
                )
            if req.reddit_post and locked_niche == "2_reddit_confessions":
                from scene_generator import generate_reddit_rewrite_script

                source_text = f"{req.reddit_post.get('title', '')}\n{req.reddit_post.get('body', '')}"
                plan = generate_reddit_rewrite_script(source_text, lang=target_lang)
                plan["reddit_post"] = req.reddit_post
            else:
                plan = generate_scenes(
                    keyword,
                    niche_type=locked_niche,
                    language=target_lang,
                    variation_attempt=orig_attempt,
                    enable_outro=getattr(req, "enable_outro", True) is not False,
                )
            stamp_visual_mode_fn(plan, vm)
            try:
                from hybrid_niches import enrich_plan_with_hybrid

                plan = enrich_plan_with_hybrid(plan, keyword, locked_niche)
            except Exception:
                pass

        if req.reddit_post and locked_niche == "2_reddit_confessions" and isinstance(plan, dict):
            plan["reddit_post"] = req.reddit_post

        if orig_attempt == 0 and plan:
            plan = ensure_ui_plan_fn(plan, keyword, locked_niche, target_lang)

        from scenes.retention_hooks import ensure_retention_hooks_on_plan

        try:
            from craft import apply_human_craft

            plan = apply_human_craft(
                plan,
                title=keyword,
                niche_id=locked_niche,
                language=target_lang,
                variation=orig_attempt,
            )
            db = (plan.get("human_craft") or {}).get("discovery_beast") or {}
            log_fn(
                f"[HumanCraft] POV={(plan.get('human_craft') or {}).get('pov_angle')} "
                f"discovery={db.get('score')} pass={db.get('pass')}",
                15,
            )
        except Exception as hc_err:
            log_fn(f"[HumanCraft] skip: {hc_err}")

        plan = ensure_retention_hooks_on_plan(
            plan,
            keyword,
            lang=target_lang,
            niche_type=locked_niche,
            variation_attempt=orig_attempt,
            enable_outro=getattr(req, "enable_outro", True) is not False,
        )
        try:
            from scenes.enrichment import enrich_plan_scenes

            plan = enrich_plan_scenes(plan, lang=target_lang, niche_id=locked_niche)
        except Exception:
            pass
        try:
            from scenes.enrichment import enforce_specific_search_queries

            if plan.get("scenes"):
                enforce_specific_search_queries(plan["scenes"])
        except Exception:
            pass
        meta = plan.get("retention_metadata") or {}
        if meta.get("hook_strategy"):
            log_fn(
                f"[RetentionHooks] {meta.get('hook_strategy')} | "
                f"opening: {(meta.get('opening_hook') or '')[:60]}…",
                16,
            )

        check_cancelled()
        sm.transition_to(
            PipelineStage.STAGE_3_DIRECTOR_PLAN,
            "DirectorPlan derleniyor (timeline + visual intent + audio bus)",
            pct=18.0,
        )
        log_fn("[Director] DirectorPlan derleniyor (timeline + visual intent + audio bus)...", 18)
        director = None
        if use_director:
            director = compile_director_plan(
                plan,
                title=keyword,
                niche_id=locked_niche,
                language=target_lang,
                reddit_post=getattr(req, "reddit_post", None),
            )
            plan = director.to_legacy_plan()
            narration_repaired = True
            log_fn(
                f"[Timeline] {len(director.scenes)} sahne | {director.total_duration():.1f}s | "
                f"niş={director.niche_id} | SFX={len(director.audio_events)}",
                22,
            )
            if director.validation and not director.validation.get("ok"):
                for err in director.validation.get("errors") or []:
                    log_fn(f"[Director][Uyarı] {err}")
        else:
            plan["niche_profile"] = get_niche_production_profile(locked_niche)

        with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        if director:
            with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)

        sm.transition_to(
            PipelineStage.STAGE_4_ORIGINALITY_GATE,
            "Özgünlük Kontrolü (Madde 120) ve Senaryo Kalite Kapısı",
            pct=25.0,
        )
        allow_similar = bool(
            getattr(req, "allow_similar_script", False)
            or getattr(req, "force_render", False)
            or getattr(req, "allow_draft_render", False)
        )
        is_original, similarity, matched_title = check_script_originality(
            plan.get("full_narration", ""),
            keyword=keyword,
            title=plan.get("title", keyword),
            auto_add_if_approved=False,
            only_completed_renders=True,
            allow_similar_script=allow_similar,
            channel_slug=ch_paths["slug"],
        )
        if is_original:
            if similarity >= 0.45 and allow_similar:
                log_fn(
                    f"[QualityGate] UYARI: Senaryo benzerlik eşiğini aştı (%{similarity * 100:.1f} - '{matched_title}'), "
                    "ancak 'Yine De Devam Et' seçeneği aktif olduğu için render onaylandı.",
                    25,
                )
            break
        plan = None

    if not is_original:
        allow_similar = bool(
            getattr(req, "allow_similar_script", False)
            or getattr(req, "force_render", False)
            or getattr(req, "allow_draft_render", False)
            or not getattr(config, "STRICT_ORIGINALITY_GATE", False)
        )
        if allow_similar:
            log_fn(
                f"[QualityGate] UYARI: Senaryo benzerliği yüksek (%{similarity * 100:.1f}), "
                "ancak 'Yine De Devam Et' / esnek mod aktif, render devam ediyor.",
                25,
            )
        else:
            message = (
                f"Senaryo benzerlik eşiğini aştı (%{similarity * 100:.1f}); "
                f"en yakın kayıt: {matched_title or 'bilinmiyor'}. "
                "İçerik ve videolar farklıysa 'Yine De Devam Et' seçeneği ile render alabilirsiniz."
            )
            if db_id:
                database.update_video_status(db_id, "failed", error_message=message)
            state.broadcast_event("error", message)
            return False, plan, director, keyword, final_variation_attempt, pre_result

    if isinstance(plan, dict):
        plan.setdefault("meta", {})
        plan["meta"]["originality"] = {
            "similarity": round(float(similarity), 4),
            "originality_score": round(max(0.0, (1.0 - float(similarity)) * 100.0), 1),
            "matched_title": matched_title or "",
        }

    repaired_for_director: Optional[Dict[str, Any]] = None
    try:
        from production.quality import validate_script_quality

        script_quality = validate_script_quality(plan or {})
        plan.setdefault("meta", {})
        plan["meta"]["script_quality"] = script_quality
        if director is not None:
            from production.script_repair import repair_script_quality_plan

            repair_result = repair_script_quality_plan(
                plan or {},
                script_quality,
                title=keyword,
                niche_id=locked_niche,
                language=target_lang,
            )
            quality_repair = repair_result["quality_repair"]
            if quality_repair["status"] in ("repaired", "partially_repaired"):
                plan = repair_result["plan"]
                director = repair_result["director"]
                keyword = plan.get("title") or keyword
                script_quality = repair_result["script_quality"]
                narration_repaired = False
                plan.setdefault("meta", {})
                plan["meta"]["script_quality"] = script_quality
                plan["meta"]["script_quality_repair"] = quality_repair
                plan["meta"]["render_allowed"] = bool(script_quality.get("ok"))
                with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
                    json.dump(plan, f, ensure_ascii=False, indent=2)
                with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                    json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)
                log_fn(
                    "[QualityGate] AI repaired script-quality findings: "
                    f"{quality_repair['status']}",
                    24,
                )
            elif quality_repair["status"] != "not_needed":
                log_fn(
                    "[QualityGate] AI repair incomplete: "
                    f"{quality_repair['status']}",
                    24,
                )
        for warning in script_quality.get("warnings") or []:
            if warning.startswith(
                (
                    "opening_repeats_title",
                    "repeated_narration_scenes",
                    "numeric_claims_not_in_source",
                    "numeric_source_conflicts",
                    "age_claims_not_in_source",
                    "age_source_conflicts",
                    "year_claims_not_in_source",
                    "year_source_conflicts",
                    "date_claims_not_in_source",
                    "date_source_conflicts",
                    "ending_is_brief_statement",
                    "ending_scene_missing",
                )
            ):
                log_fn(f"[QualityGate] Senaryo uyarısı: {warning}", 24)

        allow_draft_render = bool(getattr(req, "allow_draft_render", False))
        if not quality_report_allows_render_fn(
            script_quality,
            allow_draft_render=allow_draft_render,
        ):
            if not narration_repaired:
                from scenes.narration_validate import apply_auto_repair_if_needed

                repaired_plan, narr_fixes, _ = apply_auto_repair_if_needed(plan)
                narration_repaired = True
                if narr_fixes:
                    log_fn(
                        f"[QualityGate] Anlatım sözleşme ihlali için otomatik onarıldı: {len(narr_fixes)} fix",
                        24,
                    )
                    plan = repaired_plan
                    repaired_for_director = repaired_plan
                    script_quality = validate_script_quality(plan)
                    plan["meta"]["script_quality"] = script_quality

            if not quality_report_allows_render_fn(
                script_quality,
                allow_draft_render=allow_draft_render,
            ):
                issues_list = script_quality.get("issues", [])
                reason = ", ".join(issues_list)
                msg = f"Senaryo üretim sözleşmesi uyarısı: {reason}"
                if getattr(config, "STRICT_SCRIPT_QUALITY_GATE", False):
                    log_fn(f"[QualityGate] HARD-FAIL: {msg}", 24)
                    if db_id:
                        database.update_video_status(db_id, "failed", error_message=msg)
                    state.broadcast_event("error", msg)
                    return False, plan, director, keyword, final_variation_attempt, pre_result
                else:
                    log_fn(f"[QualityGate] UYARI: {msg} (Render devam ediyor)", 24)
    except Exception as script_quality_err:
        if isinstance(plan, dict):
            plan.setdefault("meta", {}).setdefault(
                "script_quality",
                {"ok": True, "issues": [], "warnings": [], "error": str(script_quality_err)},
            )
        msg = f"Senaryo kalite sözleşmesi istisnası: {script_quality_err}"
        log_fn(f"[QualityGate] UYARI: {msg} (Render devam ediyor)", 24)

    if director:
        from scenes.narration_validate import apply_auto_repair_if_needed

        prior_meta = dict((plan or {}).get("meta") or {}) if isinstance(plan, dict) else {}
        if not narration_repaired:
            cand_plan, narr_fixes, _ = apply_auto_repair_if_needed(director.to_legacy_plan())
            narration_repaired = True
            if narr_fixes:
                log_fn(f"[QualityGate] Anlatim otomatik duzeltildi: {len(narr_fixes)} fix", 24)
                repaired_for_director = cand_plan
        if repaired_for_director is not None:
            director = compile_director_plan(
                repaired_for_director,
                title=keyword,
                niche_id=locked_niche,
                language=target_lang,
                reddit_post=getattr(req, "reddit_post", None),
            )
            plan = director.to_legacy_plan()
            if prior_meta:
                plan.setdefault("meta", {}).update(prior_meta)
            with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
                json.dump(plan, f, ensure_ascii=False, indent=2)
            with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)

        pre_result = pre_render_score(director)
        log_fn(
            f"[QualityGate] Pre-score={pre_result['score']} ok={pre_result['ok']} issues={pre_result.get('issues')}",
            25,
        )
        for warning in pre_result.get("warnings") or []:
            log_fn(f"[RetentionGate] Görsel ritim uyarısı: {warning}", 25)
        semantic_block = [
            i
            for i in pre_result.get("issues", [])
            if i.startswith("fragment")
            or i.startswith("low_words")
            or i.startswith("empty_narration")
            or i.startswith("no_terminal")
        ]
        if semantic_block and not narration_repaired:
            plan_dict = director.to_legacy_plan()
            repaired_plan, narr_fixes2, _ = apply_auto_repair_if_needed(plan_dict)
            narration_repaired = True
            if narr_fixes2:
                log_fn(
                    f"[QualityGate] Pre-gate ikinci onarım: {len(narr_fixes2)} fix",
                    25,
                )
                director = compile_director_plan(
                    repaired_plan,
                    title=keyword,
                    niche_id=locked_niche,
                    language=target_lang,
                    reddit_post=getattr(req, "reddit_post", None),
                )
                plan = director.to_legacy_plan()
                if prior_meta:
                    plan.setdefault("meta", {}).update(prior_meta)
                pre_result = pre_render_score(director)
                semantic_block = [
                    i
                    for i in pre_result.get("issues", [])
                    if i.startswith("fragment")
                    or i.startswith("low_words")
                    or i.startswith("empty_narration")
                    or i.startswith("no_terminal")
                ]
        if semantic_block:
            msg = f"Pre-render narration gate blocked: {', '.join(semantic_block)}"
            log_fn(f"[QualityGate] {msg}", 25)
            if db_id:
                database.update_video_status(db_id, "failed", error_message=msg)
            state.broadcast_event("error", msg)
            return False, plan, director, keyword, final_variation_attempt, pre_result
        bad = scenes_needing_regen(director, pre_result)
        if bad:
            target_scenes = [
                director.scenes[idx] for idx in bad if 0 <= idx < len(director.scenes)
            ]
            if target_scenes:
                apply_visual_intents(target_scenes, director.niche_id, title=director.title)
                build_audio_events(director)
                plan = director.to_legacy_plan()
                if prior_meta:
                    plan.setdefault("meta", {}).update(prior_meta)
                log_fn(f"[Visual] {len(target_scenes)} sahne intent yenilendi (must_exclude temizliği)")

    if db_id and isinstance(plan, dict) and plan.get("scenes"):
        database.save_scenes(db_id, plan["scenes"])

    try:
        from compliance import evaluate_plan_compliance, publication_decision
        from compliance.viewer_score import compute_viewer_score
        from research_service import build_topic_research_brief

        plan["keyword"] = keyword
        plan["niche_id"] = locked_niche
        plan["research_brief"] = plan.get("research_brief") or build_topic_research_brief(
            keyword, niche_id=locked_niche, lang=target_lang
        )
        compliance_result = evaluate_plan_compliance(plan)
        viewer_result = compute_viewer_score(plan, compliance=compliance_result)
        plan.setdefault("meta", {})
        plan["meta"]["compliance"] = compliance_result
        plan["meta"]["viewer_score"] = viewer_result
        plan["meta"]["publication"] = publication_decision(plan, compliance_result, viewer_result)
        with open(os.path.join(proj, "compliance.json"), "w", encoding="utf-8") as fh:
            json.dump(
                {"compliance": compliance_result, "viewer_score": viewer_result},
                fh,
                ensure_ascii=False,
                indent=2,
            )
        log_fn(
            f"[Compliance] risk={(compliance_result.get('inauthentic') or {}).get('risk')} "
            f"viewer={viewer_result.get('score')} action="
            f"{(compliance_result.get('niche_gate') or {}).get('action')} "
            f"research={(compliance_result.get('research') or {}).get('action')} "
            f"render_blocking={compliance_result.get('render_blocking')} "
            f"reason={(compliance_result.get('diagnosis') or {}).get('primary')}",
            27,
        )
        render_blocking = bool(compliance_result.get("render_blocking"))
        if render_blocking:
            reason = ", ".join(compliance_result.get("hard_fail_reasons") or [])
            if not reason:
                reason = "render_blocking_without_reason"
            msg = f"Para kazanma kalite kapısı uyarısı: {reason}"
            if getattr(config, "STRICT_COMPLIANCE_GATE", False):
                log_fn(f"[Compliance] HARD-FAIL: {msg}", 28)
                if db_id:
                    database.update_video_status(db_id, "failed", error_message=msg)
                state.broadcast_event("error", msg)
                return False, plan, director, keyword, final_variation_attempt, pre_result
            else:
                log_fn(f"[Compliance] UYARI: {msg} (Render devam ediyor)", 28)
        if compliance_result.get("hard_fail"):
            reason = ", ".join(compliance_result.get("hard_fail_reasons") or [])
            log_fn(
                f"[Compliance] RENDER_ALLOWED_REVIEW: {reason or 'publication review required'}",
                27,
            )
    except Exception as compliance_err:
        if isinstance(plan, dict):
            plan.setdefault("meta", {}).setdefault(
                "compliance",
                {"render_blocking": False, "hard_fail": False, "error": str(compliance_err)},
            )
        msg = f"Uyumluluk kalite kapısı istisnası: {compliance_err}"
        log_fn(f"[Compliance] UYARI: {msg} (Render devam ediyor)", 28)

    return True, plan, director, keyword, final_variation_attempt, pre_result
