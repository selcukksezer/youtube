"""
Procedural & B5 Hybrid Overlays (Items 276–345, R10 #97 Interactive Quiz).
Extracted from `effects/overlays.py` for modular maintainability.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

from moviepy.editor import CompositeVideoClip, VideoClip, VideoFileClip
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config


def _overlay_safe_mode_bypass(base_clip, item_label: str):
    try:
        if getattr(config, "RENDER_SAFE_MODE", True):
            print(f"    [{item_label}] RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass
    return None


def _make_procedural_rgba_clip(base_clip, duration: float, frame_fn):
    w, h = base_clip.size
    fps = getattr(base_clip, "fps", None) or 30.0
    dur = min(duration, base_clip.duration)

    def make_rgb(t):
        return frame_fn(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return frame_fn(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=dur).set_fps(fps)
    overlay = VideoClip(make_rgb, ismask=False, duration=dur).set_fps(fps).set_mask(mask).set_start(0)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    return composite


def apply_infinite_spiral_overlay(
    base_clip,
    duration: float = 4.0,
    opacity: float = 0.35,
    rotation_speed: float = 0.8,
):
    """
    Item 224: Sonsuz Sarmal Animasyonu — merkezde dönen hipnotik spiral overlay.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 224] Infinite spiral: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    fps = getattr(base_clip, "fps", None) or 30.0
    dur = min(duration, base_clip.duration)
    cx, cy = w // 2, h // 2
    max_r = int(min(w, h) * 0.45)

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        angle_offset = t * rotation_speed * 360.0
        for arm in range(3):
            base_angle = angle_offset + arm * 120.0
            for step in range(40):
                r = max_r * (step / 40.0)
                theta = math.radians(base_angle + step * 18.0)
                x = cx + r * math.cos(theta)
                y = cy + r * math.sin(theta)
                alpha = int(255 * opacity * (1.0 - step / 40.0))
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(180, 220, 255, alpha))
        return np.array(img)

    def make_rgb(t):
        return make_rgba(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_rgba(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=dur).set_fps(fps)
    overlay = VideoClip(make_rgb, ismask=False, duration=dur).set_fps(fps).set_mask(mask).set_start(0)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    print(f"    [Item 224] Infinite spiral overlay ({dur:.1f}s, opacity={opacity})")
    return composite


def apply_time_tunnel_overlay(
    base_clip,
    duration: float = 3.5,
    streak_count: int = 24,
    opacity: float = 0.42,
):
    """
    Item 261: Zaman Tüneli Hissi — radial streak / zoom warp overlay.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 261] Time tunnel: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    fps = getattr(base_clip, "fps", None) or 30.0
    dur = min(duration, base_clip.duration)
    cx, cy = w // 2, h // 2

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pulse = 0.5 + 0.5 * math.sin(t * 4.0)
        for i in range(streak_count):
            angle = (360.0 / streak_count) * i + t * 120.0
            rad = math.radians(angle)
            inner = int(min(w, h) * 0.08)
            outer = int(min(w, h) * (0.35 + 0.25 * pulse))
            x0 = cx + inner * math.cos(rad)
            y0 = cy + inner * math.sin(rad)
            x1 = cx + outer * math.cos(rad)
            y1 = cy + outer * math.sin(rad)
            alpha = int(255 * opacity * (0.4 + 0.6 * pulse))
            draw.line([x0, y0, x1, y1], fill=(120, 200, 255, alpha), width=3)
        draw.ellipse(
            [cx - inner, cy - inner, cx + inner, cy + inner],
            fill=(255, 255, 255, int(80 * opacity)),
        )
        return np.array(img)

    def make_rgb(t):
        return make_rgba(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_rgba(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=dur).set_fps(fps)
    overlay = VideoClip(make_rgb, ismask=False, duration=dur).set_fps(fps).set_mask(mask).set_start(0)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    print(f"    [Item 261] Time tunnel overlay ({dur:.1f}s)")
    return composite


def apply_hybrid_frame_overlay(
    base_clip,
    label: str = "",
    bg_style: str = "",
    accent_rgb: Tuple[int, int, int] = (0, 255, 200),
    opacity: float = 0.85,
):
    """
    B5 generic hybrid frame — niche label bar + accent border (Items 289–345 fallback).
    """
    bypass = _overlay_safe_mode_bypass(base_clip, "B5 hybrid_frame")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = base_clip.duration
    display = (label or bg_style or "HYBRID")[:42]
    accent = accent_rgb

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pulse = 0.65 + 0.35 * math.sin(t * 3.0)
        border = int(3 + pulse * 2)
        draw.rectangle([8, 8, w - 8, h - 8], outline=(*accent, int(220 * opacity)), width=border)
        bar_h = int(h * 0.07)
        draw.rectangle([0, h - bar_h, w, h], fill=(10, 12, 20, int(200 * opacity)))
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", max(18, w // 28))
        except Exception:
            font = ImageFont.load_default()
        draw.text((24, h - bar_h + 8), display.upper(), fill=(*accent, 255), font=font)
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print(f"    [B5] Hybrid frame overlay ({display[:24]})")
    return out


def apply_neon_frame_overlay(base_clip, opacity: float = 0.9):
    """Item 276: cyberpunk neon corner brackets."""
    bypass = _overlay_safe_mode_bypass(base_clip, "Item 276 neon_frame")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = base_clip.duration
    colors = [(0, 255, 220), (255, 0, 180)]

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        seg = int(min(w, h) * 0.12)
        for idx, col in enumerate(colors):
            off = int(12 + 4 * math.sin(t * 4 + idx))
            x0, y0 = off, off
            x1, y1 = w - off, h - off
            draw.line([x0, y0, x0 + seg, y0], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x0, y0, x0, y0 + seg], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x1, y0, x1 - seg, y0], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x1, y0, x1, y0 + seg], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x0, y1, x0 + seg, y1], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x0, y1, x0, y1 - seg], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x1, y1, x1 - seg, y1], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x1, y1, x1, y1 - seg], fill=(*col, int(230 * opacity)), width=4)
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print("    [Item 276] Neon frame overlay applied.")
    return out


def apply_epic_vignette_overlay(base_clip, opacity: float = 0.55):
    """Item 282: cinematic gold-edge vignette."""
    bypass = _overlay_safe_mode_bypass(base_clip, "Item 282 epic_vignette")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = base_clip.duration

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, h], fill=(0, 0, 0, int(90 * opacity)))
        inset = int(min(w, h) * 0.06)
        draw.rectangle(
            [inset, inset, w - inset, h - inset],
            outline=(255, 210, 120, int(180 * opacity)),
            width=3,
        )
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print("    [Item 282] Epic vignette overlay applied.")
    return out


def apply_soft_vignette_overlay(base_clip, opacity: float = 0.35):
    """Item 285: warm soft vignette for spiritual/rain niches."""
    bypass = _overlay_safe_mode_bypass(base_clip, "Item 285 soft_vignette")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = base_clip.duration

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, h], fill=(255, 245, 230, int(40 * opacity)))
        draw.rectangle([0, h - int(h * 0.18), w, h], fill=(20, 30, 50, int(120 * opacity)))
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print("    [Item 285] Soft vignette overlay applied.")
    return out


def apply_countdown_wheel_overlay(base_clip, duration: float = 4.0, opacity: float = 0.75):
    """Item 327: spinning stop-wheel game overlay."""
    bypass = _overlay_safe_mode_bypass(base_clip, "Item 327 countdown_wheel")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = min(duration, base_clip.duration)
    cx, cy = w // 2, int(h * 0.62)
    radius = int(min(w, h) * 0.22)

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        angle = t * 220.0
        for i in range(8):
            a = math.radians(angle + i * 45)
            x = cx + radius * math.cos(a)
            y = cy + radius * math.sin(a)
            col = (255, 60, 60) if i % 2 == 0 else (60, 120, 255)
            draw.polygon(
                [cx, cy, x, y, cx + radius * 0.3 * math.cos(a + 0.4), cy + radius * 0.3 * math.sin(a + 0.4)],
                fill=(*col, int(200 * opacity)),
            )
        draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(255, 255, 255, int(240 * opacity)))
        draw.text((cx - 28, cy - 10), "DUR!", fill=(20, 20, 30, 255))
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print(f"    [Item 327] Countdown wheel overlay ({dur:.1f}s)")
    return out


def apply_eq_bar_overlay(base_clip, duration: float = None, bar_count: int = 16, opacity: float = 0.8):
    """Item 325: subtitle-area EQ visualizer bars."""
    bypass = _overlay_safe_mode_bypass(base_clip, "Item 325 eq_bar")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = min(duration or base_clip.duration, base_clip.duration)
    base_y = int(h * 0.82)
    bar_w = max(4, w // (bar_count * 2))

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for i in range(bar_count):
            x = int(w * 0.1) + i * (bar_w + 4)
            level = abs(math.sin(t * 6.0 + i * 0.7)) * 0.85 + 0.1
            bh = int(h * 0.08 * level)
            col = (0, 255, 180) if i % 3 else (120, 200, 255)
            draw.rectangle([x, base_y - bh, x + bar_w, base_y], fill=(*col, int(220 * opacity)))
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print(f"    [Item 325] EQ bar overlay ({dur:.1f}s)")
    return out


def apply_split_choice_overlay(base_clip, header: str = "SEÇ", body: str = "Kırmızı vs Mavi", duration: float = 3.5):
    """Items 280/284: red vs blue split choice panel."""
    bypass = _overlay_safe_mode_bypass(base_clip, "split_choice")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = min(duration, base_clip.duration)

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        mid = w // 2
        draw.rectangle([0, int(h * 0.55), mid, int(h * 0.78)], fill=(220, 40, 40, 180))
        draw.rectangle([mid, int(h * 0.55), w, int(h * 0.78)], fill=(40, 80, 220, 180))
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", max(20, w // 24))
        except Exception:
            font = ImageFont.load_default()
        draw.text((w // 4 - 20, int(h * 0.58)), "A", fill=(255, 255, 255, 255), font=font)
        draw.text((mid + w // 4 - 20, int(h * 0.58)), "B", fill=(255, 255, 255, 255), font=font)
        draw.text((24, int(h * 0.50)), header[:24], fill=(255, 255, 255, 230), font=font)
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print("    [B5] Split choice overlay applied.")
    return out


def apply_subtitle_bar_overlay(base_clip, header: str = "Dizi", body: str = "Kelime...", duration: float = 4.0):
    """Item 288: TV subtitle bar overlay."""
    bypass = _overlay_safe_mode_bypass(base_clip, "subtitle_bar")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = min(duration, base_clip.duration)

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        bar_y = int(h * 0.72)
        draw.rectangle([40, bar_y, w - 40, bar_y + int(h * 0.08)], fill=(0, 0, 0, 190))
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", max(18, w // 30))
        except Exception:
            font = ImageFont.load_default()
        draw.text((56, bar_y + 8), f"{header}: {body}"[:48], fill=(255, 255, 100, 255), font=font)
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print("    [Item 288] Subtitle bar overlay applied.")
    return out


def apply_interactive_quiz_overlay(
    base_clip: VideoFileClip,
    question: str = "Hangisi Doğru?",
    options: Optional[list] = None,
    correct_index: int = 0,
    countdown_sec: float = 3.0,
) -> VideoFileClip:
    """
    R10 #97: İnteraktif Canlı Quiz & Geri Sayım Kartı.
    Generates dynamic 3-second countdown quiz overlay:
    - Phase 1 (0 to countdown_sec): Question card + neutral A/B/C options + ticking countdown timer.
    - Phase 2 (countdown_sec to end): Correct answer option lights up in emerald green with checkmark!
    """
    if options is None or not options:
        options = ["A) Seçenek 1", "B) Seçenek 2", "C) Seçenek 3"]
    w, h = base_clip.size
    dur = base_clip.duration or 5.0

    def make_frame(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_q = ImageFont.truetype("arial.ttf", int(w * 0.045))
            font_opt = ImageFont.truetype("arial.ttf", int(w * 0.038))
            font_timer = ImageFont.truetype("arial.ttf", int(w * 0.065))
        except Exception:
            font_q = font_opt = font_timer = ImageFont.load_default()

        box_y1 = int(h * 0.22)
        box_y2 = int(h * 0.36)
        margin = int(w * 0.06)
        draw.rounded_rectangle(
            [(margin, box_y1), (w - margin, box_y2)],
            radius=16,
            fill=(15, 23, 42, 235),
            outline=(168, 85, 247, 255),
            width=3,
        )
        draw.text((w // 2, (box_y1 + box_y2) // 2), question[:70], fill=(255, 255, 255, 255), font=font_q, anchor="mm")

        is_revealed = t >= countdown_sec
        remaining = max(1, int(math.ceil(countdown_sec - t))) if not is_revealed else 0
        timer_text = f"⏱️ {remaining}" if not is_revealed else "✅ DOĞRU!"
        timer_color = (245, 158, 11, 255) if not is_revealed else (16, 185, 129, 255)
        draw.text((w // 2, box_y2 + int(h * 0.035)), timer_text, fill=timer_color, font=font_timer, anchor="mm")

        start_opt_y = int(h * 0.45)
        opt_h = int(h * 0.08)
        gap = int(h * 0.02)

        for idx, opt_text in enumerate(options[:3]):
            y1 = start_opt_y + idx * (opt_h + gap)
            y2 = y1 + opt_h
            if is_revealed and idx == correct_index:
                fill_color = (6, 78, 59, 245)
                border_color = (16, 185, 129, 255)
                text_color = (255, 255, 255, 255)
                badge = " ✔"
            else:
                fill_color = (30, 41, 59, 220)
                border_color = (255, 255, 255, 60)
                text_color = (226, 232, 240, 255)
                badge = ""

            draw.rounded_rectangle([(margin, y1), (w - margin, y2)], radius=12, fill=fill_color, outline=border_color, width=2)
            draw.text((margin + 20, (y1 + y2) // 2), f"{opt_text}{badge}", fill=text_color, font=font_opt, anchor="lm")

        return np.array(img)

    try:
        return _make_procedural_rgba_clip(base_clip, dur, make_frame)
    except Exception as e:
        print(f"    [InteractiveQuiz] Overlay error: {e}")
        return base_clip


def apply_hybrid_render_overlay(base_clip, overlay_spec: dict):
    """Dispatch B5 hybrid overlay spec → concrete MoviePy overlay."""
    if not overlay_spec:
        return base_clip
    kind = overlay_spec.get("overlay")
    ui_type = overlay_spec.get("ui_type")
    if ui_type == "interactive_quiz" or kind == "interactive_quiz":
        return apply_interactive_quiz_overlay(
            base_clip,
            question=overlay_spec.get("question", "Hangisi Doğru?"),
            options=overlay_spec.get("options"),
            correct_index=overlay_spec.get("correct_index", 0),
            countdown_sec=float(overlay_spec.get("countdown_sec", 3.0)),
        )
    if ui_type == "split_choice":
        return apply_split_choice_overlay(
            base_clip,
            header=overlay_spec.get("header", "SEÇ"),
            body=overlay_spec.get("body", ""),
        )
    if ui_type == "subtitle_bar":
        return apply_subtitle_bar_overlay(
            base_clip,
            header=overlay_spec.get("header", "Dizi"),
            body=overlay_spec.get("body", ""),
        )
    if kind == "neon_frame":
        return apply_neon_frame_overlay(base_clip)
    if kind == "epic_vignette":
        return apply_epic_vignette_overlay(base_clip)
    if kind == "soft_vignette":
        return apply_soft_vignette_overlay(base_clip)
    if kind == "spiral":
        return apply_infinite_spiral_overlay(base_clip)
    if kind == "time_tunnel":
        return apply_time_tunnel_overlay(base_clip)
    if kind == "countdown_wheel":
        return apply_countdown_wheel_overlay(base_clip)
    if kind == "eq_bar":
        return apply_eq_bar_overlay(base_clip)
    if kind == "hybrid_frame":
        label = str(
            overlay_spec.get("label")
            or overlay_spec.get("item")
            or overlay_spec.get("hybrid_id")
            or ""
        )
        return apply_hybrid_frame_overlay(
            base_clip,
            label=label,
            bg_style=overlay_spec.get("bg_style", ""),
        )
    return base_clip
