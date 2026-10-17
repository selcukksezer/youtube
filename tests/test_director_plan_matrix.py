"""DirectorPlan unit tests — schema, timeline, visual lock, audio bus, quality gate."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from director import (
    compile_director_plan,
    solve_timeline,
    validate_director_plan,
    build_audio_events,
    collect_tape_stop_times,
    pre_render_score,
    resolve_niche_from_topic,
    resolve_topic_intelligence,
    semantic_relevance_score,
)
import config
from director.quality_gate import check_narration_integrity
from director.schema import DirectorPlan, ScenePlan, VisualIntent, QualityThresholds
from director.visual_intent import text_contains_excluded, apply_visual_intents


class TestTopicIntelligenceMatrix(unittest.TestCase):
    """P1-02: 20+ topic → niche resolution matrix (regex, alias, fuzzy, hybrid)."""

    TOPIC_CASES = [
        ("Marcus Aurelius stoacı kurallar", "1_news_flash", "6_stoic_philosophy"),
        ("whatsapp mesajları dram hikayesi", "1_news_flash", "20_whatsapp_chat_story"),
        ("AITA annem beni evden attı", "1_news_flash", "2_reddit_confessions"),
        ("SON DAKİKA deprem haberi", "6_stoic_philosophy", "1_news_flash"),
        ("bitcoin fiyatı düştü kripto", "1_news_flash", "8_crypto_market"),
        ("karanlık psikoloji manipülasyon", "1_news_flash", "7_dark_psychology"),
        ("yanlış bilinen 5 mit", "1_news_flash", "27_common_myths_busted"),
        ("tercih et uyumak mı yemek mi", "1_news_flash", "4_would_you_rather"),
        ("bayrak tahmin oyunu hangi ülke", "1_news_flash", "5_guess_flag_country"),
        ("bermuda üçgeni ufo gizemi", "1_news_flash", "13_mystery_paranormal"),
        ("Mbappe transfer haberi", "1_news_flash", "15_football_transfers"),
        ("sigma gigachad karakter analizi", "1_news_flash", "24_sigma_character_study"),
        ("minecraft split screen gameplay", "1_news_flash", "3_split_gameplay"),
        ("zengin olmak pasif gelir", "1_news_flash", "16_wealth_entrepreneurship"),
        ("chatgpt yapay zeka ipuçları", "1_news_flash", "21_ai_tools_hacks"),
        ("koç burcu astroloji yorumu", "1_news_flash", "18_astrology_horoscope"),
        ("netflix film özeti spoiler", "1_news_flash", "14_movie_summaries"),
        ("rüyada yılan görmek tabiri", "1_news_flash", "28_dream_meanings"),
        ("lamborghini süper araba", "1_news_flash", "31_supercars_automotive"),
        ("protein tozu fitness kas", "1_news_flash", "23_fitness_nutrition_hacks"),
        ("kuran ayeti dini söz", "1_news_flash", "10_religious_quotes"),
        ("Hz Peygamber in en çok tekrar ettiği o dua bugün hayatınızı değiştirebilir", "6_stoic_philosophy", "10_religious_quotes"),
        ("stoacilik disiplin motivasyon", "13_mystery_paranormal", "6_stoic_philosophy"),
        ("flaş haber trafik kaza", "6_stoic_philosophy", "1_news_flash"),
    ]

    def test_topic_niche_matrix(self):
        for topic, requested, expected in self.TOPIC_CASES:
            with self.subTest(topic=topic[:40]):
                got = resolve_niche_from_topic(topic, requested)
                self.assertEqual(got, expected, msg=f"{topic!r} -> {got}, want {expected}")

    def test_topic_intelligence_methods(self):
        intel = resolve_topic_intelligence("Marcus Aurelius stoacı", "1_news_flash")
        self.assertEqual(intel["resolved_niche"], "6_stoic_philosophy")
        self.assertIn(intel["match_method"], ("regex_lock", "alias", "fuzzy", "hybrid", "passthrough"))
        self.assertTrue(intel["locked"])

    def test_hybrid_niche_detection(self):
        intel = resolve_topic_intelligence(
            "Marcus Aurelius cyberpunk neon distopya gelecek",
            "1_news_flash",
        )
        self.assertEqual(intel["resolved_niche"], "6_stoic_philosophy")
        self.assertEqual(intel["hybrid_niche"], "stoic_cyberpunk")
        self.assertEqual(intel["match_method"], "regex_lock")

    def test_fuzzy_fallback_trending_keyword(self):
        intel = resolve_topic_intelligence("gündem breaking news gelişme", "6_stoic_philosophy")
        self.assertEqual(intel["resolved_niche"], "1_news_flash")


class TestChannelScopedOutput(unittest.TestCase):
    """P3-30: per-channel folder paths."""

    def test_default_channel_uses_legacy_dirs(self):
        paths = config.channel_paths(None)
        self.assertEqual(paths["slug"], "default")
        self.assertEqual(paths["assets_dir"], config.ASSETS_DIR)
        self.assertEqual(paths["output_dir"], config.OUTPUT_DIR)

    def test_named_channel_scoped_dirs(self):
        paths = config.channel_paths("Stoic TR Channel")
        self.assertEqual(paths["slug"], "stoic_tr_channel")
        self.assertIn("channels", paths["assets_dir"])
        self.assertIn("stoic_tr_channel", paths["assets_dir"])
        self.assertTrue(os.path.isdir(paths["assets_dir"]))


class TestFFmpegGraphHelpers(unittest.TestCase):
    def test_build_scene_filter_chain(self):
        from render.ffmpeg_graph import build_scene_filter_chain, get_look_filters
        chain = build_scene_filter_chain(0, 3.0, 1080, 1920, 0, enable_ken_burns=True)
        self.assertIn("trim=duration=3.000", chain)
        self.assertIn("[v0]", chain)
        self.assertNotIn("zoompan", chain)
        zoom = build_scene_filter_chain(
            0, 3.0, 1080, 1920, 0, enable_ken_burns=False, enable_zoompan=True,
        )
        self.assertIn("zoompan=", zoom)
        self.assertIn("1.000 + (0.120)", zoom)
        self.assertIn("cos(3.14159265", zoom)
        pan = build_scene_filter_chain(
            0, 3.0, 1080, 1920, 1, enable_ken_burns=False, enable_zoompan=True,
        )
        self.assertIn("z='1.12'", pan)
        pull = build_scene_filter_chain(
            0, 3.0, 1080, 1920, 2, enable_ken_burns=False, enable_zoompan=True,
        )
        self.assertIn("1.120 + (-0.120)", pull)
        padded = build_scene_filter_chain(
            0, 3.0, 1080, 1920, 0, enable_ken_burns=False, pad_seconds=1.2,
        )
        self.assertIn("tpad=stop_mode=clone:stop_duration=1.200", padded)
        shifted = build_scene_filter_chain(
            0, 3.0, 1080, 1920, 0, enable_ken_burns=False, crop_x=120,
        )
        self.assertIn("crop=1080:1920:x=120", shifted)
        look = get_look_filters(1080, 1920, anti_duplicate=True)
        self.assertIn("unsharp", look)
        self.assertIn("eq=", look)


if __name__ == "__main__":
    unittest.main()
