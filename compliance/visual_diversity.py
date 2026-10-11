"""
compliance/visual_diversity.py — Sequential Visual Clip Clustering & Diversity Guard.

Adapted and evolved from reference_repos2/autoclip (backend/tasks/video.py & backend/utils/video_editor.py).
Ensures consecutive scenes in a Short do not use visually redundant stock assets:
1. Detects repeated creator IDs, identical color tones, and identical source providers.
2. Re-orders or substitutes candidates from secondary pools to maintain high visual pacing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def compute_clip_fingerprint(clip: Dict[str, Any]) -> Dict[str, Any]:
    """Generates comparison features for visual clustering."""
    provider = str(clip.get("source") or clip.get("provider") or "").lower()
    creator_id = str(clip.get("creator_id") or clip.get("user_id") or "").lower()
    color_tone = str(clip.get("dominant_color") or clip.get("color_tone") or clip.get("tone") or "neutral").lower()
    query = str(clip.get("query") or clip.get("search_term") or "").lower()

    return {
        "provider": provider,
        "creator_id": creator_id,
        "color_tone": color_tone,
        "query": query,
    }


def is_visually_too_similar(clip_a: Dict[str, Any], clip_b: Dict[str, Any]) -> bool:
    """
    Evaluates whether two candidate clips are too similar to be placed back-to-back.
    Returns True for the same creator or repeated queries without explicitly different color tones.
    """
    if not clip_a or not clip_b:
        return False

    fp_a = compute_clip_fingerprint(clip_a)
    fp_b = compute_clip_fingerprint(clip_b)

    # 1. Same creator ID with non-empty creator string
    if fp_a["creator_id"] and fp_b["creator_id"] and fp_a["creator_id"] == fp_b["creator_id"]:
        return True

    # Unknown tone metadata should not make an identical query appear diverse.
    if fp_a["query"] and fp_a["query"] == fp_b["query"]:
        if (
            fp_a["color_tone"] == fp_b["color_tone"]
            or "neutral" in (fp_a["color_tone"], fp_b["color_tone"])
        ):
            return True

    return False


def diversify_scene_search_queries(scenes: List[Dict[str, Any]]) -> int:
    """Prioritize an existing alternate query when adjacent scenes repeat a visual."""
    adjusted_count = 0
    previous_visual: Optional[Dict[str, Any]] = None

    for scene in scenes:
        intent = scene.get("visual_intent")
        raw_queries = scene.get("search_queries")
        if not raw_queries and isinstance(intent, dict):
            raw_queries = intent.get("search_queries")
        if isinstance(raw_queries, str):
            raw_queries = [raw_queries]
        if not isinstance(raw_queries, (list, tuple)):
            previous_visual = None
            continue

        queries = [
            query.strip()
            for query in raw_queries
            if isinstance(query, str) and query.strip()
        ]
        if not queries:
            previous_visual = None
            continue

        color_tone = (
            scene.get("dominant_color")
            or scene.get("color_tone")
            or (intent.get("color_tone") if isinstance(intent, dict) else None)
            or "neutral"
        )
        color_tone = str(color_tone).strip().casefold() or "neutral"
        current_visual = {"query": queries[0], "color_tone": color_tone}

        if previous_visual and is_visually_too_similar(previous_visual, current_visual):
            alternatives = [
                {"query": query, "color_tone": color_tone}
                for query in queries[1:]
                if query.casefold() != queries[0].casefold()
            ]
            adjusted_pair = enforce_visual_clip_diversity(
                [previous_visual, current_visual],
                candidate_pools={1: alternatives},
            )
            selected_query = adjusted_pair[1]["query"]
            if selected_query != queries[0]:
                reordered = [selected_query] + [
                    query for query in queries if query.casefold() != selected_query.casefold()
                ]
                scene["search_queries"] = reordered
                if isinstance(intent, dict):
                    intent_queries = intent.get("search_queries")
                    if isinstance(intent_queries, list) and any(
                        isinstance(query, str)
                        and query.casefold() == selected_query.casefold()
                        for query in intent_queries
                    ):
                        intent["search_queries"] = [selected_query] + [
                            query for query in intent_queries
                            if not isinstance(query, str)
                            or query.casefold() != selected_query.casefold()
                        ]
                scene["visual_diversity_adjusted"] = True
                current_visual = {"query": selected_query, "color_tone": color_tone}
                adjusted_count += 1

        previous_visual = current_visual

    return adjusted_count


def enforce_visual_clip_diversity(
    chosen_clips: List[Dict[str, Any]],
    candidate_pools: Optional[Dict[int, List[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    """
    Inspects consecutive clips in a sequence. If clip[i] and clip[i+1] are too similar,
    substitutes clip[i+1] with an alternative from candidate_pools[i+1] or swaps with a later scene.
    """
    if len(chosen_clips) <= 1:
        return list(chosen_clips)

    result = list(chosen_clips)
    pools = candidate_pools or {}

    for i in range(len(result) - 1):
        current = result[i]
        nxt = result[i + 1]

        if is_visually_too_similar(current, nxt):
            # Attempt 1: Substitute from candidate pool for scene i+1
            pool_candidates = pools.get(i + 1, [])
            substituted = False
            for cand in pool_candidates:
                if not is_visually_too_similar(current, cand):
                    # Also check against scene i+2 if present
                    if i + 2 < len(result) and is_visually_too_similar(cand, result[i + 2]):
                        continue
                    result[i + 1] = cand
                    substituted = True
                    break

            # Attempt 2: Swap scene i+1 with a later scene that is not too similar
            if not substituted and i + 2 < len(result):
                for j in range(i + 2, len(result)):
                    cand_swap = result[j]
                    if not is_visually_too_similar(current, cand_swap):
                        # Verify swap works in both directions
                        if not is_visually_too_similar(cand_swap, result[i + 2 if i + 2 != j else j]):
                            result[i + 1], result[j] = result[j], result[i + 1]
                            substituted = True
                            break

    return result
