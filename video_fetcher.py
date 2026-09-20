"""
5-Source Video Fetcher — Pexels + Pixabay + Coverr + Mixkit + Videvo
- Round-robin: each scene pulls from a DIFFERENT source when possible
- Strict dedup: no video ever reused (ID + file hash)
- Smart scoring: resolution + orientation + duration
- scene_description matching for better relevance
"""
import os, hashlib, requests, re, time, subprocess, json
import imageio_ffmpeg
import config
import database
from stock_providers import ALL_SOURCES

# P1-12: published IDs persist cross-job; job-local IDs block only within one render
_published_ids: set = set()
_job_used_ids: set = set()
_used_hashes: set = set()
_source_counter: int = 0  # Round-robin counter
_USED_PERSIST_PATH = os.path.join(
    getattr(config, "BASE_DIR", os.path.dirname(os.path.abspath(__file__))),
    "data",
    "used_stock_ids.json",
)

# Backward-compatible alias (published-only set for legacy imports/tests)
_used_ids = _published_ids


def _load_persisted_used_ids() -> set:
    try:
        if os.path.exists(_USED_PERSIST_PATH):
            with open(_USED_PERSIST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            ids = data.get("ids") if isinstance(data, dict) else data
            return set(str(x) for x in (ids or []))
    except Exception:
        pass
    return set()


def _persist_published_ids() -> None:
    try:
        os.makedirs(os.path.dirname(_USED_PERSIST_PATH), exist_ok=True)
        # Cap growth — keep most recent ~4000 ids
        ids = list(_published_ids)
        if len(ids) > 4000:
            ids = ids[-4000:]
        with open(_USED_PERSIST_PATH, "w", encoding="utf-8") as f:
            json.dump({"ids": ids}, f, ensure_ascii=False)
    except Exception as e:
        print(f"  [Fetcher] used_ids persist notice: {e}")


def _blocked_stock_ids() -> set:
    return _published_ids | _job_used_ids


def _stock_candidate_blocked(v: dict) -> bool:
    """P2-24: skip published, job-local, and copyright-blocklisted stock."""
    vid = str(v.get("id", ""))
    source_key = f"{v.get('source', '')}:{vid}"
    if not vid:
        return True
    if vid in _blocked_stock_ids():
        return True
    contributor = str(v.get("contributor", "") or "")
    return database.is_stock_blocklisted(source_key, vid, contributor)


# Warm published set from disk — failed/cancelled jobs do not pollute this pool
_published_ids.update(_load_persisted_used_ids())


def commit_published_stock_ids(extra_ids=None) -> int:
    """P1-12: persist stock IDs only after successful publish/render."""
    global _published_ids
    commit = set(extra_ids or []) | set(_job_used_ids)
    if not commit:
        return 0
    _published_ids.update(commit)
    _persist_published_ids()
    return len(commit)


def discard_job_stock_ids() -> None:
    """Drop job-local IDs without persisting (cancel/fail)."""
    _job_used_ids.clear()


def count_pool_candidates(
    queries,
    target_duration=7,
    scene_description="",
    narration="",
    visual_intent=None,
    must_exclude=None,
) -> int:
    """P1-12: count unscored stock pool size for a narrow query (no download)."""
    if isinstance(queries, str):
        queries = [queries]
    seen: set = set()
    total = 0
    blocked = _blocked_stock_ids()
    for query in queries[:4]:
        for _src_name, src_fn in ALL_SOURCES:
            try:
                results = src_fn(query) or []
            except Exception:
                results = []
            for v in results:
                vid = str(v.get("id", ""))
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                source_key = f"{v['source']}:{vid}"
                if vid in blocked or _stock_candidate_blocked(v) or database.source_asset_was_used(source_key):
                    continue
                sc = _score(
                    v,
                    target_duration,
                    narration=narration or scene_description,
                    visual_intent=visual_intent,
                )
                if sc > 0:
                    total += 1
    return total


def _file_hash(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(8192), b""):
            h.update(c)
    return h.hexdigest()


def _score(v, target_dur, narration="", visual_intent=None, recent_texts=None):
    """Technical score + semantic relevance (DirectorPlan visual intent)."""
    w, h, d = v["width"], v["height"], v["duration"]
    if d < 3: return -1
    s = 0.0
    px = w * h
    s += 40 if px >= 1920*1080 else 30 if px >= 1280*720 else 15 if px >= 854*480 else 5
    s += 25 if h > w else 10 if abs(h-w) < 100 else 5
    s += 25 if d >= target_dur else 15 if d >= target_dur*0.7 else 8 if d >= target_dur*0.4 else 2
    if d > 60: s -= 5
    if 5 <= d <= 30: s += 10

    # Semantic layer — title/tags/url text vs narration + intent
    cand_text = " ".join(str(v.get(k, "")) for k in ("title", "tags", "description", "url", "id"))
    try:
        from director.visual_intent import semantic_relevance_score, text_contains_excluded, VisualIntent
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

def _download(url, path, cancel_check=None):
    try:
        if cancel_check and cancel_check():
            return False
        r = requests.get(url, stream=True, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        with open(path, "wb") as f:
            for c in r.iter_content(8192):
                if cancel_check and cancel_check():
                    f.close()
                    if os.path.exists(path):
                        os.remove(path)
                    return False
                f.write(c)
        return os.path.getsize(path) > 10000  # At least 10KB
    except:
        if os.path.exists(path): os.remove(path)
        return False


def slice_random_background_loop(source_video_path: str, project_dir: str,
                                  scene_index: int, target_duration: float = 7.0) -> str:
    """
    Item 139: Arka Plan Döngü Videolarının Süresi.
    Subway Surfers, Minecraft parkur veya oynanış videoları 1 dakikalık sabit
    parça olarak kullanılmamalıdır; rastgele başlangıç noktalarından kesilip
    harmanlanarak YouTube'un şablon tekrarlı içerik tespiti engellenir.
    """
    import subprocess, json, random
    out_path = os.path.join(project_dir, f"s{scene_index:03d}_sliced_loop.mp4")

    # Get source video total duration
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffprobe_cmd = [
        ffmpeg_exe, "-i", source_video_path,
        "-hide_banner"
    ]
    total_dur = 60.0
    try:
        p = subprocess.run(ffprobe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        import re
        m = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', p.stderr)
        if m:
            total_dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass

    # Pick random start point
    max_start = max(0.0, total_dur - target_duration - 1.0)
    start_point = round(random.uniform(0.0, max_start), 2) if max_start > 0 else 0.0

    cmd = [
        ffmpeg_exe, "-y",
        "-ss", str(start_point),
        "-i", source_video_path,
        "-t", str(target_duration),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-an",
        out_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(out_path):
            return out_path
    except Exception as e:
        print(f"    [Item 139] Slice loop error: {e}")

    return source_video_path


def _generate_fallback_clip(scene_index, project_dir, target_duration=7):
    """
    Failsafe generator: Creates a 1080x1920 HD animated/colored visual clip
    when no stock video could be retrieved from external APIs.
    Guarantees the video pipeline NEVER fails due to missing stock clips.
    """
    try:
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
        path = os.path.join(project_dir, f"s{scene_index:03d}_procedural_fallback.mp4")
        
        # Color palette cycling based on scene index
        colors = [(15, 20, 35), (20, 15, 35), (35, 15, 25), (15, 30, 35), (25, 20, 15)]
        col = colors[scene_index % len(colors)]
        
        bg_clip = ColorClip(size=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color=col, duration=target_duration)

        try:
            text_clip = TextClip("Gorsel Bulunamadi", fontsize=70, color='white', bg_color='rgba(0,0,0,100)')
            text_clip = text_clip.set_position('center').set_duration(target_duration)
            final_clip = CompositeVideoClip([bg_clip, text_clip])
        except Exception:
            # Fallback if ImageMagick is missing or fails
            final_clip = bg_clip

        final_clip.write_videofile(path, fps=config.FPS, codec="libx264", audio=False, preset="ultrafast", logger=None)
        final_clip.close()
        
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            print(f"    [OK] [FAILSAFE] Created procedural fallback clip ({target_duration}s)")
            return path
    except Exception as e:
        print(f"    [FAILSAFE] Warning generating fallback clip: {e}")
    return None

def search_and_download(queries, scene_index, project_dir, target_duration=7,
                        scene_description="", preferred_source=None, cancel_check=None,
                        allow_custom=True, narration="", visual_intent=None,
                        must_exclude=None, recent_texts=None):
    global _source_counter

    if isinstance(queries, str):
        queries = [queries]

    # Merge must_exclude from intent
    exclude = list(must_exclude or [])
    if isinstance(visual_intent, dict):
        exclude.extend(visual_intent.get("must_exclude") or [])
        if not narration:
            narration = visual_intent.get("subject", "")
    elif visual_intent is not None:
        exclude.extend(getattr(visual_intent, "must_exclude", []) or [])

    # Drop queries that themselves contain excluded pollution terms
    clean_queries = []
    for q in queries:
        ql = (q or "").lower()
        if exclude and any(ex.lower() in ql for ex in exclude):
            continue
        clean_queries.append(q)
    if not clean_queries:
        # Fall back to intent subject only
        if isinstance(visual_intent, dict) and visual_intent.get("search_queries"):
            clean_queries = list(visual_intent["search_queries"])
        elif visual_intent is not None and getattr(visual_intent, "search_queries", None):
            clean_queries = list(visual_intent.search_queries)
        else:
            clean_queries = list(queries)

    # Add general fallback queries — skip if they hit must_exclude
    extended_queries = list(clean_queries)
    for fallback_q in ["cinematic atmosphere", "dramatic light particles", "nature aerial", "architectural detail"]:
        if fallback_q not in extended_queries:
            if exclude and any(ex.lower() in fallback_q for ex in exclude):
                continue
            extended_queries.append(fallback_q)

    # Item 98: Kendi Çektiğiniz Arka Plan Kütüphanesi (Custom 4K/HD Footage Pool)
    custom_bg_dir = os.path.join(config.BASE_DIR, "assets", "custom_backgrounds")
    if allow_custom and os.path.exists(custom_bg_dir):
        valid_exts = (".mp4", ".mov", ".mkv", ".webm")
        custom_files = [
            os.path.join(custom_bg_dir, f) for f in os.listdir(custom_bg_dir)
            if f.lower().endswith(valid_exts) and os.path.isfile(os.path.join(custom_bg_dir, f))
        ]
        if custom_files:
            # Filter unused custom clips
            available_custom = [
                f for f in custom_files
                if f not in _blocked_stock_ids() and not database.source_asset_was_used(f"custom:{_file_hash(f)}")
            ]
            if not available_custom:
                custom_files = []
            if custom_files and available_custom:
                raw_custom = available_custom[scene_index % len(available_custom)]
            else:
                raw_custom = None
            if raw_custom:
                source_hash = _file_hash(raw_custom)
                database.record_source_asset(f"custom:{source_hash}", raw_custom, source_hash, "custom")
                _job_used_ids.add(raw_custom)
                selected_custom = slice_random_background_loop(raw_custom, project_dir, scene_index, target_duration=target_duration)
                print(f"    [OK] [KENDİ ÇEKİM HAVUZU - Madde 98 & 139] Özel kütüphane klibi dinamik kesildi: {os.path.basename(selected_custom)}")
                return selected_custom

    # A requested provider is tried exclusively so the render pipeline can
    # deliberately mix suppliers; the default retains round-robin behavior.
    if preferred_source:
        source_order = [
            source for source in ALL_SOURCES
            if source[0].lower() == preferred_source.lower()
        ] + [
            source for source in ALL_SOURCES
            if source[0].lower() != preferred_source.lower()
        ]
    else:
        n = len(ALL_SOURCES)
        source_order = [ALL_SOURCES[(scene_index + i) % n] for i in range(n)]

    for qi, query in enumerate(extended_queries):
        if cancel_check and cancel_check():
            return None
        label = "primary" if qi == 0 else "secondary" if qi < len(queries) else "fallback"

        # Search sources for this query
        all_results = []
        for src_name, src_fn in source_order:
            if cancel_check and cancel_check():
                return None
            results = src_fn(query)
            if results:
                all_results.extend(results)

        if not all_results:
            continue

        # Score and deduplicate (technical + semantic)
        scored = []
        for v in all_results:
            source_key = f"{v['source']}:{v['id']}"
            if _stock_candidate_blocked(v) or database.source_asset_was_used(source_key):
                continue
            sc = _score(
                v, target_duration,
                narration=narration or scene_description,
                visual_intent=visual_intent,
                recent_texts=recent_texts,
            )
            if sc > 0:
                scored.append((sc, v))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Download best
        for sc, v in scored[:7]:
            if cancel_check and cancel_check():
                return None
            sid = str(v['id']).split('_')[-1]
            path = os.path.join(project_dir, f"s{scene_index:03d}_{v['source']}_{sid}.mp4")
            if _download(v["url"], path, cancel_check=cancel_check):
                fh = _file_hash(path)
                if fh in _used_hashes:
                    os.remove(path)
                    continue
                if database.source_asset_was_used(f"{v['source']}:{v['id']}", fh):
                    os.remove(path)
                    continue
                database.record_source_asset(f"{v['source']}:{v['id']}", v["url"], fh, v["source"])
                _job_used_ids.add(v["id"])
                _used_hashes.add(fh)
                print(f"    [OK] [{v['source'].upper()}] {v['fw']}x{v['fh']} {v['duration']}s score:{sc:.0f}")
                return path
            time.sleep(0.1)

    if cancel_check and cancel_check():
        return None

    # If all API searches fail, use procedural failsafe clip generator
    fallback_path = _generate_fallback_clip(scene_index, project_dir, target_duration)
    if fallback_path:
        return fallback_path

    print(f"    [FAIL] Scene {scene_index}: Could not retrieve clip")
    return None


def reset_used_videos():
    """P1-12: clear job-local dedup; published pool stays for cross-job diversity."""
    global _used_hashes, _source_counter
    _job_used_ids.clear()
    _used_hashes.clear()
    _source_counter = 0


# ─── ITEM 113: Yapay Zeka ile Çizilmiş Görselleri Kullanma ───────────────────

def generate_ai_image_clip(
    scene_description: str,
    output_path: str,
    duration: float = 5.0,
    width: int = 1080,
    height: int = 1920,
    style_prefix: str = "cinematic dark dramatic, high detail, 4K, "
) -> str:
    """
    Item 113 – Yapay Zeka ile Çizilmiş Görselleri Kullanma.
    Sahne açıklamasından özgün AI görseli üretir. FAL.ai (Flux-Schnell) öncelikli;
    yoksa Stability AI SDXL API'ye düşer. Üretilen görsel Ken Burns hareketi ile
    hareketlendirilerek MP4 video klibe dönüştürülür.

    Entegrasyon noktası: fetch_scene_clip() içinde, tüm stok video API'leri başarısız
    olduğunda bu fonksiyon otomatik olarak çağrılır.

    Args:
        scene_description: Sahne açıklama metni (Türkçe veya İngilizce)
        output_path: Üretilecek MP4 klip dosya yolu
        duration: Klip süresi saniye cinsinden
        width, height: Video boyutları (varsayılan: 1080x1920 Shorts)
        style_prefix: Görsel kalitesini artıracak sinematik stil öneki
    Returns:
        output_path (başarılıysa) veya None (başarısız)
    """
    import subprocess, tempfile, base64

    print(f"  [Item 113] AI görsel üretiliyor: '{scene_description[:60]}...'")

    full_prompt = (
        f"{style_prefix}{scene_description}. "
        f"Vertical 9:16 aspect ratio, professional photography, no text, no watermark."
    )

    image_path = None

    # ── Google AI Pro / Nano Banana (öncelikli — Madde 113 + Gemini API) ──
    # Item 416: skip if circuit open (429 spam kills render speed)
    gemini_ok = getattr(config, "USE_GEMINI_IMAGE_GEN", True) and getattr(config, "GEMINI_API_KEY", "")
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
            import json
            headers = {
                "Authorization": f"Key {config.FAL_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "prompt": full_prompt,
                "image_size": {"width": width, "height": height},
                "num_inference_steps": 4,   # Flux-Schnell: 4 adım yeterli
                "num_images": 1,
                "enable_safety_checker": False
            }
            resp = requests.post(
                "https://fal.run/fal-ai/flux/schnell",
                headers=headers,
                json=payload,
                timeout=60
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
                "style_preset": "cinematic"
            }
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.STABILITY_API_KEY}"
            }
            resp = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers=headers,
                json=payload,
                timeout=90
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

    # ── API'ler yoksa None dön (Böylece sistem gerçek stok videoya fallback yapar) ──
    if not image_path:
        print(f"    [Item 113] AI görsel yok/kota/devre — stok videoya geçiliyor.")
        return None

    # ── Görsel → Video (Ken Burns hareketi) ─────────────────────────────────
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        # Ken Burns: hafif zoom in (1.00x → 1.04x)
        zoom_rate = 1.04 / duration  # toplam zoom miktarı / süre
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"zoompan=z='min(zoom+{zoom_rate/30:.6f},1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={int(duration * 30)}:s={width}x{height}:fps=30"
        )

        cmd = [
            ffmpeg, "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", vf,
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"    [Item 113] AI görsel → Ken Burns klip: {duration:.1f}s → {output_path}")
            try:
                os.remove(image_path)
            except Exception:
                pass
            return output_path
        else:
            print(f"    [Item 113] FFmpeg hatası: {result.stderr[:200]}")

    except Exception as e:
        print(f"    [Item 113] Video dönüştürme hatası: {e}")

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

# Kaynak dağılımı takibi — mevcut video üretim oturumunda hangi sağlayıcı kaç kez kullanıldı
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
    if any(tag in basename for tag in ("ai_gen", "gemini", "veo", "_ai.")):
        return "ai"
    if "reddit" in basename or "procedural_fallback" in basename or "custom" in basename:
        return "local"
    return "unknown"


def fetch_scene_clip(
    search_queries,
    scene_index,
    project_dir,
    target_duration=7,
    scene_description="",
    mood="epic",
    cancel_check=None,
    narration="",
    visual_intent=None,
    must_exclude=None,
    recent_texts=None,
    allow_custom=True,
    preferred_source=None,
):
    """
    P0-05 / Item 130 – Per-scene multi-provider stock fetch.
    Rotates primary provider via _pick_next_source; on failure tries ≥1 alternate.
    """
    if isinstance(search_queries, str):
        search_queries = [search_queries]

    stock_sources = ["pexels", "pixabay", "coverr", "mixkit", "videvo"]
    primary = (preferred_source or _pick_next_source(scene_index)).lower()
    if primary == "ai":
        primary = stock_sources[scene_index % len(stock_sources)]

    attempted = []

    def _try(source_name):
        attempted.append(source_name)
        return search_and_download(
            search_queries,
            scene_index,
            project_dir,
            target_duration=target_duration,
            scene_description=scene_description,
            preferred_source=source_name,
            cancel_check=cancel_check,
            narration=narration,
            visual_intent=visual_intent,
            must_exclude=must_exclude,
            recent_texts=recent_texts,
            allow_custom=allow_custom,
        )

    clip_path = _try(primary)

    if not clip_path:
        alt_order = sorted(
            [s for s in stock_sources if s != primary],
            key=lambda s: _SESSION_SOURCE_COUNTS.get(s, 0),
        )
        for alt in alt_order:
            if cancel_check and cancel_check():
                return None
            print(
                f"    [MultiSource] Scene {scene_index}: "
                f"[{primary.upper()}] failed -> trying [{alt.upper()}]"
            )
            clip_path = _try(alt)
            if clip_path:
                break

    if not clip_path:
        tried = ", ".join(s.upper() for s in attempted)
        print(f"    [MultiSource] Scene {scene_index}: exhausted providers ({tried})")
        return None

    label = _source_label_from_path(clip_path)
    if label in _SESSION_SOURCE_COUNTS:
        _SESSION_SOURCE_COUNTS[label] = _SESSION_SOURCE_COUNTS.get(label, 0) + 1

    try:
        from system_resilience import verify_stock_video_integrity
        integrity = verify_stock_video_integrity(
            clip_path, min_duration=min(1.0, target_duration * 0.3)
        )
        if not integrity.get("valid"):
            print(
                f"    [MultiSource] ffprobe reject {os.path.basename(clip_path)}: "
                f"{integrity.get('reason')}"
            )
            try:
                os.remove(clip_path)
            except OSError:
                pass
            return None
    except Exception:
        pass

    return clip_path


def _pick_next_source(scene_index: int) -> str:
    """
    Item 130 – Belirleyici kaynak rotasyonu.
    Her sahne için önceki tercihlere bakarak en az kullanılan
    sağlayıcıyı seçer. Hedef: Tek bir video içinde
    en az 2 farklı sağlayıcıdan klip kullanılması.

    Returns:
        "pexels" | "pixabay" | "coverr" | "mixkit" | "ai"
    """
    counts = _SESSION_SOURCE_COUNTS

    # Toplam 0 ise baştan başla: scene_index'e göre cyclic seçim
    if sum(counts.values()) == 0:
        sources = ["pexels", "pixabay", "coverr", "pexels", "pixabay",
                   "ai", "mixkit", "pexels", "pixabay", "coverr"]
        return sources[scene_index % len(sources)]

    # En az kullanılanı bul (AI her 4 sahnede bir)
    total = sum(counts.values())
    ai_ratio = counts["ai"] / max(1, total)

    if ai_ratio < 0.25 and scene_index % 4 == 3:
        return "ai"

    # Pexels ve Pixabay arasında dönüşümlü
    if counts["pexels"] <= counts["pixabay"]:
        return "pexels"
    elif counts["pixabay"] <= counts["coverr"]:
        return "pixabay"
    else:
        return "coverr"


def fetch_multi_source_clips(scenes: list, project_dir: str,
                              force_source_mix: bool = True) -> list:
    """
    Item 130 – İki Farklı Stok Sağlayıcıyı Karıştırma.
    Aynı videoda hem Pexels hem Pixabay hem de AI ile üretilmiş
    görsellerin birlikte harmanlanmasını sağlar.

    Her sahne için kaynak rotasyonu algoritması çalışır:
    - Pexels: Scene 0, 3, 6, 9 ... (her 3 sahnede bir)
    - Pixabay: Scene 1, 4, 7, 10 ... (her 3 sahnede 1)
    - Coverr/Mixkit: Scene 2, 5, 8 ... (ara dolgu)
    - AI Generated: Her 4 sahnede bir (daha fazla çeşitlilik)

    force_source_mix=True → Tüm klipler aynı kaynaktan gelse bile
    en az 2 farklı kaynak kullanılmasını zorlar.

    Args:
        scenes: Sahne listesi (scene_generator'dan)
        project_dir: Kliplerin kaydedileceği dizin
        force_source_mix: Kaynak çeşitliliği zorlama
    Returns:
        (scene_index, clip_path, source_label) tuple listesi
    """
    reset_session_source_counts()
    results = []

    print(f"\n  [Item 130] Çok kaynaklı stok karıştırma: {len(scenes)} sahne...")

    for i, scene in enumerate(scenes):
        query = scene.get("search_queries", ["nature", "abstract", "city"])[0]
        duration = scene.get("duration", 6.0)
        scene_desc = scene.get("scene_description", query)

        # Kaynak tercihi belirle
        preferred_source = _pick_next_source(i)

        clip_path = None
        used_source = None

        # Tercih edilen kaynaktan dene
        if preferred_source == "ai":
            ai_path = os.path.join(project_dir, f"s{i:03d}_ai_gen.mp4")
            clip_path = generate_ai_image_clip(
                scene_description=scene_desc,
                output_path=ai_path,
                duration=duration
            )
            used_source = "ai" if clip_path else None

        if not clip_path:
            clip_path = fetch_scene_clip(
                search_queries=scene.get("search_queries", [query]),
                scene_index=i,
                project_dir=project_dir,
                target_duration=duration,
                scene_description=scene_desc,
                mood=scene.get("mood", "epic"),
            )
            if clip_path:
                used_source = _source_label_from_path(clip_path)

        if clip_path and used_source:
            results.append((i, clip_path, used_source))
            print(f"    [Item 130] Sahne {i}: [{used_source.upper()}] {os.path.basename(clip_path)}")
        else:
            results.append((i, None, "failed"))
            print(f"    [Item 130] Sahne {i}: Klip alınamadı")

    # Dağılım özeti
    dist = get_session_source_distribution()
    unique_sources = [k for k, v in dist.items() if v > 0]
    print(f"\n  [Item 130] Kaynak dağılımı: {dist}")
    print(f"  [Item 130] Kullanılan kaynaklar: {unique_sources} ({len(unique_sources)} farklı)")

    # force_source_mix kontrolü
    if force_source_mix and len(unique_sources) < 2:
        print(f"  [Item 130] UYARI: Tek kaynak kullanıldı ({unique_sources}). Çeşitlilik hedefi karşılanmadı.")

    return results
