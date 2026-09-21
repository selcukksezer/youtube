# İnsan Eli Değmiş Shorts — Keşfet Canavarı Manifesto

**Tarih:** 2026-09-21  
**Kaynak prompt:** Kullanıcı (kelimesi kelimesine karşılandı — §0)  
**Resmî politika:** [YouTube YPP / inauthentic](https://support.google.com/youtube/answer/1311392) (15 Tem 2025)  
**Kod:** `craft/human_director.py` · `compliance/` · görsel mix `visuals/`

---

## 0. Prompt cümle → karşılık (yüzeysel okuma yok)

| Kullanıcı cümlesi | Karşılık |
|-------------------|----------|
| “Senaryo için kendinden bir şeyler kat” | `craft/human_director.py` her videoya **tek POV açısı** (kanıt / paradoks / itiraf / sayı / yasak) enjekte eder; şablon listicle’ı reddeder. |
| “İlla denilenin dışına çıkma zorunluluğu yok” | Bu belge + kod, roadmap maddesine kör bağlı değil; keşfet sinyallerine göre karar verir. |
| “Hâlâ kaliteli video üretemiyoruz” | Kabul. Eski pipeline = AI senaryo + stok = **AI çöpü**. Yeni hedef: insan editör hissi + retention. |
| “Stok + farklı telifsiz kaynaklar” | `visuals/` multi-source + AI/stok/prosedürel **mix** (`bb45e84`); lisans ledger. |
| “Telif ihlali yok” | Yalnız CC0 / platform commercial / AI commercial; YouTube rip yok. |
| “API anahtarın var, sen yaz” | Higgsfield/Fal/Kling/… adapter’lar + mix; key `.env`’de. |
| “İlk kodun üstüne inşa zorunlu değil” | `craft/` **yeni katman** — eski generator’ı yamalamak yerine son geçişte insan-yönetmen rewrite. |
| “Amaç: Shorts’tan para” | YPP + inauthentic + Shorts pool bilgisi §1; spam kanal = gelir 0. |
| “Politika araştır: para / AI / telif / ihlal” | `RESEARCH_YOUTUBE_SHORTS_2026.md` + bu dosya §1 (resmî URL’ler). |
| “Forum / başarılı creator / bot özellikleri” | §2–3; CapCut/Submagic/Fliki/Revid özellik matrisi → bizde olmalı listesi. |
| “3 saniyelik araştırma değil” | Resmî Help + TechCrunch + creator guide + rakip teardown; tarihli. |
| “3–5 satır stub yazma” | `human_director.py` tam rewrite/ skor / edit directive — testli. |
| “Web’den bak, kod örneği bak” | Bu oturumda Help Center + Submagic/CapCut feature sayfaları tarandı. |
| “Düz AI senaryo + stok basit bot olma” | **Yasak profil.** İnsan POV + mute hook + loop + kesim yoğunluğu + özgün açı. |
| “İnsan elinden çıkmış gibi” | §4 craft kuralları + `apply_human_craft()`. |
| “AI çöplüğü oluşturma” | `inauthentic_risk` hard-fail + `discovery_beast` eşik. |
| “İnsanların izlediği / takip ettiği kanal” | Retention/swipe/share sinyalleri §5; skor UI’da. |
| “Keşfete düşürmez / keşfet canavarı” | Seed test: ilk 1–3 sn + %izlenme + loop/share; `discovery_beast_score`. |
| “Bu promptu kelimesine kadar oku” | Bu tablo + implementasyon. |

---

## 1. Politika (para kazanma için ölüm / yaşam)

**Resmî (15 Tem 2025):** “repetitious” → **inauthentic content**.  
AI yasak değil. Yasak olan: kitlesel şablon, aynı anlatımla slayt, yüzeysel farkla özdeş videolar, izleyici değeri olmayan spam.

**Ölüm sinyalleri (kanal):**
- Her Short birbirinin kopyası (aynı beat, aynı stok, aynı kanca)
- AI ses + generic stok + “şunu aklında tut” filler
- AI uzman persona + finans/sağlık/hukuk tavsiyesi → monetize **DROP**

**Yaşam sinyalleri:**
- Özgün bakış / yorum / hikâye
- Anlamlı kurgu (kesim, tempo, caption)
- Nişte spesifik detay (genel “kripto yükseliyor” değil)

Kaynak: https://support.google.com/youtube/answer/1311392

---

## 2. Keşfet (Discover) gerçekleri

Algo yüz tanımaz; **swipe vs izle**, %izlenme, rewatch/loop, share bakar.  
Faceless cezası yok; ince şablon spam’i izleyici reddeder → seed ölür.

**Bizim kaldıraçlar:**
1. İlk 1–3 sn: sessiz okunabilir kanca (≤10 kelime caption)
2. 2–4 sn’de görsel değişim (statik 6 sn = ölüm)
3. Payoff + döngü (son sahne ilk vaadi kapatır)
4. Paylaşılacak bir cümle / sayı / yasak

---

## 3. Rakip araçlar → bizde olmalı

| Özellik | CapCut/Submagic/Fliki | Biz (hedef) |
|---------|----------------------|-------------|
| Karaoke caption ortada | ✅ | Edit directive + mevcut word timings |
| Hook title overlay | ✅ | `human_craft.mute_hook_line` |
| B-roll her 2–4 sn | ✅ | Mix + cut_density directive |
| Silence trim / jump cut | ✅ | TTS breath + shock silence (var) |
| Özgün senaryo açısı | zayıf (çoğu şablon) | **human_director POV** |
| Inauthentic gate | yok | **compliance hard-fail** |
| Lisans ledger | zayıf | visuals license |

---

## 4. İnsan eli kuralları (kodda enforce)

1. **Tek video = tek POV** — aynı nişte bile açı değişir (seed).
2. **Mute hook** — sahne 1’in ilk satırı caption’da tek başına okunur.
3. **Spesifiklik** — jenerik filler yasak; sayı / isim / kontrast zorunlu.
4. **Loop** — final, açılış vaadini kelime/öz olarak bağlar.
5. **Kesim yoğunluğu** — hedef ortalama shot ≤ 3.5 sn.
6. **Görsel çeşit** — AI+stok+prosedürel mix; aynı query tekrarı cezalı.
7. **Ses insanı** — Edge yerine mümkünse Azure/ElevenLabs; jitter/breath zaten var.
8. **Keşfet skoru < eşik → regenerate / fail soft**

---

## 6. Derin denetim sonucu (2026-09-21 tekrar)

**Boşluk bulundu:** `edit_directives` yazılıyordu ama render/UI **uygulamıyordu** → kağıt kaplan.

**Kapatıldı:**
| Boşluk | Fix |
|--------|-----|
| Shot hold clamp yok | `enforce_shot_holds()` craft’ta + composer’da `max_hold` |
| Mute hook overlay yok | Intro card + sticky banner = `mute_hook_line` |
| Karaoke ortada yok | `y_position=0.52` + mid-frame margin izni |
| Render UI planı craft’sız | `render_worker` Director öncesi `apply_human_craft` |
| Composer directive görmüyor | `human_craft=` kwargs → interrupt süresi, banner, intro |
| UI keşfet skoru yok | `sqp-discovery` + `sqp-pov` pills; düşük skor render kapar |

**Hâlâ zayıf (sonraki tur):** CapCut density **lite** bilinçli tradeoff (punch-in 1080p MoviePy kilidi / hang risk — değiştirilmedi).

**DONE bu tur:**
| Boşluk | Fix |
|--------|-----|
| Azure TTS | `azure_tts.py` + `AZURE_SPEECH_KEY/REGION`; sıra ElevenLabs→Azure→Gemini→Edge |
| Kanal B-roll arşivi | `channel_broll.py` → `assets/channels/<slug>/broll/<niche>/` archive-first + promote |
