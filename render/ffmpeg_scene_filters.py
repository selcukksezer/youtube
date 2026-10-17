"""
Per-scene FFmpeg filter chain, camera motion, and input graph builder.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import config
from .ffmpeg_overlays import _plan_cutaways, get_look_filters
from .ffmpeg_probes import (
    align_even_dimension,
    color_convert_filter,
    face_cover_crop_x,
    gameplay_start_seconds,
    probe_stream_color,
    _probe_duration,
    _probe_is_landscape,
)
from .keyframe_motion import KeyframeProperty, KeyframeTrajectory


def _fg():
    return sys.modules.get("render.ffmpeg_graph")


def _fg_attr(name: str, default: Any) -> Any:
    fg = _fg()
    return getattr(fg, name, default) if fg is not None else default


def resolve_camera_intent(
    scene_intent: Optional[str] = None,
    camera_direction: Optional[str] = None,
    scene_index: int = 0,
    total_scenes: int = 1,
    narration: Optional[str] = None,
) -> str:
    """
    Bölüm 33.3 P4 (youtube-shorts-pipeline verticals/broll.py 3-kamera niyet modeli):
    Sahne niyetine göre 3 temel kamera hareketinden birini belirler.
    """
    cam = (camera_direction or "").lower().strip()
    if cam in (
        "zoom_in", "zoom_out", "pan_right", "pan_left",
        "tilt_down", "tilt_up", "static", "push_in", "pull_out"
    ):
        return cam

    intent = (scene_intent or "").lower().strip()
    if intent in (
        "question", "soru", "hook", "curiosity", "establishing",
        "closeup", "soru_zoom_in", "shock", "quiz"
    ):
        return "zoom_in"
    if intent in (
        "transition", "gecis", "geçiş", "action", "body",
        "conflict", "bridge", "gecis_pan"
    ):
        return "pan_right"
    if intent in (
        "conclusion", "kapanis", "kapanış", "outro", "cta",
        "climax", "resolution", "kapanis_zoom_out", "final"
    ):
        return "zoom_out"

    narr = (narration or "").lower().strip()
    if "?" in narr or any(narr.startswith(w) for w in (
        "neden", "nasıl", "kim", "hiç", "biliyor musun", "fark ettin mi",
        "why", "how", "did you know", "what if"
    )):
        return "zoom_in"

    if total_scenes > 2 and scene_index == total_scenes - 1:
        return "zoom_out"

    cycle = ["zoom_in", "pan_right", "zoom_out"]
    return cycle[int(scene_index) % 3]


def cheap_pan_filter(
    width: int,
    height: int,
    duration: float,
    scene_index: int = 0,
    camera_direction: Optional[str] = None,
    scene_intent: Optional[str] = None,
    total_scenes: Optional[int] = None,
    narration: Optional[str] = None,
) -> str:
    """
    Smooth cosine ease-in-out push via overscale + moving crop (Madde 418 / Master Plan Paket 4 / Bölüm 7.6).
    """
    dur = max(float(duration), 0.1)
    sw = max(width + 2, (int(width * 1.08) // 2) * 2)
    sh = max(height + 2, (int(height * 1.08) // 2) * 2)

    prog = f"0.5*(1-cos(PI*min(t\\,{dur:.3f})/{dur:.3f}))"
    prog_rev = f"0.5*(1+cos(PI*min(t\\,{dur:.3f})/{dur:.3f}))"

    cam = resolve_camera_intent(
        scene_intent=scene_intent,
        camera_direction=camera_direction,
        scene_index=scene_index,
        total_scenes=total_scenes or 1,
        narration=narration or "",
    )
    if cam == "pan_right":
        xexpr, yexpr = f"(in_w-out_w)*{prog}", "(in_h-out_h)/2"
    elif cam == "pan_left":
        xexpr, yexpr = f"(in_w-out_w)*{prog_rev}", "(in_h-out_h)/2"
    elif cam == "tilt_down":
        xexpr, yexpr = "(in_w-out_w)/2", f"(in_h-out_h)*{prog}"
    elif cam == "tilt_up":
        xexpr, yexpr = "(in_w-out_w)/2", f"(in_h-out_h)*{prog_rev}"
    elif cam == "static":
        xexpr, yexpr = "(in_w-out_w)/2", "(in_h-out_h)/2"
    elif cam in ("zoom_in", "push_in"):
        xexpr, yexpr = f"(in_w-out_w)*0.5*{prog}", f"(in_h-out_h)*0.5*{prog}"
    elif cam in ("zoom_out", "pull_out"):
        xexpr, yexpr = f"(in_w-out_w)*0.5*{prog_rev}", f"(in_h-out_h)*0.5*{prog_rev}"
    else:
        direction = int(scene_index) % 4
        if direction == 0:
            xexpr, yexpr = f"(in_w-out_w)*{prog}", "(in_h-out_h)/2"
        elif direction == 1:
            xexpr, yexpr = f"(in_w-out_w)*{prog_rev}", "(in_h-out_h)/2"
        elif direction == 2:
            xexpr, yexpr = "(in_w-out_w)/2", f"(in_h-out_h)*{prog}"
        else:
            xexpr, yexpr = "(in_w-out_w)/2", f"(in_h-out_h)*{prog_rev}"

    return f"scale={sw}:{sh},crop={width}:{height}:x='{xexpr}':y='{yexpr}'"


def _keyframed_camera_expression(
    prop: KeyframeProperty,
    start_value: float,
    end_value: float,
    duration_frames: int,
    fps: float,
) -> str:
    duration_seconds = duration_frames / fps
    trajectory = KeyframeTrajectory(prop)
    trajectory.add_keyframe(0.0, start_value)
    trajectory.add_keyframe(duration_seconds, end_value)
    return trajectory.build_ffmpeg_cosine_expression(var_name=f"on/{fps:.6f}")


def zoompan_filter(
    width: int,
    height: int,
    duration: float,
    scene_index: int = 0,
    camera_direction: Optional[str] = None,
    output_fps: Optional[float] = None,
    scene_intent: Optional[str] = None,
    total_scenes: Optional[int] = None,
    narration: Optional[str] = None,
) -> str:
    """
    Opt-in Ken Burns (Bölüm 33.3 P4 / youtube-shorts-pipeline:animate_frame).
    """
    cfg_mod = _fg_attr("config", config)
    fps = float(output_fps) if output_fps else float(getattr(cfg_mod, "FPS", 30) or 30)
    frames = max(1, int(max(float(duration), 0.1) * fps))
    zoom_in = _keyframed_camera_expression(KeyframeProperty.SCALE, 1.0, 1.12, frames, fps)
    zoom_out = _keyframed_camera_expression(KeyframeProperty.SCALE, 1.12, 1.0, frames, fps)
    pan_forward = _keyframed_camera_expression(KeyframeProperty.POSITION_X, 0.0, 1.0, frames, fps)
    pan_reverse = _keyframed_camera_expression(KeyframeProperty.POSITION_X, 1.0, 0.0, frames, fps)
    tilt_forward = _keyframed_camera_expression(KeyframeProperty.POSITION_Y, 0.0, 1.0, frames, fps)
    tilt_reverse = _keyframed_camera_expression(KeyframeProperty.POSITION_Y, 1.0, 0.0, frames, fps)

    cam = resolve_camera_intent(
        scene_intent=scene_intent,
        camera_direction=camera_direction,
        scene_index=scene_index,
        total_scenes=total_scenes or 1,
        narration=narration or "",
    )
    if cam in ("zoom_in", "push_in"):
        z_expr, x_expr, y_expr = zoom_in, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif cam in ("zoom_out", "pull_out"):
        z_expr, x_expr, y_expr = zoom_out, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif cam in ("pan_right", "pan"):
        z_expr, x_expr, y_expr = "1.12", f"(iw-iw/zoom)*({pan_forward})", "(ih-ih/zoom)/2"
    elif cam == "pan_left":
        z_expr, x_expr, y_expr = "1.12", f"(iw-iw/zoom)*({pan_reverse})", "(ih-ih/zoom)/2"
    elif cam == "tilt_down":
        z_expr, x_expr, y_expr = "1.12", "(iw-iw/zoom)/2", f"(ih-ih/zoom)*({tilt_forward})"
    elif cam == "tilt_up":
        z_expr, x_expr, y_expr = "1.12", "(iw-iw/zoom)/2", f"(ih-ih/zoom)*({tilt_reverse})"
    elif cam == "static":
        z_expr, x_expr, y_expr = "1.0", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:
        kind = int(scene_index) % 3
        if kind == 1:
            z_expr, x_expr, y_expr = "1.12", f"(iw-iw/zoom)*({pan_forward})", "(ih-ih/zoom)/2"
        elif kind == 2:
            z_expr, x_expr, y_expr = zoom_out, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
        else:
            z_expr, x_expr, y_expr = zoom_in, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"

    return (
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
        f"d=1:s={width}x{height}:fps={fps:.2f}"
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
    fit_and_fill: bool = False,
    gameplay_start: float = 0.0,
    crop_x: Optional[int] = None,
    tail_crop_x=None,
    tail_fit_and_fill: Optional[bool] = None,
    pad_seconds: float = 0.0,
    tail_input_index: Optional[int] = None,
    head_seconds: Optional[float] = None,
    color_filter: str = "",
    tail_color_filter: str = "",
    gameplay_color_filter: str = "",
    camera_direction: Optional[str] = None,
    output_fps: Optional[float] = None,
    scene_intent: Optional[str] = None,
    total_scenes: Optional[int] = None,
    narration: Optional[str] = None,
) -> str:
    """
    Per-input video chain: trim, fps, scale/crop cover, optional crop-pan.
    Split: top 58% scene, bottom 42% looped gameplay (soap / satisfying).
    Fit & Fill: Blurred background + centered aspect-ratio preserved foreground (Paket 2).
    """
    cfg_mod = _fg_attr("config", config)
    cheap_pan_fn = _fg_attr("cheap_pan_filter", cheap_pan_filter)
    zoompan_fn = _fg_attr("zoompan_filter", zoompan_filter)

    width = align_even_dimension(width)
    height = align_even_dimension(height)
    split = bool(split_screen and (gameplay_label or gameplay_index is not None))
    out_h = align_even_dimension(int(height * 0.58)) if split else height
    fps = float(output_fps) if output_fps else float(getattr(cfg_mod, "FPS", 30) or 30)
    fps_token = f"{fps:.2f}".rstrip("0").rstrip(".")

    def _lead(label: str, extra: str) -> str:
        extra = (extra or "").strip().strip(",")
        return f"{label}{extra}," if extra else label

    pad = ""
    if pad_seconds and float(pad_seconds) > 0.12:
        pad = f"tpad=stop_mode=clone:stop_duration={float(pad_seconds):.3f},"
    cover_crop = f"crop={width}:{out_h}"
    if crop_x is not None and not fit_and_fill:
        offset = f"'{crop_x}'" if isinstance(crop_x, str) else str(max(0, int(crop_x)))
        cover_crop += f":x={offset}"

    if tail_input_index is not None and head_seconds is not None and not split:
        head_len = max(0.2, min(float(head_seconds), float(duration) - 0.2))
        tail_len = max(0.2, float(duration) - head_len)

        def _piece(src_index: int, seg_dur: float, seg_pad: float, suffix: str) -> str:
            pad_f = f"tpad=stop_mode=clone:stop_duration={float(seg_pad):.3f}," if seg_pad and float(seg_pad) > 0.12 else ""
            tag = f"seg{scene_index}{suffix}"
            src = _lead(f"[{src_index}:v]", color_filter if suffix == "a" else tail_color_filter)
            piece_fit = fit_and_fill if suffix == "a" or tail_fit_and_fill is None else tail_fit_and_fill
            piece_crop = cover_crop if suffix == "a" else f"crop={width}:{out_h}"
            if suffix == "b" and tail_crop_x is not None:
                offset = f"'{tail_crop_x}'" if isinstance(tail_crop_x, str) else str(max(0, int(tail_crop_x)))
                piece_crop += f":x={offset}"
            if piece_fit:
                return (
                    f"{src}trim=duration={seg_dur:.3f},{pad_f}setpts=PTS-STARTPTS,"
                    f"fps={fps_token},split[fg_raw_{scene_index}{suffix}][bg_raw_{scene_index}{suffix}];"
                    f"[bg_raw_{scene_index}{suffix}]scale={width}:{out_h}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{out_h},boxblur=25:5[bg_blur_{scene_index}{suffix}];"
                    f"[fg_raw_{scene_index}{suffix}]scale={width}:{out_h}:force_original_aspect_ratio=decrease"
                    f"[fg_fit_{scene_index}{suffix}];"
                    f"[bg_blur_{scene_index}{suffix}][fg_fit_{scene_index}{suffix}]overlay=(W-w)/2:(H-h)/2,"
                    f"setsar=1[{tag}]"
                )
            return (
                f"{src}trim=duration={seg_dur:.3f},{pad_f}setpts=PTS-STARTPTS,"
                f"fps={fps_token},scale={width}:{out_h}:force_original_aspect_ratio=increase,"
                f"{piece_crop},setsar=1[{tag}]"
            )

        head = _piece(input_index, head_len, 0.0, "a")
        tail = _piece(int(tail_input_index), tail_len, float(pad_seconds or 0.0), "b")
        motion = ""
        if enable_zoompan:
            motion = "," + zoompan_fn(
                width, out_h, duration, scene_index,
                camera_direction=camera_direction, output_fps=fps,
                scene_intent=scene_intent, total_scenes=total_scenes, narration=narration,
            )
        elif enable_ken_burns:
            motion = "," + cheap_pan_fn(
                width, out_h, duration, scene_index,
                camera_direction=camera_direction, scene_intent=scene_intent,
                total_scenes=total_scenes, narration=narration,
            )
        bright = ""
        try:
            from effects.filters import get_scene_brightness_alternation_filter
            bright = "," + get_scene_brightness_alternation_filter(scene_index)
        except Exception:
            pass
        joined = f"{head};{tail};[seg{scene_index}a][seg{scene_index}b]concat=n=2:v=1:a=0[cat{scene_index}]"
        return joined + f";[cat{scene_index}]null{bright}{motion},setsar=1[v{scene_index}]"

    if fit_and_fill:
        base = (
            f"{_lead(f'[{input_index}:v]', color_filter)}"
            f"trim=duration={duration:.3f},{pad}setpts=PTS-STARTPTS,"
            f"fps={fps_token},"
            f"split[fg_raw_{scene_index}][bg_raw_{scene_index}];"
            f"[bg_raw_{scene_index}]scale={width}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={width}:{out_h},boxblur=25:5[bg_blur_{scene_index}];"
            f"[fg_raw_{scene_index}]scale={width}:{out_h}:force_original_aspect_ratio=decrease[fg_fit_{scene_index}];"
            f"[bg_blur_{scene_index}][fg_fit_{scene_index}]overlay=(W-w)/2:(H-h)/2,setsar=1"
        )
    else:
        base = (
            f"{_lead(f'[{input_index}:v]', color_filter)}"
            f"trim=duration={duration:.3f},{pad}setpts=PTS-STARTPTS,"
            f"fps={fps_token},scale={width}:{out_h}:force_original_aspect_ratio=increase,{cover_crop},setsar=1"
        )
    try:
        from effects.filters import get_scene_brightness_alternation_filter
        base += f",{get_scene_brightness_alternation_filter(scene_index)}"
    except Exception:
        pass
    if enable_zoompan:
        base += "," + zoompan_fn(
            width, out_h, duration, scene_index,
            camera_direction=camera_direction, output_fps=fps,
            scene_intent=scene_intent, total_scenes=total_scenes, narration=narration,
        )
    elif enable_ken_burns:
        base += "," + cheap_pan_fn(
            width, out_h, duration, scene_index,
            camera_direction=camera_direction, scene_intent=scene_intent,
            total_scenes=total_scenes, narration=narration,
        )
    if not split:
        base += f",setsar=1[v{scene_index}]"
        return base
    bot_h = align_even_dimension(int(height - out_h))
    base += f"[top{scene_index}]"
    gp_src = gameplay_label or f"[{gameplay_index}:v]"
    start = max(0.0, float(gameplay_start or 0.0))
    gameplay = (
        f"{_lead(gp_src, gameplay_color_filter)}trim=start={start:.3f}:duration={duration:.3f},setpts=PTS-STARTPTS,"
        f"fps={fps_token},scale={width}:{bot_h}:force_original_aspect_ratio=increase,"
        f"crop={width}:{bot_h},drawbox=y=0:h=3:color=0xFFD700@0.95:t=fill,setsar=1[bot{scene_index}]"
    )
    stack = f"[top{scene_index}][bot{scene_index}]vstack=inputs=2,setsar=1[v{scene_index}]"
    return base + ";" + gameplay + ";" + stack


def build_all_scene_inputs_and_filters(
    *,
    valid: List[Dict[str, Any]],
    cmd: List[str],
    filter_parts: List[str],
    W: int,
    H: int,
    output_fps: float,
    gameplay_path: Optional[str],
    enable_ken_burns: bool,
    enable_zoompan: bool,
    enable_face_center: bool,
    anti_duplicate: bool,
    cancel_check: Optional[Callable] = None,
) -> Tuple[int, float]:
    """Build per-scene FFmpeg inputs, split-screen gameplay, concat, and look/progress filter."""
    os_mod = _fg_attr("os", os)
    probe_dur_fn = _fg_attr("_probe_duration", _probe_duration)
    probe_land_fn = _fg_attr("_probe_is_landscape", _probe_is_landscape)
    face_crop_fn = _fg_attr("face_cover_crop_x", face_cover_crop_x)
    color_conv_fn = _fg_attr("color_convert_filter", color_convert_filter)
    probe_color_fn = _fg_attr("probe_stream_color", probe_stream_color)
    scene_chain_fn = _fg_attr("build_scene_filter_chain", build_scene_filter_chain)
    gp_start_fn = _fg_attr("gameplay_start_seconds", gameplay_start_seconds)
    look_fn = _fg_attr("get_look_filters", get_look_filters)

    gp_ok = bool(gameplay_path and os_mod.path.exists(gameplay_path))
    gp_dur = probe_dur_fn(gameplay_path) if gp_ok else 0.0
    n = len(valid)
    cursor = 0
    for i, clip in enumerate(valid):
        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
        dur = float(clip.get("duration", 3.0))
        media_dur = probe_dur_fn(clip.get("path"))
        pad_seconds = 0.0
        tail_index = None
        head_seconds = None
        tail_path = "" if gp_ok else (clip.get("tail_path") or "")
        use_tail = (
            bool(tail_path)
            and os_mod.path.exists(tail_path)
            and media_dur > 0.2
            and dur - media_dur > 0.12
        )
        if use_tail:
            cmd.extend(["-i", clip["path"]])
            head_index = cursor
            cursor += 1
            cmd.extend(["-i", tail_path])
            tail_index = cursor
            cursor += 1
            head_seconds = min(media_dur, max(0.2, dur - 0.2))
            tail_need = max(0.2, dur - head_seconds)
            tail_media = probe_dur_fn(tail_path)
            if tail_media > 0.2 and tail_need - tail_media > 0.12:
                pad_seconds = tail_need - tail_media
        elif media_dur > 0.2 and dur - media_dur > 0.12:
            cmd.extend(["-stream_loop", "-1", "-i", clip["path"]])
            head_index = cursor
            cursor += 1
            pad_seconds = 0.0
        else:
            cmd.extend(["-i", clip["path"]])
            head_index = cursor
            cursor += 1
        panel_h = align_even_dimension(int(H * 0.58)) if gp_ok else H
        crop_x = clip.get("crop_x")
        is_landscape = probe_land_fn(clip.get("path"))

        if enable_face_center and is_landscape:
            if crop_x is None:
                crop_x = face_crop_fn(clip.get("path"), W, panel_h, duration=dur)
            if crop_x is not None:
                use_fit_fill = False
            elif clip.get("fit_and_fill") is not None:
                use_fit_fill = bool(clip.get("fit_and_fill"))
            else:
                use_fit_fill = True
        else:
            use_fit_fill = clip.get("fit_and_fill")
            use_fit_fill = is_landscape if use_fit_fill is None else bool(use_fit_fill)
        tail_crop_x = None
        tail_fit_fill = None
        if use_tail:
            tail_fit_fill = probe_land_fn(tail_path)
            if enable_face_center and tail_fit_fill:
                tail_crop_x = face_crop_fn(tail_path, W, panel_h, duration=tail_need)
                if tail_crop_x is not None:
                    tail_fit_fill = False
        tracking = enable_face_center and (crop_x is not None or tail_crop_x is not None)
        gp_label = (f"[{cursor}:v]" if n == 1 else f"[gp{i}]") if gp_ok else None
        vis_intent = clip.get("visual_intent") if isinstance(clip.get("visual_intent"), dict) else {}
        filter_parts.append(
            scene_chain_fn(
                head_index, dur, W, H, i,
                enable_ken_burns=enable_ken_burns and not tracking,
                enable_zoompan=enable_zoompan and not tracking,
                split_screen=gp_ok,
                gameplay_index=cursor if gp_ok and n == 1 else None,
                gameplay_label=gp_label,
                fit_and_fill=use_fit_fill,
                gameplay_start=gp_start_fn(gp_dur, dur, i) if gp_ok else 0.0,
                crop_x=crop_x,
                tail_crop_x=tail_crop_x,
                tail_fit_and_fill=tail_fit_fill,
                pad_seconds=pad_seconds,
                tail_input_index=tail_index,
                head_seconds=head_seconds,
                color_filter=color_conv_fn(probe_color_fn(clip.get("path") or "")),
                tail_color_filter=color_conv_fn(probe_color_fn(tail_path)) if use_tail else "",
                gameplay_color_filter=color_conv_fn(probe_color_fn(gameplay_path or "")) if gp_ok else "",
                camera_direction=clip.get("camera_direction") or vis_intent.get("camera_direction") or "",
                output_fps=output_fps,
                scene_intent=(
                    clip.get("scene_intent") or clip.get("intent") or clip.get("beat_type")
                    or vis_intent.get("shot_type") or ""
                ),
                total_scenes=n,
                narration=clip.get("narration") or "",
            )
        )

    gp_index = cursor
    if gp_ok and gameplay_path:
        cmd.extend(["-stream_loop", "-1", "-i", gameplay_path])
        cursor += 1
        print(f"  [FFmpegGraph] Split-screen alt panel: {os_mod.path.basename(gameplay_path)}", flush=True)
        if n > 1:
            arms = "".join(f"[gp{i}]" for i in range(n))
            filter_parts.insert(0, f"[{gp_index}:v]split={n}{arms}")
    concat_in = "".join(f"[v{i}]" for i in range(n))
    filter_parts.append(f"{concat_in}concat=n={n}:v=1:a=0[vcat]")

    look = look_fn(W, H, anti_duplicate=anti_duplicate)
    total_dur = max(0.1, sum(float(c.get("duration", 3.0)) for c in valid))
    prog = f"drawbox=x=0:y=ih-6:w='iw*min(1\\,t/{total_dur:.3f})':h=6:color=0x00E5FF@0.9:t=fill"
    filter_parts.append(f"[vcat]{look},{prog}[vlook]")
    return cursor, total_dur
