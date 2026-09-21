"""
Closed-loop Quality Gate — pre/post render scoring (Items 88, 129, 201, 205, 494).
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import imageio_ffmpeg

from .schema import DirectorPlan
from .visual_intent import semantic_relevance_score, text_contains_excluded

from scenes.narration_validate import (
    MIN_WORDS_PER_SCENE,
    MIN_WORDS_PER_SENTENCE,
    normalize_narration_for_validation,
    scene_narration_issues,
    _split_sentences,
    _FRAGMENT_ENDING_RE,
)


def check_narration_integrity(plan: DirectorPlan) -> List[str]:
    """Detect condense artifacts: dangling endings and under-word scenes (normalized text)."""
    issues: List[str] = []
    seen: set[str] = set()

    def _add(code: str) -> None:
        if code not in seen:
            seen.add(code)
            issues.append(code)

    for s in plan.scenes:
        narr = (s.narration or "").strip()
        if not narr:
            _add(f"empty_narration_scene_{s.index}")
            continue
        codes = scene_narration_issues(narr)
        for code in codes:
            if code == "empty":
                _add(f"empty_narration_scene_{s.index}")
            elif code == "low_words":
                _add(f"low_words_scene_{s.index}")
            elif code == "no_terminal":
                _add(f"no_terminal_scene_{s.index}")
            elif code in ("fragment_ending", "fragment_sentence", "dangling_tail", "dangling_sentence"):
                _add(f"fragment_sentence_scene_{s.index}")

    # Full-narration scan only when stale vs scene join (avoids hook false-positives)
    scene_joined = " ".join(
        normalize_narration_for_validation(s.narration or "")
        for s in plan.scenes
        if (s.narration or "").strip()
    )
    full = normalize_narration_for_validation(plan.full_narration or "")
    # Compare letters/digits only: per-scene normalization collapses trailing
    # "..." / "!?" runs while the full-text pass keeps them mid-sentence, which
    # used to flag a false "stale" mismatch and block render on scenes ending in "...".
    _alnum = lambda t: re.sub(r"[\W_]+", "", t, flags=re.UNICODE)
    if _alnum(full) != _alnum(scene_joined):
        for sent in _split_sentences(full):
            if len(sent.split()) < MIN_WORDS_PER_SENTENCE:
                _add("fragment_sentence_full")
                break
            if _FRAGMENT_ENDING_RE.search(sent):
                _add("fragment_sentence_full")
                break

    return issues


def _ffprobe_duration(path: str) -> float:
    if not path or not os.path.exists(path):
        return 0.0
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        p = subprocess.run(
            [exe, "-i", path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, timeout=30,
        )
        import re
        err = (p.stderr or b"").decode("utf-8", errors="replace")
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", err)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return 0.0


def pre_render_score(plan: DirectorPlan) -> Dict[str, Any]:
    qt = plan.quality_thresholds
    issues: List[str] = []
    score = 100.0

    n = len(plan.scenes)
    if n < qt.min_scenes:
        issues.append(f"cadence<{qt.min_scenes}")
        score -= 25

    total = plan.total_duration()
    if total < qt.min_duration or total > qt.max_duration:
        issues.append("duration_out_of_band")
        score -= 20

    if plan.scenes and plan.scenes[0].beat_type != "hook":
        issues.append("missing_hook_beat")
        score -= 10

    # Alignment: narration vs visual intent
    align_scores = []
    for s in plan.scenes:
        qtext = " ".join(s.search_queries or s.visual_intent.search_queries)
        align_scores.append(semantic_relevance_score(qtext, s.narration, s.visual_intent) / 40.0)
        for q in (s.search_queries or []):
            if text_contains_excluded(q, s.visual_intent.must_exclude):
                issues.append(f"excluded_query_scene_{s.index}")
                score -= 5

    avg_align = sum(align_scores) / max(1, len(align_scores))
    if avg_align < qt.min_alignment_score:
        issues.append("low_visual_alignment")
        score -= 15

    sfx_n = len(plan.audio_events)
    density = sfx_n / max(1, n)
    if density > qt.max_sfx_density * 3:  # events per scene soft cap
        issues.append("sfx_overdense")
        score -= 10

    narration_issues = check_narration_integrity(plan)
    for ni in narration_issues:
        issues.append(ni)
        score -= 15 if ni.startswith("fragment") else 10

    hard_blockers = [
        i for i in issues
        if i == "duration_out_of_band"
        or i.startswith("cadence")
        or i.startswith("fragment")
        or i.startswith("low_words")
        or i.startswith("empty_narration")
        or i.startswith("no_terminal")
    ]
    ok = score >= 60 and not hard_blockers
    return {
        "ok": ok,
        "score": max(0, round(score, 1)),
        "issues": issues,
        "avg_alignment": round(avg_align, 3),
        "sfx_events": sfx_n,
        "duration": total,
        "scene_count": n,
        "phase": "pre",
    }


def post_render_score(
    plan: DirectorPlan,
    video_path: str,
    audio_path: Optional[str] = None,
) -> Dict[str, Any]:
    qt = plan.quality_thresholds
    issues: List[str] = []
    score = 100.0

    if not video_path or not os.path.exists(video_path):
        return {"ok": False, "score": 0, "issues": ["missing_output"], "phase": "post"}

    size = os.path.getsize(video_path)
    if size < 500_000:  # Item 452
        issues.append("file_too_small")
        score -= 40

    vdur = _ffprobe_duration(video_path)
    target = plan.total_duration()
    if audio_path and os.path.exists(audio_path):
        adur = _ffprobe_duration(audio_path)
    else:
        adur = target

    delta = abs(vdur - adur) if vdur and adur else 0.0
    if delta > qt.max_av_delta + 0.15:  # slightly soft for encode pad
        issues.append(f"av_delta_{delta:.3f}")
        score -= 20

    if vdur and (vdur < qt.min_duration - 1 or vdur > qt.max_duration + 1.0):
        issues.append("post_duration_band")
        score -= 35  # Madde 494 — duration band is a hard publish gate

    # Prefer 1080p for final deliverables (540p/720p = test only)
    try:
        import config as _cfg
        tw, th = getattr(_cfg, "get_target_resolution", lambda: (1080, 1920))()
        if th < 1080 or tw < 540:
            issues.append("low_resolution_test_mode")
            score -= 5
    except Exception:
        pass

    # Duplicate path + content hash check (P0-04)
    paths = [s.path for s in plan.scenes if s.path]
    if len(paths) != len(set(paths)):
        issues.append("duplicate_shots")
        score -= 10
    scene_clips = [{"path": p} for p in paths]
    if scene_clips:
        uniq = clip_uniqueness_report(scene_clips, min_unique=len(plan.scenes))
        if "duplicate_content_hash" in uniq.get("issues", []):
            issues.append("duplicate_content_hash")
            score -= 25

    # Hard-fail: never mark publishable if duration band violated (Madde 494)
    hard_blockers = {"missing_output", "file_too_small", "post_duration_band", "duplicate_content_hash"}
    ok = score >= 55 and not (hard_blockers & set(issues))
    return {
        "ok": ok,
        "score": max(0, round(score, 1)),
        "issues": issues,
        "video_duration": round(vdur, 3),
        "audio_duration": round(adur, 3) if adur else None,
        "av_delta": round(delta, 3),
        "file_mb": round(size / (1024 * 1024), 2),
        "phase": "post",
        "roadmap_items": [88, 129, 452, 494],
    }


def _file_md5(path: str) -> Optional[str]:
    """MD5 digest for on-disk clip (P0-04 content duplicate gate)."""
    if not path or not os.path.isfile(path):
        return None
    digest = hashlib.md5()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def clip_uniqueness_report(
    clips: List[Dict[str, Any]],
    min_unique: Optional[int] = None,
) -> Dict[str, Any]:
    """Reject duplicate clip paths or identical file content (P0-04)."""
    total = len(clips)
    min_required = min_unique if min_unique is not None else total

    path_to_indices: Dict[str, List[int]] = {}
    hash_to_indices: Dict[str, List[int]] = {}
    resolved = 0

    for i, clip in enumerate(clips):
        path = clip.get("path")
        if not path:
            continue
        resolved += 1
        path_to_indices.setdefault(path, []).append(i)
        file_hash = _file_md5(path)
        if file_hash:
            hash_to_indices.setdefault(file_hash, []).append(i)

    duplicate_path_indices: List[int] = []
    for indices in path_to_indices.values():
        if len(indices) > 1:
            duplicate_path_indices.extend(indices[1:])

    duplicate_hash_indices: List[int] = []
    for indices in hash_to_indices.values():
        if len(indices) > 1:
            duplicate_hash_indices.extend(indices[1:])

    unique_paths = len(path_to_indices)
    unique_hashes = len(hash_to_indices)

    issues: List[str] = []
    if duplicate_path_indices:
        issues.append("duplicate_paths")
    if duplicate_hash_indices:
        issues.append("duplicate_content_hash")
    if resolved < total:
        issues.append("missing_paths")
    if unique_hashes < min_required:
        issues.append(f"unique_hashes<{min_required}")

    ok = resolved == total and not issues
    return {
        "ok": ok,
        "total": total,
        "resolved": resolved,
        "unique_paths": unique_paths,
        "unique_hashes": unique_hashes,
        "min_required": min_required,
        "duplicate_path_indices": sorted(set(duplicate_path_indices)),
        "duplicate_hash_indices": sorted(set(duplicate_hash_indices)),
        "issues": issues,
    }


def format_duplicate_clips_error(report: Dict[str, Any]) -> str:
    """Human-readable abort when clip paths or content hashes repeat (P0-04)."""
    if report.get("ok"):
        return ""
    total = report.get("total", 0)
    unique_hashes = report.get("unique_hashes", 0)
    min_required = report.get("min_required", total)
    path_dupes = report.get("duplicate_path_indices") or []
    hash_dupes = report.get("duplicate_hash_indices") or []
    parts = [
        f"Visual uniqueness gate failed: {unique_hashes}/{min_required} unique clip hashes "
        f"for {total} scenes."
    ]
    if path_dupes:
        shown = ", ".join(str(i + 1) for i in path_dupes[:16])
        if len(path_dupes) > 16:
            shown += f", ... (+{len(path_dupes) - 16} more)"
        parts.append(f"Duplicate paths at scenes (1-based): {shown}.")
    if hash_dupes:
        shown = ", ".join(str(i + 1) for i in hash_dupes[:16])
        if len(hash_dupes) > 16:
            shown += f", ... (+{len(hash_dupes) - 16} more)"
        parts.append(f"Duplicate content hash at scenes (1-based): {shown}.")
    parts.append("Render aborted to avoid repeated stock footage.")
    return " ".join(parts)


def clip_coverage_report(clips: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Post-fetch clip contract: every scene must have a resolved path."""
    total = len(clips)
    missing = [i for i, c in enumerate(clips) if not c.get("path")]
    ok = total - len(missing)
    return {
        "total": total,
        "ok": ok,
        "missing_indices": missing,
        "complete": total > 0 and not missing,
    }


def format_missing_clips_error(report: Dict[str, Any]) -> str:
    """Human-readable abort message for partial visual fetch (P0-03)."""
    total = report.get("total", 0)
    ok = report.get("ok", 0)
    missing = report.get("missing_indices") or []
    if not missing:
        return ""
    shown = ", ".join(str(i + 1) for i in missing[:24])
    if len(missing) > 24:
        shown += f", ... (+{len(missing) - 24} more)"
    return (
        f"Visual clip contract failed: {ok}/{total} scenes fetched. "
        f"Missing scenes (1-based): {shown}. Render aborted to avoid single-clip repeat."
    )


def scenes_needing_regen(plan: DirectorPlan, pre: Dict[str, Any]) -> List[int]:
    """Return scene indices that failed exclusion / alignment checks."""
    bad = []
    for s in plan.scenes:
        for q in (s.search_queries or []):
            if text_contains_excluded(q, s.visual_intent.must_exclude):
                bad.append(s.index)
                break
        else:
            qtext = " ".join(s.search_queries or [])
            if semantic_relevance_score(qtext, s.narration, s.visual_intent) < 0:
                bad.append(s.index)
    return sorted(set(bad))
