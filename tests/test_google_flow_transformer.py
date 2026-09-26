"""
Tests for Google Flow Transformer Service:
1. Extraction of viral DNA from video metadata.
2. Storyboard generation with Veo camera movements & volumetric lighting prompts.
3. Clipboard text generation for direct copy-paste into Google Flow / labs.google.
"""

import unittest
from unittest.mock import patch, MagicMock
from services.google_flow_transformer import GoogleFlowTransformer, transform_youtube_url_to_flow


class TestGoogleFlowTransformer(unittest.TestCase):

    def setUp(self):
        self.transformer = GoogleFlowTransformer()

    def test_generate_flow_storyboard(self):
        mock_dna = {
            "video_id": "test1234",
            "url": "https://youtube.com/shorts/test1234",
            "title": "3 İnanılmaz Pratik Mutfak Aleti",
            "duration": 55,
            "view_count": 2500000,
            "transcript": "Gündelik hayatınızı kolaylaştıracak 3 harika mutfak aleti. İlki poşet kapatıcı.",
        }

        with patch("services.google_flow_transformer.generate_scenes") as mock_gen:
            mock_gen.return_value = {
                "title": "3 İnanılmaz Pratik Mutfak Aleti",
                "scenes": [
                    {
                        "scene_index": 0,
                        "narration": "Gündelik hayatınızı inanılmaz kolaylaştıracak 3 harika ürün var.",
                        "scene_description": "smart kitchen gadgets on modern countertop",
                        "duration": 5.0,
                    },
                    {
                        "scene_index": 1,
                        "narration": "İlk ürün açık kalan poşetleri anında mühürleyen alet.",
                        "scene_description": "mini bag sealer sealing snack bag",
                        "duration": 5.5,
                    },
                ]
            }

            storyboard = self.transformer.generate_flow_storyboard(mock_dna, target_niche="12_amazon_affiliate")
            self.assertEqual(len(storyboard["scenes"]), 2)
            s1 = storyboard["scenes"][0]
            self.assertIn("flow_prompt", s1)
            self.assertIn("camera_motion", s1)
            self.assertIn("9:16", s1["flow_prompt"])
            self.assertIn("negative_prompt", s1)

            # Test clipboard export
            text = self.transformer.export_flow_clipboard_text(storyboard)
            self.assertIn("GOOGLE FLOW", text)
            self.assertIn("SAHNE 1", text)


if __name__ == "__main__":
    unittest.main()
