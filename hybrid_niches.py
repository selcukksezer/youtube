"""
Hybrid Niches & Synergy Library
Implements Items 276 - 345 of the 500-Item YouTube Shorts Automation Roadmap.
Blends top-performing high-RPM niches with visual retention formats,
niche collision formulas, episodic hooks, and Tier-1 market adapters.
"""

from typing import Dict, List, Any, Optional

from effects.hybrid_ui_cards import (
    EXTENDED_HYBRID_NICHES,
    HYBRID_RENDER_OVERLAY_MAP,
    _extract_hybrid_item_number,
    enrich_plan_with_hybrid,
    get_hybrid_render_overlay_spec,
)


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
    **EXTENDED_HYBRID_NICHES,
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


def list_all_hybrid_niches() -> List[Dict[str, Any]]:
    """Lists all hybrid synergy niches with metadata."""
    return list(HYBRID_NICHES.values())


def collide_two_niches(niche_a_id: str, niche_b_id: str) -> Dict[str, Any]:
    """Item 320: İki Farklı Nişin Çarpışması (Niche Collision Engine)."""
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
        "loop_bridge": "...ve işte bu iki dünyanın çarpıştığı o ilk ana geri dönersek...",
        "system_prompt": (
            f"Bu senaryoda iki farklı dünyayı melezle: {niche_a['name']} VE {niche_b['name']}. "
            f"Her iki konseptin görsel ve tematik unsurlarını sahne sahne harmanla."
        )
    }


def generate_episodic_series_hook(series_title: str, episode_num: int = 1, total_parts: int = 10, lang: str = "tr") -> Dict[str, str]:
    """Item 314: Seri Formatı (Bölüm 1 / Part 1 Episodic Hook Generator)."""
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
    """Item 329: İronik / Ters Tavsiye Kancası (Ironic Reverse Psychology Bait)."""
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
    """Item 330: Bilimsel Hipotez Simülasyonu."""
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
    """Item 345 & Plan 7.2: Kusursuz Bitiş ve Başlangıç (Perfect Seamless Loop Bridge)."""
    from viral_retention_engine import ViralRetentionEngine
    res = ViralRetentionEngine.synthesize_seamless_loop(
        opening_hook=opening_hook,
        final_narration="",
        video_index=video_index,
        lang=lang,
    )
    instruction = (
        "Last spoken line must flow seamlessly into the first frame/word so the viewer "
        "replays without noticing the cut. Match final visual tone to opening frame."
        if lang == "en"
        else "Son konuşulan cümle ilk kare/kelimeye kusursuz bağlanmalı; izleyici kesiti fark etmeden "
        "tekrar izlemeli. Son görsel tonu açılış karesiyle eşle."
    )
    return {
        "opening_line": res["opening_hook"],
        "closing_line": res["seamless_closing"],
        "loop_bridge": res["ending_bridge"],
        "preview_loop": res["preview_loop"],
        "retention_target_pct": 200,
        "instruction": instruction,
    }


def adapt_to_tier1_market(turkish_concept: str, target_country: str = "US") -> Dict[str, Any]:
    """Item 321: Tier-1 Ülke Adaptasyonu (Global High-RPM English Conversion)."""
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
