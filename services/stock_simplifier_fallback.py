"""
Stock Query Simplifier & Fallback Ladder.
Adapted from SaarD00/AI-Youtube-Shorts-Generator (asset_manager.py).
When complex queries return 0 stock videos, extracts the core noun to prevent black screen / fallback drops.
"""
import re
from typing import List

# Common stop words to strip when searching for core nouns
_STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "with", "from",
    "by", "and", "or", "of", "about", "very", "extreme", "slow", "fast",
    "looking", "showing", "scene", "view", "high", "low", "deep", "dark",
    "light", "bright", "side", "front", "back", "top", "bottom"
}


def simplify_query_to_noun(query: str) -> List[str]:
    """
    Given a complex query like 'ancient roman marble bust statue',
    generates fallback candidates in descending specificity:
    1. Primary phrase (2 words): 'marble bust'
    2. Core noun (1 word): 'statue'
    """
    clean = re.sub(r"[^\w\s-]", "", query.lower()).strip()
    words = [w for w in clean.split() if w not in _STOP_WORDS and len(w) > 2]

    if not words:
        return ["nature", "abstract"]

    fallbacks = []

    # 2-word focused phrase
    if len(words) >= 3:
        fallbacks.append(f"{words[-2]} {words[-1]}")
    elif len(words) == 2:
        fallbacks.append(f"{words[0]} {words[1]}")

    # Single core noun (usually the last substantive word in English)
    core_noun = words[-1]
    if core_noun not in fallbacks:
        fallbacks.append(core_noun)

    # First word if distinct (e.g. 'ocean' from 'ocean waves crashing')
    if words[0] not in fallbacks and len(words) > 1:
        fallbacks.append(words[0])

    return fallbacks


def build_resilient_query_ladder(initial_queries: List[str]) -> List[str]:
    """
    Takes an initial query list and appends simplified fallbacks so search never starves.
    """
    results = []
    seen = set()

    for q in initial_queries:
        q_clean = q.strip()
        if q_clean and q_clean.lower() not in seen:
            results.append(q_clean)
            seen.add(q_clean.lower())

    # Generate simplified versions for each query
    for q in list(results):
        for simplified in simplify_query_to_noun(q):
            if simplified.lower() not in seen:
                results.append(simplified)
                seen.add(simplified.lower())

    return results
