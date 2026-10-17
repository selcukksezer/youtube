"""Synthesized Acoustic Primitives (Items 154-158): Sub-Bass Impact, Riser Whoosh, Tape Stop, Heartbeat, Ticking Clock."""
import os, math, wave, struct, random, subprocess
import imageio_ffmpeg
import config

SFX_DIR = os.path.join(config.BASE_DIR, "assets", "sfx")
os.makedirs(SFX_DIR, exist_ok=True)

# ─── ITEM 154: Sub-Bass Patlaması (Impact Sub - 45Hz) ────────────────────────

def ensure_sub_bass_impact_sfx(output_path: str = None, duration: float = 0.8, base_freq: float = 45.0) -> str:
    """
    Madde 154: Sub-Bass Patlaması (Impact Sub).
    Şok edici açıklama veya kanca anlarında vuracak 45Hz sub-bass darbesi.
    Mobil telefon hoparlörlerinde de duyulabilmesi için 2. harmonik (90Hz) satürasyonu
    ile zenginleştirilmiş, 45Hz'e sönen saf sinüs vuruşudur.
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, "sub_bass_impact_45hz.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    for i in range(num_samples):
        t = i / sample_rate
        # İlk 80ms'de 55Hz'den 45Hz'e mikro pitch-drop
        current_freq = base_freq + max(0.0, (1.0 - t / 0.08)) * 10.0
        # Üstel düşüş (Hollywood sinematik sub sönümleme)
        env = math.exp(-4.5 * (t / duration)) * min(1.0, t * 80.0)

        # Temel 45Hz sinüs dalgası + %15 2. harmonik (90Hz mobil algı)
        wave_val = (
            math.sin(2 * math.pi * current_freq * t) * 0.85 +
            math.sin(2 * math.pi * (current_freq * 2) * t) * 0.15
        )
        val = wave_val * env * 0.90
        val = max(-1.0, min(1.0, val))
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 154] 45Hz Sub-Bass Impact SFX sentezlendi ({duration}s) → {output_path}")
    return output_path


def inject_sub_bass_impact(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0, volume: float = 0.85) -> str:
    """
    Madde 154: Belirtilen saniyeye 45Hz sub-bass patlaması efekti miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    sub_sfx = ensure_sub_bass_impact_sfx()
    if not os.path.exists(sub_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        delay_ms = max(0, int(timestamp_sec * 1000))
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-i", sub_sfx,
            "-filter_complex",
            f"[1:a]volume={volume},adelay={delay_ms}|{delay_ms}[sub];[0:a][sub]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 154] Sub-bass inject hatası: {e}")

    return audio_wav


# ─── ITEM 155: Riser / Whoosh Senkronizasyonu (250ms) ─────────────────────────

def ensure_riser_whoosh_sfx(output_path: str = None, duration: float = 0.25) -> str:
    """
    Madde 155: Riser / Whoosh Senkronizasyonu.
    Sahne geçişinden tam 0.25 saniye önce başlayıp sahne kesim anında
    zirveye (peak volume) ulaşan, logaritmik yükselen özel Whoosh efekti.
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, "riser_whoosh_250ms.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    start_freq = 120.0
    end_freq = 2400.0

    for i in range(num_samples):
        t = i / sample_rate
        progress = t / duration

        # Logaritmik frekans tırmanışı
        freq = start_freq * ((end_freq / start_freq) ** progress)
        # Zirveye doğru katlanarak artan hacim (0'dan 1'e sert eğri)
        env = (progress ** 2.2) * min(1.0, (duration - t) * 60.0)

        # Testere dişi tınısı + pembeleşmiş gürültü sentezi
        noise = (random.random() * 2.0 - 1.0) * 0.45
        sine = math.sin(2 * math.pi * freq * t) * 0.55
        val = (noise + sine) * env * 0.85
        val = max(-1.0, min(1.0, val))
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 155] 250ms Sahne Geçiş Riser SFX sentezlendi → {output_path}")
    return output_path


def sync_riser_whoosh_transitions(audio_wav: str, scene_cut_times: list, output_wav: str, volume: float = 0.65) -> str:
    """
    Madde 155: Her sahne geçişinden tam 0.25 saniye önce başlayan Riser seslerini
    belirtilen sahne kesim zamanlarına (scene_cut_times) göre senkronize eder.
    """
    if not os.path.exists(audio_wav) or not scene_cut_times:
        return audio_wav

    riser_sfx = ensure_riser_whoosh_sfx()
    if not os.path.exists(riser_sfx):
        return audio_wav

    # 0.25s öncesi hesaplanır, negatifler veya 0'dan küçük olanlar elenir
    valid_starts = [max(0.0, cut - 0.25) for cut in scene_cut_times if cut >= 0.25]
    if not valid_starts:
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        inputs = ["-i", audio_wav]
        filter_parts = []
        mix_inputs = ["[0:a]"]

        for idx, start_t in enumerate(valid_starts, start=1):
            inputs.extend(["-i", riser_sfx])
            delay_ms = int(start_t * 1000)
            filter_parts.append(f"[{idx}:a]volume={volume},adelay={delay_ms}|{delay_ms}[r{idx}]")
            mix_inputs.append(f"[r{idx}]")

        total_inputs = len(mix_inputs)
        filter_str = ";".join(filter_parts) + f";{''.join(mix_inputs)}amix=inputs={total_inputs}:duration=first:dropout_transition=0:normalize=0[out]"

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
        print(f"    [Item 155] Riser senkronizasyon hatası: {e}")

    return audio_wav


# ─── ITEM 156: Tape-Stop Efekti (0.4s Kaset Durması & Sessizlik) ─────────────

def ensure_tape_stop_sfx(output_path: str = None, duration: float = 0.40) -> str:
    """
    Madde 156: Tape-Stop Efekti.
    Şaşırtıcı bir tezat veya beklenmedik gerçek söylendiğinde müziğin/sesin
    kaset durmuş gibi perdesinin ve hızının düşerek 0.4 saniye tamamen susması.
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, "tape_stop_400ms.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    decel_time = 0.16  # Kaset motorunun yavaşlama süresi
    num_decel = int(sample_rate * decel_time)

    for i in range(num_samples):
        t = i / sample_rate
        if i < num_decel:
            progress = t / decel_time
            # Frekans 450Hz'den 25Hz'e logaritmik düşer
            freq = 450.0 * (1.0 - progress) ** 2.2 + 25.0
            env = (1.0 - progress) * 0.95

            # Testere dişi dalga + mekanik kaset sürtünme gürültüsü
            phase = (t * freq) % 1.0
            saw = (2.0 * phase - 1.0) * 0.65
            noise = (random.random() * 2.0 - 1.0) * 0.25
            val = (saw + noise) * env * 0.85
        elif i < int(sample_rate * 0.20):
            # Mekanik durma 'klik' sesi (0.16s - 0.20s)
            click_progress = (t - decel_time) / 0.04
            click_env = math.exp(-click_progress * 15.0)
            click_tone = math.sin(2 * math.pi * 550.0 * t) * click_env * 0.5
            val = click_tone
        else:
            # Geri kalan kısım tam sessizlik (0.20s - 0.40s)
            val = 0.0

        val = max(-1.0, min(1.0, val))
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 156] 0.4s Tape-Stop SFX sentezlendi → {output_path}")
    return output_path


def apply_tape_stop_to_audio(audio_wav: str, output_wav: str, stop_timestamps: list, volume: float = 0.85) -> str:
    """
    Madde 156: Belirtilen zaman damgalarında sesi 0.4 saniye susturur ve Tape-Stop efektini miksler.
    """
    if not os.path.exists(audio_wav) or not stop_timestamps:
        return audio_wav

    tape_sfx = ensure_tape_stop_sfx()
    if not os.path.exists(tape_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        # Her tezat anı için 0.4 saniyelik sessizlik pencereleri
        mute_windows = "+".join(
            f"between(t,{max(0.0, tp):.3f},{tp + 0.40:.3f})" for tp in stop_timestamps
        )
        mute_filter = f"volume=enable='{mute_windows}':volume=0" if mute_windows else "anull"

        inputs = ["-i", audio_wav]
        filter_parts = [f"[0:a]{mute_filter}[muted]"]
        mix_inputs = ["[muted]"]

        for idx, tp in enumerate(stop_timestamps, start=1):
            inputs.extend(["-i", tape_sfx])
            delay_ms = max(0, int(tp * 1000))
            filter_parts.append(f"[{idx}:a]volume={volume},adelay={delay_ms}|{delay_ms}[ts{idx}]")
            mix_inputs.append(f"[ts{idx}]")

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
        print(f"    [Item 156] Tape-stop uygulama hatası: {e}")

    return audio_wav


# ─── ITEM 157: Kalp Atışı Efekti (Heartbeat SFX & Layering) ──────────────────

def ensure_heartbeat_sfx(output_path: str = None, duration: float = 4.0, bpm: float = 65.0) -> str:
    """
    Madde 157: Kalp Atışı Efekti (Heartbeat).
    Korku ve gerilim sahnelerinde derinden vuran ritmik çift vuruşlu (Lub-Dub, ~65 BPM)
    sub-frekans kalp atışı sentezi.
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, f"heartbeat_{int(bpm)}bpm_{int(duration)}s.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    beat_interval = 60.0 / bpm  # ~0.923s per heartbeat pair

    for i in range(num_samples):
        t = i / sample_rate
        pos_in_beat = t % beat_interval

        val = 0.0
        # Vuruş 1 (Lub): 0.0s - 0.09s @ 52Hz
        if pos_in_beat < 0.09:
            env1 = math.sin(math.pi * (pos_in_beat / 0.09)) ** 1.5
            tone1 = math.sin(2 * math.pi * 52.0 * pos_in_beat)
            val = tone1 * env1 * 0.85

        # Vuruş 2 (Dub): 0.15s - 0.22s @ 74Hz (biraz daha tiz ve kısa)
        elif 0.15 <= pos_in_beat < 0.22:
            t2 = pos_in_beat - 0.15
            env2 = math.sin(math.pi * (t2 / 0.07)) ** 1.8
            tone2 = math.sin(2 * math.pi * 74.0 * t2)
            val = tone2 * env2 * 0.70

        val = max(-1.0, min(1.0, val))
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 157] Kalp Atışı SFX sentezlendi ({bpm} BPM, {duration}s) → {output_path}")
    return output_path


def inject_heartbeat_layer(audio_wav: str, output_wav: str, start_sec: float = 0.0,
                           duration_sec: float = 4.0, volume: float = 0.35, bpm: float = 65.0) -> str:
    """
    Madde 157: Gerilim veya korku anlarında alttan sub-frekans kalp atışı ritmi miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    hb_sfx = ensure_heartbeat_sfx(duration=duration_sec, bpm=bpm)
    if not os.path.exists(hb_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        delay_ms = max(0, int(start_sec * 1000))
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-i", hb_sfx,
            "-filter_complex",
            f"[1:a]volume={volume},adelay={delay_ms}|{delay_ms}[hb];[0:a][hb]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 157] Kalp atışı miks hatası: {e}")

    return audio_wav


# ─── ITEM 158: Saat Tik-Tak Sesi (Ticking Clock SFX - 3s) ────────────────────

def ensure_ticking_clock_sfx(output_path: str = None, duration: float = 3.0) -> str:
    """
    Madde 158: Saat Tik-Tak Sesi (Ticking Clock).
    Zaman kısıtlaması, soru-cevap ve quiz sahnelerinde dikkati toplayan 3 saniyelik analog saat sesi.
    Saniyede 1 'Tik' (yüksek frekans metalik tık) ve yarım saniyede bir 'Tak' (düşük gövde tıkı).
    """
    if not output_path:
        output_path = os.path.join(SFX_DIR, f"ticking_clock_{int(duration)}s.wav")
    if os.path.exists(output_path):
        return output_path

    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    for i in range(num_samples):
        t = i / sample_rate
        pos_in_sec = t % 1.0

        val = 0.0
        # Tik: 0.0s - 0.035s @ 2400Hz + 450Hz mekanik rezonans
        if pos_in_sec < 0.035:
            env = math.exp(-pos_in_sec * 120.0)
            tone = math.sin(2 * math.pi * 2400.0 * pos_in_sec) * 0.7 + math.sin(2 * math.pi * 450.0 * pos_in_sec) * 0.3
            noise = (random.random() * 2.0 - 1.0) * 0.15
            val = (tone + noise) * env * 0.90

        # Tak: 0.5s - 0.530s @ 1850Hz + 380Hz mekanik rezonans
        elif 0.50 <= pos_in_sec < 0.530:
            t_tak = pos_in_sec - 0.50
            env = math.exp(-t_tak * 140.0)
            tone = math.sin(2 * math.pi * 1850.0 * t_tak) * 0.65 + math.sin(2 * math.pi * 380.0 * t_tak) * 0.35
            noise = (random.random() * 2.0 - 1.0) * 0.12
            val = (tone + noise) * env * 0.75

        val = max(-1.0, min(1.0, val))
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 158] 3s Saat Tik-Tak SFX sentezlendi → {output_path}")
    return output_path


def inject_ticking_clock(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0,
                         duration: float = 3.0, volume: float = 0.40) -> str:
    """
    Madde 158: Belirtilen zaman noktasına 3 saniyelik saat tik-tak sesi miksler.
    """
    if not os.path.exists(audio_wav):
        return audio_wav

    clock_sfx = ensure_ticking_clock_sfx(duration=duration)
    if not os.path.exists(clock_sfx):
        return audio_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        delay_ms = max(0, int(timestamp_sec * 1000))
        cmd = [
            ffmpeg_exe, "-y",
            "-i", audio_wav,
            "-i", clock_sfx,
            "-filter_complex",
            f"[1:a]volume={volume},adelay={delay_ms}|{delay_ms}[clk];[0:a][clk]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        print(f"    [Item 158] Saat sesi miks hatası: {e}")

    return audio_wav


