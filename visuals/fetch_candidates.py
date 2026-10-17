"""Candidate normalization, hook-window selection, fallback media, and clip partner helpers for visuals.fetch."""
from __future__ import annotations

import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import imageio_ffmpeg

from .license import License, LicenseInfo
from .palettes import family_for_niche

_K1_HARD_FLOOR = 0.03

_FAMILY_GENERIC = {
    "religious": ["mosque architecture", "prayer light", "ancient manuscript", "sunrise sky clouds"],
    "history": ["ancient ruins", "old map", "historic architecture"],
    "mystery": ["dark forest fog", "night sky", "abandoned building"],
    "nature": ["nature landscape", "ocean waves", "mountain sky"],
    "general": ["cinematic landscape", "city skyline", "sky clouds timelapse"],
}


def _vf_attr(name: str, default: Any) -> Any:
    mod = sys.modules.get("visuals.fetch")
    return getattr(mod, name, default) if mod is not None else default


def _procedural_enabled() -> bool:
    return os.getenv("ALLOW_PROCEDURAL_VISUALS", "").lower() in ("1", "true", "yes", "on")


def _broaden_queries(qlist: List[str], niche_id: str) -> List[str]:
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


def _normalize_clip(
    src: str,
    dst: str,
    duration: float,
    kind: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    start_sec: float = 0.0,
) -> Optional[str]:
    """Crop/scale to 9:16. Stills get a cheap crop-pan, not zoompan."""
    ffmpeg = _vf_attr("imageio_ffmpeg", imageio_ffmpeg).get_ffmpeg_exe()
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
        seek_start = float(start_sec)
        if not math.isfinite(seek_start) or seek_start < 0:
            seek_start = 0.0
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},format=yuv420p"
        )
        cmd = [ffmpeg, "-y", "-loglevel", "error"]
        if seek_start > 0:
            cmd.extend(["-ss", f"{seek_start:.3f}"])
        cmd.extend([
            "-i", src, "-t", f"{dur:.3f}", "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-an", dst,
        ])
    try:
        res = _vf_attr("subprocess", subprocess).run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    except Exception as exc:
        print(f"    [visuals:norm] {exc}")
        return None
    if res.returncode != 0 or not (os.path.isfile(dst) and os.path.getsize(dst) > 10_000):
        return None
    return dst


def _best_window_start_from_metrics(
    metrics: List[Dict[str, float]],
    target_duration: float,
    source_duration: float,
    *,
    sample_interval: float = 0.5,
    max_start_sec: float = 20.0,
) -> float:
    """Pick a sharp, properly exposed, steady window without changing its subject."""
    if (
        not math.isfinite(target_duration)
        or not math.isfinite(source_duration)
        or not math.isfinite(sample_interval)
        or target_duration <= 0
        or source_duration <= target_duration
        or sample_interval <= 0
    ):
        return 0.0

    frames_per_window = max(1, math.ceil(target_duration / sample_interval))
    last_index = min(
        len(metrics) - frames_per_window,
        int((min(max_start_sec, source_duration - target_duration) + 1e-9) / sample_interval),
    )
    if last_index < 1:
        return 0.0

    best_score = float("-inf")
    best_start = 0.0
    for index in range(last_index + 1):
        window = metrics[index:index + frames_per_window]
        try:
            sharpness = sum(float(row["sharpness"]) for row in window) / len(window)
            brightness = sum(float(row["brightness"]) for row in window) / len(window)
            motion = sum(float(row["motion"]) for row in window) / len(window)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
        if not all(math.isfinite(value) for value in (sharpness, brightness, motion)):
            continue

        exposure_penalty = max(0.0, 60.0 - brightness) * 0.8
        exposure_penalty += max(0.0, brightness - 210.0) * 0.8
        score = sharpness * 1.6 - motion * 1.1 - exposure_penalty
        if score > best_score:
            best_score = score
            best_start = float(metrics[index].get("time_sec", index * sample_interval))
    return round(best_start, 2) if math.isfinite(best_score) else 0.0


def _best_hook_window_start(
    video_path: str,
    target_duration: float,
    source_duration: float,
    *,
    max_start_sec: float = 20.0,
) -> float:
    """Analyze low-resolution frames in a bounded prefix of the opening shot."""
    from PIL import Image, ImageChops, ImageFilter, ImageStat

    sample_interval = 0.5
    scan_duration = min(source_duration, target_duration + max_start_sec)
    frame_limit = int(math.floor(scan_duration / sample_interval)) + 1
    frames_per_window = max(1, math.ceil(target_duration / sample_interval))
    if frame_limit < frames_per_window or scan_duration <= target_duration:
        return 0.0

    ffmpeg = _vf_attr("imageio_ffmpeg", imageio_ffmpeg).get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="shorts-hook-window-") as temp_dir:
        pattern = os.path.join(temp_dir, "frame_%03d.jpg")
        command = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_path,
            "-t", f"{scan_duration:.3f}",
            "-vf", f"fps={1.0 / sample_interval:.3f},scale=120:-2:flags=area,format=gray",
            "-frames:v", str(frame_limit),
            "-q:v", "3",
            pattern,
        ]
        try:
            result = _vf_attr("subprocess", subprocess).run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"    [visuals:hook-window] frame scan failed: {exc}")
            return 0.0
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace")[-300:]
            print(f"    [visuals:hook-window] frame scan failed: {detail}")
            return 0.0

        frame_names = sorted(
            name for name in os.listdir(temp_dir) if name.endswith(".jpg")
        )
        metrics: List[Dict[str, float]] = []
        previous = None
        for index, name in enumerate(frame_names):
            frame_path = os.path.join(temp_dir, name)
            try:
                with Image.open(frame_path) as image:
                    gray = image.convert("L")
                    sharpness = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).stddev[0]
                    brightness = ImageStat.Stat(gray).mean[0]
                    motion = (
                        ImageStat.Stat(ImageChops.difference(gray, previous)).mean[0]
                        if previous is not None
                        else 0.0
                    )
                    metrics.append({
                        "time_sec": index * sample_interval,
                        "sharpness": sharpness,
                        "brightness": brightness,
                        "motion": motion,
                    })
                    previous = gray.copy()
            except OSError as exc:
                print(f"    [visuals:hook-window] unreadable sample {name}: {exc}")

    best_fn = _vf_attr("_best_window_start_from_metrics", _best_window_start_from_metrics)
    return best_fn(
        metrics,
        target_duration,
        source_duration,
        sample_interval=sample_interval,
        max_start_sec=max_start_sec,
    )


def _normalize_candidate(
    src: str,
    dst: str,
    target_duration: float,
    candidate: Any,
    scene_index: int,
    *,
    optimize_hook: bool = True,
) -> Optional[str]:
    """Use the quality-selected source window for the opening stock shot only."""
    start_sec = 0.0
    source_duration = float(getattr(candidate, "duration", 0.0) or 0.0)
    hook_fn = _vf_attr("_best_hook_window_start", _best_hook_window_start)
    norm_fn = _vf_attr("_normalize_clip", _normalize_clip)
    if (
        optimize_hook
        and scene_index == 0
        and getattr(candidate, "kind", "") == "video"
        and math.isfinite(source_duration)
        and source_duration > target_duration + 1.0
    ):
        start_sec = hook_fn(src, target_duration, source_duration)
    if start_sec > 0:
        print(f"    [visuals:hook-window] opening shot starts at {start_sec:.2f}s")
        return norm_fn(src, dst, target_duration, candidate.kind, start_sec=start_sec)
    return norm_fn(src, dst, target_duration, candidate.kind)


def _try_whiteboard_visual(
    scene_index: int,
    project_dir: str,
    target_duration: float,
    narration: str,
    scene_description: str,
    niche_id: str,
    intent: dict,
    qlist: List[str],
) -> Optional[str]:
    if not (
        os.getenv("ALLOW_PROCEDURAL_VISUALS", "").lower() in ("1", "true", "yes", "on")
        and ((intent and intent.get("style") == "whiteboard") or "whiteboard" in (niche_id or "").lower())
    ):
        return None
    try:
        from services.whiteboard_animator import animate_whiteboard_clip, generate_whiteboard_sketch_image
        sketch_img = os.path.join(project_dir, f"s{scene_index:03d}_whiteboard_sketch.jpg")
        wb_video = os.path.join(project_dir, f"s{scene_index:03d}_whiteboard.mp4")
        prompt = scene_description or narration or (qlist[0] if qlist else "sketch")
        if generate_whiteboard_sketch_image(prompt, sketch_img):
            if animate_whiteboard_clip(sketch_img, wb_video, duration=target_duration):
                file_hash_fn = _vf_attr("_file_hash", None)
                add_manifest_fn = _vf_attr("add_manifest_entry", None)
                f_hash = file_hash_fn(wb_video) if file_hash_fn else ""
                if add_manifest_fn:
                    add_manifest_fn({
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
    return None


def _try_public_apis_fallback(
    active_queries: List[str],
    scene_index: int,
    project_dir: str,
    target_duration: float,
    niche_id: str,
) -> Optional[str]:
    try:
        from services.public_apis_catalog import fetch_met_museum_artworks, fetch_openverse_media
        pub_cands = []
        for q in active_queries[:2]:
            pub_cands.extend(fetch_openverse_media(q, page_size=3))
            if not pub_cands:
                pub_cands.extend(fetch_met_museum_artworks(q, limit=2))
            if pub_cands:
                break
        already_claimed_fn = _vf_attr("asset_already_claimed", lambda *_a, **_kw: False)
        dl_fn = _vf_attr("_download", None)
        norm_fn = _vf_attr("_normalize_clip", _normalize_clip)
        hash_fn = _vf_attr("_file_hash", None)
        claim_fn = _vf_attr("claim_job_asset", lambda *_a, **_kw: True)
        add_manifest_fn = _vf_attr("add_manifest_entry", None)
        for pc in pub_cands:
            p_url = pc.get("url")
            pc_id = str(pc.get("id", ""))
            if not p_url or already_claimed_fn(pc_id):
                continue
            raw = os.path.join(project_dir, f"s{scene_index:03d}_{pc.get('source', 'public')}_raw.jpg")
            out = os.path.join(project_dir, f"s{scene_index:03d}_{pc.get('source', 'public')}_{scene_index}.mp4")
            if not dl_fn or not dl_fn(p_url, raw):
                continue
            norm = norm_fn(raw, out, target_duration, "image")
            try:
                if os.path.isfile(raw) and raw != norm:
                    os.remove(raw)
            except OSError:
                pass
            if not norm:
                continue
            f_hash = hash_fn(norm) if hash_fn else ""
            if not claim_fn(f"public:{pc_id}", f_hash or ""):
                try:
                    os.remove(norm)
                except OSError:
                    pass
                continue
            if add_manifest_fn:
                add_manifest_fn({
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
    return None


def _try_procedural_fallbacks(
    scene_index: int,
    project_dir: str,
    target_duration: float,
    narration: str,
    scene_description: str,
    niche_id: str,
    intent: dict,
    caption_text: str,
) -> Optional[str]:
    hash_fn = _vf_attr("_file_hash", None)
    add_manifest_fn = _vf_attr("add_manifest_entry", None)
    try:
        from .motion_graphics import build_kinetic_clip
        path = os.path.join(project_dir, f"s{scene_index:03d}_kinetic_procedural.mp4")
        text = (caption_text or narration or scene_description or " ").strip()
        out = build_kinetic_clip(path, duration=target_duration, text=text, niche_id=niche_id, scene_index=scene_index)
        if out:
            f_hash = hash_fn(out) if hash_fn else ""
            if add_manifest_fn:
                add_manifest_fn({
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
                        License.CC0, "procedural", title="Original procedural motion graphic",
                        author="youtubeoto", raw="original",
                    ).to_dict(),
                    "family": family_for_niche(niche_id),
                })
            print(f"    [OK] [visuals:kinetic] procedural typography scene={scene_index}")
            return out
    except Exception as exc:
        print(f"    [visuals:kinetic] {exc}")

    try:
        from render.procedural_visuals import build_procedural_clip, resolve_motif
        path = os.path.join(project_dir, f"s{scene_index:03d}_procedural_fallback.mp4")
        motif = resolve_motif(scene_description or narration, intent, niche_id=niche_id)
        out = build_procedural_clip(path, target_duration, scene_index=scene_index, motif=motif)
        if out:
            f_hash = hash_fn(out) if hash_fn else ""
            if add_manifest_fn:
                add_manifest_fn({
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
    """Fetch a partner clip when the primary clip is shorter than the scene duration."""
    from render.ffmpeg_graph import _probe_duration
    if fetch_fn is None:
        try:
            import server_core.render_worker as rw
            fetch_fn = getattr(rw, "fetch_scene_clip", None)
        except Exception:
            fetch_fn = None
    if fetch_fn is None:
        fetch_fn = _vf_attr("fetch_scene_clip", fetch_scene_clip)

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
