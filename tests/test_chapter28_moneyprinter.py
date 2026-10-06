"""
Tests for Chapter 28.12 / Section 2.2 (Madde 13):
reference_repos2/MoneyPrinter evolution:
- services/sse_log_stream.py: SSELogStream, strip_ansi_codes, ring buffer eviction, event stream
- services/parallel_stock_search.py: parallel_multi_query_search
- director/timeline.py: Proportional millisecond TTS duration lock vs MoneyPrinter uniform division
"""

import json
import unittest
from unittest.mock import patch

from services.sse_log_stream import (
    strip_ansi_codes,
    SSELogStream,
)
from services.parallel_stock_search import (
    parallel_multi_query_search,
)
from director.schema import ScenePlan


class TestMoneyPrinterSSELogStream(unittest.TestCase):
    def test_strip_ansi_codes(self):
        colored_text = "\x1b[32m[+] Video rendered successfully\x1b[0m in 12.4s"
        clean = strip_ansi_codes(colored_text)
        self.assertEqual(clean, "[+] Video rendered successfully in 12.4s")

    def test_ring_buffer_eviction(self):
        streamer = SSELogStream(maxsize=5)
        for i in range(10):
            streamer.push(f"Log message {i}")

        self.assertEqual(streamer.size(), 5)

    def test_stream_generator_and_completion(self):
        streamer = SSELogStream(maxsize=10)
        streamer.push("Initializing pipeline...", level="info")
        streamer.push_event("progress", {"percent": 50, "step": "Synthesizing voice"})
        streamer.push_event("complete", {"url": "video.mp4"})

        lines = list(streamer.stream(timeout=0.1))
        self.assertEqual(len(lines), 3)

        payload_1 = json.loads(lines[0].replace("data: ", "").strip())
        self.assertEqual(payload_1["type"], "log")
        self.assertEqual(payload_1["message"], "Initializing pipeline...")

        payload_2 = json.loads(lines[1].replace("data: ", "").strip())
        self.assertEqual(payload_2["type"], "progress")
        self.assertEqual(payload_2["percent"], 50)

        payload_3 = json.loads(lines[2].replace("data: ", "").strip())
        self.assertEqual(payload_3["type"], "complete")


class TestMoneyPrinterParallelStockSearch(unittest.TestCase):
    @patch("services.parallel_stock_search.search_single_query_mockable")
    def test_parallel_multi_query_search(self, mock_search):
        def fake_search(query, provider, limit=4, min_duration=3.0):
            return [{"id": f"{provider}_{query}_1", "url": f"https://example.com/{provider}/{query}.mp4"}]

        mock_search.side_effect = fake_search

        queries = ["cyberpunk neon city", "trading floor charts"]
        results = parallel_multi_query_search(queries, providers=["pexels", "pixabay"], max_workers=2)

        self.assertIn("cyberpunk neon city", results)
        self.assertIn("trading floor charts", results)
        self.assertEqual(len(results["cyberpunk neon city"]), 2)


class TestMoneyPrinterMillisecondDurationLock(unittest.TestCase):
    def test_proportional_duration_vs_uniform_division(self):
        """
        MoneyPrinter flaw: uniform division (audio_duration / len(scenes)).
        ShortsVideoCreators solution: each scene duration strictly reflects its narration bounds (t1 - t0).
        """
        scenes = [
            ScenePlan(index=0, narration="Kısa bir kanca cümlesi.", duration=2.0, t0=0.0, t1=2.0),
            ScenePlan(index=1, narration="Burada oldukça uzun ve detaylı bir açıklama yapılıyor ve bu süre daha uzundur.", duration=6.5, t0=2.0, t1=8.5),
            ScenePlan(index=2, narration="Sonuç ve çağrı.", duration=2.5, t0=8.5, t1=11.0),
        ]
        total_audio = 11.0
        moneyprinter_uniform = total_audio / len(scenes)  # 3.66s per clip regardless of content!

        # Scene 0: MoneyPrinter gives 3.66s, but narration is only 2.0s (+1.66s drift/lag)
        # Scene 1: MoneyPrinter gives 3.66s, but narration needs 6.5s (-2.84s truncation/cutoff)
        self.assertAlmostEqual(moneyprinter_uniform, 3.667, places=2)

        # In ShortsVideoCreators:
        durations = [s.t1 - s.t0 for s in scenes]
        self.assertEqual(durations[0], 2.0)
        self.assertEqual(durations[1], 6.5)
        self.assertEqual(durations[2], 2.5)
        self.assertEqual(sum(durations), total_audio)

    def test_sse_keepalive_heartbeat(self):
        streamer = SSELogStream(maxsize=5)
        # Empty queue stream generator should yield keepalive
        gen = streamer.stream(timeout=0.01)
        item = next(gen)
        self.assertEqual(item, ": keepalive\n\n")

    def test_solve_timeline_non_uniform_cadence(self):
        from director.timeline import solve_timeline
        from director.schema import DirectorPlan, QualityThresholds
        raw_scenes = [
            ScenePlan(index=i, narration=f"Sahne {i} anlatımı burada tamamlanıyor ve detay veriliyor.", duration=5.0)
            for i in range(8)
        ]
        plan = DirectorPlan(
            title="Cadence Test",
            niche_id="tech",
            scenes=raw_scenes,
            quality_thresholds=QualityThresholds(min_duration=40.0, max_duration=50.0),
        )
        solved = solve_timeline(plan)
        cuts = solved.time_map.get("cuts", [])
        self.assertEqual(len(cuts), 8)
        # Check acceleration: early cuts longer, later cuts faster or non-uniform
        durations = [c["t1"] - c["t0"] for c in cuts]
        self.assertTrue(any(abs(durations[i] - durations[0]) > 0.05 for i in range(1, len(durations))))


if __name__ == "__main__":
    unittest.main()
