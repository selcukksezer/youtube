# Çocuk Şarkı MV Stüdyosu — Kullanım Kılavuzu

Bu belge paylaşım paketindeki programın ne işe yaradığını, nasıl kurulacağını
ve baştan sona nasıl kullanılacağını anlatır. **Kendi API anahtarlarınızı**
girerek çalıştırırsınız; pakette hazır anahtar yoktur.

---

## 1. Bu program ne yapar?

Türkçe **çocuk şarkısı müzik videosu** üreten yerel bir stüdyodur.

1. Master ses (MP3/WAV/FLAC — Suno veya kendi dosyanız) + şarkı sözü verirsiniz.
2. Program sözleri klip sürelerine böler, sahne ve karakter planı çıkarır.
3. **Google Flow** (Veo) arayüzünü Playwright ile kontrol ederek sessiz video
   klipleri üretir.
4. Her klibe master parçanın ilgili saniye dilimini basar.
5. FFmpeg ile tek bir final MP4 birleştirir; isteğe bağlı YouTube meta / altyazı üretir.

> Flow’un resmi API’si kullanılmaz. Sizin Chrome oturumunuzdaki Flow sayfası
> otomatik tıklanır. Google şifreniz uygulamaya girilmez.

Port: **http://localhost:3210**

---

## 2. Gereksinimler (Windows 10/11)

| Gereksinim | Kontrol | Kurulum |
|---|---|---|
| Node.js 22+ | `node -v` | https://nodejs.org |
| FFmpeg + ffprobe | `ffmpeg -version` | `winget install Gyan.FFmpeg` (terminali yeniden açın) |
| Google Chrome | — | https://www.google.com/chrome/ |
| OpenAI API anahtarı | — | https://platform.openai.com/api-keys |
| Google Flow erişimi | — | https://labs.google/fx/tools/flow |
| Suno anahtarı (opsiyonel) | — | kie.ai veya kullandığınız Suno köprüsü |

---

## 3. Kurulum (ilk açılış)

PowerShell’de paket klasörüne girin:

```powershell
cd "C:\yol\cocuk-sarki-bot-paylasim"

# 1) Bagimliliklar (+ prisma generate)
npm install

# 2) Ortam dosyasi (API anahtari istege bagli; Ayarlar'dan da girilebilir)
copy .env.example .env
# Notepad ile .env acip OPENAI_API_KEY yazabilirsiniz — zorunlu degil

# 3) Veritabani
npm run db:migrate

# 4) Playwright tarayici destekleri (Chrome kontrolu icin)
npx playwright install chromium

# 5) Baslat
npm run dev
```

Tarayıcıda açın: **http://localhost:3210**

Üretim derlemesi: `npm run build` ardından `npm start`

---

## 4. İlk ayarlar (Ayarlar + Flow)

### Ayarlar (`/settings`)
1. **OpenAI API anahtarı** yapıştırın → kaydet / test edin.
2. İsterseniz **Suno API** anahtarını girin (yoksa master MP3 yükleyerek devam).
3. Üretim zaman aşımı, yeniden deneme sayısı, paralel proje limiti gibi
   varsayılanları ihtiyaca göre ayarlayın.

Anahtarlar varsayılan olarak bellekte veya şifreli yerel DB’de tutulur;
paylaşım paketinde sizin anahtarınız yoktur.

### Flow oturumu
1. Panelden **Flow’u Aç** / kurulum sihirbazını kullanın.
2. Açılan Chrome’da Google hesabınıza **bir kez elle** giriş yapın.
3. Oturum `chrome-profile/` klasöründe kalır (git’e / zip’e konmaz; her kullanıcı kendi oturumunu açar).
4. Flow arayüzü değişirse **Kalibrasyon** ile Prompt kutusu, Generate, İndir vb.
   seçicileri yeniden öğretin (`/flow-kalibrasyon`).

---

## 5. Ana iş akışı — Çocuk şarkı klibi

### 5.1 Proje oluştur
- Ana sayfa / Çocuk Şarkı listesinden **yeni proje** (hızlı oluştur).
- Proje **Ayarlar**ında mutlaka **kendi Flow proje linkinizi** yazın  
  (Flow’da yeni proje açıp URL’yi kopyalayın).  
  Aynı linki iki iş paylaşırsa klipler karışır.

### 5.2 Ses + söz
Üretim sayfası (`/cocuk-sarki/[id]/render`):
1. Master ses yükleyin **veya** Suno ile üretin.
2. Şarkı sözlerini yapıştırıp kaydedin.
3. **Hazırla** / **prepare-production**: klipleri böler + sahne planı + prompt üretir.

İsteğe bağlı **Oto bitir**: hazırla → kadroyu Flow’da oluştur → otomasyonu başlat.

### 5.3 Karakterler
- Sözden kadro analizi.
- Karakterleri Flow’da oluşturun / referans görselleri onaylayın.
- `@KarakterAdı` referansları promptlarda kullanılır.

### 5.4 Promptlar
- **Tüm promptları oluştur** (veya hazırla zaten yaptı).
- Her prompt **en fazla 8000 karakter** (Flow limiti).
- Stil: 3D animasyon / gerçekçi canlı çekim / sinematik / anime — seçim tüm dünyayı kilitler.
- Ekranda yazı (altyazı/üst yazı) yasaktır; sözler sadece seste + dudak senkronunda.

### 5.5 Otomasyon
1. Flow proje linki dolu olsun, karakterler hazır olsun.
2. **Otomasyonu Başlat**.
3. Bot her klip için: prompt yaz → Generate → bekle → indir → Flow sesini silip
   master dilimini bas → sonraki klip.
4. Hata / takılma durumunda yeniden dener; uzun süre “üretim bekleniyor”da kalmamaya çalışır.
5. Duraklat / devam / iptal kontrolleri panelde.

### 5.6 Render
- Tüm klipler tamamlanınca **Final videoyu oluştur**.
- Çıktı: `projects/<slug>/output/final.mp4` (tam master soundtrack ile).

### 5.7 Yayın (opsiyonel)
- YouTube başlık/açıklama, thumbnail, SRT paketleri.

---

## 6. Önemli kurallar (ürün mantığı)

1. **Tek film sürekliliği** — Klipler ayrı bölüm değil; ~5–10 dk’lık filmin ardışık saniyeleri. Ani yer/konu sıfırlama yok.
2. **Tek ana ses** — Aynı şarkıcı kimliği; `"İsim:"` çoklu diyalog modeli yok.
3. **Ekranda yazı yok** — Altyazı/karaoke/başlık Frame’e basılmaz.
4. **Ses kaynağı master** — Final soundtrack Flow’dan değil, yüklediğiniz / Suno parçanızdan gelir.
5. **Kahraman nesne** — Şarkı “minik balık / domates” gibiyse o nesne lead ile her karede görünür tutulur.
6. **Benzersiz Flow URL** — Her proje ayrı Flow çalışma sayfası.
7. **Sıra** — Söz → klipler → karakterler → promptlar → otomasyon → render.

---

## 7. Sekmeler (kısa)

| Yer | Ne işe yarar |
|-----|----------------|
| Üretim / Klipler | Söz dilimleri, süreler |
| Promptlar | Flow metinleri |
| Karakterler | Kadro + Flow refs |
| Otomasyon | Flow botu |
| Render | Final MP4 |
| Studio / Ayarlar | Flow URL, stil, model |
| Yayın | Meta, thumbnail, SRT |
| Global Ayarlar | API anahtarları, zaman aşımları |
| Flow kalibrasyon | Seçici onarımı |

---

## 8. Geliştiriciler için

```
src/app/                 # Next.js sayfalar + API
src/components/project/  # Üretim UI
src/server/services/     # song, clips, prompt-builder, ffmpeg, suno…
src/server/automation/   # engine, flow-adapter, browser, selectors
src/lib/                 # lyric/hero/stil/8000 kilitleri
prisma/                  # schema + migrations
tests/                   # vitest
```

```powershell
npm test                 # birim testleri
npm run db:studio        # Prisma Studio
```

Ortam değişkenleri: `.env.example` → `.env`  
Gizli dosyalar (zip’e konmaz): `.env`, `chrome-profile/`, `projects/`, `data/`,
`prisma/dev.db*`, `config/.local-encryption-key`

---

## 9. Sık sorunlar

| Sorun | Çözüm |
|-------|--------|
| `ffmpeg bulunamadı` | winget ile kurun, terminali yeniden açın |
| Port 3210 dolu | Eski `node` sürecini kapatın veya `npm run dev` öncesi kontrol edin |
| OpenAI yok / 401 | Ayarlar’dan anahtarı girin |
| Flow giriş bekliyor | Chrome’da Google’a elle giriş |
| Seçici eksik | Flow kalibrasyon |
| İki proje karıştı | Farklı `flowProjectUrl` kullanın |
| Prompt çok uzun | Sistem 8000’e sıkıştırır; yine de stil/SET düşmesin diye yeniden oluşturun |

---

## 10. Lisans / sorumluluk

- Kendi OpenAI / Suno / Google hesaplarınızın kota ve kullanım şartlarına siz uyarsınız.
- Flow arayüzü Google tarafından değiştirilebilir; kalibrasyon gerekebilir.
- Bu paket **anahtarsız** paylaşılmalıdır; `.env` ve `chrome-profile` paylaşmayın.

İyi üretimler!
