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

    assert report["hard_fail"]
    warnings = report["warnings"]
    assert "numeric_source_conflicts:4:24hours" in report["issues"]
    assert any(item.startswith("opening_repeats_title:") for item in warnings)
    assert any(item.startswith("repeated_narration_scenes:2-3") for item in warnings)
    assert any(item.startswith("numeric_claims_not_in_source:4:24hours") for item in warnings)
    assert any(item.startswith("numeric_source_conflicts:4:24hours") for item in warnings)
    assert "ending_is_brief_statement" in warnings
    assert report["story_quality"]["numeric_source_check"] == (
        "numeric, age, year, and date claims only"
    )


def test_story_quality_warns_on_premature_closing_but_ignores_final_scene():
    plan = _plan()
    plan["scenes"][2]["narration"] = (
        "Kısacası, bu kararın sonucu herkesi şaşırttı."
    )
    plan["scenes"][-1]["narration"] = (
        "To sum up, the final choice changed everything."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert "premature_closing_tone:scene_3" in report["warnings"]
    assert report["story_quality"]["premature_closing_scenes"] == [3]


def test_story_quality_warns_when_opening_has_no_curiosity_signal():
    plan = _plan()
    plan["scenes"][0]["narration"] = (
        "A quiet train crossed the valley at sunrise."
    )
    plan["scenes"][1]["narration"] = (
        "The old bridge connected two towns for decades."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert "opening_lacks_curiosity_gap" in report["warnings"]
    assert "opening_lacks_curiosity_gap" not in report["issues"]
    assert report["story_quality"]["opening_has_curiosity_signal"] is False


def test_story_quality_accepts_question_or_contrast_as_opening_curiosity():
    plan = _plan()
    plan["scenes"][0]["narration"] = (
        "**MYSTERIOUS** Nobody knew why the old bridge disappeared."
    )
    plan["scenes"][1]["narration"] = (
        "The answer changed the town's history."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert "opening_lacks_curiosity_gap" not in report["warnings"]
    assert report["story_quality"]["opening_has_curiosity_signal"] is True


def test_story_quality_only_checks_closing_phrases_at_scene_opening():
    plan = _plan()
    plan["scenes"][2]["narration"] = (
        "The source, to sum up, still leaves one important question unanswered."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any(
        warning.startswith("premature_closing_tone:")
        for warning in report["warnings"]
    )
    assert report["story_quality"]["premature_closing_scenes"] == []


def test_story_quality_does_not_guess_fact_support_without_source_text():
    plan = _plan()
    plan.pop("reddit_post")

    report = validate_script_quality(plan)

    assert report["story_quality"]["numeric_source_check"] == "source text unavailable"
    assert not any("numeric_claims_not_in_source" in warning for warning in report["warnings"])
    assert not any("numeric_source_conflicts" in warning for warning in report["warnings"])


def test_unmatched_number_without_source_conflict_stays_advisory():
    plan = _plan()
    plan["reddit_post"]["body"] = "The original post describes a hidden message and a difficult choice."

    report = validate_script_quality(plan)

    assert not any("numeric_source_conflicts" in issue for issue in report["issues"])
    assert any(
        warning.startswith("numeric_claims_not_in_source:")
        and "4:24hours" in warning
        for warning in report["warnings"]
    )


def test_equivalent_time_units_match_source_evidence():
    plan = _plan()
    plan["reddit_post"]["body"] = "The original post says I had 48 hours to decide."
    plan["scenes"][0]["narration"] = (
        "I had 2 days to decide what to do before the wedding plans changed."
    )
    plan["scenes"][3]["narration"] = (
        "The original post describes the decision clearly, but the script changed its meaning."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any("numeric_source_conflicts" in issue for issue in report["issues"])
    assert not any("numeric_claims_not_in_source" in warning for warning in report["warnings"])


def test_time_unit_conversion_still_detects_a_conflicting_claim():
    plan = _plan()
    plan["reddit_post"]["body"] = "The original post says I had 48 hours to decide."
    plan["scenes"][0]["narration"] = (
        "I had 1 day to decide what to do before the wedding plans changed."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert any(
        issue.startswith("numeric_source_conflicts:")
        and "1:1day" in issue
        for issue in report["issues"]
    )


def test_equivalent_distance_units_match_source_evidence():
    plan = _plan()
    plan["reddit_post"]["body"] = "The original post says the road was 2 km long."
    plan["scenes"][0]["narration"] = (
        "The road stretched for 2000 meters before we reached the village."
    )
    plan["scenes"][3]["narration"] = (
        "The original post describes the road and the village we reached."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any("numeric_source_conflicts" in issue for issue in report["issues"])
    assert not any("numeric_claims_not_in_source" in warning for warning in report["warnings"])


def test_spelled_out_english_quantity_matches_numeric_source():
    plan = _plan()
    plan["reddit_post"]["body"] = "The original post says I had 48 hours to decide."
    plan["scenes"][0]["narration"] = (
        "I had two days to decide what to do before the wedding plans changed."
    )
    plan["scenes"][3]["narration"] = (
        "The original post describes the decision clearly, but the script changed its meaning."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any("numeric_source_conflicts" in issue for issue in report["issues"])
    assert not any("numeric_claims_not_in_source" in warning for warning in report["warnings"])


def test_spelled_out_turkish_quantity_conflict_is_hard_fail():
    plan = _plan()
    plan["reddit_post"]["body"] = "Kaynak karar için kırk sekiz saat verildiğini söylüyor."
    plan["scenes"][0]["narration"] = (
        "Karar vermem için yalnızca bir günüm vardı ve bunu sonradan fark ettim."
    )
    plan["scenes"][3]["narration"] = (
        "Kaynakta karar için verilen süre açıkça belirtilmiş ve değiştirilemez."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert report["hard_fail"]
    assert any(
        issue.startswith("numeric_source_conflicts:")
        and "1:birgün" in issue
        for issue in report["issues"]
    )


def test_age_and_year_conflicts_are_reported_separately():
    plan = _plan()
    plan["reddit_post"]["body"] = "I was 29 years old in 2019 when the event happened."
    plan["scenes"][0]["narration"] = (
        "I was 34 years old in 2021 when I learned the truth about the event."
    )
    plan["scenes"][3]["narration"] = (
        "The source clearly describes what happened before the final decision."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert any(
        issue.startswith("age_source_conflicts:") and "1:34years" in issue
        for issue in report["issues"]
    )
    assert any(
        issue.startswith("year_source_conflicts:") and "1:2021" in issue
        for issue in report["issues"]
    )
    assert not any(issue.startswith("numeric_source_conflicts:") for issue in report["issues"])


def test_spelled_out_age_matching_source_is_not_flagged():
    plan = _plan()
    plan["reddit_post"]["body"] = "I was 29 years old in 2019 when the event happened."
    plan["scenes"][0]["narration"] = (
        "I was twenty-nine years old in 2019 when I first understood the event."
    )
    plan["scenes"][3]["narration"] = (
        "The source clearly describes what happened before the final decision."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any(issue.startswith("age_source_conflicts:") for issue in report["issues"])
    assert not any(issue.startswith("year_source_conflicts:") for issue in report["issues"])
    assert not any(warning.startswith("age_claims_not_in_source:") for warning in report["warnings"])


def test_age_and_year_without_source_evidence_remain_advisory():
    plan = _plan()
    plan["reddit_post"]["body"] = "The original post describes a difficult choice."
    plan["scenes"][0]["narration"] = (
        "I was 34 years old in 2021 when I finally understood the difficult choice."
    )
    plan["scenes"][3]["narration"] = (
        "The source describes the choice without stating a date or an age."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any(issue.startswith("age_source_conflicts:") for issue in report["issues"])
    assert not any(issue.startswith("year_source_conflicts:") for issue in report["issues"])
    assert any(warning.startswith("age_claims_not_in_source:") for warning in report["warnings"])
    assert any(warning.startswith("year_claims_not_in_source:") for warning in report["warnings"])


def test_equivalent_full_dates_match_across_iso_and_written_formats():
    plan = _plan()
    plan["reddit_post"]["body"] = "The event happened on 2020-05-03."
    plan["scenes"][0]["narration"] = (
        "The event happened on May 3, 2020, before anyone understood why."
    )
    plan["scenes"][1]["narration"] = (
        "Olay, kimse sebebini anlamadan önce 3 Mayıs 2020 tarihinde yaşandı."
    )
    plan["scenes"][3]["narration"] = (
        "The original post describes what happened before the final decision."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any(issue.startswith("date_source_conflicts:") for issue in report["issues"])
    assert not any(warning.startswith("date_claims_not_in_source:") for warning in report["warnings"])


def test_full_date_conflict_is_hard_fail_even_when_year_matches():
    plan = _plan()
    plan["reddit_post"]["body"] = "The event happened on 2020-05-03."
    plan["scenes"][0]["narration"] = (
        "The event happened on May 4, 2020, before anyone understood why."
    )
    plan["scenes"][3]["narration"] = (
        "The original post describes what happened before the final decision."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert report["hard_fail"]
    assert any(
        issue.startswith("date_source_conflicts:") and "1:2020-05-04" in issue
        for issue in report["issues"]
    )
    assert not any(issue.startswith("year_source_conflicts:") for issue in report["issues"])


def test_full_date_without_source_evidence_remains_advisory():
    plan = _plan()
    plan["reddit_post"]["body"] = "The original post describes a difficult choice."
    plan["scenes"][0]["narration"] = (
        "The event happened on 3 May 2020, before anyone understood why."
    )
    plan["scenes"][3]["narration"] = (
        "The source describes the choice without stating its exact date."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any(issue.startswith("date_source_conflicts:") for issue in report["issues"])
    assert any(
        warning.startswith("date_claims_not_in_source:")
        and "1:2020-05-03" in warning
        for warning in report["warnings"]
    )


def test_equivalent_numeric_dates_match_iso_and_turkish_dotted_formats():
    plan = _plan()
    plan["reddit_post"]["body"] = "The event happened on 2020-05-03."
    plan["scenes"][0]["narration"] = (
        "The event happened on 03.05.2020, before anyone understood why."
    )
    plan["scenes"][3]["narration"] = (
        "The original post describes what happened before the final decision."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any(issue.startswith("date_source_conflicts:") for issue in report["issues"])
    assert not any(warning.startswith("date_claims_not_in_source:") for warning in report["warnings"])


def test_equivalent_numeric_dates_match_iso_dash_and_slash_formats():
    plan = _plan()
    plan["reddit_post"]["body"] = "The event happened on 2020-05-03."
    plan["scenes"][0]["narration"] = (
        "The event happened on 2020/05/03, before anyone understood why."
    )
    plan["scenes"][3]["narration"] = (
        "The original post describes what happened before the final decision."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any(issue.startswith("date_source_conflicts:") for issue in report["issues"])
    assert not any(warning.startswith("date_claims_not_in_source:") for warning in report["warnings"])


def test_slash_iso_date_conflict_is_detected():
    plan = _plan()
    plan["reddit_post"]["body"] = "The event happened on 2020-05-03."
    plan["scenes"][0]["narration"] = (
        "The event happened on 2020/05/04, before anyone understood why."
    )
    plan["scenes"][3]["narration"] = (
        "The original post describes what happened before the final decision."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert any(
        issue.startswith("date_source_conflicts:")
        and "1:2020-05-04" in issue
        for issue in report["issues"]
    )


def test_turkish_dotted_date_conflict_is_detected():
    plan = _plan()
    plan["reddit_post"]["body"] = "The event happened on 2020-05-03."
    plan["scenes"][0]["narration"] = (
        "The event happened on 04.05.2020, before anyone understood why."
    )
    plan["scenes"][3]["narration"] = (
        "The original post describes what happened before the final decision."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert any(
        issue.startswith("date_source_conflicts:")
        and "1:2020-05-04" in issue
        for issue in report["issues"]
    )


def test_ambiguous_numeric_slash_date_is_not_assumed():
    plan = _plan()
    plan["reddit_post"]["body"] = "The event happened on 2020-05-03."
    plan["scenes"][0]["narration"] = (
        "The event happened on 03/05/2020, before anyone understood why."
    )
    plan["scenes"][3]["narration"] = (
        "The original post describes what happened before the final decision."
    )
    plan["full_narration"] = " ".join(
        scene["narration"] for scene in plan["scenes"]
    )

    report = validate_script_quality(plan)

    assert not any(issue.startswith("date_source_conflicts:") for issue in report["issues"])
    assert not any(warning.startswith("date_claims_not_in_source:") for warning in report["warnings"])
