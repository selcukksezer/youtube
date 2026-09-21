# Gelecek Yol Haritası — YouTube Shorts Ultimate

> **Tarih:** 2026-09-21  
> **Bağlam:** 500 maddelik audit tamamlandı (`ROADMAP_AUDIT.md`). Bu belge bundan sonraki adımları önceliklendirir.  
> **Kaynak denetimler:** `ROADMAP_AUDIT.md`, `SCENARIO_WRITING_AUDIT.md`, `ROADMAP_AUDIT_SPRINT2_RECOVERY.md`

---

## 1. Tamamlanan (2026-09-21)

500 maddelik yol haritasının **413 in-scope** maddesi denetlendi; **388 Done (%93.9)**, **0 Partial**, **0 Missing**, **26 Deferred**, **87 Excluded**.

### Completion sprint özeti

| Sprint | Kazanım |
|--------|---------|
| Sprint 1 | FFmpeg→MoviePy default render yolu (+65 madde) |
| Batch 2 | Hybrid overlay + EQ/countdown/neon frame (+40) |
| Batch 3 | BGM/SFX wire, retention görsel, B5 niş, B7 infra (+73) |
| Batch 4 | B6 SEO operator pack, B8 kanal sağlığı checklist (+56) |
| Appeal close-out | #472/#475 operatör workflow Done (+2) |

### Senaryo yazma (A–H)

Yarım/boş senaryo sorunu için 8 batch uygulandı: `min_ratio=1.0` narration gate, UI stale plan purge (`planVersion: 2`), render worker gate, word budget repair, `plan_linter.py`, Gemini 429 circuit breaker, astrology fallback, integration testler.

### Diğer önemli teslimler

- **BGM:** 72 parçalı `youtube_safe_bgm_catalog.json` + `youtube_safe_bgm_catalog.py`
- **Overlay:** `effects/overlays.py` hybrid render routing; MoviePy default path
- **Dual voice (#143):** TTS çift seslendirme wire
- **UI:** Senaryo navigasyonu, yeniden üret butonu, kalite paneli
- **Infra:** `docker-compose.yml`, şifreli DB yedek (`database.encrypted_db_backup`)
- **Test:** 27+ section test dosyası, batch wiring testleri

---

## 2. Deferred — 26 Madde

Bilinçli erteleme: kod dışı operasyon, ücretli API veya Studio manuel adım gerektirir. Tamamı otomatik kod ile kapatılamaz.

### A. Hesap & anti-detect (manuel operasyon)

| # | Madde | Kilidi açan |
|---|-------|-------------|
| 16 | 2FA kurulumu | Gerçek Google hesabı + SMS/authenticator |
| 35 | YouTube Premium | Ücretli abonelik |
| 58 | Dokunmatik ekran ipuçları | Playwright prod upload + cihaz profili |
| 59 | Pil API yanıtı | Playwright prod upload + cihaz profili |
| 66 | Kanal yaşlandırma (48s/7g) | Operatör disiplini; plan var, enforce yok |
| 98 | Kendi 4K arka plan kütüphanesi | 50 adet manuel çekim + dosya yükleme |

### B. Studio büyüme taktikleri

| # | Madde | Kilidi açan |
|---|-------|-------------|
| 311–315 | Yorumdan video, anket, köprü link, seri format, canlı yayın | YouTube Studio manuel veya resmi API erişimi |
| 319–322 | Affiliate, niş çarpışması, Tier-1 adaptasyon, çapraz platform | İçerik stratejisi + Studio operasyonu |

### C. Ücretli / 3rd-party API

| # | Madde | Kilidi açan |
|---|-------|-------------|
| 113 | AI çizilmiş görseller (Runway/Kling) | FAL/Stability API key + pipeline |
| 324 | Karakter canlandırma (D-ID/SadTalker) | `AVATAR_ANIMATION_API_KEY` + provider seçimi |
| 371 | TubeBuddy/VidIQ arama skoru | Ücretli SEO araç entegrasyonu |

### D. SEO & platform sinyalleri

| # | Madde | Kilidi açan |
|---|-------|-------------|
| 384 | *(audit footer)* | Detay §3 tablosunda yeniden doğrulanmalı |
| 401 | Mobil bildirim tetikleyicisi | Studio abone/bildirim operasyonu |
| 402 | Kanal rozetleri ve seviyeler | Studio operasyonu |

### E. İtiraz & monetization (operatör)

| # | Madde | Kilidi açan |
|---|-------|-------------|
| 473 | İtiraz videosunda yüz gösterme | Operatör talk-head kaydı |
| 474 | Kurgu sürecini ekran kaydıyla kanıtlama | Operatör screen record |
| 476 | Tekrarlanan içerik ret sonrası strateji | 30 gün özgün içerik planı (operasyonel) |
| 479 | Sponsorluk formatı | ~100K abone eşiği |
| 480 | Kanal satış piyasası değerlemesi | Operasyonel bilgi / danışmanlık |

**Not:** §3 madde tabloları kısmen eski formatta; item-level Deferred etiketleri footer özetine göre authoritative. Tablo restore edilmeden yeni madde sayımı yapmayın.

---

## 3. Excluded — 87 Upload Maddesi

Otomatik YouTube Studio upload, OAuth upload, günlük upload limiti, metadata upload, Playwright prod screenshot vb. **kod denetimi dışı** bırakıldı.

**Operasyonel gerçek:** Video üretimi pipeline'da; yükleme **manuel YouTube Studio** akışı ile yapılır. Simülasyon kanıtı var (`execute_studio_upload` + testler) ama prod Playwright upload bilinçli olarak scope dışı.

Excluded maddeleri Done saymak için prod upload otomasyonu gerekir — maliyet, ToS riski ve hesap güvenliği nedeniyle önerilmez.

---

## 4. Operasyonel Yapılacaklar

| Görev | Neden | Adım |
|-------|-------|------|
| **Vault unseal** | API key'ler `.env.vault` içinde | `python scripts/env_vault.py unseal` → `.env` oluştur |
| **GEMINI_MODEL doğrula** | Senaryo kalitesi + quota | `.env` içinde `GEMINI_MODEL=gemini-flash-lite-latest` (veya güncel free-tier model) |
| **1080p default** | Shorts kalite | `RENDER_RESOLUTION_MODE=1080p` (`.env.example`'da varsayılan) |
| **İlk prod render smoke** | Sprint değişikliklerini doğrula | 1 konu → senaryo → render → dosya boyutu/süre kontrol |
| **BGM dosyaları** | Katalog 72 track; MP3 cache boş olabilir | İlk render'da `AUTO_FETCH_ROYALTY_FREE_BGM=true` ile indirme veya Studio import |
| **Commit + CI** | Büyük diff tek commit'te; regresyon riski | GitHub Actions: `python -m unittest discover -s tests -p 'test_*.py'` |
| **quota_usage.json** | Runtime veri; repo'ya commit edilmemeli | `.gitignore`'a ekle veya local-only tut |

---

## 5. Ürün Öncelikleri (Önerilen Sıra)

Effort: **S** = 1–2 gün, **M** = 3–5 gün, **L** = 1–2 hafta

| # | Özellik | Effort | Gerekçe |
|---|---------|--------|---------|
| 1 | **GitHub Actions CI** | S | 60+ yeni test dosyası; merge/regresyon koruması yok |
| 2 | **§3 ROADMAP tablo restore** | M | Item-level durumlar eski; audit güvenilirliği düşük |
| 3 | **Senaryo kalite izleme dashboard** | M | `validation.issues` + plan linter metriklerini UI'da göster |
| 4 | **Niş bazlı procedural fallback genişletme** | M | Crypto dışı nişlerde AI fail → zayıf plan riski |
| 5 | **Word budget iyileştirme (96 cap)** | S | Generic filler yerine sahne-özel tamamlama |
| 6 | **DeepL çeviri (#454)** | M | Çoklu dil Shorts; API key gerekir |
| 7 | **WebRTC/STUN tam maskeleme (#32–33)** | M | Anti-detect Partial kalan maddeler |
| 8 | **Avatar pipeline (#324)** | L | D-ID key + render entegrasyonu; opsiyonel premium |
| 9 | **Frontend localStorage testleri** | S | Batch B regresyon kilidi (Playwright veya jsdom) |
| 10 | **Prod deploy dokümantasyonu** | S | Docker var; runbook eksik |

---

## 6. Senaryo Kalite — Sürekli İzleme

Audit sonrası A–H batch'leri uygulandı. Kalan riskler:

| Risk | Belirti | Önlem |
|------|---------|-------|
| AI 6-kelime stub | Schema geçer, içerik zayıf | Minimum kelime/sahne linter (opsiyonel) |
| Mood tekrarı | 14 sahnede aynı mood | `plan_linter.py` zayıf planlarda regen; eşik sıkılaştırılabilir |
| Enrichment şişirme | Kelime sayısı artar, condense keser | Batch E word budget; Director cap gözden geçir |
| Stale localStorage | Eski plan UI'da | `planVersion: 2` purge aktif; kullanıcıya "Yeniden Üret" hatırlat |
| Gemini quota | 429 → procedural | Circuit breaker aktif; quota paneli izle |

**Önerilen rutin:** Haftalık 3 konu (crypto, astroloji, genel) ile `/api/script/generate` + render smoke; `SCENARIO_WRITING_AUDIT.md` test listesini çalıştır.

**Opsiyonel AI iyileştirmeler (düşük öncelik):**
- Prompt A/B rotasyonu metrikleri
- `min_words_per_scene` schema gate
- Enrichment suffix çeşitliliği artırma

---

## 7. Teknik Borç

| Borç | Durum | Aksiyon |
|------|-------|---------|
| **§3 ROADMAP tablo restore** | Footer authoritative; §3 satırları eski Partial/Deferred karışık | Sprint sonrası item-level grep + tablo yeniden yaz |
| **Git commit cadence** | Tek mega-commit (2026-09-21) | Bundan sonra feature-batch commit'leri; CI ile koruma |
| **scipy optional dep** | `video_composer.py` lazy import; `requirements.txt`'te yok | `scipy` optional extra ekle veya pure-numpy fallback |
| **roadmap_500_evaluator.py** | 500/500 parse; impl doğrulamaz | Audit dokümanına güven; evaluator sadece smoke |
| **quota_usage.json tracked** | Runtime quota verisi diff'te | `.gitignore`'a al |
| **Playwright upload sim vs prod** | Sim Done; prod Excluded | Dokümante et; prod istenirse ayrı RFC |

---

## 8. Başarı Kriterleri (Sonraki Milestone)

- [ ] CI yeşil: tüm `tests/test_*.py` unittest discover
- [ ] 1 gerçek konu end-to-end: senaryo → 1080p render → BGM mix
- [ ] §3 tablo restore: Deferred 26 ile footer uyumlu
- [ ] Operatör: vault unseal + GEMINI_MODEL doğrulandı
- [ ] Senaryo: 14/14 usable narration 3 farklı nişte

---

*Son güncelleme: 2026-09-21 — audit completion + scenario writing sprint sonrası.*
