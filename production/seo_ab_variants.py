"""A/B title variants, hashtag/tag tables, language templates, and Studio operator pack for viral_seo_agent."""
from __future__ import annotations

import re
import sys
from typing import Any, Dict, List, Optional

import config
from scene_generator import _call, _clean_json

TITLE_VARIANTS_PROMPT = """Sen bir YouTube başlık uzmanısın. Verilen ana başlığın:
- Aynı anlamı farklı kelimelerle ifade eden
- Her biri farklı merak/duygu/kanca stratejisi kullanan
- 5 özgün başlık varyasyonu üret (Item 346: 45-60 karakter, tek kelime BÜYÜK vurgu, #Shorts dahil).

SADECE JSON FORMATINDA YANIT VER:
{"variants": ["Başlık 1", "Başlık 2", "Başlık 3", "Başlık 4", "Başlık 5"]}
"""

_NICHE_KEYWORD_POOLS = {
    "stoic": ["stoacılık", "felsefe", "marcus aurelius", "zihin gücü", "disiplin", "motivasyon", "psikoloji", "özgüven", "stoic", "shorts"],
    "finance": ["finans", "para", "yatırım", "borsa", "kripto", "ekonomi", "zenginlik", "pasif gelir", "finansal özgürlük", "shorts"],
    "tech": ["yapay zeka", "teknoloji", "yazılım", "ai", "bilim", "gelecek", "robotik", "chatgpt", "deeptech", "shorts"],
    "history": ["tarih", "ilginç olaylar", "tarihi sırlar", "antik dünya", "belgesel", "savaş taktikleri", "eski çağ", "gizemli tarih", "biyografi", "shorts"],
    "mystery": ["gizem", "komplo", "bilinmeyen", "paranormal", "karanlık sırlar", "uzay", "arkeoloji", "okyanus", "fırtına", "shorts"],
}

_TURKISH_STOPWORDS = {
    "ve", "veya", "ile", "için", "icin", "bir", "üç", "uc", "beş", "bes",
    "en", "bu", "o", "şu", "hakkında", "gibi", "kadar", "olan", "nın",
    "nin", "nun", "nün", "dan", "den", "tan", "ten", "karşı", "karsi",
    "tarafın", "tarafin", "biri", "her", "daha", "cok", "çok", "nasıl",
    "nasil", "neden", "şey", "sey",
}
_ENGLISH_STOPWORDS = {
    "and", "the", "for", "with", "from", "about", "you", "your",
    "what", "when", "where", "which", "who", "why", "how",
}


def _vsa_attr(name: str, default: Any) -> Any:
    mod = sys.modules.get("viral_seo_agent")
    return getattr(mod, name, default) if mod is not None else default


def get_channel_master_keywords(niche: str) -> List[str]:
    """Item 358: Kanal Anahtar Kelimeleri (Channel Master Keywords)."""
    low = (niche or "").lower()
    for k, pool in _NICHE_KEYWORD_POOLS.items():
        if k in low:
            return pool
    return ["bilgi", "gündem", "ilginç", "öğren", "kültür", "viral", "faydalı", "eğitim", "shorts", "trend"]


def get_optimal_upload_schedule(target_country: str = "TR", day_of_week: Optional[int] = None) -> Dict[str, Any]:
    """Items 362 & 363: En İyi Yükleme Saatleri & Hedef Ülke Saat Dilimi (Posting Windows)."""
    if day_of_week is not None and day_of_week not in range(7):
        raise ValueError("day_of_week must use Python weekday values from 0 to 6")
    is_weekend = day_of_week in (5, 6)
    is_us = (target_country or "").upper() == "US"
    if is_us:
        return {
            "target_country": "US",
            "timezone": "EST (New York)",
            "primary_window": "10:00 - 13:00 EST" if is_weekend else "12:00 - 15:00 EST",
            "secondary_window": "19:00 - 21:00 EST",
            "best_hours_24h": [10, 11, 12, 19, 20] if is_weekend else [12, 13, 14, 19, 20],
            "recommendation": (
                "ABD Doğu Yakası hafta sonu sabah ve akşam saatlerine göre zamanlayın."
                if is_weekend else "ABD Doğu Yakası öğle molası ve akşam dinlenme saatlerine göre zamanlayın."
            ),
        }
    return {
        "target_country": "TR",
        "timezone": "TRT (İstanbul, UTC+3)",
        "primary_window": "10:00 - 13:00 TRT (Hafta Sonu)" if is_weekend else "18:00 - 21:00 TRT (Akşam Zirvesi)",
        "secondary_window": "12:00 - 13:30 TRT (Öğle Molası)",
        "best_hours_24h": [10, 11, 12, 18, 19] if is_weekend else [12, 18, 19, 20],
        "recommendation": (
            "Hafta sonu 10:00-13:00 ve akşam saatlerini hedefleyin."
            if is_weekend else "Hafta içi 18:00-20:30 ve öğle molasını hedefleyin."
        ),
    }


def calculate_cta_timing(total_duration: float = 45.0) -> Dict[str, Any]:
    """Item 367: Abone Ol Çağrısı (CTA) Zamanlaması."""
    cta_start = max(15.0, round(total_duration * 0.60, 1))
    return {
        "cta_start_second": cta_start,
        "cta_duration_seconds": 4.0,
        "cta_text": "Abone Ol & Bildirimleri Aç! 🔔",
        "rule_compliance": "Item 367: Erken CTA engellendi (60%-70% aralığında zamanlandı).",
    }


def generate_15_viral_tags(keyword: str, niche: str = "", lang: str = "tr") -> List[str]:
    """Generate exactly 15 high-volume, clean, individual YouTube tags from keyword and niche."""
    is_english = (lang or "tr").lower().startswith("en")
    tags: List[str] = ["shorts", "discover", "viral", "trending"] if is_english else ["shorts", "keşfet", "viral", "trend"]
    stopwords = _ENGLISH_STOPWORDS if is_english else _TURKISH_STOPWORDS

    raw_tokens = [
        w.lower() for w in re.split(r"[^\w\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc]+", keyword)
        if len(w) >= 3 and w.lower() not in stopwords
    ]

    if len(raw_tokens) >= 2:
        for i in range(len(raw_tokens) - 1):
            pair = f"{raw_tokens[i]} {raw_tokens[i+1]}"
            if pair not in tags and len(tags) < 15:
                tags.append(pair)

    for tok in raw_tokens:
        if tok not in tags and len(tags) < 15:
            tags.append(tok)

    niche_low = (niche or keyword).lower()
    if any(k in niche_low for k in ("bilim", "gizem", "uzay", "science", "space", "myth")):
        niche_pool = (
            ["science", "scientific facts", "mysterious events", "unexplained mysteries", "universe", "space", "discovery", "documentary", "curiosity"]
            if is_english else ["bilim", "bilimsel gerçekler", "gizemli olaylar", "açıklanamayan sırlar", "evren", "uzay", "keşif", "belgesel", "merak"]
        )
    elif any(k in niche_low for k in ("tarih", "history", "ancient")):
        niche_pool = (
            ["history", "historical events", "ancient mysteries", "interesting history", "the past", "archaeology", "unknown history"]
            if is_english else ["tarih", "tarihi olaylar", "antik sırlar", "ilginç tarih", "geçmiş", "arkeoloji", "bilinmeyen tarih"]
        )
    elif any(k in niche_low for k in ("para", "finans", "money", "crypto", "business")):
        niche_pool = (
            ["finance", "make money", "economy", "investing", "success", "entrepreneurship", "motivation", "wealth"]
            if is_english else ["finans", "para kazanma", "ekonomi", "yatırım", "başarı", "girişimcilik", "motivasyon", "zenginlik"]
        )
    elif any(k in niche_low for k in ("psikoloji", "stoic", "felsefe", "mind")):
        niche_pool = (
            ["psychology", "philosophy", "stoicism", "personal growth", "mindset", "behavior", "mindfulness"]
            if is_english else ["psikoloji", "felsefe", "stoacılık", "kişisel gelişim", "zihin", "davranış", "farkındalık"]
        )
    else:
        niche_pool = (
            ["interesting facts", "amazing truths", "did you know", "learn", "knowledge", "news", "popular"]
            if is_english else ["ilginç bilgiler", "şaşırtıcı gerçekler", "bunu biliyor muydunuz", "öğren", "bilgi", "gündem", "popüler"]
        )

    for n_tag in niche_pool:
        if n_tag not in tags and len(tags) < 15:
            tags.append(n_tag)

    universal_fill = (
        ["youtube shorts", "usa", "useful facts", "short video", "watch", "curious facts", "amazing"]
        if is_english else ["youtube shorts", "türkiye", "faydalı bilgiler", "kısa video", "izle", "merak edilenler", "şaşırtıcı"]
    )
    for u_tag in universal_fill:
        if u_tag not in tags and len(tags) < 15:
            tags.append(u_tag)

    return tags[:15]


def finalize_seo_compliance(seo_data: dict, lang: str = "tr", visual_manifest=None, niche: str = "") -> dict:
    """Strip tag stuffing, cap hashtags at 3, append the real source block, and enforce COPPA/MFK on kids niches."""
    seo_data = dict(seo_data or {})
    try:
        from compliance import ai_disclosure_block, sanitize_seo_description
        from compliance.transparent_disclosure import append_ai_disclosure_to_description
        desc = sanitize_seo_description(seo_data.get("seo_description") or seo_data.get("description") or "", max_hashtags=3)
        disc = ai_disclosure_block(
            uses_tts=True, uses_ai_script=True, uses_photoreal_ai=False, lang=lang,
            clips_or_manifest=visual_manifest or None, include_sources=bool(visual_manifest),
        )
        desc = append_ai_disclosure_to_description(desc, disc)
        seo_data["seo_description"] = desc
        seo_data["description"] = desc
        seo_data["ai_disclosure"] = disc
        seo_data["studio_ai_survey"] = disc.get("studio_ai_survey")
    except Exception:
        pass

    raw_tags = seo_data.get("tags") or []
    cleaned_tags = []
    if isinstance(raw_tags, list):
        for t in raw_tags:
            t_str = str(t).strip().lower()
            if not t_str or (len(t_str) > 25 and " " not in t_str):
                continue
            if t_str not in cleaned_tags:
                cleaned_tags.append(t_str)

    if len(cleaned_tags) < 15:
        kw = seo_data.get("seo_title") or "video"
        tags_fn = _vsa_attr("generate_15_viral_tags", generate_15_viral_tags)
        pad = tags_fn(kw, niche=niche, lang=lang)
        for pt in pad:
            if pt not in cleaned_tags and len(cleaned_tags) < 15:
                cleaned_tags.append(pt)

    seo_data["tags"] = cleaned_tags[:15]

    effective_niche = niche or str(seo_data.get("niche_id") or seo_data.get("niche") or "")
    try:
        from compliance.kids_disclosure import apply_kids_upload_fields, is_made_for_kids_niche
        if is_made_for_kids_niche(effective_niche):
            kids_fields = apply_kids_upload_fields(
                niche_id=effective_niche,
                description=seo_data.get("seo_description") or seo_data.get("description") or "",
                tags=seo_data["tags"],
                language=lang,
            )
            seo_data["selfDeclaredMadeForKids"] = kids_fields["selfDeclaredMadeForKids"]
            seo_data["seo_description"] = kids_fields["description"]
            seo_data["description"] = kids_fields["description"]
            seo_data["tags"] = kids_fields["tags"][:15]
            seo_data["suppress_pinned_comment"] = kids_fields["suppress_pinned_comment"]
            seo_data["collect_viewer_data"] = kids_fields["collect_viewer_data"]
            if kids_fields["suppress_pinned_comment"]:
                seo_data["pinned_comment"] = ""
    except Exception:
        pass

    return seo_data


def attach_shopping_product_tags(seo: dict, keyword: str = "", products: list = None) -> dict:
    """R10 #95: YouTube Shopping / product-tag metadata pack for operator paste into Studio."""
    data = dict(seo or {})
    kw = (keyword or data.get("seo_title") or "ürün").strip()
    product_list = list(products or [])
    kw_low = kw.lower()
    is_product_topic = any(w in kw_low for w in ("ürün", "urun", "alet", "cihaz", "gadget", "amazon", "satın", "kulaklık", "şarj", "fiyat"))

    if not product_list:
        if not is_product_topic:
            return data
        product_list = [f"{kw} — öne çıkan ürün", f"{kw} alternatif set"]

    tags = []
    for i, name in enumerate(product_list[:5]):
        tags.append({
            "index": i + 1,
            "product_name": name,
            "suggested_shelf": "YouTube Shopping / merch shelf",
            "cta": data.get("affiliate_text") or "Link profilde / açıklamada",
        })
    data["shopping_product_tags"] = tags
    data["shopping_studio_note"] = (
        "Studio → Video details → Products — etiketleri manuel ekle "
        "(Shopping API otomatik yükleme kapsam dışı)."
    )
    return data


def generate_related_video_bridge(
    shorts_title: str,
    long_form_url: str,
    long_form_title: str = "",
) -> Dict[str, str]:
    """Items 313 & 361: Shorts → kanal içi video köprüsü metadata paketi."""
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
    """Item 392: Kart ve Bitiş Ekranı (End Screens)."""
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
    """Item 395: Rakip Kanal Analizi."""
    from trending_scanner import _get_fallback_viral_trends, scan_youtube_shorts_trends

    try:
        trends = scan_youtube_shorts_trends(topic, time_filter="day")
        if not trends:
            trends = _get_fallback_viral_trends(topic)
    except Exception:
        trends = _get_fallback_viral_trends(topic)

    competitors = [
        {
            "title": t.get("title", ""),
            "views_label": t.get("views", ""),
            "channel": t.get("channel", ""),
            "viral_score": t.get("viral_score", 0),
            "format_hint": t.get("hook_analysis", ""),
        }
        for t in trends[:3]
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
    """Item 396: Kanal Hakkında Kısmında İletişim."""
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
    """Item 109 – Özgün Başlık Üretimi (5 özgün başlık varyasyonu)."""
    kw = keyword or main_title
    finalize_fn = _vsa_attr("finalize_seo_title", lambda t, **_k: t)
    fallback_variants = [
        finalize_fn(f"{kw} Hakkında Kimsenin BİLMEDİĞİ Gerçek #Shorts"),
        finalize_fn(f"Bu {kw} Sırrını Öğrenince ŞOK Olacaksınız #Shorts"),
        finalize_fn(f"{kw}: Gizli Kalmış İNANILMAZ Detaylar #Shorts"),
        finalize_fn(f"Neden {kw}? Asıl GERÇEK Burada #Shorts"),
        finalize_fn(f"{kw}: Uzmanların SAKLADIĞI Bilgi #Shorts"),
    ]

    llm_client_fn = _vsa_attr("_seo_llm_client", lambda: (None, "", ""))
    client_info = llm_client_fn()
    if not client_info[0]:
        return fallback_variants

    client, provider_name, model_name = client_info
    call_fn = _vsa_attr("_call", _call)
    clean_json_fn = _vsa_attr("_clean_json", _clean_json)
    quota_err_fn = _vsa_attr("_is_quota_error", lambda _e: False)
    print(f"  [Item 109] '{main_title}' için 5 özgün başlık varyasyonu üretiliyor...")
    try:
        params = dict(
            model=model_name,
            messages=[
                {"role": "system", "content": TITLE_VARIANTS_PROMPT},
                {"role": "user", "content": f"Ana başlık: {main_title}\nAnahtar kelime: {kw}"},
            ],
            temperature=0.85,
            max_tokens=500,
        )
        if provider_name in ("Gemini", "OpenAI"):
            params["response_format"] = {"type": "json_object"}

        resp = call_fn(client, params, provider_name=provider_name, model_name=model_name)
        raw = resp.choices[0].message.content.strip()
        data = clean_json_fn(raw)

        if data and "variants" in data and isinstance(data["variants"], list):
            variants = [finalize_fn(v) for v in data["variants"] if isinstance(v, str) and len(v) > 5]
            if len(variants) >= 3:
                return variants[:5]

    except Exception as e:
        if quota_err_fn(e):
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
    """Paste-ready YouTube Studio metadata — auto-upload out of scope."""
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
        "channel_trailer_short": "En iyi performans gösteren Shorts'u kanal fragmanı yapın (Item 366).",
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
    script_context: str = "",
    related_video_url: str = "",
    business_email: str = "",
    target_country: str = "TR",
    lang: str = "tr",
    video_filename: str = "",
    thumb_path: str = "",
    total_renders: int = 0,
) -> Dict[str, Any]:
    """Batch 4 — B6 SEO operator pack: tüm otomatik SEO metadata + Studio yapıştırma rehberi."""
    from growth_tactics import (
        generate_studio_engagement_checklist,
        generate_weekly_live_stream_plan,
        should_show_notification_bell_cta,
    )
    from proof_archiver import ProofArchiver

    clean_title = title or keyword
    gen_meta_fn = _vsa_attr("generate_viral_seo_metadata", None)
    cfg = _vsa_attr("config", config)
    seo_meta = gen_meta_fn(
        clean_title,
        source_name=source_name,
        retention_metadata=retention_metadata,
        script_context=script_context,
        lang=lang,
    ) if gen_meta_fn else {}
    engagement = generate_studio_engagement_checklist(lang=lang)
    live_plan = generate_weekly_live_stream_plan(lang=lang)
    upload_sched = get_optimal_upload_schedule(target_country)
    cta_timing = calculate_cta_timing(total_duration=float(getattr(cfg, "TARGET_DURATION", 45.0) or 45.0))
    studio_fields = build_studio_metadata_fields(
        keyword=clean_title, tags=seo_meta.get("tags"), target_country=target_country, lang=lang,
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
