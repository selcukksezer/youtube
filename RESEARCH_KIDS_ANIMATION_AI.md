# Kids Animation AI + YouTube COPPA Research (2025–2026)

Araştırma tarihi: **2026-09-21**. Amaç: 60 sn çocuk Shorts (soft eğitim / ahlak / hayvan / alfabe) için en iyi AI video API’leri + Made for Kids gerçekliği.

## Verdict (dürüst)

| Karar | Anlam |
|-------|--------|
| **GATE** (monetizasyon) | Niche **para kazanma** için düşman ortam. Made for Kids → kişiselleştirilmiş reklam yok / gelir düşer; düşük kalite / mass AI kids → YPP askı / limited ads riski yüksek. |
| **SHIP tech** | Yayın istiyorsan teknik stack hazır; **Made for Kids zorunlu**, veri toplama metadata kapalı, gerçek çocuk yüzü yasak. |
| **DROP değil** | Yasal çocuk içeriği yayınlanabilir; sadece “otomatik kids farm → zengin ol” hikâyesi yok. |

**Özet:** Kaliteli, orijinal, net hikâyeli Soft-edutainment kısa animasyon mümkün. Spam / tekrarlayan AI kids kanalı YPP’de ölür.

---

## YouTube / COPPA — Made for Kids

### Ne yapılmalı?

- Çocuk birincil hedef veya çocuk karakter/tema/oyuncak ağırlıklıysa video **Made for Kids** işaretlenmeli (yasal sorumluluk yaratıcıda).
- Yanlış etiket → FTC/COPPA + YouTube hesap aksiyonu riski.
- Kaynaklar:
  - https://support.google.com/youtube/answer/9527654
  - https://support.google.com/youtube/answer/9528076
  - https://support.google.com/youtube/answer/9632097

### Monetizasyon limitleri

- **Kişiselleştirilmiş reklam yok** (COPPA). Contextual / sınırlı reklam + Premium pay olabilir; RPM genelde düşer.
- MFK’te kapalı: yorumlar, bildirim zili, üyelik, Super Chat/Stickers, cards/end screens, merch, save-to-playlist, vb.
- YPP kalite ilkeleri (kids & family): deceptively educational, hard-to-follow / mass auto-gen, sensational keyword stuffing, strange use of children’s characters → **limited/no ads** veya kanal YPP suspension.
  - https://support.google.com/youtube/answer/1311392
  - https://support.google.com/youtube/answer/10774223

### AI kids / otomatik kanal riski

- Temmuz 2025 “inauthentic / mass-produced” netleştirmesi: AI yasak değil; **tekrarlayan, yüzeysel, mass-produced** içerik monetizasyona elverişsiz.
- Gerçekçi AI insan benzerliği → disclosure / privacy removal süreçleri.
  - https://www.youtube.com/howyoutubeworks/ai/
- **Gerçek çocuk yüzü / okul / cinsel ima / şiddet / horror** bu repo’da sert yasak (prompt filter).

### Repo hard rules

- Upload: `selfDeclaredMadeForKids=true` kids niche’te.
- Metadata: yorum/pin/CTA data-collection yok; MFK disclosure description’da.
- Visual: `style_preset=kids_cartoon` — bright soft 2D/Pixar-like, **asla photoreal çocuk**.

---

## Ranking (kids cartoon × commercial × API × cost)

Skor 1–5. “Kids cartoon” = stil kontrolü + soft defaults.

| Rank | Provider | Kids cartoon | Commercial YT | API maturity | Cost / free | Integrated? | Notes |
|------|----------|--------------|---------------|--------------|-------------|-------------|-------|
| 1 | **Fal.ai Wan / Hunyuan** (+ cartoon prompts) | 4 | 4 (paid/credit) | 5 | Freemium credits → PAYG | **Yes** | En iyi DX; 5s → stitch 60s |
| 2 | **PiAPI Kling** | 4 | 4 (paid) | 4 | ~$0.50 signup | **Yes** | Cartoon prompt’larda güçlü |
| 3 | **Replicate** (Wan/Kling host) | 4 | 4 | 4 | Trial → PAYG | **Yes** | Model lisansına bak |
| 4 | **Runway Gen-4.5** (paid API) | 5 | 5 | 5 | Paid only | **Yes** | `RUNWAYML_API_SECRET`; 2–10s |
| 5 | **Luma Ray** (paid API) | 4 | 5 | 5 | Paid API | **Yes** | `LUMA_API_KEY`; free web ≠ commercial |
| 6 | **MiniMax Hailuo** (paid key) | 4 | 4 | 4 | Paid | **Yes** | Free app watermark / non-commercial — sadece paid key |
| 7 | **Gemini Veo** | 4 | 5 | 4 | No free video | Optional | Billing + `USE_GEMINI_VIDEO_GEN` |
| 8 | **HF Inference** Wan | 3 | 3–4 | 3 | $0.10/mo | **Yes** | Az kota |
| 9 | **DeepInfra Wan** | 3 | 4 | 3 | PAYG | **Yes** | |
| 10 | **OpenAI Sora** (`v1/videos`) | 4 | 4 | 3 | Paid; **EOL 2026-09-24** | **Yes** | Prefers U18-safe; no real people; short-lived |
| 11 | **Local ComfyUI / Wan toon** | 3–4 | Model license | 2 | GPU | Stub | `LOCAL_AI_VIDEO_URL` |
| 12 | **Higgsfield** (Seedance/Hailuo/Kling host) | 4 | 4–5 paid | 4 | PAYG | **Yes** (peer) | `HIGGSFIELD_*` — sibling wire |
| — | Pika | 3 | Confirm | 2 | Credits / via Fal | Via Fal if model ID set | Weak first-party DX |
| — | Adobe Firefly Video | 3 | Enterprise ToS | 2 | Creative Cloud | **Skip** | No simple self-serve Shorts API |
| — | Kaiber / DomoAI / Viggle | 3 | Varies | 1–2 | App-first | **Skip** | Character tools; solid public T2V API yok |
| — | Animoto | — | — | — | — | **Skip** | Template, not generative AI |
| — | DeepBrain / Elai “kids avatar” | 2 | Plan-dependent; Elai basic often non-commercial | 3 | Paid | **Skip** | Presenter avatar ≠ kids cartoon; minors ToS tight |

**Best picks for this product:** Fal + Kling (PiAPI) + Runway/Luma when budget; stitch clips to 60s. Sora only while API alive.

---

## 60s Short pipeline

1. Niche `36_kids_animation` → Made for Kids + kids_cartoon prompts + safety filter.
2. VISUAL_MIX kids bias: AI ↑, stock = kid-safe animal/nature only, procedural = soft pastel kinetic.
3. Her AI sahne: API max ~5–10s → `N = ceil(duration / clip_max)` clip üret → ffmpeg concat (`visuals/ai_video/stitch.py`).
4. Full Short hedef süre içerik-driven **≤60s** (scenario pack `max_duration=60`).

### Env keys

```
USE_AI_VIDEO=true
VISUAL_MIX_AI=0.55
VISUAL_MIX_STOCK=0.2
VISUAL_MIX_PROCEDURAL=0.25
AI_VIDEO_CLIP_MAX_SEC=5
AI_VIDEO_STYLE_PRESET=kids_cartoon   # auto for kids niche
FAL_API_KEY=
HF_TOKEN=
REPLICATE_API_TOKEN=
DEEPINFRA_TOKEN=
PIAPI_KEY=
RUNWAYML_API_SECRET=
LUMA_API_KEY=
MINIMAX_API_KEY=
OPENAI_API_KEY=          # Sora v1/videos (deprecated 2026-09-24)
LOCAL_AI_VIDEO_URL=
USE_GEMINI_VIDEO_GEN=false
GEMINI_API_KEY=
```

### Verify

1. `python -m unittest tests.test_kids_animation tests.test_ai_video_providers -q`
2. Key’lerle bir Short: niche `36_kids_animation`
3. Log: `[MIX] … ai`, `[AI-VIDEO:…]`, `[AI-VIDEO:stitch] n=…`
4. Upload status `selfDeclaredMadeForKids: true`

---

## URLs (quick index)

| Topic | URL |
|-------|-----|
| Set audience / MFK | https://support.google.com/youtube/answer/9527654 |
| Determine MFK | https://support.google.com/youtube/answer/9528076 |
| Watching MFK | https://support.google.com/youtube/answer/9632097 |
| Monetization / kids quality | https://support.google.com/youtube/answer/1311392 |
| Kids best practices | https://support.google.com/youtube/answer/10774223 |
| YouTube AI disclosure | https://www.youtube.com/howyoutubeworks/ai/ |
| Fal Wan | https://fal.ai/models/fal-ai/wan-t2v/api |
| Runway API | https://docs.dev.runwayml.com/ |
| Luma video API | https://docs.lumalabs.ai/docs/video-generation |
| OpenAI Sora video | https://developers.openai.com/api/docs/guides/video-generation |
| Free AI video research (repo) | `RESEARCH_FREE_AI_VIDEO_APIS.md` |
