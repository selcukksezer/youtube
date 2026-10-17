"""
Overlay Cards, Thumbnails, Badges, Avatars, Emoji Events & UI Elements.
Extracted from `effects/overlays.py` for modular maintainability.
PIL avatar, emoji, end-card, and UI element drawing helpers live in
`effects/overlay_card_drawers.py` and are re-exported here.
"""
from __future__ import annotations

import os
import random
import subprocess
from typing import Any, Optional, Tuple

from moviepy.editor import (
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    VideoFileClip,
    vfx,
)
import numpy as np
import PIL.Image
from PIL import Image, ImageDraw, ImageFilter, ImageFont

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, "Resampling", PIL.Image).LANCZOS

import config
from effects.overlay_card_drawers import (
    _MOOD_EMOJI_MAP,
    apply_end_card_to_video,
    apply_speaker_avatar_overlay,
    apply_ui_element_overlay,
    build_emoji_events_from_timings,
    generate_emoji_subtitle_overlay,
    generate_end_card_overlay,
    generate_retro_avatar_png,
    generate_ui_element_overlay,
    get_mood_emoji,
)


def score_frame_thumbnail_quality(frame: np.ndarray) -> float:
    """
    R10 #59/#92: Contrast + mid-bright luminance score for Shorts frame-0 pick.
    Higher = more feed-visible (avoid near-black / flat frames).
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        return 0.0
    arr = frame.astype(np.float32)
    if arr.ndim == 3:
        luma = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    else:
        luma = arr
    mean = float(np.mean(luma))
    std = float(np.std(luma))
    brightness_penalty = abs(mean - 135.0) / 135.0
    contrast = min(1.0, std / 64.0)
    return max(0.0, (contrast * 70.0) + (30.0 * (1.0 - min(1.0, brightness_penalty))))


def select_best_thumbnail_timestamp(
    video_path: str,
    sample_times: Optional[list] = None,
    max_samples: int = 8,
) -> Tuple[float, float]:
    """
    R10 #59/#92: Sample early frames and return (best_t, score).
    Defaults to first ~3s (Shorts feed decision window).
    """
    if not os.path.exists(video_path):
        return 1.0, 0.0
    times = list(sample_times or [])
    if not times:
        times = [0.05, 0.35, 0.7, 1.0, 1.4, 1.8, 2.3, 2.8][:max_samples]
    best_t, best_score = times[0], -1.0
    try:
        with VideoFileClip(video_path, audio=False) as clip:
            dur = float(clip.duration or 1.0)
            for t in times:
                tt = min(max(0.0, float(t)), max(0.0, dur - 0.04))
                try:
                    frame = clip.get_frame(tt)
                    sc = score_frame_thumbnail_quality(frame)
                    if sc > best_score:
                        best_score, best_t = sc, tt
                except Exception:
                    continue
    except Exception:
        return 1.0, 0.0
    return best_t, best_score


def extract_frame0_thumbnail(video_path: str, output_thumb_path: str) -> bool:
    """
    Items 59, 92 / R10 #59/#92: Peak-curiosity thumbnail via contrast/brightness scan.
    Falls back to t=1s still if scoring fails.
    """
    if not os.path.exists(video_path):
        return False
    try:
        import shutil
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            try:
                import imageio_ffmpeg
                ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ffmpeg_bin = "ffmpeg"

        best_t, score = select_best_thumbnail_timestamp(video_path)
        ss = max(0.0, float(best_t))
        cmd = [
            ffmpeg_bin, "-y", "-ss", f"{ss:.3f}", "-i", video_path,
            "-frames:v", "1", "-q:v", "2", output_thumb_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_thumb_path):
            meta_path = output_thumb_path.rsplit(".", 1)[0] + "_thumb_meta.txt"
            try:
                with open(meta_path, "w", encoding="utf-8") as fh:
                    fh.write(f"t={ss:.3f}\nscore={score:.2f}\nrule=r10_59_92\n")
            except Exception:
                pass
            return True
        cmd = [
            ffmpeg_bin, "-y", "-ss", "00:00:01", "-i", video_path,
            "-frames:v", "1", "-q:v", "2", output_thumb_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def generate_intro_hook_card(
    width: int,
    height: int,
    hook_text: str,
    duration: float = 1.2,
    bg_color: Tuple[int, int, int] = (12, 12, 20),
    accent: Tuple[int, int, int] = (255, 220, 40),
):
    """
    R10 #61: 1–1.5s branded intro card before main timeline (text hook + accent bar).
    Returns an ImageClip or None.
    """
    try:
        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        bar_h = max(8, height // 80)
        draw.rectangle([0, 0, width, bar_h], fill=accent)
        draw.rectangle([0, height - bar_h, width, height], fill=accent)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size=max(36, width // 18))
        except Exception:
            font = ImageFont.load_default()
        text = (hook_text or "İZLE").strip()[:72]
        words = text.split()
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if len(trial) > 22 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        lines = lines[:4] or ["İZLE"]
        y = height // 2 - (len(lines) * 48) // 2
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            draw.text(((width - tw) // 2, y), line, fill=(255, 255, 255), font=font)
            y += 52
        arr = np.array(img)
        return ImageClip(arr).set_duration(max(0.6, float(duration)))
    except Exception as e:
        print(f"    [IntroHookCard] Notice: {e}")
        return None


def apply_keyword_pop_text(
    clip: VideoFileClip,
    text: str,
    start: float = 0.0,
    duration: float = 0.85,
    color: Tuple[int, int, int] = (255, 255, 80),
) -> VideoFileClip:
    """R10 #74: Keyword pop — short emphasis text scales in over base clip."""
    try:
        w, h = clip.size
        card = generate_intro_hook_card(w, h // 5, text, duration=duration, bg_color=(0, 0, 0), accent=color)
        if card is None:
            return clip
        band = (
            card.resize(height=max(80, h // 6))
            .set_opacity(0.92)
            .set_start(max(0.0, float(start)))
            .set_duration(max(0.4, float(duration)))
            .set_position(("center", h // 2 - 40))
        )
        out = CompositeVideoClip([clip, band], size=clip.size)
        out.duration = clip.duration
        if clip.audio:
            out = out.set_audio(clip.audio)
        return out
    except Exception as e:
        print(f"    [KeywordPop] Notice: {e}")
        return clip


def apply_multi_layer_overlay(
    clip: VideoFileClip,
    opacity: float = 0.10,
    overlay_type: str = "light_leak",
) -> VideoFileClip:
    """Item 75: Görsel Katmanlama (Multi-Layer B-Roll)."""
    if getattr(config, "RENDER_SAFE_MODE", True):
        return clip
    try:
        w, h = clip.size
        asset_file = os.path.join(config.ASSETS_DIR, f"{overlay_type}.mp4")
        if os.path.exists(asset_file):
            layer = VideoFileClip(asset_file).resize((w, h)).set_opacity(opacity).set_duration(clip.duration)
            if layer.duration < clip.duration:
                layer = layer.fx(vfx.loop, duration=clip.duration)
            return CompositeVideoClip([clip, layer], size=(w, h))

        leak_color = random.choice([(255, 235, 190), (255, 215, 160), (245, 225, 205)])
        glow_layer = (
            ColorClip(size=(w, h), color=leak_color)
            .set_opacity(opacity)
            .set_duration(clip.duration)
        )
        composite = CompositeVideoClip([clip, glow_layer], size=(w, h))
        composite.duration = clip.duration
        return composite
    except Exception as e:
        print(f"    [MultiLayerOverlay] Notice: {e}")
        return clip


def overlay_graphic_badge(
    clip: VideoFileClip,
    label: str = "#1 ADIM",
    icon: str = "💡",
    position: Optional[Tuple[Any, Any]] = None,
    duration: Optional[float] = None,
) -> VideoFileClip:
    """Item 82: Metin İçi Görsel Çıkartmalar (Stickers / Badges / Counters)."""
    if not label or getattr(config, "RENDER_SAFE_MODE", True):
        return clip
    try:
        badge_w, badge_h = 320, 76
        img = PIL.Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle(
            [(2, 2), (badge_w - 2, badge_h - 2)],
            radius=24,
            fill=(20, 24, 36, 215),
            outline=(255, 215, 0, 230),
            width=3,
        )

        display_text = f"{icon}  {label}".strip()
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        draw.text((24, 26), display_text, fill=(255, 255, 255, 255), font=font)

        badge_arr = np.array(img)
        badge_clip = ImageClip(badge_arr, ismask=False, transparent=True)
        badge_dur = duration if duration is not None else min(clip.duration, 3.0)
        badge_clip = badge_clip.set_duration(badge_dur)

        pos = position if position is not None else ("center", 120)
        badge_clip = badge_clip.set_position(pos)

        composite = CompositeVideoClip([clip, badge_clip], size=clip.size)
        composite.duration = clip.duration
        return composite
    except Exception as e:
        print(f"    [GraphicBadge] Notice: {e}")
        return clip


def overlay_micro_brand_signature(
    clip: VideoFileClip,
    duration: float = 0.40,
    logo_path: Optional[str] = None,
) -> VideoFileClip:
    """Item 87: Özgün İntro/Outro İmzası."""
    try:
        w, h = clip.size
        sig_w, sig_h = int(w * 0.28), 54
        img = PIL.Image.new("RGBA", (sig_w, sig_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            [(1, 1), (sig_w - 2, sig_h - 2)],
            radius=16,
            fill=(15, 20, 30, 180),
            outline=(255, 215, 0, 200),
            width=2,
        )
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((16, 18), "⚡ OFFICIAL SHORT", fill=(255, 255, 255, 240), font=font)

        sig_arr = np.array(img)
        sig_clip = (
            ImageClip(sig_arr, ismask=False, transparent=True)
            .set_duration(duration)
            .set_position(("center", int(h * 0.08)))
        )
        return CompositeVideoClip([clip, sig_clip], size=clip.size)
    except Exception as e:
        print(f"    [MicroBrandSignature] Notice: {e}")
        return clip


def apply_affiliate_3d_mockup(
    product_img_or_clip: Any,
    target_w: int = 1080,
    target_h: int = 1920,
    shadow_offset: Tuple[int, int] = (14, 20),
    tilt_angle: float = -4.5,
) -> VideoFileClip:
    """Item 105: Affiliate Ürün Görsellerini Yeniden Boyutlandırma & 3D Mock-up."""
    try:
        if isinstance(product_img_or_clip, str) and os.path.exists(product_img_or_clip):
            prod_img = PIL.Image.open(product_img_or_clip).convert("RGBA")
        else:
            prod_img = PIL.Image.new("RGBA", (640, 640), (245, 245, 250, 255))
            draw_p = ImageDraw.Draw(prod_img)
            draw_p.rounded_rectangle([(10, 10), (630, 630)], radius=24, outline=(220, 220, 225), width=3)
            draw_p.text((120, 300), "⭐ PREMIUM PRODUCT", fill=(20, 20, 30, 255))

        pw, ph = prod_img.size
        scale = min(680 / pw, 680 / ph)
        nw, nh = int(pw * scale), int(ph * scale)
        prod_resized = prod_img.resize((nw, nh), PIL.Image.ANTIALIAS)

        canvas = PIL.Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        shadow = PIL.Image.new("RGBA", (nw + 20, nh + 20), (0, 0, 0, 90)).filter(ImageFilter.GaussianBlur(16))

        rotated_prod = prod_resized.rotate(tilt_angle, resample=PIL.Image.BICUBIC, expand=True)
        rw, rh = rotated_prod.size
        cx, cy = (target_w - rw) // 2, (target_h - rh) // 2

        canvas.paste(shadow, (cx + shadow_offset[0], cy + shadow_offset[1]), mask=shadow)
        canvas.paste(rotated_prod, (cx, cy), mask=rotated_prod)

        return ImageClip(np.array(canvas), ismask=False, transparent=True)
    except Exception as e:
        print(f"    [AffiliateMockup] Notice: {e}")
        return ColorClip(size=(target_w, target_h), color=(0, 0, 0, 0), duration=3.0)
