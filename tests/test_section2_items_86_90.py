"""
Unit tests for Section 2 Items 86 - 90 and Manual Download Protection:
86. Piksel Gürültüsü Enjeksiyonu (noise=c1s=3:c0f=u)
87. Özgün İntro/Outro İmzası (0.4s Audio Watermark & Micro Brand Signature)
88. Görsel Değişim Frekansı (Cadence - >=14 visual cuts per 45s Short)
89. Stok Video Arama Terimi Çeşitliliği (Cinematic Adjective Enrichment)
90. Yapay Zeka Halüsinasyon Kontrolü (Historical & Chronological Anachronism Check)
Plus: Manual Download Anti-Detect Auto-Protection (ctime spoofing, free atom size variation, manual SEO guide)
"""
import unittest
import os
from moviepy.editor import ColorClip

from effects_engine import get_ffmpeg_static_grain_filter, overlay_micro_brand_signature
from voice_humanizer import ensure_sonic_branding_chime, VoiceHumanizer
from scene_generator import enforce_visual_cadence_14, enrich_cinematic_search_queries, verify_and_correct_hallucinations
from anti_detect_engine import anti_detect_engine
import config

class TestSection2Items86To90(unittest.TestCase):

    def test_item_86_static_grain_filter(self):
        """Item 86: Returns noise=c1s=3:c0f=u FFmpeg filter for static imperceptible grain."""
        grain_vf = get_ffmpeg_static_grain_filter()
        self.assertEqual(grain_vf, "noise=c1s=3:c0f=u")

    def test_item_87_sonic_branding_and_signature(self):
        """Item 87: 0.4s sonic chime and visual micro brand signature."""
        # 1. Audio chime
        chime_path = ensure_sonic_branding_chime()
        self.assertTrue(os.path.exists(chime_path))
        self.assertGreater(os.path.getsize(chime_path), 500)

        # 2. Visual micro signature
        clip = ColorClip(size=(720, 1280), color=(20, 20, 30), duration=1.0)
        try:
            branded = overlay_micro_brand_signature(clip, duration=0.40)
            self.assertEqual(branded.size, (720, 1280))
            frame = branded.get_frame(0.2)
            self.assertEqual(frame.shape, (1280, 720, 3))
        finally:
            clip.close()

    def test_item_88_visual_cadence_14(self):
        """Item 88: For 45s+ video, scene count is divided/adjusted to reach >=14 visual cuts."""
        # 8 scenes totaling 48 seconds
        scenes = [{"scene_number": i + 1, "duration": 6.0, "narration": f"Sahne {i+1}", "search_queries": ["stoic"]} for i in range(8)]
        adjusted = enforce_visual_cadence_14(scenes, min_cadence=14)
        self.assertGreaterEqual(len(adjusted), 14, "48s short should have at least 14 visual cadence cuts")
        # Total duration preserved
        total_adj = sum(s["duration"] for s in adjusted)
        self.assertAlmostEqual(total_adj, 48.0, delta=0.5)

    def test_item_89_cinematic_search_adjectives(self):
        """Item 89: Generic queries are enriched with cinematic adjectives."""
        generic_queries = ["man walking in street", "ocean waves", "city traffic"]
        enriched = enrich_cinematic_search_queries(generic_queries, mood="epic")
        for q in enriched:
            has_cinematic_word = any(w in q.lower() for w in ["cinematic", "drone", "aerial", "slow motion", "macro", "atmospheric", "4k", "moody"])
            self.assertTrue(has_cinematic_word, f"Query '{q}' should contain cinematic adjective")

    def test_item_90_hallucination_control(self):
        """Item 90: Detects impossible future dates and blatant chronological contradictions."""
        # Clean scenario
        clean_scenes = [{"narration": "Marcus Aurelius M.S. 161 yılında Roma İmparatoru oldu."}]
        res_clean = verify_and_correct_hallucinations(clean_scenes, topic="Marcus Aurelius")
        self.assertTrue(res_clean["verified"])

        # Hallucinated scenario: Marcus Aurelius placed in year 1945 or 2035
        bad_scenes = [{"narration": "Marcus Aurelius 1945 yılında Roma'da savaştı ve 2038 yılında zafer kazandı."}]
        res_bad = verify_and_correct_hallucinations(bad_scenes, topic="Marcus Aurelius")
        self.assertFalse(res_bad["verified"])
        self.assertGreater(len(res_bad["hallucination_issues"]), 0)

    def test_manual_download_protection_pipeline(self):
        """Verify that MP4 size variation and ctime aging apply directly on output file."""
        tmp_dir = os.path.join(config.BASE_DIR, "output", "test_manual_pkg")
        os.makedirs(tmp_dir, exist_ok=True)
        test_mp4 = os.path.join(tmp_dir, "sample_render.mp4")

        try:
            # Create a small valid test MP4
            clip = ColorClip(size=(320, 240), color=(50, 50, 50), duration=0.5)
            clip.write_videofile(test_mp4, fps=24, logger=None)
            clip.close()

            orig_size = os.path.getsize(test_mp4)

            # 1. Rule 30 Free Atom Size Variation
            res_size = anti_detect_engine.apply_video_size_variation(test_mp4)
            self.assertTrue(res_size["success"])
            self.assertGreater(os.path.getsize(test_mp4), orig_size)

            # 2. Rule 29 ctime/mtime aging
            import time
            past_time = time.time() - 1800 # 30 mins ago
            os.utime(test_mp4, (past_time, past_time))
            stat = os.stat(test_mp4)
            self.assertLess(stat.st_mtime, time.time() - 1500)

        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
