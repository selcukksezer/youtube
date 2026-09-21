"""
Tests for R10 100-rules P0/P1 implementations (2026-09-21 batch).
Source: r10_shorts_fikirleri_ve_bot_ozellikleri.md
"""
import os
import tempfile
import unittest

import numpy as np
from moviepy.editor import ColorClip


class TestRules100P0Batch(unittest.TestCase):
    def test_r10_59_92_thumbnail_contrast_score(self):
        from effects.overlays import score_frame_thumbnail_quality, select_best_thumbnail_timestamp

        dark = np.zeros((64, 64, 3), dtype=np.uint8)
        bright = np.full((64, 64, 3), 200, dtype=np.uint8)
        contrast = bright.copy()
        contrast[:32] = 30
        self.assertGreater(
            score_frame_thumbnail_quality(contrast),
            score_frame_thumbnail_quality(dark),
        )
        clip = ColorClip(size=(320, 560), color=(40, 180, 90), duration=2.0)
        path = tempfile.mktemp(suffix=".mp4")
        try:
            clip.write_videofile(path, fps=10, codec="libx264", audio=False, verbose=False, logger=None)
            t, score = select_best_thumbnail_timestamp(path, sample_times=[0.1, 0.5, 1.0])
            self.assertGreaterEqual(t, 0.0)
            self.assertGreaterEqual(score, 0.0)
        finally:
            clip.close()
            if os.path.exists(path):
                os.remove(path)

    def test_r10_75_chroma_key(self):
        from effects.filters import apply_chroma_key

        bg = ColorClip(size=(200, 360), color=(10, 20, 40), duration=0.4)
        fg = ColorClip(size=(200, 360), color=(0, 255, 0), duration=0.4)
        try:
            out = apply_chroma_key(fg, bg, key_rgb=(0, 255, 0), threshold=30.0)
            frame = out.get_frame(0.1)
            # Mostly background blue-ish after keying out green FG
            self.assertEqual(frame.shape[0], 360)
            self.assertLess(int(frame.mean()), 80)
            out.close()
        finally:
            bg.close()
            fg.close()

    def test_r10_79_crossfade_concat(self):
        from effects.motion import concatenate_with_scene_transitions

        a = ColorClip(size=(120, 200), color=(255, 0, 0), duration=0.5)
        b = ColorClip(size=(120, 200), color=(0, 0, 255), duration=0.5)
        try:
            out = concatenate_with_scene_transitions([a, b], transition="crossfade", fade_dur=0.15)
            self.assertIsNotNone(out)
            self.assertGreater(out.duration, 0.6)
            out.close()
        finally:
            a.close()
            b.close()

    def test_r10_87_trend_hybrid_bgm(self):
        from bgm_manager import list_trend_hybrid_profiles, select_trend_hybrid_bgm

        profiles = list_trend_hybrid_profiles()
        self.assertGreaterEqual(len(profiles), 3)
        pick = select_trend_hybrid_bgm(niche_id="8_crypto_market", topic="bitcoin")
        self.assertEqual(pick["rule"], "r10_87_trend_hybrid")
        self.assertIn("path", pick)
        self.assertTrue(pick["path"])

    def test_r10_97_live_quiz_pack(self):
        from growth_tactics import generate_live_quiz_room_pack

        pack = generate_live_quiz_room_pack("Antik Roma", question_count=4)
        self.assertEqual(pack["rule"], "r10_97_live_quiz")
        self.assertEqual(len(pack["questions"]), 4)
        self.assertIn("superchat_cta", pack)
        self.assertIn("ffmpeg", pack["ffmpeg_loop_hint"])

    def test_r10_73_dubbing_pack(self):
        from services.dubbing import build_dubbing_pack, apply_dubbing_to_plan

        scenes = [{"narration": "gizli gerçek burada", "duration": 3.0}]
        pack = build_dubbing_pack(scenes, source_lang="tr", target_lang="en", title="Test")
        self.assertEqual(pack["rule"], "r10_73_dubbing")
        self.assertEqual(pack["scene_count"], 1)
        self.assertTrue(pack["scenes"][0]["dubbed_narration"])
        plan = apply_dubbing_to_plan({"title": "gizli", "language": "tr", "scenes": scenes}, "en")
        self.assertEqual(plan["language"], "en")

    def test_r10_95_shopping_tags(self):
        from viral_seo_agent import attach_shopping_product_tags, generate_viral_seo_metadata

        seo = attach_shopping_product_tags({"affiliate_text": "link"}, "mutfak aleti")
        self.assertIn("shopping_product_tags", seo)
        self.assertGreaterEqual(len(seo["shopping_product_tags"]), 1)
        meta = generate_viral_seo_metadata("test ürün")
        self.assertIn("shopping_product_tags", meta)

    def test_r10_100_ops_dashboard(self):
        import database
        database.init_db()
        snap = database.get_ops_dashboard_snapshot()
        self.assertEqual(snap["rule"], "r10_100_ops_dashboard")
        self.assertIn("local_renders", snap)

    def test_r10_45_piper_helpers(self):
        from tts_engine import generate_piper_wav, _piper_binary

        # Without model/binary → clear failure (not a fake Done)
        ok, msg = generate_piper_wav("merhaba", tempfile.mktemp(suffix=".wav"))
        self.assertFalse(ok)
        self.assertTrue(isinstance(msg, str) and len(msg) > 3)
        self.assertIsInstance(_piper_binary(), str)

    def test_r10_61_74_intro_and_pop(self):
        from effects.overlays import generate_intro_hook_card, apply_keyword_pop_text

        card = generate_intro_hook_card(360, 640, "ŞOK GERÇEK", duration=0.8)
        self.assertIsNotNone(card)
        self.assertAlmostEqual(card.duration, 0.8, places=1)
        base = ColorClip(size=(360, 640), color=(20, 20, 30), duration=1.2)
        try:
            out = apply_keyword_pop_text(base, "DİKKAT", start=0.1, duration=0.5)
            self.assertGreaterEqual(out.duration, 1.0)
            out.close()
        finally:
            base.close()
            card.close()

    def test_r10_3_niche_split_profile(self):
        from niche_templates import get_niche_production_profile

        profile = get_niche_production_profile("3_split_gameplay")
        self.assertTrue(profile["production_rules"]["split_screen"])

    def test_r10_39_semantic_score_baseline(self):
        from director.visual_intent import semantic_relevance_score

        score = semantic_relevance_score(
            "roman marble statue columns dusk",
            "Marcus Aurelius statue in Rome",
        )
        self.assertGreater(score, 0.0)


if __name__ == "__main__":
    unittest.main()
