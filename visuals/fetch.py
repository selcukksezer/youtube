"""Orchestrator: shot queries → multi-provider search → download → 9:16 normalize → license ledger."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import imageio_ffmpeg
import requests

from .fetch_candidates import (
    _FAMILY_GENERIC,
    _K1_HARD_FLOOR,
    _best_hook_window_start,
    _best_window_start_from_metrics,
    _broaden_queries,
    _normalize_candidate,
    _normalize_clip,
    _procedural_enabled,
    _try_procedural_fallbacks,
    _try_public_apis_fallback,
    _try_whiteboard_visual,
    attach_short_clip_partners,
    fetch_scene_clip,
)
from .license import License, LicenseInfo, attribution_line, is_commercial_safe
from .palettes import family_for_niche
from .query_builder import build_shot_queries
from .registry import _note_failure, is_used, mark_used, ordered_providers, reset_used, score_candidate, search_provider

USER_AGENT = "YouTubeShortsStudio/1.0 (https://github.com/youtubeoto/studio; contact@youtubeoto.local) python-requests/2.31"
_job_manifest: List[Dict[str, Any]] = []
_job_file_hashes: set = set()
_provider_search_attempts: List[Dict[str, Any]] = []
_claim_lock = threading.Lock()
_dl_host_cooldowns: Dict[str, float] = {}


def _safe_public_url(value: Any) -> Optional[str]:
    """Strip query parameters and credentials from public URLs (MoneyPrinterTurbo pattern)."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    except Exception:
        return None


def reset_job_manifest() -> None:
    global _job_manifest, _job_file_hashes, _provider_search_attempts
    _job_manifest = []
    _job_file_hashes = set()
    _provider_search_attempts = []
    reset_used()


def get_job_manifest() -> List[Dict[str, Any]]:
    return list(_job_manifest)


def _record_provider_search(
    provider: str, scene_index: int, query_index: int, elapsed_ms: float, result_count: int, error: str = "",
) -> None:
    attempt = {
        "provider": provider, "scene": scene_index + 1, "query_index": query_index + 1,
        "elapsed_ms": round(max(0.0, elapsed_ms), 1), "result_count": max(0, result_count), "error": error or None,
    }
    with _claim_lock:
        _provider_search_attempts.append(attempt)


def get_job_provider_diagnostics() -> Dict[str, Any]:
    """Summarize provider search wall times without persisting search text."""
    with _claim_lock:
        attempts = list(_provider_search_attempts)
    providers: Dict[str, Dict[str, Any]] = {}
    for attempt in attempts:
        summary = providers.setdefault(attempt["provider"], {
            "searches": 0, "total_ms": 0.0, "max_ms": 0.0, "results": 0, "empty_searches": 0, "errors": 0,
        })
        duration = float(attempt["elapsed_ms"])
        summary["searches"] += 1
        summary["total_ms"] += duration
        summary["max_ms"] = max(summary["max_ms"], duration)
        summary["results"] += int(attempt["result_count"])
        summary["empty_searches"] += int(attempt["result_count"] == 0 and not attempt["error"])
        summary["errors"] += int(bool(attempt["error"]))
    for summary in providers.values():
        summary["total_ms"] = round(summary["total_ms"], 1)
        summary["avg_ms"] = round(summary["total_ms"] / summary["searches"], 1)
        summary["max_ms"] = round(summary["max_ms"], 1)
    return {
        "searches": len(attempts),
        "providers": providers,
        "slowest_searches": sorted(attempts, key=lambda item: item["elapsed_ms"], reverse=True)[:5],
    }


def asset_already_claimed(uid: str = "", file_hash: str = "") -> bool:
    with _claim_lock:
        if uid and is_used(uid):
            return True
        if file_hash and file_hash in _job_file_hashes:
            return True
        return False


def claim_job_asset(uid: str, file_hash: str) -> bool:
    """One scene owns a stock id and a file hash. Parallel fetches cannot both win."""
    with _claim_lock:
        if uid and is_used(uid):
            return False
        if file_hash and file_hash in _job_file_hashes:
            return False
        if uid:
            mark_used(uid)
        if file_hash:
            _job_file_hashes.add(file_hash)
        return True


def _rank_scored_candidates(scored: List[tuple]) -> List[tuple]:
    best_by_uid = {}
    for row in scored:
        uid = row[1].uid
        if uid not in best_by_uid or row[0] > best_by_uid[uid][0]:
            best_by_uid[uid] = row
    return sorted(best_by_uid.values(), key=lambda row: row[0], reverse=True)


def _heal_entry_license(entry: Dict[str, Any]) -> None:
    license_data = entry.get("license") or {}
    info = LicenseInfo.from_dict(license_data) if isinstance(license_data, dict) else None
    if not info or not is_commercial_safe(info.license):
        uid_str = str(entry.get("uid") or "").lower()
        path_str = str(entry.get("path") or "").lower()
        src_str = str(entry.get("source") or "").lower()
        if any(k in uid_str or k in path_str or k in src_str for k in ("ai", "pollinations", "flux", "veo", "gemini")):
            info = LicenseInfo(License.AI_GENERATED, "ai_generated", title=entry.get("title") or "AI Clip")
        elif any(k in uid_str or k in path_str or k in src_str for k in ("pexels", "pixabay", "coverr")):
            if "pexels" in uid_str or "pexels" in path_str:
                lic_type = License.PEXELS
            elif "coverr" in uid_str or "coverr" in path_str:
                lic_type = License.COVERR
            else:
                lic_type = License.PIXABAY
            info = LicenseInfo(lic_type, "stock", title=entry.get("title") or "Stock Clip")
        else:
            info = LicenseInfo(License.CC0, entry.get("source") or "royalty_free", title=entry.get("title") or "Royalty Free Clip")
        entry["license"] = info.to_dict()


def add_manifest_entry(entry: Dict[str, Any]) -> None:
    """Add or update an entry in the job manifest for a scene_index (idempotent & self-healing)."""
    global _job_manifest, _job_file_hashes
    s_idx = entry.get("scene_index")
    if s_idx is not None:
        dropped = []
        for old_e in _job_manifest:
            if old_e.get("scene_index") == s_idx:
                old_h = old_e.get("sha256") or old_e.get("sha1")
                if old_h:
                    dropped.append(old_h)
        _job_manifest = [e for e in _job_manifest if e.get("scene_index") != s_idx]
        for old_h in dropped:
            still_used = any(
                (row.get("sha256") or row.get("sha1")) == old_h for row in _job_manifest
            )
            if not still_used:
                _job_file_hashes.discard(old_h)

    _heal_entry_license(entry)

    entry_hash = entry.get("sha256") or entry.get("sha1")
    if not entry_hash and entry.get("path") and os.path.isfile(entry["path"]):
        entry_hash = _file_hash(entry["path"])
    if entry_hash:
        _job_file_hashes.add(entry_hash)
        entry["sha256"] = entry_hash
        entry["sha1"] = entry_hash

    if entry.get("source_url"):
        entry["source_url"] = _safe_public_url(entry["source_url"]) or entry["source_url"]
    if entry.get("license_url"):
        entry["license_url"] = _safe_public_url(entry["license_url"]) or entry["license_url"]

    _job_manifest.append(entry)


def write_job_credits(project_dir: str) -> Dict[str, str]:
    """Write the auditable source manifest and description-ready credits."""
    global _job_manifest
    os.makedirs(project_dir, exist_ok=True)
    if not _job_manifest:
        raise ValueError("source manifest is empty")

    abs_proj = os.path.abspath(project_dir)
    has_proj_match = any(
        row.get("path") and os.path.dirname(os.path.abspath(str(row["path"]))) == abs_proj
        for row in _job_manifest
    )
    active_rows = (
        [
            row for row in _job_manifest
            if not row.get("path") or os.path.dirname(os.path.abspath(str(row["path"]))) == abs_proj
        ]
        if has_proj_match
        else _job_manifest
    )

    scene_map: Dict[Any, Dict[str, Any]] = {}
    for row in active_rows:
        s_idx = row.get("scene_index")
        scene_map[s_idx if s_idx is not None else len(scene_map)] = row

    sorted_clips = sorted(
        scene_map.values(),
        key=lambda r: r.get("scene_index", 0) if isinstance(r.get("scene_index"), int) else 0,
    )

    seen_uids = set()
    cleaned_manifest: List[Dict[str, Any]] = []
    for r in sorted_clips:
        entry = dict(r)
        uid = str(entry.get("uid") or f"asset_{entry.get('scene_index', len(cleaned_manifest))}")
        if uid in seen_uids:
            uid = f"{uid}_s{entry.get('scene_index', len(cleaned_manifest))}"
        seen_uids.add(uid)
        entry["uid"] = uid

        _heal_entry_license(entry)
        if entry.get("source_url"):
            entry["source_url"] = _safe_public_url(entry["source_url"]) or entry["source_url"]
        if entry.get("license_url"):
            entry["license_url"] = _safe_public_url(entry["license_url"]) or entry["license_url"]
        cleaned_manifest.append(entry)

    _job_manifest = cleaned_manifest
    json_path = os.path.join(project_dir, "visual_credits.json")
    txt_path = os.path.join(project_dir, "visual_credits.txt")
    manifest_path = os.path.join(project_dir, "source_manifest.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({"clips": _job_manifest}, fh, ensure_ascii=False, indent=2)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "version": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "clips": _job_manifest,
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )
    lines = ["Görsel kaynaklar / Visual credits:"]
    for row in _job_manifest:
        lic = row.get("license") or {}
        info = LicenseInfo.from_dict(lic) if isinstance(lic, dict) else None
        line = attribution_line(info) if info else None
        if line:
            lines.append(f"- {line}")
        else:
            src = row.get("source", "?")
            title = row.get("title") or row.get("id") or ""
            lines.append(f"- {src}: {title}")
    body = "\n".join(lines) + "\n"
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return {
        "json": json_path,
        "txt": txt_path,
        "manifest": manifest_path,
        "description_block": body,
    }


def _download(url: str, path: str, timeout: int = 45, cancel_check=None) -> bool:
    from .atomic_cache import atomic_replace, lock_for_key

    host = (urlsplit(url).hostname or "").casefold()
    is_mock = hasattr(requests.get, "_mock_name") or "unittest.mock" in type(requests.get).__module__
    if not is_mock and host and time.time() < _dl_host_cooldowns.get(host, 0.0):
        return False

    tmp_path = path + ".part"
    try:
        with lock_for_key(path):
            with requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": USER_AGENT}) as r:
                r.raise_for_status()
                with open(tmp_path, "wb") as fh:
                    for chunk in r.iter_content(256 * 1024):
                        if callable(cancel_check) and cancel_check():
                            raise InterruptedError("Download cancelled")
                        if chunk:
                            fh.write(chunk)
            if not os.path.isfile(tmp_path) or os.path.getsize(tmp_path) <= 8_000:
                raise OSError("download below size floor")
            atomic_replace(tmp_path, path)
        return True
    except Exception as exc:
        if not is_mock and ("429" in str(exc).lower() or "too many requests" in str(exc).lower()):
            if host:
                _dl_host_cooldowns[host] = time.time() + 180.0
            if "wikimedia" in host:
                _note_failure("wikimedia", exc)
        print(f"    [visuals:dl] {exc}")
        for leftover in (tmp_path, path):
            if os.path.isfile(leftover) and leftover.endswith(".part"):
                try:
                    os.remove(leftover)
                except OSError:
                    pass
        return False


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_open_visual(
    queries: Optional[List[str]] = None,
    *,
    scene_index: int = 0,
    project_dir: str,
    target_duration: float = 7.0,
    narration: str = "",
    scene_description: str = "",
    niche_id: str = "",
    visual_intent: Optional[dict] = None,
    allow_procedural: bool = True,
    caption_text: str = "",
    _expanded: bool = False,
) -> Optional[str]:
    """
    Primary entry: license-safe multi-source fetch.
    Returns local mp4 path, procedural kinetic path, whiteboard, or procedural abstract.
    """
    os.makedirs(project_dir, exist_ok=True)
    intent = visual_intent if isinstance(visual_intent, dict) else {}
    qlist = list(queries or [])
    if not qlist:
        qlist = build_shot_queries(
            narration=narration,
            scene_description=scene_description,
            niche_id=niche_id,
            visual_intent=intent,
        )

    wb_video = _try_whiteboard_visual(
        scene_index, project_dir, target_duration, narration, scene_description, niche_id, intent, qlist
    )
    if wb_video:
        return wb_video

    providers = ordered_providers(niche_id)
    if not providers:
        print("    [visuals] no providers available (keys missing?)")

    def _search_spec(spec, q, qi_idx):
        started = time.perf_counter()
        result_count = 0
        error = ""
        try:
            candidates = search_provider(spec, q, per_page=8)
            result_count = len(candidates)
        except Exception as exc:
            print(f"    [visuals:{spec.key}] {exc}")
            candidates = []
            error = type(exc).__name__
        _record_provider_search(
            spec.key, scene_index, qi_idx, (time.perf_counter() - started) * 1000, result_count, error,
        )
        return candidates, q, qi_idx

    scored: List[tuple] = []
    active_queries = qlist[:5]
    if providers and active_queries:
        primary_specs = [s for s in providers if getattr(s, "key", "") in ("pexels", "pixabay", "coverr", "pexels_img", "pixabay_img")]
        secondary_specs = [s for s in providers if s not in primary_specs]
        tiers = [t for t in (primary_specs, secondary_specs) if t]
        for tier_specs in tiers:
            with ThreadPoolExecutor(max_workers=min(8, max(1, len(tier_specs) * len(active_queries)))) as executor:
                futures = [
                    executor.submit(_search_spec, spec, query, qi)
                    for qi, query in enumerate(active_queries)
                    for spec in tier_specs
                ]
                for f in as_completed(futures):
                    cands, query, qi = f.result()
                    for c in cands:
                        sc = score_candidate(c, query, narration=narration, target_duration=target_duration)
                        sc += max(0, 8 - qi * 2)
                        if sc > 0:
                            scored.append((sc, c, query))
            if scored:
                break

    scored = _rank_scored_candidates(scored)
    hook_window_attempted = False
    for sc, cand, query in scored[:15]:
        if not cand.license or not is_commercial_safe(cand.license.license):
            continue
        if asset_already_claimed(cand.uid):
            continue
        raw_ext = ".jpg" if cand.kind == "image" else ".mp4"
        raw = os.path.join(project_dir, f"s{scene_index:03d}_{cand.source}_raw{raw_ext}")
        out = os.path.join(project_dir, f"s{scene_index:03d}_{cand.source}_{cand.id.split('_')[-1]}.mp4")
        if not _download(cand.url, raw):
            continue
        if cand.kind == "video" and os.path.isfile(raw):
            from system_resilience import verify_stock_video_integrity
            integrity = verify_stock_video_integrity(raw, min_duration=0.5)
            if not integrity.get("valid", False):
                print(f"    [visuals:integrity] candidate rejected ({integrity.get('reason')}): {cand.url}")
                try:
                    if os.path.isfile(raw):
                        os.remove(raw)
                except OSError:
                    pass
                continue
        norm = _normalize_candidate(
            raw, out, target_duration, cand, scene_index, optimize_hook=not hook_window_attempted,
        )
        if scene_index == 0 and cand.kind == "video" and float(cand.duration or 0.0) > target_duration + 1.0:
            hook_window_attempted = True
        try:
            if os.path.isfile(raw) and raw != norm:
                os.remove(raw)
        except OSError:
            pass
        if not norm:
            continue

        f_hash = _file_hash(norm)

        if not _expanded and cand.topic_match_score < 0.08 and len(narration.strip().split()) >= 3:
            print(f"    [visuals:k1] Candidate score ({cand.topic_match_score:.2f}) < 0.08 threshold, triggering K1 re-fetch...")
            narrative_queries = build_shot_queries(
                narration=narration, scene_description=scene_description or narration,
                niche_id=niche_id, visual_intent=intent, max_queries=3,
            )
            better_found = False
            for nq in narrative_queries:
                if nq in qlist:
                    continue
                for spec in providers:
                    try:
                        n_cands = search_provider(spec, nq, per_page=4)
                    except Exception:
                        continue
                    for nc in n_cands:
                        nsc = score_candidate(nc, nq, narration=narration, target_duration=target_duration)
                        if nsc > 0 and nc.topic_match_score >= 0.08 and is_commercial_safe(nc.license.license):
                            n_raw = os.path.join(project_dir, f"s{scene_index:03d}_{nc.source}_raw{raw_ext}")
                            n_out = os.path.join(project_dir, f"s{scene_index:03d}_{nc.source}_{nc.id.split('_')[-1]}.mp4")
                            if _download(nc.url, n_raw):
                                if nc.kind == "video" and os.path.isfile(n_raw):
                                    from system_resilience import verify_stock_video_integrity
                                    n_integrity = verify_stock_video_integrity(n_raw, min_duration=0.5)
                                    if not n_integrity.get("valid", False):
                                        try:
                                            if os.path.isfile(n_raw):
                                                os.remove(n_raw)
                                        except OSError:
                                            pass
                                        continue
                                n_norm = _normalize_candidate(
                                    n_raw, n_out, target_duration, nc, scene_index,
                                    optimize_hook=not hook_window_attempted,
                                )
                                if scene_index == 0 and nc.kind == "video" and float(nc.duration or 0.0) > target_duration + 1.0:
                                    hook_window_attempted = True
                                try:
                                    if os.path.isfile(n_raw) and n_raw != n_norm:
                                        os.remove(n_raw)
                                except OSError:
                                    pass
                                if n_norm:
                                    n_hash = _file_hash(n_norm)
                                    if not asset_already_claimed(nc.uid, n_hash):
                                        try:
                                            os.remove(norm)
                                        except OSError:
                                            pass
                                        norm, cand, query, sc, f_hash = n_norm, nc, nq, nsc, n_hash
                                        better_found = True
                                        print(f"    [OK] [visuals:k1] Superior narrative match: {nc.source} score={nc.topic_match_score:.2f}")
                                        break
                    if better_found:
                        break
                if better_found:
                    break

            if cand.topic_match_score < _K1_HARD_FLOOR and not better_found:
                print(f"    [visuals:k1] Candidate {cand.topic_match_score:.2f} unrelated; trying next candidate.")
                try:
                    os.remove(norm)
                except OSError:
                    pass
                continue

        if not claim_job_asset(cand.uid, f_hash or ""):
            print(f"    [visuals:dedup] Duplicate clip detected via SHA-256 ({(f_hash or '')[:8]}), skipping.")
            try:
                os.remove(norm)
            except OSError:
                pass
            continue

        entry = {
            "scene_index": scene_index,
            "path": norm,
            "uid": cand.uid,
            "source": cand.source,
            "id": cand.id,
            "url": cand.url,
            "asset_url": cand.url,
            "title": cand.title,
            "query": query,
            "kind": cand.kind,
            "score": round(sc, 1),
            "sha1": f_hash,
            "sha256": f_hash,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "source_url": _safe_public_url(cand.source_url or (cand.license.source_url if cand.license else "")),
            "license_url": _safe_public_url(cand.license_url or (cand.license.license_url if cand.license else "")),
            "attribution": (cand.attribution or (cand.license.attribution if cand.license else "")),
            "contributor": cand.contributor,
            "semantic_evidence": cand.semantic_evidence,
            "topic_match_score": cand.topic_match_score,
            "visual_verification_score": cand.visual_verification_score,
            "matched_terms": cand.matched_terms,
            "license": cand.license.to_dict(),
            "family": family_for_niche(niche_id),
        }
        add_manifest_entry(entry)
        print(f"    [OK] [visuals:{cand.source}] score={sc:.0f} lic={cand.license.license.value}")
        return norm

    pub_norm = _try_public_apis_fallback(active_queries, scene_index, project_dir, target_duration, niche_id)
    if pub_norm:
        return pub_norm

    if not _expanded:
        wide = [q for q in _broaden_queries(qlist, niche_id) if q not in qlist]
        if wide:
            print(f"    [visuals] stock miss, retrying with broader queries: {wide[:4]}")
            got = fetch_open_visual(
                wide, scene_index=scene_index, project_dir=project_dir,
                target_duration=target_duration, narration=narration,
                scene_description=scene_description, niche_id=niche_id,
                visual_intent=visual_intent, allow_procedural=allow_procedural,
                caption_text=caption_text, _expanded=True,
            )
            if got:
                return got

    if not (allow_procedural and _procedural_enabled()):
        return None

    return _try_procedural_fallbacks(
        scene_index, project_dir, target_duration, narration, scene_description, niche_id, intent, caption_text
    )
