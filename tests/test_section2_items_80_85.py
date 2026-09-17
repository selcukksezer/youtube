"""
Unit tests for Section 2 Items 80 - 85:
80. Yapay Zeka Etiketi Politikası (Altered/Synthetic Media Policy)
81. Özgün Katma Değer İlkesi (Transformative Value - 3 Arguments)
82. Metin İçi Görsel Çıkartmalar (Stickers/Badges/Counters)
83. Açıklamada Kaynak Belirtme (Investigative Research Source Reference)
84. FFmpeg Unsharp Filtresi (unsharp=5:5:0.8:5:5:0.0)
85. Ses Frekans Spektrumu Kaydırma (120Hz & 4000Hz Notch Filter)
"""
import unittest
import os
import wave
import struct
from moviepy.editor import ColorClip

from youtube_uploader import evaluate_synthetic_content_policy
from scene_generator import verify_or_enrich_transformative_value
from effects_engine import overlay_graphic_badge, get_unsharp_filter
from viral_seo_agent import append_research_source_reference
from voice_humanizer import VoiceHumanizer
import config

class TestSection2Items80To85(unittest.TestCase):

    def test_item_80_synthetic_policy(self):
        """Item 80: Do not label AI content unless face cloning or news manipulation."""
        # Standard educational/storytelling short
        eval_standard = evaluate_synthetic_content_policy(has_realistic_human_clone=False, is_news_manipulation=False)
        self.assertFalse(eval_standard["apply_synthetic_label"])
        self.assertFalse(eval_standard["self_declared_altered"])
        self.assertIn("kapalı", eval_standard["reason"].lower())

        # Face cloned or news manipulation
        eval_deepfake = evaluate_synthetic_content_policy(has_realistic_human_clone=True, is_news_manipulation=False)
        self.assertTrue(eval_deepfake["apply_synthetic_label"])

    def test_item_81_transformative_value(self):
        """Item 81: Script must contain at least 3 distinct arguments for fair use immunity."""
        scenes = [
            {"scene_number": 1, "narration": "Antik Roma'da stoacılık bir felsefeden çok bir kalkandı."},
            {"scene_number": 2, "narration": "Çoğu insan kaderi bir ceza sanır, oysa kader bir fırsattır."},
            {"scene_number": 3, "narration": "Marcus Aurelius'un dediği gibi, engeller yolun kendisidir."}
        ]
        audit = verify_or_enrich_transformative_value(scenes, topic="Stoacılık")
        self.assertTrue(audit["transformative_compliant"])
        self.assertEqual(audit["argument_count"], 3)
        self.assertEqual(len(audit["breakdown"]), 3)

    def test_item_82_graphic_badge_overlay(self):
        """Item 82: Dynamic pill badges / counter stickers composite cleanly on video."""
        clip = ColorClip(size=(720, 1280), color=(30, 30, 45), duration=1.0)
        try:
            badged = overlay_graphic_badge(clip, label="#1 KURAL", icon="💡")
            self.assertEqual(badged.size, (720, 1280))
            frame = badged.get_frame(0.2)
            self.assertEqual(frame.shape, (1280, 720, 3))
        finally:
            clip.close()

    def test_item_83_research_source_reference(self):
        """Item 83: YouTube description automatically contains investigative research reference."""
        base_desc = "Marcus Aurelius ve Stoacı felsefe hakkında ilham verici video. #shorts"
        enriched = append_research_source_reference(base_desc, keyword="Marcus Aurelius", source_name="Meditationes Arşiv Kayıtları")
        self.assertIn("📌 Kaynak & Araştırma:", enriched)
        self.assertIn("Meditationes Arşiv Kayıtları", enriched)
        self.assertIn("Fair Use", enriched)

        # Idempotent check (doesn't duplicate if already present)
        double_enriched = append_research_source_reference(enriched, keyword="Marcus Aurelius")
        self.assertEqual(enriched, double_enriched)

    def test_item_84_unsharp_filter(self):
        """Item 84: Generates unsharp=5:5:0.8:5:5:0.0 filter with micro-jitter."""
        filt = get_unsharp_filter(luma_matrix=5, luma_amount=0.8)
        self.assertTrue(filt.startswith("unsharp=5:5:"))
        self.assertTrue(filt.endswith(":5:5:0.0"))
        # Check value is close to 0.8
        val_str = filt.split(":")[2]
        val = float(val_str)
        self.assertAlmostEqual(val, 0.80, delta=0.08)

    def test_item_85_spectral_notch_filter(self):
        """Item 85: Applies 120Hz & 4000Hz notch filters to audio."""
        tmp_dir = os.path.join(config.BASE_DIR, "output", "test_tmp_notch")
        os.makedirs(tmp_dir, exist_ok=True)
        in_wav = os.path.join(tmp_dir, "test_tone.wav")
        out_wav = os.path.join(tmp_dir, "test_notch.wav")

        try:
            # Create a 0.5s test wav file
            sr = 44100
            with wave.open(in_wav, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                # 0.5s silence/tone
                samples = bytearray(struct.pack("<h", 500) * int(sr * 0.5))
                wf.writeframes(samples)

            res_path = VoiceHumanizer.apply_spectral_notch_filter(in_wav, out_wav, f1=120.0, f2=4000.0)
            self.assertTrue(os.path.exists(res_path))
            self.assertGreater(os.path.getsize(res_path), 100)
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
