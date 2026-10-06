"""P1 MoviePy proof: moving targets, timing transforms and fallback wiring."""
import sys
from unittest.mock import Mock, patch

import numpy as np
import pytest
from moviepy.editor import ColorClip, VideoClip, vfx

import video_composer as composer
from render import ffmpeg_graph
from visuals import face_reframe


def _moving_source(duration=4.0):
    def frame(time):
        pixels = np.empty((180, 320, 3), dtype=np.uint8)
        pixels[:] = (10, 20, 40)
        center = round(320 * (0.2 + 0.6 * time / duration))
        pixels[45:135, center - 12:center + 12] = (255, 0, 0)
        return pixels
    return VideoClip(frame, duration=duration).set_fps(10)


def _track(duration):
    return [(0.0, 0.2), (duration / 2.0, 0.5), (duration, 0.8)]


def _assert_centered(clip, times):
    for time in times:
        frame = clip.get_frame(time)
        mask = (frame[:, :, 0] > 200) & (frame[:, :, 1] < 50) & (frame[:, :, 2] < 50)
        _, xs = np.where(mask)
        assert len(xs), f"Tracked target disappeared at {time}s"
        assert frame.shape[1] / 3 <= xs.mean() <= frame.shape[1] * 2 / 3, (time, xs.mean())


@pytest.mark.parametrize("source_duration, scene_duration", [(4.0, 4.0), (8.0, 2.0), (2.0, 6.0)])
def test_prep_follows_motion_through_trim_or_loop(tmp_path, monkeypatch, source_duration, scene_duration):
    path = tmp_path / "source.mp4"
    path.touch()
    source = _moving_source(source_duration)
    detector = Mock(return_value=_track(source_duration))
    monkeypatch.setattr(composer, "VideoFileClip", lambda *args, **kwargs: source)
    monkeypatch.setattr(face_reframe, "detect_face_track", detector)
    out = composer._prep(str(path), scene_duration, 90, 160, enable_section2=False, enable_face_center=True)
    try:
        assert out.size == (90, 160)
        assert out.duration == pytest.approx(scene_duration)
        assert out._face_centered
        _assert_centered(out, [0.1, scene_duration * 0.4, scene_duration * 0.8])
        detector.assert_called_once_with(str(path), duration=source_duration)
    finally:
        out.close()
        source.close()


def test_face_track_stays_aligned_after_speed_and_flip(tmp_path, monkeypatch):
    path = tmp_path / "source.mp4"
    path.touch()
    source = _moving_source(8.0)
    monkeypatch.setattr(composer, "VideoFileClip", lambda *args, **kwargs: source)
    monkeypatch.setattr(face_reframe, "detect_face_track", lambda *args, **kwargs: _track(8.0))
    monkeypatch.setattr(composer, "apply_speed_ramp", lambda clip: clip.fx(vfx.speedx, 1.5))
    monkeypatch.setattr(composer, "apply_horizontal_flip", lambda clip: clip.fx(vfx.mirror_x))
    monkeypatch.setattr(composer, "apply_multi_layer_overlay", lambda clip, **kwargs: clip)
    monkeypatch.setattr(composer, "apply_corner_radius_to_clip", lambda clip, **kwargs: clip)
    out = composer._prep(str(path), 3.0, 90, 160, enable_section2=True, enable_face_center=True)
    try:
        _assert_centered(out, [0.1, 1.4, 2.9])
        assert out.duration == pytest.approx(3.0)
    finally:
        out.close()
        source.close()


def test_disabled_face_tracking_never_calls_detector(tmp_path, monkeypatch):
    source = _moving_source()
    monkeypatch.setattr(composer, "VideoFileClip", lambda *args, **kwargs: source)
    detector = Mock(side_effect=AssertionError("Off must not detect faces"))
    monkeypatch.setattr(face_reframe, "detect_face_track", detector)
    out = composer._prep(str(tmp_path / "source.mp4"), 4.0, 90, 160, enable_section2=False, enable_face_center=False)
    try:
        assert not out._face_centered
        assert out.size == (90, 160)
        detector.assert_not_called()
    finally:
        out.close()
        source.close()


@pytest.mark.parametrize("failure", ["no_face", "no_opencv", "detector_error"])
def test_missing_detection_preserves_existing_fit_fill(tmp_path, monkeypatch, failure):
    path = tmp_path / "source.mp4"
    path.touch()
    source = _moving_source()
    monkeypatch.setattr(composer, "VideoFileClip", lambda *args, **kwargs: source)
    baseline = composer._prep(str(path), 4.0, 90, 160, enable_section2=False, enable_face_center=False)
    if failure == "no_face":
        monkeypatch.setattr(face_reframe, "detect_face_track", lambda *args, **kwargs: [])
    elif failure == "detector_error":
        monkeypatch.setattr(face_reframe, "detect_face_track", Mock(side_effect=RuntimeError("Detector unavailable")))
    try:
        with patch.dict(sys.modules, {"cv2": None}) if failure == "no_opencv" else patch.dict(sys.modules, {}):
            out = composer._prep(str(path), 4.0, 90, 160, enable_section2=False, enable_face_center=True)
        assert not out._face_centered
        for time in (0.1, 1.5, 3.0):
            assert np.array_equal(out.get_frame(time), baseline.get_frame(time))
        out.close()
    finally:
        baseline.close()
        source.close()


def test_split_screen_tracks_in_top_panel(tmp_path, monkeypatch):
    source = _moving_source()
    gameplay = tmp_path / "gameplay.mp4"
    gameplay.touch()
    monkeypatch.setattr(composer, "VideoFileClip", lambda *args, **kwargs: source)
    monkeypatch.setattr(face_reframe, "detect_face_track", lambda *args, **kwargs: _track(4.0))
    from effects import layout
    monkeypatch.setattr(layout, "VideoFileClip", lambda *args, **kwargs: ColorClip((90, 68), color=(0, 0, 50), duration=4.0))
    out = composer._prep(str(tmp_path / "source.mp4"), 4.0, 90, 160, split_screen=True, gameplay_path=str(gameplay), enable_section2=False, enable_face_center=True)
    try:
        assert out.size == (90, 160)
        assert out._face_centered
        _assert_centered(out, [0.5, 2.0, 3.5])
    finally:
        out.close()
        source.close()


@pytest.mark.parametrize("hybrid", [False, True])
def test_director_fallback_retains_explicit_face_selection(monkeypatch, hybrid):
    renderer = Mock(return_value="")
    composer_call = Mock(return_value="fallback.mp4")
    monkeypatch.setattr(ffmpeg_graph, "render_with_ffmpeg_graph", renderer)
    monkeypatch.setattr(composer, "compose_video", composer_call)
    monkeypatch.setattr(ffmpeg_graph.config, "ENABLE_FFMPEG_GRAPH", True)
    result = ffmpeg_graph.compose_via_director([], "voice.wav", [], "out.mp4", enable_face_center=True, hybrid_render_overlay={"ui_type": "imessage"} if hybrid else {})
    assert result == "fallback.mp4"
    assert composer_call.call_args.kwargs["enable_face_center"] is True
    assert renderer.call_count == (0 if hybrid else 1)


@pytest.mark.parametrize("tracked", [False, True])
@pytest.mark.parametrize("section2", [False, True])
def test_composer_passes_face_setting_and_keeps_global_camera_off_tracked_faces(tmp_path, monkeypatch, tracked, section2):
    class ScenePrepared(Exception):
        pass
    path = tmp_path / "source.mp4"
    path.touch()
    clip = ColorClip((90, 160), color=(10, 20, 40), duration=1.0)
    clip._face_centered = tracked
    prep = Mock(return_value=clip)
    monkeypatch.setattr(composer, "_prep", prep)
    monkeypatch.setattr(composer, "cleanup_stray_ffmpeg_processes", lambda: None)
    monkeypatch.setattr(composer.config, "ENABLE_SFX", False)
    monkeypatch.setattr(composer.config, "ENABLE_BGM", False)
    monkeypatch.setattr(composer.config, "get_target_resolution", lambda: (90, 160))
    for name in ("apply_out_of_focus_reveal", "apply_censored_blur_bait", "apply_opening_pattern_interrupt", "apply_scene_brightness_alternation"):
        monkeypatch.setattr(composer, name, lambda clip, **kwargs: clip)
    camera_calls = {}
    for name in ("apply_ken_burns", "apply_handheld_camera_shake", "apply_alternating_motion"):
        camera_calls[name] = Mock(side_effect=lambda clip, **kwargs: clip)
        monkeypatch.setattr(composer, name, camera_calls[name])
    def progress(percent, message):
        if message.startswith("Sahneler hazırlandı"):
            raise ScenePrepared
    with pytest.raises(ScenePrepared):
        composer.compose_video([{"path": str(path), "duration": 1.0}], str(tmp_path / "voice.wav"), [], str(tmp_path / "out.mp4"), audio_premastered=True, enable_face_center=True, enable_section2_filters=section2, progress_callback=progress)
    assert prep.call_args.kwargs["enable_face_center"] is True
    assert camera_calls["apply_ken_burns"].call_count == int(not tracked and not section2)
    assert camera_calls["apply_handheld_camera_shake"].call_count == int(not tracked and section2)
    assert camera_calls["apply_alternating_motion"].call_count == int(not tracked and section2)
