"""
Unit tests for Section 7: Bot Infrastructure, Technical Architectures & Hardware Acceleration (Items 411 - 465).
"""
import unittest
import os
import tempfile
from system_resilience import (
    get_hardware_accelerated_encoder,
    CircuitBreaker,
    verify_stock_video_integrity,
    clean_ai_system_preamble,
    smart_split_narration_for_shorts,
    guard_subtitle_audio_drift,
    verify_render_output_sanity,
    sanitize_filename_and_title,
    get_system_health_status
)


class TestSection7SystemResilience(unittest.TestCase):
    def test_item_411_hardware_acceleration(self):
        encoder, args = get_hardware_accelerated_encoder()
        self.assertIn(encoder, ["h264_videotoolbox", "h264_nvenc", "libx264"])
        self.assertIsInstance(args, list)

    def test_item_416_circuit_breaker(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.2)
        service = "test_gemini"

        # Initially closed
        self.assertTrue(cb.can_execute(service))
        self.assertEqual(cb._get_service(service)["state"], CircuitBreaker.STATE_CLOSED)

        # Record 2 failures -> still closed
        cb.record_failure(service, "429 Rate Limit")
        cb.record_failure(service, "429 Rate Limit")
        self.assertTrue(cb.can_execute(service))

        # 3rd failure -> trips to OPEN
        cb.record_failure(service, "429 Rate Limit")
        self.assertFalse(cb.can_execute(service))
        self.assertEqual(cb._get_service(service)["state"], CircuitBreaker.STATE_OPEN)

        # After timeout -> HALF_OPEN
        import time
        time.sleep(0.25)
        self.assertTrue(cb.can_execute(service))
        self.assertEqual(cb._get_service(service)["state"], CircuitBreaker.STATE_HALF_OPEN)

        # Success in HALF_OPEN resets to CLOSED
        cb.record_success(service)
        self.assertEqual(cb._get_service(service)["state"], CircuitBreaker.STATE_CLOSED)

    def test_item_428_clean_ai_system_preamble(self):
        raw = "İşte hazırladığım senaryo:\n\nMarcus Aurelius antik Roma imparatorudur."
        cleaned = clean_ai_system_preamble(raw)
        self.assertEqual(cleaned, "Marcus Aurelius antik Roma imparatorudur.")

        raw_en = "Sure, here's the script:\n```json\n{\"title\": \"test\"}\n```"
        cleaned_en = clean_ai_system_preamble(raw_en)
        self.assertNotIn("here's the script", cleaned_en.lower())
        self.assertNotIn("```", cleaned_en)

    def test_item_430_smart_split_for_shorts(self):
        long_text = "Marcus Aurelius bilge bir imparatordur. Hayatını felsefeye adamıştır. " * 30
        shortened, was_split = smart_split_narration_for_shorts(long_text, max_words=50)
        self.assertTrue(was_split)
        self.assertLessEqual(len(shortened.split()), 55)
        self.assertTrue(shortened.endswith(".") or shortened.endswith("..."))

    def test_item_451_guard_subtitle_audio_drift(self):
        timings = [
            {"word": "Marcus", "start": 0.0, "end": 1.5},
            {"word": "Aurelius", "start": 1.5, "end": 3.0},
            {"word": "Roma", "start": 3.0, "end": 6.5},   # Exceeds 5.0s audio
            {"word": "Gereksiz", "start": 6.5, "end": 7.0} # Fully beyond audio
        ]
        guarded = guard_subtitle_audio_drift(timings, audio_duration=5.0)
        self.assertEqual(len(guarded), 3)
        self.assertEqual(guarded[-1]["end"], 5.0)

    def test_item_452_verify_render_output_sanity(self):
        # Non-existent
        res = verify_render_output_sanity("/non/existent/path.mp4")
        self.assertFalse(res["valid"])

        # Tiny file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"tiny-test")
            temp_path = f.name

        try:
            res_tiny = verify_render_output_sanity(temp_path, min_size_bytes=500_000)
            self.assertFalse(res_tiny["valid"])
            self.assertIn("çok küçük", res_tiny["error"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_item_461_sanitize_filename_and_title(self):
        bad_title = "Marcus Aurelius: En Büyük 3 Sırrı / Neden? * <Doğru mu?> |"
        clean = sanitize_filename_and_title(bad_title)
        self.assertNotIn("/", clean)
        self.assertNotIn(":", clean)
        self.assertNotIn("*", clean)
        self.assertNotIn("?", clean)
        self.assertNotIn("<", clean)
        self.assertNotIn(">", clean)
        self.assertNotIn("|", clean)

    def test_item_464_system_health(self):
        health = get_system_health_status()
        self.assertIn("status", health)
        self.assertIn("ffmpeg_installed", health)
        self.assertIn("hardware_acceleration", health)
        self.assertIn("disk", health)
        self.assertIn("api_providers", health)


if __name__ == "__main__":
    unittest.main()
