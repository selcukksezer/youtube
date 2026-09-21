"""
Unit tests for Section 5 items 336-345 (batch 20 audit — Bölüm 5 kapanış).
"""
import unittest

from hybrid_niches import (
    HYBRID_NICHES,
    get_hybrid_niche,
    build_hybrid_prompt_block,
    enrich_plan_with_hybrid,
    generate_perfect_seamless_loop_bridge,
)
from director.visual_intent import resolve_topic_intelligence
from viral_retention_engine import ViralRetentionEngine


HYBRID_ITEM_KEYS = {
    336: "hidden_wiretap_meeting",
    337: "photo_restoration_story",
    338: "untranslatable_words_sonder",
    339: "country_popular_things_map",
    340: "corporate_dirty_secrets",
    341: "binaural_8d_audio_illusions",
    342: "alternate_history_ai",
    343: "childhood_nostalgia_90s_2000s",
    344: "inspirational_athlete_comeback",
}


class TestSection5Items336345(unittest.TestCase):
    def test_hybrid_library_covers_336_to_344_niches(self):
        for item_num, key in HYBRID_ITEM_KEYS.items():
            with self.subTest(item=item_num):
                self.assertIn(key, HYBRID_NICHES)
                entry = get_hybrid_niche(key)
                self.assertIn(f"Item {item_num}", entry["name"])
                self.assertTrue(entry.get("system_prompt_addition"))
                self.assertTrue(entry.get("loop_bridge"))
                self.assertTrue(entry.get("bg_style"))

    def test_item_345_perfect_seamless_loop_bridge(self):
        loop = generate_perfect_seamless_loop_bridge(
            "Marcus Aurelius'un o kuralı asla unutulmamalıdır.",
            video_index=2,
            lang="tr",
        )
        self.assertEqual(loop["retention_target_pct"], 200)
        self.assertIn("Marcus Aurelius", loop["closing_line"])
        self.assertTrue(loop.get("loop_bridge"))
        bridge_en = generate_perfect_seamless_loop_bridge("The secret begins here.", lang="en")
        self.assertIn("seamlessly", bridge_en["instruction"].lower())

    def test_item_345_uses_retention_engine_pool(self):
        loop = generate_perfect_seamless_loop_bridge("Test açılış.", video_index=0)
        pool = ViralRetentionEngine.get_diverse_loop_conjunctions()
        self.assertIn(loop["loop_bridge"], pool)

    def test_build_hybrid_prompt_block_wiretap(self):
        block = build_hybrid_prompt_block("hidden_wiretap_meeting", lang="tr")
        self.assertIn("HİBRİT NİŞ FORMAT", block)
        self.assertIn("mikrofon", block.lower())

    def test_enrich_plan_with_hybrid_alternate_history(self):
        plan = {
            "title": "Alternatif tarih what if ikinci dünya savaşı yaşanmasaydı timeline",
            "scenes": [{"search_queries": ["history"], "duration": 3.0}],
        }
        out = enrich_plan_with_hybrid(plan, plan["title"], "1_news_flash")
        self.assertEqual(out.get("hybrid_niche"), "alternate_history_ai")

    def test_topic_intelligence_hybrid_signals_336_344(self):
        cases = [
            ("gizli mikrofon sızdırılmış ses gizli toplantı kayıt fısıltı", "hidden_wiretap_meeting"),
            ("fotoğraf restorasyon 100 yıl yıpranmış renklendirme before after", "photo_restoration_story"),
            ("sonder bilinmeyen kelime untranslatable duygu anlam", "untranslatable_words_sonder"),
            ("ülke popüler en sevilen yemek harita world map spor", "country_popular_things_map"),
            ("kirli sır corporate skandal fast food pazarlama oyunu", "corporate_dirty_secrets"),
            ("8d ses binaural kulaklık kafanın arkası spatial audio", "binaural_8d_audio_illusions"),
            ("alternatif tarih what if ikinci dünya savaşı yaşanmasaydı", "alternate_history_ai"),
            ("90lar nostalji 2000ler çocukluk game boy vhs crt tv", "childhood_nostalgia_90s_2000s"),
            ("sporcu hikayesi sakatlıktan dönüş comeback şampiyon stadyum", "inspirational_athlete_comeback"),
        ]
        for topic, expected_hybrid in cases:
            with self.subTest(topic=topic[:40]):
                intel = resolve_topic_intelligence(topic, "1_news_flash")
                self.assertEqual(intel.get("hybrid_niche"), expected_hybrid)


if __name__ == "__main__":
    unittest.main()
