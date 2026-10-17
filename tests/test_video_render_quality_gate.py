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


if __name__ == "__main__":
    unittest.main()
