"""
SFX Transition Audio Manager — Synthesizes & mixes scene transition sounds (Whoosh/Pop).
Boosts viewer retention and engagement on YouTube Shorts.
"""
import os, math, re, wave, struct, subprocess
import imageio_ffmpeg
import config


SFX_DIR = os.path.join(config.BASE_DIR, "assets", "sfx")

def ensure_sfx_files():
    """Synthesizes high quality clean whoosh.wav and pop.wav SFX files if missing."""
    os.makedirs(SFX_DIR, exist_ok=True)
    whoosh_path = os.path.join(SFX_DIR, "whoosh.wav")
    pop_path = os.path.join(SFX_DIR, "pop.wav")

    sample_rate = 44100

    # 1. Generate Whoosh SFX (Frequency sweep + noise modulation)
    if not os.path.exists(whoosh_path):
        dur = 0.25 # 250ms
        num_samples = int(sample_rate * dur)
        frames = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.sin(math.pi * (t / dur)) ** 2  # smooth bell envelope
            freq = 150 + 600 * math.sin(math.pi * (t / dur))
            val = math.sin(2 * math.pi * freq * t) * env
            scaled = int(val * 16000)
            frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

        with wave.open(whoosh_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)

    # 2. Generate Pop SFX (Short high punch)
    if not os.path.exists(pop_path):
        dur = 0.12 # 120ms
        num_samples = int(sample_rate * dur)
        frames = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-t * 30.0) # fast decay
            freq = 800 - t * 4000
            val = math.sin(2 * math.pi * max(100, freq) * t) * env
            scaled = int(val * 20000)
            frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

        with wave.open(pop_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)

    # 3. Generate Ding SFX (Clear high resonant bell for questions/hooks)
    ding_path = os.path.join(SFX_DIR, "ding.wav")
    if not os.path.exists(ding_path):
        dur = 0.40 # 400ms
        num_samples = int(sample_rate * dur)
        frames = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-t * 8.0) # resonant bell ring
            val = (0.7 * math.sin(2 * math.pi * 1800 * t) + 0.3 * math.sin(2 * math.pi * 3600 * t)) * env
            scaled = int(val * 18000)
            frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

        with wave.open(ding_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)

    # 4. Generate Sub Impact SFX (45Hz bass drop for shock moments - Item 154)
    impact_path = os.path.join(SFX_DIR, "sub_impact.wav")
    if not os.path.exists(impact_path):
        dur = 0.60 # 600ms
        num_samples = int(sample_rate * dur)
        frames = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-t * 5.0)
            freq = 65 - t * 40 # pitch drop 65Hz to 40Hz
            val = math.sin(2 * math.pi * max(35, freq) * t) * env
            scaled = int(val * 24000)
            frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

        with wave.open(impact_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)

    # 5. Generate Tape Stop SFX (Item 156)
    tape_path = os.path.join(SFX_DIR, "tape_stop.wav")
    if not os.path.exists(tape_path):
        dur = 0.35 # 350ms
        num_samples = int(sample_rate * dur)
        frames = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = max(0.0, 1.0 - (t / dur))
            freq = max(40, 450 * (1.0 - (t / dur)**2))
            val = math.sin(2 * math.pi * freq * t) * env
            scaled = int(val * 18000)
            frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

        with wave.open(tape_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)

    # 6. Generate Pure Math Sine/Square SFX (Item 136: Özgün SFX Frekansları)
    sine_sweep_path = os.path.join(SFX_DIR, "math_sine_sweep.wav")
    if not os.path.exists(sine_sweep_path):
        generate_pure_math_sfx(sine_sweep_path, wave_type="sine", freq_start=180, freq_end=720, duration=0.22)

    square_glitch_path = os.path.join(SFX_DIR, "math_square_glitch.wav")
    if not os.path.exists(square_glitch_path):
        generate_pure_math_sfx(square_glitch_path, wave_type="square", freq_start=240, freq_end=120, duration=0.15)

    _ensure_contextual_sfx_files(sample_rate)

    return whoosh_path, pop_path, ding_path


def _write_sfx(path, duration, sample_fn, sample_rate=44100):
    frames = bytearray()
    for index in range(int(sample_rate * duration)):
        value = max(-1.0, min(1.0, sample_fn(index / sample_rate)))
        frames.extend(struct.pack('<h', int(value * 32767)))
    with wave.open(path, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)


def _ensure_contextual_sfx_files(sample_rate=44100):
    """Synthesizes editorial-only SFX used by Items 157-159."""
    heartbeat_path = os.path.join(SFX_DIR, "heartbeat.wav")
    if not os.path.exists(heartbeat_path):
        def heartbeat(t):
            beat_position = t % 0.75
            envelope = math.exp(-36 * beat_position) if beat_position < 0.18 else 0.0
            return math.sin(2 * math.pi * 58 * t) * envelope * 0.42
        _write_sfx(heartbeat_path, 1.5, heartbeat, sample_rate)

    tick_path = os.path.join(SFX_DIR, "clock_tick.wav")
    if not os.path.exists(tick_path):
        def clock_tick(t):
            beat_position = t % 1.0
            envelope = math.exp(-55 * beat_position) if beat_position < 0.08 else 0.0
            return (math.sin(2 * math.pi * 1900 * t) + math.sin(2 * math.pi * 2800 * t) * 0.25) * envelope * 0.22
        _write_sfx(tick_path, 3.0, clock_tick, sample_rate)

    typewriter_path = os.path.join(SFX_DIR, "typewriter.wav")
    if not os.path.exists(typewriter_path):
        def typewriter(t):
            envelope = math.exp(-50 * t)
            return (math.sin(2 * math.pi * 1250 * t) + math.sin(2 * math.pi * 300 * t) * 0.4) * envelope * 0.18
        _write_sfx(typewriter_path, 0.1, typewriter, sample_rate)


def generate_pure_math_sfx(output_path: str, wave_type: str = "sine",
                          freq_start: float = 200.0, freq_end: float = 800.0,
                          duration: float = 0.20, sample_rate: int = 44100) -> str:
    """
    Item 136: Özgün SFX Frekansları.
    Web'den telifli veya parmak izli ses efekti indirmek yerine,
    matematiksel sinüs ve kare dalga formülleriyle sıfırdan pürüzsüz SFX üretir.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    num_samples = int(sample_rate * duration)
    frames = bytearray()

    phase = 0.0
    for i in range(num_samples):
        t = i / sample_rate
        frac = t / duration
        current_freq = freq_start + (freq_end - freq_start) * frac
        phase += 2 * math.pi * current_freq / sample_rate

        # Soft Hann/Sine envelope
        env = math.sin(math.pi * frac) ** 1.5

        if wave_type == "square":
            # Square wave with soft anti-aliasing
            raw = 1.0 if (math.sin(phase) >= 0) else -1.0
            val = raw * 0.5 * env
        elif wave_type == "triangle":
            val = (2.0 * math.asin(math.sin(phase)) / math.pi) * env
        else: # sine
            val = math.sin(phase) * env

        scaled = int(val * 22000)
        frames.extend(struct.pack('<h', max(-32767, min(32767, scaled))))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)

    return output_path


def ensure_reaction_sfx_files():
    """Item 149: procedural chuckle + sigh SFX for editorial reaction cues."""
    os.makedirs(SFX_DIR, exist_ok=True)
    chuckle_path = os.path.join(SFX_DIR, "chuckle.wav")
    sigh_path = os.path.join(SFX_DIR, "sigh.wav")
    sample_rate = 44100

    if not os.path.exists(chuckle_path):
        dur = 0.35
        frames = bytearray()
        for i in range(int(sample_rate * dur)):
            t = i / sample_rate
            env = math.exp(-t * 6.0) * (0.6 + 0.4 * math.sin(2 * math.pi * 7 * t))
            val = math.sin(2 * math.pi * (420 + 80 * t) * t) * env * 0.35
            scaled = int(val * 12000)
            frames.extend(struct.pack("<h", max(-32767, min(32767, scaled))))
        with wave.open(chuckle_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)

    if not os.path.exists(sigh_path):
        dur = 0.55
        frames = bytearray()
        for i in range(int(sample_rate * dur)):
            t = i / sample_rate
            env = math.exp(-t * 3.5)
            val = math.sin(2 * math.pi * 180 * t) * env * 0.4
            scaled = int(val * 10000)
            frames.extend(struct.pack("<h", max(-32767, min(32767, scaled))))
        with wave.open(sigh_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)

    return chuckle_path, sigh_path


def build_reaction_sfx_events(scene_clips):
    """Item 149: map (gül/şaşır/iç çek) parenthetical cues to mix timestamps."""
    from voice.script_humanizer import extract_reaction_cues

    events, elapsed = [], 0.0
    for scene in scene_clips or []:
        cues = extract_reaction_cues(str(scene.get("narration", "")))
        for cue in cues:
            sound = "chuckle" if cue == "chuckle" else "sigh"
            events.append({"sound": sound, "at": elapsed + 0.25})
        elapsed += float(scene.get("duration", 0.0))
    return events


def build_emphasis_kick_events(scene_clips, word_timings=None):
    """Item 192: sub-kick on emphasis keywords aligned to word timings when available."""
    from voice.script_humanizer import EMPHASIS_KEYWORDS_TR, EMPHASIS_KEYWORDS_EN

    emphasis = {k.casefold() for k in EMPHASIS_KEYWORDS_TR} | {k.casefold() for k in EMPHASIS_KEYWORDS_EN}
    events = []
    if word_timings:
        for wt in word_timings:
            token = re.sub(r"[^\w]", "", (wt.get("text") or "")).casefold()
            if token in emphasis:
                events.append({"sound": "sub_kick", "at": float(wt.get("offset", 0.0))})
                if len(events) >= 6:
                    break
        return events

    elapsed = 0.0
    for scene in scene_clips or []:
        for word in str(scene.get("narration", "")).split():
            token = re.sub(r"[^\w]", "", word).casefold()
            if token in emphasis:
                events.append({"sound": "sub_kick", "at": elapsed})
                if len(events) >= 6:
                    return events
        elapsed += float(scene.get("duration", 0.0))
    return events


def build_scene_sfx_events(scene_clips):
    """Returns non-copyrighted SFX events from scene metadata (Items 154-155)."""
    events, elapsed = [], 0.0
    # Madde 154/157/158/159: sahne içeriğine göre SFX (Whoosh → Madde 155 sync_riser, burada yok)
    shock_terms = ("şok", "inanılmaz", "korkunç", "dehşet", "gizli", "imkansız", "şok edici")
    tension_terms = ("korku", "gerilim", "tehdit", "tehlike", "paranormal", "horror")
    quiz_terms = ("tahmin", "kaç saniye", "süren var", "doğru cevap", "quiz")
    type_terms = ("daktilo", "typewriter", "belge", "rapor", "ekrana yaz")
    for index, scene in enumerate(scene_clips or []):
        searchable = " ".join(str(scene.get(key, "")) for key in ("narration", "scene_description", "title")).lower()
        if any(term in searchable for term in shock_terms):
            events.append({"sound": "sub_impact", "at": elapsed})
        if any(term in searchable for term in tension_terms):
            events.append({"sound": "heartbeat", "at": elapsed})
        if any(term in searchable for term in quiz_terms):
            events.append({"sound": "clock_tick", "at": elapsed})
        if any(term in searchable for term in type_terms):
            events.append({"sound": "typewriter", "at": elapsed})
        elapsed += float(scene.get("duration", 0.0))
    return events


def _panned_whoosh_path(whoosh_path: str) -> str:
    """Item 187: stereo pan L→R on whoosh transitions."""
    try:
        from voice.acoustic_assets import apply_stereo_pan_movement
        panned = whoosh_path.replace(".wav", "_panned.wav")
        if os.path.exists(panned) and os.path.getmtime(panned) >= os.path.getmtime(whoosh_path):
            return panned
        result = apply_stereo_pan_movement(whoosh_path, panned, direction="left_to_right", duration=0.35)
        if result and os.path.exists(result):
            return result
    except Exception:
        pass
    return whoosh_path


def add_sfx_to_narration(narration_audio_path, scene_durations, output_path, sfx_volume=0.20, scene_clips=None, word_timings=None):
    """
    Overlays scene transition Whoosh sound effects at the start of each scene cut.
    """
    whoosh_path, pop_path, ding_path = ensure_sfx_files()
    whoosh_path = _panned_whoosh_path(whoosh_path)
    ensure_reaction_sfx_files()
    impact_path = os.path.join(SFX_DIR, "sub_impact.wav")
    if not os.path.exists(whoosh_path) or not os.path.exists(narration_audio_path):
        return narration_audio_path

    if scene_clips:
        events = build_scene_sfx_events(scene_clips)
        events.extend(build_reaction_sfx_events(scene_clips))
        events.extend(build_emphasis_kick_events(scene_clips, word_timings=word_timings))
    else:
        elapsed = 0.0
        events = []
        for duration in scene_durations[:-1]:
            elapsed += duration
            events.append({"sound": "whoosh", "at": max(0.0, elapsed - 0.25)})

    if not events:
        return narration_audio_path

    # Build FFmpeg filter complex for SFX overlay
    inputs = ["-i", narration_audio_path]
    filter_parts = []
    
    sound_paths = {
        "whoosh": whoosh_path, "sub_impact": impact_path,
        "heartbeat": os.path.join(SFX_DIR, "heartbeat.wav"),
        "clock_tick": os.path.join(SFX_DIR, "clock_tick.wav"),
        "typewriter": os.path.join(SFX_DIR, "typewriter.wav"),
        "chuckle": os.path.join(SFX_DIR, "chuckle.wav"),
        "sigh": os.path.join(SFX_DIR, "sigh.wav"),
        "sub_kick": os.path.join(SFX_DIR, "sub_kick.wav"),
    }
    if events and any(e.get("sound") == "sub_kick" for e in events):
        from voice.acoustic_assets import ensure_sub_kick_sfx
        ensure_sub_kick_sfx()
    for idx, event in enumerate(events):
        sound_path = sound_paths[event["sound"]]
        inputs.extend(["-i", sound_path])
        delay_ms = int(event["at"] * 1000)
        filter_parts.append(f"[{idx+1}:a]adelay={delay_ms}|{delay_ms},volume={sfx_volume}[sfx{idx}]")

    mix_inputs = "".join(f"[sfx{i}]" for i in range(len(events)))
    filter_complex = f"{';'.join(filter_parts)};[0:a]{mix_inputs}amix=inputs={len(events)+1}:duration=first:dropout_transition=0:normalize=0[outa]"

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y"] + inputs + [
        "-filter_complex", filter_complex,

        "-map", "[outa]",
        "-c:a", "pcm_s16le",
        output_path
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and os.path.exists(output_path):
        print(f"  [SFX] Added {len(events)} scene-aware impact/whoosh effects (Items 154, 155)")
        return output_path
    else:
        print(f"  [SFX] SFX mixing skipped: {res.stderr.decode('utf-8', errors='ignore')[:150]}")
        return narration_audio_path


# ─── ITEM 199: Özel Ses Efekti Arşivi (10 Core Procedural SFX Archive) ────────

def ensure_core_sfx_suite():
    """
    Madde 199: Özel Ses Efekti Arşivi.
    Her niş için standartlaşmış 10 adet saf matematiksel / sıfır telifli SFX paketi
    (Whoosh, Pop, Ding, Sub Impact, Tape Stop, Sine Sweep, Square Glitch, Heartbeat, Clock Tick, Sub Kick)
    üretir ve hazır tutar.
    """
    ensure_sfx_files()
    sub_kick_path = os.path.join(SFX_DIR, "sub_kick.wav")
    if not os.path.exists(sub_kick_path):
        from voice.acoustic_assets import ensure_sub_kick_sfx
        ensure_sub_kick_sfx()

    suite = {
        "whoosh": os.path.join(SFX_DIR, "whoosh.wav"),
        "pop": os.path.join(SFX_DIR, "pop.wav"),
        "ding": os.path.join(SFX_DIR, "ding.wav"),
        "sub_impact": os.path.join(SFX_DIR, "sub_impact.wav"),
        "tape_stop": os.path.join(SFX_DIR, "tape_stop.wav"),
        "sine_sweep": os.path.join(SFX_DIR, "math_sine_sweep.wav"),
        "square_glitch": os.path.join(SFX_DIR, "math_square_glitch.wav"),
        "heartbeat": os.path.join(SFX_DIR, "heartbeat.wav"),
        "clock_tick": os.path.join(SFX_DIR, "clock_tick.wav"),
        "sub_kick": os.path.join(SFX_DIR, "sub_kick.wav"),
    }
    return suite


if __name__ == "__main__":
    ensure_sfx_files()
    ensure_core_sfx_suite()
    print("SFX files generated in assets/sfx")

