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
from scenes.narration_validate import (
    MIN_WORDS_PER_SCENE,
    plan_narration_usable,
    plan_quality_usable,
    scene_description_usable,
    scene_narration_usable,
)


LIVE_TOPIC = (
    "🔴LIVE TRADING: Gold & Bitcoin | 21st Sept 2026| "
    "#crypto #forex #btc #livetrading # #banknifty"
)

BITCOIN_TOPIC = "Bitcoin şu an nerede Bu seviyeyi geçerse her şey değişir"

GOOD_NARRATION = (
    "Bu sahne en az on iki kelime iceren tam ve anlamli bir Turkce cumledir."
)


def _stub_ai_plan(topic: str = BITCOIN_TOPIC, n: int = 14):
    """Simulates weak AI output: 6-8 word stubs + placeholder descriptions."""
    stub = "Bitcoin su an kritik seviyede duruyor bekleyin."
    return {
        "title": topic,
        "scenes": [
            {
                "narration": stub,
                "scene_description": "SCENE_DESCRIPTION",
                "search_queries": ["bitcoin chart screen"],
                "duration": 3.0,
            }
            for _ in range(n)
        ],
    }


class TestCryptoScenarioGeneration(unittest.TestCase):
    def test_sanitize_keeps_turkish_letters(self):
        """Python Unicode \\w keeps ş; JS sanitizer must use \\p{L} (see static/app.js)."""
        clean = sanitize_topic_title(BITCOIN_TOPIC)
        self.assertIn("şu", clean)
        self.assertIn("geçerse", clean)
        js_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "app.js")
        with open(js_path, encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn(r"[^\p{L}\p{N}\s\-&]", js)
        self.assertNotIn("keyword: apiTopic", js)

    def test_crypto_does_not_steal_other_niche(self):
        self.assertFalse(_topic_is_crypto_market(BITCOIN_TOPIC, niche_type="18_astrology_horoscope"))
        self.assertFalse(_topic_is_crypto_market(BITCOIN_TOPIC, niche_type="35_animal_kingdom_stories"))

    def test_crypto_fallback_duration_in_38_60(self):
        plan = _generate_procedural_fallback_scenes(
            BITCOIN_TOPIC, niche_type="8_crypto_market", language="tr"
        )
        total = sum(float(s.get("duration") or 0) for s in plan["scenes"])
        self.assertGreaterEqual(total, 38.0)
        self.assertLessEqual(total, 60.0)
        self.assertGreater(total, 42.5)

    def test_sanitize_topic_strips_noise(self):
        clean = sanitize_topic_title(LIVE_TOPIC)
        self.assertNotIn("#", clean)
        self.assertIn("LIVE TRADING", clean)
        self.assertIn("Gold", clean)
        self.assertIn("Bitcoin", clean)

    def test_topic_detected_as_crypto_market(self):
        self.assertTrue(_topic_is_crypto_market(LIVE_TOPIC, niche_type="8_crypto_market"))
        self.assertTrue(_topic_is_crypto_market(LIVE_TOPIC))
        self.assertTrue(_topic_is_crypto_market(BITCOIN_TOPIC))

    def test_bitcoin_stub_plan_rejected_by_quality_gate(self):
        plan = _stub_ai_plan()
        self.assertFalse(plan_quality_usable(plan["scenes"]))
        self.assertFalse(scene_narration_usable(plan["scenes"][0]["narration"]))
        self.assertFalse(scene_description_usable(plan["scenes"][0]["scene_description"]))
        errs = validate_generated_plan_errors(plan)
        self.assertTrue(errs)

    def test_bitcoin_procedural_fallback_rich(self):
        plan = _generate_procedural_fallback_scenes(
            BITCOIN_TOPIC,
            niche_type="8_crypto_market",
            language="tr",
        )
        self.assertTrue(plan_quality_usable(plan["scenes"]))
        for sc in plan["scenes"]:
            self.assertGreaterEqual(
                len((sc.get("narration") or "").split()),
                MIN_WORDS_PER_SCENE,
                sc.get("narration"),
            )
            self.assertTrue(scene_description_usable(sc.get("scene_description") or ""))

    def test_procedural_fallback_has_rich_scenes(self):
        plan = _generate_procedural_fallback_scenes(
            LIVE_TOPIC,
            niche_type="8_crypto_market",
            language="tr",
        )
        scenes = plan["scenes"]
        self.assertGreaterEqual(len(scenes), 8)
        self.assertTrue(plan_quality_usable(scenes))
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
        scenes = [
            {"narration": GOOD_NARRATION if i < 7 else ".", "search_queries": ["bitcoin chart"]}
            for i in range(14)
        ]
        self.assertFalse(plan_narration_usable(scenes))
        self.assertFalse(plan_quality_usable(scenes))

    def test_plan_narration_usable_default_requires_all_scenes(self):
        """Default min_ratio=1.0 — one bad scene rejects entire plan."""
        scenes = [{"narration": GOOD_NARRATION, "search_queries": ["bitcoin chart"]} for _ in range(13)]
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
        self.assertGreaterEqual(len(scenes), 8)
        self.assertTrue(plan_quality_usable(scenes))
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
        self.assertTrue(plan_quality_usable(legacy["scenes"]))
        self.assertTrue(all((s.get("scene_description") or "").strip() for s in legacy["scenes"]))
        empty = sum(1 for s in legacy["scenes"] if not (s.get("narration") or "").strip())
        self.assertEqual(empty, 0)


if __name__ == "__main__":
    unittest.main()
