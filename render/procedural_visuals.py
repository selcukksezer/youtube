"""
Procedural cinematic background clips (no stock API, no placeholder text).

Used when every stock provider fails for a scene. Output is a 1080x1920
animated abstract backdrop: niche-palette gradient drift + soft drifting
light particles + slow push-in + vignette + film grain. Every scene gets a
different seed/palette rotation so the unique-clip contract still holds.

Everything is a single FFmpeg lavfi graph (no MoviePy, ~1.5x realtime).
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Dict, List, Optional, Sequence, Tuple

import imageio_ffmpeg

import config

# motif -> (gradient palette [4 hex], particle color, gradient type)
_PALETTES: Dict[str, Tuple[Sequence[str], str, str]] = {
    "finance_pulse":    (("0x061224", "0x0d2f55", "0x0a4a3a", "0x03070f"), "0x7fe6b8", "linear"),
    "zodiac_night":     (("0x120a2e", "0x2b1560", "0x4a2a86", "0x07041a"), "0xf1d27a", "radial"),
    "mind_shadow":      (("0x0b0710", "0x2a0f3a", "0x3d1552", "0x050308"), "0xb48cff", "spiral"),
    "dark_archive":     (("0x0a0a0a", "0x1c1a17", "0x2f2b25", "0x050505"), "0xd6c39a", "linear"),
    "imperial_rome":    (("0x1a1208", "0x3b2a10", "0x5c4520", "0x0c0904"), "0xf3d58a", "radial"),
    "breaking_news":    (("0x140505", "0x3a0d0d", "0x5a1717", "0x080202"), "0xff9b8a", "linear"),
    "islamic_devotion": (("0x061a12", "0x0f3a2a", "0x1c5c44", "0x03100a"), "0xf1dc9a", "radial"),
    "confession_story": (("0x0c0f1a", "0x1c2438", "0x2e3a58", "0x06080f"), "0xa8c4ff", "linear"),
    "chat_ui":          (("0x0a1410", "0x123826", "0x1f5a3a", "0x050a08"), "0x9bffc4", "linear"),
    "fact_cards":       (("0x061a2a", "0x0d3a5a", "0x1a5c86", "0x03101a"), "0xa6e4ff", "radial"),
    "lifestyle_product":(("0x1a1410", "0x3a2c20", "0x5a4634", "0x0c0906"), "0xffe1b8", "linear"),
    "story_world":      (("0x0a1020", "0x1c2a55", "0x2f4a86", "0x05081a"), "0xc4d6ff", "spiral"),
    "cinematic_general":(("0x0a0f1a", "0x162238", "0x243a5a", "0x05070d"), "0xb8c8e8", "linear"),
}

_KEYWORD_MOTIF: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"bitcoin|crypto|kripto|trading|candlestick|chart|forex|market|whale|blockchain", re.I), "finance_pulse"),
    (re.compile(r"zodiac|astrolog|horoscope|burç|burc|planet|mercury|retrograde|star|galaxy|nebula|tarot", re.I), "zodiac_night"),
    (re.compile(r"psycholog|manipulat|brain|mind|dark|shadow|noir|liar|lie detect|body language", re.I), "mind_shadow"),
    (re.compile(r"battle|war|soldier|trench|cannon|empire|ottoman|history|historical|archive|ancient", re.I), "dark_archive"),
    (re.compile(r"stoic|marcus|roman|rome|marble|philosoph", re.I), "imperial_rome"),
    (re.compile(r"breaking|news|headline|urgent|flash", re.I), "breaking_news"),
    (re.compile(r"mosque|quran|prayer|dua|islam|prophet", re.I), "islamic_devotion"),
    (re.compile(r"reddit|confession|story|diary", re.I), "confession_story"),
]


def resolve_motif(scene_description: str = "", visual_intent: Optional[dict] = None, niche_id: str = "") -> str:
    """Pick a palette motif from intent motif > niche id > description keywords."""
    if isinstance(visual_intent, dict):
        motif = str(visual_intent.get("continuity_motif") or "").strip()
        if motif in _PALETTES:
            return motif
    nid = (niche_id or "").lower()
    niche_map = {
        "8_crypto": "finance_pulse", "18_astro": "zodiac_night", "7_dark": "mind_shadow",
        "19_hist": "dark_archive", "6_stoic": "imperial_rome", "1_news": "breaking_news",
        "10_relig": "islamic_devotion", "2_reddit": "confession_story", "20_whatsapp": "chat_ui",
        "9_five": "fact_cards", "12_amazon": "lifestyle_product",
    }
    for prefix, motif in niche_map.items():
        if nid.startswith(prefix):
            return motif
    text = " ".join([
        scene_description or "",
        " ".join((visual_intent or {}).get("search_queries") or []) if isinstance(visual_intent, dict) else "",
        str((visual_intent or {}).get("subject") or "") if isinstance(visual_intent, dict) else "",
    ])
    for rx, motif in _KEYWORD_MOTIF:
        if rx.search(text):
            return motif
    return "cinematic_general"


def build_procedural_clip(
    output_path: str,
    duration: float,
    scene_index: int = 0,
    motif: str = "cinematic_general",
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: Optional[int] = None,
) -> Optional[str]:
    """Render one abstract cinematic clip. Returns path or None on failure."""
    w = int(width or getattr(config, "VIDEO_WIDTH", 1080))
    h = int(height or getattr(config, "VIDEO_HEIGHT", 1920))
    r = int(fps or getattr(config, "FPS", 30) or 30)
    dur = max(1.0, float(duration))
    palette, particle, gtype = _PALETTES.get(motif, _PALETTES["cinematic_general"])
    # rotate palette + seed per scene so consecutive fallbacks never hash-collide
    rot = scene_index % len(palette)
    pal = list(palette[rot:]) + list(palette[:rot])
    gtypes = ["linear", "radial", "spiral"]
    gtype = gtypes[(gtypes.index(gtype) + scene_index) % len(gtypes)] if gtype in gtypes else gtype
    seed = 1000 + scene_index * 7919
    zoom_rate = 0.0006 + 0.0002 * (scene_index % 3)
    speed = 0.03 + 0.01 * (scene_index % 4)

    grad = (
        f"gradients=s={w}x{h}:c0={pal[0]}:c1={pal[1]}:c2={pal[2]}:c3={pal[3]}"
        f":n=4:speed={speed:.3f}:type={gtype}:duration={dur:.3f}:rate={r}:seed={seed}"
    )
    life = (
        f"life=s={max(60, w // 8)}x{max(100, h // 8)}:mold=6:r={r}:ratio=0.06:seed={seed}"
        f":death_color=black:life_color={particle}:stitch=0,"
        f"scale={w}:{h}:flags=bicubic,gblur=sigma={max(12, w // 40)}"
    )
    graph = (
        "[0:v]format=gbrp[bg];[1:v]format=gbrp[fx];"
        "[bg][fx]blend=all_mode=screen:all_opacity=0.65,"
        f"zoompan=z='1+{zoom_rate:.5f}*on':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={r},"
        "vignette=PI/4.6,noise=alls=6:allf=t,format=yuv420p"
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
        print(f"    [Procedural] ffmpeg error: {exc}")
        return None
    if res.returncode != 0:
        print(f"    [Procedural] ffmpeg failed: {res.stderr.decode('utf-8', 'ignore')[-300:]}")
        return None
    if os.path.exists(output_path) and os.path.getsize(output_path) > 10_000:
        return output_path
    return None
