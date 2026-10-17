"""
Render Pipeline Auditor -- pre-render + post-render quality gates.

Post-render verification, frame contact-sheet sampling, FFmpeg signal analysis,
and search query auditing live in `render/pipeline_post_audit.py` and are
re-exported here for full compatibility.
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Any, Dict, List, Optional

from .pipeline_post_audit import (
    _GENERIC_FALLBACKS,
    _ffmpeg_signal_report,
    _ffprobe_duration,
    _ffprobe_streams,
    audit_search_queries,
    audit_visual_frames,
    post_render_audit,
)


def _stop_words() -> set:
    return {
        "ve", "ile", "bir", "bu", "de", "da", "ki",
        "the", "a", "an", "and", "of", "in", "on", "at", "to", "is", "are",
        "was", "were", "it", "its", "from", "by", "that", "this", "with",
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
