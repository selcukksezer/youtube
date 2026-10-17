"""
Extended niche-specific procedural fallback scene generators (Religious/Hadith,
Dark Psychology, Astrology, Crypto Market).
"""
from typing import Any, Dict


def _generate_religious_quotes_scenes(clean_title: str, is_tr: bool, variation_seed: int = 0) -> Dict[str, Any]:
    """Islamic hadith/quran bilingual fallback — authentic Arabic tashkeel + Turkish translation + book citations."""
    topic = (clean_title or "").strip() or ("Günün Hadis-i Şerifi" if is_tr else "Daily Hadith")
    variant_idx = int(variation_seed or 0) % 3
    if is_tr:
        tr_datasets = [
            {
                "narrations": [
                    f"Hazreti Peygamber'in buyurduğu ve hayatımızı baştan sona aydınlatacak o kutlu ölçüye kulak verin.",
                    "Resulullah buyurdu: 'Ameller ancak niyetlere göredir ve herkesin niyet ettiği ne ise eline geçecek odur.'",
                    "İhlasla yapılan küçük bir amel, samimiyetsiz yapılan dağlar kadar amelden çok daha hayırlı ve bereketlidir.",
                    "Kim niyetini Allah'ın rızasına ve hayra bağlarsa, attığı her adımda manevi bir ferahlık bulur.",
                    "Peygamberimiz buyurur: 'İnsanlara kolaylaştırınız, asla zorlaştırmayınız; müjdeleyiniz, insanları nefret ettirip soğutmayınız.'",
                    "Güzel bir söz söylemek, bir gönle dokunmak ve bir tebessüm bırakmak sadaka yerine geçer.",
                    "Sizden biriniz, kendisi için arzulayıp istediğini din kardeşi için de istemedikçe kamil bir mümin olamaz.",
                    "Resulullah uyarır: 'Yeryüzündeki insanlara merhamet etmeyene göklerin Rabbi de merhamet etmez.'",
                    "Dua ibadetin özüdür; samimi ve ihlaslı bir niyetle açılan eller hiçbir zaman boş çevrilmez.",
                    "Rabbimiz şöyle buyurur: 'Bize dünyada da güzellik ver, ahirette de güzellik ver ve bizi koru.'",
                    "Her işinde ve her daraldığın anda yalnız sonsuz kudret sahibi olan Allah'a güvenip dayan.",
                    "Bu kutlu hadis-i şerifi hayatına rehber etmeye niyet ettiysen yoruma amin yaz, sevdiklerinle paylaş.",
                ],
                "arabic": [
                    "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                    "«إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ»",
                    "«وَإِنَّمَا لِكُلِّ امْرِئٍ مَا نَوَى»",
                    "«فَمَنْ كَانَتْ هِجْرَتُهُ إِلَى اللَّهِ وَرَسُولِهِ»",
                    "«يَسِّرُوا وَلَا تُعَسِّرُوا، وَبَشِّرُوا وَلَا تُنَفِّرُوا»",
                    "«الْكَلِمَةُ الطَّيِّبَةُ صَدَقَةٌ»",
                    "«لَا يُؤْمِنُ أَحَدُكُمْ حَتَّى يُحِبَّ لِأَخِيهِ مَا يُحِبُّ لِنَفْسِهِ»",
                    "«مَنْ لَا يَرْحَمْ لَا يُرْحَمْ»",
                    "«الدُّعَاءُ مُخُّ الْعِبَادَةِ»",
                    "«رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الآخِرَةِ حَسَنَةً»",
                    "«وَتَوَكَّلْ عَلَى الْعَزِيزِ الرَّحِيمِ»",
                    "«سُبْحَانَ اللَّهِ وَبِحَمْدِهِ»",
                ],
                "citations": [
                    "(Hadis-i Şerif - Sahih-i Buhari)",
                    "(Buhari, Bed'ü'l-Vahy, 1)",
                    "(Müslim, İmare, 155)",
                    "(Buhari, İman, 41)",
                    "(Buhari, İlim, 11)",
                    "(Buhari, Cihad, 128)",
                    "(Buhari, İman, 7)",
                    "(Müslim, Fedail, 65)",
                    "(Tirmizi, Dua, 1)",
                    "(Bakara Suresi, 201)",
                    "(Şuara Suresi, 217)",
                    "(Müslim, Zikir, 26)",
                ],
            },
            {
                "narrations": [
                    f"Ve düşünün ki Rabbiniz size şöyle ilan buyurdu, bu kutlu çağrıya kulak verin:",
                    "Rabbiniz buyurdu: 'Eğer şükrederseniz, elbette size olan nimetimi kat kat artırıp bereketlendiririm.'",
                    "'Ama nankörlük edip verilen nimeti inkar ederseniz, şüphesiz benim azabım çok ama çok çetindir.'",
                    "'Bilesiniz ki, dünyada aradığınız huzur ve sükuneti kalpler ancak Allah'ı anmakla ve zikirle bulur.'",
                    "İnşirah suresinin müjdesiyle: 'Şüphesiz her güçlük ve sıkıntıyla beraber mutlaka bir kolaylık vardır.'",
                    "'Evet, hiç şüphe yok ki her zorluğun yanında elbette bir kolaylık daha beklemektedir.'",
                    "'Rabbiniz şöyle buyurdu: Yalnız bana samimiyetle dua edin ki, ben de sizin dualarınıza cevap vereyim.'",
                    "'Ey iman edenler! Sabır ve namaz ile Allah'tan yardım dileyin; çünkü Allah sabredenlerle beraberdir.'",
                    "'Allah bize yeter, O ne güzel bir vekildir ve kulunu asla yalnız bırakmaz.'",
                    "'Kullarım sana beni sorarlarsa şüphesiz de ki: Ben onlara şah damarından bile daha yakınım.'",
                    "'Öyleyse siz beni anın ki ben de sizi anayım; bana şükredin ve asla nankörlük etmeyin.'",
                    "Rabbimiz dualarımızı kabul eylesin. Kalbinden geçirdiğin hayırlı niyete bir amin de, hayra vesile ol.",
                ],
                "arabic": [
                    "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                    "«وَإِذْ تَأَذَّنَ رَبُّكُمْ لَئِن شَكَرْتُمْ لَأَزِيدَنَّكُمْ»",
                    "«وَلَئِن كَفَرْتُمْ إِنَّ عَذَابِي لَشَدِيدٌ»",
                    "«أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ»",
                    "«فَإِنَّ مَعَ الْعُسْرِ يُسْرًا»",
                    "«إِنَّ مَعَ الْعُسْرِ يُسْرًا»",
                    "«وَقَالَ رَبُّكُمُ ادْعُونِي أَسْتَجِبْ لَكُمْ»",
                    "«إِنَّ اللَّهَ مَعَ الصَّابِرِينَ»",
                    "«حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ»",
                    "«وَإِذَا سَأَلَكَ عِبَادِي عَنِّي فَإِنِّي قَرِيبٌ»",
                    "«فَاذْكُرُونِي أَذْكُرْكُمْ وَاشْكُرُوا لِي»",
                    "«رَبَّنَا تَقَبَّلْ مِنَّا إِنَّكَ أَنتَ السَّمِيعُ الْعَلِيمُ»",
                ],
                "citations": [
                    "(Kur'an-ı Kerim Meali İbrahim Suresi 7)",
                    "(İbrahim Suresi, 7)",
                    "(İbrahim Suresi, 7)",
                    "(Rad Suresi, 28)",
                    "(İnşirah Suresi, 5)",
                    "(İnşirah Suresi, 6)",
                    "(Mümin Suresi, 60)",
                    "(Bakara Suresi, 153)",
                    "(Al-i İmran Suresi, 173)",
                    "(Bakara Suresi, 186)",
                    "(Bakara Suresi, 152)",
                    "(Bakara Suresi, 127)",
                ],
            },
            {
                "narrations": [
                    f"Hz. Peygamber'in (s.a.v.) ümmetine bıraktığı bu altın öğütler bugün kalbinize şifa ve rehber olsun.",
                    "Resulullah buyurdu: 'Bizi aldatan, insanları kandıran ve hileye başvuran kimseler asla bizden değildir.'",
                    "'Doğruluktan ve dürüstlükten asla ayrılmayın; çünkü doğruluk insanı iyiliğe, iyilik ise cennete ulaştırır.'",
                    "'Kalbinde hardal tanesi kadar kibir, gurur ve büyüklenme bulunan kimse cennete giremez.'",
                    "'İki büyük nimet vardır ki insanların çoğu bunda aldanmıştır: Sağlık ve değerlendirilmeyen boş vakit.'",
                    "'Sizin en hayırlınız Kur'an'ı hakkıyla öğrenen ve onu diğer insanlara samimiyetle öğretendir.'",
                    "'Nerede olursan ol Allah'tan sakın ve bir hatanın peşinden hemen telafi edici bir iyilik yap.'",
                    "'Birbirinize asla haset etmeyin, kin beslemeyin; ey Allah'ın kulları, birbirinize kardeş olun.'",
                    "'Allah'ım! Senden dosdoğru hidayet, takva, ahlaki iffet ve kalbe gerçek bir gönül zenginliği diliyorum.'",
                    "'Allah'ım! Bütün işlerimin temeli ve koruyucusu olan dinimi, dünyamı ve geleceğimi ıslah eyle.'",
                    "'Allah'ım! Sen çok affedicisin, kullarını affetmeyi çok seversin, öyleyse benim günahlarımı da bağışla.'",
                    "Bu kutlu dualara amin diyen tüm diller hayırla dolsun. Yoruma amin yazarak kardeşlerimize ulaştırın.",
                ],
                "arabic": [
                    "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                    "«مَنْ غَشَّنَا فَلَيْسَ مِنَّا»",
                    "«عَلَيْكُمْ بِالصِّدْقِ فَإِنَّ الصِّدْقَ يَهْدِي إِلَى الْبِرِّ»",
                    "«لَا يَدْخُلُ الْجَنَّةَ مَنْ كَانَ فِي قَلْبِهِ مِثْقَالُ ذَرَّةٍ مِنْ كِبْرٍ»",
                    "«نِعْمَتَانِ مَغْبُونٌ فِيهِمَا كَثِيرٌ: الصِّحَّةُ وَالْفَرَاغُ»",
                    "«خَيْرُكُمْ مَنْ تَعَلَّمَ الْقُرْآنَ وَعَلَّمَهُ»",
                    "«اتَّقِ اللَّهَ حَيْثُمَا كُنْتَ وَأَتْبِعِ السَّيِّئَةَ الْحَسَنَةَ»",
                    "«لَا تَحَاسَدُوا وَلَا تَبَاغَضُوا وَكُونُوا عِبَادَ اللَّهِ إِخْوَانًا»",
                    "«اللَّهُمَّ إِنِّي أَسْأَلُكَ الْهُدَى وَالتُّقَى وَالْعَفَافَ وَالْغِنَى»",
                    "«اللَّهُمَّ أَصْلِحْ لِي دِينِي الَّذِي هُوَ عِصْمَةُ أَمْرِي»",
                    "«اللَّهُمَّ إِنَّكَ عَفُوٌّ تُحِبُّ الْعَفْوَ فَاعْفُ عَنِّي»",
                    "«الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ»",
                ],
                "citations": [
                    "(Hadis-i Şerif - Sahih-i Müslim)",
                    "(Müslim, İman, 164)",
                    "(Buhari, Edeb, 69)",
                    "(Müslim, İman, 147)",
                    "(Buhari, Rikak, 1)",
                    "(Buhari, Fezailü'l-Kur'an, 21)",
                    "(Tirmizi, Birr, 55)",
                    "(Buhari, Edeb, 57)",
                    "(Müslim, Zikir, 72)",
                    "(Müslim, Zikir, 71)",
                    "(Tirmizi, Daavat, 84)",
                    "(Fatiha Suresi, 2)",
                ],
            },
        ]
        chosen = tr_datasets[variant_idx]
        narrations, arabic_texts, citations = chosen["narrations"], chosen["arabic"], chosen["citations"]
    else:
        en_variants = [
            [
                f"The timeless prophetic guidance regarding {topic} brings profound peace to the soul.",
                "The Messenger of Allah said: 'Actions are judged by motives and intentions alone.'",
                "'And every person shall have what he intended in his sincere heart.'",
                "Whoever turns his intentions toward truth will find every small step blessed.",
                "'Make things easy and do not make them difficult; give glad tidings and do not repel.'",
                "'A kind word uttered with gentleness is a blessed act of charity.'",
                "'None of you truly believes until he loves for his brother what he loves for himself.'",
                "'He who does not show mercy to people will not be shown mercy by God.'",
                "'Supplication is the very core of devotion and remembrance.'",
                "'Our Lord! Grant us good in this world and good in the hereafter, and protect us.'",
                "Place your trust in the Almighty, the Most Merciful in all circumstances.",
                "Say amin in your heart and share this noble reminder with those you cherish.",
            ],
            [
                f"And remember when your Lord proclaimed with certainty:",
                "'If you are grateful, I will surely increase you in My favor and blessings.'",
                "'Remember that in the remembrance of God do hearts truly find rest.'",
                "'Indeed, with every hardship comes ease and relief.'",
                "'Yes, with every difficulty there is certainly ease and light.'",
                "'Your Lord says: Call upon Me; I will answer you.'",
                "'Indeed, God is with those who remain patient and steadfast.'",
                "'God is sufficient for us, and He is the best guardian and protector.'",
                "'When My servants ask you concerning Me, tell them: I am indeed near.'",
                "'So remember Me; I will remember you. Be grateful to Me.'",
                "'Our Lord, accept this sincere supplication from us.'",
                "May your sincere prayers be answered. Type amin in the comments.",
            ],
        ]
        narrations = en_variants[variant_idx % len(en_variants)]
        arabic_texts = [
            "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
            "«إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ»",
            "«وَإِنَّمَا لِكُلِّ امْرِئٍ مَا نَوَى»",
            "«فَمَنْ كَانَتْ هِجْرَتُهُ إِلَى اللَّهِ وَرَسُولِهِ»",
            "«يَسِّرُوا وَلَا تُعَسِّرُوا، وَبَشِّرُوا وَلَا تُنَفِّرُوا»",
            "«الْكَلِمَةُ الطَّيِّبَةُ صَدَقَةٌ»",
            "«لَا يُؤْمِنُ أَحَدُكُمْ حَتَّى يُحِبَّ لِأَخِيهِ مَا يُحِبُّ لِنَفْسِهِ»",
            "«مَنْ لَا يَرْحَمْ لَا يُرْحَمْ»",
            "«الدُّعَاءُ مُخُّ الْعِبَادَةِ»",
            "«رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الآخِرَةِ حَسَنَةً»",
            "«وَتَوَكَّلْ عَلَى الْعَزِيزِ الرَّحِيمِ»",
            "«سُبْحَانَ اللَّهِ وَبِحَمْدِهِ»",
        ]
        citations = [
            "(Hadith - Sahih al-Bukhari)", "(Bukhari, 1)", "(Muslim, 155)", "(Bukhari, 41)",
            "(Bukhari, 11)", "(Bukhari, 128)", "(Bukhari, 7)", "(Muslim, 65)",
            "(Tirmidhi, 1)", "(Surah al-Baqarah, 201)", "(Surah ash-Shu'ara, 217)", "(Muslim, 26)",
        ]

    visuals = [
        ("Majestic Kaaba Mecca holy sanctuary aerial view at sunrise, peaceful sacred atmosphere", ["kaaba mecca sanctuary aerial", "grand mosque mecca dawn", "peaceful sacred sanctuary dawn"]),
        ("Open Quran pages with soft window light, no faces", ["open quran pages soft light", "arabic manuscript closeup", "holy book still life"]),
        ("Mosque dome catching golden sunrise light, no people facing camera", ["mosque dome golden sunrise", "islamic architecture dawn", "minaret silhouette morning"]),
        ("Prayer hands raised at dusk, cropped at wrists, respectful", ["prayer hands raised dusk", "open palms dua", "hands supplication sunset"]),
        ("Islamic geometric tile and gold calligraphy wall, no figurative idols", ["islamic geometric calligraphy", "arabesque tile pattern", "gold kufic art wall"]),
        ("Intricate Quran manuscript golden calligraphy illumination in soft cinematic light", ["quran golden calligraphy art", "islamic gold illumination manuscript", "sacred calligraphy parchment macro"]),
        ("Mosque interior lanterns glowing over empty prayer hall", ["mosque lantern interior glow", "prayer hall lamps", "islamic architecture interior"]),
        ("Olive grove in peaceful morning mist, Mediterranean", ["olive grove peaceful morning", "mediterranean olive trees dawn", "calm orchard mist"]),
        ("Courtyard fountain for ablution, water ripples, no faces", ["ablution water fountain courtyard", "mosque courtyard fountain", "wudu water closeup"]),
        ("Crescent moon above a distant mosque at night", ["crescent moon over mosque", "night sky islamic architecture", "ramadan night sky"]),
        ("Prayer rug still life with tasbih beads, no figurative art", ["prayer rug still life", "tasbih beads closeup", "islamic prayer mat detail"]),
        ("Close-up of Arabic calligraphy ink on paper, abstract letters only", ["arabic calligraphy closeup", "islamic calligraphy ink", "quranic script macro"]),
    ]
    moods = ["reverent", "hopeful", "peaceful", "solemn", "luminous", "calm", "warm", "contemplative", "hopeful", "reverent", "peaceful", "warm"]
    if len(narrations) > 10:
        chosen_indices = list(range(9)) + [len(narrations) - 1]
        narrations = [narrations[idx] for idx in chosen_indices]
        arabic_texts = [arabic_texts[idx] for idx in chosen_indices if idx < len(arabic_texts)]
        citations = [citations[idx] for idx in chosen_indices if idx < len(citations)]

    shift = variation_seed % len(visuals)
    scenes = []
    for i, narr in enumerate(narrations):
        desc, queries = visuals[(i + shift) % len(visuals)]
        scene_item = {
            "scene_number": i + 1,
            "narration": narr,
            "scene_description": desc,
            "search_queries": queries,
            "duration": 4.5,
            "mood": moods[i % len(moods)],
            "beat_type": "hook" if i == 0 else "resolution" if i == len(narrations) - 1 else "conflict",
        }
        if i < len(arabic_texts):
            scene_item["arabic_text"] = arabic_texts[i]
        if i < len(citations):
            scene_item["source_citation"] = citations[i]
        scenes.append(scene_item)

    return {
        "title": topic if is_tr else f"Hadith: {topic}",
        "visual_theme": "blue silk luxury mosque quran prayer calligraphy sunrise respectful islamic",
        "full_narration": " ".join(narrations),
        "scenes": scenes,
        "niche_id": "10_religious_quotes",
        "procedural_fallback": True,
        "scenario_pack_family": "religious",
    }


def _generate_dark_psychology_scenes(clean_title: str, is_tr: bool, variation_seed: int = 0) -> Dict[str, Any]:
    """Constructs Dark Psychology & Body Language format."""
    var_idx = int(variation_seed or 0) % 3
    if var_idx == 1:
        narrations_tr = [
            f"Kişiliğinizi sessizce ele geçiren {clean_title} ve Gaslighting manipülasyonunun anatomisi...",
            "Birisi sürekli hafızanızı sorgulatıyor ve 'sen yanlış hatırlıyorsun' diyorsa dikkat edin.",
            "Gaslighting ustaları gerçeği çarpıtarak kendi algılarını size tek doğru gibi kabul ettirir.",
            "Önce güveninizi kazanıp ardından en emin olduğunuz konularda bile şüpheye düşmenizi sağlarlar.",
            "Kendinizi sürekli özür dilerken buluyorsanız, duygusal bir kontrol ağının tam ortasındasınız demektir.",
            "Sizi yakın çevrenizden ve ailenizden izole ederek tek bilgi kaynağı haline gelmeye çalışırlar.",
            "Mikro mimiklerdeki yapay gülümseme ve sabit göz teması, gizli niyetin en net kanıtıdır.",
            "Hatalarını asla kabul etmezler; suçluluk duygusunu ustalıkla sizin üzerinize yıkarlar.",
            "Bu tuzağı bozmanın tek yolu kendi gerçekliğinize güvenmek ve söylenenleri yazılı kaydetmektir.",
            "Manipülatör ile asla duygusal tartışmaya girmeyin; soğuk gerçekler onların en büyük kabusudur.",
            "Sınırlarınızı net koyun: 'Ben böyle hatırlıyorum ve bu konuda tartışmayacağım' deyin.",
            "Kendi değerini bilen bir insanı hiçbir duygusal manipülasyon köşeye sıkıştıramaz.",
            "Farkındalık en büyük kalkandır; zihninizi kimsenin kontrol etmesine izin vermeyin.",
            "Hayatınızda böyle bir Gaslighting tecrübesi yaşadınız mı? Yorumlarda paylaşın, konuşalım!"
        ]
    elif var_idx == 2:
        narrations_tr = [
            f"İnsanların beden diliyle açık ettiği {clean_title} arkasındaki gizli bilinçaltı sinyalleri...",
            "Kelimeler yalan söyler ama mikro kas hareketleri ve beden postürü asla yalan söyleyemez.",
            "Bir konuşmada kollarını kavuşturan ve ayaklarını kapıya çeviren kişi sohbetten zihnen kopmuştur.",
            "Göz temasını aniden kesip sağ alta bakan bir zihin, genellikle duygusal bir savunma kurguluyordur.",
            "Aynalama taktiği: Karşınızdaki kişi duruşunuzu taklit ediyorsa ya size hayrandır ya da sizi ikna etmeye çalışıyordur.",
            "Ses tonunu aniden fısıltıya düşüren insanlar, bilinçaltınızda sahte bir samimiyet yaratmak ister.",
            "Tuzak soru karşısında boğaz temizleme veya yakayla oynama refleksi gizli bir gerginliğin işaretidir.",
            "Güçlü bir duruş için omuzları geriye çekmek ve doğrudan göz teması kurmak zihinsel üstünlük sağlar.",
            "Karşı tarafın manipülatif baskısını hissettiğinizde üç saniye sessizce bekleyip konuşun.",
            "Sessizlik baskıyı karşı tarafa geri iter ve manipülatörün paniklemesine yol açar.",
            "Kendi enerjinizi korumak, karşınızdaki kişinin psikolojik oyunlarını tek hamlede boşa çıkarır.",
            "Beden dilini okumayı öğrenen bir insan, girdiği her ortamda gizli lider haline gelir.",
            "İnsanları dikkatle gözlemleyin; çünkü gerçek niyetler sözlerde değil tavırlarda gizlidir.",
            "Siz karşınızdakinin yalan söylediğini en çok hangi hareketinden anlarsınız? Yorumlara yazın!"
        ]
    else:
        narrations_tr = [
            f"İnsanların sizden gizlediği {clean_title} arkasındaki karanlık psikolojik gerçek...",
            "Günlük hayatta karşılaştığınız insanların birçoğu bilinçaltınıza fark ettirmeden hükmetmeye çalışır.",
            "Manipülasyon ustaları asla doğrudan saldırmaz; en zayıf noktanızı sessizce analiz ederler.",
            "Göz temasındaki o 3 saniyelik mikro gecikme, yalanın ve gizli niyetin ilk işaretidir.",
            "Size kendinizi borçlu hissettirerek kontrolü ele alma taktiğine psikolojide 'Tuzak İkram' denir.",
            "Birisi sizi sürekli övüp aniden geri çekiliyorsa, bağımlılık yaratan 'Aralıklı Pekiştirme' altındasınız.",
            "Beden dili asla yalan söylemez; ayak uçlarının baktığı yön kişinin gitmek istediği gerçek yeri gösterir.",
            "Özgüveninizi kırmak için yapılan gizli iğnelemeler, zihinsel sınırlarınızı test etme yöntemidir.",
            "Bu taktikleri fark ettiğiniz anda manipülatörün üzerinizdeki tüm gücü bir anda yok olur.",
            "Karanlık psikolojiye karşı en güçlü savunma, duygularınızla değil soğukkanlı mantığınızla tepki vermektir.",
            "Sessizlik, bir manipülatörün en çok korktuğu ve paniklediği nihai silahtır.",
            "Kendi sınırlarını net çizen bir insanı hiçbir psikolojik hile tuzağa düşüremez.",
            "Gözlerinizi dört açın; çünkü algınızı yöneten kişi hayatınızı da yönetir.",
            "Peki siz çevrenizde bu manipülasyon taktiklerinden birine maruz kaldınız mı? Yorumlarda anlatın!"
        ]
    narrations_en = [
        f"The dark psychological reality hidden behind {clean_title} that people never talk about...",
        "In everyday life, many people subtly attempt to influence and manipulate your subconscious mind.",
        "Master manipulators never attack openly; they quietly probe and analyze your deepest vulnerabilities.",
        "A three-second micro-delay in genuine eye contact is the earliest subconscious signal of hidden deception.",
        "Making you feel indebted to gain psychological leverage is known in behavioral science as the 'Debt Trap'.",
        "If someone showers you with excessive praise only to abruptly withdraw, you are under intermittent reinforcement.",
        "Body language never lies; the direction a person's feet point reveals where their true subconscious desires lie.",
        "Subtle backhanded compliments are calculated tests designed to erode your self-confidence and boundaries.",
        "The moment you recognize these covert psychological games, the manipulator instantly loses all power over you.",
        "Your ultimate defense against dark psychology is responding with cold, unshakeable logic rather than emotional reactivity.",
        "Strategic silence is the weapon manipulators fear the most because it deprives them of emotional validation.",
        "An individual who establishes crystal-clear personal boundaries can never be trapped by psychological games.",
        "Keep your eyes wide open; because whoever controls your perception ultimately controls your reality.",
        "Have you ever experienced one of these psychological manipulation tactics in your life? Tell your story in the comments!"
    ]
    narrations = narrations_tr if is_tr else narrations_en
    visuals = [
        ("Shadowy silhouette profile of a person in high-contrast dark rim lighting", ["dark psychology shadow lighting", "silhouette moody profile dark", "mysterious man shadow face"]),
        ("Crowded urban sidewalk with anonymous faces blurred in cold tones", ["crowded sidewalk blur cold", "anonymous faces city dark", "subconscious urban crowd"]),
        ("Macro extreme close-up of human pupil dilating in dramatic lighting", ["human pupil dilating eye", "eye macro extreme close up", "intense stare iris detail"]),
        ("Micro-expression smile turning cold and calculated in split second", ["micro expression human face", "cold fake smile closeup", "deceptive expression portrait"]),
        ("Two people shaking hands with subtle tense finger pressure under spotlight", ["handshake business tension dark", "secret deal hands closeup", "manipulative agreement"]),
        ("Abstract neural pathways lighting up in dark brain digital matrix", ["brain neural network glowing", "subconscious mind abstract data", "psychology thoughts digital"]),
        ("Close-up of leather dress shoes shifting angle on hardwood floor", ["feet body language floor", "standing posture shoes", "nervous feet shifting floor"]),
        ("Subtle smirk in shadows revealing hidden malicious intent", ["smirk in shadow mysterious", "cynical grin silhouette face", "devious look dark room"]),
        ("Mirror shattering into hundreds of reflective glass shards in slow motion", ["mirror shattering slow motion", "broken glass reflection shards", "breaking psychological illusion"]),
        ("Person standing calm with impassive cold face in center of storm", ["calm impassive face portrait", "stoic emotionless eyes dark", "resilient calm mind silhouette"]),
        ("Dark moody room with single beam of spotlight cutting through smoke", ["spotlight through smoke haze", "atmospheric dark room light", "solitary dramatic silence"]),
        ("Firm boundary line drawn with glowing light across dark floor", ["boundary line neon light floor", "protection shield abstract", "confident posture silhouette"]),
        ("Sharp piercing eyes looking through camera into viewer soul", ["piercing eye contact dark", "intense psychology stare", "warning cautionary portrait"]),
        ("Cinematic outro scene asking viewer to comment their personal stories", ["dark psychology outro banner", "subscribe comment engagement", "dramatic silhouette exit"])
    ]
    selected_indices = [0, 1, 2, 3, 4, 6, 7, 8, 11, 13] if len(narrations) >= 14 else list(range(min(10, len(narrations))))
    selected_narrations = [narrations[idx] for idx in selected_indices]

    scenes = []
    for i, narr in enumerate(selected_narrations):
        desc, queries = visuals[selected_indices[i] % len(visuals)]
        scenes.append({
            "scene_number": i + 1,
            "narration": narr,
            "scene_description": desc,
            "search_queries": queries,
            "duration": 4.8,
            "mood": "mysterious" if i in (0, 1, 3, 5) else "dark" if i in (2, 4, 7) else "dramatic",
            "beat_type": "hook" if i == 0 else "climax" if i == 6 else "resolution" if i == len(selected_narrations) - 1 else "conflict",
        })
    return {
        "title": clean_title if is_tr else f"Dark Psychology: {clean_title}",
        "visual_theme": "dark psychology moody violet shadow noir",
        "full_narration": " ".join(selected_narrations),
        "scenes": scenes,
        "niche_id": "7_dark_psychology",
        "procedural_fallback": True,
    }


def _generate_astrology_horoscope_scenes(clean_title: str, is_tr: bool, variation_seed: int = 0) -> Dict[str, Any]:
    """Astrology / weekly horoscope format."""
    topic = clean_title.strip() or ("Haftalık Burç Yorumu" if is_tr else "Weekly Horoscope")
    variant = (sum(ord(c) for c in topic.lower()) + variation_seed * 11) % 2

    if is_tr:
        narrations_variants = [
            [
                f"Bu hafta gökyüzü {topic} için kritik bir dönemeçte — üç burç özellikle parlayacak! ✨🔮",
                "Merkür retrosu bitiyor; iletişim ve karar verme enerjisi yeniden açılıyor, fırsatlar geliyor. 🌙",
                "Şanslı burç listesinde üçüncü sırada Yengeç: duygusal sezgileri bu hafta altın değerinde. 🦀",
                "İkinci sırada Aslan: kariyer kapıları ve tanınma fırsatları kapıda bekliyor. ♌",
                "Birinci sırada Koç: para ve girişim enerjisi tavan yapıyor — fırsatları kaçırma! ♈💰",
                "Aşk tarafında Terazi ve Balık bu hafta en uyumlu çiftler arasında öne çıkıyor. 💕",
                "Boğa burcu için sabır haftası: acele karar vermek pahalıya patlayabilir. 🐂",
                "İkizler meraklı zihniyle yeni bağlantılar kuruyor; sosyal medya etkileşimi artıyor. ♊",
                "Akrep derin dönüşüm enerjisi taşıyor; eski alışkanlıkları bırakma zamanı. 🦂",
                "Oğlak disiplinli adımlarla hedeflerine yaklaşıyor; patron dikkatini çekebilir. ♑",
                "Kova yenilikçi fikirleriyle dikkat çekiyor; beklenmedik teklifler gelebilir. ♒",
                "Başak detaycılığı bu hafta avantaj; küçük düzenlemeler büyük fark yaratır. ♍",
                f"Özet: {topic} haftasında ana tema dönüşüm, fırsat ve sezgisel kararlar. 🌟",
                "Kendi burcunu yoruma yaz — bu hafta seni ne bekliyor birlikte bakalım! 💬♈",
            ],
            [
                f"Astrolojik radar açık! {topic} — Ay'ın burç değiştirmesi herkesi etkileyecek. 🌕🔮",
                "Venüs açıları aşk ve para konularında beklenmedik sürprizler getiriyor, dikkatli ol. 💫",
                "Üçüncü şanslı burç Yay: seyahat ve genişleme enerjisi bu hafta güçlü. ♐",
                "İkinci şanslı burç Terazi: denge ve ortaklık fırsatları ön planda. ⚖️",
                "Haftanın yıldızı Balık: sezgi ve yaratıcılık para kapılarını açıyor! ♓✨",
                "Koç ve Akrep arasında tutkulu ama zorlu bir hafta — sabır şart. 🔥",
                "Boğa maddi konularda istikrar arıyor; yatırım kararlarını ertelemek akıllıca. 💎",
                "İkizler hızlı zihinle çoklu projeler arasında gidip geliyor; odaklan! ♊",
                "Yengeç aile ve ev konularında duygusal yoğunluk yaşıyor. 🏠",
                "Aslan sahne ışığı arıyor — liderlik fırsatını değerlendir, cesur adım at. 👑",
                "Başak sağlık ve rutin düzenlemeleri için ideal bir hafta. 🌿",
                "Oğlak uzun vadeli planları gözden geçirmeli; sabır meyve verecek. 📈",
                f"{topic} özeti: Ay döngüsü kararları hızlandırıyor — dinle ve harekete geç. 🌙",
                "Burcunu yoruma bırak, haftalık yorum serisinde seni de okuyalım! 💬",
            ],
        ]
        narrations = narrations_variants[variant]
    else:
        narrations = [
            f"This week the stars align for {topic} — three zodiac signs will shine brightest! ✨🔮",
            "Mercury retrograde is ending; communication and clarity return to the cosmic stage. 🌙",
            "Third luckiest sign: Cancer — emotional intuition is pure gold this week. 🦀",
            "Second place goes to Leo — career doors and recognition await bold moves. ♌",
            "Number one: Aries — money and initiative energy peak; seize the moment! ♈💰",
            "In love, Libra and Pisces form the most harmonious pairings this week. 💕",
            "Taurus faces a patience test; rushing financial decisions could backfire. 🐂",
            "Gemini's curious mind sparks new connections; social engagement surges. ♊",
            "Scorpio carries deep transformation energy; release old patterns now. 🦂",
            "Capricorn approaches goals with disciplined steps; bosses take notice. ♑",
            "Aquarius innovates boldly; unexpected offers may arrive out of nowhere. ♒",
            "Virgo's attention to detail pays off; small tweaks create big results. ♍",
            f"Wrap-up for {topic}: transformation, opportunity, and intuitive choices dominate. 🌟",
            "Comment your sign below — let's see what the cosmos has in store for you! 💬",
        ]

    visuals = [
        ("Mystical galaxy nebula with glowing zodiac wheel overlay", ["zodiac wheel galaxy nebula", "astrology chart mystical purple", "constellation stars night sky"]),
        ("Mercury planet retrograde animation with cosmic trail", ["mercury planet space cosmic", "astrology retrograde symbol", "solar system planets motion"]),
        ("Cancer crab constellation glowing in deep blue starfield", ["cancer zodiac constellation stars", "crab constellation night sky", "mystical zodiac symbol"]),
        ("Leo lion constellation golden rays dramatic lighting", ["leo zodiac constellation golden", "lion constellation stars dramatic", "fire sign astrology"]),
        ("Aries ram constellation fiery red cosmic background", ["aries zodiac constellation fire", "ram constellation stars red", "first zodiac sign cosmic"]),
        ("Libra scales and Pisces fish romantic starry overlay", ["libra pisces zodiac love", "romantic constellation couple stars", "astrology love compatibility"]),
        ("Taurus bull constellation earthy green mystical tones", ["taurus zodiac constellation earth", "bull constellation green mystical", "earth sign astrology"]),
        ("Gemini twins constellation dual glowing figures", ["gemini zodiac twins constellation", "dual stars mystical sky", "air sign astrology"]),
        ("Scorpio scorpion constellation deep violet transformation", ["scorpio zodiac constellation dark", "scorpion stars violet sky", "transformation astrology"]),
        ("Capricorn goat constellation mountain peak stars", ["capricorn zodiac mountain stars", "goat constellation night peak", "ambition astrology symbol"]),
        ("Aquarius water bearer constellation futuristic blue", ["aquarius zodiac constellation blue", "water bearer stars futuristic", "innovation astrology"]),
        ("Virgo maiden constellation clean golden starlight", ["virgo zodiac constellation golden", "maiden constellation clean stars", "detail astrology symbol"]),
        ("Full moon over zodiac wheel montage all twelve signs", ["full moon zodiac wheel", "astrology montage all signs", "lunar cycle zodiac chart"]),
        ("Host pointing at camera inviting zodiac comment engagement", ["astrology youtube outro subscribe", "zodiac comment engagement card", "mystical direct camera portrait"]),
    ]

    moods = ["mysterious", "calm", "bright", "epic", "energetic", "calm", "calm", "energetic", "dark", "calm", "energetic", "calm", "epic", "bright"]
    selected_indices = [0, 1, 2, 3, 4, 5, 8, 9, 11, 13] if len(narrations) >= 14 else list(range(min(10, len(narrations))))
    selected_narrations = [narrations[idx] for idx in selected_indices]

    scenes = []
    for i, narr in enumerate(selected_narrations):
        desc, queries = visuals[selected_indices[i] % len(visuals)]
        scenes.append({
            "scene_number": i + 1,
            "narration": narr,
            "scene_description": desc,
            "search_queries": queries,
            "duration": 4.8,
            "mood": moods[selected_indices[i] % len(moods)],
            "beat_type": "hook" if i == 0 else "climax" if i == 4 else "resolution" if i == len(selected_narrations) - 1 else "conflict",
        })

    return {
        "title": topic if is_tr else f"Weekly Horoscope: {topic}",
        "visual_theme": "mystical astrology zodiac galaxy purple gold stars",
        "full_narration": " ".join(selected_narrations),
        "scenes": scenes,
        "niche_id": "18_astrology_horoscope",
        "procedural_fallback": True,
    }


def _crypto_variant_index(clean_title: str, variation_seed: int = 0) -> int:
    base = sum(ord(c) for c in clean_title.lower()) + (variation_seed * 13)
    return base % 2


def _generate_crypto_market_scenes(clean_title: str, is_tr: bool, variation_seed: int = 0) -> Dict[str, Any]:
    """14-scene live trading / crypto market format."""
    topic = clean_title.strip() or ("Canlı Kripto Piyasa" if is_tr else "Live Crypto Market")
    variant = _crypto_variant_index(topic, variation_seed)
    has_gold = any(k in topic.lower() for k in ("gold", "altın", "altin"))
    has_banknifty = "banknifty" in topic.lower()

    if is_tr:
        gold_line = "Altın ve Bitcoin aynı ekranda şu an tamamen ayrı bir hikâye anlatıyor, dikkatli olun." if has_gold else "Bitcoin grafiği şu an piyasadaki tüm yönü tek başına belirliyor."
        bank_line = "Bank Nifty tarafında da volatilite tavan yaptı!" if has_banknifty else "Forex masalarında dolar endeksi tüm hesabı değiştiriyor!"
        narrations_variants = [
            [
                f"CANLI YAYIN! {topic} konusunda piyasalar şu an nefesini tutmuş durumda, her mum kritik! 📈🔴",
                "İlk bakışta Bitcoin tarafında satış baskısı belirgin şekilde artıyor ve hacim de yükseliyor. ⚡",
                gold_line + " Bu ayrışma kısa vadede fırsat ve riski aynı anda büyütüyor. 💰",
                "Kritik destek seviyesinin kırılması durumunda domino etkisi hızla başlayabilir, dikkatli olun. 🎯",
                "Balinaların cüzdan hareketleri son saatlerde ciddi şekilde arttı ve piyasa bunu fiyatlıyor. 🐋",
                bank_line + " Makro tarafta volatilite artınca kaldıraçlı işlemler daha da riskli hale geliyor. 🌏",
                "Makro veri takvimi bugün yatırımcıları iki yöne de zorlayabilir, pozisyon boyutunu küçültün. 📊",
                "Kaldıraçlı pozisyonlar likidasyon bölgesine çok daha yakın görünüyor, stop seviyelerini kontrol edin. ⚠️",
                "Teknik analistlere göre direnç testi başarısız olursa satış momentumu kısa sürede hızlanabilir. 📉",
                "Risk yönetimi olmayan trader bu volatilitede hesabını korumakta ciddi zorluk yaşar, plan şart. 🛡️",
                "Kısa vadeli scalp fırsatı var ama stop-loss koymadan işlem açmak bu piyasada affetmez. ⏱️",
                "Uzun vadeli yatırımcı için panik satış genelde en pahalı hatadır, seviye oyununu sabırla oynayın. 🧠",
                f"Özet: {topic} seansında ana tema volatilite, seviye oyunu ve disiplinli risk yönetimi. 🔥",
                "Sen bu grafikte long mu short mu kalırdın? Yorumlarda stratejini yaz, bir sonraki canlıda görüşürüz! 💬",
            ],
            [
                f"Flaş piyasa! {topic} canlı takipte — bir sonraki mum her şeyi değiştirebilir, hazır olun! 🚨",
                "Açılış mumu güçlü geldi ama üst fitil satıcı baskısını ele veriyor, trend henüz net değil. 🕯️",
                "Ethereum tarafı Bitcoin'e göre daha agresif hareket ediyor ve altcoin risk iştahını test ediyor. ⚡",
                gold_line + " Portföy dengesini bozan ani hareketlerde pozisyon küçültmek akıllıca olur. 🪙",
                "Haber akışı pozitif olsa bile fiyat tepki vermiyorsa piyasa zayıf kaldığını gösterir, dikkat! 📰",
                "Asya seansından gelen hacim Avrupa açılışına taşınıyor ve likidite profili değişiyor. 🌏",
                bank_line + " Dolar endeksi ve kripto korelasyonu bugün karar verici faktör olabilir. 📈",
                "Funding oranları aşırıya kaçtığında düzeltme ihtimali artar, aşırı kaldıraçtan kaçının. ⚖️",
                "Whale Alert tarafında borsaya büyük transfer geldi — fiyat aksiyonunu yakından izleyin! 🐋",
                "Stop avı sonrası ters hareket gelirse FOMO tuzağına düşme, planına sadık kal ve bekle. 🎯",
                "Günlük plan: seviye, hacim ve haber — duygusal tepki yok, disiplinli işlem yap. 📋",
                "Kripto piyasası yedi gün yirmi dört saat açık; uyku yok ama risk yönetimi disiplini şart. 🌙",
                f"Bugünkü {topic} özeti: trend mi yoksa tuzak mı sorusunun cevabı karar anına çok yakın. 🔥",
                "Long mu short mu? Cevabını yoruma bırak, bir sonraki canlı yayında birlikte okuyalım! 💬",
            ],
        ]
        narrations = narrations_variants[variant]
    else:
        narrations = [
            f"LIVE NOW! {topic} — markets are holding their breath at this level! 📈🔴",
            "Bitcoin is facing rising sell pressure while volume keeps climbing. ⚡",
            "Gold and Bitcoin are telling two different stories on the same screen! 💰" if has_gold else "Bitcoin is steering the entire risk market right now! 💰",
            "A break below key support could trigger a fast domino move. 🎯",
            "Whale wallet flows spiked hard in the last hour — watch closely. 🐋",
            "Bank Nifty volatility is spiking on the India desk!" if has_banknifty else "Forex desks are repricing the dollar index in real time. 🌏",
            "Today's macro calendar can push traders both ways within minutes. 📊",
            "Leveraged positions are sitting dangerously close to liquidation zones. ⚠️",
            "If resistance fails, analysts expect accelerated downside momentum. 📉",
            "Without risk management, this volatility will erase accounts fast. 🛡️",
            "Scalp setups exist, but only with strict stop-loss discipline. ⏱️",
            "For long-term holders, panic selling is usually the most expensive mistake. 🧠",
            f"Wrap-up for {topic}: volatility and level games dominate this session. 🔥",
            "Would you stay long or short here? Comment below and stay tuned! 💬",
        ]

    visuals = [
        ("Live crypto trading desk with multiple glowing charts and price tickers", ["live trading desk multiple monitors", "crypto trader workstation screens", "real time market dashboard"]),
        ("Bitcoin candlestick chart zoom with red and green volume bars pulsing", ["bitcoin candlestick chart closeup", "crypto price chart screen", "trading terminal bitcoin"]),
        ("Gold bullion bars beside digital bitcoin coin on dark finance desk", ["gold bullion trading desk", "bitcoin gold coin closeup", "precious metal crypto finance"]),
        ("Trader finger hovering over buy sell buttons during volatile market open", ["trader hands keyboard urgent", "stock market sell button closeup", "financial stress trading desk"]),
        ("Whale alert notification overlay on blockchain wallet transfer screen", ["crypto whale wallet transfer", "blockchain transaction alert screen", "large bitcoin movement chart"]),
        ("Forex and crypto split screen with dollar index and BTC price", ["forex trading screens split", "dollar index chart monitor", "multi asset trading desk"]),
        ("Economic calendar release countdown on professional trading workstation", ["economic calendar trading screen", "macro data release finance", "market news countdown monitor"]),
        ("Liquidation heatmap glowing red on crypto derivatives dashboard", ["crypto liquidation heatmap screen", "leverage trading risk dashboard", "futures market red zone"]),
        ("Technical analyst drawing support resistance lines on chart tablet", ["technical analysis chart lines", "support resistance trading screen", "financial analyst tablet chart"]),
        ("Risk management checklist sticky notes beside trading keyboard", ["risk management trading desk", "stop loss strategy notes", "disciplined trader workspace"]),
        ("Fast scalping chart with one minute candles and tight spreads", ["scalping chart one minute candles", "fast trading screen closeup", "day trader monitor action"]),
        ("Calm investor reviewing portfolio during market crash red screens", ["investor calm portfolio review", "long term crypto holder desk", "market crash screens background"]),
        ("Split montage of gold chart bitcoin chart and live stream overlay", ["gold chart bitcoin split screen", "live trading overlay finance", "multi chart market recap"]),
        ("Host looking at camera asking viewers to comment long or short", ["trader direct camera finance", "live stream outro subscribe", "crypto youtube shorts ending"]),
    ]

    moods = ["urgent", "dramatic", "energetic", "tense", "dark", "urgent", "calm", "dramatic", "energetic", "calm", "energetic", "calm", "epic", "bright"]
    scenes = []
    for i in range(14):
        desc, queries = visuals[i]
        scenes.append({
            "scene_number": i + 1,
            "narration": narrations[i],
            "scene_description": desc,
            "search_queries": queries,
            "duration": 3.0,
            "mood": moods[i],
            "beat_type": "hook" if i == 0 else "climax" if i == 7 else "resolution" if i == 13 else "conflict",
        })

    return {
        "title": topic if is_tr else f"Live Market: {topic}",
        "visual_theme": "live crypto finance trading urgent red green charts",
        "full_narration": " ".join(narrations),
        "scenes": scenes,
    }
