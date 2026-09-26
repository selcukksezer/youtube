"""
Timed Visual Matcher Engine.
Adapted and improved from ShortGPT (gpt_editing.py + editing_generate_videos.yaml).
Generates concise, 1-2 word concrete English B-roll search queries based on actual spoken narration segments.
Replaces bloated 'cinematic 4k' junk with real filmable nouns and actions.
"""
import re
import json
from typing import Any, Dict, List, Optional
import config

SYSTEM_PROMPT = """You are an AI video editor specialized in generating precise B-roll video search queries for stock footage libraries (like Pexels and Pixabay).
You must output ONLY valid JSON in the specified format, with no markdown fences and no additional text.
"""

USER_PROMPT_TEMPLATE = """You are a video editor creating engaging visual Shorts.
For each scene below, suggest 3 alternative video search queries in English that match what is being spoken.

Guidelines:
1. Use ONLY English words (translate the concept if input is Turkish).
2. Keep queries between 1-3 words maximum.
3. Focus on concrete, filmable objects, actions, or environments.
4. Strictly avoid abstract feelings (e.g., do NOT use "feeling sad", "confused thoughts", "life truth").
5. Strictly avoid buzzwords (do NOT use "cinematic", "4k", "atmospheric", "viral", "epic").
6. Ensure queries are family-friendly and safe.

Good examples:
- "ocean waves"
- "typing keyboard"
- "city traffic"
- "roman marble bust"
- "burning candle dark"
- "stock market chart"

Bad examples:
- "stoic anger control philosophy 4k" (too long, abstract)
- "sad man looking into void" (abstract)
- "cinematic dramatic lighting" (buzzwords)

Scenes:
{scenes_block}

Output format:
{{
  "scene_queries": [
    {{"scene_number": 1, "queries": ["query one", "query two", "query three"]}},
    {{"scene_number": 2, "queries": ["query one", "query two", "query three"]}}
  ]
}}
"""

_CLEANUP_TOKENS = re.compile(
    r"\b(cinematic|4k|8k|uhd|atmospheric|epic|viral|trending|aesthetic|b-?roll|stock footage)\b",
    re.IGNORECASE,
)


def clean_query(query: str) -> str:
    """Strips forbidden buzzwords and keeps queries clean and concise."""
    q = _CLEANUP_TOKENS.sub("", query)
    q = re.sub(r"[^\w\s-]", "", q)
    words = [w for w in q.strip().split() if len(w) > 1]
    return " ".join(words[:3]) if words else "abstract background"


def generate_timed_visual_queries(
    scenes: List[Dict[str, Any]],
    niche_id: str = "",
    force_local: bool = False,
) -> List[Dict[str, Any]]:
    """
    Takes scenes with narration and produces 3 concise, concrete English queries for each scene.
    Falls back to intelligent local mapping if LLM is unavailable or force_local is True.
    """
    if not scenes:
        return []

    if force_local:
        return _apply_local_queries(scenes, niche_id)

    scenes_block = "\n".join(
        f"Scene {i+1}: {(s.get('narration') or s.get('scene_description') or '')[:120]}"
        for i, s in enumerate(scenes)
    )

    prompt = USER_PROMPT_TEMPLATE.format(scenes_block=scenes_block)

    try:
        from openai import OpenAI
        api_key = config.AI_API_KEY
        base_url = config.AI_BASE_URL
        model = config.AI_MODEL

        if not api_key:
            raise ValueError("No AI API key configured")

        client = OpenAI(api_key=api_key, base_url=base_url, timeout=10.0)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"} if "gemini" in model.lower() or "gpt" in model.lower() else None,
        )

        raw = resp.choices[0].message.content.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        data = json.loads(raw)
        mapped = {}
        for item in data.get("scene_queries", []):
            sc_num = item.get("scene_number")
            raw_qs = item.get("queries", [])
            cleaned_qs = [clean_query(q) for q in raw_qs if clean_query(q)]
            if sc_num and cleaned_qs:
                mapped[sc_num] = cleaned_qs[:3]

        # Apply mapped queries back to scenes
        for i, scene in enumerate(scenes):
            sc_num = i + 1
            if sc_num in mapped and mapped[sc_num]:
                scene["search_queries"] = mapped[sc_num]

        return scenes

    except Exception as exc:
        print(f"[TimedVisualMatcher] LLM query generation note: {exc}, using local keyword ladder")
        return _apply_local_queries(scenes, niche_id)


def _apply_local_queries(scenes: List[Dict[str, Any]], niche_id: str = "") -> List[Dict[str, Any]]:
    """Local fallback using visuals/query_builder ladder without network calls."""
    try:
        from visuals.query_builder import build_shot_queries
        for scene in scenes:
            narr = str(scene.get("narration") or "")
            desc = str(scene.get("scene_description") or "")
            queries = build_shot_queries(narration=narr, scene_description=desc, niche_id=niche_id)
            if queries:
                scene["search_queries"] = [clean_query(q) for q in queries[:3]]
    except Exception:
        pass
    return scenes

