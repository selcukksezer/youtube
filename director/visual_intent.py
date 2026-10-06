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
        "mood_palette": [
            "contemplative", "solemn", "disciplined", "calm",
            "epic", "reflective", "tense", "hopeful",
        ],
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
    "10_religious_quotes": {
        "motif": "islamic_devotion",
        "era": "sacred contemporary",
        "mood": "reverent peaceful",
        "mood_palette": [
            "reverent", "hopeful", "peaceful", "solemn",
            "luminous", "calm", "warm", "contemplative",
        ],
        "subjects": [
            "kaaba mecca sanctuary aerial",
            "mosque dome golden sunrise",
            "open quran pages soft light",
            "prayer hands raised dusk",
            "islamic geometric calligraphy",
            "quran golden calligraphy art",
            "minaret silhouette dawn",
            "olive grove peaceful morning",
            "mosque lantern interior glow",
            "ablution water fountain courtyard",
            "crescent moon over mosque",
            "prayer rug still life",
            "desert dunes sunrise calm",
            "arabic calligraphy closeup",
        ],
        "must_include": ["mosque", "quran", "prayer", "calligraphy", "sunrise", "kaaba", "architecture"],
        "must_exclude": [
            "statue", "idol", "marcus", "aurelius", "roman bust", "roman",
            "colosseum", "stoic", "philosopher portrait", "blacksmith",
            "bronze eagle", "alcohol", "beer", "wine", "pig", "pork",
            "prophet face", "muhammad face", "face of prophet",
            "fabric", "silk", "satin", "cloth ripple", "sheet",
        ],
    },
    "9_five_facts": {
        "motif": "classroom_science",
        "era": "contemporary",
        "mood": "curious clear",
        "subjects": [
            "open textbook classroom desk",
            "frozen lake iceberg winter",
            "classroom skeleton model",
            "honey jar close up",
            "ocean waves surface",
            "storm lightning strike",
        ],
        "must_include": ["classroom", "science", "nature"],
        "must_exclude": ["horror", "skull", "ghost", "bitcoin", "infographic"],
    },
    # ─── BÖLÜM 7.5: 16 STANDART NİŞ ÜRETİM PROFİLİ GÖRSEL MOTİFLERİ ─────────
    "2_philosophy_stoic": {
        "motif": "imperial_rome",
        "era": "ancient rome",
        "mood": "stoic calm contemplative",
        "mood_palette": ["contemplative", "solemn", "disciplined", "calm", "epic"],
        "subjects": [
            "bronze marcus aurelius statue",
            "ancient roman marble columns",
            "old parchment scroll torchlight",
            "roman forum at dusk",
            "stoic philosopher reading alone",
            "calm ocean horizon sunrise",
            "candle flame dark room",
        ],
        "must_include": ["marble", "rome", "scroll", "statue", "torch", "philosopher"],
        "must_exclude": ["skull", "ufo", "horror", "blood", "party", "modern tech"],
    },
    "3_bizarre_history": {
        "motif": "bizarre_history",
        "era": "historical vintage",
        "mood": "intriguing surreal vintage",
        "mood_palette": ["mysterious", "dramatic", "tense", "curious"],
        "subjects": [
            "sepia ancient artifact closeup",
            "vintage archival photograph",
            "victorian cobblestone street fog",
            "ancient tomb discovery torchlight",
            "old parchment secret map",
            "steampunk brass mechanism",
            "historical museum exhibit antique",
        ],
        "must_include": ["vintage", "history", "ancient", "archive", "parchment"],
        "must_exclude": ["modern smartphone", "cyberpunk neon", "supercar"],
    },
    "4_ai_money_tech": {
        "motif": "ai_future_tech",
        "era": "near future digital",
        "mood": "futuristic high tech energetic",
        "mood_palette": ["energetic", "urgent", "dramatic", "curious"],
        "subjects": [
            "neural network glowing nodes digital",
            "robotic humanoid hand precision",
            "data center servers blinking lights",
            "quantum computer circuit board",
            "abstract code matrix stream green",
            "cyberpunk holographic interface",
        ],
        "must_include": ["ai", "digital", "tech", "network", "code", "futuristic"],
        "must_exclude": ["ancient rome", "medieval armor", "farm nature"],
    },
    "5_luxury_lifestyle": {
        "motif": "ultra_luxury",
        "era": "contemporary elite",
        "mood": "luxurious prestigious sleek",
        "mood_palette": ["calm", "warm", "epic", "disciplined"],
        "subjects": [
            "private jet interior penthouse view",
            "luxury yacht mediterranean sunset",
            "carbon fiber supercar driving city",
            "high end gold wristwatch detail",
            "marble villa infinity pool dusk",
            "expensive champagne celebration",
        ],
        "must_include": ["luxury", "penthouse", "supercar", "yacht", "mansion", "gold"],
        "must_exclude": ["dirty street", "ruins", "horror", "cheap plastic"],
    },
    "6_psychology_tricks": {
        "motif": "mind_shadow",
        "era": "contemporary",
        "mood": "tense psychological",
        "mood_palette": ["tense", "mysterious", "dramatic", "solemn"],
        "subjects": [
            "silhouette of person in doorway",
            "chess board strategic move closeup",
            "mirror reflection distorted dark",
            "neon rain reflections city night",
            "subtle eye contact extreme closeup",
        ],
        "must_include": ["silhouette", "mirror", "shadow", "chess", "reflection"],
        "must_exclude": ["cartoon kids", "bright comedy", "sunny beach"],
    },
    "7_space_cosmos": {
        "motif": "deep_space",
        "era": "cosmic eternal",
        "mood": "awe-inspiring vast mysterious",
        "mood_palette": ["epic", "mysterious", "calm", "contemplative"],
        "subjects": [
            "james webb nebula galaxy colors",
            "black hole accretion disk simulation",
            "solar flare sun surface telescope",
            "astronaut spacewalk earth background",
            "saturn rings close up majestic",
            "star cluster deep void darkness",
        ],
        "must_include": ["space", "galaxy", "nebula", "planet", "cosmos", "stars"],
        "must_exclude": ["office desk", "living room", "traffic street"],
    },
    "8_survival_myth": {
        "motif": "wilderness_survival",
        "era": "raw wild",
        "mood": "intense rugged thrilling",
        "mood_palette": ["urgent", "tense", "dramatic", "epic"],
        "subjects": [
            "campfire night wilderness forest",
            "blizzard mountain peak climber",
            "deep jungle river crossing danger",
            "desert dunes mirage scorching sun",
            "survival knife carving wood",
            "raging ocean storm waves boat",
        ],
        "must_include": ["survival", "forest", "wild", "mountain", "nature", "fire"],
        "must_exclude": ["city office", "neon club", "shopping mall"],
    },
    "10_fitness_biohack": {
        "motif": "athletic_performance",
        "era": "contemporary high energy",
        "mood": "powerful disciplined dynamic",
        "mood_palette": ["energetic", "urgent", "disciplined", "dramatic"],
        "subjects": [
            "sweat dripping athlete barbell deadlift",
            "sprinting track slow motion muscles",
            "cold plunge ice bath recovery",
            "dna helix biotechnology render",
            "heart rate monitor pulse data",
            "boxing heavy bag power impact",
        ],
        "must_include": ["fitness", "athlete", "muscle", "workout", "gym", "biohack"],
        "must_exclude": ["fast food burger", "couch potato", "ancient scroll"],
    },
    "11_reddit_stories": {
        "motif": "relatable_drama",
        "era": "contemporary internet",
        "mood": "suspenseful emotional candid",
        "mood_palette": ["tense", "dramatic", "mysterious", "solemn"],
        "subjects": [
            "hands typing on smartphone glowing screen",
            "person sitting head in hands emotional",
            "dark bedroom looking out window rain",
            "subway train commute reflection",
            "whispering secret shadow silhouette",
        ],
        "must_include": ["smartphone", "person", "shadow", "reflection", "rain"],
        "must_exclude": ["ancient rome", "space nebula", "supercar"],
    },
    "12_amazon_affiliate": {
        "motif": "smart_gadget_review",
        "era": "modern consumer lifestyle",
        "mood": "crisp aesthetic satisfying",
        "mood_palette": ["warm", "calm", "curious", "energetic"],
        "subjects": [
            "sleek ergonomic desk setup clean",
            "unboxing tech gadget hands closeup",
            "smart home automation device glowing",
            "portable lifestyle everyday carry",
            "aesthetic kitchen gadget demo",
        ],
        "must_include": ["gadget", "desk", "tech", "device", "lifestyle", "clean"],
        "must_exclude": ["horror skull", "blood", "ancient ruin"],
    },
    "13_crypto_finance": {
        "motif": "finance_pulse",
        "era": "contemporary",
        "mood": "tense energetic",
        "mood_palette": ["urgent", "dramatic", "energetic", "tense", "calm"],
        "subjects": [
            "stock chart candlestick screen red green",
            "bitcoin gold coin close up metallic",
            "trading desk multiple monitors live",
            "city financial district aerial dusk",
            "blockchain cyber network grid",
        ],
        "must_include": ["chart", "coin", "market", "trading", "bitcoin"],
        "must_exclude": ["horror skull", "farm nature", "kids"],
    },
    "14_mysterious_cases": {
        "motif": "dark_archive",
        "era": "modern mystery",
        "mood": "chilling suspenseful",
        "mood_palette": ["mysterious", "tense", "solemn", "dramatic"],
        "subjects": [
            "foggy dark forest night cinematic",
            "abandoned archive case files dust",
            "police tape fluttering street light",
            "dark corridor flickering bulb",
            "vintage typewriter investigation notes",
        ],
        "must_include": ["fog", "shadow", "archive", "mystery", "police"],
        "must_exclude": ["bright beach", "cartoon comedy", "sunny day"],
    },
    "15_parenting_hacks": {
        "motif": "family_comfort",
        "era": "warm contemporary",
        "mood": "heartwarming clever reassuring",
        "mood_palette": ["warm", "peaceful", "calm", "hopeful"],
        "subjects": [
            "parent toddler learning blocks colorful",
            "baby sleeping peacefully soft lighting",
            "family kitchen healthy breakfast",
            "creative sensory toy child hands",
            "sunny nursery organized shelves calm",
        ],
        "must_include": ["family", "baby", "parent", "child", "home", "warm"],
        "must_exclude": ["horror skull", "blood", "nightclub", "cyberpunk"],
    },
    "16_islamic_wisdom": {
        "motif": "islamic_devotion",
        "era": "sacred contemporary",
        "mood": "reverent peaceful",
        "mood_palette": ["reverent", "hopeful", "peaceful", "solemn", "luminous", "calm"],
        "subjects": [
            "mosque dome golden sunrise morning",
            "open quran pages soft sunlight",
            "prayer hands raised dusk peaceful",
            "islamic geometric calligraphy gold",
            "dark blue satin silk flow slow motion",
            "minaret silhouette dawn horizon",
        ],
        "must_include": ["mosque", "quran", "prayer", "calligraphy", "sunrise", "silk"],
        "must_exclude": [
            "statue", "idol", "marcus aurelius", "colosseum", "alcohol",
            "wine", "beer", "pig", "pork", "prophet face",
        ],
    },
    "2_reddit_confessions": {
        "motif": "relatable_drama",
        "era": "contemporary internet",
        "mood": "suspenseful emotional candid",
        "mood_palette": ["tense", "dramatic", "mysterious"],
        "subjects": [
            "hands typing on smartphone glowing screen",
            "person sitting head in hands emotional",
            "dark bedroom looking out window rain",
        ],
        "must_include": ["smartphone", "person", "shadow", "rain"],
        "must_exclude": ["ancient rome", "space nebula", "supercar"],
    },
}

_DEFAULT_MOTIF = {
    "motif": "cinematic_general",
    "era": "contemporary",
    "mood": "cinematic atmospheric",
    "mood_palette": [
        "urgent", "dramatic", "energetic", "tense", "calm",
        "epic", "mysterious", "hopeful", "solemn", "warm",
    ],
    "subjects": [
        "cinematic landscape aerial",
        "dramatic light through clouds",
        "person walking empty street",
        "abstract light particles",
    ],
    "must_include": ["cinematic"],
    "must_exclude": ["horror", "skull", "ghost"],
}

DEFAULT_MOOD_CYCLE = _DEFAULT_MOTIF["mood_palette"]

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
    "religious": NICHE_MOTIFS["10_religious_quotes"],
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
    "kids": {
        "motif": "kids_soft_cartoon",
        "era": "storybook",
        "mood": "warm pastel playful",
        "mood_palette": ["sunny meadow", "soft rainbow", "gentle bedtime glow"],
        "subjects": [
            "friendly cartoon forest animals",
            "pastel alphabet letters floating",
            "cute cartoon cat sharing toys",
            "colorful numbers dancing softly",
            "gentle cartoon birds in treehouse",
        ],
        "must_include": ["cartoon", "pastel", "friendly"],
        "must_exclude": [
            "horror", "skull", "ghost", "blood", "weapon", "jump scare",
            "photoreal child", "real kid face", "dark psychology", "gore",
        ],
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
    (re.compile(r"son dakika|\bflaş\b|\bhaber\b|deprem|\bkaza\b|trafik", re.I), "1_news_flash"),
    (re.compile(r"sigma|gigachad|alpha male|lone wolf", re.I), "24_sigma_character_study"),
    (re.compile(r"split.?screen|gameplay|minecraft|parkour|subway.?surfers", re.I), "3_split_gameplay"),
    (re.compile(r"zengin|milyoner|girişimci|pasif gelir|billionaire", re.I), "16_wealth_entrepreneurship"),
    (re.compile(r"chatgpt|yapay zeka|ai araç|midjourney|prompt", re.I), "21_ai_tools_hacks"),
    (re.compile(r"burç|burcu|\bburc\b|astroloji|horoskop|zodyak|koç burcu|akrep|yengeç|başak|terazi|yay burcu|oğlak|kova|balık burcu|merkür|retrograd", re.I), "18_astrology_horoscope"),
    # Prefer astrology lock before AI-tools fuzzy traps on words like "güç" / "etki"
    (re.compile(r"film özeti|netflix|sinema|spoiler", re.I), "14_movie_summaries"),
    (re.compile(r"rüya tabiri|rüyada|dream meaning", re.I), "28_dream_meanings"),
    (re.compile(r"süper araba|lamborghini|ferrari|hypercar", re.I), "31_supercars_automotive"),
    (re.compile(r"fitness|protein|kilo ver|kas yap", re.I), "23_fitness_nutrition_hacks"),
    (re.compile(r"dini|ayet|hadis|kuran|kur'an|ibadet|peygamber|\bdua\b|allah|namaz|isl[aâ]m|sahabe|sünnet|sunnet|\bsure(?:si|ler)?\b", re.I), "10_religious_quotes"),
    (re.compile(r"ingilizce deyim|dil öğrenme|language hack|yabancı dil", re.I), "11_language_learning"),
    (re.compile(r"amazon ürün|trendyol|viral gadget|affiliate ürün", re.I), "12_amazon_affiliate"),
    (re.compile(r"before after|evrim belgesel|then vs now|100 yıl önce", re.I), "17_before_after_evolution"),
    (re.compile(r"tarihi savaş|osmanlı|savaş taktik|history battle", re.I), "19_historical_battles"),
    (re.compile(r"emoji quiz|emoji oyunu|guess the movie emoji", re.I), "22_emoji_guess_game"),
    (re.compile(r"ünlü serveti|net worth|zengin ünlü|celebrity fortune", re.I), "25_celebrity_net_worth"),
    (re.compile(r"tehlikeli yerler|yasak bölge|forbidden places|ölümcül ada", re.I), "26_dangerous_places"),
    (re.compile(r"canlı quiz|interaktif quiz|quiz shorts|3 saniyede bil", re.I), "37_interactive_quiz"),
    (re.compile(r"optik illüzyon|zeka testi|optical illusion|iq test", re.I), "29_optical_illusions_iq"),
    (re.compile(r"nazım hikmet|cemal süreya|aşk şiiri|şiir dinle", re.I), "30_poetry_quotes"),
    (re.compile(r"tüketici hakları|iade hakkı|hukuki hak|vatandaş hakkı", re.I), "32_legal_consumer_hacks"),
    (re.compile(r"ebeveynlik|çocuk psikolojisi|parenting hack|anne baba tüyosu", re.I), "33_parenting_child_hacks"),
    (re.compile(r"easter egg|gta sırları|oyun sırrı|game secret", re.I), "34_gaming_easter_eggs"),
    (re.compile(r"vahşi hayvan|hayvanlar alemi|animal kingdom|doğa belgeseli", re.I), "35_animal_kingdom_stories"),
    (re.compile(
        r"çocuk animasyon|kids cartoon|alfabe şarkısı|yumuşak eğitim|"
        r"çocuklar için animasyon|kids shorts|ahlak hikayesi çocuk",
        re.I,
    ), "36_kids_animation"),
    (re.compile(r"biliyor muydunuz|ilginç bilgi|mind blowing facts", re.I), "9_five_facts"),
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
    ("peygamber duası", "10_religious_quotes"),
    ("günlük dua", "10_religious_quotes"),
    ("hadis şerifi", "10_religious_quotes"),
    ("kuran ayeti", "10_religious_quotes"),
    ("islamic wisdom", "16_islamic_wisdom"),
    ("space and cosmos", "7_space_cosmos"),
    ("space", "7_space_cosmos"),
    ("cosmos", "7_space_cosmos"),
    ("uzay ve kozmoloji", "7_space_cosmos"),
    ("uzay", "7_space_cosmos"),
    ("bizarre history", "3_bizarre_history"),
    ("tuhaf tarih", "3_bizarre_history"),
    ("ai money", "4_ai_money_tech"),
    ("luxury lifestyle", "5_luxury_lifestyle"),
    ("lüks yaşam", "5_luxury_lifestyle"),
    ("survival myth", "8_survival_myth"),
    ("hayatta kalma efsane", "8_survival_myth"),
    ("fitness biohack", "10_fitness_biohack"),
    ("parenting hacks", "15_parenting_hacks"),
    ("ebeveynlik ipuç", "15_parenting_hacks"),
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


SHOT_TAGS = ("establishing", "closeup", "action", "transition")
_SHOT_CAMERA = {
    "establishing": "slow wide push",
    "closeup": "gentle push",
    "action": "quick pan",
    "transition": "pull back",
}
_SHOT_FRAME = {
    "establishing": "wide shot",
    "closeup": "close up",
    "action": "motion",
    "transition": "wide shot",
}
_SHOT_FIGHTS = {
    "establishing": ("close up", "closeup", "macro"),
    "closeup": ("wide shot", "aerial"),
    "action": (),
    "transition": ("close up", "closeup", "macro"),
}
_CLOSE_SHOT_RE = re.compile(
    r"\b(göz|yüz|el|parmak|detay|yakın|close|eye|face|hand|detail|macro)\b",
    re.IGNORECASE,
)
_ACTION_SHOT_RE = re.compile(
    r"\b(koş|düş|çarp|patla|kaç|vur|fırla|run|crash|hit|explode|chase|sprint)\b",
    re.IGNORECASE,
)


def assign_shot_type(narration: str, index: int, total: int, beat_type: str = "") -> str:
    """One framing tag per scene. Last scene pulls back. Verbs beat the default wide."""
    text = narration or ""
    if total > 1 and index == total - 1:
        return "transition"
    if _ACTION_SHOT_RE.search(text) or str(beat_type or "") == "climax":
        return "action"
    if _CLOSE_SHOT_RE.search(text):
        return "closeup"
    if index == 0 or str(beat_type or "") == "hook":
        return "establishing"
    return "closeup" if index % 2 else "establishing"


def _intent_for_subject(
    scene: ScenePlan,
    bank: Dict[str, Any],
    subject: str,
    scene_index: int,
    locked: bool = False,
    shot_type: str = "",
) -> VisualIntent:
    tag = shot_type if shot_type in SHOT_TAGS else assign_shot_type(
        scene.narration or "", scene_index, 0, getattr(scene, "beat_type", "") or ""
    )
    frame = _SHOT_FRAME[tag]
    fights = _SHOT_FIGHTS[tag]
    existing_q = scene.search_queries or []
    exclude = [e.lower() for e in bank.get("must_exclude", [])]
    clean_existing = []
    for q in existing_q:
        ql = q.lower()
        if any(ex in ql for ex in exclude):
            continue
        if any(bad in ql for bad in fights):
            continue
        clean_existing.append(q)

    palette = bank.get("mood_palette") or []
    scene_mood = palette[scene_index % len(palette)] if palette else str(bank.get("mood", "cinematic"))

    # One framing. A close-up query on a wide scene returns the wrong clip.
    queries = [subject, f"{subject} {frame}"]
    if not locked:
        era_q = f"{bank.get('era', '')} {subject}".strip()
        if era_q and era_q not in queries:
            queries.append(era_q)
    for q in clean_existing[:2]:
        if q not in queries:
            queries.append(q)

    return VisualIntent(
        subject=subject,
        action=_SHOT_CAMERA[tag],
        shot_type=tag,
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
    shot_type: str = "",
) -> VisualIntent:
    bank = get_motif_bank(niche_id)
    # The sentence wins. The title fills a sentence that names nothing filmable.
    # Niche motif (ocean, marble, fog) is only the fallback.
    from visuals.subject_lock import match_shot

    shot = match_shot(scene.narration or "")
    if shot is None:
        shot = match_shot(scene.scene_description or "")
    if shot is None and title:
        shot = match_shot(title)
    if shot is not None:
        return _intent_for_subject(
            scene, bank, shot.primary, scene_index, locked=True, shot_type=shot_type
        )

    subjects: List[str] = list(bank.get("subjects") or _DEFAULT_MOTIF["subjects"])
    subject = subjects[scene_index % len(subjects)]

    narr_tokens = _tokenize(scene.narration)
    for cand in subjects:
        if _tokenize(cand) & narr_tokens:
            subject = cand
            break

    return _intent_for_subject(
        scene, bank, subject, scene_index, locked=False, shot_type=shot_type
    )


def _fork_distinct_from_previous(
    intent: VisualIntent,
    scene: ScenePlan,
    bank: Dict[str, Any],
    scene_index: int,
    prev: VisualIntent,
    shot_type: str = "",
) -> VisualIntent:
    """Rotate motif when split siblings would share subject + queries (P0-06)."""
    if intent.subject != prev.subject or intent.search_queries != prev.search_queries:
        return intent
    # Same real subject on a split: change the angle, not the object.
    from visuals.subject_lock import next_variant
    alt_shot = next_variant(intent.subject, scene_index)
    if alt_shot and alt_shot != prev.subject:
        return _intent_for_subject(
            scene, bank, alt_shot, scene_index, locked=True, shot_type=shot_type or intent.shot_type
        )
    subjects: List[str] = list(bank.get("subjects") or _DEFAULT_MOTIF["subjects"])
    for offset in range(1, len(subjects)):
        alt = subjects[(scene_index + offset) % len(subjects)]
        if alt != prev.subject:
            return _intent_for_subject(
                scene, bank, alt, scene_index, shot_type=shot_type or intent.shot_type
            )
    return intent


# ─── INVIDEO-AI-NEXUS SHOT INTENTS MAP (Section 2.1.5 & Section 28.5) ───────
# Explicit intent-to-camera motion mappings: Question=zoom_in, Transition=pan_left, Conclusion=zoom_out
SHOT_INTENTS: Dict[str, Dict[str, Any]] = {
    "question": {
        "intent": "closeup",
        "camera_direction": "zoom_in",
        "action": "slow push in",
        "description": "Soru ve kanca anında izleyiciyi ekrana kilitleyen yakınlaşma.",
    },
    "transition": {
        "intent": "transition",
        "camera_direction": "pan_left",
        "action": "pan left",
        "description": "Sahne ve konu geçişlerinde akıcı yatay kamera kayması.",
    },
    "conclusion": {
        "intent": "establishing",
        "camera_direction": "zoom_out",
        "action": "slow pull out",
        "description": "Sonuç, kapanış ve döngü köprüsünde büyük resmi gösteren uzaklaşma.",
    },
    "action": {
        "intent": "action",
        "camera_direction": "pan_right",
        "action": "dynamic pan right",
        "description": "Yüksek tempolu olay örgüsü ve dinamik hareket.",
    },
    "closeup": {
        "intent": "closeup",
        "camera_direction": "zoom_in",
        "action": "tight focus zoom in",
        "description": "Somut nesne, yüz ifadesi ve şok detayı.",
    },
    "establishing": {
        "intent": "establishing",
        "camera_direction": "zoom_out",
        "action": "wide establishing pull out",
        "description": "Geniş çevre ve atmosfer kurulumu.",
    },
}


def classify_scene_intent(
    narration: str = "",
    beat_type: str = "conflict",
    index: int = 0,
    total_scenes: int = 1,
    title: str = "",
    scene_description: str = "",
) -> str:
    """
    Bölüm 7.6 & 28.5 (invideo-ai-nexus pattern):
    Sahne niyetini belirler:
    - 'question': Soru/merak kancası -> Kamera: zoom_in
    - 'transition': Konu/zaman geçişi -> Kamera: pan_left
    - 'conclusion': Sonuç/kapanış/döngü köprüsü -> Kamera: zoom_out
    - 'closeup': Şok edici detay, yüz ifadesi, mikro obje -> Kamera: zoom_in
    - 'action': Yüksek tempolu hareket, çatışma, dinamik olay -> Kamera: pan_right
    - 'establishing': Geniş çevre ve dünya kurulumu -> Kamera: zoom_out
    """
    combined = f"{narration} {scene_description}".lower()
    tokens = _tokenize(combined)

    def _hit(words: List[str]) -> int:
        score = 0
        for kw in words:
            piece = kw.lower()
            if " " in piece:
                if piece in combined:
                    score += 1
                continue
            if any(t == piece or (len(piece) >= 3 and t.startswith(piece)) for t in tokens):
                score += 1
        return score

    # 0. Soru / Kanca kontrolü (invideo-ai-nexus: Soru = zoom-in)
    question_triggers = [
        "?", "neden", "nasıl", "kim", "hiç merak", "biliyor musun", "fark ettin mi",
        "why", "how", "what if", "did you know", "ever wonder"
    ]
    if "?" in narration or _hit(question_triggers) > 0:
        if index == 0 or "neden" in combined or "nasıl" in combined or "?" in narration:
            return "question"

    # 1. Açılış sahnesi (Hook / index 0)
    if index == 0:
        closeup_hook_triggers = [
            "bu adam", "fark ettin", "gözlerine", "yüzü", "parmak", "sır",
            "fısıld", "baktı", "küçük", "close up", "detay", "shock", "göz", "yüz"
        ]
        if _hit(closeup_hook_triggers):
            return "closeup"
        return "establishing"

    # 2. Son sahne (Outro / Loop Bridge / Conclusion -> invideo-ai-nexus: Sonuç = zoom-out)
    conclusion_keywords = [
        "sonuç", "aslında", "işte bu yüzden", "böylece", "artık", "sonunda",
        "finally", "in the end", "conclusion", "remember"
    ]
    if total_scenes > 1 and index == total_scenes - 1:
        if _hit(conclusion_keywords) > 0 or beat_type in ("resolution", "climax"):
            return "conclusion"
        return "transition"

    # 3. Anlamsal anahtar kelime eşlemeleri
    establishing_keywords = [
        "dünya", "evren", "şehir", "tarihte", "uzay", "geniş", "ufuk", "sokak",
        "orman", "deniz", "gökyüzü", "aerial", "skyline", "landscape", "overview",
        "wide", "bütün", "krallık", "imparatorluk", "tapınak", "galaksi", "alan",
        "manzara", "saray", "meydan"
    ]
    closeup_keywords = [
        "göz", "yüz", "parmak", "yazı", "belge", "kitap", "para", "telefon",
        "fısıld", "küçük", "detay", "baktı", "hisset", "macro", "micro", "face",
        "hands", "letter", "coin", "altın", "saat", "ekran", "parşömen", "heykel",
        "mektup", "imza", "gözlük"
    ]
    action_keywords = [
        "koş", "patla", "fırla", "vur", "kaç", "savaş", "hızla", "çarp",
        "hareket", "sıçra", "dövüş", "tırman", "run", "jump", "explode", "strike",
        "speed", "fight", "yangın", "hücum", "kavga", "dalga", "fırtına", "kaza"
    ]
    transition_keywords = [
        "ancak", "fakat", "ardından", "sonra", "yıllar", "dönüş", "sonunda",
        "farklı", "geçiş", "köprü", "birden", "oysa", "lakin", "derken", "bunun yerine",
        "zamanla", "artık", "tam o anda", "however", "meanwhile", "later", "then"
    ]

    scores = {
        "action": _hit(action_keywords),
        "closeup": _hit(closeup_keywords),
        "establishing": _hit(establishing_keywords),
        "transition": _hit(transition_keywords),
    }

    best_intent = max(scores, key=lambda k: scores[k])
    if scores[best_intent] > 0:
        return best_intent

    # 4. Beat type fallback
    beat_lower = (beat_type or "").lower()
    if beat_lower in ("hook",):
        return "establishing"
    elif beat_lower in ("climax", "conflict", "action"):
        return "action"
    elif beat_lower in ("shock", "document", "quiz"):
        return "closeup"
    elif beat_lower in ("resolution", "bridge"):
        return "conclusion"

    # 5. Ritmik sıralı döngü fallback
    cycle = ["action", "closeup", "action", "establishing"]
    return cycle[index % len(cycle)]


def assign_camera_direction(
    scene_intent: str,
    index: int = 0,
    prev_direction: Optional[str] = None,
) -> str:
    """
    Bölüm 7.6 & 28.5 (invideo-ai-nexus pattern):
    Sahne niyetine göre akıllı kamera hareketi tayin eder:
    - question -> zoom_in
    - transition -> pan_left
    - conclusion -> zoom_out
    - closeup -> zoom_in
    - action -> pan_right
    - establishing -> zoom_out
    Ardışık sahnelerde aynı yönün körü körüne tekrarlanmasını önleyen variety kalkanı içerir.
    """
    # Öncelikli invideo-ai-nexus eşleme kuralı
    if scene_intent in SHOT_INTENTS:
        direct_cam = SHOT_INTENTS[scene_intent]["camera_direction"]
        # Eğer önceki yönle aynı değilse doğrudan niyet kuralını uygula
        if direct_cam != prev_direction:
            return direct_cam

    intent_direction_pools = {
        "question": ["zoom_in", "tilt_up"],
        "transition": ["pan_left", "tilt_down", "zoom_out"],
        "conclusion": ["zoom_out", "pan_right", "tilt_down"],
        "establishing": ["zoom_out", "pan_right", "zoom_in"],
        "closeup": ["zoom_in", "tilt_up", "zoom_out"],
        "action": ["pan_right", "pan_left", "tilt_up"],
    }
    pool = intent_direction_pools.get(scene_intent, ["zoom_in", "pan_right", "zoom_out", "pan_left"])

    chosen = pool[index % len(pool)]
    if prev_direction and chosen == prev_direction:
        for alt in pool:
            if alt != prev_direction:
                chosen = alt
                break
        else:
            general_alts = ["zoom_in", "pan_left", "zoom_out", "pan_right", "tilt_up"]
            for alt in general_alts:
                if alt != prev_direction:
                    chosen = alt
                    break

    return chosen


def apply_visual_intents(scenes: List[ScenePlan], niche_id: str, title: str = "") -> List[ScenePlan]:
    from scenes.narration_validate import scene_description_usable

    locked = resolve_niche_from_topic(title, niche_id)
    bank = get_motif_bank(locked)
    prev_cam: Optional[str] = None
    total = len(scenes)

    for i, scene in enumerate(scenes):
        sc_intent = classify_scene_intent(
            narration=scene.narration,
            beat_type=scene.beat_type,
            index=i,
            total_scenes=total,
            title=title,
            scene_description=scene.scene_description,
        )
        cam_dir = assign_camera_direction(sc_intent, index=i, prev_direction=prev_cam)
        scene.scene_intent = sc_intent
        scene.camera_direction = cam_dir
        prev_cam = cam_dir

        intent = build_visual_intent_for_scene(
            scene, locked, title=title, scene_index=i, shot_type=sc_intent
        )
        if i > 0 and scenes[i - 1].visual_intent:
            intent = _fork_distinct_from_previous(
                intent, scene, bank, i, scenes[i - 1].visual_intent, shot_type=sc_intent
            )
        scene.visual_intent = intent

        cam_to_action_map = {
            "zoom_in": "slow push in",
            "zoom_out": "slow pull out",
            "pan_left": "pan left",
            "pan_right": "pan right",
            "tilt_up": "tilt up",
            "tilt_down": "tilt down",
            "static": "static shot",
        }
        intent.action = cam_to_action_map.get(cam_dir, intent.action)
        intent.shot_type = sc_intent

        exclude = list(intent.must_exclude or [])
        fights = _SHOT_FIGHTS.get(sc_intent, ())
        from visuals.subject_lock import family_of_phrase, query_matches_clip
        locked_family = family_of_phrase(intent.subject)
        if scene.search_queries and (scene.narration or "").strip():
            merged = [
                q for q in scene.search_queries
                if not text_contains_excluded(q, exclude)
                and not any(bad in q.lower() for bad in fights)
            ]
            for q in intent.search_queries:
                if q not in merged and not text_contains_excluded(q, exclude):
                    merged.append(q)
            if locked_family is not None:
                on_subject = [
                    q for q in merged
                    if query_matches_clip(intent.subject, q) or query_matches_clip(q, intent.subject)
                ]
                if on_subject:
                    merged = on_subject
            scene.search_queries = (merged[:4] or list(intent.search_queries))
        else:
            scene.search_queries = intent.search_queries
        if not scene_description_usable(scene.scene_description or ""):
            from scenes.narration_validate import synthesize_scene_description
            scene.scene_description = synthesize_scene_description(scene)
        palette = bank.get("mood_palette") or DEFAULT_MOOD_CYCLE
        scene.mood = palette[i % len(palette)]
    return scenes


def text_contains_excluded(text: str, must_exclude: List[str]) -> bool:
    low = (text or "").lower()
    return any(ex.lower() in low for ex in (must_exclude or []))


def semantic_relevance_score(
    candidate_text: str,
    narration: str,
    intent: Optional[VisualIntent] = None,
) -> float:
    """Token overlap score 0..40 for stock candidate ranking (+ optional embedding boost)."""
    if intent and text_contains_excluded(candidate_text, intent.must_exclude):
        return -100.0
    cand = _tokenize(candidate_text)
    narr = _tokenize(narration)
    if intent:
        narr |= _tokenize(intent.subject) | _tokenize(intent.mood) | set(intent.must_include)
    if not cand or not narr:
        base = 0.0
    else:
        overlap = len(cand & narr)
        base = min(40.0, overlap * 8.0)

    # R10 #39: optional Gemini embedding cosine boost when enabled
    try:
        import config as _cfg
        if getattr(_cfg, "USE_GEMINI_EMBEDDINGS", False) and getattr(_cfg, "GEMINI_API_KEY", ""):
            boost = _embedding_similarity_boost(candidate_text, narration)
            base = min(40.0, base + boost)
    except Exception:
        pass
    return base


_EMBED_CACHE: Dict[str, List[float]] = {}


def _embedding_similarity_boost(a: str, b: str) -> float:
    """Return 0..12 boost from cosine similarity of Gemini embeddings."""
    va = _embed_text(a)
    vb = _embed_text(b)
    if not va or not vb:
        return 0.0
    import math
    dot = sum(x * y for x, y in zip(va, vb))
    na = math.sqrt(sum(x * x for x in va)) or 1.0
    nb = math.sqrt(sum(x * x for x in vb)) or 1.0
    cos = max(0.0, min(1.0, dot / (na * nb)))
    return cos * 12.0


def _embed_text(text: str) -> List[float]:
    key = (text or "").strip().lower()[:240]
    if not key:
        return []
    if key in _EMBED_CACHE:
        return _EMBED_CACHE[key]
    try:
        from google_ai_hub import embed_text
        ok, vec = embed_text(key)
        if ok and isinstance(vec, list) and vec:
            _EMBED_CACHE[key] = vec
            return vec
    except Exception:
        pass
    return []
