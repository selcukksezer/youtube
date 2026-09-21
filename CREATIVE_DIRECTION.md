# Creative Direction — Türkçe Shorts 2026

**Tarih:** 2026-09-21 · **Rol:** Creative Director + Lead Engineer · **Kapsam:** görsel kaynak, sorgu zekâsı, prosedürel grafik, senaryo zanaatı, izleyici skoru.

## 0. Ground truth (bugün ne çıkıyor)

- `.env`'de **PEXELS_API_KEY / PIXABAY_API_KEY / COVERR_API_KEY boş**. Sadece Gemini var (image kotası 429).
- Sonuç: son render (`assets/Marcus_Aurelius_.../`) **14/14 sahne `procedural_fallback.mp4`** = koyu düz renk + "Gorsel Bulunamadi" yazısı. İzleyici gözüyle: 0/10, ilk 1 sn'de kaydırılır.
- Sorgular: her sahne aynı 3 şablon (`X cinematic 4k`, `X <mood> atmospheric`, `ancient rome X`). Anlatımla bağı yok; anlatım TR, sorgu EN, skor token overlap → hep 0.
- Mixkit/Videvo scrape: 429 / HTML kırılgan. Coverr anahtar ister.

## 1. Kararlar — 2026'da Türkçe Short neden tutar

| Karar | Neden | Uygulama |
|---|---|---|
| **İlk 1.5 sn = görsel + sözel kanca aynı anda** | Shorts feed'inde karar süresi < 2 sn. Sessiz izleyen çoğunluk için yazı şart. | `scenes/craft.py` hook formülleri (aile başına 4–6 kalıp); ilk sahne kinetic başlık; captions ≤12 kelime/satır. |
| **Pattern interrupt her 2.5–4 sn** | Retention eğrisi düz kesimde 4 sn sonra düşer. | Timeline zaten 8–16 sahne; prosedürel klipler kendi içinde 2 hareket fazı (giriş / nefes). |
| **Curiosity gap → payoff → loop** | Tekrar izleme = algoritma sinyali. Son cümle ilk cümleye bağlanmalı. | `craft.validate_plan_craft`: hook soru/iddia, payoff ≥ %60 konumda, loop_line 1. sahneyle token paylaşır. |
| **Tempo 2.5–3 kelime/sn (tr-TR)** | Edge-TTS tr-TR doğal hız; altı sıkıcı, üstü anlaşılmaz. | Skor: `pacing_variance` (sahne wps std) + ortalama wps bandı. |
| **Yazı yoğunluğu: 1 fikir / ekran** | Türkçe uzun kelimeler, 9:16 dar. | `caption_lines()` ≤12 kelime, ≤42 karakter satır. |
| **Niş formatı görsel dilini belirler** | Dini: sakin hat/kubbe, yavaş zoom, sıcak amber. Kripto: hızlı grafik, koyu + neon yeşil/kırmızı. Gizem: karanlık, yavaş reveal, sis. | `visuals/palettes.py` niş paleti + hareket profili (`slow_zoom` / `fast_cut` / `reveal`). Prosedürel grafik paletten beslenir. |
| **Sorgu = ÇEKİM tarifi** | Stok API'ler "subject + action + setting + lighting" ile alakalı sonuç verir; "cinematic 4k" gürültü. | `visuals/query_builder.py`: TR anlatım → EN kavram (sözlük + opsiyonel Gemini çeviri, cache) → shot grammar. Ladder: spesifik → jenerik → niş b-roll → prosedürel. |
| **Telif = metadata, tahmin değil** | Her klip lisans + atıf taşır. CC-BY atıf açıklamaya otomatik yazılır. SA/NC/ND ve YouTube-rip **yok**. | `visuals/license.py` + `attribution.py`; job klasörüne `visual_credits.json/.txt`. |

## 2. Görsel kaynak stratejisi (anahtarsız çalışmalı)

Öncelik sırası (anahtar yoksa sessizce atlanır, tek satır log):

1. **Pexels / Pixabay** (anahtarlı, platform lisansı, ticari OK) — dikey video en iyi kaynak.
2. **Coverr** (`COVERR_API_KEY`) — ticari serbest.
3. **Wikimedia Commons** (anahtarsız) — video (webm) + fotoğraf; sadece **CC0 / PD / CC-BY**; SA filtrelenir.
4. **NASA Image & Video Library** (anahtarsız, kamu malı) — uzay/bilim/gizem/kozmik.
5. **Openverse** (anahtarsız, düşük limit → agresif cache) — CC0/BY/PDM fotoğraf.
6. **Internet Archive — yalnız Prelinger + NASA koleksiyonu** (PD) — tarih/haber arşiv dokusu. Genel arama **yok** (CC0 etiketli oyun kaydı tuzağı).
7. **Prosedürel motion graphic** — stok yoksa sahne yine "tasarlanmış" görünür.

Fotoğraf → Ken Burns (ffmpeg zoompan) ile 9:16 klip. Yatay video → merkez crop + hafif zoom (`crop_strategy`).

Niş kaynak tercihi: dini → wikimedia(cami/hat) + pexels; kripto → pexels/pixabay + prosedürel veri grafiği; gizem → nasa + wikimedia + koyu prosedürel; tarih → archive prelinger + wikimedia.

## 3. Prosedürel grafik — "FAILSAFE" değil, stil

- Arka plan: niş paletinde 2–3 renkli hareketli gradyan + yavaş parçacık/gren.
- Metin: anlatım satırı kelime kelime (kinetic), ≤12 kelime; Arial Bold (sistem), gölge + hafif glow.
- Hareket: niş profiline göre `slow_zoom` (dini/stoa), `pulse` (kripto), `reveal_from_dark` (gizem).
- Sahne 0'da başlık kartı; diğerlerinde anlatım cümlesi. Her klip farklı seed → görsel tekrar yok.

## 4. İzleyici skoru (0–100)

`hook_strength` 25 · `visual_alignment` 25 (tek dilde: anlatım EN kavramları ↔ sorgu/klip metni) · `pacing` 15 · `loop_closure` 15 · `caption_fit` 10 · `license_safety` 10 (hard: unsafe lisans → render bloke; diğerleri uyarı).

UI: `plan.meta.viewer_score` (`/api/script/generate` yanıtında).

## 5. Bilerek yapılmayanlar

- Otomatik upload (kapsam dışı). Veo/Gemini image (kota). Mixkit/Videvo scrape (kırılgan; Mixkit son sırada tutuldu, Videvo kaldırıldı — lisans karışık).
- Kardeş ajanların açık dosyalarına dokunulmadı; yeni modüller + `video_fetcher.py` / `director/compiler.py` ince bağlama.
