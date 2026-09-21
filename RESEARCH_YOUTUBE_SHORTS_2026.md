# RESEARCH — YouTube Shorts Monetizasyon & Uyum (2026)

**Tarih:** 2026-09-21 · **Rol:** Creative Director + Research Lead · **Proje:** youtubeoto (TR Shorts otomasyon)  
**Yöntem:** Resmi Help Center / Blog + TechCrunch / forum / rakip teardown. Öncelik 2025–2026 resmi kaynak.

> Amaç: Policy strike almadan para kazanmak. Yüzsüz + AI-assisted OK; şablon spam + “uzman AI persona” + metadata stuffing = kanal ölümü.

---

## A. Resmi YouTube politikaları

### A1. YPP eşikleri (2026 → Şubat 2027)

| Katman | Eşik (bugün / 2026) | Açılan özellikler | Kaynak |
|---|---|---|---|
| Fan Funding / Shopping | 500 abone + 3 public upload / 90g + (3k LF saat / 365g **veya** 3M Shorts view / 90g) | Membership, Super Chat/Thanks, Shopping | [creators.youtube.com YPP](https://www.youtube.com/creators/earn/youtube-partner-program/) · erişim 2026-09-21 |
| Ads + Premium (mevcut kanallar) | 1k abone + (4k LF saat / 365g **veya** 10M Shorts view / 90g) | Watch Page ads, Shorts Feed ads, Premium | [AdSense YPP](https://support.google.com/adsense/answer/72851) · 2026-09-21 |
| **Yeni başvuru (Şub 2027+)** | **8k** LF saat / 365g **veya** **20M** Shorts view / 90g | Ads + Premium (fan funding aynı) | [YouTube Blog 10 Ağu 2026](https://blog.youtube/news-and-events/youtube-partner-program-updates-2027-new-opportunities-earn/) |
| Shorts aylık gelir (Şub 2027+) | Her ay için **10M** qualified Shorts view / son 90g | Creator Pool + Premium Shorts payı | [Shorts monetization Help](https://support.google.com/youtube/answer/12504220) · 2026-09-21 |

**Kritik:** Shorts Feed izlenme saatleri, long-form 4k/8k eşiğine **sayılmaz**. Paid campaign view’ları YPP’ye sayılmaz.

### A2. Shorts gelir modeli

1. Ülke bazlı Shorts Feed reklam havuzu  
2. Müzik lisans kesintisi: 0 track → %100 Creator Pool; 1 track → %50; 2+ → ~%33  
3. Engaged view payına göre Creator Pool dağıtımı  
4. Creator **%45** alır (YouTube %55) — kendi müziğin payını **kişisel olarak** düşürmez  

Kaynak: [support.google.com/youtube/answer/12504220](https://support.google.com/youtube/answer/12504220) (2026-09-21).

**Uygulama:** Royalty-free / YouTube Audio Library BGM tercih; Content ID claim’li pop müzik Shorts’u 1dk+ ise blok riski.

### A3. “Inauthentic content” (15 Temmuz 2025) — eski “repetitious”

- Yeniden adlandırma + netleştirme: **kitlesel / şablon / tekrarlayan** içerik YPP’de para kazanamaz.  
- AI yasak **değil**; “orijinal + özgün bakış” şart.  
- Örnek yasak: aynı anlatımla slayt; yüzeysel farkla aynı hikâye şablonu; jenerik AI şablon.  
- Reused content politikası (clip/reaction) **değişmedi**.  

Kaynaklar:
- [Kanal monetization policies](https://support.google.com/youtube/answer/1311392) (changelog 15 Tem 2025)  
- [TechCrunch 9 Tem 2025](https://techcrunch.com/2025/07/09/youtube-prepares-crackdown-on-mass-produced-and-repetitive-videos-as-concern-over-ai-slop-grows/)  
- Rene Ritchie / TeamYouTube mythbuster (AI araçları OK; spam değil)

**Bot için ölüm sinyali:** Aynı beat şablonu + aynı stok sorgusu + günde 10+ neredeyse özdeş Short.

### A4. AI disclosure / altered content

**Zorunlu disclose (gerçekçi / yanıltıcı):**
- Gerçek kişi sanki söylemiş/yapmış gibi  
- Gerçek olay/mekân değiştirme  
- Hiç olmamış gerçekçi sahne  

**Disclose gerekmez:** Animasyon/açıkça gerçek dışı; minör filtre; script/thumbnail üretimi; **kendi sesini klonlama**; caption; gameplay.

**2026 Mayıs+:** Photoreal AI için otomatik etiket; Shorts’ta overlay. Etiket monetization/recommendation’ı **doğrudan** bozmaz; sürekli gizleme → ceza.

Kaynaklar:
- [Disclosing GenAI](https://support.google.com/youtube/answer/14328491) · 2026-09-21  
- [Blog: improving AI labels](https://blog.youtube/news-and-events/improving-ai-labels-viewers-creators/)  
- [TechCrunch 27 May 2026](https://techcrunch.com/2026/05/27/youtube-will-now-automatically-label-ai-videos/)

**Bizim bot:** TTS + stok/prosedürel = genelde “realistic synthetic person/event” değil → Studio AI survey çoğu videoda **No** olabilir; yine de açıklamaya şeffaflık satırı ekle (güven + ileride C2PA). Photoreal Gemini/Veo kişi sahnesi → **Yes** + açıklama.

### A5. AI Persona + hassas konular (HARD FAIL)

Kanal, **AI persona’yı insan uzman gibi** sunup sağlık / hukuk / finans / siyaset tavsiyesi verirse **monetize edilemez**.

Örnek: AI “doktor”, AI yatırım podcast host, AI hukuk yorumu.

Kaynak: [answer/1311392 — AI Personas Related to Sensitive Topics](https://support.google.com/youtube/answer/1311392).

**Kripto/fitness/parenting:** Eğitim + “tavsiye değil” disclaimer OK; “şunu al / kesin kazanç / teşhis” + AI uzman yüzü = DROP.

### A6. Advertiser-friendly (niş riskleri)

Kaynak: [answer/6162278](https://support.google.com/youtube/answer/6162278) · güncellemeler [9725604](https://support.google.com/youtube/answer/9725604) (Tem 2025+).

| Niş (35’ten) | Risk | Not |
|---|---|---|
| Dini alıntı / İslami | Orta | Nefret/ayrımcılık yoksa ads OK; mezhep savaş / “kâfir” framing DROP |
| Stoa / felsefe | Düşük | Güvenli |
| Kripto / finans | Yüksek | Yatırım çağrısı, get-rich, lisanssız ürün → limited/no ads + spam/scam |
| Dark psych / manipülasyon | Yüksek | Zararlı davranış “öğretme”, gaslighting glorify → limited |
| Fitness / sağlık | Yüksek | Tıbbi iddia, mucize kür → unreliable/harmful |
| Parenting | Orta–Yüksek | Çocuk istismarı / tehlikeli pratik yok; kids-directed değilse OK |
| Celebrity / gossip | Orta | Clickbait yanlış thumbnail; hassas olay sömürü |
| Haber / breaking | Yüksek | Sensitive events “profit/exploit”; dezenformasyon |
| Astroloji | Orta | “Kesin gelecek” iddiası vs eğlence |
| Quiz / eğlence | Düşük | Güvenli |
| Tarih / bilim | Düşük–Orta | Şok şiddet görselleri dikkat |

### A7. Telif / Content ID / müzik

- Shorts’ta müzik partner claim’leri Creator Pool’u küçültür (havuz seviyesi).  
- 1dk+ claimed Short → blok / monetize edilmez (Help).  
- Stok: Pexels/Pixabay platform lisansı ticari OK; Wikimedia tek tek CC; SA/NC/ND **kullanma**.  
- YouTube rip / film klipleri → reused + ineligible views.

### A8. Spam / metadata

Kaynak: [Spam Policy 2801973](https://support.google.com/youtube/answer/2801973) · [Hashtags 6390658](https://support.google.com/youtube/answer/6390658).

- Açıklamada tag stuffing yasak; tag alanı ayrı.  
- >60 hashtag yok sayılır / ceza.  
- Yanıltıcı title/thumbnail.  
- **Otomatik / sentetik kitlesel üretim** Community Guidelines spam maddesinde açıkça.

**STOP (kodda):** Açıklamaya 15+ keyword listesi; “SEO keyword dump”; aynı pinned comment spam.

---

## B. Creator / forum gerçeği (2025–2026)

### B1. Ne ölüyor?

- AI ses + jenerik stok + aynı şablon, yüksek upload hızı → inauthentic / suppress  
- Faceless **kategori olarak yasak değil**; “AI slop” hedef ([r/NewTubers tartışmaları](https://www.reddit.com/r/NewTubers/comments/1t2uj6y/is_a_faceless_channel_a_bad_idea_nowadays/))  
- Aynı stok kliplerin tekrar tekrar kullanımı bot bayrağı (kullanıcı raporları)

### B2. Ne yaşıyor?

- Özgün senaryo + gerçek araştırma / yorum  
- Görsel çeşitlilik (her videoda farklı klip seti)  
- Eğitim / açıklayıcı / hikâye (yüzsüz OK)  
- Retention: 0–1.5s hook + 2.5–4s pattern interrupt + loop  

### B3. TR pazar notu

- Dini / ahlaki kıssa + özgün yorum: talep yüksek, ads orta-güvenli (nefret yoksa)  
- Kripto: TR’de hype kanallar demonetize dalgası (2025); eğitim + affiliate disclaimer yolu  
- “Para bas” MoneyPrinter klon kanallar: 2026’da view suppress yaygın (ikincil bloglar / forum)

### B4. Retention taktikleri (forum + rakip ortak)

1. İlk karede iddia/soru (curiosity gap)  
2. Kinetic caption (sessiz izleyici)  
3. Her 3s görsel veya tipografi değişimi  
4. Payoff ≥ %60; son cümle hook’a bağlanır  
5. Günde ≤3–5 **yapısal olarak farklı** Short / kanal (sert kural değil, gözlem)

---

## C. Rakip teardown — özellik matrisi

| Özellik | Pictory | InVideo | Opus Clip | Fliki | Revid | Crayo | ShortGPT | MoneyPrinterTurbo | AutoShorts | Submagic | **Biz (bugün)** | **Biz (P0 hedef)** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Topic→script | ✓ | ✓ | ✗ (clip) | ✓ | ✓ | şablon | ✓ | ✓ | ✓ | kısmi | ✓ | ✓ |
| Stock multi-source | Storyblocks | iStock+ | kaynak video | Storyblocks | AI+stock | gameplay | Pexels | Pexels/Pixabay/Coverr | stock | ✗ | Pexels/Pixabay (+scrape) | +Wikimedia/NASA/Openverse/Archive + lisans ledger |
| License ledger | zayıf | zayıf | N/A | zayıf | zayıf | ✗ | ✗ | ✗ | ✗ | ✗ | yok | **var** |
| Kinetic captions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | güçlü | kısmi | güçlü prosedürel |
| TR TTS | zayıf | orta | N/A | güçlü | orta | zayıf | BYO | Edge/Azure/… | zayıf | ✗ | Edge+ElevenLabs | Azure tercih uyarısı |
| Inauthentic gate | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | zayıf | **hard score** |
| AI disclosure text | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | yok | **otomatik** |
| Niche ban/gate | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | kısmi | research list |
| Auto YT upload | kısmi | ✓ | ✓ | ✓ | ✓ | ✗ | opsiyon | opsiyon | ✓ | ✗ | **kapsam dışı** | out |
| Viewer score | ✗ | ✗ | virality | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | quality_gate | **API/UI** |
| Procedural fallback | ✗ | ✗ | ✗ | ✗ | AI gen | şablon | düz renk? | yok | slideshow | ✗ | cinematic gradient | +kinetic type |

Kaynaklar: [clippie.ai 2026 compare](https://clippie.ai/blog/best-ai-shorts-generator-2026-compared) · [revid.ai/vs](https://www.revid.ai/vs) · [MoneyPrinterTurbo README](https://github.com/harry0703/MoneyPrinterTurbo) · [virvid.ai compare](https://virvid.ai/blog/best-ai-shorts-generator-2026) — erişim 2026-09-21.

**Boşluğumuz (fırsat):** Rakip hiçbiri ciddi **inauthentic + lisans ledger + niş gate** sunmuyor. Monetize-first TR bot = farklılaşma burası.

---

## D. Telif-güvenli kaynaklar + TTS

### D1. Video / görsel

| Kaynak | Anahtar | Ticari | Atıf | Not |
|---|---|---|---|---|
| [Pexels](https://www.pexels.com/license/) | PEXELS_API_KEY | ✓ | opsiyonel | Platform lisansı |
| [Pixabay](https://pixabay.com/service/faq/) | PIXABAY_API_KEY | ✓ | opsiyonel | Standalone satış yasak |
| [Coverr](https://coverr.co/) | COVERR_API_KEY | ✓ | kontrol et | API |
| Mixkit Free | scrape kırılgan | Free License ✓ / Restricted ✗ | item bazlı | Son çare |
| Wikimedia Commons | yok | CC0/PD/BY ✓; SA/NC/ND ✗ | BY zorunlu | Filtre şart |
| NASA Image Library | yok | PD (genelde) | NASA endorsement yok | Uzay/bilim |
| Openverse | yok | CC0/BY/PDM | BY | Rate limit → cache |
| Archive.org Prelinger/NASA | yok | PD koleksiyon | — | Genel arama tuzak |
| AI video (Runway vb.) | ücretli | ticari plan | C2PA/disclose | Photoreal → disclose |

### D2. Müzik

- YouTube Audio Library  
- Pixabay Music / Mixkit Free Music  
- Epidemic/Artlist (ücretli, claim az)  
- **Pop / TikTok trend ses:** Shorts pool + claim risk

### D3. Türkçe TTS

| Motor | Monetize netlik | Not |
|---|---|---|
| **Azure AI Speech** | Net ticari ToS | Önerilen üretim yolu |
| ElevenLabs | Ticari plan | C2PA/etiket trendi |
| Google Cloud TTS | Net | |
| **edge-tts (Edge Read Aloud)** | **Belirsiz / desteklenmez** | MS Q&A: redistribution için yazılı izin yok; Azure önerilir ([MS Learn Q&A](https://learn.microsoft.com/en-us/answers/questions/5730260/inquiry-about-using-read-aloud) · 2026) |
| gTTS | Kısıtlı | Kalite düşük |

**Karar:** Dev/test’te Edge OK; **yayın kanalında Azure veya ElevenLabs**. UI’da uyarı.

---

## E. Sentez — hard rules + backlog

### E1. Niş DROP / GATE listesi

| Aksiyon | Niş / pattern | Neden |
|---|---|---|
| **DROP** | AI uzman persona + finans/sağlık/hukuk tavsiyesi | Policy: AI Personas Sensitive Topics |
| **DROP** | Get-rich crypto “şu coini al” | Scam + advertiser + spam |
| **DROP** | Gerçek kişi deepfake konuşturma | Disclose + reputasyon + CG |
| **DROP** | Çocuk istismarı / tehlikeli parenting “hack” | Kids + harmful |
| **GATE** | Kripto eğitim | Disclaimer zorunlu; “tavsiye değil”; inauthentic score |
| **GATE** | Dark psych | “Eğitici farkındalık” framing; zararlı talimat yok |
| **GATE** | Fitness/sağlık | Disclaimer; teşhis/kür yok |
| **GATE** | Dini | İslami görsel dil; nefret/mezhep savaş yok; Stoa fallback YASAK (zaten fix 8224433) |
| **GATE** | Haber / celebrity | Sensitive event exploit yok; clickbait thumbnail yok |
| **OK** | Stoa, tarih, bilim, quiz, hayvan, genel kültür (özgün) | Düşük risk |

### E2. P0 backlog (bu sprint — acceptance)

1. **Multi-source + license ledger** — her klip `LicenseInfo`; job `visual_credits.json`; SA/NC/ND reddi.  
2. **Niche-aware shot queries** — “cinematic 4k” soup yasak; subject+action+setting+light.  
3. **Inauthentic / originality gate** — skor ≥ eşik hard fail; AI disclosure paragrafı açıklamada.  
4. **Procedural kinetic** — stok yoksa solid renk / “Gorsel Bulunamadi” YOK.  
5. **Viewer score** — plan.meta + API.  
6. **SEO stuffing STOP** — max 3 hashtag; açıklamada tag listesi yok.

### E3. P1

- Azure TTS default path + Edge uyarı banner  
- Upload cadence limiter (yapısal çeşitlilik skoru)  
- Per-channel style fingerprint (font/palette/hook family)  
- Human review queue for GATE niches  
- Music: Audio Library only mode  

### E4. P2

- C2PA metadata yazma  
- A/B retention analytics  
- Brand deal / Shopping incentives (YPP 2027)  

### E5. Kodda STOP

- Açıklamaya keyword stuffing  
- Aynı 3 query şablonu her sahnede  
- Videvo/Mixkit kırılgan scrape’e bağımlılık  
- Edge-TTS’i “ticari garantili” diye pazarlamak  
- Otomatik YouTube upload (kapsam dışı; zaten UI’dan kaldırıldı)  
- Dini → Stoa / Marcus görsel fallback  

---

## Kaynak indeksi (erişim 2026-09-21)

1. https://support.google.com/youtube/answer/1311392 — inauthentic + AI persona  
2. https://support.google.com/youtube/answer/12504220 — Shorts revenue  
3. https://support.google.com/youtube/answer/14328491 — GenAI disclose  
4. https://support.google.com/youtube/answer/6162278 — advertiser-friendly  
5. https://support.google.com/youtube/answer/2801973 — spam  
6. https://blog.youtube/news-and-events/youtube-partner-program-updates-2027-new-opportunities-earn/  
7. https://techcrunch.com/2025/07/09/youtube-prepares-crackdown-on-mass-produced-and-repetitive-videos-as-concern-over-ai-slop-grows/  
8. https://techcrunch.com/2026/05/27/youtube-will-now-automatically-label-ai-videos/  
9. https://www.pexels.com/license/ · https://pixabay.com/service/faq/ · https://mixkit.co/license/  
10. https://learn.microsoft.com/en-us/answers/questions/5730260/inquiry-about-using-read-aloud — Edge TTS  
11. https://github.com/harry0703/MoneyPrinterTurbo · https://www.revid.ai/vs · https://clippie.ai/blog/best-ai-shorts-generator-2026-compared  

---

*Bu belge Phase 2 implementasyonunun tek otorite kaynağıdır. ROADMAP_AUDIT Done maddeleriyle çelişen “fake Done” yazılmaz.*
