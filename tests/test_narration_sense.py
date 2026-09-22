"""Scenario text must stay on the topic. No doubled titles, no fake quotes."""
import unittest

from scenes.fallback import _generate_procedural_fallback_scenes
from scenes.narration_sense import repair_nonsensical_narration
from viral_retention_engine import ViralRetentionEngine


TITLE = "Ders kitaplarında öğretilmeyen ama bilmeniz gereken 5 şok gerçek"


class NarrationSenseTests(unittest.TestCase):
    def test_quiz_fallback_does_not_repeat_the_headline(self):
        plan = _generate_procedural_fallback_scenes(TITLE, niche_type="9_five_facts", language="tr")
        blob = " ".join(s["narration"] for s in plan["scenes"]).casefold()
        visuals = " ".join(s["scene_description"] for s in plan["scenes"]).casefold()
        self.assertNotIn("yıllarca sınıfta", blob)
        self.assertNotIn("ilk kontrol", blob)
        self.assertNotIn("iddia şu", blob)
        self.assertNotIn("classroom chalkboard", visuals)
        self.assertIn("yoğundur", blob)
        self.assertNotIn("kaydırma", blob)
        self.assertNotIn("toplumun bize", blob)
        self.assertNotIn("bold infographic", visuals)
        self.assertNotIn("şablona kaymaz", blob)
        for sc in plan["scenes"]:
            narr = sc["narration"].casefold()
            self.assertEqual(narr.count("ders kitaplarında"), 1 if "ders kitaplarında" in narr else 0)
            self.assertGreaterEqual(len(narr.split()), 10)

    def test_trigger_name_does_not_splice_an_unrelated_celebrity(self):
        hook = f"İddia şu: {TITLE}."
        out = ViralRetentionEngine.inject_trigger_name_hook(hook, topic=TITLE, lang="tr")
        self.assertNotIn("Marcus Aurelius", out)
        self.assertNotIn("hakkında söylediği", out)

    def test_repair_collapses_the_doubled_title_mash(self):
        mashed = (
            "Ders kitaplarında öğretilmeyen ama bilmeniz gereken 5 şok "
            "Marcus Aurelius'ın Ders kitaplarında öğretilmeyen ama bilmeniz gereken 5 şok gerçek."
        )
        plan = {
            "title": TITLE,
            "keyword": TITLE,
            "language": "tr",
            "scenes": [
                {"narration": mashed},
                {"narration": "Bu bilgi yıllarca sınıfta tekrar edilmiş olabilir; tekrar edilmesi onu kanıtlamaz."},
                {"narration": f"İlk kontrol: {TITLE} iddiasını ders kitabı ile karşılaştır ve kaynağı oku."},
            ],
        }
        out = repair_nonsensical_narration(plan, topic=TITLE)
        first = out["scenes"][0]["narration"]
        self.assertNotIn("Marcus Aurelius", first)
        self.assertLess(first.casefold().count("ders kitaplarında"), 2)
        joined = " ".join(s["narration"] for s in out["scenes"]).casefold()
        self.assertNotIn("yıllarca sınıfta", joined)
        self.assertNotIn("ilk kontrol", joined)
        self.assertIn("ders kitaplarında", joined)

    def test_wrong_topic_script_is_rewritten_onto_the_requested_topic(self):
        topic = "Marcus Aurelius un Öfkeyi Yok Eden 3 Stoacı Kuralı"
        plan = {
            "title": TITLE,
            "language": "tr",
            "scenes": [
                {"narration": f"İddia şu: {TITLE}. Önce bu cümlenin ne söylediğini ayırıyoruz hemen."},
                {"narration": "Bu bilgi yıllarca sınıfta tekrar edilmiş olabilir; tekrar edilmesi onu kanıtlamaz."},
            ],
        }
        out = repair_nonsensical_narration(plan, topic=topic)
        self.assertEqual(out["title"], topic)
        blob = " ".join(s["narration"] for s in out["scenes"]).casefold()
        self.assertIn("aurelius", blob)
        self.assertNotIn("yıllarca sınıfta", blob)


if __name__ == "__main__":
    unittest.main()
