"""Focused regression tests for the shared visual/license contract."""
from __future__ import annotations

import unittest

from production.schemas import LicenseRecord, VisualCandidate
from visuals.license import License, LicenseInfo, is_commercial_safe, parse_cc_license
from visuals.providers import Candidate
from visuals.query_builder import build_shot_queries
from visuals.subject_lock import queries_for_scene
from visuals.registry import score_candidate


class TestVisualContract(unittest.TestCase):
    def test_restrictive_and_unknown_licenses_never_pass(self):
        for raw in ("", "unknown", "cc-by-sa", "cc-by-nc", "cc-by-nd"):
            parsed = parse_cc_license(raw)
            self.assertFalse(is_commercial_safe(parsed), raw)
            with self.assertRaises(ValueError):
                LicenseRecord(license=parsed.value, source="test")

    def test_candidate_preserves_provenance_and_attribution(self):
        info = LicenseInfo(
            License.CC_BY,
            "wikimedia",
            title="Tower",
            author="Ada",
            source_url="https://commons.wikimedia.org/wiki/File:Tower.webm",
            license_url="https://creativecommons.org/licenses/by/4.0/",
        )
        candidate = Candidate(
            source="wikimedia", id="wm_1", url="https://cdn.invalid/tower.webm",
            kind="video", title="Tower", tags=["skyscraper"], license=info,
        )
        row = candidate.to_dict()
        self.assertEqual(row["source_url"], info.source_url)
        self.assertEqual(row["license_url"], info.license_url)
        self.assertTrue(row["attribution"])
        visual = VisualCandidate(
            uid=candidate.uid, source=candidate.source, asset_id=candidate.id,
            url=candidate.url, source_url=row["source_url"],
            license_url=row["license_url"], attribution=row["attribution"],
            license=LicenseRecord(**row["license"]),
        )
        self.assertEqual(visual.source_url, info.source_url)

    def test_semantic_evidence_records_subject_match(self):
        candidate = Candidate(
            source="pexels", id="1", url="https://cdn.invalid/tower.mp4",
            kind="video", title="skyscraper tower skyline", tags=["city"],
            duration=5, license=LicenseInfo(License.PEXELS, "pexels"),
        )
        self.assertGreater(score_candidate(candidate, "skyscraper tower city skyline"), 0)
        self.assertTrue(candidate.semantic_evidence["subject_match"])
        self.assertIn("skyscraper", candidate.semantic_evidence["matched_tokens"])
        self.assertGreater(candidate.topic_match_score, 0)
        self.assertGreater(candidate.visual_verification_score, 0)

    def test_ambiguous_query_has_no_generic_nature_fallback(self):
        self.assertEqual(build_shot_queries(), [])
        self.assertEqual(queries_for_scene(existing=["nature stock footage"]), [])


if __name__ == "__main__":
    unittest.main()
