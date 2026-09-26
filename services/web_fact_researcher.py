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
            return clean_snippets
    except Exception as exc:
        print(f"  [FactResearcher] DuckDuckGo query warning: {exc}")

    return []


def format_research_prompt_context(topic: str, max_snippets: int = 5) -> str:
    """Format extracted snippets for injection into Gemini script prompt."""
    snippets = research_topic_facts(topic, max_snippets=max_snippets)
    if not snippets:
        return ""

    lines = ["GERÇEK VE GÜNCEL BİLGİ KAYNAĞI (DuckDuckGo Doğrulama / Anti-Hallucination):"]
    for i, snip in enumerate(snippets, 1):
        lines.append(f"- Bilgi {i}: {snip}")
    lines.append(
        "Kural: Senaryoyu kurgularken yukarıdaki somut gerçeklere, isimlere ve teknik detaylara sadık kal; uydurma veri üretme."
    )
    return "\n".join(lines)
