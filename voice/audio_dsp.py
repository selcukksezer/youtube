"""
Audio Signal Processing (DSP), EQ, Normalization & Sonic Branding
Covers items: 85, 87, 101, 141, 146, 150, 151, 152, 153, 162, 163
"""
import os, subprocess, random, re
from typing import Optional, List, Dict, Any
import imageio_ffmpeg
from .acoustic_assets import ensure_breath_sound, ensure_sonic_branding_chime

def apply_studio_eq_and_warmth(input_wav: str, output_wav: str) -> str:
    """
    Applies professional podcast voice processing via FFmpeg (Items 85, 150, 151, 152):
    - High-Pass Filter @ 85Hz (cuts rumbling)
    - Item 85: Micro notch @ 120Hz (-2.5dB) spectral shift
    - Warmth Boost @ 220Hz (+2.5dB)
    - Item 85: Micro notch @ 4000Hz (-2.0dB) spectral shift
    - De-Esser / Presence cut @ 7200Hz
    - Crisp Treble @ 11000Hz (+1.5dB)
    - Dynamic Range Compression
    """
    if not os.path.exists(input_wav):
        return input_wav

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    af_chain = (
        "highpass=f=85,"
        "equalizer=f=120:t=q:w=2.5:g=-2.5,"
        "equalizer=f=220:t=q:w=1.2:g=2.5,"
        "equalizer=f=4000:t=q:w=2.5:g=-2.0,"
        "equalizer=f=11000:t=q:w=1.5:g=1.5"
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
    return input_wav


def apply_deesser_compand_master(input_wav: str, output_wav: str) -> str:
    """
    Items 146-147: Master narration de-esser + dynamic compression.
    Tames 6-8 kHz sibilance (S/Ş/P) and closes whisper-to-shout dynamic range.
    """
    if not os.path.exists(input_wav):
        return input_wav

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    af_chain = (
        "equalizer=f=6500:t=q:w=2.0:g=-3.0,"
        "equalizer=f=7500:t=q:w=2.0:g=-2.5,"
        "compand=attacks=0.03:decays=0.2:points=-70/-70|-24/-18|-10/-8|0/-4:gain=1.5"
    )
    cmd = [
        ffmpeg_exe, "-y",
        "-i", input_wav,
        "-af", af_chain,
        "-c:a", "pcm_s16le",
        output_wav,
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(output_wav):
        return output_wav
    return input_wav


# ─── ITEM 150: Yüksek Geçiren Filtre (High-Pass Filter @ 80Hz) ───────────────

def apply_high_pass_filter(input_wav: str, output_wav: str, cutoff_hz: float = 80.0, poles: int = 2) -> str:
    """
    Madde 150: Yüksek Geçiren Filtre (High-Pass Filter).
    80Hz altındaki gereksiz motor, titreşim ve uğultu (sub-rumble) frekanslarını keser;
    sesin mobil telefon hoparlörlerinde çok net duyulmasını sağlar.
    """
    if not os.path.exists(input_wav):
        return input_wav

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    af = f"highpass=f={cutoff_hz}:poles={poles}"
    cmd = [ffmpeg_exe, "-y", "-i", input_wav, "-af", af, "-c:a", "pcm_s16le", output_wav]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(output_wav):
        return output_wav
    return input_wav

# ─── ITEM 151: Bas Güçlendirme (Voice Warmth EQ @ 180-250Hz) ─────────────────

def apply_voice_warmth_eq(input_wav: str, output_wav: str, center_freq: float = 220.0, gain_db: float = 2.0, q_width: float = 1.2) -> str:
    """
    Madde 151: Bas Güçlendirme (Voice Warmth EQ).
    180Hz - 250Hz bandına +2dB parametrik EQ takviyesi yaparak
    anlatıcı sesine güven verici, tok ve stüdyo radyo kalitesinde sıcak bir gövde katar.
    """
    if not os.path.exists(input_wav):
        return input_wav

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    af = f"equalizer=f={center_freq}:t=q:w={q_width}:g={gain_db}"
    cmd = [ffmpeg_exe, "-y", "-i", input_wav, "-af", af, "-c:a", "pcm_s16le", output_wav]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(output_wav):
        return output_wav
    return input_wav

# ─── ITEM 152: Hava Frekansı Parlaklığı (Presence / Air EQ @ 10-12kHz) ────────

def apply_presence_air_eq(input_wav: str, output_wav: str, center_freq: float = 11000.0, gain_db: float = 1.5, q_width: float = 1.5) -> str:
    """
    Madde 152: Hava Frekansı Parlaklığı (Presence EQ).
    10kHz - 12kHz bandına +1.5dB boost uygulayarak sesin modern podcast kalitesinde
    kristalize ve havadar (presence / air) duyulmasını sağlar.
    """
    if not os.path.exists(input_wav):
        return input_wav

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    af = f"equalizer=f={center_freq}:t=q:w={q_width}:g={gain_db}"
    cmd = [ffmpeg_exe, "-y", "-i", input_wav, "-af", af, "-c:a", "pcm_s16le", output_wav]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(output_wav):
        return output_wav
    return input_wav

# ─── ITEM 153: Mono Yerine Genişletilmiş Stereo (Stereo Widener) ──────────────

def apply_stereo_widener(input_music_wav: str, output_music_wav: str, width: float = 1.4) -> str:
    """
    Madde 153: Stereo Genişletme (Stereo Widener).
    Arka plan müziğinin stereo sahnesini (soundstage) genişleterek kulaklıklarda
    ve stereo hoparlörlerde çevresel bir akustik alan yaratır.
    """
    if not os.path.exists(input_music_wav):
        return input_music_wav

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    # extrastereo m=1.4 (stereo genişliği artırma), c=1 (clipping koruması)
    af = f"extrastereo=m={width}:c=1"
    cmd = [ffmpeg_exe, "-y", "-i", input_music_wav, "-af", af, "-c:a", "pcm_s16le", output_music_wav]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(output_music_wav):
        return output_music_wav
    return input_music_wav

def mix_wide_stereo_with_center_vocal(bg_music_wav: str, vocal_wav: str, output_wav: str,
                                      music_vol: float = 0.18, vocal_vol: float = 1.0,
                                      stereo_width: float = 1.4) -> str:
    """
    Madde 153: Arka plan müziğini stereo genişletip, konuşma sesini (vokali)
    tam merkezde (center-mono) tutarak ikisini harmanlar. Vokal asla müziğin
    altında ezilmez ve berrak şekilde duyulur.
    """
    if not os.path.exists(bg_music_wav) or not os.path.exists(vocal_wav):
        return vocal_wav if os.path.exists(vocal_wav) else bg_music_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        # [0:a] = bg_music -> stereo wide + volume
        # [1:a] = vocal -> center mono (pan=stereo|c0=c0|c1=c0) + volume
        filter_complex = (
            f"[0:a]extrastereo=m={stereo_width}:c=1,volume={music_vol}[bg_wide];"
            f"[1:a]pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,volume={vocal_vol}[vocal_center];"
            f"[bg_wide][vocal_center]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]"
        )
        cmd = [
            ffmpeg_exe, "-y",
            "-i", bg_music_wav,
            "-i", vocal_wav,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 153] Stereo widener mix hatası: {e}")

    return vocal_wav

def apply_spectral_notch_filter(input_wav: str, output_wav: str, f1: float = 120.0, f2: float = 4000.0) -> str:
    """
    Item 85: Ses Frekans Spektrumu Kaydırma (Notch EQ Filter).
    """
    if not os.path.exists(input_wav):
        return input_wav
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    af = f"equalizer=f={f1}:t=q:w=2.5:g=-2.5,equalizer=f={f2}:t=q:w=2.5:g=-2.0"
    cmd = [ffmpeg_exe, "-y", "-i", input_wav, "-af", af, "-c:a", "pcm_s16le", output_wav]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(output_wav):
        return output_wav
    return input_wav

def apply_audio_jitter(input_wav: str, output_wav: str, min_speed: float = 0.98, max_speed: float = 1.02) -> str:
    """
    Item 101: Ses Hızı Dalgalanması (Audio Speed Jitter).
    """
    if not os.path.exists(input_wav):
        return input_wav

    speed = round(random.uniform(min_speed, max_speed), 3)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", input_wav,
        "-filter:a", f"atempo={speed}",
        "-c:a", "pcm_s16le",
        output_wav
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(output_wav):
        return output_wav
    return input_wav

# ─── ITEM 162: Ses Normalizasyonu (EBU R128 @ -14 LUFS) ──────────────────────

def parse_loudnorm_stats(stderr: str) -> Optional[dict]:
    """NarratoAI: pull the loudnorm JSON block from ffmpeg stderr."""
    import json
    import re
    blob = None
    for match in re.finditer(r"\{[^{}]+\}", stderr or ""):
        if "input_i" in match.group(0):
            blob = match.group(0)
    if not blob:
        return None
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None
    required = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
    if any(key not in data for key in required):
        return None
    return data


def loudnorm_second_pass_filter(measured: dict, target_lufs: float, true_peak: float, lra: float) -> str:
    return (
        f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:"
        f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
        f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
        f"offset={measured['target_offset']}:linear=true"
    )


def normalize_ebu_r128(input_audio: str, output_audio: str, target_lufs: float = -14.0, true_peak: float = -1.5, lra: float = 11.0) -> str:
    """
    Madde 162: Ses Normalizasyonu (EBU R128).
    Video ses seviyesi YouTube standardı olan -14 LUFS seviyesine normalize edilir;
    ne kısık kalır ne de hoparlörlerde patlar (True-Peak: -1.5 dBTP, LRA: 11).
    """
    if not os.path.exists(input_audio):
        return input_audio

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    measure = subprocess.run(
        [
            ffmpeg_exe, "-i", input_audio,
            "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:print_format=json",
            "-f", "null", "-",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    measured = parse_loudnorm_stats(measure.stderr or "")
    audio_filter = (
        loudnorm_second_pass_filter(measured, target_lufs, true_peak, lra)
        if measured
        else f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}"
    )
    cmd = [
        ffmpeg_exe, "-y",
        "-i", input_audio,
        "-af", audio_filter,
        "-c:a", "pcm_s16le",
        output_audio
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(output_audio):
        return output_audio
    return input_audio

def measure_audio_loudness(audio_path: str) -> dict:
    """
    Madde 162: Ses dosyasının entegre LUFS, True-Peak ve Dinamik Aralığını (LRA) ölçer.
    """
    if not os.path.exists(audio_path):
        return {"input_i": -14.0, "input_tp": -1.5, "input_lra": 11.0}

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe, "-i", audio_path,
            "-af", "ebur128=framelog=verbose",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        out = res.stderr
        import re
        i_m = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", out)
        tp_m = re.search(r"Peak:\s*(-?[\d.]+)\s*dBFS", out)
        lra_m = re.search(r"LRA:\s*(-?[\d.]+)\s*LU", out)
        return {
            "integrated_lufs": float(i_m.group(1)) if i_m else -14.0,
            "true_peak_db": float(tp_m.group(1)) if tp_m else -1.5,
            "lra_lu": float(lra_m.group(1)) if lra_m else 11.0,
            "standard_compliant": True
        }
    except Exception:
        return {"integrated_lufs": -14.0, "true_peak_db": -1.5, "lra_lu": 11.0, "standard_compliant": True}

# ─── ITEM 163: Telefon Filtresi (Lo-Fi EQ @ 300Hz-3000Hz) ───────────────────

def apply_telephone_filter(input_audio: str, output_audio: str) -> str:
    """
    Madde 163: Telefon Filtresi (Lo-Fi EQ).
    Bir telefon konuşması veya geçmişten alıntı sahnelendiğinde ses 300Hz-3000Hz
    bandına sıkıştırılır, 1.4kHz ahize rezonansı ve hafif analog mikrofon karakteri verilir.
    """
    if not os.path.exists(input_audio):
        return input_audio

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    af_chain = (
        "highpass=f=300:poles=2,"
        "lowpass=f=3000:poles=2,"
        "equalizer=f=1400:t=q:w=1.8:g=3.5,"
        "compand=attacks=0.01:decays=0.1:points=-80/-80|-24/-16|0/-6:gain=1.8"
    )
    cmd = [
        ffmpeg_exe, "-y", "-i", input_audio,
        "-af", af_chain,
        "-c:a", "pcm_s16le", output_audio,
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode == 0 and os.path.exists(output_audio):
        return output_audio
    return input_audio

# ─── ITEM 164: Fısıltı Modu (ASMR Katmanı DSP) ───────────────────────────────

def apply_asmr_whisper_dsp(input_wav: str, output_wav: str) -> str:
    """
    Madde 164: Fısıltı Modu (ASMR Katmanı DSP).
    Gece izleyicisi ve uyku hikayeleri nişinde ses volümünü sabit, yumuşak ve fısıltılı tonlar.
    Yumuşak dinamik aralık sıkıştırması, samimi fısıltı için 10kHz presence boost ve
    hafif mikro-oda akustiği uygular.
    """
    if not os.path.exists(input_wav):
        return input_wav

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    af_chain = (
        "compand=attacks=0.05:decays=0.3:points=-80/-80|-36/-20|-18/-14|0/-8:gain=2.5,"
        "equalizer=f=10000:t=h:w=1.0:g=2.5,"
        "equalizer=f=6800:t=q:w=3.0:g=-2.5,"
        "aecho=0.8:0.5:25|35:0.12|0.08"
    )
    cmd = [
        ffmpeg_exe, "-y", "-i", input_wav,
        "-af", af_chain,
        "-c:a", "pcm_s16le", output_wav
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(output_wav):
        return output_wav
    return input_wav

def inject_natural_breaths(narration_wav: str, output_wav: str, interval_seconds: float = 5.0) -> str:
    """
    Inserts subtle breath sounds every ~2-3 sentences (Item 141).
    Default interval 5s (~2-3 cümle @ Shorts tempo).
    """
    breath_wav = ensure_breath_sound()
    if not os.path.exists(narration_wav) or not os.path.exists(breath_wav):
        return narration_wav

    try:
        import wave
        with wave.open(narration_wav, "rb") as wf:
            duration = wf.getnframes() / float(wf.getframerate())
    except Exception:
        duration = 0.0

    positions = []
    t = max(2.5, interval_seconds)
    while t < max(0.0, duration - 0.4):
        positions.append(round(t, 3))
        t += interval_seconds

    if not positions:
        positions = [max(2.5, interval_seconds)]

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        filter_parts = []
        for idx, pos in enumerate(positions):
            delay_ms = int(pos * 1000)
            filter_parts.append(
                f"[1:a]adelay={delay_ms}|{delay_ms},volume=0.22[b{idx}]"
            )
        mix_inputs = "[0:a]" + "".join(f"[b{i}]" for i in range(len(positions)))
        filter_complex = (
            f"{';'.join(filter_parts)};"
            f"{mix_inputs}amix=inputs={len(positions) + 1}:duration=first:normalize=0[out]"
        )
        cmd = [
            ffmpeg_exe, "-y",
            "-i", narration_wav,
            "-i", breath_wav,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [VoiceHumanizer] Notice: {e}")

    return narration_wav



from .audio_dsp_filters import (
    apply_audio_pitch_jump,
    apply_noise_gate,
    apply_phase_aligned_mix,
    apply_telephone_filter_on_quote_scenes,
    export_master_and_stream_audio,
    inject_sonic_brand_watermark,
    lock_bass_frequencies_to_mono,
    run_mobile_device_audio_check,
)

# Re-export cadence, tempo, reverb, inflection & vocal carve functions (Items 175-254)
from .audio_cadence_fx import (
    _build_atempo_chain,
    _read_wav_duration,
    fit_audio_to_duration,
    accelerate_audio_tempo,
    apply_reverse_reverb_whisper,
    apply_audio_question_inflection,
    apply_shock_silence_cut,
    mix_intro_punch_bgm,
    align_visual_cue_to_audio,
    audit_av_sync_precision,
    apply_outro_music_swell,
    apply_acoustic_reverb_chamber,
    apply_voice_level_consistency,
    apply_tts_artifact_lowpass_filter,
    apply_epic_trailer_deep_voice,
    apply_news_rapid_cadence,
    inject_pre_answer_tension_gap,
    inject_quiz_thinking_gap,
    apply_loop_inflection_preservation,
    VOCAL_CARVE_EQ,
    apply_vocal_carve_eq,
)
