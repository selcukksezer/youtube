"""Topic research normalization helpers, independent from web routes."""
import json
import re
import urllib.parse
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
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


def build_topic_research_brief(
    topic: str,
    *,
    niche_id: str = "",
    lang: str = "tr",
    evidence_fetcher=None,
) -> Dict[str, Any]:
    """Create a small, auditable research contract for one Short.

    The brief is intentionally provider-neutral: it records what the writing
    and visual layers must verify instead of pretending that a single search
    result is research. Network-backed signals are optional and degrade to an
    explicit ``unavailable`` status.
    """
    clean = re.sub(r"\s+", " ", (topic or "").strip())
    autocomplete = fetch_youtube_autocomplete_suggestions(clean, lang=lang, limit=8) if clean else []
    profile = get_niche_production_profile(niche_id or "1_news_flash")
    concepts = [w for w in re.findall(r"[\wçğıöşüÇĞİÖŞÜ-]{4,}", clean) if w.lower() not in {
        "hakkında", "neden", "gerçekten", "bugün", "şimdi", "video",
    }]
    queries = []
    for q in [clean, *autocomplete[:4], *concepts[:4]]:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q.casefold() not in {x.casefold() for x in queries}:
            queries.append(q)
    evidence = collect_topic_evidence(clean, lang=lang, fetcher=evidence_fetcher) if clean else []
    claims = extract_topic_claims(clean)
    if evidence_fetcher is not None:
        # Link candidates; every adapter must provide the same retrieval and
        # claim assessment evidence as the default provider.
        for claim in claims:
            claim["evidence_ids"] = [str(row.get("source_id")) for row in evidence]
    from production.evidence import evaluate_evidence
    assessment = evaluate_evidence({
        "claims": claims,
        "evidence": evidence,
    })
    claims = assessment["claims"]
    ready = assessment["ready"]
    policy = _research_policy(niche_id=niche_id, topic=clean)
    if not ready:
        policy["action"] = "GATE"
        policy["required_review"] = True
        policy["reasons"] = list(dict.fromkeys([*policy["reasons"], assessment["reason"]]))
    status = "research_ready" if ready else "evidence_insufficient"
    return {
        "topic": clean,
        "niche_id": niche_id,
        "niche_profile": profile.get("name", ""),
        # Keep the old discovery signal for clients that display it, while the
        # publish gate uses research_ready/status above.
        "status": status if evidence else ("signals_found" if autocomplete else "autocomplete_unavailable"),
        "research_ready": ready,
        "enforce": True,
        "evidence_adapter": "custom" if evidence_fetcher is not None else "wikimedia_discovery",
        "claims": claims,
        "evidence": evidence,
        "validation_errors": assessment["errors"],
        "policy": policy,
        "search_queries": queries[:8],
        "visual_queries": queries[:8],
        "autocomplete": autocomplete,
        "verification_required": [
            "at least two independent factual sources for factual claims",
            "visual subject must match the scene intent",
            "no copyrighted reuploads or unclear licenses",
            "disclose realistic synthetic media when applicable",
        ],
        "source_policy": {
            "preferred": ["official primary sources", "licensed stock", "public domain archives"],
            "avoid": ["YouTube rips", "film/TV clips", "unclear Creative Commons terms", "keyword dumps"],
        },
        "retrieval_notes": [
            "Autocomplete is a discovery signal and is never treated as factual evidence.",
            "Publishable factual claims require two independent publisher and domain groups, retrieved content, a matching hash and a supporting quote.",
            "Wikipedia and Wikidata share an ownership group and do not constitute two independent sources.",
        ],
    }


def extract_topic_claims(topic: str) -> List[Dict[str, Any]]:
    """Create conservative claim records without inventing facts.

    The writer can refine these claims later, but this layer deliberately only
    records the user-provided topic as a research target. It never fabricates
    a supporting statistic or quotation.
    """
    clean = re.sub(r"\s+", " ", (topic or "").strip())
    if len(clean) < 4:
        return []
    return [{
        "claim_id": "claim_1",
        "text": clean,
        "factual": True,
        "status": "unverified",
        "evidence_ids": [],
    }]


def _research_policy(*, niche_id: str, topic: str) -> Dict[str, Any]:
    """Return a deterministic policy decision for the research layer."""
    nid = (niche_id or "").casefold()
    lowered = (topic or "").casefold()
    risky = any(token in nid or token in lowered for token in (
        "news", "haber", "crypto", "kripto", "finance", "finans", "health",
        "sağlık", "saglik", "medical", "hukuk", "law", "kids", "çocuk",
        "cocuk", "relig", "din", "celebrity", "ünlü", "unlu",
    ))
    return {
        "action": "GATE" if risky else "ALLOW",
        "required_review": risky,
        "reasons": ["risk_sensitive_topic" ] if risky else ["low_risk_topic"],
        "ai_disclosure_required": False,
    }


def collect_topic_evidence(topic: str, *, lang: str = "tr", fetcher=None) -> List[Dict[str, Any]]:
    """Fetch auditable, public evidence with a small, testable adapter seam.

    ``fetcher`` may be supplied by tests or a future official-source adapter.
    The default uses Wikimedia's public APIs because they are keyless and have
    stable attribution URLs. Failure returns an empty list; it never becomes
    synthetic evidence.
    """
    if fetcher is not None:
        try:
            rows = fetcher(topic, lang=lang) or []
        except Exception:
            return []
        from production.evidence import text_hash
        normalized = []
        for row in rows:
            if not isinstance(row, Mapping) or not row.get("url") or not row.get("title"):
                continue
            item = dict(row)
            excerpt = str(item.get("excerpt") or "")
            item.setdefault("retrieved_at", datetime.now(timezone.utc).isoformat())
            item.setdefault("retrieval_status", "retrieved")
            item.setdefault("content_sha256", text_hash(excerpt))
            normalized.append(item)
        return normalized
    clean = re.sub(r"\s+", " ", (topic or "").strip())
    if len(clean) < 4:
        return []
    now = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []
    try:
        params = {
            "action": "query", "format": "json", "list": "search",
            "srsearch": clean, "srnamespace": 0, "srlimit": 3,
        }
        response = requests.get(
            "https://www.wikidata.org/w/api.php", params=params,
            timeout=5, headers={"User-Agent": "youtubeoto-research/1.0"},
        )
        response.raise_for_status()
        for index, item in enumerate((response.json().get("query") or {}).get("search") or []):
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            rows.append({
                "source_id": f"wikidata_{index}_{re.sub(r'[^a-z0-9]+', '-', title.casefold()).strip('-')[:40]}",
                "title": title,
                "url": "https://www.wikidata.org/wiki/Special:Search?search=" + urllib.parse.quote(title),
                "source_type": "reference",
                "publisher": "Wikidata",
                "retrieved_at": now,
                "excerpt": re.sub(r"<[^>]+>", "", str(item.get("snippet") or "")),
                "reliability": 0.55,
                "retrieval_status": "discovery_only",
            })
    except Exception:
        # Search failure must not skip the Wikipedia excerpt below.
        pass
    # Retrieve an article excerpt for research context. Wikimedia-owned pages
    # remain one source group; neither search snippets nor this unassessed
    # excerpt can grant factual approval.
    try:
        title = str((rows[0] if rows else {}).get("title") or clean).replace(" ", "_")
        lang_code = "tr" if (lang or "tr").startswith("tr") else "en"
        summary_url = f"https://{lang_code}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
        summary = requests.get(
            summary_url, timeout=5,
            headers={"User-Agent": "youtubeoto-research/1.0"},
        )
        if summary.ok:
            data = summary.json()
            page = data.get("content_urls", {}).get("desktop", {}).get("page") or ""
            extract = str(data.get("extract") or "").strip()
            if page and extract:
                from production.evidence import text_hash
                excerpt = extract[:800]
                rows.append({
                    "source_id": "wikipedia_" + re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")[:50],
                    "title": str(data.get("title") or title.replace("_", " ")),
                    "url": page,
                    "source_type": "reference",
                    "publisher": "Wikipedia",
                    "retrieved_at": now,
                    "excerpt": excerpt,
                    "reliability": 0.6,
                    "retrieval_status": "retrieved",
                    "content_sha256": text_hash(excerpt),
                })
    except Exception:
        pass
    return rows[:2]
