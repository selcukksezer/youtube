"""Tests for split-screen gameplay pool dedup and categories."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import gameplay_pool as gp


class TestGameplayPool(unittest.TestCase):
    def setUp(self):
        self._orig_ids = list(gp._gameplay_used_ids)
        gp._gameplay_used_ids = []

    def tearDown(self):
        gp._gameplay_used_ids = self._orig_ids

    def test_categories_defined(self):
        self.assertIn("mobile_game", gp.GAMEPLAY_CATEGORIES)
        self.assertIn("soap_cutting", gp.GAMEPLAY_CATEGORIES)
        self.assertIn("satisfying", gp.GAMEPLAY_CATEGORIES)
        self.assertIn("parkour", gp.GAMEPLAY_CATEGORIES)
        self.assertIn("subway_surfers_style", gp.GAMEPLAY_CATEGORIES)

    def test_every_explicit_studio_category_resolves_without_niche_fallback(self):
        categories = (
            "minecraft_parkour",
            "subway_surfers_style",
            "gta_car_ramp",
            "asmr_kinetic_sand",
            "soap_cutting",
            "satisfying",
            "parkour",
            "mobile_game",
        )
        listed_ids = {entry["id"] for entry in gp.list_categories()}

        for category in categories:
            with self.subTest(category=category):
                self.assertIn(category, gp.GAMEPLAY_CATEGORIES)
                self.assertIn(category, listed_ids)
                self.assertEqual(
                    gp.resolve_gameplay_category(category, niche="3_split_gameplay"),
                    category,
                )
                self.assertTrue(gp.queries_for_category(category))

    def test_new_explicit_categories_do_not_change_auto_rotation_set(self):
        self.assertEqual(
            gp._ROTATABLE,
            [
                "mobile_game",
                "soap_cutting",
                "satisfying",
                "parkour",
                "subway_surfers_style",
            ],
        )

    def test_resolve_auto_uses_niche_hint(self):
        cat = gp.resolve_gameplay_category("auto", niche="3_split_gameplay")
        self.assertEqual(cat, "subway_surfers_style")

    def test_resolve_explicit_category(self):
        self.assertEqual(gp.resolve_gameplay_category("soap_cutting"), "soap_cutting")

    def test_recent_blocked_window(self):
        for i in range(100):
            gp.record_gameplay_use("pexels", str(1000 + i))
        blocked = gp.recent_blocked_gameplay_ids(50)
        self.assertEqual(len(blocked), 50)
        self.assertIn("pexels:1050", blocked)
        self.assertNotIn("pexels:1000", blocked)

    def test_record_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "used_gameplay_ids.json")
            with patch.object(gp, "_USED_GAMEPLAY_PATH", path):
                gp._gameplay_used_ids = []
                gp.record_gameplay_use("pexels", "abc123")
                self.assertTrue(os.path.isfile(path))
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                self.assertIn("pexels:abc123", data["ids"])

    def test_queries_for_category(self):
        qs = gp.queries_for_category("parkour")
        self.assertTrue(any("parkour" in q.lower() for q in qs))

    def test_list_categories_has_auto(self):
        ids = [c["id"] for c in gp.list_categories()]
        self.assertIn("auto", ids)


if __name__ == "__main__":
    unittest.main()
