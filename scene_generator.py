"""
Scene generator — produces narration + per-scene search context.
Each scene gets: narration, 3 search queries, AND a scene_description
so the video fetcher can match content intelligently.
"""
import json, re, time
from openai import OpenAI
import config

PROMPT_TR = """Sen profesyonel bir YouTube Shorts senaristi ve seslendirme yazarısın.
Verilen başlık için:

1. Türkçe anlatım metni yaz (EN AZ 140-180 KELİME, KAPSAMLI VE DETAYLI ANLATIM, 60-90 SANİYE SÜRECEK. KISA TUTMA!).

2. 10-16 sahne oluştur (her biri 5-7 sn). TOPLAM EN AZ 60 SANİYE.
   Her sahne:
   - "narration": Türkçe anlatım parçası (her sahne için 10-15 kelimelik zengin açıklama)
   - "scene_description": Bu sahnede İZLEYİCİNİN GÖRMESİ GEREKEN görsel, İngilizce, 1 cümle (örn: "Aerial view of a massive ocean wave crashing against rocky cliffs at sunset")
   - "search_queries": 3 İngilizce stok video arama terimi [spesifik, orta, genel]
   - "duration": 5-7
   - "mood": epic/calm/dramatic/mysterious/energetic/dark/bright

3. search_queries kuralları:
   İYİ: "ocean waves aerial", "mountain fog drone", "city skyline night", "stars night sky"
   KÖTÜ: fantastik isimler, 4+ kelime, metin/grafik içeren terimler
   HER SAHNE FARKLI arama terimleri kullanmalı. TEKRAR YASAK.

4. scene_description çok önemli — video seçici buna bakarak en uygun videoyu seçecek.

SADECE JSON:
{"title":"...","visual_theme":"...","full_narration":"...","scenes":[{"scene_number":1,"narration":"...","scene_description":"...","search_queries":["a","b","c"],"duration":6,"mood":"epic"}]}"""

PROMPT_EN = """You are a professional YouTube Shorts scriptwriter.
For the given title:

1. Write English narration (AT LEAST 140-180 words, DETAILED AND COMPREHENSIVE, 60-90 SECONDS DURATION. DO NOT MAKE IT SHORT!).

2. Create 10-16 scenes (5-7s each). TOTAL AT LEAST 60 SECONDS.
   Each scene:
   - "narration": English narration fragment (10-15 words per scene)
   - "scene_description": What the VIEWER SHOULD SEE, 1 sentence in English (e.g., "Aerial view of a massive ocean wave crashing against rocky cliffs at sunset")
   - "search_queries": 3 English stock video search terms [specific, medium, general]
   - "duration": 5-7
   - "mood": epic/calm/dramatic/mysterious/energetic/dark/bright

3. search_queries rules:
   GOOD: "ocean waves aerial", "mountain fog drone", "city skyline night", "stars night sky"
   BAD: fantasy names, 4+ words, text/graphic terms
   EVERY scene MUST have DIFFERENT search terms. NO REPEATS.

4. scene_description is critical — the video selector uses it to find the best matching footage.

ONLY JSON:
{"title":"...","visual_theme":"...","full_narration":"...","scenes":[{"scene_number":1,"narration":"...","scene_description":"...","search_queries":["a","b","c"],"duration":6,"mood":"epic"}]}"""


def _call(client, params, retries=2):
    for i in range(retries):
        try:
            return client.chat.completions.create(**params)
        except Exception as e:
            err_str = str(e).lower()
            if "resource_exhausted" in err_str or "quota exceeded" in err_str:
                print(f"  [AI Kota Limiti] Günlük kota aşıldı: {e}. Diğer modele/sağlayıcıya geçiliyor...")
                raise
            elif "429" in str(e):
                w = 3 * (i + 1)
                print(f"  [Geçici Hız Limiti] {w}s bekleniyor...")
                time.sleep(w)
            else:
                raise
    raise RuntimeError("API rate limit exceeded")


def _clean_json(raw):
    try:
        return json.loads(raw)
    except:
        pass
    raw = re.sub(r'//[^\n]*', '', raw)
    raw = re.sub(r',\s*([}\]])', r'\1', raw)
    try:
        return json.loads(raw)
    except:
        pass
    s = raw.find('{')
    if s == -1: return None
    depth = 0
    for i in range(s, len(raw)):
        if raw[i] == '{': depth += 1
        elif raw[i] == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[s:i+1])
                except:
                    break
    t = raw[s:]
    t += ']' * (t.count('[') - t.count(']'))
    t += '}' * (t.count('{') - t.count('}'))
    try:
        return json.loads(t)
    except:
        return None

def _generate_procedural_fallback_scenes(title: str) -> dict:
    """
    Failsafe: Generates a complete 10-scene, 60-second video plan 
    when all external AI API quotas are exhausted or unreachable.
    Guarantees the system NEVER crashes and user can always create videos.
    """
    clean_title = re.sub(r'[^\w\s-]', '', title).strip()
    words = [w for w in clean_title.split() if len(w) > 2]
    main_kw = " ".join(words[:3]) if words else "epic facts"

    print(f"  [Failsafe Senaryo Motoru] AI kotaları dolu, başlık için akıllı senaryo üretiliyor: '{clean_title}'")
    
    is_tr = (config.LANGUAGE == "tr")
    
    scenes = []
    # Dynamic 10 scenes (6s each = 60s)
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


def generate_scenes(title: str) -> dict:
    prompt = PROMPT_TR if config.LANGUAGE == "tr" else PROMPT_EN
    user_msg = f"Bu başlık için senaryo oluştur: {title}" if config.LANGUAGE == "tr" else f"Create a video script for: {title}"

    # Build fallback provider chain
    providers = []
    # Primary configured provider first
    if config.AI_PROVIDER and config.AI_API_KEY:
        providers.append((config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL))
        # If Gemini, add lite and flash variants as instant fallbacks
        if config.AI_PROVIDER == "Gemini":
            for alt_m in ["gemini-flash-lite-latest", "gemma-4-26b-a4b-it", "gemini-3.6-flash"]:
                if alt_m != config.AI_MODEL:
                    providers.append(("Gemini (" + alt_m + ")", config.AI_API_KEY, config.AI_BASE_URL, alt_m))

    # Other available providers in config._P
    for n, k, u, m in config._P:
        if k and (n != config.AI_PROVIDER):
            providers.append((n, k, u, m))

    last_error = None
    data = None

    for provider_name, api_key, base_url, model_name in providers:
        print(f"  [{provider_name}] Senaryo üretiliyor: '{title}'")
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            params = dict(
                model=model_name,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}],
                temperature=0.7, max_tokens=4000,
            )
            if "Gemini" in provider_name or "OpenAI" in provider_name:
                params["response_format"] = {"type": "json_object"}

            resp = _call(client, params)
            raw = resp.choices[0].message.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            data = _clean_json(raw)
            if not data:
                print(f"  [{provider_name}] JSON ayrıştırma başarısız, retrying...")
                params["temperature"] = 0.3
                resp2 = _call(client, params)
                raw2 = resp2.choices[0].message.content.strip()
                if "```" in raw2:
                    raw2 = raw2.split("```json")[-1].split("```")[0].strip() if "```json" in raw2 else raw2.split("```")[1].split("```")[0].strip()
                data = _clean_json(raw2)

            if data and "scenes" in data and len(data["scenes"]) > 0:
                print(f"  [{provider_name}] OK: Senaryo basariyla uretildi")
                break
        except Exception as e:
            print(f"  [UYARI] {provider_name} servisi hata verdi: {e}. Sıradaki AI modeline/sağlayıcısına geçiliyor...")
            last_error = e

    if not data or not data.get("scenes"):
        print(f"  [BİLGİ] AI servisleri yanıt vermedi ({last_error}). Akıllı Prosedürel Senaryo Motoru devreye alındı.")
        data = _generate_procedural_fallback_scenes(title)

    for s in data.get("scenes", []):
        if "search_query" in s and "search_queries" not in s:
            q = s.pop("search_query")
            w = q.split()
            s["search_queries"] = [q, " ".join(w[:2]) if len(w) > 2 else q, w[0] if w else "nature"]
        if "scene_description" not in s:
            s["scene_description"] = s.get("search_queries", ["nature"])[0]

    total = sum(s["duration"] for s in data["scenes"])
    print(f"  [{config.AI_PROVIDER}] {len(data['scenes'])} scenes, {total}s")

    if total < config.MIN_DURATION:
        for s in data["scenes"]:
            s["duration"] = min(int(s["duration"] * config.MIN_DURATION / total), config.SCENE_CLIP_MAX)
    elif total > config.MAX_DURATION:
        for s in data["scenes"]:
            s["duration"] = max(int(s["duration"] * config.MAX_DURATION / total), config.SCENE_CLIP_MIN)

    total = sum(s["duration"] for s in data["scenes"])
    print(f"  [{config.AI_PROVIDER}] Adjusted: {total}s | Theme: {data.get('visual_theme', '-')}")
    return data
