"""
YouTube-safe royalty-free BGM catalog (Mixkit CDN + manual Studio imports).

YouTube Studio Audio Library has no public download API — this catalog ships
72 curated Mixkit tracks (YouTube/commercial use allowed) plus scans
bgm/youtube_studio/ for user-imported Studio Audio Library files.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import config

CATALOG_PATH = os.path.join(config.BASE_DIR, "data", "youtube_safe_bgm_catalog.json")
YOUTUBE_STUDIO_DIR = os.path.join(config.BGM_DIR, "youtube_studio")
AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".ogg")

_catalog_cache: Optional[List[Dict[str, Any]]] = None


def _ensure_dirs() -> None:
    os.makedirs(config.BGM_DIR, exist_ok=True)
    os.makedirs(YOUTUBE_STUDIO_DIR, exist_ok=True)


def load_catalog(force_reload: bool = False) -> List[Dict[str, Any]]:
    global _catalog_cache
    if _catalog_cache is not None and not force_reload:
        return _catalog_cache
    if not os.path.isfile(CATALOG_PATH):
        _catalog_cache = []
        return _catalog_cache
    with open(CATALOG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    _catalog_cache = list(data.get("tracks") or [])
    return _catalog_cache


def catalog_meta() -> Dict[str, Any]:
    if not os.path.isfile(CATALOG_PATH):
        return {"count": 0, "description": "", "studio_import_note": ""}
    with open(CATALOG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {
        "count": data.get("count", len(data.get("tracks") or [])),
        "description": data.get("description", ""),
        "studio_import_note": data.get("studio_import_note", ""),
    }


def _track_by_id(track_id: str) -> Optional[Dict[str, Any]]:
    tid = (track_id or "").strip()
    for t in load_catalog():
        if t.get("id") == tid or t.get("filename") == tid:
            return t
    return None


def track_by_filename(filename: str) -> Optional[Dict[str, Any]]:
    fn = os.path.basename(filename or "")
    for t in load_catalog():
        if t.get("filename") == fn:
            return t
    return None


def get_track_bpm(filename: str, default: float = 120.0) -> float:
    meta = track_by_filename(filename)
    if meta and meta.get("bpm"):
        return float(meta["bpm"])
    return default


def get_display_label(filename: str) -> str:
    t = track_by_filename(filename)
    if t:
        mood = t.get("mood") or ""
        genre = t.get("genre") or ""
        return f"{t.get('title', filename)} ({mood or genre})"
    if filename == "royalty_free_ambient.wav":
        return "Sentez Ambient (varsayılan)"
    return filename


def list_studio_imports() -> List[Dict[str, Any]]:
    _ensure_dirs()
    out = []
    if not os.path.isdir(YOUTUBE_STUDIO_DIR):
        return out
    for f in sorted(os.listdir(YOUTUBE_STUDIO_DIR)):
        if f.lower().endswith(AUDIO_EXTS):
            out.append({
                "filename": f,
                "title": os.path.splitext(f)[0].replace("_", " "),
                "source": "youtube_studio_import",
                "mood": "studio",
                "genre": "youtube_studio",
                "license": "YouTube Studio Audio Library (user import)",
            })
    return out


def list_catalog_entries(include_studio: bool = True) -> List[Dict[str, Any]]:
    entries = []
    for t in load_catalog():
        fn = t.get("filename", "")
        entries.append({
            "id": t.get("id"),
            "filename": fn,
            "title": t.get("title"),
            "artist": t.get("artist"),
            "mood": t.get("mood"),
            "genre": t.get("genre"),
            "bpm": t.get("bpm"),
            "niche_tags": t.get("niche_tags") or [],
            "license": t.get("license"),
            "downloaded": os.path.isfile(os.path.join(config.BGM_DIR, fn)),
            "source": t.get("source", "youtube_safe_catalog"),
            "display": get_display_label(fn),
        })
    if include_studio:
        for s in list_studio_imports():
            entries.append({
                "id": f"studio_{s['filename']}",
                "filename": s["filename"],
                "title": s["title"],
                "mood": s["mood"],
                "genre": s["genre"],
                "downloaded": True,
                "source": "youtube_studio_import",
                "display": f"{s['title']} (YouTube Studio)",
                "path_prefix": "youtube_studio/",
            })
    return entries


def search_catalog(
    query: str = "",
    mood: str = "",
    niche: str = "",
    limit: int = 12,
) -> List[Dict[str, Any]]:
    q = (query or "").lower().strip()
    m = (mood or "").lower().strip()
    n = (niche or "").lower().strip()
    scored: List[tuple] = []

    for t in load_catalog():
        score = 0.0
        blob = " ".join([
            str(t.get("title", "")),
            str(t.get("genre", "")),
            str(t.get("mood", "")),
            " ".join(t.get("niche_tags") or []),
        ]).lower()
        if q and q in blob:
            score += 3.0
        if q:
            for word in q.split():
                if word in blob:
                    score += 1.0
        if m and m in str(t.get("mood", "")).lower():
            score += 2.0
        if n:
            tags = [x.lower() for x in (t.get("niche_tags") or [])]
            if any(n in tag or tag in n for tag in tags):
                score += 4.0
            if n in blob:
                score += 1.5
        if not q and not m and not n:
            score = 1.0
        if score > 0:
            scored.append((score, t))

    scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    return [t for _, t in scored[:limit]]


def ensure_catalog_track(track_id: str = "", filename: str = "") -> Optional[str]:
    """Download catalog track into BGM_DIR; return filename."""
    _ensure_dirs()
    t = _track_by_id(track_id) if track_id else track_by_filename(filename)
    if not t:
        return None

    fn = t["filename"]
    dest = os.path.join(config.BGM_DIR, fn)
    if os.path.isfile(dest) and os.path.getsize(dest) > 2000:
        return fn

    from royalty_free_audio import download_track

    if download_track(t["url"], dest):
        print(f"  [YT-Safe BGM] İndirildi: {fn} — {t.get('title')}")
        return fn
    return None


def get_studio_track_path(filename: str) -> Optional[str]:
    safe = os.path.basename(filename)
    fp = os.path.join(YOUTUBE_STUDIO_DIR, safe)
    if os.path.isfile(fp):
        return fp
    return None


def resolve_bgm_path(track_name: str) -> Optional[str]:
    """Resolve filename to full path (bgm/ or bgm/youtube_studio/)."""
    if not track_name:
        return None
    base = os.path.join(config.BGM_DIR, os.path.basename(track_name))
    if os.path.isfile(base):
        return base
    studio = get_studio_track_path(track_name)
    if studio:
        return studio
    return None


def pick_catalog_bgm_for_niche(niche_id: str = "", query: str = "") -> Optional[str]:
    """Pick best catalog track for niche; lazy-download and return filename."""
    from bgm_manager import get_niche_target_bpm

    min_bpm, max_bpm = get_niche_target_bpm(niche_id)
    target_mid = (min_bpm + max_bpm) / 2.0
    niche = (niche_id or query or "").lower().strip()

    candidates = search_catalog(query=query or niche, niche=niche, limit=20)
    if not candidates:
        candidates = load_catalog()[:10]

    best = None
    best_score = -1.0
    for t in candidates:
        bpm = float(t.get("bpm") or 100)
        bpm_diff = abs(bpm - target_mid)
        niche_hit = 0.0
        tags = [x.lower() for x in (t.get("niche_tags") or [])]
        for tag in tags:
            if tag in niche or niche in tag:
                niche_hit += 5.0
        score = niche_hit + max(0.0, 10.0 - bpm_diff * 0.15)
        if score > best_score:
            best_score = score
            best = t

    if not best and load_catalog():
        best = load_catalog()[0]

    if not best:
        return None

    return ensure_catalog_track(track_id=best.get("id", ""))


def seed_catalog(limit: int = 8, niche: str = "") -> List[str]:
    """Pre-download starter pack into bgm/."""
    _ensure_dirs()
    picks = search_catalog(niche=niche, limit=limit) if niche else load_catalog()[:limit]
    saved = []
    for t in picks:
        fn = ensure_catalog_track(track_id=t.get("id", ""))
        if fn:
            saved.append(fn)
            time.sleep(0.15)
    return saved


def fetch_catalog_bgm(query: str = "ambient cinematic", niche: str = "") -> Optional[str]:
    """Primary royalty-free fetch: catalog match + lazy download."""
    mood_map = {
        "ambient": "calm", "cinematic": "epic", "motivation": "inspirational",
        "dark": "mysterious", "energetic": "energetic", "calm": "calm",
        "lofi": "lofi", "corporate": "corporate", "tech": "tech",
    }
    q = (query or "").lower()
    mood = next((m for k, m in mood_map.items() if k in q), "")

    fn = pick_catalog_bgm_for_niche(niche_id=niche or q, query=query)
    if fn:
        return fn

    hits = search_catalog(query=query, mood=mood, limit=3)
    for t in hits:
        fn = ensure_catalog_track(track_id=t.get("id", ""))
        if fn:
            return fn
    return None
