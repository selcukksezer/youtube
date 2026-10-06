"""
render/encoding_optimizer.py — Encoder Quality Tiers, Metadata Scrub,
Emoji Sanitization & Multi-Byte Safe Truncation.

Adapted and evolved from reference_repos/openshorts (ffmpeg_utils.py, hooks.py, camera_inset.py).
Implements Plan Section 28.6 & Section 3.4/4.5.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple


# ─── ENCODER QUALITY TIERS & NVENC CQ CALIBRATION (openshorts pattern) ──────
# Benchmarked: NVENC cq ≈ crf + 7 produces equivalent file size with VBR + spatial AQ.
QUALITY = "quality"            # Master archival: x264 crf 18 / nvenc cq 25
QUALITY_FAST = "quality_fast"  # Fast export: x264 crf 18 / nvenc cq 25 p4
DELIVERY = "delivery"          # YouTube Shorts delivery: x264 crf 22 / nvenc cq 29

_X264_ARGS: Dict[str, List[str]] = {
    QUALITY: ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"],
    QUALITY_FAST: ["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p"],
    DELIVERY: ["-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p"],
}

# -pix_fmt yuv420p is REQUIRED: with RGB/BGR input nvenc otherwise emits H.264
# in gbrp colorspace, causing web players to render green/magenta distortion.
_NVENC_ARGS: Dict[str, List[str]] = {
    QUALITY: [
        "-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq",
        "-rc", "vbr", "-cq", "25", "-b:v", "0",
        "-spatial-aq", "1", "-temporal-aq", "1", "-pix_fmt", "yuv420p",
    ],
    QUALITY_FAST: [
        "-c:v", "h264_nvenc", "-preset", "p4", "-tune", "hq",
        "-rc", "vbr", "-cq", "25", "-b:v", "0", "-spatial-aq", "1",
        "-pix_fmt", "yuv420p",
    ],
    DELIVERY: [
        "-c:v", "h264_nvenc", "-preset", "p4",
        "-rc", "vbr", "-cq", "29", "-b:v", "0", "-spatial-aq", "1",
        "-pix_fmt", "yuv420p",
    ],
}

# Per-stream metadata scrub to eliminate inherited YouTube/Google handler headers
METADATA_SCRUB: List[str] = [
    "-map_metadata", "-1",
    "-map_chapters", "-1",
    "-map_metadata:s:v", "-1",
    "-map_metadata:s:a", "-1",
]

# EBU R128 loudness filter with -2.0 dBTP headroom to prevent AAC inter-sample clipping
LOUDNORM_FILTER: str = "loudnorm=I=-14:TP=-2.0:LRA=11"


def get_encoder_args(
    encoder_name: str = "libx264",
    tier: str = DELIVERY,
) -> List[str]:
    """Returns validated encoder arguments for x264 or NVENC."""
    tier = tier if tier in _X264_ARGS else DELIVERY
    if "nvenc" in encoder_name.lower():
        return list(_NVENC_ARGS.get(tier, _NVENC_ARGS[DELIVERY]))
    return list(_X264_ARGS.get(tier, _X264_ARGS[DELIVERY]))


# ─── EMOJI SANITIZATION & MULTI-BYTE UTF-8 TRUNCATION (hooks.py pattern) ─────
# Codepoint ranges without glyph support in standard subtitle fonts (prevents tofu boxes)
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"  # emoticons, symbols, transport
    "\U00002600-\U000027BF"  # misc symbols, dingbats
    "\U0001F1E6-\U0001F1FF"  # flags
    "\U00002B00-\U00002BFF"  # arrows, stars
    "\U0000FE0E\U0000FE0F"   # variation selectors
    "\U0000200D"             # zero-width joiner
    "\U000020E3"             # combining keycap
    "]+"
)


def strip_unsupported_emojis(text: str) -> str:
    """Removes unsupported emoji codepoints that would produce tofu boxes in ASS/FFmpeg."""
    if not text:
        return ""
    cleaned = _EMOJI_RE.sub("", text)
    # Clean up duplicate whitespace left by removed emojis
    return re.sub(r" +", " ", cleaned).strip()


def truncate_bytes(text: str, max_bytes: int) -> str:
    """
    Trims string to a byte budget without splitting multi-byte UTF-8 sequences.
    Prevents corrupt Unicode decode errors on database and overlay layers.
    """
    if not text or max_bytes <= 0:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", "ignore")


# ─── CAMERA INSET & WEBCAM CORNER TRACKING (camera_inset.py pattern) ────────
def is_cornered_inset(
    box: Tuple[int, int, int, int],
    frame_w: int,
    frame_h: int,
    max_subject_height: float = 0.38,
    min_offset: float = 0.18,
    margin: float = 0.20,
) -> bool:
    """
    Determines if a bounding box (x, y, w, h) represents a screen recording
    webcam inset rather than a centered presenter in the main shot.
    """
    x, y, w, h = box
    if h > frame_h * max_subject_height:
        return False

    cx = (x + w / 2.0) / float(frame_w)
    off_centre = abs(cx - 0.5) >= min_offset

    near_edge = (
        x <= frame_w * margin
        or (x + w) >= frame_w * (1.0 - margin)
        or y <= frame_h * margin
        or (y + h) >= frame_h * (1.0 - margin)
    )
    return off_centre and near_edge


def get_nearest_corner(
    box: Tuple[int, int, int, int],
    frame_w: int,
    frame_h: int,
) -> Tuple[str, str]:
    """Returns horizontal and vertical corner location: e.g. ('right', 'bottom')."""
    cx = box[0] + box[2] / 2.0
    cy = box[1] + box[3] / 2.0
    h_side = "left" if cx < frame_w / 2.0 else "right"
    v_side = "top" if cy < frame_h / 2.0 else "bottom"
    return h_side, v_side
