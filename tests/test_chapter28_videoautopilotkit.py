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
)
from director.retention_engine import (
    RetentionEngine,
)
from director.quality_gate import pre_render_score
from director.schema import DirectorPlan, ScenePlan
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
        static_stimuli = [
            stimulus
            for stimulus in report["injected_stimuli"]
            if stimulus["global_timestamp"] > 0
        ]
        self.assertEqual(
            [stimulus["global_timestamp"] for stimulus in static_stimuli],
            [5.5],
        )

    def test_retention_stimuli_respect_camera_motion_and_three_second_intervals(self):
        moving_scene = RetentionEngine.audit_scene_retention(
            scene_index=1,
            duration=8.0,
            has_camera_motion=True,
        )
        self.assertEqual(moving_scene, [])

        static_scene = RetentionEngine.audit_scene_retention(
            scene_index=1,
            duration=8.0,
        )
        self.assertEqual(
            [stimulus.timestamp_sec for stimulus in static_scene],
            [3.0, 6.0],
        )
        self.assertTrue(all(stimulus.duration_sec <= 3.0 for stimulus in static_scene))

    def test_static_camera_direction_is_not_counted_as_motion(self):
        report = RetentionEngine.audit_timeline([
            {"duration": 7.0, "camera_direction": "static"},
        ])
        self.assertEqual(report["stale_scene_indices"], [0])
        self.assertEqual(
            [stimulus["global_timestamp"] for stimulus in report["injected_stimuli"]],
            [0.0, 3.0, 6.0],
        )

    def test_pre_render_report_surfaces_static_visual_gaps_as_advisories(self):
        narration = "The careful observer studies each visible detail before choosing what to do next."
        scenes = [
            ScenePlan(
                index=index,
                narration=narration,
                duration=7.0,
                beat_type="hook" if index == 0 else "conflict",
                scene_description=f"Careful observer studies a visible detail in setting {index}.",
                search_queries=["careful observer visible detail", "observer studies scene detail"],
                camera_direction="",
            )
            for index in range(6)
        ]
        plan = DirectorPlan(
            title="The careful observer",
            niche_id="1_news_flash",
            full_narration=" ".join(scene.narration for scene in scenes),
            scenes=scenes,
        )

        report = pre_render_score(plan)

        self.assertIn("static_visual_gap_over_3s:0", report["warnings"])
        self.assertIn(0, report["retention_audit"]["static_scene_indices"])
        self.assertEqual(report["retention_audit"]["max_static_duration_sec"], 3.0)
        self.assertNotIn("static_visual_gap_over_3s:0", report["issues"])

        scenes[0].camera_direction = "zoom_in"
        moving_report = pre_render_score(plan)
        self.assertNotIn("static_visual_gap_over_3s:0", moving_report["warnings"])


class TestVideoAutopilotKitWorkflowRetry(unittest.TestCase):
    def test_attempt_path_generation(self):
        self.assertEqual(WorkflowRenderRetry.get_attempt_path("out.mp4", 1), "out.attempt-001.mp4")
        self.assertEqual(WorkflowRenderRetry.get_attempt_path("out.mp4", 2), "out.attempt-002.mp4")

    def test_failed_retry_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = os.path.join(temp_dir, "existing.mp4")
            with open(target_file, "wb") as output:
                output.write(b"PREVIOUS_VALID_RENDER")

            calls = []

            def failed_render(out_path: str, use_gpu: bool) -> bool:
                calls.append((out_path, use_gpu))
                with open(out_path, "wb") as output:
                    output.write(b"PARTIAL_RENDER")
                return False

            with self.assertRaises(RenderAttemptError):
                WorkflowRenderRetry.execute_render_with_retry(
                    render_fn=failed_render,
                    output_path=target_file,
                    max_attempts=1,
                    initial_backoff=0,
                )

            self.assertEqual(
                calls,
                [(WorkflowRenderRetry.get_attempt_path(target_file, 1), False)],
            )
            with open(target_file, "rb") as output:
                self.assertEqual(output.read(), b"PREVIOUS_VALID_RENDER")

    def test_rejects_invalid_retry_limits(self):
        def unused_render(out_path: str, use_gpu: bool) -> bool:
            return bool(out_path) and use_gpu

        with self.assertRaises(ValueError):
            WorkflowRenderRetry.execute_render_with_retry(
                render_fn=unused_render,
                output_path="unused.mp4",
                max_attempts=0,
            )
        with self.assertRaises(ValueError):
            WorkflowRenderRetry.execute_render_with_retry(
                render_fn=unused_render,
                output_path="unused.mp4",
                max_attempts=1,
                initial_backoff=-0.1,
            )

    def test_initial_cpu_mode_never_enables_hardware(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = os.path.join(temp_dir, "cpu.mp4")
            calls = []

            def cpu_render(out_path: str, use_gpu: bool) -> bool:
                calls.append(use_gpu)
                with open(out_path, "wb") as output:
                    output.write(b"CPU_RENDER")
                return True

            WorkflowRenderRetry.execute_render_with_retry(
                render_fn=cpu_render,
                output_path=target_file,
                max_attempts=3,
                initial_backoff=0,
                initial_use_gpu=False,
            )

            self.assertEqual(calls, [False])

    def test_interrupted_render_is_not_retried(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = os.path.join(temp_dir, "cancelled.mp4")
            calls = []

            def cancelled_render(out_path: str, use_gpu: bool) -> bool:
                calls.append(out_path)
                with open(out_path, "wb") as output:
                    output.write(b"PARTIAL_RENDER")
                raise InterruptedError("render cancelled")

            with self.assertRaisesRegex(InterruptedError, "render cancelled"):
                WorkflowRenderRetry.execute_render_with_retry(
                    render_fn=cancelled_render,
                    output_path=target_file,
                    max_attempts=3,
                    initial_backoff=0,
                )

            self.assertEqual(len(calls), 1)
            self.assertFalse(os.path.exists(WorkflowRenderRetry.get_attempt_path(target_file, 1)))

    def test_retry_success_after_failure(self):
        t_fd, target_file = tempfile.mkstemp(suffix=".mp4")
        os.close(t_fd)
        with open(target_file, "wb") as output:
            output.write(b"PREVIOUS_VALID_RENDER")

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
        self.assertEqual(calls[0][0], WorkflowRenderRetry.get_attempt_path(target_file, 1))
        self.assertEqual(calls[1][0], WorkflowRenderRetry.get_attempt_path(target_file, 2))

        # Cleanup
        if os.path.exists(target_file):
            os.unlink(target_file)


if __name__ == "__main__":
    unittest.main()
