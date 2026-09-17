"""Renders an attributed Reddit research post preview as a vertical MP4."""
import os
import subprocess
import tempfile
import textwrap

import imageio_ffmpeg


def generate_reddit_post_card_clip(post: dict, output_path: str, duration: float = 4.0) -> str:
    """Renders an attributed Reddit post preview card as a vertical video clip."""
    from PIL import Image, ImageDraw, ImageFont

    image_path = tempfile.mktemp(suffix="_reddit_post.png")
    try:
        image = Image.new("RGB", (1080, 1920), "#15141b")
        draw = ImageDraw.Draw(image)
        def _get_font(font_name, size):
            candidates = [
                font_name,
                f"C:/Windows/Fonts/{font_name}.ttf",
                f"C:/Windows/Fonts/{font_name.lower()}.ttf",
                f"/System/Library/Fonts/Supplemental/{font_name}.ttf",
                "arial.ttf",
                "Arial.ttf"
            ]
            for c in candidates:
                try:
                    return ImageFont.truetype(c, size)
                except Exception:
                    pass
            return ImageFont.load_default()

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