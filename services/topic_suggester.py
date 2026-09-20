"""Advanced niche-aware topic suggestion pipeline.

Combines YouTube Shorts signals, niche templates, AI generation, RSS/Reddit
feeds, topic intelligence validation, and deduplication against recent assets.
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set

import config
from database import get_recent_videos
from director.visual_intent import resolve_topic_intelligence
from niche_templates import NICHES, get_niche_production_profile
from research_service import extract_format_fingerprint_from_title
from trending_scanner import scan_youtube_shorts_trends

SOURCE_YOUTUBE = "youtube"
SOURCE_AI = "ai"
SOURCE_TREND = "trend"
SOURCE_REDDIT = "reddit"

_GENERIC_PATTERNS = (
    r"^(?:herkes|everyone|tüm dünya)\b",
    r"^(?:bugün|today)\s+(?:herkes|everyone)",
    r"^viral (?:topic|konu)\b",
    r"^test topic\b",
)

# Offline fallback pools — niche-specific, used when APIs unavailable
_FALLBACK_TITLES: Dict[str, List[str]] = {
    "6_stoic_philosophy": [
        "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı",
        "Seneca'nın Kaygıyı Yok Eden 4 Stoacı Tekniği",
        "Epiktetos: Kontrol Edebileceğin Tek Şey Bu",
        "Stoacıların Asla Şikayet Etmeme Sırrı",
        "2000 Yıllık Bu Stoacı Kural Hayatını Değiştirir",
        "Marcus Aurelius Sabah Rutini — 3 Disiplin Kuralı",
        "Hiçbir Şeyi Kafana Takmamanın 3 Stoacı Sırrı",
    ],
    "2_reddit_confessions": [
        "AITA: Düğünümde Kayınbiraderim Her Şeyi Mahvetti",
        "Gizli Sırrımı 7 Yıl Sonra Eşime İtiraf Ettim",
        "İş Yerinde Patronumu İfşa Ettim — Pişman mıyım?",
        "Annem Benden Sakladığı DNA Testi Sonucunu Buldum",
        "En Yakın Arkadaşımın Nişanında İtiraz Ettim",
        "AITA: Miras Paylaşımında Kardeşimi Mahkemeye Verdim",
        "Eşimin Telefonunda Bulduğum Mesajlar Her Şeyi Değiştirdi",
    ],
    "1_news_flash": [
        "Son Dakika: Piyasaları Sarsan Kritik Ekonomik Karar",
        "Flaş: Teknoloji Devinden Beklenmedik Açıklama",
        "Son 24 Saatte Dünyayı Sarsan Gelişme — Detaylar",
        "Uzmanlar Uyardı: Bu Hafta Başlayan Kritik Süreç",
        "Resmi Açıklama Geldi: Gündemi Değiştiren Haber",
    ],
}


def _slugify_topic(title: str) -> str:
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    safe = re.sub(r"[^\w\s-]", "", title.translate(tr_map))
    return re.sub(r"\s+", "_", safe.strip())[:80].casefold()


def _collect_used_topics() -> Set[str]:
    used: Set[str] = set()
    assets_dir = config.ASSETS_DIR
    if os.path.isdir(assets_dir):
        for name in os.listdir(assets_dir):
            path = os.path.join(assets_dir, name)
            if os.path.isdir(path):
                used.add(name.casefold())
    try:
        for row in get_recent_videos(100):
            kw = (row.get("keyword") or row.get("title") or "").strip()
            if kw:
                used.add(_slugify_topic(kw))
                used.add(kw.casefold())
    except Exception:
        pass
    return used


def _niche_context_words(niche_id: str) -> Set[str]:
    profile = get_niche_production_profile(niche_id)
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    blob = " ".join([
        profile.get("name", ""),
        profile.get("category", ""),
        profile.get("tone", ""),
        niche.get("hook_style", ""),
        " ".join(niche.get("trending_keywords", [])),
        " ".join(niche.get("ab_test_hook_variants", [])),
    ])
    return {w for w in re.findall(r"\w{3,}", blob.lower())}


def _is_generic(title: str) -> bool:
    low = title.casefold()
    return any(re.search(pat, low, re.I) for pat in _GENERIC_PATTERNS)


def _score_candidate(
    title: str,
    niche_id: str,
    source: str,
    context_words: Set[str],
    used: Set[str],
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    topic = re.sub(r"\s+", " ", (title or "").strip())
    if len(topic) < 8 or len(topic) > 160:
        return None
    if _is_generic(topic):
        return None
    slug = _slugify_topic(topic)
    if slug in used or topic.casefold() in used:
        return None

    words = set(re.findall(r"\w{3,}", topic.casefold()))
    overlap = len(words & context_words)
    intel = resolve_topic_intelligence(topic, niche_id)
    niche_match = intel["resolved_niche"] == niche_id

    if source == SOURCE_YOUTUBE and overlap < 1:
        return None
    if source == SOURCE_REDDIT and niche_id != "2_reddit_confessions" and overlap < 1:
        return None
    if not niche_match and overlap < 1:
        return None
    if intel["match_method"] == "passthrough" and overlap < 2 and source in (SOURCE_YOUTUBE, SOURCE_AI):
        return None

    score = 50 + overlap * 8
    score += 18 if niche_match else -20
    score += 12 if source == SOURCE_YOUTUBE else 0
    score += 8 if source == SOURCE_TREND else 0
    score += 10 if source == SOURCE_REDDIT and niche_id == "2_reddit_confessions" else 0
    score += 6 if source == SOURCE_AI else 0
    score += 5 if any(ch.isdigit() for ch in topic) else 0
    if extra and extra.get("viral_score"):
        score += min(10, int(extra["viral_score"]) // 10)

    confidence = min(99, max(30, score))
    profile = get_niche_production_profile(niche_id)
    hook = (profile.get("hook_style") or "")[:120]
    fp = extract_format_fingerprint_from_title(topic)

    item: Dict[str, Any] = {
        "title": topic,
        "hook": hook,
        "source": source,
        "confidence": confidence,
        "relevance": confidence,
        "niche_aligned": niche_match,
        "format_fingerprint": fp,
        "topic_intelligence": {
            "resolved_niche": intel["resolved_niche"],
            "match_method": intel["match_method"],
            "locked": intel["locked"],
        },
    }
    if extra:
        for key in ("youtube_url", "channel", "view_count"):
            if extra.get(key):
                item[key] = extra[key]
    return item


def _fetch_youtube_candidates(niche_id: str, language: str, limit: int) -> List[Dict[str, Any]]:
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    keywords = niche.get("trending_keywords") or [niche["name"]]
    query = keywords[0]
    if language == "en" and len(keywords) > 1:
        query = next((k for k in keywords if re.search(r"[a-zA-Z]", k)), keywords[0])
    try:
        trends = scan_youtube_shorts_trends(query, time_filter="week", sort_by="views")
    except Exception:
        trends = []
    out: List[Dict[str, Any]] = []
    for t in trends[: limit * 2]:
        out.append({
            "title": t.get("title", ""),
            "source": SOURCE_YOUTUBE,
            "youtube_url": t.get("url"),
            "channel": t.get("channel"),
            "view_count": t.get("view_count"),
            "viral_score": t.get("viral_score"),
        })
    return out


def _fetch_trend_candidates(niche_id: str) -> List[Dict[str, Any]]:
    if niche_id == "1_news_flash":
        try:
            from rss_scanner import get_breaking_news_topics
            items = get_breaking_news_topics("aa_guncel", max_items=8)
            return [{"title": it["title"], "source": SOURCE_TREND} for it in items if it.get("title")]
        except Exception:
            pass
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    variants = niche.get("ab_test_hook_variants") or [niche.get("hook_style", "")]
    return [{"title": v, "source": SOURCE_TREND} for v in variants if v]


def _fetch_reddit_candidates(language: str, limit: int) -> List[Dict[str, Any]]:
    try:
        from reddit_client import fetch_public_posts
        posts = fetch_public_posts("AITA", limit=limit * 2, lang=language)
        return [{"title": p["title"], "source": SOURCE_REDDIT} for p in posts if p.get("title")]
    except Exception:
        return []


def _generate_ai_candidates(
    niche_id: str,
    language: str,
    count: int,
    topic_hint: str = "",
) -> List[Dict[str, Any]]:
    profile = get_niche_production_profile(niche_id)
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    try:
        from google_ai_hub import generate_text
        lang_label = "Turkish" if language == "tr" else "English"
        keywords = ", ".join((niche.get("trending_keywords") or [])[:6])
        hint = f"\nUser direction: {topic_hint.strip()}" if topic_hint and topic_hint.strip() else ""
        prompt = (
            f"Generate exactly {count + 4} unique YouTube Shorts video titles for niche \"{profile['name']}\".\n"
            f"Language: {lang_label}\nTone: {profile['tone']}\nKeywords: {keywords}\n"
            f"Hook reference: {niche.get('hook_style', '')}{hint}\n\n"
            "Rules:\n"
            "- Specific, viral, NOT generic\n"
            "- Use list/number hooks when fitting\n"
            "- Match niche format exactly\n"
            "- Return ONLY a JSON array of title strings, no markdown\n"
        )
        ok, text = generate_text(
            prompt,
            system=f"You are a YouTube Shorts topic strategist for {profile['name']}.",
        )
        if ok and text:
            match = re.search(r"\[[\s\S]*?\]", text)
            if match:
                titles = json.loads(match.group())
                return [
                    {"title": t, "source": SOURCE_AI}
                    for t in titles
                    if isinstance(t, str) and 8 <= len(t.strip()) <= 160
                ]
    except Exception:
        pass
    return _template_fallback_candidates(niche_id)


def _template_fallback_candidates(niche_id: str) -> List[Dict[str, Any]]:
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    titles = list(_FALLBACK_TITLES.get(niche_id, []))
    if not titles:
        variants = niche.get("ab_test_hook_variants") or []
        titles = [f"{niche['name']}: {v}" for v in variants if v]
    if not titles:
        titles = [niche.get("hook_style", niche["name"])]
    return [{"title": t, "source": SOURCE_AI} for t in titles]


def _pick_diverse(scored: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
    final: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    source_counts: Counter = Counter()

    for item in scored:
        if len(final) >= count:
            break
        key = item["title"].casefold()
        if key in seen:
            continue
        src = item["source"]
        if source_counts[src] >= 2 and len(final) < count - 1:
            continue
        final.append(item)
        seen.add(key)
        source_counts[src] += 1

    for item in scored:
        if len(final) >= count:
            break
        key = item["title"].casefold()
        if key not in seen:
            final.append(item)
            seen.add(key)
    return final[:count]


def suggest_topics(
    niche_id: str,
    language: str = "tr",
    count: int = 5,
    topic_hint: str = "",
) -> Dict[str, Any]:
    """Main entry: return up to `count` scored, niche-aligned topic suggestions."""
    niche_id = (niche_id or "1_news_flash").strip()
    count = max(1, min(int(count or 5), 10))
    language = (language or "tr").strip().lower()[:2]

    if niche_id not in NICHES:
        return {"status": "error", "message": "Geçersiz niş.", "suggestions": [], "count": 0}

    context_words = _niche_context_words(niche_id)
    used = _collect_used_topics()

    raw: List[Dict[str, Any]] = []
    raw.extend(_fetch_youtube_candidates(niche_id, language, count))
    raw.extend(_fetch_trend_candidates(niche_id))
    if niche_id == "2_reddit_confessions":
        raw.extend(_fetch_reddit_candidates(language, count))
    raw.extend(_generate_ai_candidates(niche_id, language, count, topic_hint))

    scored: List[Dict[str, Any]] = []
    seen_titles: Set[str] = set()
    for cand in raw:
        title = (cand.get("title") or "").strip()
        if not title:
            continue
        norm = title.casefold()
        if norm in seen_titles:
            continue
        seen_titles.add(norm)
        extra = {k: v for k, v in cand.items() if k not in ("title", "source")}
        item = _score_candidate(title, niche_id, cand.get("source", SOURCE_AI), context_words, used, extra)
        if item:
            scored.append(item)

    scored.sort(key=lambda x: (x["confidence"], x["niche_aligned"]), reverse=True)
    suggestions = _pick_diverse(scored, count)

    if len(suggestions) < count:
        for fb in _template_fallback_candidates(niche_id):
            if len(suggestions) >= count:
                break
            item = _score_candidate(
                fb["title"], niche_id, SOURCE_AI, context_words, used,
            )
            if item and item["title"].casefold() not in {s["title"].casefold() for s in suggestions}:
                suggestions.append(item)

    profile = get_niche_production_profile(niche_id)
    return {
        "status": "ok",
        "niche_id": niche_id,
        "niche_name": profile["name"],
        "language": language,
        "count": len(suggestions[:count]),
        "suggestions": suggestions[:count],
    }
