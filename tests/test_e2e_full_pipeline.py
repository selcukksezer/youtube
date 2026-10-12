"""End-to-End pipeline integration test suite.
Validates Topic -> DirectorPlan -> VideoRenderRequest -> Safe Output flow.
Addresses Action A4 in pipeline_kriz_analizi.md.
"""
import os
import tempfile
import pytest

from director.compiler import compile_director_plan
from director.schema import DirectorPlan
from api_models import VideoRenderRequest


def test_e2e_plan_compilation():
    """Verify that any viral niche produces a valid DirectorPlan without crashing."""
    plan = compile_director_plan(
        title="Bilinmeyen Gerçekler",
        niche_id="1_news_flash",
        language="tr",
    )
    assert plan is not None
    assert len(plan.scenes) >= 3
    assert plan.hook_text
    assert plan.loop_text
    d = plan.to_dict()
    assert "scenes" in d
    assert isinstance(d["scenes"], list)


def test_e2e_render_request_validation():
    """Verify VideoRenderRequest correctly bundles DirectorPlan payload."""
    plan = compile_director_plan(
        title="Yapay Zeka Devrimi",
        niche_id="4_ai_money_tech",
        language="tr",
    )
    req = VideoRenderRequest(
        keyword="Yapay Zeka Devrimi",
        niche="4_ai_money_tech",
        language="tr",
        tts_voice="tr-TR-AhmetNeural",
        subtitle_preset="capcut_yellow",
        anti_duplicate=True,
        enable_ken_burns=True,
        plan=plan.to_dict(),
    )
    assert req.keyword == "Yapay Zeka Devrimi"
    assert req.niche == "4_ai_money_tech"
    assert req.plan is not None
    assert len(req.plan["scenes"]) >= 3
