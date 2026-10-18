"""Advanced niche-aware topic suggestion pipeline.

Combines YouTube Shorts signals, YouTube Autocomplete live queries,
curated 37-niche viral vault, AI generation with think-tag stripping,
dynamic seed formulation, topic-specific editorial metadata synthesis,
and deduplication against recent assets and session history.
"""
from __future__ import annotations

import hashlib
import logging
import os
import random
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set, Tuple

import config
from database import get_recent_videos
from director.visual_intent import resolve_topic_intelligence
from niche_templates import NICHES, get_niche_family, get_niche_production_profile
from research_service import (
    extract_format_fingerprint_from_title,
    fetch_youtube_autocomplete_suggestions,
)
from services.niche_topic_vault import get_curated_topics_for_niche, resolve_canonical_niche
from services.topic_suggester_sources import (
    SOURCE_AI,
    SOURCE_GOOGLE_TRENDS,
    SOURCE_REDDIT,
    SOURCE_RSS,
    SOURCE_TREND,
    SOURCE_VAULT,
    SOURCE_YOUTUBE,
    _GENERIC_PATTERNS,
    _THINK_BLOCK_RE,
    _UNCLOSED_THINK_BLOCK_RE,
    _clean_llm_text,
    _fetch_google_trend_candidates,
    _fetch_reddit_candidates,
    _fetch_rss_candidates,
    _fetch_trend_candidates,
    _fetch_youtube_candidates,
    _generate_ai_candidates,
    _is_generic,
    _is_hook_boilerplate,
)
from trending_scanner import scan_youtube_shorts_trends

logger = logging.getLogger(__name__)

_STOPWORDS: Set[str] = {
    "bir", "için", "ile", "olan", "olarak", "daha", "çok", "her", "gibi",
    "kadar", "sonra", "önce", "hakkında", "üzerine", "nasıl", "neden",
    "ancak", "sadece", "bütün", "kendi", "kendisi", "aynı", "yeni", "büyük", "küçük",
    "gün", "şey", "var", "yok", "ama", "veya", "hem", "ise", "diye",
    "bunu", "şunu", "onun", "bize", "size", "beni", "seni", "sizi", "sizin",
    "bizden", "değil", "değildir", "olmaz", "olur", "eder", "eden", "ettiği",
    "the", "and", "for", "with", "that", "this", "from", "your", "you",
    "are", "how", "why", "what", "when", "into", "over", "most", "more",
    "will", "can", "about", "never", "every", "these", "those", "their",
}


def _tr_lower(text: str) -> str:
    return (text or "").replace("İ", "i").replace("I", "ı").lower()


def _smart_focus(text: str, max_len: int = 52) -> str:
    cleaned = re.sub(
        r"\s+(?:hadis-i şerifi ve (?:hikmeti|fazileti|mesajı)|hadis-i şerifi|"
        r"hadisi ve (?:hikmeti|fazileti)|hadisi|ayet-i kerimesi|ayeti|müjdesi|tesellisi)\s*$",
        "",
        text.strip(),
        flags=re.IGNORECASE,
    ).strip()
    if not cleaned:
        cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    words = cleaned.split()
    acc: List[str] = []
    for w in words:
        cand = " ".join(acc + [w])
        if len(cand) > max_len and acc:
            break
        acc.append(w)
    return " ".join(acc)


def _slugify_topic(title: str) -> str:
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    safe = re.sub(r"[^\w\s-]", "", title.translate(tr_map))
    return re.sub(r"\s+", "_", safe.strip())[:80].casefold()


def _collect_used_topics(exclude_titles: Optional[List[str]] = None) -> Set[str]:
    used: Set[str] = set()
    assets_dir = config.ASSETS_DIR
    if os.path.isdir(assets_dir):
        for name in os.listdir(assets_dir):
            path = os.path.join(assets_dir, name)
            if os.path.isdir(path):
                used.add(name.casefold())
    try:
        for row in get_recent_videos(100):
            kw = (row.get("keyword") or row.get("title") or "").strip()
            if kw:
                used.add(_slugify_topic(kw))
                used.add(kw.casefold())
    except Exception as exc:
        logger.warning("recent topic list unavailable: %s", exc)
    if exclude_titles:
        for t in exclude_titles:
            clean_t = str(t or "").strip()
            if clean_t:
                used.add(_slugify_topic(clean_t))
                used.add(clean_t.casefold())
    return used


def _niche_context_words(niche_id: str) -> Set[str]:
    profile = get_niche_production_profile(niche_id)
    niche = NICHES.get(niche_id, NICHES["1_news_flash"])
    curated_tr = get_curated_topics_for_niche(niche_id, lang="tr")
    curated_en = get_curated_topics_for_niche(niche_id, lang="en")
    blob = " ".join([
        profile.get("name", ""),
        profile.get("category", ""),
        profile.get("tone", ""),
        " ".join(niche.get("trending_keywords", [])),
        " ".join(curated_tr[:15]),
        " ".join(curated_en[:10]),
    ])
    return {
        w
        for w in re.findall(r"\w{3,}", _tr_lower(blob))
        if w not in _STOPWORDS and not w.isdigit()
    }


def _topic_hint_matches_niche(topic_hint: str, niche_id: str) -> bool:
    hint = (topic_hint or "").strip()
    if not hint:
        return False

    canonical_niche = resolve_canonical_niche(niche_id)
    intelligence = resolve_topic_intelligence(hint, canonical_niche)
    if resolve_canonical_niche(intelligence["resolved_niche"]) != canonical_niche:
        return False
    if intelligence["match_method"] != "passthrough":
        return True

    hint_words = {
        w
        for w in re.findall(r"\w{3,}", _tr_lower(hint))
        if w not in _STOPWORDS
    }
    return bool(hint_words & _niche_context_words(canonical_niche))


def _generate_seed_based_topics(
    seed_keyword: str, niche_id: str, count: int = 5, language: str = "tr"
) -> List[Dict[str, Any]]:
    """Synthesize high-CTR viral topic candidates directly from a user seed keyword."""
    if resolve_canonical_niche(niche_id) == "10_religious_quotes":
        return []

    raw = (seed_keyword or "").strip()
    raw = re.sub(r"#\w+", "", raw)
    clean = re.sub(r"[^\w\s\u00C0-\u017F-]", "", raw).strip()
    clean = re.sub(r"\bshorts\b", "", clean, flags=re.I).strip()
    if len(clean) < 3:
        return []

    words = clean.split()
    cap_seed = " ".join(w.capitalize() for w in words)
    is_tr = (language or "tr").lower()[:2] != "en"

    if not is_tr:
        templates = [
            f"3 Shocking Facts About {cap_seed}",
            f"The Hidden Truth About {cap_seed}",
            f"3 Critical Mistakes With {cap_seed}",
            f"The Untold Secret of {cap_seed}",
            f"3 Golden Rules for {cap_seed}",
            f"What Nobody Tells You About {cap_seed}",
            f"3 Powerful Tips to Master {cap_seed}",
            f"The Dark Side of {cap_seed} Experts Won't Tell You",
        ]
    else:
        templates = [
            f"{cap_seed} Hakkında 3 Şaşırtıcı Gerçek",
            f"{cap_seed} Konusunda En Yaygın 3 Hata",
            f"Kimsenin Bahsetmediği Gizli {cap_seed} Sırrı",
            f"{cap_seed} İçin 3 Altın Kural",
            f"{cap_seed} ile Hayatınızı Kolaylaştıracak 3 Yöntem",
            f"{cap_seed} Hakkında Bilmeniz Gereken 3 Şey",
            f"{cap_seed}: Çoğu İnsanın Bilmediği O Gerçek",
            f"Sıfırdan Başlayanlar İçin {cap_seed} Rehberi",
        ]
    templates = [t for t in templates if len(t) <= 75]
    random.shuffle(templates)

    out: List[Dict[str, Any]] = []
    for t in templates[:count]:
        out.append({
            "title": t,
            "source": SOURCE_AI,
            "viral_score": 95,
            "is_seed_tailored": True,
        })
    return out


def _extract_topic_features(topic: str) -> Tuple[str, str, List[str]]:
    """Extract citation in parentheses, core focus phrase, and meaningful tags."""
    citation_match = re.search(r"\(([^()]{2,35})\)", topic)
    citation = citation_match.group(1).strip() if citation_match else ""
    base = re.sub(r"\s*\([^()]*\)\s*", " ", topic).strip()
    quote_match = re.search(r"['\"“”]([^'\"“”]{4,60})['\"“”]", base)
    if quote_match:
        focus = _smart_focus(quote_match.group(1), max_len=52)
    elif ":" in base:
        parts = [p.strip() for p in base.split(":", 1) if p.strip()]
        focus = _smart_focus(parts[0] if len(parts[0]) >= 10 else base, max_len=52)
    else:
        focus = _smart_focus(base, max_len=52)

    raw_words = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]{4,}", base)
    tags: List[str] = []
    if citation:
        cit_tag = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]", "", citation.split(",")[0].title())
        if len(cit_tag) >= 3:
            tags.append(f"#{cit_tag}")
    skip_tag_words = _STOPWORDS | {
        "hadis", "hadisi", "şerif", "şerifi", "ayet", "ayeti", "suresi",
        "bakar", "giremez", "istediğini", "istem", "isteme", "yatan",
    }
    for w in raw_words:
        low = _tr_lower(w)
        if low in skip_tag_words:
            continue
        tag = f"#{w[0].upper()}{_tr_lower(w[1:])}"
        if _tr_lower(tag) not in {_tr_lower(t) for t in tags}:
            tags.append(tag)
        if len(tags) >= 4:
            break
    return citation, focus, tags


def _build_topic_editorial_metadata(
    topic: str,
    niche_id: str,
    language: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate unique, topic-specific hook, scene roadmap, angle, and tags for a topic."""
    is_tr = (language or "tr").lower()[:2] != "en"
    canonical_niche = resolve_canonical_niche(niche_id) or niche_id
    family = get_niche_family(canonical_niche)
    citation, focus, tags = _extract_topic_features(topic)
    digest = int(hashlib.md5(topic.encode("utf-8")).hexdigest()[:8], 16)
    num_match = re.search(r"\b(\d+)\b", topic)
    num_val = num_match.group(1) if num_match else ""

    if canonical_niche == "10_religious_quotes":
        low = _tr_lower(topic)
        is_ayah = any(
            k in low
            for k in (
                "ayet", "suresi", "bakara", "inşirah", "rad ", "ibrahim",
                "imran", "zümer", "talak", "duha", "hucurat", "lokman",
                "mülk", "asr", "quran", "surah", "verse",
            )
        )
        is_dua = any(k in low for k in ("dua", "niyaz", "prayer", "şifa", "ferah"))
        src_ref = citation or ("Kur'an-ı Kerim" if is_ayah else "Sahih Kaynak")

        if is_tr:
            if is_ayah:
                angle = "🕋 Ayet Meali & Hikmet"
                hooks = [
                    f"{src_ref} kaynağındaki '{focus}' ilahi mesajı daralan kalplere nasıl inşirah veriyor?",
                    f"Hayatın yükü ağırlaştığında {src_ref} ayetinin hatırlattığı '{focus}' tesellisini tefekkür edin.",
                    f"{src_ref} mealindeki '{focus}' hakikati, zorluklara bakış açınızı kökten değiştirecek.",
                    f"Kalbinizin aradığı gerçek huzur, {src_ref} ayetinin '{focus}' müjdesinde saklı.",
                ]
                summary = (
                    f"Sahne Planı: 1) {src_ref} ayetine manevi giriş · 2-4) Tashkeelli Arapça hat, "
                    f"Türkçe meal ve '{focus}' tefsiri · 5-6) Günlük hayata hikmetli ders ve dua."
                )
                why_viral = "İlahi Müjde + Yüksek Kaydetme & Paylaşım"
            elif is_dua:
                angle = "🤲 Nebevî Dua & Fazilet"
                hooks = [
                    f"Zorluk anında Peygamber Efendimiz'in ({src_ref}) sığındığı '{focus}' duası kalbinizi ferahlatacak.",
                    f"Sabah ve akşam dilinizden düşürmeyeceğiniz '{focus}' niyazının faziletini biliyor musunuz?",
                    f"Gönlünüze sekinet indiren {src_ref} kaynaklı '{focus}' duasına kalpten 'Amin' deyin.",
                    f"Kapıların kapandığını hissettiğinizde {src_ref} rivayetindeki '{focus}' yakarışına kulak verin.",
                ]
                summary = (
                    f"Sahne Planı: 1) Kalbi hazırlayan açılış · 2-4) {src_ref} kaynaklı '{focus}' duası Arapça metni, "
                    f"Türkçe anlamı ve fazileti · 5-6) Huzur veren kapanış ve yorumlarda Amin daveti."
                )
                why_viral = "Manevi Ferahlık + Yorumlarda Amin Etkileşimi"
            else:
                angle = "📖 Sahih Hadis & Ahlak"
                hooks = [
                    f"{src_ref} kaynaklı '{focus}' hadis-i şerifi, müminin günlük hayat ölçüsünü nasıl belirliyor?",
                    f"Resulullah'ın (s.a.v.) {src_ref}'de rivayet edilen '{focus}' öğüdü, kalplere nasıl şifa oluyor?",
                    f"Amellerimizi ve ahlakımızı güzelleştiren '{focus}' nebevî düsturunu birlikte hatırlayalım.",
                    f"Asr-ı Saadetten günümüze ışık tutan {src_ref} kaynaklı '{focus}' hadisinin hikmeti.",
                ]
                summary = (
                    f"Sahne Planı: 1) '{focus}' nebevî ölçüsü · 2-4) {src_ref} sahih rivayetinin "
                    f"Arapça-Türkçe meali ve hikmeti · 5-6) Günlük hayatta uygulanacak sünnet ve ahlak dersi."
                )
                why_viral = "Sahih Kaynak Güveni + Yüksek Kaydetme Oranı"
            for fallback_tag in ("#HadisiŞerif", "#AyetMeali", "#İslam", "#Maneviyat"):
                if len(tags) >= 4:
                    break
                if _tr_lower(fallback_tag) not in {_tr_lower(t) for t in tags}:
                    tags.append(fallback_tag)
        else:
            angle = "🕋 Quran & Sahih Hadith" if is_ayah else "📖 Prophetic Wisdom"
            hooks = [
                f"Discover how '{focus}' ({src_ref}) brings immediate clarity and peace to a restless heart.",
                f"When life feels overwhelming, this timeless teaching on '{focus}' ({src_ref}) restores inner strength.",
                f"Reflect on the profound spiritual lesson behind '{focus}' ({src_ref}).",
            ]
            summary = (
                f"Scene Plan: 1) Spiritual reflection hook · 2-4) Arabic calligraphy, English meaning & wisdom of {src_ref} "
                f"· 5-6) Practical moral takeaway and peaceful closing."
            )
            why_viral = "Authentic Citation + High Save & Share Rate"
            if len(tags) < 3:
                tags.extend(["#Hadith", "#Quran", "#IslamicWisdom"][: 4 - len(tags)])

        hook = hooks[digest % len(hooks)]
        return {
            "hook": hook[:145],
            "angle": angle,
            "summary": summary[:230],
            "keywords": tags[:4],
            "scope": "45-55 sn · 6 Sahne" if is_tr else "45-55s · 6 Scenes",
            "why_viral": why_viral,
        }

    # Non-religious niches: craft distinct, topic-tailored hook, angle, and 6-scene roadmap
    if is_tr:
        angle_map = {
            "stoic": f"🏛️ {num_val + ' ' if num_val else ''}Stoacı Disiplin & Felsefe",
            "dark": f"🧠 {num_val + ' ' if num_val else ''}Psikolojik Analiz & Beden Dili",
            "crypto": "📊 Piyasa & Zincir Üstü Analiz",
            "news": "⚡ Son Dakika & Perde Arkası",
            "reddit": "🎭 Gerçek İtiraf & Hikâye Kurgusu",
            "whatsapp": "💬 Gerilim & Sürükleyici Hikâye",
            "quiz": f"❓ {num_val + ' Adımlı ' if num_val else ''}İnteraktif Merak & Test",
            "product": f"🛒 {num_val + ' ' if num_val else ''}Fiyat/Performans & İnceleme",
            "mystery": "🔍 Çözülemeyen Gizem & Kanıt Dosyası",
            "entertainment": "🎬 Kültür, Sinema & Ters Köşe",
            "astrology": "✨ Burç & Bilinçaltı Analizi",
            "tech": "🤖 Yapay Zeka & Üretkenlik Rehberi",
            "fitness": "💪 Bilimsel Sağlık & Biyohack",
            "automotive": "🏎️ Mühendislik & Hız Rekoru",
            "legal": "⚖️ Tüketici Hakkı & Yasal Taktik",
            "kids": "🌟 Eğitici & Pedagojik Anlatım",
        }
        angle = angle_map.get(family, "🔥 Yüksek Merak & Bilgi Kurgusu")
        hooks_tr = [
            f"'{focus}' konusunda çoğu insanın gözden kaçırdığı o kritik detayı ilk 5 saniyede görün.",
            f"Bugüne kadar '{focus}' hakkında doğru bildiğiniz her şeyi sorgulatacak somut gerçekler.",
            f"'{focus}' başlığının perde arkasındaki mekanizmayı ve hayatınıza doğrudan etkisini inceliyoruz.",
            f"Sadece 45 saniyede '{focus}' konusunun en çarpıcı kanıtlarını ve uygulanabilir kurallarını keşfedin.",
        ]
        hook = hooks_tr[digest % len(hooks_tr)]
        summary = (
            f"Sahne Planı: 1) '{focus}' merak kancası · 2-4) Somut vaka, veri ve "
            f"{num_val + ' maddelik ' if num_val else ''}derin analiz · 5-6) Pratik çıkarım ve yorum sorusu."
        )
        why_viral = (
            f"{num_val} Maddelik Liste + Yüksek Tutundurma"
            if num_val
            else "Merak Boşluğu + Yüksek Tamamlama Oranı"
        )
        scope = "45-55 sn · 6 Sahne"
    else:
        angle = f"⚡ {num_val}-Point Breakdown" if num_val else "🔥 Deep-Dive Viral Angle"
        hooks_en = [
            f"Here is the overlooked truth behind '{focus}' that changes how you see everything.",
            f"Most people completely miss the critical mechanism driving '{focus}'—let's break it down.",
            f"In the next 45 seconds, discover the concrete evidence and rules behind '{focus}'.",
        ]
        hook = hooks_en[digest % len(hooks_en)]
        summary = (
            f"Scene Plan: 1) High-retention curiosity hook on '{focus}' · 2-4) Concrete breakdown & proof "
            f"· 5-6) Actionable takeaway & comment debate trigger."
        )
        why_viral = "Curiosity Gap + High Watch-Through Rate"
        scope = "45-55s · 6 Scenes"

    if extra:
        if extra.get("hook") and str(extra["hook"]).strip().casefold() != topic.casefold():
            hook = str(extra["hook"]).strip()
        if extra.get("angle"):
            angle = str(extra["angle"]).strip()
        if extra.get("summary"):
            summary = str(extra["summary"]).strip()
        if isinstance(extra.get("keywords"), list) and extra["keywords"]:
            tags = [str(k) for k in extra["keywords"][:4]]

    return {
        "hook": hook[:140],
        "angle": angle,
        "summary": summary[:220],
        "keywords": tags[:4],
        "scope": scope,
        "why_viral": why_viral,
    }


def _score_candidate(
    title: str,
    niche_id: str,
    source: str,
    context_words: Set[str],
    used: Set[str],
    extra: Optional[Dict[str, Any]] = None,
    language: str = "tr",
) -> Optional[Dict[str, Any]]:
    topic = re.sub(r"\s+", " ", (title or "").strip())
    if len(topic) < 8 or len(topic) > 160:
        return None
    if source in (SOURCE_AI, SOURCE_VAULT) and len(topic) > 75:
        return None
    niche_obj = NICHES.get(resolve_canonical_niche(niche_id) or niche_id, {})
    if _is_generic(topic) or _is_hook_boilerplate(topic, niche_obj):
        return None
    slug = _slugify_topic(topic)
    if slug in used or topic.casefold() in used:
        return None

    words = {
        w
        for w in re.findall(r"\w{3,}", topic.casefold())
        if w not in _STOPWORDS
    }
    overlap = len(words & context_words)
    intel = resolve_topic_intelligence(topic, niche_id)
    canonical_niche = resolve_canonical_niche(niche_id)
    niche_match = resolve_canonical_niche(intel["resolved_niche"]) == canonical_niche
    if intel["locked"] and not niche_match:
        return None

    is_vault = source == SOURCE_VAULT or bool(extra and extra.get("is_curated"))

    if not is_vault:
        if source in (SOURCE_YOUTUBE, SOURCE_GOOGLE_TRENDS, SOURCE_RSS) and overlap < 1:
            return None
        if source == SOURCE_REDDIT and niche_id != "2_reddit_confessions" and overlap < 1:
            return None
        if not niche_match and overlap < 1:
            return None
        if intel["match_method"] == "passthrough" and overlap < 1 and source in (SOURCE_YOUTUBE, SOURCE_AI):
            return None

    score = 58 + min(20, overlap * 5)
    score += 15 if (niche_match or is_vault) else -15
    score += {
        SOURCE_VAULT: 7,
        SOURCE_YOUTUBE: 8,
        SOURCE_TREND: 7,
        SOURCE_REDDIT: 6,
        SOURCE_AI: 7,
        SOURCE_GOOGLE_TRENDS: 8,
        SOURCE_RSS: 6,
    }.get(source, 0)
    score += 2 if any(ch.isdigit() for ch in topic) or "(" in topic else 0

    confidence = min(95, max(50, score))
    editorial = _build_topic_editorial_metadata(topic, niche_id, language, extra=extra)
    fp = extract_format_fingerprint_from_title(topic)

    item: Dict[str, Any] = {
        "title": topic,
        "hook": editorial["hook"],
        "angle": editorial["angle"],
        "summary": editorial["summary"],
        "keywords": editorial["keywords"],
        "scope": editorial["scope"],
        "why_viral": editorial["why_viral"],
        "source": source if source != SOURCE_VAULT else SOURCE_AI,
        "confidence": confidence,
        "relevance": confidence,
        "niche_aligned": True if is_vault else niche_match,
        "format_fingerprint": fp,
        "topic_intelligence": {
            "resolved_niche": intel["resolved_niche"],
            "match_method": intel["match_method"],
            "locked": intel["locked"],
        },
    }
    if extra:
        for key in ("youtube_url", "channel", "view_count", "source_detail"):
            if extra.get(key):
                item[key] = extra[key]
    return item


def _template_fallback_candidates(
    niche_id: str, topic_hint: str = "", language: str = "tr"
) -> List[Dict[str, Any]]:
    """Guaranteed rich, non-cliche candidates from curated vault and dynamic seed engine."""
    out: List[Dict[str, Any]] = []

    if topic_hint and len(topic_hint.strip()) >= 3:
        seed_cands = _generate_seed_based_topics(
            topic_hint.strip(), niche_id, count=6, language=language
        )
        out.extend(seed_cands)

    vault_titles = get_curated_topics_for_niche(niche_id, lang=language)
    if not vault_titles:
        vault_titles = get_curated_topics_for_niche("1_news_flash", lang=language)

    random.shuffle(vault_titles)
    is_tr = (language or "tr").lower()[:2] != "en"
    for t in vault_titles:
        out.append({
            "title": t,
            "source": SOURCE_VAULT,
            "source_detail": "Küratörlü Viral Kasa" if is_tr else "Curated Viral Vault",
            "viral_score": 94,
            "is_curated": True,
        })
    return out


def _pick_diverse(scored: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
    final: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    source_counts: Counter = Counter()
    max_per_source = 3 if count <= 5 else max(4, (count + 1) // 2)

    for item in scored:
        if len(final) >= count:
            break
        key = item["title"].casefold()
        if key in seen:
            continue
        src = item["source"]
        if source_counts[src] >= max_per_source and len(final) < count - 1:
            continue
        final.append(item)
        seen.add(key)
        source_counts[src] += 1

    for item in scored:
        if len(final) >= count:
            break
        key = item["title"].casefold()
        if key not in seen:
            final.append(item)
            seen.add(key)
    return final[:count]


def suggest_topics(
    niche_id: str,
    language: str = "tr",
    count: int = 5,
    topic_hint: str = "",
    exclude_titles: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Main entry: return up to `count` scored, niche-aligned topic suggestions."""
    raw_niche = (niche_id or "1_news_flash").strip()
    canonical_niche = resolve_canonical_niche(raw_niche)
    count = max(1, min(int(count or 5), 30))
    language = (language or "tr").strip().lower()[:2]

    if canonical_niche not in NICHES:
        return {"status": "error", "message": "Geçersiz niş.", "suggestions": [], "count": 0}

    topic_hint = (topic_hint or "").strip()
    topic_hint_ignored = bool(topic_hint) and not _topic_hint_matches_niche(
        topic_hint, canonical_niche
    )
    if topic_hint_ignored:
        logger.info("Ignoring topic hint outside selected niche %s", canonical_niche)
        topic_hint = ""

    context_words = _niche_context_words(canonical_niche)
    used = _collect_used_topics(exclude_titles=exclude_titles)

    raw: List[Dict[str, Any]] = []

    if topic_hint and len(topic_hint) >= 3:
        raw.extend(
            _generate_seed_based_topics(topic_hint, canonical_niche, count=1, language=language)
        )

    source_jobs = [
        ("YouTube", _fetch_youtube_candidates, (canonical_niche, language, count, topic_hint)),
        ("Google Trends", _fetch_google_trend_candidates, (language, 8)),
        ("RSS", _fetch_rss_candidates, (canonical_niche, language, 5)),
        ("niche trends", _fetch_trend_candidates, (canonical_niche, language)),
    ]
    if canonical_niche == "2_reddit_confessions":
        source_jobs.append(("Reddit", _fetch_reddit_candidates, (language, count)))

    with ThreadPoolExecutor(max_workers=len(source_jobs)) as executor:
        futures = {
            executor.submit(fetcher, *args): source_name
            for source_name, fetcher, args in source_jobs
        }
        for future in as_completed(futures):
            source_name = futures[future]
            try:
                raw.extend(future.result())
            except Exception as exc:
                logger.warning("%s topic source failed: %s", source_name, exc)

    raw.extend(_generate_ai_candidates(canonical_niche, language, count, topic_hint))

    scored: List[Dict[str, Any]] = []
    seen_titles: Set[str] = set()
    for cand in raw:
        title = (cand.get("title") or "").strip()
        if not title:
            continue
        norm = title.casefold()
        if norm in seen_titles:
            continue
        seen_titles.add(norm)
        extra = {k: v for k, v in cand.items() if k not in ("title", "source")}
        item = _score_candidate(
            title,
            raw_niche,
            cand.get("source", SOURCE_AI),
            context_words,
            used,
            extra,
            language=language,
        )
        if item:
            scored.append(item)

    random.shuffle(scored)
    scored.sort(key=lambda x: (round(x["confidence"] / 10), x["niche_aligned"]), reverse=True)
    suggestions = _pick_diverse(scored, count)

    if len(suggestions) < count:
        for fb in _template_fallback_candidates(raw_niche, "", language=language):
            if len(suggestions) >= count:
                break
            item = _score_candidate(
                fb["title"],
                raw_niche,
                SOURCE_VAULT,
                context_words,
                used,
                extra={"is_curated": True, "source_detail": fb.get("source_detail")},
                language=language,
            )
            if item and item["title"].casefold() not in {
                s["title"].casefold() for s in suggestions
            }:
                suggestions.append(item)

    # If exclude_titles exhausted the pool, allow curated pool without exclude_titles so user is never left empty
    if len(suggestions) < count and exclude_titles:
        base_used = _collect_used_topics(exclude_titles=None)
        for fb in _template_fallback_candidates(raw_niche, "", language=language):
            if len(suggestions) >= count:
                break
            item = _score_candidate(
                fb["title"],
                raw_niche,
                SOURCE_VAULT,
                context_words,
                base_used,
                extra={"is_curated": True, "source_detail": fb.get("source_detail")},
                language=language,
            )
            if item and item["title"].casefold() not in {
                s["title"].casefold() for s in suggestions
            }:
                suggestions.append(item)

    try:
        from hybrid_niches import HYBRID_NICHES
    except ImportError:
        HYBRID_NICHES = {}

    niche_obj = HYBRID_NICHES.get(raw_niche) or NICHES.get(raw_niche, {})
    profile = get_niche_production_profile(raw_niche)

    niche_display_name = (
        niche_obj.get("name_en")
        if language == "en" and niche_obj.get("name_en")
        else (niche_obj.get("name") or profile.get("name", raw_niche))
    )

    source_counts = Counter(item["source"] for item in suggestions[:count])
    return {
        "status": "ok",
        "niche_id": raw_niche,
        "niche_name": niche_display_name,
        "language": language,
        "topic_hint_ignored": topic_hint_ignored,
        "source_counts": dict(source_counts),
        "count": len(suggestions[:count]),
        "suggestions": suggestions[:count],
    }
