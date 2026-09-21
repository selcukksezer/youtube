"""Turkish narration → English cinematic Shorts prompt (9:16, no IP / no prophet faces)."""
from __future__ import annotations

import re
from typing import Optional

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
    return " ".join(extras)


def build_cinematic_prompt(
    narration: str = "",
    scene_description: str = "",
    niche_id: str = "",
    aspect: str = "9:16",
) -> str:
    raw = " ".join(x for x in (scene_description, narration) if x).strip()
    raw = _COPYRIGHT_BAN.sub("original character", raw)
    # Prefer English tokens from lexicon when Turkish words appear
    words = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9']+", raw)
    mapped = []
    for w in words[:40]:
        mapped.append(_LEX.get(w.lower(), w if re.match(r"^[A-Za-z]", w) else ""))
    core = " ".join(x for x in mapped if x).strip() or "cinematic abstract motion background"
    guard = _niche_guard(niche_id, raw)
    aspect_note = "vertical 9:16 smartphone framing, centered subject," if aspect == "9:16" else ""
    prompt = (
        f"Cinematic short clip, {aspect_note} photoreal lighting, subtle camera push-in, "
        f"shallow depth of field, high detail, no text overlay, no watermark, no subtitles. "
        f"Subject: {core}. {guard}"
    )
    return re.sub(r"\s+", " ", prompt).strip()[:1200]
