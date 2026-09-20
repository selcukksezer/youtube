"""
Semantic Visual Intent director (Items 89, 130, 208, 213-214).
Topic/niche motif graph — subject continuity, must_exclude hard filters.
"""
from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

from .schema import ScenePlan, VisualIntent


# Niche motif banks: preferred imagery + hard exclusions for cross-niche pollution
NICHE_MOTIFS: Dict[str, Dict[str, Any]] = {
    "6_stoic_philosophy": {
        "motif": "imperial_rome",
        "era": "ancient rome",
        "mood": "stoic calm contemplative",
        "subjects": [
            "bronze marcus aurelius statue",
            "ancient roman marble columns",
            "old parchment scroll torchlight",
            "roman forum at dusk",
            "stoic philosopher reading",
            "olive tree mediterranean wind",
            "stone amphitheater empty seats",
            "hand writing on parchment",
            "roman emperor bust close up",
            "calm ocean horizon sunrise",
            "candle flame dark room",
            "ancient stone pathway",
            "bronze eagle standard",
            "quiet library antique books",
        ],
        "must_include": ["marble", "rome", "scroll", "statue", "torch", "philosopher"],
        "must_exclude": [
            "skull", "ufo", "hooded", "horror", "zombie", "ghost", "alien",
            "paranormal", "cemetery", "blood", "monster", "demon", "witch",
        ],
    },
    "13_mystery_paranormal": {
        "motif": "dark_archive",
        "era": "modern mystery",
        "mood": "chilling suspenseful",
        "subjects": [
            "foggy forest night",
            "abandoned archive documents",
            "mysterious glowing orb",
            "dark corridor flickering light",
            "old radio static room",
        ],
        "must_include": ["fog", "shadow", "archive", "mystery"],
        "must_exclude": ["cartoon", "bright beach", "party"],
    },
    "7_dark_psychology": {
        "motif": "mind_shadow",
        "era": "contemporary",
        "mood": "tense psychological",
        "subjects": [
            "silhouette of person in doorway",
            "chess board strategy close up",
            "mirror reflection distorted",
            "city night neon rain",
        ],
        "must_include": ["silhouette", "mirror", "shadow"],
        "must_exclude": ["cartoon", "kids", "bright comedy"],
    },
    "1_news_flash": {
        "motif": "breaking_news",
        "era": "contemporary",
        "mood": "urgent cinematic",
        "subjects": [
            "city skyline night timelapse",
            "newsroom desk papers",
            "crowd street protest aerial",
            "breaking news studio lights",
        ],
        "must_include": ["city", "news", "crowd"],
        "must_exclude": ["horror skull", "ufo"],
    },
    "8_crypto_market": {
        "motif": "finance_pulse",
        "era": "contemporary",
        "mood": "tense energetic",
        "subjects": [
            "stock chart candlestick screen",
            "bitcoin gold coin close up",
            "trading desk multiple monitors",
            "city financial district aerial",
        ],
        "must_include": ["chart", "coin", "market"],
        "must_exclude": ["horror", "skull", "ghost"],
    },
}

_DEFAULT_MOTIF = {
    "motif": "cinematic_general",
    "era": "contemporary",
    "mood": "cinematic atmospheric",
    "subjects": [
        "cinematic landscape aerial",
        "dramatic light through clouds",
        "person walking empty street",
        "abstract light particles",
    ],
    "must_include": ["cinematic"],
    "must_exclude": [],
}

# Topic keyword → forced niche motif override (topic beats wrong UI niche)
TOPIC_NICHE_LOCK: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"stoa|marcus|aurelius|seneca|epiktetos|stoac", re.I), "6_stoic_philosophy"),
    (re.compile(r"whatsapp|mesajlaşma|mesaj hikay|chat story|sohbet ekran", re.I), "20_whatsapp_chat_story"),
    (re.compile(r"aita|itiraf|confession|reddit|am i wrong", re.I), "2_reddit_confessions"),
    (re.compile(r"yanılgı|mit |efsane|yanlış bilinen|doğru bilinen|bilimsel", re.I), "27_common_myths_busted"),
    (re.compile(r"\d+\s+(?:büyük|ilginç|önemli|sır|kural|adım|ipucu)|şaşırtıcı gerçek", re.I), "9_five_facts"),
    (re.compile(r"tercih et|would you rather", re.I), "4_would_you_rather"),
    (re.compile(r"bayrak|ülke tahmin|hangi ülke", re.I), "5_guess_flag_country"),
    (re.compile(r"paranormal|ufo|bermuda|51\.\s*bölge|gizem.*korku", re.I), "13_mystery_paranormal"),
    (re.compile(r"kripto|bitcoin|borsa|altın|hisse|dolar|enflasyon", re.I), "8_crypto_market"),
    (re.compile(r"karanlık psikoloji|manipülasyon|dark psychology", re.I), "7_dark_psychology"),
    (re.compile(r"transfer|futbol|premier league|şampiyonlar ligi|mbappe|messi", re.I), "15_football_transfers"),
    (re.compile(r"son dakika|flaş|\bhaber\b|deprem|kaza|trafik", re.I), "1_news_flash"),
    (re.compile(r"sigma|gigachad|alpha male|lone wolf", re.I), "24_sigma_character_study"),
    (re.compile(r"split.?screen|gameplay|minecraft|parkour|subway.?surfers", re.I), "3_split_gameplay"),
    (re.compile(r"zengin|milyoner|girişimci|pasif gelir|billionaire", re.I), "16_wealth_entrepreneurship"),
    (re.compile(r"chatgpt|yapay zeka|ai araç|midjourney|prompt", re.I), "21_ai_tools_hacks"),
    (re.compile(r"burç|astroloji|horoskop|zodyak", re.I), "18_astrology_horoscope"),
    (re.compile(r"film özeti|netflix|sinema|spoiler", re.I), "14_movie_summaries"),
    (re.compile(r"rüya tabiri|rüyada|dream meaning", re.I), "28_dream_meanings"),
    (re.compile(r"süper araba|lamborghini|ferrari|hypercar", re.I), "31_supercars_automotive"),
    (re.compile(r"fitness|protein|kilo ver|kas yap", re.I), "23_fitness_nutrition_hacks"),
    (re.compile(r"dini|ayet|hadis|kuran|ibadet", re.I), "10_religious_quotes"),
]

# P1-02: alias phrases → niche (substring match, lower priority than regex lock)
TOPIC_NICHE_ALIASES: List[Tuple[str, str]] = [
    ("stoacilik", "6_stoic_philosophy"),
    ("stoicism", "6_stoic_philosophy"),
    ("marcus aurelius", "6_stoic_philosophy"),
    ("reddit hikaye", "2_reddit_confessions"),
    ("itiraf hikayesi", "2_reddit_confessions"),
    ("whatsapp hikaye", "20_whatsapp_chat_story"),
    ("sohbet hikayesi", "20_whatsapp_chat_story"),
    ("kripto para", "8_crypto_market"),
    ("bitcoin", "8_crypto_market"),
    ("5 ilginç gerçek", "9_five_facts"),
    ("would you rather", "4_would_you_rather"),
    ("hangi ülke", "5_guess_flag_country"),
    ("bermuda", "13_mystery_paranormal"),
    ("ufo", "13_mystery_paranormal"),
    ("manipülasyon", "7_dark_psychology"),
    ("dark psychology", "7_dark_psychology"),
    ("son dakika", "1_news_flash"),
    ("flaş haber", "1_news_flash"),
    ("yanlış bilinen", "27_common_myths_busted"),
    ("mitler", "27_common_myths_busted"),
]

# P1-02: dual-domain signals → hybrid niche id (metadata only; compile uses resolved standard niche)
TOPIC_HYBRID_SIGNALS: List[Tuple[List[str], List[str], str, str]] = [
    (["stoac", "marcus", "seneca", "epiktet"], ["cyberpunk", "neon", "distopya", "gelecek"], "stoic_cyberpunk", "6_stoic_philosophy"),
    (["tarih", "napolyon", "sezar", "churchill"], ["whatsapp", "mesaj", "chat", "imessage"], "history_chat", "19_historical_battles"),
    (["psikoloji", "manipül", "dark psych"], ["parkour", "gameplay", "split screen"], "dark_psychology_parkour", "7_dark_psychology"),
    (["gizem", "komplo", "bermuda", "ufo"], ["google earth", "zoom", "uydu"], "mystery_earth_zoom", "13_mystery_paranormal"),
]


def _match_aliases(text: str) -> Optional[str]:
    low = (text or "").lower()
    for phrase, niche_id in TOPIC_NICHE_ALIASES:
        if phrase in low:
            return niche_id
    return None


def _fuzzy_match_niche(title: str, min_hits: float = 1.5) -> Optional[str]:
    """Score topic against NICHES trending_keywords + names."""
    try:
        from niche_templates import NICHES
    except ImportError:
        return None
    text = (title or "").lower()
    tokens = _tokenize(title)
    best_id: Optional[str] = None
    best_score = 0.0
    for nid, niche in NICHES.items():
        score = 0.0
        for kw in niche.get("trending_keywords", []):
            kl = kw.lower()
            if kl in text:
                score += 2.0
            elif any(kl in t or t in kl for t in tokens if len(t) >= 3):
                score += 1.0
        for label in (niche.get("name", ""), niche.get("name_en", "")):
            for part in label.lower().split():
                if len(part) >= 5 and part in text:
                    score += 0.75
        if score > best_score:
            best_score = score
            best_id = nid
    if best_score >= min_hits:
        return best_id
    # difflib fallback against niche display names
    names = {nid: (n.get("name", "") or nid) for nid, n in NICHES.items()}
    matches = difflib.get_close_matches(text[:60], list(names.values()), n=1, cutoff=0.55)
    if matches:
        for nid, name in names.items():
            if name == matches[0]:
                return nid
    return None


def _detect_hybrid_niche(title: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (hybrid_id, fallback_standard_niche) when dual-domain keywords hit."""
    low = (title or "").lower()
    for group_a, group_b, hybrid_id, fallback in TOPIC_HYBRID_SIGNALS:
        hit_a = any(k in low for k in group_a)
        hit_b = any(k in low for k in group_b)
        if hit_a and hit_b:
            return hybrid_id, fallback
    return None, None


def resolve_topic_intelligence(title: str, niche_id: str) -> Dict[str, Any]:
    """P1-02: full topic→niche resolution with method + optional hybrid hint."""
    text = title or ""
    requested = niche_id or "1_news_flash"
    for pattern, locked in TOPIC_NICHE_LOCK:
        if pattern.search(text):
            hybrid, _ = _detect_hybrid_niche(text)
            return {
                "resolved_niche": locked,
                "requested_niche": requested,
                "match_method": "regex_lock",
                "hybrid_niche": hybrid,
                "locked": locked != requested,
            }
    alias = _match_aliases(text)
    if alias:
        hybrid, _ = _detect_hybrid_niche(text)
        return {
            "resolved_niche": alias,
            "requested_niche": requested,
            "match_method": "alias",
            "hybrid_niche": hybrid,
            "locked": alias != requested,
        }
    hybrid, hybrid_fallback = _detect_hybrid_niche(text)
    if hybrid and hybrid_fallback:
        return {
            "resolved_niche": hybrid_fallback,
            "requested_niche": requested,
            "match_method": "hybrid",
            "hybrid_niche": hybrid,
            "locked": hybrid_fallback != requested,
        }
    fuzzy = _fuzzy_match_niche(text)
    if fuzzy:
        return {
            "resolved_niche": fuzzy,
            "requested_niche": requested,
            "match_method": "fuzzy",
            "hybrid_niche": None,
            "locked": fuzzy != requested,
        }
    return {
        "resolved_niche": requested,
        "requested_niche": requested,
        "match_method": "passthrough",
        "hybrid_niche": None,
        "locked": False,
    }


def resolve_niche_from_topic(title: str, niche_id: str) -> str:
    return resolve_topic_intelligence(title, niche_id)["resolved_niche"]


def get_motif_bank(niche_id: str) -> Dict[str, Any]:
    return NICHE_MOTIFS.get(niche_id, _DEFAULT_MOTIF)


def _tokenize(text: str) -> set:
    return {t for t in re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{3,}", (text or "").lower())}


def _intent_for_subject(
    scene: ScenePlan,
    bank: Dict[str, Any],
    subject: str,
    scene_index: int,
) -> VisualIntent:
    existing_q = scene.search_queries or []
    exclude = [e.lower() for e in bank.get("must_exclude", [])]
    clean_existing = []
    for q in existing_q:
        ql = q.lower()
        if any(ex in ql for ex in exclude):
            continue
        clean_existing.append(q)

    queries = [
        f"{subject} cinematic 4k",
        f"{subject} {bank.get('mood', 'cinematic')} atmospheric",
        f"{bank.get('era', '')} {subject}".strip(),
    ]
    for q in clean_existing[:2]:
        if q not in queries:
            queries.append(q)

    return VisualIntent(
        subject=subject,
        action="slow push in" if scene_index % 2 == 0 else "gentle pan",
        setting=str(bank.get("era", "")),
        era=str(bank.get("era", "")),
        mood=str(bank.get("mood", "cinematic")),
        must_include=list(bank.get("must_include") or []),
        must_exclude=list(bank.get("must_exclude") or []),
        continuity_motif=str(bank.get("motif", "default")),
        search_queries=queries,
    )


def build_visual_intent_for_scene(
    scene: ScenePlan,
    niche_id: str,
    title: str = "",
    scene_index: int = 0,
) -> VisualIntent:
    bank = get_motif_bank(niche_id)
    subjects: List[str] = list(bank.get("subjects") or _DEFAULT_MOTIF["subjects"])
    subject = subjects[scene_index % len(subjects)]

    narr_tokens = _tokenize(scene.narration)
    for cand in subjects:
        if _tokenize(cand) & narr_tokens:
            subject = cand
            break

    return _intent_for_subject(scene, bank, subject, scene_index)


def _fork_distinct_from_previous(
    intent: VisualIntent,
    scene: ScenePlan,
    bank: Dict[str, Any],
    scene_index: int,
    prev: VisualIntent,
) -> VisualIntent:
    """Rotate motif when split siblings would share subject + queries (P0-06)."""
    if intent.subject != prev.subject or intent.search_queries != prev.search_queries:
        return intent
    subjects: List[str] = list(bank.get("subjects") or _DEFAULT_MOTIF["subjects"])
    for offset in range(1, len(subjects)):
        alt = subjects[(scene_index + offset) % len(subjects)]
        if alt != prev.subject:
            return _intent_for_subject(scene, bank, alt, scene_index)
    return intent


def apply_visual_intents(scenes: List[ScenePlan], niche_id: str, title: str = "") -> List[ScenePlan]:
    locked = resolve_niche_from_topic(title, niche_id)
    bank = get_motif_bank(locked)
    for i, scene in enumerate(scenes):
        intent = build_visual_intent_for_scene(scene, locked, title=title, scene_index=i)
        if i > 0 and scenes[i - 1].visual_intent:
            intent = _fork_distinct_from_previous(
                intent, scene, bank, i, scenes[i - 1].visual_intent
            )
        scene.visual_intent = intent
        scene.search_queries = intent.search_queries
        if not scene.scene_description:
            scene.scene_description = f"{intent.subject} — {intent.mood}"
        scene.mood = intent.mood
    return scenes


def text_contains_excluded(text: str, must_exclude: List[str]) -> bool:
    low = (text or "").lower()
    return any(ex.lower() in low for ex in (must_exclude or []))


def semantic_relevance_score(
    candidate_text: str,
    narration: str,
    intent: Optional[VisualIntent] = None,
) -> float:
    """Token overlap score 0..40 for stock candidate ranking."""
    if intent and text_contains_excluded(candidate_text, intent.must_exclude):
        return -100.0
    cand = _tokenize(candidate_text)
    narr = _tokenize(narration)
    if intent:
        narr |= _tokenize(intent.subject) | _tokenize(intent.mood) | set(intent.must_include)
    if not cand or not narr:
        return 0.0
    overlap = len(cand & narr)
    return min(40.0, overlap * 8.0)
