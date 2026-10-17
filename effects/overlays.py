"""
Graphic Overlays, Watermarks, Badges, Avatars & UI Cards
Covers items: 59, 60, 75, 82, 87, 92, 105, 118, 125, 126, 131, 138, 212, 232, 238, 246

Sub-modules:
- `effects/overlay_cards.py`: Thumbnails, intro cards, badges, retro avatars, emoji events, end cards, UI overlays
- `effects/overlay_hybrid.py`: Procedural RGBA helpers, B5 hybrid overlays, interactive quiz overlay
"""
import math
import os
import random
import subprocess
import tempfile
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

from effects.overlay_cards import (
    _MOOD_EMOJI_MAP,
    apply_affiliate_3d_mockup,
    apply_end_card_to_video,
    apply_keyword_pop_text,
    apply_multi_layer_overlay,
    apply_speaker_avatar_overlay,
    apply_ui_element_overlay,
    build_emoji_events_from_timings,
    extract_frame0_thumbnail,
    generate_emoji_subtitle_overlay,
    generate_end_card_overlay,
    generate_intro_hook_card,
    generate_retro_avatar_png,
    generate_ui_element_overlay,
    get_mood_emoji,
    overlay_graphic_badge,
    overlay_micro_brand_signature,
    score_frame_thumbnail_quality,
    select_best_thumbnail_timestamp,
)
from effects.overlay_hybrid import (
    _make_procedural_rgba_clip,
    _overlay_safe_mode_bypass,
    apply_countdown_wheel_overlay,
    apply_epic_vignette_overlay,
    apply_eq_bar_overlay,
    apply_hybrid_frame_overlay,
    apply_hybrid_render_overlay,
    apply_infinite_spiral_overlay,
    apply_interactive_quiz_overlay,
    apply_neon_frame_overlay,
    apply_soft_vignette_overlay,
    apply_split_choice_overlay,
    apply_subtitle_bar_overlay,
    apply_time_tunnel_overlay,
)


def overlay_watermark(clip: VideoFileClip, watermark_path: str, opacity: float = 0.75) -> VideoFileClip:
    """
    Item 60: Brand logo / watermark overlay on top right/left.
    """
    if not watermark_path or not os.path.exists(watermark_path):
        return clip
    try:
        wm = (
            ImageClip(watermark_path)
            .resize(width=int(clip.w * 0.22))
            .set_opacity(opacity)
            .set_duration(clip.duration)
            .set_position(("right", 40))
        )
        return CompositeVideoClip([clip, wm], size=clip.size)
    except Exception as e:
        print(f"    [Watermark] Error: {e}")
        return clip


def generate_dynamic_progress_bar(
    width: int,
    height: int,
    duration: float,
    bar_height: int = 4,
    color: tuple = (0, 255, 204),
    position: str = "bottom",
    fps: float = 30.0,
) -> VideoClip:
    """
    Item 138 – Dinamik İlerleme Çubuğu.
    Ekranın en altına veya üstüne videonun bittiğini hissettirmeyen ince neon bir
    ilerleme çubuğu koyar. Süre boyunca soldan sağa akıcı bir şekilde dolar.
    """
    def make_rgb(t):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        prog = min(1.0, max(0.0, t / max(0.1, duration)))
        fill_w = int(width * prog)
        y0 = height - bar_height if position == "bottom" else 0
        y1 = height if position == "bottom" else bar_height
        if fill_w > 0:
            frame[y0:y1, 0:fill_w] = color
        return frame

    def make_mask(t):
        mask = np.zeros((height, width), dtype=float)
        prog = min(1.0, max(0.0, t / max(0.1, duration)))
        fill_w = int(width * prog)
        y0 = height - bar_height if position == "bottom" else 0
        y1 = height if position == "bottom" else bar_height
        if fill_w > 0:
            mask[y0:y1, 0:fill_w] = 0.90
        return mask

    mask_clip = VideoClip(make_mask, ismask=True, duration=duration).set_fps(fps)
    bar_clip = VideoClip(make_rgb, ismask=False, duration=duration).set_fps(fps).set_mask(mask_clip)
    print(f"    [Item 138] Dinamik neon ilerleme çubuğu üretildi: pos={position}, h={bar_height}px, {duration:.1f}s")
    return bar_clip


def apply_share_cta_overlay(
    base_clip,
    cta_text: str = "Arkadaşına gönder",
    start_at: float = 0.0,
    duration: float = 3.0,
):
    """Item 235: Paylaşma güdüsü — alt-sol neon paylaş CTA bandı."""
    try:
        w, h = base_clip.size
        dur = base_clip.duration
        show_dur = min(duration, max(0.5, dur - start_at))
        if show_dur <= 0:
            return base_clip
        bar_h = 48
        img = Image.new("RGBA", (int(w * 0.62), bar_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(0, 0), (img.width - 1, bar_h - 1)], radius=14, fill=(20, 120, 255, 220))
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((14, 14), f"↗ {cta_text[:36]}", fill=(255, 255, 255, 255), font=font)
        banner = (
            ImageClip(np.array(img), ismask=False, transparent=True)
            .set_duration(show_dur)
            .set_start(start_at)
            .set_position((16, int(h * 0.72)))
        )
        composite = CompositeVideoClip([base_clip, banner], size=(w, h))
        composite.duration = dur
        print(f"    [Item 235] Share CTA overlay @ {start_at:.1f}s")
        return composite
    except Exception as e:
        print(f"    [ShareCTA] Notice: {e}")
        return base_clip


def apply_bookmark_cta_overlay(
    base_clip,
    cta_text: str = "Videoyu kaydet",
    start_at: float = 0.0,
    duration: float = 3.0,
):
    """Item 236: Kaydetme güdüsü — alt-sağ bookmark CTA bandı."""
    try:
        w, h = base_clip.size
        dur = base_clip.duration
        show_dur = min(duration, max(0.5, dur - start_at))
        if show_dur <= 0:
            return base_clip
        bar_h = 48
        img = Image.new("RGBA", (int(w * 0.58), bar_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(0, 0), (img.width - 1, bar_h - 1)], radius=14, fill=(255, 180, 0, 225))
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((14, 14), f"🔖 {cta_text[:34]}", fill=(20, 20, 30, 255), font=font)
        banner = (
            ImageClip(np.array(img), ismask=False, transparent=True)
            .set_duration(show_dur)
            .set_start(start_at)
            .set_position((int(w * 0.38), int(h * 0.78)))
        )
        composite = CompositeVideoClip([base_clip, banner], size=(w, h))
        composite.duration = dur
        print(f"    [Item 236] Bookmark CTA overlay @ {start_at:.1f}s")
        return composite
    except Exception as e:
        print(f"    [BookmarkCTA] Notice: {e}")
        return base_clip


def apply_sticky_hook_banner_overlay(
    base_clip,
    banner_text: str = "⚠️ ASLA BUNU YAPMAYIN",
    bar_height: int = 52,
):
    """
    Item 232: Ekranın Üst Kısmına Sabit Kanca Yazısı.
    Video boyunca üstte sabit uyarı/kanca bandı.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 232] Sticky hook banner: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass
    try:
        w, h = base_clip.size
        dur = base_clip.duration
        img = Image.new("RGBA", (w, bar_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (w, bar_height)], fill=(180, 0, 0, 210))
        draw.rectangle([(0, bar_height - 3), (w, bar_height)], fill=(255, 230, 0, 255))
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((16, 16), banner_text[:48], fill=(255, 255, 255, 255), font=font)
        banner = (
            ImageClip(np.array(img), ismask=False, transparent=True)
            .set_duration(dur)
            .set_position(("center", 0))
        )
        composite = CompositeVideoClip([base_clip, banner], size=(w, h))
        composite.duration = dur
        print(f"    [Item 232] Sticky hook banner: {banner_text[:32]}")
        return composite
    except Exception as e:
        print(f"    [StickyHookBanner] Notice: {e}")
        return base_clip


def apply_micro_animated_sticker_overlay(
    base_clip,
    sticker: str = "arrow",
    duration: float = 2.5,
):
    """
    Item 238: Mikro-Animasyonlu Çıkartmalar.
    Zıplayan ok / işaret parmağı ikonu ilgiyi diri tutar.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 238] Micro animated sticker: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass
    try:
        w, h = base_clip.size
        dur = min(duration, base_clip.duration)
        icons = {"arrow": "⬇️", "point": "👆", "circle": "⭕"}
        icon = icons.get(sticker, "⬇️")
        sticker_w, sticker_h = 96, 96
        img = Image.new("RGBA", (sticker_w, sticker_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((20, 20), icon, fill=(255, 255, 255, 255), font=font)
        arr = np.array(img)

        def bounce_pos(t):
            bounce = int(12 * abs(math.sin(t * 5.0)))
            return (int(w * 0.78), int(h * 0.38) + bounce)

        sticker_clip = (
            ImageClip(arr, ismask=False, transparent=True)
            .set_duration(dur)
            .set_position(bounce_pos)
        )
        composite = CompositeVideoClip([base_clip, sticker_clip], size=(w, h))
        composite.duration = base_clip.duration
        print(f"    [Item 238] Micro animated sticker: {sticker}")
        return composite
    except Exception as e:
        print(f"    [MicroAnimatedSticker] Notice: {e}")
        return base_clip


def apply_dynamic_progress_bar(
    base_clip,
    bar_height: int = 4,
    color: tuple = (0, 255, 204),
    position: str = "bottom",
):
    """
    Item 138 – Temel klibin üzerine dinamik neon ilerleme çubuğu bindirir.
    NOT: RENDER_SAFE_MODE=True iken bypass edilir (tüm video süresince per-frame çizim).
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 138] Dinamik ilerleme çubuğu: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    dur = base_clip.duration
    fps = base_clip.fps or 30.0

    bar = generate_dynamic_progress_bar(
        w, h, duration=dur, bar_height=bar_height,
        color=color, position=position, fps=fps,
    )
    composite = CompositeVideoClip([base_clip, bar], size=(w, h))
    composite.duration = dur
    return composite


def generate_neon_countdown_overlay(
    width: int,
    height: int,
    duration: float = 3.0,
    position: str = "top_right",
    fps: float = 30.0,
    lang: str = "tr",
) -> VideoClip:
    """
    Item 212: Geri Sayım Sayacı (Countdown Timer).
    Köşede 3..2..1 neon sayaç; quiz/merak formatlarında retention kancası.
    """
    countdown_nums = [3, 2, 1]
    sec_per_num = duration / len(countdown_nums)
    neon_rgb = (0, 255, 102)
    glow_rgb = (255, 230, 0)

    def make_rgba(t):
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        if t >= duration:
            return np.array(img)

        idx = min(int(t / sec_per_num), len(countdown_nums) - 1)
        num = countdown_nums[idx]
        local_t = t - idx * sec_per_num
        pulse = 0.88 + 0.12 * math.sin(2 * math.pi * local_t * 4.0)

        box = int(min(width, height) * 0.11 * pulse)
        margin = int(width * 0.05)
        if position == "top_left":
            x0, y0 = margin, int(height * 0.07)
        else:
            x0, y0 = width - margin - box, int(height * 0.07)

        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            [x0, y0, x0 + box, y0 + box],
            radius=max(8, box // 5),
            fill=(8, 12, 24, 215),
            outline=glow_rgb + (255,),
            width=3,
        )
        inner = max(8, box // 6)
        draw.rounded_rectangle(
            [x0 + inner, y0 + inner, x0 + box - inner, y0 + box - inner],
            radius=max(6, box // 7),
            outline=neon_rgb + (180,),
            width=2,
        )
        draw.text(
            (x0 + box // 2, y0 + box // 2),
            str(num),
            fill=neon_rgb + (255,),
            anchor="mm",
        )
        if idx == 0 and local_t < 0.35:
            hint = "GÖSTERİLİYOR" if lang == "tr" else "REVEAL"
            draw.text(
                (x0 + box // 2, y0 + box + 18),
                hint,
                fill=glow_rgb + (220,),
                anchor="mm",
            )
        return np.array(img)

    def make_rgb(t):
        return make_rgba(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_rgba(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=duration).set_fps(fps)
    clip = VideoClip(make_rgb, ismask=False, duration=duration).set_fps(fps).set_mask(mask)
    print(f"    [Item 212] Neon countdown overlay: {duration:.1f}s, pos={position}")
    return clip


def apply_neon_countdown_overlay(
    base_clip,
    duration: float = 3.0,
    position: str = "top_right",
    lang: str = "tr",
):
    """
    Item 212 – Videonun ilk N saniyesine neon geri sayım bindirir.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 212] Neon countdown: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    dur = min(duration, base_clip.duration)
    fps = base_clip.fps or 30.0
    overlay = generate_neon_countdown_overlay(
        w, h, duration=dur, position=position, fps=fps, lang=lang,
    ).set_start(0)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    return composite


def generate_neon_curiosity_opening_graphic(
    width: int,
    height: int,
    duration: float = 2.5,
    symbol: str = "?",
    fps: float = 30.0,
) -> VideoClip:
    """
    Item 246: Merak Tetikleyici Açılış Grafiği — neon soru/ünlem işareti parlaması.
    """
    neon_rgb = (255, 0, 255)
    glow_rgb = (0, 255, 255)

    def make_rgba(t):
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        if t >= duration:
            return np.array(img)
        fade = 1.0 if t < duration * 0.85 else max(0.0, 1.0 - (t - duration * 0.85) / (duration * 0.15))
        pulse = 0.82 + 0.18 * math.sin(2 * math.pi * t * 3.5)
        size = int(min(width, height) * 0.18 * pulse * fade)
        cx, cy = width // 2, int(height * 0.42)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), symbol, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x0, y0 = cx - tw // 2, cy - th // 2
        for offset, alpha in ((4, 90), (2, 140), (0, 255)):
            draw.text(
                (x0 + offset, y0 + offset),
                symbol,
                font=font,
                fill=glow_rgb + (int(alpha * fade),),
            )
        draw.text((x0, y0), symbol, font=font, fill=neon_rgb + (int(255 * fade),))
        return np.array(img)

    clip = VideoClip(make_frame=lambda t: make_rgba(t)[:, :, :3], duration=duration)
    clip = clip.set_fps(fps).set_mask(
        VideoClip(make_frame=lambda t: make_rgba(t)[:, :, 3] / 255.0, ismask=True, duration=duration).set_fps(fps)
    )
    print(f"    [Item 246] Neon curiosity opening graphic: symbol={symbol}, {duration:.1f}s")
    return clip


def apply_neon_curiosity_opening_graphic(
    base_clip,
    duration: float = 2.5,
    symbol: str = "?",
):
    """
    Item 246 – Videonun açılışına neon soru/ünlem grafiği bindirir.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 246] Neon curiosity graphic: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    dur = min(duration, base_clip.duration)
    fps = base_clip.fps or 30.0
    overlay = generate_neon_curiosity_opening_graphic(
        w, h, duration=dur, symbol=symbol, fps=fps,
    ).set_start(0)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    return composite


def apply_keyword_white_flash_overlay(
    base_clip,
    timestamp: float = 0.0,
    duration: float = 0.18,
    peak_alpha: float = 0.82,
):
    """
    Item 260: Görsel Aydınlanma Anı (Flash of Light).
    Kilit kelime anında ekrandan beyaz ışık süzmesi — kısa fade-in/out overlay.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 260] White flash: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    fps = getattr(base_clip, "fps", None) or 30.0
    flash_dur = min(duration, max(0.05, base_clip.duration - timestamp))
    if flash_dur <= 0 or timestamp >= base_clip.duration:
        return base_clip

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        local = t / flash_dur if flash_dur > 0 else 0.0
        if local <= 0.5:
            alpha = peak_alpha * (local / 0.5)
        else:
            alpha = peak_alpha * (1.0 - (local - 0.5) / 0.5)
        alpha = max(0.0, min(1.0, alpha))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, h], fill=(255, 255, 255, int(alpha * 255)))
        return np.array(img)

    def make_rgb(t):
        return make_rgba(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_rgba(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=flash_dur).set_fps(fps)
    overlay = VideoClip(make_rgb, ismask=False, duration=flash_dur).set_fps(fps).set_mask(mask)
    overlay = overlay.set_start(timestamp)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    print(f"    [Item 260] Keyword white flash @ {timestamp:.2f}s ({flash_dur:.2f}s)")
    return composite
