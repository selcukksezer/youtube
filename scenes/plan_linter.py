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

    try:
        from scenes.narration_validate import MIN_WORDS_PER_SCENE, scene_description_usable
        short_narr = sum(
            1 for s in scenes
            if len(((s.get("narration") or "").strip()).split()) < MIN_WORDS_PER_SCENE
        )
        bad_desc = sum(
            1 for s in scenes
            if not scene_description_usable(
                (s.get("scene_description") or "").strip()
                or str((s.get("search_queries") or [""])[0])
            )
        )
        if short_narr >= max(1, len(scenes) // 4):
            warnings.append(f"stub_narration:{short_narr}")
            weak = True
        if bad_desc >= max(1, len(scenes) // 4):
            warnings.append(f"placeholder_descriptions:{bad_desc}")
            weak = True
    except ImportError:
        pass

    return {
        "warnings": warnings,
        "weak": weak,
        "unique_moods": len(moods),
        "duplicate_queries": dup_queries,
        "unique_primary_queries": len(set(primary_queries)),
    }


def build_scenario_quality_dashboard_metrics(
    plans: List[Dict[str, Any]] | None = None,
    recent_limit: int = 25,
) -> Dict[str, Any]:
    """
    FUTURE_ROADMAP §5 #3: Aggregate scenario quality monitoring metrics across
    recent saved plans (`projects.plan_json`) or a supplied list of plan dicts.
    Combines `lint_plan_diversity`, `scene_narration_issues`, and `plan_quality_usable`.
    """
    import json
    from collections import Counter

    evaluated_plans: List[Dict[str, Any]] = []
    if plans is not None:
        evaluated_plans = [p for p in plans if isinstance(p, dict)]
    else:
        try:
            import database

            with database.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, title, niche, language, plan_json, updated_at
                    FROM projects
                    WHERE plan_json IS NOT NULL AND plan_json != ''
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (int(max(1, recent_limit)),),
                )
                for row in cur.fetchall():
                    try:
                        parsed = json.loads(row["plan_json"])
                        if isinstance(parsed, dict):
                            parsed.setdefault("project_id", row["id"])
                            parsed.setdefault("title", row["title"])
                            parsed.setdefault("niche_id", row["niche"])
                            parsed.setdefault("language", row["language"])
                            parsed.setdefault("updated_at", row["updated_at"])
                            evaluated_plans.append(parsed)
                    except Exception:
                        continue
        except Exception:
            evaluated_plans = []

    from scenes.narration_validate import (
        normalize_narration_for_validation,
        plan_quality_usable,
        scene_narration_issues,
    )

    issue_counter: Counter[str] = Counter()
    items: List[Dict[str, Any]] = []
    usable_count = 0
    weak_count = 0
    total_moods = 0
    total_unique_queries = 0
    total_words = 0

    for plan in evaluated_plans:
        scenes = [s for s in (plan.get("scenes") or []) if isinstance(s, dict)]
        lint = lint_plan_diversity(plan)
        usable = plan_quality_usable(scenes) if scenes else False
        if usable:
            usable_count += 1
        if lint.get("weak"):
            weak_count += 1

        for w in lint.get("warnings") or []:
            key = w.split(":", 1)[0]
            issue_counter[key] += 1

        scene_issues: List[str] = []
        words = 0
        for idx, sc in enumerate(scenes):
            narr = str(sc.get("narration") or "")
            words += len(normalize_narration_for_validation(narr).split())
            for iss in scene_narration_issues(narr):
                issue_counter[f"narration_{iss}"] += 1
                scene_issues.append(f"scene_{idx}:{iss}")

        validation = plan.get("validation") if isinstance(plan.get("validation"), dict) else {}
        for err in validation.get("errors") or []:
            issue_counter["validation_error"] += 1
            scene_issues.append(str(err))

        total_moods += int(lint.get("unique_moods") or 0)
        total_unique_queries += int(lint.get("unique_primary_queries") or 0)
        total_words += words

        items.append({
            "project_id": plan.get("project_id"),
            "title": str(plan.get("title") or "")[:90],
            "niche_id": plan.get("niche_id") or "general",
            "scene_count": len(scenes),
            "word_count": words,
            "usable": usable,
            "weak_diversity": bool(lint.get("weak")),
            "unique_moods": int(lint.get("unique_moods") or 0),
            "unique_primary_queries": int(lint.get("unique_primary_queries") or 0),
            "duplicate_queries": int(lint.get("duplicate_queries") or 0),
            "linter_warnings": list(lint.get("warnings") or []),
            "validation_issues": scene_issues[:10],
            "procedural_fallback": bool(plan.get("procedural_fallback")),
        })

    n = len(evaluated_plans)
    return {
        "rule": "future_roadmap_3_scenario_quality_dashboard",
        "total_evaluated": n,
        "usable_count": usable_count,
        "usable_rate_pct": round((usable_count / n) * 100.0, 1) if n else 100.0,
        "weak_plan_count": weak_count,
        "avg_unique_moods": round(total_moods / n, 2) if n else 0.0,
        "avg_unique_queries": round(total_unique_queries / n, 2) if n else 0.0,
        "avg_word_count": round(total_words / n, 1) if n else 0.0,
        "issue_breakdown": dict(issue_counter),
        "recent_plans": items,
    }

