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
