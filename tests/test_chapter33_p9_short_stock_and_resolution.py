"""
Unit and integration tests for Plan Item P9: Kısa stok ve düşük çözünürlük payı.
References:
- MoneyPrinterTurbo: _VIDEO_DURATION_SAFETY_MARGIN = 0.1, is_material_resolution_acceptable (470px floor for WhatsApp 478x850).
- saard00_shorts_generator: Short stock clip partner concatenation (concat=n=2) instead of stream_loop.
"""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from system_resilience import is_material_resolution_acceptable, verify_stock_video_integrity
from render.ffmpeg_graph import (
    VIDEO_DURATION_SAFETY_MARGIN,
    get_required_video_duration,
    build_scene_filter_chain,
)
from visuals.fetch import attach_short_clip_partners
from visuals.providers import Candidate
from visuals.license import License, LicenseInfo
from visuals.registry import score_candidate, reset_used


class TestResolutionFloor(unittest.TestCase):
    def test_whatsapp_and_telegram_tolerances(self):
        # 478x850 (WhatsApp rounded down from 480) must be accepted
        self.assertTrue(is_material_resolution_acceptable(478, 850))
        self.assertTrue(is_material_resolution_acceptable(850, 478))
        self.assertTrue(is_material_resolution_acceptable(470, 470))
        self.assertTrue(is_material_resolution_acceptable(720, 1280))
        self.assertTrue(is_material_resolution_acceptable(1080, 1920))

    def test_true_low_resolution_rejected(self):
        # Under 470px on either side must fail
        self.assertFalse(is_material_resolution_acceptable(469, 850))
        self.assertFalse(is_material_resolution_acceptable(850, 469))
        self.assertFalse(is_material_resolution_acceptable(360, 640))
        self.assertFalse(is_material_resolution_acceptable(240, 320))

    def test_invalid_and_edge_inputs(self):
        self.assertFalse(is_material_resolution_acceptable("abc", 1080))
        self.assertFalse(is_material_resolution_acceptable(None, 1080))
        self.assertFalse(is_material_resolution_acceptable(-10, 800))


class TestVideoDurationSafetyMargin(unittest.TestCase):
    def test_safety_margin_constant(self):
        self.assertEqual(VIDEO_DURATION_SAFETY_MARGIN, 0.1)

    def test_get_required_video_duration_default_and_custom(self):
        # Default safety margin adds 0.1s to audio duration
        self.assertAlmostEqual(get_required_video_duration(10.0), 10.1, places=3)
        self.assertAlmostEqual(get_required_video_duration(0.0), 0.1, places=3)
        self.assertAlmostEqual(get_required_video_duration(-5.0), 0.0, places=3)
        # Custom safety margin
        self.assertAlmostEqual(get_required_video_duration(15.0, safety_margin=0.25), 15.25, places=3)


class TestCandidateResolutionScoring(unittest.TestCase):
    def setUp(self):
        reset_used()

    def _make_candidate(self, width: int, height: int, uid: str = "cand_1") -> Candidate:
        return Candidate(
            source="pexels",
            id=uid,
            url="https://example.com/test.mp4",
            kind="video",
            width=width,
            height=height,
            duration=7.0,
            title="mysterious dark ancient street",
            license=LicenseInfo(License.PEXELS, "pexels", title="Test Pexels Clip"),
        )

    def test_score_candidate_accepts_whatsapp_478x850(self):
        cand = self._make_candidate(478, 850)
        score = score_candidate(cand, "mysterious street")
        self.assertGreater(score, 0.0)
        self.assertTrue(cand.semantic_evidence.get("subject_match", False))

    def test_score_candidate_rejects_360x640(self):
        cand = self._make_candidate(360, 640)
        score = score_candidate(cand, "mysterious street")
        self.assertEqual(score, -1e9)
        self.assertEqual(cand.semantic_evidence.get("rejected"), "low_resolution_360x640")

    def test_score_candidate_rejects_469x1920(self):
        cand = self._make_candidate(469, 1920)
        score = score_candidate(cand, "mysterious street")
        self.assertEqual(score, -1e9)
        self.assertEqual(cand.semantic_evidence.get("rejected"), "low_resolution_469x1920")

    def test_score_candidate_allows_zero_resolution_before_download(self):
        cand = self._make_candidate(0, 0)
        score = score_candidate(cand, "mysterious street")
        self.assertGreater(score, 0.0)


class TestVerifyStockVideoIntegrity(unittest.TestCase):
    def test_verify_keeps_whatsapp_resolution_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            video_path = os.path.join(tmp, "whatsapp_rounded.mp4")
            with open(video_path, "wb") as f:
                f.write(b"x" * 2048)

            class MockProbe:
                stdout = "478,850,3.5"
                returncode = 0

            with patch("system_resilience.subprocess.run", return_value=MockProbe()):
                res = verify_stock_video_integrity(video_path)
            self.assertTrue(res["valid"])
            self.assertTrue(res["soft"])
            self.assertTrue(os.path.exists(video_path))

    def test_verify_rejects_low_resolution_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            video_path = os.path.join(tmp, "lowres.mp4")
            with open(video_path, "wb") as f:
                f.write(b"x" * 2048)

            class MockProbe:
                stdout = "360,640,3.5"
                returncode = 0

            with patch("system_resilience.subprocess.run", return_value=MockProbe()):
                res = verify_stock_video_integrity(video_path)
            self.assertFalse(res["valid"])
            self.assertIn("470px altı", res["reason"])


class TestShortStockPartnerConcatenation(unittest.TestCase):
    def test_short_clip_attaches_partner_and_records_head_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary = os.path.join(tmp, "primary.mp4")
            partner = os.path.join(tmp, "partner.mp4")
            with open(primary, "wb") as f:
                f.write(b"primary_video_content")
            with open(partner, "wb") as f:
                f.write(b"partner_video_content")

            clips = [{"path": primary, "duration": 5.0}]
            scenes = [{
                "narration": "gizemli tapınak",
                "scene_description": "ancient temple",
                "search_queries": ["ancient temple"],
                "visual_intent": {},
            }]
            with patch("render.ffmpeg_graph._probe_duration", return_value=2.0), \
                    patch("visuals.fetch.fetch_scene_clip", return_value=partner) as mock_fetch:
                count = attach_short_clip_partners(clips, scenes, tmp, fetch_fn=mock_fetch)

            self.assertEqual(count, 1)
            self.assertEqual(clips[0]["tail_path"], partner)
            self.assertEqual(clips[0]["head_duration"], 2.0)
            self.assertFalse(mock_fetch.call_args.kwargs.get("allow_procedural", True))

    def test_adequate_clip_does_not_attach_partner(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary = os.path.join(tmp, "primary.mp4")
            with open(primary, "wb") as f:
                f.write(b"content")

            clips = [{"path": primary, "duration": 5.0}]
            with patch("render.ffmpeg_graph._probe_duration", return_value=5.0):
                mock_fetch = MagicMock()
                count = attach_short_clip_partners(clips, [{}], tmp, fetch_fn=mock_fetch)

            self.assertEqual(count, 0)
            mock_fetch.assert_not_called()
            self.assertNotIn("tail_path", clips[0])

    def test_ffmpeg_graph_compiles_concat_filter_without_stream_loop(self):
        chain = build_scene_filter_chain(
            input_index=0,
            duration=5.0,
            width=1080,
            height=1920,
            scene_index=0,
            enable_ken_burns=False,
            enable_zoompan=False,
            tail_input_index=1,
            head_seconds=2.0,
        )
        self.assertIn("concat=n=2", chain)
        self.assertIn("[0:v]trim=duration=2.000", chain)
        self.assertIn("[1:v]trim=duration=3.000", chain)
        self.assertIn("[seg0a][seg0b]concat=n=2:v=1:a=0[cat0]", chain)
        self.assertNotIn("stream_loop", chain)


if __name__ == "__main__":
    unittest.main()
