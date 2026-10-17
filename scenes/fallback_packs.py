"""
Niche-specific procedural fallback scene generators (Reddit, News, Stoic, Religious/Hadith,
Dark Psychology, Astrology, Crypto Market, Five Facts).
Extracted from scenes/fallback.py for modular maintainability.
"""
from typing import Dict, Any, List


def _generate_reddit_confession_scenes(clean_title: str, combined_text: str, is_tr: bool) -> Dict[str, Any]:
    """
    Dynamically constructs a high-retention viral story arc.
    Detects themes: Job Interview / Screen Share / WhatsApp Gossip, Wedding / Debt, Inheritance, Restaurant, General.
    """
    if any(k in combined_text for k in ["ekran", "whatsapp", "mülakat", "iş görüşmesi", "dedikodu", "patron"]):
        narrations_tr = [
            f"Bunu kimseye anlatamadım ama artık içimde tutamıyorum: {clean_title}.",
            "Haftalardır hayalini kurduğum o kritik mülakat toplantısı için bilgisayar başına geçmiştim. 💼✨",
            "Patron ve üst düzey yöneticiler tam karşımdaydı, benden hazırladığım projeyi sunmamı istediler. 🖥️👀",
            "Büyük bir heyecanla 'Ekranı Paylaş' butonuna bastığımda hangi pencerenin açık olduğunu tamamen unutmuştum. 😨🖱️",
            "Büyük ekranda beliren ilk şey, mesai arkadaşlarımla patron hakkında atıp tuttuğumuz o dedikodu grubuydu. 📱💥",
            "En üstte açıkça okunan mesajda: 'Patron yine saçmalıyor, bu adamla asla çalışılmaz' yazıyordu. 😱🔥",
            "Kamerada patronun yüz ifadesinin donup kaldığını ve gözlerini ekrandaki mesaja kilitlediğini gördüm. 🥶🧊",
            "Toplantıda tam on saniye süren, insanın iliklerine kadar işleyen bir ölüm sessizliği yaşandı. 🔇😵",
            "Titreyen ellerimle pencereyi kapatmaya çalıştım ama panikten fareyi bile doğru dürüst hareket ettiremedim. 😰💻",
            "Patron derin bir nefes alıp boğazını temizledi ve 'Bu gruptaki patron ben miyim?' diye sordu. 👔🎙️",
            "Yerin yedi kat dibine geçmiştim; tek kelime bile edemeden aniden 'Toplantıdan Ayrıl' butonuna bastım ve bilgisayarı kapattım. 🚪💨",
            "Şimdi telefonum susmuyor, gruptaki herkes ne olduğunu soruyor ve şirkette adım efsaneye dönüştü. 📳👀",
            "Kariyerimin muhtemelen en utanç verici ama bir ömür unutamayacağım en büyük dersini aldım. 🥀🤦‍♂️",
            "Peki siz benim yerimde olsaydınız kamerayı kapatıp kaçar mıydınız yoksa durumu toparlamaya mı çalışırdınız? Yorumlarda buluşalım! 🤔💬"
        ]
        narrations_en = [
            f"I couldn't tell this to anyone, but I can't keep it inside anymore: During a live job interview, I opened the WhatsApp group gossiping about the boss on screen. 😱📉",
            "I sat down at my desk for the dream job interview I had been preparing for weeks. 💼✨",
            "The executive director asked me to share my screen to present the project. 🖥️👀",
            "In a moment of pure excitement, I clicked 'Share Screen' completely forgetting what was open. 😨🖱️",
            "The first window that popped up on the live stream was our office WhatsApp gossip group. 📱💥",
            "The top message in bold letters read: 'The boss is talking nonsense again, nobody can work with this guy'. 😱🔥",
            "On the webcam, I watched the director's face freeze in complete shock and disbelief. 🥶🧊",
            "A ten-second dead silence followed, so intense you could hear a pin drop. 🔇😵",
            "With trembling hands, I desperately tried to close the window, but panic took over. 😰💻",
            "The director cleared his throat and asked on audio: 'Am I the boss you are referring to in that group?' 👔🎙️",
            "Mortified beyond words, I slammed the 'Leave Meeting' button and shut my laptop lid. 🚪💨",
            "Now my phone is blowing up with notifications from coworkers asking what happened. 📳👀",
            "It was without doubt the most humiliating moment of my career, but an unforgettable lesson. 🥀🤦‍♂️",
            "If you were in my shoes, would you have hung up and fled or tried to fix it? Let me know in the comments! 🤔💬"
        ]
        narrations = narrations_tr if is_tr else narrations_en
        visuals = [
            ("Anxious candidate sitting in front of glowing laptop webcam", ["job interview zoom call", "nervous applicant laptop", "interview webcam face"]),
            ("Professional resume and job preparation notes on modern desk", ["job interview preparation desk", "corporate office resume", "professional business meeting"]),
            ("Serious executive business managers on video conference screen", ["serious executive managers", "board meeting video conference", "corporate boss listening"]),
            ("Hand reaching for mouse clicking screen share button closeup", ["hand clicking mouse computer", "screen sharing button", "laptop keyboard closeup"]),
            ("Computer screen popping up open messaging chat window", ["screen sharing computer monitor", "whatsapp chat computer screen", "popup messaging window"]),
            ("Close-up of smartphone with open WhatsApp group chat messages", ["whatsapp chat smartphone screen", "group messaging text message", "office gossip phone"]),
            ("Shocked executive manager staring closely at computer screen", ["shocked manager face reaction", "executive squinting at screen", "disbelief corporate boss"]),
            ("Awkward frozen silence in online business video meeting", ["awkward silence online meeting", "frozen video call reaction", "uncomfortable business meeting"]),
            ("Trembling hands desperately trying to navigate computer mouse", ["hands shaking mouse panic", "nervous fingers keyboard", "panic error computer"]),
            ("Deep breathing corporate executive confronting on camera", ["executive stern face confrontation", "boss speaking serious camera", "tense meeting confrontation"]),
            ("Embarrassed person covering face in pure humiliation and shock", ["embarrassed person facepalm", "humiliated face laptop", "regret panic sitting desk"]),
            ("Finger slamming laptop screen shut abruptly in dark room", ["closing laptop screen sudden", "shutting laptop lid panic", "walking away computer desk"]),
            ("Smartphone vibrating continuously with flurry of incoming messages", ["phone buzzing with notifications", "text messages blowing up", "office drama smartphone"]),
            ("Engaging video outro inviting debate and audience reflection", ["dramatic reflective city dusk", "thoughtful person looking at skyline silhouette", "cinematic closing shot window light"])
        ]

    elif any(k in combined_text for k in ["düğün", "nikah", "eş", "borç", "kumar", "kredi"]):
        narrations_tr = [
            f"Bunu kimseye anlatamadım ama artık içimde tutamıyorum: {clean_title}.",
            "Her şey hayatımın en mutlu günü olması gereken o özel sabah başladı.",
            "Nikah törenine sadece birkaç saat kala telefonuma gelen gizli bir banka bildirimi tüm dengemi bozdu.",
            "Ortak birikimimizin tamamı çekilmiş ve adıma yarım milyon liralık gizli bir kredi kullanılmıştı.",
            "Gerçeği öğrendiğimde kanım dondu; kumar borcunu kapatmak için her şeyimi feda etmişlerdi.",
            "En güvendiğim insanın arkamdan böylesine acımasız bir komplo kurabileceğini asla düşünemezdim.",
            "Nikah masasına oturduğumda gözlerine baktım ve hiçbir pişmanlık kırıntısı göremedim.",
            "Memur 'Kabul ediyor musunuz?' diye sorduğunda salonda ölüm sessizliği oldu ve 'HAYIR' diye bağırdım.",
            "Masayı terk edip salonun kapısına doğru koşar adım yürürken tüm aile ayağa fırladı.",
            "Arkamdan bağırıp beni nankörlükle ve ortalığı rezil etmekle suçlamaya başladılar.",
            "Otelden çıkıp yağmurun altına adım attığımda hissettiğim tek şey derin bir özgürlüktü.",
            "Şimdi telefonlarım susmuyor, herkes beni bencil olmakla ve bir yuvayı yıkmakla suçluyor.",
            "Ama biliyorum ki bu yalana göz yumsaydım hayatımın en büyük felaketini yaşayacaktım.",
            "Peki siz olsaydınız bu durumda ne yapardınız? Yorumlarda buluşalım ve abone olmayı unutmayın!"
        ]
        visuals = [
            ("Dramatic slow motion wedding preparations with tense moody shadows", ["wedding preparation dramatic", "stressed bride silhouette", "wedding hall dark moody"]),
            ("Person looking in luxury mirror with anxious emotional expression", ["looking in mirror worried", "luxury wedding dress suit", "dramatic window shadow"]),
            ("Close-up of hands holding smartphone with bank alert notice", ["holding phone shock message", "bank notification document", "trembling hands dramatic"]),
            ("Shocked face reading confidential financial loan documents", ["secret financial document", "shocked face reading papers", "counting cash money dark"]),
            ("Underground casino roulette and dramatic dark smoky room", ["gambling casino dark table", "secret betrayal deception", "dramatic shadowy room"]),
            ("Silhouette of couple standing back to back in cold cinematic light", ["couple back to back silhouette", "broken trust sad emotion", "cold dramatic lighting"]),
            ("Bride and groom facing each other at grand wedding altar with intense tension", ["wedding altar couple tension", "tense confrontation dramatic", "bride groom dramatic"]),
            ("Shockwave moment at altar as wedding ceremony is abruptly interrupted", ["wedding ceremony interruption", "shocked wedding crowd", "dramatic refusal gesture"]),
            ("Person walking away from grand ballroom doors in slow motion", ["walking away dramatic exit", "running out ballroom doors", "lonely figure walking away"]),
            ("Angry family crowd gesturing and shouting in chaotic heated dispute", ["angry crowd arguing conflict", "family fight shouting", "chaotic confrontation room"]),
            ("Solitary figure walking under heavy rain on city street at dusk", ["person standing in rain", "walking in rain night city", "freedom dramatic rain"]),
            ("Smartphone buzzing continuously on dark table with hostile incoming texts", ["phone buzzing dark room", "stressful text messages", "contemplative silhouette window"]),
            ("Confident person standing tall against sunrise after surviving betrayal", ["confident person standing strong", "cinematic sunrise breakthrough", "resilient hero silhouette"]),
            ("Cinematic camera pull back inviting viewer debate and engagement", ["cinematic ending reflection", "social media engagement like", "dramatic silhouette sunset"])
        ]

    elif any(k in combined_text for k in ["miras", "evlat", "kardeş", "baba", "büyükbaba", "mülk"]):
        narrations_tr = [
            f"Bunu kimseye anlatamadım ama artık içimde tutamıyorum: {clean_title}.",
            "Yıllarca büyükbabama tek başıma baktım, diğerleri kapısını bile çalmadı.",
            "Vefatının ardından vasiyetname açıldığında evi bana bıraktığı ortaya çıktı.",
            "Yıllardır ortalıkta görünmeyen kardeşlerim aniden kapıma dayandı.",
            "Hasta kardeşimin tedavi masraflarını bahane ederek evin devrini talep ettiler.",
            "Araştırdığımda öyle bir tedavi olmadığını, parayı lüks tatile harcayacaklarını öğrendim.",
            "Tapuyu devretmeyeceğimi söylediğim an gözlerindeki o maske tamamen düştü.",
            "Beni hain ilan edip aile meclisinde evlatlıktan reddettiklerini haykırdılar.",
            "Kapıyı yüzlerine kapatıp yalnız kaldığımda vicdanımın tamamen rahat olduğunu anladım.",
            "Tüm akrabalar sosyal medyada aleyhime karalama kampanyası başlattı.",
            "Ama gerçek fedakarlığı yapan bendim ve onların açgözlülüğüne boyun eğmeyecektim.",
            "Hukuki yollara başvurup evden uzaklaştırma kararı aldırdım.",
            "Şimdi hayatıma huzurla devam ediyorum ve gerçek yüzleri gördüğüm için mutluyum.",
            "Siz olsaydınız ailenin baskısına boyun eğer miydiniz? Yorumlarda buluşalım!"
        ]
        visuals = [
            ("Old historic estate mansion surrounded by mist and mystery", ["old vintage mansion aerial", "mysterious luxury house", "foggy autumn estate"]),
            ("Caregiver holding elderly person hand in quiet room", ["caring hands comforting", "vintage bedroom cozy", "emotional support elderly"]),
            ("Notary reading wax-sealed will envelope on mahogany table", ["reading will testament", "notary documents legal", "vintage lawyer office"]),
            ("Angry people pounding on wooden door in aggressive confrontation", ["people knocking aggressive", "angry relatives confrontation", "front door tense"]),
            ("Medical documents and hospital bills spread across desk", ["hospital medical bills", "doctor office inspection", "financial paperwork desk"]),
            ("Shocking discovery of fake receipts under magnifying glass", ["magnifying glass evidence", "detective investigation paper", "discovering truth dark"]),
            ("Firm hands holding house deed keys refusing to hand over", ["holding house keys firm", "defending property home", "strong determined posture"]),
            ("Furious group shouting curses in grand family room", ["angry argument living room", "family shouting dispute", "toxic relatives conflict"]),
            ("Heavy wooden door closing firmly locking out toxic outsiders", ["door slamming shut", "locking front door safe", "peaceful solitude room"]),
            ("Social media notifications flooding smartphone screen in darkness", ["social media notifications", "phone dark screen glow", "cyber harassment stress"]),
            ("Person looking out grand window with peace and quiet confidence", ["person looking out window", "peace of mind sunrise", "serene calm atmosphere"]),
            ("Legal documents being stamped with official court justice seal", ["court justice gavel stamp", "legal protection lawyer", "official contract signed"]),
            ("Walking freely through lush estate garden in golden sunlight", ["walking sunny garden estate", "luxury modern home exterior", "bright future freedom"]),
            ("Thoughtful portrait looking at camera inviting discussion", ["contemplative thoughtful face", "questioning look camera", "subscribe follow dramatic"])
        ]

    elif any(k in combined_text for k in ["restoran", "hesap", "biftek", "garson", "yemek"]):
        narrations_tr = [
            f"Bunu kimseye anlatamadım ama artık içimde tutamıyorum: {clean_title}.",
            "Doğum günümde beni yemeğe davet eden 8 kişilik arkadaş grubumla toplandık.",
            "Kutlama için bir hediye dahi getirmedikleri gibi en pahalı biftekleri sipariş ettiler.",
            "Gece boyunca masada şampanyalar açıldı, herkes benim zengin olduğumu ima ediyordu.",
            "Garson yüklü hesabı doğrudan benim önüme bıraktığında herkes kafasını çevirdi.",
            "Bir anda hepsi cüzdanlarını unuttuklarını veya kartlarının limitinin bittiğini söyledi.",
            "O an beni arkadaş olarak değil, sadece bedava bir cüzdan olarak gördüklerini anladım.",
            "Sadece kendi yediğim salatanın ve suyun parasını masaya bırakıp ayağa kalktım.",
            "Masadan uzaklaşırken arkamdan gelen şaşkınlık ve öfke çığlıklarını duydum.",
            "Restoran çıkışında telefonum hakaret ve tehdit mesajlarıyla kilitlendi.",
            "Beni cimrilikle ve dostluğu mahvetmekle suçladılar ama sınırımı çizmiştim.",
            "O gece hepsini tek tek engelleyip hayatımdan tamamen çıkardım.",
            "Artık beni sömüren sahte insanlara değil, gerçek dostlara yer açtım.",
            "Siz olsaydınız o hesabı öder miydiniz? Fikrinizi yorumlarda paylaşın ve takipte kalın!"
        ]
        visuals = [
            ("Luxury fine dining restaurant with glowing chandeliers", ["luxury restaurant interior", "fine dining wine glasses", "charlie chandelier elegance"]),
            ("Group of smiling friends sitting around crowded dinner table", ["friends dinner party restaurant", "laughing friends dining", "group toast glasses"]),
            ("Waiter serving premium Tomahawk steaks with sizzling fire", ["steak gourmet meat plate", "expensive food dish serving", "luxurious dinner meal"]),
            ("Expensive champagne popping with sparkling bubbles", ["champagne bottle pop", "sparkling wine pour luxury", "vip party restaurant"]),
            ("Waiter placing massive leather bill folder onto white table cloth", ["restaurant bill check leather", "expensive invoice payment", "waiter handing bill"]),
            ("Shifty eyes looking away avoiding eye contact around table", ["nervous eye contact avoiding", "fake smile guilt face", "people whispering deceit"]),
            ("Cold realization of being exploited by supposed friends", ["shocked betrayal realization", "cold hard truth eyes", "disappointed person sitting"]),
            ("Hand placing exact cash note on table and pushing chair back", ["leaving cash on table", "standing up leaving chair", "firm decision gesture"]),
            ("Walking out past elegant restaurant hostess into night air", ["walking out restaurant doors", "leaving dinner dramatic", "night city street lights"]),
            ("Smartphone screen vibrating with barrage of angry WhatsApp texts", ["phone buzzing with texts", "angry text notifications", "harassment screen glare"]),
            ("Silhouette standing in cool night breeze feeling liberated", ["standing in night breeze", "freedom relief smile", "city night skyline view"]),
            ("Finger tapping 'Block Contact' on smartphone screen", ["blocking phone contact", "deleting social connection", "digital boundary firm"]),
            ("Walking forward alone under bright warm city streetlights", ["walking forward city lights", "confident stride night", "peaceful solitary path"]),
            ("Direct camera gaze asking viewer verdict and call to action", ["confident solitary person walking into city night", "cinematic dusk highway lights", "reflective quiet street lamppost"])
        ]

    else:
        narrations_tr = [
            f"Bunu kimseye anlatamadım ama artık içimde tutamıyorum: {clean_title}.",
            "Her şey sıradan görünen o günde başladı, ancak yaşadığım beklenmedik olay tüm dengemi bozdu.",
            "O an neye uğradığımı şaşırdım ve hissettiğim şüphe içimi kemirmeye başladı.",
            "Gerçeği öğrenmek için biraz araştırma yaptım ve karşılaştığım şey kanımı dondurdu.",
            "En yakınlarımdan birinin arkamdan böylesine bir oyun çevirdiğini hayal bile edemezdim.",
            "Elimdeki kanıtları toparlayıp sessizce doğru yüzleşme anını beklemeye başladım.",
            "Yüzleşme anı geldiğinde inkâr etmeye çalıştılar ama tüm kanıtlar ortadaydı.",
            "Maskeleri düştüğünde hissettiğim öfke yerini soğuk bir kararlılığa bıraktı.",
            "Tüm bağlarımı bir anda koparıp hayatımın en zor ama en doğru kararını verdim.",
            "Şimdi arkamdan konuşanlara ve beni suçlayanlara kulaklarımı tamamen tıkadım.",
            "İhaneti affetmek zayıflık, arkana bakmadan yürüyüp gitmek ise gerçek güçtür.",
            "Yalnız kalmaktan korkmadım ve kendi hayatımın kontrolünü elime aldım.",
            "Şimdi hayatımın en huzurlu dönemindeyim ve doğru olanı yaptığımı biliyorum.",
            "Siz olsaydınız bu durumda ne yapardınız? İnsan bazen en büyük kararları sessizce almak zorunda kalıyor."
        ]
        visuals = [
            ("Moody cinematic portrait in dark room with mysterious rim light", ["cinematic portrait moody dark", "mysterious person silhouette", "shadow dramatic face"]),
            ("Smartphone lighting up dark room with shocking notification", ["phone screen glow dark", "unexpected message alert", "reading notification bed"]),
            ("Pacing floor anxiety stress in dimly lit apartment", ["pacing floor anxiety stress", "nervous walking room", "restless night apartment"]),
            ("Hands searching through old files and envelopes finding secret", ["searching documents dark", "uncovering secret evidence", "investigative paperwork"]),
            ("Cold realization of betrayal reflected in shattering glass concept", ["shattering glass slow motion", "broken trust abstract", "dramatic shock expression"]),
            ("Collecting physical evidence taking photo with phone camera", ["taking photo evidence phone", "documenting proof detective", "secret investigation"]),
            ("Direct confrontation two people facing off in tense living room", ["intense confrontation room", "two people arguing serious", "tense eye contact dispute"]),
            ("False excuses falling apart in uncomfortable silence", ["guilty look caught lying", "uncomfortable silence tension", "defensive body language"]),
            ("Packing suitcase closing zip walking out front door", ["packing suitcase leaving", "zipping bag departure", "walking out door freedom"]),
            ("Walking down busy city avenue ignoring buzzing phone calls", ["ignoring phone walking city", "busy street silhouette stride", "focused confident walk"]),
            ("Standing on high rooftop overlooking panoramic city at sunset", ["rooftop sunset contemplation", "overlooking city skyline", "fresh air liberation"]),
            ("Self-reliance and strength concept glowing in golden dusk light", ["inner strength portrait", "confident solitary figure", "sunset dramatic golden hour"]),
            ("Peaceful morning coffee looking out at sunny horizon", ["peaceful morning coffee sun", "serene calm breakfast", "fresh new beginning smile"]),
            ("Cinematic outro scene asking viewer what they would do", ["youtube shorts interaction", "like and follow banner", "dramatic ending silhouette"])
        ]

    narrations = narrations_tr if is_tr else locals().get("narrations_en", narrations_tr)
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
            "mood": "mysterious" if i in (0, 2, 4) else "dramatic" if i in (1, 6) else "dark" if i in (3, 5) else "epic",
            "beat_type": "hook" if i == 0 else "climax" if i == 5 else "resolution" if i == len(selected_narrations) - 1 else "conflict",
        })

    return {
        "title": clean_title,
        "visual_theme": "dark emotional cinematic moody confession",
        "full_narration": " ".join(selected_narrations),
        "scenes": scenes,
        "niche_id": "2_reddit_confessions",
        "procedural_fallback": True,
    }


def _generate_news_flash_scenes(clean_title: str, is_tr: bool) -> Dict[str, Any]:
    """Constructs urgent breaking news format (Tone: urgent, factual, dramatic)."""
    narrations_tr = [
        f"SON DAKİKA! {clean_title} hakkında tüm dengeleri değiştiren kritik bir gelişme yaşandı!",
        "Gelen ilk sıcak bilgilere göre, olay yeri ve merkezden aktarılan veriler durumun ciddiyetini ortaya koyuyor.",
        "Yetkililer konunun önemine dikkat çekerek kamuoyuna ilk acil durum açıklamasını yaptı.",
        "Olayın arka planı incelendiğinde, bu sürecin aslında çok daha derin sebeplere dayandığı anlaşılıyor.",
        "Uzman analistler ve stratejistler gelişmenin oluşturacağı etki alanını anbean mercek altına aldı.",
        "Kritik veriler ve raporlar açıklandıkça şaşırtıcı detaylar tek tek gün yüzüne çıkıyor.",
        "Piyasalarda ve kamuoyunda ardı ardına gelen ilk tepkiler gündemin zirvesine oturdu.",
        "Merkezden alınan kararlar doğrultusunda acil eylem planı derhal devreye sokuldu.",
        "Olayın doğrudan etkilediği sektörler ve kurumlar kriz masasında değerlendiriliyor.",
        "Uluslararası basında ve yerel kaynaklarda yankı uyandıran haber geniş kitlelerce tartışılıyor.",
        "Soru işaretlerinin giderilmesi ve netleşmesi için derinlemesine soruşturmalar sürüyor.",
        "Önümüzdeki saatlerde konuya ilişkin yeni resmi açıklamaların yapılması bekleniyor.",
        "Tüm bu tablo, yakın gelecekte radikal değişikliklerin kapıda olduğunu gösteriyor.",
        "Peki siz bu flaş gelişme hakkında ne düşünüyorsunuz? Yorumlarda buluşalım ve takipte kalın!"
    ]
    narrations_en = [
        f"BREAKING NEWS! A major critical development has just unfolded regarding {clean_title}!",
        "According to initial incoming reports, real-time data from the ground reveals the urgency of the situation.",
        "Authorities have issued an urgent initial public statement highlighting the gravity of the event.",
        "A closer look at the background reveals that this crisis is rooted in far deeper underlying factors.",
        "Leading analysts and strategic experts are closely monitoring the potential ripple effects in real time.",
        "As confidential reports and data are released, astonishing new details are coming to light one by one.",
        "Initial reactions across markets and the public have rapidly surged to the top of global headlines.",
        "Government leadership has officially activated an emergency crisis response plan to contain the fallout.",
        "Directly impacted sectors and vital institutions are currently meeting in high-level emergency sessions.",
        "The story is sparking widespread debate across major international media outlets and digital channels.",
        "Thorough investigations remain underway to answer lingering questions and uncover full accountability.",
        "Official spokespeople are expected to deliver a comprehensive follow-up press conference within hours.",
        "All indicators point toward radical policy shifts and structural changes on the immediate horizon.",
        "What is your take on this breaking news story? Let us know in the comments and stay tuned for live updates!"
    ]
    narrations = narrations_tr if is_tr else narrations_en
    visuals = [
        ("Breaking news television broadcast studio with glowing red graphics", ["breaking news broadcast studio", "news anchor television desk", "urgent broadcast alert"]),
        ("Press conference podium with microphone array and flash photography", ["press conference microphone", "journalists camera flashes", "official statement podium"]),
        ("Emergency government authority building exterior at dusk", ["government building exterior", "official headquarters night", "city emergency lights"]),
        ("Financial charts and data analytics screens updating rapidly", ["financial data screen urgent", "stock market chart volatility", "digital data analytics"]),
        ("Expert analyst in modern broadcast studio speaking directly to camera", ["expert analyst television", "broadcast studio interview", "serious political analyst"]),
        ("Confidential official documents and classified stamp paperwork", ["classified documents report", "investigative paperwork desk", "urgent official decree"]),
        ("Busy financial stock exchange floor with energetic trading action", ["stock exchange floor busy", "financial traders shouting", "world market exchange"]),
        ("Emergency command center with multiple monitors and tactical map", ["emergency command center", "crisis management room", "satellite tracking monitors"]),
        ("City skyline with busy traffic and dramatic rolling storm clouds", ["city skyline storm clouds", "traffic time lapse urban", "metropolis aerial dramatic"]),
        ("Global newspaper headlines spinning and digital press coverage", ["newspaper press printing", "digital media news feed", "global headline broadcast"]),
        ("Police investigation line and security detail perimeter cordons", ["investigation security perimeter", "official investigation team", "forensic inspection scene"]),
        ("Live television broadcasting satellite van on location", ["broadcast satellite truck", "live reporting camera van", "media journalists crowd"]),
        ("Dramatic sunset horizon casting long shadows over modern city", ["dramatic sunset horizon city", "urban skyline sunset golden", "cinematic future horizon"]),
        ("YouTube shorts ending screen with reflective conclusion", ["broadcast television control room monitors dimming", "journalists leaving busy newsroom dusk", "cinematic evening cityscape news tower"])
    ]
    selected_indices = [0, 1, 2, 3, 4, 6, 7, 8, 11, 12] if len(narrations) >= 14 else list(range(min(10, len(narrations))))
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
            "mood": "dramatic" if i in (0, 1, 2, 6) else "energetic" if i in (3, 4) else "mysterious" if i in (5, 7) else "epic",
            "beat_type": "hook" if i == 0 else "climax" if i == 5 else "resolution" if i == len(selected_narrations) - 1 else "conflict",
        })
    return {
        "title": clean_title if is_tr else f"Breaking News: {clean_title}",
        "visual_theme": "breaking news broadcast red amber dramatic studio",
        "full_narration": " ".join(selected_narrations),
        "scenes": scenes,
        "niche_id": "1_news_flash",
        "procedural_fallback": True,
    }


def _stoic_variant_index(clean_title: str, variation_seed: int = 0) -> int:
    base = sum(ord(c) for c in clean_title.lower()) + (variation_seed * 17)
    return base % 4


def _build_stoic_narrations(clean_title: str, is_tr: bool, variation_seed: int = 0) -> List[str]:
    """Topic-seeded Stoic narrations."""
    topic = clean_title.strip() or ("Stoacılık" if is_tr else "Stoicism")
    variant = _stoic_variant_index(topic, variation_seed)

    if is_tr:
        variants = [
            [
                f"{topic} konusu gündeme geldiğinde çoğu kişi anlık motivasyon arar; oysa Stoacılar zihinsel bir disiplin inşa eder.",
                "Marcus Aurelius Meditations'ta şunu yazar: Karşılaştığın dış olaylar seni belirlemez, onlara verdiğin tepki belirler.",
                "Kontrol edemediğin haberler, gürültü ve başkalarının öfkesi senin huzurunu çalmak zorunda değil.",
                "Seneca'nın dediği gibi: Bizler gerçek hayattan çok, zihnimizde kurduğumuz felaket senaryolarında acı çekeriz.",
                "Öfkeyi bir silah sanırsın ama o elinde tuttuğun kor ateştir; önce senin elini yakar.",
                "Bugün seni sarsan bir gerilim olduğunda nefes al; tepki vermeden önce üç saniye dur.",
                "Epiktetos şunu hatırlatır: 'Seni inciten olayların kendisi değil, o olaylara yüklediğin anlamdır.'",
                "İki bin yıllık felsefe şunu öğretir: Karşılaştığın bu zorluklar senin kontrol alanın olmayabilir; fakat duruşun tamamen senin elindedir.",
                "Güne başlarken şunu hatırla: Bugün zor insanlar, belirsizlik ve kaosla karşılaşabilirsin.",
                "Onların davranışı senin değerini değil; senin sabrını test eden bir zihinsel antrenmandır.",
                "Gerçek disiplin, iyi hissettiğinde değil; en çok dağılmak istediğinde doğru olanı seçmektir.",
                "Kriz anında panik yerine prosedür seç: Ne biliyorum, neyi değiştirebilirim, neyi serbest bırakmalıyım?",
                "Zihnini eğitmezsen, algoritmalar ve kaos senin yerine karar vermeye başlar.",
                "Kendi zihnini korumayı seçtiğinde, dışarıdaki hiçbir fırtına senin iç huzurunu ve merkezini sarsamaz.",
            ],
            [
                f"Çoğu insan {topic} karşısında hemen bir mucize bekler; bilge insan ise önce sınırını çizer.",
                "Marcus Aurelius: 'Gününün huzurunu, başkalarının hatasıyla zehirleme.'",
                "Seni endişelendiren şeyleri ikiye ayır: Kontrol edebildiklerim ve kontrolüm dışındakiler.",
                "Kontrol edemediklerin için harcadığın her dakika, kendi hayatından çaldığın bir andır.",
                "Seneca: 'Mutluluk dışarıda aranan bir ödül değil; içeride inşa edilen sessiz bir alışkanlıktır.'",
                "Stres ve baskı anında nefesini yavaşlat, omuzlarını gevşet ve zihnini ana sabitle.",
                "Epiktetos'un temel kuralı çok net: Ya eyleme geç ve çöz, ya da kabul edip serbest bırak.",
                "Antik Roma'da imparatorlar bile en büyük krizlerde önce sükûneti korumayı antrenman sayardı.",
                "Gürültülü bir dünyada sessizlik bir lüks değil; zihinsel bir savunma hattıdır.",
                "Korkularını büyüten şey gerçekler değil, zihninin ürettiği abartılı varsayımlardır.",
                "Disiplin zihnin kası gibidir: Her sakin kaldığın an, seni bir sonraki fırtınaya hazırlar.",
                "Zorluklar seni yıkmak için gelmez; ne kadar sağlam durabildiğini sana göstermek için gelir.",
                "Bugün kendine bir söz ver: Panik ve acele yok, sadece net ve soğukkanlı adımlar var.",
                "Unutma: Dünya senin kontrolünde değil, ama duruşun tamamen senin elinde.",
            ],
            [
                f"{topic} konusu etrafta bir fırtına koparabilir; fakat stoacı bir zihin kalıcı olanı seçer.",
                "Marcus Aurelius sabahları kendine sorardı: Bugün hangi zayıf tepkilerimi dizginlemeliyim?",
                "Öfke ve sabırsızlık hissettiğinde önce bedenini dinle: Çenen, nefesin ve kalp atışın.",
                "Dış dünya aniden değişmez; değişebilecek tek şey senin olaylara verdiğin anlamdır.",
                "Seneca der ki: 'Bazen ruhunu iyileştirmek için tartışmayı bırakıp sessizce uzaklaşmak gerekir.'",
                "Her kavgaya girmek zorunda değilsin; susup odağını korumak da stratejik bir güçtür.",
                "Epiktetos: 'İnsanları değiştirmeye çalışma; sadece kendi zihnini ve tepkilerini eğit.'",
                "Kadim bilgelik sihirli reçeteler sunmaz; sadece sarsılmaz bir irade ve alışkanlık kazandırır.",
                "Her gün kendine birkaç dakika ayır: Neyi kabul ediyorum, neye sınır çiziyorum?",
                "Başkalarının yarattığı kaos senin acil durumun olmak zorunda değildir.",
                "Duygularını bastırmak değil, onları bilinçle yönetip sakin bir güce dönüştürmek gerekir.",
                "Günün krizleri gelir ve geçer; fakat sergiledğin karakter hayat boyu seninle kalır.",
                "Kendi zihnini koru — çünkü hayatının gerçek komuta merkezi orasıdır.",
                "Fırtına dindiğinde geriye kalan, en çok sabır ve disiplin gösteren insan olacaktır.",
            ],
            [
                f"{topic} gibi belirsizlikler zihnini tehdit moduna sokabilir; Stoacılık ise güvenli bir kale inşa eder.",
                "Marcus Aurelius'un dediği gibi: 'Yolun önündeki engel, artık yolun kendisi olur.'",
                "Eğer geceleri zihnini kurcalayan bir sorun varsa, ilk adım soğukkanlı bir eylem planıdır.",
                "Endişe sadece çözümsüz varsayımların hayalidir; net bir eylem ise endişenin tek panzehiridir.",
                "Seneca uyarır: 'Zamanımız aslında az değil; biz onu gereksiz kaygılarla israf ediyoruz.'",
                "Tüketen kaygılara harcadığın enerjiyi, bugün atabileceğin tek bir somut adıma çevir.",
                "Epiktetos: 'Gerçek özgürlük dış koşullara değil, kendi iç kararlarına bağlıdır.'",
                "Felsefe sana hayatın tüm sorularının cevabını vermez; o sorular karşısında nasıl duracağını öğretir.",
                "Sabah rutinine sadık kal: Derin bir nefes, net bir niyet ve sakin bir zihin.",
                "Başkalarının beklentileri senin prangan olmak zorunda değil; kendi ahlaki pusulan tek rehberindir.",
                "Motivasyon bittiğinde bile devam etmeni sağlayan tek güç sistemli disiplindir.",
                "Fırtına dindiğinde ayakta kalanlar, kriz anında zihnine hâkim olmayı başaranlardır.",
                "Zihnini eğit; yoksa çevrendeki gürültü senin kaderini belirler.",
                "Bugün vereceğin soğukkanlı bir tepki, gelecekteki karakterinin temel taşıdır.",
            ],
        ]
        return variants[variant]

    en_variants = [
        [
            f"When people talk about {topic}, they often seek motivation — Stoics build quiet mental discipline.",
            "Marcus Aurelius wrote: External events cannot touch the soul; only your reaction defines you.",
            "Other people's chaos and anger are not an excuse to surrender your peace of mind.",
            "Seneca warned that we suffer far more in imagination than in reality.",
            "Anger feels like a weapon, but it is a burning coal that scorches your own hand first.",
            "If tension rises today, pause three seconds before speaking or reacting.",
            "Epictetus reminds us: You are disturbed not by things, but by the view you take of them.",
            f"Two thousand years of philosophy teach this: {topic} may be beyond your control, but your attitude is yours.",
            "Each morning expect noise, rude behavior, and unforeseen obstacles.",
            "Their conduct tests your patience — it does not define your character.",
            "Discipline is choosing what is right precisely when you least feel like doing it.",
            "In moments of crisis, trade panic for clarity: What do I know, what can I change, what must I release?",
            "Train your mind every single day, or the noise of the world will run it for you.",
            "When you master your inner state, no storm outside can shake your center.",
        ],
        [
            f"Most people panic when facing {topic}; the wise person draws boundaries first.",
            "Marcus Aurelius: Do not poison your own day with someone else's mistake.",
            "Divide everything in front of you: What you can control versus what you cannot.",
            "Every minute wasted on things outside your power is stolen from your real life.",
            "Seneca: Happiness is a habit cultivated within, not a trophy chased outside.",
            "Under stress, drop your shoulders, steady your breathing, and root yourself in the present.",
            "Epictetus: Either take purposeful action, or let it go with total peace.",
            "Even Roman emperors treated sudden crises as training for inner poise.",
            "In a frantic world, silence is not hesitation — it is deliberate mental defense.",
            "Fear grows from unexamined assumptions, not from cold facts.",
            "Discipline is steady repetition preparing you for the next inevitable storm.",
            "Adversity does not come to destroy you; it comes to reveal what you are made of.",
            "Make a clear pact today: No unnecessary panic, only deliberate steps forward.",
            "The world is not in your control, but your character belongs entirely to you.",
        ],
        [
            f"Topics like {topic} may stir up storms, but a Stoic mind stays anchored in what endures.",
            "Marcus Aurelius asked each morning: Which weak impulses must I guard against today?",
            "When irritation surfaces, check your body: Your jaw, your breathing, your pulse.",
            "The external world cannot be controlled on command; only your interpretation can.",
            "Seneca: Sometimes true strength is simply refusing to participate in the drama.",
            "You do not owe every argument your voice — silence is often the sharpest strategy.",
            "Epictetus: Stop trying to fix everyone else; discipline your own mind first.",
            "Ancient wisdom offers no shortcuts, only rock-solid mental habits.",
            "Take two minutes every morning: What do I accept today, and where do I draw the line?",
            "Another person's emergency is not your obligation to become uncentered.",
            "Discipline is not about suppressing feelings, but directing them with purpose.",
            "The drama of the day will fade, but the character you show stays with you.",
            "Protect your own mind — it is the only true fortress you will ever own.",
            "When the noise subsides, the person who kept their head will be the one still standing.",
        ],
        [
            f"Uncertainty around {topic} triggers instinctual fear; Stoicism builds unwavering confidence.",
            "Marcus Aurelius: What stands in the way becomes the way forward.",
            "If worry keeps you restless, your immediate remedy is an actionable checklist.",
            "Anxiety thrives on imagined problems; concrete action is its only true antidote.",
            "Seneca reminds us: Life is not short, but we make it short by wasting our focus.",
            "Channel the nervous energy of worry into a single constructive task.",
            "Epictetus: Freedom belongs to those who govern their own impulses.",
            "Philosophy does not solve all life's puzzles; it teaches you how to stand tall through them.",
            "Ground your mornings in simple clarity: Deep breath, clear purpose, steady resolve.",
            "Other people's demands do not define your worth; your moral compass does.",
            "When motivation runs dry, quiet consistency is what carries you across.",
            "Whoever practices calm in small moments will stand unshakable in great trials.",
            "Master your thoughts today, or the noise of tomorrow will decide for you.",
            "A single composed response today shapes the strength of your future self.",
        ],
    ]
    return en_variants[variant]


def _generate_stoic_scenes(clean_title: str, is_tr: bool, variation_seed: int = 0) -> Dict[str, Any]:
    """Constructs 10-scene Stoic philosophy format."""
    all_narrations = _build_stoic_narrations(clean_title, is_tr, variation_seed)
    visuals = [
        ("Ancient marble statue of Marcus Aurelius under dramatic side lighting", ["marcus aurelius marble statue", "ancient roman bust sculpture", "stoic statue dramatic lighting"]),
        ("Ancient Roman Colosseum at sunset with dramatic sun rays", ["rome colosseum sunset drone", "ancient roman ruins colosseum", "epic golden sunset rome"]),
        ("Chaotic crowd walking fast in modern metropolis contrasting calm observer", ["busy crowd metropolis blur", "calm person standing crowd", "solitary figure city"]),
        ("Close-up of calm stoic facial expression looking outward in thought", ["calm face meditation eyes", "disciplined man looking distance", "thoughtful philosopher portrait"]),
        ("Ancient scroll and ink quill resting on heavy weathered stone table", ["ancient parchment manuscript", "quill ink stone desk", "vintage philosophical writing"]),
        ("Glowing fiery embers in darkness symbolizing burning anger", ["burning embers fire dark", "fiery sparks slow motion", "flames fireplace dramatic"]),
        ("Solitary marble pillar standing tall amidst ancient ruined temple", ["ancient marble pillar ruins", "greek roman temple standing", "resilient stone architecture"]),
        ("Deep clear mountain lake with mirror-like undisturbed reflection", ["serene mountain lake mirror", "calm still water reflection", "peaceful nature tranquility"]),
        ("Silhouette standing on mountain cliff overlooking infinite clouds", ["silhouette cliff clouds view", "master of mind mountain", "epic panorama contemplation"]),
        ("Direct gaze to camera with thoughtful stoic nod inviting reflection", ["stoic philosopher direct gaze", "dramatic camera pull back", "subscribe follow philosophy"])
    ]
    selected_indices = [0, 1, 2, 3, 4, 5, 7, 8, 12, 13] if len(all_narrations) >= 14 else list(range(min(10, len(all_narrations))))
    narrations = [all_narrations[idx] for idx in selected_indices]

    scenes = []
    for i in range(len(narrations)):
        desc, queries = visuals[i % len(visuals)]
        scenes.append({
            "scene_number": i + 1,
            "narration": narrations[i],
            "scene_description": desc,
            "search_queries": queries,
            "duration": 5.2,
            "mood": "calm" if i in (1, 3, 7) else "epic" if i in (0, 8) else "dramatic"
        })
    return {
        "title": clean_title if is_tr else f"Stoic Wisdom: {clean_title}",
        "visual_theme": "ancient stoic marble roman gold dramatic highlights",
        "full_narration": " ".join(narrations),
        "scenes": scenes
    }


from .fallback_packs_ext import (
    _crypto_variant_index,
    _generate_astrology_horoscope_scenes,
    _generate_crypto_market_scenes,
    _generate_dark_psychology_scenes,
    _generate_religious_quotes_scenes,
)


def _generate_five_fact_scenes(clean_title: str, is_tr: bool, variation_seed: int = 0) -> Dict[str, Any]:
    """Five spoken facts. No title paste, no scroll warning, no fake quote."""
    topic = (clean_title or "").strip() or "5 gerçek"
    if is_tr:
        beats = [
            ("Beş ölçülmüş gerçek. Ders kitabı bunları çoğu zaman tek cümleyle geçirir.", "open textbook classroom desk", ["open textbook classroom", "library study desk", "students classroom"]),
            ("Su, dört santigrat derecede en yoğundur. Sıfırda buz genleşir ve gölün üstünde kalır. Alttaki su dört derecede kalır, balık donmaz.", "frozen lake iceberg winter", ["frozen lake ice", "iceberg floating water", "winter lake close up"]),
            ("Yetişkin insanda yaklaşık iki yüz altı kemik vardır. Sınıftaki iskelet modelinde bunu sayabilirsin. Bebekte sayı üç yüze yakındır, sonra bir kısmı kaynar.", "classroom skeleton model", ["classroom skeleton model", "human skeleton classroom", "anatomy model classroom"]),
            ("Arı balı kapalı kavanozda yıllarca bozulmaz. İçindeki su çok azdır ve asittir. Bu ortamda bakteri üreyemez.", "honey jar bees flowers", ["honey jar close up", "bee on flower", "honey drip spoon"]),
            ("Soluduğun oksijenin büyük kısmını okyanus planktonu üretir. Orman tek kaynak değildir. Deniz yüzeyi bu yüzden önemlidir.", "ocean waves surface plankton", ["ocean waves surface", "underwater deep sea", "sea surface aerial"]),
            ("Yıldırım aynı noktaya birden fazla kez düşebilir. Şimşek yüksek ve metal uçları tekrar hedefler. Bir kez düştü diye o yer güvenli sayılmaz.", "storm lightning strike night", ["storm lightning", "lightning strike tower", "thunder storm sky"]),
        ]
    else:
        beats = [
            ("Five measured facts. A textbook usually spends one sentence on each.", "open textbook classroom desk", ["open textbook classroom", "library study desk", "students classroom"]),
            ("Water is densest at four degrees Celsius. Ice floats, so the fish below the lake do not freeze.", "frozen lake iceberg winter", ["frozen lake ice", "iceberg floating water", "winter lake close up"]),
            ("An adult has about two hundred six bones. A newborn has closer to three hundred. Some fuse as you grow.", "classroom skeleton model", ["classroom skeleton model", "human skeleton classroom", "anatomy model classroom"]),
            ("Sealed honey can last for years. It holds very little water and it is acidic, so bacteria cannot grow.", "honey jar bees flowers", ["honey jar close up", "bee on flower", "honey drip spoon"]),
            ("Most of the oxygen you breathe comes from ocean plankton. Forests are not the only source.", "ocean waves surface plankton", ["ocean waves surface", "underwater deep sea", "sea surface aerial"]),
            ("Lightning can strike the same spot more than once. A tall metal point stays a target.", "storm lightning strike night", ["storm lightning", "lightning strike tower", "thunder storm sky"]),
        ]
    if len(beats) > 2 and variation_seed:
        fact_beats = beats[1:]
        shift = variation_seed % len(fact_beats)
        beats = [beats[0], *fact_beats[shift:], *fact_beats[:shift]]

    scenes = []
    for i, (narr, desc, queries) in enumerate(beats):
        scenes.append({
            "scene_number": i + 1,
            "narration": narr,
            "scene_description": desc,
            "search_queries": queries,
            "duration": 6.0 if i else 4.0,
            "mood": "curious",
            "beat_type": "hook" if i == 0 else "resolution" if i == len(beats) - 1 else "conflict",
        })
    return {
        "title": topic,
        "visual_theme": "classroom science facts",
        "full_narration": " ".join(b[0] for b in beats),
        "scenes": scenes,
        "niche_id": "9_five_facts",
        "procedural_fallback": True,
        "scenario_pack_family": "quiz",
    }

