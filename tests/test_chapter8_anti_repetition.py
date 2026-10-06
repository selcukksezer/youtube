"""
Tests for Chapter 8.2: YouTube Tekrarlayan ve Otomatik İçerik Koruma Kalkanı
Covers:
- RGB Color Jitter with independent gamma_r, gamma_g, gamma_b
- Dynamic FPS diversification (29.97, 30.00, 30.02)
- Invisible temporal noise layer (noise=alls=3:allf=t)
- Anti-repetition audit function
- Integration with render/ffmpeg_graph and effects/filters
"""
import re
import pytest
from compliance.anti_repetition import (
    get_rgb_color_jitter_filter,
    get_diversified_fps,
    get_temporal_noise_filter,
    build_anti_repetition_filter_chain,
    audit_anti_repetition_shield,
    ALLOWED_DIVERSIFIED_FPS,
)
from render.ffmpeg_graph import get_look_filters
from effects.filters import get_color_grading_ffmpeg_filter


def test_rgb_color_jitter_format_and_bounds():
    jitter_filter = get_rgb_color_jitter_filter(jitter_range=0.015, seed=42)
    assert jitter_filter.startswith("eq=")

    # Parse key-values
    kv_pairs = jitter_filter[3:].split(":")
    kv_dict = {}
    for pair in kv_pairs:
        k, v = pair.split("=")
        kv_dict[k] = float(v)

    assert "contrast" in kv_dict
    assert "gamma_r" in kv_dict
    assert "gamma_g" in kv_dict
    assert "gamma_b" in kv_dict
    assert "saturation" in kv_dict

    for k, val in kv_dict.items():
        assert 0.985 <= val <= 1.015, f"{k}={val} is outside [0.985, 1.015]"


def test_rgb_channels_vary_independently():
    # Over multiple random samples, RGB channels should not all be identical
    found_distinct = False
    for _ in range(10):
        filt = get_rgb_color_jitter_filter(jitter_range=0.015)
        m = re.findall(r"gamma_([rgb])=([\d\.]+)", filt)
        vals = {chan: float(val) for chan, val in m}
        if vals["r"] != vals["g"] or vals["g"] != vals["b"]:
            found_distinct = True
            break
    assert found_distinct, "gamma_r, gamma_g, and gamma_b were unexpectedly identical"


def test_diversified_fps_selection():
    assert ALLOWED_DIVERSIFIED_FPS == (29.97, 30.00, 30.02)

    selected = set()
    for _ in range(50):
        fps = get_diversified_fps()
        assert fps in ALLOWED_DIVERSIFIED_FPS
        selected.add(fps)

    # Over 50 random samples, we should observe all allowed rates
    assert len(selected) > 1, f"Expected varied FPS selection, got: {selected}"


def test_temporal_noise_filter():
    noise_str = get_temporal_noise_filter(strength=3, flag="t")
    assert noise_str == "noise=alls=3:allf=t"

    custom_noise = get_temporal_noise_filter(strength=5, flag="u")
    assert custom_noise == "noise=alls=5:allf=u"


def test_build_anti_repetition_filter_chain():
    chain = build_anti_repetition_filter_chain(
        anti_duplicate=True,
        include_vignette=True,
    )
    assert "gamma_r=" in chain
    assert "gamma_g=" in chain
    assert "gamma_b=" in chain
    assert "unsharp=5:5:0.8:5:5:0.0" in chain
    assert "noise=alls=3:allf=t" in chain
    assert "vignette=PI/5" in chain

    # Without anti_duplicate
    chain_no_noise = build_anti_repetition_filter_chain(
        anti_duplicate=False,
        include_vignette=False,
    )
    assert "noise=" not in chain_no_noise
    assert "vignette=" not in chain_no_noise


def test_audit_anti_repetition_shield():
    compliant_filter = build_anti_repetition_filter_chain(anti_duplicate=True)
    report = audit_anti_repetition_shield(
        filter_complex_str=compliant_filter,
        rendered_fps=29.97,
    )
    assert report["compliant"] is True
    assert report["rgb_jitter"] is True
    assert report["temporal_noise"] is True
    assert report["fps_diversified"] is True

    # Non-compliant filter (missing RGB gamma and wrong FPS)
    bad_report = audit_anti_repetition_shield(
        filter_complex_str="eq=gamma=1.0:contrast=1.0",
        rendered_fps=60.0,
    )
    assert bad_report["compliant"] is False
    assert bad_report["rgb_jitter"] is False
    assert bad_report["temporal_noise"] is False
    assert bad_report["fps_diversified"] is False


def test_scene_chain_uses_chosen_fps_not_a_later_retimer():
    from render.ffmpeg_graph import build_scene_filter_chain
    chain = build_scene_filter_chain(0, 3.0, 1080, 1920, 0, output_fps=29.97)
    assert "fps=29.97" in chain
    assert "fps=30," not in chain
    assert "fps=30.0" not in chain


def test_integration_render_ffmpeg_graph_look_filters():
    look = get_look_filters(1080, 1920, anti_duplicate=True)
    assert "gamma_r=" in look
    assert "gamma_g=" in look
    assert "gamma_b=" in look
    assert "contrast=" in look
    assert "saturation=" in look
    assert "unsharp=5:5:0.8:5:5:0.0" in look
    assert "noise=alls=3:allf=t" in look
    assert "vignette=PI/5" in look


def test_integration_effects_filters_color_grading():
    cg = get_color_grading_ffmpeg_filter()
    assert "gamma_r=" in cg
    assert "gamma_g=" in cg
    assert "gamma_b=" in cg
    assert "contrast=" in cg
    assert "saturation=" in cg
