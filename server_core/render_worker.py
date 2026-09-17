"""
Video render worker and batch queue processor.
"""
import os
import sys
import json
import time
import subprocess
import asyncio
import re
import imageio_ffmpeg
import config
import database
from api_models import VideoRenderRequest
from scene_generator import generate_scenes
from video_fetcher import search_and_download, reset_used_videos, generate_ai_image_clip
from reddit_card_renderer import generate_reddit_post_card_clip
from tts_engine import generate_narration_with_timing
from video_composer import compose_video
from niche_templates import get_niche_production_profile
from subtitle_generator import SUBTITLE_PRESETS
from batch_processor import batch_manager
from notifications import notify_video_ready
from . import state


def process_video_task(req: VideoRenderRequest):
    old_stdout = sys.stdout
    sys.stdout = state.SSELogStreamer(old_stdout)
    db_id = None
    orig_lang = config.LANGUAGE
    orig_voice = config.TTS_VOICE
    orig_rate = config.TTS_RATE

    def check_cancelled():
        if state.current_render_state.get("cancel_requested"):
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    try:
        state.current_render_state["cancel_requested"] = False
        state.current_render_state["cancel_notified"] = False
        target_lang = (req.language or config.LANGUAGE or "tr").lower()
        config.LANGUAGE = target_lang

        gender = req.voice_gender or "male"
        if gender == "auto":
            from voice_humanizer import select_voice_gender
            gender = select_voice_gender(req.niche, req.keyword)
        voice_pool = config.VOICES.get(target_lang, config.VOICES.get("tr", {}))
        selected_voice = voice_pool.get(gender, "en-US-GuyNeural" if target_lang == "en" else "tr-TR-AhmetNeural")
        config.TTS_VOICE = selected_voice

        plan = req.plan
        keyword = (plan.get("title") if plan and plan.get("title") else req.keyword) or "Video"
        db_id = database.add_video_record(keyword, target_lang, config.AI_PROVIDER)
        state.broadcast_event("progress", {"percent": 5, "step": f"İşlem başlatılıyor: '{keyword}'..."})
        
        check_cancelled()

        # Safe directory and filename (ASCII converted for FFmpeg libass compatibility)
        tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
        safe = re.sub(r'[^\w\s-]', '', keyword.translate(tr_map))
        safe = re.sub(r'\s+', '_', safe.strip())[:80]
        if not safe:
            safe = f"shorts_{int(time.time())}"
        proj = os.path.join(config.ASSETS_DIR, safe)

        os.makedirs(proj, exist_ok=True)
        reset_used_videos()

        # Step 1: Scene plan
        check_cancelled()
        if not plan:
            lang_label = "İngilizce" if target_lang == "en" else "Türkçe"
            msg = f"[1/4] AI senaryosu oluşturuluyor ({lang_label} - {config.AI_PROVIDER}): '{keyword}'"
            print(msg)
            state.broadcast_event("progress", {"percent": 15, "step": msg})
            plan = generate_scenes(keyword, niche_type=getattr(req, "niche", None))

        if req.reddit_post and req.niche == "2_reddit_confessions":
            from scene_generator import generate_reddit_rewrite_script
            source_text = f"{req.reddit_post.get('title', '')}\n{req.reddit_post.get('body', '')}"
            plan = generate_reddit_rewrite_script(source_text, lang=target_lang)
            plan["reddit_post"] = req.reddit_post

        plan["niche_profile"] = get_niche_production_profile(getattr(req, "niche", "1_news_flash") or "1_news_flash")

        with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

        from plagiarism_checker import check_script_originality
        is_original, similarity, matched_title = check_script_originality(
            plan.get("full_narration", ""),
            keyword=keyword,
            title=plan.get("title", keyword)
        )
        if not is_original:
            message = (
                f"Senaryo benzerlik eşiğini aştı (%{similarity * 100:.1f}); "
                f"en yakın kayıt: {matched_title or 'bilinmiyor'}."
            )
            if db_id:
                database.update_video_status(db_id, "failed", error_message=message)
            state.broadcast_event("error", message)
            return

        if db_id and plan.get("scenes"):
            database.save_scenes(db_id, plan["scenes"])

        check_cancelled()

        # Step 2: Download videos
        msg = f"[2/4] Stok videolar aranıyor ve indiriliyor ({len(plan.get('scenes', []))} sahne)..."
        print(msg)
        state.broadcast_event("progress", {"percent": 30, "step": msg})
        clips = []
        scenes = plan.get("scenes", [])
        total_s = len(scenes)
        gameplay_path = None
        if req.split_screen:
            state.broadcast_event("log", "Split-screen için benzersiz oyun/parkur klibi aranıyor...")
            gameplay_path = search_and_download(
                ["mobile game gameplay", "parkour game screen recording", "arcade gameplay"],
                10_000, proj, target_duration=12, preferred_source="pexels",
                cancel_check=lambda: state.current_render_state.get("cancel_requested", False), allow_custom=False
            )
            if not gameplay_path:
                raise RuntimeError("Split-screen için daha önce kullanılmamış oyun/parkur klibi bulunamadı.")
        for i, scene in enumerate(scenes):
            check_cancelled()
            q = scene.get("search_queries", [scene.get("search_query", "nature")])
            d = scene.get("duration", 7)
            desc = scene.get("scene_description", "")
            
            progress_pct = 30 + int((i / max(1, total_s)) * 30)
            step_msg = f"Stok klip indiriliyor [{i+1}/{total_s}]: {desc[:40]}..."
            state.broadcast_event("progress", {"percent": progress_pct, "step": step_msg})
            state.broadcast_event("log", f"  -> Sahne {i+1}/{total_s}: {desc[:50]}")
            
            source_slot = i % 3
            if i == 0 and plan.get("reddit_post"):
                p = generate_reddit_post_card_clip(plan["reddit_post"], os.path.join(proj, "s000_reddit_source.mp4"), duration=d)
            elif source_slot == 2:
                p = generate_ai_image_clip(
                    scene_description=desc or q[0],
                    output_path=os.path.join(proj, f"s{i:03d}_ai_gen.mp4"),
                    duration=d
                )
            else:
                provider = "pexels" if source_slot == 0 else "pixabay"
                p = search_and_download(
                    q, i, proj, target_duration=d, scene_description=desc,
                    preferred_source=provider,
                    cancel_check=lambda: state.current_render_state.get("cancel_requested", False)
                )
            clips.append({
                "path": p,
                "duration": d,
                "narration": scene.get("narration", ""),
                "badge_label": scene.get("badge_label"),
                "enable_pip": scene.get("enable_pip", False),
                "pip_path": scene.get("pip_path"),
                "handheld_shake": scene.get("handheld_shake", False),
                "wipe_transition": scene.get("wipe_transition", False),
                "wipe_direction": scene.get("wipe_direction", "horizontal")
            })
            time.sleep(0.1)

        check_cancelled()

        ok_clips = sum(1 for c in clips if c["path"])
        state.broadcast_event("log", f"[2/4] Stok klip indirme tamamlandı: {ok_clips}/{total_s} klip hazır.")
        if ok_clips == 0:
            state.broadcast_event("error", "Stok video indirilemedi.")
            if db_id: database.update_video_status(db_id, "failed")
            return

        # Step 3: Narration TTS
        check_cancelled()
        lang_title = "İngilizce" if target_lang == "en" else "Türkçe"
        msg = f"[3/4] {lang_title} Seslendirme üretiliyor (Edge TTS - {config.TTS_VOICE})..."
        print(msg)
        state.broadcast_event("progress", {"percent": 65, "step": msg})
        audio_path = os.path.join(config.AUDIO_DIR, f"{safe}.wav")

        from voice_humanizer import VoiceHumanizer
        asmr_profile = VoiceHumanizer.get_asmr_voice_settings(req.niche, keyword)
        _, timings = generate_narration_with_timing(plan["full_narration"], audio_path, voice_profile=asmr_profile)
        state.broadcast_event("log", f"[3/4] Seslendirme tamamlandı. {len(timings)} kelime zamanlaması çıkarıldı.")

        # Step 4: Video composition & SFX
        check_cancelled()
        msg = f"[4/4] Video birleştiriliyor, SFX ve Karaoke altyazılar işleniyor..."
        print(msg)
        state.broadcast_event("progress", {"percent": 80, "step": msg})
        output_file = os.path.join(config.OUTPUT_DIR, f"{safe}.mp4")

        sub_opts = {
            "color": req.subtitle_color,
            "highlight_color": req.subtitle_highlight_color,
            "font_size": req.subtitle_font_size,
            "y_position": req.subtitle_y_position,
        }
        if req.subtitle_preset and req.subtitle_preset in SUBTITLE_PRESETS:
            sub_opts.update(SUBTITLE_PRESETS[req.subtitle_preset])

        def on_compose_progress(pct, step_text="", *args, **kwargs):
            msg = step_text or kwargs.get("message") or kwargs.get("step") or ""
            state.broadcast_event("progress", {"percent": pct, "step": str(msg)})
            state.broadcast_event("log", f"  {msg}")

        # Step 3.8: Generate Viral SEO Metadata & 15 Tags (Items 346 - 410)
        from viral_seo_agent import generate_viral_seo_metadata
        state.broadcast_event("progress", {"percent": 75, "step": "15 Viral YouTube Etiketi & SEO Başlığı üretiliyor..."})
        seo_meta = generate_viral_seo_metadata(keyword)
        seo_file = os.path.join(config.OUTPUT_DIR, f"{safe}_seo.json")
        try:
            with open(seo_file, "w", encoding="utf-8") as sf:
                json.dump(seo_meta, sf, ensure_ascii=False, indent=2)
            state.broadcast_event("log", f"  [Viral SEO] 15 Viral Etiket ve Tıklama Kancası hazırlandı: {seo_meta.get('seo_title', keyword)}")
        except Exception as se:
            print(f"  [SEO] Notice: {se}")

        result = compose_video(
            clips, audio_path, timings, output_file, title=keyword,
            bgm_track=req.bgm_track, bgm_volume=req.bgm_volume,
            subtitle_opts=sub_opts,
            progress_callback=on_compose_progress,
            cancel_check=lambda: state.current_render_state.get("cancel_requested", False),
            split_screen=getattr(req, "split_screen", False),
            anti_duplicate=getattr(req, "anti_duplicate", True),
            watermark_path=getattr(req, "watermark_path", None),
            enable_ken_burns=getattr(req, "enable_ken_burns", True),
            gameplay_path=gameplay_path
        )

        if result and os.path.exists(result) and os.path.getsize(result) > 100000:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            validation = subprocess.run(
                [ffmpeg_exe, "-v", "error", "-i", result, "-f", "null", "-"],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30
            )
            if validation.returncode != 0:
                raise RuntimeError(
                    "Render çıktısı çözümlenemedi: " +
                    validation.stderr.decode("utf-8", errors="ignore")[:300]
                )
            size_mb = round(os.path.getsize(result) / (1024*1024), 2)
            total_dur = sum(c["duration"] for c in clips)
            
            proof_filename = f"{os.path.splitext(os.path.basename(result))[0]}_proof.json"
            proof_full_path = os.path.join(config.BASE_DIR, "proofs", proof_filename)
            proof_url = f"/proofs/{proof_filename}" if os.path.exists(proof_full_path) else None

            if db_id:
                database.update_video_status(
                    db_id, "completed", os.path.basename(result), total_dur, size_mb,
                    seo_json=json.dumps(seo_meta, ensure_ascii=False),
                    proof_path=proof_full_path if os.path.exists(proof_full_path) else None
                )

            done_msg = f"🎉 Video üretimi tamamlandı! Dosya: {os.path.basename(result)} ({size_mb} MB, {total_dur:.1f}s)"
            print(done_msg)
            state.broadcast_event("progress", {"percent": 100, "step": "Video başarıyla tamamlandı!"})
            state.broadcast_event("complete", {
                "keyword": keyword,
                "filename": os.path.basename(result),
                "url": f"/output/{os.path.basename(result)}",
                "thumb_url": f"/output/{safe}_thumb.jpg" if os.path.exists(os.path.join(config.OUTPUT_DIR, f"{safe}_thumb.jpg")) else None,
                "seo": seo_meta,
                "proof_url": proof_url
            })
            notify_video_ready(keyword, f"/output/{os.path.basename(result)}", total_dur)
        else:
            if db_id: 
                database.update_video_status(db_id, "failed", error_message="Video birleştirme MoviePy/FFmpeg hatası nedeniyle tamamlanamadı.")
            state.broadcast_event("error", "Video birleştirme tamamlanamadı.")

    except (InterruptedError, asyncio.CancelledError):
        cancel_msg = "⛔ Video üretimi kullanıcı tarafından iptal edildi."
        print(cancel_msg)
        state.broadcast_event("progress", {"percent": 0, "step": "İşlem İptal Edildi"})
        state.broadcast_event("error", cancel_msg)
        if db_id:
            database.update_video_status(db_id, "cancelled", error_message="Kullanıcı tarafından iptal edildi.")
    except Exception as e:
        if db_id: 
            database.update_video_status(db_id, "failed", error_message=str(e))
        state.broadcast_event("error", f"İşlem hatası: {str(e)}")
    finally:
        state.current_render_state["cancel_requested"] = False
        state.current_render_state["cancel_notified"] = False
        state.current_render_state["is_rendering"] = False
        state.is_rendering_active = False
        config.LANGUAGE = orig_lang
        config.TTS_VOICE = orig_voice
        config.TTS_RATE = orig_rate
        sys.stdout = old_stdout


def process_batch_queue():
    while True:
        job = batch_manager.take_next_job()
        if not job:
            return
        with state.render_lock:
            if state.is_rendering_active:
                batch_manager.finish_current_job("queued")
                return
            state.is_rendering_active = True
        process_video_task(VideoRenderRequest(
            keyword=job["topic"],
            niche=job["niche"],
            language=job["language"],
            split_screen=job.get("split_screen", False),
            anti_duplicate=True,
            enable_ken_burns=True
        ))
        batch_manager.finish_current_job(
            "cancelled" if state.current_render_state.get("cancel_requested") else "completed"
        )
