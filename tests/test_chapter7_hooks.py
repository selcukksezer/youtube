"""7.1: the four opening engines are spoken, not only stored."""
import unittest

from scenes.retention_hooks import apply_retention_hooks_to_plan, opening_strategy_names


class TestChapter7Hooks(unittest.TestCase):
    def test_plan_four_lead_the_rotation(self):
        names = opening_strategy_names()
        self.assertEqual(
            names[:4],
            ["cognitive_dissonance", "curiosity_gap", "shock_stat", "problem_agitation"],
        )

    def test_finished_opening_keeps_the_fact_after_the_hook(self):
        plan = {
            "scenes": [
                {"narration": "Roma sokakları o gün çok kalabalıktı. İkinci cümle durur.", "duration": 4.0},
                {"narration": "Son.", "duration": 3.0},
            ]
        }
        out = apply_retention_hooks_to_plan(plan, "Roma", lang="tr", variation_attempt=0)
        spoken = out["scenes"][0]["narration"]
        self.assertEqual(out["retention_metadata"]["hook_strategy"], "cognitive_dissonance")
        self.assertIn("İkinci cümle durur.", spoken)
        self.assertNotIn("Roma sokakları", spoken)
        self.assertTrue(spoken.startswith(out["retention_metadata"]["opening_hook"]))

    def test_existing_stat_is_not_replaced(self):
        opening = "İnsanların %99'u bu kuralı bilmeden emekli oluyor."
        plan = {
            "scenes": [
                {"narration": opening + " Devamı burada durur.", "duration": 4.0},
                {"narration": "Son.", "duration": 3.0},
            ]
        }
        out = apply_retention_hooks_to_plan(plan, "Emeklilik", lang="tr", variation_attempt=0)
        self.assertEqual(out["retention_metadata"]["hook_strategy"], "shock_stat")
        self.assertIn(opening, out["scenes"][0]["narration"])
        self.assertIn("Devamı burada durur.", out["scenes"][0]["narration"])


class TestChapter7Loop(unittest.TestCase):
    def test_finished_ending_joins_without_repeating_the_open(self):
        opening = "Bunu öğrenene kadar Roma konusunda bildiğiniz her şey yanılsamaydı."
        plan = {
            "scenes": [
                {"narration": opening, "duration": 4.0},
                {"narration": "Pazar o gün erken kapandı ve fiyatlar düştü.", "duration": 4.0},
            ]
        }
        out = apply_retention_hooks_to_plan(plan, "Roma", lang="tr", variation_attempt=0)
        last = out["scenes"][-1]["narration"]
        self.assertIn("Pazar o gün erken kapandı", last)
        self.assertNotIn("yanılsamaydı", last)
        self.assertNotIn("başa dön", last.lower())
        self.assertTrue(last.endswith((".", "!", "?")))
        self.assertNotRegex(last, r"(?:çünkü|yüzden|sebeple|peki)\s*$")
        preview = out["retention_metadata"]["seamless_loop_preview"]
        self.assertTrue(preview.endswith(opening))


if __name__ == "__main__":
    unittest.main()
