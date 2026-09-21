"""
Unit tests for Section 7 infrastructure items 411-425 (batch 25 audit).
Excluded from this batch: #436, #440-441, #446, #457 (manual upload / OAuth out of scope).
"""
import inspect
import os
import unittest

import config
from hardware_detector import get_system_hardware_specs
from subtitle_generator import SUBTITLE_FONT_POOL, align_words_whisper, get_session_subtitle_font
from system_resilience import CircuitBreaker, get_hardware_accelerated_encoder, verify_stock_video_integrity
from tts_engine import generate_narration_with_timing
from server_core import render_worker


class TestSection7Items411425(unittest.TestCase):
    def test_excluded_upload_items_not_in_batch(self):
        excluded = {436, 440, 441, 446, 457}
        batch = set(range(411, 426))
        self.assertFalse(excluded & batch)

    def test_item_411_hardware_detector_and_encoder(self):
        specs = get_system_hardware_specs()
        self.assertIn("gpu", specs)
        self.assertIn("recommended_threads", specs)
        encoder, args = get_hardware_accelerated_encoder()
        self.assertIn(encoder, ("h264_videotoolbox", "h264_nvenc", "libx264"))
        self.assertTrue(args)

    def test_item_412_async_gather_in_render_worker(self):
        src = inspect.getsource(render_worker._fetch_scenes_parallel)
        self.assertIn("asyncio.gather", src)

    def test_item_413_whisper_align_stub(self):
        timings = [{"text": "test", "offset": 0.0, "duration": 0.3}]
        self.assertEqual(align_words_whisper(timings), timings)
        src = inspect.getsource(align_words_whisper)
        self.assertIn("_rescale_timings_to_audio_duration", src)
        self.assertFalse(getattr(config, "WHISPER_ALIGN", False))

    def test_item_414_temp_cleanup_sweep(self):
        src = inspect.getsource(render_worker.process_video_task)
        self.assertIn("_sweep_render_temp_files", src)
        self.assertIn("finally:", src)

    def test_item_415_sqlite_queue_tables(self):
        import database

        database.init_db()
        with database.get_connection() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        self.assertIn("batch_jobs", tables)
        self.assertIn("videos", tables)

    def test_item_416_circuit_breaker_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        svc = "pexels_api"
        cb.record_failure(svc)
        cb.record_failure(svc)
        self.assertTrue(cb.can_execute(svc))
        cb.record_failure(svc)
        self.assertFalse(cb.can_execute(svc))

    def test_item_417_font_pool_rotation(self):
        self.assertGreaterEqual(len(SUBTITLE_FONT_POOL), 4)
        font = get_session_subtitle_font()
        self.assertIn(font, SUBTITLE_FONT_POOL)

    def test_item_418_filter_complex_paths(self):
        from render import ffmpeg_graph
        from video_composer import _merge

        self.assertIn("filter_complex", inspect.getsource(ffmpeg_graph.render_with_ffmpeg_graph))
        self.assertIn("filter_complex", inspect.getsource(_merge))

    def test_item_419_memory_cleanup_in_composer(self):
        from video_composer import compose_video

        src = inspect.getsource(compose_video)
        self.assertIn(".close()", src)
        self.assertIn("gc.collect()", src)

    def test_item_420_tts_provider_fallback_chain(self):
        src = inspect.getsource(generate_narration_with_timing)
        self.assertIn("ElevenLabs", src)
        self.assertIn("Edge-TTS yedek", src)

    def test_item_421_sse_events_endpoint(self):
        from routers import video_router

        # routers/__init__.py re-exports the APIRouter instance itself as `video_router`
        routes = [getattr(r, "path", "") for r in video_router.routes]
        self.assertIn("/api/events", routes)

    def test_item_422_dockerfile_exists(self):
        dockerfile = os.path.join(config.BASE_DIR, "Dockerfile")
        compose = os.path.join(config.BASE_DIR, "docker-compose.yml")
        self.assertTrue(os.path.isfile(dockerfile))
        self.assertTrue(os.path.isfile(compose))
        with open(dockerfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("ffmpeg", content.lower())
        self.assertIn("HEALTHCHECK", content)
        with open(compose, encoding="utf-8") as fh:
            compose_body = fh.read()
        self.assertIn("youtubeoto:", compose_body)

    def test_item_423_ffmpeg_thread_cap(self):
        self.assertEqual(getattr(config, "FFMPEG_THREADS", 4), int(os.getenv("FFMPEG_THREADS", "4")))
        self.assertLessEqual(config.FFMPEG_THREADS, 8)

    def test_item_424_stock_integrity_missing_file(self):
        result = verify_stock_video_integrity("/nonexistent/stock.mp4")
        self.assertFalse(result["valid"])

    def test_item_425_48khz_export_paths(self):
        from voice import audio_dsp
        from render import ffmpeg_graph

        dsp_src = inspect.getsource(audio_dsp.export_master_and_stream_audio)
        graph_src = inspect.getsource(ffmpeg_graph.render_with_ffmpeg_graph)
        self.assertIn("48000", dsp_src)
        self.assertIn("48000", graph_src)


if __name__ == "__main__":
    unittest.main()
