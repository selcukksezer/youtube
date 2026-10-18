# -*- coding: utf-8 -*-
"""Comprehensive curated viral topic vault for all 37 YouTube Shorts niches.

Provides rich, authentic, high-CTR, psychological-hook topic pools tested for Shorts engagement.
Eliminates generic boilerplate and repetitive cliches.
"""
from __future__ import annotations
from typing import Dict, List

from .niche_topic_vault_data import NICHE_ALIASES, CURATED_NICHE_TOPICS_EN


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
        "Avrupa Merkez Bankası'ndan Dijital Euro İçin Kritik Takvim Açıklaması",
        "Kuantum Bilgisayarlarda Tarihi Eşik Aşıldı: Şifreleme Sistemleri Riskte mi?",
        "Küresel Çip Krizinde Yeni Dalga: Teknoloji Fiyatları Nasıl Etkilenecek?",
        "Güneş Fırtınası Uyarısı: Uydu ve İletişim Ağı İçin Kritik 48 Saat",
        "Otonom Sürüş Teknolojisinde Yeni Yasa: Sorumluluk Kime Ait Olacak?",
        "Dünya Sağlık Örgütü'nden Modern Çağda Uyku ve Stres Raporu",
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
        "Komşumuzun Bize Yıllarca İyi Davranmasının Arkasındaki Ürpertici Neden",
        "Nişanlımın Bekarlığa Veda Partisinde Yaşananları Öğrenince Düğünü Bitirdim",
        "Şirkette Yanlışlıkla Tüm Çalışanlara Gönderilen E-posta Her Şeyi İfşa Etti",
        "AITA: Benden Habersiz Evimi Akrabalarına Açan Eşime Kilitleri Değiştirdim",
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
        "Gece Vardiyasında Güvenlik Kamerasında Gördüğüm Açıklanamayan Görüntü",
        "İkinci El Aldığım Arabanın Torpidosundan Çıkan Şifreli Not Defteri",
        "Ormanda Kamp Yaparken Çadırımızın Dışında Bırakılan Tuhaf Semboller",
        "Yanlış Numaradan Gelen Sesli Mesaj Bir Suçu Önlememi Sağladı",
    ],
    "4_would_you_rather": [
        "Zamanı Durdurabilmek mi Yoksa Geleceği Görmek mi? İmkansız 4 Tercih!",
        "Dünyanın En Zengin İnsanı Olmak mı, Ölümsüz Olmak mı? Hangisini Seçersin?",
        "Tüm Dilleri Anında Konuşabilmek mi Yoksa Hayvanlarla Konuşabilmek mi?",
        "10 Milyon Dolar mı Yoksa Zihnini %100 Kapasiteyle Kullanabilmek mi?",
        "Asla Yalan Söyleyememek mi Yoksa Kimsenin Yalanını Fark Edememek mi?",
        "Her Gün 1 Saat Fazladan Yaşamak mı Yoksa Hiç Uyumaya İhtiyaç Duymamak mı?",
        "En Büyük Korkunla Yüzleşmek mi, En Sevdiğin Anıyı Sonsuza Dek Unutmak mı?",
        "Görünmez Olabilmek mi Yoksa Işınlanabilmek mi? Kararını Ver!",
        "Geçmişteki Bir Hatayı Düzeltmek mi Yoksa 10 Yıl Sonrasını Görmek mi?",
        "İnsanların Zihnini Okumak mı Yoksa Duygularını Kontrol Edebilmek mi?",
        "Ömür Boyu Ücretsiz Seyahat mi Yoksa Hayalindeki Evin Tapusu mu?",
        "Sadece Gerçeği Duyabilmek mi Yoksa Herkesi İkna Edebilmek mi?",
    ],
    "5_guess_flag_country": [
        "Sadece Gerçek Coğrafya Dahilerinin %10'u Bu 5 Bayrağı Doğru Biliyor!",
        "Hangi Ülke? Başkentinden ve Para Biriminden Ülkeyi 3 Saniyede Tahmin Et!",
        "Renkleri Birbirine Çok Benzeyen 4 Bayrak: Hangisi Hangi Ülkeye Ait?",
        "Haritadaki Şeklinden Ülkeyi Bulabilir misin? En Zor 5 Soru!",
        "Bu Bayrak Hangi Kıtada? İpuçlarını Takip Et ve Cevabı Bul!",
        "Dünyanın En İlginç ve Bilinmeyen 5 Ülke Bayrağı!",
        "Üzerinde Ejderha ve Kılıç Olan Bu 4 Sıra Dışı Bayrağı Tanıyabilecek misin?",
        "3 İpucunda Gizli Ülkeyi Bul: Coğrafya Bilgini Test Et!",
        "Bayrağında Mor Renk Bulunan Dünyadaki O Nadir Ülkeleri Biliyor musun?",
        "Sınır Komşularından Hangi Ülke Olduğunu 5 Saniyede Tahmin Et!",
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
        "Amor Fati: Başına Gelen Her Zorluğu Güce Dönüştüren Stoacı Sır",
        "Seneca'nın Zamanın Kıymeti Üzerine Sizi Uyandıracak 3 Sert Uyarısı",
        "Hakaret ve Eleştirilere Karşı Marcus Aurelius'un Sarsılmaz Sessizlik Kuralı",
        "Kıbrıslı Zenon'un Her Şeyini Kaybettiğinde Bulduğu Zihinsel Özgürlük",
        "İradeyi Çelikleştiren ve Ertelemeyi Bitiren 3 Günlük Stoacı Pratik",
        "Kaybetme Korkusunu Yenen 'Premeditatio Malorum' Zihin Egzersizi",
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
        "Ayna Tekniği (Mirroring): İnsanların Size Hızla Güvenmesini Sağlayan Sır",
        "Gizli Kıskançlığı Ele Veren 4 İnce Davranış ve Mikro İfade",
        "Narsistlerin Sizi Suçlu Hissettirmek İçin Kullandığı DARVO Tuzağı",
        "İlk İzlenimde Karizmayı 2 Katına Çıkaran 3 Ses Tonu ve Bakış Kuralı",
        "Benjamin Franklin Etkisi: Sizi Sevmeyen Birini Kazanmanın Psikolojik Yolu",
        "Duygusal Şantajı Fark Etmenin ve Sınır Koymanın 3 Keskin Yöntemi",
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
        "Piyasa Çökerken Panik Satışı Yapmayan Yatırımcıların 3 Risk Kuralı",
        "Tokenomics Analizi: Bir Projenin Çöp Olup Olmadığını 3 Dakikada Anlayın",
        "Kurumsal Fonların Bitcoin Biriktirirken Kullandığı Likidite Tuzağı",
        "Kâr Satışı (Take Profit) Yapamayanların Boğa Sonunda Yaşadığı Büyük Kayıp",
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
        "İnsan Beyninin Uyku Sırasında Yaptığı 5 İnanılmaz İşlem",
        "Antarktika Buzullarının Altında Keşfedilen 5 Sıra Dışı Bilimsel Gerçek",
        "Zaman Algımızı Tamamen Değiştiren 5 Şaşırtıcı Tarihsel Kıyaslama",
        "Okyanusların Henüz Keşfedilmemiş Derinliklerindeki 5 Tuhaf Canlı",
    ],
    "10_religious_quotes": [
        "Hz. Peygamber'in 'Ameller Niyetlere Göredir' Hadisi ve Hikmeti (Buhari)",
        "Resulullah'ın 'Müslüman Müslümanın Kardeşidir' Hadisi (Buhari, Müslim)",
        "Peygamber Efendimiz'in 'Kolaylaştırınız, Zorlaştırmayınız' Hadisi (Buhari)",
        "İki Büyük Nimet: Sağlık ve Boş Vakit Hadis-i Şerifi ve Hikmeti (Buhari)",
        "Kendisi İçin İstediğini Kardeşi İçin de İsteme Hadis-i Şerifi (Buhari)",
        "Merhamet Etmeyene Merhamet Olunmaz Hadis-i Şerifi ve Mesajı (Müslim)",
        "Sizin En Hayırlınız Kur'an'ı Öğrenen ve Öğretendir Hadisi (Buhari)",
        "Rabbinizin Müjdesi: 'Şükrederseniz Nimetimi Artırırım' (İbrahim Suresi 7)",
        "Güzel Söz Sadakadır: Nezaket ve Tebessüm Hadis-i Şerifi (Buhari)",
        "Dua Müminin Silahıdır: Zor Zamanlarda Okunacak Nebevî Niyaz (Tirmizi)",
        "Bizi Aldatan Bizden Değildir: Doğruluk ve Emanet Hadisi (Müslim)",
        "Kalbinde Zerre Kadar Kibir Olan Cennete Giremez Hadisi (Müslim)",
        "Gıybet ve Dedikodudan Sakınmanın Önemi Hadis-i Şerifi (Ebu Davud)",
        "İlim Öğrenmek Her Müslümana Farzdır Hadis-i Şerifi (İbn Mace)",
        "Sabır ve Namazla Allah'tan Yardım İsteyin Ayeti (Bakara Suresi 153)",
        "Kalpler Ancak Allah'ı Anmakla Huzur Bulur Ayet-i Kerimesi (Rad 28)",
        "Her Zorluğun Yanında Bir Kolaylık Vardır Müjdesi (İnşirah Suresi 5-6)",
        "Peygamber Efendimiz'in Sıkıntı Anında Okuduğu Huzur Duası (Tirmizi)",
        "Allah Bize Yeter, O Ne Güzel Vekildir Ayeti (Al-i İmran Suresi 173)",
        "Allah'ın Rahmetinden Ümidinizi Kesmeyin Müjdesi (Zümer Suresi 53)",
        "Kim Allah'tan Korkarsa Ona Bir Çıkış Yolu Açar (Talak Suresi 2-3)",
        "Rabbin Seni Terk Etmedi ve Sana Darılmadı Tesellisi (Duha Suresi 3)",
        "Allah Kimseye Gücünün Yettiğinden Fazlasını Yüklemez (Bakara 286)",
        "Gerçek Pehlivan Öfke Anında Nefsine Hakim Olandır Hadisi (Buhari)",
        "Komşusu Açken Tok Yatan Bizden Değildir Hadis-i Şerifi (Hâkim)",
        "Veren El Alan Elden Üstündür: İnfak ve Cömertlik Hadisi (Buhari)",
        "Kişi Sevdiği İle Beraberdir Hadis-i Şerifi ve Hikmeti (Buhari, Müslim)",
        "Dünyada Bir Garip veya Yolcu Gibi Ol Hadis-i Şerifi (Buhari)",
        "Müminin İşine Şaşılır: Sabreder Kazanır, Şükreder Kazanır (Müslim)",
        "Cennet Annelerin Ayakları Altındadır: Anne Hakkı Hadisi (Nesai)",
        "Zandan Çokça Sakının ve Birbirinizin Kusurunu Aramayın (Hucurat 12)",
        "İnsanlara Teşekkür Etmeyen Allah'a Şükretmiş Olmaz Hadisi (Tirmizi)",
        "Allah Sizin Suretlerinize Değil Kalplerinize Bakar Hadisi (Müslim)",
        "Hayra Vesile Olan, O Hayrı Yapan Gibidir Hadis-i Şerifi (Tirmizi)",
        "Yeryüzündekilere Merhamet Edin ki Gökteki de Size Merhamet Etsin (Tirmizi)",
        "Sabah ve Akşam Okunduğunda Kötülüklerden Koruyan Nebevî Dua (Ebu Davud)",
    ],
    "11_language_learning": [
        "İngilizce Konuşurken En Çok Yapılan ve Türkçeden Çevrilen 5 Hata",
        "Dizi ve Film İzleyerek 3 Ayda Akıcı İngilizce Konuşmanın 3 Sırrı",
        "Yerli Konuşmacıların (Native) Günlük Hayatta Kullandığı 5 Harika Deyim",
        "İngilizce Kelimeleri Asla Unutmamak İçin Spaced Repetition Tekniği",
        "İş Görüşmelerinde Sizi Profesyonel Gösterecek 5 İngilizce Cümle Kalıbı",
        "Yabancı Dil Öğrenirken Telaffuzunuzu Kusursuzlaştıran Gölgeleme Tekniği",
        "'Very' Kelimesini Bırakın: İngilizcenizi Üst Seviyeye Taşıyan 5 Kelime",
        "Yurt Dışı Seyahatlerinde Hayat Kurtaran 5 Pratik İngilizce Kalıp",
        "İngilizce Düşünme Alışkanlığı Kazandıran 3 Dakikalık Günlük Egzersiz",
        "En Çok Karıştırılan 5 İngilizce Phrasal Verb ve Pratik Örnekleri",
    ],
    "12_amazon_affiliate": [
        "Hayatınızı Kolaylaştıracak 3 Akıllı Ev ve Mutfak Ürünü",
        "TikTok'ta Viral Olan ve Gerçekten İşe Yarayan 3 İnanılmaz Amazon Gadgeti",
        "Çalışma Masanızın Havasını Tamamen Değiştirecek 3 Minimalist Masaüstü Ürün",
        "Seyahat Edenlerin Yanından Asla Ayırmadığı 3 Pratik ve Kompakt Aksesuar",
        "Evde Saatlerce Vakit Kazandıracak 3 Çok Fonksiyonlu Mutfak Aleti",
        "Fiyatını Son Kuruşuna Kadar Hak Eden 3 Gizli Kalmış Fiyat/Performans Ürünü",
        "Bütçe Dostu Ama Aşırı Lüks Duran 3 Akıllı Ev Teknolojisi",
        "Kablo Dağınıklığını Sonsuza Dek Bitiren 3 Dahiyane Düzenleyici",
        "Arabanızda Mutlaka Bulunması Gereken 3 Hayat Kurtarıcı Aksesuar",
        "Küçük Odaları İki Kat Geniş Gösteren 3 Akıllı Depolama Çözümü",
        "Kamp ve Doğa Tutkunları İçin 3 İnanılmaz Taşınabilir Ekipman",
        "Telefonunuzu Profesyonel Stüdyoya Çeviren 3 Uygun Fiyatlı Aksesuar",
    ],
    "ancient_remedies_egypt": [
        "Antik Mısır'da Firavunların Hastalıklara Karşı Kullandığı Gizli Ot",
        "Modern Tıbbın Bile Şaşırdığı 3.000 Yıllık Şifa Reçetesi",
        "Kleopatra'nın Güzellik ve Gençlik Sırrı Olarak Bilinen Efsanevi Karışım",
        "Sümerlerin Baş Ağrısını Kesmek İçin Çiğnediği O Bilinmeyen Kök",
        "Eski Medeniyetlerin Doğal Antibiyotik Olarak Kullandığı 3 Güçlü Madde",
        "İbn-i Sina'nın El-Kanun fi't-Tıb Eserinde Önerdiği 3 Doğal Besin Sırrı",
        "Antik Yunan'da Hipokrat'ın Bağışıklık İçin Kullandığı Altın Karışım",
        "Osmanlı Saray Hekimlerinin Kış Hastalıklarına Karşı Hazırladığı Macun",
    ],
    "13_mystery_paranormal": [
        "1971'de Uçaktan Paraşütle Atlayıp Sırra Kadem Basan D.B. Cooper Dosyası",
        "Bermuda Şeytan Üçgeni Hakkında Bilim İnsanlarının Son Açıklaması",
        "Dyatlov Geçidi Vakası: Karlar Altında 9 Dağcının Çözülemeyen Gizemi",
        "Dünyanın En Gizemli Ses Kaydı: Okyanusun Dibindeki 'The Bloop'",
        "Mısır Piramitlerinin Hizalanmasındaki Akıl Almaz Astronomik Hassasiyet",
        "Voynich El Yazması: 600 Yıldır Hiç Kimsenin Çözemediği Şifreli Kitap",
        "Zaman Yolculuğu İddiasıyla Tarihe Geçen İnsanlar ve Tuhaf Kanıtlar",
        "Mary Celeste Gemisi: Mürettebatı Buharlaşan Hayalet Geminin Sırrı",
        "Göbeklitepe'deki 12.000 Yıllık Sütunların Çözülemeyen Astronomik Şifresi",
        "Tunguska Olayı: 1908'de Sibirya'da 80 Milyon Ağacı Yok Eden Patlama",
        "Roanoke Kolonisi: Bir Gecede İz Bırakmadan Kaybolan 115 İnsanın Gizemi",
        "Uzaydan Gelen 72 Saniyelik 'Wow! Sinyali' ve Çözülemeyen Kaynağı",
    ],
    "14_movie_summaries": [
        "Son Sahnesinde Beyninizi Yakacak ve Günlerce Düşündürecek 3 Ters Köşe Film",
        "IMDb Puanı 8 Üzeri Olan Ama Kimsenin Bilmediği 3 Gizli Başyapıt",
        "Tek Bir Mekanda Geçen Ama Nefesinizi Kesecek 3 Gerilim Filmi",
        "İzledikten Sonra Hayata Bakışınızı Değiştirecek 3 Felsefi Sinema Başyapıtı",
        "Gerçek Bir Olaydan Uyarlanan ve Tüylerinizi Ürpertecek 3 Polisiye Suç Filmi",
        "Christopher Nolan'ın Zihin Bükücü Anlatım Teknikleri ve Gizli İpuçları",
        "Zaman Döngüsü Konusunu En İyi İşleyen 3 Unutulmaz Bilim Kurgu Filmi",
        "Kötü Karakterin Aslında Haklı Olduğunu Düşündüren 3 Efsane Film",
        "İlk 10 Dakikasında İzleyiciyi Ekrana Kilitleyen 3 Sürükleyici Başyapıt",
    ],
    "15_football_transfers": [
        "Dünya Futbolunu Sarsacak Yılın En Büyük 3 Transfer İddiası",
        "Bedavaya Alınıp Kulübüne 100 Milyon Euro Kazandıran 4 Transfer Dehası",
        "Tarihin En Pahalı Ama En Büyük Hayal Kırıklığı Yaratan 3 Futbolcusu",
        "Süper Lig Kulüplerinin Gizlice Takip Ettiği 3 Genç Yıldız Adayı",
        "Bir İmza ile Tarihi Değişen Efsanevi Transfer Çalımları",
        "Real Madrid ve Manchester City'nin Gelecek Sezon Kuracağı Rüya Kadrolar",
        "Sözleşmesindeki Tek Bir Gizli Maddeyle Serbest Kalan Yıldız Futbolcular",
        "Son Dakikada Faks Makinesi Yüzünden İptal Olan Tarihi Transfer",
        "Alt Ligden Çıkıp Şampiyonlar Ligi Finaline Damga Vuran 3 İnanılmaz Hikaye",
    ],
    "16_wealth_entrepreneurship": [
        "En Zengin %1'lik Kesimin Asla Taviz Vermediği 3 Sabah Alışkanlığı",
        "Sıfırdan Milyon Dolarlık Şirket Kuran Girişimcilerin 3 Ortak Özelliği",
        "Elon Musk'ın Zamanı 5 Dakikalık Bloklara Bölen Üretkenlik Metodu",
        "Warren Buffett'tan Gençlere Para ve Yatırım Hakkında 3 Altın Kural",
        "Zenginlerin Asla Satın Almadığı Ama Orta Sınıfın Para Harcadığı 3 Şey",
        "Steve Jobs'ın Sadeleşme ve Odaklanma Felsefesi ile Başarıya Ulaşma",
        "Bileşik Getirinin Gücü: Küçük Birikimler 10 Yılda Nasıl Servete Dönüşür?",
        "Varlık ve Yükümlülük Farkı: Finansal Özgürlüğün İlk 3 Adımı",
        "Naval Ravikant'ın Zenginlik ve Kaldıraç Üzerine 4 Ezber Bozan İlkesi",
        "Maaşlı Çalışırken Yan Gelir İnşa Etmenin 3 Gerçekçi Stratejisi",
    ],
    "17_before_after_evolution": [
        "Son 50 Yılda Dünyanın En Büyük Şehirlerinin İnanılmaz Değişimi!",
        "Teknolojinin 20 Yılda Hayatımızdan Sildiği ve Unutturduğu 5 Şey",
        "Otomobil Tasarımlarının 1920'den Günümüze Akıl Almaz Evrimi",
        "Çocukken Oynadığımız Efsane Oyunların Bugünkü Halleri (Before vs After)",
        "Gökdelenlerin Olmadığı Dönemde İstanbul ve New York Manzaraları",
        "İlk Cep Telefonundan Günümüz Katlanabilir Ekranlarına 40 Yıllık Evrim",
        "100 Yıl Önce İnsanların 2020'li Yıllar İçin Yaptığı Şaşırtıcı Tahminler",
        "Fotoğrafçılığın Siyah Beyaz Karanlık Odadan Yapay Zekaya Dönüşümü",
    ],
    "18_astrology_horoscope": [
        "Bu Hafta Gökyüzünde Yaşanan Yeni Ay Hangi 3 Burcun Kaderini Değiştirecek?",
        "Zodyak'ın Asla Yalanı Affetmeyen ve En Sezgisel 3 Güçlü Burcu",
        "Merkür Retrosundan En Çok Etkilenecek Burçlar ve Korunma Yolları",
        "Aşk ve İlişkilerde Birbiriyle En Uyumlu 4 Mükemmel Burç Çifti",
        "Kariyerinde Büyük Bir Atılım Yapacak Olan 3 Şanslı Burç!",
        "Su Grubu Burçlarının Kimseye Göstermediği Derin Sezgi Gücü",
        "Ateş Grubu Burçlarının Liderlik ve Kriz Anındaki Kararlılık Sırrı",
        "Toprak Grubu Burçlarının Finans ve Güvende Kalma Stratejileri",
    ],
    "19_historical_battles": [
        "Tarihin Akışını Değiştiren ve 1 Saatte Biten En Kritik 3 Savaş",
        "Fatih Sultan Mehmed'in Gemileri Karadan Yürütme Dehası ve Planı",
        "Çanakkale'de Seyit Onbaşı'nın 276 Kiloluk Mermiyi Kaldırdığı O An",
        "Mohaç Meydan Muharebesi: 2 Saatte Kazanılan Tarihin En Hızlı Zaferi",
        "Kurtuluş Savaşı'nda Büyük Taarruz'un Gizli Başlangıç Planı ve Stratejisi",
        "Hannibal'ın Cannae Savaşı'nda Uyguladığı Efsanevi Hilal Taktik Dehası",
        "Preveze Deniz Zaferi: Barbaros Hayreddin Paşa'nın Dahi Rüzgar Manevrası",
        "Malazgirt Meydan Muharebesi'nde Sultan Alparslan'ın Turan Taktiği",
        "Stalingrad Kuşatması: 2. Dünya Savaşı'nın Kaderini Değiştiren Kırılma",
    ],
    "20_whatsapp_chat_story": [
        "Mesajı Yanlışlıkla Şirket Grubuna Atınca Yaşanan Akıl Almaz Kaos!",
        "Gecenin 3'ünde Eski Sevgiliden Gelen O Beklenmedik WhatsApp Mesajı",
        "Annemin Gönderdiği Yanlış Konum Sayesinde Öğrendiğim Aile Sırrı",
        "Ev Arkadaşımın Odasından Gelen Sesler ve Sonrasında Yazdığı İtiraf Mesajı",
        "İki Kardeş Arasında Geçen ve Herkesi Gözyaşlarına Boğan O Konuşma",
        "Apartman WhatsApp Grubuna Gece Yarısı Atılan Gizemli Güvenlik Uyarısı",
        "Kuryenin Bıraktığı Not ve Sonrasında Gelen Şok Edici Mesajlaşma",
        "5 Yıldır Kapalı Olan Numaradan Gelen Tek Cümlelik Mesaj",
    ],
    "21_ai_tools_hacks": [
        "Yapay Zeka ile Pasif Gelir Elde Etmenin 2026'da En Etkili 3 Yolu",
        "Kimsenin Bilmediği Ama Hayat Kurtaran 4 Ücretsiz Yapay Zeka Sitesi",
        "Kod Yazmadan Yapay Zekayla Web Sitesi ve Uygulama Geliştirme Rehberi",
        "ChatGPT ve Claude Kullanırken Profesyonellerin Uyguladığı 3 Prompt Sırrı",
        "Sesinizi ve Yüzünüzü Mükemmel Klonlayan En Yeni Yapay Zeka Teknolojileri",
        "Öğrencilerin ve Çalışanların İşini Yarıya İndiren 3 Üretkenlik AI Aracı",
        "10 Dakikada 1 Aylık Sosyal Medya İçeriği Üreten Yapay Zeka İş Akışı",
        "PDF ve Uzun Dokümanları Saniyeler İçinde Özetleyen 3 Ücretsiz AI Aracı",
        "Eski ve Bulanık Fotoğrafları 4K Kaliteye Çıkaran Yapay Zeka Araçları",
    ],
    "22_emoji_guess_game": [
        "Bu Emojilerden Hangi Ünlü Filmi Anlatıyoruz? Sadece Sinemaseverler Bilir!",
        "Emojileri Birleştir Şarkıyı Bul! 5 Soruluk Eğlenceli Müzik Testi",
        "Emojilerle Anlatılan Şehri Tahmin Edebilir misin? En Zor 4 Soru!",
        "Bu 3 Emoji Hangi Tarihi Olayı Simgeliyor? Cevabı Tahmin Et!",
        "Emojilerden Ünlü Markayı 5 Saniyede Bulabilir misin? Hızlı Test!",
        "Bu 4 Emoji Hangi Atasözünü Anlatıyor? Sadece %10'u Hepsini Biliyor!",
    ],
    "23_fitness_nutrition_hacks": [
        "Günde 15 Dakika Yaparak Göbek Yağlarını Hızla Eriten 3 Bilimsel Hareket",
        "Her Sabah Kahveye Bunu Eklerseniz Metabolizmanız İki Kat Hızlı Çalışır",
        "Kas Gelişimini Yarıda Kesen En Yaygın 3 Ağır Antrenman Hatası",
        "Aç Kalmadan ve Diyet Yapmadan Kilo Vermenin 4 Biyolojik Sırrı",
        "Yorgun Uyanmayı Sonsuza Dek Bitiren Uyku ve Magnezyum Tüyosu",
        "Testosteron Seviyesini Doğal Yollarla Artıran 3 Temel Besin Kaynağı",
        "Yemekten Sonra 10 Dakika Yürümenin Kan Şekerine İnanılmaz Etkisi",
        "Tatlı Krizini 3 Dakikada Kesip Tok Tutan Yüksek Proteinli Ara Öğün",
        "Masa Başı Çalışanlarda Sırt ve Boyun Ağrısını Bitiren 3 Esneme Hareketi",
    ],
    "24_sigma_character_study": [
        "Thomas Shelby'nin Manipülasyonlara Karşı Kullandığı Soğukkanlı Duruş Sırrı",
        "Sigma Erkeklerin Asla Taviz Vermediği ve Sessizce Uyguladığı 3 Kural",
        "Baskı Altında Asla Paniklemeyen İnsanların Zihinsel Dayanıklılık Formülü",
        "İnsanların Saygısını Zorlamadan Kazanan Karakterlerin 3 Gizli İlkesi",
        "Göz Teması ve Beden Diliyle Otorite Kurmanın En Güçlü Psikolojik Yolları",
        "John Wick Arketipi: Az Konuşup Sonuçla Konuşanların Disiplin Sırrı",
        "Onaylanma İhtiyacını Bitiren ve Öz Saygıyı İnşa Eden 3 Keskin Sınır",
        "Kalabalıkta Bile Kendi Merkezini Koruyan Yalnız Liderlerin 3 Alışkanlığı",
    ],
    "25_celebrity_net_worth": [
        "Dünyanın En Çok Kazanan 3 YouTube İçerik Üreticisinin Aylık Geliri",
        "Cristiano Ronaldo'nun Dakikada Kazandığı Para ve Gayrimenkul İmparatorluğu",
        "Milyarderlerin Servetlerini Nasıl Koruduğu ve Vergi Stratejileri",
        "Hollywood Yıldızlarının Tek Bir Film İçin Aldığı Akıl Almaz Ücretler",
        "Keanu Reeves'in Milyonlarca Dolarlık Kazancını Sessizce Bağışlama Hikayesi",
        "İflastan Milyar Dolarlık Markaya Dönüşen Ünlülerin Finansal Geri Dönüşü",
        "Michael Jordan'ın Nike Anlaşmasıyla Kurduğu Milyar Dolarlık Gelir Modeli",
    ],
    "26_dangerous_places": [
        "Dünyanın Girişi Kesinlikle Yasak Olan En Tehlikeli 5 Gizli Bölgesi",
        "Kuzey Sentinel Adası: Modern Dünyayla Temas Kurmayan Son Kabile",
        "Yılan Adası (Ilha da Queimada Grande): İnsanların Adım Atamadığı Ada",
        "Çernobil Dışlama Bölgesi'nde Bugün Yaşanan Akıl Almaz Değişimler",
        "Ölüm Vadisi: 57 Derece Sıcaklıkta Doğa Nasıl Hayatta Kalıyor?",
        "Türkmenistan'daki 50 Yıldır Sönmeyen 'Cehennem Kapısı' Kraterinin Sırrı",
        "Svalbard Küresel Tohum Deposu: Kıyamet Günü Kasasının İçinde Ne Var?",
        "Danakil Çöküntüsü: Dünya Üzerinde Başka Bir Gezegene En Çok Benzeyen Yer",
    ],
    "27_common_myths_busted": [
        "Filmlerde Gördüğünüz ve Hayatta Sizi Yanıltabilecek 3 Hayatta Kalma Miti",
        "Günde 8 Bardak Su İçmek Zorunda mısınız? Bilimin Açıkladığı Gerçek!",
        "Beynimizin Sadece %10'unu mu Kullanıyoruz? İşte Nörolojik Gerçekler",
        "Karanlıkta Kitap Okumak Gözleri Bozar mı? Doğru Bilinen Yanlışlar!",
        "Yutulan Sakız Midede 7 Yıl Kalır mı? Doktorların Cevabı!",
        "Napolyon Gerçekten Kısa Boylu muydu? Tarihin En Büyük Algı Yanılgısı",
        "Boğalar Kırmızı Renge mi Saldırır? Deneylerle Kanıtlanan Şaşırtıcı Gerçek",
        "Üşümek Tek Başına Hasta Eder mi? Bağışıklık Sistemi Hakkında 3 Gerçek",
    ],
    "28_dream_meanings": [
        "Rüyanızda Yüksekten Düştüğünüzü Görmek Aslında Ne Anlama Geliyor?",
        "Diş Dökülmesi Rüyasının Bilinçaltınızdaki Şok Edici Psikolojik Sebebi",
        "Tanıdığınız Birini Rüyada Görmek Bilinçaltınızın Size Verdiği Hangi Mesaj?",
        "Tekrarlayan Rüyaların Ardındaki Gizli Anlam ve Bilinçaltı Uyarıları",
        "Rüyada Koşmak İsteyip Koşamamanın Nörolojik ve Psikolojik Açıklaması",
        "Lüsid Rüya (Lucid Dreaming): Rüyalarınızı Kontrol Etmenin 3 Bilimsel Adımı",
        "Rüyada Uçtuğunu Görmenin Özgürlük ve Bilinçaltı Hedeflerle İlişkisi",
    ],
    "29_optical_illusions_iq": [
        "Sadece Yüksek IQ'lu İnsanların İlk 5 Saniyede Fark Ettiği Gizli Detay!",
        "Bu Resim Hareket Etmiyor! Beyninizi Kandıran İnanılmaz Optik İllüzyon",
        "Resimdeki Gizlenmiş Hayvanı 7 Saniyede Bulabilir misin? Dikkat Testi!",
        "Gözlerinizin Sizi Yanılttığı 3 İnanılmaz Görsel İllüzyon Deneyi",
        "Aynı Renkte Olan İki Kareyi Beynimiz Neden Farklı Görüyor? (Gölge Testi)",
        "Merkezdeki Noktaya 10 Saniye Bakın: Renklerin Nasıl Kaybolduğunu Görün!",
    ],
    "30_poetry_quotes": [
        "Nazım Hikmet'ten Ruhunuzu Derinden Saracak En Güzel Aşk Dizeleri",
        "Özdemir Asaf'ın Yalnızlığı ve Sevgiyi Anlatan Unutulmaz 4 Cümlesi",
        "Cemal Süreya'dan Kalbe Dokunan ve Asla Eskimeyen Edebi Sözler",
        "Attila İlhan'ın Şiirlerindeki Derin Melankoli ve Sevda Anlatımı",
        "Sabahattin Ali'nin Kürk Mantolu Madonna Eserinden Kalbe İşleyen 3 Alıntı",
        "Turgut Uyar'ın 'Göğe Bakma Durağı' Şiirindeki Umut ve Kaçış İmgesi",
        "Cahit Sıtkı Tarancı'nın Zaman ve Ömür Üzerine Unutulmaz Dizeleri",
    ],
    "31_supercars_automotive": [
        "Bugatti Tourbillon: 1800 Beygirlik V16 Motorun Akıl Almaz Mühendisliği",
        "Dünyanın En Hızlı 3 Seri Üretim Otomobili ve Ulaştıkları Hız Rekorları",
        "Ferrari'nin Müşterilerine Getirdiği ve Asla Taviz Vermediği İlginç Kurallar",
        "Elektrikli Hiper Arabaların 0-100 Hızlanmasındaki Yerçekimi Karşıtı Fizik",
        "Koenigsegg Jesko Absolut: 500 Km/s Sınırını Zorlayan Aerodinamik Deha",
        "Porsche 911'in 60 Yıldır Değişmeyen Motor Konumunun Mühendislik Sırrı",
        "Le Mans 24 Saat Yarışında Ford ve Ferrari Arasındaki Efsanevi Rekabet",
    ],
    "32_legal_consumer_hacks": [
        "Uçuşunuz Rötar Yaptığında Havayolundan Alabileceğiniz Gizli Tazminat Hakkı",
        "İnternetten Aldığınız Ürünlerde Çoğu Kişinin Bilmediği 14 Gün İade Hakkı",
        "Kira Sözleşmesi Yaparken Kiracıların Mutlaka Bilmesi Gereken 3 Hukuki Madde",
        "Banka Kartı ve Kredi Kartı Aidatlarını Geri Almanın En Kolay Yolu",
        "Ayıplı Mal veya Bozuk Elektronik Üründe Ücretsiz Değişim Hakkınız",
        "İstenmeyen SMS ve Aramaları Tek İşlemle Kalıcı Olarak Engelleme Yöntemi",
        "Garanti Süresi Biten Üründe 'Gizli Ayıp' Kapsamında Hak Arama Rehberi",
    ],
    "33_parenting_child_hacks": [
        "Çocuğunuz Öfke Nöbeti Geçirdiğinde Asla Söylememeniz Gereken 3 Kelime",
        "Çocuklarda Ekran Bağımlılığını Kavgasız Bitiren 3 Etkili Psikolojik Yöntem",
        "Özgüvenli ve Sorumluluk Sahibi Çocuk Yetiştirmenin 3 Temel Prensibi",
        "Çocuğunuzun Ders Çalışma İsteğini Artıran Eğlenceli Öğrenme Taktikleri",
        "Kardeş Kıskançlığını Rekabetten İşbirliğine Dönüştüren 3 Ebeveyn Kuralı",
        "Çocuğun Yaratıcılığını ve Problem Çözme Becerisini Geliştiren 3 Oyun",
        "Övgü Tuzağı: Çocuğa 'Çok Zekisin' Demek Yerine Neden Çabasını Övmelisiniz?",
    ],
    "34_gaming_easter_eggs": [
        "GTA 5'te 10 Yıldır Çoğu Oyuncunun Kaçırdığı 3 Gizli Detay ve Sır",
        "Red Dead Redemption 2'deki En Korkutucu ve Çözülemeyen 3 Gizem",
        "Minecraft Dünyasındaki En Nadir Doğa Olayları ve Gizli Kodlar",
        "The Witcher 3'te Haritanın En Ucunda Gizlenen Unutulmaz Sürprizler",
        "Half-Life ve Portal Evrenlerini Birbirine Bağlayan 3 Gizli İpucu",
        "Cyberpunk 2077 Haritasında Geliştiricilerin Bıraktığı 3 Gizli Mesaj",
        "Oyun Tarihinde Oyuncuların Yıllar Sonra Çözebildiği En Zor Easter Egg",
    ],
    "35_animal_kingdom_stories": [
        "Dünyanın En Korkusuz Hayvanı Bal Porsuğunun Hayatta Kalma Mücadelesi",
        "Ahtapotların 3 Kalbi ve 9 Beyni ile Sahip Olduğu Uzaylı Benzeri Zeka",
        "Kurt Sürülerindeki Hiyerarşi ve Liderin Sürüyü Koruma Stratejisi",
        "Kargaların İnsan Yüzlerini Asla Unutmadığını Kanıtlayan Bilimsel Deney!",
        "Ölümsüz Denizanası (Turritopsis Dohrnii) Yaşlanmayı Nasıl Durduruyor?",
        "Katil Balinaların (Orka) Okyanusta Uyguladığı İnanılmaz Takım Taktikleri",
        "Göçmen Kuşların Binlerce Kilometre Yolu Pusulasız Bulma Sırrı",
    ],
    "36_kids_animation": [
        "Sevimli Hayvan Dostlarımız Ormanda Kaybolan Yıldızı Nasıl Buldu?",
        "Trafik Işıklarının Renkleri Bize Ne Anlatıyor? Eğlenceli Öğrenme Vakti!",
        "Dişlerimizi Düzenli Fırçalamazsak Ne Olur? Mikroplarla Mücadele Hikayesi!",
        "Meyve ve Sebzelerin Süper Güçleri: Hangi Vitamin Bizi Nasıl Güçlendirir?",
        "Küçük Arı Maya ve Arkadaşları Çiçeklerden Balı Nasıl Topluyor?",
        "Gezegenleri Tanıyalım: Güneş Sistemindeki Sekiz Kardeşin Maceraları!",
        "Paylaşmanın Mutluluğu: Küçük Sincabın Kış Hazırlığı Hikayesi",
    ],
    "37_interactive_quiz": [
        "5 Soruluk Genel Kültür Testi: Sadece %5'lik Kesim Hepsini Doğru Biliyor!",
        "Tarih Bilgini Test Et! Bu 4 Olaydan Hangisi Daha Önce Gerçekleşti?",
        "Hızlı Düşünme ve Zeka Testi: Bu Mantık Bilmecesini 10 Saniyede Çöz!",
        "Dünya Coğrafyası Canlı Test: Hangi Başkent Hangi Ülkeye Ait?",
        "Bilim ve Uzay Testi: 5 Soruda Kaç Doğru Yapabileceksin?",
        "Kelime Hazinesi Testi: Türkçede En Çok Yanlış Bilinen 5 Kelime Anlamı!",
        "Görsel Hafıza Testi: 5 Saniye Bak ve Eksik Detayı Bul!",
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


__all__ = [
    "NICHE_ALIASES",
    "CURATED_NICHE_TOPICS",
    "CURATED_NICHE_TOPICS_EN",
    "resolve_canonical_niche",
    "get_curated_topics_for_niche",
]
