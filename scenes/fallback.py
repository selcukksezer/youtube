"""
Procedural and rule-based fallback scene generator when AI quotas or APIs are unavailable.
"""

import re
import config


def _detect_niche_and_terms(title: str):
    clean_title = re.sub(r'[^\w\s-]', '', title).strip()
    words = [w for w in clean_title.split() if len(w) > 2]
    main_kw = " ".join(words[:3]) if words else "epic facts"
    return clean_title, main_kw, words


def _generate_procedural_fallback_scenes(title: str, niche_type: str = None) -> dict:
    """
    Failsafe procedural scene generator when external AI models are inaccessible.
    Guarantees rich 60-second retention-friendly script structure.
    """
    clean_title, main_kw, words = _detect_niche_and_terms(title)
    is_tr = (config.LANGUAGE == "tr" or any(c in title for c in "çğıöşüÇĞİÖŞÜ") or any(w in title.lower() for w in ["tartışma", "ailemle", "itiraf", "hakkında"]))

    # Special handling for Reddit Confessions niche
    if niche_type == "2_reddit_confessions":
        if is_tr:
            narrations = [
                f"Bunu kimseye anlatamadım ama artık içimde tutamıyorum: {clean_title}.",
                "Her şey sıradan bir günde başladı, ancak aldığım bir mesaj tüm dengemi bozdu.",
                "O an neye uğradığımı şaşırdım ve hissettiğim şüphe içimi kemirmeye başladı.",
                "Gerçeği öğrenmek için biraz araştırma yaptım ve karşılaştığım şey kanımı dondurdu.",
                "En yakınlarımdan birinin arkamdan böylesine bir oyun çevirdiğini hayal bile edemezdim.",
                "Yüzleşme anı geldiğinde inkâr etmeye çalıştılar ama tüm kanıtlar ortadaydı.",
                "Şimdi hayatımın en zor dönüm noktasındayım ve kimseye güvenemiyorum.",
                "Siz olsaydınız bu durumda ne yapardınız? Yorumlarda buluşalım ve abone olmayı unutmayın!"
            ]
        else:
            narrations = [
                f"Bunu or I could never tell anyone this until now: {clean_title}.",
                "It all started innocently, but one unexpected message turned everything upside down.",
                "I was frozen in disbelief as deep suspicion began eating away at me.",
                "I decided to dig deeper, and the evidence I uncovered sent shivers down my spine.",
                "I never imagined someone so close could orchestrate such betrayal behind my back.",
                "When the confrontation happened, they tried to deny it, but the proof was undeniable.",
                "Now I am standing at a crossroads, questioning who I can really trust.",
                "What would you do if you were in my shoes? Let me know in the comments and subscribe!"
            ]

        scenes = []
        for i, text in enumerate(narrations):
            scenes.append({
                "scene_number": i + 1,
                "narration": text,
                "scene_description": f"Cinematic scene reflecting confession and emotional dilemma {i+1}",
                "search_queries": [f"{main_kw} mysterious", "thinking emotion face", "dark cinematic drama"],
                "duration": round(60.0 / len(narrations), 1),
                "mood": "mysterious" if i % 2 == 0 else "dramatic"
            })

        full_narration = " ".join(narrations)
        return {
            "title": clean_title,
            "visual_theme": "dark emotional cinematic moody confession",
            "full_narration": full_narration,
            "scenes": scenes
        }

    # Standard general fallback
    topics_tr = [
        f"Bugün sizlere {clean_title} hakkında bilinmeyen büyüleyici detayları aktarıyoruz.",
        "İlk olarak, çoğu insanın farkında bile olmadığı şaşırtıcı bir gerçekle başlayalım.",
        "Araştırmacılar ve bilim insanları bu durumun ardındaki sırrı uzun süredir çözmeye çalışıyor.",
        "Olayın derinine indiğimizde karşımıza çıkan ilk ipucu tüm dengeleri tamamen değiştiriyor.",
        "Gözden kaçan en kritik nokta, bu durumun günlük hayatımız üzerindeki doğrudan etkisidir.",
        "Şimdiye kadar bildiğiniz tüm kalıpları yıkacak olan bu detay gerçekten inanılmaz.",
        "Uzmanların yaptığı son analizler, beklenenden çok daha derin bir tablo ortaya koyuyor.",
        "Gelişmeler devam ettikçe ortaya çıkan yeni kanıtlar izleyenleri hayrete düşürüyor.",
        "Tüm bu parçaları birleştirdiğimizde gerçeğin bambaşka bir boyutta olduğunu görüyoruz.",
        "Peki siz bu konuda ne düşünüyorsunuz? Yorumlarda buluşalım ve takip etmeyi unutmayın!"
    ]

    topics_en = [
        f"Today we are exploring mind-blowing facts about {clean_title}.",
        "Let's begin with an astonishing detail that most people have never heard of.",
        "Scientists and researchers have been investigating the secret behind this for years.",
        "When looking deeper, the first hidden clue completely changes our perspective.",
        "The most critical point is the profound impact this has on the world around us.",
        "This surprising revelation challenges everything you thought you previously knew.",
        "Recent in-depth analysis uncovers a far more intriguing picture than expected.",
        "As we uncover more evidence, the true scope of this reality becomes unmistakable.",
        "Connecting all the dots proves that truth is truly stranger than fiction.",
        "What do you think about this? Let us know in the comments and subscribe for more!"
    ]

    narrations = topics_tr if is_tr else topics_en
    search_queries_list = [
        [f"{main_kw} cinematic", f"{main_kw} landscape", "cinematic slow motion"],
        [f"{main_kw} reveal", "mystery dark atmosphere", "dramatic lighting"],
        ["science laboratory research", "data technology abstract", "futuristic concept"],
        ["deep discovery investigation", "aerial drone nature", "ancient mystery"],
        ["modern civilization city", "human mind psychology", "abstract motion"],
        ["shocking discovery revelation", "explosion of light", "epic cinematic view"],
        ["detailed analysis research", "magnifying glass inspection", "digital data stream"],
        ["unbelievable truth concept", "space galaxy universe", "deep ocean mystery"],
        ["connecting elements puzzle", "light rays cinematic", "epic sunset drone"],
        ["social media engagement", "like subscribe bell", "cinematic ending landscape"]
    ]

    scenes = []
    for i in range(10):
        scenes.append({
            "scene_number": i + 1,
            "narration": narrations[i],
            "scene_description": f"Cinematic footage showing {search_queries_list[i][0]} with dramatic lighting",
            "search_queries": search_queries_list[i],
            "duration": 6,
            "mood": "epic" if i in (0, 5, 8) else "mysterious" if i in (1, 3, 7) else "energetic"
        })

    full_narration = " ".join(narrations)
    return {
        "title": clean_title,
        "visual_theme": "cinematic documentary dark and bright highlights",
        "full_narration": full_narration,
        "scenes": scenes
    }
