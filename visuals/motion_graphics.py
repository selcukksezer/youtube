"""Intentional kinetic typography clips when stock fails (not solid-color FAILSAFE)."""
from __future__ import annotations

import os
import re
import subprocess
from typing import List, Optional, Tuple

import imageio_ffmpeg

from .palettes import palette_for

try:
    import config
except Exception:  # pragma: no cover
    config = None  # type: ignore


def _rgb(c: Tuple[int, int, int]) -> str:
    return f"0x{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def caption_lines(text: str, max_words: int = 12, max_chars: int = 42) -> List[str]:
    words = re.findall(r"\S+", (text or "").strip())
    if not words:
        return [""]
    words = words[:max_words]
    lines: List[str] = []
    cur: List[str] = []
    for w in words:
        trial = (" ".join(cur + [w])).strip()
        if len(trial) > max_chars and cur:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines[:3] or [""]


def _escape_drawtext(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def build_kinetic_clip(
    output_path: str,
    duration: float,
    text: str,
    niche_id: str = "",
    scene_index: int = 0,
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: Optional[int] = None,
) -> Optional[str]:
    """
    Niche-palette gradient + word-reveal kinetic title.
    Uses lavfi gradients + drawtext; no MoviePy / ImageMagick.
    """
    w = int(width or getattr(config, "VIDEO_WIDTH", 1080) if config else 1080)
    h = int(height or getattr(config, "VIDEO_HEIGHT", 1920) if config else 1920)
    r = int(fps or getattr(config, "FPS", 30) if config else 30)
    dur = max(1.5, float(duration))
    pal = palette_for(niche_id)
    colors = pal["colors"]
    accent = pal.get("accent", (200, 200, 200))
    text_c = pal.get("text", (255, 255, 255))
    motion = pal.get("motion", "drift")

    c0, c1, c2 = colors[0], colors[1], colors[min(2, len(colors) - 1)]
    rot = scene_index % 3
    ordered = [c0, c1, c2][rot:] + [c0, c1, c2][:rot]
    gtypes = {"slow_zoom": "radial", "pulse": "spiral", "reveal": "linear", "drift": "radial", "fast_cut": "linear"}
    gtype = gtypes.get(motion, "linear")
    seed = 2000 + scene_index * 4243
    speed = 0.025 + 0.008 * (scene_index % 4)

    lines = caption_lines(text)
    display = _escape_drawtext("\n".join(lines) if lines else " ")
    # Font: prefer macOS/DejaVu
    fontfile = ""
    for cand in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if os.path.isfile(cand):
            fontfile = cand
            break

    # Staggered fade-in for kinetic feel
    fade_in = min(0.6, dur * 0.15)
    fontsize = 64 if len(display) < 40 else 52 if len(display) < 70 else 44
    font_arg = f"fontfile={fontfile}:" if fontfile else ""
    # shadow + main text
    dt_shadow = (
        f"drawtext={font_arg}text='{display}':fontsize={fontsize}:fontcolor=black@0.55:"
        f"x=(w-text_w)/2+3:y=(h-text_h)/2+3:line_spacing=12:"
        f"alpha='if(lt(t,{fade_in}),t/{fade_in},1)'"
    )
    dt_main = (
        f"drawtext={font_arg}text='{display}':fontsize={fontsize}:fontcolor={_rgb(text_c)}:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=12:"
        f"borderw=2:bordercolor={_rgb(accent)}@0.35:"
        f"alpha='if(lt(t,{fade_in}),t/{fade_in},1)'"
    )
    # Accent bar under text
    bar_y = "h/2+text_h/2+28"
    # use a fixed bar via drawbox (approx center)
    box = (
        f"drawbox=x=(w-420)/2:y=(h/2)+90:w=420:h=6:color={_rgb(accent)}@0.85:t=fill"
    )

    zoom = 0.0005 + 0.00015 * (scene_index % 3)
    grad = (
        f"gradients=s={w}x{h}:c0={_rgb(ordered[0])}:c1={_rgb(ordered[1])}:c2={_rgb(ordered[2])}:"
        f"c3={_rgb(ordered[0])}:n=4:speed={speed:.3f}:type={gtype}:duration={dur:.3f}:rate={r}:seed={seed}"
    )
    # soft particle layer
    life = (
        f"life=s={max(60, w // 10)}x{max(100, h // 10)}:mold=5:r={r}:ratio=0.05:seed={seed}:"
        f"death_color=black:life_color={_rgb(accent)}:stitch=0,"
        f"scale={w}:{h}:flags=bicubic,gblur=sigma={max(10, w // 50)}"
    )
    graph = (
        "[0:v]format=gbrp[bg];[1:v]format=gbrp[fx];"
        "[bg][fx]blend=all_mode=screen:all_opacity=0.55,"
        f"zoompan=z='1+{zoom:.5f}*on':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={r},"
        f"{box},{dt_shadow},{dt_main},vignette=PI/5,noise=alls=5:allf=t,format=yuv420p"
    )
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", grad,
        "-f", "lavfi", "-i", life,
        "-filter_complex", graph,
        "-t", f"{dur:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-an",
        output_path,
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    except Exception as exc:
        print(f"    [kinetic] {exc}")
        return None
    if res.returncode != 0:
        err = (res.stderr or b"").decode("utf-8", "ignore")[-400:]
        print(f"    [kinetic] ffmpeg failed: {err}")
        return None
    if os.path.isfile(output_path) and os.path.getsize(output_path) > 12_000:
        return output_path
    return None
