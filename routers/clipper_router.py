"""
POST /api/clipper. Long-video Shorts cuts. Narration render does not call this.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request

import config
from services.clip_subtitles import build_clip_srt, build_full_srt
from services.highlight_clipper import (
    cut_ranges_vertical,
    detect_speaker_split_centers,
    kept_timeline,
    select_highlights,
)

router = APIRouter()
MIN_RECOMMENDED_SOURCE_HEIGHT = 720


def _attach_clip_downloads(
    output: Dict[str, Any],
    output_path: str,
    segments: List[Any],
    words: List[Any],
    source_ranges: List[Any],
) -> None:
    output_filename = os.path.basename(output_path)
    output["video_url"] = (
        f"/output/shorts_clipped/{quote(output_filename, safe='')}"
    )

    subtitle_text = build_clip_srt(segments, source_ranges)
    if not subtitle_text and words:
        subtitle_text = build_clip_srt(words, source_ranges)
    if not subtitle_text:
        return

    subtitle_path = os.path.splitext(output_path)[0] + ".srt"
    with open(subtitle_path, "w", encoding="utf-8", newline="\n") as subtitle_file:
        subtitle_file.write(subtitle_text)
    subtitle_filename = os.path.basename(subtitle_path)
    output["subtitle_url"] = (
        f"/output/shorts_clipped/{quote(subtitle_filename, safe='')}"
    )


def _attach_source_transcript_download(
    output_path: str,
    segments: List[Any],
    words: List[Any],
) -> str:
    subtitle_text = build_full_srt(segments)
    if not subtitle_text and words:
        subtitle_text = build_full_srt(words)
    if not subtitle_text:
        return ""

    subtitle_path = os.path.splitext(output_path)[0] + "_full_transcript.srt"
    with open(subtitle_path, "w", encoding="utf-8", newline="\n") as subtitle_file:
        subtitle_file.write(subtitle_text)
    return f"/output/shorts_clipped/{quote(os.path.basename(subtitle_path), safe='')}"


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
            "analysis_mode": form.get("analysis_mode") or "transcript",
            "external_analysis_consent": form.get("external_analysis_consent") or False,
            "hotwords": form.get("hotwords") or "",
            "force_low_quality": form.get("force_low_quality") or False,
            "speaker_split": form.get("speaker_split") or False,
            "speaker_activity_layout": form.get("speaker_activity_layout") or False,
            "narration_theme": form.get("narration_theme") or "",
            "visual_analysis_consent": form.get("visual_analysis_consent") or False,
            "compile_clips": form.get("compile_clips") or False,
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


def _speaker_layout(
    source: str,
    ranges: List[Any],
    *,
    speaker_split: bool,
    active_speaker_layout: bool,
) -> Dict[str, Any]:
    if not speaker_split and not active_speaker_layout:
        return {
            "centers": None,
            "crop_center_x": None,
            "layout": "vertical_crop",
            "reason": None,
        }

    centers = detect_speaker_split_centers(source, ranges)
    if centers is None:
        return {
            "centers": None,
            "crop_center_x": None,
            "layout": "vertical_crop",
            "reason": (
                "İki ayrı yüz seçilen aralıklarda güvenilir biçimde algılanamadı; "
                "standart dikey kadraj kullanıldı."
            ),
        }
    if not active_speaker_layout:
        return {
            "centers": centers,
            "crop_center_x": None,
            "layout": "split_stack",
            "reason": None,
        }

    from services.speaker_activity import (
        SpeakerActivityUnavailable,
        analyze_speaker_activity,
    )

    try:
        activity = analyze_speaker_activity(source, ranges, centers)
    except SpeakerActivityUnavailable as err:
        print(f"[Clipper] Etkin konuşmacı analizi kullanılamadı: {err}")
        return {
            "centers": None,
            "crop_center_x": None,
            "layout": "vertical_crop",
            "reason": (
                f"Etkin konuşmacı analizi tamamlanamadı ({type(err).__name__}); "
                "standart dikey kadraj kullanıldı."
            ),
        }

    if activity.is_conversation:
        return {
            "centers": centers,
            "crop_center_x": None,
            "layout": "split_stack",
            "reason": None,
        }
    if activity.dominant_speaker is not None:
        share = activity.speaker_shares[activity.dominant_speaker]
        return {
            "centers": None,
            "crop_center_x": centers[activity.dominant_speaker][0],
            "layout": "vertical_crop",
            "reason": (
                f"Yerel analiz etkinlik pencerelerinin %{share * 100:.0f} kadarını "
                "bu konuşmacıya atfetti; kadraj bu yüze alındı."
            ),
        }
    return {
        "centers": None,
        "crop_center_x": None,
        "layout": "vertical_crop",
        "reason": (
            "Yerel analiz etkin konuşmacıyı güvenilir biçimde ayıramadı; "
            "standart dikey kadraj kullanıldı."
        ),
    }


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
    raw_force_low_quality = payload.get("force_low_quality", False)
    force_low_quality = raw_force_low_quality is True or (
        isinstance(raw_force_low_quality, str)
        and raw_force_low_quality.strip().lower() in ("1", "true", "yes")
    )
    raw_speaker_split = payload.get("speaker_split", False)
    speaker_split = raw_speaker_split is True or (
        isinstance(raw_speaker_split, str)
        and raw_speaker_split.strip().lower() in ("1", "true", "yes")
    )
    raw_active_speaker_layout = payload.get("speaker_activity_layout", False)
    active_speaker_layout = raw_active_speaker_layout is True or (
        isinstance(raw_active_speaker_layout, str)
        and raw_active_speaker_layout.strip().lower() in ("1", "true", "yes")
    )
    raw_compile_clips = payload.get("compile_clips", False)
    compile_clips = raw_compile_clips is True or (
        isinstance(raw_compile_clips, str)
        and raw_compile_clips.strip().lower() in ("1", "true", "yes")
    )

    if not highlights and not deleted_ids:
        url = str(payload.get("url") or "").strip()
        try:
            from services.multimodal_clipper import (
                MultimodalConfigurationError,
                analyze_video_highlights,
                multimodal_analysis_requested,
            )
            use_multimodal = multimodal_analysis_requested(payload)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err

        if use_multimodal and not url:
            raise HTTPException(
                status_code=400,
                detail="TwelveLabs analizi için HTTP(S) video URL gerekli.",
            )
        if use_multimodal and not url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail="TwelveLabs analizi için HTTP(S) video URL gerekli.",
            )
        local_video_path = ""
        if url:
            from services.youtube_clipper import youtube_clipper
            info = youtube_clipper.extract_youtube_info(url)
            duration = duration or float(info.get("duration") or 0)
            try:
                max_height = int(info.get("max_height") or 0)
            except (TypeError, ValueError):
                max_height = 0
            if (
                not force_low_quality
                and 0 < max_height < MIN_RECOMMENDED_SOURCE_HEIGHT
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "source_quality_confirmation_required",
                        "message": (
                            f"Kaynak yalnızca {max_height}p çözünürlükte mevcut. "
                            f"{MIN_RECOMMENDED_SOURCE_HEIGHT}p altı görüntüler "
                            "dikey Shorts çıktısında daha bulanık olabilir. "
                            "Yine de analiz edilsin mi?"
                        ),
                        "max_height": max_height,
                        "minimum_height": MIN_RECOMMENDED_SOURCE_HEIGHT,
                    },
                )
        elif str(payload.get("source_path") or "").strip():
            local_video_path = _resolve_source(payload)
            from render.pipeline_audit import _ffprobe_duration
            duration = _ffprobe_duration(local_video_path)
            if duration <= 0:
                raise HTTPException(
                    status_code=422,
                    detail="Yüklenen videonun süresi okunamadı; geçerli bir video dosyası seçin.",
                )

        if url or local_video_path:
            from services.youtube_clipper import youtube_clipper
            if use_multimodal:
                try:
                    highlights = analyze_video_highlights(
                        url,
                        video_duration=duration,
                        num_clips=num_clips,
                    )
                except MultimodalConfigurationError as err:
                    raise HTTPException(status_code=503, detail=str(err)) from err
                except ValueError as err:
                    raise HTTPException(status_code=400, detail=str(err)) from err
                except Exception as err:
                    raise HTTPException(
                        status_code=502,
                        detail=f"TwelveLabs video analizi başarısız: {err}",
                    ) from err
                if not highlights:
                    raise HTTPException(
                        status_code=502,
                        detail="TwelveLabs geçerli klip önerisi döndürmedi.",
                    )
            else:
                from services.youtube_clipper import normalize_transcription_hotwords
                try:
                    hotwords = normalize_transcription_hotwords(payload.get("hotwords", ""))
                except ValueError as err:
                    raise HTTPException(status_code=400, detail=str(err)) from err
                try:
                    subs = youtube_clipper.fetch_subtitles_or_transcribe(
                        url,
                        local_video_path,
                        hotwords=hotwords,
                    )
                except RuntimeError as err:
                    raise HTTPException(status_code=502, detail=f"Video transkripsiyonu başarısız: {err}") from err
                transcript = youtube_clipper.format_transcript_segments(subs)
                if not transcript:
                    raise HTTPException(
                        status_code=422,
                        detail="Videoda klip zamanlarını belirlemek için kullanılabilir zaman damgalı altyazı bulunamadı.",
                    )
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
                try:
                    highlights = youtube_clipper.detect_highlights_with_llm(
                        transcript_text=transcript,
                        num_clips=max(1, min(5, num_clips)),
                        video_duration=duration or 300.0,
                    )
                    highlights = youtube_clipper.ground_highlights_in_transcript(
                        highlights,
                        subs,
                    )
                except RuntimeError as err:
                    raise HTTPException(status_code=502, detail=f"AI klip analizi başarısız: {err}") from err

    subtitle_edit = bool(deleted_ids and segments)
    if subtitle_edit:
        ranges = kept_timeline(segments, deleted_ids)
        selected = [{"start_time": a, "end_time": b, "score": 0, "title": "Altyazı kesimi"} for a, b in ranges]
    else:
        selected = select_highlights(
            highlights,
            duration=duration,
            words=words,
            num_clips=num_clips,
            start_ost_ms=start_ost,
            end_ost_ms=end_ost,
        )
        ranges = (
            [
                (float(clip["start_time"]), float(clip["end_time"]))
                for clip in selected
            ]
            if compile_clips
            else None
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
        suffix = "_subs" if subtitle_edit else "_compilation"
        out_path = os.path.join(out_dir, f"{stem}{suffix}.mp4")
        layout = _speaker_layout(
            source,
            ranges,
            speaker_split=speaker_split,
            active_speaker_layout=active_speaker_layout,
        )
        cut_ranges_vertical(
            source,
            ranges,
            out_path,
            speaker_split_centers=layout["centers"],
            crop_center_x=layout["crop_center_x"],
        )
        output = {
            "path": out_path,
            "filename": os.path.basename(out_path),
            "ranges": ranges,
            "speaker_layout": layout["layout"],
        }
        if not subtitle_edit:
            output["compiled"] = True
            output["source_highlights"] = selected
        if layout["reason"]:
            output["speaker_layout_reason"] = layout["reason"]
        _attach_clip_downloads(output, out_path, segments, words, ranges)
        outputs.append(output)
    else:
        if not selected:
            raise HTTPException(status_code=400, detail="Kesilecek vurgu yok.")
        for index, clip in enumerate(selected, start=1):
            out_path = os.path.join(out_dir, f"{stem}_short_{index:02d}.mp4")
            clip_range = [
                (float(clip["start_time"]), float(clip["end_time"]))
            ]
            layout = _speaker_layout(
                source,
                clip_range,
                speaker_split=speaker_split,
                active_speaker_layout=active_speaker_layout,
            )
            cut_ranges_vertical(
                source,
                clip_range,
                out_path,
                speaker_split_centers=layout["centers"],
                crop_center_x=layout["crop_center_x"],
            )
            output = {
                "path": out_path,
                "filename": os.path.basename(out_path),
                "start_time": clip["start_time"],
                "end_time": clip["end_time"],
                "score": clip.get("score"),
                "speaker_layout": layout["layout"],
            }
            if layout["reason"]:
                output["speaker_layout_reason"] = layout["reason"]
            _attach_clip_downloads(output, out_path, segments, words, clip_range)
            outputs.append(output)
    source_subtitle_url = _attach_source_transcript_download(
        outputs[0]["path"],
        segments,
        words,
    )
    return {
        "status": "ok",
        "clips": outputs,
        "highlights": selected,
        "source_subtitle_url": source_subtitle_url or None,
    }


@router.post("/api/clipper/narration")
async def api_clipper_narration(request: Request):
    """Generate a Turkish narration draft from user-approved sampled video frames."""
    payload = await _payload(request)
    consent = payload.get("visual_analysis_consent")
    if consent is not True and str(consent or "").strip().lower() not in {
        "1", "true", "yes", "on",
    }:
        raise HTTPException(
            status_code=400,
            detail="Görsel anlatım için örnek karelerin Gemini'a gönderilmesine açık onay gerekli.",
        )

    theme = str(payload.get("narration_theme") or "").strip()
    if len(theme) > 240:
        raise HTTPException(
            status_code=400,
            detail="Anlatım odağı en fazla 240 karakter olabilir.",
        )

    source = _resolve_source(payload)
    from services.documentary_narration import (
        DocumentaryNarrationError,
        DocumentaryNarrationUnavailable,
        generate_documentary_narration,
    )

    try:
        result = generate_documentary_narration(source, theme=theme)
    except DocumentaryNarrationUnavailable as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    except DocumentaryNarrationError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    return {"status": "ok", **result}


@router.post("/api/clipper/teardown")
async def api_clipper_teardown(request: Request):
    """Analyze reference edit cadence locally; never sends video to an AI provider."""
    payload = await _payload(request)
    try:
        source = _resolve_source(payload)
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=502,
            detail=f"Video kaynağı alınamadı: {err}",
        ) from err

    from services.video_teardown import VideoTeardownError, analyze_reference_video

    try:
        report = analyze_reference_video(source)
    except VideoTeardownError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    return {"status": "ok", "analysis": report}
