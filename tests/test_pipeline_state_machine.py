# -*- coding: utf-8 -*-
"""
Tests for the Chapter 1 Pipeline State Machine (Section 1.3 / 10-step sequence).
"""
import json
import os
import tempfile
import unittest

from server_core.pipeline_state_machine import (
    PipelineStateMachine,
    PipelineStage,
    STAGE_SPECS,
)


class TestPipelineStateMachine(unittest.TestCase):
    def test_ten_stages_metadata_integrity(self):
        """Verify all 10 stages are properly defined in sequential order 1..10."""
        stages = [
            PipelineStage.STAGE_1_VALIDATION,
            PipelineStage.STAGE_2_HOOK_NARRATIVE,
            PipelineStage.STAGE_3_DIRECTOR_PLAN,
            PipelineStage.STAGE_4_ORIGINALITY_GATE,
            PipelineStage.STAGE_5_ASSET_INGESTION,
            PipelineStage.STAGE_6_TTS_SYNC,
            PipelineStage.STAGE_7_AUDIO_MASTERING,
            PipelineStage.STAGE_8_SUBTITLE_COMPILE,
            PipelineStage.STAGE_9_FFMPEG_RENDER,
            PipelineStage.STAGE_10_PACKAGING,
        ]
        self.assertEqual(len(stages), 10)
        for i, st in enumerate(stages, start=1):
            spec = STAGE_SPECS[st]
            self.assertEqual(spec.order, i)
            self.assertTrue(spec.min_pct < spec.max_pct)
            self.assertTrue(bool(spec.name_tr))
            self.assertTrue(bool(spec.description))

    def test_lifecycle_full_run_and_telemetry(self):
        """Verify state machine progresses through all 10 stages and exports telemetry."""
        sm = PipelineStateMachine(job_id="test_job_1", keyword="Stoic Wisdom", niche_id="6_stoic_philosophy")
        self.assertEqual(sm.current_stage, PipelineStage.STAGE_1_VALIDATION)

        # Stage 2
        sm.transition_to(PipelineStage.STAGE_2_HOOK_NARRATIVE, "Kanca kurgulanıyor", pct=8.0)
        self.assertEqual(sm.current_stage, PipelineStage.STAGE_2_HOOK_NARRATIVE)
        self.assertEqual(sm.current_pct, 8.0)

        # Stage 3
        sm.transition_to(PipelineStage.STAGE_3_DIRECTOR_PLAN, "Timeline derleniyor", pct=18.0)
        self.assertEqual(sm.current_stage, PipelineStage.STAGE_3_DIRECTOR_PLAN)

        # Stage 4
        sm.transition_to(PipelineStage.STAGE_4_ORIGINALITY_GATE, "İntihal taranıyor", pct=27.0)
        self.assertEqual(sm.current_stage, PipelineStage.STAGE_4_ORIGINALITY_GATE)

        # Stage 5
        sm.transition_to(PipelineStage.STAGE_5_ASSET_INGESTION, "Stok klipler indiriliyor", pct=35.0)
        sm.update_progress(45.0, "Klipler %50 indirildi")
        self.assertEqual(sm.current_pct, 45.0)

        # Stage 6
        sm.transition_to(PipelineStage.STAGE_6_TTS_SYNC, "TTS üretiliyor", pct=60.0)

        # Stage 7
        sm.transition_to(PipelineStage.STAGE_7_AUDIO_MASTERING, "BGM sidechain miksleniyor", pct=70.0)

        # Stage 8
        sm.transition_to(PipelineStage.STAGE_8_SUBTITLE_COMPILE, "ASS altyazılar derleniyor", pct=78.0)

        # Stage 9
        sm.transition_to(PipelineStage.STAGE_9_FFMPEG_RENDER, "FFmpeg donanım ivmeli encode", pct=88.0)

        # Stage 10
        sm.transition_to(PipelineStage.STAGE_10_PACKAGING, "Paketleniyor", pct=97.0)

        # Complete
        sm.complete("/output/test_video.mp4")
        self.assertEqual(sm.current_stage, PipelineStage.COMPLETED)
        self.assertEqual(sm.current_pct, 100.0)

        # Telemetry export
        telemetry = sm.export_telemetry()
        self.assertEqual(telemetry["job_id"], "test_job_1")
        self.assertEqual(telemetry["final_stage"], "COMPLETED")
        self.assertEqual(telemetry["final_pct"], 100.0)
        self.assertEqual(len(telemetry["stages"]), 11)  # 10 stages + completed
        self.assertGreaterEqual(telemetry["total_duration_sec"], 0.0)

        # Telemetry persistence test
        with tempfile.TemporaryDirectory() as tmp_dir:
            saved_path = sm.save_telemetry(tmp_dir)
            self.assertIsNotNone(saved_path)
            self.assertTrue(os.path.exists(saved_path))
            with open(saved_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["video_url"], "/output/test_video.mp4")

    def test_failure_handling(self):
        """Verify fail() properly captures error state and telemetry."""
        sm = PipelineStateMachine(job_id="test_fail", keyword="Kripto", niche_id="8_crypto_market")
        sm.transition_to(PipelineStage.STAGE_2_HOOK_NARRATIVE, pct=10.0)
        sm.fail("API Quota Exceeded")

        self.assertEqual(sm.current_stage, PipelineStage.FAILED)
        telemetry = sm.export_telemetry()
        self.assertEqual(telemetry["error"], "API Quota Exceeded")
        self.assertEqual(telemetry["final_stage"], "FAILED")


class TestResumeCheckpoint(unittest.TestCase):
    """youtube-shorts-pipeline is_done trusts status. A deleted wav still skips.

    reusable() requires every recorded file to exist and be at least 64 bytes.
    resume=False does not load pipeline_state.json.
    """

    def _blob(self, directory: str, name: str) -> str:
        path = os.path.join(directory, name)
        with open(path, "wb") as handle:
            handle.write(b"x" * 80)
        return path

    def test_done_without_files_is_not_reusable(self):
        with tempfile.TemporaryDirectory() as tmp:
            sm = PipelineStateMachine(job_id="empty", keyword="konu", niche_id="n")
            sm.bind_project(tmp, resume=True)
            sm.mark_done(PipelineStage.STAGE_5_ASSET_INGESTION, artifacts={"clips": []}, files=[])
            self.assertFalse(sm.reusable(PipelineStage.STAGE_5_ASSET_INGESTION))

    def test_missing_file_forces_that_stage_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            clip_a = self._blob(tmp, "a.mp4")
            clip_b = self._blob(tmp, "b.mp4")
            wav = self._blob(tmp, "voice.wav")
            master = self._blob(tmp, "master.wav")
            sm = PipelineStateMachine(job_id="job", keyword="konu", niche_id="n")
            sm.bind_project(tmp, resume=True)
            sm.mark_done(
                PipelineStage.STAGE_5_ASSET_INGESTION,
                artifacts={"clips": [{"path": clip_a}, {"path": clip_b}]},
                files=[clip_a, clip_b],
            )
            sm.mark_done(
                PipelineStage.STAGE_6_TTS_SYNC,
                artifacts={"audio_path": wav, "timings": [{"word": "bir"}]},
                files=[wav],
            )
            sm.mark_done(
                PipelineStage.STAGE_7_AUDIO_MASTERING,
                artifacts={"audio_path": master, "timings": [{"word": "bir"}]},
                files=[master],
            )
            self.assertTrue(sm.reusable(PipelineStage.STAGE_5_ASSET_INGESTION))
            os.remove(clip_b)
            reloaded = PipelineStateMachine(job_id="job", keyword="konu", niche_id="n")
            reloaded.bind_project(tmp, resume=True)
            self.assertFalse(reloaded.reusable(PipelineStage.STAGE_5_ASSET_INGESTION))
            self.assertTrue(reloaded.reusable(PipelineStage.STAGE_6_TTS_SYNC))
            os.remove(wav)
            after_audio = PipelineStateMachine(job_id="job", keyword="konu", niche_id="n")
            after_audio.bind_project(tmp, resume=True)
            self.assertFalse(after_audio.reusable(PipelineStage.STAGE_6_TTS_SYNC))
            self.assertFalse(after_audio.reusable(
                PipelineStage.STAGE_7_AUDIO_MASTERING,
                require=[PipelineStage.STAGE_6_TTS_SYNC],
            ))
            self.assertTrue(os.path.isfile(master))

    def test_new_job_does_not_read_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav = self._blob(tmp, "voice.wav")
            writer = PipelineStateMachine(job_id="old", keyword="konu", niche_id="n")
            writer.bind_project(tmp, resume=True)
            writer.mark_done(
                PipelineStage.STAGE_6_TTS_SYNC,
                artifacts={"audio_path": wav, "timings": [{"word": "bir"}]},
                files=[wav],
            )
            self.assertTrue(os.path.isfile(os.path.join(tmp, "pipeline_state.json")))
            fresh = PipelineStateMachine(job_id="new", keyword="konu", niche_id="n")
            fresh.bind_project(tmp, resume=False)
            self.assertFalse(fresh.reusable(PipelineStage.STAGE_6_TTS_SYNC))

    def test_regenerated_tts_stales_master(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav = self._blob(tmp, "voice.wav")
            master = self._blob(tmp, "master.wav")
            sm = PipelineStateMachine(job_id="job", keyword="konu", niche_id="n")
            sm.bind_project(tmp, resume=True)
            sm.mark_done(PipelineStage.STAGE_6_TTS_SYNC, {"audio_path": wav, "timings": [{"word": "a"}]}, [wav])
            sm.mark_done(PipelineStage.STAGE_7_AUDIO_MASTERING, {"audio_path": master}, [master])
            sm.invalidate_from(PipelineStage.STAGE_6_TTS_SYNC)
            self.assertFalse(sm.reusable(PipelineStage.STAGE_6_TTS_SYNC))
            self.assertFalse(sm.reusable(PipelineStage.STAGE_7_AUDIO_MASTERING))
            sm.mark_done(PipelineStage.STAGE_6_TTS_SYNC, {"audio_path": wav, "timings": [{"word": "b"}]}, [wav])
            self.assertTrue(sm.reusable(PipelineStage.STAGE_6_TTS_SYNC))
            self.assertFalse(sm.reusable(
                PipelineStage.STAGE_7_AUDIO_MASTERING,
                require=[PipelineStage.STAGE_6_TTS_SYNC],
            ))

