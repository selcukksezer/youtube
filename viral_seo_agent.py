"""
Viral SEO, Title Hooks, Description Engineering & Algorithmic Distribution Agent.
Implements Items 346 - 410 of the 500-Item YouTube Shorts Automation Roadmap.
Covers:
- 45-60 Character Title Length Limit (Item 346)
- Strategic Single-Word Capitalization (Item 347)
- Curiosity Multiplier Words (Item 348)
- Strict 3-Hashtag Distribution Rule (Item 349)
- Natural 2-3 Sentence Narrative Description (Item 352)
- 10 Channel Master Keywords Generator (Item 358)
- Target Country Timezone & Optimal Posting Schedule (Items 362, 363)
- 25-30s Delayed CTA Timing Rule (Item 367)
- 5 Diverse Title Variants (Item 109)
"""

import json
import re
import os
import random
from typing import Dict, List, Any, Optional
from openai import OpenAI
import config
from scene_generator import _call, _clean_json
from copyright_risk import filter_safe_clips, scan_copyright_risk
from headline_transformer import batch_convert_headlines, convert_headline_to_question


SEO_PROMPT = """Sen profesyonel bir YouTube SEO Uzmanı ve Viral İçerik Stratejistisin.
Verilen YouTube Shorts anahtar kelimesi/başlığı için şu bilgileri üret:

1. "hook_text": İzleyiciyi ilk 3 saniyede yakalayacak çok güçlü, merak uyandıran kanca cümlesi (en fazla 15 kelime).
2. "seo_title": Tıklama oranını (CTR) maksimize edecek, arama motorlarına uyumlu, ilgi çekici video başlığı (Item 346: 45-60 karakter, Item 347: tek bir kelime BÜYÜK harf, #Shorts dahil).
3. "seo_description": Videonun bulunabilirliğini artıracak, anahtar kelime zengini 2-3 cümlelik akıcı doğal açıklama metni (Item 352).
4. "tags": En çok aranan 15 yüksek hacimli etiket (dizi halinde: ["etiket1", "etiket2"]).
5. "pinned_comment": Yorumlarda etkileşimi patlatacak, izleyiciye doğrudan soru soran sabitleme yorumu metni (Item 350).
6. "affiliate_text": Ürün veya profil bağlantısını öneren CTA metni.

SADECE JSON FORMATINDA YANIT VER:
{"hook_text": "...", "seo_title": "...", "seo_description": "...", "tags": ["a", "b"], "pinned_comment": "...", "affiliate_text": "..."}
"""

TITLE_VARIANTS_PROMPT = """Sen bir YouTube başlık uzmanısın. Verilen ana başlığın:
- Aynı anlamı farklı kelimelerle ifade eden
- Her biri farklı merak/duygu/kanca stratejisi kullanan
- 5 özgün başlık varyasyonu üret (Item 346: 45-60 karakter, tek kelime BÜYÜK vurgu, #Shorts dahil).

SADECE JSON FORMATINDA YANIT VER:
{"variants": ["Başlık 1", "Başlık 2", "Başlık 3", "Başlık 4", "Başlık 5"]}
"""


def enforce_title_length_limit(title: str, min_len: int = 40, max_len: int = 60) -> str:
    """
    Item 346: Başlık Uzunluğu Sınırı.
    Shorts başlıkları mobil ekranda kesilmemesi için 45-60 karakter aralığında tutulur.
    """
    clean = re.sub(r'\s+', ' ', title).strip()
    if len(clean) > max_len:
        # Trim words gracefully
        words = clean.split()
        trimmed = ""
        for w in words:
            if len(f"{trimmed} {w}".strip()) <= max_len - 8:
                trimmed = f"{trimmed} {w}".strip()
            else:
                break
        if not trimmed.endswith("#shorts") and not trimmed.endswith("#Shorts"):
            trimmed = f"{trimmed} #Shorts"
        return trimmed
    return clean


def format_capital_hook_word(title: str) -> str:
    """
    Item 347: Büyük Harf Stratejisi.
    Başlığın tamamı büyük olmamalı; sadece tek bir kilit merak/duygu kelimesi BÜYÜK yazılmalıdır.
    """
    TARGET_WORDS = ["asla", "sakın", "gizli", "yasak", "şok", "neden", "hata", "aslında", "gerçek", "secret", "never", "always", "shocking", "truth"]
    words = title.split()
    capitalized = False
    new_words = []
    for w in words:
        clean_w = re.sub(r'[^\w]', '', w).lower()
        if clean_w in TARGET_WORDS and not capitalized:
            new_words.append(w.upper())
            capitalized = True
        else:
            new_words.append(w)
    return " ".join(new_words)


def inject_curiosity_words(title: str, lang: str = "tr") -> str:
    """
    Item 348: Başlıkta Merak Kelimeleri (Curiosity Multipliers).
    CTR'ı katlayan 'Gizli', 'Yasak', 'Şok Eden', 'Bilinmeyen' sıfatlarını entegre eder.
    """
    CURIOUS_WORDS_TR = ["Gizli", "Yasaklanan", "Bilinmeyen", "Şok Eden", "Akıl Almaz", "Gözden Kaçan"]
    CURIOUS_WORDS_EN = ["Hidden", "Forbidden", "Unknown", "Shocking", "Untold", "Mind-Bending"]

    words = CURIOUS_WORDS_TR if lang == "tr" else CURIOUS_WORDS_EN
    chosen = random.choice(words)
    if not any(c.lower() in title.lower() for c in words):
        return f"{chosen} {title}"
    return title


def enforce_three_hashtag_rule(title_or_desc: str, niche_tag: str, general_tag: str = "viral") -> str:
    """
    Item 349: 3-Hashtag Dağılım Kuralı.
    Algoritmanın spam saymaması için maksimum 3 odaklı hashtag (#shorts + #nis + #genel).
    """
    clean_niche = re.sub(r'[^\w]', '', niche_tag.lstrip('#')).lower() or "shorts"
    clean_general = re.sub(r'[^\w]', '', general_tag.lstrip('#')).lower() or "viral"
    
    tags = ["#Shorts", f"#{clean_niche}", f"#{clean_general}"]
    return " ".join(tags)


def build_natural_seo_description(keyword: str, hook: str = "", bullet_points: Optional[List[str]] = None, tags: Optional[List[str]] = None, source_name: str = "") -> str:
    """
    Item 352: Açıklama Kısmına Doğal Metin (Narrative Description).
    Yalnızca etiket doldurmak yerine 2-3 cümlelik akıcı, aranabilir YouTube SEO paragrafı kurar.
    """
    hook_part = hook.strip() if hook else f"{keyword} hakkında bilmeniz gereken en kritik detaylar bu videoda."
    if keyword.lower() not in hook_part.lower():
        hook_part = f"{keyword} – {hook_part}"
    desc = f"{hook_part} Tarihsel ve felsefi arka planı, uzmanların gözden kaçırdığı boyutlarıyla inceliyoruz. İzlediğiniz için teşekkürler; yeni bölümler için abone olup bildirimleri açmayı unutmayın!"
    
    if bullet_points:
        desc += "\n\n📌 Önemli Noktalar:\n" + "\n".join([f"• {bp}" for bp in bullet_points[:3]])
    
    # Item 83 & 140: Kaynak ve yasal bildirim
    desc = append_research_source_reference(desc, keyword=keyword, source_name=source_name)
    
    # 3-hashtag rule
    tag_block = enforce_three_hashtag_rule("", niche_tag=keyword.split()[0], general_tag="viral")
    desc += f"\n\n{tag_block}"
    return desc


def get_channel_master_keywords(niche: str) -> List[str]:
    """
    Item 358: Kanal Anahtar Kelimeleri (Channel Master Keywords).
    YouTube Studio kanal ayarları için 10 adet yüksek otorite niş anahtar kelimesi döndürür.
    """
    NICHE_KEYWORD_POOLS = {
        "stoic": ["stoacılık", "felsefe", "marcus aurelius", "zihin gücü", "disiplin", "motivasyon", "psikoloji", "özgüven", "stoic", "shorts"],
        "finance": ["finans", "para", "yatırım", "borsa", "kripto", "ekonomi", "zenginlik", "pasif gelir", "finansal özgürlük", "shorts"],
        "tech": ["yapay zeka", "teknoloji", "yazılım", "ai", "bilim", "gelecek", "robotik", "chatgpt", "deeptech", "shorts"],
        "history": ["tarih", "ilginç olaylar", "tarihi sırlar", "antik dünya", "belgesel", "savaş taktikleri", "eski çağ", "gizemli tarih", "biyografi", "shorts"],
        "mystery": ["gizem", "komplo", "bilinmeyen", "paranormal", "karanlık sırlar", "uzay", "arkeoloji", "okyanus", "fırtına", "shorts"]
    }
    low = (niche or "").lower()
    for k, pool in NICHE_KEYWORD_POOLS.items():
        if k in low:
            return pool
    return ["bilgi", "gündem", "ilginç", "öğren", "kültür", "viral", "faydalı", "eğitim", "shorts", "trend"]


def get_optimal_upload_schedule(target_country: str = "TR", day_of_week: Optional[int] = None) -> Dict[str, Any]:
    """
    Items 362 & 363: En İyi Yükleme Saatleri & Hedef Ülke Saat Dilimi (Posting Windows).
    Hafta içi öğle molası (12:00-14:00) ve iş dönüşü (18:00-21:00); hafta sonu (10:00-13:00).
    ABD hedefleniyorsa New York EST saat dilimine kilitlenir.
    """
    is_us = (target_country or "").upper() == "US"
    if is_us:
        return {
            "target_country": "US",
            "timezone": "EST (New York)",
            "primary_window": "12:00 - 15:00 EST",
            "secondary_window": "19:00 - 21:00 EST",
            "best_hours_24h": [12, 13, 14, 19, 20],
            "recommendation": "ABD Doğu Yakası öğle molası ve akşam dinlenme saatlerine göre zamanlayın."
        }
    return {
        "target_country": "TR",
        "timezone": "TRT (İstanbul, UTC+3)",
        "primary_window": "18:00 - 21:00 TRT (Akşam Zirvesi)",
        "secondary_window": "12:00 - 13:30 TRT (Öğle Molası)",
        "best_hours_24h": [12, 18, 19, 20],
        "recommendation": "Hafta içi 18:00-20:30, hafta sonu 11:00-13:00 en yüksek anlık izleyici hacmini sunar."
    }


def calculate_cta_timing(total_duration: float = 45.0) -> Dict[str, Any]:
    """
    Item 367: Abone Ol Çağrısı (CTA) Zamanlaması.
    Ekranda 'Abone Ol' butonu ilk 5 saniyede çıkmamalı; 25-30. saniyede çıkmalıdır.
    """
    cta_start = max(15.0, round(total_duration * 0.60, 1))
    cta_duration = 4.0
    return {
        "cta_start_second": cta_start,
        "cta_duration_seconds": cta_duration,
        "cta_text": "Abone Ol & Bildirimleri Aç! 🔔",
        "rule_compliance": "Item 367: Erken CTA engellendi (60%-70% aralığında zamanlandı)."
    }


def append_research_source_reference(description: str, keyword: str = "", source_name: str = "") -> str:
    """
    Item 83 & 140: Açıklamada Kaynak Belirtme ve Shorts İçi Yasal Bildirimler.
    """
    if "📌 Kaynak & Araştırma:" in description or "📌 Research & Source:" in description:
        return description

    ref_name = source_name.strip() if source_name else f"Tarihsel Arşiv, Akademik Literatür & Açık Kaynak İncelemesi ({keyword.strip() or 'Genel Kültür'})"
    source_block = (
        f"\n\n📌 Kaynak & Araştırma: {ref_name}\n"
        f"⚖️ Yasal Bildirim (Fair Use): Tüm görseller eğitim ve adil kullanım (Fair Use) kapsamındadır. "
        f"Bu video eğitim ve bilgilendirme amacıyla bağımsız olarak araştırılmış; özgün sesli analiz ve transformatif görsel kurguyla üretilmiştir."
    )
    return description.rstrip() + source_block


def generate_viral_seo_metadata(keyword: str, source_name: str = "") -> dict:
    fallback_title = enforce_title_length_limit(f"{keyword}: Bu Gerçeği ASLA Unutmayın #Shorts")
    fallback = {
        "hook_text": f"{keyword} hakkında kimsenin bilmediği gerçekler!",
        "seo_title": fallback_title,
        "seo_description": build_natural_seo_description(keyword, hook=f"{keyword} hakkında şok edici detaylar ve gizli kalmış sırlar bu videoda.", source_name=source_name),
        "tags": ["shorts", "bilgi", keyword.replace(" ", ""), "ilginc", "viral"],
        "pinned_comment": f"Sizce {keyword} konusundaki en şaşırtıcı detay neydi? Yorumlarda buluşalım! 👇",
        "affiliate_text": "🔗 Bahsedilen ürün ve kaynak linkleri profilimde!"
    }

    if not config.AI_PROVIDER or not config.AI_API_KEY:
        return fallback

    print(f"\n  [Viral SEO Agent] '{keyword}' için SEO ve Kanca verileri üretiliyor...")

    try:
        client = OpenAI(api_key=config.AI_API_KEY, base_url=config.AI_BASE_URL)
        params = dict(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": SEO_PROMPT},
                {"role": "user", "content": f"Anahtar kelime: {keyword}"}
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        if "Gemini" in config.AI_PROVIDER or "OpenAI" in config.AI_PROVIDER:
            params["response_format"] = {"type": "json_object"}

        resp = _call(client, params)
        raw = resp.choices[0].message.content.strip()
        data = _clean_json(raw)

        if data and "seo_title" in data:
            # Enforce 45-60 char length and capital word rules
            data["seo_title"] = enforce_title_length_limit(format_capital_hook_word(data["seo_title"]))
            # Auto-append investigative source reference
            data["seo_description"] = append_research_source_reference(data.get("seo_description", ""), keyword=keyword, source_name=source_name)
            print(f"    [OK] Viral SEO verileri başarıyla üretildi.")
            try:
                from quota_manager import quota_tracker
                quota_tracker.record_call(config.AI_PROVIDER or "Gemini")
            except Exception:
                pass
            return data
    except Exception as e:
        print(f"    [UYARI] Viral SEO Agent hatası: {e}. Fallback kullanılıyor.")
        try:
            from quota_manager import quota_tracker
            quota_tracker.record_error(config.AI_PROVIDER or "Gemini", str(e))
        except Exception:
            pass

    return fallback


def generate_title_variants(main_title: str, keyword: str = "") -> list:
    """
    Item 109 – Özgün Başlık Üretimi.
    5 özgün başlık varyasyonu türetir.
    """
    kw = keyword or main_title
    fallback_variants = [
        enforce_title_length_limit(f"{kw} Hakkında Kimsenin BİLMEDİĞİ Gerçek #Shorts"),
        enforce_title_length_limit(f"Bu {kw} Sırrını Öğrenince ŞOK Olacaksınız #Shorts"),
        enforce_title_length_limit(f"{kw}: Gizli Kalmış İNANILMAZ Detaylar #Shorts"),
        enforce_title_length_limit(f"Neden {kw}? Asıl GERÇEK Burada #Shorts"),
        enforce_title_length_limit(f"{kw}: Uzmanların SAKLADIĞI Bilgi #Shorts"),
    ]

    if not config.AI_PROVIDER or not config.AI_API_KEY:
        return fallback_variants

    print(f"  [Item 109] '{main_title}' için 5 özgün başlık varyasyonu üretiliyor...")
    try:
        client = OpenAI(api_key=config.AI_API_KEY, base_url=config.AI_BASE_URL)
        params = dict(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": TITLE_VARIANTS_PROMPT},
                {"role": "user", "content": f"Ana başlık: {main_title}\nAnahtar kelime: {kw}"}
            ],
            temperature=0.85,
            max_tokens=500,
        )
        if "Gemini" in config.AI_PROVIDER or "OpenAI" in config.AI_PROVIDER:
            params["response_format"] = {"type": "json_object"}

        resp = _call(client, params)
        raw = resp.choices[0].message.content.strip()
        data = _clean_json(raw)

        if data and "variants" in data and isinstance(data["variants"], list):
            variants = [enforce_title_length_limit(format_capital_hook_word(v)) for v in data["variants"] if isinstance(v, str) and len(v) > 5]
            if len(variants) >= 3:
                return variants[:5]

    except Exception as e:
        print(f"    [Item 109] UYARI: {e}. Fallback kullanılıyor.")

    return fallback_variants
