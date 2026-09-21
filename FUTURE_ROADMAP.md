# Gelecek Yol Haritası — YouTube Shorts Ultimate

> **Tarih:** 2026-09-21  
> **Bağlam:** 500 maddelik audit tamamlandı (`ROADMAP_AUDIT.md`). Bu belge bundan sonraki adımları önceliklendirir.  
> **Kaynak denetimler:** `ROADMAP_AUDIT.md`, `SCENARIO_WRITING_AUDIT.md`, `ROADMAP_AUDIT_SPRINT2_RECOVERY.md`

---

## 1. Tamamlanan (2026-09-21)

500 maddelik yol haritasının **413 in-scope** maddesi denetlendi; **399 Done (%96.6)**, **0 Partial**, **0 Missing**, **15 Deferred**, **87 Excluded**.

### Completion sprint özeti

| Sprint | Kazanım |
|--------|---------|
| Sprint 1 | FFmpeg→MoviePy default render yolu (+65 madde) |
| Batch 2 | Hybrid overlay + EQ/countdown/neon frame (+40) |
| Batch 3 | BGM/SFX wire, retention görsel, B5 niş, B7 infra (+73) |
| Batch 4 | B6 SEO operator pack, B8 kanal sağlığı checklist (+56) |
| Appeal close-out | #472/#475 operatör workflow Done (+2) |
| **Deferred close-out** | Growth operator pack #311-322/#384, #476 recovery (+11) |
| **Infra close-out** | GitHub Actions CI, `PRODUCTION_DEPLOY.md`, `quota_usage.json` gitignore, scipy→ffprobe |

### Senaryo yazma (A–H)

Yarım/boş senaryo sorunu için 8 batch uygulandı: `min_ratio=1.0` narration gate, UI stale plan purge (`planVersion: 2`), render worker gate, word budget repair, `plan_linter.py`, Gemini 429 circuit breaker, astrology fallback, integration testler.

### Diğer önemli teslimler

- **BGM:** 72 parçalı `youtube_safe_bgm_catalog.json` + `youtube_safe_bgm_catalog.py`
- **Overlay:** `effects/overlays.py` hybrid render routing; MoviePy default path
- **Dual voice (#143):** TTS çift seslendirme wire
- **UI:** Senaryo navigasyonu, yeniden üret butonu, kalite paneli
- **Infra:** `docker-compose.yml`, şifreli DB yedek, `.github/workflows/ci.yml`
- **API:** `/api/growth/operator-pack`, `/api/channel-health/repeated-content-recovery`
- **Test:** 27+ section test dosyası, batch wiring testleri

---

## 2. Deferred — 15 Madde

Bilinçli erteleme: kod dışı operasyon, ücretli API veya Studio manuel adım gerektirir.

### A. Hesap & anti-detect (manuel operasyon)

| # | Madde | Kilidi açan |
|---|-------|-------------|
| 16 | 2FA kurulumu | Gerçek Google hesabı + SMS/authenticator |
| 35 | YouTube Premium | Ücretli abonelik |
| 58 | Dokunmatik ekran ipuçları | Playwright prod upload + cihaz profili |
| 59 | Pil API yanıtı | Playwright prod upload + cihaz profili |
| 66 | Kanal yaşlandırma (48s/7g) | Operatör disiplini; plan var (`/api/anti_detect/warmup`), enforce yok |
| 98 | Kendi 4K arka plan kütüphanesi | 50 adet manuel çekim + dosya yükleme |

### B. Ücretli / 3rd-party API

| # | Madde | Kilidi açan |
|---|-------|-------------|
| 113 | AI çizilmiş görseller (Runway/Kling) | FAL/Stability API key + pipeline |
| 324 | Karakter canlandırma (D-ID/SadTalker) | `AVATAR_ANIMATION_API_KEY` + provider seçimi |
| 371 | TubeBuddy/VidIQ arama skoru | Ücretli SEO araç entegrasyonu |

### C. SEO & platform sinyalleri (Studio manuel)

| # | Madde | Kilidi açan |
|---|-------|-------------|
| 401 | Mobil bildirim tetikleyicisi | Studio abone/bildirim operasyonu |
| 402 | Kanal rozetleri ve seviyeler | Studio operasyonu |

### D. İtiraz & monetization (operatör)

| # | Madde | Kilidi açan |
|---|-------|-------------|
| 473 | İtiraz videosunda yüz gösterme | Operatör talk-head kaydı |
| 474 | Kurgu sürecini ekran kaydıyla kanıtlama | Operatör screen record |
| 479 | Sponsorluk formatı | ~100K abone eşiği |
| 480 | Kanal satış piyasası değerlemesi | Operasyonel bilgi / danışmanlık |

### Done (operator) — artık Deferred değil

| # | Madde | Kanıt |
|---|-------|-------|
| 311-315 | Yorumdan video, anket, köprü, seri, canlı yayın | `export_growth_operator_pack` + `/api/growth/operator-pack` |
| 319-322 | Affiliate, niş çarpışması, Tier-1, çapraz platform | Aynı growth pack + mevcut helper'lar |
| 384 | Canlı sohbet / canlı yayın geçişi | `generate_weekly_live_stream_plan` growth pack içinde |
| 476 | Tekrarlanan içerik ret sonrası strateji | `get_repeated_content_rejection_recovery_plan` + API |

---

## 3. Excluded — 87 Upload Maddesi

Otomatik YouTube Studio upload, OAuth upload, günlük upload limiti, metadata upload, Playwright prod screenshot vb. **kod denetimi dışı** bırakıldı.

**Operasyonel gerçek:** Video üretimi pipeline'da; yükleme **manuel YouTube Studio** akışı ile yapılır. Simülasyon kanıtı var (`execute_studio_upload` + testler) ama prod Playwright upload bilinçli olarak scope dışı.

---

## 4. Operasyonel Yapılacaklar

| Görev | Durum | Adım |
|-------|-------|------|
| **Vault unseal** | Operatör | `python scripts/env_vault.py unseal` → `.env` |
| **GEMINI_MODEL doğrula** | Operatör | `.env` içinde güncel free-tier model |
| **1080p default** | Operatör | `RENDER_RESOLUTION_MODE=1080p` |
| **İlk prod render smoke** | Operatör | 1 konu → senaryo → render → dosya kontrol |
| **BGM dosyaları** | Operatör | İlk render'da `AUTO_FETCH_ROYALTY_FREE_BGM=true` |
| **Commit + CI** | ✅ Done | `.github/workflows/ci.yml` |
| **quota_usage.json** | ✅ Done | `.gitignore` — `data/quota_usage.json` |

---

## 5. Ürün Öncelikleri (Önerilen Sıra)

| # | Özellik | Effort | Gerekçe |
|---|---------|--------|---------|
| 1 | ~~GitHub Actions CI~~ | — | ✅ Tamamlandı |
| 2 | ~~§3 ROADMAP tablo restore~~ | — | ✅ `scripts/reconcile_roadmap_audit_section3.py` |
| 3 | Senaryo kalite izleme dashboard | M | `validation.issues` + plan linter metrikleri UI |
| 4 | Niş bazlı procedural fallback genişletme | M | Crypto dışı nişlerde AI fail riski |
| 5 | Word budget iyileştirme (96 cap) | S | Generic filler yerine sahne-özel tamamlama |
| 6 | DeepL çeviri (#454) | M | API key gerekir — hâlâ Missing |
| 7 | WebRTC/STUN tam maskeleme (#32–33) | M | Anti-detect iyileştirme |
| 8 | Avatar pipeline (#324) | L | D-ID key — Deferred |
| 9 | Frontend localStorage testleri | S | Batch B regresyon kilidi |
| 10 | ~~Prod deploy dokümantasyonu~~ | — | ✅ `PRODUCTION_DEPLOY.md` |

---

## 6. Senaryo Kalite — Sürekli İzleme

Audit sonrası A–H batch'leri uygulandı. Kalan riskler:

| Risk | Belirti | Önlem |
|------|---------|-------|
| AI 6-kelime stub | Schema geçer, içerik zayıf | Minimum kelime/sahne linter (opsiyonel) |
| Mood tekrarı | 14 sahnede aynı mood | `plan_linter.py` zayıf planlarda regen |
| Gemini quota | 429 → procedural | Circuit breaker aktif |

**Önerilen rutin:** Haftalık 3 konu ile `/api/script/generate` + render smoke.

---

## 7. Teknik Borç

| Borç | Durum | Aksiyon |
|------|-------|---------|
| **§3 ROADMAP tablo restore** | ✅ Done | Reconcile script + footer uyumlu |
| **Git commit cadence** | Açık | Feature-batch commit'leri; CI koruma aktif |
| **scipy optional dep** | ✅ Done | ffprobe fallback `video_composer.py` |
| **quota_usage.json tracked** | ✅ Done | `.gitignore` |
| **Playwright upload sim vs prod** | Dokümante | Prod Excluded — ayrı RFC gerekir |
| **DeepL (#454)** | Missing | API key ile eklenebilir |

---

## 8. Başarı Kriterleri (Sonraki Milestone)

- [x] CI yeşil: `.github/workflows/ci.yml` tanımlı
- [ ] 1 gerçek konu end-to-end: senaryo → 1080p render → BGM mix
- [x] §3 tablo restore: 15 Deferred footer ile uyumlu
- [ ] Operatör: vault unseal + GEMINI_MODEL doğrulandı
- [ ] Senaryo: 14/14 usable narration 3 farklı nişte

---

*Son güncelleme: 2026-09-21 — deferred close-out + CI/deploy infra.*
