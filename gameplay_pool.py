"""
Split-screen gameplay clip pool — category search, dedup rotation, optional cache.

Persists used gameplay IDs separately from stock footage (data/used_gameplay_ids.json).
Excludes the last N IDs (default 75) so the same clip rarely repeats within 50–100 renders.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from typing import Callable, Dict, List, Optional, Set

import config
from stock_providers import ALL_SOURCES

GAMEPLAY_CATEGORIES: Dict[str, List[str]] = {
    "auto": [],
    "mobile_game": [
        "mobile game gameplay vertical",
        "phone game screen recording",
        "casual mobile game play",
        "touch screen game vertical",
    ],
    "soap_cutting": [
        "soap cutting asmr satisfying",
        "soap carving satisfying video",
        "cutting soap cubes asmr",
    ],
    "satisfying": [
        "oddly satisfying video",
        "satisfying slime asmr",
        "kinetic sand satisfying",
        "satisfying cleaning video",
    ],
    "parkour": [
        "parkour game screen recording",
        "first person parkour gameplay",
        "mirror edge parkour gameplay",
    ],
    "subway_surfers_style": [
        "subway surfers gameplay vertical",
        "endless runner game mobile",
        "temple run style gameplay",
        "arcade runner game screen",
    ],
}

_ROTATABLE = [k for k in GAMEPLAY_CATEGORIES if k != "auto"]

_NICHE_CATEGORY_HINTS: Dict[str, str] = {
    "3_split_gameplay": "subway_surfers_style",
    "2_reddit_confessions": "mobile_game",
    "4_would_you_rather": "mobile_game",
}

DEFAULT_ROTATION_WINDOW = int(os.getenv("GAMEPLAY_ROTATION_WINDOW", "75"))
_POOL_CACHE_DIR = os.path.join(getattr(config, "ASSETS_DIR", "assets"), "gameplay_pool")
_USED_GAMEPLAY_PATH = os.path.join(
    getattr(config, "BASE_DIR", os.path.dirname(os.path.abspath(__file__))),
    "data",
    "used_gameplay_ids.json",
)

_gameplay_used_ids: List[str] = []


def _load_used_gameplay_ids() -> List[str]:
    try:
        if os.path.exists(_USED_GAMEPLAY_PATH):
            with open(_USED_GAMEPLAY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            ids = data.get("ids") if isinstance(data, dict) else data
            return [str(x) for x in (ids or [])]
    except Exception:
        pass
    return []


def _persist_used_gameplay_ids() -> None:
    try:
        os.makedirs(os.path.dirname(_USED_GAMEPLAY_PATH), exist_ok=True)
        ids = list(_gameplay_used_ids)
        if len(ids) > 5000:
            ids = ids[-5000:]
        with open(_USED_GAMEPLAY_PATH, "w", encoding="utf-8") as f:
            json.dump({"ids": ids}, f, ensure_ascii=False)
    except Exception as e:
        print(f"  [GameplayPool] used_ids persist notice: {e}")


def _warm_used_ids() -> None:
    global _gameplay_used_ids
    if not _gameplay_used_ids:
        _gameplay_used_ids = _load_used_gameplay_ids()


_warm_used_ids()


def recent_blocked_gameplay_ids(window: int = DEFAULT_ROTATION_WINDOW) -> Set[str]:
    """IDs used in the last `window` gameplay renders."""
    _warm_used_ids()
    if window <= 0:
        return set()
    return set(_gameplay_used_ids[-window:])


def record_gameplay_use(source: str, video_id: str) -> None:
    """Append a gameplay clip to rotation history."""
    key = f"{source}:{video_id}"
    _warm_used_ids()
    _gameplay_used_ids.append(key)
    _persist_used_gameplay_ids()


def resolve_gameplay_category(requested: Optional[str], niche: Optional[str] = None) -> str:
    """Pick category — explicit > niche hint > hash rotation."""
    req = (requested or "auto").strip().lower()
    if req and req != "auto" and req in GAMEPLAY_CATEGORIES:
        return req
    niche_key = (niche or "").strip()
    if niche_key in _NICHE_CATEGORY_HINTS:
        return _NICHE_CATEGORY_HINTS[niche_key]
    if niche_key:
        idx = int(hashlib.md5(niche_key.encode()).hexdigest(), 16) % len(_ROTATABLE)
        return _ROTATABLE[idx]
    return random.choice(_ROTATABLE)


def queries_for_category(category: str) -> List[str]:
    cat = category if category in GAMEPLAY_CATEGORIES else "mobile_game"
    if cat == "auto":
        cat = random.choice(_ROTATABLE)
    return list(GAMEPLAY_CATEGORIES.get(cat) or GAMEPLAY_CATEGORIES["mobile_game"])


def list_categories() -> List[Dict[str, str]]:
    labels = {
        "auto": "Otomatik (nişe göre)",
        "mobile_game": "Mobil Oyun",
        "soap_cutting": "Sabun Kesme / ASMR",
        "satisfying": "Satisfying / Rahatlatıcı",
        "parkour": "Parkour Oyunu",
        "subway_surfers_style": "Subway Surfers / Runner",
    }
    return [{"id": k, "label": labels.get(k, k)} for k in GAMEPLAY_CATEGORIES]


def _score_gameplay(video: dict, target_duration: float = 12.0) -> float:
    fw = int(video.get("fw") or video.get("width") or 0)
    fh = int(video.get("fh") or video.get("height") or 0)
    dur = float(video.get("duration") or 10)
    score = 0.0
    if fh >= fw:
        score += 40
    if fh >= 720:
        score += 20
    if fw >= 1080:
        score += 10
    if dur >= target_duration * 0.8:
        score += 15
    if dur >= 8:
        score += 10
    return score


def _download_url(url: str, path: str, cancel_check: Optional[Callable[[], bool]] = None) -> bool:
    from video_fetcher import _download
    return _download(url, path, cancel_check=cancel_check)


def _search_candidates(
    queries: List[str],
    blocked: Set[str],
    cancel_check: Optional[Callable[[], bool]] = None,
    limit_per_query: int = 12,
) -> List[tuple]:
    """Search stock providers; return (score, video) tuples not in blocked set."""
    seen: Set[str] = set()
    scored: List[tuple] = []
    for query in queries:
        if cancel_check and cancel_check():
            return []
        for _src_name, src_fn in ALL_SOURCES:
            if cancel_check and cancel_check():
                return []
            try:
                results = src_fn(query) or []
            except Exception:
                results = []
            for v in results[:limit_per_query]:
                vid = str(v.get("id", ""))
                if not vid:
                    continue
                key = f"{v.get('source', 'unknown')}:{vid}"
                if key in seen or key in blocked:
                    continue
                seen.add(key)
                sc = _score_gameplay(v)
                if sc > 0:
                    scored.append((sc, v))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def _try_cached_clip(category: str, project_dir: str, blocked: Set[str]) -> Optional[str]:
    """Optional seed pack under assets/gameplay_pool/<category>/."""
    cat_dir = os.path.join(_POOL_CACHE_DIR, category)
    if not os.path.isdir(cat_dir):
        return None
    exts = (".mp4", ".mov", ".webm", ".mkv")
    files = [
        os.path.join(cat_dir, f)
        for f in os.listdir(cat_dir)
        if f.lower().endswith(exts)
    ]
    random.shuffle(files)
    for src in files:
        key = f"cache:{os.path.basename(src)}"
        if key in blocked:
            continue
        sid = hashlib.md5(src.encode()).hexdigest()[:8]
        dest = os.path.join(project_dir, f"gameplay_cache_{sid}.mp4")
        try:
            import shutil
            shutil.copy2(src, dest)
            record_gameplay_use("cache", os.path.basename(src))
            print(f"  [GameplayPool] Cache hit: {category}/{os.path.basename(src)}")
            return dest
        except Exception:
            continue
    return None


def fetch_gameplay_clip(
    project_dir: str,
    category: str = "auto",
    niche: Optional[str] = None,
    target_duration: float = 12.0,
    cancel_check: Optional[Callable[[], bool]] = None,
    rotation_window: int = DEFAULT_ROTATION_WINDOW,
) -> Optional[str]:
    """
    Download a vertical gameplay clip for split-screen mode.
    Returns local path or None.
    """
    os.makedirs(project_dir, exist_ok=True)
    resolved = resolve_gameplay_category(category, niche)
    blocked = recent_blocked_gameplay_ids(rotation_window)
    print(f"  [GameplayPool] category={resolved} blocked={len(blocked)} (window={rotation_window})")

    cached = _try_cached_clip(resolved, project_dir, blocked)
    if cached:
        return cached

    queries = queries_for_category(resolved)
    random.shuffle(queries)
    candidates = _search_candidates(queries, blocked, cancel_check=cancel_check)
    if not candidates and blocked:
        print("  [GameplayPool] Pool exhausted — relaxing rotation window")
        candidates = _search_candidates(queries, set(), cancel_check=cancel_check)

    for sc, v in candidates[:10]:
        if cancel_check and cancel_check():
            return None
        sid = str(v["id"]).split("_")[-1]
        path = os.path.join(project_dir, f"gameplay_{v['source']}_{sid}.mp4")
        if _download_url(v["url"], path, cancel_check=cancel_check):
            record_gameplay_use(v["source"], v["id"])
            print(
                f"  [GameplayPool] OK [{v['source']}] {resolved} "
                f"{v.get('fw')}x{v.get('fh')} score:{sc:.0f} → {os.path.basename(path)}"
            )
            return path
        time.sleep(0.1)
    return None
