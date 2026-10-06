"""P3 image acceptance: actual color pixels, emoji clusters and safe layout."""
from pathlib import Path
from unittest.mock import patch

import pytest
from types import SimpleNamespace
from PIL import Image, ImageChops, ImageFont

from effects import hook_card


def test_emoji_sequences_stay_out_of_text_font():
    samples = ["👨‍👩‍👧‍👦", "🇹🇷", "1️⃣", "👍🏽", "❤️"]
    for emoji in samples:
        runs = hook_card._split_emoji_runs("Önce " + emoji + " sonra")
        assert "".join(chunk for is_emoji, chunk in runs if is_emoji) == emoji
        assert "".join(chunk for is_emoji, chunk in runs if not is_emoji) == "Önce  sonra"


def test_color_emoji_reaches_rgba_pixels(tmp_path):
    if not any(Path(path).is_file() for path in hook_card._EMOJI_FONTS):
        pytest.skip("No system emoji font installed")
    path = tmp_path / "color.png"
    hook_card.create_hook_image("🔥🚀", 1080, str(path))
    with Image.open(path) as image:
        colored = sum(1 for r, g, b, a in image.getdata() if a > 200 and max(r, g, b) - min(r, g, b) > 60)
    assert colored > 100, "Emoji must have real color, not white glyphs"


def test_missing_emoji_font_does_not_leave_blank_space(tmp_path):
    with patch.object(hook_card, "_EMOJI_FONTS", ()):
        first, second = tmp_path / "with.png", tmp_path / "plain.png"
        hook_card.create_hook_image("Bunu 🔥 öğren", 540, str(first))
        hook_card.create_hook_image("Bunu öğren", 540, str(second))
        with Image.open(first) as a, Image.open(second) as b:
            assert a.size == b.size
            assert ImageChops.difference(a, b).getbbox() is None
        assert hook_card.create_hook_image("🔥🚀", 540, str(tmp_path / "empty.png")) == ""


def test_missing_all_font_files_keeps_turkish_text(tmp_path):
    with patch.object(hook_card, "_EMOJI_FONTS", ()), patch.object(hook_card, "_TEXT_FONTS", ()):
        out = tmp_path / "fallback.png"
        assert hook_card.create_hook_image("Şaşırtıcı bir gerçek: güç değişir! 🔥", 540, str(out)) == str(out)
        assert out.stat().st_size > 300


def test_bitmap_emoji_font_uses_supported_strike():
    fake_font = object()
    def load(path, size):
        if size != 109:
            raise OSError("invalid pixel size")
        return fake_font
    with patch.object(hook_card, "_EMOJI_FONTS", ("bitmap.ttf",)), patch.object(hook_card.os.path, "isfile", return_value=True), patch.object(ImageFont, "truetype", side_effect=load):
        font, native = hook_card._load_emoji_font(32)
    assert font is fake_font
    assert native == 109


def test_long_hook_wraps_instead_of_clipping(tmp_path):
    short, long = tmp_path / "short.png", tmp_path / "long.png"
    hook_card.create_hook_image("Kısa soru?", 540, str(short))
    hook_card.create_hook_image("Bugün öğrendiğin bu şaşırtıcı bilgi hayatındaki bütün kararları neden tamamen değiştirebilir? 🔥", 540, str(long))
    with Image.open(short) as a, Image.open(long) as b:
        assert a.width == b.width == 540
        assert b.height > a.height, "Long narration must use more than one line"
        assert b.height < 270, "Hook must stay in the top safe area"


@pytest.mark.parametrize("first", [
    {"narration": "Bunu biliyor musun? 🔥 İkinci cümle.", "text": "Eski içerik"},
    SimpleNamespace(narration="Bunu biliyor musun? 🔥 İkinci cümle."),
])
def test_first_scene_narration_beats_legacy_text_and_ends_at_sentence(first):
    assert hook_card.first_scene_hook([first]) == "Bunu biliyor musun? 🔥"


def test_hook_override_and_missing_narration():
    assert hook_card.first_scene_hook([], " Özel  metin! ") == "Özel metin!"
    assert hook_card.first_scene_hook([{"title": "Metadata"}]) == ""
    assert hook_card.first_scene_hook([{"narration": "3.14 sayısı ilginçtir. Devam."}]) == "3.14 sayısı ilginçtir."


def test_wrap_preserves_words_and_emoji_clusters():
    assert hook_card._wrap_lines("abc def ghi", len, 7) == ["abc def", "ghi"]
    assert hook_card._wrap_lines("abcdefghi jkl", len, 5) == ["abcde", "fghi", "jkl"]
    assert hook_card._split_emoji_clusters("a👨‍👩‍👧‍👦b") == ["a", "👨‍👩‍👧‍👦", "b"]
    assert hook_card._wrap_lines("abc def ghi jkl mno", len, 4, max_lines=3) == ["abc", "def", "ghi…"]
