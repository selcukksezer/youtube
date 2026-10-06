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
            "candidate_title", "candidate_tags", "candidate_description",
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
    topic_score = clip.get("candidate_topic_match_score")
    if isinstance(topic_score, (int, float)) and not isinstance(topic_score, bool) and topic_score >= 0.08:
        return 1.0
    evidence = clip.get("candidate_semantic_evidence")
    if isinstance(evidence, dict) and evidence.get("subject_match") is True and not evidence.get("rejected"):
        return 1.0
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
    a = _expand_tokens_with_translations(_tokenize(candidate_text))
    if not a:
        return 0.0
    return len(a & b) / len(a)


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
                entry["pix_fmt"] = pix_m.group(1) if pix_m else "unknown"
                streams.append(entry)
            elif ": Audio:" in line:
                codec_m = re.search(r"Audio:\s*(\w+)", line)
                streams.append({"codec_type": "audio", "codec_name": codec_m.group(1) if codec_m else "unknown"})
        return streams
    except Exception:
        return []


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
    semantic_scores: List[float] = []
    for idx, clip in enumerate(clips):
        score = _semantic_overlap(clip)
        semantic_scores.append(score)
        if score < semantic_warn_threshold and clip.get("narration"):
            subj = (clip.get("scene_description") or clip.get("narration") or "")[:60]
            clip_name = os.path.basename(clip.get("path") or "none")
            low_match.append(f"scene[{idx}]score={score:.2f} clip={clip_name[:30]} narr={subj!r}")
    if low_match:
        warnings.append(f"semantic_mismatch:{len(low_match)}scenes -- " + " | ".join(low_match[:3]))
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
