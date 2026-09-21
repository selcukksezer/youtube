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
    "weird_laws_world_map": {
        "id": "weird_laws_world_map",
        "name": "Sıra Dışı Yasalar + Dünya Haritası Animasyonu (Item 290)",
        "category": "Coğrafya & Hukuk",
        "rpm_tier": "Yüksek Merak & Paylaşım",
        "tone": "surprising, witty, educational",
        "hook_style": "'Bu ülkede sakız çiğnemek yasak!' diyerek haritada ülkenin parlaması.",
        "split_screen_default": False,
        "bg_style": "world map animation highlight country flag geography trivia",
        "loop_bridge": "...ve dünyanın en absürt yasalarından ilki tam olarak şu ülkede başlıyordu:",
        "system_prompt_addition": (
            "Dünyanın en garip ve absürt yasalarını ülke ülke anlat. "
            "Her yasa için haritada ilgili ülkeyi vurgula; Singapur, İsviçre, Japonya gibi örnekler kullan."
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
            "Gizliliği yeni kaldırılmış bir hükümet belgesi veya gizemli olay kurgusu yap. "
            "Gazete küpürü ve daktilo yazısı estetiğini vurgula."
        )
    },
    "animal_funny_dub": {
        "id": "animal_funny_dub",
        "name": "Hayvanlar Alemi + Komik İnsan Dublajı (Item 293)",
        "category": "Doğa & Mizah",
        "rpm_tier": "Yüksek Paylaşım",
        "tone": "humorous, sarcastic, anthropomorphic",
        "hook_style": "Hayvanın bakışına insanın iç sesi gibi mizahi monolog yazma.",
        "split_screen_default": False,
        "bg_style": "funny cat dog close up eyes wildlife portrait cinematic",
        "loop_bridge": "...ve o hayvanın aklından geçen ilk cümle aslında tam olarak şuydu:",
        "system_prompt_addition": (
            "Hayvanların bakış açısından birinci tekil mizahi iç ses dublajı yaz. "
            "Her sahne farklı bir hayvan portresi ve absürt insan düşüncesi içermeli."
        )
    },
    "dream_surreal_psychology": {
        "id": "dream_surreal_psychology",
        "name": "Rüya Tabirleri + Gerçeküstü Görseller (Item 294)",
        "category": "Psikoloji & Rüya",
        "rpm_tier": "Yüksek Kaydetme",
        "tone": "dreamy, surreal, introspective, mysterious",
        "hook_style": "Dali tarzı eriyen saatler ve uçan kapılar eşliğinde rüya analizi.",
        "split_screen_default": False,
        "bg_style": "surreal melting clock floating door dali dreamscape abstract",
        "loop_bridge": "...ve rüyanızın en garip anında gördüğünüz o sembol aslında şunu anlatıyordu:",
        "system_prompt_addition": (
            "Popüler rüya sembollerini psikolojik yorumla. "
            "Görseller gerçeküstü, eriyen saatler, uçan nesneler ve sisli rüya estetiği içermeli."
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
            "Gerçek bir polisiye vakayı veya gizemli kayboluşu adli tıp titizliğiyle anlat. "
            "Polis telsizi cızırtısı ve CCTV grain estetiğini vurgula."
        )
    },
    "optical_illusion_focus": {
        "id": "optical_illusion_focus",
        "name": "Optik İllüzyon + Canlı Odak Testi (Item 298)",
        "category": "İnteraktif & Görsel",
        "rpm_tier": "Yüksek Yorum & Paylaşım",
        "tone": "hypnotic, challenging, playful",
        "hook_style": "Merkeze 5 saniye odaklan, etrafındaki her şey hareket edecek.",
        "split_screen_default": False,
        "bg_style": "optical illusion spiral hypnotic pattern moving dots focus test",
        "loop_bridge": "...ve illüzyonun merkezine tekrar odaklandığınızda ilk fark ettiğiniz hareket şuydu:",
        "system_prompt_addition": (
            "Optik illüzyon ve odak testi kurgusu yap. İzleyiciye merkeze 5 saniye bakmasını söyle; "
            "sonra illüzyonun nasıl çalıştığını açıkla."
        )
    },
    "price_timeline_tunnel": {
        "id": "price_timeline_tunnel",
        "name": "Fiyat Karşılaştırması + Zaman Tüneli (Item 299)",
        "category": "Ekonomi & Nostalji",
        "rpm_tier": "Yüksek Merak",
        "tone": "nostalgic, shocking, comparative",
        "hook_style": "1990'da 100 dolarla neler alınıyordu, bugün neler alınıyor?",
        "split_screen_default": False,
        "bg_style": "vintage 1990s shopping mall retro price tag inflation timeline",
        "loop_bridge": "...ve enflasyonun gerçek yüzünü görmek için 1990'daki o ilk alışveriş sepetine dönelim:",
        "system_prompt_addition": (
            "Aynı para miktarının farklı yıllarda ne satın aldığını karşılaştır. "
            "1990 vs bugün somut ürün örnekleri ver; zaman tüneli hissi oluştur."
        )
    },
    "military_tactics_map": {
        "id": "military_tactics_map",
        "name": "Askeri Taktikler + Strateji Haritası (Item 300)",
        "category": "Tarih & Strateji",
        "rpm_tier": "Yüksek Erkek Kitle",
        "tone": "strategic, authoritative, dramatic",
        "hook_style": "Tarihin en dahi kuşatma taktiklerini kırmızı ve mavi oklarla canlandırma.",
        "split_screen_default": False,
        "bg_style": "war strategy map battlefield top down arrows military history",
        "loop_bridge": "...ve kuşatmanın kaderini değiştiren o ilk stratejik hamleye haritada dönersek...",
        "system_prompt_addition": (
            "Tarihin en ünlü askeri kuşatma veya taktik manevralarını anlat. "
            "Kırmızı/mavi ok ve strateji haritası görsel dili kullan."
        )
    },
    "celebrity_failure_stories": {
        "id": "celebrity_failure_stories",
        "name": "Ünlülerin Başarısızlık Hikayeleri (Item 301)",
        "category": "Motivasyon & Biyografi",
        "rpm_tier": "Yüksek Duygusal Bağ",
        "tone": "dramatic, inspiring, resilient",
        "hook_style": "Walt Disney'in işten kovulması, Steve Jobs'un kovulması gibi dramatik başarı öyküleri.",
        "split_screen_default": False,
        "bg_style": "black and white portrait rejection letter vintage office dramatic lighting",
        "loop_bridge": "...ve o ünlünün hayatının en karanlık anında duyduğu ilk cümle şuydu:",
        "system_prompt_addition": (
            "Ünlü bir ismin reddedilme, iflas veya kovulma anını dramatik anlat; "
            "sonrasındaki dönüşümü ilham verici bitir."
        )
    },
    "body_language_celebrity": {
        "id": "body_language_celebrity",
        "name": "Beden Dili Analizi + Ünlü Röportajları (Item 302)",
        "category": "Psikoloji & Medya",
        "rpm_tier": "Yüksek Merak",
        "tone": "analytical, revealing, forensic",
        "hook_style": "Siyasilerin veya ünlülerin yalan söylerken yaptığı 3 beden dili hareketi.",
        "split_screen_default": False,
        "bg_style": "celebrity interview press conference close up gestures news studio",
        "loop_bridge": "...ve o röportajdaki ilk şüpheli mikro jeste tekrar bakarsak...",
        "system_prompt_addition": (
            "Ünlü veya siyasi bir röportajdaki 3 beden dili ipucunu madde madde analiz et. "
            "Göz teması, el hareketi ve duruş değişimlerini vurgula."
        )
    },
    "future_2050_simulation": {
        "id": "future_2050_simulation",
        "name": "Gelecek Simülasyonu — Yıl 2050 (Item 303)",
        "category": "Gelecek & Teknoloji",
        "rpm_tier": "Yüksek Merak & Paylaşım",
        "tone": "futuristic, immersive, speculative",
        "hook_style": "2050 yılında bir gün nasıl geçecek temalı fütüristik yaşam tasviri.",
        "split_screen_default": False,
        "bg_style": "futuristic city 2050 flying car smart home neon utopia sci fi",
        "loop_bridge": "...ve 2050 sabahının başladığı o ilk an, tam olarak şöyle görünüyordu:",
        "system_prompt_addition": (
            "2050 yılında tipik bir günü dakika dakika tasvir et: uyanış, ulaşım, iş, teknoloji. "
            "Fütüristik ama inandırıcı detaylar kullan."
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
            "Mariana Çukuru ve okyanus derinliklerindeki gizemli canlıları korku ve merakla anlat. "
            "Derin deniz karanlığı ve talasofobi ambiyansını vurgula."
        )
    },
    "forgotten_historical_figures": {
        "id": "forgotten_historical_figures",
        "name": "Unutulmuş Tarihi Şahsiyetler (Item 305)",
        "category": "Tarih & Keşif",
        "rpm_tier": "Yüksek Merak",
        "tone": "revealing, epic, documentary",
        "hook_style": "Tarihin akışını değiştiren ama adı bilinmeyen gizli kahramanlar.",
        "split_screen_default": False,
        "bg_style": "ancient historical portrait archive dusty library old manuscript",
        "loop_bridge": "...ve tarihin unuttuğu o gizli kahramanın hikayesi tam olarak şurada başlıyordu:",
        "system_prompt_addition": (
            "Tarihin seyrini değiştiren ama popüler kültürde adı bilinmeyen bir şahsiyeti anlat. "
            "Arşiv belgesi ve eski portre estetiği kullan."
        )
    },
    "iq_puzzle_optical_riddle": {
        "id": "iq_puzzle_optical_riddle",
        "name": "Zeka Sorusu + Optik Bilmece (Item 306)",
        "category": "Quiz & Görsel Zeka",
        "rpm_tier": "Yüksek Yorum & Paylaşım",
        "tone": "playful, challenging, suspenseful",
        "hook_style": "Resimdeki gizlenmiş nesneyi 7 saniyede bulma challenge'ı.",
        "split_screen_default": False,
        "bg_style": "hidden object puzzle optical illusion find the difference brain teaser",
        "loop_bridge": "...ve tam da bu optik bilmecenin başladığı o ilk 7 saniyeye geri dönersek...",
        "system_prompt_addition": (
            "Optik bilmece ve zeka sorusu kurgusu yap. İzleyiciye 7 saniye süre tanı; "
            "gizlenmiş nesneyi bulmasını iste, sonra cevabı dramatik açıkla."
        )
    },
    "entrepreneur_minimal_typography": {
        "id": "entrepreneur_minimal_typography",
        "name": "E-Ticaret / Girişimcilik + Minimalist Tipografi (Item 307)",
        "category": "Girişimcilik & Finans",
        "rpm_tier": "Yüksek CPM (Tier-1)",
        "tone": "bold, authoritative, minimalist",
        "hook_style": "Siyah-beyaz ekranda yalnızca güçlü kelimelerin çarptığı girişimcilik tavsiyeleri.",
        "split_screen_default": False,
        "bg_style": "black white minimalist typography bold text motion graphic startup",
        "loop_bridge": "...ve o girişimcinin hayatını değiştiren ilk kelime tam olarak şuydu:",
        "system_prompt_addition": (
            "E-ticaret veya girişimcilik tavsiyelerini madde madde ver. "
            "Her madde tek güçlü kelime veya kısa cümle vurgusuyla; siyah-beyaz minimalist tipografi estetiği kullan."
        )
    },
    "world_records_sports_commentary": {
        "id": "world_records_sports_commentary",
        "name": "Dünya Rekorları + İnanılmaz Anlar (Item 308)",
        "category": "Spor & Rekor",
        "rpm_tier": "Yüksek Viralite",
        "tone": "excited, dramatic, sports-commentator",
        "hook_style": "Guinness rekorlarının kırılma anlarını heyecanlı maç spikeri tonuyla aktarma.",
        "split_screen_default": False,
        "bg_style": "guinness world record sports stadium crowd slow motion achievement",
        "loop_bridge": "...ve o rekorun kırıldığı o inanılmaz saniyeye tekrar dönersek...",
        "system_prompt_addition": (
            "Dünya rekoru kırılma anını canlı maç spikeri coşkusuyla anlat. "
            "Heyecan, gerilim ve final patlamasını vurgula; Guinness tarzı rekor gerçekleri kullan."
        )
    },
    "did_you_know_facts": {
        "id": "did_you_know_facts",
        "name": "Hap Bilgiler — Did You Know? (Item 309)",
        "category": "Eğitim & Merak",
        "rpm_tier": "Yüksek Paylaşım",
        "tone": "snappy, wonder-filled, punchy",
        "hook_style": "'Bunu biliyor muydunuz?' kalıbıyla peş peşe 3 akıl almaz biyoloji gerçeği.",
        "split_screen_default": False,
        "bg_style": "macro biology nature microscope colorful science fact infographic",
        "loop_bridge": "...ve bu akıl almaz gerçeklerin ilki aslında tam olarak şuydu:",
        "system_prompt_addition": (
            "Her biri 'Bunu biliyor muydunuz?' ile başlayan 3 kısa, şok edici biyoloji gerçeği ver. "
            "Hızlı tempo, hap bilgi formatı; her gerçek 10-12 saniye."
        )
    },
    "micro_street_interview": {
        "id": "micro_street_interview",
        "name": "Mikro Röportaj Kurgusu (Item 316)",
        "category": "Sosyal & Diyalog",
        "rpm_tier": "Yüksek Otantiklik",
        "tone": "casual, candid, conversational",
        "hook_style": "Sokaktaki insanlara tek derin soru sorulmuş gibi kurgulanan diyaloglar.",
        "split_screen_default": False,
        "bg_style": "street interview handheld microphone urban sidewalk candid people",
        "loop_bridge": "...ve sokakta sorduğumuz o tek derin soruya verilen ilk cevap şuydu:",
        "system_prompt_addition": (
            "Tek bir derin soru etrafında sokak röportajı kurgusu yap. "
            "Soru-cevap diyalog formatı; 2-3 farklı 'sokaktaki insan' cevabı; el mikrofonu estetiği."
        )
    },
    "seasonal_trend_reaction": {
        "id": "seasonal_trend_reaction",
        "name": "Dönemsel Trendlere Çabuk Atlama (Item 317)",
        "category": "Trend & Kültür",
        "rpm_tier": "Yüksek Anlık Trafik",
        "tone": "timely, analytical, cinematic",
        "hook_style": "Yeni vizyona giren film (Oppenheimer, Dune) üzerinden felsefe veya tarih içeriği.",
        "split_screen_default": False,
        "bg_style": "cinema premiere movie poster trending film dramatic lighting",
        "loop_bridge": "...ve o filmin vizyona girdiği hafta tartışılan asıl felsefi soru şuydu:",
        "system_prompt_addition": (
            "Gündemdeki popüler film veya trend olay üzerinden felsefe/tarih/psikoloji açısı ver. "
            "Trendi hızlı yakala; film adını kanca olarak kullan ama transformative analiz sun."
        )
    },
    "absurdist_philosophy_meme": {
        "id": "absurdist_philosophy_meme",
        "name": "Görsel Mizah + Derin Felsefe (Item 318)",
        "category": "Felsefe & Mizah",
        "rpm_tier": "Yüksek Paylaşım & Yorum",
        "tone": "absurd, witty, profound",
        "hook_style": "Komik kedi videosunun üzerine Nietzsche'nin nihilizm sözlerini oturtma.",
        "split_screen_default": False,
        "bg_style": "funny cat meme viral animal absurd comedy juxtaposition",
        "loop_bridge": "...ve o komik görüntünün altında yatan asıl felsefi gerçek tam olarak şuydu:",
        "system_prompt_addition": (
            "Komik/viral görsel mizah estetiği ile derin felsefi alıntıyı (Nietzsche, Camus, absürdizm) birleştir. "
            "Kontrast absürd ama düşündürücü; mizah üstte, felsefe altyazı/ses."
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
    "subtitle_voice_equalizer": {
        "id": "subtitle_voice_equalizer",
        "name": "Altyazı Altı Ses Frekansı Görselleştiricisi (Item 325)",
        "category": "Ses & Görsel Senkron",
        "rpm_tier": "Yüksek Tutunma",
        "tone": "rhythmic, energetic, podcast-style",
        "hook_style": "Altyazının hemen altında ritme göre zıplayan yeşil ekolayzır çubuğu.",
        "split_screen_default": False,
        "bg_style": "podcast studio microphone dark neon green waveform",
        "loop_bridge": "...ve o ritmin zirve noktasına geri döndüğümüzde ilk vuruş tam olarak şuydu:",
        "system_prompt_addition": (
            "Anlatım podcast/Storytime formatında olmalı. Her vurgulu kelimede ses frekansı zıplar gibi "
            "görselleştirme hayal et; altyazı altına yeşil ekolayzır bar meta verisi ekle."
        )
    },
    "night_mode_dark_content": {
        "id": "night_mode_dark_content",
        "name": "Gece Modu (Dark Mode) İçerikleri (Item 326)",
        "category": "Gece Yayın & Rahatlatıcı",
        "rpm_tier": "Gece 23:00–03:00 TRT Peak",
        "tone": "calm, soothing, intimate, low-light",
        "hook_style": "Gece yarısı izleyenler için karanlık temalı, rahatlatıcı sesli videolar.",
        "split_screen_default": False,
        "bg_style": "dark mode night city moonlight cozy bedroom ambient low light",
        "loop_bridge": "...ve gece yarısı sessizliğinde ilk duyduğunuz o fısıltıya geri dönüyoruz:",
        "system_prompt_addition": (
            "23:00–03:00 arası izleyenler için karanlık tema, düşük kontrast, yumuşak ses tonu kullan. "
            "Görseller gece şehri, ay ışığı, loş oda ambient içermeli."
        )
    },
    "interactive_stop_wheel_game": {
        "id": "interactive_stop_wheel_game",
        "name": "İnteraktif Durdurma Oyunları (Item 327)",
        "category": "Oyun & İnteraktif",
        "rpm_tier": "Yüksek Yorum & Tekrar İzleme",
        "tone": "playful, competitive, suspenseful",
        "hook_style": "Ekranda hızla dönen çarkı doğru yerde durdurma yarışması.",
        "split_screen_default": False,
        "bg_style": "spinning wheel game show neon countdown prize",
        "loop_bridge": "...ve çarkın durduğu o kritik an tam olarak başlangıçtaki soruydu:",
        "system_prompt_addition": (
            "Ekranda dönen şans çarkı/ rulet oyunu kurgusu kur. İzleyiciye 'doğru yerde durdur' "
            "meydan okuması ver; 3 saniye geri sayım + ding sesi hayal et."
        )
    },
    "collective_subconscious_fears": {
        "id": "collective_subconscious_fears",
        "name": "Kolektif Bilinçaltı Korkuları (Item 328)",
        "category": "Psikoloji & Korku",
        "rpm_tier": "Yüksek Viral Paylaşım",
        "tone": "unsettling, visceral, hypnotic",
        "hook_style": "Klostrofobi, talasofobi, araknofobi gibi kolektif fobileri tetikleyen görseller.",
        "split_screen_default": False,
        "bg_style": "claustrophobic narrow corridor deep ocean abyss spider shadow darkness",
        "loop_bridge": "...ve o bilinçaltı korkunun kökenine indiğimizde ilk hissettiğimiz şey tam olarak buydu:",
        "system_prompt_addition": (
            "Klostrofobi (dar alan), talasofobi (derin su), araknofobi (örümcek) gibi evrensel "
            "korkulara dokun. Görseller dar tünel, okyanus uçurumu, gölge silüet içermeli."
        )
    },
    "ancient_remedies_egypt": {
        "id": "ancient_remedies_egypt",
        "name": "Eski Medeniyetlerin Gizli İlaçları (Item 331)",
        "category": "Sağlık & Tarih",
        "rpm_tier": "Yüksek Sağlık Nişi Sinerjisi",
        "tone": "mysterious, educational, authoritative",
        "hook_style": "Antik Mısır'da kullanılan doğal şifa yöntemleri ve gizli bitkisel reçeteler.",
        "split_screen_default": False,
        "bg_style": "ancient egypt papyrus herbs hieroglyph temple healing ritual",
        "loop_bridge": "...ve o antik reçetenin ilk satırına geri döndüğümüzde şifa tam olarak burada başlıyordu:",
        "system_prompt_addition": (
            "Antik Mısır, Mezopotamya veya Çin'in unutulmuş doğal şifa yöntemlerini anlat. "
            "3 bitkisel/madde reçetesi ver; görseller papirüs, ot, tapınak içermeli."
        )
    },
    "time_machine_100years": {
        "id": "time_machine_100years",
        "name": "Zaman Makinesi Konsepti (Item 332)",
        "category": "Tarih & Görsel Dönüşüm",
        "rpm_tier": "Yüksek Merak",
        "tone": "epic, nostalgic, transformative",
        "hook_style": "Her sahnede 100 yıl geriye giderek dünyanın dönüşümünü izletme.",
        "split_screen_default": False,
        "bg_style": "time travel clock vintage sepia modern city transition timeline",
        "loop_bridge": "...ve zaman makinesinin durduğu o ilk yıla geri döndüğümüzde dünya tam olarak şöyleydi:",
        "system_prompt_addition": (
            "Her sahne 100 yıl geriye gitsin (2026→1926→1826...). Her dönemde aynı konumun "
            "görsel dönüşümünü anlat; yıl sayacı meta verisi ekle."
        )
    },
    "money_psychology_quotes": {
        "id": "money_psychology_quotes",
        "name": "Paranın Psikolojisi Alıntıları (Item 333)",
        "category": "Finans & Psikoloji",
        "rpm_tier": "Yüksek Tier-1 Uyumlu",
        "tone": "insightful, contrarian, minimalist",
        "hook_style": "Morgan Housel tarzı çarpıcı finansal gerçekler ve para psikolojisi alıntıları.",
        "split_screen_default": False,
        "bg_style": "minimalist finance dark background gold accent quote typography",
        "loop_bridge": "...ve parayla ilgili o ilk gerçeği duyduğunuzda zihniniz tam olarak şunu soracak:",
        "system_prompt_addition": (
            "Morgan Housel 'Psychology of Money' tarzında 3 çarpıcı finansal gerçek anlat. "
            "Para davranışı, risk ve sabır psikolojisine odaklan; minimalist tipografi estetiği."
        )
    },
    "viewer_choice_door_game": {
        "id": "viewer_choice_door_game",
        "name": "İzleyiciye Seçim Yaptırma (Item 335)",
        "category": "İnteraktif & Yorum Tetikleyici",
        "rpm_tier": "En Yüksek Yorum Sayısı",
        "tone": "suspenseful, participatory, dramatic",
        "hook_style": "'Kapı 1 mi, Kapı 2 mi? Seçimini yoruma yaz!' — izleyici karar formatı.",
        "split_screen_default": True,
        "bg_style": "two doors mystery red blue split screen choice dramatic lighting",
        "loop_bridge": "...ve o iki kapının ardında gizlenen gerçek tam olarak ilk soruda saklıydı:",
        "system_prompt_addition": (
            "İki zıt seçenek (Kapı 1 vs Kapı 2) sun. İzleyiciye 'Seçimini yoruma yaz' CTA ver; "
            "her kapının ardındaki sonucu dramatik anlat."
        )
    },
    "hidden_wiretap_meeting": {
        "id": "hidden_wiretap_meeting",
        "name": "Gizli Mikrofon Kaydı Estetiği (Item 336)",
        "category": "Gerilim & Sızıntı",
        "rpm_tier": "Yüksek Merak & Paylaşım",
        "tone": "covert, tense, conspiratorial, whispered",
        "hook_style": "Çok gizli bir toplantıdan sızdırılmış ses kaydı gibi fısıltılı anlatım.",
        "split_screen_default": False,
        "bg_style": "dark boardroom shadow silhouette classified document grain static",
        "loop_bridge": "...ve o gizli toplantının kaydı tam da bu ilk cümleyle başlıyordu:",
        "system_prompt_addition": (
            "Anlatım gizli mikrofon kaydı estetiğinde olmalı: fısıltılı ton, arada statik cızırtı, "
            "'Bu kayıt resmi olarak yok sayıldı' gibi sızıntı hissi. Görseller karanlık toplantı odası, "
            "gölge silüet, gizli belge içermeli."
        )
    },
    "photo_restoration_story": {
        "id": "photo_restoration_story",
        "name": "Fotoğraf Restorasyonu Hikayesi (Item 337)",
        "category": "Tarih & AI Görsel",
        "rpm_tier": "Yüksek Duygusal Tutunma",
        "tone": "nostalgic, emotional, transformative, reverent",
        "hook_style": "100 yıllık yıpranmış bir fotoğrafın AI ile renklendirilip canlandırılma hikayesi.",
        "split_screen_default": False,
        "bg_style": "vintage sepia damaged photograph colorization before after restoration",
        "loop_bridge": "...ve o eski fotoğrafın sol alt köşesindeki o küçük detaya geri döndüğümüzde hikaye başlıyor:",
        "system_prompt_addition": (
            "Yıpranmış/antik bir fotoğrafın yapay zeka ile renklendirilip canlandırılma hikayesini anlat. "
            "Before/after dönüşüm hissi; her sahne fotoğrafın farklı bölgesinin netleşmesi gibi kurgulanmalı."
        )
    },
    "country_popular_things_map": {
        "id": "country_popular_things_map",
        "name": "Ülkelerin En Popüler Şeyleri (Item 339)",
        "category": "Coğrafya & Kültür",
        "rpm_tier": "Küresel Keşif",
        "tone": "curious, upbeat, educational, travelogue",
        "hook_style": "Dünya haritası üzerinde her ülkenin en sevilen yemeği veya sporu.",
        "split_screen_default": False,
        "bg_style": "world map animated country highlight food sport culture infographic",
        "loop_bridge": "...ve haritada ilk durduğumuz o ülkeye geri dönersek en popüler şey tam buydu:",
        "system_prompt_addition": (
            "3 farklı ülkenin en popüler yemeğini veya sporunu dünya haritası üzerinde sırayla tanıt. "
            "Her ülke için 1 ikonik gerçek + görsel arama terimi (ör. 'japan sushi street food', 'brazil football stadium')."
        )
    },
    "corporate_dirty_secrets": {
        "id": "corporate_dirty_secrets",
        "name": "Büyük Şirketlerin Kirli Sırları (Item 340)",
        "category": "İş & Skandal",
        "rpm_tier": "Yüksek Tıklama & Yorum",
        "tone": "investigative, shocking, exposé, cynical",
        "hook_style": "Fast-food veya teknoloji devlerinin gizli pazarlama oyunları ve kirli sırları.",
        "split_screen_default": False,
        "bg_style": "corporate logo silhouette whistleblower document leaked memo dark office",
        "loop_bridge": "...ve o şirketin halka açıklamak istemediği ilk sırra geri dönersek:",
        "system_prompt_addition": (
            "Büyük bir fast-food, teknoloji veya perakende devinin 3 gizli pazarlama taktiğini veya "
            "skandalını anlat. İddialı ama doğrulanabilir ton; 'içeriden sızan' belge estetiği."
        )
    },
    "binaural_8d_audio_illusions": {
        "id": "binaural_8d_audio_illusions",
        "name": "Sesli İllüzyonlar (Item 341)",
        "category": "Ses & ASMR",
        "rpm_tier": "Yüksek Kulaklık İzleme",
        "tone": "hypnotic, immersive, spatial, trippy",
        "hook_style": "Kulaklıkla dinlendiğinde sesin kafanın arkasından geliyormuş hissi veren 8D kurgu.",
        "split_screen_default": False,
        "bg_style": "abstract sound wave headphones dark neon spatial audio visualization",
        "loop_bridge": "...ve o sesin tam kulağınızın arkasından geldiği o ilk an tam olarak şuydu:",
        "system_prompt_addition": (
            "8D/binaural ses illüzyonu kurgusu: ses sağdan sola, önden arkaya hareket ediyormuş gibi anlat. "
            "Kulaklıkla dinleme CTA ver; görseller soyut dalga formu, kulaklık, karanlık neon."
        )
    },
    "childhood_nostalgia_90s_2000s": {
        "id": "childhood_nostalgia_90s_2000s",
        "name": "Çocukluk Anıları Nostaljisi (Item 343)",
        "category": "Nostalji & Kültür",
        "rpm_tier": "Yüksek Paylaşım & Yorum",
        "tone": "warm, bittersweet, nostalgic, playful",
        "hook_style": "90'lar ve 2000'lerin unutulmaz televizyon, oyun ve atari anlarını hatırlatma.",
        "split_screen_default": False,
        "bg_style": "90s 2000s retro tv game console vhs arcade nostalgia childhood",
        "loop_bridge": "...ve çocukluğunuzda ilk izlediğiniz o an tam da burada başlıyordu:",
        "system_prompt_addition": (
            "90'lar ve 2000'ler nostaljisi: 3 unutulmaz TV, oyun veya teknoloji anısını sıcak ve duygusal anlat. "
            "'Bunu hatırlayan var mı?' yorum tetikleyicisi ekle; görseller VHS, Game Boy, CRT TV içermeli."
        )
    },
    "inspirational_athlete_comeback": {
        "id": "inspirational_athlete_comeback",
        "name": "İlham Verici Sporcu Hikayeleri (Item 344)",
        "category": "Spor & Motivasyon",
        "rpm_tier": "Yüksek Duygusal Tutunma",
        "tone": "epic, triumphant, emotional, cinematic",
        "hook_style": "Sakatlıktan dönüp şampiyon olan sporcuların 40 saniyelik epik öyküsü.",
        "split_screen_default": False,
        "bg_style": "sports stadium slow motion athlete injury comeback victory cinematic",
        "loop_bridge": "...ve o sporcunun en karanlık gününe geri döndüğümüzde hikaye tam burada başlıyordu:",
        "system_prompt_addition": (
            "Sakatlık veya felaketten dönüp şampiyon olan bir sporcunun 40 saniyelik epik öyküsünü anlat. "
            "3 faz: düşüş → mücadele → zafer; slow-motion stadyum görselleri hayal et."
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


def build_hybrid_prompt_block(hybrid_id: str, lang: str = "tr") -> str:
    """System prompt injection for hybrid synergy formats (Items 276-345)."""
    hybrid = get_hybrid_niche(hybrid_id)
    addition = hybrid.get("system_prompt_addition") or ""
    hook = hybrid.get("hook_style") or ""
    tone = hybrid.get("tone") or ""
    if lang == "en":
        return (
            f"\n\nHYBRID NICHE FORMAT ({hybrid.get('name', hybrid_id)}):\n"
            f"- Tone: {tone}\n- Hook style: {hook}\n- Visual bg_style: {hybrid.get('bg_style', '')}\n"
            f"{addition}"
        )
    return (
        f"\n\nHİBRİT NİŞ FORMAT ({hybrid.get('name', hybrid_id)}):\n"
        f"- Ton: {tone}\n- Kanca stili: {hook}\n- Görsel bg_style: {hybrid.get('bg_style', '')}\n"
        f"{addition}"
    )


# Render overlay specs — maps hybrid id → visual overlay applied in video_composer (B5 Items 276–345)
HYBRID_RENDER_OVERLAY_MAP: Dict[str, Dict[str, Any]] = {
    "history_chat": {"ui_type": "imessage", "header": "Tarih Grubu", "body": "Gizli mesaj...", "item": 277},
    "whatsapp_horror_voice": {"ui_type": "imessage", "header": "Bilinmeyen", "body": "Ses kaydı...", "item": 286},
    "would_you_rather_duel": {"ui_type": "split_choice", "item": 280},
    "crypto_comic_book": {"ui_type": "tweet_card", "header": "Kripto Haber", "body": "Piyasa...", "item": 283},
    "conspiracy_fbi_newspaper": {"ui_type": "search_bar", "header": "GİZLİ DOSYA", "body": "Sansürlendi", "item": 292},
    "optical_illusion_focus": {"overlay": "spiral", "item": 298},
    "price_timeline_tunnel": {"overlay": "time_tunnel", "item": 299},
    "dark_psychology_parkour": {"overlay": "split_screen", "item": 278},
    "reddit_asmr": {"overlay": "split_screen", "item": 281},
    "stoic_cyberpunk": {"overlay": "neon_frame", "item": 276},
    "cosmic_epic_hans_zimmer": {"overlay": "epic_vignette", "item": 282},
    "spiritual_rain_nature": {"overlay": "soft_vignette", "item": 285},
    "weird_laws_world_map": {"ui_type": "search_bar", "header": "Yasa Ara", "body": "Garip kanun...", "item": 290},
    "mystery_earth_zoom": {"ui_type": "ios_notification", "header": "Koordinat", "body": "Gizemli konum", "item": 279},
    "country_guess_countdown": {"ui_type": "split_choice", "item": 284},
    "movie_idiom_english": {"ui_type": "subtitle_bar", "header": "Dizi Altyazı", "body": "Kelime...", "item": 288},
    "hidden_wiretap_meeting": {"ui_type": "ios_notification", "header": "Kayıt", "body": "● REC", "item": 336},
    "microphone_hidden": {"ui_type": "ios_notification", "header": "Kayıt", "body": "● REC", "item": 336},
    "interactive_stop_wheel_game": {"overlay": "countdown_wheel", "item": 327},
    "lifehack_affiliate_3items": {"ui_type": "ios_notification", "header": "Life Hack", "body": "3 ürün...", "item": 287},
    "subtitle_voice_equalizer": {"overlay": "eq_bar", "item": 325},
    "old_money_luxury_mindset": {"overlay": "hybrid_frame", "item": 291},
    "mythology_ai_epic": {"overlay": "hybrid_frame", "item": 289},
    "night_mode_dark_content": {"overlay": "neon_frame", "item": 326},
}


def _extract_hybrid_item_number(hybrid: Dict[str, Any]) -> Optional[int]:
    import re
    name = str(hybrid.get("name") or "")
    match = re.search(r"Item\s+(\d+)", name, re.I)
    if match:
        return int(match.group(1))
    return None


def get_hybrid_render_overlay_spec(hybrid_id: str) -> Dict[str, Any]:
    """Return render overlay spec for hybrid niche (B5 visual wire)."""
    if not hybrid_id:
        return {}
    spec = dict(HYBRID_RENDER_OVERLAY_MAP.get(hybrid_id) or {})
    hybrid = get_hybrid_niche(hybrid_id)
    if not spec:
        item_num = _extract_hybrid_item_number(hybrid)
        spec = {
            "overlay": "hybrid_frame",
            "item": item_num or hybrid_id,
            "bg_style": hybrid.get("bg_style", ""),
            "label": hybrid.get("name", hybrid_id).split("(")[0].strip(),
        }
    spec["hybrid_id"] = hybrid_id
    if not spec.get("bg_style"):
        spec["bg_style"] = hybrid.get("bg_style", "")
    if not spec.get("label"):
        spec["label"] = hybrid.get("name", hybrid_id).split("(")[0].strip()
    return spec


def enrich_plan_with_hybrid(plan: Dict[str, Any], title: str, niche_id: str = "") -> Dict[str, Any]:
    """Attach hybrid metadata and bg_style hints when topic intelligence detects a synergy."""
    try:
        from director.visual_intent import resolve_topic_intelligence
    except ImportError:
        return plan
    intel = resolve_topic_intelligence(title or plan.get("title", ""), niche_id or "1_news_flash")
    hybrid_id = intel.get("hybrid_niche")
    if not hybrid_id:
        return plan
    hybrid = get_hybrid_niche(hybrid_id)
    plan["hybrid_niche"] = hybrid_id
    plan["hybrid_split_screen"] = hybrid.get("split_screen_default", False)
    plan["hybrid_render_overlay"] = get_hybrid_render_overlay_spec(hybrid_id)
    if hybrid.get("loop_bridge") and not plan.get("loop_text"):
        plan["loop_text"] = hybrid["loop_bridge"]
    bg = hybrid.get("bg_style")
    scenes = plan.get("scenes") or []
    if bg and scenes:
        for s in scenes[:3]:
            queries = list(s.get("search_queries") or [])
            if bg not in " ".join(queries):
                queries.insert(0, bg.split()[0] if bg else "cinematic")
                s["search_queries"] = queries[:3]
    overlay_spec = plan.get("hybrid_render_overlay") or {}
    ui_type = overlay_spec.get("ui_type")
    if ui_type and scenes:
        scenes[0]["hybrid_ui_overlay"] = ui_type
    if overlay_spec.get("overlay") == "spiral":
        plan["retention_spiral"] = True
    if overlay_spec.get("overlay") == "time_tunnel":
        plan["retention_time_tunnel"] = True
    if overlay_spec.get("overlay") == "eq_bar":
        plan["hybrid_eq_bar"] = True
    if overlay_spec.get("overlay") == "countdown_wheel":
        plan["hybrid_countdown_wheel"] = True
    return plan


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


def generate_perfect_seamless_loop_bridge(
    opening_hook: str,
    video_index: int = 0,
    lang: str = "tr",
) -> Dict[str, Any]:
    """
    Item 345: Kusursuz Bitiş ve Başlangıç (Perfect Seamless Loop Bridge).
    İzleyicinin videonun nerede bittiğini fark etmeden 2 kez izlemesi için
    son cümleyi ilk cümleye kusursuz bağlar (%200 retention hedefi).
    """
    try:
        from viral_retention_engine import ViralRetentionEngine
        bridge = ViralRetentionEngine.pick_loop_bridge_for_video(video_index)
        formula = ViralRetentionEngine.get_loop_formula()
    except ImportError:
        bridge = "...ve tam da bu yüzden başa döndüğünüzde ilk duyduğunuz cümle:"
        formula = {"ending": "çünkü bu sırrı ilk duyduğunuzda...", "opening": opening_hook}

    opening = (opening_hook or formula.get("opening", "")).strip()
    ending = formula.get("ending", bridge).strip()
    if lang == "en":
        return {
            "opening_line": opening,
            "closing_line": f"{ending} {opening}",
            "loop_bridge": bridge,
            "retention_target_pct": 200,
            "instruction": (
                "Last spoken line must flow seamlessly into the first frame/word so the viewer "
                "replays without noticing the cut. Match final visual tone to opening frame."
            ),
        }
    return {
        "opening_line": opening,
        "closing_line": f"{ending} {opening}",
        "loop_bridge": bridge,
        "retention_target_pct": 200,
        "instruction": (
            "Son konuşulan cümle ilk kare/kelimeye kusursuz bağlanmalı; izleyici kesiti fark etmeden "
            "tekrar izlemeli. Son görsel tonu açılış karesiyle eşle."
        ),
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
