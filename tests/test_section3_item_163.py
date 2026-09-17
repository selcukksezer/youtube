"""Telephone lo-fi voice filter test for roadmap item 163."""
import os
import tempfile
import unittest
import wave

from voice_humanizer import VoiceHumanizer


class TestSection3Item163(unittest.TestCase):
    def test_telephone_filter_generates_filtered_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = os.path.join(directory, "input.wav")
            output_path = os.path.join(directory, "telephone.wav")
            with wave.open(input_path, "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(44100)
                audio.writeframes(b"\0\0" * 4410)
            self.assertEqual(VoiceHumanizer.apply_telephone_filter(input_path, output_path), output_path)
            self.assertGreater(os.path.getsize(output_path), 44)


if __name__ == "__main__":
    unittest.main()