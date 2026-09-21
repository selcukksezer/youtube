"""Provider availability, niche preference, cache, scoring."""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Dict, List, Optional, Set

from .license import is_commercial_safe
from .palettes import family_for_niche, preferred_sources
from .providers import PROVIDERS, Candidate, ProviderSpec

_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "visual_cache")
_CACHE_TTL = 6 * 3600  # 6h
_used_uids: Set[str] = set()


def reset_used() -> None:
    _used_uids.clear()


def mark_used(uid: str) -> None:
    if uid:
        _used_uids.add(uid)


def provider_available(spec: ProviderSpec) -> bool:
    if not spec.key_env:
        return True
    try:
        import config
        return bool(getattr(config, spec.key_env, "") or os.environ.get(spec.key_env, ""))
    except Exception:
        return bool(os.environ.get(spec.key_env, ""))


def ordered_providers(niche_id: str = "") -> List[ProviderSpec]:
    family = family_for_niche(niche_id)
    pref = preferred_sources(niche_id)
    # Map palette keys → provider keys
    alias = {
        "pexels": ["pexels"],
        "pixabay": ["pixabay"],
        "coverr": ["coverr"],
        "wikimedia": ["wikimedia", "wikimedia_img"],
        "nasa": ["nasa", "nasa_img"],
        "openverse": ["openverse"],
        "archive_org": ["archive_org"],
    }
    ordered_keys: List[str] = []
    for p in pref:
        for k in alias.get(p, [p]):
            if k not in ordered_keys:
                ordered_keys.append(k)
    for k in PROVIDERS:
        if k not in ordered_keys:
            ordered_keys.append(k)

    out: List[ProviderSpec] = []
    for k in ordered_keys:
        spec = PROVIDERS.get(k)
        if not spec:
            continue
        if spec.families and family not in spec.families and family != "general":
            continue
        if not provider_available(spec):
            continue
        out.append(spec)
    return out


def _cache_path(provider: str, query: str) -> str:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    h = hashlib.sha1(f"{provider}:{query.lower()}".encode()).hexdigest()[:20]
    return os.path.join(_CACHE_DIR, f"{provider}_{h}.json")


def _load_cache(provider: str, query: str) -> Optional[List[dict]]:
    path = _cache_path(provider, query)
    if not os.path.isfile(path):
        return None
    try:
        if time.time() - os.path.getmtime(path) > _CACHE_TTL:
            return None
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _save_cache(provider: str, query: str, rows: List[dict]) -> None:
    try:
        with open(_cache_path(provider, query), "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
    except Exception:
        pass


def search_provider(spec: ProviderSpec, query: str, per_page: int = 10) -> List[Candidate]:
    cached = _load_cache(spec.key, query)
    if cached is not None:
        from .license import LicenseInfo
        out = []
        for row in cached:
            lic = row.get("license")
            c = Candidate(
                source=row["source"], id=row["id"], url=row["url"], kind=row.get("kind", spec.kind),
                width=row.get("width", 0), height=row.get("height", 0), duration=row.get("duration", 0),
                title=row.get("title", ""), tags=row.get("tags") or [], thumbnail=row.get("thumbnail", ""),
                contributor=row.get("contributor", ""),
                license=LicenseInfo.from_dict(lic) if lic else None,
                extra=row.get("extra") or {},
            )
            out.append(c)
        return out
    try:
        results = spec.fn(query, per_page=per_page)
    except TypeError:
        results = spec.fn(query)
    except Exception as exc:
        print(f"    [visuals:{spec.key}] {exc}")
        return []
    safe = [c for c in results if c.license and is_commercial_safe(c.license.license)]
    try:
        _save_cache(spec.key, query, [c.to_dict() for c in safe])
    except Exception:
        pass
    return safe


def score_candidate(
    c: Candidate,
    query: str,
    narration: str = "",
    target_duration: float = 7.0,
) -> float:
    if c.uid in _used_uids:
        return -1e9
    if not c.license or not c.license.safe:
        return -1e9
    score = 50.0
    # portrait bonus
    if c.is_portrait:
        score += 25
    elif c.width and c.height:
        score += 5
    # duration fit (video)
    if c.kind == "video" and c.duration > 0:
        score += max(0, 15 - abs(c.duration - target_duration))
    else:
        score += 8  # images OK via Ken Burns
    # text overlap
    blob = f"{c.text} {query}".lower()
    tokens = set(re_tokens(query)) | set(re_tokens(narration))
    hits = sum(1 for t in tokens if t in blob)
    score += min(30, hits * 4)
    # provider prior
    spec = PROVIDERS.get(c.source) or PROVIDERS.get(c.source.replace("_img", ""))
    if spec:
        score *= spec.weight
    return score


def re_tokens(text: str) -> List[str]:
    import re
    return [t for t in re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}", (text or "").lower()) if t not in {
        "the", "and", "for", "with", "bir", "bu", "şu", "ile", "olan", "gibi",
    }]
