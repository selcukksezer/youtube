"""TTS — Edge TTS with sentence-level rhythm and reliable word timings."""
import asyncio, os, shutil, subprocess, tempfile, wave
import imageio_ffmpeg
import edge_tts, config

def _mp3_to_wav(mp3, wav):
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-y","-i",mp3,"-ar","44100","-ac","2",wav],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if r.returncode == 0:
        try: os.remove(mp3)
        except: pass
        return wav
    return mp3

async def _tts(text, mp3_path, rate=None, volume=None):
    comm = edge_tts.Communicate(text=text, voice=config.TTS_VOICE,
                                 rate=rate or config.TTS_RATE, pitch=config.TTS_PITCH,
                                 volume=volume or "+0%")
    timings = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                text_val = chunk.get("text", "")
                offset_s = chunk.get("offset", 0) / 1e7
                dur_s = chunk.get("duration", 0) / 1e7
                if chunk["type"] == "WordBoundary":
                    timings.append({"text": text_val, "offset": offset_s, "duration": dur_s})
                else:
                    words = text_val.split()
                    if words:
                        w_dur = dur_s / max(1, len(words))
                        for idx, w in enumerate(words):
                            timings.append({"text": w, "offset": offset_s + idx * w_dur, "duration": w_dur})
    return mp3_path, timings

def _concat_wavs(wav_paths, output_path, pause_seconds=0.28):
    """Concatenates matching PCM WAV files while preserving a deterministic duration."""
    if not wav_paths:
        return "", []
    elapsed = 0.0
    offsets = []
    with wave.open(wav_paths[0], "rb") as first:
        params = first.getparams()
        with wave.open(output_path, "wb") as merged:
            merged.setparams(params)
            for index, wav_path in enumerate(wav_paths):
                offsets.append(elapsed)
                with wave.open(wav_path, "rb") as source:
                    if source.getparams()[:3] != params[:3]:
                        raise ValueError("TTS segment formats do not match")
                    frames = source.readframes(source.getnframes())
                    merged.writeframes(frames)
                    elapsed += source.getnframes() / float(source.getframerate())
                if index < len(wav_paths) - 1 and pause_seconds > 0:
                    silence_frames = int(params.framerate * pause_seconds)
                    merged.writeframes(b'\x00' * silence_frames * params.nchannels * params.sampwidth)
                    elapsed += pause_seconds
    return output_path, offsets

def generate_narration_with_timing(text, output_path, natural_pauses=True, voice_profile=None):
    print(f"  [TTS] {config.TTS_VOICE} | {len(text)} chars")
    from voice_humanizer import VoiceHumanizer
    reaction_cues = VoiceHumanizer.extract_reaction_cues(text)
    segments = VoiceHumanizer.build_speech_rhythm_segments(text)
    if not segments:
        segments = [{"text": VoiceHumanizer.clean_narration_for_speech(text), "style": "body", "rate": config.TTS_RATE}]
    temp_dir = tempfile.mkdtemp(prefix="tts_rhythm_")
    wav_paths, timings = [], []
    try:
        for index, segment in enumerate(segments):
            spoken_text = VoiceHumanizer.synthesize_natural_pauses(segment["text"], engine_type="plain") if natural_pauses else segment["text"]
            segment_mp3 = os.path.join(temp_dir, f"segment_{index}.mp3")
            segment_wav = os.path.join(temp_dir, f"segment_{index}.wav")
            rate = voice_profile.get("rate") if voice_profile and voice_profile.get("enabled") else segment["rate"]
            volume = "-22%" if voice_profile and voice_profile.get("enabled") else None
            _, segment_timings = asyncio.run(_tts(spoken_text, segment_mp3, rate=rate, volume=volume))
            _mp3_to_wav(segment_mp3, segment_wav)
            wav_paths.append(segment_wav)
            timings.append(segment_timings)
        wav, offsets = _concat_wavs(wav_paths, output_path, pause_seconds=0.28 if natural_pauses else 0.0)
        flattened_timings = []
        for offset, segment_timings in zip(offsets, timings):
            for timing in segment_timings:
                timing["offset"] += offset
                flattened_timings.append(timing)
        timings = flattened_timings
        # Item 194: Sentetik Ses Artefaktlarını Filtreleme (Low-pass @ 14kHz)
        try:
            from voice.audio_dsp import apply_tts_artifact_lowpass_filter
            filtered_wav = output_path + ".lp.wav"
            if apply_tts_artifact_lowpass_filter(output_path, filtered_wav, cutoff_hz=14000.0) == filtered_wav:
                os.replace(filtered_wav, output_path)
                print("  [TTS] Item 194: 14kHz alçak geçiren filtre ile sentetik artefaktlar temizlendi.")
        except Exception as e:
            pass
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    if reaction_cues:
        print(f"  [TTS] {len(reaction_cues)} non-verbal reaction cue(s) reserved for mix (Item 149).")
    print(f"  [TTS] {len(timings)} word timings (Item 93 Natural Pauses: {natural_pauses})")
    print(f"  [TTS] Saved: {wav}")
    return wav, timings
