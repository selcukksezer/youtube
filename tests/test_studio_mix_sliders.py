"""Studio duck, blast, and swell sliders reach the live BGM mix."""
import os
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


class TestStudioMixSliders(unittest.TestCase):
    def test_non_default_sliders_reach_mix_and_whoosh_off_silences_blast(self):
        from bgm_manager import (
            DUCK_SIDECHAIN,
            build_bgm_volume_filter,
            build_duck_sidechain,
            resolve_studio_audio_mix,
        )

        cfg = resolve_studio_audio_mix(
            duck_attack_ms=40,
            duck_release_ms=350,
            intro_blast=0.95,
            enable_intro_whoosh=True,
            outro_swell_sec=8,
            enable_outro=True,
            enable_outro_swell=True,
            allow_bgm=True,
        )
        self.assertEqual(cfg["duck_attack_ms"], 40.0)
        self.assertEqual(cfg["duck_release_ms"], 350.0)
        self.assertAlmostEqual(cfg["intro_blast"], 0.95)
        self.assertEqual(cfg["outro_swell_sec"], 8.0)

        chain = build_duck_sidechain(cfg["duck_attack_ms"], cfg["duck_release_ms"])
        self.assertIn("attack=40", chain)
        self.assertIn("release=350", chain)
        self.assertNotEqual(chain, DUCK_SIDECHAIN)

        bed = build_bgm_volume_filter(
            0.12,
            intro_blast=cfg["intro_blast"],
            outro_swell_sec=cfg["outro_swell_sec"],
            duration_sec=30.0,
        )
        self.assertIn("0.9500", bed)
        self.assertIn("8.0000", bed)

        silent = resolve_studio_audio_mix(
            intro_blast=1.0,
            enable_intro_whoosh=False,
            outro_swell_sec=9,
            enable_outro=True,
            allow_bgm=True,
        )
        self.assertEqual(silent["intro_blast"], 0.0)
        quiet_bed = build_bgm_volume_filter(0.12, intro_blast=silent["intro_blast"], outro_swell_sec=0.0)
        self.assertEqual(quiet_bed, "volume=0.120")
        self.assertNotIn("eval", quiet_bed)

    def test_html_defaults_keep_the_current_sidechain(self):
        from bgm_manager import DUCK_SIDECHAIN, build_bgm_volume_filter, build_duck_sidechain, resolve_studio_audio_mix

        cfg = resolve_studio_audio_mix()
        self.assertEqual(build_duck_sidechain(cfg["duck_attack_ms"], cfg["duck_release_ms"]), DUCK_SIDECHAIN)
        self.assertEqual(cfg["intro_blast"], 0.0)
        self.assertEqual(cfg["outro_swell_sec"], 5.0)
        self.assertEqual(build_bgm_volume_filter(0.12, intro_blast=0.0, outro_swell_sec=0.0, duration_sec=30.0), "volume=0.120")

        no_music = resolve_studio_audio_mix(outro_swell_sec=8, allow_bgm=False)
        self.assertEqual(no_music["outro_swell_sec"], 0.0)
        no_outro = resolve_studio_audio_mix(outro_swell_sec=8, enable_outro=False)
        self.assertEqual(no_outro["outro_swell_sec"], 0.0)

    def test_render_payload_reads_the_slider_ids(self):
        js = open(os.path.join(ROOT, "static", "js", "render-monitor.js"), encoding="utf-8").read()
        for element_id in (
            "range-duck-attack",
            "range-duck-release",
            "range-bgm-blast",
            "range-outro-swell-sec",
        ):
            self.assertIn(element_id, js)
        self.assertIn("duck_attack_ms:", js)
        self.assertIn("duck_release_ms:", js)
        self.assertIn("intro_blast:", js)
        self.assertIn("outro_swell_sec:", js)


if __name__ == "__main__":
    unittest.main()
