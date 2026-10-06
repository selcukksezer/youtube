"""
Niche Guardrails & Anti-Cliche Engine (Verticals v3 / Repo 10 Adaptation).
Features:
1. Forbidden Phrases Stripper — eliminates retention-killing YouTube cliches.
2. Visual Preference/Avoidance Rules — prevents generic smiling stock footage and enforces niche aesthetics.
3. Niche Caption Styling — maps optimal subtitle highlight colors and cadence per niche.
4. Viral Hook Formula Builder — generates contrarian, countdown, prediction, and shock hooks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# Retention-killing phrases forbidden across all Shorts scripts
FORBIDDEN_PHRASES_TR = [
    r"kanalıma abone olun\w*",
    r"abone olmayı unutmayın\w*",
    r"videoyu beğenmeyi unutmayın\w*",
    r"like atmayı unutmayın\w*",
    r"bildirimleri açın\w*",
    r"çan simgesine tıklayın\w*",
    r"hepinize merhaba\w*",
    r"merhaba arkadaşlar\w*",
    r"bu videoda sizlere?\b",
    r"bu videoda\b",
    r"lafı fazla uzatmadan\b",
    r"sözü fazla uzatmadan\b",
    r"hadi videomuza geçelim\b",
    r"hadi başlayalım\b",
    r"hoş geldiniz\b",
]

FORBIDDEN_PHRASES_EN = [
    r"like and subscribe\b",
    r"smash that like button\b",
    r"smash that bell\b",
    r"hit the subscribe button\b",
    r"what'?s up guys\b",
    r"hey everyone\b",
    r"in this video\b",
    r"without further ado\b",
    r"let'?s dive right in\b",
    r"welcome back to my channel\b",
    r"don'?t forget to subscribe\b",
    r"leave a comment down below\b",
]

# Niche-specific visual intelligence (Avoid vs Prefer)
NICHE_VISUAL_GUIDELINES: Dict[str, Dict[str, List[str]]] = {
    "tech": {
        "prefer": [
            "dark neon server room with blinking led lights",
            "close-up glowing computer code on high-end monitor",
            "minimalist sleek futuristic gadget on dark backdrop",
            "holographic futuristic interface with glowing data nodes",
            "macro silicon microchip circuit board shallow depth of field",
        ],
        "avoid": [
            "smiling person at generic laptop",
            "generic corporate boardroom meeting",
            "clipart or illustrated 2D icons",
            "handshakes in sunny office",
        ],
        "caption_color": "#00FF88",  # Cyber Neon Green
        "accent_music": "ambient electronic dark tech",
    },
    "finance": {
        "prefer": [
            "financial stock candlestick charts glowing red and green",
            "vault door opening with dramatic volumetric lighting",
            "macro shot counting crisp stacks of currency",
            "wall street trading floor blurred motion time lapse",
            "minimalist luxury watch and private jet silhouette",
        ],
        "avoid": [
            "cartoon piggy bank",
            "smiling generic banker in cheap suit",
            "confusing multi-colored pie charts",
        ],
        "caption_color": "#FFD700",  # Gold
        "accent_music": "fast cinematic tension heartbeat",
    },
    "12_amazon_affiliate": {
        "prefer": [
            "hands-on macro demonstration of smart home gadget",
            "satisfying clean cable organization setup before and after",
            "water-resistant portable tool being tested underwater",
            "aesthetic organized kitchen countertop with modern alet",
            "cinematic vertical product unboxing on matte black surface",
        ],
        "avoid": [
            "blurry low-res smartphone screenshot",
            "empty shopping cart in supermarket",
            "generic warehouse forklift",
        ],
        "caption_color": "#FF9900",  # Amazon Orange
        "accent_music": "upbeat energetic modern lofi",
    },
    "2_reddit_confessions": {
        "prefer": [
            "cinematic silhouette standing by rain-streaked window",
            "dimly lit moody living room late at night",
            "phone screen vibrating on nightstand in the dark",
            "dramatic shadows across worried face looking away",
        ],
        "avoid": [
            "bright sunny beach",
            "laughing groups at party",
            "corporate office presentations",
        ],
        "caption_color": "#FF4500",  # Reddit Orange/Red
        "accent_music": "suspenseful dark piano ambient",
    },
    "6_stoic_philosophy": {
        "prefer": [
            "marble bust of Marcus Aurelius in dramatic chiaroscuro light",
            "solitary figure walking through misty mountain landscape",
            "hourglass with sand slipping through in slow motion",
            "ancient Roman temple ruins against storm clouds",
        ],
        "avoid": [
            "modern neon party lights",
            "busy highway traffic",
            "cartoon illustrations",
        ],
        "caption_color": "#E0F7FA",  # Pure Ice White / Cyan
        "accent_music": "epic ancient drums and deep strings",
    },
    "1_news_flash": {
        "prefer": [
            "breaking news broadcast studio monitors",
            "press conference camera flashes and microphones",
            "emergency siren blurred city night atmosphere",
            "dramatic satellite earth zoom and crisis headlines",
        ],
        "avoid": [
            "smiling influencers",
            "peaceful sunny beaches",
            "cartoon illustrations",
        ],
        "caption_color": "#FF1744",  # High-Alert Red
        "accent_music": "urgent dramatic pulse percussion",
        "has_ticker": True,
    },
    "education": {
        "prefer": [
            "antique historical documents and wax seals",
            "chalkboard filled with intricate scientific equations",
            "macro footage of vintage globe and navigational maps",
            "museum archive artifacts in dramatic lighting",
        ],
        "avoid": [
            "generic smiling student classroom stock",
            "low-resolution clipart",
            "blank white backgrounds",
        ],
        "caption_color": "#FFD600",  # Vivid Amber
        "accent_music": "mysterious investigative documentary piano",
    },
    "fitness": {
        "prefer": [
            "chalk dust flying off heavy barbell in dramatic gym rim lighting",
            "athlete sprinting in high contrast black and white",
            "biomechanical anatomical muscle activation diagram",
            "sweat dripping close-up intense workout focus",
        ],
        "avoid": [
            "smiling people with 1kg plastic pink dumbbells",
            "unrealistic weight loss before-after cartoons",
            "empty gym with flat white fluorescent lighting",
        ],
        "caption_color": "#FF5722",  # Energetic Blaze Orange
        "accent_music": "high energy aggressive phonk bass",
    },
    "comedy": {
        "prefer": [
            "exaggerated facial expressions and intense eye contact",
            "comedic zoom-in on absurd object or mistake",
            "relatable awkward everyday situations in crisp lighting",
        ],
        "avoid": [
            "stiff corporate models",
            "unrelated melancholic landscape drone shots",
        ],
        "caption_color": "#FFEB3B",  # Vibrant Punch Yellow
        "accent_music": "quirky upbeat acoustic bounce",
    },
    "science": {
        "prefer": [
            "space telescope deep field nebula in brilliant color",
            "electron microscope cellular division time lapse",
            "quantum laboratory laser beams refracting through glass",
        ],
        "avoid": [
            "generic cartoon chemistry flasks bubbling green liquid",
            "childish illustrated science doodles",
        ],
        "caption_color": "#00E5FF",  # Sci-Fi Electric Cyan
        "accent_music": "ambient ethereal cosmic soundscape",
    },
}



def clean_forbidden_phrases(script_text: str, lang: str = "tr") -> str:
    """
    Remove all retention-destroying phrases and filler words from narration.
    Cleans both Turkish and English patterns.
    """
    patterns = FORBIDDEN_PHRASES_TR if lang.lower().startswith("tr") else FORBIDDEN_PHRASES_EN
    cleaned = script_text

    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    # Clean double spaces and stray punctuation
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.:!?])", r"\1", cleaned)
    return cleaned.strip()


def get_niche_visual_rules(niche_id: str) -> Dict[str, Any]:
    """Retrieve visual prefer and avoid guidelines for a niche."""
    key = niche_id.lower().strip()
    for n_key, rules in NICHE_VISUAL_GUIDELINES.items():
        if n_key in key or key in n_key:
            return rules
    return {
        "prefer": ["cinematic high quality vertical b-roll", "dramatic lighting with shallow depth of field"],
        "avoid": ["blurry footage", "clipart", "cheesy stock smiling"],
        "caption_color": "#FFD700",
        "accent_music": "cinematic ambient",
    }


def format_niche_prompt_guardrails(niche_id: str, lang: str = "tr") -> str:
    """Format prompt guidelines for LLM script generation."""
    rules = get_niche_visual_rules(niche_id)
    prefers = ", ".join(rules.get("prefer", [])[:3])
    avoids = ", ".join(rules.get("avoid", [])[:3])

    if lang.lower().startswith("tr"):
        return (
            f"\n\n[NİŞ VE RETENTION KORUMA KURALLARI (Verticals v3 / Repo 10)]:\n"
            f"- YASAK KALIPLAR: 'Abone olun', 'Like atın', 'Bu videoda', 'Lafı uzatmadan' gibi kalıplar KESİNLİKLE YASAK.\n"
            f"- İLK 3 SANİYE: Doğrudan çatışma ve şok edici kanca ile başla; selamlaşma veya giriş cümlesi yapma.\n"
            f"- TERCİH EDİLEN GÖRSELLER: {prefers}\n"
            f"- KAÇINILACAK GÖRSELLER: {avoids}\n"
        )
    return (
        f"\n\n[NICHE & RETENTION GUARDRAILS (Verticals v3 / Repo 10)]:\n"
        f"- FORBIDDEN PHRASES: 'Like and subscribe', 'In this video', 'Without further ado' are STRICTLY FORBIDDEN.\n"
        f"- FIRST 3 SECONDS: Jump straight into the core conflict or contrarian hook; no greetings or throat-clearing.\n"
        f"- PREFERRED VISUALS: {prefers}\n"
        f"- AVOID VISUALS: {avoids}\n"
    )


# Specific forbidden terms per niche (ported from youtube-shorts-pipeline YAMLs)
NICHE_FORBIDDEN_TERMS: Dict[str, List[str]] = {
    "finance": [
        "financial advice", "guaranteed returns", "get rich quick", "not financial advice",
        "to the moon", "yatırım tavsiyesi", "garanti kazanç", "zengin olma yolu",
    ],
    "fitness": [
        "lose 10 pounds in 3 days", "miracle diet", "3 günde 5 kilo", "mucize diyet",
    ],
    "tech": [
        "game changer", "revolutionary technology", "will blow your mind", "akıllara durgunluk",
    ],
}


def validate_script_niche_compliance(
    script_text: str, niche_id: str, lang: str = "tr"
) -> Dict[str, Any]:
    """
    Validates script against both global retention rules and niche-specific forbidden phrases.
    Returns compliance boolean, detected violations, cleaned script, and visual rules.
    """
    violations: List[str] = []
    text_lower = script_text.lower()

    # Check global forbidden phrases
    global_pats = FORBIDDEN_PHRASES_TR if lang.lower().startswith("tr") else FORBIDDEN_PHRASES_EN
    for pat in global_pats:
        match = re.search(pat, text_lower)
        if match:
            violations.append(f"Global forbidden cliché: '{match.group(0)}'")

    # Check niche-specific forbidden phrases
    niche_key = niche_id.lower().strip()
    for n_key, terms in NICHE_FORBIDDEN_TERMS.items():
        if n_key in niche_key:
            for term in terms:
                if term in text_lower:
                    violations.append(f"Niche forbidden phrase ({n_key}): '{term}'")

    cleaned = clean_forbidden_phrases(script_text, lang=lang)
    for n_key, terms in NICHE_FORBIDDEN_TERMS.items():
        if n_key in niche_key:
            for term in terms:
                cleaned = re.sub(re.escape(term), "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return {
        "compliant": len(violations) == 0,
        "violations": violations,
        "cleaned_text": cleaned,
        "visual_rules": get_niche_visual_rules(niche_id),
    }

