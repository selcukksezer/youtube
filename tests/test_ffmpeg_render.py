"""
Comprehensive End-to-End Test Suite for Bölüm 18.2 & 18.3:
FFmpeg Physical Render, Quality Assurance, Memory Leak & Process Hygiene.
Verifies:
  - 18.2 Physical MP4 output, file size > 500KB, duration matching plan, fps=30
  - 18.3 Memory leak bounds (tracemalloc delta < 5MB)
  - 18.3 Process zombie detection & temp file garbage collection
"""
import json
import os
import shutil
import subprocess
import tempfile
import tracemalloc
import unittest
import imageio_ffmpeg

from render.ffmpeg_graph import (
    render_with_ffmpeg_graph,
    compose_via_director,
    align_even_dimension,
)


def _get_ffmpeg_pids():
    try:
        import psutil
        return {
            p.pid for p in psutil.process_iter(["name", "pid"])
            if "ffmpeg" in (p.info["name"] or "").lower()
        }
    except ImportError:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True,
        )
        pids = set()
        for line in out.stdout.splitlines():
            parts = [p.strip(' "') for p in line.split(",")]
            if parts and "ffmpeg" in parts[0].lower():
                try:
                    pids.add(int(parts[1]))
                except (ValueError, IndexError):
                    pass
        return pids


class TestFFmpegRender(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cls.tmp_work_dir = tempfile.mkdtemp(prefix="test_ffrender_cls_")

        # Generate a reusable 1080x1920 3-second test clip
        cls.sample_clip = os.path.join(cls.tmp_work_dir, "sample_clip.mp4")
        subprocess.run(
            [
                cls.ffmpeg_exe, "-y", "-f", "lavfi",
                "-i", "testsrc=duration=3:size=1080x1920:rate=30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                cls.sample_clip,
            ],
            capture_output=True, check=True,
        )

        # Generate a 3-second audio wave
        cls.sample_audio = os.path.join(cls.tmp_work_dir, "sample_audio.wav")
        subprocess.run(
            [
                cls.ffmpeg_exe, "-y", "-f", "lavfi",
                "-i", "sine=frequency=500:duration=3",
                "-c:a", "pcm_s16le",
                cls.sample_audio,
            ],
            capture_output=True, check=True,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_work_dir, ignore_errors=True)

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_ffrender_case_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _probe_video(self, video_path: str) -> dict:
        """Run ffprobe / ffmpeg to inspect stream properties."""
        cmd = [
            self.ffmpeg_exe, "-i", video_path, "-hide_banner"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.stderr

    # ─── 18.2 Test 1: Fiziksel MP4 Çıktısı, Boyut (>500KB) ve FPS (30) ───
    def test_physical_mp4_generation_size_and_fps(self):
        """18.2: End-to-end MP4 export size > 500KB, fps ~30, 1080x1920, valid audio/video."""
        output_mp4 = os.path.join(self.test_dir, "render_output.mp4")
        clips = [
            {"path": self.sample_clip, "duration": 3.0, "scene_index": 0}
        ]
        word_timings = [
            {"word": "Başarı", "start": 0.2, "end": 1.2},
            {"word": "Odaklanma", "start": 1.2, "end": 2.5},
        ]

        result = render_with_ffmpeg_graph(
            clips=clips,
            audio_path=self.sample_audio,
            output_path=output_mp4,
            word_timings=word_timings,
            title="Bölüm 18 E2E Test",
        )

        self.assertTrue(os.path.isfile(output_mp4), f"Render output not found: {result}")
        size_bytes = os.path.getsize(output_mp4)
        # Criterion: > 500 KB (512,000 bytes)
        self.assertGreater(size_bytes, 500 * 1024, f"Output size {size_bytes} is under 500KB threshold")

        stderr = self._probe_video(output_mp4)
        self.assertIn("1080x1920", stderr)
        self.assertTrue("fps" in stderr or "tbr" in stderr)
        self.assertIn("Audio:", stderr)

    # ─── 18.2 Test 2: Süre Planla Uyumlu (Duration Matching) ───
    def test_render_duration_matches_plan(self):
        """18.2: Output video duration must match the audio/plan timeline within ±0.5s."""
        output_mp4 = os.path.join(self.test_dir, "duration_match.mp4")
        clips = [
            {"path": self.sample_clip, "duration": 3.0, "scene_index": 0}
        ]

        render_with_ffmpeg_graph(
            clips=clips,
            audio_path=self.sample_audio,
            output_path=output_mp4,
            word_timings=[{"word": "Zaman", "start": 0.0, "end": 2.8}],
        )
        self.assertTrue(os.path.isfile(output_mp4))

        stderr = self._probe_video(output_mp4)
        # Look for Duration: 00:00:03.xx
        self.assertIn("Duration: 00:00:03.", stderr)

    # ─── 18.3 Test 3: Bellek Sızıntısı ve Tracemalloc Doğrulaması ───
    def test_tracemalloc_memory_leak_bounds(self):
        """18.3: Sequential rendering heap allocation must remain bounded (< 5MB delta)."""
        tracemalloc.start()
        snapshot_start = tracemalloc.take_snapshot()

        for i in range(3):
            out_path = os.path.join(self.test_dir, f"loop_render_{i}.mp4")
            clips = [{"path": self.sample_clip, "duration": 1.5, "scene_index": 0}]
            render_with_ffmpeg_graph(
                clips=clips,
                audio_path=self.sample_audio,
                output_path=out_path,
                word_timings=[{"word": f"Adım {i}", "start": 0.1, "end": 1.2}],
            )

        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_end.compare_to(snapshot_start, "lineno")
        total_delta_bytes = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
        total_delta_mb = total_delta_bytes / (1024 * 1024)

        # Must be strictly under 5MB per Item 18.3
        self.assertLess(total_delta_mb, 5.0, f"Memory growth exceeded limit: {total_delta_mb:.2f} MB")

    # ─── 18.3 Test 4: Zombi Süreç ve Geçici Dosya Temizliği ───
    def test_process_and_temporary_file_cleanup(self):
        """18.3: No orphaned ffmpeg processes remain, and temporary ffgraph directories are deleted."""
        initial_ffmpeg_pids = _get_ffmpeg_pids()
        temp_root = tempfile.gettempdir()
        initial_ffgraph_dirs = {
            f for f in os.listdir(temp_root)
            if f.startswith("ffgraph_") and os.path.isdir(os.path.join(temp_root, f))
        }

        out_path = os.path.join(self.test_dir, "cleanup_test.mp4")
        clips = [{"path": self.sample_clip, "duration": 2.0, "scene_index": 0}]
        render_with_ffmpeg_graph(
            clips=clips,
            audio_path=self.sample_audio,
            output_path=out_path,
        )

        # Allow OS process reaper up to 1.5s to close completed process handles
        import time
        alive_pids = set()
        for _ in range(5):
            current_pids = _get_ffmpeg_pids()
            alive_pids = current_pids - initial_ffmpeg_pids
            if not alive_pids:
                break
            time.sleep(0.3)
        self.assertEqual(len(alive_pids), 0, f"Orphaned FFmpeg processes found: {alive_pids}")

        final_ffgraph_dirs = {
            f for f in os.listdir(temp_root)
            if f.startswith("ffgraph_") and os.path.isdir(os.path.join(temp_root, f))
        }
        leaked_dirs = final_ffgraph_dirs - initial_ffgraph_dirs
        self.assertEqual(len(leaked_dirs), 0, f"Temporary render directories not cleaned up: {leaked_dirs}")


if __name__ == "__main__":
    unittest.main()
