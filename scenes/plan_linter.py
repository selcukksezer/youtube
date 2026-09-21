"""Server-side plan diversity linter — mood/query repetition (Batch E)."""
from __future__ import annotations

from typing import Any, Dict, List


def lint_plan_diversity(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Warn or flag weak AI plans with repetitive moods or duplicate search queries.
    Returns warnings list and weak=True when regeneration is recommended.
    """
    scenes: List[Dict[str, Any]] = plan.get("scenes") or []
    if not scenes:
        return {"warnings": ["no_scenes"], "weak": True, "unique_moods": 0, "duplicate_queries": 0}

    moods = {(s.get("mood") or "").strip().lower() for s in scenes if (s.get("mood") or "").strip()}
    primary_queries: List[str] = []
    for s in scenes:
        qs = s.get("search_queries") or []
        if not qs and s.get("search_query"):
            qs = [s["search_query"]]
        primary = (qs[0] if qs else "").strip().lower()
        if primary:
            primary_queries.append(primary)

    dup_queries = max(0, len(primary_queries) - len(set(primary_queries)))
    warnings: List[str] = []
    weak = False

    if len(scenes) >= 10 and len(moods) < 4:
        warnings.append(f"low_mood_diversity:{len(moods)}")
        weak = True
    if len(scenes) >= 10 and dup_queries >= 5:
        warnings.append(f"duplicate_queries:{dup_queries}")
        weak = True
    if len(scenes) >= 10 and len(set(primary_queries)) < max(6, len(scenes) // 2):
        warnings.append(f"low_query_diversity:{len(set(primary_queries))}")
        weak = True

    return {
        "warnings": warnings,
        "weak": weak,
        "unique_moods": len(moods),
        "duplicate_queries": dup_queries,
        "unique_primary_queries": len(set(primary_queries)),
    }
