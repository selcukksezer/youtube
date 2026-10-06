"""P3 physical proof: native graph keeps the hook above ASS until 2.5s."""
from pathlib import Path
import subprocess
import wave

import numpy as np
from PIL import Image

from effects import hook_card
from render import ffmpeg_graph as graph
import system_resilience


def _write_overlapping_ass(path):
    # Solid green ASS drawing occupies the same pixels as the red PNG card.
    slash = chr(92)
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 180\nPlayResY: 320\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,20,&H0000FF00,&H0000FF00,&H0000FF00,&H00000000,"
        "0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        f"Dialogue: 0,0:00:00.00,0:00:03.20,Default,,0,0,0,,{{{slash}an7{slash}pos(0,12){slash}p1}}m 0 0 l 180 0 180 50 0 50"
        "\n",
        encoding="utf-8",
    )


def _decode_frames(ffmpeg, path):
    decoded = subprocess.run([
        ffmpeg, "-v", "error", "-i", str(path), "-an",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ], check=True, capture_output=True, timeout=30)
    return np.frombuffer(decoded.stdout, dtype=np.uint8).reshape((-1, 320, 180, 3))


def test_native_card_above_ass_has_exact_endpoint_and_keeps_original_duration(tmp_path, monkeypatch):
    monkeypatch.setattr(graph.config, "get_target_resolution", lambda: (180, 320))
    monkeypatch.setattr(graph.config, "RENDER_SAFE_MODE", True)
    monkeypatch.setattr(graph.config, "USE_GPU_ACCELERATION", False)
    monkeypatch.setattr(graph.config, "FPS_DIVERSIFY", False)
    monkeypatch.setattr(graph.config, "FPS", 10)
    monkeypatch.setattr(graph.config, "FFMPEG_THREADS", 2)
    monkeypatch.setattr(graph, "get_look_filters", lambda *args, **kwargs: "null")
    monkeypatch.setattr(graph, "face_cover_crop_x", lambda *args, **kwargs: None)
    monkeypatch.setattr(system_resilience, "get_encoder_fallback_chain", lambda *args: [
        (["-c:v", "libx264", "-preset", "ultrafast", "-crf", "0"], "P3 test CPU"),
    ])
    from anti_detect import post_render
    monkeypatch.setattr(post_render, "apply_post_render_humanization", lambda *args, **kwargs: {})

    video, audio = tmp_path / "source.mp4", tmp_path / "voice.wav"
    ass = tmp_path / "overlap.ass"
    _write_overlapping_ass(ass)
    ffmpeg = graph.imageio_ffmpeg.get_ffmpeg_exe()
    # Deterministic moving pixels exceed the existing 100 KB output guard at this
    # small size; otherwise a valid short solid-color video is rejected by it.
    pixels = np.random.default_rng(3).integers(0, 256, (32, 320, 180, 3), dtype=np.uint8)
    subprocess.run([
        ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s:v", "180x320", "-r", "10", "-i", "pipe:0", "-an",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "0",
        "-pix_fmt", "yuv420p", str(video),
    ], input=pixels.tobytes(), check=True, capture_output=True, timeout=30)
    with wave.open(str(audio), "wb") as voice:
        voice.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        voice.writeframes(b"\0\0" * 51200)

    card_paths, card_texts, render_commands = [], [], []
    def draw_card(text, width, path):
        card_paths.append(Path(path))
        card_texts.append(text)
        Image.new("RGBA", (width, 50), (255, 0, 0, 255)).save(path)
        return path
    monkeypatch.setattr(hook_card, "create_hook_image", draw_card)
    real_popen = subprocess.Popen
    def record_render(command, *args, **kwargs):
        if "-filter_complex" in command:
            render_commands.append(command)
        return real_popen(command, *args, **kwargs)
    monkeypatch.setattr(graph.subprocess, "Popen", record_render)

    outputs = {}
    for enabled in (True, False):
        destination = tmp_path / ("hook_on.mp4" if enabled else "hook_off.mp4")
        result = graph.render_with_ffmpeg_graph(
            [{"path": str(video), "duration": 3.2, "fit_and_fill": False}],
            str(audio), str(destination), title="Video metadata title",
            subtitle_opts={"hook_card_text": "First spoken sentence! 🔥", "disable_hook_card": not enabled},
            ass_path=str(ass), anti_duplicate=False, enable_ken_burns=False,
        )
        assert result == str(destination), "Physical graph encode must succeed"
        outputs[enabled] = _decode_frames(ffmpeg, destination)

    assert len(render_commands) == 2, "One native graph encode per on/off render"
    assert render_commands[0].count("-i") == 3
    assert render_commands[1].count("-i") == 2
    on_graph = render_commands[0][render_commands[0].index("-filter_complex") + 1]
    off_graph = render_commands[1][render_commands[1].index("-filter_complex") + 1]
    assert on_graph.index("subtitles=") < on_graph.index("overlay=")
    assert "overlay=" not in off_graph
    assert "hook.png" not in " ".join(render_commands[1])
    assert card_texts == ["First spoken sentence! 🔥"]
    assert all(not path.exists() for path in card_paths)

    for frames in outputs.values():
        assert len(frames) == 32, "PNG must not prepend, truncate, or extend the 3.2-second video"
    for index in (5, 24):
        r, g, b = outputs[True][index, 30, 90]
        assert r > 180 and g < 80 and b < 80, f"Red PNG must cover green ASS at {index / 10}s"
    for index in (25, 30, 31):
        r, g, b = outputs[True][index, 30, 90]
        assert g > 180 and r < 80 and b < 80, f"Green ASS must reappear at {index / 10}s"
    for index in (5, 24, 25, 31):
        r, g, b = outputs[False][index, 30, 90]
        assert g > 180 and r < 80 and b < 80, "Disabled card must never cover ASS"
