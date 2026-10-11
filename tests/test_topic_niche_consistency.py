import importlib
import os
import unittest
from pydantic import ValidationError
from unittest.mock import patch

from fastapi import HTTPException

from api_models import ScriptGenerateRequest
from routers.research_router import api_generate_script
from scenes.generator import _build_competitor_fingerprint_block, generate_scenes


class _StopAfterFallback(Exception):
    pass


class TestTopicNicheConsistency(unittest.TestCase):
    def test_niche_request_models_reject_unknown_ids(self):
        from api_models import (
            ContentGapResearchRequest,
            PlanRepairRequest,
            PlanValidateRequest,
            TopicSuggestRequest,
        )

        requests = (
            lambda: ScriptGenerateRequest(keyword="test", niche="unknown"),
            lambda: PlanValidateRequest(plan={}, niche="unknown"),
            lambda: PlanRepairRequest(plan={}, niche="unknown"),
            lambda: ContentGapResearchRequest(raw_topics="test", niche="unknown"),
            lambda: TopicSuggestRequest(niche_id="unknown"),
        )
        for create_request in requests:
            with self.subTest(create_request=create_request):
                with self.assertRaises(ValidationError):
                    create_request()

    def test_competitor_scene_count_obeys_director_speech_limit(self):
        fingerprint = {"scene_count": 12, "hook_style": "Cold open"}

        self.assertIn(
            "Target spoken scene count: 6",
            _build_competitor_fingerprint_block(fingerprint, lang="en"),
        )
        self.assertIn(
            "Hedef konuşma sahnesi sayısı: 6",
            _build_competitor_fingerprint_block(fingerprint, lang="tr"),
        )

    def test_generator_resolves_explicit_niche_against_strong_topic(self):
        title = "Marcus Aurelius stoacı disiplin"
        with (
            patch.dict(os.environ, {"SHORTS_FORCE_PROCEDURAL_FALLBACK": "1"}),
            patch("services.web_fact_researcher.research_topic_facts", return_value=[]),
            patch("services.web_fact_researcher.format_snippet_block", return_value=""),
            patch("services.ollama_provider.is_ollama_available", return_value=False),
            patch(
                "scenes.generator._generate_procedural_fallback_scenes",
                side_effect=_StopAfterFallback,
            ) as fallback,
        ):
            with self.assertRaises(_StopAfterFallback):
                generate_scenes(
                    title,
                    niche_type="13_mystery_paranormal",
                    language="tr",
                )

        self.assertEqual(
            fallback.call_args.kwargs["niche_type"],
            "6_stoic_philosophy",
        )

    def test_research_route_locks_strong_topic_before_generation(self):
        title = "Marcus Aurelius stoacı disiplin"
        research_router = importlib.import_module("routers.research_router")
        with patch.object(
            research_router,
            "generate_scenes",
            side_effect=RuntimeError("stop after observing niche"),
        ) as generate:
            with self.assertRaises(HTTPException):
                api_generate_script(
                    ScriptGenerateRequest(
                        keyword=title,
                        niche="13_mystery_paranormal",
                        language="tr",
                    )
                )

        self.assertEqual(
            generate.call_args.kwargs["niche_type"],
            "6_stoic_philosophy",
        )
