"""
Niche Templates & Viral Hook Prompt Engine
Defines 35 custom niche templates, hooks, seamless loop rules, discussion triggers, and Tier-1 translation prompts.
Covers items: 1-35, 36, 37, 73, 81, 82, 84, 90, 93, 96 from r10_shorts_fikirleri_ve_bot_ozellikleri.md

v2.0 — Advanced schema with RPM bands, viral scores, retention data, A/B hooks, competition analysis.
"""
from typing import Dict, Any, List

# 35 Niche definitions — full production schema
NICHES: Dict[str, Dict[str, Any]] = {
    "1_news_flash": {
        "id": "1_news_flash",
        "name": "Son Dakika & Flaş Haber",
        "name_en": "Breaking News Flash",
        "category": "Haber & Güncel",
        "tone": "urgent, factual, dramatic",
        "hook_style": "SON DAKİKA! Bu haber her şeyi değiştirebilir!",
        "system_instruction": "Flaş haber bülteni formatında konuş. Ciddi, acil ve dikkat çekici bir ton kullan. 3 temel kilit bilgiyi sırala ve izleyiciye görüşünü sorarak bitir.",
        "default_music": "dramatic",
        "has_split_screen": False,
        # Advanced fields
        "icon": "fa-bolt",
        "color_palette": "red_alert",
        "rpm_tier": "$3-7",
        "viral_score": 82,
        "avg_retention_pct": 68,
        "competition_level": "high",
        "best_posting_time": "08:00-10:00 & 18:00-20:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": False,
        "episodic_capable": False,
        "loop_formula": "time_reset",
        "trending_keywords": ["son dakika", "flaş haber", "breaking news", "gündem", "gelişme"],
        "ab_test_hook_variants": [
            "SON DAKİKA! Bu haber her şeyi değiştirebilir!",
            "Kimsenin size söylemediği o kritik gelişme şimdi ortaya çıktı!",
            "Bu haberi duyanlar şok geçirdi — işte tüm detaylar!"
        ]
    },
    "2_reddit_confessions": {
        "id": "2_reddit_confessions",
        "name": "Reddit / Anonim İtiraflar",
        "name_en": "Reddit & Anonymous Confessions",
        "category": "Hikaye & İtiraf",
        "tone": "conversational, suspenseful, emotional",
        "hook_style": "Hayatımın en büyük hatasını yaptım ve kimseye anlatamadım...",
        "system_instruction": "Bir Reddit kullanıcısının ağzından birinci tekil şahıs ('ben') anlatımıyla konuş. 'AITA? / Ben mi hatalıyım?' kurgusu oluştur. Merakı sürekli canlı tut.",
        "default_music": "mysterious",
        "has_split_screen": True,
        "icon": "fa-reddit-alien",
        "color_palette": "orange_reddit",
        "rpm_tier": "$4-9",
        "viral_score": 91,
        "avg_retention_pct": 79,
        "competition_level": "medium",
        "best_posting_time": "21:00-23:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "plot_twist_reset",
        "trending_keywords": ["reddit", "AITA", "itiraf", "anonim hikaye", "am I wrong"],
        "ab_test_hook_variants": [
            "Hayatımın en büyük hatasını yaptım ve kimseye anlatamadım...",
            "AITA? İş ortağımı ifşa ettim ve şimdi pişman olup olmadığımı bilmiyorum.",
            "Bu itirafı kimseyle paylaşmadım — ta ki bu geceye kadar."
        ]
    },
    "3_split_gameplay": {
        "id": "3_split_gameplay",
        "name": "Alt Ekran Oynanış (Split-Screen)",
        "name_en": "Split-Screen Gameplay Story",
        "category": "Eğlence & Hikaye",
        "tone": "entertaining, fast-paced",
        "hook_style": "Bu hikayeyi dinlerken gözlerinizi ekrandan alamayacaksınız!",
        "system_instruction": "Hızlı, dinamik ve akıcı bir hikaye kurgusu yaz. Alt ekranda parkour/oynanış olacağı için temponun hiç düşmemesini sağla.",
        "default_music": "lofi",
        "has_split_screen": True,
        "icon": "fa-gamepad",
        "color_palette": "neon_green",
        "rpm_tier": "$2-5",
        "viral_score": 88,
        "avg_retention_pct": 83,
        "competition_level": "high",
        "best_posting_time": "15:00-19:00 TRT",
        "cta_type": "save",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "curiosity_repetition",
        "trending_keywords": ["split screen", "parkour", "minecraft", "subway surfers", "gameplay story"],
        "ab_test_hook_variants": [
            "Bu hikayeyi dinlerken gözlerinizi ekrandan alamayacaksınız!",
            "İki ekran, bir sır — aynı anda hem hissedecek hem izleyeceksiniz.",
            "Alttan parkour, üstten sarsıcı itiraf — hazır mısın?"
        ]
    },
    "4_would_you_rather": {
        "id": "4_would_you_rather",
        "name": "Tercih Et (Would You Rather Quiz)",
        "name_en": "Would You Rather Quiz",
        "category": "Quiz & Oyun",
        "tone": "interactive, challenging",
        "hook_style": "Bu 3 tercihten birini seçmek zorundasın! Hangisi?",
        "system_instruction": "İzleyiciye 2 zıt ve zor seçenek sun. 'A mı yoksa B mi?' formatında 4 tur yap. Her turda 3-5 saniye düşünme süresi kurgula.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-scale-balanced",
        "color_palette": "split_red_blue",
        "rpm_tier": "$2-4",
        "viral_score": 86,
        "avg_retention_pct": 81,
        "competition_level": "medium",
        "best_posting_time": "20:00-22:00 TRT",
        "cta_type": "vote",
        "tier1_compatible": True,
        "episodic_capable": False,
        "loop_formula": "challenge_accepted",
        "trending_keywords": ["would you rather", "tercih et", "quiz", "seçim", "oylama"],
        "ab_test_hook_variants": [
            "Bu 3 tercihten birini seçmek zorundasın! Hangisi?",
            "Sana imkansız bir soru soruyorum — doğru cevap yok!",
            "%70 insan yanlış seçiyor — sen hangisini seçerdin?"
        ]
    },
    "5_guess_flag_country": {
        "id": "5_guess_flag_country",
        "name": "Bayrak / Ülke Tahmin Oyunu",
        "name_en": "Guess the Flag / Country Quiz",
        "category": "Quiz & Coğrafya",
        "tone": "gamified, educational",
        "hook_style": "Sadece dâhiler bu 3 bayrağı 5 saniyede bilebilir!",
        "system_instruction": "Aşama aşama ipuçları ver: 1. ipucu nüfus, 2. ipucu başkent, 3. ipucu ünlü yemek. Sonunda cevabı ver ve kaç doğru bildiklerini yoruma yazmalarını iste.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-flag",
        "color_palette": "world_map",
        "rpm_tier": "$3-6",
        "viral_score": 79,
        "avg_retention_pct": 74,
        "competition_level": "medium",
        "best_posting_time": "17:00-20:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "curiosity_repetition",
        "trending_keywords": ["flag quiz", "ülke tahmin", "bayrak bul", "geography quiz", "dünya coğrafyası"],
        "ab_test_hook_variants": [
            "Sadece dâhiler bu 3 bayrağı 5 saniyede bilebilir!",
            "Hangi ülke? 3 ipucu veriyorum — kaçıncıda bulursun?",
            "IQ'n ne kadar? Bu bayrağı kim bilebilir ki?"
        ]
    },
    "6_stoic_philosophy": {
        "id": "6_stoic_philosophy",
        "name": "Stoacılık & Antik Felsefe",
        "name_en": "Stoicism & Ancient Philosophy",
        "category": "Felsefe & Kişisel Gelişim",
        "tone": "deep, calm, disciplined, masculine",
        "hook_style": "Marcus Aurelius bugün yaşasaydı sana tam olarak şunu söylerdi...",
        "system_instruction": "Stoacı filozofların (Marcus Aurelius, Seneca, Epiktetos) ilkelerini modern hayattaki acılara, öfkeye ve disipline uyarla. Derin, vakur ve etkileyici bir ton kur.",
        "default_music": "epic",
        "has_split_screen": False,
        "icon": "fa-person-praying",
        "color_palette": "gold_marble",
        "rpm_tier": "$12-22",
        "viral_score": 93,
        "avg_retention_pct": 85,
        "competition_level": "medium",
        "best_posting_time": "06:00-08:00 TRT",
        "cta_type": "save",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "cause_and_effect",
        "trending_keywords": ["stoicism", "Marcus Aurelius", "Stoacılık", "antik felsefe", "disiplin"],
        "ab_test_hook_variants": [
            "Marcus Aurelius bugün yaşasaydı sana tam olarak şunu söylerdi...",
            "2000 yıllık bu felsefe bugün hayatını kurtarabilir.",
            "Stoacıların en büyük sırrı — milyonlarca insan hala bilmiyor."
        ]
    },
    "7_dark_psychology": {
        "id": "7_dark_psychology",
        "name": "Karanlık Psikoloji & Beden Dili",
        "name_en": "Dark Psychology & Body Language",
        "category": "Psikoloji & Manipülasyon",
        "tone": "mysterious, analytical, cautionary",
        "hook_style": "Biri seninle konuşurken gözlerini kaçırıyorsa bu 3 anlama gelir!",
        "system_instruction": "İnsan davranışları, manipülasyonu tespit etme, yalan yakalama veya karizma artırma üzerine 3 pratik psikolojik kural anlat.",
        "default_music": "mysterious",
        "has_split_screen": False,
        "icon": "fa-brain",
        "color_palette": "dark_purple",
        "rpm_tier": "$10-20",
        "viral_score": 95,
        "avg_retention_pct": 87,
        "competition_level": "medium",
        "best_posting_time": "21:00-23:00 TRT",
        "cta_type": "save",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "warning_loop",
        "trending_keywords": ["dark psychology", "manipulation", "beden dili", "yalan tespit", "karizma"],
        "ab_test_hook_variants": [
            "Biri seninle konuşurken gözlerini kaçırıyorsa bu 3 anlama gelir!",
            "Manipülatörlerin kullandığı en tehlikeli 3 psikolojik silah.",
            "Bu vücut hareketini yapan birine hiç güvenme — işte nedeni."
        ]
    },
    "8_crypto_market": {
        "id": "8_crypto_market",
        "name": "Kripto & Borsa Günlüğü",
        "name_en": "Crypto & Market Daily",
        "category": "Finans & Yatırım",
        "tone": "fast, analytical, informative",
        "hook_style": "Piyasa bugün kızıla boyandı! Peki balinalar ne yapıyor?",
        "system_instruction": "Bitcoin, Ethereum veya popüler altcoinler hakkında günlük özet geç. Destek/direnç seviyeleri ve makroekonomik gelişmeleri 60 saniyede net özetle.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-bitcoin-sign",
        "color_palette": "bitcoin_orange",
        "rpm_tier": "$15-30",
        "viral_score": 80,
        "avg_retention_pct": 71,
        "competition_level": "high",
        "best_posting_time": "09:00-11:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "secret_knowledge",
        "trending_keywords": ["bitcoin", "kripto", "ethereum", "borsa", "altcoin"],
        "ab_test_hook_variants": [
            "Piyasa bugün kızıla boyandı! Peki balinalar ne yapıyor?",
            "Bitcoin şu an nerede? Bu seviyeyi geçerse her şey değişir.",
            "Kripto analistlerin söylemekten korktuğu o hedef fiyat!"
        ]
    },
    "9_five_facts": {
        "id": "9_five_facts",
        "name": "5 İlginç Bilgi / Bunu Biliyor Muydunuz?",
        "name_en": "5 Mind-Blowing Facts",
        "category": "Bilim & Merak",
        "tone": "surprising, educational",
        "hook_style": "Beyninizin bu bilgiyi duyduktan sonra asla eskisi gibi olmayacak 5 gerçek!",
        "system_instruction": "Bilim, doğa, evren veya insan bedeni hakkında duyanı şaşırtacak 5 sıra dışı maddeyi art arda say.",
        "default_music": "calm",
        "has_split_screen": False,
        "icon": "fa-lightbulb",
        "color_palette": "cyan_science",
        "rpm_tier": "$5-10",
        "viral_score": 84,
        "avg_retention_pct": 77,
        "competition_level": "high",
        "best_posting_time": "12:00-15:00 TRT",
        "cta_type": "save",
        "tier1_compatible": True,
        "episodic_capable": False,
        "loop_formula": "infinite_cycle",
        "trending_keywords": ["ilginç bilgi", "inanılmaz gerçek", "biliyor muydunuz", "mind blowing facts", "bilim"],
        "ab_test_hook_variants": [
            "Beyninizin bu bilgiyi duyduktan sonra asla eskisi gibi olmayacak 5 gerçek!",
            "Ders kitaplarında öğretilmeyen ama bilmeniz gereken 5 şok gerçek.",
            "5 bilgi, 5 saniye — kaçını zaten biliyordunuz?"
        ]
    },
    "10_religious_quotes": {
        "id": "10_religious_quotes",
        "name": "Dini Sözler, Hadis & Günün Duası",
        "name_en": "Spiritual Quotes & Daily Prayers",
        "category": "Maneviyat & Din",
        "tone": "peaceful, emotional, respectful",
        "hook_style": "Gününüzü aydınlatacak ve içinizi ferahlatacak bu duaya amin deyin...",
        "system_instruction": "Huzur veren, umut aşılayan ayet, hadis veya İslam alimlerinin hikmetli sözlerini estetik ve saygılı bir dille aktar.",
        "default_music": "calm",
        "has_split_screen": False,
        "icon": "fa-moon",
        "color_palette": "emerald_spiritual",
        "rpm_tier": "$2-5",
        "viral_score": 88,
        "avg_retention_pct": 82,
        "competition_level": "low",
        "best_posting_time": "06:30-08:00 & 20:00-22:00 TRT",
        "cta_type": "save",
        "tier1_compatible": False,
        "episodic_capable": True,
        "loop_formula": "cause_and_effect",
        "trending_keywords": ["dua", "hadis", "ayet", "İslam", "günlük dua"],
        "ab_test_hook_variants": [
            "Gününüzü aydınlatacak ve içinizi ferahlatacak bu duaya amin deyin...",
            "Hz. Peygamber'in en çok tekrar ettiği o dua bugün hayatınızı değiştirebilir.",
            "Sabah uyanınca bu duayı okuyan insanların hayatına ne oluyor?"
        ]
    },
    "11_language_learning": {
        "id": "11_language_learning",
        "name": "İngilizce / Yabancı Dil Eğitimi",
        "name_en": "English & Language Hacks",
        "category": "Eğitim",
        "tone": "clear, encouraging, instructional",
        "hook_style": "Yabancıların sürekli kullandığı ama okulda öğretilmeyen 3 kalıp!",
        "system_instruction": "Günün 3 pratik deyim veya kelimesini telaffuzu, Türkçe karşılığı ve günlük hayattan örnek cümlesiyle öğret.",
        "default_music": "lofi",
        "has_split_screen": False,
        "icon": "fa-language",
        "color_palette": "sky_blue",
        "rpm_tier": "$6-12",
        "viral_score": 78,
        "avg_retention_pct": 73,
        "competition_level": "high",
        "best_posting_time": "07:00-09:00 TRT",
        "cta_type": "save",
        "tier1_compatible": False,
        "episodic_capable": True,
        "loop_formula": "curiosity_repetition",
        "trending_keywords": ["İngilizce", "dil öğrenme", "English", "deyim", "language hack"],
        "ab_test_hook_variants": [
            "Yabancıların sürekli kullandığı ama okulda öğretilmeyen 3 kalıp!",
            "Bu 3 İngilizce deyimi bilmeden yurtdışında anlaşamazsın.",
            "Netflix dizilerinde duyup anlayamadığın o 3 ifade şimdi açıklanıyor."
        ]
    },
    "12_amazon_affiliate": {
        "id": "12_amazon_affiliate",
        "name": "Viral Ürün & Amazon/Trendyol Affiliate",
        "name_en": "Viral Amazon Finds & Gadgets",
        "category": "Ürün İnceleme & Satış",
        "tone": "enthusiastic, problem-solving",
        "hook_style": "Hayatınızı kolaylaştıracak ve 'Bunu neden daha önce almadım' diyeceğiniz 3 ürün!",
        "system_instruction": "Gündelik bir sorunu çözen viral teknolojik veya ev aletini tanıt. Özelliklerini öv ve 'Ürün linkini yorumlara bıraktım' çağrısı yap.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-bag-shopping",
        "color_palette": "amazon_yellow",
        "rpm_tier": "$8-18",
        "viral_score": 82,
        "avg_retention_pct": 69,
        "competition_level": "high",
        "best_posting_time": "19:00-22:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": False,
        "episodic_capable": False,
        "loop_formula": "secret_knowledge",
        "trending_keywords": ["amazon ürün", "trendyol", "viral gadget", "life hack ürün", "affiliate"],
        "ab_test_hook_variants": [
            "Hayatınızı kolaylaştıracak ve 'Bunu neden daha önce almadım' diyeceğiniz 3 ürün!",
            "Bu 3 ürünü görünce neden daha önce bulmadım diyeceksin.",
            "Amazon'da 50 TL'ye satılan ve hayatı kolaylaştıran o gizli ürünler."
        ]
    },
    "13_mystery_paranormal": {
        "id": "13_mystery_paranormal",
        "name": "Gizem & Paranormal / Komplo Teorileri",
        "name_en": "Mysteries & Unsolved Paranormal",
        "category": "Gizem & Korku",
        "tone": "chilling, suspenseful, dark",
        "hook_style": "Bilim insanlarının bile açıklayamadığı bu olay tüylerinizi ürpertecek...",
        "system_instruction": "Çözülememiş bir gizemi, 51. Bölge, Bermuda Şeytan Üçgeni veya tarihteki açıklanamayan kayboluşları gerilim dolu bir kurguyla aktar.",
        "default_music": "mysterious",
        "has_split_screen": False,
        "icon": "fa-ghost",
        "color_palette": "dark_mystery",
        "rpm_tier": "$4-9",
        "viral_score": 90,
        "avg_retention_pct": 81,
        "competition_level": "medium",
        "best_posting_time": "22:00-00:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "warning_loop",
        "trending_keywords": ["gizem", "paranormal", "komplo", "51. bölge", "açıklanamayan"],
        "ab_test_hook_variants": [
            "Bilim insanlarının bile açıklayamadığı bu olay tüylerinizi ürpertecek...",
            "Bu olay 50 yıldır gizli tutuldu — bugün ortaya çıkıyor.",
            "NASA bunu açıklamak istemedi. Peki neden?"
        ]
    },
    "14_movie_summaries": {
        "id": "14_movie_summaries",
        "name": "Film & Dizi Tavsiyeleri / Ters Köşe",
        "name_en": "Plot Twist Movie Recommendations",
        "category": "Sinema & Dizi",
        "tone": "cinematic, engaging",
        "hook_style": "Sonunu asla tahmin edemeyeceğiniz ve beyin yakan 3 ters köşe film!",
        "system_instruction": "Spoiler vermeden 2-3 filmin ilgi çekici konusunu ve neden izlenmesi gerektiğini anlat. Finalde 'Sizce en iyi ters köşe film hangisi?' diye sor.",
        "default_music": "dramatic",
        "has_split_screen": False,
        "icon": "fa-film",
        "color_palette": "cinema_dark",
        "rpm_tier": "$3-7",
        "viral_score": 85,
        "avg_retention_pct": 76,
        "competition_level": "high",
        "best_posting_time": "20:00-23:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": False,
        "loop_formula": "plot_twist_reset",
        "trending_keywords": ["film önerisi", "ters köşe film", "izlenecek film", "dizi tavsiye", "plot twist"],
        "ab_test_hook_variants": [
            "Sonunu asla tahmin edemeyeceğiniz ve beyin yakan 3 ters köşe film!",
            "Bu 3 filmin sonunu bilen varsa konuşalım — kimse bilemedi.",
            "Bu geceyi bu 3 filmle geçirirsen sabaha kadar uyanık kalırsın."
        ]
    },
    "15_football_transfers": {
        "id": "15_football_transfers",
        "name": "Futbol & Transfer Dedikoduları",
        "name_en": "Football & Transfer Rumors",
        "category": "Spor & Futbol",
        "tone": "hype, fast, passionate",
        "hook_style": "Bomba transfer patladı! Yıldız oyuncu imzayı atıyor!",
        "system_instruction": "Süper Lig veya Avrupa'dan en çok konuşulan transfer dedikodularını, bonservis bedellerini ve oyuncu istatistiklerini yüksek enerjiyle anlat.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-futbol",
        "color_palette": "grass_green",
        "rpm_tier": "$3-7",
        "viral_score": 87,
        "avg_retention_pct": 72,
        "competition_level": "high",
        "best_posting_time": "12:00-14:00 & 22:00-00:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": False,
        "episodic_capable": False,
        "loop_formula": "time_reset",
        "trending_keywords": ["transfer haberi", "futbol", "Süper Lig", "Şampiyonlar Ligi", "bonservis"],
        "ab_test_hook_variants": [
            "Bomba transfer patladı! Yıldız oyuncu imzayı atıyor!",
            "Bu transfer gerçekleşirse lig dengesi tamamen bozulacak!",
            "Kulübün kasasını boşaltan o bomba teklif şimdi açıklandı."
        ]
    },
    "16_wealth_entrepreneurship": {
        "id": "16_wealth_entrepreneurship",
        "name": "Zenginlik & Girişimcilik Hikayeleri",
        "name_en": "Wealth & Entrepreneurship Secrets",
        "category": "İş Dünyası & Başarı",
        "tone": "inspirational, ambitious",
        "hook_style": "Sıfırdan milyarder olan bu adamın kimsenin bilmediği 1 numaralı kuralı!",
        "system_instruction": "Başarılı bir girişimcinin kriz anında aldığı radikal kararı ve bu kararın onu nasıl milyarder yaptığını hikayeleştir.",
        "default_music": "epic",
        "has_split_screen": False,
        "icon": "fa-chart-line",
        "color_palette": "gold_success",
        "rpm_tier": "$18-35",
        "viral_score": 92,
        "avg_retention_pct": 83,
        "competition_level": "medium",
        "best_posting_time": "07:00-09:00 TRT",
        "cta_type": "save",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "secret_knowledge",
        "trending_keywords": ["girişimcilik", "zenginlik", "milyarder", "başarı sırrı", "entrepreneur"],
        "ab_test_hook_variants": [
            "Sıfırdan milyarder olan bu adamın kimsenin bilmediği 1 numaralı kuralı!",
            "Bu şirketi 100$'a kurdu, 100 milyon$'a sattı — işte o sır.",
            "Başarılıların sabah 5'te yaptığı ve sana söylemediği şey."
        ]
    },
    "17_before_after_evolution": {
        "id": "17_before_after_evolution",
        "name": "Zamanın Evrimi: Before vs After",
        "name_en": "Evolution: Before vs After",
        "category": "Tarih & Teknoloji",
        "tone": "nostalgic, contrastive",
        "hook_style": "100 yıl önce hayat nasıldı, şimdi nasıl? Farkı görünce inanamayacaksınız!",
        "system_instruction": "Teknolojilerin, şehirlerin veya mesleklerin geçmişiyle günümüzü karşılaştır. Görsel kontrastlara vurgu yap.",
        "default_music": "calm",
        "has_split_screen": False,
        "icon": "fa-clock-rotate-left",
        "color_palette": "sepia_nostalgia",
        "rpm_tier": "$4-8",
        "viral_score": 77,
        "avg_retention_pct": 72,
        "competition_level": "low",
        "best_posting_time": "14:00-17:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": False,
        "loop_formula": "time_reset",
        "trending_keywords": ["before after", "zaman makinesi", "100 yıl önce", "evrim", "then vs now"],
        "ab_test_hook_variants": [
            "100 yıl önce hayat nasıldı, şimdi nasıl? Farkı görünce inanamayacaksınız!",
            "1920'den 2024'e — bu değişim sizi şok edecek.",
            "Atalarımız bunu görse ne derdi? Zaman inanılmaz değişti."
        ]
    },
    "18_astrology_horoscope": {
        "id": "18_astrology_horoscope",
        "name": "Astroloji & Günlük Burç Yorumları",
        "name_en": "Astrology & Zodiac Rankings",
        "category": "Astroloji & Yaşam",
        "tone": "mystical, intriguing",
        "hook_style": "Bu hafta talihi dönecek ve paraya boğulacak en şanslı 3 burç!",
        "system_instruction": "Burçların aşk, para ve kariyer durumlarını sırala. Dinleyicinin kendi burcunu yorumlara yazmasını teşvik et.",
        "default_music": "mysterious",
        "has_split_screen": False,
        "icon": "fa-star",
        "color_palette": "galaxy_purple",
        "rpm_tier": "$3-6",
        "viral_score": 89,
        "avg_retention_pct": 80,
        "competition_level": "medium",
        "best_posting_time": "09:00-11:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": False,
        "episodic_capable": True,
        "loop_formula": "curiosity_repetition",
        "trending_keywords": ["burç yorumu", "astroloji", "zodiac", "haftalık burç", "şanslı burç"],
        "ab_test_hook_variants": [
            "Bu hafta talihi dönecek ve paraya boğulacak en şanslı 3 burç!",
            "Kendi burcunu gör ve bu hafta seni bekleyeni öğren.",
            "Astrologlar uyarıyor: Bu 3 burç için kritik hafta başladı!"
        ]
    },
    "19_historical_battles": {
        "id": "19_historical_battles",
        "name": "Tarihi Savaşlar & Kritik Anlar",
        "name_en": "Epic Historical Battles & Tactics",
        "category": "Tarih & Askeri",
        "tone": "heroic, intense, tactical",
        "hook_style": "Tarihin kaderini değiştiren sadece 10 dakikalık o stratejik hata!",
        "system_instruction": "Tarihin en ünlü muharebelerinden birinin dönüm noktasını askeri taktikler ve komutanların cesareti üzerinden anlat.",
        "default_music": "epic",
        "has_split_screen": False,
        "icon": "fa-shield-halved",
        "color_palette": "war_crimson",
        "rpm_tier": "$6-14",
        "viral_score": 88,
        "avg_retention_pct": 81,
        "competition_level": "low",
        "best_posting_time": "16:00-20:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "time_reset",
        "trending_keywords": ["tarihi savaş", "Osmanlı", "tarihi dönüm noktası", "savaş taktikleri", "history battle"],
        "ab_test_hook_variants": [
            "Tarihin kaderini değiştiren sadece 10 dakikalık o stratejik hata!",
            "Bu savaşı kim kazandı? Cevap sandığınız gibi değil.",
            "O gün o karar alınmasaydı bugün dünya tamamen farklı olurdu."
        ]
    },
    "20_whatsapp_chat_story": {
        "id": "20_whatsapp_chat_story",
        "name": "WhatsApp / Mesajlaşma İtirafları",
        "name_en": "Text Message Drama Story",
        "category": "Drama & Mizah",
        "tone": "suspenseful, informal",
        "hook_style": "Eski sevgilisinden gelen mesaja verdiği cevap interneti yıktı!",
        "system_instruction": "İki kişi arasında geçen komik veya şok edici mesajlaşma diyaloglarını senaryolaştır.",
        "default_music": "lofi",
        "has_split_screen": True,
        "icon": "fa-comment-dots",
        "color_palette": "whatsapp_green",
        "rpm_tier": "$2-5",
        "viral_score": 91,
        "avg_retention_pct": 84,
        "competition_level": "medium",
        "best_posting_time": "22:00-01:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": False,
        "episodic_capable": True,
        "loop_formula": "plot_twist_reset",
        "trending_keywords": ["whatsapp drama", "mesaj hikayesi", "chat story", "eski sevgili mesaj", "itiraf mesajı"],
        "ab_test_hook_variants": [
            "Eski sevgilisinden gelen mesaja verdiği cevap interneti yıktı!",
            "Bu mesajlaşmayı okuyunca ne düşündüğünü yoruma yaz.",
            "3 yıllık ilişkiyi bir mesajla bitirdi — işte o konuşma."
        ]
    },
    "21_ai_tools_hacks": {
        "id": "21_ai_tools_hacks",
        "name": "Yapay Zeka Araçları & Gizli Siteler",
        "name_en": "Illegal AI Tools & Useful Websites",
        "category": "Teknoloji & Yapay Zeka",
        "tone": "hacky, enthusiastic, valuable",
        "hook_style": "Kullanması yasadışı hissettiren ama tamamen ücretsiz 3 yapay zeka sitesi!",
        "system_instruction": "İş yükünü hafifleten, tasarım, metin veya ses üreten 3 pratik AI aracını adım adım göster.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-robot",
        "color_palette": "cyber_blue",
        "rpm_tier": "$12-25",
        "viral_score": 96,
        "avg_retention_pct": 86,
        "competition_level": "medium",
        "best_posting_time": "10:00-13:00 TRT",
        "cta_type": "save",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "secret_knowledge",
        "trending_keywords": ["yapay zeka", "AI tools", "ücretsiz AI", "ChatGPT", "gizli site"],
        "ab_test_hook_variants": [
            "Kullanması yasadışı hissettiren ama tamamen ücretsiz 3 yapay zeka sitesi!",
            "Bu 3 AI sitesini bilen işini 10 kat hızlandırıyor.",
            "Google bile bu 3 yapay zeka sitesini kapatmak istedi — işte nedeni."
        ]
    },
    "22_emoji_guess_game": {
        "id": "22_emoji_guess_game",
        "name": "Emoji ile Film / Şarkı Tahmin",
        "name_en": "Guess the Movie by Emojis",
        "category": "Quiz & Eğlence",
        "tone": "playful, fast",
        "hook_style": "Bu 3 emojiden hangi efsane filmi anlattığımızı bulabilir misin?",
        "system_instruction": "Emoji ipuçları ver, izleyiciye 5 saniye sayaç tanı, ardından doğru cevabı patlat.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-icons",
        "color_palette": "emoji_yellow",
        "rpm_tier": "$2-5",
        "viral_score": 83,
        "avg_retention_pct": 79,
        "competition_level": "low",
        "best_posting_time": "17:00-21:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "challenge_accepted",
        "trending_keywords": ["emoji quiz", "film tahmin", "emoji oyunu", "guess the movie", "eğlence quiz"],
        "ab_test_hook_variants": [
            "Bu 3 emojiden hangi efsane filmi anlattığımızı bulabilir misin?",
            "5 saniyede tahmin et — %90 yanlış biliyor!",
            "Sadece gerçek sinema tutkunları bu emojileri çözebilir."
        ]
    },
    "23_fitness_nutrition_hacks": {
        "id": "23_fitness_nutrition_hacks",
        "name": "Fitness & Hızlı Yağ Yakma Tüyoları",
        "name_en": "Quick Fitness & Fat Loss Hacks",
        "category": "Sağlık & Spor",
        "tone": "motivational, scientific, direct",
        "hook_style": "Göbek yağlarını eritmek için spordan önce yapmanız gereken 1 basit kural!",
        "system_instruction": "Halk arasında doğru bilinen bir fitness hatasını düzeltip, bilimsel ve pratik bir egzersiz/beslenme ipucu sun.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-dumbbell",
        "color_palette": "fit_orange",
        "rpm_tier": "$8-16",
        "viral_score": 87,
        "avg_retention_pct": 78,
        "competition_level": "high",
        "best_posting_time": "06:00-08:00 & 17:00-19:00 TRT",
        "cta_type": "save",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "warning_loop",
        "trending_keywords": ["yağ yakma", "fitness", "spor tüyoları", "diyet", "kilo verme"],
        "ab_test_hook_variants": [
            "Göbek yağlarını eritmek için spordan önce yapmanız gereken 1 basit kural!",
            "Bu beslenme hatasını yapıyorsanız ne kadar spor yaparsanız yapın zayıflamazsınız.",
            "Bilimsel kanıtlanmış: Bu saatte yemek yemek yağ yakmayı 3 kat hızlandırıyor."
        ]
    },
    "24_sigma_character_study": {
        "id": "24_sigma_character_study",
        "name": "Karakter Analizi (Thomas Shelby / Sigma)",
        "name_en": "Sigma Character Mindset & Rules",
        "category": "Kişisel Gelişim & Karizma",
        "tone": "cold, calculated, confident",
        "hook_style": "Odaya girdiğinde herkesin saygısını kazanan erkeklerin 3 gizli kuralı...",
        "system_instruction": "Özgüven, beden dili, sessizliğin gücü ve odaklanma üzerine keskin ve net psikolojik kurallar ver.",
        "default_music": "mysterious",
        "has_split_screen": False,
        "icon": "fa-user-secret",
        "color_palette": "sigma_dark",
        "rpm_tier": "$8-18",
        "viral_score": 94,
        "avg_retention_pct": 85,
        "competition_level": "medium",
        "best_posting_time": "21:00-00:00 TRT",
        "cta_type": "save",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "cause_and_effect",
        "trending_keywords": ["sigma", "Thomas Shelby", "saygı kazanma", "özgüven", "alpha mindset"],
        "ab_test_hook_variants": [
            "Odaya girdiğinde herkesin saygısını kazanan erkeklerin 3 gizli kuralı...",
            "Thomas Shelby'nin gerçek hayatta uygulayabileceğin 3 zihin oyunu.",
            "Hiç konuşmadan otorite kuran insanların ortak 3 özelliği."
        ]
    },
    "25_celebrity_net_worth": {
        "id": "25_celebrity_net_worth",
        "name": "Ünlüler Ne Kadar Kazanıyor?",
        "name_en": "Celebrity Net Worth & Spending",
        "category": "Magazin & Para",
        "tone": "gossipy, eye-opening",
        "hook_style": "Bu ünlünün sadece 1 saatlik kazancı sıradan bir insanın 10 yıllık maaşına bedel!",
        "system_instruction": "Ünlü bir isim veya sporcunun servetini, gayrimenkullerini ve çılgın harcamalarını rakamlarla dök.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-sack-dollar",
        "color_palette": "luxury_gold",
        "rpm_tier": "$4-8",
        "viral_score": 85,
        "avg_retention_pct": 74,
        "competition_level": "medium",
        "best_posting_time": "12:00-15:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": False,
        "loop_formula": "curiosity_repetition",
        "trending_keywords": ["ünlü serveti", "net worth", "kazanç", "para harcama", "zengin ünlü"],
        "ab_test_hook_variants": [
            "Bu ünlünün sadece 1 saatlik kazancı sıradan bir insanın 10 yıllık maaşına bedel!",
            "Dünya en zengin 3 futbolcunun serveti bu rakama ulaştı.",
            "Bu parayı nasıl harcıyor? Cevap sizi şok edecek."
        ]
    },
    "26_dangerous_places": {
        "id": "26_dangerous_places",
        "name": "Dünyanın En Tehlikeli / Yasak Yerleri",
        "name_en": "Most Dangerous & Forbidden Places",
        "category": "Coğrafya & Seyahat",
        "tone": "dark, informative, thrilling",
        "hook_style": "Adımınızı attığınız an hayatınızı kaybedebileceğiniz dünyanın en yasak 3 adası!",
        "system_instruction": "Kuzey Sentinel Adası, Yılan Adası gibi girişin yasak olduğu yerlerin ürpertici hikayesini anlat.",
        "default_music": "mysterious",
        "has_split_screen": False,
        "icon": "fa-triangle-exclamation",
        "color_palette": "danger_red",
        "rpm_tier": "$5-11",
        "viral_score": 89,
        "avg_retention_pct": 82,
        "competition_level": "low",
        "best_posting_time": "21:00-23:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "warning_loop",
        "trending_keywords": ["tehlikeli yerler", "yasak bölge", "forbidden places", "ölümcül ada", "gizemli yer"],
        "ab_test_hook_variants": [
            "Adımınızı attığınız an hayatınızı kaybedebileceğiniz dünyanın en yasak 3 adası!",
            "Google haritalar bu 3 yeri bulanıklaştırıyor — işte nedeni.",
            "Buraya ayak basan son insan ne oldu? Cevap korkunç."
        ]
    },
    "27_common_myths_busted": {
        "id": "27_common_myths_busted",
        "name": "Doğru Bilinen Yanlışlar (Mit Avcısı)",
        "name_en": "Common Myths Busted",
        "category": "Bilim & Günlük Yaşam",
        "tone": "direct, eye-opening",
        "hook_style": "Çocukluğunuzdan beri doğru bildiğiniz ama tamamen yalan olan 3 bilgi!",
        "system_instruction": "Toplumda herkesin inandığı bir hurafeyi bilimsel verilerle çürüt.",
        "default_music": "calm",
        "has_split_screen": False,
        "icon": "fa-circle-xmark",
        "color_palette": "myth_buster_red",
        "rpm_tier": "$5-10",
        "viral_score": 83,
        "avg_retention_pct": 76,
        "competition_level": "low",
        "best_posting_time": "13:00-16:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": False,
        "loop_formula": "reverse_question",
        "trending_keywords": ["mit çürütme", "doğru bilinen yanlış", "hurafe", "myth busted", "bilimsel gerçek"],
        "ab_test_hook_variants": [
            "Çocukluğunuzdan beri doğru bildiğiniz ama tamamen yalan olan 3 bilgi!",
            "Öğretmenin yanlış öğretti — işte bilimsel kanıt.",
            "Milyonlarca insan bu yanlışa hala inanıyor — sen de mi?"
        ]
    },
    "28_dream_meanings": {
        "id": "28_dream_meanings",
        "name": "Rüya Tabirleri & Bilinçaltı Sırları",
        "name_en": "Psychological Dream Meanings",
        "category": "Psikoloji & Rüya",
        "tone": "mystical, psychological",
        "hook_style": "Rüyanızda yüksekten düştüğünüzü gördüyseniz bilinçaltınız size bunu haykırıyor...",
        "system_instruction": "En yaygın görülen rüyaların psikolojik ve bilinçaltı tercümelerini ilgi çekici şekilde anlat.",
        "default_music": "mysterious",
        "has_split_screen": False,
        "icon": "fa-cloud-moon",
        "color_palette": "dream_indigo",
        "rpm_tier": "$3-6",
        "viral_score": 86,
        "avg_retention_pct": 78,
        "competition_level": "low",
        "best_posting_time": "23:00-01:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": False,
        "episodic_capable": True,
        "loop_formula": "reverse_question",
        "trending_keywords": ["rüya tabiri", "bilinçaltı", "rüya anlamı", "dream meaning", "rüya psikoloji"],
        "ab_test_hook_variants": [
            "Rüyanızda yüksekten düştüğünüzü gördüyseniz bilinçaltınız size bunu haykırıyor...",
            "Bu rüyayı görenler uyanınca çok farklı bir şey hissediyor — neden?",
            "En yaygın 3 rüyanın gerçek psikolojik anlamı bugün açıklanıyor."
        ]
    },
    "29_optical_illusions_iq": {
        "id": "29_optical_illusions_iq",
        "name": "Optik İllüzyon & Zeka Testleri",
        "name_en": "Optical Illusions & Brain Teasers",
        "category": "Zeka & Eğlence",
        "tone": "challenging, quick",
        "hook_style": "İnsanların %95'i bu resimdeki gizli hayvanı 5 saniyede göremiyor!",
        "system_instruction": "Optik illüzyon veya hızlı zeka sorusu sor. Sayacı çalıştır ve cevabı açıkla.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-eye",
        "color_palette": "illusion_purple",
        "rpm_tier": "$3-6",
        "viral_score": 88,
        "avg_retention_pct": 83,
        "competition_level": "low",
        "best_posting_time": "15:00-19:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "challenge_accepted",
        "trending_keywords": ["optik illüzyon", "zeka testi", "optical illusion", "IQ test", "beyin egzersizi"],
        "ab_test_hook_variants": [
            "İnsanların %95'i bu resimdeki gizli hayvanı 5 saniyede göremiyor!",
            "IQ'n kaç? Bu testi 10 saniyede çözebilen dâhi sayılıyor.",
            "Gözlerin seni kandırıyor — ya beynin?"
        ]
    },
    "30_poetry_quotes": {
        "id": "30_poetry_quotes",
        "name": "Şiir & Edebi Aşk Sözleri",
        "name_en": "Poetry & Deep Melancholic Quotes",
        "category": "Edebiyat & Sanat",
        "tone": "emotional, slow, romantic",
        "hook_style": "İçinizdeki kırgınlıkları kelimelere döken o unutulmaz mısralar...",
        "system_instruction": "Cemal Süreya, Nazım Hikmet gibi şairlerin dokunaklı sözlerini derin bir duyguyla seslendir.",
        "default_music": "calm",
        "has_split_screen": False,
        "icon": "fa-feather-pointed",
        "color_palette": "poetry_rose",
        "rpm_tier": "$2-4",
        "viral_score": 81,
        "avg_retention_pct": 76,
        "competition_level": "low",
        "best_posting_time": "22:00-00:00 TRT",
        "cta_type": "save",
        "tier1_compatible": False,
        "episodic_capable": True,
        "loop_formula": "cause_and_effect",
        "trending_keywords": ["şiir", "aşk sözleri", "Nazım Hikmet", "Cemal Süreya", "derin söz"],
        "ab_test_hook_variants": [
            "İçinizdeki kırgınlıkları kelimelere döken o unutulmaz mısralar...",
            "Bu dizeler yüz yıldır kalpleri kavuruyor — bugün de öyle.",
            "Hiçbir zaman doğru kelimeleri bulamadınız mı? Bu şair buldu."
        ]
    },
    "31_supercars_automotive": {
        "id": "31_supercars_automotive",
        "name": "Süper Arabalar & Otomobil Tutkusu",
        "name_en": "Supercars & Automotive Beasts",
        "category": "Otomobil & Hız",
        "tone": "high-octane, roaring, technical",
        "hook_style": "0'dan 100'e sadece 1.8 saniyede çıkan bu canavar yer çekimine meydan okuyor!",
        "system_instruction": "Yeni hiper arabaların motor güçlerini, hız rekorlarını ve agresif tasarımlarını heyecanla anlat.",
        "default_music": "energetic",
        "has_split_screen": False,
        "icon": "fa-car-burst",
        "color_palette": "speed_red",
        "rpm_tier": "$10-22",
        "viral_score": 85,
        "avg_retention_pct": 77,
        "competition_level": "medium",
        "best_posting_time": "16:00-20:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": False,
        "loop_formula": "plot_twist_reset",
        "trending_keywords": ["süper araba", "hypercar", "Ferrari", "Lamborghini", "hız rekoru"],
        "ab_test_hook_variants": [
            "0'dan 100'e sadece 1.8 saniyede çıkan bu canavar yer çekimine meydan okuyor!",
            "Bu araba yasal mı? Çünkü bu performans gerçek gibi durmuyor.",
            "Fiyatına inanamayacaksın — işte dünyanın en hızlı 3 arabası."
        ]
    },
    "32_legal_consumer_hacks": {
        "id": "32_legal_consumer_hacks",
        "name": "Hukuki Haklar & Tüketici Tüyoları",
        "name_en": "Legal Rights & Everyday Law Hacks",
        "category": "Hukuk & Yaşam",
        "tone": "authoritative, protective, smart",
        "hook_style": "Polis sizi durdurursa veya bir mağaza iade almazsa bilmeniz gereken gizli hakkınız!",
        "system_instruction": "Günlük hayatta vatandaşların bilmediği tüketici ve anayasal haklarını net 3 maddede anlat.",
        "default_music": "calm",
        "has_split_screen": False,
        "icon": "fa-scale-unbalanced-flip",
        "color_palette": "law_navy",
        "rpm_tier": "$5-11",
        "viral_score": 84,
        "avg_retention_pct": 79,
        "competition_level": "low",
        "best_posting_time": "12:00-15:00 TRT",
        "cta_type": "save",
        "tier1_compatible": False,
        "episodic_capable": True,
        "loop_formula": "secret_knowledge",
        "trending_keywords": ["tüketici hakları", "hukuki hak", "kanun bilgi", "iade hakkı", "vatandaş hakkı"],
        "ab_test_hook_variants": [
            "Polis sizi durdurursa veya bir mağaza iade almazsa bilmeniz gereken gizli hakkınız!",
            "Bu 3 hakkı bilmeden sokağa çıkmayın — her an işinize yarayabilir.",
            "Avukatlar bu sırları seve seve anlatmaz — ama biz anlatıyoruz."
        ]
    },
    "33_parenting_child_hacks": {
        "id": "33_parenting_child_hacks",
        "name": "Çocuk Gelişimi & Ebeveyn Tüyoları",
        "name_en": "Parenting & Child Psychology Hacks",
        "category": "Aile & Pedagoji",
        "tone": "warm, advisory, scientific",
        "hook_style": "Çocuğunuza asla 'Aferin çok akıllısın' demeyin! İşte psikologların uyarısı...",
        "system_instruction": "Pedagojik yaklaşımlarla çocuk yetiştirirken yapılan yaygın hataları ve doğru iletişim yöntemlerini aktar.",
        "default_music": "calm",
        "has_split_screen": False,
        "icon": "fa-children",
        "color_palette": "warm_yellow",
        "rpm_tier": "$7-14",
        "viral_score": 82,
        "avg_retention_pct": 77,
        "competition_level": "low",
        "best_posting_time": "08:00-10:00 TRT",
        "cta_type": "save",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "warning_loop",
        "trending_keywords": ["ebeveynlik", "çocuk psikolojisi", "anne baba", "parenting hack", "çocuk gelişimi"],
        "ab_test_hook_variants": [
            "Çocuğunuza asla 'Aferin çok akıllısın' demeyin! İşte psikologların uyarısı...",
            "Bu cümleyi söyleyen ebeveynlerin çocukları neden daha mutsuz oluyor?",
            "Harvard araştırması: Bu 3 şeyi yapan çocuklar lider oluyor."
        ]
    },
    "34_gaming_easter_eggs": {
        "id": "34_gaming_easter_eggs",
        "name": "Oyun Sırları & Gizli Detaylar (Easter Eggs)",
        "name_en": "Video Game Secrets & Easter Eggs",
        "category": "Oyun & Gaming",
        "tone": "curious, nostalgic, gamer",
        "hook_style": "GTA veya RDR2 oynayanların %99'unun fark etmediği ürpertici detay!",
        "system_instruction": "Büyük oyunlardaki harita sırlarını, geliştirici mesajlarını veya gizemli yan görevleri anlat.",
        "default_music": "mysterious",
        "has_split_screen": True,
        "icon": "fa-puzzle-piece",
        "color_palette": "gaming_neon",
        "rpm_tier": "$5-12",
        "viral_score": 90,
        "avg_retention_pct": 83,
        "competition_level": "medium",
        "best_posting_time": "20:00-00:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "secret_knowledge",
        "trending_keywords": ["Easter egg", "oyun sırrı", "GTA sırları", "gizli detay", "game secret"],
        "ab_test_hook_variants": [
            "GTA veya RDR2 oynayanların %99'unun fark etmediği ürpertici detay!",
            "Bu oyunun haritasında 10 yıldır kimsenin göremediği sır var.",
            "Geliştiriciler bu mesajı oyuna gömdü — neden hiç bilmiyorduk?"
        ]
    },
    "35_animal_kingdom_stories": {
        "id": "35_animal_kingdom_stories",
        "name": "Hayvanlar Alemi Mikro Hikayeleri",
        "name_en": "Wild Animal Kingdom Battles & Stories",
        "category": "Vahşi Yaşam & Hayvanlar",
        "tone": "wild, dramatic, intense",
        "hook_style": "Aslanların bile yaklaşmaktan korktuğu dünyanın en çılgın hayvanı!",
        "system_instruction": "Bal porsuğu, karga hafızası veya katil balinaların akıllı av taktiklerini nefes kesici bir dille anlat.",
        "default_music": "epic",
        "has_split_screen": False,
        "icon": "fa-paw",
        "color_palette": "wild_earth",
        "rpm_tier": "$5-12",
        "viral_score": 88,
        "avg_retention_pct": 80,
        "competition_level": "low",
        "best_posting_time": "14:00-18:00 TRT",
        "cta_type": "comment",
        "tier1_compatible": True,
        "episodic_capable": True,
        "loop_formula": "infinite_cycle",
        "trending_keywords": ["vahşi hayvanlar", "hayvanlar alemi", "animal kingdom", "aslan", "doğa belgeseli"],
        "ab_test_hook_variants": [
            "Aslanların bile yaklaşmaktan korktuğu dünyanın en çılgın hayvanı!",
            "Bu küçük hayvan bir timsahı tek başına yeniyor — gerçek mi?",
            "Doğanın en akıllı 3 avı: Beyin, strateji ve sabır."
        ]
    }
}


# P1-01: competitor-format scene structures keyed by niche family
NICHE_FAMILY_MAP: Dict[str, str] = {
    "1_news_flash": "news",
    "2_reddit_confessions": "reddit",
    "6_stoic_philosophy": "stoic",
    "7_dark_psychology": "stoic",
    "8_crypto_market": "news",
    "15_football_transfers": "news",
    "16_wealth_entrepreneurship": "stoic",
    "20_whatsapp_chat_story": "whatsapp",
    "24_sigma_character_study": "stoic",
    "3_split_gameplay": "whatsapp",
}

SCENE_FORMAT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "whatsapp": {
        "tr": (
            "WHATSAPP CHAT HİKAYESİ YAPISI (rakip format — zorunlu):\n"
            "- Sahne 1: Ekranda beliren şok mesaj kancası (\"Bu mesaj her şeyi değiştirdi...\").\n"
            "- Sahne 2-11: İki kişi arası mesajlaşma akışı; her sahne bir balon diyaloğu veya tepki anı.\n"
            "  narration'da gönderen/alıcı konuşma tonu kullan; scene_description'da \"smartphone chat screen\", "
            "\"WhatsApp green bubble UI\", \"typing indicator\" belirt.\n"
            "- Sahne 12-13: Twist mesajı ve duygusal doruk.\n"
            "- Sahne 14: Döngü + \"Sen ne yapardın?\" yorum sorusu.\n"
            "YASAK: Haber bülteni, SON DAKİKA veya üç madde listesi formatı kullanma."
        ),
        "en": (
            "WHATSAPP CHAT STORY STRUCTURE (competitor format — mandatory):\n"
            "- Scene 1: Shocking on-screen message hook.\n"
            "- Scenes 2-11: Alternating chat bubbles between two people; each scene = one message or reaction beat.\n"
            "  Use conversational narration; scene_description must reference smartphone chat UI / green bubbles.\n"
            "- Scenes 12-13: Twist message and emotional peak.\n"
            "- Scene 14: Seamless loop + \"What would you do?\" comment trigger.\n"
            "FORBIDDEN: Breaking news bulletin or numbered rules list format."
        ),
    },
    "reddit": {
        "tr": (
            "REDDIT / AITA İTİRAF YAPISI (rakip format — zorunlu):\n"
            "- Sahne 1: Birinci tekil şahıs itiraf kancası (\"Hayatımın en büyük hatasını yaptım...\" / \"AITA?\").\n"
            "- Sahne 2-11: 'Ben' anlatımıyla kronolojik olay örgüsü — kurulum, çatışma, gerilim, twist.\n"
            "- Sahne 12-13: Ahlaki ikilem ve pişmanlık / sonuç.\n"
            "- Sahne 14: \"Ben mi hatalıyım?\" sorusu + döngü.\n"
            "Tüm narration birinci tekil ('ben') olmalı. Haber bülteni veya chat balonu formatı kullanma."
        ),
        "en": (
            "REDDIT / AITA CONFESSION STRUCTURE (competitor format — mandatory):\n"
            "- Scene 1: First-person confession hook (\"I made the biggest mistake...\" / \"AITA?\").\n"
            "- Scenes 2-11: Chronological story arc in first person — setup, conflict, tension, twist.\n"
            "- Scenes 12-13: Moral dilemma and consequence.\n"
            "- Scene 14: \"Am I the asshole?\" debate trigger + seamless loop.\n"
            "All narration MUST be first-person. No breaking news or chat bubble format."
        ),
    },
    "stoic": {
        "tr": (
            "STOACI 3 KURAL LİSTESİ YAPISI (rakip format — zorunlu):\n"
            "- Sahne 1: Filozof alıntısı veya modern hayat kancası (Marcus Aurelius / Seneca / Epiktetos).\n"
            "- Sahne 2-4: KURAL 1 — ilke + günlük hayata uygulama örneği.\n"
            "- Sahne 5-7: KURAL 2 — ilke + uygulama.\n"
            "- Sahne 8-10: KURAL 3 — ilke + uygulama.\n"
            "- Sahne 11-13: Üç kuralı birleştiren disiplin mesajı.\n"
            "- Sahne 14: Döngü + izleyici öz-yansıtma sorusu.\n"
            "YASAK: SON DAKİKA, flaş haber, haber bülteni, üç anahtar gelişme formatı. Bu bir felsefe/rehber videosu."
        ),
        "en": (
            "STOIC 3-RULES LIST STRUCTURE (competitor format — mandatory):\n"
            "- Scene 1: Philosopher quote hook or modern-life pain point.\n"
            "- Scenes 2-4: RULE 1 — principle + daily application.\n"
            "- Scenes 5-7: RULE 2 — principle + application.\n"
            "- Scenes 8-10: RULE 3 — principle + application.\n"
            "- Scenes 11-13: Synthesis — how all three rules build discipline.\n"
            "- Scene 14: Seamless loop + self-reflection question.\n"
            "FORBIDDEN: Breaking news, flash bulletin, or \"three key facts\" news format. This is philosophy/guidance."
        ),
    },
    "news": {
        "tr": (
            "FLAŞ HABER YAPISI (rakip format — zorunlu):\n"
            "- Sahne 1: SON DAKİKA kancası — acil, dikkat çekici, konuya doğrudan gir.\n"
            "- Sahne 2-4: Kilit bilgi 1 (ne oldu?).\n"
            "- Sahne 5-7: Kilit bilgi 2 (kim / nerede?).\n"
            "- Sahne 8-10: Kilit bilgi 3 (neden önemli?).\n"
            "- Sahne 11-13: Etki analizi veya sonraki adım.\n"
            "- Sahne 14: İzleyici görüşü sorusu + döngü.\n"
            "Ton: acil, faktüel, dramatik. Chat hikayesi veya itiraf formatı kullanma."
        ),
        "en": (
            "BREAKING NEWS FLASH STRUCTURE (competitor format — mandatory):\n"
            "- Scene 1: BREAKING hook — urgent, direct entry.\n"
            "- Scenes 2-4: Key fact 1 (what happened?).\n"
            "- Scenes 5-7: Key fact 2 (who / where?).\n"
            "- Scenes 8-10: Key fact 3 (why it matters?).\n"
            "- Scenes 11-13: Impact analysis or next steps.\n"
            "- Scene 14: Viewer opinion question + loop.\n"
            "Tone: urgent, factual, dramatic. No chat story or confession format."
        ),
    },
}


def get_niche_family(niche_key: str) -> str:
    """Returns panel/format family for a niche (news, reddit, whatsapp, stoic, general)."""
    return NICHE_FAMILY_MAP.get(niche_key, "general")


def get_niche_scene_structure(niche_key: str, language: str = "tr") -> str:
    """P1-01: competitor-format scene structure block for generator prompt."""
    family = get_niche_family(niche_key)
    lang = "tr" if language == "tr" else "en"
    templates = SCENE_FORMAT_TEMPLATES.get(family)
    if not templates:
        return ""
    return templates.get(lang, templates.get("tr", ""))


def get_niche_prompt(niche_key: str, topic: str, language: str = "tr") -> str:
    """
    Constructs a highly optimized prompt embedding:
    - Niche specialized instructions
    - Item 37: 3-second Viral Hook rules
    - Item 81: Seamless Loop structure
    - Item 82: Controversial question / discussion trigger
    - Item 93: Text density bounds (max 3-4 words per flash)
    - Item 96: Call to Action (CTA) question closing
    """
    niche = NICHES.get(niche_key, NICHES["1_news_flash"])
    is_tr = (language == "tr")
    scene_structure = get_niche_scene_structure(niche_key, language)

    if is_tr:
        prompt = f"""Sen profesyonel bir YouTube Shorts algoritma uzmanı ve viral senaristsin.
KONU: "{topic}"
NİŞ KATEGORİSİ: "{niche['name']}" ({niche['category']})
ANLATIM TONU: {niche['tone']}

ZORUNLU ALGORİTMA VE SAHNE KURALLARI:
1. CADENCE 14 VE SÜRE KURALI (Madde 88 & 494):
   TAM OLARAK 14 SAHNE ÜRET (scenes dizisinde tam 14 eleman olmalı).
   Her sahnenin "duration" değerini SEN belirle (2.0–4.5 sn arası, doğal tempo).
   Toplam video süresi 38-48 saniye olmalıdır. 3.2 sn sabit kural YOK — AI pacing karar verir.
   Her sahneye "beat_type" ata: hook / conflict / climax / resolution / shock.
   "mood" etiketi kullan: URGENT, DRAMATIC, EPIC, CALM, MYSTERIOUS vb.

2. TAM VE AKICI CÜMLE KURALI (KRİTİK):
   Her sahnenin 'narration' alanı 1-2 TAM, dilbilgisel olarak EKSİKSİZ Türkçe cümle olmalıdır.
   Drama/itiraf nişlerinde sahne başına en az 8-12 kelime; diğer nişlerde en az 6 kelime.
   Cümleleri ASLA yarım bırakma! Fiil ortasında ASLA kesme!
   YASAK bitişler: "ilan.", "et.", "de.", "ki.", "ve.", "için.", "olarak." — bunlar bir sonraki sahneye taşınmamalı.
   YASAK başlangıçlar: "Etti", "Ediyor", "Oldu" gibi devam fiili — her sahne kendi başına anlamlı olmalı.
   14 sahne baştan sona tam ve sürükleyici bir çatışma/olay akışı sunmalıdır.
   Her sahneye izleyicinin dikkatini canlı tutacak 1-2 adet ilgili EMOJİ ekle.

3. İLK 3 SANİYE KANCASI (VIRAL HOOK - Sahne 1):
   İlk sahne doğrudan konuya giren, merak uyandırıcı şok edici bir kanca cümlesi olmalı.
   Örnek Hook tarzı: "{niche['hook_style']}"

4. SONSUZ DÖNGÜ, TARTIŞMA VE CTA (SEAMLESS LOOP - Sahne 14):
   14. sahnenin son cümlesi, 1. sahnenin başına kesintisiz bağlanan bir döngü ve izleyicileri yoruma davet eden bir soru içermelidir!

5. STOK VİDEO VE GÖRSEL BAĞLAMI:
   - "scene_description": Sahne için İngilizce net görsel tasviri (Pexels video araması için).
   - "search_queries": 3 adet İngilizce stok video arama terimi [spesifik, orta, genel]. Asla Türkçe kelime koyma!

NİŞ ÖZEL TALİMATI:
{niche['system_instruction']}
{f'''
RAKİP FORMAT SAHNE YAPISI:
{scene_structure}
''' if scene_structure else ''}
SADECE VE SADECE GEÇERLİ JSON DÖNDÜR (Tam 14 sahne içermelidir):
{{
  "niche_id": "{niche['id']}",
  "title": "Çarpıcı YouTube Shorts Başlığı (#Shorts dahil)",
  "viral_hook": "İlk 3 saniye kancası",
  "seamless_loop_ending": "İlk cümleye bağlanan son cümle",
  "discussion_trigger": "Yorum yaptırma sorusu",
  "full_narration": "Tüm konuşma metni",
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "İlk sahne kancası ve emojiler...",
      "scene_description": "Clear visual description in English",
      "search_queries": ["specific english query", "medium query", "general query"],
      "duration": 3.0,
      "mood": "{niche['default_music']}"
    }}
  ]
}}"""
    else:
        prompt = f"""You are a professional YouTube Shorts algorithm expert and viral scriptwriter.
TOPIC: "{topic}"
NICHE CATEGORY: "{niche['name_en']}" ({niche['category']})
TONE OF VOICE: {niche['tone']}

MANDATORY ALGORITHM & SCENE RULES:
1. CADENCE 14 & DURATION RULE:
   Generate EXACTLY 14 SCENES (array of exactly 14 scene objects).
   YOU assign each scene "duration" (2.0–4.5s, natural pacing). Total 38-48 seconds.
   Assign "beat_type" (hook/conflict/climax/resolution/shock) and "mood" per scene.

2. COMPLETE SENTENCES (CRITICAL):
   Each scene "narration" must be 1-2 complete, self-contained grammatically sound sentences (8-16 words for drama).
   NEVER end mid-verb or start with a continuation fragment ("Etti", "Ediyor").
   Embed 1-2 relevant emojis naturally in each scene.

3. FIRST 3-SECOND VIRAL HOOK (Scene 1):
   Hook the viewer immediately. Reference: "{niche['hook_style']}"

4. SEAMLESS LOOP & CTA (Scene 14):
   Last scene must flow seamlessly back into Scene 1 and ask a debate question.

5. STOCK VIDEO QUERIES:
   - "scene_description": Precise visual depiction in English.
   - "search_queries": 3 concise English search keywords [specific, medium, general].

NICHE SPECIFIC INSTRUCTION:
{niche['system_instruction']}
{f'''
COMPETITOR FORMAT SCENE STRUCTURE:
{scene_structure}
''' if scene_structure else ''}
RETURN ONLY VALID JSON (with exactly 14 scenes):
{{
  "niche_id": "{niche['id']}",
  "title": "Viral YouTube Shorts Title (#Shorts included)",
  "viral_hook": "First 3s hook",
  "seamless_loop_ending": "Ending connecting to start",
  "discussion_trigger": "Comment trigger question",
  "full_narration": "Full narration text",
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "Scene narration with emojis...",
      "scene_description": "Clear visual description in English",
      "search_queries": ["query1", "query2", "query3"],
      "duration": 3.0,
      "mood": "{niche['default_music']}"
    }}
  ]
}}"""
    return prompt


def list_all_niches() -> List[Dict[str, Any]]:
    """Returns full metadata of all 35 niches including advanced analytics fields."""
    return [
        {
            "id": k,
            "name": v["name"],
            "name_en": v["name_en"],
            "category": v["category"],
            "tone": v["tone"],
            "has_split_screen": v.get("has_split_screen", False),
            # Advanced analytics fields
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

    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    music_terms = {
        "dramatic": "dramatic", "mysterious": "mysterious", "lofi": "lofi",
        "energetic": "energetic", "epic": "epic"
    }
    profile: Dict[str, Any] = {
        "id": niche["id"],
        "name": niche["name"],
        "category": niche["category"],
        "tone": niche["tone"],
        "hook_style": niche["hook_style"],
        "rpm_tier": niche.get("rpm_tier", "$2-5"),
        "viral_score": niche.get("viral_score", 75),
        "avg_retention_pct": niche.get("avg_retention_pct", 70),
        "competition_level": niche.get("competition_level", "medium"),
        "tier1_compatible": niche.get("tier1_compatible", False),
        "production_rules": {
            "split_screen": niche.get("has_split_screen", False),
            "ken_burns": True,
            "subtitle_preset": "red_fire" if niche.get("default_music") == "dramatic" else "capcut_yellow",
            "music_keyword": music_terms.get(niche.get("default_music"), "ambient"),
            "use_dynamic_motion": True,
            "use_progress_bar": True,
            "voice_style": niche["tone"]
        },
    }
    # P0-07: stoic/calm niches — lighter audio publish profile
    if niche_id == "6_stoic_philosophy":
        profile["effect_manifest_overrides"] = dict(STOIC_EFFECT_MANIFEST_OVERRIDES)
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
