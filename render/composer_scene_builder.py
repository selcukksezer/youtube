"""
MoviePy Scene Segment Preparation, Face Centering, and Global Overlay Pipeline
for `video_composer.py`.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, List, Optional

from moviepy.editor import ColorClip, CompositeVideoClip, VideoFileClip, vfx

import config
from effects_engine import (
    apply_affiliate_3d_mockup,
    apply_alternating_motion,
    apply_anti_duplicate,
    apply_bookmark_cta_overlay,
    apply_broll_speed_boost,
    apply_capcut_density_cuts,
    apply_censored_blur_bait,
    apply_color_splash_moviepy,
    apply_corner_radius_to_clip,
    apply_dynamic_progress_bar,
    apply_end_card_to_video,
    apply_fluid_gradient_background,
    apply_handheld_camera_shake,
    apply_heartbeat_zoom,
    apply_horizontal_flip,
    apply_hybrid_render_overlay,
    apply_impact_screen_shake,
    apply_infinite_spiral_overlay,
    apply_ken_burns,
    apply_keyword_white_flash_overlay,
    apply_mask_wipe_transition,
    apply_micro_animated_sticker_overlay,
    apply_micro_zoom_out,
    apply_multi_layer_overlay,
    apply_neon_countdown_overlay,
    apply_neon_curiosity_opening_graphic,
    apply_opening_pattern_interrupt,
    apply_out_of_focus_reveal,
    apply_particle_overlay,
    apply_pip_overlay,
    apply_scene_brightness_alternation,
    apply_share_cta_overlay,
    apply_slow_motion_highlight,
    apply_smart_crop,
    apply_speaker_avatar_overlay,
    apply_speed_ramp,
    apply_sticky_hook_banner_overlay,
    apply_time_tunnel_overlay,
    apply_ui_element_overlay,
    build_emoji_events_from_timings,
    create_split_screen_clip,
    enforce_3s_broll_rule,
    generate_emoji_subtitle_overlay,
    overlay_graphic_badge,
    overlay_watermark,
)
from viral_retention_engine import ViralRetentionEngine


def _vc_attr(name: str, default: Any) -> Any:
    vc = sys.modules.get("video_composer")
    return getattr(vc, name, default) if vc is not None else default


def _face_centered_source(clip, path, target_w, target_h):
    """Crop source frames before time/flip transforms so the same track stays aligned."""
    if clip.w <= clip.h:
        return clip, False
    try:
        from visuals.face_reframe import detect_face_track, face_center_at
        track = detect_face_track(path, duration=float(clip.duration or 0.0))
        if not track:
            return clip, False
        crop_w = min(int(clip.w), max(2, int(clip.h * target_w / target_h)))
        crop_w -= crop_w % 2
        if crop_w >= clip.w:
            return clip, False

        def follow_face(get_frame, time):
            frame = get_frame(time)
            left = round(frame.shape[1] * face_center_at(track, time) - crop_w / 2.0)
            left = max(0, min(frame.shape[1] - crop_w, left))
            left -= left % 2
            return frame[:, left:left + crop_w]

        centered = clip.fl(follow_face).resize(newsize=(target_w, target_h))
        return centered, True
    except Exception as error:
        print(f"    [FaceCenter] Fit-fill fallback: {error}")
        return clip, False


def _prep(
    path,
    dur,
    tw,
    th,
    split_screen=False,
    enable_section2=True,
    badge_label=None,
    badge_icon="💡",
    enable_pip=False,
    pip_path=None,
    gameplay_path=None,
    enable_face_center=False,
):
    os_mod = _vc_attr("os", os)
    cfg_mod = _vc_attr("config", config)
    vfc_cls = _vc_attr("VideoFileClip", VideoFileClip)
    face_src_fn = _vc_attr("_face_centered_source", _face_centered_source)

    # Item 256: Downscale 4K/oversized source before effects
    c = vfc_cls(path, audio=False)
    try:
        selected_gameplay = gameplay_path or os_mod.path.join(cfg_mod.ASSETS_DIR, "gameplay_loop.mp4")
        split_active = bool(split_screen and os_mod.path.exists(selected_gameplay))
        face_centered = False
        if enable_face_center:
            panel_h = int(th * 0.58) if split_active else th
            c, face_centered = face_src_fn(c, path, tw, panel_h)
        if c.w > tw and c.h > th:
            c = c.resize(width=tw) if c.w >= c.h else c.resize(height=th)
        elif c.w > tw * 1.2:
            c = c.resize(width=tw)
        elif c.h > th * 1.2:
            c = c.resize(height=th)

        if enable_section2:
            c = _vc_attr("apply_speed_ramp", apply_speed_ramp)(c)

        is_text_card = any(k in path.lower() for k in ("reddit", "card", "text", "title"))
        if enable_section2 and not is_text_card:
            c = _vc_attr("apply_horizontal_flip", apply_horizontal_flip)(c)

        if c.duration > dur:
            st = (c.duration - dur) / 2
            c = c.subclip(st, st + dur)
        elif c.duration < dur:
            f = c.duration / dur
            c = c.fx(vfx.speedx, f) if f >= 0.5 else c.loop(duration=dur)

        if split_screen:
            if os_mod.path.exists(selected_gameplay):
                c = _vc_attr("create_split_screen_clip", create_split_screen_clip)(c, selected_gameplay, tw, th)
            else:
                c = _vc_attr("apply_smart_crop", apply_smart_crop)(c, tw, th, blur_intensity=0.40)
        else:
            c = _vc_attr("apply_smart_crop", apply_smart_crop)(c, tw, th, blur_intensity=0.40)

        if enable_pip:
            c = _vc_attr("apply_pip_overlay", apply_pip_overlay)(c, pip_clip_or_path=pip_path)

        if enable_section2 and c.duration > 3.2:
            c = _vc_attr("enforce_3s_broll_rule", enforce_3s_broll_rule)(c, max_duration=3.2)

        if badge_label:
            c = _vc_attr("overlay_graphic_badge", overlay_graphic_badge)(c, label=badge_label, icon=badge_icon)

        if enable_section2:
            c = _vc_attr("apply_multi_layer_overlay", apply_multi_layer_overlay)(c, opacity=0.10)

        if enable_section2:
            c = _vc_attr("apply_corner_radius_to_clip", apply_corner_radius_to_clip)(c, radius=28)

        c._face_centered = face_centered
        return c
    except Exception:
        try:
            c.close()
        except Exception:
            pass
        raise


def _fit(c, tw, th):
    """Fallback legacy helper delegating directly to smart crop with 40% blur."""
    return _vc_attr("apply_smart_crop", apply_smart_crop)(c, tw, th, blur_intensity=0.40)


def build_composer_scene_segments(
    *,
    scene_clips: list,
    W: int,
    H: int,
    split_screen: bool,
    enable_section2_filters: bool,
    enable_ken_burns: bool,
    gameplay_path: Optional[str],
    enable_face_center: bool,
    niche_id: str,
    title: str,
    hc: dict,
    max_hold: float,
    cut_sec: float,
    interrupt_dur: float,
    progress_callback: Optional[Callable],
    cancel_check: Optional[Callable],
) -> List[Any]:
    """Prepare all per-scene MoviePy clips with motion, shake, color splash, and transitions."""
    os_mod = _vc_attr("os", os)
    prep_fn = _vc_attr("_prep", _prep)
    color_clip_cls = _vc_attr("ColorClip", ColorClip)
    comp_clip_cls = _vc_attr("CompositeVideoClip", CompositeVideoClip)

    segs = []
    total_scenes = len(scene_clips)
    for idx, sc in enumerate(scene_clips):
        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
        p, d = sc.get("path"), sc.get("duration", 7)
        try:
            d = float(d)
        except (TypeError, ValueError):
            d = 3.0
        if hc:
            d = min(d, max_hold)

        if not p or not os_mod.path.exists(p):
            fallback_clip = color_clip_cls(size=(W, H), color=(15, 15, 25), duration=d)
            segs.append(fallback_clip)
        else:
            try:
                enable_pip = sc.get("enable_pip", False)
                pip_path = sc.get("pip_path", None)
                badge_label = sc.get("badge_label")
                clip_seg = prep_fn(
                    p, d, W, H,
                    split_screen=split_screen,
                    enable_section2=enable_section2_filters,
                    badge_label=badge_label,
                    enable_pip=enable_pip,
                    pip_path=pip_path,
                    gameplay_path=gameplay_path,
                    enable_face_center=enable_face_center,
                )
                face_centered = bool(getattr(clip_seg, "_face_centered", False))
                if hc and clip_seg is not None and float(getattr(clip_seg, "duration", 0) or 0) > cut_sec + 0.05:
                    clip_seg = _vc_attr("apply_capcut_density_cuts", apply_capcut_density_cuts)(
                        clip_seg, cut_sec=cut_sec, force=True
                    )
                if enable_ken_burns and not enable_section2_filters and not face_centered:
                    clip_seg = _vc_attr("apply_ken_burns", apply_ken_burns)(clip_seg, zoom_start=1.00, zoom_end=1.04)

                if enable_section2_filters and not face_centered:
                    shake_intensity = 5.0 if sc.get("handheld_shake", True) else 3.5
                    clip_seg = _vc_attr("apply_handheld_camera_shake", apply_handheld_camera_shake)(
                        clip_seg, intensity=shake_intensity
                    )

                if enable_section2_filters and (
                    idx == 3
                    or sc.get("mood") in ("dramatic", "shock", "tehlike")
                    or sc.get("beat_type") == "climax"
                ):
                    clip_seg = _vc_attr("apply_color_splash_moviepy", apply_color_splash_moviepy)(
                        clip_seg, keep_hue_center=120.0, tolerance=30.0
                    )

                if sc.get("affiliate_product") or (
                    enable_section2_filters
                    and idx == max(0, len(scene_clips) - 3)
                    and any(k in (niche_id or title or "").lower() for k in ("affiliate", "wealth", "16_wealth", "monetiz"))
                ):
                    mockup = _vc_attr("apply_affiliate_3d_mockup", apply_affiliate_3d_mockup)(p, target_w=W, target_h=H)
                    if mockup:
                        mockup = mockup.set_duration(d).set_position("center")
                        clip_seg = comp_clip_cls([clip_seg, mockup], size=(W, H))
                        clip_seg.duration = d

                if sc.get("wipe_transition", False) and idx > 0:
                    direction = sc.get("wipe_direction", "horizontal")
                    clip_seg = _vc_attr("apply_mask_wipe_transition", apply_mask_wipe_transition)(
                        clip_seg, direction=direction, transition_dur=0.35
                    )

                if idx == 0 and enable_section2_filters:
                    clip_seg = _vc_attr("apply_out_of_focus_reveal", apply_out_of_focus_reveal)(
                        clip_seg, blur_duration=0.35
                    )
                    clip_seg = _vc_attr("apply_censored_blur_bait", apply_censored_blur_bait)(
                        clip_seg, reveal_after=3.0
                    )
                    interrupts = ViralRetentionEngine.PATTERN_INTERRUPTS
                    interrupt_type = interrupts[idx % len(interrupts)]["type"]
                    if interrupt_type == "warning_badge":
                        interrupt_type = "glitch_flash"
                    clip_seg = _vc_attr("apply_opening_pattern_interrupt", apply_opening_pattern_interrupt)(
                        clip_seg, interrupt_type=interrupt_type, duration=interrupt_dur
                    )

                if enable_section2_filters and not face_centered:
                    clip_seg = _vc_attr("apply_alternating_motion", apply_alternating_motion)(
                        clip_seg, scene_index=idx
                    )

                if enable_section2_filters:
                    clip_seg = _vc_attr("apply_scene_brightness_alternation", apply_scene_brightness_alternation)(
                        clip_seg, scene_index=idx
                    )

                if sc.get("slow_motion_highlight") or (
                    enable_section2_filters and sc.get("is_visual_cutaway")
                ):
                    clip_seg = _vc_attr("apply_slow_motion_highlight", apply_slow_motion_highlight)(
                        clip_seg, speed_factor=0.5
                    )

                if enable_section2_filters and sc.get("is_visual_cutaway"):
                    clip_seg = _vc_attr("apply_broll_speed_boost", apply_broll_speed_boost)(
                        clip_seg, speed_factor=1.5
                    )

                if enable_section2_filters and (
                    sc.get("impact_shake")
                    or sc.get("audio_visual_contrast")
                    or sc.get("slow_motion_highlight")
                ):
                    clip_seg = _vc_attr("apply_impact_screen_shake", apply_impact_screen_shake)(
                        clip_seg, intensity=14.0, duration=0.35
                    )

                if enable_section2_filters and idx > 0:
                    clip_seg = _vc_attr("apply_micro_zoom_out", apply_micro_zoom_out)(
                        clip_seg, zoom_start=1.04, zoom_end=1.00
                    )

                segs.append(clip_seg)
                print(f"  [Composer] Sahne #{idx+1}/{total_scenes} hazırlandı ({d:.1f}s).", flush=True)
            except Exception as e:
                print(f"    Clip error on scene #{idx+1}: {e}", flush=True)
                fallback_clip = color_clip_cls(size=(W, H), color=(15, 15, 25), duration=d)
                segs.append(fallback_clip)

        if progress_callback:
            seg_pct = int(10 + ((idx + 1) / total_scenes) * 15)
            progress_callback(seg_pct, f"Sahneler hazırlandı ({idx + 1}/{total_scenes})...")

    return segs


def apply_composer_global_overlays(
    *,
    combined: Any,
    scene_clips: list,
    word_timings: list,
    W: int,
    H: int,
    enable_section2_filters: bool,
    anti_duplicate: bool,
    watermark_path: Optional[str],
    mute_hook: str,
    retention_metadata: Optional[dict],
    title: str,
    hybrid_render_overlay: Optional[dict],
    hybrid_niche: str,
) -> Any:
    """Apply MoviePy global overlays (emoji, watermark, end card, neon, sticky banner, CTA, hybrid UI)."""
    os_mod = _vc_attr("os", os)
    cfg_mod = _vc_attr("config", config)
    comp_clip_cls = _vc_attr("CompositeVideoClip", CompositeVideoClip)

    if enable_section2_filters and not getattr(cfg_mod, "RENDER_SAFE_MODE", True):
        emoji_events = _vc_attr("build_emoji_events_from_timings", build_emoji_events_from_timings)(
            word_timings, scene_clips
        )
        if emoji_events:
            emoji_overlay = _vc_attr("generate_emoji_subtitle_overlay", generate_emoji_subtitle_overlay)(
                W, H, combined.duration, emoji_events, fps=combined.fps or cfg_mod.FPS
            )
            if emoji_overlay:
                combined = comp_clip_cls([combined, emoji_overlay], size=(W, H))
                combined.duration = sum(float(sc.get("duration", 3.0)) for sc in scene_clips)
        combined = _vc_attr("apply_heartbeat_zoom", apply_heartbeat_zoom)(combined, bpm=60.0)
        combined = _vc_attr("apply_particle_overlay", apply_particle_overlay)(
            combined, particle_type="spark", particle_count=30
        )
        combined = _vc_attr("apply_speaker_avatar_overlay", apply_speaker_avatar_overlay)(combined, avatar_size=96)
    elif getattr(cfg_mod, "RENDER_SAFE_MODE", True):
        print("  [Composer] [Item 125] Emoji animasyon katmanı: RENDER_SAFE_MODE aktif, bypass edildi.")

    if anti_duplicate and not getattr(cfg_mod, "RENDER_SAFE_MODE", True):
        print("  [Composer] Applying anti-duplicate filter (Item 50)...")
        combined = _vc_attr("apply_anti_duplicate", apply_anti_duplicate)(combined)
    elif anti_duplicate:
        print("  [Composer] [Item 50] Anti-duplicate: FFmpeg GPU renk filtreleme aktif, MoviePy CPU bypass edildi.")

    if watermark_path and os_mod.path.exists(watermark_path):
        print("  [Composer] Overlaying channel watermark logo (Item 381)...")
        combined = _vc_attr("overlay_watermark", overlay_watermark)(combined, watermark_path)

    if not getattr(cfg_mod, "RENDER_SAFE_MODE", True):
        combined = _vc_attr("apply_end_card_to_video", apply_end_card_to_video)(
            combined,
            duration=3.0,
            channel_name="Abone Ol",
            cta_text="Takip Et ve bildirimleri ac!",
        )
        print("  [Composer] End card overlay applied (Item 126).")
    else:
        print("  [Composer] [Item 126] End card overlay: RENDER_SAFE_MODE aktif, bypass edildi.")

    if enable_section2_filters:
        combined = _vc_attr("apply_neon_countdown_overlay", apply_neon_countdown_overlay)(
            combined, duration=3.0, position="top_right"
        )
        print("  [Composer] Neon countdown overlay applied (Item 212).")

        combined = _vc_attr("apply_neon_curiosity_opening_graphic", apply_neon_curiosity_opening_graphic)(
            combined, duration=2.5, symbol="?"
        )
        print("  [Composer] Neon curiosity opening graphic applied (Item 246).")

        combined = _vc_attr("apply_dynamic_progress_bar", apply_dynamic_progress_bar)(
            combined, bar_height=4, position="bottom"
        )
        print("  [Composer] Dynamic neon progress bar applied (Item 138).")

        banner = mute_hook or ViralRetentionEngine.get_sticky_hook_banner("", mood="warning", lang="tr")
        combined = _vc_attr("apply_sticky_hook_banner_overlay", apply_sticky_hook_banner_overlay)(
            combined, banner_text=banner
        )
        print(f"  [Composer] Sticky hook banner applied (Item 232): {banner[:48]!r}")

        combined = _vc_attr("apply_micro_animated_sticker_overlay", apply_micro_animated_sticker_overlay)(
            combined, sticker="arrow", duration=2.5
        )
        print("  [Composer] Micro animated sticker applied (Item 238).")

    if enable_section2_filters and not getattr(cfg_mod, "RENDER_SAFE_MODE", True):
        combined = _vc_attr("apply_fluid_gradient_background", apply_fluid_gradient_background)(combined)
        print("  [Composer] Fluid gradient background applied (Item 123).")

    if enable_section2_filters:
        meta = retention_metadata or {}
        topic = title or ""
        share_text = meta.get("share_cta") or ViralRetentionEngine.generate_share_cta(topic, lang="tr")
        bookmark_text = meta.get("bookmark_cta") or ViralRetentionEngine.generate_bookmark_cta(topic, lang="tr")
        share_at = max(0.0, combined.duration * 0.62)
        bookmark_at = max(0.0, combined.duration * 0.78)
        combined = _vc_attr("apply_share_cta_overlay", apply_share_cta_overlay)(
            combined, cta_text=share_text, start_at=share_at, duration=3.0
        )
        combined = _vc_attr("apply_bookmark_cta_overlay", apply_bookmark_cta_overlay)(
            combined, cta_text=bookmark_text, start_at=bookmark_at, duration=3.0
        )
        print("  [Composer] Share + bookmark CTA overlays applied (Items 235-236).")

    overlay_spec = hybrid_render_overlay or {}
    if not overlay_spec and hybrid_niche:
        try:
            from hybrid_niches import get_hybrid_render_overlay_spec
            overlay_spec = get_hybrid_render_overlay_spec(hybrid_niche)
        except Exception:
            overlay_spec = {}
    ui_type = overlay_spec.get("ui_type")
    if enable_section2_filters and ui_type in ("split_choice", "subtitle_bar"):
        combined = _vc_attr("apply_hybrid_render_overlay", apply_hybrid_render_overlay)(combined, overlay_spec)
        print(f"  [Composer] [B5] Hybrid structured overlay applied ({ui_type}).")
    elif enable_section2_filters and ui_type:
        combined = _vc_attr("apply_ui_element_overlay", apply_ui_element_overlay)(
            combined,
            ui_type=ui_type if ui_type != "imessage" else "ios_notification",
            header_text=overlay_spec.get("header", title or "Bildirim"),
            body_text=overlay_spec.get("body", "Sonuna kadar izle!"),
            start_time=0.6,
            duration=min(3.5, combined.duration * 0.35),
        )
        print(f"  [Composer] [Item 131/B5] Hybrid UI overlay applied ({ui_type}).")

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
            combined = _vc_attr("apply_keyword_white_flash_overlay", apply_keyword_white_flash_overlay)(
                combined, timestamp=flash_at, duration=0.18
            )
            print(f"  [Composer] [Item 260] Keyword white flash @ {flash_at:.2f}s.")

    loop_formula = (retention_metadata or {}).get("loop_formula") or ""
    if enable_section2_filters and (
        loop_formula == "infinite_cycle"
        or overlay_spec.get("overlay") == "spiral"
    ):
        combined = _vc_attr("apply_infinite_spiral_overlay", apply_infinite_spiral_overlay)(
            combined, duration=min(4.0, combined.duration)
        )
        print("  [Composer] [Item 224] Infinite spiral overlay applied.")

    if enable_section2_filters and overlay_spec.get("overlay") == "time_tunnel":
        combined = _vc_attr("apply_time_tunnel_overlay", apply_time_tunnel_overlay)(
            combined, duration=min(3.5, combined.duration)
        )
        print("  [Composer] [Item 261] Time tunnel overlay applied.")

    overlay_kind = overlay_spec.get("overlay")
    if enable_section2_filters and overlay_kind and overlay_kind not in ("spiral", "time_tunnel", "split_screen"):
        combined = _vc_attr("apply_hybrid_render_overlay", apply_hybrid_render_overlay)(combined, overlay_spec)
        item_ref = overlay_spec.get("item", overlay_kind)
        print(f"  [Composer] [B5] Hybrid render overlay applied ({item_ref}).")

    return combined
