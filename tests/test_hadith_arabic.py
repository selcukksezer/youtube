"""Hadith scenes keep Turkish speech and carry Arabic on screen."""
import unittest

from craft.human_director import apply_human_craft, human_craft_hard_reject
from director.compiler import compile_director_plan


class HadithArabicTests(unittest.TestCase):
    def _plan(self):
        return {
            "keyword": "Niyet hadisi",
            "niche_id": "16_islamic_wisdom",
            "language": "tr",
            "scenes": [
                {
                    "narration": "Resulullah buyurdu ki ameller ancak niyetlere göredir ve herkes niyet ettiği şeyin karşılığını eksiksiz alır.",
                    "scene_description": "Open Quran pages with soft window light and no faces",
                    "duration": 3.2,
                },
                {
                    "narration": "İhlasla yapılan küçük bir amel samimiyetsiz yapılan büyük bir amelden çok daha hayırlı ve bereketlidir.",
                    "scene_description": "Mosque dome catching golden sunrise light with no people",
                    "duration": 3.2,
                },
                {
                    "narration": "Bu ölçüyü hayatına alan kişi attığı her adımda bir ferahlık bulur ve kardeşine de aynı sözü hatırlatır.",
                    "scene_description": "Prayer hands raised at dusk cropped at the wrists",
                    "duration": 3.2,
                },
            ],
        }

    def test_long_hadith_is_not_blocked_for_hook_or_loop(self):
        plan = apply_human_craft(self._plan(), title="Niyet hadisi", niche_id="16_islamic_wisdom")
        _, reason = human_craft_hard_reject(plan)
        self.assertNotIn("weak_mute_hook", reason)
        self.assertNotIn("no_loop_closure", reason)
        self.assertTrue(plan["scenes"][-1].get("loop_closure"))
        self.assertIn("niyetlere", plan["scenes"][0]["narration"])

    def test_arabic_and_citation_land_on_the_scene(self):
        plan = apply_human_craft(self._plan(), title="Niyet hadisi", niche_id="16_islamic_wisdom")
        scene = plan["scenes"][0]
        self.assertIn("الْأَعْمَالُ", scene["arabic_text"])
        self.assertIn("Buhari", scene["source_citation"])
        self.assertNotRegex(scene["narration"], r"[\u0600-\u06FF]")

    def test_compiler_keeps_arabic_on_director_scene(self):
        director = compile_director_plan(
            self._plan(),
            title="Niyet hadisi",
            niche_id="16_islamic_wisdom",
            language="tr",
        )
        self.assertIn("الْأَعْمَالُ", director.scenes[0].arabic_text or "")


if __name__ == "__main__":
    unittest.main()
