"""Advanced niche-aware topic suggestion pipeline.

Combines YouTube Shorts signals, YouTube Autocomplete live queries,
curated 37-niche viral vault, AI generation with think-tag stripping,
dynamic seed formulation, and deduplication against recent assets.
"""
from __future__ import annotations

import logging
import os
import random
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set

import config
from database import get_recent_videos
from director.visual_intent import resolve_topic_intelligence
from niche_templates import NICHES, get_niche_production_profile
from research_service import (
    extract_format_fingerprint_from_title,
    fetch_youtube_autocomplete_suggestions,
)
from services.niche_topic_vault import get_curated_topics_for_niche, resolve_canonical_niche
from services.topic_suggester_sources import (
    SOURCE_AI,
    SOURCE_GOOGLE_TRENDS,
    SOURCE_REDDIT,
    SOURCE_RSS,
    SOURCE_TREND,
    SOURCE_VAULT,
    SOURCE_YOUTUBE,
    _GENERIC_PATTERNS,
    _THINK_BLOCK_RE,
    _UNCLOSED_THINK_BLOCK_RE,
    _clean_llm_text,
    _fetch_google_trend_candidates,
    _fetch_reddit_candidates,
    _fetch_rss_candidates,
    _fetch_trend_candidates,
    _fetch_youtube_candidates,
    _generate_ai_candidates,
    _is_generic,
)
from trending_scanner import scan_youtube_shorts_trends

logger = logging.getLogger(__name__)


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

    words = clean.split()
    cap_seed = " ".join(w.capitalize() for w in words)
    is_tr = (language or "tr").lower()[:2] != "en"

    if not is_tr:
        templates = [
            f"3 Shocking Facts About {cap_seed}",
            f"The Hidden Truth About {cap_seed}",
            f"3 Critical Mistakes With {cap_seed}",
            f"The Untold Secret of {cap_seed}",
            f"3 Golden Rules for {cap_seed}",
            f"What Nobody Tells You About {cap_seed}",
            f"3 Powerful Tips to Master {cap_seed}",
            f"The Dark Side of {cap_seed} Experts Won't Tell You",
        ]
    else:
        templates = [
            f"{cap_seed} Hakkında 3 Şaşırtıcı Gerçek",
            f"{cap_seed} Konusunda En Yaygın 3 Hata",
            f"Kimsenin Bahsetmediği Gizli {cap_seed} Sırrı",
            f"{cap_seed} İçin 3 Altın Kural",
            f"{cap_seed} ile Hayatınızı Kolaylaştıracak 3 Yöntem",
            f"{cap_seed} Hakkında Bilmeniz Gereken 3 Şey",
            f"{cap_seed}: Çoğu İnsanın Bilmediği O Gerçek",
            f"Sıfırdan Başlayanlar İçin {cap_seed} Rehberi",
        ]
    templates = [t for t in templates if len(t) <= 75]
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
        hook = (
            NICHE_HOOKS_EN.get(niche_id)
            or NICHE_HOOKS_EN.get(canonical_id)
            or "High-CTR viral curiosity hook..."
        )[:120]
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


def _template_fallback_candidates(
    niche_id: str, topic_hint: str = "", language: str = "tr"
) -> List[Dict[str, Any]]:
    """Guaranteed rich, non-cliche candidates from curated vault and dynamic seed engine."""
    out: List[Dict[str, Any]] = []

    if topic_hint and len(topic_hint.strip()) >= 3:
        seed_cands = _generate_seed_based_topics(
            topic_hint.strip(), niche_id, count=6, language=language
        )
        out.extend(seed_cands)

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
    topic_hint_ignored = bool(topic_hint) and not _topic_hint_matches_niche(
        topic_hint, canonical_niche
    )
    if topic_hint_ignored:
        logger.info("Ignoring topic hint outside selected niche %s", canonical_niche)
        topic_hint = ""

    context_words = _niche_context_words(canonical_niche)
    used = _collect_used_topics()

    raw: List[Dict[str, Any]] = []

    if topic_hint and len(topic_hint) >= 3:
        raw.extend(
            _generate_seed_based_topics(topic_hint, canonical_niche, count=1, language=language)
        )

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

    raw.extend(_generate_ai_candidates(canonical_niche, language, count, topic_hint))

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
        item = _score_candidate(
            title,
            raw_niche,
            cand.get("source", SOURCE_AI),
            context_words,
            used,
            extra,
            language=language,
        )
        if item:
            scored.append(item)

    random.shuffle(scored)
    scored.sort(key=lambda x: (round(x["confidence"] / 10), x["niche_aligned"]), reverse=True)
    suggestions = _pick_diverse(scored, count)

    if len(suggestions) < count:
        for fb in _template_fallback_candidates(raw_niche, "", language=language):
            if len(suggestions) >= count:
                break
            item = _score_candidate(
                fb["title"],
                raw_niche,
                SOURCE_VAULT,
                context_words,
                used,
                extra={"is_curated": True},
                language=language,
            )
            if item and item["title"].casefold() not in {
                s["title"].casefold() for s in suggestions
            }:
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
