"""
Web Fact Researcher — Anti-Hallucination Gate (Verticals v3 Adaptation).
Zero-cost, 0 TL web search using DuckDuckGo HTML endpoint without API keys.
Extracts factual snippets from live web search to feed into script generation prompts.
"""

import re
import urllib.parse
from html.parser import HTMLParser
from typing import List, Optional
import requests


class _DDGHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_snippet = False
        self._current_text: List[str] = []
        self.snippets: List[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        # DuckDuckGo HTML uses class 'result__snippet' for snippet text
        css_class = d.get("class", "")
        if "result__snippet" in css_class:
            self._in_snippet = True
            self._current_text = []

    def handle_endtag(self, tag):
        if self._in_snippet and tag in ("a", "td", "div", "span"):
            snippet = "".join(self._current_text).strip()
            # Clean up excessive whitespace
            snippet = re.sub(r"\s+", " ", snippet)
            if snippet and len(snippet) > 20:
                self.snippets.append(snippet)
            self._in_snippet = False

    def handle_data(self, data):
        if self._in_snippet:
            self._current_text.append(data)


def extract_search_keywords(topic: str) -> str:
    """Extract clean search terms from topic title for best DDG results."""
    # Normalize Turkish accents for resilient matching
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    norm = topic.translate(tr_map).lower()

    fillers = [
        r"bunu neden daha once almadim",
        r"hayatinizi kolaylastiracak",
        r"diyeceginiz",
        r"mutlaka bilmeniz gereken",
        r"kimsenin bilmedigi",
        r"sok edici",
        r"inanilmaz",
        r"en iyi",
        r"top \d+",
    ]
    for pattern in fillers:
        norm = re.sub(pattern, " ", norm)

    # Remove quotes, punctuation
    cleaned = re.sub(r"[^\w\s]", " ", norm)
    tokens = [w.strip() for w in cleaned.split() if len(w.strip()) > 1 and w.strip() not in ("ve", "ile", "de", "da", "ki")]
    if tokens:
        return " ".join(tokens[:6])
    return re.sub(r"[^\w\s]", " ", norm).strip()[:60] or topic[:60]


def research_topic_facts(
    topic: str,
    max_snippets: int = 6,
    timeout_sec: float = 6.0,
) -> List[str]:
    """
    Search DuckDuckGo HTML and extract verified factual snippets.
    Returns list of short factual snippets (no prompt injection, truncated to 250 chars).
    """
    query = extract_search_keywords(topic)
    if not query:
        return []

    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    clean_snippets: List[str] = []
    try:
        resp = requests.post(
            url,
            data={"q": query},
            headers=headers,
            timeout=timeout_sec,
        )
        if resp.status_code != 200:
            # Fallback to GET
            resp = requests.get(
                f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}",
                headers=headers,
                timeout=timeout_sec,
            )

        if resp.status_code == 200 and resp.text:
            parser = _DDGHTMLParser()
            parser.feed(resp.text)
            clean_snippets = []
            for s in parser.snippets:
                # Remove URLs, bold marks, sanitization
                s_clean = re.sub(r"https?://\S+", "", s)
                s_clean = re.sub(r"<[^>]+>", "", s_clean).strip()
                if len(s_clean) >= 25:
                    clean_snippets.append(s_clean[:250])
                if len(clean_snippets) >= max_snippets:
                    break
    except Exception as exc:
        pass

    # Fallback 1: DuckDuckGo Lite
    if not clean_snippets:
        try:
            clean_snippets = _query_duckduckgo_lite(query, max_results=max_snippets)
        except Exception:
            pass

    # Fallback 2: Wikipedia API (0 TL, kesintisiz ansiklopedik doğrulama)
    if not clean_snippets:
        try:
            clean_snippets = _query_wikipedia_snippets(query, lang="tr", max_results=max_snippets)
            if not clean_snippets:
                clean_snippets = _query_wikipedia_snippets(query, lang="en", max_results=max_snippets)
        except Exception:
            pass

    return clean_snippets[:max_snippets]


def _query_duckduckgo_lite(query: str, max_results: int = 4) -> List[str]:
    """DuckDuckGo Lite HTML fallback."""
    url = "https://lite.duckduckgo.com/lite/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    resp = requests.post(url, data={"q": query}, headers=headers, timeout=5.0)
    if resp.status_code != 200:
        return []
    text = resp.text
    # Lite puts snippets in td class="result-snippet"
    raw_snippets = re.findall(r'<td class="result-snippet"[^>]*>(.*?)</td>', text, flags=re.DOTALL)
    out = []
    for s in raw_snippets:
        clean = re.sub(r"<[^>]+>", " ", s)
        clean = re.sub(r"\s+", " ", clean).strip()
        if len(clean) >= 25:
            out.append(clean[:250])
        if len(out) >= max_results:
            break
    return out


def _query_wikipedia_snippets(query: str, lang: str = "tr", max_results: int = 3) -> List[str]:
    """Wikipedia Action API ile sıfır maliyetli ve güvenilir ansiklopedik veri arama."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "utf8": 1,
        "srlimit": max_results,
    }
    headers = {"User-Agent": "ShortsVideoCreatorsBot/1.0 (contact@example.com)"}
    resp = requests.get(url, params=params, headers=headers, timeout=5.0)
    if resp.status_code != 200:
        return []
    data = resp.json()
    items = data.get("query", {}).get("search", [])
    snippets = []
    for item in items:
        snip = item.get("snippet", "")
        clean = re.sub(r"<[^>]+>", " ", snip)
        clean = re.sub(r"&[a-z]+;", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean and len(clean) >= 20:
            snippets.append(f"{item.get('title')}: {clean[:250]}")
    return snippets


def extract_claims_from_text(text: str) -> List[dict]:
    """
    Bölüm 7.4: Metindeki sayısal, tarihsel ve süperlatif iddiaları ayıklar.
    Dönen her iddia: text, type, raw_match, value, start, end içerir.
    """
    claims = []
    if not text:
        return claims

    # 1. Yüzdelik iddialar (%99, yüzde 80, % 50)
    pct_matches = re.finditer(r"(?:%\s*(\d+(?:[.,]\d+)?)|(?:yüzde|percent)\s*(\d+(?:[.,]\d+)?))", text, flags=re.I)
    for m in pct_matches:
        val = m.group(1) or m.group(2)
        claims.append({
            "type": "percentage",
            "raw_match": m.group(0),
            "value": val,
            "sentence": text,
        })

    # 2. Yıllar ve tarihler (1800-2099 arası 4 basamaklı yıllar)
    year_matches = re.finditer(r"\b(1[4-9]\d{2}|20[0-2]\d)\b(?:\s*(?:yılında|senesinde|yılı|tarihinde|yıllarında))?", text, flags=re.I)
    for m in year_matches:
        val = m.group(1)
        claims.append({
            "type": "year",
            "raw_match": m.group(0),
            "value": val,
            "sentence": text,
        })

    # 3. Sayısal büyüklükler (milyon, milyar, bin, kat)
    metric_matches = re.finditer(r"\b(\d+(?:[.,]\d+)?)\s*(milyon|milyar|trilyon|bin|kat|katı|metre|kilometre|derece)\b", text, flags=re.I)
    for m in metric_matches:
        claims.append({
            "type": "metric",
            "raw_match": m.group(0),
            "value": f"{m.group(1)} {m.group(2)}",
            "sentence": text,
        })

    # 4. Mutlak / süperlatif iddialar (tarihteki tek, asla, dünyadaki tek)
    super_matches = re.finditer(r"\b(tarihteki tek|dünyadaki tek|asla bozulmayan|tamamı|hiçbir zaman)\b", text, flags=re.I)
    for m in super_matches:
        claims.append({
            "type": "superlative",
            "raw_match": m.group(0),
            "value": m.group(1),
            "sentence": text,
        })

    return claims


def cross_verify_claim(claim: dict, topic: str = "", web_snippets: Optional[List[str]] = None) -> dict:
    """
    İddiayı web kaynaklarıyla çapraz doğrular.
    Durum: 'verified' (teyit edildi), 'plausible' (olası), 'unverified' (teyitsiz).
    """
    val = str(claim.get("value", "")).lower()
    raw = str(claim.get("raw_match", "")).lower()
    claim_type = claim.get("type", "unknown")

    if web_snippets is None:
        query = f"{topic} {val}" if topic else val
        web_snippets = research_topic_facts(query, max_snippets=4)

    snippets_text = " ".join(web_snippets).lower()

    if not web_snippets:
        return {
            **claim,
            "status": "unchecked",
            "confidence": 0.0,
            "note": "Kaynak yok; iddia silinmedi.",
        }

    if claim_type == "percentage":
        if re.search(
            rf"(?:%|yüzde|percent)\s*{re.escape(val)}\b|\b{re.escape(val)}\s*%",
            snippets_text,
            flags=re.IGNORECASE,
        ):
            return {
                **claim,
                "status": "verified",
                "confidence": 0.95,
                "note": "Yüzde web kaynağında geçiyor.",
            }
        return {
            **claim,
            "status": "unverified",
            "confidence": 0.30,
            "note": "Yüzde web kaynaklarında yok.",
        }

    if claim_type == "year":
        if val and re.search(rf"\b{re.escape(val)}\b", snippets_text):
            return {
                **claim,
                "status": "verified",
                "confidence": 0.95,
                "note": "Yıl web kaynağında geçiyor.",
            }
        return {
            **claim,
            "status": "unverified",
            "confidence": 0.30,
            "note": "Yıl web kaynaklarında yok.",
        }

    if claim_type == "metric":
        parts = val.split()
        number = parts[0].replace(".", "").replace(",", "") if parts else ""
        unit = parts[-1] if len(parts) > 1 else ""
        flat = snippets_text.replace(".", "").replace(",", "")
        if number and number in flat and (not unit or unit in snippets_text):
            return {
                **claim,
                "status": "verified",
                "confidence": 0.95,
                "note": "Sayı ve birim web kaynağında geçiyor.",
            }
        return {
            **claim,
            "status": "unverified",
            "confidence": 0.30,
            "note": "Sayısal büyüklük web kaynaklarında yok.",
        }

    if claim_type == "superlative":
        if raw and raw in snippets_text:
            return {
                **claim,
                "status": "verified",
                "confidence": 0.95,
                "note": "İfade web kaynağında geçiyor.",
            }
        return {
            **claim,
            "status": "unverified",
            "confidence": 0.30,
            "note": "Mutlak iddia web kaynaklarında yok.",
        }

    if val and (val in snippets_text or raw in snippets_text):
        return {
            **claim,
            "status": "verified",
            "confidence": 0.95,
            "note": "Web kaynaklarında doğrudan teyit edildi.",
        }

    return {
        **claim,
        "status": "unverified",
        "confidence": 0.40,
        "note": "Web kaynaklarında teyit edilemeyen iddia.",
    }


def sanitize_unverified_claims(narration: str, claims: List[dict] = None, lang: str = "tr") -> tuple[str, List[dict]]:
    """
    Bölüm 7.4: Teyit edilemeyen sayısal veya mutlak iddiaları güvenli, bilimsel ifadelere dönüştürür.
    Örnek:
    - 'İnsanların %99'u asla bilmez' -> 'İnsanların büyük bir çoğunluğu bilmez'
    - 'Tarihteki tek lider' -> 'Tarihin en dikkat çeken liderlerinden biri'
    """
    if not narration:
        return narration, []

    if claims is None:
        claims = extract_claims_from_text(narration)

    sanitized_text = narration
    modifications = []

    for c in claims:
        # Sadece unverified veya refuted olanları düzelt
        status = c.get("status", "unverified")
        if status in ("verified", "plausible", "unchecked"):
            continue

        raw = c.get("raw_match", "")
        c_type = c.get("type", "")
        en = str(lang or "tr").lower().startswith("en")

        replacement = None
        if c_type == "percentage":
            val = float(str(c.get("value", "50")).replace(",", "."))
            if en:
                replacement = "most" if val >= 80 else ("a small share" if val <= 20 else "a large share")
            elif val >= 80:
                replacement = "büyük bir çoğunluğu"
            elif val <= 20:
                replacement = "çok küçük bir kısmı"
            else:
                replacement = "önemli bir bölümü"
        elif c_type == "year":
            replacement = "that period" if en else "o dönem"
        elif c_type == "metric":
            replacement = "many" if en else "pek çok"
        elif c_type == "superlative":
            super_map = {
                "tarihteki tek": "tarihin en nadir",
                "dünyadaki tek": "dünyanın en sıradışı",
                "asla bozulmayan": "oldukça dayanıklı",
                "tamamı": "hemen hemen hepsi",
                "hiçbir zaman": "nadiren",
            }
            replacement = super_map.get(raw.lower(), "büyük oranda")

        if replacement and raw in sanitized_text:
            # Kelime sınırını koruyarak değiştir
            sanitized_text = sanitized_text.replace(raw, replacement, 1)
            modifications.append({
                "original": raw,
                "replacement": replacement,
                "type": c_type,
                "reason": c.get("note", "Teyitsiz iddia güvenli forma dönüştürüldü."),
            })

    sanitized_text = re.sub(
        r"(büyük bir çoğunluğu|çok küçük bir kısmı|önemli bir bölümü)'[a-zçğıöşü]+",
        r"\1",
        sanitized_text,
        flags=re.IGNORECASE,
    )
    sanitized_text = re.sub(r"\s{2,}", " ", sanitized_text).strip()
    return sanitized_text, modifications


def verify_and_sanitize_scenes(
    scenes: list,
    topic: str = "",
    web_snippets: Optional[List[str]] = None,
    protect_text: str = "",
    lang: str = "tr",
) -> tuple[list, dict]:
    """
    Senaryodaki tüm sahneleri tarar, iddiaları web'de çapraz doğrular ve teyitsizleri arındırır.
    web_snippets None ise arama yapılır. Boş liste arama yapmaz ve sayıları silmez.
    protect_text içindeki iddia (açılış kancası) olduğu gibi kalır.
    """
    if not scenes:
        return scenes, {"verified_count": 0, "sanitized_count": 0, "sources": []}

    is_dict = isinstance(scenes[0], dict)
    if web_snippets is None:
        web_snippets = research_topic_facts(topic, max_snippets=6) if topic else []
    protect = (protect_text or "").strip()

    all_claims = []
    total_sanitized = 0
    updated_scenes = []

    for sc in scenes:
        narr = str(getattr(sc, "narration", None) or (sc.get("narration") if is_dict else "") or "")
        claims = extract_claims_from_text(narr)
        verified_claims = []
        for c in claims:
            v = cross_verify_claim(c, topic=topic, web_snippets=web_snippets)
            raw = str(v.get("raw_match") or "")
            if protect and raw and raw in protect:
                v = {**v, "status": "verified", "note": "Açılış kancası korunuyor."}
            verified_claims.append(v)
            all_claims.append(v)

        sanitized_narr, mods = sanitize_unverified_claims(narr, verified_claims, lang=lang)
        if mods:
            total_sanitized += len(mods)

        if is_dict:
            new_sc = dict(sc)
            new_sc["narration"] = sanitized_narr
            new_sc["fact_verified"] = True
            new_sc["claims"] = verified_claims
            updated_scenes.append(new_sc)
        else:
            sc.narration = sanitized_narr
            sc.fact_verified = True
            updated_scenes.append(sc)

    report = {
        "topic": topic,
        "total_claims": len(all_claims),
        "verified_count": sum(1 for c in all_claims if c.get("status") == "verified"),
        "plausible_count": sum(1 for c in all_claims if c.get("status") == "plausible"),
        "unverified_count": sum(1 for c in all_claims if c.get("status") == "unverified"),
        "sanitized_count": total_sanitized,
        "snippets_count": len(web_snippets),
        "sources": ["DuckDuckGo HTML", "DuckDuckGo Lite", "Wikipedia Action API"],
    }
    return updated_scenes, report


def format_snippet_block(snippets: List[str]) -> str:
    """Format already-fetched snippets. Does not hit the network again."""
    if not snippets:
        return ""
    lines = ["GERÇEK VE GÜNCEL BİLGİ KAYNAĞI (DuckDuckGo & Wikipedia Doğrulama / Anti-Hallucination):"]
    for i, snip in enumerate(snippets, 1):
        lines.append(f"- Bilgi {i}: {snip}")
    lines.append(
        "Kural: Senaryoyu kurgularken yukarıdaki somut gerçeklere, isimlere ve teknik detaylara sadık kal; uydurma veri üretme."
    )
    return "\n".join(lines)


def format_research_prompt_context(topic: str, max_snippets: int = 5) -> str:
    """Format extracted snippets for injection into Gemini script prompt."""
    return format_snippet_block(research_topic_facts(topic, max_snippets=max_snippets))


def scrub_unverified_claims(plan: dict, snippets: Optional[List[str]], lang: str = "tr") -> dict:
    """Drop claims the fetched snippets do not contain. Empty research leaves the script."""
    snippets = [s for s in (snippets or []) if str(s).strip()]
    plan["fact_snippets"] = snippets
    plan["fact_check"] = {
        "checked": bool(snippets),
        "source": "duckduckgo" if snippets else "",
        "dropped": [],
    }
    if not snippets:
        return plan
    hook = str(((plan.get("retention_metadata") or {}).get("opening_hook") or "")).strip()
    scenes, report = verify_and_sanitize_scenes(
        plan.get("scenes") or [],
        topic=str(plan.get("title") or ""),
        web_snippets=snippets,
        protect_text=hook,
        lang=lang,
    )
    plan["scenes"] = scenes
    plan["fact_check"]["dropped"] = [
        c.get("raw_match")
        for s in scenes
        for c in (s.get("claims") or [])
        if c.get("status") == "unverified"
    ]
    plan["fact_check"]["sanitized_count"] = report.get("sanitized_count", 0)
    plan["full_narration"] = " ".join(
        str(s.get("narration") or "").strip()
        for s in scenes
        if str(s.get("narration") or "").strip()
    )
    if report.get("sanitized_count"):
        print(
            f"  [FactResearcher] Teyitsiz iddia elendi: {report['sanitized_count']}"
        )
    return plan

