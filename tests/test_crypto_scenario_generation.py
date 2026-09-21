"""Finance/crypto live-trading scenario generation — narration + visuals quality."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_models import validate_generated_plan_errors
from director.compiler import compile_director_plan
from scenes.fallback import (
    sanitize_topic_title,
    _generate_procedural_fallback_scenes,
    _topic_is_crypto_market,
)
from scenes.narration_validate import plan_narration_usable, scene_narration_usable


LIVE_TOPIC = (
    "🔴LIVE TRADING: Gold & Bitcoin | 21st Sept 2026| "
    "#crypto #forex #btc #livetrading # #banknifty"
)


class TestCryptoScenarioGeneration(unittest.TestCase):
    def test_sanitize_topic_strips_noise(self):
        clean = sanitize_topic_title(LIVE_TOPIC)
        self.assertNotIn("#", clean)
        self.assertIn("LIVE TRADING", clean)
        self.assertIn("Gold", clean)
        self.assertIn("Bitcoin", clean)

    def test_topic_detected_as_crypto_market(self):
        self.assertTrue(_topic_is_crypto_market(LIVE_TOPIC, niche_type="8_crypto_market"))
        self.assertTrue(_topic_is_crypto_market(LIVE_TOPIC))

    def test_procedural_fallback_has_rich_scenes(self):
        plan = _generate_procedural_fallback_scenes(
            LIVE_TOPIC,
            niche_type="8_crypto_market",
            language="tr",
        )
        scenes = plan["scenes"]
        self.assertEqual(len(scenes), 14)
        self.assertTrue(plan_narration_usable(scenes))
        for sc in scenes:
            self.assertTrue(scene_narration_usable(sc["narration"]), sc.get("narration"))
            self.assertTrue((sc.get("scene_description") or "").strip())
            self.assertTrue(sc.get("search_queries"))
        moods = {s.get("mood") for s in scenes}
        self.assertGreater(len(moods), 1, "moods should vary by story beat")
        primary_queries = [s["search_queries"][0] for s in scenes]
        self.assertGreater(len(set(primary_queries)), 4, "search terms should diversify")

    def test_half_placeholder_plan_not_usable(self):
        good = "Bu sahne en az alti kelime iceren tam bir cumledir."
        scenes = [
            {"narration": good if i < 7 else ".", "search_queries": ["bitcoin chart"]}
            for i in range(14)
        ]
        self.assertFalse(plan_narration_usable(scenes))

    def test_plan_narration_usable_default_requires_all_scenes(self):
        """Default min_ratio=1.0 — one bad scene rejects entire plan."""
        good = "Bu sahne en az alti kelime iceren tam bir cumledir."
        scenes = [{"narration": good, "search_queries": ["bitcoin chart"]} for _ in range(13)]
        scenes.append({"narration": ".", "search_queries": ["bitcoin chart"]})
        self.assertFalse(plan_narration_usable(scenes))
        self.assertTrue(all(scene_narration_usable(s["narration"]) for s in scenes[:-1]))
        self.assertFalse(scene_narration_usable(scenes[-1]["narration"]))

    def test_schema_rejects_placeholder_narration(self):
        bad = {
            "scenes": [
                {
                    "narration": ".",
                    "search_queries": ["bitcoin chart"],
                }
                for _ in range(14)
            ]
        }
        errs = validate_generated_plan_errors(bad)
        self.assertTrue(errs)

    def test_astrology_procedural_fallback_has_rich_scenes(self):
        topic = "Koç Burcu Haftalık Yorum — Eylül 2026 astroloji"
        plan = _generate_procedural_fallback_scenes(
            topic,
            niche_type="18_astrology_horoscope",
            language="tr",
        )
        scenes = plan["scenes"]
        self.assertEqual(len(scenes), 14)
        self.assertTrue(plan_narration_usable(scenes))
        moods = {s.get("mood") for s in scenes}
        self.assertGreater(len(moods), 1)
        primary_queries = [s["search_queries"][0] for s in scenes]
        self.assertGreater(len(set(primary_queries)), 4)

    def test_compile_injects_fallback_when_ai_plan_empty(self):
        bad_plan = {
            "title": LIVE_TOPIC,
            "niche_id": "8_crypto_market",
            "scenes": [
                {
                    "narration": " ",
                    "scene_description": "",
                    "search_queries": ["bitcoin gold coin close up"],
                    "duration": 3.0,
                }
                for _ in range(14)
            ],
        }
        director = compile_director_plan(
            bad_plan,
            title=LIVE_TOPIC,
            niche_id="8_crypto_market",
            language="tr",
        )
        legacy = director.to_legacy_plan()
        self.assertTrue(plan_narration_usable(legacy["scenes"]))
        self.assertTrue(all((s.get("scene_description") or "").strip() for s in legacy["scenes"]))
        empty = sum(1 for s in legacy["scenes"] if not (s.get("narration") or "").strip())
        self.assertEqual(empty, 0)


if __name__ == "__main__":
    unittest.main()
