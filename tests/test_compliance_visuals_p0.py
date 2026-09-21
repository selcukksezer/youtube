"""P0 compliance + visuals unit tests (research-backed)."""
from __future__ import annotations

import os
import tempfile
import unittest

from compliance import (
    ai_disclosure_block,
    evaluate_plan_compliance,
    inauthentic_risk_score,
    niche_gate,
    sanitize_seo_description,
)
from compliance.viewer_score import compute_viewer_score
from visuals.license import License, parse_cc_license, is_commercial_safe
from visuals.query_builder import build_shot_queries, validate_query_list
from visuals.motion_graphics import caption_lines, build_kinetic_clip


class TestLicenseParse(unittest.TestCase):
    def test_rejects_sharealike(self):
        self.assertEqual(parse_cc_license("https://creativecommons.org/licenses/by-sa/4.0/"), License.CC_BY_SA)
        self.assertFalse(is_commercial_safe(License.CC_BY_SA))

    def test_accepts_cc0_and_pexels(self):
        self.assertEqual(parse_cc_license("CC0 1.0"), License.CC0)
        self.assertTrue(is_commercial_safe(License.PEXELS))


class TestQueryBuilder(unittest.TestCase):
    def test_religious_blocks_stoic(self):
        qs = build_shot_queries(
            narration="Sabır imanın yarısıdır, cami kubbesi altında dua",
            niche_id="10_religious_quotes",
        )
        self.assertTrue(qs)
        joined = " ".join(qs).lower()
        self.assertNotIn("marcus", joined)
        self.assertNotIn("roman", joined)
        self.assertTrue(any("mosque" in q or "prayer" in q or "quran" in q for q in qs))

    def test_bans_cinematic_soup(self):
        cleaned = validate_query_list(["bitcoin cinematic 4k atmospheric"], "8_crypto_whales")
        self.assertTrue(cleaned)
        self.assertNotIn("cinematic", cleaned[0].lower())
        self.assertNotIn("4k", cleaned[0].lower())


class TestInauthenticGate(unittest.TestCase):
    def test_investment_push_hard_fail(self):
        plan = {
            "niche_id": "8_crypto_whales",
            "full_narration": "Bu coini hemen al, garanti kazanç 100x olacak. Yatırım tavsiyesi veriyorum.",
            "scenes": [
                {"narration": "Bu coini hemen al ve zengin ol."},
                {"narration": "Garanti kazanç için bugün al."},
            ],
        }
        r = inauthentic_risk_score(plan)
        self.assertTrue(r["hard_fail"])
        self.assertIn(r["verdict"], ("templated_mass_spam", "policy_drop"))

    def test_original_commentary_ok(self):
        plan = {
            "niche_id": "6_stoic_philosophy",
            "keyword": "sabır",
            "full_narration": (
                "Neden sabır bu kadar zor? Çünkü zihin geleceği kontrol etmek ister. "
                "Ama Stoacılar aslında şunu fark eder: kontrol ettiğin tek şey tepkindir. "
                "Sen de bugün bir kez durup nefes alırsan, yarın farklı bir insan olursun."
            ),
            "scenes": [
                {"narration": "Neden sabır bu kadar zor gelir?"},
                {"narration": "Çünkü zihin geleceği kontrol etmek ister ama edemez."},
                {"narration": "Kontrol ettiğin tek şey tepkindir; bugün bir nefes al."},
            ],
        }
        r = inauthentic_risk_score(plan)
        self.assertFalse(r["hard_fail"])
        self.assertLess(r["risk"], 70)

    def test_ai_persona_drop(self):
        g = niche_gate("8_crypto", "Ben bir yatırım danışmanıyım, portföyünü şöyle kur.")
        self.assertEqual(g["action"], "DROP")


class TestSeoSanitize(unittest.TestCase):
    def test_strips_hashtag_wall(self):
        dirty = "Merhaba\n#a #b #c #d #e #f #g #h #i #j\nDevam"
        clean = sanitize_seo_description(dirty, max_hashtags=3)
        self.assertLessEqual(len(__import__("re").findall(r"#\w+", clean)), 3)

    def test_disclosure_block(self):
        d = ai_disclosure_block(lang="tr")
        self.assertIn("studio_ai_survey", d)
        self.assertIn("Üretim notu", d["description_paragraph"])


class TestViewerScore(unittest.TestCase):
    def test_score_shape(self):
        plan = {
            "scenes": [
                {"narration": "Neden kimse bunu söylemiyor?", "beat_type": "hook", "search_queries": ["curious person silhouette"]},
                {"narration": "Çünkü gerçek çok basit aslında.", "search_queries": ["simple light window"]},
                {"narration": "Kimse bunu söylemiyor ama sen artık biliyorsun.", "search_queries": ["person thinking night"]},
            ],
            "total_duration": 45,
        }
        vs = compute_viewer_score(plan)
        self.assertIn("score", vs)
        self.assertIn("components", vs)
        self.assertGreaterEqual(vs["score"], 20)


class TestKineticProcedural(unittest.TestCase):
    def test_caption_lines(self):
        lines = caption_lines("Sabır imanın yarısıdır ve her zorluk bir kapı açar", max_words=12)
        self.assertTrue(1 <= len(lines) <= 3)
        self.assertTrue(all(len(L) <= 48 for L in lines))

    def test_build_kinetic_clip(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "kin.mp4")
            path = build_kinetic_clip(
                out, duration=2.5, text="Sabır imanın yarısıdır",
                niche_id="10_religious_quotes", scene_index=0,
            )
            self.assertTrue(path and os.path.isfile(path))
            self.assertGreater(os.path.getsize(path), 12_000)


class TestEvaluatePlan(unittest.TestCase):
    def test_bundle(self):
        plan = {
            "niche_id": "4_mystery_unsolved",
            "language": "tr",
            "full_narration": "Bu koordinatta neden kimse yaşamıyor? Aslında uydu görüntüleri başka bir hikaye anlatıyor.",
            "scenes": [
                {"narration": "Bu koordinatta neden kimse yaşamıyor?"},
                {"narration": "Uydu görüntüleri başka bir hikaye anlatıyor."},
            ],
        }
        ev = evaluate_plan_compliance(plan)
        self.assertIn("ok", ev)
        self.assertIn("ai_disclosure", ev)
        self.assertEqual(ev["niche_gate"]["action"], "GATE")


if __name__ == "__main__":
    unittest.main()
