"""
Production wiring for viral retention hooks (Items 202-204, 209-210, 239, 244, 248, 257).
Called from scenes/generator.py after enrichment, before trigger-name inject.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from viral_retention_engine import ViralRetentionEngine

_FAREWELL_RE = re.compile(
    r"(?i)\b("
    r"hoşça\s+kal|görüşürüz|bye|goodbye|"
    r"teşekkürler\s+izlediğiniz|thanks\s+for\s+watching|"
    r"abone\s+olmayı\s+unutmayın|kanalıma\s+hoş\s+geldiniz"
    r")\b[^.!?]*[.!?]?"
)


def _strip_farewell_closing(text: str) -> str:
    """Item 198: drop generic veda/kapanış — loop bridge replaces it."""
    cleaned = _FAREWELL_RE.sub("", text or "").strip()
    return re.sub(r"\s+", " ", cleaned).strip(" .,")


def _resolve_loop_formula_id(niche_type: Optional[str]) -> str:
    try:
        from niche_templates import NICHES

        niche = NICHES.get(niche_type or "", NICHES["1_news_flash"])
        return niche.get("loop_formula", "cause_and_effect")
    except Exception:
        return "cause_and_effect"


def _pick_opening_hook(title: str, lang: str, variation_attempt: int) -> tuple[str, str]:
    """Rotate hook generators by variation_attempt (Items 202, 203, 244, 248, 334)."""
    strategies: List[tuple[str, Any]] = [
        ("cognitive_dissonance", lambda: ViralRetentionEngine.generate_cognitive_dissonance_hook(title, lang=lang)),
        ("zeigarnik", lambda: ViralRetentionEngine.generate_zeigarnik_hook(title, total_points=3, lang=lang)),
        ("narrow_audience", lambda: ViralRetentionEngine.generate_narrow_audience_hook(title, lang=lang)),
        ("emotional_bond", lambda: ViralRetentionEngine.generate_emotional_bond_hook(lang=lang)),
        ("single_sentence", lambda: ViralRetentionEngine.generate_single_sentence_identity_hook(title, lang=lang)),
    ]
    name, fn = strategies[variation_attempt % len(strategies)]
    return name, fn()


def apply_retention_hooks_to_plan(
    plan: Dict[str, Any],
    title: str,
    lang: str = "tr",
    niche_type: Optional[str] = None,
    variation_attempt: int = 0,
) -> Dict[str, Any]:
    """
    Inject retention hooks into first/last scene narration and attach SEO metadata.
    """
    scenes = list(plan.get("scenes") or [])
    if not scenes:
        return plan

    formula_id = _resolve_loop_formula_id(niche_type)
    formula = ViralRetentionEngine.get_loop_formula(formula_id)
    strategy, opening_hook = _pick_opening_hook(title, lang, variation_attempt)

    # Item 202/203/244/248: first-scene hook (preserve body after first sentence when possible)
    first = dict(scenes[0])
    body = (first.get("narration") or "").strip()
    if body and strategy != "zeigarnik":
        tail_parts = re.split(r"(?<=[.!?])\s+", body, maxsplit=1)
        if len(tail_parts) > 1 and tail_parts[1].strip():
            first["narration"] = f"{opening_hook} {tail_parts[1].strip()}"
        else:
            first["narration"] = opening_hook
    else:
        first["narration"] = f"{opening_hook} {body}".strip() if body else opening_hook
    scenes[0] = first

    # Item 204/198: loop ending bridge on final scene (no generic farewell)
    bridge = (formula.get("ending_bridge") or "").strip().lstrip(".")
    last = dict(scenes[-1])
    closing = _strip_farewell_closing(last.get("narration") or "")

    if variation_attempt % 3 == 2:
        twist = ViralRetentionEngine.generate_plot_twist_closing(title, lang=lang)
        closing = f"{closing} {twist}".strip() if closing else twist

    # Item 345: perfect seamless loop bridge (closing flows into opening)
    perfect_loop = None
    if variation_attempt % 4 == 3:
        try:
            from hybrid_niches import generate_perfect_seamless_loop_bridge
            perfect_loop = generate_perfect_seamless_loop_bridge(opening_hook, video_index=variation_attempt, lang=lang)
            loop_close = (perfect_loop.get("closing_line") or "").strip()
            if loop_close:
                closing = loop_close
        except ImportError:
            perfect_loop = None

    if bridge and not perfect_loop:
        closing = f"{closing} {bridge}".strip() if closing else bridge

    last["narration"] = closing.strip()
    scenes[-1] = last
    plan["scenes"] = scenes

    dilemma = ViralRetentionEngine.generate_polarizing_dilemma(title, lang=lang)
    # Item 207: dopamin split-screen — üst içerik / alt gameplay (varsayılan retention yolu)
    dopamin_split = variation_attempt % 2 == 0 or strategy in ("cognitive_dissonance", "narrow_audience")

    plan["retention_metadata"] = {
        "hook_strategy": strategy,
        "loop_formula_id": formula_id,
        "opening_hook": opening_hook,
        "ending_bridge": bridge,
        "polarizing_dilemma": dilemma,
        "dopamin_split_screen": dopamin_split,
        "spotted_mistake_bait": ViralRetentionEngine.generate_spotted_mistake_bait(title),
        "role_play_hook": ViralRetentionEngine.generate_role_play_hook(title, lang=lang),
        "share_cta": ViralRetentionEngine.generate_share_cta(title, lang=lang),
        "bookmark_cta": ViralRetentionEngine.generate_bookmark_cta(title, lang=lang),
        "pinned_comment_bait": ViralRetentionEngine.generate_pinned_comment_bait(title, lang=lang),
    }
    if perfect_loop:
        plan["retention_metadata"]["perfect_loop_bridge"] = perfect_loop
    if dopamin_split:
        plan["hybrid_split_screen"] = True
    return plan


def _rebuild_full_narration(plan: Dict[str, Any]) -> None:
    scenes = plan.get("scenes") or []
    plan["full_narration"] = " ".join(
        (s.get("narration") or "").strip()
        for s in scenes
        if isinstance(s, dict) and (s.get("narration") or "").strip()
    )


def ensure_retention_hooks_on_plan(
    plan: Dict[str, Any],
    title: str,
    lang: str = "tr",
    niche_type: Optional[str] = None,
    variation_attempt: int = 0,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Idempotent production entry: inject opening/closing retention hooks once,
    rebuild full_narration, log strategy for render terminal visibility.
    """
    if not plan or not plan.get("scenes"):
        return plan

    meta = plan.get("retention_metadata") or {}
    if not force and meta.get("hook_strategy") and meta.get("opening_hook"):
        return plan

    plan = apply_retention_hooks_to_plan(
        plan, title, lang=lang, niche_type=niche_type, variation_attempt=variation_attempt
    )

    scenes = plan.get("scenes") or []
    # Skip celebrity name injection on religious / sacred niches — mangling
    # "Hz Peygamber" with "Einstein'ın …" is niche-inappropriate (Item 240 opt-out).
    _niche = (niche_type or plan.get("niche_id") or "").lower()
    _skip_trigger = _niche.startswith(
        ("10_religious", "11_quran", "4_mystery", "13_mystery", "religious")
    )
    if scenes and not _skip_trigger:
        first_narr = (scenes[0].get("narration") or "").strip()
        if first_narr:
            scenes[0]["narration"] = ViralRetentionEngine.inject_trigger_name_hook(
                first_narr, topic=title, lang=lang
            )

    _rebuild_full_narration(plan)
    meta = plan.get("retention_metadata") or {}
    opening = (meta.get("opening_hook") or "")[:72]
    bridge = (meta.get("ending_bridge") or "")[:48]
    print(
        f"  [RetentionHooks] strategy={meta.get('hook_strategy')} | "
        f"opening=\"{opening}{'…' if len(meta.get('opening_hook') or '') > 72 else ''}\" | "
        f"loop_bridge=\"{bridge}{'…' if len(meta.get('ending_bridge') or '') > 48 else ''}\""
    )
    return plan
