"""6.1: stock providers together; generators start together only after a stock miss."""
import inspect
import os
import tempfile
import threading
import time
import unittest

from video_fetcher import gather_scene_pools


def _file(dirpath, name):
    path = os.path.join(dirpath, name)
    with open(path, "wb") as handle:
        handle.write(b"x" * 2000)
    return path


class TestChapter6PoolGather(unittest.TestCase):
    def test_stock_hit_does_not_start_generators(self):
        def boom():
            raise AssertionError("generator started after a stock hit")

        with tempfile.TemporaryDirectory() as tmp:
            stock = _file(tmp, "stock.mp4")
            winner = gather_scene_pools(
                ["tower"], 0, tmp,
                runners={"stock": lambda: stock, "flux": boom, "procedural": boom, "whiteboard": boom},
            )
        self.assertEqual(winner, stock)

    def test_generators_overlap_and_flux_wins(self):
        barrier = threading.Barrier(3)
        calls = []

        def run(name, filename, tmp):
            calls.append((name, time.monotonic()))
            barrier.wait(timeout=2)
            return _file(tmp, filename)

        with tempfile.TemporaryDirectory() as tmp:
            winner = gather_scene_pools(
                ["tower"], 1, tmp, allow_procedural=True,
                runners={
                    "stock": lambda: None,
                    "flux": lambda: run("flux", "flux.mp4", tmp),
                    "procedural": lambda: run("procedural", "proc.mp4", tmp),
                    "whiteboard": lambda: run("whiteboard", "wb.mp4", tmp),
                },
            )
            self.assertTrue(winner.endswith("flux.mp4"))
            self.assertFalse(os.path.exists(os.path.join(tmp, "proc.mp4")))
            self.assertFalse(os.path.exists(os.path.join(tmp, "whiteboard.mp4")))
        names = {name for name, _ in calls}
        self.assertEqual(names, {"flux", "procedural", "whiteboard"})
        stamps = [stamp for _, stamp in calls]
        self.assertLess(max(stamps) - min(stamps), 1.0)

    def test_procedural_when_flux_misses(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = _file(tmp, "proc.mp4")
            winner = gather_scene_pools(
                ["tower"], 2, tmp,
                runners={
                    "stock": lambda: None,
                    "flux": lambda: "",
                    "procedural": lambda: proc,
                    "whiteboard": lambda: _file(tmp, "wb.mp4"),
                },
            )
            self.assertEqual(winner, proc)
            self.assertFalse(os.path.exists(os.path.join(tmp, "wb.mp4")))

    def test_allow_procedural_false_skips_generators(self):
        def boom():
            raise AssertionError("generator started while procedural is off")

        winner = gather_scene_pools(
            ["tower"], 3, tempfile.gettempdir(), allow_procedural=False,
            runners={"stock": lambda: None, "flux": boom, "procedural": boom, "whiteboard": boom},
        )
        self.assertIsNone(winner)

    def test_live_fetch_calls_gather(self):
        src = inspect.getsource(__import__("video_fetcher").fetch_scene_clip)
        self.assertIn("gather_scene_pools", src)
        self.assertNotIn("alt_order", src)


if __name__ == "__main__":
    unittest.main()
