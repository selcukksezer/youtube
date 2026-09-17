"""
Unit tests for Section 2 Items 101 - 105:
101. Ses Hızı Dalgalanması (Audio Jitter %98 - %102)
102. BGM Beat-Syncing (Downbeat / Rhythm Grid Scene Synchronization)
103. Ekran Dışı Odak (Out-of-Focus Hook Reveal 0.35s)
104. Yapay Zeka Prompt Şablonlarını Sürekli Değiştirme (Prompt Template Rotation)
105. Affiliate Ürün Görsellerini Yeniden Boyutlandırma (3D Drop Shadow Tilt Mockup)
"""
import unittest
import os
import tempfile
from moviepy.editor import ColorClip

from voice_humanizer import VoiceHumanizer
from bgm_manager import detect_bgm_bpm_and_beats, align_scenes_to_bgm_beats
from effects_engine import apply_out_of_focus_reveal, apply_affiliate_3d_mockup
from scene_generator import get_rotated_system_prompt
import config

class TestSection2Items101To105(unittest.TestCase):

    def test_item_101_audio_jitter(self):
        """Item 101: Applies audio speed jitter between 98% and 102% using FFmpeg atempo."""
        # Create a small silent test wav
        import wave, struct
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_in:
            in_path = tmp_in.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_out:
            out_path = tmp_out.name

        try:
            with wave.open(in_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                # 0.5s tone
                wf.writeframes(b"\x00\x00" * 22050)

            jittered = VoiceHumanizer.apply_audio_jitter(in_path, out_path, min_speed=0.98, max_speed=1.02)
            self.assertTrue(os.path.exists(jittered))
            self.assertGreater(os.path.getsize(jittered), 100)
        finally:
            if os.path.exists(in_path): os.remove(in_path)
            if os.path.exists(out_path): os.remove(out_path)

    def test_item_102_bgm_beat_syncing(self):
        """Item 102: Detects BPM rhythm grid and aligns scene cut durations to closest beats."""
        beats = detect_bgm_bpm_and_beats("lofi_study_beat.mp3", duration=30.0, default_bpm=85.0)
        self.assertGreater(len(beats), 10)
        self.assertTrue(all(beats[i] < beats[i+1] for i in range(len(beats)-1)))

        # Test scene alignment
        scenes = [
            {"scene_number": 1, "duration": 5.0, "narration": "Sahne 1"},
            {"scene_number": 2, "duration": 6.0, "narration": "Sahne 2"},
            {"scene_number": 3, "duration": 5.5, "narration": "Sahne 3"}
        ]
        aligned = align_scenes_to_bgm_beats(scenes, "energetic_phonk.mp3")
        self.assertEqual(len(aligned), 3)
        for sc in aligned:
            self.assertTrue(sc.get("beat_synced", False), "Scenes should be marked beat_synced")
            self.assertGreaterEqual(sc["duration"], 2.5)

    def test_item_103_out_of_focus_hook_reveal(self):
        """Item 103: Starts with soft out-of-focus blur and reveals crisp visual in 0.35s."""
        clip = ColorClip(size=(720, 1280), color=(30, 60, 90), duration=1.0)
        try:
            revealed = apply_out_of_focus_reveal(clip, blur_duration=0.35)
            self.assertEqual(revealed.size, (720, 1280))
            frame = revealed.get_frame(0.1)
            self.assertEqual(frame.shape, (1280, 720, 3))
        finally:
            clip.close()

    def test_item_104_prompt_template_rotation(self):
        """Item 104: Rotates system prompt phrasing every 20 videos to break structural fingerprint."""
        prompt_1 = get_rotated_system_prompt(base_lang="tr")
        self.assertIn("YouTube Shorts", prompt_1)
        self.assertTrue(isinstance(prompt_1, str))

    def test_item_105_affiliate_3d_mockup(self):
        """Item 105: Embeds product image into tilted 3D card with drop shadow."""
        mockup = apply_affiliate_3d_mockup(None, target_w=720, target_h=1280, tilt_angle=-5.0)
        self.assertEqual(mockup.size, (720, 1280))
        frame = mockup.get_frame(0.0)
        self.assertEqual(frame.shape, (1280, 720, 3))

if __name__ == "__main__":
    unittest.main()
