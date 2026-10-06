"""
Bölüm 8.3: Şeffaf AI Açıklama ve Kaynakça Bloğu Üretimi
(Transparent AI Disclosure & Visual Sources Attribution Engine)

YouTube'un "Sentetik / Değiştirilmiş İçerik" politikasına ve ticari telif kurallarına tam uyum:
- Açıklama kutusu için otomatik lisans ve yapay zeka bilgilendirme metni
- Stok ve AI görsel kaynaklarının (Pexels, Pixabay, Pollinations/Flux, Wikimedia) tekil ID ve lisans atıfları
- Çift eklemeyi önleyen (idempotent) açıklama zenginleştirici
"""
from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Sequence, Union, Set


# Kanonik sağlayıcı isimleri ve lisans formatlayıcıları
PROVIDER_DISPLAY_NAMES = {
    "pexels": "Pexels",
    "pixabay": "Pixabay",
    "unsplash": "Unsplash",
    "pollinations": "Pollinations AI",
    "flux": "Flux AI",
    "flux_schnell": "Flux Schnell",
    "flux_dev": "Flux Dev",
    "dalle": "DALL-E",
    "wikimedia": "Wikimedia Commons",
    "wikipedia": "Wikipedia / Wikimedia",
    "procedural": "Procedural Graphics Engine",
    "whiteboard": "Whiteboard Animation Engine",
    "ai_generated": "AI Visual Synthesis",
}


def _extract_id_from_url_or_raw(raw_id: Any, url: str) -> str:
    if raw_id and str(raw_id).strip() and str(raw_id).strip().lower() != "none":
        return str(raw_id).strip()
    u = str(url or "").strip()
    if not u:
        return ""
    # Pexels video or photo ID from URL (e.g. /video/12345/ or /photos/12345/)
    m = re.search(r"/(?:video|videos|photo|photos)/(\d+)", u)
    if m:
        return m.group(1)
    # Pixabay ID from URL (e.g. -12345/)
    m_pix = re.search(r"-(\d+)/?$", u)
    if m_pix:
        return m_pix.group(1)
    return ""


def format_visual_source_item(clip_or_asset: Dict[str, Any]) -> str:
    """
    Format a single clip/asset into a standard attribution line:
    - Pexels: ID #9029355 (Pexels License)
    - Pollinations AI: Flux SDXL (Generated Asset)
    - Pixabay: ID #456123 (Pixabay License)
    - Wikimedia Commons: Topic Title (CC-BY-SA 4.0)
    """
    if not isinstance(clip_or_asset, dict):
        return ""

    provider_raw = str(
        clip_or_asset.get("provider")
        or clip_or_asset.get("source")
        or clip_or_asset.get("engine")
        or ""
    ).strip().lower()

    source_url = str(clip_or_asset.get("source_url") or clip_or_asset.get("url") or "").strip()
    raw_id = clip_or_asset.get("asset_id") or clip_or_asset.get("id") or clip_or_asset.get("media_id")
    asset_id = _extract_id_from_url_or_raw(raw_id, source_url)
    title = str(clip_or_asset.get("title") or "").strip()

    lic_obj = clip_or_asset.get("license") or {}
    lic_name = ""
    if isinstance(lic_obj, dict):
        lic_name = str(lic_obj.get("name") or lic_obj.get("type") or "").strip()
    elif isinstance(lic_obj, str):
        lic_name = lic_obj.strip()

    # Determine provider category
    if "pexels" in provider_raw or "pexels.com" in source_url:
        lic_label = "Pexels License"
        id_str = f"ID #{asset_id}" if asset_id else (f"'{title}'" if title else "Stock Asset")
        return f"- Pexels: {id_str} ({lic_label})"

    if "pixabay" in provider_raw or "pixabay.com" in source_url:
        lic_label = "Pixabay License"
        id_str = f"ID #{asset_id}" if asset_id else (f"'{title}'" if title else "Stock Asset")
        return f"- Pixabay: {id_str} ({lic_label})"

    if "unsplash" in provider_raw or "unsplash.com" in source_url:
        lic_label = "Unsplash License"
        id_str = f"ID #{asset_id}" if asset_id else (f"'{title}'" if title else "Stock Asset")
        return f"- Unsplash: {id_str} ({lic_label})"

    if any(k in provider_raw for k in ["pollinations", "flux", "dalle", "ai_generated", "synth"]):
        model_name = clip_or_asset.get("model") or "Flux SDXL"
        if "pollinations" in provider_raw:
            p_name = "Pollinations AI"
        elif "flux" in provider_raw:
            p_name = "Flux AI"
        else:
            p_name = "AI Visual Synthesis"
        return f"- {p_name}: {model_name} (Generated Asset)"

    if "wikimedia" in provider_raw or "wikipedia" in provider_raw or "wikimedia.org" in source_url:
        lic_label = lic_name or "CC-BY-SA"
        lbl = title or (f"Asset #{asset_id}" if asset_id else "Public Domain")
        return f"- Wikimedia Commons: {lbl} ({lic_label})"

    if "procedural" in provider_raw or "whiteboard" in provider_raw or "motion_canvas" in provider_raw:
        return "- Procedural Graphics Engine: Animated Canvas"

    # Generic fallback
    disp = PROVIDER_DISPLAY_NAMES.get(provider_raw, provider_raw.title() or "Stock Provider")
    lic_label = lic_name or "Commercial License"
    lbl = f"ID #{asset_id}" if asset_id else (f"'{title}'" if title else "Stock Clip")
    return f"- {disp}: {lbl} ({lic_label})"


def extract_unique_providers(
    clips_or_manifest: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[str]:
    """
    Extract readable unique provider names from a manifest or list of clips.
    Empty input returns no names. Unused libraries are not listed.
    """
    if not clips_or_manifest:
        return []

    found: List[str] = []
    seen: Set[str] = set()

    for item in clips_or_manifest:
        if not isinstance(item, dict):
            continue
        p_raw = str(
            item.get("provider") or item.get("source") or item.get("engine") or ""
        ).strip().lower()
        u = str(item.get("source_url") or "").lower()

        name = ""
        if "pexels" in p_raw or "pexels" in u:
            name = "Pexels"
        elif "pixabay" in p_raw or "pixabay" in u:
            name = "Pixabay"
        elif "unsplash" in p_raw or "unsplash" in u:
            name = "Unsplash"
        elif "pollinations" in p_raw or "flux" in p_raw:
            name = "Flux"
        elif "wikimedia" in p_raw or "wikipedia" in p_raw:
            name = "Wikimedia"
        elif p_raw:
            name = PROVIDER_DISPLAY_NAMES.get(p_raw, p_raw.title())

        if name and name not in seen:
            seen.add(name)
            found.append(name)

    return found


def generate_visual_sources_block(
    clips_or_manifest: Optional[Sequence[Dict[str, Any]]] = None,
    lang: str = "tr",
) -> str:
    """
    Generate the 'Görsel Kaynaklar:' / 'Visual Sources:' block with deduplicated lines.
    """
    title_header = "Görsel Kaynaklar:" if lang == "tr" else "Visual Sources:"
    if not clips_or_manifest:
        return ""

    lines: List[str] = []
    seen_lines: Set[str] = set()

    for item in clips_or_manifest:
        line = format_visual_source_item(item)
        if line and line not in seen_lines:
            seen_lines.add(line)
            lines.append(line)

    if not lines:
        return ""

    return f"{title_header}\n" + "\n".join(lines)


def build_transparent_ai_disclosure_block(
    clips_or_manifest: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    uses_tts: bool = True,
    uses_ai_script: bool = True,
    uses_photoreal_ai: bool = False,
    uses_altered_real_event: bool = False,
    uses_real_person_synthetic: bool = False,
    uses_synthetic_persona: bool = False,
    uses_ai_visual: bool = False,
    lang: str = "tr",
    include_sources: bool = True,
) -> Dict[str, Any]:
    """
    Bölüm 8.3: YouTube 'Sentetik ve Değiştirilmiş İçerik' politikası ve kaynakça bloğu üreticisi.
    Returns:
        {
            "header_text": str,
            "sources_text": str,
            "full_disclosure_text": str,
            "studio_ai_survey": "yes" | "no",
            "disclosure_required": bool,
            "reasons": List[str],
            "providers": List[str],
            "sources_count": int,
            "policy_url": str,
        }
    """
    reasons: List[str] = []
    if uses_photoreal_ai:
        reasons.append("photorealistic_ai_visual")
    if uses_altered_real_event:
        reasons.append("altered_real_event_or_place")
    if uses_real_person_synthetic:
        reasons.append("synthetic_real_person")
    if uses_synthetic_persona:
        reasons.append("synthetic_persona")

    required = bool(reasons)
    studio_ai_survey = "yes" if required else "no"

    providers = extract_unique_providers(clips_or_manifest)
    providers_str = ", ".join(providers)
    named = f" ({providers_str})" if providers_str else ""

    if lang == "tr":
        header = (
            f"Bu video, yapay zeka araçları ve telifsiz stok kütüphaneleri{named} kullanılarak üretilmiştir.\n"
            "Tüm görsel materyaller ticari kullanıma uygun lisanslanmıştır."
        )
    else:
        header = (
            f"This video was produced using AI tools and royalty-free stock libraries{named}.\n"
            "All visual materials are licensed for commercial use."
        )

    sources = generate_visual_sources_block(clips_or_manifest, lang=lang) if include_sources else ""
    full_text = f"{header}\n{sources}" if sources else header

    return {
        "header_text": header,
        "sources_text": sources,
        "full_disclosure_text": full_text,
        "studio_ai_survey": studio_ai_survey,
        "disclosure_required": required,
        "required": required,
        "ai_disclosure_required": required,
        "reasons": reasons,
        "providers": providers,
        "sources_count": len(sources.splitlines()) - 1 if sources else 0,
        "description_paragraph": full_text,
        "policy_url": "https://support.google.com/youtube/answer/14328491",
        "inputs": {
            "uses_tts": bool(uses_tts),
            "uses_ai_script": bool(uses_ai_script),
            "uses_photoreal_ai": bool(uses_photoreal_ai),
            "uses_altered_real_event": bool(uses_altered_real_event),
            "uses_real_person_synthetic": bool(uses_real_person_synthetic),
            "uses_synthetic_persona": bool(uses_synthetic_persona),
            "uses_ai_visual": bool(uses_ai_visual),
        },
    }


def append_ai_disclosure_to_description(
    description: str,
    disclosure_block: Union[Dict[str, Any], str],
    max_length: int = 5000,
) -> str:
    """
    Appends the transparent AI disclosure block to the video description safely and idempotently.
    Ensures total description length does not exceed YouTube's 5000 char limit.
    """
    desc = (description or "").strip()

    if isinstance(disclosure_block, dict):
        block_text = str(
            disclosure_block.get("full_disclosure_text")
            or disclosure_block.get("description_paragraph")
            or ""
        ).strip()
    else:
        block_text = str(disclosure_block or "").strip()

    if not block_text:
        return desc

    # Idempotency check: if already disclosed, avoid repeating
    markers = [
        "Bu video, yapay zeka araçları",
        "This video was produced using AI",
        "Görsel Kaynaklar:",
        "Visual Sources:",
        "GenAI disclosure",
    ]
    for marker in markers:
        if marker in desc:
            return desc

    combined = f"{desc}\n\n---\n{block_text}" if desc else block_text
    if len(combined) > max_length:
        # Truncate original description body to fit disclosure block
        budget = max_length - len(block_text) - 10
        if budget > 50:
            truncated_desc = desc[:budget].rstrip() + "..."
            return f"{truncated_desc}\n\n---\n{block_text}"
        return combined[:max_length]

    return combined
