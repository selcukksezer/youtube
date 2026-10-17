"""
Synthesized SFX Layers (Items 159–192): Typewriter, Quiz Ding/Buzzer, Swallow,
Vinyl Crackle, Dramatic Piano, Cyberpunk Synth Bass, Stereo Pan, Crowd Ambience, Sub-Kick.
Extracted from `voice/acoustic_assets.py`.
"""
import os, math, wave, struct, random, subprocess
import imageio_ffmpeg
import config

SFX_DIR = os.path.join(config.BASE_DIR, "assets", "sfx")
os.makedirs(SFX_DIR, exist_ok=True)

# ─── ITEM 159: Daktilo Sesi (Typewriter SFX) ──────────────────────────────────

def ensure_typewriter_sfx(output_path: str = None, duration: float = 2.0, speed_cps: float = 11.0) -> str:
    """
    Madde 159: Daktilo Sesi (Typewriter SFX).
    Ekrana tek tek harf veya belge ifşası dökülürken çalışan mikro mekanik tuş vuruşları.
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, f"typewriter_{int(duration)}s.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    # Tuş vuruş anları (ortalama speed_cps karakter/sn, hafif insanlaştırma jitter'ı ile)
    stroke_interval = 1.0 / speed_cps
    stroke_times = []
    curr_t = 0.04
    while curr_t < duration - 0.05:
        stroke_times.append(curr_t)
        curr_t += stroke_interval * random.uniform(0.75, 1.25)

    for i in range(num_samples):
        t = i / sample_rate
        val = 0.0

        for st in stroke_times:
            if st <= t < st + 0.035:
                dt = t - st
                env = math.exp(-dt * 180.0)
                # Mekanik vuruş metal tıkı + gürültü patlaması
                click = math.sin(2 * math.pi * random.choice([3100.0, 3600.0, 2800.0]) * dt) * 0.5
                noise = (random.random() * 2.0 - 1.0) * 0.5
                val += (click + noise) * env * 0.8
                break

        val = max(-1.0, min(1.0, val))
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 159] 2s Daktilo SFX sentezlendi → {output_path}")
    return output_path


def inject_typewriter_sfx(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0,
                          duration: float = 2.0, volume: float = 0.35) -> str:
    """
    Madde 159: Ekrana metin/harf düşerken mikro daktilo sesini miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    typewriter_sfx = ensure_typewriter_sfx(duration=duration)
    if not os.path.exists(typewriter_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        delay_ms = max(0, int(timestamp_sec * 1000))
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-i", typewriter_sfx,
            "-filter_complex",
            f"[1:a]volume={volume},adelay={delay_ms}|{delay_ms}[tw];[0:a][tw]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 159] Daktilo sesi miks hatası: {e}")

    return audio_wav


# ─── ITEM 167: Quiz Doğru Cevap Ding Sesi (1800Hz Kristal Zil Frekansı) ────────

def ensure_quiz_ding_sfx(output_path: str = None, freq_hz: float = 1800.0, duration: float = 0.45) -> str:
    """
    Madde 167: Ding Sesinin Frekansı.
    Quiz nişinde doğru cevap açıklandığında gelen 'Ding' sesi 1800Hz kristal zil frekansında olmalıdır.
    Sentez: 1800Hz saf sinüs temeli + 3600Hz ışıltılı harmonik, hızlı atak ve yumuşak üstel sönümlenme.
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, f"quiz_ding_{int(freq_hz)}hz.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    for i in range(num_samples):
        t = i / sample_rate
        # Hızlı vurmalı atak (5ms) + üstel sönümlenme
        attack = min(1.0, t / 0.005)
        decay = math.exp(-t * 9.5)
        env = attack * decay

        # 1800Hz kristal fundamental + 3600Hz 2. harmonik parıltı
        fundamental = math.sin(2 * math.pi * freq_hz * t)
        sparkle = math.sin(2 * math.pi * (freq_hz * 2.0) * t) * 0.22
        val = (fundamental * 0.78 + sparkle) * env * 0.85
        val = max(-1.0, min(1.0, val))

        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 167] 1800Hz Quiz Ding SFX sentezlendi → {output_path}")
    return output_path


def inject_quiz_ding(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0,
                     volume: float = 0.55) -> str:
    """
    Madde 167: Doğru cevap anında 1800Hz kristal zil sesini miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    ding_sfx = ensure_quiz_ding_sfx()
    if not os.path.exists(ding_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        delay_ms = max(0, int(timestamp_sec * 1000))
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-i", ding_sfx,
            "-filter_complex",
            f"[1:a]volume={volume},adelay={delay_ms}|{delay_ms}[ding];[0:a][ding]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 167] Ding miks hatası: {e}")

    return audio_wav


# ─── ITEM 168: Quiz Hatalı Buzzer Sesi (120Hz Testere Dişi / Sawtooth Dalga) ───

def ensure_quiz_buzzer_sfx(output_path: str = None, freq_hz: float = 120.0, duration: float = 0.55) -> str:
    """
    Madde 168: Hatalı Buzzer Sesi.
    Yanlış cevapta kullanılan 'Buzzer' sesi 120Hz testere dişi (sawtooth) dalga olmalıdır.
    Sentez: 120Hz sert testere dişi dalga (sawtooth) + hafif kare dalga distorsiyonu ile
    klasik TV quiz 'yanlış cevap' cızırtılı vızıltı sesi üretir.
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, f"quiz_buzzer_{int(freq_hz)}hz.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    for i in range(num_samples):
        t = i / sample_rate
        # Buzzer zarfı: net vuruş, 0.45s süresince düz kalıp son 0.1s hızlı kapanış
        if t < 0.45:
            env = min(1.0, t / 0.008)
        else:
            env = max(0.0, 1.0 - (t - 0.45) / 0.1)

        # 120Hz testere dişi (sawtooth): periyot boyunca -1 ile +1 arasında lineer artış
        phase = (t * freq_hz) % 1.0
        saw = 2.0 * phase - 1.0

        # İkincil harmonik (240Hz) ve hafif kare dalga doygunluğu ile vintage buzzer sertliği
        harmonic = math.sin(2 * math.pi * (freq_hz * 2.0) * t) * 0.25
        raw_val = (saw * 0.75 + harmonic) * env * 0.75
        val = max(-1.0, min(1.0, raw_val))

        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 168] 120Hz Sawtooth Quiz Buzzer SFX sentezlendi → {output_path}")
    return output_path


def inject_quiz_buzzer(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0,
                       volume: float = 0.5) -> str:
    """
    Madde 168: Hatalı cevap anında 120Hz testere dişi buzzer sesini miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    buzzer_sfx = ensure_quiz_buzzer_sfx()
    if not os.path.exists(buzzer_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        delay_ms = max(0, int(timestamp_sec * 1000))
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-i", buzzer_sfx,
            "-filter_complex",
            f"[1:a]volume={volume},adelay={delay_ms}|{delay_ms}[buzz];[0:a][buzz]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 168] Buzzer miks hatası: {e}")

    return audio_wav


# ─── ITEM 177: Doğal Yutkunma ve Duraksama (Natural Swallow & Monologue Pause) ─

def ensure_swallow_sound(output_path: str = None) -> str:
    """
    Madde 177: Doğal Yutkunma ve Duraksama.
    Uzun monologlarda robotik kesintisizliği kırmak için hafif, organik bir boğaz rahatlatma /
    yutkunma mikro sesi sentezler (220ms, yumuşak rezonans kayması 180Hz -> 130Hz).
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, "natural_swallow.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    dur = 0.22
    num_samples = int(sample_rate * dur)
    frames = bytearray()

    for i in range(num_samples):
        t = i / sample_rate
        progress = t / dur

        # Çift fazlı hafif yutkunma zarfı
        if progress < 0.35:
            env = math.sin(math.pi * (progress / 0.35)) ** 1.8 * 0.7
        else:
            env = math.sin(math.pi * ((progress - 0.35) / 0.65)) ** 2.0 * 1.0

        # Frekans yavaşça 180Hz'den 125Hz'e kayar
        freq = 180.0 - (progress * 55.0)
        tone = math.sin(2 * math.pi * freq * t) * 0.45
        noise = (random.random() * 2.0 - 1.0) * 0.18
        val = (tone + noise) * env * 0.18
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 177] Doğal yutkunma sesi sentezlendi (220ms) → {output_path}")
    return output_path


def inject_monologue_pause_and_swallow(audio_wav: str, output_wav: str,
                                       interval_seconds: float = 40.0,
                                       volume: float = 0.25) -> str:
    """
    Madde 177: Uzun monologlarda (özellikle 40 saniyeyi aşan anlatımlarda),
    her 40 saniyede bir doğal bir duraksama ve hafif yutkunma katmanı ekler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    swallow_sfx = ensure_swallow_sound()
    if not os.path.exists(swallow_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        probe = subprocess.run(
            [ffmpeg_exe, "-i", audio_wav, "-hide_banner"],
            capture_output=True, text=True
        )
        import re
        dur_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
        duration = 60.0
        if dur_match:
            h, m, s = int(dur_match.group(1)), int(dur_match.group(2)), float(dur_match.group(3))
            duration = h * 3600 + m * 60 + s

        # 40 saniye aralıklarla duraksama zaman noktaları hesapla
        pause_times = []
        curr = interval_seconds
        while curr < duration - 4.0:
            pause_times.append(curr)
            curr += interval_seconds

        if not pause_times:
            # 40 saniyenin altındaki videolarda test amaçlı veya kısa videolarda ortada hafifçe uygula
            pause_times = [min(duration * 0.5, interval_seconds)]

        inputs = ["-i", audio_wav]
        filter_parts = []
        mix_inputs = ["[0:a]"]

        for idx, pt in enumerate(pause_times, start=1):
            inputs.extend(["-i", swallow_sfx])
            delay_ms = max(0, int(pt * 1000))
            filter_parts.append(f"[{idx}:a]volume={volume},adelay={delay_ms}|{delay_ms}[sw{idx}]")
            mix_inputs.append(f"[sw{idx}]")

        total = len(mix_inputs)
        filter_str = ";".join(filter_parts) + f";{''.join(mix_inputs)}amix=inputs={total}:duration=first:dropout_transition=0:normalize=0[out]"

        cmd = [
            ffmpeg_exe, "-y",
            *inputs,
            "-filter_complex", filter_str,
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 177] Yutkunma ve duraksama enjeksiyon hatası: {e}")

    return audio_wav



from .acoustic_sfx_presets import (
    apply_stereo_pan_movement,
    ensure_crowd_room_ambience,
    ensure_cyberpunk_synth_bass_sfx,
    ensure_dramatic_piano_note_sfx,
    ensure_sub_kick_sfx,
    ensure_vinyl_crackle_sfx,
    inject_cyberpunk_synth_bass,
    inject_dramatic_piano_layer,
    inject_room_ambience,
    inject_sub_kick_hit,
    inject_vinyl_crackle_layer,
)
