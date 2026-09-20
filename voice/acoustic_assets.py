"""
Synthesized Acoustic Assets, SFX Injections, Noise & ID3 Tagging
Covers items: 87, 108, 112, 119, 141, 151, 154, 155
"""
import os, math, wave, struct, random, subprocess, tempfile, uuid, datetime
import imageio_ffmpeg
import config

SFX_DIR = os.path.join(config.BASE_DIR, "assets", "sfx")
os.makedirs(SFX_DIR, exist_ok=True)

def ensure_breath_sound() -> str:
    """
    Synthesizes a natural, subtle human inhalation breath sound (Item 141).
    180ms duration, filtered white noise with soft exponential attack and decay.
    """
    breath_path = os.path.join(SFX_DIR, "breath.wav")
    if os.path.exists(breath_path):
        return breath_path

    sample_rate = 44100
    dur = 0.18
    num_samples = int(sample_rate * dur)
    frames = bytearray()

    for i in range(num_samples):
        t = i / sample_rate
        env = math.sin(math.pi * (t / dur)) ** 1.8
        noise = (random.random() * 2.0 - 1.0)
        tone = math.sin(2 * math.pi * 1100 * t) * 0.2
        val = (noise * 0.8 + tone) * env * 0.12
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

    with wave.open(breath_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)

    return breath_path

def ensure_sonic_branding_chime() -> str:
    """
    Item 87: 0.4 Saniyelik Özgün Ses Motifi (Audio Watermark / Sonic Branding).
    Kanalın tüm Shorts videolarında ortak 0.4 saniyelik mikro ses motifi bulunur.
    Sentezlenmiş 400ms şık, temiz majör akor çan tınısı.
    """
    chime_path = os.path.join(SFX_DIR, "sonic_brand_chime.wav")
    if os.path.exists(chime_path):
        return chime_path

    sample_rate = 44100
    dur = 0.40
    num_samples = int(sample_rate * dur)
    frames = bytearray()

    freqs = [1046.5, 1318.5, 1567.98]
    for i in range(num_samples):
        t = i / sample_rate
        env = math.exp(-7.0 * (t / dur)) * math.sin(min(1.0, t * 50) * math.pi * 0.5)
        sample_val = 0.0
        for f in freqs:
            sample_val += math.sin(2 * math.pi * f * t) * (1.0 / len(freqs))
        val = sample_val * env * 0.16
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

    with wave.open(chime_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)

    return chime_path

def ensure_whoosh_ding_intro() -> str:
    """
    Item 112 – Özgün Ses İntrosu (Whoosh + Ding Sentezi).
    Videonun ilk 0.2 saniyesine yerleştirilen özel bir "Whoosh + Ding" sentezi.
    """
    intro_path = os.path.join(SFX_DIR, "whoosh_ding_intro.wav")
    if os.path.exists(intro_path):
        return intro_path

    sample_rate = 44100
    total_dur = 0.20
    whoosh_dur = 0.10
    ding_dur = 0.10
    num_whoosh = int(sample_rate * whoosh_dur)
    num_ding = int(sample_rate * ding_dur)

    frames = bytearray()

    for i in range(num_whoosh):
        t = i / sample_rate
        progress = t / whoosh_dur
        freq = 80.0 * (1200.0 / 80.0) ** progress
        env_up = min(1.0, progress * 8.0)
        env_down = 1.0 - progress * 0.3
        env = env_up * env_down
        noise = (random.random() * 2.0 - 1.0) * 0.6
        tone = math.sin(2 * math.pi * freq * t) * 0.4
        val = (noise + tone) * env * 0.22
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

    ding_freqs = [2637.0, 5274.0, 7911.0]
    ding_amps = [0.50, 0.25, 0.12]
    for i in range(num_ding):
        t = i / sample_rate
        progress = t / ding_dur
        env = math.exp(-12.0 * progress) * math.sin(min(1.0, progress * 60) * math.pi * 0.5)
        val = 0.0
        for freq, amp in zip(ding_freqs, ding_amps):
            global_t = (num_whoosh / sample_rate) + t
            val += math.sin(2 * math.pi * freq * global_t) * amp
        val *= env * 0.18
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

    with wave.open(intro_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 112] Whoosh+Ding intro sentezlendi: 200ms → {intro_path}")
    return intro_path

def _ff_err(stderr: bytes, limit: int = 200) -> str:
    """Decode FFmpeg stderr safely on Windows (cp1254 / mixed encodings)."""
    if not stderr:
        return ""
    return stderr.decode("utf-8", errors="replace")[:limit]


def prepend_whoosh_ding_to_narration(narration_wav: str, output_wav: str) -> str:
    """
    Item 112 – Whoosh+Ding intro sesini narration başına birleştirir.
    Uses filter_complex concat (not concat demuxer) so non-ASCII Windows paths work.
    """
    intro = ensure_whoosh_ding_intro()
    if not os.path.exists(narration_wav) or not os.path.exists(intro):
        return narration_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        # Avoid concat demuxer file lists — they break on paths like Users\selçuk\...
        cmd = [
            ffmpeg_exe, "-y",
            "-i", intro,
            "-i", narration_wav,
            "-filter_complex",
            (
                "[0:a]aformat=sample_fmts=s16:sample_rates=44100:channel_layouts=stereo[a0];"
                "[1:a]aformat=sample_fmts=s16:sample_rates=44100:channel_layouts=stereo[a1];"
                "[a0][a1]concat=n=2:v=0:a=1[out]"
            ),
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav,
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(output_wav):
            print(f"    [Item 112] Whoosh+Ding intro eklendi → {output_wav}")
            return output_wav
        print(f"    [Item 112] Concat hatası: {_ff_err(res.stderr)}")
    except Exception as e:
        print(f"    [Item 112] Hata: {e}")

    return narration_wav

def generate_pink_noise_wav(output_path: str, duration_secs: float, volume_db: float = -32.0) -> str:
    """
    Item 108 – Ses Katmanı Çoklaması (Audio Layer Multiplication).
    Voss-McCartney algoritması ile pembe gürültü üretir.
    """
    sample_rate = 44100
    num_samples = int(sample_rate * duration_secs)

    num_rows = 16
    rows = [0.0] * num_rows
    running_sum = 0.0
    frames = bytearray()

    amplitude = 10 ** (volume_db / 20.0)

    for i in range(num_samples):
        k = 0
        tmp = i
        while tmp & 1 == 0 and k < num_rows - 1:
            tmp >>= 1
            k += 1
        running_sum -= rows[k]
        rows[k] = (random.random() * 2.0 - 1.0)
        running_sum += rows[k]
        pink = running_sum / num_rows
        white = (random.random() * 2.0 - 1.0) * 0.05
        val = (pink + white) * amplitude
        val = max(-1.0, min(1.0, val))
        scaled = int(val * 32767)
        frames.extend(struct.pack('<h', scaled))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    print(f"    [Item 108] Pink noise üretildi: {duration_secs:.1f}s @ {volume_db}dB → {output_path}")
    return output_path

def mix_pink_noise_into_narration(narration_wav: str, output_wav: str,
                                   noise_db: float = -32.0,
                                   noise_type: str = "pink") -> str:
    """
    Item 108 – TTS sesine pembe gürültü / oda ambiyansı karıştırma.
    """
    if not os.path.exists(narration_wav):
        return narration_wav

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        probe = subprocess.run(
            [ffmpeg_exe, "-i", narration_wav, "-hide_banner"],
            capture_output=True, text=True
        )
        import re
        dur_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
        if dur_match:
            h, m, s = int(dur_match.group(1)), int(dur_match.group(2)), float(dur_match.group(3))
            duration = h * 3600 + m * 60 + s
        else:
            duration = 60.0

        tmp_noise = tempfile.mktemp(suffix="_pinknoise.wav")
        generate_pink_noise_wav(tmp_noise, duration + 0.5, volume_db=noise_db)

        if noise_type == "room":
            filter_complex = (
                f"[0:a]aecho=0.6:0.5:40|60:0.4|0.3[reverb];"
                f"[reverb][1:a]amix=inputs=2:duration=first:dropout_transition=0.5:normalize=0[out]"
            )
        else:
            filter_complex = (
                f"[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0.5:normalize=0[out]"
            )

        cmd = [
            ffmpeg_exe, "-y",
            "-i", narration_wav,
            "-i", tmp_noise,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(output_wav):
            print(f"    [Item 108] Pink noise ({noise_type}) harmanlandı: {noise_db}dB")
            try:
                os.remove(tmp_noise)
            except Exception:
                pass
            return output_wav
        else:
            print(f"    [Item 108] FFmpeg hatası: {_ff_err(res.stderr)}")

    except Exception as e:
        print(f"    [Item 108] Pink noise karıştırma hatası: {e}")

    return narration_wav

def inject_id3_tags(mp3_path: str,
                    title: str = "",
                    artist: str = "",
                    album: str = "",
                    year: str = "",
                    comment: str = "",
                    encoder_tag: str = "") -> str:
    """
    Item 119 – Ses Şifreleme: MP3 ID3 Etiket Enjeksiyonu.
    """
    if not os.path.exists(mp3_path):
        return mp3_path

    if not title:
        title = f"Track_{uuid.uuid4().hex[:8].upper()}"
    if not artist:
        studios = [
            "Horizon Audio Labs", "Meridian Sound Studio", "Apex Media Group",
            "Zenith Productions", "Vertex Creative", "Pinnacle Audio Works",
            "Summit Studio", "Crest Sound Design", "Aurora Media Productions"
        ]
        artist = random.choice(studios)
    if not year:
        year = str(datetime.datetime.now().year)
    if not album:
        album = f"Collection_{uuid.uuid4().hex[:6].upper()}"
    if not comment:
        comment = f"Produced by {artist}. All rights reserved {year}."
    if not encoder_tag:
        encoders = [
            "Logic Pro X 10.7.8", "Adobe Audition CC 2024",
            "DaVinci Resolve 19.0", "Pro Tools 2024.3",
            "Reaper 6.82", "Ableton Live 12.0.2"
        ]
        encoder_tag = random.choice(encoders)

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        tmp_out = tempfile.mktemp(suffix="_id3tagged.mp3")

        cmd = [
            ffmpeg_exe, "-y",
            "-i", mp3_path,
            "-c:a", "copy",
            "-id3v2_version", "3",
            "-metadata", f"title={title}",
            "-metadata", f"artist={artist}",
            "-metadata", f"album={album}",
            "-metadata", f"date={year}",
            "-metadata", f"comment={comment}",
            "-metadata", f"encoder={encoder_tag}",
            "-metadata", f"encoded_by={encoder_tag}",
            "-metadata", f"track={str(random.randint(1, 20))}",
            "-metadata", f"genre=Soundtrack",
            tmp_out
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(tmp_out):
            os.replace(tmp_out, mp3_path)
            print(f"    [Item 119] ID3 etiketleri enjekte edildi: title='{title}', artist='{artist}', encoder='{encoder_tag}'")
        else:
            print(f"    [Item 119] ID3 enjeksiyon hatası: {_ff_err(res.stderr)}")
            try:
                os.remove(tmp_out)
            except Exception:
                pass

    except Exception as e:
        print(f"    [Item 119] ID3 enjeksiyonu başarısız: {e}")

    return mp3_path


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




