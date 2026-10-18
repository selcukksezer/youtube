"""
Render Worker Audio Stage Helpers: BGM selection, one-pass audio mastering,
viral SEO generation, and subtitle option compilation.
Extracted from server_core/worker_audio_stage.py for modularity.
"""
import json
import os
import wave
from typing import Any, Callable, Dict, List, Optional, Tuple

import config
from subtitle_generator import (
    SUBTITLE_PRESETS,
    merge_studio_subtitle_opts,
    resolve_ab_subtitle_preset,
    rotate_session_subtitle_style,
)
from .pipeline_state_machine import PipelineStage


def _wav_seconds(path: str) -> float:
    try:
        with wave.open(path, "rb") as w:
            rate = float(w.getframerate() or 0)
            return (w.getnframes() / rate) if rate else 0.0
    except Exception:
        return 0.0


def select_and_master_bgm_audio(
    *,
    req: Any,
    director: Any,
    audio_path: str,
    timings: List[Dict[str, Any]],
    safe: str,
    keyword: str,
    sm: Any,
    check_cancelled: Callable[[], None],
    log_fn: Callable[..., None],
) -> Tuple[str, List[Dict[str, Any]], str, bool]:
    """Select royalty-free/catalog BGM and run Stage 7 one-pass audio mastering."""
    from bgm_manager import request_mutes_bgm
    from director import master_audio_one_pass

    bgm_req = (req.bgm_track or "").strip()
    bgm_track = ""
    user_wants_muted = request_mutes_bgm(bgm_req, getattr(req, "enable_bgm", None))

    if not user_wants_muted:
        if bgm_req:
            from youtube_safe_bgm_catalog import ensure_catalog_track, resolve_bgm_path

            local_p = resolve_bgm_path(bgm_req)
            if not local_p or not os.path.isfile(local_p) or os.path.getsize(local_p) < 2000:
                log_fn(f"[BGM] Katalog parçası indiriliyor: {bgm_req}...", 70)
                downloaded_fn = ensure_catalog_track(filename=bgm_req) or ensure_catalog_track(
                    track_id=bgm_req
                )
                if downloaded_fn:
                    bgm_track = downloaded_fn
                    log_fn(f"[BGM] Katalog parçası hazır: {bgm_track}", 71)
                else:
                    log_fn(
                        f"[BGM] Katalog indirme başarısız ({bgm_req}), alternatif kütüphaneden seçiliyor...",
                        71,
                    )
                    bgm_track = ""
            else:
                bgm_track = os.path.basename(local_p)
                log_fn(f"[BGM] Seçili fon müziği doğrulandı: {bgm_track}", 71)

        if (
            not bgm_track
            and getattr(config, "AUTO_FETCH_ROYALTY_FREE_BGM", True)
            and getattr(config, "ENABLE_BGM", True)
        ):
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
                    log_fn(f"[VoiceLab/RF] Telifsiz BGM secildi: {bgm_track}", 71)
            except Exception as e:
                print(f"  [VoiceLab/RF] Notice: {e}")

        if not bgm_track and getattr(config, "ENABLE_BGM", True):
            try:
                from youtube_safe_bgm_catalog import pick_catalog_bgm_for_niche

                niche_hint = director.niche_id if director else getattr(req, "niche", "")
                bgm_track = pick_catalog_bgm_for_niche(niche_id=niche_hint, query=keyword) or ""
                if bgm_track:
                    log_fn(f"[BGM] Niş uyumlu katalog müziği seçildi: {bgm_track}", 71)
            except Exception as e:
                print(f"  [BGM] Notice: {e}")

        if not bgm_track and getattr(config, "ENABLE_BGM", True):
            try:
                from bgm_manager import get_safe_default_bgm_path

                default_p = get_safe_default_bgm_path()
                if default_p and os.path.exists(default_p):
                    bgm_track = os.path.basename(default_p)
                    log_fn(f"[BGM] Varsayılan telifsiz ambient müzik seçildi: {bgm_track}", 71)
            except Exception as e:
                print(f"  [BGM] Safe default notice: {e}")

        if bgm_track:
            try:
                from bgm_manager import get_safe_default_bgm_path
                from copyright_risk import scan_audio_copyright_risk

                audio_scan = scan_audio_copyright_risk([bgm_track])
                if not audio_scan.get("safe"):
                    log_fn(f"[Copyright] BGM risk: {bgm_track} → royalty_free_ambient", 71)
                    bgm_track = os.path.basename(get_safe_default_bgm_path())
            except Exception:
                pass
    else:
        log_fn("[BGM] Kullanıcı tercihi: Müziksiz video render ediliyor.", 71)

    check_cancelled()
    sm.transition_to(
        PipelineStage.STAGE_7_AUDIO_MASTERING,
        "Akustik Tasarım ve Miksaj: Sidechain ducking (-18dB) ve EBU R128 (-14 LUFS)",
        pct=68.0,
    )
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
        log_fn("[Resume] Master ses duruyor. Miks atlandı.", 72)
    elif director:
        from bgm_manager import resolve_studio_audio_mix
        from director.audio_bus import apply_intro_whoosh_pref

        director.effect_manifest = apply_intro_whoosh_pref(
            director.effect_manifest,
            bool(getattr(req, "enable_intro_whoosh", False)),
        )
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
        log_fn(
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
        if (
            director.effect_manifest.get("item_112_whoosh_ding", False)
            and timings
            and not any(wt.get("_whoosh_shifted") for wt in timings if isinstance(wt, dict))
        ):
            timings = [
                {**wt, "offset": round(float(wt.get("offset", 0.0)) + 0.2, 4), "_whoosh_shifted": True}
                if isinstance(wt, dict)
                else wt
                for wt in timings
            ]
        if audio_path and os.path.isfile(audio_path):
            sm.mark_done(
                PipelineStage.STAGE_7_AUDIO_MASTERING,
                artifacts={"audio_path": audio_path, "timings": timings},
                files=[audio_path],
            )

    return audio_path, timings, bgm_track, user_wants_muted


def build_seo_and_subtitle_options(
    *,
    req: Any,
    plan: Dict[str, Any],
    director: Any,
    output_root: str,
    safe: str,
    keyword: str,
    locked_niche: str,
    target_lang: str,
    final_variation_attempt: int,
    sm: Any,
    log_fn: Callable[..., None],
) -> Tuple[Dict[str, Any], str, str, Dict[str, Any]]:
    """Generate viral SEO metadata, configure render resolution, and compile Stage 8 subtitle options."""
    from viral_seo_agent import generate_viral_seo_metadata

    log_fn("[Director] Viral SEO meta üretiliyor...", 74)
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
            script_text = " ".join(
                [
                    str(s.get("narration", ""))
                    for s in plan.get("scenes", [])
                    if isinstance(s, dict) and s.get("narration")
                ]
            )

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
        log_fn(f"[Director] SEO hazır: {seo_meta.get('seo_title', keyword)}")
    except Exception as se:
        print(f"  [SEO] Notice: {se}")

    if getattr(req, "resolution", None) in ("1080p", "720p", "540p"):
        res_mode = req.resolution
        config.RENDER_RESOLUTION_MODE = res_mode
        res_dims = config.RESOLUTIONS.get(res_mode, (1080, 1920))
        log_fn(f"[FFmpegGraph] Çözünürlük: {res_mode} ({res_dims[0]}x{res_dims[1]})")
    else:
        config.RENDER_RESOLUTION_MODE = "1080p"
        log_fn("[FFmpegGraph] Çözünürlük: 1080p (1080x1920) — final varsayılan")

    rotate_session_subtitle_style()
    sub_opts: Dict[str, Any] = {}
    sm.transition_to(
        PipelineStage.STAGE_8_SUBTITLE_COMPILE,
        "Kinetik Altyazı Derleme: Vektörel ASS şablonu ve kelime zıplamaları",
        pct=76.0,
    )
    preset_locked = bool(req.subtitle_preset and req.subtitle_preset in SUBTITLE_PRESETS)
    active_preset_name = req.subtitle_preset if preset_locked else ""
    if preset_locked:
        sub_opts = merge_studio_subtitle_opts(
            active_preset_name,
            font_size=req.subtitle_font_size,
            y_position=req.subtitle_y_position,
            color=req.subtitle_color,
            highlight_color=req.subtitle_highlight_color,
        )
    elif not req.subtitle_color and not req.subtitle_highlight_color:
        ab_opts = resolve_ab_subtitle_preset(final_variation_attempt, keyword)
        if ab_opts:
            clean_ab = {k: v for k, v in ab_opts.items() if k != "ab_test_variant"}
            sub_opts.update(clean_ab)
            active_preset_name = next(
                (k for k, v in SUBTITLE_PRESETS.items() if v == clean_ab),
                "red_fire",
            )
        else:
            from subtitle_generator import get_niche_subtitle_preset

            niche_preset = get_niche_subtitle_preset(locked_niche)
            sub_opts.update(niche_preset)
            active_preset_name = next(
                (k for k, v in SUBTITLE_PRESETS.items() if v == niche_preset),
                "capcut_yellow",
            )
        sub_opts = merge_studio_subtitle_opts(
            active_preset_name,
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

    arabic_overlays = []
    scenes_source = director.scenes if director else (plan or {}).get("scenes") or []
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

        if raw_t0 is not None and (
            float(raw_t0) > 0.0 or (i == 0 and raw_t1 and float(raw_t1) > 0.0)
        ):
            sc_t0 = float(raw_t0)
            sc_t1 = float(raw_t1) if raw_t1 is not None else (sc_t0 + dur)
            running_cursor = sc_t1
        else:
            sc_t0 = running_cursor
            sc_t1 = running_cursor + dur
            running_cursor += dur

        if ar or cit:
            arabic_overlays.append(
                {
                    "scene_index": i,
                    "arabic_text": ar,
                    "source_citation": cit,
                    "start": sc_t0,
                    "end": sc_t1,
                }
            )
    if arabic_overlays:
        sub_opts["arabic_overlays"] = arabic_overlays
        if req.subtitle_y_position is None:
            is_split = bool(
                getattr(req, "split_screen", False)
                or (isinstance(plan, dict) and plan.get("hybrid_split_screen"))
            )
            sub_opts["y_position"] = 0.46 if is_split else 0.56
            sub_opts["allow_mid_frame"] = True

    human_craft = (plan or {}).get("human_craft") if isinstance(plan, dict) else None
    try:
        from craft import subtitle_opts_from_craft

        craft_subs = subtitle_opts_from_craft(human_craft)
        if craft_subs:
            sub_opts = merge_studio_subtitle_opts(
                active_preset_name,
                base=sub_opts,
                font_size=req.subtitle_font_size,
                y_position=req.subtitle_y_position,
                craft_opts=craft_subs,
            )
    except Exception:
        pass

    return seo_meta, seo_file, script_text, sub_opts
