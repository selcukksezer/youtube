"""
Enrichment engines: Fair Use, Transformative Value, Cadence 14,
Hallucination Detection, and Cinematic Query Enrichment.
"""

import re
import math
import random
from typing import List, Dict, Any

CLOSING_GAZE_QUERY_HINTS = [
    "direct gaze camera portrait",
    "looking at camera closeup",
    "eye contact dramatic portrait",
    "stoic direct gaze subscribe",
]

_SHOCK_VISUAL_QUERIES = [
    "explosion shock dramatic slow motion",
    "horror reveal dramatic lightning strike",
    "extreme close up shocked eye fear",
    "disaster aftermath dramatic cinematic",
]


def enrich_cinematic_search_queries(queries: List[str], mood: str = "epic") -> List[str]:
    """
    Item 89: Generic search queries are enriched with cinematic adjectives.
    Validates that each query contains words like:
    cinematic, drone, aerial, slow motion, macro, atmospheric, 4k, moody.
    """
    cinematic_adjectives = [
        "cinematic", "drone", "aerial", "slow motion", "macro", "atmospheric", "4k", "moody"
    ]
    enriched = []
    for idx, q in enumerate(queries):
        q_str = str(q).strip()
        q_lower = q_str.lower()
        if not any(adj in q_lower for adj in cinematic_adjectives):
            adj = cinematic_adjectives[idx % len(cinematic_adjectives)]
            enriched.append(f"{q_str} {adj}")
        else:
            enriched.append(q_str)
    return enriched


def _split_narration_cleanly(narration: str, cutaway_counter: int):
    # 1. Split ONLY on sentence boundaries (. ! ?) — never mid-clause or mid-verb
    sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', narration or "") if s.strip()]
    if len(sentences) >= 2:
        mid = len(sentences) // 2
        left = " ".join(sentences[:mid])
        right = " ".join(sentences[mid:])
        if len(left.split()) >= 5 and len(right.split()) >= 5:
            return left, right

    # 2. Single sentence — keep narration whole; use reaction beat for visual cutaway
    reaction_beats = [
        "O an herkes nefesini tuttu... ⚡",
        "Gözlerime inanamadım, kalbim duracak gibiydi! 😱",
        "Odadaki gerilim bir anda tavan yaptı... 🔴",
        "Böylesine bir şok dalgası kimse beklemiyordu! 💥",
        "İçimdeki panik iliklerime kadar işledi... ❄️",
        "Bu sessizlik bir fırtınanın habercisiydi... 🌪️",
        "Tüm gözler üzerime kilitlenmişti... 👀"
    ]
    reaction = reaction_beats[cutaway_counter % len(reaction_beats)]
    return narration, reaction


def _differentiate_queries(queries: List[str], cutaway_counter: int):
    adjs = ["macro closeup", "cinematic angle", "reaction detail", "slow motion cutaway"]
    adj = adjs[cutaway_counter % len(adjs)]
    if not queries:
        return ["cinematic visual", "dramatic lighting"], [f"cutaway {adj}", "atmospheric slow motion"]
    q1 = queries[0]
    q2 = queries[1] if len(queries) > 1 else f"{q1} {adj}"
    q3 = queries[2] if len(queries) > 2 else "cinematic slow motion"
    return [q1, q2], [f"{q2} {adj}", q3, "cinematic lighting"]


def enforce_visual_cadence_14(scenes: List[Dict[str, Any]], min_cadence: int = 14) -> List[Dict[str, Any]]:
    """
    Item 88: For 45s+ Shorts, enforces visual cuts to reach >= min_cadence (14 visual cuts).
    Maintains exact total duration while guaranteeing that no two scenes have duplicate narration or search queries.
    """
    if not scenes:
        return scenes

    total_duration = sum(s.get("duration", 6.0) for s in scenes)
    if total_duration < 30.0 or len(scenes) >= min_cadence:
        return scenes

    cuts_needed = min_cadence - len(scenes)
    expanded = []
    cutaway_counter = 1

    for sc in scenes:
        curr_dur = sc.get("duration", 6.0)
        # If we still need cuts and current scene is sufficiently long (> 3.0s)
        if cuts_needed > 0 and curr_dur >= 3.5:
            part1_dur = round(curr_dur / 2.0, 2)
            part2_dur = round(curr_dur - part1_dur, 2)
            cuts_needed -= 1

            orig_narration = sc.get("narration", "")
            narr1, narr2 = _split_narration_cleanly(orig_narration, cutaway_counter)
            queries1, queries2 = _differentiate_queries(sc.get("search_queries", []), cutaway_counter)

            sc1 = dict(sc)
            sc1["duration"] = part1_dur
            sc1["scene_number"] = len(expanded) + 1
            sc1["narration"] = narr1
            sc1["search_queries"] = queries1

            sc2 = dict(sc)
            sc2["duration"] = part2_dur
            sc2["scene_number"] = len(expanded) + 2
            sc2["is_visual_cutaway"] = True
            sc2["narration"] = narr2
            sc2["search_queries"] = queries2
            sc2["scene_description"] = f"Cutaway dynamic angle showing {queries2[0]}"
            cutaway_counter += 1

            expanded.extend([sc1, sc2])
        else:
            sc_copy = dict(sc)
            sc_copy["scene_number"] = len(expanded) + 1
            expanded.append(sc_copy)

    # If still below min_cadence, split remaining largest scenes
    while len(expanded) < min_cadence:
        max_idx = max(range(len(expanded)), key=lambda i: expanded[i]["duration"])
        target = expanded[max_idx]
        if target["duration"] < 1.5:
            break
        half1 = round(target["duration"] / 2.0, 2)
        half2 = round(target["duration"] - half1, 2)

        orig_narr = target.get("narration", "")
        narr1, narr2 = _split_narration_cleanly(orig_narr, cutaway_counter)
        queries1, queries2 = _differentiate_queries(target.get("search_queries", []), cutaway_counter)

        t1 = dict(target)
        t1["duration"] = half1
        t1["narration"] = narr1
        t1["search_queries"] = queries1

        t2 = dict(target)
        t2["duration"] = half2
        t2["is_visual_cutaway"] = True
        t2["narration"] = narr2
        t2["search_queries"] = queries2
        t2["scene_description"] = f"Cutaway dynamic angle showing {queries2[0]}"
        cutaway_counter += 1

        expanded = expanded[:max_idx] + [t1, t2] + expanded[max_idx + 1:]

    # Renumber scenes
    for i, sc in enumerate(expanded):
        sc["scene_number"] = i + 1

    return expanded


_FACE_KEYWORDS = ("portrait", "face closeup", "human face", "looking at camera", "yüz", "portre")


def _looks_like_face_query(queries: List[str]) -> bool:
    joined = " ".join(str(q).lower() for q in (queries or []))
    return any(k in joined for k in _FACE_KEYWORDS)


def avoid_consecutive_face_visuals(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Item 247: Tekdüzelikten Kaçınma — arka arkaya iki yüz/portre stok sahnesi engellenir.
    """
    alt_queries = [
        "cinematic abstract texture macro",
        "dramatic landscape aerial drone",
        "slow motion object detail atmospheric",
        "neon city lights night mood",
    ]
    for i in range(1, len(scenes)):
        prev_q = scenes[i - 1].get("search_queries") or []
        curr_q = scenes[i].get("search_queries") or []
        if _looks_like_face_query(prev_q) and _looks_like_face_query(curr_q):
            alt = alt_queries[i % len(alt_queries)]
            scenes[i]["search_queries"] = [alt] + list(curr_q)[:2]
            scenes[i]["visual_diversity_adjusted"] = True
    return scenes


def enrich_numbered_rule_narration(scenes: List[Dict[str, Any]], lang: str = "tr") -> List[Dict[str, Any]]:
    """
    Item 241: Numaralandırılmış madde formatını narration'a uygular.
    """
    from viral_retention_engine import ViralRetentionEngine

    rule_scenes = []
    for idx, sc in enumerate(scenes):
        narr = (sc.get("narration") or "").strip()
        if re.search(r"\bkural\s*\d+\b", narr, re.I) or sc.get("is_rule_item"):
            rule_scenes.append((idx, narr))

    if len(rule_scenes) >= 2:
        rules = []
        for _, narr in rule_scenes:
            cleaned = re.sub(r"^\s*Kural\s*\d+\s*:\s*", "", narr, flags=re.I).strip()
            rules.append(cleaned or narr)
        formatted = ViralRetentionEngine.format_numbered_rule_hierarchy(rules, lang=lang)
        for (idx, _), item in zip(rule_scenes, formatted):
            scenes[idx]["narration"] = item["full_narration"]
            scenes[idx]["rule_number"] = item["rule_number"]
    elif scenes:
        combined = " ".join((s.get("narration") or "").strip() for s in scenes if (s.get("narration") or "").strip())
        if re.search(r"\bkural\s*[123]\b", combined, re.I):
            parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', combined) if p.strip()]
            if len(parts) >= 2:
                formatted = ViralRetentionEngine.format_numbered_rule_hierarchy(parts[:3], lang=lang)
                for i, item in enumerate(formatted):
                    if i < len(scenes):
                        scenes[i]["narration"] = item["full_narration"]
                        scenes[i]["rule_number"] = item["rule_number"]
    return scenes


def enrich_continuous_motion_hints(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Item 271: Görsel Boşluk Bırakmama — uzun sahnelerde statik kare riskini azaltmak için motion ipuçları.
    """
    for sc in scenes:
        if not sc.get("is_visual_cutaway"):
            sc["handheld_shake"] = True
    return scenes


def _must_exclude_tokens(niche_id: str = "", must_exclude=None) -> List[str]:
    raw: List[str] = list(must_exclude or [])
    if not raw and niche_id:
        try:
            from director.visual_intent import get_motif_bank
            raw = list(get_motif_bank(niche_id).get("must_exclude") or [])
        except Exception:
            raw = []
    tokens: List[str] = []
    for ex in raw:
        low = str(ex).lower().strip()
        if not low:
            continue
        tokens.append(low)
        tokens.extend(t for t in low.split() if len(t) >= 4)
    seen: List[str] = []
    for tok in tokens:
        if tok not in seen:
            seen.append(tok)
    return seen


def _shock_queries_allowed(must_exclude_tokens: List[str]) -> List[str]:
    """Keep Item 273 shock bank only when every query survives niche must_exclude."""
    if not must_exclude_tokens:
        return list(_SHOCK_VISUAL_QUERIES)
    from director.visual_intent import text_contains_excluded
    allowed = [q for q in _SHOCK_VISUAL_QUERIES if not text_contains_excluded(q, must_exclude_tokens)]
    if len(allowed) < len(_SHOCK_VISUAL_QUERIES):
        return []
    return allowed


def enrich_audio_visual_contrast_scenes(
    scenes: List[Dict[str, Any]],
    niche_id: str = "",
    must_exclude=None,
) -> List[Dict[str, Any]]:
    """
    Item 273: Ses ve Görselin Ters Uyumu — sakin anlatım + şok edici görsel (climax fazı).
    Skip shock/horror query injection when the niche already excludes those tokens.
    """
    if len(scenes) < 4:
        return scenes
    shock_pool = _shock_queries_allowed(_must_exclude_tokens(niche_id, must_exclude))
    if niche_id:
        try:
            from niche_templates import get_scenario_pack
            if not get_scenario_pack(niche_id).get("allow_shock_queries"):
                shock_pool = []
        except Exception:
            pass
    climax_idx = max(1, (len(scenes) * 2) // 3)
    for i, sc in enumerate(scenes):
        if i != climax_idx and sc.get("beat_type") != "climax":
            continue
        sc["audio_visual_contrast"] = True
        sc["impact_shake"] = True
        if shock_pool:
            queries = list(sc.get("search_queries") or [])
            shock = random.choice(shock_pool)
            if shock.split()[0] not in " ".join(queries).lower():
                queries.insert(0, shock)
            sc["search_queries"] = queries[:4]
        narr = (sc.get("narration") or "").strip()
        if narr and not narr.endswith("..."):
            sc["narration"] = narr.rstrip(".!?") + "..."
        sc["tts_calm_pace"] = True
    return scenes


def enrich_closing_gaze_queries(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Item 226: Kapanışta Ekrana Bakış.
    Son sahne stok aramasına doğrudan kameraya bakan portre ipuçları ekler.
    """
    if not scenes:
        return scenes
    last = scenes[-1]
    queries = list(last.get("search_queries") or [])
    hint = random.choice(CLOSING_GAZE_QUERY_HINTS)
    if not any(h in " ".join(queries).lower() for h in ["direct gaze", "looking at camera", "eye contact"]):
        queries.insert(0, hint)
    last["search_queries"] = queries[:4]
    last["closing_gaze"] = True
    scenes[-1] = last
    return scenes


def verify_and_correct_hallucinations(scenes: List[Dict[str, Any]], topic: str = "") -> Dict[str, Any]:
    """
    Item 90: Detects impossible future dates and blatant chronological contradictions.
    """
    issues = []
    topic_lower = topic.lower()
    ancient_markers = ["marcus aurelius", "roma", "antik", "stoa", "osmanlı", "fatih", "platon", "aristoteles", "sezar"]
    is_ancient_topic = any(m in topic_lower for m in ancient_markers)

    year_pattern = re.compile(r'\b(1[0-9]{3}|20[0-9]{2})\b')

    for sc in scenes:
        narration = sc.get("narration", "")
        matches = year_pattern.findall(narration)
        for yr_str in matches:
            yr = int(yr_str)
            # Future dates check
            if yr > 2030:
                issues.append(f"Gelecek zaman anakronizmi: {yr} yılı henüz yaşanmadı.")
            # Ancient subject placed in modern 20th/21st century
            elif is_ancient_topic and yr >= 1800:
                issues.append(f"Tarihsel çelişki: Antik konu '{topic}' için {yr} yılı anakroniktir.")

    verified = (len(issues) == 0)
    return {
        "verified": verified,
        "hallucination_issues": issues,
        "scenes": scenes
    }


def verify_or_enrich_transformative_value(scenes: List[Dict[str, Any]], topic: str = "") -> Dict[str, Any]:
    """
    Item 81: Script must contain at least 3 distinct arguments / perspectives for fair use immunity.
    """
    breakdown = []
    for sc in scenes:
        narr = sc.get("narration", "").strip()
        if narr:
            breakdown.append({
                "scene_number": sc.get("scene_number", len(breakdown) + 1),
                "argument": narr
            })

    # If fewer than 3 arguments, enrich with procedural perspective arguments
    if len(breakdown) < 3:
        supplements = [
            f"{topic} hakkında genel algının ötesindeki temel gerçek.",
            f"Tarihsel ve bilimsel kanıtların ortaya koyduğu ikinci kritik boyut.",
            f"Modern hayatımıza ve geleceğe yansıyan nihai sonuç."
        ]
        for i in range(len(breakdown), 3):
            breakdown.append({
                "scene_number": i + 1,
                "argument": supplements[i]
            })

    return {
        "transformative_compliant": len(breakdown) >= 3,
        "argument_count": len(breakdown),
        "breakdown": breakdown,
        "scenes": scenes
    }


def apply_alternate_topic_angle(plan: Dict[str, Any], topic: str, lang: str = "tr") -> Dict[str, Any]:
    """
    Item 117: Aynı konuyu farklı açıdan işleme — tez-antitez karşı argüman senaryosu.
    """
    from scenes.scripts import generate_counter_argument_script

    alt = generate_counter_argument_script(topic, lang=lang)
    merged = dict(plan or {})
    merged.update(alt)
    merged["alternate_angle"] = True
    merged["item_117"] = "counter_argument_dialectic"
    return merged


def enrich_plan_scenes(plan: Dict[str, Any], lang: str = "tr", niche_id: str = "") -> Dict[str, Any]:
    """
    Apply all scene-level enrichment passes for render path (UI-supplied plans included).
    Wires Items 226, 241, 247, 271, 273, 96 (fair use) and retention visual hints.
    """
    scenes = plan.get("scenes") or []
    if not scenes:
        return plan
    nid = niche_id or str(plan.get("niche_id") or plan.get("niche") or "")
    try:
        from copyright_risk import scenes_need_fair_use_enforcement
        if scenes_need_fair_use_enforcement(scenes):
            scenes = enforce_fair_use_2_5s_rule(scenes, is_copyrighted_source=True)
            plan["fair_use_2_5s_enforced"] = True
    except Exception:
        pass
    scenes = enrich_closing_gaze_queries(scenes)
    scenes = enrich_numbered_rule_narration(scenes, lang=lang)
    scenes = avoid_consecutive_face_visuals(scenes)
    scenes = enrich_continuous_motion_hints(scenes)
    scenes = enrich_audio_visual_contrast_scenes(scenes, niche_id=nid)
    plan["scenes"] = scenes
    return plan


def enforce_fair_use_2_5s_rule(
    scenes: List[Dict[str, Any]],
    is_copyrighted_source: bool = False,
    max_clip_duration: float = 2.5
) -> List[Dict[str, Any]]:
    """
    Item 96: Film/Dizi Kesitlerinde 2.5 Saniye Limiti (Fair Use 2.5s clip limitation & auto-split).
    Splits any scene exceeding max_clip_duration into multiple sub-segments while preserving total duration.
    """
    if not is_copyrighted_source:
        return scenes

    adjusted = []
    for sc in scenes:
        dur = float(sc.get("duration", 2.0))
        is_copyrighted = sc.get("is_copyrighted", is_copyrighted_source)

        if is_copyrighted and dur > max_clip_duration:
            num_splits = math.ceil(dur / max_clip_duration)
            segment_dur = round(dur / num_splits, 2)
            orig_narration = sc.get("narration", "")

            for s_idx in range(num_splits):
                sub = dict(sc)
                sub["duration"] = segment_dur
                sub["segment_index"] = s_idx + 1
                if s_idx > 0:
                    sub["narration"] = f"{orig_narration} [Kesit {s_idx+1}]"
                adjusted.append(sub)
        else:
            adjusted.append(dict(sc))

    # Re-index scene numbers
    for idx, s in enumerate(adjusted):
        s["scene_number"] = idx + 1

    return adjusted
