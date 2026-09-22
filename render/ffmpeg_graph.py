"""
Native FFmpeg filter_complex render graph (Item 418).
Concat demuxer + scale/crop/fps + ASS + color/grain/vignette + audio → single encode.
MoviePy remains available as capability fallback via video_composer.compose_video.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Any, Callable, Dict, List, Optional, Tuple

import imageio_ffmpeg

import config


def _escape_ass_path(path: str) -> str:
    # FFmpeg subtitles filter on Windows needs escaped drive and slashes
    p = os.path.abspath(path).replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        p = p[0] + "\\:" + p[2:]
    return p.replace("'", r"\'")


def _probe_has_audio(path: str) -> bool:
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        r = subprocess.run(
            [exe, "-i", path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=20,
        )
        return "Audio:" in (r.stderr or "")
    except Exception:
        return False


def cheap_pan_filter(width: int, height: int, duration: float, scene_index: int = 0) -> str:
    """
    Slow push via overscale + moving crop.
    Replaces zoompan. zoompan resamples every pixel on one thread.
    """
    dur = max(float(duration), 0.1)
    sw = max(width + 2, (int(width * 1.08) // 2) * 2)
    sh = max(height + 2, (int(height * 1.08) // 2) * 2)
    direction = scene_index % 4
    if direction == 0:
        xexpr = f"(in_w-out_w)*t/{dur:.3f}"
        yexpr = "(in_h-out_h)/2"
    elif direction == 1:
        xexpr = f"(in_w-out_w)*(1-t/{dur:.3f})"
        yexpr = "(in_h-out_h)/2"
    elif direction == 2:
        xexpr = "(in_w-out_w)/2"
        yexpr = f"(in_h-out_h)*t/{dur:.3f}"
    else:
        xexpr = "(in_w-out_w)/2"
        yexpr = f"(in_h-out_h)*(1-t/{dur:.3f})"
    return f"scale={sw}:{sh},crop={width}:{height}:x='{xexpr}':y='{yexpr}'"


def zoompan_filter(width: int, height: int, duration: float) -> str:
    """Opt-in slow zoom. Much slower than cheap_pan_filter."""
    fps = float(getattr(config, "FPS", 30) or 30)
    frames = max(1, int(max(float(duration), 0.1) * fps))
    return (
        f"zoompan=z='min(zoom+0.0008,1.04)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={width}x{height}:fps={fps:.2f}"
    )


def build_scene_filter_chain(
    input_index: int,
    duration: float,
    width: int,
    height: int,
    scene_index: int,
    enable_ken_burns: bool = True,
    enable_zoompan: bool = False,
    split_screen: bool = False,
    gameplay_index: Optional[int] = None,
    gameplay_label: Optional[str] = None,
) -> str:
    """
    Per-input video chain: trim, fps, scale/crop cover, optional crop-pan.
    Split: top 58% scene, bottom 42% looped gameplay (soap / satisfying).
    """
    split = bool(split_screen and (gameplay_label or gameplay_index is not None))
    out_h = (int(height * 0.58) // 2) * 2 if split else height
    fps = getattr(config, "FPS", 30)
    # Cover crop to 9:16 (or the top panel when split)
    base = (
        f"[{input_index}:v]"
        f"trim=duration={duration:.3f},setpts=PTS-STARTPTS,"
        f"fps={fps},"
        f"scale={width}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={width}:{out_h}"
    )
    try:
        from effects.filters import get_scene_brightness_alternation_filter
        base += f",{get_scene_brightness_alternation_filter(scene_index)}"
    except Exception:
        pass
    if enable_zoompan:
        base += "," + zoompan_filter(width, out_h, duration)
    elif enable_ken_burns:
        base += "," + cheap_pan_filter(width, out_h, duration, scene_index)
    if not split:
        base += f"[v{scene_index}]"
        return base
    bot_h = height - out_h
    base += f"[top{scene_index}]"
    gp_src = gameplay_label or f"[{gameplay_index}:v]"
    gameplay = (
        f"{gp_src}trim=duration={duration:.3f},setpts=PTS-STARTPTS,"
        f"fps={fps},"
        f"scale={width}:{bot_h}:force_original_aspect_ratio=increase,"
        f"crop={width}:{bot_h}[bot{scene_index}]"
    )
    stack = f"[top{scene_index}][bot{scene_index}]vstack=inputs=2[v{scene_index}]"
    return base + ";" + gameplay + ";" + stack


def get_look_filters(width: int, height: int, anti_duplicate: bool = True) -> str:
    """Color jitter, unsharp, grain, vignette (Items 72, 84, 86, 92)."""
    import random
    gamma = 1.0 + random.uniform(-0.015, 0.015)
    contrast = 1.0 + random.uniform(-0.015, 0.015)
    saturation = 1.0 + random.uniform(-0.015, 0.015)
    parts = [
        f"eq=gamma={gamma:.4f}:contrast={contrast:.4f}:saturation={saturation:.4f}",
        "unsharp=5:5:0.8:5:5:0.0",
    ]
    if anti_duplicate:
        parts.append("noise=alls=3:allf=t")
    # Soft vignette
    parts.append("vignette=PI/5")
    return ",".join(parts)


def render_with_ffmpeg_graph(
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
    ass_path: Optional[str] = None,
    gameplay_path: Optional[str] = None,
) -> str:
    """
    Item 418: Single filter_complex concat + look + optional ASS + audio mux + NVENC/libx264.
    Returns output_path on success, empty string on failure (caller may fallback to MoviePy).
    """
    valid = [c for c in clips if c.get("path") and os.path.exists(c["path"])]
    if not valid or not audio_path or not os.path.exists(audio_path):
        return ""
    # P0-03: never repeat one stock clip when fetch partially failed
    if len(valid) < len(clips):
        print(
            f"  [FFmpegGraph] ABORT: {len(valid)}/{len(clips)} clips valid "
            f"-- partial fetch would repeat one visual",
            flush=True,
        )
        return ""

    W, H = getattr(config, "get_target_resolution", lambda: (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))()
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_dir = tempfile.mkdtemp(prefix="ffgraph_")
    concat_list = os.path.join(tmp_dir, "concat.txt")

    # Generate ASS if needed
    if not ass_path and word_timings:
        try:
            from subtitle_generator import create_karaoke_subtitles
            ass_path = os.path.join(tmp_dir, "subs.ass")
            create_karaoke_subtitles(
                word_timings, ass_path, style_opts=subtitle_opts or {},
            )
        except Exception as e:
            print(f"  [FFmpegGraph] ASS notice: {e}")
            ass_path = None

    if progress_callback:
        progress_callback(76, "[FFmpegGraph] Filter complex derleniyor (Madde 418)...")

    # Build inputs
    from system_resilience import get_ffmpeg_loglevel
    cmd: List[str] = [ffmpeg, "-y", "-hide_banner", "-loglevel", get_ffmpeg_loglevel()]
    filter_parts: List[str] = []
    gp_ok = bool(gameplay_path and os.path.exists(gameplay_path))
    for i, clip in enumerate(valid):
        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
        cmd.extend(["-i", clip["path"]])
        dur = float(clip.get("duration", 3.0))
        filter_parts.append(
            build_scene_filter_chain(
                i, dur, W, H, i,
                enable_ken_burns=enable_ken_burns,
                enable_zoompan=enable_zoompan,
                split_screen=gp_ok,
                gameplay_index=len(valid) if gp_ok else None,
                gameplay_label=(f"[{len(valid)}:v]" if gp_ok and len(valid) == 1 else f"[gp{i}]") if gp_ok else None,
            )
        )

    n = len(valid)
    if gp_ok:
        cmd.extend(["-stream_loop", "-1", "-i", gameplay_path])
        print(f"  [FFmpegGraph] Split-screen alt panel: {os.path.basename(gameplay_path)}", flush=True)
        if n > 1:
            arms = "".join(f"[gp{i}]" for i in range(n))
            filter_parts.insert(0, f"[{n}:v]split={n}{arms}")
    concat_in = "".join(f"[v{i}]" for i in range(n))
    filter_parts.append(f"{concat_in}concat=n={n}:v=1:a=0[vcat]")

    look = get_look_filters(W, H, anti_duplicate=anti_duplicate)
    # Neon progress bar approximation via drawbox (Item 138) — static full-width thin bar
    # Dynamic fill is approximate: use overlay color at bottom
    prog = f"drawbox=x=0:y=ih-4:w=iw:h=4:color=0x00FFCC@0.85:t=fill"
    mid = f"[vcat]{look},{prog}[vlook]"
    filter_parts.append(mid)

    if ass_path and os.path.exists(ass_path):
        esc = _escape_ass_path(ass_path)
        filter_parts.append(f"[vlook]subtitles='{esc}'[vout]")
        vlabel = "[vout]"
    else:
        filter_parts.append("[vlook]null[vout]")
        vlabel = "[vout]"

    # Audio input index. Gameplay, when present, sits between scenes and audio.
    audio_idx = n + (1 if gp_ok else 0)
    cmd.extend(["-i", audio_path])

    filter_complex = ";".join(filter_parts)

    # Codec selection — NVENC (Windows NVIDIA) · VideoToolbox (macOS) · libx264 fallback
    from system_resilience import get_ffmpeg_vcodec_args
    use_gpu = getattr(config, "USE_GPU_ACCELERATION", True)
    gpu_codec = getattr(config, "GPU_CODEC", "")
    threads = int(getattr(config, "FFMPEG_THREADS", getattr(config, "RENDER_THREADS", 4)) or 4)
    vcodec, mode = get_ffmpeg_vcodec_args(use_gpu, gpu_codec)

    import random
    if getattr(config, "FPS_DIVERSIFY", True):
        fps = random.choice([29.97, 30.00, 30.02, 29.95, 30.04])
    else:
        fps = 30.0

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", vlabel,
        "-map", f"{audio_idx}:a",
        *vcodec,
        "-r", f"{fps:.2f}",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest",
        "-movflags", "+faststart",
        "-map_metadata", "-1",
        "-metadata", f"title={title or 'Shorts'}",
        "-metadata", "encoder=Final Cut Pro",
        "-threads", str(threads),
        output_path,
    ])

    if enable_zoompan:
        print("  [FFmpegGraph] zoompan AÇIK — bu geçiş render süresini uzatır", flush=True)
    print(f"  [FFmpegGraph] Export: {W}x{H} @ {fps:.2f} | {mode} | {n} scenes | Madde 418", flush=True)
    if progress_callback:
        progress_callback(80, f"[FFmpegGraph] Kodlama başlıyor ({mode})...")

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )
        stderr_data = []
        while True:
            if cancel_check and cancel_check():
                proc.terminate()
                raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            line = proc.stderr.readline() if proc.stderr else ""
            if line:
                stderr_data.append(line)
                if "time=" in line and progress_callback:
                    progress_callback(88, "[FFmpegGraph] Kodlama devam ediyor...")
            if proc.poll() is not None:
                break
        rest = proc.stderr.read() if proc.stderr else ""
        if rest:
            stderr_data.append(rest)

        if proc.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) < 100000:
            err = "".join(stderr_data)[-800:]
            print(f"  [FFmpegGraph] Başarısız (fallback MoviePy): {err[:300]}")
            return ""

        if progress_callback:
            progress_callback(95, "[FFmpegGraph] Tamamlandı")
        print(f"  [FFmpegGraph] OK → {output_path} ({os.path.getsize(output_path)//1024} KB)")

        # Post-render packaging: truthful metadata cleanup only.
        try:
            from anti_detect.post_render import apply_post_render_humanization
            post = apply_post_render_humanization(output_path, title=title or "")
            if post.get("metadata_applied"):
                print("  [FFmpegGraph] [PostRender] metadata cleaned and title recorded.")
        except Exception as pr_err:
            print(f"  [FFmpegGraph] PostRender note: {pr_err}")

        return output_path
    except InterruptedError:
        raise
    except Exception as e:
        print(f"  [FFmpegGraph] Exception: {e}")
        return ""
    finally:
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def _needs_moviepy_composer(kwargs: Dict[str, Any]) -> bool:
    """
    FFmpeg graph covers concat + look + ASS + NVENC in one pass.
    MoviePy only when a second picture must be composited (split / hybrid UI).
    Section-2 per-frame overlays made 60s exports take many minutes: each
    frame is drawn in Python while NVENC waits.
    """
    # Split + gameplay is a vstack inside the FFmpeg graph. MoviePy stays
    # for hybrid UI overlays that the graph cannot draw.
    overlay = kwargs.get("hybrid_render_overlay") or {}
    if isinstance(overlay, dict) and (overlay.get("ui_type") or overlay.get("overlay")):
        return True
    if kwargs.get("hybrid_niche"):
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
    if _needs_moviepy_composer(kwargs):
        print(
            "  [Director] MoviePy compose_video — full Section-2/B5 overlay pipeline "
            "(FFmpeg graph is look+subs only)",
            flush=True,
        )
        from video_composer import compose_video
        kwargs.setdefault("audio_premastered", kwargs.get("audio_premastered", True))
        return compose_video(clips, audio_path, word_timings, output_path, **kwargs)

    # Fast path: basic concat + look when overlays disabled explicitly
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
            gameplay_path=kwargs.get("gameplay_path") if kwargs.get("split_screen") or kwargs.get("gameplay_path") else None,
        )
        if result:
            return result
        print("  [Director] FFmpeg graph fallback → MoviePy compose_video")

    from video_composer import compose_video
    kwargs["audio_premastered"] = kwargs.pop("audio_premastered", True)
    return compose_video(clips, audio_path, word_timings, output_path, **kwargs)
