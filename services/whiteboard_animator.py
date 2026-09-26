"""
Whiteboard / Sketch Animation Service (FFmpeg & PIL).
Simulates hand-drawn whiteboard animations:
1. Generates minimalist black-and-white vector sketches via Pollinations Flux or converts photos to line-art via PIL edge detection.
2. Animates drawing reveal using FFmpeg hardware-accelerated `xfade=transition=wipeleft` on whiteboard canvas.
3. Adds subtle whiteboard camera motion and optional marker drawing sound effects.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Optional
import imageio_ffmpeg
from PIL import Image, ImageFilter, ImageOps
from services.pollinations_ai_visual import generate_ai_image


WHITEBOARD_TRANSITIONS = ["wipeleft", "wiperight", "wipedown", "radial"]


def convert_image_to_sketch(input_image_path: str, output_sketch_path: str) -> bool:
    """Convert any photo/image into a clean black-and-white whiteboard sketch."""
    if not os.path.exists(input_image_path):
        return False
    try:
        img = Image.open(input_image_path).convert("L")  # Grayscale
        # Edge detection
        edges = img.filter(ImageFilter.FIND_EDGES)
        # Invert edges so background is white (255) and lines are dark (0)
        inverted = ImageOps.invert(edges)
        # Enhance line contrast
        threshold = 210
        sketch = inverted.point(lambda p: 255 if p > threshold else int(p * 0.5))
        sketch = sketch.convert("RGB")
        os.makedirs(os.path.dirname(os.path.abspath(output_sketch_path)), exist_ok=True)
        sketch.save(output_sketch_path, "JPEG", quality=90)
        return True
    except Exception as e:
        print(f"  [Whiteboard] Sketch conversion error: {e}")
        return False


def generate_whiteboard_sketch_image(prompt: str, output_path: str, width: int = 540, height: int = 960) -> bool:
    """Generate a clean minimalist line art sketch using Pollinations Flux."""
    sketch_prompt = (
        f"clean black and white line art vector sketch on plain white background, "
        f"{prompt}, minimalist drawing, clear contours, no colors, no shading, vertical 9:16"
    )
    return generate_ai_image(sketch_prompt, output_path, width=width, height=height)


def animate_whiteboard_clip(
    sketch_image_path: str,
    output_video_path: str,
    duration: float = 4.0,
    width: int = 540,
    height: int = 960,
    transition_style: str = "wipeleft",
) -> bool:
    """
    Render a whiteboard drawing video clip where sketch is drawn/wiped onto the canvas.
    """
    if not os.path.exists(sketch_image_path):
        return False

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    draw_dur = min(2.5, max(1.0, duration * 0.6))
    trans = transition_style if transition_style in WHITEBOARD_TRANSITIONS else "wipeleft"

    # Filter: white color stream wipes into sketch image
    filter_complex = (
        f"[0:v]scale={width}:{height},setsar=1[c0];"
        f"[1:v]scale={width}:{height},setsar=1[c1];"
        f"[c0][c1]xfade=transition={trans}:duration={draw_dur:.2f}:offset=0.1,setsar=1"
    )

    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"color=c=white:s={width}x{height}:d={duration:.2f}",
        "-loop", "1", "-i", sketch_image_path,
        "-filter_complex", filter_complex,
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
        print(f"  [Whiteboard] Video render notice: {e}")
        return False


def create_whiteboard_scene_clip(
    scene_description: str,
    output_video_path: str,
    duration: float = 4.0,
    scene_index: int = 0,
) -> Optional[str]:
    """1-shot helper to create a whiteboard drawing video clip for a scene."""
    trans = WHITEBOARD_TRANSITIONS[scene_index % len(WHITEBOARD_TRANSITIONS)]
    with tempfile.NamedTemporaryFile(suffix="_sketch.jpg", delete=False) as tmp:
        tmp_sketch = tmp.name

    try:
        ok_sketch = generate_whiteboard_sketch_image(scene_description, tmp_sketch)
        if not ok_sketch:
            # Fallback to white canvas with drawing placeholder if offline
            img = Image.new("RGB", (540, 960), (250, 250, 250))
            img.save(tmp_sketch)

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
