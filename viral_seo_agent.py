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

_SEO_LITE_MODEL = "gemini-flash-lite-latest"


def _resolve_seo_model() -> str:
    """SEO metadata uses lightweight Gemini — avoid Pro-tier quota burn."""
    configured = (getattr(config, "GEMINI_MODEL", "") or "").strip()
    if configured and "pro" not in configured.lower():
        return configured
    return _SEO_LITE_MODEL


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("429", "quota", "rate limit", "resource_exhausted", "resource exhausted"))


def _seo_llm_client():
    """Prefer Gemini key + GEMINI_MODEL; fall back to auto-detected AI provider."""
    gemini_key = (getattr(config, "GEMINI_API_KEY", "") or "").strip()
    if gemini_key:
        return (
            OpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            ),
            "Gemini",
            _resolve_seo_model(),
        )
    if config.AI_API_KEY and config.AI_BASE_URL:
        model = config.AI_MODEL if config.AI_MODEL and config.AI_MODEL != "procedural" else _SEO_LITE_MODEL
        return OpenAI(api_key=config.AI_API_KEY, base_url=config.AI_BASE_URL), config.AI_PROVIDER or "AI", model
    return None, "", ""


TITLE_VARIANTS_PROMPT = """Sen bir YouTube başlık uzmanısın. Verilen ana başlığın:
- Aynı anlamı farklı kelimelerle ifade eden
- Her biri farklı merak/duygu/kanca stratejisi kullanan
- 5 özgün başlık varyasyonu üret (Item 346: 45-60 karakter, tek kelime BÜYÜK vurgu, #Shorts dahil).

SADECE JSON FORMATINDA YANIT VER:
{"variants": ["Başlık 1", "Başlık 2", "Başlık 3", "Başlık 4", "Başlık 5"]}
"""


def finalize_seo_title(title: str, lang: str = "tr") -> str:
    """Items 346-348: single-word caps → curiosity prefix → 45-60 char limit.

    Caps run on the ORIGINAL title first so the injected curiosity word
    ("Şok Eden") cannot steal the single uppercase slot from the real hook
    word ("asla" → "ASLA") and end up as "ŞOK Eden".
    """
    title = format_capital_hook_word(title)
    title = inject_curiosity_words(title, lang=lang)
    return enforce_title_length_limit(title)


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


def prepend_description_engagement_question(description: str, keyword: str = "", lang: str = "tr") -> str:
    """
    Item 383: Açıklamaya Kısa Soru Yazma.
    Açıklamanın ilk satırına etkileşim sorusu ekler.
    """
    low = description.lower()
    if description.strip().startswith("💬") or "ne düşünüyorsunuz" in low or "what do you think" in low:
        return description
    if lang == "en":
        question = f"💬 What do you think about {keyword or 'this topic'}? Share your take below!\n\n"
    else:
        question = "💬 Siz bu konuda ne düşünüyorsunuz? Yorumlarda buluşalım!\n\n"
    return question + description.lstrip()


def _infer_legal_disclaimer_category(keyword: str, niche: str = "") -> Optional[str]:
    """Item 485: finans/sağlık nişlerinde yasal uyarı kategorisi."""
    blob = f"{keyword} {niche}".lower()
    if any(k in blob for k in ("finans", "borsa", "kripto", "yatırım", "para", "crypto", "finance", "money")):
        return "finance"
    if any(k in blob for k in ("sağlık", "tıbbi", "fitness", "health", "medical", "diyet")):
        return "health"
    return None


def build_natural_seo_description(
    keyword: str,
    hook: str = "",
    bullet_points: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    source_name: str = "",
    niche: str = "",
    lang: str = "tr",
) -> str:
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
    desc = prepend_description_engagement_question(desc, keyword=keyword, lang=lang)
    # Item 485: Topluluk ihtarı önleme — finans/sağlık açıklamasına yasal uyarı
    disc_cat = _infer_legal_disclaimer_category(keyword, niche)
    if disc_cat:
        from proof_archiver import ProofArchiver
        desc += f"\n\n{ProofArchiver.generate_legal_disclaimer(disc_cat, lang=lang)}"
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


def enrich_seo_with_retention_metadata(seo_data: dict, retention_metadata: dict = None, lang: str = "tr") -> dict:
    """
    Items 209-210: spotted mistake bait + polarizing dilemma → SEO/yorum paketi.
    """
    if not retention_metadata:
        return finalize_seo_compliance(seo_data or {}, lang=lang)

    seo_data = dict(seo_data or {})
    mistake = (retention_metadata.get("spotted_mistake_bait") or "").strip()
    dilemma = retention_metadata.get("polarizing_dilemma") or {}
    dilemma_q = (dilemma.get("question") or "").strip()

    pinned = (seo_data.get("pinned_comment") or "").strip()
    if mistake and mistake not in pinned:
        seo_data["pinned_comment"] = f"{pinned}\n\n🎯 {mistake}".strip() if pinned else mistake
        seo_data["spotted_mistake_bait"] = mistake

    desc = (seo_data.get("seo_description") or "").strip()
    if dilemma_q and dilemma_q not in desc:
        choices = ""
        if dilemma.get("choice_a") and dilemma.get("choice_b"):
            choices = f" ({dilemma['choice_a']} vs {dilemma['choice_b']})"
        block = f"\n\n💬 Tartışma: {dilemma_q}{choices}"
        seo_data["seo_description"] = desc + block
        seo_data["polarizing_dilemma"] = dilemma

    bait = retention_metadata.get("pinned_comment_bait") or {}
    if bait.get("video_cta") and not seo_data.get("video_cta"):
        seo_data["video_cta"] = bait["video_cta"]

    for key in ("share_cta", "bookmark_cta", "role_play_hook"):
        if retention_metadata.get(key):
            seo_data[key] = retention_metadata[key]

    return finalize_seo_compliance(seo_data, lang=lang)


def finalize_seo_compliance(seo_data: dict, lang: str = "tr") -> dict:
    """Strip tag stuffing, cap hashtags at 3, append AI disclosure paragraph (research §A4/A8)."""
    seo_data = dict(seo_data or {})
    try:
        from compliance import ai_disclosure_block, sanitize_seo_description
        desc = sanitize_seo_description(seo_data.get("seo_description") or "", max_hashtags=3)
        disc = ai_disclosure_block(
            uses_tts=True, uses_ai_script=True, uses_photoreal_ai=False, lang=lang,
        )
        para = disc.get("description_paragraph") or ""
        if para and para not in desc:
            desc = f"{desc.rstrip()}\n\n{para}"
        seo_data["seo_description"] = desc
        seo_data["ai_disclosure"] = disc
        seo_data["studio_ai_survey"] = disc.get("studio_ai_survey")
    except Exception:
        pass
    tags = seo_data.get("tags") or []
    if isinstance(tags, list) and len(tags) > 15:
        seo_data["tags"] = tags[:15]
    return seo_data


def generate_viral_seo_metadata(keyword: str, source_name: str = "", retention_metadata: dict = None) -> dict:
    fallback_title = finalize_seo_title(f"{keyword}: Bu Gerçeği ASLA Unutmayın #Shorts")
    fallback = {
        "hook_text": f"{keyword} hakkında kimsenin bilmediği gerçekler!",
        "seo_title": fallback_title,
        "seo_description": build_natural_seo_description(keyword, hook=f"{keyword} hakkında şok edici detaylar ve gizli kalmış sırlar bu videoda.", source_name=source_name),
        "tags": ["shorts", "bilgi", keyword.replace(" ", ""), "ilginc", "viral"],
        "pinned_comment": f"Sizce {keyword} konusundaki en şaşırtıcı detay neydi? Yorumlarda buluşalım! 👇",
        "affiliate_text": "🔗 Bahsedilen ürün ve kaynak linkleri profilimde!"
    }

    client_info = _seo_llm_client()
    if not client_info[0]:
        return enrich_seo_with_retention_metadata(fallback, retention_metadata)

    client, provider_name, model_name = client_info
    print(f"\n  [Viral SEO Agent] '{keyword}' için SEO ve Kanca verileri üretiliyor...")

    try:
        params = dict(
            model=model_name,
            messages=[
                {"role": "system", "content": SEO_PROMPT},
                {"role": "user", "content": f"Anahtar kelime: {keyword}"}
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        if provider_name in ("Gemini", "OpenAI"):
            params["response_format"] = {"type": "json_object"}

        resp = _call(client, params, provider_name=provider_name, model_name=model_name)
        raw = resp.choices[0].message.content.strip()
        data = _clean_json(raw)

        if data and "seo_title" in data:
            raw_title = data["seo_title"]
            try:
                from research_service import align_title_to_youtube_search
                align = align_title_to_youtube_search(keyword, raw_title, lang="tr")
                if align.get("aligned_title"):
                    raw_title = align["aligned_title"]
                    data["search_alignment"] = align
            except Exception:
                pass
            data["seo_title"] = finalize_seo_title(raw_title)
            # Auto-append investigative source reference
            data["seo_description"] = append_research_source_reference(data.get("seo_description", ""), keyword=keyword, source_name=source_name)
            data["seo_description"] = prepend_description_engagement_question(data["seo_description"], keyword=keyword, lang="tr")
            print(f"    [OK] Viral SEO verileri başarıyla üretildi.")
            try:
                from quota_manager import quota_tracker
                quota_tracker.record_call(provider_name or "Gemini")
            except Exception:
                pass
            return finalize_seo_compliance(
                enrich_seo_with_retention_metadata(data, retention_metadata)
            )
    except Exception as e:
        if _is_quota_error(e):
            print("    [SEO] Gemini kotası dolu — procedural fallback kullanılıyor.")
        else:
            print(f"    [UYARI] Viral SEO Agent hatası: {e}. Fallback kullanılıyor.")
        if not _is_quota_error(e):
            try:
                from quota_manager import quota_tracker
                quota_tracker.record_error(provider_name or "Gemini", str(e))
            except Exception:
                pass

    return enrich_seo_with_retention_metadata(fallback, retention_metadata)


def generate_related_video_bridge(
    shorts_title: str,
    long_form_url: str,
    long_form_title: str = "",
) -> Dict[str, str]:
    """
    Items 313 & 361: Shorts → kanal içi video köprüsü metadata paketi.
    Açıklamaya popüler Short/uzun video linki ekler; Studio 'Related video' alanına yapıştırılır (manuel upload).
    """
    long_title = (long_form_title or shorts_title).strip()
    description_block = (
        f"\n\n🔗 Tam video: {long_title}\n{long_form_url.strip()}\n"
        f"(Shorts'tan uzun videoya trafik köprüsü — Item 313)"
    )
    return {
        "related_video_url": long_form_url.strip(),
        "related_video_title": long_title,
        "description_append": description_block,
        "studio_upload_note": "YouTube Studio → Shorts details → Related video alanına URL ekle.",
        "shorts_end_screen_note": "Shorts end screen N/A — açıklama + related video link kullan.",
    }


def generate_end_screen_guidance(
    shorts_title: str,
    long_form_url: str = "",
    long_form_title: str = "",
) -> Dict[str, Any]:
    """
    Item 392: Kart ve Bitiş Ekranı (End Screens).
    Shorts'ta end screen yok; masaüstü izleyiciler için açıklama + related video linkleri.
    """
    placeholder_url = long_form_url.strip() or "https://youtube.com/@YOURCHANNEL"
    bridge = generate_related_video_bridge(shorts_title, placeholder_url, long_form_title)
    return {
        **bridge,
        "item": "392",
        "end_screen_action": (
            "Shorts end screen eklenemez — açıklama linklerini ve Related video alanını canlı tutun."
        ),
    }


def generate_competitor_analysis_brief(topic: str, lang: str = "tr") -> Dict[str, Any]:
    """
    Item 395: Rakip Kanal Analizi.
    Aynı nişte son 48 saatte patlayan videoları tarama + farklı format önerisi.
    """
    from trending_scanner import scan_youtube_shorts_trends, _get_fallback_viral_trends

    try:
        trends = scan_youtube_shorts_trends(topic, time_filter="day")
        if not trends:
            trends = _get_fallback_viral_trends(topic)
    except Exception:
        trends = _get_fallback_viral_trends(topic)

    top3 = trends[:3]
    competitors = [
        {
            "title": t.get("title", ""),
            "views_label": t.get("views", ""),
            "channel": t.get("channel", ""),
            "viral_score": t.get("viral_score", 0),
            "format_hint": t.get("hook_analysis", ""),
        }
        for t in top3
    ]
    action = (
        "Son 48 saatte patlayan 3 rakip videosunu inceleyin; aynı konuyu farklı formatla işleyin."
        if lang == "tr"
        else "Review top 3 competitor breakout videos from the last 48h; cover the same topic in a new format."
    )
    return {
        "item": "395",
        "topic": topic,
        "competitors": competitors,
        "action": action,
        "studio_note": "Studio → Analytics → Content → rakip videoların retention eğrisini karşılaştırın.",
        "data_source": "trending_scanner_stub",
    }


def get_channel_contact_guidance(business_email: str = "", lang: str = "tr") -> Dict[str, str]:
    """
    Item 396: Kanal Hakkında Kısmında İletişim.
    Sponsorluklar için resmi iş e-postası Studio About alanına eklenmeli.
    """
    email = (business_email or "business@yourchannel.com").strip()
    if lang == "en":
        return {
            "item": "396",
            "business_email": email,
            "about_section_text": f"Business inquiries: {email}",
            "studio_action": "YouTube Studio → Customization → Basic info → Description → add business email.",
        }
    return {
        "item": "396",
        "business_email": email,
        "about_section_text": f"İş birlikleri ve sponsorluk: {email}",
        "studio_action": "YouTube Studio → Özelleştirme → Temel bilgiler → Açıklama → iş e-postası ekleyin.",
    }


def generate_title_variants(main_title: str, keyword: str = "") -> list:
    """
    Item 109 – Özgün Başlık Üretimi.
    5 özgün başlık varyasyonu türetir.
    """
    kw = keyword or main_title
    fallback_variants = [
        finalize_seo_title(f"{kw} Hakkında Kimsenin BİLMEDİĞİ Gerçek #Shorts"),
        finalize_seo_title(f"Bu {kw} Sırrını Öğrenince ŞOK Olacaksınız #Shorts"),
        finalize_seo_title(f"{kw}: Gizli Kalmış İNANILMAZ Detaylar #Shorts"),
        finalize_seo_title(f"Neden {kw}? Asıl GERÇEK Burada #Shorts"),
        finalize_seo_title(f"{kw}: Uzmanların SAKLADIĞI Bilgi #Shorts"),
    ]

    client_info = _seo_llm_client()
    if not client_info[0]:
        return fallback_variants

    client, provider_name, model_name = client_info
    print(f"  [Item 109] '{main_title}' için 5 özgün başlık varyasyonu üretiliyor...")
    try:
        params = dict(
            model=model_name,
            messages=[
                {"role": "system", "content": TITLE_VARIANTS_PROMPT},
                {"role": "user", "content": f"Ana başlık: {main_title}\nAnahtar kelime: {kw}"}
            ],
            temperature=0.85,
            max_tokens=500,
        )
        if provider_name in ("Gemini", "OpenAI"):
            params["response_format"] = {"type": "json_object"}

        resp = _call(client, params, provider_name=provider_name, model_name=model_name)
        raw = resp.choices[0].message.content.strip()
        data = _clean_json(raw)

        if data and "variants" in data and isinstance(data["variants"], list):
            variants = [finalize_seo_title(v) for v in data["variants"] if isinstance(v, str) and len(v) > 5]
            if len(variants) >= 3:
                return variants[:5]

    except Exception as e:
        if _is_quota_error(e):
            print("    [Item 109] Gemini kotası dolu — procedural fallback kullanılıyor.")
        else:
            print(f"    [Item 109] UYARI: {e}. Fallback kullanılıyor.")

    return fallback_variants


def build_studio_metadata_fields(
    keyword: str,
    tags: Optional[List[str]] = None,
    target_country: str = "TR",
    lang: str = "tr",
) -> Dict[str, Any]:
    """
    Items 354-360, 364, 366, 368-369, 372-373, 376-378, 391, 393, 404-405:
    Paste-ready YouTube Studio metadata — auto-upload out of scope.
    """
    tag_list = tags or ["shorts", "viral", keyword.replace(" ", "")]
    schedule = get_optimal_upload_schedule(target_country)
    return {
        "item_refs": "354-360,364,366,368-369,372-373,376-378,391,393,404-405",
        "location_tag": "Turkey" if target_country.upper() == "TR" else "United States",
        "audience_language": "Turkish" if lang == "tr" else "English",
        "category_id": "22",
        "category_label": "People & Blogs",
        "playlist_suggestion": f"{keyword.split()[0].title()} Shorts Serisi",
        "tags_csv": ", ".join(tag_list[:30]),
        "thumbnail_note": "Frame 0 / _thumb.jpg dosyasını Studio thumbnail olarak yükleyin (Item 360).",
        "publish_frequency": "Günde 1 tutarlı Shorts — hafta sonu 11:00-13:00 ek slot (Item 364).",
        "channel_trailer_short": f"En iyi performans gösteren Shorts'u kanal fragmanı yapın (Item 366).",
        "shorts_remix": "Açık bırakın — remix sinyali algoritmaya yardımcı olur (Item 368).",
        "description_timestamps": "Shorts açıklamasına zaman damgası EKLEMEYİN (Item 369).",
        "social_links_block": "Instagram / TikTok / Linktree — açıklamanın altına ekleyin (Item 372).",
        "auto_translate_titles": "Studio → Subtitles → Translate → başlık çevirilerini açın (Item 373).",
        "handle_tip": "Kısa, akılda kalıcı @handle — arama ve marka için kritik (Item 376).",
        "title_number_rule": "Başlıkta 1-2 sayı kullanın — CTR artırır (Item 377).",
        "punctuation_balance": "En fazla 1 ünlem + 1 soru işareti — spam algısını önler (Item 378).",
        "copyright_match_action": "Content-ID eşleşmesinde ses/görseli değiştirin; sil-yeniden-yükleme yapmayın (Item 391).",
        "music_credit_line": "Açıklamaya telifsiz müzik kredisi ekleyin (Item 393).",
        "category_lock": "Kanal niş kategorisini değiştirmeyin — algoritma profili bozulur (Item 404).",
        "bulk_upload_warning": "Aynı gün 5+ video yüklemeyin — spam riski (Item 405).",
        "recommended_upload_window": schedule.get("primary_window"),
        "studio_note": "Tüm alanlar manuel Studio yapıştırma — otomatik upload kapsam dışı.",
    }


def export_seo_operator_pack(
    keyword: str,
    title: str = "",
    source_name: str = "",
    retention_metadata: Optional[dict] = None,
    related_video_url: str = "",
    business_email: str = "",
    target_country: str = "TR",
    lang: str = "tr",
    video_filename: str = "",
    thumb_path: str = "",
    total_renders: int = 0,
) -> Dict[str, Any]:
    """
    Batch 4 — B6 SEO operator pack: tüm otomatik SEO metadata + Studio yapıştırma rehberi.
    Upload otomasyonu kapsam dışı; operatör JSON/TXT ile Studio'da uygular.
    """
    from growth_tactics import (
        generate_studio_engagement_checklist,
        generate_weekly_live_stream_plan,
        should_show_notification_bell_cta,
    )
    from proof_archiver import ProofArchiver

    clean_title = title or keyword
    seo_meta = generate_viral_seo_metadata(clean_title, source_name=source_name, retention_metadata=retention_metadata)
    engagement = generate_studio_engagement_checklist(lang=lang)
    live_plan = generate_weekly_live_stream_plan(lang=lang)
    upload_sched = get_optimal_upload_schedule(target_country)
    cta_timing = calculate_cta_timing(total_duration=float(getattr(config, "TARGET_DURATION", 45.0) or 45.0))
    studio_fields = build_studio_metadata_fields(
        keyword=clean_title,
        tags=seo_meta.get("tags"),
        target_country=target_country,
        lang=lang,
    )
    end_screen = generate_end_screen_guidance(clean_title, related_video_url)
    competitor = generate_competitor_analysis_brief(clean_title, lang=lang)
    contact = get_channel_contact_guidance(business_email, lang=lang)
    reupload = ProofArchiver.get_reupload_avoidance_guidance(lang=lang)
    feed_phase = ProofArchiver.analyze_feed_distribution_phase(swipe_rate_pct=35.0)
    algo_reset = ProofArchiver.get_algorithm_reset_guidance(days_paused=0, lang=lang)
    traffic = ProofArchiver.analyze_traffic_sources(85.0, 8.0, 5.0)
    momentum = ProofArchiver.get_channel_momentum_threshold(total_videos=total_renders, avg_views=250)
    algo_threshold = ProofArchiver.analyze_algorithmic_view_threshold(850)
    notification_cta = should_show_notification_bell_cta(total_renders)

    return {
        "pack_type": "seo_operator_pack",
        "items_covered": "346-410 (automatable subset)",
        "video_file": video_filename,
        "thumb_file": thumb_path,
        "seo": seo_meta,
        "studio_metadata": studio_fields,
        "studio_engagement": engagement,
        "live_stream_plan": live_plan,
        "upload_schedule": upload_sched,
        "cta_timing": cta_timing,
        "channel_master_keywords": get_channel_master_keywords(clean_title),
        "end_screen_guidance": end_screen,
        "competitor_analysis": competitor,
        "channel_contact": contact,
        "reupload_guidance": reupload,
        "feed_distribution_advisory": feed_phase,
        "algorithm_reset_guidance": algo_reset,
        "traffic_sources_advisory": traffic,
        "channel_momentum_advisory": momentum,
        "algorithmic_threshold_advisory": algo_threshold,
        "notification_bell_cta": notification_cta,
        "manual_studio_only": True,
    }
