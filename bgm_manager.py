"""
Background Music (BGM) Manager for Shorts Video Creator.
"""
import os, subprocess
from collections import OrderedDict
from typing import Optional
import imageio_ffmpeg
import config

# Item 432: LRU RAM cache for hot BGM/SFX paths (avoid repeated disk stat during batch render)
_BGM_RAM_CACHE: OrderedDict = OrderedDict()
_BGM_CACHE_MAX = int(os.getenv("BGM_RAM_CACHE_MAX", "12"))


def cache_bgm_file(path: Optional[str]) -> Optional[str]:
    """Item 432: Touch LRU cache entry for a resolved BGM path."""
    if not path or not os.path.isfile(path):
        return path
    key = os.path.abspath(path)
    _BGM_RAM_CACHE[key] = os.path.getmtime(key)
    _BGM_RAM_CACHE.move_to_end(key)
    while len(_BGM_RAM_CACHE) > _BGM_CACHE_MAX:
        _BGM_RAM_CACHE.popitem(last=False)
    return path


def get_cached_bgm_path(track_name: str = "") -> str:
    """Item 432: Resolve BGM path through LRU cache (default safe track when empty)."""
    path = get_bgm_path(track_name) if track_name else None
    if not path:
        path = get_safe_default_bgm_path()
    return cache_bgm_file(path) or path


def clear_bgm_ram_cache() -> None:
    """Clear Item 432 LRU cache (tests / settings reload)."""
    _BGM_RAM_CACHE.clear()

def list_bgm_tracks(include_catalog: bool = False):
    """Returns audio filenames in BGM_DIR (+ optional catalog entries not yet downloaded)."""
    if not os.path.exists(config.BGM_DIR):
        os.makedirs(config.BGM_DIR, exist_ok=True)

    exts = ('.mp3', '.wav', '.m4a', '.aac', '.ogg')
    tracks = [f for f in os.listdir(config.BGM_DIR) if f.lower().endswith(exts)]

    studio_dir = os.path.join(config.BGM_DIR, "youtube_studio")
    if os.path.isdir(studio_dir):
        for f in os.listdir(studio_dir):
            if f.lower().endswith(exts):
                tracks.append(f"youtube_studio/{f}")

    if include_catalog:
        try:
            from youtube_safe_bgm_catalog import load_catalog
            for t in load_catalog():
                fn = t.get("filename")
                if fn and fn not in tracks:
                    tracks.append(fn)
        except Exception:
            pass

    if not tracks:
        ensure_royalty_free_ambient_bgm()
        tracks = [f for f in os.listdir(config.BGM_DIR) if f.lower().endswith(exts)]
    return sorted(set(tracks))


def list_bgm_tracks_detailed(include_catalog: bool = True) -> list:
    """Returns track dicts with display labels for API/UI."""
    try:
        from youtube_safe_bgm_catalog import get_display_label, list_catalog_entries, load_catalog
    except Exception:
        return [{"filename": f, "display": f, "downloaded": True} for f in list_bgm_tracks()]

    seen = set()
    out = []
    for entry in list_catalog_entries(include_studio=True):
        fn = entry.get("filename", "")
        if not fn or fn in seen:
            continue
        seen.add(fn)
        path = os.path.join(config.BGM_DIR, fn)
        studio_path = os.path.join(config.BGM_DIR, "youtube_studio", os.path.basename(fn))
        downloaded = os.path.isfile(path) or os.path.isfile(studio_path)
        if include_catalog or downloaded:
            out.append({
                "filename": fn,
                "display": entry.get("display") or get_display_label(fn),
                "title": entry.get("title"),
                "mood": entry.get("mood"),
                "genre": entry.get("genre"),
                "bpm": entry.get("bpm"),
                "downloaded": downloaded,
                "source": entry.get("source"),
            })

    for f in list_bgm_tracks():
        if f not in seen and not f.startswith("youtube_studio/"):
            out.append({
                "filename": f,
                "display": get_display_label(f),
                "downloaded": True,
                "source": "local",
            })
    return out

def ensure_royalty_free_ambient_bgm() -> str:
    """
    Item 135: Telifli Müziklerden Kaçınma.
    Telif korumalı popüler ticari müzikler yerine YouTube Audio Library veya
    matematiksel harmoniklerle üretilmiş %100 telifsiz ambient arka plan müziği sağlar.
    """
    if not os.path.exists(config.BGM_DIR):
        os.makedirs(config.BGM_DIR, exist_ok=True)

    rf_path = os.path.join(config.BGM_DIR, "royalty_free_ambient.wav")
    if os.path.exists(rf_path):
        return rf_path

    import math, wave, struct
    sample_rate = 44100
    dur = 25.0
    num_samples = int(sample_rate * dur)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        # Peaceful ambient major triad: A3 (220Hz), C#4 (277.18Hz), E4 (329.63Hz)
        chord1 = math.sin(2 * math.pi * 220.0 * t) * 0.4
        chord2 = math.sin(2 * math.pi * 277.18 * t) * 0.3
        chord3 = math.sin(2 * math.pi * 329.63 * t) * 0.3
        # LFO slow breathing pulse
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

def get_bgm_path(track_name):
    """Returns full path of a BGM track if it exists."""
    if not track_name:
        return None
    safe = track_name.replace("\\", "/")
    if safe.startswith("youtube_studio/"):
        full_path = os.path.join(config.BGM_DIR, safe)
    else:
        full_path = os.path.join(config.BGM_DIR, os.path.basename(safe))
    if os.path.exists(full_path):
        return cache_bgm_file(full_path)
    studio = os.path.join(config.BGM_DIR, "youtube_studio", os.path.basename(safe))
    if os.path.exists(studio):
        return cache_bgm_file(studio)
    return None

def get_safe_default_bgm_path():
    """Item 135: Returns the bundled/generated royalty-free fallback track."""
    return ensure_royalty_free_ambient_bgm()

def mix_narration_and_bgm(narration_path, bgm_path, output_path, volume=0.12, tape_stop_times=None, allow_fade_out: bool = False):
    """
    Mixes narration audio with background music using ffmpeg.
    Loops BGM if shorter than narration, trims BGM if longer.
    Item 144: Uses narration sidechain ducking so music drops within 80ms
    while speech is present and returns within 200ms after speech ends.
    Item 153: Keeps narration center-mono while widening only the music bed.
    Item 166: Kapanış Müzik Sönümlemesi (Fade-Out Yok!).
    Shorts videolarında müziğe asla fade-out verilmez (dropout_transition=0.0);
    fade-out döngüyü bozar, müzik video bitişinde aniden başa dönecek şekilde kesilir.
    """
    if not bgm_path or not os.path.exists(bgm_path):
        return narration_path

    tape_stop_times = tape_stop_times or []
    mute_windows = "+".join(
        f"between(t,{max(0.0, time_point):.3f},{time_point + 0.4:.3f})" for time_point in tape_stop_times
    )
    mute_filter = f",volume=enable='{mute_windows}':volume=0" if mute_windows else ""
    dropout_val = 0.2 if allow_fade_out else 0.0

    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y",
        "-i", narration_path,

        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex",
        (
            "[0:a]pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,asplit=2[narr_sc][narr_mix];"
            f"[1:a]volume={volume},stereowiden=delay=20:feedback=0.25:crossfeed=0.2:drymix=0.8,equalizer=f=2000:t=q:w=1.0:g=-4.5{mute_filter}[bgm_wide];"
            "[bgm_wide][narr_sc]sidechaincompress=threshold=0.025:ratio=12:attack=80:release=200[ducked];"
            f"[narr_mix][ducked]amix=inputs=2:duration=first:dropout_transition={dropout_val}:normalize=0[aout]"
        ),
        "-map", "[aout]",
        "-c:a", "pcm_s16le",
        output_path
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and os.path.exists(output_path):
        fade_status = "Fade-Out Yok (Döngü Korundu, Madde 166)" if not allow_fade_out else "Fade-Out İzinli"
        print(f"  [BGM] Mixed {os.path.basename(bgm_path)} with center narration, stereo-wide music, vocal carve EQ @ 2kHz (-4.5dB, Madde 200), 80ms/200ms ducking ({fade_status})")
        return output_path
    else:
        print(f"  [BGM] Warning: BGM mixing failed, using plain narration: {res.stderr.decode('utf-8', errors='ignore')[:200]}")
        return narration_path


# ─── ITEM 200: Ses Frekans Çakışmasını Önleme (Vocal Frequency Carving @ 1-3kHz) ─

def apply_vocal_carve_eq(music_wav: str, output_wav: str,
                         notch_freq: float = 2000.0,
                         notch_gain: float = -4.5,
                         q_width: float = 1.0) -> str:
    """
    Madde 200: Ses Frekans Çakışmasını Önleme (Vocal Frequency Carving).
    Müzikteki vokal frekansları (1kHz - 3kHz aralığı) parametrik EQ ile oyularak
    anlatıcının konuşma sesine berrak bir alan açar.
    """
    from voice.audio_dsp import apply_vocal_carve_eq as _dsp_vocal_carve
    return _dsp_vocal_carve(music_wav, output_wav, notch_freq, notch_gain, q_width)


# ─── ITEM 166: Kapanış Müzik Sönümlemesi (Fade-Out Yok! Keskin Döngü Kesimi) ───

def apply_seamless_loop_cut(bgm_path: str, output_path: str, duration: float) -> str:
    """
    Madde 166: Kapanış Müzik Sönümlemesi (Fade-Out Yok!).
    Shorts videolarında müziğe asla fade-out verilmemelidir; fade-out döngüyü bozar.
    Müzik döngüsü aniden başa dönmeli, enerji son milisaniyeye kadar korunmalıdır.
    """
    if not os.path.exists(bgm_path):
        return bgm_path

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        # atrim ile tam duration anında sıfır fade-out ile kesim yapılır
        cmd = [
            ffmpeg_exe, "-y",
            "-stream_loop", "-1",
            "-i", bgm_path,
            "-af", f"atrim=0:{max(0.1, duration):.3f},asetpts=PTS-STARTPTS",
            "-c:a", "pcm_s16le",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_path):
            print(f"  [Item 166] Müzik sönümleme engellendi (Fade-Out Yok, Keskin Döngü): {duration:.2f}s → {output_path}")
            return output_path
    except Exception as e:
        print(f"  [Item 166] Seamless loop cut hatası: {e}")

    return bgm_path


# ─── ITEM 169: Müzik BPM Eşleştirmesi (Niche Temposu) ─────────────────────────

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
    "default": (90, 115)
}


def get_niche_target_bpm(niche_id: str) -> tuple:
    """
    Madde 169: Kategoriye göre önerilen BPM aralığını döndürür.
    Motivasyon: 120-130 BPM | Felsefe/Gizem: 70-85 BPM
    """
    normalized = str(niche_id or "").lower().strip()
    for k, (min_bpm, max_bpm) in NICHE_BPM_RANGES.items():
        if k in normalized:
            return (min_bpm, max_bpm)
    return NICHE_BPM_RANGES["default"]


def match_bgm_track_to_niche(niche_id: str, available_tracks: list = None) -> str:
    """
    Madde 169: Belirtilen nişe uygun BPM ve atmosferdeki parçayı seçer veya döndürür.
    """
    try:
        from youtube_safe_bgm_catalog import pick_catalog_bgm_for_niche
        fn = pick_catalog_bgm_for_niche(niche_id)
        if fn:
            path = get_bgm_path(fn)
            if path:
                return path
    except Exception:
        pass

    min_bpm, max_bpm = get_niche_target_bpm(niche_id)
    target_mid = (min_bpm + max_bpm) / 2.0

    tracks = available_tracks or list_bgm_tracks()
    if not tracks:
        return ensure_royalty_free_ambient_bgm()

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
        return get_bgm_path(best_track) or ensure_royalty_free_ambient_bgm()

    return ensure_royalty_free_ambient_bgm()


def synthesize_niche_tempo_bgm(niche_id: str, duration: float = 25.0, output_path: str = None) -> str:
    """
    Madde 169: Nişin BPM aralığına tam kilitli (örn. Motivasyon: 124 BPM, Felsefe: 75 BPM)
    harmonik arka plan ambient ritim parçası sentezler.
    """
    min_bpm, max_bpm = get_niche_target_bpm(niche_id)
    bpm = (min_bpm + max_bpm) / 2.0

    if not output_path:
        sanitized = str(niche_id or "ambient").replace("/", "_").lower()
        output_path = os.path.join(config.BGM_DIR, f"bgm_{sanitized}_{int(bpm)}bpm.wav")

    if os.path.exists(output_path):
        return output_path

    import math, wave, struct
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    beat_sec = 60.0 / bpm
    is_energetic = bpm >= 115.0

    # Frekans akorları:
    # Felsefe/Gizem: Dm (D3=146.83Hz, F3=174.61Hz, A3=220.00Hz)
    # Motivasyon: Am/C (C3=130.81Hz, G3=196.00Hz, E4=329.63Hz)
    base_f1 = 130.81 if is_energetic else 146.83
    base_f2 = 196.00 if is_energetic else 174.61
    base_f3 = 329.63 if is_energetic else 220.00

    for i in range(num_samples):
        t = i / sample_rate
        # BPM beat modülasyonu
        phase_in_beat = (t % beat_sec) / beat_sec
        pulse_env = math.exp(-phase_in_beat * (6.0 if is_energetic else 3.5))

        chord = (
            math.sin(2 * math.pi * base_f1 * t) * 0.45 +
            math.sin(2 * math.pi * base_f2 * t) * 0.35 +
            math.sin(2 * math.pi * base_f3 * t) * 0.25
        )

        # Ritim vuruş bası
        sub_kick = math.sin(2 * math.pi * (65.0 if is_energetic else 48.0) * t) * pulse_env * 0.4
        val = (chord * 0.4 + sub_kick) * 0.65
        val = max(-1.0, min(1.0, val))

        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"  [Item 169] Niş BPM ({bpm:.1f} BPM, {niche_id}) BGM parçası sentezlendi → {output_path}")
    return output_path


def parse_bgm_bpm(bgm_path: str = "", default_bpm: float = 120.0) -> float:
    """
    P2-21: Derive BPM from track filename (advisory beat grid).
    Full audio BPM analysis deferred — filename heuristics match Item 102/169.
    """
    if not bgm_path:
        return default_bpm
    fname = os.path.basename(bgm_path)
    try:
        from youtube_safe_bgm_catalog import get_track_bpm
        return get_track_bpm(fname, default_bpm)
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


def compute_scene_beat_hints(
    scenes: list,
    bgm_path: str = None,
    bpm: float = None,
) -> list:
    """
    P2-21: Advisory beat-aligned cut hints — does NOT mutate scene durations.
    Returns per-scene dicts: beat_hint_ms, suggested_cut_ms, delta_ms, bpm.
    """
    if not scenes:
        return []
    bpm = bpm if bpm is not None else parse_bgm_bpm(bgm_path or "")
    beat_interval_ms = (60.0 / bpm) * 1000.0
    total_ms = sum(
        float(getattr(s, "duration", None) or (s.get("duration") if isinstance(s, dict) else 3.0))
        * 1000.0
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
        dur_s = float(
            getattr(sc, "duration", None) or (sc.get("duration") if isinstance(sc, dict) else 3.0)
        )
        target_ms = accum_ms + dur_s * 1000.0
        if beats_ms:
            closest = min(beats_ms, key=lambda b: abs(b - target_ms))
            hints.append({
                "beat_hint_ms": round(closest, 1),
                "suggested_cut_ms": round(closest, 1),
                "actual_cut_ms": round(target_ms, 1),
                "delta_ms": round(closest - target_ms, 1),
                "bpm": bpm,
            })
        else:
            hints.append({"beat_hint_ms": round(target_ms, 1), "bpm": bpm})
        accum_ms = target_ms
    return hints


def detect_bgm_bpm_and_beats(bgm_path: str, duration: float = 60.0, default_bpm: float = 120.0) -> list:
    """
    Item 102 & 169: BGM Beat-Syncing (Ritim Tespiti).
    Müziğin temposuna (BPM) göre ritim vuruş (beat) zaman damgalarını hesaplar.
    Varsayılan hip-hop/lo-fi/energetic tempoda (100-128 BPM) vuruş ızgarası üretir.
    """
    bpm = parse_bgm_bpm(bgm_path, default_bpm=default_bpm)

    beat_interval = 60.0 / bpm
    beats = []
    curr = beat_interval
    while curr < duration:
        beats.append(round(curr, 3))
        curr += beat_interval
    return beats


def align_scenes_to_bgm_beats(scenes: list, bgm_path: str) -> list:
    """
    Item 102: BGM Beat-Syncing Sahne Kesimi.
    Arka plan müziğinin vuruş (beat) anları tespit edilip sahne kesim süreleri
    en yakın müzik vuruşuna (downbeat/bar) kilitlenir.
    """
    if not scenes or not bgm_path:
        return scenes

    total_dur = sum(s.get("duration", 6.0) for s in scenes)
    beats = detect_bgm_bpm_and_beats(bgm_path, duration=total_dur + 10.0)
    if not beats:
        return scenes

    aligned = []
    accum = 0.0
    for sc in scenes:
        target_end = accum + float(sc.get("duration", 6.0))
        # Find closest beat after or near target_end
        closest_beat = min(beats, key=lambda b: abs(b - target_end))
        new_dur = max(2.5, round(closest_beat - accum, 2))
        new_sc = dict(sc)
        new_sc["duration"] = new_dur
        new_sc["beat_synced"] = True
        accum += new_dur
        aligned.append(new_sc)

    return aligned


# ─── ITEM 180: Müziğin Giriş Hacmi & Anlık Ducking (Intro Music Punch) ─────────

def mix_intro_punch_bgm(narration_wav: str, music_wav: str, output_wav: str,
                        intro_blast_sec: float = 1.0,
                        blast_volume: float = 0.85,
                        ducked_volume: float = 0.14) -> str:
    """
    Madde 180: Müziğin Giriş Hacmi.
    Videonun ilk 1 saniyesinde müzik %100 (blast_volume) hacimle vurmalı,
    ses başladığı anda ducking ile anında kısılmalıdır.
    """
    from voice.audio_dsp import mix_intro_punch_bgm as _dsp_mix_intro_punch
    return _dsp_mix_intro_punch(
        narration_wav=narration_wav,
        music_wav=music_wav,
        output_wav=output_wav,
        intro_blast_sec=intro_blast_sec,
        blast_volume=blast_volume,
        ducked_volume=ducked_volume
    )


# ─── ITEM 185: Sona Doğru Müzik Yükselmesi (Ending Outro Music Swell) ──────────

def apply_outro_music_swell(music_audio: str, output_audio: str,
                            total_duration: float,
                            swell_seconds: float = 5.0,
                            boost_db: float = 3.5) -> str:
    """
    Madde 185: Sona Doğru Müzik Yükselmesi.
    Son 5 saniyede CTA verilirken fon müziği hafifçe yükseltilmelidir (+3.5dB).
    """
    from voice.audio_dsp import apply_outro_music_swell as _dsp_outro_swell
    return _dsp_outro_swell(
        music_audio=music_audio,
        output_audio=output_audio,
        total_duration=total_duration,
        swell_seconds=swell_seconds,
        boost_db=boost_db
    )


