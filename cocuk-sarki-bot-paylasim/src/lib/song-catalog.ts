/**
 * Cocuk sarki klibi — tek kaynak tema + muzik tarzi katalogu.
 * Client (yeni proje / stüdyo) ve sunucu (song.ts promptlari) ayni brief'i kullanir.
 */

export interface SongTheme {
  id: string;
  label: string;
  ageBands: string[];
  /** Kartlarda tek satirlik cazibe cumlesi */
  tagline: string;
  description: string;
  moodHint: string;
  propBank: string;
  /** Ilk 5 sn hook acisi (prompta akar) */
  hookAngle: string;
  /** Oyun / birlikte soyleme mekanigi */
  gameMechanic: string;
  /** Soz yazimina tohum kelimeler (Turkce) */
  lyricSeedWords: string;
  /**
   * Yaratıcı kıvılcım: beklenmedik imge / sticky hook acisi.
   * Model buna bakip ogretmen talimati degil sarki yazar.
   */
  lyricSpark: string;
  /**
   * Sarkinin duygusal vaadi — 1-2 cumle.
   * Dinleyici "bu sarki ne anlatiyor?" diye sorsa bu cevaplanir.
   */
  meaningPromise: string;
  /**
   * Kita yayi: verse'ler ayni anlami nasil ilerletir (yeni prop listesi DEGIL).
   */
  verseArc: string;
  /** Ornek BPM rehberi, or. "100-118" */
  bpmGuide: string;
  /** Kisa aranjman ipucu (TR) */
  arrangementHint: string;
}

export interface SongStyle {
  id: string;
  label: string;
  tagline: string;
  /** Ingilizce production tarif — dogrudan uretime */
  prompt: string;
  stagingHint: string;
  /** Groove ozeti (TR, UI + prompt) */
  groove: string;
  bpmRange: { min: number; max: number };
  bestForAges: string[];
  /** Miks rengi / frekans hissi (EN, prompt) */
  mixColor: string;
  /**
   * Turune ozel GORSEL ritim / canlilik kilidi (EN).
   * Arka plan nabzi, prop bounce, kamera bob — YouTube kids MV enerjisi.
   */
  beatVisuals: string;
}

export const SONG_DURATION_PRESETS = [
  { label: "30 saniye", value: 30 },
  { label: "1 dakika", value: 60 },
  { label: "1.5 dakika", value: 90 },
  { label: "2 dakika", value: 120 },
  { label: "3 dakika", value: 180 },
  { label: "5 dakika", value: 300 },
  { label: "10 dakika", value: 600 },
  { label: "15 dakika", value: 900 },
  { label: "20 dakika", value: 1200 },
] as const;

/**
 * Sure fark etmeksizin (30sn–20dk) acilis + kapanis zanaati.
 * generateSong system promptuna yapisir.
 */
export const SONG_OPENING_CLOSING_CRAFT = `ACILIS + KAPANIS ZANAATI (SURE NE OLURSA OLSUN — KIRMIZI CIZGI):

ACILIS (ilk 1 klip / ilk ~5-8 sn):
- COLD OPEN: ilk saniyelerde sticky hook veya onun mini-versiyonu SOYLENIR. Uzun "merhaba arkadaslar / hadi baslayalim / hos geldiniz" isinmasi YASAK.
- Ilk klip section = intro veya hook. Dinleyici ilk 5 sn'de sarkinin kimligini anlasin.
- Muzikal kimlik (groove + vocalStyle) ilk klibin ilk saniyesinden oturur; yavas yavas "isinma" yok.
- Acilis duygusu: davetkar, net, poster gibi — ama ogretmen emri degil.

KAPANIS (son 1-2 klip):
- Son klipler section = outro (gerekirse bir onceki son nakarat tekrari + outro).
- Tatmin edici final: sticky hook'un son bir tekrari VEYA yumusak reprise + kucuk veda jesti enerjisi (el salla, fisilti, son alkis) — yas-guvenli.
- Ani kesme YASAK: yarim kelime, yarim kafiye, ortada kopmus nakarat yok.
- Dinamik: enerjik stillerde son nakarat zirvesi sonra yumusak inis; ninni/ballad'da gitgide fisiltiya inen soft landing.
- Son soylenen cumle "kapiyi nazikce kapatir" — dinleyici sarki bittiğini hissetsin.
- Outro sozleri kisa ve sticky olsun; yeni mini-hikaye / yeni tema ACMA.`;

/**
 * Hedef sureye gore profesyonel sarki yapi / yay blueprint'i.
 * 30sn singles'tan 20dk uzun singalong'a kadar olceklenir.
 */
export function buildSongArcBlueprint(opts: {
  targetSeconds: number;
  clipCount: number;
  clipSeconds: number;
}): string {
  const { targetSeconds, clipCount, clipSeconds } = opts;
  const minutes = targetSeconds / 60;
  const minutesLabel = minutes >= 1 ? `~${minutes.toFixed(minutes % 1 === 0 ? 0 : 1)} dk` : `${targetSeconds} sn`;
  const chorusEvery = Math.max(3, Math.round(24 / Math.max(4, clipSeconds))); // ~20-25 sn'de bir nakarat
  const midClip = Math.max(2, Math.round(clipCount / 2));
  const lastClip = clipCount;
  const outroStart = Math.max(2, clipCount - (clipCount >= 20 ? 2 : 1));

  const head = [
    `SARKI YAYI / YAPI BLUEPRINT — HEDEF ${targetSeconds} sn (${minutesLabel}), ${clipCount} klip × ${clipSeconds} sn.`,
    `clips.length ZORUNLU ${clipCount}. section etiketlerini asagidaki yaya birebir oturt.`,
    `Nakarat (chorus) sozleri her tekrarda BIREBIR AYNI. Yaklasik her ${chorusEvery} klibe bir chorus donsun (sureye yayilan sticky merkez).`,
    `Orta nokta ~klip ${midClip}. Final / outro ~klip ${outroStart}–${lastClip}.`,
    SONG_OPENING_CLOSING_CRAFT,
  ];

  let body: string;
  if (clipCount <= 5 || targetSeconds <= 45) {
    body = `MIKRO SINGLE (≤~45sn / ≤5 klip):
Yapi sirasi ornegi: hook/intro → kisa verse (veya direkt) → chorus → chorus tekrari → outro.
- Acilis: klip 1'de cold hook (sarkinin en yapiskan cumlesi).
- Orta: tek net fikir; yeni bolum acma.
- Kapanis: son klip outro — hook'un kisa reprise'i + soft veda; ani kesme yok.
- Dolu dolu yaz: kisa sure "ozet sarki" bahanesi degil, yogun sticky single.`;
  } else if (targetSeconds <= 90) {
    body = `KISA SINGLE (~1–1.5 dk):
Yapi: intro/hook → verse 1 → chorus → verse 2 (veya prechorus) → chorus → outro.
- Acilis: 5 sn icinde sticky hook.
- Nakarat en az 2 kez birebir.
- Kapanis: son klip outro — son chorus satiri yumusayarak bitsin veya hook echo + el salla / fisilti.
- Radyo cocuk single hissi: temiz yay, tek omurga.`;
  } else if (targetSeconds <= 180) {
    body = `STANDART MV SINGLE (~2–3 dk):
Yapi: intro/hook → V1 → chorus → V2 → chorus → kisa bridge/prechorus → final chorus (enerji yukari) → outro.
- Acilis: cold open + kimlik.
- Bridge yeni renk getirsin ama yeni sarki olmasin.
- Final chorus en yuksek enerji; hemen ardindan outro soft landing.
- Kapanis 1-2 klip: reprise hook + tatmin edici veda — yarim cumle yok.`;
  } else if (targetSeconds <= 360) {
    body = `UZATILMIS PLAY (~3–6 dk):
Yapi: intro/hook → V1 → chorus → V2 → chorus → bridge → V3 (oyun/prop ilerler) → chorus → final chorus lift → outro.
- Acilis profesyonel MV cold open.
- Her verse ayni omurgayi ilerletsin (yeni prop/oyun adimi); her 20-25 sn'de chorus.
- Orta bolumde (~klip ${midClip}) mini enerji tepesi veya call-response zirvesi.
- Kapanis: final chorus + 1-2 outro klip; hook echo, dinamik inis, net "bitti" hissi.`;
  } else if (targetSeconds <= 720) {
    body = `UZUN SINGALONG (~6–12 dk / 10 dk bandı):
Yapi (bolumler TEK sarki, ayri mini-sarkilar DEGIL):
intro/hook → (V → chorus) x birkaç tur → mid-bridge / oyun zirvesi → (V → chorus) devam → final chorus (en yuksek) → cift outro (yumusama + veda).
- Acilis: ilk 8 sn'de sticky hook; uzun isinma yok.
- Chorus düzenli geri dönsün (yaklasik her ${chorusEvery} klip); sozler sabit.
- Verse'ler hikaye/oyun bolumleri gibi ilerlesin ama tek omurga / tek dunya.
- ~%50'de (klip ${midClip}) belirgin mid-song peak (bridge veya call-response).
- Kapanis (klip ${outroStart}–${lastClip}): final chorus lift → soft outro reprise → nazik veda. Asla ortada kesme.
- Uzun sure = daha cok tekrar + kucuk degisim; yeni tema/vaaz yigini YASAK.`;
  } else {
    body = `EPIC SINGALONG (~12–20+ dk):
Yapi: sinematik kids album journey — TEK sarki omurgasi, bolum bolum ilerleme:
1) COLD OPEN hook (klip 1)
2) Theme cycles: (verse oyun adimi → chorus) tekrarlari
3) Mid-film peak ~klip ${midClip} (bridge / en buyuk call-response / prop zirvesi)
4) Ikinci yari: chorus daha sik veya daha enerjik; omurga ayni
5) FINAL: en buyuk chorus → 2 outro klip (hook reprise + soft landing + veda)
- Acilis: ilk 5-8 sn kimlik; 20 dk'lik "giris konusmasi" YASAK.
- Her ~20-25 sn'de sticky chorus geri gelsin; dinleyici kaybolmasin.
- Verse'ler prop/oyun bolumleri — her biri oncekinin devamı; reset yok.
- Kapanis ZORUNLU ve GUZEL: son 2 klip outro; sarki "bitti" hissi; sticky son cumle; ani kesme yok.
- 20 dk = uzun yolculuk, ama TEK hit sarki gibi baslar ve biter.`;
  }

  return [...head, body].join("\n");
}


/*
 * Tema tanimlari YAPIM BRIEF'idir: kavram + prop + oyun + hook + soz tohumu.
 * Ne kadar zenginse sarki o kadar profesyonel cikar.
 */
export const SONG_THEMES: SongTheme[] = [
  {
    id: "hello",
    label: "Merhaba / gunaydin",
    ageBands: ["1-3", "3-5"],
    tagline: "Dunya uyanir — sen de aitsin; gun seninle baslar",
    description:
      "Sabah bir rutin listesi degil: ev usul usul canlanir ve kahraman 'ben buradayim' hissini kesfeder. Perde, ayna, buharli kase, esneyen ayi — her biri ayni evin parcasi olarak selamlanir. Nakarat bir isik dugmesi gibi: selam verince gun sicakar. Emir yok; aidiyet ve taze baslangic var.",
    moodHint: "sicak ve parlak; 95-110 BPM; ukulele + glockenspiel + hafif el cirpma; sabah ferahligi",
    propBank:
      "acilan perde, ayna, pencereden gunes huzmesi, buharli kase/kahvalti, esneyen oyuncak ayi, sabah terligi — sozde selamlanan HER esya kadroda dokunulabilir durur",
    hookAngle: "Ilk 5 sn: perde acilir / gunes duser ve sticky 'gunaydin' hook soylenir — isinmasi uzun merhaba yok.",
    gameMechanic: "Her kitada evin bir uyesi (esya/arkadas) isimle selamlanir; nakaratta el salla = 'sen de ailesin'.",
    lyricSeedWords: "gunaydin, merhaba, gunes, perde, ayna, ev, sicak, uyan, buradayim, hos geldin",
    lyricSpark:
      "Gunes cebinden cikmaz — pencereden EVE girer. Ayna gulumseyince kahraman kendini tanir. Hook selam degil evet: bugun buradayim. Esneyen ayi komik yan karakter; emir yok.",
    meaningPromise:
      "Yeni bir gun korkutucu degil: ev uyanir, sen de onun parcasin. Sarkinin kalbi 'hos geldin, buradayiz'.",
    verseArc:
      "V1 ev uyanir (perde/gunes). V2 kahraman kendini aynada gorur. V3 sevilen bir sey (ayi/kase) de uyanir. Nakarat ayni sicak hos geldin. Outro fisiltiyla 'iyi ki geldin'.",
    bpmGuide: "95-110",
    arrangementHint: "ukulele + glockenspiel + soft clap; nakaratta kucuk koro eko",
  },
  {
    id: "animals",
    label: "Hayvan dostlari",
    ageBands: ["1-3", "3-5", "6-8"],
    tagline: "Onlari tanidikca yakinlasiriz — ses bir selam, huy bir hikaye",
    description:
      "Hayvanat bahcesi katalogu DEGIL: her kita bir canliyi TANIR. Sesi bir selam, yuruyusu bir karakter, kucuk huyu bir hikaye. 'Kim o?' meraktan dogar; cevap 'dostum o' olur. Siddet/yirticilik yok. Nakarat taklit listesi degil — 'seni anladim' hissi.",
    moodHint: "neseli ve taklitli; 100-120 BPM; banjo/marimba + hayvan sesi vurgulari perkusyon gibi",
    propBank:
      "oyuncak/minik hayvan figuru (pati, kuyruk, kanat, kulak detayli), yem kabı, ot/cimen, su birikintisi — sozde adi gecen hayvan o karede GERCEKTEN gorunur, sadece jestle taklit yetmez",
    hookAngle: "Ilk saniye bir canli sesi + 'kim o?' — cevap hemen 'dostum' ile kapanir, uzun bilmece yok.",
    gameMechanic: "Call: ses. Response: jest + isim. Nakarat: ayni dunya, ayni dostluk — yeni hayvan verse'de gelir, omurga ayni.",
    lyricSeedWords: "dost, pati, kuyruk, kulak, yuva, su, ot, merhaba, yumusak, birlikte",
    lyricSpark:
      "Ses vurus olabilir ama TEK BASINA soz olamaz: miyav = 'ben buradayim'. Her hayvana bir ihtiyac/huy (susadi, utangac, oynaşir). Nakarat 'biz dostuz' sloganı degil; birlikte durma anı.",
    meaningPromise:
      "Farkli canlilar korkutucu degil: seslerini tanidikca yakinlasiriz. Sarkinin kalbi meraktan dostluga gecmek.",
    verseArc:
      "V1 ilk ses + tanisma. V2 ikinci canli + kucuk huy. V3 birlikte bir sey (su/ot/yuva). Nakarat ayni 'anladim seni'. Outro yan yana sessiz gulumse.",
    bpmGuide: "100-120",
    arrangementHint: "marimba + banjo + animal SFX as percussion hits",
  },
  {
    id: "colors",
    label: "Renkler",
    ageBands: ["1-3", "3-5"],
    tagline: "Renk bir hazine — bakan goz dunyayi daha sicak gorur",
    description:
      "Renk ezberi DEGIL: kahraman bakmayi ogrenir. Kirmizi cilekte, sari limonda, mavi balonda saklidir — her renk bir NESNEDE yasamadir. Nakarat renk listesi degil; 'gordum, isiklandi' hissi. Arama oyunu sozun icinde, ogretmen 'bakalim'i yok.",
    moodHint: "parlak pop; 105-118 BPM; parlak synth + el cirpma; renk adlari vurusa oturur",
    propBank:
      "renkli balon, boya kavanozu, cilek, limon, konfeti, gokkusagi kemer — sozde gecen RENK bir nesnenin boyasinda net gorunur; bos arka plan yetmez",
    hookAngle: "Ilk 5 sn tek renk + o rengin nesnesi close-up; hook 'gordum' / 'parliyor' — uzun bak-bak yok.",
    gameMechanic: "Her kita bir renk BIR nesnede kesfedilir; nakarat ayni bakma sevinci; verse yeni hazine.",
    lyricSeedWords: "kirmizi, sari, mavi, yesil, cilek, limon, balon, parliyor, gordum, sicak",
    lyricSpark:
      "Renk soyut kelime degil saklanmis hazine. Hook tek nesne + tek renk. Nakarat 'dunya dolu' hissi — kirmizi-sari-mavi ezberi YASAK.",
    meaningPromise:
      "Dikkatle bakinca siradan sey parlar. Sarkinin kalbi kesfetmenin mutlulugu — renk bir etiket degil, bir duygu.",
    verseArc:
      "V1 ilk hazine (or. kirmizi cilek). V2 ikinci (sari limon) + kucuk surpriz. V3 renkler yan yana ayni masada. Nakarat 'gordum, parliyor'. Outro gokkusagi degil, sessiz bakis.",
    bpmGuide: "105-118",
    arrangementHint: "bright synth pluck + claps; color names on downbeats",
  },
  {
    id: "body",
    label: "Eller, ayaklar, burun",
    ageBands: ["1-3", "3-5"],
    tagline: "Bedeminle dunyaya dokun — her uzuv bir is, bir his",
    description:
      "Uzuv ezberi / 'tap tap burun tik' listesi YASAK. Sarkı su anlati: ellerim tutar, ayaklarim tasir, burnum koklar — bedenimle buradayim. Her kita bir uzuv BIR ise yarar (topu tut, yola bas, buhari kokla). Yanlis hareket gulunur, ceza yok. Guvenli, dusme/akrobasi yok.",
    moodHint: "hareketli oyun sarkisi; 96-112 BPM; dur-kalk ritmi, firca davul + ziller",
    propBank:
      "boy aynasi, yumusak top, eldiven/corap, buharli kase veya cicek — isaret edilen uzuv + o uzvun IS YAPTIGI prop ayni karede",
    hookAngle: "Ilk satir bir uzuv + onun isi (el topu tutar / ayak yola basar) — 'goster' emri yok.",
    gameMechanic: "Dur-kalk oyun: muzik durunca o uzuv isi bitirir; hata = gulumse. Nakarat 'ben buradayim' hissi.",
    lyricSeedWords: "el, ayak, burun, tut, bas, kokla, ayna, top, yol, buradayim",
    lyricSpark:
      "Yansima ses CESNI olabilir (tak/hop) ama tek basina dize YASAK. El-ayak-burun bir DANS LISTESI degil; her uzuv bir anlam tasir. KOTU: 'ayak tap tap, burun tik tik'. IYI: 'ayaklarim yol bilir / burnum evi koklar / ellerim seninle alkislar'.",
    meaningPromise:
      "Bedenim oyuncak degil, dunyaya uzanan yolum. Sarkinin kalbi: yapabildigimi hissetmek, gurur ve oyun.",
    verseArc:
      "V1 ayaklar bir yere varir. V2 eller bir seyi tutar/paylasir. V3 burun/yuz bir seyi tanir (koku, ayna). Nakarat ayni 'ben buradayim'. Outro yavas nefes + gulumse.",
    bpmGuide: "96-112",
    arrangementHint: "stop-go drums + woodblock accents on body parts",
  },
  {
    id: "vehicles",
    label: "Araba, tren, ucak",
    ageBands: ["1-3", "3-5"],
    tagline: "Bir yere varmak — sesler yolda, kalp evde",
    description:
      "Vin-cuf-viiiin katalogu DEGIL: kahraman BIR yere gider (nine, park, ev). Tasit sesi yolun nabzi; vagon sayisi yalnizca o yolun parcasi. Nakarat 'gidelim' emri degil 'varacagiz' umudu. Sayma calismasi yasak; macera omurgasi var.",
    moodHint: "ritmik tekerleme; 100-116 BPM; motor/ray sesleri perkusyona islenmis, yurutucu bas",
    propBank:
      "KRITIK: oyuncak tren + SAYILABILIR vagonlar (tekerlek, kaplin, pencere detayli), ray, direksiyonlu araba, kucuk ucak, pencere manzarasi — sozde sayi varsa o sayida nesne; yolun NEDENI (canta, cicek, ev isigi) da gorunur",
    hookAngle: "Ilk saniye kalkis SFX + 'yola cikti' hook; hedef bir kelimede (eve / nineye / parka).",
    gameMechanic: "Call: tasit sesi. Response: ayni ses + bir adim ilerleme. Nakarat varis umudu; verse yeni durak.",
    lyricSeedWords: "yol, ev, pencere, vagon, tekerlek, ray, varis, merhaba, canta, birlikte",
    lyricSpark:
      "Ses cesni: vin/cuf. Asil soz NEREVE ve NEDEN. KOTU: 'vin vin cuf cuf'. IYI: 'uc kirmizi vagon nineye gider / pencereden ev isigi yanar'.",
    meaningPromise:
      "Yolculuk oyuncak degil: sevilen bir yere ulasmak. Sarkinin kalbi 'yoldayiz, varacagiz'.",
    verseArc:
      "V1 kalkis + hedef. V2 yolda kucuk aksilik (vagon gecikir, ruzgar). V3 varis / isik / kucak. Nakarat ayni yolda-olma. Outro duran tekerlek + nefes.",
    bpmGuide: "100-116",
    arrangementHint: "engine/rail SFX as percussion + bouncy bass",
  },
  {
    id: "bedtime",
    label: "Iyi geceler",
    ageBands: ["1-3", "3-5"],
    tagline: "Gece guvenli — ev nefes alir, sen de birakirsin",
    description:
      "Uyku emri DEGIL: gun yumusakca kapanir ve kahraman birakmayi ogrenir. Oyuncaklar, lamba, ay — her biri 'yarin da buradayiz' der. Karanlik korku yok; gece sicak bir cubbe. Nakarat fisiltiya iner cunku soz gercekten yavaslar.",
    moodHint: "ninni; 70-85 BPM; muzik kutusu + yumusak piyano + pes yayli pedal; dinamik gitgide kisilir",
    propBank:
      "battaniye, yastik, gece lambasi, ay isigi pencerede, yildiz mobil, uyuyan oyuncak — veda edilen her esya yumusak malzeme/isikla durur",
    hookAngle: "Ilk 5 sn lamba yanar + fisilti 'iyi geceler' — uzun gun ozeti yok.",
    gameMechanic: "Her kita bir seye nazik veda; dinamik her turda yumusar; final neredeyse nefes.",
    lyricSeedWords: "iyi geceler, yildiz, ay, battaniye, lamba, usul, yarin, buradayim, ruya, saril",
    lyricSpark:
      "Ninni siir: kisa, duyusal, emirsiz. Battaniye cubbe, ay pencere bekcisi. 'Uyu artik' YASAK. Hook 'yarin da buradayiz' hissi.",
    meaningPromise:
      "Birakmak kaybetmek degil. Sarkinin kalbi: gece guvenli, sevdiklerin yarin da evde.",
    verseArc:
      "V1 lamba + ev yavaslar. V2 oyuncaga / pencereye veda. V3 kahraman da birakir (gozler). Nakarat ayni fisilti. Outro neredeyse sessiz 'iyi geceler'.",
    bpmGuide: "70-85",
    arrangementHint: "music box + felt piano + soft pad fade-out",
  },
  {
    id: "counting",
    label: "Sayalim",
    ageBands: ["3-5", "6-8"],
    tagline: "Sayilar bir seyi toplar — her rakam bir arkadas",
    description:
      "Matematik dersi DEGIL: saymak, dunyadaki seyleri BIR ARAYA getirmektir. 3 ordek bir aile, 5 balon bir parti. Nakarat rakam ezberi degil 'hepsi burada' sevinci. Geri sayim bir kayip degil, oyunun nefesidir. Bos havaya parmak YASAK.",
    moodHint: "net vurgulu; 104-120 BPM; marimba + parmak siklatma; sayilarda dur-vur oyunu",
    propBank:
      "KRITIK: sozde gecen SAYI kadar nesne kadroda AYRI AYRI (balon, ordek, kabarcik, blok) — ayni aile/grup gibi dururlar; bos hava YASAK",
    hookAngle: "Ilk saniye 'bir!' + ilk nesne close-up; hemen 'yanina bir tane daha' hissi.",
    gameMechanic: "Her sayi bir nesneyi gruba katar; nakarat 'hepsi burada'; geri sayim oyunun nefesidir.",
    lyricSeedWords: "bir, iki, uc, birlikte, yanina, balon, ordek, sirada, burada, alkis",
    lyricSpark:
      "Sayi NESNEYE + ANLAMA yapisir. KOTU: 'bir iki uc sayalim'. IYI: 'bir sari yalnizdi / iki geldi / uc oldu bir koro'. Matematik vaazi yok.",
    meaningPromise:
      "Saymak ayirmak degil, bir araya getirmektir. Sarkinin kalbi: yalniz bir, birlikte cok.",
    verseArc:
      "V1 ilk nesne yalniz. V2 ikinci/ucuncu katilir. V3 grup tamam / kucuk eksik bulunur. Nakarat 'hepsi burada'. Outro geri sayim = yumusak kapanis, yok olma degil.",
    bpmGuide: "104-120",
    arrangementHint: "marimba counts + finger snaps on numbers",
  },
  {
    id: "wash",
    label: "Ellerimizi yikayalim",
    ageBands: ["1-3", "3-5", "6-8"],
    tagline: "Kopuk bir donusum — kir gider, eller yeniden evin olur",
    description:
      "Hijyen vaazi / 'yika yika temiz ol' DEGIL. Sarkı bir donusum anlati: kirli eller oyun izi tasir, su+sabun bir bulut olur, havlu sicak bir son dokunus. Pit-pit cesni olabilir ama anlam 'yeniden hazirim / sofra / sarilma'ya akar.",
    moodHint: "eglenceli rutin; 108-122 BPM; kopuk 'pop' perkusyonu + islikli melodi + el cirpma",
    propBank:
      "musluk, akan su, sabun kalibi, kopuk bulutu, bugulu ayna, havlu — her adim fiziksel; finalde temiz eller bir ISE yarar (kase, kapı, sarilma)",
    hookAngle: "Ilk 5 sn musluk + kopuk close-up; hook 'bulut avucuma konar' — 'yika!' emri yok.",
    gameMechanic: "Su-sabun-kopuk-havlu bir hikaye sirasi; nakarat donusum sevinci, temizlik slogani degil.",
    lyricSeedWords: "kopuk, musluk, havlu, mis, sicak, avuc, ayna, yeniden, sofra, saril",
    lyricSpark:
      "Kopuk = bulut / inci. KOTU: 'ellerimizi yikayalim temiz olalim'. IYI: 'kopuk bulut avucuma konar / havlu sicacik / ellerim sofra icin hazir'.",
    meaningPromise:
      "Bakim bir ceza degil, sevdiklerine donus. Sarkinin kalbi: ellerim yeniden evin eli.",
    verseArc:
      "V1 kirli/oyun izi + musluk. V2 kopuk donusumu. V3 havlu + yeni bir is (sofra/kapı). Nakarat ayni sicak donusum. Outro ayna gulumseme.",
    bpmGuide: "108-122",
    arrangementHint: "bubble pop SFX percussion + whistle melody",
  },
  {
    id: "tidy",
    label: "Toplama zamani",
    ageBands: ["3-5", "6-8"],
    tagline: "Her seyin bir yuvasi var — daginiklik bir macera, duzen bir kucak",
    description:
      "'Topla!' odevi DEGIL: daginik oda bir orman, her oyuncagin bir yuvasi var. Kahraman onlari evlerine goturur. Kayip oyuncak korkusuz surpriz; bulununca ev tamam olur. Kimse kaybetmez.",
    moodHint: "enerjik ama nazik; 110-124 BPM; ksilofon kosulari + alkis + ritim durduran 'tak' vurgusu",
    propBank:
      "oyuncak kutusu, raf, sepet, daginik bloklar/ayilar/kitaplar — her oyuncak hareket eder ve 'tak' ile yuvasina oturur",
    hookAngle: "Ilk saniye daginik oda + 'yuvana don' hook — 'toplama zamani' emri yok.",
    gameMechanic: "Her kita bir oyuncak yuvasini bulur; nakarat ev tamam hissi; final kayip-bulundu.",
    lyricSeedWords: "yuva, kutu, raf, sepet, tak, evinde, kayip, buldum, alkis, usul",
    lyricSpark:
      "Oyuncak ucar/kayar/tak. KOTU: 'hadi toplayalim'. IYI: 'ayi rafa uzandi / bloklar kutusunu ozur diledi / tak — ev tamam'.",
    meaningPromise:
      "Duzen ceza degil, her seyin evine donmesi. Sarkinin kalbi: yuva bulununca icimiz rahatlar.",
    verseArc:
      "V1 ilk oyuncak yuvasina. V2 ikincisi + kucuk karisiklik. V3 kayip bulunur. Nakarat 'ev tamam'. Outro sakin oda + nefes.",
    bpmGuide: "110-124",
    arrangementHint: "xylophone runs + clap hits on 'tak'",
  },
  {
    id: "sharing",
    label: "Paylasmak guzel",
    ageBands: ["3-5", "6-8"],
    tagline: "Bir seyi ikiye bolunce iki kalp aydinlanir",
    description:
      "Vaaz DEGIL: kahraman bir seye sahip, sonra yarisi uzatir — ve birden yalniz degildir. Kurabiye, boya, salincak olayin araci. Surpriz: paylasinca yeni bir oyun dogar. 'Paylasmak Guzeldir' slogani tek basina yasak.",
    moodHint: "sicak koro; 96-112 BPM; akustik gitar + cocuk korosu ekosu; nakaratta cift ses",
    propBank:
      "bolunebilir kurabiye, iki firca + boya, salincak, paylasilan top — nesne iki ele uzatilmis halde net",
    hookAngle: "Ilk 5 sn bir sey ikiye bolunur + 'seninle' — slogan yok.",
    gameMechanic: "Her kita bir uzatma jesti; nakarat iki ses; verse'de paylasimin meyvesi (yeni oyun).",
    lyricSeedWords: "yarisi, senin, uzat, kurabiye, boya, salincak, birlikte, iki, gulumse, biz",
    lyricSpark:
      "Once sahip ol, sonra uzat, sonra surpriz. KOTU: 'paylasmak guzeldir'. IYI: 'kurabiyeyi ikiye boldum / senin yarın sicakti / simdi ikimiz de guluyoruz'.",
    meaningPromise:
      "Vermek eksilmek degil, yakinlasmaktir. Sarkinin kalbi: seninle olunca tatlilik ikiye cikar.",
    verseArc:
      "V1 tek basina bir sey. V2 uzatma jesti. V3 birlikte yeni oyun. Nakarat ayni 'seninle'. Outro iki el, bir nesne.",
    bpmGuide: "96-112",
    arrangementHint: "acoustic guitar + soft group-harmony doubles on chorus",
  },
  {
    id: "friendship",
    label: "Arkadaslik",
    ageBands: ["3-5", "6-8"],
    tagline: "Yikilinca da yanindayim — birlikte yeniden, birlikte kutla",
    description:
      "Arkadaslik nutku DEGIL: iki kisi bir sey kurar, yikilir, guler, yeniden dener. Isim cagirma samimi; dislama/siddet yok. Nakarat 'birlikte' slogani degil 'seninle yeniden' vaadi.",
    moodHint: "parlak cocuk pop; 112-126 BPM; el cirpma + parlak synth + kucuk koro 'hey!' vuruslari",
    propBank:
      "renkli blok kulesi, paylasilan oyuncak, iki elin tutusmasi, yapboz parcasi — birlikte yapilan isin proplari",
    hookAngle: "Ilk saniye isim + el / kule — 'arkadaslik guzeldir' yok.",
    gameMechanic: "Aksilik → gül → birlikte yeniden; nakarat ayni vaat; verse yeni deneme.",
    lyricSeedWords: "isim, yeniden, kule, yapboz, el ele, guldum, yardim, biz, yaninda, hey",
    lyricSpark:
      "Sahne: kule duser, eller tutulur. KOTU: 'arkadaslik cok guzel'. IYI: 'kule yikildi, sen kaldin / iki el, bir kule daha'.",
    meaningPromise:
      "Gercek dost, isler yolunda gitmeyince de kalir. Sarkinin kalbi: seninle yeniden denemek.",
    verseArc:
      "V1 birlikte kurma. V2 yikilma + gülme. V3 yeniden + daha sicak. Nakarat 'yanindayim'. Outro omuz omuza.",
    bpmGuide: "112-126",
    arrangementHint: "bright-pop claps + synth + choir 'hey!' before chorus",
  },
  {
    id: "weather",
    label: "Gunes, yagmur, ruzgar",
    ageBands: ["3-5", "6-8"],
    tagline: "Hava degisir, sen kalirsin — her gokyuzunun bir oyunu var",
    description:
      "Hava raporu DEGIL: gokyuzu degisir, kahraman uyum saglar. Yagmurda birikinti, ruzgarda yaprak, guneste sicaklik — her hava bir davet. Firtina/korku yok. Nakarat 'her havada yerin var'.",
    moodHint: "degisken ama neseli; 100-118 BPM; yagmur damlasi perkusyonu + parlak nakarat patlamasi",
    propBank:
      "gunes sapkasi, su birikintisi, renkli cizme, semsiye, ucusan yaprak, gokkusagi — her havanin fiziksel izi",
    hookAngle: "Ilk 5 sn bir hava izi (damla/yaprak) + 'bugun boyle' hook — 'bak hava' ogretmenligi yok.",
    gameMechanic: "Her kita bir hava + o havaya uygun oyun; nakarat ayni aidiyet.",
    lyricSeedWords: "yagmur, gunes, ruzgar, birikinti, semsiye, yaprak, sicak, serin, bugun, oyun",
    lyricSpark:
      "Hava bir ruh hali. KOTU: 'gunes yagmur ruzgar sayalim'. IYI: 'damla burnuma kondu / cizmem guldü / semsiyem evim oldu'.",
    meaningPromise:
      "Dunya degisse de senin bir oyununu vardir. Sarkinin kalbi: havaya küsme, ona katıl.",
    verseArc:
      "V1 ilk hava + ilk oyun. V2 degisim + uyum. V3 ucuncu hava veya gokkusagi barisi. Nakarat 'yerin var'. Outro sakin gokyuzu.",
    bpmGuide: "100-118",
    arrangementHint: "raindrop percussion + bright chorus lift",
  },
  {
    id: "days",
    label: "Haftanin gunleri",
    ageBands: ["3-5", "6-8"],
    tagline: "Hafta bir yolculuk — her gunun kucuk bir kalbi var",
    description:
      "Takvim ezberi DEGIL: hafta bir tren yolculugu, her gunun kucuk bir olayı (corba, park, sarilma). Gun adi vurusa oturur ama ANLAM o gunku olaydadir. Hafta sonu zirve = dinlenme/sevinc, bagirma degil.",
    moodHint: "ritmik liste; 104-120 BPM; tren ritmi + zil vuruslari; gun adlari vurusa kilitli",
    propBank:
      "7 vagonlu gun treni (renkli vagonlar), takvim yapragi, gune ozel esya (corba, top, kitap) — gun adi + o gunku NESNE birlikte",
    hookAngle: "Ilk saniye tren + pazartesi + o gunku kucuk olay (corba/okul cantasi).",
    gameMechanic: "Her kita 1-2 gun + o gunlerin olayı; nakarat 'hafta bizi tasiyor'; son kita hafta sonu sicakligi.",
    lyricSeedWords: "pazartesi, cuma, pazar, tren, vagon, ev, park, corba, yarin, birlikte",
    lyricSpark:
      "Gun adi TEK BASINA dize olamaz. KOTU: 'pazartesi sali carsamba'. IYI: 'pazartesi corba kokar / cuma kapida top / pazar evde yavas'.",
    meaningPromise:
      "Zaman korkutucu bir liste degil, tanidik bir yol. Sarkinin kalbi: her gunun evde bir yeri var.",
    verseArc:
      "V1 hafta basi (kalkis). V2 orta gunler + kucuk yorgunluk/oyun. V3 hafta sonu ev. Nakarat ayni yolculuk. Outro pazar aksamı yumusama.",
    bpmGuide: "104-120",
    arrangementHint: "train-chug groove + bell hits on day names",
  },
  {
    id: "emotions",
    label: "Mutlu, uzgun, sakin",
    ageBands: ["6-8"],
    tagline: "Hisler bulut gibi — gelir, kalir biraz, gecer; sen kalirsin",
    description:
      "Duygu sozlugu DEGIL: kisa, guvenli sahneler. Mutluluk bir isik, uzuntu bir yumusak yagmur, sakinlik bir nefes. Travma/terk/ceza yok. Nakarat 'gecer, yanindayim' — his sen degilsin, yanindaki var.",
    moodHint: "yumusak, umutlu; 88-104 BPM; piyano + yaylilar; nakaratta majore aydinlanan armoni",
    propBank:
      "ayna, yumusak mendil, sicak isik, yumusak yagmur, sarilma battaniyesi — duygu yuz + prop ile",
    hookAngle: "Ilk 5 sn yuz degisir + 'bu da gecer' / 'yanindayim' — ders anlatimi yok.",
    gameMechanic: "Her kita bir his sahnesi; nakarat guven; final sakin gulumse.",
    lyricSeedWords: "mutlu, uzgun, sakin, nefes, yanindayim, gecer, mendil, isik, yumusak, umut",
    lyricSpark:
      "His bir hava. KOTU: 'mutlu uzgun sakin olalim'. IYI: 'icim gunes / bir damla indi / nefesim evi isitti'.",
    meaningPromise:
      "Hisler gelip gider; sen ve sevdigin kalir. Sarkinin kalbi: yalniz degilsin, bu da gecer.",
    verseArc:
      "V1 parlak his. V2 kisa uzuntu + yaninda biri/prop. V3 sakin nefes. Nakarat ayni guven. Outro gulumse.",
    bpmGuide: "88-104",
    arrangementHint: "piano + strings; chorus brightens to major",
  },
  {
    id: "courage",
    label: "Cesaret sarkisi",
    ageBands: ["6-8"],
    tagline: "Korku buyumez — bir nefes, bir adim, bir kucuk evet",
    description:
      "Kahraman nutku DEGIL: esikte durmak, nefes almak, bir adim. Kaydirak, merhaba, dugme — zafer kucuk ve gercek. Korku buyutulmez, alay yok. Nakarat 'yapabilirim' degil 'bir adim daha'.",
    moodHint: "yukselen; 100-118 BPM; kademeli guclenen davul + parlak bakir final",
    propBank:
      "kaydirak basamagi, el feneri, isik dugmesi, gece lambasi, kapi esigi — cesaretin MEKANI kadroda",
    hookAngle: "Ilk saniye esik close-up + 'bir adim' — kahraman sloganı yok.",
    gameMechanic: "Her kita bir kucuk evet; nakarat nefes+adim; final gercekci kucuk zafer.",
    lyricSeedWords: "adim, nefes, esik, merhaba, dugme, kaydirak, birlikte, yumusak, evet, sonra",
    lyricSpark:
      "KOTU: 'ben cesurum yapabilirim'. IYI: 'esikte durdum / bir nefes / dugmeye evet — isik yandi'.",
    meaningPromise:
      "Cesaret bagirmak degil, kucuk bir evet demektir. Sarkinin kalbi: korku varken de bir adim.",
    verseArc:
      "V1 esikte durma. V2 nefes + ilk dokunus. V3 adim atildi + sicak sonuc. Nakarat 'bir adim daha'. Outro sakin gurur.",
    bpmGuide: "100-118",
    arrangementHint: "building drums + bright brass sting on victory",
  },
  {
    id: "differences",
    label: "Herkes ozel",
    ageBands: ["6-8"],
    tagline: "Ayni resim, farkli parcalar — sen eksik degilsin, sen parcasin",
    description:
      "'Herkes ozel' vaazi DEGIL: yapbozda farkli parcalar ayni resmi tamamlar. Alay/dislama yok. Nakarat kutlama; her kita bir parcayi gosterir, sonra yerine oturtur.",
    moodHint: "sicak koro; 100-116 BPM; dunya perkusyonu + cok sesli mirilti + birlikte final",
    propBank:
      "farkli renkli yapboz parcalari, cesitli bloklar, farkli desenli sallar — cesitlilik GORUNUR",
    hookAngle: "Ilk 5 sn iki farkli parca yan yana + 'ayni resim' hook.",
    gameMechanic: "Her kita bir parcayi tanir; nakarat resmi tamamlar.",
    lyricSeedWords: "parca, yapboz, renk, sen, ben, yerine, tamam, birlikte, resim, uyum",
    lyricSpark:
      "KOTU: 'herkes ozeldir kutlayalim'. IYI: 'senin kenarin egri / benimki duz / tak — resim ev oldu'.",
    meaningPromise:
      "Farkli olmak disi olmak degil, resmi tamamlamaktir. Sarkinin kalbi: sen de bu evin parcasisin.",
    verseArc:
      "V1 iki farkli parca. V2 uymuyor gibi / sonra oturur. V3 resim tamam. Nakarat aidiyet. Outro yan yana bakis.",
    bpmGuide: "100-116",
    arrangementHint: "world percussion + layered hums into unison chorus",
  },
  {
    id: "seasons",
    label: "Mevsimler",
    ageBands: ["6-8"],
    tagline: "Ayni agac, dort yuz — zaman doner, kok ayni kalir",
    description:
      "Mevsim listesi DEGIL: tek bir agac / tek bir ev doner. Ilkbahar cicek, yaz isik, sonbahar yaprak, kis kar — tempo sabit, tını degisir. Nakarat 'ben ayni yerdeyim'.",
    moodHint: "renkli, donusumlu; 96-114 BPM; mevsime gore degisen tinilar, SABIT tempo ve nakarat",
    propBank:
      "ayni agacin mevsim hali, yaprak/kar/cicek/deniz kabugu, mevsimlik kiyafet — doku ve renk net",
    hookAngle: "Ilk saniye ayni agac + ilk doku (cicek veya yaprak) — ezber adi yok.",
    gameMechanic: "Her kita bir mevsim DOKUSU; nakarat ayni kok; aranjman tınısi degisir.",
    lyricSeedWords: "agac, cicek, yaprak, kar, isik, doner, ayni, ev, ruzgar, kok",
    lyricSpark:
      "KOTU: 'ilkbahar yaz sonbahar kis'. IYI: 'ayni dal cicek acti / sonra yaprak ugurladi / kar onu orter — kok durur'.",
    meaningPromise:
      "Her sey degisir, sevilen yer kalir. Sarkinin kalbi: zaman doner, ev/agac/sen ayni omurgadasin.",
    verseArc:
      "V1 ilk mevsim dokusu. V2 ikinci. V3 ucuncu+dorduncu veya kis uykusu. Nakarat ayni kok. Outro ayni agac, sakin.",
    bpmGuide: "96-114",
    arrangementHint: "fixed tempo; timbre swaps per season (flute/guitar/chimes/soft pad)",
  },
  {
    id: "family",
    label: "Aile ve sarilma",
    ageBands: ["1-3", "3-5", "6-8"],
    tagline: "Halka genisler — sofra, masal, bir cift kol yeter",
    description:
      "Aile nutku DEGIL: kapi acilir, bir yer acilir, bir kol uzanir. Sofra, masal, battaniye halkayi somutlar. Nakarat 'kocaman saril' bir slogan degil, gercek bir jest. Guven, yakinlik; kimse yok sayilmaz.",
    moodHint: "sicak, kucaklayan; 88-104 BPM; akustik gitar + hafif yaylilar + yumusak koro",
    propBank:
      "sofra / buharli kase, battaniye cadiri, masal kitabi, kapi, el ele — dokunulabilir",
    hookAngle: "Ilk 5 sn kapi veya sofra + 'hos geldin' / sarilma — 'aile cok onemli' yok.",
    gameMechanic: "Her kita halkaya bir uye/jest girer; nakarat ayni kucak.",
    lyricSeedWords: "saril, sofra, masal, kapi, ev, sicak, el, yerin, buradayiz, kocaman",
    lyricSpark:
      "KOTU: 'ailemi cok seviyorum'. IYI: 'kapı aralandi / corba buhari / senin yerin masada duruyor'.",
    meaningPromise:
      "Sevilmek bir soz degil, bir yer acilmaktir. Sarkinin kalbi: senin yerin burada, kucak hazir.",
    verseArc:
      "V1 kapi/sofra. V2 masal veya battaniye. V3 halka tamam / kocaman saril. Nakarat ayni yer. Outro fisilti 'buradayiz'.",
    bpmGuide: "88-104",
    arrangementHint: "warm acoustic guitar + soft strings + gentle choir",
  },
  {
    id: "nature",
    label: "Agac, cicek, kus",
    ageBands: ["3-5", "6-8"],
    tagline: "Once dinle — bahce konusur, sen misafirsin",
    description:
      "Doga belgeseli / isim listesi DEGIL: kahraman bahceye misafir olur. Once dinler (kus, ciy), sonra kucuk bir seyi gorur (tohum, ari). Ezmeden, buyutec netliginde. Nakarat hayret, vaaz degil.",
    moodHint: "ferah, akustik; 92-110 BPM; akustik gitar + flut + kus sesi suslemeleri; dinle-patlat dinamigi",
    propBank:
      "tohum/toprak, cicek, ari veya ugur bocegi, kus + yuva, ciy damlasi, yaprak damarlari — buyutec netligi",
    hookAngle: "Ilk 5 sn sessizlik + bir canli sesi — 'dinle!' emri yok, merak var.",
    gameMechanic: "Dinle → gor → nazik dokunma; nakarat hayret.",
    lyricSeedWords: "dinle, tohum, ari, ciy, yaprak, yuva, usul, gordum, misafir, yesil",
    lyricSpark:
      "KOTU: 'agac cicek kus sevelim'. IYI: 'ciy yapragi uyandirdi / ari isini fisildadi / ben usul usul bakiyorum'.",
    meaningPromise:
      "Doga bir sahne degil, ev sahipliği yapan bir dunya. Sarkinin kalbi: yavasla, duy, ezme.",
    verseArc:
      "V1 dinleme. V2 kucuk kesif. V3 nazik vedasiz kalma / tohum. Nakarat hayret. Outro sessiz bahce.",
    bpmGuide: "92-110",
    arrangementHint: "acoustic guitar + flute + bird-call ornaments",
  },
  {
    id: "wonder",
    label: "Merak / ilk kez",
    ageBands: ["1-3", "3-5", "6-8"],
    tagline: "Ilk kez gormek — kucuk sey, kocaman 'aa!'",
    description:
      "Kahraman dunyada ILK KEZ bir seyi fark eder: kabarcik, anahtar deligi, ayakkabi bagcigi, bocek. Tema 'aa!' hayretidir, ansiklopedi degil. Nakarat merakın sicakligi; cevap bazen basit, bazen yarim kalir — o da guzel.",
    moodHint: "merakli, parlak; 98-114 BPM; pizzicato + celesta + kucuk susleme; soru-cevap nefesi",
    propBank:
      "buyutec veya yuvarlak cam, kabarcik, anahtar, bagcik, ugur bocegi, kutu kapagi — 'ilk kez' nesnesi close-up okunur",
    hookAngle: "Ilk 5 sn kucuk nesne close-up + 'aa / ne bu?' hook — uzun aciklama yok.",
    gameMechanic: "Her kita yeni bir kucuk kesif; nakarat ayni hayret; verse cevabi biraz ilerletir.",
    lyricSeedWords: "aa, ne bu, kucuk, parliyor, ac, kutu, cam, usul, gordum, acaba",
    lyricSpark:
      "Soru samimi olsun. KOTU: 'merak etmek guzeldir'. IYI: 'kutu tikti / kapak aralandi / icinde bir isik — aa, sen misin?'",
    meaningPromise:
      "Dunya bitmez bir ders degil, kucuk mucizelerle dolu. Sarkinin kalbi: bakmaya deger, sormaya deger.",
    verseArc:
      "V1 ilk 'aa'. V2 ikinci nesne veya ayni nesnenin yeni yuzu. V3 kucuk cevap veya birlikte bakma. Nakarat hayret. Outro yavas 'acaba' fisiltisi.",
    bpmGuide: "98-114",
    arrangementHint: "pizzicato strings + celesta sparkle + soft question-pause",
  },
  {
    id: "kindness",
    label: "Kucuk iyilik",
    ageBands: ["3-5", "6-8"],
    tagline: "Bir el, bir yer, bir tesekkur — iyilik buyumeden is gorur",
    description:
      "Kahraman kucuk bir iyilik yapar: dusen sali verir, kapıyı tutar, bir yudum su uzatir. Nutuk yok. Nakarat 'ben de yapabilirim' degil 'senin icin bunu'. Tesekkur samimi, odul yok.",
    moodHint: "sicak midtempo; 94-110 BPM; akustik + yumusak clap + koro eko",
    propBank:
      "dusen sal, su bardaği, kapı kolu, yara bandi (korkusuz), paylasilan bank — iyiligin NESNESI net",
    hookAngle: "Ilk 5 sn bir ihtiyac gorulur + kucuk jest — vaaz yok.",
    gameMechanic: "Her kita bir kucuk iyilik; nakarat ayni sicak jest; verse yeni kisi/prop.",
    lyricSeedWords: "uzat, tut, ver, tesekkur, sal, su, kapi, usul, seninicin, gulumse",
    lyricSpark:
      "KOTU: 'iyilik yapmak guzeldir'. IYI: 'salin dustu / ben egildim / senin omzun yine sicak'.",
    meaningPromise:
      "Buyuk kahramanlik gerekmez; bir jest yeter. Sarkinin kalbi: gorulmek ve gormek.",
    verseArc:
      "V1 bir ihtiyac + jest. V2 tesekkur veya ikinci jest. V3 iyilik geri gelir (surpriz). Nakarat ayni el. Outro iki gulumse.",
    bpmGuide: "94-110",
    arrangementHint: "warm acoustic + soft claps + gentle choir echo",
  },
  {
    id: "kitchen",
    label: "Mutfak / birlikte pisir",
    ageBands: ["3-5", "6-8"],
    tagline: "Un, buhar, beklemek — birlikte yapmak ayni yemegi tatmak",
    description:
      "Yemek tarifi ezberi DEGIL: un ucusar, hamur yapisir, buhar kokar, beklemek ogrenilir. Tehlike yok (ates/bicak yok — soguk hamur, meyve, cokme). Nakarat birlikte beklemenin tadı.",
    moodHint: "sicak swing; 100-114 BPM; woodblock + kaşık perkusyonu + akustik",
    propBank:
      "un bulutu, tahta kaşık, hamur topagi, meyve dilimleri, onluk, buğulu tepsi — mutfak NESNELERI; ateş/bıçak yok",
    hookAngle: "Ilk 5 sn un/kaşık + 'karistiriyoruz' / 'kokuyor' hook.",
    gameMechanic: "Karistir-bekle-tat; nakarat birlikte; verse yeni malzeme veya bekleme.",
    lyricSeedWords: "un, hamur, kaşık, buhar, bekle, tatli, birlikte, onluk, kokuyor, puf",
    lyricSpark:
      "KOTU: 'hadi kek yapalim'. IYI: 'un bulut oldu / hamur elime yapisti / beklerken seninle saydik'.",
    meaningPromise:
      "Birlikte sabretmek, yemegin kendisi kadar tatlıdır. Sarkinin kalbi: yapmak + beklemek + paylaşmak.",
    verseArc:
      "V1 malzemeler dagilir. V2 karisim + kucuk aksilik (un). V3 bekleme + tatma/paylasma. Nakarat birlikte. Outro sicak koku.",
    bpmGuide: "100-114",
    arrangementHint: "woodblock spoons + acoustic guitar + warm kitchen clinks",
  },
  {
    id: "custom",
    label: "Ozel tema (konu kutusundan)",
    ageBands: ["1-3", "3-5", "6-8"],
    tagline: "Senin fikrin — bir duygu, bir sahne, bir sticky nakarat",
    description:
      "Konu kutusundaki fikir hit sarki olur: once ANLAM (ne hissedilecek), sonra sahne, sonra hook. Prop ve oyun anlamın hizmetindedir. Somut detay yazildikca sarki kisisellesir; slogan tek basina yetmez.",
    moodHint: "temaya uygun; varsayilan olarak hareketli ve neseli",
    propBank:
      "konu kutusundaki her somut isim icin dokunulabilir prop; sayilan nesneler dogru sayida",
    hookAngle: "Konunun en guclu HISSINI ilk 5 sn'de sticky cumleyle soyle; uzun aciklama yok.",
    gameMechanic: "Anlami ilerletecek bir tekrar/oyun kur — ezber listesi degil.",
    lyricSeedWords: "konu kutusundaki somut isimler + o isimlerin HISSİ — soyut slogan tek basina yok",
    lyricSpark:
      "Once 'bu sarki ne anlatiyor?' tek cumle. Sonra o cumleyi sahne+hook yap. Ogretmen anlatimi YASAK.",
    meaningPromise:
      "Kullanicinin konusu bos ritim oyunu degil: tek bir duygu vaadi tasir ve nakarat onu soyler.",
    verseArc:
      "V1 vaadi sahneye koy. V2 kucuk aksilik veya yeni ayrinti. V3 vaadi sicak kapat. Nakarat ayni anlam. Outro kisa veda.",
    bpmGuide: "96-118",
    arrangementHint: "temaya uygun broadcast-safe groove; major key default",
  },
];

/*
 * Stil promptlari PRODUKSIYON TARIFIDIR (Ingilizce): groove, enstrumantasyon,
 * davul/bas, nakarat davranisi, miks rengi. UI'da tagline + groove TR.
 */
export const SONG_STYLES: SongStyle[] = [
  {
    id: "nursery",
    label: "Tekerleme / ninni ritmi",
    tagline: "Bes notalik, soylenebilir klasik tekerleme",
    prompt:
      "classic nursery-rhyme cadence: steady quarter-note pulse ALWAYS audible under the vocal (soft kick or shaker never drops out), singsong melody within a five-note range, simple AABB rhyme with literal repetition. Instrumentation: music box, soft ukulele, glockenspiel, gentle continuous shaker. Warm, safe; every phrase resolves clearly so the hook is easy to hum — still rhythmically ALIVE, never silent bed",
    stagingHint:
      "Staging: readable prop reveals on the pulse; toys gently bob or sway every beat; warm soft light; camera holds with a tiny breath-bob so the frame never feels frozen",
    groove: "Duzenli dortluk nabiz, dar melodi, yumusak tekrar",
    bpmRange: { min: 70, max: 100 },
    bestForAges: ["1-3", "3-5"],
    mixColor: "warm midrange, soft high sparkle, no harsh compression",
    beatVisuals:
      "Soft continuous pulse: props sway on quarters, curtain/leaf micro-motion, character gentle knee-sway; NO dead still frames — even nursery stays alive",
  },
  {
    id: "kidspop",
    label: "Cocuk pop (enerjik)",
    tagline: "Kipir kipir viral family-pop — dans eder gibi",
    prompt:
      "HYPER-BOUNCY polished bright pop like a viral YouTube-family dance MV: LOUD-CLEAR four-on-the-floor kick that NEVER drops, handclaps on 2 and 4 always audible, super-bouncy syncopated bass that makes bodies wiggle, bright major-key earworm hook. Instrumentation: sparkling synth pluck, ukulele chops, glockenspiel sparkles, shaker on every 16th, layered group-harmony echoes and a cheerful 'hey!' shout INTO every chorus. From second 0 it must feel kipir-kipir / impossible to sit still; chorus EXPLODES with extra claps, wider stereo, tom fills and more percussion sparkle — peak family party energy, still broadcast-safe (no trap 808, no club aggression)",
    stagingHint:
      "Staging: saturated MV party set; props POP/bounce/wiggle on EVERY kick; character nonstop knee+shoulder bounce; chorus = brighter key + confetti/sparkles + more toys dancing in depth; camera soft beat-bob like a real family dance video",
    groove: "Kipir kipir four-on-the-floor + 2-4 alkis, ziplayan bas, nakarat patlamasi",
    bpmRange: { min: 112, max: 130 },
    bestForAges: ["3-5", "6-8"],
    mixColor: "bright wide stereo, punchy kick, sparkling tops, radio-clean vocal",
    beatVisuals:
      "MAXIMUM kipir-kipir MV: kick-locked knee bounce EVERY beat, shoulder wiggle, gentle side-to-side groove, prop hops on 1 and 3, background lights/particles pulse with claps; zero frozen talking-head frames",
  },
  {
    id: "callresponse",
    label: "Soru-cevap (call and response)",
    tagline: "Cagri-yanit — yanitta kipir kipir rebound",
    prompt:
      "call-and-response game song with a CONTINUOUS lively bed (cajon + busy shaker never fully stop): lead sings a short playful call, group harmony SNAP-answers; claps/stomps land hard on the answer; after each pause the groove REBOUNDS louder and bouncier. Instrumentation: acoustic guitar chops, cajon, tambourine, playful whistle hooks. Invite-in game energy with kipir-kipir rebound — danceable, not sleepy",
    stagingHint:
      "Staging: CALL = lean to a real prop; RESPONSE = prop wiggle/pop + body bounce SNAP-back; between calls keep soft groove bounce so the MV never dies",
    groove: "Cagri → SNAP yanit + kipir rebound, alkisli bounce",
    bpmRange: { min: 100, max: 120 },
    bestForAges: ["1-3", "3-5", "6-8"],
    mixColor: "intimate lead vs wider choir answer; playful whistle in air",
    beatVisuals:
      "Call = micro lean-in; Response = prop pop + full-body rebound + clap flash; ambient bounce between calls — always kipir, never dead air",
  },
  {
    id: "countalong",
    label: "Hareketli / saymali",
    tagline: "Dur-kalk patlamasi — say, zipla, enerji birikir",
    prompt:
      "high-energy action count song: stop-and-go drama OVER a pumping bouncy bed — freeze on cue then BURST back LOUDER and kipir-kipir; countable gesture beats (clap-clap, stomp-stomp), one new sparkle layer each verse. Instrumentation: marimba runs, woodblock counts, bouncy bass, shaker, cymbal swell into every chorus. Movement-driving party energy — after each freeze the groove returns MORE alive",
    stagingHint:
      "Staging: CRITICAL count fidelity — 1-2-3 means that many distinct props tapped in time; freeze ON a prop; burst = jump-energy bounce + light swell (no real cuts)",
    groove: "Freeze → kipir burst; sayma vuruslari; her kitada yeni katman",
    bpmRange: { min: 108, max: 126 },
    bestForAges: ["3-5", "6-8"],
    mixColor: "punchy transient drums, clear count clicks, rising layers",
    beatVisuals:
      "Comedy freeze then explosive kipir bounce-back; counted props hit on woodblock; background toys shake when the beat returns",
  },
  {
    id: "lullaby",
    label: "Sakin ninni",
    tagline: "6/8 sallanma, dimming dinamik, fisiltiya inis",
    prompt:
      "gentle lullaby: slow rocking 6/8 sway with a SOFT continuous pad+music-box bed (never dead silence), felt piano, warm strings, breathy hum. No sudden accents; dynamics fade gradually like dimming lights — still softly ALIVE with rocking motion",
    stagingHint:
      "Staging: soft lamps, blanket/plush with fabric weave; slow rock of props matching 6/8; dimming lights; camera breathes gently — calm liveliness, not dance chaos",
    groove: "Yavas 6/8 sallanma, ani vurus yok, fade-out",
    bpmRange: { min: 70, max: 88 },
    bestForAges: ["1-3", "3-5"],
    mixColor: "soft low-pass warmth, breathy air, no harsh peaks",
    beatVisuals:
      "Slow living rock only: cradle sway, mobile spin, curtain drift on the 6/8; calm but never frozen portrait",
  },
  {
    id: "funkgroove",
    label: "Funky dans (bounce)",
    tagline: "Omuz kipir, wah chuck, dans MV enerjisi",
    prompt:
      "broadcast-safe funk BOUNCE overload: tight syncopated bass ALWAYS present and groovy, muted wah-guitar chucks, punchy friendly horn stabs on the hook, strong backbeat handclaps, light shaker. Shout-along 'hey!' before chorus; clean bright mix; shoulders/knees MUST kipir-kipir bounce every bar — YouTube-family dance-MV energy without adult club aggression",
    stagingHint:
      "Staging: props hitch on the off-beat; bold primary colors; character shoulder+knee bounce synced to bass while touching a tangible toy; background silhouettes groove; chorus = brighter bounce",
    groove: "Senkopeli bas, off-beat chuck, kipir omuz bounce, alkisli backbeat",
    bpmRange: { min: 104, max: 120 },
    bestForAges: ["3-5", "6-8"],
    mixColor: "tight low-end bounce, dry claps, friendly horn sparkle",
    beatVisuals:
      "Nonstop kipir: off-beat prop hitch, shoulder+knee funk bounce EVERY bar, horn stab = color flash or prop pop; zero idle poses",
  },
  {
    id: "swing",
    label: "Neseli swing / caz",
    tagline: "Cartoon kipir — yuruyen bas, snap, zipla",
    prompt:
      "playful family swing-jazz with cartoon bounce: walking upright bass NEVER stops, brushed drums with lift, jaunty clarinet + muted trumpet answers, finger snaps on 2 and 4, light shaker. Melody skips with scat-friendly syllables; constantly light-on-its-feet kipir energy — vintage cartoon dance MV",
    stagingHint:
      "Staging: cheeky prop gags timed to snaps; scooty light feet; swingy camera arc; toys squash-and-stretch on 2 and 4",
    groove: "Swing 2-4 snap, yuruyen bas, cartoon kipir ziplama",
    bpmRange: { min: 104, max: 122 },
    bestForAges: ["3-5", "6-8"],
    mixColor: "warm vintage mids, brushed air, cheeky brass/clarinet",
    beatVisuals:
      "Snap-timed prop gags, cartoon foot scoot, walking-bass body sway, anti-phase background swing — always kipir",
  },
  {
    id: "folk",
    label: "Akustik dost (kamp atesi)",
    tagline: "Parmak gitar, ayak vurusu, birlikte mirilti",
    prompt:
      "cozy acoustic folk singalong with a CLEAR foot-tap / knee-slap pulse under every bar: fingerpicked guitar, soft mandolin, warm group hums under the chorus. Storytelling verses, easy unison chorus; campfire intimacy but still rhythmically present — soft liveliness, not stillness",
    stagingHint:
      "Staging: wood/cloth textures, campfire glow; handmade props; intimate medium shot with soft foot-tap bounce in the body and flame flicker synced lightly to the pulse",
    groove: "Parmak gitar nabzi, ayak vurusu, unison nakarat",
    bpmRange: { min: 88, max: 110 },
    bestForAges: ["1-3", "3-5", "6-8"],
    mixColor: "close mic intimacy, wood resonance, soft group hums",
    beatVisuals:
      "Foot-tap visible, flame/curtain flicker on the pulse, soft group sway on chorus; warm living set, never static",
  },
  {
    id: "worldbounce",
    label: "Dunya ritmi (world bounce)",
    tagline: "Shaker dongusu — gunesli kipir perkusyon",
    prompt:
      "broadcast-safe world-groove BOUNCE: warm hand drums + continuous busy shaker circle that never drops, kalimba/marimba ostinato, sunny major melody with danceable lilt. Playful global percussion colors (not sacred pastiche). Chorus adds group claps, whistle/flute hook and extra bounce layers — sunny family MV kipir energy",
    stagingHint:
      "Staging: woven baskets, toy drums; sunny/market colors; every percussion hit = prop tap; background toys pulse in a circle dance",
    groove: "El davulu + surekli shaker, kalimba, alkisli kipir nakarat",
    bpmRange: { min: 104, max: 120 },
    bestForAges: ["3-5", "6-8"],
    mixColor: "earthy mids, sunny tops, organic room around drums",
    beatVisuals:
      "Circular kipir: shaker motion in props/camera, hand-drum taps visible, sunny dust motes pulse; full-body groove never stops",
  },
  {
    id: "electrokids",
    label: "Parlak elektro (family electro)",
    tagline: "LED kipir — temiz kick, pixel parti enerjisi",
    prompt:
      "bright broadcast-safe electro-pop PARTY: clean four-on-floor kick ALWAYS loud and clear, gentle sidechain pump that makes the mix breathe/bounce, sparkling chiptune arpeggios, friendly blips, constant soft shaker. No aggressive EDM drops, no trap 808s. Chorus opens wider pads + handclaps + extra sparkle — colorful LED family dance MV, kipir-kipir from bar 1, crystal vocal",
    stagingHint:
      "Staging: neon-soft toy lights blink on EVERY kick; geometric colorful sets; props light-pulse with arpeggios; camera micro-bob locked to four-on-floor; chorus = more blinks + sparkles",
    groove: "Temiz kick + sidechain kipir, arpej pariltilari, alkisli chorus",
    bpmRange: { min: 114, max: 130 },
    bestForAges: ["3-5", "6-8"],
    mixColor: "crystal vocal, glittery highs, punchy controlled low end",
    beatVisuals:
      "LED blink on every kick, arpeggio sparkles as particle bursts, character kipir bounce locked to four-on-floor; hyper-alive party MV",
  },
  {
    id: "softballad",
    label: "Yumusak ballad",
    tagline: "Akustik hikaye, genis nefes, sicak nakarat",
    prompt:
      "gentle family ballad with a soft continuous pulse (brushed kick or heartbeat pad under the vocal — never empty): fingerpicked/soft-strum guitar, warm piano, subtle strings under chorus. Hopeful major color; chorus lifts with harmony — emotionally alive, cinematic MV intimacy",
    stagingHint:
      "Staging: golden-hour practicals, storybook props, slow push-ins; micro-expressions; background soft parallax so the ballad still breathes",
    groove: "Nefesli frazlar, yumusak gitar/piyano, nakaratta armoni",
    bpmRange: { min: 78, max: 100 },
    bestForAges: ["3-5", "6-8"],
    mixColor: "warm acoustic body, soft pad bloom on chorus, intimate vocal",
    beatVisuals:
      "Breathing camera push, fabric/hair micro-motion, light shafts drift; chorus = warmer bounce in body and background life",
  },
  {
    id: "parade",
    label: "Gecit / marş alkisi",
    tagline: "Alkışlı geçit — neşeli yürüyüş, kipir konfeti",
    prompt:
      "cheerful family parade march with party lift: steady walking pulse ALWAYS audible (soft snare tick + clap), brass-like stabs, whistle and cowbell, BIG group claps on chorus, light shaker underfoot. Friendly street-parade energy — proud, chantable, shout-along 'hey!' — outdoor MV kipir liveliness without militarism",
    stagingHint:
      "Staging: streamers, toy drums, soft flags; march-in-place bounce every step; confetti bursts on chorus claps; crowd-of-toys waving on the beat",
    groove: "Yuruyus nabzi, trampet, alkis+zil, kipir gecit enerjisi",
    bpmRange: { min: 108, max: 124 },
    bestForAges: ["3-5", "6-8"],
    mixColor: "forward snare tick, bright brass sparkle, wide clap chorus",
    beatVisuals:
      "March kipir every step, flags/streamers flap on snare, confetti on chorus claps; background toys parade-wave — peak outdoor family-MV energy",
  },
];

export const SONG_LYRIC_CRAFT_LOCK = `YARATICI SOZ ZANAATI (HIT COCUK SARKISI — OGRETMEN CALISMASI / VAZ DEGIL):

GERCEK SANATCI AGZI (PROFESYONEL SOYLEYEN YAZAR — EN ONCELIKLI):
- Sozler bir stüdyo sanatcisinin mikrofon basinda SOYLEYECEGI gibi aksin: dogal nefes, vurusa oturan vurgu, agizda yuvarlanan kafiye, ozenilmis prosodi.
- Robotik "sarki odevi" / calisma kagidi dili YASAK. Gercek kids-pop hit gibi: samimi, ozguvenli, oyunbaz, yayinlanabilir.
- Sanatci cocuklara SARKI soyler — ogretmen gibi emretmez. Duygu: sicak star enerjisi, yapmacik bebek dili yok.
- Her dize SOYLENEBILIR olsun: zorlama kelime yigini, carpik cumle, agza sigmayan hece yok. Turkce dogal vurgu; onemli kelime muzikal vuruda gelsin.
- Kafiye ve ic kafiye "zorlama" degil; sanatci o satiri gururla soyleyecek kadar temiz olsun.
- Nakarat bir sanatcinin imza cumlesi gibi sticky: tek dinleyiste mirildanilabilir.

ANLAM ONCE (BOS RITIM OYUNU / UZUV-RENK LISTESI YASAK):
- Her sarkinin TEK duygusal vaadi olsun (tema meaningPromise). Dinleyici "bu sarki ne anlatiyor?" diye sorsa 1 cumlede cevaplanabilsin.
- Nakarat o vaadi tasiir. Verse'ler ayni vaadi ilerletir (verseArc) — her kita yeni bir mini-sarki ACMAZ.
- Yansima ses (tap tap, cuf cuf, pit pit) CESNI olabilir; tek basina dize YASAK. Sesin yaninda NEDEN / HIS / KUCUK OLAY olsun.
- KOTU: "Ayak tap tap, burun tik tik, el sap sap" (uzuv listesi).
- IYI: "Ayaklarim yol bilir / burnum evi koklar / ellerim seninle alkislar — ev sicacik, biz buradayiz."
- KOTU: "Kirmizi sari mavi yesil" / "Pazartesi sali carsamba" (ezber).
- IYI: her adin yaninda bir sahne (kirmizi cilek isirdi, pazartesi corba kokar).
- Secilen baslik + hookLine + meaningPromise AYNI vaadi soylesin; ucu uca kacmasin.
- Her kita bir adim: kesfet/hisset → kucuk aksilik veya yeni ayrinti → ayni anlam daha sicak doner.

PIYASADAKI HIT'LERIN ORTAK DNA'SI (icerigi ASLA kopyalama; yalnizca zanaat):
- Sticky hook: 4-10 hece, mirildanilabilir; bazen tatli hece oyunu (hop-pa, la-la, tip-tip) + BIR somut kelime.
- Beklenmedik somut imge: "sabun" yerine "bulut gibi kopuk"; "tren" yerine "uc kirmizi vagon siraya girdi".
- Twist satir: A-A duz gider, B satiri kucuk surpriz / komik aksilik / yeni ses getirir.
- Karakter sesi: tipik sozu + imza hareketi soze sinsin; jenerik "cocuk sarkisi dili" YASAK.
- Duyusal zincir: ayni dizede goruntu + ses + dokunus ("ilik su, mis sabun, kaygan kopuk").
- Call/echo: dinleyiciyi iceri ceken kisa yanit — ama yonerge listesi gibi degil, oyunun icinde.

YASAK KLISELER (bunlari yazarsan basarisiz sayilir):
- "Hadi yapalim / Simdi sayalim / Tekrarla / Ellerini yika / Bakalim" ogretmen emirleri
- Tohum kelime listesini virgul virgul / sirayla dokmek
- Her dizede ayni bos fiil ("bak bak", "gel gel", "yap yap")
- Bos slogan ve vaaz: "cok guzel", "ne kadar eglenceli", "paylasmak guzeldir"
- Yetiskin pop filler (yeah-yeah) ve Ingilizce slogan yigini
- Nakaratsiz duz paragraf / hikaye anlatimi / calisma kagidi tonu
- Anlamsiz kelime salatasi / soylenemeyen carpik cumleler

ALTIN ORNEK KALIPLARI (asagidakileri KOPYALAMA — ayni zanaatla OZGUN yaz):
KOTU: "Ellerimizi yikayalim, sabun suralim, temiz olalim"
IYI: "Musluk cik cik, sabun kayar / Kopuk bulut avucuma konar / Pit pit sip sap — mis kokar!"
KOTU: "Bir iki uc sayalim, balonlari sayalim"
IYI: "Bir sari balon tak / Iki mavi, uc kirmizi bak / Hepsi siraya dizildi — alkis tak!"
KOTU: "Gunaydin arkadaslar, hadi uyanin"
IYI: "Perde swish — gunes cebimden cikar / Ayna gulumsedi, gunaydin parilar!"

NAKARAT ALTIN KURALI:
- Tek yapiskan merkez cumle + 1 echo/tekrar; araba koltugunda soylenecek kadar sticky
- Her tekrarda soz BIREBIR ayni; sadece enerji/kamera degisir
- Ilk 5 sn'de nakaratin kalbi (veya mini-versiyonu) duyulsun

KREATIF ZORUNLULUK (her sarki):
- Her kitada en az bir siradisi imge, ses oyunu VEYA karakter ic sesi
- En az bir dizede aliterasyon veya ic kafiye
- Baslik + hook bir poster cumlesi olsun
- lyricSpark (tema kivcilcimi) dogrultusunda yaz; tohum kelimeler cesni — tarif degil`;

/**
 * Soz soylenirken ekranda AYNI anda o sozun gorseli olmak zorunda.
 * Klip promptlari buna gore kurulur.
 */
export const SONG_LYRIC_PICTURE_SYNC_LOCK = `LYRIC ↔ CLIP ↔ VIDEO SYNC LOCK (NON-NEGOTIABLE):
- THIS CLIP'S AUDIO is the SCRIPT of the picture: sung lyrics AND any spoken / talk-sing / greeting in the song ("merhaba", "bakın", spoken asides). If a word is HEARD, that meaning must be VISIBLE in the same moment (object, count, color, animal, action, or gesture).
- Example: lyrics say "kelebek uçar" / "butterfly flies" → a butterfly with beating wings MUST be airborne in THIS clip — not implied, not a later clip, not a poster.
- Spoken lines in the song are still picture cues: mouth those exact words and act them (wave on merhaba) — never cover speech with a generic dance that ignores the words.
- Never stage a generic dance while ignoring the audio content. Never show unrelated props that the audio did not invite.
- CONFIRM the locked singer + friends: same face, species, height, costume as the character prompt / reference — every clip, no redesign.
- Build the shot in this order: (1) exact heard words → (2) on-screen action that illustrates those words → (3) must-show props from those words → (4) confirmed cast → (5) camera/light/set supporting that beat.
- imagePrompt MUST open with: While singing: "[exact lyric]". On-screen: [concrete action + props matching those words].
- Counting / naming / pointing in the lyric = the character physically counts / names / points to REAL props in frame.
- If sync is broken (audio says "three wagons" or "kelebek uçar" but picture shows empty hands / no butterfly), the shot FAILS.`;

/** Tum stiller icin ortak canli MV kilidi (ninni dahil yumusak form). */
export const SONG_MV_LIVELINESS_LOCK = `LIVELY FAMILY MUSIC-VIDEO LOCK (YouTube family MV energy):
- The backing groove is AUDIBLE and CONTINUOUS under the vocal for the whole clip — kick/shaker/bass/pad appropriate to the style must not vanish.
- Picture stays ALIVE every second: body groove on the beat, props reacting to rhythm, living multi-layer background (parallax, particles, lights, distant motion).
- Genre beatVisuals drive HOW it moves (funk = shoulder bounce, electro = LED kick blink, lullaby = slow rock only) — match the selected style.
- Forbidden: frozen talking-head, empty flat backdrop, silent bed with no pulse, identical idle pose across seconds.
- Still broadcast-safe: no frantic chaos, no dizzy spins, no adult club aggression.`;

/**
 * Tek sarki = tek sarki sesi. Klipler ayri uretilse bile timbre/pitch/aksan degismez.
 * voiceTone yalnizca duygu/enerji notudur; yeni sarki soyleyen degildir.
 */
export const SONG_VOICE_IDENTITY_LOCK = `SINGER VOICE IDENTITY LOCK (NON-NEGOTIABLE ACROSS EVERY CLIP):
- ONE continuous singer for the WHOLE song: identical timbre, pitch range, accent, voice character, warmth and diction from clip 1 through the final clip.
- Never switch singers, never gender-swap the voice, never switch singer identity, never a thin cartoon squeak, never a different accent mid-song.
- Clip N is the NEXT sung line of the SAME performance — as if one unbroken vocal take was sliced into shots.
- Delivery notes (voiceTone) may change ENERGY only (brighter / softer / whispery chorus) — they must NOT invent a new voice identity.
- Backing track keeps the same key/BPM under that SAME singer; no duet with a second lead vocal.`;

/**
 * Bos / kayan / bozulan kliplere karsi uretim kilidi.
 */
export const SONG_MV_PRODUCTION_LOCK = `ULTRA MUSIC-VIDEO PRODUCTION LOCK (detail + continuity + anti-glitch):
- DENSE world: foreground prop layer + mid-ground singer stage + deep readable background — never empty voids, never flat single-color walls, never sparse toy-on-void.
- Materials read on close inspection: fabric weave, fur strands, wood grain, paint chips, ceramic glaze, soft contact shadows, ground contact under every foot and prop.
- SERIAL MV CONTINUITY: each clip is the next consecutive seconds of ONE music video — soft match-on-action into the prior last second; same set geography, costume, lighting warmth, prop materials; camera may reframe but the world does not reset.
- LOCOMOTION: planted feet with real weight transfer on the beat (knee bounce / step) — absolutely NO sliding, skating, gliding, rubbery foot-smear, moonwalk drift or ice-skate travel.
- ANTI-GLITCH: no face/body morph mid-clip, no melting limbs, no warped proportions, no flicker redesign, no teleport props, no z-fighting, no clipping through geometry, no mirrored twin duplicates.
- Every second shows a readable change in gesture, prop contact OR expression — never a frozen idle portrait while audio sings.`;

/**
 * Her sarki klibinde (1. klip → son klip) AYNI karakter — bozulma / morph / yeniden tasarim YASAK.
 * Prompt builder + composeShotPrompt her cikisinda tekrarlanir.
 */
export const SONG_CHARACTER_FIDELITY_LOCK = `CHARACTER FIDELITY LOCK — EVERY CLIP (NON-NEGOTIABLE, MAXIMUM PRIORITY):
- This lock applies to EVERY music-video clip of the song — clip 1 through the final outro — identical rules every time.
- The singer must stay 100% ON-MODEL: same face shape, species, fur/surface colors and pattern, eye color and iris highlights, ear/tail/snout details, HEIGHT, body proportions, head-to-body ratio, silhouette and build.
- Costume head-to-toe stays IDENTICAL every clip (colors, materials, stitching, accessories, signature prop) — no wardrobe drift, no random recolor, no new hat/outfit mid-song.
- Supporting cast who appear keep THEIR locked faces/colors/costumes too — never swap extras into the lead's identity.
- FORBIDDEN between clips or mid-clip: redesign, recolor, identity change, species swap, morph, melt, stretch, squash-warp of the face/body, flicker redesign, twin duplicates, suddenly taller/shorter/thinner/heavier, extra limbs, mirrored clones.
- Reference / turnaround image(s) reinforce identity; they do NOT replace the written FULL lock — ALWAYS keep written face+body+costume detail in the prompt even when a reference is attached.
- Character consistency OUTRANKS camera tricks, background detail, choreography flourishes and lyric props. If anything conflicts, keep the character correct first.
- Prefer a slightly simpler background over ANY character drift.`;


export function songThemesForAge(ageBand: string): SongTheme[] {
  return SONG_THEMES.filter((t) => t.ageBands.includes(ageBand));
}

export function songStyleById(id: string): SongStyle | undefined {
  return SONG_STYLES.find((s) => s.id === id);
}

export function songThemeById(id: string): SongTheme | undefined {
  return SONG_THEMES.find((t) => t.id === id);
}
