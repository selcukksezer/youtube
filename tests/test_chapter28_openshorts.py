"""
Unit and Integration tests for Chapter 28.6 (openshorts adaptations):
- render.encoding_optimizer (get_encoder_args, METADATA_SCRUB, LOUDNORM_FILTER, strip_unsupported_emojis, truncate_bytes, is_cornered_inset)
- Verifies NVENC cq ≈ crf + 7, yuv420p enforcement, metadata scrub, tofu-box emoji stripping, and corner inset tracking.
"""

import pytest
from render.encoding_optimizer import (
    get_encoder_args,
    QUALITY,
    QUALITY_FAST,
    DELIVERY,
    METADATA_SCRUB,
    LOUDNORM_FILTER,
    strip_unsupported_emojis,
    truncate_bytes,
    is_cornered_inset,
    get_nearest_corner,
)


def test_encoder_quality_tiers_and_nvenc_cq():
    """Verify NVENC cq ≈ crf + 7 and mandatory yuv420p color space."""
    # Delivery tier: x264 CRF 22 vs NVENC CQ 29
    x264_del = get_encoder_args("libx264", DELIVERY)
    assert "-crf" in x264_del and "22" in x264_del
    assert "-pix_fmt" in x264_del and "yuv420p" in x264_del

    nvenc_del = get_encoder_args("h264_nvenc", DELIVERY)
    assert "-cq" in nvenc_del and "29" in nvenc_del
    assert "-pix_fmt" in nvenc_del and "yuv420p" in nvenc_del  # Mandatory to prevent gbrp magenta/green mess

    # Quality tier: x264 CRF 18 vs NVENC CQ 25
    x264_qual = get_encoder_args("libx264", QUALITY)
    assert "-crf" in x264_qual and "18" in x264_qual

    nvenc_qual = get_encoder_args("h264_nvenc", QUALITY)
    assert "-cq" in nvenc_qual and "25" in nvenc_qual
    assert "-spatial-aq" in nvenc_qual and "1" in nvenc_qual


def test_metadata_scrub_and_loudnorm_spec():
    """Verify metadata scrubbing flags and platform EBU R128 loudness filter."""
    assert "-map_metadata" in METADATA_SCRUB
    assert "-map_chapters" in METADATA_SCRUB
    assert "-map_metadata:s:v" in METADATA_SCRUB
    assert "-map_metadata:s:a" in METADATA_SCRUB

    # AAC inter-sample peak prevention (TP=-2.0 instead of -1.5)
    assert "TP=-2.0" in LOUDNORM_FILTER
    assert "I=-14" in LOUDNORM_FILTER


def test_strip_unsupported_emojis_tofu_prevention():
    """Verify removal of emoji codepoints that would render as tofu boxes in ASS subtitles."""
    raw = "🔥 Bu inanılmaz bir sır! 😱 Kesinlikle izleyin! 🚀✨"
    cleaned = strip_unsupported_emojis(raw)
    assert cleaned == "Bu inanılmaz bir sır! Kesinlikle izleyin!"
    assert "🔥" not in cleaned
    assert "😱" not in cleaned
    assert "🚀" not in cleaned


def test_multi_byte_safe_truncation():
    """Verify byte budget truncation without breaking multi-byte UTF-8 sequences."""
    turkish_text = "Şampiyonlar ligi ve muhteşem zafer"
    # "Ş" is 2 bytes in UTF-8
    truncated = truncate_bytes(turkish_text, 10)
    assert len(truncated.encode("utf-8")) <= 10
    # Must decode cleanly without replacement error
    assert isinstance(truncated, str)
    assert turkish_text.startswith(truncated)


def test_cornered_inset_detection():
    """Verify webcam inset tracking logic from camera_inset.py."""
    frame_w = 1920
    frame_h = 1080

    # 1. Bounding box in bottom-right corner (typical OBS webcam)
    # x=1500, y=750, w=350, h=250 -> small and off-center
    webcam_box = (1500, 750, 350, 250)
    assert is_cornered_inset(webcam_box, frame_w, frame_h) is True
    h_side, v_side = get_nearest_corner(webcam_box, frame_w, frame_h)
    assert (h_side, v_side) == ("right", "bottom")

    # 2. Main presenter filling the center shot (not an inset)
    # x=600, y=200, w=720, h=700 -> centered and large
    presenter_box = (600, 200, 720, 700)
    assert is_cornered_inset(presenter_box, frame_w, frame_h) is False
