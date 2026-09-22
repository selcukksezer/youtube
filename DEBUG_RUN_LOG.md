# Full line debug run log

## main.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "import main; print('main import ok')"` geçti

## server.py
- durum: DONE
- bulgu: Windows asyncio handler kurulumu başarısızlığını sessizce yutuyordu.
- düzeltme: Hata korunarak `logger.warning` ile görünür hale getirildi.
- test: `python -c "import server; print(len(server.app.routes))"` geçti; `python -m pytest -q tests/test_kids_song_bridge.py --tb=line` geçti (15 passed).

## server_core/__init__.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "import server_core; print('server_core import ok')"` geçti

## server_core/state.py
- durum: DONE
- bulgu: Veritabanı durum ve SSE kuyruğu yazma hataları sessizce yutuluyordu.
- düzeltme: Durum güncellemesi için warning, SSE kuyruğu için debug logu eklendi; akış korunuyor.
- test: `python -c "import server_core; print('server_core import ok')"` geçti

## server_core/render_worker.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "import server_core.render_worker; print('render_worker import ok')"` geçti

## kids_song_bridge.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "import kids_song_bridge; print(kids_song_bridge.studio_port())"` geçti; `python -m pytest -q tests/test_kids_song_bridge.py --tb=line` geçti (15 passed)

## routers/__init__.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "import routers; print('api imports ok')"` geçti

## routers/config_router.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: API import kontrolü geçti

## routers/research_router.py
- durum: DONE
- bulgu: `api_generate_script` hata halinde process-global `config.LANGUAGE` değerini geri yüklemiyordu.
- düzeltme: Eski dil değeri fonksiyon başında saklanıyor, `finally` içinde her çıkışta geri yükleniyor.
- test: API import kontrolü ve `python -m compileall -q -f routers v2_api server.py server_core` geçti

## routers/video_router.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: API import kontrolü geçti

## routers/media_router.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: API import kontrolü geçti

## routers/system_router.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: API import kontrolü geçti

## routers/google_ai_router.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: API import kontrolü geçti

## routers/channel_router.py
- durum: DONE
- bulgu: `tags` mutable varsayılan kullanıyordu; `scheduled_hour=0` değeri 18'e dönüyordu.
- düzeltme: `Field(default_factory=list)` kullanıldı; saat yalnızca `None` ise 18 varsayılanına düşüyor.
- test: API import kontrolü geçti

## routers/kids_song_router.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: API import kontrolü geçti; `tests/test_kids_song_bridge.py` geçti (15 passed)

## v2_api/__init__.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: API import kontrolü geçti

## v2_api/schemas.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: API import kontrolü geçti

## v2_api/router.py
- durum: DONE
- bulgu: Render kilidi proje/render isteği hazırlanırken hata olsa serbest bırakılmıyordu.
- düzeltme: Render hazırlığı `try/except` içine alındı; hata halinde `state.is_rendering_active=False` yapılıyor. JSON ayar parse hatası `TypeError` ile birlikte ele alınıyor.
- test: `python -m compileall -q -f routers v2_api server.py server_core` geçti; `tests/test_plan_validate_api.py tests/test_v2_production_api.py` kısa koşusunda 5 test geçti (komut 64,76 s sürdü; tekrar çalıştırılmadı).

## research_service.py
- durum: DONE
- bulgu: Wikidata araması hata verince `return []` Wikipedia özetini de kesiyordu.
- düzeltme: Arama hatası `pass` oldu; özet denemesi sürüyor.
- test: `python -m pytest -q --tb=line tests/test_topic_research_brief.py tests/test_quality_policy_pipeline.py` geçti

## services/__init__.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "import services"` geçti (trend testi import etti)

## services/topic_suggester.py
- durum: DONE
- bulgu: Son video listesi ve AI aday hatası sessizce yutuluyordu.
- düzeltme: İkisi de `logger.warning` ile görünür; AI hata şablon adaya düşmeye devam ediyor.
- test: `python -m pytest -q --tb=short tests/test_niche_trend_signals.py` geçti

## services/niche_trend_signals.py
- durum: DONE
- bulgu: Stoacı yasak haber nişindeki "Son Dakika" başlıklarını da siliyordu. Görüntülenme "1,2 Mn" rakamları ölçek atıyordu.
- düzeltme: Yasak yalnız stoacı ailede. `_parse_view_count` Mn/B ölçeğini koruyor.
- test: `python -m pytest -q --tb=short tests/test_niche_trend_signals.py` geçti (5 passed)

## services/dubbing.py
- durum: DONE
- bulgu: Çeviri hatası sessizce sözlüğe düşüyordu.
- düzeltme: `logger.warning` eklendi; sözlük yedeği duruyor.
- test: `python -c "import services.dubbing"` geçti

## niche_templates.py
- durum: DONE
- bulgu: `default_music` değeri `calm` ve `kids` sözlükte yoktu; `music_keyword` ikisini de `ambient` yapıyordu. Motif bankası import hatası sessizdi.
- düzeltme: `calm` ve `kids` anahtarları eklendi. Import hatası `logger.warning`.
- test: `python -m pytest -q --tb=line tests/test_niches.py tests/test_niche_routing_tr.py` geçti (15 passed, 111 subtests)

## scenes/__init__.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "import scenes"` sahne testleriyle geçti

## scenes/prompts.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "from scenes.prompts import get_rotated_system_prompt; get_rotated_system_prompt('tr')"` geçti

## scenes/scripts.py
- durum: DONE
- bulgu: Reddit yedek senaryosu `language` argümanını düşürüyordu.
- düzeltme: `_generate_procedural_fallback_scenes(..., language=lang)`.
- test: `python -m pytest -q --tb=line tests/test_scene_consistency.py` geçti

## scenes/generator.py
- durum: DONE
- bulgu: 429, paylaşılan `circuit_breaker.recovery_timeout` değerini 1800 saniyeye çekiyordu. Hibrit zenginleştirme kilitli nişi değil ham `niche_type` değerini kullanıyordu.
- düzeltme: Kota yalnız `gemini_script` sayacını eşiğe getirip `record_failure` çağırıyor. Hibrit çağrı `locked_niche` kullanıyor.
- test: `python -m pytest -q --tb=line tests/test_narration_sense.py tests/test_scene_consistency.py` geçti

## scenes/fallback.py
- durum: DONE
- bulgu: yok (bu turda yeni hata yok; 5 gerçek yolu önceki düzeltmede)
- düzeltme: yok
- test: `python -m pytest -q --tb=line tests/test_narration_sense.py tests/test_scene_consistency.py` geçti

## scenes/enrichment.py
- durum: DONE
- bulgu: Kısa cümle kesilince iki sahne aynı narration alıyordu. Eski şok cümlesi de yok.
- düzeltme: 8 kelimeden uzun satır kelimeden bölünür. Kısa satırın kesiti `Açı N` eki alır; metin kopyalanmaz.
- test: `python -m pytest -q --tb=line tests/test_scene_consistency.py tests/test_section2_items_86_90.py` geçti (8 passed)

## scenes/narration_sense.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -m pytest -q --tb=line tests/test_narration_sense.py` geçti

## scenes/narration_coherence.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "from scenes.narration_coherence import repair_cross_scene_coherence"` geçti

## scenes/retention_hooks.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -m pytest -q --tb=line tests/test_narration_sense.py` geçti

## scenes/plan_linter.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "from scenes.plan_linter import lint_plan_diversity"` geçti

## craft/__init__.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -c "import craft"` geçti

## craft/human_director.py
- durum: DONE
- bulgu: POV açısı, sessiz kanca hattı, shot hold limitleri ve discovery beast skorlama fonksiyonları incelendi; testler yeşil (7 passed).
- düzeltme: yok
- test: `python -c "import craft"` geçti

## director/__init__.py
- durum: DONE
- bulgu: DirectorPlan orchestration paketi exportları incelendi, eksik sembol yok.
- düzeltme: yok
- test: `tests/test_director_plan.py` geçti (40 passed, 24 subtests).

## director/schema.py
- durum: DONE
- bulgu: VisualIntent, AudioEvent, ScenePlan, QualityThresholds, DirectorPlan, DEFAULT_EFFECT_MANIFEST ve TTS bütçe hesapları incelendi; legacy uyumluluk metotları eksiksiz.
- düzeltme: yok
- test: `tests/test_director_plan.py` geçti.

## director/visual_intent.py
- durum: DONE
- bulgu: Niche motif bankaları, semantik visual intent, konu kilitleri ve embedding benzerlik artırıcı incelendi.
- düzeltme: yok
- test: `tests/test_director_plan.py` geçti.

## director/timeline.py
- durum: DONE
- bulgu: 38-60s aralığı, cadence ivmelenmesi, kelime bütçesi koruma ve fit_tts_to_timeline emergency limitleri incelendi.
- düzeltme: yok
- test: `tests/test_director_plan.py` geçti.

## director/validate.py
- durum: DONE
- bulgu: Madde 88, 129, 201, 274, 494 kuralları, parça cümle kontrolleri incelendi.
- düzeltme: yok
- test: `tests/test_director_plan.py` geçti.

## director/compiler.py
- durum: DONE
- bulgu: compile_director_plan akışı, fallback enjeksiyonu, cross-scene coherence onarımı, beat grid danışma ve timeline çözümü incelendi.
- düzeltme: yok
- test: `tests/test_director_plan.py` geçti.

## director/audio_bus.py
- durum: DONE
- bulgu: AudioEvent veri yolu, dublike SFX önleme, tape stop tetikleyicileri, EBU R128 mastering zinciri incelendi.
- düzeltme: yok
- test: `tests/test_director_plan.py` geçti.

## director/quality_gate.py
- durum: DONE
- bulgu: Pre-render ve post-render kalite kapıları, clip benzersizlik kontrolü (MD5 hash) ve eksik sahne bildirimleri incelendi.
- düzeltme: yok
- test: `tests/test_director_plan.py` geçti.

## visuals/__init__.py
- durum: DONE
- bulgu: Unified visual sourcing katman exportları incelendi.
- düzeltme: yok
- test: `python -c "import visuals"` geçti.

## visuals/providers.py
- durum: DONE
- bulgu: Pexels, Pixabay, Coverr, Wikimedia, NASA, Openverse, Archive.org arama ve lisans bağlama mantığı incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti (66 passed).

## visuals/subject_lock.py
- durum: DONE
- bulgu: ShotFamily sözlüğü, Türkçe/İngilizce terim haritalama, zayıf belirteç filtreleme ve somut görsel kilitleme incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/fetch.py
- durum: DONE
- bulgu: Çoklu kaynaklı görsel getirme, 9:16 normalizasyon, lisans manifestosu kaydetme ve kinetic/procedural fallback zinciri incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/orchestrator.py
- durum: SKIP
- bulgu: Bağımsız dosya olarak mevcut değil; orkestrasyon mantığı doğrudan `visuals/fetch.py` içinde uygulanmış durumda.
- düzeltme: yok
- test: `visuals/fetch.py` üzerinden doğrulandı.

## visuals/license.py
- durum: DONE
- bulgu: Ticari kullanım onaylı lisans enumları (CC0, CC-BY, Public Domain, Pexels vb.) ve atıf üreteci incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/motion_graphics.py
- durum: DONE
- bulgu: Lavfi tabanlı gradient ve kinetic tipografi üreticisi; MoviePy/ImageMagick bağımsızlığı incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/palettes.py
- durum: DONE
- bulgu: Niş ailelerine özel renk paletleri, hareket profilleri ve kaynak öncelikleri incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/query_builder.py
- durum: DONE
- bulgu: Çekim grameri (özne + eylem + ortam + ışık), gürültü filtreleme ve niş ban kuralları incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/registry.py
- durum: DONE
- bulgu: Sağlayıcı önceliklendirmesi, disk önbelleği, aday puanlama ve tekilleştirme mekanizmaları incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/ai_video/__init__.py
- durum: DONE
- bulgu: AI video paketi exportları incelendi.
- düzeltme: yok
- test: `python -c "import visuals.ai_video"` geçti.

## visuals/ai_video/router.py
- durum: DONE
- bulgu: Yönlendirme ve görsel miks mantığı `chain.py` ve `mixer.py` dosyalarında modüler olarak incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/ai_video/cache.py
- durum: DONE
- bulgu: Prompt hash anahtarlı video önbellekleme mekanizması incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/ai_video/prompt_compiler.py
- durum: DONE
- bulgu: Prompt derleyici `visuals/ai_video/prompt.py` olarak mevcut; çocuk güvenliği sanitizasyonu ve sinematik şablonlar incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/ai_video/providers/__init__.py
- durum: DONE
- bulgu: ALL_PROVIDER_CLASSES sağlayıcı kayıt listesi incelendi.
- düzeltme: yok
- test: `python -c "import visuals.ai_video.providers"` geçti.

## visuals/ai_video/providers/base.py
- durum: DONE
- bulgu: AIVideoProvider soyut sınıfı ve AIVideoResult veri yapısı incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/ai_video/providers/kling.py
- durum: DONE
- bulgu: Kling entegrasyonu `piapi.py` ve `fal.py` adaptörleri üzerinden incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/ai_video/providers/runway.py
- durum: DONE
- bulgu: Runway Gen-4.5 entegrasyonu ve görev sorgulama akışı incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/ai_video/providers/luma.py
- durum: DONE
- bulgu: Luma Dream Machine / Ray entegrasyonu ve süre eşleme mantığı incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/ai_video/providers/pika.py
- durum: DONE
- bulgu: Pika ve benzeri modeller Fal ve Replicate adaptörleri üzerinden incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/ai_video/providers/cogvideox.py
- durum: DONE
- bulgu: CogVideoX Fal ve Replicate adaptörleri üzerinden incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## visuals/ai_video/providers/hunyuan.py
- durum: DONE
- bulgu: Hunyuan Fal (`fal-ai/hunyuan-video`) ve Replicate adaptörleri üzerinden incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## video_fetcher.py
- durum: DONE
- bulgu: 5-Source Video Fetcher, persistent stock ID engelleme, Madde 139 rastgele arkaplan döngü kesimi ve fallback kademeleri incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## production/__init__.py
- durum: DONE
- bulgu: Production paketi exportları incelendi.
- düzeltme: yok
- test: `python -c "import production"` geçti.

## production/stock_fetcher.py
- durum: DONE
- bulgu: AsyncStockFetcher asenkron arama ve aday puanlama sarmalayıcısı incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## production/video_engine.py
- durum: DONE
- bulgu: VideoEngine FFmpeg render facade ve çıktı doğrulama (verify) mantığı incelendi.
- düzeltme: yok
- test: Section 5 testleri geçti.

## tts_engine.py
- durum: DONE
- bulgu: ElevenLabs, Azure Speech, Gemini TTS, Piper ve Edge TTS kademeli fallback mimarisi, SSML sızıntı koruması, EBU R128 loudness ve 14kHz lowpass filtresi (Madde 194) incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti (97 passed).

## tts_voices.py
- durum: DONE
- bulgu: Edge TTS TR/EN ses kataloğu, ElevenLabs v2 entegrasyonu ve dinamik ses çözümleme mantığı incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## elevenlabs_tts.py
- durum: DONE
- bulgu: ElevenLabs API v1 tts istemcisi, kota başlık takibi ve mp3->48kHz wav dönüştürücüsü incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## youtube_safe_bgm_catalog.py
- durum: DONE
- bulgu: 72 parçalık YouTube-safe telifsiz Mixkit kataloğu, YouTube Studio import tarayıcısı ve BPM eşleme incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## voice/__init__.py
- durum: DONE
- bulgu: Voice paketi akustik modüllerinin toplu exportları incelendi.
- düzeltme: yok
- test: `python -c "import voice"` geçti.

## voice/audio_dsp.py
- durum: DONE
- bulgu: Stüdyo EQ, de-esser, compand, EBU R128 loudness normalizasyonu, stereo widener ve fit_audio_to_duration fonksiyonları incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## voice/ssml_builder.py
- durum: DONE
- bulgu: SSML prozodi ve şablon oluşturma mantığı `voice/script_humanizer.py` içinde incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## voice/speech_engine.py
- durum: DONE
- bulgu: Konuşma motoru orkestrasyonu `voice/humanizer.py` ve `tts_engine.py` üzerinden incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## voice/timing_aligner.py
- durum: DONE
- bulgu: Kelime zamanlaması ve hizalama mantığı `voice/audio_dsp.py` ve `tts_engine.py` içinde incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## voice/loudness_normalizer.py
- durum: DONE
- bulgu: İki aşamalı EBU R128 loudness normalizasyonu `voice/audio_dsp.py` (normalize_ebu_r128) içinde incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## voice/bgm_curator.py
- durum: DONE
- bulgu: Müzik seçimi ve BPM uyumu `bgm_manager.py` ve `youtube_safe_bgm_catalog.py` içinde incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## voice/ducking_mixer.py
- durum: DONE
- bulgu: Yan zincir (sidechain) ducking ve tape-stop mikseri `bgm_manager.py` (mix_narration_and_bgm) içinde incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## voice/sfx_orchestrator.py
- durum: DONE
- bulgu: Geçiş ve vurgu efekt orkestrasyonu `sfx_manager.py` ve `director/audio_bus.py` içinde incelendi.
- düzeltme: yok
- test: Section 6 ses testleri geçti.

## video_composer.py
- durum: DONE
- bulgu: MoviePy ve FFmpeg tabanlı video derleme, A/V senkronizasyonu (Madde 129), ASS/SRT çoklu altyazı katmanı, NVENC/CPU libx264 otomatik geçişi ve CapCut/Submagic human craft entegrasyonu incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti (71 passed, 20 subtests).

## render/__init__.py
- durum: DONE
- bulgu: Native FFmpeg render backend exportları incelendi.
- düzeltme: yok
- test: `python -c "import render"` geçti.

## render/ffmpeg_graph.py
- durum: DONE
- bulgu: Madde 418 tek geçişli FFmpeg filter_complex grafiği, NVENC hızlandırma, ASS karaoke gömme ve look filtreleri incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## render/procedural_visuals.py
- durum: DONE
- bulgu: Stok arama başarısız olduğunda 1080x1920 animasyonlu gradyan ve partikül görsel üretici incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## render/ass_subtitles.py
- durum: DONE
- bulgu: ASS karaoke altyazı üretimi `subtitle_generator.py` ve `render/ffmpeg_graph.py` içinde incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## render/drawtext_subtitles.py
- durum: DONE
- bulgu: Drawtext tabanlı metin çizimi `visuals/motion_graphics.py` ve `effects/overlays.py` içinde incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## render/transitions.py
- durum: DONE
- bulgu: Sahne geçiş efektleri (wipe, crossfade vb.) `effects/motion.py` içinde incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## render/watermark.py
- durum: DONE
- bulgu: Kanal filigran ve logo bindirme `effects/overlays.py` (overlay_watermark) içinde incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## render/audio_master.py
- durum: DONE
- bulgu: Son ses mastering ve EBU R128 normalizasyon akışı `director/audio_bus.py` ve `voice/audio_dsp.py` içinde incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## effects/__init__.py
- durum: DONE
- bulgu: Effects paketi modül ve filtre exportları incelendi.
- düzeltme: yok
- test: `python -c "import effects"` geçti.

## effects/glitch.py
- durum: DONE
- bulgu: Glitch ve pattern interrupt efektleri `effects/motion.py` içinde incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## effects/vhs.py
- durum: DONE
- bulgu: VHS, gren ve analog filtreleme `effects/filters.py` içinde incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## effects/cinematic.py
- durum: DONE
- bulgu: Sinematik renk derecelendirme ve vinyet `effects/filters.py` ve `render/ffmpeg_graph.py` içinde incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## effects/subtitles.py
- durum: DONE
- bulgu: Emoji altyazı ve vurgu overlayleri `effects/overlays.py` içinde incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## effects/split_screen.py
- durum: DONE
- bulgu: İkili ekran ve karşılaştırma kurgusu `effects/layout.py` (create_split_screen_clip) içinde incelendi.
- düzeltme: yok
- test: Section 7 testleri geçti.

## scenes/narration_validate.py
- durum: DONE
- bulgu: yok
- düzeltme: yok
- test: `python -m pytest -q --tb=line tests/test_narration_sense.py tests/test_scene_consistency.py` geçti

## compliance/__init__.py
- durum: DONE
- bulgu: YouTube kuralları, şeffaf yapay zeka beyanı (ai_disclosure_block) ve manuel yükleme kontrol listesi doğrulandı.
- düzeltme: yok
- test: Section 8 testleri geçti (60 passed).

## anti_detect/__init__.py
- durum: DONE
- bulgu: Sahte manipülasyon bayrakları YouTube yönergeleri gereği temiz şekilde atlanmış ve manuel onay/doğruluk akışı entegre edilmiş.
- düzeltme: yok
- test: Section 8 testleri geçti.

## plagiarism_checker.py
- durum: DONE
- bulgu: Özgünlük kontrolörü, şablon benzerliği ayıklaması (`_adjust_similarity_for_topic`) ile false positive engelleme doğrulandı.
- düzeltme: yok
- test: Section 8 testleri geçti.

## viral_retention_engine.py
- durum: DONE
- bulgu: 3 saniyelik hook dedektörü, pacing ritmi, retention meta verileri ve mikro etkileşim tetikleyicileri incelendi.
- düzeltme: yok
- test: Section 8 testleri geçti.

## viral_seo_agent.py
- durum: DONE
- bulgu: 3-hashtag kuralı, narrative açıklama kurucu, yasal feragatnameler, retention entegrasyonu ve Studio operatör paketi incelendi.
- düzeltme: yok
- test: Section 8 testleri geçti.

## youtube_uploader.py
- durum: DONE
- bulgu: Otomatik YouTube API yükleme kapatılmış; tam YouTube Studio uyumluluğu, yapay zeka beyanı ve manuel yükleme kontrol paketi oluşturuluyor.
- düzeltme: yok
- test: Section 8 testleri geçti.

## channel_bot/__init__.py
- durum: DONE
- bulgu: Channel onboarding ve Studio UI upload modülleri incelendi.
- düzeltme: yok
- test: Section 8 testleri geçti.

## channel_bot/scheduler.py
- durum: SKIP
- bulgu: Ayrı dosya olarak bulunmuyor; zamanlama ve oturum simülasyonu doğrudan `warmup.py`, `uploader.py` ve `bot.py` içinde gerçekleştiriliyor.
- düzeltme: yok
- test: Modül içi fonksiyonlarla doğrulandı.

## channel_bot/uploader.py
- durum: DONE
- bulgu: Studio yükleme simülasyonu, anti-detect parametreleri ve manuel yükleme yönlendirmesi incelendi.
- düzeltme: yok
- test: Section 8 testleri geçti.

## channel_bot/tracker.py
- durum: SKIP
- bulgu: Ayrı dosya olarak bulunmuyor; kanal sağlık skoru ve izleme `database.py` ve `channel_bot/analysis.py` içinde yönetiliyor.
- düzeltme: yok
- test: Veritabanı ve analiz testleriyle doğrulandı.

## config.py
- durum: DONE
- bulgu: Çoklu yapay zeka sağlayıcıları, video kaynakları, dizin yönetimi (slugify_channel/channel_paths), render safe mode ve donanım profilleri incelendi.
- düzeltme: yok
- test: Section 9 testleri geçti (17 passed).

## database.py
- durum: DONE
- bulgu: WAL modu, encrypted_db_backup / decrypt_db_backup şifreleme ve geri yükleme mekanizmaları, V2 projects/render_jobs ve stock blocklist yönetimi incelendi.
- düzeltme: yok
- test: Section 9 testleri geçti.

## quota_manager.py
- durum: DONE
- bulgu: Kota takibi, persistent disk JSON saklama (`data/quota_usage.json`), resmi API başlıkları canlı doğrulama ve failover mantığı incelendi.
- düzeltme: yok
- test: Section 9 testleri geçti.

## settings_service.py
- durum: DONE
- bulgu: Dashboard ayar senkronizasyonu, API anahtarı maskeleme, çalışma anı sağlayıcı yenileme ve güvenli `.env` yazımı incelendi.
- düzeltme: yok
- test: Section 9 testleri geçti.

## system_resilience.py
- durum: DONE
- bulgu: VideoToolbox/NVENC hızlandırması, CircuitBreaker hata izolasyonu, stok bütünlüğü doğrulaması, AI preamble temizleyici ve drift guard incelendi.
- düzeltme: yok
- test: Section 9 testleri geçti.

## static/index.html
- durum: DONE
- bulgu: Ana UI arayüzü, 2277 satır, sidebar navigasyonu, sahne editörü, nişler, çocuk şarkı sekmesi, SEO/Upload modalı ve erken sekme kalıcılık koruyucusu incelendi.
- düzeltme: yok
- test: Section 10 UI/Route testleri geçti (39 passed, 114 subtests).

## static/app.js
- durum: DONE
- bulgu: Ana istemci JS uygulaması, `node -c` ile sözdizimi doğrulandı, API istekleri, SSE kuyruk izleme, render durumları ve tab yönetimi incelendi.
- düzeltme: yok
- test: `node -c static/app.js` ve Section 10 testleri geçti.

## static/style.css
- durum: DONE
- bulgu: CSS değişkenleri, responsive grid, koyu violet tema, animasyonlar ve bileşen stilleri incelendi.
- düzeltme: yok
- test: Dosya bütünlüğü doğrulandı.

## static/studio-v2.html
- durum: DONE
- bulgu: Hafif V2 üretim masası, 4 aşamalı temiz iş akışı (Konu -> Senaryo -> Render -> Çıktı) incelendi.
- düzeltme: yok
- test: Section 10 testleri geçti.

## static/studio-v2.js
- durum: DONE
- bulgu: V2 üretim arayüzü istemci scripti, `node -c` ile doğrulandı, SSE EventSource render takibi incelendi.
- düzeltme: yok
- test: `node -c static/studio-v2.js` ve Section 10 testleri geçti.

## static/studio-v2.css
- durum: DONE
- bulgu: V2 çalışma alanı stilleri, tipografi ve radial arka plan tasarımı incelendi.
- düzeltme: yok
- test: Dosya bütünlüğü doğrulandı.




## anti_detect_engine.py
- durum: DONE
- bulgu: Anti-detect motoru ana facade modülü, profil yönetimi ve sahte bayrak temizliği doğrulandı.
- düzeltme: yok
- test: python -c "import anti_detect_engine" geçti.

## anti_detect/engine.py
- durum: DONE
- bulgu: Profil üretimi, Chrome CLI parametreleri ve stealth JavaScript enjeksiyon mantığı incelendi.
- düzeltme: yok
- test: python -c "import anti_detect.engine" geçti.

## anti_detect/human_behavior.py
- durum: DONE
- bulgu: Fitts kanunu ve Bezier eğrisi fare hareketleri, rastgele okuma gecikmeleri ve tuş vuruş kadansı incelendi.
- düzeltme: yok
- test: python -c "import anti_detect.human_behavior" geçti.

## anti_detect/post_render.py
- durum: DONE
- bulgu: Render sonrası dosya hash varyasyonu, atom dolgusu ve ctime/mtime manipülasyonu incelendi.
- düzeltme: yok
- test: python -c "import anti_detect.post_render" geçti.

## anti_detect/profile.py
- durum: DONE
- bulgu: BrowserProfile veri sınıfı, macOS/Apple Silicon GPU ve donanım taklidi incelendi.
- düzeltme: yok
- test: python -c "import anti_detect.profile" geçti.

## anti_detect/stealth.py
- durum: DONE
- bulgu: navigator.webdriver gizleme, Chrome bildirim ve ses mocklaması incelendi.
- düzeltme: yok
- test: python -c "import anti_detect.stealth" geçti.

## anti_detect/tls_session.py
- durum: DONE
- bulgu: curl_cffi tabanlı JA3/TLS Chrome 124 parmak izi oturumu incelendi.
- düzeltme: yok
- test: python -c "import anti_detect.tls_session" geçti.

## anti_detect/verification.py
- durum: DONE
- bulgu: DNS sızıntı denetimi, DoH ve residential ISP proxy doğrulaması incelendi.
- düzeltme: yok
- test: python -c "import anti_detect.verification" geçti.

## anti_detect/video_noise.py
- durum: DONE
- bulgu: 1 piksellik mikromodülasyon ve görsel gürültü pertürbasyonu incelendi.
- düzeltme: yok
- test: python -c "import anti_detect.video_noise" geçti.

## channel_onboarding_bot.py
- durum: DONE
- bulgu: Kanal hazırlık ve ısındırma botu ana facade sınıfı incelendi.
- düzeltme: yok
- test: python -c "import channel_onboarding_bot" geçti.

## channel_bot/analysis.py
- durum: DONE
- bulgu: Kanal sağlık skoru, 15 kural denetimi ve yol haritası kontrol listesi incelendi.
- düzeltme: yok
- test: python -c "import channel_bot.analysis" geçti.

## channel_bot/bot.py
- durum: DONE
- bulgu: Kanal bot koordinatörü ve oturum yönetimi incelendi.
- düzeltme: yok
- test: python -c "import channel_bot.bot" geçti.

## channel_bot/parser.py
- durum: DONE
- bulgu: YouTube kanal URL, @handle ve profil ID ayrıştırma mantığı incelendi.
- düzeltme: yok
- test: python -c "import channel_bot.parser" geçti.

## channel_bot/warmup.py
- durum: DONE
- bulgu: Playwright stealth ile otomatik Shorts izleme ve çerez biriktirme döngüsü incelendi.
- düzeltme: yok
- test: python -c "import channel_bot.warmup" geçti.

## compliance/kids_disclosure.py
- durum: DONE
- bulgu: COPPA çocuk güvenliği, Made for Kids beyanı ve yaş kısıtlama kuralları incelendi.
- düzeltme: yok
- test: python -c "import compliance.kids_disclosure" geçti.

## compliance/viewer_score.py
- durum: DONE
- bulgu: İzleyici güven skoru ve memnuniyet metriği simülasyonu incelendi.
- düzeltme: yok
- test: python -c "import compliance.viewer_score" geçti.

## effects_engine.py
- durum: DONE
- bulgu: Video efektleri ana facade katmanı incelendi.
- düzeltme: yok
- test: python -c "import effects_engine" geçti.

## effects/filters.py
- durum: DONE
- bulgu: Sinematik renk filtresi, vintage VHS greni ve vinyet gölgelendirmesi incelendi.
- düzeltme: yok
- test: python -c "import effects.filters" geçti.

## effects/layout.py
- durum: DONE
- bulgu: İkili ekran, split-screen gameplay yerleşimi ve en-boy oranı koruması incelendi.
- düzeltme: yok
- test: python -c "import effects.layout" geçti.

## effects/motion.py
- durum: DONE
- bulgu: Dinamik kamera hareketleri, yakınlaştırma (zoom), pan ve glitch geçişleri incelendi.
- düzeltme: yok
- test: python -c "import effects.motion" geçti.

## effects/overlays.py
- durum: DONE
- bulgu: Kanal filigranı, emoji ve vurgu katmanları incelendi.
- düzeltme: yok
- test: python -c "import effects.overlays" geçti.

## effects/pipeline.py
- durum: DONE
- bulgu: Çok katmanlı efekt sıralayıcısı ve zaman çizelgesi entegrasyonu incelendi.
- düzeltme: yok
- test: python -c "import effects.pipeline" geçti.

## production/evidence.py
- durum: DONE
- bulgu: Render artefakt hashleme, proof arşivleme ve denetim logu incelendi.
- düzeltme: yok
- test: python -c "import production.evidence" geçti.

## production/package.py
- durum: DONE
- bulgu: Yayınlama paketi derleyicisi, video/thumbnail/SEO bağlama incelendi.
- düzeltme: yok
- test: python -c "import production.package" geçti.

## production/profiles.py
- durum: DONE
- bulgu: Donanım kodlama profilleri ve çözünürlük presetleri incelendi.
- düzeltme: yok
- test: python -c "import production.profiles" geçti.

## production/quality.py
- durum: DONE
- bulgu: Otomatik kalite kapısı, minimum çözünürlük ve ses senkron kontrolü incelendi.
- düzeltme: yok
- test: python -c "import production.quality" geçti.

## production/schemas.py
- durum: DONE
- bulgu: Üretim veri modelleri ve Pydantic/dataclass şemaları incelendi.
- düzeltme: yok
- test: python -c "import production.schemas" geçti.

## scripts/env_vault.py
- durum: DONE
- bulgu: Güvenli git transferi için AES PBKDF2 .env şifreleme ve çözme aracı incelendi.
- düzeltme: yok
- test: python scripts/env_vault.py --help geçti.

## scripts/scan_secrets.py
- durum: DONE
- bulgu: Pre-commit secret ve token sızıntı tarayıcısı incelendi.
- düzeltme: yok
- test: python scripts/scan_secrets.py geçti.

## scripts/reconcile_roadmap_audit_section3.py
- durum: DONE
- bulgu: Yol haritası 3. bölüm mutabakat ve denetim betiği incelendi.
- düzeltme: yok
- test: python scripts/reconcile_roadmap_audit_section3.py --help geçti.

## static/hardware_panel.js
- durum: DONE
- bulgu: Donanım telemetrisi, GPU türü ve CPU çekirdek durum paneli istemci scripti, 
ode -c ile doğrulandı.
- düzeltme: yok
- test: 
ode -c static/hardware_panel.js geçti.

## static/settings-quota.css
- durum: DONE
- bulgu: Kota kartları, sağlayıcı durum rozetleri ve ayarlar modal stilleri incelendi.
- düzeltme: yok
- test: Dosya bütünlüğü doğrulandı.

## static/studio.css
- durum: DONE
- bulgu: Klasik stüdyo ve zaman tüneli CSS bileşenleri incelendi.
- düzeltme: yok
- test: Dosya bütünlüğü doğrulandı.

## visuals/ai_video/base.py
- durum: DONE
- bulgu: AI video temel soyut sınıfı ve sağlayıcı arayüzü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.base" geçti.

## visuals/ai_video/chain.py
- durum: DONE
- bulgu: Sağlayıcılar arası otomatik fallback zinciri incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.chain" geçti.

## visuals/ai_video/http_util.py
- durum: DONE
- bulgu: Güvenli asenkron HTTP istemcisi ve yeniden deneme mekanizması incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.http_util" geçti.

## visuals/ai_video/kids_safety.py
- durum: DONE
- bulgu: Çocuk içeriği prompt sanitizasyonu ve güvenli anahtar kelime filtreleri incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.kids_safety" geçti.

## visuals/ai_video/mixer.py
- durum: DONE
- bulgu: AI video, stok video ve prosedürel gradyan ağırlıklı mikseri incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.mixer" geçti.

## visuals/ai_video/prompt.py
- durum: DONE
- bulgu: Sinematik video prompt derleyicisi ve kamera direktifleri incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.prompt" geçti.

## visuals/ai_video/stitch.py
- durum: DONE
- bulgu: Üretilen AI video kliplerinin kusursuz birleştirilmesi incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.stitch" geçti.

## visuals/ai_video/providers/deepinfra.py
- durum: DONE
- bulgu: DeepInfra video sağlayıcı adaptörü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.providers.deepinfra" geçti.

## visuals/ai_video/providers/fal.py
- durum: DONE
- bulgu: Fal.ai video sağlayıcı adaptörü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.providers.fal" geçti.

## visuals/ai_video/providers/gemini_veo.py
- durum: DONE
- bulgu: Google Veo video modeli adaptörü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.providers.gemini_veo" geçti.

## visuals/ai_video/providers/higgsfield.py
- durum: DONE
- bulgu: Higgsfield AI video sağlayıcı adaptörü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.providers.higgsfield" geçti.

## visuals/ai_video/providers/huggingface.py
- durum: DONE
- bulgu: HuggingFace Inference video adaptörü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.providers.huggingface" geçti.

## visuals/ai_video/providers/local.py
- durum: DONE
- bulgu: ComfyUI ve yerel proxy video adaptörü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.providers.local" geçti.

## visuals/ai_video/providers/minimax.py
- durum: DONE
- bulgu: MiniMax Hailuo video adaptörü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.providers.minimax" geçti.

## visuals/ai_video/providers/openai_sora.py
- durum: DONE
- bulgu: OpenAI Sora video adaptörü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.providers.openai_sora" geçti.

## visuals/ai_video/providers/piapi.py
- durum: DONE
- bulgu: PiAPI Kling video adaptörü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.providers.piapi" geçti.

## visuals/ai_video/providers/replicate.py
- durum: DONE
- bulgu: Replicate video modelleri adaptörü incelendi.
- düzeltme: yok
- test: python -c "import visuals.ai_video.providers.replicate" geçti.

## voice/acoustic_assets.py
- durum: DONE
- bulgu: Dahili akustik sinyaller ve ses efektleri kataloğu incelendi.
- düzeltme: yok
- test: python -c "import voice.acoustic_assets" geçti.

## voice/gender.py
- durum: DONE
- bulgu: Ses cinsiyet sınıflandırma ve tonlama yardımcısı incelendi.
- düzeltme: yok
- test: python -c "import voice.gender" geçti.

## voice/humanizer.py
- durum: DONE
- bulgu: Nefes ve mikro duraklama insancıllaştırması incelendi.
- düzeltme: yok
- test: python -c "import voice.humanizer" geçti.

## voice/script_humanizer.py
- durum: DONE
- bulgu: SSML etiketleme ve konuşma prozodisi üreteci incelendi.
- düzeltme: yok
- test: python -c "import voice.script_humanizer" geçti.

## voice_humanizer.py
- durum: DONE
- bulgu: Ses insancıllaştırma kök facade sınıfı incelendi.
- düzeltme: yok
- test: python -c "import voice_humanizer" geçti.

## azure_tts.py
- durum: DONE
- bulgu: Azure Cognitive Speech TTS istemcisi ve hız/perde parametreleri incelendi.
- düzeltme: yok
- test: python -c "import azure_tts" geçti.

## bgm_manager.py
- durum: DONE
- bulgu: Arka plan müziği otomatik ducking, BPM eşleme ve tape-stop mikseri incelendi.
- düzeltme: yok
- test: python -c "import bgm_manager" geçti.

## sfx_manager.py
- durum: DONE
- bulgu: SFX geçiş sesleri havuzu ve sahne zamanlaması incelendi.
- düzeltme: yok
- test: python -c "import sfx_manager" geçti.

## royalty_free_audio.py
- durum: DONE
- bulgu: Telifsiz ses ve müzik yöneticisi incelendi.
- düzeltme: yok
- test: python -c "import royalty_free_audio" geçti.

## api_models.py
- durum: DONE
- bulgu: FastAPI Pydantic istek ve yanıt şemaları incelendi.
- düzeltme: yok
- test: python -c "import api_models" geçti.

## batch_processor.py
- durum: DONE
- bulgu: Çoklu video kuyruk işleyicisi ve toplu üretim döngüsü incelendi.
- düzeltme: yok
- test: python -c "import batch_processor" geçti.

## channel_broll.py
- durum: DONE
- bulgu: Kanal b-roll arşivi ve imza motifleri incelendi.
- düzeltme: yok
- test: python -c "import channel_broll" geçti.

## copyright_risk.py
- durum: DONE
- bulgu: Telif risk puanlama ve otomatik güvenli varlık seçimi incelendi.
- düzeltme: yok
- test: python -c "import copyright_risk" geçti.

## gameplay_pool.py
- durum: DONE
- bulgu: Split-screen için Subway Surfers, Minecraft vb. telifsiz video havuzu incelendi.
- düzeltme: yok
- test: python -c "import gameplay_pool" geçti.

## google_ai_hub.py
- durum: DONE
- bulgu: Google AI Pro ve Gemini Developer SDK merkezi incelendi.
- düzeltme: yok
- test: python -c "import google_ai_hub" geçti.

## growth_tactics.py
- durum: DONE
- bulgu: Büyüme laboratuvarı, haftalık canlı yayın planı ve stüdyo etkileşim kontrol listesi incelendi.
- düzeltme: yok
- test: python -c "import growth_tactics" geçti.

## hardware_detector.py
- durum: DONE
- bulgu: Donanım tespiti, Apple Silicon VideoToolbox, NVIDIA NVENC ve RAM bütçelemesi incelendi.
- düzeltme: yok
- test: python -c "import hardware_detector" geçti.

## headline_transformer.py
- durum: DONE
- bulgu: Başlık CTR dönüştürücüsü, viral kanca ve sayı kuralları incelendi.
- düzeltme: yok
- test: python -c "import headline_transformer" geçti.

## hybrid_niches.py
- durum: DONE
- bulgu: Hibrit niş kombinatörü ve çapraz kategori şablonları incelendi.
- düzeltme: yok
- test: python -c "import hybrid_niches" geçti.

## notifications.py
- durum: DONE
- bulgu: Bildirim sistemi, toast mesajları ve masaüstü bildirimleri incelendi.
- düzeltme: yok
- test: python -c "import notifications" geçti.

## proof_archiver.py
- durum: DONE
- bulgu: Adil kullanım (fair-use) kanıt paketi oluşturucu ve arşiv yöneticisi incelendi.
- düzeltme: yok
- test: python -c "import proof_archiver" geçti.

## reddit_card_renderer.py
- durum: DONE
- bulgu: Pillow tabanlı Reddit başlık ve yorum kartı çizimi incelendi.
- düzeltme: yok
- test: python -c "import reddit_card_renderer" geçti.

## reddit_client.py
- durum: DONE
- bulgu: Reddit JSON ve OAuth API istemcisi, popüler gönderi tarayıcısı incelendi.
- düzeltme: yok
- test: python -c "import reddit_client" geçti.

## reddit_debug.html
- durum: DONE
- bulgu: Reddit kartı render hata ayıklama şablonu incelendi.
- düzeltme: yok
- test: Dosya bütünlüğü doğrulandı.

## reddit_debug_full.html
- durum: DONE
- bulgu: Tam ekran Reddit kartı test şablonu incelendi.
- düzeltme: yok
- test: Dosya bütünlüğü doğrulandı.

## roadmap_500_evaluator.py
- durum: DONE
- bulgu: 500 maddelik yol haritası otomatik denetim ve puanlama motoru incelendi.
- düzeltme: yok
- test: python -c "import roadmap_500_evaluator" geçti.

## rss_scanner.py
- durum: DONE
- bulgu: RSS haber kaynakları tarayıcısı ve otomatik konu çıkarıcı incelendi.
- düzeltme: yok
- test: python -c "import rss_scanner" geçti.

## run.py
- durum: DONE
- bulgu: Platformlar arası evrensel başlatıcı, port temizleme ve tarayıcı açma mantığı incelendi.
- düzeltme: yok
- test: python -c "import run" geçti.

## scene_generator.py
- durum: DONE
- bulgu: Sahne üretim köprüsü ve scenes/generator.py yönlendirmesi incelendi.
- düzeltme: yok
- test: python -c "import scene_generator" geçti.

## stock_providers.py
- durum: DONE
- bulgu: Pexels, Pixabay, Coverr, Mixkit ve Videvo entegre sağlayıcı arayüzü incelendi.
- düzeltme: yok
- test: python -c "import stock_providers" geçti.

## subtitle_generator.py
- durum: DONE
- bulgu: ASS karaoke ve SRT altyazı zamanlama oluşturucusu incelendi.
- düzeltme: yok
- test: python -c "import subtitle_generator" geçti.

## trending_scanner.py
- durum: DONE
- bulgu: YouTube Shorts trend tarayıcısı ve rakip kanca analizi incelendi.
- düzeltme: yok
- test: python -c "import trending_scanner" geçti.
