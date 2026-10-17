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

A/B variant generation, hashtag tables, language templates, and Studio operator
pack helpers are modularized in `production/seo_ab_variants.py` and re-exported here.
"""

from __future__ import annotations

import os
import random
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

import config
from copyright_risk import scan_copyright_risk
from headline_transformer import convert_headline_to_question
from production.seo_ab_variants import (
    TITLE_VARIANTS_PROMPT,
    attach_shopping_product_tags,
    build_studio_metadata_fields,
    calculate_cta_timing,
    export_seo_operator_pack,
    finalize_seo_compliance,
    generate_15_viral_tags,
    generate_competitor_analysis_brief,
    generate_end_screen_guidance,
    generate_related_video_bridge,
    generate_title_variants,
    get_channel_contact_guidance,
    get_channel_master_keywords,
    get_optimal_upload_schedule,
)
from scene_generator import _call, _clean_json


SEO_SYSTEM_PROMPT = """Sen profesyonel bir YouTube SEO Uzmanı, Algoritma Mühendisi ve Viral İçerik Stratejistisin.
Görevin: Verilen YouTube Shorts videosu için videonun konusuna ve SENARYOSUNA TAMAMEN ÖZEL, doğal, akıcı bir SEO açıklaması ve 15 adet gerçek YouTube arama etiketi üretmektir.

KRİTİK KURALLAR:
1. "seo_title": Tıklama oranını (CTR) maksimize edecek ilgi çekici Shorts başlığı.
   - 45-60 karakter arasında olmalı (Item 346).
   - Sadece tek bir kilit kelime BÜYÜK yazılmalı (Item 347: örn. GERÇEK, ASLA, SAKIN, GİZLİ, ŞOK).
   - Sonunda #Shorts hashtag'i bulunmalı.
2. "seo_description": Videoya ÖZEL, senaryodaki asıl olayı/detayları özetleyen, doğal ve akıcı YouTube açıklaması:
   - "Tarihsel ve felsefi arka planı, uzmanların gözden kaçırdığı boyutlarıyla..." gibi robotik veya şablon ifadeler ASLA KULLANMA.
   - Videonun senaryosunda geçen asıl sırrı veya olay akışını 2-3 akıcı cümleyle özetle.
   - İzleyicileri yoruma teşvik eden videoya özel düşündürücü/kışkırtıcı bir soru sor.
   - Metnin sonuna videonun nişine uygun 3 odaklı hashtag ekle (#Shorts ve 2 spesifik etiket).
3. "tags": Videonun konusuyla birebir ilgili, insanların YouTube arama kutusuna yazdığı TAM 15 ADET yüksek hacimli arama etiketi.
   - Dizi halinde olmalı: ["etiket1", "etiket2", ..., "etiket15"].
   - Gerçek arama terimleri olmalı (örn. 'beden dili taktikleri', 'göz teması anlamı', 'yalan tespiti').
   - Başlığı rastgele kelimelere bölüp ('ve', 'ile', 'için', 'nın', 'karşı', 'tarafın' gibi) anlamsız parçalar ASLA üretme!
4. "hook_text": İlk 3 saniyede izleyiciyi ekrana kilitleyecek 10-15 kelimelik çarpıcı kanca cümlesi.
5. "pinned_comment": Videodaki konuyla ilgili izleyicileri tartışmaya sokacak videoya özel sabitleme yorumu.
6. "affiliate_text": Profil veya kaynak linkine yönlendiren kısa CTA.

SADECE GEÇERLİ JSON DÖNDÜR:
{
  "hook_text": "...",
  "seo_title": "...",
  "seo_description": "...",
  "tags": ["etiket1", "etiket2", ..., "etiket15"],
  "pinned_comment": "...",
  "affiliate_text": "..."
}
"""

SEO_PROMPT = SEO_SYSTEM_PROMPT
_SEO_LITE_MODEL = "gemini-flash-lite-latest"


def _seo_candidate_models() -> List[str]:
    """Candidate models in priority order for SEO generation with graceful failover."""
    defaults = [
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
        "gemini-flash-latest",
        "gemini-3.5-flash-lite",
        "gemma-4-26b-a4b-it",
        "gemini-3.8-flash",
    ]
    configured = (getattr(config, "GEMINI_MODEL", "") or "").strip()
    candidates: List[str] = []
    if configured and "pro" not in configured.lower() and configured not in defaults:
        candidates.append(configured)
    for m in defaults:
        if m not in candidates:
            candidates.append(m)
    return candidates


def _resolve_seo_model() -> str:
    """SEO metadata uses lightweight Gemini — avoid Pro-tier quota burn."""
    models = _seo_candidate_models()
    return models[0] if models else _SEO_LITE_MODEL


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("429", "quota", "rate limit", "resource_exhausted", "resource exhausted"))


def _is_mocked_seo_llm() -> bool:
    return bool(
        hasattr(OpenAI, "_mock_name")
        or "unittest.mock" in type(OpenAI).__module__
        or hasattr(_call, "_mock_name")
        or "unittest.mock" in type(_call).__module__
    )


def _seo_llm_client():
    """Prefer Gemini key + GEMINI_MODEL; fall back to auto-detected AI provider."""
    if (
        os.environ.get("PYTEST_CURRENT_TEST")
        or os.environ.get("SHORTS_FORCE_PROCEDURAL_FALLBACK") == "1"
    ) and not _is_mocked_seo_llm():
        return None, "", ""
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


def finalize_seo_title(title: str, lang: str = "tr") -> str:
    """Items 346-348: single-word caps → curiosity prefix → 45-60 char limit."""
    title = format_capital_hook_word(title)
    title = inject_curiosity_words(title, lang=lang)
    return enforce_title_length_limit(title)


_DANGLING_TAIL_WORDS = {
    "ve", "veya", "ile", "için", "icin", "bu", "o", "şu", "en", "bir", "de", "da", "ki",
    "ama", "fakat", "gibi", "kadar", "olan", "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with"
}


def enforce_title_length_limit(title: str, min_len: int = 40, max_len: int = 60) -> str:
    """Item 346: Başlık Uzunluğu Sınırı (45-60 karakter aralığı)."""
    if min_len < 0 or min_len > max_len:
        raise ValueError("min_len must be between 0 and max_len")
    clean = re.sub(r'\s+', ' ', title).strip()
    if len(clean) > max_len:
        words = clean.split()
        trimmed_words: List[str] = []
        for w in words:
            candidate = " ".join(trimmed_words + [w])
            if len(candidate) <= max_len - 8:
                trimmed_words.append(w)
            else:
                break
        while trimmed_words and trimmed_words[-1].lower() in _DANGLING_TAIL_WORDS:
            trimmed_words.pop()
        trimmed = " ".join(trimmed_words).strip()
        if not trimmed:
            trimmed = clean[:max_len - 8].strip()
        if not trimmed.endswith("#shorts") and not trimmed.endswith("#Shorts"):
            trimmed = f"{trimmed} #Shorts"
        return trimmed
    return clean


def format_capital_hook_word(title: str) -> str:
    """Item 347: Büyük Harf Stratejisi (sadece tek bir kilit kelime BÜYÜK yazılır)."""
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
    """Item 348: Başlıkta Merak Kelimeleri (Curiosity Multipliers)."""
    CURIOUS_WORDS_TR = ["Gizli", "Yasaklanan", "Bilinmeyen", "Şok Eden", "Akıl Almaz", "Gözden Kaçan"]
    CURIOUS_WORDS_EN = ["Hidden", "Forbidden", "Unknown", "Shocking", "Untold", "Mind-Bending"]

    words = CURIOUS_WORDS_TR if lang == "tr" else CURIOUS_WORDS_EN
    if any(c.lower() in title.lower() for c in words):
        return title
    if len(title.strip()) >= 45 or len(title.split()) >= 6:
        return title
    chosen = random.choice(words)
    return f"{chosen} {title}"


def enforce_three_hashtag_rule(title_or_desc: str, niche_tag: str, general_tag: str = "viral") -> str:
    """Item 349: 3-Hashtag Dağılım Kuralı (#Shorts + #nis + #genel)."""
    fallback_tag = (
        re.sub(r'[^\w]', '', title_or_desc.strip().split()[0]).lower()
        if title_or_desc.strip() else ""
    )
    clean_niche = re.sub(r'[^\w]', '', niche_tag.lstrip('#')).lower() or fallback_tag or "shorts"
    clean_general = re.sub(r'[^\w]', '', general_tag.lstrip('#')).lower() or "viral"
    return " ".join(["#Shorts", f"#{clean_niche}", f"#{clean_general}"])


def prepend_description_engagement_question(description: str, keyword: str = "", lang: str = "tr") -> str:
    """Item 383: Açıklamaya Kısa Soru Yazma."""
    low = description.lower()
    if description.strip().startswith("💬") or "ne düşünüyorsunuz" in low or "what do you think" in low:
        return description
    first_block = description.strip().split("\n\n")[0]
    if "?" in first_block:
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


def append_research_source_reference(description: str, keyword: str = "", source_name: str = "") -> str:
    """Item 83 & 140: Açıklamada Kaynak Belirtme ve Shorts İçi Yasal Bildirimler."""
    if "📌 Kaynak & Araştırma:" in description or "📌 Research & Source:" in description:
        return description

    kw_low = f"{source_name} {keyword}".lower()
    if any(k in kw_low for k in ("psikoloji", "beden dili", "dark", "manipülasyon", "niyet", "göz teması", "zihin", "davranış")):
        default_ref = f"Akademik Psikoloji Literatürü & Davranış Bilimleri İncelemesi ({keyword.strip() or 'Psikoloji'})"
    elif any(k in kw_low for k in ("bilim", "uzay", "science", "space", "myth", "gizem", "fizik")):
        default_ref = f"Bilimsel Literatür, Akademik Veri & Açık Kaynak İncelemesi ({keyword.strip() or 'Bilim'})"
    elif any(k in kw_low for k in ("finans", "kripto", "para", "borsa", "yatırım", "crypto", "business")):
        default_ref = f"Finansal Veri Tabanları, Piyasa Raporları & Açık Kaynak İncelemesi ({keyword.strip() or 'Ekonomi'})"
    elif any(k in kw_low for k in ("reddit", "itiraf", "hikaye", "aita")):
        default_ref = f"Topluluk Arşivleri & Açık Kaynak Sosyal İnceleme ({keyword.strip() or 'Topluluk'})"
    else:
        default_ref = f"Tarihsel Arşiv, Akademik Literatür & Açık Kaynak İncelemesi ({keyword.strip() or 'Genel Kültür'})"

    ref_name = source_name.strip() if source_name else default_ref
    source_block = (
        f"\n\n📌 Kaynak & Araştırma: {ref_name}\n"
        f"⚖️ Yasal Bildirim (Fair Use): Tüm görseller eğitim ve adil kullanım (Fair Use) kapsamındadır. "
        f"Bu video eğitim ve bilgilendirme amacıyla bağımsız olarak araştırılmış; özgün sesli analiz ve transformatif görsel kurguyla üretilmiştir."
    )
    return description.rstrip() + source_block


def build_natural_seo_description(
    keyword: str,
    hook: str = "",
    bullet_points: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    source_name: str = "",
    niche: str = "",
    lang: str = "tr",
) -> str:
    """Item 352: Açıklama Kısmına Doğal Metin (Narrative Description)."""
    hook_part = hook.strip() if hook else f"{keyword} hakkında bilmeniz gereken en kritik detaylar bu videoda."
    if keyword.lower() not in hook_part.lower():
        hook_part = f"{keyword} – {hook_part}"

    niche_lower = f"{niche} {source_name} {keyword}".lower()
    if any(k in niche_lower for k in ("psikoloji", "beden dili", "manipülasyon", "niyet", "göz teması", "zihin", "davranış", "dark_psychology")):
        narrative = "Bilinçaltı dinamikleri ve insan davranışlarının gizli psikolojik kodlarını inceliyoruz."
    elif any(k in niche_lower for k in ("tarih", "ancient", "roma", "imparator", "arkeoloji", "felsefe", "stoic")):
        narrative = "Tarihsel ve felsefi arka planı, uzmanların gözden kaçırdığı boyutlarıyla inceliyoruz."
    elif any(k in niche_lower for k in ("bilim", "uzay", "gizem", "science", "space", "myth", "beş gerçek", "five_facts")):
        narrative = "Bilimsel veriler ve henüz açıklanamayan gizemli detayları mercek altına alıyoruz."
    elif any(k in niche_lower for k in ("finans", "kripto", "para", "borsa", "yatırım", "crypto", "business")):
        narrative = "Piyasa dinamikleri, finansal gerçekler ve stratejik ipuçlarını inceliyoruz."
    elif any(k in niche_lower for k in ("reddit", "itiraf", "hikaye", "aita", "dram", "aile")):
        narrative = "Yaşanan bu çarpıcı olayın perde arkasını ve düşündürücü detaylarını inceliyoruz."
    elif any(k in niche_lower for k in ("ürün", "urun", "alet", "cihaz", "gadget", "temu")):
        narrative = "Öne çıkan özellikleri, kullanım avantajlarını ve kullanıcı deneyimini değerlendiriyoruz."
    else:
        narrative = "Konunun en çarpıcı detaylarını ve uzmanların gözden kaçırdığı boyutlarını inceliyoruz."

    desc = f"{hook_part} {narrative} İzlediğiniz için teşekkürler; yeni bölümler için abone olup bildirimleri açmayı unutmayın!"

    if bullet_points:
        desc += "\n\n📌 Önemli Noktalar:\n" + "\n".join([f"• {bp}" for bp in bullet_points[:3]])

    desc = append_research_source_reference(desc, keyword=keyword, source_name=source_name or niche)

    description_tags = []
    for raw_tag in tags or []:
        clean_tag = re.sub(r"[^\w]", "", str(raw_tag or "").lstrip("#")).lower()
        if clean_tag and clean_tag not in {"shorts", "viral"} and clean_tag not in description_tags:
            description_tags.append(clean_tag)
    first_tag = description_tags[0] if description_tags else (
        re.sub(r'[^\w]', '', keyword.split()[0]) if keyword.split() else "Shorts"
    )
    general_tag = description_tags[1] if len(description_tags) > 1 else "viral"
    tag_block = enforce_three_hashtag_rule("", niche_tag=first_tag, general_tag=general_tag)
    desc += f"\n\n{tag_block}"
    desc = prepend_description_engagement_question(desc, keyword=keyword, lang=lang)
    disc_cat = _infer_legal_disclaimer_category(keyword, niche)
    if disc_cat:
        from proof_archiver import ProofArchiver
        desc += f"\n\n{ProofArchiver.generate_legal_disclaimer(disc_cat, lang=lang)}"
    return desc


def enrich_seo_with_retention_metadata(seo_data: dict, retention_metadata: dict = None, lang: str = "tr") -> dict:
    """Items 209-210: spotted mistake bait + polarizing dilemma → SEO/yorum paketi."""
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


def generate_viral_seo_metadata(
    keyword: str,
    source_name: str = "",
    retention_metadata: dict = None,
    visual_manifest=None,
    script_context: str = "",
    niche: str = "",
    lang: str = "tr",
) -> dict:
    effective_niche = niche or source_name
    fallback_title = finalize_seo_title(f"{keyword}: Bu Gerçeği ASLA Unutmayın #Shorts", lang=lang)
    fallback_tags = generate_15_viral_tags(keyword, niche=effective_niche, lang=lang)
    fallback = {
        "hook_text": f"{keyword} hakkında kimsenin bilmediği gerçekler!",
        "seo_title": fallback_title,
        "seo_description": build_natural_seo_description(
            keyword,
            hook=f"{keyword} hakkında şok edici detaylar ve gizli kalmış sırlar bu videoda.",
            source_name=source_name,
            niche=effective_niche,
            lang=lang,
        ),
        "tags": fallback_tags,
        "pinned_comment": f"Sizce {keyword} konusundaki en şaşırtıcı detay neydi? Yorumlarda buluşalım! 👇",
        "affiliate_text": "🔗 Bahsedilen ürün ve kaynak linkleri profilimde!",
    }

    user_prompt_parts = [f"Başlık / Anahtar Kelime: {keyword}"]
    if script_context and script_context.strip():
        user_prompt_parts.append(f"Videonun Gerçek Senaryosu / Metni:\n{script_context.strip()[:1800]}")
    if effective_niche:
        user_prompt_parts.append(f"İçerik Nişi: {effective_niche}")
    if lang:
        user_prompt_parts.append(f"Dil: {lang}")
    user_content = "\n\n".join(user_prompt_parts)

    gemini_key = (getattr(config, "GEMINI_API_KEY", "") or "").strip()
    ai_candidates = []
    skip_live_llm = (
        os.environ.get("PYTEST_CURRENT_TEST")
        or os.environ.get("SHORTS_FORCE_PROCEDURAL_FALLBACK") == "1"
    ) and not _is_mocked_seo_llm()
    if not skip_live_llm and gemini_key:
        c = OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            timeout=10.0,
        )
        for m in _seo_candidate_models():
            ai_candidates.append((c, "Gemini", m))

    if not skip_live_llm and getattr(config, "OPENAI_API_KEY", ""):
        c = OpenAI(api_key=config.OPENAI_API_KEY, timeout=10.0)
        ai_candidates.append((c, "OpenAI", "gpt-4o-mini"))

    if not skip_live_llm and getattr(config, "DEEPSEEK_API_KEY", ""):
        c = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com", timeout=10.0)
        ai_candidates.append((c, "DeepSeek", "deepseek-chat"))

    if not skip_live_llm and not ai_candidates and getattr(config, "AI_API_KEY", "") and getattr(config, "AI_BASE_URL", ""):
        c = OpenAI(api_key=config.AI_API_KEY, base_url=config.AI_BASE_URL, timeout=10.0)
        m = config.AI_MODEL if config.AI_MODEL and config.AI_MODEL != "procedural" else _SEO_LITE_MODEL
        ai_candidates.append((c, config.AI_PROVIDER or "AI", m))

    if not ai_candidates:
        enriched = enrich_seo_with_retention_metadata(fallback, retention_metadata, lang=lang)
        return finalize_seo_compliance(
            attach_shopping_product_tags(enriched, keyword),
            visual_manifest=visual_manifest,
            lang=lang,
            niche=effective_niche,
        )

    print(f"\n  [Viral SEO Agent] '{keyword}' için yapay zeka ile videoya özel SEO ve etiketler üretiliyor...")

    for client, provider_name, model_name in ai_candidates:
        try:
            params = dict(
                model=model_name,
                messages=[
                    {"role": "system", "content": SEO_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            if provider_name in ("Gemini", "OpenAI") and "gemma" not in model_name.lower():
                params["response_format"] = {"type": "json_object"}

            resp = _call(client, params, provider_name=provider_name, model_name=model_name)
            raw = resp.choices[0].message.content.strip()
            data = _clean_json(raw)

            if data and isinstance(data, dict) and "seo_title" in data and "seo_description" in data:
                raw_title = data["seo_title"]
                try:
                    from research_service import align_title_to_youtube_search
                    align = align_title_to_youtube_search(keyword, raw_title, lang=lang)
                    if align.get("aligned_title"):
                        raw_title = align["aligned_title"]
                        data["search_alignment"] = align
                except Exception:
                    pass
                data["seo_title"] = finalize_seo_title(raw_title, lang=lang)

                desc = data["seo_description"].strip()
                desc = append_research_source_reference(desc, keyword=keyword, source_name=source_name or effective_niche)
                desc = prepend_description_engagement_question(desc, keyword=keyword, lang=lang)
                data["seo_description"] = desc

                ai_tags = data.get("tags") or []
                cleaned_tags = []
                if isinstance(ai_tags, list):
                    for t in ai_tags:
                        t_str = str(t).strip().lower()
                        if t_str and t_str not in cleaned_tags and len(t_str) <= 40:
                            cleaned_tags.append(t_str)

                if len(cleaned_tags) < 15:
                    pad = generate_15_viral_tags(keyword, niche=effective_niche, lang=lang)
                    for pt in pad:
                        if pt not in cleaned_tags and len(cleaned_tags) < 15:
                            cleaned_tags.append(pt)

                data["tags"] = cleaned_tags[:15]
                print(f"    [OK] Viral SEO açıklaması ve {len(data['tags'])} etiket {provider_name} ({model_name}) ile videoya özel başarıyla üretildi.")
                try:
                    from quota_manager import quota_tracker
                    quota_tracker.record_call(provider_name)
                except Exception:
                    pass

                return finalize_seo_compliance(
                    attach_shopping_product_tags(
                        enrich_seo_with_retention_metadata(data, retention_metadata, lang=lang),
                        keyword,
                    ),
                    visual_manifest=visual_manifest,
                    lang=lang,
                    niche=effective_niche,
                )
        except Exception as e:
            if _is_quota_error(e) or "503" in str(e) or "404" in str(e):
                print(f"    [SEO] {model_name} müsait değil ({str(e)[:60]}), sonraki modele geçiliyor...")
                continue
            else:
                print(f"    [SEO] {model_name} hata ({str(e)[:60]}), sonraki modele geçiliyor...")
                continue

    print("    [SEO] Tüm AI modelleri başarısız oldu — procedural fallback kullanılıyor.")
    return finalize_seo_compliance(
        attach_shopping_product_tags(
            enrich_seo_with_retention_metadata(fallback, retention_metadata, lang=lang),
            keyword,
        ),
        visual_manifest=visual_manifest,
        lang=lang,
        niche=effective_niche,
    )
