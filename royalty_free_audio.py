"""
Royalty-free audio library: Pixabay Music/SFX + Mixkit + local VoiceLab-style pack.
VoiceLab (voicelab.cloud) has no public developer API — we mirror its free catalogue
idea via Pixabay (same API key) + Mixkit CDN + bundled ambient packs.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional

import requests

import config

VOICELAB_DIR = os.path.join(config.BASE_DIR, "voicelab")
BGM_CACHE = os.path.join(config.BGM_DIR, "pixabay")
SFX_CACHE = os.path.join(getattr(config, "ASSETS_DIR", config.BASE_DIR), "sfx", "pixabay")


def _ensure_dirs():
    for d in (VOICELAB_DIR, BGM_CACHE, SFX_CACHE, config.BGM_DIR):
        os.makedirs(d, exist_ok=True)


def search_pixabay_music(query: str, per_page: int = 12) -> List[Dict[str, Any]]:
    """
    Pixabay music endpoint (same API key as images/videos).
    Falls back gracefully if endpoint unavailable.
    """
    key = getattr(config, "PIXABAY_API_KEY", "") or ""
    if not key:
        return []
    results = []
    # Official-ish music API path used by Pixabay clients
    urls = [
        f"https://pixabay.com/api/audio/?key={key}&q={requests.utils.quote(query)}&per_page={per_page}",
        f"https://pixabay.com/api/?key={key}&q={requests.utils.quote(query)}&audio_type=music&per_page={per_page}",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=12, headers={"User-Agent": "ShortsVideoCreators/2.0"})
            if r.status_code != 200:
                continue
            data = r.json()
            hits = data.get("hits") or data.get("results") or []
            for h in hits:
                audio_url = (
                    h.get("audio")
                    or h.get("url")
                    or h.get("previewURL")
                    or (h.get("audios") or {}).get("medium", {}).get("url")
                    or (h.get("audios") or {}).get("tiny", {}).get("url")
                )
                if not audio_url:
                    continue
                results.append({
                    "id": h.get("id"),
                    "title": h.get("title") or h.get("tags") or query,
                    "url": audio_url,
                    "duration": h.get("duration"),
                    "source": "pixabay",
                    "license": "Pixabay Content License (royalty-free)",
                    "tags": h.get("tags", ""),
                })
            if results:
                break
        except Exception as e:
            print(f"  [VoiceLab/RF] Pixabay music notice: {e}")
    return results


def search_pixabay_sfx(query: str, per_page: int = 10) -> List[Dict[str, Any]]:
    key = getattr(config, "PIXABAY_API_KEY", "") or ""
    if not key:
        return []
    try:
        url = (
            f"https://pixabay.com/api/audio/?key={key}"
            f"&q={requests.utils.quote(query)}&audio_type=sound_effect&per_page={per_page}"
        )
        r = requests.get(url, timeout=12, headers={"User-Agent": "ShortsVideoCreators/2.0"})
        if r.status_code != 200:
            return search_pixabay_music(query, per_page=per_page)
        hits = r.json().get("hits") or []
        out = []
        for h in hits:
            audio_url = h.get("url") or h.get("audio") or (h.get("audios") or {}).get("tiny", {}).get("url")
            if audio_url:
                out.append({
                    "id": h.get("id"),
                    "title": h.get("title") or h.get("tags") or query,
                    "url": audio_url,
                    "source": "pixabay_sfx",
                    "license": "Pixabay Content License",
                })
        return out
    except Exception:
        return []


# Mixkit free stock music (no key) — full tracks at assets.mixkit.co/music/{n}/{n}.mp3
# (preview/*.mp3 returns 403; numeric paths are publicly downloadable)
MIXKIT_TRACKS = [
    {"id": "mixkit-tech-house-vibes-130", "title": "Tech House Vibes", "mood": "energetic",
     "url": "https://assets.mixkit.co/music/130/130.mp3"},
    {"id": "mixkit-hip-hop-02-738", "title": "Hip Hop 02", "mood": "urban",
     "url": "https://assets.mixkit.co/music/738/738.mp3"},
    {"id": "mixkit-dreaming-big-31", "title": "Dreaming Big", "mood": "inspirational",
     "url": "https://assets.mixkit.co/music/31/31.mp3"},
    {"id": "mixkit-serene-view-443", "title": "Serene View", "mood": "calm",
     "url": "https://assets.mixkit.co/music/443/443.mp3"},
    {"id": "mixkit-deep-urban-623", "title": "Deep Urban", "mood": "dark",
     "url": "https://assets.mixkit.co/music/623/623.mp3"},
    {"id": "mixkit-cat-walk-371", "title": "Cat Walk", "mood": "fun",
     "url": "https://assets.mixkit.co/music/371/371.mp3"},
    {"id": "mixkit-hazy-after-hours-132", "title": "Hazy After Hours", "mood": "mysterious",
     "url": "https://assets.mixkit.co/music/132/132.mp3"},
    {"id": "mixkit-games-worldbeat-466", "title": "Games Worldbeat", "mood": "epic",
     "url": "https://assets.mixkit.co/music/466/466.mp3"},
]


def search_mixkit(mood_or_query: str = "") -> List[Dict[str, Any]]:
    q = (mood_or_query or "").lower()
    out = []
    for t in MIXKIT_TRACKS:
        if not q or q in t["title"].lower() or q in t["mood"] or q in t["id"]:
            out.append({**t, "source": "mixkit", "license": "Mixkit License (royalty-free)"})
    return out or [{**t, "source": "mixkit", "license": "Mixkit License (royalty-free)"} for t in MIXKIT_TRACKS]


def download_track(url: str, dest_path: str) -> Optional[str]:
    try:
        r = requests.get(
            url,
            timeout=90,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
                "Referer": "https://mixkit.co/",
            },
            stream=True,
        )
        if r.status_code != 200:
            return None
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        if os.path.getsize(dest_path) < 2000:
            os.remove(dest_path)
            return None
        return dest_path
    except Exception as e:
        print(f"  [VoiceLab/RF] Download fail: {e}")
        return None


def fetch_royalty_free_bgm(query: str = "ambient cinematic", prefer: str = "auto", niche: str = "") -> Optional[str]:
    """
    Download a royalty-free BGM into BGM_DIR and return filename for composer.
    prefer: auto | catalog | pixabay | mixkit | local
    """
    _ensure_dirs()
    safe = re.sub(r"[^\w\-]+", "_", query)[:40] or "ambient"

    # YouTube-safe catalog (72 Mixkit tracks, lazy download)
    if prefer in ("auto", "catalog"):
        try:
            from youtube_safe_bgm_catalog import fetch_catalog_bgm
            fn = fetch_catalog_bgm(query=query, niche=niche or query)
            if fn:
                print(f"  [VoiceLab/RF] Catalog BGM: {fn}")
                return fn
        except Exception as e:
            print(f"  [VoiceLab/RF] Catalog notice: {e}")

    # Local VoiceLab pack first
    if prefer in ("auto", "local"):
        for f in os.listdir(VOICELAB_DIR) if os.path.isdir(VOICELAB_DIR) else []:
            if f.lower().endswith((".mp3", ".wav", ".m4a")):
                # Copy/symlink conceptually — just return path via copy into BGM
                src = os.path.join(VOICELAB_DIR, f)
                dest_name = f"voicelab_{f}"
                dest = os.path.join(config.BGM_DIR, dest_name)
                if not os.path.exists(dest):
                    try:
                        import shutil
                        shutil.copy2(src, dest)
                    except Exception:
                        continue
                return dest_name

    # Pixabay
    if prefer in ("auto", "pixabay") and getattr(config, "PIXABAY_API_KEY", ""):
        hits = search_pixabay_music(query, per_page=8)
        for h in hits[:5]:
            dest = os.path.join(BGM_CACHE, f"px_{h.get('id')}_{safe}.mp3")
            bgm_name = f"pixabay_{h.get('id')}_{safe}.mp3"
            bgm_path = os.path.join(config.BGM_DIR, bgm_name)
            if os.path.exists(bgm_path):
                return bgm_name
            if download_track(h["url"], dest):
                try:
                    import shutil
                    shutil.copy2(dest, bgm_path)
                    print(f"  [VoiceLab/RF] Pixabay BGM: {bgm_name}")
                    return bgm_name
                except Exception:
                    pass

    # Mixkit fallback (no key) — legacy 8-track list + full catalog search
    if prefer in ("auto", "mixkit"):
        try:
            from youtube_safe_bgm_catalog import search_catalog, ensure_catalog_track
            for t in search_catalog(query=query, limit=5):
                fn = ensure_catalog_track(track_id=t.get("id", ""))
                if fn:
                    return fn
        except Exception:
            pass
        for t in search_mixkit(query):
            bgm_name = f"mixkit_{t['id']}.mp3"
            bgm_path = os.path.join(config.BGM_DIR, bgm_name)
            if os.path.exists(bgm_path):
                return bgm_name
            if download_track(t["url"], bgm_path):
                print(f"  [VoiceLab/RF] Mixkit BGM: {bgm_name}")
                return bgm_name

    # Synthetic ambient last resort
    try:
        from bgm_manager import ensure_royalty_free_ambient_bgm
        path = ensure_royalty_free_ambient_bgm()
        return os.path.basename(path)
    except Exception:
        return None


def list_voicelab_library() -> Dict[str, Any]:
    _ensure_dirs()
    local = []
    if os.path.isdir(VOICELAB_DIR):
        for f in sorted(os.listdir(VOICELAB_DIR)):
            if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg")):
                fp = os.path.join(VOICELAB_DIR, f)
                local.append({
                    "filename": f,
                    "path": fp,
                    "size_kb": round(os.path.getsize(fp) / 1024, 1),
                    "source": "voicelab_local",
                })
    bgm = []
    for f in sorted(os.listdir(config.BGM_DIR)) if os.path.isdir(config.BGM_DIR) else []:
        if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg")):
            bgm.append({"filename": f, "source": "bgm_dir"})
    return {
        "voicelab_dir": VOICELAB_DIR,
        "local_voices_or_beds": local,
        "bgm_tracks": bgm,
        "mixkit_catalog": search_mixkit(""),
        "youtube_safe_catalog": _catalog_summary(),
        "note": (
            "72 parçalık YouTube-safe katalog (Mixkit) + Pixabay Music (PIXABAY_API_KEY) "
            "+ bgm/youtube_studio/ Studio Audio Library import + voicelab/ manuel ses."
        ),
    }


def _catalog_summary() -> Dict[str, Any]:
    try:
        from youtube_safe_bgm_catalog import catalog_meta, load_catalog
        meta = catalog_meta()
        return {"count": meta.get("count", 0), "tracks": len(load_catalog())}
    except Exception:
        return {"count": 0, "tracks": 0}


def seed_voicelab_pack() -> List[str]:
    """Download a starter Mixkit pack into voicelab/ for offline use."""
    _ensure_dirs()
    saved = []
    for t in MIXKIT_TRACKS[:4]:
        dest = os.path.join(VOICELAB_DIR, f"{t['id']}.mp3")
        if os.path.exists(dest):
            saved.append(dest)
            continue
        if download_track(t["url"], dest):
            saved.append(dest)
            time.sleep(0.2)
    return saved
