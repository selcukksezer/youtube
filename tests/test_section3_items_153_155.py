"""Tests for roadmap audio items 153-155."""
import unittest

from sfx_manager import build_scene_sfx_events


class TestSection3Items153to160(unittest.TestCase):
    def test_items_154_155_and_157_159_place_contextual_effects(self):
        events = build_scene_sfx_events([
            {"duration": 3.0, "narration": "Şok edici gerçek ortaya çıktı. Gerilim arttı, listeyi yaz."},
            {"duration": 2.0, "narration": "İkinci sahne."},
        ])
        self.assertIn({"sound": "sub_impact", "at": 0.0}, events)
        self.assertIn({"sound": "heartbeat", "at": 0.0}, events)
        self.assertIn({"sound": "typewriter", "at": 0.0}, events)
        # Item 155: scene-cut whoosh is now applied by sync_riser_whoosh_transitions()
        # in video_composer (avoids double whoosh), so build_scene_sfx_events must NOT emit it.
        self.assertFalse(any(e["sound"] == "whoosh" for e in events))


if __name__ == "__main__":
    unittest.main()