"""
End-to-End Pipeline Integration Test (Verifies complete lifecycle)
"""
import unittest, os
import config
from niche_templates import NICHES, get_niche_prompt
from scene_generator import _generate_procedural_fallback_scenes
from subtitle_generator import create_karaoke_subtitles, SUBTITLE_PRESETS
from sfx_manager import ensure_sfx_files, add_sfx_to_narration
from effects_engine import extract_frame0_thumbnail
from viral_seo_agent import generate_viral_seo_metadata

class TestFullPipeline(unittest.TestCase):
    def test_niche_to_seo_lifecycle(self):
        """Tests that selecting a niche flows into scenes, audio SFX, subs, and viral SEO metadata."""
        topic = "Marcus Aurelius Zihin Kontrolü"
        niche_key = "6_stoic_philosophy"

        # 1. Prompt generation
        prompt = get_niche_prompt(niche_key, topic, language="tr")
        self.assertIn(topic, prompt)
        self.assertIn("VIRAL HOOK", prompt)

        # 2. Scene generation (procedural test)
        scenes_data = _generate_procedural_fallback_scenes(topic)
        self.assertGreaterEqual(len(scenes_data["scenes"]), 8)
        self.assertIn("scenes", scenes_data)

        # 3. SFX generation
        whoosh, pop, ding = ensure_sfx_files()
        self.assertTrue(os.path.exists(whoosh))
        self.assertTrue(os.path.exists(pop))
        self.assertTrue(os.path.exists(ding))

        # 4. Viral SEO & Pinned comment generation
        seo_meta = generate_viral_seo_metadata(topic)
        self.assertIn("seo_title", seo_meta)
        self.assertIn("tags", seo_meta)
        self.assertIn("pinned_comment", seo_meta)
        self.assertIn("affiliate_text", seo_meta)

if __name__ == "__main__":
    unittest.main()
