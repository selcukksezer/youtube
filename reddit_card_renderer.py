"""
reddit_card_renderer.py — Attributed Reddit Post Card Generator & Video Overlay.

Adapted and evolved from reference_repos2/RedditVideoMakerBot (video_creation/final_video.py).
Provides:
1. Standalone full-frame vertical video clip preview (generate_reddit_post_card_clip).
2. Transparent RGBA PNG question card generator (generate_transparent_reddit_card_png).
3. Single-pass FFmpeg overlay filter expression with fade-in/fade-out timing (build_reddit_card_ffmpeg_filter).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
from typing import Dict, Optional

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont


def _get_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        font_name,
        f"C:/Windows/Fonts/{font_name}.ttf",
        f"C:/Windows/Fonts/{font_name.lower()}.ttf",
        f"/System/Library/Fonts/Supplemental/{font_name}.ttf",
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            pass
    return ImageFont.load_default()


def generate_transparent_reddit_card_png(
    title: str,
    subreddit: str = "AskReddit",
    author: str = "u/CuriousThinker",
    upvotes: str = "32.4k",
    comments: str = "1.8k",
    output_path: Optional[str] = None,
    card_width: int = 940,
) -> str:
    """
    Renders an authentic, sleek dark-themed Reddit question card with an alpha channel.
    Perfect for overlaying on gameplay/ASMR videos in the opening 3-4 seconds.
    """
    title_font = _get_font("Arial Bold", 38)
    meta_font = _get_font("Arial Bold", 24)
    stat_font = _get_font("Arial", 22)

    # Wrap title lines
    lines = textwrap.wrap(title.strip(), width=36)
    card_height = 140 + (len(lines) * 52) + 70  # header + title + footer stats

    card = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # Dark background card with rounded corners (#1A1A1B)
    draw.rounded_rectangle(
        [(0, 0), (card_width - 1, card_height - 1)],
        radius=24,
        fill=(26, 26, 27, 245),  # slightly translucent
        outline=(52, 53, 54, 255),
        width=2,
    )

    # Subreddit icon (Reddit Orange #FF4500)
    icon_radius = 24
    draw.ellipse([(32, 28), (32 + icon_radius * 2, 28 + icon_radius * 2)], fill=(255, 69, 0, 255))
    # 'r/' symbol inside icon
    draw.text((45, 36), "r/", font=meta_font, fill=(255, 255, 255, 255))

    # Subreddit name & author
    draw.text((95, 30), f"r/{subreddit}", font=meta_font, fill=(215, 218, 220, 255))
    draw.text((95, 58), f"Posted by {author} • 5h ago", font=stat_font, fill=(129, 131, 132, 255))

    # Thread Question Title
    y = 100
    for line in lines:
        draw.text((32, y), line, font=title_font, fill=(255, 255, 255, 255))
        y += 52

    # Bottom pill badges: Upvotes & Comments
    pill_y = y + 15
    # Upvote badge
    draw.rounded_rectangle([(32, pill_y), (170, pill_y + 40)], radius=18, fill=(45, 46, 47, 255))
    draw.text((50, pill_y + 8), f"▲ {upvotes}", font=stat_font, fill=(255, 69, 0, 255))

    # Comments badge
    draw.rounded_rectangle([(185, pill_y), (330, pill_y + 40)], radius=18, fill=(45, 46, 47, 255))
    draw.text((205, pill_y + 8), f"💬 {comments}", font=stat_font, fill=(215, 218, 220, 255))

    target = output_path or tempfile.mktemp(suffix="_reddit_card.png")
    card.save(target, format="PNG")
    return target


def build_reddit_card_ffmpeg_filter(
    card_png_path: str,
    display_duration: float = 3.5,
    fade_duration: float = 0.35,
    y_pos: int = 580,
    input_video_label: str = "[0:v]",
    output_label: str = "[vout]",
) -> str:
    """
    Builds a single-pass FFmpeg overlay expression with smooth fade-in and fade-out.
    Enables placing the Reddit question card on top of video footage cleanly.
    """
    card_esc = card_png_path.replace("\\", "/").replace(":", "\\:")
    fade_out_start = max(0.0, display_duration - fade_duration)

    return (
        f"movie='{card_esc}',"
        f"format=rgba,"
        f"fade=t=in:st=0:d={fade_duration:.2f}:alpha=1,"
        f"fade=t=out:st={fade_out_start:.2f}:d={fade_duration:.2f}:alpha=1[rcard];"
        f"{input_video_label}[rcard]overlay=(W-w)/2:{y_pos}:enable='between(t,0,{display_duration:.2f})'{output_label}"
    )


def generate_reddit_post_card_clip(post: dict, output_path: str, duration: float = 4.0) -> str:
    """Renders an attributed Reddit post preview card as a vertical video clip (legacy compatibility)."""
    image_path = tempfile.mktemp(suffix="_reddit_post.png")
    try:
        image = Image.new("RGB", (1080, 1920), "#15141b")
        draw = ImageDraw.Draw(image)

        title_font = _get_font("Arial Bold", 43)
        body_font = _get_font("Arial", 32)
        meta_font = _get_font("Arial", 25)
        draw.rounded_rectangle((65, 230, 1015, 1530), radius=26, fill="#25232b", outline="#ff4500", width=3)
        draw.ellipse((105, 280, 165, 340), fill="#ff4500")
        draw.text((185, 287), f"r/{post.get('subreddit', 'reddit')} | Kaynak gönderi önizlemesi", font=meta_font, fill="#c9c7d0")
        y = 390
        for line in textwrap.wrap(post.get("title", ""), width=34):
            draw.text((110, y), line, font=title_font, fill="#ffffff")
            y += 58
        y += 45
        for line in textwrap.wrap(post.get("body", "")[:900], width=48):
            draw.text((110, y), line, font=body_font, fill="#dedce5")
            y += 44
            if y > 1380:
                draw.text((110, y), "...", font=body_font, fill="#dedce5")
                break
        draw.text((110, 1450), "Özgün anlatım için araştırma kaynağı", font=meta_font, fill="#ff9b70")
        image.save(image_path)
        result = subprocess.run([
            imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loop", "1", "-i", image_path, "-t", str(duration),
            "-vf", "scale=1080:1920", "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
        return output_path if result.returncode == 0 and os.path.exists(output_path) else ""
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)