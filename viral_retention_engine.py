"""
Viral Retention, Psychological Hooks & Loop Matrix Engine
Implements Items 201 - 275 of the 500-Item YouTube Shorts Automation Roadmap.
Covers:
- 12 Seamless Infinite Loop (Döngü Köprüsü) Formulas (Items 137, 204)
- Cognitive Dissonance & Zeigarnik Hooks (Items 202, 203)
- First 1.5s Pattern Interrupt Triggers (Items 201, 237)
- Bionic Reading / High-Speed Word Formatter (Item 215)
- Controversial Question, Spotted Mistake Bait & Polarizing Dilemma (Items 209, 210)
- FOMO, Forbidden Knowledge & Social Proof Hooks (Items 218, 219, 220)
- Interactive Challenge & Countdown Hook (Items 228, 268)
- Sticky Top Hook Banner (Item 232)
- Pinned Comment Bait Generator (Items 234, 269)
- Numbered Rule Hierarchy Formatter (Item 241)
- Subconscious Color Psychology Palettes (Item 249)
- Subtitle Safe Zone & Eye-Tracking Coordinates (Items 206, 265)
- Cadence Acceleration Curve (Item 266)
- 45s Shorts Story Arc Breakdown (Item 274)
- Retention Audit Scoring (0 - 100) (Item 275)
"""

import random
from typing import Dict, List, Any


class ViralRetentionEngine:
    """Calculates and enhances video retention psychology for Shorts."""

    # 12 Distinct Loop Formulas (Item 204 & 137)
    LOOP_FORMULAS = [
        {
            "id": "cause_and_effect",
            "name": "Sebep & Sonuç Döngüsü",
            "ending_bridge": "...ve tam da bu yüzden asla unutmayın çünkü...",
            "hook_starter": "Marcus Aurelius'un bu kuralı hayatınızı baştan aşağı değiştiriyor."
        },
        {
            "id": "reverse_question",
            "name": "Ters Soru Köprüsü",
            "ending_bridge": "...çünkü bu sırrı ilk duyduğunuzda başa dönüp diyeceksiniz ki...",
            "hook_starter": "Bunu öğrenene kadar zihniniz asla sizin kontrolünüzde değildi."
        },
        {
            "id": "infinite_cycle",
            "name": "Evrensel Döngü",
            "ending_bridge": "...ve işte evrenin tam da bu döngüsü yüzünden her şey başa dönüyor:",
            "hook_starter": "Astrofizikçileri dehşete düşüren bu gerçeği çok az insan biliyor."
        },
        {
            "id": "curiosity_repetition",
            "name": "Merak Tekrarı",
            "ending_bridge": "...peki sizce neden tarihteki en büyük liderlerin hepsi ilk kural olarak...",
            "hook_starter": "Günde sadece 10 dakikada zihinsel dayanıklılığınızı ikiye katlayabilirsiniz."
        },
        {
            "id": "plot_twist_reset",
            "name": "Ters Köşe Sıfırlaması",
            "ending_bridge": "...ve işte tam da bu sebeple ilk duyduğunuzda inanmadığınız o şey...",
            "hook_starter": "İnsanların %95'i bu psikolojik tuzağa her gün bilmeden düşüyor."
        },
        {
            "id": "warning_loop",
            "name": "Uyarı & İkaz Döngüsü",
            "ending_bridge": "...bu yüzden bir dahaki sefere birisi size yaklaştığında hemen hatırlayın:",
            "hook_starter": "Manipülasyon ustalarının kullandığı en tehlikeli 3 mikro beden dili hareketi."
        },
        {
            "id": "time_reset",
            "name": "Zaman Tüneli Başa Sarma",
            "ending_bridge": "...ve zaman akıp geçerken fark edeceksiniz ki her şey tam burada başlamıştı:",
            "hook_starter": "Tarihin en gizemli 3 olayı hala mantıkla açıklanamıyor."
        },
        {
            "id": "secret_knowledge",
            "name": "Gizli Bilgi Zinciri",
            "ending_bridge": "...ve kimsenin halka açıklamak istemediği o ilk soruya geri dönersek...",
            "hook_starter": "Finansal özgürlüğe ulaşanların sabah rutini sandığınız gibi değil."
        },
        {
            "id": "challenge_accepted",
            "name": "Meydan Okuma Döngüsü",
            "ending_bridge": "...şimdi dürüstçe cevap verin, ilk saniyede gördüğünüz o detay...",
            "hook_starter": "Bu görsel bilmeceyi sadece IQ'su 125 üstü olanlar ilk bakışta çözebiliyor."
        },
        {
            "id": "whisper_echo",
            "name": "Yankılanan Felsefe",
            "ending_bridge": "...bu kuralı unutanlar her zaman aynı hataya geri düşer, çünkü...",
            "hook_starter": "Epiktetos'un dediği gibi: Seni inciten olaylar değil, onlara yüklediğin anlamdır."
        },
        {
            "id": "dialogue_restart",
            "name": "İç Ses Diyaloğu",
            "ending_bridge": "...kendinize her sorduğunuzda alacağınız tek bir gerçek cevap var:",
            "hook_starter": "Hiç kimse sana bu 3 karanlık gerçeği yüzüne karşı söylemeye cesaret edemez."
        },
        {
            "id": "bizarre_fact_chain",
            "name": "Tuhaf Gerçekler Zinciri",
            "ending_bridge": "...ve işin en akıl almaz yanı, bütün bunların nedeni tam olarak şuydu:",
            "hook_starter": "Antik Roma'da insanların servet ödediği en tuhaf 3 çılgınlık."
        }
    ]

    # Pattern Interrupt Triggers (Items 201, 237)
    PATTERN_INTERRUPTS = [
        {"type": "glitch_flash", "label": "0.1s Glitch & Beyaz Işık Patlaması"},
        {"type": "zoom_punch", "label": "1.2x Hızlı Kamera Yaklaşması (Scale Punch)"},
        {"type": "color_inversion", "label": "0.15s Siyah-Beyaz Renk Negatifi"},
        {"type": "warning_badge", "label": "Üst Ekranda '⚠️ ASLA BUNU YAPMAYIN' Sabit Kanca Çubuğu"}
    ]

    # Subconscious Color Psychology Palettes (Item 249)
    SUBCONSCIOUS_PALETTES = {
        "danger_mystery": {
            "primary": "#FF0033",      # Neon Red
            "secondary": "#0A0A0A",    # Pitch Black
            "accent": "#FFE600",       # Warning Yellow
            "description": "Tehlike, gizem ve şok edici gerçekler için retinal uyarıcı kontrast."
        },
        "wealth_success": {
            "primary": "#00E676",      # Emerald Green
            "secondary": "#FFD700",    # Imperial Gold
            "accent": "#0D1B2A",       # Deep Obsidian
            "description": "Zenginlik, finans, para ve başarı psikolojisi."
        },
        "stoic_philosophy": {
            "primary": "#E0E1DD",      # Marble White
            "secondary": "#0D1B2A",    # Dark Navy
            "accent": "#778DA9",       # Roman Steel
            "description": "Sakinlik, felsefi bilgelik, kadim güç ve derin düşünce."
        },
        "cyber_tech": {
            "primary": "#00F5D4",      # Cyber Cyan
            "secondary": "#7B2CBF",    # Deep Purple
            "accent": "#F72585",       # Neon Pink
            "description": "Yapay zeka, teknoloji, gelecek ve bilimsel buluşlar."
        }
    }

    @classmethod
    def get_loop_formula(cls, formula_id: str = None) -> Dict[str, str]:
        """Returns a selected loop formula or a random one (Item 204 & 137)."""
        if formula_id:
            for f in cls.LOOP_FORMULAS:
                if f["id"] == formula_id:
                    return f
        return random.choice(cls.LOOP_FORMULAS)

    @classmethod
    def get_diverse_loop_conjunctions(cls, min_count: int = 10) -> List[str]:
        """
        Item 137: Döngü Cümlesi Çeşitliliği.
        Her videoda aynı döngü bağlacı ('çünkü...') kullanılmamalı,
        en az 10 farklı bağlaç havuzdan çekilmeli ve sırayla çeşitlendirilmelidir.
        """
        conjunctions = [
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
            "...ve işin en akıl almaz yanı, bütün bunların nedeni tam olarak şuydu:"
        ]
        return conjunctions[:max(min_count, len(conjunctions))]

    @classmethod
    def pick_loop_bridge_for_video(cls, video_index: int = 0) -> str:
        """Item 137: Videoya özel döngüsel bağlaç seçer."""
        pool = cls.get_diverse_loop_conjunctions()
        return pool[video_index % len(pool)]

    @classmethod
    def generate_cognitive_dissonance_hook(cls, topic: str, lang: str = "tr") -> str:
        """
        Item 202: Bilişsel Çelişki Kancası (Cognitive Dissonance Hook).
        Kabul görmüş inancı veya alışılmış düşünceyi sarsan güçlü açılış cümlesi üretir.
        """
        if lang == "en":
            hooks = [
                f"Until you learn this about {topic}, your mind was never truly under your control.",
                f"Everything you've been taught about {topic} is deliberately backwards.",
                f"What if I told you the truth about {topic} is the exact opposite of what you believe?",
                f"You think you understand {topic}, but 99% of people fall for this exact cognitive trap."
            ]
        else:
            hooks = [
                f"Bunu öğrenene kadar {topic} konusunda bildiğiniz her şey sadece bir yanılsamaydı.",
                f"Çoğu insan {topic} hakkında tamamen yanılıyor ve bu hata her gün tekrarlanıyor.",
                f"{topic} hakkında size bugüne kadar anlatılanların tam tersi doğru olsaydı ne yapardınız?",
                f"Bunu bilmeden geçen her gün, {topic} tuzağına biraz daha çekiliyorsunuz."
            ]
        return random.choice(hooks)

    @classmethod
    def generate_zeigarnik_hook(cls, topic: str, total_points: int = 3, lang: str = "tr") -> str:
        """
        Item 203: Zeigarnik Etkisi (Tamamlanmamışlık Hissi).
        İzleyicide zihinsel bir açık döngü yaratarak sonuna kadar izletir.
        """
        if lang == "en":
            return f"By the end of this video, you will uncover rule #{total_points} that completely changes everything, but first..."
        return f"Bu videonun sonunda hayatınızı değiştirecek o {total_points}. kuralı duyacaksınız, ama önce..."

    @classmethod
    def get_subtitles_safe_zone(cls, screen_height: int = 1920, screen_width: int = 1080) -> Dict[str, Any]:
        """
        Items 206 & 265: Göz Bebeği Takip Noktası (Eye-Tracking Center) & Güvenli Alan (Safe Zone).
        YouTube Shorts UI elemanları (başlık, beğeni butonu, açıklama) ile çakışmayan
        ve gözün odaklandığı dikey alanı (%40-%60 aralığı, alttan en az %25 yukarıda) hesaplar.
        """
        bottom_ui_margin = int(screen_height * 0.25)       # Alttan 480px boşluk
        top_ui_margin = int(screen_height * 0.15)          # Üstten 288px boşluk
        eye_tracking_y_min = int(screen_height * 0.40)     # 768px
        eye_tracking_y_max = int(screen_height * 0.60)     # 1152px
        optimal_subtitle_y = int(screen_height * 0.52)     # 998px

        return {
            "screen_width": screen_width,
            "screen_height": screen_height,
            "bottom_ui_margin": bottom_ui_margin,
            "top_ui_margin": top_ui_margin,
            "eye_tracking_y_range": [eye_tracking_y_min, eye_tracking_y_max],
            "optimal_subtitle_y": optimal_subtitle_y,
            "max_words_per_frame": 4,                     # Item 205: Ekranda Maksimum 3-4 Kelime
            "safe_zone_verified": True
        }

    @classmethod
    def generate_polarizing_dilemma(cls, topic: str, lang: str = "tr") -> Dict[str, str]:
        """
        Item 210: Polarize Edici Soru (İzleyiciyi İkiye Bölme & Yorum Savaşı).
        """
        if lang == "en":
            dilemmas = [
                {
                    "question": f"When facing {topic}, would you choose 10 Million Dollars or turning back time 10 years?",
                    "choice_a": "10 Million Dollars",
                    "choice_b": "10 Years Back"
                },
                {
                    "question": f"Regarding {topic}: Absolute freedom with zero certainty, or complete security with zero choices?",
                    "choice_a": "Absolute Freedom",
                    "choice_b": "Complete Security"
                }
            ]
        else:
            dilemmas = [
                {
                    "question": f"{topic} konusunda siz olsaydınız: 10 Milyon Lira mı, yoksa 10 yıl gençleşmek mi?",
                    "choice_a": "10 Milyon Lira",
                    "choice_b": "10 Yıl Gençleşmek"
                },
                {
                    "question": f"{topic} karşısında hangisini seçerdiniz: Acımasız gerçekler mi, huzurlu bir yanılsama mı?",
                    "choice_a": "Acımasız Gerçekler",
                    "choice_b": "Huzurlu Yanılsama"
                }
            ]
        return random.choice(dilemmas)

    @classmethod
    def generate_fomo_forbidden_knowledge_hook(cls, topic: str, category: str = "fomo", lang: str = "tr") -> str:
        """
        Items 218, 219, 220: FOMO (Kaybetme Korkusu), Yasak Meyve & Sosyal Kanıt Kancaları.
        """
        if lang == "en":
            if category == "forbidden":
                return f"3 dark principles of {topic} that psychologists warn people never to reveal publicly."
            elif category == "social_proof":
                return f"The hidden daily habit about {topic} practiced exclusively by the top 0.1% achievers."
            return f"99% of people will fail at {topic} because nobody explained this single hidden rule."
        else:
            if category == "forbidden":
                return f"{topic} konusunda uzmanların halka açıklanmasını istemediği 3 karanlık kural."
            elif category == "social_proof":
                return f"Dünyanın en başarılı insanlarının {topic} konusunda her gün uyguladığı gizli rutin."
            return f"İnsanların %99'u {topic} konusunda bu kuralı bilmediği için kaybediyor."

    @classmethod
    def generate_challenge_hook(cls, topic: str, lang: str = "tr") -> str:
        """
        Item 228 & 268: Kullanıcıyı Harekete Geçiren Meydan Okuma & Zaman Baskısı.
        """
        if lang == "en":
            return f"Only people with an IQ above 125 can solve this {topic} puzzle on their first try: You have 5 seconds!"
        return f"Bu {topic} bilmecesini sadece IQ'su 125 üstü olanlar ilk bakışta çözebiliyor: Cevap için sadece 5 saniyen var!"

    @classmethod
    def get_sticky_hook_banner(cls, topic: str, mood: str = "warning", lang: str = "tr") -> str:
        """
        Item 232: Ekranın Üst Kısmına Sabit Kanca Yazısı (Sticky Top Hook Banner).
        Video boyunca ekranın en üstünde sabit durarak kaydırma refleksini frenler.
        """
        banners = {
            "warning": "⚠️ ASLA BUNU YAPMAYIN" if lang == "tr" else "⚠️ NEVER DO THIS",
            "secret": "🚨 SAKLANAN GERÇEK" if lang == "tr" else "🚨 HIDDEN REALITY",
            "mindset": "🧠 ZİHNİNİ YÖNETEN KURAL" if lang == "tr" else "🧠 MASTER YOUR MIND",
            "money": "💰 %1'LİK DİLİMİN SIRRI" if lang == "tr" else "💰 SECRET OF THE TOP 1%"
        }
        return banners.get(mood, banners["warning"])

    @classmethod
    def generate_pinned_comment_bait(cls, topic: str, lang: str = "tr") -> Dict[str, str]:
        """
        Items 234 & 269: Yorumlarda Cevap Arama Tuzağı & Yorum Sabitleme Kancası.
        """
        if lang == "en":
            return {
                "video_cta": "I pinned the surprising answer in the comments, let's see who guessed it first!",
                "pinned_comment": f"The hidden detail about {topic} is revealed here! The most creative reply will get pinned."
            }
        return {
            "video_cta": "Cevabı yorumlara sabitledim, bakalım doğru tahmin edebilecek misiniz?",
            "pinned_comment": f"{topic} konusundaki en şaşırtıcı detay burada! En yaratıcı cevabı veren ilk 3 kişiyi sabitliyorum."
        }

    @classmethod
    def format_numbered_rule_hierarchy(cls, rules: List[str], lang: str = "tr") -> List[Dict[str, Any]]:
        """
        Item 241: Numaralandırılmış Madde Hiyerarşisi ("Kural 1... Kural 2... Ve en tehlikelisi Kural 3...").
        """
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
                "full_narration": f"{prefix} {rule.strip()}"
            })
        return formatted

    @classmethod
    def get_subconscious_color_palette(cls, niche_or_mood: str) -> Dict[str, str]:
        """
        Item 249: Bilinçaltı Renk Psikolojisi Paleti.
        """
        low = (niche_or_mood or "").lower()
        if any(k in low for k in ["danger", "horror", "gizem", "korku", "tehlike", "shock"]):
            return cls.SUBCONSCIOUS_PALETTES["danger_mystery"]
        elif any(k in low for k in ["money", "finance", "wealth", "zengin", "para", "borsa", "kripto"]):
            return cls.SUBCONSCIOUS_PALETTES["wealth_success"]
        elif any(k in low for k in ["tech", "ai", "cyber", "robot", "bilim", "space", "yapay zeka", "zeka", "teknoloji"]):
            return cls.SUBCONSCIOUS_PALETTES["cyber_tech"]
        return cls.SUBCONSCIOUS_PALETTES["stoic_philosophy"]

    @classmethod
    def calculate_cadence_acceleration(cls, total_duration: float = 45.0, scene_count: int = 14) -> List[float]:
        """
        Item 266: Kurgu Ritim Hızlandırması (Cadence Acceleration Curve).
        Video sonuna doğru kesim sürelerini 3.2s'den 1.4s'ye düşürerek heyecan ve retention tırmandırır.
        """
        if scene_count <= 0:
            return []
        
        # Linear weight deceleration for duration: early scenes get higher weight, climax gets lower weight
        weights = [1.0 - (0.5 * (i / max(1, scene_count - 1))) for i in range(scene_count)]
        sum_weights = sum(weights)
        durations = [round((w / sum_weights) * total_duration, 2) for w in weights]
        
        # Clamp between 1.2s and 4.5s
        adjusted = [max(1.2, min(4.5, d)) for d in durations]
        diff = round(total_duration - sum(adjusted), 2)
        adjusted[-1] = round(adjusted[-1] + diff, 2)
        return adjusted

    @classmethod
    def build_shorts_story_arc_breakdown(cls, duration: float = 45.0) -> Dict[str, Any]:
        """
        Item 274: 45-Saniyelik Klasik Shorts Hikaye Arkı (Story Arc Breakdown).
        Giriş (0-3s) -> Çatışma (4-20s) -> Doruk (21-35s) -> Çözüm & Döngü (36-45s).
        """
        return {
            "total_duration": duration,
            "phases": [
                {
                    "phase": "Hook / Giriş",
                    "time_range": "0 - 3s",
                    "goal": "Pattern interrupt, şok görsel, kaydırmayı engelleme (%75+ Viewed)",
                    "sfx": "Whoosh + Ding",
                    "scale_punch": True
                },
                {
                    "phase": "Conflict / Çatışma & Gelişme",
                    "time_range": "4 - 20s",
                    "goal": "Bilişsel çelişkiyi detaylandırma, tez ve antitez argümanları",
                    "sfx": "Subtle heartbeat & ambient sound",
                    "scale_punch": False
                },
                {
                    "phase": "Climax / Duygusal Zirve",
                    "time_range": "21 - 35s",
                    "goal": "En sarsıcı bilginin açıklanması, kurgu ritminin hızlanması",
                    "sfx": "Rising tension riser",
                    "scale_punch": True
                },
                {
                    "phase": "Resolution & Loop / Çözüm & Döngü",
                    "time_range": "36 - 45s",
                    "goal": "Sentez çıkarımı, kusursuz sonsuz döngü köprüsü (Seamless Loop)",
                    "sfx": "Zero fade-out cut",
                    "scale_punch": False
                }
            ]
        }

    @staticmethod
    def format_bionic_text(words: List[str]) -> List[str]:
        """
        Bionic Reading formatter (Item 215).
        Bolds the first half of each word for ultra-fast reading and focus.
        """
        bionic = []
        for w in words:
            mid = max(1, len(w) // 2)
            first_half = w[:mid]
            second_half = w[mid:]
            bionic.append(f"<b>{first_half}</b>{second_half}")
        return bionic

    @staticmethod
    def generate_spotted_mistake_bait(topic: str) -> str:
        """
        Generates subtle engagement bait / spotted mistake to trigger comment fights (Item 209).
        """
        baits = [
            "Not: Videodaki 2. maddedeki ufak yazım hatasını sadece dikkatli izleyiciler fark eder 👀",
            "İpucu: 3. kuralın yılına dikkat edenler yorumlarda buluşuyor 👇",
            "Sizce 2. kural mı daha etkili yoksa 3. kural mı? Tartışma yorumlarda başladı."
        ]
        return random.choice(baits)

    @classmethod
    def calculate_retention_score(cls, has_split_screen: bool, has_anti_duplicate: bool, 
                                  has_karaoke: bool, has_loop: bool, audio_ducking: bool) -> Dict[str, Any]:
        """
        Calculates Retention / Virality score out of 100 based on algorithm rules (Item 275).
        """
        score = 60
        checks = []

        if has_loop:
            score += 15
            checks.append("Kusursuz Sonsuz Döngü (+15)")
        if has_karaoke:
            score += 10
            checks.append("CapCut Kelime Kelime Altyazı (+10)")
        if audio_ducking:
            score += 8
            checks.append("Akıllı Audio Ducking & SFX (+8)")
        if has_anti_duplicate:
            score += 4
            checks.append("pHash & Anti-Tekrar Koruması (+4)")
        if has_split_screen:
            score += 3
            checks.append("Dopamin Split-Screen Oynanışı (+3)")

        score = min(100, score)
        tier = "Viral Potansiyeli Yüksek 🔥" if score >= 90 else "İyi Performans 👍"

        return {
            "score": score,
            "tier": tier,
            "checks": checks
        }


viral_retention_engine = ViralRetentionEngine()
