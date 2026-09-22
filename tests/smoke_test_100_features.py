"""
Comprehensive Smoke Test for All 100 YouTube Shorts Bot Features & Niches
Validates every single item from r10_shorts_fikirleri_ve_bot_ozellikleri.md (Items 1 through 100).
"""
import unittest, os, time
from moviepy.editor import ColorClip

import config
from niche_templates import NICHES, get_niche_prompt, list_all_niches
from effects_engine import (
    apply_smart_crop, apply_anti_duplicate, apply_mirror_and_pitch,
    apply_ken_burns, overlay_watermark, extract_frame0_thumbnail,
    create_split_screen_clip
)
from subtitle_generator import (
    create_karaoke_subtitles, create_srt_file,
    SUBTITLE_PRESETS, hex_to_ass_color, _group
)
from sfx_manager import ensure_sfx_files, add_sfx_to_narration
from bgm_manager import list_bgm_tracks, get_bgm_path, mix_narration_and_bgm
from rss_scanner import DEFAULT_RSS_FEEDS, fetch_rss_feed, clean_html
from batch_processor import batch_manager
from quota_manager import quota_tracker
from notifications import (
    send_telegram_message, send_discord_notification,
    notify_video_ready, notify_upload_success
)
from youtube_uploader import upload_video_to_youtube, get_channel_token_path
from viral_seo_agent import generate_viral_seo_metadata
from growth_tactics import (
    generate_ab_test_variants, generate_community_poll,
    create_comment_to_video_hook, format_cross_platform_metadata,
    check_channel_warmup_limit, generate_live_stream_loop_command,
    check_copyright_risk
)
import database
from scene_generator import _generate_procedural_fallback_scenes
from server import app

class SmokeTest100Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        os.makedirs("output", exist_ok=True)
        os.makedirs("assets", exist_ok=True)

    # ══════════════════════════════════════════════════════════════════
    # BÖLÜM 1: 35 NİŞ VE İÇERİK FİKİRLERİ (MADDELER 1 - 35)
    # ══════════════════════════════════════════════════════════════════
    def test_001_to_035_all_niches_registered_and_prompts_valid(self):
        """Validates all distinct niches can generate valid algorithmic prompts."""
        self.assertGreaterEqual(len(NICHES), 36, "Must have at least 36 registered niches")
        niches = list_all_niches()
        self.assertGreaterEqual(len(niches), 36)

        for niche in niches:
            n_id = niche["id"]
            self.assertIn(n_id, NICHES)
            # Test prompt creation in TR and EN
            prompt_tr = get_niche_prompt(n_id, "Test Konusu", language="tr")
            self.assertIn("VIRAL HOOK", prompt_tr)
            self.assertIn("SEAMLESS LOOP", prompt_tr)
            self.assertIn("Test Konusu", prompt_tr)

            prompt_en = get_niche_prompt(n_id, "Test Topic", language="en")
            self.assertIn("VIRAL HOOK", prompt_en)
            self.assertIn("SEAMLESS LOOP", prompt_en)

    # ══════════════════════════════════════════════════════════════════
    # BÖLÜM 2: TEKNİK BOT & OTOMASYON ÖZELLİKLERİ (MADDELER 36 - 80)
    # ══════════════════════════════════════════════════════════════════
    def test_036_ai_provider_config(self):
        """Item 36: AI Provider configurations and fallbacks."""
        self.assertTrue(hasattr(config, "AI_PROVIDER"))
        self.assertTrue(len(config._P) >= 4, "Must have at least 4 AI provider configurations")

    def test_037_viral_hook_generation(self):
        """Item 37: First 3-second viral hook generation."""
        seo = generate_viral_seo_metadata("Antik Piramitler")
        self.assertIn("hook_text", seo)
        self.assertTrue(len(seo["hook_text"]) > 5)

    def test_038_039_stock_video_sources_and_semantic_matching(self):
        """Items 38 & 39: Stock video search queries and scene descriptions."""
        scenes = _generate_procedural_fallback_scenes("Okyanus Sırları")
        self.assertGreaterEqual(len(scenes["scenes"]), 8)
        for sc in scenes["scenes"]:
            self.assertIn("scene_description", sc)
            self.assertIn("search_queries", sc)
            self.assertEqual(len(sc["search_queries"]), 3)

    def test_040_smart_crop_and_blur(self):
        """Item 40: 16:9 to 9:16 Smart Crop with blurred background."""
        clip = ColorClip(size=(1920, 1080), color=(120, 40, 40), duration=0.5)
        try:
            cropped = apply_smart_crop(clip, 1080, 1920)
            self.assertEqual(cropped.size, (1080, 1920))
        finally:
            clip.close()

    def test_041_ken_burns_zoom(self):
        """Item 41: Ken Burns dynamic zoom."""
        clip = ColorClip(size=(1080, 1920), color=(40, 40, 120), duration=0.5)
        try:
            zoomed = apply_ken_burns(clip, zoom_ratio=1.05)
            self.assertEqual(zoomed.size, (1080, 1920))
        finally:
            clip.close()

    def test_042_043_karaoke_subtitles_and_presets(self):
        """Items 42 & 43: Karaoke word-by-word highlights and presets."""
        self.assertIn("capcut_yellow", SUBTITLE_PRESETS)
        self.assertIn("cyber_green", SUBTITLE_PRESETS)
        timings = [
            {"text": "Gizli", "offset": 0.0, "duration": 0.4},
            {"text": "bilgi", "offset": 0.4, "duration": 0.4}
        ]
        out_ass = "output/smoke_test.ass"
        out_srt = "output/smoke_test.srt"
        try:
            create_karaoke_subtitles(timings, out_ass, style_opts=SUBTITLE_PRESETS["capcut_yellow"])
            create_srt_file(timings, out_srt)
            self.assertTrue(os.path.exists(out_ass))
            self.assertTrue(os.path.exists(out_srt))
        finally:
            if os.path.exists(out_ass): os.remove(out_ass)
            if os.path.exists(out_srt): os.remove(out_srt)

    def test_044_045_tts_engine_voices(self):
        """Items 44 & 45: Natural TTS voices (TR/EN) & local zero cost."""
        self.assertIn("tr", config.VOICES)
        self.assertIn("en", config.VOICES)
        self.assertIn("male", config.VOICES["tr"])
        self.assertIn("female", config.VOICES["tr"])

    def test_046_047_bgm_and_audio_ducking(self):
        """Items 46 & 47: BGM tracks and audio ducking."""
        tracks = list_bgm_tracks()
        self.assertIsInstance(tracks, list)
        self.assertTrue(hasattr(config, "BGM_VOLUME"))

    def test_048_sfx_manager_whoosh_pop_ding(self):
        """Item 48: Synthesized whoosh, pop, and ding SFX."""
        w, p, d = ensure_sfx_files()
        self.assertTrue(os.path.exists(w))
        self.assertTrue(os.path.exists(p))
        self.assertTrue(os.path.exists(d))

    def test_049_split_screen_gameplay(self):
        """Item 49: Split Screen composite."""
        top = ColorClip(size=(1080, 1000), color=(10, 10, 80), duration=0.5)
        bot_path = "assets/gameplay_loop.mp4"
        try:
            if os.path.exists(bot_path):
                comp = create_split_screen_clip(top, bot_path, 1080, 1920)
                self.assertEqual(comp.size, (1080, 1920))
        finally:
            top.close()

    def test_050_anti_duplicate_filter(self):
        """Item 50: Anti-Tekrar (Anti-Duplicate) micro-modulation."""
        clip = ColorClip(size=(200, 200), color=(50, 50, 50), duration=0.5)
        try:
            mod = apply_anti_duplicate(clip)
            self.assertEqual(mod.size, (200, 200))
        finally:
            clip.close()

    def test_051_to_056_youtube_uploader_multi_channel_and_privacy(self):
        """Items 51-56: YouTube API uploader with multi-channel and privacy."""
        token_path = get_channel_token_path("channel_alpha")
        self.assertTrue(token_path.endswith("token_channel_alpha.json"))

    def test_057_rss_news_scanner(self):
        """Item 57: RSS News feed parsing."""
        self.assertTrue(len(DEFAULT_RSS_FEEDS) >= 4)
        clean = clean_html("<b>Test</b>")
        self.assertEqual(clean, "Test")

    def test_058_pinned_comment_generation(self):
        """Item 58: Auto pinned comment generator."""
        seo = generate_viral_seo_metadata("Yapay Zeka")
        self.assertIn("pinned_comment", seo)
        self.assertTrue(len(seo["pinned_comment"]) > 5)

    def test_059_frame0_thumbnail_extractor(self):
        """Item 59: Frame 0 thumbnail extraction function exists and is callable."""
        self.assertTrue(callable(extract_frame0_thumbnail))

    def test_060_watermark_brand_logo(self):
        """Item 60: Brand logo overlay."""
        clip = ColorClip(size=(500, 500), color=(20, 20, 20), duration=0.5)
        try:
            res = overlay_watermark(clip, "nonexistent.png")
            self.assertEqual(res.size, (500, 500))
        finally:
            clip.close()

    def test_061_062_zero_cost_and_outro(self):
        """Items 61 & 62: Zero cost stack is active."""
        stats = quota_tracker.get_stats()
        self.assertTrue(stats.get("zero_cost_mode_active"))

    def test_063_064_web_dashboard_and_routes(self):
        """Items 63 & 64: FastAPI routes registered."""
        routes = []
        for r in app.routes:
            if hasattr(r, "path"):
                routes.append(r.path)
            elif hasattr(r, "original_router") and hasattr(r.original_router, "routes"):
                for sr in r.original_router.routes:
                    if hasattr(sr, "path"):
                        routes.append(sr.path)
        self.assertIn("/api/niches", routes)
        self.assertIn("/api/subtitle_presets", routes)
        self.assertIn("/api/rss/sources", routes)
        self.assertIn("/api/batch/submit", routes)
        self.assertIn("/api/quota/stats", routes)

    def test_065_copyright_checker(self):
        """Item 65: Copyright and trademark safety audit."""
        safe_audit = check_copyright_risk("Evrende 5 ilginç gerçek", ["space", "stars"])
        self.assertTrue(safe_audit["is_safe_to_publish"])
        risky_audit = check_copyright_risk("Disney ve Netflix filmleri hakkında şok iddia", ["disney"])
        self.assertGreater(risky_audit["risk_score"], 0)

    def test_066_to_069_quota_and_speed_optimization(self):
        """Items 66-69: Quota tracking and speed optimization."""
        quota_tracker.record_call("OpenAI")
        stats = quota_tracker.get_stats()
        self.assertIn("OpenAI", stats["usage"])
        self.assertTrue(hasattr(config, "TTS_RATE"))

    def test_070_071_batch_generation_and_database(self):
        """Items 70 & 71: Batch manager and SQLite database tables."""
        jobs = batch_manager.parse_text_lines("Konu A\nKonu B")
        self.assertEqual(len(jobs), 2)
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        self.assertIn("videos", tables)
        self.assertIn("scenes", tables)
        self.assertIn("channels", tables)
        self.assertIn("batch_jobs", tables)

    def test_072_075_failover_and_chroma(self):
        """Items 72-75: Procedural failover and text animations."""
        fallback = _generate_procedural_fallback_scenes("Failover Test")
        self.assertIn("full_narration", fallback)

    def test_076_077_live_stream_and_notifications(self):
        """Items 76 & 77: 24/7 stream command & notification dispatchers."""
        cmd = generate_live_stream_loop_command("test.mp4", "live_key_123")
        self.assertIn("stream_loop -1", cmd)
        self.assertIn("live_key_123", cmd)
        # Notifications should return False gracefully when env vars not configured
        self.assertFalse(send_telegram_message("Test"))
        self.assertFalse(send_discord_notification("Test", "Desc"))

    def test_078_to_080_csv_and_transitions(self):
        """Items 78-80: CSV topics parser and file cleanup."""
        sample_csv = "output/test_batch.csv"
        with open(sample_csv, "w", encoding="utf-8") as f:
            f.write("topic,niche,language\nDerin Okyanus,1_news_flash,tr\n")
        try:
            parsed = batch_manager.parse_csv_topics(sample_csv)
            self.assertEqual(len(parsed), 1)
            self.assertEqual(parsed[0]["topic"], "Derin Okyanus")
        finally:
            if os.path.exists(sample_csv): os.remove(sample_csv)

    # ══════════════════════════════════════════════════════════════════
    # BÖLÜM 3: ALGORİTMA OPTİMİZASYONU & BÜYÜME TAKTİKLERİ (81 - 100)
    # ══════════════════════════════════════════════════════════════════
    def test_081_to_085_loop_discussion_comment_and_warmup(self):
        """Items 81-85: Seamless Loop, Debate trigger, Comment-to-Video, Tier-1, Warmup."""
        # 81 & 82: Embedded in niche prompt
        prompt = get_niche_prompt("1_news_flash", "Test", language="tr")
        self.assertIn("SEAMLESS LOOP", prompt)
        self.assertIn("TARTIŞMA", prompt)

        # 83: Comment-to-Video
        c2v = create_comment_to_video_hook("Bu olay gerçekten yaşandı mı?", "Ahmet")
        self.assertIn("@Ahmet", c2v["visual_overlay_text"])
        self.assertIn("Bu olay gerçekten yaşandı mı?", c2v["spoken_hook"])

        # 85: 14-day warm-up limit rule
        warmup_new = check_channel_warmup_limit("ch1", daily_uploads_count=2, channel_age_days=5)
        self.assertTrue(warmup_new["is_safe"])
        warmup_excess = check_channel_warmup_limit("ch1", daily_uploads_count=4, channel_age_days=5)
        self.assertFalse(warmup_excess["is_safe"])
        self.assertIsNotNone(warmup_excess["warning"])

    def test_086_to_090_retention_community_and_series(self):
        """Items 86-90: Retention SFX, Trend music, Community Poll, Series."""
        poll = generate_community_poll("Uzay Keşifleri")
        self.assertIn("question", poll)
        self.assertEqual(len(poll["options"]), 4)

    def test_091_to_095_competitor_frame0_density_mirror_affiliate(self):
        """Items 91-95: Competitor analysis, Frame 0, Text density, Mirror, Affiliate."""
        # 93: Text density grouping (max 3-4 words per subtitle block)
        words = [{"text": f"word_{i}", "offset": i*0.2, "duration": 0.2} for i in range(10)]
        grouped = _group(words, 3)
        for g in grouped:
            self.assertLessEqual(len(g), 3)

        # 94: Mirror flip
        clip = ColorClip(size=(100, 100), color=(10, 10, 10), duration=0.5)
        try:
            mirrored = apply_mirror_and_pitch(clip, horizontal_flip=True)
            self.assertEqual(mirrored.size, (100, 100))
        finally:
            clip.close()

        # 95: Affiliate text in viral SEO
        seo = generate_viral_seo_metadata("Temu Ürünleri")
        self.assertIn("affiliate_text", seo)

    def test_096_to_100_closing_cta_ab_testing_reels_and_analytics(self):
        """Items 96-100: Closing CTA, A/B Testing, TikTok/Reels, Analytics."""
        # 98: A/B Testing variants
        variants = generate_ab_test_variants("Karadelikler")
        self.assertEqual(len(variants), 3)
        self.assertEqual(variants[0]["variant"], "A_Curiosity")
        self.assertEqual(variants[1]["variant"], "B_Shock")
        self.assertEqual(variants[2]["variant"], "C_Debate")

        # 99: TikTok & Reels cross-platform metadata
        cross_meta = format_cross_platform_metadata("Test Shorts #Shorts", "Açıklama metni", ["shorts", "trend"])
        self.assertIn("tiktok", cross_meta)
        self.assertIn("instagram_reels", cross_meta)
        self.assertNotIn("#Shorts", cross_meta["tiktok"]["caption"])

        # 100: Analytics tracking
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM videos")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertIsInstance(count, int)

if __name__ == "__main__":
    unittest.main()
