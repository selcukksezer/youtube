"""
Procedural BGM synth generation, trend hybrid profiles, niche BPM matching, and beat grid alignment.
"""
import math
import os
import re
import struct
import subprocess
import sys
import wave
import imageio_ffmpeg
import config


def _bgm_mod():
    return sys.modules.get("bgm_manager")


def _cfg():
    mod = _bgm_mod()
    return getattr(mod, "config", config) if mod else config


def ensure_royalty_free_ambient_bgm() -> str:
    """Item 135: Generates 100% royalty-free ambient background music."""
    cfg = _cfg()
    if not os.path.exists(cfg.BGM_DIR):
        os.makedirs(cfg.BGM_DIR, exist_ok=True)

    rf_path = os.path.join(cfg.BGM_DIR, "royalty_free_ambient.wav")
    if os.path.exists(rf_path):
        return rf_path

    sample_rate = 44100
    dur = 25.0
    num_samples = int(sample_rate * dur)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        chord1 = math.sin(2 * math.pi * 220.0 * t) * 0.4
        chord2 = math.sin(2 * math.pi * 277.18 * t) * 0.3
        chord3 = math.sin(2 * math.pi * 329.63 * t) * 0.3
        lfo = 0.85 + 0.15 * math.sin(2 * math.pi * 0.2 * t)
        val = (chord1 + chord2 + chord3) * 0.25 * lfo
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

    with wave.open(rf_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)

    return rf_path


def get_safe_default_bgm_path():
    """Item 135: Returns the bundled/generated royalty-free fallback track."""
    mod = _bgm_mod()
    fn = getattr(mod, "ensure_royalty_free_ambient_bgm", ensure_royalty_free_ambient_bgm)
    return fn()


TREND_HYBRID_PROFILES = (
    {
        "id": "viral_pulse",
        "label": "Viral Pulse (trend-energy)",
        "energy": "high",
        "moods": ("energetic", "epic", "dramatic"),
        "niche_hints": ("crypto", "football", "fitness", "gaming", "news", "affiliate"),
        "keywords": ("viral", "trending", "fyp", "kesfet"),
    },
    {
        "id": "lofi_feed",
        "label": "Lo-Fi Feed Scroll",
        "energy": "mid",
        "moods": ("lofi", "ambient", "calm"),
        "niche_hints": ("stoic", "religious", "poetry", "language", "parenting", "dream"),
        "keywords": ("calm", "study", "lofi"),
    },
    {
        "id": "dark_tension",
        "label": "Dark Tension Hook",
        "energy": "mid_high",
        "moods": ("mysterious", "dramatic"),
        "niche_hints": ("mystery", "psychology", "history", "sigma", "legal"),
        "keywords": ("dark", "tension", "thriller"),
    },
)


def list_trend_hybrid_profiles() -> list:
    """R10 #87: Curated trend-energy BGM profiles (copyright-safe)."""
    return [dict(p) for p in TREND_HYBRID_PROFILES]


def select_trend_hybrid_bgm(
    niche_id: str = "",
    topic: str = "",
    preferred_mood: str = "",
) -> dict:
    """R10 #87: Pick a royalty-free BGM path that matches current 'trend energy' for the niche."""
    mod = _bgm_mod()
    list_fn = getattr(mod, "list_bgm_tracks")
    path_fn = getattr(mod, "get_bgm_path")
    safe_fn = getattr(mod, "get_safe_default_bgm_path", get_safe_default_bgm_path)

    nid = (niche_id or "").lower()
    topic_l = (topic or "").lower()
    mood = (preferred_mood or "").lower()
    chosen = TREND_HYBRID_PROFILES[1]
    for profile in TREND_HYBRID_PROFILES:
        hints = profile["niche_hints"]
        if any(h in nid for h in hints) or any(h in topic_l for h in hints):
            chosen = profile
            break
        if mood and mood in profile["moods"]:
            chosen = profile
            break

    tracks = list_fn(include_catalog=True)
    mood_terms = list(chosen["moods"])
    match = None
    for t in tracks:
        low = t.lower()
        if any(m in low for m in mood_terms):
            match = t
            break
    path = path_fn(match) if match else None
    if not path:
        path = safe_fn()
        match = os.path.basename(path) if path else ""
    return {
        "rule": "r10_87_trend_hybrid",
        "profile_id": chosen["id"],
        "label": chosen["label"],
        "energy": chosen["energy"],
        "track": match,
        "path": path,
        "note": (
            "YouTube Trend Sounds listesi API ile kapalı; telifsiz katalogda "
            "trend-enerji profili seçildi. Operatör Studio'da trend sesi manuel ekleyebilir."
        ),
    }


NICHE_BPM_RANGES = {
    "motivation": (120, 130),
    "fitness": (120, 130),
    "success": (120, 130),
    "philosophy": (70, 85),
    "stoic": (70, 85),
    "mystery": (70, 85),
    "horror": (70, 85),
    "quiz": (115, 128),
    "trivia": (115, 128),
    "finance": (105, 120),
    "tech": (120, 135),
    "technology": (120, 135),
    "history": (75, 90),
    "default": (90, 115),
}


def get_niche_target_bpm(niche_id: str) -> tuple:
    """Madde 169: Kategoriye göre önerilen BPM aralığını döndürür."""
    normalized = str(niche_id or "").lower().strip()
    for k, (min_bpm, max_bpm) in NICHE_BPM_RANGES.items():
        if k in normalized:
            return (min_bpm, max_bpm)
    return NICHE_BPM_RANGES["default"]


def match_bgm_track_to_niche(niche_id: str, available_tracks: list = None) -> str:
    """Madde 169: Belirtilen nişe uygun BPM ve atmosferdeki parçayı seçer veya döndürür."""
    mod = _bgm_mod()
    path_fn = getattr(mod, "get_bgm_path")
    list_fn = getattr(mod, "list_bgm_tracks")
    ambient_fn = getattr(mod, "ensure_royalty_free_ambient_bgm", ensure_royalty_free_ambient_bgm)

    try:
        from youtube_safe_bgm_catalog import pick_catalog_bgm_for_niche
        fn = pick_catalog_bgm_for_niche(niche_id)
        if fn:
            path = path_fn(fn)
            if path:
                return path
    except Exception:
        pass

    min_bpm, max_bpm = get_niche_target_bpm(niche_id)
    target_mid = (min_bpm + max_bpm) / 2.0

    tracks = available_tracks or list_fn()
    if not tracks:
        return ambient_fn()

    try:
        from youtube_safe_bgm_catalog import load_catalog
        catalog_by_fn = {t["filename"]: t for t in load_catalog()}
    except Exception:
        catalog_by_fn = {}

    best_track = None
    best_diff = 999.0

    for track in tracks:
        base = os.path.basename(track.replace("\\", "/"))
        meta = catalog_by_fn.get(base, {})
        est_bpm = float(meta.get("bpm") or 100.0)
        if not meta:
            fname = base.lower()
            if any(k in fname for k in ("motivation", "fitness", "energetic", "drill", "phonk")):
                est_bpm = 125.0
            elif any(k in fname for k in ("philosophy", "stoic", "mystery", "calm", "lofi", "ambient")):
                est_bpm = 78.0
            elif any(k in fname for k in ("quiz", "game", "ticking")):
                est_bpm = 120.0
            elif any(k in fname for k in ("history", "epic", "dramatic")):
                est_bpm = 85.0

        diff = abs(est_bpm - target_mid)
        if diff < best_diff:
            best_diff = diff
            best_track = track

    if best_track:
        return path_fn(best_track) or ambient_fn()
    return ambient_fn()


def synthesize_niche_tempo_bgm(niche_id: str, duration: float = 25.0, output_path: str = None) -> str:
    """Madde 169: Nişin BPM aralığına tam kilitli harmonik arka plan ambient ritim parçası sentezler."""
    cfg = _cfg()
    min_bpm, max_bpm = get_niche_target_bpm(niche_id)
    bpm = (min_bpm + max_bpm) / 2.0

    if not output_path:
        sanitized = str(niche_id or "ambient").replace("/", "_").lower()
        output_path = os.path.join(cfg.BGM_DIR, f"bgm_{sanitized}_{int(bpm)}bpm.wav")

    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    beat_sec = 60.0 / bpm
    is_energetic = bpm >= 115.0
    base_f1 = 130.81 if is_energetic else 146.83
    base_f2 = 196.00 if is_energetic else 174.61
    base_f3 = 329.63 if is_energetic else 220.00

    for i in range(num_samples):
        t = i / sample_rate
        phase_in_beat = (t % beat_sec) / beat_sec
        pulse_env = math.exp(-phase_in_beat * (6.0 if is_energetic else 3.5))
        chord = (
            math.sin(2 * math.pi * base_f1 * t) * 0.45
            + math.sin(2 * math.pi * base_f2 * t) * 0.35
            + math.sin(2 * math.pi * base_f3 * t) * 0.25
        )
        sub_kick = math.sin(2 * math.pi * (65.0 if is_energetic else 48.0) * t) * pulse_env * 0.4
        val = max(-1.0, min(1.0, (chord * 0.4 + sub_kick) * 0.65))
        frames.extend(struct.pack('<h', int(val * 32767)))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"  [Item 169] Niş BPM ({bpm:.1f} BPM, {niche_id}) BGM parçası sentezlendi → {output_path}")
    return output_path


def parse_bgm_bpm(bgm_path: str = "", default_bpm: float = 120.0) -> float:
    """P2-21: Derive BPM from track filename (advisory beat grid)."""
    if not bgm_path:
        return default_bpm
    fname = os.path.basename(bgm_path)
    try:
        from youtube_safe_bgm_catalog import track_by_filename
        meta = track_by_filename(fname)
        if meta and meta.get("bpm"):
            return float(meta["bpm"])
    except Exception:
        pass
    fname = fname.lower()
    if any(k in fname for k in ("lofi", "calm", "philosophy", "stoic", "mystery")):
        return 78.0
    if any(k in fname for k in ("dramatic", "history", "epic")):
        return 85.0
    if any(k in fname for k in ("motivation", "fitness", "energetic", "drill", "phonk")):
        return 125.0
    if any(k in fname for k in ("quiz", "news")):
        return 120.0
    return default_bpm


def normalize_bpm_to_shorts_band(bpm: float, min_bpm: float = 80.0, max_bpm: float = 120.0) -> float:
    """Bölüm 7.3: Shorts hipnotik kurgu temposu için BPM'i 80-120 aralığına normalize eder."""
    try:
        val = float(bpm) if bpm is not None else 100.0
    except (ValueError, TypeError):
        val = 100.0
    if val <= 1.0:
        return 100.0
    if min_bpm <= val <= max_bpm:
        return round(val, 1)
    doubled = val * 2.0
    if min_bpm <= doubled <= max_bpm:
        return round(doubled, 1)
    halved = val / 2.0
    if min_bpm <= halved <= max_bpm:
        return round(halved, 1)
    return round(val, 1)


def detect_audio_bpm_and_beats(
    audio_path: str,
    duration: float = 60.0,
    default_bpm: float = 120.0,
    enforce_band: bool = True,
) -> tuple[float, list]:
    """Detects real beats and BPM from audio file via FFmpeg ebur128 momentary loudness peaks."""
    raw_bpm = parse_bgm_bpm(audio_path, default_bpm=default_bpm)
    actual_beats: list[float] = []

    if audio_path and os.path.isfile(audio_path):
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [ffmpeg_exe, "-hide_banner", "-i", audio_path, "-af", "ebur128", "-f", "null", "-"]
            res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore", timeout=8)
            M = []
            for line in res.stderr.splitlines():
                m = re.search(r"M:\s*(-?[\d.]+|-?inf)", line)
                if m:
                    v = m.group(1)
                    M.append(-70.0 if "inf" in v else float(v))

            if len(M) >= 20:
                peaks = [
                    i for i in range(1, len(M) - 1)
                    if M[i] > M[i - 1] and M[i] >= M[i + 1] and M[i] > -42.0
                ]
                if len(peaks) >= 4:
                    actual_beats = [round(p * 0.1, 3) for p in peaks if p * 0.1 <= duration + 0.05]
                    dur_span = (peaks[-1] - peaks[0]) * 0.1
                    if dur_span > 1.0:
                        measured_bpm = (len(peaks) - 1) / dur_span * 60.0
                        if 40.0 <= measured_bpm <= 220.0:
                            raw_bpm = measured_bpm
        except Exception:
            pass

    final_bpm = normalize_bpm_to_shorts_band(raw_bpm) if enforce_band else raw_bpm
    if len(actual_beats) < 4:
        beat_interval = 60.0 / final_bpm
        actual_beats = []
        curr = beat_interval
        while curr <= duration + 0.05:
            actual_beats.append(round(curr, 3))
            curr += beat_interval

    return final_bpm, actual_beats


def compute_scene_beat_hints(
    scenes: list,
    bgm_path: str = None,
    bpm: float = None,
    enforce_band: bool = False,
) -> list:
    """P2-21 & Bölüm 7.3: Advisory beat-aligned cut hints."""
    if not scenes:
        return []
    used_bpm = float(bpm) if bpm is not None else parse_bgm_bpm(bgm_path or "")
    if enforce_band:
        used_bpm = normalize_bpm_to_shorts_band(used_bpm)

    beat_interval_ms = (60.0 / used_bpm) * 1000.0
    total_ms = sum(
        float(getattr(s, "duration", None) or (s.get("duration") if isinstance(s, dict) else 3.0)) * 1000.0
        for s in scenes
    ) + 10000.0
    beats_ms = []
    curr = beat_interval_ms
    while curr < total_ms:
        beats_ms.append(round(curr, 1))
        curr += beat_interval_ms

    hints = []
    accum_ms = 0.0
    for sc in scenes:
        dur_s = float(getattr(sc, "duration", None) or (sc.get("duration") if isinstance(sc, dict) else 3.0))
        target_ms = accum_ms + dur_s * 1000.0
        if beats_ms:
            closest = min(beats_ms, key=lambda b: abs(b - target_ms))
            hints.append({
                "beat_hint_ms": round(closest, 1),
                "suggested_cut_ms": round(closest, 1),
                "actual_cut_ms": round(target_ms, 1),
                "delta_ms": round(closest - target_ms, 1),
                "bpm": used_bpm,
            })
        else:
            hints.append({"beat_hint_ms": round(target_ms, 1), "bpm": used_bpm})
        accum_ms = target_ms
    return hints


def snap_durations_to_bpm(durations, bpm, total=None, min_dur=2.0, enforce_band=True):
    """Move each cut except the last onto the nearest beat."""
    durs = [float(d) for d in durations]
    if len(durs) < 2:
        return durs
    bpm_val = float(bpm) if bpm and float(bpm) > 1 else 100.0
    if enforce_band:
        bpm_val = normalize_bpm_to_shorts_band(bpm_val)
    beat = 60.0 / bpm_val
    total = float(sum(durs) if total is None else total)
    acc = 0.0
    out = []
    for dur in durs[:-1]:
        target = acc + dur
        snapped = round(target / beat) * beat
        new_dur = snapped - acc
        if new_dur < min_dur:
            new_dur = dur
        out.append(round(new_dur, 3))
        acc = round(acc + out[-1], 3)
    last = round(total - acc, 3)
    if last < min_dur and out and out[-1] - (min_dur - last) >= min_dur:
        need = round(min_dur - last, 3)
        out[-1] = round(out[-1] - need, 3)
        acc = round(acc - need, 3)
        last = round(total - acc, 3)
    out.append(last)
    drift = round(total - sum(out), 3)
    out[-1] = round(out[-1] + drift, 3)
    return out


def snap_timeline_to_beat_grid(
    scenes: list,
    bgm_path: str = "",
    bpm: float = None,
    min_scene_dur: float = 1.8,
    max_scene_dur: float = 7.0,
    enforce_band: bool = True,
) -> list:
    """Bölüm 7.3: Sahne geçişlerini 80-120 BPM müzik ritmine kilitler (Beat Snapping)."""
    if not scenes:
        return scenes

    total_time = sum(
        float(getattr(s, "duration", None) or (s.get("duration") if isinstance(s, dict) else 3.0))
        for s in scenes
    )
    if bpm is not None:
        final_bpm = normalize_bpm_to_shorts_band(bpm) if enforce_band else float(bpm)
        beat_interval = 60.0 / final_bpm
        beats = [round(i * beat_interval, 3) for i in range(1, int((total_time + 15.0) / beat_interval) + 1)]
    else:
        final_bpm, beats = detect_audio_bpm_and_beats(bgm_path, duration=total_time, enforce_band=enforce_band)

    if not beats:
        return scenes

    is_dict = isinstance(scenes[0], dict)
    out_scenes = []
    accum = 0.0

    avg_scene_dur = total_time / max(1, len(scenes))
    for idx, sc in enumerate(scenes):
        orig_dur = float(getattr(sc, "duration", None) or (sc.get("duration") if is_dict else 3.0))
        narr = str(getattr(sc, "narration", None) or (sc.get("narration") if is_dict else "") or "")
        word_count = len(narr.split())
        min_speech_s = max(min_scene_dur, (word_count * 0.30) + 0.15) if word_count > 0 else min_scene_dur
        scene_max_dur = max(max_scene_dur, orig_dur + 0.6, avg_scene_dur * 1.18)

        if idx < len(scenes) - 1:
            target_cut = accum + orig_dur
            closest_beat = min(beats, key=lambda b: abs(b - target_cut))
            new_dur = closest_beat - accum

            if new_dur < min_speech_s:
                next_beats = [b for b in beats if b - accum >= min_speech_s]
                if next_beats:
                    closest_beat = min(next_beats, key=lambda b: abs(b - (accum + min_speech_s)))
                    new_dur = closest_beat - accum
                else:
                    new_dur = max(min_speech_s, orig_dur)
                    closest_beat = accum + new_dur

            if new_dur > scene_max_dur:
                prev_beats = [b for b in beats if accum + min_speech_s <= b <= accum + scene_max_dur]
                if prev_beats:
                    closest_beat = max(prev_beats)
                    new_dur = closest_beat - accum
                else:
                    new_dur = scene_max_dur
                    closest_beat = accum + new_dur

            new_dur = round(max(min_scene_dur, new_dur), 3)
            actual_cut = round(accum + new_dur, 3)
            delta_ms = round((closest_beat - actual_cut) * 1000.0, 1)
        else:
            rem_dur = total_time - accum
            cap_last = max(scene_max_dur, min_speech_s, orig_dur * 1.2)
            new_dur = round(max(min_scene_dur, min(rem_dur, cap_last)), 3)
            actual_cut = round(accum + new_dur, 3)
            delta_ms = 0.0

        if is_dict:
            new_sc = dict(sc)
            new_sc["duration"] = new_dur
            new_sc["t0"] = round(accum, 3)
            new_sc["t1"] = round(accum + new_dur, 3)
            new_sc["beat_synced"] = True
            new_sc["beat_hint_ms"] = round(actual_cut * 1000.0, 1)
            new_sc["suggested_cut_ms"] = round(actual_cut * 1000.0, 1)
            new_sc["delta_ms"] = delta_ms
            new_sc["bpm"] = final_bpm
            out_scenes.append(new_sc)
        else:
            sc.duration = new_dur
            sc.t0 = round(accum, 3)
            sc.t1 = round(accum + new_dur, 3)
            sc.beat_synced = True
            sc.beat_hint_ms = round(actual_cut * 1000.0, 1)
            out_scenes.append(sc)

        accum = round(accum + new_dur, 3)

    return out_scenes


def detect_bgm_bpm_and_beats(bgm_path: str, duration: float = 60.0, default_bpm: float = 120.0) -> list:
    """Item 102 & 169: BGM Beat-Syncing (Ritim Tespiti)."""
    _, beats = detect_audio_bpm_and_beats(bgm_path, duration=duration, default_bpm=default_bpm, enforce_band=False)
    return beats


def align_scenes_to_bgm_beats(scenes: list, bgm_path: str) -> list:
    """Item 102 & Bölüm 7.3: BGM Beat-Syncing Sahne Kesimi."""
    if not scenes or not bgm_path:
        return scenes
    return snap_timeline_to_beat_grid(scenes, bgm_path=bgm_path, enforce_band=False)
