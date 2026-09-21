"""
Unit tests for Section 7 infrastructure items 441-465 (batch 27 audit).
Excluded: #441, #446, #457 (manual upload / OAuth out of scope).
"""
import inspect
import os
import unittest

import config
import database
import hybrid_niches
import niche_templates
from scenes.enrichment import enrich_cinematic_search_queries
from system_resilience import get_system_health_status
from video_fetcher import fetch_scene_clip


class TestSection7Items441465(unittest.TestCase):
    def test_excluded_upload_items_not_in_batch(self):
        excluded = {441, 446, 457}
        batch = set(range(441, 466)) - excluded
        self.assertEqual(len(batch), 22)
        self.assertFalse(excluded & batch)

    def test_item_439_encrypted_db_backup_wired(self):
        import database

        self.assertTrue(callable(getattr(database, "encrypted_db_backup", None)))
        self.assertTrue(callable(getattr(database, "maybe_schedule_encrypted_db_backup", None)))

    def test_item_442_dark_theme_css(self):
        css_path = os.path.join(config.BASE_DIR, "static", "style.css")
        with open(css_path, encoding="utf-8") as fh:
            css = fh.read()
        self.assertIn("--bg-base:", css)
        self.assertIn("data-theme", css)

    def test_item_443_keyboard_shortcuts(self):
        js_path = os.path.join(config.BASE_DIR, "static", "app.js")
        with open(js_path, encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn("Madde 443", js)
        self.assertIn("keydown", js)
        self.assertIn("Ctrl+Enter", js)
        self.assertIn("metaKey", js)

    def test_item_444_drag_and_drop(self):
        js_path = os.path.join(config.BASE_DIR, "static", "app.js")
        with open(js_path, encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn("csv-dropzone", js)
        self.assertIn("dragover", js)
        self.assertIn("drop", js)

    def test_item_445_render_worker_isolated(self):
        from server_core import render_worker

        src = inspect.getsource(render_worker.process_video_task)
        self.assertIn("DirectorPlan", src)
        index_path = os.path.join(config.BASE_DIR, "static", "index.html")
        with open(index_path, encoding="utf-8") as fh:
            html = fh.read()
        self.assertNotIn("process_video_task", html)

    def test_item_447_stock_blocklist(self):
        database.init_db()
        database.add_stock_blocklist("test_asset_999", "id", "audit test")
        self.assertTrue(database.is_stock_blocklisted(asset_id="test_asset_999"))
        import copyright_risk

        scan = copyright_risk.scan_copyright_risk(["epidemic_sound_track"])
        self.assertFalse(scan["safe"])

    def test_item_448_auto_delete_missing(self):
        worker_src = inspect.getsource(
            __import__("server_core.render_worker", fromlist=["process_video_task"]).process_video_task
        )
        self.assertIn("purge_old_videos", worker_src)
        self.assertIn("auto_delete", worker_src.lower())
        from system_resilience import purge_old_videos
        self.assertTrue(callable(purge_old_videos))

    def test_item_449_responsive_css(self):
        css_path = os.path.join(config.BASE_DIR, "static", "style.css")
        with open(css_path, encoding="utf-8") as fh:
            css = fh.read()
        self.assertIn("@media (max-width:", css)

    def test_item_450_cpu_thermal_missing(self):
        import hardware_detector

        src = inspect.getsource(hardware_detector.get_system_hardware_specs)
        self.assertIn("thermal", src.lower())
        thermal = hardware_detector.get_cpu_thermal_state()
        self.assertIn("thermal_throttle_recommended", thermal)

    def test_item_453_timeout_in_fetcher(self):
        src = inspect.getsource(fetch_scene_clip)
        self.assertIn("fetch_scene_clip", src)
        with open(
            os.path.join(config.BASE_DIR, "video_fetcher.py"), encoding="utf-8"
        ) as fh:
            vf_src = fh.read()
        self.assertIn("timeout=120", vf_src)

    def test_item_454_deepl_missing(self):
        self.assertFalse(hasattr(config, "DEEPL_API_KEY") and config.DEEPL_API_KEY)

    def test_item_455_prompt_enrichment(self):
        enriched = enrich_cinematic_search_queries(["ocean sunset"], mood="epic")
        self.assertTrue(any("cinematic" in q.lower() or "aerial" in q.lower() for q in enriched))

    def test_item_456_webm_support(self):
        with open(
            os.path.join(config.BASE_DIR, "video_fetcher.py"), encoding="utf-8"
        ) as fh:
            vf_src = fh.read()
        self.assertIn(".webm", vf_src)

    def test_item_458_db_indexes_partial(self):
        database.init_db()
        with database.get_connection() as conn:
            indexes = {
                row[1]
                for row in conn.execute(
                    "SELECT * FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }
        self.assertIn("idx_videos_created_at", indexes)
        self.assertNotIn("idx_videos_channel_slug", indexes)

    def test_item_459_html5_player(self):
        index_path = os.path.join(config.BASE_DIR, "static", "index.html")
        with open(index_path, encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn("<video", html)
        self.assertIn("controls", html)

    def test_item_460_watermark_overlay(self):
        from effects.overlays import overlay_watermark

        src = inspect.getsource(overlay_watermark)
        self.assertIn("set_opacity", src)

    def test_item_462_retry_partial(self):
        with open(
            os.path.join(config.BASE_DIR, "video_fetcher.py"), encoding="utf-8"
        ) as fh:
            dl_src = fh.read()
        self.assertNotIn("max_retries", dl_src)
        self.assertIn("trying [", dl_src)  # provider failover

    def test_item_463_modular_niche_dicts(self):
        self.assertIsInstance(niche_templates.NICHES, dict)
        self.assertIsInstance(hybrid_niches.HYBRID_NICHES, dict)
        self.assertGreaterEqual(len(hybrid_niches.HYBRID_NICHES), 20)

    def test_item_464_health_endpoint(self):
        health = get_system_health_status()
        self.assertIn("ffmpeg_installed", health)
        self.assertIn("disk", health)

    def test_item_465_zero_cost_stack(self):
        health = get_system_health_status()
        self.assertTrue(health.get("zero_cost_pipeline_active"))
        with open(
            os.path.join(config.BASE_DIR, "tts_engine.py"), encoding="utf-8"
        ) as fh:
            tts_src = fh.read()
        self.assertIn("Edge TTS", tts_src)


if __name__ == "__main__":
    unittest.main()
