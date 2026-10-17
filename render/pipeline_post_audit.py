"""
Post-render quality gates, visual frame contact-sheet sampler, FFmpeg signal report,
and search query auditor for `render/pipeline_audit.py`.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional


def _pa():
    return sys.modules.get("render.pipeline_audit")


def _pa_attr(name: str, default: Any) -> Any:
    pa = _pa()
    return getattr(pa, name, default) if pa is not None else default


def _ffprobe_duration(path: str) -> float:
    """Probe video duration using ffmpeg (ffprobe not bundled with imageio_ffmpeg)."""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subp = _pa_attr("subprocess", subprocess)
        r = subp.run(
            [ffmpeg, "-i", path, "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        )
        stderr = r.stderr.decode("utf-8", errors="ignore") if r.stderr else ""
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", stderr)
        if m:
            h, mn, s, cs = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            return h * 3600 + mn * 60 + s + cs / (10 ** len(m.group(4)))
        return -1.0
    except Exception:
        return -1.0


def _ffprobe_streams(path: str) -> List[Dict[str, str]]:
    """Probe stream info using ffmpeg -i (ffprobe not bundled with imageio_ffmpeg)."""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subp = _pa_attr("subprocess", subprocess)
        r = subp.run(
            [ffmpeg, "-i", path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
        )
        stderr = r.stderr.decode("utf-8", errors="ignore") if r.stderr else ""
        streams = []
        for line in stderr.split("\n"):
            if "Stream #" not in line:
                continue
            if ": Video:" in line:
                codec_m = re.search(r"Video:\s*(\w+)", line)
                res_m = re.search(r",\s*(\d{3,4})x(\d{3,4})", line)
                pix_m = re.search(r"(yuv\w+)", line)
                entry = {"codec_type": "video", "codec_name": codec_m.group(1) if codec_m else "unknown"}
                if res_m:
                    entry["resolution"] = f"{res_m.group(1)}x{res_m.group(2)}"
                    entry["width"] = res_m.group(1)
                    entry["height"] = res_m.group(2)
                entry["pix_fmt"] = pix_m.group(1) if pix_m else "unknown"
                fps_m = re.search(r",\s*(\d+(?:\.\d+)?)\s*fps\b", line)
                if fps_m:
                    entry["fps"] = fps_m.group(1)
                streams.append(entry)
            elif ": Audio:" in line:
                codec_m = re.search(r"Audio:\s*(\w+)", line)
                streams.append({"codec_type": "audio", "codec_name": codec_m.group(1) if codec_m else "unknown"})
        return streams
    except Exception:
        return []


def _ffmpeg_signal_report(path: str, has_video: bool, has_audio: bool) -> Dict[str, Any]:
    """Measure black frames, long silence, and audio peak in a single decode."""
    report: Dict[str, Any] = {
        "available": False,
        "black_intervals": [],
        "silence_intervals": [],
        "peak_volume_dbfs": None,
    }
    filters: List[str] = []
    maps: List[str] = []
    if has_video:
        filters.append("[0:v:0]blackdetect=d=0.5:pix_th=0.10[black]")
        maps.extend(["-map", "[black]"])
    if has_audio:
        filters.append("[0:a:0]silencedetect=noise=-50dB:d=1.5,volumedetect[audio]")
        maps.extend(["-map", "[audio]"])
    if not filters:
        report["error"] = "no_streams_to_analyze"
        return report

    subp = _pa_attr("subprocess", subprocess)
    try:
        import imageio_ffmpeg

        result = subp.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-hide_banner",
                "-nostats",
                "-i",
                path,
                "-filter_complex",
                ";".join(filters),
                *maps,
                "-f",
                "null",
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        return report

    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    if result.returncode != 0:
        report["error"] = stderr[-1000:] or f"ffmpeg_exit_{result.returncode}"
        return report

    report["available"] = True
    report["black_intervals"] = [
        {
            "start": round(float(match.group(1)), 3),
            "end": round(float(match.group(2)), 3),
            "duration": round(float(match.group(3)), 3),
        }
        for match in re.finditer(
            r"black_start:\s*([-\d.]+)\s+black_end:\s*([-\d.]+)\s+black_duration:\s*([-\d.]+)",
            stderr,
        )
    ]

    silence_start: Optional[float] = None
    for match in re.finditer(r"silence_(start|end):\s*([-\d.]+)", stderr):
        event, raw_time = match.groups()
        timestamp = float(raw_time)
        if event == "start":
            silence_start = timestamp
        elif silence_start is not None and timestamp >= silence_start:
            report["silence_intervals"].append({
                "start": round(silence_start, 3),
                "end": round(timestamp, 3),
                "duration": round(timestamp - silence_start, 3),
            })
            silence_start = None

    peak_match = re.search(r"max_volume:\s*(-?inf|[-\d.]+)\s*dB", stderr, re.IGNORECASE)
    if peak_match and peak_match.group(1).lower() != "-inf":
        report["peak_volume_dbfs"] = round(float(peak_match.group(1)), 2)
    return report


def audit_visual_frames(
    clips: List[Dict[str, Any]],
    contact_sheet_path: str,
) -> Dict[str, Any]:
    """Sample local frames for appearance defects; this does not verify semantics."""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageStat
    except ImportError as exc:
        return {
            "available": False,
            "evidence_scope": "technical appearance only; semantic content not verified",
            "scenes": [],
            "warnings": [f"visual_frame_analysis_unavailable:{type(exc).__name__}"],
            "error": str(exc),
        }

    os_mod = _pa_attr("os", os)
    subp = _pa_attr("subprocess", subprocess)
    samples: List[Dict[str, Any]] = []
    warning_by_scene: List[str] = []
    contact_images: List[Any] = []
    for index, clip in enumerate(clips):
        path = str((clip or {}).get("path") or "")
        if not path or not os_mod.path.isfile(path):
            warning_by_scene.append(f"visual_frame_unavailable:scene_{index + 1}:clip_missing")
            samples.append({"scene": index + 1, "available": False, "error": "clip_missing"})
            contact_images.append(None)
            continue

        try:
            if os_mod.path.splitext(path)[1].lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                with Image.open(path) as source:
                    frame = source.convert("RGB")
            else:
                duration = max(0.0, float((clip or {}).get("duration") or 0.0))
                seek = max(0.0, duration / 2.0)
                import imageio_ffmpeg
                ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
                completed = subp.run(
                    [
                        ffmpeg, "-v", "error", "-ss", f"{seek:.3f}", "-i", path,
                        "-frames:v", "1", "-vf", "scale=240:320:force_original_aspect_ratio=decrease",
                        "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=20,
                )
                if completed.returncode != 0 or not completed.stdout:
                    detail = completed.stderr.decode("utf-8", errors="replace")[:160]
                    raise RuntimeError(f"frame extraction failed: {detail}")
                from io import BytesIO
                with Image.open(BytesIO(completed.stdout)) as source:
                    frame = source.convert("RGB")

            frame.thumbnail((240, 320))
            grayscale = frame.convert("L").resize((9, 8))
            pixels = list(grayscale.tobytes())
            difference_hash = 0
            for y in range(8):
                for x in range(8):
                    difference_hash = (difference_hash << 1) | int(
                        pixels[y * 9 + x] > pixels[y * 9 + x + 1]
                    )
            histogram = grayscale.histogram()
            total_pixels = max(1, sum(histogram))
            dark_ratio = sum(histogram[:6]) / total_pixels
            mean_luma = round(float(ImageStat.Stat(grayscale).mean[0]), 1)
            provider_score = (clip or {}).get("candidate_topic_match_score")
            item = {
                "scene": index + 1,
                "available": True,
                "sample_second": round(max(0.0, float((clip or {}).get("duration") or 0.0) / 2.0), 2),
                "mean_luma": mean_luma,
                "near_black_ratio": round(dark_ratio, 3),
                "metadata_score": (
                    round(float(provider_score), 3)
                    if isinstance(provider_score, (int, float)) and not isinstance(provider_score, bool)
                    else None
                ),
                "candidate": (clip or {}).get("candidate_title") or None,
                "source": (clip or {}).get("candidate_source") or None,
                "matched_terms": (clip or {}).get("candidate_matched_terms") or [],
                "difference_hash": f"{difference_hash:016x}",
            }
            if mean_luma < 12.0 or dark_ratio >= 0.98:
                warning_by_scene.append(f"visual_frame_near_black:scene_{index + 1}")
            samples.append(item)
            contact_images.append(frame.copy())
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            error = f"{type(exc).__name__}:{str(exc)[:160]}"
            samples.append({"scene": index + 1, "available": False, "error": error})
            contact_images.append(None)
            warning_by_scene.append(f"visual_frame_unavailable:scene_{index + 1}:{type(exc).__name__}")

    duplicate_pairs = []
    for left in range(len(samples)):
        left_hash = samples[left].get("difference_hash")
        if not left_hash:
            continue
        for right in range(left + 1, len(samples)):
            right_hash = samples[right].get("difference_hash")
            if not right_hash:
                continue
            distance = bin(int(left_hash, 16) ^ int(right_hash, 16)).count("1")
            if distance <= 4:
                duplicate_pairs.append({
                    "scenes": [left + 1, right + 1],
                    "difference_bits": distance,
                })
    if duplicate_pairs:
        warning_by_scene.append(
            "visual_frames_near_duplicate:"
            + ",".join(f"{row['scenes'][0]}-{row['scenes'][1]}" for row in duplicate_pairs)
        )

    contact_sheet_written = False
    sheet_error = None
    if contact_sheet_path:
        try:
            columns = 3
            cell_width, cell_height = 280, 370
            rows = max(1, (len(samples) + columns - 1) // columns)
            sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), (24, 28, 36))
            draw = ImageDraw.Draw(sheet)
            font = ImageFont.load_default()
            for index, sample in enumerate(samples):
                x = (index % columns) * cell_width
                y = (index // columns) * cell_height
                draw.text((x + 10, y + 8), f"SCENE {index + 1}", fill=(255, 255, 255), font=font)
                frame = contact_images[index]
                if frame is not None:
                    frame.thumbnail((250, 310))
                    sheet.paste(frame, (x + (cell_width - frame.width) // 2, y + 30))
                else:
                    draw.rectangle(
                        [x + 15, y + 32, x + cell_width - 15, y + 320],
                        fill=(56, 62, 72),
                    )
                    draw.text((x + 25, y + 165), "FRAME UNAVAILABLE", fill=(255, 220, 170), font=font)
                candidate = str(sample.get("candidate") or sample.get("source") or "metadata unavailable")
                candidate = candidate.encode("ascii", errors="ignore").decode("ascii")[:34]
                metadata_score = sample.get("metadata_score")
                metadata_label = f"{metadata_score:.2f}" if isinstance(metadata_score, (int, float)) else "-"
                details = (
                    f"Luma {sample.get('mean_luma', '-')} | "
                    f"metadata {metadata_label} | {candidate}"
                )
                draw.text((x + 10, y + 345), details[:50], fill=(220, 225, 235), font=font)
            os_mod.makedirs(os_mod.path.dirname(os_mod.path.abspath(contact_sheet_path)), exist_ok=True)
            sheet.save(contact_sheet_path, "JPEG", quality=84)
            contact_sheet_written = True
        except (OSError, ValueError) as exc:
            sheet_error = f"{type(exc).__name__}:{str(exc)[:160]}"
            warning_by_scene.append(f"visual_contact_sheet_failed:{type(exc).__name__}")

    return {
        "available": any(item.get("available") for item in samples),
        "evidence_scope": "technical appearance and provider metadata only; semantic content not verified",
        "sampled_scene_count": sum(bool(item.get("available")) for item in samples),
        "scene_count": len(samples),
        "scenes": samples,
        "near_duplicate_pairs": duplicate_pairs,
        "contact_sheet_written": contact_sheet_written,
        "warnings": warning_by_scene,
        "error": sheet_error,
    }


def post_render_audit(
    output_path: str,
    audio_path: str,
    clips: List[Dict[str, Any]],
    *,
    max_av_delta: float = 2.0,
    min_size_bytes: int = 100_000,
    max_size_bytes: int = 500 * 1024 * 1024,
) -> Dict[str, Any]:
    os_mod = _pa_attr("os", os)
    probe_dur_fn = _pa_attr("_ffprobe_duration", _ffprobe_duration)
    probe_streams_fn = _pa_attr("_ffprobe_streams", _ffprobe_streams)
    signal_report_fn = _pa_attr("_ffmpeg_signal_report", _ffmpeg_signal_report)

    warnings: List[str] = []
    errors: List[str] = []
    if not output_path or not os_mod.path.exists(output_path):
        return {"ok": False, "warnings": [], "errors": ["output_file_missing"], "report": {}}

    size = os_mod.path.getsize(output_path)
    if size < min_size_bytes:
        errors.append(f"output_too_small:{size}bytes")
    elif size > max_size_bytes:
        warnings.append(f"output_very_large:{size//1024//1024}MB")

    video_dur = probe_dur_fn(output_path)
    audio_dur = probe_dur_fn(audio_path) if audio_path and os_mod.path.exists(audio_path) else -1.0
    av_delta = None
    if video_dur > 0 and audio_dur > 0:
        av_delta = abs(video_dur - audio_dur)
        if av_delta > max_av_delta:
            errors.append(f"av_sync_error:video={video_dur:.2f}s audio={audio_dur:.2f}s delta={av_delta:.2f}s")
    elif video_dur <= 0:
        errors.append("video_duration_probe_failed")

    if video_dur > 0:
        if video_dur < 25.0:
            errors.append(f"video_too_short:{video_dur:.1f}s")
        elif video_dur > 68.0:
            warnings.append(f"video_over_limit:{video_dur:.1f}s")

    streams = probe_streams_fn(output_path)
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if not has_video:
        errors.append("no_video_stream_in_output")
    if not has_audio:
        errors.append("no_audio_stream_in_output")

    codec_names = [s.get("codec_name", "") for s in streams if s.get("codec_type") == "video"]
    pix_fmts = [s.get("pix_fmt", "") for s in streams if s.get("codec_type") == "video"]
    if codec_names and "h264" not in codec_names and "hevc" not in codec_names:
        warnings.append(f"unexpected_video_codec:{codec_names}")
    if pix_fmts and not any(f in ("yuv420p", "yuvj420p") for f in pix_fmts):
        warnings.append(f"unexpected_pix_fmt:{pix_fmts}")

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    video_metadata = video_streams[0] if video_streams else {}
    signal_report = signal_report_fn(output_path, has_video, has_audio)
    if not signal_report["available"]:
        warnings.append(f"signal_analysis_unavailable:{signal_report.get('error', 'unknown')}")
    for interval in signal_report["black_intervals"]:
        warnings.append(
            f"detected_black_frames:{interval['start']:.2f}-{interval['end']:.2f}s"
        )
    for interval in signal_report["silence_intervals"]:
        warnings.append(
            f"long_silence:{interval['start']:.2f}-{interval['end']:.2f}s"
        )
    peak_volume = signal_report.get("peak_volume_dbfs")
    if peak_volume is not None and peak_volume >= -1.0:
        warnings.append(f"audio_peak_clipping_risk:{peak_volume:.2f}dBFS")

    expected_dur = sum(float(c.get("duration", 0)) for c in clips)
    if expected_dur > 0 and video_dur > 0:
        ratio = video_dur / expected_dur
        if ratio < 0.80:
            errors.append(f"output_much_shorter_than_plan:video={video_dur:.1f}s plan={expected_dur:.1f}s ratio={ratio:.2f}")
        elif ratio > 1.25:
            warnings.append(f"output_longer_than_plan:video={video_dur:.1f}s plan={expected_dur:.1f}s ratio={ratio:.2f}")

    return {
        "ok": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "report": {
            "output_path": output_path,
            "size_bytes": size,
            "size_mb": round(size / 1024 / 1024, 2),
            "video_duration": round(video_dur, 2) if video_dur > 0 else None,
            "audio_duration": round(audio_dur, 2) if audio_dur > 0 else None,
            "av_delta": round(av_delta, 2) if av_delta is not None else None,
            "video_codec": codec_names,
            "pix_fmt": pix_fmts,
            "resolution": video_metadata.get("resolution"),
            "width": int(video_metadata["width"]) if video_metadata.get("width") else None,
            "height": int(video_metadata["height"]) if video_metadata.get("height") else None,
            "fps": float(video_metadata["fps"]) if video_metadata.get("fps") else None,
            "signal_analysis": signal_report,
            "streams": len(streams),
            "expected_duration": round(expected_dur, 2),
        },
    }


_GENERIC_FALLBACKS = {
    "ocean waves aerial", "mountain fog drone", "stars night sky",
    "cinematic atmosphere", "abstract background", "bokeh lights",
    "nature drone footage", "sky clouds timelapse", "city drone shot",
    "generic b-roll", "landscape aerial view",
}


def audit_search_queries(clips: List[Dict[str, Any]]) -> Dict[str, Any]:
    from .pipeline_audit import _expand_tokens_with_translations, _narration_tokens, _tokenize
    os_mod = _pa_attr("os", os)

    issues: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips):
        queries = clip.get("search_queries") or []
        if not queries and isinstance(clip.get("visual_intent"), dict):
            queries = clip["visual_intent"].get("search_queries") or []
        if not queries and isinstance(clip.get("visual_intent"), dict) and clip["visual_intent"].get("subject"):
            queries = [clip["visual_intent"]["subject"]]
        if not queries and clip.get("scene_description"):
            queries = [clip["scene_description"]]

        bad = [q for q in queries if q.strip().lower() in _GENERIC_FALLBACKS]
        empty = [i for i, q in enumerate(queries) if not q or not q.strip()]
        narr_tokens = _narration_tokens(clip)
        query_tokens: set = set()
        for q in queries:
            query_tokens |= _expand_tokens_with_translations(_tokenize(q))
        overlap = len(narr_tokens & query_tokens) / max(1, len(narr_tokens))

        has_valid_clip = bool(clip.get("path") and os_mod.path.exists(clip["path"]) and os_mod.path.getsize(clip["path"]) > 1000)
        is_bad = bool(bad)
        all_empty = bool(queries and len(empty) == len(queries))
        missing_queries = bool(not queries and not has_valid_clip)
        low_overlap = bool(overlap < 0.05 and not has_valid_clip and not clip.get("scene_description"))

        if is_bad or all_empty or missing_queries or low_overlap:
            issues.append({
                "scene_index": idx,
                "queries": queries,
                "bad_generic": bad,
                "empty_slots": empty,
                "narration_overlap": round(overlap, 3),
                "narration_preview": (clip.get("narration") or "")[:80],
            })
    return {
        "ok": len(issues) == 0,
        "issue_count": len(issues),
        "scenes_with_bad_queries": issues[:10],
    }
