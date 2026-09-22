import json
import os
import tempfile
import unittest

from compliance import ai_disclosure_block, export_output_package, publication_decision
from youtube_uploader import evaluate_synthetic_content_policy, upload_video_to_youtube
from channel_bot.uploader import execute_studio_upload


class TestManualPolicyPackage(unittest.TestCase):
    def test_disclosure_is_deterministic(self):
        self.assertEqual(ai_disclosure_block(uses_tts=True)["studio_ai_survey"], "no")
        disclosure = ai_disclosure_block(uses_photoreal_ai=True)
        self.assertEqual(disclosure["studio_ai_survey"], "yes")
        self.assertTrue(disclosure["disclosure_required"])
        self.assertIn("photorealistic_ai_visual", disclosure["reasons"])

    def test_output_package_writes_manifest_credits_and_checklist(self):
        with tempfile.TemporaryDirectory() as td:
            video = os.path.join(td, "render.mp4")
            with open(video, "wb") as fh:
                fh.write(b"rendered bytes")
            package_dir = os.path.join(td, "package")
            package = export_output_package(
                package_dir,
                video_path=video,
                title="Skyscraper sway",
                description="A sourced explanation #shorts",
                tags=["shorts", "science"],
                source_manifest={"version": 1, "clips": [{
                    "uid": "pexels:1", "source": "pexels", "asset_id": "1",
                    "title": "Tower", "url": "https://example.test/tower",
                    "license": {"license": "Pexels", "needs_attribution": True},
                }]},
                ai_disclosure=ai_disclosure_block(),
            )
            self.assertFalse(package["automatic_upload"])
            for filename in ("source_manifest.json", "visual_credits.json", "policy_snapshot.json",
                             "ai_disclosure.json", "manual_upload_checklist.json", "package_manifest.json",
                             "visual_credits.txt", "manual_upload_checklist.txt"):
                self.assertTrue(os.path.isfile(os.path.join(package_dir, filename)), filename)
            self.assertEqual(json.load(open(os.path.join(package_dir, "visual_credits.json"), encoding="utf-8"))["credits"][0]["provider"], "pexels")

    def test_upload_entry_points_are_manual_only(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as fh:
            fh.write(b"video")
            fh.flush()
            result = upload_video_to_youtube(fh.name, "Title", "Description", ["shorts"])
            self.assertFalse(result["uploaded"])
            self.assertEqual(result["action"], "MANUAL_UPLOAD_REQUIRED")
            studio = execute_studio_upload(None, "@channel", fh.name, "Title")
            self.assertFalse(studio["uploaded"])
            self.assertEqual(studio["action"], "MANUAL_UPLOAD_REQUIRED")

    def test_synthetic_policy_marks_realistic_ai(self):
        self.assertEqual(evaluate_synthetic_content_policy(uses_photoreal_ai=True)["studio_ai_survey"], "yes")
        self.assertEqual(evaluate_synthetic_content_policy()["studio_ai_survey"], "no")

    def test_publication_never_returns_auto_publish(self):
        decision = publication_decision(
            {"niche_id": "science"},
            {"hard_fail": False, "research": {"action": "ALLOW"}, "niche_gate": {"action": "OK"}},
            {"score": 95},
        )
        self.assertNotEqual(decision["action"], "AUTO_PUBLISH")
        self.assertFalse(decision["auto_publish"])


if __name__ == "__main__":
    unittest.main()
