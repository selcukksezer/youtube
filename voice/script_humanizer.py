"""
Script Humanization, SSML Prosody, Pronunciation & AI Cliché Cleansing
Covers items: 93, 134, 141, 142, 143, 144, 145, 147, 148, 149, 161, 164
"""
import re
from typing import Dict, List, Any, Optional

PRONUNCIATION_LIBRARY = {
    # Antik Roma & Yunan Filozofları
    "Marcus Aurelius": {"ipa": "ˈmɑːrkəs ɔːˈriːliəs", "spoken": "Marküs Avreliyus"},
    "Nietzsche": {"ipa": "ˈniːtʃə", "spoken": "Niçe"},
    "Friedrich Nietzsche": {"ipa": "ˈfriːdrɪx ˈniːtʃə", "spoken": "Fridrih Niçe"},
    "Socrates": {"ipa": "ˈsɒkrətiːz", "spoken": "Sokrates"},
    "Aristotle": {"ipa": "ˈærɪstɒtəl", "spoken": "Aristoteles"},
    "Plato": {"ipa": "ˈpleɪtoʊ", "spoken": "Platon"},
    "Seneca": {"ipa": "ˈsɛnɪkə", "spoken": "Seneka"},
    "Epictetus": {"ipa": "ˌɛpɪkˈtiːtəs", "spoken": "Epiktetos"},
    "Heraclitus": {"ipa": "ˌhɛrəˈklaɪtəs", "spoken": "Herakleitos"},
    "Diogenes": {"ipa": "daɪˈɒdʒɪniːz", "spoken": "Diyojen"},
    "Pythagoras": {"ipa": "paɪˈθæɡərəs", "spoken": "Pisagor"},
    "Archimedes": {"ipa": "ˌɑːrkɪˈmiːdiːz", "spoken": "Arşimed"},
    # Modern Düşünürler & Psikologlar
    "Machiavelli": {"ipa": "ˌmækiəˈvɛli", "spoken": "Makyavelli"},
    "Niccolò Machiavelli": {"ipa": "nikkoˈlɔ mmakjaˈvɛlli", "spoken": "Nikolo Makyavelli"},
    "Schopenhauer": {"ipa": "ˈʃoʊpənˌhaʊ.ər", "spoken": "Şopenhavır"},
    "Arthur Schopenhauer": {"ipa": "ˈaʁtuːɐ̯ ˈʃoːpn̩haʊ̯ɐ", "spoken": "Artur Şopenhavır"},
    "Carl Jung": {"ipa": "kɑːrl jʊŋ", "spoken": "Karl Yung"},
    "Sigmund Freud": {"ipa": "ˈziːkmʊnt ˈfʁɔʏt", "spoken": "Zigmund Froyd"},
    "Dostoevsky": {"ipa": "ˌdɒstəˈjɛfski", "spoken": "Dostoyevski"},
    "Fyodor Dostoevsky": {"ipa": "ˈfjodər dəstɐˈjɛfskʲɪj", "spoken": "Fyodor Dostoyevski"},
    "Franz Kafka": {"ipa": "fʁants ˈkafka", "spoken": "Franz Kafka"},
    "Descartes": {"ipa": "deɪˈkɑːrt", "spoken": "Dekart"},
    "René Descartes": {"ipa": "ʁəˈne deˈkaʁt", "spoken": "Röne Dekart"},
    "Spinoza": {"ipa": "spɪˈnoʊzə", "spoken": "Spinoza"},
    "Baruch Spinoza": {"ipa": "bɐˈʁux spɪˈnoːzaː", "spoken": "Baruh Spinoza"},
    "Kierkegaard": {"ipa": "ˈkɪərkəɡɑːrd", "spoken": "Kiyerkegor"},
    "Søren Kierkegaard": {"ipa": "ˈsœːɐn ˈkʰiɐ̯kəˌkɒːˀ", "spoken": "Sören Kiyerkegor"},
    "Sun Tzu": {"ipa": "suːn ˈdzuː", "spoken": "Sun Tsu"},
    "Confucius": {"ipa": "kənˈfjuːʃəs", "spoken": "Konfüçyüs"},
    # Tarihi Şahsiyetler
    "Julius Caesar": {"ipa": "ˈdʒuːliəs ˈsiːzər", "spoken": "Jül Sezar"},
    "Alexander the Great": {"ipa": "ˌælɪɡˈzændər ðə ɡreɪt", "spoken": "Büyük İskender"},
    "Cleopatra": {"ipa": "ˌkliːəˈpætrə", "spoken": "Kleopatra"},
}

# Relative deltas vs neutral; tts_engine rebases onto config.TTS_RATE for Shorts pace.
SPEECH_RHYTHM = {
    "hook": "+10%",   # → base+8 (punchy open)
    "body": "+2%",    # → base (config.TTS_RATE, typically +18%)
    "question": "-5%",  # → base-8 (slight hold on questions)
}

def apply_pronunciation_library(text: str, engine_type: str = "plain") -> str:
    """Applies Item 161 foreign-name pronunciations for the target TTS API."""
    result = text or ""
    for name, pronunciation in PRONUNCIATION_LIBRARY.items():
        if engine_type.lower() == "ssml":
            replacement = f'<phoneme alphabet="ipa" ph="{pronunciation["ipa"]}">{name}</phoneme>'
        else:
            replacement = pronunciation["spoken"]
        result = re.sub(re.escape(name), replacement, result, flags=re.IGNORECASE)
    return result

def sanitize_ai_cliches(text: str) -> str:
    """
    Item 134: Yapay Zeka Tarafından Üretilen Metnin İnsanlaştırılması.
    GPT çıktılarındaki 'Sonuç olarak', 'Özetle', 'Göz kamaştırıcı',
    'Unutmayın ki', 'Şüphesiz ki', 'Büyüleyici bir şekilde' gibi
    basmakalıp ve yapay kokan klişeleri temizler ve doğal konuşma diline uyarlar.
    """
    if not text:
        return ""

    cliches = [
        # Madde 186: Gereksiz "Merhaba Arkadaşlar / Kanalıma Hoş Geldiniz" Girişlerini Yasaklama
        (r'^\s*(herkese\s+)?(merhaba\s+arkadaşlar|merhabalar|selamlar|hepinize\s+merhaba)[!.,;:]*\s*', ''),
        (r'\b(kanalıma\s+hoş\s+geldiniz|videoma\s+hoş\s+geldiniz)[!.,;:]*\s*', ''),
        (r'\b(abone\s+olmayı\s+ve\s+beğenmeyi\s+unutmayın)[!.,;:]*\s*', ''),
        (r'^\s*(hello\s+(everyone|guys)|welcome\s+to\s+my\s+channel)[!.,;:]*\s*', ''),
        (r'\b(sonuç olarak|sonuçta)\b[,:]?\s*', ''),
        (r'\b(bu nedenle|bu yüzden|dolayısıyla)\b[,:]?\s*', ''),
        (r'\b(özetle|özetlemek gerekirse)\b[,:]?\s*', ''),
        (r'\b(kısacası)\b[,:]?\s*', ''),
        (r'\b(göz kamaştırıcı|büyüleyici bir şekilde)\b\s*', 'etkileyici '),
        (r'\b(şüphesiz ki|kuşkusuz)\b[,:]?\s*', ''),
        (r'\b(unutmayın ki|asla unutmayın)\b[,:]?\s*', 'Unutmayın, '),
        (r'\b(bu bir sır değil ki)\b[,:]?\s*', ''),
        (r'\b(adeta bir sanat eseri)\b\s*', 'oldukça etkileyici'),
        (r'\b(in the end|in conclusion)\b[,:]?\s*', ''),
        (r'\b(to sum up|in summary)\b[,:]?\s*', ''),
        (r'\b(dazzling|breathtaking)\b\s*', 'impressive '),
    ]

    cleaned = text
    for pattern, replacement in cliches:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r'^\s*[,;]\s*', '', cleaned)
    cleaned = re.sub(r'\s+([.!?,;:])', r'\1', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


# Alias for pipeline/compiler imports (P1-09)
cleanse_ai_cliches = sanitize_ai_cliches


def clean_narration_for_speech(text: str) -> str:
    """
    Seslendirmede (TTS) robotik olarak harf harf veya isim olarak okunan
    tüm emojileri, özel sembolleri (#, *, /, @ vb.) ve konuşmayı bozan karakterleri temizler.
    """
    if not text:
        return ""

    t = sanitize_ai_cliches(text)

    # 0. Strip SSML if any upstream path still injects markup (Item 93)
    t = re.sub(r'(?i)</?speak\b[^>]*>|</?prosody\b[^>]*>|</?break\b[^>]*/?>', ' ', t)
    t = re.sub(r'(?i)xmlns[^=]*=\s*["\'][^"\']*["\']|xml:lang\s*=\s*["\'][^"\']*["\']', ' ', t)
    t = re.sub(r'<[^>]+>', ' ', t)

    # 1. Unicode Emojileri temizle
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
    t = re.sub(r'[\u2000-\u32ff]', '', t)
    t = re.sub(r'[\u2600-\u27bf]', '', t)
    t = re.sub(r'[\ufe00-\ufe0f]', '', t)

    # 2. TTS motorunun kelime gibi okuduğu sembolleri temizle
    t = re.sub(r'[#*_~^\\/|<>@=`~=\[\]{}]', ' ', t)

    # 3. Fazla tire, alt çizgi veya tırnakları konuşma dostu yap
    t = re.sub(r'[-–—_"]+', ' ', t)

    # 4. Noktalama işaretlerinin önündeki gereksiz boşlukları toparla
    t = re.sub(r'\s+([.!?,;:])', r'\1', t)

    # 5. Ardışık noktaları standart tekli veya üçlü noktaya çevir
    t = re.sub(r'\.{4,}', '...', t)

    # 6. Fazla boşlukları temizle
    t = re.sub(r'\s+', ' ', t).strip()
    t = apply_pronunciation_library(t, engine_type="plain")
    return t

def build_speech_rhythm_segments(text: str) -> List[Dict[str, Any]]:
    """Splits narration into rate-controlled sentences (Item 148)."""
    clean_text = clean_narration_for_speech(text)
    clean_text = apply_pronunciation_library(clean_text, engine_type="plain")
    clean_text = re.sub(r'\((?:[^)]*(?:gül|kıkır|iç çek|nefes al|şaşır)[^)]*)\)', '', clean_text, flags=re.IGNORECASE)
    sentences = re.findall(r'[^.!?]+[.!?]+|[^.!?]+$', clean_text)
    segments = []
    for index, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue
        style = "question" if sentence.endswith("?") else "hook" if index == 0 else "body"
        segments.append({"text": sentence, "style": style, "rate": SPEECH_RHYTHM[style]})
    return segments

def extract_reaction_cues(text: str) -> List[str]:
    """Returns non-verbal editorial cues without sending parenthetical directions to TTS (Item 149)."""
    cues = []
    for instruction in re.findall(r'\(([^)]*)\)', text or ''):
        normalized = instruction.lower()
        if any(term in normalized for term in ("gül", "kıkır", "şaşır")):
            cues.append("chuckle")
        elif any(term in normalized for term in ("iç çek", "nefes al")):
            cues.append("sigh")
    return cues

def humanize_script_ssml(text: str, is_hook: bool = False, lang: str = "tr") -> str:
    """
    Modulates speaking rate and pitch using SSML prosody (Item 142).
    """
    clean = text.strip()
    
    if is_hook:
        rate = "+9%"
        pitch = "+2Hz"
    elif clean.endswith("?"):
        rate = "-4%"
        pitch = "+5Hz"
    else:
        rate = "+3%"
        pitch = "+0Hz"

    clean = re.sub(r'([,;])', r'\1 <break time="140ms"/>', clean)
    clean = re.sub(r'([.!?])', r'\1 <break time="260ms"/>', clean)

    ssml = f'<speak><prosody rate="{rate}" pitch="{pitch}">{clean}</prosody></speak>'
    return ssml

def synthesize_natural_pauses(text: str, engine_type: str = "ssml", break_ms: int = 150) -> str:
    """
    Item 93: Ses İçi Nefes ve Duraklama Sentezi.
    """
    if not text:
        return text

    clean_text = clean_narration_for_speech(text)

    if engine_type.lower() == "ssml":
        processed = re.sub(r'([,;:])\s*', rf'\1 <break time="{break_ms}ms"/> ', clean_text)
        processed = re.sub(r'([.!?])\s*', rf'\1 <break time="{int(break_ms * 1.6)}ms"/> ', processed)
        return processed.strip()
    else:
        processed = re.sub(r'([,;:])\s+', r'\1 ... ', clean_text)
        processed = re.sub(r'([.!?])\s+', r'\1 ... ', processed)
        processed = re.sub(r'\.{4,}', '...', processed)
        return processed.strip()

def get_asmr_voice_settings(niche_id: str, keyword: str) -> dict:
    """Returns Item 164's soft, stable settings for sleep-oriented narration."""
    text = f"{niche_id or ''} {keyword or ''}".casefold()
    is_asmr = any(cue in text for cue in ("uyku", "gece", "rahatla", "meditasyon", "masal", "asmr"))
    return {"enabled": is_asmr, "rate": "-12%" if is_asmr else None, "volume": 0.78 if is_asmr else 1.0}


# ─── ITEM 160: Doğal Duraklama (Micro-Pauses: 120ms / 280ms / 450ms) ──────────

def apply_micro_pauses(text: str,
                       comma_ms: int = 120,
                       dot_ms: int = 280,
                       question_ms: int = 350,
                       paragraph_ms: int = 450,
                       engine_type: str = "ssml") -> str:
    """
    Madde 160: Doğal Duraklama (Micro-Pauses).
    Virgüllerde 120ms, noktalarda 280ms, soru/ünlemlerde 350ms,
    paragraf geçişlerinde 450ms sessizlik konarak robotik akış kırılır.
    """
    if not text:
        return text

    # Paragrafları ayır (önce satır sonlarını yakala)
    raw_paragraphs = [p.strip() for p in re.split(r'\n{2,}|\r\n{2,}', text) if p.strip()]
    cleaned_paras = [clean_narration_for_speech(p) for p in raw_paragraphs]

    if engine_type.lower() == "ssml":
        processed_paras = []
        for p in cleaned_paras:
            # Soru ve ünlemler (350ms)
            p_sub = re.sub(r'([?!])\s*', rf'\1 <break time="{question_ms}ms"/> ', p)
            # Nokta (280ms)
            p_sub = re.sub(r'(\.)\s*', rf'\1 <break time="{dot_ms}ms"/> ', p_sub)
            # Virgül, iki nokta, noktalı virgül (120ms)
            p_sub = re.sub(r'([,;:])\s*', rf'\1 <break time="{comma_ms}ms"/> ', p_sub)
            processed_paras.append(p_sub.strip())

        result = f' <break time="{paragraph_ms}ms"/> '.join(processed_paras)
        return result.strip()
    else:
        # Plain text biçimi (üç noktalar ve boşluklar)
        processed_paras = []
        for p in cleaned_paras:
            p_sub = re.sub(r'([,;:])\s+', r'\1 , ', p)
            p_sub = re.sub(r'([?!])\s+', r'\1 ... ', p_sub)
            p_sub = re.sub(r'(\.)\s+', r'\1 .. ', p_sub)
            processed_paras.append(p_sub.strip())
        return ' ... \n\n '.join(processed_paras).strip()


# ─── ITEM 171: Metin Vurgularında Pitch Sıçraması (Pitch Jump on Emphasis) ────

EMPHASIS_KEYWORDS_TR = {
    "asla", "sakın", "aslında", "şok", "inanılmaz", "en büyük", "dikkat",
    "gerçek", "sırrı", "tehlike", "şaşırtıcı", "gizli", "korkunç", "ölümcül",
    "kesinlikle", "mutlaka", "kritik", "tarihi", "dönüm", "yasak"
}

EMPHASIS_KEYWORDS_EN = {
    "never", "secret", "truth", "shocking", "insane", "crucial", "hidden",
    "deadly", "danger", "actually", "warning", "must", "critical", "mystery"
}


def apply_emphasis_pitch_jumps(text: str,
                               engine_type: str = "ssml",
                               custom_keywords: Optional[List[str]] = None,
                               pitch_boost: str = "+12%") -> str:
    """
    Madde 171: Metin Vurgularında Pitch Sıçraması.
    Önemli bir kelime veya dramatik kavram söylenirken cümlenin o kelimesinde
    perde (pitch) hafif yukarı fırlatılır (+12% / +15Hz), böylece monotonluk kırılır
    ve kritik bilgi dinleyicinin bilincine doğrudan kazınır.
    """
    if not text:
        return text

    keywords = set(k.casefold() for k in (custom_keywords or []))
    keywords.update(EMPHASIS_KEYWORDS_TR)
    keywords.update(EMPHASIS_KEYWORDS_EN)

    if engine_type.lower() == "ssml":
        tokens = re.split(r'(\s+|[.,!?;:])', text)
        result_parts = []
        for token in tokens:
            cleaned_token = re.sub(r'[^\w]', '', token).casefold()
            is_uppercase = token.isupper() and len(token) > 1 and not token.startswith("<")
            if (cleaned_token in keywords or is_uppercase) and len(cleaned_token) > 1:
                result_parts.append(f'<prosody pitch="{pitch_boost}">{token}</prosody>')
            else:
                result_parts.append(token)
        return "".join(result_parts)
    else:
        # Plain text: Vurgulanacak kelimeleri belirginleştir (örn. tırnak veya ünlem vurgusu)
        tokens = re.split(r'(\s+|[.,!?;:])', text)
        result_parts = []
        for token in tokens:
            cleaned_token = re.sub(r'[^\w]', '', token).casefold()
            if cleaned_token in keywords and len(cleaned_token) > 1:
                result_parts.append(f'*{token}*')
            else:
                result_parts.append(token)
        return "".join(result_parts)


# ─── ITEM 175: Heyecanlı Cümlelerde Ses Hızlanması (Climax Acceleration) ──────

CLIMAX_TRIGGER_CUES = [
    "işte o an", "en kritik", "tam bu noktada", "ortaya çıktı", "şaşırtıcı gerçek",
    "büyük sır", "beklenmedik", "the truth is", "suddenly", "the twist", "unbelievable"
]


def apply_climax_tempo_curve(sentences_or_scenes: List[Any],
                             climax_index: Optional[int] = None,
                             peak_rate: str = "+15%",
                             buildup_rate: str = "+8%",
                             engine_type: str = "ssml") -> List[Dict[str, Any]]:
    """
    Madde 175: Heyecanlı Cümlelerde Ses Hızlanması.
    Hikayenin doruk (climax) noktasında ses hızı kademeli olarak %115'e (+15%) tırmanır.
    Doruk öncesi hazırlık %108, doruk anı %115, ardından kapanış/döngüde normal tempoya döner.
    """
    if not sentences_or_scenes:
        return []

    # Format standartlaştırma: String listesi veya dict listesi
    items = []
    for s in sentences_or_scenes:
        if isinstance(s, dict):
            items.append(dict(s))
        else:
            items.append({"text": str(s)})

    n = len(items)
    # Doruk indeksini tespit et: Belirtilmemişse anahtar kelimelere bak veya sondan 2. sahneyi seç
    if climax_index is None or climax_index < 0 or climax_index >= n:
        detected_idx = -1
        for idx, item in enumerate(items):
            txt = (item.get("text") or item.get("narration") or "").lower()
            if any(cue in txt for cue in CLIMAX_TRIGGER_CUES):
                detected_idx = idx
                break
        if detected_idx != -1:
            climax_index = detected_idx
        else:
            # Tipik 5-6 sahneli Shorts'ta doruk sahnesi %75-80 noktasındadır (örn. 4. sahne)
            climax_index = max(0, n - 2) if n > 2 else (n - 1)

    # Tempo eğrisini hesapla
    for idx, item in enumerate(items):
        txt = item.get("text") or item.get("narration") or ""
        if idx == climax_index:
            rate = peak_rate  # %115 doruk anı
            tempo_role = "climax_peak"
        elif idx == climax_index - 1 and idx >= 0:
            rate = buildup_rate  # %108 gerilim tırmanışı
            tempo_role = "climax_buildup"
        elif idx == 0:
            rate = "+9%"  # Kanca temposu
            tempo_role = "hook"
        else:
            rate = "+2%"  # Standart gövde temposu
            tempo_role = "body_resolution"

        item["prosody_rate"] = rate
        item["tempo_role"] = tempo_role

        if engine_type.lower() == "ssml":
            clean_txt = clean_narration_for_speech(txt)
            item["ssml_text"] = f'<speak><prosody rate="{rate}">{clean_txt}</prosody></speak>'

    return items


# ─── ITEM 177: Monolog Metin İçi Doğal Duraklama (Monologue Text Pauses) ──────

def inject_monologue_text_pauses(text: str,
                                 interval_words: int = 65,
                                 pause_ms: int = 450,
                                 engine_type: str = "ssml") -> str:
    """
    Madde 177: Uzun monologlarda yaklaşık her 40 saniyede bir (~65 kelime)
    doğal bir duraksama veya nefes/yutkunma boşluğu ekler.
    """
    if not text:
        return text

    words = text.split()
    if len(words) <= interval_words:
        return text

    output_words = []
    for i, word in enumerate(words, start=1):
        output_words.append(word)
        if i % interval_words == 0 and i < len(words):
            if engine_type.lower() == "ssml":
                output_words.append(f'<break time="{pause_ms}ms"/>')
            else:
                output_words.append("... [duraksama] ...")

    return " ".join(output_words)


# ─── ITEM 178: Soru Cümlesi Tonlaması (Question Pitch Inflection +5%) ─────────

def apply_question_pitch_inflection(text: str,
                                    pitch_boost: str = "+5%",
                                    engine_type: str = "ssml") -> str:
    """
    Madde 178: Soru Cümlesi Tonlaması.
    Soru cümlelerinin sonunda ses perdesi yukarı bükülmeli (pitch="+5%").
    İnsan konuşmasında sorular yükselen entonasyonla (rising intonation) biter;
    bu fonksiyon soru cümlelerini tespit edip perdesini +5% yukarı büker.
    """
    if not text:
        return text

    # Soru cümlelerini bul (cümle sonu soru işaretiyle biten kısımlar)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    processed = []

    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        if s_clean.endswith("?") or "?" in s_clean:
            if engine_type.lower() == "ssml":
                # Eğer zaten prosody etiketi varsa içindeki pitch'i güncelle veya sar
                if '<prosody' in s_clean:
                    s_clean = re.sub(r'pitch="[^"]+"', f'pitch="{pitch_boost}"', s_clean)
                else:
                    s_clean = f'<prosody pitch="{pitch_boost}">{s_clean}</prosody>'
            else:
                s_clean = f"{s_clean} (↑)"
        processed.append(s_clean)

    return " ".join(processed)


# ─── ITEM 179: Şok Efekti Anında Ses Kesintisi (Shock Silence Drop - 0.2s) ────

SHOCK_CUE_PHRASES = [
    "ama aslında", "ancak gerçek", "but the truth", "ve sonra", "birdenbire",
    "asıl şok edici olan", "the shocking truth", "hiç beklemediği", "korkunç gerçek"
]


def inject_shock_silence_ssml(text: str,
                              trigger_phrases: Optional[List[str]] = None,
                              silence_ms: int = 200) -> str:
    """
    Madde 179: Şok Efekti Anında Ses Kesintisi (SSML).
    Beklenmedik bir bilgi verildiğinde tam o ifadenin öncesine 0.2 saniyelik
    (200ms) mutlak sessizlik boşluğu ekler; izleyicinin dikkatini zirveye çıkarır.
    """
    if not text:
        return text

    triggers = trigger_phrases or SHOCK_CUE_PHRASES
    result = text

    for phrase in triggers:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        # Öncesine 200ms mutlak sessizlik molası ekle
        replacement = f'<break time="{silence_ms}ms"/> {phrase}'
        result = pattern.sub(replacement, result)

    return result

