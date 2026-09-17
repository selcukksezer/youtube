"""Topic research normalization helpers, independent from web routes."""
import re
from typing import Any, Dict, List

from niche_templates import get_niche_production_profile


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
        seen.add(normalized)
        words = set(re.findall(r"\w+", normalized))
        relevance = min(100, 60 + len(words & context_words) * 10 + min(len(words), 6) * 3)
        suggestions.append({"topic": topic, "relevance": relevance, "reason": f"{profile['name']} profiliyle özgün senaryo için hazırlandı"})
    return sorted(suggestions, key=lambda item: item["relevance"], reverse=True)[:20]