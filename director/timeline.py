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
    natural_narration_word_cap,
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
    while len(trimmed) > MIN_WORDS_PER_SENTENCE and trimmed[-1].lower().rstrip(".,!?") in _DANGLING_END_WORDS:
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
    if len(chunk) >= MIN_WORDS_PER_SENTENCE:
        done = _ensure_terminal(" ".join(chunk))
        bad = set(scene_narration_issues(done))
        if not bad & {"dangling_tail", "dangling_sentence", "fragment_ending", "fragment_sentence", "no_terminal"}:
            return done
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


# 110 spoken words cannot carry 8–14 full sentences. 4–6 scenes, or fewer
# when the script has fewer complete sentences. Never split one sentence
# in half to fill the count.
SPOKEN_SCENE_MIN = 6
SPOKEN_SCENE_MAX = 15
_BARE_CONJUNCTIONS = frozenset({"ve", "ama", "çünkü", "cunku", "fakat"})


def _bare_conjunction(text: str) -> bool:
    words = [
        w.strip(".,!?;:\"'“”").lower()
        for w in (text or "").split()
        if w.strip(".,!?;:\"'“”")
    ]
    return len(words) == 1 and words[0] in _BARE_CONJUNCTIONS


def _clean_spoken_sentence(text: str) -> str:
    """Keep a finished sentence. Drop a bare conjunction. Do not invent a tail."""
    from scenes.narration_validate import _strip_dangling_clause

    raw = (text or "").strip()
    if not raw:
        return ""
    parts = _split_sentences(raw)
    if not parts:
        return ""
    kept: List[str] = []
    for part in parts:
        if part[-1:] not in ".!?":
            continue
        cleaned, _did = _strip_dangling_clause(part)
        cleaned = (cleaned or "").strip()
        if not cleaned or _bare_conjunction(cleaned):
            continue
        done = cleaned if cleaned[-1:] in ".!?" else _ensure_terminal(cleaned)
        bad = set(scene_narration_issues(done)) & {
            "dangling_tail",
            "dangling_sentence",
            "fragment_ending",
            "no_terminal",
        }
        if bad:
            continue
        kept.append(done)
    return " ".join(kept)


def _pending_spoken_ready(text: str) -> str:
    """Return cleaned speech only when the buffer ends on a finished sentence."""
    raw = (text or "").strip()
    if not raw:
        return ""
    parts = _split_sentences(raw)
    if not parts or parts[-1][-1:] not in ".!?":
        return ""
    return _clean_spoken_sentence(raw)


def _fit_spoken_scene_count(scenes: List[ScenePlan]) -> None:
    """
    Merge or drop until each remaining scene is a complete spoken sentence
    and the count is 4–6. A half sentence is not split further to hit 4.
    """
    units: List[Tuple[ScenePlan, str]] = []
    pending = ""
    pending_scene: Optional[ScenePlan] = None
    for scene in scenes:
        piece = (scene.narration or "").strip()
        if not piece or _bare_conjunction(piece):
            continue
        pending = f"{pending} {piece}".strip() if pending else piece
        if pending_scene is None:
            pending_scene = scene
        cleaned = _pending_spoken_ready(pending)
        if cleaned:
            units.append((pending_scene, cleaned))
            pending = ""
            pending_scene = None
    if pending and pending_scene is not None:
        cleaned = _pending_spoken_ready(pending)
        if cleaned:
            units.append((pending_scene, cleaned))
    if not units:
        return

    count = len(units)
    buckets = count if count < SPOKEN_SCENE_MIN else min(SPOKEN_SCENE_MAX, count)
    base, extra = divmod(count, buckets)
    grouped: List[List[Tuple[ScenePlan, str]]] = []
    cursor = 0
    for index in range(buckets):
        take = base + (1 if index < extra else 0)
        grouped.append(units[cursor:cursor + take])
        cursor += take

    fitted: List[ScenePlan] = []
    for group in grouped:
        if not group:
            continue
        head = group[0][0]
        head.narration = " ".join(narr for _scene, narr in group if narr).strip()
        fitted.append(head)
    if not fitted:
        return
    before = len(scenes)
    scenes[:] = fitted
    if before != len(scenes):
        print(
            f"  [Timeline] Sahne sayısı söz bütçesine indi: {before} -> {len(scenes)} "
            f"(tavan {SPOKEN_SCENE_MAX}, tam cümle)"
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
    Enforce 38-60s budget and a spoken scene count that fits the word cap.
    At or under ~110 words the plan is 4–6 complete scenes, not 8–14 cuts.
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

    # Turkish TTS ≈ 2.3–2.6 wps; only condense when over the 60s cap (Madde 494).
    # Drop whole scenes down to 4 before any per-scene trim. Do not split a
    # sentence to manufacture an 8-cut cadence.
    max_words = shorts_word_budget(qt.max_duration, qt.max_audio_speed)
    total_w = _scene_word_count(scenes)
    if total_w <= max_words and _scenes_narration_ok(scenes):
        pass  # validated plan — preserve user-authored narrations
    elif total_w > max_words:
        _apply_word_budget(scenes, max_words, SPOKEN_SCENE_MIN)

    if _scene_word_count(scenes) <= max_words:
        _fit_spoken_scene_count(scenes)
        spoken_n = len(scenes)
        floor = spoken_n if spoken_n < SPOKEN_SCENE_MIN else SPOKEN_SCENE_MIN
        qt.min_scenes = min(qt.min_scenes, max(1, floor))

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


def _plan_dict_word_count(scenes: List[dict]) -> int:
    return sum(len((s.get("narration") or "").split()) for s in scenes)


def _settle_spoken_sentence(text: str, max_words: int) -> str:
    """Finish or drop a clipped clause. Never return a dangling tail."""
    from scenes.narration_validate import (
        _append_minimal_completion,
        _strip_dangling_clause,
        scene_narration_issues,
    )

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
    if short:
        finished = _append_minimal_completion(short)
        if (
            finished
            and not scene_narration_issues(finished)
            and len(finished.split()) <= max_words
        ):
            return finished
    stripped, _did = _strip_dangling_clause(text)
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
    import copy

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
        words = len(str(plan.get("full_narration") or "").split())
    cap = natural_narration_word_cap(words, audio_seconds)
    if words <= cap:
        import copy
        intact = copy.deepcopy(plan or {})
        return intact
    return condense_plan_narration(plan, cap)


def fit_tts_to_timeline(
    audio_path: str,
    plan: DirectorPlan,
    word_timings: Optional[List[Dict[str, Any]]] = None,
    output_path: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]], float, float]:
    """
    Fit narration audio to scene budget.
    Returns (audio_path, timings, audio_dur, speed_factor).
    Natural pace only. Speech over the 60s cap is not sped up (no 1.35×).
    The caller condenses narration and runs TTS once. A second over-long
    take raises RuntimeError (Madde 494).
    """
    import wave
    import os

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

    # Natural TTS inside the Shorts cap: never speed up.
    if audio_dur <= budget_ceiling + 0.5:
        _rescale_scenes_to(audio_dur)
        return audio_path, word_timings or [], audio_dur, 1.0

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

