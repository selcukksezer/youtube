"""TTS — edge-tts with MP3→WAV conversion for bulletproof duration."""
import asyncio, os, subprocess
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

async def _tts(text, mp3_path):
    comm = edge_tts.Communicate(text=text, voice=config.TTS_VOICE,
                                 rate=config.TTS_RATE, pitch=config.TTS_PITCH)
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

def generate_narration_with_timing(text, output_path):
    print(f"  [TTS] {config.TTS_VOICE} | {len(text)} chars")
    mp3 = output_path.rsplit(".",1)[0] + ".mp3"
    mp3, timings = asyncio.run(_tts(text, mp3))
    print(f"  [TTS] {len(timings)} word timings")
    wav = output_path.rsplit(".",1)[0] + ".wav"
    final = _mp3_to_wav(mp3, wav)
    print(f"  [TTS] Saved: {final}")
    return final, timings
