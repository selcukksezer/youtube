"""
Procedural and rule-based fallback scene generator when AI quotas or APIs are unavailable.
Supports dynamic context-aware Reddit story rewriting, breaking news, stoicism, dark psychology,
and pure English stock query synthesis tailored to all 35 niches.
"""

import re
import config


TR_EN_TOPIC_MAP = {
    "düğün": "wedding bride altar", "evlilik": "wedding marriage", "eş": "couple spouse betrayal",
    "borç": "secret debt money", "para": "cash money bank", "kredi": "bank loan debt documents",
    "kumar": "gambling casino debt", "miras": "inheritance estate conflict", "ev": "house luxury property",
    "kardeş": "siblings family conflict", "aile": "family dispute arguing", "hasta": "hospital medical patient",
    "restoran": "restaurant dinner table", "hesap": "bill invoice money cash", "arkadaş": "fake friends dinner",
    "patron": "office boss executive", "şirket": "corporate office workplace", "iş": "typing laptop computer",
    "mülakat": "job interview candidate", "ekran": "computer screen monitor", "whatsapp": "whatsapp chat messaging phone",
    "dedikodu": "office gossip whispering", "yayın": "live video stream broadcast",
    "yapay zeka": "artificial intelligence futuristic", "bot": "coding software screen",
    "aldat": "cheating partner betrayal", "sevgili": "couple argument breakup", "nişanlı": "fiancé deception secret",
    "dolandırıcı": "scammer crime investigation", "yalan": "lies secret betrayal",
    "felsefe": "stoic statue marble philosophy", "roma": "ancient rome ruins colosseum",
    "psikoloji": "human psychology mind brain", "bilim": "science laboratory discovery",
    "uzay": "space galaxy universe stars", "motivasyon": "workout fitness athlete",
    "haber": "breaking news broadcast studio", "kripto": "bitcoin crypto trading chart",
    "tarih": "ancient historical battlefield", "ürün": "viral smart gadget lifestyle"
}


def _detect_niche_and_terms(title: str, body: str = ""):
    clean_title = re.sub(r'[^\w\s-]', '', title).strip()
    words = [w for w in clean_title.split() if len(w) > 2]
    combined_text = f"{title} {body}".lower()

    matched_en = []
    for tr_k, en_v in TR_EN_TOPIC_MAP.items():
        if tr_k in combined_text:
            matched_en.append(en_v)

    if matched_en:
        main_kw = matched_en[0]
    else:
        main_kw = "dramatic cinematic mystery"

    return clean_title, main_kw, words, matched_en


def _generate_reddit_confession_scenes(clean_title: str, combined_text: str, is_tr: bool):
    """
    Dynamically constructs a 14-scene high-retention viral story arc (Cadence 14, ~42 seconds).
    Detects themes: Job Interview / Screen Share / WhatsApp Gossip, Wedding / Debt, Inheritance, Restaurant, Workplace Bot.
    """
    # 1. Job Interview / Screen Sharing / WhatsApp Gossip Theme
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
            ("Engaging video outro inviting debate and audience comments", ["youtube shorts interaction ending", "like comment subscribe banner", "dramatic sunset silhouette"])
        ]

    # 2. Wedding & Secret Debt Theme
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

    # 3. Inheritance & Family Greed Theme
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

    # 4. Restaurant Bill & Fake Friends Theme
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
            ("Direct camera gaze asking viewer verdict and call to action", ["direct camera engagement", "youtube shorts ending card", "like comment subscribe"])
        ]

    # 5. General viral confession
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
            "Siz olsaydınız bu durumda ne yapardınız? Yorumlarda buluşalım ve abone olmayı unutmayın!"
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

    scenes = []
    for i in range(14):
        desc, queries = visuals[i]
        scenes.append({
            "scene_number": i + 1,
            "narration": narrations_tr[i],
            "scene_description": desc,
            "search_queries": queries,
            "duration": 3.0,
            "mood": "mysterious" if i in (0, 2, 4) else "dramatic" if i in (1, 6, 7, 9) else "dark" if i in (3, 5, 8) else "bright" if i in (10, 11, 12) else "epic"
        })

    return {
        "title": clean_title,
        "visual_theme": "dark emotional cinematic moody confession",
        "full_narration": " ".join(narrations_tr),
        "scenes": scenes
    }


def _generate_news_flash_scenes(clean_title: str, is_tr: bool):
    """
    Constructs 14-scene urgent breaking news format (Tone: urgent, factual, dramatic).
    """
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
        ("YouTube shorts ending screen with subscribe button and debate call", ["news channel outro banner", "subscribe bell follow icon", "breaking news closing"])
    ]
    scenes = []
    for i in range(14):
        desc, queries = visuals[i]
        scenes.append({
            "scene_number": i + 1,
            "narration": narrations[i],
            "scene_description": desc,
            "search_queries": queries,
            "duration": 3.0,
            "mood": "dramatic" if i in (0, 1, 2, 6, 7) else "energetic" if i in (3, 4, 8) else "mysterious" if i in (5, 9, 10) else "epic"
        })
    return {
        "title": clean_title if is_tr else f"Breaking News: {clean_title}",
        "visual_theme": "breaking news broadcast red amber dramatic studio",
        "full_narration": " ".join(narrations),
        "scenes": scenes
    }


def _generate_stoic_scenes(clean_title: str, is_tr: bool):
    """
    Constructs 14-scene Stoic philosophy format (Tone: deep, calm, disciplined, masculine).
    """
    narrations_tr = [
        f"{clean_title} karşısında zihnini sarsılmaz bir kaleye dönüştürecek Stoacı bilgelik...",
        "Marcus Aurelius yüzyıllar önce şunu yazmıştı: 'Başına gelenleri değil, onlara verdiğin tepkiyi kontrol edebilirsin.'",
        "İnsanların çoğu dış dünyadaki kaosa öfkelenerek kendi huzurunu kendi elleriyle yok eder.",
        "Oysa bilge bir insan, kontrol edemediği hiçbir şey için bir saniye bile kaygılanmaz.",
        "Seneca'nın dediği gibi: 'Gerçekte başımıza gelen felaketlerden çok, zihnimizde yarattığımız korkular yüzünden acı çekeriz.'",
        "Öfke, bir başkasına fırlatmak için eline aldığın kor bir ateştir; ilk önce senin elini yakar.",
        "Zihninde her sabah şu gerçeği kabul et: Bugün nankör, kaba ve açgözlü insanlarla karşılaşacaksın.",
        "Ama onların kusurları seni zehirleyemez; çünkü sen onlara benzememeyi seçtin.",
        "Epiktetos bize hatırlatır: 'Seni yaralayan söylenen sözler değil, o sözlere yüklediğin anlamdır.'",
        "Hayatın fırtınaları seni sarsabilir ama kökleri derin olan bir çınarı hiçbir rüzgar deviremez.",
        "Disiplin, hissettiğin duyguların kölesi olmak yerine eylemlerinin efendisi olmaktır.",
        "Zorluklar bir engel değil; bilakis seni çelikleştiren birer antrenmandır.",
        "Zihnini kontrol et, yoksa zihnin seni ve kaderini kontrol eder.",
        "Peki sen bugün öfkeni mi seçeceksin, yoksa içsel huzurunu mu? Yorumlarda buluşalım!"
    ]
    narrations_en = [
        f"Ancient Stoic wisdom to transform your mind into an invincible fortress against {clean_title}...",
        "Marcus Aurelius wrote centuries ago: 'You have power over your mind, not outside events. Realize this, and you will find strength.'",
        "Most people destroy their own peace of mind by reacting with outrage to the chaos of the outside world.",
        "Yet a truly wise individual never wastes a single second worrying about what lies beyond their control.",
        "As Seneca famously remarked: 'We suffer more often in imagination than in reality.'",
        "Anger is like a burning coal you pick up to throw at someone else; it always burns your own hand first.",
        "Remind yourself every single morning: today you will encounter rude, ungrateful, and arrogant people.",
        "Their flaws cannot harm you, because you have made the conscious choice not to become like them.",
        "Epictetus teaches us: 'Men are disturbed not by things, but by the view which they take of them.'",
        "The storms of life may shake your branches, but no wind can uproot a tree whose roots run deep into virtue.",
        "Discipline is never being the slave of your temporary emotions, but the absolute master of your deliberate actions.",
        "Adversity is not an obstacle; it is the fiery forge that shapes unyielding character and inner strength.",
        "Rule your mind with clarity, or your untrained mind will rule and ruin your destiny.",
        "Will you choose reactionary anger today, or unbreakable inner peace? Share your thoughts in the comments!"
    ]
    narrations = narrations_tr if is_tr else narrations_en
    visuals = [
        ("Ancient marble statue of Marcus Aurelius under dramatic side lighting", ["marcus aurelius marble statue", "ancient roman bust sculpture", "stoic statue dramatic lighting"]),
        ("Ancient Roman Colosseum at sunset with dramatic sun rays", ["rome colosseum sunset drone", "ancient roman ruins colosseum", "epic golden sunset rome"]),
        ("Chaotic crowd walking fast in modern metropolis contrasting calm observer", ["busy crowd metropolis blur", "calm person standing crowd", "solitary figure city"]),
        ("Close-up of calm stoic facial expression looking outward in thought", ["calm face meditation eyes", "disciplined man looking distance", "thoughtful philosopher portrait"]),
        ("Ancient scroll and ink quill resting on heavy weathered stone table", ["ancient parchment manuscript", "quill ink stone desk", "vintage philosophical writing"]),
        ("Glowing fiery embers in darkness symbolizing burning anger", ["burning embers fire dark", "fiery sparks slow motion", "flames fireplace dramatic"]),
        ("Sunrise breaking over rugged misty mountain peaks", ["sunrise mountain peak aerial", "misty alpine summit drone", "majestic nature sunrise"]),
        ("Solitary marble pillar standing tall amidst ancient ruined temple", ["ancient marble pillar ruins", "greek roman temple standing", "resilient stone architecture"]),
        ("Deep clear mountain lake with mirror-like undisturbed reflection", ["serene mountain lake mirror", "calm still water reflection", "peaceful nature tranquility"]),
        ("Ancient mighty oak tree standing strong against powerful storm winds", ["oak tree weathering storm", "strong tree wind dramatic", "resilience nature storm"]),
        ("Disciplined athlete training in cold dawn light with intense focus", ["disciplined athlete training dawn", "focused runner morning cold", "masculine discipline workout"]),
        ("Blacksmith hammering red-hot steel on anvil with flying sparks", ["blacksmith forging steel anvil", "hammering hot iron sparks", "forging resilience metal"]),
        ("Silhouette standing on mountain cliff overlooking infinite clouds", ["silhouette cliff clouds view", "master of mind mountain", "epic panorama contemplation"]),
        ("Direct gaze to camera with thoughtful stoic nod inviting reflection", ["stoic philosopher direct gaze", "dramatic camera pull back", "subscribe follow philosophy"])
    ]
    scenes = []
    for i in range(14):
        desc, queries = visuals[i]
        scenes.append({
            "scene_number": i + 1,
            "narration": narrations[i],
            "scene_description": desc,
            "search_queries": queries,
            "duration": 3.0,
            "mood": "calm" if i in (1, 3, 8) else "epic" if i in (0, 6, 12) else "dramatic"
        })
    return {
        "title": clean_title if is_tr else f"Stoic Wisdom: {clean_title}",
        "visual_theme": "ancient stoic marble roman gold dramatic highlights",
        "full_narration": " ".join(narrations),
        "scenes": scenes
    }


def _generate_dark_psychology_scenes(clean_title: str, is_tr: bool):
    """
    Constructs 14-scene Dark Psychology & Body Language format (Tone: mysterious, analytical, cautionary).
    """
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
    scenes = []
    for i in range(14):
        desc, queries = visuals[i]
        scenes.append({
            "scene_number": i + 1,
            "narration": narrations[i],
            "scene_description": desc,
            "search_queries": queries,
            "duration": 3.0,
            "mood": "mysterious" if i in (0, 1, 3, 5, 7) else "dark" if i in (2, 4, 8, 12) else "dramatic"
        })
    return {
        "title": clean_title if is_tr else f"Dark Psychology: {clean_title}",
        "visual_theme": "dark psychology moody violet shadow noir",
        "full_narration": " ".join(narrations),
        "scenes": scenes
    }


def _generate_procedural_fallback_scenes(title: str, niche_type: str = None, raw_body: str = "", language: str = None) -> dict:
    """
    Failsafe procedural scene generator when external AI models are inaccessible.
    Guarantees rich 14-scene retention-friendly script structure with pure English search terms.
    Dispatches directly to specialized niche templates based on category & tone.
    """
    clean_title, main_kw, words, matched_en = _detect_niche_and_terms(title, raw_body)
    lang = language or getattr(config, "LANGUAGE", "tr")
    is_tr = (lang == "tr")
    combined = f"{title} {raw_body}".lower()

    # 1. Reddit Confessions, WhatsApp chats & Split-screen stories
    if niche_type in ("2_reddit_confessions", "20_whatsapp_chats", "3_split_gameplay") or any(k in combined for k in ["itiraf", "reddit", "whatsapp", "mülakat", "iş görüşmesi", "patron", "aldat", "gizli"]):
        return _generate_reddit_confession_scenes(clean_title, combined, is_tr)

    # 2. Breaking News & Flash News
    if niche_type in ("1_news_flash", "57_rss_breaking") or any(k in title.lower() for k in ["son dakika", "flaş", "haber", "açıklama", "deprem", "karar"]):
        return _generate_news_flash_scenes(clean_title, is_tr)

    # 3. Stoic Philosophy
    if niche_type in ("6_stoic_philosophy", "36_stoic_cyberpunk") or any(k in title.lower() for k in ["stoa", "marcus aurelius", "seneca", "felsefe"]):
        return _generate_stoic_scenes(clean_title, is_tr)

    # 4. Dark Psychology & Body Language
    if niche_type in ("7_dark_psychology", "38_dark_psych_parkour") or any(k in title.lower() for k in ["karanlık psikoloji", "manipülasyon", "beden dili"]):
        return _generate_dark_psychology_scenes(clean_title, is_tr)

    # Standard general fallback (14 scenes, dynamic English keywords)
    primary_kw = matched_en[0] if matched_en else "cinematic nature discovery"
    second_kw = matched_en[1] if len(matched_en) > 1 else "science technology innovation"

    topics_tr = [
        f"Bugün sizlere {clean_title} hakkında bilinmeyen büyüleyici detayları aktarıyoruz.",
        "İlk olarak, çoğu insanın farkında bile olmadığı şaşırtıcı bir gerçekle başlayalım.",
        "Araştırmacılar ve bilim insanları bu durumun ardındaki sırrı uzun süredir çözmeye çalışıyor.",
        "Olayın derinine indiğimizde karşımıza çıkan ilk ipucu tüm dengeleri tamamen değiştiriyor.",
        "Gözden kaçan en kritik nokta, bu durumun günlük hayatımız üzerindeki doğrudan etkisidir.",
        "Şimdiye kadar bildiğiniz tüm kalıpları yıkacak olan bu detay gerçekten inanılmaz.",
        "Uzmanların yaptığı son analizler, beklenenden çok daha derin bir tablo ortaya koyuyor.",
        "Gelişmeler devam ettikçe ortaya çıkan yeni kanıtlar izleyenleri hayrete düşürüyor.",
        "Verileri birleştirdiğimizde gerçeğin bambaşka bir boyutta olduğunu görüyoruz.",
        "Tarihsel kanıtlar ve modern araştırmalar aynı noktayı işaret ediyor.",
        "Bu keşif, yakın gelecekte tüm alışkanlıklarımızı yeniden şekillendirebilir.",
        "Gözlerinizi açıp baktığınızda işaretleri her yerde görebilirsiniz.",
        "Gerçekler çoğu zaman çıplak gözle görülemeyecek kadar derinde saklıdır.",
        "Peki siz bu konuda ne düşünüyorsunuz? Yorumlarda buluşalım ve takip etmeyi unutmayın!"
    ]

    topics_en = [
        f"Today we explore the fascinating, untold reality behind {clean_title}.",
        "To begin with, let us look at an astonishing fact that most people are completely unaware of.",
        "Leading researchers and scientists have spent years attempting to unravel the secret behind this phenomenon.",
        "When we dive deeper beneath the surface, the first piece of evidence completely alters our understanding.",
        "The most critical takeaway is the direct and profound impact this has on our everyday lives.",
        "This surprising revelation challenges traditional assumptions and offers a fresh perspective.",
        "Recent analytical data and breakthroughs present a far more intricate and compelling picture.",
        "As ongoing investigations progress, new evidence continues to astonish observers worldwide.",
        "Connecting the data points reveals that the reality exists on an entirely different scale.",
        "Both historical archives and modern scientific research consistently point toward the exact same conclusion.",
        "This discovery has the potential to reshape our habits and perspectives in the near future.",
        "Once you know what to look for, you begin noticing the subtle signs everywhere around you.",
        "Truth is often concealed beneath layers that cannot be perceived with a casual glance.",
        "What are your thoughts on this discovery? Join the conversation in the comments and subscribe for more!"
    ]
    topics = topics_tr if is_tr else topics_en

    visuals = [
        ("Cinematic aerial drone shot over majestic landscapes with golden sunlight", [f"{primary_kw} aerial drone", "cinematic landscape sunset", "epic 4k nature"]),
        ("Mystery dark atmosphere with dramatic shadow revealing discovery", ["mystery dark atmosphere", "dramatic lighting shadow", "deep investigation reveal"]),
        ("Science laboratory research with futuristic glowing blue holographic data", ["science laboratory research", "data technology abstract", "futuristic concept blue"]),
        ("Deep discovery investigation aerial drone flight over mountain summit", ["deep discovery investigation", "aerial drone mountain", "ancient mystery ruins"]),
        ("Modern civilization city lights and human psychology abstract blur", ["modern civilization city lights", "human mind psychology", "abstract motion blur"]),
        ("Shocking discovery revelation with explosion of warm golden light rays", ["shocking discovery revelation", "explosion of light golden", "epic cinematic drone view"]),
        ("Detailed analysis research with magnifying glass inspection and cyber stream", ["detailed analysis research", "magnifying glass inspection", "digital data stream cyber"]),
        ("Unbelievable truth concept with deep cosmic space galaxy and ocean blue", ["unbelievable truth concept", "space galaxy universe stars", "deep ocean mystery blue"]),
        ("Connecting puzzle elements under light rays cinematic landscape", ["connecting elements puzzle", "light rays cinematic rays", "epic sunset drone landscape"]),
        ("Historical archive document being analyzed under vintage desk lamp", ["historical archive document", "vintage desk research", "ancient mystery scroll"]),
        ("Futuristic technology interface glowing in clean high-tech lab", ["futuristic high tech laboratory", "clean modern science room", "advanced technology screen"]),
        ("Fast dynamic drone swoop over majestic canyon and river", ["canyon river drone swoop", "extreme nature landscape", "dramatic outdoor panorama"]),
        ("Thoughtful silhouette looking towards golden sunrise horizon", ["silhouette sunrise horizon", "inspirational future view", "sunrise mountain contemplation"]),
        ("Social media engagement card with like subscribe bell icon", ["social media engagement bell", "like subscribe follow icon", "cinematic ending landscape"])
    ]

    scenes = []
    for i in range(14):
        desc, queries = visuals[i]
        scenes.append({
            "scene_number": i + 1,
            "narration": topics[i],
            "scene_description": desc,
            "search_queries": queries,
            "duration": 3.0,
            "mood": "epic" if i in (0, 5, 8, 12) else "mysterious" if i in (1, 3, 7, 9) else "energetic"
        })

    return {
        "title": clean_title,
        "visual_theme": "cinematic documentary dark and bright highlights",
        "full_narration": " ".join(topics),
        "scenes": scenes
    }
