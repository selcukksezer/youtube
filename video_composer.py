"""
Video composer — MoviePy (video only) + ffmpeg (audio + karaoke subs).
3-tier fallback: ASS karaoke → SRT styled → no subs.
"""
import os, subprocess, platform, gc, shutil
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, concatenate_videoclips, vfx

try:
    import cv2
    cv2.ocl.setUseOpenCL(False)
    cv2.setNumThreads(2)
except ImportError:
    cv2 = None  # optional — install opencv-python; motion effects use PIL fallback
except Exception:
    pass

import config
from subtitle_generator import create_karaoke_subtitles, create_srt_file
from bgm_manager import get_bgm_path, mix_narration_and_bgm, mix_intro_punch_bgm, align_scenes_to_bgm_beats
from sfx_manager import add_sfx_to_narration
from effects_engine import (
    create_split_screen_clip, apply_anti_duplicate,
    apply_ken_burns, overlay_watermark, extract_frame0_thumbnail,
    apply_smart_crop, apply_horizontal_flip, apply_speed_ramp,
    enforce_3s_broll_rule, apply_color_grading_jitter,
    apply_multi_layer_overlay, inject_pixel_noise, get_diversified_fps,
    apply_section2_anti_reused_pipeline, overlay_graphic_badge, get_unsharp_filter,
    get_ffmpeg_static_grain_filter, overlay_micro_brand_signature,
    get_ffmpeg_vignette_filter, apply_pip_overlay,
    apply_handheld_camera_shake, apply_mask_wipe_transition,
    apply_out_of_focus_reveal, apply_censored_blur_bait, apply_end_card_to_video, clean_video_metadata,
    apply_neon_countdown_overlay, apply_slow_motion_highlight,
    apply_broll_speed_boost, apply_impact_screen_shake, apply_micro_zoom_out,
    apply_particle_overlay, apply_heartbeat_zoom, apply_speaker_avatar_overlay,
    build_emoji_events_from_timings, generate_emoji_subtitle_overlay,
    apply_alternating_motion, apply_ui_element_overlay,
    apply_dynamic_progress_bar, apply_sticky_hook_banner_overlay,
    apply_micro_animated_sticker_overlay, apply_neon_curiosity_opening_graphic,
    get_color_grading_ffmpeg_filter,
    apply_scene_brightness_alternation,
    apply_opening_pattern_interrupt,
    apply_color_splash_moviepy,
    apply_affiliate_3d_mockup,
    apply_share_cta_overlay,
    apply_bookmark_cta_overlay,
    apply_corner_radius_to_clip,
    apply_keyword_white_flash_overlay,
    apply_infinite_spiral_overlay,
    apply_time_tunnel_overlay,
    apply_hybrid_render_overlay,
    apply_fluid_gradient_background,
    apply_micro_resolution_crop,
)
from viral_retention_engine import ViralRetentionEngine

from proglog import ProgressBarLogger

def cleanup_stray_ffmpeg_processes():
    """Kullanıcı render iptal ettiğinde veya işlem bittiğinde asılı kalan FFmpeg okuyucularını temizler."""
    try:
        if platform.system() == "Windows":
            subprocess.run("taskkill /F /IM ffmpeg-win*.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

class MoviePyProgressLogger(ProgressBarLogger):
    def __init__(self, callback=None, cancel_check=None):
        super().__init__(init_state=None, bars=None, ignored_bars=None, logged_bars='all', min_time_interval=0, ignore_bars_under=0)
        self.ui_callback = callback
        self.cancel_check = cancel_check
        self.last_log_time = 0.0
        self.last_frame_pct = -1
        self.print_messages = False

    def callback(self, **changes):
        pass

    def log_message(self, message):
        pass

    def bars_callback(self, bar, attr, value, old_value=None):
        if self.cancel_check and self.cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
        if bar == 't' and attr == 'index':
            total = self.bars['t'].get('total', 0)
            if total > 0:
                import time
                now = time.time()
                frame_pct = int((value / total) * 100)
                # Canlı ilerleme: Her 0.8 saniyede bir veya her %2 karede bir hem terminale hem UI'a bas
                if (now - self.last_log_time >= 0.8) or (frame_pct >= self.last_frame_pct + 2) or value >= total:
                    self.last_log_time = now
                    self.last_frame_pct = frame_pct
                    # overall_pct: export aşaması %75-98 arası (daha geniş pencere)
                    overall_pct = int(75 + (value / total) * 23)
                    msg = f"[FFmpeg Export] %{frame_pct} ({int(value)}/{int(total)} kare kodlandı)"
                    print(f"  [Composer] {msg}", flush=True)
                    if self.ui_callback:
                        try:
                            self.ui_callback(overall_pct, msg)
                        except Exception:
                            pass

def compose_video(scene_clips, audio_path, word_timings, output_path, title="", 
                  bgm_track=None, bgm_volume=None, subtitle_opts=None,
                  progress_callback=None, cancel_check=None,
                  split_screen=False, anti_duplicate=True, watermark_path=None,
                  enable_ken_burns=True, enable_section2_filters=True, gameplay_path=None,
                  niche_id="", audio_premastered=False, retention_metadata=None,
                  hybrid_niche="", hybrid_render_overlay=None):
    print(f"\n  [Composer] Building video with 500-Item Optimization Pipeline (Items 71-79)...")
    W, H = getattr(config, "get_target_resolution", lambda: (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))()
    print(f"  [Composer] Hedef Çözünürlük: {W}x{H} (Mod: {getattr(config, 'RENDER_RESOLUTION_MODE', '1080p')})", flush=True)
    _safe = getattr(config, "RENDER_SAFE_MODE", True)
    if _safe:
        print("  [Composer] ⚠ RENDER_SAFE_MODE=true — ağır overlay/efektler bypass (Tam Kural için false yap)", flush=True)
    else:
        print("  [Composer] RENDER_SAFE_MODE=false — full overlays active", flush=True)

    if cancel_check and cancel_check():
        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    # Apply Voice Humanizer (Studio Warmth EQ + -14 LUFS EBU R128 Loudness) (Items 150-162)
    # Skip when DirectorPlan AudioMaster already produced the final bed.
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

            # Item 193: segment RMS leveller (pre-LUFS)
            consistent_audio = output_path.rsplit(".", 1)[0] + "_consistent.wav"
            from voice.audio_dsp import apply_voice_level_consistency
            mastered_audio = apply_voice_level_consistency(mastered_audio, consistent_audio)
            print("  [Composer] [VoiceHumanizer] Voice level consistency applied (Item 193).")

            # Item 172: Noise gate — konuşma aralarındaki dijital artıkları kes
            gated_audio = output_path.rsplit(".", 1)[0] + "_gated.wav"
            mastered_audio = voice_humanizer.apply_noise_gate(mastered_audio, gated_audio)
            print("  [Composer] [VoiceHumanizer] Noise gate uygulandı (Madde 172).")

            breaths_audio = output_path.rsplit(".", 1)[0] + "_breaths.wav"
            mastered_audio = voice_humanizer.inject_natural_breaths(eq_audio, breaths_audio, interval_seconds=5.0)
            print("  [Composer] [VoiceHumanizer] Natural breath layer injected every ~5s (Item 141).")

            intro_audio = output_path.rsplit(".", 1)[0] + "_intro112.wav"
            from voice_humanizer import prepend_whoosh_ding_to_narration
            mastered_audio = prepend_whoosh_ding_to_narration(mastered_audio, intro_audio)
            if word_timings:
                for wt in word_timings:
                    wt["offset"] = wt.get("offset", 0.0) + 0.2
            print("  [Composer] [VoiceHumanizer] Item 112 Whoosh+Ding intro uygulandı.")

            room_audio = output_path.rsplit(".", 1)[0] + "_room.wav"
            from voice_humanizer import mix_pink_noise_into_narration
            mastered_audio = mix_pink_noise_into_narration(mastered_audio, room_audio, noise_db=-32.0, noise_type="room")
            print("  [Composer] [VoiceHumanizer] Light room ambience applied (Item 145).")

            norm_audio = output_path.rsplit(".", 1)[0] + "_norm.wav"
            mastered_audio = voice_humanizer.normalize_ebu_r128(mastered_audio, norm_audio)

            sonic_audio = output_path.rsplit(".", 1)[0] + "_sonic.wav"
            mastered_audio = voice_humanizer.inject_sonic_brand_watermark(mastered_audio, sonic_audio)
            print("  [Composer] [VoiceHumanizer] 0.4s Sonic Brand Chime Watermark injected (Item 87).")

            if enable_section2_filters:
                jitter_audio = output_path.rsplit(".", 1)[0] + "_jitter.wav"
                mastered_audio = voice_humanizer.apply_audio_jitter(mastered_audio, jitter_audio, min_speed=0.985, max_speed=1.015)
                print("  [Composer] [VoiceHumanizer] Ses hızı mikro dalgalanması uygulandı (Madde 101).")
        except Exception as vhe:
            print(f"  [Composer] Voice humanizer notice: {vhe}")
            mastered_audio = audio_path

    # Measure exact narration audio duration (wave → ffprobe; no scipy hard dep)
    import wave
    audio_dur = 0.0
    try:
        with wave.open(mastered_audio, "rb") as w:
            audio_dur = w.getnframes() / float(w.getframerate())
    except Exception:
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

    # When premastered, Director already fitted timeline — skip composer re-fit
    total_scene_dur = sum(sc.get("duration", 7) for sc in scene_clips)
    if (not audio_premastered) and audio_dur > 2.0 and total_scene_dur > 0:
        ratio = audio_dur / total_scene_dur
        if ratio > 1.06:
            from voice.audio_dsp import fit_audio_to_duration
            fitted_audio = output_path.rsplit(".", 1)[0] + "_fitted.wav"
            prev_dur = audio_dur
            mastered_audio, audio_dur, speed_factor = fit_audio_to_duration(
                mastered_audio, fitted_audio, total_scene_dur, tolerance=0.06
            )
            if speed_factor > 1.01 and word_timings:
                for wt in word_timings:
                    wt["offset"] = wt.get("offset", 0.0) / speed_factor
                    wt["duration"] = wt.get("duration", 0.0) / speed_factor
            print(
                f"  [Composer] Ses senaryo bütçesine uyarlandı "
                f"({prev_dur:.1f}s → {audio_dur:.1f}s, hedef {total_scene_dur:.1f}s, ×{ratio:.2f} hızlandırıldı)."
            )
        elif ratio < 0.94:
            scale = audio_dur / total_scene_dur
            print(f"  [Composer] Kısa ses — sahne süreleri ayarlanıyor (×{scale:.2f}, Audio: {audio_dur:.1f}s)...")
            for sc in scene_clips:
                sc["duration"] = round(sc.get("duration", 7) * scale, 2)

    # Step A: SFX mixing on narration audio (using scaled scene durations for perfect sync)
    processed_audio = mastered_audio
    if getattr(config, "ENABLE_SFX", True):
        scene_durs = [sc.get("duration", 7) for sc in scene_clips]
        sfx_audio = output_path.rsplit(".", 1)[0] + "_sfx_audio.wav"
        processed_audio = add_sfx_to_narration(
            mastered_audio, scene_durs, sfx_audio,
            sfx_volume=getattr(config, "SFX_VOLUME", 0.20),
            scene_clips=scene_clips, word_timings=word_timings
        )

        # Madde 155: Riser/Whoosh — sahne geçişlerinde (add_sfx ile çiftlenmesin diye whoosh oradan kaldırıldı)
        # Madde 154/157/158/159: add_sfx_to_narration içinde sahne içeriğine göre uygulanır
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
                print(f"  [Composer] [Item 155] Sahne geçişleri için {len(scene_cut_times)} adet 250ms Riser/Whoosh senkronize edildi.")

            # Madde 167 & 168: Quiz Doğru Cevap Ding (1800Hz Kristal Zil) ve Yanlış Cevap Buzzer (120Hz Testere Dişi)
            has_quiz = any("quiz" in str(sc.get("scene_description", "")).lower() or "soru" in str(sc.get("scene_description", "")).lower() for sc in scene_clips)
            if has_quiz:
                from voice_humanizer import inject_quiz_ding, inject_quiz_buzzer
                from voice.audio_dsp import inject_quiz_thinking_gap
                gap_insert_at = None
                elapsed_gap = 0.0
                for sc in scene_clips:
                    narr_g = str(sc.get("narration", ""))
                    combined_g = (narr_g + " " + str(sc.get("scene_description", ""))).lower()
                    is_q = "?" in narr_g or any(w in combined_g for w in ("soru", "quiz", "question", "cevapla"))
                    is_ans = any(w in combined_g for w in (
                        "doğru", "yanlış", "cevap a", "cevap b", "cevap c", "cevap d",
                        "correct", "wrong", "kazand", "kaybett", "bilemedin"
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

                # Item 254: Soru-cevap arası 0.5s gerilim boşluğu (quiz dışı soru→cevap geçişleri)
                from voice.audio_dsp import inject_pre_answer_tension_gap
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
            # Madde 176: Gizem/antik nişte cümle sonuna 0.3s reverse reverb
            has_mystery = any(
                any(k in str(sc.get(key, "")).lower() for k in ("gizem", "mystery", "antik", "esrarengiz", "legend", "sırr"))
                for sc in scene_clips for key in ("narration", "scene_description", "keyword")
            )
            if has_mystery:
                rev_audio = output_path.rsplit(".", 1)[0] + "_rev_reverb.wav"
                processed_audio = voice_humanizer.apply_reverse_reverb_whisper(processed_audio, rev_audio, tail_sec=0.30)
                print("  [Composer] [Item 176] Gizem nişine reverse reverb (0.3s) mikslendi.")

            # Madde 196: Haber/son dakika nişinde 90ms gap + hızlı tempo
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

            # Madde 181: Tarihi/nostaljik nişte arka plana -28dB vinil plak cızırtısı
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

            # Madde 179: Şok ifadelerinde 0.2s mutlak sessizlik
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

            # Madde 177: 40s+ monologlarda yutkunma/duraksama katmanı
            if audio_dur > 40.0:
                mono_pause_audio = output_path.rsplit(".", 1)[0] + "_monologue_pause.wav"
                processed_audio = voice_humanizer.inject_monologue_pause_and_swallow(
                    processed_audio, mono_pause_audio, interval_seconds=40.0
                )
                print("  [Composer] [Item 177] Uzun monologa 40s aralıklı yutkunma/duraksama eklendi.")

            # Item 163: telefon/alıntı sahnelerinde bandpass (tüm narration değil)
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

            if any(k in combined_audio for k in (
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

    # Step B: Check for BGM mixing (Items 166, 169, 170)
    final_audio = processed_audio
    chosen_bgm = bgm_track or getattr(config, "DEFAULT_BGM_TRACK", "")
    if not chosen_bgm and getattr(config, "ENABLE_BGM", True):
        # Item 169: Müzik BPM Eşleştirmesi (Niş Temposu: Motivasyon 120-130 BPM, Felsefe/Gizem 70-85 BPM)
        from bgm_manager import match_bgm_track_to_niche
        niche_hint = (niche_id or title or "") + " " + " ".join(str(s.get("scene_description", "")) for s in scene_clips[:2])
        matched_track = match_bgm_track_to_niche(niche_hint)
        chosen_bgm = os.path.basename(matched_track) if matched_track else ""

    if chosen_bgm and getattr(config, "ENABLE_BGM", True):
        bgm_p = get_bgm_path(chosen_bgm)
        if bgm_p:
            # Item 185: son 5s BGM swell (+3.5dB) before mix
            if audio_dur > 6.0:
                from bgm_manager import apply_outro_music_swell
                swelled_bgm = output_path.rsplit(".", 1)[0] + "_bgm_swell.wav"
                swelled = apply_outro_music_swell(bgm_p, swelled_bgm, total_duration=audio_dur)
                if swelled and os.path.exists(swelled):
                    bgm_p = swelled
                    print("  [Composer] [Item 185] BGM outro swell (+3.5dB son 5s) hazırlandı.")

            # Item 102: BGM Beat-Syncing
            if enable_section2_filters:
                scene_clips = align_scenes_to_bgm_beats(scene_clips, bgm_p)
                print("  [Composer] [BGM] Sahne kesimleri müzik vuruşlarına (beat-sync) kilitlendi (Madde 102).")

            vol = bgm_volume if bgm_volume is not None else getattr(config, "BGM_VOLUME", 0.12)
            mixed_audio = output_path.rsplit(".", 1)[0] + "_mixed_audio.wav"
            tape_stop_times = []
            elapsed = 0.0
            for scene in scene_clips:
                scene_text = " ".join(str(scene.get(key, "")) for key in ("narration", "scene_description")).lower()
                if any(term in scene_text for term in ("ama", "fakat", "tersine", "ancak")):
                    tape_stop_times.append(elapsed)
                elapsed += float(scene.get("duration", 0.0))
            
            # Item 180: İlk 1s müzik %100 vuruşu + anında ducking; Item 166: fade-out yok
            punch_audio = output_path.rsplit(".", 1)[0] + "_intro_punch.wav"
            final_audio = mix_intro_punch_bgm(
                processed_audio, bgm_p, punch_audio,
                intro_blast_sec=1.0, blast_volume=0.85, ducked_volume=vol
            )
            if not final_audio or not os.path.exists(final_audio):
                final_audio = mix_narration_and_bgm(
                    processed_audio, bgm_p, mixed_audio, volume=vol,
                    tape_stop_times=tape_stop_times, allow_fade_out=False
                )
            else:
                print("  [Composer] [Item 180] Müzik giriş vuruşu (%100 ilk 1s) + ducking uygulandı.")

            # Item 170: Ses Katmanlarının Faz Uyumu (Phase Alignment: Mono Bas Kilidi <120Hz)
            if final_audio and os.path.exists(final_audio):
                from voice_humanizer import lock_bass_frequencies_to_mono
                phase_aligned_audio = output_path.rsplit(".", 1)[0] + "_phase_aligned.wav"
                final_audio = lock_bass_frequencies_to_mono(final_audio, phase_aligned_audio, cutoff_hz=120.0)
                print("  [Composer] [Item 170] Ses katmanları faz uyumu (Phase Alignment: Mono Bas Kilidi <120Hz) uygulandı.")

            # Item 174: Mobil hoparlör mono netlik audit (post-mix advisory log)
            try:
                from voice_humanizer import voice_humanizer as _vh
                mobile_report = _vh.run_mobile_device_audio_check(final_audio, bgm_p)
                print(
                    f"  [Composer] [Item 174] Mobil audit: {mobile_report.get('status', 'N/A')} "
                    f"(score={mobile_report.get('mobile_readiness_score', '?')})"
                )
            except Exception:
                pass


    segs = []
    combined = None
    tmp = output_path.rsplit(".", 1)[0] + "_tmp.mp4"
    ass = output_path.rsplit(".", 1)[0] + ".ass"
    srt = output_path.rsplit(".", 1)[0] + ".srt"

    try:
        cleanup_stray_ffmpeg_processes()
        total_scenes = len(scene_clips)
        for idx, sc in enumerate(scene_clips):
            if cancel_check and cancel_check():
                raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            p, d = sc.get("path"), sc.get("duration", 7)

            if not p or not os.path.exists(p):
                fallback_clip = ColorClip(size=(W, H), color=(15, 15, 25), duration=d)
                segs.append(fallback_clip)
            else:
                try:
                    enable_pip = sc.get("enable_pip", False)
                    pip_path = sc.get("pip_path", None)
                    badge_label = sc.get("badge_label")
                    clip_seg = _prep(
                        p, d, W, H,
                        split_screen=split_screen,
                        enable_section2=enable_section2_filters,
                        badge_label=badge_label,
                        enable_pip=enable_pip,
                        pip_path=pip_path,
                        gameplay_path=gameplay_path
                    )
                    if enable_ken_burns and not enable_section2_filters:
                        # Item 73: Mikro-Zoom (Ken Burns Jitter 1.00x -> 1.04x)
                        clip_seg = apply_ken_burns(clip_seg, zoom_start=1.00, zoom_end=1.04)

                    # Item 99: Dinamik Kamera Sallantısı — tüm sahnelerde (enable_section2)
                    if enable_section2_filters:
                        shake_intensity = 5.0 if sc.get("handheld_shake", True) else 3.5
                        clip_seg = apply_handheld_camera_shake(clip_seg, intensity=shake_intensity)

                    # Item 115: Color splash (4. sahne / dramatik mood)
                    if enable_section2_filters and (
                        idx == 3
                        or sc.get("mood") in ("dramatic", "shock", "tehlike")
                        or sc.get("beat_type") == "climax"
                    ):
                        clip_seg = apply_color_splash_moviepy(clip_seg, keep_hue_center=120.0, tolerance=30.0)

                    # Item 105: Affiliate ürün 3D mock-up overlay
                    if sc.get("affiliate_product") or (
                        enable_section2_filters
                        and idx == max(0, len(scene_clips) - 3)
                        and any(k in (niche_id or title or "").lower() for k in ("affiliate", "wealth", "16_wealth", "monetiz"))
                    ):
                        mockup = apply_affiliate_3d_mockup(p, target_w=W, target_h=H)
                        if mockup:
                            mockup = mockup.set_duration(d).set_position("center")
                            clip_seg = CompositeVideoClip([clip_seg, mockup], size=(W, H))
                            clip_seg.duration = d

                    # Item 100: Görsel Maskeleme (Wipe Transition Mask Overlay)
                    if sc.get("wipe_transition", False) and idx > 0:
                        direction = sc.get("wipe_direction", "horizontal")
                        clip_seg = apply_mask_wipe_transition(clip_seg, direction=direction, transition_dur=0.35)

                    # Item 103: Ekran Dışı Odak (İlk sahnede 0.35s netleşme kancası)
                    if idx == 0 and enable_section2_filters:
                        clip_seg = apply_out_of_focus_reveal(clip_seg, blur_duration=0.35)
                        # Item 211: Merkez censored/blur bait — 3s merak penceresi
                        clip_seg = apply_censored_blur_bait(clip_seg, reveal_after=3.0)
                        # Item 201/237: İlk 1.5s pattern interrupt (glitch/zoom punch)
                        interrupts = ViralRetentionEngine.PATTERN_INTERRUPTS
                        interrupt_type = interrupts[idx % len(interrupts)]["type"]
                        if interrupt_type == "warning_badge":
                            interrupt_type = "glitch_flash"
                        clip_seg = apply_opening_pattern_interrupt(
                            clip_seg, interrupt_type=interrupt_type, duration=1.5
                        )

                    # Item 132: Görsel Hareketi Yön Değişimi (Alternating pan/tilt motion)
                    if enable_section2_filters:
                        clip_seg = apply_alternating_motion(clip_seg, scene_index=idx)

                    # Item 272: Karanlık↔parlak sahne alternasyonu
                    if enable_section2_filters:
                        clip_seg = apply_scene_brightness_alternation(clip_seg, scene_index=idx)

                    # Item 231: Slow-motion vurgu (climax/cutaway sahnelerde)
                    if sc.get("slow_motion_highlight") or (
                        enable_section2_filters and sc.get("is_visual_cutaway")
                    ):
                        clip_seg = apply_slow_motion_highlight(clip_seg, speed_factor=0.5)

                    # Item 245: B-roll hızlandırma (cutaway sahnelerde 1.5x)
                    if enable_section2_filters and sc.get("is_visual_cutaway"):
                        clip_seg = apply_broll_speed_boost(clip_seg, speed_factor=1.5)

                    # Item 243 / 273: Patlama sarsıntısı veya ses-görsel ters uyum şoku
                    if enable_section2_filters and (
                        sc.get("impact_shake")
                        or sc.get("audio_visual_contrast")
                        or sc.get("slow_motion_highlight")
                    ):
                        clip_seg = apply_impact_screen_shake(clip_seg, intensity=14.0, duration=0.35)

                    # Item 253: Cümle sonu mikro zoom-out
                    if enable_section2_filters and idx > 0:
                        clip_seg = apply_micro_zoom_out(clip_seg, zoom_start=1.04, zoom_end=1.00)

                    segs.append(clip_seg)
                    print(f"  [Composer] Sahne #{idx+1}/{total_scenes} hazırlandı ({d:.1f}s).", flush=True)
                except Exception as e:
                    print(f"    Clip error on scene #{idx+1}: {e}", flush=True)
                    fallback_clip = ColorClip(size=(W, H), color=(15, 15, 25), duration=d)
                    segs.append(fallback_clip)

            if progress_callback:
                seg_pct = int(10 + ((idx + 1) / total_scenes) * 15)
                progress_callback(seg_pct, f"Sahneler hazırlandı ({idx + 1}/{total_scenes})...")

        if not segs:
            return ""

        # Concatenate sequentially with method="chain" (zero double-encoding, low memory, fast single pass)
        combined = concatenate_videoclips(segs, method="chain")

        if enable_section2_filters and not getattr(config, 'RENDER_SAFE_MODE', True):
            emoji_events = build_emoji_events_from_timings(word_timings, scene_clips)
            if emoji_events:
                emoji_overlay = generate_emoji_subtitle_overlay(
                    W, H, combined.duration, emoji_events, fps=combined.fps or config.FPS
                )
                if emoji_overlay:
                    combined = CompositeVideoClip([combined, emoji_overlay], size=(W, H))
                    combined.duration = sum(float(sc.get("duration", 3.0)) for sc in scene_clips)
            combined = apply_heartbeat_zoom(combined, bpm=60.0)
            combined = apply_particle_overlay(combined, particle_type="spark", particle_count=30)
            combined = apply_speaker_avatar_overlay(combined, avatar_size=96)
        elif getattr(config, 'RENDER_SAFE_MODE', True):
            print("  [Composer] [Item 125] Emoji animasyon katmanı: RENDER_SAFE_MODE aktif, bypass edildi.")

        if anti_duplicate and not getattr(config, 'RENDER_SAFE_MODE', True):
            print("  [Composer] Applying anti-duplicate filter (Item 50)...")
            combined = apply_anti_duplicate(combined)
        elif anti_duplicate:
            print("  [Composer] [Item 50] Anti-duplicate: FFmpeg GPU renk filtreleme aktif, MoviePy CPU bypass edildi.")

        if watermark_path and os.path.exists(watermark_path):
            print("  [Composer] Overlaying channel watermark logo (Item 381)...")
            combined = overlay_watermark(combined, watermark_path)

        if not getattr(config, 'RENDER_SAFE_MODE', True):
            combined = apply_end_card_to_video(
                combined,
                duration=3.0,
                channel_name="Abone Ol",
                cta_text="Takip Et ve bildirimleri ac!"
            )
            print("  [Composer] End card overlay applied (Item 126).")
        else:
            print("  [Composer] [Item 126] End card overlay: RENDER_SAFE_MODE aktif, bypass edildi.")

        # Item 212: Neon geri sayım sayacı (ilk 3s)
        if enable_section2_filters:
            combined = apply_neon_countdown_overlay(combined, duration=3.0, position="top_right")
            print("  [Composer] Neon countdown overlay applied (Item 212).")

        # Item 246: Neon merak açılış grafiği (ilk 2.5s)
        if enable_section2_filters:
            combined = apply_neon_curiosity_opening_graphic(combined, duration=2.5, symbol="?")
            print("  [Composer] Neon curiosity opening graphic applied (Item 246).")

        # Item 138: Dinamik İlerleme Çubuğu (Neon progress bar)
        if enable_section2_filters:
            combined = apply_dynamic_progress_bar(combined, bar_height=4, position="bottom")
            print("  [Composer] Dynamic neon progress bar applied (Item 138).")

        # Item 232: Sabit üst kanca banner
        if enable_section2_filters:
            banner = ViralRetentionEngine.get_sticky_hook_banner("", mood="warning", lang="tr")
            combined = apply_sticky_hook_banner_overlay(combined, banner_text=banner)
            print("  [Composer] Sticky hook banner applied (Item 232).")

        # Item 238: Mikro-animasyonlu çıkartma (ok)
        if enable_section2_filters:
            combined = apply_micro_animated_sticker_overlay(combined, sticker="arrow", duration=2.5)
            print("  [Composer] Micro animated sticker applied (Item 238).")

        # Item 123: Bulanık gradient arka plan (fluid gradient overlay)
        if enable_section2_filters and not getattr(config, "RENDER_SAFE_MODE", True):
            combined = apply_fluid_gradient_background(combined)
            print("  [Composer] Fluid gradient background applied (Item 123).")

        # Items 235-236: Paylaş / Kaydet CTA görsel overlay
        if enable_section2_filters:
            meta = retention_metadata or {}
            topic = title or ""
            share_text = meta.get("share_cta") or ViralRetentionEngine.generate_share_cta(topic, lang="tr")
            bookmark_text = meta.get("bookmark_cta") or ViralRetentionEngine.generate_bookmark_cta(topic, lang="tr")
            share_at = max(0.0, combined.duration * 0.62)
            bookmark_at = max(0.0, combined.duration * 0.78)
            combined = apply_share_cta_overlay(combined, cta_text=share_text, start_at=share_at, duration=3.0)
            combined = apply_bookmark_cta_overlay(combined, cta_text=bookmark_text, start_at=bookmark_at, duration=3.0)
            print("  [Composer] Share + bookmark CTA overlays applied (Items 235-236).")

        # Item 131 + B5 hybrid UI overlays
        overlay_spec = hybrid_render_overlay or {}
        if not overlay_spec and hybrid_niche:
            try:
                from hybrid_niches import get_hybrid_render_overlay_spec
                overlay_spec = get_hybrid_render_overlay_spec(hybrid_niche)
            except Exception:
                overlay_spec = {}
        ui_type = overlay_spec.get("ui_type")
        if enable_section2_filters and ui_type in ("split_choice", "subtitle_bar"):
            combined = apply_hybrid_render_overlay(combined, overlay_spec)
            print(f"  [Composer] [B5] Hybrid structured overlay applied ({ui_type}).")
        elif enable_section2_filters and ui_type:
            combined = apply_ui_element_overlay(
                combined,
                ui_type=ui_type if ui_type != "imessage" else "ios_notification",
                header_text=overlay_spec.get("header", title or "Bildirim"),
                body_text=overlay_spec.get("body", "Sonuna kadar izle!"),
                start_time=0.6,
                duration=min(3.5, combined.duration * 0.35),
            )
            print(f"  [Composer] [Item 131/B5] Hybrid UI overlay applied ({ui_type}).")

        # Item 260: keyword emphasis white flash (~40% timeline)
        if enable_section2_filters and word_timings:
            flash_at = None
            for wt in word_timings:
                txt = str(wt.get("text", "")).upper()
                if any(k in txt for k in ("ASLA", "ŞOK", "GİZLİ", "NEVER", "SECRET", "SHOCK")):
                    flash_at = float(wt.get("offset", 0.0))
                    break
            if flash_at is None and combined.duration > 2.0:
                flash_at = combined.duration * 0.42
            if flash_at is not None:
                combined = apply_keyword_white_flash_overlay(combined, timestamp=flash_at, duration=0.18)
                print(f"  [Composer] [Item 260] Keyword white flash @ {flash_at:.2f}s.")

        # Item 224: infinite spiral (loop formula or optical hybrid)
        loop_formula = (retention_metadata or {}).get("loop_formula") or ""
        if enable_section2_filters and (
            loop_formula == "infinite_cycle"
            or overlay_spec.get("overlay") == "spiral"
        ):
            combined = apply_infinite_spiral_overlay(combined, duration=min(4.0, combined.duration))
            print("  [Composer] [Item 224] Infinite spiral overlay applied.")

        # Item 261: time tunnel (price timeline hybrid)
        if enable_section2_filters and overlay_spec.get("overlay") == "time_tunnel":
            combined = apply_time_tunnel_overlay(combined, duration=min(3.5, combined.duration))
            print("  [Composer] [Item 261] Time tunnel overlay applied.")

        # B5 hybrid overlay dispatch (neon_frame, epic_vignette, hybrid_frame, eq_bar, wheel, …)
        overlay_kind = overlay_spec.get("overlay")
        if enable_section2_filters and overlay_kind and overlay_kind not in ("spiral", "time_tunnel", "split_screen"):
            combined = apply_hybrid_render_overlay(combined, overlay_spec)
            item_ref = overlay_spec.get("item", overlay_kind)
            print(f"  [Composer] [B5] Hybrid render overlay applied ({item_ref}).")

        print(f"  [Composer] Duration: {combined.duration:.1f}s")

        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

        # Item 323: 60 FPS export OR Item 74: FPS mikro çeşitlendirme (29.97–30.04)
        import random
        export_mode = str(getattr(config, "EXPORT_FPS_MODE", "30"))
        if export_mode == "60":
            if getattr(config, "FPS_DIVERSIFY", True):
                export_fps = random.choice([59.94, 60.00, 60.02])
            else:
                export_fps = 60.0
        elif getattr(config, "FPS_DIVERSIFY", True):
            fps_pool = [29.97, 30.00, 30.02, 29.95, 30.04]
            export_fps = random.choice(fps_pool)
        else:
            export_fps = 30.0

        cpu_cores = os.cpu_count() or 16
        render_threads = int(getattr(config, 'RENDER_THREADS', 8) or 8)
        if render_threads <= 1:
            render_threads = max(4, min(8, cpu_cores // 2))

        from system_resilience import get_export_codec_settings
        use_gpu = getattr(config, "USE_GPU_ACCELERATION", True)
        gpu_codec = getattr(config, "GPU_CODEC", "")
        chosen_codec, codec_preset, extra_params, mode_desc = get_export_codec_settings(use_gpu, gpu_codec)
        mode_desc = f"{mode_desc} (threads={render_threads}/{cpu_cores})"

        print(f"  [Composer] Exporting: FPS={export_fps:.2f} (Item 74) | Motor: {mode_desc}", flush=True)
        render_logger = MoviePyProgressLogger(callback=progress_callback, cancel_check=cancel_check)

        write_kw = dict(
            fps=export_fps, codec=chosen_codec, audio=False,
            threads=render_threads, ffmpeg_params=extra_params, logger=render_logger,
        )
        if codec_preset:
            write_kw["preset"] = codec_preset
        try:
            combined.write_videofile(tmp, **write_kw)
        except Exception as enc_err:
            if chosen_codec in ("h264_nvenc", "h264_videotoolbox"):
                print(
                    f"  [Composer] [Uyarı] {chosen_codec} donanım hatası ({enc_err}). "
                    f"Otomatik CPU libx264 motoruna geçiliyor...",
                    flush=True,
                )
                combined.write_videofile(tmp, fps=export_fps, codec="libx264",
                                         preset="ultrafast", audio=False, threads=render_threads,
                                         ffmpeg_params=["-tune", "fastdecode", "-pix_fmt", "yuv420p"],
                                         logger=render_logger)
            else:
                raise

        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

        if progress_callback:
            progress_callback(97, "Altyazılar ve ses senkronize ediliyor...")

        # ALWAYS create both ASS and SRT
        create_karaoke_subtitles(word_timings, ass, style_opts=subtitle_opts)
        create_srt_file(word_timings, srt)

        # Final Audio Mastering Pass: Ensure volume is strictly normalized to -14 LUFS YouTube standard
        try:
            from voice_humanizer import normalize_ebu_r128
            master_norm_audio = output_path.rsplit(".", 1)[0] + "_master_norm.wav"
            norm_result = normalize_ebu_r128(final_audio, master_norm_audio, target_lufs=-14.0)
            if norm_result and os.path.exists(norm_result):
                final_audio = norm_result
                print("  [Composer] [AudioMaster] Final audio normalized to -14.0 LUFS EBU R128 standard.")
        except Exception as nae:
            print(f"  [Composer] Final audio normalization notice: {nae}")

        print(f"  [Composer] Merging audio + subtitles...")
        ok = _merge(tmp, final_audio, ass, srt, output_path)

        if ok and os.path.exists(output_path):
            mb = os.path.getsize(output_path) / 1048576
            print(f"  [Composer] [OK] {output_path} ({mb:.1f} MB)")
            # Extract high-curiosity Frame 0 / Thumbnail (Item 59, 92)
            thumb_path = output_path.rsplit(".", 1)[0] + "_thumb.jpg"
            extract_frame0_thumbnail(output_path, thumb_path)

            sync_path = output_path.rsplit(".", 1)[0] + "_synced.mp4"
            synced_output = enforce_av_duration_sync(output_path, sync_path)
            if synced_output == sync_path and os.path.exists(sync_path):
                os.replace(sync_path, output_path)

            # P2-02: unified post-render humanization (Rules 29/30 + Items 127/128/429)
            try:
                from anti_detect.post_render import apply_post_render_humanization
                post = apply_post_render_humanization(
                    output_path,
                    title=title or os.path.splitext(os.path.basename(output_path))[0],
                )
                if post.get("size_delta_kb"):
                    print(f"  [Composer] [Kural 30] Dosya Boyutu Varyasyonu: +{post['size_delta_kb']} KB.")
                if post.get("aged_minutes"):
                    print(f"  [Composer] [Kural 29] Dosya {post['aged_minutes']} dk geçmişe yaşlandırıldı.")
                if post.get("metadata_applied"):
                    print("  [Composer] [Items 127+128] NLE metadata imzası uygulandı.")
            except Exception as se:
                print(f"  [Composer] PostRender uyarısı: {se}")

            # Item 124: Mikro çözünürlük manipülasyonu (post-merge FFmpeg crop)
            if not getattr(config, "RENDER_SAFE_MODE", True):
                try:
                    micro_path = output_path.rsplit(".", 1)[0] + "_micro.mp4"
                    cropped = apply_micro_resolution_crop(output_path, micro_path)
                    if cropped != output_path and os.path.exists(cropped):
                        os.replace(cropped, output_path)
                        print("  [Composer] Micro resolution crop applied (Item 124).")
                except Exception as mre:
                    print(f"  [Composer] Item 124 micro crop notice: {mre}")

            # Manuel Yükleme Bilgi Paketi — export_seo_operator_pack (B6 Batch 4)
            try:
                import json
                from viral_seo_agent import export_seo_operator_pack
                from proof_archiver import proof_archiver
                from database import get_video_stats

                clean_title = title or os.path.splitext(os.path.basename(output_path))[0]
                render_stats = get_video_stats()
                total_renders = int(render_stats.get("total_completed") or 0)
                script_text = " ".join(
                    str(sc.get("narration", "")) for sc in scene_clips if sc.get("narration")
                )
                borderline_scan = proof_archiver.sanitize_borderline_words(script_text) if script_text else {}
                operator = export_seo_operator_pack(
                    keyword=clean_title,
                    title=clean_title,
                    retention_metadata=retention_metadata,
                    lang=str(getattr(config, "LANGUAGE", "tr") or "tr"),
                    video_filename=os.path.basename(output_path),
                    thumb_path=os.path.basename(output_path.rsplit(".", 1)[0] + "_thumb.jpg"),
                    total_renders=total_renders,
                )
                seo_meta = operator.get("seo") or {}
                engagement = operator.get("studio_engagement") or {}
                live_stream_plan = operator.get("live_stream_plan") or {}
                manual_pkg = {
                    **operator,
                    "video_file": os.path.basename(output_path),
                    "title": seo_meta.get("seo_title", clean_title),
                    "description": seo_meta.get("seo_description", ""),
                    "tags": seo_meta.get("tags", []),
                    "pinned_comment": seo_meta.get("pinned_comment", ""),
                    "render_spec": {
                        "aspect_ratio": "9:16",
                        "resolution": "1080x1920",
                        "video_codec": "h264",
                        "video_bitrate_mbps": "12-16",
                        "audio_codec": "aac",
                        "audio_sample_rate_hz": 48000,
                        "embedded_subtitles": "ass+srt",
                        "items": "397-400,403",
                    },
                    "borderline_content_scan": borderline_scan,
                    "channel_health": proof_archiver.build_actionable_channel_health_checklist(
                        total_videos=total_renders, lang="tr"
                    ),
                    "rule_80_altered_synthetic": "HAYIR (Yüz klonlama veya manipülasyon yoksa etiket seçilmemeli)",
                    "rule_83_source_reference": "Açıklamaya araştırma ve kaynak referansı eklendi.",
                    "anti_detect_ready": True,
                    "size_mb": round(os.path.getsize(output_path) / 1048576, 2),
                }
                info_json = output_path.rsplit(".", 1)[0] + "_manual_upload_info.json"
                info_txt = output_path.rsplit(".", 1)[0] + "_manual_upload_guide.txt"
                with open(info_json, "w", encoding="utf-8") as fj:
                    json.dump(manual_pkg, fj, ensure_ascii=False, indent=2)
                reupload_guidance = operator.get("reupload_guidance") or {}
                feed_distribution = operator.get("feed_distribution_advisory") or {}
                algorithm_reset = operator.get("algorithm_reset_guidance") or {}
                traffic_advisory = operator.get("traffic_sources_advisory") or {}
                momentum_advisory = operator.get("channel_momentum_advisory") or {}
                end_screen = operator.get("end_screen_guidance") or {}
                competitor_brief = operator.get("competitor_analysis") or {}
                contact_guidance = operator.get("channel_contact") or {}
                upload_sched = operator.get("upload_schedule") or {}
                cta_timing = operator.get("cta_timing") or {}
                studio_meta = operator.get("studio_metadata") or {}
                with open(info_txt, "w", encoding="utf-8") as ft:
                    ft.write(
                        f"=== YOUTUBE SHORTS MANUEL YÜKLEME REHBERİ ===\n\n"
                        f"📌 VİDEO BAŞLIĞI:\n{manual_pkg['title']}\n\n"
                        f"📌 VİDEO AÇIKLAMASI (Kural 83 Kaynak ve Fair Use Referanslı):\n{manual_pkg['description']}\n\n"
                        f"📌 VİDEO ETİKETLERİ:\n{', '.join(manual_pkg['tags'])}\n\n"
                        f"📌 STUDIO METADATA (Items 354-405):\n"
                        f"Konum: {studio_meta.get('location_tag')} | Dil: {studio_meta.get('audience_language')}\n"
                        f"Kategori: {studio_meta.get('category_label')} | Playlist: {studio_meta.get('playlist_suggestion')}\n"
                        f"{studio_meta.get('tags_csv')}\n\n"
                        f"📌 İLK YORUM (Sabitleyin — Item 350):\n{manual_pkg['pinned_comment']}\n\n"
                        f"❤️ YORUM KALP (Item 351):\n{engagement.get('heart_action', '')}\n\n"
                        f"💬 İLK 2 SAAT YORUM YANITI (Item 374):\n{engagement.get('reply_action', '')}\n\n"
                        f"🛡️ SPAM YORUM FİLTRESİ (Item 375):\n{engagement.get('spam_filter_action', '')}\n\n"
                        f"📺 CANLI YAYIN PLANI (Item 384):\n{live_stream_plan.get('schedule', '')}\n"
                        f"{live_stream_plan.get('studio_action', '')}\n\n"
                        f"🚫 YENİDEN YÜKLEME UYARISI (Item 380):\n{reupload_guidance.get('rule', '')}\n"
                        f"{reupload_guidance.get('action', '')}\n\n"
                        f"📈 FEED DAĞITIM İVMESİ (Item 387):\n{feed_distribution.get('message', '')}\n\n"
                        f"🔄 ALGORİTMA RESET (Item 394):\n{algorithm_reset.get('rule', '')}\n"
                        f"{algorithm_reset.get('action', '')}\n\n"
                        f"📊 TRAFİK KAYNAKLARI (Items 406-409):\n{traffic_advisory.get('diagnosis', '')}\n"
                        f"Shorts Feed hedef: ≥%{traffic_advisory.get('shorts_feed_target_pct', 80):.0f}\n\n"
                        f"⏳ SABIR EŞİĞİ (Item 410):\n{momentum_advisory.get('message', '')}\n\n"
                        f"🔗 END SCREEN / LINK (Item 392):\n{end_screen.get('end_screen_action', '')}\n\n"
                        f"🎯 RAKİP ANALİZİ (Item 395):\n{competitor_brief.get('action', '')}\n\n"
                        f"📧 KANAL İLETİŞİM (Item 396):\n{contact_guidance.get('about_section_text', '')}\n\n"
                        f"🎬 RENDER TEKNİK (Items 397-400, 403):\n"
                        f"9:16 1080x1920 · H.264 12-16 Mbps · AAC 48kHz · ASS/SRT gömülü altyazı\n\n"
                        f"🛡️ TOPLULUK KELİME TARAMASI (Item 390):\n"
                        f"{'Temiz' if borderline_scan.get('is_clean', True) else 'Şüpheli kelimeler: ' + ', '.join(borderline_scan.get('flagged_words', []))}\n\n"
                        f"⏰ YÜKLEME SAATİ (Items 362-363):\n"
                        f"{upload_sched.get('primary_window', '')} ({upload_sched.get('timezone', '')})\n\n"
                        f"🔔 CTA ZAMANLAMASI (Item 367):\n"
                        f"Abone Ol overlay ~{cta_timing.get('cta_start_second', 27)}s — {cta_timing.get('rule_compliance', '')}\n\n"
                        f"📌 STUDIO KANAL ANAHTAR KELİMELERİ (Item 358):\n"
                        f"{', '.join(manual_pkg.get('channel_master_keywords', []))}\n\n"
                        f"⚠️ YOUTUBE STUDIO ETİKET AYARI (Kural 80):\n"
                        f"- 'Yapay zeka / Değiştirilmiş içerik mi?' sorusuna 'HAYIR' yanıtını verin.\n"
                        f"  (Kural 80: Yüz klonlama veya haber manipülasyonu olmadığı sürece etiket işaretlenmemelidir;\n"
                        f"   aksi halde algoritma videoyu daha dar bir test kitlesine hapseder.)\n\n"
                        f"🛡️ DOSYA GÜVENLİK BİLGİSİ:\n"
                        f"- Dosya boyutu Kural 30 gereği MP4 'free' atomuyla benzersizleştirildi.\n"
                        f"- Dosya tarihi Kural 29 gereği geçmişe yaşlandırıldı.\n"
                        f"- pHash gürültüsü, renk jitter'ı, unsharp ve statik gren (Kural 84 & 86) videoya işlendi.\n"
                    )
                print(f"  [Composer] [OK] Manuel yükleme rehberi hazırlandı: {os.path.basename(info_txt)}")
            except Exception as mie:
                print(f"  [Composer] Manuel yükleme paketi uyarısı: {mie}")

            # Auto-archive Proof of Effort Dossier (Item 471)
            try:
                from proof_archiver import proof_archiver
                proof_archiver.archive_video_proof(
                    video_filename=os.path.basename(output_path),
                    title=os.path.splitext(os.path.basename(output_path))[0],
                    niche="auto_detected",
                    script_text=" ".join(s.get("narration", "") for s in scene_clips),
                    scenes=scene_clips,
                    render_params={"anti_duplicate": anti_duplicate, "fps": config.FPS, "split_screen": split_screen, "ken_burns": enable_ken_burns}
                )
                print(f"  [ProofArchiver] [OK] Proof dossier archived.")
            except Exception as pe:
                print(f"  [ProofArchiver] Notice: {pe}")

            return output_path
        return ""
    finally:
        # Guarantee clip resources and file handles are closed
        if combined is not None:
            try:
                combined.close()
            except Exception:
                pass
        for s in segs:
            try:
                s.close()
            except Exception:
                pass
        cleanup_stray_ffmpeg_processes()
        gc.collect()

        # Cleanup intermediate files safely
        for f in [tmp]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

        for temp_aud in [processed_audio, final_audio]:
            if temp_aud != audio_path and os.path.exists(temp_aud):
                try:
                    os.remove(temp_aud)
                except Exception:
                    pass

import imageio_ffmpeg

def _merge(vid, aud, ass, srt, out):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    out_dir = os.path.dirname(os.path.abspath(out))

    # Basenames for execution inside out_dir
    base_vid = os.path.basename(vid)
    base_ass = os.path.basename(ass)
    base_srt = os.path.basename(srt)
    base_out = os.path.basename(out)
    rel_aud = os.path.relpath(aud, out_dir).replace("\\", "/")

    # Items 72, 84, 86 & 92: FFmpeg Renk Jitter + Unsharp + Piksel Greni + Kenar Vinyet Filtresi (%4 Degrade)
    color_vf = get_color_grading_ffmpeg_filter(jitter_range=0.015)
    unsharp_vf = get_unsharp_filter(luma_matrix=5, luma_amount=0.8)
    grain_vf = get_ffmpeg_static_grain_filter()
    vignette_vf = get_ffmpeg_vignette_filter(angle=0.18)
    base_vf = f"{color_vf},{unsharp_vf},{grain_vf},{vignette_vf}"

    # Donanim Hizlandirma Yapilandirmasi (RTX NVENC vs Multi-thread CPU)
    use_gpu = getattr(config, "USE_GPU_ACCELERATION", True)
    gpu_codec = getattr(config, "GPU_CODEC", "h264_nvenc")
    render_threads = int(getattr(config, "RENDER_THREADS", 8) or 8)

    def execute_ffmpeg_pass(vf_string):
        """Attempts GPU NVENC encoding first, automatically falling back to CPU multi-threading."""
        if use_gpu and gpu_codec == "h264_nvenc":
            gpu_cmd = [
                ffmpeg_exe, "-y", "-hwaccel", "cuda", "-i", base_vid, "-i", rel_aud,
                "-vf", vf_string,
                "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "22", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", base_out
            ]
            r = subprocess.run(gpu_cmd, cwd=out_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if r.returncode == 0 and os.path.exists(out):
                return True, r
            else:
                print(f"    [Composer] NVENC merge uyarisi ({r.stderr.decode('utf-8', errors='ignore')[:120]}), CPU'ya geciliyor...", flush=True)

        # CPU Fallback (Multi-threaded libx264)
        cpu_cmd = [
            ffmpeg_exe, "-y", "-i", base_vid, "-i", rel_aud,
            "-vf", vf_string,
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "fastdecode",
            "-threads", str(render_threads), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", base_out
        ]
        r = subprocess.run(cpu_cmd, cwd=out_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return (r.returncode == 0 and os.path.exists(out)), r

    # Try 1: ASS karaoke
    if os.path.exists(ass) and os.path.getsize(ass) > 50:
        vf_chain = f"{base_vf},ass={base_ass}"
        success, r = execute_ffmpeg_pass(vf_chain)
        if success:
            print(f"    [OK] Karaoke subtitles, Unsharp, Static Grain & Vignette applied (Items 84, 86, 92, 173)")
            return True
        print(f"    ASS failed ({r.stderr.decode('utf-8', errors='ignore')[:150]}), trying SRT...")

    # Try 2: SRT styled
    if os.path.exists(srt) and os.path.getsize(srt) > 10:
        srt_vf = (
            f"{base_vf},subtitles={base_srt}:force_style='FontSize=28,FontName=Arial,Bold=1,"
            f"PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,Outline=3,"
            f"BackColour=&H80000000,BorderStyle=4,Alignment=2,MarginV=300'"
        )
        success, r = execute_ffmpeg_pass(srt_vf)
        if success:
            print(f"    [OK] SRT subtitles, Unsharp, Static Grain & Vignette applied (Items 84, 86, 92, 173)")
            return True
        print(f"    SRT failed, trying no subs...")

    # Try 3: No subs (apply unsharp, static grain & vignette filters)
    success, r = execute_ffmpeg_pass(base_vf)
    if success:
        print(f"    Video created with Unsharp, Static Grain & Vignette (no subtitles, 192k AAC 48k)")
        return True
    return False
    return False




def _prep(path, dur, tw, th, split_screen=False, enable_section2=True, badge_label=None, badge_icon="💡", enable_pip=False, pip_path=None, gameplay_path=None):
    c = VideoFileClip(path, audio=False)
    # Downscale high-resolution/4K videos early to 1080p to save RAM and CPU
    if c.w > tw and c.h > th:
        c = c.resize(width=tw) if c.w >= c.h else c.resize(height=th)
    elif c.w > tw * 1.2:
        c = c.resize(width=tw)
    elif c.h > th * 1.2:
        c = c.resize(height=th)

    # Item 79: Hız Varyasyonu (Speed Ramp %97 veya %103)
    if enable_section2:
        c = apply_speed_ramp(c)

    # Item 78: Görsel Aynalama (Horizontal Flip Content ID Koruması)
    # Metin kartları (Reddit açılış kartı vb.) ters dönmemesi için hariç tutulur
    is_text_card = any(k in path.lower() for k in ("reddit", "card", "text", "title"))
    if enable_section2 and not is_text_card:
        c = apply_horizontal_flip(c)

    # Süre senkronizasyonu
    if c.duration > dur:
        st = (c.duration - dur) / 2
        c = c.subclip(st, st + dur)
    elif c.duration < dur:
        f = c.duration / dur
        c = c.fx(vfx.speedx, f) if f >= 0.5 else c.loop(duration=dur)

    # Item 77: Yatay kaynakları 9:16 yaparken Akıllı Kırpma (%40 Gaussian Blur Arka Plan)
    if split_screen:
        selected_gameplay = gameplay_path or os.path.join(config.ASSETS_DIR, "gameplay_loop.mp4")
        if os.path.exists(selected_gameplay):
            c = create_split_screen_clip(c, selected_gameplay, tw, th)
        else:
            c = apply_smart_crop(c, tw, th, blur_intensity=0.40)
    else:
        c = apply_smart_crop(c, tw, th, blur_intensity=0.40)

    # Item 95: Çift Stok Katmanı (Picture-in-Picture)
    if enable_pip:
        c = apply_pip_overlay(c, pip_clip_or_path=pip_path)

    # Item 76: 3 Saniye Kuralı Kurgusu (3.2s üzeri sahnelerde mikro-kesit ve punch-in)
    if enable_section2 and c.duration > 3.2:
        c = enforce_3s_broll_rule(c, max_duration=3.2)

    # Item 82: Metin İçi Görsel Çıkartmalar & Sayaç Rozetleri (Stickers/Badges)
    if badge_label:
        c = overlay_graphic_badge(c, label=badge_label, icon=badge_icon)

    # Item 75: Görsel Katmanlama (Multi-Layer B-Roll %10 opaklıkta ışık sızıntısı/toz)
    if enable_section2:
        c = apply_multi_layer_overlay(c, opacity=0.10)

    # Item 106: Ana sahne köşe yuvarlama (corner radius)
    if enable_section2:
        c = apply_corner_radius_to_clip(c, radius=28)

    # Item 72 & 71: Renk Derecelendirme ve pHash Gürültüsü — sadece FFmpeg merge aşamasında uygulanır
    # (RENDER_SAFE_MODE: _prep içinde bypass, _merge'deki FFmpeg filtreleri zaten var)

    return c

def _fit(c, tw, th):
    """Fallback legacy helper delegating directly to smart crop with 40% blur."""
    return apply_smart_crop(c, tw, th, blur_intensity=0.40)


# ─── ITEM 129: Ses ve Görüntü Süre Uyuşmazlığı Koruması ─────────────────────

def enforce_av_duration_sync(video_path: str, output_path: str,
                              tolerance_sec: float = 0.05) -> str:
    """
    Item 129 – Video Dosyasında Ses ve Görüntü Süre Uyuşmazlığı Koruması.
    Ses ile görüntünün bitiş süresi 0.05 saniye hassasiyetle eşitlenir.
    Uyuşmazlık varsa kısa olan stream'i dolgu (pad/trim) ile düzeltir.

    Yöntem:
    - FFprobe ile video ve audio stream sürelerini ölçer
    - Fark > tolerance_sec ise FFmpeg atpd/apad filtresiyle hizalar
    - Uyuşmazlık yoksa orijinal dosyayı geri döndürür

    Args:
        video_path: Giriş video dosyası
        output_path: Çıkış dosyası (hizalanmış)
        tolerance_sec: İzin verilen maksimum süre farkı (saniye, varsayılan: 0.05)
    Returns:
        output_path (hizalandıysa) veya video_path (uyuşmazlık yoksa)
    """
    import subprocess, json, shutil

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    # ffprobe: sistem PATH'inde ara, yoksa ffmpeg binary yanında ara
    ffprobe = shutil.which("ffprobe") or ffmpeg.replace("ffmpeg", "ffprobe")

    # Süre ölçümü
    try:
        probe_cmd = [
            ffprobe, "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            video_path
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True)
        data = json.loads(probe.stdout)
        streams = data.get("streams", [])

        video_dur = None
        audio_dur = None
        for s in streams:
            codec_type = s.get("codec_type", "")
            dur = float(s.get("duration", 0) or 0)
            if codec_type == "video" and dur > 0:
                video_dur = dur
            elif codec_type == "audio" and dur > 0:
                audio_dur = dur

        if video_dur is None or audio_dur is None:
            print(f"    [Item 129] Stream süreleri ölçülemedi, atlanıyor.")
            return video_path

        diff = abs(video_dur - audio_dur)
        print(f"    [Item 129] Video: {video_dur:.3f}s | Audio: {audio_dur:.3f}s | Fark: {diff:.4f}s")

        if diff <= tolerance_sec:
            print(f"    [Item 129] Süre farkı tolerans içinde ({diff:.4f}s ≤ {tolerance_sec}s). Hizalama atlandı.")
            return video_path

        # Hizalama gerekli
        print(f"    [Item 129] Süre uyuşmazlığı tespit edildi ({diff:.4f}s). Hizalanıyor...")

        if audio_dur > video_dur:
            # Video kısa → son kareyi uzat
            filter_v = f"[0:v]tpad=stop_mode=clone:stop_duration={diff:.4f}[v]"
            filter_str = f"{filter_v};[0:a]acopy[a]"
        else:
            # Ses kısa → sessizlik ekle (apad)
            filter_str = "[0:v]copy[v];[0:a]apad=pad_dur={diff:.4f}[a]".format(diff=diff)

        cmd = [
            ffmpeg, "-y",
            "-i", video_path,
            "-filter_complex", filter_str.format(diff=diff),
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264", "-preset", "ultrafast", "-threads", "2", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    [Item 129] A/V hizalandı → fark {diff:.4f}s → {output_path}")
            return output_path
        else:
            print(f"    [Item 129] FFmpeg hizalama hatası: {result.stderr[:200]}")

    except Exception as e:
        print(f"    [Item 129] A/V senkronizasyon hatası: {e}")

    return video_path
