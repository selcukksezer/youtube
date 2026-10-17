"""Synthesized SFX Presets (Items 181-192): Vinyl Crackle, Dramatic Piano, Cyberpunk Synth Bass, Stereo Pan, Crowd Ambience, Sub-Kick."""
import os, math, wave, struct, random, subprocess
import imageio_ffmpeg
import config

SFX_DIR = os.path.join(config.BASE_DIR, "assets", "sfx")
os.makedirs(SFX_DIR, exist_ok=True)

# ─── ITEM 181: Hafif Vinil Cızırtısı (Vinyl Crackle @ -28dB) ──────────────────

def ensure_vinyl_crackle_sfx(output_path: str = None, duration: float = 15.0, volume_db: float = -28.0) -> str:
    """
    Madde 181: Hafif Vinil Cızırtısı (Vinyl Crackle).
    Tarihi, gizemli ve nostaljik nişlerde arka plana -28dB seviyesinde otantik analog
    plak cızırtısı (döner tabla sürtünmesi + rastgele Poisson çıtırtı/pop patlamaları) sentezler.
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, f"vinyl_crackle_{int(duration)}s.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    amp_linear = 10.0 ** (volume_db / 20.0)  # -28dB ≈ 0.0398

    # Poisson tıklama/çıtırtı frekansı (saniyede ortalama 25-35 mikro çıtırtı)
    click_prob = 30.0 / sample_rate

    # Düşük frekans pikap motor uğultusu (turntable rumble @ 42Hz)
    running_click_env = 0.0

    for i in range(num_samples):
        t = i / sample_rate

        # 1. 42Hz mekanik vinil motor uğultusu
        rumble = math.sin(2 * math.pi * 42.0 * t) * 0.15

        # 2. İnce yüzey tozu beyaz gürültü hissi (hiss)
        hiss = (random.random() * 2.0 - 1.0) * 0.22

        # 3. Rastgele çıtırtı impulsu (crackle/pop)
        if random.random() < click_prob:
            running_click_env = random.uniform(0.6, 1.0)

        click_val = 0.0
        if running_click_env > 0.001:
            click_val = (random.random() * 2.0 - 1.0) * running_click_env
            running_click_env *= 0.82  # Hızlı üstel sönümlenme

        combined = (rumble + hiss + click_val) * amp_linear * 1.2
        val = max(-1.0, min(1.0, combined))
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 181] Vinyl Crackle SFX sentezlendi ({duration}s @ {volume_db}dB) → {output_path}")
    return output_path


def inject_vinyl_crackle_layer(audio_wav: str, output_wav: str, volume_db: float = -28.0) -> str:
    """
    Madde 181: Tarihi ve nostaljik videolarda arka plana -28dB vinil plak cızırtısı miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    crackle_sfx = ensure_vinyl_crackle_sfx(volume_db=volume_db)
    if not os.path.exists(crackle_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-stream_loop", "-1",
            "-i", crackle_sfx,
            "-filter_complex",
            f"[1:a]volume=1.0[crk];[0:a][crk]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 181] Vinyl crackle miks hatası: {e}")

    return audio_wav


# ─── ITEM 182: Dramatik Keman/Piyano Katmanı (Dramatic Piano Note SFX) ────────

def ensure_dramatic_piano_note_sfx(output_path: str = None, note_freq: float = 220.0, duration: float = 3.5) -> str:
    """
    Madde 182: Dramatik Keman/Piyano Katmanı.
    Duygusal, felsefi ve dokunaklı hikayelerde derin ve yankılı tek nota kuyruklu piyano tınısı (A3 / 220Hz)
    + harmonikler + akustik gövde rezonansı sentezler.
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, f"dramatic_piano_{int(note_freq)}hz.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    # Piyano tel harmonikleri (1x, 2x, 3x, 4x, 5x, 6x)
    harmonics = [(1.0, 1.0), (2.0, 0.45), (3.0, 0.25), (4.0, 0.12), (5.0, 0.08), (6.0, 0.04)]

    for i in range(num_samples):
        t = i / sample_rate
        # Piyano vuruş çekici atağı (3ms) ve uzun rezonanslı sönümlenme
        attack = min(1.0, t / 0.003)
        decay = math.exp(-t * 1.35)
        env = attack * decay

        sample_val = 0.0
        for mult, weight in harmonics:
            f = note_freq * mult
            # Hafif faz detune ile zengin kuyruklu piyano rezonansı
            detune = math.sin(2 * math.pi * 0.5 * t) * 0.3
            sample_val += math.sin(2 * math.pi * (f + detune) * t) * weight

        val = sample_val * env * 0.42
        val = max(-1.0, min(1.0, val))
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 182] Dramatik Piyano Notası SFX sentezlendi ({note_freq}Hz, {duration}s) → {output_path}")
    return output_path


def inject_dramatic_piano_layer(audio_wav: str, output_wav: str,
                                timestamp_sec: float = 0.0,
                                volume: float = 0.35) -> str:
    """
    Madde 182: Duygusal açıklama anında tek nota dramatik piyano tınısını miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    piano_sfx = ensure_dramatic_piano_note_sfx()
    if not os.path.exists(piano_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        delay_ms = max(0, int(timestamp_sec * 1000))
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-i", piano_sfx,
            "-filter_complex",
            f"[1:a]volume={volume},adelay={delay_ms}|{delay_ms}[pno];[0:a][pno]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 182] Dramatik piyano miks hatası: {e}")

    return audio_wav


# ─── ITEM 183: Cyberpunk Synthwave Basları (Analog Synth Bass Pulse) ───────────

def ensure_cyberpunk_synth_bass_sfx(output_path: str = None, duration: float = 4.0, freq_hz: float = 55.0) -> str:
    """
    Madde 183: Cyberpunk Synthwave Basları.
    Teknoloji, yapay zeka ve gelecek haberlerinde izleyici dikkat süresini artırmak için
    derin, analog synthesizer testere dişi (sawtooth) ve 55Hz sub-bas darbe katmanı sentezler.
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, f"cyberpunk_synth_bass_{int(freq_hz)}hz.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    for i in range(num_samples):
        t = i / sample_rate

        # 2Hz LFO darbe modülasyonu (ritmik synthwave kalp atışı)
        lfo = 0.65 + 0.35 * math.sin(2 * math.pi * 2.0 * t)

        # 55Hz testere dişi (A1) analog synthesizer temeli
        phase = (t * freq_hz) % 1.0
        saw = 2.0 * phase - 1.0

        # Sub-oktav sinüs (27.5Hz sub-bass ağırlığı)
        sub_sine = math.sin(2 * math.pi * (freq_hz * 0.5) * t) * 0.85

        # 2. harmonik parıltı (110Hz)
        spark = math.sin(2 * math.pi * (freq_hz * 2.0) * t) * 0.25

        # Attack ve kapanış zarfı
        env = min(1.0, t / 0.05) * min(1.0, (duration - t) / 0.1)
        raw_val = (saw * 0.5 + sub_sine * 0.6 + spark * 0.2) * lfo * env * 0.65
        val = max(-1.0, min(1.0, raw_val))

        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 183] Cyberpunk Synth Bass SFX sentezlendi ({freq_hz}Hz, {duration}s) → {output_path}")
    return output_path


def inject_cyberpunk_synth_bass(audio_wav: str, output_wav: str,
                                timestamp_sec: float = 0.0,
                                volume: float = 0.35) -> str:
    """
    Madde 183: Teknoloji ve yapay zeka sahnelerinde alttan cyberpunk synthwave bası miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    synth_sfx = ensure_cyberpunk_synth_bass_sfx()
    if not os.path.exists(synth_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        delay_ms = max(0, int(timestamp_sec * 1000))
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-i", synth_sfx,
            "-filter_complex",
            f"[1:a]volume={volume},adelay={delay_ms}|{delay_ms}[syn];[0:a][syn]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 183] Cyberpunk synth bass miks hatası: {e}")

    return audio_wav


# ─── ITEM 187: Stereo Pan Hareketi (Stereo Pan Motion) ────────────────────────

def apply_stereo_pan_movement(sfx_wav: str, output_wav: str,
                              direction: str = "left_to_right",
                              duration: float = 0.35) -> str:
    """
    Madde 187: Stereo Pan Hareketi.
    Bir nesne veya geçiş soldan sağa kayarken Whoosh efektini de
    sol kulaklıktan sağ kulaklığa akıcı şekilde taşır.
    Eşit güç (equal-power) sinüs/kosinüs pan yasası kullanarak
    temiz stereo PCM WAV üretir.
    """
    if not os.path.exists(sfx_wav):
        return sfx_wav

    try:
        with wave.open(sfx_wav, "rb") as wf_in:
            n_channels = wf_in.getnchannels()
            sampwidth = wf_in.getsampwidth()
            framerate = wf_in.getframerate()
            n_frames = wf_in.getnframes()
            raw_data = wf_in.readframes(n_frames)

        if sampwidth != 2:
            return sfx_wav

        total_samples = n_frames * n_channels
        samples = struct.unpack(f"<{total_samples}h", raw_data)

        if n_channels == 2:
            mono_samples = [(samples[i * 2] + samples[i * 2 + 1]) // 2 for i in range(n_frames)]
        else:
            mono_samples = samples

        pan_frames = min(n_frames, max(1, int(framerate * duration)))
        out_frames = bytearray()

        for i, s in enumerate(mono_samples):
            if i < pan_frames:
                frac = i / float(pan_frames)
            else:
                frac = 1.0 if direction == "left_to_right" else 0.0

            if direction == "left_to_right":
                left_gain = math.cos(frac * (math.pi / 2.0))
                right_gain = math.sin(frac * (math.pi / 2.0))
            else:
                left_gain = math.sin(frac * (math.pi / 2.0))
                right_gain = math.cos(frac * (math.pi / 2.0))

            left_val = int(s * left_gain)
            right_val = int(s * right_gain)
            left_clamped = max(-32767, min(32767, left_val))
            right_clamped = max(-32767, min(32767, right_val))
            out_frames.extend(struct.pack("<hh", left_clamped, right_clamped))

        with wave.open(output_wav, "wb") as wf_out:
            wf_out.setnchannels(2)
            wf_out.setsampwidth(2)
            wf_out.setframerate(framerate)
            wf_out.writeframes(bytes(out_frames))

        return output_wav
    except Exception as e:
        print(f"    [Item 187] Stereo pan hareketi hatası: {e}")
        return sfx_wav


# ─── ITEM 188: Gürültülü Ortam Kurgusu (Crowd Room Ambience) ──────────────────

def ensure_crowd_room_ambience() -> str:
    """
    Madde 188: Gürültülü Ortam Kurgusu.
    Sokak röportajı veya finans haberinde hafif ambiyans insan ve ortam sesi
    ekleyerek otantik hava katar.
    """
    output_path = os.path.join(SFX_DIR, "crowd_ambience.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    duration = 5.0
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    # Çoklu harmonik ve alçak frekanslı fısıltı katmanları
    b0, b1, b2 = 0.0, 0.0, 0.0
    for i in range(num_samples):
        t = i / sample_rate
        white = random.random() * 2.0 - 1.0
        # Pink noise filtresi
        b0 = 0.99886 * b0 + white * 0.0555179
        b1 = 0.99332 * b1 + white * 0.0750759
        b2 = 0.96900 * b2 + white * 0.1538520
        pink = b0 + b1 + b2 + white * 0.5362

        # Ortam mırıltı harmonikleri (180Hz, 340Hz, 520Hz)
        murmur = (
            math.sin(2 * math.pi * 180 * t + math.sin(2 * math.pi * 0.5 * t)) * 0.15 +
            math.sin(2 * math.pi * 340 * t + math.cos(2 * math.pi * 0.3 * t)) * 0.10 +
            math.sin(2 * math.pi * 520 * t) * 0.08
        )
        val = (pink * 0.12 + murmur) * 0.18
        scaled = int(val * 24000)
        frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    return output_path


def inject_room_ambience(audio_wav: str, output_wav: str,
                         volume: float = 0.08) -> str:
    """
    Madde 188: Anlatım veya arka plana hafif sokak/oda ambiyansı miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    ambience_path = ensure_crowd_room_ambience()
    if not os.path.exists(ambience_path):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-stream_loop", "-1", "-i", ambience_path,
            "-filter_complex",
            f"[1:a]volume={volume}[amb];[0:a][amb]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 188] Ambiyans miks hatası: {e}")
    return audio_wav


# ─── ITEM 192: Vurgulu Kelimede Sub-Kick Hit (Sub-Bass Drum Hit) ──────────────

def ensure_sub_kick_sfx() -> str:
    """
    Madde 192: Vurgulu Kelimede Alttan Davul Vuruşu (Kick Hit).
    60Hz'den 35Hz'e hızlı düşen, keskin ataklı ve 180ms sönümlü
    sub-bass kick davul darbesi sentezler.
    """
    output_path = os.path.join(SFX_DIR, "sub_kick.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    dur = 0.22
    num_samples = int(sample_rate * dur)
    frames = bytearray()

    phase = 0.0
    for i in range(num_samples):
        t = i / sample_rate
        # Hızlı pitch drop (110Hz -> 42Hz)
        freq = 42.0 + (110.0 - 42.0) * math.exp(-t * 28.0)
        phase += 2 * math.pi * freq / sample_rate
        # Hızlı ve dolgun decay envelope
        env = math.exp(-t * 18.0)
        val = math.sin(phase) * env
        scaled = int(val * 28000)
        frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    return output_path


def inject_sub_kick_hit(audio_wav: str, output_wav: str,
                        timestamp_sec: float = 0.0,
                        volume: float = 0.32) -> str:
    """
    Madde 192: Cümledeki anahtar vurgulu kelimenin başladığı saniyede
    alttan tok bir bas davul vuruşu miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    kick_sfx = ensure_sub_kick_sfx()
    if not os.path.exists(kick_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        delay_ms = max(0, int(timestamp_sec * 1000))
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-i", kick_sfx,
            "-filter_complex",
            f"[1:a]volume={volume},adelay={delay_ms}|{delay_ms}[kck];[0:a][kck]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 192] Sub-kick hit miks hatası: {e}")
    return audio_wav




