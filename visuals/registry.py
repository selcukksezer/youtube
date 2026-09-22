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
                source_url=row.get("source_url", ""),
                license_url=row.get("license_url", ""),
                attribution=row.get("attribution", ""),
                semantic_evidence=row.get("semantic_evidence") or {},
                topic_match_score=float(row.get("topic_match_score") or 0.0),
                visual_verification_score=float(row.get("visual_verification_score") or 0.0),
                matched_terms=row.get("matched_terms") or [],
                extra=row.get("extra") or {},
            )
            if c.license and is_commercial_safe(c.license.license):
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
        c.topic_match_score = c.visual_verification_score = 0.0
        c.matched_terms = []
        c.semantic_evidence = {"query": query, "subject_match": False, "rejected": "already_used"}
        return -1e9
    if not c.license or not c.license.safe:
        c.topic_match_score = c.visual_verification_score = 0.0
        c.matched_terms = []
        c.semantic_evidence = {"query": query, "subject_match": False, "rejected": "unsafe_or_unknown_license"}
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
    blob = c.text.lower()
    tokens = set(re_tokens(query)) | set(re_tokens(narration))
    matched_tokens = sorted(t for t in tokens if t in blob)
    hits = len(matched_tokens)
    score += min(30, hits * 4)

    # A technically good clip is still the wrong clip when it does not
    # describe the shot.  The old baseline allowed an unrelated Pixabay or
    # Wikimedia result to win with a score of 50.  That produces the exact
    # "skyscraper title -> random atmosphere" failure we want to prevent.
    # Keep generic two-word cutaways usable, but require at least one concrete
    # subject token for a specific shot.
    # "city" inside "skyscraper tower city" must not accept a beach clip
    # whose title happens to say "city".
    from .subject_lock import query_matches_clip
    subject_match = query_matches_clip(query, c.text)
    if not subject_match:
        c.topic_match_score = c.visual_verification_score = 0.0
        c.matched_terms = matched_tokens
        c.semantic_evidence = {
            "query": query,
            "query_tokens": sorted(tokens),
            "matched_tokens": matched_tokens,
            "text_overlap": round(hits / max(1, len(tokens)), 4),
            "subject_match": False,
            "rejected": "subject_mismatch",
        }
        return -1e9
    c.semantic_evidence = {
        "query": query,
        "query_tokens": sorted(tokens),
        "matched_tokens": matched_tokens,
        "text_overlap": round(hits / max(1, len(tokens)), 4),
        "subject_match": True,
        "title_tags": c.text,
        "verification": "metadata_token_match",
    }
    c.topic_match_score = round(hits / max(1, len(tokens)), 4)
    c.visual_verification_score = round(
        len(matched_tokens) / max(1, len(re_tokens(query))), 4
    )
    c.matched_terms = matched_tokens
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
