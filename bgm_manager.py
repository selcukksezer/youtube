"""
Background Music (BGM) Manager for Shorts Video Creator.
"""
from __future__ import annotations

import math
import os, subprocess
from collections import OrderedDict
import imageio_ffmpeg
import config
from voice.bgm_synth_catalog import (
    NICHE_BPM_RANGES,
    TREND_HYBRID_PROFILES,
    align_scenes_to_bgm_beats,
    compute_scene_beat_hints,
    detect_audio_bpm_and_beats,
    detect_bgm_bpm_and_beats,
    ensure_royalty_free_ambient_bgm,
    get_niche_target_bpm,
    get_safe_default_bgm_path,
    list_trend_hybrid_profiles,
    match_bgm_track_to_niche,
    normalize_bpm_to_shorts_band,
    parse_bgm_bpm,
    select_trend_hybrid_bgm,
    snap_durations_to_bpm,
    snap_timeline_to_beat_grid,
    synthesize_niche_tempo_bgm,
)

# Item 432: LRU RAM cache for hot BGM/SFX paths (avoid repeated disk stat during batch render)
_BGM_RAM_CACHE: OrderedDict = OrderedDict()
_BGM_CACHE_MAX = int(os.getenv("BGM_RAM_CACHE_MAX", "12"))
_BGM_MUTE_TOKENS = frozenset({"none", "no_bgm", "mute", "off", "yok", "müziksiz"})
_BGM_AUTO_TOKENS = frozenset({"auto", "otomatik", "default", "varsayılan", "varsayilan"})


def _is_auto_bgm_token(bgm_track: str | None) -> bool:
    low = (bgm_track or "").strip().lower()
    if not low or low in _BGM_AUTO_TOKENS:
        return True
    return low.startswith("🎵 otomatik") or low.startswith("otomatik (")


def request_mutes_bgm(bgm_track: str | None, enable_bgm: bool | None = None) -> bool:
    """Studio 'Fon Müziği' off, or the Müziksiz track, means no music on this render."""
    if enable_bgm is False:
        return True
    low = (bgm_track or "").strip().lower()
    return low in _BGM_MUTE_TOKENS or low.startswith("🔇 müziksiz")


def cache_bgm_file(path: str | None) -> str | None:
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
    library_only = bool(getattr(config, "BGM_AUDIO_LIBRARY_ONLY", False))
    tracks = (
        []
        if library_only
        else [f for f in os.listdir(config.BGM_DIR) if f.lower().endswith(exts)]
    )

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
                if not fn:
                    continue
                if library_only and not (
                    str(fn).startswith("youtube_studio/")
                    or str(t.get("source") or "").lower() in ("youtube_audio_library", "youtube_studio")
                ):
                    continue
                if fn not in tracks:
                    tracks.append(fn)
        except Exception:
            pass

    if not tracks and not library_only:
        ensure_royalty_free_ambient_bgm()
        tracks = [f for f in os.listdir(config.BGM_DIR) if f.lower().endswith(exts)]
    return sorted(set(tracks))


def list_bgm_tracks_detailed(include_catalog: bool = True) -> list:
    """Returns track dicts with display labels for API/UI."""
    try:
        from youtube_safe_bgm_catalog import get_display_label, list_catalog_entries
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


def get_bgm_path(track_name: str | None) -> str | None:
    """Returns full path of a BGM track if it exists, auto-downloading catalog tracks if needed."""
    if not isinstance(track_name, str) or not track_name.strip():
        return None
    if request_mutes_bgm(track_name) or _is_auto_bgm_token(track_name):
        return None
    from services.bgm_security import BgmSecurityError, MAX_BGM_UPLOAD_BYTES, validate_bgm_filename

    requested = track_name.strip()
    safe = requested.replace("\\", "/")
    bgm_dir_abs = os.path.abspath(config.BGM_DIR).replace("\\", "/").rstrip("/")
    bgm_dir_real = os.path.realpath(config.BGM_DIR).replace("\\", "/").rstrip("/")
    if ".." not in safe.split("/"):
        if safe.startswith(bgm_dir_abs + "/"):
            safe = safe[len(bgm_dir_abs) + 1 :]
        elif safe.startswith(bgm_dir_real + "/"):
            safe = safe[len(bgm_dir_real) + 1 :]
        elif safe.startswith("assets/bgm/"):
            safe = safe[len("assets/bgm/") :]
        elif safe.startswith("bgm/"):
            safe = safe[len("bgm/") :]
    path_parts = safe.split("/")
    if "/" in safe and (
        len(path_parts) != 2 or path_parts[0] != "youtube_studio" or path_parts[1] in {"", ".", ".."}
    ):
        print("  [BgmSecurity] Invalid BGM track path rejected.", flush=True)
        return None

    base_name = os.path.basename(safe)
    try:
        validate_bgm_filename(base_name)
    except BgmSecurityError as filename_error:
        if "/" in safe:
            print(f"  [BgmSecurity] Invalid BGM track name rejected: {filename_error}", flush=True)
            return None

        from youtube_safe_bgm_catalog import get_display_label, track_by_filename
        catalog_track = track_by_filename(requested)
        label = requested
        download_suffix = "(indirilecek)"
        if label.casefold().endswith(download_suffix):
            label = label[:-len(download_suffix)].strip()
        aliases = set()
        if catalog_track:
            aliases = {
                str(catalog_track.get("filename") or "").casefold(),
                str(catalog_track.get("id") or "").casefold(),
                str(catalog_track.get("title") or "").casefold(),
                get_display_label(catalog_track["filename"]).casefold(),
            }
        if not catalog_track or label.casefold() not in aliases:
            print(f"  [BgmSecurity] Invalid BGM track name rejected: {filename_error}", flush=True)
            return None
        base_name = validate_bgm_filename(catalog_track["filename"])
        safe = base_name
        track_name = base_name

    full_path = os.path.join(config.BGM_DIR, safe) if safe.startswith("youtube_studio/") else os.path.join(config.BGM_DIR, os.path.basename(safe))
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


PLAN_SPEECH_LIN = 10 ** (-18.0 / 20.0)
PLAN_GAP_LIN = 10 ** (-6.0 / 20.0)
DUCK_SIDECHAIN = (
    "sidechaincompress=threshold=0.028:ratio=2.7:attack=80:release=200:"
    "knee=1:makeup=1:level_sc=2"
)
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
    """Pre-sidechain bed."""
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
    rise = f"min({num(boost)}\\,1.0+({num(boost - 1.0)})*(t-{num(swell_start)})/{num(swell)})"
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
    """Mixes narration audio with background music using ffmpeg."""
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
    duck_chain = build_duck_sidechain(attack_ms, release_ms) or DUCK_SIDECHAIN
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
        output_path,
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


def apply_vocal_carve_eq(
    music_wav: str,
    output_wav: str,
    notch_freq: float = 2000.0,
    notch_gain: float = -4.5,
    q_width: float = 1.0,
) -> str:
    """Madde 200: Ses Frekans Çakışmasını Önleme (Vocal Frequency Carving)."""
    from voice.audio_dsp import apply_vocal_carve_eq as _dsp_vocal_carve
    return _dsp_vocal_carve(music_wav, output_wav, notch_freq, notch_gain, q_width)


def apply_seamless_loop_cut(bgm_path: str, output_path: str, duration: float) -> str:
    """Madde 166: Kapanış Müzik Sönümlemesi (Fade-Out Yok!)."""
    if not os.path.exists(bgm_path):
        return bgm_path

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe, "-y",
            "-stream_loop", "-1",
            "-i", bgm_path,
            "-af", f"atrim=0:{max(0.1, duration):.3f},asetpts=PTS-STARTPTS",
            "-c:a", "pcm_s16le",
            output_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_path):
            print(f"  [Item 166] Müzik sönümleme engellendi (Fade-Out Yok, Keskin Döngü): {duration:.2f}s → {output_path}")
            return output_path
    except Exception as e:
        print(f"  [Item 166] Seamless loop cut hatası: {e}")

    return bgm_path


def mix_intro_punch_bgm(
    narration_wav: str,
    music_wav: str,
    output_wav: str,
    intro_blast_sec: float = 1.0,
    blast_volume: float = 0.85,
    ducked_volume: float = 0.14,
) -> str:
    """Madde 180: Müziğin Giriş Hacmi."""
    from voice.audio_dsp import mix_intro_punch_bgm as _dsp_mix_intro_punch
    return _dsp_mix_intro_punch(
        narration_wav=narration_wav,
        music_wav=music_wav,
        output_wav=output_wav,
        intro_blast_sec=intro_blast_sec,
        blast_volume=blast_volume,
        ducked_volume=ducked_volume,
    )


def apply_outro_music_swell(
    music_audio: str,
    output_audio: str,
    total_duration: float,
    swell_seconds: float = 5.0,
    boost_db: float = 3.5,
) -> str:
    """Madde 185: Sona Doğru Müzik Yükselmesi."""
    from voice.audio_dsp import apply_outro_music_swell as _dsp_outro_swell
    return _dsp_outro_swell(
        music_audio=music_audio,
        output_audio=output_audio,
        total_duration=total_duration,
        swell_seconds=swell_seconds,
        boost_db=boost_db,
    )
