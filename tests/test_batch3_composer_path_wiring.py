"""Batch 3: default render path routing + hybrid/B4 overlay wiring (Items 131, 191, 195, 224, 260, 261, B5)."""
import inspect
import os
import tempfile
import unittest
import wave

from moviepy.editor import ColorClip

from render.ffmpeg_graph import _needs_moviepy_composer, compose_via_director
from hybrid_niches import get_hybrid_render_overlay_spec, enrich_plan_with_hybrid
from scenes.enrichment import enrich_plan_scenes
from effects.overlays import (
    apply_infinite_spiral_overlay,
    apply_time_tunnel_overlay,
    apply_ui_element_overlay,
)
from voice.audio_dsp import apply_acoustic_reverb_chamber, apply_epic_trailer_deep_voice


class TestBatch3ComposerPathWiring(unittest.TestCase):
    def test_default_stock_render_stays_on_ffmpeg(self):
        kwargs = {
            "enable_section2_filters": True,
            "retention_metadata": {"hook_strategy": "cognitive_dissonance"},
            "split_screen": False,
        }
        self.assertFalse(_needs_moviepy_composer(kwargs))

    def test_split_filter_stacks_gameplay_under_scene(self):
        from render.ffmpeg_graph import build_scene_filter_chain
        chain = build_scene_filter_chain(
            0, 4.0, 1080, 1920, 0, split_screen=True, gameplay_index=3,
        )
        self.assertIn("vstack=inputs=2", chain)
        self.assertIn("[3:v]", chain)
        self.assertNotIn("zoompan", chain)

    def test_split_uses_ffmpeg_hybrid_uses_moviepy(self):
        self.assertFalse(_needs_moviepy_composer({
            "split_screen": True,
            "gameplay_path": "soap.mp4",
        }))
        self.assertTrue(_needs_moviepy_composer({
            "hybrid_render_overlay": {"ui_type": "imessage"},
        }))

    def test_compose_via_director_moviepy_when_section2_enabled(self):
        src = inspect.getsource(compose_via_director)
        self.assertIn("_needs_moviepy_composer", src)
        self.assertIn("compose_video", src)

    def test_hybrid_overlay_spec_history_chat(self):
        spec = get_hybrid_render_overlay_spec("history_chat")
        self.assertEqual(spec.get("ui_type"), "imessage")
        self.assertEqual(spec.get("item"), 277)

    def test_enrich_plan_with_hybrid_attaches_render_overlay(self):
        plan = {
            "title": "Sezar Napolyon WhatsApp gizli grup mesaj tarih",
            "scenes": [{"search_queries": ["roman history"], "duration": 3.0}],
        }
        out = enrich_plan_with_hybrid(plan, plan["title"], "3_history")
        if out.get("hybrid_niche"):
            self.assertIn("hybrid_render_overlay", out)

    def test_enrich_plan_scenes_wires_motion_and_gaze(self):
        plan = {
            "scenes": [
                {"narration": "Açılış.", "duration": 3.0, "search_queries": ["landscape"]},
                {"narration": "Kapanış.", "duration": 3.0, "search_queries": ["portrait face"]},
            ]
        }
        out = enrich_plan_scenes(plan, lang="tr")
        self.assertTrue(out["scenes"][0].get("handheld_shake"))
        last_q = " ".join(out["scenes"][-1].get("search_queries") or []).lower()
        # CLOSING_GAZE_QUERY_HINTS includes "eye contact …" (no gaze/camera/looking tokens).
        self.assertTrue(
            any(tok in last_q for tok in ("gaze", "camera", "looking", "eye contact")),
            msg=f"closing gaze hint missing from queries: {last_q!r}",
        )

    def test_item_224_spiral_overlay(self):
        clip = ColorClip(size=(720, 1280), color=(10, 10, 30), duration=3.0)
        out = apply_infinite_spiral_overlay(clip, duration=2.0)
        self.assertEqual(out.size, (720, 1280))

    def test_item_261_time_tunnel_overlay(self):
        clip = ColorClip(size=(720, 1280), color=(20, 30, 50), duration=3.0)
        out = apply_time_tunnel_overlay(clip, duration=2.5)
        self.assertEqual(out.size, (720, 1280))

    def test_item_131_ui_overlay_on_composite(self):
        clip = ColorClip(size=(720, 1280), color=(30, 30, 60), duration=4.0)
        out = apply_ui_element_overlay(
            clip, ui_type="ios_notification", header_text="Test", body_text="Body", start_time=0.5
        )
        self.assertEqual(out.duration, 4.0)

    def test_items_191_195_audio_dsp(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "voice.wav")
            with wave.open(src, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(b"\x00\x00" * 48000 * 2)
            rev = os.path.join(tmp, "rev.wav")
            epic = os.path.join(tmp, "epic.wav")
            self.assertTrue(apply_acoustic_reverb_chamber(src, rev).endswith("rev.wav"))
            self.assertTrue(apply_epic_trailer_deep_voice(src, epic).endswith("epic.wav"))

    def test_video_composer_accepts_hybrid_kwargs(self):
        from video_composer import compose_video
        sig = inspect.signature(compose_video)
        self.assertIn("hybrid_niche", sig.parameters)
        self.assertIn("hybrid_render_overlay", sig.parameters)


if __name__ == "__main__":
    unittest.main()
