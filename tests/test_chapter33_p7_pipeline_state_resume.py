"""
Unit and integration tests for Plan Item P7: Çöken işi kaldığı aşamadan sürdürme (Pipeline State Resume).
References:
- youtube-shorts-pipeline: verticals/state.py PipelineState (is_done, complete_stage, fail_stage, get_artifact, reset, summary, save).
- ShortsVideoCreators resilience enhancement: PipelineStateMachine (file size check >= 64B, dependency invalidation, stale cascading).
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from server_core.pipeline_state_machine import (
    PipelineStage,
    PipelineStateMachine,
    PipelineState,
    REFERENCE_PIPELINE_STAGES,
)


class TestReferencePipelineStateAdapter(unittest.TestCase):
    def test_direct_pipeline_state_reference_lifecycle(self):
        draft = {"title": "Test Short", "scenes": []}
        state = PipelineState(draft)

        self.assertFalse(state.is_done("draft"))
        self.assertFalse(state.is_failed("draft"))

        # Complete stage with artifacts
        state.complete_stage("draft", artifacts={"word_count": 120, "hook": "Secret"})
        self.assertTrue(state.is_done("draft"))
        self.assertFalse(state.is_failed("draft"))
        self.assertEqual(state.get_artifact("draft", "word_count"), 120)
        self.assertEqual(state.get_artifact("draft", "hook"), "Secret")
        self.assertIsNone(state.get_artifact("draft", "missing"))

        # Fail stage
        state.fail_stage("broll", error="Pexels rate limit 429")
        self.assertTrue(state.is_failed("broll"))
        self.assertFalse(state.is_done("broll"))

        # Summary format
        summary = state.summary()
        self.assertIn("[+] draft", summary)
        self.assertIn("[!] broll", summary)
        self.assertIn("[ ] voiceover", summary)

        # Save and reload
        with tempfile.TemporaryDirectory() as tmp:
            save_path = Path(tmp) / "draft.json"
            state.save(save_path)
            self.assertTrue(save_path.is_file())
            loaded = json.loads(save_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["title"], "Test Short")
            self.assertEqual(loaded["_pipeline_state"]["draft"]["status"], "done")

        # Reset
        state.reset()
        self.assertFalse(state.is_done("draft"))
        self.assertEqual(state.state, {})

    def test_pipeline_state_reusable_with_file_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            valid_file = os.path.join(tmp, "clip.mp4")
            with open(valid_file, "wb") as f:
                f.write(b"v" * 128)

            state = PipelineState({})
            state.complete_stage("broll", artifacts={"count": 1}, files=[valid_file])
            self.assertTrue(state.reusable("broll"))

            # Truncated file below 64 bytes fails reusable()
            corrupt_file = os.path.join(tmp, "corrupt.mp4")
            with open(corrupt_file, "wb") as f:
                f.write(b"x" * 20)  # < 64 bytes
            state.complete_stage("broll", artifacts={"count": 1}, files=[corrupt_file])
            self.assertFalse(state.reusable("broll"))

            # Deleted file fails reusable()
            os.remove(corrupt_file)
            self.assertFalse(state.reusable("broll"))


class TestPipelineStateMachineReferenceBridge(unittest.TestCase):
    def test_state_machine_supports_is_done_and_complete_stage(self):
        sm = PipelineStateMachine(job_id="bridge_test", keyword="Kuantum Fizik", niche_id="1_news_flash")
        with tempfile.TemporaryDirectory() as tmp:
            sm.bind_project(tmp, resume=True)

            self.assertFalse(sm.is_done(PipelineStage.STAGE_5_ASSET_INGESTION))
            self.assertFalse(sm.is_done("STAGE_5_ASSET_INGESTION"))

            clip_path = os.path.join(tmp, "clip_1.mp4")
            with open(clip_path, "wb") as f:
                f.write(b"c" * 100)

            sm.complete_stage(
                PipelineStage.STAGE_5_ASSET_INGESTION,
                artifacts={"clips_count": 1},
                files=[clip_path],
            )
            self.assertTrue(sm.is_done(PipelineStage.STAGE_5_ASSET_INGESTION))
            self.assertTrue(sm.is_done("STAGE_5_ASSET_INGESTION"))
            self.assertEqual(sm.get_artifact(PipelineStage.STAGE_5_ASSET_INGESTION, "clips_count"), 1)

            # Failure record
            sm.fail_stage(PipelineStage.STAGE_6_TTS_SYNC, error="TTS Quota Depleted")
            self.assertTrue(sm.is_failed(PipelineStage.STAGE_6_TTS_SYNC))
            self.assertTrue(sm.is_failed("STAGE_6_TTS_SYNC"))

            # Summary overview
            summary = sm.summary()
            self.assertIn("[+] STAGE_5_ASSET_INGESTION", summary)
            self.assertIn("[!] STAGE_6_TTS_SYNC", summary)

            # Explicit save
            custom_save = os.path.join(tmp, "custom_checkpoint.json")
            sm.save(custom_save)
            self.assertTrue(os.path.isfile(custom_save))

            # Reset
            sm.reset()
            self.assertFalse(sm.is_done(PipelineStage.STAGE_5_ASSET_INGESTION))


class TestResiliencePipelineResume(unittest.TestCase):
    def _create_file(self, directory: str, name: str, size: int = 100) -> str:
        path = os.path.join(directory, name)
        with open(path, "wb") as f:
            f.write(b"f" * size)
        return path

    def test_resume_preserves_downloaded_visuals_across_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            c1 = self._create_file(tmp, "s001.mp4", 200)
            c2 = self._create_file(tmp, "s002.mp4", 200)

            # First run completes visuals
            run1 = PipelineStateMachine(job_id="run1", keyword="Tarih", niche_id="5_history")
            run1.bind_project(tmp, resume=True)
            run1.mark_done(
                PipelineStage.STAGE_5_ASSET_INGESTION,
                artifacts={"clips": [{"path": c1}, {"path": c2}]},
                files=[c1, c2],
            )

            # Second run resumes: visuals are reusable
            run2 = PipelineStateMachine(job_id="run2", keyword="Tarih", niche_id="5_history")
            run2.bind_project(tmp, resume=True)
            self.assertTrue(run2.reusable(PipelineStage.STAGE_5_ASSET_INGESTION))
            saved = run2.stage_artifacts(PipelineStage.STAGE_5_ASSET_INGESTION)
            self.assertEqual(len(saved["clips"]), 2)

    def test_audio_file_deletion_invalidates_downstream_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav = self._create_file(tmp, "narration.wav", 500)
            master = self._create_file(tmp, "master.wav", 600)

            sm = PipelineStateMachine(job_id="job_audio", keyword="Felsefe", niche_id="6_stoic_philosophy")
            sm.bind_project(tmp, resume=True)
            sm.mark_done(PipelineStage.STAGE_6_TTS_SYNC, artifacts={"audio_path": wav}, files=[wav])
            sm.mark_done(PipelineStage.STAGE_7_AUDIO_MASTERING, artifacts={"audio_path": master}, files=[master])

            self.assertTrue(sm.reusable(PipelineStage.STAGE_6_TTS_SYNC))
            self.assertTrue(sm.reusable(PipelineStage.STAGE_7_AUDIO_MASTERING))

            # Audio file deleted by external cleaner or disk issue
            os.remove(wav)

            # Reload with resume
            sm_reloaded = PipelineStateMachine(job_id="job_audio", keyword="Felsefe", niche_id="6_stoic_philosophy")
            sm_reloaded.bind_project(tmp, resume=True)

            self.assertFalse(sm_reloaded.reusable(PipelineStage.STAGE_6_TTS_SYNC))
            # Audio mastering requires valid TTS sync
            self.assertFalse(
                sm_reloaded.reusable(
                    PipelineStage.STAGE_7_AUDIO_MASTERING,
                    require=[PipelineStage.STAGE_6_TTS_SYNC],
                )
            )

            # When Stage 6 re-runs, it invalidates Stage 7 to prevent double whoosh / stale ducking
            sm_reloaded.invalidate_from(PipelineStage.STAGE_6_TTS_SYNC)
            summary = sm_reloaded.summary()
            self.assertIn("[~] STAGE_7_AUDIO_MASTERING", summary)

    def test_resume_flag_disabled_ignores_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav = self._create_file(tmp, "voice.wav", 300)
            writer = PipelineStateMachine(job_id="prev", keyword="Bilim", niche_id="2_science_curiosity")
            writer.bind_project(tmp, resume=True)
            writer.mark_done(PipelineStage.STAGE_6_TTS_SYNC, artifacts={"audio_path": wav}, files=[wav])

            # New run with resume=False
            fresh = PipelineStateMachine(job_id="new", keyword="Bilim", niche_id="2_science_curiosity")
            fresh.bind_project(tmp, resume=False)
            self.assertFalse(fresh.reusable(PipelineStage.STAGE_6_TTS_SYNC))


if __name__ == "__main__":
    unittest.main()
