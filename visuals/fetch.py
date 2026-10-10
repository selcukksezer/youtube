"""Orchestrator: shot queries → multi-provider search → download → 9:16 normalize → license ledger."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import imageio_ffmpeg
import requests

from .license import License, LicenseInfo, attribution_line, is_commercial_safe
from .palettes import family_for_niche
from .providers import Candidate
from .query_builder import build_shot_queries
from .registry import is_used, mark_used, ordered_providers, reset_used, score_candidate, search_provider

from urllib.parse import urlsplit, urlunsplit

USER_AGENT = "youtubeoto-shorts/1.0 (license-aware fetch)"
_job_manifest: List[Dict[str, Any]] = []
_job_file_hashes: set = set()
_provider_search_attempts: List[Dict[str, Any]] = []
_claim_lock = threading.Lock()


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
    provider: str,
    scene_index: int,
    query_index: int,
    elapsed_ms: float,
    result_count: int,
    error: str = "",
) -> None:
    attempt = {
        "provider": provider,
        "scene": scene_index + 1,
        "query_index": query_index + 1,
        "elapsed_ms": round(max(0.0, elapsed_ms), 1),
        "result_count": max(0, result_count),
        "error": error or None,
    }
    with _claim_lock:
        _provider_search_attempts.append(attempt)


def get_job_provider_diagnostics() -> Dict[str, Any]:
    """Summarize provider search wall times without persisting search text."""
    with _claim_lock:
        attempts = list(_provider_search_attempts)
    providers: Dict[str, Dict[str, Any]] = {}
    for attempt in attempts:
        provider = attempt["provider"]
        summary = providers.setdefault(provider, {
            "searches": 0,
            "total_ms": 0.0,
            "max_ms": 0.0,
            "results": 0,
            "empty_searches": 0,
            "errors": 0,
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
        "slowest_searches": sorted(
            attempts, key=lambda item: item["elapsed_ms"], reverse=True
        )[:5],
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

    # Commercial safety validation & self-healing
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

    # 1. Deduplicate by scene_index: ensure only latest clip per scene is preserved
    scene_map: Dict[Any, Dict[str, Any]] = {}
    for row in _job_manifest:
        s_idx = row.get("scene_index")
        scene_map[s_idx if s_idx is not None else len(scene_map)] = row

    sorted_clips = sorted(
        scene_map.values(),
        key=lambda r: r.get("scene_index", 0) if isinstance(r.get("scene_index"), int) else 0
    )

    # 2. Ensure all UIDs are present, strictly unique, and licenses are commercial-safe
    seen_uids = set()
    cleaned_manifest: List[Dict[str, Any]] = []
    for r in sorted_clips:
        entry = dict(r)
        uid = str(entry.get("uid") or f"asset_{entry.get('scene_index', len(cleaned_manifest))}")
        if uid in seen_uids:
            uid = f"{uid}_s{entry.get('scene_index', len(cleaned_manifest))}"
        seen_uids.add(uid)
        entry["uid"] = uid

        # Commercial safety validation & self-healing
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


def _download(url: str, path: str, timeout: int = 45) -> bool:
    from .atomic_cache import atomic_replace, lock_for_key

    tmp_path = path + ".part"
    try:
        with lock_for_key(path):
            with requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": USER_AGENT}) as r:
                r.raise_for_status()
                with open(tmp_path, "wb") as fh:
                    for chunk in r.iter_content(256 * 1024):
                        if chunk:
                            fh.write(chunk)
            if not os.path.isfile(tmp_path) or os.path.getsize(tmp_path) <= 8_000:
                raise OSError("download below size floor")
            atomic_replace(tmp_path, path)
        return True
    except Exception as exc:
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


def _normalize_clip(
    src: str,
    dst: str,
    duration: float,
    kind: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> Optional[str]:
    """Crop/scale to 9:16. Stills get a cheap crop-pan, not zoompan."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    dur = max(1.2, float(duration))
    if kind == "image":
        from render.ffmpeg_graph import cheap_pan_filter
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},"
            f"{cheap_pan_filter(width, height, dur, 0)},"
            "format=yuv420p"
        )
        cmd = [
            ffmpeg, "-y", "-loglevel", "error",
            "-loop", "1", "-i", src,
            "-t", f"{dur:.3f}", "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-an", dst,
        ]
    else:
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},format=yuv420p"
        )
        cmd = [
            ffmpeg, "-y", "-loglevel", "error",
            "-i", src, "-t", f"{dur:.3f}", "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-an", dst,
        ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    except Exception as exc:
        print(f"    [visuals:norm] {exc}")
        return None
    if res.returncode != 0 or not (os.path.isfile(dst) and os.path.getsize(dst) > 10_000):
        return None
    return dst


_K1_HARD_FLOOR = 0.03

_FAMILY_GENERIC = {
    "religious": ["mosque architecture", "prayer light", "ancient manuscript", "sunrise sky clouds"],
    "history": ["ancient ruins", "old map", "historic architecture"],
    "mystery": ["dark forest fog", "night sky", "abandoned building"],
    "nature": ["nature landscape", "ocean waves", "mountain sky"],
    "general": ["cinematic landscape", "city skyline", "sky clouds timelapse"],
}


def _procedural_enabled() -> bool:
    return os.getenv("ALLOW_PROCEDURAL_VISUALS", "").lower() in ("1", "true", "yes", "on")


def _broaden_queries(qlist: List[str], niche_id: str, narration: str = "") -> List[str]:
    """Shorter / more generic variants of the failed queries plus family-level themes."""
    out: List[str] = []
    for q in qlist:
        words = [w for w in str(q).split() if len(w) > 2]
        if len(words) > 2:
            out.append(" ".join(words[:2]))
            out.append(" ".join(words[-2:]))
        elif words:
            out.append(words[0])
    out.extend(_FAMILY_GENERIC.get(family_for_niche(niche_id), _FAMILY_GENERIC["general"]))
    seen, res = set(), []
    for q in out:
        k = q.lower()
        if k not in seen:
            seen.add(k)
            res.append(q)
    return res[:6]


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

    # 6.1 Whiteboard Canvas Animator option
    if os.getenv("ALLOW_PROCEDURAL_VISUALS", "").lower() in ("1", "true", "yes", "on") and (
        (intent and intent.get("style") == "whiteboard") or "whiteboard" in (niche_id or "").lower()
    ):
        try:
            from services.whiteboard_animator import generate_whiteboard_sketch_image, animate_whiteboard_clip
            sketch_img = os.path.join(project_dir, f"s{scene_index:03d}_whiteboard_sketch.jpg")
            wb_video = os.path.join(project_dir, f"s{scene_index:03d}_whiteboard.mp4")
            prompt = scene_description or narration or (qlist[0] if qlist else "sketch")
            if generate_whiteboard_sketch_image(prompt, sketch_img):
                if animate_whiteboard_clip(sketch_img, wb_video, duration=target_duration):
                    f_hash = _file_hash(wb_video)
                    add_manifest_entry({
                        "scene_index": scene_index,
                        "path": wb_video,
                        "uid": f"whiteboard:{scene_index}",
                        "source": "whiteboard",
                        "id": f"wb_{scene_index}",
                        "title": f"whiteboard sketch {prompt[:30]}",
                        "kind": "video",
                        "score": 85.0,
                        "sha1": f_hash,
                        "sha256": f_hash,
                        "license": LicenseInfo(License.CC0, "whiteboard", title="Whiteboard Sketch Animation").to_dict(),
                        "family": family_for_niche(niche_id),
                    })
                    print(f"    [OK] [visuals:whiteboard] scene={scene_index} duration={target_duration}s")
                    return wb_video
        except Exception as exc:
            print(f"    [visuals:whiteboard] {exc}")

    providers = ordered_providers(niche_id)
    if not providers:
        print("    [visuals] no providers available (keys missing?)")

    # 6.1 Parallel multi-provider search orchestration
    from concurrent.futures import ThreadPoolExecutor, as_completed

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
            spec.key,
            scene_index,
            qi_idx,
            (time.perf_counter() - started) * 1000,
            result_count,
            error,
        )
        return candidates, q, qi_idx

    scored: List[tuple] = []
    active_queries = qlist[:5]
    if providers and active_queries:
        with ThreadPoolExecutor(max_workers=min(8, max(1, len(providers) * len(active_queries)))) as executor:
            futures = [
                executor.submit(_search_spec, spec, query, qi)
                for qi, query in enumerate(active_queries)
                for spec in providers
            ]
            for f in as_completed(futures):
                cands, query, qi = f.result()
                for c in cands:
                    sc = score_candidate(c, query, narration=narration, target_duration=target_duration)
                    sc += max(0, 8 - qi * 2)
                    if sc > 0:
                        scored.append((sc, c, query))

    scored.sort(key=lambda x: x[0], reverse=True)
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
        if cand.kind == "video":
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
        norm = _normalize_clip(raw, out, target_duration, cand.kind)
        try:
            if os.path.isfile(raw) and raw != norm:
                os.remove(raw)
        except OSError:
            pass
        if not norm:
            continue

        # 6.4 SHA-256 fingerprint check. The lock claim happens after K1,
        # once the file that will actually be kept is known.
        f_hash = _file_hash(norm)

        # 6.5 K1-Semantic narrative relevance validation (< 8% triggers narrative re-fetch)
        if not _expanded and cand.topic_match_score < 0.08 and len(narration.strip().split()) >= 3:
            print(f"    [visuals:k1] Candidate score ({cand.topic_match_score:.2f}) < 0.08 threshold, triggering K1 re-fetch...")
            from .query_builder import build_shot_queries
            narrative_queries = build_shot_queries(
                narration=narration,
                scene_description=scene_description or narration,
                niche_id=niche_id,
                visual_intent=intent,
                max_queries=3,
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
                                if nc.kind == "video":
                                    from system_resilience import verify_stock_video_integrity
                                    n_integrity = verify_stock_video_integrity(n_raw, min_duration=0.5)
                                    if not n_integrity.get("valid", False):
                                        try:
                                            if os.path.isfile(n_raw):
                                                os.remove(n_raw)
                                        except OSError:
                                            pass
                                        continue
                                n_norm = _normalize_clip(n_raw, n_out, target_duration, nc.kind)
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
                                        norm = n_norm
                                        cand = nc
                                        query = nq
                                        sc = nsc
                                        f_hash = n_hash
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

    # 34.2 Public APIs zero-cost media fallback (Openverse / Met Museum Open Access)
    try:
        from services.public_apis_catalog import fetch_openverse_media, fetch_met_museum_artworks
        pub_cands = []
        for q in active_queries[:2]:
            pub_cands.extend(fetch_openverse_media(q, page_size=3))
            if not pub_cands:
                pub_cands.extend(fetch_met_museum_artworks(q, limit=2))
            if pub_cands:
                break
        for pc in pub_cands:
            p_url = pc.get("url")
            pc_id = str(pc.get("id", ""))
            if not p_url or asset_already_claimed(pc_id):
                continue
            raw_ext = ".jpg"
            raw = os.path.join(project_dir, f"s{scene_index:03d}_{pc.get('source', 'public')}_raw{raw_ext}")
            out = os.path.join(project_dir, f"s{scene_index:03d}_{pc.get('source', 'public')}_{scene_index}.mp4")
            if not _download(p_url, raw):
                continue
            norm = _normalize_clip(raw, out, target_duration, "image")
            try:
                if os.path.isfile(raw) and raw != norm:
                    os.remove(raw)
            except OSError:
                pass
            if not norm:
                continue
            f_hash = _file_hash(norm)
            if not claim_job_asset(f"public:{pc_id}", f_hash or ""):
                try:
                    os.remove(norm)
                except OSError:
                    pass
                continue
            add_manifest_entry({
                "scene_index": scene_index,
                "path": norm,
                "uid": f"public:{pc_id}",
                "source": pc.get("source", "public_api"),
                "id": pc_id,
                "url": p_url,
                "asset_url": p_url,
                "title": pc.get("title", ""),
                "query": active_queries[0] if active_queries else "",
                "kind": "image",
                "score": 75.0,
                "sha1": f_hash,
                "sha256": f_hash,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "source_url": p_url,
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "attribution": pc.get("creator") or pc.get("artist") or "Public Domain",
                "contributor": pc.get("creator") or pc.get("artist") or "Public Domain",
                "semantic_evidence": "public_apis_catalog openverse/met fallback",
                "topic_match_score": 0.75,
                "visual_verification_score": 1.0,
                "matched_terms": [active_queries[0]] if active_queries else [],
                "license": LicenseInfo(License.CC0, pc.get("source", "public_api"), title=pc.get("title", "")).to_dict(),
                "family": family_for_niche(niche_id),
            })
            print(f"    [OK] [visuals:public_apis] fallback acquired {pc.get('source')}: {pc.get('title')[:30]}")
            return norm
    except Exception as exc:
        print(f"    [visuals:public_apis_fallback] {exc}")

    # Broaden queries once before giving up; real footage beats any placeholder.
    if not _expanded:
        wide = [q for q in _broaden_queries(qlist, niche_id, narration) if q not in qlist]
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

    # 6.6 Kinetic procedural (intentional typography)
    try:
        from .motion_graphics import build_kinetic_clip
        path = os.path.join(project_dir, f"s{scene_index:03d}_kinetic_procedural.mp4")
        text = (caption_text or narration or scene_description or " ").strip()
        out = build_kinetic_clip(
            path,
            duration=target_duration,
            text=text,
            niche_id=niche_id,
            scene_index=scene_index,
        )
        if out:
            f_hash = _file_hash(out)
            add_manifest_entry({
                "scene_index": scene_index,
                "path": out,
                "uid": f"procedural:{scene_index}",
                "source": "procedural_kinetic",
                "id": f"kin_{scene_index}",
                "title": "procedural kinetic typography",
                "query": "",
                "kind": "procedural",
                "score": 0,
                "sha1": f_hash,
                "sha256": f_hash,
                "license": LicenseInfo(
                    License.CC0,
                    "procedural",
                    title="Original procedural motion graphic",
                    author="youtubeoto",
                    raw="original",
                ).to_dict(),
                "family": family_for_niche(niche_id),
            })
            print(f"    [OK] [visuals:kinetic] procedural typography scene={scene_index}")
            return out
    except Exception as exc:
        print(f"    [visuals:kinetic] {exc}")

    # 6.6 Procedural abstract cinematic background (FFmpeg lavfi)
    try:
        from render.procedural_visuals import build_procedural_clip, resolve_motif
        path = os.path.join(project_dir, f"s{scene_index:03d}_procedural_fallback.mp4")
        motif = resolve_motif(scene_description or narration, intent, niche_id=niche_id)
        out = build_procedural_clip(path, target_duration, scene_index=scene_index, motif=motif)
        if out:
            f_hash = _file_hash(out)
            add_manifest_entry({
                "scene_index": scene_index,
                "path": out,
                "uid": f"procedural_abs:{scene_index}",
                "source": "procedural_abstract",
                "id": f"abs_{scene_index}",
                "title": f"procedural {motif}",
                "kind": "procedural",
                "score": 0,
                "sha1": f_hash,
                "sha256": f_hash,
                "license": {"license": "cc0", "source": "procedural", "safe": True},
                "family": family_for_niche(niche_id),
            })
            return out
    except Exception as exc:
        print(f"    [visuals:abstract] {exc}")

    return None


def fetch_scene_clip(*args, **kwargs):
    from video_fetcher import fetch_scene_clip as _real_fetch
    return _real_fetch(*args, **kwargs)


def attach_short_clip_partners(
    clips,
    scenes,
    project_dir: str,
    *,
    niche_id: str = "",
    channel_id=None,
    cancel_check=None,
    fetch_fn=None,
) -> int:
    """
    saard00 process_scene always cuts a scene 50/50 across two files and then
    loops each half. That repeats a long clip and still loops a short one.
    Here a second file is fetched only when the first file is shorter than
    the scene. The graph concatenates them with concat=n=2. No stream_loop on the short file.
    """
    from render.ffmpeg_graph import _probe_duration
    if fetch_fn is None:
        try:
            import server_core.render_worker as rw
            fetch_fn = getattr(rw, "fetch_scene_clip", None)
        except Exception:
            fetch_fn = None
    if fetch_fn is None:
        from video_fetcher import fetch_scene_clip as fetch_fn

    attached = 0
    for i, clip in enumerate(clips or []):
        if cancel_check and cancel_check():
            break
        path = clip.get("path")
        if not path or not os.path.exists(path) or clip.get("tail_path"):
            continue
        need = float(clip.get("duration") or 0.0)
        have = _probe_duration(path)
        if have <= 0.2 or need - have <= 0.15:
            continue
        scene = scenes[i] if i < len(scenes or []) else {}
        intent = scene.get("visual_intent") or {}
        from visuals.subject_lock import queries_for_scene
        queries = queries_for_scene(
            narration=scene.get("narration") or "",
            scene_description=scene.get("scene_description") or "",
            subject=str(intent.get("subject") or "") if isinstance(intent, dict) else "",
            existing=(
                (intent.get("search_queries") if isinstance(intent, dict) else None)
                or scene.get("search_queries")
                or scene.get("search_query")
                or []
            ),
        )
        if not queries:
            continue
        tail = fetch_fn(
            queries,
            i + 100,
            project_dir,
            target_duration=max(1.0, need - have),
            scene_description=scene.get("scene_description") or "",
            narration=scene.get("narration") or "",
            visual_intent=intent if isinstance(intent, dict) else None,
            recent_texts=[os.path.basename(path).lower()],
            niche_id=niche_id or "",
            channel_id=channel_id,
            allow_procedural=False,
            cancel_check=cancel_check,
        )
        if not tail or os.path.abspath(tail) == os.path.abspath(path):
            continue
        if not os.path.exists(tail):
            continue
        clip["tail_path"] = tail
        clip["head_duration"] = have
        attached += 1
    return attached
