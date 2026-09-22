import unittest
from unittest.mock import patch

from compliance import evaluate_plan_compliance, publication_decision, research_quality_gate
from production.schemas import LicenseRecord, SourceManifest, VisualCandidate
from research_service import build_topic_research_brief
from scenes.fallback import _pad_narration_to_min_words
from visuals.registry import score_candidate
from visuals.providers import Candidate
from visuals.license import License, LicenseInfo
from production.evidence import evaluate_evidence, text_hash


def evidence(source_id, publisher, topic, excerpt):
    return {
        "source_id": source_id, "title": publisher, "publisher": publisher,
        "url": f"https://{source_id}.test/article", "excerpt": excerpt,
        "retrieval_status": "retrieved", "content_sha256": text_hash(excerpt),
        "assessments": [{"claim_id": "claim_1", "verdict": "supports",
                         "claim_sha256": text_hash(topic), "quote": excerpt}],
    }


class TestQualityPolicyPipeline(unittest.TestCase):
    def test_research_gate_explains_cause_without_blocking_render(self):
        result = evaluate_plan_compliance({
            "niche_id": "16_wealth_entrepreneurship",
            "full_narration": "Neden bu girişimci farklı karar veriyor? Çünkü riskleri ölçüyor. Ama sonuçları garanti etmiyor.",
            "scenes": [
                {"narration": "Neden bu girişimci farklı karar veriyor?"},
                {"narration": "Çünkü riskleri ölçüyor ve sonuçları karşılaştırıyor."},
                {"narration": "Ama bu yaklaşım garanti sunmuyor."},
            ],
            "research_brief": {"enforce": True, "claims": [], "evidence": []},
        })
        self.assertTrue(result["hard_fail"])
        self.assertFalse(result["render_blocking"])
        self.assertIn("research_gate:", result["hard_fail_reasons"][-1])
        self.assertEqual(result["diagnosis"]["primary"], result["hard_fail_reasons"][0])

    def test_research_requires_two_independent_publishers(self):
        def fetcher(topic, **_kwargs):
            return [
                evidence("a", "Primary", topic, "Tall buildings are engineered to move under wind loads."),
                evidence("b", "Reference", topic, "Structural flexibility allows a tower to sway in strong wind."),
            ]

        brief = build_topic_research_brief(
            "Gökdelenler neden sallanır?",
            niche_id="5_science",
            evidence_fetcher=fetcher,
        )
        self.assertTrue(brief["research_ready"])
        self.assertEqual(brief["status"], "research_ready")
        self.assertEqual(research_quality_gate(brief)["action"], "ALLOW")

    def test_adapter_cannot_bypass_missing_support_with_trust_flag(self):
        brief = {"trusted_adapter": True, "claims": [{"claim_id": "claim_1",
                 "text": "A factual claim", "evidence_ids": ["a", "b"]}],
                 "evidence": [{"source_id": sid, "url": f"https://{sid}.test",
                               "publisher": sid} for sid in ("a", "b")]}
        self.assertFalse(evaluate_evidence(brief)["ready"])

    @patch("research_service.fetch_youtube_autocomplete_suggestions", return_value=[])
    def test_same_owner_and_copied_content_are_not_independent(self, _autocomplete):
        for mode in ("owner", "domain", "copy", "wikimedia", "hash", "quote"):
            def fetcher(topic, **_kwargs):
                first = evidence("a", "Primary", topic, "Tall buildings are engineered to move under wind loads.")
                second = evidence("b", "Reference", topic, "Structural flexibility allows towers to move under wind loads.")
                if mode == "owner":
                    second["publisher"] = first["publisher"]
                elif mode == "domain":
                    second["url"] = "https://news.a.test/other"
                elif mode == "copy":
                    second.update(excerpt=first["excerpt"], content_sha256=first["content_sha256"], assessments=first["assessments"])
                elif mode == "wikimedia":
                    first["url"], second["url"] = "https://en.wikipedia.org/wiki/A", "https://www.wikidata.org/wiki/Q1"
                elif mode == "hash":
                    second["content_sha256"] = "invalid"
                else:
                    second["assessments"][0]["quote"] = "This quote is absent from the retrieved content."
                return [first, second]
            with self.subTest(mode=mode):
                brief = build_topic_research_brief("Why do towers sway?", evidence_fetcher=fetcher)
                self.assertFalse(brief["research_ready"])
                self.assertNotEqual(research_quality_gate(brief)["action"], "ALLOW")

    def test_missing_evidence_blocks_plan(self):
        result = evaluate_plan_compliance({
            "niche_id": "5_science",
            "full_narration": "Gökdelenler rüzgâr yükünü azaltmak için esnek tasarlanır.",
            "scenes": [],
            "research_brief": {"enforce": True, "claims": [{"claim_id": "c1", "status": "unverified"}], "evidence": []},
        })
        self.assertTrue(result["hard_fail"])
        self.assertEqual(result["research"]["action"], "DROP")

    def test_subject_mismatch_rejected(self):
        candidate = Candidate(
            source="pixabay", id="1", url="https://example.test/clip.mp4", kind="video",
            title="soft sunset clouds", tags=["sky"], duration=5,
            license=LicenseInfo(License.PIXABAY, "pixabay"),
        )
        self.assertLess(score_candidate(candidate, "skyscraper tower city skyline"), 0)

    def test_manifest_rejects_duplicate_uid(self):
        license_record = LicenseRecord(license="pexels", source="pexels", safe=True)
        clip = VisualCandidate(
            uid="pexels:1", source="pexels", asset_id="1", url="https://example.test/1.mp4",
            license=license_record,
        )
        with self.assertRaises(ValueError):
            SourceManifest(clips=[clip, clip])

    def test_fallback_removes_mechanical_cta_and_emoji(self):
        text = _pad_narration_to_min_words("Bu bilgi önemli. 🚨 Yorumlarda paylaşın ve takipte kalın!", min_words=6)
        self.assertNotIn("🚨", text)
        self.assertNotIn("yorumlarda paylaşın", text.casefold())
        self.assertNotIn("takipte kalın", text.casefold())

    def test_risk_sensitive_niche_requires_human_review(self):
        decision = publication_decision(
            {"niche_id": "5_science"},
            {"hard_fail": False, "research": {"action": "ALLOW"}, "niche_gate": {"action": "GATE"}},
            {"score": 90},
        )
        self.assertEqual(decision["action"], "HUMAN_REVIEW")


if __name__ == "__main__":
    unittest.main()
