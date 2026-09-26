"""
High-CTR YouTube Thumbnail Generator (Verticals v3 Adaptation & Enhancement).
Supports both 16:9 (1280x720) and 9:16 (1080x1920 Shorts cover) thumbnails.
Features:
- Video frame extraction or Pollinations Flux AI background
- Dark gradient lower-third & vignette for guaranteed legibility
- High-impact bold typography with multi-layer drop shadow
- Accent color highlighting (gold/yellow #FFD700 or vibrant cyan/red) for numbers and hook words
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageFilter


# Target resolutions
RES_16_9 = (1280, 720)
RES_9_16 = (1080, 1920)

# High-impact accent colors
COLOR_WHITE = (255, 255, 255)
COLOR_YELLOW = (255, 215, 0)
COLOR_RED = (255, 59, 48)
COLOR_SHADOW = (10, 10, 10, 220)


def extract_best_video_frame(video_path: str, output_path: str, timestamp_sec: float = 2.0) -> bool:
    """Extract a clear frame from the rendered video using FFmpeg."""
    if not os.path.exists(video_path):
        return False
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-ss", str(max(0.5, timestamp_sec)),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_path,
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception as e:
        print(f"  [Thumbnail] Frame extraction failed: {e}")
        return False


def _find_bold_font(size: int = 64) -> ImageFont.ImageFont:
    """Locate a bold system font across Windows, Linux, and macOS."""
    font_candidates = [
        # Windows
        "C:\\Windows\\Fonts\\impact.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\seguisb.ttf",
        "C:\\Windows\\Fonts\\tahomabd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _wrap_text(draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    """Word-wrap text to fit within max_width."""
    words = text.split()
    lines = []
    curr = ""
    for w in words:
        test = f"{curr} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        w_px = bbox[2] - bbox[0]
        if w_px <= max_width:
            curr = test
        else:
            if curr:
                lines.append(curr)
            curr = w
    if curr:
        lines.append(curr)
    return lines[:4]  # Maximum 4 lines for thumbnails


def _apply_gradient_overlay(base_img: Image.Image, aspect: str = "9:16") -> Image.Image:
    """Apply a smooth dark gradient at the lower half so text is always crisp and readable."""
    w, h = base_img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Start gradient from 45% down the image to 100%
    start_y = int(h * 0.45)
    for y in range(start_y, h):
        progress = (y - start_y) / (h - start_y)
        alpha = int(progress * progress * 215)  # Quadratic fade to ~85% black
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    base_rgba = base_img.convert("RGBA")
    return Image.alpha_composite(base_rgba, overlay).convert("RGB")


def _is_accent_word(word: str) -> bool:
    """Check if word is a high-CTR number or hook trigger."""
    cleaned = re.sub(r"[^\w]", "", word).upper()
    if re.search(r"\d+", cleaned):
        return True
    triggers = {"ASLA", "ŞOK", "SAKIN", "GİZLİ", "EN", "İYİ", "BEDAVA", "ÜCRETSİZ", "HAYAT", "MUCİZE", "YASAK", "DİKKAT"}
    return cleaned in triggers


def generate_thumbnail(
    title: str,
    output_path: str,
    background_path: Optional[str] = None,
    aspect_ratio: str = "9:16",
    accent_text: Optional[str] = None,
) -> str:
    """
    Generate a high-CTR thumbnail with text overlay, drop shadow, and gradient.
    aspect_ratio: '9:16' (1080x1920) or '16:9' (1280x720)
    """
    target_res = RES_9_16 if aspect_ratio == "9:16" else RES_16_9
    w, h = target_res

    # 1. Background image
    if background_path and os.path.exists(background_path):
        try:
            bg = Image.open(background_path).convert("RGB")
            # Aspect crop
            bw, bh = bg.size
            scale = max(w / bw, h / bh)
            nw, nh = int(bw * scale), int(bh * scale)
            bg = bg.resize((nw, nh), Image.LANCZOS)
            x_crop = (nw - w) // 2
            y_crop = (nh - h) // 2
            bg = bg.crop((x_crop, y_crop, x_crop + w, y_crop + h))
        except Exception:
            bg = Image.new("RGB", target_res, (20, 24, 38))
    else:
        bg = Image.new("RGB", target_res, (20, 24, 38))

    # 2. Gradient overlay for contrast
    bg = _apply_gradient_overlay(bg, aspect_ratio)
    draw = ImageDraw.Draw(bg)

    # 3. Dynamic font sizing
    base_font_size = 84 if aspect_ratio == "9:16" else 72
    font = _find_bold_font(base_font_size)
    max_w = int(w * 0.88)

    clean_title = title.strip()
    lines = _wrap_text(draw, clean_title, font, max_w)

    # If too many lines or too tall, shrink font
    if len(lines) > 3:
        base_font_size = int(base_font_size * 0.82)
        font = _find_bold_font(base_font_size)
        lines = _wrap_text(draw, clean_title, font, max_w)

    line_height = int(base_font_size * 1.25)
    total_text_h = len(lines) * line_height

    # Position: lower third (around 62-75% down)
    start_y = int(h * 0.64) if aspect_ratio == "9:16" else int(h * 0.58)

    # 4. Render lines with drop shadow and word-level accent colors
    for line_idx, line in enumerate(lines):
        y = start_y + (line_idx * line_height)
        words = line.split()

        # Compute full line width
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_w = line_bbox[2] - line_bbox[0]
        start_x = (w - line_w) // 2

        curr_x = start_x
        for word in words:
            word_str = word + " "
            word_bbox = draw.textbbox((0, 0), word_str, font=font)
            word_w = word_bbox[2] - word_bbox[0]

            # Determine color
            fill_color = COLOR_YELLOW if _is_accent_word(word) else COLOR_WHITE
            if accent_text and accent_text.lower() in word.lower():
                fill_color = COLOR_YELLOW

            # 4-Directional Drop Shadow for 3D POP
            shadow_dist = 4
            for dx, dy in [(-shadow_dist, 0), (shadow_dist, 0), (0, -shadow_dist), (0, shadow_dist), (shadow_dist, shadow_dist)]:
                draw.text((curr_x + dx, y + dy), word_str, fill=(0, 0, 0), font=font)

            # Main text
            draw.text((curr_x, y), word_str, fill=fill_color, font=font)
            curr_x += word_w

    # 5. Save output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    bg.save(output_path, "JPEG", quality=95)
    return output_path
