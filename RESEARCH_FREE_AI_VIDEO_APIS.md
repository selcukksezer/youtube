# Free / Freemium AI Video APIs (2025–2026)

Araştırma tarihi: 2026-09-21. Amaç: YouTube Shorts (monetize) için ticari-güvenli, kaliteli text-to-video / image-to-video API’leri.

## Tasarım kararı (mixer)

Stock ve procedural **son çare değil**. Üç kaynak eşit peer:

| Kaynak | Rol |
|--------|-----|
| AI video API | Sinematik / data-viz clip |
| Stock (Pexels/Pixabay/…) | Gerçek footage |
| Procedural / kinetic | Tipografi, calligraphy, abstract |

Env oranları (normalize edilir):

```
VISUAL_MIX_AI=0.4
VISUAL_MIX_STOCK=0.4
VISUAL_MIX_PROCEDURAL=0.2
VISUAL_MIX_SEED=   # boş = job hash; set = reproducible
USE_AI_VIDEO=true  # key yoksa otomatik false sayılır
```

Niche bias (örnek): dini → procedural↑ stock↑ AI yüz↓; crypto → AI↑ stock chart↑.

---

## Ranking (freeness × quality × YouTube commercial × API ease)

| Rank | Provider | Free? | Commercial YT? | Quality | Integrated? | Notes |
|------|----------|-------|----------------|---------|-------------|-------|
| 1 | **Fal.ai** (Wan / Hunyuan) | Signup credits (variable expiry) then pay | Yes (paid/credit usage; check model ToS) | High (Wan 2.1 9:16) | **Yes** | Best API DX; `FAL_API_KEY` / `FAL_KEY` |
| 2 | **Hugging Face Inference Providers** | **$0.10/mo** free; PRO $2 | Model-dependent (Wan Apache-ish OK) | Med–High | **Yes** | Routes to fal/replicate; `HF_TOKEN` |
| 3 | **Replicate** | Try-for-free (limited), then PAYG | Model license; platform says commercial OK for hosted | High | **Yes** | `REPLICATE_API_TOKEN` |
| 4 | **DeepInfra** | Trial/PAYG (no ongoing free) | Hosted Wan OK if you pay | High (Wan 2.2) | **Yes** | `DEEPINFRA_TOKEN`; base64 video |
| 5 | **PiAPI** (Kling etc.) | **~$0.50** signup | Treat as commercial after paid; verify | High (Kling) | **Yes** | `PIAPI_KEY`; free = few clips |
| 6 | **Gemini Veo** (optional) | **No free video tier** | Paid API commercial | Highest | Optional | `USE_GEMINI_VIDEO_GEN` + billing |
| 7 | **Local / ComfyUI Wan** | Unlimited (GPU cost) | Model license (Wan open) | Med–High | Stub | `LOCAL_AI_VIDEO_URL` |
| — | Luma Dream Machine API | No free API; web free = **non-commercial** + watermark | Free = **No** | High | Skip free | Paid Plus+ only |
| — | Runway Gen-3/4 | 125 one-time, watermarked | Free = weak; paid OK | High | Skip free | Not integrated |
| — | MiniMax / Hailuo | App free = watermark, **no commercial** | Free = **No** | High | Optional paid key only | |
| — | Pika | ~80 signup credits | Confirm ToS | Med | Skip | Weak API docs |
| — | Stability SVD | **API deprecated Jul 2025** | N/A hosted | Med | No | Self-host only |

**Honest “unlimited”:** rotate free credits (Fal + HF $0.10 + PiAPI $0.50 + Replicate trials) + **cache** + stock + procedural mix. Pure free AI alone ≈ **few clips/day**, not infinite.

---

## Per-provider facts (English)

### Fal.ai — Wan / Hunyuan
- Docs: https://fal.ai/models/fal-ai/wan-t2v/api · https://fal.ai/models/fal-ai/hunyuan-video/api
- Auth: `Authorization: Key $FAL_KEY` (repo also accepts `FAL_API_KEY`)
- Cost: signup free credits; Wan ~$0.20/clip 480p, ~$0.40 720p; Hunyuan billed in units
- Limits: new accounts ~2 concurrent
- Duration/res: ~5s (81 frames @16fps); 480p/720p; **9:16**
- Commercial: intended for production; verify account terms
- Pattern: queue submit → poll → `video.url`
- Python: `fal_client` or raw `queue.fal.run`

### Hugging Face Inference Providers
- Docs: https://huggingface.co/docs/inference-providers/en/tasks/text-to-video
- Auth: Bearer `HF_TOKEN`
- Cost: **$0.10/mo** free users; then provider rates
- Model eg: `Wan-AI/Wan2.1-T2V-1.3B` via `provider="fal-ai"`
- Commercial: respect model card license
- Pattern: sync `InferenceClient.text_to_video` → bytes

### Replicate
- Docs: https://replicate.com/docs · models e.g. Wan / Kling / Veo
- Auth: `Authorization: Bearer r8_…` / `REPLICATE_API_TOKEN`
- Cost: limited free tries; then GPU/sec or per-output
- Commercial: “every video model commercial on Replicate” (blog) — still check model
- Pattern: create prediction → poll → output URL

### DeepInfra
- Docs: https://docs.deepinfra.com/apis/text-to-video
- Auth: Bearer `DEEPINFRA_TOKEN`
- Model: `Wan-AI/Wan2.2-T2V-A14B` etc.
- Response: `video_url` as **data:video/mp4;base64,…** (decode locally)
- Cost: PAYG (~$0.07+/sec class models)

### PiAPI (Kling gateway)
- Docs: https://piapi.ai/ · Kling pages
- Auth: `x-api-key` / `PIAPI_KEY`
- Free: ~$0.50 signup
- Kling 2.6 ~$0.20 / 5s standard
- Async task + poll

### Google Veo / Gemini video
- Docs: https://ai.google.dev/gemini-api/docs/video · pricing page
- **Free tier: Not available** for Veo
- Paid: Lite ~$0.05/s 720p … Standard $0.40/s
- Already in repo: `google_ai_hub.generate_veo_video`
- Enable only with billing + `USE_GEMINI_VIDEO_GEN=true`

### Luma / Runway / Hailuo free
- **Do not use free tiers for monetized Shorts** (watermark / non-commercial).

### Stability Stable Video
- Hosted API **removed 2025-07-24**. Self-host only.

### Local OSS (Mac)
- Wan 2.1 1.3B ~8–13GB VRAM; Apple Silicon via MLX/ComfyUI possible but slow.
- Adapter: POST `{LOCAL_AI_VIDEO_URL}/generate` → `{url|path}`. True unlimited when online.

---

## Daily capacity estimate (one account each, free only)

| Stack | Approx clips/day | Notes |
|-------|------------------|-------|
| HF $0.10 alone | 0–2 short Wan | Burns fast |
| Fal signup credits | tens until expiry | One-shot |
| PiAPI $0.50 | ~1–2 Kling | One-shot |
| Replicate free tries | handful | Then card |
| **Mixer (AI+stock+proc)** | **unlimited Shorts** | AI only on ~40% scenes; rest free |

Öneri: Short başına 3–5 AI sahne, kalan stock/procedural → günde onlarca Short mümkün.

---

## Env keys

```
USE_AI_VIDEO=true
VISUAL_MIX_AI=0.4
VISUAL_MIX_STOCK=0.4
VISUAL_MIX_PROCEDURAL=0.2
VISUAL_MIX_SEED=
FAL_API_KEY=          # or FAL_KEY
HF_TOKEN=
REPLICATE_API_TOKEN=
DEEPINFRA_TOKEN=
PIAPI_KEY=
LOCAL_AI_VIDEO_URL=   # optional ComfyUI/proxy
# optional paid:
USE_GEMINI_VIDEO_GEN=false
GEMINI_API_KEY=
MINIMAX_API_KEY=
```

## Verify

1. Set keys + mix ratios; `USE_AI_VIDEO=true`
2. Render one Short
3. Logs: `[MIX] scene=N → ai|stock|procedural` and `[AI-VIDEO:fal]` / stock / kinetic
4. `visual_credits.json` / description attribution for AI + CC stock
