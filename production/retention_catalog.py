"""Static hook/retention pattern catalogs and template generators for ViralRetentionEngine."""
from __future__ import annotations

import random
import re
from typing import Any, Dict, List

# Open conjunctions glued onto a finished line. They are not a sentence.
_OPEN_LOOP_TAIL_RE = re.compile(
    r"(?:\s+(?:çünkü|cunku|because|so|peki|ve tam da bu yüzden|işte bu sebeple|"
    r"and that is why|which is why|bu yüzden|bu sebeple))\s*$",
    re.IGNORECASE,
)


def _finish_spoken_line(text: str) -> str:
    """Return one finished sentence. Drop a dangling loop conjunction."""
    raw = (text or "").strip()
    raw = re.sub(r"\s*başa\s+dön\b[^.!?]*", "", raw, flags=re.IGNORECASE).strip()
    if not raw:
        return ""
    spoken = _OPEN_LOOP_TAIL_RE.sub("", raw).strip()
    spoken = re.sub(r"[\s,;:]+$", "", spoken)
    if not spoken:
        return ""
    if spoken[-1] not in ".!?":
        spoken += "."
    return spoken


def _clean_hook_topic(topic: str, lang: str = "tr") -> str:
    """Sanitize topic for mad-lib hook interpolation to avoid awkward sentence splices."""
    raw = (topic or "").strip().rstrip(".!?:;,")
    is_en = (lang or "tr").lower().startswith("en")
    if not raw:
        return "this topic" if is_en else "bu konu"
    words = raw.split()
    if len(words) <= 3:
        if is_en:
            return raw
        past_verbs = (
            "di", "dı", "du", "dü", "ti", "tı", "tu", "tü",
            "miş", "mış", "muş", "müş",
        )
        if not any(words[-1].lower().endswith(v) for v in past_verbs):
            return raw

    low = raw.lower()
    if any(k in low for k in ("yapay zeka", "ai", "chatgpt", "gemini", "claude")):
        return "artificial intelligence" if is_en else "yapay zeka"
    if any(k in low for k in ("yazılım", "kod", "programlama", "developer", "software", "code")):
        return "software" if is_en else "yazılım"
    if any(k in low for k in ("kripto", "bitcoin", "para", "borsa", "finans", "money", "crypto")):
        return "finance" if is_en else "finans"
    if any(k in low for k in ("psikoloji", "zihin", "mindset", "felsefe", "stoa")):
        return "mindset" if is_en else "psikoloji"

    return "this topic" if is_en else "bu konu"


TRIGGER_NAMES = [
    "Elon Musk", "Einstein", "Nikola Tesla", "Marcus Aurelius",
    "Steve Jobs", "Warren Buffett", "Napoleon", "Cleopatra",
]

LOOP_FORMULAS = [
    {
        "id": "cause_and_effect",
        "name": "Sebep & Sonuç Döngüsü",
        "ending_bridge": "...ve tam da bu yüzden asla unutmayın çünkü...",
        "hook_starter": "Marcus Aurelius'un bu kuralı hayatınızı baştan aşağı değiştiriyor.",
    },
    {
        "id": "reverse_question",
        "name": "Ters Soru Köprüsü",
        "ending_bridge": "...çünkü bu sırrı ilk duyduğunuzda başa dönüp diyeceksiniz ki...",
        "hook_starter": "Bunu öğrenene kadar zihniniz asla sizin kontrolünüzde değildi.",
    },
    {
        "id": "infinite_cycle",
        "name": "Evrensel Döngü",
        "ending_bridge": "...ve işte evrenin tam da bu döngüsü yüzünden her şey başa dönüyor:",
        "hook_starter": "Astrofizikçileri dehşete düşüren bu gerçeği çok az insan biliyor.",
    },
    {
        "id": "curiosity_repetition",
        "name": "Merak Tekrarı",
        "ending_bridge": "...peki sizce neden tarihteki en büyük liderlerin hepsi ilk kural olarak...",
        "hook_starter": "Günde sadece 10 dakikada zihinsel dayanıklılığınızı ikiye katlayabilirsiniz.",
    },
    {
        "id": "plot_twist_reset",
        "name": "Ters Köşe Sıfırlaması",
        "ending_bridge": "...ve işte tam da bu sebeple ilk duyduğunuzda inanmadığınız o şey...",
        "hook_starter": "İnsanların %95'i bu psikolojik tuzağa her gün bilmeden düşüyor.",
    },
    {
        "id": "warning_loop",
        "name": "Uyarı & İkaz Döngüsü",
        "ending_bridge": "...bu yüzden bir dahaki sefere birisi size yaklaştığında hemen hatırlayın:",
        "hook_starter": "Manipülasyon ustalarının kullandığı en tehlikeli 3 mikro beden dili hareketi.",
    },
    {
        "id": "time_reset",
        "name": "Zaman Tüneli Başa Sarma",
        "ending_bridge": "...ve zaman akıp geçerken fark edeceksiniz ki her şey tam burada başlamıştı:",
        "hook_starter": "Tarihin en gizemli 3 olayı hala mantıkla açıklanamıyor.",
    },
    {
        "id": "secret_knowledge",
        "name": "Gizli Bilgi Zinciri",
        "ending_bridge": "...ve kimsenin halka açıklamak istemediği o ilk soruya geri dönersek...",
        "hook_starter": "Finansal özgürlüğe ulaşanların sabah rutini sandığınız gibi değil.",
    },
    {
        "id": "challenge_accepted",
        "name": "Meydan Okuma Döngüsü",
        "ending_bridge": "...şimdi dürüstçe cevap verin, ilk saniyede gördüğünüz o detay...",
        "hook_starter": "Bu görsel bilmeceyi sadece IQ'su 125 üstü olanlar ilk bakışta çözebiliyor.",
    },
    {
        "id": "whisper_echo",
        "name": "Yankılanan Felsefe",
        "ending_bridge": "...bu kuralı unutanlar her zaman aynı hataya geri düşer, çünkü...",
        "hook_starter": "Epiktetos'un dediği gibi: Seni inciten olaylar değil, onlara yüklediğin anlamdır.",
    },
    {
        "id": "dialogue_restart",
        "name": "İç Ses Diyaloğu",
        "ending_bridge": "...kendinize her sorduğunuzda alacağınız tek bir gerçek cevap var:",
        "hook_starter": "Hiç kimse sana bu 3 karanlık gerçeği yüzüne karşı söylemeye cesaret edemez.",
    },
    {
        "id": "bizarre_fact_chain",
        "name": "Tuhaf Gerçekler Zinciri",
        "ending_bridge": "...ve işin en akıl almaz yanı, bütün bunların nedeni tam olarak şuydu:",
        "hook_starter": "Antik Roma'da insanların servet ödediği en tuhaf 3 çılgınlık.",
    },
]

PATTERN_INTERRUPTS = [
    {"type": "glitch_flash", "label": "0.1s Glitch & Beyaz Işık Patlaması"},
    {"type": "zoom_punch", "label": "1.2x Hızlı Kamera Yaklaşması (Scale Punch)"},
    {"type": "color_inversion", "label": "0.15s Siyah-Beyaz Renk Negatifi"},
    {"type": "warning_badge", "label": "Üst Ekranda '⚠️ ASLA BUNU YAPMAYIN' Sabit Kanca Çubuğu"},
]

SUBCONSCIOUS_PALETTES = {
    "danger_mystery": {
        "primary": "#FF0033", "secondary": "#0A0A0A", "accent": "#FFE600",
        "description": "Tehlike, gizem ve şok edici gerçekler için retinal uyarıcı kontrast.",
    },
    "wealth_success": {
        "primary": "#00E676", "secondary": "#FFD700", "accent": "#0D1B2A",
        "description": "Zenginlik, finans, para ve başarı psikolojisi.",
    },
    "stoic_philosophy": {
        "primary": "#E0E1DD", "secondary": "#0D1B2A", "accent": "#778DA9",
        "description": "Sakinlik, felsefi bilgelik, kadim güç ve derin düşünce.",
    },
    "cyber_tech": {
        "primary": "#00F5D4", "secondary": "#7B2CBF", "accent": "#F72585",
        "description": "Yapay zeka, teknoloji, gelecek ve bilimsel buluşlar.",
    },
}

DIVERSE_LOOP_CONJUNCTIONS_EN = [
    "...and that is exactly why you must never forget that",
    "...because the moment you hear this truth, you will realize that",
    "...and this infinite loop of the universe is why it always begins with:",
    "...so why do the greatest minds always start with this exact rule?",
    "...and this is the hidden reason nobody believed at first that",
    "...so next time you face this, remember the opening lesson:",
    "...and as time moves forward, you discover everything started right here:",
    "...which brings us right back to the question everyone avoids:",
    "...now be honest: that first detail you noticed on the screen,",
    "...forgetting this rule always brings you back to the start, because",
    "...ask yourself this question, and the only true answer is:",
    "...and the most unbelievable part is that the reason was right at the beginning:",
]

DIVERSE_LOOP_CONJUNCTIONS_TR = [
    "...ve tam da bu yüzden asla unutmayın çünkü",
    "...çünkü bu sırrı ilk duyduğunuzda başa dönüp diyeceksiniz ki",
    "...ve işte evrenin tam da bu döngüsü yüzünden her şey başa dönüyor:",
    "...peki sizce neden tarihteki en büyük liderlerin hepsi ilk kural olarak",
    "...ve işte tam da bu sebeple ilk duyduğunuzda inanmadığınız o şey",
    "...bu yüzden bir dahaki sefere birisi size yaklaştığında hemen hatırlayın:",
    "...ve zaman akıp geçerken fark edeceksiniz ki her şey tam burada başlamıştı:",
    "...ve kimsenin halka açıklamak istemediği o ilk soruya geri dönersek",
    "...şimdi dürüstçe cevap verin, ilk saniyede gördüğünüz o detay",
    "...bu kuralı unutanlar her zaman aynı hataya geri düşer, çünkü",
    "...kendinize her sorduğunuzda alacağınız tek bir gerçek cevap var:",
    "...ve işin en akıl almaz yanı, bütün bunların nedeni tam olarak şuydu:",
]


def generate_polarizing_dilemma(topic: str, lang: str = "tr") -> Dict[str, str]:
    """Item 210: Polarize Edici Soru (İzleyiciyi İkiye Bölme & Yorum Savaşı)."""
    t_low = (topic or "").lower()
    is_en = (lang or "tr").lower().startswith("en")
    is_tech = any(k in t_low for k in ("yapay zeka", "ai", "yazılım", "kod", "teknoloji", "tech", "site", "bot", "tool"))
    is_money = any(k in t_low for k in ("para", "zengin", "milyon", "dolar", "finans", "money", "rich", "wealth", "crypto", "kripto"))

    if is_en:
        if is_tech:
            dilemmas = [
                {"question": "Should advanced AI tools remain open to everyone, or strictly regulated by governments?", "choice_a": "Open to Everyone", "choice_b": "Strict Regulation"},
                {"question": "Will AI eventually replace human creators, or amplify them 10x?", "choice_a": "Replace Humans", "choice_b": "Amplify Creators"},
            ]
        elif is_money:
            dilemmas = [
                {"question": "Would you choose $10 Million right now, or guaranteed $50K passive income every month forever?", "choice_a": "$10 Million Cash", "choice_b": "$50K Monthly Forever"},
            ]
        else:
            clean = _clean_hook_topic(topic, lang="en")
            ref = f"When facing {clean}" if clean != "this topic" else "In this situation"
            dilemmas = [
                {"question": f"{ref}: Would you choose brutal truth or peaceful ignorance?", "choice_a": "Brutal Truth", "choice_b": "Peaceful Ignorance"},
                {"question": f"{ref}: Complete security with zero choices, or total freedom with zero safety?", "choice_a": "Total Freedom", "choice_b": "Complete Security"},
            ]
    else:
        if is_tech:
            dilemmas = [
                {"question": "Gelişmiş yapay zeka araçları tamamen serbest mi bırakılmalı, yoksa devletler tarafından sıkı denetlenmeli mi?", "choice_a": "Tamamen Serbest", "choice_b": "Sıkı Denetim"},
                {"question": "Yapay zeka gelecekte insan üretkenliğini katlayacak mı, yoksa meslekleri tamamen yok mu edecek?", "choice_a": "Üretkenliği Katlayacak", "choice_b": "Meslekleri Yok Edecek"},
            ]
        elif is_money:
            dilemmas = [
                {"question": "Hemen şimdi 10 Milyon Lira nakit mi, yoksa ömür boyu her ay garantili 100.000 Lira pasif gelir mi?", "choice_a": "10 Milyon Nakit", "choice_b": "Aylık 100 Bin Lira"},
            ]
        else:
            clean = _clean_hook_topic(topic, lang="tr")
            ref = f"{clean} konusunda sizce hangisi" if clean != "bu konu" else "Siz olsaydınız hangisini seçerdiniz"
            dilemmas = [
                {"question": f"{ref}: Acımasız gerçekler mi, yoksa huzurlu bir yanılsama mı?", "choice_a": "Acımasız Gerçekler", "choice_b": "Huzurlu Yanılsama"},
                {"question": f"{ref}: Sıfır riskli sıradan bir hayat mı, yoksa büyük belirsizliklerle dolu büyük başarı mı?", "choice_a": "Sıfır Risk", "choice_b": "Büyük Başarı"},
            ]
    return random.choice(dilemmas)


def generate_fomo_forbidden_knowledge_hook(topic: str, category: str = "fomo", lang: str = "tr") -> str:
    """Items 218, 219, 220: FOMO, Yasak Meyve & Sosyal Kanıt Kancaları."""
    t = _clean_hook_topic(topic, lang=lang)
    if lang == "en":
        if category == "forbidden":
            return f"3 dark principles of {t} that psychologists warn people never to reveal publicly."
        if category == "social_proof":
            return f"The hidden daily habit about {t} practiced exclusively by the top 0.1% achievers."
        return f"99% of people will fail at {t} because nobody explained this single hidden rule."
    if category == "forbidden":
        return f"{t} konusunda uzmanların halka açıklanmasını istemediği 3 karanlık kural."
    if category == "social_proof":
        return f"Dünyanın en başarılı insanlarının {t} konusunda her gün uyguladığı gizli rutin."
    return f"İnsanların %99'u {t} konusunda bu kuralı bilmediği için kaybediyor."


def generate_challenge_hook(topic: str, lang: str = "tr") -> str:
    """Item 228 & 268: Kullanıcıyı Harekete Geçiren Meydan Okuma & Zaman Baskısı."""
    t = _clean_hook_topic(topic, lang=lang)
    if lang == "en":
        return f"Only people with an IQ above 125 can solve this {t} puzzle on their first try: You have 5 seconds!"
    return f"Bu {t} bilmecesini sadece IQ'su 125 üstü olanlar ilk bakışta çözebiliyor: Cevap için sadece 5 saniyen var!"


def generate_role_play_hook(topic: str, lang: str = "tr") -> str:
    """Item 257: İzleyiciye Rol Biçme — dedektif / karar verici interaktif kanca."""
    t_low = (topic or "").lower()
    is_en = (lang or "tr").lower().startswith("en")
    is_tech = any(k in t_low for k in ("yapay zeka", "ai", "yazılım", "kod", "teknoloji", "tech", "site", "bot", "tool"))

    if is_tech:
        if is_en:
            return "You are the lead engineer and this system is in your hands. Which protocol do you deploy first?"
        return "Sen bir yapay zeka mühendisisin ve sistem kontrolden çıkmak üzere. İlk hangi protokolü devreye sokardın?"

    clean = (topic or "").strip().rstrip(".!?:;,")
    words = clean.split()
    past_verbs = ("di", "dı", "du", "dü", "ti", "tı", "tu", "tü", "miş", "mış")
    if len(words) > 4 or any(words[-1].lower().endswith(suffix) for suffix in past_verbs):
        clean_tr, clean_en = "bu gizemli olay", "this mystery"
    else:
        clean_tr, clean_en = clean, clean

    if is_en:
        return f"You are the detective on this {clean_en} case — three suspects, one truth. Which clue do you trust first?"
    return f"Sen bir dedektifsin ve {clean_tr} dosyasında önünde 3 şüpheli var. İlk hangi ipucuna güvenerdin?"


def generate_curiosity_gap_hook(topic: str, lang: str = "tr") -> str:
    """Plan 7.1: withheld rule."""
    t = _clean_hook_topic(topic, lang=lang)
    if lang == "en":
        hooks = [
            f"The one rule about {t} that nobody says out loud.",
            f"Do not decide on {t} before this missing piece.",
            f"The real part of {t} is still ahead. Do not scroll.",
        ]
    else:
        hooks = [
            f"Kimsenin {t} hakkında söylemediği o tek kural.",
            f"Bunu bilmeden {t} hakkında karar vermeyin.",
            f"{t} ile ilgili asıl parça daha gelmedi. Kaydırmayın.",
        ]
    return random.choice(hooks)


def generate_problem_agitation_hook(topic: str, lang: str = "tr") -> str:
    """Plan 7.1: the symptom is real, the assumed cause is not."""
    t = _clean_hook_topic(topic, lang=lang)
    if lang == "en":
        hooks = [
            f"If {t} keeps wearing you down, the cause is not what you think.",
            f"You have been fixing {t} in the wrong place.",
            f"The reason {t} keeps returning is the habit everyone repeats.",
        ]
    else:
        hooks = [
            f"{t} sizi yoruyorsa sebep düşündüğünüz şey değil.",
            f"{t} sorununu yanlış yerde arıyorsunuz.",
            f"{t} neden dönüp duruyor? Herkesin tekrarladığı o alışkanlık.",
        ]
    return random.choice(hooks)


def generate_shocking_statistic_hook(topic: str, lang: str = "tr") -> str:
    """Item 259: Şok Edici İstatistik Kancası."""
    t = _clean_hook_topic(topic, lang=lang)
    if lang == "en":
        templates = [
            f"Only 0.1% of the world's population shares this rare trait linked to {t}.",
            f"A Harvard study found that 97% of people get {t} completely wrong on the first try.",
            f"Less than 1 in 1,000 people know this hidden statistic about {t}.",
        ]
    else:
        templates = [
            f"İnsanların %99'u {t} konusunda bunu bilmeden devam ediyor.",
            f"Dünya nüfusunun sadece %0.1'inin sahip olduğu o nadir özellik {t} ile bağlantılı.",
            f"1.000 kişiden sadece 1'i {t} hakkında bu gizli istatistiği biliyor.",
        ]
    return random.choice(templates)


def generate_counter_intuitive_hook(topic: str, lang: str = "tr") -> str:
    """Item 263: İzleyiciye Ters Köşe Yapma."""
    t = _clean_hook_topic(topic, lang=lang)
    if lang == "en":
        templates = [
            f"Everyone says {t} works one way — but a Harvard study showed the exact opposite.",
            f"The popular belief about {t} sounds logical, until you see what the data actually says.",
            f"You were taught {t} helps you win — research says it quietly does the reverse.",
        ]
    else:
        templates = [
            f"Herkes {t} konusunda aynı şeyi söyler, ancak Harvard araştırması tam tersini gösterdi.",
            f"{t} hakkında duyduğunuz popüler inanç mantıklı görünür — ta ki veriler ortaya çıkana kadar.",
            f"Size {t} size kazandırır denildi; araştırmalar sessizce tam tersini söylüyor.",
        ]
    return random.choice(templates)


def get_sticky_hook_banner(topic: str, mood: str = "warning", lang: str = "tr") -> str:
    """Item 232: Ekranın Üst Kısmına Sabit Kanca Yazısı (Sticky Top Hook Banner)."""
    banners = {
        "warning": "⚠️ ASLA BUNU YAPMAYIN" if lang == "tr" else "⚠️ NEVER DO THIS",
        "secret": "🚨 SAKLANAN GERÇEK" if lang == "tr" else "🚨 HIDDEN REALITY",
        "mindset": "🧠 ZİHNİNİ YÖNETEN KURAL" if lang == "tr" else "🧠 MASTER YOUR MIND",
        "money": "💰 %1'LİK DİLİMİN SIRRI" if lang == "tr" else "💰 SECRET OF THE TOP 1%",
    }
    return banners.get(mood, banners["warning"])


def generate_acoustic_curiosity_hook(topic: str, lang: str = "tr") -> str:
    """Item 233: Merak Uyandıran Ses Sorusu."""
    t = _clean_hook_topic(topic, lang=lang)
    if lang == "en":
        return f"Do you hear that sound? That subtle signal about {t} is the first clue nobody talks about..."
    return f"Şu sesi duyuyor musunuz? {t} hakkında kimsenin bahsetmediği o ipucu tam da bu sesten geliyor..."


def generate_share_cta(topic: str = "", lang: str = "tr") -> str:
    """Item 235: Paylaşma Güdüsü Tetikleme."""
    if (lang or "tr").lower().startswith("en"):
        return "Send this video right now to that one friend who needs to hear this."
    if "stres" in (topic or "").lower():
        return "Bu videoyu hayatında çok stres olan o arkadaşına hemen gönder."
    return "Bu videoyu görmesi gereken o arkadaşına hemen gönder."


def generate_bookmark_cta(topic: str = "", lang: str = "tr") -> str:
    """Item 236: Kaydetme (Bookmark) Güdüsü."""
    if (lang or "tr").lower().startswith("en"):
        return "Save this video now so you never forget this list."
    t_clean = (topic or "").strip()
    words = t_clean.split()
    past_verbs = ("di", "dı", "du", "dü", "ti", "tı", "tu", "tü", "miş", "mış")
    if words and len(words) <= 3 and not any(words[-1].lower().endswith(suffix) for suffix in past_verbs):
        return f"Bu {t_clean} listesini unutmamak için videoyu hemen kaydet."
    return "Bu listeyi unutmamak için videoyu hemen kaydet."


def generate_community_follow_cta(topic: str = "", lang: str = "tr") -> str:
    """Item 270: Topluluk Hissi — aile / günlük bilgi takip CTA."""
    if lang == "en":
        base = "Join our community and learn one new insight every day — follow now."
        return f"{base} Today's focus: {topic}." if topic else base
    base = "Ailemize katılmak ve her gün 1 yeni bilgi öğrenmek için takip et."
    return f"{base} Bugünkü konu: {topic}." if topic else base


def generate_plot_twist_closing(topic: str, lang: str = "tr") -> str:
    """Item 239: Sürpriz Kapanış (Plot Twist)."""
    t = _clean_hook_topic(topic, lang=lang)
    if lang == "en":
        twists = [
            f"And the real twist about {t}? Everything you assumed at the start was backwards.",
            f"Plot twist: the villain in {t} wasn't who you thought — it was the obvious answer all along.",
        ]
    else:
        twists = [
            f"Ve {t} konusundaki asıl sürpriz? Başta sandığınız her şey tam tersiydi.",
            f"Ters köşe: {t} hikayesindeki asıl suçlu sandığınız kişi değildi — ipucu en baştaydı.",
        ]
    return random.choice(twists)


def generate_pinned_comment_bait(topic: str, lang: str = "tr") -> Dict[str, str]:
    """Items 234 & 269: Yorumlarda Cevap Arama Tuzağı & Yorum Sabitleme Kancası."""
    clean = (topic or "").strip().rstrip(".!?:;,")
    words = clean.split()
    past_verbs = ("di", "dı", "du", "dü", "ti", "tı", "tu", "tü", "miş", "mış")
    if len(words) > 4 or any(words[-1].lower().endswith(suffix) for suffix in past_verbs):
        tr_topic, en_topic = "Bu video", "this video"
    else:
        tr_topic, en_topic = f"{clean} konusu", clean

    if (lang or "tr").lower().startswith("en"):
        return {
            "video_cta": "I pinned the surprising answer in the comments, let's see who guessed it first!",
            "pinned_comment": f"The hidden detail about {en_topic} is revealed here! The most creative reply will get pinned.",
        }
    return {
        "video_cta": "Cevabı yorumlara sabitledim, bakalım doğru tahmin edebilecek misiniz?",
        "pinned_comment": (
            f"{tr_topic}ndaki en şaşırtıcı detay burada! En yaratıcı cevabı veren ilk 3 kişiyi sabitliyorum."
            if tr_topic == "Bu video"
            else f"{clean} konusundaki en şaşırtıcı detay burada! En yaratıcı cevabı veren ilk 3 kişiyi sabitliyorum."
        ),
    }


def format_numbered_rule_hierarchy(rules: List[str], lang: str = "tr") -> List[Dict[str, Any]]:
    """Item 241: Numaralandırılmış Madde Hiyerarşisi."""
    formatted = []
    total = len(rules)
    for idx, rule in enumerate(rules):
        num = idx + 1
        if num == total and total > 1:
            prefix = f"Ve en tehlikelisi Kural {num}:" if lang == "tr" else f"And the most dangerous, Rule {num}:"
        else:
            prefix = f"Kural {num}:" if lang == "tr" else f"Rule {num}:"
        formatted.append({
            "rule_number": num,
            "prefix": prefix,
            "text": rule.strip(),
            "full_narration": f"{prefix} {rule.strip()}",
        })
    return formatted


def generate_narrow_audience_hook(topic: str = "", year: int = 2026, lang: str = "tr") -> str:
    """Item 244: Hedef Kitleyi Daraltma İllüzyonu."""
    if lang == "en":
        base = f"Only people who want financial freedom in {year} should keep watching this video."
        return f"{base} Everyone else, scroll away." if not topic else f"{base} This is about {topic}."
    base = f"Sadece {year}'da finansal özgürlük isteyenler bu videoda kalsın."
    return f"{base} Geri kalanlar kaydırabilir." if not topic else f"{base} Konu: {topic}."


def generate_single_sentence_identity_hook(topic: str = "", lang: str = "tr") -> str:
    """Item 334: Tek Cümlelik Kanca."""
    hooks_tr = [
        "Bu videoyu izlemeyi bitirdiğinde artık aynı insan olmayacaksın.",
        f"{topic} hakkında duyacağın tek cümle hayatını sonsuza dek değiştirecek." if topic else
        "Hayatını değiştirecek tek cümle 3 saniye içinde geliyor.",
        "Bu 45 saniyeden sonra dünyaya bakış açın bir daha eskisi gibi olmayacak.",
    ]
    hooks_en = [
        "When you finish this video, you won't be the same person anymore.",
        f"The one sentence about {topic} will permanently shift how you see everything." if topic else
        "One sentence in the next 3 seconds will change you forever.",
    ]
    return random.choice(hooks_en if lang == "en" else hooks_tr)


def generate_emotional_bond_hook(lang: str = "tr") -> str:
    """Item 248: Duygusal Bağ Kanca Cümlesi."""
    hooks_tr = [
        "Kendinizi bazen tüm dünyaya karşı yapayalnız hissettiğiniz oldu mu?",
        "Hiç kimse seni gerçekten anlamıyormuş gibi hissettiğin bir an oldu mu?",
        "En kalabalık odada bile yalnız kalmış gibi hissettin mi hiç?",
    ]
    hooks_en = [
        "Have you ever felt completely alone against the whole world?",
        "Was there a moment when nobody seemed to truly understand you?",
    ]
    return random.choice(hooks_en if lang == "en" else hooks_tr)


def generate_spotted_mistake_bait(topic: str) -> str:
    """Generates subtle engagement bait / spotted mistake to trigger comment fights (Item 209)."""
    t_low = (topic or "").lower()
    if any(w in t_low for w in ("kural", "yasa", "stoa", "prensip", "ilke")):
        baits = [
            "İpucu: 3. kuralın mantığına dikkat edenler yorumlarda buluşuyor 👇",
            "Sizce hangi kural hayatınızı daha hızlı değiştirebilir? Yorumlarda tartışalım.",
            "Not: Bahsedilen maddelerden en zoru hangisi? Cevapları bekliyorum 👀",
        ]
    elif any(w in t_low for w in ("gizem", "bilim", "olay", "uzay", "tarih", "sır", "gerçek", "keşif")):
        baits = [
            "Sizce bu olaylardan hangisinin açıklaması hala insanlıktan gizleniyor? 👇",
            "Not: 2. maddedeki gizemli detayı fark edenler yorumlara yazsın 👀",
            "Bu teorilerden hangisi size daha inandırıcı geldi? Yorumlarda buluşalım 👇",
        ]
    elif any(w in t_low for w in ("ürün", "alet", "cihaz", "para", "finans", "satın")):
        baits = [
            "Siz olsaydınız bu listeden ilk hangisini denerdiniz? 👇",
            "Fiyat/performans açısından sizce hangisi 1 numara? Yorumlara bekliyorum.",
        ]
    else:
        baits = [
            "Not: Videodaki en şaşırtıcı detayı sadece dikkatli izleyiciler fark eder 👀",
            "Sizce listedeki en inanılmaz bilgi hangisiydi? Tartışma başladı 👇",
            "Bu bilgiyi ilk kez duyanlar kaç kişi? Sayımızı görelim 👇",
        ]
    return random.choice(baits)
