"""Completion Sprint Batch 4 — B6 SEO operator pack, B8 checklist, B2 enrichment, B1 upload sim."""
import inspect
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import config
from copyright_risk import scenes_need_fair_use_enforcement
from scenes.enrichment import apply_alternate_topic_angle, enrich_plan_scenes, enforce_fair_use_2_5s_rule
from scenes.prompts import advance_prompt_rotation, get_rotated_system_prompt
from viral_seo_agent import export_seo_operator_pack, build_studio_metadata_fields
from proof_archiver import ProofArchiver
from moviepy.editor import ColorClip


class TestCompletionSprintBatch4Wiring(unittest.TestCase):
    def test_b6_export_seo_operator_pack(self):
        pack = export_seo_operator_pack("Stoacılık", title="Stoacılık Sırları", lang="tr")
        self.assertEqual(pack["pack_type"], "seo_operator_pack")
        self.assertIn("seo", pack)
        self.assertIn("studio_metadata", pack)
        self.assertIn("studio_engagement", pack)
        self.assertIn("pinned_comment", pack["seo"])
        self.assertIn("location_tag", pack["studio_metadata"])
        self.assertIn("tags_csv", pack["studio_metadata"])
        self.assertTrue(pack["manual_studio_only"])

    def test_b6_studio_metadata_fields(self):
        fields = build_studio_metadata_fields("Finans", tags=["shorts", "finans"], lang="tr")
        self.assertIn("354", fields["item_refs"])
        self.assertEqual(fields["audience_language"], "Turkish")

    def test_b6_operator_pack_api_route(self):
        router_path = os.path.join(config.BASE_DIR, "routers", "system_router.py")
        with open(router_path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("/api/seo/operator-pack", src)
        self.assertIn("export_seo_operator_pack", src)

    def test_b8_channel_health_checklist(self):
        data = ProofArchiver.build_actionable_channel_health_checklist(
            total_videos=5, niche="Stoacılık", topic="Disiplin", lang="tr"
        )
        self.assertGreaterEqual(data["actionable_count"], 15)
        items = {c["item"] for c in data["checklist"]}
        self.assertIn(468, items)
        self.assertIn(472, items)
        self.assertIn(486, items)
        self.assertIn(499, items)
        self.assertGreaterEqual(len(data["deferred_manual"]), 3)

    def test_item_472_appeal_operator_workflow(self):
        wf = ProofArchiver.build_appeal_video_operator_workflow(
            "TestChannel", "Demo Video", channel_url="https://youtube.com/@test"
        )
        self.assertIn("YouTube Partner Program", wf["script"])
        self.assertEqual(wf["script_language"], "en")
        self.assertIn(473, wf["manual_only"])
        self.assertIn(474, wf["manual_only"])
        self.assertGreaterEqual(len(wf["checklist"]), 4)

    def test_b8_checklist_api_route(self):
        router_path = os.path.join(config.BASE_DIR, "routers", "system_router.py")
        with open(router_path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("/api/channel-health/checklist", src)
        self.assertIn("build_actionable_channel_health_checklist", src)

    def test_item_96_fair_use_wired_in_enrichment(self):
        scenes = [{"duration": 6.0, "search_queries": ["movie clip official trailer"], "narration": "Test"}]
        self.assertTrue(scenes_need_fair_use_enforcement(scenes))
        plan = enrich_plan_scenes({"scenes": scenes})
        self.assertTrue(plan.get("fair_use_2_5s_enforced"))
        for sc in plan["scenes"]:
            self.assertLessEqual(sc["duration"], 2.5)

    def test_item_96_enforce_splits_copyrighted(self):
        scenes = [{"duration": 6.0, "is_copyrighted": True, "narration": "Film"}]
        out = enforce_fair_use_2_5s_rule(scenes, is_copyrighted_source=True)
        self.assertGreater(len(out), 1)

    def test_item_117_alternate_topic_angle(self):
        plan = {"scenes": [{"narration": "Orijinal", "duration": 3.0}], "title": "Test"}
        alt = apply_alternate_topic_angle(plan, "Stoacılık", lang="tr")
        self.assertTrue(alt.get("alternate_angle"))
        self.assertEqual(alt.get("item_117"), "counter_argument_dialectic")
        self.assertGreater(len(alt.get("scenes", [])), 0)

    def test_item_104_prompt_rotation_every_20(self):
        advance_prompt_rotation(steps=0)
        p0 = get_rotated_system_prompt(base_lang="tr", force_variant=0)
        p1 = get_rotated_system_prompt(base_lang="tr", force_variant=1)
        self.assertNotEqual(p0[:80], p1[:80])

    def test_item_123_gradient_in_composer(self):
        from video_composer import compose_video
        src = inspect.getsource(compose_video)
        self.assertIn("apply_fluid_gradient_background", src)
        self.assertIn("Item 123", src)

    def test_item_124_micro_resolution_in_composer(self):
        from video_composer import compose_video
        src = inspect.getsource(compose_video)
        self.assertIn("apply_micro_resolution_crop", src)
        self.assertIn("Item 124", src)

    def test_item_123_gradient_applies(self):
        from effects_engine import apply_fluid_gradient_background
        clip = ColorClip(size=(720, 1280), color=(20, 20, 40), duration=1.5).set_fps(30)
        prev = getattr(config, "RENDER_SAFE_MODE", True)
        config.RENDER_SAFE_MODE = False
        try:
            out = apply_fluid_gradient_background(clip)
            self.assertEqual(out.size, (720, 1280))
        finally:
            config.RENDER_SAFE_MODE = prev
            clip.close()
            if hasattr(out, "close"):
                out.close()

    def test_b1_upload_sim_fields(self):
        from channel_bot.uploader import execute_studio_upload

        mock_engine = MagicMock()
        mock_engine.apply_video_size_variation.return_value = {"success": True, "delta_kb": 12, "new_size_mb": 5.1, "new_unique_md5": "abc123"}
        mock_engine.get_residential_network_conditions.return_value = {"upload_mbps": 25, "latency_ms": 18}
        mock_engine.verify_login_location_consistency.return_value = {"info": "OK"}
        mock_engine.verify_profile_cache_integrity.return_value = {"storage_size_kb": 512}
        mock_engine.test_tls_ja3_fingerprint.return_value = {"library": "curl_cffi", "ja3_hash": "abc" * 5}
        mock_engine.generate_pre_upload_interaction_plan.return_value = {
            "shorts_count": 2,
            "steps": [{"index": 1, "watch_duration_seconds": 30, "like_video": True, "leave_comment": False, "comment_text": ""}],
            "selected_comment": "Harika!",
        }
        mock_engine.calculate_natural_session_duration.return_value = {"target_session_minutes": 5}
        mock_engine.calculate_upload_jitter.return_value = {"time_str": "18:22", "jitter_applied_minutes": 4}
        mock_engine.generate_typing_delays.return_value = [0.1] * 10
        mock_engine.STANDARD_MACOS_FONTS = ["Arial"]

        with patch("channel_bot.uploader.database") as mock_db, \
             patch("channel_bot.uploader.os.path.exists", return_value=True), \
             patch("channel_bot.uploader.os.utime"):
            mock_db.get_managed_channel.return_value = {
                "id": 1,
                "handle": "@test",
                "profile_id": "prof1",
                "niche": "Stoic",
                "proxy_url": None,
                "viewport": "1920x1080",
            }
            mock_db.update_managed_channel_status.return_value = None
            result = execute_studio_upload(
                mock_engine, "@test", "/tmp/fake.mp4", "Test #Shorts"
            )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("api_flag_bypassed"))
        self.assertEqual(result.get("pre_upload_shorts_watched"), 2)
        self.assertIn("upload_bandwidth_mbps", result)
        self.assertIn("target_session_minutes", result)

    def test_composer_uses_export_seo_operator_pack(self):
        from video_composer import compose_video
        src = inspect.getsource(compose_video)
        self.assertIn("export_seo_operator_pack", src)


if __name__ == "__main__":
    unittest.main()
