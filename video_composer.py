"""
Video composer — MoviePy (video only) + ffmpeg (audio + karaoke subs).
3-tier fallback: ASS karaoke → SRT styled → no subs.

Audio mastering, SFX/BGM layering, FFmpeg process supervision, A/V duration sync,
scene building, and manual upload / proof packaging live in:
- `render/composer_mastering.py`
- `render/composer_audio_packaging.py`
- `render/composer_scene_builder.py`
"""
import gc
import os
import random
import shutil
import subprocess
import tempfile
from typing import Optional

import imageio_ffmpeg
from moviepy.editor import ColorClip, CompositeVideoClip, VideoFileClip, concatenate_videoclips, vfx

try:
    import cv2
    cv2.ocl.setUseOpenCL(False)
    cv2.setNumThreads(2)
except ImportError:
    cv2 = None
except Exception:
    pass

import config
from bgm_manager import align_scenes_to_bgm_beats, get_bgm_path, mix_intro_punch_bgm, mix_narration_and_bgm
from effects_engine import (
    apply_affiliate_3d_mockup, apply_alternating_motion, apply_anti_duplicate,
    apply_bookmark_cta_overlay, apply_broll_speed_boost, apply_capcut_density_cuts,
    apply_censored_blur_bait, apply_color_grading_jitter, apply_color_splash_moviepy,
    apply_corner_radius_to_clip, apply_dynamic_progress_bar, apply_end_card_to_video,
    apply_fluid_gradient_background, apply_handheld_camera_shake, apply_heartbeat_zoom,
    apply_horizontal_flip, apply_hybrid_render_overlay, apply_impact_screen_shake,
    apply_infinite_spiral_overlay, apply_ken_burns, apply_keyword_white_flash_overlay,
    apply_mask_wipe_transition, apply_micro_animated_sticker_overlay,
    apply_micro_resolution_crop, apply_micro_zoom_out, apply_multi_layer_overlay,
    apply_neon_countdown_overlay, apply_neon_curiosity_opening_graphic,
    apply_opening_pattern_interrupt, apply_out_of_focus_reveal, apply_particle_overlay,
    apply_pip_overlay, apply_scene_brightness_alternation,
    apply_section2_anti_reused_pipeline, apply_share_cta_overlay,
    apply_slow_motion_highlight, apply_smart_crop, apply_speaker_avatar_overlay,
    apply_speed_ramp, apply_sticky_hook_banner_overlay, apply_time_tunnel_overlay,
    apply_ui_element_overlay, build_emoji_events_from_timings, clean_video_metadata,
    concatenate_with_scene_transitions, create_split_screen_clip, enforce_3s_broll_rule,
    extract_frame0_thumbnail, generate_emoji_subtitle_overlay,
    get_color_grading_ffmpeg_filter, get_diversified_fps, get_ffmpeg_static_grain_filter,
    get_ffmpeg_vignette_filter, get_unsharp_filter, inject_pixel_noise,
    overlay_graphic_badge, overlay_micro_brand_signature, overlay_watermark,
)
from render.composer_audio_packaging import (
    MoviePyProgressLogger,
    _COMPOSER_AUDIO_TEMP_SUFFIXES,
    _cleanup_composer_audio_files,
    _run_cancellable_ffmpeg,
    _select_auto_bgm,
    build_composer_audio_master,
    enforce_av_duration_sync,
    write_composer_manual_upload_and_proof_pack,
)
from render.composer_scene_builder import (
    _face_centered_source,
    _fit,
    _prep,
    apply_composer_global_overlays,
    build_composer_scene_segments,
)
from sfx_manager import add_sfx_to_narration
from subtitle_generator import create_subtitle_files, ffmpeg_force_style_from_opts
from viral_retention_engine import ViralRetentionEngine


def compose_video(
    scene_clips,
    audio_path,
    word_timings,
    output_path,
    title="",
    bgm_track=None,
    bgm_volume=None,
    subtitle_opts=None,
    progress_callback=None,
    cancel_check=None,
    split_screen=False,
    anti_duplicate=True,
    watermark_path=None,
    enable_ken_burns=True,
    enable_section2_filters=True,
    gameplay_path=None,
    niche_id="",
    audio_premastered=False,
    retention_metadata=None,
    hybrid_niche="",
    hybrid_render_overlay=None,
    human_craft=None,
    enable_zoompan=False,
    enable_face_center=False,
    use_gpu_override: Optional[bool] = None,
    **kwargs,
):
    print("\n  [Composer] Building video with 500-Item Optimization Pipeline (Items 71-79)...")
    W, H = getattr(config, "get_target_resolution", lambda: (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))()
    print(f"  [Composer] Hedef Çözünürlük: {W}x{H} (Mod: {getattr(config, 'RENDER_RESOLUTION_MODE', '1080p')})", flush=True)
    _safe = getattr(config, "RENDER_SAFE_MODE", True)
    if _safe:
        print("  [Composer] ⚠ RENDER_SAFE_MODE=true — ağır overlay/efektler bypass (Tam Kural için false yap)", flush=True)
    else:
        print("  [Composer] RENDER_SAFE_MODE=false — full overlays active", flush=True)

    _hc = human_craft if isinstance(human_craft, dict) else {}
    _edir = _hc.get("edit_directives") or {}
    _mute_hook = (_hc.get("mute_hook_line") or "").strip()
    try:
        from craft import clamp_interrupt_duration
        _interrupt_dur = clamp_interrupt_duration(_hc, default=1.5)
    except Exception:
        _interrupt_dur = float(_edir.get("pattern_interrupt_first_sec") or 1.5)
    _max_hold = float(_edir.get("max_shot_hold_sec") or 3.5)
    _cut_sec = float(_edir.get("target_cut_sec") or 2.8)
    if _hc:
        print(
            f"  [Composer] HumanCraft POV={_hc.get('pov_angle')} "
            f"hook={_mute_hook[:40]!r} max_hold={_max_hold}s cut={_cut_sec}s interrupt={_interrupt_dur}s",
            flush=True,
        )
        try:
            from craft import subtitle_opts_from_craft
            from subtitle_generator import merge_studio_subtitle_opts
            craft_subs = subtitle_opts_from_craft(_hc)
            subtitle_opts = dict(subtitle_opts or {})
            subtitle_opts = merge_studio_subtitle_opts(
                "",
                base=subtitle_opts,
                font_size=subtitle_opts.get("font_size"),
                y_position=subtitle_opts.get("y_position") if subtitle_opts.get("honor_y_position") else None,
                craft_opts=craft_subs,
            )
            print(
                f"  [Composer] HumanCraft captions mid-frame "
                f"y={subtitle_opts.get('y_position')} words/chunk={subtitle_opts.get('max_words_per_frame')}",
                flush=True,
            )
        except Exception as se:
            print(f"  [Composer] HumanCraft subtitle merge notice: {se}", flush=True)

    if cancel_check and cancel_check():
        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    processed_audio, final_audio, scene_clips = build_composer_audio_master(
        scene_clips=scene_clips,
        audio_path=audio_path,
        word_timings=word_timings,
        output_path=output_path,
        title=title,
        niche_id=niche_id,
        bgm_track=bgm_track,
        bgm_volume=bgm_volume,
        audio_premastered=audio_premastered,
        enable_section2_filters=enable_section2_filters,
        cancel_check=cancel_check,
        extra_kwargs=kwargs,
        select_auto_bgm_fn=_select_auto_bgm,
    )

    segs = []
    combined = None
    tmp = output_path.rsplit(".", 1)[0] + "_tmp.mp4"
    ass = output_path.rsplit(".", 1)[0] + ".ass"
    srt = output_path.rsplit(".", 1)[0] + ".srt"

    try:
        segs = build_composer_scene_segments(
            scene_clips=scene_clips,
            W=W,
            H=H,
            split_screen=split_screen,
            enable_section2_filters=enable_section2_filters,
            enable_ken_burns=enable_ken_burns,
            gameplay_path=gameplay_path,
            enable_face_center=enable_face_center,
            niche_id=niche_id,
            title=title,
            hc=_hc,
            max_hold=_max_hold,
            cut_sec=_cut_sec,
            interrupt_dur=_interrupt_dur,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )

        if not segs:
            return ""

        transition_kind = "hard" if getattr(config, "RENDER_SAFE_MODE", True) else "crossfade"
        try:
            combined = concatenate_with_scene_transitions(segs, transition=transition_kind, fade_dur=0.22)
        except Exception:
            combined = concatenate_videoclips(segs, method="chain")

        # Delegated to apply_composer_global_overlays:
        # apply_opening_pattern_interrupt, apply_share_cta_overlay,
        # apply_scene_brightness_alternation, apply_neon_countdown_overlay,
        # apply_censored_blur_bait, apply_fluid_gradient_background (Item 123)
        combined = apply_composer_global_overlays(
            combined=combined,
            scene_clips=scene_clips,
            word_timings=word_timings,
            W=W,
            H=H,
            enable_section2_filters=enable_section2_filters,
            anti_duplicate=anti_duplicate,
            watermark_path=watermark_path,
            mute_hook=_mute_hook,
            retention_metadata=retention_metadata,
            title=title,
            hybrid_render_overlay=hybrid_render_overlay,
            hybrid_niche=hybrid_niche,
        )

        print(f"  [Composer] Duration: {combined.duration:.1f}s")

        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

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

        cpu_cores = os.cpu_count() or 8
        configured_threads = getattr(config, "RENDER_THREADS", 4) or 4
        render_threads = int(kwargs.get("render_threads") if kwargs.get("render_threads") is not None else configured_threads)
        render_threads = max(2, min(4, render_threads))

        from system_resilience import get_export_codec_settings
        use_gpu = (
            getattr(config, "USE_GPU_ACCELERATION", True)
            if use_gpu_override is None
            else use_gpu_override
        )
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
                combined.write_videofile(
                    tmp, fps=export_fps, codec="libx264",
                    preset="ultrafast", audio=False, threads=render_threads,
                    ffmpeg_params=["-tune", "fastdecode", "-pix_fmt", "yuv420p"],
                    logger=render_logger,
                )
            else:
                raise

        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

        if progress_callback:
            progress_callback(97, "Altyazılar ve ses senkronize ediliyor...")

        sub_opts = dict(subtitle_opts or {})
        sub_opts.setdefault("hook_card_text", title)
        if "audio_path" not in sub_opts and final_audio:
            sub_opts["audio_path"] = final_audio
        create_subtitle_files(word_timings, ass, srt, style_opts=sub_opts)

        try:
            from voice_humanizer import normalize_ebu_r128
            master_norm_audio = output_path.rsplit(".", 1)[0] + "_master_norm.wav"
            norm_result = normalize_ebu_r128(final_audio, master_norm_audio, target_lufs=-14.0)
            if norm_result and os.path.exists(norm_result):
                final_audio = norm_result
                print("  [Composer] [AudioMaster] Final audio normalized to -14.0 LUFS EBU R128 standard.")
        except Exception as nae:
            print(f"  [Composer] Final audio normalization notice: {nae}")

        print("  [Composer] Merging audio + subtitles...")
        ok = _merge(
            tmp, final_audio, ass, srt, output_path,
            style_opts=sub_opts, render_threads=render_threads,
            cancel_check=cancel_check,
        )

        if ok and os.path.exists(output_path):
            mb = os.path.getsize(output_path) / 1048576
            print(f"  [Composer] [OK] {output_path} ({mb:.1f} MB)")
            thumb_path = output_path.rsplit(".", 1)[0] + "_thumb.jpg"
            extract_frame0_thumbnail(output_path, thumb_path)

            sync_path = output_path.rsplit(".", 1)[0] + "_synced.mp4"
            synced_output = enforce_av_duration_sync(output_path, sync_path)
            if synced_output == sync_path and os.path.exists(sync_path):
                os.replace(sync_path, output_path)

            print("  [Composer] Compliance: media bytes/timestamps preserved; anti-detect transforms disabled.")

            if not getattr(config, "RENDER_SAFE_MODE", True):
                try:
                    micro_path = output_path.rsplit(".", 1)[0] + "_micro.mp4"
                    cropped = apply_micro_resolution_crop(output_path, micro_path)
                    if cropped != output_path and os.path.exists(cropped):
                        os.replace(cropped, output_path)
                        print("  [Composer] Micro resolution crop applied (Item 124).")
                except Exception as mre:
                    print(f"  [Composer] Item 124 micro crop notice: {mre}")

            from viral_seo_agent import export_seo_operator_pack
            write_composer_manual_upload_and_proof_pack(
                output_path=output_path,
                title=title,
                scene_clips=scene_clips,
                retention_metadata=retention_metadata,
                thumb_path=thumb_path,
                anti_duplicate=anti_duplicate,
                split_screen=split_screen,
                enable_ken_burns=enable_ken_burns,
                export_seo_operator_pack_fn=export_seo_operator_pack,
            )
            return output_path
        return ""
    finally:
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
        gc.collect()

        for f in [tmp]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

        _cleanup_composer_audio_files(
            output_path, audio_path, processed_audio, final_audio,
        )


def _merge(vid, aud, ass, srt, out, style_opts=None, render_threads=None, cancel_check=None):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    out_dir = os.path.dirname(os.path.abspath(out))

    base_vid = os.path.basename(vid)
    base_ass = os.path.basename(ass)
    base_srt = os.path.basename(srt)
    base_out = os.path.basename(out)
    rel_aud = os.path.relpath(aud, out_dir).replace("\\", "/")

    color_vf = get_color_grading_ffmpeg_filter(jitter_range=0.015)
    unsharp_vf = get_unsharp_filter(luma_matrix=5, luma_amount=0.8)
    grain_vf = get_ffmpeg_static_grain_filter()
    vignette_vf = get_ffmpeg_vignette_filter(angle=0.18)
    base_vf = f"{color_vf},{unsharp_vf},{grain_vf},{vignette_vf}"

    use_gpu = getattr(config, "USE_GPU_ACCELERATION", True)
    gpu_codec = getattr(config, "GPU_CODEC", "h264_nvenc")
    render_threads = int(
        render_threads
        if render_threads not in (None, 0)
        else (getattr(config, "RENDER_THREADS", 8) or 8)
    )
    output_attempted = False
    merge_succeeded = False

    hook_temp = ""
    hook_path = ""
    hook_height = 0
    hook_opts = style_opts or {}
    hook_text = str(hook_opts.get("hook_card_text") or "").strip()
    if hook_text and not hook_opts.get("disable_hook_card", False):
        try:
            from effects.hook_card import create_hook_image
            hook_width, hook_height = getattr(
                config, "get_target_resolution", lambda: (config.VIDEO_WIDTH, config.VIDEO_HEIGHT)
            )()
            fd, hook_temp = tempfile.mkstemp(prefix="hook_card_", suffix=".png", dir=out_dir)
            os.close(fd)
            hook_path = create_hook_image(hook_text, int(hook_width), hook_temp) or ""
            if not os.path.isfile(hook_path):
                hook_path = ""
        except Exception as hook_error:
            print(f"    [Composer] Hook card notice: {hook_error}")
            hook_path = ""

    def execute_ffmpeg_pass(vf_string):
        """Attempts GPU NVENC encoding first, automatically falling back to CPU multi-threading."""
        nonlocal output_attempted
        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

        def mark_output_attempted():
            nonlocal output_attempted
            output_attempted = True

        extra_inputs = []
        filter_args = ["-vf", vf_string]
        if hook_path:
            from effects.hook_card import hook_overlay_filter
            extra_inputs = ["-loop", "1", "-t", "2.5", "-i", hook_path]
            graph = (
                f"[0:v]{vf_string}[hook_base];[2:v]format=rgba[hook_image];"
                + hook_overlay_filter("hook_base", "hook_image", "hook_video", int(hook_height))
            )
            filter_args = ["-filter_complex", graph, "-map", "[hook_video]", "-map", "1:a:0"]
        if use_gpu and gpu_codec == "h264_nvenc":
            gpu_cmd = [
                ffmpeg_exe, "-y", "-hwaccel", "cuda", "-i", base_vid, "-i", rel_aud,
                *extra_inputs, *filter_args,
                "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "22", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", base_out,
            ]
            if cancel_check:
                r = _run_cancellable_ffmpeg(
                    gpu_cmd, out_dir, cancel_check, on_started=mark_output_attempted,
                )
            else:
                mark_output_attempted()
                r = subprocess.run(
                    gpu_cmd, cwd=out_dir,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
            if r.returncode == 0 and os.path.exists(out):
                return True, r
            else:
                print(
                    f"    [Composer] NVENC merge uyarisi "
                    f"({r.stderr.decode('utf-8', errors='ignore')[:120]}), CPU'ya geciliyor...",
                    flush=True,
                )

        cpu_cmd = [
            ffmpeg_exe, "-y", "-i", base_vid, "-i", rel_aud,
            *extra_inputs, *filter_args,
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "fastdecode",
            "-threads", str(render_threads), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", base_out,
        ]
        if cancel_check:
            r = _run_cancellable_ffmpeg(
                cpu_cmd, out_dir, cancel_check, on_started=mark_output_attempted,
            )
        else:
            mark_output_attempted()
            r = subprocess.run(
                cpu_cmd, cwd=out_dir,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        return (r.returncode == 0 and os.path.exists(out)), r

    try:
        if os.path.exists(ass) and os.path.getsize(ass) > 50:
            vf_chain = f"{base_vf},ass={base_ass}"
            success, r = execute_ffmpeg_pass(vf_chain)
            if success:
                merge_succeeded = True
                print("    [OK] Karaoke subtitles, Unsharp, Static Grain & Vignette applied (Items 84, 86, 92, 173)")
                return True
            print(f"    ASS failed ({r.stderr.decode('utf-8', errors='ignore')[:150]}), trying SRT...")

        if os.path.exists(srt) and os.path.getsize(srt) > 10:
            force_style = ffmpeg_force_style_from_opts(style_opts or {})
            srt_vf = f"{base_vf},subtitles={base_srt}:force_style='{force_style}'"
            success, r = execute_ffmpeg_pass(srt_vf)
            if success:
                merge_succeeded = True
                print("    [OK] SRT subtitles, Unsharp, Static Grain & Vignette applied (Items 84, 86, 92, 173)")
                return True
            print("    SRT failed, trying no subs...")

        success, r = execute_ffmpeg_pass(base_vf)
        if success:
            merge_succeeded = True
            print("    Video created with Unsharp, Static Grain & Vignette (no subtitles, 192k AAC 48k)")
            return True
        return False
    finally:
        if output_attempted and not merge_succeeded and os.path.isfile(out):
            try:
                os.remove(out)
            except OSError as cleanup_err:
                print(
                    f"    [Composer] Failed merge output cleanup failed for {out}: {cleanup_err}",
                    flush=True,
                )
        if hook_temp:
            try:
                os.remove(hook_temp)
            except OSError:
                pass
