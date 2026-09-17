"""
Niche Templates & Viral Hook Prompt Engine
Defines 35 custom niche templates, hooks, seamless loop rules, discussion triggers, and Tier-1 translation prompts.
Covers items: 1-35, 36, 37, 73, 81, 82, 84, 90, 93, 96 from r10_shorts_fikirleri_ve_bot_ozellikleri.md
"""
from typing import Dict, Any, List

# 35 Niching definitions with category, description, and custom instructions
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
        "has_split_screen": False
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
        "has_split_screen": True
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
        "has_split_screen": True
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": True
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": False
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
        "has_split_screen": True
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
        "has_split_screen": False
    }
}

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
    
    if is_tr:
        prompt = f"""Sen profesyonel bir YouTube Shorts algoritma uzmanı ve viral senaristsin.
KONU: "{topic}"
NİŞ KATEGORİSİ: "{niche['name']}" ({niche['category']})
ANLATIM TONU: {niche['tone']}

ZORUNLU ALGORİTMA KURALLARI:
1. İLK 3 SANİYE KANCASI (VIRAL HOOK):
   İlk cümle şok edici, aşırı merak uyandırıcı ve doğrudan izleyiciye hitap etmeli.
   Örnek Hook tarzı: "{niche['hook_style']}"

2. SONSUZ DÖNGÜ (SEAMLESS LOOP - Madde 81):
   Videonun EN SON cümlesi, EN BAŞTAKİ ilk cümlenin öznesi veya başlangıcı ile kesintisiz bağlanmalı!
   İzleyici video bittiğinde yeniden başladığını fark etmemeli, döngü hissi vermelidir.

3. TARTIŞMA & YORUM TETİKLEYİCİ (Madde 82):
   Senaryonun ortasında veya sonunda insanların yoruma koşmasını sağlayacak tartışmalı bir soru veya tezat unsur yer almalı.

4. METİN VE SAHNE YOĞUNLUĞU (Madde 93):
   10-14 sahne oluştur. Her sahne 5-7 saniye sürmeli. Toplam süre 60-80 saniye olmalı.
   Her sahnenin 'narration' kısmı akıcı, anlamlı, tam ve dilbilgisel olarak eksiksiz bir cümle olmalıdır (10-15 kelime).
   Cümleleri asla yarım bırakma veya anlamsız kelime öbeklerine bölme; her sahne mantıklı ve konuyla doğrudan ilgili bir gerçeği veya adımı anlatsın.
   İzleyicinin dikkatini canlı tutmak için her sahneye 1-2 adet ilgili EMOJİ ekle.

5. SORU İLE BİTİRME (CTA - Madde 96):
   Videonun kapanışına doğru izleyiciye 'Peki sen olsaydın ne yapardın?' veya 'Senin favorin hangisi?' gibi doğrudan bir soru yönelt.

6. STOK VİDEO VE GÖRSEL BAĞLAMI:
   - "scene_description": Sahne için İngilizce net görsel tasviri.
   - "search_queries": 3 adet İngilizce stok video arama terimi [spesifik, orta, genel].

NİŞ ÖZEL TALİMATI:
{niche['system_instruction']}

SADECE VE SADECE GEÇERLİ JSON DÖNDÜR:
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
      "narration": "Sahne metni ve emojiler...",
      "scene_description": "Clear visual description in English",
      "search_queries": ["query1", "query2", "query3"],
      "duration": 6,
      "mood": "{niche['default_music']}"
    }}
  ]
}}"""
    else:
        prompt = f"""You are a professional YouTube Shorts algorithm expert and viral scriptwriter.
TOPIC: "{topic}"
NICHE CATEGORY: "{niche['name_en']}" ({niche['category']})
TONE OF VOICE: {niche['tone']}

MANDATORY ALGORITHM RULES:
1. FIRST 3-SECOND VIRAL HOOK (Item 37):
   The first sentence must be high-voltage curiosity, shocking, and hook the viewer immediately.
   Reference hook: "{niche['hook_style']}"

2. SEAMLESS LOOP STRUCTURE (Item 81):
   The VERY LAST sentence must flow effortlessly into the VERY FIRST sentence of the video so viewers watch it twice.

3. DISCUSSION & COMMENT TRIGGER (Item 82):
   Include a provocative or debatable question designed to trigger debate in the comments.

4. SCENE PACING & TEXT DENSITY (Item 93):
   Generate 10-14 scenes (5-7s each). Total length 60-80 seconds.
   Each scene narration must be a complete, grammatically sound, coherent and meaningful sentence (10-15 words).
   NEVER truncate or split sentences mid-clause. Every scene must convey a crisp, fascinating, on-topic insight.
   Embed 1-2 relevant EMOJIS naturally.

5. CTA QUESTION CLOSING (Item 96):
   Ask a closing question driving immediate viewer replies.

6. STOCK VIDEO MAPPING:
   - "scene_description": Precise visual depiction in English.
   - "search_queries": 3 concise English search keywords [specific, medium, general].

NICHE SPECIFIC INSTRUCTION:
{niche['system_instruction']}

RETURN ONLY VALID JSON:
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
      "duration": 6,
      "mood": "{niche['default_music']}"
    }}
  ]
}}"""
    return prompt

def list_all_niches() -> List[Dict[str, Any]]:
    """Returns metadata of all 35 niches for the web dashboard and CLI."""
    return [
        {
            "id": k,
            "name": v["name"],
            "name_en": v["name_en"],
            "category": v["category"],
            "tone": v["tone"],
            "has_split_screen": v.get("has_split_screen", False)
        }
        for k, v in NICHES.items()
    ]


def get_niche_production_profile(niche_id: str) -> Dict[str, Any]:
    """Returns the settings that the renderer should apply for a selected niche."""
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    music_terms = {
        "dramatic": "dramatic", "mysterious": "mysterious", "lofi": "lofi",
        "energetic": "energetic", "epic": "epic"
    }
    return {
        "id": niche["id"],
        "name": niche["name"],
        "category": niche["category"],
        "tone": niche["tone"],
        "hook_style": niche["hook_style"],
        "production_rules": {
            "split_screen": niche.get("has_split_screen", False),
            "ken_burns": True,
            "subtitle_preset": "red_fire" if niche.get("default_music") == "dramatic" else "capcut_yellow",
            "music_keyword": music_terms.get(niche.get("default_music"), "ambient"),
            "use_dynamic_motion": True,
            "use_progress_bar": True,
            "voice_style": niche["tone"]
        }
    }
