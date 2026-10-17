"""
Native FFmpeg filter_complex render graph (Item 418).
Concat demuxer + scale/crop/fps + ASS + color/grain/vignette + audio → single encode.
MoviePy remains available as capability fallback via video_composer.compose_video.

Probing, per-scene filter chains, and global overlay builders are modularized into:
- `render/ffmpeg_probes.py`
- `render/ffmpeg_scene_filters.py`
- `render/ffmpeg_overlays.py`
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import imageio_ffmpeg

import config
from .ffmpeg_overlays import apply_global_overlays_to_graph
from .ffmpeg_probes import (
    VIDEO_DURATION_SAFETY_MARGIN,
    _BT2020_SPACE,
    _BT601_SPACE,
    _BT709_TAG,
    _FULL_RANGE,
    _HDR_TRANSFER,
    _build_encoder_candidates,
    _cleanup_ffmpeg_process,
    _escape_ass_path,
    _escape_drawtext,
    _escape_filter_path,
    _probe_audio_duration,
    _probe_dimensions,
    _probe_duration,
    _probe_has_audio,
    _probe_is_landscape,
    _probe_video_fps,
    _resolve_clip_transition,
    _validate_clip_paths,
    _with_ffgraph_temp_dir,
    align_even_dimension,
    color_convert_filter,
    face_cover_crop_x,
    gameplay_start_seconds,
    get_required_video_duration,
    probe_stream_color,
)
from .ffmpeg_scene_filters import (
    _keyframed_camera_expression,
    _plan_cutaways,
    build_all_scene_inputs_and_filters,
    build_scene_filter_chain,
    cheap_pan_filter,
    get_look_filters,
    resolve_camera_intent,
    zoompan_filter,
)
from .keyframe_motion import KeyframeProperty, KeyframeTrajectory


def _render_with_ffmpeg_graph_impl(
    clips: List[Dict[str, Any]],
    audio_path: str,
    output_path: str,
    *,
    word_timings: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    subtitle_opts: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable] = None,
    cancel_check: Optional[Callable] = None,
    anti_duplicate: bool = True,
    enable_ken_burns: bool = True,
    enable_zoompan: bool = False,
    enable_broll: bool = False,
    enable_face_center: bool = False,
    ass_path: Optional[str] = None,
    emphasis_ass_path: Optional[str] = None,
    enable_emphasis_card: bool = False,
    gameplay_path: Optional[str] = None,
    hybrid_render_overlay: Optional[Dict[str, Any]] = None,
    enable_audio_visualizer: bool = False,
    audio_visualizer_mode: str = "line",
    audio_visualizer_color: str = "0x00D7FF",
    enable_news_ticker: bool = False,
    news_ticker_text: Optional[str] = None,
    niche_id: str = "",
    enable_reddit_card: bool = False,
    reddit_card_path: Optional[str] = None,
    thread_limit: Optional[int] = None,
    use_gpu_override: Optional[bool] = None,
    **kwargs: Any,
) -> str:
    """
    Item 418: Single filter_complex concat + look + optional ASS + audio mux + NVENC/libx264.
    Returns output_path on success, empty string on failure (caller may fallback to MoviePy).
    """
    valid = [c for c in clips if c.get("path") and os.path.exists(c["path"])]
    if not valid or not audio_path or not os.path.exists(audio_path):
        return ""
    if len(valid) < len(clips):
        print(
            f"  [FFmpegGraph] ABORT: {len(valid)}/{len(clips)} clips valid "
            f"-- partial fetch would repeat one visual",
            flush=True,
        )
        return ""

    W, H = getattr(config, "get_target_resolution", lambda: (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))()
    W = align_even_dimension(int(W))
    H = align_even_dimension(int(H))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_dir = kwargs.pop("_ffgraph_temp_dir")

    if not ass_path and word_timings:
        try:
            from subtitle_generator import create_karaoke_subtitles
            ass_path = os.path.join(tmp_dir, "subs.ass")
            sub_opts = dict(subtitle_opts or {})
            if "audio_path" not in sub_opts and audio_path:
                sub_opts["audio_path"] = audio_path
            create_karaoke_subtitles(
                word_timings, ass_path, style_opts=sub_opts,
            )
        except Exception as e:
            print(f"  [FFmpegGraph] ASS notice: {e}")
            ass_path = None

    if progress_callback:
        progress_callback(76, "[FFmpegGraph] Filter complex derleniyor (Madde 418)...")

    if getattr(config, "FPS_DIVERSIFY", True):
        from compliance.anti_repetition import get_diversified_fps
        output_fps = get_diversified_fps()
    else:
        output_fps = float(getattr(config, "FPS", 30) or 30)

    from system_resilience import get_ffmpeg_loglevel
    cmd: List[str] = [ffmpeg, "-y", "-hide_banner", "-loglevel", get_ffmpeg_loglevel()]
    filter_parts: List[str] = []
    n = len(valid)

    # Color space normalization & BT.709 tagging (_BT709_TAG) applied in build_all_scene_inputs_and_filters
    next_input, total_dur = build_all_scene_inputs_and_filters(
        valid=valid,
        cmd=cmd,
        filter_parts=filter_parts,
        W=W,
        H=H,
        output_fps=output_fps,
        gameplay_path=gameplay_path,
        enable_ken_burns=enable_ken_burns,
        enable_zoompan=enable_zoompan,
        enable_face_center=enable_face_center,
        anti_duplicate=anti_duplicate,
        cancel_check=cancel_check,
    )

    vlabel, audio_idx, next_input = apply_global_overlays_to_graph(
        cmd=cmd,
        filter_parts=filter_parts,
        valid=valid,
        total_dur=total_dur,
        next_input=next_input,
        W=W,
        H=H,
        tmp_dir=tmp_dir,
        audio_path=audio_path,
        word_timings=word_timings,
        title=title,
        subtitle_opts=subtitle_opts,
        enable_broll=enable_broll,
        ass_path=ass_path,
        emphasis_ass_path=emphasis_ass_path,
        enable_emphasis_card=enable_emphasis_card,
        hybrid_render_overlay=hybrid_render_overlay,
        enable_audio_visualizer=enable_audio_visualizer,
        audio_visualizer_mode=audio_visualizer_mode,
        audio_visualizer_color=audio_visualizer_color,
        enable_news_ticker=enable_news_ticker,
        news_ticker_text=news_ticker_text,
        niche_id=niche_id,
        enable_reddit_card=enable_reddit_card,
        reddit_card_path=reddit_card_path,
        extra_kwargs=kwargs,
    )

    filter_complex = ";".join(filter_parts)

    from system_resilience import get_encoder_fallback_chain
    use_gpu = (
        getattr(config, "USE_GPU_ACCELERATION", True)
        if use_gpu_override is None
        else use_gpu_override
    )
    gpu_codec = getattr(config, "GPU_CODEC", "")
    threads = int(
        thread_limit
        if thread_limit is not None
        else getattr(config, "FFMPEG_THREADS", getattr(config, "RENDER_THREADS", 4))
    )
    threads = max(1, threads)
    encoder_candidates = get_encoder_fallback_chain(use_gpu, gpu_codec)
    fps = output_fps

    _clip_total = sum(float(c.get("duration", 3.0)) for c in valid)
    _audio_dur = _probe_audio_duration(ffmpeg, audio_path)
    if _audio_dur > 0:
        _t_limit = min(_audio_dur, _clip_total) + 0.5
        print(
            f"  [FFmpegGraph] K2-AV: audio={_audio_dur:.2f}s clips={_clip_total:.2f}s "
            f"→ encode limit={_t_limit:.2f}s",
            flush=True,
        )
    else:
        _t_limit = _clip_total + 0.5
        print(
            f"  [FFmpegGraph] K2-AV: audio probe failed → limit=clips+0.5={_t_limit:.2f}s",
            flush=True,
        )
    av_clamp = ["-t", f"{_t_limit:.3f}"]

    if enable_zoompan:
        print("  [FFmpegGraph] zoompan AÇIK — bu geçiş render süresini uzatır", flush=True)

    output_attempted = False
    render_succeeded = False
    try:
        from render.encoding_optimizer import METADATA_SCRUB
    except Exception:
        METADATA_SCRUB = ["-map_metadata", "-1"]
    try:
        from services.process_cleaner import GLOBAL_ROLLBACK_MANAGER
    except Exception:
        GLOBAL_ROLLBACK_MANAGER = None

    try:
        for candidate_idx, (vcodec, mode) in enumerate(encoder_candidates):
            if cancel_check and cancel_check():
                raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass
            output_attempted = True

            run_cmd = list(cmd)
            run_cmd.extend([
                "-filter_complex", filter_complex,
                "-map", vlabel,
                "-map", f"{audio_idx}:a",
                *vcodec,
                "-r", f"{fps:.2f}",
                "-colorspace", "bt709",
                "-color_primaries", "bt709",
                "-color_trc", "bt709",
                "-color_range", "tv",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                *av_clamp,
                "-movflags", "+faststart",
                *METADATA_SCRUB,
                "-metadata", f"title={title or 'Shorts'}",
                "-metadata", "encoder=Final Cut Pro",
                "-threads", str(threads),
                output_path,
            ])

            print(f"  [FFmpegGraph] Export: {W}x{H} @ {fps:.2f} | {mode} | {n} scenes | Madde 418", flush=True)
            if progress_callback:
                progress_callback(80, f"[FFmpegGraph] Kodlama başlıyor ({mode})...")

            try:
                proc = None
                reader_thread = None
                proc = subprocess.Popen(
                    run_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
                )
                if GLOBAL_ROLLBACK_MANAGER is not None:
                    GLOBAL_ROLLBACK_MANAGER.register_process(proc)
                stderr_queue: queue.Queue[str] = queue.Queue()

                def _stderr_reader(p=proc, q=stderr_queue):
                    try:
                        while p.stderr:
                            line = p.stderr.readline()
                            if not isinstance(line, str) or not line:
                                break
                            q.put(line)
                    except Exception:
                        pass

                reader_thread = threading.Thread(target=_stderr_reader, daemon=True)
                reader_thread.start()

                stderr_data = []
                last_heartbeat = time.time()
                inactivity_limit = 120.0

                while True:
                    if cancel_check and cancel_check():
                        proc.terminate()
                        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

                    try:
                        line = stderr_queue.get(timeout=1.0)
                        stderr_data.append(line)
                        last_heartbeat = time.time()
                        if "time=" in line and progress_callback:
                            progress_callback(88, f"[FFmpegGraph] Kodlama devam ediyor ({mode})...")
                    except queue.Empty:
                        pass

                    if proc.poll() is not None:
                        while not stderr_queue.empty():
                            try:
                                stderr_data.append(stderr_queue.get_nowait())
                            except queue.Empty:
                                break
                        break

                    if time.time() - last_heartbeat > inactivity_limit:
                        print(f"  [FFmpegGraph] {mode} {inactivity_limit}s sessiz kaldı (zombi koruması), sonlandırılıyor...", flush=True)
                        proc.terminate()
                        break

                if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) >= 100000:
                    if progress_callback:
                        progress_callback(95, "[FFmpegGraph] Tamamlandı")
                    print(f"  [FFmpegGraph] OK → {output_path} ({os.path.getsize(output_path)//1024} KB) [{mode}]", flush=True)

                    try:
                        from anti_detect.post_render import apply_post_render_humanization
                        post = apply_post_render_humanization(output_path, title=title or "")
                        if post.get("metadata_applied"):
                            print("  [FFmpegGraph] [PostRender] metadata cleaned and title recorded.")
                    except Exception as pr_err:
                        print(f"  [FFmpegGraph] PostRender note: {pr_err}")

                    render_succeeded = True
                    return output_path
                else:
                    err = "".join(stderr_data)[-800:]
                    print(f"  [FFmpegGraph] {mode} başarısız oldu (kod: {proc.returncode}): {err[:200]}", flush=True)
                    if candidate_idx < len(encoder_candidates) - 1:
                        next_mode = encoder_candidates[candidate_idx + 1][1]
                        print(f"  [FFmpegGraph] Sıradaki kodlayıcıya geçiliyor: {next_mode}", flush=True)
                        continue
            except InterruptedError:
                raise
            except Exception as candidate_err:
                print(f"  [FFmpegGraph] {mode} denemesinde istisna: {candidate_err}", flush=True)
                if candidate_idx < len(encoder_candidates) - 1:
                    continue
            finally:
                if GLOBAL_ROLLBACK_MANAGER is not None and proc is not None:
                    GLOBAL_ROLLBACK_MANAGER.unregister_process(proc)
                _cleanup_ffmpeg_process(proc, reader_thread)

        return ""
    except InterruptedError:
        raise
    except Exception as e:
        print(f"  [FFmpegGraph] Exception: {e}")
        return ""
    finally:
        if output_attempted and not render_succeeded and os.path.isfile(output_path):
            try:
                os.remove(output_path)
            except OSError as cleanup_err:
                print(
                    f"  [FFmpegGraph] Başarısız render çıktısı temizlenemedi: "
                    f"{output_path}: {cleanup_err}",
                    flush=True,
                )


render_with_ffmpeg_graph = _with_ffgraph_temp_dir(_render_with_ffmpeg_graph_impl)


def _needs_moviepy_composer(kwargs: Dict[str, Any]) -> bool:
    """
    FFmpeg graph covers concat + look + ASS + NVENC + hybrid UI in one pass.
    MoviePy only when explicit legacy fallback is requested or when an unknown,
    non-native overlay format is encountered.
    """
    if kwargs.get("force_moviepy"):
        return True
    if kwargs.get("enable_native_hybrid") is True:
        return False
    overlay = kwargs.get("hybrid_render_overlay") or {}
    if isinstance(overlay, dict) and (overlay.get("ui_type") or overlay.get("overlay")):
        if getattr(config, "ENABLE_NATIVE_HYBRID_OVERLAY", False):
            return False
        return True
    return False


def compose_via_director(
    clips: List[Dict[str, Any]],
    audio_path: str,
    word_timings: List[Dict[str, Any]],
    output_path: str,
    **kwargs,
) -> str:
    """
    Prefer FFmpeg graph; fall back to MoviePy compose_video for capability gaps.
    """
    prefer_ffmpeg = kwargs.pop("prefer_ffmpeg", True)
    enable_native_hybrid = kwargs.pop(
        "enable_native_hybrid", getattr(config, "ENABLE_NATIVE_HYBRID_OVERLAY", False)
    )
    use_gpu_override = kwargs.pop("use_gpu_override", None)
    if not enable_native_hybrid and _needs_moviepy_composer(kwargs):
        print(
            "  [Director] MoviePy compose_video — full Section-2/B5 overlay pipeline "
            "(FFmpeg graph is look+subs only)",
            flush=True,
        )
        from video_composer import compose_video
        kwargs.setdefault("audio_premastered", kwargs.get("audio_premastered", True))
        return compose_video(
            clips, audio_path, word_timings, output_path,
            use_gpu_override=use_gpu_override,
            **kwargs,
        )

    if prefer_ffmpeg and getattr(config, "ENABLE_FFMPEG_GRAPH", True):
        result = render_with_ffmpeg_graph(
            clips, audio_path, output_path,
            word_timings=word_timings,
            title=kwargs.get("title", ""),
            subtitle_opts=kwargs.get("subtitle_opts"),
            progress_callback=kwargs.get("progress_callback"),
            cancel_check=kwargs.get("cancel_check"),
            anti_duplicate=kwargs.get("anti_duplicate", True),
            enable_ken_burns=kwargs.get("enable_ken_burns", True),
            enable_zoompan=bool(kwargs.get("enable_zoompan", False)),
            enable_broll=bool(kwargs.get("enable_broll", False) or kwargs.get("enable_broll_insert", False)),
            enable_face_center=bool(kwargs.get("enable_face_center", False)),
            emphasis_ass_path=kwargs.get("emphasis_ass_path"),
            enable_emphasis_card=bool(kwargs.get("enable_emphasis_card", False)),
            gameplay_path=kwargs.get("gameplay_path") if kwargs.get("split_screen") or kwargs.get("gameplay_path") else None,
            hybrid_render_overlay=kwargs.get("hybrid_render_overlay"),
            enable_audio_visualizer=bool(kwargs.get("enable_audio_visualizer", False)),
            audio_visualizer_mode=kwargs.get("audio_visualizer_mode", "line"),
            audio_visualizer_color=kwargs.get("audio_visualizer_color", "0x00D7FF"),
            enable_news_ticker=bool(kwargs.get("enable_news_ticker", False)),
            news_ticker_text=kwargs.get("news_ticker_text"),
            niche_id=kwargs.get("niche_id", ""),
            enable_reddit_card=bool(kwargs.get("enable_reddit_card", False)),
            reddit_card_path=kwargs.get("reddit_card_path"),
            thread_limit=kwargs.get("ffmpeg_thread_limit"),
            use_gpu_override=use_gpu_override,
            director=kwargs.get("director"),
        )
        if result:
            return result
        print("  [Director] FFmpeg graph fallback → MoviePy compose_video")

    from video_composer import compose_video
    kwargs["audio_premastered"] = kwargs.pop("audio_premastered", True)
    return compose_video(
        clips, audio_path, word_timings, output_path,
        use_gpu_override=use_gpu_override,
        **kwargs,
    )
