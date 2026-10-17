"""
Integration tests verifying that reference-repo modules (Chapters 2, 28, 30, 33)
and .md audit items (RULES_100_AUDIT #20, SCENARIO_WRITING_REPORT P1-3/P1-4,
RESEARCH_KIDS_ANIMATION_AI COPPA/MFK) are wired into the live production pipeline.
"""
import unittest

from director.compiler import compile_director_plan
from director.visual_intent import semantic_relevance_score
from compliance.publishing_package import build_publishing_package, build_seo_meta_package
from viral_seo_agent import finalize_seo_compliance
from subtitle_generator import _clean_timings


class TestReferenceRepoLiveWiring(unittest.TestCase):
    def test_compile_director_plan_wires_story_arc_retention_and_punch_in(self):
        raw_plan = {
            "title": "Borsada Kimsenin Bilmediği 3 Gizli Kural",
            "niche_id": "8_crypto_market",
            "procedural_fallback": True,
            "scenes": [
                {
                    "narration": "Neden yatırımcıların yüzde doksanı aynı gizli tuzağa düşüyor?",
                    "duration": 4.2,
                    "camera_direction": "static",
                    "search_queries": ["stock market chart screen"],
                },
                {
                    "narration": "Birinci kural, panik anında asla duygusal satış yapmamaktır.",
                    "duration": 4.5,
                    "camera_direction": "static",
                    "search_queries": ["trader desk monitor"],
                },
                {
                    "narration": "İkinci kural, büyük balinaların sessizce topladığı veriyi izlemektir.",
                    "duration": 4.5,
                    "search_queries": ["financial data dashboard"],
                },
                {
                    "narration": "Üçüncü kural, tehlike anında portföyü nakit kalkanıyla korumaktır!",
                    "duration": 4.5,
                    "search_queries": ["gold vault security"],
                },
                {
                    "narration": "Oysa çoğu kişi şok haberlerle tüm birikimini tek günde eritiyor.",
                    "duration": 4.5,
                    "search_queries": ["red stock market crash"],
                },
                {
                    "narration": "İşte bu yüzden ilk sorudaki o gizli tuzağı asla unutmayın.",
                    "duration": 4.5,
                    "search_queries": ["chess king strategy board"],
                },
            ],
        }
        plan = compile_director_plan(raw_plan, title=raw_plan["title"], niche_id="8_crypto_market")
        legacy = plan.to_legacy_plan()

        # P1-4: procedural_fallback flag preserved in meta and legacy plan
        self.assertTrue(plan.meta.get("procedural_fallback"))
        self.assertTrue(legacy.get("procedural_fallback"))

        # StoryArcAnalyzer (dramaclaw) wired
        self.assertIn("story_arc_metrics", plan.meta)
        self.assertEqual(len(plan.meta["story_arc_metrics"]), len(plan.scenes))
        self.assertEqual(plan.scenes[0].beat_category, "hook")
        self.assertGreaterEqual(plan.scenes[0].tension_score, 0.3)

        # RetentionEngine (video-autopilot-kit) wired & heals static >3.0s shots
        self.assertIn("retention_audit", plan.meta)
        self.assertTrue(plan.meta["retention_audit"]["meets_mrbeast_pacing_standard"])
        self.assertEqual(plan.meta["retention_audit"]["stale_scene_indices"], [])

        # RoleBasedPromptChain & detect_punch_in_cues (ai-content-studio) wired
        self.assertIn("punch_in_cues", plan.meta)
        self.assertGreaterEqual(len(plan.meta["punch_in_cues"]), 1)
        self.assertIn("role_prompt_chain", plan.meta)
        self.assertIn("investigator", plan.meta["role_prompt_chain"])

    def test_whatsapp_confessions_auto_attaches_imessage_overlay(self):
        raw_plan = {
            "title": "Gece Gelen Gizli Mesaj",
            "niche_id": "20_whatsapp_confessions",
            "scenes": [
                {"narration": "Gece saat üçte telefonuma bilinmeyen bir numaradan mesaj geldi.", "duration": 4.0},
                {"narration": "Mesajda sadece kapının önündeki paketi sakın açma yazıyordu.", "duration": 4.0},
                {"narration": "Perdeyi araladığımda sokak lambasının altında bir gölge gördüm.", "duration": 4.0},
                {"narration": "Hemen polisi aramak istedim ama hattım aniden kesildi.", "duration": 4.0},
                {"narration": "Oysa o paketi bir saat önce içeri almıştım bile.", "duration": 4.0},
                {"narration": "Ve telefonuma gelen son bildirimle her şey yeniden başladı.", "duration": 4.0},
            ],
        }
        plan = compile_director_plan(raw_plan, title=raw_plan["title"], niche_id="20_whatsapp_confessions")
        overlay = plan.meta.get("hybrid_render_overlay") or {}
        self.assertEqual(overlay.get("ui_type"), "imessage")

    def test_cross_language_tr_en_semantic_relevance_score(self):
        # Turkish narration with English stock query should match via _translate_blob
        score = semantic_relevance_score(
            candidate_text="mosque dome muslim prayer sunrise",
            narration="Sabah namazında cami kubbesinden yükselen huzurlu dua sesi.",
        )
        self.assertGreaterEqual(score, 16.0)

    def test_kids_disclosure_and_license_governance_wired(self):
        seo = finalize_seo_compliance(
            {
                "seo_title": "Sevimli Hayvanlar Şarkısı #Shorts",
                "seo_description": "Renkleri ve hayvanları öğreniyoruz!",
                "tags": ["çocuk", "yorum", "abone", "animasyon"],
                "pinned_comment": "Yorum yazın!",
            },
            lang="tr",
            niche="36_kids_animation",
        )
        self.assertTrue(seo.get("selfDeclaredMadeForKids"))
        self.assertTrue(seo.get("suppress_pinned_comment"))
        self.assertEqual(seo.get("pinned_comment"), "")
        self.assertIn("Made for Kids", seo.get("seo_description", ""))

        pkg = build_publishing_package(
            title="Sevimli Hayvanlar",
            niche_id="36_kids_animation",
            viewer_score=88.0,
            manifest_items=[
                {"asset_id": "clip1", "license": "Pexels-License", "source": "pexels"},
            ],
        )
        self.assertTrue(pkg["compliance"].get("self_declared_made_for_kids"))
        self.assertEqual(pkg["credits"].get("governance_status"), "APPROVED_FAIL_CLOSED")

        seo_pkg = build_seo_meta_package(
            title="Sevimli Hayvanlar",
            description="Çocuk animasyonu",
            tags=["kids", "comment"],
            niche_id="36_kids_animation",
        )
        self.assertTrue(seo_pkg.get("selfDeclaredMadeForKids"))

    def test_subtitle_clean_timings_strips_sensevoice_and_emojis(self):
        cleaned = _clean_timings([
            {"text": "<|laughter|>Harika🔥", "offset": 0.0, "duration": 0.4},
            {"text": "bir🚀", "offset": 0.4, "duration": 0.3},
        ])
        self.assertEqual([c["text"] for c in cleaned], ["Harika", "bir"])


if __name__ == "__main__":
    unittest.main()
