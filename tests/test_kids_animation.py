"""Kids animation niche: safety filter, mixer bias, stitch, Made for Kids metadata."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from niche_templates import NICHES, get_niche_family, get_niche_scene_structure, get_scenario_pack
from visuals.ai_video.kids_safety import (
    check_kids_prompt_safety,
    is_kids_niche,
    sanitize_kids_prompt,
)
from visuals.ai_video.mixer import VisualSource, mix_weights
from visuals.ai_video.prompt import build_cinematic_prompt
from visuals.ai_video.stitch import clip_count_for_duration, ffmpeg_concat
from visuals.ai_video import chain as ai_chain
from visuals.ai_video.base import AIVideoResult
from compliance.kids_disclosure import apply_kids_upload_fields


class KidsNicheTests(unittest.TestCase):
    def test_niche_registered(self):
        self.assertIn("36_kids_animation", NICHES)
        self.assertTrue(NICHES["36_kids_animation"].get("made_for_kids"))
        self.assertEqual(get_niche_family("36_kids_animation"), "kids")
        pack = get_scenario_pack("36_kids_animation")
        self.assertEqual(pack["max_duration"], 60.0)
        self.assertFalse(pack["allow_shock_queries"])

    def test_scene_structure_kids(self):
        tr = get_niche_scene_structure("36_kids_animation", "tr")
        self.assertIn("Made for Kids", tr)
        self.assertIn("YASAK", tr)


class KidsSafetyTests(unittest.TestCase):
    def test_rejects_real_child_face(self):
        ok, reason = check_kids_prompt_safety("photoreal child face smiling at camera")
        self.assertFalse(ok)
        self.assertIn("unsafe", reason)

    def test_rejects_horror(self):
        ok, _ = check_kids_prompt_safety("jump scare horror demon for kids")
        self.assertFalse(ok)

    def test_allows_soft_animal(self):
        ok, _ = check_kids_prompt_safety("friendly cartoon cat sharing toys in a sunny meadow")
        self.assertTrue(ok)

    def test_prompt_builder_blocks_unsafe(self):
        with self.assertRaises(ValueError):
            build_cinematic_prompt(
                "real child face closeup",
                niche_id="36_kids_animation",
                style_preset="kids_cartoon",
            )

    def test_prompt_builder_kids_style(self):
        p = build_cinematic_prompt(
            "küçük kedi paylaşmayı öğreniyor",
            niche_id="36_kids_animation",
        )
        self.assertIn("kids cartoon", p.lower())
        self.assertNotIn("photoreal lighting", p.lower())

    def test_sanitize_copyright(self):
        s = sanitize_kids_prompt("peppa pig and elsa dance")
        self.assertNotIn("peppa", s.lower())
        self.assertNotIn("elsa", s.lower())


class KidsMixerTests(unittest.TestCase):
    def test_kids_bias_ai_high(self):
        base = mix_weights("general", ai=0.4, stock=0.4, procedural=0.2, ai_available=True)
        kids = mix_weights("36_kids_animation", ai=0.4, stock=0.4, procedural=0.2, ai_available=True)
        self.assertGreater(kids[VisualSource.AI], base[VisualSource.AI])
        self.assertLess(kids[VisualSource.STOCK], base[VisualSource.STOCK])
        self.assertGreater(kids[VisualSource.PROCEDURAL], base[VisualSource.PROCEDURAL])


class StitchTests(unittest.TestCase):
    def test_clip_count_60s(self):
        self.assertEqual(clip_count_for_duration(60, 5), 12)
        self.assertEqual(clip_count_for_duration(5, 5), 1)
        self.assertEqual(clip_count_for_duration(8, 5), 2)

    def test_concat_single_copy(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "a.mp4")
            out = os.path.join(td, "out.mp4")
            with open(src, "wb") as fh:
                fh.write(b"\x00" * 12_000)
            self.assertEqual(ffmpeg_concat([src], out), out)
            self.assertTrue(os.path.isfile(out))


class KidsUploadMetaTests(unittest.TestCase):
    def test_made_for_kids_forced(self):
        meta = apply_kids_upload_fields(
            niche_id="36_kids_animation",
            description="Alfabe şarkısı Short",
            tags=["comment", "alfabe", "subscribe"],
        )
        self.assertTrue(meta["selfDeclaredMadeForKids"])
        self.assertTrue(meta["suppress_pinned_comment"])
        self.assertIn("Made for Kids", meta["description"])
        self.assertNotIn("comment", [t.lower() for t in meta["tags"]])


class KidsAdapterMockTests(unittest.TestCase):
    def _fake_mp4(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"\x00" * 12_000)
        return True

    @patch("visuals.ai_video.providers.runway.download_url")
    @patch("visuals.ai_video.providers.runway.requests.post")
    @patch("visuals.ai_video.providers.runway.requests.get")
    @patch("visuals.ai_video.providers.runway.env_key", return_value="rw_test")
    def test_runway_mock(self, _ek, mock_get, mock_post, mock_dl):
        from visuals.ai_video.providers.runway import RunwayVideoProvider
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"id": "task1"})
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "SUCCEEDED", "output": ["https://example.com/v.mp4"]},
        )
        mock_dl.side_effect = lambda url, path, **kw: self._fake_mp4(path)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "o.mp4")
            res = RunwayVideoProvider().generate("kids cartoon forest", output_path=out)
            self.assertIsNotNone(res)
            self.assertEqual(res.provider, "runway")

    @patch("visuals.ai_video.providers.luma.download_url")
    @patch("visuals.ai_video.providers.luma.requests.post")
    @patch("visuals.ai_video.providers.luma.env_key", return_value="luma_test")
    def test_luma_mock(self, _ek, mock_post, mock_dl):
        from visuals.ai_video.providers.luma import LumaVideoProvider
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "g1", "state": "completed", "assets": {"video": "https://example.com/l.mp4"}},
        )
        mock_dl.side_effect = lambda url, path, **kw: self._fake_mp4(path)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "o.mp4")
            res = LumaVideoProvider().generate("pastel cartoon birds", output_path=out)
            self.assertIsNotNone(res)

    def test_chain_blocks_unsafe_kids(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "x.mp4")
            with patch.object(ai_chain, "ai_video_enabled", return_value=True), \
                 patch.object(ai_chain, "available_providers", return_value=[MagicMock()]):
                res = ai_chain.generate_ai_clip(
                    narration="photoreal child face",
                    niche_id="36_kids_animation",
                    output_path=out,
                )
            self.assertIsNone(res)

    def test_chain_stitches_long_duration(self):
        class FakeProv:
            name = "fake"
            priority = 1
            def is_available(self):
                return True
            def generate(self, prompt, **kw):
                p = kw["output_path"]
                with open(p, "wb") as fh:
                    fh.write(b"\x00" * 12_000)
                return AIVideoResult(path=p, provider="fake", model="m", prompt=prompt)

        def _stub_concat(paths, op):
            with open(op, "wb") as fh:
                fh.write(b"\x00" * 12_000)
            return op

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "long.mp4")
            with patch.object(ai_chain, "ai_video_enabled", return_value=True), \
                 patch.object(ai_chain, "available_providers", return_value=[FakeProv()]), \
                 patch.object(ai_chain, "cache_lookup", return_value=None), \
                 patch.object(ai_chain, "cache_store"), \
                 patch.object(ai_chain, "ffmpeg_concat", side_effect=_stub_concat), \
                 patch.dict(os.environ, {"AI_VIDEO_CLIP_MAX_SEC": "5"}):
                res = ai_chain.generate_ai_clip(
                    narration="friendly cartoon animals learning alphabet",
                    niche_id="36_kids_animation",
                    duration=15.0,
                    output_path=out,
                )
            self.assertIsNotNone(res)
            self.assertIn("stitch", (res.model or ""))


class NicheCountTests(unittest.TestCase):
    def test_at_least_36(self):
        self.assertGreaterEqual(len(NICHES), 36)
        self.assertTrue(is_kids_niche("36_kids_animation"))


if __name__ == "__main__":
    unittest.main()
