"""Batch 4: Completion Sprint 2 — hybrid_frame, #207 dopamin split, #422 Docker, #439 backup."""
import inspect
import os
import tempfile
import unittest

from moviepy.editor import ColorClip

import config
from effects.overlays import (
    apply_hybrid_frame_overlay,
    apply_hybrid_render_overlay,
    apply_eq_bar_overlay,
    apply_countdown_wheel_overlay,
    apply_neon_frame_overlay,
)
from hybrid_niches import (
    HYBRID_NICHES,
    HYBRID_RENDER_OVERLAY_MAP,
    get_hybrid_render_overlay_spec,
)
from scenes.retention_hooks import apply_retention_hooks_to_plan


class TestBatch4CompletionSprintWiring(unittest.TestCase):
    def test_hybrid_frame_overlay_applies(self):
        clip = ColorClip(size=(720, 1280), color=(20, 20, 40), duration=2.0)
        prev = getattr(config, "RENDER_SAFE_MODE", True)
        config.RENDER_SAFE_MODE = False
        try:
            out = apply_hybrid_frame_overlay(clip, label="Mitoloji AI", bg_style="myth epic")
            self.assertEqual(out.size, (720, 1280))
        finally:
            config.RENDER_SAFE_MODE = prev

    def test_all_unmapped_hybrids_get_hybrid_frame_spec(self):
        unmapped = set(HYBRID_NICHES.keys()) - set(HYBRID_RENDER_OVERLAY_MAP.keys())
        for hid in unmapped:
            spec = get_hybrid_render_overlay_spec(hid)
            self.assertEqual(spec.get("overlay"), "hybrid_frame")
            self.assertIn("hybrid_id", spec)

    def test_eq_and_wheel_overlay_specs(self):
        eq = get_hybrid_render_overlay_spec("subtitle_voice_equalizer")
        self.assertEqual(eq.get("overlay"), "eq_bar")
        wheel = get_hybrid_render_overlay_spec("interactive_stop_wheel_game")
        self.assertEqual(wheel.get("overlay"), "countdown_wheel")

    def test_hybrid_render_overlay_dispatch(self):
        clip = ColorClip(size=(720, 1280), color=(10, 10, 30), duration=2.5)
        prev = getattr(config, "RENDER_SAFE_MODE", True)
        config.RENDER_SAFE_MODE = False
        try:
            out = apply_hybrid_render_overlay(clip, {"overlay": "neon_frame", "item": 276})
            self.assertEqual(out.duration, 2.5)
            out2 = apply_eq_bar_overlay(clip, duration=2.0)
            self.assertEqual(out2.size, (720, 1280))
            out3 = apply_countdown_wheel_overlay(clip, duration=2.0)
            self.assertEqual(out3.size, (720, 1280))
        finally:
            config.RENDER_SAFE_MODE = prev

    def test_item_207_dopamin_split_screen_flag(self):
        plan = {
            "scenes": [
                {"narration": "Giriş.", "duration": 3.0},
                {"narration": "Kapanış.", "duration": 3.0},
            ]
        }
        out = apply_retention_hooks_to_plan(plan, "Psikoloji", lang="tr", variation_attempt=0)
        meta = out.get("retention_metadata") or {}
        self.assertTrue(meta.get("dopamin_split_screen"))
        self.assertTrue(out.get("hybrid_split_screen"))

    def test_item_422_docker_compose_exists(self):
        compose = os.path.join(config.BASE_DIR, "docker-compose.yml")
        self.assertTrue(os.path.isfile(compose))
        with open(compose, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("youtubeoto:", content)
        self.assertIn("healthcheck", content)

    def test_item_439_encrypted_db_backup(self):
        import database

        self.assertTrue(hasattr(database, "encrypted_db_backup"))
        src = inspect.getsource(database.encrypted_db_backup)
        self.assertIn("encrypted", src.lower())
        with tempfile.TemporaryDirectory() as tmp:
            test_db = os.path.join(tmp, "shorts.db")
            with open(test_db, "wb") as fh:
                fh.write(b"sqlite-test")
            old_path = database.DB_PATH
            database.DB_PATH = test_db
            try:
                enc = database.encrypted_db_backup(dest_dir=tmp, passphrase="test-pass")
                self.assertTrue(enc and os.path.isfile(enc))
                with open(enc, "rb") as fh:
                    self.assertTrue(fh.read(8).startswith(b"YTDBKP1"))
            finally:
                database.DB_PATH = old_path

    def test_render_worker_checks_dopamin_before_gameplay(self):
        from server_core import render_worker

        src = inspect.getsource(render_worker.process_video_task)
        self.assertIn("dopamin_split_screen", src)
        self.assertIn("needs_split_screen", src)


if __name__ == "__main__":
    unittest.main()
