"""6.6: last missing-clip pass may synthesize; earlier passes stay stock-only."""
import inspect
import os
import tempfile
import unittest

from render.procedural_visuals import render_geq_fallback
from server_core.render_worker import procedural_on_retry_pass


class TestProceduralRetry(unittest.TestCase):
    def test_only_the_last_pass_opens_lavfi(self):
        self.assertFalse(procedural_on_retry_pass(1, 2))
        self.assertTrue(procedural_on_retry_pass(2, 2))

    def test_retry_wires_the_flag_and_k1_stays_stock(self):
        src = inspect.getsource(__import__("server_core.render_worker", fromlist=["process_video_task"]).process_video_task)
        self.assertIn("procedural_on_retry_pass(attempt, max_passes)", src)
        self.assertIn("allow_procedural=False", src)

    def test_geq_fallback_encodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "geq.mp4")
            out = render_geq_fallback(path, 1.2, scene_index=3, width=320, height=568, fps=12)
            self.assertEqual(out, path)
            self.assertGreater(os.path.getsize(path), 10_000)


if __name__ == "__main__":
    unittest.main()
