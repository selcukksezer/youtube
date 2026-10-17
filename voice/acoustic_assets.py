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
        try:
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
                return output_wav
            else:
                print(f"    [Item 108] FFmpeg hatası: {_ff_err(res.stderr)}")
        finally:
            try:
                if os.path.exists(tmp_noise):
                    os.remove(tmp_noise)
            except Exception:
                pass

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



from .acoustic_synth_primitives import (
    apply_tape_stop_to_audio,
    ensure_heartbeat_sfx,
    ensure_riser_whoosh_sfx,
    ensure_sub_bass_impact_sfx,
    ensure_tape_stop_sfx,
    ensure_ticking_clock_sfx,
    inject_heartbeat_layer,
    inject_sub_bass_impact,
    inject_ticking_clock,
    sync_riser_whoosh_transitions,
)
# Re-export SFX layer functions (Items 159-192) for backward compatibility
from .acoustic_sfx_layers import (
    ensure_typewriter_sfx,
    inject_typewriter_sfx,
    ensure_quiz_ding_sfx,
    inject_quiz_ding,
    ensure_quiz_buzzer_sfx,
    inject_quiz_buzzer,
    ensure_swallow_sound,
    inject_monologue_pause_and_swallow,
    ensure_vinyl_crackle_sfx,
    inject_vinyl_crackle_layer,
    ensure_dramatic_piano_note_sfx,
    inject_dramatic_piano_layer,
    ensure_cyberpunk_synth_bass_sfx,
    inject_cyberpunk_synth_bass,
    apply_stereo_pan_movement,
    ensure_crowd_room_ambience,
    inject_room_ambience,
    ensure_sub_kick_sfx,
    inject_sub_kick_hit,
)
