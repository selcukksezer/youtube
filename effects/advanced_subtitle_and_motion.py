from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw


# Problem #61: True 3-Layer ASS Subtitle Extrusion (Shadow + Mid-Bevel + Foreground)
def build_3d_extrude_ass_dialogue_layers(
    start_ass: str,
    end_ass: str,
    text: str,
    x: int = 540,
    y: int = 1380,
    style: str = "Default",
) -> list[str]:
    """Generates 3 layered ASS Dialogue lines (Layer 0 deep shadow, Layer 1 mid-extrude, Layer 2 front face)."""
    layer0 = (
        f"Dialogue: 0,{start_ass},{end_ass},{style},,0,0,0,,"
        f"{{\\pos({x + 6},{y + 6})\\1c&H000000&\\3c&H000000&\\bord6\\blur3\\alpha&H50&}}{text}"
    )
    layer1 = (
        f"Dialogue: 1,{start_ass},{end_ass},{style},,0,0,0,,"
        f"{{\\pos({x + 3},{y + 3})\\1c&H222222&\\3c&H111111&\\bord4\\blur1}}{text}"
    )
    layer2 = (
        f"Dialogue: 2,{start_ass},{end_ass},{style},,0,0,0,,"
        f"{{\\pos({x},{y})\\bord3\\blur0.4}}{text}"
    )
    return [layer0, layer1, layer2]


# Problem #62: Occlusion-Free Dynamic Subtitle Y Resolver
def resolve_occlusion_free_subtitle_y(
    face_boxes: list[tuple[int, int, int, int]] | None = None,
    has_lower_third: bool = False,
    frame_height: int = 1920,
) -> int:
    """Shifts subtitle Y coordinate into the safe upper-middle zone when a face or lower-third occupies the bottom."""
    default_y = int(frame_height * 0.72)  # ~1382
    upper_safe_y = int(frame_height * 0.48)  # ~921

    if has_lower_third:
        return upper_safe_y

    if face_boxes:
        for (_, y, _, h) in face_boxes:
            box_bottom = y + h
            if y <= default_y <= box_bottom + 140:
                return upper_safe_y
    return default_y


# Problem #63: Automatic Keyword Popup & B-Roll Trigger Extractor
def extract_auto_keyword_popups(
    scene_text: str,
    scene_start_sec: float = 0.0,
    scene_duration_sec: float = 4.0,
) -> list[dict[str, Any]]:
    """Extracts numbers, percentages, and capitalized/high-salience words to trigger automatic popup badges."""
    words = (scene_text or "").split()
    if not words:
        return []

    popups: list[dict[str, Any]] = []
    time_per_word = scene_duration_sec / float(max(len(words), 1))
    for idx, raw_w in enumerate(words):
        clean_w = raw_w.strip(".,!?;:\"'()")
        is_numeric = bool(re.search(r"\d+|%|₺|\$|€", clean_w))
        is_salient = len(clean_w) >= 6 and (clean_w.isupper() or idx in (0, len(words) - 1))
        if is_numeric or is_salient:
            popups.append(
                {
                    "keyword": clean_w.upper(),
                    "trigger_sec": round(scene_start_sec + idx * time_per_word, 2),
                    "duration_sec": 0.85,
                    "badge_type": "metric_pop" if is_numeric else "keyword_highlight",
                }
            )
    return popups[:3]


# Problem #64: Tension-Triggered Dynamic Vignette Filter
def build_tension_triggered_vignette_filter(
    tension_Windows: list[tuple[float, float]],
    angle_rad: float = 0.62,
) -> str:
    """Applies FFmpeg vignette only during climax/tension windows instead of darkening the entire video."""
    if not tension_Windows:
        return "null"
    conds = "+".join([f"between(t,{s:.2f},{e:.2f})" for s, e in tension_Windows])
    return f"vignette=angle={angle_rad:.2f}:enable='{conds}'"


# Problem #65: Translucent Yellow Marker Stroke Highlight PNG
def render_marker_stroke_highlight_png(
    output_path: str | Path,
    text_width: int = 420,
    text_height: int = 84,
    progress: float = 1.0,
) -> str:
    """Renders a translucent highlighter pen stroke (`rgba(255, 230, 0, 145)`) behind emphasized words."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    w = max(64, int(text_width))
    h = max(32, int(text_height))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    fill_w = max(12, int(w * max(0.05, min(1.0, progress))))
    draw.rounded_rectangle([(4, 8), (fill_w - 4, h - 8)], radius=14, fill=(255, 230, 0, 148))
    img.save(str(out), format="PNG")
    return str(out)


# Problem #66: Damped Spring Emoji Bobbing Physics
def compute_damped_spring_emoji_bob(
    t_sec: float,
    amplitude_px: float = 24.0,
    damping: float = 4.2,
    omega: float = 16.0,
) -> dict[str, float]:
    """Computes damped harmonic oscillator (`e^(-d*t) * cos(w*t)`) vertical offset and scale for floating emojis."""
    t = max(0.0, float(t_sec))
    envelope = math.exp(-damping * t)
    y_offset = round(-amplitude_px * envelope * math.cos(omega * t), 2)
    scale = round(1.0 + 0.22 * envelope * math.sin(omega * t), 3)
    return {"y_offset_px": y_offset, "scale": scale}


# Problem #67: Niche-Mandatory Font Family Resolver
NICHE_MANDATORY_FONTS: dict[str, dict[str, str]] = {
    "finance": {"primary": "Montserrat ExtraBold", "fallback": "Arial Black"},
    "crypto": {"primary": "Montserrat ExtraBold", "fallback": "Impact"},
    "history": {"primary": "Cinzel Bold", "fallback": "Georgia"},
    "spiritual": {"primary": "Cormorant Garamond Bold", "fallback": "Times New Roman"},
    "mystery": {"primary": "Bebas Neue", "fallback": "Impact"},
    "tech": {"primary": "JetBrains Mono Bold", "fallback": "Helvetica Neue"},
}


def get_niche_mandatory_font_family(niche_id: str) -> dict[str, str]:
    """Maps a niche ID or category name to its typography palette with system-safe fallback."""
    lower = (niche_id or "").lower()
    for key, spec in NICHE_MANDATORY_FONTS.items():
        if key in lower:
            return dict(spec)
    if "dua" in lower or "islam" in lower:
        return dict(NICHE_MANDATORY_FONTS["spiritual"])
    return {"primary": "Montserrat ExtraBold", "fallback": "Helvetica Neue"}


# Problem #68: Procedural Light-Leak & Film-Burn Transition Filter
def build_light_leak_transition_filter(
    cut_time_sec: float,
    duration_sec: float = 0.35,
) -> str:
    """Builds an procedural warm film-burn / light-leak exposure flash filter across a scene cut."""
    half = duration_sec / 2.0
    start = max(0.0, cut_time_sec - half)
    end = cut_time_sec + half
    return (
        f"eq=brightness=0.22:saturation=1.35:gamma=1.18:"
        f"enable='between(t,{start:.2f},{end:.2f})'"
    )


# Problem #69: Continuous 2D Perlin-Style Low-Frequency Camera Shake
def perlin_2d_camera_shake_offset(
    t_sec: float,
    intensity_px: float = 8.0,
    freq_hz: float = 1.7,
) -> tuple[float, float]:
    """Computes smooth, non-jarring handheld camera drift `(dx, dy)` using multi-octave value noise."""
    x = (
        math.sin(2.0 * math.pi * freq_hz * t_sec) * 0.6
        + math.sin(2.0 * math.pi * (freq_hz * 2.13) * t_sec + 1.3) * 0.3
        + math.cos(2.0 * math.pi * (freq_hz * 0.53) * t_sec + 0.7) * 0.1
    )
    y = (
        math.cos(2.0 * math.pi * (freq_hz * 1.17) * t_sec + 0.5) * 0.6
        + math.sin(2.0 * math.pi * (freq_hz * 1.89) * t_sec + 2.1) * 0.3
        + math.sin(2.0 * math.pi * (freq_hz * 0.61) * t_sec + 1.9) * 0.1
    )
    return (round(x * intensity_px, 2), round(y * intensity_px, 2))


# Problem #70: Interactive NLE Timeline Scrubbing Manifest Builder
def build_nle_timeline_scrub_manifest(
    scenes: list[dict[str, Any]],
    bgm_track: str | None = None,
) -> dict[str, Any]:
    """Builds a multi-track (Video, Subtitle, Audio, FX) timeline manifest for Web Studio NLE scrubbing."""
    video_track: list[dict[str, Any]] = []
    subtitle_track: list[dict[str, Any]] = []
    fx_track: list[dict[str, Any]] = []
    cursor = 0.0

    for idx, sc in enumerate(scenes):
        dur = max(1.0, float(sc.get("duration", 4.0)))
        start = round(cursor, 2)
        end = round(cursor + dur, 2)
        video_track.append(
            {
                "scene_index": idx + 1,
                "start_sec": start,
                "end_sec": end,
                "visual_query": sc.get("visual_query", ""),
                "transition": sc.get("transition", "fade"),
            }
        )
        subtitle_track.append(
            {
                "scene_index": idx + 1,
                "start_sec": start,
                "end_sec": end,
                "text": sc.get("text", ""),
            }
        )
        fx_track.append(
            {
                "scene_index": idx + 1,
                "start_sec": start,
                "end_sec": end,
                "popups": extract_auto_keyword_popups(str(sc.get("text", "")), start, dur),
            }
        )
        cursor += dur

    return {
        "total_duration_sec": round(cursor, 2),
        "tracks": {
            "video": video_track,
            "subtitles": subtitle_track,
            "fx": fx_track,
            "bgm": {"track": bgm_track or "auto", "duration_sec": round(cursor, 2)},
        },
    }
