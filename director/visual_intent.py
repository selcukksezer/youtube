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
        "mood_palette": ["urgent", "dramatic", "energetic", "tense", "calm"],
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
    "must_exclude": ["horror", "skull", "ghost"],
}

# Family banks — every niche family has a visual policy; per-id NICHE_MOTIFS wins.
FAMILY_MOTIFS: Dict[str, Dict[str, Any]] = {
    "news": {
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
        "must_exclude": ["horror", "skull", "ghost", "ufo"],
    },
    "crypto": NICHE_MOTIFS["8_crypto_market"],
    "stoic": NICHE_MOTIFS["6_stoic_philosophy"],
    "mystery": NICHE_MOTIFS["13_mystery_paranormal"],
    "dark": NICHE_MOTIFS["7_dark_psychology"],
    "reddit": {
        "motif": "confession_story",
        "era": "contemporary",
        "mood": "tense emotional",
        "subjects": [
            "person typing laptop night",
            "anonymous hoodie silhouette",
            "apartment window rain",
            "phone screen closeup",
        ],
        "must_include": ["person", "room", "phone"],
        "must_exclude": ["horror", "skull", "ghost", "trading chart"],
    },
    "whatsapp": {
        "motif": "chat_ui",
        "era": "contemporary",
        "mood": "intimate tense",
        "subjects": [
            "smartphone chat green bubbles",
            "typing indicator phone screen",
            "hands holding phone night",
            "message notification closeup",
        ],
        "must_include": ["phone", "chat", "message"],
        "must_exclude": ["horror", "skull", "ghost", "bitcoin chart"],
    },
    "astrology": {
        "motif": "zodiac_night",
        "era": "celestial",
        "mood": "mystical",
        "subjects": [
            "zodiac constellation night sky",
            "tarot cards candle light",
            "galaxy purple nebula",
            "moon over calm ocean",
        ],
        "must_include": ["stars", "moon", "zodiac"],
        "must_exclude": ["horror", "skull", "ghost", "candlestick chart"],
    },
    "quiz": {
        "motif": "fact_cards",
        "era": "contemporary",
        "mood": "energetic curious",
        "subjects": [
            "bold infographic motion background",
            "library books research desk",
            "question mark neon light",
            "chalkboard facts list",
        ],
        "must_include": ["text space", "facts", "curious"],
        "must_exclude": ["horror", "skull", "ghost", "bitcoin"],
    },
    "product": {
        "motif": "lifestyle_product",
        "era": "contemporary",
        "mood": "clean energetic",
        "subjects": [
            "product closeup tabletop",
            "hands using gadget",
            "kitchen lifestyle hack",
            "unboxing desk natural light",
        ],
        "must_include": ["product", "hands", "lifestyle"],
        "must_exclude": ["horror", "skull", "ghost", "candlestick"],
    },
    "entertainment": {
        "motif": "story_world",
        "era": "contemporary",
        "mood": "cinematic curious",
        "subjects": [
            "wildlife animal closeup nature",
            "cinema film reel projector",
            "stadium crowd night lights",
            "gameplay screen neon",
        ],
        "must_include": ["cinematic", "story"],
        "must_exclude": ["horror", "skull", "ghost", "bitcoin chart"],
    },
    "general": _DEFAULT_MOTIF,
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
    (["would you rather", "kırmızı hap", "mavi hap", "tercih et"], ["quiz", "oylama", "seçim", "duel"], "would_you_rather_duel", "4_would_you_rather"),
    (["reddit", "itiraf", "aita"], ["asmr", "kinetik kum", "pasta", "soap cutting"], "reddit_asmr", "2_reddit_confessions"),
    (["evren", "kozmos", "galaksi", "james webb", "karadelik"], ["epik", "hans zimmer", "bas vuruş"], "cosmic_epic_hans_zimmer", "9_five_facts"),
    (["kripto", "bitcoin", "satoshi", "borsa", "wall street"], ["çizgi roman", "comic", "pop art", "halftone"], "crypto_comic_book", "8_crypto_market"),
    (["bayrak", "ülke tahmin", "hangi ülke"], ["sayac", "geri sayım", "countdown", "3 ipucu"], "country_guess_countdown", "5_guess_flag_country"),
    (["manevi", "dua", "ilahi", "spiritual"], ["yağmur", "orman", "doğa", "rain forest"], "spiritual_rain_nature", "10_religious_quotes"),
    (["whatsapp korku", "ses kaydı", "voice note"], ["korku", "gece yarısı", "hayalet", "horror"], "whatsapp_horror_voice", "20_whatsapp_chat_story"),
    (["amazon", "temu", "affiliate", "ürün inceleme"], ["hayatınızı kolaylaştır", "3 şey", "life hack"], "lifehack_affiliate_3items", "16_wealth_entrepreneurship"),
    (["ingilizce deyim", "filmde", "dizi", "peaky blinders"], ["deyim", "idiom", "friends"], "movie_idiom_english", "14_movie_summaries"),
    (["mitoloji", "zeus", "thor", "tanrı", "iskandinav"], ["ai animasyon", "epik animasyon", "hyper realistic"], "mythology_ai_epic", "27_common_myths_busted"),
    (["garip yasa", "absürt yasa", "yasak", "sıra dışı yasa"], ["harita", "dünya haritası", "singapur", "world map"], "weird_laws_world_map", "9_five_facts"),
    (["zenginlik", "old money", "disiplin", "motivasyon", "sessiz zenginlik"], ["yacht", "lüks", "klasik saat", "luxury", "old money"], "old_money_luxury_mindset", "16_wealth_entrepreneurship"),
    (["komplo", "gizli dosya", "fbi", "declassified"], ["gazete", "küpür", "sansür", "typewriter", "redacted"], "conspiracy_fbi_newspaper", "13_mystery_paranormal"),
    (["komik kedi", "funny cat", "meme", "viral hayvan"], ["nietzsche", "felsefe", "nihilism", "absürd"], "absurdist_philosophy_meme", "6_stoic_philosophy"),
    (["hayvan", "kedi", "köpek", "wildlife"], ["dublaj", "komik", "iç ses", "funny voice", "monolog"], "animal_funny_dub", "9_five_facts"),
    (["rüya tabiri", "rüyada", "dream meaning"], ["surreal", "dali", "gerçeküstü", "eriyen saat", "uçan kapı"], "dream_surreal_psychology", "28_dream_meanings"),
    (["yapay zeka", "ai araç", "chatgpt", "midjourney"], ["ekran kaydı", "canlı ekran", "site tanıtım", "laptop screen"], "ai_tools_screen", "21_ai_tools_hacks"),
    (["kitap özeti", "atomik alışkanlıklar", "1 dakika kitap"], ["hap bilgi", "özet", "sayfa çevir", "book summary"], "micro_book_summary", "9_five_facts"),
    (["suç", "mahkeme", "gerçek suç", "true crime"], ["polis telsiz", "cctv", "güvenlik kamerası", "dedektif"], "true_crime_police_radio", "13_mystery_paranormal"),
    (["optik illüzyon", "illüzyon", "hipnotik"], ["odak", "5 saniye", "merkeze bak", "focus test"], "optical_illusion_focus", "9_five_facts"),
    (["fiyat", "enflasyon", "100 dolar", "alışveriş sepeti"], ["1990", "zaman tüneli", "bugün", "yıl karşılaştır"], "price_timeline_tunnel", "8_crypto_market"),
    (["askeri taktik", "kuşatma", "savaş taktik", "strateji"], ["harita", "kırmızı ok", "mavi ok", "battle map"], "military_tactics_map", "19_historical_battles"),
    (["başarısızlık", "kovuldu", "reddedildi", "iflas"], ["walt disney", "steve jobs", "ünlü", "celebrity failure"], "celebrity_failure_stories", "16_wealth_entrepreneurship"),
    (["beden dili", "yalan", "mikro jest"], ["röportaj", "politik", "ünlü", "interview"], "body_language_celebrity", "7_dark_psychology"),
    (["2050", "gelecek simülasyon", "fütürist"], ["bir gün", "yaşam tasviri", "gelecekte"], "future_2050_simulation", "21_ai_tools_hacks"),
    (["derin deniz", "okyanus derinliği", "mariana", "abyss"], ["yaratık", "talasofobi", "bioluminescent", "10.000 metre"], "deep_sea_thalassophobia", "13_mystery_paranormal"),
    (["unutulmuş", "bilinmeyen kahraman", "gizli kahraman"], ["tarih", "şahsiyet", "arşiv", "portre"], "forgotten_historical_figures", "19_historical_battles"),
    (["zeka", "iq", "bilmece", "optik bilmece"], ["gizlenmiş", "7 saniye", "bul", "hidden object"], "iq_puzzle_optical_riddle", "9_five_facts"),
    (["e-ticaret", "girişim", "dropship", "startup"], ["minimalist", "tipografi", "siyah beyaz", "bold text"], "entrepreneur_minimal_typography", "16_wealth_entrepreneurship"),
    (["guinness", "dünya rekoru", "world record"], ["spiker", "heyecan", "rekor kır", "inanilmaz"], "world_records_sports_commentary", "9_five_facts"),
    (["bunu biliyor muydunuz", "did you know", "hap bilgi"], ["biyoloji", "3 gerçek", "akıl almaz", "fact"], "did_you_know_facts", "9_five_facts"),
    (["sokak röportaj", "mikro röportaj", "street interview"], ["tek soru", "sokaktaki", "el mikrofonu", "candid"], "micro_street_interview", "9_five_facts"),
    (["oppenheimer", "dune", "vizyona girdi", "yeni film"], ["felsefe", "tarih", "trend", "analiz"], "seasonal_trend_reaction", "14_movie_summaries"),
    (["ekolayzır", "ses frekans", "waveform", "podcast bar"], ["altyazı", "yeşil bar", "ritim", "equalizer"], "subtitle_voice_equalizer", "9_five_facts"),
    (["gece modu", "dark mode", "gece yarısı", "23:00"], ["karanlık tema", "rahatlatıcı", "uyku", "loş"], "night_mode_dark_content", "6_stoic_philosophy"),
    (["çark", "durdur", "spinning wheel", "rulet"], ["oyun", "doğru yerde", "durdurma", "yarışma"], "interactive_stop_wheel_game", "4_would_you_rather"),
    (["klostrofobi", "talasofobi", "araknofobi", "fobi"], ["korku", "bilinçaltı", "dar alan", "derin su"], "collective_subconscious_fears", "13_mystery_paranormal"),
    (["antik mısır", "gizli ilaç", "bitkisel şifa", "papirüs"], ["doğal tedavi", "reçete", "ot", "tıp tarihi"], "ancient_remedies_egypt", "27_common_myths_busted"),
    (["zaman makinesi", "100 yıl geri", "time machine"], ["dönüşüm", "timeline", "yıl sayacı", "tarih"], "time_machine_100years", "19_historical_battles"),
    (["morgan housel", "para psikolojisi", "psychology of money"], ["finans", "alıntı", "davranış", "risk"], "money_psychology_quotes", "16_wealth_entrepreneurship"),
    (["kapı 1", "kapı 2", "door 1", "door 2"], ["seçim", "yoruma yaz", "izleyici karar", "choice"], "viewer_choice_door_game", "4_would_you_rather"),
    (["gizli mikrofon", "wiretap", "sızdırılmış ses", "gizli toplantı"], ["kayıt", "fısıltı", "statik", "classified"], "hidden_wiretap_meeting", "13_mystery_paranormal"),
    (["fotoğraf restorasyon", "renklendirme", "eski fotoğraf", "photo restoration"], ["100 yıl", "yıpranmış", "canlandır", "before after"], "photo_restoration_story", "19_historical_battles"),
    (["sonder", "bilinmeyen kelime", "untranslatable", "tek kelime"], ["anlam", "duygu", "psikoloji", "dil"], "untranslatable_words_sonder", "28_dream_meanings"),
    (["ülke popüler", "en sevilen yemek", "country popular"], ["harita", "spor", "world map", "kültür"], "country_popular_things_map", "5_guess_flag_country"),
    (["kirli sır", "skandal", "pazarlama oyunu", "whistleblower"], ["fast food", "teknoloji devi", "şirket", "corporate"], "corporate_dirty_secrets", "16_wealth_entrepreneurship"),
    (["8d ses", "binaural", "ses illüzyon", "spatial audio"], ["kulaklık", "kafanın arkası", "8d audio", "headphones"], "binaural_8d_audio_illusions", "9_five_facts"),
    (["alternatif tarih", "what if tarih", "alternate history"], ["ikinci dünya savaşı", "yaşanmasaydı", "farklı sonuç", "timeline"], "alternate_history_ai", "19_historical_battles"),
    (["90lar nostalji", "2000ler", "çocukluk anısı", "retro tv"], ["game boy", "atari", "vhs", "crt tv"], "childhood_nostalgia_90s_2000s", "14_movie_summaries"),
    (["sporcu hikayesi", "comeback", "sakatlıktan dönüş"], ["şampiyon", "epik", "stadyum", "motivasyon"], "inspirational_athlete_comeback", "16_wealth_entrepreneurship"),
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
    if niche_id in NICHE_MOTIFS:
        return NICHE_MOTIFS[niche_id]
    try:
        from niche_templates import get_niche_family
        family = get_niche_family(niche_id)
    except Exception:
        family = "general"
    return FAMILY_MOTIFS.get(family, _DEFAULT_MOTIF)


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

    palette = bank.get("mood_palette") or []
    scene_mood = palette[scene_index % len(palette)] if palette else str(bank.get("mood", "cinematic"))

    queries = [
        f"{subject} cinematic 4k",
        f"{subject} {scene_mood} atmospheric",
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
        mood=scene_mood,
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
    from scenes.narration_validate import scene_description_usable

    locked = resolve_niche_from_topic(title, niche_id)
    bank = get_motif_bank(locked)
    for i, scene in enumerate(scenes):
        intent = build_visual_intent_for_scene(scene, locked, title=title, scene_index=i)
        if i > 0 and scenes[i - 1].visual_intent:
            intent = _fork_distinct_from_previous(
                intent, scene, bank, i, scenes[i - 1].visual_intent
            )
        scene.visual_intent = intent
        exclude = list(intent.must_exclude or [])
        if scene.search_queries and (scene.narration or "").strip():
            # Keep AI/fallback queries when narration exists; drop excluded tokens
            merged = [q for q in scene.search_queries if not text_contains_excluded(q, exclude)]
            for q in intent.search_queries:
                if q not in merged and not text_contains_excluded(q, exclude):
                    merged.append(q)
            scene.search_queries = (merged[:4] or list(intent.search_queries))
        else:
            scene.search_queries = intent.search_queries
        if not scene_description_usable(scene.scene_description or ""):
            scene.scene_description = f"{intent.subject} — {intent.mood}"
        palette = bank.get("mood_palette") or []
        scene.mood = palette[i % len(palette)] if palette else intent.mood
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
