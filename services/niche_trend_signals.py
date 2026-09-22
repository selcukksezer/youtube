"""Niche-aware YouTube trend signals and family-safe synthetic fallbacks."""
from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import requests

from niche_templates import NICHES, get_niche_family, get_niche_production_profile
from research_service import is_stoic_banned_title

MAX_TREND_CARDS = 5

SOURCE_YOUTUBE_API = "youtube_api"
SOURCE_YOUTUBE_SEARCH = "youtube_search"
SOURCE_AI = "ai_suggested"

SOURCE_LABELS = {
    SOURCE_YOUTUBE_API: "YouTube Data API v3",
    SOURCE_YOUTUBE_SEARCH: "YouTube canlı arama",
    SOURCE_AI: "AI niş önerisi (YouTube verisi yok)",
}

_FAMILY_FALLBACK_TITLES: Dict[str, List[str]] = {
    "stoic": [
        "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı",
        "Seneca'nın Kaygıyı Yok Eden 4 Stoacı Tekniği",
        "Epiktetos: Kontrol Edebileceğin Tek Şey Bu",
        "Stoacıların Asla Şikayet Etmeme Sırrı",
        "2000 Yıllık Bu Stoacı Kural Hayatını Değiştirir",
    ],
    "reddit": [
        "AITA: Düğünümde Kayınbiraderim Her Şeyi Mahvetti",
        "Gizli Sırrımı 7 Yıl Sonra Eşime İtiraf Ettim",
        "İş Yerinde Patronumu İfşa Ettim — Pişman mıyım?",
        "Annem Benden Sakladığı DNA Testi Sonucunu Buldum",
        "En Yakın Arkadaşımın Nişanında İtiraz Ettim",
    ],
    "whatsapp": [
        "Bu WhatsApp Mesajı Her Şeyi Değiştirdi",
        "Sevgilim Gece Yarısı Gönderdiği Mesajla Beni Şoke Etti",
        "Gruba Yanlışlıkla Giden Mesaj Skandal Çıkardı",
        "Ex'ten Gelen Bu Mesajı Okuyunca Donup Kaldım",
        "Arkadaşımın Telefonunda Bulduğum Sohbet Her Şeyi Açıkladı",
    ],
    "news": [
        "Son Dakika: Piyasaları Sarsan Kritik Ekonomik Karar",
        "Flaş: Teknoloji Devinden Beklenmedik Açıklama",
        "Son 24 Saatte Dünyayı Sarsan Gelişme — Detaylar",
        "Uzmanlar Uyardı: Bu Hafta Başlayan Kritik Süreç",
        "Resmi Açıklama Geldi: Gündemi Değiştiren Haber",
    ],
}

_CONTENT_GAP_EXAMPLES: Dict[str, List[str]] = {
    "6_stoic_philosophy": [
        "Stoacılıkta öfke kontrolü",
        "Marcus Aurelius disiplin sözleri",
        "Seneca kaygı yönetimi",
    ],
    "2_reddit_confessions": [
        "AITA düğün kayınbirader drama",
        "Gizli aile sırrı itirafı",
        "İş yerinde etik ikilem hikayesi",
    ],
    "1_news_flash": [
        "Ekonomi son dakika gelişme",
        "Teknoloji devi açıklama",
        "Piyasa kritik karar analizi",
    ],
    "20_whatsapp_chat_story": [
        "Gece yarısı gelen şok mesaj",
        "Yanlış gruba giden itiraf",
        "Ex'ten beklenmedik mesaj",
    ],
}


def get_content_gap_examples(niche_id: str) -> List[str]:
    """Return niche-appropriate Studio content-gap seed lines for UI placeholders."""
    family = get_niche_family(niche_id or "1_news_flash")
    if niche_id in _CONTENT_GAP_EXAMPLES:
        return list(_CONTENT_GAP_EXAMPLES[niche_id])
    if family == "stoic":
        return list(_CONTENT_GAP_EXAMPLES["6_stoic_philosophy"])
    if family == "reddit":
        return list(_CONTENT_GAP_EXAMPLES["2_reddit_confessions"])
    if family == "whatsapp":
        return list(_CONTENT_GAP_EXAMPLES["20_whatsapp_chat_story"])
    if family == "news":
        return list(_CONTENT_GAP_EXAMPLES["1_news_flash"])
    profile = get_niche_production_profile(niche_id or "1_news_flash")
    kw = (NICHES.get(niche_id or "1_news_flash") or {}).get("trending_keywords") or []
    seeds = [f"{profile['name']} {k}" for k in kw[:3]]
    return seeds or [profile["name"]]


def _parse_view_count(raw: str) -> int:
    """YouTube TR uses '1,2 Mn' and '12 B'; stripping digits turns those into 12."""
    text = (raw or "").casefold().replace("\xa0", " ")
    match = re.search(r"(\d+(?:[.,]\d+)*)", text)
    if not match:
        return 0
    token = match.group(1)
    if "," in token and "." not in token:
        value = float(token.replace(",", "."))
    elif token.count(".") == 1 and len(token.split(".")[-1]) != 3:
        value = float(token)
    else:
        value = float(re.sub(r"[.,]", "", token) or 0)
    if re.search(r"\b(mn|milyon|million)\b", text) or re.search(r"\d\s*m\b", text):
        value *= 1_000_000
    elif re.search(r"\b(mr|milyar|billion)\b", text):
        value *= 1_000_000_000
    elif re.search(r"\b(bin|thousand)\b", text) or re.search(r"\d\s*[bk]\b", text):
        value *= 1_000
    return int(value)


def filter_trends_for_family(trends: List[Dict[str, Any]], niche_id: str) -> List[Dict[str, Any]]:
    family = get_niche_family(niche_id)
    if family != "stoic":
        return trends[:MAX_TREND_CARDS]
    return [t for t in trends if not is_stoic_banned_title(t.get("title", ""))][:MAX_TREND_CARDS]


def niche_search_queries(niche_id: str) -> List[str]:
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    keywords = list(niche.get("trending_keywords") or [])
    if niche.get("name"):
        keywords.append(niche["name"])
    seen, out = set(), []
    for raw in keywords:
        q = re.sub(r"\s+", " ", (raw or "").strip())
        key = q.casefold()
        if q and key not in seen:
            seen.add(key)
            out.append(q)
    return out or [niche["name"]]


def fetch_public_youtube_trends(query: str, region: str = "TR", max_results: int = MAX_TREND_CARDS) -> List[Dict[str, Any]]:
    """Pull recent YouTube search results without API key."""
    q = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={q}&sp=EgIIAQ%253D%253D&gl={region.upper()}&hl=tr"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    trends: List[Dict[str, Any]] = []
    try:
        r = requests.get(url, headers=headers, timeout=8)
        match = re.search(r"var ytInitialData = ({.*?});</script>", r.text)
        if not match:
            return []
        import json

        data = json.loads(match.group(1))
        contents = (
            data.get("contents", {})
            .get("twoColumnSearchResultsRenderer", {})
            .get("primaryContents", {})
            .get("sectionListRenderer", {})
            .get("contents", [])
        )
        for section in contents:
            for item in section.get("itemSectionRenderer", {}).get("contents", []):
                vr = item.get("videoRenderer")
                if not vr:
                    continue
                title = vr.get("title", {}).get("runs", [{}])[0].get("text", "")
                vid = vr.get("videoId", "")
                channel = vr.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                raw_views = vr.get("viewCountText", {}).get("simpleText", "")
                view_count = _parse_view_count(raw_views)
                if title and vid:
                    trends.append(
                        {
                            "video_id": vid,
                            "title": title,
                            "channel": channel or "YouTube Creator",
                            "published_at": "Son 24 saat (Açık Web)",
                            "view_count": view_count,
                            "view_count_text": raw_views or "Yeni video",
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "source_type": SOURCE_YOUTUBE_SEARCH,
                        }
                    )
                    if len(trends) >= max_results:
                        return trends
    except Exception as scrape_err:
        print(f"  [TrendScraper] Web scraper notu: {scrape_err}")
    return trends


def fetch_niche_youtube_trends(niche_id: str, region: str = "TR") -> List[Dict[str, Any]]:
    """Try each niche keyword until real YouTube titles are found."""
    for query in niche_search_queries(niche_id):
        hits = fetch_public_youtube_trends(query, region=region, max_results=MAX_TREND_CARDS * 2)
        filtered = filter_trends_for_family(hits, niche_id)
        if filtered:
            return filtered
    return []


def _family_fallback_titles(niche_id: str) -> List[str]:
    family = get_niche_family(niche_id)
    titles = list(_FAMILY_FALLBACK_TITLES.get(family, []))
    if titles:
        return titles[:MAX_TREND_CARDS]
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    variants = niche.get("ab_test_hook_variants") or [niche.get("hook_style", niche["name"])]
    return [v for v in variants if v][:MAX_TREND_CARDS]


def generate_synthetic_trend_signals(niche_id: str) -> List[Dict[str, Any]]:
    """AI/template suggestions — no fabricated channels or view counts."""
    try:
        from services.topic_suggester import suggest_topics

        result = suggest_topics(niche_id, language="tr", count=MAX_TREND_CARDS)
        suggestions = result.get("suggestions") or []
    except Exception:
        suggestions = []

    stoic = get_niche_family(niche_id) == "stoic"
    titles: List[str] = []
    for item in suggestions:
        title = (item.get("title") or "").strip()
        if not title or (stoic and is_stoic_banned_title(title)):
            continue
        if title not in titles:
            titles.append(title)

    if len(titles) < MAX_TREND_CARDS:
        for title in _family_fallback_titles(niche_id):
            if len(titles) >= MAX_TREND_CARDS:
                break
            if title not in titles and not (stoic and is_stoic_banned_title(title)):
                titles.append(title)

    curated: List[Dict[str, Any]] = []
    for i, title in enumerate(titles[:MAX_TREND_CARDS]):
        curated.append(
            {
                "video_id": f"ai_{niche_id}_{i}",
                "title": title,
                "channel": "",
                "published_at": "",
                "view_count": 0,
                "view_count_text": "",
                "url": f"https://www.youtube.com/results?search_query={urllib.parse.quote(title)}",
                "source_type": SOURCE_AI,
            }
        )
    return curated


def build_trends_response(
    trends: List[Dict[str, Any]],
    source: str,
    profile: Dict[str, Any],
    fingerprint_fn,
) -> Dict[str, Any]:
    """Normalize API payload with honest source metadata."""
    capped = trends[:MAX_TREND_CARDS]
    return {
        "status": "ok",
        "source": source,
        "source_label": SOURCE_LABELS.get(source, source),
        "is_real_youtube": source in (SOURCE_YOUTUBE_API, SOURCE_YOUTUBE_SEARCH),
        "profile": profile,
        "trends": capped,
        "format_fingerprint": fingerprint_fn(capped),
    }
