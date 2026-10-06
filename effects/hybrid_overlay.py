"""
Native transparent PNG generator for Hybrid Niche UI Overlays (Items 276-345).
Generates standalone transparent PNG assets (iOS notifications, chat bubbles,
split choice panels, subtitle bars, neon frames) to be composited directly inside
the single-pass FFmpeg filter_complex via `overlay=enable='between(t,start,end)'`.

Eliminates MoviePy frame-by-frame PIL generation, CPU bottleneck and memory leaks.
"""
from __future__ import annotations

import os
import math
from typing import Any, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

_DEFAULT_FONT_PATHS = (
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Safely resolve font with fallback to default PIL font."""
    paths = (
        (r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if bold
        else (r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    )
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def is_native_hybrid_supported(overlay_spec: Dict[str, Any]) -> bool:
    """Return True if overlay_spec can be rendered natively in FFmpeg filter graph."""
    if not isinstance(overlay_spec, dict) or not overlay_spec:
        return False
    ui_type = str(overlay_spec.get("ui_type") or "").lower()
    overlay_kind = str(overlay_spec.get("overlay") or "").lower()

    supported_ui = {
        "imessage",
        "ios_notification",
        "split_choice",
        "interactive_quiz",
        "tweet_card",
        "search_bar",
        "subtitle_bar",
    }
    supported_overlay = {
        "neon_frame",
        "hybrid_frame",
        "epic_vignette",
        "soft_vignette",
        "countdown_wheel",
        "eq_bar",
        "split_screen",
    }
    return (ui_type in supported_ui) or (overlay_kind in supported_overlay)


def create_hybrid_ui_overlay_png(
    overlay_spec: Dict[str, Any],
    width: int = 1080,
    height: int = 1920,
    total_duration: float = 30.0,
    out_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Builds a transparent PNG overlay and returns positioning/timing metadata for FFmpeg.
    Returns:
        {
            "png_path": str,
            "start_time": float,
            "duration": float,
            "end_time": float,
            "x_expr": str,
            "y_expr": str,
            "enable_expr": str,
        }
    """
    if not isinstance(overlay_spec, dict) or not overlay_spec:
        return None

    if not out_path:
        out_path = os.path.abspath("temp_hybrid_overlay.png")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    ui_type = str(overlay_spec.get("ui_type") or "").lower()
    overlay_kind = str(overlay_spec.get("overlay") or "").lower()
    header = str(overlay_spec.get("header") or "BİLDİRİM").strip()
    body = str(overlay_spec.get("body") or "").strip()
    label = str(overlay_spec.get("label") or header or "HYBRID").strip()

    # 1. iOS Notification / iMessage chat simulation (Items 277, 279, 286, 287, 336)
    if ui_type in ("imessage", "ios_notification"):
        card_w = min(width - 80, 960)
        card_h = 160
        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Dark glassmorphic background with rounded pill shape
        draw.rounded_rectangle(
            [0, 0, card_w, card_h],
            radius=32,
            fill=(22, 28, 38, 230),
            outline=(80, 110, 150, 180),
            width=2,
        )

        # Left circular app avatar/badge
        avatar_r = 28
        avatar_cx = 50
        avatar_cy = card_h // 2
        draw.ellipse(
            [avatar_cx - avatar_r, avatar_cy - avatar_r, avatar_cx + avatar_r, avatar_cy + avatar_r],
            fill=(0, 122, 255, 240),
            outline=(255, 255, 255, 120),
            width=2,
        )
        # Message icon inside avatar
        draw.polygon(
            [
                (avatar_cx - 12, avatar_cy - 8),
                (avatar_cx + 12, avatar_cy - 8),
                (avatar_cx + 12, avatar_cy + 8),
                (avatar_cx - 4, avatar_cy + 8),
                (avatar_cx - 10, avatar_cy + 14),
                (avatar_cx - 10, avatar_cy + 8),
                (avatar_cx - 12, avatar_cy + 8),
            ],
            fill=(255, 255, 255, 240),
        )

        font_header = _get_font(28, bold=True)
        font_body = _get_font(24, bold=False)
        font_time = _get_font(20, bold=False)

        # Header title
        draw.text((100, 36), header[:32], fill=(255, 255, 255, 240), font=font_header)
        # Body preview
        display_body = (body or "Yeni mesaj içeriği...")[:50]
        draw.text((100, 84), display_body, fill=(195, 205, 220, 220), font=font_body)
        # Time badge right-aligned
        draw.text((card_w - 95, 38), "şimdi", fill=(140, 155, 175, 190), font=font_time)

        img.save(out_path, format="PNG")
        start_t = 0.6
        dur = min(3.5, max(2.0, total_duration * 0.35))
        return {
            "png_path": out_path,
            "start_time": start_t,
            "duration": dur,
            "end_time": start_t + dur,
            "x_expr": "(W-w)/2",
            "y_expr": str(round(height * 0.05)),
            "enable_expr": f"between(t,{start_t:.2f},{(start_t + dur):.2f})",
        }

    # 2. Split Choice / Would You Rather Duel (Items 280, 284)
    elif ui_type in ("split_choice", "interactive_quiz"):
        card_w = min(width - 120, 920)
        card_h = 280
        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Main container
        draw.rounded_rectangle(
            [0, 0, card_w, card_h],
            radius=28,
            fill=(15, 20, 30, 220),
            outline=(100, 140, 200, 160),
            width=2,
        )

        font_title = _get_font(28, bold=True)
        font_choice = _get_font(26, bold=True)

        draw.text(
            (card_w // 2 - 80, 20),
            header or "HANGİSİNİ SEÇERDİN?",
            fill=(255, 215, 0, 240),
            font=font_title,
        )

        # Option A (Red pill)
        pill_h = 75
        draw.rounded_rectangle(
            [30, 80, card_w - 30, 80 + pill_h],
            radius=18,
            fill=(220, 45, 55, 220),
            outline=(255, 120, 120, 200),
            width=2,
        )
        draw.text((60, 102), f"🔴 A: {header[:30]}", fill=(255, 255, 255, 240), font=font_choice)

        # Option B (Blue pill)
        draw.rounded_rectangle(
            [30, 175, card_w - 30, 175 + pill_h],
            radius=18,
            fill=(25, 110, 225, 220),
            outline=(120, 180, 255, 200),
            width=2,
        )
        draw.text((60, 197), f"🔵 B: {(body or 'İkinci Seçenek')[:30]}", fill=(255, 255, 255, 240), font=font_choice)

        img.save(out_path, format="PNG")
        start_t = 1.0
        dur = min(4.0, max(2.5, total_duration * 0.45))
        return {
            "png_path": out_path,
            "start_time": start_t,
            "duration": dur,
            "end_time": start_t + dur,
            "x_expr": "(W-w)/2",
            "y_expr": str(round(height * 0.38)),
            "enable_expr": f"between(t,{start_t:.2f},{(start_t + dur):.2f})",
        }

    # 3. Tweet Card or Search Bar (Items 283, 290, 292)
    elif ui_type in ("tweet_card", "search_bar"):
        card_w = min(width - 100, 920)
        card_h = 140
        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle(
            [0, 0, card_w, card_h],
            radius=24,
            fill=(18, 22, 30, 230),
            outline=(70, 90, 120, 180),
            width=2,
        )
        # Search icon / badge
        draw.ellipse([30, 42, 80, 92], fill=(40, 50, 70, 200), outline=(120, 160, 210, 180), width=2)
        font_main = _get_font(26, bold=True)
        font_sub = _get_font(22, bold=False)

        draw.text((100, 36), f"🔍 {header[:35]}", fill=(255, 255, 255, 240), font=font_main)
        draw.text((100, 80), (body or "Aranan içerik doğrulanıyor...")[:45], fill=(160, 180, 210, 210), font=font_sub)

        img.save(out_path, format="PNG")
        start_t = 0.8
        dur = min(3.5, max(2.0, total_duration * 0.35))
        return {
            "png_path": out_path,
            "start_time": start_t,
            "duration": dur,
            "end_time": start_t + dur,
            "x_expr": "(W-w)/2",
            "y_expr": str(round(height * 0.05)),
            "enable_expr": f"between(t,{start_t:.2f},{(start_t + dur):.2f})",
        }

    # 4. Subtitle bar / info ribbon (Item 288)
    elif ui_type == "subtitle_bar":
        card_w = width
        card_h = 100
        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, card_w, card_h], fill=(10, 15, 25, 210), outline=(40, 60, 90, 160), width=1)
        font_bar = _get_font(24, bold=True)
        draw.text((40, 36), f"📌 {header}: {body[:50]}", fill=(255, 255, 255, 230), font=font_bar)

        img.save(out_path, format="PNG")
        start_t = 1.0
        dur = min(4.5, max(2.5, total_duration * 0.45))
        return {
            "png_path": out_path,
            "start_time": start_t,
            "duration": dur,
            "end_time": start_t + dur,
            "x_expr": "0",
            "y_expr": str(round(height * 0.72)),
            "enable_expr": f"between(t,{start_t:.2f},{(start_t + dur):.2f})",
        }

    # 5. Neon Frame / Hybrid Frame / Vignettes (Items 276, 282, 285, 289, 291, 326)
    elif overlay_kind in ("neon_frame", "hybrid_frame", "epic_vignette", "soft_vignette"):
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        accent = (0, 255, 220) if "neon" in overlay_kind else (255, 210, 120)
        border_w = 6
        inset = 16

        # Cyber/luxury corner brackets
        bracket_len = int(min(width, height) * 0.12)
        # Top-left
        draw.line([inset, inset, inset + bracket_len, inset], fill=(*accent, 220), width=border_w)
        draw.line([inset, inset, inset, inset + bracket_len], fill=(*accent, 220), width=border_w)
        # Top-right
        draw.line([width - inset - bracket_len, inset, width - inset, inset], fill=(*accent, 220), width=border_w)
        draw.line([width - inset, inset, width - inset, inset + bracket_len], fill=(*accent, 220), width=border_w)
        # Bottom-left
        draw.line([inset, height - inset, inset + bracket_len, height - inset], fill=(*accent, 220), width=border_w)
        draw.line([inset, height - inset - bracket_len, inset, height - inset], fill=(*accent, 220), width=border_w)
        # Bottom-right
        draw.line([width - inset - bracket_len, height - inset, width - inset, height - inset], fill=(*accent, 220), width=border_w)
        draw.line([width - inset, height - inset - bracket_len, width - inset, height - inset], fill=(*accent, 220), width=border_w)

        # Top label badge
        if label:
            font_lbl = _get_font(20, bold=True)
            lbl_text = f"◆ {label.upper()[:28]} ◆"
            lbl_w = len(lbl_text) * 12 + 40
            draw.rounded_rectangle(
                [width // 2 - lbl_w // 2, 24, width // 2 + lbl_w // 2, 60],
                radius=10,
                fill=(12, 16, 24, 210),
                outline=(*accent, 180),
                width=1,
            )
            draw.text((width // 2 - lbl_w // 2 + 20, 32), lbl_text, fill=(255, 255, 255, 220), font=font_lbl)

        img.save(out_path, format="PNG")
        start_t = 0.0
        dur = max(2.0, total_duration)
        return {
            "png_path": out_path,
            "start_time": start_t,
            "duration": dur,
            "end_time": start_t + dur,
            "x_expr": "0",
            "y_expr": "0",
            "enable_expr": f"between(t,{start_t:.2f},{(start_t + dur):.2f})",
        }

    # 6. Countdown wheel or EQ bar (Items 325, 327)
    elif overlay_kind in ("countdown_wheel", "eq_bar"):
        card_w = min(width - 160, 800)
        card_h = 160
        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle(
            [0, 0, card_w, card_h],
            radius=20,
            fill=(15, 22, 32, 210),
            outline=(60, 160, 240, 180),
            width=2,
        )

        font_action = _get_font(32, bold=True)
        if overlay_kind == "countdown_wheel":
            draw.text((card_w // 2 - 120, 60), "🎯 DUR! (STOP)", fill=(255, 60, 80, 240), font=font_action)
        else:
            draw.text((card_w // 2 - 140, 60), "📊 RİTİM EŞLEME", fill=(0, 240, 180, 240), font=font_action)

        img.save(out_path, format="PNG")
        start_t = 1.0
        dur = min(4.0, max(2.0, total_duration * 0.4))
        return {
            "png_path": out_path,
            "start_time": start_t,
            "duration": dur,
            "end_time": start_t + dur,
            "x_expr": "(W-w)/2",
            "y_expr": str(round(height * 0.55)),
            "enable_expr": f"between(t,{start_t:.2f},{(start_t + dur):.2f})",
        }

    return None
