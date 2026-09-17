"""
Scene generator facade — backwards compatibility module.
Delegates to the modular `scenes` package.
"""

from scenes import (
    PROMPT_TR,
    PROMPT_EN,
    PROMPT_VARIANTS_TR,
    get_rotated_system_prompt,
    _call,
    _clean_json,
    _detect_niche_and_terms,
    _generate_procedural_fallback_scenes,
    enrich_cinematic_search_queries,
    enforce_visual_cadence_14,
    verify_and_correct_hallucinations,
    verify_or_enrich_transformative_value,
    enforce_fair_use_2_5s_rule,
    COUNTER_ARGUMENT_PROMPT_TR,
    COUNTER_ARGUMENT_PROMPT_EN,
    generate_counter_argument_script,
    REDDIT_REWRITE_PROMPT_TR,
    REDDIT_REWRITE_PROMPT_EN,
    generate_reddit_rewrite_script,
    generate_scenes
)

__all__ = [
    "PROMPT_TR",
    "PROMPT_EN",
    "PROMPT_VARIANTS_TR",
    "get_rotated_system_prompt",
    "_call",
    "_clean_json",
    "_detect_niche_and_terms",
    "_generate_procedural_fallback_scenes",
    "enrich_cinematic_search_queries",
    "enforce_visual_cadence_14",
    "verify_and_correct_hallucinations",
    "verify_or_enrich_transformative_value",
    "enforce_fair_use_2_5s_rule",
    "COUNTER_ARGUMENT_PROMPT_TR",
    "COUNTER_ARGUMENT_PROMPT_EN",
    "generate_counter_argument_script",
    "REDDIT_REWRITE_PROMPT_TR",
    "REDDIT_REWRITE_PROMPT_EN",
    "generate_reddit_rewrite_script",
    "generate_scenes"
]
