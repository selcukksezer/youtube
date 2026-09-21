"""Turkish narration / niche → English SHOT query ladder (not keyword soup).

Grammar: subject + action + setting + lighting/mood.
Ban: "cinematic 4k", "atmospheric", "ancient rome" spam, Stoic fallbacks for religious.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

from .palettes import family_for_niche

# Noise tokens that inflate stock APIs with junk
_BAN_TOKENS = re.compile(
    r"\b(cinematic|4k|8k|uhd|atmospheric|epic|viral|trending|aesthetic|"
    r"beautiful|amazing|stunning|stock footage|b-?roll)\b",
    re.I,
)

# TR → EN concept stubs (extend as needed; optional Gemini can enrich later)
_TR_EN: Dict[str, str] = {
    "cami": "mosque", "camii": "mosque", "kubbe": "dome", "minare": "minaret",
    "kuran": "quran book", "kur'an": "quran book", "namaz": "muslim prayer",
    "dua": "hands praying", "tesbih": "prayer beads", "ramazan": "ramadan lantern",
    "iman": "faith light", "sabır": "calm patience", "şükür": "gratitude sunrise",
    "bitcoin": "bitcoin candle chart", "kripto": "cryptocurrency trading screen",
    "borsa": "stock market ticker", "grafik": "financial chart screen",
    "balina": "whale underwater deep", "blockchain": "digital network nodes",
    "gizem": "foggy forest night", "sır": "locked door darkness",
    "uzay": "deep space nebula", "galaxy": "galaxy stars",
    "psikoloji": "silhouette thinking shadow", "beyin": "brain anatomy dark",
    "manipülasyon": "puppet strings shadow", "yalan": "lie detector metaphor",
    "stoa": "marble statue philosophy", "marcus": "roman marble bust",
    "tarih": "ancient manuscript archive", "savaş": "historical battlefield fog",
    "fitness": "gym workout silhouette", "koşu": "runner sunrise road",
    "haber": "news studio desk", "acil": "breaking news red light",
}

_FAMILY_BROLL: Dict[str, List[str]] = {
    "religious": [
        "mosque interior dome soft light",
        "quran open pages warm light",
        "muslim hands raised in prayer",
        "islamic geometric pattern closeup",
    ],
    "crypto": [
        "cryptocurrency trading desk monitors",
        "bitcoin coin macro dark desk",
        "digital candlestick chart screen",
        "server room blue lights",
    ],
    "mystery": [
        "fog forest night path",
        "abandoned hallway dim light",
        "deep space stars slow drift",
        "locked metal door darkness",
    ],
    "dark": [
        "shadow silhouette window night",
        "rain city street neon reflection",
        "closeup eye darkness",
        "empty chair interrogation room",
    ],
    "stoic": [
        "roman marble bust museum",
        "stone columns mediterranean light",
        "ancient parchment closeup",
        "olive tree wind greece",
    ],
    "news": [
        "newsroom desk monitors",
        "city skyline dusk traffic",
        "press conference microphones",
        "newspaper printing press",
    ],
    "history": [
        "old map parchment closeup",
        "museum archive shelves",
        "black and white historical film grain",
        "stone ruins golden hour",
    ],
    "science": [
        "laboratory glassware blue light",
        "earth from space nasa",
        "microscope lens closeup",
        "particle trails abstract",
    ],
    "astrology": [
        "night sky milky way",
        "telescope observatory dome",
        "constellation star trails",
        "moon surface crater",
    ],
    "quiz": [
        "neon question mark dark",
        "countdown timer screen",
        "crowd cheering stadium lights",
        "chalkboard equations closeup",
    ],
    "general": [
        "slow aerial landscape dusk",
        "abstract light particles dark",
        "architectural detail concrete",
        "ocean waves aerial calm",
    ],
}

# Religious must never pull Stoic/Roman
_RELIGIOUS_BAN = re.compile(
    r"\b(marcus|aurelius|roman|rome|stoic|stoicism|colosseum|gladiator|caesar)\b",
    re.I,
)

_CRYPTO_BAN = re.compile(
    r"\b(get rich|guaranteed profit|buy now|100x|moonshot tip)\b",
    re.I,
)


def _clean(q: str) -> str:
    q = _BAN_TOKENS.sub(" ", q or "")
    q = re.sub(r"\s+", " ", q).strip(" ,.-")
    return q[:90]


def _translate_blob(text: str) -> str:
    low = (text or "").lower()
    hits = []
    for tr, en in _TR_EN.items():
        if tr in low:
            hits.append(en)
    if hits:
        return " ".join(hits[:4])
    # latin/ascii leftovers
    ascii_words = re.findall(r"[a-zA-Z]{3,}", text or "")
    return " ".join(ascii_words[:6]) if ascii_words else ""


def build_shot_queries(
    narration: str = "",
    scene_description: str = "",
    niche_id: str = "",
    visual_intent: Optional[dict] = None,
    max_queries: int = 5,
) -> List[str]:
    """Return ranked EN shot queries: specific → generic → niche b-roll."""
    family = family_for_niche(niche_id)
    intent = visual_intent if isinstance(visual_intent, dict) else {}
    subject = str(intent.get("subject") or "").strip()
    action = str(intent.get("action") or intent.get("motion") or "").strip()
    setting = str(intent.get("setting") or intent.get("location") or "").strip()
    lighting = str(intent.get("lighting") or intent.get("mood") or "").strip()

    blob = " ".join([narration or "", scene_description or "", subject, action, setting])
    concepts = _translate_blob(blob)

    ladder: List[str] = []

    # 1) Existing intent queries (cleaned)
    for q in (intent.get("search_queries") or []):
        cq = _clean(str(q))
        if cq:
            ladder.append(cq)

    # 2) Shot grammar from parts
    parts = [p for p in (subject, action, setting, lighting) if p]
    if parts:
        ladder.append(_clean(" ".join(parts)))
    elif concepts:
        ladder.append(_clean(f"{concepts} soft natural light"))

    # 3) Concept-only
    if concepts:
        ladder.append(_clean(concepts))

    # 4) Niche b-roll ladder
    for b in _FAMILY_BROLL.get(family, _FAMILY_BROLL["general"]):
        ladder.append(b)

    # Dedup + bans
    out: List[str] = []
    seen = set()
    for q in ladder:
        q = _clean(q)
        if len(q) < 6:
            continue
        key = q.lower()
        if key in seen:
            continue
        if family == "religious" and _RELIGIOUS_BAN.search(q):
            continue
        if family == "crypto" and _CRYPTO_BAN.search(q):
            continue
        seen.add(key)
        out.append(q)
        if len(out) >= max_queries:
            break
    return out or list(_FAMILY_BROLL.get(family, _FAMILY_BROLL["general"])[:3])


def validate_query_list(queries: Sequence[str], niche_id: str = "") -> List[str]:
    """Drop banned tokens / stoic bleed for religious."""
    family = family_for_niche(niche_id)
    clean: List[str] = []
    for q in queries or []:
        cq = _clean(str(q))
        if not cq:
            continue
        if family == "religious" and _RELIGIOUS_BAN.search(cq):
            continue
        clean.append(cq)
    return clean
