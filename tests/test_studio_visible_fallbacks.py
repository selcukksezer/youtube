"""Studio dropdown, intro whoosh gate, local Piper fallback, public-apis snapshot."""
import os
import tempfile
import unittest
import wave
from unittest import mock

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


class TestStudioDropdownAndWhoosh(unittest.TestCase):
    def test_visual_dropdown_includes_minimax_h3_and_mixed(self):
        html = open(os.path.join(ROOT, "static", "index.html"), encoding="utf-8").read()
        select_at = html.find('id="select-visual-engine"')
        self.assertGreater(select_at, 0)
        block = html[select_at:select_at + 1200]
        for value in ("auto", "flux", "whiteboard", "minimax_h3", "mixed"):
            self.assertIn(f'value="{value}"', block)
        self.assertIn('id="btn-start-minimax-h3"', html)
        self.assertIn("http://127.0.0.1:8188", html)
        self.assertIn("start_comfy.bat", html)
        self.assertNotIn("speech-2.8-hd", html)
        js = open(os.path.join(ROOT, "static", "js", "render-monitor.js"), encoding="utf-8").read()
        self.assertIn("dropdownVal !== 'auto'", js)
        self.assertLess(
            js.find("dropdownVal !== 'auto'"),
            js.find("plan?.visual_mode"),
        )

    def test_woop_false_skips_hit(self):
        from director.audio_bus import apply_intro_whoosh_pref, master_audio_one_pass
        from director.schema import DirectorPlan

        html = open(os.path.join(ROOT, "static", "index.html"), encoding="utf-8").read()
        whoosh_at = html.find('id="chk-intro-whoosh"')
        self.assertGreater(whoosh_at, 0)
        tag = html[html.rfind("<input", 0, whoosh_at): html.find(">", whoosh_at) + 1]
        self.assertNotIn("checked", tag)

        manifest = apply_intro_whoosh_pref(
            {
                "item_112_whoosh_ding": True,
                "item_141_breaths": False,
                "item_146_compand": False,
                "item_147_deesser": False,
                "item_182_piano": False,
                "item_183_synth_bass": False,
                "item_188_crowd_ambience": False,
                "item_191_reverb_chamber": False,
            },
            False,
        )
        self.assertFalse(manifest["item_112_whoosh_ding"])
        self.assertFalse(manifest["item_191_reverb_chamber"])
        plan = DirectorPlan(title="t", niche_id="stoic", effect_manifest=manifest, scenes=[])
        prepend = mock.Mock(side_effect=AssertionError("whoosh hit"))
        with mock.patch(
            "voice_humanizer.voice_humanizer.apply_studio_eq_and_warmth",
            side_effect=lambda src, dst: src,
        ), mock.patch(
            "voice_humanizer.prepend_whoosh_ding_to_narration",
            prepend,
        ), mock.patch(
            "voice_humanizer.voice_humanizer.normalize_ebu_r128",
            side_effect=RuntimeError("stop after gate"),
        ):
            master_audio_one_pass("in.wav", plan, os.path.join(tempfile.gettempdir(), "out.wav"))
        prepend.assert_not_called()


class TestLocalTtsQuotaFallback(unittest.TestCase):
    def test_local_tts_invoked_when_gemini_429_and_edge_failed(self):
        import config
        import tts_engine

        calls = []

        def fake_local(text, output_path):
            calls.append(text)
            with wave.open(output_path, "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(b"\x00\x00" * 800)
            return True, "piper"

        out = os.path.join(tempfile.mkdtemp(prefix="local_tts_"), "out.wav")
        with mock.patch.object(config, "USE_GEMINI_TTS", True), \
                mock.patch.object(config, "GEMINI_API_KEY", "test-key"), \
                mock.patch.object(config, "TTS_VOICE", "tr-TR-AhmetNeural"), \
                mock.patch.object(config, "PREFER_AZURE_TTS", False), \
                mock.patch.object(config, "ELEVENLABS_API_KEY", ""), \
                mock.patch.object(config, "TTS_SACRED_CALM", False), \
                mock.patch(
                    "tts_engine._generate_gemini_narration",
                    side_effect=RuntimeError("Gemini TTS: HTTP 429"),
                ), \
                mock.patch(
                    "tts_engine._run_coro",
                    side_effect=RuntimeError("Edge failed"),
                ), \
                mock.patch("tts_engine.generate_local_offline_wav", side_effect=fake_local):
            wav, timings = tts_engine.generate_narration_with_timing("Merhaba dunya bu yerel yedek", out)
        self.assertTrue(calls)
        self.assertTrue(os.path.isfile(wav))
        self.assertGreaterEqual(len(timings), 1)

    def test_missing_piper_binary_logs_and_continues(self):
        import tts_engine

        with mock.patch("tts_engine._local_piper_binary", return_value=""):
            ok, msg = tts_engine.generate_local_offline_wav("merhaba", os.path.join(tempfile.gettempdir(), "missing.wav"))
        self.assertFalse(ok)
        self.assertIn("Continuing", msg)

    def test_default_voice_stays_edge_ahmet(self):
        from tts_voices import resolve_voice

        self.assertEqual(resolve_voice("tr", gender="male"), "tr-TR-AhmetNeural")
        self.assertEqual(resolve_voice("tr", voice_id="local:piper-tr"), "local:piper-tr")


class TestPublicApisStudioBlock(unittest.TestCase):
    def test_index_contains_public_api_block_and_snapshot_loads(self):
        html = open(os.path.join(ROOT, "static", "index.html"), encoding="utf-8").read()
        self.assertIn('id="public-apis-fallback"', html)
        self.assertIn("public-apis", html.lower())
        self.assertNotIn("speech-2.8-hd", html)
        from services.public_apis_catalog import load_offline_snapshot

        rows = load_offline_snapshot()
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(any(row.get("id") for row in rows))


if __name__ == "__main__":
    unittest.main()
