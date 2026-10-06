"""
effects/ticker.py — Breaking News Ticker & Red Alert Banner Generator.

Adapted and evolved from reference_repos/youtube-shorts-pipeline
(render/ticker.py, verticals/assemble.py).
Generates broadcast-grade breaking news lower-third ticker banners
with pulsing alert badges, gold accent stripes, and single-pass FFmpeg
overlay filters for the 1_news_flash and finance niches.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from services.path_security import validate_asset_path


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
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


def generate_news_ticker_image(
    headline: str,
    output_path: str,
    category: str = "SON DAKİKA",
    width: int = 1080,
    height: int = 130,
    alert_color: str = "#D32F2F",
    bar_bg_color: str = "#111111",
    text_color: str = "#FFFFFF",
    accent_stripe_color: str = "#FFD700",
) -> str:
    """
    Renders a crisp broadcast-style Breaking News ticker banner PNG:
    - Red alert badge on left [● SON DAKİKA]
    - Dark semi-transparent ticker band with yellow/gold accent stripe
    - High-legibility headline typography
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Accent top stripe (3px gold/yellow line)
    stripe_h = 4
    draw.rectangle([0, 0, width, stripe_h], fill=accent_stripe_color)

    # Main dark bar background (semi-transparent 92% opacity)
    draw.rectangle([0, stripe_h, width, height], fill=(18, 18, 18, 235))

    # Alert Badge on left (e.g. SON DAKİKA or BREAKING NEWS)
    badge_w = 260
    draw.rectangle([0, stripe_h, badge_w, height], fill=alert_color)

    # Red pulsing dot indicator inside badge
    dot_radius = 6
    dot_cx = 24
    dot_cy = stripe_h + (height - stripe_h) // 2
    draw.ellipse(
        [dot_cx - dot_radius, dot_cy - dot_radius, dot_cx + dot_radius, dot_cy + dot_radius],
        fill="#FFFFFF",
    )

    # Alert badge text
    font_badge = _get_font(28, bold=True)
    draw.text((44, dot_cy - 16), category.upper(), fill="#FFFFFF", font=font_badge)

    # Headline text inside dark bar
    font_headline = _get_font(26, bold=True)
    text_x = badge_w + 24
    text_y = stripe_h + (height - stripe_h) // 2 - 15

    # Truncate headline with ellipsis if too wide
    max_text_w = width - text_x - 30
    disp_text = headline.strip().upper()
    while len(disp_text) > 8:
        bbox = draw.textbbox((0, 0), disp_text, font=font_headline)
        if (bbox[2] - bbox[0]) <= max_text_w:
            break
        disp_text = disp_text[:-4].strip() + "..."

    draw.text((text_x, text_y), disp_text, fill=text_color, font=font_headline)

    # Bottom border
    draw.rectangle([0, height - 2, width, height], fill=(40, 40, 40, 255))

    img.save(output_path, "PNG")
    return output_path


def build_news_ticker_ffmpeg_filter(
    ticker_png_path: str,
    video_input_tag: str = "0:v",
    overlay_input_index: int = 1,
    out_tag: str = "out_ticker",
    y_pos: int = 240,
    enable_start: float = 0.0,
    enable_end: Optional[float] = None,
) -> Tuple[str, str]:
    """
    Builds the single-pass FFmpeg filter complex expression to overlay
    the breaking news ticker onto the 9:16 vertical video stream.
    Placed in the upper safe-zone (below title/header, above center focus).
    """
    enable_expr = f"gte(t,{enable_start:.2f})"
    if enable_end and enable_end > enable_start:
        enable_expr = f"between(t,{enable_start:.2f},{enable_end:.2f})"

    flt = (
        f"[{video_input_tag}][{overlay_input_index}:v]overlay="
        f"x=0:y={y_pos}:enable='{enable_expr}'[{out_tag}]"
    )
    return flt, out_tag


def is_ticker_enabled_for_niche(niche_id: str) -> bool:
    """Returns True if the niche calls for an authoritative breaking news ticker."""
    if not niche_id:
        return False
    norm = str(niche_id).lower().strip()
    return norm in ("1_news_flash", "news", "breaking_news", "finance", "crypto_news", "politics")
