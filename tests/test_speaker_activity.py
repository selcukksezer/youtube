from services.speaker_activity import classify_activity, normalise_activity


def test_balanced_mouth_activity_selects_conversation_layout():
    result = classify_activity(
        [(10, 1), (8, 1), (1, 10), (1, 8), (9, 1), (1, 9)]
    )

    assert result.is_conversation
    assert result.dominant_speaker == 0
    assert result.speaker_shares == (0.5, 0.5)
    assert result.windows_analyzed == 6


def test_dominant_mouth_activity_selects_single_speaker_crop():
    activity = [
        (10, 1), (9, 1), (8, 1), (7, 1), (6, 1),
        (5, 1), (4, 1), (3, 1), (1, 8),
    ]
    result = classify_activity(activity)

    assert not result.is_conversation
    assert result.dominant_speaker == 0
    assert result.speaker_shares[0] > 0.8


def test_silent_windows_and_ambiguous_mouth_motion_do_not_vote():
    result = classify_activity(
        [(10, 1), (1, 10), (5, 5), (10, 1)],
        loudness=[0.01, 0.01, 1.0, 1.0],
    )

    assert result.speaker_shares == (1.0, 0.0)
    assert not result.is_conversation


def test_normalise_activity_handles_empty_and_flat_signals():
    assert normalise_activity([]) == []
    assert normalise_activity([(4, 4)] * 3) == [(0.0, 0.0)] * 3
