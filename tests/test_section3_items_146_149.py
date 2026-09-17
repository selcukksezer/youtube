"""Tests for roadmap audio items 146-149."""
import unittest

from voice_humanizer import VoiceHumanizer


class TestSection3Items146to149(unittest.TestCase):
    def test_item_148_speech_rhythm_uses_hook_body_and_question_rates(self):
        segments = VoiceHumanizer.build_speech_rhythm_segments(
            "Bunu hemen bilmelisin! Asıl gerçek şimdi başlıyor. Sence neden böyle?"
        )
        self.assertEqual([segment["style"] for segment in segments], ["hook", "body", "question"])
        self.assertEqual(segments[0]["rate"], "+10%")
        self.assertEqual(segments[2]["rate"], "-5%")

    def test_item_149_reaction_directions_are_extracted_not_spoken(self):
        text = "Gerçek ortaya çıktı. (hafifçe güler) Buna inanabiliyor musun? (iç çeker)"
        self.assertEqual(VoiceHumanizer.extract_reaction_cues(text), ["chuckle", "sigh"])
        spoken = " ".join(segment["text"] for segment in VoiceHumanizer.build_speech_rhythm_segments(text))
        self.assertNotIn("hafifçe güler", spoken)
        self.assertNotIn("iç çeker", spoken)


if __name__ == "__main__":
    unittest.main()