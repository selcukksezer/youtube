"""
Composer Audio Mastering, Voice Humanizer Chain, Niche Acoustic SFX Layering,
and BGM Beat-Sync / Ducking Mix for `video_composer.py`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import wave
from typing import Any, Callable, Dict, Optional, Tuple

import config
from bgm_manager import (
    align_scenes_to_bgm_beats,
    get_bgm_path,
    mix_narration_and_bgm,
)
from sfx_manager import add_sfx_to_narration

_COMPOSER_AUDIO_TEMP_SUFFIXES = (
    "_eq.wav", "_consistent.wav", "_gated.wav", "_breaths.wav", "_intro112.wav",
    "_room.wav", "_norm.wav", "_sonic.wav", "_jitter.wav", "_sfx_audio.wav",
    "_risers.wav", "_quiz_gap.wav", "_tension_gap.wav", "_ding.wav", "_buzzer.wav",
    "_rev_reverb.wav", "_news_cadence.wav", "_vinyl_crackle.wav", "_shock_silence.wav",
    "_monologue_pause.wav", "_phone_quote.wav", "_piano182.wav", "_synth183.wav",
    "_crowd188.wav", "_reverb191.wav", "_epic195.wav", "_bgm_swell.wav",
    "_mixed_audio.wav", "_intro_punch.wav", "_phase_aligned.wav", "_master_norm.wav",
)


def _vc_attr(name: str, default: Any) -> Any:
    vc = sys.modules.get("video_composer")
    if vc is not None and hasattr(vc, name):
        return getattr(vc, name)
    cap = sys.modules.get("render.composer_audio_packaging")
    if cap is not None and hasattr(cap, name):
        return getattr(cap, name)
    return default


def _cleanup_composer_audio_files(output_path, source_audio, *temporary_audio_paths):
    os_mod = _vc_attr("os", os)
    output_base = output_path.rsplit(".", 1)[0]
    protected = (
        os_mod.path.normcase(os_mod.path.abspath(source_audio))
        if source_audio else None
    )
    candidates = [output_base + suffix for suffix in _COMPOSER_AUDIO_TEMP_SUFFIXES]
    candidates.extend(temporary_audio_paths)
    for path in dict.fromkeys(path for path in candidates if path):
        if os_mod.path.normcase(os_mod.path.abspath(path)) == protected:
            continue
        if not os_mod.path.isfile(path):
            continue
        try:
            os_mod.remove(path)
        except OSError as exc:
            print(f"  [Composer] Temporary audio cleanup failed for {path}: {exc}", flush=True)


def _select_auto_bgm(scene_clips, title, niche_id) -> Tuple[str, str]:
    from services.audio_mood_director import audio_mood_director

    script_text = " ".join(
        str(scene.get("narration") or "")
        for scene in (scene_clips or [])
        if isinstance(scene, dict)
    ).strip() or str(title or "")
    mood = audio_mood_director.detect_mood(
        script_text,
        niche_id=niche_id or "general",
    )
    matched = audio_mood_director.match_bgm_track(mood)
    if matched.get("source") == "matched_local" and matched.get("filename"):
        return str(matched["filename"]), mood.value

    from bgm_manager import select_trend_hybrid_bgm

    hybrid = select_trend_hybrid_bgm(
        niche_id=niche_id or "",
        topic=title or "",
        preferred_mood=mood.value,
    )
    return str(hybrid.get("track") or ""), mood.value


def build_composer_audio_master(
    *,
    scene_clips: list,
    audio_path: str,
    word_timings: list,
    output_path: str,
    title: str,
    niche_id: str,
    bgm_track: Optional[str],
    bgm_volume: Optional[float],
    audio_premastered: bool,
    enable_section2_filters: bool,
    cancel_check: Optional[Callable[[], bool]],
    extra_kwargs: Dict[str, Any],
    select_auto_bgm_fn: Callable = _select_auto_bgm,
) -> Tuple[str, str, list]:
    """
    Runs the Composer voice humanizer, SFX layering, and BGM mixing chain.
    Returns (processed_audio, final_audio, scene_clips).
    """
    os_mod = _vc_attr("os", os)
    cfg_mod = _vc_attr("config", config)
    add_sfx_fn = _vc_attr("add_sfx_to_narration", add_sfx_to_narration)
    get_bgm_fn = _vc_attr("get_bgm_path", get_bgm_path)
    align_beats_fn = _vc_attr("align_scenes_to_bgm_beats", align_scenes_to_bgm_beats)
    mix_bgm_fn = _vc_attr("mix_narration_and_bgm", mix_narration_and_bgm)

    mastered_audio = audio_path
    if audio_premastered:
        print("  [Composer] Audio premastered by DirectorPlan AudioMaster — voice chain skipped.")
    else:
        try:
            from voice_humanizer import voice_humanizer
            eq_audio = output_path.rsplit(".", 1)[0] + "_eq.wav"
            eq_audio = voice_humanizer.apply_studio_eq_and_warmth(audio_path, eq_audio)
            mastered_audio = eq_audio
            print("  [Composer] [VoiceHumanizer] Studio Warmth EQ applied.")

            consistent_audio = output_path.rsplit(".", 1)[0] + "_consistent.wav"
            from voice.audio_dsp import apply_voice_level_consistency
            mastered_audio = apply_voice_level_consistency(mastered_audio, consistent_audio)
            print("  [Composer] [VoiceHumanizer] Voice level consistency applied (Item 193).")

            gated_audio = output_path.rsplit(".", 1)[0] + "_gated.wav"
            mastered_audio = voice_humanizer.apply_noise_gate(mastered_audio, gated_audio)
            print("  [Composer] [VoiceHumanizer] Noise gate uygulandı (Madde 172).")

            breaths_audio = output_path.rsplit(".", 1)[0] + "_breaths.wav"
            mastered_audio = voice_humanizer.inject_natural_breaths(eq_audio, breaths_audio, interval_seconds=5.0)
            print("  [Composer] [VoiceHumanizer] Natural breath layer injected every ~5s (Item 141).")

            enable_intro_whoosh = bool(extra_kwargs.get("enable_intro_whoosh", False))
            if enable_intro_whoosh:
                intro_audio = output_path.rsplit(".", 1)[0] + "_intro112.wav"
                from voice_humanizer import prepend_whoosh_ding_to_narration
                prepended = prepend_whoosh_ding_to_narration(mastered_audio, intro_audio)
                if prepended == intro_audio and os_mod.path.exists(intro_audio):
                    mastered_audio = intro_audio
                    if word_timings:
                        for wt in word_timings:
                            wt["offset"] = wt.get("offset", 0.0) + 0.2
                    print("  [Composer] [VoiceHumanizer] Item 112 Whoosh+Ding intro uygulandı.")

            if bool(extra_kwargs.get("enable_room_tone", False)):
                room_audio = output_path.rsplit(".", 1)[0] + "_room.wav"
                from voice_humanizer import mix_pink_noise_into_narration
                mastered_audio = mix_pink_noise_into_narration(
                    mastered_audio, room_audio, noise_db=-32.0, noise_type="room"
                )
                print("  [Composer] [VoiceHumanizer] Light room ambience applied (Item 145).")

            norm_audio = output_path.rsplit(".", 1)[0] + "_norm.wav"
            mastered_audio = voice_humanizer.normalize_ebu_r128(mastered_audio, norm_audio)

            sonic_audio = output_path.rsplit(".", 1)[0] + "_sonic.wav"
            mastered_audio = voice_humanizer.inject_sonic_brand_watermark(mastered_audio, sonic_audio)
            print("  [Composer] [VoiceHumanizer] 0.4s Sonic Brand Chime Watermark injected (Item 87).")

            if enable_section2_filters:
                jitter_audio = output_path.rsplit(".", 1)[0] + "_jitter.wav"
                mastered_audio = voice_humanizer.apply_audio_jitter(
                    mastered_audio, jitter_audio, min_speed=0.985, max_speed=1.015
                )
                print("  [Composer] [VoiceHumanizer] Ses hızı mikro dalgalanması uygulandı (Madde 101).")
        except Exception as vhe:
            print(f"  [Composer] Voice humanizer notice: {vhe}")
            mastered_audio = audio_path

    audio_dur = 0.0
    try:
        with wave.open(mastered_audio, "rb") as w:
            audio_dur = w.getnframes() / float(w.getframerate())
    except Exception:
        if audio_premastered:
            audio_dur = 0.0
        else:
            ffprobe = shutil.which("ffprobe")
            if ffprobe:
                try:
                    probe_out = subprocess.check_output(
                        [
                            ffprobe, "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", mastered_audio,
                        ],
                        text=True,
                        timeout=15,
                    ).strip()
                    audio_dur = float(probe_out)
                except Exception as e:
                    print(f"    Audio duration read error: {e}")
            else:
                print("    Audio duration read error: ffprobe not found")

    total_scene_dur = sum(sc.get("duration", 7) for sc in scene_clips)
    if (not audio_premastered) and audio_dur > 2.0 and total_scene_dur > 0:
        ratio = audio_dur / total_scene_dur
        if abs(ratio - 1.0) > 0.06:
            scale = audio_dur / total_scene_dur
            print(
                f"  [Composer] Ses doğal kaldı — sahne süreleri sese göre "
                f"(×{scale:.2f}, ses {audio_dur:.1f}s). Hızlandırma yok."
            )
            for sc in scene_clips:
                sc["duration"] = round(sc.get("duration", 7) * scale, 2)

    processed_audio = mastered_audio
    if getattr(cfg_mod, "ENABLE_SFX", True):
        scene_durs = [sc.get("duration", 7) for sc in scene_clips]
        sfx_audio = output_path.rsplit(".", 1)[0] + "_sfx_audio.wav"
        processed_audio = add_sfx_fn(
            mastered_audio, scene_durs, sfx_audio,
            sfx_volume=getattr(cfg_mod, "SFX_VOLUME", 0.20),
            scene_clips=scene_clips, word_timings=word_timings,
        )

        try:
            from voice_humanizer import voice_humanizer, sync_riser_whoosh_transitions
            scene_cut_times = []
            cur_time = 0.0
            for sc in scene_clips[:-1]:
                cur_time += sc.get("duration", 7)
                scene_cut_times.append(round(cur_time, 3))
            if scene_cut_times:
                riser_audio = output_path.rsplit(".", 1)[0] + "_risers.wav"
                processed_audio = sync_riser_whoosh_transitions(processed_audio, scene_cut_times, riser_audio)
                print(
                    f"  [Composer] [Item 155] Sahne geçişleri için "
                    f"{len(scene_cut_times)} adet 250ms Riser/Whoosh senkronize edildi."
                )

            has_quiz = any(
                "quiz" in str(sc.get("scene_description", "")).lower()
                or "soru" in str(sc.get("scene_description", "")).lower()
                for sc in scene_clips
            )
            if has_quiz:
                from voice_humanizer import inject_quiz_ding, inject_quiz_buzzer
                from voice.audio_dsp import inject_quiz_thinking_gap, inject_pre_answer_tension_gap
                gap_insert_at = None
                elapsed_gap = 0.0
                for sc in scene_clips:
                    narr_g = str(sc.get("narration", ""))
                    combined_g = (narr_g + " " + str(sc.get("scene_description", ""))).lower()
                    is_q = "?" in narr_g or any(w in combined_g for w in ("soru", "quiz", "question", "cevapla"))
                    is_ans = any(w in combined_g for w in (
                        "doğru", "yanlış", "cevap a", "cevap b", "cevap c", "cevap d",
                        "correct", "wrong", "kazand", "kaybett", "bilemedin",
                    ))
                    if is_q and not is_ans:
                        gap_insert_at = elapsed_gap + float(sc.get("duration", 7.0)) * 0.9
                        break
                    elapsed_gap += float(sc.get("duration", 7.0))
                if gap_insert_at is not None:
                    gap_audio = output_path.rsplit(".", 1)[0] + "_quiz_gap.wav"
                    processed_audio = inject_quiz_thinking_gap(
                        processed_audio, gap_audio, gap_seconds=3.0, insert_at_sec=gap_insert_at
                    )
                    print(f"  [Composer] [Item 197] Quiz düşünme boşluğu (3.0s) t={gap_insert_at:.2f}s eklendi.")

                elapsed_254 = 0.0
                for sc_idx, sc in enumerate(scene_clips):
                    narr_254 = str(sc.get("narration", ""))
                    if "?" in narr_254 and sc_idx + 1 < len(scene_clips):
                        next_narr = str(scene_clips[sc_idx + 1].get("narration", ""))
                        if next_narr and "?" not in next_narr[:20]:
                            gap_at = elapsed_254 + float(sc.get("duration", 7.0)) * 0.92
                            tension_audio = output_path.rsplit(".", 1)[0] + "_tension_gap.wav"
                            processed_audio = inject_pre_answer_tension_gap(
                                processed_audio, tension_audio, gap_seconds=0.5, insert_at_sec=gap_at
                            )
                            print(f"  [Composer] [Item 254] Pre-answer tension gap (0.5s) t={gap_at:.2f}s eklendi.")
                            break
                    elapsed_254 += float(sc.get("duration", 7.0))

                elapsed_q = 0.0
                for sc in scene_clips:
                    desc_q = str(sc.get("scene_description", "")).lower()
                    narr_q = str(sc.get("narration", "")).lower()
                    if any(w in desc_q or w in narr_q for w in ("doğru", "tebrik", "cevap a", "cevap b", "cevap c", "cevap d", "correct", "kazand")):
                        ding_out = output_path.rsplit(".", 1)[0] + "_ding.wav"
                        processed_audio = inject_quiz_ding(processed_audio, ding_out, timestamp_sec=elapsed_q + 0.15, volume=0.50)
                        print(f"  [Composer] [Item 167] Quiz doğru cevaba 1800Hz kristal 'Ding' SFX mikslendi (t={elapsed_q+0.15:.2f}s).")
                        break
                    elif any(w in desc_q or w in narr_q for w in ("yanlış", "hata", "kaybett", "wrong", "bilemedin")):
                        buzz_out = output_path.rsplit(".", 1)[0] + "_buzzer.wav"
                        processed_audio = inject_quiz_buzzer(processed_audio, buzz_out, timestamp_sec=elapsed_q + 0.15, volume=0.45)
                        print(f"  [Composer] [Item 168] Quiz yanlış cevaba 120Hz testere dişi 'Buzzer' SFX mikslendi (t={elapsed_q+0.15:.2f}s).")
                        break
                    elapsed_q += float(sc.get("duration", 7.0))

            has_mystery = any(
                any(k in str(sc.get(key, "")).lower() for k in ("gizem", "mystery", "antik", "esrarengiz", "legend", "sırr"))
                for sc in scene_clips for key in ("narration", "scene_description", "keyword")
            )
            if has_mystery:
                rev_audio = output_path.rsplit(".", 1)[0] + "_rev_reverb.wav"
                processed_audio = voice_humanizer.apply_reverse_reverb_whisper(processed_audio, rev_audio, tail_sec=0.30)
                print("  [Composer] [Item 176] Gizem nişine reverse reverb (0.3s) mikslendi.")

            niche_hint_196 = (niche_id or title or "").lower()
            has_news = any(
                any(k in str(sc.get(key, "")).lower() for k in (
                    "haber", "news", "son dakika", "flaş", "breaking", "deprem", "kaza"
                ))
                for sc in scene_clips for key in ("narration", "scene_description", "keyword")
            ) or any(k in niche_hint_196 for k in ("news", "haber", "flash", "1_news"))
            if has_news:
                from voice.audio_dsp import apply_news_rapid_cadence
                news_audio = output_path.rsplit(".", 1)[0] + "_news_cadence.wav"
                processed_audio = apply_news_rapid_cadence(
                    processed_audio, news_audio, tempo=1.12, max_pause_sec=0.09
                )
                print("  [Composer] [Item 196] Haber dili hızlandırması (90ms gap + atempo 1.12) uygulandı.")

            niche_hint_181 = (niche_id or title or "").lower()
            has_historic = any(
                any(k in str(sc.get(key, "")).lower() for k in (
                    "tarih", "history", "nostalj", "vintage", "eski", "antik", "retro", "plak", "vinyl", "analog"
                ))
                for sc in scene_clips for key in ("narration", "scene_description", "keyword")
            ) or any(k in niche_hint_181 for k in ("tarih", "history", "nostalj", "vintage", "retro", "histor"))
            if has_historic:
                vinyl_audio = output_path.rsplit(".", 1)[0] + "_vinyl_crackle.wav"
                processed_audio = voice_humanizer.inject_vinyl_crackle_layer(
                    processed_audio, vinyl_audio, volume_db=-28.0
                )
                print("  [Composer] [Item 181] Tarihi/nostaljik nişe vinil cızırtısı (-28dB) mikslendi.")

            from voice.script_humanizer import SHOCK_CUE_PHRASES
            shock_times = []
            elapsed_shock = 0.0
            for sc in scene_clips:
                narr_q = str(sc.get("narration", "")).lower()
                for phrase in SHOCK_CUE_PHRASES:
                    if phrase in narr_q:
                        shock_times.append(round(elapsed_shock + 0.35, 3))
                elapsed_shock += float(sc.get("duration", 7.0))
            if shock_times:
                shock_audio = output_path.rsplit(".", 1)[0] + "_shock_silence.wav"
                processed_audio = voice_humanizer.apply_shock_silence_cut(processed_audio, shock_audio, shock_times, silence_sec=0.20)
                print(f"  [Composer] [Item 179] {len(shock_times)} adet şok sessizlik kesintisi uygulandı.")

            if audio_dur > 40.0:
                mono_pause_audio = output_path.rsplit(".", 1)[0] + "_monologue_pause.wav"
                processed_audio = voice_humanizer.inject_monologue_pause_and_swallow(
                    processed_audio, mono_pause_audio, interval_seconds=40.0
                )
                print("  [Composer] [Item 177] Uzun monologa 40s aralıklı yutkunma/duraksama eklendi.")

            phone_audio = output_path.rsplit(".", 1)[0] + "_phone_quote.wav"
            from voice.audio_dsp import apply_telephone_filter_on_quote_scenes
            processed_audio = apply_telephone_filter_on_quote_scenes(
                processed_audio, phone_audio, scene_clips
            )
            if processed_audio.endswith("_phone_quote.wav"):
                print("  [Composer] [Item 163] Alıntı/telefon sahnelerine Lo-Fi bandpass uygulandı.")

            niche_hint_audio = (niche_id or title or "").lower()
            scene_blob = " ".join(
                str(sc.get(key, "")) for sc in scene_clips for key in ("narration", "scene_description", "keyword")
            ).lower()
            combined_audio = f"{niche_hint_audio} {scene_blob}"

            if any(k in combined_audio for k in ("stoic", "felsefe", "philosophy", "duygusal", "poetry", "dini", "manevi", "tarih")):
                from voice.acoustic_assets import inject_dramatic_piano_layer
                piano_audio = output_path.rsplit(".", 1)[0] + "_piano182.wav"
                processed_audio = inject_dramatic_piano_layer(processed_audio, piano_audio, timestamp_sec=1.2, volume=0.28)
                print("  [Composer] [Item 182] Dramatik piyano katmanı mikslendi.")

            if any(k in combined_audio for k in ("yapay zeka", "ai", "cyber", "tech", "teknoloji", "gelecek", "robot")):
                from voice.acoustic_assets import inject_cyberpunk_synth_bass
                synth_audio = output_path.rsplit(".", 1)[0] + "_synth183.wav"
                processed_audio = inject_cyberpunk_synth_bass(processed_audio, synth_audio, timestamp_sec=0.0, volume=0.22)
                print("  [Composer] [Item 183] Cyberpunk synth bass mikslendi.")

            if any(k in combined_audio for k in ("haber", "news", "sokak", "street", "borsa", "finans", "kalabalık", "crowd")):
                from voice.acoustic_assets import inject_room_ambience
                crowd_audio = output_path.rsplit(".", 1)[0] + "_crowd188.wav"
                processed_audio = inject_room_ambience(processed_audio, crowd_audio, volume=0.08)
                print("  [Composer] [Item 188] Oda/kalabalık ambiyansı mikslendi.")

            if bool(extra_kwargs.get("enable_room_tone", False)) and any(k in combined_audio for k in (
                "katedral", "cathedral", "manevi", "dini", "spiritual", "epic", "temple", "ibadet", "dua"
            )):
                from voice.audio_dsp import apply_acoustic_reverb_chamber
                rev_audio = output_path.rsplit(".", 1)[0] + "_reverb191.wav"
                processed_audio = apply_acoustic_reverb_chamber(processed_audio, rev_audio, room_type="cathedral")
                print("  [Composer] [Item 191] Akustik yankı odası uygulandı.")

            if any(k in combined_audio for k in (
                "epic", "trailer", "evren", "cosmos", "hans", "sinema", "film", "destansı", "cosmic"
            )):
                from voice.audio_dsp import apply_epic_trailer_deep_voice
                epic_audio = output_path.rsplit(".", 1)[0] + "_epic195.wav"
                processed_audio = apply_epic_trailer_deep_voice(processed_audio, epic_audio, pitch_ratio=0.88)
                print("  [Composer] [Item 195] Derin anlatıcı (trailer) sesi uygulandı.")
        except Exception as se:
            print(f"  [Composer] Audio SFX layers notice: {se}")

    if cancel_check and cancel_check():
        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    final_audio = processed_audio
    chosen_bgm = bgm_track or getattr(cfg_mod, "DEFAULT_BGM_TRACK", "")
    if not chosen_bgm:
        try:
            chosen_bgm, mood = select_auto_bgm_fn(scene_clips, title, niche_id)
            if chosen_bgm:
                print(f"  [BGM] Auto mood={mood} track={chosen_bgm}")
        except Exception as err:
            print(
                f"  [BGM] Mood selection failed; using niche fallback: {err}",
                flush=True,
            )
    if not chosen_bgm and getattr(cfg_mod, "ENABLE_BGM", True):
        from bgm_manager import match_bgm_track_to_niche
        niche_hint = (niche_id or title or "") + " " + " ".join(str(s.get("scene_description", "")) for s in scene_clips[:2])
        matched_track = match_bgm_track_to_niche(niche_hint)
        chosen_bgm = os_mod.path.basename(matched_track) if matched_track else ""

    if chosen_bgm and getattr(cfg_mod, "ENABLE_BGM", True):
        bgm_p = get_bgm_fn(chosen_bgm)
        if bgm_p:
            if audio_dur > 6.0:
                from bgm_manager import apply_outro_music_swell
                swelled_bgm = output_path.rsplit(".", 1)[0] + "_bgm_swell.wav"
                swelled = apply_outro_music_swell(bgm_p, swelled_bgm, total_duration=audio_dur)
                if swelled and os_mod.path.exists(swelled):
                    bgm_p = swelled
                    print("  [Composer] [Item 185] BGM outro swell (+3.5dB son 5s) hazırlandı.")

            if enable_section2_filters:
                scene_clips = align_beats_fn(scene_clips, bgm_p)
                print("  [Composer] [BGM] Sahne kesimleri müzik vuruşlarına (beat-sync) kilitlendi (Madde 102).")

            vol = bgm_volume if bgm_volume is not None else getattr(cfg_mod, "BGM_VOLUME", 0.12)
            mixed_audio = output_path.rsplit(".", 1)[0] + "_mixed_audio.wav"
            tape_stop_times = []
            elapsed = 0.0
            for scene in scene_clips:
                scene_text = " ".join(str(scene.get(key, "")) for key in ("narration", "scene_description")).lower()
                if any(term in scene_text for term in ("ama", "fakat", "tersine", "ancak")):
                    tape_stop_times.append(elapsed)
                elapsed += float(scene.get("duration", 0.0))

            intro_blast = 0.85 if bool(extra_kwargs.get("enable_intro_whoosh", False)) else 0.0
            final_audio = mix_bgm_fn(
                processed_audio, bgm_p, mixed_audio, volume=vol,
                tape_stop_times=tape_stop_times, allow_fade_out=False,
                intro_blast=intro_blast,
            )
            if not final_audio or not os_mod.path.exists(final_audio):
                final_audio = processed_audio
            else:
                if intro_blast > 0:
                    print("  [Composer] [Item 180] Müzik giriş vuruşu (Whoosh anında) + ducking uygulandı.")
                else:
                    print(f"  [Composer] Müzik mikslendi (Vokal ducking: {vol:.2f}, tape-stop: {len(tape_stop_times)} durak).")

            if final_audio and os_mod.path.exists(final_audio):
                from voice_humanizer import lock_bass_frequencies_to_mono
                phase_aligned_audio = output_path.rsplit(".", 1)[0] + "_phase_aligned.wav"
                final_audio = lock_bass_frequencies_to_mono(final_audio, phase_aligned_audio, cutoff_hz=120.0)
                print("  [Composer] [Item 170] Ses katmanları faz uyumu (Phase Alignment: Mono Bas Kilidi <120Hz) uygulandı.")

            try:
                from voice_humanizer import voice_humanizer as _vh
                mobile_report = _vh.run_mobile_device_audio_check(final_audio, bgm_p)
                print(
                    f"  [Composer] [Item 174] Mobil audit: {mobile_report.get('status', 'N/A')} "
                    f"(score={mobile_report.get('mobile_readiness_score', '?')})"
                )
            except Exception:
                pass

    return processed_audio, final_audio, scene_clips
