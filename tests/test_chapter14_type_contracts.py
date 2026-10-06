"""
Test Suite for Bölüm 14: Tam Veri Modelleri, Pydantic Şemaları ve Tip Sözleşmeleri (Type Contracts).
Verifies strict runtime validation, boundary checks, and interoperability between director/schema.py and production/plan_contracts.py.
"""
import unittest
from pydantic import ValidationError

from production.plan_contracts import (
    AspectRatio,
    AudioBusSpec,
    LicenseType,
    PublishDirectorPlan,
    QualityGateVerdict,
    SceneIntent,
    SubtitlePage,
    VisualAssetSpec,
    VisualAssetType,
    WordTimestamp,
)
from director.schema import DirectorPlan, DirectorScene, VisualIntent


class TestChapter14TypeContracts(unittest.TestCase):

    def test_aspect_ratio_and_visual_asset_spec(self):
        spec = VisualAssetSpec(
            asset_id="hash_12345",
            asset_type=VisualAssetType.VIDEO,
            local_path="/tmp/test.mp4",
            source_url="https://images.pexels.com/video.mp4",
            provider="pexels",
            license=LicenseType.CC0,
            width=1080,
            height=1920,
            duration_sec=5.0,
            fps=30.0,
            is_safe_for_commercial=True,
        )
        self.assertEqual(spec.asset_type.value, "video")
        self.assertEqual(spec.license.value, "cc0")
        self.assertEqual(spec.width, 1080)

        # Boundary validation: width < 2 must fail
        with self.assertRaises(ValidationError):
            VisualAssetSpec(
                asset_id="fail",
                asset_type=VisualAssetType.VIDEO,
                local_path="/tmp/f.mp4",
                provider="test",
                width=1,
            )

    def test_scene_intent_and_audio_bus_spec(self):
        scene = SceneIntent(
            scene_index=0,
            start_sec=0.0,
            duration_sec=4.2,
            narration_text="Göz teması kurduğunuzda karşı tarafın niyetini anlayabilirsiniz.",
            visual_search_terms=["eye contact portrait", "dark room focus"],
            motion_type="zoom_in",
            transition_in="fade",
        )
        self.assertEqual(scene.scene_index, 0)
        self.assertEqual(scene.duration_sec, 4.2)

        # Negative duration must raise ValidationError
        with self.assertRaises(ValidationError):
            SceneIntent(
                scene_index=0,
                start_sec=0.0,
                duration_sec=0.0,  # gt=0.0 constraint
                narration_text="Hata testi",
            )

        audio_bus = AudioBusSpec(
            tts_voice="tr-TR-AhmetNeural",
            tts_rate=1.1,
            master_lufs_target=-14.0,
        )
        self.assertEqual(audio_bus.master_lufs_target, -14.0)

    def test_publish_director_plan_complete(self):
        plan = PublishDirectorPlan(
            job_id="job_uuid_9999",
            niche_id="7_dark_psychology",
            topic="Göz Temasıyla Karşı Tarafın Gerçek Niyetini Anlama Sanatı",
            aspect_ratio=AspectRatio.PORTRAIT_9_16,
            target_duration_sec=55.0,
            retention_hook_type="cognitive_dissonance",
            loop_bridge_text="Bunu öğrendikten sonra artık insanlara asla eskisi gibi bakmayacaksınız.",
            scenes=[
                SceneIntent(
                    scene_index=i,
                    start_sec=i * 5.0,
                    duration_sec=5.0,
                    narration_text=f"Sahne {i+1} anlatım metni burada yer almaktadır.",
                )
                for i in range(10)
            ],
            audio_bus=AudioBusSpec(),
            subtitle_style="capcut_yellow",
        )
        self.assertEqual(plan.aspect_ratio.value, "9:16")
        self.assertEqual(len(plan.scenes), 10)
        self.assertEqual(plan.target_duration_sec, 55.0)

        # Empty scenes list must fail
        with self.assertRaises(ValidationError):
            PublishDirectorPlan(
                job_id="fail_job",
                niche_id="test",
                topic="Empty test",
                scenes=[],
            )

    def test_subtitles_and_quality_gate_verdict(self):
        word1 = WordTimestamp(word="Göz", start_sec=0.0, end_sec=0.3, confidence=0.98)
        word2 = WordTimestamp(word="teması", start_sec=0.3, end_sec=0.8, confidence=0.99)
        page = SubtitlePage(
            page_index=0,
            start_sec=0.0,
            end_sec=0.8,
            text="Göz teması",
            words=[word1, word2],
            style_name="capcut_yellow",
        )
        self.assertEqual(len(page.words), 2)
        self.assertEqual(page.style_name, "capcut_yellow")

        verdict = QualityGateVerdict(
            job_id="job_uuid_9999",
            passed=True,
            retention_score=89.5,
            audio_lufs_actual=-14.2,
            duplicate_asset_count=0,
            unsafe_license_count=0,
            unrendered_text_count=0,
            warnings=["CTA cümlesi yumuşak geçişle onaylandı."],
        )
        self.assertTrue(verdict.passed)
        self.assertAlmostEqual(verdict.retention_score, 89.5)
        self.assertEqual(len(verdict.warnings), 1)

    def test_interoperability_with_director_schema(self):
        from director.schema import ScenePlan
        # DirectorPlan -> Pydantic PublishDirectorPlan bridge
        director_plan = DirectorPlan(
            title="Bilinmeyen Tarih Gerçekleri",
            niche_id="3_bizarre_history",
            scenes=[
                ScenePlan(
                    index=0,
                    narration="Tarihin en tuhaf olayına tanık olun.",
                    duration=5.0,
                    visual_intent=VisualIntent(subject="ancient temple", mood="mysterious"),
                )
            ],
        )
        # Convert to PublishDirectorPlan
        pydantic_scenes = [
            SceneIntent(
                scene_index=s.index,
                start_sec=s.t0,
                duration_sec=s.duration,
                narration_text=s.narration,
                visual_search_terms=s.search_queries,
            )
            for s in director_plan.scenes
        ]
        pub_plan = PublishDirectorPlan(
            job_id="job_interop_01",
            niche_id=director_plan.niche_id,
            topic=director_plan.title,
            aspect_ratio=AspectRatio.PORTRAIT_9_16,
            target_duration_sec=50.0,
            scenes=pydantic_scenes,
        )
        self.assertEqual(pub_plan.topic, "Bilinmeyen Tarih Gerçekleri")
        self.assertEqual(pub_plan.scenes[0].narration_text, "Tarihin en tuhaf olayına tanık olun.")


if __name__ == "__main__":
    unittest.main()
