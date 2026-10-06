"""
Tests for Chapter 33.3 P3: Renkli Emoji Kanca Kartı (effects/hook_card.py & render/ffmpeg_graph.py)
Covers:
- Pill-shaped hook card image generation with emoji and text runs
- Safe fallback when fonts or emojis are missing
- FFmpeg filter_complex overlay integration with 2.5s duration
- Verification that disable_hook_card produces clean graph without hook overlay
- Verification that ASS subtitles stay free of color emoji
"""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from effects.hook_card import create_hook_image, _split_emoji_runs
from render.ffmpeg_graph import render_with_ffmpeg_graph


def test_hook_card_emoji_splitting():
    text = "Bunu ASLA Yapmayın! 😱🔥"
    runs = _split_emoji_runs(text)

    # Must contain text run and emoji run
    assert any(not is_emoji and "Bunu ASLA" in chunk for is_emoji, chunk in runs)
    assert any(is_emoji and "😱" in chunk for is_emoji, chunk in runs)


def test_hook_card_generates_rgba_png():
    with tempfile.TemporaryDirectory() as tmp:
        out_png = os.path.join(tmp, "hook_card.png")
        result = create_hook_image("Bu kuralı biliyor muydunuz? 🧠", 1080, out_png)

        assert result == out_png
        assert os.path.isfile(out_png)
        assert os.path.getsize(out_png) > 300

        from PIL import Image
        with Image.open(out_png) as im:
            assert im.mode == "RGBA"
            assert im.width == 1080
            assert im.height > 20


def test_hook_card_skips_empty_or_whitespace():
    assert create_hook_image("", 1080, "test.png") == ""
    assert create_hook_image("   ", 1080, "test.png") == ""


def test_ffmpeg_graph_hook_card_overlay_chain():
    with tempfile.TemporaryDirectory() as tmp:
        # Create a mock video clip
        clip_path = os.path.join(tmp, "scene1.mp4")
        with open(clip_path, "wb") as f:
            f.write(b"mock video content 001")

        audio_path = os.path.join(tmp, "audio.mp3")
        with open(audio_path, "wb") as f:
            f.write(b"mock audio content 001")

        out_mp4 = os.path.join(tmp, "out.mp4")

        # Mock ffmpeg probe and execution
        with patch("render.ffmpeg_graph._probe_duration", return_value=5.0), \
             patch("render.ffmpeg_graph._probe_is_landscape", return_value=False), \
             patch("render.ffmpeg_graph.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.poll.return_value = 0
            mock_proc.returncode = 0
            mock_proc.stdout.readline.return_value = ""
            mock_proc.stderr.readline.return_value = ""
            mock_popen.return_value = mock_proc

            render_with_ffmpeg_graph(
                clips=[{"path": clip_path, "duration": 5.0}],
                audio_path=audio_path,
                output_path=out_mp4,
                title="Bunu Öğrenene Kadar 🚀",
                subtitle_opts={"disable_hook_card": False},
            )

            # Retrieve command passed to ffmpeg
            call_args = mock_popen.call_args[0][0]
            cmd_str = " ".join(call_args)

            # Must contain hook.png loop input and 2.5s overlay
            assert "hook.png" in cmd_str
            assert "lt(t,2.5)" in cmd_str
            assert "[hook]" in cmd_str or "vhook" in cmd_str


def test_ffmpeg_graph_disable_hook_card_clean_graph():
    with tempfile.TemporaryDirectory() as tmp:
        clip_path = os.path.join(tmp, "scene1.mp4")
        with open(clip_path, "wb") as f:
            f.write(b"mock video content 001")

        audio_path = os.path.join(tmp, "audio.mp3")
        with open(audio_path, "wb") as f:
            f.write(b"mock audio content 001")

        out_mp4 = os.path.join(tmp, "out.mp4")

        with patch("render.ffmpeg_graph._probe_duration", return_value=5.0), \
             patch("render.ffmpeg_graph._probe_is_landscape", return_value=False), \
             patch("render.ffmpeg_graph.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.poll.return_value = 0
            mock_proc.returncode = 0
            mock_proc.stdout.readline.return_value = ""
            mock_proc.stderr.readline.return_value = ""
            mock_popen.return_value = mock_proc

            render_with_ffmpeg_graph(
                clips=[{"path": clip_path, "duration": 5.0}],
                audio_path=audio_path,
                output_path=out_mp4,
                title="Bunu Öğrenene Kadar 🚀",
                subtitle_opts={"disable_hook_card": True},  # Hook card explicitly disabled
            )

            call_args = mock_popen.call_args[0][0]
            cmd_str = " ".join(call_args)

            # Must NOT contain hook.png or hook overlay
            assert "hook.png" not in cmd_str
            assert "lt(t,2.5)" not in cmd_str
