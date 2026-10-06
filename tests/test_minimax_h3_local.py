"""MiniMax-H3 stays off the default chain and talks to local ComfyUI."""
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from visuals.ai_video.providers import ALL_PROVIDER_CLASSES
from visuals.ai_video.providers.minimax_h3 import (
    FL2VA_FILE,
    generate_local_h3_clip,
)


class MiniMaxH3LocalTests(unittest.TestCase):
    def test_default_provider_chain_does_not_include_h3(self):
        names = [cls.name for cls in ALL_PROVIDER_CLASSES]
        self.assertNotIn("minimax_h3", names)
        self.assertIn("minimax", names)

    def test_comfy_prompt_uses_int8_fl2va_and_returns_mp4(self):
        created = MagicMock()
        created.status_code = 200
        created.json.return_value = {"prompt_id": "job_1", "node_errors": {}}
        history = MagicMock()
        history.status_code = 200
        history.json.return_value = {
            "job_1": {
                "status": {"status_str": "success", "completed": True},
                "outputs": {
                    "15": {
                        "images": [{
                            "filename": "MiniMax_H3_00001_.mp4",
                            "subfolder": "video",
                            "type": "output",
                        }],
                        "animated": [True],
                    }
                },
            }
        }
        media = MagicMock()
        media.status_code = 200
        media.content = b"\x00\x00\x00\x18ftyp" + (b"\x00" * 12000)
        with patch("visuals.ai_video.providers.minimax_h3.comfy_server_ready", return_value=True), \
                patch("visuals.ai_video.providers.minimax_h3.comfy_base_url", return_value="http://127.0.0.1:8188"), \
                patch("visuals.ai_video.providers.minimax_h3.requests.post", return_value=created) as post, \
                patch("visuals.ai_video.providers.minimax_h3.requests.get", side_effect=[history, media]), \
                patch("visuals.ai_video.providers.minimax_h3.write_bytes", return_value=True) as write:
            path = generate_local_h3_clip("a quiet mosque courtyard", "out.mp4", duration=3, aspect="9:16")
        self.assertEqual(path, "out.mp4")
        self.assertEqual(post.call_args.args[0], "http://127.0.0.1:8188/prompt")
        graph = post.call_args.kwargs["json"]["prompt"]
        unet = graph["1"]["inputs"]["unet_name"]
        self.assertEqual(unet, FL2VA_FILE)
        self.assertIn("int8", unet)
        self.assertEqual(graph["6"]["inputs"]["width"], 768)
        self.assertEqual(graph["6"]["inputs"]["height"], 1344)
        self.assertGreaterEqual(graph["6"]["inputs"]["length"], 5)
        self.assertEqual(graph["12"]["class_type"], "VAEDecodeTiled")
        self.assertEqual(graph["12"]["inputs"]["tile_size"], 256)
        write.assert_called_once()

    def test_missing_comfy_and_sglang_returns_none(self):
        with patch("visuals.ai_video.providers.minimax_h3.comfy_server_ready", return_value=False), \
                patch("visuals.ai_video.providers.minimax_h3.local_server_ready", return_value=False), \
                patch("visuals.ai_video.providers.minimax_h3.requests.post") as post:
            path = generate_local_h3_clip("a quiet mosque courtyard", "out.mp4")
        self.assertIsNone(path)
        post.assert_not_called()

    def test_sglang_only_when_already_up(self):
        created = MagicMock()
        created.status_code = 200
        created.json.return_value = {"id": "vid_1"}
        status = MagicMock()
        status.status_code = 200
        status.json.return_value = {"status": "completed"}
        media = MagicMock()
        media.status_code = 200
        media.content = b"\x00\x00\x00\x18ftyp"
        with patch("visuals.ai_video.providers.minimax_h3.comfy_server_ready", return_value=False), \
                patch("visuals.ai_video.providers.minimax_h3.local_server_ready", return_value=True), \
                patch("visuals.ai_video.providers.minimax_h3.requests.post", return_value=created) as post, \
                patch("visuals.ai_video.providers.minimax_h3.requests.get", side_effect=[status, media]), \
                patch("visuals.ai_video.providers.minimax_h3.local_base_url", return_value="http://127.0.0.1:30010"), \
                patch("visuals.ai_video.providers.minimax_h3.write_bytes", return_value=True):
            path = generate_local_h3_clip("a quiet mosque courtyard", "out.mp4", duration=3, aspect="9:16")
        self.assertEqual(path, "out.mp4")
        self.assertEqual(post.call_args.args[0], "http://127.0.0.1:30010/v1/videos")
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["task"], "t2va")
        self.assertGreaterEqual(body["target"]["duration_seconds"], 4.0)


class MiniMaxH3QueueTests(unittest.TestCase):
    def _history(self):
        history = MagicMock()
        history.status_code = 200
        history.json.return_value = {
            "job": {
                "status": {"status_str": "success", "completed": True},
                "outputs": {
                    "15": {
                        "images": [{
                            "filename": "MiniMax_H3_00001_.mp4",
                            "subfolder": "video",
                            "type": "output",
                        }],
                    }
                },
            }
        }
        return history

    def test_concurrent_posts_do_not_overlap(self):
        events = []
        gate = threading.Lock()

        def fake_post(url, **kwargs):
            self.assertEqual(kwargs.get("timeout"), 5.0)
            with gate:
                events.append(("start", time.monotonic()))
            time.sleep(0.2)
            with gate:
                events.append(("end", time.monotonic()))
            created = MagicMock()
            created.status_code = 200
            created.json.return_value = {"prompt_id": "job", "node_errors": {}}
            return created

        def fake_get(url, **kwargs):
            if str(url).endswith("/view") or "/view" in str(url):
                media = MagicMock()
                media.status_code = 200
                media.content = b"x" * 20
                return media
            return self._history()

        def run(label):
            generate_local_h3_clip("mosque courtyard", "out.mp4", scene_label=label)

        logs = []

        def capture(*args, **_kwargs):
            logs.append(" ".join(str(part) for part in args))

        with patch("visuals.ai_video.providers.minimax_h3.comfy_server_ready", return_value=True), \
                patch("visuals.ai_video.providers.minimax_h3.requests.post", side_effect=fake_post), \
                patch("visuals.ai_video.providers.minimax_h3.requests.get", side_effect=fake_get), \
                patch("visuals.ai_video.providers.minimax_h3.write_bytes", return_value=True), \
                patch("builtins.print", side_effect=capture):
            first = threading.Thread(target=run, args=("Sahne #1",))
            second = threading.Thread(target=run, args=("Sahne #2",))
            first.start()
            time.sleep(0.02)
            second.start()
            first.join(timeout=5)
            second.join(timeout=5)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        ordered = sorted(events, key=lambda row: row[1])
        self.assertEqual([row[0] for row in ordered], ["start", "end", "start", "end"])
        self.assertGreaterEqual(ordered[2][1], ordered[1][1])
        waiting = [line for line in logs if "bekliyor" in line]
        self.assertTrue(waiting)
        self.assertTrue(any("Sahne #1" in line for line in waiting))
        self.assertTrue(any("ComfyUI çalışıyor" in line and "Sahne #1" in line for line in logs))

    def test_poll_names_scene_every_30s(self):
        from visuals.ai_video.providers import minimax_h3 as h3

        clock = {"t": 0.0}

        def fake_time():
            return clock["t"]

        def fake_sleep(seconds):
            clock["t"] += float(seconds)

        pending = MagicMock()
        pending.status_code = 200
        pending.json.return_value = {"job": {"status": {"status_str": "running"}}}
        calls = {"n": 0}

        def fake_get(url, **kwargs):
            calls["n"] += 1
            if calls["n"] < 10:
                return pending
            return self._history()

        logs = []
        with patch.object(h3.time, "time", fake_time), \
                patch.object(h3.time, "sleep", fake_sleep), \
                patch.object(h3.requests, "get", side_effect=fake_get), \
                patch("builtins.print", side_effect=lambda *args, **_kwargs: logs.append(" ".join(str(part) for part in args))):
            found = h3._wait_comfy_video(
                "http://127.0.0.1:8188",
                "job",
                timeout=120,
                scene_label="Sahne #4",
            )
        self.assertIsNotNone(found)
        progress = [
            line for line in logs
            if "Sahne #4" in line and "ComfyUI çalışıyor" in line and "kalan" in line
        ]
        self.assertTrue(progress)
        self.assertLess(clock["t"], 120)

    def test_refused_connection_returns_none_quickly(self):
        def refused(*_args, **_kwargs):
            raise ConnectionError("connection refused")

        started = time.monotonic()
        with patch("visuals.ai_video.providers.minimax_h3.requests.get", side_effect=refused), \
                patch("visuals.ai_video.providers.minimax_h3.requests.post", side_effect=refused):
            path = generate_local_h3_clip("mosque courtyard", "out.mp4", scene_label="Sahne #1")
        elapsed = time.monotonic() - started
        self.assertIsNone(path)
        self.assertLess(elapsed, 5.0)

    def test_queued_scenes_wait_and_all_return(self):
        """A busy ComfyUI is not a dead server. Every scene still gets a clip."""
        n = 4
        results = [None] * n
        events = []
        guard = threading.Lock()
        active_posts = 0
        max_overlap = 0
        busy_probes = 0
        holder_inside_post = threading.Event()

        def fake_get(url, **kwargs):
            nonlocal busy_probes
            target = str(url)
            if target.endswith("/system_stats"):
                with guard:
                    busy = active_posts > 0
                if busy:
                    busy_probes += 1
                    raise TimeoutError("comfy busy")
                ok = MagicMock()
                ok.status_code = 200
                return ok
            if "/history/" in target:
                return self._history()
            if "/view" in target:
                media = MagicMock()
                media.status_code = 200
                media.content = b"x" * 20
                return media
            raise ConnectionError("connection refused")

        def fake_post(url, **kwargs):
            nonlocal active_posts, max_overlap
            self.assertEqual(kwargs.get("timeout"), 5.0)
            with guard:
                active_posts += 1
                max_overlap = max(max_overlap, active_posts)
                events.append(("start", time.monotonic()))
            holder_inside_post.set()
            time.sleep(0.25)
            with guard:
                active_posts -= 1
                events.append(("end", time.monotonic()))
            created = MagicMock()
            created.status_code = 200
            created.json.return_value = {"prompt_id": "job", "node_errors": {}}
            return created

        def run(index):
            results[index] = generate_local_h3_clip(
                "mosque courtyard",
                f"out_{index}.mp4",
                scene_label=f"Sahne #{index + 1}",
            )

        with patch("visuals.ai_video.providers.minimax_h3.comfy_base_url", return_value="http://127.0.0.1:8188"), \
                patch("visuals.ai_video.providers.minimax_h3.requests.post", side_effect=fake_post), \
                patch("visuals.ai_video.providers.minimax_h3.requests.get", side_effect=fake_get), \
                patch("visuals.ai_video.providers.minimax_h3.write_bytes", return_value=True):
            threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
            threads[0].start()
            self.assertTrue(holder_inside_post.wait(2))
            for thread in threads[1:]:
                thread.start()
            for thread in threads:
                thread.join(timeout=8)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(results, [f"out_{i}.mp4" for i in range(n)])
        self.assertEqual(busy_probes, 0)
        self.assertEqual(max_overlap, 1)
        ordered = sorted(events, key=lambda row: row[1])
        self.assertEqual([row[0] for row in ordered], ["start", "end"] * n)
        for index in range(0, len(ordered) - 1, 2):
            self.assertLessEqual(ordered[index + 1][1], ordered[index + 2][1] if index + 2 < len(ordered) else ordered[index + 1][1])

    def test_one_scene_failure_does_not_stop_the_rest(self):
        n = 4
        results = [None] * n
        guard = threading.Lock()
        active_posts = 0
        max_overlap = 0
        post_count = 0

        def fake_get(url, **kwargs):
            target = str(url)
            if target.endswith("/system_stats"):
                with guard:
                    if active_posts > 0:
                        raise TimeoutError("comfy busy")
                ok = MagicMock()
                ok.status_code = 200
                return ok
            if "/history/" in target:
                return self._history()
            if "/view" in target:
                media = MagicMock()
                media.status_code = 200
                media.content = b"x" * 20
                return media
            raise ConnectionError("connection refused")

        def fake_post(url, **kwargs):
            nonlocal active_posts, max_overlap, post_count
            with guard:
                post_count += 1
                this = post_count
                active_posts += 1
                max_overlap = max(max_overlap, active_posts)
            time.sleep(0.05)
            with guard:
                active_posts -= 1
            created = MagicMock()
            if this == 1:
                created.status_code = 500
                created.text = "node exploded"
                return created
            created.status_code = 200
            created.json.return_value = {"prompt_id": "job", "node_errors": {}}
            return created

        def run(index):
            results[index] = generate_local_h3_clip(
                "mosque courtyard",
                f"out_{index}.mp4",
                scene_label=f"Sahne #{index + 1}",
            )

        with patch("visuals.ai_video.providers.minimax_h3.comfy_base_url", return_value="http://127.0.0.1:8188"), \
                patch("visuals.ai_video.providers.minimax_h3.requests.post", side_effect=fake_post), \
                patch("visuals.ai_video.providers.minimax_h3.requests.get", side_effect=fake_get), \
                patch("visuals.ai_video.providers.minimax_h3.write_bytes", return_value=True):
            threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=8)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(post_count, n)
        self.assertEqual(max_overlap, 1)
        self.assertEqual(sum(path is None for path in results), 1)
        self.assertEqual(sum(path is not None for path in results), n - 1)

    def test_auto_visual_mode_does_not_call_h3(self):
        from server_core.render_worker import _fetch_single_scene_visual

        scene = {"visual_mode": "auto", "duration": 4.0, "narration": "merhaba"}
        with patch("visuals.ai_video.providers.minimax_h3.generate_local_h3_clip") as h3, \
                patch("server_core.render_worker.fetch_scene_clip", return_value="stock.mp4"):
            _i, _clip, path = _fetch_single_scene_visual(0, scene, {"visual_mode": "auto"}, "/tmp", 1)
        h3.assert_not_called()
        self.assertEqual(path, "stock.mp4")


class MiniMaxH3StartTests(unittest.TestCase):
    def test_start_endpoint_does_not_spawn_when_port_open(self):
        from fastapi.testclient import TestClient
        from server import app

        with patch("services.minimax_h3_local.comfy_port_open", return_value=True), \
                patch("services.minimax_h3_local.subprocess.Popen") as popen:
            response = TestClient(app).post("/api/system/minimax-h3/start")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "up")
        self.assertTrue(body["already_running"])
        self.assertFalse(body["spawned"])
        popen.assert_not_called()

    def test_start_endpoint_launches_bat_or_venv_python_not_sglang(self):
        from fastapi.testclient import TestClient
        from server import app

        with patch("services.minimax_h3_local.comfy_port_open", return_value=False), \
                patch("services.minimax_h3_local.subprocess.Popen") as popen:
            popen.return_value = MagicMock()
            response = TestClient(app).post("/api/system/minimax-h3/start")
        self.assertEqual(response.status_code, 200)
        argv = list(popen.call_args.args[0])
        joined = " ".join(argv).lower()
        self.assertNotIn("sglang", joined)
        uses_bat = "start_comfy.bat" in joined
        uses_venv = "main.py" in joined and "8188" in joined and "python" in joined
        self.assertTrue(uses_bat or uses_venv)
        body = response.json()
        self.assertEqual(body["status"], "starting")
        self.assertTrue(body["spawned"])
        popen.assert_called_once()


    def test_h3_frame_length_grid(self):
        from visuals.ai_video.providers.minimax_h3 import h3_frame_length
        # 3.0s -> 73 frames (17*4 + 5 = 73, ~3.04s)
        self.assertEqual(h3_frame_length(3.0), 73)
        self.assertEqual(73 % 17, 5)
        # 4.0s -> 107 frames (17*6 + 5 = 107, ~4.45s)
        self.assertEqual(h3_frame_length(4.0), 107)
        self.assertEqual(107 % 17, 5)
        # 5.0s -> 124 frames (17*7 + 5 = 124, ~5.16s)
        self.assertEqual(h3_frame_length(5.0), 124)
        self.assertEqual(124 % 17, 5)

    def test_low_vram_bounds_in_render_worker(self):
        from visuals.ai_video.providers.minimax_h3 import h3_frame_length
        for dur, expected_min, expected_max in [
            (1.0, 73, 124),
            (3.0, 73, 124),
            (4.5, 73, 124),
            (10.0, 73, 124),
        ]:
            frames = h3_frame_length(dur, min_seconds=3.0)
            target = min(124, max(73, frames))
            self.assertGreaterEqual(target, 73)
            self.assertLessEqual(target, 124)
            # Duration in seconds at 24 fps
            seconds = target / 24.0
            self.assertGreaterEqual(seconds, 3.0)
            self.assertLessEqual(seconds, 5.2)


if __name__ == "__main__":
    unittest.main()

