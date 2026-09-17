"""
Video composer — MoviePy (video only) + ffmpeg (audio + karaoke subs).
3-tier fallback: ASS karaoke → SRT styled → no subs.
"""
import os, subprocess
from moviepy.editor import VideoFileClip, ColorClip, concatenate_videoclips, vfx
import config
from subtitle_generator import create_karaoke_subtitles, create_srt_file
from bgm_manager import get_bgm_path, mix_narration_and_bgm
from sfx_manager import add_sfx_to_narration

from proglog import ProgressBarLogger

class MoviePyProgressLogger(ProgressBarLogger):
    def __init__(self, callback=None, cancel_check=None):
        super().__init__()
        self.callback = callback
        self.cancel_check = cancel_check
        self.last_pct = -1

    def bars_callback(self, bar, attr, value, old_value=None):
        if self.cancel_check and self.cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
        if bar == 't' and attr == 'index':
            total = self.bars['t'].get('total', 0)
            if total > 0 and self.callback:
                pct = int(80 + (value / total) * 16)
                if pct != self.last_pct and pct % 2 == 0:
                    self.last_pct = pct
                    self.callback(pct, f"Kareler Full HD kodlanıyor... (%{int((value/total)*100)} - {value}/{total} kare)")

def compose_video(scene_clips, audio_path, word_timings, output_path, title="", 
                  bgm_track=None, bgm_volume=None, subtitle_opts=None,
                  progress_callback=None, cancel_check=None):
    print(f"\n  [Composer] Building video...")
    W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT

    if cancel_check and cancel_check():
        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    # Measure exact narration audio duration
    import wave
    audio_dur = 0.0
    try:
        with wave.open(audio_path, "rb") as w:
            audio_dur = w.getnframes() / float(w.getframerate())
    except Exception as e:
        print(f"    Audio duration read error: {e}")

    # Scale scene clip durations to match exact audio length BEFORE mixing SFX
    total_scene_dur = sum(sc.get("duration", 7) for sc in scene_clips)
    if audio_dur > 2.0 and total_scene_dur > 0:
        scale = audio_dur / total_scene_dur
        print(f"  [Composer] Scaling scene clip durations (Scale: {scale:.2f}x, Audio: {audio_dur:.1f}s)...")
        for sc in scene_clips:
            sc["duration"] = round(sc.get("duration", 7) * scale, 2)

    # Step A: SFX mixing on narration audio (using scaled scene durations for perfect sync)
    processed_audio = audio_path
    if getattr(config, "ENABLE_SFX", True):
        scene_durs = [sc.get("duration", 7) for sc in scene_clips]
        sfx_audio = output_path.rsplit(".", 1)[0] + "_sfx_audio.wav"
        processed_audio = add_sfx_to_narration(
            audio_path, scene_durs, sfx_audio,
            sfx_volume=getattr(config, "SFX_VOLUME", 0.20)
        )

    if cancel_check and cancel_check():
        raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    # Step B: Check for BGM mixing
    final_audio = processed_audio
    chosen_bgm = bgm_track or getattr(config, "DEFAULT_BGM_TRACK", "")
    if chosen_bgm and getattr(config, "ENABLE_BGM", True):
        bgm_p = get_bgm_path(chosen_bgm)
        if bgm_p:
            vol = bgm_volume if bgm_volume is not None else getattr(config, "BGM_VOLUME", 0.12)
            mixed_audio = output_path.rsplit(".", 1)[0] + "_mixed_audio.wav"
            final_audio = mix_narration_and_bgm(processed_audio, bgm_p, mixed_audio, volume=vol)

    segs = []
    combined = None
    tmp = output_path.rsplit(".", 1)[0] + "_tmp.mp4"
    ass = output_path.rsplit(".", 1)[0] + ".ass"
    srt = output_path.rsplit(".", 1)[0] + ".srt"

    try:
        for sc in scene_clips:
            if cancel_check and cancel_check():
                raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            p, d = sc.get("path"), sc.get("duration", 7)
            if not p or not os.path.exists(p):
                segs.append(ColorClip(size=(W, H), color=(15, 15, 25), duration=d))
            else:
                try:
                    segs.append(_prep(p, d, W, H))
                except Exception as e:
                    print(f"    Clip error: {e}")
                    segs.append(ColorClip(size=(W, H), color=(15, 15, 25), duration=d))
        if not segs:
            return ""

        combined = concatenate_videoclips(segs, method="compose")
        print(f"  [Composer] Duration: {combined.duration:.1f}s")

        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

        render_logger = None
        combined.write_videofile(tmp, fps=config.FPS, codec="libx264",
                                 preset="ultrafast", audio=False, threads=4, logger=render_logger)

        if cancel_check and cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

        if progress_callback:
            progress_callback(97, "Altyazılar ve ses senkronize ediliyor...")

        # ALWAYS create both ASS and SRT
        create_karaoke_subtitles(word_timings, ass, style_opts=subtitle_opts)
        create_srt_file(word_timings, srt)

        print(f"  [Composer] Merging audio + subtitles...")
        ok = _merge(tmp, final_audio, ass, srt, output_path)

        if ok and os.path.exists(output_path):
            mb = os.path.getsize(output_path) / 1048576
            print(f"  [Composer] [OK] {output_path} ({mb:.1f} MB)")
            return output_path
        return ""
    finally:
        # Guarantee clip resources and file handles are closed
        if combined is not None:
            try:
                combined.close()
            except Exception:
                pass
        for s in segs:
            try:
                s.close()
            except Exception:
                pass

        # Cleanup intermediate files safely
        for f in [tmp]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

        for temp_aud in [processed_audio, final_audio]:
            if temp_aud != audio_path and os.path.exists(temp_aud):
                try:
                    os.remove(temp_aud)
                except Exception:
                    pass

import imageio_ffmpeg

def _merge(vid, aud, ass, srt, out):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    out_dir = os.path.dirname(os.path.abspath(out))

    # Basenames for execution inside out_dir
    base_vid = os.path.basename(vid)
    base_ass = os.path.basename(ass)
    base_srt = os.path.basename(srt)
    base_out = os.path.basename(out)
    rel_aud = os.path.relpath(aud, out_dir).replace("\\", "/")

    # Try 1: ASS karaoke
    if os.path.exists(ass) and os.path.getsize(ass) > 50:
        r = subprocess.run([ffmpeg_exe, "-y", "-i", base_vid, "-i", rel_aud,
            "-vf", f"ass={base_ass}", "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-preset", "fast", "-movflags", "+faststart", base_out],
            cwd=out_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode == 0 and os.path.exists(out):
            print(f"    [OK] Karaoke subtitles applied")
            return True
        print(f"    ASS failed ({r.stderr.decode('utf-8', errors='ignore')[:150]}), trying SRT...")

    # Try 2: SRT styled
    if os.path.exists(srt) and os.path.getsize(srt) > 10:
        r = subprocess.run([ffmpeg_exe, "-y", "-i", base_vid, "-i", rel_aud,
            "-vf", f"subtitles={base_srt}:force_style='FontSize=28,FontName=Arial,Bold=1,"
            f"PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,Outline=3,"
            f"BackColour=&H80000000,BorderStyle=4,Alignment=2,MarginV=300'",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-preset", "fast", "-movflags", "+faststart", base_out],
            cwd=out_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode == 0 and os.path.exists(out):
            print(f"    [OK] SRT subtitles applied")
            return True
        print(f"    SRT failed, trying no subs...")

    # Try 3: No subs
    r = subprocess.run([ffmpeg_exe, "-y", "-i", base_vid, "-i", rel_aud,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", base_out],
        cwd=out_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode == 0 and os.path.exists(out):
        print(f"    Video created (no subtitles)")
        return True
    return False




def _prep(path, dur, tw, th):
    c = VideoFileClip(path, audio=False)
    # Downscale high-resolution videos early to save RAM
    if c.w > tw * 1.5 or c.h > th * 1.5:
        c = c.resize(height=th)
    if c.duration > dur:
        st = (c.duration - dur) / 2
        c = c.subclip(st, st + dur)
    elif c.duration < dur:
        f = c.duration / dur
        c = c.fx(vfx.speedx, f) if f >= 0.5 else c.loop(duration=dur)
    return _fit(c, tw, th)

from moviepy.editor import CompositeVideoClip
from moviepy.video.fx.all import colorx

def _fit(c, tw, th):
    cw, ch = c.size
    tr, cr = tw/th, cw/ch

    # If the video is horizontal (landscape) and needs to fit vertical (portrait)
    if cw > ch and cr > tr * 1.2:
        # 1. Create a blurred/darkened background scaled to fill the vertical screen
        # We simulate blur by shrinking drastically and enlarging, then darkening
        try:
            bg_clip = c.resize(height=th)
            # Crop center to match target width
            bg_cw, bg_ch = bg_clip.size
            if bg_cw > tw:
                x = (bg_cw - tw) // 2
                bg_clip = bg_clip.crop(x1=x, x2=x+tw)

            # Simulate a quick blur/darken effect
            bg_clip = bg_clip.resize(0.1).resize(10).fx(colorx, 0.4)

            # 2. Resize original to fit the width of the target screen
            fg_clip = c.resize(width=tw)
            fg_clip = fg_clip.set_position("center")

            # 3. Composite
            comp = CompositeVideoClip([bg_clip, fg_clip], size=(tw, th))
            comp = comp.set_duration(c.duration)
            return comp
        except Exception as e:
            print(f"    Warning: Smart crop fallback failed: {e}")
            pass

    # Fallback to standard crop
    if cr > tr:
        nw = int(ch*tr); x = (cw-nw)//2; c = c.crop(x1=x, x2=x+nw)
    elif cr < tr:
        nh = int(cw/tr); y = (ch-nh)//2; c = c.crop(y1=y, y2=y+nh)
    return c.resize((tw, th))
