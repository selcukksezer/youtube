"""Live and AI candidate source fetchers for the topic suggestion pipeline."""
from __future__ import annotations

import json
import logging
import random
import re
import sys
from typing import Any, Dict, List

from niche_templates import NICHES, get_niche_production_profile
from research_service import fetch_youtube_autocomplete_suggestions
from services.niche_topic_vault import resolve_canonical_niche
from trending_scanner import scan_youtube_shorts_trends

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


def _ts_attr(name: str, default: Any) -> Any:
    mod = sys.modules.get("services.topic_suggester")
    return getattr(mod, name, default) if mod is not None else default


def _clean_llm_text(text: str) -> str:
    """Strip reasoning/thought tags and code fences from LLM responses."""
    if not text:
        return ""
    text = _THINK_BLOCK_RE.sub("", text)
    text = _UNCLOSED_THINK_BLOCK_RE.sub("", text)
    text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```$", "", text.strip(), flags=re.MULTILINE)
    return text.strip()


def _is_generic(title: str) -> bool:
    low = title.casefold()
    return any(re.search(pat, low, re.I) for pat in _GENERIC_PATTERNS)


def _fetch_youtube_candidates(
    niche_id: str, language: str, limit: int, topic_hint: str = ""
) -> List[Dict[str, Any]]:
    """Fetch high-intent YouTube candidates combining Autocomplete suggestions and trends."""
    try:
        from hybrid_niches import HYBRID_NICHES
    except ImportError:
        HYBRID_NICHES = {}
    niches_map = _ts_attr("NICHES", NICHES)
    niche = HYBRID_NICHES.get(niche_id) or niches_map.get(niche_id, niches_map["1_news_flash"])
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
            if re.search(
                r"\b(ve|ile|bir|için|nasıl|neden|kural|sır|hakkında|tarihi|dünyanın)\b",
                t,
                re.IGNORECASE,
            ):
                return False
        return True

    autocomplete_fn = _ts_attr(
        "fetch_youtube_autocomplete_suggestions", fetch_youtube_autocomplete_suggestions
    )
    trends_fn = _ts_attr("scan_youtube_shorts_trends", scan_youtube_shorts_trends)

    # 1. Live YouTube Autocomplete (real search volume queries)
    try:
        seen_ac = set()
        for q in autocomplete_queries:
            raw_suggs = autocomplete_fn(q, lang="en" if is_en else "tr")
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
        trends = trends_fn(
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
            if (
                _is_valid_candidate(t_title)
                and video_id
                and not video_id.startswith("trend_")
                and channel != "Viral Studio"
            ):
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
            return [
                {"title": it["title"], "source": SOURCE_TREND, "viral_score": 95}
                for it in items
                if it.get("title")
            ]
        except Exception as exc:
            logger.warning("News RSS topic signals unavailable: %s", exc)
    try:
        from hybrid_niches import HYBRID_NICHES
    except ImportError:
        HYBRID_NICHES = {}
    niches_map = _ts_attr("NICHES", NICHES)
    niche = HYBRID_NICHES.get(niche_id) or niches_map.get(niche_id, niches_map["1_news_flash"])
    variants = niche.get("ab_test_hook_variants") or []
    return [
        {"title": v, "source": SOURCE_TREND, "viral_score": 88}
        for v in variants
        if v and not _is_generic(v)
    ]


def _fetch_reddit_candidates(language: str, limit: int) -> List[Dict[str, Any]]:
    try:
        from reddit_client import fetch_public_posts

        posts = fetch_public_posts("AITA", limit=limit * 2, lang=language)
        return [
            {"title": p["title"], "source": SOURCE_REDDIT, "viral_score": 94}
            for p in posts
            if p.get("title")
        ]
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
    profile_fn = _ts_attr("get_niche_production_profile", get_niche_production_profile)
    profile = profile_fn(niche_id)
    try:
        from hybrid_niches import HYBRID_NICHES
    except ImportError:
        HYBRID_NICHES = {}
    niches_map = _ts_attr("NICHES", NICHES)
    niche = HYBRID_NICHES.get(niche_id) or niches_map.get(niche_id, niches_map["1_news_flash"])
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
        hint = (
            f"\nUser direction / seed topic: {topic_hint.strip()}"
            if topic_hint and topic_hint.strip()
            else ""
        )
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
                hook_ref = (
                    NICHE_HOOKS_EN.get(niche_id)
                    or NICHE_HOOKS_EN.get(canonical_id)
                    or "High-CTR viral curiosity hook"
                )
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
                try:
                    titles = json.loads(match.group())
                except Exception:
                    titles = re.findall(r'["\']([^"\']{8,75})["\']', match.group())
                return [
                    {"title": t.strip(), "source": SOURCE_AI, "viral_score": 96}
                    for t in titles
                    if isinstance(t, str) and 8 <= len(t.strip()) <= 75 and not _is_generic(t)
                ]
    except Exception as exc:
        logger.debug("AI topic generation notice: %s", exc)
        return []

    return []
