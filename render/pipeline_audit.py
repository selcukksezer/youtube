"""
Render Pipeline Auditor -- pre-render + post-render quality gates.
"""
from __future__ import annotations
import os, re, subprocess
from typing import Any, Dict, List, Optional


def _stop_words() -> set:
    return {
        "ve","ile","bir","bu","de","da","ki",
        "the","a","an","and","of","in","on","at","to","is","are",
        "was","were","it","its","from","by","that","this","with",
    }


def _tokenize(text: str) -> set:
    sw = _stop_words()
    return {
        w for w in re.split(r"[^a-zA-Z0-9\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc]+",
                            (text or "").lower())
        if len(w) >= 3 and w not in sw
    }


def _expand_tokens_with_translations(tokens: set) -> set:
    expanded = set(tokens)
    try:
        from visuals.query_builder import _TR_EN
        for tr_word in list(tokens):
            if tr_word in _TR_EN:
                for en_word in _tokenize(_TR_EN[tr_word]):
                    expanded.add(en_word)
    except Exception:
        pass
    return expanded


def _clip_name_tokens(clip: Dict[str, Any]) -> set:
    tokens: set = set()
    path = clip.get("path") or ""
    if path:
        tokens |= _tokenize(os.path.splitext(os.path.basename(path))[0])
    for q in clip.get("search_queries") or []:
        tokens |= _tokenize(q)
    v_intent = clip.get("visual_intent") or {}
    if isinstance(v_intent, dict):
        for q in v_intent.get("search_queries") or []:
            tokens |= _tokenize(q)
        tokens |= _tokenize(v_intent.get("subject") or "")
        tokens |= _tokenize(v_intent.get("lighting") or "")
        tokens |= _tokenize(v_intent.get("shot_type") or "")
    tokens |= _tokenize(clip.get("scene_description") or "")
    tokens |= _tokenize(clip.get("mood") or "")
    tokens |= _tokenize(clip.get("badge_label") or "")
    return _expand_tokens_with_translations(tokens)


def _narration_tokens(clip: Dict[str, Any]) -> set:
    return _expand_tokens_with_translations(_tokenize(clip.get("narration") or ""))


def attach_candidate_metadata(clips: List[Dict[str, Any]], manifest_rows: List[Dict[str, Any]]) -> None:
    """Attach provider evidence only when the manifest row belongs to this scene and path."""
    rows_by_scene = {
        row.get("scene_index"): row
        for row in manifest_rows
        if isinstance(row, dict) and row.get("scene_index") is not None
    }
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            continue
        for key in (
            "candidate_topic_match_score", "candidate_semantic_evidence",
            "candidate_visual_verification_score",
            "candidate_source", "candidate_title", "candidate_tags", "candidate_description",
            "candidate_matched_terms",
        ):
            clip.pop(key, None)
        row = rows_by_scene.get(index)
        if not row or not clip.get("path") or not row.get("path"):
            continue
        clip_path = os.path.normcase(os.path.abspath(str(clip["path"])))
        row_path = os.path.normcase(os.path.abspath(str(row["path"])))
        if clip_path != row_path:
            continue
        topic_score = row.get("topic_match_score")
        if isinstance(topic_score, (int, float)) and not isinstance(topic_score, bool):
            clip["candidate_topic_match_score"] = float(topic_score)
        verification_score = row.get("visual_verification_score")
        if isinstance(verification_score, (int, float)) and not isinstance(verification_score, bool):
            clip["candidate_visual_verification_score"] = float(verification_score)
        if row.get("source"):
            clip["candidate_source"] = str(row["source"])
        evidence = row.get("semantic_evidence")
        if isinstance(evidence, dict):
            clip["candidate_semantic_evidence"] = evidence
        for source_key, target_key in (
            ("title", "candidate_title"), ("tags", "candidate_tags"),
            ("description", "candidate_description"),
            ("matched_terms", "candidate_matched_terms"),
        ):
            if row.get(source_key):
                clip[target_key] = row[source_key]


def _semantic_overlap(clip: Dict[str, Any]) -> float:
    if not isinstance(clip, dict):
        return 0.0
    evidence = clip.get("candidate_semantic_evidence")
    if isinstance(evidence, dict):
        if evidence.get("rejected") or evidence.get("subject_match") is False:
            return 0.0
        if evidence.get("subject_match") is True:
            scores = [
                clip.get("candidate_visual_verification_score"),
                clip.get("candidate_topic_match_score"),
                evidence.get("text_overlap"),
            ]
            numeric_scores = [
                max(0.0, min(1.0, float(score)))
                for score in scores
                if isinstance(score, (int, float)) and not isinstance(score, bool)
            ]
            return max(numeric_scores) if numeric_scores else 1.0
    verification_score = clip.get("candidate_visual_verification_score")
    if isinstance(verification_score, (int, float)) and not isinstance(verification_score, bool):
        return max(0.0, min(1.0, float(verification_score)))
    source = str(clip.get("candidate_source") or "").lower()
    if source.startswith(("procedural", "ai_generated", "pollinations", "flux", "gameplay")):
        return 1.0
    topic_score = clip.get("candidate_topic_match_score")
    b = _narration_tokens(clip)
    if not b:
        return 1.0
    candidate_text = " ".join(
        str(clip.get(key) or "")
        for key in (
            "candidate_title", "candidate_tags", "candidate_description",
            "candidate_matched_terms",
        )
    )
    if not candidate_text and source in {
        "pexels", "pixabay", "coverr", "openverse", "wikimedia", "nasa", "archive_org",
    }:
        return 0.0
    if not candidate_text:
        visual_intent = clip.get("visual_intent") or {}
        query_text = " ".join(clip.get("search_queries") or [])
        if isinstance(visual_intent, dict):
            query_text += " " + " ".join(visual_intent.get("search_queries") or [])
            query_text += " " + str(visual_intent.get("subject") or "")
        candidate_text = " ".join((
            query_text,
            str(clip.get("scene_description") or ""),
            str(clip.get("mood") or ""),
            str(clip.get("badge_label") or ""),
        ))
    a = _expand_tokens_with_translations(_tokenize(candidate_text))
    if a:
        return max(0.0, min(1.0, len(a & b) / len(a)))
    if isinstance(topic_score, (int, float)) and not isinstance(topic_score, bool):
        return max(0.0, min(1.0, float(topic_score)))
    return 0.0


def retry_low_confidence_scenes(clips, retry_scene, threshold: float = 0.08):
    """Retry low-confidence scenes once and return retried and still-low indices."""
    retry_indices = [
        index for index, clip in enumerate(clips)
        if _semantic_overlap(clip) < threshold and isinstance(clip, dict) and clip.get("narration")
    ]
    for index in retry_indices:
        retry_scene(index, clips[index])
    remaining = [
        index for index, clip in enumerate(clips)
        if _semantic_overlap(clip) < threshold and isinstance(clip, dict) and clip.get("narration")
    ]
    return retry_indices, remaining


def require_semantic_confidence(scene_indices) -> None:
    if scene_indices:
        blocked = ", ".join(str(index + 1) for index in scene_indices)
        raise RuntimeError(
            f"Visual/narration mismatch remains in scene(s): {blocked}. "
            "Regenerate the script or select visuals that match the narration."
        )


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

    samples: List[Dict[str, Any]] = []
    warning_by_scene: List[str] = []
    contact_images: List[Any] = []
    for index, clip in enumerate(clips):
        path = str((clip or {}).get("path") or "")
        if not path or not os.path.isfile(path):
            warning_by_scene.append(f"visual_frame_unavailable:scene_{index + 1}:clip_missing")
            samples.append({"scene": index + 1, "available": False, "error": "clip_missing"})
            contact_images.append(None)
            continue

        try:
            if os.path.splitext(path)[1].lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                with Image.open(path) as source:
                    frame = source.convert("RGB")
            else:
                duration = max(0.0, float((clip or {}).get("duration") or 0.0))
                seek = max(0.0, duration / 2.0)
                import imageio_ffmpeg
                ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
                completed = subprocess.run(
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
            distance = (int(left_hash, 16) ^ int(right_hash, 16)).bit_count()
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
            os.makedirs(os.path.dirname(os.path.abspath(contact_sheet_path)), exist_ok=True)
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


def _ffprobe_duration(path: str) -> float:
    """Probe video duration using ffmpeg (ffprobe not bundled with imageio_ffmpeg)."""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        # Use ffmpeg -i to extract duration from stderr (bytes mode to prevent Windows cp1254 crashes)
        r = subprocess.run(
            [ffmpeg, "-i", path, "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        )
        stderr = r.stderr.decode("utf-8", errors="ignore") if r.stderr else ""
        # Parse "Duration: HH:MM:SS.ms" from stderr
        import re
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
        import imageio_ffmpeg, re
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        r = subprocess.run(
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

    try:
        import imageio_ffmpeg

        result = subprocess.run(
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


# ── pre-render ──────────────────────────────────────────────────────────────

def pre_render_audit(
    clips: List[Dict[str, Any]],
    audio_path: str,
    *,
    plan: Optional[Dict[str, Any]] = None,
    tolerance_seconds: float = 8.0,
    semantic_warn_threshold: float = 0.08,
) -> Dict[str, Any]:
    warnings: List[str] = []
    errors: List[str] = []
    n = len(clips)
    if n < 4:
        errors.append(f"scene_count_too_low:{n}")
    elif n > 16:
        warnings.append(f"scene_count_high:{n}")

    valid = [c for c in clips if c.get("path") and os.path.exists(c["path"])]
    missing_count = n - len(valid)
    if missing_count > 0:
        ratio = missing_count / n
        msg = f"missing_clips:{missing_count}/{n}({ratio*100:.0f}pct)"
        (errors if ratio >= 0.20 else warnings).append(msg)

    paths = [c.get("path") for c in valid]
    seen: Dict[str, List[int]] = {}
    for idx, p in enumerate(paths):
        if p:
            seen.setdefault(p, []).append(idx)
    dupes = {p: idxs for p, idxs in seen.items() if len(idxs) > 1}
    if dupes:
        dupe_info = ";".join(f"{os.path.basename(p)}@{idxs}" for p, idxs in list(dupes.items())[:5])
        errors.append(f"duplicate_clips:{dupe_info}")

    clip_total = sum(float(c.get("duration", 0)) for c in clips)
    audio_dur = -1.0
    av_delta = None
    if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
        audio_dur = _ffprobe_duration(audio_path)
        if audio_dur <= 0:
            warnings.append("audio_duration_probe_failed")
        else:
            av_delta = abs(clip_total - audio_dur)
            if av_delta > tolerance_seconds:
                warnings.append(f"av_duration_mismatch:clips={clip_total:.1f}s audio={audio_dur:.1f}s delta={av_delta:.1f}s")

    low_match: List[str] = []
    low_stock_match: List[int] = []
    semantic_scores: List[float] = []
    stock_semantic_scores: List[float] = []
    scene_matches: List[Dict[str, Any]] = []
    missing_scene_indices: List[int] = []
    stock_sources = {
        "pexels", "pixabay", "coverr", "openverse", "wikimedia",
        "nasa", "archive_org", "met_museum",
    }
    for idx, clip in enumerate(clips):
        score = _semantic_overlap(clip)
        semantic_scores.append(score)
        source = str(clip.get("candidate_source") or "").lower().replace("_img", "")
        if source in stock_sources:
            stock_semantic_scores.append(score)
            if score < semantic_warn_threshold:
                low_stock_match.append(idx + 1)
        path = clip.get("path") if isinstance(clip, dict) else None
        if not path or not os.path.exists(path):
            missing_scene_indices.append(idx + 1)
        evidence = clip.get("candidate_semantic_evidence") or {}
        scene_matches.append({
            "scene": idx + 1,
            "score": round(score, 3),
            "asset": os.path.basename(path) if path else None,
            "candidate": clip.get("candidate_title") or None,
            "source": clip.get("candidate_source") or None,
            "matched_terms": clip.get("candidate_matched_terms") or [],
            "rejected": evidence.get("rejected") if isinstance(evidence, dict) else None,
            "source": clip.get("candidate_source") or None,
            "evidence_available": bool(
                clip.get("candidate_title")
                or clip.get("candidate_tags")
                or clip.get("candidate_semantic_evidence")
                or clip.get("candidate_topic_match_score") is not None
                or clip.get("candidate_visual_verification_score") is not None
            ),
        })
        if score < semantic_warn_threshold and clip.get("narration"):
            candidate = clip.get("candidate_title") or os.path.basename(path or "none")
            terms = ",".join(clip.get("candidate_matched_terms") or []) or "none"
            rejection = evidence.get("rejected") if isinstance(evidence, dict) else None
            reason = f" rejected={rejection}" if rejection else ""
            low_match.append(
                f"scene[{idx + 1}]score={score:.2f} candidate={str(candidate)[:40]!r} "
                f"matched_terms={terms[:60]!r}{reason}"
            )
    if low_match:
        warnings.append(f"semantic_mismatch:{len(low_match)}scenes -- " + " | ".join(low_match[:3]))
    if low_stock_match:
        warnings.append(
            "stock_match_low_confidence_scenes:"
            + ",".join(str(index) for index in low_stock_match)
        )
    if missing_scene_indices:
        warnings.append(
            "missing_visual_scenes:" + ",".join(str(index) for index in missing_scene_indices)
        )
    avg_semantic = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0.0

    bgm_ok = True
    plan_bgm = (plan or {}).get("bgm_track") or ""
    if plan_bgm and os.path.exists(plan_bgm):
        bgm_dur = _ffprobe_duration(plan_bgm)
        if 0 < bgm_dur < clip_total * 0.5:
            warnings.append(f"bgm_too_short:bgm={bgm_dur:.1f}s clips={clip_total:.1f}s")
            bgm_ok = False

    if plan:
        plan_scenes = len(plan.get("scenes") or [])
        if plan_scenes != n:
            warnings.append(f"plan_clip_count_mismatch:plan={plan_scenes} clips={n}")

    return {
        "ok": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "report": {
            "scene_count": n,
            "valid_clips": len(valid),
            "missing_clips": missing_count,
            "duplicate_clips": len(dupes),
            "clip_total_duration": round(clip_total, 2),
            "audio_duration": round(audio_dur, 2) if audio_dur > 0 else None,
            "av_delta": round(av_delta, 2) if av_delta is not None else None,
            "avg_semantic_score": round(avg_semantic, 3),
            "low_semantic_count": len(low_match),
            "stock_scene_count": len(stock_semantic_scores),
            "avg_stock_semantic_score": (
                round(sum(stock_semantic_scores) / len(stock_semantic_scores), 3)
                if stock_semantic_scores else None
            ),
            "low_stock_match_count": len(low_stock_match),
            "scene_matches": scene_matches,
            "missing_scene_indices": missing_scene_indices,
            "bgm_ok": bgm_ok,
        },
    }


# ── post-render ─────────────────────────────────────────────────────────────

def post_render_audit(
    output_path: str,
    audio_path: str,
    clips: List[Dict[str, Any]],
    *,
    max_av_delta: float = 2.0,
    min_size_bytes: int = 100_000,
    max_size_bytes: int = 500 * 1024 * 1024,
) -> Dict[str, Any]:
    warnings: List[str] = []
    errors: List[str] = []
    if not output_path or not os.path.exists(output_path):
        return {"ok": False, "warnings": [], "errors": ["output_file_missing"], "report": {}}

    size = os.path.getsize(output_path)
    if size < min_size_bytes:
        errors.append(f"output_too_small:{size}bytes")
    elif size > max_size_bytes:
        warnings.append(f"output_very_large:{size//1024//1024}MB")

    video_dur = _ffprobe_duration(output_path)
    audio_dur = _ffprobe_duration(audio_path) if audio_path and os.path.exists(audio_path) else -1.0
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

    streams = _ffprobe_streams(output_path)
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
    signal_report = _ffmpeg_signal_report(output_path, has_video, has_audio)
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


# ── search query audit ──────────────────────────────────────────────────────

_GENERIC_FALLBACKS = {
    "ocean waves aerial","mountain fog drone","stars night sky",
    "cinematic atmosphere","abstract background","bokeh lights",
    "nature drone footage","sky clouds timelapse","city drone shot",
    "generic b-roll","landscape aerial view",
}


def audit_search_queries(clips: List[Dict[str, Any]]) -> Dict[str, Any]:
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

        has_valid_clip = bool(clip.get("path") and os.path.exists(clip["path"]) and os.path.getsize(clip["path"]) > 1000)
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


# ── full pipeline report ─────────────────────────────────────────────────────

def generate_full_audit_report(
    clips: List[Dict[str, Any]],
    audio_path: str,
    output_path: Optional[str] = None,
    *,
    plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    pre = pre_render_audit(clips, audio_path, plan=plan)
    qaudit = audit_search_queries(clips)
    result: Dict[str, Any] = {"pre_render": pre, "query_audit": qaudit}
    if output_path and os.path.exists(output_path):
        post = post_render_audit(output_path, audio_path, clips)
        result["post_render"] = post
        result["overall_ok"] = pre["ok"] and post["ok"]
    else:
        result["overall_ok"] = pre["ok"]
    return result
