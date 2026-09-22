import { prisma } from "@/server/db";
import { recordEvent } from "@/server/lib/logger";
import { analyzeCuriosityFlow, curiosityWarnings, type CuriosityFlowReport } from "@/lib/curiosity-flow";

/**
 * Merak Mimarisi.
 *
 * Dort sablonun da (anlatici, cocuk animasyonu, cocuk sarki klibi, uzun form belgesel) tek amaci var:
 * izleyici her an "acaba ne olacak?" diye merak etsin ve videoyu birakmasin.
 * Kurallar burada tek merkezde tutulur; her uretim istemi bunlari gomer.
 */

/** Tum sablonlarin paylastigi cekirdek: acik dongu, testere disi, vaat-erteleme. */
export const CURIOSITY_CORE_RULES = `
MERAK MIMARISI KURALLARI (izleyiciyi tutma — cok onemli):
- ACIK DONGU: Hicbir paragraf/bolum kendi icinde tamamen kapanmasin. Her dogal durak noktasi ya yeni bir soru acsin, ya bilgiyi yarim biraksin, ya da beklenmedik bir isaret koysun. Cevap sonraki bolumde gelsin ama o bolum de yeni bir dongu acsin.
- TESTERE DISI GERILIM: Gerilim/merak duz cizgide ilerlemesin; yukselis -> kucuk rahatlama -> daha yuksek yukselis seklinde dalgalar halinde artsin. Art arda iki "sakin" bolum olmasin.
- VAAT VE ERTELEME: Acilis kancasi buyuk bir vaat versin (or. "hayatimda yasadigim en tuhaf olay"). Bu vaadin cevabini tek seferde acma; sona kadar kucuk parcalar halinde dagit.
- KANCA CUMLELERI: Onemli bolum sonlarini merak uyandiran kisa cumlelerle bitir ("Ama kapiyi actigimda gordugum sey bambaskaydi." gibi). Bu cumleler dogal konusma akisinda kalsin, yapay "cliffhanger" kaliplarina donusmesin.
- TAHMIN KIRMA: Izleyicinin tahmin edecegi yonu en az bir kez kir (twist). Twist mantikli olsun, onceden ekilen kucuk ipuclariyla desteklensin.
`.trim();

/**
 * Cocuk animasyonu: dogal konusma + yumusak ileri enerji.
 * Surekli soru / "hep merak" kalibi YASAK (10 dk / 60 klipte monotonlasir).
 */
export const CURIOSITY_KIDS_RULES = `
DOGAL AKIS + YUMUSAK ILERI (cocuk animasyonu — diyalogta zorla soru/merak YASAK):
- Konusma DOGAL ve AKISKAN olsun: gozlem, tepki, emir, karar, nefes, paylasim, kisa kutlama KARISIMI.
- Her cumle / her klip SORU olmak ZORUNDA DEGIL. "Hep merak", "acaba ne olacak?", surekli soru isareti kalibi YASAK.
- Soft ileri enerji yeter: yarim hareket, devam eden eylem, duygusal baglanti, sonraki adima dogal gecis — interrogative kanca zorunlu degil.
- Jenerik bos sohbet ("arkadasim yardim et", "ne guzel") YASAK; canli ve sahneye bagli kalsin.
- Gerilim SERBEST ama buzda/karda KAYMA-SLIDE locomasyonu YOK: ruzgar, zor etap, ip gerilmesi, yorgunluk, takim/ekipman cozer, rahatlama gelir.
- Dehset / olum / kan / kaybolma tehdidi YOK. Heyecan cesaret + takim + fiziksel eylemden gelsin.
`.trim();

/** Cocuk animasyonu kanca puanlamasi — soru zorlamasi yok. */
export const CURIOSITY_KIDS_SCORING_RULES = `
DEVAM ENERJISI PUANLAMASI (cocuk animasyonu):
- curiosityScore 0-10: soft ileri cekme yogunlugu (SORU olmak zorunda degil).
- hookNote: Turkce kisa — soft devam enerjisi (gozlem / yarim eylem / duygu). Soru isareti zorunlu DEGIL; "hep soru" kalibi YASAK.
- Art arda iki sahne 4'un altinda olmasin; ortalama ~5-7 yeter. Doruk 9-10 nadir ve dogal olsun, her pakette zorlama.
`.trim();

/** Sarki sozlerinde merak: nakarat cevap verir, kita yeni soru acar. */
export const CURIOSITY_SONG_RULES = `
SARKIDA MERAK (sozlerle tutma):
- SORU-CEVAP DONGUSU: Kita bir soru veya yarim bilgi versin, nakarat onu cevaplasin; sonraki kita YENI bir soru acsin. Boylece dinleyici sonraki dizeyi bekler.
- SAYMA VE TAMAMLAMA: "Bir... iki... peki ya ucuncusu?" gibi tamamlanmamis sayma/siralamalar kullan. Dinleyici tamamlanmasini bekler.
- SAKLI SURPRIZ: Sarkinin basinda kucuk bir sir kur ("Sepette ne var dersin?"), ortasinda ipucu ver, sona dogru ac.
- SES ISARETI: Yansima sesleri (tik tak, sip sip, pat pat) once gelsin; neyin sesi oldugu bir sonraki dizede anlasilsin.
- DIZE SONU KANCASI: Klip sonlari "tamamlandi" hissi vermesin; bir sonraki dizeyi cagirsin (yarim kalan kafiye, "ve sonra...", cevap bekleyen soru).
- BEKLENTI KIRMA: En az bir yerde beklenen kafiye/sonuc yerine tatli bir surpriz gelsin (gulumseten, korkutmayan).
- SON KLIP: Sarkiyi cozsun, kutlasin ve izleyiciyi bir sonraki videoya baglayan minik bir soru biraksin.
`.trim();

/** Sahne/klip basina kanca puanlamasi icin ortak olcek. */
export const CURIOSITY_SCORING_RULES = `
KANCA PUANLAMASI:
- curiosityScore 0-10: 0 = tamamen kapali, hicbir soru yok; 10 = izleyici sonraki sahneyi gormeden duramaz.
- Art arda iki sahnenin puani 5'in altinda OLMASIN. Ortalama en az 6 olsun.
- En az bir sahne 9 veya 10 olsun (doruk merak).
- hookNote: o sahnenin izleyicide biraktigi SORUYU tek cumleyle yaz (Turkce). Soru yoksa sahneyi yeniden kurgula.
`.trim();

/** Uzun form belgesel: ayni merak yayı, ama 8-12 dakikada bir yumusak cliffhanger. */
export const CURIOSITY_LONGFORM_RULES = `
UZUN FORM BELGESEL MERAK (15-60 dk slayt anlati):
- TEK OMURGA: Butun film tek soru / tek dosya / tek sir etrafinda doner. Her 20-30 saniyede yeni mini-hikaye ACMA.
- UZUN YAY: Acilis kancasi buyuk vaadi versin; cevabi sona sakla. Ortada kanit, tanik, celişki, yanlis iz ekle.
- 8-12 DAKIKA CLIFFHANGER: Yaklasik her 8-12 dakikada yumusak bir kanca birak (yeni belge, eksik sayfa, beklenmedik isim). Yapay "ama o gece..." kaliplari YASAK; dogal belgesel gecisi kullan.
- UCUNCU TEKIL: Kameraya konusma, "ben" itirafi, "merhaba ben X" YOK. Anlatici gorunmez dis sestir.
- YAZI YASAGI: Sahne / gorsel tarifinde ekranda yazi, altyazi, logo, tarih seridi ISTEME.
- UYKU / MEDITASYON: Bu turlerde gerilimi dusur; merak yumusak devam enerjisi olsun, korku yok.
`.trim();

/** Iliski/ev dramasi: belgeseldeki ucuncu tekil kilidi BIRINCI TEKILI bozmasin. */
export const CURIOSITY_LONGFORM_DRAMA_RULES = `
UZUN FORM ILISKI DRAMASI (slayt anlati):
- TEK OMURGA: Ayni iliski / kirilma / ev. Her 15-20 saniyede yeni mini-hikaye ACMA.
- BIRINCI TEKIL dis ses. Anlatici ekranda yok. "Merhaba ben X" yok. "Isim:" konusmaci etiketi yok.
- Belgesel "ucuncu tekil / ben yasagi" burada GECERSIZ — "ben" dogal.
- Yatak, soyunuk, pornografik tarif YASAK. 18 yas alti yok.
- Kanit somut: mesaj, kapi, evrak, parfum, anahtar. Bagiris ve vaaz yok.
`.trim();

/**
 * SURUKLEYICILIK (her tur icin zorunlu).
 *
 * "Merak" tek basina yetmiyor: 15-60 dakikalik bir anlatida izleyici sahneyi
 * GORMEDIGI icin sadece sesle tutulur. Bu blok her 20-30 saniyeye somut bir
 * cekim gucu koymayi zorunlu kilar: sahne, kanit, mikro-gerilim, beden tepkisi.
 */
export const CURIOSITY_GRIP_RULES = `
SURUKLEYICILIK (her an — cok onemli, sazlama/gevseme YASAK):
- SAHNE GOSTER, OZET GECME: "Aramiz bozuldu" gibi ozet YASAK. O ani sahne olarak yaz: yer, saat, kim ne yapti, hangi cumle soylendi.
- HER 20-30 SANIYEDE BIR CEKIM: her kisa parcada su besliden EN AZ BIRI olsun — yeni bilgi, kucuk celiski, somut kanit, beklenmedik tepki, yaklasan tehdit.
- SOMUT DETAY: isim, saat, rakam, marka yerine somut nesne (kirik bardak, islak mont, 03:14'te gelen mesaj, ikinci sarj kablosu). Soyut duygu kelimeleri (uzuldum, sasirdim) yerine bedeni yaz: elim titredi, kulaklarim ugulduyor, nefesim yetmedi.
- BES DUYU: ses (kapinin ciriltisi), koku (yabanci parfum), dokunma (soguk anahtar), tat, isik. Her bolumde en az iki duyu gecsin.
- MIKRO-GERILIM: sahne icinde saat isliyor olsun — "on dakika sonra eve gelecekti", "telefonun sarji %4". Bekleme ve zaman baskisi hissedilsin.
- DIYALOGU ANLATIYA GOM: konusmalar TEK ses icinde aktarilsin ("bana bir kez daha sordu: nerede kaldin?"). "Isim:" etiketi ve coklu konusmaci YASAK.
- CUMLE RITMI: uzun-uzun-KISA. Gerilim doruklarinda 3-6 kelimelik kisa cumleler. Ayni kalipla baslayan cumleleri tekrarlama.
- SORU YERINE ACIK BILGI BOSLUGU: "acaba ne olacak?" diye sormak yerine izleyicinin kendi soracagi bosluk birak (bir sey gormus ama daha soylememis olsun).
- BILGI SIRASI: izleyici bir seyi kahramandan ONCE anlarsa gerilim buyur; bunu bilerek kullan (kahraman fark etmemisken izleyici fark etsin).
- TEKRAR YASAK: ayni bilgiyi, ayni cumleyi, ayni sikayeti ikinci kez anlatma. Her bolum hikayeyi ILERLETSIN; yerinde saymak yok.
- ORTA BOLUM COKMESI YASAK: filmin ortasinda tempo dusmesin — orta bolumlerde en az bir yon degistiren gelisme (yeni kanit / yanlis suclama / geri adim) olsun.
`.trim();

/** Aldatma / ihanet / intikam gibi turlerde surukleyiciligin somut karsiligi. */
export const CURIOSITY_DRAMA_GRIP_RULES = `
ILISKI DRAMASINDA SURUKLEYICILIK (aldatma, yasak ask, ihanet, kiskanclik, intikam, bosanma, aile sirri):
- KANIT ZINCIRI: hikaye tek buyuk itirafla degil, KUCUK kanitlarin birikmesiyle yurusun — silinmis konusma, degisen sifre, ters duran ayakkabi, faturada iki kisilik hesap, gec gelen mesaj. Her bolum zincire bir halka eklesin.
- SUPHE MERDIVENI: once masum aciklama inandirici olsun, sonra o aciklamayi coken tek detay gelsin. Kahraman kendini kandirsin; izleyici gercegi once sezsin.
- YAKALANMA GERILIMI: gizli bakan taraf da riskte olsun (telefonu elinde kalmak, eve erken donmek, yanlis kisiye mesaj). Fiziksel yakalanma anlari sahne olarak yazilsin.
- YUZLESMEYI GECIKTIR: buyuk yuzlesme sona sakli; ortada kucuk yuzlesmeler ve geri cekilmeler olsun ("sordum, gulup gecti").
- SESSIZ ANLAR: bagirmak yerine sessizlik, bakis, kapanan kapi. Kufur, hakaret yagmuru ve melodram YASAK.
- ADALET/KARAR: intikam veya bosanmada plan somut ve hukuki/duygusal olsun (avukat, kayit, tanik, imza). Siddet, kan, tehdit yok.
- SON: yuzlesme + karar + kisa "sonrasi" (yeni ev, imza, tek cumlelik ders). Izleyici hem rahatlasin hem film kapansin.
`.trim();

/** Anlatici video: slayttaki "sessizlik" kuralini ezer; aglamak/bagirmak serbest. */
export const CURIOSITY_NARRATOR_DRAMA_OVERRIDE = `
ANLATICI VIDEO — SESSIZLIK KURALINI EZER:
- "Bagirmak yerine sessizlik" slayt senaryosu icindir. Bu filmde aldatilan / yasak ask anlaticisi KIZAR, BAGIRIR, kapi carptirir; cirkin ofke-aglami olabilir.
- Tum film boyunca yalnizca bastirilmis bakis, hüzünlü fısıltı ve "biraz uzgun" sunucu dili YASAK.
- Duruma gore kisa kufur SERBEST (yuzlesme, yalan, kizanma). Kufur yagmuru ve kanli siddet hâlâ YASAK.
- Akis: her cumle bir oncekinin devamı; her 8 saniyede yeni mini-hikaye acma.
`.trim();

/** Son bolum CORE'daki "hicbir sey kapanmasin"i ezer. */
export const CURIOSITY_LONGFORM_END_RULES = `
FILM SONU (uzun form slayt):
- Ortada yumusak kanca / erteleme KALSIN.
- Son bolum ve son %15 MUTLAKA kapansin: ana soru cevap, yuzlesme veya karar, sonra sonrasi.
- "Devam edecek", yeni dizi kancasi, kesik final YASAK. Izleyici "bitti" desin.
`.trim();

/** Anlatici filmin ORTASI acik kalsin; SONU kapanmadan bitmesin. */
export const CURIOSITY_NARRATOR_END_RULES = `
FILM SONU (anlatici — acik donguyu ezer):
- Ortada acik dongu, testere gerilim ve vaat-erteleme KALSIN.
- Son %15-%20 MUTLAKA kapansin: yuzlesme veya karar, sonra sonrasi. Ana vaat / ana soru cevapsiz kalmasin.
- "Devam edecek", yarim itiraf, kesik kapi sesi, "o gece gordugum seyi hala unutamiyorum" diye FINAL YASAK.
- Son sahne/paragraf kancasiz olabilir; izleyici "bitti, anladim" desin. Hikaye yarıda kalmasin.
`.trim();

/** Sablon turune gore merak kurallarini birlestirir. */
export function curiosityRulesFor(templateType: string): string {
  return [CURIOSITY_CORE_RULES, CURIOSITY_KIDS_RULES, CURIOSITY_SONG_RULES, CURIOSITY_SCORING_RULES].join("\n\n");
}

/**
 * Uretim sonrasi merak akisini denetler ve zayif noktalari olay akisina yazar.
 * Uc sablon da (hikaye bolme, sahneleme, sarki klipleri) bunu cagirir.
 */
export async function reportCuriosityFlow(projectId: string): Promise<CuriosityFlowReport | null> {
  const clips = await prisma.clip.findMany({
    where: { projectId, languageVariant: "primary" },
    orderBy: { index: "asc" },
    select: { index: true, curiosityScore: true, hasHook: true },
  });
  if (clips.length === 0) return null;

  const report = analyzeCuriosityFlow(clips);
  const warnings = curiosityWarnings(report);
  await recordEvent({
    projectId,
    step: "curiosity",
    level: report.ok ? "info" : "warning",
    message: report.ok
      ? `Merak akisi saglam (ortalama ${report.averageScore}/10, doruk ${report.peakScore}/10)`
      : `Merak akisinda ${warnings.length} zayif nokta (ortalama ${report.averageScore}/10)`,
    detail: warnings,
  });
  return report;
}
