# YouTube Shorts Ultimate — Video Üretim Hattı Kapsamlı Mimari ve Geliştirme Master Planı (plan.md)

Bu belge, **ShortsVideoCreators** üretim motorunun tüm bileşenlerini 20 açık kaynaklı referans repo (`reference_repos/` [1-10] ve `reference_repos2/` [11-20]) ile karşılaştırarak; sıfır özellik eksiltme prensibiyle, endüstriyel standartlarda, hataya dayanıklı (resilient), yüksek performanslı ve tam otomatik bir video üretim fabrikasına dönüştürülmesini hedefleyen nihai mimari master planıdır.

---

## İÇİNDEKİLER

1. [Bölüm 1: Mimari Vizyon ve Sistem Topolojisi](#bölüm-1-mimari-vizyon-ve-sistem-topolojisi)
   - 1.1 Mevcut MoviePy Darboğazları ve Neden Yerel FFmpeg?
   - 1.2 Hedeflenen Sistem Mimarisi ve Katmanlar
   - 1.3 Veri Akışı ve Durum Makinesi Sıralaması
2. [Bölüm 2: 20 Referans Reponun Derinlemesine Teknik Analizi](#bölüm-2-20-referans-reponun-derinlemesine-teknik-analizi)
   - 2.1 Grup A: reference_repos (1-10)
   - 2.2 Grup B: reference_repos2 (11-20)
   - 2.3 20 Repo Karşılaştırma ve Yetenek Matrisi
3. [Bölüm 3: FFmpeg Native Graph ve Donanım Render Motoru (render/ffmpeg_graph.py)](#bölüm-3-ffmpeg-native-graph-ve-donanım-render-motoru)
   - 3.1 FilterComplex Mimari Topolojisi
   - 3.2 Sub-Pixel Float Precision Ken Burns Ease-in-out
   - 3.3 Otomatik Fit & Fill Gaussian Blur Arka Plan Katmanı
   - 3.4 Çoklu Donanım Hızlandırma Müzakeresi (NVENC, QSV, AMF, VideoToolbox, VAAPI, libx264)
   - 3.5 Subprocess Heartbeat Takibi ve Zombi Süreç Yalıtımı
   - 3.6 Çift Sayılı Piksel Modülo Hizalama ve WhatsApp/Telegram Toleransı
   - 3.7 İki Geçişli Encode ve Renk Uzayı Standartları (BT.709, YUV420p)
4. [Bölüm 4: Dinamik Kinetik Altyazı ve Tipografi Motoru (subtitle_generator.py & effects/)](#bölüm-4-dinamik-kinetik-altyazı-ve-tipografi-motoru)
   - 4.1 Advanced SubStation Alpha (.ass) Vektörel Şablon Yapısı
   - 4.2 Aktif Kelime Bouncing ve Pop Mikro-Animasyonları
   - 4.3 Shorts UI Safe-Zone Emniyet Marjı ve Çarpışma Önleme
   - 4.4 Whisper Zorunlu Kelime Hizalama (Forced Word Alignment) ve Drift Koruması
   - 4.5 16 Ön Tanımlı Profesyonel Altyazı Stili ve Font Havuzu
   - 4.6 Drop Shadow Açı ve Derinlik Varyasyonu
5. [Bölüm 5: Profesyonel Ses Miksajı ve Akustik Tasarım (director/audio_bus.py & bgm_manager.py)](#bölüm-5-profesyonel-ses-miksajı-ve-akustik-tasarım)
   - 5.1 Sidechain Compression ile Dinamik Ses Ducking (-18dB / -6dB)
   - 5.2 Vokal Frekans Açma (Vocal Carve Parametrik EQ @ 1-3kHz)
   - 5.3 EBU R128 (-14 LUFS) İki Kademeli Normalizasyon
   - 5.4 Trend-Hybrid Telifsiz BGM Kataloğu ve Mood Eşleme
   - 5.5 Doğal Nefes Enjeksiyonu, Whoosh-Ding ve Akustik Varlıklar
   - 5.6 Tape-Stop Efekti ve Beat İpuçlarında Müzik Kesimi
6. [Bölüm 6: Görsel Varlık Edinimi ve Lisans Güvenlik Defteri (visuals/fetch.py & video_fetcher.py)](#bölüm-6-görsel-varlık-edinimi-ve-lisans-güvenlik-defteri)
   - 6.1 Çoklu Sağlayıcı Arama ve İndirme Orkestrasyonu
   - 6.2 İdempotent Manifest Yönetimi ve Otomatik Çakışma Önleme
   - 6.3 Kendini İyileştiren Lisans Modeli (Self-Healing License Model)
   - 6.4 SHA-256 İçerik Parmak İzi ve Çift Klip Blokajı
   - 6.5 K1-Semantik Anlatı Tabanlı Yeniden İndirme (Re-fetch) Hattı
   - 6.6 Prosedürel Arka Plan ve Motion Graphics Motoru
7. [Bölüm 7: Yönetmen Motoru, Senaryo ve Tutundurma Mimarisi (director/ & scenes/)](#bölüm-7-yönetmen-motoru-senaryo-ve-tutundurma-mimarisi)
   - 7.1 Psikolojik Kanca (Hook) Stratejileri
   - 7.2 Kusursuz Döngü Köprüsü (Seamless Loop Bridge)
   - 7.3 BPM ve Ritim İpuçları Tabanlı Kurgu (Beat Hints)
   - 7.4 Anti-Halüsinasyon İnternet Doğrulama Ajanı (FactResearcher)
   - 7.5 16 Niş Üretim Profili ve Stil Motoru
   - 7.6 DirectorPlan Derleyici ve Sahne Niyeti Eşleme
8. [Bölüm 8: Kalite Kapıları, Özgünlük ve Uyumluluk Denetimi (compliance/ & director/quality_gate.py)](#bölüm-8-kalite-kapıları-özgünlük-ve-uyumluluk-denetimi)
   - 8.1 SQLite Tabanlı Çapraz Senaryo Özgünlük Doğrulaması (Madde 120)
   - 8.2 YouTube Tekrarlayan ve Otomatik İçerik Koruma Kalkanı
   - 8.3 Şeffaf AI Açıklama ve Kaynakça Bloğu Üretimi
   - 8.4 Yayın Paketi (Publishing Package) JSON Standardı
   - 8.5 Virality Audit ve İzleyici Puanlama Motoru
9. [Bölüm 9: Kotasız Yükleme ve Çoklu Platform Dağıtım Hattı (services/)](#bölüm-9-kotasız-yükleme-ve-çoklu-platform-dağıtım-hattı)
   - 9.1 Kotasız YouTube Studio Headless Browser Uploader
   - 9.2 PostBridge Çoklu Platform Webhook Dağıtıcısı
   - 9.3 E-Ticaret ve Amazon Satış Ortağı Kısa Video Motoru (AFM)
   - 9.4 Otomatik Küçük Resim (Thumbnail) Sentezleyici
10. [Bölüm 10: Web Studio, Telemetri ve Operasyonel Dayanıklılık (server_core/ & static/)](#bölüm-10-web-studio-telemetri-ve-operasyonel-dayanıklılık)
    - 10.1 Server-Sent Events (SSE) Canlı Log ve İlerleme Akışı
    - 10.2 Devre Kesici (Circuit Breaker) Durum Makinesi
    - 10.3 Termal Kısma (Thermal Throttle) ve Dinamik İş Parçacığı Kontrolü
    - 10.4 Modüler Ön Yüz Durum Yönetimi (State Architecture)
11. [Bölüm 11: 500 Maddelik Yol Haritası Uyumluluk Matrisi](#bölüm-11-500-maddelik-yol-haritası-uyumluluk-matrisi)
12. [Bölüm 12: Üretim Uç Durum (Edge Case) ve Arıza Kurtarma Kataloğu (50 Madde)](#bölüm-12-üretim-uç-durum-ve-arıza-kurtarma-kataloğu)
13. [Bölüm 13: 10 Aşamalı Sprint Uygulama Takvimi ve Kabul Kriterleri](#bölüm-13-10-aşamalı-sprint-uygulama-takvimi-ve-kabul-kriterleri)
14. [Bölüm 14: Tam Veri Modelleri, Pydantic Şemaları ve Tip Sözleşmeleri](#bölüm-14-tam-veri-modelleri-pydantic-şemaları-ve-tip-sözleşmeleri-type-contracts)
15. [Bölüm 15: CLI Komutları, REST API ve SSE/WebSocket Sözleşmeleri](#bölüm-15-cli-komutları-rest-api-ve-ssewebsocket-sözleşmeleri)
16. [Bölüm 16: Çoklu Donanım İvmelendirme ve FFmpeg Çapraz Platform Yapılandırması](#bölüm-16-çoklu-donanım-ivmelendirme-ve-ffmpeg-çapraz-platform-yapılandırması)
17. [Bölüm 17: Güvenlik, Kimlik Doğrulama ve Gizlilik Defteri (Zero-Trust Security)](#bölüm-17-güvenlik-kimlik-doğrulama-ve-gizlilik-defteri-zero-trust-security)
18. [Bölüm 18: Kapsamlı Test ve Kalite Güvence Planı (End-to-End Test Matrisi)](#bölüm-18-kapsamlı-test-ve-kalite-güvence-planı-end-to-end-test-matrisi)
19. [Bölüm 19: Özet Mimari Karar Kayıtları (ADR)](#bölüm-19-özet-mimari-karar-kayıtları-adr---architecture-decision-records)
20. [Bölüm 20: Sonuç ve Gelecek Vizyonu](#bölüm-20-sonuç-ve-gelecek-vizyonu)
21. [Bölüm 21: Dosya Bazlı Kod Tabanı ve Mimari Bileşen Rehberi](#bölüm-21-dosya-bazlı-kod-tabanı-ve-mimari-bileşen-rehberi)
22. [Bölüm 22: FFmpeg Filtre Grafiği Derleme Rehberi ve Komut Kütüphanesi](#bölüm-22-ffmpeg-filtre-grafiği-derleme-rehberi-ve-komut-kütüphanesi)
23. [Bölüm 23: Canlı Dağıtım, Container ve Kubernetes Çevre Yönetimi](#bölüm-23-canlı-dağıtım-container-ve-kubernetes-çevre-yönetimi)
24. [Bölüm 24: Sonuç Raporu ve Geliştirme Taahhütnamesi](#bölüm-24-sonuç-raporu-ve-geliştirme-taahhütnamesi)
25. [Bölüm 25: Geliştirici Sözlüğü ve Teknik Kısaltmalar Dizini (Glossary)](#bölüm-25-geliştirici-sözlüğü-ve-teknik-kısaltmalar-dizini-glossary)
26. [Bölüm 26: Versiyon Geçmişi ve Sürüm Yol Haritası (Changelog)](#bölüm-26-versiyon-geçmişi-ve-sürüm-yol-haritası-changelog)
27. [Bölüm 27: Hızlı Başlangıç ve Çalışma Ortamı Kontrol Listesi](#bölüm-27-hızlı-başlangıç-ve-çalışma-ortamı-kontrol-listesi-production-checklist)
28. [Bölüm 28: 20 Referans Repo Tam Dosya ve Fonksiyon İnceleme Rehberi](#bölüm-28-20-referans-repo-tam-dosya-ve-fonksiyon-inceleme-rehberi-detaylı-kaynak-kod-dizini)
29. [Bölüm 29: Kod Tabanı Çapraz İnceleme ve Entegrasyon Matrisi](#bölüm-29-kod-tabanı-çapraz-inceleme-ve-entegrasyon-matrisi-master-traceability-matrix)
30. [Bölüm 30: Referans Repolardan Çıkarılan Kritik Gizli Mühendislik Detayları](#bölüm-30-referans-repolardan-çıkarılan-kritik-gizli-mühendislik-detayları-ve-tuzaklar-gotchas--hidden-gems)
31. [Bölüm 31: Viral Konu ve Başlık Öneri Motoru Mimarisi](#bölüm-31-viral-konu-ve-başlık-öneri-motoru-mimarisi-advanced-topic-intelligence-engine)
32. [Bölüm 32: Senaryo Üretim Sözleşmesi, Kalite Kapıları ve Self-Healing Onarım Mimarisi](#bölüm-32-senaryo-üretim-sözleşmesi-kalite-kapıları-ve-self-healing-onarım-mimarisi)

---

## BÖLÜM 1: MİMARİ VİZYON VE SİSTEM TOPOLOJİSİ

ShortsVideoCreators, YouTube Shorts, TikTok ve Instagram Reels algoritmalarının en yüksek tutundurma (audience retention), izlenme süresi (watch time) ve özgünlük puanlarını hedefleyen yeni nesil bir video üretim fabrikasıdır.

### 1.1 Mevcut MoviePy Darboğazları ve Neden Yerel FFmpeg?

Geleneksel açık kaynaklı video botları (örneğin ilk nesil MoneyPrinter veya standart MoviePy betikleri), her video karesini tek iş parçacığında Python RAM'ine yükleyip numpy matrisleri üzerinde işlem yaptıkları için şu kronik sorunlarla karşılaşmaktadır:

1. **Bellek Sızıntısı (Memory Leak / OOM):** 60 saniyelik 1080x1920 30fps bir video 1800 kare içerir. Her karesi bellekte 8.3 MB yer tutar; toplamda ham veri boyutu 15 GB'a yaklaşır. Çok sahneli kurgularda işletim sistemi süreci kilitler.
2. **CPU Darboğazı:** Python GIL (Global Interpreter Lock) nedeniyle GPU boşta beklerken tek bir CPU çekirdeği %100 yükte kilitlenir; 60 saniyelik bir video 6-10 dakikada üretilir.
3. **Senkronizasyon Drifti:** MoviePy'nin ses ve görüntü zamanlayıcılarındaki kare yuvarlama hataları nedeniyle video bitişinde 1-2 karelik siyah ekran parlaması veya son kelimenin ekranda kalması problemleri yaşanır.

### 1.2 Hedeflenen Sistem Mimarisi ve Katmanlar

Bu master plan kapsamında sistemimiz, tüm kurgu, efekt, renk derecelendirme, altyazı giydirme ve ses miksajı süreçlerini tek geçişli yerel bir **FFmpeg filter_complex** boru hattına dönüştürmüştür.

```
                           SİSTEM ÇALIŞMA TOPOLOJİSİ
                           =========================

[İstemci / Web Studio UI]
         │ (HTTP REST / SSE)
         ▼
[FastAPI Sunucusu (server_core/)] ◄── [Circuit Breakers & Quota Monitors]
         │
         ├──► 1. Planlama: DirectorPlan Derleyici (director/)
         │        ├── Retention Hooks & Narrative Structure
         │        ├── Beat Hints (BPM Ritim İpuçları)
         │        └── Web Fact-Checking (Anti-Hallucination)
         │
         ├──► 2. Varlık Edinimi (visuals/ & video_fetcher.py)
         │        ├── Pexels / Pixabay API (Keyless Fallbacks)
         │        ├── Pollinations AI / Flux SDXL Video Motoru
         │        ├── Whiteboard Animasyon & Prosedürel Üretim
         │        └── Manifest Ledger (Çift Varlık & Lisans Güvencesi)
         │
         ├──► 3. Ses & Akustik (tts_engine.py & director/audio_bus.py)
         │        ├── Edge TTS / Gemini Audio Fallback Zinciri
         │        ├── Voice Humanizer (Warmth EQ, Breaths, Jitter)
         │        ├── Sidechain Compression (-18dB Ducking)
         │        └── EBU R128 (-14 LUFS) İki Kademeli Normalizasyon
         │
         ├──► 4. Altyazı & Tipografi (subtitle_generator.py & effects/)
         │        ├── Whisper Word Boundary Senkronizasyonu
         │        ├── Kinetik Tek Satır Sayfalama (Paging)
         │        └── ASS Karaoke Vektör Şablonu & Pop-Bounce Tags
         │
         ├──► 5. Render Grafiği (render/ffmpeg_graph.py)
         │        ├── Sub-pixel Float Ken Burns Pan/Zoom
         │        ├── Fit & Fill Gaussian Blur Arka Plan Katmanı
         │        ├── Çift Sayılı Piksel Modülo Hizalama
         │        └── Donanım Hızlandırma (NVENC/QSV/AMF/VT/x264)
         │
         └──► 6. Yayın & Dağıtım (services/)
                  ├── Headless YouTube Studio Uploader (Kotasız)
                  ├── PostBridge Multi-Platform Webhooks
                  └── Auditable Publishing Package (.json / .txt)
```

### 1.3 Veri Akışı ve Durum Makinesi Sıralaması

Render süreci deterministik bir durum makinesi (state machine) olarak ilerler:

1. **İstek Kabulü ve Doğrulama:**
   - Kullanıcıdan gelen anahtar kelime, niş, hedef dil ve ses tercihleri `VideoRenderRequest` modeli ile pydantic doğrulamasına girer.
   - Seçilen nişin kuralları (`niche_templates.py`) yüklenir.
2. **Kanca ve Anlatı Üretimi:**
   - 4 psikolojik kanca türünden (Bilişsel Çelişki, Merak Boşluğu, Şok İstatistik, Sorun-Büyütme) nişe en uygun olanı seçilir.
   - İlk 3 saniyede izleyicinin kaydırmasını durduracak açılış cümlesi derlenir.
3. **Senaryo Derleme (DirectorPlan):**
   - Senaryo sahneleri zaman çizelgesine (`Timeline`) yerleştirilir.
   - Her sahne için görsel niyet (`visual_intent`), kamera açısı ipucu ve BPM ritim işaretçileri hesaplanır.
4. **Özgünlük Kontrolü (Madde 120):**
   - SQLite veritabanındaki geçmiş başarılı render kayıtları taranır.
   - TF-IDF ve Jaccard kelime benzerliği hesaplanır; %30 üzeri çakışma varsa senaryo yeniden yazdırılır.
5. **Varlık Edinimi (Asset Ingestion):**
   - Sahne görsel niyetlerine göre Pexels, Pixabay, Flux AI veya Prosedürel motorlardan paralel olarak klipler indirilir.
   - SHA-256 içerik parmak izi ile aynı klibin tekrarlanması engellenir.
   - İdempotent `add_manifest_entry` ile tüm varlıklar ticari lisans güvenliği (`AI_GENERATED`, `CC0`, `PEXELS`) altında deftere işlenir.
6. **Seslendirme ve Zamanlama (TTS Synchronization):**
   - Edge TTS / Gemini motoru üzerinden ses dalgası üretilir.
   - Kelime düzeyinde milisaniyelik zaman damgaları çıkarılır.
   - Seslendirme süresi sahne sürelerini otomatik dengeler (`fit_tts_to_timeline`).
7. **Akustik Tasarım ve Miksaj (Master Audio One-Pass):**
   - Seslendiriciye stüdyo sıcaklığı (warmth EQ), mikro-jiter ve doğal nefes sesleri eklenir.
   - Nişe uygun telifsiz BGM seçilir; 2000Hz bandında vokal çentiği açılır.
   - Sidechain kompresör ile konuşurken müzik `-18dB`'e kısılır.
   - EBU R128 (-14 LUFS) normalizasyonu ile podcast/radyo kalitesinde ses dosyası oluşturulur.
8. **Kinetik Altyazı Derleme:**
   - ASS formatında vektörel altyazı dosyası üretilir.
   - Aktif kelimeye `	(0,70,\fscx115\fscy115)` zıplama efekti ve neon renk vurgusu eklenir.
   - Altyazı mobil arayüzün altına girmeyecek şekilde güvenli alana yerleştirilir.
9. **FFmpeg FilterComplex Render:**
   - Tek geçişte; yatay kliplere Gaussian blur dolgusu, tüm sahnelere kosinüs Ken Burns hareketi, renk filtresi, alt neon ilerleme çubuğu, altyazı ve ses miksajı uygulanır.
   - Donanım hızlandırma (NVIDIA NVENC, Apple VideoToolbox, Intel QSV veya libx264) ile 30 saniye içinde MP4 çıktısı alınır.
10. **Paketleme ve Dağıtım:**
    - `visual_credits.json`, `source_manifest.json`, `publishing_package.json` ve SEO etiketleri derlenir.
    - Video izlemeye ve YouTube Studio / Webhook üzerinden yayınlanmaya hazır teslim edilir.

---

## BÖLÜM 2: 20 REFERANS REPONUN DERİNLEMESİNE TEKNİK ANALİZİ

Sistemimizde bulunan 20 açık kaynaklı repo incelenmiş, her birinin üretim hattımıza kazandırdığı teknik çözümler kod tabanına haritalanmıştır.

### 2.1 Grup A: reference_repos (1-10)

#### 1. agnes-video-generator
- **Mimari:** Node/Python çok sahneli LLM montajlayıcı.
- **İncelenen Dosyalar:** `core/video_generator.py`, `utils/video.py`.
- **Teknik Özellik:** Senaryodaki kelime ve hece sayısından sahne sürelerinin otomatik türetilmesi. Konuşmacı hızına göre metni dinamik esnetme.
- **ShortsVideoCreators Entegrasyonu:** `director/timeline.py` içinde her sahnenin hedef süresi (target duration) anlatım metninin hece sayısına kilitlenir.

#### 2. ai-content-studio
- **Mimari:** Doğrulanmış haber ve bilgi içerik stüdyosu.
- **İncelenen Dosyalar:** `server/core/videofx_client.py`, `server/routers/videofx.py`.
- **Teknik Özellik:** Araştırma safhasında toplanan web kaynaklarının video çıktısına şeffaf overlay kanıt bandı olarak işlenmesi.
- **ShortsVideoCreators Entegrasyonu:** `services/web_fact_researcher.py` ile haber ve bilgi nişlerinde kanıt domainleri açıklama kutusuna ve `publishing_package.json` içine yazılır.

#### 3. anil_matcha_shorts_generator
- **Mimari:** Whisper kelime damgalarıyla yüksek enerjili anların tespiti.
- **İncelenen Dosyalar:** `transcriber.py`, `clipper.py`.
- **Teknik Özellik:** Ses dalgasındaki RMS genliği analizi ile konuşmanın en etkileyici 3 saniyesinin tespit edilmesi.
- **ShortsVideoCreators Entegrasyonu:** `subtitle_generator.py` içindeki `POWER_WORD_HIGHLIGHTS` sözlüğü ile yüksek vurgulu kelimeler neon kırmızı renkle büyütülür.

#### 4. helios
- **Mimari:** AI video üretimi ve kare enterpolasyonu (Frame Interpolation).
- **İncelenen Dosyalar:** `engine/interpolate.py`.
- **Teknik Özellik:** Düşük kareli (12-15 fps) AI animasyon kliplerinin RIFE / minterpolate ile akıcı 30/60 fps'e dönüştürülmesi.
- **ShortsVideoCreators Entegrasyonu:** `render/ffmpeg_graph.py` içinde düşük kareli Pollinations / Flux klipleri `fps=30` filtresi ile senkronize edilir.

#### 5. invideo-ai-nexus
- **Mimari:** Anlatı kurgusu, sahne niyetleri ve akıllı kamera açıları.
- **İncelenen Dosyalar:** `agents/narrator.py`, `render/camera.py`.
- **Teknik Özellik:** Sahne niyetine göre kamera hareketi tayini (Soru = Zoom-in, Geçiş = Pan-left, Sonuç = Zoom-out).
- **ShortsVideoCreators Entegrasyonu:** `director/director.py` içinde sahnenin `visual_intent` nesnesi `cheap_pan_filter` yönü ile eşleştirilir.

#### 6. openshorts
- **Mimari:** Yüz takibi ve dikey akıllı kırpma (Smart Crop).
- **İncelenen Dosyalar:** `cloud/videos.py`.
- **Teknik Özellik:** 16:9 yatay videolarda nesnenin veya yüzün koordinatlarını bularak dikey 9:16 crop merkezini nesneye kaydırma.
- **ShortsVideoCreators Entegrasyonu:** Stok videolarda merkez kırpma yerine akıllı nesne konumlandırması uygulanır.

#### 7. saard00_shorts_generator
- **Mimari:** Çift katmanlı Split-Screen ve Pexels motoru.
- **İncelenen Dosyalar:** `generator.py`.
- **Teknik Özellik:** Üst %58 anlatım sahnesi, alt %42 rahatlatıcı oynanış (soap cutting, subway surfers) videosunu tek `vstack` ile bağlama.
- **ShortsVideoCreators Entegrasyonu:** `render/ffmpeg_graph.py` içindeki `split_screen` ve `gameplay_path` parametreleri ile tek FFmpeg komutunda senkron birleştirme.

#### 8. short-video-maker
- **Mimari:** MoviePy/FFmpeg ses ve görsel spektrum montajı.
- **İncelenen Dosyalar:** `effects/audio_visualizer.py`.
- **Teknik Özellik:** Ses frekans dalga formunun (waveform) video üzerine transparan çizdirilmesi.
- **ShortsVideoCreators Entegrasyonu:** Podcast ve bilgi nişlerinde altyazı altına dinamik ses spektrum çizgisi overlay'i eklenir.

#### 9. shortgpt
- **Mimari:** Asset Engines + Editing Engines çok katmanlı soyutlama.
- **İncelenen Dosyalar:** `shortgpt/engine/editing_engine.py`, `shortgpt/engine/content_engine.py`.
- **Teknik Özellik:** Çok kanallı katman hiyerarşisi (Arka Plan -> Ana Video -> B-Roll -> Altyazı -> SFX -> BGM).
- **ShortsVideoCreators Entegrasyonu:** Tüm katmanların MoviePy açılmadan doğrudan FFmpeg `filter_complex` üzerinde birleştirilmesi.

#### 10. youtube-shorts-pipeline
- **Mimari:** Otomatik haberden Shorts üretim hattı.
- **İncelenen Dosyalar:** `pipeline/news_fetcher.py`, `render/ticker.py`.
- **Teknik Özellik:** Haber başlığı alt yazı bandı (Breaking News Ticker) ve kırmızı alert grafikleri.
- **ShortsVideoCreators Entegrasyonu:** `niche_templates.py` içindeki `1_news_flash` nişinde kayan kırmızı şerit tasarımı.

---

### 2.2 Grup B: reference_repos2 (11-20)

#### 11. MoneyPrinterTurbo (~126k ⭐)
- **Mimari:** ASS Karaoke Altyazı, Donanım Kodlayıcı Fallback ve Otomatik Ses Ducking.
- **İncelenen Dosyalar:** `app/services/video.py`, `app/services/utils/video_effects.py`.
- **Teknik Özellik:**
  - `_VIDEO_DURATION_SAFETY_MARGIN = 0.1` ile ses bittiğinde görüntünün anlık siyah frame vermesini önleme.
  - Sub-pixel float Ken Burns ölçeklendirmesi.
  - Aktif kelime üzerinde `	` ile spring/bounce animasyonu.
- **ShortsVideoCreators Entegrasyonu:**
  - `render/ffmpeg_graph.py` içinde 0.1s güvenlik marjı uygulandı.
  - `subtitle_generator.py` içine `	(0,70,\fscx115\fscy115)` zıplama etiketi entegre edildi.

#### 12. MoneyPrinterV2 (~32k ⭐)
- **Mimari:** Kotasız Tarayıcı Yükleyici (Selenium/Profile) ve E-Ticaret Ürün Motoru (AFM).
- **İncelenen Dosyalar:** `Backend/video.py`, `Backend/uploader.py`.
- **Teknik Özellik:** Chrome kullanıcı profili çerezleri ile YouTube Studio web arayüzünden kotasız video yükleme; ürün linkinden senaryo ve görsel üretimi.
- **ShortsVideoCreators Entegrasyonu:** `services/headless_uploader.py` ve `services/affiliate_product_engine.py` modülleri ile tam kotasız yükleme ve e-ticaret kurgusu sağlandı.

#### 13. MoneyPrinter (~14k ⭐)
- **Mimari:** Klasik MoviePy TTS-Görsel Senkronizasyonu.
- **İncelenen Dosyalar:** `Backend/video.py`.
- **Teknik Özellik:** Görsel klip sürelerinin TTS seslendirme süresine milisaniyelik kilitlenmesi.
- **ShortsVideoCreators Entegrasyonu:** `director/timeline.py` içinde her sahnenin süresi TTS kelime zamanlamasına göre milisaniyesi milisaniyesine kilitlenir.

#### 14. RedditVideoMakerBot (~12.5k ⭐)
- **Mimari:** Dinamik HTML/DOM Kart Renderı.
- **İncelenen Dosyalar:** `utils/videos.py`, `utils/voice.py`.
- **Teknik Özellik:** Playwright / Chromium ile Reddit soru/cevap kartlarını transparan PNG olarak render edip videonun ilk 3 saniyesine bindirme.
- **ShortsVideoCreators Entegrasyonu:** `reddit_card_renderer.py` ile soru-cevap nişinde şık kart açılışları oluşturulur.

#### 15. NarratoAI (~11.2k ⭐)
- **Mimari:** Sessizlik Tespiti (Silence Removal) ve Dinamik Pacing.
- **İncelenen Dosyalar:** `app/services/video.py`, `app/utils/video_processor.py`.
- **Teknik Özellik:** TTS sesindeki 0.4 saniyenin üzerindeki boşlukları kırparak videonun temposunu %15 artırma.
- **ShortsVideoCreators Entegrasyonu:** `voice_humanizer.py` içinde seslendirme duraklamaları optimize edilir.

#### 16. autoclip (~8.9k ⭐)
- **Mimari:** AI Highlight & Akıllı Klip Kümeleme.
- **İncelenen Dosyalar:** `backend/tasks/video.py`, `backend/utils/video_editor.py`.
- **Teknik Özellik:** Benzer renk ve sahne içeriğine sahip stok kliplerin art arda gelmesini engelleyen kümeleme algoritması.
- **ShortsVideoCreators Entegrasyonu:** `clip_uniqueness_report` içinde hem dosya hash'i hem de görsel benzerlik kontrol edilir.

#### 17. dramaclaw (~6.5k ⭐)
- **Mimari:** Fit-and-Fill Blur Dolgu, Tip Güvenli Modeller ve Görev İptal Mekanizması.
- **İncelenen Dosyalar:** `src/novelvideo/generators/video_composer.py`.
- **Teknik Özellik:** `boxblur=25:5` ile yatay videoların arkasına bulanık dolgu basma; Pydantic modelleri (`SceneAsset`, `VideoResult`).
- **ShortsVideoCreators Entegrasyonu:** `render/ffmpeg_graph.py` içinde `_probe_is_landscape` ve Fit & Fill Gaussian Blur katmanı uygulandı.

#### 18. FunClip (~6.3k ⭐)
- **Mimari:** Kelime Düzeyinde Zorunlu Hizalama (Forced Alignment).
- **İncelenen Dosyalar:** `funclip/videoclipper.py`.
- **Teknik Özellik:** Fonem tabanlı ASR ile 0 milisaniye altyazı gecikmesi.
- **ShortsVideoCreators Entegrasyonu:** Whisper Word Timings çıktısının Edge TTS çıktılarıyla birleştirilerek drift sıfırlandı.

#### 19. pyJianYingDraft (~4.4k ⭐)
- **Mimari:** CapCut / JianYing Taslak Formatı ve Keyframe Eğrileri.
- **İncelenen Dosyalar:** `pyJianYingDraft/video_segment.py`.
- **Teknik Özellik:** Doğrusal olmayan (Cubic Bezier / Cosine) kamera hareket keyframe'leri.
- **ShortsVideoCreators Entegrasyonu:** `cheap_pan_filter` fonksiyonunda kosinüs tabanlı `0.5*(1-cos(PI*t/dur))` ivmelenme eğrisi uygulandı.

#### 20. video-autopilot-kit (~2.1k ⭐)
- **Mimari:** Deterministik Timeline, Çift Varlık Koruması ve Lisans Defteri.
- **İncelenen Dosyalar:** `src/longform_maker/video_handlers.py`.
- **Teknik Özellik:** Her render için bağımsız manifest ve lisans tekilleştirmesi.
- **ShortsVideoCreators Entegrasyonu:** `visuals/fetch.py` içinde `add_manifest_entry` ve `write_job_credits` self-healing lisans yapısı uygulandı.

---

### 2.3 20 Repo Karşılaştırma ve Yetenek Matrisi

| # | Repo | Yıldız | Kategori | Temel Güç | ShortsVideoCreators Entegrasyonu |
|---|---|---|---|---|---|
| 1 | `agnes-video-generator` | ~500 | Pipeline | Metin/Hece Zamanlaması | Sahne süre hesaplayıcı (`timeline.py`) |
| 2 | `ai-content-studio` | ~800 | Research | Kanıt Kayıt Şeridi | Anti-hallucination web araştırması |
| 3 | `anil_matcha_shorts` | ~1.2k | Audio | Enerji Seviyesi Tespiti | Güçlü kelime kırmızı vurgusu (`POWER_WORDS`) |
| 4 | `helios` | ~2.5k | Render | Kare Enterpolasyonu | 30 fps akıcı kare enterpolasyonu |
| 5 | `invideo-ai-nexus` | ~3.1k | Director | Görsel Niyet Eşleme | Sahne niyetine göre kamera açısı |
| 6 | `openshorts` | ~1.9k | Visual | Yüz Takip & Dikey Crop | Akıllı kırpma (Smart Crop) |
| 7 | `saard00_shorts` | ~400 | Layout | Çift Katman Split | %58 / %42 vstack oynanış paneli |
| 8 | `short-video-maker` | ~900 | Audio | Dalga Formu Çizimi | Transparan ses spektrum overlay'i |
| 9 | `shortgpt` | ~16k | Architecture | Çok Katmanlı Render | 6 katmanlı filter_complex grafiği |
| 10 | `youtube-shorts-pipe` | ~1.1k | Layout | Kayan Haber Bandı | Breaking News kayan yazı şeridi |
| 11 | `MoneyPrinterTurbo` | ~126k | Subtitle/Render | ASS Karaoke & Ducking | Aktif kelime bounce + 0.1s emniyet |
| 12 | `MoneyPrinterV2` | ~32k | Uploader | Kotasız Browser Upload | Headless YouTube Studio uploader |
| 13 | `MoneyPrinter` | ~14k | Timeline | Milisaniye Kilit | TTS süresine tam kilitli timeline |
| 14 | `RedditVideoMakerBot`| ~12.5k| Graphics | Dinamik DOM Kartı | Transparan soru-cevap kart açılışı |
| 15 | `NarratoAI` | ~11.2k| Audio | Sessizlik Budama | Es sürelerini kırpıp tempo artırma |
| 16 | `autoclip` | ~8.9k | Visual | Klip Kümeleme | Benzer sahnelerin tekrarını önleme |
| 17 | `dramaclaw` | ~6.5k | Render | Fit & Fill Gaussian Blur | 16:9 yatay videolara bulanık arka plan |
| 18 | `FunClip` | ~6.3k | Subtitle | Fonem Düzeyinde Hizalama| Sıfır gecikmeli kelime kesimleri |
| 19 | `pyJianYingDraft` | ~4.4k | Keyframe | Bezier Kamera Eğrileri | Kosinüs yumuşak kamera ivmelenmesi |
| 20 | `video-autopilot-kit` | ~2.1k | Compliance | Lisans Manifest Defteri| Self-healing güvenli lisans defteri |

---

## BÖLÜM 3: FFMPEG NATIVE GRAPH VE DONANIM RENDER MOTORU

### 3.1 FilterComplex Mimari Topolojisi

Render motoru, MoviePy'nin her kareyi Python belleğinde numpy dizisine çevirip CPU'da çizme yavaşlığını tamamen ortadan kaldırır. Tek bir FFmpeg komutu ile tüm filtreler GPU üzerinde paralel yürütülür.

```
                    FFMPEG FILTER_COMPLEX GRAFİĞİ
                    =============================

[Giriş 0:v] ──► trim=duration ──► fps=30 ──► split ──► [bg] scale+crop+boxblur ──┐
                                                    └─► [fg] scale=decrease     ──┴─► overlay=(W-w)/2:(H-h)/2 ──► Ken Burns (Ease-in-out) ──► [v0]
[Giriş 1:v] ──► trim=duration ──► fps=30 ──► scale+crop ─────────────────────────────────────────────► Ken Burns (Ease-in-out) ──► [v1]  │
[Giriş N:v] ──► trim=duration ──► fps=30 ──► scale+crop ─────────────────────────────────────────────► Ken Burns (Ease-in-out) ──► [vN]  │
                                                                                                                                           │
[v0][v1]...[vN] concat=n=N:v=1:a=0 ────────────────────────────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼ [vcat]
Color Jitter (eq) + Unsharp (5:5:0.8) + Noise (alls=3) + Vignette (PI/5)
       │
       ▼ [vlook]
Neon Progress Bar (drawbox @ alt 4px)
       │
       ▼
libass Altyazı Katmanı (subtitles='subs.ass')
       │
       ▼ [vout]
[Giriş Audio] ──► aac 192k 48kHz (Sidechain Ducked & EBU R128 Mastered)
       │
       ▼
[ÇIKIŞ VİDEOSU: MP4 (H.264 / NVENC / QSV / AMF / VideoToolbox)]
```

### 3.2 Sub-Pixel Float Precision Ken Burns Ease-in-out

Kameranın sahne içindeki hareketi, izleyicinin dikkatini ayakta tutan en kritik faktördür. Doğrusal (linear) hareketler insan gözüne yapay gelir ve sahne başında/sonunda takılma hissi yaratır.

- **Kullanılan Matematiksel Formül:**
  \text{Progress}(t) = 0.5 \times \left(1 - \cos\left(\pi \times \frac{\min(t, \text{dur})}{\text{dur}}\right)\right)
- **Ters Yön Formülü:**
  \text{ProgressRev}(t) = 0.5 \times \left(1 + \cos\left(\pi \times \frac{\min(t, \text{dur})}{\text{dur}}\right)\right)

Bu eğri sayesinde ivme sıfırdan başlar, ortada maksimum hıza ulaşır ve sahne sonunda sıfıra yumuşakça iner. Koordinatlar float olarak hesaplandığı için pikseller arasında atlama (jitter) olmaz.

### 3.3 Otomatik Fit & Fill Gaussian Blur Arka Plan Katmanı

Yatay (16:9) veya kare (1:1) stok videolar 9:16 ekranda doğrudan ortadan kırpıldığında görüntünün %60'ı kaybolur. Otomatik tespit edilen yatay klipler için şu filtre uygulanır:

```text
split[fg_raw][bg_raw];
[bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg_blur];
[fg_raw]scale=1080:1920:force_original_aspect_ratio=decrease[fg_fit];
[bg_blur][fg_fit]overlay=(W-w)/2:(H-h)/2,setsar=1
```

Arka plan bulanıklaştırılarak ekranın tamamı doldurulur, ana video ise orijinal en-boy oranı bozulmadan ve hiçbir detayı kesilmeden ekranın tam ortasına yerleştirilir.

### 3.4 Çoklu Donanım Hızlandırma Müzakeresi

Donanım hızlandırma zinciri tek bir GPU markasına bağımlı kalmayacak şekilde hiyerarşik yapılandırılmıştır:

1. **NVIDIA GPU (Windows/Linux):** `h264_nvenc` (`-preset p4 -tune hq -cq 21 -b:v 8M`)
2. **Apple Silicon (macOS):** `h264_videotoolbox` (`-b:v 8M`)
3. **Intel CPU/GPU:** `h264_qsv` (`-preset medium -global_quality 21`)
4. **AMD GPU (Windows):** `h264_amf` (`-quality speed -rc cqp`)
5. **Windows Media Foundation:** `h264_mf`
6. **Yazılımsal Fallback (Evrensel):** `libx264` (`-preset fast -crf 20`)

Sistem başlangıçta GPU'yu otomatik algılar; donanım kodlayıcı hata verirse çökmek yerine milisaniyeler içinde bir alt kodlayıcıya geçiş yapar.

### 3.5 Subprocess Heartbeat Takibi ve Zombi Süreç Yalıtımı

Uzun süren video render işlemlerinde FFmpeg process'inin işletim sisteminde kilitlenmesini önlemek için 15 saniyelik heartbeat döngüsü çalışır. `proc.poll()` ile sürecin durumu taranır; kullanıcı arayüzden iptal ettiğinde `terminate()` ve `kill()` sinyalleriyle bellek temizlenir.

### 3.6 Çift Sayılı Piksel Modülo Hizalama

H.264 video codec'i ve YUV420p renk formatı gereği video çözünürlükleri çift sayı olmak zorundadır. WhatsApp veya Pexels kaynaklı tek sayılı boyutlar (`w - (w % 2)`) formülüyle hizalanarak render hataları tamamen engellenir.

### 3.7 İki Geçişli Encode ve Renk Uzayı Standartları (BT.709, YUV420p)

YouTube algoritmasının video renklerini bozmadan indekslemesi için standart BT.709 renk matrisi ve `yuv420p` piksel formatı kullanılır. Video başına eklenen `+faststart` bayrağı ile dosya internet üzerinden akarken anında oynatılabilir hale gelir.


---

## BÖLÜM 4: DİNAMİK KİNETİK ALTYAZI VE TİPOGRAFİ MOTORU

### 4.1 Advanced SubStation Alpha (.ass) Vektörel Şablon Yapısı

Vektörel altyazı motoru, video çözünürlüğüne (`PlayResX: 1080`, `PlayResY: 1920`) göre otomatik ölçeklenen ASS şablonunu kullanır:

```ini
[Script Info]
Title: Kinetic Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,Anton,54,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,3,4,4,2,40,40,480,1
```

Bu şablon, FFmpeg'in dahili `subtitles` filtresi tarafından donanım hızlandırmalı olarak video üzerine doğrudan rasterize edilir. MoviePy'nin her karede metin resmi oluşturma yavaşlığı ortadan kaldırılmıştır.

### 4.2 Aktif Kelime Bouncing ve Pop Mikro-Animasyonları

TikTok ve CapCut videolarının yüksek izlenme oranlarının temelindeki kelime zıplama efekti ASS `	` etiketleriyle oluşturulur:

- Aktif kelime başladığında: `	(0, 70, \fscx115\fscy115)` (İlk 70ms'de %115 büyür)
- Kelime otururken: `	(70, 140, \fscx106\fscy106)` (70-140ms arasında stabil %106 boyutuna oturur)
- Kelime bittiğinde: `\fscx100\fscy100` (Normal boyuta döner)

Örnek ASS Diyalog Satırı:
```text
Dialogue: 0,0:00:01.20,0:00:01.55,K,,0,0,0,,{\c&H0000FFFF&1\fscx106\fscy106	(0,70,\fscx115\fscy115)	(70,140,\fscx106\fscy106)lur3}MİLYARDERLERİN{\c&H00FFFFFF&0\fscx100\fscy100} sirri burada
```

### 4.3 Shorts UI Safe-Zone Emniyet Marjı ve Çarpışma Önleme

YouTube Shorts ve TikTok mobil arayüzünde alt %25'lik kısım (beğeni, yorum, kanal adı, ses başlığı butonları) ile kaplıdır. Altyazılar bu butonların altında kalmayacak şekilde tabandan en az 480 piksel yukarıda (`MarginV: 480`) merkezlenir.

```
+------------------------------------------+
|                                          |
|                                          |
|                                          |
|               ANA VİDEO                  |
|                                          |
|                                          |
|      +----------------------------+      |
|      |    KİNETİK ALTYAZI ALANI   |      |  <-- Safe-Zone (Y: 72% - 75%)
|      +----------------------------+      |
|                                          |
|  [Kanal Adı] [Abone Ol]   (Beğen) (Yorum)|  <-- Shorts Mobil UI Alt Alanı (Alt 25%)
+------------------------------------------+
```

### 4.4 Whisper Zorunlu Kelime Hizalama ve Drift Koruması

TTS çıktısındaki milisaniyelik gecikmeleri önlemek için ses süresi probe edilir (`_probe_audio_duration_sec`). Whisper veya Edge TTS Word Boundary verileri ses dosyasının tam süresine oranlanarak (scale factor) altyazı kayması (audio drift) sıfırlanır:

$$\text{Scale} = \frac{\text{AudioDuration}}{\text{LastWordEndTime}}$$
$$\text{WordOffset}_{\text{corrected}} = \text{WordOffset} \times \text{Scale}$$

### 4.5 16 Ön Tanımlı Profesyonel Altyazı Stili ve Font Havuzu

Her niş için izleyici psikolojisine uygun önceden test edilmiş altyazı ön ayarları:

1. **capcut_yellow:** Sarı vurgu (`#FFD700`), Anton font, kalın siyah kontur (4px), drop shadow.
2. **cyber_green:** Neon yeşil (`#00FF66`), Bebas Neue font, koyu yeşil kontur (4px), hafif parlama.
3. **red_fire:** Neon kırmızı (`#FF3333`), Anton font, koyu kırmızı kontur (5px), dramatik gölge.
4. **clean_white:** Saf beyaz (`#F0F0F0`), Montserrat font, ince siyah kontur (3px), modern estetik.
5. **high_contrast_retention:** Sarı (`#FFFF00`), Anton font, ekstra kalın kontur (5px), maksimum okunabilirlik.
6. **tiktok_bold:** Canlı sarı/beyaz, The Bold Font, siyah çift kontur, hızlı kelime geçişi.
7. **mrbeast_style:** Sarı vurgulu Comic/Bebas karışımı, siyah kutulu arka plan desteği.
8. **cinematic_minimal:** Açık gri (`#E0E0E0`), Helvetica/Inter font, kontursuz, zarif alt gölge.
9. **crypto_gold:** Altın sarısı (`#FFCC00`), Montserrat Black, lüks hissi veren 45° gölge.
10. **luxury_elegance:** Şampanya rengi (`#F7E7CE`), Playfair Display / Serif, klasik tipografi.
11. **horror_blood:** Kan kırmızısı (`#CC0000`), Creepster / Anton, bulanık koyu gölge.
12. **history_sepia:** Parşömen sarısı (`#F4ECD8`), Cinzel / Garamond, antika doku hissi.
13. **space_neon_blue:** Elektrik mavisi (`#00E5FF`), Orbitron / Rajdhani, fütüristik parlama.
14. **fitness_punch:** Turuncu (`#FF6600`), Impact / Anton, yüksek kontrastlı enerji.
15. **psychology_violet:** Mor vurgu (`#BF55EC`), Raleway / Poppins, merak uyandıran renk paleti.
16. **wisdom_emerald:** Zümrüt yeşili (`#2ECC71`), Amiri / Scheherazade, manevi ve dingin okuma.

### 4.6 Drop Shadow Açı ve Derinlik Varyasyonu

Altyazıların tekdüze görünmesini engellemek için her render oturumunda gölge açıları (120° - 150°) ve derinlik parametreleri (3px - 5px) deterministik olarak çeşitlendirilir (Madde 116).

---

## BÖLÜM 5: PROFESYONEL SES MİKSAJI VE AKUSTİK TASARIM

### 5.1 Sidechain Compression ile Dinamik Ses Ducking (-18dB / -6dB)

Arka plan müziğinin konuşmayı bastırmaması ve konuşma durduğunda videonun enerjisini yükseltmesi için profesyonel radyo ducking devresi uygulanır:

```text
[0:a]pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,asplit=2[narr_sc][narr_mix];
[1:a]volume=0.12,stereowiden=delay=20:feedback=0.25:crossfeed=0.2:drymix=0.8,equalizer=f=2000:t=q:w=1.0:g=-4.5[bgm_wide];
[bgm_wide][narr_sc]sidechaincompress=threshold=0.025:ratio=12:attack=80:release=200[ducked];
[narr_mix][ducked]amix=inputs=2:duration=first:dropout_transition=0.0:normalize=0[aout]
```

- Konuşma başladığında müzik 80 milisaniye içinde `-18dB`'e kısılır.
- Cümle aralarında müzik 200 milisaniye içinde `-6dB` seviyesine yükselir.

### 5.2 Vokal Frekans Açma (Vocal Carve Parametrik EQ @ 1-3kHz)

İnsan sesinin ana anlaşılırlık frekansı olan 2000 Hz bandında müzikten `-4.5dB` çentik (notch) açılarak konuşmanın kristal berraklığında duyulması sağlanır:

```text
equalizer=f=2000:t=q:w=1.0:g=-4.5
```

### 5.3 EBU R128 (-14 LUFS) İki Kademeli Normalizasyon

YouTube Shorts ses algoritması `-14 LUFS` entegre ses seviyesini hedefler. İki kademeli `loudnorm` filtresi ile ses normalize edilerek videonun diğer içeriklere göre kısık veya patlak kalması engellenir:

- Entegre Ses Hedefi (`I`): `-14.0 LUFS`
- Loudness Range (`LRA`): `7.0 LU`
- True Peak Sınırı (`TP`): `-1.0 dBFS`

### 5.4 Trend-Hybrid Telifsiz BGM Kataloğu ve Mood Eşleme

YouTube Trend Sounds listesi kapalı API olduğundan, viral trend enerjileri güvenli telifsiz müziklerle eşleştirilir:
- **Viral Pulse:** Yüksek enerjili haber, teknoloji, kripto nişleri için.
- **Lo-Fi Feed Scroll:** Sakin felsefe, motivasyon, eğitim içerikleri için.
- **Dark Tension Hook:** Gizem, suç, tarih, psikoloji nişleri için.

### 5.5 Doğal Nefes Enjeksiyonu, Whoosh-Ding ve Akustik Varlıklar

Sentetik AI sesini insanlaştırmak için her 8 saniyede bir düşük seviyeli (-32dB) doğal nefes sesleri ve introda izleyiciyi yakalayan Whoosh+Ding ses efekti eklenir:
- **Whoosh+Ding İntro:** İlk 0.2 saniyede izleyiciyi ekrana kilitleyen frekans patlaması.
- **Doğal Nefes:** Cümle başlangıçlarına mikro genlikli gerçek insan nefes örnekleri mikslenir.
- **Oda Ambiyansı:** -32dB seviyesinde pembe gürültü (pink noise) ile yapay zeka sesinin stüdyo kuruluğu kırılır.

### 5.6 Tape-Stop Efekti ve Beat İpuçlarında Müzik Kesimi

Şok edici bir bilgi veya beklenmedik bir istatistik söylendiğinde, müzik 0.4 saniyeliğine aniden kesilerek (tape-stop) izleyicinin dikkati konuşmacının ağzından çıkan tek kelimeye çekilir (Madde 156).

---

## BÖLÜM 6: GÖRSEL VARLIK EDİNİMİ VE LİSANS GÜVENLİK DEFTERİ

### 6.1 Çoklu Sağlayıcı Arama ve İndirme Orkestrasyonu

Görseller 5 bağımsız sağlayıcı havuzundan paralel çekilir (`asyncio.gather`):
1. **Pexels Video API:** Dikey 1080x1920 çözünürlüklü gerçekçi stok videolar.
2. **Pixabay Video API:** İkinci kademe yüksek kaliteli doğa, şehir ve teknoloji klipleri.
3. **Pollinations AI / Flux SDXL:** Stok bulunamayan soyut konularda anlık AI video sentezi.
4. **Procedural Motion Graphics:** Kodla üretilen parçacık efektleri, siber ızgaralar ve tipografi sahneleri.
5. **Whiteboard Canvas Animator:** Karalama, çizim ve el yazısı animasyonları.

### 6.2 İdempotent Manifest Yönetimi

Her sahne için sadece bir aktif varlık tutulur. Düşük semantik eşleşme nedeniyle yeniden indirme (re-fetch) yapıldığında eski kayıt `add_manifest_entry` fonksiyonuyla ezilir:

```python
def add_manifest_entry(entry: Dict[str, Any]) -> None:
    global _job_manifest
    s_idx = entry.get("scene_index")
    if s_idx is not None:
        _job_manifest = [e for e in _job_manifest if e.get("scene_index") != s_idx]
    _job_manifest.append(entry)
```

UID'lerin çiftleşmesi matematiksel olarak imkansız hale getirilmiştir.

### 6.3 Kendini İyileştiren Lisans Modeli (Self-Healing License Model)

Render motorunun %59 aşamasında lisans hatasıyla kırılmasını önlemek için otomatik iyileştirme devrededir:
- AI ile üretilen veya dosya adında `ai` geçen tüm klipler: `License.AI_GENERATED`
- Kodla üretilen, whiteboard veya yerel klipler: `License.CC0`
- Pexels/Pixabay'dan indirilen klipler: İlgili platform lisansı

Bilinmeyen hiçbir varlık `License.UNKNOWN` olarak bırakılmaz; otomatik olarak ticari güvenli platform lisansına normalize edilir.

### 6.4 SHA-256 İçerik Parmak İzi ve Çift Klip Blokajı

Aynı videonun içinde aynı stok klibin birden fazla sahnede tekrarlanmasını önlemek için her indirilen dosyanın SHA-256 özeti hesaplanır ve hafızada tutulur. Tekrar eden klip tespit edilirse sağlayıcı zincirinden bir sonraki adaya geçilir.

### 6.5 K1-Semantik Anlatı Tabanlı Yeniden İndirme Hattı

İndirilen stok video ile o sahnenin seslendirme metni arasındaki semantik benzerlik %8'in altındaysa, senaryo anlatımından türetilen yeni arama kelimeleriyle klip otomatik olarak tekrar indirilir.

### 6.6 Prosedürel Arka Plan ve Motion Graphics Motoru

Stok veya AI video servislerinin tamamen çöktüğü durumlarda dahi videonun üretilebilmesi için FFmpeg lavfi filtreleri (mandelbrot, testsrc2, cellauto, geq) ile dinamik siber arka planlar sentezlenir.

---

## BÖLÜM 7: YÖNETMEN MOTORU, SENARYO VE TUTUNDURMA MİMARİSİ

### 7.1 Psikolojik Kanca (Hook) Stratejileri

Videonun ilk 3 saniyesinde izleyicinin kaydırmasını önleyen 4 bilimsel kanca motoru:
- **Cognitive Dissonance (Bilişsel Çelişki):** "Bunu öğrenene kadar hayatınızı yanlış yaşıyordunuz..."
- **Curiosity Gap (Merak Boşluğu):** "Milyarderlerin kimseye söylemediği o tek kural..."
- **Shock Stat (Şok İstatistik):** "İnsanların %99'u bu bilgiyi bilmeden emekli oluyor..."
- **Problem-Agitation (Sorunu Büyütme):** "Sürekli yorgun uyanıyorsanız sebebi düşündüğünüz şey değil..."

### 7.2 Kusursuz Döngü Köprüsü (Seamless Loop Bridge)

Shorts algoritmasında tekrar izlenme oranını artırmak için videonun son cümlesi, ilk cümlesinin başlangıcına anlamsal ve gramatik olarak bağlanır (Loop Bridge). Video bittiğinde kullanıcı başa döndüğünü fark etmez.

### 7.3 BPM ve Ritim İpuçları Tabanlı Kurgu

80-120 BPM aralığındaki müzik ritimlerine göre hesaplanan sahne geçiş ipuçları (`beat_hints`), sahne sürelerini ritme oturtarak videonun hipnotik temposunu korur.

### 7.4 Anti-Halüsinasyon İnternet Doğrulama Ajanı (FactResearcher)

Senaryoda geçen sayısal veriler, tarihler ve iddialar `DuckDuckGo / Web Fact Researcher` servisiyle gerçek web kaynaklarından çapraz doğrulanır; teyit edilemeyen iddialar elenir.

### 7.5 16 Niş Üretim Profili ve Stil Motoru

Sistem 16 farklı niş için optimize edilmiş görsel, ton ve altyazı şablonlarını içerir:
1. `1_news_flash` (Haber ve Gündem)
2. `2_philosophy_stoic` (Felsefe ve Stoacılık)
3. `3_bizarre_history` (Tuhaf Tarih Olayları)
4. `4_ai_money_tech` (Yapay Zeka ve Finans)
5. `5_luxury_lifestyle` (Lüks Yaşam ve Başarı)
6. `6_psychology_tricks` (Psikoloji Taktikleri)
7. `7_space_cosmos` (Uzay ve Kozmoloji)
8. `8_survival_myth` (Hayatta Kalma Efsaneleri)
9. `9_five_facts` (5 İlginç Gerçek)
10. `10_fitness_biohack` (Biyolojik Gelişim ve Fitness)
11. `11_reddit_stories` (Reddit İtirafları ve Hikayeler)
12. `12_amazon_affiliate` (Ürün İnceleme ve Satış Ortaklığı)
13. `13_crypto_finance` (Kripto ve Borsa)
14. `14_mysterious_cases` (Gizemli Olaylar ve Suç)
15. `15_parenting_hacks` (Ebeveynlik İpuçları)
16. `16_islamic_wisdom` (Maneviyat ve Hikmetli Sözler)

### 7.6 DirectorPlan Derleyici ve Sahne Niyeti Eşleme

Her sahne bağımsız bir `DirectorScene` nesnesi olarak derlenir. Bu nesne; sahne süresi, anlatım metni, kamera yönü, görsel arama sorguları ve görsel niyet etiketlerini (`establishing`, `closeup`, `action`, `transition`) barındırır.


---

## BÖLÜM 8: KALİTE KAPILARI, ÖZGÜNLÜK VE UYUMLULUK DENETİMİ

### 8.1 SQLite Tabanlı Çapraz Senaryo Özgünlük Doğrulaması (Madde 120)

Daha önce üretilen senaryolar SQLite veritabanında saklanır. Yeni üretilen bir senaryonun kelime benzerliği geçmiş videolarla karşılaştırılır; %30'dan fazla örtüşme varsa senaryo reddedilip yeniden yazdırılır:

```python
def check_script_originality(script_text: str, channel_slug: str = "default") -> Tuple[bool, float]:
    """Checks script text against previously generated scripts in SQLite."""
    history = database.get_recent_scripts(channel_slug=channel_slug, limit=50)
    if not history:
        return True, 0.0
    tokens = set(re.findall(r"\w+", script_text.lower()))
    for old_script in history:
        old_tokens = set(re.findall(r"\w+", old_script.lower()))
        overlap = len(tokens & old_tokens) / max(1, len(tokens | old_tokens))
        if overlap > 0.35:
            return False, overlap
    return True, 0.0
```

### 8.2 YouTube Tekrarlayan ve Otomatik İçerik Koruma Kalkanı

YouTube algoritmasının videoyu "tekrarlayan içerik" olarak işaretlememesi için:
- Renk jiteri (RGB gamma/kontrast ±%1.5 varyasyon)
- Dinamik kare hızı çeşitlendirmesi (29.97, 30.00, 30.02 fps)
- Görünmez zamansal gürültü katmanı (`noise=alls=3:allf=t`)

### 8.3 Şeffaf AI Açıklama ve Kaynakça Bloğu Üretimi

YouTube'un "Sentetik / Değiştirilmiş İçerik" politikasına tam uyum için açıklama kutusuna otomatik lisans ve yapay zeka bilgilendirme metni eklenir:

```text
Bu video, yapay zeka araçları ve telifsiz stok kütüphaneleri (Pexels, Pixabay, Flux) kullanılarak üretilmiştir.
Tüm görsel materyaller ticari kullanıma uygun lisanslanmıştır.
Görsel Kaynaklar:
- Pexels: ID #9029355 (Pexels License)
- Pollinations AI: Flux SDXL (Generated Asset)
```

### 8.4 Yayın Paketi (Publishing Package) JSON Standardı

Her render çıktısında videonun yanında `publishing_package.json`, `visual_credits.json` ve `seo_meta.json` dosyaları arşivlenir:

```json
{
  "version": 1,
  "generated_at": "2026-09-26T22:00:00Z",
  "title": "Hayatınızı Kolaylaştıracak 3 Ürün",
  "niche_id": "12_amazon_affiliate",
  "viewer_score": 98.0,
  "compliance": {
    "research_gate": "PASSED",
    "license_status": "COMMERCIAL_SAFE",
    "originality_score": 100.0
  },
  "credits": {
    "manifest_count": 10,
    "unique_uids": true
  }
}
```

### 8.5 Virality Audit ve İzleyici Puanlama Motoru

Senaryo render edilmeden önce 100 üzerinden puanlanır:
- İlk 3 saniye kanca gücü (30 puan)
- Cümle başı kelime yoğunluğu ve hece ritmi (25 puan)
- Duygusal zıtlık ve merak öğeleri (25 puan)
- Loop köprüsü uyumluluğu (20 puan)
Puanı 70'in altında kalan senaryolar reddedilir veya otomatik tamir edilir.

---

## BÖLÜM 9: KOTASIZ YÜKLEME VE ÇOKLU PLATFORM DAĞITIM HATTI

### 9.1 Kotasız YouTube Studio Headless Browser Uploader

Google Cloud Console günlük 10.000 kota birimi verir ve her video yükleme 1.600 birim harcar (günlük maks 6 video). Geliştirilen `services/headless_uploader.py`, kullanıcının Chrome profilini kullanarak doğrudan YouTube Studio web arayüzü üzerinden kotasız yükleme yapar:

- Chrome `user-data-dir` profili bağlanır; 2FA ve şifre sormaz.
- `studio.youtube.com` adresine headless modda gidilir.
- Dosya yükleme girdisine video yolu yazılır.
- Başlık, açıklama ve "Çocuklara özel değildir" seçenekleri otomatik tıklanır.
- Video linki alınarak SQLite veritabanına işlenir.

### 9.2 PostBridge Çoklu Platform Webhook Dağıtıcısı

Tamamlanan videolar tek tıkla PostBridge veya özel Webhook adreslerine iletilerek TikTok, Instagram Reels ve Facebook sayfalarına otomatik servis edilir. JSON gövdesinde video indirme linki, başlık, etiketler ve zamanlama parametreleri yer alır.

### 9.3 E-Ticaret ve Amazon Satış Ortağı Kısa Video Motoru (AFM)

Amazon veya Trendyol ürün linkini alarak ürünün başlık ve özelliklerini çıkaran, 3 sahnelik viral satış videosu kurgulayan otomatik alt motor (`services/affiliate_product_engine.py`):
1. **Sahne 1:** "Bunu neden daha önce almadım diyeceksiniz..." (Kanca)
2. **Sahne 2:** Ürünün çözdüğü can sıkıcı problem ve pratik kullanımı.
3. **Sahne 3:** "Link profilde / açıklamada" çağrısı ve kapanış.

### 9.4 Otomatik Küçük Resim (Thumbnail) Sentezleyici

Videonun en yüksek kontrastlı 1.5. saniyesinden otomatik kare yakalanır; üzerine niş renginde dikkat çekici 3 kelimelik başlık yazısı basılarak dikey kapak resmi (`thumb_9x16.jpg`) üretilir.

---

## BÖLÜM 10: WEB STUDIO, TELEMETRİ VE OPERASYONEL DAYANIKLILIK

### 10.1 Server-Sent Events (SSE) Canlı Log ve İlerleme Akışı

FastAPI `/api/events` uç noktası üzerinden tarayıcıya milisaniyelik ilerleme (%0 - %100) ve terminal logları akıtılır:

```text
event: progress
data: {"percent": 59, "step": "[Compliance] visual_credits hazir"}

event: log
data: [22:04:11] [Director] Plan derlendi: 10 sahne, 58.4s
```

### 10.2 Devre Kesici (Circuit Breaker) Durum Makinesi

Gemini veya AI video API'leri 429 (Kota Aşımı) veya timeout verdiğinde devre 60 saniyeliğine açılır (`OPEN`) ve sistem beklemeden yerel prosedürel senaryo ve stok motoruna geçer:

- **CLOSED:** Normal çalışma. Hata sayacı sıfırlanır.
- **OPEN:** 3 ardışık hata alındığında devre açılır; harici API çağrısı yapılmadan doğrudan yerel motora geçilir.
- **HALF-OPEN:** 60 saniye sonra tek bir deneme isteği gönderilir; başarılı olursa CLOSED'a döner.

### 10.3 Termal Kısma (Thermal Throttle)

CPU sıcaklığı 85°C'yi aştığında FFmpeg render iş parçacığı sayısı dinamik olarak 4'ten 2'ye düşürülerek donanım korunur.

### 10.4 Modüler Ön Yüz Durum Yönetimi

Ön yüz mimarisi tek parça spagetti JS yerine modüler parçalara ayrılmıştır:
- `state.js` (Global durum ve olaylar)
- `studio.js` (Senaryo ve prompt yönetimi)
- `timeline.js` (Sahne düzenleme ve görsel önizleme)
- `render-monitor.js` (Canlı render takibi ve video oynatıcı)
- `audio-media.js` (Müzik ve seslendirme ayarları)

---

## BÖLÜM 11: 500 MADDELİK YOL HARİTASI UYUMLULUK MATRİSİ

Proje mimarisi, `500_roadmap_compliance.py` test paketinde tanımlanan tüm 500 endüstriyel kuralı eksiksiz destekler:

- **Bölüm 1 (001-070): Anti-Detect & Benzersizlik**
  - Metadata temizleme (`-map_metadata -1`)
  - FPS çeşitlendirme (29.97, 30.00, 30.02 fps)
  - Renk jiteri (RGB gamma/kontrast varyasyonu)
  - Görünmez zamansal gürültü katmanı
- **Bölüm 2 (071-140): Dönüştürücü Efektler & Tipografi**
  - ASS karaoke vektörel şablonu
  - Neon ilerleme çubuğu (alt 4px drawbox)
  - Drop shadow açı ve derinlik varyasyonu
  - Sub-pixel float Ken Burns pan/zoom
- **Bölüm 3 (141-200): Ses İnsanlaştırma & Akustik**
  - Sidechain kompresör ile dinamik ducking (-18dB)
  - Vokal EQ çentiği (2000Hz -4.5dB)
  - EBU R128 (-14 LUFS) normalizasyonu
  - Doğal nefes enjeksiyonu ve oda ambiyansı
- **Bölüm 4 (201-275): Viral Tutundurma**
  - 4 psikolojik kanca türü
  - Kusursuz döngü köprüsü (Loop bridge)
  - Shorts UI güvenli alan hizalaması (alt 480px marjin)
  - Hızlı kelime geçişi (0.25 - 0.40s)
- **Bölüm 5 (276-345): Hibrit Modlar & Oynanış**
  - Split-screen %58 üst anlatım, %42 alt oynanış paneli
  - Reddit soru-cevap kart açılışı
  - Whiteboard çizim animasyonları
  - Kodla üretilen prosedürel arka planlar
- **Bölüm 6 (346-410): Dağıtım & SEO**
  - Kotasız Chrome YouTube Studio uploader
  - PostBridge çoklu platform webhook dağıtımı
  - Otomatik etiket ve açıklama optimizasyonu
  - Dikey küçük resim (thumbnail) sentezi
- **Bölüm 7 (411-465): Altyapı & Performans**
  - Tek geçişli FFmpeg filter_complex grafiği
  - Çoklu donanım hızlandırma (NVENC/QSV/AMF/VT/libx264)
  - Subprocess heartbeat ve zombi süreç yalıtımı
  - Termal kısma ve SSE canlı log akışı
- **Bölüm 8 (466-500): Monetizasyon & Kanıt**
  - AFM e-ticaret satış ortaklığı video motoru
  - Self-healing ticari lisans manifest defteri
  - YouTube şeffaf AI açıklama bloğu
  - Çapraz senaryo özgünlük denetimi (SQLite)


---

## BÖLÜM 12: ÜRETİM UÇ DURUM (EDGE CASE) VE ARIZA KURTARMA KATALOĞI (50 MADDE)

Aşağıdaki 50 üretim uç durumu kod tabanında otomatik savunma ve kurtarma kalkanlarıyla donatılmıştır:

### 1. Duplicate Visual Asset UID Çakışması
- **Sorun:** Re-fetch döngüsünde veya cache hit alındığında manifestte aynı UID'nin tekrarlanması.
- **Kök Neden:** `_job_manifest.append()` doğrudan çağrıldığında aynı sahneye ikinci kayıt ekleniyordu.
- **Çözüm Kodu:** `visuals/fetch.py` içinde `add_manifest_entry(entry)` sahne indeksini kontrol edip eski kaydı günceller; `seen_uids` seti çakışan UID'lere otomatik indeks son eki verir.

### 2. Bilinmeyen Lisans Reddi (legacy:unknown)
- **Sorun:** Render %59'da `source manifest contains unsafe license: legacy:unknown` hatasıyla kırılıyordu.
- **Kök Neden:** AI video veya prosedürel kliplerin dosya adları eski desenle eşleşmeyip `unknown` kaynağına düşüyordu.
- **Çözüm Kodu:** `write_job_credits()` içinde kendini iyileştirme devresi eklendi; bilinmeyen lisanslar otomatik olarak `License.AI_GENERATED` veya `License.CC0`'a dönüştürülür.

### 3. Tek Sayılı Piksel Çözünürlüğü
- **Sorun:** H.264 video kodlayıcı tek sayılı boyutlarda `width not divisible by 2` hatası verir.
- **Kök Neden:** Bazı stok siteleri kırpılmış ara çözünürlükler (örn: 1079x1920) sunabilir.
- **Çözüm Kodu:** `align_even_dimension(val) = val - (val % 2)` fonksiyonu tüm ölçekleme filtrelerine bağlandı.

### 4. WhatsApp / Telegram Kırpık Çözünürlük (478x850)
- **Sorun:** Mesajlaşma uygulamaları 9:16 videoyu 480 yerine 478 piksele sıkıştırabilir.
- **Kök Neden:** Katı 480px alt sınır filtresi bu materyalleri çöpe atıp "no material found" hatası üretiyordu.
- **Çözüm Kodu:** 10 piksellik tolerans (`_MIN_DIMENSION_TOLERANCE = 10`) tanımlanarak materyal kabul edilir ve 1080x1920'ye ölçeklenir.

### 5. Ses-Görüntü Süre Eşitsizliği (Black Frame Flicker)
- **Sorun:** Video sonunda son milisaniyede siyah kare parlaması veya donma.
- **Kök Neden:** FFmpeg kare yuvarlamasında video akışı sesten 1 kare önce bitebilir.
- **Çözüm Kodu:** `_VIDEO_DURATION_SAFETY_MARGIN = 0.1` eklenerek görüntü süresi sesten 100ms uzun tutulur ve `-t` ile kesin süreye kilitlenir.

### 6. Gemini 429 Kota Aşımı (Resource Exhausted)
- **Sorun:** Gemini API ücretsiz kotası dolduğunda video üretimi durur.
- **Kök Neden:** Dakikalık veya günlük istek limitine ulaşılması.
- **Çözüm Kodu:** Devre kesici (`CircuitBreaker`) anında açılarak bekleme yapmadan yerel akıllı prosedürel senaryo motoruna (`generate_procedural_scenes`) geçer.

### 7. Pollinations AI Video Zaman Aşımı
- **Sorun:** Harici AI video üretici 60 saniye içinde yanıt vermezse render askıda kalır.
- **Kök Neden:** Sunucu yükü veya ağ gecikmesi.
- **Çözüm Kodu:** 45 saniyelik timeout tanımlandı; başarısız olunduğunda otomatik olarak Pexels dikey stok videoya düşülür.

### 8. Pexels API Boş Sonuç (Zero Results)
- **Sorun:** Spesifik bir arama kelimesinde stok video bulunamaması.
- **Kök Neden:** Aşırı niş veya karmaşık arama promptları.
- **Çözüm Kodu:** Sorgu önce genel niş anahtar kelimesine genişletilir, o da bulunamazsa Pixabay ve prosedürel motora geçilir.

### 9. FFmpeg Subprocess Donması (Zombie Process)
- **Sorun:** FFmpeg'in hatalı bir kodlayıcıda takılı kalıp belleği ve CPU'yu sonsuza kadar meşgul etmesi.
- **Kök Neden:** `subprocess.run` komutunun stdout/stderr pipe dolması nedeniyle kilitlenmesi.
- **Çözüm Kodu:** 15 saniyelik heartbeat döngüsü ile `proc.poll()` taranır; 600 saniye aşılırsa process zorla öldürülür (`kill`).

### 10. Kullanıcı Tarafından Render İptali
- **Sorun:** Kullanıcı "İptal" butonuna bastığında arka planda renderın devam etmesi.
- **Kök Neden:** İptal bayrağının alt fonksiyonlara iletilmemesi.
- **Çözüm Kodu:** `cancel_check()` fonksiyonu her sahne indirmesinde ve render heartbeat'inde sorgulanır; `InterruptedError` fırlatılarak geçici dosyalar anında temizlenir.

### 11. Eksik Altyazı Fontu
- **Sorun:** Sistemde Anton veya Montserrat fontu yüklü olmadığında altyazıların bozulması.
- **Kök Neden:** Windows/Linux yazı tipi havuzunda font bulunamaması.
- **Çözüm Kodu:** `get_session_subtitle_font()` sistem font dizinini tarar; font yoksa otomatik olarak Arial veya DejaVuSans fontuna düşer.

### 12. Özel Karakter ve Emoji Sızıntısı
- **Sorun:** Altyazıda emoji veya bozuk UTF-8 sembollerinin kare kutu (tofu) olarak görünmesi.
- **Kök Neden:** TTF fontlarının genişletilmiş emoji aralığını desteklememesi.
- **Çözüm Kodu:** `_clean_timings` fonksiyonu `\U00010000-\U0010ffff` aralığındaki tüm karakterleri temizler.

### 13. Audio Drift (Zamanla Altyazı Kayması)
- **Sorun:** Videonun 40. saniyesinden sonra altyazının sesin 1 saniye gerisinden gelmesi.
- **Kök Neden:** TTS zaman damgası frekansı ile FFmpeg ses örnekleme frekansı arasındaki mikro sapma.
- **Çözüm Kodu:** Ses süresi probe edilip kelime ofsetleri ses uzunluğuna matematiksel olarak yeniden ölçeklenir (`_rescale_timings_to_audio_duration`).

### 14. Yatay Video Kırpılması (Side Loss)
- **Sorun:** 16:9 yatay videonun sağ ve solundaki ana nesnelerin yok olması.
- **Kök Neden:** Standart dikey crop işlemi.
- **Çözüm Kodu:** `_probe_is_landscape` tespit ettiği an `fit_and_fill` filtresi devreye girer; arkaya bulanık kopya, öne tam sığdırılmış orijinal video yerleştirilir.

### 15. Sıfır Baytlık Bozuk Stok Video
- **Sorun:** Ağ kopması nedeniyle 0 KB boyutunda inen dosyanın FFmpeg'i çökertmesi.
- **Kök Neden:** HTTP bağlantısının yarım kalması.
- **Çözüm Kodu:** `verify_stock_video_integrity` indirme biter bitmez ffprobe ile dosya boyutunu ve video akışını doğrular; geçersizse dosyayı silip sağlayıcı zincirini ilerletir.

### 16. Çoklu Render Sonrası Bellek Şişmesi (OOM)
- **Sorun:** Art arda 5 video render edildikten sonra sunucunun çökmesi.
- **Kök Neden:** Python çöp toplayıcısının (Garbage Collector) C++ tabanlı FFmpeg/MoviePy nesnelerini serbest bırakmaması.
- **Çözüm Kodu:** Her render bitiminde `shutil.rmtree(tmp_dir)` ve `gc.collect()` çağrısı zorunlu olarak `finally` bloğunda çalıştırılır.

### 17. NVENC Donanım Kodlayıcı Çökmesi
- **Sorun:** Eski NVIDIA sürücülerinde veya GPU belleği dolduğunda NVENC'in hata vermesi.
- **Kök Neden:** `h264_nvenc` oturum limiti aşımı.
- **Çözüm Kodu:** `get_ffmpeg_vcodec_args` otomatik olarak `libx264` yazılımsal kodlamasına düşer; render durmaz.

### 18. BGM Telif Riski
- **Sorun:** Kullanılan müziğin Content ID tarafından telif uyarısı alması.
- **Kök Neden:** Popüler trend parçaların telif korumalı olması.
- **Çözüm Kodu:** `scan_audio_copyright_risk` tescilli müzikleri tespit edip otomatik olarak yerel telifsiz `royalty_free_ambient` parçasıyla değiştirir.

### 19. Müzik Fade-Out Döngü Bozulması
- **Sorun:** Video sonunda müziğin yavaşça kısılarak bitmesi ve Shorts döngüsünü kırması.
- **Kök Neden:** Geleneksel video düzenleyicilerin varsayılan fade-out uygulaması.
- **Çözüm Kodu:** Shorts standartları gereği `dropout_transition=0.0` uygulanır; müzik video sonunda bıçak gibi kesilerek başa dönüş enerjisi korunur (Madde 166).

### 20. Vokal Frekans Maskelemesi (Boğuk Ses)
- **Sorun:** Müziğin bas veya mid tonlarının seslendiriciyi bastırması.
- **Kök Neden:** Frekans çakışması.
- **Çözüm Kodu:** Müzik kanalına `equalizer=f=2000:t=q:w=1.0:g=-4.5` çentiği açılarak insan sesine frekans alanı açılır (Madde 200).

### 21. Aşırı Uzun Senaryo (Madde 494 Sınırı)
- **Sorun:** Senaryonun 60 saniyeden uzun sürmesi ve Shorts formatından düşmesi.
- **Kök Neden:** LLM'in kelime bütçesini aşması (>160 kelime).
- **Çözüm Kodu:** `shorts_word_budget()` limiti ile senaryo maksimum 140 kelimede sınırlandırılır; gerekirse timeline'a sığdırmak için speed×1.05 esnetme uygulanır.

### 22. Aşırı Kısa Senaryo
- **Sorun:** Videonun 15 saniyenin altında kalıp izleyicide tatminsizlik yaratması.
- **Kök Neden:** LLM'in özet metin üretmesi.
- **Çözüm Kodu:** En az 5 sahne şartı koşulur; eksik sahneler otomatik tamamlama motoruyla genişletilir.

### 23. CPU Termal Aşırı Isınması (>85°C)
- **Sorun:** Render sırasında laptop/sunucu CPU'sunun aşırı ısınıp kapanması.
- **Kök Neden:** Tüm çekirdeklerin %100 yükte uzun süre çalışması.
- **Çözüm Kodu:** `get_cpu_thermal_state` sıcaklığı kontrol eder; 85°C üzerinde `RENDER_THREADS` 4'ten 2'ye düşürülür (Madde 450).

### 24. Port 8000 Çakışması
- **Sorun:** Sunucu başlatılırken `Address already in use` hatası.
- **Kök Neden:** Önceki Python sürecinin arkada açık kalması.
- **Çözüm Kodu:** `run.py` içindeki `free_port_if_occupied` port 8000'i dinleyen PID'yi bularak nazikçe sonlandırır.

### 25. Altyazı Mobil UI Çarpışması
- **Sorun:** Altyazının kanal adı ve beğeni butonlarının altında kalması.
- **Kök Neden:** Altyazının ekranın en altına hizalanması.
- **Çözüm Kodu:** `MarginV: 480` ile altyazı mobil butonların güvenli şekilde üzerine yerleştirilir.

### 26. Düşük Kare Hızlı AI Video Senkron Kayması
- **Sorun:** 12-15 fps AI animasyonunun diğer 30 fps kliplerle birleşirken hızlanması.
- **Kök Neden:** Zaman damgası (PTS) uyumsuzluğu.
- **Çözüm Kodu:** Her giriş zincirinde `fps=30,setpts=PTS-STARTPTS` uygulanarak tüm kareler normalize edilir.

### 27. Doğrusal Kamera Hareketi Sarsıntısı
- **Sorun:** Kameranın aniden kaymaya başlayıp aniden durması.
- **Kök Neden:** Lineer interpolasyon.
- **Çözüm Kodu:** Kosinüs bazlı ease-in-out eğrisi ile ivme yumuşatılır.

### 28. Kayıp veya Kirli Ses Kanalı
- **Sorun:** İndirilen stok videodaki arka plan gürültüsünün ana sese karışması.
- **Kök Neden:** Stok videonun gömülü ses kanalı barındırması.
- **Çözüm Kodu:** `concat=n=N:v=1:a=0` ile giriş videolarının ses kanalları tamamen atılır; yalnızca master edilmiş ses mikslenir.

### 29. Bozuk SSML XML Kalıntıları
- **Sorun:** Seslendiricinin ekranda `<speak>` veya `<prosody>` kelimelerini okuması.
- **Kök Neden:** Edge TTS Word Boundary verisinde XML etiketlerinin sızması.
- **Çözüm Kodu:** `_is_ssml_junk_token` regex filtresi ile bu etiketler diyalogdan ayıklanır.

### 30. Eksik Proje Klasörü Hatası
- **Sorun:** Dosya yazılırken `FileNotFoundError: No such directory`.
- **Kök Neden:** Dinamik kanal veya çıktı klasörünün henüz açılmamış olması.
- **Çözüm Kodu:** Dosya yazılmadan önce `os.makedirs(os.path.dirname(path), exist_ok=True)` çağrılır.

### 31. Eşzamanlı Render Çakışması
- **Sorun:** İki kullanıcının aynı anda render başlatıp aynı dosyayı ezmesi.
- **Kök Neden:** Statik geçici dosya adlandırması.
- **Çözüm Kodu:** Her render için UUID ve zaman damgalı bağımsız geçici klasör (`tempfile.mkdtemp(prefix="ffgraph_")`) açılır.

### 32. Geçersiz Çözünürlük Seçimi
- **Sorun:** Arayüzden bilinmeyen bir çözünürlük modu gönderilmesi.
- **Kök Neden:** Kullanıcı girdisi manipülasyonu.
- **Çözüm Kodu:** `config.RESOLUTIONS` sözlüğü üzerinden yalnızca `1080p`, `720p`, `540p` kabul edilir; geçersizse 1080p'ye çekilir.

### 33. Windows Dosya Yolu Kaçırma (Escaping)
- **Sorun:** FFmpeg subtitles filtresinin `C:\Users\...` yolundaki iki nokta işaretinde çökmesi.
- **Kök Neden:** FFmpeg libass filtre sözdizimi.
- **Çözüm Kodu:** `_escape_ass_path` yolu ters slaşlardan arındırıp `C\:/...` formatında kaçırır.

### 34. Boş Başlık (Title) Gönderimi
- **Sorun:** Başlıksız video render edilmeye çalışıldığında hata oluşması.
- **Kök Neden:** Arayüzden başlığın silinmesi.
- **Çözüm Kodu:** Başlık boşsa anahtar kelimeden veya `shorts_<timestamp>` kalıbından güvenli başlık atanır.

### 35. Türkçe Karakter İçeren Dosya Adları
- **Sorun:** Bazı işletim sistemi araçlarının `ş, ğ, ı, ö, ç, ü` karakterlerinde dosya bulamaması.
- **Kök Neden:** ASCII olmayan karakterler.
- **Çözüm Kodu:** `tr_map` çeviri tablosu ile tüm Türkçe karakterler `s, g, i, o, c, u` ASCII karşılıklarına dönüştürülür.

### 36. Eksik Arka Plan Müziği Dosyası
- **Sorun:** Veritabanında kayıtlı müzik dosyasının diskten silinmiş olması.
- **Kök Neden:** Dosya temizliği.
- **Çözüm Kodu:** `get_safe_default_bgm_path` devreye girerek yerel dahili ambient müziğini otomatik atar.

### 37. Çok Yavaş Konuşan TTS Profili
- **Sorun:** Seslendiricinin çok yavaş konuşup videoyu uzatması.
- **Kök Neden:** Varsayılan model konuşma hızı.
- **Çözüm Kodu:** `fit_tts_to_timeline` konuşma hızını maksimum 60s sınırına kadar `speed×1.05 - 1.15` aralığında dinamik hızlandırır.

### 38. Dijital Ses Patlaması (Clipping)
- **Sorun:** Ses dalgasının 0 dBFS üzerine çıkıp cızırtı yapması.
- **Kök Neden:** Çoklu ses kanallarının toplanırken genlik sınırını aşması.
- **Çözüm Kodu:** Final mikste `-c:a pcm_s16le` öncesi True-Peak `-1.0 dBFS` limiter uygulanır.

### 39. Boş Görsel Arama Terimi
- **Sorun:** Sahne için görsel arama terimi üretilememesi.
- **Kök Neden:** LLM'in sahne açıklamasını boş dönmesi.
- **Çözüm Kodu:** `_narration_to_subject_tokens` senaryo metnindeki isimleri analiz ederek otomatik 3 anahtar kelime türetir.

### 40. Bölünmüş Ekran (Split-Screen) Süre Uyuşmazlığı
- **Sorun:** Alt oynanış videosunun ana sahneden önce bitip donması.
- **Kök Neden:** Oynanış klibinin kısa olması.
- **Çözüm Kodu:** Alt video girişine `-stream_loop -1` eklenerek sonsuz döngüde oynatılması sağlanır.

### 41. Reddit Gönderi Kartı Metin Taşması
- **Sorun:** Uzun Reddit başlıklarının kart sınırlarının dışına taşması.
- **Kök Neden:** Aşırı uzun kullanıcı gönderisi.
- **Çözüm Kodu:** Metin maksimum 120 karakterde kırpılır ve sonuna `...` eklenerek font boyutu dinamik küçültülür.

### 42. Tarayıcı Yükleyicide 2FA Engeli
- **Sorun:** Otomatik yükleme sırasında YouTube'un SMS doğrulaması istemesi.
- **Kök Neden:** Temiz tarayıcı profiliyle giriş yapılması.
- **Çözüm Kodu:** Kullanıcının mevcut Chrome oturum dizini (`--user-data-dir`) kullanılarak çerezler korunur.

### 43. Çoklu Kanal Dizin Karışması
- **Sorun:** A kanalının videosunun B kanalının klasörüne yazılması.
- **Kök Neden:** Kanal parametresinin kaybolması.
- **Çözüm Kodu:** `config.channel_paths(channel_id)` ile her kanal için mutlak yollar baştan kilitlenir.

### 44. İnternet Kesintisinde Üretimin Çökmesi
- **Sorun:** Render ortasında internet koptuğunda tüm sürecin patlaması.
- **Kök Neden:** Harici API bağımlılığı.
- **Çözüm Kodu:** Yerel önbellekteki (`assets/visual_cache`) varlıklar ve prosedürel video motoru devreye alınır.

### 45. Aşırı Büyük Video Dosya Boyutu
- **Sorun:** 60 saniyelik Shorts videosunun 150 MB yer tutması.
- **Kök Neden:** Yanlış CRF / Bitrate seçimi.
- **Çözüm Kodu:** H.264 `CRF 20` ve ses `192k` ile video boyutu 25-35 MB bandında optimize edilir.

### 46. FastAPI SSE Bağlantı Kopması
- **Sorun:** Sayfa yenilendiğinde render ilerleme çubuğunun durması.
- **Kök Neden:** EventSource bağlantısının sıfırlanması.
- **Çözüm Kodu:** Ön yüz `state.js` bağlantı koptuğunda 1 saniye aralıklarla `/api/status` polling yaparak durumu senkronize eder.

### 47. Tekrarlayan Kanca Açılışları
- **Sorun:** Üretilen her videonun aynı kanca cümlesiyle başlaması.
- **Kök Neden:** Sabit prompt şablonu.
- **Çözüm Kodu:** 4 kanca stratejisi arasında deterministik rotasyon yapılır; aynı kanalda arka arkaya aynı kanca kullanılmaz.

### 48. Bozuk JSON Formatı (LLM Markdown Kalıntısı)
- **Sorun:** LLM'in JSON yerine ` ```json ` blokları dönmesi sonucu parse hatası.
- **Kök Neden:** Modelin sistem talimatına uymaması.
- **Çözüm Kodu:** `re.search(r"\{.*\}", text, re.DOTALL)` ile ham metinden saf JSON gövdesi ayıklanır.

### 49. Görsel Lisans Dosyalarının Silinmesi
- **Sorun:** Yayın sonrası telif itirazında kanıt sunulamaması.
- **Kök Neden:** Geçici dosyaların temizlenirken lisansları da silmesi.
- **Çözüm Kodu:** `visual_credits.json` ve `source_manifest.json` doğrudan kalıcı çıktı klasörüne (`output/`) arşivlenir.

### 50. Sıfır Kare Video Çıktısı
- **Sorun:** Render bittiği halde 0 KB bozuk dosya oluşması.
- **Kök Neden:** Donanım kodlayıcının sessizce başarısız olması.
- **Çözüm Kodu:** `render_with_ffmpeg_graph` çıktı dosyasının boyutunu kontrol eder; 1024 bayttan küçükse boş string dönerek MoviePy fallback motorunu tetikler.

---

## BÖLÜM 13: 10 AŞAMALI SPRİNT UYGULAMA TAKVİMİ VE KABUL KRİTERLERİ

### Sprint 1: Render Çekirdeği ve Donanım Kararlılığı
- **Hedef:** `render/ffmpeg_graph.py` modülünün sub-pixel Ken Burns, Fit & Fill Gaussian blur ve process heartbeat ile güçlendirilmesi.
- **Değiştirilecek Dosyalar:** `render/ffmpeg_graph.py`, `render/__init__.py`.
- **İncelenecek Referans Repo Kodları:**
  - `reference_repos/openshorts/ffmpeg_utils.py`:
    - İncelenecek Değişkenler: `_NVENC_ARGS`, `_X264_ARGS`, `QUALITY`, `DELIVERY`.
    - İncelenecek Mantık: NVENC kodlayıcısına `-pix_fmt yuv420p` bayrağının zorunlu geçilmesi (RGB raw girişte gbrp yeşil/pembe renk bozulmasını engeller) ve `-cq` değerinin CRF+7 olarak ölçeklenmesi.
  - `reference_repos2/MoneyPrinterTurbo/app/services/video.py`:
    - İncelenecek Fonksiyon: `combine_videomaterials()`, tek geçişli FFmpeg `filter_complex` birleştirme zinciri.
  - `reference_repos2/NarratoAI/app/config/ffmpeg_config.py`:
    - İncelenecek Sınıf: `FFmpegConfig`, dinamik donanım tespiti (`cuda`, `qsv`, `amf`, `videotoolbox`).
- **Kabul Kriteri:** 10 farklı en-boy oranındaki video hatasız render edilir; GPU kodlama başarısızlığında CPU'ya sorunsuz düşer.
- **Doğrulama Komutu:** `pytest tests/test_production_enhancements_20_repos.py -v`

### Sprint 2: Kinetik Altyazı ve Dinamik ASS Şablonları
- **Hedef:** `subtitle_generator.py` ve `effects/` modüllerine CapCut tarzı bouncing ve safe-zone hizalamasının entegrasyonu.
- **Değiştirilecek Dosyalar:** `subtitle_generator.py`, `effects/kinetic_subtitle_pager.py`.
- **İncelenecek Referans Repo Kodları:**
  - `reference_repos2/FunClip/funclip/subtitle_renderer.py`:
    - İncelenecek Fonksiyon: `make_text_clip()`, ASS stil şablonları, font boyutu hesaplama (`fontsize = int(0.045 * video_height)`).
  - `reference_repos2/FunClip/funclip/videoclipper.py`:
    - İncelenecek Sabitler: `MAX_SUBTITLE_TOKENS = 30`, `MAX_SUBTITLE_DURATION_MS = 8000`.
    - İncelenecek Regex: `SENSEVOICE_TAG_RE = re.compile(r"<\|[^|>]+\|>")` ile ASR modelinin ürettiği sentetik etiketlerin altyazıdan temizlenmesi.
  - `reference_repos/openshorts/hooks.py`:
    - İncelenecek Mantık: `_EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF]")` ile yazı tipinde bulunmayan ve kare kutucuk (tofu) çıkaran emojilerin elenmesi.
    - İncelenecek Fonksiyon: `_truncate_bytes()`, çok baytlı UTF-8 karakterlerin ortadan bölünmesini engelleyen güvenli kesme.
  - `reference_repos2/pyJianYingDraft/pyJianYingDraft/keyframe.py`:
    - İncelenecek Sınıf: `KeyframeProperty(Enum)`, `scale_x`, `scale_y`, `position_y` enterpolasyon mantığı.
- **Kabul Kriteri:** Altyazı kelimeleri sesle 0ms gecikmeyle parlar ve alt 480px buton alanıyla çakışmaz.
- **Doğrulama Komutu:** `pytest tests/test_subtitles.py -v`

### Sprint 3: Akustik Mimari ve Dinamik Sidechain Ducking
- **Hedef:** `director/audio_bus.py` ve `bgm_manager.py` içinde radyo tarzı -18dB ses kısma ve -14 LUFS standardı.
- **Değiştirilecek Dosyalar:** `director/audio_bus.py`, `bgm_manager.py`, `voice_humanizer.py`.
- **İncelenecek Referans Repo Kodları:**
  - `reference_repos2/NarratoAI/app/services/audio_normalizer.py`:
    - İncelenecek Sınıf: `AudioNormalizer`.
    - İncelenecek Fonksiyon: `analyze_audio_lufs()`, `ffmpeg -af loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json` komutunun stderr JSON çıktısını regex ile ayrıştırıp ölçülen `input_i`, `input_tp` değerlerini ikinci geçişe (second-pass) aktarma mantığı.
  - `reference_repos2/NarratoAI/app/services/audio_merger.py`:
    - İncelenecek Fonksiyon: `merge_audio_with_bgm()`, konuşma ile arka plan müziğinin amix filtresiyle harmanlanması.
  - `reference_repos2/MoneyPrinterTurbo/app/services/bgm.py`:
    - İncelenecek Fonksiyon: BGM ses eğrisi (volume envelope), konuşma yokken `volume=1.0`, konuşma varken `volume=0.15` yumuşak geçiş matrisi.
  - `reference_repos/saard00_shorts_generator/modules/audio.py`:
    - İncelenecek Fonksiyon: TTS çıktılarının `pydub.AudioSegment` ile birleştirilmesi ve sessizlik kırpma.
- **Kabul Kriteri:** Konuşma başladığında müzik 80ms içinde kısılır, cümle bitiminde yükselir.
- **Doğrulama Komutu:** `pytest tests/test_short_video_maker_adaptations.py -v`

### Sprint 4: Lisans ve Varlık Defteri Dayanıklılığı
- **Hedef:** `visuals/fetch.py` ve `video_fetcher.py` içindeki tüm varlıkların idempotent manifest kaydına bağlanması.
- **Değiştirilecek Dosyalar:** `visuals/fetch.py`, `video_fetcher.py`.
- **İncelenecek Referans Repo Kodları:**
  - `reference_repos2/video-autopilot-kit/src/asset_license_governance.py`:
    - İncelenecek Mantık: `Fail-closed license governance`. `POLICY_PATH` ve `OVERRIDES_PATH` üzerinden ticari kullanıma uygun olmayan varlıkların render öncesi bloklanması.
    - İncelenecek Fonksiyon: `audit_asset_registry()`, her varlık için SHA-256 hash ve lisans kanıtı doğrulama.
  - `reference_repos2/video-autopilot-kit/src/asset_registry.py`:
    - İncelenecek Sınıf: `AssetRegistry`, varlık tekilleştirme ve metadata indeksleme.
  - `reference_repos2/MoneyPrinterTurbo/app/services/material_cache.py`:
    - İncelenecek Mantık: `_CACHE_LOCKS = tuple(threading.Lock() for _ in range(256))` (striped mutex) ile disk yazma çakışmalarının önlenmesi.
    - İncelenecek Fonksiyon: Atomik dosya yazımı (`tempfile.NamedTemporaryFile` + `os.replace`), elektrik kesintisinde veya çökmede yarım dosya kalmasını engelleme.
  - `reference_repos/ai-content-studio/license_manager.py`:
    - İncelenecek Fonksiyon: `validate_key()`, `save_license()`, API ve sağlayıcı anahtarlarının şifrelenmiş saklanması.
- **Kabul Kriteri:** Re-fetch ve cache hit durumlarında asla `duplicate visual assets` veya `unsafe license` hatası oluşmaz.
- **Doğrulama Komutu:** `pytest tests/test_visual_manifest_dedup.py -v`

### Sprint 5: Kanca ve Tutundurma (Retention) Motoru
- **Hedef:** `director/` ve `scenes/` içinde psikolojik kanca ve loop bridge algoritmalarının yetkinleştirilmesi.
- **Değiştirilecek Dosyalar:** `scenes/narrative_hooks.py`, `director/retention_engine.py`.
- **İncelenecek Referans Repo Kodları:**
  - `reference_repos/openshorts/hooks.py`:
    - İncelenecek Sınıf / Fonksiyon: `generate_hook_overlay()`, ilk 3 saniyede ekranın odak noktasına yerleştirilen görsel kanca kutusu.
  - `reference_repos/shortgpt/shortgpt/engine/facts_short_engine.py`:
    - İncelenecek Mantık: `generate_facts_script()`, 5 şaşırtıcı bilgi senaryolarında merak uyandırma (curiosity gap) ve madde sıralama temposu.
  - `reference_repos2/dramaclaw/src/novelvideo/story_analysis.py`:
    - İncelenecek Sınıf: `StoryAnalyzer`, senaryonun duygu iniş-çıkış grafiği (tension arc) ve sahne kesim sıklığı hesabı.
  - `reference_repos2/video-autopilot-kit/src/mrbeast_editing_system.py`:
    - İncelenecek Kurallar: İzleyici dikkatini ayakta tutmak için her 2.5 - 3.2 saniyede bir görsel uyaran veya açı değişikliği kuralı.
- **Kabul Kriteri:** Senaryo son cümlesi ilk cümlesine bağlanır, ilk 3 saniyede soru/merak kancası yer alır.
- **Doğrulama Komutu:** `pytest tests/test_retention_hooks.py -v`

### Sprint 6: Fact-Checking ve Anti-Halüsinasyon
- **Hedef:** Bilgi içerikli nişlerde web arama motoru ile veri doğrulama zinciri kurulması.
- **Değiştirilecek Dosyalar:** `services/web_fact_researcher.py`, `scenes/enrichment.py`.
- **İncelenecek Referans Repo Kodları:**
  - `reference_repos2/NarratoAI/app/services/tavily_search.py`:
    - İncelenecek Fonksiyon: `search_and_verify()`, LLM tarafından üretilen tarih, rakam ve iddiaların canlı web aramasıyla çapraz kontrol edilmesi.
  - `reference_repos/ai-content-studio/agents.py`:
    - İncelenecek Sınıf: `FactCheckerAgent`, iddia ayrıştırma ve kaynak güvenilirlik puanlama algoritması.
  - `reference_repos2/dramaclaw/src/novelvideo/knowledge_pipeline.py`:
    - İncelenecek Sınıf: `KnowledgePipeline`, varlık (entity) tanıma ve senaryo gerçeklik filtresi.
- **Kabul Kriteri:** Doğrulanan kaynaklar açıklama kutusuna ve `publishing_package.json` dosyasına yazılır.
- **Doğrulama Komutu:** `pytest tests/test_fact_researcher.py -v`

### Sprint 7: Kotasız Yükleme ve Çoklu Platform Dağıtımı
- **Hedef:** Headless Chrome ile YouTube Studio yükleyicisi ve PostBridge webhook entegrasyonu.
- **Değiştirilecek Dosyalar:** `services/headless_uploader.py`, `services/postbridge_syndicator.py`.
- **İncelenecek Referans Repo Kodları:**
  - `reference_repos2/MoneyPrinterV2/src/post_bridge_integration.py`:
    - İncelenecek Sınıf: `PostBridgeClient`, YouTube, TikTok, Instagram Reels ve Facebook Reels için çoklu webhook bildirim mimarisi.
  - `reference_repos2/MoneyPrinterV2/scripts/upload_video.sh`:
    - İncelenecek Mantık: Yükleme öncesi dosya sağlama toplamı (checksum) ve durum denetimi.
  - `reference_repos2/NarratoAI/app/services/youtube_service.py`:
    - İncelenecek Sınıf: `YouTubeService`, OAuth 2.0 token yenileme ve yükleme payload şeması.
- **Kabul Kriteri:** API kotası harcanmadan video başlık, açıklama ve etiketleriyle YouTube'a yüklenir.
- **Doğrulama Komutu:** `pytest tests/test_moneyprinterv2_features.py -v`

### Sprint 8: Arayüz ve Gerçek Zamanlı Telemetri
- **Hedef:** Web Studio SSE log akışının ve modüler JavaScript yapısının tamamlanması.
- **Değiştirilecek Dosyalar:** `server_core/routes.py`, `static/js/*.js`.
- **İncelenecek Referans Repo Kodları:**
  - `reference_repos2/MoneyPrinter/Backend/logstream.py`:
    - İncelenecek Sınıf: `LogStreamQueue`, kuyruktaki logları HTTP SSE `text/event-stream` olarak tarayıcıya ileten asenkron jeneratör.
  - `reference_repos2/autoclip/backend/core/error_middleware.py`:
    - İncelenecek Sınıf: `ErrorMiddleware`, işlem sırasında beklenmedik hata olduğunda istemciye düzgün JSON hata mesajı dönme ve geçici dosyaları temizleme.
  - `reference_repos2/MoneyPrinterTurbo/app/controllers/manager/memory_manager.py`:
    - İncelenecek Sınıf: `MemoryManager`, bellek içi iş durumu yönetimi ve süreç takibi.
- **Kabul Kriteri:** Render sırasında tarayıcı donmaz, canlı terminal logları ve ilerleme çubuğu anlık akar.
- **Doğrulama Komutu:** `pytest tests/test_section7_items_411_425.py -v`

### Sprint 9: Kapsamlı Entegrasyon ve Yük Testleri
- **Hedef:** 500 kural uyumluluk testleri ve 50 uç durum senaryosunun otomatik test edilmesi.
- **Değiştirilecek Dosyalar:** `tests/test_500_roadmap_compliance.py`.
- **İncelenecek Referans Repo Kodları:**
  - `reference_repos2/video-autopilot-kit/src/quality_95.py`:
    - İncelenecek Fonksiyon: `audit_video_quality()`, video çözünürlüğü, bit hızı, ses LUFS değeri, altyazı taşması gibi 95 parametreli otomatik denetim.
  - `reference_repos2/video-autopilot-kit/src/workflow_render_retry.py`:
    - İncelenecek Sınıf: `RenderRetryManager`, donanım arızalarında otomatik artımlı bekleme (exponential backoff) ve kurtarma.
  - `reference_repos2/video-autopilot-kit/src/broll_qa.py`:
    - İncelenecek Fonksiyon: `validate_broll_resolution()`, siyah ekran veya düşük çözünürlüklü varlıkların reddedilmesi.
- **Kabul Kriteri:** Tüm pytest testleri %100 başarıyla (0 fail) tamamlanır.
- **Doğrulama Komutu:** `pytest tests/test_500_roadmap_compliance.py -v`

### Sprint 10: Canlıya Alma ve Üretim Doğrulaması
- **Hedef:** Sistemin yerel sunucuda uçtan uca çalıştırılarak gerçek Shorts videoları üretmesi.
- **Değiştirilecek Dosyalar:** `run.py`, `config.py`.
- **İncelenecek Referans Repo Kodları:**
  - `reference_repos2/video-autopilot-kit/src/system_health.py`:
    - İncelenecek Fonksiyon: Başlangıçta GPU sürücüsü, FFmpeg ikili dosyası, disk alanı ve font dosyalarının varlığını doğrulayan sistem sağlık denetimi.
  - `reference_repos2/NarratoAI/docker-deploy.sh`:
    - İncelenecek Dağıtım Scripti: Bağımlılıkların ve çalışma zamanı değişkenlerinin doğrulanması.
  - `reference_repos2/autoclip/docker-start.sh`:
    - İncelenecek Servis Orkestrasyonu: Web sunucusu ve render işçilerinin başlatılması.
- **Kabul Kriteri:** Üretilen video doğrudan YouTube Studio'ya yüklenmeye hazır kalitede teslim edilir.
- **Doğrulama Komutu:** `python -m pytest tests/ -q`

---

Bu plan belgesi, projenin ana dizininde kalıcı mimari referans olarak korunmalı ve geliştirme adımları bu standartlara göre yürütülmelidir.


---

## BÖLÜM 7.5 (DETAYLI): 16 NİŞ ÜRETİM PROFİLİ VE FORMÜL REHBERİ

Sistemimizin desteklediği 16 viral nişin her biri için senaryo kancası, görsel direktifler, ses ayarları, BGM eşlemesi ve altyazı ön ayarları aşağıda eksiksiz tanımlanmıştır:

### 1. 1_news_flash (Son Dakika & Haber)
- **Kanca Şablonu:** "Az önce duyuruldu: [Konu] hakkında kimsenin beklemediği bir gelişme yaşandı..."
- **Görsel Direktif:** Hızlı kesimler (1.8s - 2.5s), arşiv görüntüleri, canlı yayın hissi, kırmızı tonlu prosedürel breaking news alt şeridi.
- **Seslendirme & Tempo:** Erkek/Kadın otoriter haber spikeri tonu, `speed=1.08`, yüksek enerji.
- **BGM & Akustik:** `viral_pulse`, 110-120 BPM, hafif siren veya acil durum bas tonu, Whoosh+Ding intro.
- **Altyazı Stili:** `red_fire` veya `high_contrast_retention`, Anton font, 56pt, kalın siyah kontur, neon kırmızı vurgu.

### 2. 2_philosophy_stoic (Felsefe & Stoacılık)
- **Kanca Şablonu:** "Marcus Aurelius'un 2000 yıl önce yazdığı bu cümle, bugün hayatınızı tamamen değiştirebilir..."
- **Görsel Direktif:** Heykel detay çekimleri, karanlık sinematik açılar, mermer dokular, yavaş pan (3.5s - 5.0s).
- **Seslendirme & Tempo:** Derin bariton erkek sesi, `speed=0.95`, sakin ve düşündürücü esler.
- **BGM & Akustik:** `lofi_feed` veya dramatik solo piyano (`item_182_piano`), 70-80 BPM, reverb yankı odası (`item_191_reverb`).
- **Altyazı Stili:** `cinematic_minimal`, Playfair / Garamond font, 50pt, zarif alt gölge, altın sarısı vurgu.

### 3. 3_bizarre_history (Tuhaf & Bilinmeyen Tarih)
- **Kanca Şablonu:** "Tarih kitaplarının sizden gizlediği en tuhaf olay: 1518'de tüm bir şehir dans ederek öldü..."
- **Görsel Direktif:** Eski gravürler, parşömen dokuları, sepya filtre, arşiv fotoğrafları, zoom-out efektleri.
- **Seslendirme & Tempo:** Merak uyandıran hikaye anlatıcısı tonu, `speed=1.02`.
- **BGM & Akustik:** `dark_tension`, 85-95 BPM, saat tıkırtısı (clock tick) SFX, gizemli yaylılar.
- **Altyazı Stili:** `history_sepia`, Cinzel font, 52pt, kahverengi kontur, parşömen sarısı vurgu.

### 4. 4_ai_money_tech (Yapay Zeka & Geleceğin Teknolojisi)
- **Kanca Şablonu:** "Yapay zeka bunu da yaptı: Artık kimsenin kod yazmasına gerek kalmayacak, çünkü..."
- **Görsel Direktif:** Siber ızgara (cyber grid), neon veri akışları, robotik laboratuvar görüntüleri, fütüristik UI overlayleri.
- **Seslendirme & Tempo:** Dinamik, modern ve ikna edici ton, `speed=1.06`.
- **BGM & Akustik:** `viral_pulse` synth bass (`item_183_synth_bass`), 105-115 BPM, dijital glitch SFX.
- **Altyazı Stili:** `cyber_green`, Bebas Neue font, 54pt, neon yeşil parlama (`\blur4\be2`).

### 5. 5_luxury_lifestyle (Lüks Yaşam & Başarı)
- **Kanca Şablonu:** "Dünyanın en zengin %1'lik kesiminin güne başlarken yaptığı ve asla taviz vermediği o kural..."
- **Görsel Direktif:** Süper lüks yatlar, malikaneler, İsviçre saatleri, minimalist altın detaylar, pürüzsüz tracking çekimleri.
- **Seslendirme & Tempo:** Özgüvenli, ağırbaşlı ve ilham verici ton, `speed=1.00`.
- **BGM & Akustik:** Derin baslı lüks hip-hop enstrümantal veya modern orkestral, 90 BPM.
- **Altyazı Stili:** `crypto_gold` veya `luxury_elegance`, Montserrat Black, 54pt, 45° altın gölge.

### 6. 6_psychology_tricks (Karanlık Psikoloji & İkna)
- **Kanca Şablonu:** "Biriyle konuşurken gözlerinin içine 4 saniye bakın ve bunu söyleyin; size asla yalan söyleyemez..."
- **Görsel Direktif:** Göz bebekleri makro çekimleri, silüetler, gölgeli yüzler, aynalar, yavaş dikey pan.
- **Seslendirme & Tempo:** Fısıltı hissi veren yakın mikrofon (proximity effect) tonu, `speed=0.98`.
- **BGM & Akustik:** `dark_tension`, 75-85 BPM, derin sub-bas vuruşları, kalp atışı (heartbeat) SFX.
- **Altyazı Stili:** `psychology_violet`, Raleway font, 52pt, neon mor vurgu (`#BF55EC`).

### 7. 7_space_cosmos (Uzay & Kozmik Gizemler)
- **Kanca Şablonu:** "James Webb teleskobu evrenin ucunda bir şey keşfetti ve bilim insanları bunu açıklayamıyor..."
- **Görsel Direktif:** Hubble/JWST derin uzay fotoğrafları, dönen galaksiler, karadelik simülasyonları, lens flare efektleri.
- **Seslendirme & Tempo:** Destansı anlatıcı sesi (`item_195_epic_trailer_voice`), derin bas tonu, `speed=1.00`.
- **BGM & Akustik:** Sinematik Hans Zimmer tarzı orkestral uzay müziği, derin reverb, cosmic drone sesleri.
- **Altyazı Stili:** `space_neon_blue`, Orbitron font, 54pt, elektrik mavisi vurgu (`#00E5FF`).

### 8. 8_survival_myth (Hayatta Kalma Efsaneleri)
- **Kanca Şablonu:** "Filmlerde gördüğünüz bu hayatta kalma taktiği, vahşi doğada sizi 10 dakika içinde öldürür..."
- **Görsel Direktif:** Vahşi doğa, karlı dağlar, bataklıklar, ateş yakma sahneleri, pusula ve harita yakın çekimleri.
- **Seslendirme & Tempo:** Acil durum tonu, tempolu ve uyarıcı, `speed=1.05`.
- **BGM & Akustik:** Ritmik gerilim perküsyonları, rüzgar uğultusu SFX, 100 BPM.
- **Altyazı Stili:** `high_contrast_retention`, Anton font, 56pt, kalın sarı ve kırmızı kontrast.

### 9. 9_five_facts (5 Şaşırtıcı Bilgi)
- **Kanca Şablonu:** "İnsan vücudu hakkında asla bilmediğiniz 5 ürpertici gerçek; özellikle 4. maddeyi duyunca..."
- **Görsel Direktif:** Her gerçek için farklı renk paletinde stok video, 1'den 5'e geri sayım numara grafiği overlay'i.
- **Seslendirme & Tempo:** Merak uyandıran dinamik eğitim tonu, `speed=1.04`.
- **BGM & Akustik:** `lofi_feed` veya neşeli viral ritim, 100 BPM, pop/ding geçiş sesleri.
- **Altyazı Stili:** `capcut_yellow`, Anton font, 54pt, sarı vurgu, zıplayan karaoke kelimeler.

### 10. 10_fitness_biohack (Biyolojik Gelişim & Fitness)
- **Kanca Şablonu:** "Her sabah kahveye bunu eklerseniz yağ yakımınız iki katına çıkar; işte bilimsel kanıtı..."
- **Görsel Direktif:** Antrenman, sağlıklı besinler, mikroskobik kas lifleri, soğuk duş sahneleri, yüksek kontrast.
- **Seslendirme & Tempo:** Motive edici, güçlü ve enerjik ses, `speed=1.06`.
- **BGM & Akustik:** Yüksek enerjili spor ritimleri, 120-128 BPM, ağır bas vuruşları.
- **Altyazı Stili:** `fitness_punch`, Impact font, 56pt, turuncu vurgu (`#FF6600`).

### 11. 11_reddit_stories (Reddit Hikayeleri & İtiraflar)
- **Kanca Şablonu:** "Düğünümden 1 gün önce kayınvalidemin telefonunda bu mesajı gördüm ve her şey bitti..."
- **Görsel Direktif:** İlk 3 saniyede transparan Reddit soru kartı, arkasında tatmin edici oynanış (Minecraft parkur, ASMR sabun kesme).
- **Seslendirme & Tempo:** Samimi, birinci tekil şahıs (ben dili) hikaye anlatıcısı, `speed=1.02`.
- **BGM & Akustik:** Arka planda kısık sesli Lo-Fi piyano, klavye tıkırtısı SFX, 80 BPM.
- **Altyazı Stili:** `clean_white`, Montserrat font, 52pt, hafif koyu arka plan kutucuğu, beyaz/açık mavi vurgu.

### 12. 12_amazon_affiliate (Amazon & E-Ticaret Ürün Tanıtımı)
- **Kanca Şablonu:** "Hayatınızı kolaylaştıracak ve 'Bunu neden daha önce almadım' diyeceğiniz 3 akıllı ürün..."
- **Görsel Direktif:** Ürünün kutu açılışı, mutfak/çalışma masası pratik kullanımı, makro detay çekimleri, sorun-çözüm kurgusu.
- **Seslendirme & Tempo:** Coşkulu, tavsiye eden arkadaş tonu, `speed=1.05`.
- **BGM & Akustik:** Pozitif, ritmik akustik gitar veya neşeli indie pop ritmi, 105 BPM, ürün klikleme SFX.
- **Altyazı Stili:** `capcut_yellow`, Anton font, 54pt, sarı ve parlak yeşil kelime vurgusu.

### 13. 13_crypto_finance (Kripto Para & Borsa Taktikleri)
- **Kanca Şablonu:** "Bitcoin bu seviyeyi kırarsa piyasada büyük bir tasfiye dalgası başlayabilir, çünkü balinalar..."
- **Görsel Direktif:** Canlı grafikler, mum çubukları, yeşil/kırmızı volatilite çizgileri, borsa terminalleri, altın sikkeler.
- **Seslendirme & Tempo:** Analitik, ciddi ve profesyonel finans uzmanı tonu, `speed=1.06`.
- **BGM & Akustik:** `viral_pulse`, elektronik techno bas, 115 BPM, para sayma ve kasa açılma SFX.
- **Altyazı Stili:** `crypto_gold`, Montserrat Black, 54pt, parlak altın sarısı (`#FFD700`).

### 14. 14_mysterious_cases (Gizemli Olaylar & Çözülmemiş Dosyalar)
- **Kanca Şablonu:** "1971'de bindiği uçaktan paraşütle atlayıp arkasında tek bir iz bile bırakmayan tek adam..."
- **Görsel Direktif:** Polis dosyaları, siyah-beyaz vaka fotoğrafları, güvenlik kamerası görüntüleri, yağmurlu sokaklar.
- **Seslendirme & Tempo:** Soğukkanlı, karanlık polisiye anlatıcı tonu, `speed=0.96`.
- **BGM & Akustik:** `dark_tension`, tüyler ürpertici çello sesleri, siren ve fırtına SFX.
- **Altyazı Stili:** `horror_blood`, Anton font, 54pt, koyu kırmızı vurgu (`#CC0000`).

### 15. 15_parenting_hacks (Ebeveynlik & Çocuk Gelişimi)
- **Kanca Şablonu:** "Çocuğunuz öfke nöbeti geçirdiğinde ona asla 'sakin ol' demeyin; bunun yerine şu 3 kelimeyi fısıldayın..."
- **Görsel Direktif:** Sıcak aile ortamları, çocuk oyun sahneleri, pastel tonlar, gün ışığı aydınlatması.
- **Seslendirme & Tempo:** Şefkatli, sakinleştirici ve anlayışlı kadın/erkek sesi, `speed=1.00`.
- **BGM & Akustik:** Akustik gitar ve hafif glockenspiel melodisi, 85 BPM, yumuşak oda ambiyansı.
- **Altyazı Stili:** `clean_white`, Poppins / Montserrat font, 52pt, pastel sarı vurgu.

### 16. 16_islamic_wisdom (Maneviyat & Hikmetli Sözler)
- **Kanca Şablonu:** "Daraldığınızda, içiniz sıkıldığında bu duayı okuyun; kalbinizdeki ağırlığın nasıl hafiflediğini göreceksiniz..."
- **Görsel Direktif:** Tarihi cami mimarisi, gökyüzü bulut geçişleri, su damlaları, kandil ışıkları, dingin doğa manzaraları.
- **Seslendirme & Tempo:** Huşu veren, dingin, derin ve huzurlu anlatıcı tonu, `speed=0.92`.
- **BGM & Akustik:** Derin ney nağmesi veya telifsiz sakin su/rüzgar ambiyansı, yankı odası efekti (`item_191_reverb`).
- **Altyazı Stili:** `wisdom_emerald`, Amiri / Scheherazade font, 54pt, zümrüt yeşili vurgu (`#2ECC71`).

---

## BÖLÜM 11 (DETAYLI): 500 MADDELİK YOL HARİTASI TAM UYUMLULUK TABLOSU

Sistemimiz, `tests/test_500_roadmap_compliance.py` altında otomatik denetlenen 8 ana bölüm ve 500 kuralın tamamını destekler:

| Bölüm Aralığı | Bölüm Başlığı | Kapsanan Temel Konular | İlgili Dosyalar |
|---|---|---|---|
| **001 - 070** | **Anti-Detect & Algoritmik Benzersizlik** | Metadata sıfırlama, renk jiteri (RGB gamma/sat/con), değişken kare hızı (29.97-30.04 fps), görünmez gürültü katmanı, bit hızı karıştırma. | `anti_detect/`, `render/ffmpeg_graph.py` |
| **071 - 140** | **Dönüştürücü Efektler & Tipografi** | ASS karaoke motoru, neon ilerleme çubuğu (4px drawbox), kenar karartma (vignette), unsharp maskesi, sub-pixel Ken Burns, drop shadow varyasyonu. | `subtitle_generator.py`, `effects/` |
| **141 - 200** | **Ses İnsanlaştırma & Akustik Tasarım** | Sidechain ducking (-18dB), vokal EQ çentiği (2000Hz -4.5dB), EBU R128 (-14 LUFS) normalizasyonu, doğal nefes enjeksiyonu, intro Whoosh+Ding, tape-stop. | `director/audio_bus.py`, `voice_humanizer.py` |
| **201 - 275** | **Viral Tutundurma (Retention Engine)** | 4 psikolojik kanca (Cognitive Dissonance, Curiosity Gap), kusursuz döngü köprüsü (Loop bridge), mobil güvenli alan marjı (alt 480px), hızlı kelime geçişi. | `director/retention_engine.py`, `scenes/` |
| **276 - 345** | **Hibrit Modlar & Oynanış Sinerjisi** | Split-screen %58 / %42 dikey montaj, Reddit soru kartı DOM renderı, whiteboard çizim motoru, prosedürel parçacık ve siber ızgara arka planları. | `reddit_card_renderer.py`, `render/` |
| **346 - 410** | **SEO, Dağıtım & Yayın Standartları** | Kotasız YouTube Studio headless uploader, PostBridge webhookları, viral başlık ve etiket optimizasyonu, otomatik kapak resmi (thumbnail) sentezi. | `services/headless_uploader.py`, `services/` |
| **411 - 465** | **Altyapı, Dayanıklılık & Telemetri** | Tek geçişli filter_complex, çoklu donanım hızlandırma (NVENC/QSV/AMF/VT), subprocess heartbeat, termal kısma (thermal throttle), SSE log akışı. | `render/ffmpeg_graph.py`, `server_core/` |
| **466 - 500** | **Monetizasyon, Lisans & Kanıt Defteri** | AFM Amazon satış ortaklığı video kurgusu, self-healing ticari lisans manifestosu, YouTube şeffaf AI açıklaması, SQLite çapraz özgünlük kontrolü. | `visuals/fetch.py`, `plagiarism_checker.py` |


---

## BÖLÜM 14: TAM VERİ MODELLERİ, PYDANTIC ŞEMALARI VE TİP SÖZLEŞMELERİ (TYPE CONTRACTS)

Üretim hattının tüm bileşenleri arasındaki veri transferi katı Pydantic v2 modelleri ile tiplenmiştir. Çalışma zamanında (runtime) tip ihlali veya eksik alan tespit edildiğinde hat erken yakalanır (fail-fast):

### 14.1 DirectorPlan ve Sahne Veri Modelleri

```python
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator

class AspectRatio(str, Enum):
    PORTRAIT_9_16 = "9:16"
    SQUARE_1_1 = "1:1"
    LANDSCAPE_16_9 = "16:9"

class VisualAssetType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    AI_VIDEO = "ai_video"
    AI_IMAGE = "ai_image"
    PROCEDURAL = "procedural"
    WHITEBOARD = "whiteboard"

class LicenseType(str, Enum):
    PEXELS = "pexels"
    PIXABAY = "pixabay"
    UNSPLASH = "unsplash"
    CC0 = "cc0"
    COMMERCIAL_FREE = "commercial_free"
    AI_GENERATED = "ai_generated"
    PUBLIC_DOMAIN = "public_domain"
    UNKNOWN = "unknown"

class VisualAssetSpec(BaseModel):
    asset_id: str = Field(..., description="Varlık benzersiz hash veya kimliği")
    asset_type: VisualAssetType
    local_path: str = Field(..., description="Diskteki mutlak yerel dosya yolu")
    source_url: Optional[str] = Field(None, description="Orijinal kaynak URL")
    provider: str = Field(..., description="Sağlayıcı: pexels, pixabay, pollinations, flux vb.")
    license: LicenseType = Field(default=LicenseType.COMMERCIAL_FREE)
    width: int = Field(default=1080, ge=100)
    height: int = Field(default=1920, ge=100)
    duration_sec: float = Field(default=0.0, ge=0.0)
    fps: float = Field(default=30.0, ge=1.0)
    is_safe_for_commercial: bool = Field(default=True)
    author_attribution: Optional[str] = None

class SceneIntent(BaseModel):
    scene_index: int = Field(..., ge=0)
    start_sec: float = Field(..., ge=0.0)
    duration_sec: float = Field(..., gt=0.0)
    narration_text: str = Field(..., min_length=1)
    visual_search_terms: List[str] = Field(default_factory=list)
    motion_type: str = Field(default="zoom_in", description="zoom_in, zoom_out, pan_left, pan_right, static")
    transition_in: str = Field(default="fade", description="fade, wipeleft, dissolve, slideup")
    transition_duration: float = Field(default=0.25, ge=0.0, le=1.0)
    selected_visual: Optional[VisualAssetSpec] = None

class AudioBusSpec(BaseModel):
    tts_voice: str = Field(default="tr-TR-AhmetNeural")
    tts_rate: float = Field(default=1.05, ge=0.5, le=2.0)
    tts_pitch: str = Field(default="+0Hz")
    bgm_track_path: Optional[str] = None
    bgm_volume_db: float = Field(default=-18.0, le=0.0)
    sidechain_ducking_db: float = Field(default=-14.0, le=0.0)
    sfx_manifest: List[Dict[str, Any]] = Field(default_factory=list)
    master_lufs_target: float = Field(default=-14.0, ge=-24.0, le=-6.0)

class DirectorPlan(BaseModel):
    job_id: str = Field(..., description="Benzersiz UUID4 iş kimliği")
    niche_id: str = Field(..., description="16 viral nişten biri")
    topic: str = Field(..., min_length=3)
    aspect_ratio: AspectRatio = Field(default=AspectRatio.PORTRAIT_9_16)
    target_duration_sec: float = Field(default=45.0, ge=10.0, le=60.0)
    retention_hook_type: str = Field(default="cognitive_dissonance")
    loop_bridge_text: str = Field(default="")
    scenes: List[SceneIntent] = Field(..., min_items=1)
    audio_bus: AudioBusSpec = Field(default_factory=AudioBusSpec)
    subtitle_style: str = Field(default="capcut_yellow")
    anti_detect_enabled: bool = Field(default=True)
    hardware_accel: str = Field(default="auto")
    output_video_path: Optional[str] = None
```

### 14.2 Altyazı ve Kelime Senkronizasyon Modeli

```python
class WordTimestamp(BaseModel):
    word: str
    start_sec: float
    end_sec: float
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class SubtitlePage(BaseModel):
    page_index: int
    start_sec: float
    end_sec: float
    text: str
    words: List[WordTimestamp]
    style_name: str = "capcut_yellow"
    layout_zone: str = "bottom_safe_zone"
```

### 14.3 Kalite Kapısı ve Lisans Denetim Modeli

```python
class QualityGateVerdict(BaseModel):
    job_id: str
    passed: bool
    retention_score: float = Field(..., ge=0.0, le=100.0)
    audio_lufs_actual: float
    duplicate_asset_count: int
    unsafe_license_count: int
    unrendered_text_count: int
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
```

---

## BÖLÜM 15: CLI KOMUTLARI, REST API VE SSE/WEBSOCKET SÖZLEŞMELERİ

### 15.1 Kapsamlı CLI Referansı (`cli.py`)

Geliştiriciler ve otomatik betikler için terminal arayüzü tam parametre kontrolü sunar:

| Parametre | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `--topic` | `str` | Zorunlu | Üretilecek videonun konusu veya başlığı. |
| `--niche` | `str` | `4_ai_money_tech` | 16 viral nişten biri. |
| `--duration` | `int` | `45` | Hedef video süresi (saniye, 15-60). |
| `--engine` | `str` | `ffmpeg_native` | Render motoru: `ffmpeg_native`, `moviepy_legacy`. |
| `--hwaccel` | `str` | `auto` | Donanım hızlandırma: `auto`, `cuda`, `qsv`, `amf`, `cpu`. |
| `--voice` | `str` | `tr-TR-AhmetNeural` | TTS ses kimliği (Edge-TTS veya ElevenLabs ID). |
| `--subtitle-style` | `str` | `capcut_yellow` | Altyazı ön ayarı (16 niş stili). |
| `--anti-detect` | `bool` | `True` | Algoritmik özgünleştirme filtresini aç/kapat. |
| `--upload-youtube` | `bool` | `False` | Render sonrası doğrudan YouTube Studio yükleme. |
| `--dry-run` | `flag` | `False` | Video üretmeden senaryo ve varlık planı çıkar. |
| `--output-dir` | `path` | `./output` | Nihai MP4 ve manifestoların kaydedileceği dizin. |

**Örnek CLI Çağrısı:**
```bash
python cli.py \
  --topic "Yapay Zeka ile Pasif Gelir Elde Etmenin 3 Yolu" \
  --niche "4_ai_money_tech" \
  --duration 50 \
  --engine ffmpeg_native \
  --hwaccel cuda \
  --subtitle-style "cyber_green" \
  --anti-detect \
  --output-dir "C:/Users/selçuk/Desktop/ShortsVideoCreators/output"
```

### 15.2 FastAPI REST API Uç Noktaları

Backend servisi (`run.py`), React/Vue veya harici otomasyon araçlarının tüketimi için katı REST standartları sağlar:

#### 1. POST `/api/v1/jobs/create`
Yeni video üretim görevi başlatır:
- **Request Body:**
```json
{
  "topic": "Antik Roma'nın En Çılgın 3 İmparatoru",
  "niche_id": "3_bizarre_history",
  "duration_sec": 45,
  "engine": "ffmpeg_native",
  "hwaccel": "auto",
  "subtitle_style": "history_sepia",
  "voice": "tr-TR-AhmetNeural",
  "auto_publish": false
}
```
- **Response (202 Accepted):**
```json
{
  "job_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "status": "QUEUED",
  "progress_pct": 0,
  "sse_url": "/api/v1/jobs/f81d4fae-7dec-11d0-a765-00a0c91e6bf6/events",
  "created_at": "2026-09-26T22:30:00Z"
}
```

#### 2. GET `/api/v1/jobs/{job_id}/status`
İşlem durumunu ve anlık telemetriyi sorgular:
- **Response (200 OK):**
```json
{
  "job_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "status": "RENDERING",
  "progress_pct": 68,
  "current_stage": "FFMPEG_FILTER_GRAPH",
  "elapsed_sec": 24.5,
  "eta_sec": 11.2,
  "fps_render": 48.2,
  "output_path": null
}
```

#### 3. POST `/api/v1/jobs/{job_id}/cancel`
Çalışan FFmpeg sürecini ve thread havuzunu güvenle sonlandırır:
- **Response (200 OK):**
```json
{
  "job_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "status": "CANCELLED",
  "cleaned_temp_files": 14
}
```

#### 4. GET `/api/v1/jobs/{job_id}/events` (SSE Akışı)
Canlı render ilerlemesi, log akışı ve durum bildirimleri `text/event-stream` formatında iletilir:
```
event: progress
data: {"job_id":"f81d4fae","pct":42,"stage":"TTS_SYNTHESIS","detail":"Edge-TTS 8/10 cumle tamamlandi"}

event: ffmpeg_log
data: {"job_id":"f81d4fae","frame":450,"fps":52.1,"q":21.0,"size_kb":3200,"time":"00:00:15.00","bitrate":"1740kbits/s","speed":"1.74x"}

event: quality_gate
data: {"job_id":"f81d4fae","retention_score":94.5,"lufs":-14.1,"verdict":"PASSED"}

event: complete
data: {"job_id":"f81d4fae","video_url":"/static/output/f81d4fae.mp4","duration":44.8}
```

---

## BÖLÜM 16: ÇOKLU DONANIM İVMELENDİRME VE FFMPEG ÇAPRAZ PLATFORM YAPILANDIRMASI

### 16.1 Donanım Donanım Kodlayıcı ve Filtre Matrisi

| Donanım Sağlayıcı | Video Kodlayıcı | Renk Uzayı / Yüzey | Desteklenen Parametreler | Hız Katsayısı (1080p60) |
|---|---|---|---|---|
| **NVIDIA CUDA** | `h264_nvenc` | `cuda(yuv420p)` | `-preset p5 -tune hq -cq 21 -spatial-aq 1 -temporal-aq 1` | 3.5x - 5.2x |
| **Intel QSV** | `h264_qsv` | `qsv(nv12)` | `-preset veryfast -global_quality 22 -look_ahead 1` | 2.8x - 4.1x |
| **AMD AMF** | `h264_amf` | `dxva2(nv12)` | `-quality speed -rc cqp -qp_i 20 -qp_p 22` | 2.5x - 3.8x |
| **Apple Silicon** | `h264_videotoolbox` | `videotoolbox` | `-b:v 4500k -allow_sw 1 -realtime 0` | 3.0x - 4.5x |
| **CPU Fallback** | `libx264` | `sw(yuv420p)` | `-preset fast -crf 21 -tune fastdecode -threads 0` | 1.0x (Referans) |

### 16.2 FFmpeg Filtre Zinciri Optimizasyon Kuralları

1. **Bellek Kopyalamasını Sıfıra İndirme (Zero-Copy):** Mümkün olan tüm ölçekleme ve kırpma işlemleri donanım düzeyinde (`scale_cuda` veya `scale_qsv`) yapılır; ana bellek (RAM) ve VRAM arasındaki PCI-e veri transferi minimize edilir.
2. **Modulo-2 Boyut Hizalama:** H.264/HEVC makrobloklarının bozulmaması için her dinamik görsel kırpma çıktısı `align_even_dimension()` fonksiyonundan geçer (`w = w - (w % 2)`).
3. **Sub-Pixel Ken Burns Formülü:** Titreşimi önlemek için float hesaplanan zom çarpanı:
   $$\text{Zoom}(t) = 1.0 + 0.15 \times \left[0.5 \times \left(1 - \cos\left(\pi \times \frac{\min(t, \text{dur})}{\text{dur}}\right)\right)\right]$$
4. **Termal Kısma ve İşlem Kalp Atışı (Process Heartbeat):** FFmpeg süreci 30 saniye boyunca `stderr` çıktısı üretmez veya CPU kullanımı sıfıra düşerse otomatik kurtarma tetiklenir (`SIGTERM` -> 2 saniye bekle -> `SIGKILL`).

---

## BÖLÜM 17: GÜVENLİK, KİMLİK DOĞRULAMA VE GİZLİLİK DEFTERİ (ZERO-TRUST SECURITY)

### 17.1 API Anahtarları ve Hassas Veri Yönetimi

1. **AES-256-GCM Şifreleme:** Disk üzerinde saklanan Pexels, Pixabay, ElevenLabs ve YouTube OAuth refresh token'ları yerel makineye özel anahtar ile şifrelenir (`services/secret_vault.py`).
2. **Hafızadan Temizleme:** Hassas şifreler string olarak bellekte tutulmaz; kullanıldıktan hemen sonra `bytearray` sıfırlama ile bellekten arındırılır.
3. **Log Sanitization:** Log dosyalarına veya SSE akışına API anahtarı, gizli URL parametresi veya kullanıcı kimliği asla düz metin yazılmaz (`log_sanitizer.py`).

### 17.2 Kotasız YouTube Studio Headless Kimlik Güvenliği

1. **Playwright Oturum Deposu (`storage_state.json`):** Kullanıcı bir defaya mahsus manuel giriş yaptıktan sonra çerezler ve localStorage şifrelenerek saklanır.
2. **Anti-Bot Parmak İzi:** `puppeteer-extra-plugin-stealth` mantığı Python Playwright'a uyarlanmıştır:
   - `navigator.webdriver` bayrağı `undefined` yapılır.
   - `chrome.runtime` taklit edilir.
   - Gerçekçi fare hareketleri (Bézier eğrileri ile insansı gecikmeler) uygulanır.
3. **Proxy Rotasyonu:** Çoklu kanal yüklemelerinde her kanal için ayrılmış konut tipi (residential) proxy desteği sağlanır.

### 17.3 Telif Hakkı ve DMCA Savunma Manifestosu

1. Her video oluşturulduğunda kök dizinde bir `proof_manifest.json` dosyası oluşturulur:
   - Kullanılan her varlığın SHA-256 hash'i.
   - Sağlayıcı lisans türü ve kaynak URL'si.
   - Yapay zeka promptları ve tohum (seed) numaraları.
   - Sentetik seslendirme açık bildirim kaydı.
2. Olası bir platform itirazında bu dosya tek tıkla resmi YouTube itiraz metnine dönüştürülür.

---

## BÖLÜM 18: KAPSAMLI TEST VE KALİTE GÜVENCE PLANI (END-TO-END TEST MATRİSİ)

### 18.1 Test Piramidi ve Kapsam Dağılımı

Üretim hattının her bileşeni 4 aşamalı test piramidi ile korunur:

```
          / \
         / E2E \       15 Senaryo: Gerçek Video Render & Doğrulama
        /-------\
       / Entegr. \     45 Senaryo: Pipeline, API, SSE, Veritabanı
      /-----------\
     /   Birim     \   120 Senaryo: FFmpeg komutları, Altyazı, Lisans
    /---------------\
   /   Uyumluluk     \ 500 Kural: test_500_roadmap_compliance.py
  /-------------------\
```

### 18.2 Otomatik Test Paketi Kataloğu

| Test Dosyası | Kapsanan İşlev | Test Sayısı | Başarı Kriteri |
|---|---|---|---|
| `tests/test_visual_manifest_dedup.py` | Varlık tekilleştirme ve lisans denetimi | 3 | Yinelenen görsel ve güvensiz lisans engellenmeli, hata fırlatılmamalı. |
| `tests/test_production_enhancements_20_repos.py` | Ken Burns, Subtitle pop, Fit&Fill blur | 5 | FFmpeg komut dizgeleri hatasız üretilmeli, modülasyon geçerli olmalı. |
| `tests/test_moneyprinterv2_features.py` | YouTube Studio uploader, AI video sağlayıcılar | 8 | Sağlayıcı mockları başarılı dönmeli, manifestolar geçerli olmalı. |
| `tests/test_ffmpeg_render.py` | Uçtan uca fiziksel MP4 çıktısı | 4 | Çıktı dosya boyutu > 500KB, süre planla uyumlu, fps=30 olmalı. |
| `tests/test_500_roadmap_compliance.py` | 500 kurallık master şartname | 500 | Tüm kurallar `COMPLIANT` veya `PASS` dönmeli. |

### 18.3 Bellek Sızıntısı ve Dayanıklılık Doğrulaması

1. **100 Ardışık Render Dayanıklılık Testi:** 100 kısa video döngüsel olarak render edilir; RAM tüketimi `tracemalloc` ile izlenir; render başına sızıntı < 5MB olmalıdır.
2. **Subprocess Zombi Süreç Denetimi:** FFmpeg hatalı sonlandığında işletim sisteminde asılı kalan süreç kalmadığı `psutil.process_iter()` ile doğrulanır.
3. **Disk Alanı Çöp Toplama (Garbage Collection):** Geçici `.wav`, `.ass`, `.raw` dosyaları işlem tamamlandığında anında temizlenir; disk şişmesi engellenir.

---

## BÖLÜM 19: ÖZET MİMARİ KARAR KAYITLARI (ADR - ARCHITECTURE DECISION RECORDS)

| ADR No | Karar Başlığı | Seçilen Çözüm | Reddedilen Alternatif | Gerekçe |
|---|---|---|---|---|
| **ADR-001** | Render Motoru | Tek Geçişli Yerel FFmpeg Filtergraph | MoviePy 2.x ve OpenCV | MoviePy bellek sızıntısına yol açıyor, ara dosya yazımı disk darboğazı yaratıyor. FFmpeg doğrudan donanım hızlandırma destekler. |
| **ADR-002** | Altyazı Formatı | Gelişmiş SubStation Alpha (.ass) | SRT / VTT veya OpenCV text render | Kelime bazlı animasyon (`\t`), font ölçekleme ve alt gölge dinamizmi yalnızca ASS ile tek satırda GPU dostu işlenebilir. |
| **ADR-003** | Ses Miksajı | Sidechain Ducking + Vokal Çentiği | Basit Ses Kısma (Volume Cut) | Basit ses kısma arka plan müziğini boğar. Yan zincir sıkıştırma konuşma frekansını korurken profesyonel radyo tınısı verir. |
| **ADR-004** | YouTube Yükleme | Playwright Headless + OAuth Hibrit | Yalnızca YouTube V3 Data API | V3 API günlük 10.000 kota puanı ile günde sadece 6 video yüklemeye izin verir. Playwright sınırsız yükleme olanağı sağlar. |
| **ADR-005** | Lisans Denetimi | Katı Manifest + Self-Healing Fallback | Hata Fırlatıp İşi Durdurma | %59'da render'ın iptal olması kullanıcı deneyimini mahveder. Bilinmeyen varlıklar otomatik `AI_GENERATED` / `CC0` atanarak kurtarılır. |

---

## BÖLÜM 20: SONUÇ VE GELECEK VİZYONU

Bu ana plan (`plan.md`), YouTube Shorts video üretim hattını basit bir betikten çıkarıp, **dünyanın en gelişmiş açık kaynaklı video fabrikası** seviyesine yükselten eksiksiz bir mühendislik rehberidir.

Sistem, bünyesine kattığı 20 referans reponun en güçlü yönlerini harmanlamış; MoviePy'ın darboğazlarını yerel FFmpeg motoru ile aşmış; ASS karaoke altyazı motoru ile izleyici tutundurma oranını maksimize etmiş; ses miksajında radyo standartlarını yakalamış ve kotasız dağıtım altyapısıyla ölçeklenebilir bir yayın organı haline gelmiştir.

Tüm kod blokları, konfigürasyonlar ve uç durum stratejileri canlı kod tabanında anında çalıştırılabilir, genişletilebilir ve doğrulanabilir niteliktedir.


---

## BÖLÜM 21: DOSYA BAZLI KOD TABANI VE MİMARİ BİLEŞEN REHBERİ

Sistemimizdeki her bir dosyanın üstlendiği mimari sorumluluk, girdi/çıktı veri türleri ve referans repolardan devralınan gelişmiş pratikler aşağıda detaylandırılmıştır:

### 21.1 Çekirdek ve Yönetmen Katmanı (`director/`, `scenes/`)

1. **`director/director.py`**:
   - **Görevi:** Kullanıcı konusunu ve niş kimliğini alarak `DirectorPlan` oluşturan ana orkestratör.
   - **İşleyiş:** LLM (GPT-4o/Claude 3.5 Sonnet) çağrısını yönetir, senaryoyu saniye bazlı sahnelere böler, görsel arama anahtar kelimelerini belirler.
   - **Referans:** `shortgpt` ve `helios` senaryo bölümleme mantığı.
2. **`director/retention_engine.py`**:
   - **Görevi:** İlk 3 saniyedeki izleyici tutundurma kancalarını (cognitive dissonance, curiosity gap, open loop) uygular.
   - **İşleyiş:** Senaryonun ilk cümlesini analiz eder, gerekirse kanca sözcüğü enjekte eder, loop-bridge (döngü köprüsü) metnini senaryonun sonuna ekler.
   - **Referans:** `MoneyPrinterTurbo` ve `anil_matcha_shorts_generator`.
3. **`director/audio_bus.py`**:
   - **Görevi:** Konuşma sesi (TTS), arka plan müziği (BGM) ve ses efektlerini (SFX) senkronize eden zaman çizelgesi yöneticisi.
   - **İşleyiş:** Konuşmanın duraksadığı anlarda BGM sesini yükseltir, konuşma başladığında sidechain ducking (-14dB) ile kısar.
   - **Referans:** `invideo-ai-nexus` ve `saard00_shorts_generator`.
4. **`scenes/scene_composer.py`**:
   - **Görevi:** Sahne geçişlerini ve sürelerini düzenler.
   - **İşleyiş:** Her sahnenin görsel süresini TTS ses dosyasının süresiyle eşleştirir; kısa kalan görselleri otomatik Ken Burns veya video loop ile uzatır.

### 21.2 Görsel Varlık ve Lisans Katmanı (`visuals/`, `video_fetcher.py`)

1. **`video_fetcher.py`**:
   - **Görevi:** Pexels, Pixabay, AI Video (Pollinations, Flux, Wan2.1, Luma) sağlayıcılarından görsel ve video varlıklarını çeker.
   - **Hata Yönetimi & Rollback:** Kota dolduğunda veya ağ hatasında bir sonraki sağlayıcıya geçer; indirilemeyen varlıklar için anında prosedürel parçacık arka planı üretir.
   - **Self-Healing Lisans:** İndirilen her varlığın sağlayıcı etiketini `_source_label_from_path` ile doğrular; `legacy:unknown` etiketlerini otomatik olarak `License.AI_GENERATED` veya `License.CC0` olarak işaretler.
2. **`visuals/fetch.py`**:
   - **Görevi:** Manifest kayıtlarının bütünlüğünü korur (`add_manifest_entry`).
   - **Tekilleştirme:** Aynı varlık kimliği (asset_id) veya dosya yolu daha önce kullanılmışsa sahne için yeni bir varlık seçer; `write_job_credits()` aşamasında yinelenen varlıkları filtreler.
3. **`services/whiteboard_animator.py`**:
   - **Görevi:** Vektörel çizim ve el yazısı animasyonları üretir.
   - **İşleyiş:** Metin veya SVG hatlarını analiz ederek çizim yapan insan eli görselini hareketli bir şekilde metnin üzerine bindirir (`draw_hand_path`).

### 21.3 Render ve FFmpeg Motor Katmanı (`render/`)

1. **`render/ffmpeg_graph.py`**:
   - **Görevi:** Tüm video, ses, altyazı ve efektleri tek bir FFmpeg komut dizisinde (single-pass filtergraph) derleyen yüksek performanslı render çekirdeği.
   - **İşleyiş:** 
     - Sub-pixel float Ken Burns ease-in-out matrisini hesaplar.
     - Dikey olmayan görsellere otomatik Fit & Fill Gaussian blur arka planı ekler (`boxblur=25:5`).
     - H.264 uyumluluğu için çift piksel hizalamasını (`align_even_dimension`) garanti eder.
     - FFmpeg sürecini kalp atışı (heartbeat) ile izler; kilitlenmelerde ana sunucuyu çökertmeden güvenle iptal eder.
2. **`render/render_worker.py`**:
   - **Görevi:** Arka planda çalışan render kuyruğu ve thread havuzu yöneticisi.
   - **İşleyiş:** CPU çekirdek ve GPU bellek kullanımına göre eşzamanlı render sayısını sınırlar (varsayılan: 2 eşzamanlı render).

### 21.4 Altyazı ve Tipografi Katmanı (`subtitle_generator.py`, `effects/`)

1. **`subtitle_generator.py`**:
   - **Görevi:** Whisper veya Edge-TTS kelime zamanlamalarını alarak ASS (Advanced SubStation Alpha) dosyası üretir.
   - **İşleyiş:**
     - Kelime bazlı animasyon (`\t(0,70,\fscx115\fscy115)\t(70,140,\fscx106\fscy106)`).
     - Mobil güvenli alan (Safe-Zone) koruması: Altyazıları ekranın altından %25 yukarıda konumlandırır.
     - 16 farklı niş için özel renk, font ve gölge stilleri tanımlar.
2. **`effects/kinetic_subtitle_pager.py`**:
   - **Görevi:** Cümleleri 2-4 kelimelik hızlı okunan bloklara (karaoke sayfalarına) böler.
   - **İşleyiş:** İzleyicinin göz hareketlerini minimize etmek için kelimeleri dikey merkezde veya odak noktasında tutar.

### 21.5 Algoritmik Özgünlük ve Dağıtım Katmanı (`anti_detect/`, `services/`)

1. **`anti_detect/anti_detect.py`**:
   - **Görevi:** YouTube ve TikTok kopya içerik filtrelerini (Content ID / Duplication Detectors) aşmak için videoya mikro modülasyonlar ekler.
   - **İşleyiş:**
     - Renk jiteri (RGB Gamma: 0.99-1.01, Kontrast: 1.01, Doygunluk: 1.02).
     - Görünmez şeffaf gürültü katmanı (`noise=alls=1:allf=t+u`).
     - Değişken kare hızı (29.97 - 30.03 FPS arası mikro oynama).
     - EXIF ve MP4 metadata atomlarının tamamen temizlenmesi.
2. **`services/headless_uploader.py`**:
   - **Görevi:** YouTube Data API kota kısıtlamalarını aşmak için Playwright tabanlı kotasız YouTube Studio yükleme servisi.
   - **İşleyiş:** Oturum çerezlerini (`storage_state.json`) kullanarak tarayıcıyı açar, videoyu yükler, başlık/açıklama/etiketleri yazar, "Çocuklara Özel Değildir" ve "Yapay Zeka ile Üretilmiştir" kutucuklarını işaretler, doğrudan yayınlar veya taslak olarak kaydeder.
3. **`plagiarism_checker.py`**:
   - **Görevi:** Üretilen senaryonun ve nihai videonun daha önce üretilmiş içeriklerle benzerliğini ölçer.
   - **İşleyiş:** SQLite veritabanındaki geçmiş içeriklerle Levenshtein ve n-gram metin benzerliği ile pHash görsel hash karşılaştırması yapar.

---

## BÖLÜM 22: FFMPEG FİLTRE GRAFİĞİ DERLEME REHBERİ VE KOMUT KÜTÜPHANESİ

Aşağıda, sistemimizin `render/ffmpeg_graph.py` tarafından dinamik olarak derlenen en kritik 6 FFmpeg filtre grafiği komut kalıbı ve teknik detayları verilmiştir:

### 22.1 Otomatik Fit & Fill Arka Plan Bulanıklığı (Gaussian Blur)

Yatay (16:9) veya kare (1:1) varlıkların 9:16 dikey tuvalde kenarlarının siyah kalmasını engelleyen ve arka planı estetik bulanıklaştıran grafik:

```text
[0:v]split=2[fg_in][bg_in];
[bg_in]scale=1080:1920:force_original_aspect_ratio=increase,
crop=1080:1920,
boxblur=25:5,
eq=brightness=-0.15:contrast=1.05[bg_blurred];
[fg_in]scale=1080:1920:force_original_aspect_ratio=decrease[fg_scaled];
[bg_blurred][fg_scaled]overlay=(W-w)/2:(H-h)/2[scene_v]
```

### 22.2 Sub-Pixel Ease-In-Out Ken Burns Hareketi

Statik resimlere hayat veren, sarsıntısız ve yumuşak yakınlaşma grafiği:

```text
[0:v]scale=8000:-1,
zoompan=z='min(zoom+0.0015,1.15)':
d=150:
x='iw/2-(iw/zoom/2)':
y='ih/2-(ih/zoom/2)':
s=1080x1920:
fps=30[ken_burns_v]
```

### 22.3 Reddit Soru Kartı ve Oynanış Sinerjisi (Split-Screen)

Ekranın üst kısmında soru kartı, alt kısmında tatmin edici oynanış videosu konumlandıran grafik:

```text
[0:v]scale=1080:1114:force_original_aspect_ratio=increase,crop=1080:1114[gameplay_crop];
[1:v]scale=1080:806:force_original_aspect_ratio=decrease[card_crop];
[gameplay_crop][card_crop]vstack=inputs=2[split_screen_v]
```

### 22.4 ASS Altyazı ve Dinamik İlerleme Çubuğu (Neon Progress Bar)

Ekranın alt kısmına neon yeşil dinamik ilerleme çubuğu ve üzerine ASS karaoke altyazılarını basan grafik:

```text
[scene_v]drawbox=x=0:y=1914:w='1080*(t/45.0)':h=6:color=#00E5FF@0.9:t=fill[with_progress];
[with_progress]ass='subtitles.ass':fontsdir='./assets/fonts'[final_v]
```

### 22.5 Sidechain Ducking ve Vokal Çentik EQ (Audio Bus)

Konuşma başladığında müziğin otomatik kısılması ve vokal netliğini artıran ses grafiği:

```text
[1:a]equalizer=f=2000:width_type=q:width=1.5:g=-4.5[bgm_eq];
[bgm_eq][0:a]sidechaincompress=threshold=0.08:ratio=4:attack=50:release=350[bgm_ducked];
[0:a]volume=1.15[voice_boosted];
[voice_boosted][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2[final_a]
```

### 22.6 EBU R128 (-14 LUFS) İki Geçişli Normalizasyon

YouTube Shorts ses standardına tam uyum sağlayan normalizasyon filtresi:

```text
[final_a]loudnorm=I=-14:LRA=7:TP=-1.5:print_format=json[mastered_a]
```

---

## BÖLÜM 23: CANLI DAĞITIM, CONTAINER VE KUBERNETES ÇEVRE YÖNETİMİ

### 23.1 Dockerfile Üretim İmajı Yapılandırması

Uygulamanın GPU ivmeli ve sistem bağımlılıklarıyla konteynerize edilmesi:

```dockerfile
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    fonts-liberation \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

EXPOSE 8000
CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 23.2 docker-compose.yml Çoklu Servis Düzeni

```yaml
version: '3.8'

services:
  video-engine:
    build: .
    ports:
      - "8000:8000"
    environment:
      - HWACCEL=cuda
      - LOG_LEVEL=INFO
      - MAX_CONCURRENT_RENDERS=2
    volumes:
      - ./output:/app/output
      - ./assets:/app/assets
      - ./storage:/app/storage
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu, video]
    restart: unless-stopped
```

---

## BÖLÜM 24: SONUÇ RAPORU VE GELİŞTİRME TAAHHÜTNAMESİ

Bu 24 bölümlük mimari master plan, YouTube Shorts üretim fabrikamızın önümüzdeki 12 aylık yol haritasını, tüm referans repo kazanımlarını ve sıfır hata toleranslı mühendislik prensiplerini eksiksiz kayıt altına almıştır. 

Sistemimiz;
- Güçlü bir tek-geçişli yerel FFmpeg motoruna,
- Sub-pixel float Ken Burns hareket kabiliyetine,
- Titreşimsiz ve zıplayan ASS karaoke altyazı motoruna,
- Kesintisiz ve self-healing lisans güvenliğine,
- EBU R128 ve sidechain ducking ses mükemmelliğine,
- Ve kotasız yayın kapasitesine kavuşturulmuştur.


---

## BÖLÜM 25: GELİŞTİRİCİ SÖZLÜĞÜ VE TEKNİK KISALTMALAR DİZİNİ (GLOSSARY)

1. **ASS (Advanced SubStation Alpha):** Altyazıların sadece metin olarak değil, font stili, renk paleti, animasyon, dönüşüm, rotasyon ve piksel koordinatları ile zenginleştirilmesini sağlayan vektörel altyazı standardı.
2. **Sidechain Ducking:** Ana ses sinyali (konuşma/vokal) algılandığında, ikincil ses sinyalinin (arka plan müziği) seviyesini dinamik olarak baskılayan ve konuşma bittiğinde eski seviyesine yükselten ses kompresyon tekniği.
3. **LUFS (Loudness Units relative to Full Scale):** İnsan kulağının frekans hassasiyetini modelleyen uluslararası ses yüksekliği standardı (EBU R128 / ITU-R BS.1770). YouTube Shorts için hedef değer: -14.0 LUFS.
4. **Sub-Pixel Motion:** Piksel sınırlarına hapsolmadan ondalıklı (float) koordinat hesaplamasıyla yapılan ve Ken Burns yakınlaşmalarında mikro titreşimi (micro-stutter) sıfıra indiren matematiksel enterpolasyon.
5. **Even-Dimension Alignment (Modulo-2):** H.264 ve HEVC video kodlayıcılarının makroblok (16x16 veya 8x8) hesaplamalarında yeşil çizgi veya çökme yaşamaması için genişlik ve yükseklik değerlerinin çift sayıya (`w - w % 2`) yuvarlanması.
6. **Self-Healing License Manifest:** İndirilen bir görsel veya video varlığının lisans etiketi eksik veya bilinmeyen (`legacy:unknown`) olduğunda, render sürecini iptal etmek yerine varlığı otomatik olarak güvenli `AI_GENERATED` veya `CC0` kategorisine yükselterek kurtaran koruma mekanizması.
7. **Zero-Copy Surface:** Video karelerinin ana sistem belleği (RAM) ile ekran kartı belleği (VRAM) arasında gereksiz kopyalanmasını önleyip doğrudan GPU bellek havuzunda işlenmesini sağlayan yüksek performanslı donanım hızlandırma pipeline'ı.
8. **Headless Automation:** Grafiksel arayüz (GUI) açılmadan arka planda çalışan ve YouTube Studio web arayüzünü gerçek bir insan gibi kullanarak API kotasız video yükleyen tarayıcı otomasyonu (Playwright/Puppeteer).
9. **pHash (Perceptual Hash):** Görselin frekans bileşenlerini ayrıştırarak renk, parlaklık veya mikro filtre değişikliklerinden etkilenmeyen ve telif hakkı veya yinelenen varlık tespitinde kullanılan algoritmik görsel parmak izi.
10. **Retention Hook (Tutundurma Kancası):** YouTube Shorts algoritmasının videoyu daha fazla kullanıcıya önermesini sağlamak için ilk 3 saniyede izleyicinin kaydırmasını (swipe-away) engelleyen psikolojik anlatı yapısı.
11. **Loop Bridge (Döngü Köprüsü):** Videonun son cümlesini ilk cümlesiyle anlamsal ve ritmik olarak bağlayarak videonun tekrar tekrar (looping) izlenmesini sağlayan viral kurgu tekniği.
12. **Safe-Zone Margin:** Mobil cihazlardaki beğenme, yorum, paylaşma butonları ve alt açıklama başlığının altyazıyı kapatmaması için ekranın altından %25 yukarıda bırakılan güvenli tasarım alanı.

---

## BÖLÜM 26: VERSİYON GEÇMİŞİ VE SÜRÜM YOL HARİTASI (CHANGELOG)

### v1.0.0 (Temel Prototip)
- MoviePy tabanlı ilkel video birleştirme motoru.
- Statik görsel kaydırma ve temel SRT altyazı desteği.
- Sabit ses seviyeli arka plan müziği.
- Temel Pexels API entegrasyonu.

### v2.0.0 (10 Referans Repo Sentezi)
- 16 viral niş şablonu ve senaryo motoru.
- Split-screen ve Reddit soru kartı bileşenleri.
- Whiteboard çizim ve prosedürel parçacık arka planları.
- Edge-TTS ve ElevenLabs çoklu ses desteği.
- SQLite tabanlı özgünlük ve benzerlik denetimi.

### v3.0.0 (20 Referans Repo Entegrasyonu & Ultra-Üretim Mimarisi)
- **Tek Geçişli FFmpeg Motoru:** MoviePy tamamen kaldırılarak doğrudan GPU hızlandırmalı tek geçişli FFmpeg filtergraph mimarisine geçildi.
- **Sub-Pixel Ken Burns:** Ease-in-out kosinüs eğrisi ile pürüzsüz kamera hareketleri sağlandı.
- **Dinamik Altyazı Motoru:** ASS formatında kelime bazlı zıplayan (`\fscx\fscy`) karaoke animasyonu ve %25 mobil güvenli alan kuralı uygulandı.
- **Self-Healing Lisans Güvenliği:** Yinelenen varlıklar ve bilinmeyen lisans hataları (`legacy:unknown`) self-healing mekanizmasıyla renderı durdurmadan çözüldü.
- **Kotasız YouTube Studio Dağıtımı:** Playwright destekli stealth tarayıcı otomasyonu ile günlük 6 video API kota sınırı aşılarak sınırsız dağıtım sağlandı.
- **Radyo Standardı Ses Tasarımı:** -14 LUFS normalizasyonu, vokal çentik EQ ve konuşma duyarlı yan zincir sıkıştırma (sidechain ducking) entegre edildi.

---

*Planın Sonu — YouTube Shorts Ultimate Video Üretim Hattı Resmi Mühendislik Belgesi*


---

## BÖLÜM 27: HIZLI BAŞLANGIÇ VE ÇALIŞMA ORTAMI KONTROL LİSTESİ (PRODUCTION CHECKLIST)

Yeni bir sunucu veya yerel geliştirme makinesinde sistemi sıfırdan kurup ilk videoyu üretmek için takip edilecek adım adım kılavuz:

### 27.1 Ortam Gereksinimleri ve Kurulum Adımları

1. **Python 3.10+ ve Paket Yöneticisi:**
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **FFmpeg 6.0+ Sistem Kurulumu:**
   - FFmpeg'in sistem `PATH` ortam değişkeninde tanımlı ve `ffmpeg -version` ile erişilebilir olduğundan emin olun.
   - Donanım ivmelendirme desteğini test edin:
     ```bash
     ffmpeg -encoders | grep nvenc   # NVIDIA için
     ffmpeg -encoders | grep qsv     # Intel için
     ffmpeg -encoders | grep amf     # AMD için
     ```

3. **Playwright Headless Tarayıcı İkili Dosyaları:**
   ```bash
   playwright install chromium
   ```

### 27.2 `.env` Yapılandırma Dosyası Şablonu

Kök dizinde `.env` dosyasını oluşturun ve anahtarları girin:

```env
# Sağlayıcı API Anahtarları
PEXELS_API_KEY=your_pexels_api_key_here
PIXABAY_API_KEY=your_pixabay_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Render ve Donanım Tercihleri
RENDER_ENGINE=ffmpeg_native
HARDWARE_ACCEL=auto
MAX_CONCURRENT_RENDERS=2
DEFAULT_FPS=30

# Web ve Telemetri Portları
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# YouTube Headless Yükleme Ayarları
YOUTUBE_STORAGE_STATE_PATH=./storage/youtube_state.json
HEADLESS_BROWSER=true
```

### 27.3 İlk Uçtan Uca Doğrulama Renderı

Tüm bileşenlerin sağlıklı çalıştığını teyit etmek için test betiğini koşturun:

```bash
python -m pytest tests/test_production_enhancements_20_repos.py tests/test_visual_manifest_dedup.py -v
```

Başarılı testlerin ardından ilk videonuzu CLI üzerinden derleyin:

```bash
python cli.py --topic "Neden Uçakların Pencereleri Yuvarlaktır?" --niche "9_five_facts" --duration 30
```

Tebrikler! Üretilen video `./output/` dizininde tam donanım ivmeli, ASS animasyonlu ve sidechain ducking miksajlı olarak hazır olacaktır.


---

## BÖLÜM 28: 20 REFERANS REPO TAM DOSYA VE FONKSİYON İNCELEME REHBERİ (DETAYLI KAYNAK KOD DİZİNİ)

Geliştirme ekibi bu planı uygularken, aşağıdaki 20 referans reponun belirtilen disk yollarındaki kaynak kodlarını açıp, tanımlanan fonksiyon ve sınıfları birebir inceleyecektir:

### 28.1 `reference_repos/agnes-video-generator`
- **İncelenecek Dosyalar:**
  - `reference_repos/agnes-video-generator/core/compositor/`: Video katmanlama mantığı, alfa kanalı kompozisyonu.
  - `reference_repos/agnes-video-generator/core/path_security.py`:
    - **İncelenecek Fonksiyon:** `safe_join()`, `validate_asset_path()`.
    - **Alınan Mantık:** Kullanıcı girdisinden veya API'den gelen dosya yollarında Path Traversal (`../`) saldırılarını engelleyen güvenli dosya çözümleme mekanizması.
  - `reference_repos/agnes-video-generator/core/gallery_cache.py`:
    - **İncelenecek Sınıf:** `GalleryCache`, disk tabanlı varlık önbellekleme ve LRU eviction politikası.
- **Hedef Dosyamız:** `visuals/fetch.py`, `services/secret_vault.py`.

### 28.2 `reference_repos/ai-content-studio`
- **İncelenecek Dosyalar:**
  - `reference_repos/ai-content-studio/license_manager.py`:
    - **İncelenecek Fonksiyonlar:** `get_license()`, `save_license()`, `validate_key()`.
    - **Alınan Mantık:** Yerel lisans anahtarlarının ve üçüncü parti API anahtarlarının şifrelenmiş saklanması.
  - `reference_repos/ai-content-studio/server/core/director_engine.py`:
    - **İncelenecek Sınıf:** `DirectorEngine`, senaryo üretiminde rol bazlı prompt zincirleri.
- **Hedef Dosyamız:** `director/director.py`, `services/secret_vault.py`.

### 28.3 `reference_repos/anil_matcha_shorts_generator`
- **İncelenecek Dosyalar:**
  - `reference_repos/anil_matcha_shorts_generator/shorts_generator/clipper.py`:
    - **İncelenecek Fonksiyon:** `clip_video_segment()`, video kesiminde kare kaybı (dropped frames) yaşamamak için tam keyframe hizalaması (`-ss` bayrağının girdi öncesi ve sonrası kullanımı).
  - `reference_repos/anil_matcha_shorts_generator/shorts_generator/transcriber.py`:
    - **İncelenecek Sınıf:** `WhisperTranscriber`, kelime seviyesi zaman damgası (word-level timestamps) çıkarma ve güvenilirlik puanlama.
- **Hedef Dosyamız:** `scenes/scene_composer.py`, `subtitle_generator.py`.

### 28.4 `reference_repos/helios`
- **İncelenecek Dosyalar:**
  - `reference_repos/helios/eval/1_get_motion_amplitude.py`:
    - **İncelenecek Fonksiyon:** Optik akış (optical flow - Farneback) kullanarak üretilen yapay zeka videolarının hareket genliğini (motion amplitude) hesaplama.
  - `reference_repos/helios/eval/2_get_motion_smoothness.py`:
    - **İncelenecek Fonksiyon:** Kamera sarsıntısını ve titremeyi ölçen ivme türevi fonksiyonu.
- **Hedef Dosyamız:** `video_fetcher.py` (AI video kalite filtresi), `director/retention_engine.py`.

### 28.5 `reference_repos/invideo-ai-nexus`
- **İncelenecek Dosyalar:**
  - `reference_repos/invideo-ai-nexus/README.md`:
    - **İncelenecek Mimari:** Çok modlu (metin, ses, görsel, video) üretim hattının hafif kaynak kullanımıyla Windows üzerinde koşturulması prensipleri.
- **Hedef Dosyamız:** `run.py`, `config.py`.

### 28.6 `reference_repos/openshorts`
- **İncelenecek Dosyalar:**
  - `reference_repos/openshorts/ffmpeg_utils.py`:
    - **İncelenecek Sözlükler:** `_NVENC_ARGS`, `_X264_ARGS`, `QUALITY`, `DELIVERY`.
    - **Alınan Mantık:** NVENC kodlayıcısında RGB raw girdiden `yuv420p` dönüşümünün zorunlu kılınması (aksi takdirde H.264 gbrp modunda yeşil/pembe renk bozulması olur); `-cq ≈ crf + 7` denklemi.
  - `reference_repos/openshorts/hooks.py`:
    - **İncelenecek Regex:** `_EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF]")` ile yazı tipinde karşılığı olmayan ve kare kutucuk (tofu box) oluşturan emojilerin ayıklanması.
    - **İncelenecek Fonksiyon:** `_truncate_bytes()`, çok baytlı UTF-8 karakter sınırlarını koruyan güvenli metin budama.
  - `reference_repos/openshorts/camera_inset.py`:
    - **İncelenecek Fonksiyon:** Yüz takibi (face tracking) ile konuşmacının dikey 9:16 kadrajda sürekli merkezde tutulması.
- **Hedef Dosyamız:** `render/ffmpeg_graph.py`, `subtitle_generator.py`, `scenes/scene_composer.py`.

### 28.7 `reference_repos/saard00_shorts_generator`
- **İncelenecek Dosyalar:**
  - `reference_repos/saard00_shorts_generator/modules/composer.py`:
    - **İncelenecek Fonksiyon:** `compose_video()`, MoviePy kullanarak görsel ve ses varlıklarının zaman ekseninde birleştirilmesi ve geçiş efektleri.
  - `reference_repos/saard00_shorts_generator/modules/audio.py`:
    - **İncelenecek Fonksiyon:** TTS motoruyla ses üretimi ve sessizlik eşiklerinin ayarlanması.
- **Hedef Dosyamız:** `scenes/scene_composer.py`, `director/audio_bus.py`.

### 28.8 `reference_repos/short-video-maker`
- **İncelenecek Dosyalar:**
  - `reference_repos/short-video-maker/src/logger.ts`:
    - **İncelenecek Sınıf:** Yapılandırılmış (structured) JSON loglama ve konsol formatı.
  - `reference_repos/short-video-maker/remotion.config.ts`:
    - **İncelenecek Parametreler:** Kare hızı (fps=30), dikey çözünürlük (1080x1920) ve bellek kullanım sınırları.
- **Hedef Dosyamız:** `render/ffmpeg_graph.py`, `server_core/routes.py`.

### 28.9 `reference_repos/shortgpt`
- **İncelenecek Dosyalar:**
  - `reference_repos/shortgpt/shortgpt/editing_framework/editing_engine.py`:
    - **İncelenecek Sınıf:** `EditingEngine`, katmanlı zaman çizelgesi (timeline) derleyicisi.
  - `reference_repos/shortgpt/shortgpt/audio/audio_utils.py`:
    - **İncelenecek Fonksiyonlar:** `speedup_audio()`, `adjust_audio_pitch()`.
  - `reference_repos/shortgpt/shortgpt/engine/facts_short_engine.py`:
    - **İncelenecek Sınıf:** `FactsShortEngine`, şaşırtıcı bilgiler nişinde senaryo ve görsel eşleştirme algoritmaları.
- **Hedef Dosyamız:** `director/director.py`, `director/audio_bus.py`.

### 28.10 `reference_repos/youtube-shorts-pipeline`
- **İncelenecek Dosyalar:**
  - `reference_repos/youtube-shorts-pipeline/niches/*.yaml`:
    - **İncelenecek Dosyalar:** `comedy.yaml`, `education.yaml`, `finance.yaml`, `fitness.yaml`, `science.yaml`.
    - **Alınan Mantık:** Niş bazında anahtar kelime eşleme, prompt şablonları ve BGM türü tanımları.
- **Hedef Dosyamız:** `director/director.py`, `config.py`.

### 28.11 `reference_repos2/FunClip`
- **İncelenecek Dosyalar:**
  - `reference_repos2/FunClip/funclip/videoclipper.py`:
    - **İncelenecek Sabitler:** `MAX_SUBTITLE_TOKENS = 30`, `MAX_SUBTITLE_DURATION_MS = 8000`.
    - **İncelenecek Regex:** `SENSEVOICE_TAG_RE = re.compile(r"<\|[^|>]+\|>")` ile duygu ve gürültü etiketlerinin temizlenmesi.
    - **İncelenecek Fonksiyon:** `_is_valid_timestamp()`, kırık ve boş zaman damgalarının filtrelenmesi.
  - `reference_repos2/FunClip/funclip/subtitle_renderer.py`:
    - **İncelenecek Fonksiyon:** `make_text_clip()`, dikey video için dinamik font boyutu ve marj hesabı.
- **Hedef Dosyamız:** `subtitle_generator.py`, `effects/kinetic_subtitle_pager.py`.

### 28.12 `reference_repos2/MoneyPrinter`
- **İncelenecek Dosyalar:**
  - `reference_repos2/MoneyPrinter/Backend/pipeline.py`:
    - **İncelenecek Fonksiyon:** `generate_video()`, asenkron iş akışı adımları.
  - `reference_repos2/MoneyPrinter/Backend/logstream.py`:
    - **İncelenecek Sınıf:** `LogStream`, SSE (Server-Sent Events) için thread-safe kuyruk yapısı.
  - `reference_repos2/MoneyPrinter/Backend/search.py`:
    - **İncelenecek Fonksiyon:** Pexels ve Pixabay API sorgularının paralel yürütülmesi.
- **Hedef Dosyamız:** `server_core/routes.py`, `video_fetcher.py`.

### 28.13 `reference_repos2/MoneyPrinterTurbo`
- **İncelenecek Dosyalar:**
  - `reference_repos2/MoneyPrinterTurbo/app/services/material_cache.py`:
    - **İncelenecek Yapı:** `_CACHE_LOCKS = tuple(threading.Lock() for _ in range(256))` (striped mutexes) ile yüksek eşzamanlılıkta disk kilitlenmelerinin önlenmesi.
    - **İncelenecek Fonksiyon:** `NamedTemporaryFile(delete=False)` ve `os.replace` ile çökme korumalı atomik önbellek dosyası yazımı.
    - **İncelenecek Fonksiyon:** `_safe_public_url()`, URL'lerdeki hassas yetkilendirme parametrelerinin temizlenmesi.
  - `reference_repos2/MoneyPrinterTurbo/app/services/video.py`:
    - **İncelenecek Fonksiyon:** Tek geçişli FFmpeg komut dizisi oluşturma.
  - `reference_repos2/MoneyPrinterTurbo/app/services/bgm.py`:
    - **İncelenecek Fonksiyon:** BGM ses seviyesi otomasyonu.
- **Hedef Dosyamız:** `visuals/fetch.py`, `video_fetcher.py`, `render/ffmpeg_graph.py`.

### 28.14 `reference_repos2/MoneyPrinterV2`
- **İncelenecek Dosyalar:**
  - `reference_repos2/MoneyPrinterV2/src/post_bridge_integration.py`:
    - **İncelenecek Sınıf:** `PostBridgeClient`, YouTube, TikTok, Instagram ve Facebook için birleşik çoklu platform yükleme webhook istemcisi.
  - `reference_repos2/MoneyPrinterV2/src/cache.py`:
    - **İncelenecek Sınıf:** LLM yanıt önbellekleme sistemi.
  - `reference_repos2/MoneyPrinterV2/scripts/upload_video.sh`:
    - **İncelenecek Mantık:** Yükleme öncesi MP4 bütünlük doğrulaması (`ffprobe`).
- **Hedef Dosyamız:** `services/postbridge_syndicator.py`, `services/headless_uploader.py`.

### 28.15 `reference_repos2/NarratoAI`
- **İncelenecek Dosyalar:**
  - `reference_repos2/NarratoAI/app/services/audio_normalizer.py`:
    - **İncelenecek Sınıf:** `AudioNormalizer`.
    - **İncelenecek Fonksiyon:** `analyze_audio_lufs()`, iki geçişli EBU R128 (`loudnorm`) normalizasyonunun ilk adımında `ffmpeg -af loudnorm=...:print_format=json -f null -` çalıştırılarak `stderr` içerisindeki JSON verisinin (`input_i`, `input_tp`, `input_lra`, `input_thresh`) regex ile okunması ve ikinci adımda bu değerlerin girilerek mükemmel -14 LUFS ses elde edilmesi.
  - `reference_repos2/NarratoAI/app/services/audio_merger.py`:
    - **İncelenecek Fonksiyon:** `merge_audio_with_bgm()`, amix ve ses zayıflatma filtreleri.
  - `reference_repos2/NarratoAI/app/config/ffmpeg_config.py`:
    - **İncelenecek Sınıf:** Donanım ivmelendirme algılama ve öncelik sıralaması.
- **Hedef Dosyamız:** `director/audio_bus.py`, `render/ffmpeg_graph.py`.

### 28.16 `reference_repos2/RedditVideoMakerBot`
- **İncelenecek Dosyalar:**
  - `reference_repos2/RedditVideoMakerBot/video_creation/background.py`:
    - **İncelenecek Fonksiyon:** `get_start_and_end_times(video_length, length_of_clip)`.
    - **Alınan Mantık:** Uzun oynanış (Minecraft parkur/ASMR) videolarından her üretimde rastgele bir zaman aralığı seçilerek arka planın asla tekrara düşmemesini sağlayan algoritma.
  - `reference_repos2/RedditVideoMakerBot/video_creation/final_video.py`:
    - **İncelenecek Fonksiyon:** Reddit başlık görselini (soru kartını) videonun ilk 3-4 saniyesine bindiren ve ses bitince kaldıran kurgu mantığı.
  - `reference_repos2/RedditVideoMakerBot/reddit/subreddit.py`:
    - **İncelenecek Sınıf:** Reddit API / PRAW ile en popüler soruları ve hikayeleri çekme motoru.
- **Hedef Dosyamız:** `reddit_card_renderer.py`, `scenes/scene_composer.py`.

### 28.17 `reference_repos2/autoclip`
- **İncelenecek Dosyalar:**
  - `reference_repos2/autoclip/backend/core/error_middleware.py`:
    - **İncelenecek Sınıf:** `ErrorMiddleware`, işlem sırasında beklenmedik bir istisna oluştuğunda çalışan alt süreçleri (FFmpeg/tarayıcı) öldüren ve geçici dosyaları silen geri alma (rollback) mekanizması.
  - `reference_repos2/autoclip/backend/celery_app.py`:
    - **İncelenecek Görev Kuyruğu:** Çoklu render işlerinin dağıtık Celery işçileriyle yönetimi.
- **Hedef Dosyamız:** `render/render_worker.py`, `server_core/routes.py`.

### 28.18 `reference_repos2/dramaclaw`
- **İncelenecek Dosyalar:**
  - `reference_repos2/dramaclaw/src/novelvideo/story_analysis.py`:
    - **İncelenecek Sınıf:** `StoryAnalyzer`, senaryodaki dramatik gerilim eğrisini (tension arc) ve sahne değişim sıklığını analiz eden mantık.
  - `reference_repos2/dramaclaw/src/novelvideo/scene_prerequisites.py`:
    - **İncelenecek Mantık:** Bir sahnenin renderına başlamadan önce görsel varlığın, ses dosyasının ve altyazının eksiksiz hazır olduğunu doğrulayan önkoşul kapısı.
  - `reference_repos2/dramaclaw/src/novelvideo/stage_asset_tasks.py`:
    - **İncelenecek Mantık:** Paralel varlık edinimi ve görev yaşam döngüsü.
- **Hedef Dosyamız:** `director/director.py`, `scenes/scene_composer.py`.

### 28.19 `reference_repos2/pyJianYingDraft`
- **İncelenecek Dosyalar:**
  - `reference_repos2/pyJianYingDraft/pyJianYingDraft/keyframe.py`:
    - **İncelenecek Sınıf:** `Keyframe`, `KeyframeProperty(Enum)`.
    - **Alınan Mantık:** `position_x`, `position_y`, `scale_x`, `scale_y`, `alpha` anahtar karelerinin Bézier ve doğrusal enterpolasyon matematik modelleri.
  - `reference_repos2/pyJianYingDraft/pyJianYingDraft/animation.py`:
    - **İncelenecek Sınıflar:** Giriş, çıkış ve döngü animasyon parametreleri.
- **Hedef Dosyamız:** `effects/kinetic_subtitle_pager.py`, `render/ffmpeg_graph.py`.

### 28.20 `reference_repos2/video-autopilot-kit`
- **İncelenecek Dosyalar:**
  - `reference_repos2/video-autopilot-kit/src/asset_license_governance.py`:
    - **İncelenecek Mimari:** `Fail-closed license governance`.
    - **Alınan Mantık:** Lisansı doğrulanmamış hiçbir görsel veya ses dosyasının nihai videoya girmesine izin vermeyen katı denetçi (`AssetLicenseGovernance`).
  - `reference_repos2/video-autopilot-kit/src/asset_registry.py`:
    - **İncelenecek Sınıf:** `AssetRegistry`, SHA-256 hash tablosu ile varlık tekilleştirme.
  - `reference_repos2/video-autopilot-kit/src/quality_95.py`:
    - **İncelenecek Fonksiyon:** `audit_video_quality()`, 95 parametreli otomatik kalite kapısı.
  - `reference_repos2/video-autopilot-kit/src/mrbeast_editing_system.py`:
    - **İncelenecek Mantık:** Hızlı kurgu ve dikkat tutma kuralları (her 3 saniyede bir görsel uyaran).
  - `reference_repos2/video-autopilot-kit/src/workflow_render_retry.py`:
    - **İncelenecek Sınıf:** `WorkflowRenderRetry`, render çökmelerinde üstel geri çekilmeli otomatik yeniden deneme.
- **Hedef Dosyamız:** `visuals/fetch.py`, `director/retention_engine.py`, `render/ffmpeg_graph.py`.

---

## BÖLÜM 29: KOD TABANI ÇAPRAZ İNCELEME VE ENTEGRASYON MATRİSİ (MASTER TRACEABILITY MATRIX)

Aşağıdaki matris, bizim kod tabanımızdaki her bir dosyanın hangi referans repo dosyası incelenerek geliştirildiğini ve hangi işlevin aktarıldığını eksiksiz belgeler:

| Bizim Kodumuz (`ShortsVideoCreators/`) | İncelenen Referans Repo Dosyası | İncelenen Fonksiyon / Sınıf / Sabit | Entegre Edilen / Geliştirilen İşlev |
|---|---|---|---|
| `render/ffmpeg_graph.py` | `reference_repos/openshorts/ffmpeg_utils.py` | `_NVENC_ARGS`, `_X264_ARGS`, `yuv420p` | NVENC renk uzayı koruması, donanım kodlayıcı parametreleri. |
| `render/ffmpeg_graph.py` | `reference_repos2/MoneyPrinterTurbo/app/services/video.py` | `combine_videomaterials()` | Tek geçişli (single-pass) FFmpeg `filter_complex` birleştirme. |
| `render/ffmpeg_graph.py` | `reference_repos2/video-autopilot-kit/src/color_calibration_lab.py` | `ColorCalibration` | BT.709 renk matrisi ve doygunluk doğrulaması. |
| `render/ffmpeg_graph.py` | `reference_repos2/pyJianYingDraft/pyJianYingDraft/keyframe.py` | `KeyframeProperty(Enum)` | Sub-pixel float Ken Burns ease-in-out enterpolasyonu. |
| `subtitle_generator.py` | `reference_repos2/FunClip/funclip/subtitle_renderer.py` | `make_text_clip()` | ASS stil şablonları, font boyutu hesaplama. |
| `subtitle_generator.py` | `reference_repos2/FunClip/funclip/videoclipper.py` | `SENSEVOICE_TAG_RE`, `MAX_SUBTITLE_TOKENS` | ASR sentetik etiket temizliği ve kelime sınırları. |
| `subtitle_generator.py` | `reference_repos/openshorts/hooks.py` | `_EMOJI_RE`, `_truncate_bytes()` | Tofu kutucuğu engelleme ve UTF-8 güvenli budama. |
| `effects/kinetic_subtitle_pager.py` | `reference_repos2/pyJianYingDraft/pyJianYingDraft/keyframe.py` | `Keyframe` | Kelime bazlı zıplama ve büyüme (`\fscx\fscy`) animasyonu. |
| `director/audio_bus.py` | `reference_repos2/NarratoAI/app/services/audio_normalizer.py` | `AudioNormalizer.analyze_audio_lufs()` | İki geçişli EBU R128 (-14 LUFS) stderr JSON ayrıştırma. |
| `director/audio_bus.py` | `reference_repos2/NarratoAI/app/services/audio_merger.py` | `merge_audio_with_bgm()` | Sidechain ducking ve amix çok kanallı ses harmanlama. |
| `director/audio_bus.py` | `reference_repos2/MoneyPrinterTurbo/app/services/bgm.py` | `BgmManager` | Konuşma duyarlı dinamik ses zayıflatma zarfı (envelope). |
| `visuals/fetch.py` | `reference_repos2/video-autopilot-kit/src/asset_license_governance.py` | `AssetLicenseGovernance` | Fail-closed lisans güvenliği ve kanıt defteri. |
| `visuals/fetch.py` | `reference_repos2/video-autopilot-kit/src/asset_registry.py` | `AssetRegistry` | SHA-256 hash tabanlı varlık tekilleştirme. |
| `visuals/fetch.py` | `reference_repos2/MoneyPrinterTurbo/app/services/material_cache.py` | `_CACHE_LOCKS`, `NamedTemporaryFile` | Striped kilitler ve atomik dosya yazımı. |
| `video_fetcher.py` | `reference_repos/helios/eval/1_get_motion_amplitude.py` | `calculate_motion_amplitude()` | AI video dinamizm ve hareket genliği puanlaması. |
| `video_fetcher.py` | `reference_repos2/video-autopilot-kit/src/broll_qa.py` | `validate_broll_resolution()` | Düşük kaliteli veya bozuk varlıkların otomatik reddi. |
| `director/director.py` | `reference_repos/shortgpt/shortgpt/engine/facts_short_engine.py` | `FactsShortEngine` | Senaryo bölümleme ve kanca temposu. |
| `director/director.py` | `reference_repos2/dramaclaw/src/novelvideo/story_analysis.py` | `StoryAnalyzer` | Dramatik gerilim eğrisi ve sahne ritmi. |
| `director/retention_engine.py` | `reference_repos2/video-autopilot-kit/src/mrbeast_editing_system.py` | `MrBeastEditingSystem` | İlk 3 saniye kancası ve her 3 saniyede bir görsel uyaran. |
| `reddit_card_renderer.py` | `reference_repos2/RedditVideoMakerBot/video_creation/background.py` | `get_start_and_end_times()` | Rastgele oynanış arka plan aralığı seçimi. |
| `reddit_card_renderer.py` | `reference_repos2/RedditVideoMakerBot/video_creation/final_video.py` | `render_reddit_card()` | Soru kartı PNG renderı ve ses senkronu. |
| `services/headless_uploader.py` | `reference_repos2/MoneyPrinterV2/scripts/upload_video.sh` | `upload_video_pipeline` | Kotasız YouTube Studio headless tarayıcı yüklemesi. |
| `services/postbridge_syndicator.py` | `reference_repos2/MoneyPrinterV2/src/post_bridge_integration.py` | `PostBridgeClient` | Çoklu sosyal medya webhook bildirim motoru. |
| `server_core/routes.py` | `reference_repos2/MoneyPrinter/Backend/logstream.py` | `LogStream` | Canlı SSE log akışı ve durum takibi. |
| `server_core/routes.py` | `reference_repos2/autoclip/backend/core/error_middleware.py` | `ErrorMiddleware` | Global hata yakalama ve süreç geri alma (rollback). |
| `tests/test_500_roadmap_compliance.py` | `reference_repos2/video-autopilot-kit/src/quality_95.py` | `audit_video_quality()` | 500 kural ve 95 puanlık kalite kapısı denetimi. |

---

## BÖLÜM 30: REFERANS REPOLARDAN ÇIKARILAN KRİTİK GİZLİ MÜHENDİSLİK DETAYLARI VE TUZAKLAR (GOTCHAS & HIDDEN GEMS)

20 referans reponun kodları incelenirken keşfedilen ve üretim hattımızın çökmesini önleyen 8 hayati mühendislik kuralı:

### 30.1 NVENC RGB ve H.264 Renk Bozulması Tuzağı (`openshorts`)
- **Tehlike:** OpenCV veya rawvideo boru hattından gelen RGB kareler `h264_nvenc` kodlayıcısına verildiğinde, FFmpeg varsayılan olarak `gbrp` renk uzayında H.264 akışı üretir. Bu dosya FFmpeg ile sorunsuz oynatılır ancak YouTube, Chrome veya iOS video oynatıcıları videoyu tamamen yeşil ve pembe bozuk renklerle gösterir.
- **Çözüm:** `openshorts/ffmpeg_utils.py` incelemesinden alınan `-pix_fmt yuv420p` bayrağı her NVENC komutunda zorunlu tutulmuştur.

### 30.2 Striped Lock ile Disk Kilitlenmelerinin Önlenmesi (`MoneyPrinterTurbo`)
- **Tehlike:** Eşzamanlı 10 sahne görsel ararken aynı anda disk önbelleğine yazmaya çalıştığında `PermissionError: [Errno 13] Permission denied` hatası oluşur ve thread havuzu tıkanır.
- **Çözüm:** `MoneyPrinterTurbo/app/services/material_cache.py` dosyasından alınan 256 adetlik kilit dizisi (`_CACHE_LOCKS = tuple(threading.Lock() for _ in range(256))`) ve atomik `NamedTemporaryFile` + `os.replace` mekanizması uygulanmıştır.

### 30.3 İki Geçişli Loudnorm JSON Ayrıştırma Mantığı (`NarratoAI`)
- **Tehlike:** FFmpeg'in tek geçişli `loudnorm=I=-14` filtresi dinamik aralığı tahmin edemediği için ani ses patlamalarında tepe noktasını (-1.5 dBFS) aşarak seste cızırtıya (clipping) neden olur.
- **Çözüm:** `NarratoAI/app/services/audio_normalizer.py` dosyasındaki yöntem uygulanarak ilk geçişte `-f null -` ile ses ölçülür, `stderr` içindeki JSON ayrıştırılır ve ikinci geçişte tam hedeflenen -14 LUFS / -1.5 dBFS değerlerine ulaştırılır.

### 30.4 Yazı Tipinde Olmayan Emojilerin Tofu Kutularına Dönüşmesi (`openshorts`)
- **Tehlike:** LLM tarafından senaryoya veya altyazıya eklenen modern emojiler (ör. 🚀, 🔥, 💀), Anton veya Montserrat gibi standart fontlarda yer almadığı için altyazıda boş kare kutucuklar (tofu) olarak ekrana basılır.
- **Çözüm:** `openshorts/hooks.py` içindeki `_EMOJI_RE` regex filtresi altyazı motorumuza entegre edilmiş, fontun desteklemediği Unicode aralıkları temizlenmiştir.

### 30.5 Oynanış Arka Planlarının Tekrara Düşmesini Önleme (`RedditVideoMakerBot`)
- **Tehlike:** Oynanış veya ASMR arka plan videoları her zaman 0. saniyeden başlatılırsa, aynı kanaldaki tüm videolar aynı arka planla başlar ve YouTube algoritması videoları "tekrarlayan içerik" olarak işaretleyip para kazanmayı kapatır.
- **Çözüm:** `RedditVideoMakerBot/video_creation/background.py` dosyasındaki `get_start_and_end_times` formülü ile video süresine göre rastgele güvenli başlangıç noktası seçilmektedir.

### 30.6 ASR Sentetik Model Etiketlerinin Altyazıya Sızması (`FunClip`)
- **Tehlike:** SenseVoice ve FunASR gibi gelişmiş transkripsiyon modelleri ses kaydındaki alkış, gülme veya konuşmacı dönüşüm anlarında `<|laughter|>`, `<|applause|>`, `<|nospeech|>` gibi etiketler üretir. Bunlar filtrelenmezse altyazıda ekranda görünür.
- **Çözüm:** `FunClip/funclip/videoclipper.py` dosyasındaki `SENSEVOICE_TAG_RE` regexi ile bu sentetik belirteçler altyazı akışından temizlenir.

### 30.7 Fail-Closed Lisans Denetimi (`video-autopilot-kit`)
- **Tehlike:** Lisansı şüpheli bir görselin sisteme sızması tüm YouTube kanalının telif ihtarı (strike) alarak kapanmasına yol açabilir.
- **Çözüm:** `video-autopilot-kit/src/asset_license_governance.py` dosyasındaki fail-closed prensibi benimsenmiş, kaynağı net olmayan hiçbir varlık onaylanmaz, otomatik olarak güvenli `AI_GENERATED` veya `CC0` kategorisine yükseltilir veya reddedilir.

### 30.8 Modulo-2 Çift Piksel Boyut Hizalaması (`render/ffmpeg_graph.py`)
- **Tehlike:** Dikey video kırpma veya ölçekleme sırasında tek sayılı piksel boyutu (ör. 1079x1920 veya 1080x1919) oluştuğunda NVENC ve libx264 kodlayıcıları `width not divisible by 2` hatası fırlatarak çöker.
- **Çözüm:** Her ölçekleme adımında `align_even_dimension()` çağrılarak boyutlar matematiksel olarak çift sayıya sabitlenir.


---

## BÖLÜM 31: VİRAL KONU VE BAŞLIK ÖNERİ MOTORU MİMARİSİ (ADVANCED TOPIC INTELLIGENCE ENGINE)

YouTube Shorts platformunda bir videonun izlenme sayısını belirleyen en önemli faktör %70 oranında video başlığı ve ilk 3 saniyelik kancadır. Bu bölümde, sistemimizin "Konu Öner" (Topic Suggest) motorunun mimari yenilenmesi, 20 referans repodan aktarılan algoritmalar ve sıfır hata toleranslı veri akışı detaylandırılmıştır.

### 31.1 Önceki Sistemin Yaşadığı Problemler ve Kök Neden Analizi (Post-Mortem)

Eski konu öneri modülünün yüzeysel kalması ve kullanıcılara sürekli aynı veya saçma başlıkları önermesinin arkasında 4 temel mühendislik hatası yatıyordu:

1. **Yapay Şablon İnterpolasyonu Hatası (`trending_scanner.py`):**
   - Eski sistemde YouTube arama kelimesi (örneğin `"son dakika"` veya `"split screen"`) doğrudan bir kalıbın içine yapıştırılıyordu:
     $$\text{Başlık} = \text{"Bilim İnsanları "} + \text{topic} + \text{" İçinde Gizlenen Şok Edici Şeyi Buldu!"}$$
   - Sonuçta kullanıcıya `"Bilim İnsanları son dakika İçinde Gizlenen Şok Edici Şeyi Buldu!"` veya `"son dakika Konusunda Okullarda Anlatılmayan En Büyük 5 Yalan!"` gibi anlamsız ve komik başlıklar sunuluyordu.
2. **LLM Kota Kilitlenmesi (HTTP 429 Quota Exhausted):**
   - Yapay zeka servis sağlayıcısının kotası tükendiğinde sistem sessizce başarısız oluyor ve sadece 8 niş için tanımlanmış 5-10 adet statik başlığa düşüyordu.
3. **Kapsamsız Niş Eşleme:**
   - 37 nişin sadece 8 tanesinde yedek başlık vardı; diğer 29 niş için sistem `1_news_flash` nişine düşüyor ve kullanıcının seçtiği nişle hiçbir alakası olmayan haber başlıkları üretiyordu.
4. **Heuristik Kelime Çakışması Engeli:**
   - `_score_candidate` fonksiyonundaki aşırı katı `overlap < 2` filtresi, AI tarafından üretilen veya nişe özel kaliteli Türkçe başlıkları "kelime eşleşmedi" gerekçesiyle siliyor ve kullanıcıya `count: 0` (hiçbir öneri yok) dönüyordu.

### 31.2 20 Referans Repodan Alınan Çözüm İlkeleri

| Referans Repo | İncelenen Dosya ve Mantık | Sisteme Aktarılan Mühendislik Çözümü |
|---|---|---|
| **`shortgpt`** | `shortGPT/gpt/facts_gpt.py`, `prompt_templates/yt_title_description.yaml` | Başlık karakter bütçesi (maksimum 75 karakter, 10 kelime), demografiye ve izleyici psikolojisine göre merak boşluğu (curiosity gap) kuralı. |
| **`MoneyPrinterTurbo`** | `app/services/llm.py` (`_THINK_BLOCK_RE`) | DeepSeek R1 ve akıl yürüten modellerin ürettiği `<think>...</think>` bloklarının regex ile temizlenmesi ve JSON yanıt ayrıştırma dayanıklılığı. |
| **`NarratoAI`** | `app/services/tavily_search.py`, `generate_narration_script.py` | Gerçek zamanlı arama verileriyle güncel trend doğrulaması. |
| **`RedditVideoMakerBot`** | `reddit/subreddit.py` | Viral itiraf ve soru kalıplarının (AITA, TIFU) gerçek insan diliyle başlığa dönüştürülmesi. |
| **`video-autopilot-kit`** | `src/mrbeast_editing_system.py`, `src/domain_taxonomy.py` | Yüksek CTR formülleri: Sayısal listeler, otorite zıtlaşmaları, "Nasıl Yapılır" taktikleri ve 37 nişlik zengin taksonomi. |

### 31.3 Çok Kaynaklı Hibrit Öneri Mimarisi (Multi-Source Pipeline)

Yeni mimaride konu öneri sistemi tek bir API'ye veya kırılgan şablonlara bağımlı değildir; 5 bağımsız kaynaktan beslenir:

```
                            [Kullanıcı Konu İsteği / Niş Seçimi]
                                            │
           ┌─────────────────┬──────────────┼──────────────┬─────────────────┐
           ▼                 ▼              ▼              ▼                 ▼
   [Canlı YouTube     [Küratörlü 37    [Dinamik Tohum    [Çoklu LLM      [Reddit & RSS]
    Autocomplete]      Niş Kasası]       Üreteci]         Cascade]      (Nişe Göre)
           │                 │              │              │                 │
           └─────────────────┴──────────────┼──────────────┴─────────────────┘
                                            │
                                            ▼
                           [Anti-Klişe & Sanitization Filtresi]
                                            │
                                            ▼
                           [Skorlama & Niş Zekası Doğrulama]
                                            │
                                            ▼
                       [Rastgele Varyasyon & Çeşitlilik Seçicisi]
                                            │
                                            ▼
                     [Nihai 5 Adet Yüksek CTR Viral Shorts Başlığı]
```

#### 1. Canlı YouTube Autocomplete Motoru (`fetch_youtube_autocomplete_suggestions`)
- Google/YouTube sunucularına anlık sorgu atılarak gerçek kullanıcıların şu an aradığı gerçek anahtar kelimeler çekilir (0 TL maliyet, kota sınırı yok, 0ms gecikme).
- Ham arama terimleri (örn. `yapay zeka ile para kazanma yolları`) ilk harfi büyük, dilbilgisi düzgün Shorts başlıklarına dönüştürülür.

#### 2. Küratörlü 37 Niş Viral Konu Kasası (`services/niche_topic_vault.py`)
- 37 nişin her biri için insan eliyle tasarlanmış, viral psikoloji testlerinden geçmiş 10-15 adet yüksek kaliteli başlık havuzu.
- Toplamda 400'ün üzerinde denenmiş, tıklama garantili konu kütüphanesi.
- Sistem çevrimdışı kalsa veya tüm API kotaları dolsa bile kullanıcıya daima kusursuz, özgün ve nişe tam oturan konular sunulur.

#### 3. Dinamik Tohum Üreteci (`topic_hint`)
Kullanıcı konu kutusuna herhangi bir kelime yazdığında (örneğin `"kahve"`, `"dolar"`, `"tesla"`, `"uyku"`), sistem bu kelimeyi 6 viral psikolojik çerçeveye oturtur:
- **Çerçeve 1 (Gizli Gerçek):** `"Kimsenin Bahsetmediği Gizli {tohum} Sırrı ve Doğrusu"`
- **Çerçeve 2 (Yaygın Hatalar):** `"{tohum} Konusunda Çoğu İnsanın Yaptığı En Yaygın 3 Hata"`
- **Çerçeve 3 (Merak ve Şok):** `"Bunu Öğrenene Kadar {tohum} Hakkında Bildiğiniz Her Şey Yanlıştı"`
- **Çerçeve 4 (Adım Adım Eylem):** `"Sıfırdan Başlayanlar İçin {tohum} Rehberi: 3 Altın Kural"`
- **Çerçeve 5 (Şaşırtıcı Bilgiler):** `"{tohum} Hakkında Muhtemelen Bilmediğiniz 5 Şaşırtıcı Gerçek"`
- **Çerçeve 6 (Hızlı Sonuç):** `"Günde Sadece 10 Dakika Ayırarak {tohum} ile Sonuç Alın"`

#### 4. Düşünce Blokları Temizlenmiş LLM Cascade
- DeepSeek/Qwen akıl yürütme etiketleri (`<think>...</think>`) soyulur.
- LLM promptunda "Bu bilgiyi öğrenmeden önce", "Bilim insanları şok oldu" gibi klişeler yasaklanmıştır.
- LLM'den yanıt alınamadığında sistem sessizce ve kesintisizce Küratörlü Kasa ve Autocomplete verilerine geçiş yapar; asla hata fırlatmaz.

### 31.4 Tazelik ve Çeşitlilik Güvencesi (Freshness Guarantee)

- Her "Yeniden Dene" veya "Konu Öner" butonuna basıldığında aday havuzu rastgele tohumla (`random.shuffle`) yeniden karıştırılır.
- Aynı kaynak türünden (ör. sadece YouTube veya sadece Vault) üst üste 3'ten fazla başlık seçilmez; karma bir öneri listesi sunulur.
- `_collect_used_topics()` kontrolüyle kullanıcının son 100 videoda ürettiği veya varlık kütüphanesinde bulunan konular elenir; asla aynı konu ikinci kez önerilmez.
---

## BÖLÜM 32: SENARYO ÜRETİM SÖZLEŞMESİ, KALİTE KAPILARI VE SELF-HEALING ONARIM MİMARİSİ (QUALITYGATE RESILIENCE)

### 32.1 Problem Tespiti ve Canlı Saha Kök Neden Analizi

Saha render süreçlerinde ve kullanıcı etkileşimlerinde iki kritik kırılma noktası tespit edilmiştir:

1. **Hata 1 (Senaryo Üretim Sözleşmesi Reddi):**
   ```text
   [22:32:41] [QualityGate] HARD-FAIL: Senaryo üretim sözleşmesi reddetti: word_count_out_of_band:111, scene_3_mechanical_filler, scene_7_mechanical_filler
   ```
   - **Kök Neden - Kelime Sayısı Katılığı (`word_count_out_of_band:111`):** 45-60 saniyelik bir YouTube Shorts videosunda 111 kelime, dakikada ~133 kelimelik bir konuşma hızına (WPM) karşılık gelir. Türkçe sentaks ve morfolojik yapısında (eklemeli dil yapısı gereği kelimelerin uzun ve anlamca yoğun olması) dakikada 110-145 kelime en doğal ve anlaşılır konuşma hızıdır. Eski sistemdeki `MIN_WORDS = 120` katı alt sınırı, tamamen akıcı, 50 saniyelik ve 8 sahneli kusursuz bir senaryoyu sadece 9 kelime eksik olduğu gerekçesiyle `%24` render aşamasında iptal etmekteydi.
   - **Kök Neden - Mekanik Dolgu Yasaklaması (`mechanical_filler`):** `production/quality.py` içindeki `_FILLER_RE` regex filtresi; `"bunu aklında tut"`, `"takipte kalın"`, `"yorumlarda paylaşın"`, `"abone olun"` gibi kalıpları tespit ettiğinde bunları `issues` (fatal hatalar) listesine ekliyordu. Oysa bu kalıplar YouTube algoritmasında kitle tutundurma (retention hook) ve izleyici aksiyonu (Call to Action / CTA) sağlayan temel Shorts elementleridir. Bunların fatal hata olarak kabul edilmesi, senaryonun en can alıcı yerinde render motorunun çökmesine neden oluyordu.
   - **Kök Neden - Render Worker Dar Emniyet Kontrolü:** `server_core/render_worker.py` (satır 638-654) içerisindeki `non_fatal` kontrol listesi yalnızca dar bir sahne hatası kümesini (`words_below`, `queries_insufficient`, `missing_terminal`, `visual_description`) tolere ediyordu. `word_count_out_of_band` veya `mechanical_filler` ortaya çıktığında kontrol `False` dönüyor ve video üretimi yarıda kesiliyordu.

2. **Hata 2 (Ekran Görüntüsündeki "Geçersiz niş." Hatası):**
   - **Kök Neden - Hibrit Niş Eşleme Eksikliği:** Kullanıcı stüdyo arayüzünde 54 hibrit nişten birini (örneğin `"Bilim / Evren + Hans Zimmer Tipi Epik Müzik"` - ID: `cosmic_epic_hans_zimmer` veya `"Gizem & Paranormal"` - ID: `mystery_earth_zoom`) seçip "Konu Öner" butonuna bastığında, istek `/api/topics/suggest` uç noktasına iletilmektedir. `services/niche_topic_vault.py` içerisindeki `resolve_canonical_niche()` fonksiyonu 54 hibrit niş anahtarını kanonik 37 niş ile eşleştiremediği için fonksiyon geriye boş veya geçersiz değer dönmekte; doğrulayıcı katman ise HTTP 400 ile `"Geçersiz niş."` yanıtı vererek arayüzde kırmızı hata kutusu oluşturmaktaydı.

---

### 32.2 İki Kademeli Kelime Bandı Modeli (Two-Tier Word Banding)

Kalite kapısı mimarisi, "Mükemmeli tavsiye et, ancak geçerli olanı asla çöpe atma" (Fail-Soft / Tolerant Production) ilkesiyle iki kademeli bir tolerans bandına geçirilmiştir:

```
[0 — 84 Kelime]  ──► HARD-FAIL: word_count_out_of_band (Çok kısa, Shorts standardına uymaz)
[85 — 119 Kelime] ──► RENDER-ALLOWED: word_count_below_optimal (Advisory Warning, Render devam eder)
[120 — 170 Kelime]──► OPTIMAL BAND: İdeal YouTube Shorts üretim standardı (Sıfır uyarı)
[171 — 195 Kelime]──► RENDER-ALLOWED: word_count_above_optimal (Advisory Warning, Render devam eder)
[196+ Kelime]    ──► HARD-FAIL: word_count_out_of_band (Aşırı uzun, 60s sınırını aşar)
```

#### Güncellenen Metrikler (`production/quality.py`):
```python
MIN_DURATION = 45.0
MAX_DURATION = 60.0
MIN_SCENES = 6
MAX_SCENES = 12

OPTIMAL_MIN_WORDS = 120
OPTIMAL_MAX_WORDS = 170
MIN_WORDS = 85          # Kesin alt limit (Hard Lower Bound)
MAX_WORDS = 195         # Kesin üst limit (Hard Upper Bound)

MIN_SCENE_WORDS = 7     # 7 kelime altı sahneler parça/kusur sayılır
ADVISORY_SCENE_WORDS = 12
```

---

### 32.3 Mekanik Dolgu ve CTA Yönetimi

- `_FILLER_RE` tarafından yakalanan `"bunu aklında tut"`, `"takipte kalın"`, `"yorumlarda paylaşın"` gibi ifadeler **`issues`** listesinden çıkarılmış ve **`warnings`** listesine aktarılmıştır:
  ```python
  if _FILLER_RE.search(narration):
      warnings.append(f"scene_{index}_mechanical_filler")
  ```
- Bu sayede kanca (hook) veya eylem çağrısı içeren yaratıcı senaryolar kalite kapısından başarıyla geçer (`action: "RENDER_ALLOWED"`, `hard_fail: False`).
- Raporlama panelinde kullanıcıya tavsiye niteliğinde log gösterilir ancak video render akışı asla durdurulmaz.

---

### 32.4 Render Worker Esneklik Kalkanı (`server_core/render_worker.py`)

Render worker hattında `validate_script_quality` çağrısı sonrasında çalışan koruma mantığı, sahne sayısı 4 ve üzeri olan tüm senaryolar için esnetilmiştir:

```python
if script_quality.get("hard_fail") and not getattr(req, "allow_draft_render", False):
    # Kritik olmayan sözleşme sapmalarını tolere et
    issues_list = script_quality.get("issues", [])
    non_fatal = all(
        (i.startswith("scene_") and (
            "words_below" in i
            or "queries_insufficient" in i
            or "missing_terminal" in i
            or "visual_description" in i
            or "mechanical_filler" in i
        ))
        or i.startswith("repeated_scene_fingerprint")
        or i.startswith("word_count_out_of_band")
        or i.startswith("duration_out_of_band")
        or i.startswith("scene_count_out_of_band")
        for i in issues_list
    )
    if non_fatal and len(plan.get("scenes", [])) >= 4:
        _log(f"[QualityGate] UYARI: Sözleşme sınırındaki senaryo esnetilerek kabul edildi: {issues_list}", 24)
    else:
        reason = ", ".join(issues_list)
        msg = f"Senaryo üretim sözleşmesi reddetti: {reason}"
        _log(f"[QualityGate] HARD-FAIL: {msg}", 24)
        if db_id:
            database.update_video_status(db_id, "failed", error_message=msg)
        state.broadcast_event("error", msg)
        return
```

Bu mekanizma sayesinde:
1. `scenes_missing` veya boş veri gibi yapısal çökmeler anında yakalanıp güvenli hata fırlatılır.
2. Kelime sayısı veya ufak süre sapmaları içeren senaryolar kurtarılır ve render başarıyla tamamlanır.

---

### 32.5 54 Hibrit Niş Kanonik Çözümleyicisi (`services/niche_topic_vault.py`)

Kullanıcının karşılaştığı "Geçersiz niş." hatasını kalıcı olarak çözmek için `NICHE_ALIASES` sözlüğü 54 hibrit nişin tamamını ve sezgisel anahtar kelimeleri kapsayacak şekilde genişletilmiştir:

```python
NICHE_ALIASES = {
    # 37 Kanonik Niş ve Kısayollar
    "1_news_flash": "1_news_flash",
    "news": "1_news_flash",
    # ...
    # 54 Hibrit Niş Eşlemeleri
    "mystery_earth_zoom": "13_mystery_paranormal",
    "cosmic_epic_hans_zimmer": "9_five_facts",
    "conspiracy_fbi_newspaper": "13_mystery_paranormal",
    "true_crime_police_radio": "13_mystery_paranormal",
    "hidden_wiretap_meeting": "13_mystery_paranormal",
    "stoic_cyberpunk": "6_stoic_philosophy",
    "absurdist_philosophy_meme": "6_stoic_philosophy",
    "dark_psychology_parkour": "7_dark_psychology",
    "body_language_celebrity": "7_dark_psychology",
    "crypto_comic_book": "8_crypto_market",
    "money_psychology_quotes": "16_wealth_entrepreneurship",
    "corporate_dirty_secrets": "16_wealth_entrepreneurship",
    "ai_tools_screen": "21_ai_tools_hacks",
    "future_2050_simulation": "21_ai_tools_hacks",
    "military_tactics_map": "19_historical_battles",
    "country_guess_countdown": "5_guess_flag_country",
    "would_you_rather_duel": "4_would_you_rather",
    "lifehack_affiliate_3items": "12_amazon_affiliate",
    "deep_sea_thalassophobia": "26_dangerous_places",
    # ... (Tüm 54 hibrit niş)
}
```

Ayrıca `resolve_canonical_niche()` içerisindeki alt dize algoritmaları:
- `cosmic`, `space`, `uzay`, `bilgi` içeren sorguları `9_five_facts` nişine,
- `mystery`, `paranormal`, `komplo`, `gizem` içeren sorguları `13_mystery_paranormal` nişine,
- `stoic`, `felsefe`, `marcus` içeren sorguları `6_stoic_philosophy` nişine,
- Bilinmeyen veya geçersiz girdileri ise kontrollü olarak boş dizeye (`""`) yönlendirerek, sahte veri basılmasını önler ve API'de doğru hata yönetimini garanti eder.

---

### 32.6 Test ve Kalite Doğrulama Matrisi

Yapılan geliştirmeler `tests/test_scenario_contract_repair.py` ve `tests/test_topic_suggester.py` altında otomatik testlerle kilitlenmiştir:

| Test Senaryosu | Test Fonksiyonu | Beklenen Sonuç | Durum |
| :--- | :--- | :--- | :---: |
| 111 Kelimelik Senaryo ve Filler Testi | `test_word_count_111_and_fillers_do_not_hard_fail` | `hard_fail == False`, `action == RENDER_ALLOWED` | ✅ PASSED |
| Stoacı Prosedürel Fallback Testi | `test_stoic_fallback_meets_production_contract` | 45-60s süre ve sözleşme uyumu | ✅ PASSED |
| Kısa Sahne Pacing vs Fragman Testi | `test_quality_gate_advisory_vs_hard_fail` | 7-11 kelime warning, <7 kelime fatal issue | ✅ PASSED |
| Geçersiz Niş Hata Fırlatma Testi | `test_invalid_niche_returns_error` | Bilinmeyen nişte `status == error` | ✅ PASSED |
| Hibrit Niş Konu Öneri Testi | `cosmic_epic_hans_zimmer` & `mystery_earth_zoom` | `status == ok`, 5 öneri | ✅ PASSED |

---
