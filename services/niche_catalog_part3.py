"""
Static Niche Catalog Data — Part 3 (Scene Format Templates and Outro CTAs).
Extracted from services/niche_catalog_data.py for modular maintainability.
"""
from typing import Dict

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
    "religious": {
        "tr": (
            "HADİS-İ ŞERİF & AYET MEALİ YAPISI (zorunlu):\n"
            "- Sahne 1: Hadis veya ayet kancası — Hz. Peygamber'in kutlu sözü veya ayet bağlamı, saygılı ve huzur veren ton.\n"
            "- Orta: Hadis/ayetin derin manası, günlük hayata dokunan hikmeti ve ahlaki öğüdü. İsimleri saygıyla an.\n"
            "- Son: Amin / dua çağrısı ve izleyiciyi hayra davet eden döngü.\n"
            "- EKRAN İKİ DİLLİ TASARIM: Her sahnede üstte 'arabic_text' (orijinal tashkeelli Arapça metin), ortada Türkçe meal ve altta 'source_citation' (örn: Buhari, Müslim veya Sure adı/no) yer alır.\n"
            "- SESLENDİRME: KESİNLİKLE SADECE Türkçe metni okur ('narration'). Asla Arapça harf/kelime okunmaz.\n"
            "GÖRSEL: Kabe-i Muazzama / Mekke şafak vakti (kaaba mecca sanctuary aerial), cami kubbesi altın şafak, açık Kur'an sayfası, dua eden eller, altın tezhip hat sanatı.\n"
            "YASAK: heykel, put, Marcus Aurelius, Roma büstü, colosseum, stoacı mermer, alkol, peygamber yüzü, kumaş, ipek, saten."
        ),
        "en": (
            "HADITH & QURANIC VERSE STRUCTURE (mandatory):\n"
            "- Scene 1: Respectful hook of the Hadith or Quranic verse.\n"
            "- Middle: Spiritual wisdom, moral guidance, and practical daily impact.\n"
            "- Last: Amin / comment invitation + seamless loop.\n"
            "- BILINGUAL ON-SCREEN: 'arabic_text' at top with calligraphy tashkeel, Turkish/English meaning in center, and 'source_citation' at bottom.\n"
            "- VOICEOVER: MUST ONLY speak the translated narration text, never attempting Arabic recitation.\n"
            "VISUALS: Kaaba Mecca aerial dawn, mosque dome sunrise, Quran pages, prayer hands, calligraphy art.\n"
            "FORBIDDEN: statues, idols, Marcus Aurelius, Roman busts, colosseum, stoic marble, alcohol, faces of prophets, fabric ripples, silk."
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
    "crypto": {
        "tr": (
            "KRİPTO / PİYASA ANALİZ YAPISI:\n"
            "- Sahne 1: fiyat/seviye kancası (Bitcoin, altın, endeks — konuya özel).\n"
            "- Orta sahneler: destek/direnç, hacim, makro, risk.\n"
            "- Son sahne: long/short sorusu + döngü.\n"
            "YASAK görseller: horror, skull, ghost, lightning-strike şok. Bu bir finans videosu, korku klibi değil.\n"
            "YASAK format: burç yorumu, itiraf, chat balonu."
        ),
        "en": (
            "CRYPTO / MARKET STRUCTURE:\n"
            "- Scene 1: price/level hook.\n"
            "- Middle: support, volume, macro, risk.\n"
            "- Last: long/short question + loop.\n"
            "FORBIDDEN visuals: horror, skull, ghost, shock lightning. This is finance, not horror."
        ),
    },
    "mystery": {
        "tr": (
            "GİZEM / PARANORMAL YAPISI:\n"
            "- Sahne 1: ürpertici açıklanamayan olay kancası.\n"
            "- Orta: ipucu, tanık, resmi açıklama vs boşluk.\n"
            "- Son: izleyici teorisi sorusu. Şok görsel (Item 273) bu nişte serbest."
        ),
        "en": (
            "MYSTERY / PARANORMAL STRUCTURE:\n"
            "- Scene 1: unexplained chilling hook.\n"
            "- Middle: clues vs official silence.\n"
            "- Last: audience theory. Shock visuals (Item 273) allowed."
        ),
    },
    "dark": {
        "tr": (
            "KARANLIK PSİKOLOJİ YAPISI:\n"
            "- Sahne 1: beden dili / manipülasyon uyarısı.\n"
            "- Orta: 3 işaret, gizli niyet, savunma.\n"
            "- Son: 'bunu yapan birine güvenir misin?' Şok görsel bu nişte serbest; çocuk/cartoon YASAK."
        ),
        "en": (
            "DARK PSYCHOLOGY STRUCTURE:\n"
            "- Scene 1: body-language warning hook.\n"
            "- Middle: three tells, hidden intent, defense.\n"
            "- Last: trust question. Shock visuals allowed; kids/cartoon forbidden."
        ),
    },
    "kids": {
        "tr": (
            "ÇOCUK ANIMASYON YAPISI (Made for Kids — zorunlu):\n"
            "- Sahne 1: yumuşak, neşeli kanca (hayvan / alfabe / paylaşım).\n"
            "- Orta sahneler: tek net ahlak veya öğrenme adımı; parlak pastel çizgi film.\n"
            "- Son: nazik tekrar + 'birlikte öğrendik' kapanışı (yorum tuzağı YOK).\n"
            "YASAK: gerçek çocuk yüzü, korku, şiddet, jump scare, karanlık psikoloji, cinsel ima, silah.\n"
            "Hedef süre 45–60 sn; AI clip'ler birleştirilebilir."
        ),
        "en": (
            "KIDS ANIMATION STRUCTURE (Made for Kids — mandatory):\n"
            "- Scene 1: soft cheerful hook (animal / alphabet / sharing).\n"
            "- Middle: one clear moral or learning step; bright pastel cartoon.\n"
            "- End: gentle reprise; no comment-bait CTA.\n"
            "FORBIDDEN: real child faces, horror, violence, jump scares, dark psych, sexualization, weapons.\n"
            "Target 45–60s; AI clips may be stitched."
        ),
    },
    "astrology": {
        "tr": (
            "ASTROLOJİ / BURÇ YAPISI:\n"
            "- Sahne 1: bu hafta şanslı/kritik burç kancası.\n"
            "- Orta: aşk, para, kariyer sıralaması.\n"
            "- Son: 'burcunu yoruma yaz'. YASAK: borsa grafiği, horror skull."
        ),
        "en": (
            "ASTROLOGY / ZODIAC STRUCTURE:\n"
            "- Scene 1: lucky/critical sign hook.\n"
            "- Middle: love, money, career ranking.\n"
            "- Last: comment your sign. FORBIDDEN: trading charts, horror skull."
        ),
    },
    "quiz": {
        "tr": (
            "QUIZ / LİSTE YAPISI:\n"
            "- Sahne 1: sayı+iddia kancası (5 gerçek / tercih / mit).\n"
            "- Orta: maddeler, her sahne ayrı olgu.\n"
            "- Son: skor veya 'hangisi şaşırttı?' YASAK: kripto mum grafiği, horror."
        ),
        "en": (
            "QUIZ / LIST STRUCTURE:\n"
            "- Scene 1: numbered claim hook.\n"
            "- Middle: one fact per scene.\n"
            "- Last: score / which surprised you? FORBIDDEN: crypto candles, horror."
        ),
    },
    "product": {
        "tr": (
            "ÜRÜN / HACK YAPISI:\n"
            "- Sahne 1: problem+çözüm kancası.\n"
            "- Orta: nasıl çalışır, kim kullanır, dikkat.\n"
            "- Son: kaydet/yorum. YASAK: horror, skull, unrelated finance charts."
        ),
        "en": (
            "PRODUCT / HACK STRUCTURE:\n"
            "- Scene 1: problem+fix hook.\n"
            "- Middle: how it works, who it's for.\n"
            "- Last: save/comment. FORBIDDEN: horror, unrelated charts."
        ),
    },
    "tech": {
        "tr": (
            "YAPAY ZEKA & TEKNOLOJİ REHBERİ YAPISI:\n"
            "- Sahne 1: Hayatı veya işi kökten değiştiren teknoloji / yapay zeka kancası.\n"
            "- Orta sahneler: 2-3 kilit araç/yöntem; her araç için somut fayda, ne işe yaradığı ve pratik kullanım.\n"
            "- Son sahne: 'Siz en çok hangisini kullanıyorsunuz?' sorusu + döngü.\n"
            "GÖRSEL: modern laptop, kodlama, yapay zeka grafik arayüzü, sunucu odası, fütüristik UI.\n"
            "YASAK görseller: mutfak, limon, salatalık, yemek tavası, burç yorumu, korku."
        ),
        "en": (
            "AI & TECH GUIDE STRUCTURE:\n"
            "- Scene 1: Game-changing AI / technology breakthrough hook.\n"
            "- Middle scenes: 2-3 key tools or workflows; concrete real-world benefits and use cases.\n"
            "- Last scene: 'Which tool would you use most?' question + seamless loop.\n"
            "VISUALS: modern laptop, code editing, AI interface, glowing screens, data center.\n"
            "FORBIDDEN visuals: kitchen, lemons, cucumbers, cooking pots, astrology, horror."
        ),
    },
    "entertainment": {
        "tr": (
            "EĞLENCE / BELGESEL YAPISI:\n"
            "- Sahne 1: meraklı kanca (hayvan, film, ünlü, oyun).\n"
            "- Orta: 3 çarpıcı detay, konu nişine kilitli görsel.\n"
            "- Son: yorum sorusu. YASAK: Bitcoin grafiği, horror (gizem nişi değilse)."
        ),
        "en": (
            "ENTERTAINMENT / DOCU STRUCTURE:\n"
            "- Scene 1: curiosity hook.\n"
            "- Middle: three on-niche details.\n"
            "- Last: comment ask. FORBIDDEN: Bitcoin charts, horror unless mystery family."
        ),
    },
    "fitness": {
        "tr": (
            "FİTNESS & SAĞLIK REHBERİ YAPISI:\n"
            "- Sahne 1: Yaygın bir fitness hatasını yıkan veya hızlı sonuç vadeden kanca.\n"
            "- Orta sahneler: 2-3 bilimsel egzersiz/beslenme kuralı; somut kas/yağ yakım mantığı.\n"
            "- Son sahne: 'Siz bu kuralı uyguluyor musunuz?' sorusu + döngü.\n"
            "GÖRSEL: spor salonu, ağırlık çalışan atlet, açık hava koşu, sağlıklı beslenme, kas biyomekaniği.\n"
            "YASAK: mutfak aletleri, poşet mühürleyici, fast food, korku, kripto."
        ),
        "en": (
            "FITNESS & NUTRITION GUIDE STRUCTURE:\n"
            "- Scene 1: Myth-busting or high-impact fitness/fat-loss hook.\n"
            "- Middle scenes: 2-3 science-backed training or nutrition rules with clear mechanisms.\n"
            "- Last scene: 'Do you practice this rule?' debate question + seamless loop.\n"
            "VISUALS: gym barbell training, sprinting athlete, healthy meal prep, muscle biomechanics.\n"
            "FORBIDDEN: kitchen gadgets, fast food, horror, crypto."
        ),
    },
    "automotive": {
        "tr": (
            "SÜPER ARABA & OTOMOBİL YAPISI:\n"
            "- Sahne 1: 0-100 hızlanması, motor gücü veya agresif tasarım kancası.\n"
            "- Orta sahneler: 2-3 canavar otomobil detayı; beygir gücü, aerodinamik, pist performansı.\n"
            "- Son sahne: 'Hangisini garajınızda görmek isterdiniz?' sorusu + döngü.\n"
            "GÖRSEL: yarış pistinde süper araba, egzoz alevi, gece otoban çekimi, kokpit kadranı.\n"
            "YASAK: mutfak, limon, salatalık, poşet mühürleyici, ev temizliği, korku."
        ),
        "en": (
            "SUPERCAR & AUTOMOTIVE STRUCTURE:\n"
            "- Scene 1: High-octane acceleration, horsepower, or aggressive design hook.\n"
            "- Middle scenes: 2-3 hypercar performance specs, aerodynamics, track records.\n"
            "- Last scene: 'Which one belongs in your dream garage?' question + seamless loop.\n"
            "VISUALS: track supercar rolling shot, exhaust flame, highway night cruise, cockpit tachometer.\n"
            "FORBIDDEN: kitchen, lemons, cucumbers, pantry gadgets, cleaning tools, horror."
        ),
    },
    "legal": {
        "tr": (
            "HUKUKİ HAKLAR & TÜKETİCİ REHBERİ YAPISI:\n"
            "- Sahne 1: Günlük hayatta vatandaşın haklarını koruyan şok edici yasal kanca.\n"
            "- Orta sahneler: 2-3 somut kanun maddesi / tüketici hakkı; poliste, mağazada veya iş yerinde pratik çözüm.\n"
            "- Son sahne: 'Bu hakkınızı daha önce kullandınız mı?' sorusu + döngü.\n"
            "GÖRSEL: adalet terazisi, tokmak, sözleşme imzalayan avukat, resmi belge, iş merkezi.\n"
            "YASAK: mutfak aletleri, poşet mühürleyici, limon, salatalık, korku, kripto."
        ),
        "en": (
            "LEGAL RIGHTS & CONSUMER HACKS STRUCTURE:\n"
            "- Scene 1: Shocking everyday legal right / consumer protection hook.\n"
            "- Middle scenes: 2-3 actionable rights, consumer laws, practical protection steps.\n"
            "- Last scene: 'Have you ever used this right?' question + seamless loop.\n"
            "VISUALS: scales of justice, gavel, lawyer signing contract, official legal documents.\n"
            "FORBIDDEN: kitchen gadgets, lemons, cucumbers, pantry tools, horror, crypto."
        ),
    },
    "general": {
        "tr": (
            "GENEL SHORTS YAPISI:\n"
            "- 6 tam konuşma sahnesi, kanca → kanıt → sonuç → soru; toplam narration en fazla 110 kelime.\n"
            "Konu hangi nişse o görsel bankayı kullan; başka nişin şablonunu kopyalama."
        ),
        "en": (
            "GENERAL SHORTS STRUCTURE:\n"
            "- Six complete spoken scenes, hook → proof → close → question; total narration at most 110 words.\n"
            "Stay inside this niche's visual bank; do not clone another niche's template."
        ),
    },
}


NICHE_OUTRO_CTA: Dict[str, Dict[str, str]] = {
    "1_news_flash": {
        "tr": "Son sahne: izleyiciye bu gelişme hakkında ne düşündüğünü soracak bir tartışma sorusuyla bitir. Örnek ton: 'Bu haber sizi şaşırttı mı? Bu gelişmenin en önemli boyutunu yorumlarda paylaşın.' Mekanik 'abone ol' kalıbı YASAK.",
        "en": "Final scene: close with a debate question about this news story. Example tone: 'Does this story surprise you? Drop your biggest takeaway in the comments.' No mechanical subscribe calls.",
    },
    "2_reddit_confessions": {
        "tr": "Son sahne: 'Siz olsaydınız ne yapardınız?' veya 'Bu durumda haklı olan kim?' tarzında izleyicinin kendi deneyimini paylaşmasını davet eden organik bir soru sor. Konunun duygusal temasıyla örtüşsün.",
        "en": "Final scene: invite the viewer with a relatable question like 'What would you have done?' or 'Who do you think was in the right?' Match the emotional theme of the story.",
    },
    "3_split_gameplay": {
        "tr": "Son sahne: hızlı tempoya uygun kısa ve çarpıcı bir kapanış sorusu: 'Sen olsan ne yapardın?' veya 'Yorumlara cevabını yaz!' gibi oyun/aksiyon ruhuna yakın bir CTA.",
        "en": "Final scene: fast, punchy closing question matching the action pace: 'What would you do?' or 'Drop your answer in the comments!' Keep it gameplay-energy.",
    },
    "4_would_you_rather": {
        "tr": "Son sahne: 'A mı B mi — sen hangisini seçtin? Yorumlara yaz!' formatında net bir oylama/yorum çağrısı yap. Seçenekler videonun konusuyla örtüşsün.",
        "en": "Final scene: clear voting/comment call — 'A or B — which did you choose? Tell me in the comments!' Options must match the video topic.",
    },
    "5_guess_flag_country": {
        "tr": "Son sahne: 'Kaçıncı ipucunda bildin? Kaçını doğru yaptın? Yorumlara yaz!' tarzında izleyicinin skoru paylaşmasını teşvik et.",
        "en": "Final scene: 'How many did you get right? Drop your score in the comments!' Encourage viewers to share their quiz results.",
    },
    "6_stoic_philosophy": {
        "tr": "Son sahne: stoacı prensip üzerine derin bir kapanış cümlesi yaz ve izleyiciye 'Bugün hayatına bu ilkeyi nasıl uygulayacaksın?' tarzında içgörü uyandıran bir soru sor. 'Abone ol' YASAK — kaydet teşviki organik olsun.",
        "en": "Final scene: close with a deep stoic principle and ask 'How will you apply this today?' or 'Which stoic idea resonates most with you?' No subscribe call — inspire introspection.",
    },
    "7_dark_psychology": {
        "tr": "Son sahne: izleyiciye 'Hayatınızda bu manipülasyon taktiğiyle karşılaştınız mı?' veya 'Beden dilindeki hangi işareti siz de fark ettiniz?' gibi kişisel deneyimi açığa çıkaran bir soru sor. Gizemli ve analitik ton korusun.",
        "en": "Final scene: ask 'Have you ever experienced this psychological tactic?' or 'Which body language signal have you noticed?' Keep the mysterious analytical tone throughout.",
    },
    "8_crypto_market": {
        "tr": "Son sahne: 'Bu seviyede pozisyon alır mıydın? Yorumlara hedef fiyatını yaz!' veya 'Bitcoin şimdi al mı, sat mı? Düşünceni paylaş.' tarzında piyasa tartışması başlat.",
        "en": "Final scene: spark market debate — 'Would you buy at this level? Drop your price target in the comments!' or 'Buy or sell right now? Share your trade plan.'",
    },
    "9_five_facts": {
        "tr": "Son sahne: 'Bu bilgilerden hangisi seni en çok şaşırttı? Yorumlara yaz!' tarzında izleyiciyi en çarpıcı bulduğunu seçmeye davet et.",
        "en": "Final scene: 'Which of these facts surprised you most? Tell me in the comments!' Invite viewers to pick their most mind-blowing moment.",
    },
    "10_religious_quotes": {
        "tr": "Son sahne: 'Bu hadisi/ayeti bilen kalbe amin yazsın.' veya 'Bu güzel söz size de dokundu mu? Yorumlarda paylaşın.' tarzında manevi bir yorum kapanışı yap. Mekanik takip çağrısı YASAK.",
        "en": "Final scene: spiritual closing — 'Type Amin in the comments if this touched your heart.' or 'Which verse speaks to you most?' No mechanical subscribe call.",
    },
    "11_language_learning": {
        "tr": "Son sahne: 'Bu kalıplardan hangisini ilk kez duydun? Yorumlara yaz!' veya öğrenilen kalıplardan birini cümlede kullanan bir yorum yaz.",
        "en": "Final scene: 'Which phrase was new to you? Write a sentence using it in the comments!' Encourage active language practice.",
    },
    "12_amazon_affiliate": {
        "tr": "Son sahne: 'Bu ürünlerden hangisini almak isterdin? Yorumlara yaz!' veya 'Ürün linkini biyografiye bıraktım — hangisini beğendin?' tarzında alım kararını hızlandır.",
        "en": "Final scene: 'Which product would you grab first? Tell me in the comments!' or 'Link in bio — which one caught your eye?' Accelerate the purchase decision.",
    },
    "13_mystery_paranormal": {
        "tr": "Son sahne: 'Siz bu olayı nasıl açıklıyorsunuz? Yorumlara yazın!' veya 'Buna inanıyor musunuz yoksa inanmıyor musunuz?' tarzında gerilimli bir tartışma sorusu sor.",
        "en": "Final scene: 'How do you explain this event? Tell me in the comments!' or 'Do you believe this — yes or no?' Keep the suspense alive.",
    },
    "14_movie_summaries": {
        "tr": "Son sahne: 'Bu filmlerden hangisini izlediniz? Sizin favori ters köşe filminiz hangisi? Yorumlara yazın!' tarzında sinema tartışması başlat.",
        "en": "Final scene: 'Have you seen these? What's your favourite plot-twist film? Drop it in the comments!' Spark a movie recommendation thread.",
    },
    "15_football_transfers": {
        "tr": "Son sahne: 'Bu transfer gerçekleşirse takımı güçlenir mi zayıflar mı? Yorumlara beklentini yaz!' veya 'Sence bonservis bedeli hak ediyor mu?' tarzında futbol tartışması başlat.",
        "en": "Final scene: 'Will this transfer strengthen or weaken the team? Drop your opinion in the comments!' or 'Is that fee worth it?' Spark the football debate.",
    },
    "16_wealth_entrepreneurship": {
        "tr": "Son sahne: 'Bu girişimcinin sırrından hangi dersi çıkardın? Yorumlara yaz!' veya 'Aynı fırsatla karşılaşsaydın ne yapardın?' tarzında ilham verici bir kapanış sorusu sor.",
        "en": "Final scene: 'What lesson did you take from this story? Share in the comments!' or 'What would you have done with the same opportunity?' Close with entrepreneurial inspiration.",
    },
    "17_before_after_evolution": {
        "tr": "Son sahne: 'Bu değişim sizi en çok hangi açıdan şaşırttı? Yorumlara yazın!' veya '50 yıl sonra bu nasıl görünecek? Tahminini paylaş.' tarzında nostalji/gelecek tartışması başlat.",
        "en": "Final scene: 'Which change surprised you most? Tell me in the comments!' or 'What will this look like in 50 years? Share your prediction.' Spark a past-vs-future debate.",
    },
    "18_astrology_horoscope": {
        "tr": "Son sahne: 'Kendi burcunuzu yorumlara yazın, hangi özellik size uymadı?' veya 'Bu hafta hayatınıza en çok hangi yorum yansıdı?' tarzında burç temelli yorumu kişiselleştir.",
        "en": "Final scene: 'Drop your sign in the comments — which trait didn't fit you?' or 'Which prediction came true for you this week?' Make the horoscope personal.",
    },
    "19_historical_battles": {
        "tr": "Son sahne: 'O kritik kararı sen alsaydın ne yapardın? Yorumlara yaz!' veya 'Bu savaşın seyri farklı olsaydı tarih nasıl değişirdi?' tarzında tarihi tartışma başlat.",
        "en": "Final scene: 'What would you have done in that critical moment? Tell me in the comments!' or 'How would history have changed with a different choice?' Spark a historical debate.",
    },
    "20_whatsapp_chat_story": {
        "tr": "Son sahne: 'Siz bu mesajı görseydiniz nasıl cevap verirdiniz? Yorumlara yazın!' veya 'Bu mesajlaşmada kim haklıydı?' tarzında drama tartışması başlat.",
        "en": "Final scene: 'What would you have replied to that message? Tell me in the comments!' or 'Who was right in this conversation?' Keep the drama discussion going.",
    },
    "21_ai_tools_hacks": {
        "tr": "Son sahne: 'Bu araçlardan hangisini kullanmaya başladın? Favorin hangisi? Yorumlara yaz!' veya 'Hangi görevi artık yapay zekaya yaptırıyorsun?' tarzında teknoloji tartışması başlat.",
        "en": "Final scene: 'Which tool will you try first? Drop your favourite in the comments!' or 'What task do you already delegate to AI?' Spark a productivity conversation.",
    },
    "22_emoji_guess_game": {
        "tr": "Son sahne: 'Kaçını doğru bildin? Skoru yorumlara yaz!' veya bu sefer izleyicinin 3 emojili bir film şifresi oluşturmasını isteyen bir görev ver.",
        "en": "Final scene: 'How many did you get right? Drop your score in the comments!' or challenge viewers to create their own 3-emoji movie code.",
    },
    "23_fitness_nutrition_hacks": {
        "tr": "Son sahne: 'Bu tüyolardan hangisini yarın deneyeceksin? Yorumlara yaz!' veya 'Senin en iyi yağ yakma tüyon nedir? Paylaş!' tarzında fitness topluluk motivasyonu oluştur.",
        "en": "Final scene: 'Which tip will you try tomorrow? Tell me in the comments!' or 'What's your best fat-loss hack? Share it!' Build community fitness motivation.",
    },
    "24_sigma_character_study": {
        "tr": "Son sahne: 'Bu kurallardan hangisini zaten uyguluyorsun? Yorumlara yaz!' veya 'Hangisi sana en çok uymadı — neden?' tarzında karakter/kişisel gelişim refleksiyonu teşvik et.",
        "en": "Final scene: 'Which of these rules do you already follow? Tell me in the comments!' or 'Which one challenged you most — and why?' Encourage self-reflection.",
    },
    "25_celebrity_net_worth": {
        "tr": "Son sahne: 'Bu serveti sen olsan nasıl harcardın? Yorumlara yaz!' veya 'Bu rakam sizi şaşırttı mı? Ne düşündünüz?' tarzında magazin tartışması başlat.",
        "en": "Final scene: 'How would you spend that fortune? Tell me in the comments!' or 'Did that number surprise you? What do you think?' Spark a wealth conversation.",
    },
    "26_dangerous_places": {
        "tr": "Son sahne: 'Bu yerlerden birine gitme şansın olsaydın gider miydin? Yorumlara yaz!' veya 'Hangi yer seni en çok tüyleri diken diken etti?' tarzında tehlikeli merak tartışması başlat.",
        "en": "Final scene: 'Would you ever visit one of these places if you could? Tell me in the comments!' or 'Which location gave you the most chills?' Keep the danger curiosity alive.",
    },
    "27_common_myths_busted": {
        "tr": "Son sahne: 'Bu yanlışları daha önce doğru biliyor muydunuz? Yorumlara yazın!' veya 'Hangi bilgiye en çok şaşırdınız? Çevrenizde hala buna inanan var mı?' tarzında mit tartışması başlat.",
        "en": "Final scene: 'Did you believe any of these myths before? Tell me in the comments!' or 'Which one shocked you most? Does anyone you know still believe it?' Bust the myth socially.",
    },
    "28_dream_meanings": {
        "tr": "Son sahne: 'Bu rüyaları hiç gördünüz mü? Bilinçaltınız size ne söylüyor? Yorumlara yazın!' tarzında izleyicinin kendi rüya deneyimini paylaşmasını davet et.",
        "en": "Final scene: 'Have you ever had one of these dreams? What do you think your subconscious is telling you? Share in the comments!' Invite personal dream stories.",
    },
    "29_optical_illusions_iq": {
        "tr": "Son sahne: 'Hangi resmi ilk gördünüz? IQ'nuz kaç? Yorumlara yazın!' tarzında izleyiciyi kendi algı skorunu paylaşmaya davet et.",
        "en": "Final scene: 'What did you see first? Drop your IQ score in the comments!' Invite viewers to share their perception result.",
    },
    "30_poetry_quotes": {
        "tr": "Son sahne: 'Bu mısralardan hangisi kalbinize en çok dokundu? Yorumlarda paylaşın.' tarzında duygusal bir edebiyat bağı kur. Mekanik takip çağrısı YASAK.",
        "en": "Final scene: 'Which of these lines touched your heart most? Share in the comments.' Build emotional literary connection without mechanical subscribe calls.",
    },
    "31_supercars_automotive": {
        "tr": "Son sahne: 'Bu canavarlardan hangisini kendi garajınızda görmek isterdiniz? Yorumlara yazın!' tarzında otomobil tutkusunu tartışmaya çevir.",
        "en": "Final scene: 'Which of these hypercars belongs in your dream garage? Drop your pick in the comments!' Turn automotive passion into debate.",
    },
    "32_legal_consumer_hacks": {
        "tr": "Son sahne: 'Bu yasal hakkınızı daha önce biliyor muydunuz? Başınıza benzer bir olay geldi mi? Yorumlara yazın!' tarzında hak arama bilinci oluştur.",
        "en": "Final scene: 'Did you know about this legal right before? Have you ever faced this situation? Share in the comments!' Build consumer awareness.",
    },
    "33_parenting_child_hacks": {
        "tr": "Son sahne: 'Çocuğunuzla iletişimde en çok hangi yöntem işe yarıyor? Deneyiminizi yorumlarda paylaşın.' tarzında sıcak ebeveyn dayanışması kur.",
        "en": "Final scene: 'Which parenting approach works best with your child? Share your experience in the comments.' Build warm parenting community.",
    },
    "34_gaming_easter_eggs": {
        "tr": "Son sahne: 'Bu gizli detayı oyun içinde kendi gözünüzle görmüş müydünüz? Bildiğiniz başka efsane sır var mı? Yorumlara yazın!' tarzında oyuncu tartışması başlat.",
        "en": "Final scene: 'Did you ever spot this secret in-game yourself? What's your favourite easter egg? Drop it in the comments!' Spark gamer discussion.",
    },
    "35_animal_kingdom_stories": {
        "tr": "Son sahne: 'Doğadaki bu strateji sizi de şaşırttı mı? Vahşi yaşamın en güçlü avcısı sizce hangisi? Yorumlara yazın!' tarzında doğa merakını yoruma çevir.",
        "en": "Final scene: 'Did this survival strategy surprise you? Which wild predator is the ultimate champion? Tell me in the comments!' Turn wildlife awe into engagement.",
    },
    "36_kids_animation": {
        "tr": "Son sahne: nazikçe bugünün güzel davranışını özetle ve sevgi dolu bir kapanış yap; çocuk videosu olduğu için yorum tuzağı veya abone baskısı KURMA.",
        "en": "Final scene: gently recap today's kind lesson with a warm, cheerful goodbye; Made for Kids — do NOT include comment bait or subscribe pressure.",
    },
    "37_interactive_quiz": {
        "tr": "Son sahne: 'Kaçta kaç yaptın? Süre bitmeden doğru cevabı bulabildin mi? Skorunu hemen yorumlara yaz!' tarzında yüksek enerjili skor yarışması başlat.",
        "en": "Final scene: 'What was your score? Did you beat the timer? Drop your score in the comments right now!' Spark a high-energy score challenge.",
    },
    # Legacy alias keys preserved for backward compatibility
    "30_animal_world": {
        "tr": "Son sahne: 'Bu hayvan gerçekten var olduğuna inanabiliyor musunuz? Favoriniz hangisi? Yorumlara yazın!' tarzında doğa hayranlığını yoruma çevir.",
        "en": "Final scene: 'Can you believe this animal actually exists? Which is your favourite? Tell me in the comments!' Turn nature wonder into engagement.",
    },
    "31_space_cosmos": {
        "tr": "Son sahne: 'Bu bilgi sizi de aklınızı başınızdan aldı mı? Evren hakkındaki en büyük sorunuz ne? Yorumlara yazın!' tarzında kozmos merakını tartışmaya çevir.",
        "en": "Final scene: 'Did this blow your mind too? What's your biggest question about the universe? Tell me in the comments!' Turn cosmic wonder into debate.",
    },
    "32_relationship_tips": {
        "tr": "Son sahne: 'Bu ipuçlarından hangisi ilişkinize en çok uymadı? Yorumlara yazın!' veya 'Siz ne yapardınız bu durumda?' tarzında empati ve tartışma oluştur.",
        "en": "Final scene: 'Which tip surprised you most in your own relationship? Tell me in the comments!' or 'What would you do in this situation?' Build empathetic discussion.",
    },
    "33_cooking_recipes": {
        "tr": "Son sahne: 'Bu tarifi denemek ister misiniz? Favoriniz hangisi? Yorumlara yazın!' veya 'Sizin gizli malzemeniz nedir? Paylaşın!' tarzında mutfak topluluğu oluştur.",
        "en": "Final scene: 'Would you try this recipe? Drop your favourite in the comments!' or 'What's your secret ingredient? Share it!' Build a cooking community.",
    },
    "34_travel_destinations": {
        "tr": "Son sahne: 'Bu yerlerden birine gitme fırsatınız olsa hangisini seçerdiniz? Yorumlara yazın!' veya 'En çok hangi detay sizi cezbetti? Paylaşın.'",
        "en": "Final scene: 'If you could visit one of these places, which would you choose? Tell me in the comments!' or 'Which detail tempted you most? Share it!'",
    },
    "35_personal_finance": {
        "tr": "Son sahne: 'Bu finansal tüyolardan hangisini yarın uygulayacaksın? Yorumlara yaz!' veya 'Paranı en çok nerede israf ettiğini fark ettin mi? Paylaş.' tarzında para farkındalığı oluştur.",
        "en": "Final scene: 'Which financial tip will you apply tomorrow? Tell me in the comments!' or 'Where do you waste the most money — be honest!' Build financial self-awareness.",
    },
}
