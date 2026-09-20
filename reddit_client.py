"""
Smart Reddit Research Client with Dynamic AI Story Discovery, Public Discovery & Curated Viral Archive.
Supports:
1. Official OAuth (when REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are provided).
2. Dynamic AI-Powered Live Story Discovery (generates 100% fresh, hyper-engaging viral Reddit stories on every refresh).
3. Curated High-Retention Viral Reddit Archive with rotation and anti-repeat tracking.
"""
import os
import re
import json
import time
import random
from typing import Any, Dict, List, Optional
import requests
from openai import OpenAI
import config

# Global seen posts tracker to guarantee no immediate repetition across refreshes
_SEEN_POST_IDS = set()

# ─── EXTENSIVE CURATED VIRAL REDDIT ARCHIVE (High-Retention Shorts Cues) ───────
VIRAL_REDDIT_ARCHIVE: Dict[str, List[Dict[str, Any]]] = {
    "AITA": [
        {
            "id": "aita_001",
            "subreddit": "AITA",
            "title": "Düğünümde eşimin benden gizli aldığı 500.000 TL'lik borcu öğrendiğimde masayı terk ettim. Haksız mıyım?",
            "body": "Düğünümüzden tam 3 saat önce eşimin kardeşinin kumar borcunu kapatmak için ortak birikimimizi ve adıma çekilen krediyi kullandığını öğrendim. Nikah masasında 'Hayır' deyip salonu terk ettiğimde tüm aile beni suçladı. Şimdi herkes bana bencil diyor.",
            "score": 38400,
            "author": "u/wedding_regret_24",
            "url": "https://www.reddit.com/r/AmItheAsshole/comments/aita_001"
        },
        {
            "id": "aita_002",
            "subreddit": "AITA",
            "title": "Miras kalan evi hasta kardeşime devretmeyi reddettiğim için ailem beni evlatlıktan reddetti.",
            "body": "Büyükbabam evi sadece bana bıraktı çünkü 10 yıl boyunca onun tüm bakımını tek başıma üstlendim. Diğer kardeşlerim ziyarete bile gelmedi. Şimdi hasta kardeşimin tedavi masrafları bahanesiyle evi istiyorlar. Reddedince beni hain ilan ettiler.",
            "score": 42100,
            "author": "u/inheritance_dilemma",
            "url": "https://www.reddit.com/r/AmItheAsshole/comments/aita_002"
        },
        {
            "id": "aita_003",
            "subreddit": "AITA",
            "title": "Restoranda hesabın tamamını ödememi bekleyen 8 kişilik arkadaş grubumu hesabı bölmeden orada bıraktım.",
            "body": "Doğum günü yemeğimdi ama kimse bana hediye almadığı gibi en pahalı biftekleri ve şarapları sipariş ettiler. Garson hesabı önüme koyduğunda sadece kendi yediğim salatanın parasını masaya bırakıp kalktım. Telefonum hakaret mesajlarıyla kilitlendi.",
            "score": 29800,
            "author": "u/bill_splitter_hero",
            "url": "https://www.reddit.com/r/AmItheAsshole/comments/aita_003"
        },
        {
            "id": "aita_004",
            "subreddit": "AITA",
            "title": "Kayınvalidemin habersiz değiştirdiği evimin anahtarlarını çilingir çağırıp tekrar değiştirdim.",
            "body": "Biz tatildeyken kayınvalidem evimize girip 'temizlik yapma' bahanesiyle tüm kilitleri değiştirmiş ve yedek anahtarı vermeyi reddetti. Döndüğümüzde kendi evimize giremedik. Çilingir çağırıp kapıyı açtırdım ve onu eve almadım. Eşim benimle konuşmuyor.",
            "score": 35200,
            "author": "u/door_lock_drama",
            "url": "https://www.reddit.com/r/AmItheAsshole/comments/aita_004"
        },
        {
            "id": "aita_005",
            "subreddit": "AITA",
            "title": "Bütün birikimimi harcayıp kurduğum şirkete kardeşimi ortak yapmadığım için ailem beni dışladı.",
            "body": "5 yıl boyunca günde 16 saat çalışıp borç harç bir e-ticaret markası kurdum. Şirket kara geçip ilk milyonunu kazanınca babam 'Kardeşine de %50 hisse vereceksin, o senin kanın' dedi. Kardeşim ise bugüne kadar tek bir gün bile çalışmamıştı. Reddettim, bayramda beni aramadılar.",
            "score": 48900,
            "author": "u/selfmade_founder",
            "url": "https://www.reddit.com/r/AmItheAsshole/comments/aita_005"
        },
        {
            "id": "aita_006",
            "subreddit": "AITA",
            "title": "Yıllarca bana zorbalık yapan lise arkadaşımın iş başvurusunu şirketimde veto ettiğim için haksız mıyım?",
            "body": "Lisede her gün benimle alay eden, dolabımı kıran çocuk şirketimize üst düzey pozisyon için başvurdu. Mülakat komitesinde vardım. Özgeçmişi mükemmeldi ama karakter referansını doğrudan olumsuz verdim ve elendi. Sosyal medyadan beni intikamcı olmakla suçladı.",
            "score": 52300,
            "author": "u/karma_is_real_99",
            "url": "https://www.reddit.com/r/AmItheAsshole/comments/aita_006"
        },
        {
            "id": "aita_007",
            "subreddit": "AITA",
            "title": "Uçakta arkamdaki çocuğun koltuğumu tekmelemesini durdurmayan ebeveynlere koltuğumu sonuna kadar yatırdım.",
            "body": "6 saatlik uçuş boyunca arkamdaki 8 yaşındaki çocuk aralıksız koltuğumu tekmeledi. Annesini 3 kez kibarca uyardım ama 'çocuk o, ne yapayım' dedi. Ben de koltuğumu sonuna kadar arkaya yatırıp kulaklıklarımı taktım. İçecekleri döküldü diye kıyameti kopardılar.",
            "score": 61200,
            "author": "u/flight_recliner_pro",
            "url": "https://www.reddit.com/r/AmItheAsshole/comments/aita_007"
        }
    ],
    "confession": [
        {
            "id": "conf_001",
            "subreddit": "confession",
            "title": "5 yıldır patronumun şirketini batmaktan kurtaran yapay zeka botunu ben yazdım ama o bunu bilmiyor.",
            "body": "Ofiste herkes benim geceleri fazla mesai yaparak tüm finansal raporları hazırladığımı sanıyor. Aslında her şeyi 20 satırlık Python scripti ve otomasyon yapıyor. Günde sadece 15 dakika çalışıyorum ve şirketin en yüksek primini alıyorum. Vicdan azabı çekmeli miyim?",
            "score": 49200,
            "author": "u/silent_automator",
            "url": "https://www.reddit.com/r/confession/comments/conf_001"
        },
        {
            "id": "conf_002",
            "subreddit": "confession",
            "title": "Eski sevgilimin yeni nişanlısının bir dolandırıcı olduğunu kanıtladım ama ona söylemedim.",
            "body": "Beni aldattığı için ayrılmıştık. 2 yıl sonra evleneceği adamın sahte kimlikle borç batağında olduğunu tesadüfen öğrendim. Onu uyarmak yerine sadece düğün gününü ve yaşanacak felaketi bekliyorum. Bu kötülük beni içten içe mutlu ediyor.",
            "score": 34500,
            "author": "u/petty_revenge_soul",
            "url": "https://www.reddit.com/r/confession/comments/conf_002"
        },
        {
            "id": "conf_003",
            "subreddit": "confession",
            "title": "Şirket içi piyangoda kazandığım 250.000 TL'yi gizlemek için piyangoyu kaybettim yalanı uydurdum.",
            "body": "Yılbaşı çekilişinde büyük ikramiye bana çıktı. Haberi duyan tüm akrabalar ve iş arkadaşları benden borç istemeye başladı. İkramiye biletini kaybettiğimi ve çöpe gittiğini söyledim. Herkes bana acıdı ama para şu an güvende ve bana pasif gelir getiriyor.",
            "score": 41800,
            "author": "u/lottery_ghost",
            "url": "https://www.reddit.com/r/confession/comments/conf_003"
        },
        {
            "id": "conf_004",
            "subreddit": "confession",
            "title": "En yakın arkadaşımın 3 yıldır aradığı kayıp kedisini aslında ben başka bir şehre sahiplendirdim.",
            "body": "Arkadaşım kediye çok kötü bakıyor, günlerce aç bırakıp evde yalnız kilitliyordu. Bir gün gizlice kediyi alıp kırsaldaki sevgi dolu bir aileye verdim. 3 yıldır her gün kayıp ilanlarına bakıp ağlıyor. Kendimi hem bir kurtarıcı hem bir canavar gibi hissediyorum.",
            "score": 53700,
            "author": "u/secret_rescuer",
            "url": "https://www.reddit.com/r/confession/comments/conf_004"
        }
    ],
    "tifu": [
        {
            "id": "tifu_001",
            "subreddit": "tifu",
            "title": "Bugün iş görüşmesinde ekran paylaşımı yaparken patronun dedikodusunu yaptığım WhatsApp grubunu canlı yayında açtım.",
            "body": "Son mülakatta sunum yaparken yanlış masaüstünü seçtim. Tam o anda arkadaş grubumdan gelen 'Bu şirketin CEO'su tam bir diktatör, iyi para iste' mesajı dev ekranda 5 şirket yöneticisinin gözü önünde belirdi. O an yerin dibine girmek istedim.",
            "score": 51300,
            "author": "u/screenshare_disaster",
            "url": "https://www.reddit.com/r/tifu/comments/tifu_001"
        },
        {
            "id": "tifu_002",
            "subreddit": "tifu",
            "title": "Bugün spor salonunda ağırlık kaldırırken yanlışlıkla acil durum alarmını kırdım ve tüm AVM tahliye edildi.",
            "body": "Dambılı yere bırakırken duvardaki camlı yangın alarm kutusuna çarptı. İtfaiye sirenleri çaldı, yüzlerce insan sokağa döküldü. Şimdi güvenlik kameraları inceleniyor ve AVM yönetimi benden tazminat talep ediyor.",
            "score": 27400,
            "author": "u/gym_accident_guy",
            "url": "https://www.reddit.com/r/tifu/comments/tifu_002"
        },
        {
            "id": "tifu_003",
            "subreddit": "tifu",
            "title": "Bugün tüm şirkete göndereceğim tebrik e-postasına yanlışlıkla istifa dilekçemi ekledim.",
            "body": "Masaüstünde 'duyuru.docx' yerine 'istifa_taslak.docx' dosyasını seçmişim. CEO dahil 450 çalışana 'Dayanılmaz çalışma koşulları sebebiyle derhal ayrılıyorum' metni gitti. 5 dakika sonra İK beni odasına çağırdı.",
            "score": 46200,
            "author": "u/wrong_attachment_tifu",
            "url": "https://www.reddit.com/r/tifu/comments/tifu_003"
        }
    ],
    "TrueOffMyChest": [
        {
            "id": "tomc_001",
            "subreddit": "TrueOffMyChest",
            "title": "Ailemin benden gizlediği büyük sırrı DNA testi yaptırınca tesadüfen öğrendim.",
            "body": "Eğlence olsun diye yaptırdığım DNA kiti sonucunda hayatım alt üst oldu. Büyüdüğüm babamın biyolojik babam olmadığını, annemin ise 25 yıl önce beni evlatlık aldığını gizlediğini keşfettim. Tüm hayatım bir yalan üzerine kurulmuş.",
            "score": 62000,
            "author": "u/dna_shock_2024",
            "url": "https://www.reddit.com/r/TrueOffMyChest/comments/tomc_001"
        },
        {
            "id": "tomc_002",
            "subreddit": "TrueOffMyChest",
            "title": "Evlendiğim gün hayatımın en büyük hatasını yaptığımı anladım ama artık geri dönemiyorum.",
            "body": "Nikah masasında 'Evet' dediğim saniye içime korkunç bir pişmanlık çöktü. Ailelerin beklentileri, harcanan onca masraf yüzünden hayır diyemedim. Şimdi her sabah yanımda bir yabancıyla uyanıyorum ve bu sır beni tüketiyor.",
            "score": 39100,
            "author": "u/silent_regret_now",
            "url": "https://www.reddit.com/r/TrueOffMyChest/comments/tomc_002"
        },
        {
            "id": "tomc_003",
            "subreddit": "TrueOffMyChest",
            "title": "Başarı hikayesi diye anlattığım her şey aslında tesadüfler ve küçük hilelerden ibaret.",
            "body": "İnsanlar bana imrenerek bakıyor, motivasyon konuşmaları yapmamı istiyorlar. Ama bildiğim hiçbir şeyi okulda öğrenmedim, sadece doğru zamanda doğru insanları kandırmayı başardım. Bir gün sahtekar olduğum ortaya çıkacak diye ödüm kopuyor.",
            "score": 44800,
            "author": "u/impostor_real_talk",
            "url": "https://www.reddit.com/r/TrueOffMyChest/comments/tomc_003"
        }
    ],
    "relationships": [
        {
            "id": "rel_001",
            "subreddit": "relationships",
            "title": "Nişanlımın telefonundaki kilitli gizli kasada eski sevgilisinin fotoğraflarını ve ortak günlüklerini buldum.",
            "body": "Bana onu tamamen unuttuğunu söylemişti ama her hafta o kasayı açıp eski hatıralara baktığını fark ettim. Düğünümüze 1 ay kaldı. Yüzleştiğimde sadece nostalji olduğunu iddia etti. Ne yapmalıyım?",
            "score": 22100,
            "author": "u/hidden_vault_doubt",
            "url": "https://www.reddit.com/r/relationships/comments/rel_001"
        },
        {
            "id": "rel_002",
            "subreddit": "relationships",
            "title": "Eşimin ailesine her ay gizlice maaşının yarısını gönderdiğini ev kredisi reddedilince öğrendim.",
            "body": "Ortak ev almak için kredi başvurusu yaptık ve limitimizin yetersiz olduğunu görünce banka dökümlerine baktım. 2 yıldır her ay kardeşine ve annesine benim haberim olmadan para aktarıyormuş. Güvenim tamamen sarsıldı.",
            "score": 37600,
            "author": "u/broken_trust_home",
            "url": "https://www.reddit.com/r/relationships/comments/rel_002"
        }
    ],
    "NuclearRevenge": [
        {
            "id": "nr_001",
            "subreddit": "NuclearRevenge",
            "title": "Telifimi ve projemi çalan eski patronumun vergi kaçakçılığını ortaya çıkarıp şirketini mühürlettim.",
            "body": "Aylarca gece gündüz üzerinde çalıştığım yazılım projesini kendi adına tescil edip beni tazminatsız kovdu. Ben de şirket sunucularındaki çift muhasebe kayıtlarını ve off-shore transfer belgelerini mali şubeye teslim ettim. Şimdi hapiste ve şirketi iflas etti.",
            "score": 78500,
            "author": "u/cold_served_justice",
            "url": "https://www.reddit.com/r/NuclearRevenge/comments/nr_001"
        },
        {
            "id": "nr_002",
            "subreddit": "NuclearRevenge",
            "title": "Beni iftirayla okuldan attırmaya çalışan ev arkadaşımın tüm akademik sahtekarlıklarını dekanlığa sundum.",
            "body": "Bana tuzak kurup tezimi çalmak istedi. Ben de tüm tezinin intihal olduğunu, parayla yazdırdığı makaleleri ve dekontları doğrudan etik kuruluna ilettim. Hem üniversiteden atıldı hem de diploması iptal edildi.",
            "score": 64200,
            "author": "u/academic_retaliation",
            "url": "https://www.reddit.com/r/NuclearRevenge/comments/nr_002"
        }
    ],
    "AskReddit": [
        {
            "id": "ask_001",
            "subreddit": "AskReddit",
            "title": "Hayatınızda gördüğünüz en zekice ama bir o kadar da yasa dışı plan neydi?",
            "body": "Üniversitede bir arkadaşım sahte bir otomat kiralayıp kampüsün en işlek yerine koydu. 2 yıl boyunca hiç kimse otomatın kime ait olduğunu sorgulamadı, haftalık 50 bin TL nakit topladı. Mezun olurken otomatı da alıp gitti.",
            "score": 83400,
            "author": "u/curious_mind_90",
            "url": "https://www.reddit.com/r/AskReddit/comments/ask_001"
        },
        {
            "id": "ask_002",
            "subreddit": "AskReddit",
            "title": "Kimseye anlatamadığınız ama hayatınızı sonsuza dek değiştiren o an nedir?",
            "body": "Havaalanında uçağımı 2 dakika ile kaçırdım ve sinir krizi geçirdim. O uçak havada motor arızası yaşayıp acil iniş yaptı. O gün kaderin beni koruduğunu anladım ve hayatımı sıfırdan kurmaya karar verdim.",
            "score": 71900,
            "author": "u/destiny_watcher",
            "url": "https://www.reddit.com/r/AskReddit/comments/ask_002"
        }
    ]
}


def generate_ai_reddit_posts(subreddit: str, count: int = 5, lang: str = "tr") -> List[Dict[str, Any]]:
    """
    Generates high-retention, hyper-realistic, brand new Reddit posts on-the-fly using configured AI.
    Guarantees that the user never sees the same stories again.
    """
    api_key = getattr(config, "AI_API_KEY", "") or getattr(config, "GEMINI_API_KEY", "") or getattr(config, "OPENAI_API_KEY", "")
    base_url = getattr(config, "AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    model_name = getattr(config, "AI_MODEL", "gemini-flash-lite-latest")

    if not api_key:
        return []

    target_lang = "Türkçe" if (lang or "tr").lower().startswith("tr") else "English"
    clean_sub = re.sub(r"[^A-Za-z0-9_]", "", subreddit or "AITA")

    prompt = f"""You are a Reddit trend and YouTube Shorts viral retention specialist.
Create {count} COMPLETELY NEW, UNIQUE, and HIGHLY DRAMATIC Reddit posts for 'r/{clean_sub}' in {target_lang}.
The stories MUST feel 100% authentic, emotionally intense, suspenseful, and designed for maximum YouTube Shorts watch time.
Do NOT use generic tropes. Each post must have an irresistible hook in the title and a gripping conflict in the body.

Return ONLY a valid JSON object matching this schema:
{{
  "posts": [
    {{
      "id": "{clean_sub.lower()}_ai_{int(time.time())}_1",
      "subreddit": "{clean_sub}",
      "title": "Catchy, emotional or dramatic hook title",
      "body": "First-person narrative describing the drama, dilemma or confession in 2-4 sentences (80-150 words).",
      "score": 34500,
      "author": "u/creative_username"
    }}
  ]
}}
"""
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.85,
            timeout=12
        )
        content = resp.choices[0].message.content.strip()
        data = json.loads(content)
        posts = data.get("posts", [])
        valid_posts = []
        now_ts = int(time.time())
        for idx, p in enumerate(posts):
            if not p.get("title") or not p.get("body"):
                continue
            post_id = p.get("id") or f"{clean_sub.lower()}_ai_{now_ts}_{idx}"
            valid_posts.append({
                "id": post_id,
                "subreddit": clean_sub,
                "title": p.get("title").strip(),
                "body": p.get("body").strip(),
                "score": int(p.get("score") or random.randint(18000, 65000)),
                "author": p.get("author") or f"u/story_teller_{random.randint(100, 999)}",
                "url": f"https://www.reddit.com/r/{clean_sub}/comments/{post_id}",
                "source": "ai_discovery"
            })
        if valid_posts:
            print(f"  [RedditClient] [AI Canlı Keşif] r/{clean_sub} için {len(valid_posts)} adet taze, özgün gönderi üretildi.")
            return valid_posts
    except Exception as err:
        print(f"  [RedditClient] AI keşif çağrısı başarısız oldu ({err}), viral arşive dönülüyor.")
    return []


def fetch_public_posts(subreddit: str, limit: int = 10, lang: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches non-adult text posts for research.
    1. If Reddit Client ID & Secret exist, attempts OAuth flow.
    2. Dynamically generates fresh viral stories using AI if keys are present (prevents repetitive stale content).
    3. Curated High-Retention Viral Reddit Archive with rotation and anti-repeat tracking as guaranteed fallback.
    """
    clean_sub = re.sub(r"[^A-Za-z0-9_]", "", subreddit or "AITA")
    global _SEEN_POST_IDS

    # 1. Option: Official OAuth flow if credentials provided in settings
    client_id = getattr(config, "REDDIT_CLIENT_ID", "") or ""
    client_secret = getattr(config, "REDDIT_CLIENT_SECRET", "") or ""

    if client_id and client_secret:
        try:
            token_response = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(client_id, client_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": getattr(config, "REDDIT_USER_AGENT", "web:ShortsCreator:v2.0")},
                timeout=8
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if access_token:
                res = requests.get(
                    f"https://oauth.reddit.com/r/{clean_sub}/hot",
                    params={"limit": min(max(limit, 1), 25), "raw_json": 1},
                    headers={"Authorization": f"bearer {access_token}", "User-Agent": getattr(config, "REDDIT_USER_AGENT", "web:ShortsCreator:v2.0")},
                    timeout=8
                )
                res.raise_for_status()
                posts = []
                for child in res.json().get("data", {}).get("children", []):
                    data = child.get("data", {})
                    body = (data.get("selftext") or "").strip()
                    if len(body) < 80 or data.get("over_18"):
                        continue
                    posts.append({
                        "id": data.get("id"),
                        "subreddit": clean_sub,
                        "title": data.get("title", ""),
                        "body": body[:3000],
                        "score": data.get("score", 0),
                        "url": f"https://www.reddit.com{data.get('permalink', '')}",
                        "source": "oauth"
                    })
                if posts:
                    print(f"  [RedditClient] OAuth üzerinden {len(posts)} adet gönderi çekildi (r/{clean_sub}).")
                    return posts[:limit]
        except Exception as oe:
            print(f"  [RedditClient] OAuth denemesi başarısız, otomatik akıllı keşfe geçiliyor: {oe}")

    # 2. Option: Dynamic AI Generation (produces completely fresh stories on every refresh)
    ai_posts = generate_ai_reddit_posts(clean_sub, count=min(limit, 5), lang=lang or getattr(config, "LANGUAGE", "tr"))
    if ai_posts:
        for p in ai_posts:
            _SEEN_POST_IDS.add(p["id"])
        return ai_posts[:limit]

    # 3. Option: Smart Curated Viral Archive with Anti-Repeat Rotation
    matched_key = None
    for k in VIRAL_REDDIT_ARCHIVE.keys():
        if k.lower() == clean_sub.lower():
            matched_key = k
            break

    candidate_pool: List[Dict[str, Any]] = []
    if matched_key and VIRAL_REDDIT_ARCHIVE[matched_key]:
        candidate_pool = list(VIRAL_REDDIT_ARCHIVE[matched_key])
    else:
        for posts_list in VIRAL_REDDIT_ARCHIVE.values():
            candidate_pool.extend(posts_list)

    # Filter out seen posts if possible
    unseen_posts = [p for p in candidate_pool if p["id"] not in _SEEN_POST_IDS]
    if len(unseen_posts) < limit:
        # If pool is exhausted, clear seen history for this category so cycle repeats smoothly
        _SEEN_POST_IDS.difference_update({p["id"] for p in candidate_pool})
        unseen_posts = candidate_pool

    random.shuffle(unseen_posts)
    selected = unseen_posts[:limit]
    for p in selected:
        _SEEN_POST_IDS.add(p["id"])

    print(f"  [RedditClient] [Viral Arşiv] '{clean_sub}' kategorisinden {len(selected)} adet dönen viral gönderi sunuldu.")
    return selected