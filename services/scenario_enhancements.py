from __future__ import annotations

import hashlib
import re
from typing import Any


# Problem #31: 6-Word Stub Scene Expansion
def expand_six_word_stub_scene(
    scene_text: str,
    topic: str,
    scene_index: int = 1,
    min_words: int = 12,
) -> str:
    """Expands overly short stub scenes (< min_words) with contextual detail."""
    cleaned = (scene_text or "").strip()
    words = cleaned.split()
    if len(words) >= min_words:
        return cleaned

    clean_topic = (topic or "bu kritik gelişme").strip().rstrip(".!?")
    expansions = [
        f"Özellikle {clean_topic} sürecinde perde arkasındaki detaylar dengeleri tamamen değiştiriyor.",
        f"Uzmanların {clean_topic} hakkındaki son verileri piyasadaki beklentiyi yeniden şekillendiriyor.",
        f"Bu noktada {clean_topic} etrafında oluşan yeni dalga herkesi doğrudan etkiliyor.",
        f"Sonuç olarak {clean_topic} cephesindeki bu kırılma önümüzdeki günlerin ana gündemi olacak.",
    ]
    addon = expansions[scene_index % len(expansions)]
    if not cleaned:
        return addon
    if cleaned[-1] not in ".!?":
        cleaned += "."
    expanded = f"{cleaned} {addon}"
    return expanded


# Problem #32: Enriched Plan Word Budget Rebalancer
def rebalance_enriched_plan_word_budget(
    scenes: list[dict[str, Any]],
    target_duration_sec: float = 55.0,
    words_per_sec: float = 2.55,
) -> list[dict[str, Any]]:
    """Caps and rebalances scene word counts so enriched overlays/narration don't overflow target duration."""
    max_total_words = max(25, int(round(target_duration_sec * words_per_sec)))
    if not scenes:
        return []

    total_words = sum(len(str(s.get("text", "")).split()) for s in scenes)
    if total_words <= max_total_words:
        return [dict(s) for s in scenes]

    ratio = max_total_words / float(max(total_words, 1))
    rebalanced: list[dict[str, Any]] = []
    for scene in scenes:
        copied = dict(scene)
        words = str(copied.get("text", "")).split()
        allowed = max(8, int(round(len(words) * ratio)))
        if len(words) > allowed:
            trimmed = " ".join(words[:allowed]).rstrip(",;:")
            if trimmed and trimmed[-1] not in ".!?":
                trimmed += "."
            copied["text"] = trimmed
            copied["word_budget_trimmed"] = True
        rebalanced.append(copied)
    return rebalanced


# Problem #33: English Query Suffix Deduplicator
def deduplicate_cinematic_query_suffixes(query: str) -> str:
    """Removes redundant 'vertical 9:16 cinematic 4k' tokens while preserving core visual nouns."""
    if not query:
        return "cinematic vertical scene"
    tokens = re.split(r"\s+", query.strip())
    seen: set[str] = set()
    boilerplate = {"vertical", "9:16", "4k", "8k", "hd", "uhd", "wallpaper", "stock", "video", "footage"}
    core_tokens: list[str] = []
    style_tokens: list[str] = []

    for tok in tokens:
        norm = tok.lower().strip(",.;:")
        if not norm or norm in seen:
            continue
        seen.add(norm)
        if norm in boilerplate or norm == "cinematic":
            style_tokens.append(norm)
        else:
            core_tokens.append(tok)

    result_tokens = core_tokens[:7]
    if "cinematic" not in [t.lower() for t in result_tokens]:
        result_tokens.append("cinematic")
    return " ".join(result_tokens).strip()


# Problem #34: Clause-Preserving Cadence Splitter
def preserve_clause_integrity_on_cadence_split(
    text: str,
    max_words_per_segment: int = 14,
) -> list[str]:
    """Splits long sentences at natural punctuation or conjunction boundaries rather than mid-clause."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    words = cleaned.split()
    if len(words) <= max_words_per_segment:
        return [cleaned]

    # Prefer splitting on punctuation or Turkish conjunctions
    clauses = re.split(r"(?<=[.!?;,:])\s+|\s+(?=ama\b|fakat\b|ancak\b|çünkü\b|üstelik\b|böylece\b)", cleaned)
    segments: list[str] = []
    current: list[str] = []
    current_count = 0

    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue
        c_words = clause.split()
        if current_count + len(c_words) <= max_words_per_segment or not current:
            current.append(clause)
            current_count += len(c_words)
        else:
            segments.append(" ".join(current))
            current = [clause]
            current_count = len(c_words)

    if current:
        segments.append(" ".join(current))
    return segments


# Problem #35: Procedural Fallback Template Rotator
def rotate_procedural_fallback_variant(
    niche_id: str,
    topic: str,
    run_seed: str | int = 0,
) -> dict[str, Any]:
    """Rotates across 5 distinct narrative archetypes when offline procedural fallback is used."""
    archetypes = [
        {
            "archetype": "mystery_reveal",
            "hook": f"{topic} hakkında kimsenin fark etmediği gizli detay ortaya çıktı!",
            "cta": "Sizce bu sır gerçek mi? Yorumlara yazın!",
        },
        {
            "archetype": "contrarian_shock",
            "hook": f"{topic} konusunda bildiğiniz her şey bugün tamamen değişiyor!",
            "cta": "Katılıyor musunuz yoksa karşı mı çıkıyorsunuz?",
        },
        {
            "archetype": "timeline_countdown",
            "hook": f"60 saniyede {topic} sürecini değiştiren 3 kritik kırılma noktası!",
            "cta": "En çok hangisi şaşırttı? Yorumda buluşalım!",
        },
        {
            "archetype": "analytical_breakdown",
            "hook": f"Rakamlar yalan söylemez: {topic} verilerinde büyük sinyal!",
            "cta": "Bu veriyi kaydetmeyi ve abone olmayı unutmayın!",
        },
        {
            "archetype": "urgent_warning",
            "hook": f"Dikkat! {topic} cephesinde son 24 saatin en kritik gelişmesi!",
            "cta": "Güncel gelişmeler için kanalı takip edin!",
        },
    ]
    digest = hashlib.sha256(f"{niche_id}:{topic}:{run_seed}".encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(archetypes)
    selected = dict(archetypes[idx])
    selected["variant_index"] = idx
    return selected


# Problem #36: Script Sentiment-to-BGM Mood Selector
def select_bgm_by_script_sentiment(script_text: str, default_mood: str = "dark_ambient") -> dict[str, str]:
    """Analyzes script keywords to automatically pick the best BGM mood and tempo band."""
    lower = (script_text or "").lower()
    mood_rules: list[tuple[str, str, list[str]]] = [
        ("spiritual_ney", "60-80", ["dua", "huzur", "kalp", "sabah", "şafak", "bereket", "amin", "ayet"]),
        ("urgent_pulse", "110-130", ["bitcoin", "kripto", "çöküş", "panik", "alarm", "acil", "kırılım", "borsa"]),
        ("mystic_celestial", "80-100", ["burç", "merkür", "astroloji", "koç", "akrep", "retro", "yıldız", "evren"]),
        ("epic_cinematic", "100-120", ["imparatorluk", "savaş", "zafer", "tarih", "devrim", "lider", "fetih"]),
    ]
    for mood, tempo_band, keywords in mood_rules:
        if any(k in lower for k in keywords):
            return {"bgm_mood": mood, "tempo_band": tempo_band, "matched": "sentiment"}
    return {"bgm_mood": default_mood, "tempo_band": "80-120", "matched": "default"}


# Problem #37: Dynamic Narrator Persona Adapter
def apply_narrator_persona_profile(
    persona: str,
    base_voice: str = "tr-TR-AhmetNeural",
) -> dict[str, Any]:
    """Maps narrator persona ('street_interviewer', 'calm_sage', ' energetic_analyst', etc.) to TTS prosody."""
    personas: dict[str, dict[str, Any]] = {
        "street_interviewer": {
            "voice": base_voice,
            "rate": "+12%",
            "pitch": "+2Hz",
            "style_prompt": "samimi, sokak röportajı enerjisinde, merak uyandıran",
        },
        "calm_sage": {
            "voice": base_voice,
            "rate": "-6%",
            "pitch": "-3Hz",
            "style_prompt": "dingin, bilge, güven veren ve derin",
        },
        "energetic_analyst": {
            "voice": base_voice,
            "rate": "+8%",
            "pitch": "+0Hz",
            "style_prompt": "net, analitik, vurucu ve tempolu",
        },
        "dramatic_storyteller": {
            "voice": base_voice,
            "rate": "+2%",
            "pitch": "-2Hz",
            "style_prompt": "sinematik, gerilim dozunu artıran hikaye anlatıcısı",
        },
    }
    return dict(personas.get(persona, personas["energetic_analyst"]))


# Problem #38: A/B Hook Dual-Variant Builder
def build_ab_hook_render_variants(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Produces Variant A and Variant B hook plans sharing the body scenes for A/B CTR testing."""
    scenes = list(plan.get("scenes") or [])
    hook_a = str(plan.get("hook") or (scenes[0].get("text") if scenes else "Bunu kimse beklemiyordu!"))
    alt_hooks = list(plan.get("ab_hooks") or [])
    hook_b = str(alt_hooks[0] if alt_hooks else f"Peki gerçekte ne oldu? {hook_a}")

    variant_a = dict(plan)
    variant_a["variant_id"] = "A"
    variant_a["active_hook"] = hook_a

    variant_b = dict(plan)
    variant_b["variant_id"] = "B"
    variant_b["active_hook"] = hook_b
    if scenes:
        b_scenes = [dict(s) for s in scenes]
        b_scenes[0]["text"] = hook_b
        variant_b["scenes"] = b_scenes

    return [variant_a, variant_b]


# Problem #39: ML-Weighted CTR Title Scorer
def score_title_ctr_ml_heuristic(title: str) -> dict[str, Any]:
    """Scores a YouTube Shorts title on curiosity gap, numbers, emotional punch, and optimal length."""
    cleaned = (title or "").strip()
    words = cleaned.split()
    char_len = len(cleaned)

    length_score = 30.0 if 28 <= char_len <= 62 else max(10.0, 30.0 - abs(char_len - 45) * 0.6)
    has_question_or_excl = 20.0 if ("?" in cleaned or "!" in cleaned) else 8.0
    has_number = 20.0 if re.search(r"\b\d+\b", cleaned) else 10.0

    power_words = {"neden", "gizli", "asla", "dikkat", "şok", "gerçek", "sır", "kritik", "son", "yeni", "nasıl"}
    matched_power = sum(1 for w in words if w.lower().strip(".,!?") in power_words)
    power_score = min(30.0, 12.0 + matched_power * 9.0)

    total = round(min(100.0, length_score + has_question_or_excl + has_number + power_score), 1)
    return {
        "title": cleaned,
        "ctr_score": total,
        "char_length": char_len,
        "matched_power_words": matched_power,
    }


# Problem #40: Series Continuity Fallback Injector
def inject_series_continuity_into_fallback(
    scenes: list[dict[str, Any]],
    previous_episode_title: str | None = None,
    part_number: int = 1,
) -> list[dict[str, Any]]:
    """Ensures even procedural/offline fallback scripts reference the previous episode when part_number > 1."""
    if not scenes:
        return []
    updated = [dict(s) for s in scenes]
    if part_number > 1 and previous_episode_title:
        prefix = f"Serinin {part_number - 1}. bölümünde {previous_episode_title} detayını konuşmuştuk."
        first_text = str(updated[0].get("text", "")).strip()
        if prefix not in first_text:
            updated[0]["text"] = f"{prefix} {first_text}".strip()
            updated[0]["series_linked"] = True
    return updated
