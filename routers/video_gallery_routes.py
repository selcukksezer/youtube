"""
Video gallery listing, thumbnail preview, share-decision, and file deletion routes.
Extracted from routers/video_router.py for modularity.
"""
import hashlib
import json
import os
import subprocess
import time
from typing import Any, Dict, Optional

import imageio_ffmpeg
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import config
import database
from api_models import ShareDecisionRequest
from services.path_security import UnsafePathError, validate_task_id

router = APIRouter(tags=["Video"])

_VERIFIED_VIDEO_PROBES: Dict[str, tuple] = {}
_MAX_PROBE_CACHE_ENTRIES = 500


def _gallery_thumbnail_cache_key(filename: str) -> str:
    """Keep legacy render filenames within the secure thumbnail-ID contract."""
    task_key = os.path.splitext(os.path.basename(filename or ""))[0]
    try:
        return validate_task_id(task_key)
    except UnsafePathError:
        return f"video_{hashlib.sha256(task_key.encode('utf-8')).hexdigest()[:32]}"


def _quality_gate_summary_for_filename(filename: str) -> Optional[Dict[str, Any]]:
    """P2-26: load post-render quality_gate.json summary for gallery cards."""
    base = os.path.splitext(os.path.basename(filename or ""))[0]
    if not base:
        return None
    qpath = os.path.join(config.ASSETS_DIR, base, "quality_gate.json")
    if not os.path.isfile(qpath):
        return None
    try:
        with open(qpath, "r", encoding="utf-8") as qf:
            qg = json.load(qf)
    except Exception:
        return None
    post = qg.get("post") or {}
    pre = qg.get("pre") or {}
    return {
        "ok": post.get("ok", True),
        "score": post.get("score"),
        "issues": post.get("issues") or [],
        "duration": post.get("video_duration"),
        "pre_ok": pre.get("ok"),
        "pre_score": pre.get("score"),
    }


@router.get("/api/videos")
def api_get_videos(limit: int = 50):
    import sys

    vr_mod = sys.modules.get("routers.video_router")
    ff_mod = getattr(vr_mod, "imageio_ffmpeg", imageio_ffmpeg)
    sp_mod = getattr(vr_mod, "subprocess", subprocess)
    qg_fn = getattr(vr_mod, "_quality_gate_summary_for_filename", _quality_gate_summary_for_filename)
    try:
        ffmpeg_exe = ff_mod.get_ffmpeg_exe()
        candidates = database.get_recent_videos(limit=max(1, min(limit, 200)) * 3)
        videos = []
        for video in candidates:
            if video.get("status") != "completed" or not video.get("filename"):
                continue
            safe_fname = os.path.basename(video["filename"])
            video_path = os.path.join(config.OUTPUT_DIR, safe_fname)
            try:
                st = os.stat(video_path)
            except OSError:
                continue
            if st.st_size < 100_000:
                continue
            sig = (st.st_size, getattr(st, "st_mtime_ns", int(st.st_mtime * 1000)))
            cached = _VERIFIED_VIDEO_PROBES.get(video_path)
            if cached and cached[0] == sig:
                is_valid = cached[1]
            else:
                probe = sp_mod.run(
                    [ffmpeg_exe, "-v", "error", "-t", "0.2", "-i", video_path, "-f", "null", "-"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    timeout=10,
                )
                is_valid = probe.returncode == 0
                if len(_VERIFIED_VIDEO_PROBES) >= _MAX_PROBE_CACHE_ENTRIES:
                    oldest_key = next(iter(_VERIFIED_VIDEO_PROBES))
                    _VERIFIED_VIDEO_PROBES.pop(oldest_key, None)
                _VERIFIED_VIDEO_PROBES[video_path] = (sig, is_valid)
            if not is_valid:
                continue
            video["size_mb"] = round(st.st_size / (1024 * 1024), 2)
            video.setdefault("url", f"/output/{safe_fname}")
            if not video.get("title"):
                video["title"] = video.get("keyword") or os.path.splitext(safe_fname)[0].replace("_", " ")
            qg = qg_fn(video["filename"])
            if qg:
                video["quality_gate"] = qg
            try:
                from services.gallery_cache import gallery_cache

                task_key = _gallery_thumbnail_cache_key(video["filename"])
                thumb_path = gallery_cache.ensure_thumb(task_key, video_path)
                if thumb_path:
                    video["thumbnail_url"] = gallery_cache.get_thumb_url(task_key)
            except Exception:
                pass
            videos.append(video)
            if len(videos) >= limit:
                break
        return {"status": "ok", "videos": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/videos/{task_id}/thumbnail")
def api_get_video_thumbnail(task_id: str):
    """Returns cached 480p preview thumbnail for completed video (Plan Section 28.1)."""
    from services.gallery_cache import gallery_cache

    try:
        safe_id = validate_task_id(task_id)
    except UnsafePathError:
        raise HTTPException(status_code=400, detail="Geçersiz görev kimliği.")

    thumb_path = gallery_cache.get_thumb_path(safe_id)
    if not thumb_path or not os.path.isfile(thumb_path):
        cand_video = os.path.join(config.OUTPUT_DIR, safe_id)
        if not os.path.isfile(cand_video):
            cand_video = os.path.join(config.OUTPUT_DIR, f"{safe_id}.mp4")
        if os.path.isfile(cand_video):
            thumb_path = gallery_cache.ensure_thumb(safe_id, cand_video)

    if not thumb_path or not os.path.isfile(thumb_path):
        raise HTTPException(status_code=404, detail="Önizleme resmi bulunamadı.")
    return FileResponse(
        thumb_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/api/gallery")
def get_gallery():
    if not os.path.exists(config.OUTPUT_DIR):
        return {"status": "ok", "videos": []}

    file_entries = []
    for f in os.listdir(config.OUTPUT_DIR):
        if not f.lower().endswith(".mp4") or f.lower().endswith("_tmp.mp4"):
            continue
        fp = os.path.join(config.OUTPUT_DIR, f)
        try:
            st = os.stat(fp)
            file_entries.append((st.st_mtime, st.st_size, f))
        except OSError:
            continue

    file_entries.sort(key=lambda item: item[0], reverse=True)
    videos = [
        {
            "filename": f,
            "title": f.rsplit(".", 1)[0].replace("_", " "),
            "url": f"/output/{f}",
            "size_mb": round(size_b / (1024 * 1024), 2),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
        }
        for mtime, size_b, f in file_entries
    ]
    return {"status": "ok", "videos": videos}


@router.post("/api/videos/{video_id}/share-decision")
def video_share_decision(video_id: int, req: ShareDecisionRequest):
    """
    Post-render manual upload flow (Item 133 / 471).
    keep    -> proof + SEO + assets preserved for YouTube dispute/manual upload
    discard -> delete video, proof bundle, project assets, audio temps
    """
    from proof_archiver import proof_archiver

    video = database.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video kaydı bulunamadı.")

    decision = (req.decision or "").strip().lower()
    if decision not in ("keep", "discard"):
        raise HTTPException(status_code=400, detail="decision 'keep' veya 'discard' olmalı.")

    filename = video.get("filename") or ""
    channel_slug = video.get("channel_slug") or "default"
    project_slug = req.project_slug or (os.path.splitext(filename)[0] if filename else None)

    if decision == "keep":
        if filename:
            proof_archiver.mark_share_kept(filename)
        database.update_share_decision(video_id, "keep")
        return {
            "status": "ok",
            "decision": "keep",
            "message": "Proof ve SEO paketi saklandı. YouTube'a manuel yükleyebilirsiniz.",
            "youtube_upload_url": "https://www.youtube.com/upload",
        }

    if not filename:
        database.update_share_decision(video_id, "discarded")
        database.delete_video_by_id(video_id)
        return {
            "status": "ok",
            "decision": "discard",
            "message": "Kayıt silindi (dosya yoktu).",
            "deleted": [],
        }

    result = proof_archiver.discard_video_bundle(
        filename,
        channel_slug=channel_slug,
        project_slug=project_slug,
    )
    database.update_share_decision(video_id, "discarded")
    database.delete_video_by_id(video_id)

    return {
        "status": "ok",
        "decision": "discard",
        "message": "Video ve ilişkili dosyalar silindi.",
        "deleted_count": len(result.get("deleted") or []),
        "errors": result.get("errors") or [],
    }


@router.delete("/api/gallery/{filename}")
def delete_video(filename: str):
    safe_filename = os.path.basename(filename)
    fp = os.path.realpath(os.path.join(config.OUTPUT_DIR, safe_filename))
    out_dir_real = os.path.realpath(config.OUTPUT_DIR)

    if not fp.startswith(out_dir_real) or not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")

    try:
        os.remove(fp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya silinemedi: {str(e)}")

    base_no_ext = fp.rsplit(".", 1)[0]
    for sub_ext in [".ass", ".srt"]:
        sub_path = base_no_ext + sub_ext
        if os.path.exists(sub_path):
            try:
                os.remove(sub_path)
            except Exception:
                pass

    database.delete_video_by_filename(safe_filename)

    return {"status": "ok", "message": "Video ve ilişkili dosyalar başarıyla silindi."}


@router.get("/api/database/videos")
def get_database_videos():
    videos = database.get_recent_videos(100)
    stats = database.get_video_stats()
    return {"status": "ok", "videos": videos, "stats": stats}
