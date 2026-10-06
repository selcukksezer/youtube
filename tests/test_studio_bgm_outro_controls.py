"""Studio BGM checkbox and outro checkbox reach the render path."""
import os
import tempfile
import unittest
from unittest import mock

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


class TestBgmMuteSwitch(unittest.TestCase):
    def test_checkbox_off_mutes_even_when_a_track_is_chosen(self):
        from bgm_manager import request_mutes_bgm

        self.assertTrue(request_mutes_bgm("ambient.mp3", False))
        self.assertTrue(request_mutes_bgm("none", None))
        self.assertTrue(request_mutes_bgm("none", True))
        self.assertFalse(request_mutes_bgm("", True))
        self.assertFalse(request_mutes_bgm("ambient.mp3", True))
        self.assertFalse(request_mutes_bgm("", None))

    def test_director_master_skips_autopick_when_bgm_disabled(self):
        from director.audio_bus import master_audio_one_pass
        from director.schema import DirectorPlan

        manifest = {
            "item_112_whoosh_ding": False,
            "item_141_breaths": False,
            "item_146_compand": False,
            "item_147_deesser": False,
            "item_182_piano": False,
            "item_183_synth_bass": False,
            "item_188_crowd_ambience": False,
            "item_191_reverb_chamber": False,
            "item_195_epic_trailer_voice": False,
        }
        plan = DirectorPlan(title="t", niche_id="news", effect_manifest=manifest, scenes=[])
        out = os.path.join(tempfile.gettempdir(), "bgm_mute_out.wav")
        match = mock.Mock(side_effect=AssertionError("autopick"))
        mix = mock.Mock(side_effect=AssertionError("mix"))
        with mock.patch(
            "voice_humanizer.voice_humanizer.apply_studio_eq_and_warmth",
            side_effect=lambda src, dst: src,
        ), mock.patch(
            "voice_humanizer.voice_humanizer.normalize_ebu_r128",
            side_effect=lambda src, dst, **kwargs: src,
        ), mock.patch("bgm_manager.match_bgm_track_to_niche", match), mock.patch(
            "bgm_manager.mix_narration_and_bgm", mix
        ):
            master_audio_one_pass("in.wav", plan, out, bgm_track="", allow_bgm=False)
        match.assert_not_called()
        mix.assert_not_called()


class TestOutroSwitch(unittest.TestCase):
    def test_prompt_drops_mandatory_cta_when_outro_off(self):
        from niche_templates import get_niche_prompt

        on = get_niche_prompt("6_stoic_philosophy", "Ofke", language="tr", enable_outro=True)
        off = get_niche_prompt("6_stoic_philosophy", "Ofke", language="tr", enable_outro=False)
        self.assertIn("NİŞE ÖZEL OUTRO / CTA (son sahne - ZORUNLU)", on)
        self.assertIn("OUTRO KAPALI", off)
        self.assertNotIn("NİŞE ÖZEL OUTRO / CTA (son sahne - ZORUNLU)", off)

    def test_retention_leaves_last_fact_when_outro_off(self):
        from scenes.retention_hooks import apply_retention_hooks_to_plan

        last = "Roma bu kuralı senato oylamasıyla yürürlüğe koydu."
        plan = {
            "scenes": [
                {"narration": "İlk sahne burada uzun bir cümle kurar.", "duration": 4.0},
                {"narration": last, "duration": 4.0},
            ]
        }
        out = apply_retention_hooks_to_plan(
            plan, "Roma", lang="tr", variation_attempt=0, enable_outro=False
        )
        self.assertEqual(out["scenes"][-1]["narration"], last)
        self.assertEqual(out["retention_metadata"]["ending_bridge"], "")
        self.assertFalse(out["enable_outro"])


class TestStudioPayloadWiring(unittest.TestCase):
    def test_render_and_script_payloads_send_the_checkboxes(self):
        render_js = open(os.path.join(ROOT, "static", "js", "render-monitor.js"), encoding="utf-8").read()
        studio_js = open(os.path.join(ROOT, "static", "js", "studio.js"), encoding="utf-8").read()
        audio_js = open(os.path.join(ROOT, "static", "js", "audio-media.js"), encoding="utf-8").read()
        self.assertIn("enable_bgm:", render_js)
        self.assertIn("enable_outro:", render_js)
        self.assertIn("chk-enable-bgm", render_js)
        self.assertIn("enable_outro:", studio_js)
        self.assertIn("bindTwinCheckbox('chk-enable-bgm'", audio_js)
        self.assertIn("bindTwinCheckbox('chk-enable-outro'", audio_js)
        self.assertIn("bindTwinCheckbox('chk-intro-whoosh'", audio_js)


if __name__ == "__main__":
    unittest.main()
