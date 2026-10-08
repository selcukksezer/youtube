"""
Whiteboard / Sketch Animation Service (FFmpeg & PIL).
Simulates hand-drawn whiteboard animations:
1. High-contrast line-art vector sketches via Pollinations Flux or PIL edge detection.
2. Offline 100% reliable procedural whiteboard generator with domain-specific doodles
   (Islamic/Hadith, Finance, Ideas, Tech, etc.) and handwritten concepts.
3. Animates whiteboard drawing reveal with animated dry-erase marker hand overlay
   moving along the reveal boundary with drawing oscillation, then exiting canvas.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import tempfile
from typing import Optional
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageFont
import config


WHITEBOARD_TRANSITIONS = ["wipeleft", "wiperight", "wipedown", "radial"]
MARKER_HAND_PATH = os.path.join(config.BASE_DIR, "assets", "whiteboard", "marker_hand.png")


def ensure_marker_hand_asset() -> str:
    """Ensure the dry-erase marker hand PNG asset exists, generating if needed."""
    os.makedirs(os.path.dirname(MARKER_HAND_PATH), exist_ok=True)
    if os.path.exists(MARKER_HAND_PATH) and os.path.getsize(MARKER_HAND_PATH) > 1000:
        return MARKER_HAND_PATH

    width, height = 240, 360
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Arm & Wrist (Skin tone)
    skin_color = (235, 195, 165, 255)
    skin_shadow = (210, 165, 135, 255)
    outline = (40, 30, 25, 255)

    # Arm polygon extending to bottom right
    arm_poly = [(110, 220), (width + 20, 280), (width + 20, height + 20), (90, height + 20)]
    draw.polygon(arm_poly, fill=skin_shadow, outline=outline)

    # Hand palm & base
    draw.ellipse([90, 150, 200, 260], fill=skin_color, outline=outline, width=3)

    # 2. Marker Body / Barrel (Sleek dark dry-erase marker)
    marker_body = [(35, 45), (135, 185), (105, 205), (15, 65)]
    draw.polygon(marker_body, fill=(35, 40, 45, 255), outline=(15, 15, 20, 255))
    # Marker label stripe
    draw.polygon([(45, 60), (60, 80), (45, 90), (30, 70)], fill=(37, 99, 235, 255))

    # Marker Collar / Cone
    cone = [(15, 65), (35, 45), (20, 28), (8, 42)]
    draw.polygon(cone, fill=(120, 125, 130, 255), outline=(20, 20, 25, 255))

    # Marker Chisel Tip (Black ink) - Tip at (10, 12)
    tip = [(8, 42), (20, 28), (10, 12), (4, 22)]
    draw.polygon(tip, fill=(10, 10, 10, 255), outline=(0, 0, 0, 255))

    # 3. Fingers gripping marker
    draw.ellipse([80, 130, 130, 175], fill=skin_color, outline=outline, width=3)
    draw.ellipse([65, 105, 115, 150], fill=skin_color, outline=outline, width=3)
    draw.ellipse([95, 150, 145, 195], fill=skin_color, outline=outline, width=3)
    draw.ellipse([120, 180, 165, 225], fill=skin_color, outline=outline, width=3)
    draw.ellipse([140, 210, 180, 250], fill=skin_color, outline=outline, width=3)

    # Crease accents
    draw.arc([75, 115, 105, 140], start=30, end=150, fill=outline, width=2)
    draw.arc([90, 140, 120, 165], start=30, end=150, fill=outline, width=2)

    img.save(MARKER_HAND_PATH, "PNG")
    return MARKER_HAND_PATH


def convert_image_to_sketch(input_image_path: str, output_sketch_path: str) -> bool:
    """Convert any photo/image into a clean black-and-white whiteboard sketch."""
    if not os.path.exists(input_image_path):
        return False
    try:
        img = Image.open(input_image_path).convert("L")  # Grayscale
        edges = img.filter(ImageFilter.FIND_EDGES)
        inverted = ImageOps.invert(edges)
        threshold = 210
        sketch = inverted.point(lambda p: 255 if p > threshold else int(p * 0.4))
        sketch = sketch.convert("RGB")
        os.makedirs(os.path.dirname(os.path.abspath(output_sketch_path)), exist_ok=True)
        sketch.save(output_sketch_path, "JPEG", quality=90)
        return True
    except Exception as e:
        print(f"  [Whiteboard] Sketch conversion error: {e}")
        return False


def draw_procedural_whiteboard_sketch(
    prompt: str,
    output_path: str,
    width: int = 540,
    height: int = 960,
    scene_index: int = 0,
) -> bool:
    """
    Offline 100% reliable procedural whiteboard generator with domain-specific doodles
    and hand-drawn layout. NEVER produces a blank canvas.
    """
    try:
        img = Image.new("RGB", (width, height), (252, 252, 254))
        draw = ImageDraw.Draw(img)

        # 1. Subtle dry-erase whiteboard border & corner brackets
        draw.rectangle([12, 12, width - 12, height - 12], outline=(226, 232, 240), width=3)
        draw.line([(12, 36), (12, 12), (36, 12)], fill=(148, 163, 184), width=4)
        draw.line([(width - 36, 12), (width - 12, 12), (width - 12, 36)], fill=(148, 163, 184), width=4)
        draw.line([(12, height - 36), (12, height - 12), (36, height - 12)], fill=(148, 163, 184), width=4)
        draw.line([(width - 36, height - 12), (width - 12, height - 12), (width - 12, height - 36)], fill=(148, 163, 184), width=4)

        ink_color = (20, 25, 40)
        accent_ink = (29, 78, 216)
        highlight_yellow = (254, 240, 138)

        # Load fonts
        font_large, font_mid, font_sm = None, None, None
        font_paths = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    font_large = ImageFont.truetype(fp, 32)
                    font_mid = ImageFont.truetype(fp, 24)
                    font_sm = ImageFont.truetype(fp, 18)
                    break
                except Exception:
                    pass

        # 2. Extract title & concepts from prompt / narration
        clean_text = re.sub(r"[^\w\s-]", " ", prompt or "")
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        words = clean_text.split()
        title_words = words[:4] if words else ["ÖNEMLİ", "BİLGİ"]
        clean_title = " ".join(title_words).upper()
        clean_sub = " ".join(words[4:10]).capitalize() if len(words) > 4 else ""

        # Title highlighter doodle box
        title_y = 190
        draw.polygon(
            [(50, title_y - 20), (width - 50, title_y - 25), (width - 45, title_y + 35), (55, title_y + 40)],
            fill=highlight_yellow,
        )
        draw.text((width // 2, title_y + 5), clean_title, fill=ink_color, font=font_large, anchor="mm")
        if clean_sub:
            draw.text((width // 2, title_y + 60), clean_sub, fill=accent_ink, font=font_mid, anchor="mm")

        # 3. Domain-specific Hand-Drawn Doodle Icon in center
        p_lower = prompt.lower()
        cx, cy = width // 2, 420

        if any(k in p_lower for k in ("hadis", "ayet", "dua", "allah", "peygamber", "islam", "din", "kuran", "namaz", "cennet")):
            # Islamic / Hadith: Open Holy Book / Rahle with Crescent Star
            draw.arc([cx - 90, cy - 50, cx, cy + 20], start=200, end=350, fill=ink_color, width=4)
            draw.arc([cx, cy - 50, cx + 90, cy + 20], start=190, end=340, fill=ink_color, width=4)
            draw.line([(cx - 85, cy - 5), (cx - 85, cy + 45)], fill=ink_color, width=4)
            draw.line([(cx + 85, cy - 5), (cx + 85, cy + 45)], fill=ink_color, width=4)
            draw.line([(cx, cy - 10), (cx, cy + 55)], fill=ink_color, width=4)
            draw.arc([cx - 90, cy, cx, cy + 70], start=200, end=350, fill=ink_color, width=4)
            draw.arc([cx, cy, cx + 90, cy + 70], start=190, end=340, fill=ink_color, width=4)
            # Stand legs
            draw.line([(cx - 70, cy + 45), (cx + 60, cy + 105)], fill=ink_color, width=4)
            draw.line([(cx + 70, cy + 45), (cx - 60, cy + 105)], fill=ink_color, width=4)
            # Crescent star
            draw.arc([cx - 35, cy - 130, cx + 15, cy - 80], start=45, end=315, fill=accent_ink, width=4)
            draw.arc([cx - 25, cy - 126, cx + 15, cy - 84], start=45, end=315, fill=(252, 252, 254), width=4)
            draw.ellipse([cx + 15, cy - 108, cx + 23, cy - 100], fill=accent_ink)
        elif any(k in p_lower for k in ("para", "zengin", "milyon", "dolar", "kazan", "is", "finans", "yatirim", "satis")):
            # Finance / Growth Bar Chart & Arrow
            draw.line([(cx - 110, cy + 60), (cx + 110, cy + 60)], fill=ink_color, width=4)
            draw.line([(cx - 110, cy + 60), (cx - 110, cy - 70)], fill=ink_color, width=4)
            draw.rectangle([cx - 85, cy + 15, cx - 60, cy + 60], outline=ink_color, width=3)
            draw.rectangle([cx - 40, cy - 15, cx - 15, cy + 60], outline=ink_color, width=3)
            draw.rectangle([cx + 5, cy - 45, cx + 30, cy + 60], fill=(219, 234, 254), outline=accent_ink, width=3)
            draw.line([(cx - 95, cy + 30), (cx - 25, cy), (cx + 25, cy - 55), (cx + 80, cy - 90)], fill=accent_ink, width=5)
            draw.polygon([(cx + 85, cy - 95), (cx + 60, cy - 90), (cx + 75, cy - 65)], fill=accent_ink)
        elif any(k in p_lower for k in ("bilgi", "beyin", "akil", "fikir", "ogren", "arastirma", "bilim", "sir")):
            # Idea Lightbulb with Rays
            draw.arc([cx - 55, cy - 100, cx + 55, cy + 10], start=140, end=400, fill=accent_ink, width=4)
            draw.line([(cx - 40, cy - 15), (cx - 28, cy + 40)], fill=accent_ink, width=4)
            draw.line([(cx + 40, cy - 15), (cx + 28, cy + 40)], fill=accent_ink, width=4)
            draw.rectangle([cx - 28, cy + 40, cx + 28, cy + 65], outline=ink_color, width=3)
            draw.line([(cx - 18, cy - 25), (cx, cy - 55), (cx + 18, cy - 25)], fill=ink_color, width=3)
            draw.line([(cx, cy - 125), (cx, cy - 110)], fill=accent_ink, width=4)
            draw.line([(cx - 75, cy - 85), (cx - 60, cy - 70)], fill=accent_ink, width=4)
            draw.line([(cx + 75, cy - 85), (cx + 60, cy - 70)], fill=accent_ink, width=4)
        elif any(k in p_lower for k in ("kalp", "ask", "saglik", "sevgi", "iliski", "ruh")):
            # Heart with Pulse Wave
            draw.arc([cx - 70, cy - 80, cx, cy - 10], start=180, end=360, fill=(225, 29, 72), width=5)
            draw.arc([cx, cy - 80, cx + 70, cy - 10], start=180, end=360, fill=(225, 29, 72), width=5)
            draw.line([(cx - 70, cy - 45), (cx, cy + 45)], fill=(225, 29, 72), width=5)
            draw.line([(cx + 70, cy - 45), (cx, cy + 45)], fill=(225, 29, 72), width=5)
            draw.line([(cx - 110, cy), (cx - 50, cy), (cx - 25, cy - 50), (cx, cy + 30), (cx + 25, cy - 30), (cx + 50, cy), (cx + 110, cy)], fill=ink_color, width=4)
        else:
            # Versatile Checklist Target / Bulletin Pin
            draw.ellipse([cx - 70, cy - 80, cx + 70, cy + 60], outline=accent_ink, width=4)
            draw.line([(cx - 30, cy - 10), (cx - 10, cy + 15), (cx + 35, cy - 35)], fill=ink_color, width=6)

        # 4. Whiteboard Bullet Points / Sketch Notes
        y_bullets = 580
        bullet_items = [
            f"Sahne #{scene_index + 1} Detay Çizimi",
            "Kinetik Kalem & Çizim Akışı",
            "Önemli Vurgular & Mealler",
        ]
        for b in bullet_items:
            # Bullet checkbox doodle
            draw.rectangle([65, y_bullets - 5, 85, y_bullets + 15], outline=accent_ink, width=2)
            draw.line([(68, y_bullets + 5), (75, y_bullets + 13), (88, y_bullets - 8)], fill=accent_ink, width=3)
            draw.text((100, y_bullets + 5), b, fill=ink_color, font=font_mid, anchor="lm")
            y_bullets += 48

        # Decorative doodle underline
        draw.arc([width // 2 - 120, y_bullets + 15, width // 2 + 120, y_bullets + 55], start=10, end=170, fill=accent_ink, width=3)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path, "JPEG", quality=92)
        return True
    except Exception as e:
        print(f"  [Whiteboard] Procedural sketch error: {e}")
        return False


def generate_whiteboard_sketch_image(prompt: str, output_path: str, width: int = 540, height: int = 960) -> bool:
    """
    Generate a clean black-and-white line art sketch.
    Attempts Pollinations Flux AI; converts to clean line art.
    Returns False on failure/offline.
    """
    from services.pollinations_ai_visual import generate_ai_image, pollinations_circuit_open
    if pollinations_circuit_open():
        return False

    sketch_prompt = (
        f"clean black and white line art vector sketch on plain white background, "
        f"{prompt}, minimalist drawing, clear contours, no colors, no shading, vertical 9:16"
    )
    with tempfile.NamedTemporaryFile(suffix="_raw.jpg", delete=False) as tmp:
        raw_tmp = tmp.name

    try:
        ok = generate_ai_image(sketch_prompt, raw_tmp, width=width, height=height, timeout=10)
        if ok and os.path.exists(raw_tmp) and os.path.getsize(raw_tmp) > 1000:
            converted = convert_image_to_sketch(raw_tmp, output_path)
            return converted
        return False
    finally:
        if os.path.exists(raw_tmp):
            try:
                os.remove(raw_tmp)
            except OSError:
                pass


def animate_whiteboard_clip(
    sketch_image_path: str,
    output_video_path: str,
    duration: float = 4.0,
    width: int = 540,
    height: int = 960,
    transition_style: str = "wipeleft",
) -> bool:
    """
    Renders whiteboard video clip:
    1. Whiteboard canvas wipes into the sketch image.
    2. Real marker hand overlays on the wipe boundary with natural drawing oscillation.
    3. Hand slides off-canvas cleanly once drawing finishes.
    """
    if not os.path.exists(sketch_image_path):
        return False

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    hand_path = ensure_marker_hand_asset()

    draw_dur = min(2.5, max(1.2, duration * 0.55))
    start_offset = 0.15
    end_offset = start_offset + draw_dur

    # Hand overlay math:
    # During [start_offset, end_offset], hand's marker tip stays glued to the wipe boundary.
    # Hand dimensions: scale to 180x270 (tip is near top-left of hand image)
    # Oscillation frequency: 18 rad/s, amplitude: 35px
    wipe_x_expr = f"(t - {start_offset:.2f}) / {draw_dur:.2f} * {width * 0.92:.1f} - 15"
    slide_out_x = f"{width * 0.92:.1f} + (t - {end_offset:.2f}) * 650"
    slide_out_y = f"320 + (t - {end_offset:.2f}) * 750"

    x_hand = f"if(lt(t,{start_offset:.2f}), -250, if(lt(t,{end_offset:.2f}), {wipe_x_expr}, {slide_out_x}))"
    y_hand = f"if(lt(t,{start_offset:.2f}), 340, if(lt(t,{end_offset:.2f}), 320 + 35*sin(18*t), {slide_out_y}))"

    filter_complex = (
        f"[0:v]scale={width}:{height},setsar=1[bg];"
        f"[1:v]scale={width}:{height},setsar=1[fg];"
        f"[bg][fg]xfade=transition=wipeleft:duration={draw_dur:.2f}:offset={start_offset:.2f},setsar=1[wiped];"
        f"[2:v]scale=180:270[hand];"
        f"[wiped][hand]overlay=x='{x_hand}':y='{y_hand}':enable='between(t,{start_offset * 0.8:.2f},{end_offset + 0.6:.2f})'[final]"
    )

    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"color=c=#FCFCFE:s={width}x{height}:d={duration:.2f}",
        "-loop", "1", "-i", sketch_image_path,
        "-loop", "1", "-i", hand_path,
        "-filter_complex", filter_complex,
        "-map", "[final]",
        "-t", f"{duration:.2f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        output_video_path,
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=40)
        return res.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 1000
    except Exception as e:
        print(f"  [Whiteboard] Video render error: {e}")
        return False


def create_whiteboard_scene_clip(
    scene_description: str,
    output_video_path: str,
    duration: float = 4.0,
    scene_index: int = 0,
) -> Optional[str]:
    """
    1-shot helper to create a whiteboard drawing video clip for a scene.
    AI sketch only. When generation fails (rate limit, offline) returns None so the
    caller falls back to real stock footage; no synthetic placeholder is produced.
    """
    trans = WHITEBOARD_TRANSITIONS[scene_index % len(WHITEBOARD_TRANSITIONS)]
    with tempfile.NamedTemporaryFile(suffix="_sketch.jpg", delete=False) as tmp:
        tmp_sketch = tmp.name

    try:
        ok_sketch = generate_whiteboard_sketch_image(scene_description, tmp_sketch)
        if not ok_sketch:
            return None

        ok_clip = animate_whiteboard_clip(
            sketch_image_path=tmp_sketch,
            output_video_path=output_video_path,
            duration=duration,
            transition_style=trans,
        )
        return output_video_path if ok_clip else None
    finally:
        if os.path.exists(tmp_sketch):
            try:
                os.remove(tmp_sketch)
            except OSError:
                pass
