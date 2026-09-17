"""
Unit tests for Section 2: Items 71-79 (Reused Content & Visual Defense Pipeline)
r10_shorts_500_maddelik_nihai_yol_haritasi.md:
71. Perceptual Hashing (pHash) Modülasyonu
72. FFmpeg Renk Derecelendirme (Color Grading LUT / Jitter)
73. Mikro-Zoom (Ken Burns Jitter 1.00x - 1.04x)
74. Kare Hızı (FPS) Çeşitlendirmesi (29.97, 30.02 fps)
75. Görsel Katmanlama (Multi-Layer B-Roll %10 Opacity)
76. 3 Saniye Kuralı Kurgusu (3.2s Kesintisiz Sahne Limiti)
77. Yatay Kaynakları 9:16 Yaparken Akıllı Kırpma (%40 Gaussian Blur)
78. Görsel Aynalama (Horizontal Flip)
79. Hız Varyasyonu (Speed Ramp %97 / %103)
"""
import unittest
import numpy as np
from moviepy.editor import ColorClip
from effects_engine import (
    inject_pixel_noise,
    apply_color_grading_jitter,
    get_color_grading_ffmpeg_filter,
    get_phash_ffmpeg_noise_filter,
    apply_ken_burns,
    get_diversified_fps,
    apply_multi_layer_overlay,
    enforce_3s_broll_rule,
    apply_smart_crop,
    apply_horizontal_flip,
    apply_speed_ramp,
    apply_section2_anti_reused_pipeline
)

class TestSection2Transformations(unittest.TestCase):

    def test_item_71_phash_pixel_noise(self):
        """Item 71: 0.5% pixel noise breaks identical hash while preserving shape."""
        clip = ColorClip(size=(100, 100), color=(128, 128, 128), duration=0.5)
        try:
            noisy = inject_pixel_noise(clip, intensity=0.005)
            frame_orig = clip.get_frame(0.1)
            frame_noisy = noisy.get_frame(0.1)
            self.assertEqual(frame_noisy.shape, (100, 100, 3))
            # Check difference exists (noise was added)
            diff = np.abs(frame_noisy.astype(float) - frame_orig.astype(float))
            self.assertTrue(np.mean(diff) > 0.0, "Noise should alter pixel values")
            # Check noise is subtle (< 5.0 on average out of 255)
            self.assertTrue(np.mean(diff) < 5.0, "Noise must remain imperceptible (< 5.0 level)")
            # Verify FFmpeg filter string generator
            ff_noise = get_phash_ffmpeg_noise_filter()
            self.assertIn("noise=", ff_noise)
        finally:
            clip.close()

    def test_item_72_color_grading_jitter(self):
        """Item 72: Color grading jitter modulates gamma, contrast, saturation ±1.5%."""
        clip = ColorClip(size=(60, 60), color=(100, 150, 200), duration=0.5)
        try:
            jittered = apply_color_grading_jitter(clip, jitter_range=0.015)
            self.assertEqual(jittered.size, (60, 60))
            self.assertAlmostEqual(jittered.duration, 0.5, delta=0.05)
            # Verify FFmpeg eq filter generator
            eq_filter = get_color_grading_ffmpeg_filter(0.015)
            self.assertIn("eq=gamma=", eq_filter)
            self.assertIn("contrast=", eq_filter)
            self.assertIn("saturation=", eq_filter)
        finally:
            clip.close()

    def test_item_73_micro_zoom_ken_burns(self):
        """Item 73: Micro-zoom smooth progression 1.00x -> 1.04x."""
        clip = ColorClip(size=(100, 100), color=(50, 50, 50), duration=1.0)
        try:
            kb = apply_ken_burns(clip, zoom_start=1.00, zoom_end=1.04)
            self.assertEqual(kb.duration, 1.0)
            # Frame at t=0 has base size, frame at t=1.0 has 1.04x scaling
            f0 = kb.get_frame(0.0)
            self.assertEqual(f0.shape, (100, 100, 3))
            f1 = kb.get_frame(1.0)
            self.assertEqual(f1.shape, (100, 100, 3))
        finally:
            clip.close()

    def test_item_74_fps_diversification(self):
        """Item 74: Frame rates are diversified to 29.97, 30.02, 29.98 or 30.01."""
        seen_fps = set()
        for _ in range(50):
            fps = get_diversified_fps(30.0)
            self.assertIn(fps, [29.97, 30.02, 29.98, 30.01])
            seen_fps.add(fps)
        self.assertTrue(len(seen_fps) > 1, "Should generate diversified FPS values")

    def test_item_75_multi_layer_overlay(self):
        """Item 75: Multi-layer overlay at 10% opacity."""
        clip = ColorClip(size=(120, 120), color=(40, 40, 40), duration=0.5)
        try:
            layered = apply_multi_layer_overlay(clip, opacity=0.10)
            self.assertEqual(layered.size, (120, 120))
            self.assertEqual(layered.duration, 0.5)
        finally:
            clip.close()

    def test_item_76_3s_broll_rule(self):
        """Item 76: No clip stays static longer than 3.2 seconds."""
        # Test short clip remains untouched
        short_clip = ColorClip(size=(50, 50), color=(20, 20, 20), duration=2.5)
        try:
            res_short = enforce_3s_broll_rule(short_clip, max_duration=3.2)
            self.assertEqual(res_short.duration, 2.5)
        finally:
            short_clip.close()

        # Test long clip (5.0s) is split into <= 3.2s segments
        long_clip = ColorClip(size=(50, 50), color=(20, 20, 20), duration=5.0)
        try:
            res_long = enforce_3s_broll_rule(long_clip, max_duration=3.2)
            self.assertAlmostEqual(res_long.duration, 5.0, delta=0.05)
        finally:
            long_clip.close()

    def test_item_77_smart_crop_gaussian_blur(self):
        """Item 77: 16:9 horizontal clip is converted to 9:16 vertical with 40% blur background and zero black bars."""
        horizontal_clip = ColorClip(size=(1920, 1080), color=(80, 40, 120), duration=0.5)
        try:
            vertical_9_16 = apply_smart_crop(horizontal_clip, target_w=1080, target_h=1920, blur_intensity=0.40)
            self.assertEqual(vertical_9_16.size, (1080, 1920))
            self.assertEqual(vertical_9_16.duration, 0.5)
            # Frame check
            frame = vertical_9_16.get_frame(0.1)
            self.assertEqual(frame.shape, (1920, 1080, 3))
        finally:
            horizontal_clip.close()

    def test_item_78_horizontal_flip(self):
        """Item 78: Horizontally mirrors clip for Content ID evasion."""
        clip = ColorClip(size=(60, 60), color=(30, 40, 50), duration=0.5)
        try:
            flipped = apply_horizontal_flip(clip, force=True)
            self.assertEqual(flipped.size, (60, 60))
        finally:
            clip.close()

    def test_item_79_speed_ramp(self):
        """Item 79: Modulates clip playback speed to 97% or 103%."""
        clip = ColorClip(size=(50, 50), color=(30, 40, 50), duration=1.0)
        try:
            ramped_97 = apply_speed_ramp(clip, speed_factor=0.97)
            # Duration becomes 1.0 / 0.97 ~= 1.031s
            self.assertAlmostEqual(ramped_97.duration, 1.0 / 0.97, delta=0.05)

            ramped_103 = apply_speed_ramp(clip, speed_factor=1.03)
            # Duration becomes 1.0 / 1.03 ~= 0.971s
            self.assertAlmostEqual(ramped_103.duration, 1.0 / 1.03, delta=0.05)
        finally:
            clip.close()

    def test_full_section2_pipeline(self):
        """Verify full Section 2 anti-reused pipeline chaining all 9 items."""
        clip = ColorClip(size=(640, 360), color=(100, 120, 140), duration=4.0)
        try:
            processed = apply_section2_anti_reused_pipeline(
                clip, target_w=1080, target_h=1920,
                apply_flip=True, apply_speed=True, apply_3s=True,
                apply_kb=True, apply_noise=True, apply_grading=True, apply_layer=True
            )
            self.assertEqual(processed.size, (1080, 1920))
            frame = processed.get_frame(0.2)
            self.assertEqual(frame.shape, (1920, 1080, 3))
        finally:
            clip.close()

if __name__ == "__main__":
    unittest.main()
