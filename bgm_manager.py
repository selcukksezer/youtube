"""
Background Music (BGM) Manager for Shorts Video Creator.
"""
import math
import os, subprocess
from collections import OrderedDict
from typing import Optional
import imageio_ffmpeg
import config

# Item 432: LRU RAM cache for hot BGM/SFX paths (avoid repeated disk stat during batch render)
_BGM_RAM_CACHE: OrderedDict = OrderedDict()
_BGM_CACHE_MAX = int(os.getenv("BGM_RAM_CACHE_MAX", "12"))
_BGM_MUTE_TOKENS = frozenset({"none", "no_bgm", "mute", "off", "yok", "müziksiz"})


def request_mutes_bgm(bgm_track: Optional[str], enable_bgm: Optional[bool] = None) -> bool:
    """Studio 'Fon Müziği' off, or the Müziksiz track, means no music on this render."""
    if enable_bgm is False:
        return True
    return (bgm_track or "").strip().lower() in _BGM_MUTE_TOKENS


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
        try:
            from youtube_safe_bgm_catalog import pick_catalog_bgm_for_niche
            fn = pick_catalog_bgm_for_niche()
            if fn:
                path = get_bgm_path(fn)
        except Exception:
            pass
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
    """Returns full path of a BGM track if it exists, auto-downloading catalog tracks if needed."""
    if not track_name:
        return None
    try:
        from services.bgm_security import validate_bgm_filename, MAX_BGM_UPLOAD_BYTES
        base_name = os.path.basename(track_name.replace("\\", "/"))
        validate_bgm_filename(base_name)
    except Exception as e:
        print(f"  [BgmSecurity] Invalid BGM track name rejected: {e}", flush=True)
        return None

    safe = track_name.replace("\\", "/")
    if safe.startswith("youtube_studio/"):
        full_path = os.path.join(config.BGM_DIR, safe)
    else:
        full_path = os.path.join(config.BGM_DIR, os.path.basename(safe))
    if os.path.isfile(full_path) and 2000 < os.path.getsize(full_path) <= MAX_BGM_UPLOAD_BYTES:
        return cache_bgm_file(full_path)
    studio = os.path.join(config.BGM_DIR, "youtube_studio", os.path.basename(safe))
    if os.path.isfile(studio) and 2000 < os.path.getsize(studio) <= MAX_BGM_UPLOAD_BYTES:
        return cache_bgm_file(studio)
    try:
        from youtube_safe_bgm_catalog import resolve_bgm_path
        resolved = resolve_bgm_path(track_name)
        if resolved and os.path.isfile(resolved) and 2000 < os.path.getsize(resolved) <= MAX_BGM_UPLOAD_BYTES:
            return cache_bgm_file(resolved)
    except Exception:
        pass
    return None

def get_safe_default_bgm_path():
    """Item 135: Returns the bundled/generated royalty-free fallback track."""
    return ensure_royalty_free_ambient_bgm()


# R10 #87 — Trend-style hybrid profiles (royalty-free stand-ins for YT "trend sounds")
# We cannot scrape YouTube's private Trend Sounds list; map viral energy bands → safe BGM.
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
    """
    R10 #87: Pick a royalty-free BGM path that matches current 'trend energy'
    for the niche — hybrid of trend mood tags + local safe catalog.
    """
    nid = (niche_id or "").lower()
    topic_l = (topic or "").lower()
    mood = (preferred_mood or "").lower()
    chosen = TREND_HYBRID_PROFILES[1]  # default lofi
    for profile in TREND_HYBRID_PROFILES:
        hints = profile["niche_hints"]
        if any(h in nid for h in hints) or any(h in topic_l for h in hints):
            chosen = profile
            break
        if mood and mood in profile["moods"]:
            chosen = profile
            break

    tracks = list_bgm_tracks(include_catalog=True)
    mood_terms = list(chosen["moods"])
    match = None
    for t in tracks:
        low = t.lower()
        if any(m in low for m in mood_terms):
            match = t
            break
    path = get_bgm_path(match) if match else None
    if not path:
        path = get_safe_default_bgm_path()
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

# -6 dB gap, -18 dB under speech. Measured on a -13 dB RMS sidechain
# (near -14 LUFS narration) against a full-scale music sine: duck = 12.0 dB,
# attack 80 ms, release back to the gap by 200 ms.
PLAN_SPEECH_LIN = 10 ** (-18.0 / 20.0)
PLAN_GAP_LIN = 10 ** (-6.0 / 20.0)
DUCK_SIDECHAIN = (
    "sidechaincompress=threshold=0.028:ratio=2.7:attack=80:release=200:"
    "knee=1:makeup=1:level_sc=2"
)
# HTML slider defaults. Omitted render fields use these. 80/200 keeps DUCK_SIDECHAIN.
DEFAULT_DUCK_ATTACK_MS = 80
DEFAULT_DUCK_RELEASE_MS = 200
DEFAULT_INTRO_BLAST = 0.85
DEFAULT_OUTRO_SWELL_SEC = 5.0
_OUTRO_SWELL_DB = 3.5


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def resolve_studio_audio_mix(
    duck_attack_ms: Optional[float] = None,
    duck_release_ms: Optional[float] = None,
    intro_blast: Optional[float] = None,
    enable_intro_whoosh: bool = False,
    outro_swell_sec: Optional[float] = None,
    enable_outro: bool = True,
    enable_outro_swell: bool = True,
    allow_bgm: bool = True,
) -> dict:
    """Slider values the live BGM mix reads. Whoosh off forces blast silent."""
    attack = DEFAULT_DUCK_ATTACK_MS if duck_attack_ms is None else _clamp(duck_attack_ms, 20, 200)
    release = DEFAULT_DUCK_RELEASE_MS if duck_release_ms is None else _clamp(duck_release_ms, 50, 600)
    blast_slider = DEFAULT_INTRO_BLAST if intro_blast is None else _clamp(intro_blast, 0.50, 1.00)
    swell_slider = DEFAULT_OUTRO_SWELL_SEC if outro_swell_sec is None else _clamp(outro_swell_sec, 2, 10)
    music_ok = bool(allow_bgm and enable_outro and enable_outro_swell)
    return {
        "duck_attack_ms": float(attack),
        "duck_release_ms": float(release),
        "intro_blast": float(blast_slider) if enable_intro_whoosh else 0.0,
        "outro_swell_sec": float(swell_slider) if music_ok else 0.0,
    }


def build_duck_sidechain(attack_ms: float = DEFAULT_DUCK_ATTACK_MS, release_ms: float = DEFAULT_DUCK_RELEASE_MS) -> str:
    """Same sidechain as DUCK_SIDECHAIN when attack/release stay on the HTML defaults."""
    attack = int(round(float(attack_ms)))
    release = int(round(float(release_ms)))
    if attack == DEFAULT_DUCK_ATTACK_MS and release == DEFAULT_DUCK_RELEASE_MS:
        return DUCK_SIDECHAIN
    return (
        "sidechaincompress=threshold=0.028:ratio=2.7:"
        f"attack={attack}:release={release}:knee=1:makeup=1:level_sc=2"
    )


def _wav_duration_sec(path: str) -> float:
    try:
        import wave
        with wave.open(path, "rb") as handle:
            rate = handle.getframerate() or 1
            return handle.getnframes() / float(rate)
    except Exception:
        return 0.0


def build_bgm_volume_filter(
    gap_vol: float,
    intro_blast: float = 0.0,
    outro_swell_sec: float = 0.0,
    duration_sec: float = 0.0,
) -> str:
    """
    Pre-sidechain bed. Blast 0 and swell 0 keep volume={gap}, the current mix.
    Blast is the first-second opening hit. Swell raises only the end of the bed.
    """
    gap = float(gap_vol)
    blast = float(intro_blast or 0.0)
    swell = float(outro_swell_sec or 0.0)
    duration = float(duration_sec or 0.0)
    use_blast = blast > 0.0
    use_swell = swell > 0.0 and duration > swell
    if not use_blast and not use_swell:
        return f"volume={gap:.3f}"

    def num(value: float) -> str:
        return f"{float(value):.4f}"

    if use_blast:
        bed = (
            f"if(lt(t\\,1.0)\\,{num(blast)}\\,"
            f"max({num(gap)}\\,{num(blast)}-({num(blast)}-{num(gap)})*(t-1.0)/0.08))"
        )
    else:
        bed = num(gap)
    if not use_swell:
        return f"volume=eval=frame:volume='{bed}'"
    boost = 10.0 ** (_OUTRO_SWELL_DB / 20.0)
    swell_start = max(0.1, duration - swell)
    rise = (
        f"min({num(boost)}\\,1.0+({num(boost - 1.0)})*(t-{num(swell_start)})/{num(swell)})"
    )
    expr = f"if(lt(t\\,{num(swell_start)})\\,{bed}\\,({bed})*({rise}))"
    return f"volume=eval=frame:volume='{expr}'"


def gap_volume_for_speech(speech_volume: float) -> float:
    """Slider is the music level while someone is talking. The gap is 12 dB louder."""
    speech = PLAN_SPEECH_LIN if speech_volume is None else float(speech_volume)
    speech = max(0.04, min(0.30, speech))
    return min(1.0, speech * (PLAN_GAP_LIN / PLAN_SPEECH_LIN))


def mix_narration_and_bgm(
    narration_path,
    bgm_path,
    output_path,
    volume=0.12,
    tape_stop_times=None,
    allow_fade_out: bool = False,
    duck_attack_ms: float = DEFAULT_DUCK_ATTACK_MS,
    duck_release_ms: float = DEFAULT_DUCK_RELEASE_MS,
    intro_blast: float = 0.0,
    outro_swell_sec: float = 0.0,
):
    """
    Mixes narration audio with background music using ffmpeg.
    Loops BGM if shorter than narration, trims BGM if longer.
    Item 144 / 5.1: sidechain drops music to the speech level in 80ms and
    returns it to 12 dB louder (the -6 dB gap when speech is -18 dB) in 200ms.
    youtube-shorts-pipeline switches two volumes with a 300ms hard step.
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

    from voice.audio_dsp import VOCAL_CARVE_EQ
    speech_vol = PLAN_SPEECH_LIN if volume is None else float(volume)
    gap_vol = gap_volume_for_speech(speech_vol)
    attack_ms = DEFAULT_DUCK_ATTACK_MS if duck_attack_ms is None else float(duck_attack_ms)
    release_ms = DEFAULT_DUCK_RELEASE_MS if duck_release_ms is None else float(duck_release_ms)
    duck_chain = build_duck_sidechain(attack_ms, release_ms)
    if duck_chain == DUCK_SIDECHAIN:
        duck_chain = DUCK_SIDECHAIN
    vol_filter = build_bgm_volume_filter(
        gap_vol,
        intro_blast=0.0 if intro_blast is None else float(intro_blast),
        outro_swell_sec=0.0 if outro_swell_sec is None else float(outro_swell_sec),
        duration_sec=_wav_duration_sec(narration_path),
    )

    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y",
        "-i", narration_path,

        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex",
        (
            "[0:a]pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,asplit=2[narr_sc][narr_mix];"
            f"[1:a]{vol_filter},stereowiden=delay=20:feedback=0.25:crossfeed=0.2:drymix=0.8,{VOCAL_CARVE_EQ}{mute_filter}[bgm_wide];"
            f"[bgm_wide][narr_sc]{duck_chain}[ducked];"
            f"[narr_mix][ducked]amix=inputs=2:duration=first:dropout_transition={dropout_val}:normalize=0[aout]"
        ),
        "-map", "[aout]",
        "-c:a", "pcm_s16le",
        output_path
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 2000:
        fade_status = "Fade-Out Yok (Döngü Korundu, Madde 166)" if not allow_fade_out else "Fade-Out İzinli"
        speech_db = 20.0 * math.log10(max(0.04, min(0.30, speech_vol)))
        gap_db = 20.0 * math.log10(gap_vol)
        print(
            f"  [BGM] Mixed {os.path.basename(bgm_path)} "
            f"gap {gap_db:.1f} dB, speech {speech_db:.1f} dB, {int(round(attack_ms))}ms/{int(round(release_ms))}ms, 1-3 kHz carve ({fade_status})"
        )
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
        from youtube_safe_bgm_catalog import track_by_filename
        meta = track_by_filename(fname)
        if meta and meta.get("bpm"):
            return float(meta["bpm"])
    except Exception:
        pass
    # Not a catalog track (studio import / synthesized) -> filename heuristics
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
    """
    Bölüm 7.3: Shorts hipnotik kurgu temposu için BPM'i 80-120 aralığına normalize eder.
    Aşırı yavaş parçaları çift vuruşla/harmonik katla hızlandırır, aşırı hızlı parçaları yarı-vuruşla yavaşlatır.
    """
    try:
        val = float(bpm) if bpm is not None else 100.0
    except (ValueError, TypeError):
        val = 100.0
    if val <= 1.0:
        return 100.0

    # Double or half only when that octave still lands in 80-120.
    # 1.5x and an edge clamp miss the kick. 78 stays 78. 125 stays 125.
    # 60 becomes 120. 160 becomes 80.
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
    """
    Gerçek ses dosyasından FFmpeg ebur128 momentary loudness peak'leri ile
    gerçek vuruşları (beats) ve BPM'i tespit eder.
    Dosya yoksa veya peak tespit edilemezse katalog/heuristic BPM'e döner.
    """
    raw_bpm = parse_bgm_bpm(audio_path, default_bpm=default_bpm)
    actual_beats: list[float] = []

    if audio_path and os.path.isfile(audio_path):
        try:
            import imageio_ffmpeg
            import subprocess
            import re

            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_exe,
                "-hide_banner",
                "-i", audio_path,
                "-af", "ebur128",
                "-f", "null",
                "-",
            ]
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
                    peak_times = [round(p * 0.1, 3) for p in peaks if p * 0.1 <= duration + 5.0]
                    actual_beats = peak_times
                    dur_span = (peaks[-1] - peaks[0]) * 0.1
                    if dur_span > 1.0:
                        measured_bpm = (len(peaks) - 1) / dur_span * 60.0
                        if 40.0 <= measured_bpm <= 220.0:
                            raw_bpm = measured_bpm
        except Exception as exc:
            pass

    final_bpm = normalize_bpm_to_shorts_band(raw_bpm) if enforce_band else raw_bpm

    # Eğer ses dosyasından gerçek beat gelmediyse veya az ise matematiksel grid üret
    if len(actual_beats) < 4:
        beat_interval = 60.0 / final_bpm
        actual_beats = []
        curr = beat_interval
        while curr < duration + 10.0:
            actual_beats.append(round(curr, 3))
            curr += beat_interval

    return final_bpm, actual_beats


def compute_scene_beat_hints(
    scenes: list,
    bgm_path: str = None,
    bpm: float = None,
    enforce_band: bool = False,
) -> list:
    """
    P2-21 & Bölüm 7.3: Advisory beat-aligned cut hints.
    Returns per-scene dicts: beat_hint_ms, suggested_cut_ms, delta_ms, bpm.
    """
    if not scenes:
        return []
    if bpm is not None:
        used_bpm = normalize_bpm_to_shorts_band(bpm) if enforce_band else float(bpm)
    else:
        raw_bpm = parse_bgm_bpm(bgm_path or "")
        used_bpm = normalize_bpm_to_shorts_band(raw_bpm) if enforce_band else raw_bpm

    beat_interval_ms = (60.0 / used_bpm) * 1000.0
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
                "bpm": used_bpm,
            })
        else:
            hints.append({"beat_hint_ms": round(target_ms, 1), "bpm": used_bpm})
        accum_ms = target_ms
    return hints


def snap_durations_to_bpm(durations, bpm, total=None, min_dur=2.0, enforce_band=True):
    """
    Move each cut except the last onto the nearest beat.
    The last scene keeps the timeline equal to `total`, so speech length holds.
    A snap that would shrink a scene under min_dur is refused.
    """
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
    """
    Bölüm 7.3: Sahne geçişlerini 80-120 BPM müzik ritmine kilitler (Beat Snapping).
    - Hem ScenePlan nesnelerini hem dict nesnelerini destekler.
    - Metin kelime sayısına göre konuşma süresi kalkanı (TTS speech ceiling) korur.
    - Toplam video süresini (Shorts 38-60s bandı) ve drift toleransını korur.
    - Her sahneye beat_hint_ms, suggested_cut_ms, delta_ms ve beat_synced atar.
    """
    if not scenes:
        return scenes

    if bpm is not None:
        final_bpm = normalize_bpm_to_shorts_band(bpm) if enforce_band else float(bpm)
        beat_interval = 60.0 / final_bpm
        total_time = sum(
            float(getattr(s, "duration", None) or (s.get("duration") if isinstance(s, dict) else 3.0))
            for s in scenes
        )
        beats = [round(i * beat_interval, 3) for i in range(1, int((total_time + 15.0) / beat_interval) + 1)]
    else:
        total_time = sum(
            float(getattr(s, "duration", None) or (s.get("duration") if isinstance(s, dict) else 3.0))
            for s in scenes
        )
        final_bpm, beats = detect_audio_bpm_and_beats(
            bgm_path, duration=total_time, enforce_band=enforce_band
        )

    if not beats:
        return scenes

    is_dict = isinstance(scenes[0], dict)
    out_scenes = []
    accum = 0.0

    for idx, sc in enumerate(scenes):
        orig_dur = float(getattr(sc, "duration", None) or (sc.get("duration") if is_dict else 3.0))
        narr = str(getattr(sc, "narration", None) or (sc.get("narration") if is_dict else "") or "")
        word_count = len(narr.split())
        # Konuşma koruma tavanı: kelime başına en az ~0.30s + 0.15s esneklik payı
        min_speech_s = max(min_scene_dur, (word_count * 0.30) + 0.15) if word_count > 0 else min_scene_dur

        is_last = (idx == len(scenes) - 1)
        if not is_last:
            target_cut = accum + orig_dur
            # En yakın beat vuruşunu seç
            closest_beat = min(beats, key=lambda b: abs(b - target_cut))
            new_dur = closest_beat - accum

            # Koruma kalkanları: min süre ve max süre sınırları
            if new_dur < min_speech_s:
                # Bir sonraki vuruş adayını ara
                next_beats = [b for b in beats if b - accum >= min_speech_s]
                if next_beats:
                    closest_beat = min(next_beats, key=lambda b: abs(b - (accum + min_speech_s)))
                    new_dur = closest_beat - accum
                else:
                    new_dur = max(min_speech_s, orig_dur)
                    closest_beat = accum + new_dur

            if new_dur > max_scene_dur:
                prev_beats = [b for b in beats if accum + min_speech_s <= b <= accum + max_scene_dur]
                if prev_beats:
                    closest_beat = max(prev_beats)
                    new_dur = closest_beat - accum
                else:
                    new_dur = max_scene_dur
                    closest_beat = accum + new_dur

            new_dur = round(max(min_scene_dur, new_dur), 3)
            actual_cut = round(accum + new_dur, 3)
            delta_ms = round((closest_beat - actual_cut) * 1000.0, 1)
        else:
            # Son sahne: toplam video süresini korumak için kalan süreyi alır
            new_dur = round(max(min_scene_dur, total_time - accum), 3)
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
    """
    Item 102 & 169: BGM Beat-Syncing (Ritim Tespiti).
    Müziğin temposuna (BPM) göre ritim vuruş (beat) zaman damgalarını hesaplar.
    """
    _bpm, beats = detect_audio_bpm_and_beats(
        bgm_path, duration=duration, default_bpm=default_bpm, enforce_band=False
    )
    return beats


def align_scenes_to_bgm_beats(scenes: list, bgm_path: str) -> list:
    """
    Item 102 & Bölüm 7.3: BGM Beat-Syncing Sahne Kesimi.
    Arka plan müziğinin vuruş (beat) anları tespit edilip sahne kesim süreleri
    en yakın müzik vuruşuna (downbeat/bar) kilitlenir.
    """
    if not scenes or not bgm_path:
        return scenes
    return snap_timeline_to_beat_grid(scenes, bgm_path=bgm_path, enforce_band=False)


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


