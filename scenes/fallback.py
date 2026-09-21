"""
Procedural and rule-based fallback scene generator when AI quotas or APIs are unavailable.
Supports dynamic context-aware Reddit story rewriting, breaking news, stoicism, dark psychology,
and pure English stock query synthesis tailored to all 35 niches.
"""

import re
import config


EN_TOPIC_MAP = {
    "bitcoin": "bitcoin crypto candlestick chart",
    "crypto": "cryptocurrency trading terminal",
    "forex": "forex trading desk monitors",
    "trading": "live trading desk screens",
    "livetrading": "live trading stream desk",
    "live trading": "live trading broadcast desk",
    "gold": "gold bullion trading chart",
    "ethereum": "ethereum crypto chart screen",
    "banknifty": "india bank nifty index chart",
    "btc": "bitcoin price chart screen",
    "borsa": "stock exchange trading floor",
    "altcoin": "altcoin crypto market screen",
}

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
    "altın": "gold bullion trading chart", "borsa": "stock market trading floor",
    "tarih": "ancient historical battlefield", "ürün": "viral smart gadget lifestyle"
}


def sanitize_topic_title(title: str) -> str:
    """Strip emojis, hashtags and live-stream noise; keep semantic topic text."""
    t = (title or "").strip()
    t = re.sub(r"[\U00010000-\U0010ffff]", "", t)
    t = re.sub(r"[\u2600-\u27bf\ufe00-\ufe0f]", "", t)
    t = re.sub(r"#[\w]+", " ", t)
    t = re.sub(r"[^\w\s\-&]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t).strip()
    return t or "Canlı Piyasa Özeti"


def _detect_niche_and_terms(title: str, body: str = ""):
    clean_title = sanitize_topic_title(title)
    words = [w for w in clean_title.split() if len(w) > 2]
    combined_text = f"{title} {body}".lower()

    matched_en = []
    for en_k, en_v in EN_TOPIC_MAP.items():
        if en_k in combined_text:
            matched_en.append(en_v)
    for tr_k, en_v in TR_EN_TOPIC_MAP.items():
        if tr_k in combined_text and en_v not in matched_en:
            matched_en.append(en_v)

    if matched_en:
        main_kw = matched_en[0]
    else:
        main_kw = "dramatic cinematic mystery"

    return clean_title, main_kw, words, matched_en


_CRYPTO_TOPIC_HINTS = (
    "bitcoin", "crypto", "kripto", "forex", "trading", "livetrading", "live trading",
    "gold", "altın", "borsa", "banknifty", "ethereum", "eth ", "btc", "altcoin",
)


def _pad_narration_to_min_words(text: str, min_words: int = 10, *, is_tr: bool = True) -> str:
    """Ensure procedural fallback narrations meet TTS minimum word count."""
    try:
        from scenes.narration_validate import normalize_narration_for_validation, scene_narration_usable
        raw = (text or "").strip()
        if scene_narration_usable(raw):
            return raw
        norm = normalize_narration_for_validation(raw).rstrip(".!? ")
        pad = "Bunu hafta boyunca aklında tut." if is_tr else "Keep this in mind throughout the week."
        combined = f"{norm} {pad}".strip() if norm else pad
        if combined[-1] not in ".!?":
            combined += "."
        if len(normalize_narration_for_validation(combined).split()) < min_words:
            extra = "Detayları kaçırmamak için takipte kal." if is_tr else "Stay tuned so you do not miss the details."
            combined = f"{combined.rstrip('.!? ')} {extra}."
        return combined
    except Exception:
        return text or ""


def _finalize_fallback_plan(plan: dict, *, is_tr: bool = True) -> dict:
    scenes = plan.get("scenes") or []
    for sc in scenes:
        sc["narration"] = _pad_narration_to_min_words(sc.get("narration") or "", is_tr=is_tr)
    n = len(scenes)
    if n:
        try:
            from director.schema import QualityThresholds
            qt = QualityThresholds()
            target, min_d, max_d = qt.target_duration, qt.min_duration, qt.max_duration
        except Exception:
            target, min_d, max_d = 48.0, 38.0, 60.0
        total = sum(float(sc.get("duration") or 3.0) for sc in scenes)
        if total < min_d or total > max_d or abs(total - target) > 0.75:
            per = round(max(2.0, min(7.5, target / n)), 2)
            for sc in scenes:
                sc["duration"] = per
            drift = round(target - per * n, 2)
            if scenes and abs(drift) > 0.01:
                scenes[-1]["duration"] = round(scenes[-1]["duration"] + drift, 2)
    plan["scenes"] = scenes
    plan["full_narration"] = " ".join(
        (s.get("narration") or "").strip() for s in scenes if (s.get("narration") or "").strip()
    )
    return plan


def _topic_is_crypto_market(title: str, body: str = "", niche_type: str = None) -> bool:
    if niche_type and niche_type != "8_crypto_market":
        return False
    if niche_type == "8_crypto_market":
        return True
    combined = f"{title} {body}".lower()
    return any(k in combined for k in _CRYPTO_TOPIC_HINTS)


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


def _stoic_variant_index(clean_title: str, variation_seed: int = 0) -> int:
    base = sum(ord(c) for c in clean_title.lower()) + (variation_seed * 17)
    return base % 4


def _build_stoic_narrations(clean_title: str, is_tr: bool, variation_seed: int = 0) -> list:
    """
    Topic-seeded Stoic narrations — each variant weaves user title through the arc so
    different UI topics produce distinct full_narration (not just scene 1).
    """
    topic = clean_title.strip() or ("Stoacılık" if is_tr else "Stoicism")
    variant = _stoic_variant_index(topic, variation_seed)

    if is_tr:
        variants = [
            [
                f"'{topic}' dediğinde çoğu kişi motivasyon arar; Stoacılar ise zihinsel disiplin arar.",
                f"Marcus Aurelius Meditations'ta şunu yazar: '{topic}' gibi dış olaylar seni değil, verdiğin tepki tanımlar.",
                "Kontrol edemediğin haberler, yorumlar ve başkalarının hüsranı senin huzurunu çalmak için gelmez.",
                f"Seneca der ki acının çoğu gerçekte değil, '{topic}' hakkında kurduğun senaryolarda başlar.",
                "Öfkeyi bir silah sanırsın ama o elinde tuttuğun kor ateştir; önce seni yakarsın.",
                f"Bugün '{topic}' seni sarsarsa, nefes al — tepki vermeden önce üç saniye bekle.",
                "Epiktetos: 'Seni inciten olay değil, o olaya yüklediğin anlamdır.'",
                f"2000 yıllık felsefe şunu öğretir: {topic} senin kontrol alanın değil; tutumun kontrol alanındır.",
                "Sabah aynaya bakıp şunu söyle: Bugün zor insanlar, gürültü ve belirsizlik göreceğim.",
                "Onların davranışı senin karakterini değil; senin sabrını test eden antrenmandır.",
                "Disiplin, iyi hissettiğinde değil; en çok dağılmak istediğinde doğru olanı seçmektir.",
                f"'{topic}' kriz anında panik yerine prosedür seç: ne biliyorum, ne yapabilirim, neyi bırakmalıyım?",
                "Zihnini eğitmezsen, algoritma ve kaos zihnini senin yerine yönetir.",
                f"Peki '{topic}' karşısında bugün hangi stoacı cevabı seçeceksin? Yorumlarda yaz.",
            ],
            [
                f"Çoğu insan '{topic}' duyunca hemen çözüm ister; bilge insan önce sınırını çizer.",
                "Marcus Aurelius: 'Gününü başkalarının hatasıyla zehirleme.'",
                f"'{topic}' seni endişelendiriyorsa, liste yap: kontrol edebilirim / edemem.",
                "Kontrol edemediklerin için harcadığın her dakika, hayatından çalınmış bir dakikadır.",
                "Seneca: 'Mutluluk, dışarıda aranan bir şey değil; içeride inşa edilen bir alışkanlıktır.'",
                f"Stres anında '{topic}' kelimesini tekrarlama; nefesini ve omuzlarını gevşet.",
                "Epiktetos'un Dichotomy of Control'ü: ya eyleme geç ya da bırak.",
                f"Antik Roma'da imparator bile '{topic}' karşısında sakin kalmayı antrenman sayardı.",
                "Gürültülü dünyada sessizlik bir lüks değil; bilinçli bir savunma hattıdır.",
                f"'{topic}' hakkındaki korkunu büyüten şey, kanıt değil — varsayımlarındır.",
                "Disiplin spor salonu gibidir: her tekrar zihnini bir sonraki fırtınaya hazırlar.",
                "Zorluk seni kırmak için gelmez; hangi değerlerin gerçek olduğunu göstermek için gelir.",
                "Kendi sözleşmeni yaz: Bugün panik yok, sadece net adımlar.",
                f"'{topic}' seni bugün yener mi, yoksa sen mi eğitirsin? Yorumlarda buluşalım.",
            ],
            [
                f"'{topic}' konusu viral olabilir; stoacı zihin ise kalıcı olmayı seçer.",
                "Marcus Aurelius sabah günlüğünde kendine sorardı: Bugün hangi zayıf tepkilerim var?",
                f"'{topic}' seni kızdırdığında, önce bedenini dinle: çene, omuz, kalp hızı.",
                "Dış dünya değişmez; değişen tek şey olaylara verdiğin anlamdır.",
                "Seneca: 'Bazen iyileşmek için konuşmayı bırakmak gerekir.'",
                f"'{topic}' tartışmasına girmek zorunda değilsin; susmak da stratejidir.",
                "Epiktetos: 'İnsanları değiştirmeye çalışma; kendi tepkini eğit.'",
                f"2000 yıllık bilgelik '{topic}' için sihirli cevap vermez; sihirli alışkanlık verir.",
                "Her sabah iki dakika: bugün neyi kabul ediyorum, neyi reddediyorum?",
                "Başkalarının kaosu senin acil durumun değildir; sınır çizmek saygıdır.",
                "Disiplin, duyguyu bastırmak değil; duyguyu yönetmek için pratik yapmaktır.",
                f"'{topic}' geçer; senin bugün seçtiğin karakter kalır.",
                "Zihnini koru — çünkü orası hayatının gerçek komuta merkezidir.",
                "Bugün hangi stoacı alışkanlığı deneyeceksin? Yorumlarda paylaş.",
            ],
            [
                f"'{topic}' gibi konular beynini tehdit moduna sokar; stoacılık güven modunu inşa eder.",
                "Marcus Aurelius: 'Engel yolun kendisidir.'",
                f"'{topic}' seni gece uyutuyorsa, yarın sabah ilk işin kontrol listesi olsun.",
                "Endişe, çözülmemiş problemlerin hayalidir; eylem, endişenin panzehiridir.",
                "Seneca: 'Zamanımız dar; israf edersek hayat kısa gelir.'",
                f"'{topic}' için harcadığın enerjiyi, yapabileceğin tek küçük adıma kaydır.",
                "Epiktetos: 'Özgürlük, dış koşullara değil; iç kararlarına bağlıdır.'",
                f"Antik felsefe '{topic}' sorusuna cevap değil; cevap verme biçimi öğretir.",
                "Sabah rutini: telefon yok, üç derin nefes, bir net niyet cümlesi.",
                "Başkalarının beklentisi senin görevin değil; kendi ahlaki pusulan görevindir.",
                "Disiplin, motivasyon bittiğinde devreye giren gerçek sistemdir.",
                f"'{topic}' fırtınası geçince ayakta kalan, en çok pratik yapan kişidir.",
                "Zihnini eğit; yoksa gürültü senin yerine karar verir.",
                f"'{topic}' karşısında stoacı cevabın ne? Yorumlarda tartışalım.",
            ],
        ]
        return variants[variant]

    en_variants = [
        [
            f"When people hear '{topic}', they chase motivation — Stoics train mental discipline.",
            f"Marcus Aurelius wrote: events like '{topic}' do not define you; your response does.",
            "Other people's chaos is not a license to surrender your inner peace.",
            f"Seneca warned we suffer more from stories about '{topic}' than from facts.",
            "Anger feels like a weapon, but it is a coal that burns your hand first.",
            f"If '{topic}' shakes you today, pause three seconds before reacting.",
            "Epictetus: you are disturbed not by events, but by your judgment of them.",
            f"Two thousand years of wisdom: '{topic}' is outside your control; attitude is inside.",
            "Each morning expect noise, rude people, and uncertainty.",
            "Their behavior tests your patience — not your identity.",
            "Discipline is choosing the right action when you least feel like it.",
            f"In a '{topic}' crisis, ask: what do I know, what can I do, what must I release?",
            "Train your mind, or algorithms and chaos will train it for you.",
            f"What Stoic response will you choose about '{topic}' today? Comment below.",
        ],
        [
            f"'{topic}' makes most people panic; the wise draw boundaries first.",
            "Marcus Aurelius: do not poison your day with another person's fault.",
            f"Worried about '{topic}'? Split a list: controllable vs uncontrollable.",
            "Every minute spent on the uncontrollable is stolen from your life.",
            "Seneca: happiness is a habit built inside, not found outside.",
            f"When stressed about '{topic}', relax breath and shoulders before speaking.",
            "Epictetus: act on what you control, release what you cannot.",
            f"Even emperors practiced calm responses to shocks like '{topic}'.",
            "Silence is not luxury — it is deliberate defense.",
            f"Fear about '{topic}' grows from assumptions, not proof.",
            "Discipline is repetition that prepares you for the next storm.",
            "Hardship reveals which values are real.",
            "Write a daily contract: no panic, only clear steps.",
            f"Will '{topic}' defeat you today, or will you train through it? Comment.",
        ],
        [
            f"'{topic}' may trend; a Stoic mind chooses what endures.",
            "Marcus Aurelius asked each morning: which weak reactions must I watch?",
            f"When '{topic}' angers you, scan your body: jaw, shoulders, heartbeat.",
            "The world may not change; your interpretation always can.",
            "Seneca: sometimes healing begins when you stop arguing.",
            f"You do not owe a debate about '{topic}' — silence is strategy.",
            "Epictetus: train your response, not other people.",
            f"Ancient wisdom offers no magic answer to '{topic}' — only habits.",
            "Two minutes each morning: what do I accept, what do I refuse?",
            "Someone else's chaos is not your emergency.",
            "Discipline is practice, not suppression.",
            f"'{topic}' will pass; today's character choice remains.",
            "Protect your mind — it is your real command center.",
            "Which Stoic habit will you test today? Comment below.",
        ],
        [
            f"Topics like '{topic}' trigger threat mode; Stoicism builds safety through practice.",
            "Marcus Aurelius: the obstacle is the way.",
            f"If '{topic}' keeps you awake, tomorrow's first task is a control checklist.",
            "Worry imagines unsolved problems; action is the antidote.",
            "Seneca: life is short if we waste time.",
            f"Shift energy about '{topic}' into one small executable step.",
            "Epictetus: freedom depends on inner decisions, not outer conditions.",
            f"Philosophy does not answer '{topic}' — it teaches how to respond.",
            "Morning routine: no phone, three breaths, one clear intention.",
            "Other people's expectations are not your duty.",
            "Discipline runs when motivation stops.",
            f"After the '{topic}' storm, whoever practiced most stays standing.",
            "Train your mind, or noise decides for you.",
            f"What is your Stoic answer to '{topic}'? Join the discussion.",
        ],
    ]
    return en_variants[variant]


def _generate_stoic_scenes(clean_title: str, is_tr: bool, variation_seed: int = 0):
    """
    Constructs 14-scene Stoic philosophy format (Tone: deep, calm, disciplined, masculine).
    User topic is woven through all scenes; variation_seed rotates template on retry (#104).
    """
    narrations = _build_stoic_narrations(clean_title, is_tr, variation_seed)
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


def _generate_astrology_horoscope_scenes(clean_title: str, is_tr: bool, variation_seed: int = 0):
    """
    14-scene astrology / weekly horoscope format (Tone: mystical, intriguing, ranking).
    Covers burç yorumu, şanslı burçlar, aşk/para/kariyer sıralaması.
    """
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

    moods = ["mysterious", "calm", "bright", "epic", "energetic", "calm", "calm", "energetic",
             "dark", "calm", "energetic", "calm", "epic", "bright"]
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
            "beat_type": "hook" if i == 0 else "climax" if i == 4 else "resolution" if i == 13 else "conflict",
        })

    return {
        "title": topic if is_tr else f"Weekly Horoscope: {topic}",
        "visual_theme": "mystical astrology zodiac galaxy purple gold stars",
        "full_narration": " ".join(narrations),
        "scenes": scenes,
    }


def _crypto_variant_index(clean_title: str, variation_seed: int = 0) -> int:
    base = sum(ord(c) for c in clean_title.lower()) + (variation_seed * 13)
    return base % 2


def _generate_crypto_market_scenes(clean_title: str, is_tr: bool, variation_seed: int = 0):
    """
    14-scene live trading / crypto market format (Tone: urgent, analytical, fast-paced).
    Topic-seeded for gold, bitcoin, forex and live-stream titles.
    """
    topic = clean_title.strip() or ("Canlı Kripto Piyasa" if is_tr else "Live Crypto Market")
    variant = _crypto_variant_index(topic, variation_seed)
    has_gold = any(k in topic.lower() for k in ("gold", "altın", "altin"))
    has_banknifty = "banknifty" in topic.lower()

    if is_tr:
        gold_line = "Altın ve Bitcoin aynı ekranda ayrı hikâye anlatıyor — dikkat!" if has_gold else "Bitcoin grafiği şu an tüm piyasayı belirliyor!"
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
        narrations_variants = [
            [
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
            ],
        ]
        narrations = narrations_variants[0]

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


def _generate_pack_fallback_scenes(pack: dict, clean_title: str, is_tr: bool):
    """Family-generic fallback using this niche's pack — never a crypto clone."""
    topic = (clean_title or "").strip() or pack.get("name") or "Konu"
    name = pack.get("name") or "Shorts"
    hook = pack.get("hook_style") or topic
    subjects = list(pack.get("subjects") or []) or [
        "cinematic landscape aerial",
        "dramatic light through clouds",
        "person walking empty street",
        "abstract light particles",
    ]
    include = list(pack.get("must_include") or ["cinematic"])
    if is_tr:
        narrations = [
            f"{hook} {topic} hakkında bugün net ve eksiksiz konuşuyoruz, kısa stub yok.",
            f"{name} formatında {topic} için ilk kritik nokta tam burada başlıyor izleyici.",
            f"Bu nişin kuralları başka şablona kaymaz; görseller {include[0]} dünyasında kalır.",
            f"İkinci katman: {topic} iddiasını somut örnekle bağlarız ve tempo düşmez.",
            f"Çoğu kanal burada genel belgesel kopyalar; biz {name} tonunu koruyoruz.",
            f"Kanıt sahnesi: {topic} detayı izleyiciyi yorum yazmaya zorlayacak kadar net.",
            f"Risk ve itiraz var ama {name} paketindeki yasak görselleri asla kullanmayız.",
            f"Dönüş sahnesi: {topic} sonucunu tek cümlede bağla ve merakı açık bırak.",
            f"Özet: {topic} bu nişte kanca, kanıt ve soru ile kapanır, başka niş kopyası değil.",
            f"Peki sen {topic} konusunda ne düşünüyorsun? Yorumlara yaz, döngü başa bağlanır!",
        ]
    else:
        narrations = [
            f"{hook} Today we cover {topic} fully inside the {name} niche pack.",
            f"First beat stays on {topic} with complete sentences, never a six-word stub.",
            f"Visuals stay in {include[0]} territory; we do not clone another niche template.",
            f"Second layer: a concrete example that keeps {topic} specific and paced.",
            f"Most channels paste a generic documentary; this pack keeps {name} tone.",
            f"Proof beat: a detail about {topic} strong enough to force a comment.",
            f"There is tension, but forbidden visuals from this pack never appear.",
            f"Turn: close the {topic} result in one full sentence and keep curiosity.",
            f"Summary: {topic} ends with hook, proof, and a question — not a crypto stub.",
            f"What do you think about {topic}? Comment below so the loop can restart!",
        ]
    moods = ["urgent", "dramatic", "energetic", "tense", "mysterious", "calm", "epic", "dark", "bright", "calm"]
    scenes = []
    for i, narr in enumerate(narrations):
        subject = subjects[i % len(subjects)]
        desc = f"{subject} cinematic atmospheric"
        queries = [
            subject,
            f"{subject} {include[0]}" if include else f"{subject} cinematic",
            "cinematic 4k b-roll",
        ]
        scenes.append({
            "scene_number": i + 1,
            "narration": narr,
            "scene_description": desc,
            "search_queries": queries,
            "duration": 4.8,
            "mood": moods[i % len(moods)],
            "beat_type": "hook" if i == 0 else "resolution" if i == len(narrations) - 1 else "conflict",
        })
    return {
        "title": topic if is_tr else f"{name}: {topic}",
        "visual_theme": pack.get("family") or "cinematic",
        "full_narration": " ".join(narrations),
        "scenes": scenes,
        "niche_id": pack.get("id"),
        "procedural_fallback": True,
        "scenario_pack_family": pack.get("family"),
    }


def _generate_procedural_fallback_scenes(
    title: str,
    niche_type: str = None,
    raw_body: str = "",
    language: str = None,
    variation_seed: int = 0,
) -> dict:
    """
    Failsafe when AI is unavailable. Dispatch by this topic's niche pack —
    never dump a crypto-shaped stub onto an unrelated niche.
    """
    from niche_templates import NICHES, get_scenario_pack

    clean_title, main_kw, words, matched_en = _detect_niche_and_terms(title, raw_body)
    lang = language or getattr(config, "LANGUAGE", "tr")
    is_tr = (lang == "tr")
    combined = f"{title} {raw_body}".lower()

    resolved = niche_type if niche_type in NICHES else None
    if not resolved:
        if any(k in combined for k in ["itiraf", "reddit", "whatsapp", "mülakat", "iş görüşmesi", "patron", "aldat", "gizli"]):
            resolved = "2_reddit_confessions" if "whatsapp" not in combined else "20_whatsapp_chat_story"
        elif any(k in title.lower() for k in ["son dakika", "flaş", "haber", "açıklama", "deprem", "karar"]):
            resolved = "1_news_flash"
        elif any(k in title.lower() for k in ["stoa", "marcus aurelius", "seneca", "felsefe"]):
            resolved = "6_stoic_philosophy"
        elif any(k in title.lower() for k in ["karanlık psikoloji", "manipülasyon", "beden dili"]):
            resolved = "7_dark_psychology"
        elif any(k in combined for k in ["burç", "burcu", "astroloji", "horoskop", "zodyak", "zodiac", "horoscope"]):
            resolved = "18_astrology_horoscope"
        elif _topic_is_crypto_market(title, raw_body, niche_type=None):
            resolved = "8_crypto_market"
        else:
            resolved = "9_five_facts"

    pack = get_scenario_pack(resolved, language=lang)
    family = pack["family"]
    nid = pack["id"]

    if nid == "8_crypto_market" or family == "crypto":
        return _finalize_fallback_plan(
            _generate_crypto_market_scenes(clean_title, is_tr, variation_seed=variation_seed),
            is_tr=is_tr,
        )
    if nid in ("2_reddit_confessions",) or family == "reddit":
        return _finalize_fallback_plan(_generate_reddit_confession_scenes(clean_title, combined, is_tr), is_tr=is_tr)
    if nid in ("20_whatsapp_chat_story", "3_split_gameplay") or family == "whatsapp":
        return _finalize_fallback_plan(_generate_reddit_confession_scenes(clean_title, combined, is_tr), is_tr=is_tr)
    if nid in ("1_news_flash",) or family == "news":
        return _finalize_fallback_plan(_generate_news_flash_scenes(clean_title, is_tr), is_tr=is_tr)
    if nid in ("6_stoic_philosophy",) or family == "stoic":
        return _finalize_fallback_plan(_generate_stoic_scenes(clean_title, is_tr, variation_seed=variation_seed), is_tr=is_tr)
    if nid == "7_dark_psychology" or family == "dark":
        return _finalize_fallback_plan(_generate_dark_psychology_scenes(clean_title, is_tr), is_tr=is_tr)
    if nid == "18_astrology_horoscope" or family == "astrology":
        return _finalize_fallback_plan(
            _generate_astrology_horoscope_scenes(clean_title, is_tr, variation_seed=variation_seed),
            is_tr=is_tr,
        )
    return _finalize_fallback_plan(_generate_pack_fallback_scenes(pack, clean_title, is_tr), is_tr=is_tr)
