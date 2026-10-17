from __future__ import annotations

from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont


# Problem #48: Dedicated Twitter/X Card Transparent PNG & FFmpeg Filter Renderer
def generate_transparent_twitter_card_png(
    output_path: str | Path,
    author_name: str = "Finans & Gündem",
    author_handle: str = "@gundem_analiz",
    tweet_text: str = "Son dakika: Piyasalarda kritik seviye test ediliyor.",
    verified: bool = True,
    width: int = 920,
    height: int = 340,
) -> str:
    """Renders a high-DPI dark-mode Twitter/X post card onto a transparent RGBA PNG."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded dark card background
    card_bg = (15, 20, 28, 235)
    border_col = (56, 68, 77, 255)
    draw.rounded_rectangle([(8, 8), (width - 8, height - 8)], radius=28, fill=card_bg, outline=border_col, width=3)

    # Avatar circle
    draw.ellipse([(36, 36), (108, 108)], fill=(29, 155, 240, 255))
    font = ImageFont.load_default()

    # Header & Handle
    badge = " ✓" if verified else ""
    draw.text((128, 44), f"{author_name}{badge}", fill=(255, 255, 255, 255), font=font)
    draw.text((128, 72), author_handle, fill=(139, 152, 165, 255), font=font)

    # Body text wrapping
    words = (tweet_text or "").split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        if len(" ".join(cur + [w])) <= 58:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))

    y = 132
    for line in lines[:5]:
        draw.text((40, y), line, fill=(231, 233, 234, 255), font=font)
        y += 32

    img.save(str(out), format="PNG")
    return str(out)


def build_twitter_card_ffmpeg_filter(
    card_png_path: str,
    start_sec: float = 0.5,
    end_sec: float = 4.5,
    y_expr: str = "H*0.18",
) -> dict[str, Any]:
    """Returns FFmpeg overlay filter specification for a Twitter/X breaking card."""
    return {
        "input_path": str(card_png_path),
        "filter_expr": f"overlay=(W-w)/2:{y_expr}:enable='between(t,{start_sec:.2f},{end_sec:.2f})'",
        "start_sec": start_sec,
        "end_sec": end_sec,
    }
