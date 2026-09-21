"""Azure TTS + channel B-roll archive unit tests (no network)."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock


class AzureTtsUnitTests(unittest.TestCase):
    def test_not_configured_without_keys(self):
        import azure_tts

        with mock.patch("config.AZURE_SPEECH_KEY", ""), mock.patch(
            "config.AZURE_SPEECH_REGION", ""
        ):
            self.assertFalse(azure_tts.is_configured())

    def test_ssml_escapes_and_locale(self):
        import azure_tts

        ssml = azure_tts._build_ssml("a & b <c>", "tr-TR-AhmetNeural", rate="+18%")
        self.assertIn("tr-TR", ssml)
        self.assertIn("a &amp; b &lt;c&gt;", ssml)
        self.assertIn("tr-TR-AhmetNeural", ssml)

    def test_active_provider_prefers_azure_label(self):
        import tts_engine

        with mock.patch("config.TTS_VOICE", "tr-TR-AhmetNeural"), mock.patch(
            "config.ELEVENLABS_API_KEY", ""
        ), mock.patch("config.PREFER_AZURE_TTS", True), mock.patch(
            "config.USE_GEMINI_TTS", False
        ), mock.patch("config.USE_PIPER_TTS", False), mock.patch(
            "azure_tts.is_configured", return_value=True
        ):
            label = tts_engine.active_tts_provider()
        self.assertIn("Azure Speech", label)


class ChannelBrollTests(unittest.TestCase):
    def test_promote_and_hit(self):
        from channel_broll import promote_clip, try_archive_hit

        with tempfile.TemporaryDirectory() as tmp:
            assets = os.path.join(tmp, "assets", "channels", "test_ch")
            os.makedirs(assets, exist_ok=True)
            # Fake channel_paths
            with mock.patch(
                "config.channel_paths",
                return_value={"slug": "test_ch", "assets_dir": assets, "output_dir": tmp},
            ):
                src = os.path.join(tmp, "src_clip.mp4")
                with open(src, "wb") as f:
                    f.write(b"fake-mp4-bytes-for-sha1-test-001")
                promoted = promote_clip(
                    "test_ch",
                    "13_mystery",
                    src,
                    queries=["dark hallway mystery", "candle light"],
                    source="pexels",
                    source_id="99",
                )
                self.assertTrue(promoted and os.path.isfile(promoted))

                proj = os.path.join(tmp, "proj")
                os.makedirs(proj, exist_ok=True)
                hit = try_archive_hit(
                    "test_ch",
                    "13_mystery",
                    ["mystery hallway dark"],
                    proj,
                    scene_index=0,
                    rotation_window=0,
                )
                self.assertTrue(hit and os.path.isfile(hit))
                self.assertIn("broll_", os.path.basename(hit))

    def test_no_channel_skips(self):
        from channel_broll import try_archive_hit

        self.assertIsNone(
            try_archive_hit(None, "x", ["a"], "/tmp", 0)
        )


if __name__ == "__main__":
    unittest.main()
