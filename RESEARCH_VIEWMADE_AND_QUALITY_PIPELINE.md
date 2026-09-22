# Ürün araştırması: ViewMade yaklaşımı ve kalite hattı

Bu belge, 21 Eylül 2026 tarihinde yapılan ürün ve politika incelemesinin
uygulama kararlarını kaydeder. Amaç, konu başlığını rastgele stok görüntüsüne
bağlayan bir bot değil; araştırılmış, özgün ve kaynakları denetlenebilir bir
Shorts üretim hattıdır.

## Dışarıdan doğrulanan sinyaller

ViewMade ana sayfası, Shorts akışını şu sırayla tanımlıyor: konu fırsatı ve
araştırma, senaryo ve yönetim, seslendirme, konuya ait gerçek arşiv görüntüsü,
otomatik yeniden kadraj, kelime bazlı altyazı ve her klibin kaynak kredileri.
Ürün ayrıca gerçek arşiv görüntüsünü, modelin boşluğu doldurmak için uydurduğu
görüntüden ayırıyor. Bu, bizim üretim kararımızı belirliyor: yapay görüntü,
konuya ait gerçek çekimin yerine sessizce geçmeyecek; kullanılırsa üretim
metadatasında açıkça işaretlenecek.

YouTube'un resmi kanal para kazanma politikasında 15 Temmuz 2025 açıklaması
“repetitious content” adını “inauthentic content” olarak netleştiriyor. Aynı
sayfa; materyal olarak değişmeyen şablonları, düşük değerli slayt gösterilerini,
özgün içgörü eklenmeden üretilmiş genel AI şablonlarını ve kaynak içeriğe küçük
değişiklik yapıp yeniden yüklemeyi para kazanma açısından riskli sayıyor.
Buna karşılık özgün bakış, araştırılmış anlatı, yaratıcı ses ve anlamlı görsel
düzenleme kabul edilebilir üretim sinyalleri olarak tarif ediliyor.

Kaynaklar:

- [ViewMade](https://viewmade.com/)
- [YouTube channel monetization policies](https://support.google.com/youtube/answer/1311392)
- [YouTube Shorts monetization policies](https://support.google.com/youtube/answer/12504220)
- [YouTube altered content disclosure](https://support.google.com/youtube/answer/14328491)

## Uygulama kararları

1. **Konu → shot grammar:** Her sahne, özne + eylem + ortam + ışık bileşenleri
   taşıyan arama sorgularına çevrilir. “cinematic 4k atmospheric” gibi konu
   taşımayan kelime çorbası temizlenir.
2. **Gerçek konu eşleşmesi:** Bir sağlayıcı sonucu, sorgunun somut özne
   kelimelerinden hiçbirini taşımıyorsa teknik çözünürlüğü yüksek olsa bile
   seçilmez. Eşleşme yoksa yanlış görüntü göstermek yerine özgün prosedürel
   görsel kullanılır.
3. **Kaynak çeşitliliği:** API anahtarı olan Pexels/Pixabay/Coverr yanında
   Wikimedia Commons, NASA, Openverse ve yalnızca kamu malı koleksiyonlarla
   sınırlandırılmış Internet Archive kullanılır.
4. **Lisans kapısı:** CC0, Public Domain, CC BY ve sağlayıcıların ticari
   lisansları geçer; NC, ND, SA ve belirsiz lisanslar geçmez. Her seçim
   `visual_credits.json` ve açıklamaya yapıştırılabilir `visual_credits.txt`
   içinde tutulur.
5. **Özgünlük kapısı:** Senaryo benzerliği, niş güvenliği, sahne çeşitliliği,
   anlatı bütünlüğü ve kaynak tekrarları render öncesinde kontrol edilir.
6. **İnsan ürünü hissi:** TTS tek başına ürün değildir. Hook, görsel ritim,
   kontrollü pattern interrupt, konuya özel altyazı yerleşimi, ses efektleri,
   yeniden kadraj ve finalde hook'a bağlanan loop birlikte değerlendirilir.

## Bu sürümde uygulanan P0 değişiklikleri

- Görsel aday skorlaması, somut konu kelimeleriyle hiç eşleşmeyen klipleri
  reddediyor. Böylece “gökdelen” başlığına rastgele şehir atmosferi düşmüyor.
- Türkçe konu sözlüğü gökdelen, bina, köprü, metro, tren, okyanus, orman ve
  çöl gibi gerçek çekim bulunabilen nesnelerle genişletildi.
- Her render başında görsel manifest sıfırlanıyor; bütün retry'lar bittikten
  sonra kaynak ledger'ı zorunlu olarak yazılıyor. Ledger üretilemezse render
  başarıyla tamamlanmıyor.

## Bilinçli sınırlar

YouTube keşfet veya viral sonucu garanti edilemez. Sistem, viral olma ihtimalini
artıran ölçülebilir kalite sinyallerini optimize eder ve telif/para kazanma
politikasına aykırı kestirmeleri reddeder. Sağlayıcı lisansları zamanla
değişebildiği için ledger saklanır; yayın öncesi son lisans koşulu yine kontrol
edilmelidir.
