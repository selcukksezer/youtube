"""
Tests for scenario production contract and fallback quality validation:
Verifies that procedural fallbacks, timeline solving, and quality gates
cooperate seamlessly without false-positive 'words_below_12' hard-fails.
"""
import pytest
from production.quality import (
    MAX_TITLE_LENGTH,
    MAX_HARD_SCENES,
    MIN_TITLE_LENGTH,
    MIN_SCENE_WORDS,
    MIN_WORDS,
    validate_script_quality,
)
from scenes.fallback import _generate_procedural_fallback_scenes
from scenes.narration_validate import (
    HARD_MIN_WORDS_PER_SCENE,
    MIN_PLAN_WORDS,
    plan_narration_usable,
    plan_needs_procedural_inject,
    plan_quality_usable,
    scene_narration_usable,
    scene_narration_issues,
)
from director.compiler import compile_director_plan
from director.quality_gate import check_narration_integrity
from director.schema import DirectorPlan, ScenePlan, shorts_word_budget


def _duration_boundary_plan(total_duration):
    speakers = ("Observers", "Researchers", "Experts", "Leaders", "Artists", "Analysts")
    narrations = [
        f"{speaker} notice subtle shifts in behavior throughout this sequence and "
        "compare every signal before choosing a response today."
        for speaker in speakers
    ]
    return {
        "title": "Careful observation",
        "full_narration": " ".join(narrations),
        "scenes": [
            {
                "narration": narration,
                "duration": total_duration - 5 if index == 0 else 1,
                "scene_description": f"Distinct visual setting showing careful observation {index}",
                "search_queries": [
                    f"observation detail scene {index}",
                    f"behavior shift scene {index}",
                ],
            }
            for index, narration in enumerate(narrations)
        ],
    }


def test_generation_and_render_share_script_quality_boundaries():
    assert HARD_MIN_WORDS_PER_SCENE == MIN_SCENE_WORDS == 7
    assert MIN_PLAN_WORDS == MIN_WORDS == 85

    narrations = [
        f"{speaker} notice subtle shifts in behavior throughout this sequence."
        for speaker in (
            "Observers", "Researchers", "Experts", "Leaders", "Artists",
            "Readers", "Viewers", "Friends", "Analysts", "Travelers",
        )
    ]
    accepted_plan = {
        "title": "Careful observation",
        "scenes": [
            {
                "narration": narration,
                "scene_description": f"Unique visual setting {index} with people observing behavior",
                "search_queries": [
                    f"observation behavior scene {index}",
                    f"people noticing scene {index}",
                ],
                "duration": 5.2,
            }
            for index, narration in enumerate(narrations)
        ],
        "full_narration": " ".join(narrations),
    }

    quality = validate_script_quality(accepted_plan)
    assert quality["word_count"] == 90
    assert not quality["hard_fail"], quality["issues"]
    assert any("words_below_12" in warning for warning in quality["warnings"])
    assert plan_quality_usable(accepted_plan["scenes"])
    assert not plan_needs_procedural_inject(accepted_plan["scenes"])
    assert plan_narration_usable(
        accepted_plan["scenes"], min_words=HARD_MIN_WORDS_PER_SCENE
    )
    assert scene_narration_usable(
        narrations[0], min_words=HARD_MIN_WORDS_PER_SCENE
    )
    director_plan = DirectorPlan(
        title="Observation",
        niche_id="1_news_flash",
        full_narration=accepted_plan["full_narration"],
        scenes=[
            ScenePlan(
                index=index,
                narration=scene["narration"],
                duration=scene["duration"],
                scene_description=scene["scene_description"],
                search_queries=scene["search_queries"],
            )
            for index, scene in enumerate(accepted_plan["scenes"])
        ],
    )
    assert not any(
        issue.startswith("low_words")
        for issue in check_narration_integrity(director_plan)
    )


    seven_word_scene_plan = {
        **accepted_plan,
        "scenes": [dict(scene) for scene in accepted_plan["scenes"]],
    }
    seven_word_scene_plan["scenes"][0]["narration"] = (
        "Careful observers notice subtle shifts in behavior."
    )
    seven_word_scene_plan["full_narration"] = " ".join(
        scene["narration"] for scene in seven_word_scene_plan["scenes"]
    )
    seven_word_quality = validate_script_quality(seven_word_scene_plan)
    assert seven_word_quality["word_count"] == 88
    assert not seven_word_quality["hard_fail"], seven_word_quality["issues"]
    assert plan_quality_usable(seven_word_scene_plan["scenes"])
    assert not plan_needs_procedural_inject(seven_word_scene_plan["scenes"])

    short_scene_plan = {
        **seven_word_scene_plan,
        "scenes": [dict(scene) for scene in seven_word_scene_plan["scenes"]],
    }
    short_scene_plan["scenes"][0]["narration"] = (
        "**URGENT** Careful observers notice subtle shifts today. 🚨"
    )
    short_scene_plan["full_narration"] = " ".join(
        scene["narration"] for scene in short_scene_plan["scenes"]
    )
    short_quality = validate_script_quality(short_scene_plan)
    assert short_quality["word_count"] == 87
    assert short_quality["hard_fail"]
    assert any("words_below_7" in issue for issue in short_quality["issues"])
    assert not plan_quality_usable(short_scene_plan["scenes"])
    assert "low_words" in scene_narration_issues(
        short_scene_plan["scenes"][0]["narration"]
    )

    underfilled_plan = {
        **accepted_plan,
        "scenes": [dict(scene) for scene in accepted_plan["scenes"]],
    }
    for scene in underfilled_plan["scenes"]:
        scene["narration"] = "Observers notice subtle shifts across the sequence today."
    underfilled_plan["full_narration"] = " ".join(
        scene["narration"] for scene in underfilled_plan["scenes"]
    )
    underfilled_quality = validate_script_quality(underfilled_plan)
    assert underfilled_quality["word_count"] == 80
    assert underfilled_quality["hard_fail"]
    assert not plan_quality_usable(underfilled_plan["scenes"])
    assert not plan_needs_procedural_inject(underfilled_plan["scenes"])


@pytest.mark.parametrize(
    ("duration", "hard_fail"),
    ((37.99, True), (38.0, False), (65.0, False), (65.01, True)),
)
def test_duration_limits_report_the_actual_hard_and_target_bands(duration, hard_fail):
    report = validate_script_quality(_duration_boundary_plan(duration))

    assert report["hard_fail"] is hard_fail
    assert report["limits"]["min_duration"] == 38.0
    assert report["limits"]["max_duration"] == 65.0
    assert report["limits"]["target_min_duration"] == 45.0
    assert report["limits"]["target_max_duration"] == 60.0


def test_quality_gate_rejects_stale_full_narration_and_counts_scene_text():
    narrations = [
        f"Careful observers notice subtle shifts across scene {index} today."
        for index in range(6)
    ]
    plan = {
        "full_narration": " ".join(
            ["Careful observers explain meaningful developments across this sequence today."] * 12
        ),
        "scenes": [
            {
                "narration": narration,
                "duration": 50 / 6,
                "scene_description": f"Distinct visual setting showing observation detail {index}",
                "search_queries": [
                    f"observation detail {index}",
                    f"behavior change {index}",
                ],
            }
            for index, narration in enumerate(narrations)
        ],
    }

    report = validate_script_quality(plan)

    assert report["hard_fail"]
    assert report["word_count"] == 54
    assert "full_narration_mismatch" in report["issues"]
    assert "word_count_out_of_band:54" in report["issues"]


@pytest.mark.parametrize(
    "invalid_duration",
    (0, -1, float("nan"), float("inf"), "invalid", True),
)
def test_quality_gate_rejects_invalid_scene_durations(invalid_duration):
    plan = _duration_boundary_plan(50.0)
    for scene in plan["scenes"]:
        scene["duration"] = 10.0
    plan["scenes"][0]["duration"] = invalid_duration

    report = validate_script_quality(plan)

    assert report["hard_fail"]
    assert "scene_0_duration_invalid" in report["issues"]
    assert report["duration"] == 50.0


@pytest.mark.parametrize(
    ("longest_scene", "hard_fail"),
    ((60.0, False), (60.01, True)),
)
def test_quality_gate_enforces_scene_duration_ceiling(longest_scene, hard_fail):
    plan = _duration_boundary_plan(64.0)
    for scene in plan["scenes"]:
        scene["duration"] = 0.8
    plan["scenes"][0]["duration"] = longest_scene

    report = validate_script_quality(plan)

    assert report["hard_fail"] is hard_fail
    assert report["limits"]["max_scene_duration"] == 60.0
    if hard_fail:
        assert "scene_0_duration_invalid" in report["issues"]


@pytest.mark.parametrize(
    "invalid_queries",
    ("fake query string", [1, 2], {"first": "valid query", "second": "another query"}),
)
def test_quality_gate_rejects_malformed_scene_search_queries(invalid_queries):
    plan = _duration_boundary_plan(50.0)
    plan["scenes"][0]["search_queries"] = invalid_queries

    report = validate_script_quality(plan)

    assert report["hard_fail"]
    assert "scene_0_queries_insufficient" in report["issues"]


@pytest.mark.parametrize(
    ("query_count", "hard_fail"),
    ((8, False), (9, True)),
)
def test_quality_gate_enforces_scene_search_query_ceiling(query_count, hard_fail):
    plan = _duration_boundary_plan(50.0)
    plan["scenes"][0]["search_queries"] = [
        f"valid observation search query variant {index}"
        for index in range(query_count)
    ]

    report = validate_script_quality(plan)

    assert report["hard_fail"] is hard_fail
    assert report["limits"]["max_scene_search_queries"] == 8
    if hard_fail:
        assert "scene_0_queries_above_8" in report["issues"]


@pytest.mark.parametrize(
    ("queries", "expected_issues"),
    (
        (
            ["valid observation query one", "valid observation query two", {"bad": "entry"}],
            ["scene_0_queries_invalid"],
        ),
        (
            [f"valid observation query {index}" for index in range(8)] + [False],
            ["scene_0_queries_invalid", "scene_0_queries_above_8"],
        ),
    ),
)
def test_quality_gate_rejects_mixed_type_and_overlong_raw_query_lists(
    queries, expected_issues
):
    plan = _duration_boundary_plan(50.0)
    plan["scenes"][0]["search_queries"] = queries

    report = validate_script_quality(plan)

    assert report["hard_fail"]
    for expected_issue in expected_issues:
        assert expected_issue in report["issues"]


@pytest.mark.parametrize(
    ("field", "values", "maximum"),
    (
        ("claim_ids", [f"claim-{index}" for index in range(13)], 12),
        ("caption_emphasis", [f"focus-{index}" for index in range(13)], 12),
        ("must_exclude", [f"exclude-{index}" for index in range(21)], 20),
    ),
)
def test_quality_gate_enforces_scene_metadata_list_limits(field, values, maximum):
    plan = _duration_boundary_plan(50.0)
    plan["scenes"][0][field] = values

    report = validate_script_quality(plan)

    assert report["hard_fail"]
    assert f"scene_0_{field}_above_{maximum}" in report["issues"]


@pytest.mark.parametrize("field", ("claim_ids", "caption_emphasis", "must_exclude"))
def test_quality_gate_rejects_non_string_scene_metadata_items(field):
    plan = _duration_boundary_plan(50.0)
    plan["scenes"][0][field] = ["valid item", {"invalid": "item"}]

    report = validate_script_quality(plan)

    assert report["hard_fail"]
    assert f"scene_0_{field}_invalid" in report["issues"]


@pytest.mark.parametrize(
    ("title", "expected_issue"),
    (
        (None, "title_invalid"),
        (1234, "title_invalid"),
        ("abc", "title_length_out_of_bounds:3"),
        ("   ", "title_length_out_of_bounds:0"),
        ("x" * (MAX_TITLE_LENGTH + 1), f"title_length_out_of_bounds:{MAX_TITLE_LENGTH + 1}"),
    ),
)
def test_quality_gate_rejects_invalid_title(title, expected_issue):
    plan = _duration_boundary_plan(50.0)
    plan["title"] = title

    report = validate_script_quality(plan)

    assert report["hard_fail"]
    assert expected_issue in report["issues"]
    assert report["limits"]["min_title_length"] == MIN_TITLE_LENGTH
    assert report["limits"]["max_title_length"] == MAX_TITLE_LENGTH


@pytest.mark.parametrize("title", ("Good", "x" * MAX_TITLE_LENGTH))
def test_quality_gate_accepts_title_length_boundaries(title):
    plan = _duration_boundary_plan(50.0)
    plan["title"] = title

    report = validate_script_quality(plan)

    assert not report["hard_fail"], report["issues"]


@pytest.mark.parametrize(
    ("scene_count", "hard_fail"),
    ((24, False), (25, True)),
)
def test_quality_gate_enforces_hard_scene_count_ceiling(scene_count, hard_fail):
    narrations = [
        f"Observers notice changes within scene {index} today."
        for index in range(scene_count)
    ]
    plan = {
        "title": "Careful observations",
        "full_narration": " ".join(narrations),
        "scenes": [
            {
                "narration": narration,
                "duration": 50.0 / scene_count,
                "scene_description": (
                    f"Distinct observation setting number {index} with clear context"
                ),
                "search_queries": [
                    f"observation detail {index}",
                    f"behavior change {index}",
                ],
            }
            for index, narration in enumerate(narrations)
        ],
    }

    report = validate_script_quality(plan)

    assert report["hard_fail"] is hard_fail
    assert report["limits"]["hard_max_scenes"] == MAX_HARD_SCENES
    if hard_fail:
        assert f"scene_count_exceeds_limit:{scene_count}" in report["issues"]


