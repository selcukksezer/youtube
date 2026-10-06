"""
POST /api/clipper. Long-video Shorts cuts. Narration render does not call this.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

import config
from services.highlight_clipper import cut_ranges_vertical, kept_timeline, select_highlights

router = APIRouter()


def _json_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _allowed_file(path: str) -> str:
    from services.path_security import validate_asset_path, UnsafePathError
    try:
        full = validate_asset_path(path)
    except UnsafePathError as err:
        raise HTTPException(status_code=400, detail=f"Video yolu proje klasörünün dışında: {err}")
    if not os.path.isfile(full):
        raise HTTPException(status_code=400, detail="Video dosyası yok.")
    return full


def _save_upload(upload) -> str:
    folder = os.path.join(config.OUTPUT_DIR, "clipper_uploads")
    os.makedirs(folder, exist_ok=True)
    name = os.path.basename(getattr(upload, "filename", "") or "upload.mp4")
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name) or "upload.mp4"
    dest = os.path.join(folder, f"{uuid.uuid4().hex[:8]}_{safe}")
    data = upload.file.read() if hasattr(upload, "file") else b""
    if not data:
        raise HTTPException(status_code=400, detail="Yüklenen video boş.")
    with open(dest, "wb") as handle:
        handle.write(data)
    return dest


async def _payload(request: Request) -> Dict[str, Any]:
    ctype = (request.headers.get("content-type") or "").lower()
    if "multipart/form-data" in ctype:
        form = await request.form()
        upload = form.get("file")
        source_path = str(form.get("source_path") or "")
        if upload is not None and getattr(upload, "filename", None):
            source_path = _save_upload(upload)
        return {
            "url": str(form.get("url") or ""),
            "source_path": source_path,
            "highlights": _json_list(form.get("highlights")),
            "words": _json_list(form.get("words")),
            "segments": _json_list(form.get("segments")),
            "deleted_ids": _json_list(form.get("deleted_ids")),
            "num_clips": form.get("num_clips") or 3,
            "start_ost": form.get("start_ost") or 0,
            "end_ost": form.get("end_ost") or 0,
            "duration": form.get("duration") or 0,
            "render": str(form.get("render") or "true").lower() not in ("0", "false", "no"),
        }
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    return body


def _resolve_source(payload: Dict[str, Any]) -> str:
    source = str(payload.get("source_path") or "").strip()
    url = str(payload.get("url") or "").strip()
    if source:
        return _allowed_file(source)
    if url.startswith("http://") or url.startswith("https://"):
        from services.youtube_clipper import youtube_clipper
        return _allowed_file(youtube_clipper.download_video(url))
    raise HTTPException(status_code=400, detail="Video dosyası veya http(s) URL gerekli.")


@router.post("/api/clipper")
async def api_clipper(request: Request):
    payload = await _payload(request)
    num_clips = int(payload.get("num_clips") or 3)
    start_ost = float(payload.get("start_ost") or 0)
    end_ost = float(payload.get("end_ost") or 0)
    duration = float(payload.get("duration") or 0)
    words = _json_list(payload.get("words"))
    highlights = _json_list(payload.get("highlights"))
    segments = _json_list(payload.get("segments"))
    deleted_ids = _json_list(payload.get("deleted_ids"))
    do_render = payload.get("render", True)
    if isinstance(do_render, str):
        do_render = do_render.lower() not in ("0", "false", "no")

    if not highlights and not deleted_ids:
        url = str(payload.get("url") or "").strip()
        if url:
            from services.youtube_clipper import youtube_clipper
            info = youtube_clipper.extract_youtube_info(url)
            subs = youtube_clipper.fetch_subtitles_or_transcribe(url, "")
            if not words:
                words = [
                    {"w": row.get("text") or "", "s": row.get("start"), "e": row.get("end")}
                    for row in subs
                ]
            if not segments:
                segments = [
                    {"id": str(i), "start": row.get("start"), "end": row.get("end"), "text": row.get("text") or ""}
                    for i, row in enumerate(subs)
                ]
            duration = duration or float(info.get("duration") or 0)
            transcript = " ".join(row.get("text") or "" for row in subs) or info.get("description") or ""
            highlights = youtube_clipper.detect_highlights_with_llm(
                transcript_text=transcript,
                num_clips=max(1, min(5, num_clips)),
                video_duration=duration or 300.0,
            )

    if deleted_ids and segments:
        ranges = kept_timeline(segments, deleted_ids)
        selected = [{"start_time": a, "end_time": b, "score": 0, "title": "Altyazı kesimi"} for a, b in ranges]
    else:
        ranges = None
        selected = select_highlights(
            highlights,
            duration=duration,
            words=words,
            num_clips=num_clips,
            start_ost_ms=start_ost,
            end_ost_ms=end_ost,
        )

    if not do_render:
        return {
            "status": "ok",
            "highlights": selected,
            "highlights_count": len(selected),
        }

    source = _resolve_source(payload)
    out_dir = os.path.join(config.OUTPUT_DIR, "shorts_clipped")
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(source))[0]
    outputs: List[Dict[str, Any]] = []
    if ranges:
        out_path = os.path.join(out_dir, f"{stem}_subs.mp4")
        cut_ranges_vertical(source, ranges, out_path)
        outputs.append({"path": out_path, "filename": os.path.basename(out_path), "ranges": ranges})
    else:
        if not selected:
            raise HTTPException(status_code=400, detail="Kesilecek vurgu yok.")
        for index, clip in enumerate(selected, start=1):
            out_path = os.path.join(out_dir, f"{stem}_short_{index:02d}.mp4")
            cut_ranges_vertical(
                source,
                [(float(clip["start_time"]), float(clip["end_time"]))],
                out_path,
            )
            outputs.append({
                "path": out_path,
                "filename": os.path.basename(out_path),
                "start_time": clip["start_time"],
                "end_time": clip["end_time"],
                "score": clip.get("score"),
            })
    return {"status": "ok", "clips": outputs, "highlights": selected}
