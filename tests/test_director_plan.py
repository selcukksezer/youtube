"""DirectorPlan unit tests — schema, timeline, visual lock, audio bus, quality gate."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from director import (
    compile_director_plan,
    solve_timeline,
    validate_director_plan,
    build_audio_events,
    collect_tape_stop_times,
    pre_render_score,
    resolve_niche_from_topic,
    resolve_topic_intelligence,
    semantic_relevance_score,
)
import config
from director.quality_gate import check_narration_integrity
from director.schema import DirectorPlan, ScenePlan, VisualIntent, QualityThresholds
from director.visual_intent import text_contains_excluded, apply_visual_intents


def _sample_raw_plan(n=14):
    scenes = []
    for i in range(n):
        scenes.append({
            "narration": f"Bu stoaci kural {i+1} ofkeyi yok eder ve zihni her gun sakin tutar.",
            "duration": 3.0,
            "scene_description": "dark mysterious skull horror hooded figure",
            "search_queries": ["stoic marble statue portrait", "roman emperor calm meditation"],
        })
    return {
        "title": "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı",
        "full_narration": " ".join(s["narration"] for s in scenes),
        "scenes": scenes,
    }


class TestDirectorPlan(unittest.TestCase):
    def test_niche_lock_from_topic(self):
        locked = resolve_niche_from_topic(
            "Marcus Aurelius stoacı kurallar",
            "13_mystery_paranormal",
        )
        self.assertEqual(locked, "6_stoic_philosophy")

    def test_niche_lock_whatsapp_from_topic(self):
        locked = resolve_niche_from_topic(
            "whatsapp mesajları dram hikayesi",
            "1_news_flash",
        )
        self.assertEqual(locked, "20_whatsapp_chat_story")

    def test_compile_strips_mystery_queries_for_stoic(self):
        raw = _sample_raw_plan()
        plan = compile_director_plan(raw, title=raw["title"], niche_id="13_mystery_paranormal")
        self.assertEqual(plan.niche_id, "6_stoic_philosophy")
        self.assertGreaterEqual(len(plan.scenes), 8)
        self.assertGreaterEqual(plan.total_duration(), 38.0)
        self.assertLessEqual(plan.total_duration(), 60.0)
        for s in plan.scenes:
            joined = " ".join(s.search_queries).lower()
            self.assertNotIn("skull", joined)
            self.assertNotIn("hooded", joined)
            self.assertTrue(s.visual_intent.must_exclude)

    def test_timeline_assigns_beats(self):
        raw = _sample_raw_plan()
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        self.assertEqual(plan.scenes[0].beat_type, "hook")
        beats = {s.beat_type for s in plan.scenes}
        self.assertIn("hook", beats)

    def test_audio_bus_single_whoosh_layer(self):
        raw = _sample_raw_plan()
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        # P0-07: stoic uses sparse arc transitions, not per-cut whoosh stack
        self.assertLessEqual(len(plan.audio_events), 6)
        whooshes = [e for e in plan.audio_events if e.sound == "whoosh"]
        self.assertGreaterEqual(len(whooshes), 1)
        self.assertFalse(plan.effect_manifest.get("item_108_pink_noise"))
        self.assertFalse(plan.effect_manifest.get("item_141_breaths"))
        self.assertFalse(plan.effect_manifest.get("item_87_sonic_watermark"))
        self.assertFalse(plan.effect_manifest.get("item_112_whoosh_ding"))
        for w in whooshes:
            self.assertAlmostEqual(w.volume, 0.108, places=2)
        subs = [e for e in plan.audio_events if e.sound == "sub_impact"]
        self.assertEqual(len(subs), 0)
        clocks = [e for e in plan.audio_events if e.sound == "clock_tick"]
        self.assertEqual(len(clocks), 0)  # no quiz beat

    def test_heavy_niche_keeps_full_whoosh_layer(self):
        raw = _sample_raw_plan()
        plan = compile_director_plan(raw, title="Karanlık psikoloji manipülasyon", niche_id="7_dark_psychology")
        whooshes = [e for e in plan.audio_events if e.sound == "whoosh"]
        self.assertEqual(len(whooshes), len(plan.scenes) - 1)
        self.assertTrue(plan.effect_manifest.get("item_108_pink_noise"))

    def test_quiz_beat_gets_clock(self):
        scenes = [
            ScenePlan(index=0, narration="Tahmin et kaç saniye kaldı?", duration=3.0, t0=0, t1=3, beat_type="quiz"),
            ScenePlan(index=1, narration="Cevap stoacılıktır.", duration=3.0, t0=3, t1=6, beat_type="conflict"),
        ]
        # pad to 14
        for i in range(2, 14):
            scenes.append(ScenePlan(index=i, narration=f"Kural {i}", duration=3.0, t0=i*3, t1=(i+1)*3))
        plan = DirectorPlan(title="Quiz", niche_id="9_five_facts", scenes=scenes)
        plan = solve_timeline(plan)
        # force one quiz
        plan.scenes[2].beat_type = "quiz"
        plan.scenes[2].narration = "Tahmin et doğru cevap nedir?"
        build_audio_events(plan)
        clocks = [e for e in plan.audio_events if e.sound == "clock_tick"]
        self.assertGreaterEqual(len(clocks), 1)

    def test_placeholder_scene_description_replaced(self):
        scenes = [
            ScenePlan(
                index=0,
                narration="Bitcoin grafigi su an tum piyasayi belirliyor dikkatli olun buradayiz.",
                duration=3.0,
                scene_description="(SCENE_DESCRIPTION)",
                search_queries=["bitcoin chart screen"],
            )
        ]
        out = apply_visual_intents(scenes, "8_crypto_market", title="Bitcoin şu an nerede")
        desc = (out[0].scene_description or "")
        self.assertNotIn("SCENE_DESCRIPTION", desc.upper())
        self.assertGreaterEqual(len(desc), 12)

    def test_crypto_strips_horror_search_queries(self):
        scenes = [
            ScenePlan(
                index=0,
                narration="Bitcoin grafigi su an tum piyasayi belirliyor dikkatli olun buradayiz.",
                duration=3.0,
                scene_description="Live crypto trading desk with glowing charts",
                search_queries=["horror reveal dramatic lightning strike", "bitcoin chart"],
            )
        ]
        out = apply_visual_intents(scenes, "8_crypto_market", title="Bitcoin")
        joined = " ".join(out[0].search_queries).lower()
        self.assertNotIn("horror", joined)

    def test_semantic_exclude(self):
        intent = VisualIntent(must_exclude=["skull", "ufo"])
        self.assertTrue(text_contains_excluded("creepy skull on table", intent.must_exclude))
        self.assertLess(
            semantic_relevance_score("creepy skull", "marcus aurelius", intent),
            0,
        )

    def test_pre_render_score(self):
        raw = _sample_raw_plan()
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        pre = pre_render_score(plan)
        self.assertIn("score", pre)
        self.assertTrue(pre["ok"])

    def test_validation_roadmap_items(self):
        raw = _sample_raw_plan()
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        v = validate_director_plan(plan)
        self.assertIn(88, v["roadmap_items_checked"])
        self.assertIn(494, v["roadmap_items_checked"])

    def test_sentence_safe_condense(self):
        from director.timeline import _condense_narration
        long = (
            "Öfkeyi yok etmek için önce nefes al. "
            "Sonra gerçeği kabul et ve eyleme geç. "
            "Bu üçüncü cümle kesilmemeli çünkü bütçe dolu."
        )
        out = _condense_narration(long, max_words=12)
        self.assertLessEqual(len(out.split()), 12)
        self.assertTrue(out.endswith((".", "!", "?")))
        self.assertNotIn("kesilmemeli", out)  # third sentence dropped whole

    def test_condense_no_dangling_single_sentence(self):
        from director.timeline import _condense_narration
        one = (
            "Marcus Aurelius bugün yaşasaydı sana tam olarak şunu söylerdi "
            "ve içindeki o öfkeyi yakardın çünkü stoacılık böyle öğretir."
        )
        for max_words in (10, 12, 14, 16):
            out = _condense_narration(one, max_words=max_words)
            self.assertLessEqual(len(out.split()), max_words, msg=f"budget {max_words}")
            self.assertTrue(out.endswith((".", "!", "?")), msg=out)
            tail = out.rstrip(".!?").split()[-1].lower()
            self.assertNotIn(tail, {"ve", "ama", "çünkü", "asla", "olarak", "tam"})

    def test_inflated_narration_passes_integrity_gate(self):
        raw = _sample_raw_plan()
        for s in raw["scenes"]:
            s["narration"] = (
                s["narration"]
                + " Bir cümle daha eklenir çünkü test uzun olsun ve Marcus içindeki ateşi yakardı."
            )
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        qt = plan.quality_thresholds
        wc = len(plan.full_narration.split())
        budget = int(qt.max_duration * 2.5 * qt.max_audio_speed) + 2
        self.assertLessEqual(wc, budget)
        issues = check_narration_integrity(plan)
        self.assertFalse(any(i.startswith("fragment") for i in issues), msg=issues)
        pre = pre_render_score(plan)
        self.assertTrue(pre["ok"], msg=pre["issues"])

    def test_ellipsis_scene_vs_full_not_false_stale(self):
        """Trailing '...' normalize asymmetry must not flag fragment_sentence_full."""
        raw = _sample_raw_plan(n=3)
        plan = compile_director_plan(raw, title=raw["title"], niche_id="8_crypto_market")
        plan.scenes[0].narration = (
            "Bitcoin şu an kritik destek seviyesinde sıkışıyor ve yatırımcılar nefesini tutuyor..."
        )
        plan.scenes[1].narration = (
            "Bu seviyeyi geçerse tüm piyasa dengesi bir anda değişebilir, dikkatli olun."
        )
        plan.scenes[2].narration = (
            "Hacim artmadan kırılım gelirse tuzak olabilir, planına sadık kal ve bekle."
        )
        # Full keeps mid-text ellipsis form that per-scene normalize would collapse.
        plan.full_narration = (
            plan.scenes[0].narration.replace("...", "…")
            + " "
            + plan.scenes[1].narration
            + " "
            + plan.scenes[2].narration
        )
        issues = check_narration_integrity(plan)
        self.assertNotIn("fragment_sentence_full", issues, msg=issues)

    def test_solve_timeline_enforces_word_budget(self):
        raw = _sample_raw_plan()
        # Inflate narration to force condense
        for s in raw["scenes"]:
            s["narration"] = s["narration"] + " Bir cümle daha eklenir çünkü test uzun olsun."
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        qt = plan.quality_thresholds
        wc = len(plan.full_narration.split())
        budget = int(qt.max_duration * 2.5 * qt.max_audio_speed) + 2
        self.assertLessEqual(wc, budget)

    def test_fit_tts_hard_fail_when_too_long(self):
        from director.timeline import fit_tts_to_timeline
        import tempfile, wave, struct
        raw = _sample_raw_plan()
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        # Synthetic 90s mono wav — cannot fit into 48s even at 1.35×
        path = tempfile.mktemp(suffix="_long.wav")
        fr = 8000
        nframes = fr * 90
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(fr)
            w.writeframes(b"\x00\x00" * nframes)
        try:
            with self.assertRaises(RuntimeError) as ctx:
                fit_tts_to_timeline(path, plan, word_timings=[])
            self.assertIn("494", str(ctx.exception))
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def test_ssml_timing_sanitize(self):
        from subtitle_generator import _clean_timings
        dirty = [
            {"text": "Marcus", "offset": 0.0, "duration": 0.2},
            {"text": "xmlns", "offset": 0.2, "duration": 0.1},
            {"text": 'xml:lang="tr-TR"', "offset": 0.3, "duration": 0.1},
            {"text": "<speak>", "offset": 0.4, "duration": 0.1},
            {"text": "Aurelius", "offset": 0.5, "duration": 0.2},
        ]
        cleaned = _clean_timings(dirty)
        texts = [c["text"] for c in cleaned]
        self.assertEqual(texts, ["Marcus", "Aurelius"])

    def test_broken_narration_fails_semantic_gate(self):
        raw = _sample_raw_plan()
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        # User-reported Marcus condense artifacts (post-compile injection)
        plan.scenes[0].narration = "Marcus Aurelius bugün yaşasaydı."
        plan.scenes[1].narration = "Öfkeni yok etmek için ilk kural."
        plan.scenes[2].narration = "Karşındakinin kusuru seni değil, insanların hataları senin huzurunu asla."
        plan.scenes[3].narration = "İkinci kural olaylar değil, senin onlara."
        plan.full_narration = " ".join(s.narration for s in plan.scenes)
        issues = check_narration_integrity(plan)
        self.assertTrue(any(i.startswith("fragment") for i in issues))
        pre = pre_render_score(plan)
        self.assertFalse(pre["ok"])
        v = validate_director_plan(plan)
        self.assertFalse(v["ok"])

    def test_user_sample_broken_phrases_fail_gate(self):
        """Exact broken Shorts transcript fragments must never pass pre-render gate."""
        raw = _sample_raw_plan(n=4)
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        broken = (
            "Marcus Aurelius bugün yaşasaydı. Öfkeni yok etmek için ilk kural. "
            "Karşındakinin kusuru seni değil, insanların hataları senin huzurunu asla. "
            "İkinci kural olaylar değil, senin onlara."
        )
        plan.scenes[0].narration = broken
        plan.full_narration = broken
        issues = check_narration_integrity(plan)
        self.assertTrue(any("fragment" in i for i in issues), msg=issues)
        pre = pre_render_score(plan)
        self.assertFalse(pre["ok"], msg=pre)

    def test_split_scenes_distinct_visual_intent(self):
        """P0-06: cadence splits must fork search_queries + visual_intent.subject."""
        scenes = []
        for i in range(4):
            scenes.append({
                "narration": (
                    f"Marcus Aurelius stoacı kural {i + 1} öfkeyi yok eder. "
                    "Zihni sakin tutmak için nefes al ve gerçeği kabul et. "
                    "Bu ikinci cümle split tetiklemek için yeterince uzun olmalı."
                ),
                "duration": 3.0,
                "search_queries": ["creepy skull dark table"],
            })
        raw = {
            "title": "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı",
            "scenes": scenes,
        }
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        self.assertGreaterEqual(len(plan.scenes), 8)
        for i in range(1, len(plan.scenes)):
            prev = plan.scenes[i - 1]
            curr = plan.scenes[i]
            same_subject = prev.visual_intent.subject == curr.visual_intent.subject
            same_queries = prev.search_queries == curr.search_queries
            self.assertFalse(
                same_subject and same_queries,
                msg=(
                    f"adjacent {i - 1}/{i} share subject+queries: "
                    f"{prev.visual_intent.subject!r}"
                ),
            )

    def test_compile_strips_ai_cliches_p1_09(self):
        """P1-09: Item 134 cliché cleanse runs before compile."""
        raw = _sample_raw_plan(n=3)
        raw["scenes"][0]["narration"] = (
            "Sonuç olarak, bu nedenle öfkeyi kontrol etmek kritiktir."
        )
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        narr = plan.scenes[0].narration.lower()
        self.assertNotIn("sonuç olarak", narr)
        self.assertNotIn("bu nedenle", narr)

    def test_tape_stop_sparse_stoic_only_shock_p1_10(self):
        """P1-10: stoic sparse skips contrast keyword tape-stop unless shock beat."""
        raw = _sample_raw_plan(n=4)
        raw["scenes"][1]["narration"] = "Ama aslında gerçek tam burada ortaya çıkar."
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        stops = collect_tape_stop_times(plan)
        self.assertEqual(stops, [])

        plan.scenes[2].beat_type = "shock"
        stops = collect_tape_stop_times(plan)
        self.assertEqual(len(stops), 1)
        self.assertAlmostEqual(stops[0], plan.scenes[2].t0, places=2)

    def test_tape_stop_heavy_niche_contrast_p1_10(self):
        """P1-10: heavy niches tape-stop on contrast cues at scene t0."""
        raw = _sample_raw_plan(n=4)
        raw["scenes"][2]["narration"] = "Fakat asıl sır tam burada ortaya çıkar, dikkatle dinle ve not al."
        raw["scenes"][2]["scene_description"] = "Dark psychology manipulation scene with dramatic shadow lighting"
        plan = compile_director_plan(raw, title="Karanlık psikoloji", niche_id="7_dark_psychology")
        contrast_scenes = [
            s for s in plan.scenes if "fakat" in (s.narration or "").lower()
        ]
        self.assertGreaterEqual(len(contrast_scenes), 1)
        stops = collect_tape_stop_times(plan)
        self.assertIn(contrast_scenes[0].t0, stops)

    def test_bgm_ducking_sidechain_in_mix_p1_11(self):
        """P1-11: mix_narration_and_bgm uses 80ms/200ms narration sidechain ducking."""
        import inspect
        from bgm_manager import mix_narration_and_bgm
        src = inspect.getsource(mix_narration_and_bgm)
        self.assertIn("sidechaincompress", src)
        self.assertIn("attack=80", src)
        self.assertIn("release=200", src)

    def test_marcus_breaking_news_plan_preserves_narration(self):
        """User 14-scene Marcus breaking-news plan must not be shredded on compile."""
        scenes = [
            "SON DAKİKA! Bu acil stoacı kural öfkenizi anında bitirecek, hemen dinleyin!",
            "Roma İmparatoru Marcus Aurelius'un gizli bilgileri bugün sızdırıldı, işte detaylar!",
            "Birinci kural: Kontrol edemediğin olaylara asla öfkelenme, enerjini koru ve sakin kal!",
            "Dış dünya senin iraden dışında; sakin kal ve tepkini kontrol altında tut!",
            "İkinci kural: Başkalarının davranışlarına asla öfkelenme, huzurunu koru ve ilerle!",
            "Onların kusuru senin huzurunu asla bozamaz, tavrını yalnızca sen belirlersin!",
            "Üçüncü kural: Gelecekte olacaklara asla öfkelenme, endişeyi bırak ve eyleme geç!",
            "Endişe sadece zihnini yorar, harekete geç ve kontrolü ele al!",
            "Dördüncü kural: Kendi hatalarına bile asla öfkelenme, ders al ve ilerle!",
            "Her hata bir ders, her düşüş bir kalkış fırsatıdır, unutma!",
            "Marcus Aurelius bu kuralları her gün uygulardı, sen de uygulayabilirsin!",
            "Sen de bugün uygula, öfkeni kontrol et ve zihnini sakin tut!",
            "Bu kuralları paylaş, birlikte sakin kalalım ve birbirimize destek olalım!",
            "Takip et, daha fazla stoacı bilgi için kanalda kal ve yorum yap!",
        ]
        raw = {
            "title": "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı",
            "scenes": [
                {
                    "narration": n,
                    "duration": 3.0,
                    "scene_description": "Cinematic stoic marble statue portrait in dramatic golden light",
                }
                for n in scenes
            ],
        }
        plan = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        self.assertIn("asla öfkelenme", plan.full_narration)
        self.assertNotIn("gizli.", plan.full_narration)
        self.assertNotIn("Bunu aklında tut", plan.full_narration)
        for s in plan.scenes:
            self.assertGreaterEqual(
                len((s.narration or "").split()),
                8,
                msg=f"scene {s.index} too short: {s.narration!r}",
            )
        integrity = check_narration_integrity(plan)
        self.assertFalse(any(i.startswith("fragment") for i in integrity), msg=integrity)
        pre = pre_render_score(plan)
        self.assertTrue(pre["ok"], msg=pre.get("issues"))

    def test_marcus_asset_plan_auto_repaired_passes_narration_gate(self):
        asset = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "Marcus_Aureliusun_Ofkeyi_Yok_Eden_3_Stoaci_Kurali",
            "plan.json",
        )
        if not os.path.exists(asset):
            self.skipTest("Marcus asset plan missing")
        import json
        with open(asset, encoding="utf-8") as f:
            raw = json.load(f)
        plan = compile_director_plan(raw, title=raw["title"], niche_id=raw.get("niche_id", "6_stoic_philosophy"))
        pre = pre_render_score(plan)
        integrity = check_narration_integrity(plan)
        narr_block = [
            i for i in pre.get("issues", [])
            if i.startswith("fragment") or i.startswith("low_words")
            or i.startswith("empty_narration") or i.startswith("no_terminal")
        ]
        self.assertFalse(narr_block, msg=f"narration blockers: {narr_block}, integrity: {integrity}")


class TestTopicIntelligenceMatrix(unittest.TestCase):
    """P1-02: 20+ topic → niche resolution matrix (regex, alias, fuzzy, hybrid)."""

    TOPIC_CASES = [
        ("Marcus Aurelius stoacı kurallar", "1_news_flash", "6_stoic_philosophy"),
        ("whatsapp mesajları dram hikayesi", "1_news_flash", "20_whatsapp_chat_story"),
        ("AITA annem beni evden attı", "1_news_flash", "2_reddit_confessions"),
        ("SON DAKİKA deprem haberi", "6_stoic_philosophy", "1_news_flash"),
        ("bitcoin fiyatı düştü kripto", "1_news_flash", "8_crypto_market"),
        ("karanlık psikoloji manipülasyon", "1_news_flash", "7_dark_psychology"),
        ("yanlış bilinen 5 mit", "1_news_flash", "27_common_myths_busted"),
        ("tercih et uyumak mı yemek mi", "1_news_flash", "4_would_you_rather"),
        ("bayrak tahmin oyunu hangi ülke", "1_news_flash", "5_guess_flag_country"),
        ("bermuda üçgeni ufo gizemi", "1_news_flash", "13_mystery_paranormal"),
        ("Mbappe transfer haberi", "1_news_flash", "15_football_transfers"),
        ("sigma gigachad karakter analizi", "1_news_flash", "24_sigma_character_study"),
        ("minecraft split screen gameplay", "1_news_flash", "3_split_gameplay"),
        ("zengin olmak pasif gelir", "1_news_flash", "16_wealth_entrepreneurship"),
        ("chatgpt yapay zeka ipuçları", "1_news_flash", "21_ai_tools_hacks"),
        ("koç burcu astroloji yorumu", "1_news_flash", "18_astrology_horoscope"),
        ("netflix film özeti spoiler", "1_news_flash", "14_movie_summaries"),
        ("rüyada yılan görmek tabiri", "1_news_flash", "28_dream_meanings"),
        ("lamborghini süper araba", "1_news_flash", "31_supercars_automotive"),
        ("protein tozu fitness kas", "1_news_flash", "23_fitness_nutrition_hacks"),
        ("kuran ayeti dini söz", "1_news_flash", "10_religious_quotes"),
        ("Hz Peygamber in en çok tekrar ettiği o dua bugün hayatınızı değiştirebilir", "6_stoic_philosophy", "10_religious_quotes"),
        ("stoacilik disiplin motivasyon", "13_mystery_paranormal", "6_stoic_philosophy"),
        ("flaş haber trafik kaza", "6_stoic_philosophy", "1_news_flash"),
    ]

    def test_topic_niche_matrix(self):
        for topic, requested, expected in self.TOPIC_CASES:
            with self.subTest(topic=topic[:40]):
                got = resolve_niche_from_topic(topic, requested)
                self.assertEqual(got, expected, msg=f"{topic!r} -> {got}, want {expected}")

    def test_topic_intelligence_methods(self):
        intel = resolve_topic_intelligence("Marcus Aurelius stoacı", "1_news_flash")
        self.assertEqual(intel["resolved_niche"], "6_stoic_philosophy")
        self.assertIn(intel["match_method"], ("regex_lock", "alias", "fuzzy", "hybrid", "passthrough"))
        self.assertTrue(intel["locked"])

    def test_hybrid_niche_detection(self):
        intel = resolve_topic_intelligence(
            "Marcus Aurelius cyberpunk neon distopya gelecek",
            "1_news_flash",
        )
        self.assertEqual(intel["resolved_niche"], "6_stoic_philosophy")
        self.assertEqual(intel["hybrid_niche"], "stoic_cyberpunk")
        self.assertEqual(intel["match_method"], "regex_lock")

    def test_fuzzy_fallback_trending_keyword(self):
        intel = resolve_topic_intelligence("gündem breaking news gelişme", "6_stoic_philosophy")
        self.assertEqual(intel["resolved_niche"], "1_news_flash")


class TestChannelScopedOutput(unittest.TestCase):
    """P3-30: per-channel folder paths."""

    def test_default_channel_uses_legacy_dirs(self):
        paths = config.channel_paths(None)
        self.assertEqual(paths["slug"], "default")
        self.assertEqual(paths["assets_dir"], config.ASSETS_DIR)
        self.assertEqual(paths["output_dir"], config.OUTPUT_DIR)

    def test_named_channel_scoped_dirs(self):
        paths = config.channel_paths("Stoic TR Channel")
        self.assertEqual(paths["slug"], "stoic_tr_channel")
        self.assertIn("channels", paths["assets_dir"])
        self.assertIn("stoic_tr_channel", paths["assets_dir"])
        self.assertTrue(os.path.isdir(paths["assets_dir"]))


class TestFFmpegGraphHelpers(unittest.TestCase):
    def test_build_scene_filter_chain(self):
        from render.ffmpeg_graph import build_scene_filter_chain, get_look_filters
        chain = build_scene_filter_chain(0, 3.0, 1080, 1920, 0, enable_ken_burns=True)
        self.assertIn("trim=duration=3.000", chain)
        self.assertIn("[v0]", chain)
        look = get_look_filters(1080, 1920, anti_duplicate=True)
        self.assertIn("unsharp", look)
        self.assertIn("eq=", look)


if __name__ == "__main__":
    unittest.main()
