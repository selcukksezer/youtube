"""Kids-content prompt safety: reject unsafe prompts before AI video generation."""
from __future__ import annotations

import re
from typing import Optional, Tuple

# Hard bans: real children, sexualization, violence, horror, dark psych, school targeting
_UNSAFE = re.compile(
    r"("
    r"real\s*child|photoreal(?:istic)?\s*(?:child|kid|toddler|baby)|"
    r"child\s*face|kid\s*face|çocuk\s*yüz|gerçek\s*çocuk|"
    r"school\s*(?:shoot|massacre|attack)|okul\s*(?:saldırı|katliam)|"
    r"nude|naked|sexual|porn|onlyfans|groom|"
    r"gore|blood(?:y)?|murder|kill(?:ing)?|torture|suicide|"
    r"jump\s*scare|horror|scary\s*demon|possession|slender|"
    r"dark\s*psych|manipulat(?:e|ion)\s*child|"
    r"weapon|gun|knife\s*fight|bomb|"
    r"drug|alcohol\s*for\s*kids"
    r")",
    re.I,
)

_COPYRIGHT_KIDS = re.compile(
    r"\b(mickey|minnie|elsa|anna|frozen|peppa|paw\s*patrol|barbie|"
    r"spiderman|batman|pokemon|pikachu|disney|pixar\s*character|"
    r"cocomelon|blippi|baby\s*shark\s*official)\b",
    re.I,
)

KIDS_CARTOON_STYLE = (
    "Bright soft kids cartoon animation, friendly 2D or Pixar-like 3D stylized, "
    "pastel colors, gentle round shapes, warm daylight, cheerful and calm mood, "
    "no photoreal humans, no real children, no text overlay, no watermark, "
    "vertical 9:16 framing, safe for ages 3–8."
)

KIDS_NEGATIVE = (
    "photoreal child, real kid face, horror, gore, blood, weapons, jump scare, "
    "dark atmosphere, sexualized, scary, nightmare, realistic human skin pores"
)


def is_kids_niche(niche_id: str = "") -> bool:
    n = (niche_id or "").lower()
    return any(
        k in n
        for k in (
            "kids_animation",
            "36_kids",
            "kids_cartoon",
            "cocuk_animasyon",
            "çocuk_animasyon",
            "kids_edu",
        )
    )


def check_kids_prompt_safety(text: str) -> Tuple[bool, str]:
    """
    Return (ok, reason). ok=False → do not send to providers.
    """
    raw = (text or "").strip()
    if not raw:
        return True, ""
    m = _UNSAFE.search(raw)
    if m:
        return False, f"unsafe_kids_term:{m.group(0)}"
    return True, ""


def sanitize_kids_prompt(text: str) -> str:
    """Strip copyright kids IP names; keep structure."""
    cleaned = _COPYRIGHT_KIDS.sub("friendly original cartoon character", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def assert_kids_safe_or_raise(text: str) -> None:
    ok, reason = check_kids_prompt_safety(text)
    if not ok:
        raise ValueError(f"kids_prompt_blocked:{reason}")


def kids_style_block(aspect: str = "9:16") -> str:
    aspect_note = "vertical 9:16," if aspect in ("9:16", "9/16", "portrait") else ""
    return f"{KIDS_CARTOON_STYLE} {aspect_note} Avoid: {KIDS_NEGATIVE}."


def filter_or_rewrite(text: str, *, niche_id: str = "") -> Optional[str]:
    """
    If kids niche and unsafe → None (caller skips AI).
    Else sanitize copyright and return text.
    """
    if is_kids_niche(niche_id) or "kid" in (text or "").lower() or "çocuk" in (text or "").lower():
        ok, _ = check_kids_prompt_safety(text)
        if not ok:
            return None
    return sanitize_kids_prompt(text)
