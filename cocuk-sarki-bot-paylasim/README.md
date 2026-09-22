# Çocuk Şarkı MV Stüdyosu

Yerel bilgisayarınızda çalışan, web panelli **çocuk şarkısı müzik videosu** üretim uygulaması.

- Master ses (Suno veya yüklenen MP3) + söz → klip planı + Flow promptları
- **Playwright**, sizin Chrome’unuzdaki **Google Flow** arayüzünü kontrol eder
- Sessiz klipleri indirir, master dilimi basar, **FFmpeg** ile final MP4 birleştirir
- Ana ürün yolu: **Çocuk Şarkı** stüdyosu (`/cocuk-sarki`)

> Flow’un resmî API’si **kullanılmaz**. Google şifreniz uygulamaya girilmez.
> Bu paylaşım paketinde **API anahtarı yoktur** — kendi anahtarlarınızı Ayarlar’dan veya `.env` ile girersiniz.

**Tam kullanım anlatımı:** [`KULLANIM_KILAVUZU.md`](./KULLANIM_KILAVUZU.md)

## Gereksinimler

| Gereksinim | Kurulum |
|---|---|
| Node.js 22+ | https://nodejs.org |
| FFmpeg + ffprobe | `winget install Gyan.FFmpeg` |
| Google Chrome | https://www.google.com/chrome/ |
| OpenAI API anahtarı | https://platform.openai.com |
| Google Flow erişimi | https://labs.google/fx/tools/flow |

## Hızlı kurulum

```powershell
npm install
copy .env.example .env
npm run db:migrate
npx playwright install chromium
npm run dev
```

Panel: **http://localhost:3210**

1. **Ayarlar** → OpenAI (ve isteğe bağlı Suno) anahtarınızı girin  
2. Flow’u açın → Chrome’da Google’a bir kez giriş yapın  
3. Yeni çocuk şarkı projesi → ses + söz → Hazırla → karakterler → otomasyon → render  

Ayrıntılar için **KULLANIM_KILAVUZU.md**.

## Güvenlik

- OpenAI / Suno anahtarları istemciye gönderilmez; bellek veya şifreli yerel DB
- `.env`, `chrome-profile/`, `projects/`, `prisma/dev.db` paylaşım zip’ine **dahil edilmez**
- CAPTCHA / 2FA durumunda otomasyon duraklar; engeller aşılmaz

## Geliştirme

```powershell
npm test
npm run build
npm start
```

Ana kod: `src/server/services/song.ts`, `prompt-builder.ts`, `src/server/automation/`, `src/lib/`
