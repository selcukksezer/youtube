"""API tests for the authoritative pre-render script quality gate."""
import os
import sys
import unittest
import importlib
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from server import app
from server_core import state

video_router = importlib.import_module("routers.video_router")


def _valid_plan():
    narrations = [
        "Stoacılar öfkeyi bastırmak yerine önce onun hangi düşünceden doğduğunu dikkatle inceler ve tepki vermeden önce kendilerine kısa bir düşünme alanı açar.",
        "Kontrol edemediğin olaylara enerji harcamak yerine kendi kararlarına ve tepkilerine odaklan; böylece dış koşullar değişirken iç disiplinini koruyabilirsin.",
        "Marcus Aurelius her sabah zorlukları hatırlayarak günün sürprizlerine zihnini hazırlardı ve karşılaştığı her insanın kendi mücadelesi olduğunu kendine anımsatırdı.",
        "Bir engel çıktığında hedefi bırakma; yöntemi değiştir ve ilerlemek için yeni bir yol ara, çünkü direnç bazen doğru yönü gösteren işarettir.",
        "Başkalarının davranışları senin seçimin değildir, fakat onlara nasıl karşılık verdiğin sana aittir; bu ayrımı korumak gereksiz çatışmaları azaltır.",
        "Bugün küçük bir doğru karar vermek, uzun vadede karakterini ve alışkanlıklarını yeniden şekillendirir; tutarlı seçimler zamanla güvenilir bir yaşam kurar.",
    ]
    return {
        "title": "Stoacı düşünce",
        "scenes": [
            {
                "narration": narration,
                "duration": 8,
                "scene_description": f"Distinct cinematic scene showing stoic practice number {index + 1}",
                "search_queries": [f"stoic practice {index}", f"roman philosophy {index}"],
            }
            for index, narration in enumerate(narrations)
        ],
    }


def _hard_fail_plan():
    return {
        "title": "Incomplete script",
        "scenes": [
            {
                "narration": "Kısa bir anlatım.",
                "duration": 6,
                "scene_description": "A short scene description for testing",
                "search_queries": ["short scene", "test scene"],
            }
        ],
        "meta": {"script_quality": {"hard_fail": False}},
    }


class TestVideoRenderQualityGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        state.is_rendering_active = False
        self.provider_patch = patch(
            "scenes.generator._configured_script_providers",
            return_value=[],
        )
        self.provider_patch.start()

    def tearDown(self):
        self.provider_patch.stop()
        state.is_rendering_active = False

    def test_background_task_enqueue_failure_releases_render_state(self):
        from api_models import VideoRenderRequest

        class FailingBackgroundTasks:
            def add_task(self, *_args, **_kwargs):
                raise RuntimeError("queue unavailable")

        with self.assertRaisesRegex(RuntimeError, "queue unavailable"):
            video_router.api_render_video(
                VideoRenderRequest(keyword="test"),
                FailingBackgroundTasks(),
            )

        self.assertFalse(state.is_rendering_active)
        lock_acquired = state.render_lock.acquire(blocking=False)
        self.assertTrue(lock_acquired)
        if lock_acquired:
            state.render_lock.release()

    def test_hard_fail_is_rejected_before_task_or_render_lock(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": _hard_fail_plan()},
            )

        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertEqual(detail["message"], "Senaryo üretim kalite kapısından geçemedi.")
        self.assertTrue(detail["script_quality"]["hard_fail"])
        self.assertTrue(any(
            issue.startswith("word_count_out_of_band:")
            for issue in detail["script_quality"]["issues"]
        ))
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)
        lock_acquired = state.render_lock.acquire(blocking=False)
        self.assertTrue(lock_acquired)
        if lock_acquired:
            state.render_lock.release()

    def test_non_list_scenes_are_rejected_before_render_task(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": {"title": "Malformed scenes", "scenes": 7}},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("scenes_invalid", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_non_object_visual_intent_is_rejected_before_render_task(self):
        plan = _valid_plan()
        plan["scenes"][0]["visual_intent"] = "invalid-intent"

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("scene_0_visual_intent_invalid", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_stale_full_narration_is_rejected_before_render_task(self):
        plan = _valid_plan()
        scene_narrations = [
            f"Careful observers notice subtle shifts across scene {index} today."
            for index in range(6)
        ]
        plan["full_narration"] = " ".join(
            ["Careful observers explain meaningful developments across this sequence today."] * 12
        )
        for scene, narration in zip(plan["scenes"], scene_narrations):
            scene["narration"] = narration

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertEqual(quality["word_count"], 54)
        self.assertIn("full_narration_mismatch", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_zero_duration_scene_is_rejected_before_render_task(self):
        plan = _valid_plan()
        for scene in plan["scenes"]:
            scene["duration"] = 10
        plan["scenes"][0]["duration"] = 0

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("scene_0_duration_invalid", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_overlong_single_scene_is_rejected_before_render_task(self):
        plan = _valid_plan()
        for scene in plan["scenes"]:
            scene["duration"] = 0.8
        plan["scenes"][0]["duration"] = 60.01

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("scene_0_duration_invalid", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_string_search_queries_are_rejected_before_render_task(self):
        plan = _valid_plan()
        plan["scenes"][0]["search_queries"] = "fake query string"

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("scene_0_queries_insufficient", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_excessive_search_queries_are_rejected_before_render_task(self):
        plan = _valid_plan()
        plan["scenes"][0]["search_queries"] = [
            f"valid observation query variant {index}"
            for index in range(9)
        ]

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("scene_0_queries_above_8", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_mixed_type_search_queries_are_rejected_before_render_task(self):
        plan = _valid_plan()
        plan["scenes"][0]["search_queries"] = [
            "valid observation query one",
            "valid observation query two",
            {"invalid": "entry"},
        ]

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("scene_0_queries_invalid", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_oversized_caption_emphasis_is_rejected_before_render_task(self):
        plan = _valid_plan()
        plan["scenes"][0]["caption_emphasis"] = [
            f"focus-{index}"
            for index in range(13)
        ]

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn(
            "scene_0_caption_emphasis_above_12",
            quality["issues"],
        )
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_invalid_title_is_rejected_before_render_task(self):
        plan = _valid_plan()
        plan["title"] = "   "

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("title_length_out_of_bounds:0", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_scene_count_above_schema_limit_is_rejected_before_render_task(self):
        plan = _valid_plan()
        narrations = [
            f"Observers notice changes within scene {index} today."
            for index in range(25)
        ]
        plan["full_narration"] = " ".join(narrations)
        plan["scenes"] = [
            {
                "narration": narration,
                "duration": 2,
                "scene_description": (
                    f"Distinct observation setting number {index} with clear context"
                ),
                "search_queries": [
                    f"observation detail {index}",
                    f"behavior change {index}",
                ],
            }
            for index, narration in enumerate(narrations)
        ]

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("scene_count_exceeds_limit:25", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_non_string_narration_is_rejected_before_render_task(self):
        plan = _valid_plan()
        plan["scenes"][0]["narration"] = [
            "Observers notice subtle shifts in behavior and compare every signal before responding."
        ]

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("scene_0_narration_invalid", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_placeholder_narration_is_rejected_before_render_task(self):
        plan = _valid_plan()
        plan["scenes"][0]["narration"] = (
            "Observers describe a placeholder scene that looks vivid and meaningful to viewers today."
        )

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 422)
        quality = response.json()["detail"]["script_quality"]
        self.assertTrue(quality["hard_fail"])
        self.assertIn("scene_0_narration_placeholder", quality["issues"])
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_studio_validation_rejects_non_string_scene_text_before_compile(self):
        plan = _valid_plan()
        plan["scenes"][0]["narration"] = [
            "Observers notice subtle shifts in behavior and compare every signal before responding."
        ]

        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": plan["title"],
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "plan": plan,
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["ok"])
        self.assertTrue(result["script_quality"]["hard_fail"])
        self.assertIn("scene_0_narration_invalid", result["script_quality"]["issues"])
        self.assertIn("scene_0_narration_invalid", result["pre_render_score"]["issues"])

    def test_valid_plan_queues_render_task(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": _valid_plan()},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("status"), "started")
        process_task.assert_called_once()
        self.assertTrue(state.is_rendering_active)

    def test_unsupported_language_is_rejected_before_render_task(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={
                    "keyword": "test",
                    "language": "fr",
                    "plan": _valid_plan(),
                },
            )

        self.assertEqual(response.status_code, 422)
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_blank_keyword_is_rejected_before_render_task(self):
        for keyword in ("", "   "):
            with self.subTest(keyword=repr(keyword)):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={"keyword": keyword},
                    )

                self.assertEqual(response.status_code, 422)
                process_task.assert_not_called()
                self.assertFalse(state.is_rendering_active)

    def test_keyword_is_trimmed_before_task_queueing(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "  Stoacılık  ", "plan": _valid_plan()},
            )

        self.assertEqual(response.status_code, 200)
        queued_request = process_task.call_args.args[0]
        self.assertEqual(queued_request.keyword, "Stoacılık")
        state.is_rendering_active = False

    def test_unsupported_voice_gender_is_rejected_before_render_task(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={
                    "keyword": "test",
                    "plan": _valid_plan(),
                    "voice_gender": "robot",
                },
            )

        self.assertEqual(response.status_code, 422)
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_unknown_tts_voice_is_rejected_before_render_task_without_catalog_fetch(self):
        from tts_voices import list_voices_for_language

        with patch("tts_voices.list_elevenlabs_voices", side_effect=AssertionError):
            with patch.object(video_router, "process_video_task") as process_task:
                response = self.client.post(
                    "/api/video/render",
                    json={
                        "keyword": "test",
                        "plan": _valid_plan(),
                        "tts_voice": "not-a-real-voice",
                    },
                )

        self.assertEqual(response.status_code, 422)
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)
        self.assertTrue(list_voices_for_language("tr"))

    def test_valid_tts_voice_is_normalized_and_auto_means_default(self):
        from api_models import VideoRenderRequest

        voice_request = VideoRenderRequest(
            keyword="test",
            language="tr",
            tts_voice=" tr-TR-AhmetNeural ",
        )
        self.assertEqual(voice_request.tts_voice, "tr-TR-AhmetNeural")
        self.assertIsNone(
            VideoRenderRequest(keyword="test", tts_voice=" auto ").tts_voice
        )

    def test_language_mismatched_tts_voice_is_rejected(self):
        from api_models import VideoRenderRequest
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            VideoRenderRequest(
                keyword="test",
                language="tr",
                tts_voice="en-US-GuyNeural",
            )

    def test_voice_gender_values_are_normalized_and_preserved(self):
        from api_models import VideoRenderRequest

        for gender in ("male", "female", "auto"):
            with self.subTest(gender=gender):
                normalized = VideoRenderRequest(
                    keyword="test",
                    voice_gender=f" {gender.upper()} ",
                )
                self.assertEqual(normalized.voice_gender, gender)
        self.assertIsNone(
            VideoRenderRequest(keyword="test", voice_gender=" ").voice_gender
        )

    def test_tts_preview_rejects_unsupported_voice_gender(self):
        response = self.client.post(
            "/api/tts/preview",
            json={"text": "Test", "voice_gender": "robot"},
        )

        self.assertEqual(response.status_code, 422)

    def test_tts_preview_rejects_unknown_voice_without_remote_catalog_fetch(self):
        with patch("tts_voices.list_elevenlabs_voices", side_effect=AssertionError):
            response = self.client.post(
                "/api/tts/preview",
                json={"text": "Test", "language": "tr", "tts_voice": "unknown"},
            )

        self.assertEqual(response.status_code, 422)

    def test_render_language_is_normalized_before_task_queueing(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={
                    "keyword": "test",
                    "language": " EN ",
                    "plan": _valid_plan(),
                },
            )

        self.assertEqual(response.status_code, 200)
        queued_request = process_task.call_args.args[0]
        self.assertEqual(queued_request.language, "en")

    def test_subtitle_controls_outside_studio_ranges_are_rejected(self):
        for option in (
            {"subtitle_font_size": 39},
            {"subtitle_font_size": 73},
            {"subtitle_y_position": 0.49},
            {"subtitle_y_position": 0.91},
        ):
            with self.subTest(option=option):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            **option,
                        },
                    )

                self.assertEqual(response.status_code, 422)
                process_task.assert_not_called()
                self.assertFalse(state.is_rendering_active)

    def test_subtitle_control_range_boundaries_are_accepted(self):
        for options in (
            {"subtitle_font_size": 40, "subtitle_y_position": 0.5},
            {"subtitle_font_size": 72, "subtitle_y_position": 0.9},
        ):
            with self.subTest(options=options):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            **options,
                        },
                    )

                self.assertEqual(response.status_code, 200)
                queued_request = process_task.call_args.args[0]
                self.assertEqual(queued_request.subtitle_font_size, options["subtitle_font_size"])
                self.assertEqual(queued_request.subtitle_y_position, options["subtitle_y_position"])
                state.is_rendering_active = False

    def test_bgm_volume_outside_safe_range_is_rejected(self):
        for volume in (-0.01, 0.31, 4.0):
            with self.subTest(volume=volume):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            "bgm_volume": volume,
                        },
                    )

                self.assertEqual(response.status_code, 422)
                process_task.assert_not_called()
                self.assertFalse(state.is_rendering_active)

    def test_bgm_volume_safe_range_boundaries_are_accepted(self):
        for volume in (0.0, 0.3):
            with self.subTest(volume=volume):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            "bgm_volume": volume,
                        },
                    )

                self.assertEqual(response.status_code, 200)
                queued_request = process_task.call_args.args[0]
                self.assertEqual(queued_request.bgm_volume, volume)
                state.is_rendering_active = False

    def test_unsupported_resolution_is_rejected_before_render_task(self):
        for resolution in ("4k", "480p", ""):
            with self.subTest(resolution=resolution):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            "resolution": resolution,
                        },
                    )

                self.assertEqual(response.status_code, 422)
                process_task.assert_not_called()
                self.assertFalse(state.is_rendering_active)

    def test_supported_resolutions_are_preserved_when_queued(self):
        for resolution in ("1080p", "720p", "540p"):
            with self.subTest(resolution=resolution):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            "resolution": resolution,
                        },
                    )

                self.assertEqual(response.status_code, 200)
                queued_request = process_task.call_args.args[0]
                self.assertEqual(queued_request.resolution, resolution)
                state.is_rendering_active = False

    def test_resolution_is_normalized_before_task_queueing(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={
                    "keyword": "test",
                    "plan": _valid_plan(),
                    "resolution": " 720P ",
                },
            )

        self.assertEqual(response.status_code, 200)
        queued_request = process_task.call_args.args[0]
        self.assertEqual(queued_request.resolution, "720p")
        state.is_rendering_active = False

    def test_unsupported_subtitle_preset_is_rejected_before_render_task(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={
                    "keyword": "test",
                    "plan": _valid_plan(),
                    "subtitle_preset": "not-a-real-style",
                },
            )

        self.assertEqual(response.status_code, 422)
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_subtitle_preset_is_normalized_and_auto_selection_is_preserved(self):
        from subtitle_generator import SUBTITLE_PRESETS

        self.assertIn("capcut_yellow", SUBTITLE_PRESETS)
        for preset, expected in (
            ("  CAPCUT_YELLOW ", "capcut_yellow"),
            ("", None),
        ):
            with self.subTest(preset=preset):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            "subtitle_preset": preset,
                        },
                    )

                self.assertEqual(response.status_code, 200)
                queued_request = process_task.call_args.args[0]
                self.assertEqual(queued_request.subtitle_preset, expected)
                state.is_rendering_active = False

    def test_unsupported_visual_mode_is_rejected_before_render_task(self):
        for mode in ("warp-engine", "flux_ai"):
            with self.subTest(mode=mode):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            "visual_mode": mode,
                        },
                    )

                self.assertEqual(response.status_code, 422)
                process_task.assert_not_called()
                self.assertFalse(state.is_rendering_active)

    def test_supported_visual_modes_are_normalized_and_queued(self):
        for mode in ("auto", "flux", "whiteboard", "mixed"):
            with self.subTest(mode=mode):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            "visual_mode": f" {mode.upper()} ",
                        },
                    )

                self.assertEqual(response.status_code, 200)
                queued_request = process_task.call_args.args[0]
                self.assertEqual(queued_request.visual_mode, mode)
                state.is_rendering_active = False

    def test_empty_visual_mode_keeps_plan_driven_selection(self):
        from api_models import VideoRenderRequest

        self.assertIsNone(
            VideoRenderRequest(keyword="test", visual_mode="  ").visual_mode
        )

    def test_unsupported_gameplay_category_is_rejected_before_render_task(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={
                    "keyword": "test",
                    "plan": _valid_plan(),
                    "gameplay_category": "made_up_category",
                },
            )

        self.assertEqual(response.status_code, 422)
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_supported_gameplay_categories_are_normalized_and_queued(self):
        from gameplay_pool import GAMEPLAY_CATEGORIES

        for category in GAMEPLAY_CATEGORIES:
            with self.subTest(category=category):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            "gameplay_category": f" {category.upper()} ",
                        },
                    )

                self.assertEqual(response.status_code, 200)
                queued_request = process_task.call_args.args[0]
                self.assertEqual(queued_request.gameplay_category, category)
                state.is_rendering_active = False

    def test_empty_gameplay_category_preserves_automatic_selection(self):
        from api_models import VideoRenderRequest

        self.assertIsNone(
            VideoRenderRequest(keyword="test", gameplay_category=" ").gameplay_category
        )

    def test_invalid_subtitle_colors_are_rejected_before_render_task(self):
        for field, value in (
            ("subtitle_color", "not-a-color"),
            ("subtitle_highlight_color", "#123"),
            ("subtitle_color", "#112233;\ninvalid"),
            ("subtitle_highlight_color", "red;"),
        ):
            with self.subTest(field=field, value=value):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            field: value,
                        },
                    )

                self.assertEqual(response.status_code, 422)
                process_task.assert_not_called()
                self.assertFalse(state.is_rendering_active)

    def test_subtitle_colors_normalize_valid_hex_and_named_values(self):
        from api_models import VideoRenderRequest

        request = VideoRenderRequest(
            keyword="test",
            subtitle_color=" #aAbBcC ",
            subtitle_highlight_color=" YELLOW ",
        )
        self.assertEqual(request.subtitle_color, "#AABBCC")
        self.assertEqual(request.subtitle_highlight_color, "yellow")
        self.assertIsNone(
            VideoRenderRequest(keyword="test", subtitle_color=" ").subtitle_color
        )

    def test_invalid_visualizer_options_are_rejected_before_render_task(self):
        for field, value in (
            ("audio_visualizer_mode", "not-a-mode"),
            ("audio_visualizer_color", "0xFF0000:showwaves=mode=line"),
            ("audio_visualizer_color", "#12AB"),
            ("audio_visualizer_color", "0x00D7FF@1.1"),
        ):
            with self.subTest(field=field, value=value):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            field: value,
                        },
                    )

                self.assertEqual(response.status_code, 422)
                process_task.assert_not_called()
                self.assertFalse(state.is_rendering_active)

    def test_visualizer_options_normalize_supported_values(self):
        from api_models import VideoRenderRequest

        request = VideoRenderRequest(
            keyword="test",
            audio_visualizer_mode=" FREQUENCY_BARS ",
            audio_visualizer_color=" #aAbBcC@0.80 ",
        )
        self.assertEqual(request.audio_visualizer_mode, "frequency_bars")
        self.assertEqual(request.audio_visualizer_color, "0xAABBCC@0.8")
        self.assertEqual(
            VideoRenderRequest(keyword="test").audio_visualizer_color,
            "0x00D7FF",
        )

    def test_audio_mix_values_outside_studio_slider_ranges_are_rejected(self):
        invalid_values = (
            ("duck_attack_ms", 19.9),
            ("duck_attack_ms", 200.1),
            ("duck_release_ms", 49.9),
            ("duck_release_ms", 600.1),
            ("intro_blast", 0.49),
            ("intro_blast", 1.01),
            ("outro_swell_sec", 1.9),
            ("outro_swell_sec", 10.1),
        )
        for field, value in invalid_values:
            with self.subTest(field=field, value=value):
                with patch.object(video_router, "process_video_task") as process_task:
                    response = self.client.post(
                        "/api/video/render",
                        json={
                            "keyword": "test",
                            "plan": _valid_plan(),
                            field: value,
                        },
                    )

                self.assertEqual(response.status_code, 422)
                process_task.assert_not_called()
                self.assertFalse(state.is_rendering_active)

    def test_audio_mix_values_accept_studio_slider_boundaries(self):
        from api_models import VideoRenderRequest

        for field, value in (
            ("duck_attack_ms", 20),
            ("duck_attack_ms", 200),
            ("duck_release_ms", 50),
            ("duck_release_ms", 600),
            ("intro_blast", 0.5),
            ("intro_blast", 1.0),
            ("outro_swell_sec", 2),
            ("outro_swell_sec", 10),
        ):
            with self.subTest(field=field, value=value):
                request = VideoRenderRequest(keyword="test", **{field: value})
                self.assertEqual(getattr(request, field), value)

    def test_render_request_inherits_niche_from_plan_when_not_explicit(self):
        from api_models import VideoRenderRequest

        inferred = VideoRenderRequest(
            keyword="test",
            plan={"niche_id": " 6_STOIC_PHILOSOPHY "},
        )
        self.assertEqual(inferred.niche, "6_stoic_philosophy")
        self.assertIsNone(VideoRenderRequest(keyword="test").niche)

        explicit = VideoRenderRequest(
            keyword="test",
            niche=" Stoic ",
            plan={"niche_id": "1_news_flash"},
        )
        self.assertEqual(explicit.niche, "stoic")

    def test_render_route_queues_the_plan_niche_when_request_omits_it(self):
        plan = _valid_plan()
        plan["niche_id"] = "6_stoic_philosophy"

        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": plan},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(process_task.call_args.args[0].niche, "6_stoic_philosophy")
        state.is_rendering_active = False

    def test_unsupported_render_niche_is_rejected_before_queueing(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={
                    "keyword": "test",
                    "plan": _valid_plan(),
                    "niche": "not-a-real-niche",
                },
            )

        self.assertEqual(response.status_code, 422)
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)

    def test_plan_validation_returns_story_quality_advisories(self):
        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": _valid_plan()["title"],
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "plan": _valid_plan(),
            },
        )

        self.assertEqual(response.status_code, 200)
        story_quality = response.json()["script_quality"]["story_quality"]
        self.assertIn("opening_title_overlap", story_quality)
        self.assertIn("repeated_narration_pairs", story_quality)
        self.assertIn("numeric_source_check", story_quality)
        self.assertIn("ending_style", story_quality)

    def test_studio_validation_reports_non_numeric_scene_duration_without_500(self):
        plan = _valid_plan()
        plan["scenes"][0]["duration"] = "not-a-number"

        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": plan["title"],
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "plan": plan,
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["ok"])
        self.assertTrue(result["script_quality"]["hard_fail"])
        self.assertIn(
            "scene_0_duration_invalid",
            result["script_quality"]["issues"],
        )
        self.assertIn("scene_0_duration_invalid", result["pre_render_score"]["issues"])

    def test_studio_validation_rebuilds_invalid_derived_timing_metadata(self):
        plan = _valid_plan()
        plan["full_narration"] = " ".join(scene["narration"] for scene in plan["scenes"])
        plan["scenes"][0].update({
            "index": "invalid",
            "t0": "not-a-number",
            "t1": "Infinity",
            "beat_hint_ms": "NaN",
        })

        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": plan["title"],
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "plan": plan,
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["script_quality"]["hard_fail"], result["script_quality"]["issues"])
        scene = result["plan"]["scenes"][0]
        self.assertEqual(scene["index"], 0)
        self.assertEqual(scene["t0"], 0.0)
        self.assertGreater(scene["t1"], scene["t0"])
        self.assertIsNone(scene.get("beat_hint_ms"))

    def test_studio_validation_reports_non_list_scenes_without_500(self):
        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": "Malformed scenes",
                "niche": "1_news_flash",
                "plan": {"title": "Malformed scenes", "scenes": 7},
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["ok"])
        self.assertTrue(result["script_quality"]["hard_fail"])
        self.assertIn("scenes_invalid", result["script_quality"]["issues"])

    def test_studio_validation_reports_non_object_visual_intent_without_500(self):
        plan = _valid_plan()
        plan["scenes"][0]["visual_intent"] = "invalid-intent"

        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": plan["title"],
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "plan": plan,
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["ok"])
        self.assertTrue(result["script_quality"]["hard_fail"])
        self.assertIn(
            "scene_0_visual_intent_invalid",
            result["script_quality"]["issues"],
        )
        self.assertIn(
            "scene_0_visual_intent_invalid",
            result["pre_render_score"]["issues"],
        )

    def test_studio_validation_replaces_malformed_query_string_with_real_queries(self):
        plan = _valid_plan()
        plan["full_narration"] = " ".join(scene["narration"] for scene in plan["scenes"])
        plan["scenes"][0]["search_queries"] = "fake query string"
        plan["scenes"][0]["visual_intent"] = {
            "search_queries": "fake nested query",
            "must_exclude": "gore",
        }

        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": plan["title"],
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "plan": plan,
            },
        )

        self.assertEqual(response.status_code, 200)
        quality = response.json()["script_quality"]
        self.assertFalse(quality["hard_fail"], quality["issues"])
        queries = response.json()["plan"]["scenes"][0]["search_queries"]
        self.assertIsInstance(queries, list)
        self.assertGreaterEqual(len(queries), 2)
        self.assertTrue(all(isinstance(query, str) and len(query) > 1 for query in queries))
        intent = response.json()["plan"]["scenes"][0]["visual_intent"]
        self.assertTrue(
            all(len(query) > 1 for query in intent["search_queries"])
        )
        self.assertTrue(all(len(term) > 1 for term in intent["must_exclude"]))


if __name__ == "__main__":
    unittest.main()