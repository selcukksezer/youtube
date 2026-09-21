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
from visuals.ai_video.providers.fal import FalVideoProvider
from visuals.ai_video.providers.huggingface import HuggingFaceVideoProvider
from visuals.ai_video.providers.replicate import ReplicateVideoProvider
from visuals.ai_video.providers.deepinfra import DeepInfraVideoProvider
from visuals.ai_video.providers.piapi import PiAPIVideoProvider


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


class AdapterMockTests(unittest.TestCase):
    def _fake_mp4(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"\x00" * 12_000)
        return True

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
