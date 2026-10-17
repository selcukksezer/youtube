"""
Niche Templates & Viral Hook Prompt Engine
Defines 37 custom niche templates, hooks, seamless loop rules, discussion triggers, and Tier-1 translation prompts.
Covers items: 1-35, 36, 37, 73, 81, 82, 84, 90, 93, 96 from r10_shorts_fikirleri_ve_bot_ozellikleri.md

v2.0 — Advanced schema with RPM bands, viral scores, retention data, A/B hooks, competition analysis.
Static catalog dictionaries live in services/niche_catalog_data.py.
"""
from typing import Dict, Any, List

from services.niche_catalog_data import (
    NICHES,
    SCENE_FORMAT_TEMPLATES,
    NICHE_OUTRO_CTA,
    NICHE_HOOKS_EN,
    NICHE_INSTRUCTIONS_EN,
)


# P1-01: competitor-format scene structures keyed by niche family (all 37)
NICHE_FAMILY_MAP: Dict[str, str] = {
    "1_news_flash": "news",
    "2_reddit_confessions": "reddit",
    "3_split_gameplay": "whatsapp",
    "4_would_you_rather": "quiz",
    "5_guess_flag_country": "quiz",
    "6_stoic_philosophy": "stoic",
    "7_dark_psychology": "dark",
    "8_crypto_market": "crypto",
    "9_five_facts": "quiz",
    "10_religious_quotes": "religious",
    "11_language_learning": "quiz",
    "12_amazon_affiliate": "product",
    "13_mystery_paranormal": "mystery",
    "14_movie_summaries": "entertainment",
    "15_football_transfers": "news",
    "16_wealth_entrepreneurship": "stoic",
    "17_before_after_evolution": "entertainment",
    "18_astrology_horoscope": "astrology",
    "19_historical_battles": "stoic",
    "20_whatsapp_chat_story": "whatsapp",
    "21_ai_tools_hacks": "tech",
    "22_emoji_guess_game": "quiz",
    "23_fitness_nutrition_hacks": "fitness",
    "24_sigma_character_study": "stoic",
    "25_celebrity_net_worth": "entertainment",
    "26_dangerous_places": "mystery",
    "27_common_myths_busted": "quiz",
    "28_dream_meanings": "astrology",
    "29_optical_illusions_iq": "quiz",
    "30_poetry_quotes": "stoic",
    "31_supercars_automotive": "automotive",
    "32_legal_consumer_hacks": "legal",
    "33_parenting_child_hacks": "kids",
    "34_gaming_easter_eggs": "entertainment",
    "35_animal_kingdom_stories": "entertainment",
    "36_kids_animation": "kids",
    "37_interactive_quiz": "quiz",
}

# Item 273 shock/horror queries only for these families
SHOCK_QUERY_FAMILIES = frozenset({"mystery", "dark"})

# Visual/copy bait — opt-in by family. Calm niches inherit False.
CLICKBAIT_FAMILIES = frozenset({"quiz", "mystery", "dark"})
POLARIZE_FAMILIES = frozenset({"quiz", "mystery", "dark", "news", "entertainment", "fitness", "automotive"})
DETECTIVE_BAIT_FAMILIES = frozenset({"quiz", "mystery", "dark"})
SHOPPING_FAMILIES = frozenset({"product"})
STICKY_BANNER_FAMILIES = frozenset({"quiz", "mystery", "dark", "news", "fitness", "automotive"})
CALM_FAMILIES = frozenset({"stoic", "religious", "kids", "legal"})

VISUAL_BAIT_MANIFEST_KEYS = (
    "item_211_blur_bait",
    "item_212_countdown",
    "item_246_curiosity",
    "item_232_sticky_banner",
    "item_238_sticker",
    "item_260_white_flash",
    "item_201_pattern_interrupt",
)


def overlay_policy_for_niche(niche_id: str) -> Dict[str, Any]:
    """Family overlay/copy policy. Clickbait and split are opt-in."""
    family = get_niche_family(niche_id)
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    kids = family == "kids"
    clickbait = family in CLICKBAIT_FAMILIES and not kids
    sticky = family in STICKY_BANNER_FAMILIES and not kids
    allow_split = bool(niche.get("has_split_screen", False)) and not kids
    return {
        "family": family,
        "clickbait_overlays": clickbait,
        "allow_split": allow_split,
        "allow_polarize": family in POLARIZE_FAMILIES and not kids,
        "allow_detective_bait": family in DETECTIVE_BAIT_FAMILIES and not kids,
        "allow_mistake_bait": family in DETECTIVE_BAIT_FAMILIES and not kids,
        "allow_shopping": family in SHOPPING_FAMILIES and not kids,
        "allow_sticky_banner": sticky,
        "calm_floor": family in CALM_FAMILIES,
        "effect_manifest_overrides": {
            "item_211_blur_bait": clickbait,
            "item_212_countdown": clickbait,
            "item_246_curiosity": clickbait,
            "item_232_sticky_banner": sticky,
            "item_238_sticker": clickbait,
            "item_260_white_flash": clickbait,
            "item_201_pattern_interrupt": clickbait,
        },
    }


def get_niche_outro_cta(niche_key: str, language: str = "tr") -> str:
    """Returns niche-specific AI outro/CTA instruction for the last scene.
    Used by get_niche_prompt to tell the AI how to write the closing narration.
    Falls back to a generic instruction if niche is unknown.
    """
    lang = "tr" if language == "tr" else "en"
    entry = NICHE_OUTRO_CTA.get(niche_key)
    if entry:
        return entry.get(lang, entry.get("tr", ""))
    family = NICHE_FAMILY_MAP.get(niche_key, "general")
    family_defaults: Dict[str, Dict[str, str]] = {
        "reddit": {
            "tr": "Son sahne: izleyiciye 'Siz olsaydınız ne yapardınız?' sorusunu sorarak organik yorum bağlantısı kur.",
            "en": "Final scene: ask 'What would you have done?' to create organic comment engagement.",
        },
        "news": {
            "tr": "Son sahne: bu haberin en önemli boyutunu soran bir tartışma sorusuyla bitir.",
            "en": "Final scene: close with a debate question about the most important angle of this story.",
        },
        "stoic": {
            "tr": "Son sahne: stoacı ilke üzerine derin bir soru sor; 'Bunu bugün hayatına nasıl uygulayacaksın?'",
            "en": "Final scene: close with a deep stoic question — 'How will you apply this today?'",
        },
        "crypto": {
            "tr": "Son sahne: piyasa pozisyonu veya hedef fiyat tartışması başlat.",
            "en": "Final scene: spark a market position or price target debate.",
        },
        "astrology": {
            "tr": "Son sahne: izleyiciyi kendi burcunu yorumlara yazmaya davet et.",
            "en": "Final scene: invite viewers to share their zodiac sign in the comments.",
        },
        "religious": {
            "tr": "Son sahne: 'Amin' veya manevi bir yorum davet et; mekanik takip çağrısı YASAK.",
            "en": "Final scene: invite a heartfelt 'Amen' or spiritual reflection; no mechanical subscribe call.",
        },
    }
    fb = family_defaults.get(family, {})
    if fb:
        return fb.get(lang, fb.get("tr", ""))
    if lang == "tr":
        return "Son sahne: izleyiciye konu hakkında kişisel deneyimini veya görüşünü soran organik, nişe uygun bir yorum sorusuyla bitir. Mekanik 'abone ol/beğen' kalıpları YASAK."
    return "Final scene: close with an organic, niche-appropriate comment question asking viewers for their personal experience or opinion. No mechanical 'subscribe/like' calls."


def exact_style16(niche_key: str) -> Dict[str, Any]:
    """Map a live or plan niche id onto one of the 16 style profiles.

    Unknown ids return an empty dict. They must not become news by guess.
    """
    key = str(niche_key or "").strip().lower()
    if not key:
        return {}
    try:
        from services.niche_profiles import NICHE_16_PROFILES, NICHE_CANONICAL_MAP
    except Exception:
        return {}
    canon = NICHE_CANONICAL_MAP.get(key)
    if canon in NICHE_16_PROFILES:
        return dict(NICHE_16_PROFILES[canon])
    if key in NICHE_16_PROFILES:
        return dict(NICHE_16_PROFILES[key])
    return {}


def get_niche_family(niche_key: str) -> str:
    """Returns panel/format family for a niche (news, reddit, whatsapp, stoic, crypto, ...)."""
    return NICHE_FAMILY_MAP.get(niche_key, "general")


def get_niche_scene_structure(niche_key: str, language: str = "tr") -> str:
    """P1-01: competitor-format scene structure block for generator prompt."""
    family = get_niche_family(niche_key)
    lang = "tr" if language == "tr" else "en"
    templates = SCENE_FORMAT_TEMPLATES.get(family)
    if not templates:
        return ""
    return templates.get(lang, templates.get("tr", ""))


def get_scenario_pack(niche_key: str, language: str = "tr") -> Dict[str, Any]:
    """
    Per-niche scenario pack: tone, forbidden visuals, shock policy, fallback family.
    Shared envelope (JSON / 8-16 / 38-60 / min 10 words) is NOT stored here.
    """
    style = exact_style16(niche_key)
    if niche_key in NICHES:
        key = niche_key
        niche = NICHES[key]
    elif style:
        key = style["niche_id"]
        niche = {
            "id": key,
            "name": style["name_tr"],
            "name_en": style.get("name_en", style["name_tr"]),
            "category": style.get("category", ""),
            "tone": style["tone"],
            "hook_style": style.get("hook_style", ""),
            "system_instruction": (
                f"Görsel motif: {style.get('visual_motif', '')}. "
                f"Çekim konuları: {', '.join(style.get('visual_subjects') or [])}. "
                f"Ton: {style['tone']}. "
                "Başka nişin görselini bu motife taşıma."
            ),
            "default_music": style.get("bgm_mood") or "calm",
        }
    else:
        key = "1_news_flash"
        niche = NICHES[key]
    family = get_niche_family(key)
    try:
        from director.visual_intent import get_motif_bank
        bank = get_motif_bank(key)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("motif bank unavailable for %s: %s", key, exc)
        bank = {}
    exclude = list(bank.get("must_exclude") or [])
    include = list(bank.get("must_include") or [])
    subjects = list(bank.get("subjects") or [])
    outro_cta_tr = get_niche_outro_cta(key, "tr")
    outro_cta_en = get_niche_outro_cta(key, "en")
    return {
        "id": key,
        "name": niche["name"],
        "name_en": niche.get("name_en", niche["name"]),
        "category": niche["category"],
        "tone": niche["tone"],
        "hook_style": niche["hook_style"],
        "hook_style_en": niche.get("hook_style_en") or NICHE_HOOKS_EN.get(key, ""),
        "system_instruction": niche["system_instruction"],
        "system_instruction_en": niche.get("system_instruction_en") or NICHE_INSTRUCTIONS_EN.get(key, ""),
        "default_music": niche.get("default_music", "dramatic"),
        "family": family,
        "must_exclude": exclude,
        "must_include": include,
        "subjects": subjects,
        "allow_shock_queries": family in SHOCK_QUERY_FAMILIES,
        "min_words": 10,
        "min_scenes": 8,
        "max_scenes": 16,
        "min_duration": 38.0,
        "max_duration": 60.0,
        "target_duration": 0.0,
        "scene_structure": get_niche_scene_structure(key, language),
        "outro_cta": outro_cta_tr,
        "outro_cta_en": outro_cta_en,
    }


def get_niche_prompt(niche_key: str, topic: str, language: str = "tr", enable_outro: bool = True) -> str:
    """
    Compose envelope (schema/duration) + this niche's pack (tone, forbidden visuals, structure).
    One shared PROMPT_TR is never enough — each niche gets its own content rules.
    """
    from scenes.prompts import SHARED_ENVELOPE_TR, SHARED_ENVELOPE_EN

    pack = get_scenario_pack(niche_key, language=language)
    is_tr = (language == "tr")
    envelope = SHARED_ENVELOPE_TR if is_tr else SHARED_ENVELOPE_EN
    forbidden = ", ".join(pack["must_exclude"]) if pack["must_exclude"] else ("yok" if is_tr else "none")
    shock = (
        "Item 273 şok/horror query bu nişte SERBEST."
        if pack["allow_shock_queries"]
        else "Item 273 şok/horror query bu nişte YASAK — must_exclude ile çelişmesin."
    )
    shock_en = (
        "Item 273 shock/horror queries ALLOWED for this niche."
        if pack["allow_shock_queries"]
        else "Item 273 shock/horror queries FORBIDDEN for this niche."
    )
    structure = pack["scene_structure"]
    struct_block = f"\nRAKİP FORMAT SAHNE YAPISI:\n{structure}\n" if structure and is_tr else (
        f"\nCOMPETITOR FORMAT SCENE STRUCTURE:\n{structure}\n" if structure else ""
    )
    outro_cta_tr = pack.get("outro_cta") or get_niche_outro_cta(pack["id"], "tr")
    outro_cta_en = pack.get("outro_cta_en") or get_niche_outro_cta(pack["id"], "en")
    if enable_outro:
        outro_block_tr = (
            "4. NİŞE ÖZEL OUTRO / CTA (son sahne - ZORUNLU):\n"
            f"   {outro_cta_tr}\n"
            "   Son sahne aynı zamanda 1. sahneye döngüsel bağlantı (SEAMLESS LOOP) içermeli.\n"
            "   TARTIŞMA KURALI: İzleyiciyi yoruma teşvik eden açık uçlu soru veya merak ögesi bırak."
        )
        outro_block_en = (
            "4. NICHE-SPECIFIC OUTRO / CTA (last scene - MANDATORY):\n"
            f"   {outro_cta_en}\n"
            "   The last scene should also loop back seamlessly (SEAMLESS LOOP) to the feeling of Scene 1."
        )
    else:
        outro_block_tr = (
            "4. OUTRO KAPALI:\n"
            "   Son sahneye CTA, yorum sorusu, abone çağrısı veya döngü kapanışı yazma.\n"
            "   Son cümle konunun son olgusu olsun ve orada bitsin."
        )
        outro_block_en = (
            "4. OUTRO OFF:\n"
            "   Do not write a CTA, comment question, subscribe line, or loop close.\n"
            "   The last sentence is the last fact, then stop."
        )

    if is_tr:
        return f"""{envelope}

Sen profesyonel bir YouTube Shorts algoritma uzmanı ve viral senaristsin.
KONU: "{topic}"
NİŞ PAKETİ: "{pack['name']}" ({pack['category']}) id={pack['id']} family={pack['family']}
ANLATIM TONU: {pack['tone']}
YASAK GÖRSELLER (must_exclude): {forbidden}
{shock}

NİŞ ÖZEL TALİMATI:
{pack['system_instruction']}
{struct_block}
ANLAM KURALLARI (zorunlu):
- Konu yalnızca şu: "{topic}". Başka bir videonun başlığını, örnek kancayı veya hazır şablonu anlatım yapma.
- Her sahne yeni bir bilgi söyler. Başlığın tamamını sahnenin içine yapıştırma. Aynı 4 kelimeyi bir sahnede iki kez yazma.
- Konuda adı geçmeyen kişiye söz atfetme. "X'ın {topic} hakkında söylediği söz" kalıbı yasak.
- "İddia şu: [başlığın tamamı]" ve "İlk kontrol: [başlık] iddiasını ders kitabı ile karşılaştır" kalıpları yasak. İzleyiciye o konunun kendisini anlat.

3. İLK 3 SANİYE KANCASI (VIRAL HOOK - Sahne 1):
   Örnek yalnızca ritim içindir, metne kopyalama: "{pack['hook_style']}"

{outro_block_tr}

Başka nişin şablonunu (kripto grafiği, burç listesi, itiraf, haber bülteni) bu pakete kopyalama.
"""

    sys_inst_en = pack.get("system_instruction_en") or NICHE_INSTRUCTIONS_EN.get(pack["id"]) or "Deliver a gripping, high-retention narrative on this topic in fluent English."
    hook_style_en = pack.get("hook_style_en") or NICHE_HOOKS_EN.get(pack["id"]) or "The hidden truth about this topic changes everything..."

    return f"""{envelope}

You are a professional YouTube Shorts algorithm expert and viral scriptwriter.
TOPIC: "{topic}"
NICHE PACK: "{pack['name_en']}" ({pack['category']}) id={pack['id']} family={pack['family']}
TONE OF VOICE: {pack['tone']}
FORBIDDEN VISUALS (must_exclude): {forbidden}
{shock_en}

NICHE SPECIFIC INSTRUCTION:
{sys_inst_en}
{struct_block}
SENSE RULES (mandatory):
- The only topic is "{topic}". Do not paste an example hook or another video's title into the script.
- Each scene adds a new fact. Never paste the full title into a scene, and never repeat the same four words twice in one scene.
- Do not attribute a quote to a person the topic does not name.
- Forbidden patterns: "The claim is: [full title]" and "Check [full title] against a textbook". Tell the subject itself.
- LANGUAGE MANDATE: Every single narration line in every scene MUST be written 100% in natural, fluent ENGLISH. Absolutely NO Turkish words, mixed phrases, or Turkish templates allowed.

3. FIRST 3-SECOND VIRAL HOOK (Scene 1):
   Rhythm reference only, do not copy: "{hook_style_en}"

{outro_block_en}

Do not clone another niche's template (crypto charts, horoscope list, confession, news bulletin) into this pack.
"""


def list_all_niches() -> List[Dict[str, Any]]:
    """Returns full metadata of all niches including advanced analytics fields."""
    return [
        {
            "id": k,
            "name": v["name"],
            "name_en": v["name_en"],
            "category": v["category"],
            "tone": v["tone"],
            "has_split_screen": v.get("has_split_screen", False),
            "icon": v.get("icon", "fa-fire"),
            "color_palette": v.get("color_palette", "default"),
            "rpm_tier": v.get("rpm_tier", "$2-5"),
            "viral_score": v.get("viral_score", 75),
            "avg_retention_pct": v.get("avg_retention_pct", 70),
            "competition_level": v.get("competition_level", "medium"),
            "best_posting_time": v.get("best_posting_time", "12:00-15:00 TRT"),
            "cta_type": v.get("cta_type", "comment"),
            "tier1_compatible": v.get("tier1_compatible", False),
            "episodic_capable": v.get("episodic_capable", False),
            "loop_formula": v.get("loop_formula", "cause_and_effect"),
            "trending_keywords": v.get("trending_keywords", []),
            "ab_test_hook_variants": v.get("ab_test_hook_variants", [v.get("hook_style", "")]),
            "niche_family": get_niche_family(k),
        }
        for k, v in NICHES.items()
    ]


def get_niche_production_profile(niche_id: str) -> Dict[str, Any]:
    """Returns the settings that the renderer should apply for a selected niche."""
    from director.schema import STOIC_AUDIO_RULES, STOIC_EFFECT_MANIFEST_OVERRIDES

    style = exact_style16(niche_id)
    keep_sixteen = bool(style) and niche_id == style.get("niche_id") and niche_id not in NICHES
    canonical_id = niche_id
    try:
        from hybrid_niches import HYBRID_NICHES
    except ImportError:
        HYBRID_NICHES = {}

    if niche_id in HYBRID_NICHES:
        hn = HYBRID_NICHES[niche_id]
        niche = {
            "id": hn["id"],
            "name": hn["name"],
            "category": hn["category"],
            "tone": hn["tone"],
            "hook_style": hn["hook_style"],
            "default_music": hn.get("default_music", "mysterious"),
            "rpm_tier": hn.get("rpm_tier", "$3-7"),
            "viral_score": 90,
            "avg_retention_pct": 75,
            "competition_level": "medium",
            "tier1_compatible": True,
        }
    else:
        if not keep_sixteen and niche_id not in NICHES:
            try:
                from services.niche_topic_vault import NICHE_ALIASES
                canonical_id = NICHE_ALIASES.get(niche_id, niche_id)
            except ImportError:
                pass

        niche = None if keep_sixteen else NICHES.get(canonical_id)
        if niche is None and style:
            niche = {
                "id": style["niche_id"],
                "name": style["name_tr"],
                "category": style.get("category", ""),
                "tone": style["tone"],
                "hook_style": style.get("hook_style", ""),
                "default_music": style.get("bgm_mood") or "calm",
                "rpm_tier": "$2-5",
                "viral_score": 75,
                "avg_retention_pct": 70,
                "competition_level": "medium",
                "tier1_compatible": False,
            }
        elif niche is None:
            niche = NICHES["1_news_flash"]

    policy = overlay_policy_for_niche(niche.get("id", canonical_id) if niche.get("id") in NICHES else niche_id)
    music_terms = {
        "dramatic": "dramatic", "mysterious": "mysterious", "lofi": "lofi",
        "energetic": "energetic", "epic": "epic", "calm": "calm", "kids": "kids",
        "ambient": "ambient", "news": "dramatic",
    }

    sub_preset = "red_fire" if niche.get("default_music") == "dramatic" else "capcut_yellow"
    if style and style.get("subtitle_preset"):
        sub_preset = style["subtitle_preset"]

    profile: Dict[str, Any] = {
        "id": niche["id"],
        "requested_niche": niche_id,
        "name": niche["name"],
        "category": niche["category"],
        "tone": style["tone"] if style else niche["tone"],
        "hook_style": niche["hook_style"],
        "rpm_tier": niche.get("rpm_tier", "$2-5"),
        "viral_score": niche.get("viral_score", 75),
        "avg_retention_pct": niche.get("avg_retention_pct", 70),
        "competition_level": niche.get("competition_level", "medium"),
        "tier1_compatible": niche.get("tier1_compatible", False),
        "production_rules": {
            "split_screen": policy["allow_split"],
            "ken_burns": True,
            "subtitle_preset": sub_preset,
            "music_keyword": music_terms.get(
                (style.get("bgm_mood") if style else None) or niche.get("default_music"),
                "ambient",
            ),
            "use_dynamic_motion": True,
            "use_progress_bar": True,
            "voice_style": style["tone"] if style else niche["tone"],
            "clickbait_overlays": policy["clickbait_overlays"],
            "allow_polarize": policy["allow_polarize"],
            "allow_detective_bait": policy["allow_detective_bait"],
            "allow_mistake_bait": policy["allow_mistake_bait"],
            "allow_shopping": policy["allow_shopping"],
            "allow_sticky_banner": policy["allow_sticky_banner"],
        },
        "overlay_policy": policy,
        "target_bpm": style.get("target_bpm") if style else None,
        "visual_motif": style.get("visual_motif", "") if style else "",
        "visual_subjects": list(style.get("visual_subjects") or []) if style else [],
        "must_include": list(style.get("must_include") or []) if style else [],
        "must_exclude": list(style.get("must_exclude") or []) if style else [],
        "bgm_mood": style.get("bgm_mood", "") if style else "",
        "effect_manifest_overrides": dict(policy["effect_manifest_overrides"]),
    }
    family = policy.get("family") or ""
    if family in ("dark", "mystery"):
        profile["effect_manifest_overrides"].update({
            "item_108_pink_noise": True,
            "item_112_whoosh_ding": True,
            "item_141_breaths": True,
            "item_157_heartbeat": True,
        })
    elif niche_id != "6_stoic_philosophy":
        profile["audio_rules"] = {
            "sparse_transitions": True,
            "max_transition_sfx": 2,
            "whoosh_volume": 0.07,
            "enable_sub_impact": False,
            "enable_tape_stop": False,
        }
    if niche_id == "6_stoic_philosophy" or (style and style.get("niche_id") == "2_philosophy_stoic"):
        profile["effect_manifest_overrides"].update(STOIC_EFFECT_MANIFEST_OVERRIDES)
        profile["audio_rules"] = dict(STOIC_AUDIO_RULES)
    return profile


def get_niche_ab_variants(niche_id: str) -> Dict[str, Any]:
    """Returns A/B test hook variants for a specific niche."""
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    variants = niche.get("ab_test_hook_variants", [niche.get("hook_style", "")])
    return {
        "niche_id": niche_id,
        "niche_name": niche["name"],
        "variants": [
            {"variant": label, "hook": hook, "strategy": strategy}
            for label, hook, strategy in zip(
                ["A — Merak Kancası", "B — Şok Kancası", "C — Tartışma Kancası"],
                variants + [""] * max(0, 3 - len(variants)),
                ["Curiosity Gap — İzleyiciyi asmada bırakır",
                 "Shock Value — Ani şok ile dikkat çeker",
                 "Debate Trigger — Yorum sayısını patlatır"]
            ) if hook
        ]
    }


def get_niche_leaderboard() -> List[Dict[str, Any]]:
    """Returns all niches sorted by viral_score descending for leaderboard display."""
    niches = list_all_niches()
    return sorted(niches, key=lambda x: x.get("viral_score", 0), reverse=True)
