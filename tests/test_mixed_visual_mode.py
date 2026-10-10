"""Mixed visual mode rotates stock footage and Flux."""
import unittest

from director.compiler import _scenes_from_legacy
from visuals.mixed_visual import apply_selected_visual_mode


class MixedVisualModeTests(unittest.TestCase):
    def test_mixed_replaces_every_scene_in_rotation(self):
        plan = {
            "visual_mode": "whiteboard",
            "scenes": [
                {"visual_mode": "whiteboard"},
                {},
                {"visual_mode": "flux"},
                {},
            ],
        }
        apply_selected_visual_mode(plan, "mixed")
        self.assertEqual(plan["visual_mode"], "mixed")
        self.assertEqual(
            [scene["visual_mode"] for scene in plan["scenes"]],
            ["stock", "flux", "stock", "flux"],
        )

    def test_single_engine_does_not_overwrite_existing_scene(self):
        plan = {"scenes": [{"visual_mode": "whiteboard"}, {}]}
        apply_selected_visual_mode(plan, "flux")
        self.assertEqual(plan["visual_mode"], "flux")
        self.assertEqual(plan["scenes"][0]["visual_mode"], "whiteboard")
        self.assertEqual(plan["scenes"][1]["visual_mode"], "flux")

    def test_auto_leaves_plan_untouched(self):
        plan = {"scenes": [{}]}
        apply_selected_visual_mode(plan, "auto")
        self.assertNotIn("visual_mode", plan)
        self.assertNotIn("visual_mode", plan["scenes"][0])

    def test_compiler_expands_mixed_and_keeps_explicit_scene(self):
        scenes = _scenes_from_legacy({
            "visual_mode": "karisik",
            "scenes": [
                {"narration": "bir", "scene_description": "avlu"},
                {"narration": "iki", "scene_description": "sokak"},
                {"narration": "uc", "scene_description": "oda"},
                {"narration": "dort", "scene_description": "tahta", "visual_mode": "whiteboard"},
            ],
        })
        self.assertEqual(
            [scene.visual_mode for scene in scenes],
            ["stock", "flux", "stock", "whiteboard"],
        )


if __name__ == "__main__":
    unittest.main()
