"""Content-driven Shorts length: 38–60 cap, 48 is not a magnet."""
import os
import tempfile
import unittest
import wave

from director.compiler import compile_director_plan
from director.schema import QualityThresholds, natural_target_duration, shorts_word_budget
from director.timeline import fit_tts_to_timeline, solve_timeline
from director.schema import DirectorPlan, ScenePlan
from viral_retention_engine import ViralRetentionEngine

FIFTEEN = "Bu sahne on beş kelimelik tam bir Türkçe cümle olarak burada bilinçle yazılmış duruyor şimdi."


class TestShortsDurationBand(unittest.TestCase):
    def test_natural_target_150_words_at_least_55s(self):
        self.assertEqual(15, len(FIFTEEN.split()))
        self.assertGreaterEqual(natural_target_duration(150), 55.0)
        self.assertLessEqual(natural_target_duration(150), 60.0)
        self.assertEqual(natural_target_duration(80), 38.0)
        self.assertEqual(natural_target_duration(200), 60.0)

    def test_word_budget_fits_emergency_speed(self):
        from director.schema import TTS_BUDGET_WPS_ELEVEN, TTS_EMERGENCY_MAX_SPEED, TTS_WORDS_PER_SEC
        from unittest import mock
        from tts_voices import ELEVENLABS_FREE_VOICES

        cap_edge = int(60.0 * TTS_EMERGENCY_MAX_SPEED * TTS_WORDS_PER_SEC)
        self.assertGreaterEqual(cap_edge, 170)

        cap_eleven = int(60.0 * TTS_EMERGENCY_MAX_SPEED * TTS_BUDGET_WPS_ELEVEN)
        # 170 words @ ~2.0 wps ElevenLabs ≈ 85s raw — must be rejected by cap
        self.assertLess(cap_eleven, 170)

        el_id = ELEVENLABS_FREE_VOICES[0]["id"]
        with mock.patch("config.TTS_VOICE", el_id):
            self.assertEqual(shorts_word_budget(60.0, 1.15), cap_eleven)

    def test_compiled_150_word_plan_not_shrunk_to_48(self):
        scenes = []
        for i in range(10):
            scenes.append({
                "narration": FIFTEEN,
                "scene_description": "Mosque courtyard fountain cinematic",
                "search_queries": ["mosque courtyard fountain", "dawn light", "calligraphy"],
                "duration": 3.0,
                "mood": "calm",
            })
        raw = {"title": "Hadis ve dua", "scenes": scenes, "full_narration": " ".join(FIFTEEN for _ in range(10))}
        plan = compile_director_plan(raw, title="Hadis ve dua", niche_id="10_religious_quotes")
        wc = len(plan.full_narration.split())
        self.assertGreaterEqual(wc, 140)
        total = plan.total_duration()
        self.assertGreaterEqual(total, 55.0)
        self.assertLessEqual(total, 60.0)
        self.assertNotAlmostEqual(total, 48.0, delta=0.4)

    def test_cadence_most_scenes_at_least_3_2(self):
        durs = ViralRetentionEngine.calculate_cadence_acceleration(58.0, 13)
        self.assertEqual(len(durs), 13)
        self.assertAlmostEqual(sum(durs), 58.0, delta=0.15)
        under = sum(1 for d in durs if d < 3.2 - 0.05)
        self.assertLessEqual(under, 2)

    def test_fit_tts_no_speedup_when_under_60(self):
        words = FIFTEEN
        scenes = [
            ScenePlan(index=i, narration=words, duration=5.5, scene_description="cinematic landscape aerial")
            for i in range(10)
        ]
        plan = DirectorPlan(
            title="test",
            niche_id="9_five_facts",
            scenes=scenes,
            quality_thresholds=QualityThresholds(),
        )
        plan = solve_timeline(plan)
        path = tempfile.mktemp(suffix="_tts55.wav")
        fr = 8000
        nframes = fr * 55
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(fr)
            w.writeframes(b"\x00\x00" * nframes)
        try:
            _p, _t, dur, speed = fit_tts_to_timeline(path, plan, word_timings=[])
            self.assertEqual(speed, 1.0)
            self.assertAlmostEqual(dur, 55.0, delta=0.2)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def test_fit_tts_emergency_from_72s_reaches_60(self):
        """Pass-2 must re-fit from ORIGINAL wav (never ffmpeg in-place on fitted)."""
        words = FIFTEEN
        scenes = [
            ScenePlan(index=i, narration=words, duration=5.0, scene_description="cinematic landscape aerial")
            for i in range(12)
        ]
        plan = DirectorPlan(
            title="test",
            niche_id="10_religious_quotes",
            scenes=scenes,
            quality_thresholds=QualityThresholds(),
        )
        plan = solve_timeline(plan)
        path = tempfile.mktemp(suffix="_tts72.wav")
        fitted = path.replace(".wav", "_fitted.wav")
        fr = 8000
        nframes = fr * 72
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(fr)
            w.writeframes(b"\x00\x00" * nframes)
        try:
            _p, _t, dur, speed = fit_tts_to_timeline(
                path, plan, word_timings=[], output_path=fitted
            )
            self.assertLessEqual(dur, 60.0 * 1.05)
            self.assertLessEqual(speed, 1.36)
            self.assertGreaterEqual(speed, 1.15)
        finally:
            for f in (path, fitted, fitted.replace(".wav", "_emergency.wav")):
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_ui_arc_labels_are_percent_based(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "static", "app.js"), encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn("totalSec * 0.07", js)
        self.assertIn("totalSec * 0.45", js)
        self.assertIn("totalSec * 0.75", js)
        self.assertNotIn("Math.min(3, totalSec)", js)
        with open(os.path.join(root, "static", "index.html"), encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn("arc-label-intro", html)
        self.assertNotIn("Giriş (0-3sn)", html)
        self.assertNotIn("Döngü (36-45sn)", html)


if __name__ == "__main__":
    unittest.main()
