"""Render a mixed text and color emoji hook card as a transparent PNG."""
from __future__ import annotations

import os
import re
from typing import List, Optional, Sequence, Tuple

_EMOJI_FONTS = (
    r"C:\Windows\Fonts\seguiemj.ttf",
    "/mnt/c/Windows/Fonts/seguiemj.ttf",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto-emoji/NotoColorEmoji.ttf",
)
_EMOJI_BITMAP_SIZES = (109, 128, 136, 160, 96, 72, 64, 32)
_TEXT_FONTS = (
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def first_scene_hook(scenes, override=None) -> str:
    """Resolve the opening sentence from the final narration, never metadata."""
    if isinstance(override, str) and override.strip():
        return " ".join(override.split())
    if not scenes:
        return ""
    first = scenes[0]
    for field in ("narration", "text", "narrative"):
        value = first.get(field) if isinstance(first, dict) else getattr(first, field, None)
        if isinstance(value, str) and value.strip():
            text = " ".join(value.split())
            boundary = re.search(r"[.!?…]+[\"”’']*(?=\s|$)", text)
            if not boundary:
                return text
            sentence = text[:boundary.end()]
            # An emoji after punctuation still belongs to that sentence.
            for token in text[boundary.end():].split():
                if all(is_emoji for is_emoji, _ in _split_emoji_runs(token)):
                    sentence += " " + token
                else:
                    break
            return sentence
    return ""


def hook_overlay_filter(base_label: str, hook_label: str, output_label: str, height: int) -> str:
    """Both render paths show the same card without extending the timeline."""
    return (
        f"[{base_label}][{hook_label}]overlay=x=(W-w)/2:y={round(height * 0.0375)}:"
        f"enable='lt(t,2.5)':eof_action=pass:repeatlast=0[{output_label}]"
    )

def _is_emoji_base(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x1F000 <= cp <= 0x1FAFF
        or 0x1F1E6 <= cp <= 0x1F1FF
        or 0x2600 <= cp <= 0x27BF
        or 0x2300 <= cp <= 0x23FF
        or 0x2B00 <= cp <= 0x2BFF
        or 0x2190 <= cp <= 0x21FF
        or cp in {0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139, 0x24C2, 0x3030, 0x303D, 0x3297, 0x3299}
    )


def _is_emoji_cluster_start(text: str, index: int) -> bool:
    if index >= len(text):
        return False
    ch = text[index]
    if ch in "0123456789#*":
        j = index + 1
        if j < len(text) and ord(text[j]) == 0xFE0F:
            j += 1
        return j < len(text) and ord(text[j]) == 0x20E3
    return _is_emoji_base(ch)


def _consume_emoji_cluster(text: str, index: int) -> int:
    i = index
    if text[i] in "0123456789#*":
        i += 1
        if i < len(text) and ord(text[i]) == 0xFE0F:
            i += 1
        if i < len(text) and ord(text[i]) == 0x20E3:
            return i + 1
        return index
    regional = 0x1F1E6 <= ord(text[i]) <= 0x1F1FF
    i += 1
    if regional and i < len(text) and 0x1F1E6 <= ord(text[i]) <= 0x1F1FF:
        i += 1
    while i < len(text):
        cp = ord(text[i])
        if cp in (0xFE0E, 0xFE0F, 0x20E3) or 0x1F3FB <= cp <= 0x1F3FF:
            i += 1
            continue
        if cp == 0x200D and i + 1 < len(text) and _is_emoji_cluster_start(text, i + 1):
            i = _consume_emoji_cluster(text, i + 1)
            continue
        break
    return i


def _split_emoji_runs(text: str) -> List[Tuple[bool, str]]:
    runs: List[Tuple[bool, str]] = []
    plain: List[str] = []
    emoji: List[str] = []

    def flush_plain() -> None:
        if plain:
            runs.append((False, "".join(plain)))
            plain.clear()

    def flush_emoji() -> None:
        if emoji:
            runs.append((True, "".join(emoji)))
            emoji.clear()

    i = 0
    while i < len(text):
        if _is_emoji_cluster_start(text, i):
            flush_plain()
            end = _consume_emoji_cluster(text, i)
            if end == i:
                plain.append(text[i])
                i += 1
            else:
                emoji.append(text[i:end])
                i = end
        else:
            flush_emoji()
            plain.append(text[i])
            i += 1
    flush_plain()
    flush_emoji()
    return runs or [(False, text)]


def _strip_emoji(text: str) -> str:
    return " ".join("".join(chunk for is_emoji, chunk in _split_emoji_runs(text) if not is_emoji).split())


def _load_font(paths: Sequence[str], size: int):
    from PIL import ImageFont
    for path in paths:
        if path and os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=max(12, int(size)))
    except TypeError:
        return ImageFont.load_default()


def _load_emoji_font(size: int):
    from PIL import ImageFont
    for path in _EMOJI_FONTS:
        if not path or not os.path.isfile(path):
            continue
        try:
            return ImageFont.truetype(path, size=int(size)), None
        except Exception:
            pass
        for native_size in _EMOJI_BITMAP_SIZES:
            try:
                return ImageFont.truetype(path, size=native_size), native_size
            except Exception:
                continue
    return None, None


def _font_bbox(draw, text: str, font) -> Tuple[int, int, int, int]:
    try:
        return draw.textbbox((0, 0), text, font=font)
    except Exception:
        return (0, 0, int(len(text) * 0.55 * getattr(font, "size", 32)), int(getattr(font, "size", 32)))


def _measure_text(draw, text: str, font) -> float:
    if not text:
        return 0.0
    try:
        return float(draw.textlength(text, font=font))
    except Exception:
        box = _font_bbox(draw, text, font)
        return float(box[2] - box[0])


def _render_emoji_chunk(chunk: str, emoji_font, requested_size: int, native_size: Optional[int]):
    from PIL import Image, ImageDraw
    scale = float(requested_size) / float(native_size) if native_size else 1.0
    render_size = int(native_size or requested_size)
    probe = Image.new("RGBA", (render_size * 8, render_size * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    bbox = _font_bbox(draw, chunk, emoji_font)
    pad = max(4, render_size // 8)
    canvas = Image.new("RGBA", (max(8, bbox[2] - bbox[0] + pad * 2), max(8, bbox[3] - bbox[1] + pad * 2)), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(canvas)
    xy = (pad - bbox[0], pad - bbox[1])
    try:
        cdraw.text(xy, chunk, font=emoji_font, embedded_color=True, fill=(255, 255, 255, 255))
    except TypeError:
        cdraw.text(xy, chunk, font=emoji_font, fill=(255, 255, 255, 255))
    if scale != 1.0:
        canvas = canvas.resize((max(1, int(canvas.width * scale)), max(1, int(canvas.height * scale))), Image.Resampling.LANCZOS)
    return canvas


def _split_emoji_clusters(text: str) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(text):
        if _is_emoji_cluster_start(text, i):
            end = _consume_emoji_cluster(text, i)
            if end > i:
                out.append(text[i:end])
                i = end
                continue
        out.append(text[i])
        i += 1
    return out


def _wrap_lines(text, measure, max_width, max_lines=3):
    """Wrap at spaces; split only oversized words, preserving emoji clusters."""
    lines, current = [], ""
    for word in text.split():
        candidate = (current + " " + word).strip()
        if measure(candidate) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        for cluster in _split_emoji_clusters(word):
            if current and measure(current + cluster) > max_width:
                lines.append(current)
                current = ""
            current += cluster
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        clusters = _split_emoji_clusters(lines[-1])
        while clusters and measure("".join(clusters).rstrip() + "…") > max_width:
            clusters.pop()
        lines[-1] = "".join(clusters).rstrip() + "…"
    return lines


def create_hook_image(text: str, target_width: int, output_path: str) -> str:
    """Write a color emoji hook card and return output_path, or empty string."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return ""
    raw = " ".join((text or "").split())
    if len(raw) < 2:
        return ""
    width = max(320, int(target_width))
    font_size = max(28, min(64, int(width * 0.045)))
    text_font = _load_font(_TEXT_FONTS, font_size)
    emoji_font, native_size = _load_emoji_font(font_size)
    if emoji_font is None:
        raw = _strip_emoji(raw)
        if len(raw) < 2:
            return ""
    probe = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    emoji_cache = {}

    def emoji_image(chunk: str):
        if emoji_font is None:
            return None
        if chunk not in emoji_cache:
            emoji_cache[chunk] = _render_emoji_chunk(chunk, emoji_font, font_size, native_size)
        return emoji_cache[chunk]

    def measure(is_emoji: bool, chunk: str) -> float:
        if is_emoji:
            image = emoji_image(chunk)
            return float(image.width if image else 0)
        return _measure_text(draw, chunk, text_font)

    def measure_line(line):
        return sum(measure(is_emoji, chunk) for is_emoji, chunk in _split_emoji_runs(line))

    pad_x = max(18, int(font_size * 0.7))
    max_inner = width - 40 - pad_x * 2
    lines = _wrap_lines(raw, measure_line, max_inner)
    if not lines:
        return ""
    line_widths = [measure_line(line) for line in lines]
    pad_y = max(12, int(font_size * 0.4))
    ascent, descent = text_font.getmetrics() if hasattr(text_font, "getmetrics") else (font_size, 0)
    emoji_height = max((image.height for image in emoji_cache.values()), default=0)
    line_h = max(font_size + 4, int(ascent + descent), emoji_height)
    card_w = min(width - 40, max(font_size * 3, int(max(line_widths) + 1) + pad_x * 2))
    card_h = line_h * len(lines) + pad_y * 2
    img = Image.new("RGBA", (width, card_h + 8), (0, 0, 0, 0))
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(card)
    cdraw.rounded_rectangle((0, 0, card_w - 1, card_h - 1), radius=max(10, card_h // 5), fill=(8, 10, 16, 222))
    for row, line in enumerate(lines):
        x = max(pad_x, (card_w - int(line_widths[row])) // 2)
        y = pad_y + row * line_h
        for is_emoji, token in _split_emoji_runs(line):
            if is_emoji:
                emoji = emoji_image(token)
                if emoji is not None:
                    card.alpha_composite(emoji, (int(x), int(y + max(0, line_h - emoji.height) // 2)))
                x += measure(True, token)
            else:
                cdraw.text((int(x), int(y)), token, font=text_font, fill=(255, 255, 255, 255))
                x += measure(False, token)
    img.alpha_composite(card, (max(0, (width - card_w) // 2), 4))
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
