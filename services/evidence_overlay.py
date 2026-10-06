"""
Evidence Overlay and Research Badge Generator
Inspired by reference_repos/ai-content-studio research pipeline.
Generates transparent, safe-zone compliant research evidence badges and
FFmpeg overlay filter strings for verified news, science, and fact-checking shorts.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageFont


class EvidenceBadgeGenerator:
    """
    Produces transparent verification badges showing verified information sources
    (e.g., "[✓ KAYNAK: bbc.com]" or "[✓ VERIFIED: nasa.gov]").
    Renders either as a semi-transparent PNG badge or an FFmpeg drawbox/drawtext filter chain.
    """

    DEFAULT_WIDTH = 480
    DEFAULT_HEIGHT = 70
    BG_COLOR = (15, 23, 42, 200)  # Dark slate blue with ~78% opacity
    BORDER_COLOR = (56, 189, 248, 230)  # Cyan border accent
    CHECK_COLOR = (34, 197, 94, 255)  # Emerald green check
    TEXT_COLOR = (248, 250, 252, 255)  # Off-white

    @staticmethod
    def extract_clean_domain(url_or_domain: str) -> str:
        """Cleans and extracts readable root/subdomain from raw URL or domain text."""
        raw = str(url_or_domain).strip()
        if not raw:
            return "Doğrulanmış Kaynak"

        if not raw.startswith(("http://", "https://")):
            raw = f"https://{raw}"

        try:
            parsed = urlparse(raw)
            domain = parsed.netloc or parsed.path
            domain = re.sub(r"^www\.", "", domain)
            domain = domain.split(":")[0].strip("/")
            return domain if domain else "Doğrulanmış Kaynak"
        except Exception:
            return "Doğrulanmış Kaynak"

    @classmethod
    def generate_badge_png(
        cls,
        source_domain: str,
        output_png_path: str,
        label: str = "KAYNAK",
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ) -> str:
        """
        Creates a semi-transparent PNG with rounded corners, verification glyph,
        and clean typography.
        """
        clean_domain = cls.extract_clean_domain(source_domain)
        badge_text = f"{label}: {clean_domain}"

        # Create transparent RGBA image
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Rounded rectangle background
        radius = 16
        draw.rounded_rectangle(
            [(2, 2), (width - 3, height - 3)],
            radius=radius,
            fill=cls.BG_COLOR,
            outline=cls.BORDER_COLOR,
            width=2,
        )

        # Draw checkmark badge [✓]
        check_x = 20
        check_y = height // 2 - 12
        draw.text((check_x, check_y), "✓", fill=cls.CHECK_COLOR, font=None)

        # Draw main text
        text_x = 42
        text_y = height // 2 - 8
        draw.text((text_x, text_y), badge_text, fill=cls.TEXT_COLOR, font=None)

        os.makedirs(os.path.dirname(os.path.abspath(output_png_path)), exist_ok=True)
        img.save(output_png_path, "PNG")
        return output_png_path

    @classmethod
    def build_ffmpeg_overlay_filter(
        cls,
        input_label: str,
        badge_input_label: str,
        output_label: str,
        start_time: float = 1.0,
        end_time: float = 5.5,
        margin_x: int = 40,
        margin_y: int = 140,
        position: str = "top_left",
    ) -> str:
        """
        Constructs an FFmpeg overlay filter snippet with enable='between(t,start,end)'.
        Respects Shorts UI top/bottom safe zones.
        Positions: 'top_left', 'top_right', 'bottom_left', 'bottom_right'.
        """
        if position == "top_right":
            x_expr = f"W-w-{margin_x}"
            y_expr = f"{margin_y}"
        elif position == "bottom_left":
            x_expr = f"{margin_x}"
            y_expr = f"H-h-{margin_y}"
        elif position == "bottom_right":
            x_expr = f"W-w-{margin_x}"
            y_expr = f"H-h-{margin_y}"
        else:  # top_left default
            x_expr = f"{margin_x}"
            y_expr = f"{margin_y}"

        return (
            f"[{input_label}][{badge_input_label}]overlay="
            f"x={x_expr}:y={y_expr}:"
            f"enable='between(t,{start_time:.2f},{end_time:.2f})'[{output_label}]"
        )
