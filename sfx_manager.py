"""
SFX Transition Audio Manager — Synthesizes & mixes scene transition sounds (Whoosh/Pop).
Boosts viewer retention and engagement on YouTube Shorts.
"""
import os, math, wave, struct, subprocess
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

    return whoosh_path, pop_path

def add_sfx_to_narration(narration_audio_path, scene_durations, output_path, sfx_volume=0.20):
    """
    Overlays scene transition Whoosh sound effects at the start of each scene cut.
    """
    whoosh_path, _ = ensure_sfx_files()
    if not os.path.exists(whoosh_path) or not os.path.exists(narration_audio_path):
        return narration_audio_path

    # Calculate transition timestamps
    timestamps = [0.0]
    curr = 0.0
    for d in scene_durations[:-1]:
        curr += d
        timestamps.append(curr)

    if not timestamps:
        return narration_audio_path

    # Build FFmpeg filter complex for SFX overlay
    inputs = ["-i", narration_audio_path]
    filter_parts = []
    
    # Add input for each transition
    for idx, ts in enumerate(timestamps):
        inputs.extend(["-i", whoosh_path])
        delay_ms = int(ts * 1000)
        filter_parts.append(f"[{idx+1}:a]adelay={delay_ms}|{delay_ms},volume={sfx_volume}[sfx{idx}]")

    mix_inputs = "".join(f"[sfx{i}]" for i in range(len(timestamps)))
    filter_complex = f"{';'.join(filter_parts)};[0:a]{mix_inputs}amix=inputs={len(timestamps)+1}:duration=first:dropout_transition=2[outa]"

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y"] + inputs + [
        "-filter_complex", filter_complex,

        "-map", "[outa]",
        "-c:a", "pcm_s16le",
        output_path
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and os.path.exists(output_path):
        print(f"  [SFX] Added {len(timestamps)} scene transition Whoosh SFX effects")
        return output_path
    else:
        print(f"  [SFX] SFX mixing skipped: {res.stderr.decode('utf-8', errors='ignore')[:150]}")
        return narration_audio_path

if __name__ == "__main__":
    ensure_sfx_files()
    print("SFX files generated in assets/sfx")
