"""Per-niche scenario packs — not one shared prompt for every niche."""
import os
import unittest

from director.schema import ScenePlan
from director.visual_intent import apply_visual_intents
from niche_templates import NICHES, get_niche_family, get_niche_prompt, get_scenario_pack
from scenes.enrichment import enrich_audio_visual_contrast_scenes
from scenes.fallback import _generate_procedural_fallback_scenes
from scenes.narration_validate import plan_quality_usable, scene_narration_usable


APP_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "app.js")


class TestScenarioNichePacks(unittest.TestCase):
    def test_all_35_niches_have_a_family(self):
        self.assertEqual(len(NICHES), 36)
        for nid in NICHES:
            fam = get_niche_family(nid)
            self.assertTrue(fam, nid)
            pack = get_scenario_pack(nid)
            self.assertEqual(pack["id"], nid)
            self.assertEqual(pack["min_scenes"], 8)
            self.assertEqual(pack["max_scenes"], 16)
            self.assertEqual(pack["min_duration"], 38.0)
            self.assertEqual(pack["max_duration"], 60.0)
            self.assertGreaterEqual(pack["min_words"], 10)

    def test_prompts_are_per_niche_not_one_global(self):
        crypto = get_niche_prompt("8_crypto_market", "Bitcoin şu an nerede", "tr")
        astro = get_niche_prompt("18_astrology_horoscope", "Koç burcu haftalık", "tr")
        mystery = get_niche_prompt("13_mystery_paranormal", "51. Bölge gizem", "tr")
        self.assertNotEqual(crypto, astro)
        self.assertNotEqual(astro, mystery)
        self.assertIn("8_crypto_market", crypto)
        self.assertIn("18_astrology_horoscope", astro)
        self.assertNotIn("TAM OLARAK 14", crypto)
        self.assertIn("8-16", crypto)
        self.assertIn("38-60", crypto)
        self.assertIn("horror", crypto.lower())
        self.assertIn("YASAK", crypto)
        self.assertIn("Item 273 şok/horror query bu nişte YASAK", crypto)
        self.assertIn("Item 273 şok/horror query bu nişte SERBEST", mystery)

    def test_crypto_stub_rejected_and_fallback_is_finance(self):
        stub = "Bitcoin su an kritik seviyede duruyor bekleyin."
        scenes = [
            {
                "narration": stub,
                "scene_description": "SCENE_DESCRIPTION",
                "search_queries": ["bitcoin chart"],
            }
            for _ in range(10)
        ]
        self.assertFalse(plan_quality_usable(scenes))
        plan = _generate_procedural_fallback_scenes(
            "Bitcoin şu an nerede", niche_type="8_crypto_market", language="tr"
        )
        self.assertTrue(plan_quality_usable(plan["scenes"]))
        joined = " ".join(s["narration"] for s in plan["scenes"]).lower()
        self.assertTrue("bitcoin" in joined or "piyasa" in joined or "grafik" in joined)

    def test_astrology_fallback_is_not_crypto(self):
        plan = _generate_procedural_fallback_scenes(
            "Koç Burcu Haftalık Yorum",
            niche_type="18_astrology_horoscope",
            language="tr",
        )
        joined = " ".join(s["narration"] for s in plan["scenes"]).lower()
        qjoin = " ".join(" ".join(s.get("search_queries") or []) for s in plan["scenes"]).lower()
        self.assertNotIn("bitcoin", joined)
        self.assertNotIn("kaldıraç", joined)
        self.assertNotIn("candlestick", qjoin)
        self.assertTrue("burç" in joined or "astroloji" in joined or "zodyak" in joined)
        self.assertGreaterEqual(len(plan["scenes"]), 8)
        self.assertLessEqual(len(plan["scenes"]), 16)

    def test_animal_fallback_is_not_crypto(self):
        plan = _generate_procedural_fallback_scenes(
            "Aslan avı belgesel",
            niche_type="35_animal_kingdom_stories",
            language="tr",
        )
        joined = " ".join(s["narration"] for s in plan["scenes"]).lower()
        qjoin = " ".join(" ".join(s.get("search_queries") or []) for s in plan["scenes"]).lower()
        self.assertNotIn("bitcoin", joined)
        self.assertNotIn("kaldıraç", joined)
        self.assertNotIn("candlestick", qjoin)
        self.assertTrue(plan_quality_usable(plan["scenes"]))
        for sc in plan["scenes"]:
            self.assertTrue(scene_narration_usable(sc["narration"]), sc.get("narration"))

    def test_horror_does_not_leak_into_finance_or_animals(self):
        for nid in ("8_crypto_market", "35_animal_kingdom_stories", "18_astrology_horoscope"):
            pack = get_scenario_pack(nid)
            self.assertFalse(pack["allow_shock_queries"], nid)
            scenes = [
                {"duration": 3.0, "search_queries": ["topic visual"], "narration": "Sakin tam bir cümle burada.", "beat_type": "conflict"}
                for _ in range(6)
            ]
            scenes[4]["beat_type"] = "climax"
            out = enrich_audio_visual_contrast_scenes(scenes, niche_id=nid)
            climax = next(s for s in out if s.get("audio_visual_contrast"))
            joined = " ".join(climax.get("search_queries") or []).lower()
            self.assertNotIn("horror", joined, nid)

    def test_placeholder_replaced_for_non_crypto_niche(self):
        scenes = [
            ScenePlan(
                index=0,
                narration="Koç burcu bu hafta aşk ve para konusunda kritik bir eşikte duruyor.",
                duration=3.0,
                scene_description="(SCENE_DESCRIPTION)",
                search_queries=["zodiac constellation night"],
            )
        ]
        out = apply_visual_intents(scenes, "18_astrology_horoscope", title="Koç burcu")
        self.assertNotIn("SCENE_DESCRIPTION", (out[0].scene_description or "").upper())

    def test_ui_cadence_not_hard_14_and_duration_38_60(self):
        with open(APP_JS, encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("Cadence: ${scenes.length}/14", src)
        self.assertIn("totalSec >= 38 && totalSec <= 60", src)
        self.assertNotIn("hedef 48", src)
        self.assertIn("tavan 60", src)
        self.assertIn("totalSec * 0.07", src)
        self.assertIn(r"[^\p{L}\p{N}\s\-&]", src)
        self.assertIn("words.length < 10", src)

    def test_religious_fallback_is_not_stoic(self):
        topic = "Hz Peygamber in en çok tekrar ettiği o dua bugün hayatınızı değiştirebilir"
        plan = _generate_procedural_fallback_scenes(
            topic, niche_type="10_religious_quotes", language="tr"
        )
        qjoin = " ".join(" ".join(s.get("search_queries") or []) for s in plan["scenes"]).lower()
        djoin = " ".join((s.get("scene_description") or "") for s in plan["scenes"]).lower()
        for tok in ("marcus", "aurelius", "roman bust", "colosseum", "stoic", "statue", "blacksmith"):
            self.assertNotIn(tok, qjoin, tok)
            self.assertNotIn(tok, djoin, tok)
        self.assertTrue("mosque" in qjoin or "quran" in qjoin or "prayer" in qjoin)
        moods = {(s.get("mood") or "").lower() for s in plan["scenes"]}
        self.assertGreaterEqual(len(moods), 4)
        total = sum(float(s.get("duration") or 0) for s in plan["scenes"])
        self.assertGreaterEqual(total, 38.0)
        self.assertLessEqual(total, 60.0)
        self.assertGreaterEqual(len(plan["scenes"]), 8)
        self.assertLessEqual(len(plan["scenes"]), 16)
        for sc in plan["scenes"]:
            self.assertNotIn("SCENE_DESCRIPTION", (sc.get("scene_description") or "").upper())
        under = sum(1 for s in plan["scenes"] if float(s.get("duration") or 0) < 3.2)
        self.assertLessEqual(under, 2)


if __name__ == "__main__":
    unittest.main()
