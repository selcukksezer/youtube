"""
Hybrid Niches & Synergy Library
Implements Items 276 - 345 of the 500-Item YouTube Shorts Automation Roadmap.
Blends top-performing high-RPM niches with visual retention formats,
niche collision formulas, episodic hooks, and Tier-1 market adapters.
"""

from typing import Dict, List, Any, Optional


HYBRID_NICHES: Dict[str, Dict[str, Any]] = {
    "stoic_cyberpunk": {
        "id": "stoic_cyberpunk",
        "name": "Stoacılık + Cyberpunk Distopya (Item 276)",
        "category": "Felsefe & Gelecek",
        "rpm_tier": "Yüksek (Tier-1 Uyumlu)",
        "tone": "profound, cold, futuristic, philosophical",
        "hook_style": "Antik felsefe neon ışıklı distopik gelecek estetiğiyle buluşuyor.",
        "split_screen_default": False,
        "bg_style": "cyberpunk neon city rain dark futuristic",
        "loop_bridge": "...ve tam da bu yüzden antik Stoacılar Marcus Aurelius gibi diyordu ki...",
        "system_prompt_addition": (
            "Anlatım tonu bilge, sakin ve geleceğin distopik dünyasından seslenen bir filozof gibi olmalıdır. "
            "Görsel arama terimleri 'cyberpunk neon city night rain', 'futuristic dark technology', 'stoic statue glitch neon' içermelidir."
        )
    },
    "history_chat": {
        "id": "history_chat",
        "name": "Tarih + WhatsApp / iMessage Chat Simülasyonu (Item 277)",
        "category": "Tarih & Mizah",
        "rpm_tier": "Çok Yüksek Viralite",
        "tone": "dramatic, witty, conversational",
        "hook_style": "Tarihi liderlerin gizli WhatsApp grubunda konuşuyormuş gibi diyalogları.",
        "split_screen_default": False,
        "bg_style": "vintage paper typewriter historical map",
        "loop_bridge": "...ve bu mesaj gruptan silinmeden hemen önce başlayan o ilk konuşmada...",
        "system_prompt_addition": (
            "Senaryo bir grup sohbeti (WhatsApp/iMessage) formatında kurgulanmalıdır. "
            "Her sahne bir liderin (örn. Sezar, Napolyon, Churchill) attığı mesaj gibi yazılmalıdır."
        )
    },
    "dark_psychology_parkour": {
        "id": "dark_psychology_parkour",
        "name": "Karanlık Psikoloji + Parkour Split-Screen (Item 278)",
        "category": "Psikoloji & Oynanış",
        "rpm_tier": "En Yüksek Tutunma (%120+)",
        "tone": "sharp, hypnotic, analytical",
        "hook_style": "Üstte manipülasyon kuralları, altta hipnotik parkour oynanışı.",
        "split_screen_default": True,
        "bg_style": "dark shadow psychology brain silhouette",
        "loop_bridge": "...çünkü bu psikolojik sırrı öğrendiğinizde hemen fark edeceksiniz ki...",
        "system_prompt_addition": (
            "Manipülasyon ve mikro beden dili taktiklerini madde madde açıkla. "
            "Split-screen oynanış videosuyla izleyicinin dikkatini hipnotize et."
        )
    },
    "mystery_earth_zoom": {
        "id": "mystery_earth_zoom",
        "name": "Gizem / Komplo + Google Earth 3D Zoom (Item 279)",
        "category": "Gizem & Bilim",
        "rpm_tier": "Yüksek Merak",
        "tone": "eerie, thrilling, investigative",
        "hook_style": "Uzaydan Dünya'daki o gizemli koordinata 3D yaklaşma kurgusu.",
        "split_screen_default": False,
        "bg_style": "satellite view earth space isolated mystery location",
        "loop_bridge": "...ve işte uyduların asla açıklayamadığı o ilk koordinata geri dönüyoruz:",
        "system_prompt_addition": (
            "Dünyanın en ıssız ve gizemli koordinatlarını anlat. "
            "Görseller uydu görüntüleri, 3D Dünya ve ıssız adalar içermelidir."
        )
    },
    "would_you_rather_duel": {
        "id": "would_you_rather_duel",
        "name": "Would You Rather + İki Taraflı Seçim Oylaması (Item 280)",
        "category": "Quiz & İnteraktif",
        "rpm_tier": "Yüksek Yorum Sayısı",
        "tone": "fun, competitive, suspenseful",
        "hook_style": "Ekranı ikiye bölen ve 3 saniye süre tanıyan sesli oylama.",
        "split_screen_default": False,
        "bg_style": "red vs blue contrast countdown neon",
        "loop_bridge": "...ve şimdi en zor karara geliyoruz çünkü ilk soru şuydu:",
        "system_prompt_addition": (
            "İki zıt ve çok zor seçeneği (Kırmızı Hap vs Mavi Hap) karşılaştır. "
            "İzleyiciye 3 saniye süre tanı ve Ding sesiyle sonucu sor."
        )
    },
    "reddit_asmr": {
        "id": "reddit_asmr",
        "name": "Reddit İtirafı + Kinetik Kum / Pasta ASMR (Item 281)",
        "category": "Hikaye & ASMR",
        "rpm_tier": "Popüler & Viral",
        "tone": "shocking, emotional, immersive",
        "hook_style": "Akıl almaz bir aile/iş itirafı okunurken altta tatmin edici ASMR.",
        "split_screen_default": True,
        "bg_style": "satisfying kinetic sand soap cutting cake slicing",
        "loop_bridge": "...ve bu itirafı okuduğumda tam olarak başladığım yere döndüm çünkü...",
        "system_prompt_addition": (
            "Reddit tarzı birinci tekil şahıs diliyle şok edici bir itiraf anlat. "
            "Görseller tatmin edici kinetik kum veya sabun kesme olmalıdır."
        )
    },
    "cosmic_epic_hans_zimmer": {
        "id": "cosmic_epic_hans_zimmer",
        "name": "Bilim / Evren + Hans Zimmer Tipi Epik Müzik (Item 282)",
        "category": "Bilim & Astronomi",
        "rpm_tier": "Yüksek Global İlgi",
        "tone": "epic, monumental, awe-inspiring",
        "hook_style": "James Webb teleskobu bulgularını devasa bas vuruşlu epik müziklerle sunma.",
        "split_screen_default": False,
        "bg_style": "deep space nebula james webb black hole cosmos 4k",
        "loop_bridge": "...ve evrenin bu akıl almaz genişliğinde her şey tam da bu ilk kıvılcımla başladı:",
        "system_prompt_addition": (
            "Astrofizik ve evrenin sırlarını insanı dehşete düşüren büyüklük kıyaslamalarıyla aktar. "
            "Görseller James Webb teleskobu, karadelikler ve süpernovalar içermelidir."
        )
    },
    "crypto_comic_book": {
        "id": "crypto_comic_book",
        "name": "Finans / Kripto + Retro Çizgi Roman (Item 283)",
        "category": "Finans & Grafik",
        "rpm_tier": "En Yüksek CPM ($12-$25)",
        "tone": "stylish, dynamic, narrative",
        "hook_style": "Satoshi Nakamoto veya Wall Street efsanelerini çizgi roman panelleriyle anlatma.",
        "split_screen_default": False,
        "bg_style": "pop art comic book retro halftone finance bitcoin",
        "loop_bridge": "...ve finans dünyasını sarsan bu devasa sırrın başladığı o ilk panele dönersek...",
        "system_prompt_addition": (
            "Kripto ve borsa hikayelerini gerilimli bir noir çizgi roman anlatısı gibi kurgula."
        )
    },
    "country_guess_countdown": {
        "id": "country_guess_countdown",
        "name": "Bayrak / Ülke Tahmini + Sesli Sayaç (Item 284)",
        "category": "Coğrafya & Quiz",
        "rpm_tier": "Küresel Katılım",
        "tone": "challenging, brisk, engaging",
        "hook_style": "3 ipucu verilirken mozaikten nete dönen bayrak ve 3.. 2.. 1.. sayacı.",
        "split_screen_default": False,
        "bg_style": "world map satellite geography motion blur",
        "loop_bridge": "...şimdi dürüstçe söyleyin, ilk ipucunda hangi ülkeyi tahmin etmiştiniz?",
        "system_prompt_addition": (
            "İzleyiciye 3 ipucu vererek ülkeyi tahmin ettir. Geri sayım ve merak unsuru oluştur."
        )
    },
    "spiritual_rain_nature": {
        "id": "spiritual_rain_nature",
        "name": "Manevi Sözler + Yağmurlu Doğa Çekimleri (Item 285)",
        "category": "Maneviyat & Huzur",
        "rpm_tier": "Yüksek Paylaşım & Kaydetme",
        "tone": "serene, comforting, deep, contemplative",
        "hook_style": "Dinginleştirici ses tonu ve 4K orman/yağmur atmosferiyle iç huzur.",
        "split_screen_default": False,
        "bg_style": "rain falling green forest mist autumn moody nature 4k",
        "loop_bridge": "...bu yüzden ruhunuz ne zaman yorulsa şu kadim hakikati hatırlayın çünkü...",
        "system_prompt_addition": (
            "İnsanın kalbine dokunan, huzur veren manevi ve felsefi öğütler yaz. Yağmur ve doğa görselleri kullan."
        )
    },
    "whatsapp_horror_voice": {
        "id": "whatsapp_horror_voice",
        "name": "WhatsApp Korku Hikayeleri + Ses Dalgası (Item 286)",
        "category": "Korku & Gerilim",
        "rpm_tier": "Viral Genç Kitle",
        "tone": "chilling, suspenseful, realistic",
        "hook_style": "Hikayenin ortasında WhatsApp ses kaydı dinletiliyormuş gibi yeşil ses dalgası animasyonu.",
        "split_screen_default": False,
        "bg_style": "dark night bedroom eerie shadows phone screen glowing",
        "loop_bridge": "...ve telefonuma gelen o son ses kaydını dinlediğimde her şey baştan başladı:",
        "system_prompt_addition": (
            "Gece yarısı gelen gizemli bir mesajlaşma ve ses kaydı hikayesi kurgula. Tüyler ürpertici bir son hazırla."
        )
    },
    "lifehack_affiliate_3items": {
        "id": "lifehack_affiliate_3items",
        "name": "Hayatınızı Kolaylaştıracak 3 Şey (Item 287)",
        "category": "Affiliate & Ürün",
        "rpm_tier": "Yüksek Komisyon / Dönüşüm",
        "tone": "practical, energetic, problem-solving",
        "hook_style": "'Bunu bilmeden önce hayatım çok daha zordu' problem-çözüm kurgusu.",
        "split_screen_default": False,
        "bg_style": "modern clean desk organization gadgets macro 4k",
        "loop_bridge": "...ve işinize en çok yarayacak o 1. ürünü bir kez daha hatırlatmak gerekirse...",
        "system_prompt_addition": (
            "Gündelik hayattaki can sıkıcı 3 problemi çözen akıllı araçları anlat. Net ve hızlı kurgu yap."
        )
    },
    "movie_idiom_english": {
        "id": "movie_idiom_english",
        "name": "Dil Eğitimi + Dizi / Film Deyimleri (Item 288)",
        "category": "Eğitim & Sinema",
        "rpm_tier": "Çok Yüksek Kaydetme Oranı",
        "tone": "educational, entertaining, modern",
        "hook_style": "'Bunu ders kitaplarında değil, sadece filmlerde duyarsınız' kancası.",
        "split_screen_default": False,
        "bg_style": "cinema screen film reel moody movie scene",
        "loop_bridge": "...bir dahaki sefere yabancı bir film izlerken bu ifadeyi duyduğunuzda hatırlayın:",
        "system_prompt_addition": (
            "Günlük İngilizcede en sık kullanılan ama okullarda öğretilmeyen 1 viral deyimi açıkla."
        )
    },
    "mythology_ai_epic": {
        "id": "mythology_ai_epic",
        "name": "Mitoloji + Yapay Zeka Epik Animasyonları (Item 289)",
        "category": "Mitoloji & Tarih",
        "rpm_tier": "Yüksek Retention",
        "tone": "legendary, powerful, dramatic",
        "hook_style": "İskandinav ve Yunan tanrılarının savaşlarını hiper-gerçekçi görsellerle canlandırma.",
        "split_screen_default": False,
        "bg_style": "nordic thunder zeus thor lightning ancient god epic",
        "loop_bridge": "...ve tanrıların bin yıl süren bu efsanevi savaşı tam olarak şurada başlamıştı:",
        "system_prompt_addition": (
            "Antik mitolojinin en karanlık ve güçlü hikayelerini sinematik bir dille anlat."
        )
    },
    "old_money_luxury_mindset": {
        "id": "old_money_luxury_mindset",
        "name": "Zenginlik Disiplini + Old Money Estetiği (Item 291)",
        "category": "Motivasyon & Finans",
        "rpm_tier": "Maksimum Reklamveren İlgisi",
        "tone": "refined, disciplined, quiet luxury, commanding",
        "hook_style": "Sessiz zenginlik, klasik saatler ve yacht klipleriyle çelik gibi disiplin mesajları.",
        "split_screen_default": False,
        "bg_style": "old money aesthetic vintage luxury car suit yacht classic architecture",
        "loop_bridge": "...gerçek zenginlerin asla halka açık söylemediği o ilk kurala dönersek...",
        "system_prompt_addition": (
            "Sessiz lüks ve mental disiplin ilkelerini işle. Gösterişten uzak, ağırbaşlı ve ilham verici ol."
        )
    },
    "conspiracy_fbi_newspaper": {
        "id": "conspiracy_fbi_newspaper",
        "name": "Popüler Komplo Teorileri + Gazete Küpürü (Item 292)",
        "category": "Tarih & Komplo",
        "rpm_tier": "Yüksek Viralite",
        "tone": "confidential, urgent, dark investigative",
        "hook_style": "1960'lardan kalma sansürlü FBI gizli dosya görselleriyle gizem anlatımı.",
        "split_screen_default": False,
        "bg_style": "fbi declassified document typewriter redacted stamp retro detective desk",
        "loop_bridge": "...ve dosyanın sansürlenen ilk sayfasında yer alan o soruya geri dönersek...",
        "system_prompt_addition": (
            "Gizliliği yeni kaldırılmış bir hükümet belgesi veya gizemli olay kurgusu yap."
        )
    },
    "ai_tools_screen": {
        "id": "ai_tools_screen",
        "name": "Yapay Zeka Siteleri + Canlı Ekran Arayüzü (Item 295)",
        "category": "Teknoloji & Yazılım",
        "rpm_tier": "Maksimum CPM (Tier-1)",
        "tone": "fast-paced, tech-savvy, secret discovery",
        "hook_style": "'Bu 3 yapay zeka sitesini bilmek yasa dışı hissettiriyor' kancası.",
        "split_screen_default": False,
        "bg_style": "laptop screen coding ui modern app interface",
        "loop_bridge": "...ve işte internette kimsenin bilmediği o 1. yapay zeka aracına gelirsek...",
        "system_prompt_addition": (
            "İnternette hayatı kolaylaştıran 3 devrimsel AI aracını tanıt. "
            "Hızlı tempolu, ekran kayıtları ve minimalist teknoloji estetiği kullan."
        )
    },
    "micro_book_summary": {
        "id": "micro_book_summary",
        "name": "1 Dakikada Kitap Özeti + Hap Bilgi (Item 296)",
        "category": "Kişisel Gelişim & Kitap",
        "rpm_tier": "Yüksek Kaydetme & Takip",
        "tone": "crisp, insightful, empowering",
        "hook_style": "Atomik Alışkanlıklar gibi kült kitapların 300 sayfalık ana fikrini 45 saniyede alma.",
        "split_screen_default": False,
        "bg_style": "minimalist book page turning coffee study desk typography",
        "loop_bridge": "...ve yazarın kitabın ilk sayfasında altını çizdiği o temel prensip şuydu:",
        "system_prompt_addition": (
            "Dünyaca ünlü bir kitabın hayat değiştiren 3 ana dersini hap bilgi olarak özetle."
        )
    },
    "true_crime_police_radio": {
        "id": "true_crime_police_radio",
        "name": "Gerçek Suç + Polis Telsizi & CCTV (Item 297)",
        "category": "Gerçek Suç & Belgesel",
        "rpm_tier": "Çok Yüksek Ortalama İzlenme",
        "tone": "grim, chilling, urgent, forensic",
        "hook_style": "Gerçek suç davalarını polis telsizi cızırtısı ve güvenlik kamerası estetiğiyle anlatma.",
        "split_screen_default": False,
        "bg_style": "cctv footage night static dark alley police siren blur",
        "loop_bridge": "...ve dedektiflerin olay yerinde bulduğu o ilk ipucuna dönersek...",
        "system_prompt_addition": (
            "Gerçek bir polisiye vakayı veya gizemli kayboluşu adli tıp titizliğiyle anlat."
        )
    },
    "deep_sea_thalassophobia": {
        "id": "deep_sea_thalassophobia",
        "name": "Derin Deniz Yaratıkları + Talasofobi (Item 304)",
        "category": "Doğa & Bilinmeyen",
        "rpm_tier": "Yüksek Bilişsel Şok",
        "tone": "abyssal, haunting, claustrophobic",
        "hook_style": "Okyanusun 10.000 metre altındaki garip varlıkları anlatan ürpertici içerikler.",
        "split_screen_default": False,
        "bg_style": "deep ocean dark underwater abyssal trench bioluminescent creature",
        "loop_bridge": "...ve okyanusun güneş ışığı girmeyen o ilk karanlık katmanına inersek...",
        "system_prompt_addition": (
            "Mariana Çukuru ve okyanus derinliklerindeki gizemli canlıları korku ve merakla anlat."
        )
    },
    "untranslatable_words_sonder": {
        "id": "untranslatable_words_sonder",
        "name": "Bilinmeyen Kelimeler ve Anlamları (Item 338)",
        "category": "Psikoloji & Dil",
        "rpm_tier": "Viral Paylaşım",
        "tone": "poetic, evocative, mesmerizing",
        "hook_style": "'Sonder: Yanından geçen herkesin senin kadar karmaşık bir hayatı olduğunu fark etme anı.'",
        "split_screen_default": False,
        "bg_style": "cinematic crowd blurred city sunset lonely silhouette poetic",
        "loop_bridge": "...ve hayatınız boyunca hissettiğiniz ama adını koyamadığınız o duyguya geri dönersek...",
        "system_prompt_addition": (
            "Dillerde karşılığı tek kelimede saklı olan büyüleyici psikolojik kavramları anlat."
        )
    },
    "alternate_history_ai": {
        "id": "alternate_history_ai",
        "name": "Yapay Zeka ile Alternatif Tarih (Item 342)",
        "category": "Alternatif Tarih & Gelecek",
        "rpm_tier": "Yüksek Yorum & Tartışma",
        "tone": "dramatic, speculative, monumental",
        "hook_style": "'Eğer İskender 32 yaşında ölmeseydi dünya bugün nasıl görünürdü?'",
        "split_screen_default": False,
        "bg_style": "steampunk historical monuments alternative timeline epic",
        "loop_bridge": "...ve tarihin akışını değiştiren o ilk kararın verildiği ana dönersek...",
        "system_prompt_addition": (
            "Tarihteki bir kırılma anının farklı sonuçlandığı alternatif bir evren tasvir et."
        )
    }
}


def get_hybrid_niche(niche_id: str) -> Dict[str, Any]:
    """Returns hybrid niche definition or defaults to stoic_cyberpunk."""
    return HYBRID_NICHES.get(niche_id, HYBRID_NICHES["stoic_cyberpunk"])


def list_all_hybrid_niches() -> List[Dict[str, Any]]:
    """Lists all hybrid synergy niches with metadata."""
    return list(HYBRID_NICHES.values())


def collide_two_niches(niche_a_id: str, niche_b_id: str) -> Dict[str, Any]:
    """
    Item 320: İki Farklı Nişin Çarpışması (Niche Collision Engine).
    Örnek: 'Yapay Zeka Antik Roma'yı Yönetseydi Ne Olurdu?' konsepti gibi
    farklı kategorileri melezleyerek benzersiz algoritmik bir niş üretir.
    """
    niche_a = get_hybrid_niche(niche_a_id)
    niche_b = get_hybrid_niche(niche_b_id)

    collision_title = f"{niche_a['name'].split('(')[0].strip()} X {niche_b['name'].split('(')[0].strip()}"
    blended_bg = f"{niche_a['bg_style']} blended with {niche_b['bg_style']}"
    blended_tone = f"{niche_a['tone']}, {niche_b['tone']}"

    return {
        "collision_id": f"{niche_a_id}_x_{niche_b_id}",
        "title": collision_title,
        "category_blend": f"{niche_a['category']} + {niche_b['category']}",
        "blended_tone": blended_tone,
        "blended_bg_style": blended_bg,
        "collision_hook": f"Ne zaman {niche_a['name'].split('+')[0].strip()} ile {niche_b['name'].split('+')[0].strip()} bir araya gelse, ortaya bu akıl almaz tablo çıkıyor.",
        "loop_bridge": f"...ve işte bu iki dünyanın çarpıştığı o ilk ana geri dönersek...",
        "system_prompt": (
            f"Bu senaryoda iki farklı dünyayı melezle: {niche_a['name']} VE {niche_b['name']}. "
            f"Her iki konseptin görsel ve tematik unsurlarını sahne sahne harmanla."
        )
    }


def generate_episodic_series_hook(series_title: str, episode_num: int = 1, total_parts: int = 10, lang: str = "tr") -> Dict[str, str]:
    """
    Item 314: Seri Formatı (Bölüm 1 / Part 1 Episodic Hook Generator).
    İzleyiciyi kanala abone yapıp diğer bölümleri izletmek için seri formatı üretir.
    """
    if lang == "en":
        return {
            "title": f"{series_title}: Part {episode_num}/{total_parts} #Shorts",
            "hook": f"Welcome to Part {episode_num} of {series_title}. If you missed the previous chapter, subscribe to not miss Part {episode_num + 1}!",
            "closing_cta": f"Follow for Part {episode_num + 1}, dropping tomorrow!"
        }
    return {
        "title": f"{series_title}: Bölüm {episode_num} #Shorts",
        "hook": f"{series_title} serimizin {episode_num}. bölümündeyiz. Bir sonraki kritik bölümü kaçırmamak için şimdiden takip et!",
        "closing_cta": f"{episode_num + 1}. bölüm yarın geliyor, kaçırmamak için takipte kal!"
    }


def generate_ironic_reverse_advice(topic: str, lang: str = "tr") -> Dict[str, Any]:
    """
    Item 329: İronik / Ters Tavsiye Kancası (Ironic Reverse Psychology Bait).
    'Hayatınızı mahvetmek ve sonsuza kadar başarısız kalmak istiyorsanız şu 3 şeyi yapın.'
    """
    if lang == "en":
        return {
            "hook": f"If your goal is to completely ruin your life with {topic} and stay miserable forever, follow these 3 rules:",
            "tone": "sarcastic, shocking, eye-opening",
            "reverse_rules": [
                f"Rule 1: Always blame everyone else whenever {topic} goes wrong.",
                f"Rule 2: Procrastinate every single day and wait for perfection.",
                f"Rule 3: Trust random social media opinions over deep focus."
            ]
        }
    return {
        "hook": f"Eğer {topic} konusunda hayatınızı tamamen mahvetmek ve asla başaramamak istiyorsanız, şu 3 kuralı uygulayın:",
        "tone": "ironik, sarsıcı, düşündürücü",
        "reverse_rules": [
            f"Kural 1: {topic} konusunda her terslikte hemen başkalarını suçlayın.",
            f"Kural 2: Asla harekete geçmeyin, her zaman mükemmel anı bekleyin.",
            f"Kural 3: Kendi aklınız yerine herkesin dedikodularına göre yön çizin."
        ]
    }


def generate_what_if_hypothesis(scenario: str, lang: str = "tr") -> Dict[str, Any]:
    """
    Item 330: Bilimsel Hipotez Simülasyonu ("Eğer Dünya 5 saniyeliğine oksijensiz kalsaydı...").
    """
    if lang == "en":
        return {
            "hook": f"What would actually happen if {scenario}? The scientific reality is terrifying.",
            "phases": [
                "Second 1: Immediate atmospheric shock and sound collapse.",
                "Second 2-3: Structural disintegration of concrete and metal.",
                "Second 4-5: Total irreversible cosmic transformation."
            ]
        }
    return {
        "hook": f"Eğer {scenario} gerçekleşseydi ne olurdu? Bilimsel gerçekler tahmininizden çok daha korkutucu.",
        "phases": [
            "1. Saniye: Ani atmosferik basınç düşüşü ve seslerin kesilmesi.",
            "2-3. Saniye: Beton yapıların ve metallerin anında çözülmesi.",
            "4-5. Saniye: Geri döndürülemez devasa kozmik dönüşüm."
        ]
    }


def adapt_to_tier1_market(turkish_concept: str, target_country: str = "US") -> Dict[str, Any]:
    """
    Item 321: Tier-1 Ülke Adaptasyonu (Global High-RPM English Conversion).
    Türkiye'de tutan bir nişi ABD/İngiltere hedefli küresel kanala dönüştürür.
    """
    return {
        "original_concept": turkish_concept,
        "target_market": target_country,
        "recommended_voice": "en-US-ChristopherNeural" if target_country == "US" else "en-GB-RyanNeural",
        "target_rpm_multiplier": "3.5x - 6.0x (Global Tier-1 Band)",
        "language_code": "en",
        "currency_symbol": "$",
        "timezone_posting_window": "EST 12:00 - 15:00 (New York)" if target_country == "US" else "GMT 17:00 - 20:00 (London)",
        "adaptation_guideline": "Kavramlar yerel kültüre değil, küresel evrensel psikolojiye ve popüler kültüre uyarlanmalıdır."
    }
