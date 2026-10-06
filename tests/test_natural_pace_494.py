"""Madde 494 keeps a natural pace. Long speech is condensed, never sped up."""
import os
import tempfile
import unittest
import wave
from unittest import mock

from director.schema import NATURAL_SHORTS_WORD_CAP, natural_narration_word_cap
from director.timeline import fit_tts_to_timeline, recover_overlong_narration, solve_timeline
from director.schema import DirectorPlan, QualityThresholds, ScenePlan
from scenes.retention_hooks import apply_retention_hooks_to_plan
from tts_engine import _parse_rate_pct, narration_rate_for_segment


def _sentence_bank(n_words: int) -> str:
    line = (
        "Resulullah buyurdu ki ameller ancak niyetlere göredir "
        "ve herkes niyet ettiği şeyi bulur."
    )
    words = []
    while len(words) < n_words:
        words.extend(line.split())
    return " ".join(words[:n_words - 1]) + " bulur."


def _plan_from_narration(text: str, niche: str = "16_islamic_wisdom") -> dict:
    chunks = []
    words = text.split()
    step = 12
    for i in range(0, len(words), step):
        piece = " ".join(words[i:i + step])
        if not piece.endswith("."):
            piece += "."
        chunks.append(piece)
    return {
        "title": "Sizin en hayırlınız Kur'an'ı öğrenen ve öğretendir",
        "niche_id": niche,
        "full_narration": " ".join(chunks),
        "scenes": [
            {"narration": c, "scene_description": "calm mosque courtyard", "duration": 5.0}
            for c in chunks
        ],
    }


class TestNaturalPace494(unittest.TestCase):
    def test_long_hadith_condenses_without_network_or_atempo(self):
        raw = _sentence_bank(179)
        self.assertEqual(len(raw.split()), 179)
        plan = _plan_from_narration(raw)
        cap = natural_narration_word_cap(179, 94.0)
        self.assertLessEqual(cap, NATURAL_SHORTS_WORD_CAP)
        self.assertEqual(cap, 110)

        def _net(*_a, **_k):
            raise AssertionError("network")

        with mock.patch("socket.create_connection", side_effect=_net):
            out = recover_overlong_narration(plan, audio_seconds=94.0)

        spoken = (out.get("full_narration") or "").split()
        self.assertLessEqual(len(spoken), 110)
        self.assertGreaterEqual(len(spoken), 48)
        self.assertLess(len(spoken), 179)
        blob = " ".join(spoken).lower()
        self.assertNotIn("başa dön", blob)
        self.assertNotIn("atempo", blob)

    def test_short_narration_unchanged(self):
        text = _sentence_bank(40)
        plan = _plan_from_narration(text, niche="6_stoic_philosophy")
        before = plan["full_narration"]
        out = recover_overlong_narration(plan, audio_seconds=20.0)
        self.assertEqual(out.get("full_narration"), before)
        self.assertEqual(len(out["scenes"]), len(plan["scenes"]))

    def test_fit_tts_94s_raises_and_does_not_speed(self):
        plan = DirectorPlan(
            title="hadis",
            niche_id="16_islamic_wisdom",
            scenes=[
                ScenePlan(index=0, narration=_sentence_bank(40), duration=30.0, scene_description="mosque")
            ],
            quality_thresholds=QualityThresholds(),
        )
        path = tempfile.mktemp(suffix="_tts94.wav")
        fr = 8000
        nframes = fr * 94
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(fr)
            w.writeframes(b"\x00\x00" * nframes)
        try:
            with self.assertRaises(RuntimeError) as ctx:
                fit_tts_to_timeline(path, plan, word_timings=[])
            msg = str(ctx.exception)
            self.assertIn("494", msg)
            self.assertNotIn("1.35", msg)
            with wave.open(path, "rb") as w:
                self.assertEqual(w.getnframes(), nframes)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def test_sacred_hooks_do_not_speak_basa_don(self):
        first = "Sizin en hayırlınız Kur'an'ı öğrenen ve öğretendir."
        last = "Buhari bu hadisi Fezailü'l-Kur'an bölümünde rivayet eder."
        plan = {
            "title": "Sizin en hayırlınız Kur'an'ı öğrenen ve öğretendir hadisi",
            "niche_id": "16_islamic_wisdom",
            "scenes": [
                {"narration": first},
                {"narration": last},
            ],
        }
        for niche in ("16_islamic_wisdom", "10_religious_quotes"):
            raw = {
                "title": plan["title"],
                "niche_id": niche,
                "scenes": [{"narration": first}, {"narration": last}],
            }
            out = apply_retention_hooks_to_plan(
                raw, raw["title"], lang="tr", niche_type=niche, variation_attempt=0,
            )
            spoken = " ".join(s["narration"] for s in out["scenes"]).lower()
            self.assertNotIn("başa dön", spoken)
            self.assertEqual(out["scenes"][-1]["narration"], last)
            self.assertEqual(out["retention_metadata"]["ending_bridge"], "")

    def test_110_word_narration_is_four_to_six_scenes(self):
        raw = _sentence_bank(110)
        self.assertLessEqual(len(raw.split()), 110)
        chunks = []
        words = raw.split()
        step = max(1, len(words) // 14)
        for i in range(0, len(words), step):
            piece = " ".join(words[i:i + step])
            if not piece.endswith("."):
                piece += "."
            chunks.append(piece)
        chunks = chunks[:14]
        while len(chunks) < 14:
            chunks.append(chunks[-1])
        chunks[3] = "çünkü."
        chunks[7] = "ve"
        chunks[11] = "ama."
        scenes = [
            ScenePlan(
                index=i,
                narration=chunk,
                duration=3.0,
                scene_description="calm mosque courtyard",
            )
            for i, chunk in enumerate(chunks)
        ]
        plan = DirectorPlan(
            title="Sizin en hayırlınız Kur'an'ı öğrenen ve öğretendir",
            niche_id="16_islamic_wisdom",
            scenes=scenes,
            quality_thresholds=QualityThresholds(min_scenes=8),
        )
        solved = solve_timeline(plan)
        self.assertGreaterEqual(len(solved.scenes), 4)
        self.assertLessEqual(len(solved.scenes), 6)
        spoken = (solved.full_narration or "").lower()
        self.assertNotIn("başa dön", spoken)
        self.assertNotIn("her şey bir seçimdir", spoken)
        self.assertNotIn("devam eder", spoken)
        self.assertNotIn("gerçek budur", spoken)
        for scene in solved.scenes:
            line = (scene.narration or "").strip()
            self.assertTrue(line.endswith((".", "!", "?")))
            bare = [w.strip(".,!?;:").lower() for w in line.split() if w.strip(".,!?;:")]
            self.assertFalse(len(bare) == 1 and bare[0] in {"ve", "ama", "çünkü"})
            self.assertNotIn(bare[-1], {"ve", "ama", "çünkü"})

    def test_single_sentence_is_not_split_to_fill_cadence(self):
        text = (
            "Resulullah buyurdu ki ameller ancak niyetlere göredir "
            "ve herkes niyet ettiği şeyi bulur."
        )
        plan = DirectorPlan(
            title="hadis",
            niche_id="16_islamic_wisdom",
            scenes=[
                ScenePlan(index=0, narration=text, duration=8.0, scene_description="mosque")
            ],
            quality_thresholds=QualityThresholds(min_scenes=14),
        )
        solved = solve_timeline(plan)
        self.assertEqual(len(solved.scenes), 1)
        self.assertEqual(solved.scenes[0].narration, text)

    def test_sacred_rate_is_calmer_than_hook_boost(self):
        import config
        prev_calm = config.TTS_SACRED_CALM
        prev_rate = config.TTS_RATE
        try:
            config.TTS_SACRED_CALM = False
            config.TTS_RATE = "+18%"
            rushed = narration_rate_for_segment(
                {"text": "Hayırlınız", "style": "hook", "prosody_rate": "+9%"},
                0,
                sacred_calm=False,
            )
            calm = narration_rate_for_segment(
                {"text": "Hayırlınız", "style": "hook", "prosody_rate": "+9%"},
                0,
                sacred_calm=True,
            )
            self.assertGreater(_parse_rate_pct(rushed), _parse_rate_pct("+18%"))
            self.assertEqual(calm, "+8%")
            self.assertLess(_parse_rate_pct(calm), _parse_rate_pct(rushed))
        finally:
            config.TTS_SACRED_CALM = prev_calm
            config.TTS_RATE = prev_rate


if __name__ == "__main__":
    unittest.main()
