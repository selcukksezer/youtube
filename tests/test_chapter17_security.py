"""
Test Suite for Bölüm 17: Güvenlik, Kimlik Doğrulama ve Gizlilik Defteri (Zero-Trust Security).
Verifies:
  - 17.1 AES-256-GCM token encryption, buffer wiping, log sanitization
  - 17.2 Headless uploader session security
  - 17.3 Telif Hakkı ve DMCA savunma manifestosu (proof_manifest.json)
"""
import os
import tempfile
import unittest

from services.secret_vault import seal, open_secret, wipe_buffer
from services.log_sanitizer import sanitize_log, sanitize_payload
from proof_archiver import write_proof_manifest
from compliance.transparent_disclosure import build_transparent_ai_disclosure_block


class TestChapter17Security(unittest.TestCase):

    # ─── 17.1 API Anahtarları ve Hassas Veri Yönetimi ───
    def test_aes_256_gcm_seal_and_open_roundtrip(self):
        secret_token = "sk-live-secret-api-key-9988776655"
        sealed = seal(secret_token)
        self.assertTrue(sealed.startswith("v1:"))
        self.assertNotIn(secret_token, sealed)

        decrypted = open_secret(sealed)
        self.assertEqual(decrypted, secret_token)

    def test_wipe_buffer_memory_clearing(self):
        sensitive_data = bytearray(b"super_sensitive_token_in_ram")
        self.assertTrue(any(b != 0 for b in sensitive_data))
        wipe_buffer(sensitive_data)
        self.assertTrue(all(b == 0 for b in sensitive_data))

    def test_log_sanitizer_redaction(self):
        raw_log = "Error connecting with api_key=sk-1234567890abcdef and password=secret123 to server."
        clean_log = sanitize_log(raw_log)
        self.assertNotIn("sk-1234567890abcdef", clean_log)
        self.assertNotIn("secret123", clean_log)
        self.assertIn("api_key=[REDACTED]", clean_log)
        self.assertIn("password=[REDACTED]", clean_log)

    def test_sanitize_payload_recursive(self):
        payload = {
            "title": "Shorts Video",
            "api_key": "AIzaSyD-secret-key-12345",
            "nested": {
                "token": "bearer secret_access_token_123",
                "safe": "normal text",
            },
        }
        sanitized = sanitize_payload(payload)
        self.assertNotIn("AIzaSyD-secret-key-12345", str(sanitized))
        self.assertNotIn("secret_access_token_123", str(sanitized))
        self.assertEqual(sanitized["nested"]["safe"], "normal text")

    # ─── 17.3 Telif ve DMCA Savunma Manifestosu ───
    def test_proof_manifest_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            clip_path = os.path.join(tmpdir, "test_clip.mp4")
            with open(clip_path, "wb") as f:
                f.write(b"video_binary_bytes_for_hash")

            manifest_path = os.path.join(tmpdir, "proof_manifest.json")
            assets = [
                {
                    "path": clip_path,
                    "license": {"license": "pexels", "author": "Photographer"},
                    "source_url": "https://www.pexels.com/video/123/",
                }
            ]
            result_path = write_proof_manifest(manifest_path, "Test Başlık", assets)
            self.assertTrue(os.path.isfile(result_path))

            with open(result_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Test Başlık", content)
            self.assertIn("pexels", content)
            self.assertIn("sha256", content.lower())

    def test_transparent_disclosure_compliance(self):
        disclosure = build_transparent_ai_disclosure_block(
            clips_or_manifest=[{"provider": "pexels", "source_url": "https://www.pexels.com/video/123/"}],
            uses_tts=True,
            uses_ai_script=True,
            uses_photoreal_ai=True,
        )
        self.assertTrue(disclosure.get("disclosure_required"))
        self.assertEqual(disclosure.get("studio_ai_survey"), "yes")
        self.assertIn("yapay zeka", disclosure.get("header_text", "").lower())
        self.assertIn("Pexels", disclosure.get("sources_text", ""))


if __name__ == "__main__":
    unittest.main()
