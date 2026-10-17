"""
Audio Cadence, Tempo Fit, Reverb, Inflection, Shock Silence, BGM Punch & Vocal Carve EQ.
Covers items: 175, 176, 178, 179, 180, 184, 185, 191, 193, 194, 195, 196, 197, 198, 200, 254.
Extracted from `voice/audio_dsp.py`.
"""
import os, subprocess, re
from typing import Optional, List, Dict, Any
import imageio_ffmpeg

# ─── Audio duration fit (Shorts scene budget sync) ───────────────────────────

def _build_atempo_chain(speed_factor: float) -> str:
    """Build FFmpeg atempo filter chain (each stage limited to 0.5–2.0)."""
    filters = []
    remaining = max(0.5, min(4.0, speed_factor))
    while remaining > 2.001:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.499:
        filters.append("atempo=0.5")
        remaining /= 0.5
    if abs(remaining - 1.0) > 0.004:
        filters.append(f"atempo={remaining:.4f}")
    return ",".join(filters)


def _read_wav_duration(path: str) -> float:
    import wave
    try:
        with wave.open(path, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return 0.0


def fit_audio_to_duration(input_audio: str, output_audio: str,
                          target_duration: float, tolerance: float = 0.06) -> tuple:
    """
    Speed up or slow down narration so it matches the scene budget.
    Returns (output_path, new_duration, speed_factor).
    speed_factor > 1 means audio was sped up; word timings should be divided by it.
    """
    if not os.path.exists(input_audio) or target_duration <= 0:
        return input_audio, _read_wav_duration(input_audio), 1.0

    current = _read_wav_duration(input_audio)
    if current <= 0:
        return input_audio, 0.0, 1.0

    ratio = current / target_duration
    if abs(ratio - 1.0) <= tolerance:
        return input_audio, current, 1.0

    af = _build_atempo_chain(ratio)
    if not af:
        return input_audio, current, 1.0

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe, "-y", "-i", input_audio,
            "-af", af, "-c:a", "pcm_s16le", output_audio,
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_audio):
            new_dur = _read_wav_duration(output_audio)
            return output_audio, new_dur, ratio
    except Exception as e:
        print(f"    [AudioFit] Notice: {e}")

    return input_audio, current, 1.0


# ─── ITEM 175: Heyecanlı Anlarda Ses Hızlanması (Audio Tempo Acceleration) ─────

def accelerate_audio_tempo(input_audio: str, output_audio: str,
                           speed_factor: float = 1.15) -> str:
    """
    Madde 175: Heyecanlı Cümlelerde Ses Hızlanması (Audio Seviyesi).
    Hikayenin doruk anında perdeyi bozmadan ses hızını %115'e (speed_factor=1.15) çıkarır.
    FFmpeg atempo filtresi sayesinde frekans sabit kalırken anlatım enerjisi fırlar.
    """
    if not os.path.exists(input_audio):
        return input_audio

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        # atempo 0.5 ile 2.0 arasında çalışır
        clamped_factor = max(0.5, min(2.0, speed_factor))
        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_audio,
            "-af", f"atempo={clamped_factor:.3f}",
            "-c:a", "pcm_s16le",
            output_audio
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_audio):
            return output_audio
    except Exception as e:
        print(f"    [Item 175] Tempo hızlandırma hatası: {e}")

    return input_audio


# ─── ITEM 176: Gizemli Fısıltı Efekti (0.3s Reverse Reverb Tail) ──────────────

def apply_reverse_reverb_whisper(input_wav: str, output_wav: str,
                                 tail_sec: float = 0.30,
                                 wet_mix: float = 0.40) -> str:
    """
    Madde 176: Gizemli Fısıltı Efekti.
    Gizem ve antik tarih nişlerinde cümle sonuna 0.3 saniyelik ters çevrilmiş
    yankı (reverse reverb) eklenerek tekinsiz, fısıltılı ve merak uyandıran bir aura katılır.
    """
    if not os.path.exists(input_wav):
        return input_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        probe = subprocess.run([ffmpeg_exe, "-i", input_wav, "-hide_banner"], capture_output=True, text=True)
        import re
        dur_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
        duration = 5.0
        if dur_match:
            h, m, s = int(dur_match.group(1)), int(dur_match.group(2)), float(dur_match.group(3))
            duration = h * 3600 + m * 60 + s

        tail_start = max(0.0, duration - tail_sec - 0.1)

        # Cümle sonunu al, ters çevir, yankı ver, tekrar ters çevirip miksle
        filter_complex = (
            f"[0:a]asplit=2[dry][segment];"
            f"[segment]atrim={tail_start}:{duration},asetpts=PTS-STARTPTS,"
            f"areverse,aecho=0.8:0.85:50|80:0.4|0.3,areverse,volume={wet_mix}[rev_tail];"
            f"[dry][rev_tail]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]"
        )

        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_wav,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 176] Reverse reverb hatası: {e}")

    return input_wav


# ─── ITEM 178: Soru Cümlesi Perde Bükülmesi (Audio Question Inflection) ───────

def apply_audio_question_inflection(input_wav: str, output_wav: str,
                                    end_sec: float = 0.40,
                                    pitch_semitones: float = 0.85) -> str:
    """
    Madde 178: Soru Cümlesi Tonlaması (Ses Seviyesi).
    Soru cümlelerinin son 400 milisaniyesinde ses perdesini hafifçe yukarı bükerek (+5% / +0.85 yarım ton)
    doğal insan soru sorma entonasyonu (rising terminal intonation) elde eder.
    """
    if not os.path.exists(input_wav):
        return input_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        probe = subprocess.run([ffmpeg_exe, "-i", input_wav, "-hide_banner"], capture_output=True, text=True)
        import re
        dur_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
        duration = 3.0
        if dur_match:
            h, m, s = int(dur_match.group(1)), int(dur_match.group(2)), float(dur_match.group(3))
            duration = h * 3600 + m * 60 + s

        split_pt = max(0.1, duration - end_sec)
        pitch_factor = 2.0 ** (pitch_semitones / 12.0)  # ~1.0505 (+5%)

        filter_complex = (
            f"[0:a]asplit=2[body][tail];"
            f"[body]atrim=0:{split_pt},asetpts=PTS-STARTPTS[a_body];"
            f"[tail]atrim={split_pt}:{duration},asetpts=PTS-STARTPTS,"
            f"asetrate=44100*{pitch_factor:.4f},aresample=44100,atempo={1.0/pitch_factor:.4f}[a_tail];"
            f"[a_body][a_tail]concat=n=2:v=0:a=1[out]"
        )

        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_wav,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 178] Soru tonlaması hatası: {e}")

    return input_wav


# ─── ITEM 179: Şok Efekti Anında Ses Kesintisi (Shock Silence Drop - 0.2s) ────

def apply_shock_silence_cut(audio_wav: str, output_wav: str,
                            shock_timestamps: list,
                            silence_sec: float = 0.20) -> str:
    """
    Madde 179: Şok Efekti Anında Ses Kesintisi.
    Beklenmedik bir bilgi veya şaşırtıcı ters köşe verildiğinde belirtilen
    zaman damgasında 0.2 saniyelik mutlak vakum sessizlik oluşturarak izleyicinin
    dikkatini en üst seviyeye kilitler.
    """
    if not os.path.exists(audio_wav) or not shock_timestamps:
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        mute_windows = "+".join(
            f"between(t,{max(0.0, tp):.3f},{tp + silence_sec:.3f})" for tp in shock_timestamps
        )
        mute_filter = f"volume=enable='{mute_windows}':volume=0"

        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-af", mute_filter,
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 179] Şok sessizlik kesintisi hatası: {e}")

    return audio_wav


# ─── ITEM 180: Müziğin Giriş Hacmi & Anlık Ducking (Intro Music Punch) ─────────

def mix_intro_punch_bgm(narration_wav: str, music_wav: str, output_wav: str,
                        intro_blast_sec: float = 1.0,
                        blast_volume: float = 0.85,
                        ducked_volume: float = 0.14) -> str:
    """
    Madde 180: Müziğin Giriş Hacmi.
    Videonun ilk 1.0 saniyesinde müzik blast_volume ile vurur.
    Sonra yatak ara seviyesine iner. Sidechain konuşmada ducked_volume civarına kısar.
    """
    if not os.path.exists(narration_wav) or not os.path.exists(music_wav):
        return narration_wav

    try:
        from bgm_manager import DUCK_SIDECHAIN, gap_volume_for_speech
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        gap_vol = gap_volume_for_speech(ducked_volume)
        # First second stays loud. Then the bed is the -6 dB gap; sidechain
        # takes speech down to the ducked level in 80 ms.
        vol_expr = (
            f"if(lt(t\\,{intro_blast_sec})\\,{blast_volume}\\,"
            f"max({gap_vol:.4f}\\,{blast_volume}-({blast_volume}-{gap_vol:.4f})*(t-{intro_blast_sec})/0.08))"
        )

        filter_complex = (
            f"[0:a]pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,asplit=2[narr_sc][narr_mix];"
            f"[1:a]volume=eval=frame:volume='{vol_expr}',stereowiden=delay=20:feedback=0.25:crossfeed=0.2:drymix=0.8,{VOCAL_CARVE_EQ}[music_punched];"
            f"[music_punched][narr_sc]{DUCK_SIDECHAIN}[ducked];"
            f"[narr_mix][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]"
        )

        cmd = [
            ffmpeg_exe, "-y",
            "-i", narration_wav,
            "-stream_loop", "-1",
            "-i", music_wav,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 180] Müzik giriş vuruşu miks hatası: {e}")

    return narration_wav


# ─── ITEM 184: Sesin Görselle Birebir Senkronizasyonu (A/V Sync Precision) ────

def align_visual_cue_to_audio(visual_cue_time: float,
                              audio_word_timestamps: List[Dict[str, Any]],
                              target_phrase: str,
                              tolerance_sec: float = 0.05) -> dict:
    """
    Madde 184: Sesin Görselle Birebir Senkronizasyonu.
    Ekrana "Marcus Aurelius" yazısı veya grafik kartı düştüğü mikrosaniye ile
    ismin telaffuz başlangıcı milisaniyesi milisaniyesine örtüşmelidir.
    Word timestamp listesindeki fonetik başlangıcı bulur ve görsel zamanlamasını
    milisaniye hassasiyetinde kilitler.
    """
    if not audio_word_timestamps:
        return {
            "aligned_cue_time": visual_cue_time,
            "offset": 0.0,
            "target_phrase": target_phrase,
            "sync_status": "NO_TIMESTAMPS"
        }

    import re
    norm_target = re.sub(r'[^\w\s]', '', target_phrase.lower()).strip()
    target_tokens = norm_target.split()
    if not target_tokens:
        return {
            "aligned_cue_time": visual_cue_time,
            "offset": 0.0,
            "target_phrase": target_phrase,
            "sync_status": "EMPTY_TARGET"
        }

    first_target_word = target_tokens[0]

    # Eşleşen kelimeyi bul
    matched_time = None
    for item in audio_word_timestamps:
        w = re.sub(r'[^\w\s]', '', str(item.get("word", "")).lower()).strip()
        if w == first_target_word or first_target_word in w or w in first_target_word:
            matched_time = float(item.get("start", item.get("start_time", visual_cue_time)))
            break

    if matched_time is None:
        # En yakın kelime zamanını al
        matched_time = visual_cue_time

    offset = round(matched_time - visual_cue_time, 4)
    is_in_tolerance = abs(offset) <= tolerance_sec

    return {
        "aligned_cue_time": round(matched_time, 3),
        "original_cue_time": round(visual_cue_time, 3),
        "offset": offset,
        "target_phrase": target_phrase,
        "sync_status": "LOCKED" if is_in_tolerance else "ADJUSTED",
        "precision_ms": round(abs(offset) * 1000, 1)
    }


def audit_av_sync_precision(video_duration: float, audio_duration: float, tolerance_ms: float = 25.0) -> dict:
    """
    Madde 184: Video ve ses akışlarının süre uyumunu milisaniye hassasiyetinde denetler.
    Shorts döngüsünde 25 milisaniyenin üzerindeki kaymalar anında tespit edilir.
    """
    diff_sec = abs(video_duration - audio_duration)
    diff_ms = round(diff_sec * 1000.0, 2)
    in_sync = diff_ms <= tolerance_ms

    return {
        "video_duration": round(video_duration, 4),
        "audio_duration": round(audio_duration, 4),
        "diff_ms": diff_ms,
        "tolerance_ms": tolerance_ms,
        "in_sync": in_sync,
        "status": "PERFECT" if diff_ms <= 10.0 else ("ACCEPTABLE" if in_sync else "DRIFT_DETECTED")
    }



from .audio_cadence_helpers import (
    VOCAL_CARVE_EQ,
    apply_acoustic_reverb_chamber,
    apply_epic_trailer_deep_voice,
    apply_loop_inflection_preservation,
    apply_news_rapid_cadence,
    apply_outro_music_swell,
    apply_tts_artifact_lowpass_filter,
    apply_vocal_carve_eq,
    apply_voice_level_consistency,
    inject_pre_answer_tension_gap,
    inject_quiz_thinking_gap,
)
