"""
0 TL Free AI Image-to-Video Engine (Pollinations Flux + FFmpeg Motion)
Adapted from Verticals v3 / Invideo concepts.
Generates 100% topic-matched 9:16 vertical AI visual clips with NO API KEY required.
"""
import os
import re
import urllib.parse
import urllib.request
import subprocess
import tempfile
import imageio_ffmpeg

_MOTION_PRESETS = [
    # Slow cinematic push-in (zoom in)
    "zoompan=z='min(zoom+0.0018,1.20)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps=30",
    # Slow pull-out (zoom out)
    "zoompan=z='if(lte(zoom,1.0),1.20,max(1.0,zoom-0.0018))':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps=30",
    # Slow pan right with slight zoom
    "zoompan=z='1.12':d={frames}:x='if(lte(on,1),(iw-iw/zoom)/4,min(x+0.5,(iw-iw/zoom)*0.75))':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps=30",
]


def clean_ai_prompt(prompt: str) -> str:
    """Sanitize prompt for photorealistic 9:16 vertical scene generation."""
    clean = re.sub(r"[^\w\s,.-]", " ", prompt or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        clean = "modern high detail cinematic scene"
    # Ensure vertical framing & photorealism enhancement
    return f"{clean}, photorealistic, 8k resolution, vertical 9:16, masterpiece, natural lighting"


import threading
import time

_POLLINATIONS_SEMAPHORE = threading.Semaphore(1)
_LAST_REQUEST_TIME = 0.0
_CIRCUIT_OPEN_UNTIL = 0.0
_CONSECUTIVE_FAILURES = 0


def pollinations_circuit_open() -> bool:
    """Return True if Pollinations AI circuit breaker is currently open (rate-limited / erroring)."""
    return time.time() < _CIRCUIT_OPEN_UNTIL


def trip_pollinations_circuit(duration: float = 90.0) -> None:
    """Trip the Pollinations AI circuit breaker to fast-fail subsequent requests."""
    global _CIRCUIT_OPEN_UNTIL
    _CIRCUIT_OPEN_UNTIL = time.time() + duration


def reset_pollinations_circuit() -> None:
    """Reset the Pollinations AI circuit breaker."""
    global _CIRCUIT_OPEN_UNTIL, _CONSECUTIVE_FAILURES
    _CIRCUIT_OPEN_UNTIL = 0.0
    _CONSECUTIVE_FAILURES = 0


def generate_ai_image(
    prompt: str,
    output_path: str,
    width: int = 540,
    height: int = 960,
    model: str = "flux",
    timeout: int = 8,
) -> bool:
    """
    Fetch 100% free AI generated image from Pollinations.ai (Flux/SDXL).
    Zero API key required. Uses circuit breaker, non-blocking semaphore, and fast failover.
    """
    global _LAST_REQUEST_TIME, _CONSECUTIVE_FAILURES

    if pollinations_circuit_open():
        remaining = int(_CIRCUIT_OPEN_UNTIL - time.time())
        print(f"    [PollinationsAI] Circuit breaker open ({remaining}s remaining) -> fast failover to stock/procedural")
        return False

    # Prevent concurrent bursts: if another request is already in-flight, fail fast so worker gets stock
    acquired = _POLLINATIONS_SEMAPHORE.acquire(blocking=True, timeout=1.5)
    if not acquired:
        print("    [PollinationsAI] High concurrency detected -> fast failover to stock/procedural")
        return False

    try:
        now = time.time()
        elapsed = now - _LAST_REQUEST_TIME
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        _LAST_REQUEST_TIME = time.time()

        enhanced = clean_ai_prompt(prompt)
        encoded = urllib.parse.quote(enhanced)

        # Try primary model then fast turbo fallback
        models_to_try = [model]
        if model != "turbo":
            models_to_try.append("turbo")

        for m in models_to_try:
            url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&model={m}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = resp.read()
                        if len(data) > 5000:
                            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                            with open(output_path, "wb") as f:
                                f.write(data)
                            reset_pollinations_circuit()
                            return True
            except Exception as e:
                err_str = str(e)
                print(f"    [PollinationsAI] Model {m} fetch notice: {err_str}")
                if "429" in err_str or "500" in err_str:
                    trip_pollinations_circuit(120.0)
                    print(f"    [PollinationsAI] Service throttled/erroring ({err_str}). Tripping circuit breaker for 120s.")
                    return False
                if "timed out" in err_str.lower():
                    trip_pollinations_circuit(90.0)
                    print(f"    [PollinationsAI] Timeout detected ({err_str}). Tripping circuit breaker for 90s.")
                    return False
                time.sleep(0.5)

        return False
    finally:
        _POLLINATIONS_SEMAPHORE.release()


def animate_image_to_video(
    image_path: str,
    output_path: str,
    duration: float = 4.0,
    width: int = 540,
    height: int = 960,
    motion_index: int = 0,
) -> bool:
    """
    Convert static image into smooth, cinematic 9:16 vertical video with FFmpeg zoompan.
    """
    if not os.path.exists(image_path) or os.path.getsize(image_path) < 1000:
        return False
    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        frames = max(30, int(duration * 30))
        vf_template = _MOTION_PRESETS[motion_index % len(_MOTION_PRESETS)]
        vf = vf_template.format(frames=frames, w=width, h=height) + ",setsar=1"

        cmd = [
            ffmpeg, "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", vf,
            "-t", f"{duration:.2f}",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        res = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=40,
        )
        return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception as e:
        print(f"    [PollinationsAI] Video animation notice: {e}")
        return False


def create_scene_ai_clip(
    scene_description: str,
    output_video_path: str,
    duration: float = 4.0,
    width: int = 540,
    height: int = 960,
    scene_index: int = 0,
) -> str:
    """
    One-shot free AI video clip generator: Prompt -> Flux Image -> Cinematic Motion Video.
    Returns output path on success, or empty string on failure.
    """
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
        tmp_img_path = tmp_img.name
    try:
        ok_img = generate_ai_image(scene_description, tmp_img_path, width=width, height=height)
        if not ok_img:
            return ""
        ok_vid = animate_image_to_video(
            tmp_img_path,
            output_video_path,
            duration=duration,
            width=width,
            height=height,
            motion_index=scene_index,
        )
        if ok_vid:
            return output_video_path
        return ""
    finally:
        if os.path.exists(tmp_img_path):
            try:
                os.remove(tmp_img_path)
            except OSError:
                pass


class PollinationsAIVisual:
    """OOP interface for Pollinations AI visual generation."""

    def __init__(self, width: int = 540, height: int = 960):
        self.width = width
        self.height = height

    def generate_image(self, prompt: str, output_path: str) -> bool:
        return generate_ai_image(prompt, output_path, width=self.width, height=self.height)

    def create_ai_clip(
        self,
        prompt: str,
        duration: float = 4.0,
        output_path: str = "",
        seed: int = 0,
    ) -> str:
        return create_scene_ai_clip(
            scene_description=prompt,
            output_video_path=output_path,
            duration=duration,
            width=self.width,
            height=self.height,
            scene_index=seed or 0,
        )
