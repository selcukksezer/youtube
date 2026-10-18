"""
Render Worker Stage 5 Verification & Audit: Missing Clip Retries, Short-Clip Partner Attachment,
O1 Clip/Plan Sync, Pre-Render Audit, K1 Semantic Confidence Retries, Uniqueness Pass,
and Publishing Package / Source Ledger Generation.
Extracted from server_core/render_worker.py for modularity.
"""
import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import config
import database
from director.quality_gate import (
    clip_coverage_report,
    clip_uniqueness_report,
    format_duplicate_clips_error,
    format_missing_clips_error,
)
from visuals.fetch import attach_short_clip_partners
from . import state
from .pipeline_state_machine import PipelineStage


def verify_and_audit_visual_stage(
    *,
    req: Any,
    plan: Dict[str, Any],
    director: Any,
    scenes: List[Dict[str, Any]],
    clips: List[Dict[str, Any]],
    recent_texts: List[str],
    gameplay_path: Optional[str],
    resume_visuals: bool,
    proj: str,
    output_root: str,
    safe: str,
    render_job_prefix: str,
    keyword: str,
    locked_niche: str,
    target_lang: str,
    ch_paths: Dict[str, str],
    db_id: Optional[int],
    sm: Any,
    check_cancelled: Callable[[], None],
    log_fn: Callable[..., None],
    fetch_scene_clip_fn: Callable[..., Optional[str]],
    procedural_on_retry_pass_fn: Callable[[int, int], bool],
) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Completes visual asset verification, semantic K1 retries, deduplication, and credit ledger output.
    Returns (ok_to_continue, clips, pre_audit_dict).
    """
    total_s = len(scenes)
    pre_audit_result: Dict[str, Any] = {}
    _q_audit: Dict[str, Any] = {}

    def _retry_missing_clips(max_passes: int = 2):
        for attempt in range(1, max_passes + 1):
            report = clip_coverage_report(clips)
            missing = report["missing_indices"]
            if not missing:
                return
            log_fn(
                f"[Visual] Retry pass {attempt}/{max_passes}: "
                f"{len(missing)} missing scene(s) -> indices (0-based) {missing[:16]}"
                + (f" ... (+{len(missing) - 16})" if len(missing) > 16 else "")
                + ("; lavfi yedek açık" if procedural_on_retry_pass_fn(attempt, max_passes) else "; stok araması"),
                56,
            )
            for i in missing:
                check_cancelled()
                scene = scenes[i]
                intent = scene.get("visual_intent") or {}
                from visuals.subject_lock import queries_for_scene

                q = queries_for_scene(
                    narration=scene.get("narration") or "",
                    scene_description=scene.get("scene_description") or "",
                    subject=str(intent.get("subject") or ""),
                    existing=(
                        intent.get("search_queries") or scene.get("search_queries") or scene.get("search_query") or []
                    ),
                )
                if not q:
                    log_fn(f"[Visual] Retry pass {attempt}: scene {i + 1}/{total_s} has no filmable subject; left missing")
                    continue
                p = fetch_scene_clip_fn(
                    q, i, proj,
                    target_duration=clips[i]["duration"],
                    scene_description=scene.get("scene_description", ""),
                    narration=scene.get("narration", ""),
                    visual_intent=intent,
                    cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
                    recent_texts=recent_texts,
                    niche_id=((plan or {}).get("locked_niche") or (plan or {}).get("niche_id") or ""),
                    channel_id=getattr(req, "channel_id", None),
                    allow_procedural=procedural_on_retry_pass_fn(attempt, max_passes),
                )
                clips[i]["path"] = p
                if p:
                    recent_texts.append(os.path.basename(p).lower())
                    if director and i < len(director.scenes):
                        director.scenes[i].path = p
                else:
                    log_fn(f"[Visual] Retry pass {attempt}: scene {i + 1}/{total_s} still failed")

    if not resume_visuals:
        check_cancelled()
        _retry_missing_clips(max_passes=2)
        check_cancelled()
        attach_short_clip_partners(
            clips, scenes, proj,
            niche_id=((plan or {}).get("locked_niche") or (plan or {}).get("niche_id") or ""),
            channel_id=getattr(req, "channel_id", None),
            cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
        )
        visual_files = []
        visual_clips = []
        for clip in clips or []:
            if not isinstance(clip, dict):
                continue
            visual_clips.append(
                {
                    "path": clip.get("path"),
                    "duration": clip.get("duration"),
                    "tail_path": clip.get("tail_path") or "",
                    "head_duration": clip.get("head_duration"),
                }
            )
            if clip.get("path"):
                visual_files.append(clip["path"])
            if clip.get("tail_path"):
                visual_files.append(clip["tail_path"])
        if gameplay_path:
            visual_files.append(gameplay_path)
        sm.mark_done(
            PipelineStage.STAGE_5_ASSET_INGESTION,
            artifacts={"clips": visual_clips, "gameplay_path": gameplay_path or ""},
            files=visual_files,
        )

    _plan_scene_count = len(plan.get("scenes") or [])
    if _plan_scene_count > 0 and len(clips) != _plan_scene_count:
        if len(clips) > _plan_scene_count:
            log_fn(f"[O1-Sync] clips={len(clips)} > plan={_plan_scene_count} — trimming extras", 58)
            clips = clips[:_plan_scene_count]
        else:
            log_fn(f"[O1-Sync] clips={len(clips)} < plan={_plan_scene_count} — padding with None entries", 58)
            while len(clips) < _plan_scene_count:
                _pad_idx = len(clips)
                _pad_dur = float(
                    (
                        plan["scenes"][_pad_idx].get("duration")
                        if _pad_idx < len(plan.get("scenes") or []) and isinstance(plan["scenes"][_pad_idx], dict)
                        else None
                    )
                    or 5.0
                )
                clips.append({"path": None, "duration": _pad_dur})

    coverage = clip_coverage_report(clips)
    ok_clips = coverage["ok"]
    log_fn(f"[Visual] Stok klip indirme tamamlandi: {ok_clips}/{total_s}", 58)

    try:
        from routers.video_router import normalize_scene_paths_for_web

        if plan and "scenes" in plan:
            for idx, sc_item in enumerate(plan["scenes"]):
                if idx < len(clips) and clips[idx].get("path"):
                    sc_item["path"] = clips[idx]["path"]
        with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f_up:
            json.dump(plan, f_up, ensure_ascii=False, indent=2)
        norm_plan = normalize_scene_paths_for_web(dict(plan), render_job_prefix)
        state.broadcast_event(
            "plan_updated",
            {"slug": render_job_prefix, "title": keyword, "plan": norm_plan},
        )
    except Exception as _sync_err:
        log_fn(f"[TimelineSync] note: {_sync_err}")

    try:
        from render.pipeline_audit import audit_search_queries, pre_render_audit

        pre_audit_result = pre_render_audit(clips, audio_path=None, plan=plan)
        _q_audit = audit_search_queries(clips)
        for _e in pre_audit_result.get("errors") or []:
            log_fn(f"[PipelineAudit] ERROR: {_e}", 58)
        with open(os.path.join(proj, "pipeline_audit_pre.json"), "w", encoding="utf-8") as _af:
            json.dump(
                {"pre_render": pre_audit_result, "query_audit": _q_audit},
                _af, ensure_ascii=False, indent=2,
            )
        if not pre_audit_result["ok"]:
            _blocking = [
                e for e in (pre_audit_result.get("errors") or [])
                if "duplicate_clips" in e or "scene_count_too_low" in e
            ]
            if _blocking:
                _msg = f"Pre-render audit uyarısı: {'; '.join(_blocking)}"
                if getattr(config, "STRICT_AUDIT_GATE", False):
                    log_fn(f"[PipelineAudit] HARD-FAIL: {_msg}", 58)
                    if db_id:
                        database.update_video_status(db_id, "failed", error_message=_msg)
                    state.broadcast_event("error", _msg)
                    return False, clips, pre_audit_result
                else:
                    log_fn(f"[PipelineAudit] UYARI: {_msg} (Render devam ediyor)", 58)
    except Exception as _audit_err:
        log_fn(f"[PipelineAudit] audit skip: {_audit_err}")

    from render.pipeline_audit import (
        attach_candidate_metadata,
        require_semantic_confidence,
        retry_low_confidence_scenes,
    )

    def _candidate_manifest_rows():
        try:
            from visuals.fetch import get_job_manifest

            rows = get_job_manifest()
        except Exception:
            rows = []
        try:
            with open(os.path.join(proj, "source_manifest.json"), "r", encoding="utf-8") as _mf:
                saved_rows = json.load(_mf).get("clips", [])
        except Exception:
            saved_rows = []
        merged_rows = {
            row.get("scene_index"): row
            for row in saved_rows
            if isinstance(row, dict) and row.get("scene_index") is not None
        }
        merged_rows.update(
            {
                row.get("scene_index"): row
                for row in rows
                if isinstance(row, dict) and row.get("scene_index") is not None
            }
        )
        return list(merged_rows.values())

    for _si, _clip in enumerate(clips):
        if not isinstance(_clip, dict):
            continue
        _scene = scenes[_si] if _si < len(scenes) else {}
        if not _clip.get("narration"):
            _clip["narration"] = _scene.get("narration") or ""
        if not _clip.get("scene_description"):
            _clip["scene_description"] = _scene.get("scene_description") or ""
        if not _clip.get("search_queries"):
            _clip["search_queries"] = _scene.get("search_queries") or []
        if not _clip.get("visual_intent"):
            _clip["visual_intent"] = _scene.get("visual_intent") or {}
    attach_candidate_metadata(clips, _candidate_manifest_rows())

    def _retry_semantic_scene(_si, _clip):
        _narr = _clip.get("narration") or ""
        _desc = _clip.get("scene_description") or ""
        _scene = scenes[_si] if _si < len(scenes) else {}
        _intent = _clip.get("visual_intent") or _scene.get("visual_intent") or {}
        from visuals.query_builder import build_shot_queries
        from visuals.subject_lock import queries_for_scene

        _narr_queries = list(
            build_shot_queries(
                narration=_narr,
                scene_description=_desc,
                niche_id=(plan or {}).get("locked_niche") or (plan or {}).get("niche_id") or "",
                visual_intent=_intent,
                max_queries=3,
            )
        )
        for _fb_q in queries_for_scene(
            narration=_narr,
            scene_description=_desc,
            subject=str(_intent.get("subject") or ""),
            existing=_clip.get("search_queries") or [],
        ):
            if _fb_q and _fb_q not in _narr_queries:
                _narr_queries.append(_fb_q)
        if not _narr_queries:
            log_fn(f"[K1-Semantic] Scene {_si + 1}: no scene-specific stock queries; retry unavailable")
            return
        check_cancelled()
        try:
            _np = fetch_scene_clip_fn(
                _narr_queries, _si, proj,
                target_duration=_clip.get("duration", 6),
                scene_description=_desc,
                narration=_narr,
                cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
                niche_id=(plan or {}).get("locked_niche") or (plan or {}).get("niche_id") or "",
                channel_id=getattr(req, "channel_id", None),
                allow_procedural=False,
            )
        except Exception as _retry_err:
            log_fn(f"[K1-Semantic] Scene {_si + 1} retry failed: {_retry_err}")
            return
        if _np:
            log_fn(f"[K1-Semantic] Scene {_si + 1} re-fetched: {os.path.basename(_np)}")
            _clip["path"] = _np
            if director and _si < len(director.scenes):
                director.scenes[_si].path = _np
            attach_candidate_metadata(clips, _candidate_manifest_rows())
        else:
            log_fn(f"[K1-Semantic] Scene {_si + 1} retry returned no clip")

    _retried_scenes, _low_confidence_scenes = retry_low_confidence_scenes(
        clips, _retry_semantic_scene, threshold=0.08,
    )
    if _retried_scenes:
        log_fn(
            f"[K1-Semantic] Retried scenes {[index + 1 for index in _retried_scenes]}; "
            f"remaining low-confidence scenes {[index + 1 for index in _low_confidence_scenes]}"
        )
    if _low_confidence_scenes:
        try:
            require_semantic_confidence(_low_confidence_scenes)
        except Exception as _sem_err:
            log_fn(f"[K1-Semantic] UYARI: {_sem_err} (Render mevcut stok görsellerle devam ediyor)", 58)

    try:
        from render.pipeline_audit import (
            audit_search_queries,
            audit_visual_frames,
            pre_render_audit,
        )

        if _retried_scenes or not pre_audit_result:
            pre_audit_result = pre_render_audit(clips, audio_path=None, plan=plan)
            _q_audit = audit_search_queries(clips)
        elif not _q_audit:
            _q_audit = audit_search_queries(clips)
        _visual_audit_path = os.path.join(output_root, f"{safe}_visual_audit.jpg")
        _visual_frame_audit = audit_visual_frames(clips, _visual_audit_path)
        _visual_audit_slug = ch_paths["slug"]
        _visual_frame_audit["url"] = (
            f"/output/channels/{_visual_audit_slug}/{os.path.basename(_visual_audit_path)}"
            if _visual_audit_slug != "default"
            else f"/output/{os.path.basename(_visual_audit_path)}"
        )
        pre_audit_result["report"]["visual_frame_audit"] = _visual_frame_audit
        pre_audit_result["warnings"].extend(_visual_frame_audit.get("warnings") or [])
        for _w in pre_audit_result.get("warnings") or []:
            log_fn(f"[PipelineAudit] WARN: {_w}")
        if _q_audit.get("issue_count", 0) > 0:
            log_fn(
                f"[PipelineAudit] Search query issues: "
                f"{_q_audit['issue_count']} scenes have generic/empty/off-topic queries"
            )
        with open(os.path.join(proj, "pipeline_audit_pre.json"), "w", encoding="utf-8") as _af:
            json.dump(
                {"pre_render": pre_audit_result, "query_audit": _q_audit},
                _af, ensure_ascii=False, indent=2,
            )
    except Exception as _audit_err:
        log_fn(f"[PipelineAudit] final visual audit failed: {_audit_err}", 58)

    if ok_clips == 0:
        msg = "Stok video indirilemedi."
        state.broadcast_event("error", msg)
        if db_id:
            database.update_video_status(db_id, "failed", error_message=msg)
        return False, clips, pre_audit_result

    if not coverage["complete"]:
        msg = format_missing_clips_error(coverage)
        log_fn(f"[Visual] HARD-FAIL: {msg}", 58)
        if director:
            with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)
        if db_id:
            database.update_video_status(db_id, "failed", error_message=msg)
        state.broadcast_event("error", msg)
        return False, clips, pre_audit_result

    for _dup_pass in range(1, 3):
        uniqueness = clip_uniqueness_report(clips, min_unique=total_s)
        if uniqueness["ok"]:
            break
        dupes = sorted(
            set((uniqueness.get("duplicate_hash_indices") or []) + (uniqueness.get("duplicate_path_indices") or []))
        )
        if not dupes:
            break
        log_fn(
            f"[Visual] Tekrarlı klip pass {_dup_pass}/2: sahneler {[i + 1 for i in dupes]} yeniden aranıyor",
            58,
        )
        replaced = 0
        for i in dupes:
            check_cancelled()
            scene = scenes[i] if i < len(scenes) else {}
            intent = scene.get("visual_intent") or {}
            from visuals.subject_lock import queries_for_scene

            q = queries_for_scene(
                narration=scene.get("narration") or "",
                scene_description=scene.get("scene_description") or "",
                subject=str(intent.get("subject") or ""),
                existing=(
                    intent.get("search_queries") or scene.get("search_queries") or scene.get("search_query") or []
                ),
            )
            if not q:
                continue
            old = clips[i].get("path")
            p = fetch_scene_clip_fn(
                q, i, proj,
                target_duration=clips[i].get("duration", 6),
                scene_description=scene.get("scene_description", ""),
                narration=scene.get("narration", ""),
                visual_intent=intent,
                cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
                recent_texts=recent_texts,
                niche_id=((plan or {}).get("locked_niche") or (plan or {}).get("niche_id") or ""),
                channel_id=getattr(req, "channel_id", None),
                allow_procedural=procedural_on_retry_pass_fn(_dup_pass, 2),
            )
            if not p or p == old:
                continue
            clips[i]["path"] = p
            replaced += 1
            recent_texts.append(os.path.basename(p).lower())
            if director and i < len(director.scenes):
                director.scenes[i].path = p
            log_fn(f"[Visual] Sahne {i + 1} tekrarı değiştirildi: {os.path.basename(p)}", 58)
        if replaced == 0:
            break

    uniqueness = clip_uniqueness_report(clips, min_unique=total_s)
    if not uniqueness["ok"]:
        msg = format_duplicate_clips_error(uniqueness)
        if getattr(config, "STRICT_VISUAL_UNIQUENESS_GATE", False):
            log_fn(f"[Visual] HARD-FAIL: {msg}", 58)
            if director:
                with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                    json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)
            if db_id:
                database.update_video_status(db_id, "failed", error_message=msg)
            state.broadcast_event("error", msg)
            return False, clips, pre_audit_result
        else:
            log_fn(
                f"[Visual] UYARI: {msg} (Görsel filtreler uygulanarak render devam ediyor)",
                58,
            )

    try:
        from visuals.fetch import get_job_manifest, write_job_credits

        credits = write_job_credits(proj)
        manifest_count = len(get_job_manifest())
        disclosure = ((plan.get("meta") or {}).get("compliance") or {}).get("ai_disclosure") or {}
        artifact_payloads = {
            "research_brief.json": plan.get("research_brief") or {},
            "script.json": {
                "title": plan.get("title") or keyword,
                "language": target_lang,
                "niche_id": locked_niche,
                "full_narration": plan.get("full_narration") or "",
                "scenes": plan.get("scenes") or [],
                "narrative_structure": plan.get("narrative_structure") or [],
                "hook": plan.get("hook") or "",
                "payoff": plan.get("payoff") or "",
                "loop_line": plan.get("loop_line") or "",
            },
            "shot_plan.json": {
                "scenes": [
                    {
                        "scene_index": i,
                        "visual_intent": scene.get("visual_intent") or {},
                        "search_queries": scene.get("search_queries") or [],
                        "clip": next(
                            (row for row in get_job_manifest() if row.get("scene_index") == i),
                            None,
                        ),
                    }
                    for i, scene in enumerate(plan.get("scenes") or [])
                ]
            },
        }
        for filename, payload in artifact_payloads.items():
            with open(os.path.join(proj, filename), "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
        from compliance.publishing_package import (
            build_publishing_package,
            license_status_from_manifest,
            research_gate_passed,
        )

        manifest_rows = get_job_manifest()
        originality = (plan.get("meta") or {}).get("originality") or {}
        publishing = build_publishing_package(
            title=plan.get("title") or keyword,
            niche_id=locked_niche,
            viewer_score=(plan.get("meta") or {}).get("viewer_score"),
            manifest_items=manifest_rows,
            research_gate_passed=research_gate_passed(
                (plan.get("meta") or {}).get("compliance") or {}
            ),
            license_status=license_status_from_manifest(manifest_rows),
            originality_score=float(originality.get("originality_score") or 0.0)
            if isinstance(originality, dict)
            else 0.0,
            ai_disclosure=disclosure,
        )
        publishing["research_brief"] = plan.get("research_brief") or {}
        publishing["credits_files"] = credits
        publishing["policy_decision"] = (
            (plan.get("meta") or {}).get("compliance") or {}
        ).get("niche_gate") or {}
        publishing["research_decision"] = (
            (plan.get("meta") or {}).get("compliance") or {}
        ).get("research") or {}
        publishing["publication_decision"] = (plan.get("meta") or {}).get("publication") or {}
        publishing["language"] = target_lang
        publishing["description_appendix"] = "\n\n".join(
            part
            for part in [
                credits.get("description_block", "").strip(),
                disclosure.get("description_paragraph", "").strip(),
            ]
            if part
        )
        with open(os.path.join(proj, "publishing_package.json"), "w", encoding="utf-8") as fh:
            json.dump(publishing, fh, ensure_ascii=False, indent=2)
        log_fn(
            f"[Compliance] visual_credits hazır: {manifest_count} kaynak | "
            f"{os.path.basename(credits['json'])} | publishing_package hazır",
            59,
        )
    except Exception as credits_err:
        msg = f"Görsel kaynak kayıt dosyası uyarısı: {credits_err}"
        log_fn(f"[Compliance] UYARI: {msg} (Render devam ediyor)", 59)

    if director:
        with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
            json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)
        plan = director.to_legacy_plan()
        with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

    return True, clips, pre_audit_result
