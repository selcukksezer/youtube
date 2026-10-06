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


def _word_count(text: str) -> int:
    return len((text or "").split())


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


_PLAN_HOOK_RE = (
    ("shock_stat", re.compile(r"%\s*\d|\d+\s*%|yüzde\s+\d|\b\d+\s*kişiden\b", re.I)),
    ("problem_agitation", re.compile(r"sebep|düşündüğünüz|yanlış yerde|wearing you down|not what you think", re.I)),
    ("curiosity_gap", re.compile(r"söylemediği|kaydırmayın|nobody says|do not scroll|karar vermeyin", re.I)),
    ("cognitive_dissonance", re.compile(r"öğrenene kadar|tam tersi|yanılıyor|deliberately backwards|yanılsama", re.I)),
)


def opening_strategy_names() -> List[str]:
    return [name for name, _fn in _opening_strategies("konu", "tr")]


def _opening_strategies(title: str, lang: str) -> List[tuple[str, Any]]:
    """Plan 7.1 first, then the older engines. single_sentence stays in the ring."""
    return [
        ("cognitive_dissonance", lambda: ViralRetentionEngine.generate_cognitive_dissonance_hook(title, lang=lang)),
        ("curiosity_gap", lambda: ViralRetentionEngine.generate_curiosity_gap_hook(title, lang=lang)),
        ("shock_stat", lambda: ViralRetentionEngine.generate_shocking_statistic_hook(title, lang=lang)),
        ("problem_agitation", lambda: ViralRetentionEngine.generate_problem_agitation_hook(title, lang=lang)),
        ("zeigarnik", lambda: ViralRetentionEngine.generate_zeigarnik_hook(title, total_points=3, lang=lang)),
        ("narrow_audience", lambda: ViralRetentionEngine.generate_narrow_audience_hook(title, lang=lang)),
        ("emotional_bond", lambda: ViralRetentionEngine.generate_emotional_bond_hook(lang=lang)),
        ("single_sentence", lambda: ViralRetentionEngine.generate_single_sentence_identity_hook(title, lang=lang)),
    ]


def _split_first_sentence(text: str) -> tuple[str, str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip(), maxsplit=1)
    if len(parts) < 2:
        return (parts[0] if parts else "").strip(), ""
    return parts[0].strip(), parts[1].strip()


def _detect_plan_hook(sentence: str) -> Optional[str]:
    for name, pattern in _PLAN_HOOK_RE:
        if pattern.search(sentence or ""):
            return name
    return None


def _pick_opening_hook(title: str, lang: str, variation_attempt: int) -> tuple[str, str]:
    """Rotate hook generators by variation_attempt (Items 202, 203, 244, 248, 334)."""
    strategies = _opening_strategies(title, lang)
    name, fn = strategies[variation_attempt % len(strategies)]
    return name, fn()


def apply_retention_hooks_to_plan(
    plan: Dict[str, Any],
    title: str,
    lang: str = "tr",
    niche_type: Optional[str] = None,
    variation_attempt: int = 0,
    enable_outro: bool = True,
) -> Dict[str, Any]:
    """
    Inject retention hooks into first/last scene narration and attach SEO metadata.
    """
    scenes = list(plan.get("scenes") or [])
    if not scenes:
        return plan

    formula_id = _resolve_loop_formula_id(niche_type)
    formula = ViralRetentionEngine.get_loop_formula(formula_id)
    spoken = (scenes[0].get("narration") or "").strip()
    head, rest = _split_first_sentence(spoken)
    detected = _detect_plan_hook(head) if _word_count(head) >= 6 else None
    if detected:
        strategy, opening_hook = detected, head
    else:
        strategy, opening_hook = _pick_opening_hook(title, lang, variation_attempt)

    # Five facts already speak the facts. Do not paste a second hook,
    # a fake quote, or "3. kural" on top of them.
    niche_key = str(niche_type or plan.get("niche_id") or "")
    spoken_blob = " ".join((s.get("narration") or "") for s in scenes if isinstance(s, dict))
    from scenes.hadith_overlay import is_sacred_niche
    if is_sacred_niche(niche_key, title, spoken_blob):
        # Hadith and Qur'an lines stay as written. No "başa dön" loop in the voice.
        plan["retention_metadata"] = {
            "hook_strategy": "sacred_plain",
            "loop_formula_id": formula_id,
            "opening_hook": (scenes[0].get("narration") or "")[:160],
            "ending_bridge": "",
            "dopamin_split_screen": False,
        }
        return plan
    if niche_key.startswith("9_five"):
        plan["retention_metadata"] = {
            "hook_strategy": "five_facts",
            "loop_formula_id": formula_id,
            "opening_hook": (scenes[0].get("narration") or "")[:160],
            "ending_bridge": "",
            "dopamin_split_screen": False,
        }
        return plan

    # A finished sentence stays. A stub (under 8 words) still gets one hook.
    # Pasting the title onto a real fact is what made the voice nonsense.
    first = dict(scenes[0])
    body = (first.get("narration") or "").strip()
    clean_opening = re.sub(r'#\w+', '', opening_hook or '').strip()
    clean_body = (body or "").strip()
    norm_hook = re.sub(r'[^\w\s]', '', clean_opening.lower()).strip()
    norm_body = re.sub(r'[^\w\s]', '', clean_body.lower()).strip()

    if detected:
        pass
    elif norm_hook in norm_body or norm_body in norm_hook:
        first["narration"] = clean_body if len(clean_body.split()) >= 8 else clean_opening
    elif rest:
        norm_rest = re.sub(r'[^\w\s]', '', rest.lower()).strip()
        if norm_hook in norm_rest or norm_rest in norm_hook:
            first["narration"] = rest
        else:
            first["narration"] = f"{clean_opening} {rest}".strip()
    elif _word_count(clean_body) >= 8:
        first["narration"] = f"{clean_opening} {clean_body}".strip()
    elif _word_count(clean_body) < 8:
        if clean_body and strategy != "zeigarnik":
            tail_parts = re.split(r"(?<=[.!?])\s+", clean_body, maxsplit=1)
            if len(tail_parts) > 1 and tail_parts[1].strip():
                first["narration"] = f"{clean_opening} {tail_parts[1].strip()}"
            else:
                first["narration"] = clean_opening
        else:
            first["narration"] = f"{clean_opening} {clean_body}".strip() if clean_body else clean_opening
    scenes[0] = first

    # Item 204/198 / Plan 7.2: loop ending bridge on final scene (no generic farewell)
    last = dict(scenes[-1])
    closing_raw = _strip_farewell_closing(last.get("narration") or "")

    # Studio "Outro Sahnesi" off: keep the last fact, do not attach a loop CTA.
    if not enable_outro:
        from viral_retention_engine import _finish_spoken_line
        finished = _finish_spoken_line(closing_raw) or (last.get("narration") or "").strip()
        last["narration"] = finished
        scenes[-1] = last
        plan["scenes"] = scenes
        plan["enable_outro"] = False
        plan["retention_metadata"] = {
            "hook_strategy": strategy,
            "loop_formula_id": formula_id,
            "opening_hook": opening_hook,
            "ending_bridge": "",
            "seamless_loop_preview": finished,
            "perfect_loop_bridge": {
                "opening_line": opening_hook,
                "closing_line": finished,
                "loop_bridge": "",
                "preview_loop": finished,
            },
            "dopamin_split_screen": False,
        }
        return plan

    # If the AI or fallback already crafted a rich debate question / outro (ends with ? or has comment cue),
    # preserve that organic outro rather than overwriting it with a generic conjunction.
    has_organic_outro = bool(re.search(r"(\?|yorumlarda|yorumda|ne dersin|ne düşünüyorsun|what do you think|comment below)\s*$", closing_raw, re.I))
    if has_organic_outro:
        last["narration"] = closing_raw
        loop_res = {
            "ending_bridge": "",
            "preview_loop": f"{closing_raw} {opening_hook}".strip(),
            "seamless_closing": closing_raw,
        }
    else:
        # Synthesize seamless loop bridge connecting final scene narration directly into opening_hook
        loop_res = ViralRetentionEngine.synthesize_seamless_loop(
            opening_hook=opening_hook,
            final_narration=closing_raw,
            loop_formula_id=formula_id,
            video_index=variation_attempt,
            lang=lang,
        )
        last["narration"] = loop_res["seamless_closing"]
    scenes[-1] = last
    plan["scenes"] = scenes

    dilemma = ViralRetentionEngine.generate_polarizing_dilemma(title, lang=lang)
    # Item 207: dopamin split-screen — üst içerik / alt gameplay (varsayılan retention yolu)
    dopamin_split = variation_attempt % 2 == 0 or strategy in ("cognitive_dissonance", "narrow_audience")

    plan["retention_metadata"] = {
        "hook_strategy": strategy,
        "loop_formula_id": formula_id,
        "opening_hook": opening_hook,
        "ending_bridge": loop_res["ending_bridge"],
        "seamless_loop_preview": loop_res["preview_loop"],
        "perfect_loop_bridge": {
            "opening_line": opening_hook,
            "closing_line": loop_res["seamless_closing"],
            "loop_bridge": loop_res["ending_bridge"],
            "preview_loop": loop_res["preview_loop"],
        },
        "polarizing_dilemma": dilemma,
        "dopamin_split_screen": dopamin_split,
        "spotted_mistake_bait": ViralRetentionEngine.generate_spotted_mistake_bait(title),
        "role_play_hook": ViralRetentionEngine.generate_role_play_hook(title, lang=lang),
        "share_cta": ViralRetentionEngine.generate_share_cta(title, lang=lang),
        "bookmark_cta": ViralRetentionEngine.generate_bookmark_cta(title, lang=lang),
        "pinned_comment_bait": ViralRetentionEngine.generate_pinned_comment_bait(title, lang=lang),
    }
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
    enable_outro: bool = True,
) -> Dict[str, Any]:
    """
    Idempotent production entry: inject opening/closing retention hooks once,
    rebuild full_narration, log strategy for render terminal visibility.
    """
    if not plan or not plan.get("scenes"):
        return plan

    meta = plan.get("retention_metadata") or {}
    if not force and meta.get("hook_strategy") and meta.get("opening_hook"):
        # Hooks may already exist while a caller changed scene narration. Keep
        # the aggregate narration contract synchronized on idempotent calls.
        _rebuild_full_narration(plan)
        return plan

    plan = apply_retention_hooks_to_plan(
        plan, title, lang=lang, niche_type=niche_type, variation_attempt=variation_attempt,
        enable_outro=enable_outro,
    )

    scenes = plan.get("scenes") or []
    # Skip celebrity name injection on religious / sacred niches — mangling
    # "Hz Peygamber" with "Einstein'ın …" is niche-inappropriate (Item 240 opt-out).
    _niche = (niche_type or plan.get("niche_id") or "").lower()
    from scenes.hadith_overlay import is_sacred_niche
    _skip_trigger = _niche.startswith(
        ("10_religious", "11_quran", "4_mystery", "13_mystery", "religious")
    ) or is_sacred_niche(_niche, title)
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
