"""Orchestrator: shot queries → multi-provider search → download → 9:16 normalize → license ledger."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import imageio_ffmpeg
import requests

from .license import License, LicenseInfo, attribution_line, is_commercial_safe
from .palettes import family_for_niche
from .providers import Candidate
from .query_builder import build_shot_queries
from .registry import mark_used, ordered_providers, reset_used, score_candidate, search_provider

USER_AGENT = "youtubeoto-shorts/1.0 (license-aware fetch)"
_job_manifest: List[Dict[str, Any]] = []


def reset_job_manifest() -> None:
    global _job_manifest
    _job_manifest = []
    reset_used()


def get_job_manifest() -> List[Dict[str, Any]]:
    return list(_job_manifest)


def write_job_credits(project_dir: str) -> Dict[str, str]:
    """Write the auditable source manifest and description-ready credits."""
    os.makedirs(project_dir, exist_ok=True)
    if not _job_manifest:
        raise ValueError("source manifest is empty")
    uids = [str(row.get("uid") or "") for row in _job_manifest]
    if any(not uid for uid in uids):
        raise ValueError("source manifest contains visual without uid")
    if len(uids) != len(set(uids)):
        raise ValueError("source manifest contains duplicate visual assets")
    for row in _job_manifest:
        license_data = row.get("license") or {}
        info = LicenseInfo.from_dict(license_data) if isinstance(license_data, dict) else None
        if not info or not is_commercial_safe(info.license):
            raise ValueError(f"source manifest contains unsafe license: {row.get('uid')}")
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
    try:
        with requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": USER_AGENT}) as r:
            r.raise_for_status()
            with open(path, "wb") as fh:
                for chunk in r.iter_content(256 * 1024):
                    if chunk:
                        fh.write(chunk)
        return os.path.isfile(path) and os.path.getsize(path) > 8_000
    except Exception as exc:
        print(f"    [visuals:dl] {exc}")
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
        return False


def _file_hash(path: str) -> str:
    h = hashlib.md5()
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
) -> Optional[str]:
    """
    Primary entry: license-safe multi-source fetch.
    Returns local mp4 path, procedural kinetic path, or a palette color card last.
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
    providers = ordered_providers(niche_id)
    if not providers:
        print("    [visuals] no providers available (keys missing?) → procedural")

    scored: List[tuple] = []
    for qi, query in enumerate(qlist[:5]):
        for spec in providers:
            try:
                cands = search_provider(spec, query, per_page=8)
            except Exception as exc:
                print(f"    [visuals:{spec.key}] {exc}")
                continue
            for c in cands:
                sc = score_candidate(c, query, narration=narration, target_duration=target_duration)
                # slight preference for earlier (more specific) queries
                sc += max(0, 8 - qi * 2)
                if sc > 0:
                    scored.append((sc, c, query))

    scored.sort(key=lambda x: x[0], reverse=True)
    for sc, cand, query in scored[:12]:
        if not cand.license or not is_commercial_safe(cand.license.license):
            continue
        raw_ext = ".jpg" if cand.kind == "image" else ".mp4"
        raw = os.path.join(project_dir, f"s{scene_index:03d}_{cand.source}_raw{raw_ext}")
        out = os.path.join(project_dir, f"s{scene_index:03d}_{cand.source}_{cand.id.split('_')[-1]}.mp4")
        if not _download(cand.url, raw):
            continue
        norm = _normalize_clip(raw, out, target_duration, cand.kind)
        try:
            if os.path.isfile(raw) and raw != norm:
                os.remove(raw)
        except OSError:
            pass
        if not norm:
            continue
        mark_used(cand.uid)
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
            "sha1": _file_hash(norm),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "source_url": (cand.source_url or (cand.license.source_url if cand.license else "")),
            "license_url": (cand.license_url or (cand.license.license_url if cand.license else "")),
            "attribution": (cand.attribution or (cand.license.attribution if cand.license else "")),
            "contributor": cand.contributor,
            "semantic_evidence": cand.semantic_evidence,
            "topic_match_score": cand.topic_match_score,
            "visual_verification_score": cand.visual_verification_score,
            "matched_terms": cand.matched_terms,
            "license": cand.license.to_dict(),
            "family": family_for_niche(niche_id),
        }
        _job_manifest.append(entry)
        print(f"    [OK] [visuals:{cand.source}] score={sc:.0f} lic={cand.license.license.value}")
        return norm

    if not allow_procedural:
        return None

    # Kinetic procedural (intentional typography — not FAILSAFE solid)
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
            _job_manifest.append({
                "scene_index": scene_index,
                "path": out,
                "uid": f"procedural:{scene_index}",
                "source": "procedural_kinetic",
                "id": f"kin_{scene_index}",
                "title": "procedural kinetic typography",
                "query": "",
                "kind": "procedural",
                "score": 0,
                "sha1": _file_hash(out),
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

    # Last resort: abstract cinematic (still no placeholder text). A plain
    # color card is deliberately not a publishable visual fallback.
    try:
        from render.procedural_visuals import build_procedural_clip, resolve_motif
        path = os.path.join(project_dir, f"s{scene_index:03d}_procedural_fallback.mp4")
        motif = resolve_motif(scene_description or narration, intent, niche_id=niche_id)
        out = build_procedural_clip(path, target_duration, scene_index=scene_index, motif=motif)
        if out:
            _job_manifest.append({
                "scene_index": scene_index,
                "path": out,
                "uid": f"procedural_abs:{scene_index}",
                "source": "procedural_abstract",
                "id": f"abs_{scene_index}",
                "title": f"procedural {motif}",
                "kind": "procedural",
                "license": {"license": "cc0", "source": "procedural", "safe": True},
                "family": family_for_niche(niche_id),
            })
            return out
    except Exception as exc:
        print(f"    [visuals:abstract] {exc}")
    # No "visual not found" cards: the caller must regenerate the shot or
    # stop the render when no subject-specific visual can be produced.
    return None
