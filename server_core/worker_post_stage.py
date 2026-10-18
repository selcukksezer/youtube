"""FFmpeg composition retry, post-render SFX, packaging orchestration, and batch queue worker."""
from __future__ import annotations

import glob
import os
import shutil
import sys
from typing import Any, Callable

import config
from api_models import VideoRenderRequest
from batch_processor import batch_manager
from services.workflow_retry import GLOBAL_RENDER_RETRY
from . import state
from .worker_packaging_stage import run_post_render_and_packaging_stage


def _rw_attr(name: str, default: Any) -> Any:
    mod = sys.modules.get("server_core.render_worker")
    return getattr(mod, name, default) if mod is not None else default


def _apply_optional_sonilo_sfx(video_path: str, enabled: bool) -> bool:
    if not enabled:
        return False
    from services.sonilo_sfx import SoniloSfxError, add_ai_sfx_to_video

    log_fn = _rw_attr("_log", print)
    log_fn("[Sonilo SFX] Görüntü analiziyle AI ses efekti üretiliyor; render dosyası yükleniyor.")
    backup_path = video_path + ".pre_sonilo.bak"
    try:
        if os.path.isfile(video_path):
            shutil.copy2(video_path, backup_path)
        add_ai_sfx_to_video(video_path)
        if not os.path.isfile(video_path) or os.path.getsize(video_path) < 100_000:
            raise SoniloSfxError("Sonilo SFX çıktısı eksik veya 100 KB altında")
    except (SoniloSfxError, Exception) as exc:
        if os.path.isfile(backup_path):
            try:
                shutil.copy2(backup_path, video_path)
            except OSError:
                pass
        log_fn(f"[Sonilo SFX] Uygulanamadı; mevcut render korundu: {exc}", 95)
        return False
    finally:
        if os.path.isfile(backup_path):
            try:
                os.remove(backup_path)
            except OSError:
                pass
    log_fn("[Sonilo SFX] AI ses efekti render'a eklendi.", 95)
    return True


def _compose_with_retry(
    compose_fn: Callable[..., str],
    clips: Any,
    audio_path: str,
    word_timings: Any,
    output_path: str,
    **compose_kwargs: Any,
) -> str:
    cfg = _rw_attr("config", config)
    retry_mgr = _rw_attr("GLOBAL_RENDER_RETRY", GLOBAL_RENDER_RETRY)
    log_fn = _rw_attr("_log", print)
    progress_callback = compose_kwargs.get("progress_callback")
    last_progress = float("-inf")

    def render_attempt(attempt_path: str, use_gpu: bool) -> bool:
        attempt_kwargs = dict(compose_kwargs)
        if callable(progress_callback):

            def report_progress(pct: float, *args: Any, **kwargs: Any) -> None:
                nonlocal last_progress
                last_progress = max(last_progress, float(pct))
                progress_callback(last_progress, *args, **kwargs)

            attempt_kwargs["progress_callback"] = report_progress

        rendered_path = compose_fn(
            clips,
            audio_path,
            word_timings,
            attempt_path,
            use_gpu_override=use_gpu,
            **attempt_kwargs,
        )
        return bool(
            rendered_path
            and os.path.normcase(os.path.abspath(rendered_path))
            == os.path.normcase(os.path.abspath(attempt_path))
        )

    retry = retry_mgr.execute_render_with_retry(
        render_fn=render_attempt,
        output_path=output_path,
        max_attempts=2,
        initial_backoff=0.5,
        initial_use_gpu=bool(getattr(cfg, "USE_GPU_ACCELERATION", True)),
    )
    if retry["attempts_used"] > 1:
        log_fn(
            "[RenderRetry] İlk deneme başarısız; izole çıktı ve "
            f"{'donanım' if retry['used_gpu'] else 'CPU'} kodlayıcıyla tamamlandı."
        )
    return output_path


def run_ffmpeg_compose_and_post_stage(
    *,
    req,
    plan,
    director,
    clips,
    audio_path,
    timings,
    audio_dur,
    bgm_track,
    user_wants_muted,
    seo_meta,
    seo_file,
    script_text,
    sub_opts,
    gameplay_path,
    pre_result,
    pre_audit,
    proj,
    output_root,
    safe,
    keyword,
    target_lang,
    ch_paths,
    db_id,
    sm,
    render_threads,
    ffmpeg_threads,
    check_cancelled,
    PipelineStage,
) -> str:
    """Execute Stage 7 (FFmpeg filtergraph render) and Stage 8 (Post quality gate & packaging)."""
    cfg = _rw_attr("config", config)
    st = _rw_attr("state", state)
    log_fn = _rw_attr("_log", print)
    compose_retry_fn = _rw_attr("_compose_with_retry", _compose_with_retry)
    sonilo_fn = _rw_attr("_apply_optional_sonilo_sfx", _apply_optional_sonilo_sfx)
    post_pkg_fn = _rw_attr(
        "run_post_render_and_packaging_stage", run_post_render_and_packaging_stage
    )

    def on_compose_progress(pct, step_text="", *args, **kwargs):
        msg = step_text or kwargs.get("message") or kwargs.get("step") or ""
        sm.update_progress(pct, str(msg))

    check_cancelled()
    sm.transition_to(
        PipelineStage.STAGE_9_FFMPEG_RENDER,
        "FFmpeg FilterComplex Render: Tek geçişte birleştirme ve donanım hızlandırma",
        pct=83.0,
    )
    log_fn("[FFmpegGraph] Montaj başlıyor (Madde 418)...", 78)
    output_file = os.path.join(output_root, f"{safe}.mp4")

    is_split = bool(
        getattr(req, "split_screen", False)
        or plan.get("hybrid_split_screen")
        or (director and getattr(director, "niche_id", None) == "11_reddit_stories")
        or req.niche == "11_reddit_stories"
    )
    gameplay_cat = getattr(req, "gameplay_category", "auto") or "auto"
    if is_split and (not gameplay_path or not os.path.isfile(str(gameplay_path))):
        try:
            from services.gameplay_background_manager import GLOBAL_BACKGROUND_MANAGER

            total_duration = max(
                10.0,
                float(audio_dur or 0.0)
                or sum(float(c.get("duration", 3.0)) for c in clips),
            )
            gameplay_path = GLOBAL_BACKGROUND_MANAGER.get_gameplay_clip(
                project_dir=proj,
                category=gameplay_cat,
                niche=director.niche_id if director else req.niche,
                target_duration=total_duration,
                cancel_check=lambda: st.current_render_state.get(
                    "cancel_requested", False
                ),
            )
            if gameplay_path:
                log_fn(
                    f"[SplitScreen] Oynanış videosu bağlandı: {os.path.basename(gameplay_path)} ({gameplay_cat})",
                    80,
                )
        except Exception as gp_err:
            log_fn(f"[SplitScreen] Oynanış paneli hazırlanamadı: {gp_err}", 80)
            gameplay_path = None

    reddit_card_path = None
    enable_rcard = bool(getattr(req, "enable_reddit_card", False))
    if not enable_rcard and (
        req.niche == "11_reddit_stories"
        or (director and getattr(director, "niche_id", None) == "11_reddit_stories")
        or getattr(req, "reddit_post", None)
    ):
        enable_rcard = True
    if enable_rcard:
        try:
            from reddit_card_renderer import (
                build_reddit_card_metadata,
                generate_transparent_reddit_card_png,
            )

            card_metadata = build_reddit_card_metadata(
                getattr(req, "reddit_post", None),
                fallback_title=keyword,
            )
            reddit_card_path = generate_transparent_reddit_card_png(
                **card_metadata,
                output_path=os.path.join(output_root, f"{safe}_reddit_card.png"),
            )
            log_fn("[RedditCard] Soru kartı PNG overlay oluşturuldu.", 80)
        except Exception as rcard_err:
            log_fn(f"[RedditCard] Soru kartı oluşturulamadı: {rcard_err}", 80)
            reddit_card_path = None

    from effects.hook_card import first_scene_hook

    hook_scenes = director.scenes if director else plan.get("scenes", [])
    if sub_opts is None:
        sub_opts = {}
    sub_opts["hook_card_text"] = first_scene_hook(
        hook_scenes, getattr(req, "hook_text", None)
    )
    sub_opts["disable_hook_card"] = not getattr(req, "enable_hook_card", True)

    emp_ass_path = None
    if getattr(req, "enable_emphasis_card", False):
        try:
            from subtitle_generator import create_emphasis_overlay_ass

            tw, th = getattr(
                cfg,
                "get_target_resolution",
                lambda: (cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT),
            )()
            emp_candidate_path = os.path.join(output_root, f"{safe}_emphasis.ass")
            emp_ass_path = create_emphasis_overlay_ass(
                timings, emp_candidate_path, target_w=tw, target_h=th
            )
        except Exception as emp_err:
            log_fn(f"[Emphasis] Vurgu katmanı oluşturulamadı: {emp_err}", 80)
            emp_ass_path = None

    human_craft = (plan or {}).get("human_craft") if isinstance(plan, dict) else None
    compose_kwargs = dict(
        title=keyword,
        bgm_track="" if (director or user_wants_muted) else (bgm_track or req.bgm_track),
        bgm_volume=req.bgm_volume,
        subtitle_opts=sub_opts,
        progress_callback=on_compose_progress,
        cancel_check=lambda: st.current_render_state.get("cancel_requested", False),
        split_screen=bool(is_split and gameplay_path),
        anti_duplicate=getattr(req, "anti_duplicate", True),
        watermark_path=getattr(req, "watermark_path", None),
        enable_ken_burns=getattr(req, "enable_ken_burns", True),
        enable_zoompan=bool(getattr(req, "enable_zoompan", False)),
        enable_broll=bool(getattr(req, "enable_broll_insert", False)),
        enable_broll_insert=bool(getattr(req, "enable_broll_insert", False)),
        enable_face_center=bool(getattr(req, "enable_face_center", False)),
        enable_emphasis_card=bool(
            getattr(req, "enable_emphasis_card", False) and emp_ass_path
        ),
        emphasis_ass_path=emp_ass_path,
        gameplay_path=gameplay_path,
        enable_reddit_card=bool(enable_rcard and reddit_card_path),
        reddit_card_path=reddit_card_path,
        niche_id=(director.niche_id if director else getattr(req, "niche", "")),
        retention_metadata=(plan or {}).get("retention_metadata")
        if isinstance(plan, dict)
        else None,
        hybrid_niche=(plan or {}).get("hybrid_niche", "")
        if isinstance(plan, dict)
        else "",
        hybrid_render_overlay=(plan or {}).get("hybrid_render_overlay")
        if isinstance(plan, dict)
        else None,
        enable_native_hybrid=True,
        human_craft=human_craft,
        enable_audio_visualizer=bool(getattr(req, "enable_audio_visualizer", False)),
        audio_visualizer_mode=getattr(req, "audio_visualizer_mode", "line") or "line",
        audio_visualizer_color=getattr(req, "audio_visualizer_color", "0x00D7FF")
        or "0x00D7FF",
        enable_news_ticker=bool(getattr(req, "enable_news_ticker", False)),
        news_ticker_text=getattr(req, "news_ticker_text", None),
    )

    from render.ffmpeg_graph import compose_via_director

    if director and getattr(director, "scenes", None):
        target_scene_count = len(director.scenes)
        while len(clips) < target_scene_count:
            clips.append({})
        for _idx, _sc in enumerate(director.scenes):
            if _idx < len(clips):
                c = clips[_idx]
                if not isinstance(c, dict):
                    c = {}
                    clips[_idx] = c
                c["duration"] = float(_sc.duration)
                c["t0"] = float(_sc.t0)
                c["t1"] = float(_sc.t1)
                if not c.get("path") or not os.path.exists(c["path"]):
                    if _sc.path and os.path.exists(_sc.path):
                        c["path"] = _sc.path
                    else:
                        _cands = sorted(
                            glob.glob(os.path.join(proj, f"s{_idx:03d}_*.mp4"))
                        )
                        if _cands and os.path.exists(_cands[0]):
                            c["path"] = _cands[0]
                            _sc.path = _cands[0]

    from services.scene_prerequisites import ScenePrerequisiteGate

    ScenePrerequisiteGate.check_render_prerequisites_or_raise(clips, audio_path)

    prev_sfx = getattr(cfg, "ENABLE_SFX", True)
    prev_bgm = getattr(cfg, "ENABLE_BGM", True)
    if director or user_wants_muted:
        cfg.ENABLE_SFX = False if director else prev_sfx
        cfg.ENABLE_BGM = False
    try:
        result = compose_retry_fn(
            compose_via_director,
            clips,
            audio_path,
            timings,
            output_file,
            audio_premastered=bool(director),
            render_threads=render_threads,
            ffmpeg_thread_limit=ffmpeg_threads,
            **compose_kwargs,
        )
    finally:
        cfg.ENABLE_SFX = prev_sfx
        cfg.ENABLE_BGM = prev_bgm

    if result and os.path.isfile(result):
        sonilo_fn(
            result,
            bool(getattr(req, "enable_sonilo_sfx", False)),
        )

    return post_pkg_fn(
        req=req,
        result=result,
        audio_path=audio_path,
        clips=clips,
        plan=plan,
        director=director,
        pre_result=pre_result,
        pre_audit=pre_audit,
        seo_meta=seo_meta,
        seo_file=seo_file,
        script_text=script_text,
        proj=proj,
        output_root=output_root,
        safe=safe,
        keyword=keyword,
        target_lang=target_lang,
        ch_paths=ch_paths,
        db_id=db_id,
        sm=sm,
        log_fn=log_fn,
    )


def process_batch_queue():
    bm = _rw_attr("batch_manager", batch_manager)
    st = _rw_attr("state", state)
    req_cls = _rw_attr("VideoRenderRequest", VideoRenderRequest)
    proc_fn = _rw_attr("process_video_task", None)

    while True:
        job = bm.take_next_job()
        if not job:
            return
        with st.render_lock:
            if st.is_rendering_active:
                bm.finish_current_job("queued")
                return
            st.is_rendering_active = True
        outcome = proc_fn(
            req_cls(
                keyword=job["topic"],
                niche=job["niche"],
                language=job["language"],
                split_screen=job.get("split_screen", False),
                anti_duplicate=True,
                enable_ken_burns=True,
            )
        )
        bm.finish_current_job(outcome or "completed")
