"""
AI Image/Video Fallback, Procedural Clip Generation & Multi-Source Rotation Helpers
Extracted from video_fetcher.py for modular architecture.
"""
import base64
import hashlib
import json
import os
import random
import re
import subprocess
import tempfile
from urllib.parse import urlsplit, urlunsplit

import imageio_ffmpeg
import requests

import config


def _safe_public_url(value):
    """Remove query parameters and credentials from public URLs (MoneyPrinterTurbo pattern)."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    except Exception:
        return None


def _file_hash(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def _score(v, target_dur, narration="", visual_intent=None, recent_texts=None):
    """Technical score + semantic relevance (DirectorPlan visual intent)."""
    w, h, d = v["width"], v["height"], v["duration"]
    if d < 3:
        return -1
    s = 0.0
    px = w * h
    s += 40 if px >= 1920 * 1080 else 30 if px >= 1280 * 720 else 15 if px >= 854 * 480 else 5
    s += 25 if h > w else 10 if abs(h - w) < 100 else 5
    s += 25 if d >= target_dur else 15 if d >= target_dur * 0.7 else 8 if d >= target_dur * 0.4 else 2
    if d > 60:
        s -= 5
    if 5 <= d <= 30:
        s += 10

    # Semantic layer — title/tags/url text vs narration + intent
    cand_text = " ".join(str(v.get(k, "")) for k in ("title", "tags", "description", "url", "id"))
    try:
        from director.visual_intent import semantic_relevance_score, text_contains_excluded
        intent = visual_intent
        if isinstance(intent, dict):
            from director.schema import VisualIntent as VI
            intent = VI.from_dict(intent)
        if intent and text_contains_excluded(cand_text, getattr(intent, "must_exclude", [])):
            return -1
        s += semantic_relevance_score(cand_text, narration or "", intent)
    except Exception:
        pass

    # Adjacent-scene diversity penalty (stronger — avoid visual echo)
    if recent_texts:
        low = cand_text.lower()
        url_low = str(v.get("url", "")).lower()
        for prev in recent_texts[-5:]:
            if not prev:
                continue
            prev_l = prev.lower()
            if prev_l in low or prev_l in url_low:
                s -= 18
            # Token overlap diversity
            prev_toks = set(re.findall(r"[a-z0-9]{4,}", prev_l))
            cand_toks = set(re.findall(r"[a-z0-9]{4,}", low))
            overlap = prev_toks & cand_toks
            if len(overlap) >= 2:
                s -= 8 * min(3, len(overlap))
    return s


def slice_random_background_loop(
    source_video_path: str,
    project_dir: str,
    scene_index: int,
    target_duration: float = 7.0,
) -> str:
    """
    Item 139: Arka Plan Döngü Videolarının Süresi.
    Subway Surfers, Minecraft parkur veya oynanış videoları 1 dakikalık sabit
    parça olarak kullanılmamalıdır; rastgele başlangıç noktalarından kesilip
    harmanlanarak YouTube'un şablon tekrarlı içerik tespiti engellenir.
    """
    out_path = os.path.join(project_dir, f"s{scene_index:03d}_sliced_loop.mp4")

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffprobe_cmd = [
        ffmpeg_exe, "-i", source_video_path,
        "-hide_banner",
    ]
    total_dur = 60.0
    try:
        p = subprocess.run(ffprobe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
        if m:
            total_dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass

    max_start = max(0.0, total_dur - target_duration - 1.0)
    start_point = round(random.uniform(0.0, max_start), 2) if max_start > 0 else 0.0

    cmd = [
        ffmpeg_exe, "-y",
        "-ss", str(start_point),
        "-i", source_video_path,
        "-t", str(target_duration),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-an",
        out_path,
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(out_path):
            return out_path
    except Exception as e:
        print(f"    [Item 139] Slice loop error: {e}")

    return source_video_path


def _generate_fallback_clip(
    scene_index,
    project_dir,
    target_duration=7,
    scene_description="",
    visual_intent=None,
    narration="",
    niche_id="",
    include_whiteboard=True,
):
    """
    Intentional procedural tier when stock fails: kinetic typography first,
    then abstract cinematic gradient, then a palette color card so fetch
    cannot stall. Never "Gorsel Bulunamadi".

    Disabled by default: synthetic placeholder visuals are not wanted in
    finished videos. Set config.ALLOW_PROCEDURAL_VISUALS = True to re-enable.
    """
    try:
        import config as _cfg
        if not getattr(_cfg, "ALLOW_PROCEDURAL_VISUALS", False):
            return None
    except Exception:
        return None
    intent = visual_intent if isinstance(visual_intent, dict) else (
        visual_intent.to_dict() if hasattr(visual_intent, "to_dict") else None
    )
    if include_whiteboard and ((intent and intent.get("style") == "whiteboard") or "whiteboard" in (niche_id or "").lower()):
        try:
            from services.whiteboard_animator import generate_whiteboard_sketch_image, animate_whiteboard_clip
            sketch_img = os.path.join(project_dir, f"s{scene_index:03d}_whiteboard_sketch.jpg")
            wb_video = os.path.join(project_dir, f"s{scene_index:03d}_whiteboard.mp4")
            prompt = scene_description or narration or "sketch"
            if generate_whiteboard_sketch_image(prompt, sketch_img):
                if animate_whiteboard_clip(sketch_img, wb_video, duration=target_duration):
                    print(f"    [OK] [PROCEDURAL] Whiteboard animation ({target_duration}s)")
                    return wb_video
        except Exception as e:
            print(f"    [PROCEDURAL] Whiteboard note: {e}")

    try:
        from visuals.motion_graphics import build_kinetic_clip
        path = os.path.join(project_dir, f"s{scene_index:03d}_kinetic_procedural.mp4")
        text = (narration or scene_description or "").strip()
        out = build_kinetic_clip(
            path, target_duration, text=text, niche_id=niche_id or "", scene_index=scene_index,
        )
        if out:
            print(f"    [OK] [PROCEDURAL] Kinetic typography ({target_duration}s)")
            return out
    except Exception as e:
        print(f"    [PROCEDURAL] Kinetic note: {e}")
    try:
        from render.procedural_visuals import build_procedural_clip, resolve_motif
        path = os.path.join(project_dir, f"s{scene_index:03d}_procedural_fallback.mp4")
        motif = resolve_motif(scene_description or narration or "", intent, niche_id=niche_id or "")
        out = build_procedural_clip(path, target_duration, scene_index=scene_index, motif=motif)
        if out:
            print(f"    [OK] [PROCEDURAL] Abstract cinematic ({motif}, {target_duration}s)")
            return out
    except Exception as e:
        print(f"    [PROCEDURAL] Warning generating fallback clip: {e}")
    try:
        from visuals.motion_graphics import build_solid_color_clip
        path = os.path.join(project_dir, f"s{scene_index:03d}_solid_fallback.mp4")
        out = build_solid_color_clip(
            path, target_duration, niche_id=niche_id or "", scene_index=scene_index,
        )
        if out:
            print(f"    [OK] [PROCEDURAL] Solid color card ({target_duration}s)")
            return out
    except Exception as e:
        print(f"    [PROCEDURAL] Solid card note: {e}")
    return None


# ─── ITEM 113: Yapay Zeka ile Çizilmiş Görselleri Kullanma ───────────────────

def _ai_image_providers_available() -> bool:
    """Item 113 — at least one AI image backend configured."""
    if os.getenv("DISABLE_POLLINATIONS", "").strip().lower() not in ("1", "true", "yes"):
        return True
    if getattr(config, "USE_GEMINI_IMAGE_GEN", False) and getattr(config, "GEMINI_API_KEY", ""):
        return True
    if getattr(config, "FAL_API_KEY", ""):
        return True
    if getattr(config, "STABILITY_API_KEY", ""):
        return True
    return False


def generate_ai_image_clip(
    scene_description: str,
    output_path: str,
    duration: float = 5.0,
    width: int = 1080,
    height: int = 1920,
    style_prefix: str = "cinematic dark dramatic, high detail, 4K, ",
) -> str:
    """
    Item 113 – Yapay Zeka ile Çizilmiş Görselleri Kullanma.
    Sahne açıklamasından özgün AI görseli üretir. FAL.ai (Flux-Schnell) öncelikli;
    yoksa Stability AI SDXL API'ye düşer. Üretilen görsel Ken Burns hareketi ile
    hareketlendirilerek MP4 video klibe dönüştürülür.
    """
    if not _ai_image_providers_available():
        return None

    print(f"  [Item 113] AI görsel üretiliyor: '{scene_description[:60]}...'")

    full_prompt = (
        f"{style_prefix}{scene_description}. "
        f"Vertical 9:16 aspect ratio, professional photography, no text, no watermark."
    )

    image_path = None

    # ── Google AI Pro / Nano Banana (öncelikli — Madde 113 + Gemini API) ──
    gemini_ok = getattr(config, "USE_GEMINI_IMAGE_GEN", False) and getattr(config, "GEMINI_API_KEY", "")
    if gemini_ok:
        try:
            from system_resilience import circuit_breaker
            if not circuit_breaker.can_execute("gemini_image"):
                gemini_ok = False
                print("    [Item 113] gemini_image devre açık — stok/FAL'a düşülüyor")
        except Exception:
            pass
    if gemini_ok:
        try:
            from google_ai_hub import save_generated_image
            tmp_gemini = tempfile.mktemp(suffix="_gemini_ai.png")
            saved = save_generated_image(full_prompt, tmp_gemini)
            if saved and os.path.exists(saved):
                image_path = saved
                print(f"    [Item 113] Google Nano Banana görsel: {saved}")
        except Exception as e:
            print(f"    [Item 113] Gemini image notice: {e}")

    # ── FAL.ai Flux-Schnell API ──────────────────────────────────────────
    if not image_path and config.FAL_API_KEY:
        try:
            headers = {
                "Authorization": f"Key {config.FAL_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "prompt": full_prompt,
                "image_size": {"width": width, "height": height},
                "num_inference_steps": 4,
                "num_images": 1,
                "enable_safety_checker": False,
            }
            resp = requests.post(
                "https://fal.run/fal-ai/flux/schnell",
                headers=headers,
                json=payload,
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                images = data.get("images", [])
                if images:
                    img_url = images[0].get("url", "")
                    if img_url:
                        tmp_img = tempfile.mktemp(suffix="_fal_ai.jpg")
                        img_resp = requests.get(img_url, timeout=30)
                        if img_resp.status_code == 200:
                            with open(tmp_img, "wb") as f:
                                f.write(img_resp.content)
                            image_path = tmp_img
                            print(f"    [Item 113] FAL.ai Flux görsel indirildi: {tmp_img}")
        except Exception as e:
            print(f"    [Item 113] FAL.ai hatası: {e}")

    # ── Stability AI SDXL API (Fallback) ─────────────────────────────────────
    if not image_path and config.STABILITY_API_KEY:
        try:
            payload = {
                "text_prompts": [{"text": full_prompt, "weight": 1.0}],
                "cfg_scale": 7,
                "height": min(height, 1024),
                "width": min(width, 1024),
                "steps": 30,
                "samples": 1,
                "style_preset": "cinematic",
            }
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.STABILITY_API_KEY}",
            }
            resp = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers=headers,
                json=payload,
                timeout=90,
            )
            if resp.status_code == 200:
                data = resp.json()
                artifacts = data.get("artifacts", [])
                if artifacts:
                    img_b64 = artifacts[0].get("base64", "")
                    if img_b64:
                        tmp_img = tempfile.mktemp(suffix="_stability_ai.png")
                        with open(tmp_img, "wb") as f:
                            f.write(base64.b64decode(img_b64))
                        image_path = tmp_img
                        print(f"    [Item 113] Stability AI görsel üretildi: {tmp_img}")
        except Exception as e:
            print(f"    [Item 113] Stability AI hatası: {e}")

    # ── Pollinations Free Flux AI (0 TL - Anahtarsız Ücretsiz Motor) ───────
    if not image_path and os.getenv("DISABLE_POLLINATIONS", "").strip().lower() not in ("1", "true", "yes"):
        try:
            from services.pollinations_ai_visual import generate_ai_image
            tmp_poll = tempfile.mktemp(suffix="_pollinations_ai.jpg")
            if generate_ai_image(full_prompt, tmp_poll, width=min(width, 720), height=min(height, 1280)):
                image_path = tmp_poll
                print(f"    [Item 113] Pollinations 0 TL Flux görsel üretildi: {tmp_poll}")
        except Exception as e:
            print(f"    [Item 113] Pollinations görsel uyarısı: {e}")

    if not image_path:
        print("    [Item 113] AI görsel yok/kota/devre — stok videoya geçiliyor.")
        return None

    # ── Görsel → Video (Ken Burns hareketi) ─────────────────────────────────
    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        from render.ffmpeg_graph import cheap_pan_filter
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,"
            f"{cheap_pan_filter(width, height, duration, 0)},setsar=1"
        )

        cmd = [
            ffmpeg, "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", vf,
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"    [Item 113] AI görsel → Ken Burns klip: {duration:.1f}s → {output_path}")
            return output_path
        else:
            print(f"    [Item 113] FFmpeg hatası: {result.stderr[:200]}")

    except Exception as e:
        print(f"    [Item 113] Video dönüştürme hatası: {e}")
    finally:
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass

    return None


def generate_veo_scene_clip(
    scene_description: str,
    output_path: str,
    duration: float = 6.0,
) -> str:
    """Google Veo clip for a scene (requires USE_GEMINI_VIDEO_GEN + paid quota)."""
    if not getattr(config, "USE_GEMINI_VIDEO_GEN", False):
        return None
    if not getattr(config, "GEMINI_API_KEY", ""):
        return None
    try:
        from google_ai_hub import generate_veo_video
        prompt = (
            f"{scene_description}. Vertical 9:16 YouTube Shorts B-roll, cinematic motion, "
            f"no text overlays, no watermark, photorealistic."
        )
        print(f"  [GoogleAI/Veo] Sahne videosu: '{scene_description[:50]}...'")
        saved = generate_veo_video(
            prompt,
            output_path,
            duration_seconds=int(max(4, min(8, duration))),
        )
        if saved and os.path.exists(saved):
            return saved
    except Exception as e:
        print(f"  [GoogleAI/Veo] Notice: {e}")
    return None


# ─── ITEM 130: İki Farklı Stok Sağlayıcıyı Karıştırma ───────────────────────

_SESSION_SOURCE_COUNTS: dict = {"pexels": 0, "pixabay": 0, "coverr": 0, "mixkit": 0, "ai": 0}


def get_session_source_distribution() -> dict:
    """Item 130 – Mevcut oturumdaki kaynak dağılımını döndürür."""
    return dict(_SESSION_SOURCE_COUNTS)


def reset_session_source_counts() -> None:
    """Item 130 – Oturum kaynak sayaçlarını sıfırlar."""
    for k in _SESSION_SOURCE_COUNTS:
        _SESSION_SOURCE_COUNTS[k] = 0


def _source_label_from_path(clip_path: str) -> str:
    """Infer stock provider label from downloaded clip filename."""
    if not clip_path:
        return "failed"
    basename = os.path.basename(clip_path).lower()
    for label in ("pexels", "pixabay", "coverr", "mixkit", "videvo"):
        if label in basename:
            return label
    if any(tag in basename for tag in ("ai_gen", "gemini", "veo", "_ai.", "ai_video", "pollinations", "flux")):
        return "ai"
    if "reddit" in basename or "procedural" in basename or "custom" in basename or "whiteboard" in basename:
        return "local"
    return "ai" if "ai" in basename else "local"


def _record_visual_manifest(
    clip_path: str,
    scene_index: int,
    source: str,
    source_id: str = "",
    title: str = "",
    *,
    tags=None,
    description: str = "",
    topic_match_score=None,
) -> None:
    """Record legacy stock clips in the auditable visual credits ledger."""
    if not clip_path or not os.path.isfile(clip_path):
        return
    try:
        from visuals.fetch import add_manifest_entry, get_job_manifest
        from visuals.license import License, LicenseInfo
        s_lower = (source or "").lower()
        if "ai" in s_lower or "pollinations" in s_lower or "flux" in s_lower or "veo" in s_lower:
            lic = License.AI_GENERATED
            src_name = "ai_generated"
        elif s_lower in ("custom", "local", "procedural", "whiteboard", "reddit"):
            lic = License.CC0
            src_name = source or "local"
        else:
            lic = {
                "pexels": License.PEXELS, "pixabay": License.PIXABAY,
                "coverr": License.COVERR, "mixkit": License.MIXKIT,
            }.get(s_lower, License.CC0)
            src_name = source or "stock"

        f_hash = _file_hash(clip_path)
        normalized_path = os.path.normcase(os.path.abspath(clip_path))
        if any(
            row.get("scene_index") == int(scene_index)
            and os.path.normcase(os.path.abspath(str(row.get("path") or ""))) == normalized_path
            for row in get_job_manifest()
        ):
            return
        entry = {
            "scene_index": int(scene_index), "path": clip_path,
            "uid": f"legacy:{src_name}:{source_id or f_hash}",
            "source": src_name, "id": source_id,
            "title": title or os.path.basename(clip_path), "kind": "video",
            "score": 0, "sha1": f_hash, "sha256": f_hash,
            "license": LicenseInfo(lic, src_name, title=title or os.path.basename(clip_path)).to_dict(),
        }
        if tags:
            entry["tags"] = tags
        if description:
            entry["description"] = description
        if isinstance(topic_match_score, (int, float)) and not isinstance(topic_match_score, bool):
            entry["topic_match_score"] = float(topic_match_score)
        add_manifest_entry({
            **entry,
        })
    except Exception as exc:
        print(f"    [VisualLedger] kayıt notu: {exc}")


def _pick_next_source(scene_index: int) -> str:
    """
    Item 130 – Belirleyici kaynak rotasyonu.
    Her sahne için önceki tercihlere bakarak en az kullanılan
    sağlayıcıyı seçer. Hedef: Tek bir video içinde
    en az 2 farklı sağlayıcıdan klip kullanılması.
    """
    counts = _SESSION_SOURCE_COUNTS

    if sum(counts.values()) == 0:
        sources = [
            "pexels", "pixabay", "coverr", "pexels", "pixabay",
            "mixkit", "pexels", "pixabay", "coverr",
        ]
        if _ai_image_providers_available():
            sources = [
                "pexels", "pixabay", "coverr", "pexels", "pixabay",
                "ai", "mixkit", "pexels", "pixabay", "coverr",
            ]
        return sources[scene_index % len(sources)]

    total = sum(counts.values())
    ai_ratio = counts["ai"] / max(1, total)

    if _ai_image_providers_available() and ai_ratio < 0.25 and scene_index % 4 == 3:
        return "ai"

    rotation = ["pexels", "pixabay", "coverr"]
    min_count = min(counts.get(s, 0) for s in rotation)
    least_used = [s for s in rotation if counts.get(s, 0) == min_count]
    return least_used[scene_index % len(least_used)]
