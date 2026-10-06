"""
Bölüm 8.1: SQLite Tabanlı Çapraz Senaryo Özgünlük Doğrulaması (Madde 120)
(SQLite-backed Cross-Script Originality Verifier)

Daha önce üretilen senaryolar SQLite veritabanında (generated_scripts ve tamamlanmış video sahneleri) saklanır.
Yeni üretilen senaryonun kelime benzerliği (token overlap / Jaccard) geçmiş senaryolarla kıyaslanır;
%35'ten (veya konfigüre edilen eşikten) fazla örtüşme varsa senaryo reddedilir.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple, Dict, Any
import database

# Standart eşik: %35'in üzerinde benzerlik gösteren senaryo özgün sayılmaz (Madde 120)
DEFAULT_ORIGINALITY_THRESHOLD = 0.35

# Türkçe & İngilizce stopwords: sık tekrarlanan bağlaçların benzerliği yapay yükseltmesini önlemek için opsiyonel filtrelenebilir
COMMON_STOPWORDS = frozenset({
    "ve", "bir", "bu", "için", "ile", "da", "de", "mi", "mu", "mı",
    "the", "a", "an", "in", "on", "at", "to", "of", "is", "are", "was", "were",
})


def tokenize_script(text: str, strip_stopwords: bool = False) -> set:
    """
    Senaryo metnini küçük harfli alfanümerik kelime kümesine dönüştürür.
    """
    if not text:
        return set()
    tokens = set(re.findall(r"\w+", text.lower()))
    if strip_stopwords:
        tokens = {t for t in tokens if t not in COMMON_STOPWORDS and len(t) > 1}
    return tokens


def calculate_jaccard_overlap(tokens_a: set, tokens_b: set) -> float:
    """
    İki kelime kümesi arasındaki Jaccard örtüşme oranını hesaplar:
    Kesişim / Birleşim (0.0 - 1.0)
    """
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / max(1, union)


def check_script_originality(
    script_text: str,
    channel_slug: str = "default",
    limit: int = 50,
    threshold: float = DEFAULT_ORIGINALITY_THRESHOLD,
) -> Tuple[bool, float]:
    """
    Checks script text against previously generated scripts in SQLite (Plan Bölüm 8.1 / Madde 120).

    Args:
        script_text: Doğrulanacak yeni senaryonun tam metni.
        channel_slug: Kanal bazlı geçmiş filtreleme ('default', kanal kimliği veya '*' tümü).
        limit: Kıyaslanacak en son N senaryo adedi (varsayılan 50).
        threshold: Maksimum izin verilen benzerlik eşiği (varsayılan 0.35).

    Returns:
        (is_approved: bool, max_overlap: float)
        - is_approved True ise senaryo özgündür.
        - is_approved False ise %35 üzeri kopya/tekrarlayan içerik tespit edilmiştir.
    """
    if not script_text or len(script_text.strip()) < 30:
        return True, 0.0

    history = database.get_recent_scripts(channel_slug=channel_slug, limit=limit)
    if not history:
        return True, 0.0

    tokens = tokenize_script(script_text)
    max_overlap = 0.0

    for old_script in history:
        old_tokens = tokenize_script(old_script)
        overlap = calculate_jaccard_overlap(tokens, old_tokens)
        if overlap > max_overlap:
            max_overlap = overlap
        if overlap > threshold:
            return False, overlap

    return True, max_overlap


def check_script_originality_detailed(
    script_text: str,
    channel_slug: str = "default",
    limit: int = 50,
    threshold: float = DEFAULT_ORIGINALITY_THRESHOLD,
) -> Tuple[bool, float, Optional[str]]:
    """
    Detaylı intihal/özgünlük doğrulaması. En çok benzeyen geçmiş senaryonun
    kısa bir özetini veya ilk cümlesini de raporlar.
    """
    if not script_text or len(script_text.strip()) < 30:
        return True, 0.0, None

    history = database.get_recent_scripts(channel_slug=channel_slug, limit=limit)
    if not history:
        return True, 0.0, None

    tokens = tokenize_script(script_text)
    max_overlap = 0.0
    matched_snippet = None

    for old_script in history:
        old_tokens = tokenize_script(old_script)
        overlap = calculate_jaccard_overlap(tokens, old_tokens)
        if overlap > max_overlap:
            max_overlap = overlap
            matched_snippet = (old_script.strip()[:80] + "...") if len(old_script) > 80 else old_script.strip()

    is_approved = max_overlap <= threshold
    return is_approved, max_overlap, matched_snippet if max_overlap > 0.10 else None


def register_approved_script(
    script_text: str,
    title: str = "",
    keyword: str = "",
    channel_slug: str = "default",
    niche_id: str = "",
    video_id: Optional[int] = None,
    similarity_score: float = 0.0,
) -> int:
    """
    Onaylanan özgün senaryoyu gelecekteki kontroller için SQLite hafızasına kaydeder.
    """
    return database.save_generated_script(
        script_text=script_text,
        title=title,
        keyword=keyword,
        channel_slug=channel_slug,
        niche_id=niche_id,
        video_id=video_id,
        status="approved",
        similarity_score=similarity_score,
    )
