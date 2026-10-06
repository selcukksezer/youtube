"""P1 native FFmpeg proof: dynamic face crop keeps a moving target centered."""
from pathlib import Path
import subprocess
import wave
from unittest.mock import Mock

import numpy as np

from anti_detect import post_render
from render import ffmpeg_graph as graph
from visuals import face_reframe
import system_resilience


WIDTH, HEIGHT, FPS, DURATION = 640, 360, 10, 3.6
OUT_W, OUT_H = 180, 320


def _write_motion_source(ffmpeg, path: Path):
    """Create a noisy landscape source with a red target moving left to right."""
    frame_count = round(DURATION * FPS)
    rng = np.random.default_rng(42)
    gray = rng.integers(0, 220, (frame_count, HEIGHT, WIDTH, 1), dtype=np.uint8)
    frames = np.repeat(gray, 3, axis=3)
    for index in range(frame_count):
        center = round(WIDTH * (0.22 + 0.56 * index / (frame_count - 1)))
        frames[index, 120:240, center - 30:center + 30] = (255, 0, 0)
    subprocess.run(
        [
            ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s:v", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "pipe:0", "-an",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "0",
            "-pix_fmt", "yuv420p", str(path),
        ],
        input=frames.tobytes(), check=True, capture_output=True, timeout=30,
    )


def _write_audio(path: Path):
    with wave.open(str(path), "wb") as voice:
        voice.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        voice.writeframes(b"\0\0" * round(16000 * DURATION))


def _decode_frames(ffmpeg, path: Path):
    decoded = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(path), "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
        check=True, capture_output=True, timeout=30,
    )
    return np.frombuffer(decoded.stdout, dtype=np.uint8).reshape((-1, OUT_H, OUT_W, 3))


def _red_center(frame):
    mask = (frame[:, :, 0] > 180) & (frame[:, :, 1] < 80) & (frame[:, :, 2] < 80)
    _, xs = np.where(mask)
    assert len(xs) > 200, "Moving red target must survive the native crop"
    return float(xs.mean())


def _configure_native(monkeypatch):
    monkeypatch.setattr(graph.config, "get_target_resolution", lambda: (OUT_W, OUT_H))
    monkeypatch.setattr(graph.config, "FPS", FPS)
    monkeypatch.setattr(graph.config, "FPS_DIVERSIFY", False)
    monkeypatch.setattr(graph.config, "USE_GPU_ACCELERATION", False)
    monkeypatch.setattr(graph.config, "FFMPEG_THREADS", 2)
    monkeypatch.setattr(graph, "get_look_filters", lambda *args, **kwargs: "null")
    monkeypatch.setattr(graph, "probe_stream_color", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        system_resilience,
        "get_encoder_fallback_chain",
        lambda *args: [(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "0"], "P1 test CPU")],
    )
    monkeypatch.setattr(post_render, "apply_post_render_humanization", lambda *args, **kwargs: {})


def test_native_face_track_is_dynamic_centered_single_encode_and_fit_fill_fallbacks(tmp_path, monkeypatch):
    _configure_native(monkeypatch)
    ffmpeg = graph.imageio_ffmpeg.get_ffmpeg_exe()
    source = tmp_path / "moving_landscape.mp4"
    audio = tmp_path / "voice.wav"
    _write_motion_source(ffmpeg, source)
    _write_audio(audio)

    detector_track = [
        (0.0, 0.22),
        (1.2, 0.4066667),
        (2.4, 0.5933333),
        (3.6, 0.78),
    ]
    detector = Mock(return_value=detector_track)
    monkeypatch.setattr(face_reframe, "detect_face_track", detector)

    render_commands = []
    real_popen = graph.subprocess.Popen

    def record_render(command, *args, **kwargs):
        if "-filter_complex" in command:
            render_commands.append(command)
        return real_popen(command, *args, **kwargs)

    monkeypatch.setattr(graph.subprocess, "Popen", record_render)

    active_path = tmp_path / "face_on.mp4"
    active_result = graph.render_with_ffmpeg_graph(
        [{"path": str(source), "duration": DURATION}],
        str(audio), str(active_path),
        anti_duplicate=False,
        enable_ken_burns=True,
        enable_zoompan=True,
        enable_face_center=True,
    )
    assert active_result == str(active_path)
    detector.assert_called_once_with(str(source), duration=DURATION)

    active_command = render_commands[-1]
    active_filter = active_command[active_command.index("-filter_complex") + 1]
    assert active_command.count("-i") == 2, "Native scenario must have one video and one audio input"
    assert "crop=180:320:x='" in active_filter, "Dynamic crop_x must be quoted as an FFmpeg expression"
    assert "clip((t-" in active_filter, "Face crop must vary with t"
    assert "zoompan" not in active_filter, "Tracked face suppresses zoompan"
    assert "in_w-out_w" not in active_filter, "Tracked face suppresses cheap_pan"

    active_frames = _decode_frames(ffmpeg, active_path)
    assert len(active_frames) == round(DURATION * FPS), "Face tracking must preserve source duration"
    for time in (0.15, 1.05, 2.15, 3.25):
        assert OUT_W / 3 <= _red_center(active_frames[round(time * FPS)]) <= OUT_W * 2 / 3

    off_detector = Mock(side_effect=AssertionError("disabled flag must not detect faces"))
    monkeypatch.setattr(face_reframe, "detect_face_track", off_detector)
    off_path = tmp_path / "face_off.mp4"
    off_result = graph.render_with_ffmpeg_graph(
        [{"path": str(source), "duration": DURATION}],
        str(audio), str(off_path),
        anti_duplicate=False,
        enable_ken_burns=True,
        enable_zoompan=True,
        enable_face_center=False,
    )
    assert off_result == str(off_path)
    off_detector.assert_not_called()
    off_filter = render_commands[-1][render_commands[-1].index("-filter_complex") + 1]
    assert "boxblur=25:5" in off_filter and "bg_blur_0" in off_filter

    noface_detector = Mock(return_value=[])
    monkeypatch.setattr(face_reframe, "detect_face_track", noface_detector)
    noface_path = tmp_path / "face_noface.mp4"
    noface_result = graph.render_with_ffmpeg_graph(
        [{"path": str(source), "duration": DURATION}],
        str(audio), str(noface_path),
        anti_duplicate=False,
        enable_ken_burns=True,
        enable_zoompan=True,
        enable_face_center=True,
    )
    assert noface_result == str(noface_path)
    noface_detector.assert_called_once_with(str(source), duration=DURATION)
    noface_filter = render_commands[-1][render_commands[-1].index("-filter_complex") + 1]
    assert "boxblur=25:5" in noface_filter and "bg_blur_0" in noface_filter
    assert len(render_commands) == 3, "Each scenario must use one native encode"
