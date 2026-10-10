from production.quality import validate_script_quality


def _plan():
    narrations = [
        "A hidden message changed the wedding date before I could explain what happened to anyone.",
        "I opened the conversation again and noticed the date did not match the story I had heard.",
        "I opened the conversation again and noticed the date did not match the story I had heard.",
        "The original post says I had 48 hours to decide, but the script claims I had 24 hours.",
        "I asked for an explanation and listened carefully before deciding what I should do next.",
        "I made my final decision after considering facts and trust.",
    ]
    scenes = [
        {
            "narration": narration,
            "duration": 7,
            "scene_description": f"Distinct visual scene illustrating story event {index + 1}",
            "search_queries": [f"story event {index + 1}", f"relationship decision {index + 1}"],
        }
        for index, narration in enumerate(narrations)
    ]
    return {
        "title": "A hidden message changed the wedding date",
        "full_narration": " ".join(narrations),
        "reddit_post": {
            "title": "Original post",
            "body": "The original post says I had 48 hours to decide.",
        },
        "scenes": scenes,
    }


def test_story_quality_reports_title_echo_repetition_source_conflict_and_ending():
    report = validate_script_quality(_plan())

    assert not report["hard_fail"]
    warnings = report["warnings"]
    assert any(item.startswith("opening_repeats_title:") for item in warnings)
    assert any(item.startswith("repeated_narration_scenes:2-3") for item in warnings)
    assert any(item.startswith("numeric_claims_not_in_source:4:24hours") for item in warnings)
    assert any(item.startswith("numeric_source_conflicts:4:24hours") for item in warnings)
    assert "ending_is_brief_statement" in warnings
    assert report["story_quality"]["numeric_source_check"] == "numeric claims only"


def test_story_quality_does_not_guess_fact_support_without_source_text():
    plan = _plan()
    plan.pop("reddit_post")

    report = validate_script_quality(plan)

    assert report["story_quality"]["numeric_source_check"] == "source text unavailable"
    assert not any("numeric_claims_not_in_source" in warning for warning in report["warnings"])
    assert not any("numeric_source_conflicts" in warning for warning in report["warnings"])
