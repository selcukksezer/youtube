"""Content upgrades taken from reference repos and tightened for the FFmpeg path."""
import os
import tempfile
import unittest

import config


class TestEmphasisBudget(unittest.TestCase):
    def test_numbers_and_power_words_get_a_second_layer_capped_at_three(self):
        from subtitle_generator import create_emphasis_overlay_ass

        timings = [
            {"text": "3", "offset": 0.5, "duration": 0.4},
            {"text": "milyarder", "offset": 3.0, "duration": 0.5},
            {"text": "gizemli", "offset": 5.5, "duration": 0.5},
            {"text": "12", "offset": 8.0, "duration": 0.4},
            {"text": "sokak", "offset": 8.5, "duration": 0.4},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "emphasis.ass")
            emp_file = create_emphasis_overlay_ass(timings, path)
            lines = open(emp_file, encoding="utf-8").read().splitlines()
        emphasis = [line for line in lines if line.startswith("Dialogue:")]
        self.assertEqual(len(emphasis), 3)
        self.assertNotIn("sokak", "".join(emphasis))


class TestHookCard(unittest.TestCase):
    def test_hook_card_writes_png(self):
        from effects.hook_card import create_hook_image

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "hook.png")
            written = create_hook_image("3 gizemli gerçek 🔥", 1080, out)
            self.assertEqual(written, out)
            self.assertGreater(os.path.getsize(out), 200)

    def test_empty_hook_is_skipped(self):
        from effects.hook_card import create_hook_image

        self.assertEqual(create_hook_image("  ", 1080, "unused.png"), "")


class TestMaterialFloor(unittest.TestCase):
    def test_whatsapp_478_passes_and_true_lowres_fails(self):
        from system_resilience import is_material_resolution_acceptable

        self.assertTrue(is_material_resolution_acceptable(478, 850))
        self.assertTrue(is_material_resolution_acceptable(710, 1280))
        self.assertFalse(is_material_resolution_acceptable(360, 640))
        self.assertFalse(is_material_resolution_acceptable(469, 1920))

    def test_verify_keeps_478_file(self):
        from system_resilience import verify_stock_video_integrity
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "rounded.mp4")
            with open(path, "wb") as handle:
                handle.write(b"x" * 2000)

            class Probe:
                stdout = "478,850,2.5"
                returncode = 0

            with patch("system_resilience.subprocess.run", return_value=Probe()):
                result = verify_stock_video_integrity(path)
            self.assertTrue(result["valid"], result)
            self.assertTrue(result["soft"])
            self.assertTrue(os.path.exists(path))


class TestShortClipPartner(unittest.TestCase):
    def test_two_second_file_on_five_second_scene_gets_a_second_clip(self):
        from server_core.render_worker import attach_short_clip_partners
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            primary = os.path.join(tmp, "head.mp4")
            partner = os.path.join(tmp, "tail.mp4")
            open(primary, "wb").write(b"h")
            open(partner, "wb").write(b"t")
            clips = [{"path": primary, "duration": 5.0}]
            scenes = [{
                "narration": "gizemli sokak",
                "scene_description": "dark street",
                "search_queries": ["dark street"],
                "visual_intent": {},
            }]
            with patch("render.ffmpeg_graph._probe_duration", return_value=2.0), \
                    patch("server_core.render_worker.fetch_scene_clip", return_value=partner) as fetch:
                count = attach_short_clip_partners(clips, scenes, tmp)
            self.assertEqual(count, 1)
            self.assertEqual(clips[0]["tail_path"], partner)
            self.assertEqual(clips[0]["head_duration"], 2.0)
            self.assertEqual(fetch.call_args.kwargs["allow_procedural"], False)
            self.assertNotIn("stream_loop", "")

    def test_long_enough_file_does_not_fetch_a_partner(self):
        from server_core.render_worker import attach_short_clip_partners
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            primary = os.path.join(tmp, "head.mp4")
            open(primary, "wb").write(b"h")
            clips = [{"path": primary, "duration": 5.0}]
            with patch("render.ffmpeg_graph._probe_duration", return_value=5.0), \
                    patch("server_core.render_worker.fetch_scene_clip") as fetch:
                count = attach_short_clip_partners(clips, [{}], tmp)
            self.assertEqual(count, 0)
            fetch.assert_not_called()
            self.assertNotIn("tail_path", clips[0])


class TestSceneTailConcat(unittest.TestCase):
    def test_short_head_concatenates_tail_instead_of_loop(self):
        from render.ffmpeg_graph import build_scene_filter_chain

        chain = build_scene_filter_chain(
            0, 5.0, 1080, 1920, 0,
            enable_ken_burns=False,
            tail_input_index=1,
            head_seconds=2.0,
        )
        self.assertIn("concat=n=2", chain)
        self.assertIn("[0:v]trim=duration=2.000", chain)
        self.assertIn("[1:v]trim=duration=3.000", chain)
        self.assertNotIn("stream_loop", chain)


class TestCutawayPlan(unittest.TestCase):
    def test_cutaway_uses_a_clip_that_is_not_on_screen(self):
        from render.ffmpeg_graph import _plan_cutaways

        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name in ("a.mp4", "b.mp4", "c.mp4"):
                path = os.path.join(tmp, name)
                open(path, "wb").write(b"x")
                paths.append(path)
            clips = [
                {"path": paths[0], "duration": 4.0},
                {"path": paths[1], "duration": 4.0},
                {"path": paths[2], "duration": 4.0},
            ]
            prev = config.RENDER_SAFE_MODE
            config.RENDER_SAFE_MODE = False
            try:
                cues = _plan_cutaways(clips, 12.0, [{"text": "gizemli"}])
            finally:
                config.RENDER_SAFE_MODE = prev
        self.assertTrue(cues)
        start, end = cues[0][1], cues[0][2]
        self.assertLessEqual(end - start, 3.2)
        self.assertNotEqual(cues[0][0], paths[0])

    def test_safe_mode_skips_algorithmic_cutaway(self):
        from render.ffmpeg_graph import _plan_cutaways

        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name in ("a.mp4", "b.mp4", "c.mp4"):
                path = os.path.join(tmp, name)
                open(path, "wb").write(b"x")
                paths.append(path)
            clips = [{"path": p, "duration": 4.0} for p in paths]
            prev = config.RENDER_SAFE_MODE
            config.RENDER_SAFE_MODE = True
            try:
                cues = _plan_cutaways(clips, 12.0, [{"text": "gizemli"}])
            finally:
                config.RENDER_SAFE_MODE = prev
        self.assertEqual(cues, [])


if __name__ == "__main__":
    unittest.main()
