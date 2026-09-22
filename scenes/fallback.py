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
        # Fallbacks must remain natural narration. Strip emoji and mechanical
        # engagement bait before timing and word-count validation.
        raw = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf\ufe00-\ufe0f]", "", raw)
        raw = re.sub(
            r"\s*(?:yorumlarda paylaşın|yorumlara yazın|takipte kalın|abone olun|like ve subscribe|subscribe)\s*[.!?]*",
            " ", raw, flags=re.I,
        )
        raw = re.sub(r"\s+", " ", raw).strip()
        # Generic padding must never remain in final narration. It can land
        # inside a quote after a sentence normalizer and create an open quote
        # or a false clause boundary.
        raw = re.sub(r"\s+B\u0075nu hafta boyunca akl\u0131nda tut\.?", ".", raw, flags=re.I)
        raw = re.sub(r"\s+Bunu\s+hafta\s+boyunca\s+aklında\s+tut\.?", ".", raw, flags=re.I)
        raw = re.sub(r"\s+Keep this in mind throughout the week\.?", ".", raw, flags=re.I)
        raw = re.sub(r"\.{2,}", ".", raw)
        if raw.count("'") % 2 == 1:
            raw = raw + "'"
        if raw and raw[-1] not in ".!?":
            raw += "."
        if scene_narration_usable(raw):
            return raw
        norm = normalize_narration_for_validation(raw).rstrip(".!? ")
        pad = (
            "Bu iddianın kaynağını kontrol et ve bağlamını oku."
            if is_tr else
            "Check the source of this claim and read its full context."
        )
        # Keep complete source sentences intact. The old generic padding was
        # appended after a closing quote, producing broken lines such as
        # `Seneca: '...' Bunu hafta boyunca aklında tut.`
        if norm and re.search(r"[.!?]$", norm):
            extra = (
                "Bu, sessiz kalmanın gücünü hatırlatır."
                if is_tr else "That is the power of deliberate silence."
            )
            combined = f"{norm} {extra}".strip()
        else:
            combined = f"{norm} {pad}".strip() if norm else pad
        if combined[-1] not in ".!?":
            combined += "."
        if len(normalize_narration_for_validation(combined).split()) < min_words:
            extra = "Bu ayrıntı, anlatının geri kalanını anlamak için gerekli." if is_tr else "That detail is necessary to understand the rest of the story."
            combined = f"{combined.rstrip('.!? ')} {extra}."
        return combined
    except Exception:
        return text or ""


def _finalize_fallback_plan(plan: dict, *, is_tr: bool = True) -> dict:
    scenes = plan.get("scenes") or []
    for sc in scenes:
        sc["narration"] = _pad_narration_to_min_words(sc.get("narration") or "", is_tr=is_tr)
        # Final invariant: no mechanical padding token in published narration.
        sc["narration"] = re.sub(
            r"\s+Bunu\s+hafta\s+boyunca\s+aklında\s+tut\.?", ".",
            sc["narration"], flags=re.I,
        )
        if sc["narration"].count("'") % 2 == 1:
            sc["narration"] += "'"
        sc["narration"] = sc["narration"].replace(".' .", ".'").replace(".'.", ".'")
        if sc["narration"] and sc["narration"][-1] not in ".!?":
            sc["narration"] += "."
        vi = sc.get("visual_intent") if isinstance(sc.get("visual_intent"), dict) else {}
        description = str(sc.get("scene_description") or "").strip()
        sc["visual_intent"] = {
            **vi,
            "subject": vi.get("subject") or description[:80],
            "action": vi.get("action") or "move or change visibly",
            "setting": vi.get("setting") or "real world location",
            "lighting": vi.get("lighting") or sc.get("mood") or "natural light",
            "visual_priority": vi.get("visual_priority") or "subject",
            "must_exclude": list(vi.get("must_exclude") or []),
        }
        sc.setdefault("claim_ids", [])
        sc.setdefault("evidence_required", False)
    n = len(scenes)
    if n:
        try:
            from director.schema import QualityThresholds, natural_target_duration
            from viral_retention_engine import ViralRetentionEngine
            qt = QualityThresholds()
            min_d, max_d = qt.min_duration, qt.max_duration
            wc = sum(len((sc.get("narration") or "").split()) for sc in scenes)
            target = natural_target_duration(wc, min_d, max_d)
            cadence = ViralRetentionEngine.calculate_cadence_acceleration(
                total_duration=target, scene_count=n
            )
        except Exception:
            wc = sum(len((sc.get("narration") or "").split()) for sc in scenes)
            target = max(38.0, min(60.0, round(wc / 2.45, 2) if wc else 38.0))
            cadence = [round(target / n, 2)] * n
            cadence[-1] = round(target - sum(cadence[:-1]), 2)
        moods = [
            "urgent", "dramatic", "energetic", "tense", "calm",
            "epic", "mysterious", "hopeful", "solemn", "warm",
            "reverent", "luminous",
        ]
        beat_n = n
        for i, sc in enumerate(scenes):
            sc["duration"] = float(cadence[i]) if i < len(cadence) else round(target / n, 2)
            if not (sc.get("mood") or "").strip() or (sc.get("mood") or "").strip().lower() == (
                scenes[0].get("mood") or ""
            ).strip().lower() and i > 0:
                sc["mood"] = moods[i % len(moods)]
            pct = (i + 0.5) / beat_n
            if i == 0 or pct <= 0.07:
                sc["beat_type"] = "hook"
            elif pct <= 0.45:
                sc["beat_type"] = "conflict"
            elif pct <= 0.75:
                sc["beat_type"] = "climax"
            else:
                sc["beat_type"] = "resolution"
        ms = [int(round(float(sc.get("duration") or 0) * 100)) for sc in scenes]
        target_ms = int(round(min(max_d, max(min_d, target)) * 100))
        if ms:
            ms[-1] += target_ms - sum(ms)
            for i, sc in enumerate(scenes[:-1]):
                sc["duration"] = ms[i] / 100.0
            head = sum(float(sc["duration"]) for sc in scenes[:-1])
            scenes[-1]["duration"] = float(target_ms) / 100.0 - head
        # Force mood diversity even when a family stamped one mood on every row
        unique_moods = {(sc.get("mood") or "").strip().lower() for sc in scenes}
        if len(unique_moods) < min(4, n):
            for i, sc in enumerate(scenes):
                sc["mood"] = moods[i % len(moods)]
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
            ("Engaging video outro inviting debate and audience reflection", ["dramatic reflective city dusk", "thoughtful person looking at skyline silhouette", "cinematic closing shot window light"])
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
            ("Direct camera gaze asking viewer verdict and call to action", ["confident solitary person walking into city night", "cinematic dusk highway lights", "reflective quiet street lamppost"])
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
        ("YouTube shorts ending screen with reflective conclusion", ["broadcast television control room monitors dimming", "journalists leaving busy newsroom dusk", "cinematic evening cityscape news tower"])
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
                f"{topic} konusu gündeme geldiğinde çoğu kişi anlık motivasyon arar; oysa Stoacılar zihinsel bir disiplin inşa eder.",
                "Marcus Aurelius Meditations'ta şunu yazar: Karşılaştığın dış olaylar seni belirlemez, onlara verdiğin tepki belirler.",
                "Kontrol edemediğin haberler, gürültü ve başkalarının öfkesi senin huzurunu çalmak zorunda değil.",
                "Seneca'nın dediği gibi: Bizler gerçek hayattan çok, zihnimizde kurduğumuz felaket senaryolarında acı çekeriz.",
                "Öfkeyi bir silah sanırsın ama o elinde tuttuğun kor ateştir; önce senin elini yakar.",
                "Bugün seni sarsan bir gerilim olduğunda nefes al; tepki vermeden önce üç saniye dur.",
                "Epiktetos şunu hatırlatır: 'Seni inciten olayların kendisi değil, o olaylara yüklediğin anlamdır.'",
                f"İki bin yıllık felsefe şunu öğretir: {topic} senin kontrol alanın olmayabilir; fakat duruşun tamamen senin elindedir.",
                "Güne başlarken şunu hatırla: Bugün zor insanlar, belirsizlik ve kaosla karşılaşabilirsin.",
                "Onların davranışı senin değerini değil; senin sabrını test eden bir zihinsel antrenmandır.",
                "Gerçek disiplin, iyi hissettiğinde değil; en çok dağılmak istediğinde doğru olanı seçmektir.",
                "Kriz anında panik yerine prosedür seç: Ne biliyorum, neyi değiştirebilirim, neyi serbest bırakmalıyım?",
                "Zihnini eğitmezsen, algoritmalar ve kaos senin yerine karar vermeye başlar.",
                f"Zihnini korumayı seçtiğinde, dışarıdaki hiçbir fırtına senin merkezini sarsamaz.",
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
                "Günün krizleri gelir ve geçer; fakat sergilediğin karakter hayat boyu seninle kalır.",
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


def _generate_religious_quotes_scenes(clean_title: str, is_tr: bool, variation_seed: int = 0):
    """Islamic dua/hadith fallback — mosque/Quran/prayer visuals, never stoic/Roman/idols."""
    topic = (clean_title or "").strip() or ("Günün duası" if is_tr else "Daily prayer")
    if is_tr:
        narrations = [
            f"Hz. Peygamber'in en çok tekrar ettiği o dua bugün {topic} ile hayatınıza dokunabilir, dinleyin.",
            "Bu dua sabah uyanınca okunur; kalbi yumuşatır, günü Allah'ın zikriyle açar ve içi ferahlatır.",
            "Hadis ehli nakleder: az söz, çok sevap. Kısa dua, samimi niyetle tekrar edilince bereket büyür.",
            "Cami avlusunda şafak ışığı varken eller açılır; dil tesbih çeker, gönül Rabbine yönelir.",
            "Ayet mealini saygıyla oku: her harf bir kapı açar, her amin bir sığınaktır dertlere karşı.",
            "Namazdan sonra üç kere okunan bu dua, günahı silmez iddiası değil; tevbe kapısını hatırlatır.",
            "Sahabe bu zikri yolda, evde, uykudan önce söylerdi; sünnet olan sürekliliktir, gösteriş asla olmaz.",
            "Kuran sayfası açık dururken acele etme; anlamı kalbe indir, sonra dili onunla konuştur.",
            "Dua etmek şikayet değildir. Kul aczini bilir, Rabbi kerimini bilir, aradaki bağ kopmaz.",
            "Bugün bir kez dur: ellerini kaldır, bu duayı oku, kalbindeki düğümü Allah'a bırak ve amin deyin.",
            "Yarın aynı saatte aynı dua; alışkanlık ibadeti taşır, taş kalbi yumuşatır, evi aydınlatır.",
            "Peki sen bu duayı kaç kez okudun? Yorumda amin yaz, döngü başa bağlansın kardeşlerim.",
        ]
    else:
        narrations = [
            f"The prayer the Prophet repeated most can still reshape a day around {topic}, listen closely.",
            "This dua is recited at dawn; it softens the heart and opens the morning with remembrance of God.",
            "Hadith scholars note: few words, great reward. A short prayer grows when the intention is sincere.",
            "Hands rise in a mosque courtyard at first light; the tongue remembers, the chest turns to the Lord.",
            "Read the verse meaning with respect: each letter is a door, each amin a shelter against hardship.",
            "After prayer this dua is said three times; it is not a magic wipe, it is a door to repentance.",
            "The companions repeated this dhikr at home and on the road; the sunnah is constancy, not display.",
            "When a Quran page is open, do not rush; let the meaning reach the heart, then let the tongue follow.",
            "Dua is not complaint. The servant knows his need, the Lord knows His generosity, the bond remains.",
            "Stop once today: raise your hands, recite this prayer, leave the knot in your chest with God, and say amin.",
            "Tomorrow the same hour, the same dua; habit carries worship, softens a hard heart, lights a home.",
            "How many times have you read this prayer? Write amin in the comments so the loop can restart.",
        ]
    visuals = [
        ("Mosque dome catching golden sunrise light, no people facing camera",
         ["mosque dome golden sunrise", "islamic architecture dawn", "minaret silhouette morning"]),
        ("Open Quran pages with soft window light, no faces",
         ["open quran pages soft light", "arabic manuscript closeup", "holy book still life"]),
        ("Prayer hands raised at dusk, cropped at wrists, respectful",
         ["prayer hands raised dusk", "open palms dua", "hands supplication sunset"]),
        ("Islamic geometric tile and gold calligraphy wall, no figurative idols",
         ["islamic geometric calligraphy", "arabesque tile pattern", "gold kufic art wall"]),
        ("Minaret silhouette against dawn sky and crescent",
         ["minaret silhouette dawn", "crescent moon mosque", "islamic skyline sunrise"]),
        ("Olive grove in peaceful morning mist, Mediterranean",
         ["olive grove peaceful morning", "mediterranean olive trees dawn", "calm orchard mist"]),
        ("Mosque interior lanterns glowing over empty prayer hall",
         ["mosque lantern interior glow", "prayer hall lamps", "islamic architecture interior"]),
        ("Courtyard fountain for ablution, water ripples, no faces",
         ["ablution water fountain courtyard", "mosque courtyard fountain", "wudu water closeup"]),
        ("Crescent moon above a distant mosque at night",
         ["crescent moon over mosque", "night sky islamic architecture", "ramadan night sky"]),
        ("Prayer rug still life with tasbih beads, no figurative art",
         ["prayer rug still life", "tasbih beads closeup", "islamic prayer mat detail"]),
        ("Desert dunes at calm sunrise, empty horizon",
         ["desert dunes sunrise calm", "golden sand sunrise aerial", "empty desert dawn"]),
        ("Close-up of Arabic calligraphy ink on paper, abstract letters only",
         ["arabic calligraphy closeup", "islamic calligraphy ink", "quranic script macro"]),
    ]
    moods = [
        "reverent", "hopeful", "peaceful", "solemn",
        "luminous", "calm", "warm", "contemplative",
        "hopeful", "reverent", "peaceful", "warm",
    ]
    shift = variation_seed % len(visuals)
    scenes = []
    for i, narr in enumerate(narrations):
        desc, queries = visuals[(i + shift) % len(visuals)]
        scenes.append({
            "scene_number": i + 1,
            "narration": narr,
            "scene_description": desc,
            "search_queries": queries,
            "duration": 4.5,
            "mood": moods[i % len(moods)],
            "beat_type": "hook" if i == 0 else "resolution" if i == len(narrations) - 1 else "conflict",
        })
    return {
        "title": topic if is_tr else f"Dua: {topic}",
        "visual_theme": "mosque quran prayer calligraphy sunrise respectful islamic",
        "full_narration": " ".join(narrations),
        "scenes": scenes,
        "niche_id": "10_religious_quotes",
        "procedural_fallback": True,
        "scenario_pack_family": "religious",
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


_SUBJECT_DROP = frozenset({
    "ama", "ve", "ile", "için", "icin", "bir", "bu", "şu", "su", "o", "da", "de",
    "mi", "mı", "mu", "mü", "çok", "cok", "en", "gibi", "diye", "olan", "olarak",
    "hakkında", "hakkinda", "konusunda", "size", "sen", "siz", "sizin",
    "öğretilmeyen", "ogretilmeyen", "bilmeniz", "gereken", "şok", "sok",
    "gerçek", "gercek", "bilgi", "kural", "sır", "sir", "tane", "büyük", "buyuk",
    "ilginç", "ilginc", "önemli", "onemli", "şaşırtıcı", "sasirtici", "inanılmaz",
    "inanilmaz", "facts", "fact", "shocking", "mind", "blowing", "the", "and",
    "you", "your", "about", "that", "this", "need", "know",
})


def _viewer_subject(clean_title: str) -> str:
    """Drop format words so narration talks about the subject, not the clickbait shell."""
    words = []
    for raw in (clean_title or "").split():
        token = raw.strip(".,!?'\"")
        if not token or token.isdigit():
            continue
        if token.casefold() in _SUBJECT_DROP:
            continue
        words.append(token)
    subject = " ".join(words[:6]).strip()
    return subject or (clean_title or "bu konu").strip()


def _subject_visuals(pack: dict, subject: str) -> list:
    bank = list(pack.get("subjects") or []) or [
        "library reading desk natural light",
        "open book pages close up",
        "researcher notes on a wooden desk",
        "quiet archive shelves",
    ]
    visuals = []
    for i in range(10):
        shot = bank[i % len(bank)]
        visuals.append((
            f"{shot} related to {subject}",
            [shot, f"{shot} close up", f"{shot} natural light"],
        ))
    return visuals


def _topic_bound_narrations(subject: str, is_tr: bool) -> list:
    """One subject, ten distinct beats. Natural human storytelling progression without mechanical repetitions."""
    if is_tr:
        return [
            f"{subject} deyince çoğu insanın aklına tek bir kalıp geliyor; oysa perde arkasında çok daha çarpıcı bir gerçek yatıyor.",
            "Genellikle ilk duyduğumuz bilgiler yüzeysel kalır ve asıl detayı gözden kaçırmamıza neden olur.",
            "Burada kritik nokta sadece görünen sonuç değil, o sonuca götüren görünmez adımlardır.",
            "Günlük hayatın akışı içinde küçük bir ayrıntı gibi dursa da, aslında bütün resmi baştan sona değiştirir.",
            f"Birçok insan bu noktada yanılıyor; çünkü {subject} dediğimiz durum, derinlerdeki başka bir sebebin doğrudan sonucudur.",
            "Bunu bir kez fark ettiğinizde, aynı konuya bir daha asla eski gözle bakamazsınız.",
            "İşin özü oldukça net: Yüzeysel gürültüye kapılmak yerine, asıl farkı yaratan o kilit noktaya odaklanmak gerekir.",
            "Bir dahaki sefere benzer bir iddia veya durumla karşılaştığınızda, hemen karar vermeden önce bu ayrımı hatırlayın.",
            "Çünkü en doğru bakış açısı aceleyle değil, meselenin kökenini sakince kavrayarak elde edilir.",
            "Ve işte tam bu yüzden, ilk başta basit görünen o ayrıntı, aslında tüm hikayenin en can alıcı noktasıydı.",
        ]
    return [
        f"When people mention {subject}, they usually reduce it to a simple label, but the real story runs much deeper.",
        "Most first impressions are incomplete, shaped by assumptions rather than what actually happened.",
        "The real insight is not the visible outcome, but the hidden sequence of events leading up to it.",
        "In everyday life it might look like a minor detail, yet that single element shifts the entire balance.",
        f"This is where the common narrative fails: what is called {subject} is actually the direct effect of a much larger cause.",
        "Once you grasp that dynamic, you can never look at this situation the same way again.",
        "The lesson is simple: cutting through the surface noise reveals what truly drives the outcome.",
        "Next time you encounter this claim, pause for a moment and compare it against the underlying facts.",
        "Because true understanding is never rushed; it comes from examining the quiet mechanics beneath the surface.",
        "And that is precisely why the detail everyone overlooked was the key all along.",
    ]


def _generate_pack_fallback_scenes(pack: dict, clean_title: str, is_tr: bool):
    """Topic-aware fallback. Speak about the subject. Never describe the generator."""
    topic = (clean_title or "").strip() or pack.get("name") or "Konu"
    subject = _viewer_subject(topic)
    narrations = _topic_bound_narrations(subject, is_tr)
    visuals = _subject_visuals(pack, subject)
    moods = ["urgent", "curious", "focused", "analytical", "mysterious", "tense", "calm", "bright", "reflective", "energetic"]
    scenes = []
    for i, narr in enumerate(narrations):
        desc, queries = visuals[i]
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
        "title": topic,
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
        elif any(k in combined for k in [
            "peygamber", "dua", "ayet", "hadis", "kuran", "kur'an",
            "allah", "namaz", "islam", "islâm", "sahabe", "sünnet", "ibadet", "dini",
        ]):
            resolved = "10_religious_quotes"
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
    if nid == "10_religious_quotes" or family == "religious":
        return _finalize_fallback_plan(
            _generate_religious_quotes_scenes(clean_title, is_tr, variation_seed=variation_seed),
            is_tr=is_tr,
        )
    if nid in ("6_stoic_philosophy",) or family == "stoic":
        return _finalize_fallback_plan(_generate_stoic_scenes(clean_title, is_tr, variation_seed=variation_seed), is_tr=is_tr)
    if nid == "7_dark_psychology" or family == "dark":
        return _finalize_fallback_plan(_generate_dark_psychology_scenes(clean_title, is_tr), is_tr=is_tr)
    if nid == "18_astrology_horoscope" or family == "astrology":
        return _finalize_fallback_plan(
            _generate_astrology_horoscope_scenes(clean_title, is_tr, variation_seed=variation_seed),
            is_tr=is_tr,
        )
    facts_shell = bool(re.search(r"\b(gerçek|gercek|facts|şok|sok)\b", f"{title} {clean_title}", re.I))
    if nid == "9_five_facts" and (niche_type == "9_five_facts" or facts_shell):
        return _finalize_fallback_plan(_generate_five_fact_scenes(clean_title, is_tr), is_tr=is_tr)
    return _finalize_fallback_plan(_generate_pack_fallback_scenes(pack, clean_title, is_tr), is_tr=is_tr)


def _generate_five_fact_scenes(clean_title: str, is_tr: bool) -> dict:
    """Five spoken facts. No title paste, no scroll warning, no fake quote."""
    topic = (clean_title or "").strip() or "5 gerçek"
    if is_tr:
        beats = [
            (
                "Beş ölçülmüş gerçek. Ders kitabı bunları çoğu zaman tek cümleyle geçirir.",
                "open textbook classroom desk",
                ["open textbook classroom", "library study desk", "students classroom"],
            ),
            (
                "Su, dört santigrat derecede en yoğundur. Sıfırda buz genleşir ve gölün üstünde kalır. Alttaki su dört derecede kalır, balık donmaz.",
                "frozen lake iceberg winter",
                ["frozen lake ice", "iceberg floating water", "winter lake close up"],
            ),
            (
                "Yetişkin insanda yaklaşık iki yüz altı kemik vardır. Sınıftaki iskelet modelinde bunu sayabilirsin. Bebekte sayı üç yüze yakındır, sonra bir kısmı kaynar.",
                "classroom skeleton model",
                ["classroom skeleton model", "human skeleton classroom", "anatomy model classroom"],
            ),
            (
                "Arı balı kapalı kavanozda yıllarca bozulmaz. İçindeki su çok azdır ve asittir. Bu ortamda bakteri üreyemez.",
                "honey jar bees flowers",
                ["honey jar close up", "bee on flower", "honey drip spoon"],
            ),
            (
                "Soluduğun oksijenin büyük kısmını okyanus planktonu üretir. Orman tek kaynak değildir. Deniz yüzeyi bu yüzden önemlidir.",
                "ocean waves surface plankton",
                ["ocean waves surface", "underwater deep sea", "sea surface aerial"],
            ),
            (
                "Yıldırım aynı noktaya birden fazla kez düşebilir. Şimşek yüksek ve metal uçları tekrar hedefler. Bir kez düştü diye o yer güvenli sayılmaz.",
                "storm lightning strike night",
                ["storm lightning", "lightning strike tower", "thunder storm sky"],
            ),
        ]
    else:
        beats = [
            (
                "Five measured facts. A textbook usually spends one sentence on each.",
                "open textbook classroom desk",
                ["open textbook classroom", "library study desk", "students classroom"],
            ),
            (
                "Water is densest at four degrees Celsius. Ice floats, so the fish below the lake do not freeze.",
                "frozen lake iceberg winter",
                ["frozen lake ice", "iceberg floating water", "winter lake close up"],
            ),
            (
                "An adult has about two hundred six bones. A newborn has closer to three hundred. Some fuse as you grow.",
                "classroom skeleton model",
                ["classroom skeleton model", "human skeleton classroom", "anatomy model classroom"],
            ),
            (
                "Sealed honey can last for years. It holds very little water and it is acidic, so bacteria cannot grow.",
                "honey jar bees flowers",
                ["honey jar close up", "bee on flower", "honey drip spoon"],
            ),
            (
                "Most of the oxygen you breathe comes from ocean plankton. Forests are not the only source.",
                "ocean waves surface plankton",
                ["ocean waves surface", "underwater deep sea", "sea surface aerial"],
            ),
            (
                "Lightning can strike the same spot more than once. A tall metal point stays a target.",
                "storm lightning strike night",
                ["storm lightning", "lightning strike tower", "thunder storm sky"],
            ),
        ]
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
