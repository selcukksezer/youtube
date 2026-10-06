"""
Unit tests for Pipeline Audit bilingual semantic matching, audio duration probe handling,
and Pollinations AI circuit breaker resilience.
"""
import os
import tempfile
import unittest
from unittest.mock import patch

from render.pipeline_audit import (
    pre_render_audit,
    audit_search_queries,
    _semantic_overlap,
    _clip_name_tokens,
    _narration_tokens,
    attach_candidate_metadata,
    require_semantic_confidence,
    retry_low_confidence_scenes,
)
from services.pollinations_ai_visual import (
    pollinations_circuit_open,
    trip_pollinations_circuit,
    reset_pollinations_circuit,
    generate_ai_image,
)
from visuals.ai_video.chain import ai_video_enabled, available_providers
from visuals.ai_video.providers.pollinations import PollinationsVideoProvider


class TestPipelineAuditResilience(unittest.TestCase):

    def test_audio_duration_probe_not_failed_when_audio_not_yet_rendered(self):
        """Audio file does not exist yet at visual fetch stage (58%); should not warn probe failed."""
        dummy_clips = [
            {"path": __file__, "duration": 5.0, "narration": "Modern dunyanin gizemleri", "scene_description": "foggy forest night"}
            for _ in range(5)
        ]
        non_existent_audio = "C:/tmp/non_existent_audio_file_12345.wav"
        report = pre_render_audit(dummy_clips, audio_path=non_existent_audio)
        self.assertNotIn("audio_duration_probe_failed", report["warnings"])

    def test_semantic_overlap_bilingual_turkish_narration_with_english_keywords(self):
        """Turkish narration matches English keywords via translation dictionary."""
        clip = {
            "path": "s000_pexels_4761764.mp4",
            "search_queries": ["foggy forest night", "mystery landscape"],
            "scene_description": "gizemli karanlik orman",
            "candidate_title": "modern mystery",
            "narration": "Modern dunyanin aciklayamadigi en ilginc gizem",
        }
        score = _semantic_overlap(clip)
        self.assertGreater(score, 0.0)

    def test_semantic_overlap_verified_clip_has_perfect_score(self):
        """Only provider candidate topic evidence can bypass lexical mismatch."""
        clip = {
            "path": "s001_pexels_9999.mp4",
            "candidate_topic_match_score": 0.95,
            "narration": "Farkli dilde seslendirme",
        }
        score = _semantic_overlap(clip)
        self.assertEqual(score, 1.0)

    def test_existing_mismatched_file_and_query_do_not_count_as_semantic_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            clip_path = os.path.join(temp_dir, "s000_pexels_123.mp4")
            with open(clip_path, "wb") as clip_file:
                clip_file.write(b"x" * 2048)
            clip = {
                "path": clip_path,
                "score": 100,
                "topic_match_score": 1.0,
                "search_queries": ["unrelated ocean waves"],
                "scene_description": "unrelated ocean closeup",
                "candidate_topic_match_score": 0.01,
                "candidate_title": "unrelated ocean waves",
                "narration": "Bitcoin mining uses specialized computers to verify transactions",
            }
            self.assertEqual(_semantic_overlap(clip), 0.0)

    def test_retry_success_passes_and_retry_failure_remains_blocked(self):
        clips = [{
            "path": "existing.mp4",
            "narration": "Bitcoin mining verifies transactions with specialized computers",
            "candidate_topic_match_score": 0.01,
            "candidate_title": "unrelated ocean waves",
        }]

        retried, remaining = retry_low_confidence_scenes(
            clips,
            lambda index, clip: clip.update({
                "path": "matched.mp4",
                "candidate_topic_match_score": 0.72,
            }),
        )
        self.assertEqual(retried, [0])
        self.assertEqual(remaining, [])

        clips[0]["candidate_topic_match_score"] = 0.01
        retried, remaining = retry_low_confidence_scenes(clips, lambda _index, _clip: None)
        self.assertEqual(retried, [0])
        self.assertEqual(remaining, [0])
        with self.assertRaisesRegex(RuntimeError, r"scene\(s\): 1"):
            require_semantic_confidence(remaining)

    def test_manifest_evidence_attaches_only_to_matching_scene_asset(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as clip_file:
            clip = {
                "path": clip_file.name,
                "narration": "Bitcoin mining verifies transactions",
                "score": 100,
                "topic_match_score": 1.0,
                "search_queries": ["bitcoin mining footage"],
            }
            attach_candidate_metadata([clip], [{
                "scene_index": 0,
                "path": clip_file.name,
                "topic_match_score": 0.72,
                "title": "unrelated provider title",
            }])
            self.assertEqual(clip["candidate_topic_match_score"], 0.72)
            self.assertEqual(_semantic_overlap(clip), 1.0)

            attach_candidate_metadata([clip], [{
                "scene_index": 0,
                "path": clip_file.name + ".other",
                "topic_match_score": 0.72,
                "title": "unrelated provider title",
            }])
            self.assertNotIn("candidate_topic_match_score", clip)
            self.assertEqual(_semantic_overlap(clip), 0.0)

    def test_credible_candidate_title_passes_without_mutating_valid_clip(self):
        clip = {
            "path": "s001_pexels_1234.mp4",
            "narration": "Bitcoin mining verifies transactions",
            "candidate_title": "Bitcoin cryptocurrency mining farm",
            "candidate_topic_match_score": 0.0,
        }
        original_path = clip["path"]
        retried, remaining = retry_low_confidence_scenes(
            [clip], lambda _index, _clip: self.fail("credible clip must not be retried"),
        )
        self.assertEqual(retried, [])
        self.assertEqual(remaining, [])
        self.assertEqual(clip["path"], original_path)

    def test_audit_search_queries_with_visual_intent_fallback(self):
        """If search_queries list is omitted in clip_entry, fall back to visual_intent without false failure."""
        dummy_clips = [
            {
                "path": __file__,
                "visual_intent": {"search_queries": ["deep space nebula"], "subject": "space"},
                "narration": "Uzayin derinliklerinde gizli kalmis sirlar",
                "scene_description": "deep space view",
            }
        ]
        result = audit_search_queries(dummy_clips)
        self.assertTrue(result["ok"])


class TestPollinationsCircuitBreaker(unittest.TestCase):

    def setUp(self):
        reset_pollinations_circuit()

    def tearDown(self):
        reset_pollinations_circuit()

    def test_circuit_breaker_trips_and_recovers(self):
        self.assertFalse(pollinations_circuit_open())
        trip_pollinations_circuit(60.0)
        self.assertTrue(pollinations_circuit_open())
        reset_pollinations_circuit()
        self.assertFalse(pollinations_circuit_open())

    @patch("urllib.request.urlopen")
    def test_http_429_immediately_trips_circuit_breaker(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://image.pollinations.ai",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=None,
        )
        self.assertFalse(pollinations_circuit_open())
        success = generate_ai_image("a neon light test", "/tmp/dummy_test_out.jpg")
        self.assertFalse(success)
        self.assertTrue(pollinations_circuit_open())

    def test_pollinations_provider_unavailable_when_circuit_open(self):
        provider = PollinationsVideoProvider()
        self.assertTrue(provider.is_available())
        trip_pollinations_circuit(60.0)
        self.assertFalse(provider.is_available())


if __name__ == "__main__":
    unittest.main()
