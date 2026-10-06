"""
Chapter 7.2: Seamless Loop Bridge (Kusursuz Döngü Köprüsü) Verification Suite.
Validates:
- Grammatical and semantic connection from the last scene's narration into Scene 1's opening hook.
- Stripping of generic farewells (Item 198) and injection of diverse loop conjunctions (Item 137).
- Multi-language support (Turkish and English seamless loops).
- Full narration synthesis reflecting the loop bridge on the final spoken sentence.
"""
import unittest

from viral_retention_engine import ViralRetentionEngine
from hybrid_niches import generate_perfect_seamless_loop_bridge
from scenes.retention_hooks import apply_retention_hooks_to_plan, ensure_retention_hooks_on_plan


class TestChapter7SeamlessLoopBridge(unittest.TestCase):

    def test_synthesize_seamless_loop_turkish(self):
        opening = "Bunu öğrenene kadar hayatınızı yanlış yaşıyordunuz."
        closing = "Marcus Aurelius'un bahsettiği zihinsel disiplin budur."
        res = ViralRetentionEngine.synthesize_seamless_loop(
            opening_hook=opening,
            final_narration=closing,
            video_index=0,
            lang="tr",
        )
        self.assertEqual(res["opening_hook"], opening)
        self.assertTrue(len(res["ending_bridge"]) > 0)
        # Spoken line stays a finished sentence. The bridge is metadata only.
        self.assertTrue(res["seamless_closing"].endswith((".", "!", "?")))
        self.assertNotRegex(res["seamless_closing"], r"(?:çünkü|bu yüzden|bu sebeple|peki)\s*$")
        self.assertIn("budur.", res["seamless_closing"])
        # Preview must combine seamless closing and opening hook
        self.assertIn(opening, res["preview_loop"])
        self.assertIn(res["seamless_closing"], res["preview_loop"])

    def test_synthesize_seamless_loop_english(self):
        opening = "Until you learn this rule, your mind was never truly yours."
        closing = "This is the ultimate lesson left behind by ancient stoics."
        res = ViralRetentionEngine.synthesize_seamless_loop(
            opening_hook=opening,
            final_narration=closing,
            video_index=1,
            lang="en",
        )
        self.assertEqual(res["opening_hook"], opening)
        self.assertTrue(res["seamless_closing"].endswith((".", "!", "?")))
        self.assertNotRegex(res["seamless_closing"], r"(?:because|and that is why|which is why|\bso)\s*$")
        self.assertIn("stoics.", res["seamless_closing"])
        self.assertIn(opening, res["preview_loop"])
        self.assertIn(res["seamless_closing"], res["preview_loop"])

    def test_diverse_conjunctions_rotation(self):
        pool_tr = ViralRetentionEngine.get_diverse_loop_conjunctions(lang="tr")
        pool_en = ViralRetentionEngine.get_diverse_loop_conjunctions(lang="en")
        self.assertGreaterEqual(len(pool_tr), 10)
        self.assertGreaterEqual(len(pool_en), 10)
        # Ensure sequential video indices rotate different conjunctions
        c0 = ViralRetentionEngine.pick_loop_bridge_for_video(0, lang="tr")
        c1 = ViralRetentionEngine.pick_loop_bridge_for_video(1, lang="tr")
        self.assertNotEqual(c0, c1)

    def test_strip_farewell_and_inject_loop_bridge_in_plan(self):
        plan = {
            "title": "Zaman Yönetimi",
            "scenes": [
                {"scene_number": 1, "narration": "Zamanınızı doğru yönetmek için bilmeniz gereken en kritik gerçek.", "duration": 6.0},
                {"scene_number": 2, "narration": "Gün içinde saatlerinizi çalan görünmez alışkanlıkları fark edin.", "duration": 6.0},
                {"scene_number": 3, "narration": "Verimlilik işte bu adımlarla başlar. Teşekkürler izlediğiniz için hoşça kalın, abone olmayı unutmayın!", "duration": 6.0},
            ]
        }
        out = apply_retention_hooks_to_plan(plan, "Zaman Yönetimi", lang="tr", variation_attempt=0)
        last_narr = out["scenes"][-1]["narration"]

        # Farewell cliches must be eradicated
        self.assertNotIn("hoşça kalın", last_narr.lower())
        self.assertNotIn("abone olmayı unutmayın", last_narr.lower())
        self.assertNotIn("teşekkürler", last_narr.lower())

        # Spoken ending stays a finished sentence. Bridge text stays in metadata.
        self.assertTrue(last_narr.endswith((".", "!", "?")))
        self.assertNotRegex(last_narr, r"(?:çünkü|bu yüzden|bu sebeple|peki)\s*$")
        self.assertIn("başlar", last_narr)
        meta = out.get("retention_metadata") or {}
        self.assertTrue(meta.get("ending_bridge"))
        self.assertTrue(meta.get("seamless_loop_preview"))

    def test_idempotent_rebuild_preserves_loop_bridge(self):
        plan = {
            "title": "Kripto Sırrı",
            "scenes": [
                {"scene_number": 1, "narration": "Kriptoda balinaların sizden sakladığı o gizli hareket.", "duration": 5.0},
                {"scene_number": 2, "narration": "Büyük yatırımcılar piyasayı bu yöntemle manipüle eder.", "duration": 5.0},
            ]
        }
        p1 = ensure_retention_hooks_on_plan(plan, "Kripto Sırrı", lang="tr", variation_attempt=1)
        closing_1 = p1["scenes"][-1]["narration"]
        self.assertTrue(len(closing_1) > 20)

        # Idempotent second pass must preserve the established loop narration
        p2 = ensure_retention_hooks_on_plan(p1, "Kripto Sırrı", lang="tr", variation_attempt=1)
        self.assertEqual(p2["scenes"][-1]["narration"], closing_1)
        self.assertIn(closing_1, p2["full_narration"])

    def test_dangling_cunku_is_not_spoken(self):
        opening = "Bunu öğrenene kadar göz teması konusunda bildiğiniz her şey yanılsamaydı."
        closing = (
            "Bu taktikleri fark ettiğiniz anda manipülatörün üzerinizdeki tüm gücü "
            "bir anda yok olur çünkü"
        )
        res = ViralRetentionEngine.synthesize_seamless_loop(
            opening_hook=opening,
            final_narration=closing,
            video_index=0,
            lang="tr",
        )
        self.assertTrue(res["seamless_closing"].endswith("."))
        self.assertFalse(res["seamless_closing"].lower().rstrip(".!?").endswith("çünkü"))
        self.assertIn("yok olur.", res["seamless_closing"])

        question = "Peki siz çevrenizde bu taktiğe maruz kaldınız mı? Yorumlarda anlatın!"
        kept = ViralRetentionEngine.synthesize_seamless_loop(
            opening_hook=opening,
            final_narration=question,
            video_index=0,
            lang="tr",
        )
        self.assertEqual(kept["seamless_closing"], question)


if __name__ == "__main__":
    unittest.main()
