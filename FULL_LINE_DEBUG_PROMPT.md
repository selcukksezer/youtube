# ShortsVideoCreators — satır satır hata ayıklama

Bu dosyanın tamamı ajan talimatıdır. Yeni sohbette ilk mesaj olarak yapıştır. Kod taraması bu dosyayı yazmak değildir. Tarama, bu talimat okununca başlar.

Amaç: üretim kodunu dosya dosya, satır satır oku. Bulunan hatayı, mantıksız kodu, kopuk bağlamı ve özellikler arası kopukluğu yerinde düzelt. Yarım kalan mevcut akışı tamamla. Yeni ürün özelliği uydurma.

## Rol

Bu depoda çalışan tek görevlisin. Kısa rapor yazıp durma. Her dosyayı bitir, düzelt, kanıtla, logla, sıradaki dosyaya geç.

Kullanıcı Türkçe yazar. Bulgu ve log Türkçe olsun. Kod, yol, fonksiyon adı, hata metni ve komut olduğu gibi kalsın.

## Durma koşulu

Yalnızca şu üçü birden doğruysa dur:

1. Aşağıdaki inceleme sırasındaki her dosya `DEBUG_RUN_LOG.md` içinde `DONE` veya `SKIP` satırı taşıyor.
2. Sıra bittikten sonra repoda adı listede olmayan her üretim `.py` / `static/*.{js,html,css}` dosyası da loglandı. `tests/` bu turda ürün kodu değildir; sözleşme kanıtıdır.
3. Logda `OPEN` madde yok.

Bunlar dışında durma. "Devam edeyim mi" sorma. Özet yazıp bekleme. Dosya bitince sıradakine geç.

Bağlam penceresi dolmak üzereyse: açık dosyanın log satırını yaz, son `DONE` dosyasını belirt, dur. Yeni turda bu dosyayı ve `DEBUG_RUN_LOG.md` oku. Son `DONE` kaydının hemen sonrasından devam et. Bitmiş dosyayı tekrar düzeltme. Yeni turda eski bulguyu sil baştan anlatma.

## Yasaklar

- Yeni ürün fikri, yeni ekran, yeni niş, yeni sağlayıcı ekleme.
- Çalışan mimariyi geniş refactor ile değiştirme.
- Commit, push, branch, `git config`, force, reset yok. Kullanıcı açıkça istemedikçe git komutu yok.
- Şunlara dokunma: `.env`, `credentials.json`, token, secret, `__pycache__`, `.npm-cache`, `.pytest_cache`, `assets/` medya, `output/` video ve ses, `audio/` üretilmiş dosya.
- Testi yeşile çekmek için ürün davranışını zayıflatma. Assertion silme. Beklenen değeri rastgele gevşetme.
- Sessiz `except`, sahte `return True`, boş `pass` ile hatayı gizleme.
- Aynı hatayı ikinci kez "düzelttim" diye loglama.

## Çalışma döngüsü

Her dosya için sırayı bozma:

1. `DEBUG_RUN_LOG.md` yoksa oluştur. Varsa son `DONE` dosyasından sonrasını seç.
2. Dosyayı baştan sona oku. Parça parça oku; satır atlama. Import, sabit, dal, döngü, dönüş, yan etki dahil.
3. Bu dosyayı çağıran ve bu dosyanın çağırdığı sembolleri repoda ara. İmza, alan adı, dönüş şekli, hata yolu uyuşsun.
4. Aşağıdaki satır kontrol listesini uygula. Şüpheyi tahminle kapatma. Çağrı yerini aç ve doğrula.
5. Düzeltme varsa en dar katmanda yap. Çevredeki doğru davranışı koru.
6. İlgili pytest çalıştır. Komut ve sonuç loga girer.
7. Log satırını yaz. Hemen sonraki dosyaya geç.

Dosyada bulgu yoksa da logla: `DONE`, bulgu `yok`. Atlamak yasak.

## Satır kontrol listesi

Her satırda şunlardan biri varsa düzelt:

### Hata

- Yanlış operatör, ters koşul, off-by-one, yanlış varsayılan, birim karışması (saniye / milisaniye, 0–1 / 0–100).
- `None` veya eksik anahtar sonrası patlayan erişim. API ve dosya yokluğu için gerçek hata yolu yok.
- Yarış, çift yazma, kota sayacını iki kez artırma veya hiç artırmama.
- Kaynak sızıntısı: açık dosya, subprocess, HTTP oturumu kapanmıyor.
- Yanlış kodlama, yol birleştirme (`/` ile Windows yolu), mutlak yolun makineye gömülü olması.

### Mantıksız kod

- Dal hiç çalışmıyor veya her zaman aynı kola giriyor.
- Aynı iş iki yerde, sonuçlar çelişiyor.
- Yorum ile kod ters. Yorumu koda uydur veya kodu yoruma uydur; hangisi çağıranların beklediği davranışsa o kazansın.
- Sihirli sayı, eşiği başka modüldeki eşikle çelişiyor.
- Başarı dönen fonksiyon işi yapmamış.

### Kopuk bağlam

- Üst fonksiyonun ürettiği alan alt fonksiyonun okuduğu adla aynı değil.
- `script.json`, `research_brief`, `director_plan`, `shot_plan`, `publishing_package` anahtarları üretici ve tüketici arasında kaymış.
- Dil, niş, süre bandı, çocuk içeriği bayrağı bir aşamada set edilip sonraki aşamada okunmuyor.
- Hata mesajı kullanıcıya başka hatanın metnini gösteriyor.

### Özellik dikişi

- UI aksiyonu olmayan endpoint çağırıyor veya endpoint hiçbir UI / CLI yoluna bağlı değil ve ölü kaldı.
- `server.py` rotası ile `v2_api` aynı işi farklı sözleşmeyle yapıyor.
- `kids_song_bridge.py` ana üretim yolunun zorunlu alanlarını atlıyor veya tersine ana yol kids akışını bozuyor.
- Stok çekme `quota_manager.py` dışından kota deliyor.
- Ayar `settings_service.py` / `config.py` içinden bir yolda okunuyor, kardeş yolda sabit kodlanmış.

### Geliştirilecek yer

Yalnızca mevcut akış kırık veya yarım ise geliştir:

- `TODO`, `FIXME`, `pass`, `NotImplementedError`, yutulan exception, "sonra bağlanacak" yorumu.
- Fonksiyon var, çağıran yok, çağıranın ihtiyacı o fonksiyonun işiyse bağla.
- Fallback sessizce yanlış varlık basıyor. Fallback kalsın; neden loglansın ve sözleşme bozulmasın.

Kapsam dışı: yeni niş, yeni model, yeni sekme, yeni metrik, "şunu da eklesek iyi olur".

## Zorunlu dikişler

Sıra bu dosyalara gelince dikişi ayrıca doğrula. Kopuksa düzelt:

1. `research_service.py` brief alanları → `scenes/` üretici → `script.json`.
2. `script.json` / sahne şeması → `director/schema.py`, `director/timeline.py`, `director/validate.py`, `director/compiler.py`.
3. `director_plan` / `shot_plan` alan adları → `video_composer.py`, `render/ffmpeg_graph.py`, `production/video_engine.py`.
4. `kids_song_bridge.py` + `routers/kids_song_router.py` ↔ ana `server.py` / `server_core/render_worker.py` yolu. Ortak sözleşme tek olsun.
5. `server.py` rotaları ↔ `v2_api/router.py` + `v2_api/schemas.py`. Aynı kaynak için iki şekil varsa çağıranı kıran tarafı öbürüne uydur.
6. Kota: `quota_manager.py` ↔ `video_fetcher.py` ↔ `production/stock_fetcher.py` ↔ `visuals/fetch.py`.
7. Ses: `tts_engine.py`, `tts_voices.py`, `elevenlabs_tts.py`, `voice/*` süre ve dosya adı `video_composer.py` beklentisiyle aynı.
8. Yükleme: `youtube_uploader.py` ↔ `channel_bot/uploader.py`. Başlık, açıklama, kids bayrağı, `compliance/` aynı paketten gelsin.
9. UI: `static/index.html` + `static/app.js` ve `static/studio-v2.html` + `static/studio-v2.js` aynı API yolunu ve gövde şeklini kullansın. Biri düğme gösterip diğeri 404 çağırıyorsa dikişi kapat.

## İnceleme sırası

Bu sıra bağımlılık sırasıdır. Dosyayı bitirmeden sonrakine geçme. `__init__.py` dahil. Dosya yoksa `SKIP` yaz, nedeni `dosya yok`.

### 1. Giriş

- `main.py`
- `server.py`
- `server_core/__init__.py`
- `server_core/state.py`
- `server_core/render_worker.py`
- `kids_song_bridge.py`

### 2. API

- `routers/__init__.py`
- `routers/config_router.py`
- `routers/research_router.py`
- `routers/video_router.py`
- `routers/media_router.py`
- `routers/system_router.py`
- `routers/google_ai_router.py`
- `routers/channel_router.py`
- `routers/kids_song_router.py`
- `v2_api/__init__.py`
- `v2_api/schemas.py`
- `v2_api/router.py`

### 3. Araştırma ve senaryo

- `research_service.py`
- `services/__init__.py`
- `services/topic_suggester.py`
- `services/niche_trend_signals.py`
- `services/dubbing.py`
- `niche_templates.py`
- `scenes/__init__.py`
- `scenes/prompts.py`
- `scenes/scripts.py`
- `scenes/generator.py`
- `scenes/fallback.py`
- `scenes/enrichment.py`
- `scenes/narration_sense.py`
- `scenes/narration_validate.py`
- `scenes/narration_coherence.py`
- `scenes/retention_hooks.py`
- `scenes/plan_linter.py`
- `craft/__init__.py`
- `craft/human_director.py`

### 4. Yönetmen

- `director/__init__.py`
- `director/schema.py`
- `director/visual_intent.py`
- `director/timeline.py`
- `director/validate.py`
- `director/compiler.py`
- `director/audio_bus.py`
- `director/quality_gate.py`

### 5. Görüntü ve üretim

- `visuals/__init__.py`
- `visuals/registry.py`
- `visuals/query_builder.py`
- `visuals/fetch.py`
- `visuals/providers.py`
- `visuals/license.py`
- `visuals/subject_lock.py`
- `visuals/palettes.py`
- `visuals/motion_graphics.py`
- `visuals/ai_video/__init__.py`
- `visuals/ai_video/base.py`
- `visuals/ai_video/http_util.py`
- `visuals/ai_video/cache.py`
- `visuals/ai_video/prompt.py`
- `visuals/ai_video/chain.py`
- `visuals/ai_video/mixer.py`
- `visuals/ai_video/stitch.py`
- `visuals/ai_video/kids_safety.py`
- `visuals/ai_video/providers/__init__.py`
- `visuals/ai_video/providers/local.py`
- `visuals/ai_video/providers/fal.py`
- `visuals/ai_video/providers/replicate.py`
- `visuals/ai_video/providers/runway.py`
- `visuals/ai_video/providers/luma.py`
- `visuals/ai_video/providers/minimax.py`
- `visuals/ai_video/providers/piapi.py`
- `visuals/ai_video/providers/higgsfield.py`
- `visuals/ai_video/providers/gemini_veo.py`
- `visuals/ai_video/providers/openai_sora.py`
- `visuals/ai_video/providers/huggingface.py`
- `visuals/ai_video/providers/deepinfra.py`
- `video_fetcher.py`
- `production/__init__.py`
- `production/schemas.py`
- `production/profiles.py`
- `production/evidence.py`
- `production/stock_fetcher.py`
- `production/quality.py`
- `production/package.py`
- `production/video_engine.py`

### 6. Ses

- `tts_engine.py`
- `tts_voices.py`
- `elevenlabs_tts.py`
- `youtube_safe_bgm_catalog.py`
- `voice/__init__.py`
- `voice/gender.py`
- `voice/humanizer.py`
- `voice/script_humanizer.py`
- `voice/audio_dsp.py`
- `voice/acoustic_assets.py`

### 7. Birleştirme

- `video_composer.py`
- `render/__init__.py`
- `render/ffmpeg_graph.py`
- `render/procedural_visuals.py`
- `effects/__init__.py`
- `effects/filters.py`
- `effects/overlays.py`
- `effects/layout.py`
- `effects/motion.py`
- `effects/pipeline.py`

### 8. Kalite ve yükleme

- `compliance/__init__.py`
- `compliance/kids_disclosure.py`
- `compliance/viewer_score.py`
- `anti_detect/__init__.py`
- `anti_detect/post_render.py`
- `plagiarism_checker.py`
- `viral_retention_engine.py`
- `viral_seo_agent.py`
- `youtube_uploader.py`
- `channel_bot/__init__.py`
- `channel_bot/parser.py`
- `channel_bot/analysis.py`
- `channel_bot/warmup.py`
- `channel_bot/uploader.py`
- `channel_bot/bot.py`

### 9. Durum

- `config.py`
- `database.py`
- `quota_manager.py`
- `settings_service.py`
- `system_resilience.py`

### 10. Arayüz

- `static/index.html`
- `static/app.js`
- `static/style.css`
- `static/studio-v2.html`
- `static/studio-v2.js`
- `static/studio-v2.css`

Her JS fonksiyonunda `fetch` / URL ile backend route gövdesini karşılaştır.

### 11. Listede olmayan üretim dosyaları

Sıra bitince şunu çalıştır ve listede olmayan her üretim dosyasını aynı döngüyle bitir:

```powershell
Get-ChildItem -Recurse -File -Include *.py,*.js,*.html,*.css |
  Where-Object { $_.FullName -notmatch '\\(tests|__pycache__|\.pytest_cache|\.npm-cache|assets|output|audio|node_modules)\\' }
```

### 12. Testler

Ürün dosyaları `DONE` olduktan sonra, bu turda değişen her modülün testini çalıştır. Test kırmızıysa önce ürün kodundaki gerçek hatayı düzelt. Test, kasıtlı olarak kırılan eski sözleşmeyi bekliyorsa ve yeni davranış doğruysa testi dürüstçe güncelle. Nedenini loga yaz.

Tüm ürün dosyaları bitince, süre elveriyorsa:

```powershell
python -m pytest -q --tb=line
```

Kırmızı testi sırayla kapat. Ürünü test geçsin diye bozma.

## Düzeltme kuralı

- En dar katman. Bir satır yetiyorsa fonksiyonu yeniden yazma.
- Komşu modülün doğru sözleşmesi kazansın. İkinci kopyayı birincinin alan adına uydur.
- Davranış değişince çağıran ve test birlikte güncellensin.
- Düzeltme üç dosyadan genişliyorsa dur, loga `OPEN` yaz, gerekçeyi bir cümle yaz, sıradaki dosyaya geç. Tur sonunda `OPEN` maddelere dön. Hâlâ üç dosyadan genişse `OPEN` kalsın; zorla mimari değiştirme.
- Secret ekleme, anahtar loglama, gerçek API çağrısı ile kota yakma yok. Test ağ çağırıyorsa mock veya mevcut testteki yerel yol.

## Kanıt

Düzeltme yapılan her dosyadan sonra en dar pytest:

```powershell
python -m pytest -q --tb=short tests/<ilgili_test.py>
```

İlgili test yoksa, değişen fonksiyonu içe aktaran mevcut bir testi seç. Hiç test yoksa dosyayı içe aktarmanın patlamadığını göster:

```powershell
python -c "import <modul>"
```

İçe aktarma yan etki ile ağ veya render başlatıyorsa bu komutu çalıştırma. Loga `test yok, import yan etkili` yaz.

Kırmızı kaldıysa düzeltmeyi geri al veya hatanın gerçek nedenini gider. Kırmızıyı `DONE` sayma. Log durumu `OPEN` olsun.

## Log

Kökte `DEBUG_RUN_LOG.md`. Her dosyadan sonra sona ekle. Eski satırı silme.

```markdown
## <yol>
- durum: DONE | OPEN | SKIP
- bulgu: yok | bir cümle
- düzeltme: yok | ne değişti, neden
- test: komut ve geçti/kaldı
```

`OPEN` satırında bir sonraki turun neyi kapatacağı tek cümle olsun.

Tur başında logun ilk satırından devam noktasını oku. Bitmiş `DONE` dosyasını yeniden inceleme.

## Devam protokolü

1. Bu dosyayı oku.
2. `DEBUG_RUN_LOG.md` varsa son `DONE` sonrasındaki ilk dosyadan başla.
3. Log yoksa `main.py` ile başla.
4. Döngüyü durma koşuluna kadar tekrarla.
5. Bitişte yalnız şunları yaz: `DONE` sayısı, `OPEN` sayısı, `SKIP` sayısı, hâlâ kırmızı olan test komutları.

## Bitiş cümlesi

Durma koşulu sağlanınca tek rapor:

```text
Bitti. DONE=<n> OPEN=<n> SKIP=<n>
Kırmızı: <yok | komutlar>
```

Bu rapordan önce durma. Bu rapordan sonra yeni iş açma.
