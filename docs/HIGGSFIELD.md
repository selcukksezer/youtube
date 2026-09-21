# Higgsfield AI — entegrasyon notu

> Altyapı hazır: `visuals/ai_video/providers/higgsfield.py`  
> Resmî docs: https://docs.higgsfield.ai  
> Console / bakiye: https://console.higgsfield.ai

## Ne bağlandı

| Parça | Durum |
|-------|--------|
| Auth `Authorization: Key ID:SECRET` | ✅ |
| Async submit → poll `status_url` → download MP4 | ✅ |
| Visual mixer AI peer (priority 8) | ✅ |
| Seedance 2.5 T2V varsayılan (9:16 Shorts) | ✅ |
| Model fallback listesi | ✅ |
| Image-to-video / DoP / Soul | ⏳ hazır değil — aynı client ile eklenebilir |

## `.env`

```bash
# A) tek satır
HIGGSFIELD_CREDENTIALS=your_key_id:your_key_secret

# B) çift
HIGGSFIELD_API_KEY_ID=...
HIGGSFIELD_API_KEY_SECRET=...

# Opsiyonel
HIGGSFIELD_T2V_MODEL=bytedance/seedance-2.5/text-to-video
HIGGSFIELD_RESOLUTION=720p
HIGGSFIELD_GENERATE_AUDIO=false
USE_AI_VIDEO=true
```

**Uyarı:** `HF_TOKEN` = HuggingFace. Higgsfield için kullanma.

## Akış

1. Console’da key oluştur, bakiyeyi doldur (min ~$5 PAYG).
2. Key’leri `.env`’e yaz → vault seal/unseal.
3. `./run_ui.sh` → Short üret.
4. Log: `[AI-VIDEO:higgsfield] generating…` sonra `[OK] [AI-VIDEO:higgsfield] model=…`

Mixer hâlâ stok + prosedürel peer kullanır (`VISUAL_MIX_*`).

## Model değiştirme

Console catalog’dan endpoint path kopyala → `HIGGSFIELD_T2V_MODEL=owner/model/variant`.  
Kod önce bu modeli dener; 404 olursa Seedance / Hailuo / Kling listesine düşer.

## Notlar

- Süre API’de 4–30 sn (sahne süresi clamp edilir).
- Çıktı URL’leri ~7 gün; biz hemen lokal cache’e indiriyoruz.
- Ücretsiz sınırsız tier yok — bakiye bitince HTTP 402, zincir diğer provider’a geçer.
