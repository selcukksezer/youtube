"""
Unit tests for Section 5 hybrid niches & growth tactics items 306-320 (batch 18 audit).
"""
import unittest

from hybrid_niches import (
    HYBRID_NICHES,
    get_hybrid_niche,
    build_hybrid_prompt_block,
    enrich_plan_with_hybrid,
    collide_two_niches,
    generate_episodic_series_hook,
)
from director.visual_intent import resolve_topic_intelligence
from growth_tactics import (
    generate_ab_test_variants,
    generate_community_poll,
    plan_shorts_from_poll_winner,
    create_comment_to_video_hook,
    generate_live_stream_loop_command,
    generate_micro_interview_dialogue,
    generate_seasonal_trend_hook,
    generate_affiliate_pinned_cta,
)
from viral_seo_agent import generate_related_video_bridge


HYBRID_ITEM_KEYS = {
    306: "iq_puzzle_optical_riddle",
    307: "entrepreneur_minimal_typography",
    308: "world_records_sports_commentary",
    309: "did_you_know_facts",
    316: "micro_street_interview",
    317: "seasonal_trend_reaction",
    318: "absurdist_philosophy_meme",
}


class TestSection5Items306320(unittest.TestCase):
    def test_hybrid_library_covers_306_to_309_and_316_to_318(self):
        for item_num, key in HYBRID_ITEM_KEYS.items():
            with self.subTest(item=item_num):
                self.assertIn(key, HYBRID_NICHES)
                entry = get_hybrid_niche(key)
                self.assertIn(f"Item {item_num}", entry["name"])
                self.assertTrue(entry.get("system_prompt_addition"))
                self.assertTrue(entry.get("loop_bridge"))
                self.assertTrue(entry.get("bg_style"))

    def test_build_hybrid_prompt_block_iq_puzzle(self):
        block = build_hybrid_prompt_block("iq_puzzle_optical_riddle", lang="tr")
        self.assertIn("HİBRİT NİŞ FORMAT", block)
        self.assertIn("7 saniye", block.lower())

    def test_enrich_plan_with_hybrid_did_you_know(self):
        plan = {
            "title": "Bunu biliyor muydunuz 3 akıl almaz biyoloji gerçeği hap bilgi",
            "scenes": [{"search_queries": ["biology"], "duration": 3.0}],
        }
        out = enrich_plan_with_hybrid(plan, plan["title"], "9_five_facts")
        self.assertEqual(out.get("hybrid_niche"), "did_you_know_facts")

    def test_topic_intelligence_hybrid_signals_306_318(self):
        cases = [
            ("optik bilmece zeka sorusu gizlenmiş 7 saniye bul", "iq_puzzle_optical_riddle"),
            ("e-ticaret girişim minimalist tipografi siyah beyaz", "entrepreneur_minimal_typography"),
            ("guinness dünya rekoru spiker heyecan inanılmaz", "world_records_sports_commentary"),
            ("bunu biliyor muydunuz did you know 3 biyoloji gerçeği", "did_you_know_facts"),
            ("sokak röportaj mikro tek soru el mikrofonu", "micro_street_interview"),
            ("oppenheimer vizyona girdi felsefe trend analiz", "seasonal_trend_reaction"),
            ("komik kedi meme nietzsche felsefe absürd", "absurdist_philosophy_meme"),
        ]
        for topic, expected_hybrid in cases:
            with self.subTest(topic=topic[:40]):
                intel = resolve_topic_intelligence(topic, "1_news_flash")
                self.assertEqual(intel.get("hybrid_niche"), expected_hybrid)

    def test_item_310_ab_test_subtitle_styles(self):
        variants = generate_ab_test_variants("Karadelikler")
        self.assertEqual(len(variants), 3)
        for v in variants:
            self.assertIn("subtitle_style_a", v)
            self.assertIn("subtitle_style_b", v)
            self.assertEqual(v["subtitle_style_a"], "karaoke_bold_neon")
            self.assertEqual(v["subtitle_style_b"], "minimal_white_shadow")

    def test_item_311_comment_to_video_hook(self):
        hook = create_comment_to_video_hook("Hocam bunu açıklar mısınız?", "Ahmet")
        self.assertIn("visual_overlay_text", hook)
        self.assertIn("Ahmet", hook["visual_overlay_text"])
        self.assertIn("spoken_hook", hook)

    def test_item_312_poll_to_shorts_workflow(self):
        poll = generate_community_poll("Uzay")
        self.assertEqual(poll["shorts_production_delay_hours"], 2)
        brief = plan_shorts_from_poll_winner("Uzay", poll["options"][0])
        self.assertEqual(brief["source"], "community_poll_winner")
        self.assertIn("Siz oyladınız", brief["hook"])

    def test_item_313_related_video_bridge(self):
        bridge = generate_related_video_bridge(
            "Kısa özet",
            "https://youtube.com/watch?v=abc123",
            "Tam belgesel",
        )
        self.assertEqual(bridge["related_video_url"], "https://youtube.com/watch?v=abc123")
        self.assertIn("Tam video", bridge["description_append"])
        self.assertIn("studio_upload_note", bridge)

    def test_item_314_episodic_series_hook(self):
        series = generate_episodic_series_hook("Dünyanın En Gizemli 10 Yeri", episode_num=1)
        self.assertIn("Bölüm 1", series["title"])

    def test_item_315_live_stream_loop_command(self):
        cmd = generate_live_stream_loop_command("out.mp4", "stream_key")
        self.assertIn("stream_loop", cmd)
        self.assertIn("stream_key", cmd)

    def test_item_316_micro_interview_dialogue(self):
        dialogue = generate_micro_interview_dialogue("Hayatın anlamı nedir?")
        self.assertEqual(len(dialogue["responses"]), 3)
        self.assertIn("Sokakta", dialogue["interviewer_hook"])

    def test_item_317_seasonal_trend_hook(self):
        hook = generate_seasonal_trend_hook("Oppenheimer", angle="felsefe")
        self.assertIn("Oppenheimer", hook["title"])
        self.assertEqual(hook["angle"], "felsefe")

    def test_item_318_absurdist_hybrid_niche(self):
        entry = get_hybrid_niche("absurdist_philosophy_meme")
        self.assertIn("Nietzsche", entry["hook_style"])

    def test_item_319_affiliate_pinned_cta(self):
        cta = generate_affiliate_pinned_cta("Atomik Alışkanlıklar", "https://amzn.to/test")
        self.assertIn("Şeffaf affiliate", cta["pinned_comment"])
        self.assertIn("Atomik Alışkanlıklar", cta["pinned_comment"])
        self.assertIn("#reklam", cta["affiliate_disclosure"])

    def test_item_320_niche_collision_engine(self):
        collision = collide_two_niches("stoic_cyberpunk", "mythology_ai_epic")
        self.assertIn("collision_id", collision)
        self.assertIn("system_prompt", collision)
        self.assertIn("stoic_cyberpunk_x_mythology_ai_epic", collision["collision_id"])


if __name__ == "__main__":
    unittest.main()
