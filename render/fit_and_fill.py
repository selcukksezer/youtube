"""
render/fit_and_fill.py — Fit-and-Fill Gaussian/Boxblur Landscape-to-Vertical Compositor.

Adapted and evolved from reference_repos2/dramaclaw (src/novelvideo/generators/video_composer.py).
Converts landscape (16:9) or arbitrary aspect ratio assets into vertical 9:16 (1080x1920):
- Background: Scaled to fill canvas and heavily blurred (boxblur=25:5).
- Foreground: Scaled to fit horizontally without distortion, centered cleanly.
Eliminates ugly black letterboxing without cropping out vital content.
"""

from __future__ import annotations

from typing import Optional


def build_fit_and_fill_blur_filter(
    input_label: str = "[0:v]",
    output_label: str = "[vout]",
    target_width: int = 1080,
    target_height: int = 1920,
    blur_strength: int = 25,
    blur_power: int = 5,
) -> str:
    """
    Builds a single-pass FFmpeg filter_complex snippet:
    1. Splits input into foreground and background streams.
    2. Background: scale to fill 1080x1920, crop to boundary, apply boxblur.
    3. Foreground: scale to fit width 1080 maintaining aspect ratio.
    4. Overlays foreground centered over blurred background.
    """
    fg_label = "[fg_raw]"
    bg_label = "[bg_raw]"
    bg_blurred = "[bg_blur]"
    fg_scaled = "[fg_fit]"

    return (
        f"{input_label}split=2{fg_label}{bg_label};"
        f"{bg_label}scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
        f"crop={target_width}:{target_height},"
        f"boxblur={blur_strength}:{blur_power}{bg_blurred};"
        f"{fg_label}scale={target_width}:-1:force_original_aspect_ratio=decrease{fg_scaled};"
        f"{bg_blurred}{fg_scaled}overlay=(W-w)/2:(H-h)/2{output_label}"
    )


def is_landscape_aspect_ratio(width: int, height: int) -> bool:
    """Returns True if the media width is greater than its height."""
    if width <= 0 or height <= 0:
        return False
    return width > height
