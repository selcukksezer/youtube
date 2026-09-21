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
from subtitle_generator import SUBTITLE_PRESETS, resolve_ab_subtitle_preset
from batch_processor import batch_manager
from notifications import notify_video_ready, notify_render_error
from . import state


def _log(msg, pct=None):
    print(msg, flush=True)
    state.broadcast_event("log", msg)
    if pct is not None:
        state.broadcast_event("progress", {"percent": pct, "step": msg})


def _gemini_image_circuit_open() -> bool:
    """P1-17: true when Gemini image quota tripped — force stock-only regen."""
    try:
        from system_resilience import circuit_breaker
        return not circuit_breaker.can_execute("gemini_image")
    except Exception:
        return False


def _veo_circuit_open() -> bool:
    """P3-31: true when Veo quota tripped — skip AI video, fall back to stock."""
    try:
        from system_resilience import circuit_breaker
        return not circuit_breaker.can_execute("gemini_veo")
    except Exception:
        return False


def _ensure_ui_plan_narration_usable(plan, keyword: str, locked_niche: str, target_lang: str):
    """Batch C — UI-supplied plan must pass narration gate or get procedural inject."""
    if not plan or not plan.get("scenes"):
        return plan
    try:
        from scenes.narration_validate import plan_narration_usable
        from scenes.fallback import _generate_procedural_fallback_scenes

        if plan_narration_usable(plan.get("scenes") or []):
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
    """P3-35: post-render sweep of ffgraph temp dirs and job intermediate WAVs."""
    import shutil
    import tempfile

    try:
        tmp_root = tempfile.gettempdir()
        for name in os.listdir(tmp_root):
            if name.startswith("ffgraph_"):
                path = os.path.join(tmp_root, name)
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

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


def _fetch_single_scene_visual(i, scene, plan, proj, total_s, gameplay_path=None):
    """Sync fetch for one scene — used from parallel executor (P1-13)."""
    q = scene.get("search_queries", [scene.get("search_query", "nature")])
    d = scene.get("duration", 7)
    desc = scene.get("scene_description", "")
    intent = scene.get("visual_intent") or {}
    narr = scene.get("narration", "")
    p = None
    gemini_circuit_open = _gemini_image_circuit_open()

    if i == 0 and plan.get("reddit_post"):
        p = generate_reddit_post_card_clip(
            plan["reddit_post"], os.path.join(proj, "s000_reddit_source.mp4"), duration=d
        )
    elif _veo_render_allowed() and i > 0 and (i % 4 == 1):
        p = generate_veo_scene_clip(
            scene_description=desc or (q[0] if q else "cinematic atmosphere"),
            output_path=os.path.join(proj, f"s{i:03d}_veo.mp4"),
            duration=d,
        )
    elif (
        not _veo_circuit_open()
        and getattr(config, "USE_GEMINI_VIDEO_GEN", False)
        and config.GEMINI_API_KEY
        and i > 0
        and (i % 4 == 1)
        and not getattr(config, "GEMINI_VEO_PAID_QUOTA", False)
    ):
        _log("[Visual] Veo atlandi — GEMINI_VEO_PAID_QUOTA=false (ucretli kota onayi gerekli)")
    elif (
        not gemini_circuit_open
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
        not gemini_circuit_open
        and (i % 3 == 2)
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
        or (i % 3 == 2)
        or (getattr(config, "USE_GEMINI_VIDEO_GEN", False) and i > 0 and (i % 4 == 1))
    ):
        reason = "veo 429" if _veo_circuit_open() else "gemini_image 429"
        _log(f"[Visual] Sahne {i + 1}/{total_s}: {reason} devre acik — zorunlu stok regen")

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
        )

    clip_entry = {
        "path": p,
        "duration": d,
        "narration": narr,
        "scene_description": desc,
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
        "t0": scene.get("t0", 0),
        "t1": scene.get("t1", 0),
    }
    return i, clip_entry, p


async def _fetch_scenes_parallel(scenes, plan, proj, total_s, gameplay_path=None):
    """P1-13: asyncio.gather per-scene stock fetch via thread pool."""
    loop = asyncio.get_running_loop()

    async def _one(i, scene):
        return await loop.run_in_executor(
            None,
            lambda i=i, scene=scene: _fetch_single_scene_visual(
                i, scene, plan, proj, total_s, gameplay_path=gameplay_path
            ),
        )

    return await asyncio.gather(*(_one(i, scene) for i, scene in enumerate(scenes)))


def process_video_task(req: VideoRenderRequest):
    old_stdout = sys.stdout
    sys.stdout = state.SSELogStreamer(old_stdout)
    db_id = None
    render_job_prefix = ""
    orig_lang = config.LANGUAGE
    orig_voice = config.TTS_VOICE
    orig_rate = config.TTS_RATE
    script_regen_494 = False

    def check_cancelled():
        if state.current_render_state.get("cancel_requested"):
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    try:
        state.current_render_state["cancel_requested"] = False
        state.current_render_state["cancel_notified"] = False

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
        _log(f"[Director] İşlem başlatılıyor: '{keyword}'...", 5)
        if locked_niche != requested_niche:
            _log(
                f"[Niche] Konu kilidi: '{requested_niche}' -> '{locked_niche}' "
                f"(baslik: {keyword[:48]})",
                6,
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
        reset_used_videos()
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
                )
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

            plan = ensure_retention_hooks_on_plan(
                plan,
                keyword,
                lang=target_lang,
                niche_type=locked_niche,
                variation_attempt=orig_attempt,
            )
            try:
                from scenes.enrichment import enrich_plan_scenes
                plan = enrich_plan_scenes(plan, lang=target_lang)
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

            is_original, similarity, matched_title = check_script_originality(
                plan.get("full_narration", ""),
                keyword=keyword,
                title=plan.get("title", keyword),
            )
            if is_original:
                break
            plan = None

        if not is_original:
            message = (
                f"Senaryo benzerlik eşiğini aştı (%{similarity * 100:.1f}); "
                f"en yakın kayıt: {matched_title or 'bilinmiyor'}."
            )
            if db_id:
                database.update_video_status(db_id, "failed", error_message=message)
            state.broadcast_event("error", message)
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

        # ─── 3) Acquire visuals ───────────────────────────────────────────
        check_cancelled()
        scenes = plan.get("scenes", [])
        total_s = len(scenes)
        _log(f"[Visual] Stok videolar aranıyor ({total_s} sahne, semantik skor)...", 30)

        clips = []
        gameplay_path = None
        recent_texts = []
        retention_meta = (plan or {}).get("retention_metadata") or {}
        needs_split_screen = (
            getattr(req, "split_screen", False)
            or bool(plan.get("hybrid_split_screen"))
            or bool(retention_meta.get("dopamin_split_screen"))
        )
        if needs_split_screen:
            req.split_screen = True
        if req.split_screen:
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
        _log(f"[Visual] Paralel stok fetch başlıyor ({total_s} sahne, asyncio.gather)...", 32)
        fetch_results = asyncio.run(
            _fetch_scenes_parallel(scenes, plan, proj, total_s, gameplay_path=gameplay_path)
        )
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
                    + (f" ... (+{len(missing) - 16})" if len(missing) > 16 else ""),
                    56,
                )
                for i in missing:
                    check_cancelled()
                    scene = scenes[i]
                    intent = scene.get("visual_intent") or {}
                    q = (
                        intent.get("search_queries")
                        or scene.get("search_queries")
                        or scene.get("search_query")
                        or ["cinematic atmosphere"]
                    )
                    if isinstance(q, str):
                        q = [q]
                    p = fetch_scene_clip(
                        q, i, proj, target_duration=clips[i]["duration"],
                        scene_description=scene.get("scene_description", ""),
                        narration=scene.get("narration", ""),
                        visual_intent=intent,
                        cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
                        recent_texts=recent_texts,
                    )
                    clips[i]["path"] = p
                    if p:
                        recent_texts.append(os.path.basename(p).lower())
                        if director and i < len(director.scenes):
                            director.scenes[i].path = p
                    else:
                        _log(f"[Visual] Retry pass {attempt}: scene {i + 1}/{total_s} still failed")

        check_cancelled()
        _retry_missing_clips(max_passes=2)

        coverage = clip_coverage_report(clips)
        ok_clips = coverage["ok"]
        _log(f"[Visual] Stok klip indirme tamamlandi: {ok_clips}/{total_s}", 58)

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
        _log(f"[Timeline] {lang_title} Seslendirme ({active_tts_provider()})...", 62)
        audio_path = os.path.join(config.AUDIO_DIR, f"{safe}.wav")

        from voice_humanizer import VoiceHumanizer
        niche_for_voice = (director.niche_id if director else req.niche)
        asmr_profile = VoiceHumanizer.get_asmr_voice_settings(niche_for_voice, keyword)
        narration_text = plan.get("full_narration") or ""

        # Post-compile narration gate — auto-repair once, then hard block
        if director:
            from director.quality_gate import check_narration_integrity
            from director import pre_render_score as _pre_render_score
            from scenes.narration_validate import apply_auto_repair_if_needed

            tts_plan, tts_fixes, _ = apply_auto_repair_if_needed(director.to_legacy_plan())
            if tts_fixes:
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

        _, timings = generate_narration_with_timing(narration_text, audio_path, voice_profile=asmr_profile)
        _log(f"[Timeline] TTS tamamlandı — {len(timings)} kelime zamanlaması", 68)

        if director:
            fitted = os.path.join(config.AUDIO_DIR, f"{safe}_fitted.wav")
            try:
                audio_path, timings, audio_dur, speed = fit_tts_to_timeline(
                    audio_path, director, word_timings=timings, output_path=fitted
                )
            except RuntimeError as fit_err:
                if "494" not in str(fit_err):
                    raise
                # No chipmunk/fragment recovery — regen script once or hard-fail
                if not script_regen_494:
                    script_regen_494 = True
                    _log(f"[Timeline] {fit_err} — senaryo bir kez yeniden üretiliyor...", 69)
                    new_plan = generate_scenes(keyword, niche_type=locked_niche, language=target_lang)
                    new_director = compile_director_plan(
                        new_plan,
                        title=keyword,
                        niche_id=locked_niche,
                        language=target_lang,
                        reddit_post=getattr(req, "reddit_post", None),
                    )
                    regen_pre = pre_render_score(new_director)
                    regen_block = [
                        i for i in regen_pre.get("issues", [])
                        if i.startswith("fragment") or i.startswith("low_words")
                        or i.startswith("empty_narration") or i.startswith("no_terminal")
                    ]
                    if regen_block:
                        msg = (
                            f"Senaryoyu yeniden üretin: TTS süre bandına sığmıyor (Madde 494). "
                            f"Anlatım sorunları: {', '.join(regen_block)}"
                        )
                        _log(f"[QualityGate] {msg}", 69)
                        if db_id:
                            database.update_video_status(db_id, "failed", error_message=msg)
                        state.broadcast_event("error", msg)
                        return
                    director = new_director
                    plan = director.to_legacy_plan()
                    narration_text = plan.get("full_narration") or ""
                    with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
                        json.dump(plan, f, ensure_ascii=False, indent=2)
                    with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                        json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)
                    _, timings = generate_narration_with_timing(
                        narration_text, audio_path, voice_profile=asmr_profile
                    )
                    audio_path, timings, audio_dur, speed = fit_tts_to_timeline(
                        audio_path, director, word_timings=timings, output_path=fitted
                    )
                else:
                    msg = (
                        "Senaryoyu yeniden üretin: anlatım TTS süre bandına sığmıyor (Madde 494). "
                        "Timeline'dan metni kısaltın veya yeni senaryo oluşturun."
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
                f"[Timeline] Ses bütçeye kilitlendi: {audio_dur:.1f}s (speed×{speed:.2f}, tavan {director.quality_thresholds.max_audio_speed})",
                70,
            )

        # Telifsiz BGM (Pixabay / Mixkit / VoiceLab) — boş track ise otomatik
        bgm_track = req.bgm_track or ""
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

        # ─── 5) Audio master (one-pass) ────────────────────────────────────
        check_cancelled()
        _log("[AudioMaster] EQ + SFX bus + BGM + LUFS...", 72)
        mastered = os.path.join(config.AUDIO_DIR, f"{safe}_master.wav")
        if director:
            audio_path = master_audio_one_pass(
                audio_path,
                director,
                mastered,
                bgm_track=bgm_track or "",
                bgm_volume=req.bgm_volume if req.bgm_volume is not None else 0.12,
            )
            # Whoosh+Ding intro shifts timings by 0.2s if applied
            if director.effect_manifest.get("item_112_whoosh_ding", True) and timings:
                for wt in timings:
                    wt["offset"] = wt.get("offset", 0.0) + 0.2

        # ─── 6) SEO ───────────────────────────────────────────────────────
        from viral_seo_agent import generate_viral_seo_metadata
        _log("[Director] Viral SEO meta üretiliyor...", 74)
        retention_meta = (plan or {}).get("retention_metadata") if isinstance(plan, dict) else None
        seo_meta = generate_viral_seo_metadata(keyword, retention_metadata=retention_meta)
        seo_file = os.path.join(output_root, f"{safe}_seo.json")
        try:
            with open(seo_file, "w", encoding="utf-8") as sf:
                json.dump(seo_meta, sf, ensure_ascii=False, indent=2)
            _log(f"[Director] SEO hazır: {seo_meta.get('seo_title', keyword)}")
        except Exception as se:
            print(f"  [SEO] Notice: {se}")

        if getattr(req, "resolution", None) in ("1080p", "720p", "540p"):
            # Prefer 1080p for final publish; 540p/720p only when explicitly requested as test
            res_mode = req.resolution
            if res_mode != "1080p" and not getattr(req, "force_test_resolution", False):
                # Keep user's choice but warn — publishable Marcus needs 1080p
                _log(
                    f"[FFmpegGraph] Uyarı: {res_mode} test çözünürlüğü seçili. "
                    f"Yayın için 1080p önerilir.",
                    75,
                )
            config.RENDER_RESOLUTION_MODE = res_mode
            res_dims = config.RESOLUTIONS.get(res_mode, (1080, 1920))
            _log(f"[FFmpegGraph] Çözünürlük: {res_mode} ({res_dims[0]}x{res_dims[1]})")
        else:
            config.RENDER_RESOLUTION_MODE = "1080p"
            _log("[FFmpegGraph] Çözünürlük: 1080p (1080x1920) — final varsayılan")

        sub_opts = {}
        if req.subtitle_preset and req.subtitle_preset in SUBTITLE_PRESETS:
            sub_opts.update(SUBTITLE_PRESETS[req.subtitle_preset])
        elif not req.subtitle_color and not req.subtitle_highlight_color:
            ab_opts = resolve_ab_subtitle_preset(final_variation_attempt, keyword)
            if ab_opts:
                sub_opts.update({k: v for k, v in ab_opts.items() if k != "ab_test_variant"})
            else:
                sub_opts.update(SUBTITLE_PRESETS.get("high_contrast_retention", SUBTITLE_PRESETS["red_fire"]))
        if req.subtitle_color:
            sub_opts["color"] = req.subtitle_color
        if req.subtitle_highlight_color:
            sub_opts["highlight_color"] = req.subtitle_highlight_color
        if req.subtitle_font_size is not None:
            sub_opts["font_size"] = req.subtitle_font_size
        if req.subtitle_y_position is not None:
            sub_opts["y_position"] = req.subtitle_y_position

        def on_compose_progress(pct, step_text="", *args, **kwargs):
            msg = step_text or kwargs.get("message") or kwargs.get("step") or ""
            state.broadcast_event("progress", {"percent": pct, "step": str(msg)})
            state.broadcast_event("log", f"  {msg}")

        # ─── 7) Render (FFmpeg graph → MoviePy fallback) ───────────────────
        check_cancelled()
        _log("[FFmpegGraph] Montaj başlıyor (Madde 418)...", 78)
        output_file = os.path.join(output_root, f"{safe}.mp4")

        # When director masters audio, skip duplicate SFX/BGM inside compose_video
        if plan.get("hybrid_split_screen"):
            req.split_screen = True
        compose_kwargs = dict(
            title=keyword,
            bgm_track="" if director else (bgm_track or req.bgm_track),
            bgm_volume=req.bgm_volume,
            subtitle_opts=sub_opts,
            progress_callback=on_compose_progress,
            cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
            split_screen=getattr(req, "split_screen", False) or bool(plan.get("hybrid_split_screen")),
            anti_duplicate=getattr(req, "anti_duplicate", True),
            watermark_path=getattr(req, "watermark_path", None),
            enable_ken_burns=getattr(req, "enable_ken_burns", True),
            gameplay_path=gameplay_path,
            niche_id=(director.niche_id if director else getattr(req, "niche", "")),
            retention_metadata=(plan or {}).get("retention_metadata") if isinstance(plan, dict) else None,
            hybrid_niche=(plan or {}).get("hybrid_niche", "") if isinstance(plan, dict) else "",
            hybrid_render_overlay=(plan or {}).get("hybrid_render_overlay") if isinstance(plan, dict) else None,
        )

        from render.ffmpeg_graph import compose_via_director

        prev_sfx = getattr(config, "ENABLE_SFX", True)
        prev_bgm = getattr(config, "ENABLE_BGM", True)
        if director:
            config.ENABLE_SFX = False
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

            if director:
                post = post_render_score(director, result, audio_path=audio_path)
                _log(
                    f"[QualityGate] Post-score={post['score']} ok={post.get('ok')} "
                    f"Δav={post.get('av_delta')} issues={post.get('issues')}",
                    97,
                )
                with open(os.path.join(proj, "quality_gate.json"), "w", encoding="utf-8") as qf:
                    json.dump({"pre": pre_result, "post": post}, qf, ensure_ascii=False, indent=2)
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

            proof_filename = f"{os.path.splitext(os.path.basename(result))[0]}_proof.json"
            proof_full_path = os.path.join(config.BASE_DIR, "proofs", proof_filename)
            proof_url = f"/proofs/{proof_filename}" if os.path.exists(proof_full_path) else None

            if db_id:
                database.update_video_status(
                    db_id, "completed", os.path.basename(result), total_dur, size_mb,
                    seo_json=json.dumps(seo_meta, ensure_ascii=False),
                    proof_path=proof_full_path if os.path.exists(proof_full_path) else None,
                )

            committed = commit_published_stock_ids()
            if committed:
                _log(f"[Visual] {committed} stok ID yayın sonrası kalıcı havuza eklendi (P1-12)")

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
                "url": f"/output/channels/{ch_paths['slug']}/{os.path.basename(result)}"
                if ch_paths["slug"] != "default"
                else f"/output/{os.path.basename(result)}",
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
            if db_id:
                database.update_video_status(
                    db_id, "failed",
                    error_message="Video birleştirme MoviePy/FFmpeg hatası nedeniyle tamamlanamadı.",
                )
            state.broadcast_event("error", "Video birleştirme tamamlanamadı.")
            notify_render_error(keyword, "Video birleştirme MoviePy/FFmpeg hatası nedeniyle tamamlanamadı.")

    except (InterruptedError, asyncio.CancelledError):
        discard_job_stock_ids()
        cancel_msg = "⛔ Video üretimi kullanıcı tarafından iptal edildi."
        print(cancel_msg)
        state.broadcast_event("progress", {"percent": 0, "step": "İşlem İptal Edildi"})
        state.broadcast_event("error", cancel_msg)
        if db_id:
            database.update_video_status(db_id, "cancelled", error_message="Kullanıcı tarafından iptal edildi.")
    except Exception as e:
        discard_job_stock_ids()
        if db_id:
            database.update_video_status(db_id, "failed", error_message=str(e))
        state.broadcast_event("error", f"İşlem hatası: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        traceback.print_exc()
        notify_render_error(keyword, str(e), log_snippet=tb[-600:])
    finally:
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
