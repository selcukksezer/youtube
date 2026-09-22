"""
Constraint-based Timeline Solver (Items 88, 129, 266, 274, 494).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from scenes.narration_validate import MIN_WORDS_PER_SCENE, MIN_WORDS_PER_SENTENCE, scene_narration_issues

from .schema import (
    DirectorPlan,
    ScenePlan,
    QualityThresholds,
    TTS_EMERGENCY_MAX_SPEED,
    natural_target_duration,
    shorts_word_budget,
)


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


_DANGLING_END_WORDS = frozenset({
    "ve", "ama", "çünkü", "için", "ise", "ile", "bir", "bu", "o", "senin", "kendi",
    "olan", "gibi", "de", "da", "hiçbir", "asla", "derin", "burada", "tam", "olarak",
    "içindeki", "icindeki", "ateşi", "atesi", "zehri", "kaleyi", "yelkenini", "şeye", "seye",
    "dertlerle", "marcus", "hiçbir", "hicbir", "ise", "gelecek",
})

_FILLER_PHRASES = (
    " tam olarak ", " gerçekten ", " aslında ", " yani ", " işte ", " tabii ki ",
)


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def _effective_word_count(text: str) -> int:
    return len([w.strip(".,!?;:") for w in (text or "").split() if w.strip(".,!?;:")])


def _ensure_terminal(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if s[-1] not in ".!?":
        s += "."
    return s


def _trim_dangling_tail(words: List[str]) -> List[str]:
    trimmed = list(words)
    while len(trimmed) > MIN_WORDS_PER_SCENE and trimmed[-1].lower().rstrip(".,!?") in _DANGLING_END_WORDS:
        trimmed.pop()
    return trimmed


def _shorten_sentence(text: str, max_words: int) -> str:
    """Rule-based single-sentence compress — word boundaries only (P0-01)."""
    text = (text or "").strip().rstrip(".!?")
    if not text or max_words <= 0:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return _ensure_terminal(text)

    clauses = [c.strip() for c in re.split(r",\s*", text) if c.strip()]
    if len(clauses) > 1:
        kept: List[str] = []
        count = 0
        for clause in clauses:
            cw = clause.split()
            if count + len(cw) <= max_words:
                kept.append(clause)
                count += len(cw)
            else:
                break
        if kept and count >= MIN_WORDS_PER_SCENE:
            return _ensure_terminal(", ".join(kept))

    stripped = text
    for filler in _FILLER_PHRASES:
        stripped = stripped.replace(filler, " ")
    stripped = re.sub(r"\s+", " ", stripped).strip()
    sw = stripped.split()
    if MIN_WORDS_PER_SCENE <= len(sw) <= max_words:
        return _ensure_terminal(stripped)

    chunk = _trim_dangling_tail(sw[:max_words])
    if len(chunk) >= MIN_WORDS_PER_SCENE:
        return _ensure_terminal(" ".join(chunk))
    return ""


def _split_narration_near_mid(text: str) -> Tuple[str, str]:
    """
    Split narration near midpoint ONLY on sentence boundaries (.!?).
    Never split mid-word or mid-clause — returns ("", "") when not splittable.
    """
    text = (text or "").strip()
    parts = _split_sentences(text)
    if len(parts) >= 2:
        total = len(text.split())
        best_i = 1
        best_diff = total
        cum = 0
        for i, part in enumerate(parts):
            cum += len(part.split())
            diff = abs(cum - total // 2)
            if diff < best_diff:
                best_diff = diff
                best_i = i + 1
        left = " ".join(parts[:best_i]).strip()
        right = " ".join(parts[best_i:]).strip()
        min_half = min(MIN_WORDS_PER_SCENE, MIN_WORDS_PER_SENTENCE)
        if (
            left and right
            and _effective_word_count(left) >= min_half
            and _effective_word_count(right) >= min_half
        ):
            return left, right
    return "", ""


def _visual_pad_scene(source: ScenePlan, index: int) -> ScenePlan:
    """Duplicate visual beat with alternate angle — narration stays on source scene."""
    desc = source.scene_description or "cinematic dramatic reaction"
    queries = list(source.search_queries or [])
    alt_q = [f"{q} alternate angle" if q else "cinematic reaction cutaway" for q in queries[:3]]
    if not alt_q:
        alt_q = ["cinematic reaction cutaway", "dramatic closeup", "slow motion detail"]
    return ScenePlan(
        index=index,
        narration="",
        duration=max(1.2, round(source.duration * 0.35, 2)),
        scene_description=f"Alternate angle cutaway: {desc}",
        beat_type=source.beat_type or "conflict",
        search_queries=alt_q,
    )


def _condense_narration(text: str, max_words: int) -> str:
    """Trim by whole sentences; compress oversized ones without mid-sentence cut (P0-01).
    Hard ceiling: never exceed max_words (Madde 494 TTS budget).
    """
    text = (text or "").strip()
    if not text or max_words <= 0:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return text

    parts = _split_sentences(text)
    if not parts:
        return _shorten_sentence(text, max_words)

    kept: List[str] = []
    count = 0
    for part in parts:
        pw = part.split()
        if count + len(pw) <= max_words:
            kept.append(part if part[-1] in ".!?" else _ensure_terminal(part))
            count += len(pw)
            continue
        remaining = max_words - count
        if remaining >= MIN_WORDS_PER_SCENE:
            short = _shorten_sentence(part, remaining)
            if short and len(short.split()) >= MIN_WORDS_PER_SCENE:
                kept.append(short)
        break

    out = " ".join(kept).strip()
    if not out:
        out = _shorten_sentence(text, max_words)

    if not out and text:
        from scenes.narration_validate import _append_minimal_completion
        out = _append_minimal_completion(_shorten_sentence(text, max(MIN_WORDS_PER_SCENE, max_words)))

    while out and len(out.split()) > max_words and len(kept) > 1:
        kept.pop()
        out = " ".join(kept).strip()
    if out and len(out.split()) > max_words:
        out = _shorten_sentence(out, max_words)

    return out


def _scene_word_count(scenes: List[ScenePlan]) -> int:
    return len(" ".join(
        s.narration.strip() for s in scenes if (s.narration or "").strip()
    ).split())


def _scenes_narration_ok(scenes: List[ScenePlan]) -> bool:
    return all(
        not scene_narration_issues(s.narration or "")
        for s in scenes
        if (s.narration or "").strip()
    )


def _drop_trailing_sentences_from_end(scenes: List[ScenePlan], n_words_to_drop: int) -> int:
    """Drop whole trailing sentences from end scenes. Returns words dropped."""
    dropped = 0
    while dropped < n_words_to_drop:
        found = False
        for s in reversed(scenes):
            narr = (s.narration or "").strip()
            if not narr:
                continue
            parts = _split_sentences(narr)
            if len(parts) <= 1:
                continue
            last_part_words = len(parts[-1].split())
            remaining = " ".join(parts[:-1]).strip()
            if len(remaining.split()) >= MIN_WORDS_PER_SCENE:
                s.narration = remaining
                dropped += last_part_words
                found = True
                break
        if not found:
            break
    return dropped


def _apply_word_budget(scenes: List[ScenePlan], max_words: int, min_scenes: int) -> None:
    """
    Fit narration into TTS word budget without mid-clause shredding (Madde 494).
    Prefer dropping trailing whole sentences / end scenes before per-scene shred.
    """
    total = _scene_word_count(scenes)
    if total <= max_words:
        return

    original = total
    overflow = total - max_words

    # Pass 1: drop trailing sentences from the end of the script
    _drop_trailing_sentences_from_end(scenes, overflow)

    # Pass 2: drop whole scenes from the tail when still over budget
    while _scene_word_count(scenes) > max_words and len(scenes) > min_scenes:
        scenes.pop()

    total = _scene_word_count(scenes)
    if total <= max_words:
        print(
            f"  [Timeline] Kelime butcesi: {original} -> {total} "
            f"(tavan {max_words}, Madde 494)"
        )
        return

    # Pass 3: trim longest scenes by dropping their trailing sentences first
    while _scene_word_count(scenes) > max_words:
        trimmed = False
        for s in sorted(scenes, key=lambda x: len((x.narration or "").split()), reverse=True):
            narr = (s.narration or "").strip()
            if not narr:
                continue
            words = narr.split()
            if len(words) <= MIN_WORDS_PER_SCENE:
                continue
            parts = _split_sentences(narr)
            if len(parts) > 1:
                remaining = " ".join(parts[:-1]).strip()
                if len(remaining.split()) >= MIN_WORDS_PER_SCENE:
                    s.narration = remaining
                    trimmed = True
                    break
            overflow_now = _scene_word_count(scenes) - max_words
            new_max = max(MIN_WORDS_PER_SCENE, len(words) - overflow_now)
            if new_max < len(words):
                condensed = _condense_narration(narr, new_max)
                if condensed and len(condensed.split()) >= MIN_WORDS_PER_SCENE:
                    s.narration = condensed
                    trimmed = True
                    break
        if not trimmed:
            break

    # Pass 4: proportional per-scene cap — floor MIN_WORDS_PER_SCENE, never mid-clause chop
    total = _scene_word_count(scenes)
    if total > max_words:
        tw = total
        for s in scenes:
            words = (s.narration or "").split()
            if not words:
                continue
            share = max(MIN_WORDS_PER_SCENE, int(round(max_words * (len(words) / tw))))
            if len(words) > share:
                s.narration = _condense_narration(s.narration, share)

        while _scene_word_count(scenes) > max_words:
            dropped = _drop_trailing_sentences_from_end(
                scenes, _scene_word_count(scenes) - max_words
            )
            if dropped <= 0:
                break

    final = _scene_word_count(scenes)
    print(
        f"  [Timeline] Kelime butcesi: {original} -> {final} "
        f"(tavan {max_words}, Madde 494)"
    )


def solve_timeline(plan: DirectorPlan) -> DirectorPlan:
    """
    Enforce 38-60s budget, flexible cadence (≥8 cuts), cadence acceleration, rebuild narration.
    Target follows narration length — never shrink a 55s script to 48.
    """
    qt = plan.quality_thresholds or QualityThresholds()
    scenes = list(plan.scenes)
    if not scenes:
        return plan
    word_n = _scene_word_count(scenes)
    target = natural_target_duration(word_n, qt.min_duration, qt.max_duration)
    qt.target_duration = target
    plan.quality_thresholds = qt

    # Ensure minimum cadence (Item 88) — never shred narration mid-sentence
    while len(scenes) < qt.min_scenes and scenes:
        longest = max(scenes, key=lambda s: len((s.narration or "").split()))
        left, right = _split_narration_near_mid(longest.narration or "")
        if left and right:
            longest.narration = left
            scenes.insert(
                scenes.index(longest) + 1,
                ScenePlan(
                    index=0,
                    narration=right,
                    duration=longest.duration,
                    scene_description=longest.scene_description,
                    beat_type=longest.beat_type or "conflict",
                ),
            )
        else:
            pad = _visual_pad_scene(longest, len(scenes))
            scenes.insert(scenes.index(longest) + 1, pad)

    # Turkish TTS ≈ 2.3–2.6 wps; only condense when over the 60s cap (Madde 494).
    max_words = shorts_word_budget(qt.max_duration, qt.max_audio_speed)
    total_w = _scene_word_count(scenes)
    if total_w <= max_words and _scenes_narration_ok(scenes):
        pass  # validated plan — preserve user-authored narrations
    elif total_w > max_words:
        _apply_word_budget(scenes, max_words, qt.min_scenes)

    # Cadence acceleration (Item 266)
    try:
        from viral_retention_engine import ViralRetentionEngine
        cadence = ViralRetentionEngine.calculate_cadence_acceleration(
            total_duration=target, scene_count=len(scenes)
        )
        story_arc = ViralRetentionEngine.build_shorts_story_arc_breakdown(duration=target)
    except Exception:
        n = len(scenes)
        weights = [1.0 - (0.5 * (i / max(1, n - 1))) for i in range(n)]
        sw = sum(weights) or 1.0
        cadence = [round((w / sw) * target, 2) for w in weights]
        story_arc = {"total_duration": target, "phases": []}

    plan.cadence_durations = cadence
    plan.story_arc = story_arc

    # Apply durations & time map
    t = 0.0
    for i, s in enumerate(scenes):
        s.index = i
        s.duration = float(cadence[i]) if i < len(cadence) else round(target / len(scenes), 2)
        s.t0 = round(t, 3)
        t = round(t + s.duration, 3)
        s.t1 = t

    # Normalize tiny float drift to exact target
    drift = target - t
    if scenes and abs(drift) > 0.01:
        scenes[-1].duration = round(scenes[-1].duration + drift, 3)
        scenes[-1].t1 = round(scenes[-1].t0 + scenes[-1].duration, 3)

    _assign_beat_types(scenes, target)
    plan.scenes = scenes
    plan.rebuild_full_narration()
    plan.time_map = {
        "target_duration": target,
        "scene_count": len(scenes),
        "cuts": [{"index": s.index, "t0": s.t0, "t1": s.t1, "beat": s.beat_type} for s in scenes],
        "max_audio_speed": qt.max_audio_speed,
    }
    return plan


def fit_tts_to_timeline(
    audio_path: str,
    plan: DirectorPlan,
    word_timings: Optional[List[Dict[str, Any]]] = None,
    output_path: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]], float, float]:
    """
    Fit narration audio to scene budget.
    Returns (audio_path, timings, audio_dur, speed_factor).
    Preferred speed ≤ quality_thresholds.max_audio_speed; emergency budget lock
    may go up to 1.35 so final Shorts stay inside max_duration (Item 494).
    If even 1.35× cannot fit the 60s cap, raises RuntimeError (hard-fail —
    never publish a 76s stretched Shorts). Natural TTS ≤ 60s is never sped up.
    """
    import wave
    import os

    qt = plan.quality_thresholds
    # Hard ceiling keeps videos inside Shorts band even when TTS overruns
    budget_ceiling = min(max(qt.max_duration, 60.0), 60.0)
    out = output_path or audio_path
    emergency_max_speed = TTS_EMERGENCY_MAX_SPEED

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
        t = 0.0
        for s in plan.scenes:
            s.duration = round(s.duration * scale, 3)
            s.t0 = round(t, 3)
            t = round(t + s.duration, 3)
            s.t1 = t

    # Natural TTS that already fits Shorts cap: never speed up to 42/45/48.
    if audio_dur <= qt.max_duration * 1.02:
        _rescale_scenes_to(audio_dur)
        return audio_path, word_timings or [], audio_dur, 1.0

    ratio = audio_dur / max(qt.max_duration, 0.01)
    if ratio > 1.0:
        from voice.audio_dsp import fit_audio_to_duration
        fitted = out if out != audio_path else audio_path.replace(".wav", "_fitted.wav")

        # Hard-fail early: raw TTS so long that 1.35× still exceeds Shorts band
        min_possible = audio_dur / emergency_max_speed
        if min_possible > budget_ceiling * 1.02:
            raise RuntimeError(
                f"Madde 494 hard-fail: TTS {audio_dur:.1f}s — even ×{emergency_max_speed} "
                f"yields ~{min_possible:.1f}s > {budget_ceiling:.0f}s. "
                f"Condense narration (≤~{shorts_word_budget(qt.max_duration, qt.max_audio_speed)} words) and re-render."
            )

        # Pass 1: preferred pace (Item 175-aligned ceiling)
        speed = min(ratio, qt.max_audio_speed)
        target_for_fit = audio_dur / speed
        path, new_dur, used = fit_audio_to_duration(audio_path, fitted, target_for_fit, tolerance=0.04)

        # Pass 2: if still outside Shorts band, emergency speed toward budget_ceiling
        # Always re-fit from the ORIGINAL wav — never ffmpeg in-place (path==fitted).
        if new_dur > budget_ceiling * 1.02:
            need_from_raw = audio_dur / budget_ceiling
            emergency_out = fitted.replace(".wav", "_emergency.wav")
            if need_from_raw <= emergency_max_speed + 0.01:
                path, new_dur, _used2 = fit_audio_to_duration(
                    audio_path, emergency_out, budget_ceiling, tolerance=0.04
                )
            else:
                cap_target = audio_dur / emergency_max_speed
                path, new_dur, _used2 = fit_audio_to_duration(
                    audio_path, emergency_out, cap_target, tolerance=0.04
                )
            used = audio_dur / max(new_dur, 0.01)
            print(
                f"  [Timeline] Budget lock emergency speed×{used:.2f} "
                f"-> {new_dur:.1f}s (hedef <={budget_ceiling:.0f}s, Madde 494)"
            )

        if new_dur > budget_ceiling * 1.05:
            raise RuntimeError(
                f"Madde 494 hard-fail: fitted audio {new_dur:.1f}s still outside "
                f"{qt.min_duration}-{budget_ceiling:.0f}s band (speed×{used:.2f}). "
                f"Refuse publish — re-condense script."
            )

        if word_timings and used > 1.01:
            for wt in word_timings:
                wt["offset"] = wt.get("offset", 0.0) / used
                wt["duration"] = wt.get("duration", 0.0) / used
        # Rescale scene durations to final audio (Item 129 ±0.05)
        _rescale_scenes_to(new_dur)
        return path, word_timings or [], new_dur, used

    # Audio shorter than scenes — shrink scenes to audio
    _rescale_scenes_to(audio_dur)
    return audio_path, word_timings or [], audio_dur, 1.0
