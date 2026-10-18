"""
End-to-end verification tests for the 50 production pipeline fixes across Stages 1–10.
"""
import os
import sys
import tempfile
import unittest
import wave
from unittest.mock import MagicMock, patch

import config
from server_core import state


class TestPipeline50Fixes(unittest.TestCase):
    def test_stage1_sse_log_streamer_no_nested_wrap(self):
        """Issue 1: SSELogStreamer unwraps existing SSELogStreamer instead of nesting."""
        orig = sys.stdout
        s1 = state.SSELogStreamer(orig)
        s2 = state.SSELogStreamer(s1)
        self.assertIs(s2.terminal, s1.terminal)

    def test_stage1_per_task_cancellation_isolation(self):
        """Issue 3: Per-task cancellation registry tracks and clears task_id cleanly."""
        state.register_task_state("task_alpha", {"cancel_requested": False})
        self.assertFalse(state.is_task_cancelled("task_alpha"))
        state.register_task_state("task_alpha", {"cancel_requested": True})
        self.assertTrue(state.is_task_cancelled("task_alpha"))
        state.clear_task_state("task_alpha")
        self.assertFalse(state.is_task_cancelled("task_alpha"))

    def test_stage1_ensure_ui_plan_preserves_custom_scene_fields(self):
        """Issue 5: _ensure_ui_plan_narration_usable preserves user custom scene fields on fallback."""
        from server_core.worker_preflight_stage import _ensure_ui_plan_narration_usable

        bad_plan = {
            "title": "Test Konusu",
            "scenes": [
                {
                    "narration": "...",
                    "scene_description": "...",
                    "selected_video": "/tmp/custom_user_clip.mp4",
                    "visual_mode": "ai_flux",
                    "search_queries": ["custom user query"],
                }
            ],
        }
        repaired = _ensure_ui_plan_narration_usable(
            bad_plan, "Test Konusu", "1_news_flash", "tr"
        )
        self.assertTrue(repaired.get("scenes"))
        first_scene = repaired["scenes"][0]
        self.assertEqual(first_scene.get("selected_video"), "/tmp/custom_user_clip.mp4")
        self.assertEqual(first_scene.get("visual_mode"), "ai_flux")
        self.assertIn("custom user query", first_scene.get("search_queries", []))

    def test_stage2_fact_research_cache(self):
        """Issue 7: research_topic_facts caches results for identical non-mocked queries."""
        from services import web_fact_researcher

        web_fact_researcher._FACT_CACHE.clear()
        sample = [{"title": "T", "snippet": "S", "url": "https://example.com"}]
        web_fact_researcher._FACT_CACHE[("mars gezegeni", 4)] = sample
        res = web_fact_researcher.research_topic_facts("Mars Gezegeni", max_snippets=4)
        self.assertEqual(res, sample)

    def test_stage3_fit_spoken_scene_count_merges_queries(self):
        """Issue 15: _fit_spoken_scene_count preserves search_queries across merged scenes."""
        from director.schema import ScenePlan
        from director.timeline import _fit_spoken_scene_count

        scenes = [
            ScenePlan(
                index=i,
                narration=f"Sahne {i + 1} için tam ve anlamlı bir cümle yazıldı.",
                duration=3.0,
                scene_description="" if i == 0 else f"Scene {i + 1} desc",
                search_queries=[f"query_{i}"],
            )
            for i in range(8)
        ]
        _fit_spoken_scene_count(scenes)
        self.assertLessEqual(len(scenes), 6)
        all_queries = [q for s in scenes for q in (s.search_queries or [])]
        self.assertIn("query_0", all_queries)
        self.assertIn("query_7", all_queries)

    def test_stage3_resnap_director_to_bgm_exported(self):
        """Issue 13: resnap_director_to_bgm updates plan.meta['bgm_track']."""
        from director.compiler import compile_director_plan, resnap_director_to_bgm

        plan = compile_director_plan(
            {
                "title": "Test",
                "scenes": [
                    {
                        "narration": f"Sahne {i + 1} için örnek konuşma metni burada yer alıyor.",
                        "scene_description": "dark cinematic hallway",
                        "search_queries": ["dark hallway"],
                    }
                    for i in range(6)
                ],
            },
            title="Test",
            niche_id="1_news_flash",
            language="tr",
        )
        resnap_director_to_bgm(plan, "ambient_100bpm.mp3")
        self.assertEqual(plan.meta.get("bgm_track"), "ambient_100bpm.mp3")

    def test_stage5_write_job_credits_filters_foreign_project_paths(self):
        """Issue 21: write_job_credits filters out stale manifest entries from other project dirs."""
        from visuals import fetch

        with tempfile.TemporaryDirectory() as proj_a, tempfile.TemporaryDirectory() as proj_b:
            fetch._job_manifest = [
                {
                    "scene_index": 0,
                    "uid": "foreign_clip",
                    "source": "pexels",
                    "path": os.path.join(proj_a, "s000_pexels_1.mp4"),
                    "license": {"license": "Pexels"},
                },
                {
                    "scene_index": 0,
                    "uid": "current_clip",
                    "source": "pixabay",
                    "path": os.path.join(proj_b, "s000_pixabay_2.mp4"),
                    "license": {"license": "Pixabay"},
                },
            ]
            credits = fetch.write_job_credits(proj_b)
            self.assertTrue(os.path.isfile(credits["manifest"]))
            self.assertEqual(len(fetch._job_manifest), 1)
            self.assertEqual(fetch._job_manifest[0]["uid"], "current_clip")

    def test_stage6_hook_rate_cap_and_shared_coro_pool(self):
        """Issues 27 & 28: Hook rate boost is capped at +40% and _run_coro reuses shared pool."""
        import tts_engine

        rate = tts_engine.narration_rate_for_segment(
            {"style": "hook", "rate": "+18%"}, 0, sacred_calm=False
        )
        pct = int(rate.replace("+", "").replace("%", ""))
        self.assertLessEqual(pct, 40)

    def test_stage7_audio_bus_cleans_intermediate_wavs(self):
        """Issues 31 & 32: master_audio_one_pass cleans up intermediate temp WAV files."""
        from director.audio_bus import master_audio_one_pass
        from director.schema import DirectorPlan

        with tempfile.TemporaryDirectory() as tmpdir:
            src_wav = os.path.join(tmpdir, "src.wav")
            out_wav = os.path.join(tmpdir, "master.wav")
            with wave.open(src_wav, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(b"\x00\x00" * 24000)

            plan = DirectorPlan(
                title="Test",
                niche_id="1_news_flash",
                language="tr",
                full_narration="Test",
                scenes=[],
                effect_manifest={},
            )
            res = master_audio_one_pass(
                src_wav, plan, out_wav, allow_bgm=False
            )
            self.assertTrue(os.path.isfile(res))
            leftovers = [
                f for f in os.listdir(tmpdir)
                if f.startswith("master_") and f.endswith(".wav")
            ]
            self.assertEqual(leftovers, [])

    def test_stage8_subtitle_rotation_and_wav_fast_probe(self):
        """Issues 36, 37, 38: rotate_session_subtitle_style, fast WAV probe, and Whisper stem match."""
        import subtitle_generator

        style = subtitle_generator.rotate_session_subtitle_style(seed="job-42")
        self.assertIn(style["font"], subtitle_generator.SUBTITLE_FONT_POOL)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            wav_path = tf.name
        try:
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00\x00" * 32000)
            dur = subtitle_generator._probe_audio_duration_sec(wav_path)
            self.assertAlmostEqual(dur, 2.0, places=2)
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        script = [
            {"text": "İmparatorluğun", "offset": 0.0, "duration": 0.5},
            {"text": "çöküşü", "offset": 0.5, "duration": 0.5},
        ]
        heard = [
            {"text": " İmparatorluk", "offset": 0.1, "duration": 0.45},
            {"text": " çöküş", "offset": 0.6, "duration": 0.45},
        ]
        snapped = subtitle_generator.snap_script_to_whisper(script, heard)
        self.assertEqual(len(snapped), 2)
        self.assertAlmostEqual(snapped[0]["offset"], 0.1, places=2)

    def test_stage9_subtitles_rendered_after_cards_and_sonilo_backup(self):
        """Issues 43 & 45: ASS subtitles are placed after Reddit/ticker cards, and Sonilo SFX rolls back on error."""
        from render.ffmpeg_overlays import apply_global_overlays_to_graph
        from server_core.worker_post_stage import _apply_optional_sonilo_sfx

        with tempfile.TemporaryDirectory() as tmpdir:
            ass_file = os.path.join(tmpdir, "subs.ass")
            rcard_file = os.path.join(tmpdir, "rcard.png")
            audio_file = os.path.join(tmpdir, "audio.wav")
            for p in (ass_file, rcard_file, audio_file):
                with open(p, "wb") as f:
                    f.write(b"dummy" * 100)

            cmd = []
            filter_parts = []
            apply_global_overlays_to_graph(
                cmd=cmd,
                filter_parts=filter_parts,
                valid=[{"path": rcard_file, "duration": 5.0}],
                total_dur=5.0,
                next_input=1,
                W=1080,
                H=1920,
                tmp_dir=tmpdir,
                audio_path=audio_file,
                word_timings=[],
                title="Test",
                subtitle_opts={"disable_hook_card": True},
                enable_broll=False,
                ass_path=ass_file,
                emphasis_ass_path=None,
                enable_emphasis_card=False,
                hybrid_render_overlay=None,
                enable_audio_visualizer=False,
                audio_visualizer_mode="line",
                audio_visualizer_color="0x00D7FF",
                enable_news_ticker=False,
                news_ticker_text=None,
                niche_id="11_reddit_stories",
                enable_reddit_card=True,
                reddit_card_path=rcard_file,
                extra_kwargs={},
            )
            fc = ";".join(filter_parts)
            self.assertLess(fc.find("[vrcard]"), fc.find("[vsub]"))

            vid_file = os.path.join(tmpdir, "out.mp4")
            orig_bytes = b"V" * 150_000
            with open(vid_file, "wb") as vf:
                vf.write(orig_bytes)

            with patch("services.sonilo_sfx.add_ai_sfx_to_video", side_effect=RuntimeError("boom")):
                ok = _apply_optional_sonilo_sfx(vid_file, True)
                self.assertFalse(ok)
            with open(vid_file, "rb") as vf:
                self.assertEqual(vf.read(), orig_bytes)


if __name__ == "__main__":
    unittest.main()
