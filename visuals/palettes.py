"""Niche family -> palette + motion profile + preferred sources. Drives procedural graphics and ranking."""
from __future__ import annotations

from typing import Dict, List


# motion profile keys: slow_zoom | pulse | reveal | drift | fast_cut
PALETTES: Dict[str, Dict] = {
    "religious": {
        "colors": [(18, 24, 42), (52, 36, 20), (140, 96, 32)],
        "accent": (236, 196, 110),
        "text": (250, 244, 228),
        "motion": "slow_zoom",
        "particles": "dust",
        "sources": ["pexels", "wikimedia", "pixabay", "openverse", "coverr"],
    },
    "stoic": {
        "colors": [(20, 20, 24), (48, 42, 36), (92, 78, 60)],
        "accent": (214, 190, 150),
        "text": (240, 236, 228),
        "motion": "slow_zoom",
        "particles": "dust",
        "sources": ["pexels", "wikimedia", "pixabay", "openverse"],
    },
    "crypto": {
        "colors": [(6, 10, 18), (10, 30, 34), (4, 60, 44)],
        "accent": (38, 214, 132),
        "accent_alt": (232, 66, 82),
        "text": (240, 248, 244),
        "motion": "pulse",
        "particles": "grid",
        "sources": ["pexels", "pixabay", "coverr", "wikimedia"],
    },
    "mystery": {
        "colors": [(4, 4, 8), (14, 10, 26), (30, 12, 40)],
        "accent": (150, 110, 220),
        "text": (226, 220, 240),
        "motion": "reveal",
        "particles": "fog",
        "sources": ["nasa", "pexels", "wikimedia", "pixabay", "openverse"],
    },
    "dark": {
        "colors": [(6, 6, 8), (22, 14, 20), (48, 20, 28)],
        "accent": (220, 60, 80),
        "text": (238, 230, 232),
        "motion": "reveal",
        "particles": "fog",
        "sources": ["pexels", "pixabay", "wikimedia", "openverse"],
    },
    "news": {
        "colors": [(8, 12, 28), (12, 30, 70), (150, 20, 30)],
        "accent": (255, 214, 0),
        "text": (255, 255, 255),
        "motion": "fast_cut",
        "particles": "grid",
        "sources": ["pexels", "pixabay", "wikimedia", "archive_org", "coverr"],
    },
    "astrology": {
        "colors": [(10, 6, 30), (40, 16, 70), (90, 40, 130)],
        "accent": (255, 200, 120),
        "text": (246, 240, 255),
        "motion": "drift",
        "particles": "stars",
        "sources": ["nasa", "pexels", "pixabay", "openverse"],
    },
    "history": {
        "colors": [(20, 16, 12), (60, 44, 28), (110, 80, 44)],
        "accent": (220, 180, 120),
        "text": (244, 238, 226),
        "motion": "slow_zoom",
        "particles": "dust",
        "sources": ["wikimedia", "archive_org", "pexels", "openverse"],
    },
    "science": {
        "colors": [(4, 10, 24), (8, 40, 70), (10, 90, 120)],
        "accent": (90, 220, 255),
        "text": (240, 250, 255),
        "motion": "drift",
        "particles": "stars",
        "sources": ["nasa", "pexels", "wikimedia", "pixabay"],
    },
    "quiz": {
        "colors": [(20, 10, 50), (60, 20, 110), (240, 80, 40)],
        "accent": (255, 230, 60),
        "text": (255, 255, 255),
        "motion": "pulse",
        "particles": "grid",
        "sources": ["pexels", "pixabay", "openverse"],
    },
    "general": {
        "colors": [(10, 12, 20), (24, 30, 52), (40, 60, 90)],
        "accent": (120, 200, 255),
        "text": (244, 246, 250),
        "motion": "drift",
        "particles": "dust",
        "sources": ["pexels", "pixabay", "wikimedia", "coverr", "openverse"],
    },
}

_FAMILY_ALIASES = {
    "reddit": "dark",
    "whatsapp": "dark",
    "product": "general",
    "entertainment": "general",
    "football": "news",
    "wealth": "stoic",
    "gaming": "quiz",
}

_NICHE_ID_FAMILY_HINT = [
    ("religious", "religious"),
    ("stoic", "stoic"),
    ("crypto", "crypto"),
    ("mystery", "mystery"),
    ("dark_psych", "dark"),
    ("news", "news"),
    ("astrology", "astrology"),
    ("historical", "history"),
    ("before_after", "history"),
    ("five_facts", "science"),
    ("myths", "science"),
    ("quiz", "quiz"),
    ("guess", "quiz"),
    ("would_you", "quiz"),
    ("emoji", "quiz"),
]


def family_for_niche(niche_id: str) -> str:
    """Resolve a niche id (e.g. '10_religious_quotes') to a palette family."""
    nid = (niche_id or "").lower()
    try:
        from niche_templates import get_niche_family
        fam = get_niche_family(niche_id)
        fam = _FAMILY_ALIASES.get(fam, fam)
        if fam in PALETTES and fam != "general":
            return fam
    except Exception:
        pass
    for hint, fam in _NICHE_ID_FAMILY_HINT:
        if hint in nid:
            return fam
    return "general"


def palette_for(niche_id_or_family: str) -> Dict:
    key = niche_id_or_family if niche_id_or_family in PALETTES else family_for_niche(niche_id_or_family)
    return PALETTES.get(key, PALETTES["general"])


def preferred_sources(niche_id_or_family: str) -> List[str]:
    return list(palette_for(niche_id_or_family)["sources"])
