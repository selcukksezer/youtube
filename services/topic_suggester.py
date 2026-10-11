"""Advanced niche-aware topic suggestion pipeline.

Combines YouTube Shorts signals, YouTube Autocomplete live queries,
curated 37-niche viral vault, AI generation with think-tag stripping,
dynamic seed formulation, and deduplication against recent assets.
"""
from __future__ import annotations

import json
import logging
import os
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from typing import Any, Dict, List, Optional, Set

import config
from database import get_recent_videos
from director.visual_intent import resolve_topic_intelligence
from niche_templates import NICHES, get_niche_production_profile
from research_service import extract_format_fingerprint_from_title, fetch_youtube_autocomplete_suggestions
from trending_scanner import scan_youtube_shorts_trends
from services.niche_topic_vault import get_curated_topics_for_niche, resolve_canonical_niche

logger = logging.getLogger(__name__)

SOURCE_YOUTUBE = "youtube"
SOURCE_AI = "ai"
SOURCE_TREND = "trend"
SOURCE_REDDIT = "reddit"
SOURCE_VAULT = "vault"
SOURCE_GOOGLE_TRENDS = "google_trends"
SOURCE_RSS = "rss"

_GENERIC_PATTERNS = (
    r"^(?:herkes|everyone|tüm dünya)\b",
    r"^(?:bugün|today)\s+(?:herkes|everyone)",
    r"^viral (?:topic|konu)\b",
    r"^test topic\b",
    r"^niche\[.+\]",
    r"okullarda anlatılmayan en büyük 5 yalan",
    r"içinde gizlenen şok edici şeyi buldu",
)

_THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)
_UNCLOSED_THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*$", re.IGNORECASE | re.DOTALL)


def _clean_llm_text(text: str) -> str:
    """Strip reasoning/thought tags and code fences from LLM responses."""
    if not text:
        return ""
    text = _THINK_BLOCK_RE.sub("", text)
    text = _UNCLOSED_THINK_BLOCK_RE.sub("", text)
    text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```$", "", text.strip(), flags=re.MULTILINE)
    return text.strip()


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
    except Exception as exc:
        logger.warning("recent topic list unavailable: %s", exc)
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


def _topic_hint_matches_niche(topic_hint: str, niche_id: str) -> bool:
    hint = (topic_hint or "").strip()
    if not hint:
        return False

    canonical_niche = resolve_canonical_niche(niche_id)
    intelligence = resolve_topic_intelligence(hint, canonical_niche)
    if resolve_canonical_niche(intelligence["resolved_niche"]) != canonical_niche:
        return False
    if intelligence["match_method"] != "passthrough":
        return True

    hint_words = set(re.findall(r"\w{3,}", hint.casefold()))
    return bool(hint_words & _niche_context_words(canonical_niche))


def _is_generic(title: str) -> bool:
    low = title.casefold()
    return any(re.search(pat, low, re.I) for pat in _GENERIC_PATTERNS)


def _generate_seed_based_topics(
    seed_keyword: str, niche_id: str, count: int = 5, language: str = "tr"
) -> List[Dict[str, Any]]:
    """Synthesize high-CTR viral topic candidates directly from a user seed keyword."""
    if resolve_canonical_niche(niche_id) == "10_religious_quotes":
        return []

    raw = (seed_keyword or "").strip()
    raw = re.sub(r"#\w+", "", raw)
    clean = re.sub(r"[^\w\s\u00C0-\u017F-]", "", raw).strip()
    clean = re.sub(r"\bshorts\b", "", clean, flags=re.I).strip()
    if len(clean) < 3:
        return []
    
    # Capitalize for title casing
    words = clean.split()
    cap_seed = " ".join(w.capitalize() for w in words)
    is_tr = (language or "tr").lower()[:2] != "en"
    
    if not is_tr:
        templates = [
            f"5 Shocking Facts About {cap_seed} You Were Never Told",
            f"The Hidden Truth About {cap_seed} Nobody Talks About",
            f"3 Critical Mistakes Most People Make With {cap_seed}",
            f"The Dark Side of {cap_seed} Experts Won't Tell You",
            f"Everything You Thought You Knew About {cap_seed} Is Completely Wrong",
            f"The Untold Secret of {cap_seed} That Changes Everything",
            f"How {cap_seed} Quietly Controls 99% of People Without Them Knowing",
            f"The Beginner's Guide to {cap_seed}: 3 Golden Rules You Must Follow",
        ]
    else:
        templates = [
            f"{cap_seed} Hakkında Muhtemelen Bilmediğiniz 5 Şaşırtıcı Gerçek",
            f"Kimsenin Bahsetmediği Gizli {cap_seed} Sırrı ve Doğrusu",
            f"{cap_seed} Konusunda Çoğu İnsanın Yaptığı En Yaygın 3 Hata",
            f"Bunu Öğrenene Kadar {cap_seed} Hakkında Bildiğiniz Her Şey Yanlıştı",
            f"Sıfırdan Başlayanlar İçin {cap_seed} Rehberi: 3 Altın Kural",
            f"Günde Sadece 10 Dakika Ayırarak {cap_seed} ile Sonuç Alın",
            f"{cap_seed} ile İlgili Hayatınızı Kolaylaştıracak 3 Pratik Yöntem",
            f"Uzmanların {cap_seed} Hakkında Asla Açıklamak İstemediği O Gerçek",
        ]
    random.shuffle(templates)
    
    out: List[Dict[str, Any]] = []
    for t in templates[:count]:
        out.append({
            "title": t,
            "source": SOURCE_AI,
            "viral_score": 95,
            "is_seed_tailored": True,
        })
    return out


def _score_candidate(
    title: str,
    niche_id: str,
    source: str,
    context_words: Set[str],
    used: Set[str],
    extra: Optional[Dict[str, Any]] = None,
    language: str = "tr",
) -> Optional[Dict[str, Any]]:
    topic = re.sub(r"\s+", " ", (title or "").strip())
    if len(topic) < 8 or len(topic) > 160:
        return None
    if source in (SOURCE_AI, SOURCE_VAULT) and len(topic) > 75:
        return None
    if _is_generic(topic):
        return None
    slug = _slugify_topic(topic)
    if slug in used or topic.casefold() in used:
        return None

    words = set(re.findall(r"\w{3,}", topic.casefold()))
    overlap = len(words & context_words)
    intel = resolve_topic_intelligence(topic, niche_id)
    canonical_niche = resolve_canonical_niche(niche_id)
    niche_match = resolve_canonical_niche(intel["resolved_niche"]) == canonical_niche
    if intel["locked"] and not niche_match:
        return None

    is_vault = source == SOURCE_VAULT or (extra and extra.get("is_curated"))

    if not is_vault:
        if source in (SOURCE_YOUTUBE, SOURCE_GOOGLE_TRENDS, SOURCE_RSS) and overlap < 1:
            return None
        if source == SOURCE_REDDIT and niche_id != "2_reddit_confessions" and overlap < 1:
            return None
        if not niche_match and overlap < 1:
            return None
        if intel["match_method"] == "passthrough" and overlap < 1 and source in (SOURCE_YOUTUBE, SOURCE_AI):
            return None

    score = 55 + min(20, overlap * 4)
    score += 15 if (niche_match or is_vault) else -15
    score += {
        SOURCE_VAULT: 5,
        SOURCE_YOUTUBE: 8,
        SOURCE_TREND: 5,
        SOURCE_REDDIT: 4,
        SOURCE_AI: 2,
        SOURCE_GOOGLE_TRENDS: 8,
        SOURCE_RSS: 6,
    }.get(source, 0)
    score += 2 if any(ch.isdigit() for ch in topic) else 0

    confidence = min(95, max(50, score))
    profile = get_niche_production_profile(niche_id)
    is_tr = (language or "tr").lower()[:2] != "en"
    if is_tr:
        hook = (profile.get("hook_style") or "")[:120]
    else:
        from niche_templates import NICHE_HOOKS_EN
        canonical_id = resolve_canonical_niche(niche_id)
        hook = (NICHE_HOOKS_EN.get(niche_id) or NICHE_HOOKS_EN.get(canonical_id) or "High-CTR viral curiosity hook...")[:120]
    fp = extract_format_fingerprint_from_title(topic)

    item: Dict[str, Any] = {
        "title": topic,
        "hook": hook,
        "source": source if source != SOURCE_VAULT else SOURCE_AI,
        "confidence": confidence,
        "relevance": confidence,
        "niche_aligned": True if is_vault else niche_match,
        "format_fingerprint": fp,
        "topic_intelligence": {
            "resolved_niche": intel["resolved_niche"],
            "match_method": intel["match_method"],
            "locked": intel["locked"],
        },
    }
    if extra:
        for key in ("youtube_url", "channel", "view_count", "source_detail"):
            if extra.get(key):
                item[key] = extra[key]
    return item


def _fetch_youtube_candidates(niche_id: str, language: str, limit: int, topic_hint: str = "") -> List[Dict[str, Any]]:
    """Fetch high-intent YouTube candidates combining Autocomplete suggestions and trends."""
    try:
        from hybrid_niches import HYBRID_NICHES
    except ImportError:
        HYBRID_NICHES = {}
    niche = HYBRID_NICHES.get(niche_id) or NICHES.get(niche_id, NICHES["1_news_flash"])
    is_en = (language or "tr").lower().startswith("en")
    
    if is_en:
        en_fallback_query = niche.get("name_en") or niche_id.split("_", 1)[-1].replace("_", " ")
        primary_query = (topic_hint or "").strip() or en_fallback_query
        autocomplete_queries = [primary_query]
    else:
        keywords = niche.get("trending_keywords") or [niche["name"]]
        primary_query = (topic_hint or "").strip() or keywords[0]
        autocomplete_queries = [primary_query]
        if not topic_hint and len(keywords) > 1:
            autocomplete_queries.append(keywords[1])
    
    out: List[Dict[str, Any]] = []

    def _is_valid_candidate(t: str) -> bool:
        if not t or _is_generic(t):
            return False
        if len(t.strip().split()) < 3 or len(t.strip()) < 15:
            return False
        if is_en:
            if re.search(r"[çğıöşüÇĞİÖŞÜ]", t):
                return False
            if re.search(r"\b(ve|ile|bir|için|nasıl|neden|kural|sır|hakkında|tarihi|dünyanın)\b", t, re.IGNORECASE):
                return False
        return True

    # 1. Live YouTube Autocomplete (real search volume queries)
    try:
        seen_ac = set()
        for q in autocomplete_queries:
            raw_suggs = fetch_youtube_autocomplete_suggestions(q, lang="en" if is_en else "tr")
            for s in raw_suggs:
                clean_s = s.strip()
                if clean_s.lower() not in seen_ac and _is_valid_candidate(clean_s):
                    seen_ac.add(clean_s.lower())
                    title_formatted = clean_s[0].upper() + clean_s[1:]
                    out.append({
                        "title": title_formatted,
                        "source": SOURCE_YOUTUBE,
                        "source_detail": "YouTube arama önerisi",
                        "viral_score": 92,
                    })
    except Exception as ac_err:
        logger.debug("autocomplete query error: %s", ac_err)

    # 2. Trending Shorts scanner
    try:
        trends = scan_youtube_shorts_trends(
            primary_query,
            time_filter="week",
            sort_by="views",
            region="US" if is_en else "TR",
        )
        for t in trends[: limit * 2]:
            t_title = t.get("title", "")
            video_id = str(t.get("video_id") or "")
            channel = str(t.get("channel") or "")
            # The scanner's fallback cards are synthetic, not live YouTube evidence.
            if _is_valid_candidate(t_title) and video_id and not video_id.startswith("trend_") and channel != "Viral Studio":
                view_count = t.get("view_count")
                out.append({
                    "title": t_title,
                    "source": SOURCE_YOUTUBE,
                    "youtube_url": t.get("url"),
                    "channel": channel,
                    "view_count": view_count,
                    "source_detail": f"{channel} · {view_count}" if view_count else "YouTube Shorts",
                    "viral_score": t.get("viral_score", 90),
                })
    except Exception as exc:
        logger.warning("YouTube Shorts topic signals unavailable: %s", exc)

    return out


def _fetch_google_trend_candidates(language: str = "tr", limit: int = 8) -> List[Dict[str, Any]]:
    """Fetch region-specific live Google Trends RSS signals."""
    try:
        from services.autonomous_topic_engine import AutonomousTopicEngine

        geo = "US" if (language or "tr").lower().startswith("en") else "TR"
        candidates = AutonomousTopicEngine(timeout=4.0).fetch_google_trends(geo=geo, limit=limit)
        out: List[Dict[str, Any]] = []
        for candidate in candidates:
            item = candidate.to_dict()
            title = (item.get("title") or "").strip()
            if not title:
                continue
            traffic = item.get("metadata", {}).get("traffic")
            out.append({
                "title": title,
                "source": SOURCE_GOOGLE_TRENDS,
                "source_detail": f"Google Trends · yaklaşık trafik {traffic}" if traffic else "Google Trends",
                "viral_score": round(float(item.get("trending_score") or 0.5) * 100),
            })
        return out
    except Exception as exc:
        logger.warning("Google Trends topic signals unavailable: %s", exc)
        return []


def _fetch_rss_candidates(niche_id: str, language: str = "tr", limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch RSS only for niches with an explicit, relevant feed mapping."""
    if (language or "tr").lower().startswith("tr") and niche_id != "1_news_flash":
        return []
    feed_key = {
        "8_crypto_market": "finance",
        "21_ai_tools_hacks": "tech",
    }.get(niche_id, niche_id)
    try:
        from services.autonomous_topic_engine import AutonomousTopicEngine, NICHE_RSS_FEEDS

        feed_urls = NICHE_RSS_FEEDS.get(feed_key)
        if not feed_urls:
            return []
        candidates = AutonomousTopicEngine(timeout=4.0).fetch_rss_topics(feed_urls=feed_urls, limit=limit)
        return [
            {
                "title": candidate.title,
                "source": SOURCE_RSS,
                "source_detail": "BBC News RSS" if niche_id == "1_news_flash" else "Nişe özel RSS",
                "viral_score": round(candidate.trending_score * 100),
            }
            for candidate in candidates
            if candidate.title
        ]
    except Exception as exc:
        logger.warning("RSS topic signals unavailable for %s: %s", niche_id, exc)
        return []


def _fetch_trend_candidates(niche_id: str, language: str = "tr") -> List[Dict[str, Any]]:
    is_tr = (language or "tr").lower()[:2] != "en"
    if not is_tr:
        # Never inject Turkish RSS news or Turkish A/B hook variants in English mode
        return []
    if niche_id == "1_news_flash":
        try:
            from rss_scanner import get_breaking_news_topics
            items = get_breaking_news_topics("aa_guncel", max_items=8)
            return [{"title": it["title"], "source": SOURCE_TREND, "viral_score": 95} for it in items if it.get("title")]
        except Exception as exc:
            logger.warning("News RSS topic signals unavailable: %s", exc)
    try:
        from hybrid_niches import HYBRID_NICHES
    except ImportError:
        HYBRID_NICHES = {}
    niche = HYBRID_NICHES.get(niche_id) or NICHES.get(niche_id, NICHES["1_news_flash"])
    variants = niche.get("ab_test_hook_variants") or []
    return [{"title": v, "source": SOURCE_TREND, "viral_score": 88} for v in variants if v and not _is_generic(v)]


def _fetch_reddit_candidates(language: str, limit: int) -> List[Dict[str, Any]]:
    try:
        from reddit_client import fetch_public_posts
        posts = fetch_public_posts("AITA", limit=limit * 2, lang=language)
        return [{"title": p["title"], "source": SOURCE_REDDIT, "viral_score": 94} for p in posts if p.get("title")]
    except Exception as exc:
        logger.warning("Reddit topic signals unavailable: %s", exc)
        return []


def _generate_ai_candidates(
    niche_id: str,
    language: str,
    count: int,
    topic_hint: str = "",
) -> List[Dict[str, Any]]:
    """Generate fresh AI candidates with reasoning tag stripping and graceful fallback."""
    profile = get_niche_production_profile(niche_id)
    try:
        from hybrid_niches import HYBRID_NICHES
    except ImportError:
        HYBRID_NICHES = {}
    niche = HYBRID_NICHES.get(niche_id) or NICHES.get(niche_id, NICHES["1_news_flash"])
    try:
        from google_ai_hub import generate_text
        is_tr = (language or "tr").lower()[:2] != "en"
        lang_label = "Turkish" if is_tr else "English"
        niche_display_name = profile["name"] if is_tr else (niche.get("name_en") or profile["name"])
        keywords = ", ".join((niche.get("trending_keywords") or [])[:6])
        angles = [
            "paradoxical psychological secrets or counter-intuitive realities",
            "actionable rules, practical habits or tactical daily applications",
            "dark secrets, overlooked historical truths or unspoken dynamics",
            "shocking statistical or behavioral facts that change perspectives",
            "viral question hooks and debate-provoking situations",
            "unusual discoveries, unexpected connections and practical lifehacks",
        ]
        chosen_angle = random.choice(angles)
        seed = random.randint(100, 999999)
        hint = f"\nUser direction / seed topic: {topic_hint.strip()}" if topic_hint and topic_hint.strip() else ""
        if niche_id == "10_religious_quotes":
            prompt = (
                f"Generate exactly {count + 4} unique, authentic, highly engaging YouTube Shorts video titles about Hadith (Hadis-i Şerif) and Quranic Ayah topics for niche \"{niche_display_name}\".\n"
                f"Perspective: Sahih Hadiths (Buhari, Müslim, Tirmizi, Ebu Davud) and heart-touching Quranic Ayahs with authentic moral lessons (Seed: {seed}).\n"
                f"Language: {lang_label}\nTone: {profile['tone']}\nKeywords: {keywords}\n"
                f"Format requirement: Titles must cite the source book or surah in parentheses, e.g. 'Peygamber Efendimiz\\'in Ameller Niyetlere Göredir Hadisi (Buhari)'.{hint}\n\n"
                "Rules:\n"
                "- Never invent a Hadith, verse, surah, or source citation; omit references unless certain they are authentic\n"
                "- Make each title about a distinct religious lesson; do not repeat one seed with different religious prefixes\n"
                "- High CTR, emotionally peaceful, inspiring curiosity and spiritual reflection\n"
                "- Under 75 characters per title, punchy and clear\n"
                "- Return ONLY a JSON array of title strings, no markdown\n"
            )
        else:
            if is_tr:
                hook_ref = niche.get("hook_style", "")
                lang_rule = "- Sadece Türkçe dilinde başlık üret"
                anti_cliche = "- Do NOT use robotic cliches like 'Bu bilgiyi öğrenmeden önce'"
            else:
                from niche_templates import NICHE_HOOKS_EN
                canonical_id = resolve_canonical_niche(niche_id)
                hook_ref = NICHE_HOOKS_EN.get(niche_id) or NICHE_HOOKS_EN.get(canonical_id) or "High-CTR viral curiosity hook"
                lang_rule = "- Generate ALL titles strictly in natural fluent English. Absolutely NO Turkish words. (Note: Niche name or keywords might be in Turkish, but you must translate the concept and output ONLY English titles)"
                anti_cliche = "- Do NOT use robotic cliches like 'Before you learn this fact'"
            prompt = (
                f"Generate exactly {count + 4} unique, highly engaging YouTube Shorts video titles for niche \"{niche_display_name}\".\n"
                f"Perspective / Angle: {chosen_angle} (Seed: {seed})\n"
                f"Language: {lang_label}\nTone: {profile['tone']}\nKeywords: {keywords}\n"
                f"Hook reference: {hook_ref}{hint}\n\n"
                "Rules:\n"
                "- Specific, high CTR, emotional hook or curiosity gap\n"
                "- Cover distinct subtopics; do not rephrase the same seed topic across the list\n"
                "- Under 75 characters per title, punchy and clear\n"
                f"{anti_cliche}\n"
                f"{lang_rule}\n"
                "- Return ONLY a JSON array of title strings, no markdown\n"
            )
        ok, text = generate_text(
            prompt,
            system=f"You are an elite YouTube Shorts viral title strategist for {niche_display_name}.",
        )
        if ok and text:
            cleaned = _clean_llm_text(text)
            match = re.search(r"\[[\s\S]*?\]", cleaned)
            if match:
                titles = json.loads(match.group())
                return [
                    {"title": t.strip(), "source": SOURCE_AI, "viral_score": 96}
                    for t in titles
                    if isinstance(t, str) and 8 <= len(t.strip()) <= 75 and not _is_generic(t)
                ]
    except Exception as exc:
        logger.debug("AI topic generation notice: %s", exc)
        return [{"title": "API Limitine Takıldı (Çok fazla istek). Lütfen 1-2 dakika bekleyip tekrar deneyin.", "source": SOURCE_AI, "viral_score": 0}]

    return [{"title": "Yapay zeka öneri üretemedi. (API Hatası veya Limit)", "source": SOURCE_AI, "viral_score": 0}]


def _template_fallback_candidates(niche_id: str, topic_hint: str = "", language: str = "tr") -> List[Dict[str, Any]]:
    """Guaranteed rich, non-cliche candidates from curated vault and dynamic seed engine."""
    out: List[Dict[str, Any]] = []

    # 1. If topic hint given by user, generate dynamic framed titles
    if topic_hint and len(topic_hint.strip()) >= 3:
        seed_cands = _generate_seed_based_topics(topic_hint.strip(), niche_id, count=6, language=language)
        out.extend(seed_cands)

    # 2. Add curated high-CTR vault topics
    vault_titles = get_curated_topics_for_niche(niche_id, lang=language)
    if not vault_titles:
        vault_titles = get_curated_topics_for_niche("1_news_flash", lang=language)

    random.shuffle(vault_titles)
    for t in vault_titles:
        out.append({
            "title": t,
            "source": SOURCE_VAULT,
            "viral_score": 94,
            "is_curated": True,
        })
    return out


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
        # Allow at most 3 items from the same source to keep high diversity
        if source_counts[src] >= 3 and len(final) < count - 1:
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
    raw_niche = (niche_id or "1_news_flash").strip()
    canonical_niche = resolve_canonical_niche(raw_niche)
    count = max(1, min(int(count or 5), 10))
    language = (language or "tr").strip().lower()[:2]

    if canonical_niche not in NICHES:
        return {"status": "error", "message": "Geçersiz niş.", "suggestions": [], "count": 0}

    topic_hint = (topic_hint or "").strip()
    topic_hint_ignored = bool(topic_hint) and not _topic_hint_matches_niche(topic_hint, canonical_niche)
    if topic_hint_ignored:
        logger.info("Ignoring topic hint outside selected niche %s", canonical_niche)
        topic_hint = ""

    context_words = _niche_context_words(canonical_niche)
    used = _collect_used_topics()

    raw: List[Dict[str, Any]] = []

    # 1. Custom user seed topics (highest priority if user typed a keyword)
    if topic_hint and len(topic_hint) >= 3:
        raw.extend(_generate_seed_based_topics(topic_hint, canonical_niche, count=1, language=language))

    # 2. Gather independent live sources concurrently to bound endpoint latency.
    source_jobs = [
        ("YouTube", _fetch_youtube_candidates, (canonical_niche, language, count, topic_hint)),
        ("Google Trends", _fetch_google_trend_candidates, (language, 8)),
        ("RSS", _fetch_rss_candidates, (canonical_niche, language, 5)),
        ("niche trends", _fetch_trend_candidates, (canonical_niche, language)),
    ]
    if canonical_niche == "2_reddit_confessions":
        source_jobs.append(("Reddit", _fetch_reddit_candidates, (language, count)))

    with ThreadPoolExecutor(max_workers=len(source_jobs)) as executor:
        futures = {
            executor.submit(fetcher, *args): source_name
            for source_name, fetcher, args in source_jobs
        }
        for future in as_completed(futures):
            source_name = futures[future]
            try:
                raw.extend(future.result())
            except Exception as exc:
                logger.warning("%s topic source failed: %s", source_name, exc)

    # 3. AI Generation (with reasoning tag stripping and multi-angle prompts)
    raw.extend(_generate_ai_candidates(canonical_niche, language, count, topic_hint))

    # 4. Score and filter all candidates
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
        item = _score_candidate(title, raw_niche, cand.get("source", SOURCE_AI), context_words, used, extra, language=language)
        if item:
            scored.append(item)

    # Random shuffle with score bias to ensure freshness on every "Retry"
    random.shuffle(scored)
    scored.sort(key=lambda x: (round(x["confidence"] / 10), x["niche_aligned"]), reverse=True)
    suggestions = _pick_diverse(scored, count)

    # In case count not met, fill from curated vault
    if len(suggestions) < count:
        for fb in _template_fallback_candidates(raw_niche, "", language=language):
            if len(suggestions) >= count:
                break
            item = _score_candidate(
                fb["title"], raw_niche, SOURCE_VAULT, context_words, used, extra={"is_curated": True}, language=language
            )
            if item and item["title"].casefold() not in {s["title"].casefold() for s in suggestions}:
                suggestions.append(item)

    try:
        from hybrid_niches import HYBRID_NICHES
    except ImportError:
        HYBRID_NICHES = {}
    
    niche_obj = HYBRID_NICHES.get(raw_niche) or NICHES.get(raw_niche, {})
    profile = get_niche_production_profile(raw_niche)
    
    niche_display_name = (
        niche_obj.get("name_en")
        if language == "en" and niche_obj.get("name_en")
        else (niche_obj.get("name") or profile.get("name", raw_niche))
    )
    
    source_counts = Counter(item["source"] for item in suggestions[:count])
    return {
        "status": "ok",
        "niche_id": raw_niche,
        "niche_name": niche_display_name,
        "language": language,
        "topic_hint_ignored": topic_hint_ignored,
        "source_counts": dict(source_counts),
        "count": len(suggestions[:count]),
        "suggestions": suggestions[:count],
    }
