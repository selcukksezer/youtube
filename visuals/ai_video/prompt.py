"""Turkish narration → English cinematic / kids-cartoon Shorts prompt (9:16)."""
from __future__ import annotations

import os
import re
from typing import Optional

from .kids_safety import (
    check_kids_prompt_safety,
    is_kids_niche,
    kids_style_block,
    sanitize_kids_prompt,
)

_RELIGIOUS_HINTS = re.compile(
    r"\b(allah|peygamber|hz\.?|muhammed|isa|musa|kuran|namaz|cami|islam|dua|ayet)\b",
    re.I,
)
_CRYPTO_HINTS = re.compile(
    r"\b(bitcoin|btc|eth|crypto|blockchain|token|nft|borsa|grafik|chart|whale)\b",
    re.I,
)
_COPYRIGHT_BAN = re.compile(
    r"\b(mickey|disney|marvel|pokemon|naruto|goku|elsa|spiderman|batman|harry\s*potter|"
    r"star\s*wars|minecraft|fortnite|gta|nike|adidas|apple\s*logo)\b",
    re.I,
)

# Light lexical TR→EN for common Shorts nouns (no LLM required)
_LEX = {
    "gökyüzü": "sky",
    "deniz": "ocean waves",
    "şehir": "city skyline",
    "gece": "night",
    "güneş": "sunlight",
    "ay": "moon",
    "yıldız": "stars",
    "orman": "forest",
    "dağ": "mountains",
    "yağmur": "rain",
    "ateş": "fire embers",
    "su": "water",
    "altın": "golden light",
    "para": "money floating",
    "grafik": "financial chart",
    "yükseliş": "rising candlesticks",
    "düşüş": "falling markets",
    "teknoloji": "futuristic technology",
    "uzay": "deep space nebula",
    "ışık": "volumetric light rays",
    "kalp": "abstract glowing heart shape",
    "hayvan": "friendly cartoon animal",
    "kedi": "cute cartoon cat",
    "köpek": "friendly cartoon dog",
    "kuş": "colorful cartoon bird",
    "alfabe": "alphabet letters floating softly",
    "harf": "friendly letter character",
    "sayı": "colorful number characters",
    "renk": "bright rainbow colors",
    "arkadaş": "cartoon animal friends",
    "paylaşmak": "sharing toys kindly",
    "dürüstlük": "honest cartoon moment",
}


def _niche_guard(niche_id: str, text: str) -> str:
    niche = (niche_id or "").lower()
    low = text.lower()
    extras = []
    if "relig" in niche or "islam" in niche or "din" in niche or _RELIGIOUS_HINTS.search(low):
        extras.append(
            "No faces of prophets or sacred figures. Abstract calligraphy, mosque silhouette, "
            "soft lantern light, geometric islamic patterns only."
        )
    if "crypto" in niche or "finans" in niche or _CRYPTO_HINTS.search(low):
        extras.append(
            "Abstract data visualization, glowing candlestick charts, neon HUD overlays, "
            "no real brand logos."
        )
    if is_kids_niche(niche_id):
        extras.append(
            "Soft educational kids story beat, wholesome moral, no villains with weapons, "
            "no scary faces."
        )
    return " ".join(extras)


def resolve_style_preset(niche_id: str = "", style_preset: Optional[str] = None) -> str:
    if style_preset:
        return style_preset.strip().lower()
    env = (os.getenv("AI_VIDEO_STYLE_PRESET") or "").strip().lower()
    if env:
        return env
    if is_kids_niche(niche_id):
        return "kids_cartoon"
    return "cinematic"


def build_cinematic_prompt(
    narration: str = "",
    scene_description: str = "",
    niche_id: str = "",
    aspect: str = "9:16",
    style_preset: Optional[str] = None,
) -> str:
    """
    Build English T2V prompt. For kids niches uses kids_cartoon preset.
    Raises ValueError if kids safety filter rejects the text.
    """
    raw = " ".join(x for x in (scene_description, narration) if x).strip()
    style = resolve_style_preset(niche_id, style_preset)

    if style == "kids_cartoon" or is_kids_niche(niche_id):
        ok, reason = check_kids_prompt_safety(raw)
        if not ok:
            raise ValueError(f"kids_prompt_blocked:{reason}")
        raw = sanitize_kids_prompt(raw)

    raw = _COPYRIGHT_BAN.sub("original character", raw)
    words = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9']+", raw)
    mapped = []
    for w in words[:40]:
        mapped.append(_LEX.get(w.lower(), w if re.match(r"^[A-Za-z]", w) else ""))
    core = " ".join(x for x in mapped if x).strip()
    guard = _niche_guard(niche_id, raw)

    if style == "kids_cartoon":
        core = core or "friendly cartoon forest animals learning to share"
        prompt = (
            f"{kids_style_block(aspect)} Subject: {core}. {guard}"
        )
    else:
        core = core or "cinematic abstract motion background"
        aspect_note = "vertical 9:16 smartphone framing, centered subject," if aspect == "9:16" else ""
        prompt = (
            f"Cinematic short clip, {aspect_note} photoreal lighting, subtle camera push-in, "
            f"shallow depth of field, high detail, no text overlay, no watermark, no subtitles. "
            f"Subject: {core}. {guard}"
        )
    return re.sub(r"\s+", " ", prompt).strip()[:1200]
