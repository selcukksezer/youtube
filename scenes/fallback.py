"""
Procedural and rule-based fallback scene generator when AI quotas or APIs are unavailable.
Supports dynamic context-aware Reddit story rewriting, breaking news, stoicism, dark psychology,
and pure English stock query synthesis tailored to all 37 niches.
Niche-specific template generators live in scenes/fallback_packs.py.
"""

import re
import config

from scenes.fallback_packs import (
    _generate_reddit_confession_scenes,
    _generate_news_flash_scenes,
    _stoic_variant_index,
    _build_stoic_narrations,
    _generate_stoic_scenes,
    _generate_religious_quotes_scenes,
    _generate_dark_psychology_scenes,
    _generate_astrology_horoscope_scenes,
    _crypto_variant_index,
    _generate_crypto_market_scenes,
    _generate_five_fact_scenes,
)

__all__ = [
    "EN_TOPIC_MAP",
    "TR_EN_TOPIC_MAP",
    "sanitize_topic_title",
    "_generate_procedural_fallback_scenes",
]


EN_TOPIC_MAP = {
    "bitcoin": "bitcoin crypto candlestick chart",
    "crypto": "cryptocurrency trading terminal",
    "forex": "forex trading desk monitors",
    "trading": "live trading desk screens",
    "livetrading": "live trading stream desk",
    "live trading": "live trading broadcast desk",
    "gold": "gold bullion trading chart",
    "ethereum": "ethereum crypto chart screen",
    "banknifty": "india bank nifty index chart",
    "btc": "bitcoin price chart screen",
    "borsa": "stock exchange trading floor",
    "altcoin": "altcoin crypto market screen",
}

TR_EN_TOPIC_MAP = {
    "düğün": "wedding bride altar", "evlilik": "wedding marriage", "eş": "couple spouse betrayal",
    "borç": "secret debt money", "para": "cash money bank", "kredi": "bank loan debt documents",
    "kumar": "gambling casino debt", "miras": "inheritance estate conflict", "ev": "house luxury property",
    "kardeş": "siblings family conflict", "aile": "family dispute arguing", "hasta": "hospital medical patient",
    "restoran": "restaurant dinner table", "hesap": "bill invoice money cash", "arkadaş": "fake friends dinner",
    "patron": "office boss executive", "şirket": "corporate office workplace", "iş": "typing laptop computer",
    "mülakat": "job interview candidate", "ekran": "computer screen monitor", "whatsapp": "whatsapp chat messaging phone",
    "dedikodu": "office gossip whispering", "yayın": "live video stream broadcast",
    "yapay zeka": "artificial intelligence futuristic", "bot": "coding software screen",
    "aldat": "cheating partner betrayal", "sevgili": "couple argument breakup", "nişanlı": "fiancé deception secret",
    "dolandırıcı": "scammer crime investigation", "yalan": "lies secret betrayal",
    "felsefe": "stoic statue marble philosophy", "roma": "ancient rome ruins colosseum",
    "psikoloji": "human psychology mind brain", "bilim": "science laboratory discovery",
    "uzay": "space galaxy universe stars", "motivasyon": "workout fitness athlete",
    "haber": "breaking news broadcast studio", "kripto": "bitcoin crypto trading chart",
    "altın": "gold bullion trading chart", "borsa": "stock market trading floor",
    "tarih": "ancient historical battlefield", "ürün": "viral smart gadget lifestyle"
}


def sanitize_topic_title(title: str) -> str:
    """Strip emojis, hashtags and live-stream noise; keep semantic topic text."""
    t = (title or "").strip()
    t = re.sub(r"[\U00010000-\U0010ffff]", "", t)
    t = re.sub(r"[\u2600-\u27bf\ufe00-\ufe0f]", "", t)
    t = re.sub(r"#[\w]+", " ", t)
    t = re.sub(r"[^\w\s\-&]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t).strip()
    return t or "Canlı Piyasa Özeti"


def _detect_niche_and_terms(title: str, body: str = ""):
    clean_title = sanitize_topic_title(title)
    words = [w for w in clean_title.split() if len(w) > 2]
    combined_text = f"{title} {body}".lower()

    matched_en = []
    for en_k, en_v in EN_TOPIC_MAP.items():
        if en_k in combined_text:
            matched_en.append(en_v)
    for tr_k, en_v in TR_EN_TOPIC_MAP.items():
        if tr_k in combined_text and en_v not in matched_en:
            matched_en.append(en_v)

    if matched_en:
        main_kw = matched_en[0]
    else:
        main_kw = "dramatic cinematic mystery"

    return clean_title, main_kw, words, matched_en


_CRYPTO_TOPIC_HINTS = (
    "bitcoin", "crypto", "kripto", "forex", "trading", "livetrading", "live trading",
    "gold", "altın", "borsa", "banknifty", "ethereum", "eth ", "btc", "altcoin",
)


def _clean_fallback_narration(text: str, *, is_tr: bool = True) -> str:
    """Remove non-spoken decoration without adding claims to fallback narration."""
    raw = (text or "").strip()
    raw = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf\ufe00-\ufe0f]", "", raw)
    raw = re.sub(
        r"\s*(?:yorumlarda paylaşın|yorumlara yazın|takipte kalın|abone olun|like ve subscribe|subscribe)\s*[.!?]*",
        " ", raw, flags=re.I,
    )
    raw = re.sub(r"\s+(?:ve|and)\s*[.!?]*$", "", raw, flags=re.I)
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = re.sub(r"\s+B\u0075nu hafta boyunca akl\u0131nda tut\.?", ".", raw, flags=re.I)
    raw = re.sub(r"\s+Bunu\s+hafta\s+boyunca\s+aklında\s+tut\.?", ".", raw, flags=re.I)
    raw = re.sub(r"\s+Keep this in mind throughout the week\.?", ".", raw, flags=re.I)
    legacy_padding = (
        (
            "Bu iddianın kaynağını kontrol et ve bağlamını oku",
            "Bu, sessiz kalmanın gücünü hatırlatır",
            "Bu ayrıntı, anlatının geri kalanını anlamak için gerekli",
        )
        if is_tr else (
            "Check the source of this claim and read its full context",
            "That is the power of deliberate silence",
            "That detail is necessary to understand the rest of the story",
        )
    )
    for sentence in legacy_padding:
        raw = re.sub(
            rf"(?:^|\s+){re.escape(sentence)}\s*[.!?]*",
            " ",
            raw,
            flags=re.I,
        )
    raw = re.sub(r"\s+", " ", raw).strip()
    standalone_quotes = re.sub(r"\b\w+'[a-zA-ZçğıöşüÇĞİÖŞÜ]+\b", "", raw)
    if standalone_quotes.count("'") % 2 == 1:
        raw += "'"
    if raw and raw[-1] not in ".!?":
        raw += "."
    return raw


def _finalize_fallback_plan(plan: dict, *, is_tr: bool = True) -> dict:
    scenes = plan.get("scenes") or []
    for sc in scenes:
        sc["narration"] = _clean_fallback_narration(
            sc.get("narration") or "",
            is_tr=is_tr,
        )
        standalone_q = re.sub(r"\b\w+'[a-zA-ZçğıöşüÇĞİÖŞÜ]+\b", "", sc["narration"])
        if standalone_q.count("'") % 2 == 1:
            sc["narration"] += "'"
        sc["narration"] = re.sub(r"([.!?])['\"]+\.+$", r"\1'", sc["narration"])
        sc["narration"] = sc["narration"].replace(".' .", ".'").replace(".'.", ".'")
        if sc["narration"] and sc["narration"][-1] not in ".!?":
            sc["narration"] += "."

    if scenes:
        from scenes.narration_validate import auto_repair_scenes, scene_narration_issues

        scenes, narration_fixes = auto_repair_scenes(scenes)
        if narration_fixes:
            print(f"  [Fallback] Kısa anlatımlar onarıldı: {narration_fixes}")
        remaining_issues = [
            f"scene_{i}:{','.join(scene_narration_issues(scene.get('narration') or ''))}"
            for i, scene in enumerate(scenes)
            if scene_narration_issues(scene.get("narration") or "")
        ]
        if remaining_issues:
            raise ValueError(
                "Procedural fallback narration remains invalid after repair: "
                + "; ".join(remaining_issues)
            )

    for sc in scenes:
        vi = sc.get("visual_intent") if isinstance(sc.get("visual_intent"), dict) else {}
        description = str(sc.get("scene_description") or "").strip()
        sc["visual_intent"] = {
            **vi,
            "subject": vi.get("subject") or description[:80],
            "action": vi.get("action") or "move or change visibly",
            "setting": vi.get("setting") or "real world location",
            "lighting": vi.get("lighting") or sc.get("mood") or "natural light",
            "visual_priority": vi.get("visual_priority") or "subject",
            "must_exclude": list(vi.get("must_exclude") or []),
        }
        sc.setdefault("claim_ids", [])
        sc.setdefault("evidence_required", False)
    n = len(scenes)
    if n:
        try:
            from director.schema import QualityThresholds, natural_target_duration
            from viral_retention_engine import ViralRetentionEngine
            qt = QualityThresholds()
            min_d, max_d = qt.min_duration, qt.max_duration
            wc = sum(len((sc.get("narration") or "").split()) for sc in scenes)
            target = natural_target_duration(wc, min_d, max_d)
            cadence = ViralRetentionEngine.calculate_cadence_acceleration(
                total_duration=target, scene_count=n
            )
        except Exception:
            min_d, max_d = 38.0, 60.0
            wc = sum(len((sc.get("narration") or "").split()) for sc in scenes)
            target = max(38.0, min(60.0, round(wc / 2.45, 2) if wc else 38.0))
            cadence = [round(target / n, 2)] * n
            cadence[-1] = round(target - sum(cadence[:-1]), 2)
        moods = [
            "urgent", "dramatic", "energetic", "tense", "calm",
            "epic", "mysterious", "hopeful", "solemn", "warm",
            "reverent", "luminous",
        ]
        beat_n = n
        for i, sc in enumerate(scenes):
            sc["duration"] = float(cadence[i]) if i < len(cadence) else round(target / n, 2)
            if not (sc.get("mood") or "").strip() or (sc.get("mood") or "").strip().lower() == (
                scenes[0].get("mood") or ""
            ).strip().lower() and i > 0:
                sc["mood"] = moods[i % len(moods)]
            pct = (i + 0.5) / beat_n
            if i == 0 or pct <= 0.07:
                sc["beat_type"] = "hook"
            elif pct <= 0.45:
                sc["beat_type"] = "conflict"
            elif pct <= 0.75:
                sc["beat_type"] = "climax"
            else:
                sc["beat_type"] = "resolution"
        ms = [int(round(float(sc.get("duration") or 0) * 100)) for sc in scenes]
        target_ms = int(round(min(max_d, max(min_d, target)) * 100))
        if ms:
            ms[-1] += target_ms - sum(ms)
            for i, sc in enumerate(scenes[:-1]):
                sc["duration"] = ms[i] / 100.0
            head = sum(float(sc["duration"]) for sc in scenes[:-1])
            scenes[-1]["duration"] = float(target_ms) / 100.0 - head
        unique_moods = {(sc.get("mood") or "").strip().lower() for sc in scenes}
        if len(unique_moods) < min(4, n):
            for i, sc in enumerate(scenes):
                sc["mood"] = moods[i % len(moods)]
    plan["scenes"] = scenes
    plan["full_narration"] = " ".join(
        (s.get("narration") or "").strip() for s in scenes if (s.get("narration") or "").strip()
    )
    return plan


def _topic_is_crypto_market(title: str, body: str = "", niche_type: str = None) -> bool:
    if niche_type and niche_type != "8_crypto_market":
        return False
    if niche_type == "8_crypto_market":
        return True
    combined = f"{title} {body}".lower()
    return any(k in combined for k in _CRYPTO_TOPIC_HINTS)


_SUBJECT_DROP = frozenset({
    "ama", "ve", "ile", "için", "icin", "bir", "bu", "şu", "su", "o", "da", "de",
    "mi", "mı", "mu", "mü", "çok", "cok", "en", "gibi", "diye", "olan", "olarak",
    "hakkında", "hakkinda", "konusunda", "size", "sen", "siz", "sizin",
    "öğretilmeyen", "ogretilmeyen", "bilmeniz", "gereken", "şok", "sok",
    "gerçek", "gercek", "bilgi", "kural", "sır", "sir", "tane", "büyük", "buyuk",
    "ilginç", "ilginc", "önemli", "onemli", "şaşırtıcı", "sasirtici", "inanılmaz",
    "inanilmaz", "facts", "fact", "shocking", "mind", "blowing", "the", "and",
    "you", "your", "about", "that", "this", "need", "know",
})


def _viewer_subject(clean_title: str) -> str:
    """Drop format words so narration talks about the subject, not the clickbait shell."""
    words = []
    for raw in (clean_title or "").split():
        token = raw.strip(".,!?'\"")
        if not token or token.isdigit():
            continue
        if token.casefold() in _SUBJECT_DROP:
            continue
        words.append(token)
    subject = " ".join(words[:6]).strip()
    return subject or (clean_title or "bu konu").strip()


def _subject_visuals(pack: dict, subject: str) -> list:
    base_bank = list(pack.get("subjects") or []) or [
        "library reading desk natural light",
        "open book pages close up",
        "researcher notes on a wooden desk",
        "quiet archive shelves",
        "focused person taking notes",
        "historical documents under desk lamp",
        "vintage journal on dark wood table",
        "magnifying glass analyzing text",
        "minimalist study room ambient atmosphere",
        "atmospheric room with dust motes in sunlight",
        "thoughtful person looking out window",
        "macro view of handwritten fountain pen manuscript",
    ]
    angles = [
        "wide establishing view",
        "extreme close-up macro",
        "over-the-shoulder angle",
        "slow tracking motion",
        "low angle perspective",
        "high overhead top-down view",
        "cinematic depth-of-field focus pull",
        "dramatic side silhouette lighting",
        "eye-level inspection shot",
        "dynamic slow pan transition",
        "warm atmospheric contrast angle",
        "intense central composition framing",
    ]
    from visuals.query_builder import _TR_EN
    low_subj = (subject or "").lower()
    en_hits = []
    for tr_k, en_v in _TR_EN.items():
        if tr_k in low_subj and en_v not in en_hits:
            en_hits.append(en_v)
    en_concept = en_hits[0] if en_hits else ""

    visuals = []
    for i in range(12):
        base_shot = base_bank[i % len(base_bank)]
        angle = angles[i % len(angles)]
        shot_desc = f"{base_shot} {angle}"
        queries = [
            f"{base_shot} {angle}",
            base_shot,
            f"{en_concept} {angle}".strip() if en_concept else f"{base_shot} closeup",
        ]
        visuals.append((shot_desc, queries))
    return visuals


from scenes.fallback_narrations import _topic_bound_narrations


def _generate_pack_fallback_scenes(pack: dict, clean_title: str, is_tr: bool):
    """Topic-aware fallback. Speak about the subject. Never describe the generator."""
    topic = (clean_title or "").strip() or pack.get("name") or "Konu"
    subject = _viewer_subject(topic)
    family = pack.get("family", "")
    nid = pack.get("id", "")
    narrations = _topic_bound_narrations(subject, is_tr, family=family, nid=nid)
    visuals = _subject_visuals(pack, subject)
    moods = ["urgent", "curious", "focused", "analytical", "mysterious", "tense", "calm", "bright", "reflective", "energetic"]
    scenes = []
    for i, narr in enumerate(narrations):
        desc, queries = visuals[i]
        scenes.append({
            "scene_number": i + 1,
            "narration": narr,
            "scene_description": desc,
            "search_queries": queries,
            "duration": 4.8,
            "mood": moods[i % len(moods)],
            "beat_type": "hook" if i == 0 else "resolution" if i == len(narrations) - 1 else "conflict",
        })
    return {
        "title": topic,
        "visual_theme": pack.get("family") or "cinematic",
        "full_narration": " ".join(narrations),
        "scenes": scenes,
        "niche_id": pack.get("id"),
        "procedural_fallback": True,
        "scenario_pack_family": pack.get("family"),
    }


def _generate_procedural_fallback_scenes(
    title: str,
    niche_type: str = None,
    raw_body: str = "",
    language: str = None,
    variation_seed: int = 0,
    lang: str = None,
) -> dict:
    """
    Failsafe when AI is unavailable. Dispatch by this topic's niche pack —
    never dump a crypto-shaped stub onto an unrelated niche.
    """
    from niche_templates import NICHES, get_scenario_pack

    clean_title, _, _, _ = _detect_niche_and_terms(title, raw_body)
    lang = language or lang or getattr(config, "LANGUAGE", "tr")
    is_tr = (lang == "tr")
    combined = f"{title} {raw_body}".lower()

    resolved = niche_type if niche_type in NICHES else None
    if not resolved:
        if any(k in combined for k in ["itiraf", "reddit", "whatsapp", "mülakat", "iş görüşmesi", "patron", "aldat", "gizli"]):
            resolved = "2_reddit_confessions" if "whatsapp" not in combined else "20_whatsapp_chat_story"
        elif any(k in title.lower() for k in ["son dakika", "flaş", "haber", "açıklama", "deprem", "karar"]):
            resolved = "1_news_flash"
        elif any(k in combined for k in [
            "peygamber", "dua", "ayet", "hadis", "kuran", "kur'an",
            "allah", "namaz", "islam", "islâm", "sahabe", "sünnet", "ibadet", "dini",
        ]):
            resolved = "10_religious_quotes"
        elif any(k in title.lower() for k in ["stoa", "marcus aurelius", "seneca", "felsefe"]):
            resolved = "6_stoic_philosophy"
        elif any(k in title.lower() for k in ["karanlık psikoloji", "manipülasyon", "beden dili"]):
            resolved = "7_dark_psychology"
        elif any(k in combined for k in ["burç", "burcu", "astroloji", "horoskop", "zodyak", "zodiac", "horoscope"]):
            resolved = "18_astrology_horoscope"
        elif _topic_is_crypto_market(title, raw_body, niche_type=None):
            resolved = "8_crypto_market"
        else:
            resolved = "9_five_facts"

    pack = get_scenario_pack(resolved, language=lang)
    family = pack["family"]
    nid = pack["id"]

    if nid == "8_crypto_market" or family == "crypto":
        return _finalize_fallback_plan(
            _generate_crypto_market_scenes(clean_title, is_tr, variation_seed=variation_seed),
            is_tr=is_tr,
        )
    if nid in ("2_reddit_confessions",) or family == "reddit":
        return _finalize_fallback_plan(_generate_reddit_confession_scenes(clean_title, combined, is_tr), is_tr=is_tr)
    if nid in ("20_whatsapp_chat_story", "3_split_gameplay") or family == "whatsapp":
        return _finalize_fallback_plan(_generate_reddit_confession_scenes(clean_title, combined, is_tr), is_tr=is_tr)
    if nid in ("1_news_flash",) or family == "news":
        return _finalize_fallback_plan(_generate_news_flash_scenes(clean_title, is_tr), is_tr=is_tr)
    if nid == "10_religious_quotes" or family == "religious":
        return _finalize_fallback_plan(
            _generate_religious_quotes_scenes(clean_title, is_tr, variation_seed=variation_seed),
            is_tr=is_tr,
        )
    if nid in ("6_stoic_philosophy",) or family == "stoic":
        return _finalize_fallback_plan(_generate_stoic_scenes(clean_title, is_tr, variation_seed=variation_seed), is_tr=is_tr)
    if nid == "7_dark_psychology" or family == "dark":
        return _finalize_fallback_plan(_generate_dark_psychology_scenes(clean_title, is_tr, variation_seed=variation_seed), is_tr=is_tr)
    if nid == "18_astrology_horoscope" or family == "astrology":
        return _finalize_fallback_plan(
            _generate_astrology_horoscope_scenes(clean_title, is_tr, variation_seed=variation_seed),
            is_tr=is_tr,
        )
    facts_shell = bool(re.search(r"\b(gerçek|gercek|facts|şok|sok)\b", f"{title} {clean_title}", re.I))
    if nid == "9_five_facts" and (niche_type == "9_five_facts" or facts_shell):
        return _finalize_fallback_plan(_generate_five_fact_scenes(clean_title, is_tr, variation_seed=variation_seed), is_tr=is_tr)
    return _finalize_fallback_plan(_generate_pack_fallback_scenes(pack, clean_title, is_tr), is_tr=is_tr)
