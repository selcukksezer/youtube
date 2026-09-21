"""Topic research normalization helpers, independent from web routes."""
import json
import re
import urllib.parse
from collections import Counter
from typing import Any, Dict, List

import requests

from niche_templates import get_niche_family, get_niche_production_profile

_STOIC_BANNED_RE = re.compile(
    r"skandal|24\s*saat|viral|breaking|son\s*dakika|fla[sş]|bomba|"
    r"şok|sarsan|dosyas[ıi]|interneti|d[üu]nyay[ıi]|kimsenin\s+fark|"
    r"bug[uü]n\s+herkes|olay[ıi]|gelişme|haber|flaş",
    re.I,
)


def is_stoic_banned_title(title: str) -> bool:
    return bool(_STOIC_BANNED_RE.search(title or ""))

_LIST_COUNT_RE = re.compile(
    r"\b(\d+)\s*(?:kural|gerçek|yalan|ipucu|adım|madde|şey|haber|taktik|kuralı|"
    r"rules?|facts?|tips?|steps?|things?|ways?|secrets?)\b",
    re.I,
)


def build_content_gap_suggestions(raw_topics: str, niche_id: str) -> List[Dict[str, Any]]:
    """Cleans exported Studio queries without acquiring third-party scripts."""
    profile = get_niche_production_profile(niche_id or "1_news_flash")
    seen, suggestions = set(), []
    context = f"{profile['name']} {profile['category']} {profile['tone']}".lower()
    context_words = set(re.findall(r"\w+", context))
    for candidate in re.split(r"[\r\n,;]+", raw_topics or ""):
        topic = re.sub(r"^\s*(?:[-*#]|\d+[.)])\s*", "", candidate).strip()
        topic = re.sub(r"\s+", " ", topic)
        normalized = topic.casefold()
        if len(topic) < 4 or len(topic) > 160 or normalized in seen:
            continue
        if get_niche_family(niche_id) == "stoic" and is_stoic_banned_title(topic):
            continue
        seen.add(normalized)
        words = set(re.findall(r"\w+", normalized))
        relevance = min(100, 60 + len(words & context_words) * 10 + min(len(words), 6) * 3)
        suggestions.append({"topic": topic, "relevance": relevance, "reason": f"{profile['name']} profiliyle özgün senaryo için hazırlandı"})
    return sorted(suggestions, key=lambda item: item["relevance"], reverse=True)[:20]


def infer_hook_style_from_title(title: str) -> str:
    """P2-04: classify viral hook pattern from competitor title."""
    t = title or ""
    if re.search(r"\b\d+\b", t):
        return "Sayısal Liste Kancası"
    if "?" in t:
        return "Merak Uyandıran Soru Kancası"
    if "!" in t:
        return "Şok Edici İddia Kancası"
    return "Gizem / Merak Kancası"


def infer_scene_count_from_title(title: str, default: int = 14) -> int:
    """P2-04: estimate scene cadence from list-style competitor titles."""
    match = _LIST_COUNT_RE.search(title or "")
    if match:
        beats = int(match.group(1))
        return min(14, max(5, beats + 3))
    return default


def extract_format_fingerprint_from_title(title: str, hook_analysis: str = "") -> Dict[str, Any]:
    """P2-04: single-title competitor format fingerprint."""
    scene_count = infer_scene_count_from_title(title)
    hook_style = (hook_analysis or "").strip() or infer_hook_style_from_title(title)
    return {
        "scene_count": scene_count,
        "hook_style": hook_style,
        "avg_scene_duration": round(4.0, 1),
        "source_title": title,
    }


def aggregate_format_fingerprint(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """P2-04: merge fingerprints from trend scan or content-gap samples."""
    if not items:
        return {
            "scene_count": 14,
            "hook_style": "Gizem / Merak Kancası",
            "avg_scene_duration": 3.0,
            "sample_size": 0,
        }
    scene_counts = [int(i.get("scene_count", 14)) for i in items]
    hooks = [str(i.get("hook_style", "")).strip() for i in items if str(i.get("hook_style", "")).strip()]
    avg_scenes = round(sum(scene_counts) / len(scene_counts))
    hook_mode = Counter(hooks).most_common(1)[0][0] if hooks else "Gizem / Merak Kancası"
    return {
        "scene_count": avg_scenes,
        "hook_style": hook_mode,
        "avg_scene_duration": round(4.0, 1),
        "sample_size": len(items),
    }


def build_content_gap_fingerprint(suggestions: List[Dict[str, Any]], niche_id: str = "") -> Dict[str, Any]:
    """P2-04: fingerprint from top content-gap topic candidates."""
    _ = niche_id
    samples = [extract_format_fingerprint_from_title(s["topic"]) for s in suggestions[:5]]
    return aggregate_format_fingerprint(samples)


def fetch_youtube_autocomplete_suggestions(query: str, lang: str = "tr", limit: int = 5) -> List[str]:
    """
    Item 353: YouTube arama çubuğu autocomplete önerileri.
    Google suggest endpoint (client=youtube) — ağ yoksa boş liste döner.
    """
    seed = re.sub(r"\s+", " ", (query or "").strip())
    if len(seed) < 2:
        return []
    try:
        params = {
            "client": "youtube",
            "hl": lang,
            "gl": "TR" if lang == "tr" else "US",
            "q": seed,
        }
        resp = requests.get(
            "https://clients1.google.com/complete/search",
            params=params,
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        text = resp.text.strip()
        if text.startswith("window.google.ac.h("):
            payload = text[len("window.google.ac.h("):].rsplit(")", 1)[0]
            data = json.loads(payload)
            suggestions = data[1] if isinstance(data, list) and len(data) > 1 else []
            return [row[0] for row in suggestions[:limit] if row and row[0]]
    except Exception:
        pass
    return []


def _autocomplete_overlap_score(left: str, right: str) -> float:
    left_words = set(re.findall(r"\w+", (left or "").casefold()))
    right_words = set(re.findall(r"\w+", (right or "").casefold()))
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / max(len(left_words), len(right_words))


def align_title_to_youtube_search(seed: str, title: str = "", lang: str = "tr") -> Dict[str, Any]:
    """
    Item 353: Başlığı YouTube autocomplete ile hizalar.
    En yüksek kelime örtüşmesine sahip öneriyi seçer; mevcut başlık zaten uyumluysa korur.
    """
    seed_clean = re.sub(r"\s+", " ", (seed or "").strip())
    title_clean = re.sub(r"\s+", " ", (title or seed_clean).strip())
    suggestions = fetch_youtube_autocomplete_suggestions(seed_clean, lang=lang, limit=8)

    if not suggestions:
        return {
            "aligned_title": title_clean,
            "matched_autocomplete": None,
            "suggestions": [],
            "match_score": 0.0,
            "item_353_compliant": False,
            "note": "Autocomplete alınamadı; YouTube Studio arama çubuğunda manuel doğrulayın.",
        }

    best = max(suggestions, key=lambda s: _autocomplete_overlap_score(title_clean, s))
    best_score = _autocomplete_overlap_score(title_clean, best)
    aligned = title_clean if best_score >= 0.6 else best
    aligned_score = best_score if best_score >= 0.6 else _autocomplete_overlap_score(aligned, best)

    return {
        "aligned_title": aligned,
        "matched_autocomplete": best,
        "suggestions": suggestions,
        "match_score": round(aligned_score, 2),
        "item_353_compliant": aligned_score >= 0.5,
        "note": (
            "Başlık autocomplete ile hizalandı."
            if aligned != title_clean
            else "Mevcut başlık autocomplete ile uyumlu."
        ),
    }