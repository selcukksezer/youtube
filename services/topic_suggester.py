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
from collections import Counter
from typing import Any, Dict, List, Optional, Set

import config
from database import get_recent_videos
from director.visual_intent import resolve_topic_intelligence
from niche_templates import NICHES, get_niche_production_profile
from research_service import extract_format_fingerprint_from_title, fetch_youtube_autocomplete_suggestions
from trending_scanner import scan_youtube_shorts_trends
from services.niche_topic_vault import CURATED_NICHE_TOPICS, resolve_canonical_niche

logger = logging.getLogger(__name__)

SOURCE_YOUTUBE = "youtube"
SOURCE_AI = "ai"
SOURCE_TREND = "trend"
SOURCE_REDDIT = "reddit"
SOURCE_VAULT = "vault"

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


def _is_generic(title: str) -> bool:
    low = title.casefold()
    return any(re.search(pat, low, re.I) for pat in _GENERIC_PATTERNS)


def _generate_seed_based_topics(seed_keyword: str, niche_id: str, count: int = 5) -> List[Dict[str, Any]]:
    """Synthesize high-CTR viral topic candidates directly from a user seed keyword."""
    clean = re.sub(r"[^\w\s\u00C0-\u017F-]", "", (seed_keyword or "").strip())
    if len(clean) < 3:
        return []
    
    # Capitalize for title casing
    words = clean.split()
    cap_seed = " ".join(w.capitalize() for w in words)
    
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
    for t in templates[:count + 2]:
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

    # If it is from our curated vault or seed tailored, it is inherently niche-aligned
    is_vault = source == SOURCE_VAULT or (extra and extra.get("is_curated")) or (extra and extra.get("is_seed_tailored"))

    if not is_vault:
        if source == SOURCE_YOUTUBE and overlap < 1:
            return None
        if source == SOURCE_REDDIT and niche_id != "2_reddit_confessions" and overlap < 1:
            return None
        if not niche_match and overlap < 1:
            return None
        if intel["match_method"] == "passthrough" and overlap < 1 and source in (SOURCE_YOUTUBE, SOURCE_AI):
            return None

    score = 65 + overlap * 6
    score += 15 if (niche_match or is_vault) else -15
    score += 10 if source == SOURCE_VAULT else 0
    score += 12 if source == SOURCE_YOUTUBE else 0
    score += 8 if source == SOURCE_TREND else 0
    score += 10 if source == SOURCE_REDDIT and niche_id == "2_reddit_confessions" else 0
    score += 8 if source == SOURCE_AI else 0
    score += 5 if any(ch.isdigit() for ch in topic) else 0
    if extra and extra.get("viral_score"):
        score += min(10, int(extra["viral_score"]) // 10)

    confidence = min(99, max(50, score))
    profile = get_niche_production_profile(niche_id)
    hook = (profile.get("hook_style") or "")[:120]
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
        for key in ("youtube_url", "channel", "view_count"):
            if extra.get(key):
                item[key] = extra[key]
    return item


def _fetch_youtube_candidates(niche_id: str, language: str, limit: int, topic_hint: str = "") -> List[Dict[str, Any]]:
    """Fetch high-intent YouTube candidates combining Autocomplete suggestions and trends."""
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    keywords = niche.get("trending_keywords") or [niche["name"]]
    
    # Priority query: topic_hint if provided, otherwise primary niche keyword
    primary_query = (topic_hint or "").strip() or keywords[0]
    if language == "en" and len(keywords) > 1 and not topic_hint:
        primary_query = next((k for k in keywords if re.search(r"[a-zA-Z]", k)), keywords[0])
    
    out: List[Dict[str, Any]] = []

    # 1. Live YouTube Autocomplete (real search volume queries)
    try:
        autocomplete_queries = [primary_query]
        if not topic_hint and len(keywords) > 1:
            autocomplete_queries.append(keywords[1])
        
        seen_ac = set()
        for q in autocomplete_queries:
            raw_suggs = fetch_youtube_autocomplete_suggestions(q)
            for s in raw_suggs:
                clean_s = s.strip()
                if 12 <= len(clean_s) <= 100 and clean_s.lower() not in seen_ac:
                    seen_ac.add(clean_s.lower())
                    title_formatted = clean_s[0].upper() + clean_s[1:]
                    out.append({
                        "title": title_formatted,
                        "source": SOURCE_YOUTUBE,
                        "viral_score": 92,
                    })
    except Exception as ac_err:
        logger.debug("autocomplete query error: %s", ac_err)

    # 2. Trending Shorts scanner
    try:
        trends = scan_youtube_shorts_trends(primary_query, time_filter="week", sort_by="views")
        for t in trends[: limit * 2]:
            t_title = t.get("title", "")
            if t_title and not _is_generic(t_title):
                out.append({
                    "title": t_title,
                    "source": SOURCE_YOUTUBE,
                    "youtube_url": t.get("url"),
                    "channel": t.get("channel"),
                    "view_count": t.get("view_count"),
                    "viral_score": t.get("viral_score", 90),
                })
    except Exception:
        pass

    return out


def _fetch_trend_candidates(niche_id: str) -> List[Dict[str, Any]]:
    if niche_id == "1_news_flash":
        try:
            from rss_scanner import get_breaking_news_topics
            items = get_breaking_news_topics("aa_guncel", max_items=8)
            return [{"title": it["title"], "source": SOURCE_TREND, "viral_score": 95} for it in items if it.get("title")]
        except Exception:
            pass
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    variants = niche.get("ab_test_hook_variants") or []
    return [{"title": v, "source": SOURCE_TREND, "viral_score": 88} for v in variants if v and not _is_generic(v)]


def _fetch_reddit_candidates(language: str, limit: int) -> List[Dict[str, Any]]:
    try:
        from reddit_client import fetch_public_posts
        posts = fetch_public_posts("AITA", limit=limit * 2, lang=language)
        return [{"title": p["title"], "source": SOURCE_REDDIT, "viral_score": 94} for p in posts if p.get("title")]
    except Exception:
        return []


def _generate_ai_candidates(
    niche_id: str,
    language: str,
    count: int,
    topic_hint: str = "",
) -> List[Dict[str, Any]]:
    """Generate fresh AI candidates with reasoning tag stripping and graceful fallback."""
    profile = get_niche_production_profile(niche_id)
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    try:
        from google_ai_hub import generate_text
        lang_label = "Turkish" if language == "tr" else "English"
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
        prompt = (
            f"Generate exactly {count + 4} unique, highly engaging YouTube Shorts video titles for niche \"{profile['name']}\".\n"
            f"Perspective / Angle: {chosen_angle} (Seed: {seed})\n"
            f"Language: {lang_label}\nTone: {profile['tone']}\nKeywords: {keywords}\n"
            f"Hook reference: {niche.get('hook_style', '')}{hint}\n\n"
            "Rules:\n"
            "- Specific, high CTR, emotional hook or curiosity gap\n"
            "- Under 75 characters per title, punchy and clear\n"
            "- Do NOT use robotic cliches like 'Bu bilgiyi öğrenmeden önce'\n"
            "- Return ONLY a JSON array of title strings, no markdown\n"
        )
        ok, text = generate_text(
            prompt,
            system=f"You are an elite YouTube Shorts viral title strategist for {profile['name']}.",
        )
        if ok and text:
            cleaned = _clean_llm_text(text)
            match = re.search(r"\[[\s\S]*?\]", cleaned)
            if match:
                titles = json.loads(match.group())
                return [
                    {"title": t.strip(), "source": SOURCE_AI, "viral_score": 96}
                    for t in titles
                    if isinstance(t, str) and 8 <= len(t.strip()) <= 160 and not _is_generic(t)
                ]
    except Exception as exc:
        logger.debug("AI topic generation notice: %s", exc)

    # Resilient fallback: Return curated niche titles and seed-tailored topics
    return _template_fallback_candidates(niche_id, topic_hint)


def _template_fallback_candidates(niche_id: str, topic_hint: str = "") -> List[Dict[str, Any]]:
    """Guaranteed rich, non-cliche candidates from curated vault and dynamic seed engine."""
    canonical_id = resolve_canonical_niche(niche_id)
    out: List[Dict[str, Any]] = []

    # 1. If topic hint given by user, generate dynamic framed titles
    if topic_hint and len(topic_hint.strip()) >= 3:
        seed_cands = _generate_seed_based_topics(topic_hint.strip(), canonical_id, count=6)
        out.extend(seed_cands)

    # 2. Add curated high-CTR vault topics
    vault_titles = list(CURATED_NICHE_TOPICS.get(canonical_id, []))
    if not vault_titles:
        vault_titles = list(CURATED_NICHE_TOPICS.get("1_news_flash", []))

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

    context_words = _niche_context_words(canonical_niche)
    used = _collect_used_topics()

    raw: List[Dict[str, Any]] = []

    # 1. Custom user seed topics (highest priority if user typed a keyword)
    if topic_hint and len(topic_hint.strip()) >= 3:
        raw.extend(_generate_seed_based_topics(topic_hint.strip(), canonical_niche, count=count))

    # 2. Real-time YouTube Signals (Autocomplete + Trending)
    raw.extend(_fetch_youtube_candidates(canonical_niche, language, count, topic_hint))
    
    # 3. Trending & Breaking News
    raw.extend(_fetch_trend_candidates(canonical_niche))

    # 4. Reddit Viral Stories (if applicable)
    if canonical_niche == "2_reddit_confessions":
        raw.extend(_fetch_reddit_candidates(language, count))

    # 5. AI Generation (with reasoning tag stripping and multi-angle prompts)
    raw.extend(_generate_ai_candidates(canonical_niche, language, count, topic_hint))

    # If raw candidates are still insufficient (e.g. offline/mocked), inject curated vault
    if len(raw) < count:
        raw.extend(_template_fallback_candidates(canonical_niche, topic_hint))

    # Score and filter all candidates
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
        item = _score_candidate(title, canonical_niche, cand.get("source", SOURCE_AI), context_words, used, extra)
        if item:
            scored.append(item)

    # Random shuffle with score bias to ensure freshness on every "Retry"
    random.shuffle(scored)
    scored.sort(key=lambda x: (round(x["confidence"] / 10), x["niche_aligned"]), reverse=True)
    suggestions = _pick_diverse(scored, count)

    # In case count not met, fill from curated vault
    if len(suggestions) < count:
        for fb in _template_fallback_candidates(canonical_niche, topic_hint):
            if len(suggestions) >= count:
                break
            item = _score_candidate(
                fb["title"], canonical_niche, SOURCE_VAULT, context_words, used, extra={"is_curated": True}
            )
            if item and item["title"].casefold() not in {s["title"].casefold() for s in suggestions}:
                suggestions.append(item)

    profile = get_niche_production_profile(canonical_niche)
    return {
        "status": "ok",
        "niche_id": canonical_niche,
        "niche_name": profile["name"],
        "language": language,
        "count": len(suggestions[:count]),
        "suggestions": suggestions[:count],
    }
