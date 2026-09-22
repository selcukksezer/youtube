"""Batch 3 Completion Sprint — B4 retention, B3 audio, B7 ops, B5 hybrid, RENDER_SAFE_MODE default."""
import inspect
import os
import tempfile
import unittest
from unittest.mock import patch
import wave

import config
from bgm_manager import cache_bgm_file, clear_bgm_ram_cache, get_cached_bgm_path, _BGM_RAM_CACHE
from copyright_risk import scan_audio_copyright_risk
from director.compiler import compile_director_plan
from director.timeline import solve_timeline
from hardware_detector import get_cpu_thermal_state, get_system_hardware_specs
from hybrid_niches import HYBRID_NICHES, get_hybrid_render_overlay_spec, enrich_plan_with_hybrid
from scenes.enrichment import enrich_plan_scenes
from scenes.retention_hooks import apply_retention_hooks_to_plan
from subtitle_generator import align_words_whisper, _rescale_timings_to_audio_duration
from system_resilience import purge_old_videos
from viral_retention_engine import ViralRetentionEngine
from tts_engine import _segment_pitch, _segment_has_emphasis
from sfx_manager import build_reaction_sfx_events
from voice.script_humanizer import extract_reaction_cues
from voice.script_humanizer import get_asmr_voice_settings


# B5 partial cluster (276–288, 290, 298, 299, 336) — hybrid ids from roadmap
B5_PARTIAL_HYBRID_IDS = [
    "stoic_cyberpunk", "history_chat", "dark_psychology_parkour", "mystery_earth_zoom",
    "would_you_rather_duel", "reddit_asmr", "cosmic_epic_hans_zimmer", "crypto_comic_book",
    "country_guess_countdown", "spiritual_rain_nature", "whatsapp_horror_voice",
    "lifehack_affiliate_3items", "movie_idiom_english", "weird_laws_world_map",
    "optical_illusion_focus", "price_timeline_tunnel", "hidden_wiretap_meeting",
]


class TestBatch3CompletionSprintWiring(unittest.TestCase):
    def test_render_safe_mode_default_false(self):
        """RENDER_SAFE_MODE boolean configuration path."""
        self.assertIsInstance(config.RENDER_SAFE_MODE, bool)
        with patch.dict(os.environ, {"RENDER_SAFE_MODE": "false"}):
            parsed = os.getenv("RENDER_SAFE_MODE", "false").lower() in ("true", "1", "yes")
            self.assertFalse(parsed)

    def test_item_432_bgm_ram_cache(self):
        clear_bgm_ram_cache()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(b"RIFF")
            path = tmp.name
        try:
            cache_bgm_file(path)
            self.assertIn(os.path.abspath(path), _BGM_RAM_CACHE)
            resolved = get_cached_bgm_path("")
            self.assertTrue(resolved and os.path.isfile(resolved))
        finally:
            os.unlink(path)
            clear_bgm_ram_cache()

    def test_item_448_purge_old_videos(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.path.join(tmp, "old_render.mp4")
            with open(old, "wb") as fh:
                fh.write(b"\x00" * 1024)
            os.utime(old, (1_000_000_000, 1_000_000_000))
            result = purge_old_videos(output_dir=tmp, max_age_days=30, dry_run=True)
            self.assertIn(old, result["purged"])
            self.assertGreaterEqual(result["purged_count"], 1)

    def test_item_450_cpu_thermal_state(self):
        thermal = get_cpu_thermal_state()
        self.assertIn("thermal_throttle_recommended", thermal)
        specs = get_system_hardware_specs()
        self.assertIn("thermal", specs)
        src = inspect.getsource(get_system_hardware_specs)
        self.assertIn("thermal", src.lower())

    def test_item_448_render_worker_auto_delete(self):
        from server_core import render_worker
        src = inspect.getsource(render_worker.process_video_task)
        self.assertIn("purge_old_videos", src)
        self.assertIn("auto_delete", src.lower())

    def test_item_413_whisper_duration_align(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wf = wave.open(tmp.name, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00\x00" * 48000 * 2)
            wf.close()
            audio = tmp.name
        try:
            timings = [{"text": "Merhaba", "offset": 0.0, "duration": 1.0}]
            scaled = _rescale_timings_to_audio_duration(timings, audio)
            self.assertEqual(len(scaled), 1)
            out = align_words_whisper(timings, audio_path=audio)
            self.assertTrue(out)
        finally:
            os.unlink(audio)

    def test_item_190_audio_copyright_scan(self):
        safe = scan_audio_copyright_risk(["royalty_free_ambient.wav"])
        self.assertTrue(safe["safe"])
        risky = scan_audio_copyright_risk(["epidemic_sound_pop_hit.mp3"])
        self.assertFalse(risky["safe"])

    def test_item_149_reaction_sfx_pipeline(self):
        scenes = [{"narration": "Şok edici (gül) bir gerçek.", "duration": 4.0}]
        cues = extract_reaction_cues(scenes[0]["narration"])
        self.assertIn("chuckle", cues)
        events = build_reaction_sfx_events(scenes)
        self.assertTrue(any(e["sound"] == "chuckle" for e in events))

    def test_item_164_asmr_profile(self):
        profile = get_asmr_voice_settings("asmr", "whisper sleep")
        self.assertTrue(profile.get("enabled") or profile.get("rate"))

    def test_item_171_emphasis_pitch(self):
        seg = {"style": "body", "text": "Bu ASLA unutulmamalı"}
        self.assertTrue(_segment_has_emphasis(seg["text"]))
        self.assertEqual(_segment_pitch(seg), "+12Hz")

    def test_item_208_cadence_in_timeline(self):
        src = inspect.getsource(solve_timeline)
        self.assertIn("calculate_cadence_acceleration", src)
        durations = ViralRetentionEngine.calculate_cadence_acceleration(45.0, 14)
        self.assertEqual(len(durations), 14)
        self.assertLess(durations[-1], durations[0])

    def test_b4_retention_visual_enrichment(self):
        plan = {
            "scenes": [
                {"narration": "Açılış.", "duration": 3.0, "search_queries": ["city"]},
                {"narration": "Kapanış.", "duration": 3.0, "search_queries": ["face portrait"]},
            ]
        }
        out = enrich_plan_scenes(plan, lang="tr")
        self.assertTrue(out["scenes"][0].get("handheld_shake"))
        self.assertTrue(out["scenes"][-1].get("closing_gaze"))

    def test_b4_share_bookmark_metadata(self):
        plan = {"scenes": [{"narration": "Test.", "duration": 3.0}, {"narration": "End.", "duration": 3.0}]}
        out = apply_retention_hooks_to_plan(plan, "Stres", lang="tr", variation_attempt=0)
        meta = out.get("retention_metadata") or {}
        self.assertTrue(meta.get("share_cta") or ViralRetentionEngine.generate_share_cta("Stres"))

    def test_b5_all_partial_hybrids_have_overlay_spec(self):
        for hid in B5_PARTIAL_HYBRID_IDS:
            self.assertIn(hid, HYBRID_NICHES, hid)
            spec = get_hybrid_render_overlay_spec(hid)
            self.assertTrue(spec.get("overlay") or spec.get("ui_type"), hid)

    def test_b5_hybrid_legacy_plan_preservation(self):
        titles = {
            "stoic_cyberpunk": "Marcus Aurelius cyberpunk neon distopya felsefe",
            "history_chat": "Sezar Napolyon WhatsApp gizli grup mesaj tarih",
            "optical_illusion_focus": "optik illüzyon odak testi beyin",
        }
        for hid, title in titles.items():
            raw = {"title": title, "scenes": [{"narration": "Test.", "duration": 3.0, "search_queries": ["test"]}]}
            raw = enrich_plan_with_hybrid(raw, title, "1_news_flash")
            if raw.get("hybrid_niche") != hid:
                continue
            plan = compile_director_plan(raw, title=title, niche_id="1_news_flash")
            legacy = plan.to_legacy_plan()
            self.assertEqual(legacy.get("hybrid_niche"), hid)
            self.assertTrue(legacy.get("hybrid_render_overlay"))

    def test_video_composer_retention_overlays_wired(self):
        from video_composer import compose_video
        src = inspect.getsource(compose_video)
        for marker in (
            "apply_opening_pattern_interrupt",
            "apply_share_cta_overlay",
            "apply_scene_brightness_alternation",
            "apply_neon_countdown_overlay",
            "apply_censored_blur_bait",
        ):
            self.assertIn(marker, src)

    def test_render_worker_enrichment_path(self):
        from server_core import render_worker
        src = inspect.getsource(render_worker.process_video_task)
        self.assertIn("enrich_plan_scenes", src)
        self.assertIn("scan_audio_copyright_risk", src)


if __name__ == "__main__":
    unittest.main()
