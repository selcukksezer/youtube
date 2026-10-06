"""7.3: scene cuts sit on the beat. The last scene keeps the audio length."""
import unittest

from bgm_manager import normalize_bpm_to_shorts_band, snap_durations_to_bpm


class TestChapter7BeatSnap(unittest.TestCase):
    def test_middle_cuts_land_on_beats_and_total_holds(self):
        bpm = 120.0
        beat = 60.0 / bpm
        original = [3.2, 3.2, 3.2]
        snapped = snap_durations_to_bpm(original, bpm)
        self.assertAlmostEqual(sum(snapped), sum(original), places=2)
        acc = 0.0
        for dur in snapped[:-1]:
            acc += dur
            beats = acc / beat
            self.assertAlmostEqual(beats, round(beats), places=2)
        self.assertNotEqual(snapped[0], original[0])

    def test_refuses_a_snap_under_two_seconds(self):
        snapped = snap_durations_to_bpm([2.05, 4.0], 40.0, enforce_band=False)
        self.assertEqual(snapped[0], 2.05)
        self.assertAlmostEqual(sum(snapped), 6.05, places=2)

    def test_octave_fold_keeps_the_kick(self):
        self.assertEqual(normalize_bpm_to_shorts_band(78), 78.0)
        self.assertEqual(normalize_bpm_to_shorts_band(125), 125.0)
        self.assertEqual(normalize_bpm_to_shorts_band(60), 120.0)
        self.assertEqual(normalize_bpm_to_shorts_band(160), 80.0)


if __name__ == "__main__":
    unittest.main()
