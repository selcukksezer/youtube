"""
Video composer — MoviePy (video only) + ffmpeg (audio + karaoke subs).
3-tier fallback: ASS karaoke → SRT styled → no subs.
"""
import os, subprocess, platform, gc, shutil
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, concatenate_videoclips, vfx
import cv2

# Disable OpenCL GPU acceleration and cap threads to 2 to eliminate GPU driver crashes and black screens
try:
    cv2.ocl.setUseOpenCL(False)
    cv2.setNumThreads(2)
except Exception:
    pass

import config
from subtitle_generator import create_karaoke_subtitles, create_srt_file
from bgm_manager import get_bgm_path, mix_narration_and_bgm, align_scenes_to_bgm_beats
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
    apply_out_of_focus_reveal, apply_end_card_to_video, clean_video_metadata,
    apply_particle_overlay, apply_heartbeat_zoom, apply_speaker_avatar_overlay,
    build_emoji_events_from_timings, generate_emoji_subtitle_overlay,
    apply_alternating_motion, apply_ui_element_overlay,
    apply_dynamic_progress_bar, get_color_grading_ffmpeg_filter
)

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
        super().__init__(init_state=None, bars=None, ignored_bars=None, logged_bars='all', min_time_interval=0, ignore_new_bars=False)
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
                # Canlı ilerleme: Her 1.2 saniyede bir veya her %4 karede bir hem terminale hem UI'a bas
                if (now - self.last_log_time >= 1.2) or (frame_pct >= self.last_frame_pct + 4) or value >= total:
                    self.last_log_time = now
                    self.last_frame_pct = frame_pct
                    overall_pct = int(80 + (value / total) * 16)
                    msg = f"Kareler Full HD kodlanıyor: %{frame_pct} ({int(value)}/{int(total)} kare)"
                    print(f"  [Composer] {msg}", flush=True)
                    # Free temporary NumPy frame arrays from RAM
                    gc.collect()
                    if self.ui_callback:
                        try:
                            self.ui_callback(overall_pct, msg)
                        except Exception:
                            pass

def compose_video(scene_clips, audio_path, word_timings, output_path, title="", 
                  bgm_track=None, bgm_volume=None, subtitle_opts=None,
                  progress_callback=None, cancel_check=None,
                  split_screen=False, anti_duplicate=True, watermark_path=None,
                  enable_ken_burns=True, enable_section2_filters=True, gameplay_path=None):
    print(f"\n  [Composer] Building video with 500-Item Optimization Pipeline (Items 71-79)...")
    W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT

    if cancel_check and cancel_check():
        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    # Apply Voice Humanizer (Studio Warmth EQ + -14 LUFS EBU R128 Loudness) (Items 150-162)
    mastered_audio = audio_path
    try:
        from voice_humanizer import voice_humanizer
        eq_audio = output_path.rsplit(".", 1)[0] + "_eq.wav"
        eq_audio = voice_humanizer.apply_studio_eq_and_warmth(audio_path, eq_audio)
        mastered_audio = eq_audio
        print("  [Composer] [VoiceHumanizer] Studio Warmth EQ applied.")

        # Item 141: Insert subtle breaths between natural narration sections.
        breaths_audio = output_path.rsplit(".", 1)[0] + "_breaths.wav"
        mastered_audio = voice_humanizer.inject_natural_breaths(eq_audio, breaths_audio, interval_seconds=8.0)
        print("  [Composer] [VoiceHumanizer] Natural breath layer injected (Item 141).")

        # Item 145: Add a very light room ambience/reverb layer.
        room_audio = output_path.rsplit(".", 1)[0] + "_room.wav"
        from voice_humanizer import mix_pink_noise_into_narration
        mastered_audio = mix_pink_noise_into_narration(mastered_audio, room_audio, noise_db=-34.0, noise_type="room")
        print("  [Composer] [VoiceHumanizer] Light room ambience applied (Item 145).")

        # Normalize after the voice layers so output stays at the loudness target.
        norm_audio = output_path.rsplit(".", 1)[0] + "_norm.wav"
        mastered_audio = voice_humanizer.normalize_ebu_r128(mastered_audio, norm_audio)

        # Item 87: 0.4s Sonic Brand Chime Watermark
        sonic_audio = output_path.rsplit(".", 1)[0] + "_sonic.wav"
        mastered_audio = voice_humanizer.inject_sonic_brand_watermark(mastered_audio, sonic_audio)
        print("  [Composer] [VoiceHumanizer] 0.4s Sonic Brand Chime Watermark injected (Item 87).")

        # Item 101: Ses Hızı Dalgalanması (Audio Speed Jitter %98 - %102)
        if enable_section2_filters:
            jitter_audio = output_path.rsplit(".", 1)[0] + "_jitter.wav"
            mastered_audio = voice_humanizer.apply_audio_jitter(mastered_audio, jitter_audio, min_speed=0.985, max_speed=1.015)
            print("  [Composer] [VoiceHumanizer] Ses hızı mikro dalgalanması uygulandı (Madde 101).")
    except Exception as vhe:
        print(f"  [Composer] Voice humanizer notice: {vhe}")
        mastered_audio = audio_path

    # Measure exact narration audio duration
    import wave
    audio_dur = 0.0
    try:
        with wave.open(mastered_audio, "rb") as w:
            audio_dur = w.getnframes() / float(w.getframerate())
    except Exception:
        try:
            from scipy.io import wavfile
            rate, data = wavfile.read(mastered_audio)
            audio_dur = len(data) / float(rate)
        except Exception as e:
            print(f"    Audio duration read error: {e}")

    # Scale scene clip durations to match exact audio length BEFORE mixing SFX
    total_scene_dur = sum(sc.get("duration", 7) for sc in scene_clips)
    if audio_dur > 2.0 and total_scene_dur > 0:
        scale = audio_dur / total_scene_dur
        print(f"  [Composer] Scaling scene clip durations (Scale: {scale:.2f}x, Audio: {audio_dur:.1f}s)...")
        for sc in scene_clips:
            sc["duration"] = round(sc.get("duration", 7) * scale, 2)

    # Step A: SFX mixing on narration audio (using scaled scene durations for perfect sync)
    processed_audio = mastered_audio
    if getattr(config, "ENABLE_SFX", True):
        scene_durs = [sc.get("duration", 7) for sc in scene_clips]
        sfx_audio = output_path.rsplit(".", 1)[0] + "_sfx_audio.wav"
        processed_audio = add_sfx_to_narration(
            mastered_audio, scene_durs, sfx_audio,
            sfx_volume=getattr(config, "SFX_VOLUME", 0.20), scene_clips=scene_clips
        )

        # Madde 155 & Madde 154: Sahne geçişi Riser (0.25s) ve Kanca 45Hz Sub-Bass darbesi
        try:
            from voice_humanizer import sync_riser_whoosh_transitions, inject_sub_bass_impact
            scene_cut_times = []
            cur_time = 0.0
            for sc in scene_clips[:-1]:
                cur_time += sc.get("duration", 7)
                scene_cut_times.append(round(cur_time, 3))
            if scene_cut_times:
                riser_audio = output_path.rsplit(".", 1)[0] + "_risers.wav"
                processed_audio = sync_riser_whoosh_transitions(processed_audio, scene_cut_times, riser_audio)
                print(f"  [Composer] [Item 155] Sahne geçişleri için {len(scene_cut_times)} adet 250ms Riser/Whoosh senkronize edildi.")

            sub_audio = output_path.rsplit(".", 1)[0] + "_subbass.wav"
            sub_time = min(2.5, scene_clips[0].get("duration", 3.0) * 0.7) if scene_clips else 2.0
            processed_audio = inject_sub_bass_impact(processed_audio, sub_audio, timestamp_sec=sub_time)
            print(f"  [Composer] [Item 154] Kanca vurgusuna 45Hz Sub-Bass Impact darbesi mikslendi (t={sub_time:.2f}s).")

            # Madde 157: Korku, gerilim veya karanlık temalarda Kalp Atışı (Heartbeat) alt katmanı
            has_tension = any(any(k in str(sc.get("scene_description", "")).lower() for k in ("korku", "gerilim", "horror", "mystery", "dark", "şok", "karanlık")) for sc in scene_clips)
            if has_tension:
                from voice_humanizer import inject_heartbeat_layer
                hb_audio = output_path.rsplit(".", 1)[0] + "_heartbeat.wav"
                processed_audio = inject_heartbeat_layer(processed_audio, hb_audio, start_sec=1.5, duration_sec=4.0, volume=0.30)
                print("  [Composer] [Item 157] Gerilim sahnesine Kalp Atışı (Heartbeat) alt katmanı mikslendi.")

            # Madde 158: Soru, quiz veya geri sayım anında Saat Tik-Tak Sesi (Ticking Clock)
            has_question = any("?" in str(sc.get("narration", "")) or "quiz" in str(sc.get("scene_description", "")).lower() for sc in scene_clips)
            if has_question:
                from voice_humanizer import inject_ticking_clock
                q_time = 2.0
                elapsed = 0.0
                for sc in scene_clips:
                    if "?" in str(sc.get("narration", "")):
                        q_time = elapsed
                        break
                    elapsed += sc.get("duration", 7)
                clk_audio = output_path.rsplit(".", 1)[0] + "_clock.wav"
                processed_audio = inject_ticking_clock(processed_audio, clk_audio, timestamp_sec=q_time, duration=3.0, volume=0.35)
                print(f"  [Composer] [Item 158] Soru/Quiz anına 3s Saat Tik-Tak sesi mikslendi (t={q_time:.2f}s).")

            # Madde 159: Belge, ifşa veya ekrana yazı dökülme sahnelerinde Daktilo Sesi (Typewriter SFX)
            has_document = any(any(k in str(sc.get("scene_description", "")).lower() for k in ("belge", "yazı", "typewriter", "daktilo", "rapor", "metin")) for sc in scene_clips)
            if has_document:
                from voice_humanizer import inject_typewriter_sfx
                tw_audio = output_path.rsplit(".", 1)[0] + "_typewriter.wav"
                processed_audio = inject_typewriter_sfx(processed_audio, tw_audio, timestamp_sec=2.0, duration=2.0, volume=0.30)
                print("  [Composer] [Item 159] Ekrana yazı dökülme sahnesine Daktilo Sesi mikslendi.")

            # Madde 167 & 168: Quiz Doğru Cevap Ding (1800Hz Kristal Zil) ve Yanlış Cevap Buzzer (120Hz Testere Dişi)
            has_quiz = any("quiz" in str(sc.get("scene_description", "")).lower() or "soru" in str(sc.get("scene_description", "")).lower() for sc in scene_clips)
            if has_quiz:
                from voice_humanizer import inject_quiz_ding, inject_quiz_buzzer
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
        niche_hint = (title or "") + " " + " ".join(str(s.get("scene_description", "")) for s in scene_clips[:2])
        matched_track = match_bgm_track_to_niche(niche_hint)
        chosen_bgm = os.path.basename(matched_track) if matched_track else ""

    if chosen_bgm and getattr(config, "ENABLE_BGM", True):
        bgm_p = get_bgm_path(chosen_bgm)
        if bgm_p:
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
            
            # Item 166: Kapanış Müzik Sönümlemesi (Fade-Out Yok! Keskin Döngü)
            final_audio = mix_narration_and_bgm(processed_audio, bgm_p, mixed_audio, volume=vol,
                                               tape_stop_times=tape_stop_times, allow_fade_out=False)

            # Item 170: Ses Katmanlarının Faz Uyumu (Phase Alignment: Mono Bas Kilidi <120Hz)
            if final_audio and os.path.exists(final_audio):
                from voice_humanizer import lock_bass_frequencies_to_mono
                phase_aligned_audio = output_path.rsplit(".", 1)[0] + "_phase_aligned.wav"
                final_audio = lock_bass_frequencies_to_mono(final_audio, phase_aligned_audio, cutoff_hz=120.0)
                print("  [Composer] [Item 170] Ses katmanları faz uyumu (Phase Alignment: Mono Bas Kilidi <120Hz) uygulandı.")


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
                    badge_label = sc.get("badge_label") or f"{idx + 1}/{total_scenes}"
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

                    # Item 99: Dinamik Kamera Sallantısı (Handheld Camera Shake)
                    if sc.get("handheld_shake", False):
                        clip_seg = apply_handheld_camera_shake(clip_seg, intensity=5.0)

                    # Item 100: Görsel Maskeleme (Wipe Transition Mask Overlay)
                    if sc.get("wipe_transition", False) and idx > 0:
                        direction = sc.get("wipe_direction", "horizontal")
                        clip_seg = apply_mask_wipe_transition(clip_seg, direction=direction, transition_dur=0.35)

                    # Item 103: Ekran Dışı Odak (İlk sahnede 0.35s netleşme kancası)
                    if idx == 0 and enable_section2_filters:
                        clip_seg = apply_out_of_focus_reveal(clip_seg, blur_duration=0.35)

                    # Item 132: Görsel Hareketi Yön Değişimi (Alternating pan/tilt motion)
                    if enable_section2_filters:
                        clip_seg = apply_alternating_motion(clip_seg, scene_index=idx)

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

        if enable_section2_filters:
            emoji_events = build_emoji_events_from_timings(word_timings, scene_clips)
            if emoji_events:
                emoji_overlay = generate_emoji_subtitle_overlay(
                    W, H, combined.duration, emoji_events, fps=combined.fps or config.FPS
                )
                combined = CompositeVideoClip([combined, emoji_overlay], size=(W, H))
                combined.duration = sum(float(sc.get("duration", 3.0)) for sc in scene_clips)
            combined = apply_heartbeat_zoom(combined, bpm=60.0)
            combined = apply_particle_overlay(combined, particle_type="spark", particle_count=30)
            combined = apply_speaker_avatar_overlay(combined, avatar_size=96)
        if anti_duplicate:
            print("  [Composer] Applying anti-duplicate filter (Item 50)...")
            combined = apply_anti_duplicate(combined)
        if watermark_path and os.path.exists(watermark_path):
            print("  [Composer] Overlaying watermark logo (Item 60)...")
            combined = overlay_watermark(combined, watermark_path)
        combined = apply_end_card_to_video(
            combined,
            duration=3.0,
            channel_name="Abone Ol",
            cta_text="Takip Et ve bildirimleri ac!"
        )
        print("  [Composer] End card overlay applied (Item 126).")

        # Item 138: Dinamik İlerleme Çubuğu (Neon progress bar)
        if enable_section2_filters:
            combined = apply_dynamic_progress_bar(combined, bar_height=4, position="bottom")
            print("  [Composer] Dynamic neon progress bar applied (Item 138).")

        print(f"  [Composer] Duration: {combined.duration:.1f}s")

        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

        # Item 74: Kare Hızı (FPS) Çeşitlendirmesi (29.97, 30.02 fps)
        # Limit encoding threads to 2 and disable GPU OpenCL to keep PC cool and prevent driver crashes
        export_fps = getattr(combined, "fps", 30.0) or 30.0
        print(f"  [Composer] Exporting with diversified FPS: {export_fps:.2f} (Item 74, threads=2)...", flush=True)
        render_logger = MoviePyProgressLogger(callback=progress_callback, cancel_check=cancel_check)
        combined.write_videofile(tmp, fps=export_fps, codec="libx264",
                                 preset="ultrafast", audio=False, threads=2, logger=render_logger)

        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

        if progress_callback:
            progress_callback(97, "Altyazılar ve ses senkronize ediliyor...")

        # ALWAYS create both ASS and SRT
        create_karaoke_subtitles(word_timings, ass, style_opts=subtitle_opts)
        create_srt_file(word_timings, srt)

        print(f"  [Composer] Merging audio + subtitles...")
        ok = _merge(tmp, final_audio, ass, srt, output_path)

        if ok and os.path.exists(output_path):
            mb = os.path.getsize(output_path) / 1048576
            print(f"  [Composer] [OK] {output_path} ({mb:.1f} MB)")
            # Extract high-curiosity Frame 0 / Thumbnail (Item 59, 92)
            thumb_path = output_path.rsplit(".", 1)[0] + "_thumb.jpg"
            extract_frame0_thumbnail(output_path, thumb_path)

            # Scramble MD5/SHA256 hash (Item 429)
            from effects_engine import scramble_mp4_hash
            scramble_mp4_hash(output_path)

            # Rule 30: Apply MP4 free atom size variation (avoid duplicate template byte size)
            try:
                from anti_detect_engine import anti_detect_engine
                size_res = anti_detect_engine.apply_video_size_variation(output_path)
                if size_res.get("success"):
                    print(f"  [Composer] [Kural 30] Dosya Boyutu Varyasyonu uygulandı: +{size_res['delta_kb']} KB 'free' atomu.")
            except Exception as se:
                print(f"  [Composer] Boyut varyasyonu uyarısı: {se}")

            # Rule 29: Spoof file ctime/mtime (15-45 minutes into past)
            try:
                import random, time
                past_secs = random.randint(900, 2700)
                aged_time = time.time() - past_secs
                os.utime(output_path, (aged_time, aged_time))
                print(f"  [Composer] [Kural 29] Dosya meta verisi {past_secs // 60} dk geçmişe yaşlandırıldı (ctime spoofing).")
            except Exception as ute:
                print(f"  [Composer] utime uyarısı: {ute}")

            sync_path = output_path.rsplit(".", 1)[0] + "_synced.mp4"
            synced_output = enforce_av_duration_sync(output_path, sync_path)
            if synced_output == sync_path and os.path.exists(sync_path):
                os.replace(sync_path, output_path)

            metadata_path = output_path.rsplit(".", 1)[0] + "_metadata.mp4"
            titled_output = clean_video_metadata(
                output_path,
                metadata_path,
                title=title or os.path.splitext(os.path.basename(output_path))[0]
            )
            if titled_output == metadata_path and os.path.exists(metadata_path):
                os.replace(metadata_path, output_path)

            # Manuel Yükleme Bilgi Paketi Oluşturma (Rules 80, 83)
            try:
                import json
                from viral_seo_agent import generate_viral_seo_metadata
                clean_title = title or os.path.splitext(os.path.basename(output_path))[0]
                seo_meta = generate_viral_seo_metadata(clean_title)
                manual_pkg = {
                    "video_file": os.path.basename(output_path),
                    "title": seo_meta.get("seo_title", clean_title),
                    "description": seo_meta.get("seo_description", ""),
                    "tags": seo_meta.get("tags", []),
                    "pinned_comment": seo_meta.get("pinned_comment", ""),
                    "rule_80_altered_synthetic": "HAYIR (Yüz klonlama veya manipülasyon yoksa etiket seçilmemeli)",
                    "rule_83_source_reference": "Açıklamaya araştırma ve kaynak referansı eklendi.",
                    "anti_detect_ready": True,
                    "size_mb": round(os.path.getsize(output_path) / 1048576, 2)
                }
                info_json = output_path.rsplit(".", 1)[0] + "_manual_upload_info.json"
                info_txt = output_path.rsplit(".", 1)[0] + "_manual_upload_guide.txt"
                with open(info_json, "w", encoding="utf-8") as fj:
                    json.dump(manual_pkg, fj, ensure_ascii=False, indent=2)
                with open(info_txt, "w", encoding="utf-8") as ft:
                    ft.write(
                        f"=== YOUTUBE SHORTS MANUEL YÜKLEME REHBERİ ===\n\n"
                        f"📌 VİDEO BAŞLIĞI:\n{manual_pkg['title']}\n\n"
                        f"📌 VİDEO AÇIKLAMASI (Kural 83 Kaynak ve Fair Use Referanslı):\n{manual_pkg['description']}\n\n"
                        f"📌 VİDEO ETİKETLERİ:\n{', '.join(manual_pkg['tags'])}\n\n"
                        f"📌 İLK YORUM (Sabitleyin):\n{manual_pkg['pinned_comment']}\n\n"
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

    # Try 1: ASS karaoke
    if os.path.exists(ass) and os.path.getsize(ass) > 50:
        vf_chain = f"{base_vf},ass={base_ass}"
        r = subprocess.run([ffmpeg_exe, "-y", "-i", base_vid, "-i", rel_aud,
            "-vf", vf_chain, "-c:v", "libx264", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
            "-preset", "fast", "-movflags", "+faststart", base_out],
            cwd=out_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode == 0 and os.path.exists(out):
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
        r = subprocess.run([ffmpeg_exe, "-y", "-i", base_vid, "-i", rel_aud,
            "-vf", srt_vf, "-c:v", "libx264", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
            "-preset", "fast", "-movflags", "+faststart", base_out],
            cwd=out_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode == 0 and os.path.exists(out):
            print(f"    [OK] SRT subtitles, Unsharp, Static Grain & Vignette applied (Items 84, 86, 92, 173)")
            return True
        print(f"    SRT failed, trying no subs...")

    # Try 3: No subs (apply unsharp, static grain & vignette filters)
    r = subprocess.run([ffmpeg_exe, "-y", "-i", base_vid, "-i", rel_aud,
        "-vf", base_vf, "-c:v", "libx264", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
        "-preset", "fast", "-movflags", "+faststart", base_out],
        cwd=out_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode == 0 and os.path.exists(out):
        print(f"    Video created with Unsharp, Static Grain & Vignette (no subtitles, 320k AAC 48k)")
        return True
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
    if enable_section2:
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

    # Item 72: Renk Derecelendirme (±%1.5 gamma, kontrast, doygunluk)
    if enable_section2:
        c = apply_color_grading_jitter(c, jitter_range=0.015)

    # Item 71: Perceptual Hashing (pHash) Modülasyonu (%0.5 piksel gürültüsü)
    if enable_section2:
        c = inject_pixel_noise(c, intensity=0.005)

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
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
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
