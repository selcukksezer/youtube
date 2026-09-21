# Senaryo Yazımı — Canlı Durum Raporu

**Tarih:** 2026-09-21  
**Kapsam:** UI → `/api/script/generate` → generator → fallback → doğrulama → director → JSON → sahne kartları  
**Kaynak:** Diskteki **güncel kod**. `SCENARIO_WRITING_AUDIT.md` (A–H Done) **doğrulanmış gerçek değil**.  
**Canlı kanıt (eski dump):** Bitcoin stub + `(SCENE_DESCRIPTION)` + `/14` + horror query. **Kodda P0-1..5 kapatıldı** (2026-09-21 niş paket). Canlı teyit: `./run_ui.sh` + Senaryoyu Yeniden Üret.

**Sonuç cümlesi:** Ortak zarf şema/süre; içerik niş paketi. Dini konu `10_religious_quotes` / family `religious`. Süre 38–60, tavan 60, 48 mıknatıs yok. P0 kapalı.

---

## Canlı arıza (Peygamber duası → stoacı Roma) — KAPANDI

Konu: `Hz Peygamber in en çok tekrar ettiği o dua bugün hayatınızı değiştirebilir`. Sunucu yeni koddaydı (Cadence 13 sahne) ama 13× mood `STOIC CALM CONTEMPLATIVE`, Marcus/Roma query, `(SCENE_DESCRIPTION)`, 48.0s.

| Bug | Kök neden | Fix |
|-----|-----------|-----|
| Niş | `TOPIC_NICHE_LOCK` dini regex yalnız `dini\|ayet\|hadis\|kuran\|ibadet` — `peygamber`/`dua` yok. Fuzzy `dua` bazen tutardı; UI stoacı passthrough da mümkün. | Lock: peygamber, dua, Allah, namaz, sure, sahabe, sünnet. `kaza` artık `\bkaza\b` (`kazanç` haber çalmaz). |
| Aile | `NICHE_FAMILY_MAP["10_religious_quotes"] = "stoic"` → fallback `_generate_stoic_scenes`, motif bankası Marcus/heykel. | Family `religious`. İslami fallback + motif (cami, Kuran, dua elleri, hat). `must_exclude`: statue/idol/marcus/roman bust/alcohol/prophet face. |
| Placeholder | `apply_visual_intents` yetmez: compile exception veya generator placeholder bırakınca router ham plan döner. UI `GÖRSEL AÇIKLAMA: (SCENE_DESCRIPTION)`. | `sanitize_plan_scene_descriptions` router sınırında (`research_router` 184, `video_router` 278/431). `scene_description` substring yasak. |
| Mood 13× aynı | Stoic bankasında `mood_palette` yok; `apply_visual_intents` hepsine `intent.mood` yazdı. | Palette + fallback beat mood. |
| 3.2s ×9 | `target=48` + cadence 1.2–4.5 son sahneleri kısalttı. | Cadence taban 3.2 (band izin verince). Hedef kelime/TTS, 48 değil. |

Kanıt HTTP (port **8012**, `SHORTS_FORCE_PROCEDURAL_FALLBACK=1`): `/tmp/script_generate_religious.json` — niche `10_religious_quotes`, 12 sahne, 60.0s, query `mosque/quran/prayer`, placeholder yok, 8 mood, 0 sahne <3.2s. Aynı yol: crypto `/tmp/script_generate_crypto.json`, astroloji `/tmp/script_generate_astrology.json`.

Test: `tests/test_niche_routing_tr.py`, `tests/test_shorts_duration_band.py`, `tests/test_script_generate_placeholder_router.py`, `tests/test_scenario_niche_packs.py::test_religious_fallback_is_not_stoic`.

---

## 45/48 kilidi kaldırıldı

48 mıknatıs değil. Hedef = `clamp(kelime / 2.45 wps, 38, 60)`. Yalnız 60 tavan (Shorts loop). 55s script 48’e sıkıştırılmaz. TTS ≤60s iken speed×1.15 yok.

| Dosya | Satır | Ne değişti |
|-------|-------|------------|
| `director/schema.py` | 124–148 | `TTS_WORDS_PER_SEC=2.45`, `natural_target_duration`, `shorts_word_budget` (≥172), `QualityThresholds.target_duration=0` |
| `director/timeline.py` | 20–34, 342, 367, ~448 | Beat % (0–7/45/75/100); hedef kelimeden; tavan 172 kelime; `fit_tts_to_timeline` TTS≤60 ise speed=1.0 |
| `viral_retention_engine.py` | 549–593, 588+ | Cadence taban 3.2s; hikaye arkı süreye orantılı |
| `scenes/fallback.py` | 105–140, 1155 | Finalize TTS uzunluğu (48 magnet yok); religious dispatcher |
| `scenes/prompts.py` | 8–27, 87 | Zarf: “konu ne kadar istiyorsa, 60’ı aşma”; 38–48 varyant silindi |
| `scenes/generator.py` | 125, 169, 420, 486 | Fingerprint 4.0s; `SHORTS_FORCE_PROCEDURAL_FALLBACK`; kelime 172; sanitize çıkış |
| `scenes/narration_validate.py` | 158–210, 433 | Placeholder substring; `sanitize_plan_scene_descriptions`; default 172 |
| `director/validate.py` | 41–48 | 42s≈118 kelime uyarısı kalktı; 60s tavan |
| `research_service.py` | 79, 100 | `42.0 / n` → 4.0s avg |
| `server_core/render_worker.py` | 800 | Log: hız yalnız 60s tavanı aşınca |
| `static/app.js` | 579, 2127–2148, 2550 | “hedef 48” yok; ark %; dengele 38 veya 60 |
| `static/index.html` | 659, 685–688, 702 | Chip tavan 60; ark etiket id |
| `niche_templates.py` | 1007, 1288 | religious family; pack `target_duration=0` |
| `ROADMAP_AUDIT.md` | 266, 274, 494 | Done kaldı; kanıt “38–60, cap 60, content-driven” |

Test: `test_compiled_150_word_plan_not_shrunk_to_48`, `test_fit_tts_no_speedup_when_under_60`, `test_ui_arc_labels_are_percent_based`.

Madde 88 / 266 / 274 / 494 **Done**. 45s hikaye arkı artık yüzde.

---

## 1. Akış

Uçtan uca 11 adım. Sahip: dosya + fonksiyon.

| # | Adım | Sahip | Ne yapar |
|---|------|--------|----------|
| 1 | Konu al, varsa eski planı göster | `static/app.js` `generateScriptFromTopic` (1919–1998) | `forceRegenerate` yoksa ve `hasExistingPlan()` true ise **API çağırmaz**, timeline’a gider. Konuyu `sanitizeTopicTitleForDisplay` ile kırpar, `keyword` olarak gönderir. |
| 2 | HTTP üret | `routers/research_router.py` `api_generate_script` (78–193) | Niş kilit (`resolve_topic_intelligence`), `generate_scenes` veya Reddit rewrite, stok adayları, enrich + auto-repair, `compile_director_plan`, QualityGate **notu**, planı JSON döner. Kapı kırmızı olsa da **plan yine döner**. |
| 3 | AI senaryo | `scenes/generator.py` `generate_scenes` (141–480) | Prompt + user mesajı; Gemini/OpenAI zinciri; 429’da circuit; şema retry; `plan_quality_usable` fail → prosedürel fallback. |
| 4 | Prompt | `scenes/prompts.py` `get_rotated_system_prompt` / `PROMPT_TR` | 8–16 sahne, 38–60 sn; konu ne kadar istiyorsa, 60’ı aşma. |
| 5 | Zenginleştirme | `scenes/enrichment.py` (`enrich_cinematic_search_queries`, `enforce_visual_cadence_14`, `enrich_audio_visual_contrast_scenes`, `enrich_plan_scenes`) | Sinematik sonek, cadence pad, **Item 273 şok/horror query**, kapanış bakışı. Generate **ve** `/api/plan/validate` tekrar çalıştırır. |
| 6 | AI yok / kalitesiz | `scenes/fallback.py` `_generate_procedural_fallback_scenes` (891–940) + `_generate_crypto_market_scenes` (783–888) | Kripto nişinde 14 sahne, her biri `duration: 3.0` → **42 sn**. Kardeş ajan anlatımı uzatıyor + `_pad_narration_to_min_words`; sahne sayısı hâlâ 14. |
| 7 | Anlatım kapısı | `scenes/narration_validate.py` (`scene_narration_usable`, `plan_quality_usable`, `repair_post_hook_word_budget`) | Sahne ≥10 kelime (diskte; HEAD’de 12’ydi). Stub + placeholder AI planını teoride reddeder. `min_ratio=1.0` = tüm sahneler. |
| 8 | Çeşitlilik | `scenes/plan_linter.py` `lint_plan_diversity` | Mood/query tekrar + stub uyarısı. `weak` ise generator prosedürel fallback’e geçer (AI planı için). |
| 9 | Derleme | `director/compiler.py` `compile_director_plan` (79–243) | Zayıf plan → prosedürel enjekte (`plan_needs_procedural_inject`, kardeş ajan). `solve_timeline`, visual intent, SFX, `to_legacy_plan`. |
| 10 | Süre / kelime | `director/timeline.py` `solve_timeline` | Hedef `natural_target_duration` (38–60). Kelime tavanı 172. Cadence ≥ `min_scenes=8`. |
| 11 | Kart + panel | `static/app.js` `renderTimelineScenes` (2154–2266), `updateStudioQualityPanel` (186–218) | `scene_description` kutusu, “X klm”, Cadence `n/14`, süre yeşil **yalnız 38–48 sn**. `planVersion: 2` localStorage. |

Render (`server_core/render_worker.py`) bu raporun dışında (randint crash ayrı ajan).

---

## 2. Şu an ne kırık

Kanıt: kullanıcının Bitcoin dump’u + kod. Öncelik P0/P1/P2.

**2026-09-21 kapanış (niş paket mimarisi):** P0-1..P0-5 kodda kapatıldı. Tek niş (kripto) özel kasası yok — 35 niş `get_scenario_pack` ile ayrı kural taşır. Ortak zarf yalnızca JSON/8–16/38–60/min 10 kelime. Item 88 cadence helper ve Item 273 mystery/dark şok query duruyor. ROADMAP_AUDIT sayacı değişmedi.

### P0 — kapatılanlar

**P0-1. JS konu kırpma Türkçe harfi siler — KAPANDI**  
`sanitizeTopicTitleForDisplay` artık `/[^\p{L}\p{N}\s\-&]/gu`. API’ye ham `keyword: topic`. Display hâlâ emoji/hashtag kırpar.

**P0-2. 6 kelimelik stub cache — KAPANDI (UI)**  
`planHasBrokenNarration` min 10 kelime + `sceneDescriptionUsable`. Bozuk plan “Oluştur” ile sessiz açılmaz, regen zorlanır. Kart `<10` kırmızı. Generate kapısı hâlâ plan döndürebilir (P1).

**P0-3. `(SCENE_DESCRIPTION)` — KAPANDI (router sınır)**  
`apply_visual_intents` + generator synthesize + `sanitize_plan_scene_descriptions` API JSON’da.

**P0-4. Süre 38–60 / cadence 8–16 — KAPANDI (48 magnet yok)**  
UI yeşil 38–60, tavan 60. Fallback TTS uzunluğu. `enforce_visual_cadence_14` helper duruyor (Madde 88).

**P0-5. Bozuk plan yeniden üretilmez — KAPANDI**  
Bozuk cache silinir; Oluştur API’ye gider.

### P1 — kalan

**P1-1. 14 sahne kutsal** — UI ve prompt 8–16. Bazı prosedürel şablonlar (kripto/haber/stoa) hâlâ 14 sahne üretir; bu izin bandında, zorunluluk değil.

**P1-2. Item 273 horror** — KAPANDI niş paketiyle: şok query yalnız `mystery` + `dark` family. Crypto/astro/quiz/entertainment yasak. Mystery’de Item 273 duruyor.

**P1-3. `low_visual_alignment`** — açık (TR×EN token).

**P1-4. 429 şablon şeffaflığı** — açık (banner yok). Fallback artık niş paketine göre; hayvan konusuna Bitcoin şablonu basılmaz.

**P1-5. Kelime bütçesi** — kısmen (tavan 172).

**P1-6. QualityGate generate’de hard-fail değil** — açık.

### P2
`planVersion: 2`, `max_tokens`, prompt varyant envelope’da 38–60; `director/validate.py` 42s yorumu duruyor.

### Audit notu

Madde 88 (`enforce_visual_cadence_14`) ve Madde 273 (mystery/dark şok) **Done kaldı**. Madde 494: 38–60 / tavan 60, content-driven hedef. ROADMAP_AUDIT sayacı değişmedi.


### Audit A–H vs gerçek

| Batch (audit iddiası) | Disk gerçeği |
|----------------------|--------------|
| A — AI stub reddi | `plan_quality_usable` + şema var. Canlı 6 KLM durmadı: cache, pad, eski süreç, kapı uyarı. |
| B — planVersion / regenerate | Var. `hasExistingPlan` hâlâ API’yi atlar. Kırık eşik 5 kelime. |
| C — kripto prosedürel | Şablon zenginleşiyor (kardeş ajan). Hâlâ 14×3.0=42. Konu JS’te bozulursa şablon “u an” ile yazılır. |
| D — word budget 160 | Hook sonrası keser; director (HEAD) tekrar 110’a keser. Stub üretir. |
| E — diversity linter | AI zayıfsa fallback. Fallback’i `procedural_fallback` ile lint’ten muaf tutar (`generator.py` 419). |
| F/G — 429 / API | Circuit var. Sonuç şablon, kaliteli senaryo değil. Test `plan_quality_usable` şablona bakıyor. |
| H — UI kart | `scene_description` kutusu var; placeholder’ı temizlemez. Cadence /14, süre 38–48. |

---

## 3. Basit (S) / orta (M) / büyük (L)

Süre: operatör saati. Kardeş ajanın kelime/pad işi **S’yi kapatmaz**.

### S — saatler

1. JS sanitize: `\w` yerine Unicode harf (`\p{L}`) veya kırpmayı kaldır; API’ye ham konu. Kabul: `şu an` başlıkta kalır.  
2. `planHasBrokenNarration`: min kelime 10 + `scene_description` placeholder. Cache stub silinir.  
3. “Oluştur” mevcut planı sessizce açmasın; konu değiştiyse üret.  
4. UI Cadence `n/8–16`, süre yeşil **38–60**.  
5. `apply_visual_intents`: placeholder `scene_description` boş kabul, motif cümlesi yaz.  
6. Item 273: kripto/finans nişinde horror query yok. `enrich_plan_scenes` validate’de şok query enjekte etmesin (veya must_exclude süz).  
7. Kart: `<10 kelime` kırmızı (şimdi 5).

### M — günler

1. Fallback süre: 14×3.0 kaldır. Sahne 8–16, toplam **hedef 48–60**, min 38.  
2. Timeline kelime tavanı `max_duration` (60s) × gerçek wps; sahne tabanı 12’nin altına inmesin; pad 6 kelimelik “Bunu aklında tut.” yasak.  
3. `api_generate_script`: `plan_quality_usable` fail ise planı **kabul etme** — fallback zorunlu ve UI `procedural_fallback` göstersin.  
4. Alignment: TR anlatımı EN query ile skorlama; niş motif token ekle veya dili ayır.  
5. Gemini 429: UI “kota — şablon kullanıldı” banner. Sessiz şablon yok.  
6. generate + validate çift `enrich_plan_scenes` / Item 273 — bir kez, niş-aware.

### L — tasarım

1. 14 sahne / 42 sn / Item 88 “cadence 14” mitini kır: kesim sayısı süreye bağlı, kutsal değil.  
2. Prosedürel şablon ≠ senaryo yazımı. Kota sonrası kısa retry veya “üretim durdu”.  
3. Tek kelime bütçesi (prompt 120–160, hook trim 160, director 110/172, validate 48×2.6) — bir kaynak.  
4. `scene_description` / `search_queries` / `visual_intent` tek sözleşme; placeholder şemada hard-fail, UI’da da.

---

## 4. Yanlış tasarım varsayımları

1. **14 sahne kutsal.** Retention = kesim sayısı sanılıyor. Shorts 8 sahne × ~6 sn de olur. UI `/14` cezalandırır.  
2. **42 / 48 sn tavan.** Kullanıcı 60’a kadar ister. `max_duration=60` var, hedef ve UI 48’de kilitli; fallback 42.  
3. **Stub “usable”.** 6–8 kelime + nokta + pad cümlesi kapıdan geçer (UI 5, auto-repair 3+3).  
4. **Placeholder görsel, query varsa olur.** `plan_quality_usable` boş desc’te query’ye düşer; dolu `(SCENE_DESCRIPTION)` düşmez ve kartta kalır.  
5. **Prosedürel fallback = başarı.** Log “OK”, 14 sahne, test yeşil. Konu bozulmuş, süre kısa, metin tekrar.  
6. **QualityGate bloklar.** Generate yolunda uyarı. `excluded_query` / `low_visual_alignment` hard-fail değil.  
7. **TR anlatım ↔ EN stok overlap = görsel uyum.** Dil skoru, içerik skoru değil.  
8. **Item 273 her nişe şok görsel.** Kripto climax’e horror query → kendi `must_exclude` listesini ihlal.  
9. **localStorage plan taze.** Version 2 + 7 gün. 6 kelimelik Bitcoin planı “yeni” sayılır.  
10. **Kardeş ajan bitince canlı düzelir.** Pad + 172 kelime stub/42 sn/JS ş/14 sahne/horror/cache’i çözmez.

---

## 5. Nasıl gelişir (sıra)

Her adım: ne değişir + kabul testi. Önce S, sonra M.

1. **JS Unicode konu.** Ham `inputTopic` API’ye. Test: `"Bitcoin şu an nerede Bu seviyeyi geçerse her şey değişir"` plan `title`/hook içinde `şu` ve `geçerse` durur.  
2. **Cache kapısı.** `planHasBrokenNarration` ≥10 kelime + usable `scene_description`. Eski Bitcoin dump restore edilmez; toast “yeniden üret”.  
3. **Placeholder sil.** Compile’da `scene_description_usable` false ise motif cümlesi. Kabul: kartta `(SCENE_DESCRIPTION)` yok.  
4. **Horror × finans.** Item 273 kripto/news finance’te atla; validate yeniden enjekte etmesin. Kabul: Bitcoin planında `excluded_query_scene_*` yok.  
5. **Süre bandı UI + fallback.** Fallback toplam `max(38, min(60, n * avg))` ama **42’ye kilitleme**; director hedef 52–58 veya kullanıcı 60. Kabul: yeni Bitcoin planı 50–60 sn, UI yeşil ≤60.  
6. **Sahne sayısı esnek.** Crypto `range(8, 13)` veya süreye göre. UI `/14` kalksın. Kabul: 10 sahnelik plan kırmızı cadence değil.  
7. **Kelime tavanı tek kaynak.** Director tavanı 60s×~2.3 wps (~140–160) **ve** sahne tabanı 12; pad en az 12 kelime. Kabul: hiçbir sahnede “6 KLM”.  
8. **Generate hard-fail.** `plan_quality_usable` false ise yanıt `status=ok` + zayıf AI planı değil; zorunlu zengin fallback **veya** 422 + mesaj. Kabul: stub AI JSON UI’ya düşmez.  
9. **429 şeffaflığı.** `procedural_fallback: true` banner. Kabul: kota bitince operatör şablon olduğunu bilir.  
10. **Alignment.** Skoru TR stem veya niş `must_include` ile hesapla. Kabul: temiz kripto planda `low_visual_alignment` yok.

Kardeş ajan (pad, MIN_WORDS 10, tavan 172, `plan_needs_procedural_inject`) **7’ye yardım eder, 1–6 ve 8–10’u bitirmez.** Çakışan edit yapma; o PR bitsin, sonra 1–6.

---

## 6. Doğrulama checklist (sonraki regen)

Sunucuyu **restart** et (diskteki kardeş ajan değişikliği yoksa eski süreç çalışır). Timeline’da **Senaryoyu Yeniden Üret** (sessiz “oluştur” değil). localStorage: Application → `shortsCurrentPlan` sil.

Konu (aynen): `Bitcoin şu an nerede Bu seviyeyi geçerse her şey değişir`

| Kontrol | Geçer | Kalan semptom (fail) |
|---------|--------|----------------------|
| Başlık / hook | `şu`, `geçerse` duruyor | `Bitcoin u an...` |
| Sahne kelime | Her kart **≥12** (ideal 15–25); “6 KLM” yok | 5–8 kelime, pad cümlesi |
| Görsel kutu | İngilizce 1 cümle, ≥12 karakter | `(SCENE_DESCRIPTION)`, `tbd`, boş |
| Sahne sayısı | 8–16, konuya göre; 14 zorunlu değil | Hep 14, UI `/14` fail |
| Süre (kart toplam) | 38–60; tercihen 50–60 | ~42 veya UI 48’de yeşil kilit |
| QualityGate | `excluded_query_scene_*` yok; `low_visual_alignment` yok veya açıklanmış | 5/6/7/9 + alignment |
| Fallback bayrağı | Kota varsa banner | Sessiz 14 sahnelik şablon “AI yazdı” |
| Cache | Sayfa yenile, aynı plan ancak kelime/desc kapıdan geçiyorsa | Eski 6 KLM geri geldi |
| `procedural_fallback` | Network JSON’da true ise şablon beklenir | true + yine stub/placeholder |

Hâlâ 6 KLM + placeholder + 42 sn + `u an` → **A–H kapanmadı.** Bu checklist kırmızıysa yeni batch “Done” yazma.

---

## Disk notu (kardeş ajan, 2026-09-21)

Uncommitted (özet):

- `scenes/fallback.py`: kripto/astro anlatım uzatma, `_pad_narration_to_min_words`, `_finalize_fallback_plan`. **14×3.0 duruyor.**  
- `scenes/narration_validate.py`: `MIN_WORDS` 12→10, `plan_needs_procedural_inject`, ortalama kelime kapısı.  
- `director/timeline.py`: kelime tavanı ~110→172.  
- `director/compiler.py`: inject `plan_needs_procedural_inject` kullanır.

Bu, prosedürel cümleleri 10 kelime eşiğine taşır. Kullanıcı dump’undaki JS kiriş, cache, 42 sn, 14 sahne, placeholder mapping, horror query, alignment **açık**.
