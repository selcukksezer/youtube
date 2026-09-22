/**
 * Yeni proje / Ayarlar sekmesindeki Flow uretim anahtarlarinin
 * kullaniciya gosterilen aciklamalari.
 */
export const FLOW_TOGGLE_HELP = {
  allowSubtitles: {
    label: "Videoya gomulu altyazi",
    summary: "Kalici kapali. Dikey (9:16) ve yatay (16:9) tum kliplerde ekranda hic yazi olmaz.",
    detail:
      "Gomulu altyazi, karaoke, sarki sozu, tabela, onluk etiketi ve Ingilizce otomatik caption YASAK. YouTube icin altyazi gerekirse Yayin sekmesinden ayri SRT uretin — kareye yazilmaz.",
  },
  audioEnabled: {
    label: "Ses acik",
    summary: "Flow kendi konusma/sarki sesini uretir. Sarki klibinde KAPALI kalir — ses yuklediginiz MP3'tur.",
    detail:
      "Sarki klibi: her zaman kapali. Flow sessiz goruntu uretir; her klibe master MP3'un o saniye dilimi basilir. Acik birakirsaniz Veo kendi sesini soyler ve parcanizla uyusmaz.",
  },
  useReference: {
    label: "Referans kullan",
    summary: "Karakter gorselini Flow'a referans olarak yukler; yuz/kostum tutarliligi artar.",
    detail:
      "Acik: Karakter sekmesindeki referans gorseller Flow'a eklenir. Cocuk animasyonunda sahnedeki [Kadro] uyelerinin (ana + yan) referanslari birden fazla yuklenir — boylece sabit hikaye kadrosu klipler arasinda bozulmaz. Kapali: model yalnizca metne guvenir; yuzler kolay bozulur. Model referansi desteklemiyorsa kapatilir.",
  },
  useFlowCharacter: {
    label: "Flow karakteri kullan",
    summary: "Flow'da kayitli @karakter referansini prompta yazar.",
    detail:
      "Acik: Karakter profilindeki Flow karakter adi (@Ornek) promptun basina eklenir; Flow ayni kayitli karakteri tanir. Once Flow'da karakter olusturup ismini projeye yazmaniz gerekir. Kapali: sadece yuklediginiz gorsel referans + metin prompt kullanilir.",
  },
  useStartFrame: {
    label: "Baslangic karesi kullan",
    summary: "Klibe sabit bir baslangic karesi (start frame) verir.",
    detail:
      "Acik: uretim, sectiginiz/urettiginiz baslangic karesinden baslar — poz ve kompozisyon daha kontrollu olur. Kapali: model sahneyi sifirdan kurar. Bazi modeller start frame desteklemez; destek yoksa bu anahtar etkisiz kalir veya hata verir.",
  },
  usePrevLastFrame: {
    label: "Onceki son kareyi kullan",
    summary: "Onceki klibin son karesini sonraki klibin baslangici yapar (sureklilik).",
    detail:
      "Acik: her tamamlanan klibin son karesi bir sonraki klibe baslangic olarak verilir — mekan, isik ve karakter konumu klipler arasinda daha tutarli akar. Kapali: her klip bagimsiz baslar; gecislerde ziplama olabilir. Ilk klipte onceki kare olmadigi icin bu anahtar 2. klipten itibaren ise yarar.",
  },
  reuseFlowProject: {
    label: "Ayni Flow projesini kullan",
    summary: "Tum klipler ayni Google Flow projesinde uretilir.",
    detail:
      "Acik: otomasyon ayni Flow proje adini/acilmis projeyi tekrar kullanir — gecmis uretimler bir arada kalir, karakter/proje baglami korunur. Kapali: her seferinde yeni veya farkli proje acilabilir; duzen daginiklasir. Cok klipli hikayelerde acik tutmak onerilir.",
  },
} as const;

export type FlowToggleKey = keyof typeof FLOW_TOGGLE_HELP;
