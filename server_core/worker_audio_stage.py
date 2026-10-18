"""
Render Worker Stages 6–8: TTS Synthesis & Timeline Fit, Royalty-Free BGM Selection,
One-Pass Audio Mastering (Sidechain Ducking + EBU R128), Viral SEO Generation,
and Subtitle Option Compilation.
Extracted from server_core/render_worker.py for modularity.
"""
import json
import os
import wave
from typing import Any, Callable, Dict, List, Optional, Tuple

import config
import database
from subtitle_generator import (
    SUBTITLE_PRESETS,
    merge_studio_subtitle_opts,
    resolve_ab_subtitle_preset,
)
from tts_engine import active_tts_provider, generate_narration_with_timing
from . import state
from .pipeline_state_machine import PipelineStage
from .worker_audio_helpers import (
    _wav_seconds,
    build_seo_and_subtitle_options,
    select_and_master_bgm_audio,
)


def run_tts_and_audio_master_stage(
    *,
    req: Any,
    plan: Dict[str, Any],
    director: Any,
    clips: List[Dict[str, Any]],
    proj: str,
    output_root: str,
    safe: str,
    keyword: str,
    locked_niche: str,
    target_lang: str,
    final_variation_attempt: int,
    db_id: Optional[int],
    sm: Any,
    check_cancelled: Callable[[], None],
    log_fn: Callable[..., None],
) -> Tuple[
    bool,
    Dict[str, Any],
    Any,
    str,
    List[Dict[str, Any]],
    float,
    str,
    bool,
    Dict[str, Any],
    str,
    str,
    Dict[str, Any],
]:
    """
    Executes Stages 6, 7, and 8 (TTS, Audio Mastering, SEO, and Subtitle compilation).
    Returns:
        (ok_to_continue, plan, director, audio_path, timings, audio_dur,
         bgm_track, user_wants_muted, seo_meta, seo_file, script_text, sub_opts)
    """
    from director import compile_director_plan, fit_tts_to_timeline
    from voice_humanizer import VoiceHumanizer

    check_cancelled()
    lang_title = "İngilizce" if target_lang == "en" else "Türkçe"
    sm.transition_to(
        PipelineStage.STAGE_6_TTS_SYNC,
        f"Seslendirme ve Zamanlama ({active_tts_provider()}): {lang_title} ses üretiliyor",
        pct=58.0,
    )
    log_fn(f"[Timeline] {lang_title} Seslendirme ({active_tts_provider()})...", 62)
    audio_path = os.path.join(config.AUDIO_DIR, f"{safe}.wav")

    niche_for_voice = director.niche_id if director else req.niche
    asmr_profile = VoiceHumanizer.get_asmr_voice_settings(niche_for_voice, keyword)
    narration_text = plan.get("full_narration") or ""

    tts_restored = False
    saved_tts: Dict[str, Any] = {}
    timings: List[Dict[str, Any]] = []
    audio_dur = 0.0
    speed = 1.0
    script_regen_494 = False

    if sm.reusable(PipelineStage.STAGE_6_TTS_SYNC):
        saved_tts = sm.stage_artifacts(PipelineStage.STAGE_6_TTS_SYNC)
        saved_audio = saved_tts.get("audio_path") or ""
        saved_timings = saved_tts.get("timings") or []
        if saved_audio and isinstance(saved_timings, list) and saved_timings:
            audio_path = saved_audio
            timings = saved_timings
            tts_restored = True
            log_fn("[Resume] Ses dosyası duruyor. TTS atlandı.", 62)

    if director and not tts_restored:
        from director import pre_render_score as _pre_render_score
        from scenes.narration_validate import apply_auto_repair_if_needed

        tts_plan, tts_fixes, _ = apply_auto_repair_if_needed(director.to_legacy_plan())
        if tts_fixes:
            check_cancelled()
            log_fn(f"[QualityGate] TTS oncesi anlatim duzeltildi: {len(tts_fixes)} fix", 60)
            director = compile_director_plan(
                tts_plan,
                title=keyword,
                niche_id=locked_niche,
                language=target_lang,
                reddit_post=getattr(req, "reddit_post", None),
            )
            plan = director.to_legacy_plan()
            narration_text = plan.get("full_narration") or ""

        try:
            from services.niche_guardrails import validate_script_niche_compliance

            _ng_niche = director.niche_id if director else getattr(req, "niche", "")
            niche_val = validate_script_niche_compliance(
                narration_text,
                niche_id=_ng_niche,
                lang=target_lang,
            )
            if not niche_val.get("compliant", True):
                log_fn(
                    f"[NicheGuardrails] Cliché tespit edildi ({len(niche_val.get('violations', []))} adet), temizleniyor...",
                    60,
                )
                narration_text = niche_val.get("cleaned_text", narration_text)
                for _sc in getattr(director, "scenes", []) or []:
                    _sc_narr = getattr(_sc, "narration", "") or ""
                    if _sc_narr:
                        _sc.narration = validate_script_niche_compliance(
                            _sc_narr, niche_id=_ng_niche, lang=target_lang
                        ).get("cleaned_text", _sc_narr)
                if plan:
                    for _psc in plan.get("scenes") or []:
                        if isinstance(_psc, dict) and _psc.get("narration"):
                            _psc["narration"] = validate_script_niche_compliance(
                                _psc["narration"], niche_id=_ng_niche, lang=target_lang
                            ).get("cleaned_text", _psc["narration"])
                    plan["full_narration"] = narration_text
        except Exception as ng_err:
            log_fn(f"[NicheGuardrails] Denetim uyarısı: {ng_err}", 60)

        tts_pre = _pre_render_score(director)
        tts_block = [
            i
            for i in tts_pre.get("issues", [])
            if i.startswith("fragment")
            or i.startswith("low_words")
            or i.startswith("empty_narration")
            or i.startswith("no_terminal")
        ]
        if tts_block:
            msg = f"TTS öncesi anlatım kapısı: {', '.join(tts_block)}. Senaryoyu yeniden üretin."
            log_fn(f"[QualityGate] {msg}", 61)
            if db_id:
                database.update_video_status(db_id, "failed", error_message=msg)
            state.broadcast_event("error", msg)
            return (
                False,
                plan,
                director,
                audio_path,
                timings,
                audio_dur,
                "",
                False,
                {},
                "",
                "",
                {},
            )

    if not tts_restored:
        sm.invalidate_from(PipelineStage.STAGE_6_TTS_SYNC)
        _, timings = generate_narration_with_timing(
            narration_text, audio_path, voice_profile=asmr_profile
        )
        log_fn(f"[Timeline] TTS tamamlandı — {len(timings)} kelime zamanlaması", 68)

    if director and tts_restored:
        audio_dur = float(saved_tts.get("audio_dur") or 0.0)
        speed = float(saved_tts.get("speed") or 1.0)
        for i, span in enumerate(saved_tts.get("scene_spans") or []):
            if not isinstance(span, dict):
                continue
            if i < len(director.scenes):
                director.scenes[i].duration = float(
                    span.get("duration") or director.scenes[i].duration
                )
                director.scenes[i].t0 = float(span.get("t0") or 0.0)
                director.scenes[i].t1 = float(span.get("t1") or 0.0)
            if i < len(clips) and isinstance(clips[i], dict):
                clips[i]["duration"] = (
                    director.scenes[i].duration
                    if i < len(director.scenes)
                    else span.get("duration")
                )
                clips[i]["t0"] = span.get("t0")
                clips[i]["t1"] = span.get("t1")
        plan = director.to_legacy_plan()
        log_fn(
            f"[Timeline] Kayıtlı TTS {audio_dur:.1f}s (speed×{speed:.2f})",
            70,
        )
    elif director:
        fitted = os.path.join(config.AUDIO_DIR, f"{safe}_fitted.wav")

        def _condense_and_retts(raw_sec: float) -> None:
            nonlocal director, plan, narration_text, audio_path, timings, script_regen_494
            from director.timeline import recover_overlong_narration
            from scenes.generator import _gemini_script_circuit_open

            spoken = len((narration_text or "").split())
            log_fn(
                f"[Timeline] TTS {raw_sec:.1f}s / {spoken} kelime — doğal tempo, yerel kısaltma. Hızlandırma yok.",
                69,
            )
            if _gemini_script_circuit_open():
                log_fn("[Timeline] gemini_script açık — Gemini çağrılmadı.", 69)
            old_scenes = list(getattr(director, "scenes", []) or [])
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
                matched_clips: List[Dict[str, Any]] = []
                used_clip_idxs: set = set()
                for i, sc in enumerate(director.scenes):
                    sc_path = getattr(sc, "path", None) or ""
                    sc_narr_prefix = (getattr(sc, "narration", "") or "").strip()[:30]
                    sc_desc_prefix = (getattr(sc, "scene_description", "") or "").strip()[:30]
                    best_idx: Optional[int] = None
                    if sc_path:
                        for j, c in enumerate(clips):
                            if j in used_clip_idxs:
                                continue
                            orig_sc = old_scenes[j] if j < len(old_scenes) else None
                            c_path = (c.get("path") if isinstance(c, dict) else "") or (
                                getattr(orig_sc, "path", "") if orig_sc else ""
                            )
                            if c_path and c_path == sc_path:
                                best_idx = j
                                break
                    if best_idx is None and (sc_narr_prefix or sc_desc_prefix):
                        for j, c in enumerate(clips):
                            if j in used_clip_idxs:
                                continue
                            orig_sc = old_scenes[j] if j < len(old_scenes) else None
                            c_narr = (
                                (c.get("narration") if isinstance(c, dict) else "")
                                or (getattr(orig_sc, "narration", "") if orig_sc else "")
                                or ""
                            ).strip()[:30]
                            c_desc = (
                                (
                                    (c.get("scene_description") or c.get("description"))
                                    if isinstance(c, dict)
                                    else ""
                                )
                                or (getattr(orig_sc, "scene_description", "") if orig_sc else "")
                                or ""
                            ).strip()[:30]
                            if (sc_narr_prefix and c_narr == sc_narr_prefix) or (
                                sc_desc_prefix and c_desc == sc_desc_prefix
                            ):
                                best_idx = j
                                break
                    if best_idx is None:
                        if i < len(clips) and i not in used_clip_idxs:
                            best_idx = i
                        else:
                            best_idx = next(
                                (j for j in range(len(clips)) if j not in used_clip_idxs),
                                min(i, len(clips) - 1),
                            )
                    used_clip_idxs.add(best_idx)
                    matched_clips.append(clips[best_idx])
                clips[:] = matched_clips
            with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
                json.dump(plan, f, ensure_ascii=False, indent=2)
            with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
                json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)
            log_fn(f"[Timeline] Kısaltılmış anlatım {new_words} kelime — TTS bir kez daha.", 69)
            _, timings_new = generate_narration_with_timing(
                narration_text, audio_path, voice_profile=asmr_profile
            )
            timings = timings_new

        raw_sec = _wav_seconds(audio_path)
        if raw_sec > 60.0 and not script_regen_494:
            try:
                _condense_and_retts(raw_sec)
            except Exception as cond_err:
                log_fn(
                    f"[QualityGate] UYARI: Anlatım kısaltma: {cond_err} (Tempo uyarlaması ile devam ediliyor)",
                    69,
                )
        try:
            audio_path, timings, audio_dur, speed = fit_tts_to_timeline(
                audio_path,
                director,
                word_timings=timings,
                output_path=fitted,
                allow_tempo_fallback=True,
            )
        except Exception as fit_err:
            log_fn(
                f"[QualityGate] UYARI: {fit_err} — otomatik tempo uyarlaması uygulanıyor",
                69,
            )
            try:
                from services.audio_tempo_guard import speedup_audio

                fitted_audio = audio_path.rsplit(".", 1)[0] + "_fitted.wav"
                speedup_audio(audio_path, fitted_audio, target_duration=59.0)
                audio_path = fitted_audio
                audio_dur = 59.0
                speed = raw_sec / 59.0
                if speed > 0:
                    rescaled_timings: List[Dict[str, Any]] = []
                    for w in timings or []:
                        if isinstance(w, dict):
                            w_copy = dict(w)
                            w_copy["offset"] = round(float(w.get("offset", 0.0)) / speed, 4)
                            w_copy["duration"] = round(
                                max(0.04, float(w.get("duration", 0.1)) / speed), 4
                            )
                            if "start" in w_copy:
                                w_copy["start"] = round(float(w.get("start", 0.0)) / speed, 4)
                            if "end" in w_copy:
                                w_copy["end"] = round(float(w.get("end", 0.0)) / speed, 4)
                            rescaled_timings.append(w_copy)
                    timings = rescaled_timings
                    if getattr(director, "scenes", None):
                        total_sc_dur = sum(
                            max(0.0, float(getattr(s, "duration", 0.0) or 0.0))
                            for s in director.scenes
                        )
                        sc_scale = (
                            (audio_dur / total_sc_dur)
                            if total_sc_dur > 0
                            else (1.0 / speed)
                        )
                        cursor = 0.0
                        for idx_s, s in enumerate(director.scenes):
                            if idx_s == len(director.scenes) - 1:
                                s_dur = round(max(0.1, audio_dur - cursor), 3)
                            else:
                                s_dur = round(
                                    max(0.1, float(getattr(s, "duration", 0.0) or 0.0) * sc_scale),
                                    3,
                                )
                            s.duration = s_dur
                            s.t0 = round(cursor, 3)
                            cursor = round(cursor + s_dur, 3)
                            s.t1 = round(cursor, 3)
            except Exception:
                audio_dur = min(raw_sec, 59.0)
                speed = 1.0

        for i, s in enumerate(director.scenes):
            if i < len(clips):
                clips[i]["duration"] = s.duration
                clips[i]["t0"] = s.t0
                clips[i]["t1"] = s.t1
        plan = director.to_legacy_plan()
        log_fn(
            f"[Timeline] TTS {audio_dur:.1f}s (speed×{speed:.2f}; doğal tempo, hızlandırma yok)",
            70,
        )

    if not tts_restored and audio_path and os.path.isfile(audio_path):
        scene_spans = []
        if director:
            scene_spans = [
                {"duration": s.duration, "t0": s.t0, "t1": s.t1} for s in director.scenes
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

    audio_path, timings, bgm_track, user_wants_muted = select_and_master_bgm_audio(
        req=req,
        director=director,
        audio_path=audio_path,
        timings=timings,
        safe=safe,
        keyword=keyword,
        sm=sm,
        check_cancelled=check_cancelled,
        log_fn=log_fn,
    )

    seo_meta, seo_file, script_text, sub_opts = build_seo_and_subtitle_options(
        req=req,
        plan=plan,
        director=director,
        output_root=output_root,
        safe=safe,
        keyword=keyword,
        locked_niche=locked_niche,
        target_lang=target_lang,
        final_variation_attempt=final_variation_attempt,
        sm=sm,
        log_fn=log_fn,
    )

    return (
        True,
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
    )
