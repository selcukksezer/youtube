"""Local end-to-end smoke tests for scenario-to-MP4 rendering."""
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import imageio_ffmpeg

import config
from production.quality import validate_script_quality
from render.ffmpeg_graph import (
    _probe_duration,
    _probe_has_audio,
    render_with_ffmpeg_graph,
)
from scenes.fallback import _generate_procedural_fallback_scenes
from scenes.narration_validate import plan_quality_usable
from server_core.pipeline_state_machine import PipelineStateMachine


class TestRenderPipelineSmoke(unittest.TestCase):
    topic = "Koç burcu için haftalık gökyüzü hareketleri"
    niche_id = "18_astrology_horoscope"

    def _build_valid_plan(self):
        plan = _generate_procedural_fallback_scenes(
            self.topic,
            niche_type=self.niche_id,
            language="tr",
        )
        report = validate_script_quality(plan)
        self.assertTrue(plan_quality_usable(plan["scenes"]))
        self.assertFalse(report["hard_fail"], report["issues"])
        return plan

    def test_scenario_renders_to_valid_vertical_mp4_and_completes(self):
        plan = self._build_valid_plan()
        duration = sum(float(scene["duration"]) for scene in plan["scenes"])
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        with tempfile.TemporaryDirectory(prefix="render_smoke_") as temp_dir:
            clips = []
            palette = (
                "red", "blue", "green", "yellow", "magenta",
                "cyan", "orange", "purple", "white", "black",
            )
            for index, scene in enumerate(plan["scenes"]):
                clip_path = os.path.join(temp_dir, f"scene_{index:02d}.mp4")
                subprocess.run(
                    [
                        ffmpeg, "-y", "-f", "lavfi", "-i",
                        f"color=c={palette[index % len(palette)]}:"
                        "s=360x640:r=24:d=1",
                        "-c:v", "libx264", "-preset", "ultrafast",
                        "-pix_fmt", "yuv420p", clip_path,
                    ],
                    capture_output=True,
                    check=True,
                )
                clips.append({
                    "path": clip_path,
                    "duration": float(scene["duration"]),
                    "scene_index": index,
                    "narration": scene["narration"],
                    "beat_type": scene.get("beat_type"),
                })

            audio_path = os.path.join(temp_dir, "voice_fixture.wav")
            subprocess.run(
                [
                    ffmpeg, "-y", "-f", "lavfi", "-i",
                    f"sine=frequency=440:sample_rate=48000:duration={duration:.3f}",
                    "-c:a", "pcm_s16le", audio_path,
                ],
                capture_output=True,
                check=True,
            )
            output_path = os.path.join(temp_dir, "smoke_output.mp4")

            with (
                patch.object(config, "get_target_resolution", return_value=(360, 640)),
                patch.object(config, "FPS_DIVERSIFY", False),
                patch.object(config, "FPS", 24),
            ):
                result = render_with_ffmpeg_graph(
                    clips=clips,
                    audio_path=audio_path,
                    output_path=output_path,
                    title="",
                )

            self.assertEqual(result, output_path)
            self.assertTrue(os.path.isfile(output_path))
            self.assertGreater(os.path.getsize(output_path), 10_000)
            self.assertTrue(_probe_has_audio(output_path))
            self.assertAlmostEqual(_probe_duration(output_path), duration, delta=1.0)

            probe = subprocess.run(
                [ffmpeg, "-i", output_path, "-hide_banner"],
                capture_output=True,
                text=True,
            )
            self.assertIn("360x640", probe.stderr)

            pipeline = PipelineStateMachine(
                job_id="render-smoke-success",
                keyword=self.topic,
                niche_id=self.niche_id,
            )
            with patch("server_core.state.broadcast_event") as broadcast_event:
                pipeline.complete(output_path)
            self.assertEqual(broadcast_event.call_args.args[0], "complete")
            self.assertEqual(
                broadcast_event.call_args.args[1]["url"],
                output_path,
            )
            self.assertEqual(
                pipeline.export_telemetry()["final_stage"],
                "COMPLETED",
            )

    def test_production_resolution_renders_valid_1080p_vertical_mp4(self):
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        duration = 1.5

        with tempfile.TemporaryDirectory(prefix="render_smoke_1080p_") as temp_dir:
            clip_path = os.path.join(temp_dir, "scene.mp4")
            audio_path = os.path.join(temp_dir, "voice.wav")
            output_path = os.path.join(temp_dir, "smoke_1080p.mp4")
            subprocess.run(
                [
                    ffmpeg, "-y", "-f", "lavfi", "-i",
                    f"color=c=blue:s=360x640:r=24:d={duration}",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", clip_path,
                ],
                capture_output=True,
                check=True,
            )
            subprocess.run(
                [
                    ffmpeg, "-y", "-f", "lavfi", "-i",
                    f"sine=frequency=440:sample_rate=48000:duration={duration}",
                    "-c:a", "pcm_s16le", audio_path,
                ],
                capture_output=True,
                check=True,
            )

            with (
                patch.object(config, "get_target_resolution", return_value=(1080, 1920)),
                patch.object(config, "FPS_DIVERSIFY", False),
                patch.object(config, "FPS", 24),
            ):
                result = render_with_ffmpeg_graph(
                    clips=[{"path": clip_path, "duration": duration, "scene_index": 0}],
                    audio_path=audio_path,
                    output_path=output_path,
                    title="",
                )

            self.assertEqual(result, output_path)
            self.assertTrue(_probe_has_audio(output_path))
            self.assertAlmostEqual(_probe_duration(output_path), duration, delta=1.0)
            probe = subprocess.run(
                [ffmpeg, "-i", output_path, "-hide_banner"],
                capture_output=True,
                text=True,
            )
            self.assertIn("1080x1920", probe.stderr)

    def test_invalid_scene_set_aborts_and_marks_pipeline_failed(self):
        with tempfile.TemporaryDirectory(prefix="render_smoke_failure_") as temp_dir:
            valid_clip = os.path.join(temp_dir, "valid-placeholder.mp4")
            audio_path = os.path.join(temp_dir, "voice-placeholder.wav")
            output_path = os.path.join(temp_dir, "must_not_exist.mp4")
            with open(valid_clip, "wb") as handle:
                handle.write(b"not-decoded-before-partial-set-check")
            with open(audio_path, "wb") as handle:
                handle.write(b"audio-fixture")

            result = render_with_ffmpeg_graph(
                clips=[
                    {"path": valid_clip, "duration": 1.0},
                    {"path": os.path.join(temp_dir, "missing-scene.mp4"), "duration": 1.0},
                ],
                audio_path=audio_path,
                output_path=output_path,
            )

            self.assertEqual(result, "")
            self.assertFalse(os.path.exists(output_path))

            pipeline = PipelineStateMachine(
                job_id="render-smoke-failure",
                keyword=self.topic,
                niche_id=self.niche_id,
            )
            with patch("server_core.state.broadcast_event") as broadcast_event:
                pipeline.fail("Eksik sahne klibi")
            self.assertEqual(broadcast_event.call_args.args[0], "error")
            self.assertEqual(broadcast_event.call_args.args[1], "Eksik sahne klibi")
            telemetry = pipeline.export_telemetry()
            self.assertEqual(telemetry["final_stage"], "FAILED")
            self.assertEqual(telemetry["error"], "Eksik sahne klibi")


if __name__ == "__main__":
    unittest.main()
