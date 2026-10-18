"""
Video render worker — DirectorPlan orchestration spine.
Phases: Director → Timeline → Visual → Voice → AudioMaster → FFmpegGraph → QualityGate
Stage implementations are modularized into:
  - server_core.worker_preflight_stage
  - server_core.worker_script_stage
  - server_core.worker_visual_stage
  - server_core.worker_audio_stage
  - server_core.worker_post_stage
  - server_core.worker_packaging_stage
"""
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Callable, Mapping

import imageio_ffmpeg

import config
import database
from api_models import VideoRenderRequest
from batch_processor import batch_manager
from niche_templates import get_niche_production_profile
from notifications import notify_render_error, notify_video_ready
from reddit_card_renderer import generate_reddit_post_card_clip
from scene_generator import generate_scenes
from services.workflow_retry import GLOBAL_RENDER_RETRY
from subtitle_generator import (
    SUBTITLE_PRESETS,
    merge_studio_subtitle_opts,
    resolve_ab_subtitle_preset,
)
from tts_engine import generate_narration_with_timing
from video_fetcher import (
    commit_published_stock_ids,
    discard_job_stock_ids,
    fetch_scene_clip,
    fetch_selected_stock_video,
    generate_ai_image_clip,
    generate_veo_scene_clip,
    reset_session_source_counts,
    reset_used_videos,
    search_and_download,
)
from visuals.fetch import attach_short_clip_partners
from . import state
from .worker_audio_stage import run_tts_and_audio_master_stage
from .worker_packaging_stage import run_post_render_and_packaging_stage
from .worker_post_stage import (
    _apply_optional_sonilo_sfx,
    _compose_with_retry,
    process_batch_queue,
    run_ffmpeg_compose_and_post_stage,
)
from .worker_preflight_stage import (
    _SCRIPT_SLOP,
    _ensure_ui_plan_narration_usable,
    _fetch_scenes_parallel,
    _fetch_single_scene_visual,
    _gemini_image_circuit_open,
    _get_render_thread_limits,
    _log,
    _quality_report_allows_render,
    _stamp_visual_mode,
    _sweep_render_temp_files,
    _veo_circuit_open,
    _veo_render_allowed,
    procedural_on_retry_pass,
    run_preflight_and_init_stage,
)
from .worker_script_stage import run_script_and_director_stage
from .worker_visual_stage import verify_and_audit_visual_stage


def process_video_task(req: VideoRenderRequest, *, reset_cancel_request: bool = True):
    """
    Isolated render worker spine orchestrating preflight (auto_delete / purge_old_videos),
    DirectorPlan (enrich_plan_scenes), visual ingestion, TTS/AudioMaster
    (scan_audio_copyright_risk), single-pass FFmpegGraph composition (Madde 418),
    and post-render quality gate.
    """
    old_stdout = sys.stdout
    while isinstance(old_stdout, state.SSELogStreamer):
        next_out = getattr(old_stdout, "terminal", None) or getattr(
            old_stdout, "original_stdout", None
        )
        if next_out is None or next_out is old_stdout:
            break
        old_stdout = next_out
    sys.stdout = state.SSELogStreamer(old_stdout)
    db_id = None
    render_job_prefix = ""
    _orig_config = {
        "LANGUAGE": getattr(config, "LANGUAGE", "tr"),
        "TTS_VOICE": getattr(config, "TTS_VOICE", None),
        "TTS_RATE": getattr(config, "TTS_RATE", "+0%"),
        "TTS_SACRED_CALM": bool(getattr(config, "TTS_SACRED_CALM", False)),
        "RENDER_RESOLUTION_MODE": getattr(config, "RENDER_RESOLUTION_MODE", "1080p"),
    }
    gate_context = None
    gate_entered = False
    sm = None
    keyword = getattr(req, "keyword", None) or "Video"
    task_id = getattr(req, "task_id", None) or f"task_{int(time.time()*1000)}"
    gameplay_path = None
    render_outcome = "failed"

    def check_cancelled():
        if state.current_render_state.get("cancel_requested", False) or state.is_task_cancelled(task_id):
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    try:
        from render.render_limits import GLOBAL_RENDER_GATE
        from services.structured_logger import get_structured_logger

        slogger = get_structured_logger(
            "render_worker", task_id=task_id, niche=req.niche, topic=req.keyword
        )
        slogger.info(
            "Render kuyruğuna alındı",
            extra={
                "queued_renders": GLOBAL_RENDER_GATE.queued_count,
                "active_renders": GLOBAL_RENDER_GATE.active_count,
            },
        )
        gate_context = GLOBAL_RENDER_GATE.acquire_slot_sync(
            task_id=task_id, timeout=180.0
        )
        gate_context.__enter__()
        gate_entered = True
        slogger.info(
            "Render donanım slotu tahsis edildi",
            extra={"active_renders": GLOBAL_RENDER_GATE.active_count},
        )

        if reset_cancel_request:
            state.current_render_state["cancel_requested"] = False
        state.current_render_state["cancel_notified"] = False
        state.current_render_state["is_rendering"] = True
        state.current_render_state["error"] = None
        state.current_render_state["video_url"] = None
        state.current_render_state["percent"] = 0
        state.current_render_state["step"] = "Başlatılıyor"
        state.register_task_state(
            task_id,
            {
                "is_rendering": True,
                "cancel_requested": False
                if reset_cancel_request
                else bool(state.current_render_state.get("cancel_requested", False)),
                "keyword": keyword,
                "percent": 0,
                "step": "Başlatılıyor",
            },
        )
        check_cancelled()

        (
            render_threads,
            ffmpeg_threads,
            target_lang,
            plan,
            vm,
            keyword,
            locked_niche,
            ch_paths,
            db_id,
            sm,
            safe,
            render_job_prefix,
            output_root,
            proj,
            PipelineStage,
        ) = run_preflight_and_init_stage(req, check_cancelled)

        # ─── 1–2) Script + DirectorPlan + Compliance Gates ─────────────────
        ok_script, plan, director, keyword, final_variation_attempt, pre_result = (
            run_script_and_director_stage(
                req=req,
                plan=plan,
                keyword=keyword,
                locked_niche=locked_niche,
                target_lang=target_lang,
                vm=vm,
                proj=proj,
                ch_paths=ch_paths,
                db_id=db_id,
                sm=sm,
                check_cancelled=check_cancelled,
                log_fn=_log,
                stamp_visual_mode_fn=_stamp_visual_mode,
                ensure_ui_plan_fn=_ensure_ui_plan_narration_usable,
                quality_report_allows_render_fn=_quality_report_allows_render,
            )
        )
        if not ok_script or not plan:
            return render_outcome

        # ─── 3) Acquire visuals ───────────────────────────────────────────
        check_cancelled()
        scenes = plan.get("scenes", [])
        total_s = len(scenes)
        sm.transition_to(
            PipelineStage.STAGE_5_ASSET_INGESTION,
            f"Varlık Edinimi: {total_s} sahne için görsel klipler temin ediliyor",
            pct=32.0,
        )
        _log(f"[Visual] Stok videolar aranıyor ({total_s} sahne, semantik skor)...", 30)

        clips = []
        gameplay_path = None
        recent_texts = []
        niche_profile = (plan or {}).get("niche_profile") or {}
        if not niche_profile and locked_niche:
            try:
                niche_profile = get_niche_production_profile(locked_niche) or {}
                plan["niche_profile"] = niche_profile
            except Exception:
                niche_profile = {}
        production_rules = (
            (niche_profile.get("production_rules") or {})
            if isinstance(niche_profile, dict)
            else {}
        )
        gp_cat = (getattr(req, "gameplay_category", None) or "auto").strip().lower()
        if gp_cat not in ("", "auto"):
            req.split_screen = True
        hybrid_split = bool(plan.get("hybrid_niche")) and bool(
            plan.get("hybrid_split_screen")
        )
        needs_split_screen = (
            getattr(req, "split_screen", False)
            or getattr(req, "dopamin_split_screen", False)
            or hybrid_split
            or bool(production_rules.get("split_screen"))
        )
        if needs_split_screen:
            req.split_screen = True
        resume_visuals = sm.reusable(PipelineStage.STAGE_5_ASSET_INGESTION)
        saved_visuals = (
            sm.stage_artifacts(PipelineStage.STAGE_5_ASSET_INGESTION)
            if resume_visuals
            else {}
        )
        if resume_visuals and len(saved_visuals.get("clips") or []) != total_s:
            resume_visuals = False
        if resume_visuals and req.split_screen:
            saved_gameplay = saved_visuals.get("gameplay_path") or ""
            if not saved_gameplay or not os.path.isfile(saved_gameplay):
                resume_visuals = False
        if req.split_screen and not resume_visuals:
            from gameplay_pool import fetch_gameplay_clip, resolve_gameplay_category

            gp_cat = getattr(req, "gameplay_category", None) or "auto"
            resolved_cat = resolve_gameplay_category(gp_cat, locked_niche)
            state.broadcast_event(
                "log",
                f"Split-screen gameplay havuzu: kategori={resolved_cat}…",
            )
            gameplay_path = fetch_gameplay_clip(
                proj,
                category=gp_cat,
                niche=locked_niche,
                target_duration=12,
                cancel_check=lambda: state.current_render_state.get(
                    "cancel_requested", False
                )
                or state.is_task_cancelled(task_id),
            )
            if not gameplay_path:
                state.broadcast_event(
                    "log", "Gameplay havuzu boş — stok aramasına düşülüyor…"
                )
                gameplay_path = search_and_download(
                    [
                        "mobile game gameplay",
                        "parkour game screen recording",
                        "arcade gameplay",
                    ],
                    10_000,
                    proj,
                    target_duration=12,
                    preferred_source="pexels",
                    cancel_check=lambda: state.current_render_state.get(
                        "cancel_requested", False
                    )
                    or state.is_task_cancelled(task_id),
                    allow_custom=False,
                )
            if not gameplay_path:
                raise RuntimeError(
                    "Split-screen için daha önce kullanılmamış oyun/parkur klibi bulunamadı."
                )

        check_cancelled()
        if resume_visuals:
            gameplay_path = saved_visuals.get("gameplay_path") or None
            clips = []
            for i, item in enumerate(saved_visuals.get("clips") or []):
                entry = {
                    "path": item.get("path"),
                    "duration": item.get("duration")
                    or (scenes[i].get("duration") if i < len(scenes) else 5),
                }
                if item.get("tail_path"):
                    entry["tail_path"] = item["tail_path"]
                    entry["head_duration"] = item.get("head_duration")
                clips.append(entry)
                if director and i < len(director.scenes):
                    director.scenes[i].path = entry.get("path")
            _log("[Resume] Görseller duruyor. Stok indirme atlandı.", 32)
        else:
            _log(
                f"[Visual] Paralel stok fetch başlıyor ({total_s} sahne, asyncio.gather)...",
                32,
            )
            _channel_id = getattr(req, "channel_id", None)
            fetch_results = asyncio.run(
                _fetch_scenes_parallel(
                    scenes,
                    plan,
                    proj,
                    total_s,
                    gameplay_path=gameplay_path,
                    channel_id=_channel_id,
                )
            )
            check_cancelled()
            clips = [None] * total_s
            for i, clip_entry, p in sorted(fetch_results, key=lambda row: row[0]):
                clips[i] = clip_entry
                if director and i < len(director.scenes):
                    director.scenes[i].path = p
                if p:
                    recent_texts.append(os.path.basename(p).lower())
                scene = scenes[i]
                intent = scene.get("visual_intent") or {}
                desc = scene.get("scene_description", "")
                progress_pct = 30 + int(((i + 1) / max(1, total_s)) * 28)
                step_msg = f"[Visual] Sahne {i + 1}/{total_s}: {(intent.get('subject') or desc)[:40]}..."
                state.broadcast_event(
                    "progress", {"percent": progress_pct, "step": step_msg}
                )
                state.broadcast_event(
                    "log",
                    f"  -> Sahne {i + 1}/{total_s}: {(desc or intent.get('subject', ''))[:50]}",
                )

        # Chapter 6: K1 visual retry uses allow_procedural=False; K2 uses procedural_on_retry_pass(attempt, max_passes)
        ok_visuals, clips, _pre_audit = verify_and_audit_visual_stage(
            req=req,
            plan=plan,
            director=director,
            scenes=scenes,
            clips=clips,
            recent_texts=recent_texts,
            gameplay_path=gameplay_path,
            resume_visuals=resume_visuals,
            proj=proj,
            output_root=output_root,
            safe=safe,
            render_job_prefix=render_job_prefix,
            keyword=keyword,
            locked_niche=locked_niche,
            target_lang=target_lang,
            ch_paths=ch_paths,
            db_id=db_id,
            sm=sm,
            check_cancelled=check_cancelled,
            log_fn=_log,
            fetch_scene_clip_fn=fetch_scene_clip,
            procedural_on_retry_pass_fn=procedural_on_retry_pass,
        )
        if not ok_visuals:
            return render_outcome

        # ─── 4–6) TTS + Audio Master + SEO + Subtitles ─────────────────────
        (
            ok_audio,
            plan,
            director,
            audio_path,
            timings,
            audio_dur,
            bgm_track,
            user_wants_muted,
            seo_meta,
            seo_file,
            script_text,
            sub_opts,
        ) = run_tts_and_audio_master_stage(
            req=req,
            plan=plan,
            director=director,
            clips=clips,
            proj=proj,
            output_root=output_root,
            safe=safe,
            keyword=keyword,
            locked_niche=locked_niche,
            target_lang=target_lang,
            final_variation_attempt=final_variation_attempt,
            db_id=db_id,
            sm=sm,
            check_cancelled=check_cancelled,
            log_fn=_log,
        )
        if not ok_audio:
            return render_outcome

        # ─── 7–8) Render + Post quality gate & packaging ───────────────────
        render_outcome = run_ffmpeg_compose_and_post_stage(
            req=req,
            plan=plan,
            director=director,
            clips=clips,
            audio_path=audio_path,
            timings=timings,
            audio_dur=audio_dur,
            bgm_track=bgm_track,
            user_wants_muted=user_wants_muted,
            seo_meta=seo_meta,
            seo_file=seo_file,
            script_text=script_text,
            sub_opts=sub_opts,
            gameplay_path=gameplay_path,
            pre_result=pre_result,
            pre_audit=_pre_audit,
            proj=proj,
            output_root=output_root,
            safe=safe,
            keyword=keyword,
            target_lang=target_lang,
            ch_paths=ch_paths,
            db_id=db_id,
            sm=sm,
            render_threads=render_threads,
            ffmpeg_threads=ffmpeg_threads,
            check_cancelled=check_cancelled,
            PipelineStage=PipelineStage,
        )

    except (InterruptedError, asyncio.CancelledError):
        if sm is not None:
            sm.fail("Kullanıcı tarafından iptal edildi.", broadcast=False)
            sm.save_telemetry(locals().get("proj") or "")
        discard_job_stock_ids()
        cancel_msg = "⛔ Video üretimi kullanıcı tarafından iptal edildi."
        print(cancel_msg)
        state.broadcast_event("progress", {"percent": 0, "step": "İşlem İptal Edildi"})
        state.broadcast_event("error", cancel_msg)
        if db_id:
            database.update_video_status(
                db_id, "cancelled", error_message="Kullanıcı tarafından iptal edildi."
            )
        render_outcome = "cancelled"
    except Exception as e:
        if sm is not None:
            sm.fail(str(e), broadcast=False)
            sm.save_telemetry(locals().get("proj") or "")
        discard_job_stock_ids()
        if db_id:
            database.update_video_status(db_id, "failed", error_message=str(e))
        state.broadcast_event("error", f"İşlem hatası: {str(e)}")
        import traceback

        tb = traceback.format_exc()
        traceback.print_exc()
        notify_render_error(keyword, str(e), log_snippet=tb[-600:])
        render_outcome = "failed"
    finally:
        if gate_entered and gate_context is not None:
            try:
                gate_context.__exit__(None, None, None)
            except Exception:
                pass
        try:
            _sweep_render_temp_files(render_job_prefix)
        except Exception:
            pass
        state.clear_task_state(task_id)
        state.current_render_state["cancel_requested"] = False
        state.current_render_state["cancel_notified"] = False
        state.current_render_state["is_rendering"] = False
        state.is_rendering_active = False
        config.LANGUAGE = _orig_config["LANGUAGE"]
        config.TTS_VOICE = _orig_config["TTS_VOICE"]
        config.TTS_RATE = _orig_config["TTS_RATE"]
        config.TTS_SACRED_CALM = _orig_config["TTS_SACRED_CALM"]
        config.RENDER_RESOLUTION_MODE = _orig_config["RENDER_RESOLUTION_MODE"]
        sys.stdout = old_stdout
    return render_outcome
