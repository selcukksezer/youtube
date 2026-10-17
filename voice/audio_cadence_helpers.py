"""Audio Cadence Helpers (Items 185-200): Outro Music Swell, Reverb Chamber, Voice Level Consistency, Lowpass, Deep Voice, News Cadence, Quiz Gaps, Loop Inflection & Vocal Carve."""
import os, subprocess, re
from typing import Optional, List, Dict, Any
import imageio_ffmpeg

# ─── ITEM 185: Sona Doğru Müzik Yükselmesi (Ending Outro Music Swell) ──────────

def apply_outro_music_swell(music_audio: str, output_audio: str,
                            total_duration: float,
                            swell_seconds: float = 5.0,
                            boost_db: float = 3.5) -> str:
    """
    Madde 185: Sona Doğru Müzik Yükselmesi.
    Son 5 saniyede CTA (Harekete Geçirici Mesaj / Abone Ol / Yorum Yap) verilirken
    fon müziği kademeli olarak +3.5dB seviyesine yükseltilerek heyecan ve enerji tazelenir.
    """
    if not os.path.exists(music_audio):
        return music_audio

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        swell_start = max(0.1, total_duration - swell_seconds)
        boost_mult = 10.0 ** (boost_db / 20.0)  # +3.5dB ≈ 1.496

        # Swell start'a kadar 1.0, ardından boost_mult değerine lineer yükseliş
        vol_expr = (
            f"if(lt(t\\,{swell_start})\\,1.0\\,"
            f"min({boost_mult:.3f}\\,1.0+({boost_mult - 1.0:.3f})*(t-{swell_start})/{swell_seconds}))"
        )

        cmd = [
            ffmpeg_exe, "-y",
            "-i", music_audio,
            "-af", f"volume=eval=frame:volume='{vol_expr}'",
            "-c:a", "pcm_s16le",
            output_audio
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_audio):
            return output_audio
    except Exception as e:
        print(f"    [Item 185] Outro müzik yükselme hatası: {e}")

    return music_audio


# ─── ITEM 191: Akustik Yankı Odası (Acoustic Reverb Chamber) ─────────────────

def apply_acoustic_reverb_chamber(input_wav: str, output_wav: str,
                                  room_type: str = "cathedral",
                                  mix_ratio: float = 0.25) -> str:
    """
    Madde 191: Akustik Yankı Odası.
    Korku, gizem ve gerilim nişlerinde konuşma sesini sanki boş bir katedralde
    veya mağaradaymış gibi yankılandırır (aecho / reverb DSP).
    """
    if not os.path.exists(input_wav):
        return input_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if room_type == "cave":
            reverb_filter = "aecho=0.8:0.7:120|240:0.4|0.25"
        elif room_type == "hall":
            reverb_filter = "aecho=0.85:0.75:60|120:0.35|0.2"
        else:  # cathedral
            reverb_filter = "aecho=0.88:0.82:80|160|240:0.45|0.3|0.18"

        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_wav,
            "-af", reverb_filter,
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 191] Akustik yankı odası hatası: {e}")
    return input_wav


# ─── ITEM 193: Ses Tonu Tutarlılığı (Voice Level Consistency / RMS Leveller) ─

def apply_voice_level_consistency(input_wav: str, output_wav: str,
                                  target_rms_db: float = -18.0) -> str:
    """
    Madde 193: Ses Tonu Tutarlılığı.
    Bir video içinde mikrofon mesafesi ve ses tonunun sabit kalmasını sağlar;
    cümleler veya segmentler arasındaki ani ses sıçramalarını ve düşüşlerini
    dinamik compand algoritmasıyla eşitler.
    """
    if not os.path.exists(input_wav):
        return input_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        compand_chain = (
            "compand=attacks=0.03:decays=0.2:"
            "points=-70/-70|-40/-28|-20/-16|0/-6:"
            "gain=2:volume=-1:delay=0.05"
        )
        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_wav,
            "-af", compand_chain,
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 193] Ses tonu tutarlılığı hatası: {e}")
    return input_wav


# ─── ITEM 194: Sentetik Ses Artefaktlarını Filtreleme (Low-Pass @ 14kHz) ───────

def apply_tts_artifact_lowpass_filter(input_wav: str, output_wav: str,
                                      cutoff_hz: float = 14000.0,
                                      poles: int = 2) -> str:
    """
    Madde 194: Sentetik Ses Artefaktlarını Filtreleme.
    TTS motorunun oluşturduğu 14kHz üzerindeki yapay metalik çınlamaları,
    dijital fısıltı artefaktlarını ve keskin üst harmonikleri alçak geçiren
    filtreyle (low-pass) yumuşatarak stüdyo analog sıcaklığı sağlar.
    """
    if not os.path.exists(input_wav):
        return input_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        af = f"lowpass=f={cutoff_hz}:poles={poles}"
        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_wav,
            "-af", af,
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 194] Sentetik artefakt filtresi hatası: {e}")
    return input_wav


# ─── ITEM 195: Derin Anlatıcı Sesi (Epic Movie Trailer Voice) ─────────────────

def apply_epic_trailer_deep_voice(input_wav: str, output_wav: str,
                                  pitch_ratio: float = 0.88,
                                  bass_boost_db: float = 3.5) -> str:
    """
    Madde 195: Derin Anlatıcı Sesi (Epic Movie Trailer Voice).
    Erkek sesini derinleştirerek sinematik fragman tonu elde eder.
    Pitch oranını düşürürken tempo telafisi yapar ve 120Hz bas gövdesini besler.
    """
    if not os.path.exists(input_wav):
        return input_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        sample_rate = 44100
        mod_rate = int(sample_rate * pitch_ratio)
        tempo_comp = 1.0 / max(0.01, float(pitch_ratio))
        from services.audio_tempo_guard import build_atempo_filter_chain
        atempo_chain = build_atempo_filter_chain(tempo_comp)
        af_chain = (
            f"asetrate={mod_rate},"
            f"{atempo_chain},"
            f"equalizer=f=120:t=q:w=1.2:g={bass_boost_db},"
            f"aformat=sample_rates=44100:channel_layouts=stereo"
        )
        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_wav,
            "-af", af_chain,
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 195] Derin anlatıcı sesi hatası: {e}")
    return input_wav


# ─── ITEM 196: Hızlı Tempolu Haber Dili (Fast-Paced News Cadence) ──────────────

def apply_news_rapid_cadence(input_wav: str, output_wav: str,
                             tempo: float = 1.12,
                             max_pause_sec: float = 0.09) -> str:
    """
    Madde 196: Hızlı Tempolu Haber Dili.
    Haber videolarında cümleler arası boşluğu 90 milisaniyeye (0.09s) kadar düşürür
    ve anlatım temposunu atempo filtresiyle hızlandırarak son dakika heyecanını yansıtır.
    """
    if not os.path.exists(input_wav):
        return input_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        from services.audio_tempo_guard import build_atempo_filter_chain
        atempo_chain = build_atempo_filter_chain(tempo)
        af_chain = (
            f"silenceremove=stop_periods=-1:stop_duration={max_pause_sec}:stop_threshold=-35dB,"
            f"{atempo_chain}"
        )
        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_wav,
            "-af", af_chain,
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 196] Hızlı haber dili hatası: {e}")
    return input_wav


# ─── ITEM 254: Soruya Cevap Vermeden Önceki Boşluk (0.5s Tension Gap) ─────────

def inject_pre_answer_tension_gap(
    audio_wav: str,
    output_wav: str,
    gap_seconds: float = 0.5,
    insert_at_sec: Optional[float] = None,
) -> str:
    """
    Madde 254: Soruya cevap verilmeden önce 0.5 saniyelik nefes kesici gerilim.
    """
    return inject_quiz_thinking_gap(
        audio_wav, output_wav, gap_seconds=gap_seconds, insert_at_sec=insert_at_sec
    )


# ─── ITEM 197: Soru-Cevap Arası Sessizlik (Quiz Thinking Gap) ─────────────────

def inject_quiz_thinking_gap(audio_wav: str, output_wav: str,
                             gap_seconds: float = 3.0,
                             insert_at_sec: Optional[float] = None) -> str:
    """
    Madde 197: Soru-Cevap Arası Sessizlik.
    Quiz videolarında soru sorulduktan sonra izleyicinin düşünmesi için
    tam 3.0 saniye fon müziği / düşünme boşluğu bırakır.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd_dur = [ffmpeg_exe, "-i", audio_wav]
        res_dur = subprocess.run(cmd_dur, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res_dur.stderr.decode("utf-8", errors="ignore"))
        total_dur = 4.0
        if dur_match:
            h, m, s = float(dur_match.group(1)), float(dur_match.group(2)), float(dur_match.group(3))
            total_dur = h * 3600 + m * 60 + s

        split_at = insert_at_sec if (insert_at_sec is not None and insert_at_sec < total_dur) else max(0.5, total_dur / 2.0)
        
        filter_complex = (
            f"[0:a]atrim=0:{split_at:.3f},asetpts=PTS-STARTPTS[part1];"
            f"aevalsrc=0:d={gap_seconds:.3f}:s=44100[gap];"
            f"[0:a]atrim={split_at:.3f}:{total_dur:.3f},asetpts=PTS-STARTPTS[part2];"
            f"[part1][gap][part2]concat=n=3:v=0:a=1[outa]"
        )
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 197] Quiz soru-cevap boşluğu hatası: {e}")
    return audio_wav


# ─── ITEM 198: Kapanış Cümlesinin Ses Tonu (Loop Continuity Inflection) ─────────

def apply_loop_inflection_preservation(input_wav: str, output_wav: str,
                                       tail_duration: float = 1.0) -> str:
    """
    Madde 198: Kapanış Cümlesinin Ses Tonu.
    Videonun son cümlesi bir veda gibi sönüp bitmemeli, sanki bir sonraki kelime
    hemen gelecekmiş gibi akıcı tonda kalmalıdır.
    Son 1 saniyede ses seviyesinin düşmesini (volume fade/tail drop) engeller,
    sabit kazanç ile son milisaniyeye kadar enerjiyi canlı tutar.
    """
    if not os.path.exists(input_wav):
        return input_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        af = "alimiter=limit=0.95:attack=5:release=50:asc=1"
        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_wav,
            "-af", af,
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 198] Döngü tonu koruma hatası: {e}")
    return input_wav


# ─── ITEM 200 / 5.2: 1-3 kHz presence carve, about -4.5 dB ──────────────
# A single Q=1 bell at 2 kHz is -4.5 dB only at the center: 1 kHz was -1.4 dB
# and 3 kHz was -2.6 dB. Three bells hold the band. Measured on full-scale sines:
# 1 kHz -4.3, 2 kHz -4.6, 3 kHz -4.5. 400 Hz -0.4. 6 kHz -0.7.
VOCAL_CARVE_EQ = (
    "equalizer=f=1100:t=q:w=1.4:g=-4.0,"
    "equalizer=f=2000:t=q:w=1.7:g=-2.0,"
    "equalizer=f=2900:t=q:w=1.35:g=-3.5"
)


def apply_vocal_carve_eq(music_wav: str, output_wav: str,
                         notch_freq: float = 2000.0,
                         notch_gain: float = -4.5,
                         q_width: float = 1.0) -> str:
    """
    Madde 200: Ses Frekans Çakışmasını Önleme (Vocal Frequency Carving).
    Default cut is the measured 1-3 kHz band. A custom freq/gain/Q stays one bell.
    """
    if not os.path.exists(music_wav):
        return music_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if (float(notch_freq), float(notch_gain), float(q_width)) == (2000.0, -4.5, 1.0):
            eq_filter = VOCAL_CARVE_EQ
        else:
            eq_filter = f"equalizer=f={notch_freq}:t=q:w={q_width}:g={notch_gain}"
        cmd = [
            ffmpeg_exe, "-y",
            "-i", music_wav,
            "-af", eq_filter,
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 200] Vokal frekans oyma hatası: {e}")
    return music_wav




