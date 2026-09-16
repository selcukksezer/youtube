"""
Background Music (BGM) Manager for Shorts Video Creator.
"""
import os, subprocess
import imageio_ffmpeg
import config

def list_bgm_tracks():

    """Returns a list of available audio files in BGM_DIR."""
    if not os.path.exists(config.BGM_DIR):
        os.makedirs(config.BGM_DIR, exist_ok=True)
    
    exts = ('.mp3', '.wav', '.m4a', '.aac', '.ogg')
    tracks = [f for f in os.listdir(config.BGM_DIR) if f.lower().endswith(exts)]
    return sorted(tracks)

def get_bgm_path(track_name):
    """Returns full path of a BGM track if it exists."""
    if not track_name:
        return None
    full_path = os.path.join(config.BGM_DIR, track_name)
    if os.path.exists(full_path):
        return full_path
    return None

def mix_narration_and_bgm(narration_path, bgm_path, output_path, volume=0.12):
    """
    Mixes narration audio with background music using ffmpeg.
    Loops BGM if shorter than narration, trims BGM if longer.
    Applies ducking / lowering volume on BGM.
    """
    if not bgm_path or not os.path.exists(bgm_path):
        return narration_path

    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y",
        "-i", narration_path,

        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex",
        f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "[aout]",
        "-c:a", "pcm_s16le",
        output_path
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and os.path.exists(output_path):
        print(f"  [BGM] Mixed background music ({os.path.basename(bgm_path)}) at {int(volume*100)}% volume")
        return output_path
    else:
        print(f"  [BGM] Warning: BGM mixing failed, using plain narration: {res.stderr.decode('utf-8', errors='ignore')[:200]}")
        return narration_path
