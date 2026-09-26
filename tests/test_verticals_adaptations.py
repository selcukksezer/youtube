"""
Tests for Verticals v3 Adaptations:
1. Web Fact Researcher (Anti-hallucination DuckDuckGo gate)
2. High-CTR Thumbnail Generator (16:9 & 9:16 with gradient + drop shadow)
3. Pollinations Free AI Visual Engine (Flux + Ken Burns zoompan)
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from services.web_fact_researcher import extract_search_keywords, research_topic_facts, format_research_prompt_context
from services.thumbnail_generator import generate_thumbnail, extract_best_video_frame
from services.pollinations_ai_visual import clean_ai_prompt, PollinationsAIVisual


class TestVerticalsAdaptations(unittest.TestCase):

    def test_extract_search_keywords(self):
        topic = "Hayatınızı kolaylaştıracak ve Bunu neden daha önce almadım diyeceğiniz 3 ürün"
        kw = extract_search_keywords(topic)
        self.assertTrue(len(kw) > 0)
        # Filler words like 'Bunu neden daha önce almadım' should be stripped
        self.assertNotIn("almadım", kw.lower())

    @patch("requests.post")
    def test_research_topic_facts_mock(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html>
            <a class="result__snippet">Pratik el dikiş makinesi evde yırtıkları hızlıca onarır.</a>
            <a class="result__snippet">Manyetik kablo düzenleyici masadaki kablo karmaşasını çözer.</a>
        </html>
        """
        mock_post.return_value = mock_resp
        snippets = research_topic_facts("pratik ev aletleri", max_snippets=2)
        self.assertEqual(len(snippets), 2)
        self.assertIn("Pratik el dikiş makinesi", snippets[0])

    def test_clean_ai_prompt(self):
        prompt = "smart mini vacuum cleaner on modern desk"
        cleaned = clean_ai_prompt(prompt)
        self.assertIn("photorealistic", cleaned)
        self.assertIn("vertical 9:16", cleaned)

    def test_thumbnail_generator_916_and_169(self):
        out_916 = "output/test_verticals_thumb_916.jpg"
        out_169 = "output/test_verticals_thumb_169.jpg"
        try:
            p9 = generate_thumbnail("3 İNANILMAZ ÜRÜN!", out_916, aspect_ratio="9:16")
            p16 = generate_thumbnail("3 İNANILMAZ ÜRÜN!", out_169, aspect_ratio="16:9")
            self.assertTrue(os.path.exists(p9))
            self.assertTrue(os.path.getsize(p9) > 1000)
            self.assertTrue(os.path.exists(p16))
            self.assertTrue(os.path.getsize(p16) > 1000)
        finally:
            for p in (out_916, out_169):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass


if __name__ == "__main__":
    unittest.main()
