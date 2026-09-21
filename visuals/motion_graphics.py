"""Intentional kinetic typography clips when stock fails (not solid-color FAILSAFE)."""
from __future__ import annotations

import os
import re
import subprocess
from typing import List, Optional, Sequence, Tuple

import imageio_ffmpeg

from .palettes import palette_for

try:
    import config
except Exception:  # pragma: no cover
    config = None  # type: ignore


# Prefer paths without spaces; quoted fallback still handles Arial Bold.
_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
)

# Item 240 trigger names stuffed into spoken hooks — not for on-screen kinetic.
_STUFFED_NAME_RE = re.compile(
    r"\b(?:Elon Musk|Einstein|Nikola Tesla|Marcus Aurelius|"
    r"Steve Jobs|Warren Buffett|Napoleon|Cleopatra)"
    r"(?:['’](?:ın|in|un|ün|s))?\b[:,]?\s*",
    re.IGNORECASE,
)


def _rgb(c: Tuple[int, int, int]) -> str:
    return f"0x{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def _strip_stuffed_names(text: str) -> str:
    cleaned = _STUFFED_NAME_RE.sub("", text or "")
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def caption_lines(text: str, max_words: int = 12, max_chars: int = 42) -> List[str]:
    words = re.findall(r"\S+", _strip_stuffed_names(text))
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
    """Escape a string for drawtext text='...' (no real newlines, no ASCII apostrophe)."""
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("'", "\u2019").replace("\u2018", "\u2019")
    return (
        s.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("%", "\\%")
        .replace("\n", "\\n")
    )


def _quote_filter_path(path: str) -> str:
    """Quote a filesystem path for an ffmpeg filter option (spaces/colons safe)."""
    escaped = (
        (path or "")
        .replace("\\", "\\\\")
        .replace("'", r"\'")
        .replace(":", r"\:")
    )
    return f"'{escaped}'"


def _pick_fontfile() -> str:
    for cand in _FONT_CANDIDATES:
        if os.path.isfile(cand):
            return cand
    return ""


def _write_kinetic_textfile(path: str, lines: Sequence[str]) -> str:
    body = "\n".join(lines) if any(lines) else " "
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


def _drawtext_filter(
    *,
    fontfile: str,
    textfile: str,
    fontsize: int,
    fontcolor: str,
    x: str,
    y: str,
    fade_in: float,
    borderw: int = 0,
    bordercolor: str = "",
) -> str:
    font_arg = f"fontfile={_quote_filter_path(fontfile)}:" if fontfile else ""
    border = ""
    if borderw and bordercolor:
        border = f"borderw={borderw}:bordercolor={bordercolor}:"
    return (
        f"drawtext={font_arg}textfile={_quote_filter_path(textfile)}:expansion=none:"
        f"fontsize={fontsize}:fontcolor={fontcolor}:"
        f"x={x}:y={y}:line_spacing=12:{border}"
        f"alpha='if(lt(t,{fade_in}),t/{fade_in},1)'"
    )


def _grain_suffix(enabled: bool) -> str:
    if enabled:
        return ",vignette=PI/5,noise=alls=5:allf=t,format=yuv420p"
    return ",format=yuv420p"


def _run_ffmpeg(cmd: List[str], output_path: str, label: str, min_size: int = 12_000) -> bool:
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    except Exception as exc:
        print(f"    [kinetic] {label}: {exc}")
        return False
    if res.returncode != 0:
        err = (res.stderr or b"").decode("utf-8", "ignore")[-400:]
        print(f"    [kinetic] ffmpeg failed ({label}): {err}")
        return False
    return os.path.isfile(output_path) and os.path.getsize(output_path) > min_size


def build_solid_color_clip(
    output_path: str,
    duration: float,
    niche_id: str = "",
    scene_index: int = 0,
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: Optional[int] = None,
    textfile: str = "",
    fontfile: str = "",
) -> Optional[str]:
    """Palette color card (+ optional drawtext). Last-resort scene so fetch never stalls."""
    w = int(width or getattr(config, "VIDEO_WIDTH", 1080) if config else 1080)
    h = int(height or getattr(config, "VIDEO_HEIGHT", 1920) if config else 1920)
    r = int(fps or getattr(config, "FPS", 30) if config else 30)
    dur = max(1.0, float(duration))
    pal = palette_for(niche_id)
    colors = pal["colors"]
    bg = colors[scene_index % len(colors)]
    text_c = pal.get("text", (255, 255, 255))
    accent = pal.get("accent", (200, 200, 200))
    color_src = f"color=c={_rgb(bg)}:s={w}x{h}:d={dur:.3f}:r={r}"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if textfile and os.path.isfile(textfile):
        font = fontfile or _pick_fontfile()
        dt = _drawtext_filter(
            fontfile=font,
            textfile=textfile,
            fontsize=52,
            fontcolor=_rgb(text_c),
            x="(w-text_w)/2",
            y="(h-text_h)/2",
            fade_in=0.4,
            borderw=2,
            bordercolor=f"{_rgb(accent)}@0.35",
        )
        cmd = [
            ffmpeg, "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", color_src,
            "-filter_complex", f"{dt},format=yuv420p",
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-an",
            output_path,
        ]
        if _run_ffmpeg(cmd, output_path, "solid+text", min_size=2_000):
            return output_path
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", color_src,
        "-t", f"{dur:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-an",
        output_path,
    ]
    if _run_ffmpeg(cmd, output_path, "solid", min_size=2_000):
        return output_path
    return None


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
    On ffmpeg filter failure, retries without grain then a solid color card.
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
    fontfile = _pick_fontfile()
    textfile = output_path + ".kinetic.txt"
    _write_kinetic_textfile(textfile, lines)

    fade_in = max(0.05, round(min(0.6, dur * 0.15), 3))
    joined_len = sum(len(L) for L in lines)
    fontsize = 64 if joined_len < 40 else 52 if joined_len < 70 else 44
    dt_shadow = _drawtext_filter(
        fontfile=fontfile,
        textfile=textfile,
        fontsize=fontsize,
        fontcolor="black@0.55",
        x="(w-text_w)/2+3",
        y="(h-text_h)/2+3",
        fade_in=fade_in,
    )
    dt_main = _drawtext_filter(
        fontfile=fontfile,
        textfile=textfile,
        fontsize=fontsize,
        fontcolor=_rgb(text_c),
        x="(w-text_w)/2",
        y="(h-text_h)/2",
        fade_in=fade_in,
        borderw=2,
        bordercolor=f"{_rgb(accent)}@0.35",
    )
    box = (
        f"drawbox=x=(w-420)/2:y=(h/2)+90:w=420:h=6:color={_rgb(accent)}@0.85:t=fill"
    )

    zoom = 0.0005 + 0.00015 * (scene_index % 3)
    grad = (
        f"gradients=s={w}x{h}:c0={_rgb(ordered[0])}:c1={_rgb(ordered[1])}:c2={_rgb(ordered[2])}:"
        f"c3={_rgb(ordered[0])}:n=4:speed={speed:.3f}:type={gtype}:duration={dur:.3f}:rate={r}:seed={seed}"
    )
    life = (
        f"life=s={max(60, w // 10)}x{max(100, h // 10)}:mold=5:r={r}:ratio=0.05:seed={seed}:"
        f"death_color=black:life_color={_rgb(accent)}:stitch=0,"
        f"scale={w}:{h}:flags=bicubic,gblur=sigma={max(10, w // 50)}"
    )
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    def _full_graph(grain: bool) -> str:
        return (
            "[0:v]format=gbrp[bg];[1:v]format=gbrp[fx];"
            "[bg][fx]blend=all_mode=screen:all_opacity=0.55,"
            f"zoompan=z='1+{zoom:.5f}*on':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={r},"
            f"{box},{dt_shadow},{dt_main}{_grain_suffix(grain)}"
        )

    try:
        for grain, label in ((True, "full"), (False, "no-grain")):
            cmd = [
                ffmpeg, "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", grad,
                "-f", "lavfi", "-i", life,
                "-filter_complex", _full_graph(grain),
                "-t", f"{dur:.3f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-an",
                output_path,
            ]
            if _run_ffmpeg(cmd, output_path, label):
                return output_path
        print("    [kinetic] falling back to solid color card")
        return build_solid_color_clip(
            output_path,
            dur,
            niche_id=niche_id,
            scene_index=scene_index,
            width=w,
            height=h,
            fps=r,
            textfile=textfile,
            fontfile=fontfile,
        )
    finally:
        try:
            if os.path.isfile(textfile):
                os.remove(textfile)
        except OSError:
            pass
