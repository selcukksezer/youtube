"""
Comprehensive Smoke Test Suite for the 500-Item YouTube Shorts Engine
Tests all 8 phases:
- Anti-Detection & Jitter Engine (Items 1-70)
- Advanced Transformative Effects & pHash Breaking (Items 71-140)
- Voice Humanizer & Audio Engineering (Items 141-200)
- Viral Retention & Loop Matrix (Items 201-275)
- Hybrid Synergy Niches (Items 276-345)
- Proof of Effort Archiver & Appeal Generator (Items 466-500)
- Fast API REST Endpoints
"""

import os
import unittest
import json
from fastapi.testclient import TestClient

from anti_detect_engine import anti_detect_engine, BrowserProfile
from effects_engine import (
    scramble_mp4_hash, enforce_3s_broll_rule, get_hardware_acceleration_flags
)
from voice_humanizer import voice_humanizer, ensure_breath_sound
from sfx_manager import ensure_sfx_files
from viral_retention_engine import viral_retention_engine
from hybrid_niches import list_all_hybrid_niches, get_hybrid_niche
from proof_archiver import proof_archiver
from server import app


class Test500ItemEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # ══════════════════════════════════════════════════════════════
    # PHASE 1: Anti-Detection & Jitter (Items 1 - 70)
    # ══════════════════════════════════════════════════════════════
    def test_01_browser_profile_generation(self):
        profile = anti_detect_engine.generate_profile(channel_id="ch_test_101", lang="en")
        self.assertIsInstance(profile, BrowserProfile)
        self.assertIn("Macintosh", profile.user_agent)
        self.assertGreaterEqual(profile.viewport_width, 1440)
        self.assertIn("Apple", profile.webgl_renderer)
        self.assertGreater(profile.canvas_noise_seed, 0.0)

    def test_02_upload_jitter_calculation(self):
        jitter = anti_detect_engine.calculate_upload_jitter(target_hour=19, target_minute=10)
        self.assertIn("scheduled_hour", jitter)
        self.assertIn("time_str", jitter)
        self.assertGreater(jitter["jitter_applied_minutes"], 0)

    def test_03_typing_delays(self):
        delays = anti_detect_engine.generate_typing_delays("Marcus Aurelius")
        self.assertEqual(len(delays), len("Marcus Aurelius"))
        for d in delays:
            self.assertGreater(d, 0.0)

    def test_04_bezier_mouse_trajectory(self):
        path = anti_detect_engine.generate_bezier_mouse_path(100, 100, 800, 600, steps=20)
        self.assertEqual(len(path), 21)
        self.assertEqual(path[0], {"x": 100, "y": 100})
        self.assertEqual(path[-1], {"x": 800, "y": 600})

    def test_05_organic_warmup_plan(self):
        plan = anti_detect_engine.generate_warmup_session_plan("stoic")
        self.assertIn("steps", plan)
        self.assertGreaterEqual(plan["shorts_count"], 2)
        self.assertGreater(plan["estimated_total_session_minutes"], 0)

    # ══════════════════════════════════════════════════════════════
    # PHASE 2: Advanced Transformative Effects & pHash (Items 71 - 140)
    # ══════════════════════════════════════════════════════════════
    def test_06_scramble_mp4_hash(self):
        test_file = "tests/scratch_hash_test.bin"
        os.makedirs("tests", exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"HEADER_DATA_12345")
        
        initial_size = os.path.getsize(test_file)
        ok = scramble_mp4_hash(test_file)
        self.assertTrue(ok)
        new_size = os.path.getsize(test_file)
        self.assertEqual(new_size, initial_size + 16)
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_07_hardware_acceleration_flags(self):
        flags = get_hardware_acceleration_flags()
        self.assertIsInstance(flags, list)
        self.assertGreater(len(flags), 0)

    # ══════════════════════════════════════════════════════════════
    # PHASE 3: Voice Humanizer & Audio Engineering (Items 141 - 200)
    # ══════════════════════════════════════════════════════════════
    def test_08_breath_sound_synthesis(self):
        breath_path = ensure_breath_sound()
        self.assertTrue(os.path.exists(breath_path))
        self.assertGreater(os.path.getsize(breath_path), 500)

    def test_09_ssml_humanizer(self):
        ssml = voice_humanizer.humanize_script_ssml("Marcus Aurelius dedi ki, asla vazgeçmeyin.", is_hook=True)
        self.assertIn("<speak>", ssml)
        self.assertIn('prosody rate="+9%"', ssml)
        self.assertIn('<break time="', ssml)

    def test_10_extended_sfx_synthesizers(self):
        whoosh, pop, ding = ensure_sfx_files()
        self.assertTrue(os.path.exists(whoosh))
        self.assertTrue(os.path.exists(pop))
        self.assertTrue(os.path.exists(ding))
        sub_impact = os.path.join(os.path.dirname(whoosh), "sub_impact.wav")
        tape_stop = os.path.join(os.path.dirname(whoosh), "tape_stop.wav")
        self.assertTrue(os.path.exists(sub_impact))
        self.assertTrue(os.path.exists(tape_stop))

    # ══════════════════════════════════════════════════════════════
    # PHASE 4: Viral Retention & Loop Matrix (Items 201 - 275)
    # ══════════════════════════════════════════════════════════════
    def test_11_loop_formulas(self):
        self.assertEqual(len(viral_retention_engine.LOOP_FORMULAS), 12)
        f = viral_retention_engine.get_loop_formula("cause_and_effect")
        self.assertIn("ending_bridge", f)
        self.assertIn("hook_starter", f)

    def test_12_bionic_reading_formatter(self):
        words = ["Marcus", "Aurelius", "Stoacılık"]
        bionic = viral_retention_engine.format_bionic_text(words)
        self.assertEqual(len(bionic), 3)
        self.assertIn("<b>Mar</b>cus", bionic[0])

    def test_13_retention_score_audit(self):
        score = viral_retention_engine.calculate_retention_score(
            has_split_screen=True, has_anti_duplicate=True, has_karaoke=True,
            has_loop=True, audio_ducking=True
        )
        self.assertGreaterEqual(score["score"], 90)
        self.assertIn("🔥", score["tier"])

    # ══════════════════════════════════════════════════════════════
    # PHASE 5: Hybrid Niches (Items 276 - 345)
    # ══════════════════════════════════════════════════════════════
    def test_14_hybrid_niches_completeness(self):
        hybrids = list_all_hybrid_niches()
        self.assertGreaterEqual(len(hybrids), 20)
        keys = [h["id"] for h in hybrids]
        self.assertIn("stoic_cyberpunk", keys)
        self.assertIn("history_chat", keys)
        self.assertIn("dark_psychology_parkour", keys)
        self.assertIn("mystery_earth_zoom", keys)
        self.assertIn("would_you_rather_duel", keys)
        self.assertIn("reddit_asmr", keys)
        self.assertIn("weird_laws_world_map", keys)
        self.assertIn("ai_tools_screen", keys)

    # ══════════════════════════════════════════════════════════════
    # PHASE 6: Proof of Effort & Appeal Archiver (Items 466 - 500)
    # ══════════════════════════════════════════════════════════════
    def test_15_archive_video_proof(self):
        proof_path = proof_archiver.archive_video_proof(
            video_filename="test_video_101.mp4",
            title="3 Stoic Rules",
            niche="stoic_cyberpunk",
            script_text="Marcus Aurelius kuralları...",
            scenes=[{"text": "Sahne 1", "duration": 3.0}],
            render_params={"fps": 30, "resolution": "1080x1920"}
        )
        self.assertTrue(os.path.exists(proof_path))
        with open(proof_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["video_filename"], "test_video_101.mp4")
        self.assertEqual(data["niche"], "stoic_cyberpunk")
        if os.path.exists(proof_path):
            os.remove(proof_path)

    def test_16_appeal_script_generation(self):
        script = proof_archiver.generate_appeal_video_script(
            channel_name="Shorts AI Master",
            video_title="Marcus Aurelius'un Öfkeyi Yok Eden 3 Kuralı"
        )
        self.assertIn("Shorts AI Master", script)
        self.assertIn("YouTube Partner Program", script)
        self.assertIn("FAIR USE & VALUE TO THE COMMUNITY", script)

    # ══════════════════════════════════════════════════════════════
    # PHASE 7: REST API Endpoints Verification
    # ══════════════════════════════════════════════════════════════
    def test_17_api_anti_detect_profile(self):
        res = self.client.get("/api/anti_detect/profile?channel_id=unit_test")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["profile"]["profile_id"], "unit_test")

    def test_18_api_anti_detect_jitter(self):
        res = self.client.get("/api/anti_detect/jitter?hour=19&minute=0")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("jitter", data)

    def test_19_api_hybrid_niches(self):
        res = self.client.get("/api/hybrid_niches")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data["hybrid_niches"]), 20)

    def test_20_api_retention_formulas(self):
        res = self.client.get("/api/retention/formulas")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["formulas"]), 12)

    def test_21_api_proof_appeal_script(self):
        res = self.client.get("/api/proof/appeal_script?channel_name=TestChannel")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("TestChannel", data["script"])


if __name__ == "__main__":
    unittest.main()
