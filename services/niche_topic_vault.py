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
