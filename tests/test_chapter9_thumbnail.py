"""
Unit tests for Chapter 9.4: Otomatik Kucuk Resim (Thumbnail) Sentezleyici
Testing:
- format_3_word_hook_title (extracts punchy 3-word title, removes stop words)
- get_niche_thumbnail_palette (returns valid RGB tuples for all niches)
- synthesize_shorts_thumbnail (creates 1080x1920 thumb_9x16.jpg with gradient + typography)
- extract_highest_contrast_frame (graceful fallback/error on invalid video)
"""

import os
import pytest
from PIL import Image

from services.thumbnail_generator import (
    format_3_word_hook_title,
    get_niche_thumbnail_palette,
    synthesize_shorts_thumbnail,
    extract_highest_contrast_frame,
    ThumbnailGenerator,
    generate_thumbnail
)


def test_format_3_word_hook_title_basic():
    text = "Dunyayi Degistiren 5 Buyuk Sir Ve Gercekler"
    hook = format_3_word_hook_title(text)
    words = hook.split()
    assert len(words) <= 3
    assert hook.isupper()
    # Stop-word "ve" should be excluded
    assert "VE" not in words


def test_format_3_word_hook_title_fallback():
    empty_hook = format_3_word_hook_title("")
    assert len(empty_hook.split()) <= 3
    assert empty_hook.isupper()

    one_word = format_3_word_hook_title("Inanilmaz")
    assert one_word == "INANILMAZ"


def test_get_niche_thumbnail_palette():
    niches = ["finance", "horror", "history", "tech", "affiliate", "unknown_niche"]
    for niche in niches:
        palette = get_niche_thumbnail_palette(niche)
        assert "primary" in palette
        assert "secondary" in palette
        assert "accent" in palette
        assert "bg_dark" in palette
        for key in ["primary", "secondary", "accent", "bg_dark"]:
            assert isinstance(palette[key], tuple)
            assert len(palette[key]) == 3


def test_synthesize_shorts_thumbnail_dry_run(tmp_path):
    output_dir = tmp_path / "thumb_test"
    thumb_path = synthesize_shorts_thumbnail(
        video_path="dummy.mp4",
        hook_text="Kripto Parada Son Durum",
        niche="finance",
        output_dir=str(output_dir),
        dry_run=True
    )
    assert os.path.exists(thumb_path)
    assert os.path.basename(thumb_path) == "thumb_9x16.jpg"

    # Verify image dimensions
    with Image.open(thumb_path) as img:
        assert img.size == (1080, 1920)
        assert img.format in ("JPEG", "MPO")

    # File size should be substantial (> 5KB)
    assert os.path.getsize(thumb_path) > 5000


def test_thumbnail_generator_class_wrapper(tmp_path):
    gen = ThumbnailGenerator()
    out = gen.generate(
        video_path="non_existent.mp4",
        hook_text="Yapay Zeka Gelisimi",
        niche="tech",
        output_dir=str(tmp_path),
        dry_run=True
    )
    assert os.path.exists(out)


def test_extract_highest_contrast_frame_nonexistent():
    # Should safely return None on missing file without crashing
    res = extract_highest_contrast_frame("non_existent_file_xyz_123.mp4")
    assert res is None
