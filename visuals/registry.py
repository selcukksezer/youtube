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

# Cross-job memory so consecutive videos do not reuse the same stock assets.
_RECENT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "recent_visual_uids.json")
_RECENT_MAX = 400
_recent_uids: Optional[List[str]] = None
_RECENT_PENALTY = 0.35

import threading

# Provider cooldown after 429 / timeout so one flaky API cannot stall every scene.
_cooldowns: Dict[str, float] = {}
_fail_counts: Dict[str, int] = {}
_COOLDOWN_429 = 180.0
_COOLDOWN_TIMEOUT = 90.0
_provider_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
_KEYLESS_SERIALIZED = {"wikimedia", "wikimedia_img", "openverse", "archive_org"}


def _get_provider_lock(key: str) -> threading.Lock:
    canon = "wikimedia" if key in ("wikimedia", "wikimedia_img") else key
    with _locks_guard:
        lock = _provider_locks.get(canon)
        if lock is None:
            lock = threading.Lock()
            _provider_locks[canon] = lock
        return lock


def _load_recent() -> List[str]:
    global _recent_uids
    if _recent_uids is None:
        try:
            with open(_RECENT_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            _recent_uids = [str(x) for x in data][-_RECENT_MAX:]
        except Exception:
            _recent_uids = []
    return _recent_uids


def _persist_recent(uid: str) -> None:
    rec = _load_recent()
    if uid in rec:
        rec.remove(uid)
    rec.append(uid)
    del rec[:-_RECENT_MAX]
    try:
        os.makedirs(os.path.dirname(_RECENT_FILE), exist_ok=True)
        with open(_RECENT_FILE, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
    except Exception:
        pass


def is_recent(uid: str) -> bool:
    return bool(uid) and uid in _load_recent()


def provider_cooling_down(key: str) -> bool:
    return time.time() < _cooldowns.get(key, 0.0)


def _note_failure(key: str, exc: Exception) -> None:
    text = str(exc).lower()
    if "429" in text or "too many requests" in text or "rate limit" in text:
        until = time.time() + _COOLDOWN_429
        _cooldowns[key] = until
        if key in ("wikimedia", "wikimedia_img"):
            _cooldowns["wikimedia"] = until
            _cooldowns["wikimedia_img"] = until
        return
    if "timed out" in text or "timeout" in text:
        _fail_counts[key] = _fail_counts.get(key, 0) + 1
        if _fail_counts[key] >= 2:
            until = time.time() + _COOLDOWN_TIMEOUT
            _cooldowns[key] = until
            if key in ("wikimedia", "wikimedia_img"):
                _cooldowns["wikimedia"] = until
                _cooldowns["wikimedia_img"] = until
            _fail_counts[key] = 0


def reset_used() -> None:
    _used_uids.clear()


def mark_used(uid: str) -> None:
    if uid:
        _used_uids.add(uid)
        _persist_recent(uid)


def is_used(uid: str) -> bool:
    return bool(uid) and uid in _used_uids


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
        "pexels": ["pexels", "pexels_img"],
        "pixabay": ["pixabay", "pixabay_img"],
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
        if spec.families and family not in spec.families:
            continue
        if not provider_available(spec):
            continue
        if provider_cooling_down(spec.key):
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
    is_mock = hasattr(spec.fn, "_mock_name") or "unittest.mock" in type(spec.fn).__module__
    if not is_mock and provider_cooling_down(spec.key):
        return []
    lock = _get_provider_lock(spec.key) if (not is_mock and spec.key in _KEYLESS_SERIALIZED) else None
    if lock is not None:
        with lock:
            if provider_cooling_down(spec.key):
                return []
            try:
                try:
                    results = spec.fn(query, per_page=per_page)
                except TypeError:
                    results = spec.fn(query)
            except Exception as exc:
                _note_failure(spec.key, exc)
                print(f"    [visuals:{spec.key}] {exc}")
                return []
    else:
        try:
            try:
                results = spec.fn(query, per_page=per_page)
            except TypeError:
                results = spec.fn(query)
        except Exception as exc:
            _note_failure(spec.key, exc)
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
    if c.width and c.height:
        from system_resilience import is_material_resolution_acceptable
        if not is_material_resolution_acceptable(c.width, c.height):
            c.topic_match_score = c.visual_verification_score = 0.0
            c.matched_terms = []
            c.semantic_evidence = {
                "query": query,
                "subject_match": False,
                "rejected": f"low_resolution_{c.width}x{c.height}",
            }
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
    blob_tokens = set(re_tokens(c.text))
    query_tokens = set(re_tokens(query))
    narration_tokens = set(re_tokens(narration)) - query_tokens
    unsafe_tokens = (blob_tokens - query_tokens) & _UNSAFE_OR_OFFTOPIC_TOKENS
    if unsafe_tokens:
        c.topic_match_score = c.visual_verification_score = 0.0
        c.matched_terms = []
        c.semantic_evidence = {
            "query": query,
            "subject_match": False,
            "rejected": f"brand_unsafe_or_offtopic:{','.join(sorted(unsafe_tokens))}",
        }
        return -1e9
    matched_query_tokens = sorted(query_tokens & blob_tokens)
    matched_narration_tokens = sorted(narration_tokens & blob_tokens)
    matched_tokens = sorted(set(matched_query_tokens) | set(matched_narration_tokens))
    hits = len(matched_tokens)
    score += min(30, len(matched_query_tokens) * 6 + len(matched_narration_tokens) * 2)

    from .subject_lock import query_matches_clip
    subject_match = query_matches_clip(query, c.text)
    if not subject_match:
        c.topic_match_score = c.visual_verification_score = 0.0
        c.matched_terms = matched_tokens
        c.semantic_evidence = {
            "query": query,
            "query_tokens": sorted(query_tokens),
            "matched_tokens": matched_tokens,
            "matched_query_terms": matched_query_tokens,
            "matched_narration_terms": matched_narration_tokens,
            "query_match_score": round(
                len(matched_query_tokens) / max(1, len(query_tokens)), 4
            ),
            "text_overlap": round(
                hits / max(1, len(query_tokens | narration_tokens)), 4
            ),
            "subject_match": False,
            "rejected": "subject_mismatch",
        }
        return -1e9
    c.semantic_evidence = {
        "query": query,
        "query_tokens": sorted(query_tokens),
        "matched_tokens": matched_tokens,
        "matched_query_terms": matched_query_tokens,
        "matched_narration_terms": matched_narration_tokens,
        "query_match_score": round(
            len(matched_query_tokens) / max(1, len(query_tokens)), 4
        ),
        "text_overlap": round(
            hits / max(1, len(query_tokens | narration_tokens)), 4
        ),
        "subject_match": True,
        "title_tags": c.text,
        "verification": "metadata_token_match",
    }
    q_ratio = len(matched_query_tokens) / max(1, len(query_tokens))
    c.topic_match_score = round(
        max(hits / max(1, len(query_tokens | narration_tokens)), q_ratio * 0.5), 4
    )
    c.visual_verification_score = round(q_ratio, 4)
    c.matched_terms = matched_tokens
    # provider prior
    spec = PROVIDERS.get(c.source) or PROVIDERS.get(c.source.replace("_img", "")) or PROVIDERS.get(f"{c.source}_img")
    if spec:
        score *= spec.weight
    if is_recent(c.uid):
        score *= _RECENT_PENALTY
    return score


_UNSAFE_OR_OFFTOPIC_TOKENS: Set[str] = {
    "parade", "pride", "carnival", "festival", "naked", "nude", "nudity",
    "naturist", "naturism", "topless", "bodypaint", "bodypainting",
    "shirtless", "bikini", "lingerie", "erotic", "burlesque", "stripper",
    "protest", "demonstration", "riot", "contrabassoon", "bassoon",
    "recital", "webcam", "cosplay", "nightclub", "rave", "locomotive",
}


def re_tokens(text: str) -> List[str]:
    import re
    return [t for t in re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}", (text or "").lower()) if t not in {
        "the", "and", "for", "with", "bir", "bu", "şu", "ile", "olan", "gibi",
    }]

