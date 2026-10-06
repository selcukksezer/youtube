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
import sqlite3
import time
from typing import Tuple, List, Optional
import config

# ─── Veritabanı dosya yolu ────────────────────────────────────────────────────
_DB_PATH = os.path.join(config.BASE_DIR, "plagiarism_db.json")

# Plan 8.1: %35 üstü örtüşme reddedilir. %45 kopyayı içeri alıyordu.
SIMILARITY_THRESHOLD = 0.35

# Maksimum veritabanı boyutu (en son N senaryo saklanır)
MAX_DB_ENTRIES = 500

# Topic overlap below this → discount niche-template boilerplate similarity
_TOPIC_DIVERGENCE_THRESHOLD = 0.35

_TR_STOPWORDS = frozenset({
    "ve", "bir", "bu", "için", "ile", "da", "de", "mi", "mu", "mı", "the", "a", "an",
    "in", "on", "at", "to", "of", "is", "are", "was", "were", "that", "this", "bugün",
    "hayatını", "hayat", "kurtarabilir", "yıllık", "felsefe", "shorts", "video",
})


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^\w\sğüşıöçĞÜŞİÖÇ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()



def _get_ngrams(words: List[str], n: int = 3) -> set:
    """Metinden n-gram kümeleri oluşturur."""
    return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))

def _jaccard_similarity(text_a: str, text_b: str, n: int = 3) -> float:
    """Jaccard n-gram benzerliği."""
    ngrams_a = _get_ngrams(_extract_words(text_a), n)
    ngrams_b = _get_ngrams(_extract_words(text_b), n)
    intersection = ngrams_a.intersection(ngrams_b)
    union = ngrams_a.union(ngrams_b)
    if not union:
        return 0.0
    return len(intersection) / len(union)

def _extract_words(text: str) -> List[str]:
    return _normalize_text(text).split()


def _topic_token_set(keyword: str, title: str) -> set:
    """Distinctive topic tokens from user keyword/title (not full script body)."""
    raw = f"{keyword or ''} {title or ''}".strip()
    if not raw:
        return set()
    return {
        w for w in _extract_words(raw)
        if len(w) > 2 and w not in _TR_STOPWORDS
    }


def _topic_overlap(keyword_a: str, title_a: str, keyword_b: str, title_b: str) -> float:
    """Jaccard overlap on topic seed tokens — separates same-niche, different-topic scripts."""
    ta = _topic_token_set(keyword_a, title_a)
    tb = _topic_token_set(keyword_b, title_b)
    if not ta or not tb:
        return 0.0
    inter = ta.intersection(tb)
    union = ta.union(tb)
    return len(inter) / len(union) if union else 0.0


def _verbatim_phrase_overlap(text_a: str, text_b: str, n: int = 4) -> float:
    """Calculates n-gram verbatim phrase overlap (4-gram and 5-gram)."""
    words_a = _extract_words(text_a)
    words_b = _extract_words(text_b)
    if len(words_a) < n or len(words_b) < n:
        return 0.0
    ngrams_a = _get_ngrams(words_a, n)
    ngrams_b = _get_ngrams(words_b, n)
    if not ngrams_a or not ngrams_b:
        return 0.0
    inter = ngrams_a.intersection(ngrams_b)
    return len(inter) / max(len(ngrams_a), 1)


def _adjust_similarity_for_topic(
    body_sim: float,
    new_keyword: str,
    new_title: str,
    entry_keyword: str,
    entry_title: str,
    new_text: str = "",
    entry_text: str = "",
) -> float:
    """
    Item 120 Upgrade: Prevents false-positive rejection when titles are similar
    but actual script narrative sentences and content are completely different.
    """
    overlap = _topic_overlap(new_keyword, new_title, entry_keyword, entry_title)
    phrase_copy = 0.0
    if new_text and entry_text:
        phrase_copy = max(
            _verbatim_phrase_overlap(new_text, entry_text, n=4),
            _verbatim_phrase_overlap(new_text, entry_text, n=5),
        )
    # A copied sentence stays a copy even when the title changed.
    if phrase_copy > SIMILARITY_THRESHOLD:
        return max(body_sim, phrase_copy)

    # Same niche words, different sentences: do not reject the fresh script.
    if overlap >= _TOPIC_DIVERGENCE_THRESHOLD:
        if phrase_copy < 0.12:
            return min(body_sim * 0.40, SIMILARITY_THRESHOLD - 0.01)
        return min(body_sim * 0.65, SIMILARITY_THRESHOLD - 0.01)

    scale = 0.25 + (0.75 * overlap / max(_TOPIC_DIVERGENCE_THRESHOLD, 0.01))
    return body_sim * scale


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


def compute_similarity(text_a: str, text_b: str, method: str = "robust") -> float:
    """
    İki metin arasındaki benzerlik skorunu hesaplar.
    method: "difflib" | "tfidf" | "jaccard" | "combined" | "robust"
    """
    if method == "difflib":
        return _difflib_similarity(text_a, text_b)
    elif method == "tfidf":
        return _cosine_similarity_tfidf(text_a, text_b)
    elif method == "jaccard":
        return _jaccard_similarity(text_a, text_b)
    elif method == "combined":
        dl = _difflib_similarity(text_a, text_b)
        tf = _cosine_similarity_tfidf(text_a, text_b)
        return dl * 0.4 + tf * 0.6
    else:
        dl = _difflib_similarity(text_a, text_b)
        tf = _cosine_similarity_tfidf(text_a, text_b)
        jc = _jaccard_similarity(text_a, text_b, n=3)
        return (dl * 0.3) + (tf * 0.5) + (jc * 0.2)


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


def add_script_to_db(
    script_text: str,
    keyword: str = "",
    title: str = "",
    video_id: Optional[int] = None,
    render_status: str = "completed",
    channel_slug: str = "default",
    similarity_score: float = 0.0,
) -> None:
    """Onaylanmış ve başarıyla render edilmiş senaryoyu veritabanına ekler (SQLite + JSON fallback)."""
    if not script_text or len(script_text.strip()) < 50:
        return

    # SQLite (Bölüm 8.1)
    if render_status == "completed":
        try:
            import database
            database.save_generated_script(
                script_text=script_text,
                title=title,
                keyword=keyword,
                channel_slug=channel_slug,
                video_id=video_id,
                status=render_status,
                similarity_score=similarity_score,
            )
        except Exception as dbe:
            print(f"    [Item 120] SQLite senaryo kayıt uyarısı: {dbe}")

    entries = _load_db()
    norm = _normalize_text(script_text)
    if any(e.get("text") == norm for e in entries):
        return
    entries.append({
        "keyword": keyword,
        "title": title,
        "text": norm,
        "length": len(script_text.split()),
        "video_id": video_id,
        "render_status": render_status,
        "created_at": time.time(),
        "channel_slug": channel_slug,
    })
    _save_db(entries)
    print(f"    [Item 120] Senaryo DB'ye eklendi (başarılı render): '{title[:40]}' ({len(script_text.split())} kelime)")


def _is_entry_active_and_successful(entry: dict) -> bool:
    """
    Yalnızca başarılı (completed) render alınmış senaryoları intihal kontrolüne dahil eder.
    Henüz renderı bitmemiş, iptal edilmiş veya hata vermiş denemeler intihal karşılaştırmasına dahil edilmez.
    """
    if entry.get("render_status") and entry.get("render_status") != "completed":
        return False

    vid_id = entry.get("video_id")
    kw = entry.get("keyword") or ""
    ti = entry.get("title") or ""

    try:
        from database import DB_PATH
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            cur = conn.cursor()
            if vid_id is not None:
                cur.execute("SELECT status FROM videos WHERE id = ?", (vid_id,))
                row = cur.fetchone()
                conn.close()
                if row:
                    return row[0] == "completed"
                return True

            if kw or ti:
                cur.execute(
                    "SELECT status FROM videos WHERE keyword = ? OR title = ?",
                    (kw, ti if ti else kw)
                )
                statuses = [r[0] for r in cur.fetchall()]
                conn.close()
                if statuses and not any(s == "completed" for s in statuses):
                    # Bu başlık için denemeler yapılmış ama hepsi failed/cancelled olmuş
                    return False
    except Exception:
        pass

    return True


def check_script_originality(
    new_script: str,
    threshold: float = SIMILARITY_THRESHOLD,
    method: str = "robust",
    keyword: str = "",
    title: str = "",
    auto_add_if_approved: bool = False,
    only_completed_renders: bool = True,
    allow_similar_script: bool = False,
    channel_slug: str = "default",
) -> Tuple[bool, float, Optional[str]]:
    """
    Item 120 – Otomatik Senaryo İntihal Kontrolü (SQLite + JSON).
    Üretilen yeni senaryoyu veritabanındaki tüm eski senaryolarla karşılaştırır.

    Karar kriteri:
    - Benzerlik < threshold (%35-45) → ONAYLANDI (özgün)
    - Benzerlik >= threshold → REDDEDİLDİ (intihal riski)
    - allow_similar_script == True → Benzerlik eşiği aşılsa bile kullanıcı onayıyla devam eder.

    Returns:
        (is_approved: bool, max_similarity: float, matched_title: str | None)
    """
    if not new_script or len(new_script.strip()) < 30:
        print("  [Item 120] Senaryo çok kısa; kontrol atlandı.")
        return True, 0.0, None

    raw_entries = _load_db()
    if only_completed_renders:
        entries = [e for e in raw_entries if _is_entry_active_and_successful(e)]
    else:
        entries = list(raw_entries)
    wanted = channel_slug or "default"
    if wanted not in ("*", "all"):
        entries = [e for e in entries if (e.get("channel_slug") or "default") == wanted]

    # SQLite generated_scripts entegrasyonu (Bölüm 8.1 / Madde 120)
    try:
        import database
        sqlite_scripts = database.get_recent_scripts(channel_slug=channel_slug or "default", limit=50)
        existing_texts = {e.get("text") for e in entries}
        for s in sqlite_scripts:
            norm_s = _normalize_text(s)
            if norm_s and norm_s not in existing_texts:
                entries.append({
                    "keyword": "",
                    "title": s[:40],
                    "text": norm_s,
                    "length": len(s.split()),
                    "render_status": "completed",
                    "created_at": time.time(),
                    "channel_slug": channel_slug,
                })
                existing_texts.add(norm_s)
    except Exception as sqle:
        pass

    if not entries:
        print(f"  [Item 120] DB boş veya başarılı render kaydı yok; senaryo özgün kabul edildi.")
        if auto_add_if_approved:
            add_script_to_db(new_script, keyword=keyword, title=title, channel_slug=channel_slug)
        return True, 0.0, None

    print(f"  [Item 120] İntihal kontrolü: {len(entries)} eski senaryo ile karşılaştırılıyor...")

    max_sim = 0.0
    matched_title = None
    norm_new = _normalize_text(new_script)
    norm_kw = _normalize_text(keyword or "")
    norm_title = _normalize_text(title or keyword or "")

    for entry in entries:
        entry_kw = _normalize_text(entry.get("keyword", "") or "")
        entry_title = _normalize_text(entry.get("title", "") or "")
        raw_sim = compute_similarity(norm_new, entry.get("text", ""), method=method)
        sim = _adjust_similarity_for_topic(
            raw_sim,
            keyword,
            title,
            entry.get("keyword", ""),
            entry.get("title", ""),
            new_text=norm_new,
            entry_text=entry.get("text", ""),
        )
        if sim > max_sim:
            max_sim = sim
            matched_title = entry.get("title", entry.get("keyword", "Bilinmiyor"))

    is_approved = (max_sim < threshold) or bool(allow_similar_script)
    status = "ONAYLANDI" if is_approved else "REDDEDILDI"
    if allow_similar_script and max_sim >= threshold:
        status += " (Yine de devam et / allow_similar_script devrede)"
    sim_pct = max_sim * 100

    print(f"    [Item 120] Sonuç: {status}")
    print(f"    [Item 120] Maksimum benzerlik: %{sim_pct:.1f} (esik: %{threshold*100:.0f})")
    if matched_title and max_sim > 0.1:
        print(f"    [Item 120] En benzer senaryo: '{matched_title[:50]}'")

    if is_approved and auto_add_if_approved:
        add_script_to_db(new_script, keyword=keyword, title=title, channel_slug=channel_slug)

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
    """Veritabanını temizler (JSON + SQLite)."""
    _save_db([])
    try:
        import database
        with database.get_connection() as conn:
            conn.execute("DELETE FROM generated_scripts")
            conn.commit()
    except Exception:
        pass
    print("  [Item 120] Intihal veritabani temizlendi.")
