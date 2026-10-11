"""
Unit Tests for Chapter 3: FFmpeg Native Graph ve Donanım Render Motoru (render/ffmpeg_graph.py).
Validates:
- 3.1 FilterComplex Mimari Topolojisi
- 3.2 Sub-Pixel Float Precision Ken Burns Ease-in-out
- 3.3 Otomatik Fit & Fill Gaussian Blur Arka Plan Katmanı
- 3.4 Çoklu Donanım Hızlandırma Müzakeresi (NVENC, QSV, AMF, VideoToolbox, VAAPI, libx264)
- 3.5 Subprocess Heartbeat Takibi ve Zombi Süreç Yalıtımı
- 3.6 Çift Sayılı Piksel Modülo Hizalama ve WhatsApp/Telegram Toleransı
- 3.7 Renk uzayı BT.709. İki geçişli video encode yok
"""
import unittest
import inspect
import io
import os
import shutil
import subprocess
import tempfile
from unittest.mock import patch
from render import ffmpeg_graph
from system_resilience import (
    get_encoder_fallback_chain,
    get_available_ffmpeg_encoders,
    get_ffmpeg_vcodec_args,
)


class TestChapter3FFmpegNativeGraph(unittest.TestCase):
    def test_temp_workspace_is_removed_when_progress_callback_raises(self):
        with tempfile.TemporaryDirectory() as inputs:
            clip_path = os.path.join(inputs, "clip.mp4")
            audio_path = os.path.join(inputs, "voice.wav")
            for path in (clip_path, audio_path):
                with open(path, "wb") as media:
                    media.write(b"placeholder")

            created = []
            original_mkdtemp = tempfile.mkdtemp

            def record_temp_dir(*args, **kwargs):
                path = original_mkdtemp(*args, **kwargs)
                created.append(path)
                return path

            def fail_progress(*_args, **_kwargs):
                raise RuntimeError("progress callback failed")

            try:
                with patch.object(ffmpeg_graph.tempfile, "mkdtemp", side_effect=record_temp_dir), \
                    patch.object(ffmpeg_graph.imageio_ffmpeg, "get_ffmpeg_exe", return_value="ffmpeg"):
                    with self.assertRaisesRegex(RuntimeError, "progress callback failed"):
                        ffmpeg_graph.render_with_ffmpeg_graph(
                            [{"path": clip_path, "duration": 3.0}],
                            audio_path,
                            os.path.join(inputs, "out.mp4"),
                            progress_callback=fail_progress,
                        )

                self.assertEqual(len(created), 1)
                self.assertFalse(os.path.exists(created[0]))
            finally:
                for path in created:
                    shutil.rmtree(path, ignore_errors=True)

    def test_ffmpeg_process_is_reaped_when_progress_callback_raises(self):
        class RunningProcess:
            def __init__(self):
                self.returncode = None
                self.stdout = io.StringIO("")
                self.stderr = io.StringIO("frame=20 time=00:00:01.00\n")
                self.terminated = False
                self.killed = False
                self.waited = False

            def poll(self):
                return self.returncode

            def terminate(self):
                self.terminated = True
                self.returncode = -15

            def kill(self):
                self.killed = True
                self.returncode = -9

            def wait(self, timeout=None):
                self.waited = True
                return self.returncode

        with tempfile.TemporaryDirectory() as inputs:
            clip_path = os.path.join(inputs, "clip.mp4")
            audio_path = os.path.join(inputs, "voice.wav")
            for path in (clip_path, audio_path):
                with open(path, "wb") as media:
                    media.write(b"placeholder")

            process = RunningProcess()

            def fail_during_encode(percent, _message):
                if percent == 88:
                    raise RuntimeError("progress callback failed")

            with patch.object(ffmpeg_graph.imageio_ffmpeg, "get_ffmpeg_exe", return_value="ffmpeg"), \
                patch.object(ffmpeg_graph, "_probe_duration", return_value=3.0), \
                patch.object(ffmpeg_graph, "_probe_is_landscape", return_value=False), \
                patch.object(ffmpeg_graph, "_probe_has_audio", return_value=True), \
                patch.object(ffmpeg_graph, "_probe_audio_duration", return_value=3.0), \
                patch.object(ffmpeg_graph, "probe_stream_color", return_value={}), \
                patch("system_resilience.get_encoder_fallback_chain", return_value=[(["-c:v", "libx264"], "CPU")]), \
                patch.object(ffmpeg_graph.subprocess, "Popen", return_value=process):
                ffmpeg_graph.render_with_ffmpeg_graph(
                    [{"path": clip_path, "duration": 3.0}],
                    audio_path,
                    os.path.join(inputs, "out.mp4"),
                    progress_callback=fail_during_encode,
                )

            self.assertTrue(process.terminated)
            self.assertTrue(process.waited)
            self.assertTrue(process.stdout.closed)
            self.assertTrue(process.stderr.closed)

    def test_ffmpeg_process_is_killed_and_reaped_after_terminate_timeout(self):
        class StuckProcess:
            def __init__(self):
                self.wait_calls = 0
                self.killed = False
                self.returncode = None
                self.stdout = io.StringIO("")
                self.stderr = io.StringIO("")

            def poll(self):
                return self.returncode

            def terminate(self):
                return None

            def kill(self):
                self.killed = True
                self.returncode = -9

            def wait(self, timeout=None):
                self.wait_calls += 1
                if self.wait_calls == 1:
                    raise subprocess.TimeoutExpired("ffmpeg", timeout)
                return self.returncode

        process = StuckProcess()
        ffmpeg_graph._cleanup_ffmpeg_process(process)
        self.assertTrue(process.killed)
        self.assertEqual(process.wait_calls, 2)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(process.stderr.closed)

    def test_partial_output_is_removed_when_all_encoders_fail(self):
        class FailedProcess:
            def __init__(self):
                self.returncode = 1
                self.stdout = io.StringIO("")
                self.stderr = io.StringIO("encoding failed\n")

            def poll(self):
                return self.returncode

            def wait(self, timeout=None):
                return self.returncode

            def terminate(self):
                return None

            def kill(self):
                return None

        with tempfile.TemporaryDirectory() as inputs:
            clip_path = os.path.join(inputs, "clip.mp4")
            audio_path = os.path.join(inputs, "voice.wav")
            output_path = os.path.join(inputs, "partial.mp4")
            for path in (clip_path, audio_path):
                with open(path, "wb") as media:
                    media.write(b"placeholder")

            process = FailedProcess()

            def create_partial_output(command, **_kwargs):
                with open(command[-1], "wb") as output:
                    output.write(b"partial mp4")
                return process

            with patch.object(ffmpeg_graph.imageio_ffmpeg, "get_ffmpeg_exe", return_value="ffmpeg"), \
                patch.object(ffmpeg_graph, "_probe_duration", return_value=3.0), \
                patch.object(ffmpeg_graph, "_probe_is_landscape", return_value=False), \
                patch.object(ffmpeg_graph, "_probe_has_audio", return_value=True), \
                patch.object(ffmpeg_graph, "_probe_audio_duration", return_value=3.0), \
                patch.object(ffmpeg_graph, "probe_stream_color", return_value={}), \
                patch("system_resilience.get_encoder_fallback_chain", return_value=[(["-c:v", "libx264"], "CPU")]), \
                patch.object(ffmpeg_graph.subprocess, "Popen", side_effect=create_partial_output):
                result = ffmpeg_graph.render_with_ffmpeg_graph(
                    [{"path": clip_path, "duration": 3.0}],
                    audio_path,
                    output_path,
                )

            self.assertEqual(result, "")
            self.assertFalse(os.path.exists(output_path))

    def test_generated_reddit_overlay_uses_cleaned_graph_workspace(self):
        with tempfile.TemporaryDirectory() as inputs:
            clip_path = os.path.join(inputs, "clip.mp4")
            audio_path = os.path.join(inputs, "voice.wav")
            for path in (clip_path, audio_path):
                with open(path, "wb") as media:
                    media.write(b"placeholder")

            generated = []

            def generate_card(*, output_path, **_kwargs):
                generated.append(output_path)
                with open(output_path, "wb") as card:
                    card.write(b"reddit overlay")
                return output_path

            def fail_progress(percent, _message):
                if percent == 80:
                    raise RuntimeError("render setup stopped")

            with patch.object(ffmpeg_graph.tempfile, "gettempdir", return_value=inputs), \
                patch.object(ffmpeg_graph.imageio_ffmpeg, "get_ffmpeg_exe", return_value="ffmpeg"), \
                patch.object(ffmpeg_graph, "_probe_duration", return_value=3.0), \
                patch.object(ffmpeg_graph, "_probe_is_landscape", return_value=False), \
                patch.object(ffmpeg_graph, "_probe_has_audio", return_value=True), \
                patch.object(ffmpeg_graph, "_probe_audio_duration", return_value=3.0), \
                patch.object(ffmpeg_graph, "probe_stream_color", return_value={}), \
                patch("reddit_card_renderer.generate_transparent_reddit_card_png", side_effect=generate_card):
                result = ffmpeg_graph.render_with_ffmpeg_graph(
                    [{"path": clip_path, "duration": 3.0}],
                    audio_path,
                    os.path.join(inputs, "out.mp4"),
                    enable_reddit_card=True,
                    progress_callback=fail_progress,
                )

            self.assertEqual(len(generated), 1)
            self.assertEqual(result, "")
            self.assertFalse(os.path.exists(generated[0]))

    def test_3_2_ken_burns_cosine_ease_in_out(self):
        """3.2: Sub-pixel float precision cosine ease-in-out progression."""
        filt = ffmpeg_graph.cheap_pan_filter(1080, 1920, 4.0, scene_index=0)
        self.assertIn("0.5*(1-cos(PI*min(t", filt)
        self.assertIn("crop=1080:1920", filt)
        # Even dimension check for overscale
        self.assertIn("scale=", filt)

    def test_3_3_fit_and_fill_gaussian_blur(self):
        """3.3: Landscape assets get blurred background + centered foreground."""
        chain = ffmpeg_graph.build_scene_filter_chain(
            input_index=0,
            duration=3.5,
            width=1080,
            height=1920,
            scene_index=0,
            fit_and_fill=True,
        )
        self.assertIn("boxblur=25:5", chain)
        self.assertIn("force_original_aspect_ratio=increase", chain)
        self.assertIn("force_original_aspect_ratio=decrease", chain)
        self.assertIn("overlay=(W-w)/2:(H-h)/2", chain)

    def test_3_4_hardware_acceleration_negotiation(self):
        """3.4: Fallback chain contains GPU encoders and terminates with libx264."""
        chain = get_encoder_fallback_chain(use_gpu=True)
        self.assertTrue(len(chain) >= 2)
        # Last candidate must always be CPU libx264
        last_args, last_label = chain[-1]
        self.assertIn("libx264", last_args)
        self.assertIn("CPU", last_label)

        # Probed encoders set is non-empty
        encoders = get_available_ffmpeg_encoders()
        self.assertIn("libx264", encoders)

    def test_3_6_modulo_2_even_dimensions(self):
        """3.6: Odd input dimensions must be aligned to even numbers."""
        chain = ffmpeg_graph.build_scene_filter_chain(
            input_index=0,
            duration=3.0,
            width=1081,  # Odd width
            height=1921,  # Odd height
            scene_index=0,
            split_screen=True,
            gameplay_label="[gp0]",
        )
        # Even heights only
        self.assertIn("crop=1080:", chain)

    def test_3_7_color_space_and_faststart(self):
        """3.7: Color space flags (bt709) and faststart in render source."""
        src = inspect.getsource(ffmpeg_graph.render_with_ffmpeg_graph)
        self.assertIn("-colorspace", src)
        self.assertIn("bt709", src)
        self.assertIn("-color_primaries", src)
        self.assertIn("-color_trc", src)
        self.assertIn("-pix_fmt", src)
        self.assertIn("yuv420p", src)
        self.assertIn("+faststart", src)
        self.assertIn("-color_range", src)
        self.assertIn("_BT709_TAG", src)
        self.assertIn("setparams=color_primaries=bt709", ffmpeg_graph._BT709_TAG)
        self.assertNotIn('"-pass"', src)

    def test_3_7_convert_bt601_and_full_range_only(self):
        """Untagged bt709 is not converted. bt601 and full range are."""
        self.assertEqual(ffmpeg_graph.color_convert_filter({}), "")
        self.assertEqual(
            ffmpeg_graph.color_convert_filter({"color_space": "bt709", "color_range": "tv"}),
            "",
        )
        filt = ffmpeg_graph.color_convert_filter({
            "color_space": "smpte170m",
            "color_range": "pc",
        })
        self.assertIn("iall=bt601-6-525", filt)
        self.assertIn("irange=pc", filt)
        self.assertIn("range=tv", filt)
        hdr = ffmpeg_graph.color_convert_filter({"color_transfer": "arib-std-b67"})
        self.assertIn("zscale=pin=bt2020:tin=arib-std-b67:min=bt2020nc:", hdr)
        self.assertIn("t=bt709:m=bt709:p=bt709:r=tv", hdr)
        self.assertNotIn("tonemap", hdr)
        pq = ffmpeg_graph.color_convert_filter({
            "color_transfer": "smpte2084",
            "color_space": "bt2020ncl",
        })
        self.assertIn("tin=smpte2084:min=bt2020nc:", pq)
        chain = ffmpeg_graph.build_scene_filter_chain(
            0, 3.0, 1080, 1920, 0, enable_ken_burns=False, color_filter=filt,
        )
        self.assertTrue(chain.startswith(f"[0:v]{filt},trim="))


if __name__ == "__main__":
    unittest.main()
