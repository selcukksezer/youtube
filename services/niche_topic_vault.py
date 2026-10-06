# -*- coding: utf-8 -*-
"""Comprehensive curated viral topic vault for all 37 YouTube Shorts niches.

Provides rich, authentic, high-CTR, psychological-hook topic pools tested for Shorts engagement.
Eliminates generic boilerplate and repetitive cliches.
"""
from __future__ import annotations
from typing import Dict, List

# Mapping from common plan/director aliases to canonical NICHES keys
NICHE_ALIASES: Dict[str, str] = {
    "1_news_flash": "1_news_flash",
    "news": "1_news_flash",
    "2_reddit_confessions": "2_reddit_confessions",
    "reddit": "2_reddit_confessions",
    "11_reddit_stories": "2_reddit_confessions",
    "3_split_gameplay": "3_split_gameplay",
    "split": "3_split_gameplay",
    "4_would_you_rather": "4_would_you_rather",
    "quiz": "4_would_you_rather",
    "5_guess_flag_country": "5_guess_flag_country",
    "flag": "5_guess_flag_country",
    "6_stoic_philosophy": "6_stoic_philosophy",
    "stoic": "6_stoic_philosophy",
    "2_philosophy_stoic": "6_stoic_philosophy",
    "philosophy": "6_stoic_philosophy",
    "7_dark_psychology": "7_dark_psychology",
    "6_psychology_tricks": "7_dark_psychology",
    "psychology": "7_dark_psychology",
    "8_crypto_market": "8_crypto_market",
    "13_crypto_finance": "8_crypto_market",
    "crypto": "8_crypto_market",
    "9_five_facts": "9_five_facts",
    "facts": "9_five_facts",
    "7_space_cosmos": "9_five_facts",
    "10_religious_quotes": "10_religious_quotes",
    "16_islamic_wisdom": "10_religious_quotes",
    "islamic": "10_religious_quotes",
    "hadis": "10_religious_quotes",
    "hadith": "10_religious_quotes",
    "ayet": "10_religious_quotes",
    "hadisler": "10_religious_quotes",
    "11_language_learning": "11_language_learning",
    "english": "11_language_learning",
    "12_amazon_affiliate": "12_amazon_affiliate",
    "affiliate": "12_amazon_affiliate",
    "amazon": "12_amazon_affiliate",
    "13_mystery_paranormal": "13_mystery_paranormal",
    "14_mysterious_cases": "13_mystery_paranormal",
    "mystery": "13_mystery_paranormal",
    "3_bizarre_history": "13_mystery_paranormal",
    "14_movie_summaries": "14_movie_summaries",
    "movie": "14_movie_summaries",
    "15_football_transfers": "15_football_transfers",
    "football": "15_football_transfers",
    "16_wealth_entrepreneurship": "16_wealth_entrepreneurship",
    "5_luxury_lifestyle": "16_wealth_entrepreneurship",
    "wealth": "16_wealth_entrepreneurship",
    "17_before_after_evolution": "17_before_after_evolution",
    "18_astrology_horoscope": "18_astrology_horoscope",
    "19_historical_battles": "19_historical_battles",
    "history": "19_historical_battles",
    "20_whatsapp_chat_story": "20_whatsapp_chat_story",
    "21_ai_tools_hacks": "21_ai_tools_hacks",
    "4_ai_money_tech": "21_ai_tools_hacks",
    "ai": "21_ai_tools_hacks",
    "22_emoji_guess_game": "22_emoji_guess_game",
    "23_fitness_nutrition_hacks": "23_fitness_nutrition_hacks",
    "10_fitness_biohack": "23_fitness_nutrition_hacks",
    "fitness": "23_fitness_nutrition_hacks",
    "24_sigma_character_study": "24_sigma_character_study",
    "25_celebrity_net_worth": "25_celebrity_net_worth",
    "26_dangerous_places": "26_dangerous_places",
    "27_common_myths_busted": "27_common_myths_busted",
    "8_survival_myth": "27_common_myths_busted",
    "myths": "27_common_myths_busted",
    "28_dream_meanings": "28_dream_meanings",
    "29_optical_illusions_iq": "29_optical_illusions_iq",
    "30_poetry_quotes": "30_poetry_quotes",
    "31_supercars_automotive": "31_supercars_automotive",
    "32_legal_consumer_hacks": "32_legal_consumer_hacks",
    "33_parenting_child_hacks": "33_parenting_child_hacks",
    "15_parenting_hacks": "33_parenting_child_hacks",
    "parenting": "33_parenting_child_hacks",
    "34_gaming_easter_eggs": "34_gaming_easter_eggs",
    "35_animal_kingdom_stories": "35_animal_kingdom_stories",
    "36_kids_animation": "36_kids_animation",
    "37_interactive_quiz": "37_interactive_quiz",
    # 54 Hybrid Niches mappings
    "mystery_earth_zoom": "13_mystery_paranormal",
    "cosmic_epic_hans_zimmer": "9_five_facts",
    "conspiracy_fbi_newspaper": "13_mystery_paranormal",
    "true_crime_police_radio": "13_mystery_paranormal",
    "hidden_wiretap_meeting": "13_mystery_paranormal",
    "stoic_cyberpunk": "6_stoic_philosophy",
    "absurdist_philosophy_meme": "6_stoic_philosophy",
    "dark_psychology_parkour": "7_dark_psychology",
    "body_language_celebrity": "7_dark_psychology",
    "night_mode_dark_content": "7_dark_psychology",
    "crypto_comic_book": "8_crypto_market",
    "money_psychology_quotes": "16_wealth_entrepreneurship",
    "old_money_luxury_mindset": "16_wealth_entrepreneurship",
    "corporate_dirty_secrets": "16_wealth_entrepreneurship",
    "entrepreneur_minimal_typography": "16_wealth_entrepreneurship",
    "ai_tools_screen": "21_ai_tools_hacks",
    "future_2050_simulation": "21_ai_tools_hacks",
    "alternate_history_ai": "19_historical_battles",
    "military_tactics_map": "19_historical_battles",
    "history_chat": "19_historical_battles",
    "forgotten_historical_figures": "19_historical_battles",
    "mythology_ai_epic": "19_historical_battles",
    "country_guess_countdown": "5_guess_flag_country",
    "country_popular_things_map": "5_guess_flag_country",
    "would_you_rather_duel": "4_would_you_rather",
    "viewer_choice_door_game": "4_would_you_rather",
    "interactive_stop_wheel_game": "37_interactive_quiz",
    "iq_puzzle_optical_riddle": "29_optical_illusions_iq",
    "optical_illusion_focus": "29_optical_illusions_iq",
    "binaural_8d_audio_illusions": "29_optical_illusions_iq",
    "spiritual_rain_nature": "10_religious_quotes",
    "ancient_remedies_egypt": "23_fitness_nutrition_hacks",
    "reddit_asmr": "2_reddit_confessions",
    "whatsapp_horror_voice": "20_whatsapp_chat_story",
    "lifehack_affiliate_3items": "12_amazon_affiliate",
    "price_timeline_tunnel": "17_before_after_evolution",
    "time_machine_100years": "17_before_after_evolution",
    "photo_restoration_story": "17_before_after_evolution",
    "childhood_nostalgia_90s_2000s": "17_before_after_evolution",
    "movie_idiom_english": "11_language_learning",
    "untranslatable_words_sonder": "11_language_learning",
    "micro_book_summary": "14_movie_summaries",
    "animal_funny_dub": "35_animal_kingdom_stories",
    "dream_surreal_psychology": "28_dream_meanings",
    "collective_subconscious_fears": "28_dream_meanings",
    "weird_laws_world_map": "32_legal_consumer_hacks",
    "celebrity_failure_stories": "25_celebrity_net_worth",
    "world_records_sports_commentary": "15_football_transfers",
    "inspirational_athlete_comeback": "15_football_transfers",
    "did_you_know_facts": "9_five_facts",
    "subtitle_voice_equalizer": "9_five_facts",
    "deep_sea_thalassophobia": "26_dangerous_places",
    "seasonal_trend_reaction": "1_news_flash",
    "micro_street_interview": "1_news_flash",
}

def resolve_canonical_niche(niche_id: str) -> str:
    """Normalize any niche identifier, hybrid niche, or alias to canonical NICHES key."""
    clean = (niche_id or "").strip().lower()
    if clean in NICHE_ALIASES:
        return NICHE_ALIASES[clean]
    
    # Substring / keyword heuristics
    if any(k in clean for k in ("mystery", "paranormal", "komplo", "gizem", "earth_zoom")):
        return "13_mystery_paranormal"
    if any(k in clean for k in ("stoic", "felsefe", "philosophy")):
        return "6_stoic_philosophy"
    if any(k in clean for k in ("psychology", "psikoloji", "beden_dili", "dark")):
        return "7_dark_psychology"
    if any(k in clean for k in ("crypto", "kripto", "bitcoin", "borsa")):
        return "8_crypto_market"
    if any(k in clean for k in ("news", "haber", "flash")):
        return "1_news_flash"
    if any(k in clean for k in ("reddit", "itiraf", "confess", "aita")):
        return "2_reddit_confessions"
    if any(k in clean for k in ("split", "parkour", "gameplay")):
        return "3_split_gameplay"
    if any(k in clean for k in ("quiz", "rather", "tercih")):
        return "4_would_you_rather"
    if any(k in clean for k in ("flag", "country", "bayrak", "ülke", "ulke")):
        return "5_guess_flag_country"
    if any(k in clean for k in ("fact", "bilgi", "gerçek", "cosmic", "space", "uzay")):
        return "9_five_facts"
    if any(k in clean for k in ("relig", "dini", "hadis", "dua", "spiritual", "islamic", "kuran")):
        return "10_religious_quotes"
    if any(k in clean for k in ("language", "english", "ingilizce", "dil")):
        return "11_language_learning"
    if any(k in clean for k in ("amazon", "affiliate", "ürün", "urun", "gadget", "trendyol")):
        return "12_amazon_affiliate"
    if any(k in clean for k in ("movie", "film", "dizi", "cinema")):
        return "14_movie_summaries"
    if any(k in clean for k in ("football", "futbol", "transfer", "spor")):
        return "15_football_transfers"
    if any(k in clean for k in ("wealth", "zengin", "para", "money", "luxury", "entrepreneur")):
        return "16_wealth_entrepreneurship"
    if any(k in clean for k in ("evolution", "before_after", "evrim", "nostalgia")):
        return "17_before_after_evolution"
    if any(k in clean for k in ("astrology", "burç", "burc", "horoscope")):
        return "18_astrology_horoscope"
    if any(k in clean for k in ("battle", "savaş", "savas", "tarih", "history", "military")):
        return "19_historical_battles"
    if any(k in clean for k in ("whatsapp", "chat", "mesaj")):
        return "20_whatsapp_chat_story"
    if any(k in clean for k in ("ai", "yapay_zeka", "tech", "teknoloji")):
        return "21_ai_tools_hacks"
    if any(k in clean for k in ("fitness", "spor", "nutrition", "beslenme", "diyet", "kilo")):
        return "23_fitness_nutrition_hacks"
    if any(k in clean for k in ("myth", "mit", "survival")):
        return "27_common_myths_busted"
    if any(k in clean for k in ("parenting", "çocuk", "cocuk", "ebeveyn")):
        return "33_parenting_child_hacks"

    return ""


CURATED_NICHE_TOPICS: Dict[str, List[str]] = {
    "1_news_flash": [
        "Merkez Bankası'ndan Beklenmeyen Faiz Kararı: Piyasaları Ne Bekliyor?",
        "Yapay Zeka Devinden Tarihi Açıklama: Yazılım Sektörü Kökten Değişiyor",
        "NASA James Webb Teleskobu ile Yaşam İzi Olabilecek Yeni Gezegen Keşfetti",
        "Küresel Enerji Koridorunda Kritik Hamle: Yeni Anlaşmanın Perde Arkası",
        "Milyonlarca Kullanıcıyı İlgilendiren Kritik Siber Güvenlik Uyarısı",
        "Elektrikli Araç Piyasasında Büyük Kriz: Batarya Tedarik Zinciri Kırıldı",
        "Altın ve Para Piyasalarında Beklenmedik Kırılma: Uzmanlar Ne Diyor?",
        "Uzay Turizminde Yeni Dönem: İlk Ticari Ay Yolculuğu Tarihi Belli Oldu",
        "Akıllı Telefonlara Gelecek Yeni Yasal Düzenleme Her Şeyi Değiştirecek",
        "Büyük Şirketlerin Sessizce Başlattığı Yapay Zeka Dönüşümü",
    ],
    "2_reddit_confessions": [
        "AITA: Düğünümden 1 Gün Önce Kayınvalidemin Telefonunda Bu Mesajı Gördüm",
        "7 Yıllık Sırrımı Eşime İtiraf Ettim — Hayatımız Tamamen Değişti",
        "İş Yerinde Patronumun Şirket Parasını Kaçırdığını Fark Ettiğim Gün",
        "AITA: Kardeşimin Düğününde Nişanlımın Ailesini Davet Etmeyi Reddettim",
        "Annemden Gizli Yaptırdığım DNA Testi Ailemizin En Büyük Yalanını Çözdü",
        "En Yakın Arkadaşımın Çift Hayatını Keşfettim ve Sessiz Kalamadım",
        "Doğum Günümde Yapılan Korkunç Şaka Sonrası Tüm Ailemle Bağımı Kopardım",
        "Patronum Beni Kovmak İçin Komplo Kurdu, Ama Elimde Tüm Kanıtlar Vardı",
        "5 Yıl Sonra Eski Eşimin Kapıma Gelip İtiraf Ettiği Şok Gerçek",
        "AITA: Miras Paylaşımında Kardeşlerime Dava Açtım Çünkü Hakkımı Gasp Ettiler",
    ],
    "3_split_gameplay": [
        "Otel Odasında Bulduğum Gizli Kamera Hayatımın En Büyük Kabusu Oldu",
        "Gece Yarısı Issız Otoyolda Karşıma Çıkan Gizemli Aracın Sırrı",
        "Yeni Taşındığımız Evin Duvarının İçinden Çıkan 50 Yıllık Günlük",
        "Büyük Bir Holdingde Staj Yaparken Şahit Olduğum En Büyük Şirket Skandalı",
        "Sosyal Medyada Tanıştığım Kişinin Aslında Kim Olduğunu Öğrendiğim An",
        "Kayıp Kardeşimi 12 Yıl Sonra Bir Metro İstasyonunda Gördüm",
        "Eski Sevgilimin Yeni Nişanlısı Beni Gizlice Arayıp Bunu Söyledi",
        "Uçakta Yanıma Oturan Gizemli Yolcunun Bana Bıraktığı Zarf",
        "Lisede Herkesin Dalgaya Aldığı Çocuğun 10 Yıl Sonraki İntikamı",
        "Kiralık Evin Tabanındaki Gizli Kapak ve Altındaki Korkunç Oda",
    ],
    "4_would_you_rather": [
        "Zamanı Durdurabilmek mi Yoksa Geleceği Görmek mi? İmkansız 4 Tercih!",
        "Dünyanın En Zengin İnsanı Olmak mı, Ölümsüz Olmak mı? Hangisini Seçersin?",
        "Tüm Dilleri Anında Konuşabilmek mi Yoksa Hayvanlarla Konuşabilmek mi?",
        "10 Milyon Dolar mı Yoksa Zihnini %100 Kapasiteyle Kullanabilmek mi?",
        "Asla Yalan Söyleyememek mi Yoksa Kimsenin Yalanını Fark Edememek mi?",
        "Her Gün 1 Saat Fazladan Yaşamak mı Yoksa Hiç Uyumaya İhtiyaç Duymamak mı?",
        "En Büyük Korkunla Yüzleşmek mi Yoksa En Sevdiğin Şeyi Sonsuza Dek Unutmak mı?",
        "Görünmez Olabilmek mi Yoksa Işınlanabilmek mi? Kararını Ver!",
    ],
    "5_guess_flag_country": [
        "Sadece Gerçek Coğrafya Dahilerinin %10'u Bu 5 Bayrağı Doğru Biliyor!",
        "Hangi Ülke? Başkentinden ve Para Biriminden Ülkeyi 3 Saniyede Tahmin Et!",
        "Renkleri Birbirine Çok Benzeyen 4 Bayrak: Hangisi Hangi Ülkeye Ait?",
        "Haritadaki Şeklinden Ülkeyi Bulabilir misin? En Zor 5 Soru!",
        "Bu Bayrak Hangi Kıtada? İpuçlarını Takip Et ve Cevabı Bul!",
        "Dünyanın En İlginç ve Bilinmeyen 5 Ülke Bayrağı!",
    ],
    "6_stoic_philosophy": [
        "Marcus Aurelius'un Öfkeyi ve Stresi Yok Eden 3 Stoacı Kuralı",
        "Seneca'nın Kaygıyı ve Aşırı Düşünmeyi Bitiren 4 Antik Dersi",
        "Epiktetos: Kontrol Edebileceğin Tek Şey Kendi Tepkindir",
        "Stoacıların Asla Şikayet Etmeme ve Zihinsel Güç Sırrı",
        "2000 Yıllık Bu Stoacı İlke Hayata Bakışınızı Tamamen Değiştirecek",
        "Marcus Aurelius'un Sabah Rutini: Güne Zihinsel Zırhla Başlamanın Yolu",
        "Hiçbir Şeyi Kafaya Takmamanın ve İç Huzurun 3 Stoacı Formülü",
        "Zor ve Toksik İnsanlarla Başa Çıkmanın Stoacı Yolu",
        "Memento Mori (Ölümü Hatırla): Hayatınızı Sadeleştiren En Güçlü Felsefe",
        "Duygusal Bağımlılığı Kıran ve Özgürleştiren Epiktetos Öğretisi",
    ],
    "7_dark_psychology": [
        "Biri Konuşurken Yalan Söylediğini Ele Veren 3 Mikro Beden Dili İpucu",
        "Manipülatif İnsanlara Karşı Zihninizi Korumanın 3 Psikolojik Kalkanı",
        "Beden Dilinizle Karşı Tarafta Anında Saygı ve Otorite Uyandırmanın 3 Yolu",
        "İkna Etmenin Gizli Gücü: Karşı Tarafı Fark Ettirmeden Yönlendirme",
        "Toksik İnsanları İlk 5 Dakikada Teşhis Eden 3 Davranış Modeli",
        "Sessizliğin Gücü: Tartışmalarda Üstünlük Sağlayan Psikolojik Taktik",
        "Göz Temasıyla Karşı Tarafın Gerçek Niyetini Anlama Sanatı",
        "Karşındakinin Sana Saygı Duymasını Sağlayan 3 Güçlü Duruş Kuralı",
        "Gaslighting Yapan Birini Anında Durduran O Sihirli Cümle",
    ],
    "8_crypto_market": [
        "Bitcoin Balinalarının Sessizce Uyguladığı 3 Portföy Büyütme Stratejisi",
        "Kripto Piyasasında Kaybetmeyi Bırakmak İçin 3 Altın Kural",
        "Boğa Sezonunda Küçük Yatırımcıların Yaptığı En Ölümcül 3 Hata",
        "DCA (Kademeli Alım) Yöntemiyle Sıfır Stresle Kripto Sepeti Yapmak",
        "On-Chain Verilerinin Gösterdiği ve Çoğunluğun Kaçırdığı 3 Alım Sinyali",
        "Kriptoda Kaldıraçlı İşlemlerden Neden Uzak Durmalısınız? İstatistikler",
        "Altcoin Sepeti Yaparken Dikkat Edilmesi Gereken 4 Hayati Metrik",
        "Kripto Cüzdan Güvenliği: Varlıklarınızı Hacklenmekten Korumanın 3 Yolu",
    ],
    "9_five_facts": [
        "İnsan Vücudu Hakkında Muhtemelen Bilmediğiniz 5 Şaşırtıcı Gerçek",
        "Dünyanın En Derin Noktası Mariana Çukuru Hakkında 5 Ürpertici Bilgi",
        "Gözlerinize İnanamayacağınız 5 Doğa Olayı ve Arkasındaki Bilim",
        "Uzay Hakkında Bilim İnsanlarını Bile Hayrete Düşüren 5 Gizem",
        "Günde Sadece 15 Dakika Yürüyüş Yapmanın Vücuda 5 Mucizevi Etkisi",
        "Hayvanlar Aleminin En Tuhaf ve İnanılmaz 5 Süper Yeteneği",
        "Tarihin En Zeki İnsanlarının Sahip Olduğu 5 Garip Alışkanlık",
        "Dünyanın En İlginç 5 Arkeolojik Keşfi ve Çözülemeyen Sırları",
    ],
    "10_religious_quotes": [
        "Hz. Peygamber'in 'Ameller Niyetlere Göredir' Hadis-i Şerifi ve Fazileti (Buhari)",
        "Resulullah'ın 'Müslüman Müslümanın Kardeşidir' Hadis-i Şerifi (Buhari, Müslim)",
        "Peygamber Efendimiz'in 'Kolaylaştırınız, Zorlaştırmayınız' Hadisi (Buhari)",
        "İki Büyük Nimet: Sağlık ve Boş Vakit Hadis-i Şerifi ve Hikmeti (Buhari)",
        "Kendisi İçin İstediğini Kardeşi İçin de İstemedikçe İman Tam Olmaz Hadisi (Buhari)",
        "Merhamet Etmeyene Merhamet Olunmaz Hadis-i Şerifi (Müslim)",
        "Sizin En Hayırlınız Kur'an'ı Öğrenen ve Öğretendir Hadisi (Buhari)",
        "Rabbinizin Müjdesi: 'Şükrederseniz Elbette Nimetimi Artırırım' (İbrahim Suresi 7)",
        "Güzel Bir Söz Söylemek Sadakadır: Nezaket ve Tebessüm Hadisi (Buhari)",
        "Dua Müminin Silahıdır: Zor Zamanlarda Okunacak Nebevî Niyaz (Tirmizi)",
        "Bizi Aldatan Bizden Değildir: Doğruluk ve Dürüstlük Hadisi (Müslim)",
        "Kalbinde Zerre Kadar Kibir Olan Cennete Giremez Hadis-i Şerifi (Müslim)",
        "Gıybet ve Dedikodudan Sakınmanın Önemi Hadis-i Şerifi (Ebu Davud)",
        "İlim Öğrenmek Her Müslümana Farzdır Hadis-i Şerifi (İbn Mace)",
        "Sabır ve Namazla Allah'tan Yardım İsteyin Ayet-i Kerimesi (Bakara 153)",
        "Kalpler Ancak Allah'ı Anmakla Huzur Bulur Ayet-i Kerimesi (Rad 28)",
        "Şüphesiz Her Zorluğun Yanında Bir Kolaylık Vardır Müjdesi (İnşirah Suresi)",
        "Peygamber Efendimiz'in (s.a.v.) Zorluk Anlarında Okuduğu Eşsiz Dua (Tirmizi)",
        "Gününüzü Aydınlatacak ve Kalbinizi Ferahlatacak Faziletli Dua",
        "Allah Bize Yeter, O Ne Güzel Vekildir Ayet-i Kerimesi (Al-i İmran 173)",
    ],
    "11_language_learning": [
        "İngilizce Konuşurken En Çok Yapılan ve Türkçeden Çevrilen 5 Hata",
        "Dizi ve Film İzleyerek 3 Ayda Akıcı İngilizce Konuşmanın 3 Sırrı",
        "Yerli Konuşmacıların (Native) Günlük Hayatta Kullandığı 5 Harika Deyim",
        "İngilizce Kelimeleri Asla Unutmamak İçin Spaced Repetition Tekniği",
        "İş Görüşmelerinde Sizi Profesyonel Gösterecek 5 İngilizce Cümle Kalıbı",
        "Yabancı Dil Öğrenirken Telaffuzunuzu Kusursuzlaştıran Gölgeleme (Shadowing)",
    ],
    "12_amazon_affiliate": [
        "Hayatınızı Kolaylaştıracak ve 'Bunu Neden Daha Önce Almadım' Diyeceğiniz 3 Akıllı Ürün",
        "TikTok'ta Viral Olan ve Gerçekten İşe Yarayan 3 İnanılmaz Amazon Gadgeti",
        "Çalışma Masanızın Havasını Tamamen Değiştirecek 3 Minimalist Masaüstü Ürün",
        "Seyahat Edenlerin Yanından Asla Ayırmadığı 3 Pratik ve Kompakt Aksesuar",
        "Evde Saatlerce Vakit Kazandıracak 3 Çok Fonksiyonlu Mutfak Aleti",
        "Fiyatını Son Kuruşuna Kadar Hak Eden 3 Gizli Kalmış Fiyat/Performans Ürünü",
        "Bütçe Dostu Ama Aşırı Lüks Duran 3 Akıllı Ev Teknolojisi",
        "Kablo Dağınıklığını Sonsuza Dek Bitiren 3 Dahiyane Düzenleyici",
        "Her Gün Kullanacağınız ve Asla Pişman Olmayacağınız 3 Pratik Tavsiye",
    ],
    "ancient_remedies_egypt": [
        "Antik Mısır'da Firavunların Hastalıklardan Korunmak İçin Kullandığı Gizli Ot",
        "Modern Tıbbın Bile Şaşırdığı 3.000 Yıllık Şifa Reçetesi",
        "Kleopatra'nın Güzellik ve Gençlik Sırrı Olarak Bilinen Efsanevi Karışım",
        "Sümerlerin Baş Ağrısını Kesmek İçin Çiğnediği O Bilinmeyen Kök",
        "Eski Medeniyetlerin Doğal Antibiyotik Olarak Kullandığı 3 Güçlü Madde",
    ],
    "13_mystery_paranormal": [
        "1971'de Uçaktan Paraşütle Atlayıp Sırra Kadem Basan D.B. Cooper Dosyası",
        "Bermuda Şeytan Üçgeni Hakkında Bilim İnsanlarının Son Açıklaması",
        "Dyatlov Geçidi Vakası: Karlar Altında 9 Dağcının Çözülemeyen Gizemi",
        "Dünyanın En Gizemli Ses Kaydı: Okyanusun Dibindeki 'The Bloop'",
        "Antik Mısır Piramitlerinin Hizalanmasındaki Akıl Almaz Astronomik Hassasiyet",
        "Voynich El Yazması: 600 Yıldır Hiç Kimsenin Çözemediği Şifreli Kitap",
        "Zaman Yolculuğu Yaptığını İddia Eden İnsanlar ve Bıraktıkları Tuhaf Kanıtlar",
    ],
    "14_movie_summaries": [
        "Son Sahnesinde Beyninizi Yakacak ve Günlerce Düşündürecek 3 Ters Köşe Film",
        "IMDb Puanı 8 Üzeri Olan Ama Kimsenin Bilmediği 3 Gizli Başyapıt",
        "Tek Bir Mekanda Geçen Ama Nefesinizi Kesecek 3 Gerilim Filmi",
        "İzledikten Sonra Hayata Bakışınızı Değiştirecek 3 Felsefi Sinema Başyapıtı",
        "Gerçek Bir Olaydan Uyarlanan ve Tüylerinizi Ürpertecek 3 Polisiye Suç Filmi",
        "Christopher Nolan'ın Zihin Bükücü Anlatım Teknikleri ve Gizli İpuçları",
    ],
    "15_football_transfers": [
        "Dünya Futbolunu Sarsacak Yılın En Büyük 3 Transfer İddiası",
        "Bedavaya Alınıp Kulübüne 100 Milyon Euro Kazandıran 4 Transfer Dehası",
        "Tarihin En Pahalı Ama En Büyük Hayal Kırıklığı Yaratan 3 Futbolcusu",
        "Süper Lig Kulüplerinin Gizlice Takip Ettiği 3 Genç Yıldız Adayı",
        "Bir İmza ile Tarihi Değişen Efsanevi Transfer Çalımları",
        "Real Madrid ve Manchester City'nin Gelecek Sezon Kuracağı Rüya Kadrolar",
    ],
    "16_wealth_entrepreneurship": [
        "Dünyanın En Zengin %1'lik Kesiminin Asla Taviz Vermediği 3 Sabah Alışkanlığı",
        "Sıfırdan Milyon Dolarlık Şirket Kuran Girişimcilerin 3 Ortak Özelliği",
        "Elon Musk'ın Zamanı 5 Dakikalık Bloklara Bölen Üretkenlik Metodu",
        "Warren Buffett'tan Gençlere Para ve Yatırım Hakkında 3 Altın Kural",
        "Zenginlerin Asla Satın Almadığı Ama Orta Sınıfın Para Harcadığı 3 Şey",
        "Steve Jobs'ın Sadeleşme ve Odaklanma Felsefesi ile Başarıya Ulaşma",
    ],
    "17_before_after_evolution": [
        "Son 50 Yılda Dünyanın En Büyük Şehirlerinin İnanılmaz Değişimi!",
        "Teknolojinin 20 Yılda Hayatımızdan Sildiği ve Unutturduğu 5 Şey",
        "Otomobil Tasarımlarının 1920'den Günümüze Akıl Almaz Evrimi",
        "Çocukken Oynadığımız Efsane Oyunların Bugünkü Halleri (Before vs After)",
        "Gökdelenlerin Olmadığı Dönemde İstanbul ve New York Manzaraları",
    ],
    "18_astrology_horoscope": [
        "Bu Hafta Gökyüzünde Yaşanan Yeni Ay Hangi 3 Burcun Kaderini Değiştirecek?",
        "Zodyak'ın Asla Yalanı Affetmeyen ve En Sezgisel 3 Güçlü Burcu",
        "Merkür Retrosundan En Çok Etkilenecek Burçlar ve Korunma Yolları",
        "Aşk ve İlişkilerde Birbiriyle En Uyumlu 4 Mükemmel Burç Çifti",
        "Kariyerinde Büyük Bir Atılım Yapacak Olan 3 Şanslı Burç!",
    ],
    "19_historical_battles": [
        "Tarihin Akışını Değiştiren ve 1 Saatte Biten En Kritik 3 Savaş",
        "Fatih Sultan Mehmed'in Gemileri Karadan Yürütme Dehası ve Matematiksel Planı",
        "Çanakkale'de Seyit Onbaşı'nın 276 Kiloluk Mermiyi Kaldırdığı O Anın Perde Arkası",
        "Mohaç Meydan Muharebesi: 2 Saatte Kazanılan Tarihin En Hızlı Zaferi",
        "Kurtuluş Savaşı'nda Büyük Taarruz'un Gizli Başlangıç Planı ve Stratejisi",
    ],
    "20_whatsapp_chat_story": [
        "Mesajı Yanlışlıkla Şirket Grubuna Atınca Yaşanan Akıl Almaz Kaos!",
        "Gecenin 3'ünde Eski Sevgiliden Gelen O Beklenmedik WhatsApp Mesajı",
        "Annemin Gönderdiği Yanlış Konum Sayesinde Öğrendiğim Aile Sırrı",
        "Ev Arkadaşımın Odasından Gelen Sesler ve Sonrasında Yazdığı İtiraf Mesajı",
        "İki Kardeş Arasında Geçen ve Herkesi Gözyaşlarına Boğan O Konuşma",
    ],
    "21_ai_tools_hacks": [
        "Yapay Zeka ile Pasif Gelir Elde Etmenin 2026'da En Etkili 3 Yolu",
        "Kimsenin Bilmediği Ama Hayat Kurtaran 4 Ücretsiz Yapay Zeka Sitesi",
        "Kod Yazmadan Yapay Zekayla Web Sitesi ve Uygulama Geliştirme Rehberi",
        "ChatGPT ve Claude Kullanırken Profesyonellerin Uyguladığı 3 Prompt Sırrı",
        "Sesinizi ve Yüzünüzü Mükemmel Klonlayan En Yeni Yapay Zeka Teknolojileri",
        "Öğrencilerin ve Çalışanların İşini Yarıya İndiren 3 Üretkenlik AI Aracı",
    ],
    "22_emoji_guess_game": [
        "Bu Emojilerden Hangi Ünlü Filmi Anlatıyoruz? Sadece Sinemaseverler Bilir!",
        "Emojileri Birleştir Şarkıyı Bul! 5 Soruluk Eğlenceli Müzik Testi",
        "Emojilerle Anlatılan Şehri Tahmin Edebilir misin? En Zor 4 Soru!",
        "Bu 3 Emoji Hangi Tarihi Olayı Simgeliyor? Cevabı Tahmin Et!",
    ],
    "23_fitness_nutrition_hacks": [
        "Günde Sadece 15 Dakika Yaparak Göbek Yağlarını Hızla Eriten 3 Bilimsel Hareket",
        "Her Sabah Kahveye Bunu Eklerseniz Metabolizmanız İki Kat Daha Hızlı Çalışır",
        "Kas Gelişimini Yarıda Kesen En Yaygın 3 Ağır Antrenman Hatası",
        "Aç Kalmadan ve Diyet Yapmadan Kilo Vermenin 4 Biyolojik Sırrı",
        "Yorgun Uyanmayı Sonsuza Dek Bitiren Uyku ve Magnezyum Tüyosu",
        "Testosteron Seviyesini Doğal Yollarla Artıran 3 Temel Besin Kaynağı",
    ],
    "24_sigma_character_study": [
        "Thomas Shelby'nin Manipülasyonlara Karşı Kullandığı Soğukkanlı Duruş Sırrı",
        "Sigma Erkeklerin Asla Taviz Vermediği ve Sessizce Uyguladığı 3 Kural",
        "Baskı Altında Asla Paniklemeyen İnsanların Zihinsel Dayanıklılık Formülü",
        "İnsanların Saygısını Zorlamadan Kazanan Karakterlerin 3 Gizli İlkesi",
        "Göz Teması ve Beden Diliyle Otorite Kurmanın En Güçlü Psikolojik Yolları",
    ],
    "25_celebrity_net_worth": [
        "Dünyanın En Çok Kazanan 3 YouTube İçerik Üreticisinin Aylık Geliri",
        "Cristiano Ronaldo'nun Dakikada Kazandığı Para ve Gayrimenkul İmparatorluğu",
        "Milyarderlerin Servetlerini Nasıl Koruduğu ve Vergi Stratejileri",
        "Hollywood Yıldızlarının Tek Bir Film İçin Aldığı Akıl Almaz Ücretler",
    ],
    "26_dangerous_places": [
        "Dünyanın Girişi Kesinlikle Yasak Olan En Tehlikeli 5 Gizli Bölgesi",
        "Kuzey Sentinel Adası: Modern Dünyayla Temas Kurmayan Son Kabile",
        "Yılan Adası (Ilha da Queimada Grande): İnsanların Adım Atamadığı Ölümcül Ada",
        "Çernobil Dışlama Bölgesi'nde Bugün Yaşanan Akıl Almaz Değişimler",
        "Ölüm Vadisi: 57 Derece Sıcaklıkta Doğa Nasıl Hayatta Kalıyor?",
    ],
    "27_common_myths_busted": [
        "Filmlerde Gördüğünüz ve Gerçek Hayatta Sizi Öldürebilecek 3 Hayatta Kalma Miti",
        "Günde 8 Bardak Su İçmek Zorunda mısınız? Bilimin Açıkladığı Gerçek!",
        "Beynimizin Sadece %10'unu mu Kullanıyoruz? İşte Gerçek Nörolojik Gerçekler",
        "Karanlıkta Kitap Okumak Gözleri Bozar mı? Doğru Bilinen Yanlışlar!",
        "Yutulan Sakız Midede 7 Yıl Kalır mı? Doktorların Cevabı!",
    ],
    "28_dream_meanings": [
        "Rüyanızda Yüksekten Düştüğünüzü Görmek Aslında Ne Anlama Geliyor?",
        "Diş Dökülmesi Rüyasının Bilinçaltınızdaki Şok Edici Psikolojik Sebebi",
        "Tanıdığınız Birini Rüyada Görmek Bilinçaltınızın Size Verdiği Hangi Mesaj?",
        "Tekrarlayan Rüyaların Ardındaki Gizli Anlam ve Bilinçaltı Uyarıları",
    ],
    "29_optical_illusions_iq": [
        "Sadece Yüksek IQ'lu İnsanların İlk 5 Saniyede Fark Ettiği Gizli Detay!",
        "Bu Resim Hareket Etmiyor! Beyninizi Kandıran İnanılmaz Optik İllüzyon",
        "Resimdeki Gizlenmiş Hayvanı 7 Saniyede Bulabilir misin? Dikkat Testi!",
        "Gözlerinizin Sizi Yanılttığı 3 İnanılmaz Görsel İllüzyon Deneyi",
    ],
    "30_poetry_quotes": [
        "Nazım Hikmet'ten Ruhunuzu Derinden Saracak En Güzel Aşk Dizeleri",
        "Özdemir Asaf'ın Yalnızlığı ve Sevgiyi Anlatan Unutulmaz 4 Cümlesi",
        "Cemal Süreya'dan Kalbe Dokunan ve Asla Eskimeyen Edebi Sözler",
        "Attila İlhan'ın Şiirlerindeki Derin Melankoli ve Sevda Anlatımı",
    ],
    "31_supercars_automotive": [
        "Bugatti Tourbillon: 1800 Beygirlik V16 Motorun Akıl Almaz Mühendislik Sırları",
        "Dünyanın En Hızlı 3 Seri Üretim Otomobili ve Ulaştıkları Hız Rekorları",
        "Ferrari'nin Müşterilerine Getirdiği ve Asla Taviz Vermediği İlginç Kurallar",
        "Elektrikli Hiper Arabaların 0-100 Hızlanmasındaki Yerçekimi Karşıtı Fizik",
    ],
    "32_legal_consumer_hacks": [
        "Uçuşunuz Rötara Uğradığında Havayolundan Alabileceğiniz Gizli Tazminat Hakkı",
        "İnternetten Satın Aldığınız Ürünlerde Asla Bilmediğiniz 14 Günlük İade Hakkı",
        "Kira Sözleşmesi Yaparken Kiracıların Mutlaka Bilmesi Gereken 3 Hukuki Madde",
        "Banka Kartı ve Kredi Kartı Aidatlarını Geri Almanın En Kolay Yolu",
    ],
    "33_parenting_child_hacks": [
        "Çocuğunuz Öfke Nöbeti Geçirdiğinde Asla Söylememeniz Gereken 3 Kelime",
        "Çocuklarda Ekran Bağımlılığını Kavgasız Bitiren 3 Etkili Psikolojik Yöntem",
        "Özgüvenli ve Sorumluluk Sahibi Çocuk Yetiştirmenin 3 Temel Prensibi",
        "Çocuğunuzun Ders Çalışma İsteğini Artıran Eğlenceli Öğrenme Taktikleri",
    ],
    "34_gaming_easter_eggs": [
        "GTA 5'te 10 Yıldır Çoğu Oyuncunun Kaçırdığı 3 Gizli Detay ve Sır",
        "Red Dead Redemption 2'deki En Korkutucu ve Çözülemeyen 3 Gizem",
        "Minecraft Dünyasındaki En Nadir Doğa Olayları ve Gizli Kodlar",
        "The Witcher 3'te Haritanın En Ucunda Gizlenen Unutulmaz Sürprizler",
    ],
    "35_animal_kingdom_stories": [
        "Dünyanın En Korkusuz Hayvanı Bal Porsuğunun Akıl Almaz Hayatta Kalma Mücadelesi",
        "Ahtapotların 3 Kalbi ve 9 Beyni ile Sahip Olduğu Uzaylı Benzeri Zeka",
        "Kurt Sürülerindeki Hiyerarşi ve Liderin Sürüyü Koruma Stratejisi",
        "Kargaların İnsan Yüzlerini Asla Unutmadığını Biliyor muydunuz? Bilimsel Deney!",
    ],
    "36_kids_animation": [
        "Sevimli Hayvan Dostlarımız Ormanda Kaybolan Yıldızı Nasıl Buldu?",
        "Trafik Işıklarının Renkleri Bize Ne Anlatıyor? Eğlenceli Öğrenme Vakti!",
        "Dişlerimizi Düzenli Fırçalamazsak Ne Olur? Mikroplarla Mücadele Hikayesi!",
        "Meyve ve Sebzelerin Süper Güçleri: Hangi Vitamin Bizi Nasıl Güçlendirir?",
    ],
    "37_interactive_quiz": [
        "5 Soruluk Genel Kültür Testi: Sadece %5'lik Kesim Hepsini Doğru Biliyor!",
        "Tarih Bilgini Test Et! Bu 4 Olaydan Hangisi Daha Önce Gerçekleşti?",
        "Hızlı Düşünme ve Zeka Testi: Bu Mantık Bilmecesini 10 Saniyede Çözebilir misin?",
        "Dünya Coğrafyası Canlı Test: Hangi Başkent Hangi Ülkeye Ait?",
    ],
}

CURATED_NICHE_TOPICS_EN: Dict[str, List[str]] = {
    "1_news_flash": [
        "BREAKING: 3 Critical Global Developments Changing Everything",
        "The Shocking Economic Warning Mainstream News Won't Report",
        "NASA James Webb Space Telescope Detects Unexplained Deep Space Anomaly",
        "Urgent Cybersecurity Alert Affecting Millions of Smartphone Users",
        "The Massive Global Shift Nobody Is Talking About Right Now",
    ],
    "2_reddit_confessions": [
        "AITA: I checked my fiancé's phone 2 days before our wedding and found this",
        "I confessed my 7-year secret to my wife and our entire life flipped",
        "The day I caught my CEO secretly embezzling company funds",
        "A secret DNA test revealed the darkest lie my family kept for 20 years",
        "My ex-fiancée called me 5 years later with a shocking confession",
    ],
    "3_split_gameplay": [
        "The Hidden Camera in My Hotel Room Became My Worst Nightmare",
        "The Creepy Hitchhiker on Desert Highway 50 at 2 AM",
        "The 50-Year-Old Diary We Found Hidden Inside Our New Bedroom Wall",
        "The Strange Letter Left on My Passenger Seat by an Unknown Passenger",
        "Why You Should Never Look Behind the Mirror in Abandoned Cabins",
    ],
    "4_would_you_rather": [
        "Would You Rather: Impossible Moral Dilemmas Only 1% Pass",
        "Would You Rather: $10 Million Cash or 5 Minutes In The Future?",
        "The Hardest Would You Rather Choices That Will Break Your Brain",
        "Would You Rather Know How You Die or When You Die?",
        "4 Impossible Survival Scenarios: Which Door Would You Pick?",
    ],
    "5_guess_flag_country": [
        "Guess The Country in 3 Clues (Hard Mode IQ Test)",
        "Can You Guess This Country Before The 5-Second Timer Ends?",
        "World Flag Quiz: 95% of Adults Fail Question Number 3",
        "Only 2% of People Can Identify All 5 Flags Without Mistakes",
        "Guess The Hidden Country from Its Most Bizarre Law",
    ],
    "6_stoic_philosophy": [
        "3 Stoic Rules of Marcus Aurelius That Kill Anger Instantly",
        "Seneca's Secret to Conquering Crippling Anxiety in Under 60 Seconds",
        "How to Become Emotionally Unshakable (Ancient Stoic Method)",
        "Why Quiet People Always Win in the End (Marcus Aurelius Wisdom)",
        "The Brutal Truth About Why People Betray You (Stoic Reality)",
    ],
    "7_dark_psychology": [
        "3 Dark Psychology Secrets Manipulation Experts Never Tell You",
        "The Subtle Art of Reading Anyone in 3 Seconds (FBI Body Language)",
        "How Manipulators Secretly Gaslight You (And How to Stop Them)",
        "The Mirroring Trick: How Toxic People Make You Trust Them Instantly",
        "3 Dark Psychological Signs Someone Is Secretly Envious of You",
        "Strategic Silence: The Deadliest Psychological Weapon Against Bullies",
    ],
    "8_crypto_market": [
        "The Secret Crypto Whale Move Happening Right Now in Plain Sight",
        "Why 99% of Bitcoin Investors Will Miss the Next Millionaire Wave",
        "3 Terrifying Truths About the Modern Banking System You Never Knew",
        "The Next Trillion Dollar Narrative That Smart Money Is Accumulating",
        "How Central Banks Are Secretly Preparing for Digital Currencies",
    ],
    "9_five_facts": [
        "5 Mind-Blowing Facts Science Class Kept Secret From You",
        "3 Bizarre Facts About Human Anatomy That Sound Like Pure Lies",
        "5 Unbelievable Facts About Deep Space That Will Give You Chills",
        "5 Ocean Secrets That Prove We Barely Know Our Own Planet",
        "5 Historical Facts That Sound Completely Fake But Are 100% True",
    ],
    "10_religious_quotes": [
        "3 Powerful Daily Verses That Bring Instant Inner Peace and Strength",
        "The Golden Hadith That Changes How You Look at Life Forever",
        "A Short Prayer for Difficult Times That Heals The Soul",
        "The Ancient Wisdom Behind Staying Patient During Life's Trials",
        "3 Timeless Spiritual Teachings That Quiet an Overthinking Mind",
    ],
    "11_language_learning": [
        "5 English Idioms Native Speakers Use That Textbooks Never Teach",
        "How to Sound 10x More Fluent in English in 60 Seconds",
        "Stop Saying 'Very': 5 Powerful Advanced English Vocabulary Swaps",
        "3 Pronunciation Mistakes That Immediately Reveal You Aren't Native",
        "Phrasal Verbs Native Speakers Use Daily and What They Actually Mean",
    ],
    "12_amazon_affiliate": [
        "3 Viral Amazon Gadgets That Will Actually Change Your Life",
        "The Genius Tech Product You Never Knew You Desperately Needed",
        "3 Incredible Travel Gadgets on Amazon Under $25 That Save Hours",
        "The Smart Home Hack Under $30 That Every Apartment Needs",
        "3 Life-Saving Car Accessories Everyone Should Keep in Their Glove Box",
    ],
    "ancient_remedies_egypt": [
        "The 3,000-Year-Old Egyptian Remedy For Perfect Skin Science Just Confirmed",
        "3 Ancient Babylonian Healing Rituals That Actually Work Today",
        "Why Egyptian Pharaohs Rubbed This One Desert Plant on Their Wounds",
        "The Secret Painkilling Herb Found in Cleopatra's Personal Journal",
        "How Ancient Healers Cured Infections Before Antibiotics Existed",
    ],

    "13_mystery_paranormal": [
        "3 Terrifying Paranormal Mysteries Science Still Cannot Explain",
        "What Really Happened Inside Room 1046? (Unsolved True Mystery)",
        "Dyatlov Pass Incident: The Bizarre Mystery Rescuers Found in the Snow",
        "The Vanishing of Flight 370: 3 Clues Experts Still Cannot Reconcile",
        "The Disturbing Sound Recorded 6 Miles Below Earth's Crust",
    ],
    "14_movie_summaries": [
        "The 3 Greatest Movie Plot Twists in Cinema History Ranked",
        "3 Underrated Psychological Thrillers That Will Blow Your Mind",
        "The Disturbing Hidden Detail in Interstellar Most People Missed",
        "Why The Ending of Inception Is Even Darker Than You Thought",
        "3 Movie Villains Who Were Actually Right All Along",
    ],
    "15_football_transfers": [
        "The Most Expensive Football Transfers That Completely Flopped",
        "How One Impossible Goal Changed Football History Forever",
        "The Secret Contract Clause That Shocked European Football",
        "5 Wonderkids Who Mysteriously Disappeared From World Football",
        "The Untold Story of How Real Madrid Hijacked Barcelona's Star",
    ],
    "16_wealth_entrepreneurship": [
        "How Warren Buffett Built an Empire With One Golden Rule",
        "The Ruthless Daily Routine of Multi-Billionaire Founders",
        "3 Harsh Money Truths The Middle Class Refuses to Accept",
        "How Broke 20-Year-Olds Are Quietly Building 6-Figure Side Incomes",
        "The Difference Between Fake Rich and Real Wealthy in 3 Habits",
    ],
    "17_before_after_evolution": [
        "What Major Cities Looked Like 100 Years Ago vs Today",
        "The Shocking Evolution of Everyday Technology Over 50 Years",
        "How Famous Landmarks Looked Before Tourism Changed Them",
        "The Evolution of Earth's Climate Over the Last 10,000 Years",
        "How Human Faces and Fashion Shifted Every Single Decade",
    ],
    "18_astrology_horoscope": [
        "The 3 Most Dangerous Zodiac Signs When Pushed to Their Limit",
        "The Hidden Subconscious Power of Water Signs Revealed",
        "Why Earth Signs Hide Their Deepest Emotions Until It's Too Late",
        "The Dark Side of Fire Signs Nobody Likes to Talk About",
        "The One Zodiac Pairing That Never Survives Long-Term",
    ],
    "19_historical_battles": [
        "The Greatest Military Masterstroke in Ancient Warfare History",
        "How 300 Spartans Held Off an Entire Persian Army",
        "The Battle of Cannae: Hannibal's Genius Double Envelopment Masterpiece",
        "The Costly Blunder That Doomed Napoleon at Waterloo",
        "How a Single Archer Decided the Fate of the English Crown",
    ],
    "20_whatsapp_chat_story": [
        "The Creepy Midnight Text Message From an Unknown Number",
        "My Roommate Left This Voicemail Before Vanishing Into Thin Air",
        "When I Texted My Dead Brother's Phone and Got an Immediate Reply",
        "The Group Chat Confession That Destroyed a 5-Year Friendship",
        "The Security Guard's Last Warning Text From the 13th Floor",
    ],
    "21_ai_tools_hacks": [
        "3 Secret AI Websites That Feel Completely Illegal to Know",
        "How to Use Free AI Tools to Automate Your Entire Work Week",
        "The AI Workflow That Generates 30 Days of Content in 10 Minutes",
        "Stop Wasting Hours: 3 AI Tools That Replace an Entire Agency",
        "The Best Hidden ChatGPT Prompts That Give God-Mode Answers",
    ],
    "22_emoji_guess_game": [
        "Guess The Famous Hollywood Movie By Emoji in 5 Seconds",
        "Emoji Quiz: Can You Guess The Famous Global Brand?",
        "Can You Guess The Song Title From These 3 Emojis Before Time Runs Out?",
        "Emoji IQ Challenge: 90% of Viewers Miss the Last Level",
        "Guess The Country From These 3 Emojis (Impossible Level)",
    ],
    "23_fitness_nutrition_hacks": [
        "3 Quick Fat-Loss Hacks Backed by Science (Zero Starvation)",
        "The One Morning Habit That Doubles Your Metabolic Rate",
        "3 Gym Mistakes Keeping You Skinny-Fat and How to Fix Them",
        "Why Doing 100 Crunches Won't Give You Six-Pack Abs",
        "The High-Protein Snack Secret That Destroys Sugar Cravings",
    ],
    "24_sigma_character_study": [
        "How to Build an Unbreakable Sigma Aura (Psychological Breakdown)",
        "Why High-Value Individuals Never Explain Themselves to Fools",
        "The Silent Body Language Habits That Demand Instant Respect",
        "Why the Lone Wolf Always Survives the Coldest Winters",
        "3 Psychological Boundaries You Must Never Let Anyone Cross",
    ],
    "25_celebrity_net_worth": [
        "How Much Money Hollywood Superstars Actually Take Home After Taxes",
        "The Secret Investment Portfolios of the World's Richest Athletes",
        "How Keanu Reeves Quietly Donated Millions Without Telling the Media",
        "From Bankruptcy to Billions: The Wildest Celebrity Financial Comebacks",
        "The Most Absurd Purchases Billionaire Celebrities Actually Made",
    ],
    "26_dangerous_places": [
        "The Most Dangerous Forbidden Islands on Earth No Human Can Visit",
        "5 Terrifying Places on Earth Where You Will Die in Minutes",
        "The Gates of Hell: The Turkmenistan Crater Burning for 50 Years",
        "Why You Are Strictly Forbidden from Stepping Foot on Snake Island",
        "The Death Valley Salt Flats Where Rocks Move on Their Own",
    ],
    "27_common_myths_busted": [
        "5 Historical Myths That Everyone Still Believes Are True",
        "The Lie About Shaving That Even Doctors Believed for Decades",
        "Why Everything You Know About the Bermuda Triangle Is Fabricated",
        "3 Food Myths Debunked: Carbs Do Not Actually Make You Fat",
        "Napoleon Wasn't Short: The Truth Behind History's Biggest Smear",
    ],
    "28_dream_meanings": [
        "What Falling in Your Dreams Actually Means (Subconscious Warning)",
        "The Psychological Reason Why You Dream About Your Teeth Falling Out",
        "Why You Keep Seeing the Same Person in Your Dreams Over and Over",
        "What It Means When You Can't Run or Scream in a Nightmare",
        "Lucid Dreaming: How to Take Full Control of Your Dreams Tonight",
    ],
    "29_optical_illusions_iq": [
        "Only People With 130+ IQ Can Spot The Hidden Animal in 7 Seconds",
        "This Optical Illusion Will Trick Your Brain in 3 Seconds Flat",
        "Look at the Dot in the Center: What Happens Next Will Shock You",
        "Is the Circle Moving or Standing Still? The Eye Trick Explained",
        "Only 1 Out of 10 People Can Find the Odd Number in This Image",
    ],
    "30_poetry_quotes": [
        "3 Hauntingly Beautiful Quotes on Love and Silent Heartbreak",
        "The Most Painful Lines Ever Written in English Literature",
        "Words That Will Comfort You on Your Darkest Loneliest Nights",
        "3 Timeless Quotes on Letting Go and Finding Peace Within",
        "The Poetry Line That Saved Countless Souls From Despair",
    ],
    "31_supercars_automotive": [
        "Bugatti Tourbillon: 1800HP V16 Insane Engineering Secrets",
        "Why The Koenigsegg Jesko Might Be The Last Hypercar of Its Kind",
        "The Real Reason Ferrari Bans Celebrities From Buying Their Cars",
        "How Porsche Engineered the Most Reliable Supercar in History",
        "3 Supercars That Were So Dangerous They Got Banned Immediately",
    ],
    "32_legal_consumer_hacks": [
        "3 Hidden Rights Airlines Don't Want You to Know About Flights",
        "The Secret Law That Forces Hotels to Give You Free Room Upgrades",
        "3 Sneaky Contract Clauses Landlords Use to Steal Your Deposit",
        "How to Legally Wipe Unfair Negative Items Off Your Credit Report",
        "The One Word You Must Say to Debt Collectors to Stop Calls Instantly",
    ],
    "33_parenting_child_hacks": [
        "3 Words You Should Never Say to an Angry Child (Child Psychology)",
        "How to Stop a Toddler Tantrum in 10 Seconds Without Yelling",
        "The Secret to Raising Mentally Resilient Kids in a Digital World",
        "Why Rewarding Good Grades With Cash Actually Destroys Motivation",
        "3 Gentle Parenting Phrases That Immediately De-escalate Conflict",
    ],
    "34_gaming_easter_eggs": [
        "3 Terrifying Easter Eggs Hidden in GTA 5 for Over a Decade",
        "The Dark Secret Hidden in Minecraft's Deepest Caverns",
        "5 Secret Rooms in Video Games That Took Players Years to Discover",
        "The Creepy Ghost Mystery in Red Dead Redemption 2 Explained",
        "Why Developers Hid a Real Cry for Help Inside This Retro Game",
    ],
    "35_animal_kingdom_stories": [
        "Why Even Pride of Lions Fear The Fearless Honey Badger",
        "The Orca Whale That Outsmarted Marine Biologists for 3 Decades",
        "Why Crows Never Forget a Human Face (Scientific Experiment)",
        "The Parasite That Literally Turns Ants Into Real-Life Zombies",
        "How an Elephant Reunited With Its Human Rescuer After 15 Years",
    ],
    "36_kids_animation": [
        "The Curious Little Fox and The Secret of The Starlight Mountain",
        "Why Do We Need Sleep? A Fun Bedtime Adventure for Kids",
        "The Mystery of the Disappearing Colors in the Magic Forest",
        "How The Brave Little Turtle Learned to Swim Across the Big Ocean",
        "The Friendly Dragon Who Was Afraid of the Dark",
    ],
    "37_interactive_quiz": [
        "5-Question General Knowledge IQ Test: 90% Get at Least One Wrong",
        "Can You Pass This Grade 5 Science Quiz Without Cheating?",
        "Geography Trivia: Name These 5 Capitals in Under 15 Seconds",
        "Quick History Quiz: Which of These 4 Events Happened First?",
        "The 60-Second Mind Challenge: Only Geniuses Score 5 Out of 5",
    ],
}


def get_curated_topics_for_niche(niche_id: str, lang: str = "tr") -> List[str]:
    """Returns curated viral topic pool tailored by niche and language."""
    canonical = resolve_canonical_niche(niche_id) or niche_id
    if (lang or "").lower().startswith("en"):
        topics = CURATED_NICHE_TOPICS_EN.get(niche_id) or CURATED_NICHE_TOPICS_EN.get(canonical)
        if topics:
            return list(topics)
        return list(CURATED_NICHE_TOPICS_EN.get("7_dark_psychology", []))
    topics = CURATED_NICHE_TOPICS.get(niche_id) or CURATED_NICHE_TOPICS.get(canonical)
    if topics:
        return list(topics)
    return list(CURATED_NICHE_TOPICS.get("1_news_flash", []))

