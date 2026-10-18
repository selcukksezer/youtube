"""
Global overlay filter builders for FFmpeg render graph (B-roll cutaways, look filters,
hook card, audio visualizer, ASS subtitles, emphasis card, hybrid UI, news ticker,
Reddit card, punch-in zoom, and evidence badge).
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import config
from .ffmpeg_probes import _BT709_TAG, _escape_ass_path


def _fg():
    return sys.modules.get("render.ffmpeg_graph")


def _fg_attr(name: str, default: Any) -> Any:
    fg = _fg()
    return getattr(fg, name, default) if fg is not None else default


def _plan_cutaways(
    clips: List[Dict[str, Any]],
    total_dur: float,
    word_timings: Optional[List[Dict[str, Any]]],
) -> List[Tuple[str, float, float]]:
    """
    ai-content-studio overlays with enable=between, one new encode per cue.
    This keeps the window and drops the extra encode. Cue length is 2.0-3.2s.
    Non-overlapping overlays, maximum 3.
    """
    os_mod = _fg_attr("os", os)
    cfg_mod = _fg_attr("config", config)
    candidates: List[Tuple[str, float, float]] = []
    hook_guard = 1.8
    tail_guard = 1.0
    for clip in clips:
        for item in clip.get("broll_inserts") or []:
            path = item.get("path")
            if not path or not os_mod.path.exists(path):
                continue
            raw_start = max(0.0, float(item.get("start") or 0.0))
            raw_end = float(item.get("end") or (raw_start + 2.5))
            dur = max(2.0, min(3.2, raw_end - raw_start))
            start = max(hook_guard, raw_start)
            end = min(total_dur - tail_guard, start + dur)
            if end - start < 2.0 and total_dur >= hook_guard + 2.0 + tail_guard:
                end = total_dur - tail_guard
                start = max(hook_guard, end - dur)
            if end - start >= 2.0:
                candidates.append((path, start, end))

    if not candidates and not getattr(cfg_mod, "RENDER_SAFE_MODE", False) and len(clips) >= 3 and total_dur >= 10.0:
        narration = " ".join(str(w.get("text") or "") for w in (word_timings or []))
        try:
            from services.dynamic_broll_director import dynamic_broll_director
            cues = dynamic_broll_director.plan_retention_broll(total_dur, narration)[:3]
        except Exception:
            cues = []
        starts: List[float] = []
        cursor = 0.0
        for clip in clips:
            starts.append(cursor)
            cursor += float(clip.get("duration") or 3.0)
        for cue in cues:
            raw_start = float(cue.start_offset)
            dur = max(2.0, min(3.2, float(cue.end_offset) - raw_start))
            start = max(hook_guard, raw_start)
            end = min(total_dur - tail_guard, start + dur)
            if end - start < 2.0:
                continue
            donor = None
            for idx, clip in enumerate(clips):
                scene_end = starts[idx] + float(clip.get("duration") or 3.0)
                if end <= starts[idx] or start >= scene_end:
                    donor = clip.get("path")
                    break
            if donor and os_mod.path.exists(donor):
                candidates.append((donor, start, end))

    candidates.sort(key=lambda x: x[1])
    selected: List[Tuple[str, float, float]] = []
    last_end = hook_guard
    for path, start, end in candidates:
        if start < last_end:
            if last_end + 0.2 + 2.0 <= total_dur - tail_guard:
                original_dur = end - start
                start = last_end + 0.2
                end = min(total_dur - tail_guard, start + original_dur)
                if end - start < 2.0:
                    continue
            else:
                continue
        if end - start >= 2.0 and len(selected) < 3:
            selected.append((path, round(start, 2), round(end, 2)))
            last_end = end
    return selected


def get_look_filters(width: int, height: int, anti_duplicate: bool = True) -> str:
    """Color jitter with independent RGB gamma channels, unsharp, temporal noise, vignette (Items 72, 84, 86, 92, Chapter 8.2)."""
    from compliance.anti_repetition import get_rgb_color_jitter_filter, get_temporal_noise_filter
    parts = [
        get_rgb_color_jitter_filter(jitter_range=0.015),
        "unsharp=5:5:0.8:5:5:0.0",
    ]
    if anti_duplicate:
        parts.append(get_temporal_noise_filter(strength=3, flag="t"))
    parts.append("vignette=PI/5")
    return ",".join(parts)


def apply_global_overlays_to_graph(
    *,
    cmd: List[str],
    filter_parts: List[str],
    valid: List[Dict[str, Any]],
    total_dur: float,
    next_input: int,
    W: int,
    H: int,
    tmp_dir: str,
    audio_path: str,
    word_timings: Optional[List[Dict[str, Any]]],
    title: str,
    subtitle_opts: Optional[Dict[str, Any]],
    enable_broll: bool,
    ass_path: Optional[str],
    emphasis_ass_path: Optional[str],
    enable_emphasis_card: bool,
    hybrid_render_overlay: Optional[Dict[str, Any]],
    enable_audio_visualizer: bool,
    audio_visualizer_mode: str,
    audio_visualizer_color: str,
    enable_news_ticker: bool,
    news_ticker_text: Optional[str],
    niche_id: str,
    enable_reddit_card: bool,
    reddit_card_path: Optional[str],
    extra_kwargs: Dict[str, Any],
) -> Tuple[str, int, int]:
    """
    Append all global overlays onto the filter_complex graph and return (vlabel, audio_idx, next_input).
    """
    os_mod = _fg_attr("os", os)
    cfg_mod = _fg_attr("config", config)
    plan_cutaways_fn = _fg_attr("_plan_cutaways", _plan_cutaways)
    esc_ass_fn = _fg_attr("_escape_ass_path", _escape_ass_path)

    picture = "vlook"
    if enable_broll and not getattr(cfg_mod, "RENDER_SAFE_MODE", False):
        cutaways = plan_cutaways_fn(valid, total_dur, word_timings)[:3]
        for bi, (bpath, bstart, bend) in enumerate(cutaways):
            cmd.extend(["-i", bpath])
            dest = f"vcut{bi}"
            filter_parts.append(
                f"[{next_input}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H}[broll{bi}];"
                f"[{picture}][broll{bi}]overlay=0:0:"
                f"enable='between(t,{bstart:.2f},{bend:.2f})'[{dest}]"
            )
            picture = dest
            next_input += 1

    hook_path = ""
    hook_input: Optional[int] = None
    hook_opts = subtitle_opts or {}
    hook_text = hook_opts.get("hook_card_text", title) or ""
    if hook_text and not hook_opts.get("disable_hook_card"):
        try:
            from effects.hook_card import create_hook_image
            hook_path = create_hook_image(hook_text, W, os_mod.path.join(tmp_dir, "hook.png")) or ""
        except Exception as hook_err:
            print(f"  [FFmpegGraph] hook card notice: {hook_err}")
            hook_path = ""
    if hook_path and os_mod.path.exists(hook_path):
        cmd.extend(["-loop", "1", "-t", "2.5", "-i", hook_path])
        hook_input = next_input
        next_input += 1

    should_visualize = bool(enable_audio_visualizer)

    audio_idx: Optional[int] = None
    if should_visualize and os_mod.path.exists(audio_path):
        audio_idx = next_input
        cmd.extend(["-i", audio_path])
        next_input += 1
        try:
            from effects.audio_visualizer import build_waveform_filter
            wave_flt, wave_tag = build_waveform_filter(
                audio_tag=f"{audio_idx}:a",
                video_tag=picture,
                out_tag="vwave",
                width=W,
                height=96,
                y_pos=int(H * 0.85),
                mode=audio_visualizer_mode or "line",
                color=audio_visualizer_color or "0x00D7FF",
                opacity=0.55,
            )
            filter_parts.append(wave_flt)
            picture = wave_tag
        except Exception as wave_err:
            print(f"  [FFmpegGraph] audio visualizer notice: {wave_err}", flush=True)

    hybrid_spec = hybrid_render_overlay
    hybrid_info = None
    if hybrid_spec and isinstance(hybrid_spec, dict):
        try:
            from effects.hybrid_overlay import create_hybrid_ui_overlay_png
            hybrid_info = create_hybrid_ui_overlay_png(
                hybrid_spec,
                width=W,
                height=H,
                total_duration=total_dur,
                out_path=os_mod.path.join(tmp_dir, "hybrid_ui.png"),
            )
        except Exception as hy_err:
            print(f"  [FFmpegGraph] hybrid UI overlay notice: {hy_err}", flush=True)
            hybrid_info = None

    if hybrid_info and os_mod.path.exists(hybrid_info["png_path"]):
        h_dur = hybrid_info["duration"]
        cmd.extend(["-loop", "1", "-t", f"{h_dur:.2f}", "-i", hybrid_info["png_path"]])
        hybrid_input = next_input
        next_input += 1
        filter_parts.append(f"[{hybrid_input}:v]format=rgba[hy_rgba]")
        x_expr = hybrid_info["x_expr"]
        y_expr = hybrid_info["y_expr"]
        enable_expr = hybrid_info["enable_expr"]
        filter_parts.append(
            f"[{picture}][hy_rgba]overlay=x={x_expr}:y={y_expr}:"
            f"enable='{enable_expr}':eof_action=pass:repeatlast=0[vhybrid]"
        )
        picture = "vhybrid"

    should_ticker = bool(enable_news_ticker)
    if not should_ticker and niche_id:
        try:
            from effects.ticker import is_ticker_enabled_for_niche
            should_ticker = is_ticker_enabled_for_niche(niche_id)
        except Exception:
            should_ticker = False

    if should_ticker:
        try:
            from effects.ticker import generate_news_ticker_image
            t_text = news_ticker_text or title or "SON DAKİKA GELİŞMESİ"
            ticker_png = os_mod.path.join(tmp_dir, "news_ticker.png")
            generate_news_ticker_image(
                headline=t_text,
                output_path=ticker_png,
                width=W,
                height=130,
            )
            if os_mod.path.exists(ticker_png):
                cmd.extend(["-loop", "1", "-t", f"{total_dur:.3f}", "-i", ticker_png])
                ticker_input = next_input
                next_input += 1
                filter_parts.append(f"[{ticker_input}:v]format=rgba[ticker_rgba]")
                filter_parts.append(
                    f"[{picture}][ticker_rgba]overlay=x=0:y={int(H * 0.14)}:"
                    f"enable='between(t,0.5,{total_dur:.3f})':eof_action=pass:repeatlast=0[vticker]"
                )
                picture = "vticker"
        except Exception as ticker_err:
            print(f"  [FFmpegGraph] news ticker notice: {ticker_err}", flush=True)

    _director = extra_kwargs.get("director")
    _reddit_active = bool(
        enable_reddit_card
        or extra_kwargs.get("enable_reddit_card", False)
        or (_director and getattr(_director, "niche_id", "") in ("reddit", "reddit_story", "11_reddit_stories"))
        or (niche_id in ("reddit", "reddit_story", "11_reddit_stories"))
    )
    rcard_png = reddit_card_path or extra_kwargs.get("reddit_card_path")
    if _reddit_active or (rcard_png and os_mod.path.exists(rcard_png)):
        try:
            from reddit_card_renderer import (
                REDDIT_CARD_DISPLAY_DURATION_SEC,
                REDDIT_CARD_FADE_DURATION_SEC,
                generate_transparent_reddit_card_png,
            )
            if not rcard_png or not os_mod.path.exists(rcard_png):
                rcard_png = os_mod.path.join(tmp_dir, "reddit_card.png")
                card_title = title or "Reddit Soru"
                generate_transparent_reddit_card_png(
                    title=card_title,
                    subreddit="AskReddit",
                    output_path=rcard_png,
                    card_width=int(W * 0.88),
                )
            if rcard_png and os_mod.path.exists(rcard_png):
                card_duration = min(REDDIT_CARD_DISPLAY_DURATION_SEC, total_dur)
                fade_duration = min(REDDIT_CARD_FADE_DURATION_SEC, card_duration / 2.0)
                fade_out_start = max(0.0, card_duration - fade_duration)
                cmd.extend(["-loop", "1", "-t", f"{card_duration:.3f}", "-i", rcard_png])
                rcard_input = next_input
                next_input += 1
                filter_parts.append(
                    f"[{rcard_input}:v]format=rgba,"
                    f"fade=t=in:st=0:d={fade_duration:.3f}:alpha=1,"
                    f"fade=t=out:st={fade_out_start:.3f}:d={fade_duration:.3f}:alpha=1[rcard_faded]"
                )
                filter_parts.append(
                    f"[{picture}][rcard_faded]overlay=x=(W-w)/2:y={int(H * 0.28)}:"
                    f"enable='between(t,0,{card_duration:.3f})':eof_action=pass:repeatlast=0[vrcard]"
                )
                picture = "vrcard"
                print("  [FFmpegGraph] Reddit question card overlay active", flush=True)
        except Exception as rcard_err:
            print(f"  [FFmpegGraph] Reddit card overlay notice: {rcard_err}", flush=True)

    if ass_path and os_mod.path.exists(ass_path):
        esc = esc_ass_fn(ass_path)
        filter_parts.append(f"[{picture}]subtitles='{esc}'[vsub]")
        picture = "vsub"

    if enable_emphasis_card and emphasis_ass_path and os_mod.path.exists(emphasis_ass_path):
        esc_emp = esc_ass_fn(emphasis_ass_path)
        filter_parts.append(f"[{picture}]subtitles='{esc_emp}'[vemp]")
        picture = "vemp"

    if hook_path and hook_input is not None and os_mod.path.exists(hook_path):
        from effects.hook_card import hook_overlay_filter
        filter_parts.append(f"[{hook_input}:v]format=rgba[hook]")
        filter_parts.append(hook_overlay_filter(picture, "hook", "vhook", H))
        picture = "vhook"

    if extra_kwargs.get("enable_punch_in", False):
        try:
            from director.prompt_chains import detect_punch_in_cues, build_punch_in_filter
            punch_cues = extra_kwargs.get("punch_in_cues")
            if not punch_cues and word_timings:
                w_formatted = [
                    {
                        "word": str(w.get("text") or w.get("word") or ""),
                        "start": float(w.get("offset", w.get("start", 0.0))),
                        "end": float(w.get("offset", w.get("start", 0.0))) + float(w.get("duration", 0.3)),
                    }
                    for w in word_timings
                ]
                punch_cues = detect_punch_in_cues(w_formatted, max_cues=3)
            if punch_cues:
                p_filter, p_out = build_punch_in_filter(
                    punch_cues, input_label=picture, output_label="vpunch", width=W, height=H
                )
                if p_filter:
                    filter_parts.append(str(p_filter))
                    picture = p_out
        except Exception as punch_err:
            print(f"  [FFmpegGraph] punch-in filter notice: {punch_err}", flush=True)

    evidence_src = extra_kwargs.get("evidence_source") or (
        ((getattr(_director, "meta", None) or {}).get("evidence_source")) if _director else None
    )
    if evidence_src:
        try:
            from services.evidence_overlay import EvidenceBadgeGenerator
            ebadge_png = os_mod.path.join(tmp_dir, "evidence_badge.png")
            EvidenceBadgeGenerator.generate_badge_png(str(evidence_src), ebadge_png)
            if os_mod.path.exists(ebadge_png):
                eb_end = min(5.5, max(2.0, total_dur - 0.5))
                cmd.extend(["-loop", "1", "-t", f"{eb_end:.2f}", "-i", ebadge_png])
                eb_input = next_input
                next_input += 1
                filter_parts.append(f"[{eb_input}:v]format=rgba[ebadge_rgba]")
                filter_parts.append(
                    EvidenceBadgeGenerator.build_ffmpeg_overlay_filter(
                        input_label=picture,
                        badge_input_label="ebadge_rgba",
                        output_label="vevidence",
                        start_time=1.0,
                        end_time=eb_end,
                    )
                )
                picture = "vevidence"
        except Exception as eb_err:
            print(f"  [FFmpegGraph] evidence badge notice: {eb_err}", flush=True)

    filter_parts.append(f"[{picture}]format=yuv420p,{_BT709_TAG}[vout]")
    vlabel = "[vout]"

    if audio_idx is None:
        audio_idx = next_input
        cmd.extend(["-i", audio_path])
        next_input += 1

    return vlabel, audio_idx, next_input
