"""
whatsapp_chat_renderer.py — WhatsApp / iMessage Dark-Mode Chat Bubble Renderer
==============================================================================
RULES_100_AUDIT.md #20 (`20_whatsapp_chat_story` / `20_whatsapp_confessions`):
- PIL tabanlı şeffaf (RGBA) WhatsApp / iMessage tarzı karanlık mod sohbet baloncukları
- Çift mavi tık (✓✓), zaman damgası, gönderen/alıcı hizalaması ve pop-in animasyonu
- FFmpeg overlay filtre zinciri ve MoviePy ImageClip entegrasyonu
"""
from __future__ import annotations

import os
import textwrap
from typing import Any

from PIL import Image, ImageDraw, ImageFont

import config


def _load_chat_font(size: int, bold: bool = False):
    font_candidates = [
        getattr(config, "FONT_BOLD" if bold else "FONT_REGULAR", ""),
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_candidates:
        if fp and os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_transparent_whatsapp_chat_png(
    output_path: str,
    messages: list[dict[str, Any]] | None = None,
    contact_name: str = "Gizli Numara",
    status_text: str = "çevrimiçi",
    width: int = 920,
) -> str:
    """
    WhatsApp Dark Mode tarzında şeffaf (RGBA) sohbet kartı PNG üretir.
    messages: [{"sender": "other"|"me", "text": "...", "time": "23:41"}]
    """
    if not messages:
        messages = [
            {"sender": "other", "text": "Bunu kimseye söylemeyeceğine söz ver.", "time": "23:41"},
            {"sender": "me", "text": "Ne oldu? Beni korkutuyorsun.", "time": "23:42"},
            {"sender": "other", "text": "Dün gece gördüğüm şey tesadüf değildi...", "time": "23:43"},
        ]

    font_header = _load_chat_font(28, bold=True)
    font_status = _load_chat_font(20, bold=False)
    font_msg = _load_chat_font(28, bold=False)
    font_time = _load_chat_font(18, bold=False)

    wrapped_items = []
    total_bubbles_h = 0
    for msg in messages[:6]:
        raw_text = str(msg.get("text") or "").strip()
        lines = textwrap.wrap(raw_text, width=30) or [""]
        bubble_h = 28 + len(lines) * 38 + 24
        wrapped_items.append(
            {
                "sender": str(msg.get("sender") or "other").lower(),
                "lines": lines,
                "time": str(msg.get("time") or "23:45"),
                "height": bubble_h,
            }
        )
        total_bubbles_h += bubble_h + 18

    header_h = 96
    pad = 24
    height = header_h + pad * 2 + total_bubbles_h + 16

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer container (WhatsApp Dark Mode #0B141A)
    draw.rounded_rectangle(
        [(0, 0), (width - 1, height - 1)],
        radius=32,
        fill=(11, 20, 26, 238),
        outline=(42, 57, 66, 220),
        width=3,
    )

    # Top header bar (#202C33)
    draw.rounded_rectangle(
        [(0, 0), (width - 1, header_h)],
        radius=32,
        fill=(32, 44, 51, 250),
    )
    draw.rectangle([(0, header_h - 28), (width - 1, header_h)], fill=(32, 44, 51, 250))

    # Avatar circle in header
    av_x, av_y, av_r = 32, 20, 56
    draw.ellipse([(av_x, av_y), (av_x + av_r, av_y + av_r)], fill=(0, 168, 132, 255))
    initial = (contact_name.strip()[:1] or "?").upper()
    draw.text((av_x + 18, av_y + 12), initial, font=font_header, fill=(255, 255, 255, 255))

    # Contact name & online status
    draw.text((av_x + av_r + 18, 22), contact_name[:28], font=font_header, fill=(233, 237, 239, 255))
    draw.text((av_x + av_r + 18, 56), status_text[:28], font=font_status, fill=(0, 168, 132, 255))

    y_cursor = header_h + pad
    for item in wrapped_items:
        is_me = item["sender"] in ("me", "self", "outgoing", "right")
        bubble_w = min(width - 140, max(280, max(len(line) for line in item["lines"]) * 17 + 72))
        bubble_h = item["height"]
        if is_me:
            bx0 = width - pad - bubble_w
            bx1 = width - pad
            bg_color = (0, 92, 75, 248)  # WhatsApp outgoing dark green (#005C4B)
        else:
            bx0 = pad
            bx1 = pad + bubble_w
            bg_color = (32, 44, 51, 248)  # WhatsApp incoming dark slate (#202C33)

        draw.rounded_rectangle(
            [(bx0, y_cursor), (bx1, y_cursor + bubble_h)],
            radius=22,
            fill=bg_color,
        )

        ty = y_cursor + 16
        for line in item["lines"]:
            draw.text((bx0 + 20, ty), line, font=font_msg, fill=(233, 237, 239, 255))
            ty += 38

        # Timestamp + read receipt ticks
        time_label = f"{item['time']}  ✓✓" if is_me else item["time"]
        time_color = (83, 189, 235, 255) if is_me else (134, 150, 160, 235)
        draw.text((bx1 - 115 if is_me else bx1 - 75, y_cursor + bubble_h - 26), time_label, font=font_time, fill=time_color)
        y_cursor += bubble_h + 18

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def build_whatsapp_card_ffmpeg_filter(
    png_path: str,
    duration: float = 4.0,
    video_w: int = 1080,
    video_h: int = 1920,
) -> dict[str, Any]:
    """FFmpeg filter_complex overlay definition with pop-in slide animation."""
    card_w = 920
    x_expr = f"({video_w}-{card_w})/2"
    target_y = int(video_h * 0.20)
    y_expr = f"if(lt(t,0.30), {target_y}+50*(1-t/0.30), {target_y})"
    filter_complex = (
        f"[1:v]format=rgba,fade=in:st=0:d=0.25:alpha=1[wa_card];"
        f"[0:v][wa_card]overlay=x='{x_expr}':y='{y_expr}':eof_action=pass[outv]"
    )
    return {
        "png_path": png_path,
        "filter_complex": filter_complex,
        "input_args": ["-i", png_path],
        "output_map": "[outv]",
        "duration": duration,
    }


def generate_whatsapp_chat_clip(
    messages: list[dict[str, Any]] | None = None,
    contact_name: str = "Gizli Numara",
    duration: float = 4.0,
    video_size: tuple[int, int] = (1080, 1920),
):
    """MoviePy RGBA ImageClip wrapper for WhatsApp chat story overlay."""
    import tempfile
    from moviepy.editor import ImageClip

    tmp_png = os.path.join(tempfile.gettempdir(), f"wa_chat_{os.getpid()}.png")
    generate_transparent_whatsapp_chat_png(
        output_path=tmp_png,
        messages=messages,
        contact_name=contact_name,
    )
    return ImageClip(tmp_png, transparent=True).set_duration(duration).set_position(("center", int(video_size[1] * 0.18)))
