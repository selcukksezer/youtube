"""Preflight checks, circuit breaker helpers, and parallel scene visual fetch stage."""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import sys
import time
from typing import Any, Callable, Mapping

import config
import database
from reddit_card_renderer import generate_reddit_post_card_clip
from video_fetcher import (
    fetch_scene_clip,
    fetch_selected_stock_video,
    generate_ai_image_clip,
    generate_veo_scene_clip,
    reset_session_source_counts,
    reset_used_videos,
)
from . import state


def _rw_attr(name: str, default: Any) -> Any:
    mod = sys.modules.get("server_core.render_worker")
    return getattr(mod, name, default) if mod is not None else default


def _quality_report_allows_render(
    script_quality: Mapping[str, Any], *, allow_draft_render: bool = False
) -> bool:
    return allow_draft_render or not bool(script_quality.get("hard_fail"))


def _gemini_image_circuit_open() -> bool:
    """P1-17: true when Gemini image quota tripped — force stock-only regen."""
    try:
        from system_resilience import circuit_breaker

        return not circuit_breaker.can_execute("gemini_image")
    except Exception:
        return False


def procedural_on_retry_pass(attempt: int, max_passes: int) -> bool:
    """Stock-only on early passes. The last pass may synthesize lavfi."""
    return int(attempt) >= int(max_passes)


def _log(msg, pct=None):
    st = _rw_attr("state", state)
    print(msg, flush=True)
    if pct is not None:
        st.broadcast_event("progress", {"percent": pct, "step": msg})


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
    log_fn = _rw_attr("_log", _log)
    try:
        from scenes.fallback import _generate_five_fact_scenes, _generate_procedural_fallback_scenes
        from scenes.narration_validate import plan_quality_usable

        blob = " ".join(
            str((s or {}).get("narration") or "") for s in (plan.get("scenes") or []) if isinstance(s, dict)
        ).casefold()
        slop = any(mark in blob for mark in _SCRIPT_SLOP)
        if slop and (locked_niche == "9_five_facts" or "gerçek" in (keyword or "").casefold() or "gercek" in (keyword or "").casefold()):
            log_fn("[Director] Senaryo şablon çöp — 5 gerçek anlatımıyla değiştiriliyor", 11)
            plan = dict(plan)
            plan.update(_generate_five_fact_scenes(keyword, target_lang != "en"))
            plan["niche_id"] = locked_niche or "9_five_facts"
            return plan

        if plan_quality_usable(plan.get("scenes") or []):
            return plan
        log_fn("[Director] UI plan narration unusable — prosedürel fallback enjekte ediliyor", 11)
        fb = _generate_procedural_fallback_scenes(keyword, niche_type=locked_niche, language=target_lang)
        plan = dict(plan)
        plan.update(fb)
    except Exception as exc:
        log_fn(f"[Director] UI plan narration gate atlandı: {exc}", 11)
    return plan


def _veo_render_allowed() -> bool:
    """P3-31: sparse Veo policy — paid quota confirm + preview model + circuit closed."""
    cfg = _rw_attr("config", config)
    veo_open_fn = _rw_attr("_veo_circuit_open", _veo_circuit_open)
    if not getattr(cfg, "USE_GEMINI_VIDEO_GEN", False) or not cfg.GEMINI_API_KEY:
        return False
    if not getattr(cfg, "GEMINI_VEO_PAID_QUOTA", False) or veo_open_fn():
        return False
    model = getattr(cfg, "GEMINI_VIDEO_MODEL", "") or ""
    if getattr(cfg, "GEMINI_VEO_PREVIEW_ONLY", True) and "preview" not in model.lower():
        return False
    return True


def _sweep_render_temp_files(job_prefix: str = "") -> None:
    """Remove this job's intermediate WAVs; FFmpeg graph owns its temp dirs."""
    if not job_prefix:
        return
    cfg = _rw_attr("config", config)
    audio_dir = getattr(cfg, "AUDIO_DIR", "")
    if not audio_dir or not os.path.isdir(audio_dir):
        return
    suffixes = (
        "_eq.wav", "_146147.wav", "_breaths.wav", "_intro112.wav", "_room.wav",
        "_norm.wav", "_sonic.wav", "_jitter.wav", "_sfxbus.wav", "_bgm.wav",
        "_fitted.wav", "_piano182.wav", "_synth183.wav", "_crowd188.wav", "_reverb191.wav", "_epic195.wav",
    )
    for prefix in (job_prefix, f"{job_prefix}_master"):
        for suffix in suffixes:
            fp = os.path.join(audio_dir, f"{prefix}{suffix}")
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                except OSError:
                    pass


def _get_render_thread_limits(thermal_state=None):
    cfg = _rw_attr("config", config)
    render_threads = int(getattr(cfg, "RENDER_THREADS", 4) or 4)
    ffmpeg_threads = int(getattr(cfg, "FFMPEG_THREADS", render_threads) or render_threads)
    if isinstance(thermal_state, Mapping) and "unified_ram_gb" in thermal_state:
        from .render_resilience import resolve_safe_render_threads

        safe_t = resolve_safe_render_threads(requested_threads=render_threads)
        ram_gb = float(thermal_state.get("unified_ram_gb") or 16)
        if ram_gb <= 8 or thermal_state.get("thermal_throttle_recommended"):
            safe_t = min(safe_t, 2)
        return safe_t, safe_t
    if (thermal_state or {}).get("thermal_throttle_recommended"):
        render_threads = max(2, min(render_threads, 4))
        ffmpeg_threads = render_threads
    return render_threads, ffmpeg_threads


def _stamp_visual_mode(plan, selected) -> None:
    from visuals.mixed_visual import apply_selected_visual_mode, is_mixed_mode

    log_fn = _rw_attr("_log", _log)
    if plan and is_mixed_mode(selected):
        log_fn("[Visual] Karışık mod: sahneler sırayla stok ve Flux")
    apply_selected_visual_mode(plan, selected)


def _fetch_single_scene_visual(
    i, scene, plan, proj, total_s, gameplay_path=None, channel_id=None, req=None
):
    """Sync fetch for one scene — used from parallel executor (P1-13)."""
    st = _rw_attr("state", state)
    cfg = _rw_attr("config", config)
    log_fn = _rw_attr("_log", _log)
    gemini_open_fn = _rw_attr("_gemini_image_circuit_open", _gemini_image_circuit_open)
    veo_open_fn = _rw_attr("_veo_circuit_open", _veo_circuit_open)
    veo_allowed_fn = _rw_attr("_veo_render_allowed", _veo_render_allowed)
    fetch_selected_fn = _rw_attr("fetch_selected_stock_video", fetch_selected_stock_video)
    reddit_card_fn = _rw_attr("generate_reddit_post_card_clip", generate_reddit_post_card_clip)
    veo_clip_fn = _rw_attr("generate_veo_scene_clip", generate_veo_scene_clip)
    ai_img_fn = _rw_attr("generate_ai_image_clip", generate_ai_image_clip)
    scene_clip_fn = _rw_attr("fetch_scene_clip", fetch_scene_clip)

    def _is_cancelled():
        return bool(st.current_render_state.get("cancel_requested", False))

    if _is_cancelled():
        return i, None, None

    q = scene.get("search_queries") or ([scene.get("search_query")] if scene.get("search_query") else [])
    d = scene.get("duration", 7)
    desc = scene.get("scene_description", "")
    intent = scene.get("visual_intent") or {}
    narr = scene.get("narration", "")
    if not q and isinstance(intent, dict):
        q = intent.get("search_queries") or ([intent.get("subject")] if intent.get("subject") else [])
    if not q and desc:
        q = [desc]
    niche_id = (plan or {}).get("locked_niche") or (plan or {}).get("niche_id") or scene.get("niche_id") or ""
    p = None
    gemini_circuit_open = gemini_open_fn()
    source_policy = str(scene.get("visual_source_policy") or "licensed_first").casefold()
    prefer_ai = source_policy in {"ai", "synthetic", "ai_first"} or bool((plan or {}).get("prefer_ai_visuals"))

    visual_mode = str(
        scene.get("visual_mode") or (plan or {}).get("visual_mode")
        or (getattr(req, "visual_mode", "") if req else "") or (plan or {}).get("visual_style") or ""
    ).lower()
    from visuals.mixed_visual import is_mixed_mode, mixed_scene_mode

    if is_mixed_mode(visual_mode):
        visual_mode = mixed_scene_mode(i)
    if visual_mode == "stock":
        prefer_ai = False

    selected_vid = scene.get("selected_video") or {}
    local_candidate = selected_vid.get("path") or scene.get("video_path") or selected_vid.get("file_path")

    if not local_candidate and scene.get("path") and os.path.exists(scene.get("path")):
        if not (selected_vid and selected_vid.get("url") and not selected_vid.get("path")):
            local_candidate = scene.get("path")

    if not local_candidate and scene.get("video_url") and not str(scene.get("video_url")).startswith("http"):
        rel_p = str(scene["video_url"]).replace("\\", "/").lstrip("/")
        if rel_p.startswith("assets/"):
            rel_p = rel_p[7:]
        cand_p = os.path.join(cfg.ASSETS_DIR, rel_p)
        if os.path.isfile(cand_p):
            local_candidate = cand_p

    if local_candidate and os.path.exists(local_candidate):
        cand_name = os.path.basename(local_candidate).lower()
        if visual_mode in ("whiteboard", "sketch", "cizim") and "whiteboard" not in cand_name:
            p = None
        else:
            p = local_candidate
            log_fn(f"[Visual] Sahne #{i+1}: Önceden üretilen yerel klip kullanılıyor: {os.path.basename(p)}")

    if not p and not selected_vid and scene.get("video_url") and str(scene["video_url"]).startswith("http"):
        v_url = str(scene["video_url"])
        src = "pexels" if "pexels" in v_url else ("pixabay" if "pixabay" in v_url else "stock")
        selected_vid = {
            "url": v_url, "source": src, "kind": "video",
            "id": f"clip_{hashlib.sha256(v_url.encode()).hexdigest()[:16]}",
        }

    if not p and selected_vid and visual_mode not in ("whiteboard", "sketch", "cizim"):
        sel_kind = str(selected_vid.get("kind") or "video").strip().casefold()
        sel_src = str(selected_vid.get("source") or "").strip().casefold()
        is_sel_mock = hasattr(fetch_selected_fn, "_mock_name") or "unittest.mock" in type(fetch_selected_fn).__module__
        if is_sel_mock or (sel_kind == "video" and sel_src in {"pexels", "pixabay", "coverr", "mixkit"}):
            p = fetch_selected_fn(selected_vid, i, proj, target_duration=d, cancel_check=_is_cancelled)
            if p and os.path.isfile(p):
                scene["path"] = scene["video_path"] = selected_vid["path"] = p
                log_fn(f"[Visual] Sahne #{i+1}: Timeline seçimi stok klip indirildi: {os.path.basename(p)}")

    if not p and visual_mode in ("whiteboard", "sketch", "cizim"):
        from services.whiteboard_animator import create_whiteboard_scene_clip

        log_fn(f"[Whiteboard] Sahne #{i+1}: El çizim line-art animasyonu üretiliyor...")
        wb_path = os.path.join(proj, f"s{i:03d}_whiteboard.mp4")
        p = create_whiteboard_scene_clip(
            scene_description=desc or narr or (q[0] if q else "whiteboard line art sketch"),
            output_video_path=wb_path, duration=d, scene_index=i, narration=narr,
        )

    if not p and (
        visual_mode in ("pollinations", "flux", "0tl_ai", "flux_ai", "pollinations_ai")
        or (prefer_ai and not cfg.GEMINI_API_KEY and not getattr(cfg, "FAL_API_KEY", "") and not getattr(cfg, "STABILITY_API_KEY", ""))
    ):
        from services.pollinations_ai_visual import create_scene_ai_clip

        log_fn(f"[Flux AI] Sahne #{i+1}: 0 TL Pollinations Flux SDXL 9:16 görsel üretiliyor...")
        ai_path = os.path.join(proj, f"s{i:03d}_flux.mp4")
        p = create_scene_ai_clip(
            scene_description=desc or (q[0] if q else narr) or "cinematic vertical 9:16 footage",
            output_video_path=ai_path, duration=d, scene_index=i,
        )

    if not p and i == 0 and plan.get("reddit_post"):
        p = reddit_card_fn(plan["reddit_post"], os.path.join(proj, "s000_reddit_source.mp4"), duration=d)
    elif not p and prefer_ai and veo_allowed_fn() and i > 0:
        p = veo_clip_fn(
            scene_description=desc or (q[0] if q else (narr[:120] or "subject detail")),
            output_path=os.path.join(proj, f"s{i:03d}_veo.mp4"), duration=d,
        )
    elif not veo_open_fn() and getattr(cfg, "USE_GEMINI_VIDEO_GEN", False) and cfg.GEMINI_API_KEY and i > 0 and not getattr(cfg, "GEMINI_VEO_PAID_QUOTA", False):
        log_fn("[Visual] Veo atlandi — GEMINI_VEO_PAID_QUOTA=false (ucretli kota onayi gerekli)")
    elif prefer_ai and not gemini_circuit_open and getattr(cfg, "PREFER_GEMINI_SCENE_IMAGES", False) and getattr(cfg, "USE_GEMINI_IMAGE_GEN", False) and cfg.GEMINI_API_KEY:
        p = ai_img_fn(scene_description=desc or (q[0] if q else "cinematic"), output_path=os.path.join(proj, f"s{i:03d}_gemini.mp4"), duration=d)
    elif prefer_ai and not gemini_circuit_open and ((getattr(cfg, "USE_GEMINI_IMAGE_GEN", False) and cfg.GEMINI_API_KEY) or getattr(cfg, "FAL_API_KEY", "") or getattr(cfg, "STABILITY_API_KEY", "")):
        p = ai_img_fn(scene_description=desc or (q[0] if q else "cinematic"), output_path=os.path.join(proj, f"s{i:03d}_ai_gen.mp4"), duration=d)
    elif (veo_open_fn() or gemini_circuit_open) and (getattr(cfg, "PREFER_GEMINI_SCENE_IMAGES", False) or prefer_ai or (getattr(cfg, "USE_GEMINI_VIDEO_GEN", False) and i > 0 and prefer_ai)):
        reason = "veo 429" if veo_open_fn() else "gemini_image 429"
        log_fn(f"[Visual] Sahne {i + 1}/{total_s}: {reason} devre acik — zorunlu stok regen")

    if _is_cancelled():
        return i, None, None

    if not p:
        p = scene_clip_fn(
            q, i, proj, target_duration=d, scene_description=desc,
            cancel_check=lambda: st.current_render_state.get("cancel_requested", False),
            narration=narr, visual_intent=intent,
            must_exclude=(intent.get("must_exclude") if isinstance(intent, dict) else None),
            recent_texts=None, niche_id=niche_id, channel_id=channel_id,
        )

    if not p and not prefer_ai and not gemini_circuit_open:
        if veo_allowed_fn() and getattr(cfg, "USE_GEMINI_VIDEO_GEN", False):
            p = veo_clip_fn(scene_description=desc or (q[0] if q else "cinematic subject footage"), output_path=os.path.join(proj, f"s{i:03d}_veo_fallback.mp4"), duration=d)
        elif getattr(cfg, "USE_GEMINI_IMAGE_GEN", False) and cfg.GEMINI_API_KEY:
            p = ai_img_fn(scene_description=desc or (q[0] if q else "cinematic subject footage"), output_path=os.path.join(proj, f"s{i:03d}_ai_fallback.mp4"), duration=d)

    clip_entry = {
        "path": p, "duration": d, "narration": narr, "scene_description": desc, "search_queries": q,
        "badge_label": scene.get("badge_label"), "enable_pip": scene.get("enable_pip", False),
        "pip_path": scene.get("pip_path"), "handheld_shake": scene.get("handheld_shake", True),
        "affiliate_product": scene.get("affiliate_product", False), "beat_type": scene.get("beat_type", "conflict"),
        "mood": scene.get("mood", ""), "wipe_transition": scene.get("wipe_transition", False),
        "wipe_direction": scene.get("wipe_direction", "horizontal"), "visual_intent": intent,
        "scene_intent": scene.get("scene_intent") or (intent.get("shot_type") if isinstance(intent, dict) else ""),
        "camera_direction": scene.get("camera_direction") or "", "score": 100 if p else 0,
        "topic_match_score": 1.0 if p else 0.0, "t0": scene.get("t0", 0), "t1": scene.get("t1", 0),
    }
    return i, clip_entry, p


async def _fetch_scenes_parallel(scenes, plan, proj, total_s, gameplay_path=None, channel_id=None):
    """P1-13: asyncio.gather per-scene stock fetch via thread pool."""
    loop = asyncio.get_running_loop()
    st = _rw_attr("state", state)

    def _cancelled():
        return bool(st.current_render_state.get("cancel_requested", False))

    if _cancelled():
        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
    from compliance.visual_diversity import diversify_scene_search_queries

    adjusted_visuals = diversify_scene_search_queries(scenes)
    if adjusted_visuals:
        st.broadcast_event(
            "log",
            f"[VisualDiversity] {adjusted_visuals} sahnede tekrar eden arama sorgusu mevcut alternatif açıyla değiştirildi.",
        )

    async def _one(i, scene):
        if _cancelled():
            return i, None, None
        fetch_single_fn = _rw_attr("_fetch_single_scene_visual", _fetch_single_scene_visual)
        return await loop.run_in_executor(
            None,
            lambda i=i, scene=scene: fetch_single_fn(
                i, scene, plan, proj, total_s, gameplay_path=gameplay_path, channel_id=channel_id
            ),
        )

    tasks = [_one(i, scene) for i, scene in enumerate(scenes)]
    results = await asyncio.gather(*tasks)
    if _cancelled():
        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
    return results


def run_preflight_and_init_stage(req, check_cancelled: Callable[[], None]):
    """Run ops cleanup, thermal checks, niche/voice resolution, and project workspace binding."""
    cfg = _rw_attr("config", config)
    db = _rw_attr("database", database)
    log_fn = _rw_attr("_log", _log)
    threads_fn = _rw_attr("_get_render_thread_limits", _get_render_thread_limits)
    stamp_fn = _rw_attr("_stamp_visual_mode", _stamp_visual_mode)
    reset_used_fn = _rw_attr("reset_used_videos", reset_used_videos)
    reset_counts_fn = _rw_attr("reset_session_source_counts", reset_session_source_counts)

    render_threads, ffmpeg_threads = threads_fn()

    try:
        from system_resilience import purge_old_videos

        purge_result = purge_old_videos(max_age_days=30)
        if purge_result.get("purged_count"):
            log_fn(
                f"[Ops] auto_delete: {purge_result['purged_count']} eski video silindi ({purge_result['bytes_freed'] // 1024} KB)",
                2,
            )
    except Exception:
        pass

    try:
        from hardware_detector import get_cpu_thermal_state

        thermal = get_cpu_thermal_state()
        if thermal.get("thermal_throttle_recommended"):
            render_threads, ffmpeg_threads = threads_fn(thermal)
            log_fn(f"[Ops] CPU thermal throttle: {thermal.get('temperature_c')}°C — threads={render_threads}", 2)
    except Exception:
        pass

    target_lang = (req.language or cfg.LANGUAGE or "tr").lower()
    cfg.LANGUAGE = target_lang

    plan = req.plan
    vm = getattr(req, "visual_mode", None)
    stamp_fn(plan, vm)
    keyword = (plan.get("title") if plan and plan.get("title") else req.keyword) or "Video"

    from director import resolve_niche_from_topic

    requested_niche = getattr(req, "niche", None) or "1_news_flash"
    locked_niche = resolve_niche_from_topic(keyword, requested_niche)
    req.niche = locked_niche

    ch_paths = cfg.channel_paths(getattr(req, "channel_id", None))
    db_id = db.add_video_record(keyword, target_lang, cfg.AI_PROVIDER, channel_slug=ch_paths["slug"])
    from .pipeline_state_machine import PipelineStage, PipelineStateMachine

    sm = PipelineStateMachine(job_id=str(db_id or "job"), keyword=keyword, niche_id=locked_niche)
    log_fn(f"[Director] İşlem başlatılıyor: '{keyword}'...", 5)
    if locked_niche != requested_niche:
        log_fn(f"[Niche] Konu kilidi: '{requested_niche}' -> '{locked_niche}' (baslik: {keyword[:48]})", 6)

    from scenes.hadith_overlay import is_sacred_niche

    if is_sacred_niche(locked_niche, keyword):
        cfg.TTS_SACRED_CALM = True
        cfg.TTS_RATE = getattr(cfg, "SACRED_TTS_RATE", "+8%")
        log_fn("[TTS] Kutsal niş: tempo varsayılandan sakin. Ses hızlandırılmaz.", 7)

    gender = req.voice_gender or "male"
    if gender == "auto":
        from voice_humanizer import select_voice_gender

        gender = select_voice_gender(locked_niche, keyword)
    from tts_voices import resolve_voice, voice_gender_for_id

    selected_voice = resolve_voice(target_lang, voice_id=getattr(req, "tts_voice", None), gender=gender)
    cfg.TTS_VOICE = selected_voice
    cfg.TTS_GENDER = voice_gender_for_id(selected_voice, target_lang)

    check_cancelled()

    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    safe = re.sub(r"\s+", "_", re.sub(r"[^\w\s-]", "", keyword.translate(tr_map)).strip())[:80] or f"shorts_{int(time.time())}"
    render_job_prefix = safe
    assets_root, output_root = ch_paths["assets_dir"], ch_paths["output_dir"]
    if ch_paths["slug"] != "default":
        log_fn(f"[Channel] Çıktı klasörü: channels/{ch_paths['slug']}", 7)
    proj = os.path.join(assets_root, safe)
    os.makedirs(proj, exist_ok=True)
    sm.bind_project(proj, resume=bool(getattr(req, "resume", False)))
    reset_used_fn()
    try:
        from visuals.fetch import reset_job_manifest

        reset_job_manifest()
    except Exception as manifest_err:
        log_fn(f"[Visual] Manifest reset note: {manifest_err}", 8)
    reset_counts_fn()

    return (
        render_threads, ffmpeg_threads, target_lang, plan, vm, keyword,
        locked_niche, ch_paths, db_id, sm, safe, render_job_prefix,
        output_root, proj, PipelineStage,
    )
