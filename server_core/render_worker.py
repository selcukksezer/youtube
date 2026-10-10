"""
Video render worker — DirectorPlan orchestration spine.
Phases: Director → Timeline → Visual → Voice → AudioMaster → FFmpegGraph → QualityGate
"""
import os
import sys
import json
import time
import subprocess
import asyncio
import re
import imageio_ffmpeg
import config
import database
from api_models import VideoRenderRequest
from scene_generator import generate_scenes
from video_fetcher import (
    search_and_download,
    reset_used_videos,
    reset_session_source_counts,
    fetch_scene_clip,
    generate_ai_image_clip,
    generate_veo_scene_clip,
    commit_published_stock_ids,
    discard_job_stock_ids,
)
from reddit_card_renderer import generate_reddit_post_card_clip
from tts_engine import generate_narration_with_timing
from niche_templates import get_niche_production_profile
from subtitle_generator import SUBTITLE_PRESETS, merge_studio_subtitle_opts, resolve_ab_subtitle_preset
from batch_processor import batch_manager
from notifications import notify_video_ready, notify_render_error
from . import state


def _gemini_image_circuit_open() -> bool:
    """P1-17: true when Gemini image quota tripped — force stock-only regen."""
    try:
        from system_resilience import circuit_breaker
        return not circuit_breaker.can_execute("gemini_image")
    except Exception:
        return False


from visuals.fetch import attach_short_clip_partners


def procedural_on_retry_pass(attempt: int, max_passes: int) -> bool:
    """Stock-only on early passes. The last pass may synthesize lavfi.

    A missing scene has no licensed clip. Turning procedural on for every
    pass would freeze a mandelbrot in before a rate-limited API answers.
    Leaving it off for the last pass hard-fails the render, which is the
    hole this guards. K1 and the short-clip tail stay stock-only: those
    scenes already have a real file.
    """
    return int(attempt) >= int(max_passes)


def _log(msg, pct=None):
    # print only. SSELogStreamer already broadcasts stdout. A second
    # broadcast made every scene line appear twice in the live log.
    print(msg, flush=True)
    if pct is not None:
        state.broadcast_event("progress", {"percent": pct, "step": msg})


def _veo_circuit_open() -> bool:
    """P3-31: true when Veo quota tripped — skip AI video, fall back to stock."""
    try:
        from system_resilience import circuit_breaker
        return not circuit_breaker.can_execute("gemini_veo")
    except Exception:
        return False


_SCRIPT_SLOP = (
    "sonunu görmeden kaydırma",
    "gözlerime inanamadım",
    "toplumun bize dayattığı",
    "hakkında söylediği söz",
    "konusunda tamamen yanılıyor",
)


def _ensure_ui_plan_narration_usable(plan, keyword: str, locked_niche: str, target_lang: str):
    """Batch C — UI-supplied plan must pass narration gate or get procedural inject."""
    if not plan or not plan.get("scenes"):
        return plan
    try:
        from scenes.narration_validate import plan_quality_usable
        from scenes.fallback import _generate_procedural_fallback_scenes, _generate_five_fact_scenes

        blob = " ".join(
            str((s or {}).get("narration") or "")
            for s in (plan.get("scenes") or [])
            if isinstance(s, dict)
        ).casefold()
        slop = any(mark in blob for mark in _SCRIPT_SLOP)
        if slop and (locked_niche == "9_five_facts" or "gerçek" in (keyword or "").casefold() or "gercek" in (keyword or "").casefold()):
            _log("[Director] Senaryo şablon çöp — 5 gerçek anlatımıyla değiştiriliyor", 11)
            plan = dict(plan)
            plan.update(_generate_five_fact_scenes(keyword, target_lang != "en"))
            plan["niche_id"] = locked_niche or "9_five_facts"
            return plan

        if plan_quality_usable(plan.get("scenes") or []):
            return plan
        _log(
            "[Director] UI plan narration unusable — prosedürel fallback enjekte ediliyor",
            11,
        )
        fb = _generate_procedural_fallback_scenes(
            keyword,
            niche_type=locked_niche,
            language=target_lang,
        )
        plan = dict(plan)
        plan.update(fb)
    except Exception as exc:
        _log(f"[Director] UI plan narration gate atlandı: {exc}", 11)
    return plan


def _veo_render_allowed() -> bool:
    """P3-31: sparse Veo policy — paid quota confirm + preview model + circuit closed."""
    if not getattr(config, "USE_GEMINI_VIDEO_GEN", False):
        return False
    if not config.GEMINI_API_KEY:
        return False
    if not getattr(config, "GEMINI_VEO_PAID_QUOTA", False):
        return False
    if _veo_circuit_open():
        return False
    model = getattr(config, "GEMINI_VIDEO_MODEL", "") or ""
    if getattr(config, "GEMINI_VEO_PREVIEW_ONLY", True) and "preview" not in model.lower():
        return False
    return True


def _sweep_render_temp_files(job_prefix: str = "") -> None:
    """Remove this job's intermediate WAVs; FFmpeg graph owns its temp dirs."""
    if not job_prefix:
        return
    audio_dir = getattr(config, "AUDIO_DIR", "")
    if not audio_dir or not os.path.isdir(audio_dir):
        return
    suffixes = (
        "_eq.wav", "_146147.wav", "_breaths.wav", "_intro112.wav", "_room.wav",
        "_norm.wav", "_sonic.wav", "_jitter.wav", "_sfxbus.wav", "_bgm.wav", "_fitted.wav",
    )
    for suffix in suffixes:
        fp = os.path.join(audio_dir, f"{job_prefix}{suffix}")
        if os.path.isfile(fp):
            try:
                os.remove(fp)
            except OSError:
                pass


def _stamp_visual_mode(plan, selected) -> None:
    from visuals.mixed_visual import apply_selected_visual_mode, is_mixed_mode

    if plan and is_mixed_mode(selected):
        _log("[Visual] Karışık mod: sahneler sırayla stok ve Flux")
    apply_selected_visual_mode(plan, selected)


def _fetch_single_scene_visual(i, scene, plan, proj, total_s, gameplay_path=None, channel_id=None, req=None):
    """Sync fetch for one scene — used from parallel executor (P1-13)."""
    def _is_cancelled():
        return bool(state.current_render_state.get("cancel_requested", False))

    if _is_cancelled():
        return i, None, None

    q = scene.get("search_queries") or ([scene.get("search_query")] if scene.get("search_query") else [])
    d = scene.get("duration", 7)
    desc = scene.get("scene_description", "")
    intent = scene.get("visual_intent") or {}
    narr = scene.get("narration", "")
    if not q and isinstance(intent, dict):
        q = intent.get("search_queries") or []
    if not q and isinstance(intent, dict) and intent.get("subject"):
        q = [intent.get("subject")]
    if not q and desc:
        q = [desc]
    niche_id = (
        (plan or {}).get("locked_niche")
        or (plan or {}).get("niche_id")
        or scene.get("niche_id")
        or ""
    )
    p = None
    gemini_circuit_open = _gemini_image_circuit_open()
    # Licensed stock/archive footage is the default. AI is only selected when
    # a shot explicitly requests it or when semantic stock retrieval fails.
    source_policy = str(scene.get("visual_source_policy") or "licensed_first").casefold()
    prefer_ai = source_policy in {"ai", "synthetic", "ai_first"} or bool((plan or {}).get("prefer_ai_visuals"))

    visual_mode = str(
        scene.get("visual_mode")
        or (plan or {}).get("visual_mode")
        or (getattr(req, "visual_mode", "") if req else "")
        or (plan or {}).get("visual_style")
        or ""
    ).lower()
    from visuals.mixed_visual import is_mixed_mode, mixed_scene_mode
    if is_mixed_mode(visual_mode):
        visual_mode = mixed_scene_mode(i)
    if visual_mode == "stock":
        prefer_ai = False

    # 0) Direct assigned clip (AI preview, Whiteboard preview, or custom selected local clip)
    selected_vid = scene.get("selected_video") or {}
    local_candidate = selected_vid.get("path") or scene.get("video_path") or selected_vid.get("file_path")
    if local_candidate and os.path.exists(local_candidate):
        cand_name = os.path.basename(local_candidate).lower()
        if visual_mode in ("whiteboard", "sketch", "cizim") and "whiteboard" not in cand_name:
            p = None
        else:
            p = local_candidate
            _log(f"[Visual] Sahne #{i+1}: Önceden üretilen yerel klip kullanılıyor: {os.path.basename(p)}")

    if not p and visual_mode in ("whiteboard", "sketch", "cizim"):
        from services.whiteboard_animator import create_whiteboard_scene_clip
        _log(f"[Whiteboard] Sahne #{i+1}: El çizim line-art animasyonu üretiliyor...")
        wb_path = os.path.join(proj, f"s{i:03d}_whiteboard.mp4")
        p = create_whiteboard_scene_clip(
            scene_description=desc or narr or (q[0] if q else "whiteboard line art sketch"),
            output_video_path=wb_path,
            duration=d,
            scene_index=i,
            narration=narr,
        )

    if not p and (
        visual_mode in ("pollinations", "flux", "0tl_ai", "flux_ai", "pollinations_ai")
        or (prefer_ai and not config.GEMINI_API_KEY and not getattr(config, "FAL_API_KEY", "") and not getattr(config, "STABILITY_API_KEY", ""))
    ):
        from services.pollinations_ai_visual import create_scene_ai_clip
        _log(f"[Flux AI] Sahne #{i+1}: 0 TL Pollinations Flux SDXL 9:16 görsel üretiliyor...")
        ai_path = os.path.join(proj, f"s{i:03d}_flux.mp4")
        p = create_scene_ai_clip(
            scene_description=desc or (q[0] if q else narr) or "cinematic vertical 9:16 footage",
            output_video_path=ai_path,
            duration=d,
            scene_index=i,
        )

    if not p and i == 0 and plan.get("reddit_post"):
        p = generate_reddit_post_card_clip(
            plan["reddit_post"], os.path.join(proj, "s000_reddit_source.mp4"), duration=d
        )
    elif not p and prefer_ai and _veo_render_allowed() and i > 0:
        p = generate_veo_scene_clip(
            scene_description=desc or (q[0] if q else (narr[:120] or "subject detail")),
            output_path=os.path.join(proj, f"s{i:03d}_veo.mp4"),
            duration=d,
        )
    elif (
        not _veo_circuit_open()
        and getattr(config, "USE_GEMINI_VIDEO_GEN", False)
        and config.GEMINI_API_KEY
        and i > 0
        and not getattr(config, "GEMINI_VEO_PAID_QUOTA", False)
    ):
        _log("[Visual] Veo atlandi — GEMINI_VEO_PAID_QUOTA=false (ucretli kota onayi gerekli)")
    elif (
        prefer_ai
        and not gemini_circuit_open
        and getattr(config, "PREFER_GEMINI_SCENE_IMAGES", False)
        and getattr(config, "USE_GEMINI_IMAGE_GEN", False)
        and config.GEMINI_API_KEY
    ):
        p = generate_ai_image_clip(
            scene_description=desc or (q[0] if q else "cinematic"),
            output_path=os.path.join(proj, f"s{i:03d}_gemini.mp4"),
            duration=d,
        )
    elif (
        prefer_ai
        and not gemini_circuit_open
        and (
            getattr(config, "USE_GEMINI_IMAGE_GEN", False) and config.GEMINI_API_KEY
            or getattr(config, "FAL_API_KEY", "")
            or getattr(config, "STABILITY_API_KEY", "")
        )
    ):
        p = generate_ai_image_clip(
            scene_description=desc or (q[0] if q else "cinematic"),
            output_path=os.path.join(proj, f"s{i:03d}_ai_gen.mp4"),
            duration=d,
        )
    elif (_veo_circuit_open() or gemini_circuit_open) and (
        getattr(config, "PREFER_GEMINI_SCENE_IMAGES", False)
        or prefer_ai
        or (getattr(config, "USE_GEMINI_VIDEO_GEN", False) and i > 0 and prefer_ai)
    ):
        reason = "veo 429" if _veo_circuit_open() else "gemini_image 429"
        _log(f"[Visual] Sahne {i + 1}/{total_s}: {reason} devre acik — zorunlu stok regen")

    if _is_cancelled():
        return i, None, None

    if not p:
        p = fetch_scene_clip(
            q,
            i,
            proj,
            target_duration=d,
            scene_description=desc,
            cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
            narration=narr,
            visual_intent=intent,
            must_exclude=(intent.get("must_exclude") if isinstance(intent, dict) else None),
            recent_texts=None,
            niche_id=niche_id,
            channel_id=channel_id,
        )

    # A configured AI provider may fill only an otherwise missing licensed
    # shot. The provider manifest marks the result as synthetic for disclosure.
    if not p and not prefer_ai and not gemini_circuit_open:
        if _veo_render_allowed() and getattr(config, "USE_GEMINI_VIDEO_GEN", False):
            p = generate_veo_scene_clip(
                scene_description=desc or (q[0] if q else "cinematic subject footage"),
                output_path=os.path.join(proj, f"s{i:03d}_veo_fallback.mp4"),
                duration=d,
            )
        elif getattr(config, "USE_GEMINI_IMAGE_GEN", False) and config.GEMINI_API_KEY:
            p = generate_ai_image_clip(
                scene_description=desc or (q[0] if q else "cinematic subject footage"),
                output_path=os.path.join(proj, f"s{i:03d}_ai_fallback.mp4"),
                duration=d,
            )

    clip_entry = {
        "path": p,
        "duration": d,
        "narration": narr,
        "scene_description": desc,
        "search_queries": q,
        "badge_label": scene.get("badge_label"),
        "enable_pip": scene.get("enable_pip", False),
        "pip_path": scene.get("pip_path"),
        "handheld_shake": scene.get("handheld_shake", True),
        "affiliate_product": scene.get("affiliate_product", False),
        "beat_type": scene.get("beat_type", "conflict"),
        "mood": scene.get("mood", ""),
        "wipe_transition": scene.get("wipe_transition", False),
        "wipe_direction": scene.get("wipe_direction", "horizontal"),
        "visual_intent": intent,
        "scene_intent": scene.get("scene_intent") or (intent.get("shot_type") if isinstance(intent, dict) else ""),
        "camera_direction": scene.get("camera_direction") or "",
        "score": 100 if p else 0,
        "topic_match_score": 1.0 if p else 0.0,
        "t0": scene.get("t0", 0),
        "t1": scene.get("t1", 0),
    }
    return i, clip_entry, p


async def _fetch_scenes_parallel(scenes, plan, proj, total_s, gameplay_path=None, channel_id=None):
    """P1-13: asyncio.gather per-scene stock fetch via thread pool."""
    loop = asyncio.get_running_loop()

    def _cancelled():
        return bool(state.current_render_state.get("cancel_requested", False))

    async def _one(i, scene):
        if _cancelled():
            return i, None, None
        return await loop.run_in_executor(
            None,
            lambda i=i, scene=scene: _fetch_single_scene_visual(
                i, scene, plan, proj, total_s,
                gameplay_path=gameplay_path, channel_id=channel_id,
            ),
        )

    tasks = [_one(i, scene) for i, scene in enumerate(scenes)]
    results = await asyncio.gather(*tasks)
    if _cancelled():
        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
    return results


def process_video_task(req: VideoRenderRequest):
    old_stdout = sys.stdout
    sys.stdout = state.SSELogStreamer(old_stdout)
    db_id = None
    render_job_prefix = ""
    orig_lang = config.LANGUAGE
    orig_voice = config.TTS_VOICE
    orig_rate = config.TTS_RATE
    orig_sacred = bool(getattr(config, "TTS_SACRED_CALM", False))
    script_regen_494 = False
    gate_context = None
    slot_acquired = False

    def check_cancelled():
        if state.current_render_state.get("cancel_requested"):
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    try:
        # Chapter 28.8 / short-video-maker: Hardware Render Concurrency Guard & Structured Logging
        from render.render_limits import GLOBAL_RENDER_GATE
        from services.structured_logger import get_structured_logger
        task_id = getattr(req, "task_id", None) or f"task_{int(time.time()*1000)}"
        slogger = get_structured_logger("render_worker", task_id=task_id, niche=req.niche, topic=req.keyword)
        slogger.info("Render kuyruğuna alındı", extra={"queued_renders": GLOBAL_RENDER_GATE.queued_count, "active_renders": GLOBAL_RENDER_GATE.active_count})
        gate_context = GLOBAL_RENDER_GATE.acquire_slot_sync(task_id=task_id, timeout=180.0)
        gate_context.__enter__()
        slot_acquired = True
        slogger.info("Render donanım slotu tahsis edildi", extra={"active_renders": GLOBAL_RENDER_GATE.active_count})

        state.current_render_state["cancel_requested"] = False
        state.current_render_state["cancel_notified"] = False
        # Every job starts with clean terminal state. Otherwise a previous
        # failed render remains visible while a new render is already running.
        state.current_render_state["error"] = None
        state.current_render_state["video_url"] = None
        state.current_render_state["percent"] = 0
        state.current_render_state["step"] = "Başlatılıyor"

        # Item 448: auto-delete rendered outputs older than 30 days (best-effort)
        try:
            from system_resilience import purge_old_videos
            purge_result = purge_old_videos(max_age_days=30)
            if purge_result.get("purged_count"):
                _log(
                    f"[Ops] auto_delete: {purge_result['purged_count']} eski video silindi "
                    f"({purge_result['bytes_freed'] // 1024} KB)",
                    2,
                )
        except Exception:
            pass

        # Item 450: thermal throttle — reduce threads when CPU hot
        try:
            from hardware_detector import get_cpu_thermal_state
            thermal = get_cpu_thermal_state()
            if thermal.get("thermal_throttle_recommended"):
                config.RENDER_THREADS = max(2, min(getattr(config, "RENDER_THREADS", 4), 4))
                config.FFMPEG_THREADS = config.RENDER_THREADS
                _log(
                    f"[Ops] CPU thermal throttle: {thermal.get('temperature_c')}°C — "
                    f"threads={config.RENDER_THREADS}",
                    2,
                )
        except Exception:
            pass

        target_lang = (req.language or config.LANGUAGE or "tr").lower()
        config.LANGUAGE = target_lang

        plan = req.plan
        vm = getattr(req, "visual_mode", None)
        _stamp_visual_mode(plan, vm)
        keyword = (plan.get("title") if plan and plan.get("title") else req.keyword) or "Video"

        # Niche lock ASAP — voice gender + Gemini both need correct motif
        from director import resolve_niche_from_topic
        requested_niche = getattr(req, "niche", None) or "1_news_flash"
        locked_niche = resolve_niche_from_topic(keyword, requested_niche)
        req.niche = locked_niche

        ch_paths = config.channel_paths(getattr(req, "channel_id", None))
        db_id = database.add_video_record(
            keyword, target_lang, config.AI_PROVIDER, channel_slug=ch_paths["slug"]
        )
        from .pipeline_state_machine import PipelineStateMachine, PipelineStage
        sm = PipelineStateMachine(job_id=str(db_id or "job"), keyword=keyword, niche_id=locked_niche)
        _log(f"[Director] İşlem başlatılıyor: '{keyword}'...", 5)
        if locked_niche != requested_niche:
            _log(
                f"[Niche] Konu kilidi: '{requested_niche}' -> '{locked_niche}' "
                f"(baslik: {keyword[:48]})",
                6,
            )

        from scenes.hadith_overlay import is_sacred_niche
        if is_sacred_niche(locked_niche, keyword):
            config.TTS_SACRED_CALM = True
            config.TTS_RATE = getattr(config, "SACRED_TTS_RATE", "+8%")
            _log(
                "[TTS] Kutsal niş: tempo varsayılandan sakin. Ses hızlandırılmaz.",
                7,
            )

        gender = req.voice_gender or "male"
        if gender == "auto":
            from voice_humanizer import select_voice_gender
            gender = select_voice_gender(locked_niche, keyword)
        from tts_voices import resolve_voice, voice_gender_for_id
        selected_voice = resolve_voice(target_lang, voice_id=getattr(req, "tts_voice", None), gender=gender)
        config.TTS_VOICE = selected_voice
        config.TTS_GENDER = voice_gender_for_id(selected_voice, target_lang)

        check_cancelled()

        tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
        safe = re.sub(r'[^\w\s-]', '', keyword.translate(tr_map))
        safe = re.sub(r'\s+', '_', safe.strip())[:80]
        if not safe:
            safe = f"shorts_{int(time.time())}"
        render_job_prefix = safe
        assets_root = ch_paths["assets_dir"]
        output_root = ch_paths["output_dir"]
        if ch_paths["slug"] != "default":
            _log(f"[Channel] Çıktı klasörü: channels/{ch_paths['slug']}", 7)
        proj = os.path.join(assets_root, safe)
        os.makedirs(proj, exist_ok=True)
        sm.bind_project(proj, resume=bool(getattr(req, "resume", False)))
        reset_used_videos()
        # One render owns one visual manifest.  Reset it before parallel scene
        # acquisition so credits never leak from a previous job.
        try:
            from visuals.fetch import reset_job_manifest
            reset_job_manifest()
        except Exception as manifest_err:
            _log(f"[Visual] Manifest reset note: {manifest_err}", 8)
        reset_session_source_counts()

        # ─── 1–2) Script + DirectorPlan (Item 120: max 3 originality retries) ─
        from plagiarism_checker import check_script_originality
        from director import (
            compile_director_plan,
            fit_tts_to_timeline,
            master_audio_one_pass,
            pre_render_score,
            post_render_score,
            scenes_needing_regen,
            build_audio_events,
            apply_visual_intents,
        )
        from director.quality_gate import (
            clip_coverage_report,
            clip_uniqueness_report,
            format_duplicate_clips_error,
            format_missing_clips_error,
        )

        MAX_ORIGINALITY_RETRIES = 3
        use_director = getattr(config, "ENABLE_DIRECTOR_PLAN", True)
        director = None
        is_original = False
        similarity = 0.0
        matched_title = None
        final_variation_attempt = 0
        lang_label = "İngilizce" if target_lang == "en" else "Türkçe"

        for orig_attempt in range(MAX_ORIGINALITY_RETRIES):
            final_variation_attempt = orig_attempt
            check_cancelled()
            if orig_attempt > 0 or not plan:
                if orig_attempt == 0:
                    sm.transition_to(PipelineStage.STAGE_2_HOOK_NARRATIVE, f"Kanca ve Anlatı Üretimi: '{keyword}' (Niş: {locked_niche})", pct=8.0)
                    _log(
                        f"[Director] AI senaryosu oluşturuluyor ({lang_label} - {config.AI_PROVIDER}, "
                        f"niş={locked_niche}): '{keyword}'",
                        12,
                    )
                else:
                    _log(
                        f"[Item 120] Benzerlik yüksek (%{similarity * 100:.1f}) — "
                        f"senaryo yeniden üretiliyor ({orig_attempt + 1}/{MAX_ORIGINALITY_RETRIES})...",
                        14 + orig_attempt,
                    )
                plan = generate_scenes(
                    keyword,
                    niche_type=locked_niche,
                    language=target_lang,
                    variation_attempt=orig_attempt,
                    enable_outro=getattr(req, "enable_outro", True) is not False,
                )
                _stamp_visual_mode(plan, vm)
                try:
                    from hybrid_niches import enrich_plan_with_hybrid
                    plan = enrich_plan_with_hybrid(plan, keyword, locked_niche)
                except Exception:
                    pass

            if req.reddit_post and locked_niche == "2_reddit_confessions" and orig_attempt == 0:
                from scene_generator import generate_reddit_rewrite_script
                source_text = f"{req.reddit_post.get('title', '')}\n{req.reddit_post.get('body', '')}"
                plan = generate_reddit_rewrite_script(source_text, lang=target_lang)
                plan["reddit_post"] = req.reddit_post

            if orig_attempt == 0 and plan:
                plan = _ensure_ui_plan_narration_usable(
                    plan, keyword, locked_niche, target_lang
                )

            # Items 202-210, 239, 244, 248, 257 — always inject before Director compile
            # (covers UI-supplied plans that skipped generate_scenes)
            from scenes.retention_hooks import ensure_retention_hooks_on_plan

            # Human-craft BEFORE hooks — always (script layer is cheap).
            # CapCut density cuts run in composer with force=True when human_craft present,
            # including under RENDER_SAFE_MODE. Do NOT bypass craft here.
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
                _log(
                    f"[HumanCraft] POV={(plan.get('human_craft') or {}).get('pov_angle')} "
                    f"discovery={db.get('score')} pass={db.get('pass')}",
                    15,
                )
            except Exception as hc_err:
                _log(f"[HumanCraft] skip: {hc_err}")

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
            # O3: replace generic fallback search queries with narration-derived ones
            try:
                from scenes.enrichment import enforce_specific_search_queries
                if plan.get("scenes"):
                    enforce_specific_search_queries(plan["scenes"])
            except Exception:
                pass
            meta = plan.get("retention_metadata") or {}
            if meta.get("hook_strategy"):
                _log(
                    f"[RetentionHooks] {meta.get('hook_strategy')} | "
                    f"opening: {(meta.get('opening_hook') or '')[:60]}…",
                    16,
                )

            check_cancelled()
            sm.transition_to(PipelineStage.STAGE_3_DIRECTOR_PLAN, "DirectorPlan derleniyor (timeline + visual intent + audio bus)", pct=18.0)
            _log("[Director] DirectorPlan derleniyor (timeline + visual intent + audio bus)...", 18)
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
                _log(
                    f"[Timeline] {len(director.scenes)} sahne | {director.total_duration():.1f}s | "
                    f"niş={director.niche_id} | SFX={len(director.audio_events)}",
                    22,
                )
                if director.validation and not director.validation.get("ok"):
                    for err in director.validation.get("errors") or []:
                        _log(f"[Director][Uyarı] {err}")
            else:
                plan["niche_profile"] = get_niche_production_profile(locked_niche)

            with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
                json.dump(plan, f, ensure_ascii=False, indent=2)
            if director:
                with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                    json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)

            sm.transition_to(PipelineStage.STAGE_4_ORIGINALITY_GATE, "Özgünlük Kontrolü (Madde 120) ve Senaryo Kalite Kapısı", pct=25.0)
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
                    _log(
                        f"[QualityGate] UYARI: Senaryo benzerlik eşiğini aştı (%{similarity * 100:.1f} - '{matched_title}'), "
                        f"ancak 'Yine De Devam Et' seçeneği aktif olduğu için render onaylandı.",
                        25,
                    )
                break
            plan = None

        if not is_original:
            allow_similar = bool(
                getattr(req, "allow_similar_script", False)
                or getattr(req, "force_render", False)
                or getattr(req, "allow_draft_render", False)
            )
            if allow_similar:
                _log(
                    f"[QualityGate] UYARI: Senaryo benzerliği yüksek (%{similarity * 100:.1f}), "
                    f"ancak 'Yine De Devam Et' seçeneği aktif, render devam ediyor.",
                    25,
                )
            else:
                message = (
                    f"Senaryo benzerlik eşiğini aştı (%{similarity * 100:.1f}); "
                    f"en yakın kayıt: {matched_title or 'bilinmiyor'}. "
                    f"İçerik ve videolar farklıysa 'Yine De Devam Et' seçeneği ile render alabilirsiniz."
                )
            if db_id:
                database.update_video_status(db_id, "failed", error_message=message)
            state.broadcast_event("error", message)
            return

        if isinstance(plan, dict):
            plan.setdefault("meta", {})
            plan["meta"]["originality"] = {
                "similarity": round(float(similarity), 4),
                "originality_score": round(max(0.0, (1.0 - float(similarity)) * 100.0), 1),
                "matched_title": matched_title or "",
            }

        # Strict production contract: drafts that do not meet the intended
        # 45-60s / 6-12 scene / 120-170 word shape must be regenerated rather
        # than rendered as filler-heavy output.
        try:
            from production.quality import validate_script_quality
            script_quality = validate_script_quality(plan or {})
            plan.setdefault("meta", {})
            plan["meta"]["script_quality"] = script_quality

            if script_quality.get("hard_fail") and not getattr(req, "allow_draft_render", False):
                # Attempt auto-repair before aborting
                from scenes.narration_validate import apply_auto_repair_if_needed
                repaired_plan, narr_fixes, _ = apply_auto_repair_if_needed(plan)
                if narr_fixes:
                    _log(f"[QualityGate] Anlatım sözleşme ihlali için otomatik onarıldı: {len(narr_fixes)} fix", 24)
                    plan = repaired_plan
                    script_quality = validate_script_quality(plan)
                    plan["meta"]["script_quality"] = script_quality

                if script_quality.get("hard_fail") and not getattr(req, "allow_draft_render", False):
                    # Check if issues are non-fatal per-scene discrepancies or soft threshold deviations
                    issues_list = script_quality.get("issues", [])
                    non_fatal = all(
                        (i.startswith("scene_") and (
                            "words_below" in i
                            or "queries_insufficient" in i
                            or "missing_terminal" in i
                            or "visual_description" in i
                            or "mechanical_filler" in i
                        ))
                        or i.startswith("repeated_scene_fingerprint")
                        or i.startswith("word_count_out_of_band")
                        or i.startswith("duration_out_of_band")
                        or i.startswith("scene_count_out_of_band")
                        for i in issues_list
                    )
                    if non_fatal and len(plan.get("scenes", [])) >= 4:
                        _log(f"[QualityGate] UYARI: Sözleşme sınırındaki senaryo esnetilerek kabul edildi: {issues_list}", 24)
                    else:
                        reason = ", ".join(issues_list)
                        msg = f"Senaryo üretim sözleşmesi reddetti: {reason}"
                        _log(f"[QualityGate] HARD-FAIL: {msg}", 24)
                        if db_id:
                            database.update_video_status(db_id, "failed", error_message=msg)
                        state.broadcast_event("error", msg)
                        return
        except Exception as script_quality_err:
            msg = f"Senaryo kalite sözleşmesi çalıştırılamadı: {script_quality_err}"
            _log(f"[QualityGate] HARD-FAIL: {msg}", 24)
            if db_id:
                database.update_video_status(db_id, "failed", error_message=msg)
            state.broadcast_event("error", msg)
            return

        if db_id and plan.get("scenes"):
            database.save_scenes(db_id, plan["scenes"])

        # Pre-render quality gate (auto-repair once before hard block)
        if director:
            from scenes.narration_validate import apply_auto_repair_if_needed

            plan_dict = director.to_legacy_plan()
            repaired_plan, narr_fixes, _ = apply_auto_repair_if_needed(plan_dict)
            if narr_fixes:
                _log(f"[QualityGate] Anlatim otomatik duzeltildi: {len(narr_fixes)} fix", 24)
                director = compile_director_plan(
                    repaired_plan,
                    title=keyword,
                    niche_id=locked_niche,
                    language=target_lang,
                    reddit_post=getattr(req, "reddit_post", None),
                )
                plan = director.to_legacy_plan()
                with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
                    json.dump(plan, f, ensure_ascii=False, indent=2)
                with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                    json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)

            pre = pre_render_score(director)
            _log(
                f"[QualityGate] Pre-score={pre['score']} ok={pre['ok']} issues={pre.get('issues')}",
                25,
            )
            semantic_block = [
                i for i in pre.get("issues", [])
                if i.startswith("fragment") or i.startswith("low_words")
                or i.startswith("empty_narration") or i.startswith("no_terminal")
            ]
            if semantic_block:
                # Second-chance repair after recompile/enrich drift vs /api/script/generate
                plan_dict = director.to_legacy_plan()
                repaired_plan, narr_fixes2, _ = apply_auto_repair_if_needed(plan_dict)
                if narr_fixes2:
                    _log(
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
                    pre = pre_render_score(director)
                    semantic_block = [
                        i for i in pre.get("issues", [])
                        if i.startswith("fragment") or i.startswith("low_words")
                        or i.startswith("empty_narration") or i.startswith("no_terminal")
                    ]
            if semantic_block:
                msg = f"Pre-render narration gate blocked: {', '.join(semantic_block)}"
                _log(f"[QualityGate] {msg}", 25)
                if db_id:
                    database.update_video_status(db_id, "failed", error_message=msg)
                state.broadcast_event("error", msg)
                return
            bad = scenes_needing_regen(director, pre)
            if bad:
                apply_visual_intents(director.scenes, director.niche_id, title=director.title)
                build_audio_events(director)
                plan = director.to_legacy_plan()
                _log(f"[Visual] {len(bad)} sahne intent yenilendi (must_exclude temizliği)")

        # Monetization-first gate: the render path must enforce the same
        # policy checks exposed by the script API.  Previously a plan could
        # pass the UI audit and still be rendered by the worker.
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
                    fh, ensure_ascii=False, indent=2,
                )
            _log(
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
                msg = f"Para kazanma kalite kapısı renderı durdurdu: {reason}"
                _log(f"[Compliance] HARD-FAIL: {msg}", 28)
                if db_id:
                    database.update_video_status(db_id, "failed", error_message=msg)
                state.broadcast_event("error", msg)
                return
            if compliance_result.get("hard_fail"):
                # Research evidence is a publication gate, not a render safety
                # gate. Keep the diagnosis visible so the UI can request sources.
                reason = ", ".join(compliance_result.get("hard_fail_reasons") or [])
                _log(
                    f"[Compliance] RENDER_ALLOWED_REVIEW: {reason or 'publication review required'}",
                    27,
                )
        except Exception as compliance_err:
            msg = f"Uyumluluk kalite kapısı çalıştırılamadı: {compliance_err}"
            _log(f"[Compliance] HARD-FAIL: {msg}", 28)
            if db_id:
                database.update_video_status(db_id, "failed", error_message=msg)
            state.broadcast_event("error", msg)
            return

        # ─── 3) Acquire visuals ───────────────────────────────────────────
        check_cancelled()
        scenes = plan.get("scenes", [])
        total_s = len(scenes)
        sm.transition_to(PipelineStage.STAGE_5_ASSET_INGESTION, f"Varlık Edinimi: {total_s} sahne için görsel klipler temin ediliyor", pct=32.0)
        _log(f"[Visual] Stok videolar aranıyor ({total_s} sahne, semantik skor)...", 30)

        clips = []
        gameplay_path = None
        recent_texts = []
        retention_meta = (plan or {}).get("retention_metadata") or {}
        niche_profile = (plan or {}).get("niche_profile") or {}
        if not niche_profile and locked_niche:
            try:
                niche_profile = get_niche_production_profile(locked_niche) or {}
                plan["niche_profile"] = niche_profile
            except Exception:
                niche_profile = {}
        production_rules = (niche_profile.get("production_rules") or {}) if isinstance(niche_profile, dict) else {}
        gp_cat = (getattr(req, "gameplay_category", None) or "auto").strip().lower()
        # Sabun kesme / parkour picked in the UI is the split request.
        # Niche profile used to clear the checkbox and the render went full frame.
        if gp_cat not in ("", "auto"):
            req.split_screen = True
        # dopamin_split_screen stays in metadata. It does not fetch gameplay.
        # Split is the user checkbox, a real hybrid niche, or the niche rule.
        hybrid_split = bool(plan.get("hybrid_niche")) and bool(plan.get("hybrid_split_screen"))
        needs_split_screen = (
            getattr(req, "split_screen", False)
            or hybrid_split
            or bool(production_rules.get("split_screen"))
        )
        if needs_split_screen:
            req.split_screen = True
        resume_visuals = sm.reusable(PipelineStage.STAGE_5_ASSET_INGESTION)
        saved_visuals = sm.stage_artifacts(PipelineStage.STAGE_5_ASSET_INGESTION) if resume_visuals else {}
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
                cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
            )
            if not gameplay_path:
                state.broadcast_event("log", "Gameplay havuzu boş — stok aramasına düşülüyor…")
                gameplay_path = search_and_download(
                    ["mobile game gameplay", "parkour game screen recording", "arcade gameplay"],
                    10_000, proj, target_duration=12, preferred_source="pexels",
                    cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
                    allow_custom=False,
                )
            if not gameplay_path:
                raise RuntimeError("Split-screen için daha önce kullanılmamış oyun/parkur klibi bulunamadı.")

        check_cancelled()
        if resume_visuals:
            gameplay_path = saved_visuals.get("gameplay_path") or None
            clips = []
            for i, item in enumerate(saved_visuals.get("clips") or []):
                entry = {
                    "path": item.get("path"),
                    "duration": item.get("duration") or (scenes[i].get("duration") if i < len(scenes) else 5),
                }
                if item.get("tail_path"):
                    entry["tail_path"] = item["tail_path"]
                    entry["head_duration"] = item.get("head_duration")
                clips.append(entry)
                if director and i < len(director.scenes):
                    director.scenes[i].path = entry.get("path")
            _log("[Resume] Görseller duruyor. Stok indirme atlandı.", 32)
        else:
            _log(f"[Visual] Paralel stok fetch başlıyor ({total_s} sahne, asyncio.gather)...", 32)
            _channel_id = getattr(req, "channel_id", None)
            fetch_results = asyncio.run(
                _fetch_scenes_parallel(
                    scenes, plan, proj, total_s,
                    gameplay_path=gameplay_path, channel_id=_channel_id,
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
                state.broadcast_event("progress", {"percent": progress_pct, "step": step_msg})
                state.broadcast_event(
                    "log",
                    f"  -> Sahne {i + 1}/{total_s}: {(desc or intent.get('subject', ''))[:50]}",
                )

        def _retry_missing_clips(max_passes=2):
            """Regen failed scene indices only (P0-03 unique clip contract)."""
            for attempt in range(1, max_passes + 1):
                report = clip_coverage_report(clips)
                missing = report["missing_indices"]
                if not missing:
                    return
                _log(
                    f"[Visual] Retry pass {attempt}/{max_passes}: "
                    f"{len(missing)} missing scene(s) -> indices (0-based) {missing[:16]}"
                    + (f" ... (+{len(missing) - 16})" if len(missing) > 16 else "")
                    + (
                        "; lavfi yedek açık"
                        if procedural_on_retry_pass(attempt, max_passes)
                        else "; stok araması"
                    ),
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
                            intent.get("search_queries")
                            or scene.get("search_queries")
                            or scene.get("search_query")
                            or []
                        ),
                    )
                    if not q:
                        _log(
                            f"[Visual] Retry pass {attempt}: scene {i + 1}/{total_s} "
                            "has no filmable subject; left missing"
                        )
                        continue
                    p = fetch_scene_clip(
                        q, i, proj, target_duration=clips[i]["duration"],
                        scene_description=scene.get("scene_description", ""),
                        narration=scene.get("narration", ""),
                        visual_intent=intent,
                        cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
                        recent_texts=recent_texts,
                        niche_id=(
                            (plan or {}).get("locked_niche")
                            or (plan or {}).get("niche_id")
                            or ""
                        ),
                        channel_id=getattr(req, "channel_id", None),
                        allow_procedural=procedural_on_retry_pass(attempt, max_passes),
                    )
                    clips[i]["path"] = p
                    if p:
                        recent_texts.append(os.path.basename(p).lower())
                        if director and i < len(director.scenes):
                            director.scenes[i].path = p
                    else:
                        _log(f"[Visual] Retry pass {attempt}: scene {i + 1}/{total_s} still failed")

        if not resume_visuals:
            check_cancelled()
            _retry_missing_clips(max_passes=2)
            check_cancelled()
            attach_short_clip_partners(
                clips,
                scenes,
                proj,
                niche_id=(
                    (plan or {}).get("locked_niche")
                    or (plan or {}).get("niche_id")
                    or ""
                ),
                channel_id=getattr(req, "channel_id", None),
                cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
            )
            visual_files = []
            visual_clips = []
            for clip in clips or []:
                if not isinstance(clip, dict):
                    continue
                visual_clips.append({
                    "path": clip.get("path"),
                    "duration": clip.get("duration"),
                    "tail_path": clip.get("tail_path") or "",
                    "head_duration": clip.get("head_duration"),
                })
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

        # O1: Clip/plan count sync — director recompile may change scene count.
        # Trim or pad clips to match current plan so pre-audit count check is accurate.
        _plan_scene_count = len(plan.get("scenes") or [])
        if _plan_scene_count > 0 and len(clips) != _plan_scene_count:
            if len(clips) > _plan_scene_count:
                _log(
                    f"[O1-Sync] clips={len(clips)} > plan={_plan_scene_count} "
                    f"— trimming extras", 58
                )
                clips = clips[:_plan_scene_count]
            else:
                _log(
                    f"[O1-Sync] clips={len(clips)} < plan={_plan_scene_count} "
                    f"— padding with None entries", 58
                )
                while len(clips) < _plan_scene_count:
                    clips.append({"path": None, "duration": 5.0})

        coverage = clip_coverage_report(clips)
        ok_clips = coverage["ok"]
        _log(f"[Visual] Stok klip indirme tamamlandi: {ok_clips}/{total_s}", 58)

        # ─── Pre-render pipeline audit ────────────────────────────────
        try:
            from render.pipeline_audit import pre_render_audit, audit_search_queries
            _pre_audit = pre_render_audit(
                clips,
                audio_path=None,
                plan=plan,
            )
            _q_audit = audit_search_queries(clips)
            for _w in _pre_audit.get("warnings") or []:
                _log(f"[PipelineAudit] WARN: {_w}")
            for _e in _pre_audit.get("errors") or []:
                _log(f"[PipelineAudit] ERROR: {_e}", 58)
            if _q_audit.get("issue_count", 0) > 0:
                _log(
                    f"[PipelineAudit] Search query issues: "
                    f"{_q_audit['issue_count']} scenes have generic/empty/off-topic queries"
                )
            import json as _json
            with open(os.path.join(proj, "pipeline_audit_pre.json"), "w", encoding="utf-8") as _af:
                _json.dump({"pre_render": _pre_audit, "query_audit": _q_audit}, _af, ensure_ascii=False, indent=2)
            if not _pre_audit["ok"]:
                _blocking = [e for e in (_pre_audit.get("errors") or []) if "duplicate_clips" in e or "scene_count_too_low" in e]
                if _blocking:
                    _msg = f"Pre-render audit blocked render: {'; '.join(_blocking)}"
                    _log(f"[PipelineAudit] HARD-FAIL: {_msg}", 58)
                    if db_id:
                        database.update_video_status(db_id, "failed", error_message=_msg)
                    state.broadcast_event("error", _msg)
                    return
        except Exception as _audit_err:
            _log(f"[PipelineAudit] audit skip: {_audit_err}")

        # K1: Retry narration mismatches using provider evidence, then block any unresolved scene.
        from render.pipeline_audit import (
            attach_candidate_metadata,
            require_semantic_confidence,
            retry_low_confidence_scenes,
        )
        from scenes.enrichment import _narration_to_subject_tokens

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
            merged_rows.update({
                row.get("scene_index"): row
                for row in rows
                if isinstance(row, dict) and row.get("scene_index") is not None
            })
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
            _ntokens = _narration_to_subject_tokens(_narr or _desc)
            if not _ntokens:
                _log(f"[K1-Semantic] Scene {_si + 1}: no filmable narration tokens; retry unavailable")
                return
            _narr_queries = [
                f"{' '.join(_ntokens[:2]).lower()} closeup",
                f"{' '.join(_ntokens[:2]).lower()} detail shot",
                f"{_ntokens[0].lower()} footage",
            ]
            check_cancelled()
            try:
                _np = fetch_scene_clip(
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
                _log(f"[K1-Semantic] Scene {_si + 1} retry failed: {_retry_err}")
                return
            if _np:
                _log(f"[K1-Semantic] Scene {_si + 1} re-fetched: {os.path.basename(_np)}")
                _clip["path"] = _np
                if director and _si < len(director.scenes):
                    director.scenes[_si].path = _np
                attach_candidate_metadata(clips, _candidate_manifest_rows())
            else:
                _log(f"[K1-Semantic] Scene {_si + 1} retry returned no clip")

        _retried_scenes, _low_confidence_scenes = retry_low_confidence_scenes(
            clips, _retry_semantic_scene, threshold=0.08,
        )
        if _retried_scenes:
            _log(
                f"[K1-Semantic] Retried scenes {[index + 1 for index in _retried_scenes]}; "
                f"remaining low-confidence scenes {[index + 1 for index in _low_confidence_scenes]}"
            )
        if _low_confidence_scenes:
            require_semantic_confidence(_low_confidence_scenes)

        if ok_clips == 0:
            msg = "Stok video indirilemedi."
            state.broadcast_event("error", msg)
            if db_id:
                database.update_video_status(db_id, "failed", error_message=msg)
            return

        if not coverage["complete"]:
            msg = format_missing_clips_error(coverage)
            _log(f"[Visual] HARD-FAIL: {msg}", 58)
            if director:
                with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                    json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)
            if db_id:
                database.update_video_status(db_id, "failed", error_message=msg)
            state.broadcast_event("error", msg)
            return

        for _dup_pass in range(1, 3):
            uniqueness = clip_uniqueness_report(clips, min_unique=total_s)
            if uniqueness["ok"]:
                break
            dupes = sorted(set(
                (uniqueness.get("duplicate_hash_indices") or [])
                + (uniqueness.get("duplicate_path_indices") or [])
            ))
            if not dupes:
                break
            _log(
                f"[Visual] Tekrarlı klip pass {_dup_pass}/2: "
                f"sahneler {[i + 1 for i in dupes]} yeniden aranıyor",
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
                        intent.get("search_queries")
                        or scene.get("search_queries")
                        or scene.get("search_query")
                        or []
                    ),
                )
                if not q:
                    continue
                old = clips[i].get("path")
                p = fetch_scene_clip(
                    q, i, proj, target_duration=clips[i].get("duration", 6),
                    scene_description=scene.get("scene_description", ""),
                    narration=scene.get("narration", ""),
                    visual_intent=intent,
                    cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
                    recent_texts=recent_texts,
                    niche_id=(
                        (plan or {}).get("locked_niche")
                        or (plan or {}).get("niche_id")
                        or ""
                    ),
                    channel_id=getattr(req, "channel_id", None),
                    allow_procedural=procedural_on_retry_pass(_dup_pass, 2),
                )
                if not p or p == old:
                    continue
                clips[i]["path"] = p
                replaced += 1
                recent_texts.append(os.path.basename(p).lower())
                if director and i < len(director.scenes):
                    director.scenes[i].path = p
                _log(f"[Visual] Sahne {i + 1} tekrarı değiştirildi: {os.path.basename(p)}", 58)
            if replaced == 0:
                break

        uniqueness = clip_uniqueness_report(clips, min_unique=total_s)
        if not uniqueness["ok"]:
            msg = format_duplicate_clips_error(uniqueness)
            _log(f"[Visual] HARD-FAIL: {msg}", 58)
            if director:
                with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                    json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)
            if db_id:
                database.update_video_status(db_id, "failed", error_message=msg)
            state.broadcast_event("error", msg)
            return

        # ViewMade-style deliverable: ship an auditable source ledger with the
        # render.  This is also the single place where the description-ready
        # attribution block is created, after all retries have settled.
        try:
            from visuals.fetch import write_job_credits, get_job_manifest
            credits = write_job_credits(proj)
            manifest_count = len(get_job_manifest())
            disclosure = ((plan.get("meta") or {}).get("compliance") or {}).get("ai_disclosure") or {}
            # Persist the complete production chain before encoding so a
            # failed render still leaves an auditable explanation.
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
            originality = ((plan.get("meta") or {}).get("originality") or {})
            publishing = build_publishing_package(
                title=plan.get("title") or keyword,
                niche_id=locked_niche,
                viewer_score=(plan.get("meta") or {}).get("viewer_score"),
                manifest_items=manifest_rows,
                research_gate_passed=research_gate_passed((plan.get("meta") or {}).get("compliance") or {}),
                license_status=license_status_from_manifest(manifest_rows),
                originality_score=float(originality.get("originality_score") or 0.0) if isinstance(originality, dict) else 0.0,
                ai_disclosure=disclosure,
            )
            publishing["research_brief"] = plan.get("research_brief") or {}
            publishing["credits_files"] = credits
            publishing["policy_decision"] = ((plan.get("meta") or {}).get("compliance") or {}).get("niche_gate") or {}
            publishing["research_decision"] = ((plan.get("meta") or {}).get("compliance") or {}).get("research") or {}
            publishing["publication_decision"] = (plan.get("meta") or {}).get("publication") or {}
            publishing["language"] = target_lang
            publishing["description_appendix"] = "\n\n".join(
                part for part in [
                    credits.get("description_block", "").strip(),
                    disclosure.get("description_paragraph", "").strip(),
                ] if part
            )
            with open(os.path.join(proj, "publishing_package.json"), "w", encoding="utf-8") as fh:
                json.dump(publishing, fh, ensure_ascii=False, indent=2)
            _log(
                f"[Compliance] visual_credits hazır: {manifest_count} kaynak | "
                f"{os.path.basename(credits['json'])} | publishing_package hazır",
                59,
            )
        except Exception as credits_err:
            msg = f"Görsel kaynak kayıt dosyası oluşturulamadı: {credits_err}"
            _log(f"[Compliance] HARD-FAIL: {msg}", 59)
            if db_id:
                database.update_video_status(db_id, "failed", error_message=msg)
            state.broadcast_event("error", msg)
            return

        # Persist successful paths before TTS/render
        if director:
            with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)
            plan = director.to_legacy_plan()
            with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
                json.dump(plan, f, ensure_ascii=False, indent=2)

        # ─── 4) TTS ───────────────────────────────────────────────────────
        check_cancelled()
        lang_title = "İngilizce" if target_lang == "en" else "Türkçe"
        from tts_engine import active_tts_provider
        sm.transition_to(PipelineStage.STAGE_6_TTS_SYNC, f"Seslendirme ve Zamanlama ({active_tts_provider()}): {lang_title} ses üretiliyor", pct=58.0)
        _log(f"[Timeline] {lang_title} Seslendirme ({active_tts_provider()})...", 62)
        audio_path = os.path.join(config.AUDIO_DIR, f"{safe}.wav")

        from voice_humanizer import VoiceHumanizer
        niche_for_voice = (director.niche_id if director else req.niche)
        asmr_profile = VoiceHumanizer.get_asmr_voice_settings(niche_for_voice, keyword)
        narration_text = plan.get("full_narration") or ""

        tts_restored = False
        saved_tts = {}
        if sm.reusable(PipelineStage.STAGE_6_TTS_SYNC):
            saved_tts = sm.stage_artifacts(PipelineStage.STAGE_6_TTS_SYNC)
            saved_audio = saved_tts.get("audio_path") or ""
            saved_timings = saved_tts.get("timings") or []
            if saved_audio and isinstance(saved_timings, list) and saved_timings:
                audio_path = saved_audio
                timings = saved_timings
                tts_restored = True
                _log("[Resume] Ses dosyası duruyor. TTS atlandı.", 62)

        # Post-compile narration gate — auto-repair once, then hard block
        if director and not tts_restored:
            from director.quality_gate import check_narration_integrity
            from director import pre_render_score as _pre_render_score
            from scenes.narration_validate import apply_auto_repair_if_needed

            tts_plan, tts_fixes, _ = apply_auto_repair_if_needed(director.to_legacy_plan())
            if tts_fixes:
                check_cancelled()
                _log(f"[QualityGate] TTS oncesi anlatim duzeltildi: {len(tts_fixes)} fix", 60)
                director = compile_director_plan(
                    tts_plan,
                    title=keyword,
                    niche_id=locked_niche,
                    language=target_lang,
                    reddit_post=getattr(req, "reddit_post", None),
                )
                plan = director.to_legacy_plan()
                narration_text = plan.get("full_narration") or ""

            # Chapter 28.10 / youtube-shorts-pipeline: Retention Guardrails & Cliché Stripping
            try:
                from services.niche_guardrails import validate_script_niche_compliance
                niche_val = validate_script_niche_compliance(
                    narration_text,
                    niche_id=director.niche_id if director else getattr(req, "niche", ""),
                    lang=target_lang,
                )
                if not niche_val.get("compliant", True):
                    _log(f"[NicheGuardrails] Cliché tespit edildi ({len(niche_val.get('violations', []))} adet), temizleniyor...", 60)
                    narration_text = niche_val.get("cleaned_text", narration_text)
                    if plan:
                        plan["full_narration"] = narration_text
            except Exception as ng_err:
                _log(f"[NicheGuardrails] Denetim uyarısı: {ng_err}", 60)

            tts_pre = _pre_render_score(director)
            tts_block = [
                i for i in tts_pre.get("issues", [])
                if i.startswith("fragment") or i.startswith("low_words")
                or i.startswith("empty_narration") or i.startswith("no_terminal")
            ]
            if tts_block:
                msg = f"TTS öncesi anlatım kapısı: {', '.join(tts_block)}. Senaryoyu yeniden üretin."
                _log(f"[QualityGate] {msg}", 61)
                if db_id:
                    database.update_video_status(db_id, "failed", error_message=msg)
                state.broadcast_event("error", msg)
                return

        if not tts_restored:
            sm.invalidate_from(PipelineStage.STAGE_6_TTS_SYNC)
            _, timings = generate_narration_with_timing(narration_text, audio_path, voice_profile=asmr_profile)
            _log(f"[Timeline] TTS tamamlandı — {len(timings)} kelime zamanlaması", 68)

        if director and tts_restored:
            audio_dur = float(saved_tts.get("audio_dur") or 0.0)
            speed = float(saved_tts.get("speed") or 1.0)
            for i, span in enumerate(saved_tts.get("scene_spans") or []):
                if not isinstance(span, dict):
                    continue
                if i < len(director.scenes):
                    director.scenes[i].duration = float(span.get("duration") or director.scenes[i].duration)
                    director.scenes[i].t0 = float(span.get("t0") or 0.0)
                    director.scenes[i].t1 = float(span.get("t1") or 0.0)
                if i < len(clips) and isinstance(clips[i], dict):
                    clips[i]["duration"] = director.scenes[i].duration if i < len(director.scenes) else span.get("duration")
                    clips[i]["t0"] = span.get("t0")
                    clips[i]["t1"] = span.get("t1")
            plan = director.to_legacy_plan()
            _log(
                f"[Timeline] Kayıtlı TTS {audio_dur:.1f}s (speed×{speed:.2f})",
                70,
            )
        elif director:
            fitted = os.path.join(config.AUDIO_DIR, f"{safe}_fitted.wav")

            def _wav_seconds(path: str) -> float:
                import wave
                try:
                    with wave.open(path, "rb") as w:
                        rate = float(w.getframerate() or 0)
                        return (w.getnframes() / rate) if rate else 0.0
                except Exception:
                    return 0.0

            def _condense_and_retts(raw_sec: float) -> None:
                nonlocal director, plan, narration_text, audio_path, timings, script_regen_494
                from director.timeline import recover_overlong_narration
                from scenes.generator import _gemini_script_circuit_open

                spoken = len((narration_text or "").split())
                _log(
                    f"[Timeline] TTS {raw_sec:.1f}s / {spoken} kelime — doğal tempo, yerel kısaltma. Hızlandırma yok.",
                    69,
                )
                if _gemini_script_circuit_open():
                    _log("[Timeline] gemini_script açık — Gemini çağrılmadı.", 69)
                new_plan = recover_overlong_narration(plan, audio_seconds=raw_sec)
                new_words = len((new_plan.get("full_narration") or "").split())
                if new_words <= 0 or new_words >= spoken:
                    raise RuntimeError(
                        f"Madde 494 hard-fail: yerel kısaltma {spoken} kelimeden inemedi "
                        f"(TTS {raw_sec:.1f}s). Tek deneme."
                    )
                script_regen_494 = True
                new_director = compile_director_plan(
                    new_plan,
                    title=keyword,
                    niche_id=locked_niche,
                    language=target_lang,
                    reddit_post=getattr(req, "reddit_post", None),
                )
                director = new_director
                plan = director.to_legacy_plan()
                narration_text = plan.get("full_narration") or ""
                if len(clips) > len(director.scenes):
                    del clips[len(director.scenes):]
                with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
                    json.dump(plan, f, ensure_ascii=False, indent=2)
                with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                    json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)
                _log(f"[Timeline] Kısaltılmış anlatım {new_words} kelime — TTS bir kez daha.", 69)
                _, timings_new = generate_narration_with_timing(
                    narration_text, audio_path, voice_profile=asmr_profile
                )
                timings = timings_new

            raw_sec = _wav_seconds(audio_path)
            if raw_sec > 60.0 and not script_regen_494:
                try:
                    _condense_and_retts(raw_sec)
                except RuntimeError as cond_err:
                    msg = str(cond_err)
                    _log(f"[QualityGate] {msg}", 69)
                    if db_id:
                        database.update_video_status(db_id, "failed", error_message=msg)
                    state.broadcast_event("error", msg)
                    return
            try:
                audio_path, timings, audio_dur, speed = fit_tts_to_timeline(
                    audio_path, director, word_timings=timings, output_path=fitted
                )
            except RuntimeError as fit_err:
                if "494" not in str(fit_err):
                    raise
                if not script_regen_494:
                    try:
                        _condense_and_retts(_wav_seconds(audio_path) or raw_sec)
                        audio_path, timings, audio_dur, speed = fit_tts_to_timeline(
                            audio_path, director, word_timings=timings, output_path=fitted
                        )
                    except RuntimeError as second_err:
                        msg = (
                            "Senaryoyu yeniden üretin: anlatım TTS süre bandına sığmıyor (Madde 494). "
                            + str(second_err)
                        )
                        _log(f"[QualityGate] {msg}", 69)
                        if db_id:
                            database.update_video_status(db_id, "failed", error_message=msg)
                        state.broadcast_event("error", msg)
                        return
                else:
                    msg = (
                        "Senaryoyu yeniden üretin: anlatım TTS süre bandına sığmıyor (Madde 494). "
                        "İkinci TTS de 60s üstünde. Hızlandırma yok."
                    )
                    _log(f"[QualityGate] {msg}", 69)
                    if db_id:
                        database.update_video_status(db_id, "failed", error_message=msg)
                    state.broadcast_event("error", msg)
                    return

            # Sync clip durations from director after fit
            for i, s in enumerate(director.scenes):
                if i < len(clips):
                    clips[i]["duration"] = s.duration
                    clips[i]["t0"] = s.t0
                    clips[i]["t1"] = s.t1
            plan = director.to_legacy_plan()
            _log(
                f"[Timeline] TTS {audio_dur:.1f}s (speed×{speed:.2f}; doğal tempo, hızlandırma yok)",
                70,
            )

        if not tts_restored and audio_path and os.path.isfile(audio_path):
            scene_spans = []
            if director:
                scene_spans = [
                    {"duration": s.duration, "t0": s.t0, "t1": s.t1}
                    for s in director.scenes
                ]
            sm.mark_done(
                PipelineStage.STAGE_6_TTS_SYNC,
                artifacts={
                    "audio_path": audio_path,
                    "timings": timings,
                    "audio_dur": float(audio_dur) if director else 0.0,
                    "speed": float(speed) if director else 1.0,
                    "scene_spans": scene_spans,
                },
                files=[audio_path],
            )

        # Telifsiz BGM (Pixabay / Mixkit / VoiceLab / Catalog)
        bgm_req = (req.bgm_track or "").strip()
        bgm_track = ""
        from bgm_manager import request_mutes_bgm
        user_wants_muted = request_mutes_bgm(bgm_req, getattr(req, "enable_bgm", None))

        if not user_wants_muted:
            if bgm_req:
                from youtube_safe_bgm_catalog import resolve_bgm_path, ensure_catalog_track
                local_p = resolve_bgm_path(bgm_req)
                if not local_p or not os.path.isfile(local_p) or os.path.getsize(local_p) < 2000:
                    _log(f"[BGM] Katalog parçası indiriliyor: {bgm_req}...", 70)
                    downloaded_fn = ensure_catalog_track(filename=bgm_req) or ensure_catalog_track(track_id=bgm_req)
                    if downloaded_fn:
                        bgm_track = downloaded_fn
                        _log(f"[BGM] Katalog parçası hazır: {bgm_track}", 71)
                    else:
                        _log(f"[BGM] Katalog indirme başarısız ({bgm_req}), alternatif kütüphaneden seçiliyor...", 71)
                        bgm_track = ""
                else:
                    bgm_track = os.path.basename(local_p)
                    _log(f"[BGM] Seçili fon müziği doğrulandı: {bgm_track}", 71)

            # Auto-fetch if not specified or failed
            if (not bgm_track) and getattr(config, "AUTO_FETCH_ROYALTY_FREE_BGM", True) and getattr(config, "ENABLE_BGM", True):
                try:
                    from royalty_free_audio import fetch_royalty_free_bgm
                    mood_q = "ambient cinematic"
                    niche_hint = ""
                    if director:
                        tone = (director.niche_profile or {}).get("tone") or director.niche_id or ""
                        niche_hint = director.niche_id or tone or ""
                        mood_q = f"{tone} ambient cinematic"
                    bgm_track = fetch_royalty_free_bgm(mood_q, prefer="auto", niche=niche_hint) or ""
                    if bgm_track:
                        _log(f"[VoiceLab/RF] Telifsiz BGM secildi: {bgm_track}", 71)
                except Exception as e:
                    print(f"  [VoiceLab/RF] Notice: {e}")

            # Pick from catalog for niche as primary fallback
            if (not bgm_track) and getattr(config, "ENABLE_BGM", True):
                try:
                    from youtube_safe_bgm_catalog import pick_catalog_bgm_for_niche
                    niche_hint = director.niche_id if director else getattr(req, "niche", "")
                    bgm_track = pick_catalog_bgm_for_niche(niche_id=niche_hint, query=keyword) or ""
                    if bgm_track:
                        _log(f"[BGM] Niş uyumlu katalog müziği seçildi: {bgm_track}", 71)
                except Exception as e:
                    print(f"  [BGM] Notice: {e}")

            # Fallback to local default safe track
            if (not bgm_track) and getattr(config, "ENABLE_BGM", True):
                try:
                    from bgm_manager import get_safe_default_bgm_path
                    default_p = get_safe_default_bgm_path()
                    if default_p and os.path.exists(default_p):
                        bgm_track = os.path.basename(default_p)
                        _log(f"[BGM] Varsayılan telifsiz ambient müzik seçildi: {bgm_track}", 71)
                except Exception as e:
                    print(f"  [BGM] Safe default notice: {e}")

            # Item 190: BGM telif heuristic — riskli parça yerine güvenli fallback
            if bgm_track:
                try:
                    from copyright_risk import scan_audio_copyright_risk
                    from bgm_manager import get_safe_default_bgm_path
                    audio_scan = scan_audio_copyright_risk([bgm_track])
                    if not audio_scan.get("safe"):
                        _log(f"[Copyright] BGM risk: {bgm_track} → royalty_free_ambient", 71)
                        bgm_track = os.path.basename(get_safe_default_bgm_path())
                except Exception:
                    pass
        else:
            _log("[BGM] Kullanıcı tercihi: Müziksiz video render ediliyor.", 71)

        # ─── 5) Audio master (one-pass) ────────────────────────────────────
        check_cancelled()
        sm.transition_to(PipelineStage.STAGE_7_AUDIO_MASTERING, "Akustik Tasarım ve Miksaj: Sidechain ducking (-18dB) ve EBU R128 (-14 LUFS)", pct=68.0)
        mastered = os.path.join(config.AUDIO_DIR, f"{safe}_master.wav")
        master_restored = sm.reusable(
            PipelineStage.STAGE_7_AUDIO_MASTERING,
            require=[PipelineStage.STAGE_6_TTS_SYNC],
        )
        if master_restored:
            saved_master = sm.stage_artifacts(PipelineStage.STAGE_7_AUDIO_MASTERING)
            audio_path = saved_master.get("audio_path") or audio_path
            if isinstance(saved_master.get("timings"), list) and saved_master.get("timings"):
                timings = saved_master["timings"]
            _log("[Resume] Master ses duruyor. Miks atlandı.", 72)
        elif director:
            from director.audio_bus import apply_intro_whoosh_pref
            director.effect_manifest = apply_intro_whoosh_pref(
                director.effect_manifest,
                bool(getattr(req, "enable_intro_whoosh", False)),
            )
            from bgm_manager import resolve_studio_audio_mix
            mix_cfg = resolve_studio_audio_mix(
                duck_attack_ms=getattr(req, "duck_attack_ms", None),
                duck_release_ms=getattr(req, "duck_release_ms", None),
                intro_blast=getattr(req, "intro_blast", None),
                enable_intro_whoosh=bool(getattr(req, "enable_intro_whoosh", False)),
                outro_swell_sec=getattr(req, "outro_swell_sec", None),
                enable_outro=getattr(req, "enable_outro", True) is not False,
                enable_outro_swell=getattr(req, "enable_outro_swell", True) is not False,
                allow_bgm=not user_wants_muted,
            )
            _log(
                f"[AudioMaster] EQ + SFX bus + BGM ({bgm_track or 'yok'}) "
                f"duck {int(mix_cfg['duck_attack_ms'])}/{int(mix_cfg['duck_release_ms'])} ms "
                f"blast {mix_cfg['intro_blast']:.2f} swell {mix_cfg['outro_swell_sec']:.0f}s + LUFS...",
                72,
            )
            audio_path = master_audio_one_pass(
                audio_path,
                director,
                mastered,
                bgm_track="" if user_wants_muted else (bgm_track or ""),
                bgm_volume=req.bgm_volume if req.bgm_volume is not None else 0.12,
                allow_bgm=not user_wants_muted,
                duck_attack_ms=mix_cfg["duck_attack_ms"],
                duck_release_ms=mix_cfg["duck_release_ms"],
                intro_blast=mix_cfg["intro_blast"],
                outro_swell_sec=mix_cfg["outro_swell_sec"],
            )
            # Whoosh+Ding intro shifts timings by 0.2s if applied
            if director.effect_manifest.get("item_112_whoosh_ding", False) and timings:
                for wt in timings:
                    wt["offset"] = wt.get("offset", 0.0) + 0.2
            if audio_path and os.path.isfile(audio_path):
                sm.mark_done(
                    PipelineStage.STAGE_7_AUDIO_MASTERING,
                    artifacts={"audio_path": audio_path, "timings": timings},
                    files=[audio_path],
                )

        # ─── 6) SEO ───────────────────────────────────────────────────────
        from viral_seo_agent import generate_viral_seo_metadata
        _log("[Director] Viral SEO meta üretiliyor...", 74)
        retention_meta = (plan or {}).get("retention_metadata") if isinstance(plan, dict) else None
        try:
            from visuals.fetch import get_job_manifest
            visual_manifest = get_job_manifest()
        except Exception:
            visual_manifest = []
        script_text = ""
        if isinstance(plan, dict):
            script_text = plan.get("full_narration") or plan.get("script") or ""
            if not script_text and plan.get("scenes"):
                script_text = " ".join([
                    str(s.get("narration", ""))
                    for s in plan.get("scenes", [])
                    if isinstance(s, dict) and s.get("narration")
                ])

        seo_meta = generate_viral_seo_metadata(
            keyword,
            source_name=locked_niche,
            retention_metadata=retention_meta,
            visual_manifest=visual_manifest,
            script_context=script_text,
            niche=locked_niche,
            lang=target_lang,
        )
        seo_file = os.path.join(output_root, f"{safe}_seo.json")
        try:
            with open(seo_file, "w", encoding="utf-8") as sf:
                json.dump(seo_meta, sf, ensure_ascii=False, indent=2)
            _log(f"[Director] SEO hazır: {seo_meta.get('seo_title', keyword)}")
        except Exception as se:
            print(f"  [SEO] Notice: {se}")

        if getattr(req, "resolution", None) in ("1080p", "720p", "540p"):
            res_mode = req.resolution
            config.RENDER_RESOLUTION_MODE = res_mode
            res_dims = config.RESOLUTIONS.get(res_mode, (1080, 1920))
            _log(f"[FFmpegGraph] Çözünürlük: {res_mode} ({res_dims[0]}x{res_dims[1]})")
        else:
            config.RENDER_RESOLUTION_MODE = "1080p"
            _log("[FFmpegGraph] Çözünürlük: 1080p (1080x1920) — final varsayılan")

        sub_opts = {}
        sm.transition_to(PipelineStage.STAGE_8_SUBTITLE_COMPILE, "Kinetik Altyazı Derleme: Vektörel ASS şablonu ve kelime zıplamaları", pct=76.0)
        preset_locked = bool(req.subtitle_preset and req.subtitle_preset in SUBTITLE_PRESETS)
        if preset_locked:
            sub_opts = merge_studio_subtitle_opts(
                req.subtitle_preset,
                font_size=req.subtitle_font_size,
                y_position=req.subtitle_y_position,
                color=req.subtitle_color,
                highlight_color=req.subtitle_highlight_color,
            )
        elif not req.subtitle_color and not req.subtitle_highlight_color:
            ab_opts = resolve_ab_subtitle_preset(final_variation_attempt, keyword)
            if ab_opts:
                sub_opts.update({k: v for k, v in ab_opts.items() if k != "ab_test_variant"})
            else:
                from subtitle_generator import get_niche_subtitle_preset
                sub_opts.update(get_niche_subtitle_preset(niche))
            sub_opts = merge_studio_subtitle_opts(
                "",
                base=sub_opts,
                font_size=req.subtitle_font_size,
                y_position=req.subtitle_y_position,
            )
        else:
            sub_opts = merge_studio_subtitle_opts(
                "",
                font_size=req.subtitle_font_size,
                y_position=req.subtitle_y_position,
                color=req.subtitle_color,
                highlight_color=req.subtitle_highlight_color,
            )
        if getattr(req, "language", None):
            sub_opts["language"] = req.language
        if getattr(req, "whisper_align", None) is None:
            sub_opts["whisper_align"] = bool(getattr(config, "WHISPER_ALIGN", False))
        else:
            sub_opts["whisper_align"] = bool(req.whisper_align)

        # Extract bilingual Arabic / citation overlays for spiritual/hadith niches
        arabic_overlays = []
        scenes_source = (director.scenes if director else (plan or {}).get("scenes") or [])
        running_cursor = 0.0
        for i, sc in enumerate(scenes_source):
            if isinstance(sc, dict):
                ar = sc.get("arabic_text")
                cit = sc.get("source_citation")
                raw_t0 = sc.get("t0")
                raw_t1 = sc.get("t1")
                dur = float(sc.get("duration", 3.0))
            else:
                ar = getattr(sc, "arabic_text", None)
                cit = getattr(sc, "source_citation", None)
                raw_t0 = getattr(sc, "t0", None)
                raw_t1 = getattr(sc, "t1", None)
                dur = float(getattr(sc, "duration", 3.0))

            if raw_t0 is not None and (float(raw_t0) > 0.0 or (i == 0 and raw_t1 and float(raw_t1) > 0.0)):
                sc_t0 = float(raw_t0)
                sc_t1 = float(raw_t1) if raw_t1 is not None else (sc_t0 + dur)
                running_cursor = sc_t1
            else:
                sc_t0 = running_cursor
                sc_t1 = running_cursor + dur
                running_cursor += dur

            if ar or cit:
                arabic_overlays.append({
                    "scene_index": i,
                    "arabic_text": ar,
                    "source_citation": cit,
                    "start": sc_t0,
                    "end": sc_t1,
                })
        if arabic_overlays:
            sub_opts["arabic_overlays"] = arabic_overlays
            if req.subtitle_y_position is None:
                sub_opts["y_position"] = 0.56
                sub_opts["allow_mid_frame"] = True

        # Human-craft karaoke mid-frame overrides (Discover: captions readable on mute)
        human_craft = (plan or {}).get("human_craft") if isinstance(plan, dict) else None
        try:
            from craft import subtitle_opts_from_craft
            craft_subs = subtitle_opts_from_craft(human_craft)
            if craft_subs:
                # Lab preset + sliders stay. Craft may set chunk size only.
                sub_opts = merge_studio_subtitle_opts(
                    req.subtitle_preset if preset_locked else "",
                    base=sub_opts,
                    font_size=req.subtitle_font_size,
                    y_position=req.subtitle_y_position,
                    craft_opts=craft_subs,
                )
        except Exception:
            pass

        def on_compose_progress(pct, step_text="", *args, **kwargs):
            msg = step_text or kwargs.get("message") or kwargs.get("step") or ""
            sm.update_progress(pct, str(msg))

        # ─── 7) Render (FFmpeg graph → MoviePy fallback) ───────────────────
        check_cancelled()
        sm.transition_to(PipelineStage.STAGE_9_FFMPEG_RENDER, "FFmpeg FilterComplex Render: Tek geçişte birleştirme ve donanım hızlandırma", pct=83.0)
        _log("[FFmpegGraph] Montaj başlıyor (Madde 418)...", 78)
        output_file = os.path.join(output_root, f"{safe}.mp4")

        # Section 2.2.14 / Chapter 28.16: Gameplay / Split-screen resolution
        is_split = bool(getattr(req, "split_screen", False) or plan.get("hybrid_split_screen") or (director and getattr(director, "niche_id", None) == "11_reddit_stories") or req.niche == "11_reddit_stories")
        gameplay_cat = getattr(req, "gameplay_category", "auto") or "auto"
        gameplay_path = None
        if is_split:
            try:
                from services.gameplay_background_manager import GLOBAL_BACKGROUND_MANAGER
                total_duration = max(10.0, float(locals().get("audio_dur") or 0.0) or sum(float(c.get("duration", 3.0)) for c in clips))
                gameplay_path = GLOBAL_BACKGROUND_MANAGER.get_gameplay_clip(
                    project_dir=proj,
                    category=gameplay_cat,
                    niche=director.niche_id if director else req.niche,
                    target_duration=total_duration,
                    cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
                )
                if gameplay_path:
                    _log(f"[SplitScreen] Oynanış videosu bağlandı: {os.path.basename(gameplay_path)} ({gameplay_cat})", 80)
            except Exception as gp_err:
                _log(f"[SplitScreen] Oynanış paneli hazırlanamadı: {gp_err}", 80)
                gameplay_path = None

        # Reddit Post Card Overlay for AskReddit/Story niches
        reddit_card_path = None
        enable_rcard = bool(getattr(req, "enable_reddit_card", False))
        if not enable_rcard and (req.niche == "11_reddit_stories" or (director and getattr(director, "niche_id", None) == "11_reddit_stories") or getattr(req, "reddit_post", None)):
            enable_rcard = True
        if enable_rcard:
            try:
                from reddit_card_renderer import generate_transparent_reddit_card_png
                rcard_title = keyword
                if getattr(req, "reddit_post", None) and isinstance(req.reddit_post, dict):
                    rcard_title = req.reddit_post.get("title") or keyword
                reddit_card_path = generate_transparent_reddit_card_png(
                    title=rcard_title,
                    subreddit="AskReddit" if req.niche == "11_reddit_stories" else "ShortsStories",
                    output_path=os.path.join(output_root, f"{safe}_reddit_card.png"),
                )
                _log("[RedditCard] Soru kartı PNG overlay oluşturuldu.", 80)
            except Exception as rcard_err:
                _log(f"[RedditCard] Soru kartı oluşturulamadı: {rcard_err}", 80)
                reddit_card_path = None

        # Use final narration after timeline/length repairs; metadata stays separate.
        from effects.hook_card import first_scene_hook
        hook_scenes = director.scenes if director else plan.get("scenes", [])
        if sub_opts is None:
            sub_opts = {}
        sub_opts["hook_card_text"] = first_scene_hook(hook_scenes, getattr(req, "hook_text", None))
        sub_opts["disable_hook_card"] = not getattr(req, "enable_hook_card", True)

        # Section 33.3 P6: Secondary emphasis overlay layer
        emp_ass_path = None
        if getattr(req, "enable_emphasis_card", False):
            try:
                from subtitle_generator import create_emphasis_overlay_ass
                tw, th = getattr(config, "get_target_resolution", lambda: (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))()
                emp_candidate_path = os.path.join(output_root, f"{safe}_emphasis.ass")
                emp_ass_path = create_emphasis_overlay_ass(timings, emp_candidate_path, target_w=tw, target_h=th)
            except Exception as emp_err:
                _log(f"[Emphasis] Vurgu katmanı oluşturulamadı: {emp_err}", 80)
                emp_ass_path = None

        compose_kwargs = dict(
            title=keyword,
            bgm_track="" if (director or user_wants_muted) else (bgm_track or req.bgm_track),
            bgm_volume=req.bgm_volume,
            subtitle_opts=sub_opts,
            progress_callback=on_compose_progress,
            cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
            split_screen=bool(is_split and gameplay_path),
            anti_duplicate=getattr(req, "anti_duplicate", True),
            watermark_path=getattr(req, "watermark_path", None),
            enable_ken_burns=getattr(req, "enable_ken_burns", True),
            enable_zoompan=bool(getattr(req, "enable_zoompan", False)),
            enable_broll=bool(getattr(req, "enable_broll_insert", False)),
            enable_broll_insert=bool(getattr(req, "enable_broll_insert", False)),
            enable_face_center=bool(getattr(req, "enable_face_center", False)),
            enable_emphasis_card=bool(getattr(req, "enable_emphasis_card", False) and emp_ass_path),
            emphasis_ass_path=emp_ass_path,
            gameplay_path=gameplay_path,
            enable_reddit_card=bool(enable_rcard and reddit_card_path),
            reddit_card_path=reddit_card_path,
            niche_id=(director.niche_id if director else getattr(req, "niche", "")),
            retention_metadata=(plan or {}).get("retention_metadata") if isinstance(plan, dict) else None,
            hybrid_niche=(plan or {}).get("hybrid_niche", "") if isinstance(plan, dict) else "",
            hybrid_render_overlay=(plan or {}).get("hybrid_render_overlay") if isinstance(plan, dict) else None,
            enable_native_hybrid=True,
            human_craft=human_craft,
            enable_audio_visualizer=bool(getattr(req, "enable_audio_visualizer", False)),
            audio_visualizer_mode=getattr(req, "audio_visualizer_mode", "line") or "line",
            audio_visualizer_color=getattr(req, "audio_visualizer_color", "0x00D7FF") or "0x00D7FF",
            enable_news_ticker=bool(getattr(req, "enable_news_ticker", False)),
            news_ticker_text=getattr(req, "news_ticker_text", None),
        )

        from render.ffmpeg_graph import compose_via_director

        # Guard: Align clips with director.scenes and recover disk paths if missing
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
                            import glob
                            _cands = sorted(glob.glob(os.path.join(proj, f"s{_idx:03d}_*.mp4")))
                            if _cands and os.path.exists(_cands[0]):
                                c["path"] = _cands[0]
                                _sc.path = _cands[0]

        prev_sfx = getattr(config, "ENABLE_SFX", True)
        prev_bgm = getattr(config, "ENABLE_BGM", True)
        if director or user_wants_muted:
            config.ENABLE_SFX = False if director else prev_sfx
            config.ENABLE_BGM = False
        try:
            result = compose_via_director(
                clips, audio_path, timings, output_file,
                audio_premastered=bool(director),
                **compose_kwargs,
            )
        finally:
            config.ENABLE_SFX = prev_sfx
            config.ENABLE_BGM = prev_bgm

        # ─── 8) Post quality gate ─────────────────────────────────────────
        pre_result = locals().get("pre") or {}
        if result and os.path.exists(result) and os.path.getsize(result) > 100000:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            validation = subprocess.run(
                [ffmpeg_exe, "-v", "error", "-i", result, "-f", "null", "-"],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30,
            )
            if validation.returncode != 0:
                raise RuntimeError(
                    "Render çıktısı çözümlenemedi: "
                    + validation.stderr.decode("utf-8", errors="ignore")[:300]
                )

            # ─── Post-render pipeline audit ───────────────────────────────
            try:
                from render.pipeline_audit import post_render_audit
                _post_audit = post_render_audit(result, audio_path, clips)
                for _pw in _post_audit.get("warnings") or []:
                    _log(f"[PipelineAudit] Post-WARN: {_pw}")
                for _pe in _post_audit.get("errors") or []:
                    _log(f"[PipelineAudit] Post-ERROR: {_pe}", 97)
                with open(os.path.join(proj, "pipeline_audit_post.json"), "w", encoding="utf-8") as _paf:
                    json.dump(_post_audit, _paf, ensure_ascii=False, indent=2)
                if not _post_audit["ok"]:
                    _post_blocking = [e for e in (_post_audit.get("errors") or [])
                                      if "av_sync_error" in e or "video_too_short" in e
                                      or "no_video_stream" in e or "output_too_small" in e]
                    if _post_blocking:
                        _msg = f"Post-render audit kalite kapısı: {'; '.join(_post_blocking)}"
                        _log(f"[PipelineAudit] HARD-FAIL: {_msg}", 97)
                        if db_id:
                            database.update_video_status(db_id, "failed", error_message=_msg)
                        state.broadcast_event("error", _msg)
                        return
            except Exception as _post_audit_err:
                _log(f"[PipelineAudit] post-audit skip: {_post_audit_err}")

            # Chapter 28.14 / MoneyPrinterV2: MP4 Preflight Integrity Check
            try:
                from services.video_preflight import verify_mp4_integrity
                preflight = verify_mp4_integrity(result, min_duration=3.0, max_duration=70.0)
                if not preflight.get("valid", False):
                    pf_errs = preflight.get("errors", [])
                    msg = f"MP4 Preflight Bütünlük Hatası: {'; '.join(pf_errs)}"
                    _log(f"[VideoPreflight] HARD-FAIL: {msg}", 97)
                    if db_id:
                        database.update_video_status(db_id, "failed", error_message=msg)
                    state.broadcast_event("error", msg)
                    return
                _log(f"[VideoPreflight] Doğrulandı: {preflight.get('width')}x{preflight.get('height')} @ {preflight.get('duration')}s (Ses: {preflight.get('has_audio')})", 96)
            except Exception as pf_exc:
                _log(f"[VideoPreflight] Preflight istisnası: {pf_exc}")

            if director:
                post = post_render_score(director, result, audio_path=audio_path)
                _log(
                    f"[QualityGate] Post-score={post['score']} ok={post.get('ok')} "
                    f"Dav={post.get('av_delta')} issues={post.get('issues')}",
                    97,
                )
                with open(os.path.join(proj, "quality_gate.json"), "w", encoding="utf-8") as qf:
                    json.dump({"pre": pre_result, "post": post}, qf, ensure_ascii=False, indent=2)
                with open(os.path.join(proj, "render_verification.json"), "w", encoding="utf-8") as vf:
                    json.dump(
                        {
                            "video_path": result,
                            "audio_path": audio_path,
                            "verified": bool(post.get("ok")),
                            "video_duration": post.get("video_duration"),
                            "audio_duration": post.get("audio_duration"),
                            "av_delta": post.get("av_delta"),
                            "issues": post.get("issues") or [],
                        },
                        vf,
                        ensure_ascii=False,
                        indent=2,
                    )
                # Persist final director paths after render
                with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                    json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)

                if not post.get("ok"):
                    issues = post.get("issues") or []
                    msg = (
                        f"Kalite kapısı reddetti (Madde 494): {', '.join(issues)}. "
                        f"Süre={post.get('video_duration')}s — yayınlanamaz."
                    )
                    _log(f"[QualityGate] HARD-FAIL: {msg}")
                    if db_id:
                        database.update_video_status(db_id, "failed", error_message=msg)
                    state.broadcast_event("error", msg)
                    return

            size_mb = round(os.path.getsize(result) / (1024 * 1024), 2)
            total_dur = sum(c["duration"] for c in clips)

            # File-only delivery contract: policy snapshot, AI disclosure,
            # quality report, manual checklist and output checksum are written
            # before the job is marked completed.
            sm.transition_to(PipelineStage.STAGE_10_PACKAGING, "Paketleme ve Dağıtım: Lisans künyesi, SEO künyesi ve telemetri arşivleniyor", pct=96.0)
            try:
                from production.package import write_delivery_package
                from production.quality import validate_script_quality
                package_quality = ((plan.get("meta") or {}).get("script_quality")
                                   if isinstance(plan, dict) else None)
                if not package_quality:
                    package_quality = validate_script_quality(plan or {})
                manifest_payload = None
                manifest_path = os.path.join(proj, "source_manifest.json")
                if os.path.isfile(manifest_path):
                    with open(manifest_path, "r", encoding="utf-8") as mf:
                        manifest_payload = json.load(mf)
                package_paths = write_delivery_package(
                    proj,
                    plan=plan if isinstance(plan, dict) else {},
                    output_path=result,
                    quality_report=package_quality,
                    source_manifest=manifest_payload,
                    seo=seo_meta if isinstance(seo_meta, dict) else {},
                )
                _log(
                    f"[Package] Dosya teslim paketi hazır: {', '.join(sorted(package_paths))}",
                    98,
                )
            except Exception as package_err:
                msg = f"Teslim paketi oluşturulamadı: {package_err}"
                _log(f"[Package] HARD-FAIL: {msg}", 98)
                if db_id:
                    database.update_video_status(db_id, "failed", error_message=msg)
                state.broadcast_event("error", msg)
                return

            proof_filename = f"{os.path.splitext(os.path.basename(result))[0]}_proof.json"
            proof_full_path = os.path.join(config.BASE_DIR, "proofs", proof_filename)
            proof_url = f"/proofs/{proof_filename}" if os.path.exists(proof_full_path) else None

            # High-CTR Thumbnail Generation (Verticals v3 Adaptation)
            thumb_path = os.path.join(output_root, f"{safe}_thumb.jpg")
            thumb_169_path = os.path.join(output_root, f"{safe}_thumb_16x9.jpg")
            try:
                from services.thumbnail_generator import generate_thumbnail, extract_best_video_frame
                _log("[Thumbnail] High-CTR kapak görseli hazırlanıyor (Verticals v3)...", 99)
                raw_frame = os.path.join(proj, "raw_thumb_frame.jpg")
                got_frame = extract_best_video_frame(result, raw_frame, timestamp_sec=min(3.0, total_dur * 0.25))
                bg_src = raw_frame if got_frame else None
                generate_thumbnail(
                    title=seo_meta.get("seo_title", keyword),
                    output_path=thumb_path,
                    background_path=bg_src,
                    aspect_ratio="9:16",
                )
                generate_thumbnail(
                    title=seo_meta.get("seo_title", keyword),
                    output_path=thumb_169_path,
                    background_path=bg_src,
                    aspect_ratio="16:9",
                )
                _log(f"[Thumbnail] 9:16 ve 16:9 kapak hazır: {os.path.basename(thumb_path)}")
            except Exception as thumb_err:
                _log(f"[Thumbnail] Kapak üretim uyarısı: {thumb_err}")

            if db_id:
                database.update_video_status(
                    db_id, "completed", os.path.basename(result), total_dur, size_mb,
                    seo_json=json.dumps(seo_meta, ensure_ascii=False),
                    proof_path=proof_full_path if os.path.exists(proof_full_path) else None,
                )

            # Manual upload info & guide package (Items 354-410, gallery modal support)
            try:
                manual_pkg = {
                    "video_file": os.path.basename(result),
                    "title": seo_meta.get("seo_title") or plan.get("title") or keyword,
                    "description": (
                        seo_meta.get("seo_description")
                        or seo_meta.get("description")
                        or f"{keyword} #shorts\n\n📌 Kaynak & Araştırma: Bağımsız Eğitici İnceleme\n⚖️ Hakkaniyet & Katma Değer (Fair Use): Bu video eğitim ve analiz amacıyla özgün ses ve dinamik görselleştirme ile üretilmiştir."
                    ),
                    "tags": seo_meta.get("tags") or ["shorts", "bilgi", "viral", "trend"],
                    "pinned_comment": seo_meta.get("pinned_comment") or "Sizce bu konudaki en şaşırtıcı detay neydi? Yorumlarda buluşalım! 👇",
                    "rule_80_altered_synthetic": "HAYIR (Yüz klonlama veya manipülasyon yoksa etiket seçilmemeli)",
                    "rule_83_source_reference": "Açıklamaya araştırma ve kaynak referansı eklendi.",
                    "anti_detect_ready": True,
                    "size_mb": size_mb,
                    "duration": total_dur,
                }
                info_json_targets = {result.rsplit(".", 1)[0] + "_manual_upload_info.json"}
                info_json_targets.add(os.path.join(config.OUTPUT_DIR, f"{safe}_manual_upload_info.json"))
                for target_json in info_json_targets:
                    with open(target_json, "w", encoding="utf-8") as fj:
                        json.dump(manual_pkg, fj, ensure_ascii=False, indent=2)

                guide_txt_path = result.rsplit(".", 1)[0] + "_manual_upload_guide.txt"
                with open(guide_txt_path, "w", encoding="utf-8") as ft:
                    ft.write(
                        f"=== YOUTUBE SHORTS MANUEL YÜKLEME REHBERİ ===\n\n"
                        f"📌 VİDEO BAŞLIĞI:\n{manual_pkg['title']}\n\n"
                        f"📌 VİDEO AÇIKLAMASI:\n{manual_pkg['description']}\n\n"
                        f"📌 VİDEO ETİKETLERİ:\n{', '.join(manual_pkg['tags'])}\n\n"
                        f"📌 İLK YORUM (Sabitleyin):\n{manual_pkg['pinned_comment']}\n\n"
                        f"🎬 DOSYA:\n{os.path.basename(result)} ({size_mb} MB, {total_dur:.1f}s)\n"
                    )
            except Exception as e_info:
                _log(f"[Package] Manual upload info oluşturulamadı: {e_info}")

            # Item 120: Senaryoyu intihal DB'sine YALNIZCA başarılı render tamamlanınca ekle
            try:
                from plagiarism_checker import add_script_to_db
                add_script_to_db(
                    plan.get("full_narration", ""),
                    keyword=keyword,
                    title=plan.get("title", keyword),
                    video_id=db_id,
                    render_status="completed",
                    channel_slug=ch_paths["slug"],
                )
            except Exception as e:
                _log(f"[Item 120] DB kayıt uyarısı: {e}")

            committed = commit_published_stock_ids()
            if committed:
                _log(f"[Visual] {committed} stok ID yayın sonrası kalıcı havuza eklendi (P1-12)")

            final_video_url = (
                f"/output/channels/{ch_paths['slug']}/{os.path.basename(result)}"
                if ch_paths["slug"] != "default"
                else f"/output/{os.path.basename(result)}"
            )
            sm.save_telemetry(proj)
            sm.complete(final_video_url)

            done_msg = (
                f"🎉 Video üretimi tamamlandı! Dosya: {os.path.basename(result)} "
                f"({size_mb} MB, {total_dur:.1f}s)"
            )
            print(done_msg)
            state.broadcast_event("progress", {"percent": 100, "step": "Video başarıyla tamamlandı!"})
            state.broadcast_event("complete", {
                "video_id": db_id,
                "project_slug": safe,
                "keyword": keyword,
                "filename": os.path.basename(result),
                "url": final_video_url,
                "thumb_url": (
                    (
                        f"/output/channels/{ch_paths['slug']}/{safe}_thumb.jpg"
                        if ch_paths["slug"] != "default"
                        else f"/output/{safe}_thumb.jpg"
                    )
                    if os.path.exists(os.path.join(output_root, f"{safe}_thumb.jpg"))
                    else None
                ),
                "channel_slug": ch_paths["slug"],
                "seo": seo_meta,
                "proof_url": proof_url,
                "quality_gate": {
                    "pre": pre_result,
                    "post": locals().get("post") or {},
                },
                "director": {
                    "niche_id": director.niche_id if director else req.niche,
                    "duration": total_dur,
                    "scenes": len(clips),
                },
            })
            notify_video_ready(keyword, f"/output/{os.path.basename(result)}", total_dur)
        else:
            sm.fail("Video birleştirme MoviePy/FFmpeg hatası nedeniyle tamamlanamadı.")
            sm.save_telemetry(proj)
            if db_id:
                database.update_video_status(
                    db_id, "failed",
                    error_message="Video birleştirme MoviePy/FFmpeg hatası nedeniyle tamamlanamadı.",
                )
            state.broadcast_event("error", "Video birleştirme tamamlanamadı.")
            notify_render_error(keyword, "Video birleştirme MoviePy/FFmpeg hatası nedeniyle tamamlanamadı.")

    except (InterruptedError, asyncio.CancelledError):
        sm.fail("Kullanıcı tarafından iptal edildi.")
        sm.save_telemetry(locals().get("proj") or "")
        discard_job_stock_ids()
        cancel_msg = "⛔ Video üretimi kullanıcı tarafından iptal edildi."
        print(cancel_msg)
        state.broadcast_event("progress", {"percent": 0, "step": "İşlem İptal Edildi"})
        state.broadcast_event("error", cancel_msg)
        if db_id:
            database.update_video_status(db_id, "cancelled", error_message="Kullanıcı tarafından iptal edildi.")
    except Exception as e:
        sm.fail(str(e))
        sm.save_telemetry(locals().get("proj") or "")
        discard_job_stock_ids()
        if db_id:
            database.update_video_status(db_id, "failed", error_message=str(e))
        state.broadcast_event("error", f"İşlem hatası: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        traceback.print_exc()
        notify_render_error(keyword, str(e), log_snippet=tb[-600:])
    finally:
        if slot_acquired and gate_context is not None:
            try:
                gate_context.__exit__(None, None, None)
            except Exception:
                pass
        try:
            _sweep_render_temp_files(render_job_prefix)
        except Exception:
            pass
        state.current_render_state["cancel_requested"] = False
        state.current_render_state["cancel_notified"] = False
        state.current_render_state["is_rendering"] = False
        state.is_rendering_active = False
        config.LANGUAGE = orig_lang
        config.TTS_VOICE = orig_voice
        config.TTS_RATE = orig_rate
        config.TTS_SACRED_CALM = orig_sacred
        sys.stdout = old_stdout


def process_batch_queue():
    while True:
        job = batch_manager.take_next_job()
        if not job:
            return
        with state.render_lock:
            if state.is_rendering_active:
                batch_manager.finish_current_job("queued")
                return
            state.is_rendering_active = True
        process_video_task(VideoRenderRequest(
            keyword=job["topic"],
            niche=job["niche"],
            language=job["language"],
            split_screen=job.get("split_screen", False),
            anti_duplicate=True,
            enable_ken_burns=True,
        ))
        batch_manager.finish_current_job(
            "cancelled" if state.current_render_state.get("cancel_requested") else "completed"
        )
