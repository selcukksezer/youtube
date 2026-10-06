"""P3 acceptance for the MoviePy final merge: shared card, timing and cleanup."""
from pathlib import Path
import subprocess
import wave
from unittest.mock import Mock

import numpy as np
import pytest
from PIL import Image

from effects import hook_card
import video_composer as composer


def _configure_merge(monkeypatch, *, safe_mode=True):
    monkeypatch.setattr(composer.config, "USE_GPU_ACCELERATION", False)
    monkeypatch.setattr(composer.config, "RENDER_SAFE_MODE", safe_mode)
    monkeypatch.setattr(composer.config, "get_target_resolution", lambda: (180, 320))
    monkeypatch.setattr(composer, "get_color_grading_ffmpeg_filter", lambda **kwargs: "null")
    monkeypatch.setattr(composer, "get_unsharp_filter", lambda **kwargs: "null")
    monkeypatch.setattr(composer, "get_ffmpeg_static_grain_filter", lambda: "null")
    monkeypatch.setattr(composer, "get_ffmpeg_vignette_filter", lambda **kwargs: "null")


def _media_paths(tmp_path, subtitle_kind="none"):
    video, audio = tmp_path / "picture.mp4", tmp_path / "voice.wav"
    ass, srt, out = tmp_path / "captions.ass", tmp_path / "captions.srt", tmp_path / "final.mp4"
    video.touch()
    audio.touch()
    if subtitle_kind == "ass":
        ass.write_text("[Script Info]\n" + "; test subtitle\n" * 8, encoding="utf-8")
    elif subtitle_kind == "srt":
        srt.write_text("1\n00:00:00,000 --> 00:00:03,200\nA spoken sentence.\n", encoding="utf-8")
    return video, audio, ass, srt, out


def _solid_card(text, width, path):
    Image.new("RGBA", (width, 50), (255, 0, 0, 255)).save(path)
    return path


@pytest.mark.parametrize("subtitle_kind", ["ass", "srt", "none"])
@pytest.mark.parametrize("safe_mode", [True, False])
def test_card_joins_existing_merge_after_subtitles(tmp_path, monkeypatch, subtitle_kind, safe_mode):
    _configure_merge(monkeypatch, safe_mode=safe_mode)
    paths = _media_paths(tmp_path, subtitle_kind)
    commands = []
    render_card = Mock(side_effect=_solid_card)
    monkeypatch.setattr(hook_card, "create_hook_image", render_card)

    def encode(command, **kwargs):
        commands.append(command)
        assert Path(command[command.index("-loop") + 5]).is_file()
        paths[-1].write_bytes(b"encoded")
        return subprocess.CompletedProcess(command, 0, stderr=b"")

    monkeypatch.setattr(composer.subprocess, "run", encode)
    assert composer._merge(*(str(p) for p in paths), style_opts={"hook_card_text": "First sentence! 🔥"})
    assert len(commands) == 1, "Card must use the existing merge encode"
    graph = commands[0][commands[0].index("-filter_complex") + 1]
    assert "[hook_base][hook_image]overlay=" in graph
    if subtitle_kind == "ass":
        assert graph.index("ass=captions.ass") < graph.index("overlay=")
    elif subtitle_kind == "srt":
        assert graph.index("subtitles=captions.srt") < graph.index("overlay=")
    assert "enable='lt(t,2.5)'" in graph
    assert "eof_action=pass:repeatlast=0" in graph
    assert render_card.call_args.args[:2] == ("First sentence! 🔥", 180)
    assert not Path(render_card.call_args.args[2]).exists()


@pytest.mark.parametrize("options", [
    {"hook_card_text": "First sentence", "disable_hook_card": True},
    {"hook_card_text": ""},
    {"hook_card_text": "   "},
])
def test_disabled_or_empty_hook_keeps_original_merge(tmp_path, monkeypatch, options):
    _configure_merge(monkeypatch)
    paths = _media_paths(tmp_path, "srt")
    render_card = Mock(side_effect=AssertionError("Disabled card must not render"))
    monkeypatch.setattr(hook_card, "create_hook_image", render_card)
    commands = []

    def encode(command, **kwargs):
        commands.append(command)
        paths[-1].write_bytes(b"encoded")
        return subprocess.CompletedProcess(command, 0, stderr=b"")

    monkeypatch.setattr(composer.subprocess, "run", encode)
    assert composer._merge(*(str(p) for p in paths), style_opts=options)
    assert len(commands) == 1
    assert commands[0].count("-i") == 2
    assert "-vf" in commands[0]
    assert "-filter_complex" not in commands[0]
    render_card.assert_not_called()
    assert not list(tmp_path.glob("hook_card_*.png"))


def test_subtitle_fallbacks_keep_card_and_remove_temp(tmp_path, monkeypatch):
    _configure_merge(monkeypatch)
    paths = _media_paths(tmp_path, "ass")
    paths[3].write_text("1\n00:00:00,000 --> 00:00:03,200\nFallback.\n", encoding="utf-8")
    monkeypatch.setattr(hook_card, "create_hook_image", _solid_card)
    graphs = []

    def encode(command, **kwargs):
        graphs.append(command[command.index("-filter_complex") + 1])
        success = len(graphs) == 3
        if success:
            paths[-1].write_bytes(b"encoded")
        return subprocess.CompletedProcess(command, 0 if success else 1, stderr=b"Unsupported subtitle")

    monkeypatch.setattr(composer.subprocess, "run", encode)
    assert composer._merge(*(str(p) for p in paths), style_opts={"hook_card_text": "Keep the hook"})
    assert len(graphs) == 3
    assert "ass=captions.ass" in graphs[0]
    assert "subtitles=captions.srt" in graphs[1]
    assert all("overlay=" in graph for graph in graphs)
    assert not list(tmp_path.glob("hook_card_*.png"))


def test_failed_merge_removes_hook_temp(tmp_path, monkeypatch):
    _configure_merge(monkeypatch)
    paths = _media_paths(tmp_path)
    monkeypatch.setattr(hook_card, "create_hook_image", _solid_card)
    monkeypatch.setattr(composer.subprocess, "run", Mock(side_effect=OSError("Encoder unavailable")))
    with pytest.raises(OSError, match="Encoder unavailable"):
        composer._merge(*(str(p) for p in paths), style_opts={"hook_card_text": "Temporary hook"})
    assert not list(tmp_path.glob("hook_card_*.png"))


def test_real_merge_hook_ends_at_2_5_and_preserves_duration(tmp_path, monkeypatch):
    _configure_merge(monkeypatch)
    video, audio, ass, srt, out = _media_paths(tmp_path)
    monkeypatch.setattr(hook_card, "create_hook_image", _solid_card)
    ffmpeg = composer.imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([
        ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i",
        "color=c=blue:s=180x320:r=10:d=3.2", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", str(video),
    ], check=True, capture_output=True, timeout=30)
    with wave.open(str(audio), "wb") as voice:
        voice.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        voice.writeframes(b"\0\0" * 51200)
    assert composer._merge(
        str(video), str(audio), str(ass), str(srt), str(out),
        style_opts={"hook_card_text": "Visible only before 2.5"},
    )
    decoded = subprocess.run([
        ffmpeg, "-v", "error", "-i", str(out), "-an",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ], check=True, capture_output=True, timeout=30)
    frames = np.frombuffer(decoded.stdout, dtype=np.uint8).reshape((-1, 320, 180, 3))
    assert len(frames) == 32, "Card must neither prepend a clip nor truncate at PNG EOF"
    assert frames[24, 30, 90, 0] > 200, "Card must still show at 2.4 seconds"
    assert frames[24, 30, 90, 2] < 30
    assert frames[25, 30, 90, 2] > 200, "Card must disappear at 2.5 seconds"
    assert frames[25, 30, 90, 0] < 30
    assert frames[-1, 30, 90, 2] > 200
    assert not list(tmp_path.glob("hook_card_*.png"))
