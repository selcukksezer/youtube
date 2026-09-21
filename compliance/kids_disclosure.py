"""Made for Kids disclosure + no data-collection upload metadata helpers."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

DISCLOSURE_TR = (
    "Bu video çocuklar için hazırlanmıştır (Made for Kids). "
    "Yapay zekâ destekli çizgi animasyon içerir; gerçek çocuk görüntüsü yoktur. "
    "Kişisel veri toplamaz, yorum/üye etkileşimi istemez."
)

DISCLOSURE_EN = (
    "This video is Made for Kids. It uses AI-assisted cartoon animation; "
    "no real children are depicted. No personal data collection; comments/memberships disabled by policy."
)


def is_made_for_kids_niche(niche_id: str = "") -> bool:
    try:
        from visuals.ai_video.kids_safety import is_kids_niche
        return is_kids_niche(niche_id)
    except Exception:
        n = (niche_id or "").lower()
        return "kids" in n or "çocuk" in n or "cocuk" in n


def kids_description_suffix(language: str = "tr") -> str:
    return DISCLOSURE_TR if (language or "tr").startswith("tr") else DISCLOSURE_EN


def apply_kids_upload_fields(
    *,
    niche_id: str = "",
    description: str = "",
    tags: Optional[List[str]] = None,
    language: str = "tr",
    force: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Hard-code Made for Kids when niche is kids animation.
    Strips engagement CTAs that imply data collection.
    """
    mfk = bool(force) if force is not None else is_made_for_kids_niche(niche_id)
    desc = description or ""
    tag_list = list(tags or [])
    if mfk:
        suffix = kids_description_suffix(language)
        if "Made for Kids" not in desc and "çocuklar için" not in desc.lower():
            desc = (desc.rstrip() + "\n\n" + suffix).strip()
        # Avoid comment-bait tags
        ban = {"comment", "yorum", "subscribe", "abone", "like", "beğen"}
        tag_list = [t for t in tag_list if t and t.lower().lstrip("#") not in ban]
        if "MadeForKids" not in tag_list and "made for kids" not in [t.lower() for t in tag_list]:
            tag_list = (tag_list + ["MadeForKids", "kids animation"])[:30]
    return {
        "selfDeclaredMadeForKids": mfk,
        "description": desc,
        "tags": tag_list,
        "suppress_pinned_comment": mfk,  # comments disabled on MFK anyway
        "collect_viewer_data": False if mfk else None,
    }
