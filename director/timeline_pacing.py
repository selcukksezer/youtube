"""
Timeline Pacing, Beat Assignment, Overlong TTS Recovery, and Beat-Grid Snapping
for `director/timeline.py`.
"""
from __future__ import annotations

import copy
import re
import sys
import wave
from typing import Any, Dict, List, Optional, Tuple

from scenes.narration_validate import (
    _strip_dangling_clause,
    normalize_narration_for_validation,
    scene_narration_issues,
)

from .schema import (
    DirectorPlan,
    ScenePlan,
    natural_narration_word_cap,
)


def _tl_attr(name: str, default: Any) -> Any:
    tl = sys.modules.get("director.timeline")
    return getattr(tl, name, default) if tl is not None else default


def _assign_beat_types(scenes: List[ScenePlan], total: float) -> None:
    """Map scenes onto classic Shorts arc (Item 274) — percent of actual duration."""
    span = total if total and total > 0 else 1.0
    for s in scenes:
        mid = (s.t0 + s.t1) / 2.0
        pct = mid / span
        narr_l = (s.narration or "").lower()
        if s.index == 0 or pct <= 0.07:
            s.beat_type = "hook"
        elif pct <= 0.45:
            s.beat_type = "conflict"
        elif pct <= 0.75:
            s.beat_type = "climax"
        else:
            s.beat_type = "resolution"

        if any(k in narr_l for k in ("tahmin", "quiz", "kaç saniye", "doğru cevap", "a mı b")):
            s.beat_type = "quiz"
        elif any(k in narr_l for k in ("belge", "rapor", "daktilo", "ifşa")):
            s.beat_type = "document"
        elif any(k in narr_l for k in ("şok", "inanılmaz", "asla tahmin")):
            if s.beat_type in ("conflict", "climax"):
                s.beat_type = "shock"


def _plan_dict_word_count(scenes: List[dict]) -> int:
    return sum(
        len(normalize_narration_for_validation(s.get("narration") or "").split())
        for s in scenes
    )


def _settle_spoken_sentence(text: str, max_words: int) -> str:
    """Finish or drop a clipped clause. Never return a dangling tail."""
    from .timeline import _ensure_terminal, _shorten_sentence, _split_sentences

    text = (text or "").strip()
    if not text or max_words <= 0:
        return ""
    if len(text.split()) <= max_words and not scene_narration_issues(text):
        return text

    kept: List[str] = []
    count = 0
    for part in _split_sentences(text):
        cand = _ensure_terminal(part)
        pw = len(cand.split())
        if count + pw > max_words:
            break
        if scene_narration_issues(cand):
            break
        kept.append(cand)
        count += pw
    if kept:
        return " ".join(kept)

    short = _shorten_sentence(text, max_words)
    if short and not scene_narration_issues(short) and len(short.split()) <= max_words:
        return short
    stripped, _ = _strip_dangling_clause(text)
    stripped = _ensure_terminal(stripped) if stripped else ""
    if stripped and not scene_narration_issues(stripped) and len(stripped.split()) <= max_words:
        return stripped
    return ""


def condense_plan_narration(plan: dict, max_words: int) -> dict:
    """
    Shorten a legacy plan to max_words. No network.
    Already-short narration is copied unchanged.
    A clipped clause is finished or dropped.
    """
    from .timeline import _ensure_terminal, _split_sentences

    out = copy.deepcopy(plan or {})
    scenes = [s for s in (out.get("scenes") or []) if isinstance(s, dict)]
    if _plan_dict_word_count(scenes) <= max_words:
        out["scenes"] = scenes
        out["full_narration"] = " ".join(
            (s.get("narration") or "").strip() for s in scenes if (s.get("narration") or "").strip()
        )
        return out

    flat: List[Tuple[int, str]] = []
    for i, scene in enumerate(scenes):
        parts = _split_sentences(scene.get("narration") or "")
        if not parts and (scene.get("narration") or "").strip():
            parts = [(scene.get("narration") or "").strip()]
        for part in parts:
            flat.append((i, _ensure_terminal(part)))

    kept_by_scene: Dict[int, List[str]] = {i: [] for i in range(len(scenes))}
    count = 0
    for idx, sent in flat:
        cleaned = _settle_spoken_sentence(sent, max_words - count)
        if not cleaned:
            continue
        pw = len(cleaned.split())
        if count + pw > max_words:
            break
        kept_by_scene[idx].append(cleaned)
        count += pw

    new_scenes: List[dict] = []
    for i, scene in enumerate(scenes):
        narr = " ".join(kept_by_scene[i]).strip()
        if not narr:
            continue
        narr = _settle_spoken_sentence(narr, len(narr.split()))
        if not narr:
            continue
        row = dict(scene)
        row["narration"] = narr
        new_scenes.append(row)

    guard = 0
    while _plan_dict_word_count(new_scenes) > max_words and new_scenes and guard < 40:
        guard += 1
        last = new_scenes[-1]
        parts = _split_sentences(last.get("narration") or "")
        if len(parts) > 1:
            last["narration"] = " ".join(_ensure_terminal(p) for p in parts[:-1])
            continue
        if len(new_scenes) > 1:
            new_scenes.pop()
            continue
        last["narration"] = _settle_spoken_sentence(last.get("narration") or "", max_words)
        break

    out["scenes"] = new_scenes
    out["full_narration"] = " ".join(
        (s.get("narration") or "").strip() for s in new_scenes if (s.get("narration") or "").strip()
    )
    out["word_budget_494"] = {
        "max": max_words,
        "words": _plan_dict_word_count(new_scenes),
    }
    return out


def recover_overlong_narration(plan: dict, *, audio_seconds: float) -> dict:
    """
    First over-long TTS recovery. Condenses. Does not raise Madde 494.
    Does not call Gemini. One shot — the caller runs TTS once after this.
    """
    scenes = [s for s in ((plan or {}).get("scenes") or []) if isinstance(s, dict)]
    words = _plan_dict_word_count(scenes)
    if not words and (plan or {}).get("full_narration"):
        words = len(
            normalize_narration_for_validation(
                str(plan.get("full_narration") or "")
            ).split()
        )
    cap = natural_narration_word_cap(words, audio_seconds)
    if words <= cap:
        return copy.deepcopy(plan or {})
    condense_fn = _tl_attr("condense_plan_narration", condense_plan_narration)
    return condense_fn(plan, cap)


def fit_tts_to_timeline(
    audio_path: str,
    plan: DirectorPlan,
    word_timings: Optional[List[Dict[str, Any]]] = None,
    output_path: Optional[str] = None,
    allow_tempo_fallback: bool = False,
) -> Tuple[str, List[Dict[str, Any]], float, float]:
    """
    Fit narration audio to scene budget.
    Returns (audio_path, timings, audio_dur, speed_factor).
    """
    qt = plan.quality_thresholds
    budget_ceiling = min(max(qt.max_duration, 60.0), 60.0)
    _ = output_path

    try:
        with wave.open(audio_path, "rb") as w:
            audio_dur = w.getnframes() / float(w.getframerate())
    except Exception:
        return audio_path, word_timings or [], 0.0, 1.0

    if audio_dur <= 0:
        return audio_path, word_timings or [], audio_dur, 1.0

    def _rescale_scenes_to(dur: float) -> None:
        if dur <= 2.0 or not plan.scenes:
            return
        scale = dur / max(plan.total_duration(), 0.01)
        scaled = [round(s.duration * scale, 3) for s in plan.scenes]
        bpm = float((plan.meta or {}).get("beat_bpm") or 100.0)
        try:
            from bgm_manager import snap_durations_to_bpm
            scaled = snap_durations_to_bpm(scaled, bpm, total=dur)
        except Exception:
            pass
        t = 0.0
        for s, dur_s in zip(plan.scenes, scaled):
            s.duration = dur_s
            s.t0 = round(t, 3)
            t = round(t + s.duration, 3)
            s.t1 = round(t, 3)
            s.beat_hint_ms = round(s.t1 * 1000.0, 1)

    if audio_dur <= budget_ceiling + 0.5:
        _rescale_scenes_to(audio_dur)
        return audio_path, word_timings or [], audio_dur, 1.0

    if allow_tempo_fallback:
        try:
            from services.audio_tempo_guard import speedup_audio
            target_cap = min(budget_ceiling, 59.5)
            fitted_audio = (output_path or audio_path).rsplit(".", 1)[0] + "_fitted.wav"
            speedup_audio(audio_path, fitted_audio, target_duration=target_cap)
            scaled_dur = target_cap
            speed_factor = audio_dur / target_cap
            scaled_timings = []
            for wt in (word_timings or []):
                wt_copy = dict(wt)
                if "start" in wt_copy:
                    wt_copy["start"] = round(wt_copy["start"] / speed_factor, 3)
                if "end" in wt_copy:
                    wt_copy["end"] = round(wt_copy["end"] / speed_factor, 3)
                scaled_timings.append(wt_copy)
            _rescale_scenes_to(scaled_dur)
            return fitted_audio, scaled_timings, scaled_dur, speed_factor
        except Exception:
            _rescale_scenes_to(min(audio_dur, 59.5))
            return audio_path, word_timings or [], min(audio_dur, 59.5), 1.0

    cap_words = natural_narration_word_cap(max_duration=budget_ceiling)
    raise RuntimeError(
        f"Madde 494 hard-fail: TTS {audio_dur:.1f}s > {budget_ceiling:.0f}s at natural pace. "
        f"Condense narration (≤{cap_words} words) and re-render. Do not speed up."
    )


def snap_scenes_to_beat_hints(
    scenes: List[ScenePlan],
    bgm_path: str = "",
    bpm: Optional[float] = None,
    min_scene_dur: float = 1.8,
    max_scene_dur: float = 7.0,
) -> List[ScenePlan]:
    """
    Bölüm 7.3: Timeline sahnelerini 80-120 BPM aralığındaki müzik ritim vuruşlarına kilitler.
    """
    from bgm_manager import snap_timeline_to_beat_grid
    return snap_timeline_to_beat_grid(
        scenes,
        bgm_path=bgm_path,
        bpm=bpm,
        min_scene_dur=min_scene_dur,
        max_scene_dur=max_scene_dur,
        enforce_band=True,
    )
