"""Unit tests for AI video adapters, failover chain, and visual mixer."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from visuals.ai_video.base import AIVideoResult
from visuals.ai_video.mixer import (
    VisualSource,
    assign_visual_source,
    mix_weights,
    peer_failover_order,
)
from visuals.ai_video.prompt import build_cinematic_prompt
from visuals.ai_video.cache import prompt_hash, cache_store, cache_lookup
from visuals.ai_video import chain as ai_chain
from visuals.ai_video.providers.agnes import AgnesVideoProvider
from visuals.ai_video.providers import ALL_PROVIDER_CLASSES
from visuals.ai_video.providers.fal import FalVideoProvider
from visuals.ai_video.providers.huggingface import HuggingFaceVideoProvider
from visuals.ai_video.providers.replicate import ReplicateVideoProvider
from visuals.ai_video.providers.deepinfra import DeepInfraVideoProvider
from visuals.ai_video.providers.piapi import PiAPIVideoProvider
from visuals.ai_video.providers.higgsfield import (
    HiggsfieldVideoProvider,
    resolve_higgsfield_credentials,
    _clamp_duration,
    _aspect_ratio,
)
from visuals.ai_video.http_util import download_url, write_bytes


class MixerTests(unittest.TestCase):
    def test_weights_normalize(self):
        w = mix_weights(ai=0.4, stock=0.4, procedural=0.2, ai_available=True)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=5)
        self.assertGreater(w[VisualSource.AI], 0)

    def test_ai_disabled_redistributes(self):
        w = mix_weights(ai=0.5, stock=0.3, procedural=0.2, ai_available=False)
        self.assertEqual(w[VisualSource.AI], 0.0)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=5)

    def test_religious_niche_biases_procedural(self):
        base = mix_weights("general", ai=0.4, stock=0.4, procedural=0.2, ai_available=True)
        faith = mix_weights("religious_islam", ai=0.4, stock=0.4, procedural=0.2, ai_available=True)
        self.assertGreater(faith[VisualSource.PROCEDURAL], base[VisualSource.PROCEDURAL])
        self.assertLess(faith[VisualSource.AI], base[VisualSource.AI])

    def test_assign_reproducible_with_seed(self):
        a = [assign_visual_source(i, seed="fixed", ai_available=True) for i in range(12)]
        b = [assign_visual_source(i, seed="fixed", ai_available=True) for i in range(12)]
        self.assertEqual(a, b)
        # Expect variety across 12 scenes
        kinds = {x.value for x in a}
        self.assertGreaterEqual(len(kinds), 2)

    def test_peer_failover_keeps_procedural_last(self):
        order = peer_failover_order(VisualSource.AI, ai_available=True)
        self.assertEqual(order[0], VisualSource.AI)
        self.assertEqual(order[-1], VisualSource.PROCEDURAL)


class PromptTests(unittest.TestCase):
    def test_prompt_blocks_prophet_faces_for_religious(self):
        p = build_cinematic_prompt("Hz. Muhammed hakkında", niche_id="religious")
        self.assertIn("No faces of prophets", p)
        self.assertIn("9:16", p)

    def test_prompt_strips_copyright_chars(self):
        p = build_cinematic_prompt("mickey mouse dancing", niche_id="story")
        self.assertNotIn("mickey", p.lower())


class CacheTests(unittest.TestCase):
    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            key = prompt_hash("hello world", aspect="9:16", duration=5.0)
            src = os.path.join(td, "src.mp4")
            with open(src, "wb") as fh:
                fh.write(b"\x00" * 20_000)
            cache_store(key, src, meta={"ok": True}, base_dir=td)
            dest = os.path.join(td, "out.mp4")
            hit = cache_lookup(key, dest, base_dir=td)
            self.assertTrue(hit)
            self.assertTrue(os.path.isfile(dest))


class HttpUtilityTests(unittest.TestCase):
    def test_successful_download_replaces_destination(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "clip.mp4")
            with open(path, "wb") as fh:
                fh.write(b"previous valid video" * 1000)

            response = MagicMock()
            response.__enter__.return_value = response
            response.iter_content.return_value = [b"new video" * 2000]
            with patch(
                "visuals.ai_video.http_util.requests.get",
                return_value=response,
            ):
                self.assertTrue(download_url("https://example.invalid/clip", path))

            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), b"new video" * 2000)
            self.assertEqual(os.listdir(td), ["clip.mp4"])

    def test_interrupted_download_preserves_existing_destination(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "clip.mp4")
            previous = b"previous valid video" * 1000
            with open(path, "wb") as fh:
                fh.write(previous)

            response = MagicMock()
            response.__enter__.return_value = response

            def interrupted_chunks(chunk_size):
                yield b"x" * chunk_size
                raise OSError("simulated interrupted transfer")

            response.iter_content.side_effect = interrupted_chunks
            with patch(
                "visuals.ai_video.http_util.requests.get",
                return_value=response,
            ):
                self.assertFalse(download_url("https://example.invalid/clip", path))

            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), previous)
            self.assertEqual(os.listdir(td), ["clip.mp4"])

    def test_successful_bytes_replace_destination(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "clip.mp4")
            data = b"new video" * 2000
            with open(path, "wb") as fh:
                fh.write(b"previous valid video" * 1000)

            self.assertTrue(write_bytes(data, path))

            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), data)
            self.assertEqual(os.listdir(td), ["clip.mp4"])

    def test_rejected_small_bytes_preserve_existing_destination(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "clip.mp4")
            previous = b"previous valid video" * 1000
            with open(path, "wb") as fh:
                fh.write(previous)

            self.assertFalse(write_bytes(b"too small", path))

            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), previous)
            self.assertEqual(os.listdir(td), ["clip.mp4"])


class AdapterMockTests(unittest.TestCase):
    def _fake_mp4(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"\x00" * 12_000)
        return True

    @patch("visuals.ai_video.providers.agnes.download_url")
    @patch("visuals.ai_video.providers.agnes.requests.get")
    @patch("visuals.ai_video.providers.agnes.requests.post")
    @patch(
        "visuals.ai_video.providers.agnes.env_key",
        side_effect=lambda *names: {
            "AGNES_API_KEY": "agnes-test-key",
            "AGNES_BASE_URL": "https://agnes.example/v1",
            "AGNES_VIDEO_MODEL": "agnes-video-2.5-flash",
        }.get(names[0], ""),
    )
    def test_agnes_video_25_adapter(self, _env_key, mock_post, mock_get, mock_dl):
        mock_post.return_value = MagicMock(
            status_code=202,
            json=lambda: {"video_id": "task-test-123"},
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "completed", "data": {"video_url": "https://example.com/a.mp4"}},
        )
        mock_dl.return_value = True
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "agnes.mp4")
            result = AgnesVideoProvider().generate(
                "cinematic mountain sunrise",
                duration=15,
                aspect="portrait",
                seed=17,
                output_path=out,
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.provider, "agnes")
            self.assertEqual(result.model, "agnes-video-2.5-flash")
            self.assertEqual(result.duration, 12.0)
            self.assertEqual(result.aspect, "9:16")
            submit_args = mock_post.call_args
            self.assertEqual(submit_args.args[0], "https://agnes.example/v1/videos")
            self.assertEqual(submit_args.kwargs["headers"]["Authorization"], "Bearer agnes-test-key")
            payload = submit_args.kwargs["json"]
            self.assertEqual(payload["mode"], "text")
            self.assertEqual(payload["seconds"], "12")
            self.assertEqual(payload["size"], "720P")
            self.assertEqual(payload["aspect_ratio"], "9:16")
            self.assertEqual(payload["seed"], 17)
            self.assertNotIn("width", payload)
            self.assertNotIn("num_frames", payload)
            poll_url = mock_get.call_args.args[0]
            self.assertIn("video_id=task-test-123", poll_url)
            self.assertIn("model_name=agnes-video-2.5-flash", poll_url)
            mock_dl.assert_called_once_with("https://example.com/a.mp4", out)
            _env_key.assert_any_call("AGNES_API_KEY")

    def test_agnes_availability_requires_explicit_api_key(self):
        self.assertIn(AgnesVideoProvider, ALL_PROVIDER_CLASSES)
        with patch("visuals.ai_video.providers.agnes.env_key", return_value=""):
            self.assertFalse(AgnesVideoProvider().is_available())
        with patch(
            "visuals.ai_video.providers.agnes.env_key",
            side_effect=lambda *names: "agnes-test-key" if names[0] == "AGNES_API_KEY" else "",
        ):
            self.assertTrue(AgnesVideoProvider().is_available())

    @patch("visuals.ai_video.providers.agnes.download_url", return_value=True)
    @patch("visuals.ai_video.providers.agnes.requests.get")
    @patch("visuals.ai_video.providers.agnes.requests.post")
    @patch(
        "visuals.ai_video.providers.agnes.env_key",
        side_effect=lambda *names: {
            "AGNES_API_KEY": "agnes-key-1",
            "AGNES_API_KEY_2": "agnes-key-2",
            "AGNES_BASE_URL": "https://agnes.example/v1",
            "AGNES_VIDEO_MODEL": "agnes-video-2.5-flash",
        }.get(names[0], ""),
    )
    def test_agnes_rotates_keys_after_submit_and_poll_429(
        self, _env_key, mock_post, mock_get, mock_dl
    ):
        mock_post.side_effect = [
            MagicMock(status_code=429, text="rate limited"),
            MagicMock(status_code=202, json=lambda: {"video_id": "task-rotated"}),
        ]
        mock_get.side_effect = [
            MagicMock(status_code=429, text="rate limited"),
            MagicMock(
                status_code=200,
                json=lambda: {"status": "completed", "url": "https://example.com/rotated.mp4"},
            ),
        ]
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "agnes-rotated.mp4")
            result = AgnesVideoProvider().generate(
                "cinematic mountain sunrise",
                output_path=out,
            )

        self.assertIsNotNone(result)
        submit_auth = [call.kwargs["headers"]["Authorization"] for call in mock_post.call_args_list]
        poll_auth = [call.kwargs["headers"]["Authorization"] for call in mock_get.call_args_list]
        self.assertEqual(submit_auth, ["Bearer agnes-key-1", "Bearer agnes-key-2"])
        self.assertEqual(poll_auth, ["Bearer agnes-key-2", "Bearer agnes-key-1"])
        mock_dl.assert_called_once_with("https://example.com/rotated.mp4", out)
        _env_key.assert_any_call("AGNES_API_KEY_2")

    @patch("visuals.ai_video.providers.fal.download_url")
    @patch("visuals.ai_video.providers.fal.requests.post")
    @patch("visuals.ai_video.providers.fal.env_key", return_value="test-fal-key")
    def test_fal_adapter(self, _ek, mock_post, mock_dl):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"video": {"url": "https://example.com/v.mp4"}},
        )
        mock_dl.side_effect = lambda url, path, **kw: self._fake_mp4(path)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "o.mp4")
            res = FalVideoProvider().generate("cinematic ocean", output_path=out)
            self.assertIsNotNone(res)
            self.assertEqual(res.provider, "fal")

    @patch("visuals.ai_video.providers.replicate.download_url")
    @patch("visuals.ai_video.providers.replicate.requests.post")
    @patch("visuals.ai_video.providers.replicate.env_key", side_effect=lambda *n: "r8_test" if "REPLICATE" in n[0] else "")
    def test_replicate_adapter(self, _ek, mock_post, mock_dl):
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"status": "succeeded", "output": "https://example.com/r.mp4"},
        )
        mock_dl.side_effect = lambda url, path, **kw: self._fake_mp4(path)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "o.mp4")
            # Force token available
            with patch.object(ReplicateVideoProvider, "is_available", return_value=True):
                with patch("visuals.ai_video.providers.replicate.env_key", return_value="r8_test"):
                    res = ReplicateVideoProvider().generate("neon city", output_path=out)
            self.assertIsNotNone(res)

    @patch("visuals.ai_video.providers.deepinfra.decode_data_uri")
    @patch("visuals.ai_video.providers.deepinfra.requests.post")
    @patch("visuals.ai_video.providers.deepinfra.env_key", return_value="di_test")
    def test_deepinfra_adapter(self, _ek, mock_post, mock_dec):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"video_url": "data:video/mp4;base64,AAAA"},
        )
        mock_dec.side_effect = lambda uri, path: self._fake_mp4(path)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "o.mp4")
            res = DeepInfraVideoProvider().generate("lake sunrise", output_path=out)
            self.assertIsNotNone(res)

    @patch("visuals.ai_video.providers.piapi.download_url")
    @patch("visuals.ai_video.providers.piapi.requests.post")
    @patch("visuals.ai_video.providers.piapi.env_key", return_value="pi_test")
    def test_piapi_adapter(self, _ek, mock_post, mock_dl):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": {"status": "completed", "video_url": "https://example.com/k.mp4"}},
        )
        mock_dl.side_effect = lambda url, path, **kw: self._fake_mp4(path)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "o.mp4")
            res = PiAPIVideoProvider().generate("drone lighthouse", output_path=out)
            self.assertIsNotNone(res)

    @patch("visuals.ai_video.providers.huggingface.write_bytes")
    @patch("visuals.ai_video.providers.huggingface.requests.post")
    @patch("visuals.ai_video.providers.huggingface.env_key", return_value="hf_test")
    def test_huggingface_adapter_http(self, _ek, mock_post, mock_wb):
        mock_post.return_value = MagicMock(
            status_code=200,
            headers={"content-type": "video/mp4"},
            content=b"\x00" * 12_000,
            text="",
        )
        mock_wb.side_effect = lambda data, path: self._fake_mp4(path)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "o.mp4")
            # Avoid requiring huggingface_hub
            with patch.dict("sys.modules", {"huggingface_hub": None}):
                res = HuggingFaceVideoProvider().generate("walking street", output_path=out)
            self.assertIsNotNone(res)

    def test_higgsfield_credentials_combined(self):
        with patch.dict(os.environ, {
            "HIGGSFIELD_CREDENTIALS": "kid123:secret456",
            "HIGGSFIELD_API_KEY_ID": "",
            "HIGGSFIELD_API_KEY_SECRET": "",
            "HF_API_KEY_ID": "",
            "HF_API_KEY_SECRET": "",
            "HF_CREDENTIALS": "",
        }, clear=False):
            # Clear competing names via env_key path — patch env_key
            with patch(
                "visuals.ai_video.providers.higgsfield.env_key",
                side_effect=lambda *names: (
                    "kid123:secret456" if "CREDENTIALS" in names[0] else ""
                ),
            ):
                kid, secret = resolve_higgsfield_credentials()
            self.assertEqual(kid, "kid123")
            self.assertEqual(secret, "secret456")

    def test_higgsfield_duration_and_aspect(self):
        self.assertEqual(_clamp_duration(2.0), 4)
        self.assertEqual(_clamp_duration(12.0), 12)
        self.assertEqual(_clamp_duration(99.0), 30)
        self.assertEqual(_aspect_ratio("9:16"), "9:16")
        self.assertEqual(_aspect_ratio("portrait"), "9:16")

    @patch("visuals.ai_video.providers.higgsfield.download_url")
    @patch("visuals.ai_video.providers.higgsfield.requests.get")
    @patch("visuals.ai_video.providers.higgsfield.requests.post")
    @patch(
        "visuals.ai_video.providers.higgsfield.resolve_higgsfield_credentials",
        return_value=("kid", "secret"),
    )
    def test_higgsfield_adapter_poll(self, _cred, mock_post, mock_get, mock_dl):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "status": "queued",
                "request_id": "req-1",
                "status_url": "https://api.higgsfield.ai/requests/req-1/status",
            },
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "status": "completed",
                "request_id": "req-1",
                "video": {"url": "https://cdn.example.com/h.mp4"},
            },
        )
        mock_dl.side_effect = lambda url, path, **kw: self._fake_mp4(path)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "o.mp4")
            res = HiggsfieldVideoProvider().generate(
                "cartoon fox in forest",
                duration=5.0,
                aspect="9:16",
                output_path=out,
            )
            self.assertIsNotNone(res)
            self.assertEqual(res.provider, "higgsfield")
            self.assertIn("seedance", res.model)
            mock_post.assert_called()
            args, kwargs = mock_post.call_args
            self.assertIn("Authorization", kwargs["headers"])
            self.assertTrue(kwargs["headers"]["Authorization"].startswith("Key kid:secret"))
            self.assertEqual(kwargs["json"]["aspect_ratio"], "9:16")
            self.assertFalse(kwargs["json"]["generate_audio"])


class ChainFailoverTests(unittest.TestCase):
    def test_chain_tries_second_provider(self):
        ok = AIVideoResult(path="", provider="b", model="m", prompt="p")

        class A:
            name = "a"
            priority = 1
            def is_available(self):
                return True
            def generate(self, *a, **k):
                return None

        class B:
            name = "b"
            priority = 2
            def is_available(self):
                return True
            def generate(self, prompt, **kw):
                p = kw["output_path"]
                with open(p, "wb") as fh:
                    fh.write(b"\x00" * 12_000)
                return AIVideoResult(path=p, provider="b", model="m", prompt=prompt)

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "clip.mp4")
            with patch.object(ai_chain, "ai_video_enabled", return_value=True), \
                 patch.object(ai_chain, "available_providers", return_value=[A(), B()]), \
                 patch.object(ai_chain, "cache_lookup", return_value=None), \
                 patch.object(ai_chain, "cache_store"):
                res = ai_chain.generate_ai_clip(narration="test", output_path=out)
            self.assertIsNotNone(res)
            self.assertEqual(res.provider, "b")


@unittest.skipUnless(
    any(os.getenv(k) for k in (
        "FAL_API_KEY", "FAL_KEY", "HF_TOKEN", "REPLICATE_API_TOKEN",
        "DEEPINFRA_TOKEN", "PIAPI_KEY", "LOCAL_AI_VIDEO_URL",
        "HIGGSFIELD_CREDENTIALS", "HIGGSFIELD_API_KEY_ID", "HF_API_KEY_ID",
    )),
    "live AI video keys not set",
)
class LiveSmokeTest(unittest.TestCase):
    def test_live_one_provider(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "live.mp4")
            res = ai_chain.generate_ai_clip(
                narration="calm ocean waves at sunset",
                scene_description="aerial ocean",
                duration=5.0,
                output_path=out,
            )
            self.assertIsNotNone(res)
            self.assertTrue(os.path.isfile(res.path))
            self.assertGreater(os.path.getsize(res.path), 10_000)


if __name__ == "__main__":
    unittest.main()
