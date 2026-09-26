"""
Affiliate Marketing & E-Commerce Video Engine (AFM).
Adapted and enhanced from MoneyPrinterV2's AFM architecture.

Turns product links (Amazon, Trendyol, Hepsiburada, or any e-commerce page) or product descriptions
into high-converting, viral 9:16 YouTube Shorts / TikTok scripts and scene plans with:
- Automatic product feature and title extraction.
- Problem -> Agitation -> Solution -> Call-To-Action (Hook-Retain-Convert) structure.
- Affiliate disclosure & custom CTA ("Link in bio / comments").
- Compatible with ShortsVideoCreators visual pipeline (Flux AI / Stock / Ken-Burns).
"""

from __future__ import annotations
import re
import json
import logging
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AffiliateProductEngine")

VIRAL_PRODUCT_HOOKS = {
    "life_hack": {
        "tr": [
            "Bunu neden daha önce almadım diyeceğiniz o ürün!",
            "Evdeki en sinir bozucu sorunu 10 saniyede çözen alet!",
            "İnternetin gizli kalmış en iyi hayat kurtarıcı ürünü!",
        ],
        "en": [
            "The one product that made me say 'Why didn't I buy this sooner?!'",
            "This gadget fixes the most annoying daily problem in 10 seconds!",
            "The internet's best-kept life-saving secret product!",
        ]
    },
    "problem_solver": {
        "tr": [
            "Eğer sürekli bu sorunu yaşıyorsanız, bu ürün tam size göre!",
            "Paranızı ve zamanınızı kurtaran inanılmaz bir icat!",
            "Sonunda herkesin şikayet ettiği o probleme kesin çözüm bulundu!",
        ],
        "en": [
            "If you constantly struggle with this, this product is for you!",
            "An unbelievable invention that saves your money and time!",
            "Finally, a permanent solution to everyone's biggest headache!",
        ]
    },
    "honest_review": {
        "tr": [
            "Viral olan bu ürünü gerçekten almaya değer mi? Dürüst inceleme!",
            "Herkesin övdüğü o ürünü test ettik, işte gerçekler!",
            "Ucuz mu kaliteli mi? İşte almadan önce bilmeniz gerekenler!",
        ],
        "en": [
            "Is this viral product actually worth your money? Honest test!",
            "Everyone is talking about this product, here is the raw truth!",
            "Cheap or game-changer? What you MUST know before buying!",
        ]
    }
}


def extract_product_from_url(url: str, timeout: float = 6.0) -> Dict[str, Any]:
    """
    Extract product title, key features, price and images from an e-commerce URL.
    Uses clean HTTP request with realistic user-agent; falls back gracefully.
    """
    data = {
        "url": url,
        "title": "",
        "features": [],
        "price": "",
        "image_urls": [],
        "source": "web_scrape"
    }
    
    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        # If user just gave product name or text
        data["title"] = clean_url
        data["features"] = ["Pratik kullanım", "Ergonomik tasarım", "Yüksek performans"]
        data["source"] = "manual_text"
        return data

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        req = urllib.request.Request(clean_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as res:
            html = res.read().decode("utf-8", errors="ignore")
            
            # 1. Title Extraction
            # Check og:title
            og_title = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html, re.I)
            if not og_title:
                og_title = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:title["\']', html, re.I)
            
            if og_title:
                data["title"] = og_title.group(1).strip()
            else:
                title_tag = re.search(r'<title>(.*?)</title>', html, re.I | re.DOTALL)
                if title_tag:
                    data["title"] = re.sub(r'\s+', ' ', title_tag.group(1)).strip()
            
            # Clean title from e-commerce brand suffixes
            data["title"] = re.sub(r'(\s*[-|–]\s*(Amazon|Trendyol|Hepsiburada|eBay|AliExpress).*)$', '', data["title"], flags=re.I).strip()
            if not data["title"]:
                # Fallback to URL slug
                parsed = urllib.parse.urlparse(clean_url)
                slug = [p for p in parsed.path.split('/') if p][-1] if parsed.path else "Ürün"
                data["title"] = slug.replace("-", " ").replace("_", " ").title()

            # 2. Features / Bullets Extraction
            # Try finding bullet points or list items
            bullets = re.findall(r'<li[^>]*>(.*?)</li>', html, re.I | re.DOTALL)
            clean_bullets = []
            for b in bullets:
                txt = re.sub(r'<[^>]+>', '', b).strip()
                if 15 < len(txt) < 150 and not any(skip in txt.lower() for skip in ("çerez", "cookie", "sepet", "giriş", "kargo")):
                    clean_bullets.append(txt)
                if len(clean_bullets) >= 4:
                    break
            data["features"] = clean_bullets or [
                "Zaman ve enerji tasarrufu sağlayan akıllı tasarım",
                "Kolay taşınabilir ve pratik kullanım",
                "Kullanıcı puanları ve memnuniyet oranı yüksek"
            ]

            # 3. Product Image Extraction
            og_img = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.I)
            if og_img:
                data["image_urls"].append(og_img.group(1))

    except Exception as e:
        logger.warning(f"Failed to scrape product URL ({url}): {e}")
        parsed = urllib.parse.urlparse(clean_url)
        slug = [p for p in parsed.path.split('/') if p][-1] if parsed.path else "Ürün"
        data["title"] = slug.replace("-", " ").replace("_", " ").title() or "Akıllı Günlük Ürün"
        data["features"] = ["Pratik kullanım", "Yüksek verimlilik", "Bütçe dostu"]
        data["source"] = "fallback"

    return data


def generate_affiliate_short_plan(
    product_input: str,
    affiliate_url: str = "",
    hook_style: str = "life_hack",
    language: str = "tr",
    target_duration: float = 48.0,
    cta_text: str = "Link profilde ve ilk yorumda sabitli!"
) -> Dict[str, Any]:
    """
    Generates a complete, structured video creation plan for an affiliate product.
    Outputs a plan ready for ShortsVideoCreators render pipeline.
    """
    lang = language.lower() if language else "tr"
    product_info = extract_product_from_url(product_input)
    product_name = product_info.get("title") or "Bu Ürün"
    # Truncate overly long product titles
    short_product_name = product_name[:60] if len(product_name) > 60 else product_name

    hooks = VIRAL_PRODUCT_HOOKS.get(hook_style, VIRAL_PRODUCT_HOOKS["life_hack"]).get(lang, VIRAL_PRODUCT_HOOKS["life_hack"]["tr"])
    hook_sentence = hooks[0]

    features = product_info.get("features", [])
    f1 = features[0] if len(features) > 0 else "kullanım kolaylığı"
    f2 = features[1] if len(features) > 1 else "ergonomik tasarımı"
    f3 = features[2] if len(features) > 2 else "yüksek dayanıklılığı"

    if lang == "en":
        scenes = [
            {
                "scene_index": 1,
                "duration": 4.5,
                "narration": f"{hook_sentence} Everyone on the internet is raving about this!",
                "scene_description": f"Person reacting with surprised expression looking at a sleek {short_product_name}",
                "search_queries": [f"{short_product_name} gadget reveal", "shocked expression reaction", "smart home gadget"]
            },
            {
                "scene_index": 2,
                "duration": 6.0,
                "narration": f"Here is the problem: we waste hours every week doing this manually and dealing with daily frustration.",
                "scene_description": "Frustrated person struggling with messy task before finding modern tool",
                "search_queries": ["frustrated person daily struggle", "messy routine problem", "slow manual work"]
            },
            {
                "scene_index": 3,
                "duration": 7.0,
                "narration": f"That's where the {short_product_name} comes in. Look at how seamlessly it solves this issue in seconds.",
                "scene_description": f"Close-up unboxing and first smooth action of {short_product_name}",
                "search_queries": [f"{short_product_name} unboxing", "gadget in action macro", "satisfying clean process"]
            },
            {
                "scene_index": 4,
                "duration": 8.0,
                "narration": f"First off, {f1}. It feels extremely premium and saves huge amounts of effort.",
                "scene_description": f"Hands-on demonstration showing first feature of {short_product_name}",
                "search_queries": ["hands on tech review", "premium product detail", "effortless productivity"]
            },
            {
                "scene_index": 5,
                "duration": 8.0,
                "narration": f"Secondly, {f2}. You don't need any complex setup, it works immediately right out of the box.",
                "scene_description": "Effortless plug and play usage demonstration with satisfied smile",
                "search_queries": ["easy setup gadget", "minimalist modern design", "satisfying demonstration"]
            },
            {
                "scene_index": 6,
                "duration": 7.5,
                "narration": f"And best of all, {f3}. Once you start using it, there is honestly no going back.",
                "scene_description": "Cinematic slow motion shot highlighting product quality and durability",
                "search_queries": ["cinematic product lighting", "durable quality gadget", "lifestyle modern comfort"]
            },
            {
                "scene_index": 7,
                "duration": 7.0,
                "narration": f"If you want to grab one with the best discount, {cta_text}. Let me know in the comments if you would buy this!",
                "scene_description": "Phone showing shopping cart with discount code and finger tapping link",
                "search_queries": ["online shopping checkout", "mobile phone tap bio link", "call to action review"]
            },
        ]
        topic_title = f"Why You Need {short_product_name}! #Shorts"
        seo_description = (
            f"Honest review of {short_product_name}. Check out how it fixes daily hassles!\n\n"
            f"🛒 Product Link: {affiliate_url or 'Link in bio'}\n"
            f"⚡ Disclosure: This video contains affiliate links. #affiliate #gadget #review"
        )
    else:
        scenes = [
            {
                "scene_index": 1,
                "duration": 4.5,
                "narration": f"{hook_sentence} Sosyal medyada herkesin neden bunu konuştuğuna inanamayacaksınız!",
                "scene_description": f"Kişi şaşırmış bir ifadeyle {short_product_name} cihazına bakıyor",
                "search_queries": [f"{short_product_name} tanıtım", "şaşırmış insan tepkisi", "akıllı ev aleti"]
            },
            {
                "scene_index": 2,
                "duration": 6.0,
                "narration": f"Asıl problem şu: her gün aynı can sıkıcı işle vakit kaybedip gereksiz yere yoruluyoruz.",
                "scene_description": "Günlük işlerde zorlanan ve yorulan insan yakın çekim",
                "search_queries": ["günlük stres yorgunluk", "zorlanan insan", "karmaşık masa işi"]
            },
            {
                "scene_index": 3,
                "duration": 7.0,
                "narration": f"İşte tam bu noktada {short_product_name} devreye giriyor. Bakın tek harekette sorunu nasıl çözüyor.",
                "scene_description": f"{short_product_name} ürününün kutudan çıkışı ve ilk çalışma anı",
                "search_queries": [f"{short_product_name} kutu açılışı", "tatmin edici ürün kullanımı", "akıllı teknoloji"]
            },
            {
                "scene_index": 4,
                "duration": 8.0,
                "narration": f"İlk olarak {f1}. Malzeme kalitesi gerçekten birinci sınıf ve inanılmaz pratik.",
                "scene_description": f"{short_product_name} ürününün birinci özelliğinin yakın plan testi",
                "search_queries": ["ürün inceleme yakın çekim", "kaliteli teknoloji aleti", "hızlı pratik çözüm"]
            },
            {
                "scene_index": 5,
                "duration": 8.0,
                "narration": f"İkincisi ise {f2}. Hiçbir karmaşık ayarla uğraşmadan anında kullanıma hazır hale geliyor.",
                "scene_description": "Kolay kurulum ve rahatça çalışan aletin detaylı görüntüsü",
                "search_queries": ["kolay kurulum", "minimalist modern alet", "rahat kullanım"]
            },
            {
                "scene_index": 6,
                "duration": 7.5,
                "narration": f"En güzel yanı da {f3}. Bir kere denedikten sonra eski yöntemlere geri dönmek imkansız.",
                "scene_description": "Sinematik ışıklandırma altında ürünün estetik duruşu ve pürüzsüz çalışma",
                "search_queries": ["sinematik ürün çekimi", "dayanıklı kaliteli ürün", "modern yaşam konforu"]
            },
            {
                "scene_index": 7,
                "duration": 7.0,
                "narration": f"Ürünü indirimli linkten incelemek isterseniz, {cta_text}. Sizce bu fiyata değer mi? Yorumlara yazın!",
                "scene_description": "Ekranda indirim bağlantısına tıklayan parmak ve ürünün son pozu",
                "search_queries": ["internetten alışveriş indirim", "telefonda bağlantıya tıklama", "ürün inceleme sonu"]
            },
        ]
        topic_title = f"Bunu Neden Daha Önce Almadım Diyeceksiniz: {short_product_name}! #Shorts"
        seo_description = (
            f"{short_product_name} detaylı ve dürüst ürün incelemesi. Hayatınızı nasıl kolaylaştırdığını izleyin!\n\n"
            f"🛒 Ürün Bağlantısı: {affiliate_url or 'Profildeki linkten ve sabitli yorumdan ulaşabilirsiniz.'}\n"
            f"📌 Not: Bu video işbirliği/affiliate bağlantısı içerir. #işbirliği #ürüninceleme #shorts"
        )

    total_calc_duration = sum(s["duration"] for s in scenes)

    return {
        "ok": True,
        "topic": topic_title,
        "product_info": product_info,
        "niche": "3_gadget_review",
        "language": lang,
        "target_duration": round(total_calc_duration, 1),
        "seo_metadata": {
            "title": topic_title,
            "description": seo_description,
            "tags": [
                "ürün inceleme", "gadgets", "amazon finds", "tiktok made me buy it",
                "hayat kurtaran ürünler", "shorts", "teknoloji"
            ],
            "affiliate_url": affiliate_url
        },
        "scenes": scenes,
    }
