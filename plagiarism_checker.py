"""
Otomatik Senaryo İntihal Kontrolü — Item 120
Üretilen senaryo yerel difflib veya TF-IDF ile eski senaryolarla kıyaslanır;
benzerlik %45'in altındaysa onaylanır.

Veritabanı: JSON dosyası (plagiarism_db.json)
"""

import os
import json
import re
import math
import difflib
from typing import Tuple, List, Optional
import config

# ─── Veritabanı dosya yolu ────────────────────────────────────────────────────
_DB_PATH = os.path.join(config.BASE_DIR, "plagiarism_db.json")

# Benzerlik eşiği: %45'in ÜSTÜNDE ise reddedilir
SIMILARITY_THRESHOLD = 0.45

# Maksimum veritabanı boyutu (en son N senaryo saklanır)
MAX_DB_ENTRIES = 500


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^\w\sğüşıöçĞÜŞİÖÇ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_words(text: str) -> List[str]:
    return _normalize_text(text).split()


def _cosine_similarity_tfidf(text_a: str, text_b: str) -> float:
    """TF-IDF tabanlı kosinüs benzerliği hesaplar."""
    words_a = _extract_words(text_a)
    words_b = _extract_words(text_b)
    if not words_a or not words_b:
        return 0.0
    vocab = set(words_a) | set(words_b)
    vocab_idx = {w: i for i, w in enumerate(vocab)}

    def vec(words):
        v = {}
        for w in words:
            if w in vocab_idx:
                v[vocab_idx[w]] = v.get(vocab_idx[w], 0) + 1
        total = sum(v.values())
        return {k: val / total for k, val in v.items()}

    va = vec(words_a)
    vb = vec(words_b)
    dot = sum(va.get(k, 0) * vb.get(k, 0) for k in va)
    mag_a = math.sqrt(sum(v ** 2 for v in va.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vb.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _difflib_similarity(text_a: str, text_b: str) -> float:
    """difflib SequenceMatcher ile hızlı benzerlik skoru."""
    norm_a = _normalize_text(text_a)
    norm_b = _normalize_text(text_b)
    if not norm_a or not norm_b:
        return 0.0
    return difflib.SequenceMatcher(None, norm_a, norm_b).ratio()


def compute_similarity(text_a: str, text_b: str, method: str = "combined") -> float:
    """
    İki metin arasındaki benzerlik skorunu hesaplar.
    method: "difflib" | "tfidf" | "combined"
    """
    if method == "difflib":
        return _difflib_similarity(text_a, text_b)
    elif method == "tfidf":
        return _cosine_similarity_tfidf(text_a, text_b)
    else:
        dl = _difflib_similarity(text_a, text_b)
        tf = _cosine_similarity_tfidf(text_a, text_b)
        return dl * 0.4 + tf * 0.6


def _load_db() -> List[dict]:
    if not os.path.exists(_DB_PATH):
        return []
    try:
        with open(_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_db(entries: List[dict]) -> None:
    if len(entries) > MAX_DB_ENTRIES:
        entries = entries[-MAX_DB_ENTRIES:]
    try:
        with open(_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"    [Item 120] DB kayıt hatası: {e}")


def add_script_to_db(script_text: str, keyword: str = "", title: str = "") -> None:
    """Onaylanmış senaryoyu veritabanına ekler."""
    if not script_text or len(script_text.strip()) < 50:
        return
    entries = _load_db()
    entries.append({
        "keyword": keyword,
        "title": title,
        "text": _normalize_text(script_text),
        "length": len(script_text.split())
    })
    _save_db(entries)
    print(f"    [Item 120] Senaryo DB'ye eklendi: '{title[:40]}' ({len(script_text.split())} kelime)")


def check_script_originality(
    new_script: str,
    threshold: float = SIMILARITY_THRESHOLD,
    method: str = "combined",
    keyword: str = "",
    title: str = "",
    auto_add_if_approved: bool = True
) -> Tuple[bool, float, Optional[str]]:
    """
    Item 120 – Otomatik Senaryo İntihal Kontrolü.
    Üretilen yeni senaryoyu veritabanındaki tüm eski senaryolarla karşılaştırır.

    Karar kriteri:
    - Benzerlik < threshold (%45) → ONAYLANDI (özgün)
    - Benzerlik >= threshold (%45) → REDDEDİLDİ (intihal riski)

    Returns:
        (is_approved: bool, max_similarity: float, matched_title: str | None)
    """
    if not new_script or len(new_script.strip()) < 30:
        print("  [Item 120] Senaryo çok kısa; kontrol atlandı.")
        return True, 0.0, None

    entries = _load_db()

    if not entries:
        print(f"  [Item 120] DB boş; senaryo özgün kabul edildi (ilk kayıt).")
        if auto_add_if_approved:
            add_script_to_db(new_script, keyword=keyword, title=title)
        return True, 0.0, None

    print(f"  [Item 120] İntihal kontrolü: {len(entries)} eski senaryo ile karşılaştırılıyor...")

    max_sim = 0.0
    matched_title = None
    norm_new = _normalize_text(new_script)

    for entry in entries:
        sim = compute_similarity(norm_new, entry.get("text", ""), method=method)
        if sim > max_sim:
            max_sim = sim
            matched_title = entry.get("title", entry.get("keyword", "Bilinmiyor"))

    is_approved = max_sim < threshold
    status = "ONAYLANDI" if is_approved else "REDDEDILDI"
    sim_pct = max_sim * 100

    print(f"    [Item 120] Sonuç: {status}")
    print(f"    [Item 120] Maksimum benzerlik: %{sim_pct:.1f} (esik: %{threshold*100:.0f})")
    if matched_title and max_sim > 0.1:
        print(f"    [Item 120] En benzer senaryo: '{matched_title[:50]}'")

    if is_approved and auto_add_if_approved:
        add_script_to_db(new_script, keyword=keyword, title=title)

    return is_approved, max_sim, matched_title if max_sim >= threshold else None


def get_db_stats() -> dict:
    """Veritabanı istatistiklerini döndürür."""
    entries = _load_db()
    return {
        "total_scripts": len(entries),
        "db_path": _DB_PATH,
        "max_capacity": MAX_DB_ENTRIES,
        "threshold_pct": SIMILARITY_THRESHOLD * 100
    }


def clear_plagiarism_db() -> None:
    """Veritabanını temizler."""
    _save_db([])
    print("  [Item 120] Intihal veritabani temizlendi.")
