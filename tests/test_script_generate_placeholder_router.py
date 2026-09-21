"""Router boundary: placeholder scene_description never leaves /api/script/generate."""
import os
import unittest

from fastapi.testclient import TestClient

from scenes.narration_validate import sanitize_plan_scene_descriptions, scene_description_usable


class TestScriptGeneratePlaceholderRouter(unittest.TestCase):
    def test_sanitize_strips_placeholder(self):
        plan = {
            "scenes": [
                {
                    "narration": "Bu sahne en az on kelimelik tam bir Türkçe cümledir burada.",
                    "scene_description": "(SCENE_DESCRIPTION)",
                    "search_queries": ["mosque dome golden sunrise", "quran pages"],
                }
            ]
        }
        out = sanitize_plan_scene_descriptions(plan)
        desc = out["scenes"][0]["scene_description"]
        self.assertTrue(scene_description_usable(desc))
        self.assertNotIn("SCENE_DESCRIPTION", desc.upper())
        self.assertIn("mosque", desc.lower())

    def test_generate_endpoint_ai_mocked_fail_no_placeholder(self):
        os.environ["SHORTS_FORCE_PROCEDURAL_FALLBACK"] = "1"
        self.addCleanup(lambda: os.environ.pop("SHORTS_FORCE_PROCEDURAL_FALLBACK", None))
        from server import app

        client = TestClient(app)
        resp = client.post(
            "/api/script/generate",
            json={
                "keyword": "Hz Peygamber in en çok tekrar ettiği o dua bugün hayatınızı değiştirebilir",
                "niche": "6_stoic_philosophy",
                "language": "tr",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text[:400])
        body = resp.json()
        plan = body.get("plan") or {}
        self.assertEqual(plan.get("niche_id"), "10_religious_quotes")
        self.assertTrue(plan.get("scenes"))
        for sc in plan["scenes"]:
            desc = sc.get("scene_description") or ""
            self.assertNotIn("SCENE_DESCRIPTION", desc.upper(), desc)
            self.assertTrue(scene_description_usable(desc), desc)
        # Force a leftover placeholder through the same sanitizer the router uses
        dirty = {
            "scenes": [
                {
                    "narration": plan["scenes"][0]["narration"],
                    "scene_description": "(SCENE_DESCRIPTION)",
                    "search_queries": plan["scenes"][0].get("search_queries") or ["mosque dome"],
                }
            ]
        }
        cleaned = sanitize_plan_scene_descriptions(dirty)
        self.assertNotIn("SCENE_DESCRIPTION", cleaned["scenes"][0]["scene_description"].upper())


if __name__ == "__main__":
    unittest.main()
