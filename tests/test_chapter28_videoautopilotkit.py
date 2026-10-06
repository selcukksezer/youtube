"""
Tests for Chapter 28.20 / Section 2.2 (Madde 20):
reference_repos2/video-autopilot-kit evolution:
- compliance/license_governance.py: AssetLicenseGovernance, fail-closed audit, credits manifest
- director/retention_engine.py: RetentionEngine, 3-second stimulus pacing rule
- services/workflow_retry.py: WorkflowRenderRetry, attempt isolation and fallback
"""

import os
import tempfile
import unittest

from compliance.license_governance import (
    AssetLicenseGovernance,
    GLOBAL_LICENSE_GOVERNANCE,
)
from director.retention_engine import (
    RetentionEngine,
    GLOBAL_RETENTION_ENGINE,
)
from services.workflow_retry import (
    WorkflowRenderRetry,
    RenderAttemptError,
)


class TestVideoAutopilotKitLicenseGovernance(unittest.TestCase):
    def test_evaluate_license_fail_closed(self):
        # Approved licenses
        ok, _ = AssetLicenseGovernance.evaluate_license("Pexels-License", "pexels.com/123")
        self.assertTrue(ok)

        ok, _ = AssetLicenseGovernance.evaluate_license("CC0-1.0", "archive.org")
        self.assertTrue(ok)

        # Blocked: missing provenance
        ok, reason = AssetLicenseGovernance.evaluate_license("CC0-1.0", "unknown")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", reason)

        # Blocked: non-commercial / all rights reserved
        ok, reason = AssetLicenseGovernance.evaluate_license("all-rights-reserved", "creator_site")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", reason)

    def test_audit_all_assets_and_credits_manifest(self):
        assets = [
            {"asset_id": "vid1", "path": "v1.mp4", "license": "Pexels-License", "provenance": "pexels", "creator_attribution": "Jane Doe"},
            {"asset_id": "aud1", "path": "a1.mp3", "license": "CC-BY-4.0", "provenance": "freesound", "creator_attribution": "John Smith"},
        ]
        audit = AssetLicenseGovernance.audit_all_assets_fail_closed(assets)
        self.assertTrue(audit["success"])
        self.assertEqual(audit["approved_count"], 2)

        manifest = AssetLicenseGovernance.compile_credits_manifest(assets)
        self.assertEqual(manifest["policy"], "FAIL_CLOSED_ZERO_COPYRIGHT_RISK")
        self.assertEqual(len(manifest["attributions"]), 2)


class TestVideoAutopilotKitRetentionEngine(unittest.TestCase):
    def test_retention_audit_and_stimulus_injection(self):
        scenes = [
            {"duration": 2.5, "has_motion": True},
            {"duration": 5.0, "has_motion": False},  # Stale: > 3.0s without motion
            {"duration": 2.0, "has_motion": True},
        ]
        report = RetentionEngine.audit_timeline(scenes)
        self.assertEqual(report["total_duration"], 9.5)
        self.assertIn(1, report["stale_scene_indices"])
        self.assertFalse(report["meets_mrbeast_pacing_standard"])

        # Injected stimuli includes promise_cold_open and midpoint break
        stim_types = [s["event_type"] for s in report["injected_stimuli"]]
        self.assertIn("promise_cold_open", stim_types)
        self.assertIn("camera_zoom_in", stim_types)


class TestVideoAutopilotKitWorkflowRetry(unittest.TestCase):
    def test_attempt_path_generation(self):
        self.assertEqual(WorkflowRenderRetry.get_attempt_path("out.mp4", 1), "out.mp4")
        self.assertEqual(WorkflowRenderRetry.get_attempt_path("out.mp4", 2), "out.attempt-002.mp4")

    def test_retry_success_after_failure(self):
        t_fd, target_file = tempfile.mkstemp(suffix=".mp4")
        os.close(t_fd)
        os.unlink(target_file)  # Ensure it doesn't exist yet

        calls = []

        def dummy_render(out_path: str, use_gpu: bool) -> bool:
            calls.append((out_path, use_gpu))
            if len(calls) == 1:
                # Attempt 1 fails
                return False
            # Attempt 2 succeeds
            with open(out_path, "wb") as f:
                f.write(b"RENDERED_VIDEO_DATA")
            return True

        result = WorkflowRenderRetry.execute_render_with_retry(
            render_fn=dummy_render,
            output_path=target_file,
            max_attempts=3,
            initial_backoff=0.01,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["attempts_used"], 2)
        self.assertTrue(os.path.exists(target_file))
        self.assertEqual(os.path.getsize(target_file), len(b"RENDERED_VIDEO_DATA"))

        # Cleanup
        if os.path.exists(target_file):
            os.unlink(target_file)


if __name__ == "__main__":
    unittest.main()
