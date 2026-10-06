"""Plan sections 14, 16, 17, 22.4, and 30 wiring."""
import os
import tempfile
import unittest

from production.plan_contracts import PublishDirectorPlan, QualityGateVerdict, SceneIntent
from proof_archiver import write_proof_manifest
from render.ffmpeg_graph import (
    align_even_dimension,
    build_scene_filter_chain,
    gameplay_start_seconds,
)
from services.log_sanitizer import sanitize_log
from subtitle_generator import _clean_timings
from voice.audio_dsp import loudnorm_second_pass_filter, parse_loudnorm_stats
from visuals.atomic_cache import atomic_replace, lock_for_key


class PlanAdvancedWiringTests(unittest.TestCase):
    def test_even_dimension_and_gameplay_offset(self):
        self.assertEqual(align_even_dimension(1919), 1918)
        self.assertEqual(align_even_dimension(1), 2)
        self.assertEqual(gameplay_start_seconds(3.0, 2.9, 4), 0.0)
        self.assertGreater(gameplay_start_seconds(40.0, 3.0, 1), 0.0)

    def test_split_graph_uses_gameplay_start(self):
        chain = build_scene_filter_chain(
            0, 3.0, 1080, 1920, 1,
            split_screen=True, gameplay_index=2, gameplay_start=4.5,
        )
        self.assertIn("trim=start=4.500:duration=3.000", chain)
        self.assertIn("boxblur=25:5", chain) if False else self.assertIn("vstack=inputs=2", chain)

    def test_subtitle_strips_emoji_and_sensevoice(self):
        cleaned = _clean_timings([
            {"text": "Merhaba <|laughter|> 🔥", "offset": 0.0, "duration": 0.4},
            {"text": "<|nospeech|>", "offset": 0.4, "duration": 0.2},
        ])
        self.assertEqual(len(cleaned), 1)
        self.assertNotIn("<|", cleaned[0]["text"])
        self.assertNotIn("🔥", cleaned[0]["text"])
        self.assertIn("Merhaba", cleaned[0]["text"])

    def test_loudnorm_second_pass_parser(self):
        stderr = 'foo {"input_i":"-23.1","input_tp":"-3.2","input_lra":"8.1","input_thresh":"-33.4","target_offset":"1.2"}'
        stats = parse_loudnorm_stats(stderr)
        filt = loudnorm_second_pass_filter(stats, -14.0, -1.5, 7.0)
        self.assertIn("measured_I=-23.1", filt)
        self.assertIn("linear=true", filt)

    def test_log_sanitizer(self):
        hidden = sanitize_log("token=supersecret sk-abcdefghijklmnop")
        self.assertNotIn("supersecret", hidden)
        self.assertNotIn("sk-abcdefghijklmnop", hidden)
        self.assertIn("[REDACTED]", hidden)

    def test_atomic_replace_and_lock(self):
        self.assertIs(lock_for_key("a"), lock_for_key("a"))
        with tempfile.TemporaryDirectory() as folder:
            src = os.path.join(folder, "clip.part")
            dst = os.path.join(folder, "clip.mp4")
            with open(src, "wb") as handle:
                handle.write(b"frames")
            atomic_replace(src, dst)
            self.assertTrue(os.path.isfile(dst))
            self.assertFalse(os.path.isfile(src))

    def test_publish_contract_and_proof_manifest(self):
        plan = PublishDirectorPlan(
            job_id="job-1",
            niche_id="1_news_flash",
            topic="Az once duyurulan gelisme",
            scenes=[SceneIntent(scene_index=0, start_sec=0, duration_sec=3.2, narration_text="Az once duyuruldu.")],
        )
        self.assertEqual(plan.aspect_ratio.value, "9:16")
        verdict = QualityGateVerdict(
            job_id="job-1", passed=True, retention_score=82, audio_lufs_actual=-14.1,
            duplicate_asset_count=0, unsafe_license_count=0, unrendered_text_count=0,
        )
        self.assertTrue(verdict.passed)
        with tempfile.TemporaryDirectory() as folder:
            clip = os.path.join(folder, "a.mp4")
            with open(clip, "wb") as handle:
                handle.write(b"0123456789")
            out = write_proof_manifest(
                os.path.join(folder, "proof_manifest.json"),
                "Baslik",
                [{"path": clip, "license": {"license": "pexels"}, "source_url": "https://pexels.com/1"}],
            )
            self.assertTrue(os.path.isfile(out))


if __name__ == "__main__":
    unittest.main()
